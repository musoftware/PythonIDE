"""Data inspector values for the byte(s) at the cursor: integers (8..64-bit, little / big endian, signed /
unsigned), floats, binary, a character through the table, and the 6502 instruction that starts there
(official NMOS 6502 opcodes; table written from the MOS programming manual's opcode matrix)."""
from __future__ import annotations

import struct

# opcode -> (mnemonic, mode)
_M6502 = """
00 BRK imp|01 ORA izx|05 ORA zp|06 ASL zp|08 PHP imp|09 ORA imm|0A ASL acc|0D ORA abs|0E ASL abs
10 BPL rel|11 ORA izy|15 ORA zpx|16 ASL zpx|18 CLC imp|19 ORA aby|1D ORA abx|1E ASL abx
20 JSR abs|21 AND izx|24 BIT zp|25 AND zp|26 ROL zp|28 PLP imp|29 AND imm|2A ROL acc|2C BIT abs|2D AND abs|2E ROL abs
30 BMI rel|31 AND izy|35 AND zpx|36 ROL zpx|38 SEC imp|39 AND aby|3D AND abx|3E ROL abx
40 RTI imp|41 EOR izx|45 EOR zp|46 LSR zp|48 PHA imp|49 EOR imm|4A LSR acc|4C JMP abs|4D EOR abs|4E LSR abs
50 BVC rel|51 EOR izy|55 EOR zpx|56 LSR zpx|58 CLI imp|59 EOR aby|5D EOR abx|5E LSR abx
60 RTS imp|61 ADC izx|65 ADC zp|66 ROR zp|68 PLA imp|69 ADC imm|6A ROR acc|6C JMP ind|6D ADC abs|6E ROR abs
70 BVS rel|71 ADC izy|75 ADC zpx|76 ROR zpx|78 SEI imp|79 ADC aby|7D ADC abx|7E ROR abx
81 STA izx|84 STY zp|85 STA zp|86 STX zp|88 DEY imp|8A TXA imp|8C STY abs|8D STA abs|8E STX abs
90 BCC rel|91 STA izy|94 STY zpx|95 STA zpx|96 STX zpy|98 TYA imp|99 STA aby|9A TXS imp|9D STA abx
A0 LDY imm|A1 LDA izx|A2 LDX imm|A4 LDY zp|A5 LDA zp|A6 LDX zp|A8 TAY imp|A9 LDA imm|AA TAX imp|AC LDY abs|AD LDA abs|AE LDX abs
B0 BCS rel|B1 LDA izy|B4 LDY zpx|B5 LDA zpx|B6 LDX zpy|B8 CLV imp|B9 LDA aby|BA TSX imp|BC LDY abx|BD LDA abx|BE LDX aby
C0 CPY imm|C1 CMP izx|C4 CPY zp|C5 CMP zp|C6 DEC zp|C8 INY imp|C9 CMP imm|CA DEX imp|CC CPY abs|CD CMP abs|CE DEC abs
D0 BNE rel|D1 CMP izy|D5 CMP zpx|D6 DEC zpx|D8 CLD imp|D9 CMP aby|DD CMP abx|DE DEC abx
E0 CPX imm|E1 SBC izx|E4 CPX zp|E5 SBC zp|E6 INC zp|E8 INX imp|E9 SBC imm|EA NOP imp|EC CPX abs|ED SBC abs|EE INC abs
F0 BEQ rel|F1 SBC izy|F5 SBC zpx|F6 INC zpx|F8 SED imp|F9 SBC aby|FD SBC abx|FE INC abx
"""
OPCODES_6502: dict[int, tuple[str, str]] = {}
for _item in _M6502.replace("\n", "|").split("|"):
    _item = _item.strip()
    if _item:
        _op, _mn, _mode = _item.split()
        OPCODES_6502[int(_op, 16)] = (_mn, _mode)

MODE_SIZE = {"imp": 1, "acc": 1, "imm": 2, "zp": 2, "zpx": 2, "zpy": 2, "izx": 2, "izy": 2, "rel": 2,
             "abs": 3, "abx": 3, "aby": 3, "ind": 3}


