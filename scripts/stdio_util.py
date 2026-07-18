"""Shared helpers for packaging scripts (Windows-safe console I/O)."""

from __future__ import annotations

import sys


def configure_stdio() -> None:
    """Avoid UnicodeEncodeError on Windows consoles (cp1252, etc.)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
