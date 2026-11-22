'use strict';
// Built-in commands of VS Code that the extension host implements itself (the API commands of
// src/vs/workbench/api/common/extHostApiCommands.ts and workbench commands that need extension-host state),
// following the argument / return conventions of microsoft/vscode (see radide/vsx/reference/commands.json).
// main.js asks run(id, args) after its own switch; NOT_HANDLED sends the command on to the IDE
// (radide/vsx/workbench_ui.py exec_command). Commands VS Code has but RAD IDE cannot show resolve to
// undefined like VS Code without that UI; ids nobody knows reject with "command 'x' not found".

const fs = require('fs');
const path = require('path');
const T = require('./types');

const NOT_HANDLED = Symbol('notHandled');
const PROVIDER_TIMEOUT = 5000;

function withTimeout(promise, ms, dflt) {
  let timer;
  return Promise.race([Promise.resolve(promise), new Promise((res) => { timer = setTimeout(() => res(dflt), ms); })]).finally(() => clearTimeout(timer));
}

// ids of every built-in VS Code command (radide/vsx/reference/commands.json), loaded on first use
let _known = null;
function knownVsCodeCommands() {
  if (_known) return _known;
  _known = new Set();
  try {
    const j = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'reference', 'commands.json'), 'utf8'));
    for (const c of j.commands || []) _known.add(c.id);
    for (const c of j.apiCommands || []) _known.add(c.id);
  } catch (_) { /* reference data missing: nothing is "known" */ }
  return _known;
}
function isDynamicVsCodeCommand(id) {
  // ${viewId}.focus / .open / .resetViewLocation / .toggleVisibility / .removeView, workbench.view.extension.*
  return /\.(focus|open|resetViewLocation|toggleVisibility|removeView)$/.test(id) || id.startsWith('workbench.view.extension.');
}

class BuiltinCommands {
  constructor(host) {
    this.host = host;
    this._callItems = new WeakMap();     // CallHierarchyItem -> provider
    this._typeItems = new WeakMap();     // TypeHierarchyItem -> provider
    this.handlers = new Map(Object.entries(this._table()));
  }

  ids() { return [...this.handlers.keys()]; }
  has(id) { return this.handlers.has(id); }
  isKnown(id) { return knownVsCodeCommands().has(id) || isDynamicVsCodeCommand(id); }

  async run(id, args) {
    const h = this.handlers.get(id);
    if (!h) return NOT_HANDLED;
    return h.call(this, args || []);
  }

  // ------------------------------------------------------------------ helpers
  asUri(u) {
    const C = require('./convert');
    if (u === undefined || u === null) return undefined;
    if (T.Uri.isUri(u)) return u;
    if (typeof u === 'object' && u.$uri) return C.uriFromIde(u.$uri);
    if (typeof u === 'object' && u.scheme) return T.Uri.from(u);
    return C.uriFromIde(String(u));
  }
  async doc(u) { return this.host.openTextDocument(this.asUri(u)); }
  pos(p) { return p instanceof T.Position ? p : new T.Position(p.line, p.character); }
  range(r) {
    if (r instanceof T.Range) return r;
    if (r && r.start) return new T.Range(this.pos(r.start), this.pos(r.end || r.start));
    return new T.Range(this.pos(r), this.pos(r));
  }
  providers(kind, doc) { return this.host._providersFor(kind, doc); }
  async collect(kind, doc, call) { return this.host._collect(kind, doc, call); }
  ide(command, args) { return this.host.rpc.request('commands/executeIde', { command, args: require('./convert').plain(args || []) }); }
  unsupported(id, why) { this.host.unsupported(null, `command ${id}${why ? ' (' + why + ')' : ''}`); }

