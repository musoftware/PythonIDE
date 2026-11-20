"""Shared plumbing of the "others" foreign adapters (Qt .ui, Java IDEs, CMake, VS Code
folders, Python projects) - opened IN PLACE: the native files stay authoritative.

* ``ForeignAdapter``  - one native project (pom.xml, CMakeLists.txt, .vscode, ...): its source
  files, its forms (``FormBinding``: native form file <-> neutral ``Form``), run targets and
  build/run/debug commands with the project's own toolchain.
* ``ForeignProject``  - a ``radide.model.Project`` that is NEVER written as project.radproj:
  ``form_path()`` points to a neutral-model copy under the IDE state folder
  (``%APPDATA%\\RADIDE\\foreign\\<hash>``) and ``save()`` writes changed forms BACK to their
  native files through the binding's writer (which preserves what it does not understand).
* ``ForeignPlugin``   - a per-project language plugin (registered lazily when the project
  opens) that gives the IDE code/designer files and builds/runs/debugs with the adapter.
* ``show_projects(win, projects, ...)`` - puts foreign projects into the main window as an
  implicit solution (nothing written into the user's folder).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ..languages.base import LanguagePlugin, RunSpec
from ..model import Form, Project

# ---------------------------------------------------------------- state folder


def state_root() -> Path:
    env = os.environ.get("RADIDE_FOREIGN_STATE")
    if env:
        return Path(env)
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "RADIDE" / "foreign"


def state_dir(native: Path) -> Path:
    """IDE-only state of a native project (never inside the user's folder)."""
    key = os.path.normcase(str(Path(native).resolve()))
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(native).name)[:40] or "project"
    d = state_root() / f"{safe}-{h}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_text_keep(path: Path) -> tuple[str, str, str]:
    """(text, encoding, newline) of a native text file, so it can be written back identically."""
    raw = Path(path).read_bytes()
    enc = "utf-8"
    if raw.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError:
        enc = "cp1252"
        text = raw.decode(enc, errors="replace")
    nl = "\r\n" if b"\r\n" in raw else "\n"
    return text.replace("\r\n", "\n"), enc, nl


def write_text_keep(path: Path, text: str, enc: str = "utf-8", nl: str = "\n") -> bool:
    """Write *text* ("\\n" newlines) with the file's original encoding/newlines.
    Returns False (and writes nothing) when the bytes would not change."""
    data = text.replace("\r\n", "\n")
    if nl != "\n":
        data = data.replace("\n", nl)
    raw = data.encode(enc, errors="replace")
    p = Path(path)
    try:
        if p.exists() and p.read_bytes() == raw:
            return False
    except OSError:
        pass
    p.write_bytes(raw)
    return True


def load_jsonc(path: Path):
    """JSON with comments and trailing commas (VS Code files)."""
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    clean = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    return json.loads(clean) if clean.strip() else {}


# ---------------------------------------------------------------- tools


def _newest(paths: list[Path]) -> str:
    paths = [p for p in paths if p.exists()]
    return str(sorted(paths)[-1]) if paths else ""


def local_tools() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE" / "tools"


def mingw_bin() -> str:
    p = Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE" / "toolchains" / "mingw64" / "bin"
    if (p / "gcc.exe").exists():
        return str(p)
    g = shutil.which("gcc")
    return str(Path(g).parent) if g else ""


def find_cmake() -> str:
    return shutil.which("cmake") or _newest(list(local_tools().glob("cmake/*/bin/cmake.exe")))


def find_gdb() -> str:
    g = shutil.which("gdb")
    if g:
        return g
    mb = mingw_bin()
    return str(Path(mb) / "gdb.exe") if mb and (Path(mb) / "gdb.exe").exists() else ""


def find_java(tool: str = "java") -> str:
    exe = tool + (".exe" if os.name == "nt" else "")
    jh = os.environ.get("JAVA_HOME")
    if jh and (Path(jh) / "bin" / exe).exists():
        return str(Path(jh) / "bin" / exe)
    w = shutil.which(tool)
    if w:
        return w
    return _newest(list(local_tools().glob(f"jdk*/bin/{exe}")) + list(local_tools().glob(f"jdk*/*/bin/{exe}")))


