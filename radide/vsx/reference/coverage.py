"""Compare the VS Code inventories in this folder with what RAD IDE implements; writes COVERAGE.md and
coverage.json next to this file.

    python radide/vsx/reference/coverage.py [--snapshot before.json]

* vscode.d.ts: ``node api_probe.js`` introspects the real ``vscode`` module of radide/vsx/host (api.js on a
  real Host) - implemented / stub / missing per declaration; interfaces RAD IDE fills in are probed on real
  instances, extension-implemented interfaces count as covered when RAD IDE calls their methods, option /
  data interfaces when RAD IDE reads the member.
* commands: the host's own (main.js switch + host/commands.js), the IDE's (ide_commands.COMMANDS,
  workbench_ui / host_ide special cases, contrib_keybindings.VSCODE_TO_IDE), Monaco (editor commands that the
  bundled Monaco has), accepted no-ops, and the rest (VS Code commands RAD IDE has no UI for: they resolve to
  undefined like VS Code without that part; unknown ids reject).
* context keys: radide/vsx/context_keys.PROVIDED (+ setContext keys work generically).
* contribution points / menus: the table below (what radide/vsx implements).
Priorities come from usage_top_extensions.json (top Open VSX extensions + Claude Code)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
VSX = HERE.parent
REPO = VSX.parents[1]
sys.path.insert(0, str(REPO))

# ---------------------------------------------------------------------------- contribution points
CONTRIB = {
    # point: (status, note)
    "commands": ("implemented", "Command Palette (title, category, enablement, commandPalette when), icons in menus"),
    "menus": ("partial", "see the menu table"),
    "submenus": ("implemented", "nested in editor/context, editor/title, view/title, view/item/context"),
    "keybindings": ("implemented", "Monaco keybindings with when clauses (config.* included) + window shortcuts"),
    "configuration": ("implemented", "Tools > Options > VS Code Extensions; getConfiguration / onDidChangeConfiguration"),
    "configurationDefaults": ("implemented", "language-specific defaults merged into getConfiguration"),
    "views": ("implemented", "tree views (TreePane) and webview views in their container's area"),
    "viewsContainers": ("implemented", "activitybar -> primary side bar, panel -> bottom panel, secondarySidebar -> right; Activity Bar entries in the VS Code layout"),
    "viewsWelcome": ("implemented", "shown while the tree view is empty; buttons for command links"),
    "languages": ("implemented", ""), "grammars": ("implemented", ""), "snippets": ("implemented", ""),
    "themes": ("implemented", ""), "iconThemes": ("implemented", ""), "productIconThemes": ("missing", "RAD IDE uses its own icons"),
    "jsonValidation": ("missing", "no JSON schema validation in the editor"),
    "debuggers": ("implemented", "debug adapters through the host"), "breakpoints": ("implemented", ""),
    "walkthroughs": ("partial", "opened as a Markdown page (no Welcome page)"),
    "customEditors": ("partial", "webview custom editors in a dock (not an editor tab)"),
    "taskDefinitions": ("partial", "task providers run (workbench.action.tasks.runTask); no tasks.json schema"),
    "problemMatchers": ("missing", ""), "problemPatterns": ("missing", ""),
    "icons": ("partial", "codicons render; contributed icon fonts are not loaded"),
    "colors": ("partial", "theme colours of extensions are not registered"),
    "semanticTokenTypes": ("missing", ""), "semanticTokenModifiers": ("missing", ""), "semanticTokenScopes": ("missing", ""),
    "notebooks": ("partial", "serializers run (executeDataToNotebook / NotebookToData); no notebook editor"),
    "notebookRenderer": ("missing", "no notebook editor"), "notebookPreload": ("missing", "no notebook editor"),
    "localizations": ("missing", "RAD IDE has its own UI translation"),
    "authentication": ("implemented", "authentication.registerAuthenticationProvider / getSession"),
    "resourceLabelFormatters": ("missing", ""), "statusBarItems": ("missing", "declarative status bar items"),
    "terminal": ("implemented", "terminal profiles (Extensions > New Extension Terminal from Profile...)"),
    "terminalQuickFixes": ("missing", ""), "chatParticipants": ("missing", "no chat UI"), "languageModelTools": ("missing", "no chat UI"),
    "languageModelToolSets": ("missing", "no chat UI"), "languageModelChatProviders": ("missing", "no chat UI"),
    "mcpServerDefinitionProviders": ("missing", "no chat UI"), "chatSessions": ("missing", "no chat UI"),
    "chatContext": ("missing", "no chat UI"), "chatViewsWelcome": ("missing", "no chat UI"), "chatOutputRenderers": ("missing", "no chat UI"),
    "chatPlugins": ("missing", "no chat UI"), "chatResources": ("missing", "no chat UI"), "remoteCodingAgents": ("missing", "no chat UI"),
    "debugVisualizers": ("missing", ""), "css": ("missing", ""), "continueEditSession": ("missing", ""),
    "remoteHelp": ("missing", ""), "speechProviders": ("missing", ""), "linkPresentationProviders": ("missing", ""),
    "jsonValidationRegistry": ("missing", ""),
}
MENUS = {
    "commandPalette": ("implemented", "when clauses hide entries"),
    "editor/title": ("implemented", "buttons ('navigation') + '...' on every editor tab and on diff tabs; the command gets the resource URI"),
    "editor/context": ("implemented", "groups, separators, submenus; the command gets the resource URI"),
    "view/title": ("implemented", "title row of tree / webview views"),
    "view/item/context": ("implemented", "viewItem = contextValue; (element) or (element, selection[]) with canSelectMany"),
    "editor/title/run": ("missing", ""), "editor/title/context": ("missing", ""), "explorer/context": ("missing", "Solution Explorer has its own menu"),
    "webview/context": ("missing", "the webview's own context menu"), "scm/title": ("missing", "no SCM view for extensions"),
    "terminal/context": ("missing", ""), "debug/toolBar": ("missing", ""), "notebook/toolbar": ("missing", "no notebook editor"),
}


# the state before radide/vsx/reference existed (for `--baseline`: before/after numbers in COVERAGE.md)
BASELINE_CONTRIB = {"views": ("partial", "tree views in a right dock, webview views"), "viewsContainers": ("missing", ""),
                    "viewsWelcome": ("missing", ""), "submenus": ("missing", ""), "menus": ("partial", "")}
BASELINE_MENUS = {"view/title": ("missing", ""), "view/item/context": ("missing", ""),
                  "editor/title": ("partial", "diff tabs only")}

# ---------------------------------------------------------------------------- RAD IDE command sets
def host_commands() -> tuple[set, set]:
    main = (VSX / "host" / "main.js").read_text("utf-8")
    sw = main[main.index("async _builtinCommand(id, args) {"):main.index("getCommands(filterInternal)")]
    cases = set(re.findall(r"case '([^']+)'", sw))
    cj = (VSX / "host" / "commands.js").read_text("utf-8") if (VSX / "host" / "commands.js").is_file() else ""
    table = set(re.findall(r"^\s*'([\w.:\-]+)':\s*(?:async|nothing|\(a\))", cj, re.M))
    noop_cases = set()
    m = re.search(r"// one editor group, one window:(.*?)await ide\(id, args\);", sw, re.S)
    if m:
        noop_cases = set(re.findall(r"case '([^']+)'", m.group(1)))
    nothing = set(re.findall(r"'([\w.:\-]+)':\s*nothing\(", cj))
    return (cases | table) - noop_cases - nothing, noop_cases | nothing


def _literals_in(path: Path, start: str, end: str) -> set:
    t = path.read_text("utf-8")
    if start not in t:
        return set()
    body = t[t.index(start):]
    body = body[:body.index(end)] if end in body else body
    return set(re.findall(r'"((?:workbench|vscode|editor|revealInExplorer|revealFileInOS)[\w.:\-]*)"', body))


def ide_commands() -> tuple[set, set]:
    from radide.vsx import contrib_keybindings as KB
    try:
        from radide.vsx import ide_commands as IC
    except ImportError:            # a baseline copy without ide_commands.py: what the old code routed
        old = _literals_in(VSX / "workbench_ui.py", "def exec_command", "def _focus_view")
        old |= _literals_in(VSX / "host_ide.py", "def exec_ide", "H[\"commands/executeIde\"]")
        old -= {"workbench.action.terminal."}
        noop = {"workbench.action.lockEditorGroup", "workbench.action.unlockEditorGroup",
                "workbench.action.moveEditorToNewWindow", "workbench.action.copyEditorToNewWindow",
                "workbench.action.splitEditor", "workbench.action.splitEditorRight",
                "workbench.action.moveEditorToNextGroup", "workbench.action.moveEditorToPreviousGroup",
                "workbench.action.newGroupRight", "workbench.action.focusSecondEditorGroup",
                "workbench.action.joinAllGroups", "workbench.action.evenEditorWidths",
                "workbench.action.toggleMaximizeEditorGroup", "workbench.action.reopenClosedEditor"}
        return (old - noop) | {k for k, v in KB.VSCODE_TO_IDE.items() if v != "monaco"}, noop

    handled = set(IC.COMMANDS) | {k for k, v in KB.VSCODE_TO_IDE.items() if v != "monaco"}
    handled |= {"vscode.openFolder", "revealFileInOS", "workbench.action.focusFirstEditorGroup",
                "workbench.action.focusActiveEditorGroup", "workbench.action.reloadWindow",
                "workbench.action.output.toggleOutput", "workbench.panel.output.focus",
                "workbench.action.terminal.selectAll", "workbench.action.terminal.copySelection",
                "workbench.action.terminal.clearSelection", "workbench.action.terminal.clear"}
    return handled, set(IC.NOOP)


def command_status(cid: str, files: list[str], host: set, host_noop: set, ide: set, ide_noop: set) -> str:
    from radide.vsx import contrib_keybindings as KB
    if cid in host or cid in ide:
        return "implemented"
    if cid in host_noop or cid in ide_noop:
        return "accepted (no-op)"
    if KB.is_monaco_command(cid) and any(f.startswith("src/vs/editor/") for f in files):
        return "implemented (Monaco)"
    if cid.startswith("_"):
        return "internal"
    return "no UI (resolves undefined)"


# ---------------------------------------------------------------------------- main
def api_status() -> dict:
    out = subprocess.run(["node", str(HERE / "api_probe.js"), str(HERE / "vscode_api.json")], capture_output=True,
                         text=True, stdin=subprocess.DEVNULL, encoding="utf-8", timeout=120)
    return json.loads(out.stdout)


def main(argv):
    if "--baseline" in argv:
        CONTRIB.update(BASELINE_CONTRIB)
        MENUS.update(BASELINE_MENUS)
    cmds = json.loads((HERE / "commands.json").read_text("utf-8"))
    keys = json.loads((HERE / "context_keys.json").read_text("utf-8"))
    cps = json.loads((HERE / "contribution_points.json").read_text("utf-8"))
    api = json.loads((HERE / "vscode_api.json").read_text("utf-8"))
    usage = json.loads((HERE / "usage_top_extensions.json").read_text("utf-8"))
    meta = cmds["meta"]
    # ------------------------------------------------------------------ commands
    host, host_noop = host_commands()
    ide, ide_noop = ide_commands()
    cmd_use = dict(usage["commands"])
    for c, n in usage.get("keybindingCommands", []):
        cmd_use[c] = cmd_use.get(c, 0) + n
    cstat = {}
    for c in cmds["commands"]:
        cstat[c["id"]] = command_status(c["id"], c.get("files") or [], host, host_noop, ide, ide_noop)
    # ------------------------------------------------------------------ API
    ast = api_status()
    items = {i["name"]: i for i in api["items"]}
    # ------------------------------------------------------------------ context keys
    try:
        from radide.vsx import context_keys as CK
        provided = set(CK.PROVIDED)
    except ImportError:            # baseline: the keys the old host_ide.context_for set
        t = (VSX / "host_ide.py").read_text("utf-8")
        body = t[t.index("def context_for"):t.index("def _contributed_commands")]
        provided = set(re.findall(r'"([A-Za-z][\w.]*)":', body)) | set(re.findall(r'ctx\["([\w.]+)"\]', body))
    kstat = {k["key"]: ("implemented" if k["key"] in provided else "missing") for k in keys["contextKeys"]}
    when_use = dict(usage["whenKeys"])
    # ------------------------------------------------------------------ summary numbers
    def cnt(d, ok):
        return sum(1 for v in d.values() if v in ok)
    api_items = {n: s for n, s in ast.items() if s not in ("type", "n/a")}
    api_ok = {"implemented", "honoured", "consumed", "extension-implemented", "data"}
    summary = {
        "commands": {"total": len(cstat), **Counter(cstat.values())},
        "commandsUsed": {"total": sum(1 for c in cmd_use if c in cstat),
                         "implemented": sum(1 for c in cmd_use if cstat.get(c, "").startswith("implemented"))},
        "apiCommands": {"total": len(cmds["apiCommands"]),
                        "implemented": sum(1 for a in cmds["apiCommands"] if cstat.get(a["id"], "").startswith("implemented"))},
        "api": {"total": len(api_items), **Counter(api_items.values())},
        "apiCovered": cnt(api_items, api_ok),
        "contextKeys": {"total": len(kstat), "implemented": cnt(kstat, {"implemented"})},
        "contextKeysUsed": {"total": sum(1 for k in when_use if k in kstat),
                            "implemented": sum(1 for k in when_use if kstat.get(k) == "implemented")},
        "contributionPoints": {"total": len({c["extensionPoint"] for c in cps["contributionPoints"] if c.get("extensionPoint")}),
                               **Counter(CONTRIB.get(c["extensionPoint"], ("missing", ""))[0]
                                         for c in cps["contributionPoints"] if c.get("extensionPoint"))},
        "menus": {"total": len(cps["menus"]), **Counter(MENUS.get(m["key"], ("missing", ""))[0] for m in cps["menus"])},
    }
    snap = None
    if "--snapshot" in argv:
        snap = Path(argv[argv.index("--snapshot") + 1])
    before = json.loads(snap.read_text("utf-8")) if snap and snap.is_file() else None
    if "--summary-to" in argv:
        Path(argv[argv.index("--summary-to") + 1]).write_text(json.dumps(summary, indent=1), "utf-8")
        print(json.dumps(summary, indent=1))
        return
    data = {"meta": meta, "summary": summary, "commands": cstat, "api": ast, "contextKeys": kstat}
    (HERE / "coverage.json").write_text(json.dumps(data, indent=1, sort_keys=True), "utf-8")
    write_md(meta, summary, before, cmds, cstat, cmd_use, ast, items, usage, keys, kstat, when_use, cps)
    print(json.dumps(summary, indent=1))


def _pct(a, b):
    return f"{(100.0 * a / b):.1f}%" if b else "-"


def write_md(meta, summary, before, cmds, cstat, cmd_use, ast, items, usage, keys, kstat, when_use, cps):
    L = []
    w = L.append
    w("# VS Code API coverage of RAD IDE's extension host")
    w("")
    w(f"Generated by `radide/vsx/reference/coverage.py` from the inventories of microsoft/vscode "
      f"`{meta['commit'][:12]}` (version {meta['version']}, MIT) against `radide/vsx` "
      f"(emulated API level: `radide.vsx.API_LEVEL`). Usage counts: {len(usage['extensions'])} most downloaded "
      f"Open VSX extensions (package.json), {len(usage['bundles'])} of their bundles + Claude Code's extension.js.")
    w("")
    s = summary
    w("## Summary")
    w("")
    w("| Inventory | Items | Covered | Notes |")
    w("|---|---|---|---|")
    c = s["commands"]
    impl = c.get("implemented", 0) + c.get("implemented (Monaco)", 0)
    w(f"| Built-in commands | {c['total']} | {impl} implemented ({_pct(impl, c['total'])}), "
      f"{c.get('accepted (no-op)', 0)} accepted no-ops | {c.get('no UI (resolves undefined)', 0)} have no RAD IDE UI "
      f"(resolve `undefined`), {c.get('internal', 0)} internal `_` ids |")
    w(f"| Commands the scanned extensions call / bind | {s['commandsUsed']['total']} | {s['commandsUsed']['implemented']} "
      f"({_pct(s['commandsUsed']['implemented'], s['commandsUsed']['total'])}) | |")
    w(f"| API commands (extHostApiCommands.ts) | {s['apiCommands']['total']} | {s['apiCommands']['implemented']} | |")
    a = s["api"]
    w(f"| vscode.d.ts declarations | {a['total']} | {s['apiCovered']} ({_pct(s['apiCovered'], a['total'])}) | "
      f"implemented {a.get('implemented', 0)}, honoured options {a.get('honoured', 0)}, consumed provider methods "
      f"{a.get('consumed', 0)}, stubs {a.get('stub', 0)}, missing {a.get('missing', 0)}, ignored options "
      f"{a.get('ignored', 0)}, provider methods never called {a.get('not-consumed', 0)} |")
    k = s["contextKeys"]
    w(f"| Context keys (RawContextKey) | {k['total']} | {k['implemented']} ({_pct(k['implemented'], k['total'])}) | "
      f"keys used by the scanned extensions: {s['contextKeysUsed']['implemented']}/{s['contextKeysUsed']['total']}; "
      "`setContext` keys and `config.*` work for any name |")
    cp = s["contributionPoints"]
    w(f"| Contribution points | {cp['total']} | implemented {cp.get('implemented', 0)}, partial {cp.get('partial', 0)} | "
      f"missing {cp.get('missing', 0)} |")
    m = s["menus"]
    w(f"| Menu ids | {m['total']} | implemented {m.get('implemented', 0)} | the 5 menus that cover most extension use |")
    if before:
        b = before
        w("")
        w("### Before / after this change")
        w("")
        w("| | before | after |")
        w("|---|---|---|")
        bi = b["commands"].get("implemented", 0) + b["commands"].get("implemented (Monaco)", 0)
        w(f"| commands implemented | {bi} / {b['commands']['total']} | {impl} / {c['total']} |")
        w(f"| commands used by extensions implemented | {b['commandsUsed']['implemented']} / {b['commandsUsed']['total']} | "
          f"{s['commandsUsed']['implemented']} / {s['commandsUsed']['total']} |")
        w(f"| API commands | {b['apiCommands']['implemented']} / {b['apiCommands']['total']} | "
          f"{s['apiCommands']['implemented']} / {s['apiCommands']['total']} |")
        w(f"| vscode.d.ts covered | {b['apiCovered']} / {b['api']['total']} (missing {b['api'].get('missing', 0)}, "
          f"stubs {b['api'].get('stub', 0)}) | {s['apiCovered']} / {a['total']} (missing {a.get('missing', 0)}, "
          f"stubs {a.get('stub', 0)}) |")
        w(f"| context keys | {b['contextKeys']['implemented']} / {b['contextKeys']['total']} | "
          f"{k['implemented']} / {k['total']} |")
        w(f"| context keys used by extensions | {b['contextKeysUsed']['implemented']} / {b['contextKeysUsed']['total']} | "
          f"{s['contextKeysUsed']['implemented']} / {s['contextKeysUsed']['total']} |")
        w(f"| contribution points (implemented + partial) | {b['contributionPoints'].get('implemented', 0)} + "
          f"{b['contributionPoints'].get('partial', 0)} | {cp.get('implemented', 0)} + {cp.get('partial', 0)} |")
        w(f"| menu ids | {b['menus'].get('implemented', 0)} | {m.get('implemented', 0)} |")
    w("")
    w("Status words: *implemented* - does what VS Code does; *implemented (Monaco)* - an editor command the bundled "
      "Monaco runs on the active editor; *accepted (no-op)* - RAD IDE has no such part (second editor group, Test "
      "Explorer, notebook editor ...), the command resolves like VS Code would with that part unavailable; *no UI "
      "(resolves undefined)* - a VS Code command RAD IDE has no UI for: `executeCommand` resolves `undefined` (logged "
      "once to the Extension Host output) instead of rejecting, ids VS Code does not know reject with "
      "`command 'x' not found`. API: *honoured* - an option / data member RAD IDE reads; *consumed* - a provider "
      "method RAD IDE calls; *stub* - present with VS Code's type but inert (events that cannot fire in RAD IDE, "
      "e.g. `window.onDidChangeTextEditorViewColumn` with one editor group, `env.onDidChangeShell`); *ignored* / "
      "*not-consumed* - accepted but without effect.")
    w("")
    w("### What cannot exist in RAD IDE (behaves like VS Code without that UI)")
    w("")
    for line in (
        "Notebook editor / interactive window: serializers, controllers and `executeDataToNotebook` work; "
        "`showNotebookDocument` returns an editor object, notebook commands and events are inert.",
        "Chat / language models / MCP: `chat.createChatParticipant`, `lm.registerTool`, "
        "`lm.registerLanguageModelChatProvider`, MCP definition providers register; nothing calls them; "
        "`lm.selectChatModels` resolves `[]`.",
        "Test Explorer, SCM view, comments UI, Timeline view: controllers / providers are created with VS Code's "
        "shapes (`tests.createTestController`, `scm.createSourceControl`, `comments.createCommentController`, "
        "`workspace.registerTimelineProvider`) but are not shown.",
        "Editor groups / auxiliary windows: one editor group; split / move-to-group commands are accepted no-ops; "
        "`workbench.action.moveEditorToNewWindow` floats a webview panel as its own window.",
        "Port forwarding, remote, workspace trust: `asExternalUri` returns the URI, every folder is trusted, "
        "`registerPortAttributesProvider` registers.",
        "Menus without a RAD IDE surface (scm/*, testing/*, notebook/*, comments/*, terminal/context, "
        "webview/context, explorer/context, debug/*): ignored.",
    ):
        w("* " + line)
    # ------------------------------------------------------------------ commands by usage
    w("")
    w("## Commands, by how many scanned extensions use them")
    w("")
    w("| Command | Extensions | Status |")
    w("|---|---|---|")
    for cid, n in sorted(cmd_use.items(), key=lambda x: (-x[1], x[0])):
        if cid in cstat:
            w(f"| `{cid}` | {n} | {cstat[cid]} |")
    # ------------------------------------------------------------------ API by usage
    w("")
    w("## API members, by how many scanned bundles use them")
    w("")
    w("| Member | Bundles | Status |")
    w("|---|---|---|")
    for name, n in usage["api"]:
        if name in ast:
            w(f"| `{name}` | {n} | {ast[name]} |")
    for name, n in usage["classes"]:
        if name in ast and n >= 2:
            w(f"| `new {name}` | {n} | {ast[name]} |")
    # ------------------------------------------------------------------ context keys by usage
    w("")
    w("## Built-in context keys, by how often `when` clauses of the scanned extensions use them")
    w("")
    w("| Key | Uses | Status | Meaning |")
    w("|---|---|---|---|")
    kd = {x["key"]: x for x in keys["contextKeys"]}
    for key, n in sorted(when_use.items(), key=lambda x: -x[1]):
        if key in kstat:
            w(f"| `{key}` | {n} | {kstat[key]} | {(kd[key].get('description') or '').replace('|', '/')[:120]} |")
    w("| `config.*` | " + str(when_use.get("config.*", 0)) + " | implemented | any setting (extension defaults included) |")
    # ------------------------------------------------------------------ contribution points + menus
    w("")
    w("## Contribution points")
    w("")
    w("| Point | Extensions (of " + str(len(usage["extensions"])) + ") | Status | Note |")
    w("|---|---|---|---|")
    cu = dict(usage["contributes"])
    for p in sorted({c["extensionPoint"] for c in cps["contributionPoints"] if c.get("extensionPoint")} | set(CONTRIB),
                    key=lambda x: -cu.get(x, 0)):
        st, note = CONTRIB.get(p, ("missing", ""))
        w(f"| `{p}` | {cu.get(p, 0)} | {st} | {note} |")
    w("")
    w("| Menu id | Extensions | Status | Note |")
    w("|---|---|---|---|")
    mu = dict(usage["menus"])
    for mm in sorted(cps["menus"], key=lambda x: -mu.get(x["key"], 0)):
        st, note = MENUS.get(mm["key"], ("missing", ""))
        w(f"| `{mm['key']}` | {mu.get(mm['key'], 0)} | {st} | {note} |")
    w("")
    vc = dict(usage["viewsContainers"])
    w(f"viewsContainers locations used: activitybar {vc.get('activitybar', 0)}, panel {vc.get('panel', 0)}, "
      f"secondarySidebar {vc.get('secondarySidebar', 0)} - all three are implemented.")
    # ------------------------------------------------------------------ every item
    w("")
    w("## Every item")
    w("")
    w("The complete per-item status is in `coverage.json` (commands, API declarations, context keys). "
      "Grouped lists:")
    groups: dict[str, list] = {}
    for cid, st in cstat.items():
        groups.setdefault(st, []).append(cid)
    for st in sorted(groups):
        w("")
        w(f"<details><summary>Commands: {st} ({len(groups[st])})</summary>")
        w("")
        w(", ".join(f"`{x}`" for x in sorted(groups[st])))
        w("")
        w("</details>")
    ag: dict[str, list] = {}
    for n, st in ast.items():
        ag.setdefault(st, []).append(n)
    for st in sorted(ag):
        if st in ("implemented", "honoured", "type", "n/a"):
            w("")
            w(f"<details><summary>API: {st} ({len(ag[st])})</summary>")
            w("")
            w(", ".join(f"`{x}`" for x in sorted(ag[st])[:4000]))
            w("")
            w("</details>")
            continue
        w("")
        w(f"<details open><summary>API: {st} ({len(ag[st])})</summary>")
        w("")
        w(", ".join(f"`{x}`" for x in sorted(ag[st])))
        w("")
        w("</details>")
    kg: dict[str, list] = {}
    for kk, st in kstat.items():
        kg.setdefault(st, []).append(kk)
    for st in sorted(kg):
        w("")
        w(f"<details><summary>Context keys: {st} ({len(kg[st])})</summary>")
        w("")
        w(", ".join(f"`{x}`" for x in sorted(kg[st])))
        w("")
        w("</details>")
    (HERE / "COVERAGE.md").write_text("\n".join(L) + "\n", "utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
