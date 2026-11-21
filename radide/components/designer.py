"""Design-surface rendering of component packages (radide/preview.py calls these).

A package's ``designer.py`` may define any of (all optional)::

    def create(parent, props, ctx) -> QWidget      # build the preview widget (a real Qt widget)
    def apply(widget, props, ctx) -> None           # update it after a property changed
    def paint(painter, rect, props, ctx) -> None    # or just draw it (QPainter, QRect) - simplest

*props* is the control's property dict, *ctx* a :class:`DesignContext` (control name and type, the package,
the project folder, ``resource(path)`` -> absolute path, ``icon()`` -> QIcon). Without ``create``/``paint`` the
default renderer draws a labelled box with the package icon. Errors in package code are caught: the control is
then drawn by the default renderer with the error in red, the IDE keeps working.
"""
from __future__ import annotations

import traceback
from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget

from . import package_of


class DesignContext:
    def __init__(self, ctrl, pkg, root):
        self.name = ctrl.name
        self.type = ctrl.type
        self.package = pkg
        self.root = Path(root) if root else None

    def resource(self, path: str) -> str:
        p = Path(str(path or ""))
        if not str(path or "") or p.is_absolute() or self.root is None:
            return str(p)
        return str(self.root / p)

    def icon(self) -> QIcon:
        from ..toolbox import control_icon
        return control_icon(self.type)


class ComponentPreview(QWidget):
    """Default / ``paint()``-based preview of a component."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.props: dict = {}
        self.ctx: DesignContext | None = None
        self.error = ""

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        pkg = self.ctx.package if self.ctx else None
        mod = pkg.designer_module() if pkg is not None else None
        fn = getattr(mod, "paint", None) if mod is not None else None
        if callable(fn) and not self.error:
            try:
                fn(p, QRect(r), dict(self.props), self.ctx)
                p.end()
                return
            except Exception:  # noqa: BLE001
                self.error = traceback.format_exc(limit=2).strip().splitlines()[-1]
        draw_default(p, r, self.ctx.type if self.ctx else "?", self.props, self.error,
                     missing=pkg is None)
        p.end()


def draw_default(p: QPainter, r: QRect, type_name: str, props: dict, error: str = "", missing=False) -> None:
    back = QColor(props.get("BackColor") or ("#FFF4F4" if missing or error else "#FAFBFD"))
    p.fillRect(r, back)
    p.setPen(QPen(QColor("#C04040" if missing or error else "#8A94A6"), 1, Qt.PenStyle.DashLine))
    p.drawRect(r.adjusted(0, 0, -1, -1))
    x = 4
    if r.height() >= 20 and r.width() >= 30:
        try:
            from ..toolbox import control_icon
            control_icon(type_name).paint(p, QRect(4, (r.height() - 16) // 2 if r.height() < 40 else 4, 16, 16))
            x = 24
        except Exception:  # noqa: BLE001
            pass
    p.setPen(QColor(props.get("ForeColor") or ("#A02020" if missing or error else "#2B3A55")))
    f = QFont(props.get("FontName") or "Segoe UI", 8)
    p.setFont(f)
    label = f"{props.get('Name', '')} ({type_name})" if props.get("Name") else type_name
    if missing:
        label = f"{type_name}: package not installed"
    elif error:
        label = f"{type_name}: {error}"
    top = 0 if r.height() < 40 else 4
    p.drawText(QRect(x, top, max(4, r.width() - x - 4), r.height() - top if r.height() < 40 else 16),
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)


def _design_flags(w: QWidget) -> None:
    w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    for child in w.findChildren(QWidget):
        child.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def make_component_preview(ctrl, parent: QWidget, root=None) -> QWidget:
    pkg = package_of(ctrl.type)
    ctx = DesignContext(ctrl, pkg, root)
    mod = pkg.designer_module() if pkg is not None else None
    create = getattr(mod, "create", None) if mod is not None else None
    w = None
    err = ""
    if callable(create):
        try:
            w = create(parent, dict(ctrl.props), ctx)
            if not isinstance(w, QWidget):
                err, w = "create() did not return a QWidget", None
        except Exception:  # noqa: BLE001
            err = traceback.format_exc(limit=2).strip().splitlines()[-1]
            w = None
    if w is None:
        w = ComponentPreview(parent)
        w.error = err
    w.rad_comp = True
    w.rad_comp_ctx = ctx
    w.setProperty("rad_root", str(root) if root else "")
    _design_flags(w)
    apply_component_props(w, ctrl)
    w.show()
    return w


def apply_component_props(w: QWidget, ctrl) -> None:
    p = ctrl.props
    w.setObjectName(f"rad_{ctrl.name}")
    try:
        w.setGeometry(int(p.get("Left", 0)), int(p.get("Top", 0)), max(4, int(p.get("Width", 4))),
                      max(4, int(p.get("Height", 4))))
    except (TypeError, ValueError):
        pass
    ctx = getattr(w, "rad_comp_ctx", None)
    if isinstance(w, ComponentPreview):
        w.props = dict(p)
        w.ctx = ctx
        w.error = "" if not w.error.startswith("create()") else w.error
        w.update()
    else:
        mod = ctx.package.designer_module() if ctx is not None and ctx.package is not None else None
        fn = getattr(mod, "apply", None) if mod is not None else None
        if callable(fn):
            try:
                fn(w, dict(p), ctx)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
        _design_flags(w)
    w.setToolTip(str(p.get("ToolTip", "")))
    w.setGraphicsEffect(None)
    if not p.get("Visible", True):
        eff = QGraphicsOpacityEffect(w)
        eff.setOpacity(0.4)
        w.setGraphicsEffect(eff)


__all__ = ["DesignContext", "ComponentPreview", "draw_default", "make_component_preview", "apply_component_props"]
