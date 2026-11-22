"""VS Code settings (``contributes.configuration``) -> a settings page per extension in Tools > Options.

The values live in ``<vsx root>\\settings.json`` (a flat {"section.key": value} map like VS Code's user
settings.json); only values that differ from the schema default are stored. The extension host reads them
with ``values()`` / ``get()`` (workspace.getConfiguration).

Options gets one "VS Code Extensions" tab: the file icon theme, then a list of the extensions that have
settings and, for the selected one, a form built from its JSON schema (boolean -> check box, enum -> combo
box, string -> line edit, number / integer -> spin box, array / object -> JSON text).
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from .contrib_common import enabled_extensions

SETTINGS_FILE = "settings.json"
_lock = threading.RLock()
# callables(changed: dict) run after the settings were saved (the extension host forwards the change)
ON_CHANGED: list = []


# ============================================================================ schema
def sections(ext) -> list[dict]:
    """[{title, properties: {key: schema}}] of one extension (configuration may be an object or a list)."""
    conf = ext.contributes.get("configuration") if isinstance(getattr(ext, "contributes", None), dict) else None
    items = conf if isinstance(conf, list) else [conf] if isinstance(conf, dict) else []
    out = []
    for c in items:
        if not isinstance(c, dict) or not isinstance(c.get("properties"), dict) or not c["properties"]:
            continue
        props = {k: v for k, v in c["properties"].items() if isinstance(v, dict)}
        out.append({"title": str(c.get("title") or ext.label), "properties": props})
    return out


def schema() -> dict:
    """key -> (schema, ext id) for every enabled extension."""
    out = {}
    for ext in enabled_extensions():
        for sec in sections(ext):
            for k, v in sec["properties"].items():
                out[k] = (v, ext.id)
    return out


def default_of(prop: dict):
    if "default" in prop:
        return prop["default"]
    t = prop.get("type")
    t = t[0] if isinstance(t, list) and t else t
    return {"boolean": False, "string": "", "number": 0, "integer": 0, "array": [], "object": {}}.get(t)


# ============================================================================ store
def settings_path() -> Path:
    from .package import vsx_root
    return vsx_root() / SETTINGS_FILE


def load() -> dict:
    with _lock:
        try:
            from .user_keybindings import strip_jsonc          # VS Code's settings.json allows comments
            data = json.loads(strip_jsonc(settings_path().read_text("utf-8")))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}


def save(data: dict) -> None:
    with _lock:
        p = settings_path()
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), "utf-8")
        tmp.replace(p)


def get(key: str, default=None):
    data = load()
    if key in data:
        return data[key]
    s = schema().get(key)
    return default_of(s[0]) if s else default


def values(prefix: str = "") -> dict:
    """Effective values (defaults overlaid with the user's) of every key under *prefix*."""
    out = {}
    for k, (prop, _ext) in schema().items():
        if not prefix or k == prefix or k.startswith(prefix + "."):
            out[k] = default_of(prop)
    for k, v in load().items():
        if not prefix or k == prefix or k.startswith(prefix + "."):
            out[k] = v
    return out


def set_values(changes: dict) -> dict:
    """Store {key: value}; a value equal to the default (or None) removes the key. Returns the real changes."""
    sch = schema()
    with _lock:
        data = load()
        changed = {}
        for k, v in changes.items():
            d = default_of(sch[k][0]) if k in sch else None
            old = data.get(k, d)
            if v is None or v == d:
                if k in data:
                    data.pop(k)
                    changed[k] = d
            else:
                data[k] = v
                if old != v:
                    changed[k] = v
        if changed:
            save(data)
    for fn in list(ON_CHANGED):
        try:
            if changed:
                fn(dict(changed))
        except Exception:  # noqa: BLE001
            pass
    return changed


# ============================================================================ Options page
def _plain(text: str) -> str:
    text = re.sub(r"`#?([^`]+?)#?`", r"\1", text or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.replace("**", "").strip()


def _ptype(prop: dict) -> str:
    t = prop.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), t[0] if t else "string")
    if "enum" in prop and isinstance(prop["enum"], list):
        return "enum"
    return str(t or "string")


class _Field:
    def __init__(self, key: str, prop: dict, value):
        from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit,
                                     QSpinBox)
        self.key, self.prop = key, prop
        self.kind = _ptype(prop)
        if self.kind == "boolean":
            w = QCheckBox(_plain(prop.get("markdownDescription") or prop.get("description") or key)[:300])
            w.setChecked(bool(value))
        elif self.kind == "enum":
            w = QComboBox()
            descs = prop.get("enumDescriptions") or prop.get("markdownEnumDescriptions") or []
            for i, v in enumerate(prop["enum"]):
                w.addItem(str(v), v)
                if i < len(descs) and isinstance(descs[i], str):
                    w.setItemData(i, _plain(descs[i]), 3)        # tool tip
            idx = next((i for i, v in enumerate(prop["enum"]) if v == value), 0)
            w.setCurrentIndex(idx)
        elif self.kind == "integer":
            w = QSpinBox()
            w.setRange(int(prop.get("minimum", -2**31)), int(prop.get("maximum", 2**31 - 1)))
            try:
                w.setValue(int(value or 0))
            except (TypeError, ValueError):
                pass
        elif self.kind == "number":
            w = QDoubleSpinBox()
            w.setDecimals(3)
            w.setRange(float(prop.get("minimum", -1e9)), float(prop.get("maximum", 1e9)))
            try:
                w.setValue(float(value or 0))
            except (TypeError, ValueError):
                pass
        elif self.kind in ("array", "object"):
            w = QPlainTextEdit(json.dumps(value, indent=1) if value is not None else "")
            w.setFixedHeight(64)
        else:
            w = QLineEdit("" if value is None else str(value))
        self.widget = w

    def value(self):
        w, k = self.widget, self.kind
        if k == "boolean":
            return w.isChecked()
        if k == "enum":
            return w.currentData()
        if k in ("integer", "number"):
            return w.value()
        if k in ("array", "object"):
            txt = w.toPlainText().strip()
            if not txt:
                return default_of(self.prop)
            try:
                return json.loads(txt)
            except ValueError:
                return default_of(self.prop)
        return w.text()


