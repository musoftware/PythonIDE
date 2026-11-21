'use strict';
// Webviews (vscode.window.registerWebviewViewProvider / createWebviewPanel / registerWebviewPanelSerializer).
// The extension side lives here; RAD IDE shows each webview in a QWebEngineView (radide/vsx/webview_ui.py)
// and relays postMessage both ways:
//   host -> IDE  webview/create {handle, kind, viewType, title, options, ext, extPath}
//                webview/html {handle, html}      webview/postMessage {handle, message}
//                webview/title {handle, title}    webview/reveal {handle}   webview/dispose {handle}
//                webviewView/registered {viewId, ext}
//   IDE -> host  webviewView/resolve (request) {viewId} -> {handle}
//                webview/message {handle, message}   webview/visible {handle, visible}
//                webview/closed {handle}

const path = require('path');
const T = require('./types');

class Webviews {
  constructor(host) {
    this.host = host;
    this.providers = new Map();    // viewId -> {ext, provider, options}
    this.serializers = new Map();  // viewType -> {ext, serializer}
    this.items = new Map();        // handle -> {webview, owner (view|panel), ext}
    this.views = new Map();        // viewId -> handle of the resolved view
    this._n = 0;
  }

  get rpc() { return this.host.rpc; }

  // ------------------------------------------------------------------ the Webview object
  _makeWebview(ext, handle, options) {
    const rpc = this.rpc;
    const host = this.host;
    const onMessage = new T.EventEmitter();
    let html = '';
    let opts = Object.assign({ enableScripts: false }, options || {});
    const webview = {
      get options() { return opts; },
      set options(v) { opts = Object.assign({}, v || {}); rpc.notify('webview/options', { handle, options: plainOptions(opts) }); },
      get html() { return html; },
      set html(v) { html = String(v == null ? '' : v); rpc.notify('webview/html', { handle, html }); },
      onDidReceiveMessage: onMessage.event,
      postMessage(message) {
        rpc.notify('webview/postMessage', { handle, message: jsonSafe(message) });
        return Promise.resolve(true);
      },
      asWebviewUri(uri) {
        // RAD IDE serves local resources from 127.0.0.1 (radide/vsx/webview_ui.py ResourceServer)
        if (uri && uri.scheme === 'file' && host.webviewBase) {
          const p = uri.fsPath.replace(/\\/g, '/').replace(/^\/*/, '/');
          const enc = p.split('/').map((s) => encodeURIComponent(s).replace(/%3A/gi, ':')).join('/');
          return new WebviewUri(host.webviewBase + '/f' + enc);
        }
        return uri;
      },
      get cspSource() { return (host.webviewOrigin || '') + " 'self' data: blob:"; },
    };
    return { webview, onMessage };
  }

  _register(ext, kind, viewType, title, options, owner, wv) {
    const handle = owner._handle;
    this.items.set(handle, { ext, kind, owner, webview: wv.webview, onMessage: wv.onMessage });
    this.rpc.notify('webview/create', {
      handle, kind, viewType, title: title || '', options: plainOptions(options),
      ext: ext ? ext.id : '', extPath: ext ? ext.path : '',
      roots: rootsOf(ext, options),
    });
  }

  // ------------------------------------------------------------------ webview views (sidebar)
  registerProvider(ext, viewId, provider, options) {
    this.providers.set(viewId, { ext, provider, options: options || {} });
    this.rpc.notify('webviewView/registered', { viewId, ext: ext ? ext.id : '' });
    return new T.Disposable(() => { if (this.providers.get(viewId)?.provider === provider) this.providers.delete(viewId); });
  }

  async resolveView({ viewId }) {
    if (this.views.has(viewId)) return { handle: this.views.get(viewId) };
    if (!this.providers.has(viewId)) await this.host.activateByEvent('onView:' + viewId);
    const entry = this.providers.get(viewId);
    if (!entry) return { handle: null, error: `no webview provider registered for ${viewId}` };
    const handle = 'wv' + (++this._n);
    const ext = entry.ext;
    const wv = this._makeWebview(ext, handle, {});
    const visEm = new T.EventEmitter();
    const dispEm = new T.EventEmitter();
    const self = this;
    let title = viewTitle(ext, viewId);
    let description;
    const view = {
      _handle: handle, viewType: viewId, webview: wv.webview, visible: true, badge: undefined,
      get title() { return title; }, set title(v) { title = v; self.rpc.notify('webview/title', { handle, title: String(v || '') }); },
      get description() { return description; }, set description(v) { description = v; },
      onDidChangeVisibility: visEm.event, onDidDispose: dispEm.event,
      show(preserveFocus) { self.rpc.notify('webview/reveal', { handle, preserveFocus: !!preserveFocus }); },
      _visEm: visEm, _dispEm: dispEm,
    };
    this._register(ext, 'view', viewId, title, entry.options.webviewOptions || {}, view, wv);
    this.views.set(viewId, handle);
    const cts = new T.CancellationTokenSource();
    try {
      await entry.provider.resolveWebviewView(view, { state: undefined }, cts.token);
    } catch (e) {
      this.host.log(ext, `resolveWebviewView(${viewId}) failed: ${e && e.stack || e}`);
    }
    return { handle };
  }

  // ------------------------------------------------------------------ webview panels (editor area)
  createPanel(ext, viewType, title, showOptions, options) {
    const handle = 'wv' + (++this._n);
    const wv = this._makeWebview(ext, handle, options);
    return this._panel(ext, handle, viewType, title, showOptions, options, wv);
  }

  _panel(ext, handle, viewType, title, showOptions, options, wv) {
    const self = this;
    const visEm = new T.EventEmitter();
    const dispEm = new T.EventEmitter();
    let disposed = false;
    let iconPath;
    let viewColumn = typeof showOptions === 'number' ? showOptions : (showOptions && showOptions.viewColumn) || T.ViewColumn.One;
    const panel = {
      _handle: handle, viewType, webview: wv.webview, options: options || {}, active: true, visible: true,
      get title() { return title; }, set title(v) { title = String(v || ''); self.rpc.notify('webview/title', { handle, title }); },
      get iconPath() { return iconPath; }, set iconPath(v) { iconPath = v; },
      get viewColumn() { return viewColumn; },
      onDidChangeViewState: visEm.event, onDidDispose: dispEm.event,
      reveal(col, preserveFocus) { if (col) viewColumn = col; self.rpc.notify('webview/reveal', { handle, preserveFocus: !!preserveFocus }); },
      dispose() {
        if (disposed) return;
        disposed = true;
        self.rpc.notify('webview/dispose', { handle });
        self._closed(handle);
      },
      _visEm: visEm, _dispEm: dispEm,
    };
    this._register(ext, 'panel', viewType, title, options || {}, panel, wv);
    return panel;
  }

  registerSerializer(ext, viewType, serializer) {
    this.serializers.set(viewType, { ext, serializer });
    return new T.Disposable(() => this.serializers.delete(viewType));
  }

  // ------------------------------------------------------------------ IDE -> host
  message({ handle, message }) {
    const it = this.items.get(handle);
    if (!it) return;
    try { it.onMessage.fire(message); } catch (e) { this.host.log(it.ext, 'webview message handler failed: ' + (e && e.stack || e)); }
  }

  visible({ handle, visible }) {
    const it = this.items.get(handle);
    if (!it) return;
    const o = it.owner;
    o.visible = !!visible;
    if (it.kind === 'panel') { o.active = !!visible; o._visEm.fire({ webviewPanel: o }); } else o._visEm.fire();
  }

  _closed(handle) {
    const it = this.items.get(handle);
    if (!it) return;
    this.items.delete(handle);
    for (const [vid, h] of this.views) if (h === handle) this.views.delete(vid);
    it.owner.visible = false;
    try { it.owner._dispEm.fire(); } catch (e) { this.host.log(it.ext, 'webview dispose handler failed: ' + e); }
  }

  closed({ handle }) { this._closed(handle); }

  register(R, N) {
    R('webviewView/resolve', (p) => this.resolveView(p));
    R('webviewView/providers', async () => [...this.providers.keys()]);
    N('webview/message', (p) => this.message(p));
    N('webview/visible', (p) => this.visible(p));
    N('webview/closed', (p) => this.closed(p));
  }
}

// a vscode.Uri whose toString() is exactly the served URL (Uri.parse would re-encode the path)
class WebviewUri extends T.Uri {
  constructor(url) {
    const u = new URL(url);
    super('http', u.host, decodeURIComponent(u.pathname), '', '');
    this._url = url;
  }
  toString() { return this._url; }
  toJSON() { return { $mid: 1, scheme: 'http', authority: this.authority, path: this.path, external: this._url }; }
}

function plainOptions(o) {
  o = o || {};
  return { enableScripts: !!o.enableScripts, enableForms: o.enableForms !== false, retainContextWhenHidden: !!o.retainContextWhenHidden,
    enableCommandUris: !!o.enableCommandUris };
}

function rootsOf(ext, o) {
  const roots = ((o && o.localResourceRoots) || []).map((u) => (u && u.fsPath) || String(u));
  if (ext && ext.path) roots.push(ext.path);
  return roots;
}

function viewTitle(ext, viewId) {
  const views = (ext && ext.packageJSON && ext.packageJSON.contributes && ext.packageJSON.contributes.views) || {};
  for (const list of Object.values(views)) for (const v of list || []) if (v && v.id === viewId) return v.name || viewId;
  return viewId;
}

function jsonSafe(v) {
  try { return JSON.parse(JSON.stringify(v === undefined ? null : v)); } catch (_) { return null; }
}

module.exports = { Webviews };
