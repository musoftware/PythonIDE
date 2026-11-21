"""ECU / Firmware project in the IDE, the way a user works (qh.py harness: QSettings org RADIDE-TEST, offscreen,
screenshots only through widget.grab()).  Synthetic firmware only (radide/firmware/project/synth.py).

Run:  python samples\\Tests\\Firmware\\EcuProject\\qa_ecu_project_ide.py

  1  New Project > Firmware group lists "ECU / Firmware Project"; the demo template opens; the one-time safety
     notice appears once (accepted -> stored, not shown for the next ECU project).
  2  Solution Explorer "ECU Project" node; Project > ECU Project menu.
  3  Working copy in the hex editor: edit a calibration byte, save -> the calibration CRC is recalculated on save
     (Output names the block); the original opens read-only.
  4  Checksums dialog: verify, run the checksum finder (thread) on the original, add a candidate as a block,
     export / import a profile, OK -> ecu.json.
  5  Versions dialog: save a version, map-level diff, restore.
  6  Build (checksum report), Build Settings -> Intel HEX, Export Modification Report (HTML), Export / Import BPS.
  7  Checksum Toolkit on any file; the dialogs in Arabic.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "ecu_project")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, wait  # noqa: E402

from PyQt6.QtCore import Qt, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

WORK = Path(qh.WORK) / "ecu_project"
for _dp, _dn, _fn in os.walk(WORK):          # originals are read-only on disk
    for _f in _fn:
        os.chmod(os.path.join(_dp, _f), 0o666)
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True, exist_ok=True)
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)


def gshot(widget, name):
    p = SHOTS / (name + ".png")
    widget.grab().save(str(p))
    print("SHOT", p, flush=True)
    return p


def later(fn, ms=50):
    """Run *fn* once a modal dialog is up (QTimer + the dialog's own event loop)."""
    errors = []

    def run():
        try:
            fn()
        except Exception as e:  # noqa: BLE001 - reported as a failed check
            import traceback
            errors.append(traceback.format_exc())
            check(f"dialog step {fn.__name__} raised", False, e)
            for wdg in QApplication.topLevelWidgets():
                if wdg.isModal() and wdg.isVisible():
                    wdg.close()
    QTimer.singleShot(ms, run)
    return errors


NOTICES = []


def click_notice():
    for wdg in QApplication.topLevelWidgets():
        if isinstance(wdg, QMessageBox) and wdg.objectName() == "firmwareSafetyNotice" and wdg.isVisible():
            NOTICES.append(wdg.text())
            gshot(wdg, "01_safety_notice")
            for b in wdg.buttons():
                if wdg.buttonRole(b) == QMessageBox.ButtonRole.AcceptRole:
                    b.click()
                    return
    QTimer.singleShot(100, click_notice)


w = qh.window()
feat = getattr(w, "firmware_project", None)
check("feature installed", feat is not None)

# ---------------------------------------------------------------- 1 New Project + notice
from radide import dialogs  # noqa: E402
from radide.languages import get_plugin  # noqa: E402
from radide.firmware.project import notice  # noqa: E402
from radide.firmware.project.model import EcuProject  # noqa: E402

check("1 New Project has a Firmware group with ECU / Firmware Project",
      ("Firmware", ["firmware-ecu"]) in dialogs.LANGUAGE_GROUPS or
      any(g == "Firmware" and "firmware-ecu" in ids for g, ids in dialogs.LANGUAGE_GROUPS))
dlg = dialogs.NewProjectDialog(w)
groups = {dlg.langs.topLevelItem(i).text(0): [dlg.langs.topLevelItem(i).child(j).text(0)
                                              for j in range(dlg.langs.topLevelItem(i).childCount())]
          for i in range(dlg.langs.topLevelItemCount())}
check("1 New Project dialog: Firmware > ECU / Firmware Project",
      any("ECU" in t for t in groups.get("Firmware", [])), groups.get("Firmware"))
gshot(dlg, "00_new_project")
dlg.close()
check("1 notice not accepted yet (fresh test settings)", not notice.accepted())
folder = WORK / "DemoEcu"
get_plugin("firmware-ecu").create_new_project(folder, "DemoEcu", "ecu_demo")
QTimer.singleShot(100, click_notice)
w.open_project(folder, ask=False)
check("1 ECU project opened", w.project is not None and w.project.language == "firmware-ecu")
wait(lambda: notice.accepted(), 10)
check("1 safety notice shown once and accepted", len(NOTICES) == 1 and notice.accepted() and
      "emissions" in NOTICES[0], NOTICES)

# ---------------------------------------------------------------- 2 tree + menu
pump(0.5)


def tree_texts():
    out, stack = [], [w.solution.topLevelItem(i) for i in range(w.solution.topLevelItemCount())]
    while stack:
        it = stack.pop()
        out.append(it.text(0))
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


tt = tree_texts()
check("2 Solution Explorer: ECU Project node", "ECU Project" in tt and any(t.startswith("Original:") for t in tt) and
      any(t.startswith("Checksums (3 block(s)") for t in tt), tt)
gshot(w.solution, "02_solution_explorer")
acts = [a.text().replace("&", "") for a in feat.menu.actions()]
check("2 Project > ECU Project menu", all(x in acts for x in ("Set Original...", "Checksums...", "Versions...",
                                                                 "Build ECU Project", "Export Patch (IPS / BPS)...",
                                                                 "Checksum Toolkit (any file)...")), acts)

# ---------------------------------------------------------------- 3 hex editor + correct on save
ep = EcuProject.load(folder)
doc = feat.edit_work()
check("3 working copy opens in the hex editor (writable)", doc is not None and not doc.read_only)
pack = ep.map_pack()
m16 = pack.get("Demo map 16x16")
off = m16.address + 10
old = doc.data()[off]
doc.buf.overwrite(off, bytes([(old + 7) & 0xFF]))
check("3 edit marks the document modified", doc.is_modified())
w.log("--- before save ---")
doc.save()
pump(0.8)
ep = EcuProject.load(folder)
res = ep.verify_checksums()
out = w.output.toPlainText()
check("3 save -> checksums recalculated on save, all OK", all(r.ok for r in res) and
      "Checksums recalculated on save (1 of 3 block(s))" in out and "Calibration CRC32" in out.split("before save")[-1],
      [r.line() for r in res])
check("3 the open document shows the corrected bytes", doc.data() == ep.work_bytes() and not doc.is_modified())
od = feat.view_original()
check("3 original opens read-only", od is not None and od.read_only)
gshot(doc, "03_working_copy_hex")

# ---------------------------------------------------------------- 4 checksums dialog + finder
prof = WORK / "exported.ecuprofile.json"


def checksum_step():
    d = feat.last_dialog
    d.verify()
    check("4 verify in the dialog: 3 OK", d.report.toPlainText().count(": OK") == 3, d.report.toPlainText())
    gshot(d, "04_checksums_blocks")
    d.tabs.setCurrentIndex(1)
    d.f_gran.setCurrentText("0x1000")
    for i in range(d.f_algos.count()):            # keep the run short: three algorithms
        it = d.f_algos.item(i)
        it.setCheckState(Qt.CheckState.Checked if it.text() in ("crc32", "crc16-ccitt-false", "sum16-be")
                         else Qt.CheckState.Unchecked)
    d.f_holes.setChecked(True)
    d.run_finder()
    ok = wait(lambda: d.found and not d.finder_running(), 60)
    algos = [(c.algorithm, c.store) for c in d.found]
    check("4 finder (thread) locates the three demo checksums in the original",
          ok and {("crc32", 0xFFFC), ("crc16-ccitt-false", 0x7FFC), ("sum16-be", 0x3FFE)} <= set(algos), algos)
    gshot(d, "05_checksum_finder")
    row = next(i for i, c in enumerate(d.found) if c.algorithm == "crc16-ccitt-false")
    d.f_table.selectRow(row)
    n = d.add_selected()
    check("4 candidate added as a block (unverified)", n == 1 and len(d.blocks) == 4 and not d.blocks[-1].verified)
    d.export_profile(str(prof))
    check("4 profile exported", prof.is_file() and len(json.loads(prof.read_text("utf-8"))["blocks"]) == 4)
    d.accept()


later(checksum_step, 300)
feat.checksums()
ep = EcuProject.load(folder)
check("4 OK saved the blocks into ecu.json", len(ep.checksums) == 4)
ep.checksums = ep.checksums[:3]
ep.save()

# ---------------------------------------------------------------- 5 versions
def versions_step():
    d = feat.last_dialog
    v = d.save_version("Raised a cell", "map 16x16 +0.7")
    check("5 version saved", v is not None and v.id == "v001")
    d.against.setCurrentIndex(d.against.findData("original"))
    d.select("v001")
    txt = d.diff.toPlainText()
    check("5 map-level diff against the original", "Demo map 16x16" in txt and "Changed maps" in txt, txt[:600])
    gshot(d, "06_versions")
    d.reject()


later(versions_step, 300)
feat.versions()
ep = EcuProject.load(folder)
check("5 version kept in ecu.json", [v.name for v in ep.versions] == ["Raised a cell"])

# ---------------------------------------------------------------- 6 build, settings, report, patches
data = bytearray(ep.work_bytes())
data[m16.address + 40] ^= 0x11                 # an edit written outside the hex editor (no save hook)
ep.write_work(data)
r = feat.build()
check("6 Build: output written, calibration CRC recalculated",
      r is not None and r.output.is_file() and [x.name for x in r.recalculated] == ["Calibration CRC32"],
      r and [x.line() for x in r.checksums])
check("6 Build log in the Output window", "Calibration CRC32 @ 0xFFFC: recalculated" in w.output.toPlainText())


def settings_step():
    d = feat.last_dialog
    d.container.setCurrentIndex(d.container.findData("hex"))
    d.base.setText("0x80000000")
    gshot(d, "07_build_settings")
    d._ok()


later(settings_step, 300)
feat.build_settings()
r2 = feat.build()
from radide.firmware.project.model import load_image  # noqa: E402
flat, fmt, base = load_image(r2.output)
check("6 Build Settings -> Intel HEX at 0x80000000", r2.output.suffix == ".hex" and fmt == "ihex" and
      base == 0x80000000, (r2.output, fmt, hex(base)))
rp = feat.export_report(str(WORK / "report.html"))
check("6 modification report (HTML)", rp is not None and "Demo map 16x16" in rp.read_text(encoding="utf-8"))
pp = feat.export_patch(str(WORK / "mod.bps"))
check("6 BPS exported", pp is not None and pp.stat().st_size > 0)
folder2 = WORK / "SecondEcu"
get_plugin("firmware-ecu").create_new_project(folder2, "SecondEcu", "ecu_demo")
NOTICES.clear()
w.open_project(folder2, ask=False)
pump(1.0)
check("1 the notice is not shown again", not NOTICES and not any(isinstance(x, QMessageBox) and x.isVisible()
                                                                   for x in QApplication.topLevelWidgets()))
feat.import_patch(str(pp))
e2 = EcuProject.load(folder2)
check("6 BPS imported into a fresh project = built image", e2.work_bytes() == flat and
      any(v.name.startswith("Imported") for v in e2.versions))
gshot(w, "08_ide_after_import")


# ---------------------------------------------------------------- 7 toolkit + Arabic
def toolkit_step():
    d = feat.last_dialog
    check("7 Checksum Toolkit is read-only (no Correct)", not d.b_correct.isEnabled())
    d.reject()


later(toolkit_step, 300)
feat.checksum_toolkit(str(folder / "original" / "demo_ecu.bin"))
from radide import i18n  # noqa: E402
i18n.set_language(qh.app, "ar")
pump(0.5)


def arabic_step():
    d = feat.last_dialog
    gshot(d, "09_checksums_arabic")
    check("7 Arabic: dialog tabs translated (code still sees English)",
          d.tabs.tabBar().tabText(1) == "Checksum Finder" and i18n.tr("Checksum Finder") != "Checksum Finder")
    d.reject()


later(arabic_step, 400)
feat.checksums()
missing = [s for s in ("ECU Project", "Checksums...", "Versions...", "Build ECU Project", "Checksum Finder",
                       "Find Checksums", "Add Selected as Block", "Vehicle software notice", "I understand",
                       "ECU / Firmware Project", "ECU Project (Demo Firmware)", "Export Modification Report...")
           if i18n.tr(s) == s]
check("7 Arabic catalog has the ECU strings", not missing, missing)
i18n.set_language(qh.app, "en")
qh.finish(w)
