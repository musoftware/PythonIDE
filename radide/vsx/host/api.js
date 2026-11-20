'use strict';
// The "vscode" module each extension gets (one object per extension, like VS Code does).
// Every namespace is wrapped so that an API RAD IDE does not implement fails softly: the first use is
// logged to the "Extension Host" output channel and a harmless stub is returned (never a crash).

const fs = require('fs');
const os = require('os');
const path = require('path');
const T = require('./types');
const C = require('./convert');
const { matchGlob } = require('./glob');

// ============================================================================ soft stubs
function softStub(host, ext, name) {
  const fn = function () { host.unsupported(ext, name); return softStub(host, ext, name + '()'); };
  return new Proxy(fn, {
    get(_t, p) {
      if (p === 'then' || typeof p === 'symbol') return undefined;
      if (p === 'dispose') return () => {};
      if (p === 'toString' || p === 'valueOf') return () => '';
      if (p === 'length') return 0;
      if (/^on(Did|Will)[A-Z]/.test(p)) return () => new T.Disposable(() => {});
      return softStub(host, ext, name + '.' + p);
    },
    apply() { host.unsupported(ext, name); return softStub(host, ext, name + '()'); },
    construct() { host.unsupported(ext, 'new ' + name); return softStub(host, ext, name + '{}'); },
  });
}

function wrapNs(host, ext, obj, nsName) {
  return new Proxy(obj, {
    get(t, p, recv) {
      if (p in t) return Reflect.get(t, p, recv);
      if (typeof p === 'symbol' || p === 'then' || p === 'toJSON' || p === '__esModule' || p === 'default') return undefined;
      const name = nsName ? nsName + '.' + p : 'vscode.' + p;
      if (/^on(Did|Will)[A-Z]/.test(p)) { host.unsupported(ext, name); return () => new T.Disposable(() => {}); }
      return softStub(host, ext, name);
    },
  });
}

const noopEvent = () => new T.Disposable(() => {});

// ============================================================================ helpers
function selectorScore(selector, doc) {
  if (!selector || !doc) return 0;
  if (Array.isArray(selector)) return Math.max(0, ...selector.map((s) => selectorScore(s, doc)));
  if (typeof selector === 'string') {
    if (selector === '*') return 5;
    return selector === doc.languageId ? 10 : 0;
  }
  const { language, scheme, pattern, notebookType } = selector;
  if (notebookType) return 0;
  let score = 0;
  if (scheme) { if (scheme === doc.uri.scheme) score = 10; else if (scheme === '*') score = 5; else return 0; }
  if (language) { if (language === doc.languageId) score = 10; else if (language === '*') score = Math.max(score, 5); else return 0; }
  if (pattern) {
    if (matchGlob(pattern, doc.uri.scheme === 'file' ? doc.uri.fsPath : doc.uri.path)) score = 10; else return 0;
  }
  return score || (scheme || language || pattern ? 0 : 0);
}

function serializeSelector(selector) {
  const list = Array.isArray(selector) ? selector : [selector];
  return list.map((s) => {
    if (typeof s === 'string') return { language: s };
    const out = {};
    if (s.language) out.language = s.language;
    if (s.scheme) out.scheme = s.scheme;
    if (s.pattern) out.pattern = typeof s.pattern === 'string' ? s.pattern : { base: s.pattern.baseUri ? s.pattern.baseUri.fsPath : s.pattern.base, pattern: s.pattern.pattern };
    return out;
  });
}

function messageArgs(args) {
  // (message, ...items) | (message, options, ...items)
  const message = String(args[0] === undefined ? '' : args[0]);
  let rest = args.slice(1);
  let options = {};
  if (rest.length && rest[0] && typeof rest[0] === 'object' && !('title' in rest[0]) && !Array.isArray(rest[0])) { options = rest[0]; rest = rest.slice(1); }
  if (rest.length === 1 && Array.isArray(rest[0])) rest = rest[0];
  return { message, options, items: rest.filter((x) => x !== undefined) };
}

