#!/usr/bin/env python3
"""Launch TubeFetch desktop window (pywebview) or browser fallback."""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def find_free_port(preferred: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def run_server(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(
        "tubefetch.server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="TubeFetch — YouTube 下载客户端")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--browser",
        action="store_true",
        help="仅用系统浏览器打开（不启动桌面窗口）",
    )
    args = parser.parse_args()
    port = args.port if args.port else find_free_port()
    # If preferred port busy, pick free
    port = find_free_port(port)
    url = f"http://{args.host}:{port}/"

    thread = threading.Thread(target=run_server, args=(args.host, port), daemon=True)
    thread.start()

    # Wait until server is up
    for _ in range(50):
        try:
            with socket.create_connection((args.host, port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    else:
        print("服务启动失败")
        sys.exit(1)

    print(f"TubeFetch 已启动: {url}")
    print("仅供个人合法用途，请遵守 YouTube 条款与版权规定。")

    if args.browser:
        webbrowser.open(url)
        print("按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n已退出")
        return

    try:
        import webview
    except ImportError:
        print("未安装 pywebview，改用浏览器模式。可执行: pip install pywebview")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n已退出")
        return

    webview.create_window(
        "TubeFetch",
        url,
        width=980,
        height=820,
        min_size=(720, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
