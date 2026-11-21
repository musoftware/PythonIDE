// ES module loaded through webview.asWebviewUri (the case file:// pages cannot do)
const vscode = acquireVsCodeApi();
const out = document.getElementById('out');
window.addEventListener('message', (e) => {
  const m = e.data;
  if (m && m.type === 'echo') {
    out.textContent = 'echo: ' + m.text;
    vscode.setState({ last: m.text });
    vscode.postMessage({ type: 'echoed', text: m.text, bg: getComputedStyle(document.documentElement).getPropertyValue('--vscode-editor-background').trim(), kind: document.body.className });
  }
});
document.getElementById('btn').addEventListener('click', () => vscode.postMessage({ type: 'clicked' }));
vscode.postMessage({ type: 'ready', module: true, state: vscode.getState() });
