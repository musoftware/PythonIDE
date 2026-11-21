"""DOSBox-X adapter of the DOS projects (no Qt in here).

The emulator itself is found / downloaded by radide.retro.emu (toolchain.dosbox_exe); this module writes a
``.conf`` for every run (mounts, CPU cycles preset, machine, memory, sound) and starts DOSBox-X:

    run = DosRun(mounts=[("C", folder)], commands=["HELLO.EXE"], cycles="486")
    proc = launch(run, conf_dir)                        # a window; keeps the DOS prompt when run.keep_window
    rc, timed_out = run_headless(run, conf_dir, 60)     # -silent: no window, for builds and tests

Headless runs use DOSBox-X's ``-silent`` switch (no window, exit after AUTOEXEC) and ``-time-limit`` as the
safety net; the caller redirects program output to a file inside the mounted folder (``PROG > OUT.TXT``).
The DOSBox-X debugger (``run.debugger``) starts the program with the built-in ``DEBUGBOX`` command, which breaks
at the program's first instruction (Alt+Pause opens the debugger at any time).
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# CPU speed presets -> DOSBox-X "cycles" values
CYCLES = {
    "xt": ("IBM PC/XT 8088 4.77 MHz", "fixed 300"),
    "286": ("AT 80286 12 MHz", "fixed 2000"),
    "386": ("80386DX 33 MHz", "fixed 8000"),
    "486": ("80486DX2 66 MHz", "fixed 27000"),
    "pentium": ("Pentium 90 MHz", "fixed 60000"),
    "auto": ("Automatic (DOSBox-X decides)", "auto"),
    "max": ("As fast as possible", "max"),
}
MACHINES = {"svga_s3": "SVGA (S3 Trio64) - default", "vgaonly": "VGA only", "ega": "EGA", "cga": "CGA",
            "hercules": "Hercules (monochrome)", "tandy": "Tandy 1000", "pcjr": "IBM PCjr"}


def cycles_value(preset: str) -> str:
    if preset in CYCLES:
        return CYCLES[preset][1]
    p = str(preset or "").strip()
    if p.isdigit():
        return f"fixed {p}"
    return p or "max"


def to_dos_path(p: str) -> str:
    return str(p).replace("/", "\\")


@dataclass
class DosRun:
    mounts: list = field(default_factory=list)       # [(letter, host folder)] - C: is the working drive
    commands: list = field(default_factory=list)     # DOS commands run after mounting
    path: list = field(default_factory=list)         # extra PATH entries (DOS paths, e.g. "D:\\")
    env: dict = field(default_factory=dict)          # SET name=value
    cycles: str = "max"
    machine: str = "svga_s3"
    memsize: int = 16
    keep_window: bool = False                        # stay at the DOS prompt after the commands
    title: str = ""
    sound: bool = True
    debugger: bool = False                           # DEBUGBOX the last command
    fullscreen: bool = False
    core: str = "auto"
    extra: dict = field(default_factory=dict)        # {"section": {"key": "value"}}

    def autoexec(self) -> list[str]:
        lines = ["@echo off"]
        for letter, host in self.mounts:
            lines.append(f'mount {letter.lower()} "{Path(host)}"')
        drive = (self.mounts[0][0] if self.mounts else "C").upper()
        lines.append(f"{drive}:")
        path = list(self.path) + ["Z:\\"]
        lines.append("set PATH=" + ";".join(path))
        for k, v in self.env.items():
            lines.append(f"set {k}={v}")
        cmds = list(self.commands)
        if self.debugger and cmds:
            cmds[-1] = "debugbox " + cmds[-1]
        lines += cmds
        if self.keep_window:
            lines += ["echo.", "echo [RAD IDE] The program has ended - type EXIT to close DOSBox-X."]
        else:
            lines.append("exit")
        return lines


def write_conf(run: DosRun, path: Path) -> Path:
    """The .conf of *run* (mounts and commands go into [autoexec])."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sections: dict[str, dict[str, str]] = {
        "sdl": {"output": "surface", "fullscreen": "true" if run.fullscreen else "false", "autolock": "false"},
        "dosbox": {"machine": run.machine, "memsize": str(int(run.memsize)), "quit warning": "false",
                   "title": run.title or "RAD IDE"},
        "cpu": {"cycles": cycles_value(run.cycles), "core": run.core},
        "dos": {"lfn": "false", "ver": "6.22"},
        "mixer": {"nosound": "false" if run.sound else "true"},
        "speaker": {"pcspeaker": "true"},
        "sblaster": {"sbtype": "sb16"},
        "log": {"logfile": ""},
    }
    for sec, kv in (run.extra or {}).items():
        sections.setdefault(sec, {}).update({k: str(v) for k, v in kv.items()})
    out = ["# written by RAD IDE (radide/retro/dos/dosbox.py) - regenerated on every run"]
    for sec, kv in sections.items():
        out.append(f"[{sec}]")
        out += [f"{k}={v}" for k, v in kv.items()]
        out.append("")
    out.append("[autoexec]")
    out += run.autoexec()
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def _exe(log=print, download: bool = True) -> str:
    from .toolchain import dosbox_exe
    exe = dosbox_exe(download=download, log=log)
    if not exe:
        raise FileNotFoundError("DOSBox-X was not found. Tools > Retro Emulators... (or Tools > DOS Toolchains...) "
                                "downloads the official portable build.")
    return exe


