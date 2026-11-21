'use strict';
// Registries behind APIs that used to be no-op mocks in api.js:
//   window.registerUriHandler (+ IDE request uri/handle), window.registerFileDecorationProvider
//   (+ IDE request decorations/file), authentication.*, tasks.* (providers, fetch, execute + events),
//   window.registerCustomEditorProvider (custom editors in webview panels, vscode.openWith),
//   notebooks (serializers, openNotebookDocument, controllers - no notebook UI),
//   comments / tests / scm / chat / lm objects with VS Code's shapes (no UI in RAD IDE).

const path = require('path');
const T = require('./types');
const { decode } = require('./workbench');

// ============================================================================ URI handlers
class UriHandlers {
  constructor(host) { this.host = host; this.handlers = new Map(); }

  register(ext, handler) {
    if (this.handlers.has(ext.id)) throw new Error(`Protocol handler already registered for extension ${ext.idOriginal || ext.id}`);
    this.handlers.set(ext.id, { ext, handler });
    return new T.Disposable(() => { if (this.handlers.get(ext.id)?.handler === handler) this.handlers.delete(ext.id); });
  }

  /** deliver <scheme>://publisher.name/path?query#fragment to the extension publisher.name */
  async handle({ uri }) {
    let u;
    try { u = T.Uri.parse(String(uri)); } catch (e) { return { ok: false, error: String(e) }; }
    const id = String(u.authority || '').toLowerCase();
    const ext = this.host.extensions.get(id);
    if (!ext) return { ok: false, error: `no extension '${u.authority}' is installed` };
    if (!this.handlers.has(id)) {
      if (ext.main && !ext.active) await this.host.activate(ext, 'onUri');
    }
    const h = this.handlers.get(id);
    if (!h) return { ok: false, error: `the extension '${u.authority}' has no URI handler` };
    try { await h.handler.handleUri(u); return { ok: true }; } catch (e) {
      this.host.log(ext, 'handleUri failed: ' + (e && e.stack || e));
      return { ok: false, error: String(e && e.message || e) };
    }
  }
}

// ============================================================================ file decorations
class FileDecorations {
  constructor(host) { this.host = host; this.providers = new Set(); }

  register(ext, provider) {
    const e = { ext, provider, sub: null };
    if (provider && typeof provider.onDidChangeFileDecorations === 'function') {
      e.sub = provider.onDidChangeFileDecorations((uris) => {
        const list = uris === undefined ? null : (Array.isArray(uris) ? uris : [uris]).filter(Boolean).map((u) => (u.scheme === 'file' ? u.fsPath : u.toString()));
        this.host.rpc.notify('decorations/fileChanged', { paths: list });
      });
    }
    this.providers.add(e);
    this.host.rpc.notify('decorations/fileChanged', { paths: null });
    return new T.Disposable(() => { this.providers.delete(e); try { e.sub && e.sub.dispose(); } catch (_) { /* */ } });
  }

  async provide({ paths }) {
    const out = {};
    for (const p of paths || []) {
      const uri = /^[a-zA-Z][\w+.-]+:\/\//.test(p) ? T.Uri.parse(p) : T.Uri.file(p);
      const merged = {};
      for (const e of this.providers) {
        try {
          const d = await Promise.race([Promise.resolve(e.provider.provideFileDecoration(uri, T.CancellationTokenNone)), new Promise((r) => setTimeout(() => r(undefined), 2000))]);
          if (!d) continue;
          if (d.badge && !merged.badge) merged.badge = String(d.badge);
          if (d.tooltip) merged.tooltip = merged.tooltip ? merged.tooltip + ' - ' + d.tooltip : String(d.tooltip);
          if (d.color && !merged.color) merged.color = d.color.id || String(d.color);
          if (d.propagate) merged.propagate = true;
        } catch (err) { this.host.log(e.ext, 'file decoration provider failed: ' + err); }
      }
      if (Object.keys(merged).length) out[p] = merged;
    }
    return out;
  }
}

// ============================================================================ authentication
class Authentication {
  constructor(host) { this.host = host; this.providers = new Map(); this.em = new T.EventEmitter(); }

