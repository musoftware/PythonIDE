"""Built-in context keys for ``when`` clauses (menus, keybindings, views, commandPalette, enablement).

Names and meanings follow the RawContextKey definitions of microsoft/vscode (radide/vsx/reference/
context_keys.json). ``compute(svc, editor)`` returns a ``Context``: a dict that also answers
``config.<setting>`` (the effective value of any setting, extension defaults included) and
``view.<viewId>.visible`` lazily. Keys extensions set with ``setContext`` are merged in (svc.context).

Focus keys come from Qt's focus: ``install(svc)`` follows QApplication.focusChanged and remembers which
part of the window last had keyboard focus (pop-ups such as the Command Palette or a menu do not count, the
way VS Code evaluates a command's when clause against the part it was invoked from).
``PROVIDED`` lists the keys this module computes (for radide/vsx/reference/coverage.py)."""
from __future__ import annotations

import os
from pathlib import Path

PROVIDED = {
    # platform / window
    "isWindows", "isLinux", "isMac", "isWeb", "isIOS", "isMobile", "isMacNative", "isDevelopment", "remoteName",
    "virtualWorkspace", "shellExecutionSupported", "processExecutionSupported", "extensionHostKind",
    "isWorkspaceTrusted", "workspaceFolderCount", "workbenchState", "isSessionsWindow", "isAuxiliaryWindow",
    "isFullscreen", "isCloud9", "inputFocus", "textInputFocus", "embedderIdentifier", "notebookEditorFocused",
    "notebookType", "isInDiffEditor", "isInEmbeddedEditor", "activeEditorGroupEmpty", "multipleEditorGroups",
    "editorIsOpen", "activeEditor", "activeEditorIsDirty", "activeEditorIsReadonly", "activeEditorIsNotPreview",
    "activeEditorIsPinned", "activeEditorAvailableEditorIds", "activeEditorCanSplitInGroup", "activeCustomEditorId",
    "activeWebviewPanelId", "dirtyWorkingCopies", "groupEditorsCount", "textCompareEditorVisible",
    "textCompareEditorActive", "sideBySideEditorActive", "editorPartMultipleEditorGroups",
    # editor
    "editorFocus", "editorTextFocus", "editorHasSelection", "editorHasMultipleSelections", "editorReadonly",
    "editorLangId", "editorTabMovesFocus", "editorHasCompletionItemProvider", "editorHasCodeActionsProvider",
    "editorHasCodeLensProvider", "editorHasDefinitionProvider", "editorHasDeclarationProvider",
    "editorHasImplementationProvider", "editorHasTypeDefinitionProvider", "editorHasHoverProvider",
    "editorHasDocumentHighlightProvider", "editorHasDocumentSymbolProvider", "editorHasReferenceProvider",
    "editorHasRenameProvider", "editorHasSignatureHelpProvider", "editorHasInlayHintsProvider",
    "editorHasDocumentFormattingProvider", "editorHasDocumentSelectionFormattingProvider",
    "editorHasMultipleDocumentFormattingProvider", "editorHasCallHierarchyProvider", "editorHasTypeHierarchyProvider",
    "suggestWidgetVisible", "inSnippetMode", "findWidgetVisible",
    # resource (ResourceContextKey)
    "resource", "resourceScheme", "resourceFilename", "resourceDirname", "resourcePath", "resourceLangId",
    "resourceExtname", "resourceSet", "isFileSystemResource", "resourceIsFolder",
    # parts / views
    "sideBarVisible", "sideBarFocus", "panelVisible", "panelFocus", "panelPosition", "panelAlignment",
    "panelMaximized", "auxiliaryBarVisible", "auxiliaryBarFocus", "activeViewlet", "activePanel", "activeAuxiliary",
    "focusedView", "view", "viewItem", "listFocus", "listMultiSelection", "treeElementCanCollapse",
    "treeElementCanExpand", "terminalFocus", "terminalIsOpen", "terminalCount", "webviewFindWidgetVisible",
    "webviewId", "webview", "webviewItem", "explorerViewletVisible", "explorerViewletFocus",
    "explorerResourceIsFolder", "explorerResourceIsRoot", "explorerResourceReadonly", "filesExplorerFocus",
    # debug
    "inDebugMode", "debugState", "debugType", "inDebugRepl", "debugConfigurationType", "debuggersAvailable",
    # editor widget / workbench states RAD IDE derives or never has (VS Code's value in that situation)
    "foldingEnabled", "acceptSuggestionOnEnter", "remoteConnectionState", "inDiffEditor", "isInDiffRightEditor",
    "isInDiffLeftEditor", "terminalEditorActive", "inQuickOpen", "parameterHintsVisible", "searchViewletVisible",
    "canNavigateBack", "canNavigateForward", "foldersViewVisible", "listSupportsFind", "hasWordHighlights",
    "inCompositeEditor", "editorHoverVisible", "renameInputVisible", "listDoubleSelection", "inOutput",
    "terminalTabsFocus", "isMergeResultEditor", "inChat", "inlineChatFocused", "terminalTextSelectedInFocused",
    "taskCommandsRegistered", "inlineSuggestionVisible", "findInputFocussed", "replaceInputFocussed",
    "explorerResourceMoveableToTrash", "notebookKernel", "scmProvider", "commentController", "callStackItemType",
    "notebookCellType", "notebookCellListFocused", "notebookOutputInputFocused", "comment", "commentThread",
    "chatSessionType", "testId", "controllerId", "isCompositeNotebook", "notebookKernelCount",
    "notebookCellExecuting", "notebookEditable", "inlineEditIsVisible", "commentIsEmpty", "commentingEnabled",
    # dynamic
    "config.*", "view.<viewId>.visible",
}

