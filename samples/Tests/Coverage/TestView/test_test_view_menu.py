"""Coverage: the Test menu and View > Terminal / Layout / AI Chat / Agent Manager (functional, offscreen IDE).

* Test > Test Explorer (Ctrl+E, T): the dock opens and discovers the sandbox project's unittest tests (3 tests in
  test_cov_a.py / test_cov_b.py, written by this test).
* Test > Run Tests in Current File (Ctrl+R, T) with test_cov_a.py in the editor: only its 2 tests run - Test
  Explorer shows 1 passed / 1 failed, test_cov_b.py's test stays "not run"; the failure message is kept.
* Test > Run All Tests (Ctrl+R, A): all 3 run - 2 passed / 1 failed; the Output window gets "[tests] ..." summary.
* View > Terminal (Ctrl+`): the Terminal dock opens with a shell in the project folder; "echo cov-ok" typed in
  it (Enter) prints cov-ok.
* View > AI Chat (Ctrl+Alt+I) and View > Agent Manager (Ctrl+Alt+M) in the Visual Studio layout: their docks open
  (no prompt is ever sent - no network).
* View > Layout > Toggle Panel (Ctrl+J) / Toggle Side Bar (Ctrl+B) in the VS Code layout: the bottom panel and the
  side bar hide and show again; AI Chat / Agent Manager become the active side bar view there.

Run:  .venv\\Scripts\\python samples\\Tests\\Coverage\\TestView\\test_test_view_menu.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cov_harness import action, check, finish, open_sample, output_text, pump, start, trigger, wait  # noqa: E402

TEST_A = '''import unittest


class CovA(unittest.TestCase):
    def test_cov_pass(self):
        self.assertEqual(1 + 1, 2)

    def test_cov_fail(self):
        self.assertEqual(1 + 1, 3)


if __name__ == "__main__":
    unittest.main()
'''
TEST_B = '''import unittest


class CovB(unittest.TestCase):
    def test_cov_b_ok(self):
        self.assertTrue(True)
'''

w = start("test_view_menu")
proj = open_sample(w, "python-tk")
check("Python Tk sample opened", w.project is not None)
(proj / "test_cov_a.py").write_text(TEST_A, encoding="utf-8")
(proj / "test_cov_b.py").write_text(TEST_B, encoding="utf-8")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

panel = w.test_explorer


def states():
    return {it.name: it.state for it in panel.items.values()}


# ------------------------------------------------------------------ Test Explorer
a_te = action(w, "Test", "Test Explorer")
check("Test > Test Explorer exists with Ctrl+E, T", a_te is not None and a_te.shortcut().toString() == "Ctrl+E, T",
      a_te and a_te.shortcut().toString())
trigger(a_te, 0.5)
check("the Test Explorer dock opens", not w.dock_tests.isHidden())
ok = wait(lambda: not panel.discovering and len(panel.items) == 3, 120)
check("Test Explorer discovers the 3 tests of the project", ok, (states(), panel.summary.text()))

# ------------------------------------------------------------------ Run Tests in Current File
ed = w.open_any_file(proj / "test_cov_a.py")
pump(0.8)
from radide.features.formatting import _current_editor  # noqa: E402
cur = _current_editor(w)
check("test_cov_a.py is the current editor",
      cur is not None and Path(getattr(cur, "path", "")).name == "test_cov_a.py", cur and getattr(cur, "path", None))
a_cf = action(w, "Test", "Run Tests in Current File")
check("Test > Run Tests in Current File exists with Ctrl+R, T",
      a_cf is not None and a_cf.shortcut().toString() == "Ctrl+R, T", a_cf and a_cf.shortcut().toString())
panel.finished_run = False
trigger(a_cf, 0.3)
ok = wait(lambda: getattr(panel, "finished_run", False) and not panel.running(), 180)
check("the current file's tests ran", ok, (states(), panel.log.toPlainText()[-800:]))
c = getattr(panel, "counts", {})
check("Test Explorer: 1 passed / 1 failed", c.get("passed") == 1 and c.get("failed") == 1, (c, states()))
st = states()
check("test_cov_pass passed, test_cov_fail failed", st.get("test_cov_pass") == "passed"
      and st.get("test_cov_fail") == "failed", st)
check("the other file's test was not run", st.get("test_cov_b_ok") == "unknown" and c.get("unknown") == 1, st)
check("the summary line shows the counts", "1 passed" in panel.summary.text() and "1 failed" in panel.summary.text(),
      panel.summary.text())
fail_it = next((it for it in panel.items.values() if it.name == "test_cov_fail"), None)
check("the failed test keeps its assertion message", fail_it is not None and "3" in (fail_it.message or ""),
      fail_it and fail_it.message)

# ------------------------------------------------------------------ Run All Tests
a_all = action(w, "Test", "Run All Tests")
check("Test > Run All Tests exists with Ctrl+R, A",
      a_all is not None and a_all.shortcut().toString() == "Ctrl+R, A", a_all and a_all.shortcut().toString())
w.output.clear()
panel.finished_run = False
trigger(a_all, 0.3)
ok = wait(lambda: getattr(panel, "finished_run", False) and not panel.running(), 180)
check("Run All Tests finished", ok, (states(), panel.log.toPlainText()[-800:]))
c = getattr(panel, "counts", {})
check("Run All: 2 passed / 1 failed, none left unrun",
      c.get("passed") == 2 and c.get("failed") == 1 and c.get("unknown") == 0, (c, states()))
check("Output window gets the test summary", "[tests] Tests: 2 passed, 1 failed" in output_text(w),
      output_text(w)[-400:])

# ------------------------------------------------------------------ View > Terminal
a_term = action(w, "View", "Terminal")
check("View > Terminal exists with Ctrl+`", a_term is not None and a_term.shortcut().toString() == "Ctrl+`",
      a_term and a_term.shortcut().toString())
trigger(a_term, 0.5)
t = w.terminal
check("the Terminal dock opens", not w.dock_terminal.isHidden())
check("a shell runs in the terminal", wait(t.running, 20))
check("the shell starts in the project folder", Path(t.cwd).resolve() == proj.resolve(), t.cwd)
pump(1.5)
t.input.setText("echo cov-ok")
QTest.keyClick(t.input, Qt.Key.Key_Return)


def term_lines():
    return [ln.strip() for ln in t.out.toPlainText().splitlines()]


check("'echo cov-ok' prints cov-ok in the terminal", wait(lambda: "cov-ok" in term_lines(), 30),
      t.out.toPlainText()[-600:])
check("the command went to the history", "echo cov-ok" in t.input.history, t.input.history[-3:])

# ------------------------------------------------------------------ AI Chat / Agent Manager (Visual Studio layout)
from radide.features import workbench  # noqa: E402
wb = workbench.get(w)
check("the IDE starts in the Visual Studio layout", wb is not None and wb.mode == "vs", wb and wb.mode)
a_chat = action(w, "View", "AI Chat")
check("View > AI Chat exists with Ctrl+Alt+I", a_chat is not None and a_chat.shortcut().toString() == "Ctrl+Alt+I",
      a_chat and a_chat.shortcut().toString())
w.dock_ai_chat.hide()
trigger(a_chat, 0.5)
check("AI Chat opens its dock", not w.dock_ai_chat.isHidden())
a_ag = action(w, "View", "Agent Manager")
check("View > Agent Manager exists with Ctrl+Alt+M", a_ag is not None and a_ag.shortcut().toString() == "Ctrl+Alt+M",
      a_ag and a_ag.shortcut().toString())
w.dock_agents.hide()
trigger(a_ag, 0.5)
check("Agent Manager opens its dock", not w.dock_agents.isHidden())

# ------------------------------------------------------------------ View > Layout (VS Code layout)
a_panel = action(w, "View", "Layout", "Toggle Panel")
a_side = action(w, "View", "Layout", "Toggle Side Bar")
check("View > Layout > Toggle Panel exists with Ctrl+J", a_panel is not None and a_panel.shortcut().toString() == "Ctrl+J",
      a_panel and a_panel.shortcut().toString())
check("View > Layout > Toggle Side Bar exists with Ctrl+B",
      a_side is not None and a_side.shortcut().toString() == "Ctrl+B", a_side and a_side.shortcut().toString())
wb.set_mode("vscode")
pump(1.5)
check("the VS Code layout is active", wb.mode == "vscode", wb.mode)

p0 = wb.panel_visible()
trigger(a_panel, 0.5)
p1 = wb.panel_visible()
trigger(a_panel, 0.5)
p2 = wb.panel_visible()
check("Toggle Panel flips the bottom panel", p1 != p0, (p0, p1))
check("Toggle Panel again flips it back", p2 == p0, (p0, p1, p2))
if not wb.panel_visible():                     # the effect in both directions, starting from a shown panel
    trigger(a_panel, 0.5)
check("Toggle Panel hides every panel dock (Output, Terminal ...)",
      trigger(a_panel, 0.5) and all(d.isHidden() for d in wb.panel_docks()),
      [(d.objectName(), d.isHidden()) for d in wb.panel_docks()])
trigger(a_panel, 0.5)
check("... and shows the panel again", wb.panel_visible())

s0 = wb.side_visible()
trigger(a_side, 0.5)
s1 = wb.side_visible()
trigger(a_side, 0.5)
s2 = wb.side_visible()
check("Toggle Side Bar flips the side bar", s1 != s0, (s0, s1))
check("Toggle Side Bar again flips it back", s2 == s0, (s0, s1, s2))

trigger(a_chat, 0.8)
check("AI Chat in the VS Code layout: the chat is the active side bar view",
      wb._active.get("vscode") == "chat" and wb.side_visible() and not w.dock_ai_chat.isHidden(),
      (wb._active.get("vscode"), wb.side_visible()))
trigger(a_ag, 0.8)
check("Agent Manager in the VS Code layout: the agents view is active",
      wb._active.get("vscode") == "agents" and not w.dock_agents.isHidden(), wb._active.get("vscode"))
wb.set_mode("vs")
pump(1.0)
check("back to the Visual Studio layout", wb.mode == "vs")
check("no modal dialog left open", QApplication.activeModalWidget() is None)
finish(w)