  // ------------------------------------------------------------------ the table
  _table() {
    const self = this;
    const nothing = (id, why) => async () => { self.unsupported(id, why); return undefined; };
    return {
      // ---------------------------------------------------------------- language feature API commands
      'vscode.executeCompletionItemProvider': async ([u, position, triggerCharacter, itemResolveCount]) => {
        const doc = await this.doc(u);
        const pos = doc.validatePosition(this.pos(position));
        const ctx = triggerCharacter ? { triggerKind: T.CompletionTriggerKind.TriggerCharacter, triggerCharacter } : { triggerKind: T.CompletionTriggerKind.Invoke, triggerCharacter: undefined };
        let incomplete = false;
        const items = [];
        const owners = [];
        const cts = new T.CancellationTokenSource();
        await Promise.all(this.providers('completion', doc).map(async (p) => {
          if (triggerCharacter && !p.triggers.includes(triggerCharacter)) return;
          try {
            const r = await withTimeout(p.provider.provideCompletionItems(doc, pos, cts.token, ctx), PROVIDER_TIMEOUT, undefined);
            if (!r) return;
            const list = Array.isArray(r) ? r : (r.items || []);
            if (!Array.isArray(r) && r.isIncomplete) incomplete = true;
            for (const it of list) { items.push(it); owners.push(p); }
          } catch (e) { this.host.log(p.ext, 'completion provider failed: ' + (e && e.stack || e)); }
        }));
        const n = Math.min(Number(itemResolveCount) || 0, items.length);
        for (let i = 0; i < n; i++) {
          const p = owners[i].provider;
          if (typeof p.resolveCompletionItem === 'function') {
            try { const r = await withTimeout(p.resolveCompletionItem(items[i], cts.token), PROVIDER_TIMEOUT, undefined); if (r) items[i] = r; } catch (_) { /* */ }
          }
        }
        cts.cancel();
        return new T.CompletionList(items, incomplete);
      },
      'vscode.executeCodeActionProvider': async ([u, rangeOrSelection, kind, itemResolveCount]) => {
        const doc = await this.doc(u);
        const range = this.range(rangeOrSelection);
        const only = kind ? new T.CodeActionKind(kind) : undefined;
        const ctx = { diagnostics: this.host.getDiagnostics(doc.uri).filter((d) => d.range.intersection(range)), only, triggerKind: T.CodeActionTriggerKind.Invoke };
        const out = [];
        const owners = [];
        const cts = new T.CancellationTokenSource();
        await Promise.all(this.providers('codeAction', doc).map(async (p) => {
          const provided = p.metadata && p.metadata.providedCodeActionKinds;
          if (only && provided && !provided.some((k) => only.contains(k) || k.contains(only))) return;
          try {
            const r = await withTimeout(p.provider.provideCodeActions(doc, range, ctx, cts.token), PROVIDER_TIMEOUT, undefined);
            for (const a of r || []) {
              if (only && a && a.kind && !only.contains(a.kind)) continue;
              out.push(a); owners.push(p);
            }
          } catch (e) { this.host.log(p.ext, 'code action provider failed: ' + (e && e.stack || e)); }
        }));
        const n = Math.min(Number(itemResolveCount) || 0, out.length);
        for (let i = 0; i < n; i++) {
          const p = owners[i].provider;
          if (out[i] && !out[i].edit && typeof p.resolveCodeAction === 'function' && !(typeof out[i].command === 'string')) {
            try { const r = await withTimeout(p.resolveCodeAction(out[i], cts.token), PROVIDER_TIMEOUT, undefined); if (r) out[i] = r; } catch (_) { /* */ }
          }
        }
        cts.cancel();
        return out;
      },
      'vscode.executeCodeLensProvider': async ([u, itemResolveCount]) => {
        const doc = await this.doc(u);
        const out = [];
        const cts = new T.CancellationTokenSource();
        for (const p of this.providers('codeLens', doc)) {
          try {
            const lenses = (await withTimeout(p.provider.provideCodeLenses(doc, cts.token), PROVIDER_TIMEOUT, [])) || [];
            for (const l of lenses) out.push({ l, p });
          } catch (e) { this.host.log(p.ext, 'code lens provider failed: ' + (e && e.stack || e)); }
        }
        let budget = Number(itemResolveCount) || 0;
        const res = [];
        for (const { l, p } of out) {
          let lens = l;
          if (!lens.command && budget > 0 && typeof p.provider.resolveCodeLens === 'function') {
            budget--;
            try { lens = (await withTimeout(p.provider.resolveCodeLens(lens, cts.token), PROVIDER_TIMEOUT, undefined)) || lens; } catch (_) { /* */ }
          }
          res.push(lens);
        }
        cts.cancel();
        return res;
      },
      'vscode.executeLinkProvider': async ([u, linkResolveCount]) => {
        const doc = await this.doc(u);
        const out = [];
        const cts = new T.CancellationTokenSource();
        let budget = Number(linkResolveCount) || 0;
        for (const p of this.providers('documentLink', doc)) {
          try {
            for (let link of (await withTimeout(p.provider.provideDocumentLinks(doc, cts.token), PROVIDER_TIMEOUT, [])) || []) {
              if (!link.target && budget > 0 && typeof p.provider.resolveDocumentLink === 'function') {
                budget--;
                try { link = (await withTimeout(p.provider.resolveDocumentLink(link, cts.token), PROVIDER_TIMEOUT, undefined)) || link; } catch (_) { /* */ }
              }
              out.push(link);
            }
          } catch (e) { this.host.log(p.ext, 'link provider failed: ' + (e && e.stack || e)); }
        }
        cts.cancel();
        return out;
      },
      'vscode.executeFormatOnTypeProvider': async ([u, position, ch, options]) => {
        const doc = await this.doc(u);
        const p = this.providers('onTypeFormatting', doc).find((x) => !ch || x.triggers.includes(ch));
        if (!p) return [];
        return (await withTimeout(p.provider.provideOnTypeFormattingEdits(doc, this.pos(position), String(ch || ''), options || { tabSize: 4, insertSpaces: true }, T.CancellationTokenNone), PROVIDER_TIMEOUT, [])) || [];
      },
      'vscode.executeColorPresentationProvider': async ([color, context]) => {
        const doc = await this.doc(context && context.uri);
        const out = await this.collect('color', doc, (p, tok) => (typeof p.provideColorPresentations === 'function' ? p.provideColorPresentations(color, { document: doc, range: this.range(context.range) }, tok) : undefined));
        return out.flat();
      },
      'vscode.executeInlineValueProvider': async ([u, range, context]) => {
        const doc = await this.doc(u);
        return (await this.collect('inlineValues', doc, (p, tok) => p.provideInlineValues(doc, this.range(range), context || { frameId: 0, stoppedLocation: this.range(range) }, tok))).flat();
      },
      'vscode.prepareCallHierarchy': async ([u, position]) => {
        const doc = await this.doc(u);
        const out = [];
        for (const p of this.providers('callHierarchy', doc)) {
          try {
            const r = await withTimeout(p.provider.prepareCallHierarchy(doc, this.pos(position), T.CancellationTokenNone), PROVIDER_TIMEOUT, undefined);
            for (const it of [].concat(r || [])) { this._callItems.set(it, p.provider); out.push(it); }
          } catch (e) { this.host.log(p.ext, 'call hierarchy provider failed: ' + (e && e.stack || e)); }
        }
        return out;
      },
      'vscode.provideIncomingCalls': async ([item]) => {
        const p = item && this._callItems.get(item);
        if (!p) return [];
        const r = (await withTimeout(p.provideCallHierarchyIncomingCalls(item, T.CancellationTokenNone), PROVIDER_TIMEOUT, [])) || [];
        for (const c of r) if (c && c.from) this._callItems.set(c.from, p);
        return r;
      },
      'vscode.provideOutgoingCalls': async ([item]) => {
        const p = item && this._callItems.get(item);
        if (!p) return [];
        const r = (await withTimeout(p.provideCallHierarchyOutgoingCalls(item, T.CancellationTokenNone), PROVIDER_TIMEOUT, [])) || [];
        for (const c of r) if (c && c.to) this._callItems.set(c.to, p);
        return r;
      },
      'vscode.prepareTypeHierarchy': async ([u, position]) => {
        const doc = await this.doc(u);
        const out = [];
        for (const p of this.providers('typeHierarchy', doc)) {
          try {
            const r = await withTimeout(p.provider.prepareTypeHierarchy(doc, this.pos(position), T.CancellationTokenNone), PROVIDER_TIMEOUT, undefined);
            for (const it of [].concat(r || [])) { this._typeItems.set(it, p.provider); out.push(it); }
          } catch (e) { this.host.log(p.ext, 'type hierarchy provider failed: ' + (e && e.stack || e)); }
        }
        return out;
      },
      'vscode.provideSupertypes': async ([item]) => {
        const p = item && this._typeItems.get(item);
        if (!p) return [];
        const r = (await withTimeout(p.provideTypeHierarchySupertypes(item, T.CancellationTokenNone), PROVIDER_TIMEOUT, [])) || [];
        for (const it of r) this._typeItems.set(it, p);
        return r;
      },
      'vscode.provideSubtypes': async ([item]) => {
        const p = item && this._typeItems.get(item);
        if (!p) return [];
        const r = (await withTimeout(p.provideTypeHierarchySubtypes(item, T.CancellationTokenNone), PROVIDER_TIMEOUT, [])) || [];
        for (const it of r) this._typeItems.set(it, p);
        return r;
      },
      'vscode.provideDocumentSemanticTokensLegend': async ([u]) => {
        const doc = await this.doc(u);
        const p = this.providers('semanticTokens', doc)[0];
        return p ? p.metadata : undefined;
      },
      'vscode.provideDocumentSemanticTokens': async ([u]) => {
        const doc = await this.doc(u);
        const p = this.providers('semanticTokens', doc)[0];
        if (!p) return undefined;
        const r = await withTimeout(p.provider.provideDocumentSemanticTokens(doc, T.CancellationTokenNone), PROVIDER_TIMEOUT, undefined);
        return r && r.data ? r : undefined;
      },
      'vscode.provideDocumentRangeSemanticTokensLegend': async ([u]) => {
        const doc = await this.doc(u);
        const p = this.providers('rangeSemanticTokens', doc)[0] || this.providers('semanticTokens', doc)[0];
        return p ? p.metadata : undefined;
      },
      'vscode.provideDocumentRangeSemanticTokens': async ([u, range]) => {
        const doc = await this.doc(u);
        const p = this.providers('rangeSemanticTokens', doc)[0];
        if (!p) return undefined;
        return (await withTimeout(p.provider.provideDocumentRangeSemanticTokens(doc, this.range(range), T.CancellationTokenNone), PROVIDER_TIMEOUT, undefined)) || undefined;
      },
      'vscode.experimental.executeDefinitionProvider_recursive': (a) => this.host.executeCommand('vscode.executeDefinitionProvider', a),
      'vscode.experimental.executeDeclarationProvider_recursive': (a) => this.host.executeCommand('vscode.executeDeclarationProvider', a),
      'vscode.experimental.executeTypeDefinitionProvider_recursive': (a) => this.host.executeCommand('vscode.executeTypeDefinitionProvider', a),
      'vscode.experimental.executeImplementationProvider_recursive': (a) => this.host.executeCommand('vscode.executeImplementationProvider', a),
      'vscode.experimental.executeHoverProvider_recursive': (a) => this.host.executeCommand('vscode.executeHoverProvider', a),
      'vscode.experimental.executeReferenceProvider': (a) => this.host.executeCommand('vscode.executeReferenceProvider', a),
      // ---------------------------------------------------------------- notebooks (serializers work, no notebook editor)
      'vscode.executeDataToNotebook': async ([notebookType, data]) => {
        const s = this.host.notebooks.serializers && this.host.notebooks.serializers.get(notebookType);
        if (!s) throw new Error(`No notebook serializer for '${notebookType}'`);
        return s.serializer.deserializeNotebook(data, T.CancellationTokenNone);
      },
      'vscode.executeNotebookToData': async ([notebookType, data]) => {
        const s = this.host.notebooks.serializers && this.host.notebooks.serializers.get(notebookType);
        if (!s) throw new Error(`No notebook serializer for '${notebookType}'`);
        return s.serializer.serializeNotebook(data, T.CancellationTokenNone);
      },
      'vscode.resolveNotebookContentProviders': async () => {
        const out = [];
        for (const ext of this.host.extensions.values()) {
          for (const nb of ((ext.packageJSON.contributes || {}).notebooks) || []) {
            out.push({ viewType: nb.type, displayName: nb.displayName, filenamePattern: (nb.selector || []).map((s) => s.filenamePattern).filter(Boolean), options: { transientOutputs: false, transientCellMetadata: {}, transientDocumentMetadata: {} } });
          }
        }
        return out;
      },
      'vscode.executeNotebookVariableProvider': async () => [],
      'notebook.selectKernel': nothing('notebook.selectKernel', 'no notebook editor'),
      'interactive.open': nothing('interactive.open', 'no interactive window'),
      'vscode.editorChat.start': nothing('vscode.editorChat.start', 'no inline chat'),
      'vscode.extensionPromptFileProvider': async () => [],
      'vscode.executeStructuralDiffProvider': async () => undefined,
      'vscode.experimental.editSession.continue': nothing('vscode.experimental.editSession.continue', 'no edit sessions'),
      // ---------------------------------------------------------------- testing (no Test Explorer)
      'vscode.revealTestInExplorer': nothing('vscode.revealTestInExplorer', 'no Test Explorer'),
      'vscode.startContinuousTestRun': nothing('vscode.startContinuousTestRun', 'no Test Explorer'),
      'vscode.stopContinuousTestRun': nothing('vscode.stopContinuousTestRun', 'no Test Explorer'),
      // ---------------------------------------------------------------- files / editors
      'workbench.action.files.newUntitledFile': async ([opts]) => {
        // NEW_UNTITLED_FILE_COMMAND_ID (fileCommands.ts): args { languageId?, viewType?, fileName? }
        const o = opts && typeof opts === 'object' ? opts : {};
        if (o.viewType && this.host.customEditors.providers.has(o.viewType)) return undefined;
        const doc = await this.host.openTextDocument({ language: o.languageId || 'plaintext', content: '' });
        await this.host.showTextDocument(doc);
        return undefined;
      },
      'copyFilePath': async ([resource, ctx]) => this._copyPaths(resource, ctx, false),
      'copyRelativeFilePath': async ([resource, ctx]) => this._copyPaths(resource, ctx, true),
      'editor.action.showReferences': async ([u, position, locations]) => this._locations(u, position, locations, 'peek'),
      'editor.action.goToLocations': async ([u, position, locations, multiple, noResultsMessage]) => this._locations(u, position, locations, multiple || 'peek', noResultsMessage),
      'editor.action.peekLocations': async ([u, position, locations, multiple]) => this._locations(u, position, locations, multiple || 'peek'),
      // ---------------------------------------------------------------- tasks
      'workbench.action.tasks.runTask': async ([arg]) => {
        // arg: task name | { type, task } (tasks contribution); without one VS Code shows the task picker
        const tasks = await this.host.tasksSvc.fetch();
        let task;
        if (typeof arg === 'string') task = tasks.find((t) => t.name === arg || `${t.source}: ${t.name}` === arg);
        else if (arg && typeof arg === 'object') task = tasks.find((t) => (!arg.type || (t.definition && t.definition.type === arg.type)) && (!arg.task || t.name === arg.task));
        if (!task && tasks.length) {
          const pick = await this.host.showQuickPick(tasks.map((t) => ({ label: t.name, description: t.source, task: t })), { placeHolder: 'Select the task to run' });
          task = pick && pick.task;
        }
        if (task) await this.host.executeTask(null, task);
        return undefined;
      },
      'workbench.action.tasks.reRunTask': async () => {
        const last = this.host.tasksSvc.last;
        if (last) await this.host.executeTask(last.ext, last.task);
        return undefined;
      },
      // runCommands (src/vs/workbench/contrib/commands/common/commands.contribution.ts): { commands: (id | {command, args})[] }
      'runCommands': async ([arg]) => {
        const list = arg && Array.isArray(arg.commands) ? arg.commands : [];
        if (!list.length) throw new Error('runCommands: no commands to run');
        for (const c of list) {
          if (typeof c === 'string') await this.host.executeCommand(c, []);
          else if (c && typeof c.command === 'string') await this.host.executeCommand(c.command, c.args === undefined ? [] : [c.args]);
        }
        return undefined;
      },
      // editor.action.insertSnippet (snippets contribution): { snippet?, langId?, name? } into the active editor
      'editor.action.insertSnippet': async ([arg]) => {
        const ed = this.host.activeEditor();
        if (!ed || !arg) return undefined;
        let body = typeof arg.snippet === 'string' ? arg.snippet : undefined;
        if (body === undefined && arg.name) {
          for (const ext of this.host.extensions.values()) {
            for (const sn of ((ext.packageJSON.contributes || {}).snippets) || []) {
              if (arg.langId && sn.language !== arg.langId) continue;
              try {
                const j = JSON.parse(fs.readFileSync(path.join(ext.path, sn.path), 'utf8').replace(/^﻿/, ''));
                const hit = j[arg.name];
                if (hit) body = Array.isArray(hit.body) ? hit.body.join('\n') : String(hit.body);
              } catch (_) { /* */ }
            }
          }
        }
        if (body !== undefined) await ed.insertSnippet(new T.SnippetString(body));
        return undefined;
      },
      // ---------------------------------------------------------------- extensions / help
      'workbench.action.openIssueReporter': async ([arg]) => {
        const o = typeof arg === 'string' ? { extensionId: arg } : (arg || {});
        const ext = o.extensionId && this.host.extensions.get(String(o.extensionId).toLowerCase());
        const pj = ext ? ext.packageJSON : null;
        let url = pj && pj.bugs && (typeof pj.bugs === 'string' ? pj.bugs : pj.bugs.url);
        if (!url && pj && pj.repository) {
          const r = typeof pj.repository === 'string' ? pj.repository : pj.repository.url;
          if (r && /github\.com/.test(r)) url = r.replace(/^git\+/, '').replace(/\.git$/, '') + '/issues/new';
        }
        if (!url) url = 'https://github.com/microsoft/vscode/issues/new';
        if (o.issueTitle || o.issueBody) {
          const q = [o.issueTitle ? 'title=' + encodeURIComponent(o.issueTitle) : '', o.issueBody ? 'body=' + encodeURIComponent(o.issueBody) : ''].filter(Boolean).join('&');
          url += (url.includes('?') ? '&' : '?') + q;
        }
        await this.host.rpc.request('env/openExternal', { uri: url });
        return undefined;
      },
      'workbench.trust.manage': nothing('workbench.trust.manage', 'RAD IDE trusts every folder'),
      'workbench.action.manageTrustedDomain': nothing('workbench.action.manageTrustedDomain'),
    };
  }

