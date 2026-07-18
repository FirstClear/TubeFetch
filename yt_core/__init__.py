"""Shared YouTube download / metadata core used by CLI and TubeFetch."""

from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yt_dlp

def _compat_format(max_side: int | None = None) -> str:
    """Prefer H.264 + AAC so macOS QuickTime can play video (not audio-only).

    YouTube often serves AV1/VP9 + Opus as "best"; remuxing those into MP4
    yields files that play sound but show a black screen in QuickTime.

    For capped quality, match either orientation: landscape uses height<=N,
    portrait Shorts use width<=N (short side).
    """
    if max_side is None:
        return (
            "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
            "bestvideo[vcodec^=avc1]+bestaudio/"
            "bestvideo*+bestaudio/best"
        )
    n = max_side
    return (
        f"bestvideo[width<={n}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
        f"bestvideo[height<={n}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
        f"bestvideo[width<={n}][vcodec^=avc1]+bestaudio/"
        f"bestvideo[height<={n}][vcodec^=avc1]+bestaudio/"
        f"bestvideo[width<={n}]+bestaudio[acodec^=mp4a]/"
        f"bestvideo[height<={n}]+bestaudio[acodec^=mp4a]/"
        f"bestvideo[width<={n}]+bestaudio/"
        f"bestvideo[height<={n}]+bestaudio/"
        "bestvideo*+bestaudio/best"
    )


QUALITY_PRESETS = {
    "best": _compat_format(),
    "4k": _compat_format(2160),
    "1080": _compat_format(1080),
    "720": _compat_format(720),
    "480": _compat_format(480),
}

ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass
class DownloadJob:
    """Cancellable download handle."""

    cancel_flag: threading.Event = field(default_factory=threading.Event)
    result_path: Path | None = None
    error: str | None = None


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def is_youtube_url(url: str) -> bool:
    u = url.strip().lower()
    return any(
        x in u
        for x in (
            "youtube.com/watch",
            "youtu.be/",
            "youtube.com/shorts/",
            "youtube.com/live/",
            "m.youtube.com/",
        )
    )


def _proxy_opts(proxy: str | None) -> dict[str, Any]:
    if proxy and proxy.strip():
        return {"proxy": proxy.strip()}
    return {}


def extract_metadata(url: str, proxy: str | None = None) -> dict[str, Any]:
    """Fetch video metadata without downloading."""
    if not is_youtube_url(url):
        raise ValueError("请输入有效的 YouTube 视频 / Shorts 链接")

    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        **_proxy_opts(proxy),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise RuntimeError("无法解析视频信息")

    thumbnails = info.get("thumbnails") or []
    thumbnail = info.get("thumbnail") or (thumbnails[-1]["url"] if thumbnails else None)
    duration = _normalize_duration_seconds(info.get("duration"))
    # Always format from numeric seconds when possible — yt-dlp duration_string
    # can be inconsistent (e.g. missing zero-padding or stale webpage text).
    duration_string = (
        _format_duration(duration)
        if duration is not None
        else _coerce_duration_string(info.get("duration_string"))
    )
    return {
        "id": info.get("id"),
        "title": info.get("title") or "",
        "description": info.get("description") or "",
        "duration": duration,
        "duration_string": duration_string,
        "channel": info.get("channel") or info.get("uploader") or "",
        "thumbnail": thumbnail,
        "webpage_url": info.get("webpage_url") or url,
    }


def _normalize_duration_seconds(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return int(round(seconds))


def _coerce_duration_string(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip()
    # Reject ISO-8601 style leftovers if any extractor returns them
    if text.startswith("PT"):
        return ""
    return text


def _format_duration(seconds: float | int) -> str:
    s = max(0, int(round(float(seconds))))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def _build_ydl_opts(
    output_dir: Path,
    *,
    quality: str = "best",
    audio_only: bool = False,
    proxy: str | None = None,
    progress_hooks: list | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    common: dict[str, Any] = {
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "keepvideo": False,
        "continuedl": True,
        "retries": 10,
        "fragment_retries": 10,
        "noprogress": True,
        **_proxy_opts(proxy),
    }
    if progress_hooks:
        common["progress_hooks"] = progress_hooks

    if audio_only:
        return {
            **common,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

    fmt = QUALITY_PRESETS.get(quality, quality)
    return {
        **common,
        "format": fmt,
        "merge_output_format": "mp4",
    }


def download(
    url: str,
    output_dir: Path,
    *,
    audio_only: bool = False,
    separate: bool = False,
    quality: str = "best",
    proxy: str | None = None,
    progress_callback: ProgressCallback | None = None,
    job: DownloadJob | None = None,
) -> Path | None:
    """
    Download a single YouTube URL.
    Returns the output file path when possible, else None.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    job = job or DownloadJob()

    if not ffmpeg_available() and not audio_only:
        # Still allow; yt-dlp may fall back to progressive formats
        pass

    if separate:
        # CLI-only advanced path; no progress UI in V1 main screen
        video_opts = {
            "outtmpl": str(output_dir / "%(title)s.video.%(ext)s"),
            "format": "bestvideo",
            "continuedl": True,
            **_proxy_opts(proxy),
        }
        audio_opts = {
            "outtmpl": str(output_dir / "%(title)s.audio.%(ext)s"),
            "format": "bestaudio/best",
            "continuedl": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            **_proxy_opts(proxy),
        }
        with yt_dlp.YoutubeDL(video_opts) as ydl:
            ydl.download([url])
        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            ydl.download([url])
        return None

    last_filename: list[str | None] = [None]

    def hook(d: dict[str, Any]) -> None:
        if job.cancel_flag.is_set():
            raise yt_dlp.utils.DownloadCancelled("用户取消下载")
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            pct = (downloaded / total * 100) if total else 0
            speed = d.get("speed") or 0
            eta = d.get("eta")
            if progress_callback:
                progress_callback(
                    {
                        "status": "downloading",
                        "percent": round(pct, 1),
                        "speed": speed,
                        "eta": eta,
                        "downloaded_bytes": downloaded,
                        "total_bytes": total,
                        "filename": d.get("filename"),
                    }
                )
        elif status == "finished":
            last_filename[0] = d.get("filename")
            if progress_callback:
                progress_callback(
                    {
                        "status": "processing",
                        "percent": 100,
                        "filename": d.get("filename"),
                    }
                )

    opts = _build_ydl_opts(
        output_dir,
        quality=quality,
        audio_only=audio_only,
        proxy=proxy,
        progress_hooks=[hook],
    )

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if job.cancel_flag.is_set():
                job.error = "已取消"
                return None
            # Resolve final path
            if info:
                prepared = ydl.prepare_filename(info)
                if audio_only:
                    prepared = str(Path(prepared).with_suffix(".mp3"))
                path = Path(prepared)
                if path.exists():
                    job.result_path = path
                    return path
            if last_filename[0]:
                p = Path(last_filename[0])
                if p.exists():
                    job.result_path = p
                    return p
            # Fallback: newest file in output_dir
            files = sorted(
                output_dir.glob("*"),
                key=lambda p: p.stat().st_mtime if p.is_file() else 0,
                reverse=True,
            )
            for f in files:
                if f.is_file() and f.suffix.lower() in {
                    ".mp4",
                    ".webm",
                    ".mkv",
                    ".mp3",
                    ".m4a",
                }:
                    job.result_path = f
                    return f
    except yt_dlp.utils.DownloadCancelled:
        job.error = "已取消"
        if progress_callback:
            progress_callback({"status": "cancelled", "percent": 0})
        return None
    except Exception as exc:
        job.error = str(exc)
        raise

    return job.result_path
