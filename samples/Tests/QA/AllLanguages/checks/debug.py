"""Check family "debug": F5 with a breakpoint in Button1_Click, for languages whose debugger the IDE supports.

  start       F5 (run_project(debug=True)) starts the program; its window "Form1" appears (Win32, own process)
  breakpoint  Button1 is clicked (posted messages to that window) and the IDE pauses in the handler
  locals      the Locals window shows variables
  step_over   Step Over pauses again on a later line
  continue    Continue resumes; Stop ends the session
"""
from __future__ import annotations

import os
import time
import traceback

from . import common as C


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
    return None


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
    try:
        from .ide import editor_for_form
        ed, hline, handler = editor_for_form(h)
        lines = ed.text().split("\n")
        first = C.CLICK[pl.id][0].strip()[:20]
        bp = next((i for i in range(hline + 1, min(len(lines), hline + 12)) if first in lines[i]), -1)
        if bp < 0:
            sub[k + "start"] = f"FAIL: handler body not found ({handler})"
            return
        print("    [debug] ed.set_breakpoints([bp])", time.strftime("%X"), flush=True)
        ed.set_breakpoints([bp])
        w._sync_breakpoints()
        print("    [debug] w.run_project(debug=True)", time.strftime("%X"), flush=True)
        w.run_project(debug=True)
        slow = 300 if pl.id in ("rust-bridge", "java-bridge", "csharp-bridge", "dart-bridge", "go-bridge",
                                "cpp-bridge", "fortran-bridge", "typescript") else 120
        form = _program_window(slow, h)
        if not form:
            out = w.output.toPlainText()[-600:] if hasattr(w, "output") else ""
            sub[k + "start"] = f"FAIL: no program window within {slow}s; Output: {out}"
            return
        sub[k + "start"] = "PASS - program window shown under the debugger"
        h.pump(1.5)
        print("    [debug] C.click_button_ext(form)", time.strftime("%X"), flush=True)
        C.click_button_ext(form)
        hit = h.wait(lambda: w.stopped_at is not None, 30)
        for _ in range(2):                  # like gui_test: a click can be lost while the program starts up
            if hit or C.get_text(form) == C.EXPECTED_TITLE:
                break
            C.click_button_ext(form)
            hit = h.wait(lambda: w.stopped_at is not None, 20)
        how = "click on the program's window"
        covered = C.ensure_uncovered(form, form, 10, 10) if not hit else ""
        if not hit and callable(getattr(w.session, "simulate", None)):
            # the debugger's own event injection (radide/bridgedebug.py simulate): tells a click problem from a
            # debugger problem
            w.session.simulate("Button1", "Click")
            hit = h.wait(lambda: w.stopped_at is not None, 40)
            how = ("only with session.simulate (the real click did not stop)" if "stays covered" not in covered else
                   "with session.simulate (another program's window covers the screen: no real click possible)")
        if not hit:
            full = w.output.toPlainText() if hasattr(w, "output") else ""
            r.note("IDE Output during debug:\n" + full[-3000:])
            out = full[-400:]
            sub[k + "breakpoint"] = (f"FAIL: the breakpoint in the Click handler was not hit; title "
                                     f"{C.get_text(form)!r}; Output: {out}")
            return
        line0 = w.stopped_at[1]
        sub[k + "breakpoint"] = (f"PASS - paused at line {line0 + 1} ({how})"
                                 if how.startswith(("click", "with session")) else
                                 f"FAIL: paused at line {line0 + 1} {how}")
        n = w.locals.topLevelItemCount()
        names = [w.locals.topLevelItem(i).text(0) for i in range(min(n, 6))]
        sub[k + "locals"] = f"PASS - {n} variable(s): {names}" if n else "FAIL: Locals is empty at the breakpoint"
        if w.session is None:
            sub[k + "step_over"] = "FAIL: the debug session ended at the breakpoint"
            return
        print("    [debug] w.session.step_over()", time.strftime("%X"), flush=True)
        w.session.step_over()
        moved = h.wait(lambda: w.stopped_at is not None and w.stopped_at[1] != line0, 40)
        sub[k + "step_over"] = f"PASS - now at line {w.stopped_at[1] + 1}" if moved else \
            "FAIL: Step Over did not pause on another line"
        if w.session is None:
            sub[k + "continue"] = "FAIL: the debug session ended after Step Over"
            return
        print("    [debug] w.session.cont()", time.strftime("%X"), flush=True)
        w.session.cont()
        h.pump(2)
        resumed = w.stopped_at is None
        print("    [debug] w.stop_project()", time.strftime("%X"), flush=True)
        w.stop_project()
        ended = h.wait(lambda: w.session is None, 30)
        sub[k + "continue"] = ("PASS - continued and stopped" if resumed and ended else
                               f"FAIL: continue={'ok' if resumed else 'still paused'} "
                               f"stop={'ok' if ended else 'session still running'}")
    except Exception as e:  # noqa: BLE001
        sub[k + "error"] = f"FAIL: {type(e).__name__}: {e}"
        r.note(traceback.format_exc())
    finally:
        try:
            if w.session is not None:
                w.stop_project()
                h.wait(lambda: w.session is None, 15)
            ed = w.codeviews.get("Form1")
            if ed is not None:
                ed.editor.set_breakpoints([])
                w._sync_breakpoints()
        except Exception:  # noqa: BLE001
            pass