def find_maven(root: Path | None = None) -> str:
    if root is not None:
        for n in ("mvnw.cmd", "mvnw.bat") if os.name == "nt" else ("mvnw",):
            if (Path(root) / n).exists():
                return str(Path(root) / n)
    return shutil.which("mvn") or _newest(list(local_tools().glob("maven/*/bin/mvn.cmd")))


def find_gradle(root: Path | None = None) -> str:
    if root is not None:
        for n in ("gradlew.bat",) if os.name == "nt" else ("gradlew",):
            if (Path(root) / n).exists():
                return str(Path(root) / n)
    w = shutil.which("gradle")
    if w:
        return w
    dists = Path.home() / ".gradle" / "wrapper" / "dists"
    return _newest(list(dists.glob("gradle-*/*/gradle-*/bin/gradle.bat"))
                   + list(local_tools().glob("gradle/*/bin/gradle.bat")))


def tool_env(extra_path: list[str] | None = None) -> dict:
    """Environment for native tools: MinGW (gcc/gdb/make) and the JDK first on PATH."""
    env = {}
    parts = [p for p in (extra_path or []) if p]
    mb = mingw_bin()
    if mb:
        parts.append(mb)
    jv = find_java("javac")
    if jv:
        parts.append(str(Path(jv).parent))
    if parts:
        env["PATH"] = os.pathsep.join(parts + [os.environ.get("PATH", "")])
    return env


# ---------------------------------------------------------------- data


@dataclass
class Step:
    """One command of a build/run chain."""
    argv: list
    cwd: Path
    env: dict = field(default_factory=dict)
    title: str = ""


class LazyStep(Step):
    """A Step whose argv is computed when it starts (paths known only after a build step)."""

    def __init__(self, fn, cwd, env=None, title=""):
        self._fn = fn
        super().__init__([], Path(cwd), dict(env or {}), title)

    @property
    def argv(self):
        return self._fn()

    @argv.setter
    def argv(self, _v):
        pass


@dataclass
class RunTarget:
    """Something F5 can start: an executable, a Java main class, a Python script, a launch config."""
    name: str
    kind: str                       # "exe" | "java" | "python" | "task" | "launch"
    data: dict = field(default_factory=dict)


class FormBinding:
    """A native form file shown in the designer. Subclasses implement load() and write()."""
    kind = ""

    def __init__(self, name: str, native: Path):
        self.name = name
        self.native = Path(native)
        self.code_path: Path | None = None     # the code file shown by View Code (native)
        self.notes: list[str] = []

    def load(self) -> Form:
        raise NotImplementedError

    def write(self, form: Form) -> list[str]:
        """Write *form* back into the native file(s); returns notes for the log."""
        raise NotImplementedError

    # events (double-click in the designer) - default: no code generation
    def handler_name(self, form: Form, ctrl, event: str) -> str:
        owner = ctrl.name if ctrl is not None else form.name
        return f"{owner}_{event}"

    def find_handler(self, code: str, name: str) -> int:
        for i, line in enumerate(code.splitlines()):
            if re.search(rf"\b{re.escape(name)}\s*\(", line):
                return i
        return -1

    def add_handler(self, code: str, name: str, form: Form, args=None) -> tuple[str, int]:
        return code, max(self.find_handler(code, name), 0)



