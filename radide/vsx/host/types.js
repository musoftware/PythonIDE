'use strict';
// The value classes and enums of the VS Code extension API (vscode.d.ts), written from the public
// API documentation. Behaviour follows VS Code where extensions depend on it (Uri encoding, Range
// normalisation, WorkspaceEdit entries, EventEmitter semantics ...).

const path = require('path');

// ============================================================================ Uri (vscode-uri compatible)
const _schemePattern = /^\w[\w\d+.-]*$/;
const _uriRegExp = /^(([^:/?#]+?):)?(\/\/([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?/;
const isWindows = process.platform === 'win32';

function _encode(s, allowSlash) {
  // encodeURIComponent but like vscode-uri: keep unreserved chars, optionally '/'
  let out = '';
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    const c = s.charCodeAt(i);
    if ((c >= 97 && c <= 122) || (c >= 65 && c <= 90) || (c >= 48 && c <= 57) || ch === '-' || ch === '.' ||
        ch === '_' || ch === '~' || (allowSlash && ch === '/')) {
      out += ch;
    } else if (c >= 0xD800 && c <= 0xDBFF && i + 1 < s.length) {
      out += encodeURIComponent(s.substr(i, 2)); i++;
    } else {
      out += encodeURIComponent(ch);
    }
  }
  return out;
}

function _decode(s) {
  try { return decodeURIComponent(s); } catch (_) { return s; }
}

class Uri {
  constructor(scheme, authority, p, query, fragment) {
    if (typeof scheme === 'object' && scheme) {
      ({ scheme, authority, path: p, query, fragment } = scheme);
    }
    this.scheme = scheme || 'file';
    this.authority = authority || '';
    p = p || '';
    if (this.scheme === 'file' || this.scheme === 'http' || this.scheme === 'https') {
      if (!p) p = '/'; else if (p[0] !== '/') p = '/' + p;
    }
    this.path = p;
    this.query = query || '';
    this.fragment = fragment || '';
    if (!_schemePattern.test(this.scheme)) throw new Error('[UriError]: Scheme contains illegal characters.');
  }

  static isUri(thing) {
    return thing instanceof Uri || (!!thing && typeof thing.authority === 'string' && typeof thing.fragment === 'string' &&
      typeof thing.path === 'string' && typeof thing.query === 'string' && typeof thing.scheme === 'string' &&
      typeof thing.fsPath === 'string' && typeof thing.with === 'function' && typeof thing.toString === 'function');
  }

  static parse(value, _strict) {
    const m = _uriRegExp.exec(String(value));
    if (!m) return new Uri('file', '', '', '', '');
    return new Uri(m[2] || 'file', _decode(m[4] || ''), _decode(m[5] || ''), _decode(m[7] || ''), _decode(m[9] || ''));
  }

  static file(fsPath) {
    let authority = '';
    let p = String(fsPath);
    if (isWindows) p = p.replace(/\\/g, '/');
    if (p[0] === '/' && p[1] === '/') {                       // UNC
      const idx = p.indexOf('/', 2);
      if (idx === -1) { authority = p.substring(2); p = '/'; } else { authority = p.substring(2, idx); p = p.substring(idx) || '/'; }
    }
    return new Uri('file', authority, p, '', '');
  }

  static from(c) { return new Uri(c.scheme, c.authority, c.path, c.query, c.fragment); }

  static joinPath(base, ...segments) {
    if (!base.path) throw new Error('[UriError]: cannot call joinPath on URI without path');
    let p;
    if (isWindows && base.scheme === 'file') p = Uri.file(path.win32.join(base.fsPath, ...segments)).path;
    else p = path.posix.join(base.path, ...segments);
    return base.with({ path: p });
  }

  static revive(data) {
    if (!data) return data;
    if (data instanceof Uri) return data;
    return new Uri(data.scheme, data.authority, data.path, data.query, data.fragment);
  }

  get fsPath() {
    let value;
    if (this.authority && this.path.length > 1 && this.scheme === 'file') value = `//${this.authority}${this.path}`;
    else if (this.path.charCodeAt(0) === 47 && /^\/[a-zA-Z]:/.test(this.path)) value = this.path[1].toLowerCase() + this.path.substr(2);
    else value = this.path;
    if (isWindows) value = value.replace(/\//g, '\\');
    return value;
  }

  with(change) {
    if (!change) return this;
    let { scheme, authority, path: p, query, fragment } = change;
    if (scheme === undefined) scheme = this.scheme; else if (scheme === null) scheme = '';
    if (authority === undefined) authority = this.authority; else if (authority === null) authority = '';
    if (p === undefined) p = this.path; else if (p === null) p = '';
    if (query === undefined) query = this.query; else if (query === null) query = '';
    if (fragment === undefined) fragment = this.fragment; else if (fragment === null) fragment = '';
    if (scheme === this.scheme && authority === this.authority && p === this.path && query === this.query &&
        fragment === this.fragment) return this;
    return new Uri(scheme, authority, p, query, fragment);
  }

  toString(skipEncoding) {
    const enc = skipEncoding ? (s) => s : _encode;
    let res = '';
    if (this.scheme) res += this.scheme + ':';
    if (this.authority || this.scheme === 'file') res += '//';
    if (this.authority) {
      let a = this.authority.toLowerCase();
      const at = a.lastIndexOf('@');
      if (at !== -1) { res += enc(a.substr(0, at), false) + '@'; a = a.substr(at + 1); }
      const colon = a.lastIndexOf(':');
      res += colon === -1 ? enc(a, false) : enc(a.substr(0, colon), false) + a.substr(colon);
    }
    if (this.path) {
      let p = this.path;
      const m = /^\/([A-Za-z]):/.exec(p) || /^([A-Za-z]):/.exec(p);
      if (m) {                                                // drive letter: lower case, ':' encoded
        const lead = p[0] === '/' ? '/' : '';
        p = lead + m[1].toLowerCase() + ':' + p.substr(lead.length + 2);
        res += skipEncoding ? p : lead + m[1].toLowerCase() + '%3A' + _encode(p.substr(lead.length + 2), true);
      } else {
        res += enc(p, true);
      }
    }
    if (this.query) res += '?' + enc(this.query, false);
    if (this.fragment) res += '#' + (skipEncoding ? this.fragment : _encode(this.fragment, false));
    return res;
  }

  toJSON() {
    return { $mid: 1, scheme: this.scheme, authority: this.authority, path: this.path, query: this.query,
      fragment: this.fragment, fsPath: this.scheme === 'file' ? this.fsPath : undefined, external: this.toString() };
  }
}

// ============================================================================ positions
class Position {
  constructor(line, character) {
    if (line < 0) throw new Error('Illegal argument: line must be non-negative');
    if (character < 0) throw new Error('Illegal argument: character must be non-negative');
    this._line = line | 0; this._character = character | 0;
  }
  get line() { return this._line; }
  get character() { return this._character; }
  static isPosition(o) { return o instanceof Position || (!!o && typeof o.line === 'number' && typeof o.character === 'number'); }
  isBefore(o) { return this._line < o.line || (this._line === o.line && this._character < o.character); }
  isBeforeOrEqual(o) { return this._line < o.line || (this._line === o.line && this._character <= o.character); }
  isAfter(o) { return !this.isBeforeOrEqual(o); }
  isAfterOrEqual(o) { return !this.isBefore(o); }
  isEqual(o) { return this._line === o.line && this._character === o.character; }
  compareTo(o) { return this._line < o.line ? -1 : this._line > o.line ? 1 : this._character < o.character ? -1 : this._character > o.character ? 1 : 0; }
  translate(lineDelta, characterDelta) {
    if (typeof lineDelta === 'object' && lineDelta) ({ lineDelta = 0, characterDelta = 0 } = lineDelta);
    lineDelta = lineDelta || 0; characterDelta = characterDelta || 0;
    if (!lineDelta && !characterDelta) return this;
    return new Position(this._line + lineDelta, this._character + characterDelta);
  }
  with(line, character) {
    if (typeof line === 'object' && line) ({ line, character } = line);
    if (line === undefined) line = this._line;
    if (character === undefined) character = this._character;
    return line === this._line && character === this._character ? this : new Position(line, character);
  }
  toJSON() { return { line: this._line, character: this._character }; }
}

class Range {
  constructor(a, b, c, d) {
    let start, end;
    if (typeof a === 'number') { start = new Position(a, b); end = new Position(c, d); } else { start = a; end = b; }
    if (!(start instanceof Position)) start = new Position(start.line, start.character);
    if (!(end instanceof Position)) end = new Position(end.line, end.character);
    if (start.isAfter(end)) { this._start = end; this._end = start; } else { this._start = start; this._end = end; }
  }
  get start() { return this._start; }
  get end() { return this._end; }
  static isRange(o) { return o instanceof Range || (!!o && Position.isPosition(o.start) && Position.isPosition(o.end)); }
  get isEmpty() { return this._start.isEqual(this._end); }
  get isSingleLine() { return this._start.line === this._end.line; }
  contains(x) {
    if (Range.isRange(x)) return this.contains(x.start) && this.contains(x.end);
    return !(x.isBefore(this._start) || this._end.isBefore(x));
  }
  isEqual(o) { return this._start.isEqual(o.start) && this._end.isEqual(o.end); }
  intersection(o) {
    const start = this._start.isAfter(o.start) ? this._start : o.start;
    const end = this._end.isBefore(o.end) ? this._end : o.end;
    return start.isAfter(end) ? undefined : new Range(start, end);
  }
  union(o) {
    return new Range(this._start.isBefore(o.start) ? this._start : o.start, this._end.isAfter(o.end) ? this._end : o.end);
  }
  with(start, end) {
    if (start && !Position.isPosition(start) && typeof start === 'object') ({ start, end } = start);
    start = start || this._start; end = end || this._end;
    return start.isEqual(this._start) && end.isEqual(this._end) ? this : new Range(start, end);
  }
  toJSON() { return { start: this._start.toJSON(), end: this._end.toJSON() }; }
}

class Selection extends Range {
  constructor(a, b, c, d) {
    let anchor, active;
    if (typeof a === 'number') { anchor = new Position(a, b); active = new Position(c, d); } else { anchor = a; active = b; }
    super(anchor, active);
    this._anchor = anchor; this._active = active;
  }
  get anchor() { return this._anchor; }
  get active() { return this._active; }
  get isReversed() { return this._anchor === this._end; }
  static isSelection(o) { return o instanceof Selection || (Range.isRange(o) && Position.isPosition(o.anchor)); }
  toJSON() { return { start: this.start, end: this.end, active: this.active, anchor: this.anchor }; }
}

class Location {
  constructor(uri, rangeOrPosition) {
    this.uri = uri;
    this.range = rangeOrPosition instanceof Position ? new Range(rangeOrPosition, rangeOrPosition) : rangeOrPosition;
  }
  static isLocation(o) { return o instanceof Location || (!!o && Uri.isUri(o.uri) && Range.isRange(o.range)); }
}

// ============================================================================ events / disposables
class Disposable {
  constructor(callOnDispose) { this._fn = callOnDispose; }
  static from(...items) {
    return new Disposable(() => { for (const d of items) { try { d && typeof d.dispose === 'function' && d.dispose(); } catch (_) { /* */ } } });
  }
  dispose() { if (typeof this._fn === 'function') { const f = this._fn; this._fn = undefined; f(); } }
}

class EventEmitter {
  constructor() { this._listeners = []; this._disposed = false; }
  get event() {
    if (!this._event) {
      this._event = (listener, thisArgs, disposables) => {
        const entry = { listener, thisArgs };
        this._listeners.push(entry);
        const d = new Disposable(() => { const i = this._listeners.indexOf(entry); if (i >= 0) this._listeners.splice(i, 1); });
        if (Array.isArray(disposables)) disposables.push(d);
        return d;
      };
    }
    return this._event;
  }
  fire(data) {
    for (const { listener, thisArgs } of this._listeners.slice()) {
      try { listener.call(thisArgs, data); } catch (e) { EventEmitter.onListenerError(e); }
    }
  }
  dispose() { this._listeners = []; this._disposed = true; }
}
EventEmitter.onListenerError = (e) => { try { process.stderr.write('[event listener] ' + (e && e.stack || e) + '\n'); } catch (_) { /* */ } };

class CancellationError extends Error { constructor() { super('Canceled'); this.name = 'Canceled'; } }

const _neverEvent = () => new Disposable(() => {});
const CancellationTokenNone = Object.freeze({ isCancellationRequested: false, onCancellationRequested: _neverEvent });

class CancellationTokenSource {
  constructor() { this._emitter = null; this._cancelled = false; this._token = null; }
  get token() {
    if (!this._token) {
      const self = this;
      this._token = {
        get isCancellationRequested() { return self._cancelled; },
        onCancellationRequested: (l, t, d) => {
          if (self._cancelled) { setTimeout(() => l.call(t)); return new Disposable(() => {}); }
          if (!self._emitter) self._emitter = new EventEmitter();
          return self._emitter.event(l, t, d);
        },
      };
    }
    return this._token;
  }
  cancel() { if (!this._cancelled) { this._cancelled = true; if (this._emitter) this._emitter.fire(undefined); } }
  dispose(cancel) { if (cancel) this.cancel(); if (this._emitter) this._emitter.dispose(); }
}

// ============================================================================ edits
class TextEdit {
  constructor(range, newText) { this.range = range; this.newText = newText; }
  static replace(range, newText) { return new TextEdit(range, newText); }
  static insert(position, newText) { return new TextEdit(new Range(position, position), newText); }
  static delete(range) { return new TextEdit(range, ''); }
  static setEndOfLine(eol) { const e = new TextEdit(new Range(new Position(0, 0), new Position(0, 0)), ''); e.newEol = eol; return e; }
  static isTextEdit(o) { return o instanceof TextEdit || (!!o && Range.isRange(o.range) && typeof o.newText === 'string'); }
}

class SnippetTextEdit {
  constructor(range, snippet) { this.range = range; this.snippet = snippet; }
  static replace(range, snippet) { return new SnippetTextEdit(range, snippet); }
  static insert(position, snippet) { return new SnippetTextEdit(new Range(position, position), snippet); }
  static isSnippetTextEdit(o) { return o instanceof SnippetTextEdit; }
}

class WorkspaceEdit {
  constructor() { this._edits = []; }          // {_type: 1 file op | 2 text, ...}
  renameFile(from, to, options, metadata) { this._edits.push({ _type: 1, from, to, options, metadata }); }
  createFile(uri, options, metadata) { this._edits.push({ _type: 1, from: undefined, to: uri, options, metadata }); }
  deleteFile(uri, options, metadata) { this._edits.push({ _type: 1, from: uri, to: undefined, options, metadata }); }
  replace(uri, range, newText, metadata) { this._edits.push({ _type: 2, uri, edit: new TextEdit(range, newText), metadata }); }
  insert(resource, position, newText, metadata) { this.replace(resource, new Range(position, position), newText, metadata); }
  delete(resource, range, metadata) { this.replace(resource, range, '', metadata); }
  has(uri) { return this._edits.some((e) => e._type === 2 && e.uri.toString() === uri.toString()); }
  set(uri, edits) {
    this._edits = this._edits.filter((e) => !(e._type === 2 && e.uri.toString() === uri.toString()));
    for (const item of edits || []) {
      const e = Array.isArray(item) ? item[0] : item;
      if (!e) continue;
      if (e instanceof SnippetTextEdit || e.snippet) this._edits.push({ _type: 2, uri, edit: new TextEdit(e.range, e.snippet.value || String(e.snippet)) });
      else this._edits.push({ _type: 2, uri, edit: e });
    }
  }
  get(uri) { return this._edits.filter((e) => e._type === 2 && e.uri.toString() === uri.toString()).map((e) => e.edit); }
  entries() {
    const map = new Map();
    for (const e of this._edits) {
      if (e._type !== 2) continue;
      const k = e.uri.toString();
      if (!map.has(k)) map.set(k, [e.uri, []]);
      map.get(k)[1].push(e.edit);
    }
    return [...map.values()];
  }
  get size() { return this.entries().length; }
  toJSON() { return this.entries(); }
}

// ============================================================================ strings
class SnippetString {
  constructor(value) { this.value = value || ''; this._tabstop = 1; }
  static isSnippetString(o) { return o instanceof SnippetString || (!!o && typeof o.value === 'string' && typeof o.appendTabstop === 'function'); }
  static _escape(v) { return v.replace(/\$|}|\\/g, '\\$&'); }
  appendText(string) { this.value += SnippetString._escape(string); return this; }
  appendTabstop(number) { this.value += '$' + (number === undefined ? this._tabstop++ : number); return this; }
  appendPlaceholder(value, number) {
    if (typeof value === 'function') { const nested = new SnippetString(); nested._tabstop = this._tabstop; value(nested); this._tabstop = nested._tabstop; value = nested.value; } else value = SnippetString._escape(value);
    this.value += '${' + (number === undefined ? this._tabstop++ : number) + ':' + value + '}'; return this;
  }
  appendChoice(values, number) {
    const v = values.map((s) => s.replace(/\$|}|\\|,/g, '\\$&')).join(',');
    this.value += '${' + (number === undefined ? this._tabstop++ : number) + '|' + v + '|}'; return this;
  }
  appendVariable(name, defaultValue) {
    if (typeof defaultValue === 'function') { const nested = new SnippetString(); nested._tabstop = this._tabstop; defaultValue(nested); this._tabstop = nested._tabstop; defaultValue = nested.value; } else if (typeof defaultValue === 'string') defaultValue = defaultValue.replace(/\$|}/g, '\\$&');
    this.value += '${' + name + (defaultValue ? ':' + defaultValue : '') + '}'; return this;
  }
}

