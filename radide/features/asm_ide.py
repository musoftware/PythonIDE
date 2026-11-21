"""Assembly editor integration (NASM, MASM, FASM, GNU as): the IDE side of radide/asm_intel.

* Every Monaco editor of an assembly file (``.asm .nasm .s .S .fasm .masm .mac``, and ``.inc`` next to assembly
  sources) gets assembly IntelliSense - also when the project's plugin is not an assembly plugin (a ``.s`` file in
  a C / Rust project, a loose file): ``MonacoEditor.plugin_overlays`` wraps the plugin with
  radide/asm_intel/plugin.AsmPluginOverlay. Assembly language plugins mix in AsmIntelMixin instead.
* The plugin's ``monaco_language()`` gives Monaco the dialect's Monarch grammar, word pattern and folding rules
  (radRegisterMonarch, radide/web/editor.html).
* This module adds, per assembly editor page: Monaco's document-symbol provider (breadcrumbs, Ctrl+Shift+O "Go to
  Symbol") and a same-file definition provider (Ctrl+click), both answered by the ``radAsm`` channel object; the
  Document Outline dock uses the plugin's ``document_symbols`` (radide/features/ring_ide.py).
* With asm-lsp attached (optional, radide/asm_intel/lsp.py) the built-in items are merged with the server's
  completions through ``MonacoEditor.completion_providers``.
"""
from __future__ import annotations

import json

from PyQt6.QtCore import QObject, pyqtSlot

SYMBOL_KIND = {"package": 3, "function": 11, "method": 5, "variable": 12, "constant": 13, "class": 4,
               "attribute": 7}

JS_PROVIDERS = """(function () {
  if (window.__radAsm) return;
  const obj = window.radChannel && window.radChannel.objects.radAsm;
  const editor = window.radEditor;
  if (!obj || !editor) return;
  window.__radAsm = true;
  const lang = editor.getModel().getLanguageId();
  const toSym = s => {
    const r = new monaco.Range(s.line + 1, 1, (s.end == null ? s.line : s.end) + 1, 1);
    const sel = new monaco.Range(s.line + 1, 1, s.line + 1, 1);
    return { name: s.name, detail: s.detail || '', kind: s.kind, range: r, selectionRange: sel, tags: [],
             children: (s.children || []).map(toSym) };
  };
  monaco.languages.registerDocumentSymbolProvider(lang, {
    displayName: 'Assembly',
    provideDocumentSymbols: model => model !== editor.getModel() ? [] : new Promise(res =>
      obj.symbols(r => { let list = []; try { list = JSON.parse(r || '[]'); } catch (e) {} res(list.map(toSym)); })) });
  monaco.languages.registerDefinitionProvider(lang, {
    provideDefinition: (model, pos) => model !== editor.getModel() ? null : new Promise(res =>
      obj.definition(pos.lineNumber - 1, pos.column - 1, line => res(line >= 0 ?
        { uri: model.uri, range: new monaco.Range(line + 1, 1, line + 1, 1) } : null))) });
})();"""


def _is_asm_editor(ed) -> bool:
    return bool(getattr(getattr(ed, "plugin", None), "asm_intel", False))


