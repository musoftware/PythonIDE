"""Check family "debug": F5 with a breakpoint in Button1_Click, for languages whose debugger the IDE supports.

The debugger is driven like a user does: the program's window gets a REAL click (Win32 messages to the program's
own window, checks/common.py click_button), the IDE's own windows are read back (Locals, Call Stack, Watch,
Immediate) and the session's commands are the menu commands (F10 / F11 / Shift+F11 / F5 / Shift+F5).

  start       F5 (run_project(debug=True)) starts the program; its window "Form1" appears (Win32, own process)
  breakpoint  Button1 is clicked and the IDE pauses in the handler (a click lost / only session.simulate = FAIL)
  locals      the Locals window shows the handler's local variable with its value 42
  callstack   the Call Stack window shows the handler on top
  immediate   the Immediate window evaluates the local variable (42)
  watch       a Watch expression (the local variable) shows 42
  step_over   Step Over pauses again on a later line
  step_into   Step Into pauses again (inside a called function or on the next line)
  step_out    Step Out leaves the handler (pauses in the caller, or the handler finishes and the program runs)
  continue    Continue resumes and the handler finishes (title "Hi QA")
  condition   a breakpoint condition: false (var == 41) -> the click does not stop; true (var == 42) -> it stops
  hitcount    hit count "2": the first click does not stop, the second does
  stop        Stop (Shift+F5) ends the program and the session
  exception   a run with an error thrown in the handler (Break on Exceptions on, no breakpoint) pauses at it
"""
from __future__ import annotations

import os
import time
import traceback

from . import common as C

# the handler's local variable (checks/common.py LOCAL) and its value
VAR = {"vb-basic": "qaN", "python-tk": "qa_n", "python-qt": "qa_n", "ring-qt": "qaN", "c-bridge": "qa_n",
       "cpp-bridge": "qa_n", "csharp-bridge": "qaN", "powershell-bridge": "$qaN", "java-bridge": "qaN",
       "javascript": "qaN", "typescript": "qaN", "php": "$qaN", "rust-bridge": "_qa_n", "go-bridge": "qaN",
       "fortran-bridge": "qa_n", "lua-bridge": "qaN", "ruby-bridge": "qa_n", "perl-bridge": "$qaN",
       "dart-bridge": "qaN"}
# breakpoint condition "var equals N" in the language's syntax
EQ = {"vb-basic": "{v} = {n}", "powershell-bridge": "{v} -eq {n}", "ring-qt": "{v} = {n}"}
# a statement that throws (or crashes) in the handler, inserted before the breakpoint line
THROW = {"vb-basic": "Err.Raise 5", "python-tk": "raise ValueError('qa')", "python-qt": "raise ValueError('qa')",
         "ring-qt": 'raise("qa")', "c-bridge": "qa_n = qa_n / (qa_n - 42);",
         "cpp-bridge": "qa_n = qa_n / (qa_n - 42);", "csharp-bridge": 'if (qaN == 42) throw new System.Exception("qa");',
         "powershell-bridge": 'throw "qa"', "java-bridge": 'if (qaN == 42) throw new RuntimeException("qa");',
         "javascript": 'if (qaN === 42) throw new Error("qa");', "typescript": 'if (qaN === 42) throw new Error("qa");',
         "rust-bridge": 'if _qa_n == 42 { panic!("qa"); }', "go-bridge": 'if qaN == 42 { panic("qa") }',
         "fortran-bridge": "qa_n = qa_n / (qa_n - 42)", "lua-bridge": 'error("qa")', "ruby-bridge": 'raise "qa"',
         "perl-bridge": 'die "qa";', "dart-bridge": "if (qaN == 42) throw Exception('qa');"}
# one more statement after the Click body (so Step Over / Step Into have a next line in the handler)
EXTRA = {"vb-basic": "qaN = qaN + 1", "python-tk": "qa_n = qa_n + 1", "python-qt": "qa_n = qa_n + 1",
         "ring-qt": "qaN = qaN + 1", "c-bridge": "qa_n = qa_n + 1;", "cpp-bridge": "qa_n = qa_n + 1;",
         "csharp-bridge": "qaN = qaN + 1;", "powershell-bridge": "$qaN = $qaN + 1", "java-bridge": "qaN = qaN + 1;",
         "javascript": "qaN = qaN + 1;", "typescript": "qaN = qaN + 1;", "php": "$qaN = $qaN + 1;",
         "rust-bridge": "let _qa_m = _qa_n + 1;", "go-bridge": "qaN = qaN + 1", "fortran-bridge": "qa_n = qa_n + 1",
         "lua-bridge": "qaN = qaN + 1", "ruby-bridge": "qa_n = qa_n + 1", "perl-bridge": "$qaN = $qaN + 1;",
         "dart-bridge": "qaN = qaN + 1;"}
