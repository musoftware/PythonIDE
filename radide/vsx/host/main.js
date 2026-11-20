'use strict';
// RAD IDE extension host: runs the JavaScript of VS Code extensions (package.json "main") in Node.
//
//   node main.js            (started by radide/vsx/bridge.py; JSON-RPC with Content-Length framing on stdio)
//
// * require('vscode') inside an extension returns that extension's API object (api.js) - a practical
//   subset of the VS Code API; anything missing fails softly (logged once to "Extension Host").
// * The IDE feeds documents / editors / settings in, and asks for language features in LSP shape
//   (method "lsp"), commands, debug adapters ...; the host asks the IDE for UI (messages, quick picks,
//   status bar items, output channels, edits ...). The full protocol is described in bridge.py.
// * Extensions write to stdout freely: stdout / console are redirected to stderr (logged by the IDE).

const realStdoutWrite = process.stdout.write.bind(process.stdout);
process.stdout.write = function (chunk, encoding, cb) { return process.stderr.write(chunk, encoding, cb); };
for (const k of ['log', 'info', 'debug', 'trace']) console[k] = (...a) => process.stderr.write(require('util').format(...a) + '\n');
console.warn = (...a) => process.stderr.write('[warn] ' + require('util').format(...a) + '\n');
console.error = (...a) => process.stderr.write('[error] ' + require('util').format(...a) + '\n');

const crypto = require('crypto');
const fs = require('fs');
const Module = require('module');
const os = require('os');
const path = require('path');

const T = require('./types');
const C = require('./convert');
const { Rpc } = require('./rpc');
const { DocumentStore } = require('./documents');
const { createApi, createContext, selectorScore, serializeSelector } = require('./api');
const { matchGlob, globToRegExp } = require('./glob');
const { Debug } = require('./debug');

const PROVIDER_TIMEOUT = 5000;

function withTimeout(promise, ms, dflt) {
  return new Promise((resolve) => {
    let done = false;
    const t = setTimeout(() => { if (!done) { done = true; resolve(dflt); } }, ms);
    Promise.resolve(promise).then((v) => { if (!done) { done = true; clearTimeout(t); resolve(v); } },
      () => { if (!done) { done = true; clearTimeout(t); resolve(dflt); } });
  });
}

function deepClone(v) { return v === undefined ? undefined : JSON.parse(JSON.stringify(v)); }

function setPath(tree, key, value) {
  const parts = key.split('.');
  let o = tree;
  for (let i = 0; i < parts.length - 1; i++) {
    if (!o[parts[i]] || typeof o[parts[i]] !== 'object' || Array.isArray(o[parts[i]])) o[parts[i]] = {};
    o = o[parts[i]];
  }
  const last = parts[parts.length - 1];
  if (value && typeof value === 'object' && !Array.isArray(value) && o[last] && typeof o[last] === 'object' && !Array.isArray(o[last])) {
    o[last] = Object.assign({}, o[last], value);
  } else o[last] = value;
}

function getPath(tree, key) {
  if (!key) return tree;
  let o = tree;
  for (const part of key.split('.')) {
    if (o === undefined || o === null || typeof o !== 'object') return undefined;
    o = o[part];
  }
  return o;
}

// ============================================================================ Host
class Host {
  constructor() {
    this.rpc = new Rpc(process.stdin, realStdoutWrite);
    this.docs = new DocumentStore();
    this.docs.saveHandler = (doc) => this.rpc.request('workspace/save', { path: doc.uri.fsPath }).then((r) => !!r);
    this.apiVersion = '1.90.0';
    this.extensions = new Map();          // id (lower) -> ext record
    this.commands = new Map();            // id -> {ext, callback, thisArg}
    this.providers = [];                  // {id, ext, kind, selector, provider, triggers, metadata}
    this.collections = new Set();
    this.mementos = [];
    this.contentProviders = new Map();
    this.watchers = new Set();
    this.trees = new Map();
    this.cmdCache = new C.CommandCache();
    this.events = {};
    for (const k of ['activeEditor', 'visibleEditors', 'selection', 'windowState', 'terminalOpen', 'terminalClose', 'theme',
      'workspaceFolders', 'createFiles', 'deleteFiles', 'renameFiles', 'configuration', 'diagnostics', 'extensions']) this.events[k] = new T.EventEmitter();
    this.debug = new Debug(this);
    this._folders = [];
    this._settings = {};
    this._configDefaults = {};
    this._editors = new Map();            // uri -> TextEditor
    this._active = null;
    this._unsupported = new Set();
    this._outputs = new Map();
    this._status = new Map();
    this._terminals = new Map();
    this._n = 0;
    this._providersTimer = null;
    this.storageRoot = path.join(os.homedir(), '.radide-vsx');
    this.appRoot = path.resolve(__dirname, '..', '..');
    this.uiLanguage = 'en';
    this.themeKind = T.ColorThemeKind.Dark;
    this.machineId = crypto.createHash('sha256').update(os.hostname() + os.userInfo().username).digest('hex');
    this.sessionId = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
    this.ideLanguages = [];
    this.fsApi = this._makeFs();
    this._installRequireHook();
    this._registerHandlers();
    process.on('uncaughtException', (e) => this.logHost('uncaught exception: ' + (e && e.stack || e)));
    process.on('unhandledRejection', (e) => this.logHost('unhandled rejection: ' + (e && e.stack || e)));
  }

  // -------------------------------------------------------------------------- logging
  logHost(text) { this.rpc.notify('output/append', { channel: 'Extension Host', text: String(text) + '\n' }); }
  log(ext, text) { this.logHost(`[${ext ? ext.id : 'host'}] ${text}`); }
  unsupported(ext, name) {
    const key = (ext ? ext.id : '') + '|' + name;
    if (this._unsupported.has(key)) return;
    this._unsupported.add(key);
    this.log(ext, `${name} is not supported by RAD IDE (ignored)`);
    this.rpc.notify('host/unsupported', { ext: ext ? ext.id : '', api: name });
  }

  // -------------------------------------------------------------------------- require('vscode')
  _installRequireHook() {
    const host = this;
    const origLoad = Module._load;
    Module._load = function (request, parent, isMain) {
      if (request === 'vscode') {
        const ext = host._extForFile(parent && parent.filename) || host._activating || host._anyExt();
        if (!ext) throw new Error("Cannot find module 'vscode'");
        if (!ext.api) ext.api = createApi(host, ext);
        return ext.api;
      }
      return origLoad.apply(this, arguments);
    };
  }

  _extForFile(file) {
    if (!file) return null;
    const f = path.resolve(file).toLowerCase();
    let best = null;
    for (const ext of this.extensions.values()) {
      const p = ext.path.toLowerCase() + path.sep;
      if (f.startsWith(p) && (!best || p.length > best.path.length)) best = ext;
    }
    return best;
  }

  _anyExt() { return this.extensions.values().next().value || null; }

  // -------------------------------------------------------------------------- extensions
  extensionList() { return [...this.extensions.values()]; }

  extensionApiObject(id) {
    if (!id) return undefined;
    const ext = this.extensions.get(String(id).toLowerCase());
    if (!ext) return undefined;
    if (!ext.apiObject) {
      const host = this;
      ext.apiObject = {
        id: ext.idOriginal, extensionUri: T.Uri.file(ext.path), extensionPath: ext.path, packageJSON: ext.packageJSON,
        extensionKind: T.ExtensionKind.Workspace,
        get isActive() { return ext.active; },
        get exports() { return ext.exports; },
        activate: () => host.activate(ext, 'api').then(() => ext.exports),
      };
    }
    return ext.apiObject;
  }

  _activationEvents(ext) {
    const pj = ext.packageJSON;
    const ev = new Set(pj.activationEvents || []);
    const c = pj.contributes || {};
    for (const cmd of c.commands || []) if (cmd && cmd.command) ev.add('onCommand:' + cmd.command);
    for (const l of c.languages || []) if (l && l.id) ev.add('onLanguage:' + l.id);
    for (const d of c.debuggers || []) if (d && d.type) ev.add('onDebugResolve:' + d.type);
    for (const views of Object.values(c.views || {})) for (const v of views || []) if (v && v.id) ev.add('onView:' + v.id);
    for (const ce of c.customEditors || []) if (ce && ce.viewType) ev.add('onCustomEditor:' + ce.viewType);
    for (const a of c.authentication || []) if (a && a.id) ev.add('onAuthenticationRequest:' + a.id);
    return ev;
  }

  async activateByEvent(event) {
    const todo = [];
    for (const ext of this.extensions.values()) {
      if (ext.active || ext.failed || !ext.main) continue;
      if (ext.events.has(event) || (event.startsWith('onLanguage:') && ext.events.has('onLanguage'))) todo.push(ext);
    }
    await Promise.all(todo.map((e) => this.activate(e, event)));
  }

