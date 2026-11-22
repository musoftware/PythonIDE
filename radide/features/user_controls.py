"""User controls in the IDE (VB 2005 "Project > Add User Control").

* Project > Add User Control... creates <Name>.form (kind "usercontrol") + its code files and opens its
  designer (a plain design surface, no window caption).
* Project > User Control Properties and Events... (also in the user control designer's right-click menu)
  edits the table of its own properties (name, type, default, "maps to" an inner control property,
  description) and events.
* The Toolbox shows the project's user controls in a "<Project> Components" group; they are placed on
  forms (and inside other user controls) like any control; their custom properties appear in the
  Properties window (category Custom) and their events in the Events list.
* Editing a user control updates its instances in the open designers at once.
Code generation lives in radide/usercontrols.py (python-tk and python-qt)."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QListWidgetItem, QMessageBox, QPushButton, QSpinBox,
                             QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget, QLineEdit)

from .. import usercontrols as uc
from ..controls import CONTROL_TYPES

UC_ROLE = Qt.ItemDataRole.UserRole + 7          # marks the Toolbox items this feature adds
NONE_MAP = "(none)"


def uc_icon() -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#3c3c3c")))
    p.setBrush(QColor("#ffffff"))
    p.drawRect(1, 3, 18, 14)
    p.setBrush(QColor("#4a78c2"))
    p.drawRect(3, 5, 6, 4)
    p.setBrush(QColor("#dfe8f6"))
    p.drawRect(3, 11, 14, 4)
    p.setBrush(QColor("#2fb12f"))
    p.drawEllipse(11, 5, 5, 5)
    p.end()
    return QIcon(pm)


# ====================================================================== Properties and Events dialog
class UserControlDialog(QDialog):
    """The user control's own properties and events (VB: the control's public interface)."""

    TYPES = list(uc.PROP_TYPES)

    def __init__(self, parent, form):
        super().__init__(parent)
        self.form = form
        self.setWindowTitle(f"User Control Properties and Events - {form.name}")
        self.resize(820, 460)
        spec = uc.spec_of(form)
        lay = QVBoxLayout(self)
        intro = QLabel("Properties appear in the Properties window when the user control is placed on a form; "
                       "\"Maps to\" connects a property to a property of a control inside (e.g. lblTitle.Text). "
                       "Raise an event from the user control's code with  self.RaiseEvent(\"Changed\")  - the form "
                       "handles it in <instance>_Changed().")
        intro.setWordWrap(True)
        intro.setProperty("radRole", "muted")
        lay.addWidget(intro)
        tabs = QTabWidget()
        lay.addWidget(tabs, 1)
        # properties
        pw = QWidget()
        pl = QVBoxLayout(pw)
        self.props = QTableWidget(0, 5)
        self.props.setHorizontalHeaderLabels(["Name", "Type", "Default", "Maps to", "Description"])
        self.props.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.props.verticalHeader().hide()
        pl.addWidget(self.props, 1)
        row = QHBoxLayout()
        add_p, del_p = QPushButton("Add Property"), QPushButton("Remove")
        add_p.clicked.connect(lambda: self._add_prop({"name": self._free("Property"), "type": "str",
                                                      "default": "", "maps": "", "description": ""}))
        del_p.clicked.connect(lambda: self._remove(self.props))
        row.addWidget(add_p)
        row.addWidget(del_p)
        row.addStretch(1)
        pl.addLayout(row)
        tabs.addTab(pw, "Properties")
        # events
        ew = QWidget()
        el = QVBoxLayout(ew)
        self.events = QTableWidget(0, 2)
        self.events.setHorizontalHeaderLabels(["Name", "Description"])
        self.events.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.events.verticalHeader().hide()
        el.addWidget(self.events, 1)
        row = QHBoxLayout()
        add_e, del_e = QPushButton("Add Event"), QPushButton("Remove")
        add_e.clicked.connect(lambda: self._add_event({"name": self._free("Event"), "description": ""}))
        del_e.clicked.connect(lambda: self._remove(self.events))
        row.addWidget(add_e)
        row.addWidget(del_e)
        row.addStretch(1)
        el.addLayout(row)
        f = QFormLayout()
        self.default_event = QComboBox()
        self.default_event.setEditable(True)
        f.addRow("Default event (double-click on an instance):", self.default_event)
        el.addLayout(f)
        tabs.addTab(ew, "Events")
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        for p in spec["properties"]:
            self._add_prop(p)
        for e in spec["events"]:
            self._add_event(e)
        self.default_event.addItem("")
        self.default_event.addItems([e["name"] for e in spec["events"]])
        self.default_event.setCurrentText(spec["default_event"])

    # ------------------------------------------------------------ rows
    def _targets(self) -> list[str]:
        out = [NONE_MAP]
        for c in self.form.controls:
            if c.ctype.nonvisual:
                continue
            for prop in uc.MAP_PROPS:
                if prop in c.props:
                    out.append(f"{c.name}.{prop}")
        return out

    def _free(self, base: str) -> str:
        taken = {self._cell(t, r, 0) for t in (self.props, self.events) for r in range(t.rowCount())}
        i = 1
        while f"{base}{i}" in taken:
            i += 1
        return f"{base}{i}"

    @staticmethod
    def _cell(table, row, col) -> str:
        w = table.cellWidget(row, col)
        if isinstance(w, QComboBox):
            return w.currentText()
        it = table.item(row, col)
        return it.text() if it is not None else ""

    def _add_prop(self, p: dict) -> None:
        r = self.props.rowCount()
        self.props.insertRow(r)
        self.props.setItem(r, 0, QTableWidgetItem(p["name"]))
        t = QComboBox()
        t.addItems(self.TYPES)
        t.setCurrentText(p.get("type", "str"))
        self.props.setCellWidget(r, 1, t)
        self.props.setItem(r, 2, QTableWidgetItem(str(p.get("default", ""))))
        m = QComboBox()
        m.setEditable(True)
        m.addItems(self._targets())
        m.setCurrentText(p.get("maps") or NONE_MAP)
        self.props.setCellWidget(r, 3, m)
        self.props.setItem(r, 4, QTableWidgetItem(p.get("description", "")))
        self.props.setColumnWidth(3, 160)

    def _add_event(self, e: dict) -> None:
        r = self.events.rowCount()
        self.events.insertRow(r)
        self.events.setItem(r, 0, QTableWidgetItem(e["name"]))
        self.events.setItem(r, 1, QTableWidgetItem(e.get("description", "")))

    @staticmethod
    def _remove(table) -> None:
        r = table.currentRow()
        if r >= 0:
            table.removeRow(r)

    # ------------------------------------------------------------ result
    def spec(self) -> dict:
        props, events = [], []
        for r in range(self.props.rowCount()):
            t = self._cell(self.props, r, 1)
            maps = self._cell(self.props, r, 3)
            props.append({"name": self._cell(self.props, r, 0).strip(), "type": t,
                          "default": uc._coerce(self._cell(self.props, r, 2), t),
                          "maps": "" if maps in ("", NONE_MAP) else maps.strip(),
                          "description": self._cell(self.props, r, 4)})
        for r in range(self.events.rowCount()):
            events.append({"name": self._cell(self.events, r, 0).strip(),
                           "description": self._cell(self.events, r, 1)})
        return {"properties": props, "events": events, "default_event": self.default_event.currentText().strip()}

    def _accept(self) -> None:
        spec = self.spec()
        names = [p["name"] for p in spec["properties"]] + [e["name"] for e in spec["events"]]
        bad = [n for n in names if not uc._ident(n)]
        reserved = {"Name", "Left", "Top", "Width", "Height", "Parent", "Visible", "Enabled", "ToolTip", "BackColor",
                    "TabIndex", "Anchor", "Dock", "ForeColor", "FontName", "FontSize", "FontBold", "FontItalic",
                    "root", "RaiseEvent", "show"}
        clash = [n for n in names if n in reserved]
        dup = {n for n in names if names.count(n) > 1}
        if bad or clash or dup:
            QMessageBox.warning(self, "User Control", "Check the names:\n" + "\n".join(
                [f"'{n}' is not a valid name" for n in bad] + [f"'{n}' is a built-in property" for n in clash] +
                [f"'{n}' is used twice" for n in sorted(dup)]))
            return
        self.accept()


# ====================================================================== feature
class UserControlsFeature:
    def __init__(self, win):
        self.win = win
        self._timers: dict[str, QTimer] = {}
        self._watched: set[int] = set()

    # ------------------------------------------------------------ helpers
    def designers(self):
        seen = set()
        for st in self.win.project_states() if hasattr(self.win, "project_states") else []:
            for v in st.get("designers", {}).values():
                if id(v) not in seen:
                    seen.add(id(v))
                    yield v
        for v in getattr(self.win, "designers", {}).values():
            if id(v) not in seen:
                seen.add(id(v))
                yield v

    def project_ucs(self) -> list[str]:
        p = self.win.project
        if p is None:
            return []
        uc.register_folder(p.folder)
        return uc.project_user_controls(p)

    def supported(self, plugin_id: str) -> bool:
        return plugin_id in uc.SUPPORTED

    # ------------------------------------------------------------ toolbox
    def refresh_toolbox(self, *_a) -> None:
        tb = getattr(self.win, "toolbox", None)
        if tb is None:
            return
        for row in reversed(range(tb.count())):
            if tb.item(row).data(UC_ROLE):
                tb.takeItem(row)
        names = self.project_ucs()
        if not names:
            return
        current = self.win._current_designer() if hasattr(self.win, "_current_designer") else None
        own = current.doc.form.name if current is not None else ""
        header = QListWidgetItem(f"{self.win.project.name} Components")
        f = header.font()
        f.setBold(True)
        header.setFont(f)
        header.setFlags(Qt.ItemFlag.ItemIsEnabled)
        header.setSizeHint(QSize(10, 22))
        header.setData(UC_ROLE, "header")
        tb.insertItem(1, header)
        for i, n in enumerate(sorted(names)):
            it = QListWidgetItem(uc_icon(), n)
            it.setData(Qt.ItemDataRole.UserRole, n)
            it.setData(UC_ROLE, "item")
            ct = CONTROL_TYPES.get(n)
            it.setToolTip(ct.description if ct is not None else n)
            it.setSizeHint(QSize(10, 24))
            if n == own or self._contains(n, own):
                it.setFlags(Qt.ItemFlag.NoItemFlags)
                it.setToolTip(f"{n}: cannot be placed on itself.")
            tb.insertItem(2 + i, it)
        self._on_mode()

    def _contains(self, outer: str, inner: str) -> bool:
        """True when user control *outer* contains *inner* (directly or nested) - placing outer inside inner
        would be an endless loop."""
        if not inner or inner not in uc.USER_CONTROLS:
            return False
        seen, todo = set(), [outer]
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            info = uc.USER_CONTROLS.get(n)
            for c in (info["data"].get("controls", []) if info else []):
                t = c.get("type") if isinstance(c, dict) else None
                if t == inner:
                    return True
                if t in uc.USER_CONTROLS:
                    todo.append(t)
        return False

    def _on_mode(self, *_a) -> None:
        """After the Toolbox switched desktop / phone mode: our group is for desktop forms."""
        from ..toolbox import TOOL_STATE
        tb = getattr(self.win, "toolbox", None)
        if tb is None:
            return
        for row in range(tb.count()):
            it = tb.item(row)
            if it.data(UC_ROLE):
                it.setHidden(bool(TOOL_STATE.mobile))

    # ------------------------------------------------------------ live updates
    def watch(self, view) -> None:
        """A user control designer: its instances in other designers follow the edits."""
        if id(view) in self._watched:
            return
        self._watched.add(id(view))
        doc = view.doc
        orig_create = view.create_control

        def create_control(type_name, pos, size=None, *, _orig=orig_create, _view=view):   # size: a click-drag
            name = _view.doc.form.name
            if type_name == name or self._contains(type_name, name):
                self.win.statusBar().showMessage(f"{type_name} cannot be placed inside itself.", 5000)
                return
            if type_name in uc.USER_CONTROLS:
                try:
                    plugin = self.win.plugin_for_form(name)
                    if not self.supported(plugin.id):
                        QMessageBox.information(self.win, "User Control",
                                                f"User controls are generated for Python (Tkinter) and Python "
                                                f"(Qt) forms; {name} is {plugin.display_name}.")
                        return
                except Exception:  # noqa: BLE001
                    pass
            return _orig(type_name, pos, size)
        view.create_control = create_control
        if not uc.is_usercontrol(doc.form):
            return
        name = doc.form.name

        def changed(*_a, n=name, d=doc):
            t = self._timers.get(n)
            if t is None:
                t = QTimer(self.win)
                t.setSingleShot(True)
                t.setInterval(350)
                t.timeout.connect(lambda n=n, d=d: self.update_uc(n, d))
                self._timers[n] = t
            t.start()
        doc.structureChanged.connect(changed)
        doc.controlChanged.connect(changed)

    def update_uc(self, name: str, doc) -> None:
        try:
            form = doc.form
        except RuntimeError:
            return
        if not uc.is_usercontrol(form):
            return
        uc.register(name, form.to_dict(), doc.path)
        for v in self.designers():
            try:
                if v.doc is doc:
                    continue
                if any(c.type == name or self._contains(c.type, name) for c in v.doc.form.controls):
                    v.rebuild()
            except RuntimeError:
                continue
        props = getattr(self.win, "properties", None)
        if props is not None:
            try:
                props.refresh()
            except (RuntimeError, AttributeError):
                pass
        self.refresh_toolbox()

    # ------------------------------------------------------------ commands
    def add_user_control(self) -> None:
        win = self.win
        p = win.project
        if p is None:
            return
        plugin = win.plugin
        if not self.supported(plugin.id):
            QMessageBox.information(win, "Add User Control",
                                    "User controls are generated for Python (Tkinter) and Python (Qt) projects. "
                                    f"This project is {plugin.display_name}.")
            return
        dlg = QDialog(win)
        dlg.setWindowTitle("Add User Control")
        lay = QFormLayout(dlg)
        i = 1
        while f"UserControl{i}" in p.forms or f"UserControl{i}" in CONTROL_TYPES:
            i += 1
        name = QLineEdit(f"UserControl{i}")
        name.selectAll()
        w, h = QSpinBox(), QSpinBox()
        for s, v in ((w, 240), (h, 120)):
            s.setRange(16, 4000)
            s.setValue(v)
        lay.addRow("Name:", name)
        lay.addRow("Width:", w)
        lay.addRow("Height:", h)
        hint = QLabel("A user control is designed like a form and placed on forms from the Toolbox "
                      f"(group \"{p.name} Components\").")
        hint.setWordWrap(True)
        hint.setProperty("radRole", "muted")
        lay.addRow(hint)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addRow(bb)
        if not dlg.exec():
            return
        n = name.text().strip()
        import os
        taken = {f.lower() for f in p.forms} | {os.path.splitext(m)[0].lower() for m in p.modules}
        if not uc._ident(n) or n.lower() in taken or (n in CONTROL_TYPES and n not in uc.USER_CONTROLS):
            QMessageBox.warning(win, "Add User Control", f"'{n}' is not a valid new name.")
            return
        win.save_all()
        uc.create_usercontrol(p, n, w.value(), h.value())
        win._fill_solution()
        win.open_designer(n)
        self.refresh_toolbox()
        win.log(f"Added user control {n}: design it, declare its properties / events "
                f"(Project > User Control Properties and Events), then place it on a form from the Toolbox.")

    def edit_interface(self) -> None:
        v = self.win._current_designer()
        if v is None or not uc.is_usercontrol(v.doc.form):
            names = self.project_ucs()
            if not names:
                QMessageBox.information(self.win, "User Control", "The project has no user controls "
                                        "(Project > Add User Control...).")
                return
            n, ok = QInputDialog.getItem(self.win, "User Control", "User control:", names, 0, False)
            if not ok:
                return
            self.win.open_designer(n)
            v = self.win._current_designer()
            if v is None:
                return
        self.edit_view(v)

    def edit_view(self, v) -> None:
        dlg = UserControlDialog(self.win, v.doc.form)
        if not dlg.exec():
            return
        v.doc.checkpoint()
        uc.set_spec(v.doc.form, dlg.spec())
        v.doc.set_modified()
        v.frame.update()
        self.update_uc(v.doc.form.name, v.doc)


def install(win) -> None:
    from PyQt6.QtGui import QAction
    feat = UserControlsFeature(win)
    win.user_controls = feat
    a_add = QAction("Add &User Control...", win)
    a_add.setStatusTip("Add a user control: designed like a form, reused on forms from the Toolbox")
    a_add.triggered.connect(feat.add_user_control)
    a_if = QAction("User Control &Properties and Events...", win)
    a_if.setStatusTip("The properties and events a user control shows to the forms that use it")
    a_if.triggered.connect(feat.edit_interface)
    win.a_add_user_control, win.a_uc_interface = a_add, a_if
    for act in win.menuBar().actions():
        if act.text().replace("&", "") == "Project" and act.menu() is not None:
            m = act.menu()
            acts = m.actions()
            anchor = next((a for a in acts if a is getattr(win, "a_add_form", None)), None)
            idx = acts.index(anchor) + 1 if anchor in acts else 0
            before = acts[idx] if idx < len(acts) else None
            if before is not None:
                m.insertAction(before, a_add)
                m.insertAction(before, a_if)
            else:
                m.addAction(a_add)
                m.addAction(a_if)
            break

    win.extension_points.on("project_activated", lambda: QTimer.singleShot(0, feat.refresh_toolbox),
                            "user controls")

    def before_open(_name) -> None:          # the project's user controls before the form loads
        if win.project is not None:
            uc.register_folder(win.project.folder)

    def after_open(name) -> None:
        v = win.designers.get(name)
        if v is not None:
            feat.watch(v)
        feat.refresh_toolbox()

    def after_save(name, completed) -> None:
        doc = win.docs.get(name)
        if completed and doc is not None and uc.is_usercontrol(doc.form):
            uc.register(name, doc.form.to_dict(), doc.path)
    win.extension_points.on("designer_opening", before_open, "user controls")
    win.extension_points.on("designer_opened", after_open, "user controls")
    win.extension_points.on("form_saved", after_save, "user controls")

    def designer_menu(form_name, m, c):          # after the window's own items
        v = win.designers.get(form_name)
        if v is not None and uc.is_usercontrol(v.doc.form) and c is None:
            m.addSeparator()
            m.addAction(a_if)
    win.extension_points.on("designer_menu", designer_menu, "user controls")

    from ..toolbox import TOOL_STATE
    TOOL_STATE.modeChanged.connect(feat._on_mode)
    tabs = getattr(win, "tabs", None)
    if tabs is not None:
        tabs.currentChanged.connect(lambda _i: QTimer.singleShot(0, feat.refresh_toolbox))
