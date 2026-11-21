"""Checksum toolkit tests (no Qt): radide/firmware/checksum.

Run:  python samples\\Tests\\Firmware\\Checksum\\test_checksum_core.py

* every algorithm preset vs the CRC RevEng catalogue check value over b"123456789" (+ Adler-32, Fletcher,
  sums), the zlib / binascii fast paths vs the generic table engine on random data, multi-part CRCs,
  custom Rocksoft parameters (CRC-12/DECT, CRC-24/OPENPGP, CRC-64/XZ);
* blocks: multi-range + skip, complement copy, store modes, multipoint repeat, verify / correct report,
  profile save / load (JSON), the simpler {"algo", "start", "end"} shape;
* finder on synthetic images: sum16 BE at the end of a region, CRC-16 with a complement pair, CRC-32 over
  two ranges around a skipped hole, "before" header checksum, cross-check with a second image, and the
  correction after edits.
"""
from __future__ import annotations

import os
import random
import struct
import sys
import time
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.firmware.checksum import algorithms as A  # noqa: E402
from radide.firmware.checksum.blocks import (ChecksumBlock, correct, load_profile, report, save_profile,  # noqa: E402
                                             subtract, verify)
from radide.firmware.checksum.finder import complement_pairs, confirm, find  # noqa: E402
from radide.firmware.project import synth  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


CHECK = b"123456789"
# CRC RevEng catalogue (https://reveng.sourceforge.io/crc-catalogue/) check values
CATALOGUE = {
    "crc8": 0xF4, "crc8-sae-j1850": 0x4B, "crc8-autosar": 0xDF, "crc8-maxim": 0xA1,
    "crc16-ccitt-false": 0x29B1, "crc16-xmodem": 0x31C3, "crc16-kermit": 0x2189, "crc16-x25": 0x906E,
    "crc16-aug-ccitt": 0xE5CC, "crc16-genibus": 0xD64E, "crc16-arc": 0xBB3D, "crc16-modbus": 0x4B37,
    "crc16-usb": 0xB4C8, "crc16-buypass": 0xFEE8, "crc32": 0xCBF43926, "crc32-bzip2": 0xFC891918,
    "crc32-mpeg2": 0x0376E6E7, "crc32-posix": 0x765E7680, "crc32-jamcrc": 0x340BC6D9, "crc32c": 0xE3069283,
    "crc32-autosar": 0x1697D06A, "adler32": 0x091E01DE,
}


def test_algorithms():
    for name, want in CATALOGUE.items():
        got = A.compute(CHECK, name)
        check(f"check value {name} = {want:X}", got == want, f"got {got:X}")
    custom = [({"type": "crc", "width": 12, "poly": 0x80F, "init": 0, "refin": False, "xorout": 0}, 0xF5B,
               "CRC-12/DECT"),
              ({"type": "crc", "width": 24, "poly": 0x864CFB, "init": 0xB704CE, "refin": False, "xorout": 0},
               0x21CF02, "CRC-24/OPENPGP"),
              ({"type": "crc", "width": 64, "poly": 0x42F0E1EBA9EA3693, "init": 0xFFFFFFFFFFFFFFFF, "refin": True,
                "xorout": 0xFFFFFFFFFFFFFFFF}, 0x995DC9BBDF1939FA, "CRC-64/XZ"),
              ({"type": "crc", "width": 5, "poly": 0x05, "init": 0x1F, "refin": True, "xorout": 0x1F}, 0x19,
               "CRC-5/USB"),
              ({"type": "crc", "width": 7, "poly": 0x09, "init": 0, "refin": False, "xorout": 0}, 0x75, "CRC-7/MMC")]
    for spec, want, title in custom:
        got = A.compute(CHECK, spec)
        check(f"custom {title} = {want:X}", got == want, f"got {got:X}")
    check("sum8 of '123456789' = DD", A.compute(CHECK, "sum8") == 0xDD)
    check("sum8 two's complement makes the block add to 0",
          (sum(CHECK) + A.compute(CHECK, "sum8-twos")) & 0xFF == 0)
    check("sum16 bytes = 01DD", A.compute(CHECK, "sum16-bytes") == 0x1DD)
    be = sum(struct.unpack(">4H", CHECK[:8])) + (CHECK[8] << 8)
    check("sum16-be over words (odd tail zero-padded)", A.compute(CHECK, "sum16-be") == be & 0xFFFF)
    check("sum16-be-ones = ~sum", A.compute(CHECK, "sum16-be-ones") == (~be) & 0xFFFF)
    check("xor8 of '123456789' = 31", A.compute(CHECK, "xor8") == 0x31)
    check("Fletcher-16('abcde') = C8F0", A.compute(b"abcde", "fletcher16") == 0xC8F0)
    check("Fletcher-32('abcde') = F04FC729", A.compute(b"abcde", "fletcher32") == 0xF04FC729)
    check("Fletcher-32('abcdefgh') = EBE19591", A.compute(b"abcdefgh", "fletcher32") == 0xEBE19591)
    rnd = random.Random(5)
    data = bytes(rnd.randrange(256) for _ in range(5000))
    bad = []
    for name in A.preset_names("crc"):
        d = A.resolve(name)
        reg = A.reflect(d["init"], d["width"]) if d["refin"] else d["init"]
        generic = A.crc_finish(A._crc_register_generic(data, d["width"], d["poly"], reg, d["refin"]), d)
        if generic != A.compute(data, name):
            bad.append(name)
        if A.compute_parts([data[:1234], data[1234:4000], data[4000:]], name) != A.compute(data, name):
            bad.append(name + " (parts)")
    check("fast paths (zlib / crc_hqx) = generic engine, incremental parts = whole", not bad, bad)
    check("crc32 = zlib.crc32", A.compute(data, "crc32") == zlib.crc32(data))
    try:
        A.resolve({"type": "crc", "width": 16, "poly": 0x1020})
        check("even polynomial rejected", False)
    except A.AlgorithmError:
        check("even polynomial rejected", True)


