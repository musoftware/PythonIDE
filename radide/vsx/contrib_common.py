"""Shared helpers of the declarative VS Code contributions (radide/vsx/contrib_*.py).

* ``read_jsonc``: VS Code's JSON-with-comments files (themes, language configurations, snippets) -
  // and /* */ comments and trailing commas are allowed there.
* ``enabled_extensions``: the enabled installed extensions (radide.vsx.list_enabled) - never raises.
* colour helpers: VS Code colours are #RGB, #RGBA, #RRGGBB or #RRGGBBAA; Qt style sheets want #RRGGBB, so
  translucent colours are blended onto a background.
No Qt import here."""
from __future__ import annotations

import json
import plistlib
import re
from pathlib import Path


# ============================================================================ JSON with comments
def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments (outside strings) and trailing commas."""
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    s = "".join(out)
    # trailing commas (outside strings: the comments are gone, strings cannot contain a raw newline)
    return _TRAILING.sub(r"\1", s)


_TRAILING = re.compile(r",(\s*[}\]])")


def read_jsonc(path, default=None):
    """A JSON / JSONC file (also a .plist/.tmTheme/.tmLanguage XML property list) or *default*."""
    try:
        p = Path(path)
        data = p.read_bytes()
    except (OSError, TypeError):
        return default
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    head = data[:200].lstrip()
    if head.startswith(b"<?xml") or head.startswith(b"<plist") or head.startswith(b"<!DOCTYPE plist"):
        try:
            return plistlib.loads(data)
        except Exception:  # noqa: BLE001 - a broken plist is "no data"
            return default
    text = data.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except ValueError:
        pass
    try:
        return json.loads(strip_jsonc(text))
    except ValueError:
        return default


# ============================================================================ extensions
def enabled_extensions() -> list:
    """Enabled installed VS Code extensions (radide.vsx.package.Extension); [] when anything fails."""
    try:
        from . import list_enabled
        return list(list_enabled())
    except Exception:  # noqa: BLE001 - a broken install folder must never stop the IDE
        return []


def ext_file(ext, rel: str) -> Path | None:
    """A file of the extension by its manifest-relative path, or None (missing / outside the folder)."""
    try:
        p = ext.file(rel)
    except Exception:  # noqa: BLE001
        return None
    return p if p is not None and p.is_file() else None


# ============================================================================ colours
_HEX = re.compile(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def parse_color(value) -> tuple[int, int, int, float] | None:
    """'#rgb' / '#rgba' / '#rrggbb' / '#rrggbbaa' -> (r, g, b, alpha 0..1); None for anything else."""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not _HEX.match(v):
        return None
    h = v[1:]
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return r, g, b, a


def to_hex(rgb) -> str:
    r, g, b = (max(0, min(255, int(round(x)))) for x in rgb[:3])
    return f"#{r:02X}{g:02X}{b:02X}"


def solid(value, background="#000000") -> str | None:
    """A VS Code colour as opaque #RRGGBB (translucent colours are blended onto *background*)."""
    c = parse_color(value)
    if c is None:
        return None
    r, g, b, a = c
    if a >= 0.999:
        return to_hex((r, g, b))
    bg = parse_color(background) or (0, 0, 0, 1)
    return to_hex((bg[0] + (r - bg[0]) * a, bg[1] + (g - bg[1]) * a, bg[2] + (b - bg[2]) * a))


def mix(a: str, b: str, t: float) -> str:
    """Blend two #RRGGBB colours: t=0 -> a, t=1 -> b."""
    ca, cb = parse_color(a) or (0, 0, 0, 1), parse_color(b) or (0, 0, 0, 1)
    return to_hex(tuple(ca[i] + (cb[i] - ca[i]) * t for i in range(3)))


def luminance(c: str) -> float:
    p = parse_color(c) or (0, 0, 0, 1)

    def ch(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(p[0]) + 0.7152 * ch(p[1]) + 0.0722 * ch(p[2])


def is_dark_color(c: str) -> bool:
    return luminance(c) < 0.2


def readable_on(bg: str, light="#FFFFFF", dark="#000000") -> str:
    return light if is_dark_color(bg) else dark


def monaco_color(value) -> str | None:
    """A colour Monaco's defineTheme accepts (#RRGGBB or #RRGGBBAA)."""
    c = parse_color(value)
    if c is None:
        return None
    r, g, b, a = c
    if a >= 0.999:
        return to_hex((r, g, b))
    return to_hex((r, g, b)) + f"{int(round(a * 255)):02X}"


__all__ = ["strip_jsonc", "read_jsonc", "enabled_extensions", "ext_file", "parse_color", "to_hex", "solid",
           "mix", "luminance", "is_dark_color", "readable_on", "monaco_color"]