  register(ext, id, label, provider, options) {
    if (this.providers.has(id)) throw new Error(`An authentication provider with id '${id}' is already registered.`);
    const e = { ext, id, label: label || id, provider, options: options || {}, sub: null };
    if (provider && typeof provider.onDidChangeSessions === 'function') {
      e.sub = provider.onDidChangeSessions(() => this.em.fire({ provider: { id, label: e.label } }));
    }
    this.providers.set(id, e);
    return new T.Disposable(() => { if (this.providers.get(id) === e) { this.providers.delete(id); try { e.sub && e.sub.dispose(); } catch (_) { /* */ } } });
  }

  async _entry(id) {
    if (!this.providers.has(id)) await this.host.activateByEvent('onAuthenticationRequest:' + id);
    return this.providers.get(id);
  }

  async getSession(ext, providerId, scopes, options) {
    const o = options || {};
    scopes = [...(scopes || [])];
    const e = await this._entry(providerId);
    if (!e) {
      if (o.createIfNone || o.forceNewSession) throw new Error(`No authentication provider '${providerId}' is currently registered.`);
      return undefined;
    }
    const sessions = (await e.provider.getSessions(scopes, { account: o.account })) || [];
    const sorted = (a) => [...a].sort().join(' ');
    const found = sessions.find((s) => sorted(s.scopes || []) === sorted(scopes)) || sessions[0];
    if (found && !o.forceNewSession) return found;
    if (o.silent || !(o.createIfNone || o.forceNewSession)) return undefined;
    const who = (ext && ext.packageJSON && (ext.packageJSON.displayName || ext.packageJSON.name)) || 'An extension';
    const detail = typeof o.forceNewSession === 'object' && o.forceNewSession.detail ? o.forceNewSession.detail : '';
    const pick = await this.host.showMessage('info', { message: `The extension '${who}' wants to sign in using ${e.label}.`, options: { modal: true, detail }, items: ['Allow'] });
    if (pick !== 'Allow') throw new Error('User did not consent to login.');
    return e.provider.createSession(scopes, { account: o.account });
  }

  async getAccounts(providerId) {
    const e = await this._entry(providerId);
    if (!e) return [];
    const sessions = (await e.provider.getSessions(undefined, {})) || [];
    const seen = new Map();
    for (const s of sessions) if (s.account && !seen.has(s.account.id)) seen.set(s.account.id, s.account);
    return [...seen.values()];
  }
}

// ============================================================================ tasks
class Tasks {
  constructor(host) {
    this.host = host;
    this.providers = new Map();           // type -> [{ext, provider}]
    this.executions = new Set();
    this.em = {};
    for (const k of ['start', 'end', 'startProcess', 'endProcess']) this.em[k] = new T.EventEmitter();
  }

  register(ext, type, provider) {
    const e = { ext, provider };
    if (!this.providers.has(type)) this.providers.set(type, []);
    this.providers.get(type).push(e);
    return new T.Disposable(() => { const l = this.providers.get(type) || []; const i = l.indexOf(e); if (i >= 0) l.splice(i, 1); });
  }

  async fetch(filter) {
    const type = filter && filter.type;
    if (type) await this.host.activateByEvent('onTaskType:' + type);
    const out = [];
    for (const [t, list] of this.providers) {
      if (type && t !== type) continue;
      for (const e of list) {
        try { const r = await e.provider.provideTasks(T.CancellationTokenNone); if (Array.isArray(r)) out.push(...r); } catch (err) { this.host.log(e.ext, 'task provider failed: ' + err); }
      }
    }
    return out;
  }

  async _resolve(task) {
    if (task.execution) return task;
    const list = this.providers.get(task.definition && task.definition.type) || [];
    for (const e of list) {
      if (typeof e.provider.resolveTask !== 'function') continue;
      try { const r = await e.provider.resolveTask(task, T.CancellationTokenNone); if (r && r.execution) return r; } catch (_) { /* */ }
    }
    return task;
  }

