// RAD IDE test extension (MIT): exercises view containers, tree views, menus and built-in VS Code commands.
const vscode = require('vscode');

const calls = [];          // every command / event this extension saw (read back through ref.state)
const record = (name, data) => calls.push({ name, data });

const TREE = {
  fruits: { label: 'Fruits', children: ['apple', 'banana'] },
  veg: { label: 'Vegetables', children: ['carrot'] },
  apple: { label: 'Apple', parent: 'fruits', ctx: 'fruit', check: true },
  banana: { label: 'Banana', parent: 'fruits', ctx: 'fruit' },
  carrot: { label: 'Carrot', parent: 'veg', ctx: 'veg' },
};

class Tree {
  constructor() { this._em = new vscode.EventEmitter(); this.onDidChangeTreeData = this._em.event; }
  getChildren(el) { return el ? (TREE[el].children || []) : ['fruits', 'veg']; }
  getParent(el) { return TREE[el].parent; }
  getTreeItem(el) {
    const n = TREE[el];
    const it = new vscode.TreeItem(n.label, n.children ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None);
    it.id = el;
    it.contextValue = n.ctx;
    it.iconPath = new vscode.ThemeIcon(n.children ? 'folder' : 'symbol-misc');
    if (n.check !== undefined) it.checkboxState = n.check ? vscode.TreeItemCheckboxState.Checked : vscode.TreeItemCheckboxState.Unchecked;
    if (!n.children) it.command = { command: 'ref.addItem', title: 'click', arguments: [el] };
    it.description = n.children ? `${n.children.length} items` : undefined;
    return it;
  }
  resolveTreeItem(item) { item.tooltip = 'resolved: ' + item.label; return item; }
}

class Empty {
  constructor() { this.items = []; this._em = new vscode.EventEmitter(); this.onDidChangeTreeData = this._em.event; }
  getChildren() { return this.items; }
  getTreeItem(el) { return new vscode.TreeItem(el); }
}

