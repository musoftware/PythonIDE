"""IDE test of the .NET tools (samples/Tests/QA/Integration/qh.py harness, QSettings "RADIDE-TEST", widget.grab only).

Copies samples/Tests/DotNet/ToolsSolution to a temp folder, opens ToolsSolution.sln and checks: Test Explorer
(project > namespace > class grouping, Run All with live + TRX results, Run Failed, Debug a test with a breakpoint
through netcoredbg), Dependencies > Analyzers (rules + severities, Set severity -> .editorconfig, generators and
Show Generated Files), the Analyze menu, Run Code Analysis -> Error List -> Configure severity / Suppress, Code
Cleanup on a document, Remove and Sort Usings, the light bulb (using / add reference) and Go To Decompiled
Definition (read-only tab), the dotnet CLI submenu of the Project menu.

    python samples/Tests/DotNet/ToolsTests/ui_test.py
"""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
os.environ.setdefault("QA_NAME", "dotnet-tools")
import qh  # noqa: E402
from qh import check, finish, pump, shot, wait  # noqa: E402

work = Path(qh.WORK) / "dotnet-tools"
if work.exists():
    shutil.rmtree(work, ignore_errors=True)
shutil.copytree(HERE.parent / "ToolsSolution", work / "ToolsSolution",
                ignore=shutil.ignore_patterns("bin", "obj", "TestResults"))
sol = work / "ToolsSolution"
sln_file = sol / "ToolsSolution.sln"

from PyQt6.QtCore import Qt  # noqa: E402

from radide.dotnet.tools import editorconfig as EC  # noqa: E402
from radide.dotnet.tools import sdk  # noqa: E402
from radide.dotnet.tools import ui as DUI  # noqa: E402
from radide.features import solution_ui  # noqa: E402

code, out = sdk.run([sdk.dotnet(), "build", str(sln_file), "-nologo", "-v:q"], cwd=sol, timeout=900)
check("sample builds", code == 0, out[-600:])

ROLE = Qt.ItemDataRole.UserRole
w = qh.window()
from radide.foreign import vs_ui  # noqa: E402

vs_ui.open_in_window(w, sln_file)
pump(2)
check("solution opened", w.sln is not None and Path(w.sln.file) == sln_file.resolve(), w.sln)


def find(kind, name_part=""):
    stack = [w.solution.topLevelItem(i) for i in range(w.solution.topLevelItemCount())]
    while stack:
        it = stack.pop(0)
        d = it.data(0, ROLE) or ("", "")
        if d[0] == kind and name_part.lower() in str(d[1] if len(d) > 1 else "").lower():
            return it
        stack.extend(it.child(i) for i in range(it.childCount()))
    return None


def menu_texts(m):
    out = []
    for a in m.actions():
        out.append(a.text().replace("&", ""))
        if a.menu() is not None:
            out += [a.text().replace("&", "") + ">" + b.text().replace("&", "") for b in a.menu().actions()]
    return out


# ---------------------------------------------------------------- Analyze menu
check("Analyze menu between Test and Tools", [a.text().replace("&", "") for a in w.menuBar().actions()].index(
    "Analyze") == [a.text().replace("&", "") for a in w.menuBar().actions()].index("Test") + 1,
    [a.text() for a in w.menuBar().actions()])
check("Analyze menu items", {"Run Code Analysis>On Solution", "Code Cleanup>Run Code Cleanup on Document",
                             "Remove and Sort Usings", "Go To Decompiled Definition",
                             "Configure Code Analysis (.editorconfig)..."} <= set(menu_texts(w.analyze_menu)),
      menu_texts(w.analyze_menu))

# ---------------------------------------------------------------- Solution Explorer: Analyzers
calc = next(p for p in w.sln.all_projects() if p.name == "Calc")
xt = next(p for p in w.sln.all_projects() if p.name == "Calc.XTests")
an = find("dn_analyzers", "Calc.XTests.csproj")
check("Dependencies > Analyzers node", an is not None and an.parent().text(0) == "Dependencies")
an.setExpanded(True)
check("analyzers load on expand", wait(lambda: find("dn_analyzers", "Calc.XTests.csproj").childCount() > 3 and
                                       find("dn_analyzers", "Calc.XTests.csproj").child(0).text(0) != "Loading...",
                                       120))
