'use strict';
// vscode API values <-> LSP-shaped JSON (the IDE side reuses radide/lsp.py's converters on LSP JSON),
// and <-> the IDE's own shapes (diagnostics, edits).

const T = require('./types');

const isWin = process.platform === 'win32';

function ideUri(uri) {
  // a file URI the IDE turns back into a path with QUrl(uri).toLocalFile() (like pathlib's as_uri())
  if (!uri) return '';
  if (typeof uri === 'string') return uri;
  if (uri.scheme !== 'file') return uri.toString();
  let p = uri.fsPath.replace(/\\/g, '/');
  if (!p.startsWith('/')) p = '/' + p;
  return 'file://' + (uri.authority ? uri.authority : '') + p.split('/').map((s, i) =>
    (i === 1 && /^[a-zA-Z]:$/.test(s)) ? s.toUpperCase() : encodeURIComponent(s)).join('/');
}

function uriFromIde(s) {
  if (!s) return undefined;
  if (typeof s !== 'string') return T.Uri.revive(s);
  if (/^[a-zA-Z]:[\\/]/.test(s) || s.startsWith('\\\\') || (!isWin && s.startsWith('/'))) return T.Uri.file(s);
  const u = T.Uri.parse(s);
  return u.scheme === 'file' ? T.Uri.file(u.fsPath) : u;
}

const pos = (p) => ({ line: p.line, character: p.character });
const range = (r) => r ? { start: pos(r.start), end: pos(r.end) } : undefined;
const toPosition = (p) => new T.Position(p.line, p.character);
const toRange = (r) => new T.Range(toPosition(r.start), toPosition(r.end));

function markup(v) {
  if (v === undefined || v === null) return undefined;
  if (typeof v === 'string') return v;
  if (T.MarkdownString.isMarkdownString(v) || (typeof v.value === 'string' && v.language === undefined)) return { kind: 'markdown', value: v.value };
  if (typeof v.value === 'string' && v.language !== undefined) return { kind: 'markdown', value: '```' + v.language + '\n' + v.value + '\n```' };
  return String(v);
}

function markdownText(v) {
  const m = markup(v);
  return m === undefined ? '' : typeof m === 'string' ? m : m.value;
}

// ---------------------------------------------------------------------------- commands (args cached)
class CommandCache {
  constructor() { this._n = 0; this._map = new Map(); }
  put(cmd) {
    if (!cmd) return undefined;
    if (typeof cmd === 'string') return { title: '', command: cmd };
    const args = cmd.arguments;
    let lspArgs;
    if (args && args.length) {
      const id = ++this._n;
      this._map.set(id, args);
      if (this._map.size > 5000) this._map.delete(this._map.keys().next().value);
      lspArgs = [{ $vsxArgs: id }];
    }
    return { title: cmd.title || '', command: cmd.command, arguments: lspArgs, tooltip: cmd.tooltip };
  }
  args(lspArgs) {
    if (Array.isArray(lspArgs) && lspArgs.length === 1 && lspArgs[0] && lspArgs[0].$vsxArgs) return this._map.get(lspArgs[0].$vsxArgs) || [];
    return lspArgs || [];
  }
}

// ---------------------------------------------------------------------------- completion
function completionItem(it, cmds) {
  if (typeof it === 'string') it = new T.CompletionItem(it);
  const label = typeof it.label === 'string' ? it.label : (it.label && it.label.label) || '';
  const out = { label };
  if (it.label && typeof it.label === 'object' && (it.label.detail || it.label.description)) {
    out.labelDetails = { detail: it.label.detail, description: it.label.description };
  }
  if (typeof it.kind === 'number') out.kind = it.kind <= 24 ? it.kind + 1 : 1;
  if (it.detail) out.detail = String(it.detail);
  if (it.documentation) out.documentation = markup(it.documentation);
  if (it.sortText) out.sortText = it.sortText;
  if (it.filterText) out.filterText = it.filterText;
  if (it.preselect) out.preselect = true;
  if (it.tags) out.tags = it.tags;
  let text = it.insertText;
  if (text === undefined || text === null) text = label;
  if (T.SnippetString.isSnippetString(text)) { out.insertTextFormat = 2; text = text.value; } else text = String(text);
  if (it.textEdit) {                     // deprecated API
    out.textEdit = { range: range(it.textEdit.range), newText: it.textEdit.newText };
  } else if (it.range) {
    const r = T.Range.isRange(it.range) ? it.range : (it.range.replacing || it.range.inserting);
    out.textEdit = { range: range(r), newText: text };
  } else out.insertText = text;
  if (it.additionalTextEdits) out.additionalTextEdits = it.additionalTextEdits.map((e) => ({ range: range(e.range), newText: e.newText }));
  if (it.command) out.command = cmds.put(it.command);
  if (it.commitCharacters) out.commitCharacters = it.commitCharacters;
  return out;
}

