"""FormDocument: a form being edited, shared by designer, properties and code views.

Supports multi-selection, snapshot based undo/redo, clipboard and alignment.
"""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QMimeData, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .controls import CONTROL_TYPES, MENU_TYPES, PAGED_TYPES, split_items
from .layout import client_size, relayout, resize_children
from .model import Control, Form
from .preview import REBUILD_PROPS

# properties whose change can move docked / anchored controls
LAYOUT_PROPS = {"Left", "Top", "Width", "Height", "Dock", "Anchor", "Visible", "TabPage", "TabPages",
                "Spacing", "Align", "Padding"}       # the last three: mobile Column / Row / Stack

CLIP_MIME = "application/x-radide-controls"
UNDO_LIMIT = 200
GRID = 8                # the designer's grid (radide/designer.py)
PASTE_STEP = 16         # a pasted group shifts by this while its place is taken

SPACING_MODES = {"hspace_equal", "hspace_inc", "hspace_dec", "hspace_remove",
                 "vspace_equal", "vspace_inc", "vspace_dec", "vspace_remove"}
# Format menu command -> how many selected controls it needs (Visual Studio greys it out below that)
FORMAT_MIN = {"left": 2, "center_v": 2, "right": 2, "top": 2, "middle": 2, "bottom": 2, "to_grid": 1,
              "same_width": 2, "same_height": 2, "same_size": 2, "size_to_grid": 1,
              "hspace_equal": 3, "hspace_inc": 2, "hspace_dec": 2, "hspace_remove": 2,
              "vspace_equal": 3, "vspace_inc": 2, "vspace_dec": 2, "vspace_remove": 2,
              "center_form_h": 1, "center_form_v": 1}


def is_docked(c) -> bool:
    return str(c.props.get("Dock") or "None") != "None"


