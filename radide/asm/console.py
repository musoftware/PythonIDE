"""Run a console program in its own console window and keep the window open at the end.

    python -m radide.asm.console <program.exe> [args...]

Used by Assembly projects whose "asm" settings say ``"console": "external"`` (like Ctrl+F5 in Visual Studio:
"Press any key to continue"). The exit code of the program is returned.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    exe = Path(argv[0])
    args = " ".join(f'"{a}"' for a in argv[1:])
    title = exe.parent.name or exe.stem
    line = (f'title {title} & "{exe}" {args} & set RC=!errorlevel! & echo. & '
            f'echo Program exited with code !RC! & pause & exit !RC!')
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    try:
        p = subprocess.Popen(f'cmd /v:on /c "{line}"', cwd=str(exe.parent), creationflags=flags)
    except OSError as e:
        print(f"cannot start {exe}: {e}", file=sys.stderr)
        return 1
    print(f"{exe.name} runs in its own console window.", flush=True)
    return p.wait()


if __name__ == "__main__":
    sys.exit(main())
