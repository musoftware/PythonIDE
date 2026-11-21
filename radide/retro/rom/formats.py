"""Copy As: the selected bytes as hex, a C array, assembler data lines (db / .byte / dc.b / DEFB), a Python
bytes literal, Base64 or text."""
from __future__ import annotations

import base64

COPY_FORMATS = [("hex", "Hex (A9 00 8D)"), ("hexcompact", "Hex, no spaces (A9008D)"), ("c", "C array"),
                ("asm_db", "Assembly: db (NASM / FASM / MASM)"), ("asm_byte", "Assembly: .byte (ca65 / DASM / 64tass)"),
                ("asm_dcb", "Assembly: dc.b (68000 / vasm)"), ("asm_defb", "Assembly: DEFB (Z80)"),
                ("python", "Python bytes"), ("base64", "Base64"), ("text", "Text")]


def _rows(data: bytes, per: int = 16):
    for i in range(0, len(data), per):
        yield data[i:i + per]


def copy_text(data: bytes, fmt: str = "hex", offset: int = 0, table=None, codec: str = "latin-1") -> str:
    if fmt == "hex":
        return " ".join(f"{b:02X}" for b in data)
    if fmt == "hexcompact":
        return data.hex().upper()
    if fmt == "c":
        body = ",\n".join("    " + ", ".join(f"0x{b:02X}" for b in r) for r in _rows(data, 12))
        return f"/* {len(data)} bytes from offset 0x{offset:X} */\nconst unsigned char data[{len(data)}] = {{\n{body}\n}};\n"
    if fmt in ("asm_db", "asm_byte", "asm_dcb", "asm_defb"):
        kw = {"asm_db": "db", "asm_byte": ".byte", "asm_dcb": "dc.b", "asm_defb": "DEFB"}[fmt]
        pre = "$" if fmt in ("asm_byte", "asm_dcb") else ""
        suf = "h" if fmt in ("asm_db", "asm_defb") else ""
        comment = ";"

        def num(b: int) -> str:
            if suf:
                s = f"{b:02X}h"
                return "0" + s if s[0] in "ABCDEF" else s
            return f"{pre}{b:02X}"
        lines = [f"{comment} {len(data)} bytes from offset 0x{offset:X}"]
        lines += [f"    {kw} " + ", ".join(num(b) for b in r) for r in _rows(data, 16)]
        return "\n".join(lines) + "\n"
    if fmt == "python":
        return repr(bytes(data))
    if fmt == "base64":
        return base64.b64encode(bytes(data)).decode("ascii")
    if fmt == "text":
        if table is not None:
            return table.decode(data)
        return bytes(data).decode(codec, errors="replace")
    raise ValueError(f"unknown copy format {fmt}")


__all__ = ["COPY_FORMATS", "copy_text"]
