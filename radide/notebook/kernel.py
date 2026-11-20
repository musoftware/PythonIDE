"""Jupyter kernels for the notebook editor (jupyter_client).

* :func:`discover` lists the kernels this machine can run: every Python interpreter that is found (the
  project's ``.venv``, the IDE's own Python, ``py -0p``, PATH, configured interpreters) - each runs
  ``python -m ipykernel_launcher`` - plus every installed Jupyter kernelspec of another language (IRkernel,
  IJulia, ...).
* :class:`KernelSession` runs one kernel.  All ZMQ traffic happens on one worker thread (ZMQ sockets are not
  thread-safe); results come back to the Qt thread as signals.  Requests are built on the Qt thread so the
  caller gets the msg_id at once and can match the replies.
"""
from __future__ import annotations

import ast
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@dataclass
class KernelChoice:
    id: str                          # "py:<path>" | "spec:<name>"
    label: str
    kind: str                        # "python" | "spec"
    python: str = ""                 # interpreter (kind == "python")
    spec_name: str = ""              # kernelspec name (kind == "spec")
    language: str = "python"


# ---------------------------------------------------------------------- discovery
_IPYK_CACHE: dict[str, tuple[bool, str]] = {}


def has_ipykernel(python: str, refresh: bool = False) -> tuple[bool, str]:
    """(installed, version or error) - cached per interpreter."""
    key = os.path.normcase(str(python))
    if not refresh and key in _IPYK_CACHE:
        return _IPYK_CACHE[key]
    try:
        if os.path.normcase(os.path.abspath(python)) == os.path.normcase(os.path.abspath(sys.executable)) \
                and not getattr(sys, "frozen", False):     # release build: sys.executable is a real Python
            import ipykernel
            import jupyter_client
            assert jupyter_client
            res = (True, getattr(ipykernel, "__version__", "?"))
        else:
            out = subprocess.run([python, "-c", "import ipykernel; print(ipykernel.__version__)"],
                                 capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW)
            res = (out.returncode == 0, (out.stdout or out.stderr).strip().splitlines()[-1:][0]
                   if (out.stdout or out.stderr).strip() else "")
    except (OSError, subprocess.SubprocessError, ImportError) as e:
        res = (False, str(e))
    _IPYK_CACHE[key] = res
    return res


