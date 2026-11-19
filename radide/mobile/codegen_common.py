"""Helpers shared by the mobile code generators (Flutter / Kivy) - CONTRACTS 10.1 / 10.4.

The mobile control types themselves are defined by ``radide.mobile.controls`` (owner mobile-designer).
``ensure_types()`` imports that module (it registers the types in ``radide.controls.CONTROL_TYPES``) and,
only for names still missing, registers minimal stand-ins so that .form files with mobile controls can
always be loaded and generated (e.g. by the command line tests or before the designer part is present).
"""
from __future__ import annotations

import re

from ..controls import CONTROL_TYPES, ControlType, split_items
from ..controls import _p as _prop

MOBILE_TYPES = ("AppBar", "BottomNav", "Fab", "Card", "MListView", "Switch", "MSlider", "MTextField",
                "MImage", "MIcon", "Drawer", "MTabBar", "MWebView", "Column", "Row", "Stack")
CONTAINER_TYPES = ("Card", "Column", "Row", "Stack", "Panel", "GroupBox")
# events the generators can wire (anything else listed by a control type is ignored)
CLICK_EVENTS = ("Click", "Tap", "DoubleClick", "LongPress")
CHANGE_EVENTS = ("Changed", "TextChanged", "CheckedChanged", "ValueChanged", "SelectedIndexChanged")
SUBMIT_EVENTS = ("Submitted",)
SUPPORTED_EVENTS = CLICK_EVENTS + CHANGE_EVENTS + SUBMIT_EVENTS + ("Tick",)


def _fallback_types() -> list[ControlType]:
    p = _prop
    layout = [p("Spacing", "int", 8, "Space between the children.", category="Layout"),
              p("Align", "enum", "Start", "How the children are aligned.",
                ("Start", "Center", "End", "Stretch", "SpaceBetween"), category="Layout"),
              p("Padding", "int", 8, "Space inside the container.", category="Layout")]
    return [
        ControlType("AppBar", "AppBar", (360, 56), ["Click"],
                    [p("Title", "str", "My App", category="Appearance"),
                     p("Actions", "list", "", "Action names separated by ; (Material icon names show icons).",
                       category="Data")], common_events=False, description="Title bar of a screen."),
        ControlType("BottomNav", "BottomNav", (360, 64), ["Changed"],
                    [p("Items", "list", "Home;Search;Profile", category="Data"),
                     p("SelectedIndex", "int", 0, category="Behavior")], has_text=False, common_events=False,
                    description="Navigation bar at the bottom of a screen."),
        ControlType("Fab", "Fab", (56, 56), ["Click"], [p("Icon", "str", "add", category="Appearance")],
                    common_events=False, description="Floating action button."),
        ControlType("Card", "Card", (300, 150), ["Click"], [p("Elevation", "int", 2, category="Appearance")],
                    has_text=False, container=True, common_events=False, description="A raised card."),
        ControlType("MListView", "ListView", (300, 240), ["Tap"],
                    [p("Items", "list", "Item 1;Item 2;Item 3", category="Data"),
                     p("ItemTemplate", "str", "title", "Fields of an item separated by | "
                       "(title|subtitle|icon|trailing).", category="Data")], has_text=False,
                    common_events=False, description="A scrolling list."),
        ControlType("Switch", "Switch", (200, 40), ["Changed"], [p("Checked", "bool", False, category="Behavior")],
                    common_events=False, description="An on/off switch."),
        ControlType("MSlider", "Slider", (240, 40), ["Changed"],
                    [p("Minimum", "int", 0, category="Behavior"), p("Maximum", "int", 100, category="Behavior"),
                     p("Value", "int", 50, category="Behavior")], has_text=False, common_events=False),
        ControlType("MTextField", "TextField", (280, 56), ["Changed", "Submitted"],
                    [p("Hint", "str", "", category="Appearance"), p("Password", "bool", False, category="Behavior")],
                    common_events=False, description="A text entry field."),
        ControlType("MImage", "Image", (160, 120), ["Click"],
                    [p("Image", "file", "", category="Appearance"),
                     p("Fit", "enum", "Contain", choices=("Contain", "Cover", "Fill", "None"),
                       category="Appearance")], has_text=False, common_events=False),
        ControlType("MIcon", "Icon", (32, 32), ["Click"], [p("Icon", "str", "star", category="Appearance")],
                    has_text=False, common_events=False),
        ControlType("Drawer", "Drawer", (240, 40), ["Click"], [p("Items", "list", "Home;Settings;About",
                                                                  category="Data")],
                    common_events=False, description="Side menu opened from the app bar."),
        ControlType("MTabBar", "TabBar", (360, 48), ["Changed"],
                    [p("Tabs", "list", "Tab 1;Tab 2;Tab 3", category="Data"),
                     p("SelectedIndex", "int", 0, category="Behavior")], has_text=False, common_events=False),
        ControlType("MWebView", "WebView", (320, 240), [], [p("Url", "str", "https://flutter.dev",
                                                             category="Behavior")],
                    has_text=False, common_events=False),
        ControlType("Column", "Column", (300, 200), [], layout, has_text=False, container=True,
                    common_events=False),
        ControlType("Row", "Row", (300, 60), [], layout, has_text=False, container=True, common_events=False),
        ControlType("Stack", "Stack", (300, 200), [], layout, has_text=False, container=True,
                    common_events=False),
    ]