class ForeignAdapter:
    """A native project. Subclasses fill modules / bindings / targets in scan()."""
    kind = "foreign"
    title = "Foreign project"
    base_language = "python-tk"      # plugin whose keywords/IntelliSense the project's code uses

    def __init__(self, native: Path, root: Path | None = None, name: str = ""):
        self.native = Path(native).resolve()
        self.root = Path(root).resolve() if root is not None else \
            (self.native if self.native.is_dir() else self.native.parent)
        self.name = name or self.root.name
        self.modules: list[str] = []
        self.bindings: dict[str, FormBinding] = {}
        self.targets: list[RunTarget] = []
        self.info: list[str] = []
        self.state = state_dir(self.native)

    # -- scanning
    def scan(self) -> None:
        raise NotImplementedError

    def rel(self, p: Path) -> str:
        try:
            return Path(p).resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    def add_binding(self, b: FormBinding) -> FormBinding:
        name, i = b.name, 2
        while name.lower() in {k.lower() for k in self.bindings}:
            name = f"{b.name}_{i}"
            i += 1
        b.name = name
        self.bindings[name] = b
        return b

    # -- build / run
    def tool(self) -> str:
        return sys.executable

    def build_steps(self, target: RunTarget | None, debug: bool) -> list[Step]:
        return []

    def run_step(self, target: RunTarget, debug: bool) -> Step | None:
        return None

    def debug_session(self, win, target: RunTarget, pre: list[Step]):
        """A session that debugs *target* (after *pre* steps), or None = run without debugger."""
        return None

    def commands(self) -> list[tuple[str, list[Step]]]:
        """Extra commands for the Native menu: (label, steps)."""
        return []

    def target(self, name: str) -> RunTarget | None:
        return next((t for t in self.targets if t.name == name), None) or (self.targets[0] if self.targets else None)


# ---------------------------------------------------------------- the project


def _mtime(p) -> float:
    try:
        return Path(p).stat().st_mtime_ns if p is not None else 0
    except OSError:
        return 0


