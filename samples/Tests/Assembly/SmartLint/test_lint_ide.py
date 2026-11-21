"""The smart assembly editor in the real IDE (qh.py harness: offscreen, QSettings "RADIDE-TEST", cleared afterwards).

Opens the NasmMistakes and Emu8086Mistakes projects with the IDE in Arabic and checks: squiggles (Monaco markers
of owner radAsmLint) with Arabic messages, gutter icons, the hover explanation (why / how to fix), Ctrl+. code
actions and applying a quick fix, the Problems Explained panel (Fix button, Learn more), the Error List rows,
the merge with an assembler message on the same line, and the English texts after switching back.

Run:  python samples/Tests/Assembly/SmartLint/test_lint_ide.py      (screenshots: %TEMP%/radide-qa/shots)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "SmartLint")
os.environ["RADIDE_NO_BROWSER"] = "1"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

ARABIC = re.compile(r"[؀-ۿ]")
WORK = Path(qh.WORK) / "smart_lint"
shutil.rmtree(WORK, ignore_errors=True)
for name in ("NasmMistakes", "Emu8086Mistakes"):
    shutil.copytree(HERE / name, WORK / name)

w = qh.window()
from PyQt6.QtWidgets import QTreeWidgetItem  # noqa: E402

from radide import i18n  # noqa: E402
from radide import tools  # noqa: E402
from radide.features import asm_smart_lint as L  # noqa: E402


def js(ed, code, timeout=8.0):
    box = []
    ed.page().runJavaScript(code, box.append)
    wait(lambda: box, timeout)
    return box[0] if box else None


def markers(ed):
    raw = js(ed, "JSON.stringify(monaco.editor.getModelMarkers({owner: 'radAsmLint'}).map(m => "
                 "[m.startLineNumber, m.code, m.message, m.severity]))")
    try:
        return json.loads(raw or "[]")
    except ValueError:
        return []


def line_of(ed, text):
    return next(i for i, x in enumerate(ed.text().split("\n")) if text in x)


i18n.set_language(qh.app, "ar")
pump(0.5)

# ---------------------------------------------------------------- 1. open the NASM project
w.open_project(WORK / "NasmMistakes", ask=False)
pump(2)
ed = w.open_any_file(WORK / "NasmMistakes" / "main.asm")
check("main.asm opened in Monaco", ed is not None and hasattr(ed, "page"), repr(ed))
wait(lambda: getattr(ed, "_ready", False), 40)
check("assembly editor gets the analyzer", L.is_lint_editor(ed), repr(getattr(ed, "plugin", None)))
check("analyzer script installed in the page", wait(lambda: js(ed, "!!window.__radAsmLint"), 20))
wait(lambda: len(markers(ed)) >= 5, 20)
mk = markers(ed)
codes = {m[1] for m in mk}
check("squiggles for the mistakes (ASM101 ASM102 ASM403 ASM402 ASM307 ASM301)",
      {"ASM101", "ASM102", "ASM403", "ASM402", "ASM307", "ASM301"} <= codes, sorted(codes))
l101 = line_of(ed, "mov eax, bl")
m101 = next((m for m in mk if m[1] == "ASM101"), None)
check("ASM101 squiggle on the right line", m101 is not None and m101[0] == l101 + 1, (m101, l101))
check("marker message is Arabic", m101 is not None and ARABIC.search(m101[2] or ""), m101)
check("ASM101 is an error marker (severity 8)", m101 is not None and m101[3] == 8, m101)
glyphs = js(ed, "editor_glyphs = radEditor.getModel().getAllDecorations().filter(d => "
                "(d.options.glyphMarginClassName || '').indexOf('rad-lint-') >= 0).length")
check("gutter icons for the problem lines", (glyphs or 0) >= 5, glyphs)
shot(ed, "smartlint_nasm_ar")

# ---------------------------------------------------------------- 2. hover explanation
hov = js(ed, f"JSON.stringify(radAsmLintHover({l101}, 9))")
hov = json.loads(hov or "[]")
check("hover on the squiggle explains it in Arabic (why / how to fix)",
      hov and "لماذا" in hov[0] and "كيف أصلحه" in hov[0] and "ASM101" in hov[0], hov[:1])
check("hover keeps the English message for searching", hov and "Operand sizes do not match" in hov[0], hov[:1])
check("hover links Learn more", hov and "اعرف المزيد" in hov[0], hov[:1])
js(ed, f"radEditor.setPosition({{lineNumber: {l101 + 1}, column: 10}}); radEditor.focus(); "
       "radEditor.trigger('test', 'editor.action.showHover', {}); 1")
ui_hover = wait(lambda: "لماذا" in (js(ed, "(document.querySelector('.monaco-hover') || {}).innerText || ''") or ""),
                8)
check("Monaco hover widget shows the explanation", ui_hover,
      (js(ed, "(document.querySelector('.monaco-hover') || {}).innerText || ''") or "")[:200])
shot(ed, "smartlint_hover_ar")
js(ed, "radEditor.setPosition({lineNumber: 1, column: 1}); 1")

# ---------------------------------------------------------------- 3. Ctrl+. code actions
acts = json.loads(js(ed, f"JSON.stringify(radAsmLintActions({l101}))") or "[]")
check("code actions for ASM101: movzx / movsx / AL + Explain", any("movzx" in a for a in acts) and
      any("movsx" in a for a in acts) and any("ASM101" in a for a in acts), acts)
check("code action titles are Arabic", all(ARABIC.search(a) for a in acts), acts)
js(ed, f"radEditor.setPosition({{lineNumber: {l101 + 1}, column: 6}}); radEditor.focus(); "
       "radEditor.trigger('test', 'editor.action.quickFix', {}); 1")
qf = wait(lambda: "movzx" in (js(ed, "(document.querySelector('.action-widget') || {}).innerText || ''") or ""), 8)
check("Ctrl+. light-bulb menu lists the quick fixes", qf,
      (js(ed, "(document.querySelector('.action-widget') || {}).innerText || ''") or "")[:200])
shot(ed, "smartlint_quickfix_ar")
js(ed, "radEditor.trigger('test', 'hideCodeActionWidget', {}); radEditor.focus(); 1")
pump(0.3)
check("apply the first quick fix", js(ed, f"radAsmLintApplyFix({l101}, 0)") is True)
check("the line became movzx eax, bl", wait(lambda: "movzx eax, bl" in ed.text().split("\n")[l101], 5),
      ed.text().split("\n")[l101])
check("ASM101 squiggle disappears after the fix", wait(lambda: "ASM101" not in {m[1] for m in markers(ed)}, 10),
      [m[1] for m in markers(ed)])

# ---------------------------------------------------------------- 4. Problems Explained panel
panel = w.show_asm_problems()
pump(0.5)
check("Problems Explained dock is shown", w._asm_lint_dock.isVisible())
check("panel lists the file's problems", panel.list.count() >= 4, panel.list.count())
rows = [panel.list.item(i).text() for i in range(panel.list.count())]
check("panel rows are Arabic", any(ARABIC.search(r) for r in rows), rows[:3])
i102 = next((k for k, it in enumerate(panel.issues) if it.rule == "ASM102"), -1)
panel.list.setCurrentRow(i102)
pump(0.2)
body = panel.text.toPlainText()
check("panel explains why and how to fix (Arabic)", "لماذا" in body and "كيف أصلحه" in body, body[:200])
check("panel adds the instruction reference (asm_intel)", "MOV" in body and "Intel SDM" in body, body[-300:])
check("Fix button enabled for ASM102", panel.b_fix.isEnabled())
check("Open Lesson enabled (course lesson 04)", panel.b_lesson.isEnabled() and panel.issues[i102].lesson() == "04-data")
shot(w._asm_lint_dock, "smartlint_panel_ar")
l102 = panel.issues[i102].line
panel.fix()
check("Fix writes the size keyword", wait(lambda: "dword [count]" in ed.text().split("\n")[l102], 5),
      ed.text().split("\n")[l102])
check("ASM102 gone after the panel fix", wait(lambda: "ASM102" not in {m[1] for m in markers(ed)}, 10),
      [m[1] for m in markers(ed)])
panel.learn()
check("Learn more shows the instruction reference", "MOV" in panel.text.toPlainText(), panel.text.toPlainText()[:150])

# ---------------------------------------------------------------- 5. Error List + assembler message merge
diags = tools.run_checks(w)
pump(0.5)
el = w.error_list
lint_rows = [el.topLevelItem(i) for i in range(el.topLevelItemCount())
             if re.match(r"ASM\d{3}: ", el.topLevelItem(i).text(1))]
check("Error List gets the analyzer rows", len(lint_rows) >= 3, [r.text(1)[:60] for r in lint_rows])
check("Error List rows are Arabic", any(ARABIC.search(r.text(1)) for r in lint_rows))
l403 = line_of(ed, "div ecx") + 1
fake = QTreeWidgetItem(["Error", "main.asm:12: error: invalid combination of opcode and operands", "main.asm",
                        str(line_of(ed, "[count], 4") + 1)])
el.addTopLevelItem(fake)
pump(0.3)
check("assembler message explained in Arabic (friendly text first)", ARABIC.search(fake.text(1) or "") and
      "invalid combination" in fake.text(1), fake.text(1))
check("assembler message gets an explanation tool tip", "invalid combination" in fake.toolTip(1) and
      len(fake.toolTip(1)) > 60, fake.toolTip(1)[:120])
dup = QTreeWidgetItem(["Error", "ASM403: duplicate test row", "main.asm", str(l403)])
asm_same_line = QTreeWidgetItem(["Error", "main.asm:x: error: something", "main.asm", str(l403)])
el.addTopLevelItem(dup)
el.addTopLevelItem(asm_same_line)
pump(0.3)
texts = [el.topLevelItem(i).text(1) for i in range(el.topLevelItemCount())]
check("analyzer row on the same line as an assembler error is merged away", "ASM403: duplicate test row" not in texts)

# ---------------------------------------------------------------- 6. emu8086 project
w.open_project(WORK / "Emu8086Mistakes", ask=False)
pump(2)
ed2 = w.open_any_file(WORK / "Emu8086Mistakes" / "main.asm")
wait(lambda: getattr(ed2, "_ready", False), 40)
wait(lambda: len(markers(ed2)) >= 4, 20)
codes2 = {m[1] for m in markers(ed2)}
check("emu8086: DS not set, missing $, CX clobbered, [ax], missing exit",
      {"ASM601", "ASM605", "ASM402", "ASM106", "ASM602"} <= codes2, sorted(codes2))
acts2 = json.loads(js(ed2, f"JSON.stringify(radAsmLintActions({line_of(ed2, 'int 21h')}))") or "[]")
check("emu8086 quick fixes: insert mov ax, @data / add '$'", any("@data" in a for a in acts2) and
      any("$" in a for a in acts2), acts2)
shot(ed2, "smartlint_emu8086_ar")

# ---------------------------------------------------------------- 7. English
i18n.set_language(qh.app, "en")
pump(0.3)
js(ed, "radAsmLintRun(); 1")
check("messages switch to English", wait(lambda: any("does not set the flags" in (m[2] or "") for m in markers(ed)),
                                         10), [m[2] for m in markers(ed)][:3])
hov_en = json.loads(js(ed, f"JSON.stringify(radAsmLintHover({line_of(ed, 'jz .done')}, 5))") or "[]")
check("English hover: Why? / How to fix", hov_en and "**Why?**" in hov_en[0] and "How to fix" in hov_en[0],
      hov_en[:1])
shot(ed, "smartlint_nasm_en")
qh.finish(w)