// ============================================================================ the API
function createApi(host, ext) {
  const api = {};
  const N = (obj, name) => wrapNs(host, ext, obj, name);

  Object.assign(api, T);
  api.version = host.apiVersion;
  api.CancellationTokenNone = undefined;
  delete api.CancellationTokenNone;
  api.CancellationToken = { None: T.CancellationTokenNone, Cancelled: Object.freeze({ isCancellationRequested: true, onCancellationRequested: noopEvent }) };

  // -------------------------------------------------------------------------- commands
  api.commands = N({
    registerCommand(id, callback, thisArg) { return host.registerCommand(ext, id, callback, thisArg); },
    registerTextEditorCommand(id, callback, thisArg) {
      return host.registerCommand(ext, id, (...args) => {
        const ed = host.activeEditor();
        if (!ed) { host.log(ext, `command ${id}: no active text editor`); return undefined; }
        const builder = host.editBuilder(ed);
        const res = callback.call(thisArg, ed, builder.edit, ...args);
        return Promise.resolve(res).then(() => builder.apply());
      });
    },
    executeCommand(id, ...args) { return host.executeCommand(id, args, ext); },
    getCommands(filterInternal) { return host.getCommands(filterInternal); },
    registerDiffInformationCommand(id, cb, thisArg) { return host.registerCommand(ext, id, cb, thisArg); },
  }, 'commands');

  // -------------------------------------------------------------------------- window
  const win = {
    showInformationMessage: (...a) => host.showMessage('info', messageArgs(a)),
    showWarningMessage: (...a) => host.showMessage('warning', messageArgs(a)),
    showErrorMessage: (...a) => host.showMessage('error', messageArgs(a)),
    showQuickPick: (items, options, token) => host.showQuickPick(items, options || {}, token),
    showInputBox: (options, token) => host.showInputBox(options || {}, token),
    showOpenDialog: (options) => host.rpc.request('window/showOpenDialog', { ...(options || {}), defaultUri: options && options.defaultUri ? options.defaultUri.fsPath : undefined })
      .then((paths) => (paths && paths.length ? paths.map((p) => T.Uri.file(p)) : undefined)),
    showSaveDialog: (options) => host.rpc.request('window/showSaveDialog', { ...(options || {}), defaultUri: options && options.defaultUri ? options.defaultUri.fsPath : undefined })
      .then((p) => (p ? T.Uri.file(p) : undefined)),
    showWorkspaceFolderPick: async (options) => {
      const folders = host.workspaceFolders();
      if (folders.length <= 1) return folders[0];
      const pick = await host.showQuickPick(folders.map((f) => ({ label: f.name, description: f.uri.fsPath, folder: f })), options || {});
      return pick ? pick.folder : undefined;
    },
    createOutputChannel: (name, options) => host.createOutputChannel(ext, name, options),
    createStatusBarItem: (a, b, c) => host.createStatusBarItem(ext, a, b, c),
    setStatusBarMessage: (text, hide) => {
      const timeout = typeof hide === 'number' ? hide : 0;
      host.rpc.notify('window/setStatusBarMessage', { text: String(text), timeout });
      if (hide && typeof hide.then === 'function') hide.then(() => host.rpc.notify('window/setStatusBarMessage', { text: '', timeout: 1 }));
      return new T.Disposable(() => host.rpc.notify('window/setStatusBarMessage', { text: '', timeout: 1 }));
    },
    withProgress: (options, task) => host.withProgress(ext, options || {}, task),
    withScmProgress: (task) => host.withProgress(ext, { location: T.ProgressLocation.SourceControl }, (p, t) => task(p, t)),
    get activeTextEditor() { return host.activeEditor(); },
    get visibleTextEditors() { return host.visibleEditors(); },
    onDidChangeActiveTextEditor: host.events.activeEditor.event,
    onDidChangeVisibleTextEditors: host.events.visibleEditors.event,
    onDidChangeTextEditorSelection: host.events.selection.event,
    onDidChangeTextEditorVisibleRanges: noopEvent,
    onDidChangeTextEditorOptions: noopEvent,
    onDidChangeTextEditorViewColumn: noopEvent,
    onDidChangeWindowState: host.events.windowState.event,
    state: { focused: true, active: true },
    showTextDocument: (docOrUri, columnOrOptions, preserveFocus) => host.showTextDocument(docOrUri, columnOrOptions, preserveFocus),
    createTextEditorDecorationType: (options) => host.createDecorationType(ext, options),
    createTerminal: (a, b, c) => host.createTerminal(ext, a, b, c),
    get terminals() { return host.terminals(); },
    get activeTerminal() { return host.terminals()[0]; },
    onDidOpenTerminal: host.events.terminalOpen.event,
    onDidCloseTerminal: host.events.terminalClose.event,
    onDidChangeActiveTerminal: noopEvent,
    onDidChangeTerminalState: noopEvent,
    onDidChangeTerminalShellIntegration: noopEvent,
    onDidStartTerminalShellExecution: noopEvent,
    onDidEndTerminalShellExecution: noopEvent,
    registerTerminalProfileProvider: () => new T.Disposable(() => {}),
    registerTerminalLinkProvider: () => new T.Disposable(() => {}),
    get activeColorTheme() { return { kind: host.themeKind }; },
    onDidChangeActiveColorTheme: host.events.theme.event,
    createQuickPick: () => host.createQuickPick(ext),
    createInputBox: () => host.createInputBox(ext),
    registerTreeDataProvider: (viewId, provider) => host.registerTreeDataProvider(ext, viewId, provider),
    createTreeView: (viewId, options) => host.createTreeView(ext, viewId, options),
    registerUriHandler: () => new T.Disposable(() => {}),
    registerFileDecorationProvider: () => new T.Disposable(() => {}),
    get tabGroups() { return host.tabGroups(); },
    get visibleNotebookEditors() { return []; },
    get activeNotebookEditor() { return undefined; },
    onDidChangeVisibleNotebookEditors: noopEvent,
    onDidChangeActiveNotebookEditor: noopEvent,
    onDidChangeNotebookEditorSelection: noopEvent,
    onDidChangeNotebookEditorVisibleRanges: noopEvent,
  };
  api.window = N(win, 'window');

  // -------------------------------------------------------------------------- workspace
  const ws = {
    get workspaceFolders() { const f = host.workspaceFolders(); return f.length ? f : undefined; },
    get name() { const f = host.workspaceFolders(); return f.length ? f[0].name : undefined; },
    get rootPath() { const f = host.workspaceFolders(); return f.length ? f[0].uri.fsPath : undefined; },
    get workspaceFile() { return undefined; },
    getWorkspaceFolder: (uri) => host.workspaceFolderOf(uri),
    asRelativePath: (pathOrUri, includeWorkspaceFolder) => host.asRelativePath(pathOrUri, includeWorkspaceFolder),
    onDidChangeWorkspaceFolders: host.events.workspaceFolders.event,
    updateWorkspaceFolders: () => false,
    get textDocuments() { return host.docs.all(); },
    openTextDocument: (arg) => host.openTextDocument(arg),
    onDidOpenTextDocument: host.docs.onDidOpen.event,
    onDidCloseTextDocument: host.docs.onDidClose.event,
    onDidChangeTextDocument: host.docs.onDidChange.event,
    onDidSaveTextDocument: host.docs.onDidSave.event,
    onWillSaveTextDocument: host.docs.onWillSave.event,
    onDidCreateFiles: host.events.createFiles.event,
    onDidDeleteFiles: host.events.deleteFiles.event,
    onDidRenameFiles: host.events.renameFiles.event,
    onWillCreateFiles: noopEvent,
    onWillDeleteFiles: noopEvent,
    onWillRenameFiles: noopEvent,
    getConfiguration: (section, scope) => host.getConfiguration(section, scope),
    onDidChangeConfiguration: host.events.configuration.event,
    createFileSystemWatcher: (glob, ic, ich, idl) => host.createFileSystemWatcher(glob, ic, ich, idl),
    findFiles: (include, exclude, maxResults, token) => host.findFiles(include, exclude, maxResults, token),
    applyEdit: (edit) => host.applyEdit(edit),
    saveAll: (includeUntitled) => host.rpc.request('workspace/saveAll', { includeUntitled: !!includeUntitled }).then((r) => !!r),
    save: (uri) => host.rpc.request('workspace/save', { path: uri.fsPath }).then((r) => (r ? uri : undefined)),
    registerTextDocumentContentProvider: (scheme, provider) => host.registerContentProvider(scheme, provider),
    registerTaskProvider: () => new T.Disposable(() => {}),
    registerFileSystemProvider: (scheme) => { host.unsupported(ext, 'workspace.registerFileSystemProvider(' + scheme + ')'); return new T.Disposable(() => {}); },
    get fs() { return host.fsApi; },
    get isTrusted() { return true; },
    requestWorkspaceTrust: () => Promise.resolve(true),
    onDidGrantWorkspaceTrust: noopEvent,
    get notebookDocuments() { return []; },
    onDidOpenNotebookDocument: noopEvent,
    onDidCloseNotebookDocument: noopEvent,
    onDidChangeNotebookDocument: noopEvent,
    onDidSaveNotebookDocument: noopEvent,
    onWillSaveNotebookDocument: noopEvent,
    registerNotebookSerializer: () => new T.Disposable(() => {}),
    get textDocumentsCount() { return host.docs.all().length; },
  };
  api.workspace = N(ws, 'workspace');

  // -------------------------------------------------------------------------- languages
  const reg = (kind) => (selector, provider, ...rest) => host.registerProvider(ext, kind, selector, provider, rest);
  const langs = {
    registerCompletionItemProvider: reg('completion'),
    registerHoverProvider: reg('hover'),
    registerDefinitionProvider: reg('definition'),
    registerDeclarationProvider: reg('declaration'),
    registerTypeDefinitionProvider: reg('typeDefinition'),
    registerImplementationProvider: reg('implementation'),
    registerReferenceProvider: reg('references'),
    registerSignatureHelpProvider: reg('signatureHelp'),
    registerDocumentFormattingEditProvider: reg('formatting'),
    registerDocumentRangeFormattingEditProvider: reg('rangeFormatting'),
    registerOnTypeFormattingEditProvider: reg('onTypeFormatting'),
    registerCodeActionsProvider: reg('codeAction'),
    registerCodeLensProvider: reg('codeLens'),
    registerDocumentSymbolProvider: reg('documentSymbol'),
    registerWorkspaceSymbolProvider: (provider) => host.registerProvider(ext, 'workspaceSymbol', '*', provider, []),
    registerRenameProvider: reg('rename'),
    registerDocumentHighlightProvider: reg('documentHighlight'),
    registerDocumentLinkProvider: reg('documentLink'),
    registerColorProvider: reg('color'),
    registerFoldingRangeProvider: reg('foldingRange'),
    registerSelectionRangeProvider: reg('selectionRange'),
    registerInlayHintsProvider: reg('inlayHint'),
    registerDocumentSemanticTokensProvider: reg('semanticTokens'),
    registerDocumentRangeSemanticTokensProvider: reg('rangeSemanticTokens'),
    registerCallHierarchyProvider: reg('callHierarchy'),
    registerTypeHierarchyProvider: reg('typeHierarchy'),
    registerLinkedEditingRangeProvider: reg('linkedEditing'),
    registerInlineCompletionItemProvider: reg('inlineCompletion'),
    registerInlineValuesProvider: reg('inlineValues'),
    registerEvaluatableExpressionProvider: reg('evaluatableExpression'),
    registerDocumentDropEditProvider: reg('documentDrop'),
    registerDocumentPasteEditProvider: reg('documentPaste'),
    registerMultiDocumentHighlightProvider: reg('multiDocumentHighlight'),
    createDiagnosticCollection: (name) => host.createDiagnosticCollection(ext, name),
    getDiagnostics: (uri) => host.getDiagnostics(uri),
    onDidChangeDiagnostics: host.events.diagnostics.event,
    setLanguageConfiguration: (language, configuration) => host.setLanguageConfiguration(ext, language, configuration),
    getLanguages: () => Promise.resolve(host.languages()),
    setTextDocumentLanguage: (doc, languageId) => host.rpc.request('workspace/setLanguage', { path: doc.uri.fsPath, language: languageId }).then(() => doc),
    match: (selector, doc) => selectorScore(selector, doc),
    createLanguageStatusItem: (id, selector) => host.createLanguageStatusItem(ext, id, selector),
  };
  api.languages = N(langs, 'languages');

  // -------------------------------------------------------------------------- env
  const env = {
    appName: 'RAD IDE',
    appRoot: host.appRoot,
    appHost: 'desktop',
    get language() { return host.uiLanguage; },
    machineId: host.machineId,
    sessionId: host.sessionId,
    uriScheme: 'radide',
    uiKind: T.UIKind.Desktop,
    remoteName: undefined,
    shell: process.env.ComSpec || '/bin/sh',
    isNewAppInstall: false,
    isTelemetryEnabled: false,
    onDidChangeTelemetryEnabled: noopEvent,
    onDidChangeShell: noopEvent,
    logLevel: T.LogLevel.Info,
    onDidChangeLogLevel: noopEvent,
    clipboard: {
      readText: () => host.rpc.request('env/clipboardRead', {}).then((t) => t || ''),
      writeText: (text) => host.rpc.request('env/clipboardWrite', { text: String(text) }).then(() => undefined),
    },
    openExternal: (uri) => host.rpc.request('env/openExternal', { uri: uri.toString(true) }).then((r) => !!r),
    asExternalUri: (uri) => Promise.resolve(uri),
    createTelemetryLogger: () => ({ logUsage() {}, logError() {}, dispose() {}, isUsageEnabled: false, isErrorsEnabled: false, onDidChangeEnableStates: noopEvent }),
  };
  api.env = N(env, 'env');

  // -------------------------------------------------------------------------- extensions
  api.extensions = N({
    getExtension: (id) => host.extensionApiObject(id),
    get all() { return host.extensionList().map((e) => host.extensionApiObject(e.id)); },
    get allAcrossExtensionHosts() { return host.extensionList().map((e) => host.extensionApiObject(e.id)); },
    onDidChange: host.events.extensions.event,
  }, 'extensions');

  // -------------------------------------------------------------------------- debug
  api.debug = N({
    registerDebugConfigurationProvider: (type, provider, triggerKind) => host.debug.registerConfigProvider(ext, type, provider, triggerKind),
    registerDebugAdapterDescriptorFactory: (type, factory) => host.debug.registerDescriptorFactory(ext, type, factory),
    registerDebugAdapterTrackerFactory: (type, factory) => host.debug.registerTrackerFactory(ext, type, factory),
    startDebugging: (folder, nameOrConfig, parentOrOptions) => host.debug.start(folder, nameOrConfig, parentOrOptions),
    stopDebugging: (session) => host.rpc.request('debug/stop', { id: session && session.id }).then(() => undefined),
    get activeDebugSession() { return host.debug.activeSession; },
    get activeDebugConsole() { return host.debug.console(ext); },
    get breakpoints() { return []; },
    get activeStackItem() { return undefined; },
    addBreakpoints: () => {},
    removeBreakpoints: () => {},
    asDebugSourceUri: (source) => T.Uri.file(source.path || ''),
    onDidStartDebugSession: host.debug.events.start.event,
    onDidTerminateDebugSession: host.debug.events.terminate.event,
    onDidChangeActiveDebugSession: host.debug.events.active.event,
    onDidReceiveDebugSessionCustomEvent: host.debug.events.custom.event,
    onDidChangeBreakpoints: noopEvent,
    onDidChangeActiveStackItem: noopEvent,
  }, 'debug');

  // -------------------------------------------------------------------------- tasks / scm / misc
  api.tasks = N({
    registerTaskProvider: () => new T.Disposable(() => {}),
    fetchTasks: () => Promise.resolve([]),
    executeTask: (task) => host.executeTask(ext, task),
    get taskExecutions() { return []; },
    onDidStartTask: noopEvent, onDidEndTask: noopEvent, onDidStartTaskProcess: noopEvent, onDidEndTaskProcess: noopEvent,
  }, 'tasks');
  api.l10n = N({
    t: (...args) => {
      let message; let params = [];
      if (typeof args[0] === 'object' && args[0] && 'message' in args[0]) { message = args[0].message; params = args[0].args || []; } else { message = String(args[0]); params = args.slice(1); }
      const bundle = host.l10nBundle(ext);
      if (bundle && bundle[message]) message = typeof bundle[message] === 'string' ? bundle[message] : bundle[message].message || message;
      const named = params.length === 1 && params[0] && typeof params[0] === 'object' ? params[0] : null;
      return message.replace(/\{([^}]+)\}/g, (m, k) => {
        const v = named ? named[k] : params[parseInt(k, 10)];
        return v === undefined ? m : String(v);
      });
    },
    get bundle() { return host.l10nBundle(ext); },
    get uri() { return undefined; },
  }, 'l10n');
  api.authentication = N({
    getSession: () => Promise.resolve(undefined),
    getAccounts: () => Promise.resolve([]),
    onDidChangeSessions: noopEvent,
    registerAuthenticationProvider: () => new T.Disposable(() => {}),
  }, 'authentication');
  api.scm = N({ get inputBox() { return undefined; } }, 'scm');
  api.comments = N({}, 'comments');
  api.notebooks = N({}, 'notebooks');
  api.tests = N({}, 'tests');
  api.chat = N({}, 'chat');
  api.lm = N({ selectChatModels: () => Promise.resolve([]), onDidChangeChatModels: noopEvent, get tools() { return []; } }, 'lm');
  api.interactive = N({}, 'interactive');
  return new Proxy(api, {
    get(t, p, recv) {
      if (p in t) return Reflect.get(t, p, recv);
      if (typeof p === 'symbol' || p === 'then' || p === '__esModule' || p === 'default' || p === 'toJSON') return undefined;
      return softStub(host, ext, 'vscode.' + p);
    },
  });
}

