"""VS Code file icon themes (``contributes.iconThemes``: Material Icon Theme, vscode-icons, Seti ...)
-> Solution Explorer file / folder icons.

An icon theme JSON has ``iconDefinitions`` (id -> {"iconPath": svg/png} or a font glyph {"fontCharacter",
"fontColor", "fontId"}), ``fonts``, the defaults ``file`` / ``folder`` / ``folderExpanded`` / ``rootFolder``,
the maps ``fileExtensions`` / ``fileNames`` / ``folderNames`` / ``folderNamesExpanded`` / ``languageIds`` and
``light`` / ``highContrast`` overrides. ``IconTheme.icon_for(name, is_dir, expanded)`` resolves like VS Code:
file name, then the longest extension ("spec.ts" before "ts"), then the language, then the default.

The active theme is the QSettings value ``vsx/iconTheme`` ("<ext id>/<theme id>", "none" = off). While it
was never chosen, a newly installed icon theme is used (like Material's "activate" prompt).
radide.features.solution_ui.FILE_ICON_PROVIDER is set to ``provider``."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .contrib_common import enabled_extensions, ext_file, read_jsonc

SETTING = "vsx/iconTheme"


@dataclass
class IconThemeInfo:
    ext_id: str
    theme_id: str            # "<ext id>/<id>"
    label: str
    path: Path


@dataclass
class IconTheme:
    info: IconThemeInfo
    data: dict = field(default_factory=dict)
    _cache: dict = field(default_factory=dict)
    _fonts: dict = field(default_factory=dict)       # font id -> (family, size factor) or None

    @classmethod
    def load(cls, info: IconThemeInfo) -> "IconTheme | None":
        data = read_jsonc(info.path, None)
        if not isinstance(data, dict) or not isinstance(data.get("iconDefinitions"), dict):
            return None
        return cls(info, data)

    # ------------------------------------------------------------------ resolution
    def _maps(self, light: bool) -> list[dict]:
        """The override section first (light / highContrast), then the main one."""
        out = []
        if light and isinstance(self.data.get("light"), dict):
            out.append(self.data["light"])
        out.append(self.data)
        return out

    def definition_for(self, name: str, is_dir: bool = False, expanded: bool = False, root: bool = False,
                       language: str | None = None, strict: bool = False, light: bool = False) -> str | None:
        low = name.lower()
        maps = self._maps(light)
        if is_dir:
            keys = (["rootFolderNamesExpanded", "folderNamesExpanded"] if expanded else []) + \
                   (["rootFolderNames"] if root else []) + (["folderNamesExpanded"] if expanded else []) + ["folderNames"]
            for key in keys:
                for m in maps:
                    d = m.get(key)
                    if isinstance(d, dict) and low in d:
                        return d[low]
            if strict:
                return None
            defaults = (["rootFolderExpanded"] if root and expanded else []) + (["rootFolder"] if root else []) + \
                       (["folderExpanded"] if expanded else []) + ["folder"]
            for key in defaults:
                for m in maps:
                    if isinstance(m.get(key), str):
                        return m[key]
            return None
        for m in maps:
            d = m.get("fileNames")
            if isinstance(d, dict):
                if low in d:
                    return d[low]
                if name in d:
                    return d[name]
        parts = low.split(".")
        for i in range(1, len(parts)):               # "a.spec.ts": "spec.ts" then "ts"
            ext = ".".join(parts[i:])
            for m in maps:
                d = m.get("fileExtensions")
                if isinstance(d, dict) and ext in d:
                    return d[ext]
        if language:
            for m in maps:
                d = m.get("languageIds")
                if isinstance(d, dict) and language in d:
                    return d[language]
        if strict:
            return None
        for m in maps:
            if isinstance(m.get("file"), str):
                return m["file"]
        return None

    def icon_for(self, name: str, is_dir: bool = False, expanded: bool = False, root: bool = False,
                 strict: bool = False):
        light = _light_theme()
        lang = None if is_dir else _language_of(name)
        did = self.definition_for(name, is_dir, expanded, root, lang, strict, light)
        if did is None:
            return None
        return self.icon(did)

    # ------------------------------------------------------------------ rendering
    def icon(self, did: str):
        if did in self._cache:
            return self._cache[did]
        ic = None
        d = (self.data.get("iconDefinitions") or {}).get(did)
        if isinstance(d, dict):
            try:
                if isinstance(d.get("iconPath"), str):
                    p = (self.info.path.parent / d["iconPath"]).resolve()
                    if p.is_file():
                        ic = _file_icon(p)
                elif isinstance(d.get("fontCharacter"), str):
                    ic = self._glyph_icon(d)
            except Exception:  # noqa: BLE001 - a broken icon is "no icon"
                ic = None
        self._cache[did] = ic
        return ic

    def _font(self, font_id: str | None):
        fonts = [f for f in self.data.get("fonts") or [] if isinstance(f, dict)]
        if not fonts:
            return None
        f = next((x for x in fonts if x.get("id") == font_id), fonts[0])
        key = f.get("id") or ""
        if key in self._fonts:
            return self._fonts[key]
        res = None
        from PyQt6.QtGui import QFontDatabase
        for src in f.get("src") or []:
            if not isinstance(src, dict) or not isinstance(src.get("path"), str):
                continue
            p = (self.info.path.parent / src["path"]).resolve()
            if not p.is_file():
                continue
            fid = QFontDatabase.addApplicationFont(str(p))
            fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            if fams:
                size = 1.0
                s = str(f.get("size") or "")
                if s.endswith("%"):
                    try:
                        size = float(s[:-1]) / 100
                    except ValueError:
                        size = 1.0
                res = (fams[0], size)
                break
        self._fonts[key] = res
        return res

    def _glyph_icon(self, d: dict):
        from PyQt6.QtCore import QRectF, Qt
        from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
        font = self._font(d.get("fontId"))
        if font is None:
            return None
        ch = d["fontCharacter"]
        if ch.startswith("\\"):
            try:
                ch = chr(int(ch[1:], 16))
            except ValueError:
                return None
        icon = QIcon()
        for px in (16, 32):
            pm = QPixmap(px, px)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            f = QFont(font[0])
            f.setPixelSize(max(6, int(px * 0.85 * font[1])))
            p.setFont(f)
            p.setPen(QColor(d.get("fontColor") or "#8A8A8A"))
            p.drawText(QRectF(0, 0, px, px), int(Qt.AlignmentFlag.AlignCenter), ch)
            p.end()
            icon.addPixmap(pm)
        return icon


def _file_icon(p: Path):
    from PyQt6.QtCore import QSize, Qt
    from PyQt6.QtGui import QIcon, QPainter, QPixmap
    if p.suffix.lower() != ".svg":
        return QIcon(str(p))
    # render the SVG once at 16 and 32 px (a QIcon(svg) re-renders on every paint)
    try:
        from PyQt6.QtSvg import QSvgRenderer
    except Exception:  # noqa: BLE001 - no QtSvg: let the image plugin try
        return QIcon(str(p))
    r = QSvgRenderer(str(p))
    if not r.isValid():
        return None
    icon = QIcon()
    for px in (16, 20, 32):
        pm = QPixmap(QSize(px, px))
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        r.render(painter)
        painter.end()
        icon.addPixmap(pm)
    return icon


def _light_theme() -> bool:
    try:
        from .. import theme
        return not theme.is_dark()
    except Exception:  # noqa: BLE001
        return False


def _language_of(name: str) -> str | None:
    """The VS Code language id of a file name (for languageIds)."""
    try:
        from .contrib_languages import MONACO_TO_VSCODE, registry
        lang = registry().language_for_file(name)
        if lang:
            return lang
        from .. import monaco_editor as me
        m = me.MONACO_FILENAMES.get(name.lower()) or me.MONACO_LANG.get(Path(name).suffix.lower())
        if m:
            alts = [a for a in MONACO_TO_VSCODE.get(m, []) if a != m]
            return alts[0] if alts and m == "shell" else m       # Monaco "shell" is VS Code "shellscript"
    except Exception:  # noqa: BLE001
        return None
    return None


# ============================================================================ the active theme
_themes: list[IconThemeInfo] = []
_active: IconTheme | None = None


def collect(extensions=None) -> list[IconThemeInfo]:
    out = []
    for ext in (enabled_extensions() if extensions is None else extensions):
        for c in ext.contributes_list("iconThemes"):
            if not isinstance(c, dict) or not isinstance(c.get("path"), str):
                continue
            p = ext_file(ext, c["path"])
            if p is None:
                continue
            tid = str(c.get("id") or c.get("label") or p.stem)
            out.append(IconThemeInfo(ext.id, f"{ext.id}/{tid}", str(c.get("label") or tid), p))
    return out


def available() -> list[IconThemeInfo]:
    return list(_themes)


def _settings():
    try:
        from ..monaco_editor import _settings as s
        return s()
    except Exception:  # noqa: BLE001
        from PyQt6.QtCore import QSettings
        return QSettings("RADIDE", "RAD IDE")


def chosen() -> str:
    """The setting: "<ext id>/<id>", "none", or "" (never chosen)."""
    try:
        return str(_settings().value(SETTING, "") or "")
    except Exception:  # noqa: BLE001
        return ""


def choose(theme_id: str) -> None:
    """Pick the icon theme ("none" = the IDE's own icons) and load it."""
    _settings().setValue(SETTING, theme_id or "none")
    refresh()


def refresh(extensions=None) -> IconTheme | None:
    """Re-read the installed icon themes and load the active one."""
    global _themes, _active
    _themes = collect(extensions)
    want = chosen()
    info = None
    if want and want != "none":
        info = next((t for t in _themes if t.theme_id == want), None)
    if info is None and not want and _themes:
        info = _themes[0]                       # never chosen: a freshly installed icon theme is used
    if _active is not None and info is not None and _active.info.theme_id == info.theme_id \
            and _active.info.path == info.path:
        return _active
    _active = IconTheme.load(info) if info is not None else None
    return _active


def active() -> IconTheme | None:
    return _active


def provider(name: str, is_dir: bool = False, expanded: bool = False, root: bool = False, strict: bool = False):
    """FILE_ICON_PROVIDER for Solution Explorer: a QIcon or None (= keep the IDE's own icon)."""
    t = _active
    if t is None:
        return None
    return t.icon_for(name, is_dir, expanded, root, strict)


def clear_cache() -> None:
    """The light/dark variant changes with the IDE theme."""
    if _active is not None:
        _active._cache.clear()


__all__ = ["IconTheme", "IconThemeInfo", "collect", "available", "chosen", "choose", "refresh", "active",
           "provider", "clear_cache", "SETTING"]
