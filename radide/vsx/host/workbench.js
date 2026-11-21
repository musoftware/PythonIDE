'use strict';
// Workbench services of the extension host that used to be no-op mocks:
//   FileSystems   workspace.registerFileSystemProvider + workspace.fs routing for its schemes
//   Tabs          window.tabGroups (text / diff / webview / custom editor tabs), vscode.diff, tab close
//   Terminals     window.createTerminal: real processes (shellPath / default shell) or Pseudoterminals,
//                 shell integration (executeCommand + start / end events), profiles, links
//   Registries    URI handlers, file decorations, authentication providers, task providers,
//                 custom editors, notebook serializers, comments / tests / scm / chat models (no UI)
//
// Protocol additions (see bridge.py for the transport):
//   host -> IDE requests   window/showDiff {id, title, language, left, right, preserveFocus}
//                          tabs/close {diffId | path}      tabs/activate {diffId | path}
//   host -> IDE notify     diff/setText {id, side, text}    editor/setText {path, text}
//                          terminal/create|write|show|exit|dispose|rename   decorations/fileChanged {paths}
//                          fs/registered {scheme}
//   IDE -> host notify     tabs/active {kind, id|path}      tabs/closed {diffId}
//                          diff/changed {id, side, text}    diff/save {id}
//                          terminal/input {id, text}        terminal/closed {id}   terminal/link {id, line}
//                          editor/visibleRanges {path, ranges}
//   IDE -> host requests   uri/handle {uri}  decorations/file {paths}  terminal/profiles  terminal/newFromProfile {id}

const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');
const T = require('./types');

const decoder = new TextDecoder('utf-8');
const decode = (data) => (typeof data === 'string' ? data : decoder.decode(data || new Uint8Array()));
const encode = (text) => new Uint8Array(Buffer.from(String(text == null ? '' : text), 'utf8'));
const uriBase = (u) => { const p = (u && (u.scheme === 'file' ? u.fsPath : u.path)) || ''; return path.basename(p) || p || (u ? u.toString() : ''); };

// ============================================================================ file system providers
class FileSystems {
  constructor(host) {
    this.host = host;
    this.providers = new Map();          // scheme -> {ext, scheme, provider, isReadonly, isCaseSensitive}
  }

  register(ext, scheme, provider, options) {
    scheme = String(scheme);
    if (scheme === 'file') throw new Error("A filesystem provider for the scheme 'file' is already registered.");
    if (this.providers.has(scheme)) throw new Error(`A filesystem provider for the scheme '${scheme}' is already registered.`);
    const o = options || {};
    const entry = { ext, scheme, provider, isReadonly: !!o.isReadonly, isCaseSensitive: !!o.isCaseSensitive };
    this.providers.set(scheme, entry);
    let sub;
    try { if (provider && typeof provider.onDidChangeFile === 'function') sub = provider.onDidChangeFile((events) => this._changed(entry, events)); } catch (_) { /* */ }
    this.host.rpc.notify('fs/registered', { scheme, ext: ext ? ext.id : '', readonly: entry.isReadonly });
    return new T.Disposable(() => {
      if (this.providers.get(scheme) === entry) this.providers.delete(scheme);
      try { sub && sub.dispose && sub.dispose(); } catch (_) { /* */ }
    });
  }

  has(scheme) { return this.providers.has(scheme); }

  async entry(scheme) {
    if (!this.providers.has(scheme) && !this.host.contentProviders.has(scheme)) await this.host.activateByEvent('onFileSystem:' + scheme);
    return this.providers.get(scheme);
  }

  async read(uri) {
    const e = await this.entry(uri.scheme);
    if (!e) return undefined;
    return decode(await e.provider.readFile(uri));
  }

  _changed(entry, events) {
    for (const ev of events || []) {
      if (!ev || !ev.uri || ev.type === T.FileChangeType.Deleted) continue;
      const doc = this.host.docs.get(ev.uri);
      if (!doc || doc.isDirty) continue;
      Promise.resolve().then(() => entry.provider.readFile(ev.uri)).then((data) => {
        const text = decode(data);
        if (doc.getText() !== text) { this.host.docs.change(ev.uri, undefined, text, false); this.host.tabs.docUpdated(doc); }
      }).catch(() => {});
    }
    for (const w of this.host.watchers) {
      for (const ev of events || []) {
        if (!ev || !ev.uri || !w._matchUri || !w._matchUri(ev.uri)) continue;
        w._fireUri(ev.type === T.FileChangeType.Created ? 'create' : ev.type === T.FileChangeType.Deleted ? 'delete' : 'change', ev.uri);
      }
    }
  }