an = find("dn_analyzers", "Calc.XTests.csproj")
names = [an.child(i).text(0) for i in range(an.childCount())]
check("analyzer assemblies listed", "xunit.analyzers" in names and "Microsoft.CodeAnalysis.NetAnalyzers" in names,
      names)
rule = find("dn_rule", "CA1822|")
check("rule node with effective severity from .editorconfig", rule is not None and "warning" in rule.toolTip(0) and
      rule.text(0).startswith("CA1822:"), rule.toolTip(0) if rule else None)
m = vs_ui.project_menu(w, xt, rule, "dn_rule", rule.data(0, ROLE)[1])
check("rule context menu: Set severity / View Help", {"Set severity>Error", "Set severity>None", "View Help"} <=
      set(menu_texts(m)), menu_texts(m))
DUI.set_rule_severity(w, xt, "CA1822", "error")
check("Set severity writes .editorconfig", EC.rule_severities(sol / "x.cs").get("CA1822") == "error",
      (sol / ".editorconfig").read_text())
rule = find("dn_rule", "CA1822|")
check("rule node refreshed with the new severity", rule is not None and "Effective severity: error" in rule.toolTip(0),
      (rule.toolTip(0), rule.parent().parent().data(0, ROLE)) if rule else None)
an.setExpanded(True)
w.solution.scrollToItem(an)
shot(w.solution, "dotnet_tools_analyzers")
DUI.set_rule_severity(w, xt, "CA1822", "warning")

# generators of Calc: Show Generated Files
an_c = find("dn_analyzers", "Calc.csproj")
an_c.setExpanded(True)
wait(lambda: find("dn_generator", "RegexGenerator") is not None, 120)
gen = find("dn_generator", "RegexGenerator")
check("source generator node", gen is not None)
DUI.show_generated_files(w, calc)
check("Show Generated Files lists RegexGenerator.g.cs", wait(lambda: find("dn_genfile", "RegexGenerator.g.cs")
                                                             is not None, 300))
gf = find("dn_genfile", "RegexGenerator.g.cs")
if gf is not None:
    vs_ui.activate(w, calc, gf, "dn_genfile", gf.data(0, ROLE)[1])
    pump(1.5)
    ed = DUI._current_editor(w)
    check("generated file opens read-only", ed is not None and getattr(ed, "isReadOnly", lambda: True)(),
          getattr(ed, "path", None))

# ---------------------------------------------------------------- Test Explorer
te = w.test_explorer
w.dock_tests.show()
te.discover(force=True)
check("Test Explorer discovers the solution's tests", wait(lambda: len(te.items) >= 8 and not te.discovering, 180),
      (len(te.items), te.summary.text(), te.log.toPlainText()[-500:]))
tops = [te.tree.topLevelItem(i).text(0) for i in range(te.tree.topLevelItemCount())]
check("grouped by project (top level)", any(t.startswith("Calc.XTests") for t in tops) and
      any(t.startswith("Calc.NTests") for t in tops), tops)
te.run(None)
check("Run All finishes", wait(lambda: getattr(te, "finished_run", False) and not te.running(), 600))
st = {it.name: it.state for it in te.items.values()}
check("results: passed + the intentional failure", st.get("Add_IntentionalFailure") == "failed" and
      st.get("Divide_Exact") == "passed" and st.get("Divide_ByZero_Throws") == "passed", st)
fail_key = next(k for k, it in te.items.items() if it.name == "Add_IntentionalFailure")
te.tree.setCurrentItem(te.nodes[fail_key])
te._show_detail()
links = DUI.stack_links(te.detail.toPlainText())
check("failure detail with stack-trace link", links and links[0][2].endswith("CalculatorTests.cs") and
      links[0][3] == 25, te.detail.toPlainText()[:400])
check("stack-trace link underlined", len(te.detail.extraSelections()) >= 1)
shot(w.dock_tests, "dotnet_tools_test_explorer")
te.finished_run = False
te.run_failed()
check("Run Failed runs only the failed test", wait(lambda: getattr(te, "finished_run", False) and not te.running(),
                                                     300) and "--filter" in te.log.toPlainText())

