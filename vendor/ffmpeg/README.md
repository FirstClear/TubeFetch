# Bundled FFmpeg

Static `ffmpeg` / `ffprobe` binaries live here, one folder per platform:

```
vendor/ffmpeg/darwin-arm64/
vendor/ffmpeg/darwin-x64/
…
```

Download for the current machine (on macOS this fetches **both** arm64 and Intel x64):

```bash
python scripts/fetch_ffmpeg.py
```

macOS only:

```bash
python scripts/fetch_ffmpeg.py --macos
```

All platforms (for CI multi-arch builds):

```bash
python scripts/fetch_ffmpeg.py --all
```

Source: [eugeneware/ffmpeg-static](https://github.com/eugeneware/ffmpeg-static) (FFmpeg 6.x). See each platform folder’s `LICENSE`.

Runtime resolution order (see `yt_core/ffmpeg_util.py`):

1. `TUBEFETCH_FFMPEG_DIR`
2. PyInstaller bundle (`…/ffmpeg/` or `…/ffmpeg/<platform>/`)
3. This `vendor/ffmpeg/<platform>/` tree (native arch first; on Apple Silicon, Intel x64 is a Rosetta fallback)
4. System `PATH`
