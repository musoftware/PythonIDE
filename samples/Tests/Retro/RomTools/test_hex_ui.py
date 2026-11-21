"""IDE test of the ROM workbench (qh.py harness: offscreen, QSettings "RADIDE-TEST", widget.grab() only).

Run:  python samples\\Tests\\Retro\\RomTools\\test_hex_ui.py
Opens synthetic ROMs (radide/retro/rom/synth.py, no game data) in the hex editor: type, undo, search, save, fix a
checksum, compare two files, then creates a ROM Hacking project (Demo ROM template) and builds it."""
from __future__ import annotations

import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "retro_rom")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "QA", "Integration")))
import qh  # noqa: E402
from qh import check, finish, pump, shot, window  # noqa: E402

from pathlib import Path  # noqa: E402

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

WORK = Path(qh.WORK) / "retro_rom"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)

from radide.retro.rom import synth  # noqa: E402
from radide.retro.rom.detect import detect  # noqa: E402

nes = WORK / "homebrew.nes"
nes.write_bytes(synth.nes_rom())
w = window()
feat = getattr(w, "rom_feature", None)
check("feature installed", feat is not None)
tools = next(a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == "Tools")
retro = next((a.menu() for a in tools.actions() if a.menu() and a.text().replace("&", "") == "Retro"), None)
rw = retro and next((a.menu() for a in retro.actions() if a.menu() and "ROM Workbench" in a.text().replace("&", "")),
                    None)
check("Tools > Retro > ROM Workbench menu", rw is not None and
      any("Hex Editor" in a.text().replace("&", "") for a in rw.actions()))

from radide.retro.rom.hexdoc import HexDocument  # noqa: E402

w.open_any_file(nes)
pump(0.5)
doc = w.tabs.currentWidget()
check("a .nes file opens in the hex editor", isinstance(doc, HexDocument), type(doc))
rows = dict(doc.info.rows)
check("ROM info panel: NES, NROM, 16 KB PRG", rows.get("Mapper", "").startswith("0 - NROM") and
      rows.get("PRG ROM") == "16 KB", rows)