def test_blocks(tmp):
    check("subtract ranges", subtract([(0, 100), (200, 300)], [(10, 20), (250, 400)]) ==
          [(0, 10), (20, 100), (200, 250)])
    rnd = random.Random(9)
    d = bytearray(rnd.randrange(256) for _ in range(0x2000))
    blocks = [ChecksumBlock("crc a", "crc32", [(0, 0x800), (0x900, 0xFFC)], [(0x100, 0x110)], 0xFFC, 4, "be"),
              ChecksumBlock("sum b", "sum16-le-twos", [(0x1000, 0x1800)], [], 0x17FC, 2, "le", 0x17FE),
              ChecksumBlock("fill", "crc16-ccitt-false", [(0x1800, 0x1900)], [], 0x1810, 2, "be", store_mode="fillFF"),
              ChecksumBlock("multi", "xor8", [(0x1900, 0x190F)], [], 0x190F, 1, "be", repeat_count=8,
                            repeat_stride=0x10)]
    res = correct(d, blocks)
    check("correct: 4 definitions -> 11 blocks, all recalculated", len(res) == 11 and all(r.corrected for r in res),
          report(res))
    check("verify after correct: all OK", all(r.ok for r in verify(d, blocks)), report(verify(d, blocks)))
    expect = zlib.crc32(bytes(d[0:0x100] + d[0x110:0x800] + d[0x900:0xFFC]))
    check("multi-range + skip CRC value", int.from_bytes(d[0xFFC:0x1000], "big") == expect)
    s = int.from_bytes(d[0x17FC:0x17FE], "little")
    check("complement copy written", int.from_bytes(d[0x17FE:0x1800], "little") == (~s) & 0xFFFF)
    words = sum(struct.unpack("<1022H", bytes(d[0x1000:0x17FC])))
    check("two's complement sum: words + value = 0", (words + s) & 0xFFFF == 0)
    tmpd = bytearray(d)
    tmpd[0x1810:0x1812] = b"\xFF\xFF"
    check("store mode fillFF counts the stored bytes as FF",
          int.from_bytes(d[0x1810:0x1812], "big") == A.compute(bytes(tmpd[0x1800:0x1900]), "crc16-ccitt-false"))
    d[0x200] ^= 1
    d[0x1905] ^= 0x40
    r = verify(d, blocks)
    bad = [x.name for x in r if not x.ok]
    check("an edit breaks exactly the covering blocks", bad == ["crc a", "multi #1"], bad)
    res = correct(d, blocks)
    check("correct after edits recalculates only those", [x.name for x in res if x.corrected] == ["crc a", "multi #1"],
          report(res))
    d[0x17FE] ^= 0xFF
    r = verify(d, blocks)
    check("a wrong complement copy is reported", any(x.complement_ok is False and not x.ok for x in r))
    correct(d, blocks)
    p = save_profile(os.path.join(tmp, "p.ecuprofile.json"), blocks, "Test", "unit test", len(d))
    meta, back = load_profile(p)
    check("profile round trip", [b.to_dict() for b in back] == [b.to_dict() for b in blocks] and
          meta.get("file_size") == len(d) and "disclaimer" in meta)
    b = ChecksumBlock.from_dict({"name": "simple", "algo": "sum16be", "start": 0, "end": 0x1000, "store": "0x1FFE",
                                 "width": 2, "endian": "big"})
    check("simple {algo, start, end} shape accepted", b.algorithm == "sum16-be" and b.ranges == [(0, 0x1000)])
    out = verify(d, [ChecksumBlock("past end", "crc32", [(0, 0x5000)], [], 0x10, 4)])
    check("a range past the end of the file is an error, not a crash", out[0].error and not out[0].ok)