  async execute(ext, task) {
    task = await this._resolve(task);
    const ex = task.execution;
    const host = this.host;
    const execution = { task, terminate: () => {} };
    this.executions.add(execution);
    let term;
    if (ex instanceof T.CustomExecution || (ex && typeof ex.callback === 'function')) {
      const pty = await ex.callback(task.definition || {});
      term = host.terminalsSvc.create(ext, { name: task.name || 'Task', pty });
    } else if (ex && (ex.commandLine || ex.command || ex.process)) {
      const o = ex.options || {};
      const q = (a) => (typeof a === 'object' && a ? a.value : String(a));
      if (ex.process) {
        term = host.terminalsSvc.create(ext, { name: task.name || 'Task', shellPath: q(ex.process), shellArgs: (ex.args || []).map(q), cwd: o.cwd, env: o.env });
      } else {
        const line = ex.commandLine || [q(ex.command), ...(ex.args || []).map((a) => { const v = q(a); return /\s/.test(v) ? `"${v}"` : v; })].join(' ');
        const shell = (o.executable) || (process.platform === 'win32' ? (process.env.ComSpec || 'cmd.exe') : '/bin/sh');
        const args = o.shellArgs || (process.platform === 'win32' && /cmd(\.exe)?$/i.test(shell) ? ['/d', '/s', '/c', line] : ['-c', line]);
        term = host.terminalsSvc.create(ext, { name: task.name || 'Task', shellPath: shell, shellArgs: o.shellArgs ? [...args, line] : args, cwd: o.cwd, env: o.env });
      }
    } else {
      host.unsupported(ext, 'tasks.executeTask (task without execution)');
      this.executions.delete(execution);
      return execution;
    }
    execution.terminate = () => term.dispose();
    if (!(task.presentationOptions && task.presentationOptions.reveal === T.TaskRevealKind.Never)) term.show(true);
    this.em.start.fire({ execution });
    term.processId.then((pid) => { if (pid) this.em.startProcess.fire({ execution, processId: pid }); });
    const sub = host.terminalsSvc.em.close.event((t) => {
      if (t !== term) return;
      sub.dispose();
      this.executions.delete(execution);
      this.em.endProcess.fire({ execution, exitCode: t.exitStatus ? t.exitStatus.code : undefined });
      this.em.end.fire({ execution });
    });
    return execution;
  }
}

// ============================================================================ custom editors
class CustomEditors {
  constructor(host) { this.host = host; this.providers = new Map(); }

  register(ext, viewType, provider, options) {
    this.providers.set(viewType, { ext, provider, options: options || {} });
    return new T.Disposable(() => { if (this.providers.get(viewType)?.provider === provider) this.providers.delete(viewType); });
  }

  /** viewType whose contributes.customEditors selector matches the file (priority default) */
  viewTypeFor(uri) {
    for (const ext of this.host.extensions.values()) {
      for (const ce of ((ext.packageJSON.contributes || {}).customEditors || [])) {
        if (!ce || !ce.viewType || ce.priority === 'option') continue;
        const { matchGlob } = require('./glob');
        if ((ce.selector || []).some((s) => s && s.filenamePattern && matchGlob(s.filenamePattern.includes('/') ? s.filenamePattern : '**/' + s.filenamePattern, uri.fsPath))) return ce.viewType;
      }
    }
    return undefined;
  }

  async open(uri, viewType, column) {
    if (!this.providers.has(viewType)) await this.host.activateByEvent('onCustomEditor:' + viewType);
    const e = this.providers.get(viewType);
    if (!e) return false;
    const host = this.host;
    const title = path.basename(uri.fsPath || uri.path);
    const panel = host.webviews.createPanel(e.ext, viewType, title, column || T.ViewColumn.One, Object.assign({ enableScripts: true }, e.options.webviewOptions || {}));
    host.tabs.custom.set(panel._handle, { uri, viewType });
    host.tabs.setActive('webview:' + panel._handle);
    panel.onDidDispose(() => { host.tabs.custom.delete(panel._handle); host.tabs.changed(); });
    const cts = new T.CancellationTokenSource();
    try {
      if (typeof e.provider.resolveCustomTextEditor === 'function') {
        const doc = await host.openTextDocument(uri);
        await e.provider.resolveCustomTextEditor(doc, panel, cts.token);
      } else {
        const doc = await e.provider.openCustomDocument(uri, { backupId: undefined, untitledDocumentData: undefined }, cts.token);
        panel.onDidDispose(() => { try { doc.dispose && doc.dispose(); } catch (_) { /* */ } });
        await e.provider.resolveCustomEditor(doc, panel, cts.token);
      }
    } catch (err) { host.log(e.ext, `custom editor ${viewType} failed: ${err && err.stack || err}`); }
    host.tabs.changed();
    return true;
  }
}

