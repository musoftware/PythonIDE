"""IDE test of the retro game designers (qh.py harness: offscreen, QSettings "RADIDE-TEST", widget.grab()).

Run:  .venv\\Scripts\\python.exe samples\\Tests\\Retro\\DesignGames\\test_gamedesign_ui.py

Creates one design of each system in the QA work folder through Tools > Retro > Game Designers, paints with the
pencil / rectangle / fill tools, moves an object, edits properties, undo / redo, exports a PNG, saves (the code
is generated under gen/<name>/), reopens the file through File > Open and builds (when the toolchain is
installed; the build runs the same headless checks as test_gamedesign_core.py)."""
from __future__ import annotations

import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "retro_gamedesign")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "QA", "Integration")))
import qh  # noqa: E402
from qh import check, finish, pump, shot, wait, window  # noqa: E402

from pathlib import Path  # noqa: E402

from PyQt6.QtCore import QPoint, Qt  # noqa: E402

WORK = Path(qh.WORK) / "retro_gamedesign"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)

w = window()
feat = getattr(w, "retro_designs", None)
check("feature installed", feat is not None)
tools = next(a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == "Tools")
retro = next((a.menu() for a in tools.actions() if a.menu() and a.text().replace("&", "") == "Retro"), None)
gd = retro and next((a.menu() for a in retro.actions() if a.menu() and "Game" in a.text().replace("&", "")), None)
check("Tools > Retro > Game Designers menu", gd is not None and
      sum(1 for a in gd.actions() if a.text().startswith("New ")) >= 4, [a.text() for a in gd.actions()] if gd else None)

from radide.retro.design.game import EXTS, gen_dir, load  # noqa: E402
from radide.retro.design.game.ui import GameDesigner  # noqa: E402
from radide.retro.design.game.compat import find_tool  # noqa: E402