# Debug a test with a breakpoint in Calculator.Add
from radide.bridgedebug import find_netcoredbg  # noqa: E402
if find_netcoredbg():
    calc_cs = sol / "Calc" / "Calculator.cs"
    w.activate_project(calc)
    w.open_module("Calculator.cs")
    pump(2)
    ed = w.modviews["Calculator.cs"].editor
    try:
        ed.set_breakpoints([4]) if hasattr(ed, "set_breakpoints") else ed.toggle_breakpoint(4)
    except Exception as e:  # noqa: BLE001
        print("breakpoint:", e)
    pump(0.5)
    add_key = next(k for k, it in te.items.items() if it.name == "Add_TwoNumbers_ReturnsSum")
    te.tree.clearSelection()
    te.nodes[add_key].setSelected(True)
    stops = []
    orig_stopped = w._on_stopped

    def on_stop(info):
        stops.append(info)
        orig_stopped(info)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: w.session.cont())
    w._on_stopped = on_stop
    check("Debug is enabled for a .NET test", te._can_debug())
    te.debug_selected()
    check("debug run finishes with the TRX result", wait(lambda: getattr(te, "debug_finished", False), 300) and
          te.items[add_key].state == "passed", (te.items[add_key].state, w.output.toPlainText()[-600:]))
    check("breakpoint hit in Calculator.cs while debugging the test",
          any(str(getattr(i, "file", "")).lower().endswith("calculator.cs") for i in stops),
          [(getattr(i, "file", ""), getattr(i, "line", 0)) for i in stops])
    w._on_stopped = orig_stopped
else:
    check("debug test (netcoredbg missing - skipped)", True)

# ---------------------------------------------------------------- Code Cleanup + usings + light bulb
w.activate_project(calc)
w.open_module("Messy.cs")
pump(2)
ed = w.modviews["Messy.cs"].editor
w.tabs.setCurrentWidget(w.modviews["Messy.cs"])
done = []
DUI.remove_and_sort_usings(w, ed, then=lambda new, removed, err: done.append((new, removed, err)))
check("Remove and Sort Usings in the editor", wait(lambda: bool(done), 180) and len(done[0][1]) == 4 and
      "using System" not in ed.text(), done[:1])
w.save_all()
pump(0.5)
res = []
DUI.code_cleanup(w, "document", "whitespace", then=lambda code, changed: res.append((code, changed)))
check("Code Cleanup on the document reformats the open editor", wait(lambda: bool(res), 300) and res[0][0] == 0 and
      "    public int Twice(int a)" in ed.text(), (res, ed.text()[:300]))

# light bulb in CalculatorTests.cs: StringBuilder -> using System.Text;
w.activate_project(xt)
w.open_module("CalculatorTests.cs")
pump(2)
ted = w.modviews["CalculatorTests.cs"].editor
from radide import editkit  # noqa: E402
txt = ted.text().replace("var c = new Calculator();", "var c = new Calculator(); var sb = new StringBuilder();")
editkit.apply_text(ted, txt)
ln = next(i for i, s in enumerate(ted.text().split("\n")) if "StringBuilder" in s)
col = ted.text().split("\n")[ln].index("StringBuilder") + 2
acts = DUI.quick_action_provider(w, ted, ln, col)
check("light bulb offers 'using System.Text;'", acts and acts[0][0] == "using System.Text;", [a[0] for a in acts])
if acts:
    acts[0][1]()
    pump(0.5)
check("using inserted", "using System.Text;" in ted.text().split("namespace")[0], ted.text()[:200])
from radide.features import refactor  # noqa: E402
w._refactor_no_exec = True
ln = next(i for i, s in enumerate(ted.text().split("\n")) if "new StringBuilder" in s)
col = ted.text().split("\n")[ln].index("StringBuilder") + 2
w._refactor_menu = None
refactor.quick_actions(w, ted, ln, col)
wait(lambda: getattr(w, "_refactor_menu", None) is not None, 60)
menu = getattr(w, "_refactor_menu", None)
check("quick actions menu (Ctrl+.) built with RAD IDE's entries", menu is not None and any(
    "Rename" in a.text() for a in menu.actions()), [a.text() for a in menu.actions()] if menu else None)

# Go To Decompiled Definition on StringBuilder
ted.setCursorPosition(ln, col) if hasattr(ted, "setCursorPosition") else None
pump(0.3)
opened = []
DUI.goto_decompiled_definition(w, ted, then=lambda f: opened.append(f))
check("decompiled StringBuilder opens read-only", wait(lambda: bool(opened), 300) and opened[0] is not None and
      "StringBuilder" in Path(opened[0]).name, opened)