// ============================================================================ notebooks (data model, no notebook UI)
class Notebooks {
  constructor(host) {
    this.host = host;
    this.serializers = new Map();      // notebookType -> {ext, serializer, options}
    this.docs = new Map();
    this.em = { open: new T.EventEmitter(), close: new T.EventEmitter(), change: new T.EventEmitter(), save: new T.EventEmitter() };
    this._n = 0;
  }

  registerSerializer(ext, type, serializer, options) {
    this.serializers.set(type, { ext, serializer, options: options || {} });
    return new T.Disposable(() => { if (this.serializers.get(type)?.serializer === serializer) this.serializers.delete(type); });
  }

  typeFor(uri) {
    for (const ext of this.host.extensions.values()) {
      for (const nb of ((ext.packageJSON.contributes || {}).notebooks || [])) {
        const { matchGlob } = require('./glob');
        if (nb && nb.type && (nb.selector || []).some((s) => s && s.filenamePattern && matchGlob(s.filenamePattern.includes('/') ? s.filenamePattern : '**/' + s.filenamePattern, uri.fsPath || uri.path))) return nb.type;
      }
    }
    return undefined;
  }

  _make(uri, type, data) {
    const host = this.host;
    const nb = {
      uri, notebookType: type, version: 1, isDirty: false, isUntitled: uri.scheme === 'untitled', isClosed: false,
      metadata: (data && data.metadata) || {}, _cells: [],
      get cellCount() { return this._cells.length; },
      cellAt(i) { return this._cells[i]; },
      getCells(range) { return range ? this._cells.slice(range.start, range.end) : [...this._cells]; },
      save: () => this.save(nb),
    };
    (data && data.cells || []).forEach((c, i) => {
      const cellUri = T.Uri.from({ scheme: 'vscode-notebook-cell', path: uri.path, fragment: 'C' + i });
      const doc = host.docs.open(cellUri, c.languageId || 'plaintext', 1, c.value || '');
      nb._cells.push({ index: i, notebook: nb, kind: c.kind, document: doc, metadata: c.metadata || {}, outputs: c.outputs || [], executionSummary: c.executionSummary });
    });
    this.docs.set(uri.toString(), nb);
    this.em.open.fire(nb);
    return nb;
  }

  async open(a, b) {
    if (T.Uri.isUri(a)) {
      const ex = this.docs.get(a.toString());
      if (ex) return ex;
      const type = this.typeFor(a);
      if (!type) throw new Error(`No notebook serializer is registered for ${a.toString()}`);
      if (!this.serializers.has(type)) await this.host.activateByEvent('onNotebook:' + type);
      const s = this.serializers.get(type);
      if (!s) throw new Error(`No notebook serializer is registered for the notebook type '${type}'`);
      const bytes = a.scheme === 'file' ? new Uint8Array(await require('fs').promises.readFile(a.fsPath)) : await this.host.fsApi.readFile(a);
      const data = await s.serializer.deserializeNotebook(bytes, T.CancellationTokenNone);
      return this._make(a, type, data);
    }
    const type = String(a);
    if (!this.serializers.has(type)) await this.host.activateByEvent('onNotebook:' + type);
    return this._make(T.Uri.from({ scheme: 'untitled', path: 'Untitled-' + (++this._n) + '.ipynb' }), type, b || { cells: [] });
  }

  async save(nb) {
    const s = this.serializers.get(nb.notebookType);
    if (!s || nb.isUntitled) return false;
    const data = { metadata: nb.metadata, cells: nb._cells.map((c) => ({ kind: c.kind, value: c.document.getText(), languageId: c.document.languageId, outputs: c.outputs, metadata: c.metadata })) };
    const bytes = await s.serializer.serializeNotebook(data, T.CancellationTokenNone);
    await this.host.fsApi.writeFile(nb.uri, bytes);
    nb.isDirty = false;
    this.em.save.fire(nb);
    return true;
  }

