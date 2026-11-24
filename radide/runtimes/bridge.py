"""GUI Bridge: give any language (Fortran, BASIC compilers, C, COBOL...) a
RAD IDE form. The IDE draws the forms; the program talks over stdin/stdout:

  host -> program :  EVENT <object> <event> [args]      (then the program runs its handler)
                     QUIT
  program -> host :  SET <object> <property> <value>
                     GET <object> <property>            (host answers with one line)
                     CALL <object> <method> [arg]       (host answers with one line)
                     MSGBOX <text>                      (host answers 1)
                     INPUT <prompt>                     (host answers the text)
                     SHOW <form> | HIDE <form>
                     DONE                               (handler finished)
                     END                                (quit the program)
  any other line is program output (shown in the IDE Output window).
  ESC <command ...>  the same command with \\ \n \r escaped in its values (multi-line text); its answer is
                     escaped the same way. Answers to commands without ESC are kept on one line.
  CALL <Form> ShowDialog  shows the form modally for the user and answers at once (see form_call).

<object> is a control name, a form name, or Form.Control.

    python -m radide.runtimes.bridge <project-folder> [--build "<cmd>"] -- <program> [args]
"""
from __future__ import annotations

import os
import queue
import shlex
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path

from ..controls import CONTROL_TYPES, FORM_EVENTS, menu_leaves
from ..model import Form
from .vbinterp import to_bool, to_str
from .vbrun import Runtime, VBForm

DEBUG = bool(os.environ.get("RAD_BRIDGE_DEBUG"))      # started by the IDE debugger (radide/bridgedebug.py)


def escape_line(s: str) -> str:
    """Value -> one protocol line ("ESC" commands): \\ -> \\\\, newline -> \\n, CR -> \\r."""
    return str(s).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def unescape_line(s: str) -> str:
    """Inverse of escape_line; an unknown escape is kept as written."""
    if "\\" not in s:
        return s
    out, i, n = [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n and s[i + 1] in "\\nr":
            out.append({"\\": "\\", "n": "\n", "r": "\r"}[s[i + 1]])
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def one_line(s: str) -> str:
    """An answer for a client that does not escape: newlines would split it into several protocol lines."""
    s = str(s)
    return s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ") if ("\n" in s or "\r" in s) else s


RUNTIME_HINTS = {
    "dart": "the Dart SDK (https://dart.dev/get-dart)", "perl": "Perl (https://strawberryperl.com)",
    "ruby": "Ruby (https://rubyinstaller.org)", "php": "PHP (https://windows.php.net/download)",
    "node": "Node.js (https://nodejs.org)", "lua": "Lua (https://www.lua.org)", "java": "Java (https://adoptium.net)",
    "javaw": "Java (https://adoptium.net)", "dotnet": ".NET (https://dotnet.microsoft.com/download)",
    "pwsh": "PowerShell 7 (https://aka.ms/powershell)", "python": "Python (https://www.python.org)",
    "ring": "Ring (https://ring-lang.github.io)", "tsx": "Node.js + tsx (https://nodejs.org)",
}


def missing_runtime_text(exe: str, ex: Exception | None = None) -> str:
    name = Path(str(exe)).stem.lower()
    what = RUNTIME_HINTS.get(name, f"'{Path(str(exe)).name}'")
    text = (f"This program needs {what} to run, but '{Path(str(exe)).name}' was not found on this computer "
            f"(not in the program folder and not on PATH).\n\nInstall it, then start the program again.")
    if ex is not None and not isinstance(ex, FileNotFoundError):
        text += f"\n\n({ex})"
    return text


def fatal(title: str, text: str, code: int = 3):
    """A message box (the published host has no console) and exit. RADIDE_TEST_NO_DIALOGS: stderr only."""
    print(f"[bridge] {title}: {text}", file=sys.stderr, flush=True)
    if not os.environ.get("RADIDE_TEST_NO_DIALOGS"):
        try:
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, text, title, 0x10 | 0x10000)     # MB_ICONERROR|SETFOREGROUND
            else:
                root = tk.Tk()
                root.withdraw()
                from tkinter import messagebox
                messagebox.showerror(title, text)
                root.destroy()
        except Exception:  # noqa: BLE001 - no GUI at all: stderr is all there is
            pass
    os._exit(code)          # forms may already be loaded (Tk root, threads): leave at once


