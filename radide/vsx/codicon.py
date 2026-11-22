"""VS Code product icons ("codicons", ThemeIcon ids such as ``refresh``, ``$(add)``) as QIcons.

The bundled Monaco (radide/web/monaco, MIT) ships codicon.ttf and registers every icon name with its code
point in editor.main.js (``register("refresh", 60215)``): both are read once; icons are painted with the
current theme's foreground colour."""
from __future__ import annotations

import re
from pathlib import Path

_WEB = Path(__file__).resolve().parents[1] / "web" / "monaco" / "vs"
_MAP: dict[str, int] | None = None
_FAMILY: str | None = None
_CACHE: dict = {}
ALIASES = {"gear": "settings-gear", "repo-sync": "sync", "remove-close": "close"}


def names() -> dict[str, int]:
    global _MAP
    if _MAP is None:
        _MAP = {}
        try:
            text = (_WEB / "editor" / "editor.main.js").read_text("utf-8", errors="ignore")
            for n, cp in re.findall(r'"([a-z0-9-]+)",(\d{5})\)', text):
                _MAP.setdefault(n, int(cp))
        except OSError:
            pass
    return _MAP


def _family() -> str:
    global _FAMILY
    if _FAMILY is None:
        _FAMILY = ""
        try:
            from PyQt6.QtGui import QFontDatabase
            fid = QFontDatabase.addApplicationFont(str(_WEB / "base" / "browser" / "ui" / "codicons" / "codicon"
                                                       / "codicon.ttf"))
            fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            _FAMILY = fams[0] if fams else ""
        except Exception:  # noqa: BLE001
            _FAMILY = ""
    return _FAMILY


def _fg() -> str:
    try:
        from PyQt6.QtWidgets import QApplication
        return QApplication.palette().windowText().color().name()
    except Exception:  # noqa: BLE001
        return "#c5c5c5"


def icon(name: str, color: str | None = None, size: int = 16):
    """QIcon of a codicon (``refresh``, ``sync~spin`` -> ``sync``), or None when unknown."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
    n = (name or "").split("~")[0]
    n = ALIASES.get(n, n)
    cp = names().get(n)
    fam = _family()
    if cp is None or not fam:
        return None
    col = color or _fg()
    key = (n, col, size)
    if key in _CACHE:
        return _CACHE[key]
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    f = QFont(fam)
    f.setPixelSize(size * 2 - 4)
    p.setFont(f)
    p.setPen(QColor(col))
    p.drawText(QRectF(0, 0, size * 2, size * 2), int(Qt.AlignmentFlag.AlignCenter), chr(cp))
    p.end()
    ic = QIcon(pm)
    _CACHE[key] = ic
    return ic


def strip(text: str) -> tuple[str, str | None]:
    """'$(refresh) Reload' -> ('Reload', 'refresh'): the label without icons and the first icon name."""
    m = re.search(r"\$\(([a-z0-9\-~]+)\)", text or "")
    return re.sub(r"\$\([a-z0-9\-~]+\)\s*", "", text or "").strip(), (m.group(1) if m else None)


__all__ = ["icon", "names", "strip"]
