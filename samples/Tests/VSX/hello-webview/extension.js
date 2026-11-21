const vscode = require('vscode');

function page(webview, root, title) {
  const nonce = Math.random().toString(36).slice(2);
  const js = webview.asWebviewUri(vscode.Uri.joinPath(root, 'media', 'main.mjs'));
  const css = webview.asWebviewUri(vscode.Uri.joinPath(root, 'media', 'style.css'));
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; img-src ${webview.cspSource} data:;">
<link rel="stylesheet" href="${css}"></head><body>
<h2>${title}</h2><button id="btn">Click me</button><div id="out">waiting</div>
<script nonce="${nonce}" type="module" src="${js}"></script></body></html>`;
}

function wire(ext, webview, label) {
  webview.onDidReceiveMessage((m) => {
    ext.messages.push(Object.assign({ from: label }, m));
    if (m.type === 'ready') webview.postMessage({ type: 'echo', text: label + ' hello' });
  });
}

function activate(context) {
  const state = { messages: [], panel: null };
  context.subscriptions.push(vscode.window.registerWebviewViewProvider('helloWebview.view', {
    resolveWebviewView(view) {
      view.webview.options = { enableScripts: true, localResourceRoots: [context.extensionUri] };
      wire(state, view.webview, 'view');
      view.webview.html = page(view.webview, context.extensionUri, 'Hello View');
    },
  }));
  context.subscriptions.push(vscode.commands.registerCommand('helloWebview.openPanel', () => {
    const panel = vscode.window.createWebviewPanel('helloWebview.panel', 'Hello Panel', vscode.ViewColumn.One,
      { enableScripts: true, localResourceRoots: [context.extensionUri] });
    wire(state, panel.webview, 'panel');
    panel.webview.html = page(panel.webview, context.extensionUri, 'Hello Panel');
    panel.onDidDispose(() => state.messages.push({ from: 'panel', type: 'disposed' }));
    state.panel = panel;
    return true;
  }));
  context.subscriptions.push(vscode.commands.registerCommand('helloWebview.messages', () => state.messages));
  context.subscriptions.push(vscode.commands.registerCommand('helloWebview.closePanel', () => { if (state.panel) state.panel.dispose(); return true; }));
}

module.exports = { activate, deactivate() {} };