  activate(ext, reason) {
    if (ext.activation) return ext.activation;
    ext.activation = (async () => {
      for (const dep of ext.packageJSON.extensionDependencies || []) {
        const d = this.extensions.get(String(dep).toLowerCase());
        if (d && d.main) await this.activate(d, 'dependency of ' + ext.id);
      }
      const started = Date.now();
      try {
        this._activating = ext;
        let mod;
        try { mod = require(ext.main); } finally { this._activating = null; }
        ext.module = mod;
        ext.context = createContext(this, ext);
        if (mod && typeof mod.activate === 'function') {
          this._activating = ext;
          let r;
          try { r = mod.activate(ext.context); } finally { this._activating = null; }
          ext.exports = await withTimeout(Promise.resolve(r), 60000, undefined);
        }
        ext.active = true;
        this.log(ext, `activated (${reason}) in ${Date.now() - started} ms`);
        this.rpc.notify('extension/activated', { id: ext.id, reason, ms: Date.now() - started });
        this.events.extensions.fire();
      } catch (e) {
        ext.failed = String(e && e.stack || e);
        this.log(ext, 'activation failed: ' + ext.failed);
        this.rpc.notify('extension/activationFailed', { id: ext.id, error: String(e && e.message || e), stack: ext.failed });
      }
    })();
    return ext.activation;
  }

  async deactivateAll() {
    for (const ext of this.extensions.values()) {
      if (!ext.active) continue;
      try {
        if (ext.module && typeof ext.module.deactivate === 'function') await withTimeout(ext.module.deactivate(), 4000);
      } catch (e) { this.log(ext, 'deactivate failed: ' + e); }
      for (const d of (ext.context && ext.context.subscriptions) || []) { try { d && d.dispose && d.dispose(); } catch (_) { /* */ } }
    }
    for (const m of this.mementos) m.flush();
    this.debug.dispose();
    for (const w of this.watchers) w.dispose();
  }

  l10nBundle(ext) {
    if (ext.l10n !== undefined) return ext.l10n;
    ext.l10n = null;
    const dir = ext.packageJSON.l10n ? path.join(ext.path, ext.packageJSON.l10n) : null;
    if (dir && this.uiLanguage !== 'en') {
      for (const lang of [this.uiLanguage, this.uiLanguage.split('-')[0]]) {
        const f = path.join(dir, `bundle.l10n.${lang}.json`);
        try { ext.l10n = JSON.parse(fs.readFileSync(f, 'utf8')); break; } catch (_) { /* */ }
      }
    }
    return ext.l10n;
  }

  // -------------------------------------------------------------------------- commands
  registerCommand(ext, id, callback, thisArg) {
    if (this.commands.has(id)) this.log(ext, `command '${id}' already exists (replaced)`);
    this.commands.set(id, { ext, callback, thisArg });
    this.rpc.notify('commands/registered', { id, ext: ext.id });
    return new T.Disposable(() => {
      const c = this.commands.get(id);
      if (c && c.callback === callback) { this.commands.delete(id); this.rpc.notify('commands/unregistered', { id }); }
    });
  }

  async executeCommand(id, args, ext) {
    args = args || [];
    if (!this.commands.has(id)) await this.activateByEvent('onCommand:' + id);
    const c = this.commands.get(id);
    if (c) return c.callback.apply(c.thisArg, args);
    const builtin = await this._builtinCommand(id, args);
    if (builtin !== undefined) return builtin === null ? undefined : builtin;
    const r = await this.rpc.request('commands/executeIde', { command: id, args: C.plain(args) });
    void ext;
    return r === null ? undefined : r;
  }

  async _builtinCommand(id, args) {
    switch (id) {
      case 'setContext':
        this.rpc.notify('context/set', { key: args[0], value: C.plain(args[1]) });
        return null;
      case 'vscode.open': {
        const uri = T.Uri.isUri(args[0]) ? args[0] : C.uriFromIde(String(args[0]));
        if (uri.scheme === 'http' || uri.scheme === 'https' || uri.scheme === 'mailto') {
          await this.rpc.request('env/openExternal', { uri: uri.toString(true) });
        } else await this.showTextDocument(uri, args[1]);
        return null;
      }
      case 'vscode.openWith': await this.showTextDocument(args[0]); return null;
      case 'workbench.action.files.save': {
        const ed = this.activeEditor();
        if (ed) await this.rpc.request('workspace/save', { path: ed.document.uri.fsPath });
        return null;
      }
      case 'vscode.executeCompletionItemProvider': {
        const doc = await this.openTextDocument(args[0]);
        const r = await this._lspCompletion(doc, args[1]);
        return new T.CompletionList((r.items || []).map((i) => new T.CompletionItem(i.label, (i.kind || 1) - 1)), r.isIncomplete);
      }
      case 'vscode.executeHoverProvider': {
        const doc = await this.openTextDocument(args[0]);
        return this._collect('hover', doc, (p, tok) => p.provideHover(doc, args[1], tok));
      }
      case 'vscode.executeDefinitionProvider': {
        const doc = await this.openTextDocument(args[0]);
        return (await this._collect('definition', doc, (p, tok) => p.provideDefinition(doc, args[1], tok))).flat();
      }
      case 'vscode.executeFormatDocumentProvider': {
        const doc = await this.openTextDocument(args[0]);
        const p = this._providersFor('formatting', doc)[0];
        return p ? p.provider.provideDocumentFormattingEdits(doc, args[1] || { tabSize: 4, insertSpaces: true }, T.CancellationTokenNone) : [];
      }
      case 'vscode.executeDocumentSymbolProvider': {
        const doc = await this.openTextDocument(args[0]);
        return (await this._collect('documentSymbol', doc, (p, tok) => p.provideDocumentSymbols(doc, tok))).flat();
      }
      default: return undefined;
    }
  }

  getCommands(filterInternal) {
    const ids = [...this.commands.keys()];
    return Promise.resolve(filterInternal ? ids.filter((i) => !i.startsWith('_')) : ids.concat(['setContext', 'vscode.open']));
  }

  // -------------------------------------------------------------------------- window: messages / pickers
  async showMessage(severity, { message, options, items }) {
    const titles = items.map((i) => (typeof i === 'string' ? i : (i && i.title) || ''));
    const ext = this._activatingName();
    const idx = await this.rpc.request('window/showMessage', { severity, message, detail: options.detail || '', modal: !!options.modal, items: titles, source: ext });
    return typeof idx === 'number' && idx >= 0 && idx < items.length ? items[idx] : undefined;
  }

  _activatingName() { return ''; }

  async showQuickPick(items, options, token) {
    items = await items;
    if (!items || !items.length) return undefined;
    const isStr = typeof items[0] === 'string';
    const list = items.map((i) => (typeof i === 'string' ? { label: i } : { label: i.label, description: i.description, detail: i.detail, picked: !!i.picked, kind: i.kind }));
    const req = this.rpc.request('window/showQuickPick', { items: list, canPickMany: !!options.canPickMany, placeHolder: options.placeHolder || '', title: options.title || '', matchOnDescription: !!options.matchOnDescription, matchOnDetail: !!options.matchOnDetail });
    const res = await (token ? Promise.race([req, new Promise((r) => token.onCancellationRequested(() => r(null)))]) : req);
    if (res === null || res === undefined) return undefined;
    if (options.canPickMany) return (Array.isArray(res) ? res : [res]).map((i) => items[i]).filter((x) => x !== undefined);
    const picked = items[Array.isArray(res) ? res[0] : res];
    if (picked !== undefined && options.onDidSelectItem) { try { options.onDidSelectItem(picked); } catch (_) { /* */ } }
    void isStr;
    return picked;
  }

  async showInputBox(options, token) {
    let value = options.value || '';
    let message = '';
    for (let i = 0; i < 20; i++) {
      const req = this.rpc.request('window/showInputBox', { value, prompt: options.prompt || '', placeHolder: options.placeHolder || '', password: !!options.password, title: options.title || '', validationMessage: message });
      const r = await (token ? Promise.race([req, new Promise((res) => token.onCancellationRequested(() => res(null)))]) : req);
      if (r === null || r === undefined) return undefined;
      if (typeof options.validateInput !== 'function') return r;
      let v = await options.validateInput(r);
      if (v && typeof v === 'object') v = v.message;
      if (!v) return r;
      value = r; message = String(v);
    }
    return undefined;
  }

