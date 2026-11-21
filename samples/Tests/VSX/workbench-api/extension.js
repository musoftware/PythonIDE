// RAD IDE test extension (MIT): the workbench APIs that used to be no-op mocks in the extension host.
// samples/Tests/VSX/test_vsx_workbench.py drives it through the commands wbTest.run / wbTest.report.
const vscode = require('vscode');
const path = require('path');

const state = { events: [], uris: [], saves: 0, visibleRangeEvents: 0, decoRequests: 0, diffResult: null, terminals: {}, termOutput: {}, closed: {}, ptyInput: '', tabEvents: 0 };
const log = (e) => state.events.push(e);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(fn, ms) { const end = Date.now() + ms; while (Date.now() < end) { const v = fn(); if (v) return v; await wait(50); } return fn(); }

// ------------------------------------------------------------------ an in-memory FileSystemProvider (like Claude Code's)
class MemFs {
  constructor() { this.files = new Map(); this.dirs = new Set(['/']); this.em = new vscode.EventEmitter(); this.onDidChangeFile = this.em.event; this.writes = 0; }
  watch() { return new vscode.Disposable(() => {}); }
  stat(uri) {
    if (this.dirs.has(uri.path)) return { type: vscode.FileType.Directory, ctime: 0, mtime: 0, size: 0 };
    const f = this.files.get(uri.path);
    if (!f) throw vscode.FileSystemError.FileNotFound(uri);
    return { type: vscode.FileType.File, ctime: 0, mtime: f.mtime, size: f.data.length };
  }
  readDirectory(uri) {
    const base = uri.path.replace(/\/$/, '') + '/';
    const out = [];
    for (const p of this.files.keys()) if (p.startsWith(base) && !p.substring(base.length).includes('/')) out.push([p.substring(base.length), vscode.FileType.File]);
    for (const d of this.dirs) if (d !== '/' && d.startsWith(base) && !d.substring(base.length).includes('/')) out.push([d.substring(base.length), vscode.FileType.Directory]);
    return out;
  }
  createDirectory(uri) { this.dirs.add(uri.path); }
  readFile(uri) { const f = this.files.get(uri.path); if (!f) throw vscode.FileSystemError.FileNotFound(uri); return f.data; }
  writeFile(uri, content, options) {
    const exists = this.files.has(uri.path);
    if (!exists && options && options.create === false) throw vscode.FileSystemError.FileNotFound(uri);
    if (exists && options && options.create && options.overwrite === false) throw vscode.FileSystemError.FileExists(uri);
    this.files.set(uri.path, { data: content, mtime: Date.now() });
    this.writes++;
    this.em.fire([{ type: exists ? vscode.FileChangeType.Changed : vscode.FileChangeType.Created, uri }]);
  }
  delete(uri) { if (!this.files.delete(uri.path)) throw vscode.FileSystemError.FileNotFound(uri); this.em.fire([{ type: vscode.FileChangeType.Deleted, uri }]); }
  rename(a, b, o) {
    if (this.files.has(b.path) && !(o && o.overwrite)) throw vscode.FileSystemError.FileExists(b);
    const f = this.files.get(a.path);
    if (!f) throw vscode.FileSystemError.FileNotFound(a);
    this.files.delete(a.path); this.files.set(b.path, f);
  }
}
const memfs = new MemFs();
const mem = (p) => vscode.Uri.from({ scheme: 'wbmem', path: p });
const text = (bytes) => Buffer.from(bytes).toString('utf8');
const bytes = (s) => new Uint8Array(Buffer.from(s, 'utf8'));

