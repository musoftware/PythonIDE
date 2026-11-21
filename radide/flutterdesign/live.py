"""Live preview of designed Flutter screens (docs/FLUTTER_DESIGNER.md section 8).

Two modes:

* **Live** (default): ``preview_host/`` is a small Flutter web app that renders a ``*.fscreen.json`` tree with the
  real Flutter widgets. It is built once per Flutter SDK version (``flutter build web --release``) into
  ``%LOCALAPPDATA%\\RADIDE\\flutter-preview-host\\<flutter version>-<source hash>\\``, served together with the
  project folder (assets, fonts) by a small local HTTP server, and shown in a QWebEngineView. Python pushes the
  screen and then only model patches (debounced); the host answers with node rects, clicks, hovers and issues.
* **Exact**: the real generated project (``codegen.write_all``) runs with ``flutter run -d web-server`` in the same
  view; saving hot-reloads it - full fidelity for hand-written code / Code nodes.

Qt objects: ``LivePreview`` (the engine: server + page + bridge, no UI of its own), ``ExactRunner`` and
``PreviewPane`` (a ready-made widget: tool bar + view, used by the designer). Everything else is plain Python.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import mimetypes
import os
import re
import shutil
import socketserver
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path

from PyQt6.QtCore import QFile, QIODevice, QObject, QPointF, QRectF, Qt, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout,
                             QWidget)

HOST_SRC = Path(__file__).resolve().parent / "preview_host"
HOST_VERSION = 1
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# name, width, height (logical px, portrait), platform
DEVICES = [
    ("iPhone 15", 393, 852, "ios"),
    ("iPhone SE", 375, 667, "ios"),
    ("iPhone 15 Pro Max", 430, 932, "ios"),
    ("Pixel 8", 412, 915, "android"),
    ("Pixel 5", 393, 851, "android"),
    ("Galaxy S20", 360, 800, "android"),
    ("iPad mini", 744, 1133, "ios"),
    ("Android tablet", 800, 1280, "android"),
    ("Desktop 1280x800", 1280, 800, "android"),
]


# ======================================================================================== host build
_FLUTTER_HINTS = [str(Path(p) / "bin" / "flutter.bat") for p in (r"C:\flutter", r"C:\src\flutter", r"C:\tools\flutter")]
_FLUTTER_HINTS.insert(2, str(Path.home() / "flutter" / "bin" / "flutter.bat"))


def _flutter() -> tuple[str, str]:
    """(flutter executable, SDK root) - same search as radide.languages.flutter (PATH, then usual folders)."""
    exe = ""
    for name in ("flutter.bat", "flutter"):
        exe = shutil.which(name) or ""
        if exe:
            break
    if not exe:
        exe = next((h for h in _FLUTTER_HINTS if Path(h).exists()), "")
    return exe, (str(Path(exe).resolve().parent.parent) if exe else "")


def flutter_version() -> str:
    """Framework version of the installed SDK ('' when Flutter is missing)."""
    _exe, root = _flutter()
    if not root:
        return ""
    for f in (Path(root) / "bin" / "cache" / "flutter.version.json",):
        try:
            return str(json.loads(f.read_text(encoding="utf-8")).get("frameworkVersion") or "")
        except (OSError, ValueError):
            pass
    try:
        return (Path(root) / "version").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _source_files() -> list[Path]:
    out = [HOST_SRC / "pubspec.yaml"]
    for sub in ("lib", "web"):
        out += sorted(p for p in (HOST_SRC / sub).rglob("*") if p.is_file())
    return [p for p in out if p.exists()]


def host_source_hash() -> str:
    h = hashlib.sha1(f"v{HOST_VERSION}".encode())
    for p in _source_files():
        h.update(p.relative_to(HOST_SRC).as_posix().encode())
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def cache_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "RADIDE" / "flutter-preview-host"


def host_work_dir() -> Path:
    ver = re.sub(r"[^0-9A-Za-z.]+", "_", flutter_version() or "noflutter")
    return cache_root() / f"{ver}-{host_source_hash()}"


def host_build_dir() -> Path:
    return host_work_dir() / "build" / "web"


def host_ready() -> bool:
    d = host_build_dir()
    return (d / "index.html").exists() and (d / "main.dart.js").exists() and (host_work_dir() / "ok.json").exists()


_ICON_RX = re.compile(r"static const IconData (\w+)\s*=\s*IconData\(\s*(0x[0-9a-fA-F]+)\s*,([^)]*)\)", re.S)


def generate_icons_dart(sdk_root: str | Path) -> str:
    """lib/icons_gen.dart: Icons.* / CupertinoIcons.* name -> code point (bit 20 = matchTextDirection)."""
    def table(path: Path) -> list[str]:
        rows = []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return rows
        seen = set()
        for m in _ICON_RX.finditer(text):
            name, cp, rest = m.group(1), int(m.group(2), 16), m.group(3)
            if name in seen:
                continue
            seen.add(name)
            if "matchTextDirection: true" in rest:
                cp |= 0x100000
            rows.append(f"  '{name}': 0x{cp:x},")
        return rows
    lib = Path(sdk_root) / "packages" / "flutter" / "lib" / "src"
    mat = table(lib / "material" / "icons.dart")
    cup = table(lib / "cupertino" / "icons.dart")
    return ("// GENERATED by radide/flutterdesign/live.py from the Flutter SDK - do not edit.\n"
            "const Map<String, int> materialIcons = {\n" + "\n".join(mat) + "\n};\n"
            "const Map<String, int> cupertinoIcons = {\n" + "\n".join(cup) + "\n};\n")


def prepare_work_dir(log=print) -> Path:
    """Copy the host source into the cache work dir and generate the icon tables (no flutter call)."""
    _exe, root = _flutter()
    work = host_work_dir()
    work.mkdir(parents=True, exist_ok=True)
    for p in _source_files():
        dst = work / p.relative_to(HOST_SRC)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dst)
    for extra in ("analysis_options.yaml",):
        if (HOST_SRC / extra).exists():
            shutil.copyfile(HOST_SRC / extra, work / extra)
    (work / "lib" / "icons_gen.dart").write_text(generate_icons_dart(root), encoding="utf-8")
    (work / "ok.json").unlink(missing_ok=True)
    log(f"preview host source -> {work}\n")
    return work


def build_steps(work: Path) -> list[list[str]]:
    exe, _root = _flutter()
    steps = []
    if not (work / ".dart_tool" / "package_config.json").exists():
        steps.append([exe, "pub", "get", "--offline"])
    steps.append([exe, "build", "web", "--release", "--no-tree-shake-icons", "--no-web-resources-cdn",
                  "--no-wasm-dry-run", "--no-source-maps"])
    return steps


def finish_build(work: Path) -> bool:
    ok = (work / "build" / "web" / "main.dart.js").exists()
    if ok:
        (work / "ok.json").write_text(json.dumps({"flutter": flutter_version(), "hash": host_source_hash(),
                                                  "built": time.strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
        # old builds (other Flutter versions / host sources) are removed
        for d in cache_root().iterdir():
            if d.is_dir() and d != work:
                shutil.rmtree(d, ignore_errors=True)
    return ok


def build_host_sync(log=print, timeout: int = 1200) -> Path:
    """Build the host now (blocking) - tests / command line. Returns build/web."""
    exe, _root = _flutter()
    if not exe:
        raise RuntimeError("Flutter SDK not found")
    if host_ready():
        return host_build_dir()
    work = prepare_work_dir(log)
    for argv in build_steps(work):
        log("> flutter " + " ".join(argv[1:]) + "\n")
        r = subprocess.run(argv, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, creationflags=CREATE_NO_WINDOW)
        log(r.stdout[-4000:] + r.stderr[-4000:])
        if r.returncode != 0 and argv[-1] == "--offline":
            r = subprocess.run(argv[:-1], cwd=work, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout, creationflags=CREATE_NO_WINDOW)
            log(r.stdout[-4000:] + r.stderr[-4000:])
        if r.returncode != 0:
            raise RuntimeError(f"flutter {' '.join(argv[1:3])} failed ({r.returncode})")
    if not finish_build(work):
        raise RuntimeError("flutter build web produced no main.dart.js")
    return host_build_dir()


class HostBuilder(QObject):
    """Builds the host in the background (QProcess steps). finished(ok, build_dir)."""
    output = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps = None
        self._work: Path | None = None

    def running(self) -> bool:
        return self._steps is not None and self._steps.running()

    def start(self) -> None:
        from ..features.mobile import StepProcess
        if host_ready():
            QTimer.singleShot(0, lambda: self.finished.emit(True, str(host_build_dir())))
            return
        exe, _root = _flutter()
        if not exe:
            QTimer.singleShot(0, lambda: self.finished.emit(False, "Flutter SDK not found"))
            return
        try:
            self._work = prepare_work_dir(self.output.emit)
        except OSError as e:
            QTimer.singleShot(0, lambda err=str(e): self.finished.emit(False, err))
            return
        self.output.emit("Building the Flutter preview host (once per Flutter version, about a minute)...\n")
        self._steps = StepProcess(build_steps(self._work), self._work, self)
        self._steps.output.connect(self.output.emit)
        self._steps.finished.connect(self._done)
        self._steps.start()

    def _done(self, code: int) -> None:
        ok = code == 0 and self._work is not None and finish_build(self._work)
        self.finished.emit(ok, str(host_build_dir()) if ok else f"flutter build web failed ({code})")

    def cancel(self) -> None:
        if self._steps is not None:
            self._steps.cancel()


# ======================================================================================= HTTP server
_MIME = {".js": "text/javascript", ".mjs": "text/javascript", ".wasm": "application/wasm", ".json": "application/json",
         ".ttf": "font/ttf", ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2", ".svg": "image/svg+xml",
         ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
         ".html": "text/html; charset=utf-8", ".css": "text/css", ".frag": "application/octet-stream",
         ".bin": "application/octet-stream"}


class _Handler(http.server.BaseHTTPRequestHandler):
    server_version = "RADPreview/1"

    def log_message(self, *a):          # quiet
        pass

    def _resolve(self) -> Path | None:
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        srv = self.server
        if path.startswith("/project/"):
            root = srv.project_dir           # type: ignore[attr-defined]
            rel = path[len("/project/"):]
        else:
            root = srv.host_dir              # type: ignore[attr-defined]
            rel = path.lstrip("/") or "index.html"
        if root is None:
            return None
        root = Path(root).resolve()
        p = (root / rel).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            return None
        if p.is_dir():
            p = p / "index.html"
        return p if p.is_file() else None

    def do_HEAD(self):
        self.do_GET(head=True)

    def do_GET(self, head: bool = False):
        p = self._resolve()
        if p is None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            data = p.read_bytes()
        except OSError:
            self.send_response(500)
            self.end_headers()
            return
        ctype = _MIME.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if not head:
            try:
                self.wfile.write(data)
            except (ConnectionError, OSError):
                pass


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class PreviewServer:
    """127.0.0.1 static server: / = the built host, /project/ = the project folder (assets, fonts)."""

    def __init__(self):
        self._srv: _Server | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return self._srv.server_address[1] if self._srv else 0

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/" if self._srv else ""

    def start(self, host_dir, project_dir=None) -> int:
        if self._srv is None:
            self._srv = _Server(("127.0.0.1", 0), _Handler)
            self._thread = threading.Thread(target=self._srv.serve_forever, name="flutter-preview-http",
                                            daemon=True)
            self._thread.start()
        self._srv.host_dir = str(host_dir) if host_dir else None        # type: ignore[attr-defined]
        self._srv.project_dir = str(project_dir) if project_dir else None  # type: ignore[attr-defined]
        return self.port

    def set_project(self, project_dir) -> None:
        if self._srv is not None:
            self._srv.project_dir = str(project_dir) if project_dir else None  # type: ignore[attr-defined]

    def stop(self) -> None:
        if self._srv is not None:
            self._srv.shutdown()
            self._srv.server_close()
            self._srv = None


# ============================================================================================ engine
class _Bridge(QObject):
    received = pyqtSignal(str)

    @pyqtSlot(str)
    def post(self, msg: str) -> None:
        self.received.emit(msg)


def _qwebchannel_js() -> str:
    f = QFile(":/qtwebchannel/qwebchannel.js")
    if f.open(QIODevice.OpenModeFlag.ReadOnly):
        try:
            return bytes(f.readAll()).decode("utf-8")
        finally:
            f.close()
    return ""


def _screen_dict(screen) -> dict:
    if screen is None:
        return {}
    if hasattr(screen, "to_dict"):
        return screen.to_dict()
    return screen


class LivePreview(QObject):
    """Server + page + bridge of the live preview (no widgets of its own besides ``view``).

    Push: ``set_screen(screen)``, ``push_patch(patch)`` (model patches, debounced into one message per event-loop
    burst), ``select(id)``, ``hover(id)``, ``set_device(...)``, ``set_mode('design'|'interact')``, ``play()``,
    ``set_app_theme(spec)``, ``set_project(folder)``. Receive: the signals below; ``rects`` holds the last node
    rects (view coordinates), ``issues`` the last issue list.
    """
    ready = pyqtSignal()                      # host loaded (state re-sent)
    rendered = pyqtSignal(int, float)         # seq, ms from the push to the frame being on screen
    rectsChanged = pyqtSignal(dict)           # id -> QRectF (view coordinates)
    nodeClicked = pyqtSignal(str, dict)       # id, message (path deepest..root, x, y, shift, ctrl)
    nodeDoubleClicked = pyqtSignal(str, dict)
    contextRequested = pyqtSignal(str, dict)
    nodeHovered = pyqtSignal(str)             # '' = none
    issuesChanged = pyqtSignal(list)          # [{"id", "level", "message"}]
    eventFired = pyqtSignal(dict)             # interact mode: {"id", "event", "handler", "value"}
    log = pyqtSignal(str, str)                # level, text
    statusChanged = pyqtSignal(str)
    buildOutput = pyqtSignal(str)

    DEBOUNCE_MS = 12

    def __init__(self, view=None, parent=None):
        super().__init__(parent)
        from PyQt6.QtWebChannel import QWebChannel
        from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineScript, QWebEngineSettings
        from PyQt6.QtWebEngineWidgets import QWebEngineView

        self.view = view if view is not None else QWebEngineView()
        self.view.setProperty("i18n_skip", True)
        outer = self

        class _Page(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, line, source):    # noqa: N802
                if message.startswith("RADHOST:"):
                    outer._on_message(message[8:])
                elif level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                    outer.log.emit("error", f"{message} ({source}:{line})")

        self.page = _Page(self.view)
        self.view.setPage(self.page)
        s = self.page.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, False)
        js = _qwebchannel_js()
        if js:
            sc = QWebEngineScript()
            sc.setName("qwebchannel")
            sc.setSourceCode(js)
            sc.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            sc.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            sc.setRunsOnSubFrames(False)
            self.page.scripts().insert(sc)
        self._bridge = _Bridge(self)
        self._bridge.received.connect(self._on_message)
        self._channel = QWebChannel(self.page)
        self._channel.registerObject("radBridge", self._bridge)
        self.page.setWebChannel(self._channel)
        self.page.loadFinished.connect(self._on_load)

        self.server = PreviewServer()
        self.builder: HostBuilder | None = None
        self.exact: ExactRunner | None = None
        self.project_dir: str | None = None
        self.is_ready = False
        self.mode = "design"
        self.device = {"width": 393, "height": 852, "textScale": 1.0, "dark": False, "frame": True,
                       "platform": "ios", "rtl": False, "zoom": None}
        self.app_theme: dict | None = None
        self.selected: str | None = None
        self.rects: dict[str, QRectF] = {}
        self.hidden: list[str] = []
        self.device_rect = QRectF()
        self.issues: list[dict] = []
        self.last_latency_ms = 0.0
        self._screen = None              # Screen object or dict (the caller's - re-read on resync)
        self._seq = 0
        self._sent: dict[int, float] = {}
        self._queue: list[dict] = []      # messages waiting for "ready"
        self._ops: list[dict] = []        # debounced patch ops
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_ops)

    # ------------------------------------------------------------------------------------- lifecycle
    def start(self, project_dir=None) -> None:
        """Serve and load the host (building it first when needed)."""
        if project_dir is not None:
            self.project_dir = str(project_dir)
        if host_ready():
            self._serve(host_build_dir())
            return
        if self.builder is not None and self.builder.running():
            return
        self.statusChanged.emit("Building the Flutter preview host...")
        self.builder = HostBuilder(self)
        self.builder.output.connect(self.buildOutput.emit)
        self.builder.finished.connect(self._built)
        self.builder.start()

    def _built(self, ok: bool, info: str) -> None:
        if ok:
            self._serve(Path(info))
        else:
            self.statusChanged.emit(f"Preview host build failed: {info}")
            self.log.emit("error", info)

    def _serve(self, build_dir: Path) -> None:
        self.server.start(build_dir, self.project_dir)
        self.is_ready = False
        self.view.setUrl(QUrl(self.server.url + f"?v={host_source_hash()}"))
        self.statusChanged.emit("Loading the preview...")

    def reload(self) -> None:
        self.is_ready = False
        if self.server.port:
            self.view.setUrl(QUrl(self.server.url + f"?v={host_source_hash()}&t={int(time.time())}"))

    def shutdown(self) -> None:
        if self.exact is not None:
            self.exact.stop()
            self.exact = None
        if self.builder is not None:
            self.builder.cancel()
        self.server.stop()

    def set_project(self, project_dir) -> None:
        self.project_dir = str(project_dir) if project_dir else None
        self.server.set_project(self.project_dir)
        self.send({"type": "config", "assetBase": "/project/"})

    def _on_load(self, ok: bool) -> None:
        if not ok and self.exact is None:
            self.statusChanged.emit("The preview page did not load")

    # ------------------------------------------------------------------------------------------ push
    def send(self, msg: dict) -> None:
        if not self.is_ready:
            # state messages are re-sent on ready anyway; keep only one-shot ones
            if msg.get("type") in ("play", "stop", "rects"):
                self._queue.append(msg)
            return
        self._js(msg)

    def _js(self, msg: dict) -> None:
        text = json.dumps(json.dumps(msg, ensure_ascii=False))
        self.page.runJavaScript(f"window.radHost && window.radHost.deliver({text});")

    def _next_seq(self) -> int:
        self._seq += 1
        self._sent[self._seq] = time.perf_counter()
        if len(self._sent) > 200:
            for k in sorted(self._sent)[:100]:
                self._sent.pop(k, None)
        return self._seq

    def set_screen(self, screen) -> None:
        """Show a screen (a model.Screen or its dict). Later edits: push_patch() or set_screen() again."""
        self._screen = screen
        self._ops.clear()
        self._flush_timer.stop()
        self.send({"type": "screen", "screen": _screen_dict(screen), "seq": self._next_seq()})

    def resync(self) -> None:
        if self._screen is not None:
            self.set_screen(self._screen)

    def push_patch(self, patch: list) -> None:
        """A model patch (model.insert / set_prop / ... result, or model.invert(...) for undo) already applied
        to the screen given to set_screen(). Sent debounced: all patches of one burst go in one message."""
        if not patch:
            return
        self._ops.extend(patch)
        if not self._flush_timer.isActive():
            self._flush_timer.start(self.DEBOUNCE_MS)

    def _flush_ops(self) -> None:
        if not self._ops:
            return
        ops, self._ops = self._ops, []
        if not self.is_ready:
            return            # the whole screen is sent on ready
        self._js({"type": "patch", "ops": ops, "seq": self._next_seq()})

    def select(self, node_id: str | None, reveal: bool = False) -> None:
        self.selected = node_id
        self.send({"type": "select", "id": node_id, "reveal": reveal})

    def hover(self, node_id: str | None) -> None:
        self.send({"type": "hover", "id": node_id})

    def set_device(self, width=None, height=None, **opts) -> None:
        """width / height (logical px), textScale, dark, frame, platform ('ios' | 'android'), rtl, zoom (None=fit)."""
        if width is not None:
            self.device["width"] = float(width)
        if height is not None:
            self.device["height"] = float(height)
        self.device.update({k: v for k, v in opts.items() if k in ("textScale", "dark", "frame", "platform",
                                                                   "rtl", "zoom")})
        self.send({"type": "device", **self.device, "seq": self._next_seq()})

    def rotate(self) -> None:
        self.set_device(self.device["height"], self.device["width"])

    def set_mode(self, mode: str) -> None:
        self.mode = "interact" if mode == "interact" else "design"
        self.send({"type": "mode", "mode": self.mode, "seq": self._next_seq()})

    def play(self) -> None:
        self.send({"type": "play", "seq": self._next_seq()})

    def stop_animations(self) -> None:
        self.send({"type": "stop", "seq": self._next_seq()})

    def set_app_theme(self, spec: dict | None) -> None:
        self.app_theme = spec
        self.send({"type": "config", "appTheme": spec, "seq": self._next_seq()})

    def request_rects(self) -> None:
        self.send({"type": "rects"})

    # --------------------------------------------------------------------------------------- receive
    def _on_message(self, text: str) -> None:
        try:
            m = json.loads(text)
        except ValueError:
            return
        t = m.get("type")
        if t == "ready":
            self.is_ready = True
            self._js({"type": "config", "assetBase": "/project/", "appTheme": self.app_theme})
            self._js({"type": "device", **self.device})
            self._js({"type": "mode", "mode": self.mode})
            if self._screen is not None:
                self._ops.clear()
                self._js({"type": "screen", "screen": _screen_dict(self._screen), "seq": self._next_seq()})
            if self.selected:
                self._js({"type": "select", "id": self.selected})
            for q in self._queue:
                self._js(q)
            self._queue.clear()
            self.statusChanged.emit("Live preview ready")
            self.ready.emit()
        elif t == "rendered":
            seq = int(m.get("seq") or 0)
            t0 = self._sent.pop(seq, None)
            ms = (time.perf_counter() - t0) * 1000 if t0 is not None else float(m.get("ms") or 0)
            self.last_latency_ms = ms
            self.rendered.emit(seq, ms)
        elif t == "rects":
            self.rects = {k: QRectF(*v) for k, v in (m.get("rects") or {}).items() if len(v) == 4}
            self.hidden = list(m.get("hidden") or [])
            d = m.get("device")
            self.device_rect = QRectF(*d) if d else QRectF()
            self.rectsChanged.emit(self.rects)
        elif t in ("click", "dblclick", "context"):
            nid = m.get("id") or ""
            if t == "click":
                self.selected = nid or None
                self.nodeClicked.emit(nid, m)
            elif t == "dblclick":
                self.nodeDoubleClicked.emit(nid, m)
            else:
                self.contextRequested.emit(nid, m)
        elif t == "hover":
            self.nodeHovered.emit(m.get("id") or "")
        elif t == "issues":
            self.issues = list(m.get("issues") or [])
            self.issuesChanged.emit(self.issues)
        elif t == "event":
            self.eventFired.emit(m)
        elif t == "log":
            level = m.get("level", "info")
            self.log.emit(level, str(m.get("text", "")))
            if level == "error" and "patch:" in str(m.get("text", "")):
                self.resync()           # the host tree diverged: send the whole screen again
        elif t == "pong":
            pass

    # ------------------------------------------------------------------------------------- helpers
    def node_at(self, pos: QPointF) -> str | None:
        """The smallest node rect containing *pos* (view coordinates) - Python-side hit test."""
        best, area = None, None
        for k, r in self.rects.items():
            if r.contains(pos):
                a = r.width() * r.height()
                if area is None or a < area:
                    best, area = k, a
        return best

    def issues_of(self, node_id: str) -> list[dict]:
        return [i for i in self.issues if i.get("id") == node_id]

    # ----------------------------------------------------------------------------------------- exact
    def start_exact(self, project_dir, route: str = "/") -> None:
        """Run the generated project (flutter run -d web-server) in the view; ``exact_reload()`` after saves."""
        self.stop_exact(load_host=False)
        self.exact = ExactRunner(project_dir, route, self)
        self.exact.output.connect(self.buildOutput.emit)
        self.exact.status.connect(self.statusChanged.emit)
        self.exact.urlReady.connect(self._exact_load)
        self.exact.finished.connect(lambda code: self.statusChanged.emit(f"Exact preview stopped ({code})"))
        self.is_ready = False
        self.exact.start()

    EXACT_WATCHDOG_S = 25

    def _exact_load(self, url: str) -> None:
        """Load the served app. A watchdog reloads the page (twice at most) when the app connected to
        flutter run but has not created its Flutter view 25 s later - QtWebEngine sometimes keeps the first
        debug load blank. (Before the connection the debug compile is still running: no reload then.)"""
        self.view.setUrl(QUrl(url))
        self._exact_t0 = 0.0
        self._exact_reloads = 0
        if getattr(self, "_exact_timer", None) is None:
            self._exact_timer = QTimer(self)
            self._exact_timer.setInterval(2000)
            self._exact_timer.timeout.connect(self._exact_watch)
        self._exact_timer.start()

    def _exact_watch(self) -> None:
        sess = self.exact.session if self.exact is not None else None
        if sess is None:
            self._exact_timer.stop()
            return
        if not sess.ready:
            return
        if not self._exact_t0:
            self._exact_t0 = time.time()

        def seen(has_view) -> None:
            if not self._exact_timer.isActive() or self.exact is None:
                return
            if has_view:
                self._exact_timer.stop()
            elif time.time() - self._exact_t0 > self.EXACT_WATCHDOG_S:
                if self._exact_reloads >= 2:
                    self._exact_timer.stop()
                    self.statusChanged.emit("Exact preview: the app did not start - see the build output")
                    return
                self._exact_reloads += 1
                self._exact_t0 = time.time()
                self.statusChanged.emit("Exact preview: reloading the page...")
                self.view.reload()
        self.page.runJavaScript("!!document.querySelector('flutter-view, flt-glass-pane')", seen)

    def exact_reload(self) -> bool:
        return self.exact.reload() if self.exact is not None else False

    def stop_exact(self, load_host: bool = True) -> None:
        if getattr(self, "_exact_timer", None) is not None:
            self._exact_timer.stop()
        if self.exact is not None:
            self.exact.stop()
            self.exact = None
            if load_host:
                self.start()


# ============================================================================================ exact
def _free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _package_of(folder: Path) -> str:
    try:
        m = re.search(r"^name:\s*([A-Za-z_]\w*)", (folder / "pubspec.yaml").read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    except OSError:
        pass
    return re.sub(r"\W+", "_", folder.name.lower()) or "app"


class ExactRunner(QObject):
    """The generated project under ``flutter run -d web-server`` (hot reload on save)."""
    output = pyqtSignal(str)
    status = pyqtSignal(str)
    urlReady = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, project_dir, route: str = "/", parent=None):
        super().__init__(parent)
        self.folder = Path(project_dir)
        self.route = route or "/"
        self.port = _free_port()
        self.session = None
        self.url = ""
        self._buf = ""

    def regenerate(self) -> None:
        from . import codegen
        try:
            codegen.write_all(self.folder)
        except Exception as e:     # noqa: BLE001 - a broken screen must not kill the run
            self.output.emit(f"code generation failed: {e}\n")

    def start(self) -> None:
        from ..features.mobile import FlutterSession
        self.regenerate()
        dev = {"id": "web-server", "name": "Exact preview", "platform": "web", "port": self.port}
        self.session = FlutterSession(self.folder, dev, _package_of(self.folder), self,
                                      extra_args=["--web-hostname", "127.0.0.1"])
        self.session.output.connect(self._read)
        self.session.status.connect(self.status.emit)
        self.session.failed.connect(lambda t: self.status.emit(t))
        self.session.finished.connect(self.finished.emit)
        self.status.emit("Starting flutter run -d web-server (the first compile takes a while)...")
        self.session.start()

    def _read(self, text: str) -> None:
        self.output.emit(text)
        if self.url:
            return
        self._buf = (self._buf + text)[-4000:]
        m = re.search(r"is being served at\s+(http://\S+)", self._buf) or \
            re.search(r"(http://(?:localhost|127\.0\.0\.1):%d\S*)" % self.port, self._buf)
        if m:
            base = m.group(1).rstrip("/.")
            self.url = f"{base}/#{self.route}"
            self.status.emit(f"Exact preview: {self.url}")
            self.urlReady.emit(self.url)

    def reload(self) -> bool:
        """Regenerate the screens and hot reload (hot restart when the reload is rejected)."""
        if self.session is None:
            return False
        self.regenerate()
        return self.session.hot_reload() or self.session.hot_restart()

    def stop(self) -> None:
        if self.session is not None:
            self.session.stop()


# ====================================================================================== the widget
class PreviewPane(QWidget):
    """Tool bar (device, rotate, dark, text size, RTL, Design / Interact, Play, Exact) + the live view.

    ``pane.live`` is the LivePreview; the designer connects its signals (nodeClicked -> select in the tree,
    rectsChanged, issuesChanged) and calls ``pane.live.set_screen / push_patch / select``.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("flutterPreviewPane")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        bar = QHBoxLayout()
        bar.setContentsMargins(4, 2, 4, 2)
        bar.setSpacing(4)
        self.cbo_device = QComboBox()
        self.cbo_device.setToolTip("Device size")
        for name, w, h, pf in DEVICES:
            self.cbo_device.addItem(f"{name}  {w}x{h}", (w, h, pf))
        self.btn_rotate = QToolButton(text="Rotate")
        self.btn_rotate.setToolTip("Portrait / landscape")
        self.chk_dark = QCheckBox("Dark")
        self.chk_frame = QCheckBox("Frame")
        self.chk_frame.setChecked(True)
        self.chk_rtl = QCheckBox("RTL")
        self.cbo_scale = QComboBox()
        self.cbo_scale.setToolTip("Text scale")
        for s in (0.85, 1.0, 1.15, 1.3, 1.5, 2.0):
            self.cbo_scale.addItem(f"Aa {int(s * 100)}%", s)
        self.cbo_scale.setCurrentIndex(1)
        self.cbo_mode = QComboBox()
        self.cbo_mode.addItem("Design", "design")
        self.cbo_mode.addItem("Interact", "interact")
        self.cbo_mode.setToolTip("Design: clicks select widgets - Interact: use the screen like the app")
        self.btn_play = QToolButton(text="Play")
        self.btn_play.setToolTip("Play the entrance animations")
        self.btn_exact = QToolButton(text="Exact")
        self.btn_exact.setCheckable(True)
        self.btn_exact.setToolTip("Run the generated project with flutter run (full fidelity, hot reload on save)")
        for w in (self.cbo_device, self.btn_rotate, self.chk_dark, self.chk_frame, self.chk_rtl, self.cbo_scale,
                  self.cbo_mode, self.btn_play, self.btn_exact):
            bar.addWidget(w)
        bar.addStretch(1)
        self.lbl_status = QLabel("")
        self.lbl_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        bar.addWidget(self.lbl_status, 2)
        lay.addLayout(bar)
        self.live = LivePreview(parent=self)
        self.view = self.live.view
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        lay.addWidget(self.view, 1)
        self.project_dir: str | None = None
        self.route = "/"

        self.cbo_device.currentIndexChanged.connect(self._device_changed)
        self.btn_rotate.clicked.connect(self.live.rotate)
        self.chk_dark.toggled.connect(lambda v: self.live.set_device(dark=v))
        self.chk_frame.toggled.connect(lambda v: self.live.set_device(frame=v))
        self.chk_rtl.toggled.connect(lambda v: self.live.set_device(rtl=v))
        self.cbo_scale.currentIndexChanged.connect(lambda _i: self.live.set_device(textScale=self.cbo_scale.currentData()))
        self.cbo_mode.currentIndexChanged.connect(lambda _i: self.live.set_mode(self.cbo_mode.currentData()))
        self.btn_play.clicked.connect(self.live.play)
        self.btn_exact.toggled.connect(self._exact_toggled)
        self.live.statusChanged.connect(self.lbl_status.setText)
        self._device_changed(0)

    def _device_changed(self, _i: int) -> None:
        w, h, pf = self.cbo_device.currentData()
        if self.live.device["width"] > self.live.device["height"]:
            w, h = h, w
        self.live.set_device(w, h, platform=pf)

    def start(self, project_dir=None) -> None:
        self.project_dir = str(project_dir) if project_dir else None
        self.live.start(project_dir)

    def set_route(self, route: str) -> None:
        self.route = route or "/"

    def _exact_toggled(self, on: bool) -> None:
        if on:
            if not self.project_dir:
                self.btn_exact.setChecked(False)
                self.lbl_status.setText("Exact mode needs a Flutter project folder")
                return
            self.live.start_exact(self.project_dir, self.route)
        else:
            self.live.stop_exact()

    def screen_saved(self) -> None:
        """Call after the screen file was saved: hot reloads the exact preview."""
        if self.live.exact is not None:
            self.live.exact_reload()

    def shutdown(self) -> None:
        self.live.shutdown()

    def closeEvent(self, e):      # noqa: N802
        self.shutdown()
        super().closeEvent(e)


if __name__ == "__main__":       # python -m radide.flutterdesign.live --build
    import sys
    if "--build" in sys.argv:
        print(build_host_sync(lambda s: print(s, end="")))
    else:
        print("ready" if host_ready() else "not built", host_build_dir())
