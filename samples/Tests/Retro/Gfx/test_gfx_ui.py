"""IDE test of the retro graphics / text tools (qh.py harness: offscreen, QSettings "RADIDE-TEST", widget.grab()).

Run:  .venv\\Scripts\\python.exe samples\\Tests\\Retro\\Gfx\\test_gfx_ui.py
Works on copies of samples/Tests/Retro/Gfx/Sample in the QA work folder."""
from __future__ import annotations

import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "retro_gfx")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "QA", "Integration")))
import qh  # noqa: E402
from qh import check, finish, pump, shot, window  # noqa: E402

from PyQt6.QtCore import QPoint, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

WORK = os.path.join(qh.WORK, "retro_gfx")
shutil.rmtree(WORK, ignore_errors=True)
shutil.copytree(os.path.join(HERE, "Sample"), WORK)

w = window()
from radide.retro.gfx.textable import TextTable  # noqa: E402
from radide.retro.gfx.ui_playfield import PlayfieldEditor  # noqa: E402
from radide.retro.gfx.ui_text import TableEditor  # noqa: E402
from radide.retro.gfx.ui_tilemap import TilemapEditor  # noqa: E402
from radide.retro.gfx.ui_tiles import TileEditor  # noqa: E402

feat = getattr(w, "retro_gfx", None)
check("feature installed", feat is not None)
tools = next(a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == "Tools")
retro = next((a.menu() for a in tools.actions() if a.menu() and a.text().replace("&", "") == "Retro"), None)
gfx = retro and next((a.menu() for a in retro.actions() if a.menu() and "Graphics" in a.text()), None)
check("Tools > Retro > Graphics & Text menu", gfx is not None and
      any("Tile Editor" in a.text() for a in gfx.actions()) and any("Script" in a.text() for a in gfx.actions()))

