"""Is a source file 16-bit DOS / 8086 course code (to be opened as an "8086 Assembly (Emulator)" project)?

    from radide.emu8086.detect import dos16_score, is_dos16_source
    is_dos16_source(text)      # True for emu8086 / MASM / TASM 16-bit programs (int 21h, org 100h, @data ...)

Used by Open Folder / foreign-project detection to prefer the emulator over NASM / MASM 32/64-bit toolchains.
"""
from __future__ import annotations

import re

_STRONG = [r"^\s*org\s+100h\b", r"\bint\s+21h\b", r"\bint\s+10h\b", r"\bint\s+16h\b", r"@data\b",
           r"^\s*\.model\s+(tiny|small|medium|compact|large|huge)\b", r"^\s*#make_(com|exe|bin)#",
           r"\binclude\s+['\"]?emu8086\.inc", r"\bmov\s+ah\s*,\s*(4ch|09h?|0?2h?|01h?|0ah)\b",
           r"^\s*assume\s+cs\s*:", r"\b0b800h\b"]
_WEAK_32 = [r"\b(e[abcd]x|e[sd]i|e[sb]p|r[abcd]x|r[sd]i|r\d+d?)\b", r"^\s*(section|segment)\s+\.(text|data|bss)\b",
            r"^\s*global\s+(main|_start|_main)\b", r"^\s*bits\s+(32|64)\b", r"\bextern\s+\w+",
            r"^\s*\.(386|486|586|686)", r"^\s*\.intel_syntax", r"\binvoke\b", r"^\s*format\s+pe"]


def dos16_score(text: str) -> int:
    """Positive = looks like 16-bit DOS code, negative = 32/64-bit code."""
    low = text.lower()
    score = 0
    for rx in _STRONG:
        if re.search(rx, low, re.M):
            score += 2
    for rx in _WEAK_32:
        if re.search(rx, low, re.M):
            score -= 3
    return score


def is_dos16_source(text: str) -> bool:
    return dos16_score(text) >= 2