// ============================================================================ ExtensionContext
function readJson(f, dflt) { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (_) { return dflt; } }

class Memento {
  constructor(file) {
    this._file = file;
    this._data = readJson(file, {});
    this._timer = null;
  }
  keys() { return Object.keys(this._data); }
  get(key, dflt) { return key in this._data ? this._data[key] : dflt; }
  update(key, value) {
    if (value === undefined) delete this._data[key]; else this._data[key] = value;
    if (this._timer) clearTimeout(this._timer);
    this._timer = setTimeout(() => this.flush(), 200);
    return Promise.resolve();
  }
  setKeysForSync() {}
  flush() {
    this._timer = null;
    try { fs.mkdirSync(path.dirname(this._file), { recursive: true }); fs.writeFileSync(this._file, JSON.stringify(this._data)); } catch (_) { /* */ }
  }
}

class SecretStorage {
  // basic: kept next to the extension's global storage, obfuscated (not encrypted) - documented limitation
  constructor(file) { this._file = file; this._emitter = new T.EventEmitter(); this.onDidChange = this._emitter.event; }
  _load() { const d = readJson(this._file, {}); return d && typeof d === 'object' ? d : {}; }
  _save(d) { try { fs.mkdirSync(path.dirname(this._file), { recursive: true }); fs.writeFileSync(this._file, JSON.stringify(d)); } catch (_) { /* */ } }
  get(key) { const v = this._load()[key]; return Promise.resolve(v === undefined ? undefined : Buffer.from(v, 'base64').toString('utf8')); }
  store(key, value) { const d = this._load(); d[key] = Buffer.from(String(value), 'utf8').toString('base64'); this._save(d); this._emitter.fire({ key }); return Promise.resolve(); }
  delete(key) { const d = this._load(); delete d[key]; this._save(d); this._emitter.fire({ key }); return Promise.resolve(); }
  keys() { return Promise.resolve(Object.keys(this._load())); }
}

