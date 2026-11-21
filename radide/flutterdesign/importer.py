"""Flutter designer import: hand-written Dart widget code -> *.fscreen.json trees (docs/FLUTTER_DESIGNER.md 5).

A small Dart CLI built on package:analyzer (dart_tools/bin/fsimport.dart) parses the file and prints a JSON
expression tree; this module maps it onto the catalog. Whatever it cannot model is kept verbatim: widget
expressions become "Code" nodes (with designable children in #{slot:...} holes), property values become
{"$code": ...}. The CLI is compiled once with the Flutter SDK (``dart compile exe``) into
%LOCALAPPDATA%\\RADIDE\\cache\\flutterdesign and rebuilt when its source changes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

from . import model as M

TOOL_DIR = Path(__file__).with_name("dart_tools")
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# =============================================================================== the Dart CLI
def _dart() -> str:
    try:
        from ..languages.flutter import dart_exe
        return dart_exe()
    except Exception:  # noqa: BLE001
        return shutil.which("dart") or ""


def cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "RADIDE" / "cache" / "flutterdesign"


def _tool_hash() -> str:
    h = hashlib.sha1()
    for rel in ("pubspec.yaml", "bin/fsimport.dart"):
        h.update((TOOL_DIR / rel).read_bytes())
    return h.hexdigest()[:12]


def tool_path() -> Path:
    return cache_dir() / f"fsimport-{_tool_hash()}{'.exe' if os.name == 'nt' else ''}"


def tool_status() -> str:
    """'ready', 'buildable' (dart found, not compiled yet) or 'no-dart'."""
    if tool_path().exists():
        return "ready"
    return "buildable" if _dart() else "no-dart"


def ensure_tool(log=None) -> Path:
    """Compile the importer CLI when needed; returns the executable. Raises RuntimeError on failure."""
    exe = tool_path()
    if exe.exists():
        return exe
    dart = _dart()
    if not dart:
        raise RuntimeError("The Dart SDK was not found (install Flutter: the importer needs its dart).")
    work = cache_dir() / "src"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    (work / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(TOOL_DIR / "pubspec.yaml", work / "pubspec.yaml")
    shutil.copy2(TOOL_DIR / "bin" / "fsimport.dart", work / "bin" / "fsimport.dart")
    out = ""
    ok = False
    for args in (["pub", "get", "--offline"], ["pub", "get"]):
        r = subprocess.run([dart, *args], cwd=str(work), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600, creationflags=_NOWIN)
        out += (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            ok = True
            break
    if not ok:
        raise RuntimeError("dart pub get failed for the importer:\n" + out[-2000:])
    if log:
        log("Compiling the Dart importer (once)...")
    tmp = exe.with_suffix(".tmp" + exe.suffix)
    r = subprocess.run([dart, "compile", "exe", "bin/fsimport.dart", "-o", str(tmp)], cwd=str(work),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
                       creationflags=_NOWIN)
    if r.returncode != 0 or not tmp.exists():
        raise RuntimeError("dart compile failed for the importer:\n" + ((r.stdout or "") + (r.stderr or ""))[-3000:])
    for old in cache_dir().glob("fsimport-*"):
        if old.is_file() and old != tmp:
            try:
                old.unlink()
            except OSError:
                pass
    tmp.replace(exe)
    return exe


def parse_dart(source: str, expr: bool = False) -> dict:
    """Run the CLI on *source* (a file's text, or one expression with expr=True) -> its JSON."""
    exe = ensure_tool()
    r = subprocess.run([str(exe), "--expr" if expr else "--stdin"], input=source.encode("utf-8"),
                       capture_output=True, timeout=120, creationflags=_NOWIN)
    if r.returncode != 0:
        raise RuntimeError("the Dart importer failed: " + r.stderr.decode("utf-8", "replace")[-2000:])
    return json.loads(r.stdout.decode("utf-8"))


# ================================================================================ results
@dataclass
class ImportResult:
    screens: list = field(default_factory=list)       # screen dicts (*.fscreen.json content)
    report: list = field(default_factory=list)        # (level, text): info / warning / error
    stats: dict = field(default_factory=dict)         # exact widgets / Code nodes / $code props per screen


# Material colour names (Colors.x) are kept by name; only literal colours become #AARRGGBB.
_HELPER_ANIMS = {
    # name -> anim type (animate_do style widgets: FadeInUp(delay: ..., duration: ..., child: ...))
    "FadeIn": "fadeIn", "FadeInUp": "fadeInUp", "FadeInDown": "fadeInDown", "FadeInLeft": "fadeInLeft",
    "FadeInRight": "fadeInRight", "SlideInUp": "slideUp", "SlideInDown": "slideDown",
    "SlideInLeft": "slideRight", "SlideInRight": "slideLeft", "ZoomIn": "zoomIn", "BounceIn": "bounceIn",
    "BounceInUp": "bounceIn", "BounceInDown": "bounceIn",
}


_HELPER_IMPORTS = {r"^package:animate_do/": set(_HELPER_ANIMS), r"(^|/)fade_?animation\.dart$|FadeAnimation\.dart$":
                   {"FadeAnimation"}}


class _Ctx:
    def __init__(self, source: str):
        self.src = source
        self.exact = 0
        self.code_nodes: list[str] = []
        self.code_props: list[str] = []
        self.anim_helpers: set[str] = set()
        self.fonts: set[str] = set()
        self.assets: set[str] = set()
        self.fields: dict[str, dict] = {}      # State fields: name -> {"type", "init": expr json}
        self.handlers: set[str] = set()
        self.bound: set[str] = set()
        self.dropped_imports: list[str] = []           # State fields wired to widgets (generated again)
        self.methods: set[str] = set()

        # the Dart CLI reports UTF-16 offsets: slice in UTF-16 when the text has non-BMP characters
        self.u16 = source.encode("utf-16-le") if any(ord(c) > 0xFFFF for c in source) else None

    def slice(self, o: int, e: int) -> str:
        if self.u16 is not None:
            return self.u16[o * 2:e * 2].decode("utf-16-le", "replace")
        return self.src[o:e]

    def s(self, e: dict | None) -> str:
        if not e:
            return ""
        return self.slice(e["o"], e["e"])


class Unsupported(Exception):
    pass


def _ws(s: str) -> str:
    return " ".join(s.split())


def _tight(s: str) -> str:
    """Whitespace-collapsed code without spaces inside brackets and without trailing commas (for matching)."""
    s = _ws(s)
    s = re.sub(r",\s*([)\]}])", r"\1", s)
    s = re.sub(r"([(\[])\s+", r"\1", s)
    return re.sub(r"\s+([)\]])", r"\1", s)


# ============================================================================== value parsing
def _num(e: dict, ctx: _Ctx):
    k = e.get("k")
    if k in ("int", "dbl"):
        return e["v"]
    if k == "id" and e["s"] == "double.infinity":
        return "infinity"
    raise Unsupported


def _str(e: dict, ctx: _Ctx):
    if e.get("k") == "str":
        return e["v"]
    raise Unsupported


def _bool(e: dict, ctx: _Ctx):
    if e.get("k") == "bool":
        return e["v"]
    raise Unsupported


def _hex(v: int) -> str:
    return "#%08X" % (v & 0xFFFFFFFF)


def _color(e: dict, ctx: _Ctx):
    k = e.get("k")
    if k == "call" and e.get("callee") in ("Color", "ui.Color") and len(e["p"]) == 1 and e["p"][0]["k"] == "int":
        return _hex(e["p"][0]["v"])
    if k == "call" and e.get("callee") in ("Color.fromRGBO", "Color.fromARGB") and len(e["p"]) == 4:
        vals = [_num(a, ctx) for a in e["p"]]
        if e["callee"] == "Color.fromRGBO":
            r, g, b, o = vals
            a = int(round(float(o) * 255))
        else:
            a, r, g, b = vals
        return _hex((int(a) << 24) | (int(r) << 16) | (int(g) << 8) | int(b))
    if k == "id":
        s = e["s"]
        if re.match(r"^(Colors|CupertinoColors)\.\w+$", s):
            return s
        if re.match(r"^Colors\.\w+\.shade\d+$", s):
            return s
    if k == "index" and e["tgt"].get("k") == "id" and re.match(r"^Colors\.\w+$", e["tgt"]["s"]) \
            and e["i"].get("k") == "int":
        return f"{e['tgt']['s']}.shade{e['i']['v']}"
    if k == "prop":
        m = re.match(r"^Theme\.of\(\s*context\s*\)\.colorScheme\.(\w+)$", _ws(ctx.s(e)).replace(" ", ""))
        if m:
            return "scheme." + m.group(1)
    raise Unsupported


def _enum_parser(enum: str):
    def p(e: dict, ctx: _Ctx):
        if e.get("k") == "id" and e["s"].startswith(enum + ".") and e["s"].split(".", 1)[1] in M.ENUMS[enum]:
            return e["s"]
        raise Unsupported
    return p


def _named(e: dict) -> dict:
    return e.get("a") or {}


def _call(e: dict, *callees) -> bool:
    return e.get("k") == "call" and e.get("callee") in callees


def _edge(e: dict, ctx: _Ctx):
    if e.get("k") == "id" and e["s"] == "EdgeInsets.zero":
        return {"all": 0}
    if _call(e, "EdgeInsets.all") and len(e["p"]) == 1:
        return {"all": _num(e["p"][0], ctx)}
    if _call(e, "EdgeInsets.symmetric"):
        a = _named(e)
        out = {}
        if "horizontal" in a:
            out["h"] = _num(a["horizontal"], ctx)
        if "vertical" in a:
            out["v"] = _num(a["vertical"], ctx)
        if set(a) - {"horizontal", "vertical"}:
            raise Unsupported
        return out or {"all": 0}
    if _call(e, "EdgeInsets.only"):
        a = _named(e)
        keys = {"left": "l", "top": "t", "right": "r", "bottom": "b"}
        if set(a) - set(keys):
            raise Unsupported
        return {keys[k]: _num(v, ctx) for k, v in a.items()} or {"all": 0}
    if _call(e, "EdgeInsets.fromLTRB") and len(e["p"]) == 4:
        vals = [_num(a, ctx) for a in e["p"]]
        return {k: v for k, v in zip("ltrb", vals) if v}
    raise Unsupported


def _radius_value(e: dict, ctx: _Ctx):
    if _call(e, "Radius.circular") and len(e["p"]) == 1:
        return _num(e["p"][0], ctx)
    if e.get("k") == "id" and e["s"] == "Radius.zero":
        return 0
    raise Unsupported


def _radius(e: dict, ctx: _Ctx):
    if _call(e, "BorderRadius.circular") and len(e["p"]) == 1:
        return _num(e["p"][0], ctx)
    if _call(e, "BorderRadius.all") and len(e["p"]) == 1:
        return _radius_value(e["p"][0], ctx)
    if e.get("k") == "id" and e["s"] == "BorderRadius.zero":
        return 0
    if _call(e, "BorderRadius.only"):
        keys = {"topLeft": "tl", "topRight": "tr", "bottomLeft": "bl", "bottomRight": "br"}
        a = _named(e)
        if set(a) - set(keys):
            raise Unsupported
        return {keys[k]: _radius_value(v, ctx) for k, v in a.items()}
    if _call(e, "BorderRadius.vertical"):
        a = _named(e)
        out = {}
        if "top" in a:
            out["tl"] = out["tr"] = _radius_value(a["top"], ctx)
        if "bottom" in a:
            out["bl"] = out["br"] = _radius_value(a["bottom"], ctx)
        return out
    raise Unsupported


def _alignment(e: dict, ctx: _Ctx):
    if e.get("k") == "id" and re.match(r"^Alignment(Directional)?\.\w+$", e["s"]):
        name = e["s"].split(".", 1)[1]
        name = {"topStart": "topLeft", "topEnd": "topRight", "centerStart": "centerLeft", "centerEnd": "centerRight",
                "bottomStart": "bottomLeft", "bottomEnd": "bottomRight"}.get(name, name)
        if name in M.ENUMS["Alignment"]:
            return f"Alignment.{name}"
    if _call(e, "Alignment") and len(e["p"]) == 2:
        return {"x": _num(e["p"][0], ctx), "y": _num(e["p"][1], ctx)}
    raise Unsupported


def _icon(e: dict, ctx: _Ctx):
    if e.get("k") == "id" and re.match(r"^(Icons|CupertinoIcons)\.\w+$", e["s"]):
        return e["s"]
    raise Unsupported


def _icon_widget(e: dict, ctx: _Ctx):
    if _call(e, "Icon") and len(e["p"]) == 1 and not _named(e):
        return _icon(e["p"][0], ctx)
    raise Unsupported


def _offset(e: dict, ctx: _Ctx):
    if _call(e, "Offset") and len(e["p"]) == 2:
        return [_num(e["p"][0], ctx), _num(e["p"][1], ctx)]
    if e.get("k") == "id" and e["s"] == "Offset.zero":
        return [0, 0]
    raise Unsupported


def _duration(e: dict, ctx: _Ctx):
    if _call(e, "Duration") and not e["p"]:
        mult = {"milliseconds": 1, "seconds": 1000, "minutes": 60000, "microseconds": 0.001}
        a = _named(e)
        if set(a) - set(mult):
            raise Unsupported
        total = sum(_num(v, ctx) * mult[k] for k, v in a.items())
        return int(round(total))
    raise Unsupported


def _string_list(e: dict, ctx: _Ctx):
    if e.get("k") == "list":
        return [_str(i, ctx) for i in e["items"]]
    raise Unsupported


def _image(e: dict, ctx: _Ctx):
    if _call(e, "AssetImage") and len(e["p"]) == 1 and not _named(e):
        src = _str(e["p"][0], ctx)
        ctx.assets.add(src)
        return {"source": "asset", "src": src}
    if _call(e, "NetworkImage") and len(e["p"]) == 1 and not _named(e):
        return {"source": "network", "src": _str(e["p"][0], ctx)}
    raise Unsupported


def _soft(parser, e: dict, ctx: _Ctx, label: str = ""):
    """A nested value: parsed, or {"$code": src} for just that part (the rest stays designable)."""
    try:
        return parser(e, ctx)
    except (Unsupported, KeyError, TypeError, ValueError):
        ctx.code_props.append(f"{label}: {_ws(ctx.s(e))[:80]}")
        return {"$code": ctx.s(e)}


def _list_of(parser):
    def p(e: dict, ctx: _Ctx):
        if e.get("k") != "list":
            raise Unsupported
        return [_soft(parser, i, ctx, "list item") for i in e["items"]]
    return p


def _gradient(e: dict, ctx: _Ctx):
    kinds = {"LinearGradient": "linear", "RadialGradient": "radial", "SweepGradient": "sweep"}
    if e.get("k") != "call" or e.get("callee") not in kinds or e["p"]:
        raise Unsupported
    out = {"type": kinds[e["callee"]]}
    fields = {"begin": _alignment, "end": _alignment, "center": _alignment, "radius": _num, "startAngle": _num,
              "endAngle": _num, "colors": _list_of(_color), "stops": _list_of(_num)}
    for k, v in _named(e).items():
        if k not in fields:
            raise Unsupported
        out[k] = _soft(fields[k], v, ctx, f"{e['callee']}.{k}")
    return out


def _shadows(e: dict, ctx: _Ctx):
    if e.get("k") != "list":
        raise Unsupported
    out = []
    for it in e["items"]:
        if not _call(it, "BoxShadow") or it["p"]:
            raise Unsupported
        s = {}
        keys = {"color": ("color", _color), "blurRadius": ("blur", _num), "spreadRadius": ("spread", _num),
                "offset": ("offset", _offset)}
        for k, v in _named(it).items():
            if k not in keys:
                raise Unsupported
            s[keys[k][0]] = keys[k][1](v, ctx)
        out.append(s)
    return out


def _side(e: dict, ctx: _Ctx):
    if _call(e, "BorderSide") and not e["p"]:
        out = {}
        for k, v in _named(e).items():
            if k == "color":
                out["color"] = _color(v, ctx)
            elif k == "width":
                out["width"] = _num(v, ctx)
            else:
                raise Unsupported
        return out
    if e.get("k") == "id" and e["s"] == "BorderSide.none":
        return {"width": 0}
    raise Unsupported


def _border(e: dict, ctx: _Ctx):
    if _call(e, "Border.all") and not e["p"]:
        out = {}
        for k, v in _named(e).items():
            if k == "color":
                out["color"] = _color(v, ctx)
            elif k == "width":
                out["width"] = _num(v, ctx)
            else:
                raise Unsupported
        return out
    if _call(e, "Border") and not e["p"]:
        a = _named(e)
        if set(a) - {"top", "right", "bottom", "left"}:
            raise Unsupported
        return {k: _side(v, ctx) for k, v in a.items()}
    raise Unsupported


def _decoration_image(e: dict, ctx: _Ctx):
    if not _call(e, "DecorationImage") or e["p"]:
        raise Unsupported
    a = _named(e)
    if "image" not in a or set(a) - {"image", "fit", "alignment", "opacity"}:
        raise Unsupported
    out = dict(_image(a["image"], ctx))
    if "fit" in a:
        out["fit"] = _enum_parser("BoxFit")(a["fit"], ctx)
    if "alignment" in a:
        out["alignment"] = _alignment(a["alignment"], ctx)
    if "opacity" in a:
        out["opacity"] = _num(a["opacity"], ctx)
    return out


def _decoration(e: dict, ctx: _Ctx):
    if not _call(e, "BoxDecoration") or e["p"]:
        raise Unsupported
    fields = {"color": _color, "image": _decoration_image, "border": _border, "borderRadius": _radius,
              "boxShadow": _shadows, "gradient": _gradient, "shape": _enum_parser("BoxShape")}
    return _fields(e, fields, ctx)


def _fields(e: dict, fields: dict, ctx: _Ctx, rename: dict | None = None) -> dict:
    out = {}
    for k, v in _named(e).items():
        if k not in fields:
            raise Unsupported
        out[(rename or {}).get(k, k)] = _soft(fields[k], v, ctx, f"{e.get('callee')}.{k}")
    return out


def _google_name(method: str) -> str:
    """GoogleFonts.openSans -> 'Open Sans', GoogleFonts.robotoMono -> 'Roboto Mono'."""
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", method)
    return " ".join(p[:1].upper() + p[1:] for p in parts)


_TEXT_FIELDS = {"color": _color, "backgroundColor": _color, "fontSize": _num,
                "fontWeight": _enum_parser("FontWeight"), "fontStyle": _enum_parser("FontStyle"),
                "letterSpacing": _num, "wordSpacing": _num, "height": _num,
                "decoration": _enum_parser("TextDecoration"), "decorationColor": _color,
                "decorationThickness": _num, "fontFamily": _str}


def _text_style(e: dict, ctx: _Ctx):
    if _call(e, "TextStyle") and not e["p"]:
        return _fields(e, _TEXT_FIELDS, ctx)
    callee = e.get("callee") or ""
    if e.get("k") == "call" and callee.startswith("GoogleFonts."):
        method = callee.split(".", 1)[1]
        a = dict(_named(e))
        if method == "getFont":
            if len(e["p"]) != 1:
                raise Unsupported
            fam = _str(e["p"][0], ctx)
        elif e["p"] or method in ("getTextTheme", "config", "asMap"):
            raise Unsupported
        else:
            fam = _google_name(method)
        out = {}
        base = a.pop("textStyle", None)
        if base is not None:
            out.update(_text_style(base, ctx))
            out.pop("googleFont", None)
        fields = {k: v for k, v in _TEXT_FIELDS.items() if k != "fontFamily"}
        for k, v in a.items():
            if k not in fields:
                raise Unsupported
            out[k] = fields[k](v, ctx)
        out["googleFont"] = fam
        ctx.fonts.add(fam)
        return out
    raise Unsupported


def _shape(e: dict, ctx: _Ctx):
    c = e.get("callee") if e.get("k") == "call" else None
    m = {"RoundedRectangleBorder": "rounded", "CircleBorder": "circle", "StadiumBorder": "stadium",
         "BeveledRectangleBorder": "beveled"}
    if c not in m or e["p"]:
        raise Unsupported
    out = {"type": m[c]}
    for k, v in _named(e).items():
        if k == "borderRadius":
            out["radius"] = _radius(v, ctx)
        elif k == "side":
            out["side"] = _side(v, ctx)
        else:
            raise Unsupported
    return out


def _size(e: dict, ctx: _Ctx):
    if _call(e, "Size") and len(e["p"]) == 2:
        return [_num(e["p"][0], ctx), _num(e["p"][1], ctx)]
    if _call(e, "Size.fromHeight") and len(e["p"]) == 1:
        return ["infinity", _num(e["p"][0], ctx)]
    raise Unsupported


def _button_style(e: dict, ctx: _Ctx):
    callee = e.get("callee") or ""
    if e.get("k") != "call" or not callee.endswith(".styleFrom") or e["p"]:
        raise Unsupported
    fields = {"backgroundColor": _color, "foregroundColor": _color, "padding": _edge, "shape": _shape,
              "elevation": _num, "minimumSize": _size, "textStyle": _text_style, "side": _side}
    return _fields(e, fields, ctx)


def _input_border(e: dict, ctx: _Ctx) -> tuple[str, object, object]:
    """(kind, radius, colour) of an InputBorder."""
    if e.get("k") == "id" and e["s"] == "InputBorder.none":
        return "none", None, None
    c = e.get("callee") if e.get("k") == "call" else None
    if c in ("OutlineInputBorder", "UnderlineInputBorder") and not e["p"]:
        a = _named(e)
        if set(a) - {"borderRadius", "borderSide"}:
            raise Unsupported
        radius = _radius(a["borderRadius"], ctx) if "borderRadius" in a else None
        side = _side(a["borderSide"], ctx) if "borderSide" in a else {}
        if set(side) - {"color", "width"}:
            raise Unsupported
        return ("outline" if c == "OutlineInputBorder" else "underline"), radius, side.get("color")
    raise Unsupported


def _input_decoration(e: dict, ctx: _Ctx):
    if not _call(e, "InputDecoration") or e["p"]:
        raise Unsupported
    simple = {"hintText": _str, "labelText": _str, "helperText": _str, "prefixIcon": _icon_widget,
              "suffixIcon": _icon_widget, "hintStyle": _text_style, "labelStyle": _text_style, "filled": _bool,
              "fillColor": _color, "isDense": _bool, "contentPadding": _edge}
    out = {}
    a = _named(e)
    for k, v in a.items():
        if k in simple:
            out[k] = simple[k](v, ctx)
        elif k in ("border", "enabledBorder", "focusedBorder"):
            kind, radius, color = _input_border(v, ctx)
            if out.get("border") and out["border"] != kind:
                raise Unsupported
            out["border"] = kind
            if radius is not None:
                if out.get("borderRadius") not in (None, radius):
                    raise Unsupported
                out["borderRadius"] = radius
            if color is not None:
                if k == "focusedBorder":
                    out["focusedBorderColor"] = color
                elif k == "enabledBorder":
                    out["borderColor"] = color
                else:
                    raise Unsupported
        else:
            raise Unsupported
    return out


def _nav_items(e: dict, ctx: _Ctx):
    if e.get("k") != "list":
        raise Unsupported
    out = []
    for it in e["items"]:
        c = it.get("callee") if it.get("k") == "call" else None
        if c not in ("BottomNavigationBarItem", "NavigationDestination") or it["p"]:
            raise Unsupported
        d = {}
        for k, v in _named(it).items():
            if k == "icon":
                d["icon"] = _icon_widget(v, ctx)
            elif k in ("activeIcon", "selectedIcon"):
                d["activeIcon"] = _icon_widget(v, ctx)
            elif k == "label":
                d["label"] = _str(v, ctx)
            else:
                raise Unsupported
        out.append(d)
    return out


def _constraints(e: dict, ctx: _Ctx):
    if _call(e, "BoxConstraints") and not e["p"]:
        return _fields(e, {k: _num for k in ("minWidth", "maxWidth", "minHeight", "maxHeight")}, ctx)
    raise Unsupported


def _physics(e: dict, ctx: _Ctx):
    if e.get("k") == "call" and e.get("callee") in M.ENUMS["Physics"] and not e["p"] and not _named(e):
        return e["callee"]
    raise Unsupported


PARSERS = {"string": _str, "int": _num, "double": _num, "bool": _bool, "color": _color, "edge_insets": _edge,
           "border_radius": _radius, "alignment": _alignment, "icon": _icon, "offset": _offset,
           "duration": _duration, "string_list": _string_list, "image": _image, "gradient": _gradient,
           "box_shadows": _shadows, "border": _border, "box_decoration": _decoration, "text_style": _text_style,
           "shape": _shape, "button_style": _button_style, "input_decoration": _input_decoration,
           "nav_items": _nav_items, "constraints": _constraints, "physics": _physics}


def parse_value(ps: M.PropSpec, e: dict, ctx: _Ctx, owner: str = "", key: str = ""):
    """A property value from an expression (``{"$code": src}`` when it cannot be modelled)."""
    try:
        if ps.kind == "enum":
            v = _enum_parser(ps.enum)(e, ctx)
        elif ps.kind == "int":
            v = _num(e, ctx)
            if not isinstance(v, int):
                raise Unsupported
        else:
            v = PARSERS[ps.kind](e, ctx)
        return v
    except (Unsupported, KeyError, TypeError, ValueError):
        ctx.code_props.append(f"{owner}.{key}: {_ws(ctx.s(e))[:80]}")
        return {"$code": ctx.s(e)}


# =============================================================================== widgets
_NAV_RX = [
    (re.compile(r"^\(\)\s*(?:=>\s*|\{\s*)Navigator\.(?:of\(context\)\.)?pushNamed\((?:context,\s*)?'([^']*)'\);?\s*\}?$"),
     "nav:"),
    (re.compile(r"^\(\)\s*(?:=>\s*|\{\s*)Navigator\.(?:of\(context\)\.)?pushReplacementNamed\((?:context,\s*)?'([^']*)'"
                r"\);?\s*\}?$"), "replace:"),
    (re.compile(r"^\(\)\s*(?:=>\s*|\{\s*)Navigator\.(?:of\(context\)\.)?pop\((?:context)?\);?\s*\}?$"), "back"),
    (re.compile(r"^\(\)\s*(?:=>\s*|\{\s*)Navigator\.(?:of\(context\)\.)?push\((?:context,\s*)?MaterialPageRoute\("
                r"builder:\s*\(\w*\)\s*=>\s*(?:const\s+)?(\w+)\(\)\s*,?\s*\)\s*,?\s*\);?\s*\}?$"), "push:"),
]
_EMPTY_FN = re.compile(r"^\(\)\s*(\{\s*\}|=>\s*null)$")


def _event_value(e: dict, ctx: _Ctx) -> str | None:
    """Handler name / navigation action of a callback expression; None = keep it as code."""
    if e.get("k") == "id" and re.match(r"^[A-Za-z_]\w*$", e["s"]):
        ctx.handlers.add(e["s"])
        return e["s"]
    src = _tight(ctx.s(e))
    for rx, kind in _NAV_RX:
        m = rx.match(src)
        if m:
            return "back" if kind == "back" else kind + m.group(1)
    return None


def _widget_like(e: dict) -> bool:
    """Does the expression look like a widget (a call of a catalog widget / an animation helper)?"""
    if e.get("k") != "call":
        return False
    head = (e.get("callee") or "").split(".")[0]
    if head in M.CATALOG or head in _HELPER_ANIMS or head in ("RadFx", "FadeAnimation"):
        return True
    return head[:1].isupper() and head not in _VALUE_CLASSES and \
        any(k in ("child", "children", "body") for k in _named(e))


_VALUE_CLASSES = {"EdgeInsets", "BorderRadius", "Radius", "BoxDecoration", "TextStyle", "Color", "Colors",
                  "LinearGradient", "RadialGradient", "BoxShadow", "Offset", "Duration", "Alignment", "Size",
                  "InputDecoration", "ThemeData", "GoogleFonts", "Border", "BorderSide"}


class TreeImporter:
    def __init__(self, ctx: _Ctx):
        self.ctx = ctx
        self.n = 0

    def new_id(self) -> str:
        self.n += 1
        return f"w{self.n}"

    # ---- entry
    def widget(self, e: dict) -> dict:
        try:
            node = self._widget(e)
            if node is not None:
                return node
        except Unsupported:
            pass
        return self.code_node(e)

    def code_node(self, e: dict) -> dict:
        """A Code node; widget arguments of an unknown call stay designable through #{slot:..} holes."""
        node = {"id": self.new_id(), "type": "Code", "props": {}}
        ctx = self.ctx
        src = ctx.s(e)
        holes = []
        if e.get("k") == "call":
            for i, a in enumerate(e.get("p") or []):
                if _widget_like(a):
                    holes.append((f"arg{i}", a))
            for k, a in (e.get("a") or {}).items():
                if _widget_like(a):
                    holes.append((k, a))
                elif a.get("k") == "list" and a["items"] and all(_widget_like(i) for i in a["items"]):
                    holes.append((k, a))
        if holes:
            pieces, last, slots = [], e["o"], {}
            for name, a in sorted(holes, key=lambda h: h[1]["o"]):
                if a.get("k") == "list":       # keep the brackets, design the items
                    first, end = a["items"][0]["o"], a["items"][-1]["e"]
                    pieces.append(ctx.slice(last, first))
                    pieces.append(f"#{{slot:{name}}}")
                    last = end
                    slots[name] = [self.widget(i) for i in a["items"]]
                else:
                    pieces.append(ctx.slice(last, a["o"]))
                    pieces.append(f"#{{slot:{name}}}")
                    last = a["e"]
                    slots[name] = self.widget(a)
            pieces.append(ctx.slice(last, e["e"]))
            node["props"]["code"] = "".join(pieces)
            node["slots"] = slots
        else:
            node["props"]["code"] = src
        self.ctx.code_nodes.append(_ws(src)[:90])
        return node

    def _widget(self, e: dict) -> dict | None:
        if e.get("k") != "call":
            return None
        callee = e.get("callee") or ""
        parts = callee.split(".")
        head = parts[0]
        # ---- animation helpers -> anim
        anim = self._anim(e, callee)
        if anim is not None:
            return anim
        spec0 = M.CATALOG.get(head)
        if spec0 is None or head == "Code" or len(parts) > 2:
            return None
        ctor = parts[1] if len(parts) == 2 else None
        if ctor and ctor not in spec0.ctors:
            return None
        if not ctor and not spec0.unnamed_ctor:
            return None
        if head == "DropdownButton":
            return self._dropdown(e)
        spec = spec0.resolved(ctor)
        node: dict = {"id": self.new_id(), "type": head}
        if ctor:
            node["ctor"] = ctor
        props, slots, events = {}, {}, {}
        positional = sorted(((p.positional, k, p) for k, p in spec.props.items() if p.positional is not None))
        if len(e["p"]) > len(positional):
            raise Unsupported
        for (_i, k, ps), a in zip(positional, e["p"]):
            props[k] = parse_value(ps, a, self.ctx, head, k)
        args = e.get("a") or {}
        # stateful bindings: value: <field> / controller: <field> + onChanged: (value) => setState(...)
        if spec.needs_name:
            self._binding(node, spec, args, props, events)
        for k, a in args.items():
            if k == "controller" and spec.value_type == "TextEditingController" and node.get("_bound"):
                continue
            if spec.value_prop and k == spec.value_prop and node.get("_bound"):
                continue
            if k in events or (node.get("_bound") and k == next(iter(spec.events))):
                continue
            if k in spec.slots:
                ss = spec.slots[k]
                if ss.multi:
                    if a.get("k") != "list":
                        raise Unsupported
                    slots[k] = [self.widget(i) for i in a["items"]]
                else:
                    slots[k] = self.widget(a)
            elif spec.children and k == spec.children:
                if a.get("k") != "list":
                    raise Unsupported
                node["children"] = [self.widget(i) for i in a["items"]]
            elif k in spec.events:
                v = _event_value(a, self.ctx)
                if v is not None:
                    events[k] = v
                elif _EMPTY_FN.match(_tight(self.ctx.s(a))) and k in spec.required_events:
                    pass                         # () {} = an enabled button without a handler
                else:
                    props[k] = {"$code": self.ctx.s(a)}
                    self.ctx.code_props.append(f"{head}.{k}: {_ws(self.ctx.s(a))[:80]}")
            elif k in spec.props:
                props[k] = parse_value(spec.props[k], a, self.ctx, head, k)
            else:
                props[k] = {"$code": self.ctx.s(a)}
                if k != "key":
                    self.ctx.code_props.append(f"{head}.{k}: {_ws(self.ctx.s(a))[:80]}")
        if head == "DefaultTabController" and "length" in props:
            tabs = next((len(c.get("children") or []) for c, *_ in M.walk_node({"slots": slots})
                         if c.get("type") == "TabBar"), None)
            if tabs is not None and props["length"] == tabs:
                props.pop("length")          # generated automatically from the TabBar
        if props:
            node["props"] = props
        if slots:
            node["slots"] = slots
        if events:
            node["events"] = events
        self.ctx.exact += 1
        if head in ("Positioned", "Expanded", "Flexible"):
            child = slots.get("child")
            if isinstance(child, dict) and child.get("anim") and child.get("_lift"):
                node["anim"] = child.pop("anim")
        for c in slots.values():
            if isinstance(c, dict):
                c.pop("_lift", None)
        return node

    def _binding(self, node, spec, args, props, events) -> None:
        ctx = self.ctx
        if spec.value_type == "TextEditingController":
            c = args.get("controller")
            if c and c.get("k") == "id" and re.match(r"^\w+$", c["s"]):
                if not re.match(r"^_w\d+$", c["s"]):
                    node["name"] = c["s"]
                node["_bound"] = True
                self.ctx.bound.add(c["s"])
            return
        v = args.get(spec.value_prop)
        if not (v and v.get("k") == "id" and re.match(r"^\w+$", v["s"])):
            return
        fname = v["s"]
        ev = next(iter(spec.events))
        auto = re.match(r"^_w\d+$", fname)      # a field generated for an unnamed widget
        cb = args.get(ev)
        if cb is None:
            return
        src = _tight(ctx.s(cb))
        m = re.match(r"^\((\w+)\)\s*(?:=>\s*setState\(\(\)\s*=>\s*(\w+)\s*=\s*\1(?:\s*\?\?\s*false)?\)|\{\s*setState\("
                     r"\(\)\s*=>\s*(\w+)\s*=\s*\1(?:\s*\?\?\s*false)?\);\s*(\w+)\(\1\);\s*\})$", src)
        if not m or (m.group(2) or m.group(3)) != fname:
            return
        if not auto:
            node["name"] = fname
        node["_bound"] = True
        ctx.bound.add(fname)
        if m.group(4):
            events[ev] = m.group(4)
            ctx.handlers.add(m.group(4))
        f = ctx.fields.get(fname)
        if f and f.get("init") is not None:
            try:
                if spec.value_type == "bool":
                    val = _bool(f["init"], ctx)
                elif spec.value_type in ("double", "int"):
                    val = _num(f["init"], ctx)
                elif f["init"].get("k") == "str":
                    val = f["init"]["v"]
                else:
                    val = None
                default = spec.props[spec.value_prop].default
                if val is not None and val != default:
                    props[spec.value_prop] = val
            except Unsupported:
                pass

    def _dropdown(self, e: dict) -> dict:
        args = e.get("a") or {}
        node: dict = {"id": self.new_id(), "type": "DropdownButton"}
        props, events = {}, {}
        spec = M.CATALOG["DropdownButton"]
        self._binding(node, spec, args, props, events)
        for k, a in args.items():
            if k in events or (k == "value" and node.get("_bound")):
                continue
            if k == "items":
                src = _tight(self.ctx.s(a))
                t = a.get("tgt") if a.get("m") == "toList" else None
                lst = t.get("tgt") if t and t.get("m") == "map" else None
                if lst and lst.get("k") == "list" and re.search(r"DropdownMenuItem\(value: (\w+), child: Text\(\1\)\)",
                                                                src):
                    props["items"] = _string_list(lst, self.ctx)
                    continue
                raise Unsupported
            if k == "hint":
                if _call(a, "Text") and len(a["p"]) == 1 and not _named(a):
                    props["hint"] = _str(a["p"][0], self.ctx)
                    continue
                raise Unsupported
            if k == "onChanged":
                v = _event_value(a, self.ctx)
                if v is None:
                    raise Unsupported
                events[k] = v
                continue
            if k == "isExpanded":
                props[k] = _bool(a, self.ctx)
                continue
            if k == "key":
                props[k] = {"$code": self.ctx.s(a)}
                continue
            raise Unsupported
        if props:
            node["props"] = props
        if events:
            node["events"] = events
        self.ctx.exact += 1
        return node

    def _anim(self, e: dict, callee: str) -> dict | None:
        ctx = self.ctx
        args = e.get("a") or {}
        if callee == "RadFx":
            if "child" not in args or e["p"]:
                raise Unsupported
            a = {}
            for k, v in args.items():
                if k == "type":
                    if v.get("k") != "id" or not v["s"].startswith("RadFxType."):
                        raise Unsupported
                    a["type"] = v["s"].split(".", 1)[1]
                elif k in ("delayMs", "durationMs"):
                    a[k] = int(_num(v, ctx))
                elif k in ("offsetX", "offsetY", "scale"):
                    a[k] = _num(v, ctx)
                elif k == "curve":
                    if v.get("k") != "id" or not v["s"].startswith("Curves."):
                        raise Unsupported
                    a["curve"] = v["s"]
                elif k != "child":
                    raise Unsupported
            node = self.widget(args["child"])
            node["anim"] = {"type": a.pop("type", "fadeIn"), **a}
            node["_lift"] = True
            return node
        if callee == "FadeAnimation" and len(e["p"]) == 2:
            # the classic FadeAnimation(delaySeconds, child) helper (simple_animations based): fade + slide up
            delay = _num(e["p"][0], ctx)
            node = self.widget(e["p"][1])
            node["anim"] = {"type": "fadeInUp", "delayMs": int(round(float(delay) * 500)), "durationMs": 500,
                            "offsetY": 30, "from": "FadeAnimation"}
            node["_lift"] = True
            ctx.anim_helpers.add("FadeAnimation")
            return node
        if callee in _HELPER_ANIMS and "child" in args and not e["p"]:
            a = {"type": _HELPER_ANIMS[callee], "from": callee}
            t = a["type"]          # animate_do moves 100 px by default
            if t in ("fadeInUp", "slideUp", "fadeInDown", "slideDown"):
                a["offsetY"] = -100 if t in ("fadeInDown", "slideDown") else 100
            elif t in ("fadeInLeft", "fadeInRight", "slideLeft", "slideRight"):
                a["offsetX"] = -100 if t in ("fadeInLeft", "slideRight") else 100
            for k, v in args.items():
                if k == "delay":
                    a["delayMs"] = _duration(v, ctx)
                elif k == "duration":
                    a["durationMs"] = _duration(v, ctx)
                elif k == "from":
                    off = _num(v, ctx)
                    if a["type"] in ("fadeInLeft", "fadeInRight", "slideLeft", "slideRight"):
                        a["offsetX"] = -off if a["type"] in ("fadeInLeft", "slideRight") else off
                    else:
                        a["offsetY"] = -off if a["type"] in ("fadeInDown", "slideDown") else off
                elif k != "child":
                    raise Unsupported
            node = self.widget(args["child"])
            node["anim"] = a
            node["_lift"] = True
            ctx.anim_helpers.add(callee)
            return node
        return None


def _strip_internal(node):
    if isinstance(node, list):
        for c in node:
            _strip_internal(c)
        return
    if not isinstance(node, dict):
        return
    node.pop("_lift", None)
    node.pop("_bound", None)
    for c in (node.get("slots") or {}).values():
        _strip_internal(c)
    for c in node.get("children") or []:
        _strip_internal(c)


# ======================================================================================= screens
_GENERATED_IMPORTS = {"package:flutter/material.dart", "package:flutter/cupertino.dart",
                      "package:google_fonts/google_fonts.dart", "../radfx.dart", "radfx.dart",
                      "package:flutter/widgets.dart"}


def _theme_unwrap(e: dict, ctx: _Ctx) -> tuple[dict, dict] | None:
    """Theme(data: ThemeData(...), child: Builder(builder: (context) => tree)) -> (theme, tree expr)."""
    if not _call(e, "Theme"):
        return None
    a = _named(e)
    data, child = a.get("data"), a.get("child")
    if not (data and child and _call(data, "ThemeData") and _call(child, "Builder")):
        return None
    b = _named(child).get("builder")
    if not (b and b.get("k") == "fn" and b.get("expr")):
        return None
    theme = {}
    try:
        for k, v in _named(data).items():
            if k == "colorScheme" and _call(v, "ColorScheme.fromSeed"):
                for k2, v2 in _named(v).items():
                    if k2 == "seedColor":
                        theme["seedColor"] = _color(v2, ctx)
                    elif k2 == "brightness" and v2.get("k") == "id":
                        theme["brightness"] = v2["s"].split(".")[-1]
                    else:
                        return None
            elif k == "brightness" and v.get("k") == "id":
                theme["brightness"] = v["s"].split(".")[-1]
            elif k == "scaffoldBackgroundColor":
                theme["background"] = _color(v, ctx)
            elif k == "textTheme" and _call(v, "GoogleFonts.getTextTheme") and len(v["p"]) == 1:
                theme["fontFamily"] = _str(v["p"][0], ctx)
                ctx.fonts.add(theme["fontFamily"])
            else:
                return None
    except Unsupported:
        return None
    return theme, b["expr"]


def _dedent(s: str) -> str:
    s = s.strip("\n")
    lines = s.splitlines()
    if not lines:
        return ""
    first = lines[0].lstrip()
    rest = textwrap.dedent("\n".join(lines[1:])) if len(lines) > 1 else ""
    return (first + ("\n" + rest if rest else "")).strip()


def _screen_from_class(info: dict, cls: dict, widget_name: str, source: str, previous: dict | None,
                       designer_mode: bool) -> tuple[dict, _Ctx]:
    ctx = _Ctx(source)
    build = next((m for m in cls["members"] if m.get("kind") == "method" and m.get("name") == "build"), None)
    body = (build or {}).get("body") or {}
    if not body.get("expr"):
        raise ValueError(f"{cls['name']}.build() has no return expression")
    # fields first: initial values of bound widgets
    for m in cls["members"]:
        if m.get("kind") == "field" and not m.get("static"):
            for v in m["vars"]:
                ctx.fields[v["name"]] = {"type": m.get("type"), "init": v.get("init")}
    expr = body["expr"]
    theme = {}
    tu = _theme_unwrap(expr, ctx)
    if tu:
        theme, expr = tu
    imp = TreeImporter(ctx)
    tree = imp.widget(expr)
    _strip_internal(tree)
    # prelude: statements before the return
    prelude = ""
    if "blockStart" in body and "return" in body:
        prelude = _dedent(ctx.slice(body["blockStart"], body["return"]["o"]))
        if not body.get("last", True):
            prelude += "\n" + "// (statements after the return were dropped)"
    # members: everything except build / generated parts
    named = {}
    for n, *_ in M.walk_node(tree):
        if n.get("name"):
            named[n["name"]] = n
    keep = []
    for m in cls["members"]:
        kind = m.get("kind")
        if kind == "method" and m.get("name") == "build":
            continue
        if kind == "ctor":
            continue
        if kind == "method" and m.get("abstract") and designer_mode:
            continue                     # abstract handler declarations of a generated designer
        if kind == "method" and m.get("name") == "dispose" and designer_mode:
            continue
        if kind == "method" and m.get("name") == "createState":
            continue
        if kind == "field" and all(v["name"] in named or v["name"] in ctx.bound for v in m["vars"]):
            continue                     # fields of named widgets are generated again
        if kind == "field" and m.get("static") and designer_mode:
            continue
        keep.append(_dedent(ctx.slice(m["o"], m["e"])))
    route = "/" + M.snake(widget_name)
    wcls = next((c for c in info.get("classes", []) if c["name"] == widget_name), None)
    for m in (wcls or {}).get("members", []):
        if m.get("kind") == "field" and m.get("static"):
            for v in m["vars"]:
                if v["name"] in ("route", "routeName") and (v.get("init") or {}).get("k") == "str":
                    route = v["init"]["v"]
    pushed = {M.snake(n["events"][k][5:]) + ".dart" for n, *_ in M.walk_node(tree)
              for k in (n.get("events") or {}) if str(n["events"][k]).startswith("push:")}
    data = {"version": M.SCHEMA_VERSION, "name": M.class_name(widget_name),
            "route": route, "theme": theme,
            "assets": sorted(ctx.assets), "fonts": [{"family": f, "source": "google"} for f in sorted(ctx.fonts)]}
    imports = [i["uri"] for i in info.get("imports", []) if i.get("uri") and i["uri"] not in _GENERATED_IMPORTS
               and not i.get("prefix") and i["uri"] not in pushed]
    imports += [f"{i['uri']} as {i['prefix']}" for i in info.get("imports", []) if i.get("prefix")]
    # imports of animation helpers that all became RadFx (and are not used by kept code) are dropped
    kept_code = " ".join([prelude, *keep] + [str((n.get("props") or {}).get("code", "")) for n, *_ in
                                             M.walk_node(tree) if n.get("type") == "Code"] + ctx.code_props)
    for helper_import, names in _HELPER_IMPORTS.items():
        for imp_ in list(imports):
            if re.search(helper_import, imp_) and ctx.anim_helpers & names and \
                    not any(re.search(rf"\b{n}\b", kept_code) for n in names):
                imports.remove(imp_)
                ctx.dropped_imports.append(imp_)
    if imports:
        data["imports"] = imports
    code = {}
    if prelude:
        code["prelude"] = prelude
    if keep:
        code["members"] = "\n\n".join(keep)
    if code:
        data["code"] = code
    data["tree"] = tree
    if previous:
        keep_ids(data["tree"], previous.get("tree") or {})
    _renumber(data, previous)
    return data, ctx


def _renumber(data: dict, previous: dict | None) -> None:
    """Make ids unique (ids kept from *previous* win; the others get fresh numbers)."""
    used = set()
    nodes = [n for n, *_ in M.walk_node(data["tree"])]
    kept = [n for n in nodes if n.get("_kept")]
    for n in kept:
        used.add(n["id"])
    nxt = max([int(i[1:]) for i in used if re.match(r"^w\d+$", i)] + [0])
    if previous:
        nxt = max([nxt] + [int(n["id"][1:]) for n, *_ in M.walk_node(previous.get("tree") or {})
                           if re.match(r"^w\d+$", str(n.get("id", "")))])
    for n in nodes:
        if n.pop("_kept", False):
            continue
        nxt += 1
        n["id"] = f"w{nxt}"


def keep_ids(tree: dict, old: dict) -> None:
    """Copy ids of *old* onto *tree* where the path and the type match (stable selection after a re-import)."""
    if not old or tree.get("type") != old.get("type"):
        return
    if old.get("id"):
        tree["id"] = old["id"]
        tree["_kept"] = True
    oa, na = old.get("anim") or {}, tree.get("anim")
    if na and oa.get("from") and "from" not in na:        # informational, not in the generated code
        na["from"] = oa["from"]
    for slot, v in (tree.get("slots") or {}).items():
        ov = (old.get("slots") or {}).get(slot)
        if isinstance(v, list) and isinstance(ov, list):
            for a, b in zip(v, ov):
                keep_ids(a, b)
        elif isinstance(v, dict) and isinstance(ov, dict):
            keep_ids(v, ov)
    for a, b in zip(tree.get("children") or [], old.get("children") or []):
        keep_ids(a, b)


def _widget_name_of(cls: dict, classes: dict) -> tuple[str, bool] | None:
    """(screen name, designer_mode) for a class with build(), None for other classes."""
    ext = cls.get("extends") or ""
    if not any(m.get("kind") == "method" and m.get("name") == "build" for m in cls["members"]):
        return None
    if ext == "State" and cls.get("extendsArgs"):
        w = cls["extendsArgs"][0]
        designer = cls.get("abstract") and cls["name"] == f"{w}Designer"
        return w, bool(designer)
    if ext in ("StatelessWidget", "StatefulWidget") or ext.endswith("Widget"):
        return cls["name"], False
    return None


def import_dart(source: str, class_name: str | None = None, previous: dict | None = None) -> ImportResult:
    """Import every screen-like class (a build() method) of a Dart file; *class_name* picks one widget."""
    res = ImportResult()
    info = parse_dart(source)
    for d in info.get("diagnostics", [])[:5]:
        res.report.append(("warning", f"syntax: {d['msg']} (offset {d['o']})"))
    classes = {c["name"]: c for c in info.get("classes", [])}
    found = []
    for c in info.get("classes", []):
        wn = _widget_name_of(c, classes)
        if wn:
            found.append((wn[0], wn[1], c))
    if class_name:
        found = [f for f in found if f[0] == class_name or f[2]["name"] == class_name]
    if not found:
        res.report.append(("error", "no widget class with a build() method found"
                           + (f" named {class_name}" if class_name else "")))
        return res
    for wname, designer_mode, cls in found:
        try:
            data, ctx = _screen_from_class(info, cls, wname, source, previous, designer_mode)
        except (ValueError, KeyError) as ex:
            res.report.append(("error", f"{cls['name']}: {ex}"))
            continue
        res.screens.append(data)
        res.stats[data["name"]] = {"exact": ctx.exact, "code_nodes": list(ctx.code_nodes),
                                   "code_props": list(ctx.code_props),
                                   "anim_helpers": sorted(ctx.anim_helpers)}
        res.report.append(("info", f"{data['name']}: {ctx.exact} widgets imported exactly, "
                                   f"{len(ctx.code_nodes)} kept as Code nodes, {len(ctx.code_props)} property "
                                   f"values kept as code"))
        for c in ctx.code_nodes:
            res.report.append(("warning", f"{data['name']}: Code node: {c}"))
        for c in ctx.code_props:
            res.report.append(("warning", f"{data['name']}: code value: {c}"))
        for h in sorted(ctx.anim_helpers):
            res.report.append(("info", f"{data['name']}: {h}(...) became a designer animation (RadFx)"))
        for d in ctx.dropped_imports:
            res.report.append(("info", f"{data['name']}: import '{d}' dropped (its helpers became RadFx)"))
    return res


def import_file(path, class_name: str | None = None, previous: dict | None = None) -> ImportResult:
    p = Path(path)
    return import_dart(p.read_text(encoding="utf-8", errors="replace"), class_name, previous)


def import_expression(expr: str) -> dict:
    """One widget expression -> a node (paste Dart code into the designer)."""
    info = parse_dart(expr, expr=True)
    e = info.get("expr")
    if not e:
        raise ValueError("not a Dart expression")
    ctx = _Ctx(expr)
    node = TreeImporter(ctx).widget(e)
    _strip_internal(node)
    return copy.deepcopy(node)
