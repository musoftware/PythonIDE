"""Intel HEX (.hex / .ihex / .ihx): record types 00 data, 01 EOF, 02 extended segment address, 03 start segment
address, 04 extended linear address, 05 start linear address. Pure Python (no intelhex dependency)."""
from __future__ import annotations

from .memmap import MemoryMap


class HexFormatError(ValueError):
    pass


def _rec(rtype: int, addr: int, data: bytes) -> str:
    body = bytes([len(data), (addr >> 8) & 0xFF, addr & 0xFF, rtype]) + data
    return ":" + body.hex().upper() + f"{(-sum(body)) & 0xFF:02X}"


def looks_like(head: bytes) -> bool:
    text = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    if not text.startswith(b":"):
        return False
    line = text.split(b"\n", 1)[0].strip()
    return len(line) >= 11 and all(c in b"0123456789abcdefABCDEF" for c in line[1:])


def parse(text: str, strict: bool = True) -> MemoryMap:
    m = MemoryMap()
    upper = 0                   # extended linear (04) << 16 or extended segment (02) << 4
    chunks: list[tuple[int, bytes]] = []  # runs of contiguous data records
    run_start = None
    run = bytearray()
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if not line.startswith(":"):
            if strict:
                raise HexFormatError(f"line {n}: does not start with ':'")
            continue
        try:
            rec = bytes.fromhex(line[1:])
        except ValueError:
            raise HexFormatError(f"line {n}: not hexadecimal") from None
        if len(rec) < 5 or len(rec) != rec[0] + 5:
            raise HexFormatError(f"line {n}: wrong record length")
        if sum(rec) & 0xFF:
            raise HexFormatError(f"line {n}: checksum error")
        count, addr, rtype, data = rec[0], (rec[1] << 8) | rec[2], rec[3], rec[4:4 + rec[0]]
        if rtype == 0x00:
            a = upper + addr
            if run_start is not None and a == run_start + len(run):
                run += data
            else:
                if run_start is not None:
                    chunks.append((run_start, bytes(run)))
                run_start, run = a, bytearray(data)
        elif rtype == 0x01:
            break
        elif rtype == 0x02:
            upper = ((data[0] << 8) | data[1]) << 4
        elif rtype == 0x04:
            upper = ((data[0] << 8) | data[1]) << 16
        elif rtype == 0x03:
            cs, ip = (data[0] << 8) | data[1], (data[2] << 8) | data[3]
            m.start = (cs << 4) + ip
            m.meta["start_cs_ip"] = (cs, ip)
        elif rtype == 0x05:
            m.start = int.from_bytes(data[:4], "big")
        elif strict:
            raise HexFormatError(f"line {n}: unknown record type {rtype:02X}")
        del count
    if run_start is not None:
        chunks.append((run_start, bytes(run)))
    for a, d in chunks:
        m.add(a, d)
    m.meta["format"] = "ihex"
    return m


def dumps(m: MemoryMap, width: int = 16) -> str:
    """Intel HEX text (extended linear address records above 64 KB, start linear address when known)."""
    out: list[str] = []
    upper = 0
    for s in m.segments:
        a = s.address
        i = 0
        while i < len(s.data):
            if (a >> 16) != upper:
                upper = a >> 16
                out.append(_rec(0x04, 0, upper.to_bytes(2, "big")))
            # never cross a 64 KB boundary inside one record
            k = min(width, len(s.data) - i, 0x10000 - (a & 0xFFFF))
            out.append(_rec(0x00, a & 0xFFFF, bytes(s.data[i:i + k])))
            a += k
            i += k
    if m.start is not None:
        if "start_cs_ip" in m.meta:
            cs, ip = m.meta["start_cs_ip"]
            out.append(_rec(0x03, 0, cs.to_bytes(2, "big") + ip.to_bytes(2, "big")))
        else:
            out.append(_rec(0x05, 0, (m.start & 0xFFFFFFFF).to_bytes(4, "big")))
    out.append(":00000001FF")
    return "\n".join(out) + "\n"