// ---------------------------------------------------------------------------- hover / locations
function hover(h) {
  if (!h) return null;
  const parts = (h.contents || []).map(markdownText).filter((s) => s);
  if (!parts.length) return null;
  return { contents: { kind: 'markdown', value: parts.join('\n\n---\n\n') }, range: range(h.range) };
}

function location(l) {
  if (!l) return null;
  if (l.targetUri) return { uri: ideUri(l.targetUri), range: range(l.targetSelectionRange || l.targetRange), targetUri: ideUri(l.targetUri), targetRange: range(l.targetRange), targetSelectionRange: range(l.targetSelectionRange || l.targetRange) };
  return { uri: ideUri(l.uri), range: range(l.range) };
}

function locations(v) {
  if (!v) return [];
  return (Array.isArray(v) ? v : [v]).map(location).filter(Boolean);
}

// ---------------------------------------------------------------------------- signature help
function signatureHelp(s) {
  if (!s || !s.signatures || !s.signatures.length) return null;
  return {
    activeSignature: s.activeSignature || 0,
    activeParameter: s.activeParameter || 0,
    signatures: s.signatures.map((sig) => ({
      label: sig.label,
      documentation: markup(sig.documentation),
      activeParameter: sig.activeParameter,
      parameters: (sig.parameters || []).map((p) => ({ label: p.label, documentation: markup(p.documentation) })),
    })),
  };
}

// ---------------------------------------------------------------------------- edits
function textEdits(list) {
  return (list || []).filter(Boolean).map((e) => ({ range: range(e.range), newText: e.newText !== undefined ? e.newText : (e.snippet ? e.snippet.value : '') }));
}

function workspaceEdit(we) {
  if (!we) return null;
  const changes = {};
  const documentChanges = [];
  let fileOps = false;
  for (const e of we._edits || []) {
    if (e._type === 1) {
      fileOps = true;
      if (e.from && e.to) documentChanges.push({ kind: 'rename', oldUri: ideUri(e.from), newUri: ideUri(e.to), options: e.options });
      else if (e.to) documentChanges.push({ kind: 'create', uri: ideUri(e.to), options: e.options });
      else documentChanges.push({ kind: 'delete', uri: ideUri(e.from), options: e.options });
    } else {
      const k = ideUri(e.uri);
      (changes[k] = changes[k] || []).push({ range: range(e.edit.range), newText: e.edit.newText });
      documentChanges.push({ textDocument: { uri: k, version: null }, edits: [{ range: range(e.edit.range), newText: e.edit.newText }] });
    }
  }
  return fileOps ? { documentChanges } : { changes };
}

// IDE apply-edit payload: {edits: [{path, edits: [{range: [l1, c1, l2, c2], text}]}], files: [...]}
function ideWorkspaceEdit(we) {
  const byPath = new Map();
  const files = [];
  for (const e of we._edits || []) {
    if (e._type === 1) {
      files.push({ op: e.from && e.to ? 'rename' : e.to ? 'create' : 'delete', from: e.from && e.from.fsPath, to: e.to && e.to.fsPath, options: e.options || {}, contents: e.options && e.options.contents ? Buffer.from(e.options.contents).toString('utf8') : undefined });
      continue;
    }
    const p = e.uri.scheme === 'file' ? e.uri.fsPath : e.uri.toString();
    if (!byPath.has(p)) byPath.set(p, []);
    const r = e.edit.range;
    byPath.get(p).push({ range: [r.start.line, r.start.character, r.end.line, r.end.character], text: e.edit.newText });
  }
  return { edits: [...byPath.entries()].map(([path, edits]) => ({ path, edits })), files };
}

