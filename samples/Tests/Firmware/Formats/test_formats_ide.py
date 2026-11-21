"""Firmware formats + analysis in the IDE (qh.py harness: QSettings org RADIDE-TEST, offscreen, screenshots only
through widget.grab()). Synthetic firmware only.

    python samples/Tests/Firmware/Formats/test_formats_ide.py

  1  New Project > Firmware lists "Firmware / ECU Analysis"; the demo template creates a project with a
     read-only original + SHA-256; Solution Explorer "Firmware Analysis" node; Project > Firmware Analysis menu.
  2  Analysis view: one-time notice bar, CPU / base guesses, entropy graph, regions, strings with
     identification tags, disassembly listing, references to a calibration table, memory map; Show in hex.
  3  An S-record TriCore image and an ELF open in the view (addresses from the container).
  4  Firmware Converter: convert, even / odd split, merge.
  5  Build writes build/analysis.txt (report node in Solution Explorer); Ghidra tab (when Ghidra is installed).
  6  Arabic: the new strings are in the catalog and the view's tabs are translated.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "fw_formats")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, wait  # noqa: E402

WORK = Path(qh.WORK) / "fw_formats"
for _dp, _dn, _fn in os.walk(WORK):          # originals are read-only on disk
    for _f in _fn:
        os.chmod(os.path.join(_dp, _f), 0o666)
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True, exist_ok=True)

w = qh.window()
feat = getattr(w, "firmware_analysis", None)
check("feature installed (win.firmware_analysis)", feat is not None)

from radide import dialogs  # noqa: E402
from radide.languages import get_plugin  # noqa: E402
from radide.firmware.analysis.project import FirmwareProject  # noqa: E402
from radide.firmware.analysis.synth import make_image  # noqa: E402
from radide.firmware.analysis.view import FirmwareAnalysisView  # noqa: E402
from radide.firmware.formats import MemoryMap, Symbol, elf, load, save  # noqa: E402

# ---------------------------------------------------------------- 1 project
check("1 LANGUAGE_GROUPS: Firmware has firmware-analysis",
      any(g == "Firmware" and "firmware-analysis" in ids for g, ids in dialogs.LANGUAGE_GROUPS))
dlg = dialogs.NewProjectDialog(w)
groups = {dlg.langs.topLevelItem(i).text(0): [dlg.langs.topLevelItem(i).child(j).text(0)
                                              for j in range(dlg.langs.topLevelItem(i).childCount())]
          for i in range(dlg.langs.topLevelItemCount())}
check("1 New Project dialog: Firmware > Firmware / ECU Analysis",
      any("Firmware / ECU Analysis" in t for t in groups.get("Firmware", [])), groups.get("Firmware"))
qh.shot(dlg, "fwfmt_00_new_project")
dlg.close()
folder = WORK / "DemoAnalysis"
get_plugin("firmware-analysis").create_new_project(folder, "DemoAnalysis", "fwa_demo")
fp = FirmwareProject.load(folder)
check("1 demo: original read-only with SHA-256", fp.original_path.is_file() and not os.access(fp.original_path, os.W_OK)
      and len(fp.sha256) == 64)
check("1 demo: CPU + base recorded", fp.arch == "arm-thumb" and fp.base == 0x08000000, (fp.arch, hex(fp.base)))
w.open_project(folder, ask=False)
pump(1.5)


def tree_items():
    out = []
    stack = [w.solution.topLevelItem(i) for i in range(w.solution.topLevelItemCount())]
    while stack:
        it = stack.pop()
        out.append(it)
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


from PyQt6.QtCore import Qt  # noqa: E402
names = [it.text(0) for it in tree_items()]
check("1 Solution Explorer: Firmware Analysis node + original", "Firmware Analysis" in names and
      any(n.startswith("Original: synthetic_cortex_m.bin") for n in names), names[:30])
pm = next((a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == "Project"), None)
sub = next((a.menu() for a in pm.actions() if a.menu() is not None and
            a.text().replace("&", "") == "Firmware Analysis"), None) if pm else None
check("1 Project > Firmware Analysis menu", sub is not None)
if sub is not None:
    feat._update_menu()
    check("1 menu enabled for the analysis project", all(a.isEnabled() for a in sub.actions() if a.text()))
tm = next((a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == "Tools"), None)
fwm = next((a.menu() for a in tm.actions() if a.menu() is not None and "Firmware" in a.text()), None) if tm else None
check("1 Tools > Firmware & ECU > Analyze Firmware File...", fwm is not None and
      any(a.text().replace("&", "") == "Analyze Firmware File..." for a in fwm.actions()))
fw_menus = [a for a in tm.actions() if a.menu() is not None and "Firmware" in a.text()] if tm else []
check("1 only one Firmware & ECU menu under Tools", len(fw_menus) == 1, [a.text() for a in fw_menus])

# ---------------------------------------------------------------- 2 analysis view
view = feat.analyze_project()
check("2 analysis view opened", isinstance(view, FirmwareAnalysisView))
check("2 analysis finished", wait(lambda: view.ready, 60))
check("2 notice bar shown once (fresh settings)", view.notice.isVisible() or view.notice.isVisibleTo(view))
pump(0.5)
qh.shot(view, "fwfmt_01_overview")
check("2 CPU: ARM Cortex-M first", view.cpu_table.item(0, 0).data(Qt.ItemDataRole.UserRole) == "arm-thumb",
      view.cpu_table.item(0, 0).text())
check("2 base 0x08000000", view.base_address() == 0x08000000, hex(view.base_address()))
check("2 base table filled", view.base_table.rowCount() >= 1 and view.base_table.item(0, 0).text() == "0x08000000")
view.tabs.setCurrentIndex(1)
pump(0.3)
check("2 entropy graph has data", len(view.graph.profile) > 10 and set(view.graph.kinds) >= {"code", "empty"},
      set(view.graph.kinds))
qh.shot(view, "fwfmt_02_entropy")
check("2 region table", view.region_table.rowCount() >= 3)
view.tabs.setCurrentIndex(2)
view.str_ids.setChecked(True)
pump(0.2)
texts = [view.str_table.item(r, 3).text() for r in range(view.str_table.rowCount())]
check("2 strings: identification-like filter", "X 123 456 78 90" in texts and "SW 1234567890" in texts, texts[:10])
qh.shot(view, "fwfmt_03_strings")
view.str_ids.setChecked(False)
view.tabs.setCurrentIndex(3)
pump(0.2)
lst = view.listing.toPlainText()
check("2 disassembly listing at the reset handler", "push" in lst and "reset_handler:" in lst, lst[:400])
check("2 reference index built", wait(lambda: view.xrefs is not None, 60))
im = make_image("arm-thumb", seed=3)
tab = next(t for t in im.tables if t.address in im.xrefs)
hits = view.find_xrefs(tab.address)
check("2 references to a calibration table", {s for s, _k in hits} >= set(im.xrefs[tab.address]),
      ([hex(s) for s, _ in hits], [hex(x) for x in im.xrefs[tab.address]]))
view.xref_addr.setText(f"0x{tab.address:X}")
view.find_xrefs_from_ui()
check("2 references listed in the UI", view.xref_list.count() >= 1)
qh.shot(view, "fwfmt_04_disassembly")
first = view.xref_list.item(0).data(Qt.ItemDataRole.UserRole)
view.show_disassembly(first)
check("2 follow a reference", view.dis_addr.text() == f"0x{first:X}")
view.tabs.setCurrentIndex(5)
pump(0.2)
check("2 memory map table", view.seg_table.rowCount() >= 1 and view.seg_table.item(0, 0).text() == "0x08000000")
doc = feat.show_hex(view, tab.address)
check("2 Show in hex: hex editor opens read-only at the address", doc is not None and getattr(doc, "read_only", False))
for b in view.notice.findChildren(type(view.btn_hex)):
    b.click()
check("2 notice accepted -> hidden", not view.notice.isVisible())
try:
    from radide.firmware.project import notice
    check("2 notice acceptance shared with the ECU tools", notice.accepted())
except ImportError:
    pass

# ---------------------------------------------------------------- 3 containers
tri = make_image("tricore")
mm = MemoryMap.from_bytes(tri.bytes(), tri.base)
srec_path = save(mm, WORK / "tricore_image.s37")
v2 = feat.open_analysis(srec_path)
check("3 S-record opens", wait(lambda: v2.ready, 60))
check("3 S-record: TriCore at 0x80000000", v2.current_arch() == "tricore" and v2.base_address() == 0x80000000,
      (v2.current_arch(), hex(v2.base_address())))
th = make_image("arm-thumb", seed=8)
emm = MemoryMap.from_bytes(th.bytes(), th.base, ".text")
emm.segments[0].flags = "rx"
emm.symbols = [Symbol("reset_handler", th.entry | 1, 16, "func"), Symbol("map0", th.tables[2].address, 32, "object")]
elf_path = WORK / "thumb_image.elf"
elf_path.write_bytes(elf.dumps(emm, machine=40))
v3 = feat.open_analysis(elf_path)
check("3 ELF opens", wait(lambda: v3.ready, 60))
check("3 ELF: Thumb, symbols in the memory map tab", v3.current_arch() == "arm-thumb" and
      v3.sym_table.rowCount() >= 3, (v3.current_arch(), v3.sym_table.rowCount()))
qh.shot(v3, "fwfmt_05_elf")

# ---------------------------------------------------------------- 4 converter
dlg = feat.converter(str(srec_path))
p = dlg.convert(str(srec_path), str(WORK / "conv.hex"), "ihex")
check("4 converter: S-record -> Intel HEX", load(p) == load(srec_path))
parts = dlg.split(str(fp.original_path), "deint")
check("4 converter: even / odd split", len(parts) == 2 and parts[0].stat().st_size * 2 == fp.original_path.stat().st_size)
mp = dlg.merge([f"{parts[0]} @ 0x0", f"{parts[1]} @ 0x100000"], str(WORK / "merged.s19"))
check("4 converter: merge at addresses", len(load(mp).segments) == 2)
qh.shot(dlg, "fwfmt_06_converter")
dlg.close()

# ---------------------------------------------------------------- 5 build + Ghidra
cmd = get_plugin("firmware-analysis").build_command(folder)
r = subprocess.run(cmd, shell=True, cwd=str(folder), capture_output=True, text=True, timeout=300)
check("5 Build: verify + build/analysis.txt", r.returncode == 0 and (folder / "build" / "analysis.txt").is_file(),
      r.stdout[-300:] + r.stderr[-300:])
w._fill_solution()
pump(0.3)
check("5 report node in Solution Explorer", any(it.text(0) == "Report: build/analysis.txt" for it in tree_items()))
from radide.firmware.analysis import ghidra  # noqa: E402
ok, info = ghidra.available()
if ok and os.environ.get("RADIDE_TEST_SKIP_GHIDRA") != "1":
    view.tabs.setCurrentIndex(4)
    view.run_ghidra()
    check("5 Ghidra run finished", wait(lambda: view.ghidra_result is not None or
                                        (view._gjob is None and view.btn_ghidra.isEnabled()), 600))
    check("5 Ghidra: functions + read-only C", view.gfuncs.count() > 10 and view.gcode.isReadOnly() and
          "Decompiled by Ghidra" in view.gcode.toPlainText(), view.ghidra_status.text())
    qh.shot(view, "fwfmt_07_ghidra")
else:
    print("SKIP Ghidra:", info)

# ---------------------------------------------------------------- 6 Arabic
from radide import i18n  # noqa: E402
i18n.set_language(qh.app, "ar")
pump(0.5)
check("6 Arabic: tabs translated, code sees English",
      view.tabs.tabText(1) == "Entropy" and i18n.tr("Entropy") != "Entropy" and
      i18n.shown(view.btn_ghidra) == i18n.tr("Analyze in Ghidra") != "Analyze in Ghidra",
      i18n.shown(view.btn_ghidra))
qh.shot(view, "fwfmt_08_arabic")
NEW = ["Firmware / ECU Analysis", "Firmware Analysis (Synthetic ARM Image)", "Firmware Analysis", "Set Original...",
       "Analyze", "Verify Original", "Make Working Copy", "Open Notes", "Open Labels", "Analyze Firmware File...",
       "Firmware Converter (HEX / S-record / ELF / split / merge)...", "Create Synthetic Test Firmware...",
       "Overview", "Entropy", "Strings", "Disassembly", "Memory Map", "Re-analyze", "Open in Hex Editor",
       "Save Report...", "Analyze in Ghidra", "References to", "Identification-like only", "Show in Hex",
       "I understand", "CPU (guess)", "Load address (guess)", "Firmware Converter", "Convert", "Split / Swap",
       "Merge", "Analyze Firmware", "Entry points:", "Auto-detect"]
from radide.firmware.analysis.view import NOTICE  # noqa: E402
NEW.append(NOTICE)
missing = [s for s in NEW if i18n.tr(s) == s]
check("6 Arabic catalog has the new strings", not missing, missing)
i18n.set_language(qh.app, "en")
qh.finish(w)
