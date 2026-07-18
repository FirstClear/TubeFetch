#!/usr/bin/env python3
"""Download static ffmpeg/ffprobe into vendor/ffmpeg/<platform>/ for bundling."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import platform
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

from stdio_util import configure_stdio

configure_stdio()

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "ffmpeg"

# eugeneware/ffmpeg-static b6.1.1 (FFmpeg 6.1.1) — static binaries + LICENSE
RELEASE = "b6.1.1"
BASE = f"https://github.com/eugeneware/ffmpeg-static/releases/download/{RELEASE}"

# Map our platform key -> asset name prefix used by ffmpeg-static
PLATFORM_ASSETS = {
    "darwin-arm64": "darwin-arm64",
    "darwin-x64": "darwin-x64",
    "linux-x64": "linux-x64",
    "linux-arm64": "linux-arm64",
    "win32-x64": "win32-x64",
}


def detect_platform() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        return f"darwin-{arch}"
    if system == "linux":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        return f"linux-{arch}"
    if system == "windows":
        return "win32-x64"
    raise SystemExit(f"不支持的平台: {system} {machine}")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  下载: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "TubeFetch-fetch-ffmpeg/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def _gunzip(src: Path, dest: Path) -> None:
    with gzip.open(src, "rb") as fin, open(dest, "wb") as fout:
        shutil.copyfileobj(fin, fout)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_platform(plat: str, *, force: bool = False) -> Path:
    if plat not in PLATFORM_ASSETS:
        raise SystemExit(f"未知平台 key: {plat}。可选: {', '.join(PLATFORM_ASSETS)}")

    asset = PLATFORM_ASSETS[plat]
    out_dir = VENDOR / plat
    is_win = plat.startswith("win32")
    ffmpeg_name = "ffmpeg.exe" if is_win else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if is_win else "ffprobe"
    ffmpeg_bin = out_dir / ffmpeg_name
    ffprobe_bin = out_dir / ffprobe_name

    if ffmpeg_bin.is_file() and ffprobe_bin.is_file() and not force:
        print(f"已存在，跳过: {out_dir}")
        return out_dir

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tubefetch-ffmpeg-") as tmp:
        tmp_path = Path(tmp)
        for tool in ("ffmpeg", "ffprobe"):
            gz_name = f"{tool}-{asset}.gz"
            gz_path = tmp_path / gz_name
            _download(f"{BASE}/{gz_name}", gz_path)
            target = out_dir / (f"{tool}.exe" if is_win else tool)
            _gunzip(gz_path, target)
            target.chmod(0o755)
            print(f"  写入: {target} ({target.stat().st_size // (1024 * 1024)} MB, sha256={_sha256(target)[:12]}…)")

        license_url = f"{BASE}/{asset}.LICENSE"
        license_dest = out_dir / "LICENSE"
        try:
            _download(license_url, license_dest)
        except Exception as exc:  # noqa: BLE001 — best-effort license copy
            print(f"  警告: 未能下载 LICENSE ({exc})")

    meta = out_dir / "VERSION.txt"
    meta.write_text(
        f"source=eugeneware/ffmpeg-static\nrelease={RELEASE}\nplatform={plat}\n",
        encoding="utf-8",
    )
    print(f"完成: {out_dir}")
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="下载静态 ffmpeg/ffprobe 到 vendor/")
    parser.add_argument(
        "--platform",
        default="auto",
        help=f"目标平台 (auto|macos|{'|'.join(PLATFORM_ASSETS)})；auto 在 macOS 上下载 arm64+x64",
    )
    parser.add_argument("--all", action="store_true", help="下载所有支持的平台")
    parser.add_argument(
        "--macos",
        action="store_true",
        help="下载 macOS arm64 + Intel x64（与 --platform macos 相同）",
    )
    parser.add_argument("--force", action="store_true", help="强制重新下载")
    args = parser.parse_args()

    if args.all:
        plats = list(PLATFORM_ASSETS)
    elif args.macos or args.platform == "macos":
        plats = ["darwin-arm64", "darwin-x64"]
    elif args.platform == "auto":
        # On macOS fetch both arches so Apple Silicon / Intel both work from source
        if platform.system().lower() == "darwin":
            plats = ["darwin-arm64", "darwin-x64"]
        else:
            plats = [detect_platform()]
    else:
        plats = [args.platform]

    print(f"输出目录: {VENDOR}")
    for plat in plats:
        print(f"\n== {plat} ==")
        fetch_platform(plat, force=args.force)


if __name__ == "__main__":
    main()
