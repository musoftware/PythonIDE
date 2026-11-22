# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Shared harness of the end-to-end user journeys (samples/Tests/E2E/Web, samples/Tests/E2E/Mobile).

A journey drives the real IDE (``radide.app.MainWindow``, offscreen) the way a user does - New Project dialog,
code editor, designers, Databases workspace, Run (dev server + Preview), debugger, Publish - and records one
PASS / FAIL / SKIP line per step, with screenshots taken from the IDE's own widgets (``widget.grab()``), web pages
(``QWebEngineView.grab()``) and programs the journey started (``PrintWindow`` of their own window). Never a
full-screen capture.

    import e2e_lib as E
    j = E.Journey("Web", "php")              # creates the QApplication (own QSettings org RADIDE-TEST-E2EWEB)
    win = j.window()
    with j.step("create project"):
        ...
        j.check(cond, "detail")              # raises StepFailed when cond is false
        raise E.Skip("reason")               # SKIP
    j.finish()                               # results JSON + summary + exit code = number of failed steps

Output: ``E2E_OUT`` (default ``%TEMP%/radide-e2e``) / <area>-<journey> / {results.json, shots/, work/}.
"""
from __future__ import annotations

import contextlib
import ctypes
import html.parser
import http.cookiejar
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
REAL = os.environ.get("E2E_REAL") == "1"
if not REAL:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
os.environ.setdefault("RADIDE_PYWEB_NO_PROGRESS", "1")
os.environ.setdefault("RADIDE_CI_NO_UI", "1")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")      # Arabic text in the step details
except Exception:  # noqa: BLE001
    pass

ORG = os.environ.get("RADIDE_TEST_ORG", "RADIDE-TEST-E2EWEB")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Skip(Exception):
    """Raised inside a step: the step is SKIPped with this reason."""


class StepFailed(Exception):
    """Raised by Journey.check: the step FAILs with this detail."""


# ============================================================================ Qt helpers
_app = None


def qapp(name: str):
    global _app
    if _app is not None:
        return _app
    if os.name == "nt" and not REAL:
        # offscreen Qt draws text with FreeType, which keeps every opened font file as a C stdio stream; Arabic
        # text makes the font fallback open many system fonts and the UCRT default of 512 streams runs out, after
        # which every new glyph fails ("QFontEngineFT: Failed to create FreeType font engine") and painting
        # crawls. The real Windows platform plugin uses DirectWrite and is not affected.
        try:
            ctypes.cdll.ucrtbase._setmaxstdio(8192)
        except Exception:  # noqa: BLE001
            pass
    import PyQt6.QtWebEngineWidgets  # noqa: F401 - must be imported before the QApplication
    from PyQt6.QtCore import QCoreApplication, QSettings
    from PyQt6.QtWidgets import QApplication
    QCoreApplication.setOrganizationName(ORG)
    QCoreApplication.setApplicationName(f"{ORG}-{name}")
    try:        # like radide.app.main(): the Preview's DevTools port (JavaScript debugging in the Preview)
        from radide.web_site.browser_debug import enable_remote_debugging
        enable_remote_debugging()
    except Exception:  # noqa: BLE001
        pass
    _app = QApplication(sys.argv[:1])
    QSettings().clear()
    return _app


def pump(sec: float = 0.3) -> None:
    from PyQt6.QtWidgets import QApplication
    t = time.time() + sec
    while time.time() < t:
        QApplication.processEvents()
        time.sleep(0.01)


def wait(pred, timeout: float = 30.0, step: float = 0.05) -> bool:
    from PyQt6.QtWidgets import QApplication
    t = time.time() + timeout
    while time.time() < t:
        QApplication.processEvents()
        try:
            if pred():
                return True
        except Exception:  # noqa: BLE001 - a predicate may look at a half-built object
            pass
        time.sleep(step)
    try:
        return bool(pred())
    except Exception:  # noqa: BLE001
        return False


def js(page, expr: str, timeout: float = 15.0):
    """Evaluate *expr* in a QWebEnginePage and return its (JSON-able) value; 'ERR:...' on an exception."""
    box = {}
    page.runJavaScript(f"(function(){{try{{return ({expr});}}catch(e){{return 'ERR:'+e;}}}})()",
                       lambda v: box.setdefault("v", v))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def page_loaded(view, url_part: str = "", timeout: float = 30.0) -> bool:
    """Wait until the view's document is complete (and its URL contains url_part)."""
    def ok():
        if url_part and url_part not in view.url().toString():
            return False
        return js(view.page(), "document.readyState", 3) == "complete"
    return wait(ok, timeout, 0.2)


