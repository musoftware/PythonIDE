"""Start a ROM / program in its emulator, with debugging and hot reload (no Qt in here).

    proc = run_rom("build/game.nes")                         # Mesen 2 (or FCEUX)
    proc = run_rom("game.bin", "a2600", debug=True, symbols="game.sym")   # Stella's debugger with DASM labels
    proc = run_rom("game.gba", debug=True)                   # mGBA + GDB stub -> proc.gdb()  (GdbRsp)
    proc = run_rom("game.prg", debug=True)                   # VICE + binary monitor -> proc.monitor() (ViceMonitor)
    proc.reload("game.prg")                                  # hot reload (VICE autostart) or restart
    proc.stop()                                              # only processes RAD IDE started

How debugging works per emulator:

    stella    -debug opens Stella's own debugger; a DASM symbol file (-s) / listing (-l) is copied next to the
              ROM as <rom>.sym / <rom>.lst, which Stella loads by itself, so labels and source show.
    mesen     Mesen's debugger windows; ca65/ld65 .dbg, RGBDS .sym, .mlb files next to the ROM are imported
              automatically; a .lua script (symbols=..., or lua=...) is passed on the command line.
    fceux     -lua <script> when given; its debugger is in its Debug menu.
    mgba      -g: GDB stub on a free TCP port (proc.gdb_port) -> Retro Debugger (radide/retro/emu/gdb_rsp.py).
    vice      -binarymonitor on a free port (proc.monitor_port) -> Retro Debugger (vice_monitor.py); labels from a
              VICE label file (al C:xxxx .name) via -moncommands.
    atari800  -monitor (debug) starts in its built-in monitor; -label-file loads labels; -bpc <addr> breaks.
    dosbox-x  see dos.py (generated .conf).
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

from .catalog import EMULATORS, SYSTEM_TITLES, emulators_for
from .manager import config_dir, find, missing_hint
from .systems import detect_system


class EmuError(Exception):
    pass


def free_port(preferred: int = 0) -> int:
    for p in ([preferred] if preferred else []) + [0]:
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return s.getsockname()[1]
        except OSError:
            continue
        finally:
            s.close()
    return preferred or 6502


def _startupinfo(minimized: bool):
    if os.name != "nt" or not minimized:
        return None
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 7                      # SW_SHOWMINNOACTIVE: minimised, keeps the IDE focused
    return si


def _place_symbols(rom: Path, symbols, exts) -> list[str]:
    """Copy symbol / listing files next to *rom* named <rom stem><ext> (what Stella / Mesen look for). Files
    already in place are left alone; an older copy RAD IDE made is replaced."""
    placed = []
    for s in ([symbols] if isinstance(symbols, (str, Path)) else list(symbols or [])):
        src = Path(s)
        if not src.is_file() or src.suffix.lower() not in exts:
            continue
        dst = rom.with_suffix(src.suffix.lower())
        try:
            if src.resolve() != dst.resolve():
                if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                    shutil.copy2(src, dst)
            placed.append(str(dst))
        except OSError:
            pass
    return placed


class RetroProcess:
    """A running emulator started by RAD IDE."""

    def __init__(self, emulator: str, exe: str, args: list, rom: str, system: str, debug: bool, cwd: str = "",
                 env: dict | None = None, minimized: bool = False):
        self.emulator, self.exe, self.args, self.rom, self.system, self.debug = emulator, exe, args, rom, system, debug
        self.cwd = cwd or str(Path(rom).parent if rom else Path(exe).parent)
        self.env = env
        self.minimized = minimized
        self.popen: subprocess.Popen | None = None
        self.gdb_port = 0
        self.monitor_port = 0
        self.symbols: list[str] = []
        self.labels: dict[int, str] = {}
        self._monitor = None
        self._gdb = None
        self.started_at = 0.0
        self.rebuild = None             # optional callable() -> rom path, used by hot reload

    # ------------------------------------------------------------------ process
    @property
    def command(self) -> list:
        return [self.exe] + list(self.args)

    def start(self) -> "RetroProcess":
        env = dict(os.environ)
        env.update(self.env or {})
        self.popen = subprocess.Popen(self.command, cwd=self.cwd, env=env, startupinfo=_startupinfo(self.minimized),
                                      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.started_at = time.time()
        return self

    @property
    def pid(self) -> int:
        return self.popen.pid if self.popen else 0

    def alive(self) -> bool:
        return self.popen is not None and self.popen.poll() is None

    def wait(self, timeout: float | None = None) -> int | None:
        if self.popen is None:
            return None
        try:
            return self.popen.wait(timeout)
        except subprocess.TimeoutExpired:
            return None

    def stop(self, timeout: float = 5.0) -> None:
        """Close the emulator RAD IDE started (never any other process)."""
        for client in (self._monitor, self._gdb):
            try:
                if client is not None:
                    client.close()
            except Exception:  # noqa: BLE001
                pass
        self._monitor = self._gdb = None
        if not self.alive():
            return
        self.popen.terminate()
        try:
            self.popen.wait(timeout)
        except subprocess.TimeoutExpired:
            self.popen.kill()
            self.popen.wait(timeout)

    # ------------------------------------------------------------------ debugging
    def monitor(self, retry_for: float = 10.0):
        """The VICE binary monitor connection (connects on first use)."""
        if self.emulator != "vice" or not self.monitor_port:
            raise EmuError("no VICE binary monitor in this session")
        if self._monitor is None or not self._monitor.connected:
            from .vice_monitor import ViceMonitor
            self._monitor = ViceMonitor(self.monitor_port, timeout=10.0).connect(retry_for=retry_for)
        return self._monitor

    def gdb(self, retry_for: float = 10.0):
        """The GDB stub connection of mGBA (connects on first use)."""
        if not self.gdb_port:
            raise EmuError("no GDB stub in this session (start it with debug=True)")
        if self._gdb is None or not self._gdb.connected:
            from .gdb_rsp import GdbRsp
            self._gdb = GdbRsp(self.gdb_port).connect(retry_for=retry_for)
        return self._gdb

    @property
    def debug_backend(self) -> str:
        if self.emulator == "vice" and self.monitor_port:
            return "vice-monitor"
        if self.gdb_port:
            return "gdb-rsp"
        return ""

    # ------------------------------------------------------------------ hot reload
    def can_hot_reload(self) -> bool:
        return self.emulator == "vice" and bool(self.monitor_port) and self.alive()

    def reload(self, rom: str | None = None) -> "RetroProcess":
        """Load the rebuilt ROM: in place when the emulator supports it (VICE: autostart through the monitor),
        otherwise the emulator is restarted with the same options. Returns the process now running it."""
        rom = str(rom or (self.rebuild() if callable(self.rebuild) else self.rom))
        if self.can_hot_reload():
            try:
                mon = self.monitor()
                mon.autostart(rom)
                if not mon.running:
                    mon.exit_monitor()
                self.rom = rom
                return self
            except Exception:  # noqa: BLE001 - fall back to a restart
                pass
        old_rom = self.rom
        self.stop()
        args = [rom if a == old_rom else a for a in self.args]
        self.args, self.rom = args, rom
        self.start()
        return self


_JOBS: list = []


def tie_to_this_process(proc: "RetroProcess") -> bool:
    """Windows: put the emulator into a job object that is closed with this process, so killing the
    ``python -m radide.retro.emu`` runner (the IDE's Stop button) also closes the emulator it started."""
    if os.name != "nt" or proc.popen is None:
        return False
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.OpenProcess.restype = wintypes.HANDLE
        job = k32.CreateJobObjectW(None, None)

        class BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("r", "w", "o", "rt", "wt", "ot")]

        class EXT(ctypes.Structure):
            _fields_ = [("Basic", BASIC), ("Io", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]
        info = EXT()
        info.Basic.LimitFlags = 0x2000                       # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            return False
        h = k32.OpenProcess(0x0101, False, proc.popen.pid)  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
        ok = bool(h) and bool(k32.AssignProcessToJobObject(job, h))
        if h:
            k32.CloseHandle(h)
        _JOBS.append(job)
        return ok
    except Exception:  # noqa: BLE001 - best effort
        return False


# ====================================================================== command lines
def _cmd_stella(exe, rom: Path, debug, symbols, opts) -> tuple[list, dict]:
    args = ["-basedir", str(config_dir("stella"))]
    if debug:
        args.append("-debug")
    for bp in opts.get("breakpoints") or []:
        args += ["-break", f"${int(bp):04X}" if isinstance(bp, int) else str(bp)]
    if opts.get("quiet"):
        args += ["-audio.enabled", "0"]
    return args + [str(rom)], {}


def _cmd_mesen(exe, rom: Path, debug, symbols, opts) -> tuple[list, dict]:
    args = [str(rom)]
    lua = opts.get("lua") or next((s for s in ([symbols] if isinstance(symbols, (str, Path)) else symbols or [])
                                   if str(s).lower().endswith(".lua")), None)
    if lua:
        args.append(str(lua))
    if opts.get("fullscreen"):
        args.append("--fullscreen")
    return args, {}


def _cmd_fceux(exe, rom: Path, debug, symbols, opts) -> tuple[list, dict]:
    args = []
    lua = opts.get("lua")
    if lua:
        args += ["-lua", str(lua)]
    return args + [str(rom)], {}


def _cmd_mgba(exe, rom: Path, debug, symbols, opts) -> tuple[list, dict]:
    args, info = [], {}
    if debug:                               # mGBA's stub always listens on 2345
        if free_port(2345) != 2345:
            raise EmuError("TCP port 2345 (mGBA's GDB stub) is in use - close the other debugger / emulator.")
        args.append("-g")
        info["gdb_port"] = 2345
    if opts.get("bios"):
        args += ["-b", str(opts["bios"])]
    if opts.get("patch"):
        args += ["-p", str(opts["patch"])]
    return args + [str(rom)], info


def _vice_moncommands(labels: Path, rom: Path) -> str:
    """A -moncommands file loading *labels* (VICE label file or 'name = $addr' listing)."""
    from .vice_monitor import load_labels
    lab = load_labels(labels)
    if not lab:
        return ""
    out = config_dir("vice") / f"{rom.stem}.moncommands"
    out.write_text("".join(f"al C:{a:04x} .{n}\n" for a, n in sorted(lab.items())), encoding="utf-8")
    return str(out)


def _cmd_vice(exe, rom: Path, debug, symbols, opts) -> tuple[list, dict]:
    cfg = config_dir("vice") / "vice.ini"
    args = ["-config", str(cfg), "-logfile", str(cfg.with_name("vice.log")),
            "-autostartprgmode", "1"]                 # inject .prg into RAM: no autostart disk image in %APPDATA%
    info = {}
    if debug or opts.get("monitor", True):
        port = free_port(int(opts.get("monitor_port") or 6502))
        args += ["-binarymonitor", "-binarymonitoraddress", f"ip4://127.0.0.1:{port}"]
        info["monitor_port"] = port
    sym = next((Path(s) for s in ([symbols] if isinstance(symbols, (str, Path)) else symbols or [])
                if Path(s).is_file()), None)
    if sym is not None:
        mc = _vice_moncommands(sym, rom)
        if mc:
            args += ["-moncommands", mc]
    if opts.get("initbreak"):
        args += ["-initbreak", str(opts["initbreak"])]
    if opts.get("quiet"):
        args += ["+sound"]
    if opts.get("minimized"):
        args += ["-minimized"]
    if opts.get("warp"):
        args += ["-warp"]
    return args + ["-autostart", str(rom)], info


def _cmd_atari800(exe, rom: Path, debug, symbols, opts) -> tuple[list, dict]:
    if Path(exe).name.lower().startswith("altirra"):
        args = ["/portable"] + (["/debug"] if debug else []) + [str(rom)]
        return args, {}
    args = ["-config", str(config_dir("atari800") / "atari800.cfg"), "-no-autosave-config", "-xl"]
    if debug:
        args.append("-monitor")
    sym = next((Path(s) for s in ([symbols] if isinstance(symbols, (str, Path)) else symbols or [])
                if Path(s).is_file()), None)
    if sym is not None:
        args += ["-label-file", str(sym)]
    for bp in opts.get("breakpoints") or []:
        args += ["-bpc", f"{int(bp):04x}" if isinstance(bp, int) else str(bp)]
    if opts.get("quiet"):
        args.append("-nosound")
    ext = rom.suffix.lower()
    if ext in (".car", ".rom", ".bin"):
        args += ["-cart", str(rom)]
    elif ext in (".atr", ".atx", ".xfd"):
        args += [str(rom)]
    else:
        args += ["-run", str(rom)]
    return args, {}


BUILDERS = {"stella": _cmd_stella, "mesen": _cmd_mesen, "fceux": _cmd_fceux, "mgba": _cmd_mgba, "vice": _cmd_vice,
            "atari800": _cmd_atari800}
SYMBOL_EXTS = {"stella": {".sym", ".lst"}, "mesen": {".dbg", ".sym", ".mlb", ".cdl", ".nl"}, "fceux": {".nl"}}


def command_for(path, system: str | None = None, debug: bool = False, symbols=None, emulator: str | None = None,
                **opts) -> RetroProcess:
    """The RetroProcess (not started) that would run *path*; raises EmuError when no emulator is available."""
    rom = Path(path).resolve()
    system = system or detect_system(rom)
    if not system:
        raise EmuError(f"Cannot tell which machine {rom.name} is for - choose the system.")
    if system == "dos":
        from .dos import dos_process
        return dos_process(rom, debug=debug, **opts)
    cands = [EMULATORS[emulator]] if emulator else emulators_for(system)
    if not cands:
        raise EmuError(f"RAD IDE has no emulator for {SYSTEM_TITLES.get(system, system)}.")
    exe = ""
    emu = cands[0]
    for e in cands:
        exe = find(e.id, opts.get("role", "")) or find(e.id)
        if exe:
            emu = e
            break
    if not exe:
        raise EmuError(missing_hint(cands[0].id))
    from .manager import prepare_portable
    prepare_portable(emu.id)
    if emu.id in SYMBOL_EXTS and symbols:
        placed = _place_symbols(rom, symbols, SYMBOL_EXTS[emu.id])
    else:
        placed = []
    args, info = BUILDERS[emu.id](exe, rom, debug, symbols, opts)
    env = {}
    if opts.get("quiet"):
        env["SDL_AUDIODRIVER"] = "dummy"
    proc = RetroProcess(emu.id, exe, args, str(rom), system, debug, cwd=str(rom.parent), env=env,
                        minimized=bool(opts.get("minimized")))
    proc.gdb_port = info.get("gdb_port", 0)
    proc.monitor_port = info.get("monitor_port", 0)
    proc.symbols = placed or ([str(symbols)] if isinstance(symbols, (str, Path)) else list(symbols or []))
    if emu.id == "vice" and symbols:
        from .vice_monitor import load_labels
        for s in proc.symbols:
            proc.labels.update(load_labels(s))
    return proc


def run_rom(path, system: str | None = None, debug: bool = False, symbols=None, emulator: str | None = None,
            **opts) -> RetroProcess:
    """Start *path* (ROM, program, disk image, DOS folder) in the right emulator and return the RetroProcess.

    *system*: a system id (catalog.SYSTEM_TITLES) or None to detect it. *symbols*: a path or list of
    symbol / listing / label / Lua files. Options: emulator="mesen"|..., minimized=True, quiet=True (no
    sound), breakpoints=[addr, ...] (Stella / Atari800), lua=..., monitor_port=..., initbreak=... (VICE)."""
    proc = command_for(path, system, debug, symbols, emulator, **opts)
    _LAST.clear()
    _LAST.append(proc)
    return proc.start()


_LAST: list[RetroProcess] = []


def last_process() -> RetroProcess | None:
    """The emulator run_rom started last (for Hot Reload / the Retro Debugger)."""
    return _LAST[0] if _LAST else None


__all__ = ["BUILDERS", "EmuError", "RetroProcess", "command_for", "free_port", "last_process", "run_rom",
           "tie_to_this_process"]
