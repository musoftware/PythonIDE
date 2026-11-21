"""Mobile apps in the IDE (CONTRACTS 10.1): device selector, F5 = flutter run with hot reload on save,
hot restart, Android emulators started on demand, Build > APK / App Bundle / Windows / Web, and the Dart
debugger (flutter debug_adapter through radide/dap.py) for breakpoints.

Everything works on the *active* project when its start-up plugin is mobile (``is_mobile = True``):
    flutter  - this module runs it (flutter run / builds)
    kivy     - the normal Python run (python <Startup>.py); this module keeps radkivy.py up to date
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QComboBox, QLabel, QMenu, QMessageBox, QToolBar

PLATFORM_FOLDERS = {"windows": "windows", "web": "web", "android": "android", "ios": "ios", "macos": "macos",
                    "linux": "linux"}


# ===================================================================== helpers
def sdk_root() -> Path | None:
    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        v = os.environ.get(env)
        if v and Path(v).is_dir():
            return Path(v)
    p = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk"
    return p if p.is_dir() else None


def emulator_exe() -> str:
    root = sdk_root()
    if root:
        p = root / "emulator" / ("emulator.exe" if os.name == "nt" else "emulator")
        if p.exists():
            return str(p)
    return ""


def adb_exe() -> str:
    root = sdk_root()
    if root:
        p = root / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
        if p.exists():
            return str(p)
    return ""


def list_avds() -> list[str]:
    exe = emulator_exe()
    if not exe:
        return []
    try:
        r = subprocess.run([exe, "-list-avds"], capture_output=True, text=True, timeout=20,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip() and not ln.startswith(("INFO", "WARNING"))]


# ===================================================================== foldable emulator (docs/CONTRACTS.md 10.8)
FOLD_AVD = "RADIDE_Fold"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def avdmanager_exe() -> str:
    """cmdline-tools avdmanager (latest first), or ""."""
    root = sdk_root()
    if not root:
        return ""
    name = "avdmanager.bat" if os.name == "nt" else "avdmanager"
    cands = [root / "cmdline-tools" / "latest" / "bin" / name]
    try:
        cands += sorted((root / "cmdline-tools").glob(f"*/bin/{name}"), reverse=True)
    except OSError:
        pass
    cands.append(root / "tools" / "bin" / name)
    return next((str(c) for c in cands if c.is_file()), "")


def avd_device_profiles() -> list[str]:
    """Hardware profile ids that `avdmanager list device -c` knows."""
    exe = avdmanager_exe()
    if not exe:
        return []
    try:
        r = subprocess.run([exe, "list", "device", "-c"], capture_output=True, text=True, timeout=120,
                           creationflags=_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip() and not ln.startswith(("Loading", "Warning"))]


def host_abis() -> tuple[str, ...]:
    import platform
    m = platform.machine().lower()
    return ("arm64-v8a",) if m in ("arm64", "aarch64") else ("x86_64", "x86")


def best_system_image() -> str:
    """The newest installed system image for this CPU, as an sdkmanager package path
    ("system-images;android-36;google_apis_playstore;x86_64"), or ""."""
    root = sdk_root()
    if not root:
        return ""
    best, best_key = "", None
    tags = ("google_apis_playstore", "google_apis", "default")
    abis = host_abis()
    try:
        for img in (root / "system-images").glob("android-*/*/*"):
            if not (img / "system.img").is_file() and not (img / "source.properties").is_file():
                continue
            api, tag, abi = img.parent.parent.name, img.parent.name, img.name
            if abi not in abis or tag not in tags:
                continue
            num = re.sub(r"\D", "", api.split("-", 1)[-1]) or "0"
            key = (int(num), -tags.index(tag), -abis.index(abi))
            if best_key is None or key > best_key:
                best, best_key = f"system-images;{api};{tag};{abi}", key
    except OSError:
        return ""
    return best


def foldable_avd(name: str = FOLD_AVD, log=None) -> tuple[bool, str]:
    """Create the foldable Android emulator *name* (never touches other AVDs; an existing one of that name
    is kept).  Returns (ok, message)."""
    say = log or (lambda _t: None)
    if name in list_avds():
        return True, f"The emulator {name} already exists."
    exe = avdmanager_exe()
    if not exe:
        return False, "Android SDK command-line tools (avdmanager) not found - install them with the SDK Manager."
    image = best_system_image()
    if not image:
        return False, "No Android system image for this computer is installed (SDK Manager > SDK Platforms)."
    profiles = avd_device_profiles()
    from ..devices import FOLDABLE_AVD_PROFILES
    profile = next((d for d in FOLDABLE_AVD_PROFILES if d in profiles), "")
    if not profile:
        return False, "This Android SDK has no foldable hardware profile (update the command-line tools)."
    say(f"> avdmanager create avd -n {name} -k {image} -d {profile}\n")
    try:
        r = subprocess.run([exe, "create", "avd", "-n", name, "-k", image, "-d", profile],
                           input="no\n", capture_output=True, text=True, timeout=300, creationflags=_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"avdmanager failed: {e}"
    say((r.stdout or "") + (r.stderr or ""))
    if name not in list_avds():
        return False, f"avdmanager could not create {name}: {(r.stderr or r.stdout or '').strip()[-400:]}"
    return True, f"Created the foldable emulator {name} ({profile}, {image.split(';')[1]})."


_STATE_NAMES = {"folded": ("CLOSED", "FOLDED", "CLOSE"),
                "half-opened": ("HALF_OPENED", "HALF_FOLDED", "HALF_OPEN", "TABLETOP", "HALF"),
                "flat": ("OPENED", "OPEN", "UNFOLDED", "FLAT")}


def _adb(serial: str, *args, timeout=30) -> str:
    adb = adb_exe()
    if not adb:
        return ""
    try:
        r = subprocess.run([adb, "-s", serial, *args], capture_output=True, text=True, timeout=timeout,
                           creationflags=_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (r.stdout or "") + (r.stderr or "")


def device_states(serial: str) -> dict[str, int]:
    """{state name: identifier} from `cmd device_state print-states` (names vary by system image)."""
    out = _adb(serial, "shell", "cmd", "device_state", "print-states")
    states = {}
    for m in re.finditer(r"identifier=(\d+),\s*name='([^']*)'", out):
        states[m.group(2).upper()] = int(m.group(1))
    return states


def current_device_state(serial: str) -> str:
    """Name of the current device state (e.g. OPENED / HALF_OPENED / CLOSED), or ""."""
    out = _adb(serial, "shell", "cmd", "device_state", "print-state")
    m = re.search(r"name='([^']*)'", out)
    if m:
        return m.group(1).upper()
    states = {v: k for k, v in device_states(serial).items()}
    m = re.search(r"(\d+)", out)
    return states.get(int(m.group(1)), "") if m else ""


def set_posture(serial: str, posture: str) -> tuple[bool, str]:
    """Put the foldable emulator *serial* in *posture* (Flat / HalfOpened / Folded, any spelling) with
    `cmd device_state state <id>` (fallback: the emulator console `fold` / `unfold`).  Verifies the result
    and returns (ok, current state name)."""
    from ..devices import posture_key
    key = posture_key(posture)
    states = device_states(serial)
    ident = None
    for nm in _STATE_NAMES[key]:
        ident = next((i for s_, i in states.items() if s_ == nm), None)
        if ident is not None:
            break
    if ident is None:                                   # a looser match (e.g. "HALF_OPENED_TENT")
        ident = next((i for s_, i in states.items() if any(nm in s_ for nm in _STATE_NAMES[key])
                      and not (key == "flat" and "HALF" in s_)), None)
    if ident is not None:
        _adb(serial, "shell", "cmd", "device_state", "state", str(ident))
    else:
        _adb(serial, "emu", "fold" if key == "folded" else "unfold")
    now = current_device_state(serial)
    ok = any(nm == now or (nm in now and not (key == "flat" and "HALF" in now)) for nm in _STATE_NAMES[key])
    return ok, now


def platform_of(target: str) -> str:
    """flutter devices targetPlatform -> project platform folder ('android-x64' -> 'android')."""
    t = (target or "").lower()
    if t.startswith("web"):
        return "web"
    for p in ("android", "windows", "ios", "darwin", "linux"):
        if t.startswith(p):
            return "macos" if p == "darwin" else p
    return "windows"


def is_flutter(win) -> bool:
    try:
        rp = win.run_plugin()
    except Exception:  # noqa: BLE001
        rp = getattr(win, "plugin", None)
    return getattr(rp, "id", "") == "flutter" and win.project is not None


def is_mobile(win) -> bool:
    try:
        rp = win.run_plugin()
    except Exception:  # noqa: BLE001
        rp = getattr(win, "plugin", None)
    return bool(getattr(rp, "is_mobile", False)) and win.project is not None


def kill_tree(pid: int) -> None:
    if not pid:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


BROWSER_DEVICES = {"chrome": "chrome", "edge": "msedge"}     # flutter web devices that launch a browser


def browser_marker(device_id: str) -> str:
    """A harmless extra browser switch (``--web-browser-flag``) that tags the browser this run launches,
    so it can be closed when flutter ends without closing it (compile error, crash). "" = no browser."""
    if device_id not in BROWSER_DEVICES:
        return ""
    import uuid
    return f"--radide-run={uuid.uuid4().hex[:12]}"


def kill_marked_browser(marker: str) -> None:
    """End the browser process tree(s) whose command line carries *marker* (only the one this run started)."""
    if not marker or os.name != "nt" or not re.fullmatch(r"--radide-run=[0-9a-f]+", marker):
        return
    script = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' or Name='msedge.exe'\" | "
              f"Where-Object {{ $_.CommandLine -like '*{marker}*' }} | "
              "ForEach-Object { taskkill /PID $_.ProcessId /T /F | Out-Null }")
    try:          # in the background: the IDE does not wait for PowerShell
        subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        pass


def startup_size(project) -> tuple[int, int] | None:
    """Window size for the desktop run: the start-up form's safe area plus the title bar."""
    try:
        from ..model import Form
        f = Form.load(project.form_path(project.startup))
        return int(f.props.get("Width", 412)), int(f.props.get("Height", 867)) + 40
    except Exception:  # noqa: BLE001
        return None