def test_finder():
    img = synth.image()
    blocks = synth.demo_blocks()
    check("synthetic image: demo blocks verify", all(r.ok for r in verify(img, blocks)))
    t = time.time()
    res = find(img)
    dt = time.time() - t
    print(f"  finder: {res.tried:,} tries, {len(res.candidates)} candidates, {dt:.1f} s")

    def hit(cands, algo, store, ranges=None, skip=None, comp=None):
        for c in cands:
            if c.algorithm == algo and c.store == store and (ranges is None or c.ranges == ranges) and \
                    (skip is None or c.skip == skip) and (comp is None or c.complement_at == comp):
                return c
        return None
    c1 = hit(res.candidates, "sum16-be", 0x3FFE, [(0, 0x3FFE)])
    check("finder: sum16 BE at the end of its region", c1 is not None and c1.endian == "be")
    c2 = hit(res.candidates, "crc16-ccitt-false", 0x7FFC, [(0x4000, 0x7FFC)], comp=0x7FFE)
    check("finder: CRC-16 + complement pair, ranked first", c2 is not None and res.candidates[0] is c2,
          [x.describe() for x in res.candidates[:3]])
    check("finder candidates re-verify as blocks", all(confirm(img, c) for c in res.candidates))
    t = time.time()
    rh = find(img, ["crc32", "crc32-mpeg2", "sum32-be"], granularity=0x1000, search_holes=True)
    c3 = hit(rh.candidates, "crc32", 0xFFFC, [(0x8000, 0xFFFC)], [(0xC000, 0xD000)])
    check("finder: CRC-32 over two ranges with a skipped hole", c3 is not None and rh.candidates[0] is c3,
          [x.describe() for x in rh.candidates[:3]])
    print(f"  hole search {time.time() - t:.2f} s")
    rk = find(img, ["crc32"], holes=[(0xC000, 0xD000)])
    check("finder: known hole given by the user", hit(rk.candidates, "crc32", 0xFFFC, skip=[(0xC000, 0xD000)]))
    other = synth.image(seed=77)
    rc = find(img, confirm_with=[other])
    names = {(c.algorithm, c.store) for c in rc.candidates}
    check("cross-check with a second image keeps the real blocks",
          {("sum16-be", 0x3FFE), ("crc16-ccitt-false", 0x7FFC)} <= names and len(rc.candidates) <= 4,
          [c.describe() for c in rc.candidates])
    # "before": a header checksum over the block that follows it, stored in its first bytes
    rnd = random.Random(3)
    d = bytearray(rnd.randrange(256) for _ in range(0x8000))
    hb = ChecksumBlock("header", "crc32-mpeg2", [(0x2004, 0x6000)], [], 0x2000, 4, "le")
    correct(d, [hb])
    rb = find(bytes(d), ["crc32-mpeg2", "crc32"], granularity=0x1000)
    check("finder: header checksum before its range (LE)",
          hit(rb.candidates, "crc32-mpeg2", 0x2000, [(0x2004, 0x6000)]) is not None,
          [c.describe() for c in rb.candidates[:3]])
    # complement pair at the end, 32-bit sum
    d2 = bytearray(rnd.randrange(256) for _ in range(0x4000))
    sb = ChecksumBlock("sum32", "sum32-be-twos", [(0, 0x3FF8)], [], 0x3FF8, 4, "be", 0x3FFC)
    correct(d2, [sb])
    r2 = find(bytes(d2), granularity=0x400)
    c4 = hit(r2.candidates, "sum32-be-twos", 0x3FF8, [(0, 0x3FF8)], comp=0x3FFC)
    check("finder: 32-bit two's complement sum + complement copy", c4 is not None and r2.candidates[0] is c4,
          [c.describe() for c in r2.candidates[:3]])
    pairs = complement_pairs(d2, (4,))
    check("complement pair scan finds 0x3FF8", any(p == 0x3FF8 for p, _w, _e in pairs))
    # found block -> edit -> correct
    blk = c3.to_block("found")
    mod = bytearray(img)
    mod[0x8150] = (mod[0x8150] + 1) & 0xFF
    check("edit inside the found block breaks it", not verify(mod, [blk])[0].ok)
    rr = correct(mod, [blk])
    check("correction of the found block", rr[0].corrected and verify(mod, [blk])[0].ok)
    check("finder never reports 8-bit algorithms by default",
          not any(A.resolve(c.algorithm)["width"] < 16 for c in res.candidates))


def main() -> int:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="radide-cks-")
    test_algorithms()
    test_blocks(tmp)
    test_finder()
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
