"""Property type system of component packages (no Qt here: used by the registry, generators and runtimes).

Every property of a ``component.json`` has a ``type``. The canonical kinds (``PropDef.kind``) are:

==============  ======================  ==========================================================
kind            stored value            Properties window editor
==============  ======================  ==========================================================
str             "text"                  inline text
multiline       "line 1\\nline 2"        "..." text dialog
int             12                      inline number (``min`` / ``max``)
float           1.5                     inline number (``min`` / ``max`` / ``decimals``)
bool            true                    True / False list
enum            "Value"                 drop-down list of ``choices``
flags           "Bold, Italic"          check list of ``choices``
color           "#RRGGBB" ("" = system) colour dialog
font            "Segoe UI"              font list
image           "Resources/a.png"       file dialog (images), copied into the project
file            "data/a.csv"            file dialog (``filter``)
list            "a;b;c"                 inline text, items separated by ;
columns         "Name;Age"              "..." collection editor (one per line)
menu            [{"Text", "Name"}]      menu editor (MenuStrip / ToolStrip)
padding         "4, 4, 4, 4"            inline text (left, top, right, bottom)
anchor          "Top, Left"             VS anchor popup
alignment       "MiddleCenter"          drop-down of the 9 positions
gradient        "#FFFFFF, #000000, 90"  "..." editor (start colour, end colour, angle)
shadow          "2, 2, 6, #80000000"    "..." editor (dx, dy, blur, colour)
border          "1, solid, #808080, 4"  "..." editor (width, style, colour, radius)
dbref           "Source.Column"         data binding list (Data Sources window)
event           "Handler"               handler name (text)
custom          anything JSON           the package's own editor (``editor`` id)
==============  ======================  ==========================================================

Aliases accepted in manifests: string, text -> str; integer -> int; number, double -> float; boolean -> bool;
items -> list; margins -> padding; binding, databinding -> dbref; resource -> image; path -> file;
dock -> enum with the Dock choices; handler -> event.
"""
from __future__ import annotations

import re

ALIASES = {"string": "str", "text": "str", "integer": "int", "number": "float", "double": "float",
           "boolean": "bool", "items": "list", "margins": "padding", "margin": "padding", "binding": "dbref",
           "databinding": "dbref", "resource": "image", "path": "file", "handler": "event", "colour": "color"}
KINDS = ("str", "multiline", "int", "float", "bool", "enum", "flags", "color", "font", "image", "file", "list",
         "columns", "menu", "padding", "anchor", "alignment", "gradient", "shadow", "border", "dbref", "event",
         "custom")
ALIGNMENTS = ("TopLeft", "TopCenter", "TopRight", "MiddleLeft", "MiddleCenter", "MiddleRight",
              "BottomLeft", "BottomCenter", "BottomRight")
DOCKS = ("None", "Top", "Bottom", "Left", "Right", "Fill")
BORDER_STYLES = ("none", "solid", "dashed", "dotted", "double")

GENERIC_HELP = {
    "multiline": "Text of several lines: click ... to edit it.",
    "float": "A number (decimals allowed).",
    "flags": "Any combination of the listed values: click to choose.",
    "image": "An image file of the project: click ... to choose it.",
    "columns": "Column headers: click ... to edit the list.",
    "padding": "Left, Top, Right, Bottom in pixels (one number = the same on every side).",
    "alignment": "Where the content sits inside the control.",
    "gradient": "Background gradient: start colour, end colour, angle in degrees (empty = none).",
    "shadow": "Drop shadow: X offset, Y offset, blur radius, colour (empty = none).",
    "border": "Border: width, style (solid, dashed, dotted, double, none), colour, corner radius.",
    "event": "The name of an event handler.",
    "custom": "Click to edit the value with the component's own editor.",
}

# value type each kind stores in the .form JSON (for validation of defaults)
_PY_TYPES = {"int": (int,), "float": (int, float), "bool": (bool,), "menu": (list,)}


def normalize(kind) -> str:
    k = str(kind or "str").strip()
    k = ALIASES.get(k.lower(), k if k in KINDS else k.lower())
    return k if k in KINDS else ("enum" if k == "dock" else k)


def is_known(kind) -> bool:
    k = str(kind or "").strip().lower()
    return normalize(k) in KINDS or k == "dock"


def default_for(kind: str):
    k = normalize(kind)
    if k == "int":
        return 0
    if k == "float":
        return 0.0
    if k == "bool":
        return False
    if k == "menu":
        return []
    if k == "alignment":
        return "MiddleLeft"
    if k == "anchor":
        return "Top, Left"
    return ""


def check_default(kind: str, value) -> bool:
    """True when *value* has the JSON type the kind stores."""
    k = normalize(kind)
    if k in _PY_TYPES:
        if k in ("int", "float") and isinstance(value, bool):
            return False
        return isinstance(value, _PY_TYPES[k])
    if k == "custom":
        return True
    return isinstance(value, str)


def number_text(value) -> str:
    """A number typed with the user's locale habits as Python reads it: Arabic decimal separator (U+066B) and
    a single decimal comma ("0,5" on Arabic / German / Turkish Windows) become ".", Arabic thousands
    separators (U+066C), no-break / thin spaces and Unicode minus signs are handled. Arabic-Indic digits are
    read by int() / float() themselves."""
    t = str(value).strip().replace("٫", ".").replace("٬", "").replace("−", "-")
    t = t.replace(" ", "").replace(" ", "").replace(" ", "").replace("‏", "").replace("‎", "")
    if "," in t and "." not in t and t.count(",") == 1:
        t = t.replace(",", ".")
    return t