# ============================================================================ HTTP "browser"
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class FormParser(html.parser.HTMLParser):
    """The forms of a page: [{'action', 'method', 'fields': {name: value}, 'html_attrs'}]."""

    def __init__(self):
        super().__init__()
        self.forms: list[dict] = []
        self._cur = None
        self._select = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "form":
            self._cur = {"action": a.get("action", ""), "method": (a.get("method") or "get").lower(),
                         "fields": {}, "attrs": a}
            self.forms.append(self._cur)
        elif self._cur is not None and tag == "input" and a.get("name"):
            t = a.get("type", "text").lower()
            if t in ("checkbox", "radio") and "checked" not in a:
                return
            if t in ("submit", "button", "image", "file"):
                return
            self._cur["fields"][a["name"]] = a.get("value", "")
        elif self._cur is not None and tag in ("textarea",) and a.get("name"):
            self._cur["fields"][a["name"]] = ""
        elif self._cur is not None and tag == "select" and a.get("name"):
            self._select = a["name"]
            self._cur["fields"].setdefault(self._select, "")
        elif self._cur is not None and tag == "option" and self._select:
            if "selected" in a or not self._cur["fields"].get(self._select):
                self._cur["fields"][self._select] = a.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self._cur = None
        elif tag == "select":
            self._select = None


class Response:
    def __init__(self, url, status, headers, body: bytes, chain):
        self.url, self.status, self.headers, self.body, self.chain = url, status, headers, body, chain

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)

    @property
    def ctype(self) -> str:
        return self.headers.get("Content-Type", "") if self.headers else ""

    def forms(self) -> list[dict]:
        p = FormParser()
        p.feed(self.text)
        return p.forms

    def __repr__(self):
        return f"<{self.status} {self.url} {len(self.body)}B chain={self.chain}>"


