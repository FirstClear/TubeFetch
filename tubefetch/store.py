"""Local JSON settings and download history for TubeFetch."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


def app_data_dir() -> Path:
    path = Path.home() / ".tubefetch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_downloads_dir() -> Path:
    # Prefer project downloads/ when running from repo; else ~/.tubefetch/downloads
    project = Path(__file__).resolve().parents[1] / "downloads"
    if project.parent.exists():
        project.mkdir(parents=True, exist_ok=True)
        return project
    path = app_data_dir() / "downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


DEFAULT_SETTINGS: dict[str, Any] = {
    "download_dir": str(default_downloads_dir()),
    "quality": "1080",
    "proxy": "http://127.0.0.1:7890",
    "use_system_proxy": False,
    "accepted_terms": False,
    "language": "zh",
}


class Store:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or app_data_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.root / "settings.json"
        self.history_path = self.root / "history.json"

    def load_settings(self) -> dict[str, Any]:
        if not self.settings_path.exists():
            settings = dict(DEFAULT_SETTINGS)
            settings["download_dir"] = str(default_downloads_dir())
            self.save_settings(settings)
            return settings
        with self.settings_path.open(encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        return merged

    def save_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        merged = dict(DEFAULT_SETTINGS)
        merged.update(settings)
        with self.settings_path.open("w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        return merged

    def load_history(self) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        with self.history_path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []

    def save_history(self, items: list[dict[str, Any]]) -> None:
        with self.history_path.open("w", encoding="utf-8") as f:
            json.dump(items[:200], f, ensure_ascii=False, indent=2)

    def add_history(self, item: dict[str, Any]) -> dict[str, Any]:
        items = self.load_history()
        record = {
            "id": item.get("id") or str(uuid.uuid4()),
            "title": item.get("title") or "",
            "url": item.get("url") or "",
            "path": item.get("path") or "",
            "status": item.get("status") or "success",
            "error": item.get("error") or "",
            "created_at": item.get("created_at") or time.time(),
        }
        items.insert(0, record)
        self.save_history(items)
        return record

    def delete_history(self, record_id: str) -> bool:
        items = self.load_history()
        new_items = [x for x in items if x.get("id") != record_id]
        if len(new_items) == len(items):
            return False
        self.save_history(new_items)
        return True