check("structure overlay: header fields", any(f.name == "PRG ROM" and f.offset == 4 for f in doc.view.fields))
v = doc.view
v.setFocus()
v.set_cursor(0x20)
QTest.keyClicks(v, "AB")
pump(0.2)
check("typing hex digits overwrites a byte", doc.buf.data[0x20] == 0xAB and v.cursor == 0x21, hex(doc.buf.data[0x20]))
check("tab shows modified", w.tabs.tabText(w.tabs.indexOf(doc)).endswith("*"), w.tabs.tabText(w.tabs.indexOf(doc)))
QTest.keyClick(v, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
pump(0.2)
check("Ctrl+Z undoes the whole byte", doc.buf.data[0x20] == nes.read_bytes()[0x20] and not doc.is_modified(),
      hex(doc.buf.data[0x20]))
QTest.keyClick(v, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
pump(0.2)
check("Ctrl+Y redoes", doc.buf.data[0x20] == 0xAB)
# insert mode + text area
QTest.keyClick(v, Qt.Key.Key_Insert)
v.area = "text"
v.set_cursor(0x30)
size = len(doc.buf)
QTest.keyClicks(v, "RAD")
check("insert mode in the text column", len(doc.buf) == size + 3 and doc.buf.read(0x30, 3) == b"RAD")
QTest.keyClick(v, Qt.Key.Key_Insert)
check("Insert toggles back to overwrite", not v.insert_mode)
# search
QTest.keyClick(v, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
pump(0.2)
check("Ctrl+F shows the Find bar", doc.find_panel.isVisible())
doc.find_panel.mode.setCurrentIndex(0)
doc.find_panel.find.setText("48 45 4C ?? 4F")
check("hex search with wildcard finds HELLO", doc.find_next() and v.cursor == 0x110 + 3, hex(v.cursor))
doc.find_panel.mode.setCurrentIndex(1)
doc.find_panel.find.setText("rad ide")
doc.find_panel.case.setChecked(False)
check("text search (case-insensitive) Find All", doc.find_all() == 1 and doc.results.count() == 1)
doc.find_panel.find.setText("FROM")
doc.find_panel.replace.setText("FRUM")
check("replace all", doc.replace(True) == 1 and b"FRUM" in bytes(doc.buf.data))
shot(w, "retro_rom_hex_nes")
# save
w.save_all()
pump(0.3)
disk = nes.read_bytes()
check("Save All writes the file", disk[0x20] == 0xAB and b"FRUM" in disk and len(disk) == size + 3)
check("saved: no * in the tab", not w.tabs.tabText(w.tabs.indexOf(doc)).endswith("*"))
# go to + inspector
doc.goto(0x10)
insp = {doc.inspector.item(i, 0).text(): doc.inspector.item(i, 1).text() for i in range(doc.inspector.rowCount())}
check("inspector: 6502 opcode + CPU address at the PRG start", insp.get("6502", "").startswith("SEI") and
      insp.get("CPU address (6502)") == "$C000", insp)

# ------------------------------------------------------------------ checksum fix on a GB ROM
gb = bytearray(synth.gb_rom())
gb[0x300] = 0x77
gbp = WORK / "broken.gb"
gbp.write_bytes(bytes(gb))
gdoc = w.open_hex(gbp)
check("broken GB checksum detected", gdoc.info.checksum_ok is False)
gdoc.fix_checksum()
check("Fix Header Checksum (undoable, then saved)", gdoc.info.checksum_ok and gdoc.is_modified())
gdoc.save()
check("fixed GB ROM on disk", detect(gbp.read_bytes(), "broken.gb").checksum_ok)
shot(gdoc, "retro_rom_gb_info")

# ------------------------------------------------------------------ compare
a, b = WORK / "a.sfc", WORK / "b.sfc"
a.write_bytes(synth.snes_rom())
bb = bytearray(synth.snes_rom())
bb[0x100:0x104] = b"DIFF"
bb[0x5000] ^= 1
b.write_bytes(bytes(bb))
cv = feat.compare(str(a), str(b))
check("Compare Files: 2 differences", cv is not None and len(cv.ranges) == 2, getattr(cv, "ranges", None))
cv.goto_diff(1)
check("Next Difference moves both views", cv.views[0].cursor == 0x100 and cv.views[1].cursor == 0x100)
shot(cv, "retro_rom_compare")

# ------------------------------------------------------------------ ROM Hacking project
from radide.languages import get_plugin  # noqa: E402

plugin = get_plugin("retro-romhack")
pfolder = WORK / "DemoHack"
plugin.create_new_project(pfolder, "DemoHack", "romhack_demo")
w.open_project(pfolder, ask=False)
pump(1.0)
check("ROM Hacking project opened", w.project is not None and w.project.language == "retro-romhack")
from radide.features.solution_ui import tree_items  # noqa: E402

items = tree_items(w)
check("Solution Explorer: ROM Hacking / Source ROM / Patches nodes",
      any(t == "ROM Hacking" for _d, t, _x in items) and any(t.startswith("Source ROM: demo.nes") for _d, t, _x in items)
      and any(t == "001_message.ips" for _d, t, _x in items), [t for _d, t, _x in items])
src_doc = feat.view_source()
check("the source ROM opens read-only", src_doc is not None and src_doc.read_only and src_doc.view.read_only)
src_doc.view.set_cursor(0x30)
QTest.keyClicks(src_doc.view, "FF")
check("typing into the read-only source ROM does nothing", src_doc.buf.data[0x30] == synth.nes_rom()[0x30])
pm = feat.open_manager()
check("Patch Manager lists the demo patch", pm is not None and pm.list.count() == 1)
out = pm.build()
check("Build writes the patched ROM", out is not None and b"PATCHED BY RAD IDE" in out.read_bytes() and
      (pfolder / "rom" / "demo.nes").read_bytes() == synth.nes_rom())
work = pm.edit_work()
pump(0.3)
wdoc = w.tabs.currentWidget()
check("Edit Working Copy opens work/ in the hex editor", isinstance(wdoc, HexDocument) and not wdoc.read_only and
      Path(wdoc.path) == work)
wdoc.view.set_cursor(0x200)
wdoc.view.area = "hex"
QTest.keyClicks(wdoc.view, "4142")
wdoc.save()
check("Capture Edits as Patch adds patch 2", pm.capture("more") and len(pm.rp.patches) == 2 and
      pm.rp.patches[1].file.endswith(".ips"))
out = pm.build()
check("rebuild contains the captured edit", out.read_bytes()[0x200:0x202] == b"AB")
w._fill_solution()
pump(0.3)
check("Solution Explorer shows the Build output", any(t.startswith("Build: DemoHack_patched.nes")
                                                     for _d, t, _x in tree_items(w)))
shot(w, "retro_rom_project")
# Ctrl+F5: build + hand the ROM to the emulator slice (dry run: the command is resolved, no emulator starts;
# when none is installed the Output says how to get one)
os.environ["RADIDE_RETRO_DRY_RUN"] = "1"
w.run_project(debug=False)
got = qh.wait(lambda: "Build: build/DemoHack_patched.nes" in w.output.toPlainText() and
              ("Emulator command (dry run)" in w.output.toPlainText() or
               "Cannot start an emulator" in w.output.toPlainText()), 60)
check("Ctrl+F5 builds and hands the ROM to the emulator slice", got, w.output.toPlainText()[-800:])
qh.wait(lambda: w.session is None or not w.session.running(), 30)
finish(w)
