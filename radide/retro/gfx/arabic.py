"""Arabic for old games (which only draw fixed tiles left to right).

An old game engine knows nothing about Arabic: it prints one tile per byte, left to right.  To show Arabic
text the translator therefore

1. **shapes** the text - every letter becomes its isolated / initial / medial / final form (and lam-alef
   becomes one ligature), using the Unicode *Arabic Presentation Forms-B* characters;
2. puts it in **visual order** - reverses each line so the engine, printing left to right, shows it right
   to left (runs of Latin letters and digits keep their own order);
3. maps each presentation form to one byte in the .tbl file and draws that glyph into the game's font tiles
   (the tile editor).  ``arabic_table()`` builds such a table: one code per letter form.

The forms come from Python's ``unicodedata`` names (``ARABIC LETTER BEH INITIAL FORM`` ...), so no table of
code points is hard-coded here.
"""
from __future__ import annotations

import re
import unicodedata

from .textable import TextTable

LETTERS = ("ءآأؤإئابةتثجحخد"
           "ذرزسشصضطظعغفقكل"
           "منهوىي")
FORM_NAMES = ("ISOLATED", "FINAL", "INITIAL", "MEDIAL")
TATWEEL = "ـ"


def _form(name: str, form: str) -> str | None:
    try:
        return unicodedata.lookup(f"{name} {form} FORM")
    except KeyError:
        return None


def _build() -> dict[str, dict[str, str]]:
    forms: dict[str, dict[str, str]] = {}
    for ch in LETTERS:
        name = unicodedata.name(ch)
        f = {k: _form(name, k) for k in FORM_NAMES}
        if f["ISOLATED"] is None and ch == "ء":
            f["ISOLATED"] = "ﺀ"
        forms[ch] = {k: v for k, v in f.items() if v}
    return forms


FORMS = _build()
LAM_ALEF = {a: {k: _form(f"ARABIC LIGATURE LAM WITH {n}", k) for k in ("ISOLATED", "FINAL")}
            for a, n in (("ا", "ALEF"), ("أ", "ALEF WITH HAMZA ABOVE"),
                         ("إ", "ALEF WITH HAMZA BELOW"), ("آ", "ALEF WITH MADDA ABOVE"))}
HARAKAT = re.compile("[ً-ْٰ]")


def joins_left(ch: str) -> bool:
    """True when the letter connects to the following letter (it has an initial form)."""
    return "INITIAL" in FORMS.get(ch, {}) or ch == TATWEEL


def joins_right(ch: str) -> bool:
    return "FINAL" in FORMS.get(ch, {}) or ch == TATWEEL


def shape(text: str, keep_harakat: bool = False) -> str:
    """Contextual forms (logical order is kept)."""
    if not keep_harakat:
        text = HARAKAT.sub("", text)
    out = []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch not in FORMS:
            out.append(ch)
            i += 1
            continue
        prev = text[i - 1] if i > 0 else ""
        joined_before = bool(prev) and joins_left(prev)
        if ch == "ل" and i + 1 < n and text[i + 1] in LAM_ALEF:       # lam-alef ligature
            lig = LAM_ALEF[text[i + 1]]
            out.append(lig["FINAL"] if joined_before else lig["ISOLATED"])
            i += 2
            continue
        nxt = text[i + 1] if i + 1 < n else ""
        joined_after = joins_left(ch) and bool(nxt) and joins_right(nxt)
        f = FORMS[ch]
        if joined_before and joined_after:
            out.append(f.get("MEDIAL") or f.get("FINAL") or f["ISOLATED"])
        elif joined_before:
            out.append(f.get("FINAL") or f["ISOLATED"])
        elif joined_after:
            out.append(f.get("INITIAL") or f["ISOLATED"])
        else:
            out.append(f["ISOLATED"])
        i += 1
    return "".join(out)


_LTR_RUN = re.compile(r"[0-9A-Za-z][0-9A-Za-z.,:%+\-/ ]*[0-9A-Za-z]|[0-9A-Za-z]|<[^<>]*>")
_MIRROR = str.maketrans("()[]{}<>", ")(][}{><")


def visual(text: str) -> str:
    """Visual (left-to-right display) order of each line: the line is reversed, but Latin / digit runs and
    ``<control>`` codes keep their order."""
    lines = []
    for line in text.split("\n"):
        tokens = []
        pos = 0
        for m in _LTR_RUN.finditer(line):
            tokens.append(("rtl", line[pos:m.start()]))
            tokens.append(("ltr", m.group(0)))
            pos = m.end()
        tokens.append(("rtl", line[pos:]))
        lines.append("".join(t if k == "ltr" else t[::-1].translate(_MIRROR) for k, t in reversed(tokens)))
    return "\n".join(lines)


def prepare(text: str, do_shape: bool = True, do_visual: bool = True) -> str:
    """Text as an old left-to-right engine must store it.  Control codes such as ``<end>`` stay at the end."""
    m = re.search(r"(<[^<>]*>)+$", text)
    tail = m.group(0) if m else ""
    body = text[: len(text) - len(tail)] if tail else text
    if do_shape:
        body = shape(body)
    if do_visual:
        body = visual(body)
    return body + tail


def all_glyphs() -> list[str]:
    """Every presentation form the shaper can produce (one font tile each)."""
    seen: list[str] = []
    for f in FORMS.values():
        for k in FORM_NAMES:
            g = f.get(k)
            if g and g not in seen:
                seen.append(g)
    for lig in LAM_ALEF.values():
        for g in lig.values():
            if g and g not in seen:
                seen.append(g)
    return seen


def arabic_table(start: int = 0x80, base: TextTable | None = None, end_code: int = 0xFF,
                 space: int = 0x20, digits: bool = True) -> TextTable:
    """A .tbl that gives each Arabic letter form its own byte from *start* (about 120 codes), plus a space,
    the end code and (optionally) ASCII digits; merged into *base* when given."""
    t = base or TextTable(name="arabic.tbl")
    used = set(t.entries) | set(t.ends) | set(t.breaks)
    code = start
    if bytes([space]) not in used:
        t.entries[bytes([space])] = " "
    if digits:
        for d in range(10):
            b = bytes([0x30 + d])
            if b not in used:
                t.entries[b] = str(d)
    for ch in "!.":
        if bytes([ord(ch)]) not in used:
            t.entries[bytes([ord(ch)])] = ch
    for g in all_glyphs() + ["،", "؟"]:
        if g in t.entries.values():
            continue
        while code <= 0xFF and (bytes([code]) in used or code in (space, end_code)):
            code += 1
        if code > 0xFF:
            t.errors.append(f"no free code left for U+{ord(g):04X} - start the Arabic codes lower")
            break
        t.entries[bytes([code])] = g
        used.add(bytes([code]))
        code += 1
    if not t.ends:
        t.ends[bytes([end_code])] = "<end>"
    return t
