// RAD IDE test extension (MIT): exercises the VS Code API subset of the RAD IDE extension host.
const vscode = require('vscode');

function activate(context) {
  const out = vscode.window.createOutputChannel('Hello Commands');
  out.appendLine('activated, vscode.version=' + vscode.version + ', appName=' + vscode.env.appName);

  // ---- status bar item
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  item.text = '$(smiley) Hello';
  item.tooltip = 'Say hello';
  item.command = 'helloCommands.sayHello';
  item.show();
  context.subscriptions.push(item);

  // ---- state
  const runs = context.globalState.get('runs', 0) + 1;
  context.globalState.update('runs', runs);
  let changes = 0;
  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument((e) => { changes++; item.text = `$(smiley) Hello (${changes})`; }));
  context.subscriptions.push(vscode.workspace.onDidOpenTextDocument((d) => out.appendLine('opened ' + d.languageId + ' ' + d.fileName)));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument((d) => out.appendLine('saved ' + d.fileName)));

  // ---- commands
  context.subscriptions.push(vscode.commands.registerCommand('helloCommands.sayHello', async (who) => {
    const cfg = vscode.workspace.getConfiguration('helloCommands');
    let text = `${cfg.get('greeting')} ${who || 'World'}!`;
    if (cfg.get('shout')) text = text.toUpperCase();
    const choice = await vscode.window.showInformationMessage(text, 'Again', 'Close');
    out.appendLine('message choice: ' + choice);
    return text;
  }));
  context.subscriptions.push(vscode.commands.registerCommand('helloCommands.pick', async () => {
    const pick = await vscode.window.showQuickPick([{ label: 'Apple', description: 'red' }, { label: 'Banana', description: 'yellow' }], { placeHolder: 'Pick a fruit' });
    out.appendLine('picked: ' + (pick && pick.label));
    return pick && pick.label;
  }));
  context.subscriptions.push(vscode.commands.registerCommand('helloCommands.ask', async () => {
    const name = await vscode.window.showInputBox({ prompt: 'Your name', validateInput: (v) => (v.trim() ? undefined : 'Please type a name') });
    if (name) await vscode.workspace.getConfiguration('helloCommands').update('greeting', 'Hi ' + name, vscode.ConfigurationTarget.Global);
    return name;
  }));
  context.subscriptions.push(vscode.commands.registerTextEditorCommand('helloCommands.insertDate', (editor, edit) => {
    edit.insert(editor.selection.active, '2026-01-01');
  }));
  context.subscriptions.push(vscode.commands.registerCommand('helloCommands.state', () => ({ runs, changes, docs: vscode.workspace.textDocuments.length, folders: (vscode.workspace.workspaceFolders || []).map((f) => f.name) })));
  context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((e) => {
    if (e.affectsConfiguration('helloCommands')) out.appendLine('configuration changed: greeting=' + vscode.workspace.getConfiguration('helloCommands').get('greeting'));
  }));

  // ---- language features for plain text
  const sel = { language: 'plaintext' };
  context.subscriptions.push(vscode.languages.registerCompletionItemProvider(sel, {
    provideCompletionItems(doc, pos, token, ctx) {
      const a = new vscode.CompletionItem('helloWorld', vscode.CompletionItemKind.Function);
      a.detail = 'from hello-commands';
      a.documentation = new vscode.MarkdownString('Inserts **hello world**');
      a.insertText = new vscode.SnippetString('hello(${1:world})');
      const b = new vscode.CompletionItem('trigger:' + (ctx.triggerCharacter || 'none'), vscode.CompletionItemKind.Keyword);
      return [a, b];
    },
  }, '@'));
  context.subscriptions.push(vscode.languages.registerHoverProvider(sel, {
    provideHover(doc, pos) {
      const r = doc.getWordRangeAtPosition(pos);
      if (!r) return undefined;
      return new vscode.Hover(new vscode.MarkdownString('Word: **' + doc.getText(r) + '**'), r);
    },
  }));
  context.subscriptions.push(vscode.languages.registerDefinitionProvider(sel, {
    provideDefinition(doc, pos) { return new vscode.Location(doc.uri, new vscode.Position(0, 0)); },
  }));
  context.subscriptions.push(vscode.languages.registerDocumentFormattingEditProvider(sel, {
    provideDocumentFormattingEdits(doc) {
      const edits = [];
      for (let i = 0; i < doc.lineCount; i++) {
        const line = doc.lineAt(i);
        const trimmed = line.text.replace(/\s+$/, '');
        if (trimmed !== line.text) edits.push(vscode.TextEdit.replace(line.range, trimmed));
      }
      return edits;
    },
  }));
  const diags = vscode.languages.createDiagnosticCollection('hello');
  context.subscriptions.push(diags);
  const lint = (doc) => {
    if (doc.languageId !== 'plaintext') return;
    const list = [];
    for (let i = 0; i < doc.lineCount; i++) {
      const idx = doc.lineAt(i).text.indexOf('TODO');
      if (idx >= 0) {
        const d = new vscode.Diagnostic(new vscode.Range(i, idx, i, idx + 4), 'TODO found', vscode.DiagnosticSeverity.Warning);
        d.source = 'hello';
        d.code = 'todo';
        list.push(d);
      }
    }
    diags.set(doc.uri, list);
  };
  vscode.workspace.textDocuments.forEach(lint);
  context.subscriptions.push(vscode.workspace.onDidOpenTextDocument(lint), vscode.workspace.onDidChangeTextDocument((e) => lint(e.document)));
  context.subscriptions.push(vscode.languages.registerCodeActionsProvider(sel, {
    provideCodeActions(doc, range, ctx) {
      return ctx.diagnostics.filter((d) => d.code === 'todo').map((d) => {
        const a = new vscode.CodeAction('Replace TODO with DONE', vscode.CodeActionKind.QuickFix);
        a.edit = new vscode.WorkspaceEdit();
        a.edit.replace(doc.uri, d.range, 'DONE');
        a.diagnostics = [d];
        return a;
      });
    },
  }, { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }));
  vscode.languages.setLanguageConfiguration('plaintext', { comments: { lineComment: '#' }, wordPattern: /[A-Za-z_]\w*/ });

  // ---- tree view
  const fruits = { Fruits: ['Apple', 'Banana'], Colors: ['Red'] };
  context.subscriptions.push(vscode.window.registerTreeDataProvider('helloCommands.view', {
    getChildren(el) { return el ? fruits[el] || [] : Object.keys(fruits); },
    getTreeItem(el) {
      const item = new vscode.TreeItem(el, fruits[el] ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None);
      if (!fruits[el]) item.command = { command: 'helloCommands.sayHello', title: 'Hello', arguments: [el] };
      return item;
    },
  }));

  // an unsupported API must not break activation
  try { vscode.window.createWebviewTextEditorInset(undefined, 0, 1, {}); } catch (e) { out.appendLine('inset threw: ' + e); }   // a proposed API RAD IDE does not have
  return { hello: (who) => `${vscode.workspace.getConfiguration('helloCommands').get('greeting')} ${who}` };
}

function deactivate() {}

module.exports = { activate, deactivate };
