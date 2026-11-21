"""Retro QA (end to end, as a user): the workflows that cross the retro slices.

1. ROM hacking: New Project > ROM Hacking Project (Demo ROM) -> Patch Manager -> Edit Working Copy -> type bytes
   in the hex editor -> Capture Edits as Patch (IPS) -> open the same working copy in the Tile Editor, draw on a
   CHR tile, Write to File (the open hex editor refreshes) -> Script Dump (table) of the message, translate it,
   Insert in place into the working copy -> Capture Edits as Patch (BPS) -> Build -> the patched ROM equals the
   working copy, the original ROM is untouched -> Tools > Retro > ROM Workbench Create Patch / Apply Patch dialogs
   (BPS + IPS) give the same bytes -> F5 runs the patched ROM in the real emulator, Stop closes it.
2. Disassemble ROM into Project for a NES (ca65) and a Game Boy (RGBDS) ROM built from the templates, and for
   the ROM slice's synthetic NES ROM: the rebuild is byte-identical.
3. Apollo: Hello DSKY F5 -> DSKY dock, V35E lights 88888 -> Stop; Comanche055 downloaded (official Virtual AGC
   GitHub) into the work folder, opened as a project, Build with yaYUL -> 0 errors.  (--no-net skips it.)
4. Legacy Fortran: the OrbitTable sample, Ctrl+F5 output equals expected_output.txt.

    python samples/Tests/Retro/QA/e2e_workflows.py [rom] [disasm] [agc] [fortran] [--no-net]
"""
import os
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault("QA_NAME", "retro_qa_workflows")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

import psutil  # noqa: E402
from PyQt6.QtCore import QPoint, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

from radide.languages import get_plugin  # noqa: E402

REPO = Path(qh.ROOT)
PARTS = [a for a in sys.argv[1:] if not a.startswith("-")] or ["rom", "disasm", "agc", "fortran"]
NO_NET = "--no-net" in sys.argv or bool(os.environ.get("RADIDE_OFFLINE"))
WORK = Path(qh.WORK) / "retro_qa_workflows"
EMU_NAMES = ("stella", "mesen", "fceux", "mgba", "x64sc", "atari800", "dosbox", "yaagc")


def emu_children(pid: int):
    try:
        return [k for k in psutil.Process(pid).children(recursive=True)
                if any(n in (k.name() or "").lower() for n in EMU_NAMES)]
    except psutil.Error:
        return []


def wait_gone(pids, timeout=10):
    def gone():
        for p in pids:
            try:
                if psutil.Process(p).status() != psutil.STATUS_ZOMBIE:
                    return False
            except psutil.Error:
                pass
        return True
    return wait(gone, timeout)


