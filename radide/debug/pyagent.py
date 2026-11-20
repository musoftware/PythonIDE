"""RAD IDE Python debug agent.

Usage: python -u pyagent.py <script.py>
Breakpoints come from RADDBG_BP ("file|line;file|line", file = basename).
Speaks the RAD IDE line protocol on stdout/stdin (see languages/base.py).
Runs standalone: uses only the standard library.
"""
import bdb
import json
import os
import re
import queue
import sys
import threading
import traceback

TAG = "@@RADDBG@@"
class _Never:
    """A "stop frame" that matches no frame. It has an f_code because Python 3.12's
    bdb.dispatch_exception reads stopframe.f_code.co_flags when an exception passes a frame."""
    f_code = (lambda: None).__code__


_NEVER = _Never()
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


def has_children(value):
    if isinstance(value, (str, bytes, int, float, complex, bool, type(None))):
        return False
    if isinstance(value, (list, tuple, dict, set, frozenset)):
        return len(value) > 0
    return hasattr(value, "__dict__") and not callable(value) and bool(vars(value))


def children_of(value, limit=300):
    """[(name, child)] of a list / tuple / dict / set / object with attributes."""
    if isinstance(value, dict):
        return [(f"[{short(k, 60)}]", v) for k, v in list(value.items())[:limit]]
    if isinstance(value, (list, tuple)):
        return [(f"[{i}]", v) for i, v in enumerate(value[:limit])]
    if isinstance(value, (set, frozenset)):
        return [(f"<{i}>", v) for i, v in enumerate(list(value)[:limit])]
    try:
        items = list(vars(value).items())
    except TypeError:
        return []
    return [(k, v) for k, v in items[:limit] if not k.startswith("__")]


def parse_bp(text):
    """condition string -> (cond, hit, log); "@@bp {json}" carries hit count / logpoint."""
    if text and text.startswith("@@bp "):
        try:
            d = json.loads(text[5:])
            return d.get("cond") or None, d.get("hit") or "", d.get("log") or ""
        except ValueError:
            pass
    return text or None, "", ""


def hit_ok(hit, count):
    m = re.fullmatch(r"\s*(==|>=|>|%|=)?\s*(\d+)\s*", hit or "")
    if not m:
        return True
    op, n = m.group(1) or "==", int(m.group(2))
    return {"==": count == n, "=": count == n, ">=": count >= n, ">": count > n}.get(op, n > 0 and count % n == 0)


class Agent(bdb.Bdb):
    def __init__(self, root):
        super().__init__()
        self.root = os.path.normcase(os.path.abspath(root))
        self.commands = queue.Queue()
        self.by_name = {}            # basename -> canonical path, for breakpoints
        self.handles = {}            # handle -> value (expandable Locals / Watch), reset at each stop
        self.extra = {}              # (path, line) -> (hit, log)
        self.hits = {}               # (path, line) -> times the breakpoint was reached (condition true)

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
            parts = spec.split("|")
            name, line = parts[0], parts[1]
            cond, hit, log = parse_bp("|".join(parts[2:]))
            path = os.path.join(self.root, name)
            for f in os.listdir(self.root):
                if f.lower() == name.lower():
                    path = os.path.join(self.root, f)
            path = self.canonic(path)
            self.clear_break(path, int(line))
            self.extra.pop((path, int(line)), None)
            self.hits.pop((path, int(line)), None)
            if not remove:
                self.set_break(path, int(line), cond=cond)
                if hit or log:
                    self.extra[(path, int(line))] = (hit, log)
        except Exception as e:  # noqa: BLE001
            send("log", f"breakpoint error: {e}")

    # ----------------------------------------------------------- stopping
    def user_call(self, frame, argument_list):
        pass

    def user_line(self, frame):
        reason = "breakpoint" if self.break_here(frame) else "step"
        if reason == "breakpoint":
            key = (self.canonic(frame.f_code.co_filename), frame.f_lineno)
            self.hits[key] = self.hits.get(key, 0) + 1
            hit, log = self.extra.get(key, ("", ""))
            if hit and not hit_ok(hit, self.hits[key]):
                if self.stopframe is _NEVER or self.stopframe is self.botframe:
                    return                   # running: this hit does not count yet
                reason = "step"
            elif log:
                _out.write(self.format_log(log, frame) + "\n")
                _out.flush()
                if self.stopframe is _NEVER or self.stopframe is self.botframe:
                    return                   # a logpoint prints and goes on
                reason = "step"
        self.interact(frame, reason)

    def format_log(self, message, frame):
        def rep(m):
            try:
                return str(eval(m.group(1), frame.f_globals, frame.f_locals))
            except Exception as e:  # noqa: BLE001
                return f"<{type(e).__name__}: {e}>"
        return re.sub(r"\{([^{}]+)\}", rep, message)

    def handle(self, value):
        """Handle for an expandable value (0 = no children)."""
        if not has_children(value):
            return 0
        h = len(self.handles) + 1
        self.handles[h] = value
        return h

    def user_exception(self, frame, exc_info):
        pass

    def interact(self, frame, reason):
        send("stop", frame.f_code.co_filename, frame.f_lineno, reason)
        self.handles = {}
        for name, value in frame.f_locals.items():
            if name.startswith("__"):
                continue
            send("var", name, type(value).__name__, short(value))
            h = self.handle(value)
            if h:
                send("ref", name, h)
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
            if cmd.startswith("k "):
                try:
                    value = self.handles.get(int(cmd[2:].strip()))
                except ValueError:
                    value = None
                for name, child in children_of(value) if value is not None else []:
                    send("kid", name, type(child).__name__, short(child), self.handle(child))
                send("kend")
                send("wait")
                continue
            if cmd.startswith("w "):
                try:
                    v = eval(cmd[2:], frame.f_globals, frame.f_locals)
                    send("watch", type(v).__name__, self.handle(v), short(v, 2000))
                except Exception as e:  # noqa: BLE001
                    send("watch", "", 0, f"{type(e).__name__}: {e}")
                send("wait")
                continue
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
