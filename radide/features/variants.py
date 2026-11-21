"""Layout variants in the form designer: change the design for ONE window size without touching the others.

Above every form designer a *sizes bar* shows ``Edit: [All sizes | This size only]``, the size combo
(``Base design`` + the form's sizes), ``Add Size...``, ``Edit Sizes...``, ``Hide on this size`` and
``Side-by-side``.  With *All sizes* (the default, exactly the old behaviour) every edit changes the one
design; with a size picked it is previewed (anchored / docked controls follow its client area) and edits
still go to the base.  *This size only* draws an orange frame around the designer and records every edit
of a size-able property (radide/variants/model.py ``VARIANT_PROPS``) as an override of that size only.

* ``VariantPreview`` (one per DesignerView, pattern of localization.LocPreview): wraps the document's
  ``set_prop`` / ``set_geometry`` of this designer, chains ``doc.display_props``, provides
  ``doc.prop_marker`` (◆ changed on this size / ◇ changed on other sizes in the Properties window) and
  ``doc.prop_menu`` (Apply to all sizes, Reset to base, Copy to >, Hide / Show on this size).
* Precedence (plan 1.8): This size only > Blend record > localization language; turning This size only on
  switches the state / timeline Record off and is refused while a non-default Language is edited;
  starting a Record switches it off again.
* The "Sizes" dock shows a thumbnail of every size (click = show it in the designer); Side-by-side opens it
  as a wide floating window with large thumbnails.
"""
from __future__ import annotations

import copy

from PyQt6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QPushButton,
                             QSpinBox, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from ..variants import model as vm

ORANGE = "#F7630C"
BAR_H = 30
GEO = ("Left", "Top", "Width", "Height")
SIG_KEYS = tuple(dict.fromkeys(vm.VARIANT_PROPS + ("Parent", "TabPage", "Name")))


def tr(text: str) -> str:
    try:
        from ..i18n import tr as _tr
        return _tr(text)
    except Exception:  # noqa: BLE001 - translation is cosmetic
        return text


def _status(view, text: str, ms: int = 6000) -> None:
    try:
        win = view.window()
        if hasattr(win, "statusBar"):
            win.statusBar().showMessage(text, ms)
    except RuntimeError:
        pass