function tabsSummary() {
  return vscode.window.tabGroups.all.flatMap((g) => g.tabs).map((t) => ({
    label: t.label, active: t.isActive, dirty: t.isDirty,
    kind: t.input instanceof vscode.TabInputTextDiff ? 'diff' : t.input instanceof vscode.TabInputText ? 'text' : t.input instanceof vscode.TabInputCustom ? 'custom' : t.input instanceof vscode.TabInputWebview ? 'webview' : 'other',
    uri: t.input && (t.input.uri || t.input.modified) ? String(t.input.uri || t.input.modified) : undefined,
    viewType: t.input && t.input.viewType,
  }));
}
const diffTabs = (uri) => vscode.window.tabGroups.all.flatMap((g) => g.tabs).filter((t) => t.input instanceof vscode.TabInputTextDiff && t.input.modified.toString() === uri.toString());

async function finishDiff(accepted, arg) {
  const tab = arg instanceof vscode.Uri ? diffTabs(arg)[0] : vscode.window.tabGroups.activeTabGroup.activeTab;
  if (!tab || !(tab.input instanceof vscode.TabInputTextDiff)) { state.diffResult = { accepted, error: 'no diff tab', viaUri: arg instanceof vscode.Uri }; return false; }
  const doc = await vscode.workspace.openTextDocument(tab.input.modified);
  const final = doc.getText();
  if (accepted && doc.isDirty) await doc.save();
  const closed = await vscode.window.tabGroups.close(tab);
  state.diffResult = { accepted, text: final, viaUri: arg instanceof vscode.Uri, closed, after: diffTabs(tab.input.modified).length };
  return true;
}

