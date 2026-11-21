"""Firmware & ECU - end-to-end QA as a user (real MainWindow, qh.py: QSettings org RADIDE-TEST, widget.grab only).

Run:  python samples\\Tests\\Firmware\\QA\\qa_firmware_e2e.py
      set QA_LANG=ar & set QA_THEME=dark & python samples\\Tests\\Firmware\\QA\\qa_firmware_e2e.py
      set QA_GHIDRA=1 to also run Ghidra headless on the rusEFI image (several minutes)

Synthetic firmware only (RAD IDE writes it: ARM Cortex-M code + vector table + calibration maps with axes +
identification strings + two checksum blocks); real open-source firmware = rusEFI (GPL-3.0) from its official GitHub
releases into %TEMP%\\radide-fw-data (skipped offline). Flow:

  1  menus, one-time safety notice (modal of the project feature + bar of the workbench = one notice)
  2  ECU project from a raw .bin  -> CPU/base detection, Find Maps, A2L labels, map edit (table/3D),
     ori vs mod differences, checksums wrong -> corrected, Build to .bin / .hex / .s19 (Build Settings of the
     project feature, then F7 in the workbench), modification report (HTML + text), IPS patch, versions + compare
  3  ECU project from Intel HEX at 0x08000000 -> builds back to HEX at the same address
  4  rusEFI firmware: analysis view (ARM Cortex-M, base 0x08000000, disassembly; Ghidra with QA_GHIDRA=1)
  5  EEPROM image view
  6  regression smoke: retro ROM hex editor (.nes / plain .bin), go.mod stays text, Python / C files open
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
sys.path.insert(0, str(HERE.parent / "Formats"))
LANG = os.environ.get("QA_LANG", "")
THEME = os.environ.get("QA_THEME", "")
TAG = (LANG or "en") + ("_" + THEME if THEME else "")
os.environ.setdefault("QA_NAME", "fwe2e_" + TAG)
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import qh  # noqa: E402

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QDialog, QMessageBox  # noqa: E402

check, pump, wait = qh.check, qh.pump, qh.wait
WORK = Path(qh.WORK) / ("fwe2e_" + TAG)


def _writable(func, path, _exc):
    os.chmod(path, 0o666)
    func(path)


if WORK.exists():
    shutil.rmtree(WORK, onerror=_writable)
WORK.mkdir(parents=True)


def shot(widget, name):
    return qh.shot(widget, f"fwe2e_{TAG}_{name}")


# ---- the modal safety notice of the project feature: record it and press "I understand"
NOTICES = []
_orig_exec = QMessageBox.exec


def _exec(box):
    if box.objectName() == "firmwareSafetyNotice":
        NOTICES.append(box.text())
        ok = next((b for b in box.buttons() if box.buttonRole(b) == QMessageBox.ButtonRole.AcceptRole), None)
        if ok is not None:
            ok.click()
        return 0
    return _orig_exec(box)


QMessageBox.exec = _exec

# ---- dialogs driven by the test (Build Settings)
DIALOG_SETUP = []
_orig_dexec = QDialog.exec


def _dexec(dlg):
    if DIALOG_SETUP:
        fn = DIALOG_SETUP.pop(0)
        fn(dlg)
        return dlg.result()
    return _orig_dexec(dlg)


QDialog.exec = _dexec

if LANG:
    from radide import i18n
    i18n.set_language(qh.app, LANG)
w = qh.window()
if THEME:
    from radide.features.workbench import set_theme
    set_theme(w, THEME.capitalize())
    pump(0.5)

from radide.firmware.analysis.synth import make_image  # noqa: E402
from radide.firmware.checksum.blocks import ChecksumBlock, correct, verify  # noqa: E402
from radide.firmware.formats import load as fw_load  # noqa: E402
from radide.firmware.formats import save as fw_save  # noqa: E402
from radide.firmware.formats.memmap import MemoryMap  # noqa: E402
from radide.firmware.maps.a2l import export_a2l  # noqa: E402
from radide.firmware.maps.model import AxisDef, MapDef, MapPack  # noqa: E402
from radide.firmware.ui import adapters as A  # noqa: E402
from radide.firmware.ui.workbench import FirmwareWorkbench  # noqa: E402
from radide.retro.rom.hexdoc import HexDocument  # noqa: E402

fe = getattr(w, "firmware_ide", None)
fp = getattr(w, "ecu_project_feature", None)
fa = getattr(w, "firmware_analysis", None)
fm = getattr(w, "firmware_maps", None)
check("1 all four firmware features installed", None not in (fe, fp, fa, fm), (fe, fp, fa, fm))


def plain(t):
    return t.replace("&&", "\x00").replace("&", "").replace("\x00", "&")


def find_menu(title, parent=None):
    acts = parent.actions() if parent is not None else w.menuBar().actions()
    return next((a.menu() for a in acts if a.menu() is not None and plain(a.text()) == title), None)


tools = find_menu("Tools")
fw_menus = [a for a in tools.actions() if a.menu() is not None and plain(a.text()) == "Firmware & ECU"]
check("1 exactly one Tools > Firmware & ECU menu", len(fw_menus) == 1, len(fw_menus))
fwm = fw_menus[0].menu() if fw_menus else None
names = [plain(a.text()) for a in fwm.actions()] if fwm else []
subs = {plain(a.text()): a.menu() for a in fwm.actions() if a.menu() is not None} if fwm else {}
check("1 menu has workbench, analysis, converter and maps entries",
      {"Open Firmware in Workbench...", "Analyze Firmware File..."} <= set(names)
      and any(x.startswith("Firmware Converter") for x in names)
      and "Calibration Maps" in subs, names)

# ============================================================== synthetic firmware with maps + checksums
img = make_image("arm-thumb", seed=11)
BASE = img.base
data = bytearray(img.bytes())
size = len(data)
calib = img.calib_start
blocks = [ChecksumBlock("Code sum16", "sum16-le", [(0, calib - 4)], [], calib - 4, 2, "le", note="synthetic"),
          ChecksumBlock("Calibration CRC32", "crc32", [(calib, size - 4)], [], size - 4, 4, "le", note="synthetic")]
correct(data, blocks)
data = bytes(data)
check("synthetic image: checksums valid", all(r.ok for r in verify(data, blocks)))
maps_truth = [t for t in img.tables if t.kind == "map"]
axes = {t.name: t for t in img.tables if t.kind == "axis"}
raw_bin = WORK / "synthetic_ecu.bin"
raw_bin.write_bytes(data)
hex_file = WORK / "synthetic_ecu.hex"
fw_save(MemoryMap.from_bytes(data, BASE), hex_file, "ihex")
prof_file = WORK / "synthetic_checksums.json"
import json  # noqa: E402
prof_file.write_text(json.dumps({"blocks": [b.to_dict() for b in blocks]}, indent=1))

# an A2L that names the maps (ECU addresses at 0x08000000)
a2l_maps = []
for i, t in enumerate(maps_truth):
    ax, ay = axes[f"axis_x{i}"], axes[f"axis_y{i}"]
    a2l_maps.append(MapDef(f"KF_DEMO_{i}", t.address - BASE, t.cols, t.rows, "u16", "le", "row", 0.1, 0.0, "%",
                           AxisDef("rpm", ax.address - BASE, ax.cols, "u16", "le", 1.0, 0.0, "rpm"),
                           AxisDef("load", ay.address - BASE, ay.cols, "u16", "le", 1.0, 0.0, "mg/stroke"),
                           folder="Demo", description=f"synthetic map {i}", source="a2l"))
a2l_file = WORK / "synthetic_ecu.a2l"
a2l_file.write_text(export_a2l(MapPack("SYNTH", a2l_maps, base_address=BASE)), encoding="utf-8")

# ============================================================== 2 ECU project from the raw .bin
from radide.firmware.project import notice  # noqa: E402
check("1 notice not yet accepted (fresh settings)", not notice.accepted())
proj = WORK / "SynthEcu"
wb = fe.new_project_dialog(source=str(raw_bin), folder=proj, name="SynthEcu")
pump(1.5)
check("2 ECU project created (firmware-ecu) and workbench open", isinstance(wb, FirmwareWorkbench) and
      w.project is not None and w.project.language == "firmware-ecu", (type(wb), getattr(w.project, "language", "")))
check("1 safety notice shown exactly once", len(NOTICES) == 1 and ("emissions" in NOTICES[0].lower() or
                                                               "الانبعاث" in NOTICES[0]), NOTICES)
check("1 notice accepted and stored", notice.accepted())
pump(0.3)
check("1 workbench notice bar hidden after the notice was accepted (no second notice)",
      wb is not None and not wb.notice.isVisible(), wb.notice.isVisible() if wb else None)
shot(w, "01_project_opened")
check("2 original read-only on disk", not os.access(wb.proj.original_path, os.W_OK))
check("2 working copy = original", wb.data() == data)

# CPU / base
res = wb.analyze()
cpu = str(res["facts"].get("CPU (guess)", ""))
check("2 Analyze: ARM Cortex-M detected", "ARM" in cpu or "Cortex" in cpu, res["facts"])
base_fact = " ".join(str(v) for k, v in res["facts"].items() if "base" in k.lower() or "address" in k.lower())
check("2 Analyze: load address 0x08000000 suggested", "08000000" in base_fact.upper(), res["facts"])
shot(w, "02_analysis")
n = wb.disassemble(0x200)
check("2 Disassembly (Thumb) at 0x200", n > 10 and any(m in wb.dis_text.toPlainText() for m in ("push", "bl ", "ldr")),
      wb.dis_text.toPlainText()[:300])

# checksums profile
check("2 checksum profile loaded", wb.load_profile(prof_file) == 2)
rep = wb.verify_checksums(True)
check("2 checksums OK on the original", len(rep) == 2 and all(r["ok"] for r in rep), rep)

# Find maps
cnt = wb.find_maps()
found = {m.address for m in wb.potential}
truth_off = {t.address - BASE for t in maps_truth}
hit = truth_off & found
check("2 Find Maps finds the embedded maps", len(hit) >= len(truth_off) - 1, (sorted(hex(x) for x in truth_off),
                                                                              sorted(hex(x) for x in found)[:20]))
shot(w, "03_potential_maps")

# A2L labels
n_a2l = wb.import_a2l(a2l_file)
named = {m.name: m for m in wb.maps}
check("2 A2L import names all maps", n_a2l == len(maps_truth) and all(f"KF_DEMO_{i}" in named
                                                                       for i in range(len(maps_truth))),
      (n_a2l, list(named)))
m0 = named.get("KF_DEMO_0")
check("2 A2L map at the right file offset with axes", m0 is not None and m0.address == maps_truth[0].address - BASE
      and m0.x_addr == axes["axis_x0"].address - BASE and abs(m0.factor - 0.1) < 1e-9,
      m0 and (hex(m0.address), hex(m0.x_addr), m0.factor))

# edit in the table / 3D view
wb.open_map(m0)
pump(0.3)
t = wb.mapedit.table
check("2 map editor: rows x cols from the A2L", (t.rowCount(), t.columnCount()) == (m0.rows, m0.cols),
      (t.rowCount(), t.columnCount()))
before = A.read_map(wb.data(), m0)[2][2][3]
t.setFocus()
t.clearSelection()
t.setCurrentCell(2, 3)
pump(0.1)
QTest.keyClick(t, Qt.Key.Key_PageUp)
pump(0.2)
after = A.read_map(wb.data(), m0)[2][2][3]
check("2 Page Up raises a cell by ten steps", after == before + 10, (before, after))
t.clearSelection()
for c in range(4):
    t.item(5, c).setSelected(True)
check("2 +5 % on four cells", wb.mapedit.percent(5) == 4)
wb.mapedit.set_view(2)
pump(0.3)
shot(wb.mapedit, "04_map_3d")
check("2 3D view shown", wb.mapedit.stack.currentIndex() == 2)
wb.mapedit.set_view(0)

# ori vs mod
nd = wb.compare()
dmaps = {wb.difftree.topLevelItem(i).text(4) for i in range(wb.difftree.topLevelItemCount())}
check("2 differences ori vs mod name the edited map", nd >= 1 and "KF_DEMO_0" in dmaps, (nd, dmaps))
shot(w, "05_differences")

# checksums wrong -> corrected
rep = wb.verify_checksums(True)
check("2 edits make the calibration CRC wrong", any(not r["ok"] for r in rep), rep)
rep = wb.correct_checksums()
check("2 Correct Checksums", rep and all(r["ok"] for r in rep), rep)
wb.save()
pump(0.3)

# build to .bin (F7)
w.activateWindow()
wb.mapedit.table.setFocus()
pump(0.2)
QTest.keyClick(wb.mapedit.table, Qt.Key.Key_F7)
pump(1.0)
built = getattr(wb, "built", None)
check("2 F7 builds .bin", built is not None and Path(built).suffix == ".bin" and Path(built).is_file(), built)
if built:
    check("2 .bin output has valid checksums", all(r.ok for r in verify(Path(built).read_bytes(), blocks)))


def build_as(container: str, base: int):
    def setup(dlg):
        dlg.container.setCurrentIndex(dlg.container.findData(container))
        dlg.base.setText(f"0x{base:X}")
        dlg._ok()
    DIALOG_SETUP.append(setup)
    fp.build_settings()
    pump(0.2)
    wb.built = None
    wb.build()
    pump(0.5)
    return getattr(wb, "built", None)


out_hex = build_as("hex", BASE)
check("2 Build Settings -> Intel HEX, F7 builds .hex", out_hex is not None and Path(out_hex).suffix == ".hex", out_hex)
if out_hex:
    mm = fw_load(out_hex)
    check("2 .hex output at 0x08000000 with the modified bytes", mm.min_address == BASE and
          mm.to_flat() == wb.data(), hex(mm.min_address))
out_s19 = build_as("s19", BASE)
check("2 Build Settings -> S-record, F7 builds .s19", out_s19 is not None and Path(out_s19).suffix == ".s19", out_s19)
if out_s19:
    mm = fw_load(out_s19)
    check("2 .s19 output at 0x08000000 with valid checksums", mm.min_address == BASE and
          all(r.ok for r in verify(mm.to_flat(), blocks)), hex(mm.min_address))
from radide.firmware.project.model import EcuProject  # noqa: E402
check("2 ecu.json keeps the s19 container after the workbench saved", EcuProject.load(proj).container == "s19",
      EcuProject.load(proj).container)
check("2 original never written", EcuProject.load(proj).check_original()[0])

# report + IPS
rp_html = fp.export_report(str(WORK / "report.html"))
rp_txt = fp.export_report(str(WORK / "report.txt"))
txt = Path(rp_txt).read_text(encoding="utf-8") if rp_txt else ""
check("2 modification report (HTML + text) names the map and the checksum blocks",
      rp_html and Path(rp_html).is_file() and "KF_DEMO_0" in txt and "Calibration CRC32" in txt, txt[:600])
ips = fp.export_patch(str(WORK / "mod.ips"))
from radide.retro.rom.patches import apply_patch  # noqa: E402
if ips:
    patched = apply_patch(data, Path(ips).read_bytes())
    check("2 IPS patch: original + patch = working copy with corrected checksums",
          bytes(patched) == wb.data() and all(r.ok for r in verify(bytes(patched), blocks)))
else:
    check("2 IPS patch exported", False)

# versions + compare
v1 = wb.save_version("stage A", "map 0 edited")
t.clearSelection()
t.setCurrentCell(0, 0)
wb.mapedit.step(3)
wb.correct_checksums()
v2 = wb.save_version("stage B", "one more cell")
check("2 two versions saved", v1 and v2 and len(EcuProject.load(proj).versions) == 2)
ep = EcuProject.load(proj)
vids = [v.id for v in ep.versions]
d = ep.diff(vids[0], vids[1])
check("2 compare versions: map-level change in KF_DEMO_0", any(mc.name == "KF_DEMO_0" for mc in d.maps),
      d.summary() + " " + str([mc.line() for mc in d.maps]))
nd2 = wb.compare(ep.version_bytes(vids[0]))
check("2 workbench compare against version A", nd2 >= 1, nd2)
shot(w, "06_versions_compare")
w.save_all()
pump(0.3)

# ============================================================== 3 ECU project from Intel HEX
proj2 = WORK / "SynthHex"
wb2 = fe.new_project_dialog(source=str(hex_file), folder=proj2, name="SynthHex")
pump(1.0)
check("3 HEX project: workbench at base 0x08000000", isinstance(wb2, FirmwareWorkbench) and wb2.img.base == BASE
      and wb2.data() == data, getattr(getattr(wb2, "img", None), "base", None))
check("3 notice not shown again", len(NOTICES) == 1 and not wb2.notice.isVisible())
wb2.load_profile(prof_file)
n_a2l2 = wb2.import_a2l(a2l_file)
check("3 A2L on the HEX project", n_a2l2 == len(maps_truth), n_a2l2)
mx = next(m for m in wb2.maps if m.name == "KF_DEMO_1")
wb2.open_map(mx)
wb2.mapedit.table.setCurrentCell(1, 1)
wb2.mapedit.step(1)
wb2.correct_checksums()
out2 = wb2.build()
pump(0.5)
check("3 HEX project builds to .hex (same container)", out2 is not None and Path(out2).suffix == ".hex", out2)
if out2:
    mm2 = fw_load(out2)
    check("3 HEX output at 0x08000000, checksums valid", mm2.min_address == BASE and
          all(r.ok for r in verify(mm2.to_flat(), blocks)), hex(mm2.min_address))
w.save_all()

# ============================================================== 4 rusEFI
try:
    from download_rusefi import ensure
    rus = ensure()
except Exception as e:  # noqa: BLE001
    print("rusEFI download error:", e)
    rus = None
if rus is None:
    print("SKIP rusEFI (offline)")
else:
    view = fa.open_analysis(rus / "rusefi.bin")
    check("4 rusEFI analysis view", view is not None and wait(lambda: view.ready, 120))
    if view is not None and view.ready:
        check("4 rusEFI: ARM Cortex-M", view.current_arch() == "arm-thumb", view.current_arch())
        check("4 rusEFI: base 0x08000000", view.base_address() == 0x08000000, hex(view.base_address()))
        view.tabs.setCurrentIndex(3)
        pump(0.3)
        lst = view.listing.toPlainText()
        check("4 rusEFI: disassembly listing", len(lst.splitlines()) > 50 and ("push" in lst or "bl" in lst), lst[:200])
        check("4 rusEFI: no notice bar (already accepted)", not view.notice.isVisible())
        shot(view, "07_rusefi_disasm")
        from radide.firmware.analysis import ghidra
        ok_g, info_g = ghidra.available()
        if ok_g and os.environ.get("QA_GHIDRA") == "1":
            view.run_ghidra()
            check("4 rusEFI Ghidra run", wait(lambda: view.ghidra_result is not None or
                                             (view._gjob is None and view.btn_ghidra.isEnabled()), 1800))
            check("4 rusEFI Ghidra decompiled C", "Decompiled by Ghidra" in view.gcode.toPlainText(),
                  view.ghidra_status.text())
            shot(view, "08_rusefi_ghidra")
        else:
            print("SKIP Ghidra on rusEFI:", "set QA_GHIDRA=1" if ok_g else info_g)
    # the rusEFI .bin also opens in the workbench (Open With) and is guessed as ARM
    wbr = fe.open_workbench(rus / "rusefi.bin", read_only=True)
    pump(0.5)
    if wbr is not None:
        r = wbr.analyze()
        check("4 rusEFI in the workbench: ARM", "ARM" in str(r["facts"].get("CPU (guess)", "")), r["facts"])

# ============================================================== 5 EEPROM
eep = WORK / "dash_95080.eep"
eep_bytes = bytes((i * 13 + 5) & 0xFF for i in range(1024))
eep.write_bytes(eep_bytes)
wbe = w.open_any_file(str(eep))
pump(0.3)
check("5 EEPROM image opens read-only with chip list", isinstance(wbe, FirmwareWorkbench) and wbe.read_only and
      wbe.ee is not None and any("95080" in c for c in wbe.ee.chips), getattr(getattr(wbe, "ee", None), "chips", None))
if isinstance(wbe, FirmwareWorkbench):
    wbe.tabs.setCurrentIndex(wbe.tabs.count() - 1)
    wbe.ee_mode.setCurrentIndex(wbe.ee_mode.findData("swap16"))
    pump(0.2)
    check("5 EEPROM 16-bit swap view", wbe.eeprom_view_bytes()[:2] == bytes([eep_bytes[1], eep_bytes[0]]))
    shot(wbe, "09_eeprom")

# ============================================================== 6 regression smoke
nes = WORK / "tiny.nes"
nes.write_bytes(b"NES\x1a\x02\x01\x01\x00" + bytes(8) + bytes(32768) + bytes(8192))
dn = w.open_any_file(str(nes))
pump(0.3)
check("6 .nes opens in the retro hex editor", isinstance(w.tabs.currentWidget(), HexDocument),
      type(w.tabs.currentWidget()).__name__)
plain_bin = WORK / "data.bin"
plain_bin.write_bytes(bytes(range(256)) * 4)
w.open_any_file(str(plain_bin))
pump(0.3)
check("6 ordinary .bin outside an ECU project: ROM hex editor", isinstance(w.tabs.currentWidget(), HexDocument),
      type(w.tabs.currentWidget()).__name__)
gomod = WORK / "go.mod"
gomod.write_text("module example.com/x\n\ngo 1.22\n")
w.open_any_file(str(gomod))
pump(0.3)
cur = w.tabs.currentWidget()
check("6 go.mod opens as text (not the workbench)", not isinstance(cur, (FirmwareWorkbench, HexDocument)),
      type(cur).__name__)
for name, text in (("hello.py", "print('hi')\n"), ("hello.c", "int main(void){return 0;}\n")):
    p = WORK / name
    p.write_text(text)
    w.open_any_file(str(p))
    pump(0.3)
    cur = w.tabs.currentWidget()
    ed = getattr(cur, "editor", cur)
    check(f"6 {name} opens in a code editor", hasattr(ed, "text") or hasattr(ed, "toPlainText"), type(cur).__name__)
    got = ed.text() if hasattr(ed, "text") else ed.toPlainText()
    check(f"6 {name} content shown", text.strip() in got, got[:80])
shot(w, "10_ide")

# ============================================================== Arabic
if LANG == "ar":
    from radide import i18n
    for label, wd, attr in (("workbench Find Maps", wb.a_find, "text"), ("dock Potential Maps", wb.d_pot, "windowTitle")):
        s = i18n.shown(wd, attr) if attr != "text" else i18n.shown(wd)
        check(f"AR {label} translated", any("؀" <= c <= "ۿ" for c in s), s)
    check("AR safety notice text translated", NOTICES and any("؀" <= c <= "ۿ" for c in NOTICES[0]), NOTICES[:1])

qh.finish(w)