def _extension_form(ext, store: dict):
    from PyQt6.QtWidgets import QFormLayout, QLabel, QScrollArea, QWidget
    from .. import theme as T
    from PyQt6.QtCore import Qt
    page = QWidget()
    # the extension's own (English) keys and descriptions: left-to-right and never through the UI translator,
    # also in the Arabic IDE (a right-to-left form garbles and clips them)
    page.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    page.setProperty("i18n_skip", True)
    form = QFormLayout(page)
    head = QLabel(f"<b>{ext.label}</b> &nbsp; <span>{ext.id} {ext.version}</span>")
    form.addRow(head)
    fields = []
    for sec in sections(ext):
        if len(sections(ext)) > 1:
            lbl = QLabel(f"<b>{sec['title']}</b>")
            form.addRow(lbl)
        props = sorted(sec["properties"].items(), key=lambda kv: (kv[1].get("order", 1e9), kv[0]))
        for key, prop in props:
            if prop.get("deprecationMessage") or prop.get("markdownDeprecationMessage"):
                continue
            val = store.get(key, default_of(prop))
            f = _Field(key, prop, val)
            fields.append(f)
            form.addRow(QLabel(key), f.widget)
            if f.kind != "boolean":          # (a check box shows the description as its text)
                desc = _plain(prop.get("markdownDescription") or prop.get("description") or "")
                if desc:
                    d = QLabel(desc[:400])
                    d.setWordWrap(True)
                    T.role(d, "muted")
                    form.addRow("", d)
    sa = QScrollArea()
    sa.setLayoutDirection(Qt.LayoutDirection.LeftToRight)     # scrolls from the left like the form inside
    sa.setWidgetResizable(True)
    sa.setWidget(page)
    return sa, fields


def options_page(dialog):
    """settings.PAGE_HOOKS hook: (widget, title, apply) - the "VS Code Extensions" tab."""
    from PyQt6.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout, QLabel, QListWidget, QStackedWidget,
                                 QVBoxLayout, QWidget)
    from . import contrib_icons
    exts = [e for e in enabled_extensions() if sections(e)]
    icons = contrib_icons.available()
    if not exts and not icons:
        return None
    w = QWidget()
    lay = QVBoxLayout(w)
    top = QFormLayout()
    icon_combo = QComboBox()
    try:
        from ..i18n import tr
    except Exception:  # noqa: BLE001
        def tr(s):
            return s
    icon_combo.addItem(tr("None (RAD IDE icons)"), "none")
    for t in icons:
        icon_combo.addItem(t.label, t.theme_id)
    cur = contrib_icons.active()
    icon_combo.setCurrentIndex(max(0, icon_combo.findData(cur.info.theme_id if cur else "none")))
    top.addRow("File icon theme:", icon_combo)
    lay.addLayout(top)
    store = load()
    pages: dict[int, list] = {}
    if exts:
        sec = QLabel("Extension settings")
        sec.setStyleSheet("font-weight: bold; padding-top: 6px;")
        lay.addWidget(sec)
        row = QHBoxLayout()
        lst = QListWidget()
        lst.setMaximumWidth(220)
        stack = QStackedWidget()
        for e in exts:
            lst.addItem(e.label)
            stack.addWidget(QWidget())            # built when first shown

        def show(i):
            if i < 0:
                return
            if i not in pages:
                sa, fields = _extension_form(exts[i], store)
                old = stack.widget(i)
                stack.removeWidget(old)
                old.deleteLater()
                stack.insertWidget(i, sa)
                pages[i] = fields
            stack.setCurrentIndex(i)
        lst.currentRowChanged.connect(show)
        row.addWidget(lst)
        row.addWidget(stack, 1)
        lay.addLayout(row, 1)
        lst.setCurrentRow(0)
        w._vsx_list = lst
    w._vsx_icon_combo = icon_combo

    def apply():
        changes = {}
        for fields in pages.values():
            for f in fields:
                changes[f.key] = f.value()
        if changes:
            set_values(changes)
        want = icon_combo.currentData()
        act = contrib_icons.active()
        have = act.info.theme_id if act else "none"
        if want != have or contrib_icons.chosen() != want:
            contrib_icons.choose(want)
            try:
                from . import contrib_runtime
                contrib_runtime.refresh_icons(dialog.win)
            except Exception:  # noqa: BLE001
                pass
    return w, "VS Code Extensions", apply


__all__ = ["sections", "schema", "load", "save", "get", "values", "set_values", "options_page", "settings_path",
           "ON_CHANGED"]
