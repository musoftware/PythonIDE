"""VS Code style Settings and Keyboard Shortcuts pages (Preferences: Open Settings (UI) / Open Keyboard Shortcuts).

* ``show_settings(win, query)``: every setting the enabled extensions contribute (contributes.configuration),
  grouped by extension, with VS Code's search syntax (text, ``@ext:publisher.name``, ``@modified``, a setting
  id). Booleans are check boxes, enums combo boxes, numbers / strings line edits, arrays / objects JSON;
  changes go to the user settings.json (contrib_configuration.set_values - extensions get
  onDidChangeConfiguration). "Edit in settings.json" opens the file.
* ``show_keyboard_shortcuts(win, query)``: the commands with their keybindings - IDE menu commands, VS Code
  built-in commands RAD IDE runs (default keys), extension contributes.keybindings and the user's
  keybindings.json - searchable by title, id or key ("ctrl+shift"), with source and when clause.
  Double-click / "Change Keybinding..." writes a rule (and the "-command" removal of the old key) to
  keybindings.json, like VS Code's editor.
Texts are English and translated by radide/i18n (Arabic table entries in radide/i18n/ar.json)."""
from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QInputDialog,
                             QLabel, QLineEdit, QPushButton, QScrollArea, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)


# ============================================================================ settings
def _matches(q: str, key: str, prop: dict, ext_id: str, modified: bool) -> bool:
    q = (q or "").strip()
    if not q:
        return True
    words = q.split()
    for w in words:
        wl = w.lower()
        if wl.startswith("@ext:"):
            if ext_id.lower() != wl[5:]:
                return False
        elif wl == "@modified":
            if not modified:
                return False
        elif wl not in key.lower() and wl not in str(prop.get("description") or prop.get("markdownDescription")
                                                        or "").lower():
            return False
    return True


class SettingsPage(QDialog):
    def __init__(self, win, query: str = ""):
        super().__init__(win)
        self.win = win
        self.setObjectName("vsxSettingsPage")
        self.setWindowTitle("Settings")
        self.resize(860, 620)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search = QLineEdit(query)
        self.search.setPlaceholderText("Search settings (@ext:publisher.name, @modified)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.fill)
        top.addWidget(self.search, 1)
        js = QPushButton("Edit in settings.json")
        js.clicked.connect(self.open_json)
        top.addWidget(js)
        lay.addLayout(top)
        self.count = QLabel()
        lay.addWidget(self.count)
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        lay.addWidget(self.area, 1)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        box.accepted.connect(self.accept)
        lay.addWidget(box)
        self.editors: dict = {}
        self.fill()

    def open_json(self):
        from . import contrib_configuration as CC
        p = CC.settings_path()
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}\n", "utf-8")
        svc = getattr(self.win, "vsx_host", None)
        if svc is not None:
            svc.open_path(str(p))
        self.accept()

    def fill(self):
        from . import contrib_configuration as CC
        from .contrib_common import enabled_extensions
        user = CC.load()
        page = QWidget()
        form = QVBoxLayout(page)
        self.editors = {}
        n = 0
        labels = {e.id: e.label for e in enabled_extensions()}
        groups: dict = {}
        for key, (prop, ext_id) in sorted(CC.schema().items()):
            if _matches(self.search.text(), key, prop, ext_id, key in user):
                groups.setdefault(ext_id, []).append((key, prop))
        for ext_id, items in groups.items():
            head = QLabel(f"<h3>{labels.get(ext_id, ext_id)}</h3>")
            head.setProperty("i18n_skip", True)
            form.addWidget(head)
            fl = QFormLayout()
            for key, prop in items:
                w = self._editor(key, prop, user.get(key, CC.default_of(prop)))
                lab = QLabel(f"<b>{key}</b>" + ("  •" if key in user else "") + "<br><span style='color:gray'>"
                             + str(prop.get("description") or prop.get("markdownDescription") or "")[:300] + "</span>")
                lab.setWordWrap(True)
                lab.setProperty("i18n_skip", True)
                lab.setTextFormat(Qt.TextFormat.RichText)
                fl.addRow(lab, w)
                self.editors[key] = w
                n += 1
            form.addLayout(fl)
        form.addStretch(1)
        self.area.setWidget(page)
        self.count.setText(f"{n} settings" if n else "No settings found")

    def _editor(self, key: str, prop: dict, value):
        from . import contrib_configuration as CC
        t = prop.get("type")
        t = t[0] if isinstance(t, list) and t else t

        def store(v):
            CC.set_values({key: v})
        if t == "boolean":
            w = QCheckBox()
            w.setChecked(bool(value))
            w.toggled.connect(store)
            return w
        if isinstance(prop.get("enum"), list) and prop["enum"]:
            w = QComboBox()
            for opt in prop["enum"]:
                w.addItem(str(opt), opt)
            i = w.findData(value)
            w.setCurrentIndex(max(0, i))
            w.currentIndexChanged.connect(lambda _i: store(w.currentData()))
            return w
        w = QLineEdit(json.dumps(value) if t in ("array", "object") else ("" if value is None else str(value)))

        def done():
            txt = w.text()
            try:
                v = json.loads(txt) if t in ("array", "object", "number", "integer") else txt
            except ValueError:
                return
            store(v)
        w.editingFinished.connect(done)
        return w


