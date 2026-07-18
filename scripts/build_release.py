#!/usr/bin/env python3
"""Build a standalone TubeFetch release with bundled ffmpeg.

Usage:
  python scripts/fetch_ffmpeg.py
  pip install -r requirements-build.txt
  python scripts/build_release.py                         # current platform
  python scripts/build_release.py --platform darwin-arm64
  python scripts/build_release.py --platform win32-x64     # must run on Windows

Output: dist/TubeFetch-<platform>/  and  dist/TubeFetch-<platform>.zip

Windows note:
  PyInstaller cannot cross-compile. Build the .exe on Windows (or via
  GitHub Actions: .github/workflows/build-windows.yml).
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUPPORTED = {
    "darwin-arm64",
    "darwin-x64",
    "linux-x64",
    "linux-arm64",
    "win32-x64",
}


def platform_key() -> str:
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
    return f"{system}-{machine}"


def ensure_ffmpeg(plat: str) -> Path:
    ffmpeg_dir = ROOT / "vendor" / "ffmpeg" / plat
    exe = "ffmpeg.exe" if plat.startswith("win32") else "ffmpeg"
    if not (ffmpeg_dir / exe).is_file():
        print(f"未找到内置 ffmpeg ({plat})，正在下载…")
        subprocess.check_call(
            [sys.executable, str(ROOT / "scripts" / "fetch_ffmpeg.py"), "--platform", plat],
            cwd=ROOT,
        )
    if not (ffmpeg_dir / exe).is_file():
        raise SystemExit(f"ffmpeg 下载失败: {ffmpeg_dir}")
    return ffmpeg_dir


def darwin_ffmpeg_dirs() -> list[tuple[str, Path]]:
    """Fetch both Mac arches so the package works under native + Rosetta."""
    return [(key, ensure_ffmpeg(key)) for key in ("darwin-arm64", "darwin-x64")]


def run_pyinstaller(
    plat: str,
    ffmpeg_payload: list[tuple[str, Path]],
    *,
    console: bool = False,
) -> Path:
    try:
        import PyInstaller.__main__  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "缺少 PyInstaller。请先执行: pip install -r requirements-build.txt"
        ) from exc

    # Friendly exe name on Windows; keep platform tag in folder/zip name
    app_name = "TubeFetch" if plat.startswith("win32") else f"TubeFetch-{plat}"
    dist_folder = f"TubeFetch-{plat}"
    work = ROOT / "build" / "pyinstaller"
    dist = ROOT / "dist"
    work.mkdir(parents=True, exist_ok=True)
    dist.mkdir(parents=True, exist_ok=True)

    out_dir = dist / dist_folder
    if out_dir.exists():
        shutil.rmtree(out_dir)

    add_data = [
        f"{ROOT / 'tubefetch' / 'static'}{os.pathsep}tubefetch/static",
    ]
    primary: Path | None = None
    for key, ffmpeg_dir in ffmpeg_payload:
        if key == plat:
            primary = ffmpeg_dir
        is_win = key.startswith("win32")
        ffmpeg_bin = ffmpeg_dir / ("ffmpeg.exe" if is_win else "ffmpeg")
        ffprobe_bin = ffmpeg_dir / ("ffprobe.exe" if is_win else "ffprobe")
        add_data.append(f"{ffmpeg_bin}{os.pathsep}ffmpeg/{key}")
        add_data.append(f"{ffprobe_bin}{os.pathsep}ffmpeg/{key}")
        license_file = ffmpeg_dir / "LICENSE"
        if license_file.is_file():
            add_data.append(f"{license_file}{os.pathsep}ffmpeg/{key}")

    if primary is not None:
        is_win = plat.startswith("win32")
        add_data.append(
            f"{primary / ('ffmpeg.exe' if is_win else 'ffmpeg')}{os.pathsep}ffmpeg"
        )
        add_data.append(
            f"{primary / ('ffprobe.exe' if is_win else 'ffprobe')}{os.pathsep}ffmpeg"
        )

    args = [
        "--noconfirm",
        "--clean",
        "--name",
        app_name,
        "--onedir",
        f"--distpath={dist}",
        f"--workpath={work}",
        f"--specpath={work}",
        "--paths",
        str(ROOT),
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--collect-submodules=yt_dlp",
        "--collect-all=webview",
    ]

    if plat.startswith("win32"):
        args.append("--console" if console else "--windowed")
    else:
        args.append("--console")

    if plat.startswith("darwin"):
        args.extend(["--target-arch", "arm64" if plat.endswith("arm64") else "x86_64"])

    for item in add_data:
        args.extend(["--add-data", item])

    wrapper = work / "tubefetch_entry.py"
    wrapper.write_text(
        "from tubefetch.app import main\n\nif __name__ == '__main__':\n    main()\n",
        encoding="utf-8",
    )
    args.append(str(wrapper))

    print("运行 PyInstaller…")
    subprocess.check_call([sys.executable, "-m", "PyInstaller", *args], cwd=ROOT)

    # PyInstaller writes to dist/<app_name>/; normalize to dist/TubeFetch-<plat>/
    built = dist / app_name
    if built.is_dir() and built.resolve() != out_dir.resolve():
        if out_dir.exists():
            shutil.rmtree(out_dir)
        built.rename(out_dir)

    if not out_dir.is_dir():
        raise SystemExit(f"构建失败，未找到: {out_dir}")

    if plat.startswith("win32"):
        exe = out_dir / "TubeFetch.exe"
        if not exe.is_file():
            candidates = list(out_dir.rglob("TubeFetch.exe"))
            if not candidates:
                raise SystemExit("构建完成但未找到 TubeFetch.exe")
        print(f"Windows 入口: {out_dir / 'TubeFetch.exe'}")

    return out_dir


def zip_dir(src: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src.parent))
    print(f"已打包: {zip_path} ({zip_path.stat().st_size // (1024 * 1024)} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="打包 TubeFetch Release（含 ffmpeg）")
    parser.add_argument(
        "--platform",
        default="auto",
        help=f"目标平台 (auto|{'|'.join(sorted(SUPPORTED))})",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Windows 下保留控制台窗口（调试用）",
    )
    args = parser.parse_args()

    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    native = platform_key()
    plat = native if args.platform == "auto" else args.platform
    if plat not in SUPPORTED:
        raise SystemExit(f"不支持的平台: {plat}")

    host = platform.system().lower()
    if plat.startswith("win32") and host != "windows":
        raise SystemExit(
            "无法在当前系统交叉编译 Windows .exe。\n"
            "请任选其一:\n"
            "  1) 在 Windows 电脑上执行:\n"
            "       pip install -r requirements.txt -r requirements-build.txt\n"
            "       python scripts/build_release.py --platform win32-x64\n"
            "  2) 推送代码后用 GitHub Actions 构建 "
            "(.github/workflows/build-release.yml)\n"
        )
    if plat.startswith("darwin") and host != "darwin":
        raise SystemExit(f"无法在 {host} 上打包 macOS 应用，请在 Mac 上构建。")
    if plat.startswith("linux") and host != "linux":
        raise SystemExit(f"无法在 {host} 上打包 Linux 应用，请在 Linux 上构建。")

    py_arch = platform.machine().lower()
    want_x86 = plat.endswith("x64")
    is_arm_python = py_arch in {"arm64", "aarch64"}
    if plat.startswith("darwin") and want_x86 and is_arm_python:
        print(
            "警告: 当前 Python 是 arm64，却要打 darwin-x64 包。\n"
            "  可执行文件仍会是 arm64，Intel Mac 无法运行。\n"
            "  请在 Intel Mac 上构建，或用 Rosetta x86_64 Python:\n"
            "    arch -x86_64 /usr/local/bin/python3 scripts/build_release.py "
            "--platform darwin-x64\n"
        )

    print(f"平台: {plat}（本机 Python arch={py_arch}）")

    if plat.startswith("darwin"):
        ffmpeg_payload = darwin_ffmpeg_dirs()
        print("内置 ffmpeg:", ", ".join(k for k, _ in ffmpeg_payload))
    else:
        ffmpeg_payload = [(plat, ensure_ffmpeg(plat))]

    out_dir = run_pyinstaller(plat, ffmpeg_payload, console=args.console)

    zip_path = ROOT / "dist" / f"{out_dir.name}.zip"
    zip_dir(out_dir, zip_path)
    print("\n完成。发布时上传:")
    print(f"  {zip_path}")
    if plat.startswith("win32"):
        print("  用户解压后运行 TubeFetch.exe（需已安装 Edge WebView2，Win10/11 一般自带）")
    elif plat.startswith("darwin"):
        other = "darwin-x64" if plat == "darwin-arm64" else "darwin-arm64"
        print(f"  另一架构: python scripts/build_release.py --platform {other}")
    print("无需单独安装 ffmpeg / Python。")


if __name__ == "__main__":
    main()