function activate(context) {
  const tree = new Tree();
  const view = vscode.window.createTreeView('ref.tree', { treeDataProvider: tree, canSelectMany: true, showCollapseAll: true });
  view.onDidChangeSelection((e) => record('selection', e.selection));
  view.onDidChangeVisibility((e) => record('visible', e.visible));
  view.onDidExpandElement((e) => record('expand', e.element));
  view.onDidChangeCheckboxState((e) => record('checkbox', e.items.map(([el, st]) => [el, st])));
  const empty = new Empty();
  context.subscriptions.push(view,
    vscode.window.registerTreeDataProvider('ref.empty', empty),
    vscode.window.registerTreeDataProvider('ref.panelTree', { getChildren: () => ['p1'], getTreeItem: (e) => new vscode.TreeItem('Panel item ' + e) }),
    vscode.window.registerTreeDataProvider('ref.whenTree', { getChildren: () => ['w1'], getTreeItem: (e) => new vscode.TreeItem('When item ' + e) }),
    vscode.window.registerWebviewViewProvider('ref.webview', {
      resolveWebviewView(wv) { wv.webview.options = { enableScripts: true }; wv.webview.html = '<html><body><h3 id="t">Ref Webview</h3></body></html>'; record('webviewResolved', true); },
    }));
  // a completion provider (for vscode.executeCompletionItemProvider) and a call hierarchy (prepareCallHierarchy ...)
  context.subscriptions.push(vscode.languages.registerCompletionItemProvider('reftest', {
    provideCompletionItems(doc, pos, tok, ctx) {
      const a = new vscode.CompletionItem('refAlpha', vscode.CompletionItemKind.Function);
      const b = new vscode.CompletionItem('refBeta', vscode.CompletionItemKind.Variable);
      return new vscode.CompletionList([a, b], ctx.triggerCharacter === '.');
    },
    resolveCompletionItem(item) { item.detail = 'resolved ' + item.label; return item; },
  }, '.'));
  context.subscriptions.push(vscode.languages.registerCallHierarchyProvider('reftest', {
    prepareCallHierarchy(doc, pos) { return new vscode.CallHierarchyItem(vscode.SymbolKind.Function, 'main', '', doc.uri, new vscode.Range(0, 0, 0, 4), new vscode.Range(0, 0, 0, 4)); },
    provideCallHierarchyIncomingCalls(item) { return [new vscode.CallHierarchyIncomingCall(new vscode.CallHierarchyItem(vscode.SymbolKind.Function, 'caller', '', item.uri, item.range, item.range), [item.range])]; },
    provideCallHierarchyOutgoingCalls() { return []; },
  }));
  context.subscriptions.push(vscode.languages.registerCodeLensProvider('reftest', {
    provideCodeLenses() { return [new vscode.CodeLens(new vscode.Range(0, 0, 0, 1)), new vscode.CodeLens(new vscode.Range(1, 0, 1, 1))]; },
    resolveCodeLens(lens) { lens.command = { title: 'resolved', command: 'ref.state' }; return lens; },
  }));

  const reg = (id, fn) => context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  for (const id of ['ref.refresh', 'ref.addItem', 'ref.itemAction', 'ref.titleOverflow', 'ref.editorTitle', 'ref.editorTitleOther', 'ref.disabled']) {
    reg(id, (...args) => {
      record(id, args.map((a) => (a instanceof vscode.Uri ? a.toString() : a)));
      if (id === 'ref.refresh') tree._em.fire();
    });
  }
  reg('ref.state', () => calls.slice());
  reg('ref.clear', () => { calls.length = 0; });
  // run any command from inside the extension host: {value} or {error}
  reg('ref.exec', async (id, ...args) => {
    try {
      const v = await vscode.commands.executeCommand(id, ...args.map((a) => (a && a.$uri ? vscode.Uri.parse(a.$uri) : a)));
      return { value: summarize(v) };
    } catch (e) { return { error: String(e && e.message || e) }; }
  });
  reg('ref.api', async () => {
    const cmds = await vscode.commands.getCommands(true);
    return {
      version: vscode.version,
      portable: vscode.env.isAppPortable,
      types: ['DataTransfer', 'DataTransferItem', 'TimelineItem', 'LanguageModelDataPart', 'LanguageModelToolResult', 'McpStdioServerDefinition',
        'QuickInputButtonLocation', 'InputBoxValidationSeverity', 'TestCoverageCount', 'FileCoverage', 'TelemetryTrustedValue', 'ChatResponseMarkdownPart',
        'DebugStackFrame', 'IndentAction', 'TerminalShellExecutionCommandLineConfidence'].filter((n) => typeof vscode[n] !== 'undefined'),
      dataTransfer: new vscode.DataTransfer([['Text/Plain', new vscode.DataTransferItem('x')]]).get('text/plain').value,
      kindContains: vscode.DocumentDropOrPasteEditKind.Text.contains(vscode.DocumentDropOrPasteEditKind.TextUpdateImports),
      fileCoverage: vscode.FileCoverage.fromDetails(vscode.Uri.file('/x'), [new vscode.StatementCoverage(1, new vscode.Position(0, 0)), new vscode.StatementCoverage(0, new vscode.Position(1, 0))]).statementCoverage,
      hasCommands: ['workbench.action.openSettings', 'vscode.executeDocumentSymbolProvider', 'ref.refresh', 'workbench.view.explorer'].filter((c) => cmds.includes(c)),
      timeline: typeof vscode.workspace.registerTimelineProvider === 'function' && typeof vscode.lm.registerLanguageModelChatProvider === 'function',
    };
  });
  reg('ref.reveal', async () => { await view.reveal('banana', { select: true, focus: false, expand: false }); return true; });
  reg('ref.decorate', () => { view.message = 'Ref message'; view.description = 'desc'; view.badge = { value: 3, tooltip: 'three' }; return true; });
  reg('ref.empty.fill', () => { empty.items = ['filled']; empty._em.fire(); return true; });
  record('activated', true);
}

function summarize(v) {
  if (v === undefined) return '<undefined>';
  if (v instanceof vscode.CompletionList) return { items: v.items.map((i) => ({ label: i.label, detail: i.detail })), isIncomplete: v.isIncomplete };
  if (Array.isArray(v)) return v.map((x) => (x && x.name ? x.name : x && x.from ? 'from:' + x.from.name : x && x.command ? 'lens:' + x.command.title : x && x.range ? 'lens:unresolved' : x));
  return v;
}

module.exports = { activate, deactivate() {} };
