"""Qt widgets used to *preview* controls on the design surface - a thin dispatcher.

Every control type draws itself: the built-in controls are component packages too
(``radide/components/builtin/<Name>/designer.py``, sharing the VB look of radide/components/classic.py), like
installed packages (radide/components/designer.py). Only these cases are routed elsewhere:

* mobile controls, and the classic ones on a phone form (radide/mobile/render.py, Material look);
* user controls (radide/usercontrols.py);
* a type registered in the legacy ``_FACTORY`` / ``_SPECIAL`` hooks (``_FACTORY[type](parent) -> QWidget``,
  ``_SPECIAL[type](widget, props, ctrl)``) - kept for old plugins; new code writes a component package.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget

from .components import REBUILD_PROPS     # properties whose change rebuilds the preview (document.py)
from .mobile.render import apply_mobile_props, make_mobile_preview, wants_mobile_preview
from .model import Control

# legacy hooks (see the module doc)
_FACTORY: dict = {}
_SPECIAL: dict = {}


def make_preview(ctrl: Control, parent: QWidget, root: Path | None = None) -> QWidget:
    if wants_mobile_preview(ctrl.type, parent):          # mobile controls / phone forms (radide/mobile)
        return make_mobile_preview(ctrl, parent, root)
    if ctrl.type in _FACTORY:
        return _make_legacy(ctrl, parent, root)
    from .usercontrols import is_user_type, make_uc_preview
    if is_user_type(ctrl.type):                         # a user control (radide/usercontrols.py)
        return make_uc_preview(ctrl, parent, root)
    # a component package - built-in or installed (radide/components): its designer.py, else the default box
    from .components.designer import make_component_preview
    return make_component_preview(ctrl, parent, root)


def apply_props(w: QWidget, ctrl: Control) -> None:
    if getattr(w, "rad_mobile", False):
        return apply_mobile_props(w, ctrl)
    if getattr(w, "rad_uc", False):                     # a user control (radide/usercontrols.py)
        from .usercontrols import apply_uc_props
        return apply_uc_props(w, ctrl)
    if getattr(w, "rad_legacy", False):
        return _apply_legacy(w, ctrl)
    from .components.designer import apply_component_props
    return apply_component_props(w, ctrl)


# ------------------------------------------------------------------ legacy _FACTORY / _SPECIAL types
def _make_legacy(ctrl: Control, parent: QWidget, root: Path | None) -> QWidget:
    from .components.classic import prepare
    w = prepare(_FACTORY[ctrl.type](parent))
    w.rad_legacy = True
    w.setProperty("rad_root", str(root) if root else "")
    _apply_legacy(w, ctrl)
    w.show()
    return w


def _apply_legacy(w: QWidget, ctrl: Control) -> None:
    from .components.classic import apply_classic
    p = ctrl.props
    w.setObjectName(f"rad_{ctrl.name}")
    w.setGeometry(int(p["Left"]), int(p["Top"]), max(4, int(p["Width"])), max(4, int(p["Height"])))
    apply_classic(w, p, ctrl, special=_SPECIAL.get(ctrl.type))
    w.setToolTip(str(p.get("ToolTip", "")))
    w.setGraphicsEffect(None)
    if not p.get("Visible", True):
        eff = QGraphicsOpacityEffect(w)
        eff.setOpacity(0.4)
        w.setGraphicsEffect(eff)


__all__ = ["REBUILD_PROPS", "apply_props", "make_preview"]
