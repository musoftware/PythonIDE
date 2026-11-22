"""Runs one EventsDemo program on a Tk engine IN THIS PROCESS and drives it through the steps of spec.py:

    python tk_driver.py vbrun  <project folder> <log file>     VB6 project on the IDE's VB runtime (vbrun.py)
    python tk_driver.py python <project folder> <log file>     Python Tkinter project (generated designer)
    python tk_driver.py bridge <project folder> <log file>     any GUI Bridge language on the IDE's bridge host

Tk does not take posted mouse messages (it reads the button state with GetKeyState and drops a press it did
not see), so mouse and keyboard input are injected with Tk's own `event generate` on the real widgets (the
whole binding chain runs: widget, class, toplevel); focus is taken with `focus -force` once; closing posts a
real WM_CLOSE to the toplevel's frame window. The log gets the program's EVT lines and the step markers.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE))

from evcore import FileLog, ListLog, run_steps  # noqa: E402

user32 = ctypes.WinDLL("user32")
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
user32.LoadKeyboardLayoutW.restype = ctypes.c_void_p
user32.ActivateKeyboardLayout.argtypes = [ctypes.c_void_p, ctypes.c_uint]
user32.SetActiveWindow.argtypes = [ctypes.c_void_p]
user32.SetFocus.argtypes = [ctypes.c_void_p]
VK = {c: ord(c.upper()) for c in "abcdefghijklmnopqrstuvwxyz"}


class TkDriver:
    def __init__(self, root, widget_of, alive_fn, read_fn, set_fn):
        self.root = root
        self.widget_of = widget_of
        self._alive = alive_fn
        self._read = read_fn
        self._set = set_fn
        # US keyboard layout for this (test) thread only: `event generate -keysym a` needs a key for "a"
        user32.ActivateKeyboardLayout(user32.LoadKeyboardLayoutW("00000409", 0), 0)
        self.pump(0.2)
        # the toplevel takes the Win32 focus of this thread: Tk only raises FocusIn / FocusOut while it has it
        self.take_focus()

    def take_focus(self):
        """Give the toplevel the Win32 focus of this thread again when another program took it."""
        if user32.GetFocus():
            return
        frame = int(self.root.wm_frame(), 16)
        user32.SetActiveWindow(frame)
        user32.SetFocus(frame)
        self.pump(0.2)

    def pump(self, sec):
        end = time.time() + sec
        while True:
            try:
                self.root.update()
            except Exception:  # noqa: BLE001 - the window was destroyed
                time.sleep(0.02)
            if time.time() >= end:
                break
            time.sleep(0.01)

    def click(self, name, x, y):
        self.take_focus()
        w = self.widget_of(name)
        w.event_generate("<Enter>", x=x, y=y)
        w.event_generate("<ButtonPress-1>", x=x, y=y)
        self.pump(0.05)
        w.event_generate("<ButtonRelease-1>", x=x, y=y)
        self.pump(0.05)

    def _gen(self, w, seq, letter):
        """event generate of a key; the thread's layout can be switched back by the desktop: US again, retry."""
        for _ in range(3):
            try:
                w.event_generate(seq, keycode=VK[letter], keysym=letter)
                return
            except Exception:  # noqa: BLE001 - TclError "no keycode for keysym"
                user32.ActivateKeyboardLayout(user32.LoadKeyboardLayoutW("00000409", 0), 0)
                self.pump(0.1)
        print(f"[tk_driver] could not generate {seq} {letter}", file=sys.stderr, flush=True)

    def key(self, name, letter):
        self.take_focus()
        w = self.root.focus_get() or self.widget_of(name)
        self._gen(w, "<KeyPress>", letter)
        self.pump(0.05)
        w = self.root.focus_get() or w
        self._gen(w, "<KeyRelease>", letter)

    def msgbox(self, name, seconds):
        """Click *name* (its handler shows a message box: the click returns when the box is closed); a thread
        closes the box after *seconds*."""
        import threading
        from evcore import close_dialogs

        def closer():
            end = time.time() + seconds + 10
            time.sleep(seconds)
            while time.time() < end and not close_dialogs(os.getpid()):
                time.sleep(0.1)
        threading.Thread(target=closer, daemon=True).start()
        self.click(name, 5, 5)

    def text(self, name, value):
        self._set(name, value)

    def read(self, name):
        return self._read(name)

    def focus(self):
        f = self.root.focus_get()
        if f is None:
            return ""
        for cand in ("txtA", "txtB", "cmdA", "cmdCode", "cmdTmr", "chkA", "lstA"):
            try:
                if self.widget_of(cand) is f:
                    return cand
            except Exception:  # noqa: BLE001
                pass
        return str(f)

    def close(self):
        try:
            frame = int(self.root.wm_frame(), 16)
        except Exception:  # noqa: BLE001
            return
        user32.PostMessageW(frame, 0x0010, 0, 0)            # WM_CLOSE

    def alive(self):
        return self._alive()

    def wait_exit(self):
        end = time.time() + 5
        while time.time() < end and self.alive():
            self.pump(0.1)


