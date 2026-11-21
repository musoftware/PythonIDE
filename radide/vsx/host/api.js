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
const W = require('./workbench');
const S = require('./services');

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
    onDidChangeTextEditorVisibleRanges: host.events.visibleRanges.event,
    onDidChangeTextEditorOptions: host.events.editorOptions.event,
    onDidChangeTextEditorViewColumn: noopEvent,          // one editor group: the view column never changes
    onDidChangeWindowState: host.events.windowState.event,
    get state() { return host.windowState; },
    showTextDocument: (docOrUri, columnOrOptions, preserveFocus) => host.showTextDocument(docOrUri, columnOrOptions, preserveFocus),
    createTextEditorDecorationType: (options) => host.createDecorationType(ext, options),
    createTerminal: (a, b, c) => host.createTerminal(ext, a, b, c),
    get terminals() { return host.terminals(); },
    get activeTerminal() { return host.terminalsSvc.active; },
    onDidOpenTerminal: host.terminalsSvc.em.open.event,
    onDidCloseTerminal: host.terminalsSvc.em.close.event,
    onDidChangeActiveTerminal: host.terminalsSvc.em.active.event,
    onDidChangeTerminalState: host.terminalsSvc.em.state.event,
    onDidChangeTerminalShellIntegration: host.terminalsSvc.em.shellIntegration.event,
    onDidStartTerminalShellExecution: host.terminalsSvc.em.startExec.event,
    onDidEndTerminalShellExecution: host.terminalsSvc.em.endExec.event,
    registerTerminalProfileProvider: (id, provider) => host.terminalsSvc.registerProfileProvider(ext, id, provider),
    registerTerminalLinkProvider: (provider) => host.terminalsSvc.registerLinkProvider(ext, provider),
    get activeColorTheme() { return { kind: host.themeKind }; },
    onDidChangeActiveColorTheme: host.events.theme.event,
    createQuickPick: () => host.createQuickPick(ext),
    createInputBox: () => host.createInputBox(ext),
    registerTreeDataProvider: (viewId, provider) => host.registerTreeDataProvider(ext, viewId, provider),
    createTreeView: (viewId, options) => host.createTreeView(ext, viewId, options),
    registerWebviewViewProvider: (viewId, provider, options) => host.webviews.registerProvider(ext, viewId, provider, options),
    createWebviewPanel: (viewType, title, showOptions, options) => {
      const panel = host.webviews.createPanel(ext, viewType, title, showOptions, options);
      // window.tabGroups: the new panel is the active tab until another tab becomes active
      try {
        if (!(showOptions && typeof showOptions === 'object' && showOptions.preserveFocus)) host.tabs.setActive('webview:' + panel._handle);
        host.tabs.changed();
        panel.onDidDispose(() => { if (host.tabs.activeKey === 'webview:' + panel._handle) host.tabs.activeKey = null; host.tabs.changed(); });
        panel.onDidChangeViewState(() => { if (panel.active) host.tabs.setActive('webview:' + panel._handle); host.tabs.changed(); });
      } catch (_) { /* */ }
      return panel;
    },
    registerWebviewPanelSerializer: (viewType, serializer) => host.webviews.registerSerializer(ext, viewType, serializer),
    registerUriHandler: (handler) => host.uriHandlers.register(ext, handler),
    registerFileDecorationProvider: (provider) => host.fileDecorations.register(ext, provider),
    registerCustomEditorProvider: (viewType, provider, options) => host.customEditors.register(ext, viewType, provider, options),
    get tabGroups() { return host.tabGroups(); },
    showNotebookDocument: async (doc) => {
      host.log(ext, 'showNotebookDocument: RAD IDE has no notebook editor (the notebook stays open as a document)');
      return { notebook: doc, selections: [new T.NotebookRange(0, 0)], selection: new T.NotebookRange(0, 0), visibleRanges: [], viewColumn: T.ViewColumn.One, revealRange() {}, setDecorations() {} };
    },
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
    updateWorkspaceFolders: (start, deleteCount, ...add) => host.updateWorkspaceFolders(start, deleteCount, ...add),
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
    onWillCreateFiles: host.events.willCreateFiles.event,
    onWillDeleteFiles: host.events.willDeleteFiles.event,
    onWillRenameFiles: host.events.willRenameFiles.event,
    getConfiguration: (section, scope) => host.getConfiguration(section, scope),
    onDidChangeConfiguration: host.events.configuration.event,
    createFileSystemWatcher: (glob, ic, ich, idl) => host.createFileSystemWatcher(glob, ic, ich, idl),
    findFiles: (include, exclude, maxResults, token) => host.findFiles(include, exclude, maxResults, token),
    applyEdit: (edit) => host.applyEdit(edit),
    saveAll: (includeUntitled) => host.rpc.request('workspace/saveAll', { includeUntitled: !!includeUntitled }).then((r) => !!r),
    save: (uri) => host.rpc.request('workspace/save', { path: uri.fsPath }).then((r) => (r ? uri : undefined)),
    registerTextDocumentContentProvider: (scheme, provider) => host.registerContentProvider(scheme, provider),
    registerTaskProvider: (type, provider) => host.tasksSvc.register(ext, type, provider),
    registerFileSystemProvider: (scheme, provider, options) => host.fsx.register(ext, scheme, provider, options),
    encode: (text) => Promise.resolve(W.encode(text)),
    decode: (bytes) => Promise.resolve(W.decode(bytes)),
    registerPortAttributesProvider: () => new T.Disposable(() => {}),   // no port forwarding in a local IDE
    get fs() { return host.fsApi; },
    get isTrusted() { return true; },
    requestWorkspaceTrust: () => Promise.resolve(true),
    onDidGrantWorkspaceTrust: noopEvent,
    get notebookDocuments() { return [...host.notebooks.docs.values()]; },
    openNotebookDocument: (a, b) => host.notebooks.open(a, b),
    onDidOpenNotebookDocument: host.notebooks.em.open.event,
    onDidCloseNotebookDocument: host.notebooks.em.close.event,
    onDidChangeNotebookDocument: host.notebooks.em.change.event,
    onDidSaveNotebookDocument: host.notebooks.em.save.event,
    onWillSaveNotebookDocument: noopEvent,
    registerNotebookSerializer: (type, serializer, options) => host.notebooks.registerSerializer(ext, type, serializer, options),
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
    get uriScheme() { return host.uriScheme; },
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
    openExternal: (uri) => {
      const u = T.Uri.isUri(uri) ? uri : T.Uri.parse(String(uri));
      if (u.scheme === host.uriScheme) return host.uriHandlers.handle({ uri: u.toString() }).then((r) => !!(r && r.ok));
      if (u.scheme === 'command') return host.executeCommand(u.path, u.query ? [].concat(JSON.parse(decodeURIComponent(u.query))) : [], ext).then(() => true, () => false);
      return host.rpc.request('env/openExternal', { uri: u.toString(true) }).then((r) => !!r);
    },
    asExternalUri: (uri) => Promise.resolve(uri),     // local desktop IDE: http(s)://localhost and radide:// URIs are reachable as they are
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
    get breakpoints() { return [...host.breakpoints]; },
    get activeStackItem() { return undefined; },
    addBreakpoints: (bps) => { const added = (bps || []).filter((b) => !host.breakpoints.includes(b)); host.breakpoints.push(...added); if (added.length) host.events.breakpoints.fire({ added, removed: [], changed: [] }); },
    removeBreakpoints: (bps) => { const removed = (bps || []).filter((b) => host.breakpoints.includes(b)); host.breakpoints = host.breakpoints.filter((b) => !removed.includes(b)); if (removed.length) host.events.breakpoints.fire({ added: [], removed, changed: [] }); },
    asDebugSourceUri: (source) => T.Uri.file(source.path || ''),
    onDidStartDebugSession: host.debug.events.start.event,
    onDidTerminateDebugSession: host.debug.events.terminate.event,
    onDidChangeActiveDebugSession: host.debug.events.active.event,
    onDidReceiveDebugSessionCustomEvent: host.debug.events.custom.event,
    onDidChangeBreakpoints: host.events.breakpoints.event,
    onDidChangeActiveStackItem: noopEvent,
  }, 'debug');

  // -------------------------------------------------------------------------- tasks / scm / misc
  api.tasks = N({
    registerTaskProvider: (type, provider) => host.tasksSvc.register(ext, type, provider),
    fetchTasks: (filter) => host.tasksSvc.fetch(filter),
    executeTask: (task) => host.executeTask(ext, task),
    get taskExecutions() { return [...host.tasksSvc.executions]; },
    onDidStartTask: host.tasksSvc.em.start.event, onDidEndTask: host.tasksSvc.em.end.event,
    onDidStartTaskProcess: host.tasksSvc.em.startProcess.event, onDidEndTaskProcess: host.tasksSvc.em.endProcess.event,
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
    getSession: (providerId, scopes, options) => host.auth.getSession(ext, providerId, scopes, options),
    getAccounts: (providerId) => host.auth.getAccounts(providerId),
    onDidChangeSessions: host.auth.em.event,
    registerAuthenticationProvider: (id, label, provider, options) => host.auth.register(ext, id, label, provider, options),
  }, 'authentication');
  // no UI for these in RAD IDE: the objects have VS Code's shapes so extensions run normally
  api.scm = N({ get inputBox() { return undefined; }, createSourceControl: (id, label, rootUri) => S.sourceControl(id, label, rootUri) }, 'scm');
  api.comments = N({ createCommentController: (id, label) => S.commentController(id, label) }, 'comments');
  api.notebooks = N({
    createNotebookController: (id, notebookType, label, handler) => host.notebooks.controller(ext, id, notebookType, label, handler),
    registerNotebookCellStatusBarItemProvider: () => new T.Disposable(() => {}),
    createRendererMessaging: () => ({ onDidReceiveMessage: noopEvent, postMessage: () => Promise.resolve(false) }),
  }, 'notebooks');
  api.tests = N({ createTestController: (id, label) => S.testController(id, label), createTestObserver: () => ({ tests: [], onDidChangeTest: noopEvent, dispose() {} }) }, 'tests');
  api.chat = N({ createChatParticipant: (id, handler) => S.chatParticipant(id, handler), registerChatVariableResolver: () => new T.Disposable(() => {}) }, 'chat');
  api.lm = N({
    selectChatModels: () => Promise.resolve([]), onDidChangeChatModels: noopEvent, get tools() { return []; },
    registerTool: () => new T.Disposable(() => {}),
    invokeTool: (name) => Promise.reject(new Error(`No language model tool named '${name}' is registered in RAD IDE`)),
    registerMcpServerDefinitionProvider: () => new T.Disposable(() => {}),
    registerChatModelProvider: () => new T.Disposable(() => {}),
  }, 'lm');
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
  const ctx = {
    subscriptions: [],
    workspaceState,
    globalState,
    secrets: new SecretStorage(path.join(gs, 'secrets.json')),
    extensionUri: T.Uri.file(ext.path),
    extensionPath: ext.path,
    environmentVariableCollection: W.envCollection(true),
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
