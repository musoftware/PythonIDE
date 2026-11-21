"""Firmware & ECU workbench - full IDE test (MainWindow, QSettings org RADIDE-TEST, widget.grab screenshots).

Run:  python samples\\Tests\\Firmware\\Workbench\\test_workbench_ide.py
      set QA_LANG=ar & set QA_THEME=dark & python samples\\Tests\\Firmware\\Workbench\\test_workbench_ide.py

Flow on synthetic firmware only (radide/firmware/ui/demo.py - written by RAD IDE, no vehicle data):
menus -> one-time safety notice -> .ori opens in the workbench, ordinary .bin does not -> Intel HEX -> EEPROM dump
(read-only, chip sizes, word-swap view) -> Tools > Firmware & ECU > New ECU Project -> load checksum profile ->
Find Maps -> add a map -> edit with the WinOLS-like keys (+, PgUp, undo) -> Verify (wrong) -> Correct -> Compare
-> Build (F7) -> versions -> Analyze -> Disassembly -> A2L import -> Save All -> Open With in Solution Explorer.
Screenshots go to %TEMP%\\radide-qa\\shots\\fw_<lang>[_dark]_*.png.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
LANG = os.environ.get("QA_LANG", "")
THEME = os.environ.get("QA_THEME", "")
TAG = (LANG or "en") + ("_" + THEME if THEME else "")
os.environ.setdefault("QA_NAME", "fwwb_" + TAG)
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
import qh  # noqa: E402

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QMenu  # noqa: E402

WORK = Path(qh.WORK) / ("fwwb_" + TAG)
def _writable(func, path, _exc):          # originals of ECU projects are read-only
    os.chmod(path, 0o666)
    func(path)


if WORK.exists():
    shutil.rmtree(WORK, onerror=_writable)
WORK.mkdir(parents=True)

if LANG:
    from radide import i18n
    i18n.set_language(qh.app, LANG)
w = qh.window()
if THEME:
    from radide.features.workbench import set_theme
    set_theme(w, THEME.capitalize())
    qh.pump(0.5)

from radide.firmware.ui import adapters as A  # noqa: E402
from radide.firmware.ui import demo  # noqa: E402
from radide.firmware.ui.workbench import FirmwareWorkbench, notice_accepted  # noqa: E402
from radide.retro.rom.hexdoc import HexDocument  # noqa: E402

check = qh.check
fe = getattr(w, "firmware_ide", None)
check("feature installed", fe is not None)


def shot(widget, name):
    return qh.shot(widget, f"fw_{TAG}_{name}")


def plain(text):
    return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")


def menu_texts(menu):
    return [plain(a.text()) for a in menu.actions()]


def find_menu(title, parent=None):
    acts = parent.actions() if parent is not None else w.menuBar().actions()
    return next((a.menu() for a in acts if a.menu() is not None and plain(a.text()) == title), None)


# ------------------------------------------------------------------ menus
tools = find_menu("Tools")
fwm = find_menu("Firmware & ECU", tools) if tools else None
check("Tools > Firmware & ECU menu", fwm is not None and "Open Firmware in Workbench..." in menu_texts(fwm),
      menu_texts(fwm) if fwm else None)
pm = find_menu("Project")
ecu = find_menu("ECU Project", pm) if pm else None
check("Project > ECU Project has the workbench entries", ecu is not None and "Open Workbench" in menu_texts(ecu),
      menu_texts(ecu) if ecu else None)
ecu_menus = [a for a in pm.actions() if a.menu() is not None and a.text().replace("&", "") == "ECU Project"]
check("only one ECU Project submenu", len(ecu_menus) == 1, len(ecu_menus))

# ------------------------------------------------------------------ demo files
data, maps, profiles = demo.build_image()
data2, _m2, _p2 = demo.build_image(1)
ori = WORK / "demo_ecu.ori"
ori.write_bytes(data)
prof_file = WORK / "demo_checksums.json"
prof_file.write_text(json.dumps({"checksums": profiles}, indent=1))

# ------------------------------------------------------------------ notice + .ori opens in the workbench
check("notice not yet accepted (fresh test settings)", not notice_accepted())
wb1 = w.open_any_file(str(ori))
qh.pump(0.5)
check(".ori opens in the workbench", isinstance(wb1, FirmwareWorkbench) and w.tabs.currentWidget() is wb1,
      (type(wb1), qh.MSGS[-3:], w.output.toPlainText()[-600:]))
check(".ori opens read-only", wb1 is not None and wb1.read_only)
check("safety notice shown once", wb1 is not None and wb1.notice.isVisible())
shot(w, "01_notice_start")
wb1.accept_notice()
qh.pump(0.2)
check("notice accepted and hidden", notice_accepted() and not wb1.notice.isVisible())
check("Getting Started page has the workflow", "Find maps" in wb1.start.text.toPlainText() or
      "ابحث عن الخرائط" in wb1.start.text.toPlainText(), wb1.start.text.toPlainText()[:200])
wb1.start.show_language(True)
check("Getting Started in Arabic", "الخرائط" in wb1.start.text.toPlainText())
shot(wb1, "02_getting_started_ar")
wb1.start.show_language(False)
check("Getting Started in English", "Getting started" in wb1.start.text.toPlainText() or
      "getting started" in wb1.start.text.toPlainText())

# ------------------------------------------------------------------ ordinary .bin is not hijacked
plain_bin = WORK / "plain_data.bin"
plain_bin.write_bytes(bytes(range(256)) * 3 + b"\x00\x01")
check("ordinary .bin: workbench not wanted", not fe.wants(plain_bin))
d_plain = w.open_any_file(str(plain_bin))
qh.pump(0.3)
check("ordinary .bin opens in the ROM hex editor", isinstance(w.tabs.currentWidget(), HexDocument),
      type(w.tabs.currentWidget()).__name__)

# ------------------------------------------------------------------ Intel HEX
hexf = WORK / "small_fw.hex"
recs = [":020000040800F2"]
for i in range(0, 64, 16):
    chunk = bytes((i + k) & 0xFF for k in range(16))
    rec = bytes([16, 0, i, 0]) + chunk
    recs.append(":" + (rec + bytes([(-sum(rec)) & 0xFF])).hex().upper())
recs.append(":00000001FF")
hexf.write_text("\n".join(recs) + "\n")
check("Intel HEX: workbench wanted (no project open)", fe.wants(hexf))
wbh = w.open_any_file(str(hexf))
qh.pump(0.3)
check("Intel HEX opens at 0x08000000, read-only", isinstance(wbh, FirmwareWorkbench) and wbh.img.base == 0x08000000
      and wbh.read_only and len(wbh.data()) == 64, (getattr(wbh, "img", None) and hex(wbh.img.base)))

# ------------------------------------------------------------------ EEPROM dump
eep = WORK / "board_24c16.eep"
eep_bytes = bytes((i * 7) & 0xFF for i in range(2048))
eep.write_bytes(eep_bytes)
wbe = w.open_any_file(str(eep))
qh.pump(0.3)
check("EEPROM dump opens read-only", isinstance(wbe, FirmwareWorkbench) and wbe.is_eeprom and wbe.read_only)
check("EEPROM chips listed (24C16 / 93C86 / 95160)", wbe is not None and wbe.ee is not None and
      {"24C16 (I2C)", "93C86 (Microwire)", "95160 (SPI)"} <= set(wbe.ee.chips), wbe.ee.chips if wbe else None)
if wbe is not None:
    wbe.tabs.setCurrentIndex(wbe.tabs.count() - 1)
    wbe.ee_mode.setCurrentIndex(wbe.ee_mode.findData("swap16"))
    qh.pump(0.2)
    check("EEPROM 16-bit swap view", wbe.eeprom_view_bytes()[:4] == bytes([eep_bytes[1], eep_bytes[0], eep_bytes[3],
                                                                           eep_bytes[2]]))
    check("EEPROM: map edits refused (read-only)", wbe.mapedit.read_only)
    shot(wbe, "03_eeprom_swap16")

# ------------------------------------------------------------------ new ECU project
proj_dir = WORK / "EcuDemo"
wb = fe.new_project_dialog(source=str(ori), folder=proj_dir, name="EcuDemo")
qh.pump(1.0)
check("ECU project created and opened", w.project is not None and w.project.language == "firmware-ecu" and
      A.is_ecu_project(proj_dir), getattr(w.project, "language", None))
check("project workbench open", isinstance(wb, FirmwareWorkbench) and wb.proj is not None)
wbs = [x for x in fe.docs.values() if fe._alive(x) and x.proj is not None]
check("one workbench for the project (auto-open did not duplicate)", len(wbs) == 1, len(wbs))
check("original is read-only on disk", wb.proj.original_path.is_file() and
      not os.access(wb.proj.original_path, os.W_OK))
check("working copy = original", wb.data() == data)
tree_texts = []


def walk(it):
    tree_texts.append(it.text(0))
    for i in range(it.childCount()):
        walk(it.child(i))


for i in range(wb.tree.topLevelItemCount()):
    walk(wb.tree.topLevelItem(i))
check("project tree: original / working copy / versions / maps / checksums",
      all(any(t.startswith(p) for t in tree_texts) for p in ("Original:", "Working copy:", "Versions", "Maps",
                                                            "Checksum profiles")), tree_texts)

# ------------------------------------------------------------------ checksum profile
n = wb.load_profile(prof_file)
check("checksum profile loaded (2 blocks)", n == 2 and len(wb.profiles) == 2)
rep = wb.verify_checksums(True)
check("checksums verify OK on the original", len(rep) == 2 and all(r["ok"] for r in rep), rep)
check("profile stored in ecu.json", len(A.EcuProject.load(proj_dir).checksums) == 2)

# ------------------------------------------------------------------ find maps
cnt = wb.find_maps()
addrs = [m.address for m in wb.potential]
check("Find Maps finds the demo tables", cnt >= 3 and maps[0]["address"] in addrs and maps[2]["address"] in addrs,
      [hex(a) for a in addrs[:10]])
row = addrs.index(maps[0]["address"])
wb.pot.clearSelection()
wb.pot.setCurrentCell(row, 0)          # (selectRow is a no-op in right-to-left offscreen runs)
check("add potential map to the project", wb.add_selected_potential() == 1 and len(wb.maps) == 1)
m0 = wb.maps[0]
check("map pack saved", any(x.address == m0.address for x in A.EcuProject.load(proj_dir).map_defs()))
shot(w, "04_potential_maps")

# ------------------------------------------------------------------ edit the map with the keys
wb.open_map(m0)
qh.pump(0.3)
t = wb.mapedit.table
check("map editor shows 16x16", t.rowCount() == 16 and t.columnCount() == 16, (t.rowCount(), t.columnCount()))
w.activateWindow()
t.setFocus()
t.setCurrentCell(3, 4)
qh.pump(0.2)
before = A.read_map(wb.data(), m0)[2][3][4]
QTest.keyClick(t, Qt.Key.Key_Plus)
qh.pump(0.3)
after_plus = A.read_map(wb.data(), m0)[2][3][4]
check("+ raises the cell by one step", after_plus == before + 1, (before, after_plus))
QTest.keyClick(t, Qt.Key.Key_PageUp)
qh.pump(0.3)
after_pg = A.read_map(wb.data(), m0)[2][3][4]
check("Page Up raises by ten steps", after_pg == before + 11, (before, after_pg))
check("workbench modified, tab marked", wb.is_modified() and w.tabs.tabText(w.tabs.indexOf(wb)).endswith("*"),
      w.tabs.tabText(w.tabs.indexOf(wb)))
QTest.keyClick(t, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
qh.pump(0.4)
check("Ctrl+Z undoes the last map edit", A.read_map(wb.data(), m0)[2][3][4] == before + 1,
      A.read_map(wb.data(), m0)[2][3][4])
QTest.keyClick(t, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
qh.pump(0.4)
check("Ctrl+Y redoes it", A.read_map(wb.data(), m0)[2][3][4] == before + 11)
t.clearSelection()
t.setCurrentCell(5, 5)
t.item(5, 5).setSelected(True)
t.item(5, 6).setSelected(True)
check("percent change on 2 cells", wb.mapedit.percent(10) == 2)
it = t.item(3, 4)
check("changed cell marked (bold, original in tooltip)", it.font().bold() and str(before) in it.toolTip(),
      it.toolTip())
shot(w, "05_map_text")
QTest.keyClick(t, Qt.Key.Key_2)
qh.pump(0.2)
check("2 switches to the 2D view", wb.mapedit.stack.currentIndex() == 1)
shot(wb.mapedit, "06_map_2d")
QTest.keyClick(wb.mapedit.stack.currentWidget(), Qt.Key.Key_3)
wb.mapedit.set_view(2)
qh.pump(0.2)
shot(wb.mapedit, "07_map_3d")
wb.mapedit.set_view(0)

# ------------------------------------------------------------------ checksums / compare / build
rep = wb.verify_checksums(True)
check("Verify: edits broke the checksums", rep and not all(r["ok"] for r in rep), rep)
rep = wb.correct_checksums()
check("Correct Checksums fixes them in the working copy", rep and all(r["ok"] for r in rep), rep)
nd = wb.compare()
diff_maps = {wb.difftree.topLevelItem(i).text(4) for i in range(wb.difftree.topLevelItemCount())}
check("Compare lists the changed map and the checksum bytes", nd >= 3 and m0.name in diff_maps, (nd, diff_maps))
shot(w, "08_differences")
wb.mapedit.table.setFocus()
qh.pump(0.1)
QTest.keyClick(wb.mapedit.table, Qt.Key.Key_F7)
qh.pump(1.0)
out = A.EcuProject.load(proj_dir).output_path
built = getattr(wb, "built", None)
check("F7 builds the project", built is not None and Path(built).is_file(), built)
if built is not None and Path(built).is_file():
    bdata = Path(built).read_bytes()
    check("build output has valid checksums", all(r["ok"] for r in A.verify(bdata, profiles)))
    check("build output = working copy", bdata == wb.data())
check("original never written", A.EcuProject.load(proj_dir).original_bytes() == data)
check("working copy saved by Build", not wb.is_modified() and
      A.EcuProject.load(proj_dir).working_path.read_bytes() == wb.data())
shot(w, "09_checksum_report")

vp = wb.save_version("stage 1", "ignition +10 at one cell")
check("Save Version", vp is not None and vp.is_file() and len(wb.proj.versions) == 1)
vitem = None
for i in range(wb.tree.topLevelItemCount()):
    stack = [wb.tree.topLevelItem(i)]
    while stack:
        x = stack.pop()
        if (x.data(0, Qt.ItemDataRole.UserRole) or (None,))[0] == "version":
            vitem = x
        stack.extend(x.child(k) for k in range(x.childCount()))
check("version in the project tree", vitem is not None)
if vitem is not None:
    wb._on_tree_item(vitem)
    check("double-click version: compare shows no differences", len(wb.diffs) == 0, wb.diffs[:3])
wb.compare(str(WORK / "v2.bin") if (WORK / "v2.bin").write_bytes(data2) else None)
check("compare with another software version", len(wb.diffs) > 5, len(wb.diffs))

# ------------------------------------------------------------------ analysis / disassembly / 2D
res = wb.analyze()
check("Analyze: PowerPC", "PowerPC" in str(res["facts"].get("CPU (guess)")), res["facts"])
check("Analyze: identification strings listed", wb.strings.topLevelItemCount() > 0)
shot(w, "10_analysis")
nlines = wb.disassemble(0x200)
check("Disassembly at 0x200 (PowerPC)", nlines > 10 and "stwu" in wb.dis_text.toPlainText())
shot(w, "11_disassembly")
for name in ("maps", "analysis"):            # the other firmware features' full views
    if name in wb.integrations:
        n_tabs = w.tabs.count()
        r = wb.integrate(name)
        qh.pump(0.8)
        check(f"More > full {name} view opens in a tab", r is not None or w.tabs.count() > n_tabs,
              (r, w.tabs.count(), n_tabs))
        w._show_tab(wb, "")
    else:
        print(f"SKIP {name} integration (feature not installed)")
wb.tabs.setCurrentIndex(3)
wb.goto(maps[0]["block"])
wb.tabs.setCurrentIndex(3)
qh.pump(0.3)
shot(w, "12_2d_view")

# ------------------------------------------------------------------ A2L import
try:
    from radide.firmware.maps.a2l import export_a2l
    from radide.firmware.maps.model import MapPack
    pack = MapPack("demo", [A.MapDef.from_any(x).to_slice_map() for x in maps[1:4]])
    a2l = WORK / "demo.a2l"
    a2l.write_text(export_a2l(pack))
    before_maps = len(wb.maps)
    w.open_any_file(str(a2l))
    qh.pump(0.3)
    check("A2L opened while a workbench is active imports its maps", len(wb.maps) == before_maps + 3,
          [x.name for x in wb.maps])
except ImportError as e:
    check("maps slice for A2L", False, e)

# ------------------------------------------------------------------ Save All / properties / Open With
wb.open_map(wb.maps[-1])
wb.mapedit.table.setCurrentCell(0, 0)
wb.mapedit.step(1)
check("modified before Save All", wb.is_modified())
w.save_all()
qh.pump(0.5)
check("Save All writes the working copy", not wb.is_modified() and
      A.EcuProject.load(proj_dir).working_path.read_bytes() == wb.data())
props = {wb.props.topLevelItem(i).text(0): wb.props.topLevelItem(i) for i in range(wb.props.topLevelItemCount())}
check("Properties show the map", "Factor" in props and "Address" in props, list(props))
if "Factor" in props:
    props["Factor"].setText(1, "0.5")
    qh.pump(0.2)
    check("editing Factor in Properties updates the map", abs(wb.mapedit.m.factor - 0.5) < 1e-9)

from radide.features.solution_ui import apply_menu_hooks  # noqa: E402
target = None
stack = [w.solution.topLevelItem(i) for i in range(w.solution.topLevelItemCount())]
while stack:
    x = stack.pop()
    dd = x.data(0, Qt.ItemDataRole.UserRole)
    if dd and str(dd[0]) in ("ecuproj_work", "module") and str(dd[1]).lower().endswith(".bin"):
        target = x
    stack.extend(x.child(k) for k in range(x.childCount()))
check("Solution Explorer has a .bin node of the project", target is not None)
if target is not None:
    mm = QMenu(w)
    apply_menu_hooks(w, target, mm)
    ow = next((a.menu() for a in mm.actions() if a.menu() is not None and a.text().replace("&", "") == "Open With"),
              None)
    check("Open With > Firmware & ECU Workbench", ow is not None and any("Workbench" in a.text().replace("&", "")
                                                                        for a in ow.actions()))
check(".bin inside the ECU project opens in the workbench", fe.wants(wb.proj.working_path))
shot(w, "13_ide_full")

# ------------------------------------------------------------------ Arabic UI strings
if LANG == "ar":
    from radide import i18n
    shown = i18n.shown(wb.a_find)
    check("Arabic: toolbar translated", shown != "Find Maps" and any("؀" <= c <= "ۿ" for c in shown), shown)
    check("Arabic: dock titles translated", any("؀" <= c <= "ۿ" for c in i18n.shown(wb.d_pot, "windowTitle")),
          i18n.shown(wb.d_pot, "windowTitle"))
    # English texts of the workbench's own widgets that the catalog does not translate (map / file names and
    # numbers are the user's content and stay as they are)
    from PyQt6.QtWidgets import QAbstractButton, QDockWidget, QLabel
    seen = set()
    for wbx in [x for x in fe.docs.values() if fe._alive(x)]:
        for wd in wbx.findChildren(QLabel) + wbx.findChildren(QAbstractButton):
            if wbx.doc.isAncestorOf(wd) or wd in (wbx.mapedit.title, wbx.start.b_en, wbx.start.b_ar):
                continue            # the ROM hex editor's own status bar; the map name; language buttons
            seen.add(i18n.english(wd, i18n.shown(wd)))
            seen.add(wd.toolTip())
        for wd in wbx.findChildren(QDockWidget):
            seen.add(wd.windowTitle())
        for i in range(wbx.tabs.count()):
            seen.add(wbx.tabs.tabText(i))
        for a in wbx.toolbar.actions() + wbx.more_menu.actions():
            seen.add(a.text())
            seen.add(a.toolTip())
    miss = sorted(s for s in i18n.missing() if s in seen)
    (WORK / "missing_ar.txt").write_text("\n".join(sorted(i18n.missing())), encoding="utf-8")
    check("Arabic: no untranslated workbench strings", not miss, miss[:20])

qh.finish(w)