# the breakpoint goes on this CLICK line (C: line 0 is a declaration without code - the debugger would move it)
BP_INDEX = {"c-bridge": 1}
SLOW = ("rust-bridge", "java-bridge", "csharp-bridge", "dart-bridge", "go-bridge", "cpp-bridge", "fortran-bridge",
        "typescript", "c-bridge")


def _program_window(timeout, h):
    """The window 'Form1' of a process started by this test process (the debuggee / bridge host)."""
    def find():
        mine = set()
        if C.psutil is not None:
            try:
                mine = {p.pid for p in C.psutil.Process(os.getpid()).children(recursive=True)}
            except C.psutil.Error:
                pass
        for hw in C.top_windows(mine):
            if C.get_text(hw) in ("Form1", C.EXPECTED_TITLE):
                return hw
        return None
    end = time.time() + timeout
    while time.time() < end:
        h.pump(0.3)
        hw = find()
        if hw:
            return hw
        if h.w.session is None:          # the program / session ended
            return None
    return None


def _cond(pid, n):
    return EQ.get(pid, "{v} == {n}").format(v=VAR.get(pid, ""), n=n)


class _Run:
    """One F5 run: the session's StopInfo objects are recorded."""

    def __init__(self, h):
        self.h, self.w = h, h.w
        self.stops = []
        self.form = None

    def start(self, slow):
        w = self.w
        # the debuggee inherits the IDE's environment: without this a Qt program (Python Qt, RingQt) would
        # inherit QT_QPA_PLATFORM=offscreen and never show a real window
        saved_env = C.program_env_begin()
        try:
            w.run_project(debug=True)
        finally:
            C.program_env_end(saved_env)
        if w.session is not None:
            w.session.stopped.connect(lambda info: self.stops.append(info))
        self.form = _program_window(slow, self.h)
        return self.form

    def paused(self):
        return self.w.session is not None and bool(self.w.session.paused)

    def click(self, wait=30.0, retries=2):
        """Real click on Button1; True when the IDE paused."""
        C.click_button_ext(self.form)
        hit = self.h.wait(self.paused, wait)
        for _ in range(retries):     # like gui_test: a click can be lost while the program starts up
            if hit:
                break
            C.click_button_ext(self.form)
            hit = self.h.wait(self.paused, wait * 0.6)
        return hit

    def resume_and_wait(self, cmd, timeout=40.0):
        """cmd() then wait until the IDE pauses again (True) or not."""
        n = len(self.stops)
        cmd()
        return self.h.wait(lambda: len(self.stops) > n and self.paused(), timeout)


def _var_value(w, var) -> str:
    want = var.lstrip("$").lower()
    for i in range(w.locals.topLevelItemCount()):
        it = w.locals.topLevelItem(i)
        if it.text(0).lstrip("$").lower().split(".")[-1] == want:
            return it.text(1)
    return ""