  // ---------------------------------------------------------------- workspace.fs for provider schemes
  async op(name, uri, ...args) {
    const e = await this.entry(uri.scheme);
    if (!e) throw T.FileSystemError.Unavailable(uri);
    const p = e.provider;
    switch (name) {
      case 'stat': return p.stat(uri);
      case 'readDirectory': return p.readDirectory(uri);
      case 'createDirectory': return p.createDirectory(uri);
      case 'readFile': return new Uint8Array(await p.readFile(uri));
      case 'writeFile':
        if (e.isReadonly) throw T.FileSystemError.NoPermissions(uri);
        return p.writeFile(uri, args[0], { create: true, overwrite: true });
      case 'delete': return p.delete(uri, { recursive: !!(args[0] && args[0].recursive), useTrash: !!(args[0] && args[0].useTrash) });
      default: throw T.FileSystemError.Unavailable(uri);
    }
  }

  async move(kind, src, dst, options, fileFs) {
    const overwrite = !!(options && options.overwrite);
    if (src.scheme === dst.scheme && src.scheme !== 'file') {
      const e = await this.entry(src.scheme);
      if (!e) throw T.FileSystemError.Unavailable(src);
      if (kind === 'rename') return e.provider.rename(src, dst, { overwrite });
      if (typeof e.provider.copy === 'function') return e.provider.copy(src, dst, { overwrite });
    }
    // across schemes (or a provider without copy): read + write (+ delete for rename)
    const readFs = src.scheme === 'file' ? fileFs : null;
    const data = readFs ? await readFs.readFile(src) : await this.op('readFile', src);
    if (!overwrite) {
      let exists = true;
      try { if (dst.scheme === 'file') await fileFs.stat(dst); else await this.op('stat', dst); } catch (_) { exists = false; }
      if (exists) throw T.FileSystemError.FileExists(dst);
    }
    if (dst.scheme === 'file') await fileFs.writeFile(dst, data); else await this.op('writeFile', dst, data);
    if (kind === 'rename') { if (src.scheme === 'file') await fileFs.delete(src); else await this.op('delete', src); }
    return undefined;
  }

  isWritable(scheme) {
    if (scheme === 'file') return true;
    const e = this.providers.get(scheme);
    return e ? !e.isReadonly : undefined;
  }
}

// ============================================================================ tabs (window.tabGroups)
class Tabs {
  constructor(host) {
    this.host = host;
    this.diffs = new Map();         // id -> {id, original, modified, label, sides}
    this.virtual = new Map();       // uri string -> {uri, path}   (non-file documents shown in the IDE)
    this.byPath = new Map();        // lower-case temp path -> uri string
    this.custom = new Map();        // webview handle -> {uri, viewType}
    this.pinned = new Set();
    this.activeKey = null;
    this._tabs = new Map();         // key -> Tab
    this._prev = new Map();         // key -> snapshot string
    this._n = 0;
    this._timer = null;
    this.tabsEm = new T.EventEmitter();
    this.groupsEm = new T.EventEmitter();
    const self = this;
    this.group = {
      isActive: true, viewColumn: T.ViewColumn.One,
      get activeTab() { return self._list().find((t) => t.isActive); },
      get tabs() { return self._list(); },
    };
    this.api = {
      get all() { return [self.group]; },
      get activeTabGroup() { return self.group; },
      onDidChangeTabs: this.tabsEm.event,
      onDidChangeTabGroups: this.groupsEm.event,
      close: (t, preserveFocus) => this.close(t, preserveFocus),
    };
  }

  // ---------------------------------------------------------------- model
  _entries() {
    const out = [];
    const host = this.host;
    for (const d of host.docs.all()) {
      if (d.uri.scheme !== 'file' || !d._ideOpen || this.byPath.has(d.uri.fsPath.toLowerCase())) continue;
      out.push({ key: 'text:' + d.uri.toString(), label: path.basename(d.uri.fsPath), input: () => new T.TabInputText(d.uri), dirty: d.isDirty, sig: d.uri.toString() });
    }
    for (const v of this.virtual.values()) {
      const d = host.docs.get(v.uri);
      out.push({ key: 'text:' + v.uri.toString(), label: uriBase(v.uri), input: () => new T.TabInputText(v.uri), dirty: !!(d && d.isDirty), sig: v.uri.toString() });
    }
    for (const e of this.diffs.values()) {
      const d = host.docs.get(e.modified);
      out.push({ key: 'diff:' + e.id, label: e.label, input: () => new T.TabInputTextDiff(e.original, e.modified), dirty: !!(d && d.isDirty), sig: e.original.toString() + '|' + e.modified.toString() });
    }
    for (const [h, it] of host.webviews.items) {
      if (it.kind !== 'panel') continue;
      const c = this.custom.get(h);
      out.push({ key: 'webview:' + h, label: it.owner.title || it.owner.viewType, dirty: false, handle: h, sig: (c ? 'c:' : 'w:') + it.owner.viewType,
        input: () => (c ? new T.TabInputCustom(c.uri, c.viewType) : new T.TabInputWebview('mainThreadWebview-' + it.owner.viewType)) });
    }
    for (const t of host.terminalsSvc.list()) {
      if (!t._editorArea) continue;
      out.push({ key: 'terminal:' + t._id, label: t.name, dirty: false, input: () => new T.TabInputTerminal(), sig: 'term' });
    }
    return out;
  }

