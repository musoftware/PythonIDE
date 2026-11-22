"""Which VS Code editor commands (commands.json, defined under src/vs/editor/) the bundled Monaco has.

    python radide/vsx/reference/tools/monaco_commands.py

Writes radide/vsx/reference/monaco_commands.json: the ids whose string literal is registered in
radide/web/monaco/vs/editor/editor.main.js (Monaco = the editor of VS Code, the same command ids;
``editor.trigger(source, id, args)`` runs editor actions, editor commands and the core cursor / type commands).
radide/vsx/contrib_keybindings.is_monaco_command reads the file."""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE.parent
REPO = REF.parents[2]
BUNDLE = REPO / "radide" / "web" / "monaco" / "vs" / "editor" / "editor.main.js"
NOT_COMMANDS = {"command"}            # an id in commands.json that is a plain word in the bundle


def main() -> None:
    text = BUNDLE.read_text("utf-8")
    m = re.search(r"Version: ([0-9.]+)", text)
    lits = set(re.findall(r"[\"']([A-Za-z_][\w.:\-]*)[\"']", text))
    cmds = json.loads((REF / "commands.json").read_text("utf-8"))["commands"]
    ids = sorted(c["id"] for c in cmds if any(f.startswith("src/vs/editor/") for f in c.get("files") or [])
                 and c["id"] in lits and not c["id"].startswith("_") and c["id"] not in NOT_COMMANDS)
    out = {"monacoVersion": m.group(1) if m else "", "source": "radide/web/monaco/vs/editor/editor.main.js",
           "commands": ids}
    (REF / "monaco_commands.json").write_text(json.dumps(out, indent=1), "utf-8")
    print(len(ids), "Monaco commands")


if __name__ == "__main__":
    main()
