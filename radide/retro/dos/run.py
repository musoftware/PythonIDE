"""Run a DOS project in DOSBox-X (no Qt in here; the IDE's Run / Ctrl+F5 starts this module).

    python -m radide.retro.dos.run <folder> [--debug] [--qbasic] [--no-build] [--capture [--keys K] [--timeout N]]

* builds first when the program is missing or older than a source (radide/retro/dos/build.py);
* DOSBox-X gets a fresh ``_build/run.conf``: the project folder is drive C:, the CPU cycles preset, machine and
  memory come from the project's DOS settings, Z:\\BIN (CWSDPMI, DOS/4GW) is on the PATH; the window stays at
  the DOS prompt afterwards when "keep window" is on;
* ``--debug`` starts the program with DOSBox-X's ``DEBUGBOX`` (the built-in debugger stops at its first
  instruction); the symbol map of the build is printed so that breakpoints can be set with ``BP seg:off``;
* ``--qbasic`` runs the .BAS source in the user's own QBASIC.EXE / QB.EXE (``/RUN``) instead of building;
* ``--capture`` runs without a window, stuffs ``--keys`` (helpers.RADKEYS syntax) and prints what the program
  wrote (standard output + the text screen) - for tests and "Run (captured)".
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from . import build as B
from . import dosbox, toolchain


def _run_config(folder: Path, s: dict, debug: bool = False) -> dosbox.DosRun:
    return dosbox.DosRun(mounts=[("C", folder)], path=["Z:\\BIN", "Z:\\DOS"], cycles=str(s.get("cycles", "max")),
                         machine=str(s.get("machine", "svga_s3")), memsize=int(s.get("memsize", 16) or 16),
                         keep_window=bool(s.get("keep_window", True)), title=f"{s['exe']} - RAD IDE",
                         debugger=debug)


def program_command(s: dict) -> str:
    args = str(s.get("args", "") or "").strip()
    if s["kind"] == "batch":
        return f"CALL {s['main']}" + (f" {args}" if args else "")
    return B.output_name(s) + (f" {args}" if args else "")


def qbasic_command(s: dict) -> tuple[str, str]:
    """(folder to mount as D:, command) for the user's own QBasic / QuickBASIC, or ("", "")."""
    for key, exe_name in (("qbasic", "QBASIC.EXE"), ("quickbasic", "QB.EXE")):
        exe = toolchain.user_tool(key)
        if exe:
            return str(Path(exe).parent), f"D:\\{Path(exe).name.upper()} /RUN {s['main']}"
    return "", ""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    folder = Path(argv[0]).resolve()
    debug = "--debug" in argv
    from ...model import Project
    project = Project.load(folder)
    s = B.settings_for(project)

    def log(t: str) -> None:
        print(t, flush=True)

    try:
        exe = toolchain.dosbox_exe(download=True, log=log)
    except Exception as e:  # noqa: BLE001
        exe = ""
        log(f"DOSBox-X: {e}")
    if not exe:
        log("*** DOSBox-X is not installed: Tools > Retro Emulators... (or Tools > DOS Toolchains...) downloads the "
            "official portable build, or set the path of your own dosbox-x.exe there.")
        return 1

    run = _run_config(folder, s, debug)
    if "--qbasic" in argv:
        if s["kind"] != "qbasic":
            log("*** Run in QBasic is for QBasic projects.")
            return 1
        qb_dir, cmd = qbasic_command(s)
        if not cmd:
            log("*** Your own QBASIC.EXE / QB.EXE is not configured: Tools > DOS Toolchains... > your own copies "
                "(RAD IDE never downloads Microsoft's QBasic).")
            return 1
        run.mounts.append(("D", qb_dir))
        run.debugger = False
        run.commands = [cmd]
    else:
        if s["kind"] == "batch":
            B.Builder(folder, project, log=log).build()          # GOTO / CALL checks only
        elif "--no-build" not in argv and B.is_stale(folder, s):
            if not B.Builder(folder, project, log=log).build():
                return 1
        if s["kind"] != "batch" and not (folder / B.output_name(s)).is_file():
            log(f"*** {B.output_name(s)} was not built.")
            return 1
        if s["kind"] == "batch":
            for p in B.sources(folder, "batch"):           # COMMAND.COM wants CR LF
                data = p.read_bytes()
                fixed = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                if fixed != data:
                    p.write_bytes(fixed)
        run.commands = [program_command(s)]

    if "--capture" in argv:
        keys = argv[argv.index("--keys") + 1] if "--keys" in argv else ""
        timeout = int(argv[argv.index("--timeout") + 1]) if "--timeout" in argv else 20
        run.path = ["Z:\\BIN", "Z:\\DOS"]
        cmd = run.commands.pop()
        res = dosbox.capture_text(run, folder, cmd, keys=keys, timeout=timeout, log=log)
        log("------ program output ------")
        log(res["stdout"].replace("\r\r\n", "\n").rstrip())
        if res["screen"].strip():
            log("------ screen ------")
            log("\n".join(ln.rstrip() for ln in res["screen"].splitlines()).rstrip())
        if res["graphics"]:
            log(f"------ mode 13h frame saved: {res['graphics']} ------")
        log(f"[DOSBox-X exit code {res['rc']}{', timed out' if res['timed_out'] else ''}]")
        return 0 if not res["timed_out"] else 3

    if debug:
        data = B.read_diagnostics(folder)
        mp = data.get("map") or ""
        log("DOSBox-X debugger: the program stops at its first instruction (DEBUGBOX). F5 runs, F10 / F11 step, "
            "'BP seg:off' sets a breakpoint, Alt+Pause breaks in again.")
        if mp and Path(mp).is_file():
            log(f"Symbol map: {mp}")
            for line in Path(mp).read_text(encoding="utf-8", errors="replace").splitlines()[:60]:
                log("  " + line)
    log(f"Starting {run.commands[-1]} in DOSBox-X (cycles {dosbox.cycles_value(run.cycles)}, {run.machine})")
    t0 = time.time()
    proc = dosbox.launch(run, folder / B.BUILD_DIR, log=log)
    rc = proc.wait()
    log(f"DOSBox-X closed after {time.time() - t0:.1f} s (exit code {rc}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
