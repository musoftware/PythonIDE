"""Start QtWebEngine + Monaco in the background right after the IDE opens, so the
first code file opens instantly (Chromium's first start takes a few seconds)."""
from __future__ import annotations

from PyQt6.QtCore import QTimer


def install(win) -> None:
    from ..editor import use_monaco
    if not use_monaco():
        return

    def warm():
        try:
            from pathlib import Path

            from ..languages import get_plugin
            from ..monaco_editor import MonacoEditor
            ed = MonacoEditor(get_plugin("python-tk"), Path("_warmup.py"))
            ed.resize(10, 10)
            ed.hide()
            win._monaco_warm = ed          # kept alive: the engine and the page cache stay warm
        except Exception:  # noqa: BLE001 - warm-up is optional
            pass
    QTimer.singleShot(300, warm)
