"""Coverage: the Debug menu (functional, offscreen IDE, sandbox copy of the Python Tk sample, real debugpy session).

* Debug > Toggle Breakpoint (F9) on the caret line of Form1.py: the editor and the window's breakpoint table get the
  line, F9 again removes it; the breakpoints are saved per project (QSettings key breakpoints/<folder>).
* Debug > Breakpoint Condition (Alt+F9): the condition typed in the input box is stored for that line and is
  passed with the breakpoint to the debugger (win._all_breakpoints); on a line without a breakpoint it also sets one.
* Debug > Breakpoint Settings (Condition, Hit Count, Log): the dialog opens pre-filled with the stored condition;
  OK stores condition + hit count + logpoint (debug_extras.encode_bp), the dialog shows them again, and clearing
  hit count / log stores the plain condition.
* Debug > Run to Cursor (Ctrl+F10): starts debugpy and pauses on the caret line (current line, Call Stack top frame
  Form1_Load ... line 14); the temporary breakpoint is removed afterwards.
* Debug > Step Over (F10) / Step Into (F11): the current line moves to the next line / into cov_double().
* Debug > Continue (F5): the conditional breakpoint whose condition is false (a == 999) is passed over, the one
  whose condition is true (c == 60) stops - the conditions really reach debugpy.
* Debug > Windows > Call Stack / Threads (Ctrl+Alt+H): the docks toggle; Threads lists MainThread while paused.
* Debug > Attach to Process (Ctrl+Alt+P) while debugging: "Stop the program being debugged first".
* Debug > Stop Debugging (Shift+F5): the session ends ("Debugging stopped"), the program process is gone.
* Debug > Attach to Process with no session: the dialog lists the running processes (a python child started by
  this test, found by the PID filter); Cancel attaches nothing.

The debuggee is a real Tk program (a window may appear for a few seconds); it is stopped by the test.
Run:  .venv\\Scripts\\python samples\\Tests\\Coverage\\Debug\\test_debug_menu.py
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cov_harness import (action, check, finish, on_modal, open_sample, output_text, pump, start, trigger,  # noqa: E402
                         wait)

FORM1 = '''from Form1_designer import Form1Designer, EventArgs  # noqa: F401
import Helpers


def cov_double(x):
    y = x * 2
    return y


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        a = 20
        b = cov_double(a)
        c = a + b
        print('cov-load', c)

    def Button1_MouseMove(self, e):
        print('move', e.X, e.Y)

    def Button1_Click(self):
        pass

    def TextBox1_KeyPress(self, e):
        print('key', e.KeyChar)

    def Form1_FormClosing(self, e):
        print('closing'); e.Cancel = False

    def Form1_Resize(self):
        pass

    def NumericUpDown1_ValueChanged(self):
        print('num', self.NumericUpDown1_var.get())

    def TrackBar1_ValueChanged(self):
        pass

    def Label1_DoubleClick(self):
        pass


if __name__ == "__main__":
    Form1().show()
'''
# 1-based lines of FORM1
L_Y, L_RET, L_A, L_B, L_C, L_PRINT = 6, 7, 14, 15, 16, 17

w = start("debug_menu")
proj = open_sample(w, "python-tk")
check("Python Tk sample opened", w.project is not None and w.project.language == "python-tk")

from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox  # noqa: E402

from radide import debug_extras as dx  # noqa: E402

(proj / "Form1.py").write_text(FORM1, encoding="utf-8")
w.open_code("Form1")
pump(0.5)
cv = w.codeviews.get("Form1")
ed = cv.editor if cv is not None else None
check("Form1.py is open in a code editor", ed is not None)
ed.setText(FORM1)
pump(0.5)
cf = w.plugin_for_form("Form1").code_file("Form1")          # "Form1.py"


def caret(line1: int):
    if w._current_code() is not cv:
        w.open_code("Form1")
    ed.setCursorPosition(line1 - 1, 0)
    w._update_actions()
    pump(0.1)


# ------------------------------------------------------------------ Toggle Breakpoint (F9)
a_bp = action(w, "Debug", "Toggle Breakpoint")
check("Debug > Toggle Breakpoint exists with F9", a_bp is not None and a_bp.shortcut().toString() == "F9",
      a_bp and a_bp.shortcut().toString())
caret(L_C)
check("Toggle Breakpoint is enabled in a Python code editor", a_bp.isEnabled())
trigger(a_bp, 0.2)
check("F9 sets a breakpoint on the caret line (editor)", (L_C - 1) in ed.breakpoints(), ed.breakpoints())
check("F9: the window's breakpoint table has the line", (L_C - 1) in w.breakpoints.get(cf, set()), w.breakpoints)
trigger(a_bp, 0.2)
check("F9 again removes the breakpoint", (L_C - 1) not in ed.breakpoints()
      and (L_C - 1) not in w.breakpoints.get(cf, set()), (ed.breakpoints(), w.breakpoints))
trigger(a_bp, 0.2)
check("F9 a third time sets it again", (L_C - 1) in ed.breakpoints())

# ------------------------------------------------------------------ Breakpoint Condition (Alt+F9)
cond_seen = []


def answer_condition(text):
    def h(dlg):
        if not isinstance(dlg, QInputDialog) or dlg.windowTitle() != "Breakpoint Condition":
            return False
        cond_seen.append((dlg.labelText(), dlg.textValue()))
        dlg.setTextValue(text)
        dlg.accept()
        return True
    return h


a_cond = action(w, "Debug", "Breakpoint Condition")
check("Debug > Breakpoint Condition exists with Alt+F9",
      a_cond is not None and a_cond.shortcut().toString() == "Alt+F9", a_cond and a_cond.shortcut().toString())
from cov_harness import clear_modal_handlers  # noqa: E402
on_modal(answer_condition("a > 5"))
caret(L_C)
trigger(a_cond, 0.5)
check("Breakpoint Condition asks for the line's condition", cond_seen and f"line {L_C}" in cond_seen[0][0], cond_seen)
check("the condition is stored for the line", w.bp_conditions.get((cf, L_C - 1)) == "a > 5", w.bp_conditions)
check("the condition goes with the breakpoint to the debugger",
      (cf, L_C, "a > 5") in w._all_breakpoints(), w._all_breakpoints())

# ------------------------------------------------------------------ Breakpoint Settings (Condition, Hit Count, Log)
bps_seen = []


def bp_settings(set_to):
    def h(dlg):
        if type(dlg).__name__ != "BreakpointDialog":
            return False
        bps_seen.append({"title": dlg.windowTitle(), "cond": dlg.cond.text(), "hit_kind": dlg.hit_kind.currentIndex(),
                         "hit_n": dlg.hit_n.value(), "log_on": dlg.log_on.isChecked(), "log": dlg.log.text()})
        cond, kind, n, log = set_to
        dlg.cond.setText(cond)
        dlg.hit_kind.setCurrentIndex(kind)
        dlg.hit_n.setValue(n)
        dlg.log_on.setChecked(bool(log))
        dlg.log.setText(log)
        dlg.accept()
        return True
    return h


clear_modal_handlers()
on_modal(bp_settings(("a == 999", 2, 3, "c is {c}")))
a_set = action(w, "Debug", "Breakpoint Settings (Condition, Hit Count, Log)")
check("Debug > Breakpoint Settings exists", a_set is not None)
caret(L_C)
trigger(a_set, 0.5)
check("Breakpoint Settings opens for the caret line, pre-filled with the stored condition",
      bps_seen and bps_seen[0]["title"].endswith(f"line {L_C}") and bps_seen[0]["cond"] == "a > 5", bps_seen)
d = dx.parse_bp(w.bp_conditions.get((cf, L_C - 1), ""))
check("OK stores condition + hit count (multiple of 3) + log message",
      d == {"cond": "a == 999", "hit": "%3", "log": "c is {c}"}, d)
check("the status bar describes the breakpoint", "every 3 hits" in w.statusBar().currentMessage(),
      w.statusBar().currentMessage())

clear_modal_handlers()
on_modal(bp_settings(("a == 999", 0, 1, "")))
trigger(a_set, 0.5)
check("the dialog shows the stored hit count and log message again",
      len(bps_seen) == 2 and bps_seen[1]["cond"] == "a == 999" and bps_seen[1]["hit_kind"] == 2
      and bps_seen[1]["hit_n"] == 3 and bps_seen[1]["log_on"] and bps_seen[1]["log"] == "c is {c}", bps_seen[1:])
check("clearing hit count and log stores the plain condition",
      w.bp_conditions.get((cf, L_C - 1)) == "a == 999", w.bp_conditions)

# Alt+F9 on a line without a breakpoint: sets breakpoint + condition
clear_modal_handlers()
cond_seen.clear()
on_modal(answer_condition("c == 60"))
caret(L_PRINT)
trigger(a_cond, 0.5)
check("Breakpoint Condition on a line without a breakpoint sets one", (L_PRINT - 1) in ed.breakpoints(),
      ed.breakpoints())
check("... with the condition", w.bp_conditions.get((cf, L_PRINT - 1)) == "c == 60", w.bp_conditions)
clear_modal_handlers()

# saved per project
w._save_breakpoints()
raw = str(w.settings.value(w._bp_key(), "") or "")
check("breakpoints are saved for the project (QSettings)",
      f"{cf}:{L_C - 1}" in raw and f"{cf}:{L_PRINT - 1}" in raw, raw)

# ------------------------------------------------------------------ Run to Cursor (Ctrl+F10)
a_rtc = action(w, "Debug", "Run to Cursor")
check("Debug > Run to Cursor exists with Ctrl+F10", a_rtc is not None and a_rtc.shortcut().toString() == "Ctrl+F10",
      a_rtc and a_rtc.shortcut().toString())
caret(L_A)
trigger(a_rtc, 1.0)
check("Run to Cursor starts a debug session", w.session is not None)
s = w.session
check("the session is debugpy (DAP)", type(s).__name__ == "DapSession", type(s).__name__)


def paused_at(line1):
    return (w.session is not None and w.session.paused and w.stopped_at is not None
            and w.stopped_at[1] == line1 - 1)


ok = wait(lambda: paused_at(L_A), 150)
check(f"Run to Cursor pauses on the caret line {L_A}", ok,
      (w.stopped_at and w.stopped_at[1] + 1, output_text(w)[-1500:]))
frames = [w.callstack.item(i).text() for i in range(w.callstack.count())]
check("Call Stack top frame is Form1_Load at the cursor line",
      frames and frames[0].startswith("Form1_Load()") and f"Form1.py: line {L_A}" in frames[0], frames[:3])
check("the temporary Run to Cursor breakpoint is gone afterwards", w._run_to is None
      and (L_A - 1) not in w.breakpoints.get(cf, set()), (w._run_to, w.breakpoints))
check("the window title shows [break]", "[break]" in w.windowTitle(), w.windowTitle())

# ------------------------------------------------------------------ Debug > Windows: Call Stack / Threads
a_stack = action(w, "Debug", "Windows", "Call Stack")
a_thr = action(w, "Debug", "Windows", "Threads")
check("Debug > Windows > Call Stack exists", a_stack is not None)
check("Debug > Windows > Threads exists with Ctrl+Alt+H",
      a_thr is not None and a_thr.shortcut().toString() == "Ctrl+Alt+H", a_thr and a_thr.shortcut().toString())
was = not w.dock_stack.isHidden()
trigger(a_stack, 0.2)
flipped = (not w.dock_stack.isHidden()) != was
if w.dock_stack.isHidden():
    trigger(a_stack, 0.2)
check("Call Stack toggles its dock", flipped and not w.dock_stack.isHidden(), was)
if not w.dock_threads.isHidden():                  # hidden at install; shown only by a saved layout
    trigger(a_thr, 0.2)
trigger(a_thr, 0.3)
check("Debug > Windows > Threads shows the Threads dock", not w.dock_threads.isHidden())
tt = w.threads_tree


def thread_names():
    return [tt.topLevelItem(i).text(2) for i in range(tt.topLevelItemCount())]


check("Threads lists MainThread while paused", wait(lambda: "MainThread" in thread_names(), 20), thread_names())
cur = [tt.topLevelItem(i) for i in range(tt.topLevelItemCount()) if tt.topLevelItem(i).text(0) == "→"]
check("the current thread is marked (MainThread)", cur and cur[0].text(2) == "MainThread",
      [(i.text(0), i.text(2)) for i in cur])

# ------------------------------------------------------------------ Step Over (F10) / Step Into (F11)
a_over = action(w, "Debug", "Step Over")
a_into = action(w, "Debug", "Step Into")
check("Step Over (F10) / Step Into (F11) exist",
      a_over is not None and a_over.shortcut().toString() == "F10"
      and a_into is not None and a_into.shortcut().toString() == "F11")
check("Step Over / Step Into are enabled while paused", a_over.isEnabled() and a_into.isEnabled())
trigger(a_over, 0.2)
check(f"Step Over moves to line {L_B}", wait(lambda: paused_at(L_B), 40), w.stopped_at and w.stopped_at[1] + 1)
trigger(a_into, 0.2)
ok = wait(lambda: paused_at(L_Y) or paused_at(L_Y - 1), 40)
frames = [w.callstack.item(i).text() for i in range(w.callstack.count())]
check("Step Into goes into cov_double()", ok and frames and frames[0].startswith("cov_double()"),
      (w.stopped_at and w.stopped_at[1] + 1, frames[:3]))
check("the Call Stack has cov_double over Form1_Load",
      len(frames) >= 2 and frames[1].startswith("Form1_Load()") and f"line {L_B}" in frames[1], frames[:3])
line_now = w.stopped_at[1] + 1 if w.stopped_at else 0
trigger(a_over, 0.2)
check("Step Over inside cov_double moves one line down",
      wait(lambda: paused_at(line_now + 1), 40), w.stopped_at and w.stopped_at[1] + 1)

# ------------------------------------------------------------------ conditions reach debugpy (Continue)
a_cont = w.a_run                                   # Start / Continue (F5)
check("Start Debugging / Continue is enabled while paused", a_cont.isEnabled())
trigger(a_cont, 0.2)
ok = wait(lambda: paused_at(L_PRINT) or paused_at(L_C), 40)
check(f"Continue passes the false condition (line {L_C}: a == 999) and stops at the true one "
      f"(line {L_PRINT}: c == 60)", ok and paused_at(L_PRINT), w.stopped_at and w.stopped_at[1] + 1)

# ------------------------------------------------------------------ Attach to Process while debugging
msgs = []


def note_box(dlg):
    if isinstance(dlg, QMessageBox) and dlg.windowTitle() == "Attach to Process":
        msgs.append(dlg.text())
        dlg.accept()
        return True
    return False


on_modal(note_box)
a_att = action(w, "Debug", "Attach to Process")
check("Debug > Attach to Process exists with Ctrl+Alt+P",
      a_att is not None and a_att.shortcut().toString() == "Ctrl+Alt+P", a_att and a_att.shortcut().toString())
trigger(a_att, 0.5)
check("Attach to Process while debugging says to stop first", msgs and "Stop the program" in msgs[0], msgs)
check("... and keeps the debug session", w.session is s)
clear_modal_handlers()

# ------------------------------------------------------------------ Stop Debugging (Shift+F5)
a_stop = action(w, "Debug", "Stop Debugging")
check("Debug > Stop Debugging exists with Shift+F5", a_stop is not None and a_stop.shortcut().toString() == "Shift+F5")
trigger(a_stop, 0.5)
check("Stop Debugging ends the session", wait(lambda: w.session is None, 30))
check("Output says 'Debugging stopped'", "Debugging stopped" in output_text(w), output_text(w)[-500:])
check("the debugged program is no longer running", wait(lambda: not s.running(), 15))
check("Step Over is disabled again", not a_over.isEnabled())
check("no current-line marker is left", w.stopped_at is None)

# ------------------------------------------------------------------ Attach to Process (dialog, Cancel)
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
att = []


def cancel_attach(dlg):
    if type(dlg).__name__ != "AttachDialog":
        return False
    pids = [dlg.tree.topLevelItem(i).text(1) for i in range(dlg.tree.topLevelItemCount())]
    dlg.filter.setText(str(child.pid))
    rows = [(dlg.tree.topLevelItem(i).text(0), dlg.tree.topLevelItem(i).text(1), dlg.tree.topLevelItem(i).text(2))
            for i in range(dlg.tree.topLevelItemCount())]
    att.append({"title": dlg.windowTitle(), "n": len(pids), "has_child": str(child.pid) in pids, "rows": rows})
    dlg.reject()
    return True


on_modal(cancel_attach)
try:
    pump(1.0)
    w.output.clear()
    trigger(a_att, 0.8)
finally:
    child.kill()
    child.wait(10)
check("Attach to Process opens its dialog", att and att[0]["title"] == "Attach to Process", att)
check("the dialog lists the running processes", att and att[0]["n"] > 5, att and att[0]["n"])
check("the python process started by the test is listed", att and att[0]["has_child"], att)
check("the PID filter leaves just that process (kind python)",
      att and len(att[0]["rows"]) == 1 and att[0]["rows"][0][1] == str(child.pid) and att[0]["rows"][0][2] == "python",
      att and att[0]["rows"])
check("Cancel attaches nothing", w.session is None and "Attach:" not in output_text(w), output_text(w)[-300:])
clear_modal_handlers()
check("no modal dialog left open", QApplication.activeModalWidget() is None)
finish(w)
