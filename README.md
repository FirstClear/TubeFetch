# TubeFetch

中文 | [English](#tubefetch-1)

面向个人创作者的本地 YouTube 单视频下载客户端（macOS 桌面 GUI / 浏览器）。

基于 [PRD](docs/PRD-youtube-downloader-client.md) 的 V1 实现。

## 功能

- 粘贴 YouTube / Shorts 链接 → 解析标题、简介、封面
- 选择清晰度：best / 4K / 1080 / 720 / 480 / 仅音频
- 实时进度、取消、失败后可重试
- 设置：保存目录、HTTP/SOCKS 代理（常见如 `http://127.0.0.1:7890`）
- 本地下载历史，可打开文件所在目录

## 架构

```
tubefetch/app.py          # 桌面窗口启动（pywebview）
tubefetch/server.py       # FastAPI 本地 API
tubefetch/store.py        # 设置与历史（~/.tubefetch/）
tubefetch/static/         # 前端界面
yt_core/                  # 与 CLI 共用的 yt-dlp 核心
vendor/ffmpeg/            # 内置静态 ffmpeg/ffprobe（fetch 脚本下载）
scripts/fetch_ffmpeg.py   # 下载 ffmpeg
scripts/build_release.py  # PyInstaller 打包（含 ffmpeg）
download_youtube.py       # 命令行入口（复用 yt_core）
```

## 环境要求

- Python 3.10+（推荐 3.13）
- ffmpeg：**Release 包已内置**；从源码运行时请先拉取静态二进制（见下）

## 安装

```bash
pip install -r requirements.txt

# 下载内置 ffmpeg/ffprobe 到 vendor/（macOS 会同时拉 arm64 + Intel x64）
python scripts/fetch_ffmpeg.py

# 也可改用系统 ffmpeg：brew install ffmpeg  或  conda install -c conda-forge ffmpeg
```

## 打包 Release（开箱即用）

```bash
pip install -r requirements-build.txt
python scripts/fetch_ffmpeg.py
# Apple Silicon
python scripts/build_release.py --platform darwin-arm64
# Intel Mac（需在 Intel 机器，或 Rosetta 下的 x86_64 Python）
python scripts/build_release.py --platform darwin-x64
```

### Windows `.exe`

**不能在 macOS 上交叉编译**，需在 Windows 本机或用 GitHub Actions：

```bat
REM 在 Windows 上
pip install -r requirements.txt -r requirements-build.txt
python scripts/fetch_ffmpeg.py --platform win32-x64
python scripts/build_release.py --platform win32-x64
```

产出 `dist/TubeFetch-win32-x64.zip`，解压后运行 `TubeFetch.exe`（已内置 ffmpeg）。  
桌面窗口依赖 Edge WebView2（Win10/11 通常已自带）。

用 GitHub Actions：仓库 Actions 里手动跑 **Build Windows**，或推送 `v*` 标签自动构建并挂到 Release。

产出 `dist/TubeFetch-darwin-arm64.zip` / `dist/TubeFetch-darwin-x64.zip`。  
macOS 包内会同时带上 **arm64 + x64** 两套 ffmpeg，运行时按 CPU 自动选择。  
应用本体需按架构分别打包（Python/PyInstaller 与目标 CPU 一致）。

解压后直接运行，**无需**再装 Python / ffmpeg。

## 启动

```bash
# 桌面窗口（推荐）
python -m tubefetch.app

# 仅用系统浏览器
python -m tubefetch.app --browser
```

默认地址：`http://127.0.0.1:8765/`

首次使用请打开「设置」，勾选合法使用承诺，并按需配置代理。

## 命令行下载

```bash
python download_youtube.py "https://www.youtube.com/watch?v=VIDEO_ID" -q 1080
python download_youtube.py "URL" -a          # 仅音频
```

## 请作者喝杯咖啡

如果觉得这个项目有用，可以请作者喝杯咖啡：

<p align="center">
  <img src="tubefetch/static/donate.png" alt="微信收款码" width="240" />
</p>

## 合规说明

仅供个人合法用途。请遵守 [YouTube 服务条款](https://www.youtube.com/t/terms) 与版权规定。本项目不提供绕过 DRM 或账号限制的能力。

---

# TubeFetch

[中文](#tubefetch) | English

A local single-video YouTube downloader for personal creators (macOS desktop GUI / browser).

V1 implementation based on the [PRD](docs/PRD-youtube-downloader-client.md).

## Features

- Paste a YouTube / Shorts URL → preview title, description, and thumbnail
- Quality options: best / 4K / 1080 / 720 / 480 / audio only
- Live progress, cancel, and retry on failure
- Settings: save directory, HTTP/SOCKS proxy (e.g. `http://127.0.0.1:7890`)
- Local download history with “open in Finder”

## Architecture

```
tubefetch/app.py          # Desktop launcher (pywebview)
tubefetch/server.py       # Local FastAPI server
tubefetch/store.py        # Settings & history (~/.tubefetch/)
tubefetch/static/         # Web UI
yt_core/                  # Shared yt-dlp core (CLI + GUI)
vendor/ffmpeg/            # Bundled static ffmpeg/ffprobe
scripts/fetch_ffmpeg.py   # Download ffmpeg
scripts/build_release.py  # PyInstaller release (includes ffmpeg)
download_youtube.py       # CLI entry (uses yt_core)
```

## Requirements

- Python 3.10+ (3.13 recommended)
- ffmpeg: **bundled in Release builds**; from source, fetch static binaries (below)

## Install

```bash
pip install -r requirements.txt

# Download bundled ffmpeg/ffprobe into vendor/ (macOS: arm64 + Intel x64)
python scripts/fetch_ffmpeg.py

# Or use a system ffmpeg: brew install ffmpeg  /  conda install -c conda-forge ffmpeg
```

## Build a Release (zero extra deps for end users)

```bash
pip install -r requirements-build.txt
python scripts/fetch_ffmpeg.py
python scripts/build_release.py --platform darwin-arm64   # Apple Silicon
python scripts/build_release.py --platform darwin-x64     # Intel (x86_64 Python)
```

### Windows `.exe`

Cannot cross-compile from macOS. Build on Windows or via GitHub Actions:

```bat
pip install -r requirements.txt -r requirements-build.txt
python scripts/fetch_ffmpeg.py --platform win32-x64
python scripts/build_release.py --platform win32-x64
```

Output: `dist/TubeFetch-win32-x64.zip` → run `TubeFetch.exe` (ffmpeg bundled).  
Needs Edge WebView2 (usually preinstalled on Win10/11).

Or run the **Build Windows** workflow / push a `v*` tag.

Produces `dist/TubeFetch-darwin-arm64.zip` / `dist/TubeFetch-darwin-x64.zip`.  
macOS builds embed **both** arm64 and x64 ffmpeg; the runtime picks by CPU.  
The app binary itself must be built with a matching Python arch.

Users unzip and run — no separate Python / ffmpeg install.

## Run

```bash
# Desktop window (recommended)
python -m tubefetch.app

# Browser only
python -m tubefetch.app --browser
```

Default URL: `http://127.0.0.1:8765/`

On first launch, open **Settings**, accept the personal-use notice, and configure a proxy if needed.

## CLI download

```bash
python download_youtube.py "https://www.youtube.com/watch?v=VIDEO_ID" -q 1080
python download_youtube.py "URL" -a          # audio only
```

## Buy the author a coffee

If you find this project useful, feel free to buy the author a coffee (WeChat Pay):

<p align="center">
  <img src="tubefetch/static/donate.png" alt="WeChat Pay QR code" width="240" />
</p>

## Compliance

For personal, lawful use only. Comply with the [YouTube Terms of Service](https://www.youtube.com/t/terms) and copyright laws. This project does not bypass DRM or account restrictions.
