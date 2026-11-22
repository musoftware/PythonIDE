"""Flutter colour names (Colors.* from the SDK, with a fallback table) and the Material 3 ColorScheme."""
from __future__ import annotations

import colorsys
import re
from functools import lru_cache

from PyQt6.QtGui import QColor

from .. import iconfont
from .. import model as M


# ============================================================================== colours
_FALLBACK_COLORS = {
    "transparent": "#00000000", "black": "#FF000000", "white": "#FFFFFFFF", "black87": "#DD000000",
    "black54": "#8A000000", "black45": "#73000000", "black38": "#61000000", "black26": "#42000000",
    "black12": "#1F000000", "white70": "#B3FFFFFF", "white60": "#99FFFFFF", "white54": "#8AFFFFFF",
    "white38": "#62FFFFFF", "white30": "#4DFFFFFF", "white24": "#3DFFFFFF", "white12": "#1FFFFFFF",
    "white10": "#1AFFFFFF", "red": "#FFF44336", "pink": "#FFE91E63", "purple": "#FF9C27B0",
    "deepPurple": "#FF673AB7", "indigo": "#FF3F51B5", "blue": "#FF2196F3", "lightBlue": "#FF03A9F4",
    "cyan": "#FF00BCD4", "teal": "#FF009688", "green": "#FF4CAF50", "lightGreen": "#FF8BC34A",
    "lime": "#FFCDDC39", "yellow": "#FFFFEB3B", "amber": "#FFFFC107", "orange": "#FFFF9800",
    "deepOrange": "#FFFF5722", "brown": "#FF795548", "grey": "#FF9E9E9E", "blueGrey": "#FF607D8B",
}


@lru_cache(maxsize=1)
def flutter_colors() -> tuple[dict[str, str], dict[str, dict[int, str]]]:
    """(plain colours, swatches name -> {shade: '#AARRGGBB'}) read from the Flutter SDK's colors.dart."""
    plain = dict(_FALLBACK_COLORS)
    swatches: dict[str, dict[int, str]] = {}
    sdk = iconfont._sdk()
    if sdk is None:
        return plain, swatches
    try:
        text = (sdk / "packages" / "flutter" / "lib" / "src" / "material" / "colors.dart").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return plain, swatches
    ints = {m.group(1): m.group(2) for m in re.finditer(r"static const int (_\w+) = 0x([0-9A-Fa-f]{8});", text)}
    for m in re.finditer(r"static const Color (\w+) = Color\(0x([0-9A-Fa-f]{8})\);", text):
        plain[m.group(1)] = "#" + m.group(2).upper()
    for m in re.finditer(r"static const Material(?:Accent)?Color (\w+) = Material(?:Accent)?Color\(\s*(\w+),\s*"
                         r"<int, Color>\{(.*?)\}\);", text, re.S):
        name, prim, body = m.group(1), m.group(2), m.group(3)
        shades = {}
        for s in re.finditer(r"(\d+): Color\((0x[0-9A-Fa-f]{8}|_\w+)\)", body):
            v = s.group(2)
            hexv = v[2:] if v.startswith("0x") else ints.get(v, "")
            if hexv:
                shades[int(s.group(1))] = "#" + hexv.upper()
        pv = prim[2:] if prim.startswith("0x") else ints.get(prim, "")
        if pv:
            plain[name] = "#" + pv.upper()
        swatches[name] = shades
    return plain, swatches


def _hex_color(h: str) -> QColor:
    h = h.lstrip("#")
    if len(h) == 6:
        h = "FF" + h
    v = int(h, 16)
    return QColor((v >> 16) & 255, (v >> 8) & 255, v & 255, (v >> 24) & 255)


def named_color(name: str) -> QColor | None:
    """'Colors.white' / 'Colors.grey.shade300' / 'Colors.blue[700]' / 'CupertinoColors.activeBlue'."""
    m = re.match(r"^(?:Colors|CupertinoColors)\.(\w+)(?:\.shade(\d+)|\[(\d+)\])?$", name.strip())
    if not m:
        return None
    plain, sw = flutter_colors()
    base, shade = m.group(1), m.group(2) or m.group(3)
    if name.startswith("CupertinoColors."):
        cup = {"activeBlue": "#FF007AFF", "systemBlue": "#FF007AFF", "activeGreen": "#FF34C759",
               "systemGreen": "#FF34C759", "systemRed": "#FFFF3B30", "destructiveRed": "#FFFF3B30",
               "systemGrey": "#FF8E8E93", "systemGrey6": "#FFF2F2F7", "white": "#FFFFFFFF",
               "black": "#FF000000", "systemOrange": "#FFFF9500", "systemYellow": "#FFFFCC00",
               "systemBackground": "#FFFFFFFF", "secondaryLabel": "#993C3C43", "label": "#FF000000",
               "separator": "#493C3C43", "systemPurple": "#FFAF52DE", "systemPink": "#FFFF2D55"}
        v = cup.get(base)
        return _hex_color(v) if v else None
    if shade:
        v = sw.get(base, {}).get(int(shade))
        return _hex_color(v) if v else None
    v = plain.get(base)
    return _hex_color(v) if v else None


