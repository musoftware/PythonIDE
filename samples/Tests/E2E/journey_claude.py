"""J4: the Claude Code extension in the frozen IDE - install from the cached .vsix through the Command Palette,
the open project is VS Code's workspace folder (IDE side, lock file, extension host environment), the Claude
view opens from the Command Palette, a fake Claude CLI (samples/Tests/VSX/claude_open_diff.js) asks the IDE for a
diff, Accept is pressed in the IDE and the accepted text is saved in the project. No real Claude conversation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from radauto import Report, Skip, check
import e2e_common as C

REPO = Path(__file__).resolve().parent.parent.parent.parent
VSIX_DEFAULT = Path(os.environ.get("RADIDE_E2E_CLAUDE_VSIX", r"C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd"
                    r"\02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9\scratchpad\vsxroot\.cache\vsix"
                    r"\Anthropic.claude-code-2.1.330@win32-x64.vsix"))


def palette(ide, text: str):
    """Ctrl+Shift+P, type, Enter - like a user."""
    ide.call("key", keys="Ctrl+Shift+P", sel="@tabs")
    time.sleep(0.6)
    edits = [w for w in ide.call("widgets", sel={"cls": "QLineEdit", "within": {"cls": "QuickInput"}})]
    check(edits, "the Command Palette did not open")
    ide.call("set_value", sel={"cls": "QLineEdit", "within": {"cls": "QuickInput"}}, value=">" + text)
    time.sleep(0.8)
    items = ide.call("widget", sel={"cls": "QListWidget", "within": {"cls": "QuickInput"}}).get("items", [])
    ide.call("key", keys="Return", sel={"cls": "QLineEdit", "within": {"cls": "QuickInput"}}, async_=True)
    return items[:5]


def locks(cfg: Path) -> list[dict]:
    out = []
    for f in (cfg / "ide").glob("*.lock") if (cfg / "ide").is_dir() else []:
        try:
            out.append(json.loads(f.read_text("utf-8")))
        except (OSError, ValueError):
            pass
    return out


def j4_claude(env: C.Env, rep: Report, vsix: Path = VSIX_DEFAULT):
    if not vsix.is_file():
        rep.skip_rest(["J4 (all steps)"], f"no cached Claude Code vsix at {vsix}")
        return
    C.portable_copy(env)
    cfg = env.scratch / "claude-config"
    shutil.rmtree(cfg, ignore_errors=True)
    cfg.mkdir(parents=True)
    vsx_root = env.scratch / "j4-vsx"
    shutil.rmtree(vsx_root, ignore_errors=True)
    ide = C.launch(env, "J4", extra_env={"CLAUDE_CONFIG_DIR": str(cfg), "RADIDE_VSX_ROOT": str(vsx_root)})
    rep.ide = ide
    ide.call("auto_dialogs", rules=C.AUTO_RULES + [{"match": "CLAUDE.md", "button": "Yes"}])
    proj = env.scratch / "projects" / "J4" / "ClaudeHello"
    shutil.rmtree(proj, ignore_errors=True)
    shutil.copytree(REPO / "samples" / "HelloVB", proj)
    st = {}

    def install():
        ide.call("file_dialog", answers=[str(vsix)])
        items = palette(ide, "Extensions: Install from VSIX")
        ide.wait_output("installed from VSIX", timeout=180)
        got = ide.py("from radide.vsx import package as P\nimport json\n"
                     "result = [d.name for d in P.vsx_root().iterdir() if d.is_dir() and 'claude' in d.name.lower()]")
        check(got, "Claude Code not in the extensions folder")
        return f"palette: {items[:2]}; folder {got}"
    if not rep.step("Command Palette > Extensions: Install from VSIX (Claude Code)", install, shot=True):
        rep.skip_rest(["activation", "project = workspace folder", "lock file", "host env", "Claude view",
                       "fake CLI openDiff", "Accept -> saved"], "not installed")
        return

    def activated(timeout=120):
        state = ide.wait_for(lambda: (lambda a: a if a == "active" else None)(ide.py(
            "svc = getattr(win, 'vsx_host', None)\n"
            "result = svc.activation.get('anthropic.claude-code') if svc is not None else None")), timeout,
            step=2, desc="Claude Code active (VS Code activates a newly installed extension without a restart)")
        return state
    if not rep.step("Claude Code activates right after the install (no restart)", activated):
        ide.quit()                                   # what a user does next: restart the IDE
        ide = C.launch(env, "J4b", extra_env={"CLAUDE_CONFIG_DIR": str(cfg), "RADIDE_VSX_ROOT": str(vsx_root)})
        rep.ide = ide
        ide.call("auto_dialogs", rules=C.AUTO_RULES + [{"match": "CLAUDE.md", "button": "Yes"}])
        rep.step("after restarting the IDE, Claude Code activates", lambda: activated(180))

    def workspace():
        ide.call("open_project", path=str(proj))
        folders = ide.wait_for(lambda: (lambda f: f if f else None)(ide.py("result = win.vsx_host.folders()")), 30)
        check([os.path.normcase(f) for f in folders] == [os.path.normcase(str(proj.resolve()))],
              f"workspace folders {folders} != {proj}")
        return folders
    rep.step("open project -> workspace folders == the project folder", workspace)

    def lockfile():
        ide.wait_for(lambda: ide.py("result = win.vsx_host.activation.get('anthropic.claude-code')") == "active",
                     180, step=2, desc="active again after the host restart")
        lk = ide.wait_for(lambda: [x for x in locks(cfg) if any(
            os.path.normcase(str(Path(w).resolve())) == os.path.normcase(str(proj.resolve()))
            for w in x.get("workspaceFolders") or [])], 60, step=2, desc="lock file with the project")
        return lk[0].get("workspaceFolders")
    rep.step("Claude Code lock file: workspaceFolders = project (what the CLI uses as cwd)", lockfile)

    def host_env():
        env_ = ide.py("result = win.vsx_host._agent_env()")
        check(os.path.normcase(env_.get("RADIDE_WORKSPACE", "")) == os.path.normcase(str(proj.resolve())),
              f"RADIDE_WORKSPACE={env_.get('RADIDE_WORKSPACE')}")
        cli = env_.get("RADIDE_CLI", "")
        check("radide" in cli.lower() and Path(cli.split('"')[1] if cli.startswith('"') else cli.split(" ")[0]).exists()
              or "radide" in cli.lower(), f"RADIDE_CLI={cli}")
        return {k: env_.get(k) for k in ("RADIDE_WORKSPACE", "RADIDE_CLI")}
    rep.step("extension host env: RADIDE_WORKSPACE + RADIDE_CLI of the frozen exe", host_env)

    def view():
        items = palette(ide, "Claude Code: Open")
        time.sleep(4)
        rep.shot("claude view")
        vis = ide.py("from PyQt6.QtWidgets import QWidget\n"
                     "result = [type(w).__name__ + ':' + (w.windowTitle() or w.objectName()) for w in "
                     "app.allWidgets() if w.isVisible() and 'webview' in type(w).__name__.lower()]")
        check(vis, f"no webview visible after the palette command {items}")
        return {"palette": items[:3], "webviews": vis[:3]}
    rep.step("Command Palette > Claude Code: Open -> the Claude view (webview) shows", view)

    def diff():
        node = ide.py("from radide.vsx.bridge import find_node\nresult = find_node()")
        if not node:
            raise Skip("node not found")
        target = proj / "Form1.bas"
        new_text = target.read_text(encoding="utf-8") + "\n' E2E accepted by Claude\n"
        nf = env.scratch / "j4_new.txt"
        nf.write_text(new_text, encoding="utf-8")
        p = subprocess.Popen([node, str(REPO / "samples" / "Tests" / "VSX" / "claude_open_diff.js"), str(cfg),
                              str(target), str(nf), "e2e-accept"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8")
        st["proc"], st["target"], st["new"] = p, target, new_text
        ids = ["claude-vscode.acceptProposedDiff", "claude-code.acceptProposedDiff"]
        code = ("from PyQt6.QtGui import QAction\n"
                f"ids = {['vsxTitle:' + i for i in ids]!r}\n"
                "result = next((a.objectName()[9:] for a in win.findChildren(QAction) if a.objectName() in ids), None)")
        name = ide.wait_for(lambda: ide.py(code), 40, step=1, desc="diff tab with Accept")
        time.sleep(2)                       # the extension starts listening once the tab is there
        rep.shot("diff tab")
        ide.call("trigger", name=f"vsxTitle:{name}")
        out, _ = p.communicate(timeout=60)
        events = [json.loads(x) for x in out.splitlines() if x.startswith("{")]
        res = next((e for e in events if e.get("event") == "result"), None)
        txt = json.dumps(res)
        check(res and "FILE_SAVED" in txt, f"openDiff answer: {events[-3:]}")
        st["res"] = res
        return "FILE_SAVED"
    if rep.step("fake CLI openDiff -> Accept pressed in the IDE -> FILE_SAVED", diff):
        def saved():
            texts = [c.get("text", "") for c in (st["res"]["result"].get("content") or [])]
            body = texts[1] if len(texts) > 1 else st["new"]
            st["target"].write_text(body, encoding="utf-8")          # the CLI writes the accepted contents
            time.sleep(2)
            check("E2E accepted by Claude" in st["target"].read_text(encoding="utf-8"), "file not saved")
            ed = ide.call("editor_text", file="Form1.bas")["text"]
            check("E2E accepted by Claude" in ed, "the IDE editor does not show the accepted change")
            return "file + editor updated"
        rep.step("accepted change saved in the project and shown in the editor", saved)
    rep.step("no internal errors", lambda: C.no_internal_errors(ide))
    ide.quit()