class MarkdownString {
  constructor(value, supportThemeIcons) { this.value = value || ''; this.isTrusted = undefined; this.supportThemeIcons = !!supportThemeIcons; this.supportHtml = false; this.baseUri = undefined; }
  static isMarkdownString(o) { return o instanceof MarkdownString || (!!o && typeof o.value === 'string' && typeof o.appendMarkdown === 'function'); }
  appendText(value) { this.value += value.replace(/[\\`*_{}[\]()#+\-!<>]/g, '\\$&').replace(/\n/g, '\n\n'); return this; }
  appendMarkdown(value) { this.value += value; return this; }
  appendCodeblock(code, language) { this.value += '\n```' + (language || '') + '\n' + code + '\n```\n'; return this; }
}

// ============================================================================ enums
const E = (names, start = 0) => { const o = {}; names.forEach((n, i) => { o[n] = start + i; o[start + i] = n; }); return o; };
const CompletionItemKind = E(['Text', 'Method', 'Function', 'Constructor', 'Field', 'Variable', 'Class', 'Interface', 'Module',
  'Property', 'Unit', 'Value', 'Enum', 'Keyword', 'Snippet', 'Color', 'File', 'Reference', 'Folder', 'EnumMember', 'Constant',
  'Struct', 'Event', 'Operator', 'TypeParameter', 'User', 'Issue']);
const CompletionItemTag = { Deprecated: 1 };
const CompletionTriggerKind = E(['Invoke', 'TriggerCharacter', 'TriggerForIncompleteCompletions']);
const SymbolKind = E(['File', 'Module', 'Namespace', 'Package', 'Class', 'Method', 'Property', 'Field', 'Constructor', 'Enum',
  'Interface', 'Function', 'Variable', 'Constant', 'String', 'Number', 'Boolean', 'Array', 'Object', 'Key', 'Null', 'EnumMember',
  'Struct', 'Event', 'Operator', 'TypeParameter']);
const SymbolTag = { Deprecated: 1 };
const DiagnosticSeverity = E(['Error', 'Warning', 'Information', 'Hint']);
const DiagnosticTag = { Unnecessary: 1, Deprecated: 2 };
const DocumentHighlightKind = E(['Text', 'Read', 'Write']);
const StatusBarAlignment = { Left: 1, Right: 2 };
const ViewColumn = { Active: -1, Beside: -2, One: 1, Two: 2, Three: 3, Four: 4, Five: 5, Six: 6, Seven: 7, Eight: 8, Nine: 9 };
const ConfigurationTarget = { Global: 1, Workspace: 2, WorkspaceFolder: 3 };
const EndOfLine = { LF: 1, CRLF: 2 };
const TextEditorRevealType = E(['Default', 'InCenter', 'InCenterIfOutsideViewport', 'AtTop']);
const TextEditorCursorStyle = E(['Line', 'Block', 'Underline', 'LineThin', 'BlockOutline', 'UnderlineThin'], 1);
const TextEditorLineNumbersStyle = E(['Off', 'On', 'Relative', 'Interval']);
const TextEditorSelectionChangeKind = E(['Keyboard', 'Mouse', 'Command'], 1);
const TextDocumentSaveReason = E(['Manual', 'AfterDelay', 'FocusOut'], 1);
const TextDocumentChangeReason = E(['Undo', 'Redo'], 1);
const DecorationRangeBehavior = E(['OpenOpen', 'ClosedClosed', 'OpenClosed', 'ClosedOpen']);
const OverviewRulerLane = { Left: 1, Center: 2, Right: 4, Full: 7 };
const ProgressLocation = { SourceControl: 1, Window: 10, Notification: 15 };
const FileType = { Unknown: 0, File: 1, Directory: 2, SymbolicLink: 64 };
const FilePermission = { Readonly: 1 };
const FileChangeType = { Changed: 1, Created: 2, Deleted: 3 };
const TreeItemCollapsibleState = E(['None', 'Collapsed', 'Expanded']);
const TreeItemCheckboxState = E(['Unchecked', 'Checked']);
const ExtensionMode = { Production: 1, Development: 2, Test: 3 };
const ExtensionKind = { UI: 1, Workspace: 2 };
const UIKind = { Desktop: 1, Web: 2 };
const ColorThemeKind = { Light: 1, Dark: 2, HighContrast: 3, HighContrastLight: 4 };
const FoldingRangeKind = { Comment: 1, Imports: 2, Region: 3 };
const SignatureHelpTriggerKind = E(['Invoke', 'TriggerCharacter', 'ContentChange'], 1);
const CodeActionTriggerKind = E(['Invoke', 'Automatic'], 1);
const InlayHintKind = { Type: 1, Parameter: 2 };
const InlineCompletionTriggerKind = E(['Invoke', 'Automatic']);
const QuickPickItemKind = { Separator: -1, Default: 0 };
const LanguageStatusSeverity = E(['Information', 'Warning', 'Error']);
const DebugConsoleMode = E(['Separate', 'MergeWithParent']);
const DebugConfigurationProviderTriggerKind = E(['Initial', 'Dynamic'], 1);
const TaskRevealKind = E(['Always', 'Silent', 'Never'], 1);
const TaskPanelKind = E(['Shared', 'Dedicated', 'New'], 1);
const TaskScope = { Global: 1, Workspace: 2 };
const ShellQuoting = E(['Escape', 'Strong', 'Weak'], 1);
const TerminalLocation = E(['Panel', 'Editor'], 1);
const TerminalExitReason = E(['Unknown', 'Shutdown', 'Process', 'User', 'Extension']);
const EnvironmentVariableMutatorType = E(['Replace', 'Append', 'Prepend'], 1);
const CommentMode = E(['Editing', 'Preview']);
const CommentThreadCollapsibleState = E(['Collapsed', 'Expanded']);
const CommentThreadState = E(['Unresolved', 'Resolved']);
const NotebookCellKind = { Markup: 1, Code: 2 };
const NotebookEditorRevealType = E(['Default', 'InCenter', 'InCenterIfOutsideViewport', 'AtTop']);
const NotebookControllerAffinity = { Default: 1, Preferred: 2 };
const NotebookCellStatusBarAlignment = { Left: 1, Right: 2 };
const TestRunProfileKind = { Run: 1, Debug: 2, Coverage: 3 };
const TestMessageStackFrame = class { constructor(label, uri, position) { this.label = label; this.uri = uri; this.position = position; } };
const SemanticTokensLegendCls = null;  // placeholder (class below)
const LogLevel = E(['Off', 'Trace', 'Debug', 'Info', 'Warning', 'Error']);
const SyntaxTokenType = E(['Other', 'Comment', 'String', 'RegEx']);
const DocumentPasteTriggerKind = E(['Automatic', 'PasteAs']);
const InlineCompletionsDisposeReasonKind = E(['Other', 'Empty', 'TokenCancellation', 'LostRace', 'NotTaken']);
const PortAutoForwardAction = E(['Notify', 'OpenBrowser', 'OpenPreview', 'Silent', 'Ignore', 'OpenBrowserOnce'], 1);
const ChatResultFeedbackKind = { Unhelpful: 0, Helpful: 1 };
const LanguageModelChatMessageRole = { User: 1, Assistant: 2 };
void SemanticTokensLegendCls;

// ============================================================================ language feature values
class CompletionItem {
  constructor(label, kind) { this.label = label; this.kind = kind; }
}
class CompletionList {
  constructor(items, isIncomplete) { this.items = items || []; this.isIncomplete = !!isIncomplete; }
}
class Hover {
  constructor(contents, range) {
    this.contents = Array.isArray(contents) ? contents : (contents ? [contents] : []);
    this.range = range;
  }
}
class VerboseHover extends Hover { constructor(contents, range, canIncreaseVerbosity, canDecreaseVerbosity) { super(contents, range); this.canIncreaseVerbosity = canIncreaseVerbosity; this.canDecreaseVerbosity = canDecreaseVerbosity; } }
class Diagnostic {
  constructor(range, message, severity) {
    this.range = range; this.message = message;
    this.severity = severity === undefined ? DiagnosticSeverity.Error : severity;
  }
}
class DiagnosticRelatedInformation { constructor(location, message) { this.location = location; this.message = message; } }
class CodeActionKind {
  constructor(value) { this.value = value; }
  append(parts) { return new CodeActionKind(this.value ? this.value + '.' + parts : parts); }
  intersects(other) { return this.contains(other) || other.contains(this); }
  contains(other) { return this.value === other.value || other.value.startsWith(this.value + '.') || this.value === ''; }
}
CodeActionKind.Empty = new CodeActionKind('');
CodeActionKind.QuickFix = new CodeActionKind('quickfix');
CodeActionKind.Refactor = new CodeActionKind('refactor');
CodeActionKind.RefactorExtract = CodeActionKind.Refactor.append('extract');
CodeActionKind.RefactorInline = CodeActionKind.Refactor.append('inline');
CodeActionKind.RefactorMove = CodeActionKind.Refactor.append('move');
CodeActionKind.RefactorRewrite = CodeActionKind.Refactor.append('rewrite');
CodeActionKind.Source = new CodeActionKind('source');
CodeActionKind.SourceOrganizeImports = CodeActionKind.Source.append('organizeImports');
CodeActionKind.SourceFixAll = CodeActionKind.Source.append('fixAll');
CodeActionKind.Notebook = new CodeActionKind('notebook');
class CodeAction { constructor(title, kind) { this.title = title; this.kind = kind; } }
class CodeLens { constructor(range, command) { this.range = range; this.command = command; } get isResolved() { return !!this.command; } }
class DocumentLink { constructor(range, target) { this.range = range; this.target = target; } }
class DocumentSymbol {
  constructor(name, detail, kind, range, selectionRange) { this.name = name; this.detail = detail; this.kind = kind; this.range = range; this.selectionRange = selectionRange; this.children = []; }
}
class SymbolInformation {
  constructor(name, kind, a, b, c) {
    this.name = name; this.kind = kind;
    if (a instanceof Location || Location.isLocation(a)) { this.location = a; this.containerName = b; } else if (typeof a === 'string') { this.containerName = a; this.location = new Location(c, b); } else { this.location = new Location(b, a); this.containerName = c; }
  }
}
class FoldingRange { constructor(start, end, kind) { this.start = start; this.end = end; this.kind = kind; } }
class SelectionRange { constructor(range, parent) { this.range = range; this.parent = parent; } }
class SignatureHelp { constructor() { this.signatures = []; this.activeSignature = 0; this.activeParameter = 0; } }
class SignatureInformation { constructor(label, documentation) { this.label = label; this.documentation = documentation; this.parameters = []; } }
class ParameterInformation { constructor(label, documentation) { this.label = label; this.documentation = documentation; } }
class Color { constructor(red, green, blue, alpha) { this.red = red; this.green = green; this.blue = blue; this.alpha = alpha; } }
class ColorInformation { constructor(range, color) { this.range = range; this.color = color; } }
class ColorPresentation { constructor(label) { this.label = label; } }
class DocumentHighlight { constructor(range, kind) { this.range = range; this.kind = kind === undefined ? DocumentHighlightKind.Text : kind; } }
class InlayHint { constructor(position, label, kind) { this.position = position; this.label = label; this.kind = kind; } }
class InlayHintLabelPart { constructor(value) { this.value = value; } }
class SemanticTokensLegend { constructor(tokenTypes, tokenModifiers) { this.tokenTypes = tokenTypes; this.tokenModifiers = tokenModifiers || []; } }
class SemanticTokens { constructor(data, resultId) { this.data = data; this.resultId = resultId; } }
class SemanticTokensEdit { constructor(start, deleteCount, data) { this.start = start; this.deleteCount = deleteCount; this.data = data; } }
class SemanticTokensEdits { constructor(edits, resultId) { this.edits = edits; this.resultId = resultId; } }
class SemanticTokensBuilder {
  constructor(legend) { this._legend = legend; this._data = []; this._prevLine = 0; this._prevChar = 0; }
  push(a, b, c, d, e) {
    let line, char, length, type, mods;
    if (typeof a === 'number') { line = a; char = b; length = c; type = d; mods = e || 0; } else {
      const range = a; line = range.start.line; char = range.start.character; length = range.end.character - range.start.character;
      type = this._legend.tokenTypes.indexOf(b); mods = 0;
      for (const m of c || []) { const i = this._legend.tokenModifiers.indexOf(m); if (i >= 0) mods |= (1 << i); }
    }
    const dl = line - this._prevLine; const dc = dl === 0 ? char - this._prevChar : char;
    this._data.push(dl, dc, length, type, mods); this._prevLine = line; this._prevChar = char;
  }
  build(resultId) { return new SemanticTokens(new Uint32Array(this._data), resultId); }
}
class CallHierarchyItem { constructor(kind, name, detail, uri, range, selectionRange) { Object.assign(this, { kind, name, detail, uri, range, selectionRange }); } }
class CallHierarchyIncomingCall { constructor(from, fromRanges) { this.from = from; this.fromRanges = fromRanges; } }
class CallHierarchyOutgoingCall { constructor(to, fromRanges) { this.to = to; this.fromRanges = fromRanges; } }
class TypeHierarchyItem { constructor(kind, name, detail, uri, range, selectionRange) { Object.assign(this, { kind, name, detail, uri, range, selectionRange }); } }
class LinkedEditingRanges { constructor(ranges, wordPattern) { this.ranges = ranges; this.wordPattern = wordPattern; } }
class InlineValueText { constructor(range, text) { this.range = range; this.text = text; } }
class InlineValueVariableLookup { constructor(range, variableName, caseSensitiveLookup = true) { Object.assign(this, { range, variableName, caseSensitiveLookup }); } }
class InlineValueEvaluatableExpression { constructor(range, expression) { this.range = range; this.expression = expression; } }
class InlineCompletionItem { constructor(insertText, range, command) { this.insertText = insertText; this.range = range; this.command = command; } }
class InlineCompletionList { constructor(items) { this.items = items; } }
class EvaluatableExpression { constructor(range, expression) { this.range = range; this.expression = expression; } }
class DocumentDropEdit { constructor(insertText, title, kind) { this.insertText = insertText; this.title = title; this.kind = kind; } }
class DocumentPasteEdit { constructor(insertText, title, kind) { this.insertText = insertText; this.title = title; this.kind = kind; } }
class DocumentDropOrPasteEditKind {
  constructor(value) { this.value = value; }
  append(...parts) { return new DocumentDropOrPasteEditKind((this.value ? [this.value, ...parts] : parts).join('.')); }
  intersects(other) { return this.contains(other) || other.contains(this); }
  contains(other) { return this.value === other.value || other.value.startsWith(this.value + '.'); }
}
DocumentDropOrPasteEditKind.Empty = new DocumentDropOrPasteEditKind('');
DocumentDropOrPasteEditKind.Text = new DocumentDropOrPasteEditKind('text');
DocumentDropOrPasteEditKind.TextUpdateImports = DocumentDropOrPasteEditKind.Text.append('updateImports');
class RelativePattern {
  constructor(base, pattern) {
    if (typeof base === 'string') { this.baseUri = Uri.file(base); } else if (Uri.isUri(base)) this.baseUri = base; else this.baseUri = base.uri;
    this.base = this.baseUri.fsPath; this.pattern = pattern;
  }
}
class ThemeColor { constructor(id) { this.id = id; } }
class ThemeIcon { constructor(id, color) { this.id = id; this.color = color; } }
ThemeIcon.File = new ThemeIcon('file'); ThemeIcon.Folder = new ThemeIcon('folder');
class TreeItem {
  constructor(a, collapsibleState) {
    if (Uri.isUri(a)) this.resourceUri = a; else this.label = a;
    this.collapsibleState = collapsibleState === undefined ? TreeItemCollapsibleState.None : collapsibleState;
  }
}
class FileDecoration { constructor(badge, tooltip, color) { this.badge = badge; this.tooltip = tooltip; this.color = color; } }
class FileSystemError extends Error {
  constructor(messageOrUri, code) { super(Uri.isUri(messageOrUri) ? messageOrUri.toString(true) : (messageOrUri || 'Unknown')); this.code = code || 'Unknown'; this.name = (code || 'Unknown') + ' (FileSystemError)'; }
  static FileNotFound(m) { return new FileSystemError(m, 'FileNotFound'); }
  static FileExists(m) { return new FileSystemError(m, 'FileExists'); }
  static FileNotADirectory(m) { return new FileSystemError(m, 'FileNotADirectory'); }
  static FileIsADirectory(m) { return new FileSystemError(m, 'FileIsADirectory'); }
  static NoPermissions(m) { return new FileSystemError(m, 'NoPermissions'); }
  static Unavailable(m) { return new FileSystemError(m, 'Unavailable'); }
}
class TabInputText { constructor(uri) { this.uri = uri; } }
class TabInputTextDiff { constructor(original, modified) { this.original = original; this.modified = modified; } }
class TabInputCustom { constructor(uri, viewType) { this.uri = uri; this.viewType = viewType; } }
class TabInputWebview { constructor(viewType) { this.viewType = viewType; } }
class TabInputNotebook { constructor(uri, notebookType) { this.uri = uri; this.notebookType = notebookType; } }
class TabInputNotebookDiff { constructor(original, modified, notebookType) { Object.assign(this, { original, modified, notebookType }); } }
class TabInputTerminal { constructor() { } }

// ============================================================================ debug / tasks
class DebugAdapterExecutable { constructor(command, args, options) { this.command = command; this.args = args || []; this.options = options; } }
class DebugAdapterServer { constructor(port, host) { this.port = port; this.host = host; } }
class DebugAdapterNamedPipeServer { constructor(p) { this.path = p; } }
class DebugAdapterInlineImplementation { constructor(implementation) { this.implementation = implementation; } }
let _bpId = 0;
class Breakpoint { constructor(enabled, condition, hitCondition, logMessage) { this.id = 'bp' + (++_bpId); Object.assign(this, { enabled: enabled !== false, condition, hitCondition, logMessage }); } }
class SourceBreakpoint extends Breakpoint { constructor(location, enabled, condition, hitCondition, logMessage) { super(enabled, condition, hitCondition, logMessage); this.location = location; } }
class FunctionBreakpoint extends Breakpoint { constructor(functionName, enabled, condition, hitCondition, logMessage) { super(enabled, condition, hitCondition, logMessage); this.functionName = functionName; } }
class DataBreakpoint extends Breakpoint { constructor(label, dataId, canPersist, enabled, condition, hitCondition, logMessage) { super(enabled, condition, hitCondition, logMessage); Object.assign(this, { label, dataId, canPersist }); } }
class TaskGroup { constructor(id, label) { this.id = id; this.label = label; this.isDefault = undefined; } }
TaskGroup.Clean = new TaskGroup('clean', 'Clean'); TaskGroup.Build = new TaskGroup('build', 'Build');
TaskGroup.Rebuild = new TaskGroup('rebuild', 'Rebuild'); TaskGroup.Test = new TaskGroup('test', 'Test');
class ShellExecution { constructor(a, b, c) { if (Array.isArray(b) || (b && typeof b === 'object' && b.length !== undefined)) { this.command = a; this.args = b; this.options = c; } else { this.commandLine = a; this.options = b; } } }
class ProcessExecution { constructor(process, a, b) { this.process = process; if (Array.isArray(a)) { this.args = a; this.options = b; } else { this.args = []; this.options = a; } } }
class CustomExecution { constructor(callback) { this.callback = callback; } }
class Task {
  constructor(definition, a, b, c, d, e) {
    this.definition = definition;
    if (typeof a === 'string') { this.name = a; this.source = b; this.execution = c; this.problemMatchers = d; } else { this.scope = a; this.name = b; this.source = c; this.execution = d; this.problemMatchers = e; }
    this.isBackground = false; this.presentationOptions = {}; this.runOptions = {};
  }
}
class TerminalLink { constructor(startIndex, length, tooltip) { Object.assign(this, { startIndex, length, tooltip }); } }
class TerminalProfile { constructor(options) { this.options = options; } }
class NotebookRange { constructor(start, end) { this.start = start; this.end = end; } get isEmpty() { return this.start === this.end; } with(c) { return new NotebookRange(c.start ?? this.start, c.end ?? this.end); } }
class NotebookCellData { constructor(kind, value, languageId) { Object.assign(this, { kind, value, languageId }); } }
class NotebookData { constructor(cells) { this.cells = cells; } }
class NotebookCellOutputItem { constructor(data, mime) { this.data = data; this.mime = mime; } static text(v, mime) { return new NotebookCellOutputItem(Buffer.from(String(v)), mime || 'text/plain'); } static json(v, mime) { return new NotebookCellOutputItem(Buffer.from(JSON.stringify(v)), mime || 'text/x-json'); } static stdout(v) { return NotebookCellOutputItem.text(v, 'application/vnd.code.notebook.stdout'); } static stderr(v) { return NotebookCellOutputItem.text(v, 'application/vnd.code.notebook.stderr'); } static error(e) { return NotebookCellOutputItem.json({ name: e.name, message: e.message, stack: e.stack }, 'application/vnd.code.notebook.error'); } }
class NotebookCellOutput { constructor(items, id, metadata) { Object.assign(this, { items, id, metadata }); } }
class NotebookEdit {
  constructor(range, newCells) { this.range = range; this.newCells = newCells; }
  static replaceCells(range, newCells) { return new NotebookEdit(range, newCells); }
  static insertCells(index, newCells) { return new NotebookEdit(new NotebookRange(index, index), newCells); }
  static deleteCells(range) { return new NotebookEdit(range, []); }
  static updateCellMetadata(index, newMetadata) { const e = new NotebookEdit(new NotebookRange(index, index), []); e.newCellMetadata = newMetadata; return e; }
  static updateNotebookMetadata(newMetadata) { const e = new NotebookEdit(new NotebookRange(0, 0), []); e.newNotebookMetadata = newMetadata; return e; }
}
class TestMessage { constructor(message) { this.message = message; } static diff(message, expected, actual) { const m = new TestMessage(message); m.expectedOutput = expected; m.actualOutput = actual; return m; } }
class TestTag { constructor(id) { this.id = id; } }
class TestRunRequest { constructor(include, exclude, profile, continuous) { Object.assign(this, { include, exclude, profile, continuous }); } }
class LanguageModelChatMessage { constructor(role, content, name) { Object.assign(this, { role, content, name }); } static User(c, n) { return new LanguageModelChatMessage(1, c, n); } static Assistant(c, n) { return new LanguageModelChatMessage(2, c, n); } }
class LanguageModelTextPart { constructor(value) { this.value = value; } }
class LanguageModelError extends Error {
  constructor(message, code, cause) { super(message, cause ? { cause } : undefined); this.name = 'LanguageModelError'; this.code = code || ''; }
  static NotFound(message) { return new LanguageModelError(message, 'NotFound'); }
  static NoPermissions(message) { return new LanguageModelError(message, 'NoPermissions'); }
  static Blocked(message) { return new LanguageModelError(message, 'Blocked'); }
}
class QuickInputButtonsCls { }
const QuickInputButtons = { Back: { iconPath: new ThemeIcon('arrow-left'), tooltip: 'Back' } };
void QuickInputButtonsCls;


// ============================================================================ API types added through VS Code 1.147
// (constructors / defaults as in src/vs/workbench/api/common/extHostTypes.ts of microsoft/vscode, MIT)
const InputBoxValidationSeverity = { Info: 1, Warning: 2, Error: 3 };
const IndentAction = E(['None', 'Indent', 'IndentOutdent', 'Outdent']);
const TerminalShellExecutionCommandLineConfidence = E(['Low', 'Medium', 'High']);
const QuickInputButtonLocation = { Title: 1, Inline: 2, Input: 3 };
const TimelineTriggerKind = { Invoke: 1, Automatic: 2 };
const LanguageModelChatToolMode = { Auto: 1, Required: 2 };
class DataTransferItem {
  constructor(value) { this.value = value; }
  async asString() { return typeof this.value === 'string' ? this.value : JSON.stringify(this.value); }
  asFile() { return undefined; }
}
class DataTransfer {
  constructor(init) { this._items = new Map(); for (const [mime, item] of init || []) { const k = String(mime).toLowerCase(); const ex = this._items.get(k); if (ex) ex.push(item); else this._items.set(k, [item]); } }
  get(mimeType) { const l = this._items.get(String(mimeType).toLowerCase()); return l ? l[0] : undefined; }
  set(mimeType, value) { this._items.set(String(mimeType).toLowerCase(), [value]); }
  forEach(cb, thisArg) { for (const [mime, items] of this._items) for (const item of items) cb.call(thisArg, item, mime, this); }
  *[Symbol.iterator]() { for (const [mime, items] of this._items) for (const item of items) yield [mime, item]; }
}
class TimelineItem { constructor(arg1, timestamp) { if (Uri.isUri(arg1)) this.resourceUri = arg1; else this.label = arg1; this.timestamp = timestamp; } }
class NotebookCellStatusBarItem { constructor(text, alignment) { this.text = text; this.alignment = alignment; } }
class DebugThread { constructor(session, threadId) { this.session = session; this.threadId = threadId; } }
class DebugStackFrame { constructor(session, threadId, frameId) { this.session = session; this.threadId = threadId; this.frameId = frameId; } }
class TestCoverageCount {
  constructor(covered, total) {
    this.covered = covered; this.total = total;
    if (covered > total) throw new Error(`The total number of covered items (${covered}) cannot be greater than the total (${total})`);
    if (total < 0) throw new Error(`The number of covered items (${total}) cannot be negative`);
  }
}
class FileCoverage {
  constructor(uri, statementCoverage, branchCoverage, declarationCoverage, includesTests) { Object.assign(this, { uri, statementCoverage, branchCoverage, declarationCoverage, includesTests: includesTests || [] }); }
  static fromDetails(uri, details) {
    const st = new TestCoverageCount(0, 0); const br = new TestCoverageCount(0, 0); const de = new TestCoverageCount(0, 0);
    for (const d of details) {
      if ('branches' in d) { st.total += 1; st.covered += d.executed ? 1 : 0; for (const b of d.branches) { br.total += 1; br.covered += b.executed ? 1 : 0; } } else { de.total += 1; de.covered += d.executed ? 1 : 0; }
    }
    const c = new FileCoverage(uri, st, br.total > 0 ? br : undefined, de.total > 0 ? de : undefined);
    c.detailedCoverage = details;
    return c;
  }
}
class StatementCoverage { constructor(executed, location, branches) { Object.assign(this, { executed, location, branches: branches || [] }); } get executionCount() { return +this.executed; } set executionCount(n) { this.executed = n; } }
class BranchCoverage { constructor(executed, location, label) { Object.assign(this, { executed, location, label }); } get executionCount() { return +this.executed; } set executionCount(n) { this.executed = n; } }
class DeclarationCoverage { constructor(name, executed, location) { Object.assign(this, { name, executed, location }); } get executionCount() { return +this.executed; } set executionCount(n) { this.executed = n; } }
class TelemetryTrustedValue { constructor(value) { this.value = value; this.isTrustedTelemetryValue = true; } }
class ChatResponseMarkdownPart {
  constructor(value) {
    if (typeof value !== 'string' && value && value.isTrusted === true) throw new Error('The boolean form of MarkdownString.isTrusted is NOT supported for chat participants.');
    this.value = typeof value === 'string' ? new MarkdownString(value) : value;
  }
}
class ChatResponseFileTreePart { constructor(value, baseUri) { this.value = value; this.baseUri = baseUri; } }
class ChatResponseAnchorPart { constructor(value, title) { this.value = value; this.title = title; } }
class ChatResponseProgressPart { constructor(value) { this.value = value; } }
class ChatResponseReferencePart { constructor(value, iconPath) { this.value = value; this.iconPath = iconPath; } }
class ChatResponseCommandButtonPart { constructor(value) { this.value = value; } }
class ChatRequestTurn { constructor(prompt, command, references, participant, toolReferences) { Object.assign(this, { prompt, command, references, participant, toolReferences: toolReferences || [] }); } }
class ChatResponseTurn { constructor(response, result, participant, command) { Object.assign(this, { response, result, participant, command }); } }
class LanguageModelToolCallPart { constructor(callId, name, input) { this.callId = callId; this.name = name; this.input = input; } }
class LanguageModelToolResultPart { constructor(callId, content, isError) { this.callId = callId; this.content = content; this.isError = isError ?? false; } }
class LanguageModelPromptTsxPart { constructor(value) { this.value = value; } toJSON() { return { value: this.value }; } }
class LanguageModelToolResult { constructor(content) { this.content = content; } toJSON() { return { content: this.content }; } }
class LanguageModelDataPart {
  constructor(data, mimeType) { this.mimeType = mimeType; this.data = data; }
  static image(data, mimeType) { return new LanguageModelDataPart(data, mimeType); }
  static json(value, mime = 'text/x-json') { return new LanguageModelDataPart(new Uint8Array(Buffer.from(JSON.stringify(value, undefined, '\t'))), mime); }
  static text(value, mime = 'text/plain') { return new LanguageModelDataPart(new Uint8Array(Buffer.from(String(value))), mime); }
}
class McpStdioServerDefinition { constructor(label, command, args, env, version) { Object.assign(this, { label, command, args: args || [], env: env || {}, version }); this.cwd = undefined; } }
class McpHttpServerDefinition { constructor(label, uri, headers, version) { Object.assign(this, { label, uri, headers: headers || {}, version }); } }

module.exports = {
  Uri, Position, Range, Selection, Location, Disposable, EventEmitter, CancellationTokenSource, CancellationError,
  CancellationTokenNone, TextEdit, SnippetTextEdit, WorkspaceEdit, SnippetString, MarkdownString,
  CompletionItemKind, CompletionItemTag, CompletionTriggerKind, SymbolKind, SymbolTag, DiagnosticSeverity, DiagnosticTag,
  DocumentHighlightKind, StatusBarAlignment, ViewColumn, ConfigurationTarget, EndOfLine, TextEditorRevealType,
  TextEditorCursorStyle, TextEditorLineNumbersStyle, TextEditorSelectionChangeKind, TextDocumentSaveReason,
  TextDocumentChangeReason, DecorationRangeBehavior, OverviewRulerLane, ProgressLocation, FileType, FilePermission,
  FileChangeType, TreeItemCollapsibleState, TreeItemCheckboxState, ExtensionMode, ExtensionKind, UIKind, ColorThemeKind,
  FoldingRangeKind, SignatureHelpTriggerKind, CodeActionTriggerKind, InlayHintKind, InlineCompletionTriggerKind,
  QuickPickItemKind, LanguageStatusSeverity, DebugConsoleMode, DebugConfigurationProviderTriggerKind, TaskRevealKind,
  TaskPanelKind, TaskScope, ShellQuoting, TerminalLocation, TerminalExitReason, EnvironmentVariableMutatorType, CommentMode,
  CommentThreadCollapsibleState, CommentThreadState, NotebookCellKind, NotebookEditorRevealType, NotebookControllerAffinity,
  NotebookCellStatusBarAlignment, TestRunProfileKind, TestMessageStackFrame, LogLevel, SyntaxTokenType,
  DocumentPasteTriggerKind, InlineCompletionsDisposeReasonKind, PortAutoForwardAction, ChatResultFeedbackKind,
  LanguageModelChatMessageRole,
  CompletionItem, CompletionList, Hover, VerboseHover, Diagnostic, DiagnosticRelatedInformation, CodeActionKind, CodeAction,
  CodeLens, DocumentLink, DocumentSymbol, SymbolInformation, FoldingRange, SelectionRange, SignatureHelp,
  SignatureInformation, ParameterInformation, Color, ColorInformation, ColorPresentation, DocumentHighlight, InlayHint,
  InlayHintLabelPart, SemanticTokensLegend, SemanticTokens, SemanticTokensEdit, SemanticTokensEdits, SemanticTokensBuilder,
  CallHierarchyItem, CallHierarchyIncomingCall, CallHierarchyOutgoingCall, TypeHierarchyItem, LinkedEditingRanges,
  InlineValueText, InlineValueVariableLookup, InlineValueEvaluatableExpression, InlineCompletionItem, InlineCompletionList,
  EvaluatableExpression, DocumentDropEdit, DocumentPasteEdit, DocumentDropOrPasteEditKind, RelativePattern, ThemeColor,
  ThemeIcon, TreeItem, FileDecoration, FileSystemError, TabInputText, TabInputTextDiff, TabInputCustom, TabInputWebview,
  TabInputNotebook, TabInputNotebookDiff, TabInputTerminal, DebugAdapterExecutable, DebugAdapterServer,
  DebugAdapterNamedPipeServer, DebugAdapterInlineImplementation, Breakpoint, SourceBreakpoint, FunctionBreakpoint,
  DataBreakpoint, TaskGroup, ShellExecution, ProcessExecution, CustomExecution, Task, TerminalLink, TerminalProfile,
  NotebookRange, NotebookCellData, NotebookData, NotebookCellOutputItem, NotebookCellOutput, NotebookEdit, TestMessage,
  TestTag, TestRunRequest, LanguageModelChatMessage, LanguageModelTextPart, LanguageModelError, QuickInputButtons,
  InputBoxValidationSeverity, IndentAction, TerminalShellExecutionCommandLineConfidence, QuickInputButtonLocation,
  TimelineTriggerKind, LanguageModelChatToolMode, DataTransferItem, DataTransfer, TimelineItem, NotebookCellStatusBarItem,
  DebugThread, DebugStackFrame, TestCoverageCount, FileCoverage, StatementCoverage, BranchCoverage, DeclarationCoverage,
  TelemetryTrustedValue, ChatResponseMarkdownPart, ChatResponseFileTreePart, ChatResponseAnchorPart, ChatResponseProgressPart,
  ChatResponseReferencePart, ChatResponseCommandButtonPart, ChatRequestTurn, ChatResponseTurn, LanguageModelToolCallPart,
  LanguageModelToolResultPart, LanguageModelPromptTsxPart, LanguageModelToolResult, LanguageModelDataPart,
  McpStdioServerDefinition, McpHttpServerDefinition,
};
