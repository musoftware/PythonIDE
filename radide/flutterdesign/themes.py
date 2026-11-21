"""App theme (ThemeData) editor model for designed Flutter screens (docs/FLUTTER_DESIGNER.md section 7.3).

A project theme lives in ``<project>/screens/app.ftheme.json`` and is generated into ``lib/theme/app_theme.dart``
(``AppTheme.light`` / ``AppTheme.dark`` / ``AppTheme.mode``); RAD IDE Flutter projects get
``theme: AppTheme.light, darkTheme: AppTheme.dark, themeMode: AppTheme.mode`` in lib/main.dart.

```json
{
 "version": 1,
 "seedColor": "#FF5B6CF9",            // ColorScheme.fromSeed
 "variant": "tonalSpot",              // DynamicSchemeVariant (tonalSpot, fidelity, vibrant, expressive, content,
                                      //   monochrome, neutral, rainbow, fruitSalad)
 "mode": "system",                    // ThemeMode: system | light | dark
 "colors": {"light": {"primary": "#FF...", "secondary": ..., "tertiary", "surface", "error", ...},
            "dark":  {...}},          // ColorScheme overrides (copyWith)
 "background": {"light": "#FFF7F7FB", "dark": "#FF101018"},   // scaffoldBackgroundColor
 "font": {"family": "Poppins", "source": "google" | "asset", "headings": "Playfair Display",
          "headingsSource": "google", "headingWeight": "FontWeight.w700"},
 "buttons": {"radius": 14, "height": 52, "elevation": 0, "padding": {"h": 24, "v": 14},
             "textStyle": {"fontSize": 16, "fontWeight": "FontWeight.w600"}},
 "inputs": {"style": "outline" | "underline" | "filled", "radius": 14, "fillColor": "#FFF1F2F8",
            "contentPadding": {"h": 16, "v": 14}},
 "cards": {"radius": 18, "elevation": 0, "color": null, "margin": {"all": 0}},
 "appBar": {"centerTitle": true, "elevation": 0, "transparent": false},
 "useMaterial3": true
}
```

The per-screen ``theme`` of a .fscreen.json (seedColor / brightness / fontFamily / background) stays supported
by codegen; ``screen_theme(spec)`` derives one from a project theme. Plain Python (no Qt).
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from . import codegen as CG
from . import model as M

THEME_FILE = "screens/app.ftheme.json"
THEME_DART = "lib/theme/app_theme.dart"
VARIANTS = ["tonalSpot", "fidelity", "vibrant", "expressive", "content", "monochrome", "neutral", "rainbow",
            "fruitSalad"]
SCHEME_KEYS = ["primary", "onPrimary", "primaryContainer", "onPrimaryContainer", "secondary", "onSecondary",
               "secondaryContainer", "tertiary", "onTertiary", "error", "onError", "surface", "onSurface",
               "surfaceContainerHighest", "outline", "outlineVariant"]
INPUT_STYLES = ["outline", "underline", "filled"]

DEFAULT = {
    "version": 1,
    "seedColor": "#FF5B6CF9",
    "variant": "tonalSpot",
    "mode": "system",
    "colors": {"light": {}, "dark": {}},
    "background": {},
    "font": {},
    "buttons": {"radius": 14, "height": 52, "elevation": 0},
    "inputs": {"style": "outline", "radius": 14},
    "cards": {"radius": 16, "elevation": 1},
    "appBar": {"centerTitle": True, "elevation": 0},
    "useMaterial3": True,
}

# ready-made palettes for the editor's "Presets" list (all original colour choices)
PRESETS = {
    "Indigo dusk": {"seedColor": "#FF5B6CF9", "variant": "tonalSpot"},
    "Coral sunrise": {"seedColor": "#FFFF6B5B", "variant": "vibrant"},
    "Forest": {"seedColor": "#FF2E7D5B", "variant": "tonalSpot"},
    "Ocean": {"seedColor": "#FF0077B6", "variant": "fidelity"},
    "Grape soda": {"seedColor": "#FF7B2FF7", "variant": "expressive"},
    "Sand": {"seedColor": "#FFC79A5B", "variant": "content"},
    "Graphite": {"seedColor": "#FF44475A", "variant": "monochrome"},
    "Mint": {"seedColor": "#FF18B69B", "variant": "rainbow"},
}


def new_theme(**overrides) -> dict:
    t = copy.deepcopy(DEFAULT)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(t.get(k), dict):
            t[k].update(v)
        else:
            t[k] = v
    return t


def normalize(spec: dict) -> dict:
    """Fill defaults, canonicalise colours, check enums. Raises ValueError on bad values."""
    t = new_theme()
    for k, v in (spec or {}).items():
        if isinstance(v, dict) and isinstance(t.get(k), dict) and k != "colors":
            t[k] = {**t[k], **v}
        else:
            t[k] = copy.deepcopy(v)
    t["seedColor"] = _color(t.get("seedColor") or DEFAULT["seedColor"])
    if t.get("variant") not in VARIANTS:
        raise ValueError(f"variant must be one of {', '.join(VARIANTS)}")
    if t.get("mode") not in ("system", "light", "dark"):
        raise ValueError("mode must be system, light or dark")
    cols = t.get("colors") or {}
    t["colors"] = {b: {k: _color(v) for k, v in (cols.get(b) or {}).items() if v and k in SCHEME_KEYS}
                   for b in ("light", "dark")}
    t["background"] = {b: _color(v) for b, v in (t.get("background") or {}).items() if v and b in ("light", "dark")}
    if (t.get("inputs") or {}).get("style", "outline") not in INPUT_STYLES:
        raise ValueError(f"inputs.style must be one of {', '.join(INPUT_STYLES)}")
    if t["inputs"].get("fillColor"):
        t["inputs"]["fillColor"] = _color(t["inputs"]["fillColor"])
    if (t.get("cards") or {}).get("color"):
        t["cards"]["color"] = _color(t["cards"]["color"])
    return t


def _color(v) -> str:
    c = M.normalize_color(v)
    if not isinstance(c, str):
        raise ValueError(f"bad colour {v!r}")
    return c


def load(project_folder) -> dict | None:
    p = Path(project_folder) / THEME_FILE
    if not p.exists():
        return None
    return normalize(json.loads(p.read_text(encoding="utf-8")))


def save(project_folder, spec: dict) -> Path:
    p = Path(project_folder) / THEME_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(normalize(spec), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def apply_preset(spec: dict, name: str) -> dict:
    return normalize({**(spec or {}), **PRESETS[name]})


def screen_theme(spec: dict, brightness: str = "light") -> dict:
    """The simple per-screen ``theme`` (codegen section 1) closest to a project theme."""
    t = normalize(spec)
    out = {"seedColor": t["seedColor"], "brightness": brightness}
    font = t.get("font") or {}
    if font.get("family") and font.get("source", "google") == "google":
        out["fontFamily"] = font["family"]
    bg = (t.get("background") or {}).get(brightness)
    if bg:
        out["background"] = bg
    return out


def fonts_used(spec: dict) -> list[dict]:
    """Screen-style font entries the theme needs (for pubspec / google_fonts)."""
    f = (normalize(spec).get("font") or {})
    out = []
    for fam, src in ((f.get("family"), f.get("source", "google")), (f.get("headings"), f.get("headingsSource",
                                                                                              "google"))):
        if fam and not any(o["family"] == fam for o in out):
            out.append({"family": fam, "source": src})
    return out


# ------------------------------------------------------------------------------------------ codegen
def _c(v: str) -> str:
    """'#AARRGGBB' -> Color(0xAARRGGBB) (also accepts Colors.x / scheme refs as Dart text)."""
    return CG.x_color(v).render()


def _edge(v) -> str:
    return CG.x_edge(v).render()


def _text_style(v: dict | None) -> str | None:
    if not v:
        return None
    x = CG.x_text_style(v)
    return x.render() if x is not None else None


def _shape(radius) -> str:
    return f"RoundedRectangleBorder(borderRadius: BorderRadius.circular({CG.dart_num(radius)}))"


def _input_border(style: str, radius, color: str | None = None, width: float | None = None) -> str:
    side = ""
    if color or width:
        parts = []
        if color:
            parts.append(f"color: {color}")
        if width:
            parts.append(f"width: {CG.dart_num(width)}")
        side = f"borderSide: BorderSide({', '.join(parts)})"
    if style == "underline":
        return f"UnderlineInputBorder({side})"
    if style == "filled":
        r = f"borderRadius: BorderRadius.circular({CG.dart_num(radius)})"
        return f"OutlineInputBorder({r}, borderSide: BorderSide.none)" if not side else \
            f"OutlineInputBorder({r}, {side})"
    args = [f"borderRadius: BorderRadius.circular({CG.dart_num(radius)})"] + ([side] if side else [])
    return f"OutlineInputBorder({', '.join(args)})"


def _font_call(family: str, source: str, base: str) -> str:
    if source == "asset":
        return f"{base}.apply(fontFamily: {CG.dart_string(family)})"
    return f"GoogleFonts.getTextTheme({CG.dart_string(family)}, {base})"


def generate_dart(spec: dict) -> str:
    """lib/theme/app_theme.dart for a project theme (formatted with dart format when available)."""
    t = normalize(spec)
    font = t.get("font") or {}
    uses_gf = any(f["source"] == "google" for f in fonts_used(t))
    b, inp, card, bar = t["buttons"], t["inputs"], t["cards"], t["appBar"]
    L = ["// AUTO-GENERATED by RAD IDE from screens/app.ftheme.json - do not edit: the theme editor rewrites it.",
         "import 'package:flutter/material.dart';"]
    if uses_gf:
        L.append("import 'package:google_fonts/google_fonts.dart';")
    L += ["", "/// The app theme designed in RAD IDE (Flutter designer > Theme).", "class AppTheme {",
          "  AppTheme._();", "",
          f"  static const Color seed = {CG.x_color(t['seedColor']).render(True)};",
          f"  static const ThemeMode mode = ThemeMode.{t['mode']};", "",
          "  static ThemeData get light => _build(Brightness.light);",
          "  static ThemeData get dark => _build(Brightness.dark);", "",
          "  static ThemeData _build(Brightness brightness) {",
          "    final isDark = brightness == Brightness.dark;",
          "    var scheme = ColorScheme.fromSeed(",
          "      seedColor: seed,",
          "      brightness: brightness,",
          f"      dynamicSchemeVariant: DynamicSchemeVariant.{t['variant']},",
          "    );"]
    lo, do = t["colors"]["light"], t["colors"]["dark"]
    if lo or do:
        def cw(d):
            return "scheme.copyWith(" + ", ".join(f"{k}: {_c(v)}" for k, v in d.items()) + ")" if d else "scheme"
        L.append(f"    scheme = isDark ? {cw(do)} : {cw(lo)};")
    L.append(f"    final base = ThemeData(colorScheme: scheme, useMaterial3: {str(bool(t['useMaterial3'])).lower()});")
    tt = "base.textTheme"
    if font.get("family"):
        tt = _font_call(font["family"], font.get("source", "google"), tt)
    L.append(f"    var textTheme = {tt};")
    if font.get("headings"):
        hw = font.get("headingWeight")
        L.append("    final headings = " + _font_call(font["headings"], font.get("headingsSource", "google"),
                                                       "textTheme") + ";")
        keys = ["displayLarge", "displayMedium", "displaySmall", "headlineLarge", "headlineMedium",
                "headlineSmall", "titleLarge"]
        L.append("    textTheme = textTheme.copyWith(")
        for k in keys:
            extra = f"?.copyWith(fontWeight: {hw})" if hw else ""
            L.append(f"      {k}: headings.{k}{extra},")
        L.append("    );")
    elif font.get("headingWeight"):
        hw = font["headingWeight"]
        L.append("    textTheme = textTheme.copyWith(")
        for k in ("displayLarge", "displayMedium", "displaySmall", "headlineLarge", "headlineMedium",
                  "headlineSmall", "titleLarge"):
            L.append(f"      {k}: textTheme.{k}?.copyWith(fontWeight: {hw}),")
        L.append("    );")
    bg = t.get("background") or {}
    if bg:
        lb = _c(bg["light"]) if bg.get("light") else "scheme.surface"
        db = _c(bg["dark"]) if bg.get("dark") else "scheme.surface"
        bg_x = f"isDark ? {db} : {lb}"
    else:
        bg_x = None
    # buttons
    bargs = []
    if b.get("height"):
        bargs.append(f"minimumSize: const Size(64, {CG.dart_num(b['height'])})")
    if b.get("padding"):
        bargs.append(f"padding: {_edge(b['padding'])}")
    if b.get("radius") is not None:
        bargs.append(f"shape: {_shape(b['radius'])}")
    if b.get("textStyle"):
        ts = _text_style(b["textStyle"])
        if ts:
            bargs.append(f"textStyle: {ts}")
    common = ", ".join(bargs)
    el_args = ", ".join([a for a in [common, (f"elevation: {CG.dart_num(b['elevation'])}"
                                              if b.get("elevation") is not None else "")] if a])
    L.append("    return base.copyWith(")
    L.append("      textTheme: textTheme,")
    if bg_x:
        L.append(f"      scaffoldBackgroundColor: {bg_x},")
    L.append(f"      elevatedButtonTheme: ElevatedButtonThemeData(style: ElevatedButton.styleFrom({el_args})),")
    L.append(f"      filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom({common})),")
    L.append(f"      outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom({common})),")
    tb = [a for a in bargs if not a.startswith("minimumSize")]
    L.append(f"      textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom({', '.join(tb)})),")
    # inputs
    style = inp.get("style", "outline")
    r = inp.get("radius", 12)
    iargs = []
    if style == "filled" or inp.get("fillColor"):
        iargs.append("filled: true")
        iargs.append(f"fillColor: {_c(inp['fillColor'])}" if inp.get("fillColor") else
                     "fillColor: scheme.surfaceContainerHighest")
    if inp.get("contentPadding"):
        iargs.append(f"contentPadding: {_edge(inp['contentPadding'])}")
    iargs.append(f"border: {_input_border(style, r)}")
    if style != "filled":
        iargs.append(f"enabledBorder: {_input_border(style, r, 'scheme.outlineVariant')}")
    else:
        iargs.append(f"enabledBorder: {_input_border(style, r)}")
    iargs.append(f"focusedBorder: {_input_border('outline' if style == 'filled' else style, r, 'scheme.primary', 2)}")
    L.append(f"      inputDecorationTheme: InputDecorationTheme({', '.join(iargs)}),")
    # cards
    cargs = []
    if card.get("elevation") is not None:
        cargs.append(f"elevation: {CG.dart_num(card['elevation'])}")
    if card.get("color"):
        cargs.append(f"color: {_c(card['color'])}")
    if card.get("margin"):
        cargs.append(f"margin: {_edge(card['margin'])}")
    if card.get("radius") is not None:
        cargs.append(f"shape: {_shape(card['radius'])}")
    L.append(f"      cardTheme: CardThemeData({', '.join(cargs)}),")
    # app bar
    aargs = []
    if bar.get("centerTitle") is not None:
        aargs.append(f"centerTitle: {str(bool(bar['centerTitle'])).lower()}")
    if bar.get("elevation") is not None:
        aargs.append(f"elevation: {CG.dart_num(bar['elevation'])}")
        aargs.append("scrolledUnderElevation: " + CG.dart_num(max(float(bar['elevation']), 2)))
    if bar.get("transparent"):
        aargs.append("backgroundColor: Colors.transparent")
    elif bg_x:
        aargs.append(f"backgroundColor: {bg_x}")
    if font.get("headings") or font.get("family"):
        aargs.append("titleTextStyle: textTheme.titleLarge?.copyWith(color: scheme.onSurface)")
    L.append(f"      appBarTheme: AppBarTheme({', '.join(aargs)}),")
    L.append("    );")
    L += ["  }", "}", ""]
    code = "\n".join(L)
    if "isDark ?" not in code:
        code = code.replace("    final isDark = brightness == Brightness.dark;\n", "")
    if "scheme = isDark" not in code:
        code = code.replace("    var scheme = ColorScheme", "    final scheme = ColorScheme")
    if "textTheme = textTheme" not in code:
        code = code.replace("    var textTheme = ", "    final textTheme = ")
    return CG.format_dart(code)


def patch_main_theme(main_code: str) -> str:
    """Point lib/main.dart's MaterialApp at AppTheme (idempotent)."""
    if "AppTheme.light" in main_code:
        return main_code
    new, n = re.subn(r"^(\s*)theme:\s*ThemeData\(.*\),\s*\n", r"\1theme: AppTheme.light,\n", main_code,
                     count=1, flags=re.M)
    if not n:
        return main_code
    m = re.search(r"^(\s*)theme: AppTheme\.light,\n", new, re.M)
    ind = m.group(1)
    dark = re.compile(r"^\s*darkTheme:\s*ThemeData\(.*\),\s*\n", re.M)
    if dark.search(new):
        new = dark.sub(f"{ind}darkTheme: AppTheme.dark,\n", new, count=1)
    else:
        new = new[:m.end()] + f"{ind}darkTheme: AppTheme.dark,\n" + new[m.end():]
    m = re.search(r"^\s*darkTheme: AppTheme\.dark,\n", new, re.M)
    if "themeMode:" not in new:
        new = new[:m.end()] + f"{ind}themeMode: AppTheme.mode,\n" + new[m.end():]
    imp = "import 'theme/app_theme.dart';\n"
    last = list(re.finditer(r"^import .*;\n", new, re.M))
    i = last[-1].end() if last else 0
    return new[:i] + imp + new[i:]


def write_project_theme(project_folder) -> list[str]:
    """Generate lib/theme/app_theme.dart and the pubspec font entries for the project's app.ftheme.json.
    Returns the written relative paths (empty when the project has no theme file)."""
    folder = Path(project_folder)
    spec = load(folder)
    if spec is None:
        return []
    written = []
    code = generate_dart(spec)
    p = folder / THEME_DART
    if not p.exists() or p.read_text(encoding="utf-8", errors="replace") != code:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(code, encoding="utf-8")
        written.append(THEME_DART)
    pp = folder / "pubspec.yaml"
    if pp.exists():
        text = pp.read_text(encoding="utf-8")
        fonts = fonts_used(spec)
        new = CG.update_pubspec(text, [], [], any(f["source"] == "google" for f in fonts))
        if new != text:
            pp.write_text(new, encoding="utf-8")
            written.append("pubspec.yaml")
    return written


def integrate(project_folder, main_code: str) -> tuple[str, list[str]]:
    """Hook for codegen.integrate_rad_project: theme file + main.dart wiring. No theme file = no change."""
    written = write_project_theme(project_folder)
    if (Path(project_folder) / THEME_FILE).exists():
        main_code = patch_main_theme(main_code)
    return main_code, written