  // copyFilePath / copyRelativeFilePath (fileCommands.ts resourcesToClipboard)
  async _copyPaths(resource, ctx, relative) {
    let uris = [];
    if (ctx && Array.isArray(ctx.allUris)) uris = ctx.allUris.map((u) => this.asUri(u));
    else if (resource) uris = [this.asUri(resource)];
    else { const ed = this.host.activeEditor(); if (ed) uris = [ed.document.uri]; }
    uris = uris.filter(Boolean);
    if (!uris.length) return undefined;
    const cfg = this.host.getConfiguration('explorer');
    const sepSetting = cfg.get(relative ? 'copyRelativePathSeparator' : 'copyPathSeparator');
    const sep = sepSetting === '/' || sepSetting === '\\' ? sepSetting : (process.platform === 'win32' ? '\\' : '/');
    const lines = uris.map((u) => {
      let p = u.scheme === 'file' ? u.fsPath : u.toString(true);
      if (relative && u.scheme === 'file') p = this.host.asRelativePath(u, false);
      return u.scheme === 'file' ? p.replace(/[\\/]/g, sep) : p;
    });
    await this.host.rpc.request('env/clipboardWrite', { text: lines.join(process.platform === 'win32' ? '\r\n' : '\n') });
    return undefined;
  }

