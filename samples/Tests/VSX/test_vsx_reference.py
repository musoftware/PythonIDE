"""VS Code reference inventories + built-in commands, context keys and contribution points in RAD IDE.

    python samples/Tests/VSX/test_vsx_reference.py <scratch folder> [path to anthropic.claude-code .vsix]

* radide/vsx/reference/*.json (extracted from microsoft/vscode) are present and sane;
* the reference-test extension (engines ^1.100 -> needs the raised API level) runs: view containers in the
  activity bar (left) / panel (bottom) / secondary side bar (right), tree view with view/title buttons and
  overflow, view/item/context menu with viewItem, checkboxes, selection / expand events, reveal(), message /
  description / badge, viewsWelcome, a when-clause view that follows setContext, editor/title buttons on a
  normal editor tab, editor/context submenu, enablement;
* commands: unknown ids reject like VS Code, VS Code ids without a RAD IDE UI resolve, getCommands has the
  built-ins, vscode.executeCompletionItemProvider (trigger char + resolve), prepareCallHierarchy +
  provideIncomingCalls, executeCodeLensProvider with resolve count, copyFilePath, runCommands, goToLocations,
  workbench.action.openSettings with a query, toggleAuxiliaryBar, problems view, workbench.view.extension.*;
* context keys: platform, config.* (extension defaults), view.<id>.visible, activeViewlet, focusedView ...;
* Claude Code (optional): Command Palette entries Open in Side Bar / New Tab / New Window / Focus input /
  New Conversation / Show Logs and the editor/title button, also after an extension-host restart with the
  side bar dock closed (the "Open in Side Bar does nothing" case).
RADIDE-TEST QSettings (cleared before/after), scratch RADIDE_VSX_ROOT, offscreen friendly, widget.grab() only.
Exit code = number of failures."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_reference_test"
CLAUDE_VSIX = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
os.environ["RADIDE_VSX_ROOT"] = str(SCRATCH / "vsxroot")
os.environ["RADIDE_NO_BROWSER"] = "1"
sys.path.insert(0, str(REPO))

RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:300]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:300]}]" if detail else ""), flush=True)


# ---------------------------------------------------------------- 1. the reference inventories
REF = REPO / "radide" / "vsx" / "reference"
cmds = json.loads((REF / "commands.json").read_text("utf-8"))
ids = {c["id"]: c for c in cmds["commands"]}
check(len(ids) > 2500 and cmds["meta"]["version"] and len(cmds["meta"]["commit"]) == 40,
      "commands.json: built-in commands + source commit", (len(ids), cmds["meta"].get("version")))
check(any(k.get("key") == "ctrl+comma" for k in ids.get("workbench.action.openSettings", {}).get("keybinding", [])),
      "commands.json: workbench.action.openSettings has its Ctrl+, keybinding")
api_cmds = {a["id"]: a for a in cmds["apiCommands"]}
ecp = api_cmds.get("vscode.executeCompletionItemProvider", {})
check(len(api_cmds) >= 50 and [a.get("name") for a in ecp.get("args", [])] == ["uri", "position", "triggerCharacter", "itemResolveCount"],
      "commands.json: API commands with their argument names", [a.get("name") for a in ecp.get("args", [])])
api = json.loads((REF / "vscode_api.json").read_text("utf-8"))["items"]
names = {i["name"] for i in api}
check(len(api) > 2700 and "window.createTreeView" in names and "TreeView.reveal" in names, "vscode_api.json: vscode.d.ts surface",
      len(api))
keys = {k["key"]: k for k in json.loads((REF / "context_keys.json").read_text("utf-8"))["contextKeys"]}
check(len(keys) > 1200 and "focus" in (keys.get("editorTextFocus", {}).get("description") or ""),
      "context_keys.json: RawContextKeys with descriptions", len(keys))
cps = json.loads((REF / "contribution_points.json").read_text("utf-8"))
vc = next((c for c in cps["contributionPoints"] if c.get("extensionPoint") == "viewsContainers"), {})
check(set((vc.get("jsonSchema") or {}).get("properties", {})) == {"activitybar", "panel", "secondarySidebar"}
      and any(m["key"] == "view/item/context" for m in cps["menus"]), "contribution_points.json: schemas + menu ids")

from radide import vsx  # noqa: E402

check(vsx.API_LEVEL == "1.147.0", "emulated API level raised to 1.147.0", vsx.API_LEVEL)


# ---------------------------------------------------------------- 2. IDE
def pack(src: Path, out: Path) -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/'
                   'json"/></Types>')
        for f in src.rglob("*"):
            if f.is_file():
                z.write(f, "extension/" + f.relative_to(src).as_posix())
    return out


__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, Qt, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QToolButton  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
QSettings().clear()

from radide.vsx import manager  # noqa: E402

exts = manager.install_vsix_file(pack(HERE / "reference-test", SCRATCH / "radide-test.reference-test-0.0.1.vsix"),
                                 with_dependencies=False)
check(exts and exts[0].enabled, "install reference-test (engines ^1.100.0)", exts and exts[0].id)
if CLAUDE_VSIX and CLAUDE_VSIX.is_file():
    ce = manager.install_vsix_file(CLAUDE_VSIX, with_dependencies=False)
    check(ce and ce[0].id == "anthropic.claude-code", "install Claude Code vsix", ce and ce[0].id)

from radide.app import MainWindow  # noqa: E402

DIALOGS = []
SETTINGS_SEEN = []


def close_dialogs():
    w = QApplication.activeModalWidget()
    if isinstance(w, QMessageBox):
        DIALOGS.append(w.text()[:120])
        w.reject() if w.escapeButton() is None else w.escapeButton().click()
        if w.isVisible():
            w.done(0)
    elif isinstance(w, QDialog):
        from PyQt6.QtWidgets import QTabWidget
        tabs = w.findChild(QTabWidget)
        if w.windowTitle() == "Options" and tabs is not None:
            page = tabs.currentWidget()
            lst = getattr(page, "_vsx_list", None)
            SETTINGS_SEEN.append((tabs.tabText(tabs.currentIndex()), lst.currentItem().text() if lst and lst.currentItem() else ""))
        DIALOGS.append(w.windowTitle()[:120])
        w.reject()


_dlg_timer = QTimer()
_dlg_timer.timeout.connect(close_dialogs)
_dlg_timer.start(300)


def wait(cond, timeout=20.0, step=0.05):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(step)
    app.processEvents()
    return False


def command(cmd, args=None, timeout=15.0):
    box = {}
    svc.execute(cmd, args or [], lambda r: box.setdefault("v", r))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def ref_exec(cmd, *args):
    return command("ref.exec", [cmd, *args]) or {}


def state():
    return command("ref.state") or []


def calls(name):
    return [c.get("data") for c in state() if c.get("name") == name]


ws = SCRATCH / "ws"
ws.mkdir()
sample = ws / "sample.reftest"
sample.write_text("main()\nrefcall\n", "utf-8")

win = MainWindow()
win.resize(1400, 900)
win.show()
svc = getattr(win, "vsx_host", None)
check(svc is not None and hasattr(svc, "views"), "views manager installed")
check(wait(lambda: svc.host.running() and svc.host.init_result is not None, 30), "extension host started")
check(wait(lambda: svc.activation.get("radide-test.reference-test") == "active", 30), "reference-test activated",
      svc.activation)

# ---------------------------------------------------------------- 3. API surface + commands from inside the host
info = command("ref.api") or {}
check(info.get("version") == vsx.API_LEVEL, "vscode.version is the emulated API level", info.get("version"))
check(len(info.get("types") or []) == 15, "API types added through 1.147 exist", info.get("types"))
check(info.get("dataTransfer") == "x" and info.get("kindContains") is True and info.get("timeline") is True,
      "DataTransfer / DocumentDropOrPasteEditKind.contains / timeline + LM provider registration", info)
check((info.get("fileCoverage") or {}).get("covered") == 1 and (info.get("fileCoverage") or {}).get("total") == 2,
      "FileCoverage.fromDetails like VS Code", info.get("fileCoverage"))
check(set(info.get("hasCommands") or []) == {"workbench.action.openSettings", "vscode.executeDocumentSymbolProvider",
                                             "ref.refresh", "workbench.view.explorer"},
      "commands.getCommands() includes VS Code's built-in commands", info.get("hasCommands"))
r = ref_exec("no.such.command.xyz")
check(r.get("error") == "command 'no.such.command.xyz' not found", "unknown command rejects like VS Code", r)
r = ref_exec("notebook.selectKernel")
check(r.get("value") == "<undefined>" and "error" not in r, "VS Code command without a RAD IDE UI resolves undefined", r)
r = ref_exec("runCommands", {"commands": ["ref.titleOverflow", {"command": "ref.itemAction", "args": "x"}]})
check("error" not in r and calls("ref.titleOverflow") and ["x"] in calls("ref.itemAction"), "runCommands runs each command in order",
      r)

ed = win.open_any_file(sample)
check(ed is not None and wait(lambda: getattr(ed, "_ready", True), 30), "sample.reftest opened")
wait(lambda: svc.active_editor() is ed, 10)
uri = {"$uri": sample.resolve().as_uri()}
r = ref_exec("vscode.executeCompletionItemProvider", uri, {"line": 0, "character": 0}, ".", 1)
v = r.get("value") or {}
check([i.get("label") for i in v.get("items", [])] == ["refAlpha", "refBeta"] and v.get("isIncomplete") is True
      and v["items"][0].get("detail") == "resolved refAlpha" and not v["items"][1].get("detail"),
      "executeCompletionItemProvider: trigger character + itemResolveCount", r)
r = ref_exec("vscode.prepareCallHierarchy", uri, {"line": 0, "character": 1})
check(r.get("value") == ["main"], "vscode.prepareCallHierarchy", r)
r = ref_exec("vscode.executeCodeLensProvider", uri, 1)
check(r.get("value") == ["lens:resolved", "lens:unresolved"], "executeCodeLensProvider resolves itemResolveCount lenses", r)
QApplication.clipboard().setText("")
ref_exec("copyFilePath", uri)
check(wait(lambda: QApplication.clipboard().text().lower() == str(sample.resolve()).lower(), 5),
      "copyFilePath copies the file path (Uri.fsPath: lower-case drive like VS Code)",
      QApplication.clipboard().text())
other = ws / "other.reftest"
other.write_text("x\n", "utf-8")
r = ref_exec("editor.action.goToLocations", uri, {"line": 0, "character": 0},
             [{"uri": {"$uri": other.resolve().as_uri()}, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}}}],
             "goto")
check(wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "other.reftest", 10),
      "editor.action.goToLocations opens the location", r)
win.open_any_file(sample)
wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "sample.reftest", 10)

# ---------------------------------------------------------------- 4. view containers + tree view
command("workbench.view.extension.refActivity")
check(wait(lambda: "ref.tree" in svc.views.docks and svc.views.docks["ref.tree"].isVisible(), 15),
      "workbench.view.extension.<container> opens its views")
d_tree = svc.views.docks.get("ref.tree")
check(d_tree is not None and win.dockWidgetArea(d_tree) == Qt.DockWidgetArea.LeftDockWidgetArea,
      "activitybar container -> primary side bar (left)")
tree = svc.views.tree("ref.tree")
check(wait(lambda: tree.topLevelItemCount() == 2, 15), "tree view loads its root",
      [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())] if tree else None)
top = tree.topLevelItem(0) if tree else None
check(top is not None and "2 items" in top.text(0) and not top.icon(0).isNull(), "tree item description + codicon icon",
      top and top.text(0))
pane = svc.views.panes.get("ref.tree")
check(pane is not None and pane.title_row.commands() == ["ref.refresh"], "view/title: 'navigation' entries are buttons",
      pane and pane.title_row.commands())
check(pane is not None and any(b.text() == "..." for b in pane.title_row.findChildren(QToolButton)),
      "view/title: other groups under '...'")
check(pane is not None and any(b.toolTip() == "Collapse All" for b in pane.title_row.findChildren(QToolButton)),
      "showCollapseAll adds Collapse All")
if top is not None:
    top.setExpanded(True)
    check(wait(lambda: top.childCount() == 2, 10), "children load on expand", top.childCount())
    check(wait(lambda: calls("expand"), 5), "onDidExpandElement fires", calls("expand"))
    apple = top.child(0)
    check(apple is not None and apple.checkState(0) == Qt.CheckState.Checked, "checkboxState shown")
    if apple is not None:
        apple.setCheckState(0, Qt.CheckState.Unchecked)
        check(wait(lambda: calls("checkbox"), 5), "onDidChangeCheckboxState fires", calls("checkbox"))
        tree.setCurrentItem(apple)
        check(wait(lambda: ["apple"] in calls("selection"), 5), "onDidChangeSelection fires with elements", calls("selection")[-1:])
        from PyQt6.QtWidgets import QMenu
        from radide.vsx import menus as M
        ctx = svc.views.context_for_view("ref.tree", apple)
        ents = M.entries(svc, "view/item/context", ctx)
        # VS Code order (menuService.ts): named groups first, entries without a group last
        check([e.command for e in ents] == ["ref.disabled", "ref.itemAction"] and ctx.get("viewItem") == "fruit",
              "view/item/context with viewItem == contextValue, VS Code group order", [e.command for e in ents])
        check(bool(ents) and not ents[0].enabled and ents[-1].enabled, "command enablement disables the menu entry")
        svc.views.run_item_command("ref.tree", "ref.itemAction", apple.data(0, Qt.ItemDataRole.UserRole), [])
        check(wait(lambda: ["apple"] in calls("ref.itemAction"), 5), "item command gets the tree element",
              calls("ref.itemAction"))
        apple.setData(0, Qt.ItemDataRole.UserRole + 5, None)
        pane._hover(apple, 0)
        check(wait(lambda: apple.toolTip(0) == "resolved: Apple", 5), "resolveTreeItem fills the tooltip", apple.toolTip(0))
tree.collapseAll()
command("ref.reveal")
check(wait(lambda: tree.currentItem() is not None and tree.currentItem().text(0).startswith("Banana"), 10),
      "TreeView.reveal expands the parents and selects", tree.currentItem() and tree.currentItem().text(0))
command("ref.decorate")
check(wait(lambda: pane.message.isVisible() and pane.message.text() == "Ref message", 5), "TreeView.message")
check("desc" in d_tree.windowTitle() and "(3)" in d_tree.windowTitle(), "TreeView.description + badge in the title",
      d_tree.windowTitle())
svc.views.show_view("ref.empty")
pe = svc.views.panes.get("ref.empty")
check(wait(lambda: pe is not None and pe.welcome.isVisible(), 10), "viewsWelcome while the tree is empty")
from PyQt6.QtWidgets import QPushButton  # noqa: E402

btn = next((b for b in pe.welcome.findChildren(QPushButton) if b.text() == "Add Item"), None) if pe else None
check(btn is not None, "welcome content: command link -> button")
if btn is not None:
    btn.click()
    check(wait(lambda: calls("ref.addItem"), 5), "welcome button runs its command")
command("ref.empty.fill")
check(wait(lambda: pe.tree.isVisible() and pe.tree.topLevelItemCount() == 1, 10), "welcome hides once the tree has items")
command("ref.panelTree.focus")
dp = svc.views.docks.get("ref.panelTree")
check(dp is not None and wait(dp.isVisible, 5) and win.dockWidgetArea(dp) == Qt.DockWidgetArea.BottomDockWidgetArea,
      "panel container -> bottom panel (<view>.focus)")
command("ref.webview.focus")
check(wait(lambda: "ref.webview" in svc.webviews.view_docks and svc.webviews.view_docks["ref.webview"].isVisible(), 20),
      "webview view in the secondary side bar opens")
dw = svc.webviews.view_docks.get("ref.webview")
check(dw is not None and win.dockWidgetArea(dw) == Qt.DockWidgetArea.RightDockWidgetArea,
      "secondarySidebar container -> right side")
command("workbench.action.toggleAuxiliaryBar")
check(wait(lambda: not dw.isVisible(), 5), "workbench.action.toggleAuxiliaryBar hides the secondary side bar")
command("workbench.action.toggleAuxiliaryBar")
check(wait(dw.isVisible, 5), "... and shows it again")
# a view whose when clause follows setContext
command("ref.exec", ["setContext", "ref.showWhenTree", True])
svc.views.show_view("ref.whenTree")
dwt = svc.views.docks.get("ref.whenTree")
check(dwt is not None and wait(dwt.isVisible, 5), "view with a when clause shown")
command("ref.exec", ["setContext", "ref.showWhenTree", False])
check(wait(lambda: not dwt.isVisible(), 5), "view hides when its when clause turns false")
command("ref.exec", ["setContext", "ref.showWhenTree", True])
check(wait(dwt.isVisible, 5), "... and comes back when it turns true")

# ---------------------------------------------------------------- 5. context keys
win.open_any_file(sample)
wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "sample.reftest", 10)
ctx = svc.context_for()
check(ctx.get("isWindows") == (os.name == "nt") and ctx.get("resourceExtname") == ".reftest" and ctx.get("editorLangId") == "reftest"
      and ctx.get("resourceScheme") == "file", "editor / resource / platform context keys",
      {k: ctx.get(k) for k in ("isWindows", "resourceExtname", "editorLangId", "resourceScheme")})
check(ctx.get("config.reftest.flag") is True and ctx.get("config.reftest.mode") == "alpha", "config.* = extension defaults",
      (ctx.get("config.reftest.flag"), ctx.get("config.reftest.mode")))
from radide.vsx import when as W  # noqa: E402

check(W.evaluate("config.reftest.flag && config.reftest.mode == alpha && !config.reftest.missing", ctx),
      "when clause with config.*")
check(ctx.get("view.ref.tree.visible") is True, "view.<id>.visible")
check(ctx.get("activeViewlet") == "workbench.view.extension.refActivity", "activeViewlet = the shown container",
      ctx.get("activeViewlet"))
check(ctx.get("editorHasCompletionItemProvider") is True and ctx.get("editorHasCallHierarchyProvider") is True,
      "editorHas*Provider keys")
check(ctx.get("workspaceFolderCount") is not None and ctx.get("isWorkspaceTrusted") is True and ctx.get("shellExecutionSupported"),
      "workspace keys")
win.activateWindow()
pane.tree.setFocus()
if not wait(lambda: svc._focus.get("view") == "ref.tree", 3):
    from radide.vsx import context_keys as CK      # offscreen: no real focus change - feed the focus handler
    CK._focus_changed(svc, pane.tree)
c2 = svc.context_for()
check(c2.get("focusedView") == "ref.tree" and c2.get("sideBarFocus") is True and c2.get("editorTextFocus") is False,
      "focus keys follow Qt focus (focusedView / sideBarFocus / editorTextFocus)",
      {k: c2.get(k) for k in ("focusedView", "sideBarFocus", "editorTextFocus")})

# ---------------------------------------------------------------- 6. editor/title + editor/context
win.open_any_file(sample)
wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "sample.reftest", 10)
tb = svc.workbench.title_bar
check(tb is not None and wait(lambda: "ref.editorTitle" in tb.commands(), 10), "editor/title on a normal editor tab",
      tb and tb.commands())
check(tb is not None and tb.isVisible(), "editor/title bar visible")
if tb is not None and "ref.editorTitle" in tb.commands():
    tb.run("ref.editorTitle")
    from urllib.parse import unquote
    want = unquote(sample.resolve().as_uri()).lower()
    check(wait(lambda: any(x and unquote(str(x[0])).lower() == want for x in calls("ref.editorTitle")), 5),
          "editor/title command gets the resource URI", calls("ref.editorTitle"))
m = QMenu()
ed2 = svc.active_editor()
ed2.contextMenuAboutToShow.emit(m) if hasattr(ed2, "contextMenuAboutToShow") else svc._context_menu(ed2, m)
subs = [a for a in m.actions() if a.menu() is not None and a.text() == "Ref Submenu"]
check(subs and [x.text() for x in subs[0].menu().actions()] == ["Add Item"], "editor/context submenu",
      [a.text() for a in m.actions()])

# ---------------------------------------------------------------- 7. workbench commands
command("workbench.action.openSettings", ["@ext:radide-test.reference-test"])
check(wait(lambda: SETTINGS_SEEN, 10) and SETTINGS_SEEN[-1][0] == "VS Code Extensions"
      and "reference" in SETTINGS_SEEN[-1][1].lower(), "workbench.action.openSettings(query) opens that extension's settings",
      SETTINGS_SEEN)
command("workbench.actions.view.problems")
de = getattr(win, "dock_errors", None)
check(de is None or wait(de.isVisible, 5), "workbench.actions.view.problems shows the Error List")
command("workbench.action.output.toggleOutput")

# ---------------------------------------------------------------- 8. Claude Code (optional)
if CLAUDE_VSIX and CLAUDE_VSIX.is_file():
    from radide.features import command_palette as cp
    check(wait(lambda: svc.activation.get("anthropic.claude-code") == "active", 90), "Claude Code activated",
          svc.activation.get("anthropic.claude-code"))
    check(not svc.context.get("claude-code:doesNotSupportSecondarySidebar"),
          "Claude Code uses the secondary side bar (API >= 1.106)", svc.context.get("claude-code:doesNotSupportSecondarySidebar"))

    def palette(title):
        c = next((x for x in cp.commands() if x.title == title or x.title.endswith(title)), None)
        if c is None:
            return False
        c.callback()
        return True

    def claude_dock():
        return svc.webviews.view_docks.get("claudeVSCodeSidebarSecondary")

    def visible_claude():
        return [w for w in svc.webviews.items.values() if w.view_type.startswith("claudeVSCode") and w.dock.isVisible()]

    check(palette("Claude Code: Open in Side Bar") and wait(lambda: claude_dock() is not None and claude_dock().isVisible(), 40),
          "palette: Open in Side Bar shows the Claude view")
    d = claude_dock()
    check(d is not None and win.dockWidgetArea(d) == Qt.DockWidgetArea.RightDockWidgetArea, "... in the secondary side bar")
    cw = svc.webviews.items.get(svc.webviews.view_handles.get("claudeVSCodeSidebarSecondary"))
    check(cw is not None and wait(lambda: (cw.web.page() is not None), 5), "Claude view has its page")
    if d is not None:
        d.grab().save(str(SCRATCH / "claude_sidebar.png"))
        # the reported failure: dock closed, then the extension host restarts (reload / install) -> Open in Side Bar
        d.hide()
        svc.restart()
        check(wait(lambda: svc.host.running() and svc.activation.get("anthropic.claude-code") == "active"
                   and "claudeVSCodeSidebarSecondary" in svc.webviews.providers, 90), "host restarted, Claude active again")
        check(palette("Claude Code: Open in Side Bar") and wait(lambda: claude_dock().isVisible(), 40),
              "Open in Side Bar after a host restart with the dock closed shows it again")
    for w in list(svc.webviews.items.values()):
        w.dock.hide()
    n_panels = len([w for w in svc.webviews.items.values() if w.kind == "panel"])
    check(palette("Claude Code: Open in New Tab") and wait(lambda: any(w.kind == "panel" and w.dock.isVisible()
                                                                         for w in svc.webviews.items.values()), 40),
          "palette: Open in New Tab shows a Claude panel")
    check(palette("Claude Code: Open in New Window") and wait(lambda: any(w.kind == "panel" and w.dock.isFloating()
                                                                            and w.dock.isVisible()
                                                                            for w in svc.webviews.items.values()), 40),
          "palette: Open in New Window -> the panel in its own window")
    for title in ("Claude Code: Focus input", "Claude Code: New Conversation"):
        check(palette(title) and wait(lambda: bool(visible_claude()), 20), f"palette: {title.split(': ')[1]} runs with a Claude view shown",
              [(w.view_type, w.dock.isVisible()) for w in svc.webviews.items.values()])
    svc.dock and svc.dock.hide()
    check(palette("Claude Code: Show Logs") and wait(lambda: "Claude" in svc.output.combo.currentText()
                                                     and svc.dock is not None and svc.dock.isVisible(), 15),
          "palette: Show Logs shows Claude's output channel", svc.output.combo.currentText())
    win.open_any_file(sample)
    wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "sample.reftest", 15)
    tb.refresh()
    check(wait(lambda: "claude-vscode.editor.openLast" in tb.commands(), 10), "editor/title: Claude Code button on an editor tab",
          tb.commands())
    btn = tb.findChild(QToolButton, "vsxEditorTitle:claude-vscode.editor.openLast")
    check(btn is not None and not btn.icon().isNull(), "... with the Claude icon")
    for w in list(svc.webviews.items.values()):
        w.dock.hide()
    if btn is not None:
        btn.click()
        check(wait(lambda: bool(visible_claude()), 40), "clicking the editor/title button opens Claude",
              [(w.view_type, w.dock.isVisible()) for w in svc.webviews.items.values()])
    win.grab().save(str(SCRATCH / "claude_ide.png"))
    un = [a for e, a in svc.unsupported if e == "anthropic.claude-code"]
    print("  Claude Code APIs reported unsupported:", un)

win.grab().save(str(SCRATCH / "reference_ide.png"))
if DIALOGS:
    print("  dialogs dismissed:", DIALOGS)
fails = [r for r in RESULTS if not r[0]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed; screenshots in {SCRATCH}", flush=True)
(SCRATCH / "results.json").write_text(json.dumps(RESULTS, indent=1), "utf-8")
QSettings().clear()
try:
    svc.host.stop()                     # os._exit would leave the Node extension host running
except Exception:  # noqa: BLE001
    pass
win.close()
QSettings().clear()
sys.stdout.flush()
os._exit(len(fails))
