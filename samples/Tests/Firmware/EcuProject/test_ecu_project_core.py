"""ECU project tests (no Qt): radide/firmware/project.

Run:  python samples\\Tests\\Firmware\\EcuProject\\test_ecu_project_core.py

* new project from the synthetic demo image: original copied + read-only + SHA-256, working copy;
* an edit of a calibration map -> verify finds the broken CRC -> versions with notes -> map-level diff
  (radide/firmware/maps pack) -> Build (.bin / .hex / .s19 via radide/firmware/formats) with corrected checksums
  and a report naming the recalculated block -> the built file reloads to the same bytes;
* restore / delete versions, export BPS / IPS of the mod and import it into a fresh project (same bytes),
  the original is never written (guard + SHA-256 check stops the build when it changed);
* an Intel HEX original at 0x80000000 builds back to HEX at the same address;
* the command line (python -m radide.firmware.project build / verify / diff / report / find).
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.firmware.checksum.blocks import verify  # noqa: E402
from radide.firmware.project import synth  # noqa: E402
from radide.firmware.project.model import EcuProject, EcuProjectError, load_image, new_project, sha256  # noqa: E402
from radide.firmware.project.report import modification_report_html  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def demo_project(tmp: Path, name="Demo") -> EcuProject:
    src = tmp / f"{name}_stock.bin"
    src.write_bytes(synth.image())
    ep = new_project(tmp / name, name, src)
    ep.checksums = synth.demo_blocks()
    ep.maps = synth.demo_maps()
    ep.save()
    return ep


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="radide-ecu-"))
    ep = demo_project(tmp)
    ep = EcuProject.load(ep.folder)
    op = ep.original_path
    check("original copied into original/", op.is_file() and op.parent.name == "original")
    check("original is read-only on disk", not os.stat(op).st_mode & stat.S_IWRITE)
    check("SHA-256 recorded", ep.original_sha256 == sha256(op.read_bytes()))
    check("working copy = original", ep.work_bytes() == op.read_bytes())
    check("check_original OK", ep.check_original()[0])
    check("ecu.json keeps 3 checksum blocks + 3 inline maps", len(ep.checksums) == 3 and len(ep.maps) == 3)
    try:
        ep.write_work.__func__(type("X", (), {"work_path": op, "_guard": ep._guard, "folder": ep.folder,
                                              "rel": ep.rel, "work": ep.work})(), b"x")
        check("writing the original is refused", False)
    except EcuProjectError:
        check("writing the original is refused", True)
    # ---- edit a calibration map (16x16 map cell [2][3] + one curve value)
    pack = ep.map_pack()
    m16 = pack.get("Demo map 16x16")
    data = bytearray(ep.work_bytes())
    cell = m16.address + (2 * 16 + 3) * 2
    v = int.from_bytes(data[cell:cell + 2], "big")
    data[cell:cell + 2] = (v + 25).to_bytes(2, "big")
    curve = pack.get("Demo curve")
    data[curve.address:curve.address + 2] = (1500).to_bytes(2, "big")
    ep.write_work(data)
    res = ep.verify_checksums()
    check("verify: only the calibration CRC is wrong after the edit",
          [r.name for r in res if not r.ok] == ["Calibration CRC32"], [r.line() for r in res])
    v1 = ep.snapshot("Map tweak", "16x16 cell +2.5, curve start 1500")
    ep.save()
    check("version saved with note", ep.version("v001").note.startswith("16x16") and Path(ep.path(v1.file)).is_file())
    d = ep.diff("original", "v001")
    names = [m.name for m in d.maps]
    check("map-level diff names the changed maps", names == ["Demo map 16x16", "Demo curve"], [m.line() for m in d.maps])
    mc = d.maps[0]
    check("map diff: 1 cell, +2.5 units", mc.cells_changed == 1 and abs(mc.max_delta - 2.5) < 1e-9, mc.line())
    check("byte diff: 2 ranges", len(d.ranges) == 2 and d.bytes_changed <= 4, d.ranges)
    # ---- build in three containers
    for cont, fmt in (("bin", "raw"), ("hex", "ihex"), ("s19", "srec")):
        ep.set_container(cont)
        ep.save()
        logs = []
        b = ep.build(log=logs.append)
        flat, f2, base = load_image(b.output)
        check(f"build .{cont}: output format {fmt}", f2 == fmt and b.output.suffix == "." + cont, (f2, b.output))
        check(f"build .{cont}: checksums of the output all OK", all(r.ok for r in verify(flat, ep.checksums)))
        check(f"build .{cont}: report names the recalculated block",
              [r.name for r in b.recalculated] == ["Calibration CRC32"] and
              "Calibration CRC32 @ 0xFFFC: recalculated" in b.report_path.read_text(encoding="utf-8"))
        check(f"build .{cont}: Path(result) = output file", Path(b) == b.output)
    rep = b.report_path.read_text(encoding="utf-8")
    check("report: changed maps + checksum range tagged", "Demo map 16x16" in rep and "[checksum]" in rep, rep[:800])
    html = modification_report_html(ep, bytes(flat), b.checksums)
    check("HTML report", html.startswith("<!doctype html>") and "Changed maps" in html and "Calibration CRC32" in html)
    check("work copy unchanged by Build (checksum fixed only in the output)", ep.work_bytes() == bytes(data))
    # ---- versions: second edit, restore, delete
    d2 = bytearray(ep.work_bytes())
    d2[0x8410] = 99
    ep.write_work(d2)
    saved = ep.restore("original")
    ep.save()
    check("restore original saves the unsaved working copy first", saved is not None and
          ep.version(saved.id).name.startswith("Before restoring"))
    check("after restore: work = original", ep.work_bytes() == ep.original_bytes())
    ep.restore("v001")
    check("restore v001", ep.work_bytes() == bytes(data))
    check("delete version", ep.delete_version(saved.id) and ep.version(saved.id) is None)
    ep.save()
    # ---- patches
    ep.set_container("bin")
    ep.save()
    built = load_image(ep.build(log=lambda s: None).output)[0]
    for fmt in ("bps", "ips"):
        p = ep.export_patch(ep.folder / "build" / f"mod.{fmt}")
        ep2 = demo_project(tmp, f"Imp{fmt}")
        ep2.import_patch(p)
        ep2.save()
        check(f"{fmt.upper()} export -> import into a fresh project = built image", ep2.work_bytes() == built)
        check(f"{fmt.upper()} import made a version", any(v.name.startswith("Imported") for v in ep2.versions))
    # ---- original changed on disk -> build stops
    os.chmod(op, stat.S_IREAD | stat.S_IWRITE)
    raw = bytearray(op.read_bytes())
    raw[0] ^= 0xFF
    op.write_bytes(raw)
    try:
        ep.build(log=lambda s: None)
        check("build stops when the original changed", False)
    except EcuProjectError as e:
        check("build stops when the original changed", "original file changed" in str(e), e)
    raw[0] ^= 0xFF
    op.write_bytes(raw)
    # ---- an Intel HEX original at 0x80000000
    from radide.firmware.formats import MemoryMap, save
    hexsrc = tmp / "flash.hex"
    save(MemoryMap.from_bytes(synth.image(), 0x80000000), hexsrc)
    eh = new_project(tmp / "HexProj", "HexProj", hexsrc)
    eh.checksums = synth.demo_blocks()
    eh.set_container("same")
    eh.save()
    check("HEX original: flat working copy + base 0x80000000",
          eh.original_format == "ihex" and eh.image_base == 0x80000000 and len(eh.work_bytes()) == 0x10000)
    w = bytearray(eh.work_bytes())
    w[0x8200] ^= 0x5A
    eh.write_work(w)
    bh = eh.build(log=lambda s: None)
    flat, fmt, base = load_image(bh.output)
    check("HEX build: same container, same address, checksums OK",
          fmt == "ihex" and base == 0x80000000 and bh.output.suffix == ".hex" and
          all(r.ok for r in verify(flat, eh.checksums)))
    # ---- command line
    env = dict(os.environ, PYTHONPATH=ROOT)

    def cli(*args):
        r = subprocess.run([sys.executable, "-m", "radide.firmware.project", *map(str, args)], capture_output=True,
                           text=True, env=env, cwd=str(tmp))
        return r.returncode, r.stdout + r.stderr
    rc, out = cli("verify", ep.folder)
    check("CLI verify reports the mismatch (exit 1)", rc == 1 and "MISMATCH" in out, out)
    rc, out = cli("build", ep.folder)
    check("CLI build", rc == 0 and "recalculated" in out and "Output:" in out, out)
    rc, out = cli("diff", ep.folder, "original", "v001")
    check("CLI diff shows maps", rc == 0 and "map Demo map 16x16" in out, out)
    rc, out = cli("report", ep.folder, tmp / "r.html")
    check("CLI report (HTML)", rc == 0 and (tmp / "r.html").read_text(encoding="utf-8").startswith("<!doctype"))
    rc, out = cli("find", op)
    check("CLI find", rc == 0 and "crc16-ccitt-false" in out, out[:500])
    # ---- the language plugin's templates (no Qt windows)
    from radide.languages.firmware_ecu import PLUGIN
    prj = PLUGIN.create_new_project(tmp / "TplDemo", "TplDemo", "ecu_demo")
    et = EcuProject.load(prj.folder)
    check("template 'ECU Project (Demo Firmware)': original, blocks, map pack, profile",
          et.original_path.is_file() and len(et.checksums) == 3 and et.map_pack() is not None and
          len(list(et.map_pack())) == 3 and (prj.folder / "profiles" / "demo_ecu.ecuprofile.json").is_file())
    PLUGIN.create_new_project(tmp / "TplEmpty", "TplEmpty", "ecu_empty")
    check("template 'ECU / Firmware Project' (empty)", (tmp / "TplEmpty" / "ecu.json").is_file())
    try:
        from radide.firmware.ui import adapters
        wa = adapters.EcuProject.load(prj.folder)
        check("workbench adapter reads the project (native model)", wa.native is not None and
              str(wa.working_path).endswith(".bin") and len(wa.checksums) == 3, (wa.working_path, wa.native))
    except ImportError:
        print("SKIP workbench adapter not present")
    shutil.rmtree(tmp, ignore_errors=True, onerror=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
