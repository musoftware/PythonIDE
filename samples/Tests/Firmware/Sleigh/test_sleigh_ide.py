"""Built-in SLEIGH disassembly in the IDE (qh.py harness: QSettings org RADIDE-TEST, offscreen, RADIDE_NO_BROWSER,
screenshots only through widget.grab()). Synthetic firmware only.

    python samples/Tests/Firmware/Sleigh/test_sleigh_ide.py

  1  Firmware Analysis view, Disassembly tab for 8051, V850, C166 and PowerPC VLE: decoder label (SLEIGH),
     prologue + call labels in the listing, reference index finds every calibration-table reference, follow a
     call by double-click data, Show P-code adds p-code lines.
  2  ECU workbench Disassembly tab (CPU combo -> C166 / 8051 / V850): instructions, no "use Ghidra" line.
  3  Arabic: the new strings are translated.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "fw_sleigh")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, wait  # noqa: E402

WORK = Path(qh.WORK) / "fw_sleigh"
WORK.mkdir(parents=True, exist_ok=True)

w = qh.window()
feat = getattr(w, "firmware_analysis", None)
fe = getattr(w, "firmware_ide", None)
check("firmware analysis + workbench features installed", feat is not None and fe is not None)

from radide.firmware.analysis import sleigh  # noqa: E402
from radide.firmware.analysis.synth import make_image  # noqa: E402

if not sleigh.available():
    print("SKIP: pypcode is not installed")
    qh.finish(w)
    sys.exit(0)

FIRST = {"8051": "push", "v850": "add", "c166": "push", "ppc-vle": "e_stwu"}
CALL = {"8051": "lcall", "v850": "jarl", "c166": "calla", "ppc-vle": "e_bl"}

# ---------------------------------------------------------------- 1 analysis view
for arch in ("8051", "v850", "c166", "ppc-vle"):
    im = make_image(arch, seed=3)
    p = WORK / f"synth_{arch}.bin"
    p.write_bytes(im.bytes())
    view = feat.open_analysis(p, base=im.base, arch=arch)
    check(f"1 {arch}: view opened", view is not None)
    if view is None:
        continue
    check(f"1 {arch}: analysis finished", wait(lambda: view.ready, 60))
    if hasattr(view, "accept_notice"):
        try:
            view.accept_notice()
        except Exception:  # noqa: BLE001
            pass
    view.tabs.setCurrentIndex(3)
    f = im.functions[4]
    lines = view.show_disassembly(f)
    pump(0.3)
    lst = view.listing.toPlainText()
    check(f"1 {arch}: decoder label says SLEIGH", "SLEIGH" in view.dis_backend.text(), view.dis_backend.text())
    check(f"1 {arch}: listing starts with '{FIRST[arch]}' and has calls with labels",
          lines and lines[0].mnemonic == FIRST[arch] and CALL[arch] in lst and "sub_" in lst, lst[:300])
    check(f"1 {arch}: reference index built", wait(lambda: view.xrefs is not None, 120))
    # the view indexes the entropy "code" regions (+ entry points), so the first / last functions of the synthetic
    # image can fall outside; the exact-range check is in test_sleigh_core.py
    pairs = [(t, s) for t, srcs in im.xrefs.items() for s in srcs]
    found = {t: {s for s, _k in view.find_xrefs(t)} for t in im.xrefs}
    hit = sum(1 for t, s in pairs if s in found[t])
    check(f"1 {arch}: calibration-table references found in the view ({hit}/{len(pairs)}), every table referenced",
          hit >= 0.8 * len(pairs) and all(found[t] & set(im.xrefs[t]) for t in im.xrefs), f"{hit}/{len(pairs)}")
    tab = max((t for t in im.tables if t.address in im.xrefs), key=lambda t: len(found[t.address]))
    view.xref_addr.setText(f"0x{tab.address:X}")
    view.find_xrefs_from_ui()
    check(f"1 {arch}: references listed in the UI", view.xref_list.count() >= 1 and
          view.xref_list.count() == len(view.xrefs.to(tab.address)))
    view.show_disassembly(im.xrefs[tab.address][0])
    qh.shot(view, f"fwsleigh_{arch}_disassembly")
    call = next((ln for ln in view.show_disassembly(f) if ln.call and ln.target is not None), None)
    if call is not None:
        view.show_disassembly(call.target)
        check(f"1 {arch}: follow a call", view.dis_addr.text() == f"0x{call.target:X}")
    view.show_disassembly(f)
    check(f"1 {arch}: Show P-code enabled", view.dis_pcode.isEnabled())
    view.dis_pcode.setChecked(True)
    pump(0.2)
    pl = view.listing.toPlainText()
    check(f"1 {arch}: p-code lines under the instructions", pl.count("| ") > 5 and len(pl) > len(lst) // 2, pl[:300])
    qh.shot(view, f"fwsleigh_{arch}_pcode")
    view.dis_pcode.setChecked(False)

# ---------------------------------------------------------------- 2 workbench
for arch in ("c166", "8051", "v850"):
    im = make_image(arch, seed=5)
    p = WORK / f"wb_{arch}.ori"
    p.write_bytes(im.bytes())
    wb = fe.open_workbench(p)
    check(f"2 {arch}: workbench opened", wb is not None)
    if wb is None:
        continue
    pump(0.5)
    if hasattr(wb, "accept_notice"):
        wb.accept_notice()
    i = wb.arch.findData(arch)
    wb.arch.setCurrentIndex(i)
    wb.base_edit.setText(f"0x{im.base:X}")
    n = wb.disassemble(im.functions[2] - im.base)
    pump(0.3)
    txt = wb.dis_text.toPlainText()
    check(f"2 {arch}: workbench Disassembly tab lists instructions", i >= 0 and n > 20 and FIRST[arch] in txt and
          "Ghidra" not in txt, txt[:300])
    check(f"2 {arch}: note names the SLEIGH decoder", "SLEIGH" in wb.dis_note.text(), wb.dis_note.text())
    qh.shot(wb, f"fwsleigh_wb_{arch}")

# ---------------------------------------------------------------- 3 Arabic
from radide import i18n  # noqa: E402
NEW = ["Show P-code", "Ghidra's intermediate language under every instruction (SLEIGH CPUs)"]
missing = [s for s in NEW if i18n.tr(s) == s]
i18n.set_language(qh.app, "ar")
pump(0.5)
check("3 Arabic catalog has the new strings", not missing or all(i18n.tr(s) != s for s in NEW), missing)
i18n.set_language(qh.app, "en")
qh.finish(w)
