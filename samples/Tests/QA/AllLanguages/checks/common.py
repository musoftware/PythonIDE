"""Shared helpers of the all-languages QA test: results, processes started by the test, windows of those
processes (Win32 messages only, no screen capture), project creation like File > New Project."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes as wt
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent           # samples/Tests/QA/AllLanguages
REPO = HERE.parents[3]
FROZEN = bool(getattr(sys, "frozen", False))
if not FROZEN and str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_QT_KEYS = ("QT_QPA_PLATFORM", "QT_QPA_FONTDIR")
_ORIG_ENV = {k: os.environ.get(k) for k in _QT_KEYS}
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
os.environ["RADIDE_NO_BROWSER"] = "1"
ORG, APP = "RADIDE-TEST-QA", "RADIDE-TEST-QA"

try:
    import psutil  # noqa: E402
except ImportError:                   # the frozen IDE (RADIDE_AS_PYTHON) may not bundle psutil
    psutil = None

user32 = ctypes.WinDLL("user32", use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
user32.EnumChildWindows.argtypes = [wt.HWND, WNDENUMPROC, wt.LPARAM]
user32.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT,
                                       ctypes.POINTER(ctypes.c_size_t)]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.ScreenToClient.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.RealChildWindowFromPoint.argtypes = [wt.HWND, wt.POINT]
user32.RealChildWindowFromPoint.restype = wt.HWND
user32.IsWindowVisible.argtypes = [wt.HWND]
WM_GETTEXT, WM_GETTEXTLENGTH, WM_CLOSE = 0x000D, 0x000E, 0x0010
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0200, 0x0201, 0x0202

FORM_LANGS_EXTRA = ("python-tk", "python-qt", "vb-basic", "ring-qt")
EXPECTED_TITLE = "Hi QA"

# Button1_Click body per language: Label1.Text = "Hi " + TextBox1.Text ; Form1.Text = Label1.Text
CLICK = {
    "python-tk": ["self.Label1.config(text='Hi ' + self.TextBox1_var.get())",
                  "self.root.title(self.Label1.cget('text'))"],
    "python-qt": ["self.Label1.setText('Hi ' + self.TextBox1.text())",
                  "self.setWindowTitle(self.Label1.text())"],
    "vb-basic": ['Label1.Text = "Hi " & TextBox1.Text', "Me.Text = Label1.Text"],
    "ring-qt": ['Label1.setText("Hi " + TextBox1.text())', "Form1.setWindowTitle(Label1.text())"],
    "c-bridge": ['char qa_buf[256];', 'snprintf(qa_buf, sizeof qa_buf, "Hi %s", rad_get("TextBox1", "Text"));',
                 'rad_set("Label1", "Text", qa_buf);', 'rad_set("Form1", "Text", rad_get("Label1", "Text"));'],
    "cpp-bridge": ['rad::set("Label1", "Text", "Hi " + rad::get("TextBox1", "Text"));',
                   'rad::set("Form1", "Text", rad::get("Label1", "Text"));'],
    "csharp-bridge": ['Label1.Text = "Hi " + TextBox1.Text;', 'Set("Form1", "Text", Label1.Text);'],
    "powershell-bridge": ['$Label1.Text = "Hi " + $TextBox1.Text', 'RadSet Form1 Text $Label1.Text'],
    "java-bridge": ['Label1.setText("Hi " + TextBox1.getText());', 'set("Form1", "Text", Label1.getText());'],
    "javascript": ['set("Label1", "Text", "Hi " + get("TextBox1", "Text"));',
                   'set("Form1", "Text", get("Label1", "Text"));'],
    "typescript": ['set("Label1", "Text", "Hi " + get("TextBox1", "Text"));',
                   'set("Form1", "Text", get("Label1", "Text"));'],
    "php": ["rad_set('Label1', 'Text', 'Hi ' . rad_get('TextBox1', 'Text'));",
            "rad_set('Form1', 'Text', rad_get('Label1', 'Text'));"],
    "rust-bridge": ['set("Label1", "Text", format!("Hi {}", get("TextBox1", "Text")));',
                    'set("Form1", "Text", get("Label1", "Text"));'],
    "go-bridge": ['Set("Label1", "Text", "Hi "+Get("TextBox1", "Text"))', 'Set("Form1", "Text", Get("Label1", "Text"))'],
    "fortran-bridge": ['call rad_set("Label1", "Text", "Hi " // rad_get("TextBox1", "Text"))',
                       'call rad_set("Form1", "Text", rad_get("Label1", "Text"))'],
    "lua-bridge": ['rad.set("Label1", "Text", "Hi " .. rad.get("TextBox1", "Text"))',
                   'rad.set("Form1", "Text", rad.get("Label1", "Text"))'],
    "ruby-bridge": ['Rad.set("Label1", "Text", "Hi " + Rad.get("TextBox1", "Text"))',
                    'Rad.set("Form1", "Text", Rad.get("Label1", "Text"))'],
    "perl-bridge": ['rad_set("Label1", "Text", "Hi " . rad_get("TextBox1", "Text"));',
                    'rad_set("Form1", "Text", rad_get("Label1", "Text"));'],
    "dart-bridge": ["Rad.set('Label1', 'Text', 'Hi ' + Rad.get('TextBox1', 'Text'));",
                    "Rad.set('Form1', 'Text', Rad.get('Label1', 'Text'));"],
}
C_PRELUDE = {"c-bridge": "#include <stdio.h>\n"}
# a local variable at the start of Button1_Click (the debugger's Locals must show it)
LOCAL = {"vb-basic": ["Dim qaN As Integer", "qaN = 42"], "python-tk": ["qa_n = 42"], "python-qt": ["qa_n = 42"],
         "ring-qt": ["qaN = 42"], "c-bridge": ["int qa_n = 42;"], "cpp-bridge": ["int qa_n = 42;"],
         "csharp-bridge": ["int qaN = 42;"], "powershell-bridge": ["$qaN = 42"], "java-bridge": ["int qaN = 42;"],
         "javascript": ["let qaN = 42;"], "typescript": ["let qaN: number = 42;"], "php": ["$qaN = 42;"],
         "rust-bridge": ["let _qa_n = 42;"], "go-bridge": ["qaN := 42", "_ = qaN"],
         "fortran-bridge": ["integer :: qa_n", "qa_n = 42"], "lua-bridge": ["local qaN = 42"],
         "ruby-bridge": ["qa_n = 42"], "perl-bridge": ["my $qaN = 42;"], "dart-bridge": ["var qaN = 42;"]}


# ====================================================================== results
@dataclass
class Result:
    language: str
    template: str
    display: str = ""
    create: str = ""
    build: str = ""
    run: str = ""
    publish_kind: str = ""
    publish: str = ""
    published_run: str = ""
    exe_size: int = 0
    dist_size: int = 0
    python_inside: str = ""
    intellisense: str = ""          # family summaries of the IDE checks (PASS / FAIL: which sub-checks / SKIP)
    designer: str = ""
    debug: str = ""
    frozen: str = ""
    sub: dict = field(default_factory=dict)     # "intellisense.completion" -> "PASS - ..." / "FAIL: ..." / "SKIP: ..."
    result: str = ""
    notes: list[str] = field(default_factory=list)
    seconds: float = 0.0

    def note(self, text: str) -> None:
        text = str(text).strip()
        if text:
            self.notes.append(text[-1500:])


def status(s: str) -> str:
    return (s or "").split(":", 1)[0].split(" ", 1)[0]


def overall(r: Result) -> str:
    st = [status(x) for x in (r.create, r.build, r.run, r.publish, r.published_run, r.intellisense, r.designer,
                              r.debug, r.frozen) if x]
    if "FAIL" in st or any(status(v) == "FAIL" for v in r.sub.values()):
        return "FAIL"
    if "PASS" in st or any(status(v) == "PASS" for v in r.sub.values()):
        return "PASS" + ("*" if "SKIP" in st else "")
    return "SKIP"


# ====================================================================== processes / windows
def child_env(env: dict | None) -> dict:
    e = dict(os.environ if env is None else env)
    for k in _QT_KEYS:
        e.pop(k, None)
        if _ORIG_ENV.get(k):
            e[k] = _ORIG_ENV[k]
    e.setdefault("RADIDE_NO_BROWSER", "1")
    e["PYTHONIOENCODING"] = "utf-8"
    return e


class Started:
    """A process this script started (stdout/stderr collected in a thread)."""

    def __init__(self, argv, cwd, env=None, shell=False):
        self.argv = argv
        self.proc = subprocess.Popen(argv, cwd=str(cwd), env=child_env(env), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                                     if shell else 0)
        self.out: list[str] = []
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for raw in self.proc.stdout:
            self.out.append(raw.decode("utf-8", "replace").rstrip("\r\n"))

    def pids(self) -> set[int]:
        if psutil is None:
            return {self.proc.pid}
        try:
            return {self.proc.pid} | {c.pid for c in psutil.Process(self.proc.pid).children(recursive=True)}
        except psutil.Error:
            return {self.proc.pid}

    def alive(self) -> bool:
        return self.proc.poll() is None

    def text(self, n=40) -> str:
        return "\n".join(self.out[-n:])

    def kill(self):
        """Close / kill only this process tree."""
        if psutil is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)
            return
        try:
            procs = [psutil.Process(self.proc.pid)] + psutil.Process(self.proc.pid).children(recursive=True)
        except psutil.Error:
            procs = []
        for p in reversed(procs):
            try:
                p.kill()
            except psutil.Error:
                pass
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            pass


def _pid_of(h) -> int:
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value


def top_windows(pids: set[int]) -> list:
    out = []

    def cb(h, _l):
        if user32.IsWindowVisible(h) and _pid_of(h) in pids:
            out.append(h)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def get_text(h) -> str:
    res = ctypes.c_size_t()
    if not user32.SendMessageTimeoutW(h, WM_GETTEXTLENGTH, 0, 0, 2, 2000, ctypes.byref(res)):
        return ""
    n = int(res.value)
    b = ctypes.create_unicode_buffer(n + 2)
    user32.SendMessageTimeoutW(h, WM_GETTEXT, n + 1, ctypes.cast(b, ctypes.c_void_p).value, 2, 2000,
                               ctypes.byref(res))
    return b.value


def class_name(h) -> str:
    b = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, b, 256)
    return b.value


def descendants(h) -> list:
    out = []

    def cb(c, _l):
        out.append(c)
        return True
    user32.EnumChildWindows(h, WNDENUMPROC(cb), 0)
    return out


def wait_for(pred, timeout, step=0.2):
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


def _lparam(x, y) -> int:
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, wt.BOOL]
HWND_TOPMOST, HWND_NOTOPMOST = wt.HWND(-1), wt.HWND(-2)
# no size / move / activate; ASYNC: a program paused in the debugger must not block the caller
SWP_KEEP = 0x0001 | 0x0002 | 0x0010 | 0x4000


def post_click(h, x, y, form=None):
    """Mouse move + press + release sent to one window of the program (no real input, no screen capture).

    Toolkits that read the real mouse state (Tk: GetKeyState(VK_LBUTTON), WindowFromPoint on release) need two
    helpers that only touch the program's own window/thread: the form is made topmost for the click (so
    WindowFromPoint finds it) and our input state is attached to its thread with the left button marked down
    between press and release."""
    res = ctypes.c_size_t()
    if form:
        # synchronous when the program answers (an asynchronous topmost is not applied reliably); a program paused
        # in a debugger never answers and the test (the IDE's thread) must not wait for it: asynchronous then
        res0 = ctypes.c_size_t()
        alive = user32.SendMessageTimeoutW(form, 0, 0, 0, 2, 500, ctypes.byref(res0))      # WM_NULL
        user32.SetWindowPos(form, HWND_TOPMOST, 0, 0, 0, 0, SWP_KEEP & ~0x4000 if alive else SWP_KEEP)
        if not alive:
            time.sleep(0.3)
    tid = user32.GetWindowThreadProcessId(h, None)
    me = kernel32.GetCurrentThreadId()
    attached = bool(user32.AttachThreadInput(me, tid, True))
    ks = (ctypes.c_ubyte * 256)()

    def send(msg, wp):
        user32.SendMessageTimeoutW(h, msg, wp, _lparam(x, y), 2, 3000, ctypes.byref(res))

    def lbutton(down):
        if attached:
            user32.GetKeyboardState(ks)
            ks[1] = 0x80 if down else 0
            user32.SetKeyboardState(ks)
    try:
        send(WM_MOUSEMOVE, 0)
        lbutton(True)
        send(WM_LBUTTONDOWN, 1)
        lbutton(False)
        send(WM_LBUTTONUP, 0)
    finally:
        if attached:
            user32.AttachThreadInput(me, tid, False)
        if form:
            user32.SetWindowPos(form, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_KEEP)


user32.WindowFromPoint.argtypes = [wt.POINT]
user32.WindowFromPoint.restype = wt.HWND
user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
user32.GetAncestor.restype = wt.HWND


def _uncovered(form, h, x, y) -> bool:
    pt = wt.POINT(int(x), int(y))
    user32.ClientToScreen(h, ctypes.byref(pt))
    top = user32.WindowFromPoint(pt)
    return bool(top) and user32.GetAncestor(top, 2) == form           # GA_ROOT


def ensure_uncovered(form, h, x, y) -> str:
    """Toolkits that check WindowFromPoint (Tk) need the click point visible on screen. If another program's
    window (a system dialog, ...) covers it even with our window topmost, move OUR program's window to a corner
    where the point is visible. Only the program's own window is moved."""
    res0 = ctypes.c_size_t()
    if not user32.SendMessageTimeoutW(form, 0, 0, 0, 2, 500, ctypes.byref(res0)):    # paused in a debugger
        return ""
    user32.SetWindowPos(form, HWND_TOPMOST, 0, 0, 0, 0, SWP_KEEP & ~0x4000)
    if _uncovered(form, h, x, y):
        return ""
    r = wt.RECT()
    user32.GetWindowRect(form, ctypes.byref(r))
    w, hh = r.right - r.left, r.bottom - r.top
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    for nx, ny in ((0, 0), (sw - w, 0), (0, sh - hh), (sw - w, sh - hh), ((sw - w) // 2, 0), (0, (sh - hh) // 2)):
        user32.SetWindowPos(form, HWND_TOPMOST, max(0, nx), max(0, ny), 0, 0, 0x0001 | 0x0010)
        time.sleep(0.2)
        if _uncovered(form, h, x, y):
            return f" (moved to {nx},{ny}: the point was covered by another window)"
    return " (the click point stays covered by another window)"


def click_button(form, text="Button1", design=(20, 20, 75, 23)) -> str:
    """Click Button1: a native child window with that text (Win32 / WinForms / Tk buttons), else the deepest
    child at the button's design position (Qt / Swing draw their own controls). Returns how it clicked."""
    for c in descendants(form):
        if user32.IsWindowVisible(c) and get_text(c) == text:
            r = wt.RECT()
            user32.GetClientRect(c, ctypes.byref(r))
            note = ensure_uncovered(form, c, max(1, r.right // 2), max(1, r.bottom // 2))
            post_click(c, max(1, r.right // 2), max(1, r.bottom // 2), form)
            return f"native {class_name(c)}{note}"
    x, y = design[0] + design[2] // 2, design[1] + design[3] // 2
    target, pt = form, wt.POINT(x, y)
    for _ in range(8):                      # descend to the deepest real child at that point
        child = user32.RealChildWindowFromPoint(target, pt)
        if not child or child == target:
            break
        sp = wt.POINT(pt.x, pt.y)
        user32.ClientToScreen(target, ctypes.byref(sp))
        user32.ScreenToClient(child, ctypes.byref(sp))
        target, pt = child, sp
    note = ensure_uncovered(form, target, pt.x, pt.y)
    post_click(target, pt.x, pt.y, form)
    return f"at ({pt.x},{pt.y}) of {class_name(target)}{note}"


ERROR_TITLES = ("build failed", "error", "unhandled exception", "traceback", "fatal", "failed to execute")


def gui_test(st: Started, timeout: float, title="Form1") -> tuple[str, str]:
    """The program's window "Form1" appears; Button1's Click sets the title to "Hi QA"."""
    def find():
        if not st.alive() and not (st.pids() - {st.proc.pid}):
            return "exited"
        for h in top_windows(st.pids()):
            t = get_text(h)
            if t == title or t == EXPECTED_TITLE:
                return h
            if t and any(e in t.lower() for e in ERROR_TITLES):
                return ("error", h, t)
        return None
    w = wait_for(find, timeout, 0.3)
    if w is None:
        wins = [(get_text(h), class_name(h)) for h in top_windows(st.pids())]
        return "FAIL", f"no window '{title}' within {timeout:.0f}s (windows: {wins[:5]})"
    if w == "exited":
        return "FAIL", f"the program exited (code {st.proc.returncode}) before showing '{title}'"
    if isinstance(w, tuple):
        detail = "  ".join(get_text(c) for c in descendants(w[1]) if get_text(c))[:600]
        return "FAIL", f"error window '{w[2]}': {detail}"
    time.sleep(1.0)                          # let the Load handlers finish
    how = ""
    for _attempt in range(3):
        how = click_button(w)
        if wait_for(lambda: get_text(w) == EXPECTED_TITLE, 6, 0.2):
            break
    got = get_text(w)
    ok = got == EXPECTED_TITLE
    user32.PostMessageW(w, WM_CLOSE, 0, 0)
    try:
        st.proc.wait(8)
        closed = True
    except subprocess.TimeoutExpired:
        closed = False
    if ok:
        return "PASS", f"window shown, Click -> title '{got}' ({how})" + ("" if closed else "; had to be killed")
    if "stays covered" in how:
        return "SKIP", (f"window shown, but another program's window (e.g. a Windows Security / firewall prompt) "
                        f"covers the whole screen, so the click cannot be delivered ({how})")
    return "FAIL", f"window shown but after Click the title is '{got}' (clicked {how})"


def generic_run(st: Started, timeout: float) -> tuple[str, str]:
    """Console program: exit code 0; GUI / game / emulator / server: still running at the time limit."""
    end = time.time() + timeout
    while time.time() < end:
        if not st.alive():
            time.sleep(0.3)
            code = st.proc.returncode
            out = st.text(12)
            return ("PASS" if code == 0 else "FAIL"), f"exit {code}: {out[-600:]}"
        time.sleep(0.3)
    wins = [get_text(h) or class_name(h) for h in top_windows(st.pids())]
    out = st.text(6)
    bad = [t for t in wins if any(e in t.lower() for e in ERROR_TITLES)]
    if bad:
        return "FAIL", f"error window {bad[0]!r}: {st.text(15)[-700:]}"
    if wins:
        return "PASS", f"running, window(s) {wins[:3]}; {out[-300:]}"
    return "PASS", f"still running after {timeout:.0f}s (no window): {out[-300:]}"


# ====================================================================== project creation
def plugins():
    from radide.languages import all_plugins
    return {p.id: p for p in all_plugins() if not getattr(p, "foreign_only", False)}


def groups() -> dict[str, list[str]]:
    from radide.dialogs import LANGUAGE_GROUPS
    return {g: list(ids) for g, ids in LANGUAGE_GROUPS}


def is_website(p) -> bool:
    return getattr(p, "project_kind", "") == "website"


# templates whose first entry needs a file the user picks (a ROM, a firmware dump, an old DOS exe): the
# self-contained demo of the same language is tested first instead
PREFERRED_TEMPLATE = {"retro-romhack": "romhack_demo", "firmware-ecu": "ecu_demo", "firmware-analysis": "fwa_demo",
                      "retro-dos": "dos_asm"}


def templates_of(p) -> list[str]:
    if is_website(p):
        from radide.web_site.project import templates_for
        return [t.id for t in templates_for(p.id)] or [""]
    if callable(getattr(p, "project_templates", None)) and callable(getattr(p, "create_new_project", None)):
        ids = [t[0] for t in p.project_templates()] or [""]
        pref = PREFERRED_TEMPLATE.get(p.id)
        return ([pref] + [i for i in ids if i != pref]) if pref in ids else ids
    return ["windows"]


def has_form_code(p) -> bool:
    return p.id in CLICK


def create(folder: Path, name: str, p, template: str):
    from radide.model import Project
    from radide.workspace import create_project
    if is_website(p):
        from radide.web_site.project import create_website
        return create_website(folder, name, p.id, template)
    if callable(getattr(p, "create_new_project", None)):
        return p.create_new_project(folder, name, template)
    project = create_project(folder, name, p.id)
    if template not in ("", "windows"):
        from radide.features.templates import apply_template
        apply_template(folder, template)
        project = Project.load(folder)
    return project


def add_click_form(project, p) -> None:
    """Button1 + TextBox1 ("QA") + Label1 on Form1 and the Click handler (like the designer does)."""
    from radide.model import Form
    from radide.workspace import _regen
    path = project.form_path("Form1")
    form = Form.load(path)
    btn = form.add("Button", 20, 20)
    tb = form.add("TextBox", 20, 60)
    tb.props["Text"] = "QA"
    form.add("Label", 20, 100)
    form.save(path)
    code_path = project.folder / p.code_file("Form1")
    code = code_path.read_text(encoding="utf-8")
    name = p.handler_for(form, btn, "Click")
    code, line = p.add_handler(code, name, form)
    lines = code.splitlines()
    # the stub's body line: the cursor line given by add_handler; keep its indentation
    indent = lines[line][:len(lines[line]) - len(lines[line].lstrip())] if line < len(lines) else "    "
    if not indent.strip() == "" or not indent:
        indent = "    "
    body = [indent + s for s in LOCAL.get(p.id, []) + CLICK[p.id]]
    if line < len(lines) and lines[line].strip() in ("", "pass"):
        lines[line:line + 1] = body
    else:
        lines[line + 1:line + 1] = body
    code = "\n".join(lines) + "\n"
    code = C_PRELUDE.get(p.id, "") + code
    code_path.write_text(code, encoding="utf-8")
    _regen(project, "Form1")




def summarize(sub: dict, family: str) -> str:
    """Family summary from its sub-checks: FAIL lists the failed ones, PASS counts, SKIP when nothing ran."""
    items = {k.split(".", 1)[1]: v for k, v in sub.items() if k.startswith(family + ".")}
    if not items:
        return ""
    fails = [k for k, v in items.items() if status(v) == "FAIL"]
    passes = [k for k, v in items.items() if status(v) == "PASS"]
    if fails:
        return "FAIL: " + ", ".join(fails)
    if passes:
        return f"PASS ({len(passes)}/{len(items)})"
    return "SKIP: " + "; ".join(sorted({v.split(":", 1)[-1].strip()[:80] for v in items.values()}))[:200]


def click_button_ext(form, timeout: float = 30) -> str:
    """click_button from a separate small process. Inside the IDE test (a Qt GUI thread) the attached-input click
    is not delivered reliably to Tk programs; a plain helper process clicks like the pipeline checks do."""
    py = sys.executable
    env = child_env(None)
    if FROZEN:
        env["RADIDE_AS_PYTHON"] = "1"
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from checks.common import click_button; "
            "print(click_button(int(sys.argv[2])))")
    try:
        r = subprocess.run([py, "-c", code, str(HERE), str(int(form))], capture_output=True, text=True,
                           timeout=timeout, env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return (r.stdout.strip() or r.stderr.strip()[-300:]) + " (helper process)"
    except subprocess.TimeoutExpired:
        return "helper process timed out"
