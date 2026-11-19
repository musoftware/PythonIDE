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
from .vbinterp import to_str
from .vbrun import Runtime, VBForm

DEBUG = bool(os.environ.get("RAD_BRIDGE_DEBUG"))      # started by the IDE debugger (radide/bridgedebug.py)


class BridgeRuntime(Runtime):
    def __init__(self, folder: Path, program: list[str], handlers: set[str]):
        super().__init__(folder)
        self.program = program
        self.handler_names = {h.lower() for h in handlers}
        self.proc: subprocess.Popen | None = None
        self.lines: queue.Queue = queue.Queue()

    # -- process
    def start_program(self):
        self.proc = subprocess.Popen(self.program, cwd=str(self.folder), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=None, text=True, encoding="utf-8",
                                     errors="replace", bufsize=1)
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
        args = ""
        if e is not None and hasattr(e, "X"):
            args = f"{e.X} {e.Y} {e.Button} {e.KeyCode} {e.KeyChar}".strip()
        self.send(f"EVENT {owner} {ev} {args}".rstrip())
        return self.serve()

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
                    self.resolve_obj(obj).vb_set(prop.lower(), value)
                elif up == "GET":
                    obj, prop = (rest.split(" ", 1) + [""])[:2]
                    self.send(to_str(self.resolve_obj(obj).vb_get(prop.strip().lower())))
                elif up == "CALL":
                    obj, method, arg = (rest.split(" ", 2) + ["", ""])[:3]
                    args = [a for a in arg.split("\t")] if arg else []
                    self.send(to_str(self.resolve_obj(obj).vb_call(method.lower(), args)))
                elif up == "MSGBOX":
                    self.send(str(self.msgbox(rest, 0, "")))
                elif up == "INPUT":
                    self.send(self.inputbox(rest, "", ""))
                elif up in ("SHOW", "HIDE"):
                    self.forms[rest.strip().lower()].vb_call(up.lower(), [])
                else:
                    print(line, flush=True)            # plain program output
            except Exception as ex:  # noqa: BLE001 - report and keep the program alive
                print(f"[bridge] {line!r}: {ex}", file=sys.stderr, flush=True)
                if up in ("GET", "CALL", "INPUT", "MSGBOX"):
                    self.send("")

    def resolve_obj(self, path: str):
        parts = path.split(".")
        if parts[0].lower() in self.forms:
            vf = self.forms[parts[0].lower()]
            vf.load()
            return vf if len(parts) == 1 else vf.vb_get(parts[1].lower())
        for vf in self.forms.values():
            if vf.loaded and vf.vb_has(parts[0].lower()):
                return vf.vb_get(parts[0].lower())
        raise KeyError(f"unknown object '{path}'")

    def close_form(self, vf):
        if f"{vf.name}_FormClosing".lower() in self.handler_names:
            self.event(vf.name, "FormClosing")
        self.unload(vf, events=False)

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
    folder = Path(argv[0]).resolve()
    build = None
    if "--build" in argv:
        build = argv[argv.index("--build") + 1]
    program = argv[argv.index("--") + 1:] if "--" in argv else []
    handlers = set(filter(None, os.environ.get("RAD_HANDLERS", "").split(",")))
    if build:
        print(f"------ Build: {build}", flush=True)
        r = subprocess.run(build if os.name == "nt" else shlex.split(build), cwd=str(folder), shell=os.name == "nt",
                           capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        if out:
            print(out, flush=True)
        if r.returncode != 0:
            print(f"------ Build failed (exit code {r.returncode})", file=sys.stderr, flush=True)
            try:
                root = tk.Tk()
                root.withdraw()
                from tkinter import messagebox
                messagebox.showerror("Build failed", out[-1500:] or "build failed")
            except tk.TclError:
                pass
            sys.exit(r.returncode)
    BridgeRuntime(folder, program, handlers).run()


if __name__ == "__main__":
    main()
