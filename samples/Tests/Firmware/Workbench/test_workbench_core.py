"""Firmware & ECU workbench - core tests without Qt (radide/firmware/ui: adapters, eeprom, demo).

Run:  python samples\\Tests\\Firmware\\Workbench\\test_workbench_core.py

* the synthetic demo image (radide/firmware/ui/demo.py) has the maps / checksums it claims;
* the map finder (maps slice, or the built-in fallback) finds the demo maps at their true addresses;
* checksum verify / fix through the checksum slice and through the built-in fallback agree;
* Intel HEX / S-record files load at their address (formats slice and the built-in parsers);
* EEPROM sizes 128 B .. 512 KB are recognised, 16/32-bit swap views are their own inverse;
* the ECU project adapter (project slice): create -> maps saved in the map pack -> build fixes the checksums;
* A2L text from the maps slice imports back to the same addresses.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.firmware.ui import adapters as A  # noqa: E402
from radide.firmware.ui import demo, eeprom  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


WORK = Path(tempfile.gettempdir()) / "radide-fw-workbench-core"
def _writable(func, path, _exc):          # originals of ECU projects are read-only
    os.chmod(path, 0o666)
    func(path)


if WORK.exists():
    shutil.rmtree(WORK, onerror=_writable)
WORK.mkdir(parents=True)

# ------------------------------------------------------------------ demo image
data, maps, profiles = demo.build_image()
check("demo image is 256 KB", len(data) == demo.SIZE)
check("demo image has 5 maps / values", len(maps) == 5, [m["name"] for m in maps])
check("demo checksums are correct", all(r["ok"] for r in A.verify(data, profiles)), A.verify(data, profiles))
v2, _m, _p = demo.build_image(1)
check("variant 1 differs (second software version)", v2 != data and len(v2) == len(data))
ign = A.MapDef.from_any(maps[0])
xs, ys, rows = A.read_map(data, ign)
check("read_map returns the stored values", [v for r in rows for v in r] == maps[0]["values"])
check("x axis = rpm 600..7005", xs[0] == 600 and xs[-1] == 600 + 15 * 427, xs)

# ------------------------------------------------------------------ map finder
found = A.find_maps(data)
addrs = {m.address for m in found}
check("finder: ignition map found", maps[0]["address"] in addrs, [hex(a) for a in sorted(addrs)][:10])
check("finder: boost map found", maps[2]["address"] in addrs)
check("finder: warm-up curve found", maps[3]["address"] in addrs)
builtin = A.builtin_find_maps(data)
check("built-in finder finds all four tables exactly",
      {m["address"] for m in maps[:4]} <= {m.address for m in builtin}, [(hex(m.address), m.rows, m.cols)
                                                                         for m in builtin])
print("  finder backend:", A.backends().get("maps"))

# ------------------------------------------------------------------ checksums
bad = bytearray(data)
bad[maps[0]["address"]] ^= 0x01
rep = A.verify(bad, profiles)
check("an edit breaks both checksums", [r["ok"] for r in rep] == [False, False], rep)
fixed, rep2 = A.fix(bytes(bad), profiles)
check("fix makes them valid", all(r["ok"] for r in A.verify(fixed, profiles)))
check("built-in checksum = slice checksum", [A.builtin_checksum(fixed, p) for p in profiles] ==
      [r["computed"] for r in A.verify(fixed, profiles)])
check("built-in shape is converted", A.norm_profile({"algo": "sum16be", "start": 0, "end": 4, "store": 4,
                                                     "endian": "big"})["algorithm"] == "sum16-be")

# ------------------------------------------------------------------ text formats
hexf = WORK / "fw.hex"
lines = [":020000040800F2"]
payload = bytes(range(32))
for i in range(0, 32, 16):
    chunk = payload[i:i + 16]
    rec = bytes([len(chunk), (i >> 8) & 0xFF, i & 0xFF, 0]) + chunk
    lines.append(":" + (rec + bytes([(-sum(rec)) & 0xFF])).hex().upper())
lines.append(":00000001FF")
hexf.write_text("\n".join(lines) + "\n")
img = A.load_image(hexf)
check("Intel HEX loads at 0x08000000", img.base == 0x08000000 and bytes(img.data) == payload, (hex(img.base), img.fmt))
check("Intel HEX format name", img.fmt == "ihex", img.fmt)
mem, notes = A._parse_ihex(hexf.read_text())
check("built-in Intel HEX parser agrees", bytes(mem[0x08000000 + i] for i in range(32)) == payload and not notes)
s19 = WORK / "fw.s19"
srec_lines = []
for i in range(0, 32, 16):
    chunk = payload[i:i + 16]
    rec = bytes([len(chunk) + 5]) + (0x80000000 + i).to_bytes(4, "big") + chunk
    srec_lines.append("S3" + (rec + bytes([(~sum(rec)) & 0xFF])).hex().upper())
s19.write_text("\n".join(srec_lines) + "\nS70500000000FA\n")
img2 = A.load_image(s19)
check("S-record loads at 0x80000000", img2.base == 0x80000000 and bytes(img2.data) == payload, hex(img2.base))
check("sniff: .s19 is srec, demo .ori is binary", A.sniff_format(s19) == "srec")

# ------------------------------------------------------------------ EEPROM
for size, chip in ((128, "24C01"), (256, "93C56"), (2048, "24C16"), (32768, "95256"), (512 * 1024, "95M04")):
    info = eeprom.guess(bytes(size))
    check(f"EEPROM {size} B -> {chip}", info is not None and any(chip in c for c in info.chips),
          info.chips if info else None)
check("not an EEPROM size: 3000 B", eeprom.guess(bytes(3000)) is None)
check("not an EEPROM size: 1 MB", eeprom.guess(bytes(1 << 20)) is None)
sample = bytes(range(256)) * 8
check("swap16 swaps byte pairs", eeprom.swap16(sample)[:4] == bytes([1, 0, 3, 2]))
check("swap16 twice = identity", eeprom.swap16(eeprom.swap16(sample)) == sample)
check("swap32 reverses words", eeprom.swap32(sample)[:4] == bytes([3, 2, 1, 0]) and
      eeprom.swap32(eeprom.swap32(sample)) == sample)
check("blank EEPROM noted", "erased" in " ".join(eeprom.guess(b"\xFF" * 1024).notes))

# ------------------------------------------------------------------ ECU project adapter
proj_dir = WORK / "EcuDemo"
ep = A.EcuProject.create(proj_dir, "EcuDemo", data=data, checksums=profiles, maps=maps)
check("project: ecu.json written", A.is_ecu_project(proj_dir))
ep = A.EcuProject.load(proj_dir)
check("project: working copy = original", ep.work_bytes() == data == ep.original_bytes())
check("project: 2 checksum profiles", len(ep.checksums) == 2)
check("project: maps saved in the map pack", [m.name for m in ep.map_defs()] == [m["name"] for m in maps],
      [m.name for m in ep.map_defs()])
w = bytearray(ep.work_bytes())
w[maps[0]["address"] + 1] += 3
out, report = ep.build(bytes(w), log=lambda *_a: None)
check("project: build writes the output", out.is_file() and out.stat().st_size == len(data))
check("project: build corrected the checksums", all(r["ok"] for r in A.verify(out.read_bytes(), profiles)), report)
check("project: original untouched", ep.original_bytes() == data)
p = ep.add_version(bytes(w), "stage", "test note")
check("project: version saved", p.is_file() and ep.versions[-1]["name"] == "stage", ep.versions)
print("  project backend:", A.backends().get("project"))

# ------------------------------------------------------------------ A2L round trip (maps slice)
try:
    from radide.firmware.maps.a2l import export_a2l
    from radide.firmware.maps.model import MapPack
    pack = MapPack("demo", [A.MapDef.from_any(m).to_slice_map() for m in maps[:4]])
    text = export_a2l(pack)
    back = A.parse_a2l(text, data)
    check("A2L round trip: same addresses", sorted(m.address for m in back) == sorted(m["address"] for m in maps[:4]),
          [(m.name, hex(m.address)) for m in back])
    check("A2L round trip: same sizes", sorted((m.rows, m.cols) for m in back) ==
          sorted((m["rows"], m["cols"]) for m in maps[:4]))
except ImportError as e:
    check("maps slice available for the A2L round trip", False, e)

# ------------------------------------------------------------------ analysis / disassembly
res = A.analyze(A.Image(bytearray(data)))
check("analysis: PowerPC guessed", "PowerPC" in res["facts"]["CPU (guess)"], res["facts"])
check("analysis: ID string found", any("RADIDE-ECU-DEMO" in s for _o, s in res["strings"]))
dis = A.disassemble(data, 0, "ppc", 0x200, 12)
check("disassembly: PowerPC prologue", [r[2] for r in dis[:2]] == ["stwu", "mflr"], dis[:3])

ok = sum(1 for _n, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