async function activate(context) {
  context.subscriptions.push(vscode.workspace.registerFileSystemProvider('wbmem', memfs, { isCaseSensitive: true }));
  memfs.dirs.add('/dir');
  context.subscriptions.push(vscode.window.registerUriHandler({ handleUri(uri) { state.uris.push({ path: uri.path, query: uri.query, authority: uri.authority }); } }));
  const decoEm = new vscode.EventEmitter();
  context.subscriptions.push(vscode.window.registerFileDecorationProvider({
    onDidChangeFileDecorations: decoEm.event,
    provideFileDecoration(uri) { state.decoRequests++; if (uri.fsPath.endsWith('notes.txt')) return new vscode.FileDecoration('W', 'workbench test badge', new vscode.ThemeColor('charts.red')); return undefined; },
  }));
  context.environmentVariableCollection.replace('WB_VAR', 'fromCollection');
  // like Claude Code: the editor/title buttons follow a context key set from the visible editors
  context.subscriptions.push(vscode.window.onDidChangeVisibleTextEditors((eds) => {
    vscode.commands.executeCommand('setContext', 'wbTest.viewingDiff', eds.some((e) => e.document.uri.scheme === 'wbmem'));
  }));
  context.subscriptions.push(vscode.window.onDidChangeTextEditorVisibleRanges(() => { state.visibleRangeEvents++; }));
  context.subscriptions.push(vscode.window.tabGroups.onDidChangeTabs(() => { state.tabEvents++; }));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument((d) => { if (d.uri.scheme === 'wbmem') state.saves++; }));
  context.subscriptions.push(vscode.commands.registerCommand('wbTest.acceptDiff', (arg) => finishDiff(true, arg)));
  context.subscriptions.push(vscode.commands.registerCommand('wbTest.rejectDiff', (arg) => finishDiff(false, arg)));
  context.subscriptions.push(vscode.window.registerTerminalProfileProvider('wbTest.profile', {
    provideTerminalProfile() { return new vscode.TerminalProfile({ name: 'WB From Profile', shellPath: process.execPath, shellArgs: ['-e', 'console.log("profile terminal")'] }); },
  }));
  context.subscriptions.push(vscode.window.registerTerminalLinkProvider({
    provideTerminalLinks(ctx) { const i = ctx.line.indexOf('LINK:'); return i >= 0 ? [Object.assign(new vscode.TerminalLink(i, 5, 'open'), { data: ctx.line.substring(i + 5).trim() })] : []; },
    handleTerminalLink(link) { state.link = link.data; },
  }));
  context.subscriptions.push(vscode.tasks.registerTaskProvider('wbtask', {
    provideTasks() { return [new vscode.Task({ type: 'wbtask' }, vscode.TaskScope.Workspace, 'wb exit 4', 'wbtask', new vscode.ProcessExecution(process.execPath, ['-e', 'process.exit(4)']))]; },
    resolveTask() { return undefined; },
  }));
  let sessions = [];
  const authEm = new vscode.EventEmitter();
  context.subscriptions.push(vscode.authentication.registerAuthenticationProvider('wbauth', 'WB Auth', {
    onDidChangeSessions: authEm.event,
    getSessions: async () => sessions,
    createSession: async (scopes) => { const s = { id: 's1', accessToken: 'token', account: { id: 'u1', label: 'User One' }, scopes }; sessions = [s]; authEm.fire({ added: [s], removed: [], changed: [] }); return s; },
    removeSession: async () => { sessions = []; },
  }));
  context.subscriptions.push(vscode.workspace.registerNotebookSerializer('wbnb', {
    deserializeNotebook(data) { const j = JSON.parse(text(data) || '{"cells":[]}'); return new vscode.NotebookData(j.cells.map((c) => new vscode.NotebookCellData(vscode.NotebookCellKind.Code, c, 'python'))); },
    serializeNotebook(data) { return bytes(JSON.stringify({ cells: data.cells.map((c) => c.value) })); },
  }));
  context.subscriptions.push(vscode.window.registerCustomEditorProvider('wbTest.custom', {
    resolveCustomTextEditor(document, panel) {
      panel.webview.options = { enableScripts: true };
      panel.webview.html = `<!doctype html><html><body><pre id="t">${document.getText().replace(/</g, '&lt;')}</pre></body></html>`;
      state.customResolved = { text: document.getText(), viewType: panel.viewType };
    },
  }));

  context.subscriptions.push(vscode.commands.registerCommand('wbTest.report', () => {
    const { terminals, ...rest } = state;
    return JSON.parse(JSON.stringify(rest));
  }));
  context.subscriptions.push(vscode.commands.registerCommand('wbTest.run', async (step, ...args) => {
    switch (step) {
      case 'fs': {
        const fsx = vscode.workspace.fs;
        const r = {};
        await fsx.writeFile(mem('/a.txt'), bytes('alpha'));
        r.read = text(await fsx.readFile(mem('/a.txt')));
        r.stat = (await fsx.stat(mem('/a.txt'))).size;
        r.dir = (await fsx.readDirectory(mem('/'))).map((e) => e[0]).sort();
        await fsx.rename(mem('/a.txt'), mem('/b.txt'));
        r.renamed = memfs.files.has('/b.txt') && !memfs.files.has('/a.txt');
        await fsx.copy(mem('/b.txt'), mem('/c.txt'));
        r.copied = text(memfs.files.get('/c.txt').data);
        await fsx.delete(mem('/c.txt'));
        r.deleted = !memfs.files.has('/c.txt');
        try { await fsx.readFile(mem('/missing.txt')); r.missing = 'no error'; } catch (e) { r.missing = e.code || e.name; }
        r.writable = [fsx.isWritableFileSystem('wbmem'), fsx.isWritableFileSystem('file'), fsx.isWritableFileSystem('nope')];
        if (args[0]) { await fsx.copy(mem('/b.txt'), vscode.Uri.file(args[0]), { overwrite: true }); r.toDisk = true; }
        return r;
      }
      case 'doc': {
        memfs.writeFile(mem('/doc.txt'), bytes('one\ntwo\n'), { create: true, overwrite: true });
        const doc = await vscode.workspace.openTextDocument(mem('/doc.txt'));
        const r = { text: doc.getText(), scheme: doc.uri.scheme };
        const we = new vscode.WorkspaceEdit();
        we.insert(doc.uri, new vscode.Position(0, 0), 'zero\n');
        r.applied = await vscode.workspace.applyEdit(we);
        r.dirty = doc.isDirty;
        r.saved = await doc.save();
        r.provider = text(memfs.files.get('/doc.txt').data);
        r.saves = state.saves;
        memfs.writeFile(mem('/doc.txt'), bytes('changed outside\n'), { create: true, overwrite: true });
        r.reloaded = await until(() => doc.getText() === 'changed outside\n', 2000);
        return r;
      }
      case 'diff': {
        const left = vscode.Uri.file(args[0]);
        const right = mem('/proposed/' + path.basename(args[0]));
        memfs.dirs.add('/proposed');
        memfs.writeFile(right, bytes(args[1]), { create: true, overwrite: true });
        await vscode.workspace.openTextDocument(right);
        state.diffResult = null;
        await vscode.commands.executeCommand('vscode.diff', left, right, 'Proposed (wb)', { preview: false, preserveFocus: true });
        const tab = await until(() => diffTabs(right)[0], 1000);        // Claude Code waits 1 s for the tab
        return { found: !!tab, label: tab && tab.label, active: tab && tab.isActive, right: right.toString(), visible: vscode.window.visibleTextEditors.map((e) => e.document.uri.scheme) };
      }
      case 'diffState': return { result: state.diffResult, tabs: tabsSummary() };
      case 'tabs': return { tabs: tabsSummary(), active: vscode.window.tabGroups.activeTabGroup.activeTab ? vscode.window.tabGroups.activeTabGroup.activeTab.label : null, events: state.tabEvents };
      case 'closeTab': {
        const t = vscode.window.tabGroups.all.flatMap((g) => g.tabs).find((x) => x.label === args[0]);
        return t ? vscode.window.tabGroups.close(t) : 'no tab';
      }
      case 'showVirtual': {
        memfs.writeFile(mem('/shown.txt'), bytes('shown text\n'), { create: true, overwrite: true });
        const doc = await vscode.workspace.openTextDocument(mem('/shown.txt'));
        const ed = await vscode.window.showTextDocument(doc, { preview: false });
        return { active: vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.uri.toString(), uri: doc.uri.toString(), ed: ed.document.uri.toString(), tab: tabsSummary().find((t) => t.uri === doc.uri.toString()) };
      }
      case 'virtualText': { const d = vscode.workspace.textDocuments.find((x) => x.uri.toString() === args[0]); return d ? { text: d.getText(), dirty: d.isDirty, provider: memfs.files.get(d.uri.path) ? text(memfs.files.get(d.uri.path).data) : null } : null; }
      case 'termProc': {
        const t = vscode.window.createTerminal({ name: 'WB Proc', shellPath: process.execPath, shellArgs: ['-e', 'console.log("hello-term " + process.env.WB_VAR + " " + process.env.WB_OWN); process.stdin.on("data", (d) => { process.stdout.write("echo:" + d); if (String(d).includes("bye")) process.exit(3); });'], env: { WB_OWN: 'own' } });
        state.terminals.proc = t;
        const sub = vscode.window.onDidCloseTerminal((x) => { if (x === t) { state.closed.proc = x.exitStatus; sub.dispose(); } });
        const pid = await t.processId;
        t.show(true);
        return { pid: typeof pid === 'number' && pid > 0, name: t.name, active: vscode.window.activeTerminal === t, count: vscode.window.terminals.length };
      }
      case 'termSend': state.terminals.proc.sendText(args[0] || 'hi'); return true;
      case 'termClosed': return state.closed;
      case 'termPty': {
        const writeEm = new vscode.EventEmitter();
        const closeEm = new vscode.EventEmitter();
        const pty = {
          onDidWrite: writeEm.event, onDidClose: closeEm.event,
          open() { writeEm.fire('pty ready\r\n'); },
          close() { state.ptyClosed = true; },
          handleInput(d) { state.ptyInput += d; writeEm.fire('got ' + JSON.stringify(d) + '\r\n'); if (d.includes('quit')) closeEm.fire(7); },
        };
        const t = vscode.window.createTerminal({ name: 'WB Pty', pty });
        const sub = vscode.window.onDidCloseTerminal((x) => { if (x === t) { state.closed.pty = x.exitStatus; sub.dispose(); } });
        t.show();
        return true;
      }
      case 'termShell': {
        const t = vscode.window.createTerminal({ name: 'WB Shell' });
        const si = await new Promise((resolve) => {
          if (t.shellIntegration) return resolve(t.shellIntegration);
          const sub = vscode.window.onDidChangeTerminalShellIntegration((e) => { if (e.terminal === t) { sub.dispose(); resolve(e.shellIntegration); } });
          setTimeout(() => resolve(undefined), 8000);
        });
        if (!si) { t.dispose(); return { integration: false }; }
        const started = new Promise((r) => { const s = vscode.window.onDidStartTerminalShellExecution((e) => { if (e.terminal === t) { s.dispose(); r(true); } }); setTimeout(() => r(false), 8000); });
        const ended = new Promise((r) => { const s = vscode.window.onDidEndTerminalShellExecution((e) => { if (e.terminal === t) { s.dispose(); r(e.exitCode); } }); setTimeout(() => r('timeout'), 15000); });
        const ex = si.executeCommand('echo wbshell');
        let out = '';
        for await (const d of ex.read()) out += d;
        const r = { integration: true, started: await started, exitCode: await ended, output: out.includes('wbshell'), line: ex.commandLine.value };
        t.dispose();
        return r;
      }
      case 'task': {
        const tasks = await vscode.tasks.fetchTasks({ type: 'wbtask' });
        const ended = new Promise((r) => { const s = vscode.tasks.onDidEndTaskProcess((e) => { s.dispose(); r(e.exitCode); }); setTimeout(() => r('timeout'), 15000); });
        const started = new Promise((r) => { const s = vscode.tasks.onDidStartTask((e) => { s.dispose(); r(e.execution.task.name); }); setTimeout(() => r('timeout'), 15000); });
        await vscode.tasks.executeTask(tasks[0]);
        return { count: tasks.length, started: await started, exitCode: await ended, executions: vscode.tasks.taskExecutions.length };
      }
      case 'auth': {
        const r = {};
        r.silent = await vscode.authentication.getSession('wbauth', ['read'], { silent: true }) === undefined;
        const changes = [];
        const sub = vscode.authentication.onDidChangeSessions((e) => changes.push(e.provider.id));
        const s = await vscode.authentication.getSession('wbauth', ['read'], { createIfNone: true });
        r.created = s && s.account.label;
        r.again = (await vscode.authentication.getSession('wbauth', ['read'], {})).id;
        r.accounts = (await vscode.authentication.getAccounts('wbauth')).map((a) => a.id);
        try { await vscode.authentication.getSession('nobody', [], { createIfNone: true }); r.unknown = 'no error'; } catch (e) { r.unknown = 'error'; }
        r.unknownSilent = await vscode.authentication.getSession('nobody', [], { silent: true }) === undefined;
        r.changes = changes;
        sub.dispose();
        return r;
      }
      case 'notebook': {
        const nb = await vscode.workspace.openNotebookDocument(vscode.Uri.file(args[0]));
        const untitled = await vscode.workspace.openNotebookDocument('wbnb', new vscode.NotebookData([new vscode.NotebookCellData(vscode.NotebookCellKind.Markup, '# hi', 'markdown')]));
        return { type: nb.notebookType, cells: nb.cellCount, first: nb.cellAt(0).document.getText(), untitled: untitled.cellCount, open: vscode.workspace.notebookDocuments.length };
      }
      case 'custom': {
        await vscode.commands.executeCommand('vscode.openWith', vscode.Uri.file(args[0]), 'wbTest.custom');
        await until(() => state.customResolved, 3000);
        return { resolved: state.customResolved, tab: tabsSummary().find((t) => t.kind === 'custom') };
      }
      case 'misc': {
        const r = {};
        const cc = vscode.comments.createCommentController('wb', 'WB');
        const th = cc.createCommentThread(vscode.Uri.file(args[0]), new vscode.Range(0, 0, 0, 0), []);
        r.comment = typeof th.dispose === 'function' && th.uri.fsPath === vscode.Uri.file(args[0]).fsPath;
        const tc = vscode.tests.createTestController('wbt', 'WB Tests');
        const item = tc.createTestItem('t1', 'Test 1');
        tc.items.add(item);
        r.tests = tc.items.size === 1 && typeof tc.createRunProfile('Run', vscode.TestRunProfileKind.Run, () => {}).dispose === 'function';
        const sc = vscode.scm.createSourceControl('wbscm', 'WB SCM');
        r.scm = sc.createResourceGroup('g', 'Group').resourceStates.length === 0 && sc.inputBox.value === '';
        r.chat = typeof vscode.chat.createChatParticipant('wb.chat', () => {}).dispose === 'function';
        r.models = (await vscode.lm.selectChatModels()).length;
        r.commands = (await vscode.commands.getCommands()).filter((c) => ['vscode.diff', 'vscode.open', 'setContext', 'workbench.action.openSettings'].includes(c)).length;
        r.env = { uriScheme: vscode.env.uriScheme, appName: vscode.env.appName, uiKind: vscode.env.uiKind, remoteName: vscode.env.remoteName === undefined, shell: !!vscode.env.shell };
        await vscode.env.clipboard.writeText('wb-clip');
        r.clipboard = await vscode.env.clipboard.readText();
        r.encode = await vscode.workspace.decode(await vscode.workspace.encode('héllo'));
        const before = (vscode.workspace.workspaceFolders || []).length;
        const changed = new Promise((res) => { const s = vscode.workspace.onDidChangeWorkspaceFolders((e) => { s.dispose(); res(e.added.length); }); setTimeout(() => res(-1), 3000); });
        r.updateFolders = vscode.workspace.updateWorkspaceFolders(before, 0, { uri: vscode.Uri.file(args[1]) });
        r.foldersAdded = await changed;
        r.folders = (vscode.workspace.workspaceFolders || []).length - before;
        vscode.workspace.updateWorkspaceFolders(before, 1);
        r.ext = !!vscode.extensions.getExtension('radide-test.workbench-api') && vscode.extensions.getExtension('RADIDE-TEST.workbench-api').id;
        r.storage = !!context.storageUri && !!context.globalStorageUri && !!context.logUri && context.extensionMode === vscode.ExtensionMode.Production;
        context.globalState.setKeysForSync(['x']);
        await context.secrets.store('k', 'secret');
        r.secret = await context.secrets.get('k');
        const bp = new vscode.SourceBreakpoint(new vscode.Location(vscode.Uri.file(args[0]), new vscode.Position(0, 0)));
        vscode.debug.addBreakpoints([bp]);
        r.breakpoints = vscode.debug.breakpoints.length;
        vscode.debug.removeBreakpoints([bp]);
        r.state = vscode.window.state.focused !== undefined;
        r.open = await vscode.env.openExternal(vscode.Uri.parse(vscode.env.uriScheme + '://radide-test.workbench-api/fromOpenExternal?x=1'));
        return r;
      }
      case 'visible': {
        const ed = vscode.window.activeTextEditor;
        return { events: state.visibleRangeEvents, ranges: ed ? ed.visibleRanges.map((r) => [r.start.line, r.end.line]) : null, file: ed ? path.basename(ed.document.fileName) : null };
      }
      case 'setOptions': { const ed = vscode.window.activeTextEditor; if (!ed) return false; ed.options = { tabSize: 2, insertSpaces: true }; return ed.options.tabSize; }
      default: return 'unknown step ' + step;
    }
  }));
  log('activated');
}

module.exports = { activate, deactivate() {} };
