"""TubeFetch local FastAPI backend."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tubefetch.store import Store
from yt_core import (
    DownloadJob,
    QUALITY_PRESETS,
    download,
    extract_metadata,
    ffmpeg_available,
    is_youtube_url,
)

STATIC_DIR = Path(__file__).parent / "static"
store = Store()

app = FastAPI(title="TubeFetch", version="1.0.0")

_tasks: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


class ParseRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    quality: str = "1080"
    audio_only: bool = False
    download_dir: str | None = None
    proxy: str | None = None
    title: str = ""


class SettingsUpdate(BaseModel):
    download_dir: str | None = None
    quality: str | None = None
    proxy: str | None = None
    use_system_proxy: bool | None = None
    accepted_terms: bool | None = None
    language: str | None = None


class HistoryDelete(BaseModel):
    id: str
    delete_file: bool = False


class OpenPathRequest(BaseModel):
    path: str


def _msg(key: str) -> str:
    lang = store.load_settings().get("language") or "zh"
    messages = {
        "invalid_url": {
            "zh": "请输入有效的 YouTube 视频 / Shorts 链接",
            "en": "Please enter a valid YouTube video / Shorts URL",
        },
        "parse_failed": {
            "zh": "解析失败: {err}",
            "en": "Parse failed: {err}",
        },
        "accept_terms": {
            "zh": "请先在设置中确认合法使用承诺",
            "en": "Please accept the terms in Settings first",
        },
        "cancelled": {"zh": "已取消", "en": "Cancelled"},
        "task_not_found": {"zh": "任务不存在", "en": "Task not found"},
        "path_missing": {"zh": "路径不存在", "en": "Path does not exist"},
        "history_missing": {"zh": "记录不存在", "en": "Record not found"},
        "open_failed": {"zh": "无法打开: {err}", "en": "Cannot open: {err}"},
    }
    entry = messages.get(key, {})
    return entry.get(lang) or entry.get("zh") or key


def _effective_proxy(settings: dict[str, Any], override: str | None = None) -> str | None:
    if override is not None:
        return override.strip() or None
    if settings.get("use_system_proxy"):
        return None
    proxy = (settings.get("proxy") or "").strip()
    return proxy or None


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "ffmpeg": ffmpeg_available(),
        "qualities": list(QUALITY_PRESETS.keys()) + ["audio"],
    }


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    return store.load_settings()


@app.put("/api/settings")
def put_settings(body: SettingsUpdate) -> dict[str, Any]:
    current = store.load_settings()
    data = body.model_dump(exclude_none=True)
    if "language" in data and data["language"] not in ("zh", "en"):
        raise HTTPException(400, "language must be zh or en")
    current.update(data)
    return store.save_settings(current)


@app.post("/api/parse")
def parse_video(body: ParseRequest) -> dict[str, Any]:
    url = body.url.strip()
    if not is_youtube_url(url):
        raise HTTPException(400, _msg("invalid_url"))
    settings = store.load_settings()
    proxy = _effective_proxy(settings)
    try:
        meta = extract_metadata(url, proxy=proxy)
        return {"ok": True, "ffmpeg": ffmpeg_available(), "video": meta}
    except Exception as exc:
        raise HTTPException(400, _msg("parse_failed").format(err=exc)) from exc


def _run_download(task_id: str, req: DownloadRequest) -> None:
    settings = store.load_settings()
    output_dir = Path(req.download_dir or settings["download_dir"])
    proxy = _effective_proxy(settings, req.proxy)
    quality = req.quality if req.quality != "audio" else "best"
    audio_only = req.audio_only or req.quality == "audio"
    job = DownloadJob()

    with _lock:
        _tasks[task_id]["job"] = job
        _tasks[task_id]["status"] = "downloading"

    def on_progress(info: dict[str, Any]) -> None:
        with _lock:
            t = _tasks.get(task_id)
            if not t:
                return
            t["progress"] = info
            if info.get("status") == "cancelled":
                t["status"] = "cancelled"

    try:
        path = download(
            req.url.strip(),
            output_dir,
            audio_only=audio_only,
            quality=quality,
            proxy=proxy,
            progress_callback=on_progress,
            job=job,
        )
        with _lock:
            t = _tasks[task_id]
            if job.cancel_flag.is_set() or t.get("status") == "cancelled":
                t["status"] = "cancelled"
                t["error"] = _msg("cancelled")
                store.add_history(
                    {
                        "title": req.title or req.url,
                        "url": req.url,
                        "path": "",
                        "status": "cancelled",
                    }
                )
            else:
                t["status"] = "success"
                t["path"] = str(path) if path else ""
                t["progress"] = {"status": "finished", "percent": 100}
                store.add_history(
                    {
                        "title": req.title or (path.name if path else req.url),
                        "url": req.url,
                        "path": str(path) if path else "",
                        "status": "success",
                    }
                )
    except Exception as exc:
        with _lock:
            _tasks[task_id]["status"] = "failed"
            _tasks[task_id]["error"] = str(exc)
            _tasks[task_id]["progress"] = {"status": "failed", "percent": 0}
        store.add_history(
            {
                "title": req.title or req.url,
                "url": req.url,
                "path": "",
                "status": "failed",
                "error": str(exc),
            }
        )


@app.post("/api/download")
def start_download(body: DownloadRequest) -> dict[str, Any]:
    url = body.url.strip()
    if not is_youtube_url(url):
        raise HTTPException(400, _msg("invalid_url"))
    settings = store.load_settings()
    if not settings.get("accepted_terms"):
        raise HTTPException(400, _msg("accept_terms"))

    task_id = str(uuid.uuid4())
    with _lock:
        _tasks[task_id] = {
            "id": task_id,
            "status": "queued",
            "progress": {"percent": 0, "status": "queued"},
            "path": "",
            "error": "",
            "url": url,
            "title": body.title,
            "created_at": time.time(),
        }

    thread = threading.Thread(target=_run_download, args=(task_id, body), daemon=True)
    thread.start()
    return {"ok": True, "task_id": task_id, "ffmpeg": ffmpeg_available()}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            raise HTTPException(404, _msg("task_not_found"))
        return {
            "id": task["id"],
            "status": task["status"],
            "progress": task.get("progress") or {},
            "path": task.get("path") or "",
            "error": task.get("error") or "",
            "title": task.get("title") or "",
            "url": task.get("url") or "",
        }


@app.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str) -> dict[str, Any]:
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            raise HTTPException(404, _msg("task_not_found"))
        job: DownloadJob | None = task.get("job")
        if job:
            job.cancel_flag.set()
        task["status"] = "cancelled"
        task["error"] = _msg("cancelled")
    return {"ok": True}


@app.get("/api/history")
def history() -> dict[str, Any]:
    return {"items": store.load_history()}


@app.post("/api/history/delete")
def history_delete(body: HistoryDelete) -> dict[str, Any]:
    items = store.load_history()
    target = next((x for x in items if x.get("id") == body.id), None)
    if not target:
        raise HTTPException(404, _msg("history_missing"))
    if body.delete_file and target.get("path"):
        p = Path(target["path"])
        if p.exists() and p.is_file():
            p.unlink()
    ok = store.delete_history(body.id)
    return {"ok": ok}


@app.post("/api/open-path")
def open_path(body: OpenPathRequest) -> dict[str, Any]:
    path = Path(body.path)
    if not path.exists():
        raise HTTPException(404, _msg("path_missing"))
    target = str(path if path.is_dir() else path.parent)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", target])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", target])
        else:
            subprocess.Popen(["xdg-open", target])
    except Exception as exc:
        raise HTTPException(500, _msg("open_failed").format(err=exc)) from exc
    return {"ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def create_app() -> FastAPI:
    return app