class ForeignProject(Project):
    """In-memory Project of a native project - project.radproj is never written."""

    def __init__(self, adapter: ForeignAdapter):
        adapter.scan()
        plugin = ForeignPlugin.for_adapter(adapter)
        Project.__init__(self, adapter.root, adapter.name, plugin.id, list(adapter.bindings),
                         adapter.targets[0].name if adapter.targets else "", list(adapter.modules))
        self.adapter = adapter
        self.foreign = True
        self.extra = {"foreign": adapter.kind}
        self._synced: dict[str, str] = {}
        (adapter.state / "forms").mkdir(parents=True, exist_ok=True)
        for name, b in adapter.bindings.items():
            self._materialize(name, b)
        self._load_state()

    # -- forms
    def form_path(self, form_name: str) -> Path:
        return self.adapter.state / "forms" / f"{form_name}.form"

    def missing_forms(self) -> list[str]:
        return [f for f in self.forms if f not in self.adapter.bindings or not self.adapter.bindings[f].native.exists()]

    def _materialize(self, name: str, b: FormBinding) -> None:
        try:
            form = b.load()
        except Exception as e:  # noqa: BLE001 - a broken form must not stop the project
            form = Form()
            form.props["Name"] = name
            form.props["Text"] = f"{name} (could not be read: {e})"
            b.notes.append(f"*** {b.native.name}: {e}")
        form.props["Name"] = name
        text = json.dumps(form.to_dict(), indent=2, ensure_ascii=False)
        self.form_path(name).write_text(text, encoding="utf-8")
        self._synced[name] = text

    def reload_form(self, name: str) -> None:
        b = self.adapter.bindings.get(name)
        if b is not None:
            self._materialize(name, b)

    def sync_forms(self, log=None) -> list[str]:
        """Write every form whose neutral copy changed back to its native file."""
        notes = []
        for name, b in self.adapter.bindings.items():
            p = self.form_path(name)
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            if text == self._synced.get(name):
                continue
            try:
                form = Form.from_dict(json.loads(text))
                before = _mtime(b.code_path)
                notes += b.write(form) or []
                self._synced[name] = text
                if b.code_path is not None and _mtime(b.code_path) != before:
                    cb = getattr(self, "_refresh", None)
                    if cb:
                        cb(b.code_path)
            except Exception as e:  # noqa: BLE001
                notes.append(f"*** {b.native.name}: cannot write back: {e}")
        for n in notes:
            if log:
                log(n)
        return notes

    # -- MainWindow._save_form hook: write the native form file (+ its code file) directly
    def save_form(self, name, form, code, code_changed, form_modified):
        b = self.adapter.bindings.get(name)
        if b is None:
            return None
        if code is not None and code_changed and b.code_path is not None:
            self.write_code(b.code_path, code)
        text = json.dumps(form.to_dict(), indent=2, ensure_ascii=False)
        self.form_path(name).write_text(text, encoding="utf-8")
        if text == self._synced.get(name):
            return None
        before = _mtime(b.code_path)
        try:
            notes = b.write(form) or []
            self._synced[name] = text
        except Exception as e:  # noqa: BLE001
            notes = [f"*** {b.native.name}: cannot write back: {e}"]
        log = getattr(self, "_log", None)
        for n in notes:
            if log:
                log(n)
        if b.code_path is not None and _mtime(b.code_path) != before:
            return self.read_code(b.code_path)       # NetBeans: initComponents() was regenerated
        return None

    # -- code files keep their encoding / BOM / newlines (MainWindow read_code / write_code hooks)
    def read_code(self, path) -> str:
        p = Path(path)
        if not p.exists():
            return ""
        text, enc, nl = read_text_keep(p)
        self._enc = getattr(self, "_enc", {})
        self._enc[os.path.normcase(str(p.resolve()))] = (enc, nl)
        return text

    def write_code(self, path, text: str) -> None:
        p = Path(path)
        key = os.path.normcase(str(p.resolve()))
        default = ("utf-8", chr(10))
        enc, nl = getattr(self, "_enc", {}).get(key) or (read_text_keep(p)[1:] if p.exists() else default)
        write_text_keep(p, text, enc, nl)

    # -- IDE state (never in the user's folder)
    def _state_file(self) -> Path:
        return self.adapter.state / "ide-state.json"

    def _load_state(self) -> None:
        try:
            d = json.loads(self._state_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        st = d.get("startup")
        if st and any(t.name == st for t in self.adapter.targets):
            self.startup = st

    def save(self) -> None:
        self.sync_forms(log=getattr(self, "_log", None))
        data = {"native": str(self.adapter.native), "kind": self.adapter.kind, "startup": self.startup}
        try:
            self._state_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass


# ---------------------------------------------------------------- the plugin


class ForeignPlugin(LanguagePlugin):
    """Per-project plugin: code/designer files of foreign forms + build/run/debug by the adapter."""
    foreign = True
    supports_debug = True

    def __init__(self, adapter: ForeignAdapter):
        self.adapter = adapter
        h = hashlib.sha1(os.path.normcase(str(adapter.native)).encode()).hexdigest()[:8]
        self.id = f"foreign-{adapter.kind}-{h}"
        self.display_name = f"{adapter.title} ({adapter.name})"
        self.code_ext = ""
        try:
            from ..languages import get_plugin
            self.base = get_plugin(adapter.base_language)
        except Exception:  # noqa: BLE001
            self.base = None
        for attr in ("keywords", "builtins", "case_sensitive", "line_comments", "block_comment", "string_quotes"):
            if self.base is not None:
                setattr(self, attr, getattr(self.base, attr))

    @staticmethod
    def for_adapter(adapter: ForeignAdapter) -> "ForeignPlugin":
        from .. import languages
        languages.all_plugins()
        p = ForeignPlugin(adapter)
        languages._PLUGINS[p.id] = p          # lazily: only while a foreign project is open
        return p

    # -- files
    def _binding(self, name):
        return self.adapter.bindings.get(name)

    def code_file(self, form_name: str) -> str:
        b = self._binding(form_name)
        if b is not None and b.code_path is not None:
            return str(b.code_path)
        p = self.adapter.state / "forms" / f"{form_name}.notes.txt"
        if not p.exists():
            native = b.native if b is not None else form_name
            p.write_text(f"# {form_name}: designed from {native}\n"
                         "# This form has no code file of its own in the native project.\n", encoding="utf-8")
        return str(p)

    def designer_file(self, form_name: str) -> str:
        # generated code is written by the binding (FormBinding.write) with the file's own encoding
        # and newlines - the IDE's generic "designer file" goes to the state folder
        return str(self.adapter.state / "forms" / f"{form_name}.generated.txt")

    def generate_designer(self, form: Form, user_code: str) -> str:
        b = self._binding(form.name)
        return f"# {form.name}: the native form file is the designer file ({b.native if b else ''})\n"

    def new_code(self, form: Form, is_startup: bool) -> str:
        return ""

    # -- events
    def handler_for(self, form, ctrl, event):
        b = self._binding(form.name)
        return b.handler_name(form, ctrl, event) if b is not None else super().handler_for(form, ctrl, event)

    def find_handler(self, code: str, name: str) -> int:
        for b in self.adapter.bindings.values():
            return b.find_handler(code, name)
        return -1

    def add_handler(self, code, name, form, args=None):
        b = self._binding(form.name)
        if b is None:
            return code, 0
        return b.add_handler(code, name, form, args)

    def completions(self, *a, **kw):
        return self.base.completions(*a, **kw) if self.base is not None else []

    def calltip(self, *a, **kw):
        return self.base.calltip(*a, **kw) if self.base is not None else None

    # -- run / debug
    def find_interpreter(self, configured: str = "") -> str:
        return self.adapter.tool() or sys.executable

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        t = self.adapter.target(startup_form)
        step = self.adapter.run_step(t, False) if t is not None else None
        if step is None:
            raise RuntimeError(f"{self.adapter.title}: nothing to run (no target)")
        return RunSpec(str(step.argv[0]), [str(a) for a in step.argv[1:]], Path(step.cwd), dict(step.env) or None)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)

    def make_session(self, win, spec, debug: bool):
        """Called by MainWindow._make_session: build steps, then run (or debug) the target."""
        t = self.adapter.target(win.project.startup if win.project is not None else "")
        if t is None:
            return None
        pre = self.adapter.build_steps(t, debug)
        if debug:
            try:
                s = self.adapter.debug_session(win, t, pre)
            except Exception as e:  # noqa: BLE001
                win.log(f"*** {self.adapter.title}: debugger unavailable ({e}) - running without it")
                s = None
            if s is not None:
                return s
            win.log(f"{self.adapter.title}: no debugger for '{t.name}' - running without breakpoints")
        run = self.adapter.run_step(t, debug)
        if run is not None and spec is not None and spec.env:
            run.env = {**(spec.env or {}), **run.env}
        return ChainSession(pre + ([run] if run else []), None, win)