function lspWorkspaceEditToVscode(lwe) {
  const we = new T.WorkspaceEdit();
  if (!lwe) return we;
  for (const [uri, edits] of Object.entries(lwe.changes || {})) {
    for (const e of edits) we.replace(uriFromIde(uri), toRange(e.range), e.newText);
  }
  for (const dc of lwe.documentChanges || []) {
    if (dc.textDocument) for (const e of dc.edits || []) we.replace(uriFromIde(dc.textDocument.uri), toRange(e.range), e.newText);
    else if (dc.kind === 'create') we.createFile(uriFromIde(dc.uri), dc.options);
    else if (dc.kind === 'rename') we.renameFile(uriFromIde(dc.oldUri), uriFromIde(dc.newUri), dc.options);
    else if (dc.kind === 'delete') we.deleteFile(uriFromIde(dc.uri), dc.options);
  }
  return we;
}

// ---------------------------------------------------------------------------- diagnostics
const SEV = ['error', 'warning', 'info', 'hint'];

function ideDiagnostic(d) {
  const code = d.code && typeof d.code === 'object' ? d.code.value : d.code;
  return { line: d.range.start.line, col: d.range.start.character, endLine: d.range.end.line, endCol: d.range.end.character,
    message: String(d.message || ''), severity: SEV[d.severity === undefined ? 0 : d.severity] || 'info',
    source: d.source || '', code: code === undefined ? '' : code };
}

function lspDiagnostic(d) {
  const code = d.code && typeof d.code === 'object' ? d.code.value : d.code;
  return { range: range(d.range), message: String(d.message || ''), severity: (d.severity === undefined ? 0 : d.severity) + 1,
    source: d.source, code };
}

function vscodeDiagnostic(ld) {
  const d = new T.Diagnostic(toRange(ld.range), ld.message || '', ld.severity ? ld.severity - 1 : 0);
  if (ld.source) d.source = ld.source;
  if (ld.code !== undefined && ld.code !== '') d.code = ld.code;
  return d;
}

// ---------------------------------------------------------------------------- code actions / symbols
function codeAction(a, cmds) {
  if (!a) return null;
  if (typeof a.command === 'string' && a.edit === undefined && a.kind === undefined && !a.diagnostics) {
    return { title: a.title, command: a.command, arguments: cmds.put(a).arguments };
  }
  const out = { title: a.title };
  if (a.kind) out.kind = a.kind.value;
  if (a.diagnostics) out.diagnostics = a.diagnostics.map(lspDiagnostic);
  if (a.edit) out.edit = workspaceEdit(a.edit);
  if (a.command) out.command = cmds.put(a.command);
  if (a.isPreferred) out.isPreferred = true;
  if (a.disabled) out.disabled = a.disabled;
  return out;
}

function documentSymbol(s) {
  if (s.location) return { name: s.name, kind: (s.kind || 0) + 1, containerName: s.containerName, location: location(s.location) };
  return { name: s.name, detail: s.detail, kind: (s.kind || 0) + 1, range: range(s.range), selectionRange: range(s.selectionRange),
    children: (s.children || []).map(documentSymbol) };
}

function inlayHint(h) {
  const label = typeof h.label === 'string' ? h.label : (h.label || []).map((p) => ({ value: p.value, tooltip: markup(p.tooltip) }));
  return { position: pos(h.position), label, kind: h.kind, paddingLeft: h.paddingLeft, paddingRight: h.paddingRight, tooltip: markup(h.tooltip) };
}

// ---------------------------------------------------------------------------- JSON for messages / results
function plain(v, depth = 0) {
  // something JSON can carry (results of commands); Uris become {uri, path}
  if (depth > 6 || v === undefined || typeof v === 'function') return undefined;
  if (v === null || typeof v !== 'object') return v;
  if (T.Uri.isUri(v)) return { $uri: v.toString(), path: v.scheme === 'file' ? v.fsPath : undefined };
  if (v instanceof T.Position) return pos(v);
  if (v instanceof T.Range) return range(v);
  if (Array.isArray(v)) return v.map((x) => plain(x, depth + 1));
  if (ArrayBuffer.isView(v)) return Array.from(v);
  const out = {};
  for (const k of Object.keys(v)) { if (k[0] !== '_') { const x = plain(v[k], depth + 1); if (x !== undefined) out[k] = x; } }
  return out;
}

module.exports = {
  ideUri, uriFromIde, pos, range, toPosition, toRange, markup, markdownText, CommandCache, completionItem, hover,
  location, locations, signatureHelp, textEdits, workspaceEdit, ideWorkspaceEdit, lspWorkspaceEditToVscode,
  ideDiagnostic, lspDiagnostic, vscodeDiagnostic, codeAction, documentSymbol, inlayHint, plain,
};