  _list() {
    const entries = this._entries();
    const seen = new Set();
    const list = [];
    for (const e of entries) {
      seen.add(e.key);
      let tab = this._tabs.get(e.key);
      if (!tab || tab._sig !== e.sig) {
        tab = { _key: e.key, _sig: e.sig, _handle: e.handle, label: e.label, input: e.input(), group: this.group, isActive: false, isDirty: false, isPinned: false, isPreview: false };
        this._tabs.set(e.key, tab);
      }
      tab.label = e.label;
      tab.isDirty = !!e.dirty;
      tab.isActive = e.key === this.activeKey;
      tab.isPinned = this.pinned.has(e.key);
      list.push(tab);
    }
    for (const k of [...this._tabs.keys()]) if (!seen.has(k)) this._tabs.delete(k);
    return list;
  }

  /** something that may change the tabs happened: compare and fire onDidChangeTabs (coalesced) */
  changed() {
    if (this._timer) return;
    this._timer = setImmediate(() => {
      this._timer = null;
      const prevTabs = new Map(this._prevTabs || []);
      const list = this._list();
      const now = new Map(list.map((t) => [t._key, `${t.label}|${t.isActive}|${t.isDirty}|${t.isPinned}`]));
      const opened = []; const changed = []; const closed = [];
      for (const t of list) {
        if (!this._prev.has(t._key)) opened.push(t);
        else if (this._prev.get(t._key) !== now.get(t._key)) changed.push(t);
      }
      for (const [k] of this._prev) if (!now.has(k)) closed.push(prevTabs.get(k) || { _key: k, label: k, input: undefined, group: this.group, isActive: false, isDirty: false, isPinned: false, isPreview: false });
      const activeBefore = this._prevActive;
      this._prev = now;
      this._prevTabs = list.map((t) => [t._key, t]);
      this._prevActive = this.activeKey;
      if (opened.length || changed.length || closed.length) {
        try { this.tabsEm.fire({ opened, closed, changed }); } catch (e) { this.host.logHost('onDidChangeTabs listener failed: ' + e); }
      }
      if (activeBefore !== this.activeKey) {
        try { this.groupsEm.fire({ opened: [], closed: [], changed: [this.group] }); } catch (_) { /* */ }
      }
    });
  }

  setActive(key) { if (this.activeKey !== key) { this.activeKey = key; this.changed(); } }

  // ---------------------------------------------------------------- virtual documents shown in the IDE
  tempPathFor(uri) {
    const key = uri.toString();
    const v = this.virtual.get(key);
    if (v) return v.path;
    const h = require('crypto').createHash('md5').update(key).digest('hex').substring(0, 10);
    const name = uriBase(uri).replace(/[^\w.\-]+/g, '_') || 'document';
    return path.join(this.host.storageRoot, 'virtual', h, name);
  }

  addVirtual(uri, p) {
    this.virtual.set(uri.toString(), { uri, path: p });
    this.byPath.set(p.toLowerCase(), uri.toString());
    this.changed();
  }

  virtualFor(p) {
    if (!p) return undefined;
    const k = this.byPath.get(String(p).toLowerCase());
    return k ? this.virtual.get(k) : undefined;
  }

  removeVirtualPath(p) {
    const v = this.virtualFor(p);
    if (!v) return undefined;
    this.virtual.delete(v.uri.toString());
    this.byPath.delete(String(p).toLowerCase());
    if (this.activeKey === 'text:' + v.uri.toString()) this.activeKey = null;
    this.changed();
    return v;
  }