# ====================================================================== preview / interceptor
class VariantPreview(QObject):
    """Layout sizes on one DesignerView (see the module docstring)."""

    changed = pyqtSignal()                  # size / mode / overrides changed: bar, banner, gallery follow

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.doc = view.doc
        self.vid: str | None = None
        self.mode = "all"                   # "all" | "this"
        self._ver = 0
        self._cache = None                  # (key, {id(ctrl): props}, form props)
        self._sig = None
        self._shadow: dict = {}
        self._pending: set = set()
        self._flush_all = False
        self._flush_queued = False
        view._variant_preview = self
        doc = self.doc
        doc.controlChanged.connect(self._changed)
        doc.structureChanged.connect(self._structure)
        self._prev_display = getattr(doc, "display_props", None)
        doc.display_props = self.display_props
        doc.variant_display = self.overlay      # applied by properties.py even if display_props is replaced later
        doc.prop_marker = self.prop_marker
        doc.prop_menu = self.prop_menu
        self._orig_set_prop = doc.set_prop
        self._orig_set_geometry = doc.set_geometry
        doc.set_prop = self._set_prop
        doc.set_geometry = self._set_geometry
        self._guard = QTimer(self)          # a Blend / timeline Record started: This size only goes off
        self._guard.setInterval(400)
        self._guard.timeout.connect(self._check_record)
        self._capture()

    @staticmethod
    def of(view, create: bool = True):
        vp = getattr(view, "_variant_preview", None)
        if vp is None and create:
            vp = VariantPreview(view)
        return vp

    # ------------------------------------------------------------ state
    @property
    def form(self):
        return self.doc.form

    @property
    def active(self) -> bool:
        """A layout size is shown (in either mode)."""
        if self.vid is None:
            return False
        if vm.size(self.form, self.vid) is None:         # removed (Edit Sizes / undo)
            self.vid, self.mode = None, "all"
            return False
        return True

    @property
    def this_size(self) -> bool:
        return self.mode == "this" and self.active

    def size_label(self) -> str:
        return vm.label(self.form, self.vid) if self.vid else tr("Base design")

    def describe(self) -> str:
        if not self.active:
            return tr("Base design")
        ctx = vm.context(self.form, self.vid)
        return f"{tr(vm.label(self.form, self.vid))} {ctx['width']} x {ctx['height']}"

    # ------------------------------------------------------------ effective values
    def invalidate(self) -> None:
        self._ver += 1
        self._cache = None

    def _signature(self) -> str:
        """Cheap fingerprint of the base values the shown size depends on (once per event-loop pass)."""
        if self._sig is not None:
            return self._sig
        f = self.form
        parts = [repr([f.props.get(k) for k in ("Width", "Height", "Device", "Orientation", "Posture")])]
        for c in f.controls:
            parts.append(repr((id(c), [c.props.get(k) for k in SIG_KEYS])))
        self._sig = "|".join(parts)
        QTimer.singleShot(0, self._drop_sig)
        return self._sig

    def _drop_sig(self) -> None:
        self._sig = None

    def _effective(self):
        key = (self.vid, self._ver, id(self.form), id(self.form.controls), self._signature())
        if self._cache is None or self._cache[0] != key:
            f = self.form
            ef = vm.effective_form(f, self.vid)
            by_id = {id(c0): c1.props for c0, c1 in zip(f.controls, ef.controls)}
            self._cache = (key, by_id, ef.props)
        return self._cache

    def design_props(self, c) -> dict:
        """What the shown size has for *c* (None = the form)."""
        if not self.active:
            return c.props if c is not None else self.form.props
        _key, by_id, fprops = self._effective()
        if c is None:
            return fprops
        return by_id.get(id(c), c.props)

    def hidden(self, c) -> bool:
        """True when *c* is hidden on the shown size although the base design shows it."""
        if not self.active or not c.props.get("Visible", True):
            return False
        return not self.design_props(c).get("Visible", True)

    def display_props(self, ctrl, props) -> dict:
        """Properties window (FormDocument hook used by properties.py; chained after localization)."""
        base = props
        if self._prev_display is not None:
            try:
                base = self._prev_display(ctrl, props)
            except Exception:  # noqa: BLE001
                base = props
        return self.overlay(ctrl, base)

    def overlay(self, ctrl, props) -> dict:
        """*props* with the shown size's values of the size-able properties (idempotent)."""
        if not self.active:
            return props
        eff = self.design_props(ctrl)
        keys = vm.FORM_VARIANT_PROPS if ctrl is None else vm.VARIANT_PROPS
        out = dict(props)
        for k in keys:
            if k in eff:
                out[k] = eff[k]
        return out

    # ------------------------------------------------------------ preview widgets
    def apply(self, ctrl) -> None:
        """Show *ctrl* as the shown size has it (with a Blend state / timeline / sample data on top)."""
        from ..model import Control
        from ..preview import apply_props
        w = self.view.previews.get(id(ctrl))
        if w is None:
            return
        if not self.active:
            apply_props(w, ctrl)
            return
        props = dict(self.view._blend_over(ctrl, self.design_props(ctrl)))
        bp = getattr(self.view, "_blend_preview", None)
        if bp is not None and getattr(bp, "samples", False):
            try:
                eff = bp.effective(ctrl)
                props.update({k: v for k, v in eff.items() if ctrl.props.get(k) != v and k not in GEO})
            except Exception:  # noqa: BLE001
                pass
        try:
            apply_props(w, Control(ctrl.type, props, ctrl.states))
        except (TypeError, ValueError, KeyError):
            apply_props(w, ctrl)

    def refresh(self) -> None:
        """Every preview again (a size was picked / dropped, overrides changed)."""
        from ..preview import apply_props
        v = self.view
        if self.active:
            for c in self.form.visual():
                self.apply(c)
        else:
            for c in self.form.visual():
                w = v.previews.get(id(c))
                if w is not None:
                    apply_props(w, c)
            bp = getattr(v, "_blend_preview", None)
            if bp is not None:
                bp.refresh()
            lp = getattr(v, "_loc_preview", None)
            if lp is not None and (lp.code or lp.mirrored):
                lp.refresh()
        try:
            v.sync_pages()
            v.layout_form()
            v.frame.update()
            v.overlay.update()
        except (AttributeError, RuntimeError):
            pass

    def _queue(self, ctrl=None, everything: bool = False) -> None:
        """Re-apply after the other listeners of the same change (Blend / localization previews) ran."""
        if everything or ctrl is None:
            self._flush_all = True
        else:
            self._pending.add(id(ctrl))
        if not self._flush_queued:
            self._flush_queued = True
            QTimer.singleShot(0, self._flush)

    def _flush(self) -> None:
        self._flush_queued = False
        pending, everything = self._pending, self._flush_all
        self._pending, self._flush_all = set(), False
        try:
            if not self.active:
                return
            if everything:
                self.refresh()
                return
            for c in self.form.visual():
                if id(c) in pending:
                    self.apply(c)
            self.view.overlay.update()
        except RuntimeError:          # the designer was closed
            pass

    # ------------------------------------------------------------ listeners
    def _capture(self) -> None:
        f = self.form
        self._shadow = {id(c): {k: c.props.get(k) for k in vm.VARIANT_PROPS} for c in f.controls}
        self._shadow["form"] = {k: f.props.get(k) for k in vm.FORM_VARIANT_PROPS}

    def _structure(self) -> None:
        self.invalidate()
        self._capture()
        if self.vid is not None and not self.active:
            self.set_size(None)
            return
        self._queue(everything=True)
        self.changed.emit()

    def _changed(self, ctrl) -> None:
        self.invalidate()
        if self.this_size:
            self._catch_base_edit(ctrl)
        key = "form" if ctrl is None else id(ctrl)
        owner_props = self.form.props if ctrl is None else ctrl.props
        keys = vm.FORM_VARIANT_PROPS if ctrl is None else vm.VARIANT_PROPS
        self._shadow[key] = {k: owner_props.get(k) for k in keys}
        if self.active:
            self._queue(ctrl)
        self.changed.emit()

    def _catch_base_edit(self, ctrl) -> None:
        """This size only, an edit that did not go through set_prop / set_geometry (Format > Align ...):
        the changed size-able values become overrides of the size and the base gets its values back."""
        key = "form" if ctrl is None else id(ctrl)
        shadow = self._shadow.get(key)
        if shadow is None:
            return
        props = self.form.props if ctrl is None else ctrl.props
        keys = vm.FORM_VARIANT_PROPS if ctrl is None else vm.VARIANT_PROPS
        moved = False
        for k in keys:
            if k in props and props.get(k) != shadow.get(k) and shadow.get(k) is not None:
                vm.set_override(self.form, ctrl, self.vid, k, props[k])
                props[k] = shadow[k]
                moved = True
        if moved:
            self.invalidate()
            self.doc.set_modified()

    def _check_record(self) -> None:
        try:
            if self.this_size and self.view.blend_recording():
                self.set_mode("all")
                _status(self.view, tr("Recording a visual state / timeline: This size only was switched off."))
        except RuntimeError:
            self._guard.stop()

    # ------------------------------------------------------------ edit interception
    def _set_prop(self, owner, name, value, record=True):
        if not self.active:
            return self._orig_set_prop(owner, name, value, record)
        if self.mode == "this" and self.view.blend_recording():
            self.set_mode("all")
        allowed = vm.FORM_VARIANT_PROPS if owner is None else vm.VARIANT_PROPS
        if name not in allowed:
            if self.mode == "this" and name not in ("SelectedIndex", "TabIndex"):
                _status(self.view, f"{name}: " + tr("the same on every size - changed for all sizes."))
            return self._orig_set_prop(owner, name, value, record)
        shown = self.design_props(owner)
        if self.mode == "this":
            if shown.get(name) == value:
                return None
            if record:
                self.doc.checkpoint()
            self._override(owner, name, value)
            self._after_edit(owner)
            return None
        # All sizes while a size is shown: the base changes (geometry by the same distance)
        base = owner.props if owner is not None else self.form.props
        if name in GEO:
            try:
                value = int(base.get(name, 0)) + int(value) - int(shown.get(name, 0))
            except (TypeError, ValueError):
                pass
        elif name in vm.overrides(self.form, owner, self.vid):
            _status(self.view, f"{name}: " + tr("this size has its own value - the change went to the other "
                                               "sizes. Use This size only to change it here."), 8000)
        return self._orig_set_prop(owner, name, value, record)

    def _set_geometry(self, ctrl, x, y, w, h, relayout=True):
        if not self.active:
            return self._orig_set_geometry(ctrl, x, y, w, h, relayout)
        if self.mode == "this" and self.view.blend_recording():
            self.set_mode("all")
        shown = self.design_props(ctrl)
        new = [int(v) for v in (x, y, w, h)]
        if self.mode == "this":
            changed = False
            for k, v in zip(GEO, new):
                if int(shown.get(k, 0)) != v:
                    vm.set_override(self.form, ctrl, self.vid, k, v)
                    changed = True
            if changed:
                self._after_edit(ctrl)
            return None
        base = [int(ctrl.props.get(k, 0)) + v - int(shown.get(k, 0)) for k, v in zip(GEO, new)]
        return self._orig_set_geometry(ctrl, *base, relayout=relayout)

    def _override(self, owner, name, value) -> None:
        f = self.form
        base = owner.props if owner is not None else f.props
        if name not in GEO and name not in ("Anchor", "Dock") and base.get(name) == value and \
                len(vm.cascade(f, self.vid)) == 1:
            vm.remove_override(f, owner, self.vid, name)        # back to the base value: no override
        else:
            vm.set_override(f, owner, self.vid, name, value)

    def _after_edit(self, owner) -> None:
        self.invalidate()
        self.doc.set_modified()
        self.doc.controlChanged.emit(owner)

    # ------------------------------------------------------------ size / mode
    def set_size(self, vid) -> None:
        if vid is not None and vm.size(self.form, vid) is None:
            vid = None
        self.vid = vid
        if vid is None:
            self.mode = "all"
        self.invalidate()
        phone = getattr(self.view, "phone", None)
        if phone is not None and getattr(phone, "active", False) and hasattr(phone, "preview"):
            try:
                if vid is None:
                    phone.preview()
                else:
                    ctx = vm.context(self.form, vid)
                    from .. import devices
                    phone.preview(ctx.get("device"), "Landscape" if ctx["orientation"] == "landscape" else
                                  "Portrait", devices.posture_name(ctx.get("posture") or "Flat"))
            except Exception:  # noqa: BLE001 - the phone preview is cosmetic
                pass
        self._sync_guard()
        self.refresh()
        self.changed.emit()

    def set_mode(self, mode: str) -> bool:
        """"all" | "this"; returns False when This size only is refused (no size, a language is edited)."""
        if mode == "this":
            if not self.active:
                return False
            if not self._language_ok():
                _status(self.view, tr("Switch the form's Language back to (Default) to edit one size only."),
                        8000)
                self.changed.emit()
                return False
            self._stop_records()
        self.mode = "this" if mode == "this" else "all"
        self._capture()
        self._sync_guard()
        self.refresh()
        self.changed.emit()
        return True

    def _sync_guard(self) -> None:
        if self.this_size:
            self._guard.start()
        else:
            self._guard.stop()

    def _language_ok(self) -> bool:
        lang = self.form.props.get("Language")
        if not lang:
            return True
        try:
            from .localization import language_code
            return not language_code(lang)
        except Exception:  # noqa: BLE001
            return str(lang) in ("(Default)", "Default")

    def _stop_records(self) -> None:
        """Plan 1.8: This size only switches the visual-state and timeline Record off."""
        win = self.view.window()
        sp = getattr(win, "states_panel", None)
        rec = getattr(sp, "rec", None)
        if rec is not None and rec.isChecked():
            rec.setChecked(False)
        for cb in win.findChildren(QCheckBox, "timelineRecord") if hasattr(win, "findChildren") else []:
            if cb.isChecked():
                cb.setChecked(False)
        bp = getattr(self.view, "_blend_preview", None)
        if bp is not None and (bp.recording or bp.key_recorder is not None):
            bp.set_recording(False)
            bp.key_recorder = None

    # ------------------------------------------------------------ Properties window hooks
    def prop_marker(self, owner, name):
        """(symbol, tooltip) for a Properties row: ◆ changed on the shown size, ◇ changed on others."""
        if not vm.sizes(self.form):
            return None
        ids = vm.overridden_in(self.form, owner, name)
        if not ids:
            return None
        base = (owner.props if owner is not None else self.form.props).get(name)
        if self.active and self.vid in ids:
            return ("◆", f"{tr('Overridden on this size')}: {tr(vm.label(self.form, self.vid))}\n"
                              f"{tr('Base value')}: {base}\n{tr('Right-click > Reset to base to use the base value.')}")
        names = ", ".join(tr(vm.label(self.form, i)) for i in ids)
        return ("◇", f"{tr('Overridden on other sizes')}: {names}\n{tr('Base value')}: {base}")

    def prop_menu(self, menu: QMenu, owner, name) -> None:
        """Extra items of the Properties window's context menu for a size-able property."""
        f = self.form
        allowed = vm.FORM_VARIANT_PROPS if owner is None else vm.VARIANT_PROPS
        if name not in allowed or not vm.sizes(f):
            return
        menu.addSeparator()
        ids = vm.overridden_in(f, owner, name)
        a = menu.addAction(tr("Apply to all sizes"), lambda: self.apply_to_all(owner, name))
        a.setEnabled(bool(ids))
        a.setToolTip(tr("Use the value shown now on every size (removes the per-size values)."))
        a = menu.addAction(tr("Reset to base"), lambda: self.reset_to_base(owner, name))
        a.setEnabled(self.active and self.vid in ids)
        sub = menu.addMenu(tr("Copy to"))
        sub.setEnabled(self.active or bool(ids))
        for s in vm.sizes(f):
            if s["id"] != self.vid:
                sub.addAction(tr(vm.label(s)), lambda _=False, t=s["id"]: self.copy_to(owner, name, t))
        if owner is not None and self.active:
            hidden = not self.design_props(owner).get("Visible", True)
            menu.addAction(tr("Show on this size") if hidden else tr("Hide on this size"),
                           lambda: self.set_hidden([owner], not hidden))

    # ------------------------------------------------------------ commands
    def apply_to_all(self, owner, name) -> None:
        f = self.form
        value = self.design_props(owner).get(name)
        self.doc.checkpoint()
        props = owner.props if owner is not None else f.props
        for vid in vm.overridden_in(f, owner, name):
            vm.remove_override(f, owner, vid, name)
        if value is not None and name not in GEO:
            props[name] = value
        elif value is not None and self.active and name in GEO:
            props[name] = int(value)
        self._capture()
        self._after_edit(owner)
        self.refresh()

    def reset_to_base(self, owner, name) -> None:
        if not self.active:
            return
        self.doc.checkpoint()
        vm.remove_override(self.form, owner, self.vid, name)
        self._after_edit(owner)
        self.refresh()

    def copy_to(self, owner, name, target) -> None:
        value = self.design_props(owner).get(name)
        self.doc.checkpoint()
        vm.set_override(self.form, owner, target, name, value)
        self._after_edit(owner)

    def set_hidden(self, ctrls, hide: bool) -> None:
        """Hide on this size / Show on this size (the base design keeps its Visible)."""
        if not self.active or not ctrls:
            return
        self.doc.checkpoint()
        for c in ctrls:
            if c.ctype.nonvisual:
                continue
            if bool(c.props.get("Visible", True)) == (not hide) and len(vm.cascade(self.form, self.vid)) == 1:
                vm.remove_override(self.form, c, self.vid, "Visible")
            else:
                vm.set_override(self.form, c, self.vid, "Visible", not hide)
        self.invalidate()
        self.doc.set_modified()
        for c in ctrls:
            self.doc.controlChanged.emit(c)
        self.refresh()

    def add_size(self, sz: dict, select: bool = True, edit_only: bool = True) -> dict:
        self.doc.checkpoint()
        made = vm.add_size(self.form, sz)
        self.doc.set_modified()
        if select:
            self.set_size(made["id"])
            if edit_only:
                self.set_mode("this")
        else:
            self.changed.emit()
        return made