# ===================================================================== 1. ROM hacking
def rom_workflow(w):
    from radide.retro.gfx.ui_tiles import TileEditor
    from radide.retro.rom.dialogs import ApplyPatchDialog, CreatePatchDialog
    from radide.retro.rom.hexdoc import HexDocument
    from radide.retro.rom.patches import apply_patch
    from radide.retro.rom.project import RomProject

    folder = WORK / "HackDemo"
    get_plugin("retro-romhack").create_new_project(folder, "HackDemo", "romhack_demo")
    w.open_project(folder, ask=False)
    pump(1.5)
    check("rom: ROM Hacking project opened", w.project is not None and w.project.language == "retro-romhack")
    rp = RomProject.load(folder)
    src = rp.rom_path
    src_before = src.read_bytes()
    w.rom_feature.open_manager()
    pump(0.5)
    pm = w.tabs.currentWidget()
    check("rom: Patch Manager opens", type(pm).__name__ == "PatchManager", type(pm).__name__)
    shot(w, "retro_qa_patch_manager")
    # ---- hex edit in the working copy
    work = pm.edit_work()
    pump(0.8)
    hexdoc = w.tabs.currentWidget()
    check("rom: Edit Working Copy opens the hex editor", isinstance(hexdoc, HexDocument) and work is not None
          and Path(hexdoc.path) == Path(work), type(hexdoc).__name__)
    hexdoc.view.set_cursor(0x300)
    hexdoc.view.area = "hex"
    QTest.keyClicks(hexdoc.view, "DEADBEEF")
    pump(0.2)
    check("rom: typed DE AD BE EF at $300", bytes(hexdoc.buf.data[0x300:0x304]) == b"\xde\xad\xbe\xef",
          bytes(hexdoc.buf.data[0x300:0x304]).hex())
    hexdoc.save()
    w.tabs.setCurrentWidget(pm)
    pm.fmt.setCurrentText("ips")
    check("rom: Capture Edits as Patch (IPS)", pm.capture("hex_bytes"),
          pm.log.toPlainText()[-400:])
    ips = sorted((folder / "patches").glob("*hex_bytes*.ips"))
    check("rom: the IPS patch file exists and is listed", ips and pm.list.count() >= 2,
          [p.name for p in (folder / "patches").iterdir()])
    # ---- tile editor on the same working copy (iNES -> starts at the CHR ROM)
    ted = w.retro_gfx.open_tiles(work)
    pump(0.6)
    check("rom: Tile Editor opens the working copy", isinstance(ted, TileEditor), type(ted).__name__)
    chr_off = 16 + 16384 * src_before[4]
    check("rom: Tile Editor starts at the CHR ROM", ted.sheet.offset == chr_off, (hex(ted.sheet.offset), hex(chr_off)))
    ted.sheet_view.set_selection(1, 0, 1, 1)
    pump(0.2)
    ted.set_tool("pencil")
    ted.palette.current = 3
    pv = ted.pixels
    pv.resize(320, 320)
    sx, sy = pv.scale()
    before_tile = bytes(Path(work).read_bytes()[chr_off + 16:chr_off + 32])
    for x in range(8):        # a line of colour 3 across row 0 of tile 1
        QTest.mouseClick(pv, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(x * sx + sx // 2, sy // 2))
    pump(0.2)
    check("rom: pencil drew a row of colour 3", ted.pixels.block[0] == [3] * 8, ted.pixels.block[0])
    shot(w, "retro_qa_tile_edit")
    check("rom: Tile Editor Write to File", ted.save())
    pump(0.6)
    after = Path(work).read_bytes()
    check("rom: tile bytes written into the working copy (plane 0 + 1 row 0 = $FF)",
          after[chr_off + 16] == 0xFF and after[chr_off + 24] == 0xFF and
          after[chr_off + 16:chr_off + 32] != before_tile, after[chr_off + 16:chr_off + 32].hex())
    check("rom: the open hex editor refreshed from disk (file bus)",
          bytes(hexdoc.buf.data[chr_off + 16:chr_off + 17]) == b"\xff" and not hexdoc.is_modified())
    # ---- script dump / insert with the project's table
    se = w.retro_gfx.open_script(str(work), str(folder / "tables" / "ascii.tbl"))
    pump(0.4)
    se.mode.setCurrentIndex(se.mode.findData("ranges"))
    se.ranges.setText("110-122")
    msg = Path(work).read_bytes()[0x110:0x122].decode("ascii", "replace")     # (the demo's 001 patch changed it)
    check("rom: Script Dump of the message by range", se.dump() and se.sheet.rowCount() >= 1 and
          se.sheet.item(0, 4).text() == msg, (msg, se.sheet.item(0, 4).text() if se.sheet.rowCount() else None))
    se.sheet.item(0, 5).setText("HALLO VON RAD IDE!")
    se.ins_mode.setCurrentIndex(se.ins_mode.findData("inplace"))
    se.out_edit.setText(str(work))
    ok = se.do_insert()
    check("rom: in-place insert into the working copy", ok and b"HALLO VON RAD IDE!" in Path(work).read_bytes(),
          se.report.toPlainText()[-600:])
    shot(w, "retro_qa_script")
    pump(0.5)
    check("rom: the hex editor shows the inserted text", b"HALLO VON RAD IDE!" in bytes(hexdoc.buf.data))
    w.tabs.setCurrentWidget(pm)
    pm.fmt.setCurrentText("bps")
    check("rom: Capture Edits as Patch (BPS) for the tile + text edits", pm.capture("tile_and_text"),
          pm.log.toPlainText()[-400:])
    bps = sorted((folder / "patches").glob("*tile_and_text*.bps"))
    check("rom: the BPS patch file exists", bool(bps))
    # ---- build
    out = pm.build()
    check("rom: Build writes the patched ROM", out is not None and Path(out).is_file(), pm.log.toPlainText()[-400:])
    if out is not None:
        check("rom: patched ROM == working copy (every edit captured)", Path(out).read_bytes() == Path(work).read_bytes())
    check("rom: the source ROM is unchanged", src.read_bytes() == src_before)
    # each patch applies on its own chain
    data = src_before
    for e in RomProject.load(folder).patches:
        if e.enabled:
            data = apply_patch(data, rp.path(e.file).read_bytes())
    check("rom: applying the patch chain by hand gives the same ROM", out is not None and data == Path(out).read_bytes())
    # ---- Tools > Retro > ROM Workbench: Create Patch / Apply Patch dialogs
    for fmt_i, ext in ((0, "bps"), (1, "ips")):
        d = CreatePatchDialog(w, str(src), str(out))
        d.fmt.setCurrentIndex(fmt_i)
        d.out.setText(str(WORK / f"whole.{ext}"))
        d.accept()
        check(f"rom: Create Patch dialog ({ext.upper()})", (WORK / f"whole.{ext}").is_file())
        a = ApplyPatchDialog(w, str(src), str(WORK / f"whole.{ext}"))
        a.out.setText(str(WORK / f"applied_{ext}.nes"))
        a.accept()
        check(f"rom: Apply Patch dialog ({ext.upper()}) rebuilds the patched ROM",
              (WORK / f"applied_{ext}.nes").is_file() and
              (WORK / f"applied_{ext}.nes").read_bytes() == Path(out).read_bytes())
    d = CreatePatchDialog(w, str(src), str(out))
    shot(d, "retro_qa_create_patch")
    d.close()
    # ---- F5: the patched ROM in the real emulator
    w.output.clear()
    w.run_project(debug=False)
    s = w.session
    spid = int(s.proc.processId()) if s is not None else 0
    got = wait(lambda: emu_children(spid) or (s is not None and not s.running()), 120)
    kids = emu_children(spid)
    cmd = " ".join(kids[0].cmdline()) if kids else ""
    check("rom: F5 starts the emulator with the patched ROM", got and kids and "HackDemo" in cmd and "build" in cmd,
          (cmd, w.output.toPlainText()[-800:]))
    if kids:
        pump(2)
        kp = [k.pid for k in kids]
        w.stop_project()
        check("rom: Stop closes the emulator", wait_gone(kp))


# ===================================================================== 2. disassembly
def disasm_workflow(w):
    import subprocess

    from radide.features import retro_dev
    from radide.retro.rom import synth
    roms = []
    for pid, tpl, name in (("retro-nes", "nes_asm", "NesSrc"), ("retro-gameboy", "gb_asm", "GbSrc")):
        folder = WORK / name
        plugin = get_plugin(pid)
        plugin.create_new_project(folder, name, tpl)
        r = subprocess.run(plugin.build_command(folder, None), shell=True, cwd=str(folder), capture_output=True,
                           text=True, errors="replace", timeout=600)
        built = [p for p in folder.iterdir() if p.suffix.lower() in (".nes", ".gb")]
        check(f"disasm: {name} builds ({tpl})", r.returncode == 0 and built, (r.stdout + r.stderr)[-800:])
        if built:
            dst = WORK / f"{name}{built[0].suffix}"
            shutil.copy2(built[0], dst)
            roms.append(dst)
    synth_rom = WORK / "SynthDemo.nes"
    synth_rom.write_bytes(synth.nes_rom())
    roms.append(synth_rom)
    for rom in roms:
        d = retro_dev.DisassembleDialog(w, str(rom))
        d.folder.setText(str(WORK / (rom.stem + "_disasm")))
        d.show()
        d.run()
        done = wait(lambda: d.result_obj is not None or "Could not" in d.summary.text(), 300)
        check(f"disasm: {rom.name} -> project, rebuild byte-identical", done and "byte-identical" in d.summary.text(),
              d.summary.text()[:600])
        shot(d, f"retro_qa_disasm_{rom.stem}")
        d.close()


# ===================================================================== 3. Apollo
def agc_workflow(w):
    folder = WORK / "HelloDSKY"
    get_plugin("agc-yul").create_new_project(folder, "HelloDSKY", "agc_hello")
    w.open_project(folder, ask=False)
    pump(1.5)
    w.run_project(debug=True)
    ok = wait(lambda: getattr(w, "_agc_dock", None) is not None and w._agc_dock.isVisible(), 30)
    check("agc: F5 shows the Apollo AGC dock", ok)
    s = w.session
    pump(3)
    panel = None
    try:
        from radide.agc.session import ensure_panel
        panel = ensure_panel(w)
    except Exception as e:  # noqa: BLE001
        check("agc: DSKY panel", False, repr(e))
    if panel is not None:
        for k in ("VERB", "3", "5", "ENTR"):           # click the DSKY's own buttons
            QTest.mouseClick(panel.dsky.buttons[k], Qt.MouseButton.LeftButton)
            pump(0.3)
        check("agc: V35E (clicked on the DSKY) lights +88888", wait(lambda: panel.dsky.model.r1 == "+88888", 6),
              getattr(panel.dsky.model, "r1", None))
        pump(0.5)
        shot(w, "retro_qa_agc_dsky")
    if s is not None and s.running():
        w.stop_project()
    pump(1)
    if NO_NET:
        print("SKIP Comanche055 (--no-net)")
        return
    from radide.agc import toolchain
    from radide.agc.apollo_source import download
    if not toolchain.status().get("yaYUL"):
        print("SKIP Comanche055 build: yaYUL not installed")
        return
    try:
        cfolder = download("Comanche055", WORK, log=lambda t: None)
    except Exception as e:  # noqa: BLE001
        print(f"SKIP Comanche055: download failed ({e})")
        return
    check("agc: Comanche055 downloaded with a project file + licence note",
          (cfolder / "project.radproj").is_file() and (cfolder / "README_RADIDE.txt").is_file(),
          [p.name for p in cfolder.iterdir()][:20])
    w.open_project(cfolder, ask=False)
    pump(1.5)
    check("agc: Comanche055 opens as an Apollo AGC project", w.project is not None and w.project.language == "agc-yul",
          getattr(w.project, "language", None))
    w.output.clear()
    from radide.features import retro_nasa
    retro_nasa.build_with_yayul(w)
    ok = wait(lambda: "[yaYUL] exit code" in w.output.toPlainText(), 300)
    out = w.output.toPlainText()
    check("agc: Build with yaYUL on Comanche055: exit code 0, 0 errors", ok and "[yaYUL] exit code 0, 0 error(s)" in out,
          out[-800:])
    shot(w, "retro_qa_comanche")
    # F5 on the real flight program: interpretive code -> yaYUL + yaAGC with the IDE's DSKY
    w.output.clear()
    w.run_project(debug=True)
    s = w.session
    check("agc: F5 on Comanche055 starts a session", wait(lambda: w.session is not None and w.session.running(), 120),
          w.output.toPlainText()[-800:])
    s = w.session
    print("Comanche session:", type(s).__name__, flush=True)
    panel = getattr(w, "_agc_panel", None)
    if panel is not None and s is not None:
        pump(8)                                  # let the AGC finish its fresh start
        ok = False
        for _attempt in range(3):
            for k in ("VERB", "3", "5", "ENTR"):
                QTest.mouseClick(panel.dsky.buttons[k], Qt.MouseButton.LeftButton)
                pump(0.4)
            if wait(lambda: panel.dsky.model.r1 == "+88888", 8):
                ok = True
                break
        check("agc: Comanche055 in yaAGC answers V35E on the IDE's DSKY", ok, getattr(panel.dsky.model, "r1", None))
        shot(w, "retro_qa_comanche_dsky")
    kids = [k.pid for k in psutil.Process().children(recursive=True) if "yaagc" in (k.name() or "").lower()]
    if s is not None and s.running():
        w.stop_project()
    check("agc: Stop ends yaAGC", wait_gone(kids, 10), kids)


# ===================================================================== 4. Fortran
def fortran_workflow(w):
    src = REPO / "samples" / "Tests" / "Retro" / "LegacyFortran" / "OrbitTable"
    folder = WORK / "OrbitTable"
    shutil.copytree(src, folder)
    w.open_project(folder, ask=False)
    pump(1.5)
    w.output.clear()
    w.run_project(debug=False)
    s = w.session
    ok = wait(lambda: s is not None and not s.running(), 180)
    out = w.output.toPlainText()
    exp = (src / "expected_output.txt").read_text(encoding="utf-8")
    lines = [ln.rstrip() for ln in exp.strip().splitlines()]
    check("fortran: Ctrl+F5 prints the expected orbit table", ok and all(ln in out for ln in lines if ln.strip()),
          out[-1200:])
    shot(w, "retro_qa_fortran")


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    w = qh.window()
    for name, fn in (("rom", rom_workflow), ("disasm", disasm_workflow), ("agc", agc_workflow),
                     ("fortran", fortran_workflow)):
        if name in PARTS:
            t = time.time()
            try:
                fn(w)
            except Exception as e:  # noqa: BLE001
                import traceback
                traceback.print_exc()
                check(f"{name}: workflow ran without an exception", False, repr(e))
            print(f"--- {name}: {time.time() - t:.0f} s", flush=True)
    qh.finish(w)


if __name__ == "__main__":
    main()