  /** a document changed on the extension side: refresh the IDE views showing it */
  docUpdated(doc, origin) {
    const key = doc.uri.toString();
    for (const e of this.diffs.values()) {
      if (origin && origin.diff === e.id) continue;
      if (e.modified.toString() === key) this.host.rpc.notify('diff/setText', { id: e.id, side: 'right', text: doc.getText() });
      if (e.original.toString() === key) this.host.rpc.notify('diff/setText', { id: e.id, side: 'left', text: doc.getText() });
    }
    const v = this.virtual.get(key);
    if (v && !(origin && origin.ide)) this.host.rpc.notify('editor/setText', { path: v.path, text: doc.getText() });
    this.changed();
  }

  // ---------------------------------------------------------------- diffs
  async _sideDoc(uri) {
    if (!uri) return { text: '', doc: undefined };
    try {
      const doc = await this.host.openTextDocument(uri);
      return { text: doc.getText(), doc };
    } catch (e) {
      return { text: '', doc: undefined };
    }
  }

  async openDiff(left, right, title, options) {
    if (!T.Uri.isUri(left)) left = left ? T.Uri.parse(String(left)) : undefined;
    if (!T.Uri.isUri(right)) right = T.Uri.parse(String(right));
    const opts = options && typeof options === 'object' ? options : {};
    const [l, r] = await Promise.all([this._sideDoc(left), this._sideDoc(right)]);
    if (!left) left = right.with({ scheme: 'untitled', path: right.path + '.empty' });
    // an existing diff of the same pair is revealed instead of opening a second one (VS Code does the same)
    for (const e of this.diffs.values()) {
      if (e.original.toString() === left.toString() && e.modified.toString() === right.toString()) {
        this.setActive('diff:' + e.id);
        this.host.diffActivated(e);
        await this.host.rpc.request('tabs/activate', { diffId: e.id });
        return undefined;
      }
    }
    const id = 'diff' + (++this._n);
    const label = title ? String(title) : `${uriBase(left)} ↔ ${uriBase(right)}`;
    const entry = { id, original: left, modified: right, label };
    this.diffs.set(id, entry);
    this.activeKey = 'diff:' + id;
    this.changed();
    this.host.diffActivated(entry);
    const side = (u, s, editable) => ({
      uri: u.toString(), title: uriBase(u), text: s.text, path: u.scheme === 'file' ? u.fsPath : null,
      editable, virtual: u.scheme !== 'file',
    });
    const rightEditable = right.scheme === 'file' || this.host.fsx.isWritable(right.scheme) === true || right.scheme === 'untitled';
    const lang = (r.doc && r.doc.languageId) || (l.doc && l.doc.languageId) || this.host.languageForPath(right.path);
    await this.host.rpc.request('window/showDiff', {
      id, title: label, language: lang, preserveFocus: !!opts.preserveFocus, preview: opts.preview !== false,
      left: side(left, l, false), right: side(right, r, rightEditable),
      selection: opts.selection ? [opts.selection.start.line, opts.selection.start.character, opts.selection.end.line, opts.selection.end.character] : null,
    });
    return undefined;
  }

  diffClosed(id) {
    const e = this.diffs.get(id);
    if (!e) return;
    this.diffs.delete(id);
    if (this.activeKey === 'diff:' + id) this.activeKey = null;
    this.changed();
    this.host.diffDeactivated(e);
  }

  diffChanged({ id, side, text }) {
    const e = this.diffs.get(id);
    if (!e) return;
    const uri = side === 'left' ? e.original : e.modified;
    if (uri.scheme === 'file') return;          // file buffers are the IDE's own editors / the file on disk
    const doc = this.host.docs.get(uri);
    if (!doc || doc.getText() === text) return;
    this.host.docs.change(uri, undefined, text, true);
    this.docUpdated(doc, { diff: id });
  }

  async diffSave({ id }) {
    const e = this.diffs.get(id);
    if (!e) return false;
    const doc = this.host.docs.get(e.modified);
    if (!doc) return false;
    return doc.save();
  }

  // ---------------------------------------------------------------- close / activate
  _tabsOf(arg) {
    const arr = Array.isArray(arg) ? arg : [arg];
    const out = [];
    for (const x of arr) {
      if (!x) continue;
      if (x === this.group || (x.tabs && x.viewColumn !== undefined)) out.push(...this._list());
      else out.push(x);
    }
    return out;
  }