def designer_state(win) -> dict:
    """The field lines (initial control values) of every generated Flutter designer file. Hot reload keeps
    the State of a screen, so when these change the IDE does a hot restart instead."""
    out = {}
    proj = win.project
    if proj is None:
        return out
    for f in (Path(proj.folder) / "lib").glob("*_designer.dart"):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # the control fields: from "abstract class <Form>Designer" to the "_code" getter
        start = text.find("abstract class ")
        end = text.find(" get _code => ", start)
        out[f.name] = text[start:end] if start >= 0 and end > start else text
    return out


def phone_window(folder: Path, size: tuple[int, int]) -> None:
    """Give the Windows runner of a Flutter project the phone's size instead of 1280 x 720."""
    main = Path(folder) / "windows" / "runner" / "main.cpp"
    try:
        text = main.read_text(encoding="utf-8")
    except OSError:
        return
    new = text.replace("Win32Window::Size size(1280, 720);", f"Win32Window::Size size({size[0]}, {size[1]});")
    if new != text:
        main.write_text(new, encoding="utf-8")


def _project_mobile(project) -> dict:
    d = project.extra.get("mobile")
    if not isinstance(d, dict):
        d = {}
        project.extra["mobile"] = d
    return d


# ===================================================================== steps (create / pub get)
def prepare_steps(folder: Path, platform: str, package: str) -> list[list[str]]:
    """argv lists (after 'flutter') to run before flutter run / build for *platform*."""
    from ..languages.flutter import flutter_exe
    fl = flutter_exe()
    steps = []
    pf = PLATFORM_FOLDERS.get(platform, platform)
    if pf and not (folder / pf).is_dir():
        steps.append([fl, "create", f"--platforms={pf}", "--project-name", package, "--org", "org.radide",
                      "--no-pub", "."])
    spec, cfg = folder / "pubspec.yaml", folder / ".dart_tool" / "package_config.json"
    if steps or not cfg.exists() or (spec.exists() and cfg.stat().st_mtime < spec.stat().st_mtime):
        steps.append([fl, "pub", "get", "--offline"])
    return steps