PROVIDER_KEYS = {
    "completion": "editorHasCompletionItemProvider", "codeAction": "editorHasCodeActionsProvider",
    "codeLens": "editorHasCodeLensProvider", "definition": "editorHasDefinitionProvider",
    "declaration": "editorHasDeclarationProvider", "implementation": "editorHasImplementationProvider",
    "typeDefinition": "editorHasTypeDefinitionProvider", "hover": "editorHasHoverProvider",
    "documentHighlight": "editorHasDocumentHighlightProvider", "documentSymbol": "editorHasDocumentSymbolProvider",
    "references": "editorHasReferenceProvider", "rename": "editorHasRenameProvider",
    "signatureHelp": "editorHasSignatureHelpProvider", "inlayHint": "editorHasInlayHintsProvider",
    "formatting": "editorHasDocumentFormattingProvider", "rangeFormatting": "editorHasDocumentSelectionFormattingProvider",
    "callHierarchy": "editorHasCallHierarchyProvider", "typeHierarchy": "editorHasTypeHierarchyProvider",
}


class Context(dict):
    """dict of context keys that also resolves ``config.*`` and ``view.<id>.visible`` on demand."""

    def __init__(self, *a, svc=None, **kw):
        super().__init__(*a, **kw)
        self._svc = svc
        self._cfg = None

    def get(self, key, default=None):
        if dict.__contains__(self, key):
            return dict.__getitem__(self, key)
        if isinstance(key, str) and key.startswith("config."):
            return self._config(key[7:], default)
        if isinstance(key, str) and key.startswith("view.") and key.endswith(".visible") and self._svc is not None:
            vid = key[5:-8]
            d = self._svc.views.docks.get(vid) or self._svc.webviews.view_docks.get(vid)
            return bool(d is not None and d.isVisible())
        return default

    def __contains__(self, key):
        return dict.__contains__(self, key) or (isinstance(key, str) and key.startswith("config."))

    def _config(self, key, default=None):
        if self._cfg is None:
            try:
                from . import contrib_configuration as CC
                self._cfg = CC.values()
            except Exception:  # noqa: BLE001
                self._cfg = {}
            try:
                self._cfg.update(self._svc.settings() if self._svc is not None else {})
            except Exception:  # noqa: BLE001
                pass
        if key in self._cfg:
            return self._cfg[key]
        # a section ("config.editor" -> truthy when any key under it exists)
        sub = {k[len(key) + 1:]: v for k, v in self._cfg.items() if k.startswith(key + ".")}
        return sub or default

    def copy(self):
        c = Context(dict(self), svc=self._svc)
        c._cfg = self._cfg
        return c


# ============================================================================ focus tracking
def install(svc) -> None:
    svc._focus = {"region": "", "view": "", "dock": None}
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(lambda _old, new, svc=svc: _focus_changed(svc, new))
    except Exception:  # noqa: BLE001
        pass