# ---------------------------------------------------------------- sessions

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal  # noqa: E402


def _cmdq(a: str) -> str:
    return f'"{a}"' if (" " in a or "&" in a) and not a.startswith('"') else a


def _qenv(env: dict | None) -> QProcessEnvironment:
    e = QProcessEnvironment.systemEnvironment()
    for k, v in (env or {}).items():
        e.insert(k, str(v))
    return e


class ChainSession(QObject):
    """Runs Steps one after the other (output to the IDE), then hands over to an optional inner
    session made by *factory()* (a debugger). Same signals/methods as radide.debugger.Session."""
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, steps: list[Step], factory=None, parent=None):
        super().__init__(parent)
        self.steps = [s for s in steps if s is not None]
        self.factory = factory
        self.inner = None
        self.proc: QProcess | None = None
        self.paused = False
        self.debug = factory is not None
        self.user_stopped = False
        self._done = False
        self.adapter = "chain"

    def start(self):
        self._next()

    def _next(self):
        if self.user_stopped:
            return self._finish(1)
        if not self.steps:
            if self.factory is None:
                return self._finish(0)
            try:
                self.inner = self.factory()
            except Exception as e:  # noqa: BLE001
                self.failed.emit(str(e))
                return self._finish(1)
            if self.inner is None:
                return self._finish(0)
            for sig in ("output", "stopped", "resumed", "evalResult", "failed"):
                getattr(self.inner, sig).connect(getattr(self, sig).emit)
            self.inner.stopped.connect(lambda _i: setattr(self, "paused", True))
            self.inner.resumed.connect(lambda: setattr(self, "paused", False))
            self.inner.finished.connect(self._finish)
            self.inner.start()
            return None
        step = self.steps.pop(0)
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(str(step.cwd))
        self.proc.setProcessEnvironment(_qenv(step.env))
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._step_done)
        self.proc.errorOccurred.connect(self._error)
        if step.title:
            self.output.emit(f"> {step.title}\n")
        argv = [str(a) for a in step.argv]
        if os.name == "nt" and argv[0].lower().endswith((".cmd", ".bat")):
            argv = ["cmd.exe", "/d", "/s", "/c", " ".join(_cmdq(a) for a in argv)]
        if os.name == "nt" and Path(argv[0]).name.lower() == "cmd.exe" and "/c" in [a.lower() for a in argv[1:4]]:
            # cmd.exe parses its own command line: pass it verbatim (QProcess would add \" escapes)
            i = [a.lower() for a in argv].index("/c")
            self.proc.setProgram(argv[0])
            self.proc.setNativeArguments(" ".join(argv[1:i + 1]) + ' "' + " ".join(argv[i + 1:]) + '"')
            self.proc.start()
            return None
        self.proc.start(argv[0], argv[1:])
        return None

    def _read(self):
        if self.proc is not None:
            self.output.emit(bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace"))

    def _error(self, err):
        if err == QProcess.ProcessError.FailedToStart and self.proc is not None:
            self.failed.emit(f"cannot start {self.proc.program()}")
            self._finish(1)

    def _step_done(self, code, _status):
        self._read()
        if code != 0 or self.user_stopped:
            return self._finish(code or 1)
        self._next()
        return None

    def _finish(self, code):
        if self._done:
            return
        self._done = True
        self.finished.emit(int(code))

    def running(self) -> bool:
        if self._done:
            return False
        return True

    # debugger commands go to the inner session
    def _fwd(self, name, *a):
        f = getattr(self.inner, name, None) if self.inner is not None else None
        return f(*a) if callable(f) else None

    def cont(self):
        self._fwd("cont")

    def step_into(self):
        self._fwd("step_into")

    def step_over(self):
        self._fwd("step_over")

    def step_out(self):
        self._fwd("step_out")

    def evaluate(self, expr):
        self._fwd("evaluate", expr)

    def set_breakpoint(self, *a):
        self._fwd("set_breakpoint", *a)

    def set_break_on_exception(self, on):
        self._fwd("set_break_on_exception", on)

    def children(self, *a):
        self._fwd("children", *a)

    def watch(self, *a):
        self._fwd("watch", *a)

    def send(self, cmd):
        if self.inner is None and self.proc is not None:
            self.proc.write((cmd + "\n").encode())
        else:
            self._fwd("send", cmd)

    def stop(self):
        self.user_stopped = True
        if self.inner is not None:
            self._fwd("stop")
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.proc.kill()
            self.proc.waitForFinished(3000)


class JavaDebugSession(QObject):
    """Starts a JVM with a JDWP agent (suspend=y) and attaches radide.jdwp_engine.JdwpSession."""
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, step: Step, port: int, breakpoints, parent=None):
        super().__init__(parent)
        from ..jdwp_engine import JdwpSession
        self.step, self.port = step, port
        self.dbg = JdwpSession(port, step.cwd, breakpoints, self)
        for sig in ("stopped", "resumed", "evalResult", "failed"):
            getattr(self.dbg, sig).connect(getattr(self, sig).emit)
        self.dbg.output.connect(self.output.emit)
        self.dbg.stopped.connect(lambda _i: setattr(self, "paused", True))
        self.dbg.resumed.connect(lambda: setattr(self, "paused", False))
        self.paused = False
        self.debug = True
        self.user_stopped = False
        self.adapter = "jdwp"
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(str(step.cwd))
        self.proc.setProcessEnvironment(_qenv(step.env))
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._done)
        self._started_dbg = False
        self._fin = False

    def start(self):
        argv = [str(a) for a in self.step.argv]
        self.proc.start(argv[0], argv[1:])
        self._attach()

    def _attach(self):
        if not self._started_dbg:
            self._started_dbg = True
            self.dbg.start()

    def _read(self):
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        text = "\n".join(line for line in text.split("\n") if "Listening for transport" not in line)
        if text:
            self.output.emit(text)

    def _done(self, code, _s):
        self._read()
        try:
            self.dbg.stop()
        except Exception:  # noqa: BLE001
            pass
        if not self._fin:
            self._fin = True
            self.finished.emit(int(code))

    def running(self):
        return self.proc.state() != QProcess.ProcessState.NotRunning

    def __getattr__(self, name):
        if name in ("cont", "step_into", "step_over", "step_out", "evaluate", "set_breakpoint",
                    "set_break_on_exception", "children", "watch", "threads", "select_thread"):
            return getattr(self.dbg, name)
        raise AttributeError(name)

    def stop(self):
        self.user_stopped = True
        try:
            self.dbg.stop()
        except Exception:  # noqa: BLE001
            pass
        if self.running():
            self.proc.kill()
            self.proc.waitForFinished(3000)


