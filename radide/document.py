"""FormDocument: a form being edited, shared by designer, properties and code views.

Supports multi-selection, snapshot based undo/redo, clipboard and alignment.
"""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QMimeData, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .controls import CONTROL_TYPES, MENU_TYPES
from .layout import client_size, relayout, resize_children
from .model import Control, Form
from .preview import REBUILD_PROPS

# properties whose change can move docked / anchored controls
LAYOUT_PROPS = {"Left", "Top", "Width", "Height", "Dock", "Anchor", "Visible", "TabPage", "TabPages",
                "Spacing", "Align", "Padding"}       # the last three: mobile Column / Row / Stack

CLIP_MIME = "application/x-radide-controls"
UNDO_LIMIT = 200


class FormDocument(QObject):
    selectionChanged = pyqtSignal(object)      # primary Control | None (None = the form)
    controlChanged = pyqtSignal(object)        # Control | None (None = form props)
    structureChanged = pyqtSignal()            # controls added / removed / reordered / renamed
    modifiedChanged = pyqtSignal(bool)
    eventRequested = pyqtSignal(object, str)   # owner (Control | None), event name
    renamed = pyqtSignal(str, str)             # old name, new name (control)
    formRenameRequested = pyqtSignal(str, str) # old, new (form)
    undoStateChanged = pyqtSignal()

    def __init__(self, form: Form, path: Path):
        super().__init__()
        self.form = form
        self.path = path
        self.selection: list[Control] = []
        self._modified = False
        self._undo: list[str] = []
        self._redo: list[str] = []

    # ------------------------------------------------------------ state
    @property
    def selected(self) -> Control | None:
        """Primary selection (the one shown in the Properties window)."""
        return self.selection[-1] if self.selection else None

    @property
    def modified(self) -> bool:
        return self._modified

    def set_modified(self, value: bool = True) -> None:
        if value != self._modified:
            self._modified = value
            self.modifiedChanged.emit(value)

    def select(self, ctrl: Control | None, add: bool = False) -> None:
        if add and ctrl is not None:
            if ctrl in self.selection:
                self.selection.remove(ctrl)
            else:
                self.selection.append(ctrl)
        else:
            if ctrl is None and not self.selection:
                return
            if ctrl is not None and self.selection == [ctrl]:
                return
            self.selection = [ctrl] if ctrl is not None else []
        self.selectionChanged.emit(self.selected)

    def select_many(self, ctrls: list[Control]) -> None:
        self.selection = list(ctrls)
        self.selectionChanged.emit(self.selected)

    # ------------------------------------------------------------ undo
    def checkpoint(self) -> None:
        self._undo.append(self.form.snapshot())
        if len(self._undo) > UNDO_LIMIT:
            self._undo.pop(0)
        self._redo.clear()
        self.undoStateChanged.emit()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> None:
        if self._undo:
            self._redo.append(self.form.snapshot())
            self._restore(self._undo.pop())

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self.form.snapshot())
            self._restore(self._redo.pop())

    def _restore(self, snap: str) -> None:
        names = [c.name for c in self.selection]
        restored = Form.from_dict(json.loads(snap))
        self.form.props = restored.props
        self.form.controls = restored.controls
        self.form.extra = restored.extra          # Blend states / storyboards / data bindings
        self.selection = [c for c in (self.form.find(n) for n in names) if c]
        self.structureChanged.emit()
        self.controlChanged.emit(None)
        self.selectionChanged.emit(self.selected)
        self.set_modified()
        self.undoStateChanged.emit()

    # ------------------------------------------------------------ edits
    def add_control(self, type_name: str, x: int, y: int, parent: str = "") -> Control:
        self.checkpoint()
        ctrl = self.form.add(type_name, x, y, parent)
        self._set_tab_page(ctrl)
        self._normalize()
        self._relayout(emit=False)
        self.structureChanged.emit()
        self.set_modified()
        self.select(ctrl)
        return ctrl

    def remove_controls(self, ctrls: list[Control]) -> None:
        if not ctrls:
            return
        self.checkpoint()
        doomed = []
        for c in ctrls:
            if c in self.form.controls and c not in doomed:
                doomed.append(c)
                doomed += [d for d in self.form.descendants(c) if d not in doomed]
        for c in doomed:
            self.form.controls.remove(c)
        self.selection = [c for c in self.selection if c not in doomed]
        self.structureChanged.emit()
        self.selectionChanged.emit(self.selected)
        self.set_modified()

    def remove_control(self, ctrl: Control) -> None:
        self.remove_controls([ctrl])

    def set_prop(self, owner: Control | None, name: str, value, record: bool = True) -> None:
        props = owner.props if owner else self.form.props
        if props.get(name) == value:
            return
        if owner is None and name == "Name":
            self.formRenameRequested.emit(self.form.name, value)
            return
        if record:
            self.checkpoint()
        old = props.get(name)
        resized = name in ("Width", "Height") and (owner is None or owner.ctype.container)
        before = client_size(self.form, owner) if resized else None
        props[name] = value
        if resized:          # anchored children follow the container / the form
            for c in resize_children(self.form, owner, before, client_size(self.form, owner)):
                self.controlChanged.emit(c)
        if name in REBUILD_PROPS:
            self.structureChanged.emit()
        if name == "Name" and owner is not None:
            for c in self.form.controls:          # keep children attached
                if c.parent == old:
                    c.props["Parent"] = value
            self.renamed.emit(old, value)
            self.structureChanged.emit()
        self.controlChanged.emit(owner)
        if name in LAYOUT_PROPS or owner is None:
            self._relayout()
        self.set_modified()

    def set_geometry(self, ctrl: Control, x: int, y: int, w: int, h: int) -> None:
        """No checkpoint: callers record one for the whole gesture."""
        before = client_size(self.form, ctrl) if ctrl.ctype.container else None
        for k, v in (("Left", x), ("Top", y), ("Width", w), ("Height", h)):
            ctrl.props[k] = int(v)
        if before is not None:
            for c in resize_children(self.form, ctrl, before, client_size(self.form, ctrl)):
                self.controlChanged.emit(c)
        self.controlChanged.emit(ctrl)
        self._relayout()
        self.set_modified()

    def _relayout(self, emit: bool = True) -> None:
        """Snap docked controls to their edges (after any geometry change)."""
        changed = relayout(self.form)
        if emit:
            for c in dict.fromkeys(changed):
                self.controlChanged.emit(c)

    def _set_tab_page(self, ctrl: Control) -> None:
        """Controls dropped on a TabControl go to its selected page."""
        parent = self.form.find(ctrl.parent) if ctrl.parent else None
        if parent is not None and parent.type == "TabControl":
            ctrl.props["TabPage"] = int(parent.props.get("SelectedIndex", 0) or 0)
        else:
            ctrl.props.pop("TabPage", None)

    @property
    def locked(self) -> bool:
        return bool(self.form.props.get("LockControls"))

    def set_locked(self, on: bool) -> None:
        """Format > Lock Controls: controls can be selected but not moved or resized."""
        if self.locked != bool(on):
            self.form.props["LockControls"] = bool(on)
            self.controlChanged.emit(None)
            self.set_modified()

    def reparent(self, ctrl: Control, parent: str) -> None:
        """Move ctrl into another container keeping its absolute position."""
        if ctrl.parent == parent:
            return
        ax, ay = self.form.abs_pos(ctrl)
        px, py = self.form.client_origin(self.form.find(parent) if parent else None)
        ctrl.props["Parent"] = parent
        ctrl.props["Left"], ctrl.props["Top"] = ax - px, ay - py
        self._set_tab_page(ctrl)
        self._normalize()
        self._relayout(emit=False)
        self.structureChanged.emit()
        self.set_modified()

    def reorder(self, ctrl: Control, front: bool) -> None:
        self.checkpoint()
        self.form.controls.remove(ctrl)
        if front:
            self.form.controls.append(ctrl)
        else:
            self.form.controls.insert(0, ctrl)
        self._normalize()
        self.structureChanged.emit()
        self.set_modified()

    def _normalize(self) -> None:
        self.form.controls = self.form.ordered() + self.form.nonvisual()

    # ------------------------------------------------------------ clipboard
    def copy(self) -> bool:
        if not self.selection:
            return False
        picked: list[Control] = []
        for c in self.selection:
            for x in [c, *self.form.descendants(c)]:
                if x not in picked:
                    picked.append(x)
        mime = QMimeData()
        mime.setData(CLIP_MIME, json.dumps([c.to_dict() for c in picked]).encode())
        QApplication.clipboard().setMimeData(mime)
        return True

    def cut(self) -> None:
        if self.copy():
            self.remove_controls(list(self.selection))

    def can_paste(self) -> bool:
        md = QApplication.clipboard().mimeData()
        return md is not None and md.hasFormat(CLIP_MIME)

    def paste(self) -> None:
        if not self.can_paste():
            return
        data = json.loads(bytes(QApplication.clipboard().mimeData().data(CLIP_MIME)).decode())
        self.checkpoint()
        new: list[Control] = []
        mapping: dict[str, str] = {}
        taken: set[str] = set()
        for d in data:
            c = Control.from_dict(d)
            ctype = CONTROL_TYPES[c.type]
            if c.type in MENU_TYPES and any(x.type == c.type for x in self.form.controls):
                continue                                   # one menu / tool strip per form
            new_name = self.form.unique_name(ctype.prefix, taken)
            taken.add(new_name.lower())
            mapping[c.name] = new_name
            c.props["Name"] = new_name
            new.append(c)
        for c in new:
            if c.parent in mapping:
                c.props["Parent"] = mapping[c.parent]
            else:
                c.props["Parent"] = ""
                if not c.ctype.nonvisual:
                    c.props["Left"] = int(c.props["Left"]) + 16
                    c.props["Top"] = int(c.props["Top"]) + 16
            if c.type in MENU_TYPES:   # menu item names must stay unique too
                self._rename_menu_items(c.props.get("Items", []), taken)
        self.form.controls += new
        self._normalize()
        self._relayout(emit=False)
        self.structureChanged.emit()
        self.set_modified()
        self.select_many([c for c in new if c.parent not in mapping.values()])

    def _rename_menu_items(self, items: list, taken: set[str]) -> None:
        for it in items:
            if it.get("Name"):
                base = it["Name"].rstrip("0123456789") or "mnu"
                it["Name"] = self.form.unique_name(base, taken)
                taken.add(it["Name"].lower())
            self._rename_menu_items(it.get("Items", []), taken)

    # ------------------------------------------------------------ format
    def align(self, mode: str) -> None:
        sel = [c for c in self.selection if not c.ctype.nonvisual]
        ref = self.selected
        if ref is None or ref.ctype.nonvisual:
            return
        p = lambda c, k: int(c.props[k])
        if mode.startswith("center_form"):
            if not sel:
                return
            self.checkpoint()
            for c in sel:
                parent = self.form.find(c.parent) if c.parent else None
                pw = p(parent, "Width") if parent else int(self.form.props["Width"])
                ph = p(parent, "Height") if parent else int(self.form.props["Height"])
                if mode == "center_form_h":
                    c.props["Left"] = (pw - p(c, "Width")) // 2
                else:
                    c.props["Top"] = (ph - p(c, "Height")) // 2
                self.controlChanged.emit(c)
            self.set_modified()
            return
        if len(sel) < 2:
            return
        self.checkpoint()
        for c in sel:
            if c is ref:
                continue
            if mode == "left":
                c.props["Left"] = p(ref, "Left")
            elif mode == "right":
                c.props["Left"] = p(ref, "Left") + p(ref, "Width") - p(c, "Width")
            elif mode == "top":
                c.props["Top"] = p(ref, "Top")
            elif mode == "bottom":
                c.props["Top"] = p(ref, "Top") + p(ref, "Height") - p(c, "Height")
            elif mode == "center_v":
                c.props["Left"] = p(ref, "Left") + (p(ref, "Width") - p(c, "Width")) // 2
            elif mode == "middle":
                c.props["Top"] = p(ref, "Top") + (p(ref, "Height") - p(c, "Height")) // 2
            elif mode == "same_width":
                c.props["Width"] = p(ref, "Width")
            elif mode == "same_height":
                c.props["Height"] = p(ref, "Height")
            elif mode == "same_size":
                c.props["Width"], c.props["Height"] = p(ref, "Width"), p(ref, "Height")
            self.controlChanged.emit(c)
        self.set_modified()

    def save(self) -> None:
        self.form.save(self.path)
        self.set_modified(False)