  async close(arg, preserveFocus) {
    void preserveFocus;
    const tabs = this._tabsOf(arg);
    let all = true;
    for (const tab of tabs) {
      const key = tab._key || '';
      let ok = false;
      try {
        if (key.startsWith('diff:')) {
          const id = key.substring(5);
          if (this.diffs.has(id)) { ok = !!(await this.host.rpc.request('tabs/close', { diffId: id })); if (ok) this.diffClosed(id); }
        } else if (key.startsWith('webview:')) {
          const it = this.host.webviews.items.get(tab._handle);
          if (it && it.owner && typeof it.owner.dispose === 'function') { it.owner.dispose(); ok = true; }
        } else if (key.startsWith('terminal:')) {
          const t = this.host.terminalsSvc.byId(key.substring(9));
          if (t) { t.dispose(); ok = true; }
        } else if (key.startsWith('text:')) {
          const uri = T.Uri.parse(key.substring(5));
          const v = this.virtual.get(uri.toString());
          const p = v ? v.path : uri.fsPath;
          ok = !!(await this.host.rpc.request('tabs/close', { path: p }));
          if (ok && v) this.removeVirtualPath(p);
        }
      } catch (e) { this.host.logHost('tabGroups.close: ' + e); ok = false; }
      all = all && ok;
    }
    this.changed();
    return all;
  }

  async activate(tab) {
    const key = tab && tab._key;
    if (!key) return false;
    if (key.startsWith('diff:')) { await this.host.rpc.request('tabs/activate', { diffId: key.substring(5) }); }
    else if (key.startsWith('text:')) {
      const uri = T.Uri.parse(key.substring(5));
      const v = this.virtual.get(uri.toString());
      await this.host.rpc.request('tabs/activate', { path: v ? v.path : uri.fsPath });
    } else if (key.startsWith('webview:')) {
      const it = this.host.webviews.items.get(tab._handle);
      if (it && it.owner.reveal) it.owner.reveal();
    }
    this.setActive(key);
    return true;
  }
}

// ============================================================================ terminals
const MARK = '__RADIDE_DONE_';
const MARK_RE = /__RADIDE_DONE_(\d+)_(-?\d*)__/;

function shellKind(shellPath) {
  const b = path.basename(String(shellPath || '')).toLowerCase().replace(/\.exe$/, '');
  if (b === 'cmd') return 'cmd';
  if (b === 'powershell' || b === 'pwsh') return 'pwsh';
  if (['bash', 'sh', 'zsh', 'dash', 'ksh', 'fish'].includes(b)) return 'posix';
  return null;
}

class Terminals {
  constructor(host) {
    this.host = host;
    this.items = new Map();             // id -> terminal record
    this.active = undefined;
    this.profileProviders = new Map();  // profile id -> {ext, provider}
    this.linkProviders = new Set();     // {ext, provider}
    this.em = {};
    for (const k of ['open', 'close', 'active', 'state', 'shellIntegration', 'startExec', 'endExec']) this.em[k] = new T.EventEmitter();
    this._n = 0;
  }

  list() { return [...this.items.values()].map((r) => r.term); }
  byId(id) { const r = this.items.get(id); return r ? r.term : undefined; }

  _setActive(term) {
    if (this.active === term) return;
    this.active = term;
    try { this.em.active.fire(term); } catch (_) { /* */ }
  }

  _env(ext, options) {
    const base = options.strictEnv ? {} : Object.assign({}, process.env);
    // EnvironmentVariableCollection of every extension (VS Code applies them to new terminals)
    for (const e of this.host.extensions.values()) {
      const coll = e.context && e.context.environmentVariableCollection;
      if (!coll || typeof coll._apply !== 'function') continue;
      coll._apply(base);
    }
    for (const [k, v] of Object.entries(options.env || {})) {
      if (v === null || v === undefined) delete base[k]; else base[k] = String(v);
    }
    return base;
  }

  _cwd(options) {
    const c = options.cwd;
    let dir = c ? (T.Uri.isUri(c) ? c.fsPath : String(c)) : undefined;
    if (!dir || !fs.existsSync(dir)) {
      const f = this.host.workspaceFolders()[0];
      dir = f ? f.uri.fsPath : os.homedir();
    }
    return dir;
  }

