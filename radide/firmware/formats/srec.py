"""Motorola S-record (.s19 / .s28 / .s37 / .mot / .srec / .s): S0 header, S1/S2/S3 data with 16/24/32-bit
addresses, S5/S6 record counts, S7/S8/S9 start address. Pure Python."""
from __future__ import annotations

from .memmap import MemoryMap

ADDR_LEN = {"0": 2, "1": 2, "2": 3, "3": 4, "5": 2, "6": 3, "7": 4, "8": 3, "9": 2}


class SrecFormatError(ValueError):
    pass


def looks_like(head: bytes) -> bool:
    text = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    if len(text) < 10 or text[:1] not in (b"S", b"s") or text[1:2] not in b"0123456789":
        return False
    line = text.split(b"\n", 1)[0].strip()
    return all(c in b"0123456789abcdefABCDEF" for c in line[2:])


def parse(text: str, strict: bool = True) -> MemoryMap:
    m = MemoryMap()
    run_start, run = None, bytearray()
    chunks: list[tuple[int, bytes]] = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line[0] not in "Ss" or len(line) < 4:
            if strict:
                raise SrecFormatError(f"line {n}: not an S-record")
            continue
        t = line[1]
        if t not in ADDR_LEN:
            if strict:
                raise SrecFormatError(f"line {n}: unknown record type S{t}")
            continue
        try:
            rec = bytes.fromhex(line[2:])
        except ValueError:
            raise SrecFormatError(f"line {n}: not hexadecimal") from None
        if not rec or len(rec) != rec[0] + 1:
            raise SrecFormatError(f"line {n}: wrong record length")
        if (sum(rec[:-1]) ^ 0xFF) & 0xFF != rec[-1]:
            raise SrecFormatError(f"line {n}: checksum error")
        al = ADDR_LEN[t]
        addr = int.from_bytes(rec[1:1 + al], "big")
        data = rec[1 + al:-1]
        if t == "0":
            m.header = data.decode("latin-1").rstrip("\x00")
        elif t in "123":
            if run_start is not None and addr == run_start + len(run):
                run += data
            else:
                if run_start is not None:
                    chunks.append((run_start, bytes(run)))
                run_start, run = addr, bytearray(data)
            m.meta.setdefault("addr_bytes", al)
            m.meta["addr_bytes"] = max(m.meta["addr_bytes"], al)
        elif t in "789":
            m.start = addr
    if run_start is not None:
        chunks.append((run_start, bytes(run)))
    for a, d in chunks:
        m.add(a, d)
    m.meta["format"] = "srec"
    return m


def _rec(t: str, addr: int, data: bytes) -> str:
    al = ADDR_LEN[t]
    body = bytes([al + len(data) + 1]) + addr.to_bytes(al, "big") + data
    return f"S{t}" + body.hex().upper() + f"{(sum(body) & 0xFF) ^ 0xFF:02X}"


def dumps(m: MemoryMap, width: int = 32, addr_bytes: int | None = None, header: str | None = None) -> str:
    """S-record text. *addr_bytes* 2/3/4 = S19/S28/S37 (default: the smallest that fits, or the loaded one)."""
    top = max(m.max_address - 1, m.start or 0, 0)
    need = 2 if top <= 0xFFFF else 3 if top <= 0xFFFFFF else 4
    al = max(need, addr_bytes or int(m.meta.get("addr_bytes", 0) or 0) or need)
    al = min(al, 4)
    dt = {2: "1", 3: "2", 4: "3"}[al]
    st = {2: "9", 3: "8", 4: "7"}[al]
    out = [_rec("0", 0, (m.header if header is None else header).encode("latin-1", "replace")[:250])]
    count = 0
    for s in m.segments:
        for i in range(0, len(s.data), width):
            out.append(_rec(dt, s.address + i, bytes(s.data[i:i + width])))
            count += 1
    if count <= 0xFFFF:
        out.append(_rec("5", count, b""))
    elif count <= 0xFFFFFF:
        out.append(_rec("6", count, b""))
    out.append(_rec(st, m.start or 0, b""))
    return "\n".join(out) + "\n"
