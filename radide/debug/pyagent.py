"""RAD IDE Python debug agent.

Usage: python -u pyagent.py <script.py>
Breakpoints come from RADDBG_BP ("file|line;file|line", file = basename).
Speaks the RAD IDE line protocol on stdout/stdin (see languages/base.py).
Runs standalone: uses only the standard library.
"""
import bdb
import os
import queue
import sys
import threading
import traceback

TAG = "@@RADDBG@@"
_NEVER = object()   # a "stop frame" that matches no frame
_out = sys.__stdout__


def send(*fields):
    text = "|".join(str(f).replace("\n", "\\n").replace("|", "¦") for f in fields)
    _out.write(f"{TAG}{text}\n")
    _out.flush()


def short(value, limit=200):
    try:
        r = repr(value)
    except Exception as e:  # noqa: BLE001
        r = f"<repr failed: {e}>"
    return r if len(r) <= limit else r[:limit] + "..."


class Agent(bdb.Bdb):
    def __init__(self, root):
        super().__init__()
        self.root = os.path.normcase(os.path.abspath(root))
        self.commands = queue.Queue()
        self.by_name = {}            # basename -> canonical path, for breakpoints

    # ----------------------------------------------------------- filtering
    def in_project(self, filename):
        f = os.path.normcase(os.path.abspath(filename))
        return f.startswith(self.root) and not f.endswith("pyagent.py")

    def stop_here(self, frame):
        return self.in_project(frame.f_code.co_filename) and super().stop_here(frame)

    def set_continue(self):
        # unlike bdb, keep tracing so breakpoints added later still work
        self._set_stopinfo(self.botframe or _NEVER, None, -1)

    def start(self, code, globs):
        """Like Bdb.run but starts *running* (stops only at breakpoints)."""
        self.reset()
        self._set_stopinfo(_NEVER, None, -1)
        sys.settrace(self.trace_dispatch)
        try:
            exec(code, globs)
        except bdb.BdbQuit:
            pass
        finally:
            self.quitting = True
            sys.settrace(None)

    # ----------------------------------------------------------- breakpoints
    def add_bp(self, spec, remove=False):
        try:
            name, line = spec.rsplit("|", 1)
            path = os.path.join(self.root, name)
            for f in os.listdir(self.root):
                if f.lower() == name.lower():
                    path = os.path.join(self.root, f)
            path = self.canonic(path)
            if remove:
                self.clear_break(path, int(line))
            else:
                self.set_break(path, int(line))
        except Exception as e:  # noqa: BLE001
            send("log", f"breakpoint error: {e}")

    # ----------------------------------------------------------- stopping
    def user_call(self, frame, argument_list):
        pass

    def user_line(self, frame):
        reason = "breakpoint" if self.break_here(frame) else "step"
        self.interact(frame, reason)

    def user_exception(self, frame, exc_info):
        pass

    def interact(self, frame, reason):
        send("stop", frame.f_code.co_filename, frame.f_lineno, reason)
        for name, value in frame.f_locals.items():
            if name.startswith("__"):
                continue
            send("var", name, type(value).__name__, short(value))
            if name == "self":
                for k, v in list(vars(value).items())[:60] if hasattr(value, "__dict__") else []:
                    if not k.startswith("_"):
                        send("var", f"self.{k}", type(v).__name__, short(v))
        f = frame
        while f is not None:
            if self.in_project(f.f_code.co_filename):
                send("frame", f.f_code.co_name, f.f_code.co_filename, f.f_lineno)
            f = f.f_back
        send("wait")
        while True:
            cmd = self.commands.get()
            if cmd == "c":
                self.set_continue()
                return
            if cmd == "s":
                self.set_step()
                return
            if cmd == "n":
                self.set_next(frame)
                return
            if cmd == "o":
                self.set_return(frame)
                return
            if cmd == "q":
                self.set_quit()
                os._exit(0)
            if cmd.startswith("e "):
                try:
                    try:
                        result = short(eval(cmd[2:], frame.f_globals, frame.f_locals), 2000)
                    except SyntaxError:
                        exec(cmd[2:], frame.f_globals, frame.f_locals)
                        result = "OK"
                except Exception as e:  # noqa: BLE001
                    result = f"{type(e).__name__}: {e}"
                send("eval", result)
                send("wait")


def reader(agent):
    for line in sys.__stdin__:
        line = line.rstrip("\r\n").lstrip("﻿")
        if line.startswith("b "):
            agent.add_bp(line[2:])
        elif line.startswith("B "):
            agent.add_bp(line[2:], remove=True)
        elif line:
            agent.commands.put(line)
    agent.commands.put("c")


def main():
    script = os.path.abspath(sys.argv[1])
    root = os.environ.get("RADDBG_ROOT") or os.path.dirname(script)
    sys.argv = [script] + sys.argv[2:]
    sys.path.insert(0, os.path.dirname(script))
    agent = Agent(root)
    for spec in filter(None, os.environ.get("RADDBG_BP", "").split(";")):
        agent.add_bp(spec)
    threading.Thread(target=reader, args=(agent,), daemon=True).start()
    with open(script, encoding="utf-8") as fh:
        code = compile(fh.read(), script, "exec")
    globs = {"__name__": "__main__", "__file__": script, "__builtins__": __builtins__}
    try:
        agent.start(code, globs)
    except SystemExit:
        pass
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    send("done")


if __name__ == "__main__":
    main()