  create(ext, a, b, c) {
    let options;
    if (typeof a === 'string' || a === undefined || a === null) options = { name: a || undefined, shellPath: b, shellArgs: c };
    else options = a;
    const host = this.host;
    const self = this;
    const id = 'term' + (++this._n);
    const rec = { id, ext, options, proc: null, pty: options.pty || null, buffer: '', exec: null };
    let name = options.name || (options.pty ? 'Extension Terminal' : path.basename(String(options.shellPath || this._defaultShell())).replace(/\.exe$/i, ''));
    let resolvePid;
    const pidPromise = new Promise((r) => { resolvePid = r; });
    const term = {
      _id: id,
      get name() { return name; },
      processId: pidPromise,
      creationOptions: Object.freeze(Object.assign({}, options)),
      exitStatus: undefined,
      state: { isInteractedWith: false, shell: undefined },
      shellIntegration: undefined,
      selection: undefined,
      _editorArea: !!(options.location && (options.location === T.TerminalLocation.Editor || options.location.viewColumn !== undefined)),
      sendText(text, shouldExecute) {
        self._input(rec, String(text) + (shouldExecute === false ? '' : (rec.pty ? '\r' : os.EOL)), false);
      },
      show(preserveFocus) {
        self._setActive(term);
        host.rpc.notify('terminal/show', { id, preserveFocus: !!preserveFocus });
      },
      hide() { host.rpc.notify('terminal/hide', { id }); },
      dispose() { self._close(rec, T.TerminalExitReason.Extension, undefined, true); },
    };
    rec.term = term;
    this.items.set(id, rec);
    host.rpc.notify('terminal/create', {
      id, name, pty: !!options.pty, hidden: !!options.hideFromUser, ext: ext ? ext.id : '',
      shellPath: options.shellPath, shellArgs: options.shellArgs, cwd: options.pty ? undefined : this._cwd(options),
    });
    if (options.pty) {
      const pty = options.pty;
      const subs = [];
      if (pty.onDidWrite) subs.push(pty.onDidWrite((d) => this._output(rec, String(d))));
      if (pty.onDidClose) subs.push(pty.onDidClose((code) => this._close(rec, T.TerminalExitReason.Extension, typeof code === 'number' ? code : undefined, false)));
      if (pty.onDidChangeName) subs.push(pty.onDidChangeName((n) => { name = String(n); host.rpc.notify('terminal/rename', { id, name }); }));
      if (pty.onDidOverrideDimensions) subs.push(pty.onDidOverrideDimensions(() => {}));
      rec.subs = subs;
      resolvePid(undefined);
      setImmediate(() => { try { pty.open && pty.open({ columns: 120, rows: 30 }); } catch (e) { host.log(ext, 'pseudoterminal open failed: ' + e); } });
    } else {
      this._spawn(rec, resolvePid);
    }
    if (!options.hideFromUser && !this.active) this._setActive(term);
    try { this.em.open.fire(term); } catch (_) { /* */ }
    this.host.tabs.changed();
    return term;
  }

  _defaultShell() {
    if (process.platform === 'win32') return process.env.ComSpec || 'cmd.exe';
    return process.env.SHELL || '/bin/sh';
  }