class Browser:
    """A tiny cookie-keeping HTTP client: get / post / submit (fills a page's form like a user, keeping its
    hidden fields such as CSRF tokens). Redirects are followed by hand so every status of the chain is known."""

    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), _NoRedirect(),
                                                  urllib.request.ProxyHandler({}))

    def url(self, path: str) -> str:
        return path if path.startswith("http") else self.base + (path if path.startswith("/") else "/" + path)

    def request(self, method: str, path: str, data=None, headers=None, follow: bool = True,
                timeout: float = 60) -> Response:
        url = self.url(path)
        chain = []
        body = None
        hdrs = {"User-Agent": "RADIDE-E2E", "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
        hdrs.update(headers or {})
        if data is not None:
            if isinstance(data, (dict, list)) and hdrs.get("Content-Type", "").startswith("application/json"):
                body = json.dumps(data).encode()
            elif isinstance(data, (dict, list)):
                body = urllib.parse.urlencode(data).encode()
                hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
            else:
                body = data if isinstance(data, bytes) else str(data).encode()
        for _ in range(10):
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            try:
                with self.opener.open(req, timeout=timeout) as r:
                    status, rh, raw = r.status, r.headers, r.read()
            except urllib.error.HTTPError as e:
                status, rh, raw = e.code, e.headers, e.read()
            chain.append(status)
            loc = rh.get("Location") if rh else None
            if follow and status in (301, 302, 303, 307, 308) and loc:
                url = urllib.parse.urljoin(url, loc)
                if status in (301, 302, 303):
                    method, body = "GET", None
                    hdrs.pop("Content-Type", None)
                continue
            return Response(url, status, rh, raw, chain)
        return Response(url, status, rh, raw, chain)

    def get(self, path, **k) -> Response:
        return self.request("GET", path, **k)

    def post(self, path, data=None, **k) -> Response:
        return self.request("POST", path, data=data if data is not None else {}, **k)

    def submit(self, page_path: str, fields: dict, form_match: str = "", follow: bool = True,
               page: Response | None = None) -> Response:
        """GET page_path, pick the form whose action contains form_match (else the first form with a field
        named like one of *fields*), merge *fields* into its own (hidden) fields and send it."""
        page = page or self.get(page_path)
        forms = page.forms()
        if not forms:
            raise StepFailed(f"no <form> on {page_path} ({page.status})")
        form = None
        for f in forms:
            if form_match and form_match in f["action"]:
                form = f
                break
        if form is None:
            keys = set(fields)
            form = max(forms, key=lambda f: len(keys & set(f["fields"])) + (0.5 if f["method"] == "post" else 0))
        data = dict(form["fields"])
        data.update(fields)
        action = urllib.parse.urljoin(page.url, form["action"] or page.url)
        if form["method"] == "get":
            return self.get(action + ("&" if "?" in action else "?") + urllib.parse.urlencode(data), follow=follow)
        return self.post(action, data, follow=follow)

    def cookies(self) -> dict:
        return {c.name: c.value for c in self.jar}


# ============================================================================ process / window helpers
STARTED: list[subprocess.Popen] = []


def start(argv, cwd=None, env=None, log: Path | None = None) -> subprocess.Popen:
    """Start a program the journey owns (stopped by stop_all / finish)."""
    out = open(log, "w", encoding="utf-8", errors="replace") if log else subprocess.DEVNULL
    p = subprocess.Popen([str(a) for a in argv], cwd=str(cwd) if cwd else None, env=env, stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    STARTED.append(p)
    return p


def kill_tree(p: subprocess.Popen) -> None:
    if p is None or p.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, creationflags=NO_WINDOW)
    else:
        p.kill()
    try:
        p.wait(10)
    except Exception:  # noqa: BLE001
        pass


def stop_all() -> None:
    for p in STARTED:
        kill_tree(p)
    STARTED.clear()


def run(argv, cwd=None, env=None, timeout: float = 900) -> tuple[int, str]:
    """Run a command to completion: (exit code, combined output)."""
    try:
        r = subprocess.run([str(a) for a in argv], cwd=str(cwd) if cwd else None, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout,
                           stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        return -1, f"timeout after {timeout}s: {e}"
    except OSError as e:
        return -2, str(e)


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http_up(url: str, timeout: float = 60.0) -> bool:
    def ok():
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=3) as r:
                return r.status < 500
        except urllib.error.HTTPError as e:
            return e.code < 500
        except Exception:  # noqa: BLE001
            return False
    t = time.time() + timeout
    while time.time() < t:
        if ok():
            return True
        try:
            pump(0.4)
        except Exception:  # noqa: BLE001
            time.sleep(0.4)
    return ok()


def process_tree(pid_root: int) -> set[int]:
    """pid_root and all its descendants (Toolhelp32 snapshot; no wmic needed)."""
    if os.name != "nt":
        return {pid_root}
    import ctypes.wintypes as wt

    class PE(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    snap = k32.CreateToolhelp32Snapshot(2, 0)
    pairs = []
    e = PE()
    e.dwSize = ctypes.sizeof(PE)
    ok = k32.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        pairs.append((e.th32ParentProcessID, e.th32ProcessID))
        ok = k32.Process32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    pids = {pid_root}
    changed = True
    while changed:
        changed = False
        for ppid, pid in pairs:
            if ppid in pids and pid not in pids:
                pids.add(pid)
                changed = True
    return pids


def wait_window(proc: subprocess.Popen, title_part: str = "", timeout: float = 60.0):
    """(hwnd, title) of the first visible window of a started program (title contains title_part), or None."""
    box = {}

    def find():
        for h, t in windows_of(proc.pid):
            if title_part.lower() in t.lower() and t:
                box["w"] = (h, t)
                return True
        return False
    t0 = time.time()
    while time.time() - t0 < timeout:
        if find():
            return box["w"]
        if proc.poll() is not None:
            return None
        time.sleep(0.4)
    return None


def close_window(hwnd: int) -> None:
    """Ask a window to close (WM_CLOSE), like the user clicking X."""
    if os.name == "nt":
        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)


def windows_of(pid_root: int) -> list[tuple[int, str]]:
    """Visible top-level windows (hwnd, title) of a process tree."""
    if os.name != "nt":
        return []
    import ctypes.wintypes as wt
    pids = {pid_root}
    try:
        out = subprocess.run(["wmic", "process", "get", "ProcessId,ParentProcessId"], capture_output=True,
                             text=True, creationflags=NO_WINDOW, timeout=20).stdout.split()
        pairs = [(int(out[i]), int(out[i + 1])) for i in range(2, len(out) - 1, 2) if out[i].isdigit()]
        changed = True
        while changed:
            changed = False
            for ppid, pid in pairs:
                if ppid in pids and pid not in pids:
                    pids.add(pid)
                    changed = True
    except Exception:  # noqa: BLE001 - no wmic (removed from recent Windows 11): the Toolhelp snapshot
        pids = process_tree(pid_root)
    user32 = ctypes.windll.user32
    found = []
    proto = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(hwnd, _l):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            found.append((hwnd, buf.value))
        return True
    user32.EnumWindows(proto(cb), 0)
    return found


def print_window(hwnd: int, path: Path) -> bool:
    """Screenshot of one window (PrintWindow, PW_RENDERFULLCONTENT) - not the screen."""
    if os.name != "nt":
        return False
    import ctypes.wintypes as wt
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return False
    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    ok = user32.PrintWindow(hwnd, mdc, 2)

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                    ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                    ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                    ("biClrImportant", wt.DWORD)]
    bih = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)
    try:
        from PyQt6.QtGui import QImage
        img = QImage(buf.raw, w, h, w * 4, QImage.Format.Format_ARGB32).copy()
        return bool(ok) and img.save(str(path))
    except Exception:  # noqa: BLE001
        return False