function createContext(host, ext) {
  const gs = path.join(host.storageRoot, 'globalStorage', ext.id);
  const wsKey = host.workspaceKey();
  const wsDir = path.join(host.storageRoot, 'workspaceStorage', wsKey, ext.id);
  const logDir = path.join(host.storageRoot, 'logs', ext.id);
  const globalState = new Memento(path.join(gs, 'state.json'));
  const workspaceState = new Memento(path.join(wsDir, 'state.json'));
  host.mementos.push(globalState, workspaceState);
  const envColl = () => {
    const m = new Map();
    return { persistent: true, description: undefined, replace: (k, v) => m.set(k, { value: v, type: 1 }), append: (k, v) => m.set(k, { value: v, type: 2 }), prepend: (k, v) => m.set(k, { value: v, type: 3 }), get: (k) => m.get(k), forEach: (cb) => m.forEach((v, k) => cb(k, v, this)), delete: (k) => m.delete(k), clear: () => m.clear(), getScoped: () => envColl(), [Symbol.iterator]: () => m.entries() };
  };
  const ctx = {
    subscriptions: [],
    workspaceState,
    globalState,
    secrets: new SecretStorage(path.join(gs, 'secrets.json')),
    extensionUri: T.Uri.file(ext.path),
    extensionPath: ext.path,
    environmentVariableCollection: envColl(),
    asAbsolutePath: (rel) => path.join(ext.path, rel),
    storageUri: T.Uri.file(wsDir),
    storagePath: wsDir,
    globalStorageUri: T.Uri.file(gs),
    globalStoragePath: gs,
    logUri: T.Uri.file(logDir),
    logPath: logDir,
    extensionMode: T.ExtensionMode.Production,
    get extension() { return host.extensionApiObject(ext.id); },
    languageModelAccessInformation: { onDidChange: noopEvent, canSendRequest: () => undefined },
  };
  try { fs.mkdirSync(gs, { recursive: true }); } catch (_) { /* */ }
  return ctx;
}

module.exports = { createApi, createContext, selectorScore, serializeSelector, softStub, os };