class FormDocument(QObject):
    selectionChanged = pyqtSignal(object)      # primary Control | None (None = the form)
    controlChanged = pyqtSignal(object)        # Control | None (None = form props)
    structureChanged = pyqtSignal()            # controls added / removed / reordered / renamed
    modifiedChanged = pyqtSignal(bool)
    eventRequested = pyqtSignal(object, str)   # owner (Control | None), event name
    renamed = pyqtSignal(str, str)             # old name, new name (control)
    # an undo / redo gave a control its other name back: the code must follow (the form's own data -
    # localization keys, states, bindings - is already in the snapshot, so `renamed` does not fire)
    codeRenamed = pyqtSignal(str, str)         # old name, new name
    formRenameRequested = pyqtSignal(str, str) # old, new (form)
    undoStateChanged = pyqtSignal()
    # a mouse drag in the designer (move / resize a control, resize the form) is in progress: only
    # the designer follows each step (cheap geometry update); controlChanged - and with it the
    # Properties grid, Document Outline, localization / Blend previews ... - fires once on release
    liveChanged = pyqtSignal(object)           # Control | None, while live (see begin_live)

    def __init__(self, form: Form, path: Path):
        super().__init__()
        self.form = form
        self.path = path
        self.selection: list[Control] = []
        self._modified = False
        self._undo: list[str] = []
        self._redo: list[str] = []
        self._live: dict | None = None         # id -> Control (None key = the form) changed while live
        self.restoring = False                 # True while _restore (undo / redo) notifies the views

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

    def drop_noop(self) -> None:
        """A gesture recorded a checkpoint but changed nothing (a drag that snapped back to where it
        started, an arrow key on a docked control ...): forget that empty undo step, like Visual Studio."""
        if self._undo and self._undo[-1] == self.form.snapshot():
            self._undo.pop()
            self.undoStateChanged.emit()

    def cancel_gesture(self) -> None:
        """Esc during a drag: put everything back as it was at the last checkpoint, without a redo step."""
        if self._undo:
            self._restore(self._undo.pop())

    def _restore(self, snap: str) -> None:
        self._live = None                       # an undo replaces every control: nothing left to commit
        names = [c.name for c in self.selection]
        before = [(c.type, c.name) for c in self.form.controls]
        restored = Form.from_dict(json.loads(snap))
        renames = self._renames(before, [(c.type, c.name) for c in restored.controls])
        self.form.props = restored.props
        self.form.controls = restored.controls
        self.form.extra = restored.extra          # Blend states / storyboards / data bindings
        self.selection = [c for c in (self.form.find(n) for n in names) if c]
        # an undo / redo gives back EXACTLY the recorded form: listeners must not adjust it while they
        # follow (the designer would show the page of a selected control by changing SelectedIndex)
        self.restoring = True
        try:
            self.structureChanged.emit()
            self.controlChanged.emit(None)
            self.selectionChanged.emit(self.selected)
        finally:
            self.restoring = False
        for old, new in renames:
            self.codeRenamed.emit(old, new)
        self.set_modified()
        self.undoStateChanged.emit()

    @staticmethod
    def _renames(before: list, after: list) -> list[tuple[str, str]]:
        """(old, new) names of the controls an undo / redo renames. A rename keeps the order and the types
        of the controls, so the lists line up; any other step (add, delete, paste ...) renames nothing.
        A swap (A -> B while B -> A) cannot be done one name at a time in the code: left alone."""
        if len(before) != len(after) or any(b[0] != a[0] for b, a in zip(before, after)):
            return []
        pairs = [(b[1], a[1]) for b, a in zip(before, after) if b[1] != a[1]]
        olds = {o.lower() for o, _ in pairs}
        if any(n.lower() in olds for _, n in pairs):
            return []
        return pairs

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
        if owner is not None and owner.type in PAGED_TYPES and name in ("TabPages", "Pages"):
            # a page was removed: its controls go onto the last page that is left (same undo step) instead of
            # staying on a page that no longer exists (never shown, never reachable in the designer)
            n = max(1, len(split_items(value)))
            for c in self.form.controls:
                if c.parent == owner.name and isinstance(c.props.get("TabPage"), int) and c.props["TabPage"] >= n:
                    c.props["TabPage"] = n - 1
                    self._emit_changed(c)
        if resized:          # anchored children follow the container / the form
            for c in resize_children(self.form, owner, before, client_size(self.form, owner)):
                self._emit_changed(c)
        if self._live is not None and name in ("Left", "Top", "Width", "Height"):
            self._emit_changed(owner)          # a drag step: designer only, the rest on release
            self._relayout()
            self.set_modified()
            return
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

    def set_geometry(self, ctrl: Control, x: int, y: int, w: int, h: int, relayout: bool = True) -> None:
        """No checkpoint: callers record one for the whole gesture. relayout=False: the caller moves
        several controls and calls relayout_docked() once after the last one."""
        new = [int(v) for v in (x, y, w, h)]
        keys = ("Left", "Top", "Width", "Height")
        if self._live is not None and [ctrl.props.get(k) for k in keys] == new:
            return                              # a drag step that did not reach the next grid line
        before = client_size(self.form, ctrl) if ctrl.ctype.container else None
        for k, v in zip(keys, new):
            ctrl.props[k] = v
        if before is not None:
            for c in resize_children(self.form, ctrl, before, client_size(self.form, ctrl)):
                self._emit_changed(c)
        self._emit_changed(ctrl)
        if relayout:
            self._relayout()
        self.set_modified()

    def relayout_docked(self) -> None:
        """Snap docked controls after a batch of set_geometry(..., relayout=False) calls."""
        self._relayout()

    def _relayout(self, emit: bool = True) -> None:
        """Snap docked controls to their edges (after any geometry change)."""
        changed = relayout(self.form)
        if emit:
            for c in dict.fromkeys(changed):
                self._emit_changed(c)

    # ------------------------------------------------------------ live drags
    @property
    def live(self) -> bool:
        return self._live is not None

    def begin_live(self) -> None:
        """A designer drag starts: geometry changes notify liveChanged only, until end_live()."""
        if self._live is None:
            self._live = {}

    def end_live(self) -> None:
        """The drag ended: ONE controlChanged per control (and the form) changed during it."""
        pending, self._live = self._live, None
        if not pending:
            return
        if None in pending:                     # the form first (layout), then its controls
            self.controlChanged.emit(None)
        alive = {id(c) for c in self.form.controls}
        for key, c in pending.items():
            if key is not None and key in alive:
                self.controlChanged.emit(c)

    def _emit_changed(self, c) -> None:
        if self._live is None:
            self.controlChanged.emit(c)
            return
        key = None if c is None else id(c)
        self._live.pop(key, None)               # keep "last changed" order
        self._live[key] = c
        self.liveChanged.emit(c)

    def _set_tab_page(self, ctrl: Control) -> None:
        """Controls dropped on a TabControl go to its selected page."""
        parent = self.form.find(ctrl.parent) if ctrl.parent else None
        if parent is not None and parent.type in PAGED_TYPES:
            try:
                idx = int(parent.props.get("SelectedIndex", 0) or 0)
            except (TypeError, ValueError):
                idx = 0
            n = len(split_items(parent.props.get("TabPages", parent.props.get("Pages", ""))))
            # (SelectedIndex typed past the last page / -1): the control goes onto an existing page
            ctrl.props["TabPage"] = max(0, min(idx, max(1, n) - 1))
        else:
            ctrl.props.pop("TabPage", None)

    @property
    def locked(self) -> bool:
        return bool(self.form.props.get("LockControls"))

    def set_locked(self, on: bool) -> None:
        """Format > Lock Controls: controls can be selected but not moved or resized."""
        if self.locked != bool(on):
            self.checkpoint()                   # VS: Lock Controls is an undoable designer change
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

    def reorder(self, ctrl, front: bool) -> None:
        """Bring to Front / Send to Back.  *ctrl*: one control or a list (VS applies the command to every
        selected control and keeps their order among themselves)."""
        ctrls = [c for c in (ctrl if isinstance(ctrl, (list, tuple)) else [ctrl])
                 if c is not None and c in self.form.controls and not c.ctype.nonvisual]
        if not ctrls:
            return
        moved = [c for c in self.form.controls if c in ctrls]          # their current z-order
        rest = [c for c in self.form.controls if c not in ctrls]
        new = rest + moved if front else moved + rest
        if new == self.form.controls:
            return
        self.checkpoint()
        self.form.controls = new
        self._normalize()
        self._relayout(emit=False)             # the dock order follows the z-order
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

    def paste_target(self) -> str:
        """Where Edit > Paste puts the controls (Visual Studio): into the selected container, next to a
        selected control (its container), else on the form."""
        c = self.selected
        if c is None or c.ctype.nonvisual:
            return ""
        return c.name if c.ctype.container else (c.parent or "")

    def paste(self, parent: str | None = None) -> None:
        if not self.can_paste():
            return
        data = json.loads(bytes(QApplication.clipboard().mimeData().data(CLIP_MIME)).decode())
        if parent is None:
            parent = self.paste_target()
        if parent and self.form.find(parent) is None:
            parent = ""
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
        tops = [c for c in new if c.parent not in mapping]
        for c in new:
            if c.parent in mapping:
                c.props["Parent"] = mapping[c.parent]
            else:
                c.props["Parent"] = "" if c.ctype.nonvisual else parent
            if c.type in MENU_TYPES:   # menu item names must stay unique too
                self._rename_menu_items(c.props.get("Items", []), taken)
        # VS: the pasted controls keep their Location; while that spot is taken by a control of the same
        # container (pasting next to the originals, pasting again ...) the whole group shifts by a step
        vis = [c for c in tops if not c.ctype.nonvisual]
        if vis:
            def pos(c):
                return int(c.props["Left"]), int(c.props["Top"])
            used = {pos(c) for c in self.form.children(parent) if c not in new}
            off = 0
            while off < 100 * PASTE_STEP and any((x + off, y + off) in used for x, y in map(pos, vis)):
                off += PASTE_STEP
            for c in vis:
                c.props["Left"], c.props["Top"] = pos(c)[0] + off, pos(c)[1] + off
        self.form.controls += new
        for c in vis:
            self._set_tab_page(c)              # pasted onto a TabControl: its selected page
        self._normalize()
        self._relayout(emit=False)
        self.structureChanged.emit()
        self.set_modified()
        self.select_many(tops)

    def _rename_menu_items(self, items: list, taken: set[str]) -> None:
        for it in items:
            if it.get("Name"):
                base = it["Name"].rstrip("0123456789") or "mnu"
                it["Name"] = self.form.unique_name(base, taken)
                taken.add(it["Name"].lower())
            self._rename_menu_items(it.get("Items", []), taken)

    # ------------------------------------------------------------ format
    def format_targets(self) -> list[Control]:
        """Selected controls a Format command may move / resize: visual ones whose container is not also
        selected (that one carries them), not docked (the dock decides their place)."""
        sel = [c for c in self.selection if not c.ctype.nonvisual and c in self.form.controls]
        ids = {id(c) for c in sel}
        out = []
        for c in sel:
            p, seen, ok = (self.form.find(c.parent) if c.parent else None), set(), True
            while p is not None and p.name not in seen:
                seen.add(p.name)
                if id(p) in ids:
                    ok = False
                    break
                p = self.form.find(p.parent) if p.parent else None
            if ok and not is_docked(c):
                out.append(c)
        return out

    def can_format(self, mode: str) -> bool:
        """Whether the Format command *mode* applies to the selection (Visual Studio greys it out
        otherwise): Align / Make Same Size need 2 controls, Make Equal spacing 3, Center in Form,
        Align to Grid and Size to Grid 1; nothing moves while the controls are locked."""
        need = FORMAT_MIN.get(mode)
        if need is None or self.locked:
            return False
        targets = self.format_targets()
        if not targets:
            return False
        ref = self.selected
        if need >= 2:
            if ref is None or ref.ctype.nonvisual:
                return False
            count = len(targets) + (0 if ref in targets else 1)
            if ref not in targets and mode in SPACING_MODES:
                count = len(targets)
            return count >= need and any(c is not ref for c in targets)
        return True

    def _abs_rect(self, c: Control) -> list[int]:
        x, y = self.form.abs_pos(c)
        return [x, y, int(c.props["Width"]), int(c.props["Height"])]

    def _origin(self, c: Control) -> tuple[int, int]:
        return self.form.client_origin(self.form.find(c.parent) if c.parent else None)

    def align(self, mode: str, grid: int = GRID) -> None:
        """Format menu: Align (Lefts / Centers / Rights / Tops / Middles / Bottoms / to Grid), Make Same
        Size (Width / Height / Both / Size to Grid), Horizontal / Vertical Spacing (Make Equal / Increase /
        Decrease / Remove) and Center in Form - like Visual Studio: relative to the PRIMARY selection (the
        control with the white handles), in form coordinates (controls of different containers line up on
        screen), one undo step, nothing at all when the command does not apply."""
        if not self.can_format(mode):
            return
        targets = self.format_targets()
        ref = self.selected
        old = {id(c): self._abs_rect(c) for c in targets}
        new = {k: list(v) for k, v in old.items()}
        R = self._abs_rect(ref) if ref is not None and not ref.ctype.nonvisual else None
        if mode in ("left", "center_v", "right", "top", "middle", "bottom",
                    "same_width", "same_height", "same_size"):
            for c in targets:
                if c is ref:
                    continue
                r = new[id(c)]
                if mode == "left":
                    r[0] = R[0]
                elif mode == "right":
                    r[0] = R[0] + R[2] - r[2]
                elif mode == "center_v":
                    r[0] = R[0] + (R[2] - r[2]) // 2
                elif mode == "top":
                    r[1] = R[1]
                elif mode == "bottom":
                    r[1] = R[1] + R[3] - r[3]
                elif mode == "middle":
                    r[1] = R[1] + (R[3] - r[3]) // 2
                if mode in ("same_width", "same_size"):
                    r[2] = R[2]
                if mode in ("same_height", "same_size"):
                    r[3] = R[3]
        elif mode == "to_grid":                 # the Location goes to the nearest grid point
            for c in targets:
                r, (ox, oy) = new[id(c)], self._origin(c)
                r[0] = int(round((r[0] - ox) / grid) * grid) + ox
                r[1] = int(round((r[1] - oy) / grid) * grid) + oy
        elif mode == "size_to_grid":            # the Size goes to the nearest whole number of grid steps
            for c in targets:
                r = new[id(c)]
                r[2] = max(grid, int(round(r[2] / grid) * grid))
                r[3] = max(grid, int(round(r[3] / grid) * grid))
        elif mode in ("center_form_h", "center_form_v"):
            # the selection moves as ONE group (the spaces between the controls stay); controls of
            # different containers are centred in their own container
            groups: dict[str, list] = {}
            for c in targets:
                groups.setdefault(c.parent or "", []).append(c)
            a, s = (0, 2) if mode == "center_form_h" else (1, 3)
            for parent_name, items in groups.items():
                parent = self.form.find(parent_name) if parent_name else None
                cw, ch = client_size(self.form, parent)
                origin = self.form.client_origin(parent)[a]
                lo = min(old[id(c)][a] for c in items) - origin
                hi = max(old[id(c)][a] + old[id(c)][s] for c in items) - origin
                delta = ((cw if a == 0 else ch) - (hi - lo)) // 2 - lo
                for c in items:
                    new[id(c)][a] += delta
        elif mode in SPACING_MODES:
            a, s = (0, 2) if mode.startswith("h") else (1, 3)
            kind = mode.split("_", 1)[1]
            items = sorted(targets, key=lambda c: (old[id(c)][a], old[id(c)][1 - a]))
            if kind == "equal":                 # the outermost controls stay, the others share the room
                first, last = old[id(items[0])], old[id(items[-1])]
                room = last[a] + last[s] - first[a] - sum(old[id(c)][s] for c in items)
                gap = room / (len(items) - 1)
                pos = float(first[a])
                for i, c in enumerate(items):
                    if 0 < i < len(items) - 1:
                        new[id(c)][a] = int(round(pos))
                    pos += old[id(c)][s] + gap
            else:                               # the primary control stays where it is
                k = items.index(ref) if ref in items else 0
                if kind in ("inc", "dec"):
                    step = grid if kind == "inc" else -grid
                    for i, c in enumerate(items):
                        new[id(c)][a] = old[id(c)][a] + (i - k) * step
                else:                           # remove: the controls touch each other
                    pivot = old[id(items[k])]
                    pos = pivot[a] + pivot[s]
                    for c in items[k + 1:]:
                        new[id(c)][a] = pos
                        pos += old[id(c)][s]
                    pos = pivot[a]
                    for c in reversed(items[:k]):
                        pos -= old[id(c)][s]
                        new[id(c)][a] = pos
        changed = [c for c in targets if new[id(c)] != old[id(c)]]
        if not changed:
            return
        self.checkpoint()
        for c in changed:
            r, (ox, oy) = new[id(c)], self._origin(c)
            self.set_geometry(c, r[0] - ox, r[1] - oy, max(1, r[2]), max(1, r[3]), relayout=False)
        self._relayout()
        self.set_modified()

    def save(self) -> None:
        self.form.save(self.path)
        self.set_modified(False)