# ------------------------------------------------------------------ tile editor on a CHR file
chr_path = os.path.join(WORK, "homebrew.chr")
orig = open(chr_path, "rb").read()
ed = w.open_any_file(chr_path)
pump(0.5)
check("opening .chr shows the Tile Editor", isinstance(ed, TileEditor) and w.tabs.currentWidget() is ed)
check("NES format guessed", ed.sheet.fmt.key == "nes")
ed.sheet_view.set_selection(1, 0, 1, 1)                     # tile 1 = digit 0
pump(0.2)
check("selected tile decoded", any(v for r in ed.pixels.block for v in r))
ed.set_tool("pencil")
ed.palette.current = 3
pv = ed.pixels
pv.resize(320, 320)
sx, sy = pv.scale()
QTest.mouseClick(pv, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(sx // 2, sy // 2))
pump(0.2)
check("pencil click draws colour 3", ed.pixels.block[0][0] == 3, ed.pixels.block[0])
check("document modified + tab title *", ed.is_modified() and w.tabs.tabText(w.tabs.indexOf(ed)).endswith("*"))
ed.undo()
check("undo", ed.pixels.block[0][0] != 3 and not ed.is_modified())
ed.redo()
check("redo", ed.pixels.block[0][0] == 3)
ed.transform(lambda b: [r[::-1] for r in b], "Flip")
check("flip horizontal", ed.pixels.block[0][7] == 3)
ed.set_tool("fill")
ed.palette.current = 2
QTest.mouseClick(pv, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(1, sy * 3 + 1))                  # background left of the digit
pump(0.2)
check("fill tool", sum(v == 2 for r in ed.pixels.block for v in r) > 10)
ed.block_combo.setCurrentIndex(1)                          # 2x2 tiles
pump(0.2)
check("2x2 tile edit block", len(ed.pixels.block) == 16 and len(ed.pixels.block[0]) == 16)
ed.step("tile", 1)
check("offset navigation +tile", ed.sheet.offset == 16 and ed.off_spin.value() == 16)
ed.step("tile", -1)
shot(w, "retro_gfx_tile_editor")

# ---- write back + the tile map that uses this CHR is refreshed (filebus)
mp = w.open_any_file(os.path.join(WORK, "level.rtmap"))
pump(0.5)
check("opening .rtmap shows the Tile Map Editor", isinstance(mp, TilemapEditor))
check("tile set loaded relative to the map", mp.src.sheet is not None and mp.tileset_path().name == "homebrew.chr")
shot(w, "retro_gfx_tilemap")
reloads = []
orig_reload = mp.reload_from_disk
mp.reload_from_disk = lambda: (reloads.append(1), orig_reload())
w.tabs.setCurrentWidget(ed)
check("save writes the bytes back into the file", ed.save() and open(chr_path, "rb").read() != orig and
      open(chr_path, "rb").read() == bytes(ed.sheet.data))
check("other editor of that file refreshed", reloads == [1])
check("saved -> not modified", not ed.is_modified() and not w.tabs.tabText(w.tabs.indexOf(ed)).endswith("*"))
# ---- external change reloads the tile editor
data = bytearray(open(chr_path, "rb").read())
data[16:32] = bytes(16)
open(chr_path, "wb").write(data)
from radide.retro import filebus  # noqa: E402
filebus.file_changed(w, chr_path, source=None)
check("filebus reloads the tile editor from disk", bytes(ed.sheet.data[16:32]) == bytes(16))

# ---- PNG export / import through the editor
png = os.path.join(WORK, "page.png")
ed.export_png(png)
check("export PNG", os.path.getsize(png) > 100)
ed.sheet_view.set_selection(4, 4, 1, 1)
n = ed.import_png(png)
check("import PNG at the selected tile quantises into tiles", n > 0 and ed.is_modified())
ed.undo()

# ---- Atari 2600 player graphics
bin_path = os.path.join(WORK, "castle.bin")
ed2 = feat.open_tiles(bin_path, fmt="a2600")
pump(0.3)
ed2.h_spin.setValue(8)
ed2.set_offset(0x80)
ed2.sheet_view.set_selection(0, 0, 1, 1)
pump(0.2)
check("2600 player decoded from castle.bin", ed2.pixels.block[0] == [0, 0, 0, 1, 1, 0, 0, 0], ed2.pixels.block[:2])
check("2600 preview and .byte listing shown", ed2.preview_box.isVisibleTo(ed2) and "%00011000" in ed2.asm_label.text())
ed2.nusiz_combo.setCurrentIndex(3)
ed2.reflect_check.setChecked(True)
pump(0.2)
shot(w, "retro_gfx_2600_player")
ed2.bottom_up.setChecked(True)
pump(0.1)
check("upside-down storage flips the view", ed2.pixels.block[-1] == [0, 0, 0, 1, 1, 0, 0, 0])
ed2.bottom_up.setChecked(False)

# ------------------------------------------------------------------ playfield editor
pfe = w.open_any_file(os.path.join(WORK, "castle.rtpf"))
pump(0.3)
check("opening .rtpf shows the Playfield Editor", isinstance(pfe, PlayfieldEditor) and pfe.pf.height == 16)
check("reflected castle drawn on both halves", pfe.pf.get(0, 0) == 1 and pfe.pf.get(39, 0) == 1)
check("DASM tables listed", "Playfield_PF0:" in pfe.asm.toPlainText())
cv = pfe.canvas
QTest.mouseClick(cv, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                 QPoint(5 * cv.cw + 2, 18 + 3 * cv.ch + 2))
pump(0.1)
check("click toggles a playfield block", pfe.pf.get(5, 3) == 1 and pfe.is_modified())
n = pfe.write_binary(bin_path, 0x20)
from radide.retro.gfx.atari2600 import Playfield  # noqa: E402
back = Playfield.from_binary(open(bin_path, "rb").read(), 0x20, 16, reflect=True)
check("write playfield into castle.bin and read back", n == 1 and back.rows[3][:20] == pfe.pf.rows[3][:20])
check("tile editor of castle.bin refreshed after the playfield write", bytes(ed2.sheet.data) ==
      open(bin_path, "rb").read())
pfe.asym.setChecked(True)
pump(0.1)
check("asymmetric mode: 6 tables", "Playfield_PF2R:" in pfe.asm.toPlainText())
shot(w, "retro_gfx_playfield")
check("save .rtpf", pfe.save() and not pfe.is_modified())

# ------------------------------------------------------------------ text table editor
te = w.open_any_file(os.path.join(WORK, "demo.tbl"))
pump(0.3)
check("opening .tbl shows the Text Table Editor", isinstance(te, TableEditor))
t = te.table()
check("table has ASCII + Arabic forms", t.entries.get(b"A") == "A" and t.entries.get(b"\x80") is not None and
      not t.errors, t.errors)
te.test_text.setText("أهلا!<end>")
te.shape_check.setChecked(True)
pump(0.1)
check("encode test with Arabic shaping has no missing letters", "not in the table" not in te.test_hex_out.text()
      and te.test_hex_out.text().endswith("00"), te.test_hex_out.text())
check("check: no problems", te.check() == [])
shot(w, "retro_gfx_table")

# ------------------------------------------------------------------ script dump / insert
se = feat.open_script(os.path.join(WORK, "demo.rom"), os.path.join(WORK, "demo.tbl"))
se.ptr_off.setValue(0x40)
se.ptr_count.setValue(5)
se.ptr_base.setValue(0x8000)
se.ptr_add.setValue(0x10)
check("dump by pointer table", se.dump() and se.sheet.rowCount() == 5 and
      se.sheet.item(1, 4).text() == "PRESS START<end>")
n = se.load_sheet(os.path.join(WORK, "demo_ar.csv"))
check("load the Arabic sheet", n == 5 and se.sheet.item(0, 5).text().startswith("أ"))
se.shape.setChecked(True)
se.rtl.setChecked(True)
se.ins_mode.setCurrentIndex(0)
check("in place refuses the longer Arabic text", not se.do_insert() and "NOT inserted" in se.report.toPlainText())
se.ins_mode.setCurrentIndex(1)
se.reg_start.setValue(0x100)
se.reg_end.setValue(0x180)
ok = se.do_insert()
out = os.path.join(WORK, "demo_translated.rom")
check("repack insert writes demo_translated.rom", ok and os.path.isfile(out), se.report.toPlainText())
from radide.retro.gfx.script import PointerSpec, dump_pointers  # noqa: E402
from radide.retro.gfx import arabic  # noqa: E402
tb = TextTable.load(os.path.join(WORK, "demo.tbl"))
d = dump_pointers(open(out, "rb").read(), tb, PointerSpec(0x40, 5, 2, "little", 0x8000, 0x10))
check("translated ROM decodes to the shaped right-to-left Arabic", d.entries[2].original ==
      arabic.prepare("انتهت اللعبة<end>") and d.entries[4].original == "HELLO!<end>",
      [e.original for e in d.entries])
csv_out = os.path.join(WORK, "sheet_out.csv")
se.save_sheet(csv_out)
check("save sheet CSV (UTF-8)", "انتهت" in open(csv_out, encoding="utf-8-sig").read())
shot(w, "retro_gfx_script")

# ------------------------------------------------------------------ Arabic UI
from radide import i18n  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
i18n.set_language(QApplication.instance(), "ar")
pump(0.5)
w.tabs.setCurrentWidget(ed)
pump(0.3)
missing = [s for s in ("Tile Editor (Open ROM / Binary)...", "Atari 2600 Playfield Editor", "Script Dump / Insert",
                       "Pencil", "Write to File", "Add Arabic Letter Forms", "Shape Arabic",
                       "Right-to-left (visual order)", "Graphics && Text", "Retro")
           if i18n.tr(s) == s]
check("Arabic translations for the new UI", not missing, missing)
shot(w, "retro_gfx_tile_editor_ar")
i18n.set_language(QApplication.instance(), "en")
pump(0.3)

# close prompts: modified docs ask; the harness answers Yes (= save)
mp.set_modified(False)
for doc in (ed, ed2, pfe, te, se, mp):
    doc.set_modified(False)
finish(w)
