# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Shared helpers for the example-project tests (samples/Examples/<Language>/<Name>).

Used by test_examples_scripting.py and the ex_*.py group modules next to it:

* create(folder, name, language, template)   - make a project exactly as File > New Project does
* make_form(project, form_name, form_props, controls) / add_form(...) - lay out a form through radide.model
* designer_check(folder)                      - every form loads into the real designer (DesignerView) without
                                                losing a control
* temp_copy(folder)                           - tests work on a copy, the samples folder stays clean
* BridgeDriver(folder)                        - run a GUI Bridge project (JS, TS, PHP, Perl, Lua, Ruby, PowerShell,
                                                Dart ...) in the IDE's own bridge host and drive it in-process
* TkDriver(folder)                            - load a python-tk project's startup form and drive it in-process
* windows_of(pid) / wait(...)                 - Win32 window checks (only processes the test started)
* publish(folder)                             - Build > Publish's build step; returns kind/size/python-inside
* http_get / http_post                        - talk to a dev server the test started

Every check runs in its own child process (see test_examples_scripting.py); nothing is captured from the screen.
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from ctypes import wintypes as wt
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXAMPLES = ROOT / "samples" / "Examples"
SCRATCH = Path(os.environ.get("RADIDE_EX_SCRATCH") or (Path(tempfile.gettempdir()) / "radide_examples2"))
QORG, QAPP = "RADIDE-TEST-EX2", "RADIDE-TEST-EX2"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def setup_env() -> None:
    """Environment for every child: offscreen Qt with real fonts, no browser, no help viewer."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    os.environ["RADIDE_NO_BROWSER"] = "1"
    os.environ["RADIDE_TEST_NO_DIALOGS"] = "1"
    os.environ["RADIDE_NO_UPDATE_CHECK"] = "1"
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def clear_qsettings() -> None:
    try:
        from PyQt6.QtCore import QSettings
        QSettings(QORG, QAPP).clear()
        QSettings(QORG, QAPP).sync()
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ project creation
def create(folder: Path, name: str, language: str, template: str = ""):
    """Create a project the way radide.features.solution_ui.create_project_from_dialog does."""
    from radide.languages import get_plugin
    from radide.model import Project
    from radide.workspace import create_library_project, create_project
    folder = Path(folder)
    plugin = get_plugin(language)
    if getattr(plugin, "project_kind", "") == "website":
        from radide.web_site.project import create_website
        return create_website(folder, name, language, template)
    if callable(getattr(plugin, "create_new_project", None)):
        return plugin.create_new_project(folder, name, template)
    if template == "library":
        return create_library_project(folder, name, language)
    project = create_project(folder, name, language)
    if template not in ("", "windows"):
        from radide.features.templates import apply_template
        apply_template(folder, template)
        project = Project.load(folder)
    return project


def make_form(project, form_name: str, form_props: dict | None, controls: list, *, regen: bool = True):
    """Lay out *form_name* (it must exist; see add_form).

    controls: list of dicts {"type", "name", "x", "y", ["w", "h", "parent", **other props]}.
    Every control starts from the toolbox defaults (Form.add), so the .form has all properties the designer
    writes.  Returns the Form."""
    from radide.model import Form
    from radide.workspace import _regen
    path = project.form_path(form_name)
    f = Form.load(path)
    f.controls = []
    f.props.update(form_props or {})
    f.props["Name"] = form_name
    for spec in controls:
        spec = dict(spec)
        t, name = spec.pop("type"), spec.pop("name")
        x, y = int(spec.pop("x", 0)), int(spec.pop("y", 0))
        parent = spec.pop("parent", "")
        c = f.add(t, x, y, parent)
        c.props["Name"] = name
        if "w" in spec:
            c.props["Width"] = int(spec.pop("w"))
        if "h" in spec:
            c.props["Height"] = int(spec.pop("h"))
        c.props.update(spec)
    f.save(path)
    if regen:
        _regen(project, form_name)
    return f


def add_form(project, name: str, language: str | None = None):
    from radide.workspace import create_form
    return create_form(project, name, language)


def write(path: Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n"), encoding="utf-8", newline="\n")
    return path


def regen_all(folder: Path) -> None:
    """Regenerate every designer file (after editing the code files)."""
    from radide.model import Project
    from radide.workspace import _regen
    p = Project.load(Path(folder))
    for name in p.forms:
        _regen(p, name)


# ============================================================================ copies
def temp_copy(folder: Path, tag: str = "") -> Path:
    """Copy a sample to the scratch folder (build output never lands in samples/)."""
    folder = Path(folder)
    dst = SCRATCH / (tag or folder.parent.name) / folder.name
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(folder, dst, ignore=shutil.ignore_patterns(
        "Publish", "build", "dist", "node_modules", ".venv", "__pycache__", ".radide", "*.pyc"))
    return dst


def dir_size(p: Path) -> int:
    p = Path(p)
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def mb(n: int) -> float:
    return round(n / (1024 * 1024), 2)


# ============================================================================ designer
_QAPP = None


def qapp():
    """The PyQt6 application the designer needs (offscreen; QSettings org/app RADIDE-TEST-EX2)."""
    global _QAPP
    setup_env()
    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtWidgets import QApplication
    QCoreApplication.setOrganizationName(QORG)
    QCoreApplication.setApplicationName(QAPP)
    _QAPP = QApplication.instance() or QApplication(sys.argv)
    return _QAPP


def designer_check(folder: Path) -> tuple[bool, str]:
    """Open every form of the project in the real designer (DesignerView + FormDocument, as the IDE does) and
    check that no control is lost: the .form's control count == the document's, every visual control has a
    preview widget, and the generated designer file mentions every control.  Also grabs the designer surface
    (widget.grab - never the screen) to make sure it paints."""
    from radide.model import Form, Project
    from radide.languages import plugin_for_form
    folder = Path(folder)
    project = Project.load(folder)
    if not project.forms:
        return True, "no forms"
    app = qapp()
    from radide.designer import DesignerView
    from radide.document import FormDocument
    notes = []
    ok = True
    for name in project.forms:
        path = project.form_path(name)
        raw = json.loads(path.read_text(encoding="utf-8"))
        want = len(raw.get("controls", []))
        doc = FormDocument(Form.load(path), path)
        view = DesignerView(doc)
        view.resize(1200, 900)
        view.show()
        app.processEvents()
        got = len(doc.form.controls)
        missing = [c.name for c in doc.form.visual()
                   if c.type not in ("MenuStrip", "ToolStrip", "StatusBar") and c.parent == ""
                   and view.previews.get(id(c)) is None]
        img = view.surface.grab()
        plugin = plugin_for_form(project, name)
        dfile = folder / plugin.designer_file(name)
        gen = plugin.generate_designer(doc.form, (folder / plugin.code_file(name)).read_text(encoding="utf-8")) \
            if (folder / plugin.code_file(name)).exists() else ""
        absent = [c.name for c in doc.form.controls if c.name not in gen and c.type not in ("MenuStrip", "ToolStrip")]
        good = got == want and not missing and not img.isNull() and not absent
        ok &= good
        notes.append(f"{name}: {got}/{want} controls" + (f" no preview: {missing}" if missing else "")
                     + (f" not in designer file: {absent}" if absent else "")
                     + ("" if dfile.exists() else " (designer file missing)"))
        view.close()
        view.deleteLater()
        app.processEvents()
    return ok, "; ".join(notes)


# ============================================================================ Win32 windows
user32 = ctypes.WinDLL("user32", use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
WM_CLOSE = 0x0010


def window_title(h) -> str:
    b = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(h, b, 512)
    return b.value


def windows_of(pids, visible_only=True) -> list[tuple[int, str]]:
    """(hwnd, title) of the top-level windows that belong to the given process ids."""
    pids = {pids} if isinstance(pids, int) else set(pids)
    out = []

    def cb(h, _l):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and (not visible_only or user32.IsWindowVisible(h)):
            out.append((h, window_title(h)))
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def process_tree(pid: int) -> list[int]:
    """pid + all its descendants (wmic-free: uses toolhelp snapshots)."""
    TH32CS_SNAPPROCESS = 0x2

    class PE(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateToolhelp32Snapshot.restype = wt.HANDLE
    snap = k.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE()
    pe.dwSize = ctypes.sizeof(PE)
    parent = {}
    if k.Process32FirstW(snap, ctypes.byref(pe)):
        while True:
            parent[pe.th32ProcessID] = pe.th32ParentProcessID
            if not k.Process32NextW(snap, ctypes.byref(pe)):
                break
    k.CloseHandle(snap)
    tree, changed = {pid}, True
    while changed:
        changed = False
        for c, p in parent.items():
            if p in tree and c not in tree:
                tree.add(c)
                changed = True
    return sorted(tree)


def wait(pred, timeout=10.0, step=0.1):
    end = time.time() + timeout
    while time.time() < end:
        try:
            v = pred()
        except Exception:  # noqa: BLE001
            v = None
        if v:
            return v
        time.sleep(step)
    return None


def wait_window(proc: subprocess.Popen, title_part: str = "", timeout=30.0):
    """The first visible top-level window of *proc* (or a descendant) whose title contains title_part."""
    def find():
        for h, t in windows_of(process_tree(proc.pid)):
            if title_part.lower() in t.lower():
                return h, t
        return None
    return wait(find, timeout, 0.25)


def stop_tree(proc: subprocess.Popen, timeout=5.0) -> None:
    """Close the windows of a process the test started, then kill only that process tree if it hangs."""
    if proc.poll() is not None:
        return
    for h, _t in windows_of(process_tree(proc.pid)):
        user32.PostMessageW(h, WM_CLOSE, 0, 0)
    try:
        proc.wait(timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)


# ============================================================================ GUI Bridge driver
class BridgeDriver:
    """Runs a GUI Bridge project in radide.runtimes.bridge.BridgeRuntime (the host the IDE starts on F5) inside
    this process: the form is a real Tk window of this process, the program (node, php, perl ...) is the child
    the IDE would start.  MsgBox/InputBox answers are scripted (self.answers) and recorded (self.msgs)."""

    def __init__(self, folder: Path, build_timeout=300):
        setup_env()
        import tkinter
        from radide.languages import get_plugin
        from radide.model import Project
        from radide.runtimes.bridge import BridgeRuntime
        tkinter.Misc.wait_window = lambda self, w=None: None
        tkinter.Misc.grab_set = lambda self: None
        self.folder = folder = Path(folder)
        project = Project.load(folder)
        plugin = get_plugin(project.form_languages.get(project.startup, project.language)
                            if project.startup else project.language)
        self.plugin = plugin
        plugin.prepare(folder, project)
        build = plugin.build_command(folder, project)
        self.build_output = ""
        if build:
            r = subprocess.run(build, cwd=str(folder), shell=True, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=build_timeout)
            self.build_output = (r.stdout + r.stderr).strip()
            if r.returncode != 0:
                raise RuntimeError(f"build failed ({r.returncode}): {self.build_output[-2000:]}")
        handlers = set(plugin.handlers_in_project(folder, project))
        self.rt = rt = BridgeRuntime(folder, plugin.run_command(folder, project), handlers)
        self.msgs: list[str] = []
        self.answers: list = []
        self.output: list[str] = []

        def msgbox(prompt, buttons=0, title=""):
            self.msgs.append(str(prompt))
            print(f"    [MsgBox] {prompt}", flush=True)
            return self.answers.pop(0) if self.answers else 1

        def inputbox(prompt, title="", default=""):
            ans = self.answers.pop(0) if self.answers else default
            print(f"    [InputBox] {prompt} -> {ans!r}", flush=True)
            return str(ans)
        rt.msgbox, rt.inputbox = msgbox, inputbox
        self.ended = False

        def end():
            self.ended = True
            try:
                rt.send("QUIT")
            except Exception:  # noqa: BLE001
                pass
        rt.end = end
        rt.load()
        rt.start_program()
        start = rt.forms[(project.startup or project.forms[0]).lower()]
        rt.startup_form = start
        start.load()
        start.vb_call("show", [])
        self.pump(300)

    def pump(self, ms=100):
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            try:
                if self.rt.root is not None:
                    self.rt.root.update()
            except Exception:  # noqa: BLE001
                return
            time.sleep(0.005)

    def form(self, name):
        vf = self.rt.forms[name.lower()]
        return vf

    def ctl(self, name: str, form: str | None = None):
        if form:
            return self.form(form).vb_get(name.lower())
        return self.rt.resolve_obj(name)

    def get(self, name, prop="Text", form=None):
        from radide.runtimes.vbinterp import to_str
        return to_str(self.ctl(name, form).vb_get(prop.lower()))

    def set(self, name, value, prop="Text", form=None):
        self.ctl(name, form).vb_set(prop.lower(), value)

    def call(self, name, method, *args, form=None):
        return self.ctl(name, form).vb_call(method.lower(), list(args))

    def event(self, owner, ev="Click", e=None):
        r = self.rt.event(owner, ev, e)
        self.pump(50)
        return r

    def click(self, owner):
        return self.event(owner, "Click")

    def list_items(self, name, form=None) -> list[str]:
        c = self.ctl(name, form)
        n = int(c.vb_get("listcount"))
        return [str(c.vb_call("list", [i])) for i in range(n)]

    def window(self, title_part=""):
        """The host's own Tk window as Windows sees it (EnumWindows over this process)."""
        return wait(lambda: next(((h, t) for h, t in windows_of(os.getpid())
                                  if title_part.lower() in t.lower()), None), 5, 0.1)

    def close(self):
        try:
            self.rt.send("QUIT")
            if self.rt.proc:
                self.rt.proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            if self.rt.proc and self.rt.proc.poll() is None:
                self.rt.proc.kill()
        try:
            self.rt.root.destroy()
        except Exception:  # noqa: BLE001
            pass