class AsmBridge(QObject):
    """Published to each Monaco page as ``radAsm`` (used only by assembly editors)."""

    def __init__(self, editor):
        super().__init__(editor)
        self.ed = editor

    @pyqtSlot(result=str)
    def symbols(self) -> str:
        if not _is_asm_editor(self.ed):
            return "[]"
        try:
            from ..asm_intel import engine
            from ..asm_intel.index import parse
            plugin = self.ed.plugin
            text = self.ed.text()
            syms = engine.document_symbols(text, self.ed.path, plugin)
            dia = getattr(plugin, "asm_dialect", "") or engine.detect_dialect(self.ed.path, text, plugin)
            ends = {(s.name, s.line): s.end_line for s in parse(text, dia).symbols}

            def conv(s):
                return {"name": s["name"], "detail": s.get("detail", ""), "line": s["line"],
                        "end": max(s["line"], ends.get((s["name"], s["line"]), s["line"])),
                        "kind": SYMBOL_KIND.get(s.get("kind"), 12),
                        "children": [conv(c) for c in s.get("children") or []]}
            return json.dumps([conv(s) for s in syms])
        except Exception as e:  # noqa: BLE001 - the outline must never break the editor
            print(f"[asm] symbols failed: {e}")
            return "[]"

    @pyqtSlot(int, int, result=int)
    def definition(self, line: int, col: int) -> int:
        """Line of the definition when it is in this same file (Ctrl+click), else -1 (F12 opens other files)."""
        if not _is_asm_editor(self.ed):
            return -1
        try:
            res = self.ed.plugin.definition(self.ed.text(), line, col, self.ed.path, None)
        except Exception:  # noqa: BLE001
            return -1
        if not res:
            return -1
        from pathlib import Path
        try:
            same = Path(res[0]).resolve() == Path(str(self.ed.path)).resolve()
        except OSError:
            same = False
        return int(res[1]) if same else -1


def on_editor_ready(ed) -> None:
    if not _is_asm_editor(ed):
        return
    try:
        ed._js(JS_PROVIDERS)
        win = ed.window()
        spec = ed._custom_spec() if hasattr(ed, "_custom_spec") else None
        if spec and win is not None and hasattr(win, "statusBar"):
            from .. import i18n
            from ..asm_intel.directives import DIALECT_NAMES
            from ..asm_intel.index import abi_of
            abi = abi_of(ed.text() or "", spec.get("dialect", "nasm"), ed.path)
            abi_name = {"win64": "Windows x64", "sysv": "Linux x86-64", "x86": "32-bit x86",
                        "dos16": "16-bit DOS"}.get(abi, abi)
            win.statusBar().showMessage(i18n.tr("Assembly") + f": {DIALECT_NAMES.get(spec.get('dialect'), '')} - "
                                        f"{i18n.tr(abi_name)}" + (" (AT&T)" if spec.get("att") else ""), 4000)
    except Exception as e:  # noqa: BLE001 - never break the editor
        print(f"[asm] editor hook: {e}")


def lsp_completions(ed, line: int, col: int):
    """MonacoEditor.completion_providers entry: built-in items merged with asm-lsp's (only while it is attached -
    without a server the plugin's own completions are used directly)."""
    if not _is_asm_editor(ed) or getattr(ed, "lsp", None) is None:
        return None
    from ..monaco_editor import KIND
    out = []
    for c in ed.plugin.completions(ed.text(), line, col, ed.path, None)[:300]:
        item = {"label": c.name, "kind": KIND.get(c.kind, 18), "detail": c.detail or c.kind}
        if getattr(c, "doc", ""):
            item["documentation"] = c.doc
        if getattr(c, "insert", ""):
            item["insertText"] = c.insert
        if getattr(c, "snippet", False):
            item["snippet"] = True
        if getattr(c, "sort", ""):
            item["sortText"] = c.sort
        if getattr(c, "edits", None):
            item["additionalTextEdits"] = c.edits
        out.append(item)
    return out


def install(win) -> None:
    try:
        from ..monaco_editor import MonacoEditor
    except ImportError:                      # no QtWebEngine: the built-in editor has no Monaco hooks
        return
    from ..asm_intel.plugin import overlay_for
    if hasattr(MonacoEditor, "plugin_overlays") and overlay_for not in MonacoEditor.plugin_overlays:
        MonacoEditor.plugin_overlays.append(overlay_for)
    MonacoEditor.channel_objects["radAsm"] = AsmBridge
    if on_editor_ready not in MonacoEditor.ready_hooks:
        MonacoEditor.ready_hooks.append(on_editor_ready)
    if lsp_completions not in MonacoEditor.completion_providers:
        MonacoEditor.completion_providers.append(lsp_completions)