def disasm_6502(data, offset: int, pc: int | None = None) -> tuple[str, int]:
    """(text, size) of the 6502 instruction at *offset*; *pc* = its CPU address (for branch targets)."""
    if offset >= len(data):
        return "", 0
    op = data[offset]
    entry = OPCODES_6502.get(op)
    if entry is None:
        return f".byte ${op:02X}  (not an official 6502 opcode)", 1
    mn, mode = entry
    size = MODE_SIZE[mode]
    if offset + size > len(data):
        return f"{mn} (truncated)", len(data) - offset
    lo = data[offset + 1] if size > 1 else 0
    w = lo | (data[offset + 2] << 8) if size > 2 else lo
    if mode == "imp":
        arg = ""
    elif mode == "acc":
        arg = "A"
    elif mode == "imm":
        arg = f"#${lo:02X}"
    elif mode == "zp":
        arg = f"${lo:02X}"
    elif mode == "zpx":
        arg = f"${lo:02X},X"
    elif mode == "zpy":
        arg = f"${lo:02X},Y"
    elif mode == "izx":
        arg = f"(${lo:02X},X)"
    elif mode == "izy":
        arg = f"(${lo:02X}),Y"
    elif mode == "abs":
        arg = f"${w:04X}"
    elif mode == "abx":
        arg = f"${w:04X},X"
    elif mode == "aby":
        arg = f"${w:04X},Y"
    elif mode == "ind":
        arg = f"(${w:04X})"
    else:   # rel
        rel = lo - 256 if lo >= 128 else lo
        arg = f"${(pc + 2 + rel) & 0xFFFF:04X}" if pc is not None else f"*{rel + 2:+d}"
    return (f"{mn} {arg}".strip()), size


def inspect(data, offset: int, table=None, cpu_address: int | None = None) -> list[tuple[str, str]]:
    """(name, value) rows for the inspector panel."""
    rows: list[tuple[str, str]] = []
    n = len(data)
    if offset < 0 or offset >= n:
        return [("Offset", "-")]
    chunk = bytes(data[offset:offset + 8])
    b = chunk[0]
    rows.append(("Offset", f"0x{offset:X}  ({offset:,})"))
    rows.append(("Binary", f"{b:08b}"))
    rows.append(("Int8 / UInt8", f"{struct.unpack('b', chunk[:1])[0]} / {b}"))
    for bits, fmt_s, fmt_u in ((16, "h", "H"), (32, "i", "I"), (64, "q", "Q")):
        k = bits // 8
        if len(chunk) >= k:
            part = chunk[:k]
            le_s, le_u = struct.unpack("<" + fmt_s, part)[0], struct.unpack("<" + fmt_u, part)[0]
            be_s, be_u = struct.unpack(">" + fmt_s, part)[0], struct.unpack(">" + fmt_u, part)[0]
            rows.append((f"Int{bits} LE", f"{le_s}  (u {le_u}, 0x{le_u:0{k * 2}X})"))
            rows.append((f"Int{bits} BE", f"{be_s}  (u {be_u}, 0x{be_u:0{k * 2}X})"))
    if len(chunk) >= 4:
        rows.append(("Float32 LE / BE", f"{struct.unpack('<f', chunk[:4])[0]:.7g} / {struct.unpack('>f', chunk[:4])[0]:.7g}"))
    if len(chunk) >= 8:
        rows.append(("Float64 LE / BE", f"{struct.unpack('<d', chunk)[0]:.15g} / {struct.unpack('>d', chunk)[0]:.15g}"))
    rows.append(("BCD", f"{b >> 4}{b & 15}" if (b >> 4) < 10 and (b & 15) < 10 else "-"))
    ch = chr(b) if 32 <= b < 127 else "."
    rows.append(("ASCII", ch))
    if table is not None:
        text, _k = table.char_at(data, offset)
        rows.append(("Table", text or "-"))
    text, size = disasm_6502(data, offset, cpu_address)
    rows.append(("6502", f"{text}   [{' '.join(f'{x:02X}' for x in data[offset:offset + size])}]"))
    return rows


__all__ = ["OPCODES_6502", "disasm_6502", "inspect"]
