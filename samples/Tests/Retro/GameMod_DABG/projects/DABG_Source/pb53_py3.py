#!/usr/bin/env python3
"""PB53 tile packer - Python 3 port of pb53.py from Double Action Blaster Guys (NovaSquirrel, zlib licence).

ALTERED SOURCE (zlib licence, clause 2): ported to Python 3 for the RAD IDE GameMod_DABG sample; only packing
(with the 2-byte-per-word header) and unpacking are kept. The format and the output bytes are the original's.

    python pb53_py3.py --raw ascii.chr ascii.pb53     # pack without the length header (what DABG uses)
    python pb53_py3.py ascii.chr out.pb53             # pack with the header
    python pb53_py3.py -d in.pb53 out.chr             # unpack (header form)
"""
import sys


def _pb8_oneplane(plane, top=None):
    ctile = [0]
    last = top
    flag = 0
    for c in plane:
        flag <<= 1
        if c == last:
            flag |= 1
        else:
            ctile.append(c)
            last = c
    ctile[0] = flag & 0xFF
    return ctile


def pb53(chrdata: bytes):
    out = bytearray()
    seekpoints = []
    for i in range(0, len(chrdata), 16):
        if i > 0 and i % 4096 == 0:
            seekpoints.append(len(out))
        tile = chrdata[i:i + 16]
        solid0 = tile[0] in (0x00, 0xFF) and all(x == tile[0] for x in tile[1:8])
        solid1 = tile[8] in (0x00, 0xFF) and all(x == tile[8] for x in tile[9:16])
        if solid0 and solid1:
            out.append(0x84 | (0x02 & tile[8]) | (0x01 & tile[0]))
            continue
        if i >= 16 and chrdata[i - 16:i] == tile:
            out.append(0x82)
            continue
        if i >= 4096 and chrdata[i - 4096:i - 4080] == tile:
            out.append(0x83)
            continue
        if solid0:
            out.append(0x80 | (0x01 & tile[0]))
        else:
            out.extend(_pb8_oneplane(tile[0:8]))
        if solid1:
            out.append(0x80 | (0x01 & tile[8]))
        elif tile[0:8] == tile[8:16]:
            out.append(0x82)
        elif all(a ^ b == 0xFF for a, b in zip(tile[0:8], tile[8:16])):
            out.append(0x83)
        else:
            out.extend(_pb8_oneplane(tile[8:16]))
    return bytes(out), seekpoints


def _plane(ctrl, it):
    if ctrl >= 0x80:
        return [0xFF if ctrl & 1 else 0x00] * 8
    data = [next(it)]
    while len(data) < 8:
        ctrl <<= 1
        data.append(data[-1] if ctrl & 0x80 else next(it))
    return data


def unpb53(data: bytes, num_tiles=None) -> bytes:
    out = bytearray()
    it = iter(data)
    for ctrl in it:
        if num_tiles is not None and len(out) >= num_tiles * 16:
            break
        if 0x84 <= ctrl <= 0x87:
            out.extend([0xFF if ctrl & 1 else 0] * 8)
            out.extend([0xFF if ctrl & 2 else 0] * 8)
            continue
        if ctrl == 0x82:
            out.extend(out[-16:])
            continue
        if ctrl == 0x83:
            out.extend(out[-4096:-4080])
            continue
        out.extend(_plane(ctrl, it))
        ctrl = next(it)
        if ctrl in (0x82, 0x83):
            x = 0xFF if ctrl & 1 else 0
            out.extend(c ^ x for c in out[-8:])
        else:
            out.extend(_plane(ctrl, it))
    return bytes(out)


def pack_file(data: bytes) -> bytes:
    body, seekpoints = pb53(data)
    words = [(len(data) // 16) % 0x10000] + seekpoints
    return b"".join(bytes(((v >> 8) & 0xFF, v & 0xFF)) for v in words) + body


def unpack_file(data: bytes) -> bytes:
    num = data[0] * 256 + data[1]
    start = -((-num) // 256) * 2
    return unpb53(data[start:], num)


def main(argv):
    unpack, raw = "-d" in argv, "--raw" in argv
    args = [a for a in argv[1:] if a not in ("-d", "--raw")]
    if len(args) != 2:
        print(__doc__)
        return 2
    src = open(args[0], "rb").read()
    if unpack:
        out = unpb53(src) if raw else unpack_file(src)
    else:
        out = pb53(src)[0] if raw else pack_file(src)
    open(args[1], "wb").write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