def ensure_types() -> None:
    """Make sure every mobile control type of CONTRACTS 10.4 is in CONTROL_TYPES."""
    try:
        import importlib
        importlib.import_module(f"{__package__}.controls")      # registers the real types
    except Exception:  # noqa: BLE001 - not there yet / broken: use the stand-ins
        pass
    for t in _fallback_types():
        CONTROL_TYPES.setdefault(t.name, t)


# ------------------------------------------------------------------ values
NAMED_COLORS = {
    "black": "000000", "white": "FFFFFF", "red": "F44336", "green": "4CAF50", "blue": "2196F3",
    "yellow": "FFEB3B", "orange": "FF9800", "purple": "9C27B0", "pink": "E91E63", "grey": "9E9E9E",
    "gray": "9E9E9E", "teal": "009688", "indigo": "3F51B5", "cyan": "00BCD4", "brown": "795548",
    "amber": "FFC107", "lime": "CDDC39", "transparent": "",
}


def color_hex(value) -> str | None:
    """'#RRGGBB' / '#AARRGGBB' / 'red' -> 'AARRGGBB' (None when empty or unknown)."""
    s = str(value or "").strip()
    if not s:
        return None
    if s.lower() in NAMED_COLORS:
        h = NAMED_COLORS[s.lower()]
        return ("FF" + h) if h else "00000000"
    m = re.fullmatch(r"#?([0-9a-fA-F]{6}|[0-9a-fA-F]{8}|[0-9a-fA-F]{3})", s)
    if not m:
        return None
    h = m.group(1).upper()
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return h if len(h) == 8 else "FF" + h


def items(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return split_items(value or "")


def num(value, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def font_px(props: dict) -> float | None:
    """Designer font points -> logical pixels (96 dpi): 9 pt -> 12 px."""
    size = num(props.get("FontSize"), 0)
    return round(size * 4 / 3, 1) if size > 0 else None


def align_word(value) -> str:
    s = str(value or "").lower()
    if "between" in s:
        return "between"
    if "around" in s:
        return "around"
    if "stretch" in s or "fill" in s:
        return "stretch"
    if "center" in s or "middle" in s:
        return "center"
    if "end" in s or "right" in s or "bottom" in s:
        return "end"
    return "start"


def snake(name: str) -> str:
    """'MainScreen' -> 'main_screen' (Dart file names / package names)."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    s = re.sub(r"\W+", "_", s).strip("_").lower()
    if not s or not s[0].isalpha():
        s = "app_" + s
    return s


def form_children(form, parent: str) -> list:
    """Visible-type controls directly inside *parent* ("" = the form), in z-order."""
    return [c for c in form.controls
            if not c.ctype.nonvisual and (c.props.get("Parent") or "") == parent]


ICON_SYNONYMS = {"profile": "person", "account": "person", "user": "person", "me": "person",
                 "favorites": "favorite", "favourites": "favorite", "likes": "favorite",
                 "cart": "shopping_cart", "shop": "store", "messages": "message", "chat": "chat",
                 "about": "info", "help": "help", "contacts": "contacts", "photos": "photo",
                 "camera": "camera_alt", "music": "music_note", "videos": "videocam", "news": "article",
                 "calendar": "calendar_today", "logout": "logout", "login": "login", "add": "add",
                 "new": "add", "delete": "delete", "edit": "edit", "save": "save", "share": "share",
                 "back": "arrow_back", "next": "arrow_forward", "list": "list", "map": "map",
                 "notifications": "notifications", "alerts": "notifications", "tasks": "task_alt",
                 "dashboard": "dashboard", "explore": "explore", "library": "library_books"}


def icon_key(text: str) -> str:
    """'Shopping Cart' -> 'shopping_cart'; synonyms (Profile -> person) applied."""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(text or "").strip()).strip("_").lower()
    return ICON_SYNONYMS.get(s, s)