def gdb_session(win, exe: Path, args: list, cwd: Path, env: dict | None):
    """gdb (MinGW, >= 14) over DAP: radide.dap.DapSession('gdb')."""
    gdb = find_gdb()
    if not gdb:
        return None
    from ..bridgedebug import gdb_env
    from ..dap import DapSession
    env = {**(env or {}), **gdb_env(gdb)}       # WinLibs gdb needs PYTHONHOME for its embedded Python (-i dap)
    s = DapSession("gdb", str(exe), list(args), Path(cwd), env, win._all_breakpoints(), win)
    s.argv = [gdb, "-i", "dap"]
    s.break_on_exception = False
    return s


def debugpy_session(win, python: str, script: Path, args: list, cwd: Path, env: dict | None):
    import importlib.util
    if importlib.util.find_spec("debugpy") is None:
        return None
    from ..dap import DapSession
    s = DapSession("debugpy", str(script), list(args), Path(cwd), env, win._all_breakpoints(), win)
    s.launch_args["python"] = [python]
    s.break_on_exception = win.settings.value("debug/break_on_exception", True) in (True, "true")
    return s


# ---------------------------------------------------------------- the main window


def show_projects(win, projects: list[ForeignProject], name: str, native: Path, startup: str = "") -> bool:
    """Show foreign projects as an implicit solution (nothing is written into their folders)."""
    from ..solution import Solution, SolutionProject
    if not projects:
        return False
    if hasattr(win, "_confirm_close_project") and not win._confirm_close_project():
        return True                       # handled (the user cancelled)
    root = Path(projects[0].folder)
    sln = Solution(name, root, [SolutionProject(p.name, str(Path(p.folder).resolve())) for p in projects],
                   startup or projects[0].name, None)
    for p in projects:
        sln._cache[p.name.lower()] = p
        p._log = win.log
        p._refresh = lambda path: refresh_editors(win, path)
    sln.foreign_native = Path(native)
    win.stop_project()
    win._reset()
    win.sln = sln
    for p in projects:
        win._state_for(p)
    target = sln.project(startup) if startup else None
    win.activate_project(target or projects[0])
    try:
        win._remember(Path(native))
    except Exception:  # noqa: BLE001
        pass
    win._fill_solution()
    p = win.project
    if p.forms:
        win.open_designer(p.forms[0])
    elif p.modules:
        first = next((m for m in p.modules if Path(m).suffix.lower() in
                      (".py", ".java", ".cpp", ".c", ".cs", ".js", ".ts")), p.modules[0])
        win.open_module(first)
    try:
        win.toolbox.setEnabled(bool(p.forms))
    except Exception:  # noqa: BLE001
        pass
    win._update_title()
    win._update_actions()
    for pr in projects:
        a = pr.adapter
        win.log(f"Opened {a.title} '{pr.name}' in place: {a.native}")
        for line in a.info:
            win.log(f"  {line}")
        for b in a.bindings.values():
            for n in b.notes:
                win.log(f"  {n}")
        win.log(f"  IDE state (not in your folder): {a.state}")
    install_native_menu(win)
    return True


