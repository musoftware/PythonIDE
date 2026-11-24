"""F5 for RAD C# projects in native mode: build, then run the WinForms exe (no Qt, no GUI Bridge host).

    python -m radide.dotnet.native_run <project-folder>

The build output and the program's Console output go to stdout (the IDE's Output window). The exe is put into a
kill-on-close Job Object, so Stop in the IDE (which kills this process) also closes the program.

Debugging (radide/bridgedebug.py, RAD_BRIDGE_DEBUG=1): the build is the same Debug build (with a .pdb); the exe is
started with RAD_WAIT_GO=1, this host prints "@@RADBRIDGE@@pid|<pid>", the IDE attaches netcoredbg, sets the
breakpoints and writes "go" - which is passed on to the program, that only then creates its forms (RadApp.Run).
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

BRIDGE_TAG = "@@RADBRIDGE@@"


def _pump(stream, out) -> None:
    for raw in iter(stream.readline, b""):
        out.write(raw.decode("utf-8", "replace"))
        out.flush()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    folder = Path(os.path.abspath(argv[0]))
    from ..languages import csharp_bridge as C
    if C.build(folder, sys.stdout) != 0:
        return 1
    exe = C.program_file(folder)
    if not exe.is_file():
        print(f"C#: {exe} was not built", flush=True)
        return 1
    debug = os.environ.get("RAD_BRIDGE_DEBUG") == "1"
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1")
    env.pop("RAD_BRIDGE_DEBUG", None)
    if debug:
        env["RAD_WAIT_GO"] = "1"
    proc = subprocess.Popen([str(exe), *argv[1:]], cwd=str(folder), env=env,
                            stdin=subprocess.PIPE if debug else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        from ..web_site.server import adopt_process
        adopt_process(proc)
    except Exception:  # noqa: BLE001 - not on Windows / no job object: the program just is not killed with us
        pass
    t = threading.Thread(target=_pump, args=(proc.stdout, sys.stdout), daemon=True)
    t.start()
    if debug:
        print(f"{BRIDGE_TAG}pid|{proc.pid}", flush=True)
        line = sys.stdin.readline()                     # "go" (or EOF: the IDE is gone)
        try:
            proc.stdin.write((line.strip() or "go").encode() + b"\n")
            proc.stdin.close()
        except OSError:
            pass
    code = proc.wait()
    t.join(2)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