  createQuickPick(ext) {
    const host = this;
    const em = { accept: new T.EventEmitter(), hide: new T.EventEmitter(), value: new T.EventEmitter(), active: new T.EventEmitter(), selection: new T.EventEmitter(), button: new T.EventEmitter(), itemButton: new T.EventEmitter() };
    const qp = {
      items: [], activeItems: [], selectedItems: [], value: '', placeholder: '', title: '', busy: false, enabled: true,
      ignoreFocusOut: false, canSelectMany: false, matchOnDescription: false, matchOnDetail: false, keepScrollPosition: false, buttons: [], step: undefined, totalSteps: undefined, sortByLabel: true,
      onDidAccept: em.accept.event, onDidHide: em.hide.event, onDidChangeValue: em.value.event, onDidChangeActive: em.active.event,
      onDidChangeSelection: em.selection.event, onDidTriggerButton: em.button.event, onDidTriggerItemButton: em.itemButton.event,
      _shown: false,
      async show() {
        if (this._shown) return;
        this._shown = true;
        for (let i = 0; i < 60 && (!this.items || !this.items.length); i++) await new Promise((r) => setTimeout(r, 50));
        const res = await host.rpc.request('window/showQuickPick', { items: (this.items || []).map((x) => ({ label: x.label, description: x.description, detail: x.detail, picked: !!x.picked, kind: x.kind })), canPickMany: !!this.canSelectMany, placeHolder: this.placeholder || '', title: this.title || '', value: this.value || '' });
        this._shown = false;
        if (res !== null && res !== undefined) {
          const sel = (Array.isArray(res) ? res : [res]).map((i) => this.items[i]).filter(Boolean);
          this.selectedItems = sel; this.activeItems = sel;
          em.active.fire(sel); em.selection.fire(sel); em.accept.fire();
        }
        em.hide.fire();
      },
      hide() {}, dispose() { Object.values(em).forEach((e) => e.dispose()); },
    };
    void ext;
    return qp;
  }

  createInputBox(ext) {
    const host = this;
    const em = { accept: new T.EventEmitter(), hide: new T.EventEmitter(), value: new T.EventEmitter(), button: new T.EventEmitter() };
    const ib = {
      value: '', placeholder: '', prompt: '', password: false, title: '', busy: false, enabled: true, ignoreFocusOut: false, validationMessage: undefined, buttons: [], valueSelection: undefined,
      onDidAccept: em.accept.event, onDidHide: em.hide.event, onDidChangeValue: em.value.event, onDidTriggerButton: em.button.event,
      async show() {
        const r = await host.rpc.request('window/showInputBox', { value: this.value || '', prompt: this.prompt || '', placeHolder: this.placeholder || '', password: !!this.password, title: this.title || '', validationMessage: typeof this.validationMessage === 'string' ? this.validationMessage : '' });
        if (r !== null && r !== undefined) { this.value = r; em.value.fire(r); em.accept.fire(); }
        em.hide.fire();
      },
      hide() {}, dispose() { Object.values(em).forEach((e) => e.dispose()); },
    };
    void ext;
    return ib;
  }

  // -------------------------------------------------------------------------- window: output / status bar / progress
  createOutputChannel(ext, name, options) {
    const host = this;
    const log = options && typeof options === 'object' && options.log;
    const send = (method, extra) => host.rpc.notify(method, { channel: name, ...extra });
    const ch = {
      name,
      append: (v) => send('output/append', { text: String(v) }),
      appendLine: (v) => send('output/append', { text: String(v) + '\n' }),
      replace: (v) => send('output/replace', { text: String(v) }),
      clear: () => send('output/clear', {}),
      show: (a, b) => send('output/show', { preserveFocus: typeof a === 'boolean' ? a : !!b }),
      hide: () => {},
      dispose: () => {},
    };
    if (log) {
      const L = (lvl) => (msg, ...args) => {
        const text = msg instanceof Error ? (msg.stack || msg.message) : require('util').format(msg, ...args);
        ch.appendLine(`${new Date().toISOString().replace('T', ' ').substring(0, 23)} [${lvl}] ${text}`);
      };
      Object.assign(ch, { logLevel: T.LogLevel.Info, onDidChangeLogLevel: () => new T.Disposable(() => {}), trace: L('trace'), debug: L('debug'), info: L('info'), warn: L('warning'), error: L('error') });
    }
    send('output/create', { ext: ext ? ext.id : '' });
    return ch;
  }

  createStatusBarItem(ext, a, b, c) {
    const host = this;
    let id; let alignment; let priority;
    if (typeof a === 'string') { id = a; alignment = b; priority = c; } else { alignment = a; priority = b; }
    const key = (ext ? ext.id : 'host') + ':' + (id || ('item' + (++this._n)));
    const state = { id: key, alignment: alignment || T.StatusBarAlignment.Left, priority: priority || 0, text: '', tooltip: '', command: undefined, color: undefined, backgroundColor: undefined, name: '', visible: false };
    let timer = null;
    const push = () => {
      if (timer) return;
      timer = setImmediate(() => {
        timer = null;
        const cmd = state.command ? (typeof state.command === 'string' ? { command: state.command } : this.cmdCache.put(state.command)) : undefined;
        const color = state.color && typeof state.color === 'object' ? state.color.id : state.color;
        const bg = state.backgroundColor && typeof state.backgroundColor === 'object' ? state.backgroundColor.id : state.backgroundColor;
        host.rpc.notify('statusBar/set', { id: key, ext: ext ? ext.id : '', alignment: state.alignment, priority: state.priority, text: state.text, tooltip: C.markdownText(state.tooltip), command: cmd, color, backgroundColor: bg, name: state.name, visible: state.visible });
      });
    };
    const item = {
      get id() { return key; }, get alignment() { return state.alignment; }, get priority() { return state.priority; },
      show() { state.visible = true; push(); }, hide() { state.visible = false; push(); },
      dispose() { state.visible = false; host.rpc.notify('statusBar/remove', { id: key }); },
      accessibilityInformation: undefined,
    };
    for (const prop of ['text', 'tooltip', 'command', 'color', 'backgroundColor', 'name']) {
      Object.defineProperty(item, prop, { get: () => state[prop], set: (v) => { state[prop] = v; push(); }, enumerable: true });
    }
    return item;
  }

  createLanguageStatusItem(ext, id, selector) {
    const item = this.createStatusBarItem(ext, 'lang:' + id, T.StatusBarAlignment.Right, 0);
    const wrapper = { id, selector, severity: T.LanguageStatusSeverity.Information, detail: '', busy: false, accessibilityInformation: undefined, dispose: () => item.dispose() };
    for (const prop of ['text', 'command', 'name']) Object.defineProperty(wrapper, prop, { get: () => item[prop], set: (v) => { item[prop] = v; item.show(); }, enumerable: true });
    return wrapper;
  }

  async withProgress(ext, options, task) {
    const id = 'p' + (++this._n);
    const title = options.title || '';
    this.rpc.notify('window/progress', { id, op: 'start', title, location: options.location, cancellable: !!options.cancellable, ext: ext ? ext.id : '' });
    const cts = new T.CancellationTokenSource();
    this._progress = this._progress || new Map();
    this._progress.set(id, cts);
    try {
      return await task({ report: (v) => this.rpc.notify('window/progress', { id, op: 'report', message: v && v.message, increment: v && v.increment }) }, cts.token);
    } finally {
      this._progress.delete(id);
      this.rpc.notify('window/progress', { id, op: 'end' });
    }
  }

  // -------------------------------------------------------------------------- editors
  _editorFor(doc) {
    const key = doc.uri.toString();
    let ed = this._editors.get(key);
    if (!ed || ed.document !== doc) { ed = new TextEditor(this, doc); this._editors.set(key, ed); }
    return ed;
  }

  activeEditor() { return this._active && !this._active.document.isClosed ? this._active : undefined; }
  visibleEditors() { const a = this.activeEditor(); return a ? [a] : []; }

  editBuilder(ed) {
    const we = new T.WorkspaceEdit();
    const uri = ed.document.uri;
    const edit = {
      replace: (loc, text) => we.replace(uri, loc instanceof T.Position ? new T.Range(loc, loc) : loc, text),
      insert: (p, text) => we.insert(uri, p, text),
      delete: (r) => we.delete(uri, r),
      setEndOfLine: () => {},
    };
    return { edit, apply: () => this.applyEdit(we) };
  }

  async showTextDocument(docOrUri, columnOrOptions, preserveFocus) {
    let doc = docOrUri;
    if (!doc) return undefined;
    if (T.Uri.isUri(doc)) doc = await this.openTextDocument(doc);
    const opts = columnOrOptions && typeof columnOrOptions === 'object' ? columnOrOptions : { preserveFocus };
    const sel = opts.selection ? [opts.selection.start.line, opts.selection.start.character, opts.selection.end.line, opts.selection.end.character] : null;
    await this.rpc.request('window/showTextDocument', { path: doc.uri.scheme === 'file' ? doc.uri.fsPath : null, uri: doc.uri.toString(), languageId: doc.languageId, content: doc.uri.scheme === 'file' ? undefined : doc.getText(), selection: sel, preserveFocus: !!opts.preserveFocus, preview: opts.preview !== false });
    const ed = this._editorFor(this.docs.get(doc.uri) || doc);
    if (!opts.preserveFocus) { this._active = ed; }
    return ed;
  }

