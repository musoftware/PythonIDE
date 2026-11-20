'use strict';
// vscode.TextDocument / TextLine models fed by the IDE's editors (full text on every change).

const T = require('./types');

const DEFAULT_WORD = /(-?\d*\.\d\w*)|([^`~!@#$%^&*()\-=+[{\]}\\|;:'",.<>/?\s]+)/g;

class TextLine {
  constructor(lineNumber, text, isLast) {
    this.lineNumber = lineNumber;
    this.text = text;
    this._isLast = isLast;
  }
  get range() { return new T.Range(this.lineNumber, 0, this.lineNumber, this.text.length); }
  get rangeIncludingLineBreak() {
    return this._isLast ? this.range : new T.Range(this.lineNumber, 0, this.lineNumber + 1, 0);
  }
  get firstNonWhitespaceCharacterIndex() { const m = /^(\s*)/.exec(this.text); return m ? m[1].length : 0; }
  get isEmptyOrWhitespace() { return this.firstNonWhitespaceCharacterIndex === this.text.length; }
}

class TextDocument {
  constructor(uri, languageId, version, text, store) {
    this.uri = uri;
    this.languageId = languageId || 'plaintext';
    this.version = version || 1;
    this.isDirty = false;
    this.isClosed = false;
    this.encoding = 'utf8';
    this._store = store;
    this._setText(text || '');
  }

  _setText(text) {
    this._text = text;
    this._lines = text.split(/\r\n|\r|\n/);
    this.eol = text.indexOf('\r\n') >= 0 ? T.EndOfLine.CRLF : T.EndOfLine.LF;
    this._offsets = null;
  }

  get fileName() { return this.uri.scheme === 'file' ? this.uri.fsPath : this.uri.path; }
  get isUntitled() { return this.uri.scheme === 'untitled'; }
  get lineCount() { return this._lines.length; }
  get notebook() { return undefined; }

  _lineOffsets() {
    if (!this._offsets) {
      const offs = [0];
      const t = this._text;
      for (let i = 0; i < t.length; i++) {
        const c = t.charCodeAt(i);
        if (c === 13) { if (t.charCodeAt(i + 1) === 10) i++; offs.push(i + 1); } else if (c === 10) offs.push(i + 1);
      }
      this._offsets = offs;
    }
    return this._offsets;
  }

  getText(range) {
    if (!range) return this._text;
    const r = this.validateRange(range);
    return this._text.substring(this.offsetAt(r.start), this.offsetAt(r.end));
  }

  lineAt(lineOrPos) {
    const line = typeof lineOrPos === 'number' ? lineOrPos : lineOrPos.line;
    if (line < 0 || line >= this._lines.length) throw new Error('Illegal value for `line`');
    return new TextLine(line, this._lines[line], line === this._lines.length - 1);
  }

  offsetAt(position) {
    const p = this.validatePosition(position);
    return this._lineOffsets()[p.line] + p.character;
  }

  positionAt(offset) {
    offset = Math.max(0, Math.min(Math.floor(offset), this._text.length));
    const offs = this._lineOffsets();
    let lo = 0; let hi = offs.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (offs[mid] <= offset) lo = mid; else hi = mid - 1;
    }
    return new T.Position(lo, Math.min(offset - offs[lo], this._lines[lo].length));
  }

  validatePosition(position) {
    let line = Math.max(0, position.line | 0);
    let ch = Math.max(0, position.character | 0);
    if (line >= this._lines.length) { line = this._lines.length - 1; ch = this._lines[line].length; }
    ch = Math.min(ch, this._lines[line].length);
    if (position instanceof T.Position && line === position.line && ch === position.character) return position;
    return new T.Position(line, ch);
  }

  validateRange(range) {
    const s = this.validatePosition(range.start);
    const e = this.validatePosition(range.end);
    if (range instanceof T.Range && s === range.start && e === range.end) return range;
    return new T.Range(s, e);
  }

  getWordRangeAtPosition(position, regex) {
    const p = this.validatePosition(position);
    const text = this._lines[p.line];
    let re = regex || DEFAULT_WORD;
    if (!re.global) re = new RegExp(re.source, re.flags + 'g');
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(text))) {
      const start = m.index; const end = start + m[0].length;
      if (start <= p.character && p.character <= end && m[0].length) return new T.Range(p.line, start, p.line, end);
      if (start > p.character) break;
      if (!m[0].length) re.lastIndex++;
    }
    return undefined;
  }

  save() { return this._store ? this._store.saveDocument(this) : Promise.resolve(false); }
}

class DocumentStore {
  constructor() {
    this.docs = new Map();          // uri string -> TextDocument
    this.onDidOpen = new T.EventEmitter();
    this.onDidClose = new T.EventEmitter();
    this.onDidChange = new T.EventEmitter();
    this.onDidSave = new T.EventEmitter();
    this.onWillSave = new T.EventEmitter();
    this.saveHandler = null;        // (doc) => Promise<bool>
  }

  get(uri) { return this.docs.get(typeof uri === 'string' ? uri : uri.toString()); }
  all() { return [...this.docs.values()]; }

  open(uri, languageId, version, text) {
    const key = uri.toString();
    const old = this.docs.get(key);
    if (old && !old.isClosed) {
      if (old.languageId !== languageId) {        // language changed: VS Code closes and re-opens
        this.close(uri);
      } else {
        this.change(uri, version, text);
        return old;
      }
    }
    const doc = new TextDocument(uri, languageId, version, text, this);
    this.docs.set(key, doc);
    this.onDidOpen.fire(doc);
    return doc;
  }

  change(uri, version, text, dirty) {
    const doc = this.get(uri);
    if (!doc) return undefined;
    if (dirty !== undefined) doc.isDirty = !!dirty;
    if (doc._text === text) return doc;
    const oldEnd = doc.positionAt(doc._text.length);
    const range = new T.Range(new T.Position(0, 0), oldEnd);
    const rangeLength = doc._text.length;
    doc._setText(text);
    doc.version = version && version > doc.version ? version : doc.version + 1;
    this.onDidChange.fire({ document: doc, contentChanges: [{ range, rangeOffset: 0, rangeLength, text }], reason: undefined });
    return doc;
  }

  saved(uri) {
    const doc = this.get(uri);
    if (!doc) return;
    doc.isDirty = false;
    this.onDidSave.fire(doc);
  }

  close(uri) {
    const doc = this.get(uri);
    if (!doc) return;
    this.docs.delete(uri.toString());
    doc.isClosed = true;
    this.onDidClose.fire(doc);
  }

  saveDocument(doc) { return this.saveHandler ? this.saveHandler(doc) : Promise.resolve(false); }
}

module.exports = { TextDocument, TextLine, DocumentStore };