def _focus_changed(svc, w) -> None:
    if w is None:
        return
    try:
        from PyQt6.QtWidgets import QDockWidget, QMenu
        win = svc.win
        if isinstance(w, QMenu) or w.window() is not win and not (w.window().property("vsxFloatingView")):
            # pop-ups (Command Palette, menus, dialogs): keep the part the user came from
            top = w.window()
            if not isinstance(top, QDockWidget):
                return
        region, view = "", ""
        x = w
        dock = None
        while x is not None:
            if x in getattr(svc, "_editors", ()) or getattr(x, "diff_id", None) is not None:
                region = "editor"
                break
            if isinstance(x, QDockWidget):
                dock = x
                break
            x = x.parentWidget()
        if region != "editor" and dock is not None:
            view = dock.property("vsxViewId") or ""
            name = dock.objectName()
            if name.startswith("vsxWebview_") and dock.property("vsxHandle"):
                region = "webviewPanel"
            elif "terminal" in name.lower():
                region = "terminal"
            else:
                from PyQt6.QtCore import Qt
                area = win.dockWidgetArea(dock)
                region = {Qt.DockWidgetArea.LeftDockWidgetArea: "sideBar",
                          Qt.DockWidgetArea.BottomDockWidgetArea: "panel",
                          Qt.DockWidgetArea.RightDockWidgetArea: "auxiliaryBar"}.get(area, "sideBar")
        if not region:
            tabs = getattr(win, "tabs", None)
            y = w
            while y is not None and y is not tabs:
                y = y.parentWidget()
            region = "editorArea" if y is tabs and tabs is not None else ""
        svc._focus = {"region": region, "view": view, "dock": dock, "widget": w}
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ compute
def compute(svc, ed=None) -> Context:
    from .lsp_client import editor_lang
    win = svc.win
    ctx = Context(svc=svc)
    focus = getattr(svc, "_focus", {}) or {}
    region = focus.get("region", "")
    folders = svc.folders()
    wb = getattr(win, "workbench", None)
    code_mode = wb is not None and getattr(wb, "mode", "vs") != "vs"
    ctx.update({
        "isWindows": os.name == "nt", "isLinux": os.name != "nt" and not _is_mac(), "isMac": _is_mac(),
        "isMacNative": _is_mac(), "isWeb": False, "isIOS": False, "isMobile": False, "isDevelopment": False,
        "remoteName": "", "virtualWorkspace": "", "shellExecutionSupported": True, "processExecutionSupported": True,
        "extensionHostKind": "local", "isWorkspaceTrusted": True, "workspaceFolderCount": len(folders),
        "workbenchState": "folder" if len(folders) == 1 else "workspace" if folders else "empty",
        "isSessionsWindow": False, "isAuxiliaryWindow": False, "isCloud9": False, "embedderIdentifier": "",
        "isFullscreen": bool(win.isFullScreen()), "notebookEditorFocused": False, "notebookType": "",
        "isInEmbeddedEditor": False, "multipleEditorGroups": False, "editorPartMultipleEditorGroups": False,
        "suggestWidgetVisible": False, "inSnippetMode": False, "findWidgetVisible": False,
        "editorTabMovesFocus": False, "panelPosition": "bottom", "panelAlignment": "center",
        "panelMaximized": False, "debuggersAvailable": True,
    })
    # ---------------------------------------------------------------- editor + resource
    ed = ed if ed is not None else svc.active_editor()
    tabs = getattr(win, "tabs", None)
    cur = tabs.currentWidget() if tabs is not None else None
    diff = cur is not None and getattr(cur, "diff_id", None) is not None
    # no focus seen yet (start-up, offscreen tests): the active editor counts as focused, like before
    editor_focus = region in ("editor", "editorArea") or (region == "" and (ed if ed is not None else svc.active_editor()) is not None)
    ctx.update({"editorIsOpen": bool(tabs is not None and tabs.count()), "groupEditorsCount": tabs.count() if tabs else 0,
                "activeEditorGroupEmpty": not (tabs is not None and tabs.count()), "isInDiffEditor": diff,
                "textCompareEditorVisible": diff, "textCompareEditorActive": diff, "sideBySideEditorActive": False,
                "editorFocus": editor_focus, "editorTextFocus": editor_focus, "textInputFocus": editor_focus,
                "inputFocus": editor_focus or _is_text_input(focus.get("widget")), "dirtyWorkingCopies": False})
    if diff:
        try:
            ctx.update(cur.context())
        except Exception:  # noqa: BLE001
            pass
    elif ed is not None:
        p = Path(ed.path)
        lang = editor_lang(ed)
        sel = getattr(ed, "_selection", (0, 0, 0, 0)) or (0, 0, 0, 0)
        dirty = bool(getattr(ed, "is_modified", lambda: False)()) if callable(getattr(ed, "is_modified", None)) else False
        readonly = bool(getattr(ed, "_readonly", False))
        ctx.update({"editorLangId": lang, "resourceLangId": lang, "resourceExtname": p.suffix.lower(),
                    "resourceFilename": p.name, "resourcePath": str(p), "resourceDirname": str(p.parent),
                    "resource": p.as_uri() if p.is_absolute() else str(p), "resourceScheme": _scheme_of(svc, ed, p),
                    "resourceSet": True, "isFileSystemResource": True, "resourceIsFolder": False,
                    "editorHasSelection": not (sel[0] == sel[2] and sel[1] == sel[3]),
                    "editorHasMultipleSelections": bool(getattr(ed, "_multi_selection", False)),
                    "editorReadonly": readonly, "activeEditorIsReadonly": readonly, "activeEditorIsDirty": dirty,
                    "activeEditorIsNotPreview": True, "activeEditorIsPinned": False,
                    "activeEditor": "workbench.editors.files.textFileEditor",
                    "activeEditorAvailableEditorIds": "default", "activeEditorCanSplitInGroup": False,
                    "dirtyWorkingCopies": dirty})
        try:
            kinds = svc.index.kinds(lang, str(p))
        except Exception:  # noqa: BLE001
            kinds = set()
        for kind, key in PROVIDER_KEYS.items():
            ctx[key] = kind in kinds
    # webview panels / custom editors
    wp = svc.webviews.active_panel() if hasattr(svc.webviews, "active_panel") else None
    ctx["activeWebviewPanelId"] = wp.view_type if wp is not None and region in ("webviewPanel", "") else ""
    if wp is not None and region == "webviewPanel":
        ctx["activeEditor"] = "WebviewEditor"
        if getattr(wp, "custom_editor", False):
            ctx["activeCustomEditorId"] = wp.view_type
    ctx.setdefault("activeCustomEditorId", "")
    # ---------------------------------------------------------------- parts / views
    view = focus.get("view") or ""
    dock = focus.get("dock")
    ctx.update({"sideBarFocus": region == "sideBar", "panelFocus": region in ("panel", "terminal"),
                "auxiliaryBarFocus": region == "auxiliaryBar", "terminalFocus": region == "terminal",
                "focusedView": view, "listFocus": bool(view) and region in ("sideBar", "panel", "auxiliaryBar")
                and _is_tree(focus.get("widget")), "webviewFindWidgetVisible": False})
    if region == "webviewPanel" and wp is not None:
        ctx["webviewId"] = wp.view_type
    side = _docks_in(win, "left")
    ctx["sideBarVisible"] = bool(wb.side_visible()) if code_mode and hasattr(wb, "side_visible") else any(d.isVisible() for d in side)
    ctx["panelVisible"] = any(d.isVisible() for d in _docks_in(win, "bottom"))
    ctx["auxiliaryBarVisible"] = any(d.isVisible() for d in _docks_in(win, "right"))
    ctx["activeViewlet"] = _active_container(svc, "activitybar") or ("workbench.view.explorer" if ctx["sideBarVisible"] else "")
    ctx["activePanel"] = _active_container(svc, "panel") or ("workbench.panel.output" if ctx["panelVisible"] else "")
    ctx["activeAuxiliary"] = _active_container(svc, "secondarySidebar")
    sol = getattr(win, "dock_solution", None)
    ctx["explorerViewletVisible"] = bool(sol is not None and sol.isVisible())
    ctx["explorerViewletFocus"] = ctx["filesExplorerFocus"] = bool(dock is not None and dock is sol)
    term = getattr(svc.workbench, "terminals", None)
    n_terms = len(getattr(term, "views", {}) or {}) if term is not None else 0
    ctx.update({"terminalIsOpen": n_terms > 0, "terminalCount": n_terms})
    # ---------------------------------------------------------------- debug
    s = getattr(win, "session", None)
    try:
        running = bool(s is not None and s.running())
    except Exception:  # noqa: BLE001
        running = False
    paused = bool(running and getattr(s, "paused", False))
    ctx.update({"inDebugMode": running, "debugState": "stopped" if paused else "running" if running else "inactive",
                "debugType": str(getattr(s, "vsx_type", "") or getattr(s, "debug_type", "") or "") if running else "",
                "inDebugRepl": False, "debugConfigurationType": ""})
    ctx["inDebugRepl"] = bool(dock is not None and dock is getattr(win, "dock_immediate", None))
    # ---------------------------------------------------------------- derived / never-shown states
    find = getattr(win, "dock_find", None)
    out = getattr(svc, "dock", None)
    ctx.update({
        "foldingEnabled": True, "acceptSuggestionOnEnter": True, "remoteConnectionState": "", "inDiffEditor": diff,
        "isInDiffRightEditor": diff and editor_focus, "isInDiffLeftEditor": False, "terminalEditorActive": False,
        "inQuickOpen": False, "parameterHintsVisible": False, "searchViewletVisible": bool(find is not None and find.isVisible()),
        "canNavigateBack": False, "canNavigateForward": False, "foldersViewVisible": ctx["explorerViewletVisible"],
        "listSupportsFind": False, "hasWordHighlights": False, "inCompositeEditor": False, "editorHoverVisible": False,
        "renameInputVisible": False, "listDoubleSelection": False, "inOutput": bool(dock is not None and dock is out),
        "terminalTabsFocus": False, "isMergeResultEditor": False, "inChat": False, "inlineChatFocused": False,
        "terminalTextSelectedInFocused": False, "taskCommandsRegistered": True, "inlineSuggestionVisible": False,
        "findInputFocussed": False, "replaceInputFocussed": False, "explorerResourceMoveableToTrash": True,
        "notebookKernel": "", "scmProvider": "", "commentController": "", "callStackItemType": "", "notebookCellType": "",
        "notebookCellListFocused": False, "notebookOutputInputFocused": False, "comment": "", "commentThread": "",
        "chatSessionType": "", "testId": "", "controllerId": "", "isCompositeNotebook": False, "notebookKernelCount": 0,
        "notebookCellExecuting": False, "notebookEditable": False, "inlineEditIsVisible": False, "commentIsEmpty": True,
        "commentingEnabled": False,
    })
    # ---------------------------------------------------------------- setContext keys win
    ctx.update(svc.context)
    return ctx


