// RAD IDE test extension (MIT): Command Palette entries and vscode.commands.executeCommand of VS Code's
// built-in editor / workbench commands.
const vscode = require('vscode');

function activate(context) {
  const calls = [];
  const reg = (id, fn) => context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  reg('paletteTest.visible', () => { calls.push('visible'); return 'visible'; });
  reg('paletteTest.hidden', () => { calls.push('hidden'); return 'hidden'; });
  reg('paletteTest.disabled', () => { calls.push('disabled'); return 'disabled'; });
  reg('paletteTest.calls', () => calls.slice());
  // paletteTest.exec(id, ...args) -> {value} | {error}
  reg('paletteTest.exec', async (id, ...args) => {
    try {
      const v = await vscode.commands.executeCommand(id, ...args);
      return { value: v === undefined ? '<undefined>' : v };
    } catch (e) {
      return { error: String(e && e.message || e) };
    }
  });
  reg('paletteTest.editorText', () => {
    const ed = vscode.window.activeTextEditor;
    return ed ? { text: ed.document.getText(), path: ed.document.uri.fsPath } : null;
  });
}

function deactivate() {}

module.exports = { activate, deactivate };