# Tk keysym -> Windows virtual-key code (KeyCode of KeyDown / KeyUp / KeyPress for the bridge clients)
_VK = {"return": 13, "kp_enter": 13, "tab": 9, "backspace": 8, "escape": 27, "space": 32, "prior": 33, "next": 34,
       "end": 35, "home": 36, "left": 37, "up": 38, "right": 39, "down": 40, "insert": 45, "delete": 46,
       "shift_l": 16, "shift_r": 16, "control_l": 17, "control_r": 17, "alt_l": 18, "alt_r": 18, "pause": 19,
       "caps_lock": 20, "num_lock": 144, "scroll_lock": 145, "print": 44, "menu": 93, "app": 93,
       "win_l": 91, "win_r": 92, "super_l": 91, "super_r": 92, "kp_multiply": 106, "kp_add": 107,
       "kp_subtract": 109, "kp_decimal": 110, "kp_divide": 111, "semicolon": 186, "equal": 187, "plus": 187,
       "comma": 188, "minus": 189, "period": 190, "slash": 191, "grave": 192, "bracketleft": 219,
       "backslash": 220, "bracketright": 221, "apostrophe": 222, "quoteright": 222}


def vk_code(e) -> int:
    """The Windows virtual-key code of a key event (EventArgs of radide/languages/python_tk.py: KeyCode is the Tk
    keysym name, raw the Tk event). On Windows Tk's own keycode already is the VK code."""
    code = getattr(e, "KeyCode", 0)
    if isinstance(code, int):
        return code
    raw = getattr(e, "raw", None)
    kc = getattr(raw, "keycode", None)
    if os.name == "nt" and isinstance(kc, int) and kc > 0:
        return kc
    return keysym_to_vk(str(code or ""))


def keysym_to_vk(sym: str) -> int:
    if not sym or sym == "??":
        return 0
    if sym.lstrip("-").isdigit():
        return int(sym)
    low = sym.lower()
    if low in _VK:
        return _VK[low]
    if len(sym) == 1:
        ch = sym.upper()
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            return ord(ch)
        return 0
    if low.startswith("f") and low[1:].isdigit() and 1 <= int(low[1:]) <= 24:
        return 111 + int(low[1:])                         # F1 = 112
    if low.startswith("kp_") and low[3:].isdigit():
        return 96 + int(low[3:])                          # numpad 0 = 96
    return 0