def install_native_menu(win) -> None:
    """A 'Native' menu with the project's own build/run commands (VS Code tasks, CMake targets, ...)."""
    from PyQt6.QtWidgets import QMenu
    menu = getattr(win, "_others_native_menu", None)
    if menu is None:
        menu = QMenu("&Native", win)
        win._others_native_menu = menu
        win.menuBar().addMenu(menu)
    menu.clear()
    projects = [st["project"] for st in win.project_states() if getattr(st["project"], "foreign", False)
                and hasattr(st["project"], "adapter")]
    menu.menuAction().setVisible(bool(projects))
    for p in projects:
        sub = menu.addMenu(f"{p.name}  [{p.adapter.title}]") if len(projects) > 1 else menu
        for label, steps in p.adapter.commands():
            sub.addAction(label, lambda s=steps, lb=label: run_steps(win, s, lb))
        if p.adapter.targets:
            tm = sub.addMenu("Startup target")
            for t in p.adapter.targets:
                a = tm.addAction(t.name, lambda pr=p, n=t.name: _set_startup(win, pr, n))
                a.setCheckable(True)
                a.setChecked(t.name == p.startup)
        sub.addSeparator()
        sub.addAction("Open native project file", lambda pr=p: win.open_any_file(pr.adapter.native)
                      if pr.adapter.native.is_file() else None)
        sub.addAction("Reload forms from disk", lambda pr=p: _reload_forms(win, pr))
        sub.addAction("Show IDE state folder", lambda pr=p: win.log(str(pr.adapter.state)))