def command_line(run: DosRun, conf: Path, silent: bool = False, time_limit: int | None = None,
                 exe: str | None = None) -> list[str]:
    args = [exe or _exe(), "-conf", str(conf), "-nopromptfolder", "-fastlaunch", "-nolog"]
    if silent:
        args.append("-silent")
    if time_limit:
        args += ["-time-limit", str(int(time_limit))]
    return args


def _tie(proc: subprocess.Popen) -> None:
    """Close DOSBox-X together with this runner (the IDE's Stop kills the runner): the emu slice's job object."""
    try:
        from types import SimpleNamespace

        from ..emu.launch import tie_to_this_process
        tie_to_this_process(SimpleNamespace(popen=proc))       # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - best effort
        pass


def launch(run: DosRun, conf_dir: Path, name: str = "run.conf", log=print) -> subprocess.Popen:
    """Start DOSBox-X with a window (the IDE's Run). The caller owns the process."""
    conf = write_conf(run, Path(conf_dir) / name)
    args = command_line(run, conf, exe=_exe(log))
    log("DOSBox-X: " + " ".join(f'"{a}"' if " " in a else a for a in args))
    proc = subprocess.Popen(args, cwd=str(Path(args[0]).parent))
    _tie(proc)
    return proc


def run_headless(run: DosRun, conf_dir: Path, timeout: int = 60, name: str = "headless.conf",
                 log=print) -> tuple[int, bool]:
    """Run without a window and wait (builds inside DOS, tests). Returns (exit code, timed out?)."""
    run.keep_window = False
    conf = write_conf(run, Path(conf_dir) / name)
    args = command_line(run, conf, silent=True, time_limit=timeout + 5, exe=_exe(log))
    t0 = time.time()
    p = subprocess.Popen(args, cwd=str(Path(args[0]).parent), creationflags=NO_WINDOW)
    _tie(p)
    try:
        rc = p.wait(timeout=timeout + 15)
        return rc, (time.time() - t0) >= timeout
    except subprocess.TimeoutExpired:
        p.kill()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        return -1, True


def capture_text(run: DosRun, folder: Path, command: str, out_name: str = "_OUT.TXT", timeout: int = 30,
                 keys: str = "", screen: bool = True, log=print) -> dict:
    """Run *command* headless with its output redirected to *out_name* in *folder* (mounted as C:) and, when
    *screen*, the text screen saved by RADSCR.COM (helpers.py). *keys* are stuffed into the keyboard buffer first
    (RADKEYS.COM). Returns {"rc", "timed_out", "stdout", "screen", "graphics"}."""
    from . import helpers
    folder = Path(folder)
    tools = folder / "_build" / "radtools"
    helpers.write_helpers(tools)
    for f in (out_name, "_SCREEN.TXT", "_SCR13.RAW"):
        try:
            (folder / f).unlink()
        except OSError:
            pass
    rel = os.path.relpath(tools, folder).replace("/", "\\")
    pre = [f"C:\\{rel}\\RADCAP.COM"]
    if keys:
        pre.append(f"C:\\{rel}\\RADKEYS.COM {keys}")
    post = [f"C:\\{rel}\\RADSCR.COM"] if screen else []
    run.commands = list(run.commands) + pre + [f"{command} > {out_name}"] + post
    rc, timed_out = run_headless(run, folder / "_build", timeout, log=log)
    res = {"rc": rc, "timed_out": timed_out, "stdout": "", "screen": "", "graphics": None}
    try:
        res["stdout"] = (folder / out_name).read_bytes().decode("cp437", "replace")
    except OSError:
        pass
    try:
        res["screen"] = (folder / "_SCREEN.TXT").read_bytes().decode("cp437", "replace")
    except OSError:
        pass
    raw = folder / "_SCR13.RAW"
    if raw.is_file():
        res["graphics"] = str(raw)
    return res


__all__ = ["CYCLES", "MACHINES", "DosRun", "capture_text", "command_line", "cycles_value", "launch",
           "run_headless", "to_dos_path", "write_conf"]
