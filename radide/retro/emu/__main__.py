"""Command line of the retro emulators (used by DOS Program projects' F5 and by tests).

    python -m radide.retro.emu status
    python -m radide.retro.emu install <emulator id>          (downloads the pinned official build)
    python -m radide.retro.emu run <rom> [--system S] [--debug] [--symbols FILE] [--emulator ID]
    python -m radide.retro.emu dos <project folder | program> [--wait]

``run`` / ``dos`` wait until the emulator is closed, so the IDE's Run session (and Stop) follow it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _dos(target: str) -> int:
    from .dos import DosSettings, _project_dos_block, build_com_with_nasm, build_command, dos_process, scan_dos_folder
    from .launch import EmuError
    t = Path(target)
    folder = t if t.is_dir() else t.parent
    settings = DosSettings.from_dict(_project_dos_block(folder))
    if t.is_file():
        settings.program = t.name
    if not settings.program:
        settings.program = scan_dos_folder(folder)["start"]
    pre = ""
    prog = settings.program
    src_ext = Path(prog).suffix.lower()
    if src_ext == ".asm" and not settings.build:              # NASM on Windows -> .COM, then run it
        com = build_com_with_nasm(folder / prog, log=print)
        if not com:
            print("*** Build failed")
            return 1
        print(f"Built {Path(com).name} with NASM")
        settings.program = str(Path(prog).with_suffix(".COM"))
    elif src_ext in (".pas", ".c", ".bas", ".asm"):
        cmd, problem = build_command(settings, prog)
        if problem:
            print(f"*** {problem}")
            return 1
        exe = Path(prog).with_suffix(".EXE").name.upper()
        pre = cmd
        if src_ext == ".bas" and "/RUN" in cmd.upper():
            settings.program, pre = "", cmd + ("\nexit" if settings.exit_after else "")
        else:
            settings.program = str(Path(prog).parent / exe) if Path(prog).parent != Path(".") else exe
    if settings.program:
        print(f"DOSBox-X: {settings.program}  (cycles {settings.cycles}, {settings.memsize} MB, {settings.machine}, "
              f"sound {settings.sound})")
    try:
        proc = dos_process(folder, settings=settings, pre=pre)
    except EmuError as e:
        print(f"*** {e}")
        return 1
    proc.start()
    from .launch import tie_to_this_process
    tie_to_this_process(proc)
    try:
        return proc.wait() or 0
    except KeyboardInterrupt:
        proc.stop()
        return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m radide.retro.emu")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    i = sub.add_parser("install")
    i.add_argument("emulator")
    r = sub.add_parser("run")
    r.add_argument("rom")
    r.add_argument("--system")
    r.add_argument("--debug", action="store_true")
    r.add_argument("--symbols", action="append")
    r.add_argument("--emulator")
    r.add_argument("--no-wait", action="store_true")
    d = sub.add_parser("dos")
    d.add_argument("target")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        from .manager import status
        for row in status():
            print(f"{row['id']:9} {row['title']:16} {'OK  ' + row['path'] if row['path'] else 'not installed'}")
        return 0
    if a.cmd == "install":
        from .manager import install
        return 0 if install(a.emulator) else 1
    if a.cmd == "run":
        from .launch import EmuError, run_rom
        try:
            proc = run_rom(a.rom, a.system, a.debug, a.symbols, a.emulator)
        except EmuError as e:
            print(f"*** {e}")
            return 1
        print(f"{proc.emulator}: {' '.join(proc.command)}")
        if proc.gdb_port:
            print(f"GDB stub: localhost:{proc.gdb_port}")
        if proc.monitor_port:
            print(f"VICE binary monitor: localhost:{proc.monitor_port}")
        if a.no_wait:
            return 0
        from .launch import tie_to_this_process
        tie_to_this_process(proc)
        try:
            return proc.wait() or 0
        except KeyboardInterrupt:
            proc.stop()
            return 0
    if a.cmd == "dos":
        return _dos(a.target)
    return 2


if __name__ == "__main__":
    sys.exit(main())