# ============================================================================ python-tk driver
class TkDriver:
    """Imports a python-tk project's startup form from a (temporary copy of the) project and creates it without
    entering mainloop; tests call handlers / widget.invoke() and pump the Tk event loop."""

    def __init__(self, folder: Path, form: str | None = None):
        setup_env()
        import importlib
        from radide.model import Project
        self.folder = folder = Path(folder)
        project = Project.load(folder)
        sys.path.insert(0, str(folder))
        os.chdir(folder)
        name = form or project.startup
        mod = importlib.import_module(name)
        self.mod = mod
        self.form = getattr(mod, name)()
        self.pump(300)

    def pump(self, ms=100):
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            try:
                self.form.root.update()
            except Exception:  # noqa: BLE001
                return
            time.sleep(0.005)

    def window(self, title_part=""):
        return wait(lambda: next(((h, t) for h, t in windows_of(os.getpid())
                                  if title_part.lower() in t.lower()), None), 5, 0.1)

    def close(self):
        try:
            self.form.root.destroy()
        except Exception:  # noqa: BLE001
            pass


# ============================================================================ processes / HTTP
def run_spec_proc(folder: Path, *, interpreter: str = "", env_extra: dict | None = None, stdin=None,
                  capture=True) -> subprocess.Popen:
    """Start the project like F5 does: the startup plugin's run_spec (program, args, cwd, env)."""
    from radide.languages import get_plugin
    from radide.model import Project
    project = Project.load(Path(folder))
    lang = project.form_languages.get(project.startup, project.language) if project.startup else project.language
    plugin = get_plugin(lang)
    if not interpreter and callable(getattr(plugin, "find_interpreter", None)):
        interpreter = plugin.find_interpreter("")        # what the IDE passes on F5 (python-tk / python-qt ...)
    spec = plugin.run_spec(Path(folder), project.startup, interpreter)
    env = dict(spec.env or os.environ)
    env.update(env_extra or {})
    return subprocess.Popen([spec.program, *spec.args], cwd=str(spec.cwd or folder), env=env,
                            stdin=stdin, stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.STDOUT if capture else None, text=True, encoding="utf-8",
                            errors="replace")


