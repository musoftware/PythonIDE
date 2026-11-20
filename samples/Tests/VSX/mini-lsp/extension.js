// RAD IDE test extension (MIT): the standard vscode-languageclient pattern of VS Code language extensions.
const path = require('path');
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');

let client;

function activate(context) {
  const serverModule = context.asAbsolutePath(path.join('server.js'));
  const serverOptions = {
    run: { module: serverModule, transport: TransportKind.ipc },
    debug: { module: serverModule, transport: TransportKind.ipc },
  };
  const clientOptions = {
    documentSelector: [{ scheme: 'file', language: 'minilang' }],
    synchronize: { configurationSection: 'miniLang' },
  };
  client = new LanguageClient('miniLang', 'Mini Lang Server', serverOptions, clientOptions);
  return client.start();
}

function deactivate() { return client ? client.stop() : undefined; }

module.exports = { activate, deactivate };