  // editor.action.showReferences / goToLocations / peekLocations: one location -> go there; several -> pick one
  // (RAD IDE has no peek widget: a quick pick lists the locations like the References view would)
  async _locations(u, position, locations, multiple, noResultsMessage) {
    // Location | LocationLink (and their plain JSON shapes)
    const locs = (locations || []).map((l) => {
      if (!l) return null;
      if (l.targetUri) return new T.Location(this.asUri(l.targetUri), this.range(l.targetSelectionRange || l.targetRange));
      if (l.uri && l.range) return l instanceof T.Location ? l : new T.Location(this.asUri(l.uri), Array.isArray(l.range) ? new T.Range(this.pos(l.range[0]), this.pos(l.range[1])) : this.range(l.range));
      return null;
    }).filter((l) => l && l.uri);
    if (!locs.length) {
      if (noResultsMessage) await this.host.showMessage('info', { message: String(noResultsMessage), options: {}, items: [] });
      return undefined;
    }
    let target = locs[0];
    if (locs.length > 1 && multiple !== 'goto' && multiple !== 'gotoAndPeek') {
      const items = [];
      for (const l of locs) {
        let text = '';
        try { const d = await this.host.openTextDocument(l.uri); text = d.lineAt(l.range.start.line).text.trim(); } catch (_) { /* */ }
        items.push({ label: `${path.basename(l.uri.fsPath || l.uri.path)}:${l.range.start.line + 1}`, description: text.slice(0, 120), detail: l.uri.fsPath, loc: l });
      }
      const pick = await this.host.showQuickPick(items, { placeHolder: `${locs.length} locations` });
      if (!pick) return undefined;
      target = pick.loc;
    }
    await this.host.showTextDocument(target.uri, { selection: target.range });
    return undefined;
  }
}

module.exports = { BuiltinCommands, NOT_HANDLED, knownVsCodeCommands, isDynamicVsCodeCommand };