def run(h, r, pl, project, folder) -> None:
    sub = r.sub
    k = "debug."
    w = h.w
    if not pl.supports_debug:
        sub[k + "start"] = "SKIP: the IDE has no debugger for this language"
        return
    if not getattr(w.project, "forms", None) or pl.id not in C.CLICK:
        sub[k + "start"] = "SKIP: no form in this template"
        return
    var = VAR.get(pl.id, "")
    slow = 300 if pl.id in SLOW else 120
    ed = None
    original_text = None
    try:
        from .ide import editor_for_form
        ed, hline, handler = editor_for_form(h)
        lines = ed.text().split("\n")
        first = C.CLICK[pl.id][BP_INDEX.get(pl.id, 0)].strip()[:20]
        bp = next((i for i in range(hline + 1, min(len(lines), hline + 12)) if first in lines[i]), -1)
        if bp < 0:
            sub[k + "start"] = f"FAIL: handler body not found ({handler})"
            return
        original_text = ed.text()
        if pl.id in EXTRA:
            after = bp - BP_INDEX.get(pl.id, 0) + len(C.CLICK[pl.id])
            indent = lines[bp][:len(lines[bp]) - len(lines[bp].lstrip())]
            lines.insert(after, indent + EXTRA[pl.id])
            ed.setText("\n".join(lines))
            h.pump(1.0)
        print("    [debug] ed.set_breakpoints([bp])", time.strftime("%X"), flush=True)
        ed.set_breakpoints([bp])
        w._sync_breakpoints()
        code_file = w.plugin_for_form("Form1").code_file("Form1")
        print("    [debug] w.run_project(debug=True)", time.strftime("%X"), flush=True)
        run1 = _Run(h)
        form = run1.start(slow)
        if not form:
            out = w.output.toPlainText()[-600:] if hasattr(w, "output") else ""
            sub[k + "start"] = f"FAIL: no program window within {slow}s; Output: {out}"
            return
        sub[k + "start"] = "PASS - program window shown under the debugger"
        h.pump(1.5)
        print("    [debug] click", time.strftime("%X"), flush=True)
        hit = run1.click()
        how = "real click on the program's window"
        if not hit:
            covered = C.ensure_uncovered(form, form, 10, 10)
            if callable(getattr(w.session, "simulate", None)):
                # the debugger's own event injection (radide/bridgedebug.py simulate): tells a click problem
                # from a debugger problem
                w.session.simulate("Button1", "Click")
                hit = h.wait(run1.paused, 40)
                how = ("only with session.simulate (the real click did not stop)" if "stays covered" not in covered
                       else "with session.simulate (another program's window covers the screen: no real click)")
        if not hit:
            full = w.output.toPlainText() if hasattr(w, "output") else ""
            r.note("IDE Output during debug:\n" + full[-3000:])
            sub[k + "breakpoint"] = (f"FAIL: the breakpoint in the Click handler was not hit; title "
                                     f"{C.get_text(form)!r}; Output: {full[-400:]}")
            return
        line0 = run1.stops[-1].line - 1 if run1.stops else (w.stopped_at[1] if w.stopped_at else -1)
        sub[k + "breakpoint"] = (f"PASS - paused at line {line0 + 1} ({how})" if how.startswith("real") else
                                 f"FAIL: paused at line {line0 + 1} {how}")
        if line0 != bp:
            sub[k + "breakpoint"] = f"FAIL: paused at line {line0 + 1}, the breakpoint is on line {bp + 1} ({how})"
        h.pump(1.0)

        # ---- Locals / Call Stack / Immediate / Watch
        n = w.locals.topLevelItemCount()
        names = [w.locals.topLevelItem(i).text(0) for i in range(min(n, 6))]
        val = _var_value(w, var)
        sub[k + "locals"] = (f"PASS - {var} = {val} ({n} variable(s))" if "42" in val else
                             f"FAIL: {var} not shown as 42 (value {val!r}); Locals: {names}" if n else
                             "FAIL: Locals is empty at the breakpoint")
        frames = [w.callstack.item(i).text() for i in range(w.callstack.count())]
        hname = handler.split(".")[-1].split("::")[-1].lower()
        sub[k + "callstack"] = (f"PASS - {len(frames)} frame(s), top: {frames[0][:60]}" if frames and
                                hname in frames[0].lower() else
                                f"FAIL: the handler {hname} is not on top: {frames[:3]}" if frames else
                                "FAIL: the Call Stack is empty")
        log0 = w.immediate.log.toPlainText()
        w.immediate.input.setText(var)
        w.immediate._run()
        h.wait(lambda: len(w.immediate.log.toPlainText()) > len(log0) + len(var) + 4, 20)
        h.pump(0.5)
        got = w.immediate.log.toPlainText()[len(log0):].strip().replace("\n", " | ")
        sub[k + "immediate"] = (f"PASS - {got[:80]}" if "42" in got.split("|", 1)[-1] else
                                f"FAIL: Immediate {var} gave {got[:200]!r}")
        tree = getattr(w, "watch_tree", None)
        if tree is not None:
            from PyQt6.QtWidgets import QLineEdit
            entry = w.dock_watch.widget().findChild(QLineEdit)     # "Add a watch expression and press Enter"
            entry.setText(var)
            entry.returnPressed.emit()
            it = tree.topLevelItem(tree.topLevelItemCount() - 1)
            h.wait(lambda: "42" in it.text(1), 15)
            sub[k + "watch"] = (f"PASS - {var} = {it.text(1)[:60]}" if "42" in it.text(1) else
                                f"FAIL: Watch {var} shows {it.text(1)[:200]!r}")
            tree.takeTopLevelItem(tree.indexOfTopLevelItem(it))
        else:
            sub[k + "watch"] = "SKIP: no Watch window"

        # ---- stepping
        if w.session is None:
            sub[k + "step_over"] = "FAIL: the debug session ended at the breakpoint"
            return
        print("    [debug] step over / into / out", time.strftime("%X"), flush=True)
        moved = run1.resume_and_wait(w.session.step_over) and run1.stops[-1].line - 1 != line0
        sub[k + "step_over"] = (f"PASS - line {line0 + 1} -> {run1.stops[-1].line}" if moved else
                                "FAIL: Step Over did not pause on another line")
        if moved:
            f1 = len(run1.stops[-1].frames)
            into = run1.resume_and_wait(w.session.step_into)
            if into:
                info = run1.stops[-1]
                sub[k + "step_into"] = (f"PASS - paused at {os.path.basename(info.file)}:{info.line} "
                                        f"(depth {f1} -> {len(info.frames)})")
            else:
                sub[k + "step_into"] = "FAIL: Step Into did not pause again"
            if into and w.session is not None:
                depth = len(run1.stops[-1].frames)
                fn = run1.stops[-1].file
                out = run1.resume_and_wait(w.session.step_out, 20)
                if out:
                    info = run1.stops[-1]
                    ok = len(info.frames) < depth or info.file != fn or not info.frames
                    sub[k + "step_out"] = ((f"PASS - paused in the caller {os.path.basename(info.file)}:{info.line}"
                                            f" (depth {depth} -> {len(info.frames)})") if ok else
                                           f"FAIL: Step Out paused at {os.path.basename(info.file)}:{info.line} "
                                           f"(depth {depth} -> {len(info.frames)})")
                elif w.session is not None and not w.session.paused and h.wait(
                        lambda: C.get_text(form) == C.EXPECTED_TITLE, 10):
                    sub[k + "step_out"] = "PASS - the handler finished and the program runs (caller is not user code)"
                else:
                    sub[k + "step_out"] = (f"FAIL: Step Out: session {'ended' if w.session is None else 'running'}, "
                                           f"title {C.get_text(form)!r}")
        if w.session is None:
            sub[k + "continue"] = "FAIL: the debug session ended while stepping"
            return

        # ---- continue
        if run1.paused():
            w.session.cont()
        h.wait(lambda: not run1.paused(), 10)
        fin = h.wait(lambda: C.get_text(form) == C.EXPECTED_TITLE, 20)
        if run1.paused():                 # stopped again (e.g. a step command still pending): resume once more
            w.session.cont()
            fin = h.wait(lambda: C.get_text(form) == C.EXPECTED_TITLE, 20)
        sub[k + "continue"] = ("PASS - resumed, the handler finished (title 'Hi QA')" if fin and not run1.paused()
                               else f"FAIL: continue: paused={run1.paused()} title={C.get_text(form)!r}")

        # ---- conditional breakpoint
        from radide.debug_extras import encode_bp
        from radide.features.debug_views import apply_breakpoint_settings
        if w.session is not None and not run1.paused():
            print("    [debug] condition", time.strftime("%X"), flush=True)
            apply_breakpoint_settings(w, code_file, bp, encode_bp(cond=_cond(pl.id, 41)), ed)
            h.pump(1.5)
            false_hit = run1.click(wait=8, retries=0)
            if false_hit:
                w.session.cont()
                h.wait(lambda: not run1.paused(), 10)
            apply_breakpoint_settings(w, code_file, bp, encode_bp(cond=_cond(pl.id, 42)), ed)
            h.pump(1.5)
            true_hit = run1.click(wait=20, retries=1)
            sub[k + "condition"] = ("PASS - false condition did not stop, true condition stopped"
                                    if true_hit and not false_hit else
                                    f"FAIL: {_cond(pl.id, 41)!r} {'stopped' if false_hit else 'did not stop'}, "
                                    f"{_cond(pl.id, 42)!r} {'stopped' if true_hit else 'did not stop'}")
            if run1.paused():
                w.session.cont()
                h.wait(lambda: not run1.paused(), 10)

        # ---- hit count
        if w.session is not None and not run1.paused():
            print("    [debug] hit count", time.strftime("%X"), flush=True)
            ed.set_breakpoints([])
            w._on_bp_toggled(code_file, bp, False)
            w.bp_conditions.pop((code_file, bp), None)
            h.pump(1.0)
            apply_breakpoint_settings(w, code_file, bp, encode_bp(hit="2"), ed)
            h.pump(1.5)
            first_hit = run1.click(wait=8, retries=0)
            if first_hit:
                w.session.cont()
                h.wait(lambda: not run1.paused(), 10)
            second_hit = run1.click(wait=20, retries=0)
            sub[k + "hitcount"] = ("PASS - 1st click did not stop, 2nd stopped" if second_hit and not first_hit else
                                   f"FAIL: hit count 2: 1st click {'stopped' if first_hit else 'did not stop'}, "
                                   f"2nd {'stopped' if second_hit else 'did not stop'}")
            if run1.paused():
                w.session.cont()
                h.wait(lambda: not run1.paused(), 10)
            w.bp_conditions.pop((code_file, bp), None)

        # ---- stop
        print("    [debug] w.stop_project()", time.strftime("%X"), flush=True)
        w.stop_project()
        ended = h.wait(lambda: w.session is None, 30)
        gone = h.wait(lambda: not C.user32.IsWindow(form), 15)
        sub[k + "stop"] = ("PASS - session ended, program window closed" if ended and gone else
                           f"FAIL: stop: session {'ended' if ended else 'still running'}, "
                           f"window {'closed' if gone else 'still open'}")

        # ---- exception (second run, no breakpoint, Break on Exceptions on)
        throw = THROW.get(pl.id)
        if not throw:
            sub[k + "exception"] = "SKIP: no throwing statement for this language"
            return
        print("    [debug] exception run", time.strftime("%X"), flush=True)
        ed.set_breakpoints([])
        w.bp_conditions.clear()
        w._sync_breakpoints()
        lines = ed.text().split("\n")
        indent = lines[bp][:len(lines[bp]) - len(lines[bp].lstrip())]
        lines.insert(bp, indent + throw)
        ed.setText("\n".join(lines))
        h.pump(1.0)
        if getattr(w, "a_break_on_exception", None) is not None:
            w.a_break_on_exception.setChecked(True)
        run2 = _Run(h)
        form2 = run2.start(slow)
        if not form2:
            sub[k + "exception"] = f"FAIL: no program window (with the throw) within {slow}s: " \
                                   f"{w.output.toPlainText()[-300:]}"
            return
        h.pump(1.5)
        stopped = run2.click(wait=30, retries=1)
        if stopped:
            info = run2.stops[-1]
            at = f"{os.path.basename(info.file)}:{info.line} (reason {info.reason})"
            sub[k + "exception"] = (f"PASS - paused at the throw, {at}" if info.line == bp + 1 and
                                    os.path.basename(info.file).lower() == code_file.lower() else
                                    f"FAIL: paused at {at}, the throw is at {code_file}:{bp + 1}")
        else:
            out = w.output.toPlainText()
            sub[k + "exception"] = ("FAIL: the error did not pause the debugger; Output: "
                                    + out[-300:].replace("\n", " | "))
    except Exception as e:  # noqa: BLE001
        sub[k + "error"] = f"FAIL: {type(e).__name__}: {e}"
        r.note(traceback.format_exc())
    finally:
        try:
            if w.session is not None:
                w.stop_project()
                h.wait(lambda: w.session is None, 15)
            if ed is not None and original_text is not None:
                ed.setText(original_text)
                w.save_all()
            cv = w.codeviews.get("Form1")
            if cv is not None:
                cv.editor.set_breakpoints([])
                w._sync_breakpoints()
            if hasattr(w, "bp_conditions"):
                w.bp_conditions.clear()
        except Exception:  # noqa: BLE001
            pass