  createDecorationType(ext, options) {
    const key = 'vsxdeco' + (++this._n);
    const o = {};
    const pick = (src) => {
      const out = {};
      for (const k of ['backgroundColor', 'color', 'border', 'borderColor', 'borderStyle', 'borderWidth', 'borderRadius', 'outline', 'fontStyle', 'fontWeight', 'textDecoration', 'opacity', 'isWholeLine', 'overviewRulerColor', 'cursor', 'letterSpacing']) {
        if (src[k] !== undefined) out[k] = src[k] && typeof src[k] === 'object' && src[k].id ? `var(--vscode-${String(src[k].id).replace(/\./g, '-')})` : src[k];
      }
      for (const k of ['before', 'after']) if (src[k]) out[k] = { contentText: src[k].contentText, color: src[k].color && src[k].color.id ? undefined : src[k].color, margin: src[k].margin, fontStyle: src[k].fontStyle };
      return out;
    };
    Object.assign(o, pick(options || {}));
    if (options && options.dark) o.dark = pick(options.dark);
    if (options && options.light) o.light = pick(options.light);
    this.rpc.notify('decorations/type', { key, options: o, ext: ext ? ext.id : '' });
    return { key, dispose: () => this.rpc.notify('decorations/disposeType', { key }) };
  }

  tabGroups() {
    const docs = this.docs.all().filter((d) => d.uri.scheme === 'file');
    const active = this.activeEditor();
    const tabs = docs.map((d) => ({ label: path.basename(d.fileName), input: new T.TabInputText(d.uri), isActive: !!active && active.document === d, isDirty: d.isDirty, isPinned: false, isPreview: false, group: null }));
    const group = { isActive: true, viewColumn: 1, activeTab: tabs.find((t) => t.isActive), tabs };
    tabs.forEach((t) => { t.group = group; });
    this._tabEvents = this._tabEvents || { tabs: new T.EventEmitter(), groups: new T.EventEmitter() };
    return { all: [group], activeTabGroup: group, onDidChangeTabs: this._tabEvents.tabs.event, onDidChangeTabGroups: this._tabEvents.groups.event, close: () => Promise.resolve(false) };
  }

  // -------------------------------------------------------------------------- terminals
  createTerminal(ext, a, b, c) {
    const id = 'term' + (++this._n);
    let options = {};
    if (typeof a === 'string' || a === undefined) options = { name: a, shellPath: b, shellArgs: c }; else options = a;
    const host = this;
    const term = {
      name: options.name || 'Terminal', processId: Promise.resolve(undefined), creationOptions: options, exitStatus: undefined,
      state: { isInteractedWith: false, shell: undefined }, shellIntegration: undefined,
      sendText(text, addNewLine) {
        if (options.pty && typeof options.pty.handleInput === 'function') { options.pty.handleInput(String(text) + (addNewLine === false ? '' : '\r')); return; }
        host.rpc.notify('terminal/sendText', { id, text: String(text), addNewLine: addNewLine !== false });
      },
      show(preserveFocus) { host.rpc.notify('terminal/show', { id, preserveFocus: !!preserveFocus }); },
      hide() {},
      dispose() { host._terminals.delete(id); host.rpc.notify('terminal/dispose', { id }); if (options.pty && options.pty.close) { try { options.pty.close(); } catch (_) { /* */ } } host.events.terminalClose.fire(term); },
    };
    this._terminals.set(id, term);
    const env = options.env ? Object.fromEntries(Object.entries(options.env).filter(([, v]) => v !== null && v !== undefined).map(([k, v]) => [k, String(v)])) : undefined;
    this.rpc.notify('terminal/create', { id, name: term.name, cwd: options.cwd ? (T.Uri.isUri(options.cwd) ? options.cwd.fsPath : String(options.cwd)) : undefined, env, shellPath: options.shellPath, shellArgs: options.shellArgs, pty: !!options.pty, ext: ext ? ext.id : '' });
    if (options.pty) {
      const pty = options.pty;
      if (pty.onDidWrite) pty.onDidWrite((d) => this.rpc.notify('terminal/write', { id, data: String(d) }));
      if (pty.onDidClose) pty.onDidClose(() => term.dispose());
      setImmediate(() => { try { pty.open && pty.open({ columns: 120, rows: 30 }); } catch (e) { this.log(ext, 'pseudoterminal open failed: ' + e); } });
    }
    this.events.terminalOpen.fire(term);
    return term;
  }

  terminals() { return [...this._terminals.values()]; }

  async executeTask(ext, task) {
    const ex = task && task.execution;
    if (ex && (ex.commandLine || ex.command || ex.process)) {
      const line = ex.commandLine || [ex.command || ex.process, ...(ex.args || [])].map((a) => (typeof a === 'object' ? a.value : a)).join(' ');
      const t = this.createTerminal(ext, { name: task.name || 'Task', cwd: ex.options && ex.options.cwd, env: ex.options && ex.options.env });
      t.sendText(line);
      t.show();
      return { task, terminate: () => t.dispose() };
    }
    this.unsupported(ext, 'tasks.executeTask (custom execution)');
    return { task, terminate: () => {} };
  }

  // -------------------------------------------------------------------------- tree views
  registerTreeDataProvider(ext, viewId, provider) {
    const entry = { ext, viewId, provider, handles: new Map(), n: 0 };
    this.trees.set(viewId, entry);
    if (provider.onDidChangeTreeData) provider.onDidChangeTreeData(() => this.rpc.notify('tree/changed', { viewId }));
    this.rpc.notify('tree/registered', { viewId, ext: ext.id });
    return new T.Disposable(() => { this.trees.delete(viewId); });
  }

  createTreeView(ext, viewId, options) {
    const d = this.registerTreeDataProvider(ext, viewId, options.treeDataProvider);
    const em = new T.EventEmitter();
    return { visible: true, selection: [], message: undefined, title: undefined, description: undefined, badge: undefined,
      onDidChangeSelection: em.event, onDidChangeVisibility: em.event, onDidExpandElement: em.event, onDidCollapseElement: em.event, onDidChangeCheckboxState: em.event,
      reveal: () => Promise.resolve(), dispose: () => d.dispose() };
  }

  async treeChildren({ viewId, handle }) {
    const t = this.trees.get(viewId);
    if (!t) { await this.activateByEvent('onView:' + viewId); }
    const tree = this.trees.get(viewId);
    if (!tree) return [];
    const parent = handle ? tree.handles.get(handle) : undefined;
    const kids = (await withTimeout(tree.provider.getChildren(parent), PROVIDER_TIMEOUT, [])) || [];
    const out = [];
    for (const el of kids) {
      const item = await tree.provider.getTreeItem(el);
      const h = 'n' + (++tree.n);
      tree.handles.set(h, el);
      const label = typeof item.label === 'string' ? item.label : (item.label && item.label.label) || (item.resourceUri ? path.basename(item.resourceUri.fsPath) : '');
      out.push({ handle: h, label, description: typeof item.description === 'string' ? item.description : '', tooltip: C.markdownText(item.tooltip), collapsible: item.collapsibleState || 0, command: item.command ? this.cmdCache.put(item.command) : undefined, icon: item.iconPath && item.iconPath.id ? item.iconPath.id : undefined, contextValue: item.contextValue, path: item.resourceUri && item.resourceUri.scheme === 'file' ? item.resourceUri.fsPath : undefined });
    }
    return out;
  }

  // -------------------------------------------------------------------------- workspace
  workspaceFolders() { return this._folders; }

  workspaceFolderOf(uri) {
    if (!uri) return undefined;
    const p = (T.Uri.isUri(uri) ? uri.fsPath : String(uri)).toLowerCase();
    let best;
    for (const f of this._folders) {
      const fp = f.uri.fsPath.toLowerCase();
      if ((p === fp || p.startsWith(fp.endsWith(path.sep) ? fp : fp + path.sep)) && (!best || fp.length > best.uri.fsPath.length)) best = f;
    }
    return best;
  }

  workspaceKey() {
    const f = this._folders[0];
    return f ? crypto.createHash('md5').update(f.uri.fsPath.toLowerCase()).digest('hex').substring(0, 16) : 'empty';
  }

  asRelativePath(pathOrUri, includeWorkspaceFolder) {
    const p = T.Uri.isUri(pathOrUri) ? pathOrUri.fsPath : String(pathOrUri);
    const f = this.workspaceFolderOf(T.Uri.file(p));
    if (!f) return p;
    const rel = path.relative(f.uri.fsPath, p).replace(/\\/g, '/');
    return (includeWorkspaceFolder === true || (includeWorkspaceFolder === undefined && this._folders.length > 1)) ? f.name + '/' + rel : rel;
  }

  languageForPath(p) {
    const base = path.basename(p).toLowerCase();
    const ext = path.extname(p).toLowerCase();
    for (const e of this.extensions.values()) {
      for (const l of ((e.packageJSON.contributes || {}).languages || [])) {
        if (!l || !l.id) continue;
        if ((l.filenames || []).some((f) => f.toLowerCase() === base)) return l.id;
        if ((l.extensions || []).some((x) => x.toLowerCase() === ext || (x.length > ext.length && base.endsWith(x.toLowerCase())))) return l.id;
        if ((l.filenamePatterns || []).some((g) => matchGlob(g, p))) return l.id;
      }
    }
    const map = { '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript', '.ts': 'typescript', '.json': 'json', '.md': 'markdown', '.py': 'python', '.html': 'html', '.css': 'css', '.yaml': 'yaml', '.yml': 'yaml', '.xml': 'xml', '.php': 'php', '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.h': 'c', '.cs': 'csharp', '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.lua': 'lua', '.sh': 'shellscript', '.ps1': 'powershell', '.toml': 'toml', '.txt': 'plaintext' };
    return map[ext] || 'plaintext';
  }

