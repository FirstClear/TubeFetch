"""Resolve bundled / system ffmpeg for yt-dlp."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from functools import lru_cache
from pathlib import Path


def _machine_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    if machine in {"x86_64", "amd64", "x64"}:
        return "x64"
    return machine


def _platform_keys() -> list[str]:
    """Preferred platform folder names, native first then compatible fallbacks."""
    system = platform.system().lower()
    arch = _machine_arch()
    if system == "darwin":
        keys = [f"darwin-{arch}"]
        # Apple Silicon can run Intel binaries via Rosetta
        if arch == "arm64":
            keys.append("darwin-x64")
        return keys
    if system == "linux":
        keys = [f"linux-{arch}"]
        return keys
    if system == "windows":
        return ["win32-x64"]
    return [f"{system}-{arch}"]


def _exe_name(tool: str) -> str:
    return f"{tool}.exe" if platform.system().lower() == "windows" else tool


def _candidate_dirs() -> list[Path]:
    """Ordered search roots that may contain ffmpeg (+ ffprobe)."""
    dirs: list[Path] = []
    env = os.environ.get("TUBEFETCH_FFMPEG_DIR", "").strip()
    if env:
        dirs.append(Path(env))

    # PyInstaller: binaries next to the executable / in _MEIPASS
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base = Path(meipass)
            dirs.append(base / "ffmpeg")
            # Multi-arch layout: _internal/ffmpeg/darwin-arm64, darwin-x64, …
            for key in _platform_keys():
                dirs.append(base / "ffmpeg" / key)
            dirs.append(base)
        exe_dir = Path(sys.executable).resolve().parent
        dirs.append(exe_dir / "ffmpeg")
        dirs.append(exe_dir / "_internal" / "ffmpeg")
        for key in _platform_keys():
            dirs.append(exe_dir / "_internal" / "ffmpeg" / key)
            dirs.append(exe_dir / "ffmpeg" / key)
        dirs.append(exe_dir)
        resources = exe_dir.parent / "Resources" / "ffmpeg"
        dirs.append(resources)
        for key in _platform_keys():
            dirs.append(resources / key)

    # Source / editable install: <repo>/vendor/ffmpeg/<platform>
    here = Path(__file__).resolve().parent  # yt_core/
    root = here.parent
    vendor = root / "vendor" / "ffmpeg"
    for key in _platform_keys():
        dirs.append(vendor / key)
    dirs.append(vendor)

    dirs.append(here / "ffmpeg")
    return dirs


def _dir_has_ffmpeg(d: Path) -> bool:
    return (d / _exe_name("ffmpeg")).is_file()


@lru_cache(maxsize=1)
def get_ffmpeg_dir() -> Path | None:
    """Directory containing ffmpeg (and ideally ffprobe), or None."""
    for d in _candidate_dirs():
        if _dir_has_ffmpeg(d):
            return d
    which = shutil.which("ffmpeg")
    if which:
        return Path(which).resolve().parent
    return None


@lru_cache(maxsize=1)
def get_ffmpeg_exe() -> Path | None:
    d = get_ffmpeg_dir()
    if not d:
        return None
    path = d / _exe_name("ffmpeg")
    return path if path.is_file() else None


def ffmpeg_available() -> bool:
    return get_ffmpeg_exe() is not None


def ffmpeg_ydl_opts() -> dict:
    """yt-dlp options that point at our bundled ffmpeg when present."""
    d = get_ffmpeg_dir()
    if d is None:
        return {}
    return {"ffmpeg_location": str(d)}