def http_get(url: str, timeout=10.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def http_post(url: str, data: dict, timeout=10.0, json_body=False) -> tuple[int, str]:
    body = json.dumps(data).encode() if json_body else urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json" if json_body else "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def wait_http(url: str, timeout=60.0) -> bool:
    return bool(wait(lambda: http_get(url, 3)[0] < 500, timeout, 0.5))


def free_port() -> int:
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ============================================================================ publish
def publish(folder: Path, log_file: Path | None = None, **cfg_overrides) -> dict:
    """Build > Publish's build step (radide.deploy.build.build) on *folder* (use a temp copy).
    Returns {"ok", "kind", "exe", "size_mb", "python_inside", "notes"}; no installer is made."""
    from radide.deploy.build import build
    from radide.deploy.config import load as load_cfg
    from radide.model import Project
    try:                 # the project's publish.json / the Publish dialog's defaults (app name = project name)
        cfg = load_cfg(Path(folder), Project.load(Path(folder)).name)
    except Exception:  # noqa: BLE001
        from radide.deploy.config import PublishConfig
        cfg = PublishConfig()
    cfg.make_installer = False
    for k, v in cfg_overrides.items():
        setattr(cfg, k, v)
    lines: list[str] = []
    try:
        res = build(Path(folder), cfg, log=lambda s: lines.append(str(s)))
    except Exception as e:  # noqa: BLE001
        if log_file:
            write(log_file, "\n".join(lines) + f"\n*** {e}")
        return {"ok": False, "kind": "", "error": str(e)[-400:], "log_tail": lines[-15:]}
    if log_file:
        write(log_file, "\n".join(lines))
    dist = Path(res.dist)
    exe = dist / res.exe
    py = any(p.name.lower().startswith("python3") and p.suffix.lower() == ".dll" for p in dist.rglob("*.dll"))
    return {"ok": exe.exists(), "kind": res.kind, "exe": res.exe, "size_mb": mb(dir_size(dist)),
            "exe_mb": mb(exe.stat().st_size) if exe.exists() else 0, "python_inside": py or res.python_based,
            "dist": str(dist), "notes": res.notes}


# ============================================================================ results
class Result(dict):
    """One project's row: open / build / run / publish / size / result (+ notes)."""

    def __init__(self, project: str, language: str):
        super().__init__(project=project, language=language, open="-", build="-", run="-", publish="-",
                         size="-", result="-", notes=[])

    def step(self, key: str, ok, note: str = ""):
        self[key] = "ok" if ok is True else ("FAIL" if ok is False else str(ok))
        if note:
            self["notes"].append(f"{key}: {note}")
        print(("ok   " if ok is True else "FAIL " if ok is False else "--   ") + f"{self['project']} {key} {note}",
              flush=True)
        return ok

    def finish(self):
        steps = [self[k] for k in ("open", "build", "run", "publish")]
        self["result"] = "FAIL" if "FAIL" in steps else "ok"
        return self


def emit(res: Result) -> None:
    """Child -> runner: the row as one marked JSON line."""
    print("@@RESULT@@" + json.dumps(res.finish(), ensure_ascii=False), flush=True)
