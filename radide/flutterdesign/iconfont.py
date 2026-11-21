"""Material icons for the Flutter designer: every ``Icons.<name>`` of the installed Flutter SDK.

The names and code points are read from the SDK's ``packages/flutter/lib/src/material/icons.dart`` and the
glyphs are drawn with the SDK's own ``MaterialIcons-Regular.otf`` (Apache License 2.0, Google), so the icon picker
and the Qt preview show exactly the icons Flutter will draw. Nothing is copied into RAD IDE: without a Flutter SDK
the small bundled SVG set of ``radide.mobile.material_icons`` is used.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_RX = re.compile(r"static const IconData (\w+)\s*=\s*IconData\(\s*0x([0-9a-fA-F]+)")
_family: str | None = None
_family_tried = False


@lru_cache(maxsize=1)
def _sdk() -> Path | None:
    try:
        from ..languages.flutter import flutter_root
        root = flutter_root()
    except Exception:  # noqa: BLE001
        root = ""
    for r in ([root] if root else []) + [r"C:\flutter", r"C:\src\flutter", str(Path.home() / "flutter")]:
        p = Path(r)
        if (p / "packages" / "flutter" / "lib" / "src" / "material" / "icons.dart").is_file():
            return p
    return None


@lru_cache(maxsize=1)
def codepoints() -> dict[str, int]:
    """Icons.<name> -> code point (empty without a Flutter SDK)."""
    sdk = _sdk()
    if sdk is None:
        return {}
    try:
        text = (sdk / "packages" / "flutter" / "lib" / "src" / "material" / "icons.dart").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return {}
    return {m.group(1): int(m.group(2), 16) for m in _RX.finditer(text)}


def icon_names(styles: bool = True) -> list[str]:
    """Every Material icon name; ``styles=False`` hides the _outlined / _rounded / _sharp variants."""
    names = list(codepoints())
    if not names:
        from ..mobile.material_icons import icon_names as small
        names = list(small())
    if not styles:
        names = [n for n in names if not n.endswith(("_outlined", "_rounded", "_sharp"))]
    return sorted(names)


def font_family() -> str | None:
    """The Qt family of the Material icons font (loaded once from the Flutter SDK), None when missing."""
    global _family, _family_tried
    if _family_tried:
        return _family
    _family_tried = True
    sdk = _sdk()
    if sdk is None:
        return None
    from PyQt6.QtGui import QFontDatabase
    folder = sdk / "bin" / "cache" / "artifacts" / "material_fonts"
    for name in ("materialicons-regular.otf", "MaterialIcons-Regular.otf"):
        p = folder / name
        if p.is_file():
            fid = QFontDatabase.addApplicationFont(str(p))
            fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            if fams:
                _family = fams[0]
                return _family
    return None


def bare(name: str) -> str:
    """'Icons.email_outlined' -> 'email_outlined' (CupertinoIcons.* -> a close Material name)."""
    n = str(name or "")
    if n.startswith("Icons."):
        return n[6:]
    if n.startswith("CupertinoIcons."):
        n = n[15:]
        return {"home": "home", "search": "search", "person": "person", "settings": "settings",
                "back": "arrow_back_ios", "forward": "arrow_forward_ios", "add": "add", "heart": "favorite_border",
                "heart_fill": "favorite", "mail": "mail_outline", "bell": "notifications_none",
                "star": "star_border", "star_fill": "star", "trash": "delete_outline",
                "chat_bubble": "chat_bubble_outline", "info": "info_outline", "lock": "lock_outline",
                "share": "ios_share", "camera": "photo_camera", "cart": "shopping_cart"}.get(n, n)
    return n


def draw(p, rect, name: str, color) -> None:
    """Paint an icon into a QRectF with a QColor (or '#hex')."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QFont
    col = color if isinstance(color, QColor) else QColor(str(color))
    n = bare(name)
    cp = codepoints().get(n)
    fam = font_family() if cp is not None else None
    if fam:
        f = QFont(fam)
        f.setPixelSize(max(1, int(min(rect.width(), rect.height()))))
        f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        p.save()
        p.setFont(f)
        p.setPen(col)
        p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), chr(cp))
        p.restore()
        return
    from ..mobile import material_icons as mi
    key = mi.resolve(re.sub(r"_(outlined|rounded|sharp|outline)$", "", n), "")
    if key:
        mi.draw_icon(p, rect, key, col.name())
        return
    p.save()                                    # unknown: a rounded square with the first letter
    p.setPen(col)
    p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 3, 3)
    f = QFont("Segoe UI")
    f.setPixelSize(max(6, int(rect.height() * 0.5)))
    p.setFont(f)
    p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), (n[:1] or "?").upper())
    p.restore()


def pixmap(name: str, size: int = 20, color="#1D1B20"):
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QPainter, QPixmap
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    draw(p, QRectF(0, 0, size, size), name, color)
    p.end()
    return pm


def icon(name: str, size: int = 20, color="#1D1B20"):
    from PyQt6.QtGui import QIcon
    return QIcon(pixmap(name, size, color))