  controller(ext, id, notebookType, label, handler) {
    const em = new T.EventEmitter();
    let order = 0;
    const ctrl = {
      id, notebookType, label, description: undefined, detail: undefined, supportedLanguages: undefined, supportsExecutionOrder: false,
      executeHandler: handler, interruptHandler: undefined, onDidChangeSelectedNotebooks: em.event,
      createNotebookCellExecution(cell) {
        return {
          cell, token: T.CancellationTokenNone, executionOrder: undefined,
          start() { this.executionOrder = this.executionOrder || ++order; },
          end(success, endTime) { cell.executionSummary = { executionOrder: this.executionOrder, success, timing: endTime ? { startTime: 0, endTime } : undefined }; },
          clearOutput() { cell.outputs = []; return Promise.resolve(); },
          replaceOutput(o) { cell.outputs = Array.isArray(o) ? o : [o]; return Promise.resolve(); },
          appendOutput(o) { cell.outputs = cell.outputs.concat(Array.isArray(o) ? o : [o]); return Promise.resolve(); },
          replaceOutputItems() { return Promise.resolve(); }, appendOutputItems() { return Promise.resolve(); },
        };
      },
      updateNotebookAffinity() {}, dispose() { em.dispose(); },
    };
    void ext;
    return ctrl;
  }
}

// ============================================================================ objects without UI in RAD IDE
function commentController(id, label) {
  const threads = new Set();
  return {
    id, label, options: undefined, commentingRangeProvider: undefined, reactionHandler: undefined,
    createCommentThread(uri, range, comments) {
      const t = {
        uri, range, comments: comments || [], collapsibleState: T.CommentThreadCollapsibleState.Collapsed, canReply: true,
        contextValue: undefined, label: undefined, state: T.CommentThreadState.Unresolved,
        dispose() { threads.delete(t); },
      };
      threads.add(t);
      return t;
    },
    dispose() { threads.clear(); },
    get _threads() { return [...threads]; },
  };
}

function testController(id, label) {
  const makeCollection = (parent) => {
    const map = new Map();
    return {
      get size() { return map.size; },
      replace(items) { map.clear(); for (const i of items || []) { i.parent = parent; map.set(i.id, i); } },
      forEach(cb, thisArg) { map.forEach((v) => cb.call(thisArg, v, this)); },
      add(i) { i.parent = parent; map.set(i.id, i); }, delete(itemId) { map.delete(itemId); }, get(itemId) { return map.get(itemId); },
      [Symbol.iterator]() { return map.entries(); },
    };
  };
  const ctrl = {
    id, label, items: makeCollection(undefined), resolveHandler: undefined, refreshHandler: undefined,
    createTestItem(itemId, itemLabel, uri) {
      const item = { id: itemId, label: itemLabel, uri, canResolveChildren: false, busy: false, tags: [], description: undefined, sortText: undefined, range: undefined, error: undefined, parent: undefined };
      item.children = makeCollection(item);
      return item;
    },
    createRunProfile(profileLabel, kind, runHandler, isDefault, tag, supportsContinuousRun) {
      return { label: profileLabel, kind, runHandler, isDefault: !!isDefault, tag, supportsContinuousRun: !!supportsContinuousRun, configureHandler: undefined, loadDetailedCoverage: undefined, onDidChangeDefault: () => new T.Disposable(() => {}), dispose() {} };
    },
    createTestRun(request, name, persist) {
      return { name, token: T.CancellationTokenNone, isPersisted: persist !== false, onDidDispose: () => new T.Disposable(() => {}),
        enqueued() {}, started() {}, skipped() {}, failed() {}, errored() {}, passed() {}, appendOutput() {}, addCoverage() {}, end() {} };
    },
    invalidateTestResults() {}, dispose() {},
  };
  return ctrl;
}

function sourceControl(id, label, rootUri) {
  const groups = [];
  return {
    id, label, rootUri, count: undefined, quickDiffProvider: undefined, commitTemplate: undefined, acceptInputCommand: undefined, statusBarCommands: undefined,
    inputBox: { value: '', placeholder: '', enabled: true, visible: true },
    createResourceGroup(gid, glabel) {
      const g = { id: gid, label: glabel, hideWhenEmpty: undefined, resourceStates: [], contextValue: undefined, dispose() { const i = groups.indexOf(g); if (i >= 0) groups.splice(i, 1); } };
      groups.push(g);
      return g;
    },
    dispose() { groups.length = 0; },
  };
}

function chatParticipant(id, handler) {
  const fb = new T.EventEmitter();
  return { id, iconPath: undefined, requestHandler: handler, followupProvider: undefined, onDidReceiveFeedback: fb.event, dispose() { fb.dispose(); } };
}

module.exports = { UriHandlers, FileDecorations, Authentication, Tasks, CustomEditors, Notebooks, commentController, testController, sourceControl, chatParticipant, decode };