def _is_mac() -> bool:
    import sys
    return sys.platform == "darwin"


def _scheme_of(svc, ed, p: Path) -> str:
    try:
        v = svc.workbench.virtual_scheme(str(p)) if hasattr(svc.workbench, "virtual_scheme") else None
        if v:
            return v
    except Exception:  # noqa: BLE001
        pass
    return "file"


def _is_text_input(w) -> bool:
    try:
        from PyQt6.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit
        return isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit))
    except Exception:  # noqa: BLE001
        return False


def _is_tree(w) -> bool:
    try:
        from PyQt6.QtWidgets import QAbstractItemView
        return isinstance(w, QAbstractItemView)
    except Exception:  # noqa: BLE001
        return False


def _docks_in(win, where: str) -> list:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QDockWidget
    area = {"left": Qt.DockWidgetArea.LeftDockWidgetArea, "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
            "right": Qt.DockWidgetArea.RightDockWidgetArea}[where]
    try:
        return [d for d in win.findChildren(QDockWidget) if d.parent() is win and not d.isFloating()
                and win.dockWidgetArea(d) == area]
    except Exception:  # noqa: BLE001
        return []


def _active_container(svc, location: str) -> str:
    """workbench.view.extension.<id> of the visible extension container in that location (VS Code's
    activeViewlet / activePanel / activeAuxiliary)."""
    try:
        for c in svc.views.containers():
            if c.get("location") != location:
                continue
            for v in c.get("views", []):
                d = svc.views.docks.get(v) or svc.webviews.view_docks.get(v)
                if d is not None and d.isVisible() and not d.visibleRegion().isEmpty():
                    from .views_ui import BUILTIN_CONTAINERS
                    return ("workbench.view." + c["id"]) if c["id"] in BUILTIN_CONTAINERS else \
                        "workbench.view.extension." + c["id"]
    except Exception:  # noqa: BLE001
        pass
    return ""


__all__ = ["Context", "compute", "install", "PROVIDED"]