class StepProcess(QObject):
    """Run argv lists one after another (QProcess, merged output); finished(code) at the end or the first
    failure. A failing 'pub get --offline' is retried online."""
    output = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, steps: list[list[str]], cwd: Path, parent=None):
        super().__init__(parent)
        self.steps = list(steps)
        self.cwd = Path(cwd)
        self.proc: QProcess | None = None
        self._cur: list[str] = []
        self._cancelled = False

    def start(self):
        self._next(0)

    def cancel(self):
        self._cancelled = True
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            kill_tree(int(self.proc.processId()))

    def running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def _next(self, code: int):
        if self._cancelled:
            self.finished.emit(1)
            return
        if code != 0:
            if self._cur[-2:] == ["get", "--offline"]:
                self.steps.insert(0, self._cur[:-1])          # online pub get
            else:
                self.finished.emit(code)
                return
        if not self.steps:
            self.finished.emit(0)
            return
        self._cur = self.steps.pop(0)
        self.output.emit("> " + " ".join(Path(self._cur[0]).name if i == 0 else a for i, a in enumerate(self._cur))
                         + "\n")
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(str(self.cwd))
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(
            lambda: self.output.emit(bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")))
        self.proc.finished.connect(lambda c, _s: self._next(c))
        self.proc.errorOccurred.connect(lambda e: self._next(1) if e == QProcess.ProcessError.FailedToStart else None)
        self.proc.start(self._cur[0], self._cur[1:])


# ===================================================================== flutter run session
class FlutterSession(QObject):
    """``flutter run -d <device>`` with the interface of radide.debugger.Session (win.session):
    output / finished signals, stop(); plus hot_reload() / hot_restart() (keys r / R on stdin)."""
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)
    status = pyqtSignal(str)          # "Reloaded ..." / "Restarted ..." / "Running on ..."

    def __init__(self, folder: Path, device: dict, package: str, parent=None, extra_args=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.device = device
        self.package = package
        self.paused = False
        self.user_stopped = False
        self.debug = False
        self.ready = False
        self.extra_args = list(extra_args or [])
        self.window_size: tuple[int, int] | None = None     # Windows desktop: the phone's size
        self.proc: QProcess | None = None
        self.steps: StepProcess | None = None
        self._boot_timer: QTimer | None = None
        self._buf = ""
        self._done = False
        self.browser_marker = browser_marker(device.get("id", ""))

    # -------------------------------------------------------------- lifecycle
    def start(self):
        dev = self.device
        if dev.get("kind") == "avd":
            self._boot_avd(dev["avd"])
            return
        self._prepare()

    def _prepare(self):
        steps = prepare_steps(self.folder, self.device.get("platform", "windows"), self.package)
        if not steps:
            self._run()
            return
        self.steps = StepProcess(steps, self.folder, self)
        self.steps.output.connect(self.output.emit)
        self.steps.finished.connect(lambda c: self._run() if c == 0 else self._finish(c))
        self.steps.start()

    def _run(self):
        from ..languages.flutter import flutter_exe
        if self.user_stopped:
            self._finish(0)
            return
        if self.device.get("platform") == "windows" and self.window_size:
            phone_window(self.folder, self.window_size)
        args = ["run", "-d", self.device["id"], "--target", "lib/main.dart", *self.extra_args]
        if self.device["id"] == "web-server":
            args += ["--web-port", str(self.device.get("port", 8765))]
        if self.browser_marker:
            args.append(f"--web-browser-flag={self.browser_marker}")
        self.output.emit(f"> flutter {' '.join(args)}\n")
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(str(self.folder))
        env = QProcessEnvironment.systemEnvironment()
        env.insert("NO_COLOR", "1")
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(lambda c, _s: self._finish(c))
        self.proc.errorOccurred.connect(self._on_error)
        self.proc.start(flutter_exe() or "flutter", args)

    def _on_error(self, err):
        if err == QProcess.ProcessError.FailedToStart:
            self.failed.emit("flutter could not be started - is Flutter installed?")
            self._finish(1)

    def _read(self):
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
        self.output.emit(text)
        self._buf = (self._buf + text)[-4000:]
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(("Reloaded", "Restarted")) or "Hot reload" in s and "rejected" in s:
                self.status.emit(s)
            # ready = the app is connected (web: after the browser loaded it), not only the key help
            if "Dart VM Service" in s and "available at" in s and not self.ready:
                self.ready = True
                self.status.emit(f"Running on {self.device.get('name', self.device['id'])} - "
                                 "save to hot reload")

    def _finish(self, code: int):
        if self._done:
            return
        self._done = True
        if self._boot_timer is not None:
            self._boot_timer.stop()
        # flutter leaves the browser it launched open when it ends on a compile error: close that one
        kill_marked_browser(self.browser_marker)
        self.finished.emit(int(code))

    def running(self) -> bool:
        if self._done:
            return False
        return True

    # -------------------------------------------------------------- commands
    def send(self, key: str) -> bool:
        if self.proc is not None and self.proc.state() == QProcess.ProcessState.Running:
            self.proc.write((key + "\n").encode())
            return True
        return False

    def hot_reload(self) -> bool:
        return self.ready and self.send("r")

    def hot_restart(self) -> bool:
        return self.ready and self.send("R")

    def stop(self):
        self.user_stopped = True
        if self.steps is not None and self.steps.running():
            self.steps.cancel()
        if self.proc is None or self.proc.state() == QProcess.ProcessState.NotRunning:
            self._finish(0)
            return
        self.send("q")
        pid = int(self.proc.processId())
        QTimer.singleShot(5000, lambda: kill_tree(pid) if self.proc is not None and
                          self.proc.state() != QProcess.ProcessState.NotRunning else None)

    # Session interface (no debugger in plain flutter run)
    def cont(self):
        pass

    step_into = step_over = step_out = cont

    def evaluate(self, expr: str):
        self.evalResult.emit("(the Immediate window needs Debug > Use Dart debugger)")

    def set_breakpoint(self, *a, **kw):
        pass

    def set_break_on_exception(self, on):
        pass

    # -------------------------------------------------------------- Android emulator
    def _boot_avd(self, name: str):
        exe, adb = emulator_exe(), adb_exe()
        if not exe or not adb:
            self.failed.emit("Android SDK emulator / adb not found")
            self._finish(1)
            return
        self.output.emit(f"> Starting the Android emulator '{name}' (first boot can take a minute)...\n")
        before = set(_adb_devices(adb))
        ok, _pid = QProcess.startDetached(exe, ["-avd", name, "-no-snapshot-save"])
        if not ok:
            self.failed.emit(f"could not start the emulator {name}")
            self._finish(1)
            return
        self._booted_serial = None
        self._boot_left = 600 // 3
        self._boot_timer = QTimer(self)

        def poll():
            if self.user_stopped:
                self._boot_timer.stop()
                self._finish(0)
                return
            self._boot_left -= 1
            if self._boot_left <= 0:
                self._boot_timer.stop()
                self.failed.emit("the emulator did not boot in 10 minutes")
                self._finish(1)
                return
            if self._booted_serial is None:
                new = [s for s in _adb_devices(adb) if s.startswith("emulator-") and s not in before]
                if not new:
                    new = [s for s in _adb_devices(adb) if s.startswith("emulator-")]
                if new:
                    self._booted_serial = new[0]
                    self.output.emit(f"  emulator is {new[0]}, waiting for Android to boot...\n")
                return
            r = subprocess.run([adb, "-s", self._booted_serial, "shell", "getprop", "sys.boot_completed"],
                               capture_output=True, text=True, timeout=10,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.stdout.strip() == "1":
                self._boot_timer.stop()
                self.output.emit("  Android is ready.\n")
                self.device = {"id": self._booted_serial, "name": f"{name} ({self._booted_serial})",
                               "platform": "android", "kind": "device"}
                self.status.emit(f"emulator {self._booted_serial} ready")
                self._prepare()
        self._boot_timer.timeout.connect(poll)
        self._boot_timer.start(3000)


def _adb_devices(adb: str) -> list[str]:
    try:
        r = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=15,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.split()[0] for ln in r.stdout.splitlines()[1:] if ln.strip() and ln.split()[-1] == "device"]


# ===================================================================== the feature
class MobileFeature(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.devices: list[dict] = []          # from flutter devices + AVDs
        self.build: StepProcess | None = None
        self._dev_proc: QProcess | None = None
        self._make_ui()
        self._wrap()
        self._fill_devices([])
        QTimer.singleShot(0, self._attach_build_menu)
        self.update_ui()

    # ---------------------------------------------------------------- UI
    def _make_ui(self):
        win = self.win
        tb = QToolBar("Mobile", win)
        tb.setObjectName("Mobile")
        self.toolbar = tb
        lbl = QLabel(" Device: ")
        tb.addWidget(lbl)
        self.combo = QComboBox()
        self.combo.setMinimumWidth(220)
        self.combo.setToolTip("Where F5 runs the mobile app (Windows, a browser, a phone or an Android emulator)")
        self.combo.activated.connect(self._on_device_chosen)
        tb.addWidget(self.combo)
        self.a_refresh = QAction("Refresh devices", win)
        self.a_refresh.setToolTip("Look for devices again (flutter devices + Android emulators)")
        self.a_refresh.triggered.connect(self.refresh_devices)
        self.a_reload = QAction("Hot Reload", win)
        self.a_reload.setShortcut(QKeySequence("Ctrl+Alt+R"))
        self.a_reload.setToolTip("Hot Reload (Ctrl+Alt+R) - also done automatically when you save")
        self.a_reload.triggered.connect(lambda: self.hot_reload(manual=True))
        self.a_restart = QAction("Hot Restart", win)
        self.a_restart.setShortcut(QKeySequence("Ctrl+Alt+Shift+R"))
        self.a_restart.setToolTip("Hot Restart (Ctrl+Alt+Shift+R) - restarts the app, the state is lost")
        self.a_restart.triggered.connect(self.hot_restart)
        try:
            from .. import icons
            for a, name in ((self.a_refresh, "refresh"), (self.a_reload, "hot_reload"), (self.a_restart, "restart")):
                ic = icons.icon(name)
                if ic is not None and not ic.isNull():
                    a.setIcon(ic)
        except Exception:  # noqa: BLE001 - text-only buttons
            pass
        for a in (self.a_refresh, self.a_reload, self.a_restart):
            tb.addAction(a)
            win.addAction(a)
        self.a_dap = QAction("Always Use the Dart Debugger for F5", win, checkable=True)
        self.a_dap.setToolTip("F5 starts the app under the Dart debugger (flutter debug_adapter): breakpoints, "
                              "stepping and variables. Without this option the debugger is used when the project "
                              "has breakpoints. Ctrl+F5 always runs without it.")
        self.a_dap.setChecked(str(win.settings.value("mobile/use_dap", "false")).lower() == "true")
        self.a_dap.toggled.connect(lambda on: win.settings.setValue("mobile/use_dap", "true" if on else "false"))
        win.addToolBar(tb)
        tb.setVisible(False)

    def _attach_build_menu(self):
        win = self.win
        mb = win.menuBar()
        build = None
        for a in mb.actions():
            m = a.menu()
            if m is not None and a.text().replace("&", "").strip().lower() == "build":
                build = m
                break
        if build is None:
            build = QMenu("&Build", win)
            debug_act = next((a for a in mb.actions() if a.text().replace("&", "") == "Debug"), None)
            if debug_act is not None:
                mb.insertMenu(debug_act, build)
            else:
                mb.addMenu(build)
        self.build_menu = build.addMenu("&Mobile App")
        self.build_menu.menuAction().setToolTip("Build the Flutter app")
        for text, kind in (("Android &APK", "apk"), ("Android App &Bundle (Google Play)", "appbundle"),
                           ("&Windows EXE", "windows"), ("&Web site", "web"), (None, None),
                           ("Android APK (&debug, faster)", "apk-debug")):
            if text is None:
                self.build_menu.addSeparator()
                continue
            self.build_menu.addAction(text, lambda k=kind: self.build_app(k))
        self.build_menu.addSeparator()
        self.a_cancel_build = self.build_menu.addAction("&Cancel Build", self.cancel_build)
        self.build_menu.addSeparator()
        self.a_fold_avd = self.build_menu.addAction("Create Foldable Emulator", self.create_foldable_emulator)
        self.a_fold_avd.setToolTip(f"Create the Android emulator {FOLD_AVD} (a foldable phone) - other emulators "
                                   "are not changed")
        # Debug menu: hot reload / restart / the Dart debugger option
        dbg = next((a.menu() for a in mb.actions() if a.menu() is not None
                    and a.text().replace("&", "") == "Debug"), None)
        if dbg is not None:
            dbg.addSeparator()
            self.mobile_debug_menu = dbg.addMenu("&Mobile")
            for a in (self.a_reload, self.a_restart):
                self.mobile_debug_menu.addAction(a)
            self.mobile_debug_menu.addSeparator()
            self.mobile_debug_menu.addAction(self.a_dap)
            self.mobile_debug_menu.addAction(self.a_refresh)
        self.update_ui()

    def update_ui(self):
        mob = is_mobile(self.win)
        fl = is_flutter(self.win)
        if self.toolbar.isVisible() != fl:
            self.toolbar.setVisible(fl)
            if fl and len(self.devices) <= 1:
                self.refresh_devices()
        running = isinstance(self.win.session, (FlutterSession,)) and self.win.session.running() or \
            self._dap_running()
        self.a_reload.setEnabled(fl and running)
        self.a_restart.setEnabled(fl and running)
        if hasattr(self, "build_menu"):
            self.build_menu.menuAction().setVisible(fl)
            self.a_cancel_build.setEnabled(self.build is not None and self.build.running())
        if hasattr(self, "mobile_debug_menu"):
            self.mobile_debug_menu.menuAction().setVisible(mob)
        if fl:
            self._select_saved_device()

    def _dap_running(self) -> bool:
        s = self.win.session
        return s is not None and getattr(s, "_radide_flutter_dap", False) and s.running()

    # ---------------------------------------------------------------- devices
    def _fill_devices(self, devices: list[dict]):
        base = [{"id": "windows", "name": "Windows (desktop)", "platform": "windows", "kind": "device"},
                {"id": "chrome", "name": "Chrome (web)", "platform": "web", "kind": "device"},
                {"id": "web-server", "name": "Web server (any browser, http://localhost:8765)", "platform": "web",
                 "kind": "device"}]
        seen = {d["id"] for d in devices}
        out = list(devices)
        for d in base:
            if d["id"] not in seen and (d["id"] != "chrome" or not devices):
                out.append(d)
        running_avds = {d.get("avd") for d in devices}
        for avd in list_avds():
            if avd not in running_avds:
                out.append({"id": f"avd:{avd}", "name": f"Android emulator: {avd.replace('_', ' ')} (start)",
                            "platform": "android", "kind": "avd", "avd": avd})
        self.devices = out
        self.combo.blockSignals(True)
        self.combo.clear()
        for d in out:
            self.combo.addItem(d["name"], d["id"])
        self.combo.blockSignals(False)
        self._select_saved_device()

    def refresh_devices(self):
        """flutter devices --machine in the background (it takes a few seconds)."""
        from ..languages.flutter import flutter_exe
        exe = flutter_exe()
        if not exe or (self._dev_proc is not None and self._dev_proc.state() != QProcess.ProcessState.NotRunning):
            return
        self.combo.setToolTip("Looking for devices...")
        p = QProcess(self)
        self._dev_proc = p
        p.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)

        def done(_c, _s):
            text = bytes(p.readAllStandardOutput()).decode("utf-8", "replace")
            i = text.find("[")
            try:
                raw = json.loads(text[i:]) if i >= 0 else []
            except ValueError:
                raw = []
            devs = []
            for d in raw:
                if not d.get("isSupported", True):
                    continue
                plat = platform_of(d.get("targetPlatform", ""))
                name = d.get("name", d.get("id"))
                if d.get("emulator") and plat == "android":
                    name = f"Android emulator: {name}"
                devs.append({"id": d.get("id"), "name": f"{name} ({d.get('id')})" if plat == "android" else name,
                             "platform": plat, "kind": "device",
                             "avd": (d.get("emulatorId") or "") if d.get("emulator") else ""})
            self._fill_devices(devs)
            self.combo.setToolTip("Where F5 runs the mobile app")
        p.finished.connect(done)
        p.start(exe, ["devices", "--machine"])

    def current_device(self) -> dict:
        i = self.combo.currentIndex()
        if 0 <= i < len(self.devices):
            return self.devices[i]
        return {"id": "windows", "name": "Windows (desktop)", "platform": "windows", "kind": "device"}

    def _select_saved_device(self):
        proj = self.win.project
        if proj is None:
            return
        want = str(_project_mobile(proj).get("device") or "windows")
        for i, d in enumerate(self.devices):
            if d["id"] == want or (d.get("avd") and f"avd:{d['avd']}" == want):
                if self.combo.currentIndex() != i:
                    self.combo.setCurrentIndex(i)
                return

    def _on_device_chosen(self, i):
        proj = self.win.project
        if proj is not None and 0 <= i < len(self.devices):
            d = self.devices[i]
            _project_mobile(proj)["device"] = d["id"]
            try:
                proj.save()
            except OSError:
                pass

    # ---------------------------------------------------------------- wrapping the main window
    def _wrap(self):
        win = self.win
        orig_run, orig_save = win.run_project, win.save_all
        orig_update = win._update_actions

        def run_project(debug: bool = True):
            if is_flutter(win):
                return self.run_flutter(debug)
            if is_mobile(win):
                self._write_files()
            return orig_run(debug)

        def save_all():
            before = designer_state(win) if is_flutter(win) else None
            ok = orig_save()
            if ok and is_mobile(win):
                self._write_files()
                if before is not None and designer_state(win) != before:
                    self.hot_restart()          # initial values of controls changed: State must be rebuilt
                else:
                    self.hot_reload(manual=False)
            return ok

        def update_actions():
            orig_update()
            try:
                self.update_ui()
            except Exception:  # noqa: BLE001 - never break the IDE
                pass
        win.run_project = run_project
        win.save_all = save_all
        win._update_actions = update_actions

    def _write_files(self):
        proj = self.win.project
        try:
            plugin = self.win.run_plugin()
            if hasattr(plugin, "write_project_files"):
                written = plugin.write_project_files(proj)
                if written and "lib/main.dart" in written:
                    self.win.statusBar().showMessage("Updated lib/main.dart (screens)", 2000)
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[mobile] could not write the project files: {e}")

    # ---------------------------------------------------------------- run
    def run_flutter(self, debug: bool = True):
        win = self.win
        if win.project is None or (win.session is not None and win.session.running()):
            return
        from ..languages.flutter import flutter_exe, package_name
        if not flutter_exe():
            QMessageBox.warning(win, "Run", "Flutter is not installed.\nInstall it from https://flutter.dev "
                                            "and add flutter\\bin to PATH (C:\\flutter is found too).")
            return
        win.save_all()
        plugin = win.run_plugin()
        try:
            plugin.regenerate_all(win.project)
        except Exception as e:  # noqa: BLE001
            win.log(f"*** Cannot generate the app: {e}")
            return
        dev = self.current_device()
        folder = Path(win.project.folder)
        win.output.clear()
        win.dock_output.show()
        win.dock_output.raise_()
        use_dap = self.a_dap.isChecked() or any(win._all_breakpoints())      # F5 with breakpoints = debugger
        if debug and use_dap and dev.get("kind") != "avd":
            if self._start_dap(dev, folder, package_name(win.project.name)):
                return
        win.log(f"------ Run {win.project.name} on {dev['name']} ------")
        s = FlutterSession(folder, dev, package_name(win.project.name), win)
        s.window_size = startup_size(win.project)
        s.output.connect(win._append_output)
        s.failed.connect(lambda err: win.log(f"*** Error: {err}"))
        s.status.connect(lambda m: win.statusBar().showMessage(m, 6000))
        s.finished.connect(win._on_finished)
        win.session = s
        s.start()
        win.statusBar().showMessage(f"Starting on {dev['name']}...")
        win._update_actions()

    def _start_dap(self, dev: dict, folder: Path, package: str) -> bool:
        """F5 under the Dart debugger: flutter debug_adapter through radide.dap.DapSession."""
        win = self.win
        steps = prepare_steps(folder, dev.get("platform", "windows"), package)
        if steps:          # create the platform folder / pub get synchronously-free: run them first, then debug
            sp = StepProcess(steps, folder, win)
            sp.output.connect(win._append_output)
            sp.finished.connect(lambda c: self._start_dap(dev, folder, package) if c == 0 else
                                win.log(f"*** Preparing the project failed ({c})"))
            self.build = sp
            sp.start()
            return True
        from ..dap import DapSession
        from ..languages.flutter import flutter_exe
        win.log(f"------ Debug {win.project.name} on {dev['name']} (Dart debugger) ------")
        s = DapSession("dart", str(folder / "lib" / "main.dart"), [], folder, None, win._all_breakpoints(), win)
        s.argv = [flutter_exe(), "debug_adapter"]
        marker = browser_marker(dev["id"])
        tool_args = ["-d", dev["id"]] + ([f"--web-browser-flag={marker}"] if marker else [])
        s.launch_args.update({"program": str(folder / "lib" / "main.dart"), "cwd": str(folder),
                              "deviceId": dev["id"], "toolArgs": tool_args})
        s._radide_flutter_dap = True
        if marker:           # close the browser flutter started when the session ends (also on compile errors)
            s.finished.connect(lambda _c: kill_marked_browser(marker))

        def stop():                      # flutter.bat -> flutter tool -> the app: end the whole tree
            if not s.running():
                return
            s.user_stopped = True
            pid = int(s.proc.processId())
            s._request("disconnect", {"terminateDebuggee": True})
            QTimer.singleShot(4000, lambda: kill_tree(pid) if s.running() else None)
        s.stop = stop
        s.output.connect(win._append_output)
        s.stopped.connect(win._on_stopped)
        s.resumed.connect(win._on_resumed)
        s.evalResult.connect(lambda txt: win.immediate.show_result(txt))
        s.finished.connect(win._on_finished)
        s.failed.connect(lambda err: win.log(f"*** Error: {err}"))
        win.session = s
        s.start()
        win._update_actions()
        return True

    # ---------------------------------------------------------------- hot reload
    def hot_reload(self, manual: bool = False) -> bool:
        s = self.win.session
        if isinstance(s, FlutterSession):
            if s.hot_reload():
                self.win.statusBar().showMessage("Hot reload...", 3000)
                return True
            if manual:
                self.win.statusBar().showMessage("The app is still starting - try again in a moment", 3000)
            return False
        if s is not None and getattr(s, "_radide_flutter_dap", False) and s.running():
            s._request("hotReload", {})
            self.win.statusBar().showMessage("Hot reload...", 3000)
            return True
        return False

    def hot_restart(self) -> bool:
        s = self.win.session
        if isinstance(s, FlutterSession):
            return s.hot_restart()
        if s is not None and getattr(s, "_radide_flutter_dap", False) and s.running():
            s._request("hotRestart", {})
            return True
        return False

    # ---------------------------------------------------------------- build
    BUILDS = {
        "apk": (["build", "apk", "--release"], "android", "build/app/outputs/flutter-apk/app-release.apk"),
        "apk-debug": (["build", "apk", "--debug"], "android", "build/app/outputs/flutter-apk/app-debug.apk"),
        "appbundle": (["build", "appbundle"], "android", "build/app/outputs/bundle/release/app-release.aab"),
        "windows": (["build", "windows"], "windows", "build/windows/x64/runner/Release"),
        "web": (["build", "web"], "web", "build/web"),
    }

    def build_app(self, kind: str):
        win = self.win
        if not is_flutter(win):
            QMessageBox.information(win, "Build", "Open a Flutter project first.")
            return
        if self.build is not None and self.build.running():
            QMessageBox.information(win, "Build", "A build is already running (Build > Mobile App > Cancel Build).")
            return
        from ..languages.flutter import flutter_exe, package_name
        args, platform, artifact = self.BUILDS[kind]
        win.save_all()
        plugin = win.run_plugin()
        plugin.regenerate_all(win.project)
        folder = Path(win.project.folder)
        steps = prepare_steps(folder, platform, package_name(win.project.name)) + [[flutter_exe(), *args]]
        win.output.clear()
        win.dock_output.show()
        win.dock_output.raise_()
        win.log(f"------ Build {kind}: {win.project.name} ------")
        sp = StepProcess(steps, folder, win)
        sp.output.connect(win._append_output)

        def done(code):
            out = folder / artifact
            if code == 0 and out.exists():
                win.log(f"\n------ Build succeeded: {out} ------")
                win.statusBar().showMessage(f"Build succeeded: {out.name}", 8000)
                if kind == "web":
                    win.log("Serve the folder with any web server, e.g.  python -m http.server -d build/web")
            else:
                win.log(f"\n------ Build failed (exit code {code}) ------")
            self.update_ui()
        sp.finished.connect(done)
        self.build = sp
        sp.start()
        self.update_ui()

    def create_foldable_emulator(self):
        """Build > Mobile App > Create Foldable Emulator: avdmanager in a worker thread (it takes a while)."""
        import threading
        win = self.win
        if FOLD_AVD in list_avds():
            QMessageBox.information(win, "Create Foldable Emulator",
                                    f"The foldable emulator {FOLD_AVD} already exists - choose it in the Device box.")
            return
        win.statusBar().showMessage(f"Creating the foldable emulator {FOLD_AVD}...")
        result: dict = {}

        def work():
            result["r"] = foldable_avd(FOLD_AVD)

        th = threading.Thread(target=work, daemon=True)
        th.start()
        timer = QTimer(self)

        def poll():
            if th.is_alive():
                return
            timer.stop()
            ok, msg = result.get("r", (False, "failed"))
            win.log(msg)
            win.statusBar().showMessage(msg, 8000)
            if ok:
                self._fill_devices([d for d in self.devices if d.get("kind") == "device"
                                    and d["id"] not in ("windows", "chrome", "web-server")])
            else:
                QMessageBox.warning(win, "Create Foldable Emulator", msg)
        timer.timeout.connect(poll)
        timer.start(500)

    def cancel_build(self):
        if self.build is not None and self.build.running():
            self.build.cancel()
            self.win.log("\n------ Build cancelled ------")


def foldable_diags(win) -> list:
    """Error List provider: controls lying across the hinge of a foldable / dual-screen form."""
    proj = getattr(win, "project", None)
    if proj is None:
        return []
    from ..tools import Diag
    from ..mobile.controls import hinge_conflicts, is_foldable
    out = []
    docs = getattr(win, "docs", {}) or {}
    for name in list(getattr(proj, "forms", []) or []):
        try:
            if name in docs:
                form = docs[name].form
            else:
                from ..model import Form
                path = proj.form_path(name)
                if not path.is_file() or "Device" not in path.read_text(encoding="utf-8", errors="replace"):
                    continue
                form = Form.load(path)
            if not is_foldable(form.props.get("Device")):
                continue
            for _ctrl, msg in hinge_conflicts(form):
                out.append(Diag("Warning", f"Controls cross the hinge: {msg}", f"{name}.form", 1))
        except Exception:  # noqa: BLE001 - never break the Error List
            continue
    return out


def install(win) -> None:
    win.mobile = MobileFeature(win)
    providers = win.__dict__.setdefault("diag_providers", [])
    if foldable_diags not in providers:
        providers.append(foldable_diags)
