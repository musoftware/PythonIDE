"""React Native (Expo) projects in the IDE (CONTRACTS 10.1, optional item): F5 runs the app.

    Web (Preview)       npm install (first time) -> npx expo start --web; the page opens in the Preview dock
    Android emulator    the AVD is started when needed (adb waits for the boot) -> npx expo start --android
                        (Expo Go is installed on the emulator by the Expo CLI)
Saving a file regenerates the screens (features/mobile.py writes App.js / radapp.js) and Metro fast-refreshes
the running app - nothing to restart. The session has the interface of radide.debugger.Session (win.session).
"""
from __future__ import annotations

import re
import socket
import subprocess
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QComboBox, QLabel, QMessageBox, QToolBar

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def is_expo(win) -> bool:
    try:
        rp = win.run_plugin()
    except Exception:  # noqa: BLE001
        rp = getattr(win, "plugin", None)
    return getattr(rp, "id", "") == "expo" and win.project is not None


def free_port(start: int = 8081) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def needs_install(folder: Path) -> bool:
    """True when node_modules is missing or older than package.json."""
    lock = Path(folder) / "node_modules" / ".package-lock.json"
    pkg = Path(folder) / "package.json"
    if not (Path(folder) / "node_modules" / "expo").is_dir() or not lock.exists():
        return True
    try:
        return pkg.stat().st_mtime > lock.stat().st_mtime + 1
    except OSError:
        return False


def _settings(project) -> dict:
    d = project.extra.get("expo")
    if not isinstance(d, dict):
        d = {}
        project.extra["expo"] = d
    return d