  _spawn(rec, resolvePid) {
    const o = rec.options;
    const shell = o.shellPath ? String(o.shellPath) : this._defaultShell();
    let args = o.shellArgs;
    if (typeof args === 'string') args = process.platform === 'win32' ? [args] : args.split(/\s+/).filter(Boolean);
    args = Array.isArray(args) ? args.map(String) : [];
    const kind = shellKind(shell);
    if (!o.shellPath && kind === 'cmd' && !args.length) args = ['/Q', '/K', 'chcp 65001>nul'];
    if (kind === 'pwsh' && !args.length) args = ['-NoLogo', '-NoProfile', '-NoExit', '-Command', '-'];
    let proc;
    try {
      proc = cp.spawn(shell, args, { cwd: this._cwd(o), env: this._env(rec.ext, o), windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], windowsVerbatimArguments: kind === 'cmd' });
    } catch (e) {
      this._output(rec, `\r\nThe terminal process failed to launch: ${e.message}\r\n`);
      resolvePid(undefined);
      setImmediate(() => this._close(rec, T.TerminalExitReason.Process, 1, false));
      return;
    }
    rec.proc = proc;
    rec.kind = kind;
    proc.on('error', (e) => { this._output(rec, `\r\nThe terminal process failed to launch: ${e.message}\r\n`); resolvePid(undefined); this._close(rec, T.TerminalExitReason.Process, 1, false); });
    proc.on('spawn', () => {
      resolvePid(proc.pid);
      rec.term.state = { isInteractedWith: false, shell: kind || undefined };
      if (kind) setTimeout(() => this._enableShellIntegration(rec), 30);
    });
    const onData = (d) => this._output(rec, d.toString('utf8'));
    proc.stdout.on('data', onData);
    proc.stderr.on('data', onData);
    proc.on('exit', (code) => this._close(rec, T.TerminalExitReason.Process, code === null ? undefined : code, false));
    proc.stdin.on('error', () => {});
  }

  _enableShellIntegration(rec) {
    if (!this.items.has(rec.id) || rec.term.shellIntegration) return;
    const self = this;
    const cwd = T.Uri.file(this._cwd(rec.options));
    const si = {
      cwd,
      executeCommand(a, b) {
        const line = b === undefined ? String(a) : [a, ...(b || [])].map((x) => (/\s/.test(String(x)) ? `"${x}"` : String(x))).join(' ');
        return self._execute(rec, si, line);
      },
    };
    rec.term.shellIntegration = si;
    try { this.em.shellIntegration.fire({ terminal: rec.term, shellIntegration: si }); } catch (_) { /* */ }
  }

  _execute(rec, si, line) {
    const n = ++this._n;
    const chunks = [];
    const waiters = [];
    let done = false;
    const exec = {
      commandLine: { value: line, isTrusted: true, confidence: 2 },
      cwd: si.cwd,
      read() {
        let i = 0;
        return {
          [Symbol.asyncIterator]() { return this; },
          next() {
            if (i < chunks.length) return Promise.resolve({ value: chunks[i++], done: false });
            if (done) return Promise.resolve({ value: undefined, done: true });
            return new Promise((r) => waiters.push(() => r(i < chunks.length ? { value: chunks[i++], done: false } : { value: undefined, done: true })));
          },
        };
      },
      _push(d) { chunks.push(d); waiters.splice(0).forEach((w) => w()); },
      _end() { done = true; waiters.splice(0).forEach((w) => w()); },
    };
    rec.exec = { n, exec, si };
    const marker = rec.kind === 'cmd' ? `${line} & echo ${MARK}${n}_%ERRORLEVEL%__`
      : rec.kind === 'pwsh' ? `${line}; echo "${MARK}${n}_$(if ($?) { if ($LASTEXITCODE) { $LASTEXITCODE } else { 0 } } else { if ($LASTEXITCODE) { $LASTEXITCODE } else { 1 } })__"`
        : `${line}; echo "${MARK}${n}_$?__"`;
    this._input(rec, marker + os.EOL, true);
    try { this.em.startExec.fire({ terminal: rec.term, shellIntegration: si, execution: exec }); } catch (_) { /* */ }
    return exec;
  }

  _output(rec, data) {
    let text = data;
    if (rec.exec) {
      rec.buffer += text;
      const m = MARK_RE.exec(rec.buffer);
      if (m && Number(m[1]) === rec.exec.n) {
        const { exec, si } = rec.exec;
        const before = rec.buffer.substring(0, m.index);
        rec.exec = null;
        rec.buffer = '';
        exec._push(before);
        exec._end();
        const code = m[2] === '' ? undefined : Number(m[2]);
        text = before.replace(/[^\n]*$/, (last) => (last.includes(MARK) ? '' : last));
        setImmediate(() => { try { this.em.endExec.fire({ terminal: rec.term, shellIntegration: si, execution: exec, exitCode: code }); } catch (_) { /* */ } });
      } else {
        // keep a tail in the buffer in case the marker is split over two chunks
        const cut = Math.max(0, rec.buffer.length - 200);
        const safe = rec.buffer.substring(0, cut);
        rec.buffer = rec.buffer.substring(cut);
        if (safe) rec.exec.exec._push(safe);
        text = safe;
        if (!text) return;
      }
    }
    text = text.split('\n').filter((l) => !(l.includes(MARK) && /%ERRORLEVEL%|\$LASTEXITCODE|\$\?/.test(l))).join('\n');
    if (text) this.host.rpc.notify('terminal/write', { id: rec.id, data: text });
  }

  _input(rec, text, internal) {
    if (!internal && !rec.term.state.isInteractedWith) {
      rec.term.state = { isInteractedWith: true, shell: rec.term.state.shell };
      try { this.em.state.fire(rec.term); } catch (_) { /* */ }
    }
    if (rec.pty) {
      if (typeof rec.pty.handleInput === 'function') { try { rec.pty.handleInput(text); } catch (e) { this.host.log(rec.ext, 'pseudoterminal input failed: ' + e); } }
      return;
    }
    if (rec.proc && rec.proc.stdin && rec.proc.stdin.writable) rec.proc.stdin.write(text);
  }

  _close(rec, reason, code, fromApi) {
    if (!this.items.has(rec.id)) return;
    this.items.delete(rec.id);
    rec.term.exitStatus = { code, reason };
    if (rec.exec) { rec.exec.exec._end(); rec.exec = null; }
    for (const s of rec.subs || []) { try { s.dispose(); } catch (_) { /* */ } }
    if (rec.pty && fromApi && typeof rec.pty.close === 'function') { try { rec.pty.close(); } catch (_) { /* */ } }
    if (rec.proc && rec.proc.exitCode === null) {
      try {
        if (process.platform === 'win32' && rec.proc.pid) cp.spawn('taskkill', ['/PID', String(rec.proc.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
        else rec.proc.kill();
      } catch (_) { /* */ }
    }
    this.host.rpc.notify(fromApi ? 'terminal/dispose' : 'terminal/exit', { id: rec.id, code });
    if (this.active === rec.term) this._setActive(this.list()[this.list().length - 1]);
    try { this.em.close.fire(rec.term); } catch (_) { /* */ }
    this.host.tabs.changed();
  }

  // ---------------------------------------------------------------- IDE -> host
  input({ id, text }) { const r = this.items.get(id); if (r) { this._setActive(r.term); this._input(r, String(text || ''), false); } }
  closedByUser({ id, code }) { const r = this.items.get(id); if (r) { if (r.pty && typeof r.pty.close === 'function') { try { r.pty.close(); } catch (_) { /* */ } } this._close(r, T.TerminalExitReason.User, code, false); } }
  focused({ id }) { const r = this.items.get(id); if (r) this._setActive(r.term); }

  async link({ id, line }) {
    const r = this.items.get(id);
    if (!r) return false;
    for (const lp of this.linkProviders) {
      try {
        const links = await lp.provider.provideTerminalLinks({ line: String(line || ''), terminal: r.term }, T.CancellationTokenNone);
        if (links && links.length) { await lp.provider.handleTerminalLink(links[0]); return true; }
      } catch (e) { this.host.log(lp.ext, 'terminal link provider failed: ' + e); }
    }
    return false;
  }

  registerProfileProvider(ext, id, provider) {
    this.profileProviders.set(id, { ext, provider });
    return new T.Disposable(() => { if (this.profileProviders.get(id)?.provider === provider) this.profileProviders.delete(id); });
  }

  registerLinkProvider(ext, provider) {
    const e = { ext, provider };
    this.linkProviders.add(e);
    return new T.Disposable(() => this.linkProviders.delete(e));
  }

  profiles() {
    const out = [];
    for (const ext of this.host.extensions.values()) {
      const t = (ext.packageJSON.contributes || {}).terminal || {};
      for (const p of t.profiles || []) if (p && p.id) out.push({ id: p.id, title: p.title || p.id, ext: ext.id });
    }
    return out;
  }

  async newFromProfile({ id }) {
    if (!this.profileProviders.has(id)) await this.host.activateByEvent('onTerminalProfile:' + id);
    const e = this.profileProviders.get(id);
    if (!e) return false;
    const cts = new T.CancellationTokenSource();
    const prof = await e.provider.provideTerminalProfile(cts.token);
    if (!prof || !prof.options) return false;
    const t = this.create(e.ext, prof.options);
    t.show();
    return true;
  }
}

// ============================================================================ environment variable collections
function envCollection(persistentDefault) {
  const m = new Map();
  const emitter = new T.EventEmitter();
  const coll = {
    persistent: persistentDefault !== false,
    description: undefined,
    replace(k, v, o) { m.set(k, { value: String(v), type: T.EnvironmentVariableMutatorType.Replace, options: o || {} }); emitter.fire(); },
    append(k, v, o) { m.set(k, { value: String(v), type: T.EnvironmentVariableMutatorType.Append, options: o || {} }); emitter.fire(); },
    prepend(k, v, o) { m.set(k, { value: String(v), type: T.EnvironmentVariableMutatorType.Prepend, options: o || {} }); emitter.fire(); },
    get(k) { return m.get(k); },
    forEach(cb, thisArg) { m.forEach((v, k) => cb.call(thisArg, k, v, coll)); },
    delete(k) { m.delete(k); },
    clear() { m.clear(); },
    getScoped() { return coll; },
    [Symbol.iterator]() { return m.entries(); },
    _apply(env) {
      const sep = process.platform === 'win32' ? ';' : ':';
      void sep;
      for (const [k, v] of m) {
        const cur = env[k] || '';
        if (v.type === T.EnvironmentVariableMutatorType.Replace) env[k] = v.value;
        else if (v.type === T.EnvironmentVariableMutatorType.Append) env[k] = cur + v.value;
        else env[k] = v.value + cur;
      }
    },
  };
  return coll;
}

module.exports = { FileSystems, Tabs, Terminals, envCollection, decode, encode, uriBase };
