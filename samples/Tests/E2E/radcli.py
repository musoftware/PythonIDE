"""Interactive helper for writing journeys: keep one IDE running on the hidden desktop and send commands.

    python radcli.py launch [--exe RADIDE.exe | --source] [--portable-copy DIR]   -> session file
    python radcli.py call <cmd> '{"arg": 1}'
    python radcli.py py "result = win.windowTitle()"
    python radcli.py quit
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from radauto import IDE, REPO, Desktop  # noqa: E402

SESSION = Path(os.environ.get("RADIDE_E2E_SCRATCH") or (Path(__file__).resolve().parent / "_out")) / "session.json"


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "launch":
        exe = None
        if "--exe" in argv:
            exe = argv[argv.index("--exe") + 1]
        cmd = exe if exe else [str(REPO / ".venv" / "Scripts" / "python.exe"), "-m", "radide", "--new-window"]
        with Desktop(os.environ.get("RADIDE_E2E_DESKTOP", "RADIDE_E2E")) as d:
            ide = IDE.launch(cmd, desktop=d.name, scratch=SESSION.parent,
                             env_extra={"RADIDE_SETTINGS_ORG": "RADIDE-TEST-E2E",
                                        "RADIDE_UPDATE_API": "http://127.0.0.1:9/none"},
                             offscreen="--onscreen" not in argv)
        SESSION.parent.mkdir(parents=True, exist_ok=True)
        SESSION.write_text(json.dumps({"pipe": ide.pipe, "token": ide.token, "pid": ide.proc.pid,
                                       "log": str(ide.log_path)}))
        print(json.dumps(ide.call("hello"), indent=1))
        return 0
    s = json.loads(SESSION.read_text())
    ide = IDE(s["pipe"], s["token"])
    if argv[0] == "call":
        args = json.loads(argv[2]) if len(argv) > 2 else {}
        r = ide.request(argv[1], args, async_job="--job" in argv)
    elif argv[0] == "py":
        r = ide.request("exec", {"code": argv[1]})
    elif argv[0] == "quit":
        r = ide.request("quit", {"force": True})
    else:
        print(__doc__)
        return 2
    print(json.dumps(r, indent=1, ensure_ascii=False)[:20000])
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