LEFT = Qt.MouseButton.LeftButton
eds = {}
for system in ("a2600", "nes", "gb", "dos13h"):
    ed = feat.new_design(system, folder=WORK, ask=False)
    pump(0.3)
    eds[system] = ed
    check(f"{system}: designer tab opened", isinstance(ed, GameDesigner) and w.tabs.currentWidget() is ed)
    check(f"{system}: saved into the folder", ed.path is not None and ed.path.is_file() and ed.path.suffix in EXTS)
    check(f"{system}: code generated on save", gen_dir(ed.path).is_dir() and any(gen_dir(ed.path).iterdir()))
    check(f"{system}: not modified after save", not ed.is_modified())

    # pencil stroke on the first layer
    lay = ed.doc.layers[0] if system != "a2600" else ed.doc.layer("Playfield")
    ed._select_layer_name(lay.name)
    ed.set_tool("pencil")
    before = bytes(lay.data)
    cw, ch = lay.cw, lay.ch
    row = 100 if system == "a2600" else 3          # 2600: below the frame the starter screen draws
    ed.press(QPoint(cw * 3, ch * row), LEFT)
    ed.drag(QPoint(cw * 9, ch * row), LEFT)
    ed.release(QPoint(cw * 3, ch * row), QPoint(cw * 9, ch * row), LEFT)
    pump(0.1)
    check(f"{system}: pencil stroke changes the layer + one undo step", bytes(lay.data) != before and ed.undo.count() == 1)
    check(f"{system}: tab title shows *", w.tabs.tabText(w.tabs.indexOf(ed)).endswith("*"))
    ed.a_undo.trigger()
    lay = ed.doc.layer(lay.name)
    check(f"{system}: undo restores the layer", bytes(lay.data) == before)
    ed.a_redo.trigger()
    lay = ed.doc.layer(lay.name)
    check(f"{system}: redo paints again", bytes(lay.data) != before)

    # rectangle + fill on the collision layer
    col = ed.doc.layer("Collision")
    ed._select_layer_name(col.name)
    ed.set_tool("rect")
    ed.press(QPoint(0, 0), LEFT)
    ed.release(QPoint(0, 0), QPoint(col.cw * 2, col.ch * 2), LEFT)
    col = ed.doc.layer("Collision")
    check(f"{system}: rectangle on the collision layer", col.get(0, 0) == 1 and col.get(2, 2) == 1)
    ed.set_tool("fill")
    ed.values[col.name] = 2
    ed.press(QPoint(col.cw * 5, col.ch * 5), LEFT)
    col = ed.doc.layer("Collision")
    check(f"{system}: fill on the collision layer", col.get(5, 5) == 2)

    # select + drag an object, property edit
    ed._select_layer_name("Objects")
    o = next(o for o in ed.doc.objects if o.get("enabled", True))
    i = ed.doc.objects.index(o)
    from radide.retro.design.game.ui import object_bounds  # noqa: E402
    r = object_bounds(ed.doc, o)
    x0, y0 = o["x"], o["y"]
    ed.press(QPoint(r.x() + r.width() // 2, r.y() + r.height() // 2), LEFT)
    ed.drag(QPoint(r.x() + r.width() // 2 + 6, r.y() + r.height() // 2 + 4), LEFT)
    ed.release(QPoint(0, 0), QPoint(0, 0), LEFT)
    o = ed.doc.objects[i]
    check(f"{system}: object selected and moved by dragging", ed.sel_index == i and (o["x"], o["y"]) == (x0 + 6, y0 + 4),
          (ed.sel_index, i, o["x"], o["y"], x0, y0))
    ed.set_property(o, "name", "Renamed")
    check(f"{system}: Properties grid rename", ed.doc.objects[i]["name"] == "Renamed" and
          "Renamed" in ed.obj_list.item(i).text())
    if system != "a2600":
        n0 = len(ed.doc.objects)
        ed.add_object()
        check(f"{system}: Add object", len(ed.doc.objects) == n0 + 1 and ed.sel_index == n0)
        ed.delete_object()
        check(f"{system}: Delete object", len(ed.doc.objects) == n0)
    png = ed.export_png(WORK / f"{system}.png")
    check(f"{system}: Export PNG", png is not None and png.stat().st_size > 200)
    ed.set_zoom(4)
    check(f"{system}: zoom changes the canvas size", ed.canvas.zoom == 4 and ed.canvas.width() >= ed.canvas.image.width() * 4)
    shot(ed, f"gamedesign_{system}")
    w.save_current()
    check(f"{system}: File > Save writes the design", not ed.is_modified() and load(ed.path).objects[i]["name"] == "Renamed")

# settings that change the document shape
e26 = eds["a2600"]
e26.set_property(None, "tv", "PAL")
check("2600: TV = PAL resizes the scan-line layers", e26.doc.layer("Playfield").h == 228 and e26.canvas.image.height() == 228)
e26.a_undo.trigger()
check("2600: undo TV change", e26.doc.layer("Playfield").h == 192)
enes = eds["nes"]
enes.set_property(None, "screens", 4)
check("NES: 4 screens widen the level", enes.doc.layer("Nametable").w == 128 and enes.canvas.image.width() == 1024)
# mirrored playfield painting: a click on the right half edits the mirrored bit
e26._select_layer_name("Playfield")
e26.set_tool("pencil")
pf = e26.doc.layer("Playfield")
pf.set(2, 100, 0)
e26.press(QPoint((39 - 2) * 4 + 1, 100), LEFT)
e26.release(None, QPoint(0, 0), LEFT)
check("2600: painting the right half sets the mirrored bit", e26.doc.layer("Playfield").get(2, 100) == 1)
# import tiles made elsewhere (CHR written by the NES generator of another design)
from radide.retro.design.game import nes as N  # noqa: E402
other = N.new_design("Other", 1)
other.tiles[300] = bytearray([3] * 64)
chr_file = WORK / "other.chr"
chr_file.write_bytes(N.chr_bytes(other))
n_imp = enes.import_tiles(chr_file)
check("NES: Import Tiles reads a .chr (512 tiles)", n_imp == 512 and enes.doc.tiles[300] == bytearray([3] * 64))
w.save_all()
check("Save All saves the designers", not any(e.is_modified() for e in eds.values()))

# reopen through File > Open
p = eds["gb"].path
idx = w.tabs.indexOf(eds["gb"])
w.tabs.removeTab(idx)
ed2 = w.open_any_file(p)
pump(0.2)
check("File > Open opens a .gbmap in the designer", isinstance(ed2, GameDesigner) and ed2.doc.system == "gb")

# build (toolchain installed?) - runs in a thread; wait=True for the test
for system, exe in (("a2600", "dasm"), ("nes", "ca65"), ("gb", "rgbasm"), ("dos13h", "nasm")):
    ed = eds[system] if system != "gb" else ed2
    if not find_tool(exe):
        print(f"SKIP {system} build ({exe} not installed)")
        continue
    res = ed.build_and_run(run=False, wait=True, download=False)
    wait(lambda: not ed._busy, 60)
    check(f"{system}: Build && Run builds", res.get("ok"), res.get("log", "")[-800:])
    check(f"{system}: build checks pass", res.get("checks") and all(ok for ok, _m in res["checks"]), res.get("checks"))

# Arabic UI
from radide import i18n  # noqa: E402
i18n.load("ar")
check("Arabic strings for the designers", all(i18n.tr(s) != s for s in (
    "New Atari 2600 Screen...", "New NES Screen / Level...", "New Game Boy Map...", "New DOS Mode 13h Screen...",
    "Build && Run", "Export PNG...", "Layers", "Properties", "Generate Code")))
i18n.load("en")
finish(w)