  languages() {
    const s = new Set(this.ideLanguages);
    for (const e of this.extensions.values()) for (const l of ((e.packageJSON.contributes || {}).languages || [])) if (l && l.id) s.add(l.id);
    return [...s];
  }

  async openTextDocument(arg) {
    if (arg === undefined || (arg && typeof arg === 'object' && !T.Uri.isUri(arg))) {
      const o = arg || {};
      const uri = new T.Uri('untitled', '', 'Untitled-' + (++this._n));
      return this.docs.open(uri, o.language || 'plaintext', 1, o.content || '');
    }
    let uri = typeof arg === 'string' ? T.Uri.file(arg) : arg;
    if (uri.scheme === 'file') uri = T.Uri.file(uri.fsPath);
    const open = this.docs.get(uri);
    if (open) return open;
    if (uri.scheme === 'file') {
      const text = await fs.promises.readFile(uri.fsPath, 'utf8');
      return this.docs.open(uri, this.languageForPath(uri.fsPath), 1, text);
    }
    if (uri.scheme === 'untitled') return this.docs.open(uri, 'plaintext', 1, '');
    const cp = this.contentProviders.get(uri.scheme);
    if (!cp) { await this.activateByEvent('onFileSystem:' + uri.scheme); }
    const prov = this.contentProviders.get(uri.scheme);
    if (prov) {
      const text = await prov.provideTextDocumentContent(uri, T.CancellationTokenNone);
      return this.docs.open(uri, this.languageForPath(uri.path), 1, text || '');
    }
    throw new Error('cannot open ' + uri.toString());
  }

  registerContentProvider(scheme, provider) {
    this.contentProviders.set(scheme, provider);
    return new T.Disposable(() => { if (this.contentProviders.get(scheme) === provider) this.contentProviders.delete(scheme); });
  }

  async applyEdit(we) {
    if (!we) return false;
    const payload = C.ideWorkspaceEdit(we);
    const ok = await this.rpc.request('workspace/applyEdit', payload);
    return !!ok;
  }

  // -------------------------------------------------------------------------- configuration
  _rebuildDefaults() {
    const tree = {};
    for (const ext of this.extensions.values()) {
      const c = ext.packageJSON.contributes || {};
      const confs = Array.isArray(c.configuration) ? c.configuration : (c.configuration ? [c.configuration] : []);
      for (const conf of confs) {
        for (const [k, v] of Object.entries((conf && conf.properties) || {})) if (v && v.default !== undefined) setPath(tree, k, deepClone(v.default));
      }
      for (const [k, v] of Object.entries(c.configurationDefaults || {})) {
        if (k.startsWith('[')) tree[k] = Object.assign(tree[k] || {}, deepClone(v)); else setPath(tree, k, deepClone(v));
      }
    }
    this._configDefaults = tree;
    this._configTree = null;
  }

  _tree() {
    if (!this._configTree) {
      const tree = deepClone(this._configDefaults) || {};
      for (const [k, v] of Object.entries(this._settings)) {
        if (k.startsWith('[')) tree[k] = Object.assign(tree[k] || {}, v); else setPath(tree, k, deepClone(v));
      }
      this._configTree = tree;
    }
    return this._configTree;
  }

