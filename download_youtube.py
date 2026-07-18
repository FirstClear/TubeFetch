#!/usr/bin/env python3
"""Download YouTube videos by URL using yt-dlp (CLI wrapper over yt_core)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yt_dlp
    from yt_core import QUALITY_PRESETS, download, ffmpeg_available
except ImportError as exc:
    print(f"依赖缺失: {exc}")
    print("请运行: pip install -r requirements.txt")
    print("建议使用 Python 3.10+，例如: /Users/*/miniconda3/bin/python")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="下载 YouTube 视频（默认最高清晰度）")
    parser.add_argument("url", nargs="?", help="YouTube 视频链接")
    parser.add_argument(
        "-o",
        "--output",
        default="downloads",
        help="保存目录（默认: downloads）",
    )
    parser.add_argument(
        "-a",
        "--audio",
        action="store_true",
        help="仅下载音频（转为 mp3）",
    )
    parser.add_argument(
        "-s",
        "--separate",
        action="store_true",
        help="视频和音频分开下载（音频自动转为 mp3）",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default="best",
        help="清晰度: best / 4k / 1080 / 720 / 480，或自定义 yt-dlp format 字符串",
    )
    parser.add_argument(
        "--proxy",
        default="",
        help="代理地址，如 http://127.0.0.1:7890",
    )
    args = parser.parse_args()

    url = args.url or input("请输入 YouTube 视频链接: ").strip()
    if not url:
        print("未提供链接，已退出。")
        sys.exit(1)

    if not ffmpeg_available():
        print("警告: 未检测到 ffmpeg。高清视频通常是音视频分离的，合并需要 ffmpeg。")
        print("安装方式: brew install ffmpeg  或  conda install -c conda-forge ffmpeg")

    fmt = QUALITY_PRESETS.get(args.quality, args.quality)
    print(f"开始下载: {url}")
    print(f"保存目录: {Path(args.output).resolve()}")
    if args.audio:
        print("模式: 仅音频")
    elif args.separate:
        print("模式: 音视频分离")
    else:
        print(f"清晰度: {args.quality} ({fmt})")

    try:
        path = download(
            url,
            Path(args.output),
            audio_only=args.audio,
            separate=args.separate,
            quality=args.quality,
            proxy=args.proxy or None,
        )
        if path:
            print(f"下载完成: {path}")
        else:
            print("下载完成。")
    except yt_dlp.utils.DownloadError as exc:
        print(f"下载失败: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已取消下载。")
        sys.exit(130)


if __name__ == "__main__":
    main()