def coerce(kind: str, value, choices=()):
    """*value* converted to what *kind* stores (text typed in the Properties window, JSON from a manifest)."""
    k = normalize(kind)
    if k == "int":
        try:
            return int(float(number_text(value)))
        except (TypeError, ValueError):
            raise ValueError(f"{value!r} is not a whole number") from None
    if k == "float":
        try:
            return float(number_text(value))
        except (TypeError, ValueError):
            raise ValueError(f"{value!r} is not a number") from None
    if k == "bool":
        return value if isinstance(value, bool) else str(value).strip().lower() in ("1", "true", "yes", "on")
    if k == "enum" and choices and str(value) not in choices:
        raise ValueError(f"{value!r} is not one of {', '.join(choices)}")
    if k == "flags":
        return format_flags(parse_flags(value, choices))
    if k == "padding":
        return format_padding(parse_padding(value))
    if k in ("menu", "custom"):
        return value
    return "" if value is None else str(value)


# ------------------------------------------------------------------ structured values
def parse_flags(value, choices=()) -> list[str]:
    words = [w.strip() for w in re.split(r"[,|;]", str(value or "")) if w.strip()]
    if choices:                       # in the order of the choices, known values only
        on = {w.lower() for w in words}
        return [c for c in choices if c.lower() in on]
    return words


def format_flags(flags) -> str:
    return ", ".join(flags)


def parse_padding(value) -> tuple[int, int, int, int]:
    """'4' -> (4, 4, 4, 4); '4, 8' -> (4, 8, 4, 8); 'l, t, r, b'."""
    nums = []
    for w in re.split(r"[,\s]+", str(value or "").strip()):
        if w:
            try:
                nums.append(int(float(w)))
            except ValueError:
                raise ValueError(f"{value!r}: use numbers like 4, 4, 4, 4") from None
    if not nums:
        return (0, 0, 0, 0)
    if len(nums) == 1:
        return (nums[0],) * 4
    if len(nums) == 2:
        return (nums[0], nums[1], nums[0], nums[1])
    if len(nums) == 3:
        return (nums[0], nums[1], nums[2], nums[1])
    return tuple(nums[:4])


def format_padding(p) -> str:
    return ", ".join(str(int(x)) for x in p)


def parse_alignment(value) -> tuple[str, str]:
    """'MiddleCenter' -> ('middle', 'center')  (vertical, horizontal)."""
    v = str(value or "MiddleLeft")
    m = re.match(r"(Top|Middle|Bottom)(Left|Center|Right)$", v)
    return (m.group(1).lower(), m.group(2).lower()) if m else ("middle", "left")


def parse_gradient(value) -> dict | None:
    """'#FFFFFF, #000000, 90' -> {"start", "end", "angle"}; '' -> None."""
    parts = [p.strip() for p in str(value or "").split(",") if p.strip()]
    if len(parts) < 2:
        return None
    try:
        angle = float(parts[2]) if len(parts) > 2 else 90.0
    except ValueError:
        angle = 90.0
    return {"start": parts[0], "end": parts[1], "angle": angle}


def format_gradient(start: str, end: str, angle: float = 90) -> str:
    return f"{start}, {end}, {int(angle) if float(angle).is_integer() else angle}" if start and end else ""


def parse_shadow(value) -> dict | None:
    parts = [p.strip() for p in str(value or "").split(",") if p.strip()]
    if len(parts) < 3:
        return None
    try:
        dx, dy, blur = int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
    except ValueError:
        return None
    return {"dx": dx, "dy": dy, "blur": blur, "color": parts[3] if len(parts) > 3 else "#80000000"}


def format_shadow(dx: int, dy: int, blur: int, color: str) -> str:
    return f"{int(dx)}, {int(dy)}, {int(blur)}, {color}"


def parse_border(value) -> dict | None:
    parts = [p.strip() for p in str(value or "").split(",") if p.strip()]
    if not parts:
        return None
    try:
        width = int(float(parts[0]))
    except ValueError:
        return None
    style = parts[1].lower() if len(parts) > 1 and parts[1].lower() in BORDER_STYLES else "solid"
    color = parts[2] if len(parts) > 2 else "#808080"
    try:
        radius = int(float(parts[3])) if len(parts) > 3 else 0
    except ValueError:
        radius = 0
    return {"width": width, "style": style, "color": color, "radius": radius}


def format_border(width: int, style: str, color: str, radius: int = 0) -> str:
    return f"{int(width)}, {style}, {color}, {int(radius)}"


def text_of(kind: str, value) -> str:
    """How the Properties window shows a value."""
    k = normalize(kind)
    if k == "bool":
        return "True" if value else "False"
    if k == "multiline":
        first = str(value or "").split("\n", 1)[0]
        return first + (" ..." if "\n" in str(value or "") else "")
    if k == "menu":
        return "(Collection)"
    if k == "custom" and not isinstance(value, str):
        import json
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


__all__ = ["KINDS", "ALIASES", "ALIGNMENTS", "DOCKS", "BORDER_STYLES", "GENERIC_HELP", "normalize", "is_known",
           "default_for", "check_default", "coerce", "parse_flags", "format_flags", "parse_padding",
           "format_padding", "parse_alignment", "parse_gradient", "format_gradient", "parse_shadow",
           "format_shadow", "parse_border", "format_border", "text_of"]
