"""SuperPreview (Expression Web): the same page side by side at two sizes and/or in two browser
engines, phone/tablet/desktop presets, rotate, an onion-skin overlay and a difference view, and
"Open in Chrome / Edge / Firefox" for the browsers installed on this machine.

Engines per pane:
- "Live (Qt WebEngine)"   - an interactive embedded Chromium view, scaled to fit the pane
                            (the page still sees the preset's CSS width).
- "<Browser> screenshot"  - a headless screenshot made by an installed browser (Edge, Chrome,
                            Firefox, Brave), so different engines (Blink vs Gecko) can be compared.

Logic that does not need Qt (browser detection, presets, headless commands) is at the top.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# ====================================================================== presets + browsers


@dataclass(frozen=True)
class Preset:
    name: str
    width: int
    height: int
    mobile: bool = False


PRESETS = [
    Preset("Phone - iPhone SE", 375, 667, True),
    Preset("Phone - iPhone 15", 393, 852, True),
    Preset("Phone - Android (Pixel 8)", 412, 915, True),
    Preset("Tablet - iPad Mini", 768, 1024, True),
    Preset("Tablet - iPad Pro 12.9", 1024, 1366, True),
    Preset("Laptop 1366 x 768", 1366, 768),
    Preset("Desktop 1440 x 900", 1440, 900),
    Preset("Desktop 1920 x 1080", 1920, 1080),
]
CUSTOM = "Custom"
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/124.0.0.0 Mobile Safari/537.36")
TABLET_UA = ("Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/17.4 Mobile/15E148 Safari/604.1")

CHROMIUM = {"Chrome", "Edge", "Brave", "Opera", "Vivaldi", "Chromium"}
_EXE = {"Chrome": "chrome.exe", "Edge": "msedge.exe", "Firefox": "firefox.exe", "Brave": "brave.exe"}
_WIN_PATHS = {
    "Chrome": [r"Google\Chrome\Application\chrome.exe"],
    "Edge": [r"Microsoft\Edge\Application\msedge.exe"],
    # RADIDE\tools\firefox = the per-user copy the IDE installs (under %LOCALAPPDATA%)
    "Firefox": [r"Mozilla Firefox\firefox.exe", r"Firefox Developer Edition\firefox.exe",
                r"RADIDE\tools\firefox\firefox.exe"],
    "Brave": [r"BraveSoftware\Brave-Browser\Application\brave.exe"],
}
_UNIX = {"Chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
         "Edge": ["microsoft-edge", "microsoft-edge-stable"], "Firefox": ["firefox"], "Brave": ["brave-browser"]}
_MAC = {"Chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "Edge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "Firefox": "/Applications/Firefox.app/Contents/MacOS/firefox",
        "Brave": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"}
_cache: dict[str, str] | None = None


def _app_path(exe: str) -> str | None:
    try:
        import winreg
    except ImportError:
        return None
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (0, getattr(winreg, "KEY_WOW64_32KEY", 0)):
            try:
                with winreg.OpenKey(hive, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}", 0,
                                    winreg.KEY_READ | view) as k:
                    v, _ = winreg.QueryValueEx(k, "")
                    v = str(v).strip('"')
                    if v and Path(v).is_file():
                        return v
            except OSError:
                continue
    return None


def detect_browsers(refresh: bool = False) -> dict[str, str]:
    """{"Chrome": path, "Edge": path, "Firefox": path, "Brave": path} for the installed browsers."""
    global _cache
    if _cache is not None and not refresh:
        return dict(_cache)
    found: dict[str, str] = {}
    for name in ("Chrome", "Edge", "Firefox", "Brave"):
        path = None
        if sys.platform == "win32":
            path = _app_path(_EXE[name])
            if not path:
                for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                             os.environ.get("LOCALAPPDATA")):
                    for rel in _WIN_PATHS[name]:
                        if base and (Path(base) / rel).is_file():
                            path = str(Path(base) / rel)
                            break
                    if path:
                        break
        elif sys.platform == "darwin":
            path = _MAC[name] if Path(_MAC[name]).is_file() else None
        if not path:
            for cmd in _UNIX.get(name, []) if sys.platform != "win32" else []:
                path = shutil.which(cmd)
                if path:
                    break
        if path:
            found[name] = path
    _cache = found
    return dict(found)


def open_in_browser(browser: str, url: str, browsers: dict[str, str] | None = None) -> subprocess.Popen:
    """Start an installed browser on url (the browser keeps running; it is the user's)."""
    browsers = browsers if browsers is not None else detect_browsers()
    exe = browsers.get(browser) or browser
    if not Path(exe).is_file():
        raise FileNotFoundError(f"{browser} is not installed")
    return subprocess.Popen([exe, url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, close_fds=True)


def screenshot_command(browser: str, exe: str, url: str, width: int, height: int, out_png: Path,
                       profile_dir: Path) -> list[str]:
    """Headless screenshot command. A private profile folder keeps it away from the user's
    running browser windows. For Chromium browsers `url` should be the frame wrapper (see
    headless_screenshot): their headless window cannot be narrower than ~500 px."""
    if browser == "Firefox":
        return [exe, "--headless", "-no-remote", "-profile", str(profile_dir), "--window-size",
                f"{width},{height}", "--screenshot", str(out_png), url]
    win_w, win_h = max(width, 520) + 40, height + 200
    return [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            "--no-default-browser-check", "--disable-extensions", "--disable-sync", "--disable-default-apps",
            "--disable-background-networking", "--disable-component-update", f"--user-data-dir={profile_dir}",
            f"--window-size={win_w},{win_h}", f"--screenshot={out_png}", "--virtual-time-budget=4000", url]


FRAME_WRAPPER = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:#fff;overflow:hidden}}
iframe{{position:absolute;left:0;top:0;width:{w}px;height:{h}px;border:0;display:block}}
</style></head><body><iframe src="{url}"></iframe></body></html>"""


def headless_screenshot(browser: str, exe: str, url: str, width: int, height: int, out_png: Path,
                        timeout: float = 60) -> tuple[bool, str]:
    """Runs the browser headless and waits for the PNG (exactly width x height CSS pixels).
    Chromium: the page is shown in an iframe of the exact size inside a larger headless window and
    the PNG is cropped to it, so media queries see the preset's width. Returns (ok, message)."""
    import html as _html
    out_png = Path(out_png)
    if out_png.exists():
        out_png.unlink()
    profile = Path(tempfile.mkdtemp(prefix="radide-sp-"))
    target = url
    framed = browser != "Firefox"
    if framed:
        wrapper = profile / "radide-frame.html"
        wrapper.write_text(FRAME_WRAPPER.format(w=width, h=height, url=_html.escape(url, quote=True)),
                           encoding="utf-8")
        target = wrapper.as_uri()
    argv = screenshot_command(browser, exe, target, width, height, out_png, profile / "profile")
    t0 = time.time()
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return False, f"{browser} did not finish within {timeout:.0f} s"
        # Firefox may write the file a moment after exiting
        for _ in range(20):
            if out_png.is_file() and out_png.stat().st_size > 0:
                break
            time.sleep(0.1)
        if not (out_png.is_file() and out_png.stat().st_size > 0):
            text = (out or b"").decode("utf-8", "replace").strip().splitlines()[-3:]
            return False, f"{browser} made no screenshot (exit {proc.returncode}) " + " ".join(text)
        if framed:
            from PyQt6.QtGui import QImage
            img = QImage(str(out_png))
            if img.isNull():
                return False, f"{browser} wrote an unreadable screenshot"
            img.copy(0, 0, min(width, img.width()), min(height, img.height())).save(str(out_png))
        return True, f"{browser} {width}x{height} in {time.time() - t0:.1f} s"
    except OSError as e:
        return False, f"Cannot start {browser}: {e}"
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def fit_scale(css_w: int, css_h: int, avail_w: int, avail_h: int, minimum: float = 0.25) -> float:
    """Scale that fits a css_w x css_h viewport into the available pixels (never above 1)."""
    if css_w <= 0 or css_h <= 0 or avail_w <= 0 or avail_h <= 0:
        return 1.0
    return max(minimum, min(1.0, avail_w / css_w, avail_h / css_h))


# ====================================================================== Qt UI
from PyQt6.QtCore import QObject, QSize, Qt, QTimer, QUrl, pyqtSignal  # noqa: E402
from PyQt6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPixmap  # noqa: E402
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,  # noqa: E402
                             QMenu, QMessageBox, QPushButton, QSizePolicy, QSlider, QSpinBox, QSplitter,
                             QStackedWidget, QToolButton, QVBoxLayout, QWidget)

try:  # noqa: E402
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAVE_WEBENGINE = True
except Exception:  # noqa: BLE001
    HAVE_WEBENGINE = False

LIVE = "Live (Qt WebEngine)"


class _ShotSignals(QObject):
    done = pyqtSignal(int, bool, str, str)       # request id, ok, message, png path


class PreviewPane(QWidget):
    """One side of SuperPreview: preset/size/rotate/engine controls above a scaled view."""
    changed = pyqtSignal()
    status = pyqtSignal(str)

    def __init__(self, title: str, preset_index: int = 0, browsers: dict[str, str] | None = None, parent=None):
        super().__init__(parent)
        self.browsers = browsers if browsers is not None else detect_browsers()
        self.url = ""
        self.image: QImage | None = None           # screenshot engines
        self._req = 0
        self._rotated = False
        self._shots = _ShotSignals()
        self._shots.done.connect(self._on_shot)
        self._tmp = Path(tempfile.gettempdir()) / f"radide-superpreview-{os.getpid()}-{id(self)}.png"

        self.title = QLabel(f"<b>{title}</b>")
        self.preset = QComboBox()
        self.preset.addItems([p.name for p in PRESETS] + [CUSTOM])
        self.w = QSpinBox(minimum=200, maximum=3840, singleStep=10)
        self.h = QSpinBox(minimum=200, maximum=4000, singleStep=10)
        self.w.setSuffix(" w")
        self.h.setSuffix(" h")
        self.rotate_btn = QToolButton(text="Rotate", toolTip="Swap width and height (portrait / landscape)")
        self.engine = QComboBox(toolTip="Rendering engine of this pane")
        self.engine.addItem(LIVE)
        for name in self.browsers:
            self.engine.addItem(f"{name} screenshot")
        self.info = QLabel()
        self.info.setProperty("radRole", "muted")
        top = QHBoxLayout()
        top.setContentsMargins(4, 2, 4, 2)
        for wdg in (self.title, self.preset, self.w, self.h, self.rotate_btn, self.engine):
            top.addWidget(wdg)
        top.addStretch(1)
        top.addWidget(self.info)

        self.stage = QWidget()                     # gray backdrop with the device frame centred
        self.stage.setProperty("radRole", "stage")
        self.stage.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view = None
        self.profile = None
        if HAVE_WEBENGINE:
            self.view = QWebEngineView(self.stage)
            # off the record, own cookies and user agent per pane; created after the view so that
            # Qt deletes the view (and its page) before the profile
            self.profile = QWebEngineProfile(self)
            self._default_ua = self.profile.httpUserAgent()
            self.view.setPage(QWebEnginePage(self.profile, self.view))
            self.view.loadFinished.connect(lambda ok: self.status.emit(
                f"{title}: {'loaded' if ok else 'failed to load'} {self.view.url().toString()}"))
        self.shot = QLabel(self.stage)
        self.shot.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.shot.setStyleSheet("background: white;")
        self.shot.hide()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addLayout(top)
        lay.addWidget(self.stage, 1)

        self.preset.currentIndexChanged.connect(self._on_preset)
        self.w.valueChanged.connect(self._on_size)
        self.h.valueChanged.connect(self._on_size)
        self.rotate_btn.clicked.connect(self.rotate)
        self.engine.currentIndexChanged.connect(self._on_engine)
        self._block = False
        self.preset.setCurrentIndex(preset_index)
        self._on_preset(preset_index)

    # ---------------------------------------------------------------- size
    def css_size(self) -> tuple[int, int]:
        return self.w.value(), self.h.value()

    def current_preset(self) -> Preset | None:
        i = self.preset.currentIndex()
        return PRESETS[i] if 0 <= i < len(PRESETS) else None

    def set_size(self, w: int, h: int) -> None:
        self._block = True
        self.w.setValue(w)
        self.h.setValue(h)
        self._block = False
        self._on_size()

    def _on_preset(self, i: int) -> None:
        p = self.current_preset()
        if p is None:
            return
        w, h = (p.height, p.width) if self._rotated else (p.width, p.height)
        self._block = True
        self.w.setValue(w)
        self.h.setValue(h)
        self._block = False
        if self.profile is not None:
            ua = (TABLET_UA if p.width >= 700 else MOBILE_UA) if p.mobile else self._default_ua
            if self.profile.httpUserAgent() != ua:
                self.profile.setHttpUserAgent(ua)
                if self.url:
                    self.view.reload()
        self._on_size()

    def _on_size(self) -> None:
        if self._block:
            return
        p = self.current_preset()
        if p is not None and {self.w.value(), self.h.value()} != {p.width, p.height}:
            self.preset.blockSignals(True)
            self.preset.setCurrentText(CUSTOM)
            self.preset.blockSignals(False)
        self.layout_view()
        if self.is_screenshot() and self.url:
            self.capture()
        self.changed.emit()

    def rotate(self) -> None:
        self._rotated = not self._rotated
        w, h = self.css_size()
        self.set_size(h, w)

    def scale(self) -> float:
        w, h = self.css_size()
        return fit_scale(w, h, self.stage.width() - 16, self.stage.height() - 16)

    def layout_view(self) -> None:
        w, h = self.css_size()
        s = self.scale()
        dw, dh = max(1, int(w * s)), max(1, int(h * s))
        x = max(0, (self.stage.width() - dw) // 2)
        y = 8 if self.stage.height() > dh + 16 else 0
        if self.view is not None:
            self.view.setGeometry(x, y, dw, dh)
            if abs(self.view.zoomFactor() - s) > 1e-3:
                self.view.setZoomFactor(s)
        self.shot.setGeometry(x, y, dw, dh)
        if self.image is not None:
            self.shot.setPixmap(QPixmap.fromImage(self.image).scaled(
                dw, dh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.info.setText(f"{w} x {h}  @ {int(s * 100)}%")

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        QTimer.singleShot(0, self.layout_view)

    def showEvent(self, e):  # noqa: N802
        super().showEvent(e)
        QTimer.singleShot(0, self.layout_view)

    # ---------------------------------------------------------------- engine
    def engine_name(self) -> str:
        t = self.engine.currentText()
        return t[:-len(" screenshot")] if t.endswith(" screenshot") else ""

    def is_screenshot(self) -> bool:
        return bool(self.engine_name())

    def set_engine(self, name: str) -> bool:
        """name = "" / LIVE for the live view, else a browser name ("Edge")."""
        text = LIVE if not name or name == LIVE else f"{name} screenshot"
        i = self.engine.findText(text)
        if i < 0:
            return False
        self.engine.setCurrentIndex(i)
        return True

    def _on_engine(self, _i=None) -> None:
        shot = self.is_screenshot()
        if self.view is not None:
            self.view.setVisible(not shot)
        self.shot.setVisible(shot)
        if shot and self.url:
            self.capture()
        elif not shot and self.url and self.view is not None:
            self.view.setUrl(QUrl(self.url))
        self.changed.emit()

    # ---------------------------------------------------------------- loading
    def load(self, url: str) -> None:
        self.url = url
        if self.is_screenshot():
            self.capture()
        elif self.view is not None:
            self.view.setUrl(QUrl(url))

    def reload(self) -> None:
        if self.is_screenshot():
            self.capture()
        elif self.view is not None:
            self.view.reload()

    def capture(self) -> None:
        """Take a headless screenshot with the pane's browser (in a thread)."""
        name = self.engine_name()
        exe = self.browsers.get(name)
        if not exe or not self.url:
            return
        self._req += 1
        req = self._req
        w, h = self.css_size()
        out = self._tmp.with_name(f"{self._tmp.stem}-{req}.png")
        self.shot.setText(f"  {name} is rendering {w} x {h} ...")
        self.status.emit(f"{name}: rendering {self.url} at {w} x {h} ...")

        def work():
            ok, msg = headless_screenshot(name, exe, self.url, w, h, out)
            try:
                self._shots.done.emit(req, ok, msg, str(out))
            except RuntimeError:
                pass                              # pane closed meanwhile
        threading.Thread(target=work, daemon=True).start()

    def _on_shot(self, req: int, ok: bool, msg: str, path: str) -> None:
        if req != self._req:
            Path(path).unlink(missing_ok=True)
            return
        if ok:
            img = QImage(path)
            Path(path).unlink(missing_ok=True)
            self.image = img if not img.isNull() else None
            self.layout_view()
        else:
            self.image = None
            self.shot.setPixmap(QPixmap())
            self.shot.setText("  " + msg)
        self.status.emit(msg)
        self.changed.emit()

    def snapshot(self) -> QImage | None:
        """What the pane shows, at its CSS size (for the overlay)."""
        w, h = self.css_size()
        if self.is_screenshot():
            img = self.image
        elif self.view is not None and self.view.isVisible():
            img = self.view.grab().toImage()
        else:
            img = None
        if img is None or img.isNull():
            return None
        return img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def closeEvent(self, e):  # noqa: N802
        self._req += 1
        super().closeEvent(e)


class OnionSkin(QWidget):
    """Draws image A and image B on top of it with an adjustable opacity, or their difference."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.a: QImage | None = None
        self.b: QImage | None = None
        self.opacity = 0.5
        self.mode = "overlay"          # overlay | difference
        self.setMinimumSize(200, 200)

    def set_images(self, a: QImage | None, b: QImage | None) -> None:
        self.a, self.b = a, b
        self.update()

    def composed(self, size: QSize | None = None) -> QImage | None:
        if self.a is None and self.b is None:
            return None
        base = self.a or self.b
        w, h = base.width(), base.height()
        out = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        out.fill(QColor("white"))
        p = QPainter(out)
        if self.a is not None:
            p.drawImage(0, 0, self.a.scaled(w, h))
        if self.b is not None:
            b = self.b.scaled(w, h)
            if self.mode == "difference" and self.a is not None:
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Difference)
            else:
                p.setOpacity(self.opacity)
            p.drawImage(0, 0, b)
        p.end()
        if size is not None:
            out = out.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return out

    def difference_ratio(self) -> float:
        """Share of pixels that differ noticeably between A and B (0..1)."""
        if self.a is None or self.b is None:
            return 0.0
        w, h = min(self.a.width(), 400), min(self.a.height(), 400)
        a = self.a.scaled(w, h).convertToFormat(QImage.Format.Format_RGB32)
        b = self.b.scaled(w, h).convertToFormat(QImage.Format.Format_RGB32)
        diff = 0
        step = 2
        n = 0
        for y in range(0, h, step):
            for x in range(0, w, step):
                ca, cb = a.pixelColor(x, y), b.pixelColor(x, y)
                n += 1
                if abs(ca.red() - cb.red()) + abs(ca.green() - cb.green()) + abs(ca.blue() - cb.blue()) > 60:
                    diff += 1
        return diff / n if n else 0.0

    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#3a3d44"))
        img = self.composed(self.size())
        if img is None:
            p.setPen(QColor("white"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Load a page in both panes, then press Capture.")
        else:
            p.drawImage((self.width() - img.width()) // 2, (self.height() - img.height()) // 2, img)
        p.end()


class SuperPreview(QMainWindow):
    """The SuperPreview window. `SuperPreview(url).show()`."""

    def __init__(self, url: str = "", parent=None, browsers: dict[str, str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("SuperPreview")
        self.resize(1400, 860)
        self.browsers = browsers if browsers is not None else detect_browsers()
        central = QWidget()
        self.setCentralWidget(central)

        self.address = QLineEdit(url, placeholderText="http://127.0.0.1:8000/")
        go = QPushButton("Go")
        reload_ = QPushButton("Reload")
        self.mode = QComboBox()
        self.mode.addItems(["Side by side (horizontal)", "Side by side (vertical)", "Overlay (onion skin)",
                            "Difference"])
        self.opacity = QSlider(Qt.Orientation.Horizontal, minimum=0, maximum=100, value=50)
        self.opacity.setFixedWidth(140)
        self.opacity.setToolTip("Onion skin: opacity of the right-hand pane over the left-hand one")
        self.capture_btn = QPushButton("Capture")
        self.capture_btn.setToolTip("Take new snapshots of both panes for the overlay")
        self.sync = QCheckBox("Sync scroll", checked=True)
        self.open_btn = QToolButton(text="Open in browser")
        self.open_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.open_btn)
        for name in self.browsers:
            menu.addAction(name, lambda n=name: self.open_external(n))
        menu.addSeparator()
        menu.addAction("Default browser", lambda: QDesktopServices.openUrl(QUrl(self.address.text().strip())))
        self.open_btn.setMenu(menu)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Address:"))
        bar.addWidget(self.address, 1)
        for wdg in (go, reload_, QLabel("  View:"), self.mode, self.opacity, self.capture_btn, self.sync,
                    self.open_btn):
            bar.addWidget(wdg)

        self.left = PreviewPane("A", 0, self.browsers)          # phone
        self.right = PreviewPane("B", 7, self.browsers)         # desktop 1920
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.left)
        self.split.addWidget(self.right)
        self.split.setSizes([500, 900])
        self.onion = OnionSkin()
        self.stack = QStackedWidget()
        self.stack.addWidget(self.split)
        self.stack.addWidget(self.onion)
        self.diff_label = QLabel()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addLayout(bar)
        lay.addWidget(self.stack, 1)
        lay.addWidget(self.diff_label)

        go.clicked.connect(self.go)
        self.address.returnPressed.connect(self.go)
        reload_.clicked.connect(self.reload)
        self.mode.currentIndexChanged.connect(self._on_mode)
        self.opacity.valueChanged.connect(self._on_opacity)
        self.capture_btn.clicked.connect(self.capture)
        for pane in (self.left, self.right):
            pane.status.connect(self.statusBar().showMessage)
            pane.changed.connect(self._pane_changed)
        if HAVE_WEBENGINE and self.left.view is not None:
            self.left.view.page().scrollPositionChanged.connect(lambda pos: self._sync_scroll(self.left, self.right))
            self.right.view.page().scrollPositionChanged.connect(lambda pos: self._sync_scroll(self.right, self.left))
        self._syncing = False
        self._on_mode(0)
        if url:
            QTimer.singleShot(0, self.go)

    # ---------------------------------------------------------------- actions
    def go(self, url: str | None = None) -> None:
        url = (url or self.address.text()).strip()
        if not url:
            return
        if "://" not in url:
            url = "http://" + url
        self.address.setText(url)
        self.left.layout_view()            # zoom first, so the page loads at the preset's CSS width
        self.right.layout_view()
        self.left.load(url)
        self.right.load(url)

    def reload(self) -> None:
        self.left.reload()
        self.right.reload()

    def open_external(self, browser: str) -> None:
        url = self.address.text().strip()
        try:
            open_in_browser(browser, url, self.browsers)
            self.statusBar().showMessage(f"Opened {url} in {browser}")
        except (OSError, FileNotFoundError) as e:
            QMessageBox.warning(self, "SuperPreview", str(e))

    def _on_mode(self, i: int) -> None:
        overlay = i >= 2
        self.opacity.setVisible(i == 2)
        self.capture_btn.setVisible(overlay)
        if i in (0, 1):
            self.split.setOrientation(Qt.Orientation.Horizontal if i == 0 else Qt.Orientation.Vertical)
            self.stack.setCurrentWidget(self.split)
            self.diff_label.clear()
        else:
            self.onion.mode = "difference" if i == 3 else "overlay"
            self.capture()

    def _on_opacity(self, v: int) -> None:
        self.onion.opacity = v / 100
        self.onion.update()

    def capture(self) -> None:
        """Snapshot both panes (they must be visible to be grabbed) and show the overlay."""
        self.stack.setCurrentWidget(self.split)
        QTimer.singleShot(150, self._grab)

    def _grab(self) -> None:
        a, b = self.left.snapshot(), self.right.snapshot()
        self.onion.set_images(a, b)
        if self.mode.currentIndex() >= 2:
            self.stack.setCurrentWidget(self.onion)
            if a is not None and b is not None:
                r = self.onion.difference_ratio()
                self.diff_label.setText(f"About {r * 100:.1f}% of the page differs between A and B. "
                                        "Use the same size in both panes to compare engines.")
            else:
                self.diff_label.setText("A pane has nothing to show yet.")

    def _pane_changed(self) -> None:
        if self.mode.currentIndex() >= 2 and self.stack.currentWidget() is self.onion:
            self.capture()

    def _sync_scroll(self, src: PreviewPane, dst: PreviewPane) -> None:
        if not self.sync.isChecked() or self._syncing or dst.view is None or src.view is None:
            return
        self._syncing = True
        js = ("(function(){var h=document.documentElement.scrollHeight-innerHeight;"
              "return h>0?scrollY/h:0;})()")

        def apply(ratio):
            if isinstance(ratio, (int, float)):
                dst.view.page().runJavaScript(
                    f"window.scrollTo(0,(document.documentElement.scrollHeight-innerHeight)*{float(ratio)});")
            QTimer.singleShot(50, lambda: setattr(self, "_syncing", False))
        src.view.page().runJavaScript(js, apply)

    def closeEvent(self, e):  # noqa: N802
        for pane in (self.left, self.right):
            pane._req += 1
            if pane.view is not None:
                pane.view.setUrl(QUrl("about:blank"))
        super().closeEvent(e)
