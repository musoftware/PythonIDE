// RAD IDE test extension (MIT): a debugger contribution with a configuration provider, a ${command:...}
// variable and an optional inline adapter (setting miniDebug.inline).
const vscode = require('vscode');
const { InlineAdapter } = require('./adapter');

function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand('miniDebug.pickProgram', async () => {
    const ed = vscode.window.activeTextEditor;
    return ed ? ed.document.fileName : vscode.window.showInputBox({ prompt: 'Program to debug' });
  }));
  context.subscriptions.push(vscode.debug.registerDebugConfigurationProvider('minidbg', {
    resolveDebugConfiguration(folder, config) {
      if (!config.type && !config.request && !config.name) {
        const ed = vscode.window.activeTextEditor;
        if (ed && ed.document.languageId === 'minidbg') {
          config.type = 'minidbg'; config.name = 'Debug current file'; config.request = 'launch';
          config.program = '${command:PickProgram}'; config.stopOnEntry = false;
        }
      }
      return config;
    },
  }));
  if (vscode.workspace.getConfiguration('miniDebug').get('inline')) {
    context.subscriptions.push(vscode.debug.registerDebugAdapterDescriptorFactory('minidbg', {
      createDebugAdapterDescriptor() { return new vscode.DebugAdapterInlineImplementation(new InlineAdapter(vscode)); },
    }));
  }
  context.subscriptions.push(vscode.debug.onDidReceiveDebugSessionCustomEvent((e) => {
    vscode.window.createOutputChannel('Mini Debug').appendLine('custom event ' + e.event + ' ' + JSON.stringify(e.body));
  }));
  context.subscriptions.push(vscode.debug.onDidStartDebugSession((s) => vscode.window.createOutputChannel('Mini Debug').appendLine('session started ' + s.type)));
}

module.exports = { activate, deactivate() {} };
