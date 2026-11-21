"""Mobile control catalogue, device presets and mobile form properties (docs/CONTRACTS.md 10.1 / 10.4).

The mobile controls are ordinary entries of `radide.controls.CONTROL_TYPES` (registered at the end
of radide/controls.py), so `.form` files keep the usual neutral format:
    {"type": "AppBar", "props": {"Name": "AppBar1", "Title": "Home", "Actions": "search;more_vert", ...}}

Mobile forms carry three extra form properties: `Device` (preset id from DEVICES), `Orientation`
(Portrait | Landscape) and `Route` (screen route name).  The form's Width / Height are the size of
the device's *safe area* in logical pixels (dp) for that orientation - the rectangle the designer
shows inside the phone frame, below the status bar and above the gesture / navigation bar.
Control Left / Top are relative to that safe area, exactly like a desktop form's client area.

Pure Python (no Qt) - code generators may import it without a QApplication.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..controls import EVENT_HELP, ControlType, _p
from .material_icons import icon_names

# ------------------------------------------------------------------ devices
# Device presets and the foldable geometry live in radide/devices.py (shared with the Flutter designer,
# SuperPreview and the runtimes); re-exported here so existing imports keep working.
from ..devices import (DEFAULT_DEVICE, DEFAULT_POSTURE, DEVICES, FOLDABLE_IDS, ORIENTATIONS,  # noqa: E402,F401
                       POSTURES, Device, device, display_features, effective_posture, fold_axis, hinge_rect,
                       hinge_screen_rect, is_foldable, is_separating, landscape, posture_key, posture_name,
                       postures, rect_crosses, safe_area_size, safe_insets, screen_size, segments, span, two_pane)


def form_posture(props) -> str:
    """The posture that applies to a mobile form (Flat for devices that do not fold)."""
    props = getattr(props, "props", props) or {}
    return effective_posture(props.get("Device"), props.get("Posture", DEFAULT_POSTURE))


# ------------------------------------------------------------------ form properties
MOBILE_FORM_PROPS = {p.name: p for p in [
    _p("Device", "enum", DEFAULT_DEVICE, "Phone / tablet shown around the form in the designer. The form's "
       "size is the safe area of this device.", tuple(DEVICES), category="Layout"),
    _p("Orientation", "enum", "Portrait", "Portrait or Landscape.", ORIENTATIONS, category="Layout"),
    _p("Route", "str", "", "Route name of this screen (Navigator), e.g. /details. Empty = /<FormName>.",
       category="Behavior"),
    _p("Posture", "enum", DEFAULT_POSTURE, "Foldable devices only: Flat (fully open), HalfOpened (tabletop / "
       "book, the hinge splits the screen) or Folded (the cover screen). The form's size follows it.",
       POSTURES, category="Layout"),
]}
FOLDABLE_FORM_PROPS = ("Posture",)          # shown only when the Device is a foldable
# desktop-window properties that mean nothing on a phone (hidden in the Properties window of mobile forms;
# Width / Height follow the Device)
DESKTOP_FORM_PROPS = ("Width", "Height", "StartPosition", "FormBorderStyle", "TopMost", "WindowState", "Icon",
                      "ScaleMode")


def is_mobile_plugin(plugin) -> bool:
    return bool(getattr(plugin, "is_mobile", False))


def is_mobile_form(form, plugin=None) -> bool:
    """A form is mobile when its language plugin says so (is_mobile = True) or it has a Device."""
    props = getattr(form, "props", form) or {}
    return is_mobile_plugin(plugin) or "Device" in props


def ensure_mobile_props(props: dict) -> bool:
    """Give a mobile form its Device / Orientation / Route and the matching Width / Height.
    Returns True when something changed."""
    changed = False
    for name, d in MOBILE_FORM_PROPS.items():
        if name in FOLDABLE_FORM_PROPS and not is_foldable(props.get("Device")):
            continue
        if name not in props:
            props[name] = d.default
            changed = True
    if props.get("Device") not in DEVICES:
        props["Device"] = DEFAULT_DEVICE
        changed = True
    if props.get("Orientation") not in ORIENTATIONS:
        props["Orientation"] = "Landscape" if landscape(props.get("Orientation")) else "Portrait"
        changed = True
    if is_foldable(props["Device"]) and props.get("Posture") not in POSTURES:
        props["Posture"] = posture_name(props.get("Posture"))
        changed = True
    w, h = safe_area_size(props["Device"], props["Orientation"], form_posture(props))
    if int(props.get("Width", 0) or 0) != w or int(props.get("Height", 0) or 0) != h:
        props["Width"], props["Height"] = w, h
        changed = True
    return changed


def form_prop_defs(form, plugin=None) -> list:
    """Property definitions the Properties window shows for *form* (desktop or mobile)."""
    from ..controls import FORM_PROPS
    if not is_mobile_form(form, plugin):
        return list(FORM_PROPS.values())
    props = getattr(form, "props", form) or {}
    fold = is_foldable(props.get("Device"))
    return [d for d in FORM_PROPS.values() if d.name not in DESKTOP_FORM_PROPS] +         [d for d in MOBILE_FORM_PROPS.values() if fold or d.name not in FOLDABLE_FORM_PROPS]


# ------------------------------------------------------------------ controls
ALIGNS = ("Start", "Center", "End", "Stretch", "SpaceBetween", "SpaceAround")
FITS = ("Cover", "Contain", "Fill", "FitWidth", "FitHeight", "None")
ICON_NAMES = tuple(icon_names())

EVENT_HELP.setdefault("Tap", "The user tapped the control (MListView / Drawer: e.Index = the item).")
EVENT_HELP.setdefault("Changed", "The value changed (Switch, Slider, TextField, BottomNav / TabBar index).")
EVENT_HELP.setdefault("Submitted", "The user pressed Done / Enter on the keyboard.")


# The mobile controls are built-in component packages ("mobile": true) like the desktop ones:
# radide/components/builtin/<AppBar|BottomNav|Fab|Card|MListView|Switch|MSlider|MTextField|MImage|MIcon|Drawer|
# MTabBar|MWebView|Column|Row|Stack>/component.json (docs/COMPONENTS.md). Their design-time look is drawn by
# radide/mobile/render.py (Material 3), their code by the mobile language plugins (Flutter, Kivy ...).
from ..components import builtin_mobile_types as _builtin_mobile_types  # noqa: E402

MOBILE_CONTROL_TYPES: dict[str, ControlType] = _builtin_mobile_types()

MOBILE_TYPES = tuple(MOBILE_CONTROL_TYPES)
LAYOUT_TYPES = ("Column", "Row", "Stack")

# classic controls a mobile plugin can generate too (shown in the Toolbox of mobile projects); the other
# classic controls are Windows-only and shown greyed.  A plugin may override with `supported_controls`.
MOBILE_CLASSIC = ("Button", "Label", "TextBox", "CheckBox", "RadioButton", "ComboBox", "PictureBox",
                  "ProgressBar", "Timer", "LinkLabel")


def is_mobile_type(type_name: str) -> bool:
    return type_name in MOBILE_CONTROL_TYPES


def supported_controls(plugin) -> set[str]:
    """Control types the Toolbox enables for a mobile *plugin*."""
    sup = getattr(plugin, "supported_controls", None)
    if sup:
        return set(sup)
    return set(MOBILE_TYPES) | set(MOBILE_CLASSIC)


__all__ = ["DEVICES", "DEFAULT_DEVICE", "Device", "ORIENTATIONS", "MOBILE_FORM_PROPS", "MOBILE_CONTROL_TYPES",
           "MOBILE_TYPES", "LAYOUT_TYPES", "MOBILE_CLASSIC", "ALIGNS", "FITS", "ICON_NAMES", "device",
           "screen_size", "safe_insets", "safe_area_size", "is_mobile_form", "is_mobile_plugin",
           "is_mobile_type", "ensure_mobile_props", "form_prop_defs", "supported_controls", "landscape"]