if opened and opened[0]:
    ded = DUI._current_editor(w)
    check("decompiled tab is read-only and shows the class", ded is not None and "class StringBuilder" in ded.text()
          and getattr(ded, "isReadOnly", lambda: True)())
    shot(w, "dotnet_tools_decompiled")

# ---------------------------------------------------------------- Run Code Analysis -> Error List
diags = []
DUI.run_code_analysis(w, "solution", then=lambda d: diags.extend(d))
check("Run Code Analysis -> CA1822 in the Error List", wait(lambda: bool(diags), 600) and any(
    "CA1822" in w.error_list.topLevelItem(i).text(1) for i in range(w.error_list.topLevelItemCount())),
    [w.error_list.topLevelItem(i).text(1) for i in range(min(5, w.error_list.topLevelItemCount()))])
row_item = next((w.error_list.topLevelItem(i) for i in range(w.error_list.topLevelItemCount())
                 if "CA1822" in w.error_list.topLevelItem(i).text(1)), None)
if row_item is not None:
    pos = w.error_list.visualItemRect(row_item).center()
    em = DUI.error_list_menu(w, pos)
    check("Error List menu: Configure severity / Suppress / Show Error Help",
          {"Configure severity>Error", "Configure severity>None", "Suppress>In Source", "Show Error Help"} <=
          set(menu_texts(em)), menu_texts(em))
    row = DUI._error_row(w, row_item)
    DUI.configure_severity(w, row, "suggestion")
    check("Configure severity -> .editorconfig", EC.rule_severities(sol / "Calc" / "x.cs").get("CA1822") ==
          "suggestion")
    ok = DUI.suppress_in_source(w, row)
    f = Path(row["file"])
    check("Suppress in Source adds #pragma warning disable/restore", ok and "#pragma warning disable CA1822" in
          (editkit.find_editor(w, f).text() if editkit.find_editor(w, f) else f.read_text()))
    shot(w.dock_errors, "dotnet_tools_error_list")

# ---------------------------------------------------------------- Configure Code Analysis dialog
dlg = DUI.configure_code_analysis(w, calc, exec_=False)
check("Configure Code Analysis: rules listed", wait(lambda: dlg.rules.topLevelItemCount() > 100, 120),
      dlg.rules_note.text())
dlg.search.setText("CA1050")
vis = [dlg.rules.topLevelItem(i) for i in range(dlg.rules.topLevelItemCount())
       if not dlg.rules.topLevelItem(i).isHidden()]
check("rule search filters", len(vis) == 1 and vis[0].text(0) == "CA1050", [v.text(0) for v in vis])
vis[0].setSelected(True)
dlg.sev_combo.setCurrentIndex(dlg.sev_combo.findData("error"))
dlg._set_selected()
dlg.combos[("[*]", "trim_trailing_whitespace")].setCurrentIndex(
    dlg.combos[("[*]", "trim_trailing_whitespace")].findData("true"))
dlg.resize(900, 600)
dlg.show()
pump(0.5)
shot(dlg, "dotnet_tools_editorconfig")
dlg.accept()
txt = (sol / ".editorconfig").read_text()
check("dialog writes severities and whitespace", "dotnet_diagnostic.CA1050.severity = error" in txt and
      "trim_trailing_whitespace = true" in txt, txt)

# ---------------------------------------------------------------- dotnet CLI in the Project menu
from radide.project_actions import ActionContext  # noqa: E402
from radide.project_actions_providers.dotnet import VisualStudio  # noqa: E402
ctx = ActionContext(w, calc)
acts = VisualStudio().actions(ctx)
cli = next((a for a in acts if getattr(a, "title", "") == "dotnet CLI"), None)
check("Project menu has the dotnet CLI submenu", cli is not None and len(cli.items) > 10,
      [getattr(a, "title", "-") for a in acts])

# Solution Explorer project menu: Analyze and Code Cleanup
pi = find("project", "Calc")
m = solution_ui.build_menu(w, pi)
check("project context menu: Analyze and Code Cleanup", m is not None and
      any(t.startswith("Analyze and Code Cleanup>Run Code Analysis") for t in menu_texts(m)),
      menu_texts(m) if m else None)

finish(w)
