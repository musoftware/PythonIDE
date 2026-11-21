"""IDE test (qh harness, QSettings org RADIDE-TEST, screenshots with widget.grab only): calibration maps in the
real window.

    python samples/Tests/Firmware/Maps/qa_maps_ide.py          (screenshots: %TEMP%/radide-qa/shots/maps_*.png)

* Tools > Firmware & ECU > Calibration Maps menu, the hex editor's "Open in Map Editor"
* a synthetic firmware opens in the map editor: the safety notice banner, Find Maps ranks the 7 embedded maps
  first, Add to Map Pack, the map table (heat map), 3D surface and 2D chart, the whole-file 2D view
* editing: +10 % on a selection, set value, interpolate, smooth, paste from Excel text, cell edit; undo / redo
  through Edit > Undo; differences (ori vs mod) list + colouring; hex edits show in the map; Save writes the
  binary, the map pack and keeps the original
* A2L import (sample_ecu.a2l) with the right maps, export A2L, CSV
* rusEFI-style tune (ini + msq) opened as a calibration image
* compare two binaries: differing maps, Copy Map from B to A
* Arabic UI strings
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
sys.path.insert(0, str(HERE))
os.environ.setdefault("QA_NAME", "fwmaps")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
import qh  # noqa: E402
from qh import check, pump, shot  # noqa: E402

import numpy as np  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from radide.firmware.maps import ops  # noqa: E402
from radide.firmware.maps.synth import build_image  # noqa: E402
from sample_ecu import build_sample_bin  # noqa: E402

WORK = Path(qh.WORK) / "fwmaps"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)

img, MAPS = build_image(11)
BIN = WORK / "demo_ecu.bin"
BIN.write_bytes(img)


def menu_actions(menu, prefix=""):
    out = []
    for a in menu.actions():
        t = prefix + a.text().replace("&", "")
        out.append(t)
        if a.menu() is not None:
            out += menu_actions(a.menu(), t + " > ")
    return out


def phase_menus(w):
    from radide.features.firmware_maps import firmware_menu
    check("win.firmware_maps installed", getattr(w, "firmware_maps", None) is not None)
    acts = menu_actions(firmware_menu(w))
    for want in ("Calibration Maps > Open Binary in Map Editor...", "Calibration Maps > Find Maps in a Binary...",
                 "Calibration Maps > Compare Two Binaries (Maps)...",
                 "Calibration Maps > Open rusEFI / Speeduino Tune (msq + ini)..."):
        check(f"menu: Tools > Firmware & ECU > {want}", want in acts, acts)
    hexdoc = w.open_hex(BIN) if hasattr(w, "open_hex") else None
    if hexdoc is not None:
        m = hexdoc.build_context_menu()
        check("hex editor context menu: Open in Map Editor", "Open in Map Editor" in [a.text() for a in m.actions()])


def phase_editor(w):
    fm = w.firmware_maps
    d = fm.open_maps(BIN)
    pump(0.5)
    st = {"doc": d}
    check("map editor tab opened", d is not None and w.tabs.currentWidget() is d and
          "[Maps]" in w.tabs.tabText(w.tabs.indexOf(d)))
    check("safety notice banner shown (not accepted yet)", d.banner is not None and d.banner.isVisible())
    shot(d, "maps_01_opened")
    cands = d.find_maps()
    top = cands[:len(MAPS)]
    hits = [m.name for m in MAPS if any(c.mapdef.address == m.address and (c.mapdef.cols, c.mapdef.rows) ==
                                        (m.cols, m.rows) for c in top)]
    check(f"Find Maps: the {len(MAPS)} embedded maps are the top {len(MAPS)}", len(hits) == len(MAPS),
          (hits, [c.label() for c in top]))
    check("Potential Maps list filled", d.pot.topLevelItemCount() == len(cands))
    d.left.setCurrentIndex(1)
    shot(d, "maps_02_potential")
    # async search finishes too
    d.find_maps_async()
    ok = qh.wait(lambda: d._find_thread is not None and not d._find_thread.is_alive() and d.b_find.isEnabled(), 60)
    check("Find Maps in the background finishes", ok and len(d.candidates) == len(cands))
    d.pot.clearSelection()
    for i in range(len(MAPS)):
        d.pot.topLevelItem(i).setSelected(True)
    n = d.add_selected_candidates()
    check("Add to Map Pack: 7 maps", n == len(MAPS) and len(d.pack) == len(MAPS))
    # name the maps like the synthetic definitions
    for m in MAPS:
        pm = next(x for x in d.pack.maps if x.address == m.address)
        new = pm.copy()
        new.name, new.factor, new.unit, new.folder = m.name, m.factor, m.unit, "Demo"
        new.x_axis, new.y_axis = m.copy().x_axis, m.copy().y_axis
        d.replace_map(pm, new)
    check("map pack tree shows the folder and 7 maps", len([it for it in d.tree_items() if it.data(0, qh_role())
                                                           and it.data(0, qh_role())[0] == "map"]) == len(MAPS))
    m = d.open_map("KF_BOSCH8")
    ed = d.editor
    check("KF_BOSCH8 opened as a 12 x 10 table", m is not None and ed.model.rowCount() == 10 and
          ed.model.columnCount() == 12)
    check("axis headers are physical (rpm x 40)", ed.model.headerData(0, qh_h()) == str(int(MAPS[0].x_axis.phys(img)[0])))
    ed.views.setCurrentIndex(0)
    ed.surface.set_view(-50, 35)
    d.resize(1300, 860)
    pump(0.3)
    shot(w, "maps_03_window_map_3d")
    shot(ed.surface, "maps_04_surface3d")
    ed.views.setCurrentIndex(1)
    pump(0.2)
    shot(ed.chart, "maps_05_chart2d")
    ed.views.setCurrentIndex(0)
    st["m"] = m
    return st


def qh_role():
    from PyQt6.QtCore import Qt
    return Qt.ItemDataRole.UserRole


def qh_h():
    from PyQt6.QtCore import Qt
    return Qt.Orientation.Horizontal


def phase_edit(w, st):
    d, m = st["doc"], st["m"]
    ed = d.editor
    before = m.phys(d.buf.data).copy()
    ed.select_cells(2, 3, 4, 6)
    ok = ed.op_percent(10)
    d.flush()
    after = m.phys(d.buf.data)
    expect = before.copy()
    expect[2:5, 3:7] = np.clip(np.rint(before[2:5, 3:7] * 1.1 / m.factor), 0, 255) * m.factor
    check("+10% on a 3x4 selection (rounded to the factor)", ok and np.allclose(after, expect) and
          np.allclose(after[0], before[0]))
    check("document modified: tab title has *", d.is_modified() and w.tabs.tabText(w.tabs.indexOf(d)).endswith("*"))
    check("Differences: KF_BOSCH8 listed with 12 cells", d.diff.topLevelItemCount() >= 1 and
          d.diff.topLevelItem(0).text(0) == "KF_BOSCH8" and d.diff.topLevelItem(0).text(1).startswith("12 /"),
          [d.diff.topLevelItem(i).text(1) for i in range(d.diff.topLevelItemCount())])
    check("changed cells are marked in the model", int(ed.model.changed().sum()) == 12)
    ed.colour.setCurrentIndex(1)
    pump(0.2)
    d.left.setCurrentIndex(2)
    shot(w, "maps_06_differences")
    ed.colour.setCurrentIndex(0)
    # undo / redo through the IDE's Edit menu
    w.tabs.setCurrentWidget(d)
    d.editor.table.setFocus()
    pump(0.2)
    check("Edit > Undo is enabled on the map tab", w.a_undo.isEnabled())
    w.a_undo.trigger()
    d.flush()
    check("Edit > Undo restores the map", np.allclose(m.phys(d.buf.data), before))
    pump(0.2)
    check("Edit > Redo is enabled after the undo", w.a_redo.isEnabled())
    w.a_redo.trigger()
    d.flush()
    check("Edit > Redo applies it again", np.allclose(m.phys(d.buf.data), expect))
    # set value / interpolate / smooth / cell edit
    ed.select_cells(0, 0, 0, 0)
    ed.op_set(150)
    check("Set Value 150 on one cell", m.phys(d.buf.data)[0, 0] == 150)
    ed.select_cells(5, 0, 5, 11)
    ed.op_interpolate("h")
    row = m.phys(d.buf.data)[5]
    lin = np.linspace(row[0], row[-1], 12)
    check("interpolate a row (within one raw step)", np.all(np.abs(row - lin) <= m.factor / 2 + 1e-9), (row, lin))
    ed.select_cells(6, 1, 8, 4)
    zb = m.phys(d.buf.data)
    ed.op_smooth()
    check("smooth changes only the selection", np.allclose(m.phys(d.buf.data)[0:6], zb[0:6]))
    idx = ed.model.index(9, 11)
    ed.model.setData(idx, "99")
    check("type a value into a cell", np.isclose(m.phys(d.buf.data)[9, 11], 99, atol=m.factor / 2))
    QApplication.clipboard().setText("30\t31,5\n32\t33\n")
    ed.select_cells(1, 1, 1, 1)
    ed.paste()
    z = m.phys(d.buf.data)
    check("paste from Excel (decimal comma)", np.allclose(z[1:3, 1:3], [[30, 31.5], [32, 33]], atol=m.factor / 2),
          z[1:3, 1:3])
    txt = ed.copy(with_axes=True)
    check("copy with axes: header row of rpm values", txt.split("\n")[0].split("\t")[1] ==
          str(int(MAPS[0].x_axis.phys(img)[0])))
    # hex edit inside the map shows in the table
    d.buf.replace(m.address + 10 * 0 + 11, bytes([200]))
    d.flush()
    check("hex edit inside the map shows in the map table", np.isclose(ed.model.z[0, 11], 200 * m.factor))
    d.center.setCurrentIndex(1)
    d.graph_zoom.setCurrentIndex(3)
    d.goto_graph(m.address)
    pump(0.2)
    shot(w, "maps_07_2dview")
    d.graph.offsetClicked.emit(MAPS[1].address + 4)
    check("2D view click opens the map under the cursor", d.editor.m is not None and d.editor.m.name == "KF_BOSCH16")
    d.center.setCurrentIndex(0)
    # save: binary + map pack + original kept
    ok = d.save()
    bak = BIN.with_name("demo_ecu.original.bin")
    check("Save writes the binary", ok and BIN.read_bytes() == bytes(d.buf.data) and not d.is_modified())
    check("Save keeps the original as demo_ecu.original.bin", bak.is_file() and bak.read_bytes() == img)
    check("Save writes the map pack demo_ecu.bin.maps.json", BIN.with_name("demo_ecu.bin.maps.json").is_file())
    # reopen: pack is loaded again
    w.tabs.removeTab(w.tabs.indexOf(d))
    d2 = w.firmware_maps.open_maps(BIN, original=bak)
    check("reopen: the map pack loads with the binary", len(d2.pack) == len(MAPS))
    check("reopen with the original: KF_BOSCH8 listed as changed", any(d2.diff.topLevelItem(i).text(0) == "KF_BOSCH8"
                                                                     for i in range(d2.diff.topLevelItemCount())))
    st["doc"] = d2


def phase_a2l(w, st):
    data, exp = build_sample_bin()
    p = WORK / "sample_ecu.bin"
    p.write_bytes(data)
    d = w.firmware_maps.open_maps(p)
    res = d.import_a2l(HERE / "sample_ecu.a2l")
    check("A2L import: 8 maps, base 0x80000000", len(d.pack) == 8 and d.pack.base_address == 0x80000000,
          (len(d.pack), res.warnings))
    m = d.open_map("KFLAMBDA")
    check("KFLAMBDA (big endian, column order) shown with the right values",
          np.allclose(d.editor.model.z, np.array(exp["KFLAMBDA"]["z"]), atol=1e-6))
    d.editor.views.setCurrentIndex(0)
    d.editor.surface.set_view(-120, 28)
    pump(0.2)
    shot(w, "maps_08_a2l_kflambda")
    shot(d.editor.surface, "maps_09_kflambda_3d")
    out = WORK / "export.a2l"
    d.export_a2l(out)
    from radide.firmware.maps.a2l import load_a2l
    back = load_a2l(out, data)
    check("export A2L reads back with the same maps", [x.name for x in back.pack.maps] == [x.name for x in d.pack.maps])
    csvp = d.export_csv(WORK / "maps.csv")
    check("export CSV", csvp.is_file() and "KFZW" in csvp.read_text(encoding="utf-8"))
    check("folders from the A2L in the tree", any(it.text(0) == "Ignition" for it in d.tree_items()))
    _ = m


def phase_tune(w, st):
    from test_maps_core import INI, MSQ
    ini = WORK / "synthetic.ini"
    msq = WORK / "tune.msq"
    ini.write_text(INI, encoding="utf-8")
    msq.write_text(MSQ, encoding="utf-8")
    d = w.firmware_maps.open_tune(ini, msq)
    check("tune (ini + msq) opened as a calibration image", d is not None and (WORK / "tune.bin").is_file() and
          d.pack.get("veTable") is not None)
    m = d.open_map("veTable")
    check("VE table values from the tune", np.allclose(d.editor.model.z[3], [70, 75, 80, 85, 90, 92]))
    shot(d, "maps_10_tune")
    _ = m


def phase_compare(w, st):
    a = WORK / "cmp_a.bin"
    b = WORK / "cmp_b.bin"
    a.write_bytes(img)
    from radide.firmware.maps.model import MapPack
    bb = bytearray(img)
    m3 = MAPS[2]
    z = m3.phys(bb)
    z[1:3, 2:5] *= 1.2
    ops.apply(bb, m3, z)
    b.write_bytes(bytes(bb))
    MapPack("demo", [m.copy() for m in MAPS]).save(a.with_name(a.name + ".maps.json"))
    d = w.firmware_maps.compare_maps(a, b)
    pump(0.3)
    names = [d.list.topLevelItem(i).text(0) for i in range(d.list.topLevelItemCount())]
    check("compare: only the changed map differs", names == [m3.name], names)
    d.list.setCurrentItem(d.list.topLevelItem(0))
    pump(0.2)
    shot(w, "maps_11_compare")
    ok = d.copy_current()
    pump(0.3)
    check("Copy Map from B to A", ok and bytes(d.buf.data[m3.address:m3.end]) == bytes(bb[m3.address:m3.end]))
    d.only_diff.setChecked(False)
    pump(0.2)
    check("after the copy no map differs", "0 of 7" in d.summary.text(), d.summary.text())
    d.save()
    check("compare: Save writes file A", a.read_bytes() == bytes(bb))


def phase_arabic(w, st):
    from radide import i18n
    i18n.set_language(qh.app, "ar")
    try:
        for s in ("Calibration &Maps", "Find Maps", "Potential Maps", "Differences", "Map Pack", "Interpolate",
                  "Copy Map from B to A", "Edits to vehicle software can affect safety, warranty and emissions "
                  "legality. Keep the original file and follow your local laws."):
            check(f"Arabic: {s[:40]}", i18n.tr(s) != s, i18n.tr(s))
        d = w.firmware_maps.open_maps(BIN)
        i18n.translate_widget(d)
        pump(0.3)
        d.open_map("KF_BOSCH8")
        pump(0.3)
        shot(w, "maps_12_arabic")
    finally:
        i18n.set_language(qh.app, "en")


def main():
    w = qh.window()
    st = {}
    for ph in ("menus", "editor", "edit", "a2l", "tune", "compare", "arabic"):
        try:
            fn = globals()["phase_" + ph]
            r = fn(w) if ph in ("menus", "editor") else fn(w, st)
            if isinstance(r, dict):
                st.update(r)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"phase {ph} raised", False, e)
    qh.finish(w)


main()
