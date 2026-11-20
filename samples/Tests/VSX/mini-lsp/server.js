// RAD IDE test language server (MIT) built with vscode-languageserver.
const { createConnection, TextDocuments, ProposedFeatures, CompletionItemKind, DiagnosticSeverity, TextDocumentSyncKind } = require('vscode-languageserver/node');
const { TextDocument } = require('vscode-languageserver-textdocument');

const connection = createConnection(ProposedFeatures.all);
const documents = new TextDocuments(TextDocument);
const KEYWORDS = ['print', 'let', 'loop', 'stop'];

connection.onInitialize(() => ({
  capabilities: {
    textDocumentSync: TextDocumentSyncKind.Incremental,
    completionProvider: { triggerCharacters: ['.'] },
    hoverProvider: true,
    documentFormattingProvider: true,
  },
}));

function validate(doc) {
  const diagnostics = [];
  doc.getText().split(/\r?\n/).forEach((line, i) => {
    const idx = line.indexOf('bad');
    if (idx >= 0) diagnostics.push({ severity: DiagnosticSeverity.Error, range: { start: { line: i, character: idx }, end: { line: i, character: idx + 3 } }, message: "'bad' is not allowed", source: 'mini-lsp' });
  });
  connection.sendDiagnostics({ uri: doc.uri, diagnostics });
}

documents.onDidChangeContent((e) => validate(e.document));
connection.onCompletion(() => KEYWORDS.map((k) => ({ label: k, kind: CompletionItemKind.Keyword, detail: 'mini keyword' })));
connection.onHover((p) => {
  const doc = documents.get(p.textDocument.uri);
  const line = doc ? doc.getText().split(/\r?\n/)[p.position.line] || '' : '';
  const word = (line.slice(0, p.position.character).match(/\w*$/)[0] + line.slice(p.position.character).match(/^\w*/)[0]);
  return word ? { contents: { kind: 'markdown', value: `**${word}** (mini-lsp)` } } : null;
});
connection.onDocumentFormatting((p) => {
  const doc = documents.get(p.textDocument.uri);
  if (!doc) return [];
  return doc.getText().split(/\r?\n/).map((line, i) => ({ line, i })).filter((x) => /\s+$/.test(x.line))
    .map((x) => ({ range: { start: { line: x.i, character: x.line.replace(/\s+$/, '').length }, end: { line: x.i, character: x.line.length } }, newText: '' }));
});

documents.listen(connection);
connection.listen();