# ======================================================================== colour scheme
def _hsl(c: QColor, s_mul: float, light: float, s_min: float = 0.0) -> str:
    h, _l, s = colorsys.rgb_to_hls(c.redF(), c.greenF(), c.blueF())
    s = max(s_min, min(1.0, s * s_mul))
    r, g, b = colorsys.hls_to_rgb(h, light, s)
    return "#FF%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def color_scheme(seed: str | None, dark: bool) -> dict[str, QColor]:
    """An approximate Material 3 ColorScheme.fromSeed (tones by HSL lightness)."""
    sc = _hex_color(M.normalize_color(seed) if seed and str(seed).startswith("#") else "#FF6750A4")
    if seed and not str(seed).startswith("#"):
        sc = named_color(str(seed)) or sc
    if not dark:
        t = {"primary": _hsl(sc, 1.0, .40, .35), "onPrimary": "#FFFFFFFF", "primaryContainer": _hsl(sc, 1.0, .90),
             "onPrimaryContainer": _hsl(sc, 1.0, .12), "secondary": _hsl(sc, .30, .40),
             "onSecondary": "#FFFFFFFF", "secondaryContainer": _hsl(sc, .40, .90),
             "onSecondaryContainer": _hsl(sc, .40, .12), "tertiary": _hsl(sc, .5, .40),
             "surface": _hsl(sc, .25, .985), "onSurface": _hsl(sc, .12, .11),
             "onSurfaceVariant": _hsl(sc, .14, .30), "surfaceContainerLowest": "#FFFFFFFF",
             "surfaceContainerLow": _hsl(sc, .25, .965), "surfaceContainer": _hsl(sc, .25, .945),
             "surfaceContainerHigh": _hsl(sc, .22, .925), "surfaceContainerHighest": _hsl(sc, .2, .90),
             "outline": _hsl(sc, .10, .48), "outlineVariant": _hsl(sc, .12, .80), "error": "#FFB3261E",
             "onError": "#FFFFFFFF", "shadow": "#FF000000", "inverseSurface": _hsl(sc, .1, .19),
             "surfaceTint": _hsl(sc, 1.0, .40, .35)}
    else:
        t = {"primary": _hsl(sc, 1.0, .80, .35), "onPrimary": _hsl(sc, 1.0, .20), "primaryContainer": _hsl(sc, 1.0, .30),
             "onPrimaryContainer": _hsl(sc, 1.0, .90), "secondary": _hsl(sc, .30, .80),
             "onSecondary": _hsl(sc, .3, .20), "secondaryContainer": _hsl(sc, .30, .30),
             "onSecondaryContainer": _hsl(sc, .3, .90), "tertiary": _hsl(sc, .5, .80),
             "surface": _hsl(sc, .2, .07), "onSurface": _hsl(sc, .12, .90),
             "onSurfaceVariant": _hsl(sc, .12, .80), "surfaceContainerLowest": _hsl(sc, .2, .045),
             "surfaceContainerLow": _hsl(sc, .2, .10), "surfaceContainer": _hsl(sc, .2, .12),
             "surfaceContainerHigh": _hsl(sc, .2, .17), "surfaceContainerHighest": _hsl(sc, .2, .22),
             "outline": _hsl(sc, .10, .58), "outlineVariant": _hsl(sc, .12, .30), "error": "#FFF2B8B5",
             "onError": "#FF601410", "shadow": "#FF000000", "inverseSurface": _hsl(sc, .1, .90),
             "surfaceTint": _hsl(sc, 1.0, .80, .35)}
    out = {k: _hex_color(v) for k, v in t.items()}
    out["background"] = out["surface"]
    out["onBackground"] = out["onSurface"]
    return out