  getConfiguration(section, scope) {
    const host = this;
    const tree = this._tree();
    let langId = null;
    if (scope && typeof scope === 'object') {
      if (scope.languageId) langId = scope.languageId;
      else if (scope.uri && scope.languageId) langId = scope.languageId;
    }
    const lookup = (key) => {
      const full = section ? (key ? section + '.' + key : section) : key;
      let v = getPath(tree, full);
      if (langId && tree['[' + langId + ']'] && full) {
        const lv = tree['[' + langId + ']'][full];
        if (lv !== undefined) v = lv;
      }
      return v;
    };
    const value = deepClone(lookup(''));
    const result = {
      has: (key) => lookup(key) !== undefined,
      get: (key, dflt) => { const v = lookup(key); return v === undefined ? dflt : deepClone(v); },
      update: (key, value, target) => {
        const full = section ? section + '.' + key : key;
        return host.rpc.request('configuration/update', { key: full, value: value === undefined ? null : C.plain(value), remove: value === undefined, target: target === true ? 1 : target === false ? 2 : (target || 1) }).then(() => undefined);
      },
      inspect: (key) => {
        const full = section ? section + '.' + key : key;
        return { key: full, defaultValue: deepClone(getPath(host._configDefaults, full)), globalValue: host._settings[full], workspaceValue: undefined, workspaceFolderValue: undefined };
      },
    };
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      for (const [k, v] of Object.entries(value)) if (!(k in result)) result[k] = v;
    }
    return Object.freeze(result);
  }

  // -------------------------------------------------------------------------- files
  _makeFs() {
    const fsp = fs.promises;
    const wrap = (fn) => async (...a) => {
      try { return await fn(...a); } catch (e) {
        if (e && e.code === 'ENOENT') throw T.FileSystemError.FileNotFound(a[0]);
        if (e && e.code === 'EEXIST') throw T.FileSystemError.FileExists(a[0]);
        if (e && (e.code === 'EPERM' || e.code === 'EACCES')) throw T.FileSystemError.NoPermissions(a[0]);
        if (e && e.code === 'EISDIR') throw T.FileSystemError.FileIsADirectory(a[0]);
        if (e && e.code === 'ENOTDIR') throw T.FileSystemError.FileNotADirectory(a[0]);
        throw e;
      }
    };
    const host = this;
    const P = (u) => (T.Uri.isUri(u) ? u.fsPath : String(u));
    return {
      stat: wrap(async (u) => {
        if (T.Uri.isUri(u) && u.scheme !== 'file') { const d = await host.openTextDocument(u); return { type: T.FileType.File, ctime: 0, mtime: 0, size: d.getText().length }; }
        const s = await fsp.stat(P(u));
        return { type: s.isDirectory() ? T.FileType.Directory : s.isFile() ? T.FileType.File : T.FileType.Unknown, ctime: s.ctimeMs, mtime: s.mtimeMs, size: s.size };
      }),
      readDirectory: wrap(async (u) => (await fsp.readdir(P(u), { withFileTypes: true })).map((d) => [d.name, d.isDirectory() ? T.FileType.Directory : d.isFile() ? T.FileType.File : d.isSymbolicLink() ? T.FileType.SymbolicLink : T.FileType.Unknown])),
      createDirectory: wrap(async (u) => { await fsp.mkdir(P(u), { recursive: true }); }),
      readFile: wrap(async (u) => {
        if (T.Uri.isUri(u) && u.scheme !== 'file') { const d = await host.openTextDocument(u); return new Uint8Array(Buffer.from(d.getText(), 'utf8')); }
        return new Uint8Array(await fsp.readFile(P(u)));
      }),
      writeFile: wrap(async (u, content) => { await fsp.mkdir(path.dirname(P(u)), { recursive: true }); await fsp.writeFile(P(u), Buffer.from(content)); }),
      delete: wrap(async (u, o) => { await fsp.rm(P(u), { recursive: !!(o && o.recursive), force: false }); }),
      rename: wrap(async (a, b, o) => { if (!(o && o.overwrite) && fs.existsSync(P(b))) throw T.FileSystemError.FileExists(b); await fsp.rename(P(a), P(b)); }),
      copy: wrap(async (a, b, o) => { await fsp.cp(P(a), P(b), { recursive: true, force: !!(o && o.overwrite), errorOnExist: !(o && o.overwrite) }); }),
      isWritableFileSystem: (scheme) => scheme === 'file',
    };
  }

  _excludes() {
    const ex = this.getConfiguration('files').get('exclude') || {};
    const out = ['**/node_modules/**', '**/.git/**'];
    for (const [k, v] of Object.entries(ex)) if (v === true) out.push(k.endsWith('/**') ? k : k + '/**', k);
    return out;
  }

  async findFiles(include, exclude, maxResults, token) {
    const results = [];
    const limit = maxResults || 100000;
    const excludes = exclude === null ? [] : this._excludes();
    if (typeof exclude === 'string' || (exclude && exclude.pattern)) excludes.push(exclude);
    const roots = include && typeof include === 'object' && (include.baseUri || include.base) ?
      [{ dir: include.baseUri ? include.baseUri.fsPath : include.base, pattern: include.pattern }] :
      this._folders.map((f) => ({ dir: f.uri.fsPath, pattern: String(include || '**') }));
    let visited = 0;
    for (const root of roots) {
      const re = globToRegExp(root.pattern.replace(/\\/g, '/'));
      const walk = async (dir) => {
        if (results.length >= limit || visited > 200000 || (token && token.isCancellationRequested)) return;
        let entries;
        try { entries = await fs.promises.readdir(dir, { withFileTypes: true }); } catch (_) { return; }
        for (const e of entries) {
          if (results.length >= limit) return;
          visited++;
          const full = path.join(dir, e.name);
          if (excludes.some((x) => matchGlob(x, full) || (e.isDirectory() && matchGlob(x, full + '/x')))) continue;
          if (e.isDirectory()) await walk(full);
          else if (re.test(path.relative(root.dir, full).replace(/\\/g, '/'))) results.push(T.Uri.file(full));
        }
      };
      await walk(root.dir);
    }
    return results;
  }

  createFileSystemWatcher(glob, ignoreCreate, ignoreChange, ignoreDelete) {
    const host = this;
    const em = { create: new T.EventEmitter(), change: new T.EventEmitter(), delete: new T.EventEmitter() };
    const w = {
      ignoreCreateEvents: !!ignoreCreate, ignoreChangeEvents: !!ignoreChange, ignoreDeleteEvents: !!ignoreDelete,
      onDidCreate: em.create.event, onDidChange: em.change.event, onDidDelete: em.delete.event,
      _match: (p) => matchGlob(glob, p),
      _fire: (kind, p) => {
        if (kind === 'create' && w.ignoreCreateEvents) return;
        if (kind === 'change' && w.ignoreChangeEvents) return;
        if (kind === 'delete' && w.ignoreDeleteEvents) return;
        em[kind].fire(T.Uri.file(p));
      },
      dispose: () => { host.watchers.delete(w); },
    };
    this.watchers.add(w);
    this._ensureFsWatch();
    return w;
  }

  _ensureFsWatch() {
    this._fsWatches = this._fsWatches || new Map();
    for (const f of this._folders) {
      const dir = f.uri.fsPath;
      if (this._fsWatches.has(dir)) continue;
      try {
        const pending = new Map();
        const watcher = fs.watch(dir, { recursive: true }, (evt, filename) => {
          if (!filename) return;
          const full = path.join(dir, filename.toString());
          if (/[\\/](node_modules|\.git)[\\/]/.test(full)) return;
          pending.set(full, evt);
          clearTimeout(this._fsTimer);
          this._fsTimer = setTimeout(() => {
            const items = [...pending.entries()]; pending.clear();
            for (const [p, e] of items) {
              const exists = fs.existsSync(p);
              const kind = !exists ? 'delete' : e === 'rename' ? 'create' : 'change';
              for (const w of this.watchers) if (w._match(p)) w._fire(kind, p);
            }
          }, 100);
        });
        watcher.on('error', () => {});
        this._fsWatches.set(dir, watcher);
      } catch (e) { this.logHost('file watcher: ' + e); }
    }
  }

  // -------------------------------------------------------------------------- diagnostics
  createDiagnosticCollection(ext, name) {
    const host = this;
    const owner = (name || ext.id) + '#' + (++this._n);
    const map = new Map();          // uri string -> [uri, Diagnostic[]]
    const pending = new Set();
    let timer = null;
    const flush = () => {
      timer = null;
      const uris = [];
      for (const k of pending) {
        const e = map.get(k);
        const uri = e ? e[0] : T.Uri.parse(k);
        uris.push(uri);
        host.rpc.notify('diagnostics/set', { owner, path: uri.scheme === 'file' ? uri.fsPath : null, uri: uri.toString(), diagnostics: e ? e[1].map(C.ideDiagnostic) : [] });
      }
      pending.clear();
      host.events.diagnostics.fire({ uris });
    };
    const touch = (k) => { pending.add(k); if (!timer) timer = setImmediate(flush); };
    const coll = {
      name: name || ext.id,
      set(a, b) {
        if (Array.isArray(a)) {
          for (const [uri, diags] of a) {
            const k = uri.toString();
            if (!diags) { map.delete(k); } else {
              const prev = map.get(k);
              map.set(k, [uri, (prev && pending.has(k) ? prev[1] : []).concat(diags)]);
            }
            touch(k);
          }
          return;
        }
        const k = a.toString();
        if (!b) map.delete(k); else map.set(k, [a, [...b]]);
        touch(k);
      },
      delete(uri) { const k = uri.toString(); if (map.delete(k)) touch(k); },
      clear() { for (const k of map.keys()) touch(k); map.clear(); },
      forEach(cb, thisArg) { for (const [uri, diags] of map.values()) cb.call(thisArg, uri, diags, coll); },
      get(uri) { const e = map.get(uri.toString()); return e ? e[1] : undefined; },
      has(uri) { return map.has(uri.toString()); },
      dispose() { coll.clear(); host.collections.delete(coll); },
      [Symbol.iterator]: function* () { for (const [uri, diags] of map.values()) yield [uri, diags]; },
      _map: map,
    };
    this.collections.add(coll);
    return coll;
  }

  getDiagnostics(uri) {
    if (uri) {
      const out = [];
      for (const c of this.collections) { const d = c.get(uri); if (d) out.push(...d); }
      return out;
    }
    const all = new Map();
    for (const c of this.collections) for (const [u, d] of c._map.values()) { const k = u.toString(); if (!all.has(k)) all.set(k, [u, []]); all.get(k)[1].push(...d); }
    return [...all.values()];
  }

  setLanguageConfiguration(ext, language, configuration) {
    const ser = (v) => {
      if (v instanceof RegExp) return { $regex: v.source, flags: v.flags };
      if (Array.isArray(v)) return v.map(ser);
      if (v && typeof v === 'object') { const o = {}; for (const [k, x] of Object.entries(v)) o[k] = ser(x); return o; }
      return v;
    };
    this.rpc.notify('languages/setConfiguration', { language, config: ser(configuration || {}), ext: ext.id });
    return new T.Disposable(() => {});
  }

  // -------------------------------------------------------------------------- language providers
  registerProvider(ext, kind, selector, provider, rest) {
    let triggers = [];
    let metadata;
    if (kind === 'completion') triggers = rest.filter((x) => typeof x === 'string');
    else if (kind === 'signatureHelp') {
      if (rest[0] && typeof rest[0] === 'object') { metadata = rest[0]; triggers = [...(metadata.triggerCharacters || []), ...(metadata.retriggerCharacters || [])]; } else triggers = rest.filter((x) => typeof x === 'string');
    } else if (kind === 'onTypeFormatting') triggers = rest.filter((x) => typeof x === 'string');
    else metadata = rest[0];
    const entry = { id: ++this._n, ext, kind, selector, provider, triggers, metadata };
    this.providers.push(entry);
    this._providersChanged();
    return new T.Disposable(() => {
      const i = this.providers.indexOf(entry);
      if (i >= 0) { this.providers.splice(i, 1); this._providersChanged(); }
    });
  }

  _providersChanged() {
    if (this._providersTimer) return;
    this._providersTimer = setTimeout(() => {
      this._providersTimer = null;
      this.rpc.notify('providers/changed', { providers: this.providers.map((p) => ({ kind: p.kind, ext: p.ext.id, selector: serializeSelector(p.selector), triggers: p.triggers })) });
    }, 50);
  }

  _providersFor(kind, doc) {
    return this.providers.filter((p) => p.kind === kind && selectorScore(p.selector, doc) > 0)
      .sort((a, b) => selectorScore(b.selector, doc) - selectorScore(a.selector, doc) || b.id - a.id);
  }

  async _collect(kind, doc, call, timeout) {
    const out = [];
    const cts = new T.CancellationTokenSource();
    await Promise.all(this._providersFor(kind, doc).map(async (p) => {
      try {
        const r = await withTimeout(Promise.resolve(call(p.provider, cts.token, p)), timeout || PROVIDER_TIMEOUT, undefined);
        if (r !== undefined && r !== null) out.push(r);
      } catch (e) { this.log(p.ext, `${kind} provider failed: ${e && e.stack || e}`); }
    }));
    cts.cancel();
    return out;
  }

  async _first(kind, doc, call) {
    for (const p of this._providersFor(kind, doc)) {
      try {
        const r = await withTimeout(Promise.resolve(call(p.provider, T.CancellationTokenNone)), PROVIDER_TIMEOUT, undefined);
        if (r !== undefined && r !== null && !(Array.isArray(r) && !r.length)) return r;
      } catch (e) { this.log(p.ext, `${kind} provider failed: ${e && e.stack || e}`); }
    }
    return undefined;
  }

  async _docFor(uriString) {
    const uri = C.uriFromIde(uriString);
    if (!uri) return undefined;
    const d = this.docs.get(uri);
    if (d) return d;
    try { return await this.openTextDocument(uri); } catch (_) { return undefined; }
  }

  async _lspCompletion(doc, position) {
    const pos = doc.validatePosition(position);
    const line = doc.lineAt(pos.line).text;
    const ch = pos.character > 0 ? line[pos.character - 1] : '';
    const cts = new T.CancellationTokenSource();
    let incomplete = false;
    const items = [];
    await Promise.all(this._providersFor('completion', doc).map(async (p) => {
      const isTrigger = ch && p.triggers.includes(ch);
      const ctx = { triggerKind: isTrigger ? T.CompletionTriggerKind.TriggerCharacter : T.CompletionTriggerKind.Invoke, triggerCharacter: isTrigger ? ch : undefined };
      try {
        const r = await withTimeout(Promise.resolve(p.provider.provideCompletionItems(doc, pos, cts.token, ctx)), PROVIDER_TIMEOUT, undefined);
        if (!r) return;
        const list = Array.isArray(r) ? r : (r.items || []);
        if (!Array.isArray(r) && r.isIncomplete) incomplete = true;
        for (const it of list.slice(0, 2000)) items.push(C.completionItem(it, this.cmdCache));
      } catch (e) { this.log(p.ext, 'completion provider failed: ' + (e && e.stack || e)); }
    }));
    cts.cancel();
    return { isIncomplete: incomplete, items };
  }

  async lsp({ method, params }) {
    params = params || {};
    if (method === 'workspace/executeCommand') {
      const r = await this.executeCommand(params.command, this.cmdCache.args(params.arguments));
      return C.plain(r);
    }
    const doc = params.textDocument ? await this._docFor(params.textDocument.uri) : undefined;
    if (!doc) return null;
    const P = params.position ? doc.validatePosition(C.toPosition(params.position)) : undefined;
    const R = params.range ? doc.validateRange(C.toRange(params.range)) : undefined;
    switch (method) {
      case 'textDocument/completion': return this._lspCompletion(doc, P);
      case 'textDocument/hover': {
        const hs = await this._collect('hover', doc, (p, tok) => p.provideHover(doc, P, tok));
        const parts = hs.map(C.hover).filter(Boolean);
        if (!parts.length) return null;
        return { contents: { kind: 'markdown', value: parts.map((h) => h.contents.value).join('\n\n---\n\n') }, range: parts[0].range };
      }
      case 'textDocument/definition': return C.locations(await this._first('definition', doc, (p, tok) => p.provideDefinition(doc, P, tok)));
      case 'textDocument/declaration': return C.locations(await this._first('declaration', doc, (p, tok) => p.provideDeclaration(doc, P, tok)));
      case 'textDocument/typeDefinition': return C.locations(await this._first('typeDefinition', doc, (p, tok) => p.provideTypeDefinition(doc, P, tok)));
      case 'textDocument/implementation': return C.locations(await this._first('implementation', doc, (p, tok) => p.provideImplementation(doc, P, tok)));
      case 'textDocument/references': {
        const rs = await this._collect('references', doc, (p, tok) => p.provideReferences(doc, P, params.context || { includeDeclaration: true }, tok));
        return rs.flat().map(C.location).filter(Boolean);
      }
      case 'textDocument/signatureHelp': {
        const r = await this._first('signatureHelp', doc, (p, tok) => p.provideSignatureHelp(doc, P, tok, { triggerKind: T.SignatureHelpTriggerKind.Invoke, isRetrigger: false, activeSignatureHelp: undefined }));
        return C.signatureHelp(r);
      }
      case 'textDocument/formatting': {
        const opts = params.options || { tabSize: 4, insertSpaces: true };
        return C.textEdits(await this._first('formatting', doc, (p, tok) => p.provideDocumentFormattingEdits(doc, opts, tok)));
      }
      case 'textDocument/rangeFormatting': {
        const opts = params.options || { tabSize: 4, insertSpaces: true };
        const r = await this._first('rangeFormatting', doc, (p, tok) => p.provideDocumentRangeFormattingEdits(doc, R, opts, tok));
        return C.textEdits(r);
      }
      case 'textDocument/codeAction': {
        const ctx = params.context || {};
        const vctx = { diagnostics: (ctx.diagnostics || []).map(C.vscodeDiagnostic), only: ctx.only && ctx.only.length ? new T.CodeActionKind(ctx.only[0]) : undefined, triggerKind: ctx.triggerKind || T.CodeActionTriggerKind.Invoke };
        if (!vctx.diagnostics.length) vctx.diagnostics = this.getDiagnostics(doc.uri).filter((d) => d.range.intersection(R));
        const rs = await this._collect('codeAction', doc, (p, tok) => p.provideCodeActions(doc, R, vctx, tok));
        return rs.flat().map((a) => C.codeAction(a, this.cmdCache)).filter(Boolean);
      }
      case 'textDocument/rename': {
        const we = await this._first('rename', doc, (p, tok) => p.provideRenameEdits(doc, P, params.newName, tok));
        return C.workspaceEdit(we);
      }
      case 'textDocument/prepareRename': {
        const p = this._providersFor('rename', doc)[0];
        if (!p || typeof p.provider.prepareRename !== 'function') return null;
        const r = await p.provider.prepareRename(doc, P, T.CancellationTokenNone);
        if (!r) return null;
        return T.Range.isRange(r) ? C.range(r) : { range: C.range(r.range), placeholder: r.placeholder };
      }
      case 'textDocument/documentSymbol': {
        const r = await this._first('documentSymbol', doc, (p, tok) => p.provideDocumentSymbols(doc, tok));
        return (r || []).map(C.documentSymbol);
      }
      case 'textDocument/documentHighlight': {
        const r = await this._first('documentHighlight', doc, (p, tok) => p.provideDocumentHighlights(doc, P, tok));
        return (r || []).map((h) => ({ range: C.range(h.range), kind: (h.kind || 0) + 1 }));
      }
      case 'textDocument/inlayHint': {
        const rs = await this._collect('inlayHint', doc, (p, tok) => p.provideInlayHints(doc, R, tok));
        return rs.flat().map(C.inlayHint);
      }
      case 'textDocument/codeLens': {
        const rs = await this._collect('codeLens', doc, (p, tok) => p.provideCodeLenses(doc, tok));
        return rs.flat().map((l) => ({ range: C.range(l.range), command: l.command ? this.cmdCache.put(l.command) : undefined }));
      }
      case 'textDocument/foldingRange': {
        const rs = await this._collect('foldingRange', doc, (p, tok) => p.provideFoldingRanges(doc, {}, tok));
        return rs.flat().map((f) => ({ startLine: f.start, endLine: f.end, kind: f.kind === 1 ? 'comment' : f.kind === 2 ? 'imports' : f.kind === 3 ? 'region' : undefined }));
      }
      case 'textDocument/documentLink': {
        const rs = await this._collect('documentLink', doc, (p, tok) => p.provideDocumentLinks(doc, tok));
        return rs.flat().map((l) => ({ range: C.range(l.range), target: l.target ? l.target.toString() : undefined, tooltip: l.tooltip }));
      }
      default: return null;
    }
  }

  // -------------------------------------------------------------------------- IDE -> host
  _registerHandlers() {
    const R = (m, fn) => this.rpc.requestHandlers.set(m, fn);
    const N = (m, fn) => this.rpc.notificationHandlers.set(m, fn);

    R('initialize', async (p) => {
      this.apiVersion = p.apiVersion || this.apiVersion;
      this.storageRoot = p.storageRoot || this.storageRoot;
      this.appRoot = p.appRoot || this.appRoot;
      this.uiLanguage = p.language || 'en';
      this.themeKind = p.themeKind || this.themeKind;
      this.ideLanguages = p.languages || [];
      if (p.machineId) this.machineId = p.machineId;
      this._settings = p.settings || {};
      this._folders = (p.workspaceFolders || []).map((f, i) => ({ uri: T.Uri.file(f), name: path.basename(f), index: i }));
      const loaded = [];
      for (const e of p.extensions || []) {
        let pj = e.packageJSON;
        if (!pj) { try { pj = JSON.parse(fs.readFileSync(path.join(e.path, 'package.json'), 'utf8')); } catch (err) { this.logHost(`cannot read ${e.path}: ${err}`); continue; } }
        const id = (e.id || `${pj.publisher}.${pj.name}`).toLowerCase();
        const main = pj.main ? path.resolve(e.path, pj.main) : null;
        const ext = { id, idOriginal: `${pj.publisher}.${pj.name}`, path: e.path, packageJSON: pj, main, active: false, failed: null, exports: undefined, activation: null };
        ext.events = this._activationEvents(ext);
        this.extensions.set(id, ext);
        loaded.push({ id, main: !!main, events: [...ext.events] });
      }
      this._rebuildDefaults();
      setImmediate(() => this._startup());
      return { ok: true, pid: process.pid, node: process.version, extensions: loaded };
    });

    R('shutdown', async () => {
      await this.deactivateAll();
      setTimeout(() => process.exit(0), 50);
      return true;
    });
    R('ping', async () => 'pong');
    R('activate', async (p) => { await this.activateByEvent(p.event); return true; });
    R('extensions/status', async () => this.extensionList().map((e) => ({ id: e.id, active: e.active, failed: e.failed, main: !!e.main })));
    R('commands/execute', async (p) => {
      const r = await this.executeCommand(p.command, this.cmdCache.args(p.args));
      return C.plain(r);
    });
    R('commands/list', async () => [...this.commands.keys()]);
    R('lsp', (p) => this.lsp(p));
    R('tree/children', (p) => this.treeChildren(p));
    R('debug/resolve', (p) => this.debug.resolve(p));
    R('debug/contributed', async () => this.debug.contributed().map((d) => ({ type: d.type, label: d.label, languages: d.languages, ext: d.ext.id, initialConfigurations: d.contribution.initialConfigurations || [], configurationAttributes: d.contribution.configurationAttributes || {}, hasProgram: !!(d.contribution.program || d.contribution.runtime || d.contribution.windows) })));
    N('debug/sessionStarted', (p) => this.debug.started(p));
    N('debug/sessionTerminated', (p) => this.debug.terminated(p));
    N('debug/customEvent', (p) => this.debug.customEvent(p));

    N('document/open', (p) => {
      const uri = p.path ? T.Uri.file(p.path) : T.Uri.parse(p.uri);
      const doc = this.docs.open(uri, p.languageId, p.version || 1, p.text || '');
      if (p.dirty !== undefined) doc.isDirty = !!p.dirty;
      this.activateByEvent('onLanguage:' + doc.languageId);
    });
    N('document/change', (p) => { this.docs.change(p.path ? T.Uri.file(p.path) : T.Uri.parse(p.uri), p.version, p.text, p.dirty); });
    N('document/save', (p) => {
      const uri = p.path ? T.Uri.file(p.path) : T.Uri.parse(p.uri);
      const doc = this.docs.get(uri);
      if (doc && p.text !== undefined) this.docs.change(uri, undefined, p.text, false);
      this.docs.saved(uri);
    });
    N('document/close', (p) => {
      const uri = p.path ? T.Uri.file(p.path) : T.Uri.parse(p.uri);
      this.docs.close(uri);
      this._editors.delete(uri.toString());
      if (this._active && this._active.document.uri.toString() === uri.toString()) { this._active = null; this.events.activeEditor.fire(undefined); }
    });
    N('editor/active', (p) => {
      let ed = null;
      if (p.path) {
        const doc = this.docs.get(T.Uri.file(p.path));
        if (doc) { ed = this._editorFor(doc); if (p.selection) ed._setSelection(p.selection); }
      }
      if (ed !== this._active) {
        this._active = ed;
        this.events.activeEditor.fire(ed || undefined);
        this.events.visibleEditors.fire(this.visibleEditors());
        if (this._tabEvents) this._tabEvents.tabs.fire({ opened: [], closed: [], changed: [] });
      }
    });
    N('editor/selection', (p) => {
      const doc = p.path && this.docs.get(T.Uri.file(p.path));
      if (!doc) return;
      const ed = this._editorFor(doc);
      ed._setSelection(p.selection);
      this.events.selection.fire({ textEditor: ed, selections: ed.selections, kind: T.TextEditorSelectionChangeKind.Keyboard });
    });
    N('configuration/changed', (p) => {
      const old = this._tree();
      this._settings = p.settings || {};
      this._configTree = null;
      const neu = this._tree();
      const keys = p.keys || [];
      this.events.configuration.fire({
        affectsConfiguration: (section) => {
          if (keys.length) return keys.some((k) => k === section || k.startsWith(section + '.') || section.startsWith(k + '.'));
          return JSON.stringify(getPath(old, section)) !== JSON.stringify(getPath(neu, section));
        },
      });
    });
    N('workspace/folders', (p) => {
      const old = this._folders;
      this._folders = (p.folders || []).map((f, i) => ({ uri: T.Uri.file(f), name: path.basename(f), index: i }));
      this.events.workspaceFolders.fire({ added: this._folders.filter((f) => !old.some((o) => o.uri.fsPath === f.uri.fsPath)), removed: old.filter((o) => !this._folders.some((f) => o.uri.fsPath === f.uri.fsPath)) });
      this._ensureFsWatch();
      this._workspaceContains();
    });
    N('theme/changed', (p) => { this.themeKind = p.kind || this.themeKind; this.events.theme.fire({ kind: this.themeKind }); });
    N('window/focus', (p) => this.events.windowState.fire({ focused: !!p.focused, active: !!p.focused }));
    N('progress/cancel', (p) => { const c = this._progress && this._progress.get(p.id); if (c) c.cancel(); });
    N('terminal/closed', (p) => { const t = this._terminals.get(p.id); if (t) { this._terminals.delete(p.id); t.exitStatus = { code: p.code, reason: T.TerminalExitReason.Process }; this.events.terminalClose.fire(t); } });
    N('files/event', (p) => {
      const uris = (p.paths || []).map((x) => T.Uri.file(x));
      if (p.kind === 'create') this.events.createFiles.fire({ files: uris });
      else if (p.kind === 'delete') this.events.deleteFiles.fire({ files: uris });
      for (const u of uris) for (const w of this.watchers) if (w._match(u.fsPath)) w._fire(p.kind, u.fsPath);
    });
  }

  async _startup() {
    await this.activateByEvent('*');
    await this._workspaceContains();
    for (const d of this.docs.all()) await this.activateByEvent('onLanguage:' + d.languageId);
    setTimeout(() => {
      this.activateByEvent('onStartupFinished').then(() => this.rpc.notify('host/ready', { extensions: this.extensionList().map((e) => ({ id: e.id, active: e.active, failed: e.failed })) }));
    }, 300);
  }

  async _workspaceContains() {
    for (const ext of this.extensions.values()) {
      if (ext.active || ext.failed || !ext.main) continue;
      for (const ev of ext.events) {
        if (!ev.startsWith('workspaceContains:')) continue;
        const pattern = ev.substring('workspaceContains:'.length);
        const hits = await this.findFiles(pattern.includes('/') || pattern.includes('*') ? pattern : '**/' + pattern, undefined, 1);
        if (hits.length) { this.activate(ext, ev); break; }
      }
    }
  }
}