class ExpoSession(QObject):
    """npm install (when needed) -> [start the AVD] -> npx expo start --web|--android."""
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)
    status = pyqtSignal(str)
    url_ready = pyqtSignal(str)            # the web address of the running app

    def __init__(self, folder: Path, device: dict, parent=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.device = device
        self.paused = False
        self.debug = False
        self.user_stopped = False
        self.port = free_port()
        self.url = ""
        self.proc: QProcess | None = None
        self.emulator: subprocess.Popen | None = None       # an emulator this session started
        self._serial = ""
        self._timer: QTimer | None = None
        self._done = False

    # ------------------------------------------------------------ steps
    def start(self):
        if needs_install(self.folder):
            self._step(self._npm(), ["install", "--no-audit", "--no-fund"], self._after_install,
                       "Installing the npm packages (first run, a few minutes)...")
        else:
            self._after_install(0)

    @staticmethod
    def _npm() -> str:
        from ..languages.expo_app import node_tool
        return node_tool("npm") or "npm"

    def _env(self) -> QProcessEnvironment:
        env = QProcessEnvironment.systemEnvironment()
        env.insert("BROWSER", "none")              # the page opens in the IDE's Preview, not a new browser tab
        env.insert("EXPO_NO_TELEMETRY", "1")
        env.insert("FORCE_COLOR", "0")
        env.remove("CI")                           # CI mode turns fast refresh off
        from .mobile import sdk_root
        root = sdk_root()
        if root is not None:
            env.insert("ANDROID_HOME", str(root))
        return env

    def _step(self, program: str, args: list[str], then, message: str = ""):
        if self.user_stopped:
            self._finish(0)
            return
        if message:
            self.status.emit(message)
        self.output.emit(f"> {Path(program).stem} {' '.join(args)}\n")
        p = QProcess(self)
        self.proc = p
        p.setWorkingDirectory(str(self.folder))
        p.setProcessEnvironment(self._env())
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self._read)
        p.finished.connect(lambda c, _s: then(c))
        p.errorOccurred.connect(lambda e: (self.failed.emit(f"{program} could not be started - is Node.js "
                                                            f"installed?"), self._finish(1))
                                if e == QProcess.ProcessError.FailedToStart else None)
        p.start(program, args)

    def _after_install(self, code: int):
        if code != 0:
            self.failed.emit(f"npm install failed (exit code {code})")
            self._finish(code)
            return
        if self.device.get("platform") == "android":
            self._ensure_android()
        else:
            self._expo(["--web"])

    def _expo(self, extra: list[str]):
        from ..languages.expo_app import node_tool
        args = ["expo", "start", "--port", str(self.port), *extra]
        self._step(node_tool("npx") or "npx", args, self._finish, "Starting the Expo dev server (Metro)...")

    # ------------------------------------------------------------ android
    def _ensure_android(self):
        from .mobile import _adb_devices, adb_exe, emulator_exe
        adb = adb_exe()
        if not adb:
            self.failed.emit("The Android SDK (adb) was not found")
            self._finish(1)
            return
        if self.device.get("kind") != "avd":
            self._serial = self.device.get("id", "")
            self._expo(["--android"])
            return
        before = set(_adb_devices(adb))
        avd = self.device["avd"]
        self.output.emit(f"> emulator -avd {avd}\n")
        try:
            self.emulator = subprocess.Popen([emulator_exe(), "-avd", avd, "-no-snapshot-save"],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             creationflags=NOWIN)
        except OSError as e:
            self.failed.emit(f"The emulator could not be started: {e}")
            self._finish(1)
            return
        self.status.emit(f"Starting the emulator {avd}...")
        self._timer = QTimer(self)
        waited = [0]

        def poll():
            waited[0] += 3
            if self.user_stopped:
                self._timer.stop()
                self._finish(0)
                return
            new = [s for s in _adb_devices(adb) if s not in before] or \
                [s for s in _adb_devices(adb) if s.startswith("emulator-")]
            for serial in new:
                try:          # adb can hang while the emulator boots: never let an exception out of the slot
                    r = subprocess.run([adb, "-s", serial, "shell", "getprop", "sys.boot_completed"],
                                       capture_output=True, text=True, timeout=10, creationflags=NOWIN)
                except (OSError, subprocess.SubprocessError):
                    continue
                if r.stdout.strip() == "1":
                    self._timer.stop()
                    self._serial = serial
                    self.output.emit(f"  Android is ready ({serial}).\n")
                    self._expo(["--android"])
                    return
            if waited[0] > 300:
                self._timer.stop()
                self.failed.emit("The emulator did not finish booting in 5 minutes")
                self._finish(1)
        self._timer.timeout.connect(poll)
        self._timer.start(3000)

    # ------------------------------------------------------------ output
    def _read(self):
        if self.proc is None:
            return
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
        self.output.emit(text)
        if not self.url:
            m = re.search(r"(?:Web is waiting on|Waiting on)\s+(https?://\S+)", text)
            if m:
                self.url = m.group(1).rstrip(".,")
                if "localhost" not in self.url and "127.0.0.1" not in self.url:
                    self.url = f"http://localhost:{self.port}"
                self.url_ready.emit(self.url)
                self.status.emit(f"Running at {self.url} - save a file to fast-refresh")

    # ------------------------------------------------------------ lifecycle
    def running(self) -> bool:
        return not self._done

    def stop(self):
        self.user_stopped = True
        if self._timer is not None:
            self._timer.stop()
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            from .mobile import kill_tree
            kill_tree(int(self.proc.processId()))
        else:
            self._finish(0)

    def stop_emulator(self):
        """Shut down the emulator this session started (toolbar: Close the Emulator)."""
        from .mobile import adb_exe
        if self._serial and self.emulator is not None and adb_exe():
            try:
                subprocess.run([adb_exe(), "-s", self._serial, "emu", "kill"], capture_output=True, timeout=20,
                               creationflags=NOWIN)
            except (OSError, subprocess.SubprocessError):
                pass
        self.emulator = None

    def _finish(self, code: int):
        if self._done:
            return
        self._done = True
        if self._timer is not None:
            self._timer.stop()
        self.finished.emit(int(code))

    # Session methods the IDE may call - nothing to do without a debugger
    def cont(self):
        pass

    step_into = step_over = step_out = cont

    def evaluate(self, expr: str):
        self.evalResult.emit("(the Immediate window is not available for React Native - use console.log)")

    def set_breakpoint(self, *a, **k):
        pass

    def set_break_on_exception(self, *a, **k):
        pass

    def send(self, cmd: str):
        pass