class BridgeRuntime(Runtime):
    def __init__(self, folder: Path, program: list[str], handlers: set[str]):
        super().__init__(folder)
        self.program = program
        self.handler_names = {h.lower() for h in handlers}
        self.proc: subprocess.Popen | None = None
        self.lines: queue.Queue = queue.Queue()
        self._serving = False                    # an EVENT is being handled by the program
        self._pending: list = []                 # events raised meanwhile (sent after its DONE)

    # -- process
    def start_program(self):
        if not self.program:
            fatal("GUI Bridge", "No program to run (the published _radlaunch.json names none).")
        try:
            self.proc = subprocess.Popen(self.program, cwd=str(self.folder), stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=None, text=True, encoding="utf-8",
                                         errors="replace", bufsize=1,
                                         # the published (windowed) host: no console window for a console program
                                         creationflags=0x08000000 if os.name == "nt" and getattr(sys, "frozen", False)
                                         else 0)
        except OSError as ex:
            # a published program whose interpreter (dart, perl, ruby, php, node ...) is not installed: say so
            # instead of sitting there with no window
            fatal(f"{self.project.name if getattr(self, 'project', None) else 'Program'} cannot start",
                  missing_runtime_text(self.program[0], ex))
        threading.Thread(target=self._reader, daemon=True).start()
        if DEBUG:
            # IDE debugger (radide/bridgedebug.py): tell it the pid, wait until it has attached and
            # set the breakpoints ("go"), then keep reading control lines ("EVENT obj ev" = simulate)
            print(f"@@RADBRIDGE@@pid|{self.proc.pid}", flush=True)
            sys.stdin.readline()
            self.control: queue.Queue = queue.Queue()

            def ctl():
                for line in sys.stdin:
                    self.control.put(line.strip())
            threading.Thread(target=ctl, daemon=True).start()

    def _poll_control(self):
        try:
            while True:
                cmd, *rest = (self.control.get_nowait().split() or [""])
                if cmd.upper() == "EVENT" and len(rest) >= 2:
                    self.event(rest[0], rest[1])
        except queue.Empty:
            pass
        if self.root is not None:
            self.root.after(100, self._poll_control)

    def _reader(self):
        for line in self.proc.stdout:
            self.lines.put(line.rstrip("\r\n"))
        self.lines.put(None)

    def send(self, text: str):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.write(text + "\n")
                self.proc.stdin.flush()
            except OSError:
                pass

    # -- forms: every event with a handler in the program is forwarded
    def load(self):
        for name in self.project.forms:
            vf = VBForm(self, Form.load(self.project.form_path(name)))
            self.forms[name.lower()] = vf

    def build_form(self, vf: VBForm):
        form = vf.model
        fake, handlers = [], {}
        for c in [None, *form.controls]:
            if c is not None and c.type in ("MenuStrip", "ToolStrip"):
                for it in menu_leaves(c.props.get("Items", [])):
                    h = f"{it['Name']}_Click"
                    if h.lower() in self.handler_names:
                        fake.append(f"    def {h}(")
                        handlers[h] = (it["Name"], "Click")
                continue
            owner = form.name if c is None else c.name
            events = FORM_EVENTS if c is None else CONTROL_TYPES[c.type].all_events()
            for ev in events:
                h = f"{owner}_{ev}"
                if h.lower() in self.handler_names and not (c is None and ev == "Load"):
                    fake.append(f"    def {h}(")
                    handlers[h] = (owner, ev)
        code = self.plugin.generate_designer(form, "\n".join(fake))
        ns = {"__name__": f"bridge_{form.name}", "__file__": str(self.folder / f"{form.name}.py")}
        exec(compile(code, f"<{form.name} designer>", "exec"), ns)
        base = ns[f"{form.name}Designer"]
        runtime = self

        class FormUI(base):
            def __getattr__(self, name):
                if name in handlers:
                    owner, ev = handlers[name]
                    return lambda *a: runtime.event(owner, ev, a[0] if a else None)
                return base.__getattr__(self, name)
        ui = FormUI(None if self.root is None else self.root)
        vf.ui = ui
        if self.root is None:
            self.root = ui.root
        else:
            ui.root.withdraw()
        ui.root.protocol("WM_DELETE_WINDOW", lambda: self.close_form(vf))

    def fire(self, vf, owner, event, *args):
        name = vf.name if owner == "Form" else owner
        if f"{name}_{event}".lower() in self.handler_names:
            self.event(name, event, None)

    # -- events
    def event(self, owner: str, ev: str, e=None):
        # an event raised while the program's handler is running (e.g. CALL rate1 Reset -> ValueChanged of a
        # component package control) is sent after DONE: the program is waiting for the CALL's answer
        if getattr(self, "_serving", False):
            self._pending.append((owner, ev, e))
            return None
        args = ""
        if e is not None and hasattr(e, "X"):
            # a control character as KeyChar (Return = CR, Tab ...) would break the line protocol: leave it out
            # like the native runtimes do; KeyCode is the numeric Windows virtual-key code (13 = Enter, 27 = Esc,
            # 65 = A ...) the clients parse as a number, like the native (radforms / WinForms / Swing) paths
            char = "".join(ch for ch in str(e.KeyChar or "") if ch >= " " and ch != "\x7f")
            args = f"{e.X} {e.Y} {e.Button} {vk_code(e)} {char}".strip()
        self.send(f"EVENT {owner} {ev} {args}".rstrip())
        self._serving = True
        try:
            r = self.serve()
        finally:
            self._serving = False
        pending, self._pending = list(getattr(self, "_pending", [])), []
        for o, v, x in pending:
            self.event(o, v, x)
        return r

    def serve(self):
        """Handle commands until the program says DONE (or exits)."""
        while True:
            try:
                line = self.lines.get(timeout=None if DEBUG else 30)     # paused at a breakpoint: wait
            except queue.Empty:
                print("[bridge] the program did not answer within 30 s", file=sys.stderr, flush=True)
                return None
            if line is None:
                self.end()
                return None
            # "ESC <command>": the client escaped \\ \n \r in the values (multi-line text) and wants the
            # answer escaped the same way; without it an answer is kept on one line (newlines -> spaces)
            esc = line.startswith("ESC ")
            if esc:
                line = unescape_line(line[4:])
            reply = (lambda s: self.send(escape_line(s))) if esc else (lambda s: self.send(one_line(s)))
            cmd, _, rest = line.partition(" ")
            up = cmd.upper()
            try:
                if up == "DONE":
                    return None
                if up == "END":
                    self.send("QUIT")
                    self.end()
                    return None
                if up == "SET":
                    obj, prop, value = (rest.split(" ", 2) + ["", ""])[:3]
                    target = self.resolve_obj(obj)
                    if prop.lower() == "cancel" and isinstance(target, VBForm):
                        target._close_cancel = to_bool(value)     # FormClosing: keep the form open
                    else:
                        target.vb_set(prop.lower(), value)
                elif up == "GET":
                    obj, prop = (rest.split(" ", 1) + [""])[:2]
                    target, prop = self.resolve_obj(obj), prop.strip().lower()
                    if prop == "color" and getattr(target, "type", "") == "ColorDialog":
                        reply(str(target.w.Color))      # "#RRGGBB" like the native runtimes (VB code gets a number)
                    else:
                        reply(to_str(target.vb_get(prop)))
                elif up == "CALL":
                    obj, method, arg = (rest.split(" ", 2) + ["", ""])[:3]
                    args = [a for a in arg.split("\t")] if arg else []
                    target = self.resolve_obj(obj)
                    if isinstance(target, VBForm):
                        reply(self.form_call(target, method.lower(), args))
                    else:
                        reply(to_str(target.vb_call(method.lower(), args)))
                elif up == "MSGBOX":
                    reply(str(self.msgbox(rest, 0, "")))
                elif up == "INPUT":
                    reply(self.inputbox(rest, "", ""))
                elif up in ("SHOW", "HIDE"):
                    vf = self.forms[rest.strip().lower()]
                    if up == "HIDE":
                        self.release_grab(vf)
                    vf.vb_call(up.lower(), [])
                else:
                    print(line, flush=True)            # plain program output
            except Exception as ex:  # noqa: BLE001 - report and keep the program alive
                print(f"[bridge] {line!r}: {ex}", file=sys.stderr, flush=True)
                if up in ("GET", "CALL", "INPUT", "MSGBOX"):
                    self.send("")

    def form_call(self, vf, method: str, args) -> str:
        """CALL <Form> <method>. ShowDialog shows the form modally for the user (the other forms do not take
        mouse / keyboard input until it is hidden or closed) but answers at once: the program is blocked
        while it waits for an answer, so a blocking ShowDialog could never get the dialog's own events.
        Write the dialog's result handling in its OK / Cancel handlers (works the same in a native build)."""
        if method in ("showdialog", "showmodal"):
            vf.load()
            vf.vb_call("show", [])
            root = vf.ui.root
            if root is not self.root:
                try:
                    root.transient(self.root)
                    root.grab_set()
                except tk.TclError:
                    pass
            return ""
        if method in ("hide", "unload", "close"):
            self.release_grab(vf)
            if method == "close":
                method = "unload"
        return to_str(vf.vb_call(method, args))

    @staticmethod
    def release_grab(vf):
        try:
            if vf.loaded and vf.ui.root.grab_current() is not None:
                vf.ui.root.grab_release()
        except Exception:  # noqa: BLE001
            pass

    def resolve_obj(self, path: str):
        parts = path.split(".")
        if parts[0].lower() in self.forms:
            vf = self.forms[parts[0].lower()]
            vf.load()
            return vf if len(parts) == 1 else vf.vb_get(parts[1].lower())
        for vf in self.forms.values():
            if vf.loaded and vf.vb_has(parts[0].lower()):
                return vf.vb_get(parts[0].lower())
        glob = self.global_object(parts[0].lower())
        if glob is not None:            # GET Screen Width / CALL Clipboard SetText / GET App Path
            return glob
        raise KeyError(f"unknown object '{path}'")

    def global_object(self, name: str):
        """The VB global objects App, Screen and Clipboard (radide/runtimes/vbrun.py) for the bridge languages."""
        from .vbrun import App, Clipboard, Screen
        cls = {"app": App, "screen": Screen, "clipboard": Clipboard}.get(name)
        if cls is None:
            return None
        cache = self.__dict__.setdefault("_globals", {})
        if name not in cache:
            cache[name] = cls(self)
        return cache[name]

    def close_form(self, vf):
        # FormClosing: the program cancels with SET <Form> Cancel True (radforms' rad_set / Set / rad.set) or
        # e.Cancel = true (C# / Java clients send that SET after the handler) - like the native runtimes
        vf._close_cancel = False
        if f"{vf.name}_FormClosing".lower() in self.handler_names:
            self.event(vf.name, "FormClosing")
        if getattr(vf, "_close_cancel", False):
            vf._close_cancel = False
            return
        self.unload(vf, events=False)
        if f"{vf.name}_FormClosed".lower() in self.handler_names:
            self.event(vf.name, "FormClosed")

    def end(self):
        if self.proc and self.proc.poll() is None:
            self.send("QUIT")
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        super().end()

    def run(self):
        self.load()
        self.start_program()
        start = self.forms[(self.project.startup or self.project.forms[0]).lower()]
        self.startup_form = start
        start.load()
        start.vb_call("show", [])     # Load was sent by VBForm.load()
        if DEBUG:
            self._poll_control()
        self.root.mainloop()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    folder = Path(argv[0]).absolute()      # not resolve(): a deep project runs through its short alias
    build = None
    if "--build" in argv:
        build = argv[argv.index("--build") + 1]
    program = argv[argv.index("--") + 1:] if "--" in argv else []
    handlers = set(filter(None, os.environ.get("RAD_HANDLERS", "").split(",")))
    note = os.environ.get("RAD_HOST_NOTE", "")
    if note and "console program" not in note:   # why the native forms host (radbridge.exe) is not used
        print(f"[forms host] Python / Tk host: {note}", flush=True)
    try:        # console mode: a project without forms (its own main) runs as a plain console program
        from ..model import Project
        console = not Project.load(folder).forms
    except Exception:  # noqa: BLE001 - no/invalid project file: keep the GUI Bridge behaviour
        console = False
    if build:
        print(f"------ Build: {build}", flush=True)
        cwd, cmd = str(folder), build
        if os.name == "nt" and cwd.startswith("\\\\"):
            # a project on a network share: cmd.exe refuses a UNC working folder (it builds in C:\Windows) -
            # pushd maps a temporary drive letter for the build, popd removes it (success / failure kept)
            cmd = f'pushd "{cwd}" && ({build}) && (popd & exit /b 0) || (popd & exit /b 1)'
            cwd = os.environ.get("SystemRoot", r"C:\Windows")
        r = subprocess.run(cmd if os.name == "nt" else shlex.split(cmd), cwd=cwd, shell=os.name == "nt",
                           capture_output=True)
        # bytes: a compiler may answer in UTF-8, the OEM (cp720 ...) or the ANSI code page (cp1256 ...) -
        # text=True would decode with the ANSI code page and crash on bytes it does not define
        from ..console_text import decode
        out = (decode(r.stdout) + decode(r.stderr)).strip()
        if out:
            print(out, flush=True)
        if r.returncode != 0:
            print(f"------ Build failed (exit code {r.returncode})", file=sys.stderr, flush=True)
            if console:                 # the errors are in the Output window; no dialog for console programs
                sys.exit(r.returncode)
            try:
                root = tk.Tk()
                root.withdraw()
                from tkinter import messagebox
                messagebox.showerror("Build failed", out[-1500:] or "build failed")
            except tk.TclError:
                pass
            sys.exit(r.returncode)
    if console and program:
        sys.stdout.flush()
        if not DEBUG:
            try:
                sys.exit(subprocess.run(program, cwd=str(folder)).returncode)     # stdin/stdout/stderr inherited
            except OSError as ex:
                fatal("Program cannot start", missing_runtime_text(program[0], ex))
        # debugger (radide/bridgedebug.py): same handshake as the GUI Bridge - pid, then wait for "go"
        proc = subprocess.Popen(program, cwd=str(folder), stdin=subprocess.DEVNULL)
        print(f"@@RADBRIDGE@@pid|{proc.pid}", flush=True)
        sys.stdin.readline()
        sys.exit(proc.wait())
    BridgeRuntime(folder, program, handlers).run()


if __name__ == "__main__":
    main()
