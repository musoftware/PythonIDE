"""Mobile control catalogue, device presets and mobile form properties (docs/CONTRACTS.md 10.1 / 10.4).

The mobile controls are ordinary entries of `radide.controls.CONTROL_TYPES` (registered at the end
of radide/controls.py), so `.form` files keep the usual neutral format:
    {"type": "AppBar", "props": {"Name": "AppBar1", "Title": "Home", "Actions": "search;more_vert", ...}}

Mobile forms carry three extra form properties: `Device` (preset id from DEVICES), `Orientation`
(Portrait | Landscape) and `Route` (screen route name); forms on a foldable Device also carry `Posture`
(Flat | HalfOpened | Folded - Folded = the cover screen).  The form's Width / Height are the size of
the device's *safe area* in logical pixels (dp) for that orientation - the rectangle the designer
shows inside the phone frame, below the status bar and above the gesture / navigation bar.
Control Left / Top are relative to that safe area, exactly like a desktop form's client area.

Pure Python (no Qt) - code generators may import it without a QApplication.
"""
from __future__ import annotations

from ..controls import EVENT_HELP, ControlType, _p
from .material_icons import icon_names

# ------------------------------------------------------------------ devices
# Device presets and the foldable geometry live in radide/devices.py (shared with the Flutter designer,
# SuperPreview and the runtimes); re-exported here so existing imports keep working.
from ..devices import (DEFAULT_DEVICE, DEFAULT_POSTURE, DEVICES, FOLDABLE_IDS, ORIENTATIONS,  # noqa: E402
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

# TwoPane (foldables / large screens, docs/CONTRACTS.md 10.8) is made in code: two child containers side by
# side or one above the other, split at the hinge of a foldable or at Ratio; a narrow single screen shows
# only SinglePane.  Laid out by radide/mobile/frame.py:layout_container.
PANE_MODES = ("Auto", "Horizontal", "Vertical")
SINGLE_PANES = ("Start", "End")
EVENT_HELP.setdefault("PaneModeChanged", "TwoPane: the panes changed between one and two (e.Mode = single | "
                      "horizontal | vertical) - the device was folded / unfolded or the window resized.")
if "TwoPane" not in MOBILE_CONTROL_TYPES:
    MOBILE_CONTROL_TYPES["TwoPane"] = ControlType(
        "TwoPane", "TwoPane", (360, 400), ["PaneModeChanged"], [
            _p("PaneMode", "enum", "Auto", "Auto: side by side at the hinge of a foldable or on a wide screen "
               "(>= 600 dp), only SinglePane on a narrow single screen. Horizontal / Vertical: always two panes "
               "(side by side / one above the other).", PANE_MODES, category="Layout"),
            _p("Ratio", "float", 0.5, "Share of the first pane (0.05 - 0.95) when there is no hinge to split at.",
               category="Layout"),
            _p("SinglePane", "enum", "Start", "The pane shown when only one fits (Start = the first child "
               "container, End = the second).", SINGLE_PANES, category="Layout"),
            _p("HingeAware", "bool", True, "Split exactly at the hinge / fold of a foldable so no content sits "
               "under it.", category="Layout"),
        ], has_text=False, container=True, common_events=False, category="Mobile",
        description="Two panes for foldables and large screens: put exactly two containers (Column, Stack, "
                    "Panel ...) inside. They are split at the hinge or at Ratio; a phone shows one of them.",
        overrides=(("FontSize", 11),))

MOBILE_TYPES = tuple(MOBILE_CONTROL_TYPES)
LAYOUT_TYPES = ("Column", "Row", "Stack", "TwoPane")
# controls meant to run across the whole screen: never reported as crossing the hinge
SPAN_OK_TYPES = ("AppBar", "BottomNav", "MTabBar", "Drawer", "TwoPane")


def hinge_conflicts(form, device_id=None, orientation=None, posture=None) -> list[tuple[str, str]]:
    """[(control name, message)] for the visible non-container controls of a mobile form that lie across
    the hinge of a dual-screen device, or across the fold of a half-opened foldable (their content would be
    hidden by / bent over the hinge).  device_id / orientation / posture override the form's properties.
    Pure: works on a radide.model.Form without Qt."""
    props = getattr(form, "props", {}) or {}
    dev_id = device_id or props.get("Device")
    if not is_foldable(dev_id):
        return []
    posture = effective_posture(dev_id, posture if posture is not None else props.get("Posture", DEFAULT_POSTURE))
    if not is_separating(dev_id, posture):
        return []
    hinge = hinge_rect(dev_id, orientation or props.get("Orientation", "Portrait"), posture)
    if hinge is None:
        return []
    out = []
    what = "hinge" if device(dev_id).fold == "dual" else "fold"
    for c in getattr(form, "controls", []):
        ct = getattr(c, "ctype", None)
        if ct is None or ct.nonvisual or ct.container or c.type in SPAN_OK_TYPES:
            continue
        if not c.props.get("Visible", True):
            continue
        try:
            x, y = form.abs_pos(c)
            rect = (x, y, int(c.props.get("Width", 0) or 0), int(c.props.get("Height", 0) or 0))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if rect_crosses(rect, hinge, margin=1):
            out.append((c.name, f"{c.name} crosses the {what} of {device(dev_id).name} "
                                f"({posture}): move it to one side or put it in a TwoPane"))
    return out

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


__all__ = ["DEVICES", "DEFAULT_DEVICE", "Device", "ORIENTATIONS", "POSTURES", "MOBILE_FORM_PROPS",
           "FOLDABLE_FORM_PROPS", "PANE_MODES", "SINGLE_PANES", "SPAN_OK_TYPES", "hinge_conflicts", "hinge_rect",
           "form_posture", "is_foldable", "posture_name", "posture_key", "two_pane", "FOLDABLE_IDS",
           "display_features", "fold_axis", "hinge_screen_rect", "postures", "segments", "span",
           "effective_posture", "is_separating", "rect_crosses", "DEFAULT_POSTURE", "MOBILE_CONTROL_TYPES",
           "MOBILE_TYPES", "LAYOUT_TYPES", "MOBILE_CLASSIC", "ALIGNS", "FITS", "ICON_NAMES", "device",
           "screen_size", "safe_insets", "safe_area_size", "is_mobile_form", "is_mobile_plugin",
           "is_mobile_type", "ensure_mobile_props", "form_prop_defs", "supported_controls", "landscape"]