# ====================================================================== banner (orange frame)
class VariantBanner(QWidget):
    """Orange frame + "This size only: Tablet 800 x 1000" over the designer (mouse-transparent); a quiet
    label while a size is only previewed."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.mode = ""                      # "" | "this" | "preview"
        self.text = ""
        self.setObjectName("variantBanner")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        view.viewport().installEventFilter(self)
        self.hide()

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show) and self.mode:
            self._place()
        return False

    def _place(self) -> None:
        self.setGeometry(self.view.viewport().geometry())
        self.raise_()

    def set_mode(self, mode: str, text: str = "") -> None:
        self.mode, self.text = mode, text
        if mode:
            self._place()
            self.show()
            self.update()
        else:
            self.hide()

    def paintEvent(self, _e):
        if not self.mode:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = QColor(ORANGE) if self.mode == "this" else QColor("#5B6B7F")
        if self.mode == "this":
            p.setPen(QPen(col, 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(2, 2, self.width() - 4, self.height() - 4))
        f = p.font()
        f.setBold(True)
        p.setFont(f)
        tw = min(p.fontMetrics().horizontalAdvance(self.text) + 20, self.width() - 20)
        th = p.fontMetrics().height() + 8          # top-right (bottom-right on a phone: its device bar is on top)
        phone = getattr(getattr(self.view, "phone", None), "active", False)
        r = QRectF(self.width() - tw - 22, self.height() - th - 14 if phone else 10, tw, th)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(r, 5, 5)
        p.setPen(QColor("#ffffff"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text)
        p.end()


# ====================================================================== sizes bar
class VariantBar(QWidget):
    """The strip above a form designer (in the scroll area's top viewport margin)."""

    def __init__(self, view, vp: VariantPreview):
        super().__init__(view)
        self.view, self.vp = view, vp
        self.setObjectName("variantBar")
        self.setAutoFillBackground(True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(4)
        self.lbl_edit = QLabel("Edit:")
        lay.addWidget(self.lbl_edit)
        self.btn_all = self._tool("All sizes", "Edit every size at once (the normal way): a change here changes "
                                               "the design on every window size.", checkable=True)
        self.btn_this = self._tool("This size only", "Change the design for the selected size only - the other "
                                                     "sizes keep their layout. The designer gets an orange frame.",
                                   checkable=True)
        self.btn_all.setObjectName("variantAll")
        self.btn_this.setObjectName("variantThis")
        self.btn_all.clicked.connect(lambda: self._mode("all"))
        self.btn_this.clicked.connect(lambda: self._mode("this"))
        lay.addWidget(self.btn_all)
        lay.addWidget(self.btn_this)
        lay.addSpacing(8)
        self.lbl_size = QLabel("Size:")
        lay.addWidget(self.lbl_size)
        self.combo = QComboBox()
        self.combo.setObjectName("variantSize")
        self.combo.setMinimumContentsLength(14)
        self.combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo.setToolTip("The window size shown in the designer. Base design = the size you designed; "
                              "pick a size to see (and, with This size only, change) its layout.")
        self.combo.activated.connect(self._picked)
        lay.addWidget(self.combo)
        self.btn_add = self._tool("Add Size...", "Add a window size (Phone, Tablet, Landscape, foldable postures "
                                                 "...) whose layout you can change on its own.")
        self.btn_add.setObjectName("variantAdd")
        self.btn_add.clicked.connect(lambda: add_size_dialog(self.view))
        lay.addWidget(self.btn_add)
        self.btn_edit = self._tool("Edit Sizes...", "Rename sizes, change when they apply (width range, "
                                                    "orientation, posture) and their preview size.")
        self.btn_edit.clicked.connect(lambda: edit_sizes_dialog(self.view))
        lay.addWidget(self.btn_edit)
        lay.addSpacing(8)
        self.btn_hide = self._tool("Hide on this size", "Hide the selected controls on this size only (they stay "
                                                        "on the other sizes). Click again to show them.",
                                   checkable=True)
        self.btn_hide.setObjectName("variantHide")
        self.btn_hide.clicked.connect(self._hide)
        lay.addWidget(self.btn_hide)
        self.btn_side = self._tool("Side-by-side", "Show every size next to each other in the Sizes window "
                                                   "(click one to show it here).", checkable=True)
        self.btn_side.setObjectName("variantSide")
        self.btn_side.clicked.connect(self._side)
        lay.addWidget(self.btn_side)
        lay.addSpacing(8)
        self.info = QLabel()
        self.info.setObjectName("variantInfo")
        self.info.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(self.info, 1)
        try:
            from .. import theme
            theme.role(self.info, "muted")
        except Exception:  # noqa: BLE001
            pass
        self.banner = VariantBanner(view)
        vp.changed.connect(self.sync)
        view.doc.selectionChanged.connect(lambda *_a: self.sync())
        view.setViewportMargins(0, BAR_H, 0, 0)
        view.installEventFilter(self)
        self._place()
        self.sync()
        self.show()

    def _tool(self, text, tip, checkable=False) -> QToolButton:
        b = QToolButton()
        b.setText(text)
        b.setToolTip(tip)                   # the i18n setters translate (and switch back) these
        b.setAutoRaise(True)
        b.setCheckable(checkable)
        return b

    def eventFilter(self, obj, ev):
        if obj is self.view and ev.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._place()
        return False

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.Type.LanguageChange:        # Tools > Options > Language: texts built with tr()
            QTimer.singleShot(0, self.sync)

    def _place(self) -> None:
        fw = self.view.frameWidth()
        self.setGeometry(fw, fw, max(10, self.view.width() - 2 * fw), BAR_H)
        self.raise_()

    # ------------------------------------------------------------ actions
    def _mode(self, mode: str) -> None:
        vp = self.vp
        if mode == "this" and not vp.active:
            sizes = vm.sizes(vp.form)
            if sizes:                       # pick the first size and edit it alone
                vp.set_size(sizes[0]["id"])
            else:
                self.sync()
                add_size_dialog(self.view)
                return
        if not vp.set_mode(mode):
            self.sync()
            return
        if mode == "this":
            _status(self.view, tr("This size only: your changes apply to {}. Click All sizes to edit every "
                                  "size again.").format(vp.describe()), 8000)
        else:
            _status(self.view, tr("All sizes: your changes apply to every size."), 5000)

    def _picked(self, index: int) -> None:
        vid = self.combo.itemData(index)
        self.vp.set_size(vid or None)
        if vid:
            _status(self.view, tr("Showing {}.").format(self.vp.describe()) + " " +
                    (tr("Changes apply to this size only.") if self.vp.this_size else
                     tr("Changes still apply to every size - choose This size only to change this size alone.")),
                    8000)

    def _hide(self) -> None:
        vp = self.vp
        sel = [c for c in vp.doc.selection if not c.ctype.nonvisual]
        if not vp.active or not sel:
            self.sync()
            return
        hide = not all(not vp.design_props(c).get("Visible", True) for c in sel)
        vp.set_hidden(sel, hide)

    def _side(self, on: bool) -> None:
        win = self.view.window()
        panel = getattr(win, "sizes_panel", None)
        if panel is None:
            self.btn_side.setChecked(False)
            return
        panel.set_side_by_side(on)

    # ------------------------------------------------------------ state
    def sync(self) -> None:
        try:
            self._sync()
        except RuntimeError:              # closed designer
            pass

    def _sync(self) -> None:
        vp = self.vp
        f = vp.form
        sizes = vm.sizes(f)
        active = vp.active
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem(tr("Base design"), "")
        self.combo.setItemData(0, tr("The size you designed (what every size starts from)"),
                               Qt.ItemDataRole.ToolTipRole)
        for s in sizes:
            ctx = vm.context(f, s)
            mark = " ◆" if vm.has_overrides(f, s["id"]) else ""
            self.combo.addItem(f"{tr(vm.label(s))}  {ctx['width']} x {ctx['height']}{mark}", s["id"])
            self.combo.setItemData(self.combo.count() - 1, f"{tr('When')}: {vm.when_text(s.get('when'))}",
                                   Qt.ItemDataRole.ToolTipRole)
        i = self.combo.findData(vp.vid if active else "")
        self.combo.setCurrentIndex(max(0, i))
        self.combo.blockSignals(False)
        this = vp.this_size
        self.btn_all.setChecked(not this)
        self.btn_this.setChecked(this)
        self.btn_this.setStyleSheet(f"QToolButton:checked {{ background:{ORANGE}; color:white; font-weight:bold; "
                                    "border-radius:3px; }")
        sel = [c for c in vp.doc.selection if not c.ctype.nonvisual]
        self.btn_hide.setEnabled(active and bool(sel))
        hidden = bool(sel) and active and all(not vp.design_props(c).get("Visible", True) for c in sel)
        self.btn_hide.setChecked(hidden)
        self.btn_hide.setText(tr("Show on this size") if hidden else tr("Hide on this size"))
        self.btn_edit.setEnabled(bool(sizes))
        win = self.view.window()
        panel = getattr(win, "sizes_panel", None)
        self.btn_side.setChecked(bool(panel is not None and panel.side_by_side))
        if this:
            text = tr("Only {} changes").format(vp.describe())
            self.info.setStyleSheet(f"color:{ORANGE}; font-weight:bold;")
            self.banner.set_mode("this", f"{tr('This size only')}: {vp.describe()}")
        elif active:
            text = tr("Previewing - changes apply to every size")
            self.info.setStyleSheet("")
            self.banner.set_mode("preview", f"{tr('Preview')}: {vp.describe()}")
        else:
            text = tr("One design for every size. Add a size to change it for phones, tablets ...") \
                if not sizes else tr("Pick a size to see it; This size only changes just that size.")
            self.info.setStyleSheet("")
            self.banner.set_mode("")
        self.info.setText(text)
        self.info.setToolTip(text)


# ====================================================================== dialogs
def _preset_entries():
    """(label, [preset keys]) for the Add Size dialog: single sizes, then ready-made sets."""
    out = []
    for group, keys in vm.PRESET_GROUPS:
        for k in keys:
            s = vm.PRESETS[k]
            out.append((f"{tr(group)}: {tr(s['label'])}  ({vm.when_text(s['when'])})", [k]))
    sets = {"desktop": "Desktop set: Small + Medium + Large", "phone": "Phone set: Portrait + Landscape",
            "foldable": "Foldable set: Folded + Half-open + Flat", "responsive": "Responsive set: Phone + Tablet"}
    for key, text in sets.items():
        out.append((tr(text), list(vm.PRESET_SETS[key])))
    out.append((tr("Custom size (choose the width range)"), []))
    return out


def add_size_dialog(view) -> dict | None:
    """Add Size...: pick a ready-made size (or a set), rename it, start editing it alone."""
    vp = VariantPreview.of(view)
    dlg = QDialog(view)
    dlg.setWindowTitle(tr("Add Size"))
    lay = QVBoxLayout(dlg)
    intro = QLabel(tr("A size is a window size (or phone orientation / foldable posture) whose layout you can "
                      "change without touching the others. Everything you do not change stays as designed."))
    intro.setWordWrap(True)
    lay.addWidget(intro)
    pick = QComboBox()
    pick.setObjectName("variantPreset")
    entries = _preset_entries()
    for text, keys in entries:
        pick.addItem(text, keys)
    lay.addWidget(pick)
    row = QHBoxLayout()
    row.addWidget(QLabel(tr("Name:")))
    name = QLineEdit()
    name.setObjectName("variantName")
    row.addWidget(name, 1)
    lay.addLayout(row)
    custom = QWidget()
    crow = QHBoxLayout(custom)
    crow.setContentsMargins(0, 0, 0, 0)
    lo, hi = QSpinBox(), QSpinBox()
    for sb in (lo, hi):
        sb.setRange(0, 10000)
    hi.setValue(599)
    crow.addWidget(QLabel(tr("Width from")))
    crow.addWidget(lo)
    crow.addWidget(QLabel(tr("to")))
    crow.addWidget(hi)
    crow.addStretch(1)
    lay.addWidget(custom)
    start = QCheckBox(tr("Start editing this size only"))
    start.setObjectName("variantStart")
    start.setChecked(True)
    lay.addWidget(start)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    lay.addWidget(bb)

    def changed(_i=0):
        keys = pick.currentData() or []
        custom.setVisible(not keys)
        name.setEnabled(len(keys) <= 1)
        name.setText(tr(vm.PRESETS[keys[0]]["label"]) if len(keys) == 1 else
                     (tr("Custom") if not keys else ""))
    pick.currentIndexChanged.connect(changed)
    changed()
    dlg._parts = {"pick": pick, "name": name, "start": start, "lo": lo, "hi": hi}     # tests
    view._variant_dialog = dlg
    if not dlg.exec():
        return None
    return _add_from_dialog(vp, pick.currentData() or [], name.text().strip(), start.isChecked(), lo.value(),
                            hi.value())


def _add_from_dialog(vp, keys, label, start, lo=0, hi=599) -> dict | None:
    if not keys:
        when = {}
        if lo > 0:
            when["minWidth"] = lo
        if hi > 0:
            when["maxWidth"] = hi
        sz = {"id": label or "custom", "label": label or "Custom", "when": when,
              "preview": {"width": max(lo, min(hi, int(vp.form.props.get("Width", 600)))) if hi else lo + 200}}
        return vp.add_size(sz, edit_only=start)
    if len(keys) == 1:
        sz = vm.preset(keys[0])
        if label and label != tr(sz["label"]):
            sz["label"] = label
            sz["id"] = label
        return vp.add_size(sz, edit_only=start)
    vp.doc.checkpoint()
    made = [vm.add_size(vp.form, vm.preset(k)) for k in keys]
    vp.doc.set_modified()
    vp.set_size(made[0]["id"])
    if start:
        vp.set_mode("this")
    return made[0]


WHEN_CHOICES = {"orientation": ("", "portrait", "landscape"), "posture": ("", "flat", "half-opened", "folded"),
                "span": ("", "single", "dual"), "fold": ("", "vertical", "horizontal")}
COLUMNS = ("Name", "Min width", "Max width", "Orientation", "Posture", "Span", "Preview width", "Preview height",
           "Preview device")


def edit_sizes_dialog(view) -> bool:
    """Edit Sizes...: a table of the form's sizes (conditions, preview size / device, order)."""
    from .. import devices
    vp = VariantPreview.of(view)
    form = vp.form
    work = copy.deepcopy(vm.sizes(form))
    dlg = QDialog(view)
    dlg.setWindowTitle(tr("Edit Sizes"))
    dlg.resize(980, 380)
    lay = QVBoxLayout(dlg)
    info = QLabel(tr("Each size applies when all its conditions hold (empty = any). When several sizes apply, "
                     "the lower one in the list wins. Preview = how big the designer shows it."))
    info.setWordWrap(True)
    lay.addWidget(info)
    grid = QTableWidget()
    grid.setObjectName("variantSizesGrid")
    grid.setColumnCount(len(COLUMNS))
    grid.setHorizontalHeaderLabels([tr(c) for c in COLUMNS])
    grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    grid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    lay.addWidget(grid, 1)
    btns = QHBoxLayout()
    b_add, b_rem, b_up, b_down = (QPushButton(tr(t)) for t in ("Add", "Remove", "Move Up", "Move Down"))
    for b in (b_add, b_rem, b_up, b_down):
        btns.addWidget(b)
    btns.addStretch(1)
    lay.addLayout(btns)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    lay.addWidget(bb)
    dev_ids = [""] + list(devices.DEVICES)

    def combo(values, current, labels=None):
        cb = QComboBox()
        for i, v in enumerate(values):
            cb.addItem((labels[i] if labels else (tr(v) if v else tr("(any)"))), v)
        cb.setCurrentIndex(max(0, cb.findData(current or "")))
        return cb

    def fill():
        grid.setRowCount(len(work))
        for r, s in enumerate(work):
            when, pv = s.get("when") or {}, s.get("preview") or {}
            grid.setItem(r, 0, QTableWidgetItem(str(s.get("label") or s.get("id"))))
            for col, key in ((1, "minWidth"), (2, "maxWidth")):
                grid.setItem(r, col, QTableWidgetItem("" if when.get(key) in (None, "") else str(when[key])))
            for col, key in ((3, "orientation"), (4, "posture"), (5, "span")):
                grid.setCellWidget(r, col, combo(WHEN_CHOICES[key], str(when.get(key) or "").lower()))
            grid.setItem(r, 6, QTableWidgetItem(str(pv.get("width") or "")))
            grid.setItem(r, 7, QTableWidgetItem(str(pv.get("height") or "")))
            grid.setCellWidget(r, 8, combo(dev_ids, pv.get("device") or "",
                                           [tr("(none)")] + [d.name for d in devices.DEVICES.values()]))

    def num(r, c):
        it = grid.item(r, c)
        try:
            return int(it.text()) if it is not None and it.text().strip() else None
        except ValueError:
            return None

    def collect():
        for r, s in enumerate(work):
            it = grid.item(r, 0)
            s["label"] = it.text().strip() if it is not None and it.text().strip() else s.get("label") or s["id"]
            when = dict(s.get("when") or {})
            for col, key in ((1, "minWidth"), (2, "maxWidth")):
                v = num(r, col)
                if v is None:
                    when.pop(key, None)
                else:
                    when[key] = v
            for col, key in ((3, "orientation"), (4, "posture"), (5, "span")):
                cb = grid.cellWidget(r, col)
                v = cb.currentData() if cb is not None else ""
                if v:
                    when[key] = v
                else:
                    when.pop(key, None)
            s["when"] = when
            pv = dict(s.get("preview") or {})
            for col, key in ((6, "width"), (7, "height")):
                v = num(r, col)
                if v is None:
                    pv.pop(key, None)
                else:
                    pv[key] = v
            cb = grid.cellWidget(r, 8)
            dev = cb.currentData() if cb is not None else ""
            if dev:
                pv["device"] = dev
                pv.setdefault("orientation", "Landscape" if when.get("orientation") == "landscape" else "Portrait")
            else:
                for k in ("device", "orientation", "posture"):
                    pv.pop(k, None)
            if pv:
                s["preview"] = pv
            else:
                s.pop("preview", None)

    def add():
        collect()
        taken = {s["id"] for s in work}
        base, i = "size", 1
        while f"{base}{i}" in taken:
            i += 1
        work.append({"id": f"{base}{i}", "label": f"Size {i}", "when": {"maxWidth": 599},
                     "preview": {"width": 400}})
        fill()

    def remove():
        collect()
        r = grid.currentRow()
        if 0 <= r < len(work):
            work.pop(r)
            fill()

    def move(d):
        collect()
        r = grid.currentRow()
        if 0 <= r < len(work) and 0 <= r + d < len(work):
            work[r], work[r + d] = work[r + d], work[r]
            fill()
            grid.selectRow(r + d)

    b_add.clicked.connect(add)
    b_rem.clicked.connect(remove)
    b_up.clicked.connect(lambda: move(-1))
    b_down.clicked.connect(lambda: move(1))
    fill()
    dlg._parts = {"grid": grid, "collect": collect, "work": work, "add": add, "remove": remove}     # tests
    view._variant_dialog = dlg
    if not dlg.exec():
        return False
    collect()
    apply_sizes(vp, work)
    return True


def apply_sizes(vp, work: list[dict]) -> None:
    """Replace the form's size list (sizes no longer listed lose their overrides) - one undo step."""
    form = vp.form
    vp.doc.checkpoint()
    keep = {s["id"] for s in work}
    for s in vm.sizes(form):
        if s["id"] not in keep:
            vm.remove_size(form, s["id"])
    if work:
        vm.data(form, create=True)["sizes"] = copy.deepcopy(work)
    else:
        d = vm.data(form)
        if d:
            d["sizes"] = []
            vm._clean(form)
    vp.doc.set_modified()
    vp.invalidate()
    if vp.vid is not None and vp.vid not in keep:
        vp.set_size(None)
    else:
        vp.set_size(vp.vid)
    vp.doc.controlChanged.emit(None)


# ====================================================================== Sizes gallery dock
def render_size(form, path, vid, max_w: int, max_h: int, host=None) -> QPixmap:
    """A picture of *form* on size *vid* (None = the base design): its effective form drawn by a hidden
    designer (*host*: a DesignerView made by renderer() and reused, else a temporary one)."""
    ef = vm.effective_form(form, vid) if vid else copy.deepcopy(form)
    v = host if host is not None else renderer(path)
    try:
        v.doc.form, v.doc.path = ef, path
        v.doc.selection = []
        if getattr(v.phone, "previewing", False):
            v.phone.preview()
        v.rebuild()
        if vid and getattr(v.phone, "active", False):
            ctx = vm.context(form, vid)
            from .. import devices
            v.phone.preview(ctx.get("device"), "Landscape" if ctx["orientation"] == "landscape" else "Portrait",
                            devices.posture_name(ctx.get("posture") or "Flat"))
        v.layout_form()
        pm = v.frame.grab()
    finally:
        if host is None:
            v.hide()
            v.deleteLater()
    if pm.width() > max_w or pm.height() > max_h:
        pm = pm.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    return pm


def renderer(path):
    """A hidden DesignerView for render_size() (never shown on screen)."""
    from ..designer import DesignerView
    from ..document import FormDocument
    from ..model import Form
    v = DesignerView(FormDocument(Form(), path))
    v.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    v.resize(1600, 1400)
    v.show()
    return v


class SizesPanel(QWidget):
    """Dock "Sizes": a thumbnail of every size of the current form; click = show it in the designer."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.view = None
        self.side_by_side = False
        self.dock = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)
        self.list = QListWidget()
        self.list.setObjectName("variantGallery")
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setWrapping(True)
        self.list.setSpacing(6)
        self.list.setWordWrap(True)
        self.list.itemClicked.connect(self._clicked)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.btn_add = QPushButton("Add Size...")
        self.btn_add.clicked.connect(lambda: self.view is not None and add_size_dialog(self.view))
        row.addWidget(self.btn_add)
        self.btn_side = QPushButton("Side-by-side")
        self.btn_side.setCheckable(True)
        self.btn_side.clicked.connect(self.set_side_by_side)
        row.addWidget(self.btn_side)
        row.addStretch(1)
        lay.addLayout(row)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.render)
        self._vp = None
        self._doc = None
        self._host = None               # hidden DesignerView that draws the thumbnails (reused)

    def thumb_size(self) -> QSize:
        return QSize(340, 300) if self.side_by_side else QSize(150, 130)

    def bind(self, view) -> None:
        if view is self.view:
            return
        for sig, slot in self._links():
            try:
                sig.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self.view = view
        self._vp = VariantPreview.of(view) if view is not None else None
        self._doc = view.doc if view is not None else None
        for sig, slot in self._links():
            sig.connect(slot)
        self.schedule()

    def _links(self):
        out = []
        if self._vp is not None:
            out.append((self._vp.changed, self.schedule))
        if self._doc is not None:
            out.append((self._doc.modifiedChanged, self.schedule))
            out.append((self._doc.controlChanged, self.schedule))
        return out

    def schedule(self, *_a) -> None:
        if self.isVisible() or self.side_by_side:
            self.timer.start()

    def showEvent(self, e):
        super().showEvent(e)
        self.schedule()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.Type.LanguageChange:        # captions / hint are built with tr()
            QTimer.singleShot(0, self._retranslate)

    def _retranslate(self) -> None:
        try:
            if self.list.count() or self.hint.text():
                self.render()
        except RuntimeError:
            pass

    def set_side_by_side(self, on: bool) -> None:
        self.side_by_side = bool(on)
        self.btn_side.setChecked(self.side_by_side)
        dock = self.dock
        if dock is not None:
            if on:
                dock.show()
                dock.raise_()
                dock.setFloating(True)
                n = max(1, len(vm.sizes(self.view.doc.form)) + 1) if self.view is not None else 3
                dock.resize(min(1500, 370 * n + 40), 420)
            else:
                dock.setFloating(False)
        self.list.setIconSize(self.thumb_size())
        self.render()
        vp = self._vp
        if vp is not None:
            vp.changed.emit()

    def render(self) -> None:
        try:
            self._render()
        except RuntimeError:
            pass

    def _render(self) -> None:
        self.list.clear()
        view = self.view
        if view is None:
            self.hint.setText(tr("Open a form designer to see its sizes."))
            return
        vp = VariantPreview.of(view)
        form = view.doc.form
        sizes = vm.sizes(form)
        self.hint.setText(tr("Click a size to show it in the designer. An orange outline = the size has its own "
                             "changes.") if sizes else
                          tr("This form has one design for every size. Add a size to change the layout of "
                             "phones, tablets or foldables separately."))
        ts = self.thumb_size()
        self.list.setIconSize(ts)
        entries = [(None, tr("Base design"))] + [(s["id"], tr(vm.label(s))) for s in sizes]
        for vid, text in entries:
            try:
                if self._host is None:
                    self._host = renderer(view.doc.path)
                pm = render_size(form, view.doc.path, vid, ts.width() - 8, ts.height() - 8, self._host)
            except Exception as e:  # noqa: BLE001 - a thumbnail must never break the designer
                pm = QPixmap(ts.width() - 8, ts.height() - 8)
                pm.fill(QColor("#dddddd"))
                text += f" ({type(e).__name__})"
            own = bool(vid and vm.has_overrides(form, vid))
            current = (vp.vid if vp.active else None) == vid
            canvas = QPixmap(ts)
            canvas.fill(Qt.GlobalColor.transparent)
            p = QPainter(canvas)
            p.drawPixmap((ts.width() - pm.width()) // 2, (ts.height() - pm.height()) // 2, pm)
            if own or current:
                p.setPen(QPen(QColor(ORANGE) if own else QColor("#0f6cbd"), 4 if current else 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(2, 2, ts.width() - 4, ts.height() - 4)
            p.end()
            caption = text
            if vid:
                ctx = vm.context(form, vid)
                caption += f"\n{ctx['width']} x {ctx['height']}"
                n = sum(len((c.variants or {}).get(vid) or {}) for c in form.controls)
                if n:
                    caption += f"  ◆ {n}"
            it = QListWidgetItem(QIcon(canvas), caption)
            it.setData(Qt.ItemDataRole.UserRole, vid or "")
            it.setToolTip(f"{tr('When')}: {vm.when_text((vm.size(form, vid) or {}).get('when'))}" if vid else
                          tr("The size you designed (what every size starts from)"))
            self.list.addItem(it)

    def _clicked(self, item) -> None:
        if self.view is None:
            return
        vid = item.data(Qt.ItemDataRole.UserRole) or None
        VariantPreview.of(self.view).set_size(vid)


# ====================================================================== install
def attach(view):
    """VariantPreview + sizes bar on one DesignerView (idempotent)."""
    vp = VariantPreview.of(view)
    if getattr(view, "_variant_bar", None) is None:
        view._variant_bar = VariantBar(view, vp)
    return vp


def _designers(win):
    for st in win.project_states() if hasattr(win, "project_states") else []:
        yield from st.get("designers", {}).values()
    yield from getattr(win, "designers", {}).values()


def install(win) -> None:
    def hook_open(*_a):
        for v in list(_designers(win)):
            if getattr(v, "_variant_bar", None) is None:
                try:
                    attach(v)
                except Exception as e:  # noqa: BLE001 - never break the designer
                    win.log(f"[variants] {e}")

    orig_open = win.open_designer

    def open_designer(name, *a, **kw):
        r = orig_open(name, *a, **kw)
        hook_open()
        return r
    win.open_designer = open_designer

    panel = SizesPanel(win)
    win.sizes_panel = panel
    try:
        from .states import _add_dock, current_view
        panel.dock = _add_dock(win, "Sizes", panel, "dock_sizes")
        win.tabs.currentChanged.connect(lambda *_a: panel.bind(current_view(win)))
    except Exception as e:  # noqa: BLE001
        win.log(f"[variants] Sizes window: {e}")

    def designer_menu(form_name, m, c, _orig=win._designer_menu):
        _orig(form_name, m, c)
        v = win._current_designer() if hasattr(win, "_current_designer") else None
        if v is None:
            return
        vp = VariantPreview.of(v)
        sub = m.addMenu(tr("Layout Size"))
        a = sub.addAction(tr("All sizes"), lambda: vp.set_mode("all"))
        a.setCheckable(True)
        a.setChecked(not vp.this_size)
        bar = getattr(v, "_variant_bar", None)
        a = sub.addAction(tr("This size only"), lambda: bar._mode("this") if bar is not None else vp.set_mode("this"))
        a.setCheckable(True)
        a.setChecked(vp.this_size)
        sub.addSeparator()
        for vid, text in [(None, tr("Base design"))] + [(s["id"], tr(vm.label(s))) for s in vm.sizes(vp.form)]:
            a = sub.addAction(text, lambda _=False, i=vid: vp.set_size(i))
            a.setCheckable(True)
            a.setChecked((vp.vid if vp.active else None) == vid)
        sub.addSeparator()
        sub.addAction(tr("Add Size..."), lambda: add_size_dialog(v))
        if c is not None and not c.ctype.nonvisual and vp.active:
            hidden = not vp.design_props(c).get("Visible", True)
            m.addAction(tr("Show on this size") if hidden else tr("Hide on this size"),
                        lambda: vp.set_hidden([x for x in v.doc.selection if not x.ctype.nonvisual] or [c],
                                              not hidden))
    win._designer_menu = designer_menu
