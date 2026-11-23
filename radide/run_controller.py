"""Run / Debug of the IDE (moved out of MainWindow): find the startup file, start the program or the debugger,
the RAD Hub for cross-language calls, show a stop / resumed / the end of the program, stop it.

MainWindow keeps one-line methods with the same names - features, tests and signal connections use them - and
the steps around them that features take part in (run_project, _make_session, _on_stopped, _on_resumed,
_on_finished: radide/extension_points.py). Calls between the steps go through the window (``w.<name>``) so those
stay the single place to change or observe a step.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

from .debugger import Session, StopInfo
from .interpreters import debugpy_adapter_for, python_info, real_python


MAIN_RX = re.compile(r"__name__\s*==\s*['\"]__main__['\"]|\bsub\s+main\b|\bfunc(?:tion)?\s+main\b|"
                          r"\b(?:def|fn|void|int|static\s+void)\s+main\s*\(|^\s*main\s*\(\s*\)", re.I | re.M)


def bring_to_front(win) -> None:
    """Raise the IDE above the paused program (Windows blocks plain
    activateWindow from background processes), and flash the taskbar."""
    if win.isMinimized():
        win.showNormal()
    win.raise_()
    win.activateWindow()
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # a synthetic Alt press lets SetForegroundWindow pass Windows'
            # focus-stealing guard without attaching to the (paused) program
            VK_MENU, KEYUP = 0x12, 0x0002
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_MENU, 0, KEYUP, 0)
            user32.SetForegroundWindow(int(win.winId()))
        except Exception:  # noqa: BLE001 - best effort
            pass
    QApplication.alert(win, 3000)


class RunController:
    def __init__(self, win):
        self.win = win

    def _effective_startup(self, rp) -> str | None:
        """The startup the run plugin gets. A console project with no forms and an empty
        "startup" runs the module with a main (if __name__ == "__main__", def main, Sub Main...)
        or else the first module of the plugin's language. None = nothing can run (logged)."""
        w = self.win
        p = w.project
        startup = (p.startup or "").strip()
        if startup:
            return startup
        if p.forms:
            first = p.forms[0]
            return first if (Path(p.folder) / rp.code_file(first)).exists() else startup
        ext = (getattr(rp, "code_ext", "") or "").lower()
        mods = [m for m in p.modules if not ext or m.lower().endswith(ext)]
        if not mods:
            if not p.modules:
                w.log("*** Nothing to run: the project has no forms and no modules")
                return None
            return startup              # other languages decide themselves (plugins with no code_ext)
        chosen = None
        for m in mods:
            try:
                text = (Path(p.folder) / m).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if MAIN_RX.search(text):
                chosen = m
                break
        chosen = chosen or next((m for m in mods if Path(m).stem.lower() in ("main", "program", "app")), mods[0])
        stem = chosen[:-len(ext)] if ext and chosen.lower().endswith(ext) else chosen
        w.log(f"No startup object is set: running {chosen} (Project > Properties > Startup to change)")
        return stem
    def _run_project(self, debug: bool = True):
        w = self.win
        if not w.project or (w.session is not None and w.session.running()):
            return
        if w.save_all() is False:             # disk full / locked file: the message is shown, no run of old code
            return
        if w.sln is not None:                 # a solution runs its StartUp Project
            from .features.solution_ui import prepare_run
            if not prepare_run(w):
                return
        if getattr(w.project, "kind", "") == "website":      # web site: DevServer + Preview (CONTRACTS 8.1)
            from .features.web_workspace import run_website
            run_website(w, w.project, debug=debug)
            return
        interp = w._interpreter()
        if not interp:
            w.log("No interpreter configured (Tools > Interpreter Path...)")
            return
        rp = w.run_plugin()
        if rp.id.startswith("python") or getattr(rp, "uses_debugpy", False):
            interp = real_python(interp)        # not the Windows Store alias
        debug = debug and rp.supports_debug
        startup = w._effective_startup(rp)
        if startup is None:
            return
        # a project in a deep folder runs through a short junction (Windows cannot start a program in a working
        # directory over MAX_PATH, toolchains fail on long names); debugging only when it would fail otherwise,
        # so breakpoint paths stay the real ones (paths.short_alias)
        from .paths import short_alias
        run_folder = short_alias(w.project.folder, limit=200 if debug else 100)
        if run_folder != Path(w.project.folder):
            w.log(f"(long path: running through the short alias {run_folder})")
        try:
            if debug:
                spec = rp.debug_spec(run_folder, startup, interp,
                                     w._all_breakpoints())
            else:
                spec = rp.run_spec(run_folder, startup, interp)
        except Exception as e:  # noqa: BLE001 - show plugin errors instead of crashing
            w.log(f"*** Cannot start the program: {e}")
            return
        spec = w._start_hub(spec)
        try:        # data sources: database passwords the IDE knows reach the program (environment only)
            from .features.data_sources import run_env
            spec.env = run_env(w, spec.env)
        except Exception as e:  # noqa: BLE001 - never stop F5
            w.log(f"[data sources] {e}")
        w.output.clear()
        w.locals.clear()
        w.callstack.clear()
        w.dock_output.show()
        w.dock_output.raise_()
        w.log(f"------ {'Debug' if debug else 'Run'}: {spec.program} {' '.join(spec.args)} ------")
        if rp.id.startswith("python") or getattr(rp, "uses_debugpy", False):
            ver = python_info(interp)[0]
            w.log(f"Python interpreter: {interp}" + (f" (Python {ver})" if ver else ""))
        s = w._make_session(spec, debug, rp, interp, startup)
        s.output.connect(w._append_output)
        s.stopped.connect(w._on_stopped)
        s.resumed.connect(w._on_resumed)
        from .tools import on_eval_result
        s.evalResult.connect(lambda txt: on_eval_result(w, txt) or w.immediate.show_result(txt))
        s.finished.connect(lambda code, s=s: w._on_finished(code, s))
        s.failed.connect(lambda err: w.log(f"*** Error: {err}"))
        w.session = s
        s.start()
        if debug and type(s) is Session:      # agents (VB, Ring, ...): Debug > Break on Exceptions from the start
            s.set_break_on_exception(w.settings.value("debug/break_on_exception", True) in (True, "true"))
        w._set_run_state("Running...")
        w._update_actions()
    def _create_session(self, spec, debug, plugin, interp, startup=None):
        """Python debugging uses debugpy (DAP) when installed: conditional breakpoints and
        break on exception come ready-made. Everything else uses the plugin's own agent."""
        w = self.win
        factory = getattr(plugin, "make_session", None)      # foreign projects (radide/foreign/*): own toolchain
        if callable(factory):
            s = factory(w, spec, debug)
            if s is not None:
                return s
        adapter = None
        if debug and (plugin.id.startswith("python") or getattr(plugin, "uses_debugpy", False)) \
                and w.settings.value("debug/python_engine", "debugpy") == "debugpy":
            # the program runs with the same interpreter as Run (project .venv / configured / found); debugpy
            # comes from that interpreter, the IDE, or is installed into the interpreter on demand
            py = real_python(interp)
            adapter, how = debugpy_adapter_for(py, w._install_debugpy)
            if adapter:
                w.log(f"Debugger: {how}")
            else:
                w.log("Debugger: the IDE's built-in Python debugger (debugpy is not available for this "
                         "interpreter)")
        if adapter:
            from .dap import DapSession
            program = str(w.project.folder / plugin.code_file(w.project.startup if startup is None else startup))
            s = DapSession("debugpy", program, [], w.project.folder.resolve(), spec.env,
                           w._all_breakpoints(), w)
            s.argv = adapter
            s.launch_args["python"] = [real_python(interp)]
            # the generated *_designer.py is not "my code" (like VS's designer files): stepping skips it, and an
            # error in an event handler called by Qt (C++ calls the designer's wrapper, nothing in Python catches
            # it) still counts as user-unhandled - debugpy then pauses on the line that raised it
            s.launch_args["rules"] = [{"path": str(Path(w.project.folder).resolve() / "*_designer.py"),
                                       "include": False}]
            s.break_on_exception = w.settings.value("debug/break_on_exception", True) in (True, "true")
            return s
        from .languages.bridgebase import BridgeLanguagePlugin
        if debug and isinstance(plugin, BridgeLanguagePlugin):
            from .bridgedebug import BridgeDebugSession, engine_for
            if engine_for(plugin):        # GUI Bridge program: attach gdb / netcoredbg / js-debug / dart
                return BridgeDebugSession(spec, plugin, w._all_breakpoints(), w,       # Debug > Break on
                                          break_on_exception=w.settings.value(          # Exceptions
                                              "debug/break_on_exception", True) in (True, "true"))
        return Session(spec, debug, w)
    def _install_debugpy(self, python: str) -> bool:
        """pip install debugpy into *python* (the program's interpreter) - like the IDE does for PyInstaller; the
        window stays responsive, the pip output goes to the Output window. Tools > Options can turn it off
        (QSettings debug/install_debugpy)."""
        w = self.win
        if w.settings.value("debug/install_debugpy", True) in (False, "false", "0", 0) \
                or os.environ.get("RADIDE_NO_DEBUGPY_INSTALL"):
            return False
        from PyQt6.QtCore import QElapsedTimer, QEventLoop, QProcess
        w.log(f"Installing debugpy into {python} (pip install debugpy) ...")
        w.dock_output.show()
        proc = QProcess()                        # waited for below: no parent needed
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(
            lambda: w._append_output(bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")))
        proc.start(python, ["-m", "pip", "install", "--disable-pip-version-check", "--no-input", "debugpy"])
        if not proc.waitForStarted(10000):
            w.log("*** pip could not be started")
            return False
        timer = QElapsedTimer()
        timer.start()
        while proc.state() != QProcess.ProcessState.NotRunning and timer.elapsed() < 300_000:
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            proc.waitForFinished(50)
        if proc.state() != QProcess.ProcessState.NotRunning:
            proc.kill()
            proc.waitForFinished(3000)
            w.log("*** pip install debugpy timed out")
            return False
        ok = proc.exitStatus() == QProcess.ExitStatus.NormalExit and proc.exitCode() == 0
        if not ok:
            w.log(f"*** pip install debugpy failed (exit code {proc.exitCode()})")
        return ok
    def _start_hub(self, spec):
        """Start a RAD Hub for this run and give the program RAD_HUB / RAD_PROJECT."""
        w = self.win
        import os as _os

        from .runtimes.radhub import RadHub
        w._stop_hub()

        def interp_for(plugin):
            return plugin.find_interpreter(w._configured_interpreter(plugin))
        search = []
        if w.sln is not None:   # modules of referenced projects (transitively) are found too
            search = [Path(p.folder) for p in w.sln.referenced_projects(w.project)]
        try:
            w.hub = RadHub(w.project.folder, log=w._hub_log.emit, interpreter_for=interp_for,
                              search_folders=search)
        except TypeError:          # older RadHub without solution support
            w.hub = RadHub(w.project.folder, log=w._hub_log.emit, interpreter_for=interp_for)
        try:
            w.hub.start()
        except OSError as e:
            w.log(f"*** RAD Hub could not start ({e}); cross-language calls are disabled")
            w.hub = None
            return spec
        w._copy_clients()
        spec.env = w.hub.child_env(base=spec.env if spec.env is not None else dict(_os.environ))
        return spec
    def _copy_clients(self):
        """radcall clients that a language loads from the project folder."""
        w = self.win
        folder = w.project.folder
        try:
            if any("radcall" in f.read_text(encoding="utf-8", errors="replace")
                   for f in folder.glob("*.ring") if f.name != "radcall.ring"):
                from .languages.ring_qt import copy_ring_client
                copy_ring_client(folder)
        except OSError as e:
            w.log(f"*** cannot copy radcall.ring: {e}")
        try:                     # Python: also on PYTHONPATH; the copy helps IntelliSense and EXE builds
            if any("radcall" in f.read_text(encoding="utf-8", errors="replace")
                   for f in folder.glob("*.py") if f.name != "radcall.py"):
                from .runtimes.radhub import CLIENTS
                src = (CLIENTS / "python" / "radcall.py").read_bytes()
                target = folder / "radcall.py"
                if not target.exists() or target.read_bytes() != src:
                    target.write_bytes(src)
        except OSError as e:
            w.log(f"*** cannot copy radcall.py: {e}")
    def _stop_hub(self):
        w = self.win
        hub, w.hub = getattr(w, "hub", None), None
        if hub is not None:
            hub.stop()
    def _append_output(self, text: str):
        w = self.win
        w.output.moveCursor(w.output.textCursor().MoveOperation.End)
        if getattr(w, "_output_after_log", False) and not w.output.document().isEmpty():
            text = "\n" + text
        w._output_after_log = False
        w.output.insertPlainText(text)
        w.output.ensureCursorVisible()
    def _form_for_file(self, file: str) -> str | None:
        w = self.win
        base = Path(file).name.lower()
        for name in w.project.forms:
            if w.plugin_for_form(name).code_file(name).lower() == base:
                return name
        return None
    def _show_stopped(self, info: StopInfo):
        w = self.win
        w._clear_current_line()
        ed = w._editor_for_file(info.file)
        if ed is not None:
            ed.set_current_line(info.line - 1)
            w.stopped_at = (ed, info.line - 1)
        where = f"{Path(info.file).name} line {info.line}"
        w._set_run_state(f"Paused ({info.reason}) at {where}")
        if info.reason == "error":
            w.log(f"\n*** Error at {where}")
        w.locals.clear()
        for name, typ, value in info.variables:
            QTreeWidgetItem(w.locals, [name, value, typ])
        w.callstack.clear()
        for func, file, line in info.frames:
            w.callstack.addItem(f"{func}()   {Path(file).name}: line {line}")
            w.callstack.item(w.callstack.count() - 1).setData(Qt.ItemDataRole.UserRole, (file, line))
        w.dock_locals.show()
        w.dock_locals.raise_()
        bring_to_front(w)
        w._update_actions()
    def _on_frame_dclick(self, item):
        w = self.win
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            ed = w._editor_for_file(data[0])
            if ed is not None:
                ed.goto_line(int(data[1]) - 1)
    def _clear_current_line(self):
        w = self.win
        if w.stopped_at:
            try:
                w.stopped_at[0].set_current_line(None)
            except RuntimeError:     # editor already closed
                pass
        w.stopped_at = None
    def _set_run_state(self, text: str) -> None:
        """Run / debug state in the status bar. Also kept in the permanent left label: on a real
        display any status tip (the mouse over a toolbar, the Preview page...) clears the temporary
        message, which then showed "Ready" while the program was still paused."""
        w = self.win
        w.statusBar().showMessage(text)
        lbl = getattr(w, "status_ready", None)
        if lbl is not None:
            lbl.setText(text)
    def _show_resumed(self):
        w = self.win
        w._clear_current_line()
        w._set_run_state("Running...")
        w._update_actions()
    def stop_project(self):
        w = self.win
        if w.session is not None:
            w.session.stop()
        if getattr(w, "web_server", None) is not None:    # web site dev server (CONTRACTS 8.1)
            from .features.web_workspace import stop_website
            stop_website(w)
    def _show_finished(self, code, session=None):
        w = self.win
        if session is not None and w.session is not None and session is not w.session:
            return      # an earlier (stopped) session ended after F5 started a new one: keep the new one
        w._clear_current_line()
        if w.session is not None and w.session.user_stopped:
            w.log("\n------ Debugging stopped ------")
        else:
            w.log(f"\n------ Program exited with code {code} ------")
        w.session = None
        w._stop_hub()
        w._set_run_state("Ready")
        w._update_actions()