def show_settings(win, query: str = "") -> SettingsPage:
    dlg = SettingsPage(win, query)
    win._vsx_settings_page = dlg
    dlg.show()
    return dlg


# ============================================================================ keyboard shortcuts
def shortcut_rows(win) -> list[dict]:
    """[{title, command, key, when, source}] - what the Keyboard Shortcuts page lists."""
    rows: list[dict] = []
    seen = set()
    try:
        from ..features import command_palette as cp
        for label, a in cp.menu_actions(win):
            sc = cp._shortcut_text(a)
            rows.append({"title": label, "command": a.objectName() or label, "key": sc, "when": "", "source": "RAD IDE"})
        for c in cp.commands():
            rows.append({"title": c.label, "command": c.id, "key": c.shortcut, "when": "", "source":
                         "Extension" if "." in c.id else "RAD IDE"})
            seen.add(c.id)
    except Exception:  # noqa: BLE001
        pass
    from . import vscode_commands as VC
    for e in VC.palette_entries(win):
        if e["id"] in seen:
            continue
        rows.append({"title": (e["category"] + ": " if e["category"] else "") + e["title"], "command": e["id"],
                     "key": VC.display_key(e["key"]), "when": "", "source": "Default"})
    from . import contrib_keybindings as KB
    for b in KB.collect():
        rows.append({"title": b.get("title") or b["command"], "command": b["command"], "key": KB.qt_sequence(b["key"]),
                     "when": b.get("when", ""), "source": "User" if b.get("user") else f"Extension ({b.get('ext')})"})
    return rows


class KeyboardShortcutsPage(QDialog):
    def __init__(self, win, query: str = ""):
        super().__init__(win)
        self.win = win
        self.setObjectName("vsxKeyboardShortcuts")
        self.setWindowTitle("Keyboard Shortcuts")
        self.resize(920, 620)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search = QLineEdit(query)
        self.search.setPlaceholderText("Type to search in keybindings (title, command id or key)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.fill)
        top.addWidget(self.search, 1)
        ch = QPushButton("Change Keybinding...")
        ch.clicked.connect(self.change)
        top.addWidget(ch)
        js = QPushButton("Open Keyboard Shortcuts (JSON)")
        js.clicked.connect(self.open_json)
        top.addWidget(js)
        lay.addLayout(top)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Command", "Keybinding", "When", "Source", "Command ID"])
        self.tree.setRootIsDecorated(False)
        self.tree.setProperty("i18n_skip_items", True)
        self.tree.itemDoubleClicked.connect(lambda *_: self.change())
        lay.addWidget(self.tree, 1)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        self.rows = shortcut_rows(win)
        self.fill()

    def fill(self):
        q = self.search.text().strip().lower().replace(" ", "")
        self.tree.clear()
        for r in self.rows:
            hay = (r["title"] + r["command"] + r["key"]).lower().replace(" ", "")
            if q and q not in hay and not all(w in hay for w in self.search.text().lower().split()):
                continue
            it = QTreeWidgetItem([r["title"], r["key"], r["when"], r["source"], r["command"]])
            it.setData(0, Qt.ItemDataRole.UserRole, r)
            self.tree.addTopLevelItem(it)
        for i in range(4):
            self.tree.resizeColumnToContents(i)

    def open_json(self):
        from . import user_keybindings
        svc = getattr(self.win, "vsx_host", None)
        if svc is not None:
            svc.open_path(str(user_keybindings.ensure_file()))
        self.accept()

    def change(self, key: str | None = None):
        it = self.tree.currentItem()
        if it is None:
            return False
        r = it.data(0, Qt.ItemDataRole.UserRole)
        if key is None:
            key, ok = QInputDialog.getText(self, "Change Keybinding", f"Key for {r['title']} (e.g. ctrl+alt+k):")
            if not ok:
                return False
        return add_user_binding(r["command"], key.strip().lower(), old_key=r["key"], when=r["when"])


def add_user_binding(command: str, key: str, old_key: str = "", when: str = "") -> bool:
    """Append {key, command} (and {"-command"} for the old key) to keybindings.json."""
    from . import user_keybindings as UK
    if not key or not command:
        return False
    p = UK.ensure_file()
    rules = UK.load()
    if old_key:
        rules.append({"key": old_key.lower().replace(", ", " "), "command": "-" + command})
    rule = {"key": key, "command": command}
    if when:
        rule["when"] = when
    rules.append(rule)
    p.write_text("// Place your key bindings in this file to override the defaults (VS Code format).\n"
                 + json.dumps(rules, indent=2) + "\n", "utf-8")
    try:
        from . import contrib_runtime
        contrib_runtime.refresh()
    except Exception:  # noqa: BLE001
        pass
    return True


def show_keyboard_shortcuts(win, query: str = "") -> KeyboardShortcutsPage:
    dlg = KeyboardShortcutsPage(win, query)
    win._vsx_keys_page = dlg
    dlg.show()
    return dlg


__all__ = ["SettingsPage", "KeyboardShortcutsPage", "show_settings", "show_keyboard_shortcuts", "shortcut_rows",
           "add_user_binding"]