# ============================================================================ the journey
class Journey:
    def __init__(self, area: str, name: str, title: str = ""):
        self.area, self.name, self.title = area, name, title or name
        base = Path(os.environ.get("E2E_OUT") or Path(tempfile.gettempdir()) / "radide-e2e")
        self.out = base / f"{area}-{name}"
        if self.out.exists() and os.environ.get("E2E_KEEP_WORK") != "1":
            shutil.rmtree(self.out / "shots", ignore_errors=True)
        self.shots = self.out / "shots"
        self.work = self.out / "work"
        self.shots.mkdir(parents=True, exist_ok=True)
        self.work.mkdir(parents=True, exist_ok=True)
        self.steps: list[dict] = []
        self._cur: dict | None = None
        self.msgs: list = []
        self.win = None
        self.t0 = time.time()
        self.app = qapp(f"{area}-{name}")
        self._patch_boxes()
        print(f"=== E2E {area} / {self.title}  (out: {self.out})", flush=True)

    # ------------------------------------------------------------ dialogs
    def _patch_boxes(self):
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication, QMessageBox
        msgs = self.msgs
        QMessageBox.question = staticmethod(lambda *a, **k: (msgs.append(("question", [str(x)[:300] for x in a[1:3]])),
                                                             QMessageBox.StandardButton.Yes)[1])
        for n in ("warning", "critical", "information"):
            setattr(QMessageBox, n, staticmethod(lambda *a, _n=n, **k: (
                msgs.append((_n, [str(x)[:300] for x in a[1:3]])), QMessageBox.StandardButton.Ok)[1]))
        self.allow_modal = set()

        def close_boxes():
            m = QApplication.activeModalWidget()
            if m is not None and m.windowTitle() not in self.allow_modal and not getattr(m, "_e2e_keep", False):
                msgs.append(("modal-closed", [m.windowTitle()]))
                print("  (closing unexpected modal:", m.windowTitle(), ")", flush=True)
                m.close()
        self._killer = QTimer()
        self._killer.timeout.connect(close_boxes)
        self._killer.start(1500)

    def window(self, w: int = 1600, h: int = 1000):
        from PyQt6.QtCore import QPoint
        from radide.app import MainWindow
        win = MainWindow()
        win.resize(w, h)
        if REAL:
            win.move(QPoint(-3000, 40))
        win.show()
        pump(2)
        self.win = win
        return win

    # ------------------------------------------------------------ steps
    @contextlib.contextmanager
    def step(self, name: str):
        rec = {"step": name, "status": "PASS", "detail": "", "shots": [], "sec": 0.0}
        self._cur = rec
        t = time.time()
        print(f"--- {name}", flush=True)
        try:
            yield rec
        except Skip as e:
            rec["status"], rec["detail"] = "SKIP", str(e)
        except StepFailed as e:
            rec["status"], rec["detail"] = "FAIL", str(e)
        except Exception as e:  # noqa: BLE001 - an exception is a failed step, the journey goes on
            rec["status"] = "FAIL"
            rec["detail"] = f"{type(e).__name__}: {e}"
            rec["trace"] = traceback.format_exc()[-2500:]
            print(rec["trace"], flush=True)
        rec["sec"] = round(time.time() - t, 1)
        self.steps.append(rec)
        self._cur = None
        line = f"{rec['status']} {name}" + (f"  [{rec['detail'][:900]}]" if rec["detail"] else "")
        print(line, flush=True)

    def selected(self, name: str | None = None) -> bool:
        """False when E2E_ONLY (comma separated step names) is set and does not list this step."""
        only = [s.strip() for s in os.environ.get("E2E_ONLY", "").split(",") if s.strip()]
        name = name or (self._cur or {}).get("step", "")
        return not only or name in only

    def gate(self) -> None:
        """First line of a step: SKIP it when E2E_ONLY does not select it (re-running one step of a journey)."""
        if not self.selected():
            raise Skip("not selected (E2E_ONLY)")

    def note(self, text: str) -> None:
        """Add text to the current step's detail (shown for PASS too)."""
        if self._cur is not None:
            self._cur["detail"] = (self._cur["detail"] + "; " if self._cur["detail"] else "") + str(text)[:600]

    def check(self, cond, detail: str = "") -> None:
        if not cond:
            raise StepFailed(detail or "check failed")

    def shot(self, widget, name: str) -> str:
        p = self.shots / f"{len(self.steps) + 1:02d}_{name}.png"
        try:
            pm = widget.grab()
            pm.save(str(p))
        except Exception as e:  # noqa: BLE001
            print("  shot failed", name, e, flush=True)
            return ""
        if self._cur is not None:
            self._cur["shots"].append(p.name)
        return str(p)

    def shot_window(self, hwnd: int, name: str) -> str:
        p = self.shots / f"{len(self.steps) + 1:02d}_{name}.png"
        if print_window(hwnd, p):
            if self._cur is not None:
                self._cur["shots"].append(p.name)
            return str(p)
        return ""

    # ------------------------------------------------------------ IDE actions shared by the journeys
    def new_project(self, language: str, template: str, name: str, location: Path | None = None):
        """File > New Project: pick the language group item + template, name, location, OK."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QTreeWidgetItemIterator
        from radide.dialogs import NewProjectDialog
        from radide.features.solution_ui import create_project_from_dialog
        win = self.win
        dlg = NewProjectDialog(win)
        itr = QTreeWidgetItemIterator(dlg.langs)
        item = None
        while itr.value():
            if itr.value().data(0, Qt.ItemDataRole.UserRole) == language:
                item = itr.value()
            itr += 1
        self.check(item is not None, f"New Project has no language {language}")
        dlg.langs.setCurrentItem(item)
        pump(0.2)
        ids = [dlg.templates.item(i).data(Qt.ItemDataRole.UserRole) for i in range(dlg.templates.count())]
        self.check(template in ids, f"New Project > {language} has no template {template}: {ids}")
        dlg.templates.setCurrentRow(ids.index(template))
        loc = location or self.work
        dlg.location.setText(str(loc))
        dlg.name.setText(name)
        pump(0.1)
        self.shot(dlg, f"new_project_{language}")
        prj = create_project_from_dialog(win, dlg)
        dlg.deleteLater()
        pump(1.0)
        self.check(prj is not None, f"project not created; messages: {self.msgs[-3:]}")
        return prj

    def edit(self, path: Path, text: str, save: bool = True):
        """Open a file in the IDE's code editor (Solution Explorer double-click), replace its text, save."""
        from radide.features import web_workspace as ww
        path = Path(path)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            ww.create_file(self.win, path.parent, path.name, "")
            pump(0.2)
        ed = ww.open_file(self.win, path)
        self.check(ed is not None, f"the editor did not open {path}")
        ed.setText(text)
        pump(0.1)
        if save:
            self.win.save_all()
            pump(0.2)
            got = path.read_text(encoding="utf-8")
            self.check(got.replace("\r\n", "\n").strip() == text.replace("\r\n", "\n").strip(),
                       f"saved file differs: {path} ({len(got)} vs {len(text)} chars)")
        return ed

    def write_files(self, folder: Path, files: dict[str, str]) -> list[str]:
        """New File (Solution Explorer > Add > New File) + editor + Save for every file."""
        done = []
        for rel, text in files.items():
            self.edit(Path(folder) / rel, text)
            done.append(rel)
        return done

    def messages_since(self, n: int) -> list:
        return self.msgs[n:]

    def output_text(self) -> str:
        try:
            return self.win.output.toPlainText()
        except Exception:  # noqa: BLE001
            return ""

    # ------------------------------------------------------------ end
    def counts(self) -> dict:
        c = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        for s in self.steps:
            c[s["status"]] += 1
        return c

    def finish(self, close: bool = True):
        c = self.counts()
        res = {"area": self.area, "journey": self.name, "title": self.title, "counts": c, "steps": self.steps,
               "messages": self.msgs[-60:], "seconds": round(time.time() - self.t0)}
        (self.out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"=== {self.area}/{self.title}: {c['PASS']} passed, {c['FAIL']} failed, {c['SKIP']} skipped "
              f"of {len(self.steps)} steps; FAILED: {[s['step'] for s in self.steps if s['status'] == 'FAIL'] or 'none'}",
              flush=True)
        if close and self.win is not None:
            try:
                from radide.features import web_workspace as ww
                ww.stop_website(self.win)
            except Exception:  # noqa: BLE001
                pass
            try:
                self.win.close()
                pump(1.5)
            except Exception as e:  # noqa: BLE001
                print("close error", e, flush=True)
        stop_all()
        try:
            from PyQt6.QtCore import QSettings
            QSettings().clear()
        except Exception:  # noqa: BLE001
            pass
        sys.stdout.flush()
        os._exit(min(c["FAIL"], 100))