def vbrun_engine(folder: Path, logpath: Path):
    from radide.runtimes import vbrun
    from radide.runtimes.vbinterp import to_str
    log = ListLog(logpath)
    rt = vbrun.Runtime(folder)
    rt.interp.output = log.write
    state = {"ended": False}

    def end():
        state["ended"] = True
        try:
            rt.root.withdraw()
        except Exception:  # noqa: BLE001
            pass
    rt.end = end
    rt.load()
    vf = rt.forms[rt.project.startup.lower()]
    rt.startup_form = vf
    vf.load()
    vf.vb_call("show", [])

    def widget(name):
        return vf.controls[name.lower()].w

    def setter(name, value):
        vf.controls[name.lower()].vb_set("text", value)
    d = TkDriver(rt.root, widget, lambda: not state["ended"] and vf.loaded,
                 lambda n: to_str(vf.controls[n.lower()].vb_get("text")), setter)
    return d, log


def python_engine(folder: Path, logpath: Path):
    from radide.languages import get_plugin
    from radide.model import Form
    plugin = get_plugin("python-tk")
    form = Form.load(folder / "Form1.form")
    user = (folder / "Form1.py").read_text(encoding="utf-8")
    (folder / "Form1_designer.py").write_text(plugin.generate_designer(form, user), encoding="utf-8")
    os.environ["RADEVT_LOG"] = str(logpath)
    log = FileLog(logpath)
    sys.path.insert(0, str(folder))
    os.chdir(folder)
    import Form1  # noqa: E402
    app = Form1.Form1()

    def alive():
        try:
            return bool(app.root.winfo_exists())
        except Exception:  # noqa: BLE001
            return False

    def setter(name, value):
        getattr(app, f"{name}_var").set(value)
    d = TkDriver(app.root, lambda n: getattr(app, n), alive, lambda n: getattr(app, f"{n}_var").get(), setter)
    return d, log


def bridge_engine(folder: Path, logpath: Path):
    from radide.languages import get_plugin
    from radide.model import Project
    from radide.runtimes import bridge
    from radide.runtimes.vbinterp import to_str
    project = Project.load(folder)
    plugin = get_plugin(project.language)
    spec = plugin.run_spec(folder, project.startup, "")
    args = spec.args
    build = args[args.index("--build") + 1] if "--build" in args else None
    program = args[args.index("--") + 1:]
    if build:
        r = subprocess.run(build, cwd=str(folder), shell=True, capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            print("BUILD FAILED\n" + (r.stdout + r.stderr)[-3000:], flush=True)
            sys.exit(3)
    os.environ.update({k: v for k, v in (spec.env or {}).items() if k.startswith("RAD")})
    os.environ["RADEVT_LOG"] = str(logpath)
    handlers = set(filter(None, os.environ.get("RAD_HANDLERS", "").split(",")))
    log = FileLog(logpath)
    rt = bridge.BridgeRuntime(folder, program, handlers)
    state = {"ended": False}

    def end():
        if state["ended"]:
            return
        state["ended"] = True
        if rt.proc and rt.proc.poll() is None:
            rt.send("QUIT")
            try:
                rt.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                rt.proc.kill()
        try:
            rt.root.withdraw()
        except Exception:  # noqa: BLE001
            pass
    rt.end = end
    rt.load()
    rt.start_program()
    vf = rt.forms[(project.startup or project.forms[0]).lower()]
    rt.startup_form = vf
    vf.load()
    vf.vb_call("show", [])

    def widget(name):
        return vf.controls[name.lower()].w

    def setter(name, value):
        vf.controls[name.lower()].vb_set("text", value)
    d = TkDriver(rt.root, widget, lambda: not state["ended"] and vf.loaded,
                 lambda n: to_str(vf.controls[n.lower()].vb_get("text")), setter)
    return d, log


def main():
    engine, folder, logpath = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
    family = sys.argv[4] if len(sys.argv) > 4 else {"vbrun": "vb6", "python": "tk"}.get(engine, "neutral")
    logpath.unlink(missing_ok=True)
    d, log = {"vbrun": vbrun_engine, "python": python_engine, "bridge": bridge_engine}[engine](folder, logpath)
    try:
        run_steps(d, log, family)
    finally:
        print("DRIVER DONE", flush=True)
    os._exit(0)                 # Tk / the bridge's reader thread: leave at once


if __name__ == "__main__":
    main()