def refresh_editors(win, path: Path) -> None:
    """A binding rewrote a code file (NetBeans initComponents): reload unmodified open editors."""
    path = Path(path).resolve()
    for st in win.project_states():
        for view in list(st["codeviews"].values()) + list(st["modviews"].values()):
            vp = getattr(view, "path", None)
            if vp is None or Path(vp).resolve() != path:
                continue
            ed = view.editor
            if ed.isModified():
                continue
            try:
                ed.setText(read_text_keep(path)[0])
                ed.setModified(False)
            except OSError:
                pass


def _set_startup(win, project, name):
    project.startup = name
    project.save()
    install_native_menu(win)
    win.log(f"{project.name}: startup target = {name}")


def _reload_forms(win, project):
    for name in project.forms:
        project.reload_form(name)
        win.docs.pop(name, None) if win.project is project else None
    win.log(f"{project.name}: forms reloaded from the native files (close and reopen open designers)")


def run_steps(win, steps: list[Step], title: str = ""):
    """Run commands of the Native menu in the Output window."""
    s = ChainSession(list(steps), None, win)
    s.output.connect(lambda t: win._append_output(t) if hasattr(win, "_append_output") else win.log(t))
    s.failed.connect(lambda e: win.log(f"*** {e}"))
    s.finished.connect(lambda c: win.log(f"------ {title}: exit code {c} ------"))
    procs = getattr(win, "_others_procs", None)
    if procs is None:
        procs = win._others_procs = []
    procs[:] = [p for p in procs if p.running()]
    procs.append(s)
    try:
        win.dock_output.show()
        win.dock_output.raise_()
    except Exception:  # noqa: BLE001
        pass
    win.log(f"------ {title} ------")
    s.start()
    return s


def source_files(root: Path, exts: tuple, skip_dirs=(".git", ".idea", ".vscode", "node_modules", "build", "out",
                                                   "target", ".gradle", "bin", "obj", "__pycache__", ".venv",
                                                   "venv", "env", "dist", ".radide", "cmake-build-debug",
                                                   "cmake-build-release", ".tox", ".mypy_cache"),
                 limit: int = 3000, extra_names=()) -> list[str]:
    """Relative paths of files under *root* with one of *exts* (sorted, bounded)."""
    out = []
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs and not d.startswith("."))
        for f in sorted(filenames):
            if f.lower().endswith(exts) or f in extra_names:
                out.append(Path(dirpath, f).relative_to(root).as_posix())
                if len(out) >= limit:
                    return out
    return out