def python_version(python: str) -> str:
    try:
        out = subprocess.run([python, "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
                             capture_output=True, text=True, timeout=15, creationflags=NO_WINDOW)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _py_launcher_paths() -> list[str]:
    if os.name != "nt" or not shutil.which("py"):
        return []
    try:
        out = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=15, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return []
    paths = []
    for line in out.stdout.splitlines():
        parts = line.strip().split()
        if parts and parts[-1].lower().endswith(".exe"):
            paths.append(parts[-1])
    return paths


def _venv_python(folder: Path) -> str | None:
    for name in (".venv", "venv", "env"):
        for rel in (("Scripts", "python.exe"), ("bin", "python")):
            p = folder / name / Path(*rel)
            if p.is_file():
                return str(p)
    return None


def discover(start_folder: Path | None = None, extra: list[str] | None = None,
             include_specs: bool = True, quick: bool = False) -> list[KernelChoice]:
    """Kernels to offer, the best first (a venv next to the notebook, then the IDE's Python).
    *quick* skips the slower searches (``py -0p``, PATH)."""
    seen: set[str] = set()
    out: list[KernelChoice] = []

    def add_py(path: str | None, label: str):
        if not path:
            return
        try:
            rp = str(Path(path).resolve())
        except OSError:
            return
        key = os.path.normcase(rp)
        if key in seen or not Path(rp).is_file() or "windowsapps" in key:
            return
        seen.add(key)
        out.append(KernelChoice(f"py:{rp}", label, "python", python=rp))

    if start_folder is not None:
        f = Path(start_folder)
        for _ in range(4):
            vp = _venv_python(f)
            if vp:
                add_py(vp, f"Python ({f.name}{os.sep}{Path(vp).parents[1].name})")
            if f.parent == f:
                break
            f = f.parent
    add_py(sys.executable, f"Python {sys.version_info.major}.{sys.version_info.minor} (RAD IDE)")
    for p in extra or []:
        add_py(p, f"Python ({Path(p).parent.name})")
    for p in ([] if quick else _py_launcher_paths()):
        add_py(p, f"Python ({Path(p).parent.name})")
    for name in ([] if quick else ("python", "python3")):
        add_py(shutil.which(name), f"Python ({name} on PATH)")
    if include_specs:
        try:
            from jupyter_client.kernelspec import KernelSpecManager
            for name, info in sorted(KernelSpecManager().get_all_specs().items()):
                spec = info.get("spec") or {}
                if name == "python3" and (spec.get("argv") or [""])[0] in ("python", "python3"):
                    continue                           # = the IDE's Python, already listed
                out.append(KernelChoice(f"spec:{name}", f"{spec.get('display_name', name)} (Jupyter kernel)",
                                        "spec", spec_name=name, language=(spec.get("language") or "").lower()))
        except Exception:  # noqa: BLE001 - jupyter_client missing / broken specs
            pass
    return out


def choice_from_id(cid: str) -> KernelChoice | None:
    if cid.startswith("py:"):
        p = cid[3:]
        return KernelChoice(cid, f"Python ({Path(p).parent.name})", "python", python=p) if Path(p).is_file() \
            else None
    if cid.startswith("spec:"):
        return KernelChoice(cid, cid[5:], "spec", spec_name=cid[5:], language="")
    return None


def install_ipykernel_command(python: str) -> list[str]:
    return [python, "-m", "pip", "install", "--disable-pip-version-check", "ipykernel"]


# ---------------------------------------------------------------------- variables helper (Python kernels)
VARS_HELPER = r'''
try:   # runtime completions (fast); static analysis comes from pylsp in the IDE
    get_ipython().Completer.use_jedi = False
except Exception:
    pass

def _rad_vars(_limit=200):
    import json as _j, types as _t
    _ip = get_ipython()
    _hidden = getattr(_ip, 'user_ns_hidden', {})
    _out = []
    for _k, _v in list(_ip.user_ns.items()):
        if _k.startswith('_') or _k in _hidden or _k in ('In', 'Out', 'exit', 'quit', 'get_ipython'):
            continue
        if isinstance(_v, (_t.ModuleType, _t.FunctionType, _t.BuiltinFunctionType, _t.MethodType, type)):
            continue
        _tn = type(_v).__name__
        _size = ''
        try:
            _sh = getattr(_v, 'shape', None)
            if isinstance(_sh, tuple):
                _size = ' x '.join(str(_x) for _x in _sh)
            elif hasattr(_v, '__len__'):
                _size = str(len(_v))
        except Exception:
            pass
        try:
            _r = repr(_v)
        except Exception as _e:
            _r = '<repr failed: %s>' % _e
        if len(_r) > _limit:
            _r = _r[:_limit] + '...'
        _out.append([_k, _tn, _size, ' '.join(_r.split())])
        if len(_out) >= 500:
            break
    return _j.dumps(_out)
'''


def parse_vars(reply_content: dict) -> list | None:
    """The ``_rad_vars()`` user expression of an execute_reply -> [[name, type, size, value], ...]."""
    import json
    ue = (reply_content.get("user_expressions") or {}).get("v") or {}
    if ue.get("status") != "ok":
        return None
    txt = ((ue.get("data") or {}).get("text/plain")) or ""
    try:
        return json.loads(ast.literal_eval(txt))
    except (ValueError, SyntaxError):
        return None


# ---------------------------------------------------------------------- session
class KernelSession(QObject):
    """One running kernel.  Signals arrive on the Qt thread."""
    statusChanged = pyqtSignal(str)          # starting | idle | busy | restarting | dead | stopped | error
    started = pyqtSignal(dict)               # kernel_info_reply content (language_info ...)
    failed = pyqtSignal(str)                 # could not start
    iopub = pyqtSignal(dict)                 # every IOPub message (msg_type, parent_header, content)
    shellReply = pyqtSignal(dict)            # execute / complete / inspect replies
    inputRequested = pyqtSignal(str, bool)   # prompt, password  -> answer with send_input()
    restarted = pyqtSignal()

    def __init__(self, choice: KernelChoice, cwd: Path | None = None, session_name: str = "", parent=None):
        super().__init__(parent)
        self.choice = choice
        self.cwd = str(cwd) if cwd else None
        self.session_name = session_name
        self.km = None
        self.kc = None
        self.kernel_info: dict = {}
        self.status = "stopped"
        self._q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._session = None                  # jupyter_client.session.Session (builds messages)
        self.last_error = ""

    # ------------------------------------------------------------ public API (Qt thread)
    @property
    def language(self) -> str:
        li = self.kernel_info.get("language_info") or {}
        return (li.get("name") or self.choice.language or "python").lower()

    @property
    def is_python(self) -> bool:
        return self.language == "python"

    def start(self) -> None:
        if self._thread is not None:
            return
        from jupyter_client.session import Session
        self._session = Session(username="radide")     # builds request headers; the client signs on send
        self._set_status("starting")
        self._thread = threading.Thread(target=self._run, name="rad-kernel", daemon=True)
        self._thread.start()

    def execute(self, code: str, silent: bool = False, user_expressions: dict | None = None,
                store_history: bool | None = None, allow_stdin: bool = True) -> str:
        content = {"code": code, "silent": silent, "store_history": (not silent) if store_history is None
                   else store_history, "user_expressions": user_expressions or {}, "allow_stdin": allow_stdin,
                   "stop_on_error": not silent}
        return self._send("shell", "execute_request", content)

    def complete(self, code: str, cursor_pos: int) -> str:
        return self._send("shell", "complete_request", {"code": code, "cursor_pos": cursor_pos})

    def inspect(self, code: str, cursor_pos: int, detail_level: int = 0) -> str:
        return self._send("shell", "inspect_request", {"code": code, "cursor_pos": cursor_pos,
                                                       "detail_level": detail_level})

    def send_input(self, text: str) -> None:
        self._q.put(("input", text))

    def interrupt(self) -> None:
        self._q.put(("interrupt", None))

    def restart(self) -> None:
        self._set_status("restarting")
        self._q.put(("restart", None))

    def shutdown(self, wait: float = 6.0) -> None:
        if self._thread is None:
            return
        self._q.put(("shutdown", None))
        self._thread.join(wait)
        if self._thread.is_alive():                       # last resort: kill the process we started
            self._stop.set()
            proc = getattr(getattr(self.km, "provisioner", None), "process", None)
            try:
                if proc is not None:
                    proc.kill()
            except Exception:  # noqa: BLE001
                pass
            self._thread.join(2)
        self._thread = None
        self._set_status("stopped")

    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and self.status not in ("dead", "stopped")

    # ------------------------------------------------------------ internals
    def _set_status(self, s: str) -> None:
        self.status = s
        self.statusChanged.emit(s)

    def _send(self, channel: str, msg_type: str, content: dict) -> str:
        msg = self._session.msg(msg_type, content)      # own Session: msg_id counters are not thread-safe
        self._q.put(("send", (channel, msg)))
        return msg["header"]["msg_id"]

    def _env(self) -> dict:
        env = dict(os.environ)
        for k in ("PYTHONHOME", "VIRTUAL_ENV", "MPLBACKEND", "PYTHONSTARTUP", "QT_QPA_PLATFORM",
                  "QTWEBENGINE_CHROMIUM_FLAGS", "QT_FORCE_STDERR_LOGGING"):
            env.pop(k, None)
        if self.choice.kind == "python":
            env.pop("PYTHONPATH", None)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
        if self.session_name:
            env["JPY_SESSION_NAME"] = self.session_name
        return env

    def _make_manager(self):
        from jupyter_client import KernelManager
        if self.choice.kind == "python":
            from jupyter_client.kernelspec import KernelSpec, KernelSpecManager

            spec = KernelSpec(argv=[self.choice.python, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                              display_name=self.choice.label, language="python", interrupt_mode="signal",
                              env={}, metadata={})

            class _OneSpec(KernelSpecManager):
                def get_kernel_spec(self, kernel_name, *a, **k):
                    return spec
            km = KernelManager(kernel_name="radide-python", kernel_spec_manager=_OneSpec())
        else:
            km = KernelManager(kernel_name=self.choice.spec_name)
        km.shutdown_wait_time = 3.0
        return km

    def _connect(self):
        kc = self.km.blocking_client()
        kc.allow_stdin = True
        kc.start_channels()
        kc.wait_for_ready(timeout=90)
        self.kc = kc
        msg = self.km.session.msg("kernel_info_request", {})
        kc.shell_channel.send(msg)
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                rep = kc.shell_channel.get_msg(timeout=0.5)
            except queue.Empty:
                continue
            if rep.get("parent_header", {}).get("msg_id") == msg["header"]["msg_id"]:
                return rep.get("content") or {}
        return {}

    def _run(self) -> None:                               # worker thread
        import zmq
        try:
            self.km = self._make_manager()
            self.km.start_kernel(cwd=self.cwd, env=self._env())
            self.kernel_info = self._connect()
        except Exception as e:  # noqa: BLE001 - missing interpreter, broken kernelspec, timeout ...
            self.last_error = f"{type(e).__name__}: {e}"
            self._cleanup()
            self.failed.emit(self.last_error)
            self._set_status("dead")
            return
        self.status = "idle"                       # before started: the Qt side may queue work at once
        self.started.emit(self.kernel_info)
        self.statusChanged.emit("idle")
        poller = None
        sockets = ()
        last_alive = time.time()
        while not self._stop.is_set():
            # commands from the Qt thread
            try:
                while True:
                    cmd, arg = self._q.get_nowait()
                    if cmd == "send":
                        ch, msg = arg
                        (self.kc.shell_channel if ch == "shell" else self.kc.control_channel).send(msg)
                    elif cmd == "input":
                        self.kc.input(arg)
                    elif cmd == "interrupt":
                        try:
                            self.km.interrupt_kernel()
                        except Exception as e:  # noqa: BLE001
                            self.iopub.emit({"msg_type": "rad_log", "content": {"text": f"interrupt failed: {e}"},
                                             "parent_header": {}})
                    elif cmd == "restart":
                        try:
                            self.kc.stop_channels()
                            self.km.restart_kernel(now=True, env=self._env())
                            self.kernel_info = self._connect() or self.kernel_info
                            poller = None
                            self.status = "idle"
                            self.restarted.emit()
                            self.statusChanged.emit("idle")
                        except Exception as e:  # noqa: BLE001
                            self.last_error = f"restart failed: {e}"
                            self.failed.emit(self.last_error)
                            self._set_status("dead")
                    elif cmd == "shutdown":
                        self._cleanup(graceful=True)
                        return
            except queue.Empty:
                pass
            if self.kc is None:
                time.sleep(0.05)
                continue
            if poller is None:
                poller = zmq.Poller()
                sockets = (self.kc.iopub_channel.socket, self.kc.shell_channel.socket, self.kc.stdin_channel.socket)
                for s in sockets:
                    poller.register(s, zmq.POLLIN)
            try:
                events = dict(poller.poll(40))
            except zmq.ZMQError:
                poller = None
                time.sleep(0.05)
                continue
            if events:
                for _ in range(200):                     # drain what is ready, then look at commands again
                    got = False
                    for ch, sig in ((self.kc.iopub_channel, "iopub"), (self.kc.shell_channel, "shell"),
                                    (self.kc.stdin_channel, "stdin")):
                        try:
                            if not ch.msg_ready():
                                continue
                            msg = ch.get_msg(timeout=0)
                        except (queue.Empty, zmq.ZMQError):
                            continue
                        except Exception as e:  # noqa: BLE001 - undecodable message
                            self.iopub.emit({"msg_type": "rad_log", "content": {"text": str(e)}, "parent_header": {}})
                            continue
                        got = True
                        self._dispatch(sig, msg)
                    if not got:
                        break
            if time.time() - last_alive > 1.5:
                last_alive = time.time()
                try:
                    if not self.km.is_alive() and self.status != "restarting":
                        self._set_status("dead")
                except Exception:  # noqa: BLE001
                    pass
        self._cleanup()

    def _dispatch(self, channel: str, msg: dict) -> None:
        slim = {"msg_type": msg.get("msg_type") or msg.get("header", {}).get("msg_type"),
                "parent_header": msg.get("parent_header") or {}, "content": msg.get("content") or {},
                "metadata": msg.get("metadata") or {}}
        if channel == "iopub":
            if slim["msg_type"] == "status":
                st = slim["content"].get("execution_state")
                if st in ("busy", "idle"):
                    self.status = st
                    self.statusChanged.emit(st)
            self.iopub.emit(slim)
        elif channel == "shell":
            self.shellReply.emit(slim)
        elif channel == "stdin" and slim["msg_type"] == "input_request":
            c = slim["content"]
            self.inputRequested.emit(c.get("prompt", ""), bool(c.get("password")))

    def _cleanup(self, graceful: bool = False) -> None:
        try:
            if self.kc is not None:
                self.kc.stop_channels()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self.km is not None and self.km.has_kernel:
                self.km.shutdown_kernel(now=not graceful)
        except Exception:  # noqa: BLE001
            try:
                self.km.shutdown_kernel(now=True)
            except Exception:  # noqa: BLE001
                pass
        try:
            if self.km is not None:
                self.km.cleanup_resources()
        except Exception:  # noqa: BLE001
            pass
        self.kc = None