// ============================================================================ TextEditor
class TextEditor {
  constructor(host, doc) {
    this._host = host;
    this._doc = doc;
    this._selections = [new T.Selection(0, 0, 0, 0)];
    this.options = { tabSize: 4, insertSpaces: true, cursorStyle: T.TextEditorCursorStyle.Line, lineNumbers: T.TextEditorLineNumbersStyle.On, indentSize: 4 };
    this.viewColumn = T.ViewColumn.One;
  }
  get document() { return this._host.docs.get(this._doc.uri) || this._doc; }
  get selection() { return this._selections[0]; }
  set selection(s) { this.selections = [s]; }
  get selections() { return this._selections; }
  set selections(list) {
    this._selections = list.map((s) => (s instanceof T.Selection ? s : new T.Selection(s.start, s.end)));
    const s = this._selections[0];
    this._host.rpc.notify('editor/setSelection', { path: this.document.uri.fsPath, selection: [s.anchor.line, s.anchor.character, s.active.line, s.active.character] });
  }
  get visibleRanges() { return [new T.Range(0, 0, this.document.lineCount, 0)]; }
  _setSelection(sel) {
    const [l1, c1, l2, c2] = sel;
    this._selections = [new T.Selection(l1, c1, l2, c2)];
  }
  async edit(callback) {
    const b = this._host.editBuilder(this);
    callback(b.edit);
    return b.apply();
  }
  insertSnippet(snippet, location) {
    let range = null;
    if (location) {
      const r = Array.isArray(location) ? location[0] : location;
      range = r instanceof T.Position ? [r.line, r.character, r.line, r.character] : [r.start.line, r.start.character, r.end.line, r.end.character];
    }
    return this._host.rpc.request('editor/insertSnippet', { path: this.document.uri.fsPath, snippet: typeof snippet === 'string' ? snippet : snippet.value, range }).then((r) => !!r);
  }
  setDecorations(type, rangesOrOptions) {
    const ranges = (rangesOrOptions || []).map((x) => {
      const r = T.Range.isRange(x) ? x : x.range;
      const o = { range: [r.start.line, r.start.character, r.end.line, r.end.character] };
      if (!T.Range.isRange(x)) {
        if (x.hoverMessage) o.hover = Array.isArray(x.hoverMessage) ? x.hoverMessage.map(C.markdownText).join('\n\n') : C.markdownText(x.hoverMessage);
        if (x.renderOptions) o.after = x.renderOptions.after && x.renderOptions.after.contentText;
      }
      return o;
    });
    this._host.rpc.notify('editor/decorations', { path: this.document.uri.fsPath, key: type.key, ranges });
  }
  revealRange(range, revealType) {
    this._host.rpc.notify('editor/reveal', { path: this.document.uri.fsPath, line: range.start.line, type: revealType || 0 });
  }
  show() { this._host.showTextDocument(this.document); }
  hide() {}
}

// ============================================================================ start
const host = new Host();
module.exports = { host };
