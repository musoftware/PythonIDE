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
@dataclass(frozen=True)
class Device:
    id: str
    name: str
    width: int                     # portrait width in dp
    height: int                    # portrait height in dp
    platform: str                  # android | ios
    insets: tuple                  # portrait safe-area insets (left, top, right, bottom)
    land_insets: tuple             # landscape safe-area insets (left, top, right, bottom)
    radius: int = 28               # screen corner radius
    cutout: str = "punch"          # punch | island | none  (camera cut-out drawn in the status bar)
    home_button: bool = False      # iPhone SE style chin with a round home button
    tablet: bool = False


DEVICES: dict[str, Device] = {d.id: d for d in [
    Device("pixel", "Pixel / Medium phone (412 x 915)", 412, 915, "android", (0, 24, 0, 24), (0, 24, 0, 16),
           radius=34, cutout="punch"),
    Device("small_phone", "Small phone (360 x 640)", 360, 640, "android", (0, 24, 0, 48), (0, 24, 0, 48),
           radius=18, cutout="none"),
    Device("tablet", "Tablet (800 x 1280)", 800, 1280, "android", (0, 24, 0, 48), (0, 24, 0, 48),
           radius=24, cutout="none", tablet=True),
    Device("iphone_15", "iPhone 15 (393 x 852)", 393, 852, "ios", (0, 59, 0, 34), (59, 0, 59, 21),
           radius=55, cutout="island"),
    Device("iphone_se", "iPhone SE (375 x 667)", 375, 667, "ios", (0, 20, 0, 0), (0, 0, 0, 0),
           radius=0, cutout="none", home_button=True),
]}
DEFAULT_DEVICE = "pixel"
ORIENTATIONS = ("Portrait", "Landscape")


def device(device_id) -> Device:
    return DEVICES.get(str(device_id or ""), DEVICES[DEFAULT_DEVICE])


def landscape(orientation) -> bool:
    return str(orientation or "").lower().startswith("land")


def screen_size(device_id, orientation="Portrait") -> tuple[int, int]:
    """Whole screen in dp for the orientation."""
    d = device(device_id)
    return (d.height, d.width) if landscape(orientation) else (d.width, d.height)


def safe_insets(device_id, orientation="Portrait") -> tuple[int, int, int, int]:
    d = device(device_id)
    return tuple(d.land_insets if landscape(orientation) else d.insets)


def safe_area_size(device_id, orientation="Portrait") -> tuple[int, int]:
    """The form's Width / Height for a device + orientation (screen minus the safe-area insets)."""
    w, h = screen_size(device_id, orientation)
    left, top, right, bottom = safe_insets(device_id, orientation)
    return w - left - right, h - top - bottom


# ------------------------------------------------------------------ form properties
MOBILE_FORM_PROPS = {p.name: p for p in [
    _p("Device", "enum", DEFAULT_DEVICE, "Phone / tablet shown around the form in the designer. The form's "
       "size is the safe area of this device.", tuple(DEVICES), category="Layout"),
    _p("Orientation", "enum", "Portrait", "Portrait or Landscape.", ORIENTATIONS, category="Layout"),
    _p("Route", "str", "", "Route name of this screen (Navigator), e.g. /details. Empty = /<FormName>.",
       category="Behavior"),
]}
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
        if name not in props:
            props[name] = d.default
            changed = True
    if props.get("Device") not in DEVICES:
        props["Device"] = DEFAULT_DEVICE
        changed = True
    if props.get("Orientation") not in ORIENTATIONS:
        props["Orientation"] = "Landscape" if landscape(props.get("Orientation")) else "Portrait"
        changed = True
    w, h = safe_area_size(props["Device"], props["Orientation"])
    if int(props.get("Width", 0) or 0) != w or int(props.get("Height", 0) or 0) != h:
        props["Width"], props["Height"] = w, h
        changed = True
    return changed


def form_prop_defs(form, plugin=None) -> list:
    """Property definitions the Properties window shows for *form* (desktop or mobile)."""
    from ..controls import FORM_PROPS
    if not is_mobile_form(form, plugin):
        return list(FORM_PROPS.values())
    return [d for d in FORM_PROPS.values() if d.name not in DESKTOP_FORM_PROPS] + list(MOBILE_FORM_PROPS.values())


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