class ExpoFeature(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.devices: list[dict] = []
        self.last_session: ExpoSession | None = None
        self._make_ui()
        self._wrap()
        self.update_ui()

    def _make_ui(self):
        win = self.win
        tb = QToolBar("Expo", win)
        tb.setObjectName("Expo")
        tb.addWidget(QLabel(" Run on: "))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(240)
        self.combo.setToolTip("Where F5 runs the React Native app: the Preview (web) or an Android emulator / "
                              "phone with Expo Go")
        self.combo.activated.connect(self._chosen)
        tb.addWidget(self.combo)
        self.a_refresh = QAction("Refresh devices", win)
        self.a_refresh.triggered.connect(self.refresh_devices)
        self.a_browser = QAction("Open in Browser", win)
        self.a_browser.setToolTip("Open the running app in the default web browser")
        self.a_browser.triggered.connect(self.open_browser)
        self.a_emu = QAction("Close the Emulator", win)
        self.a_emu.setToolTip("Shut down the Android emulator that F5 started")
        self.a_emu.triggered.connect(self.close_emulator)
        for a in (self.a_refresh, self.a_browser, self.a_emu):
            tb.addAction(a)
        win.addToolBar(tb)
        tb.setVisible(False)
        self.toolbar = tb
        self.refresh_devices()

    def refresh_devices(self):
        from .mobile import _adb_devices, adb_exe, list_avds
        devs = [{"id": "web", "name": "Web (Preview window)", "platform": "web", "kind": "web"}]
        adb = adb_exe()
        for serial in (_adb_devices(adb) if adb else []):
            devs.append({"id": serial, "name": f"Android: {serial} (Expo Go)", "platform": "android",
                         "kind": "device"})
        for avd in list_avds():
            devs.append({"id": f"avd:{avd}", "name": f"Android emulator: {avd.replace('_', ' ')} (start)",
                         "platform": "android", "kind": "avd", "avd": avd})
        self.devices = devs
        self.combo.blockSignals(True)
        self.combo.clear()
        for d in devs:
            self.combo.addItem(d["name"], d["id"])
        self.combo.blockSignals(False)
        self._select_saved()

    def _select_saved(self):
        proj = self.win.project
        if proj is None:
            return
        want = str(_settings(proj).get("device") or "web")
        for i, d in enumerate(self.devices):
            if d["id"] == want:
                self.combo.setCurrentIndex(i)
                return

    def _chosen(self, i):
        proj = self.win.project
        if proj is not None and 0 <= i < len(self.devices):
            _settings(proj)["device"] = self.devices[i]["id"]
            try:
                proj.save()
            except OSError:
                pass

    def current_device(self) -> dict:
        i = self.combo.currentIndex()
        return self.devices[i] if 0 <= i < len(self.devices) else self.devices[0]

    def update_ui(self):
        on = is_expo(self.win)
        if self.toolbar.isVisible() != on:
            self.toolbar.setVisible(on)
            if on:
                self._select_saved()
        s = self.win.session
        self.a_browser.setEnabled(isinstance(s, ExpoSession) and bool(s.url))
        last = self.last_session
        self.a_emu.setEnabled(last is not None and last.emulator is not None)

    def _wrap(self):
        win = self.win
        orig_run = win.run_project

        def run_project(debug: bool = True):
            if is_expo(win):
                return self.run(debug)
            return orig_run(debug)

        win.run_project = run_project
        win.extension_points.on("actions_updated", lambda: self.update_ui(), "expo")      # errors logged once

    # ------------------------------------------------------------ run
    def run(self, debug: bool = True):
        win = self.win
        if win.project is None or (win.session is not None and win.session.running()):
            return None
        from ..languages.expo_app import node_exe
        if not node_exe():
            QMessageBox.warning(win, "Run", "Node.js is not installed.\nInstall it from https://nodejs.org "
                                            "(it brings npm and npx) and run again.")
            return None
        win.save_all()
        plugin = win.run_plugin()
        try:
            plugin.regenerate_all(win.project)
        except Exception as e:  # noqa: BLE001
            win.log(f"*** Cannot generate the app: {e}")
            return None
        dev = self.current_device()
        win.output.clear()
        win.dock_output.show()
        win.dock_output.raise_()
        win.log(f"------ Run {win.project.name} on {dev['name']} (React Native / Expo) ------")
        s = ExpoSession(Path(win.project.folder), dev, win)
        s.output.connect(win._append_output)
        s.failed.connect(lambda err: win.log(f"*** Error: {err}"))
        s.status.connect(lambda m: win.statusBar().showMessage(m, 8000))
        s.finished.connect(win._on_finished)
        s.finished.connect(lambda _c: self.update_ui())
        if dev.get("platform") == "web":
            s.url_ready.connect(self.show_preview)
        s.url_ready.connect(lambda _u: self.update_ui())
        win.session = s
        self.last_session = s
        s.start()
        win._update_actions()
        return s

    def show_preview(self, url: str):
        pv = getattr(self.win, "web_preview", None)
        dock = getattr(self.win, "dock_web_preview", None)
        if pv is None or dock is None:
            self.open_browser()
            return
        try:                       # a phone-sized page
            for i in range(pv.device.count()):
                w, h = pv.device.itemData(i) or (0, 0)
                if 360 <= int(w or 0) <= 430 and int(h or 0) > int(w or 0):
                    pv.device.setCurrentIndex(i)
                    break
        except Exception:  # noqa: BLE001
            pass
        pv.open_url(url)
        dock.show()
        dock.raise_()

    def open_browser(self):
        s = self.win.session
        url = s.url if isinstance(s, ExpoSession) else ""
        if url:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(url))

    def close_emulator(self):
        s = self.last_session
        if s is not None:
            s.stop_emulator()
        self.update_ui()


def install(win) -> None:
    win.expo = ExpoFeature(win)


__all__ = ["ExpoFeature", "ExpoSession", "free_port", "is_expo", "needs_install", "install"]
