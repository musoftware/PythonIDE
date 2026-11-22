'use strict';
// vscode.window.registerTreeDataProvider / createTreeView (semantics of src/vs/workbench/api/common/extHostTreeViews.ts):
// handles "1/<id>" for items with an id, "0/<parent>/<n>:<label>" otherwise; reveal() needs getParent;
// onDidChangeTreeData(element | element[] | undefined) refreshes those nodes (or the root).
//   host -> IDE  tree/registered {viewId, ext, options}   tree/changed {viewId, handles?}
//                tree/update {viewId, title?, description?, message?, badge?}   tree/reveal {viewId, chain, options}
//   IDE -> host  tree/children (request) {viewId, handle} -> [item]   tree/resolve (request) {viewId, handle}
//                tree/selection {viewId, handles}   tree/visible {viewId, visible}   tree/expand {viewId, handle, expanded}
//                tree/checkbox {viewId, items: [[handle, state]]}   tree/focus {viewId, handle}

const path = require('path');
const T = require('./types');
const C = require('./convert');

const PROVIDER_TIMEOUT = 8000;
function withTimeout(promise, ms, dflt) {
  let timer;
  return Promise.race([Promise.resolve(promise), new Promise((res) => { timer = setTimeout(() => res(dflt), ms); })]).finally(() => clearTimeout(timer));
}

function iconOf(icon, resourceUri, collapsible) {
  if (!icon) return undefined;
  if (icon instanceof T.ThemeIcon || (icon && typeof icon.id === 'string' && !icon.scheme)) return { codicon: icon.id, color: icon.color && icon.color.id };
  const file = (x) => (x && x.scheme === 'file' ? x.fsPath : (typeof x === 'string' ? x : undefined));
  if (T.Uri.isUri(icon) || typeof icon === 'string') return { path: file(icon) };
  if (icon.light || icon.dark) return { path: file(icon.dark || icon.light), light: file(icon.light), dark: file(icon.dark) };
  void resourceUri; void collapsible;
  return undefined;
}

class TreeView {
  constructor(svc, ext, viewId, options) {
    this._svc = svc;
    this._ext = ext;
    this.viewId = viewId;
    this._options = options || {};
    this._provider = this._options.treeDataProvider;
    this._handles = new Map();      // handle -> element
    this._nodes = new Map();        // element -> {handle, parent (handle|null), item}
    this._children = new Map();     // parent handle ('' = root) -> [handles]
    this._title = undefined;
    this._description = undefined;
    this._message = '';
    this._badge = undefined;
    this.visible = false;
    this.selection = [];
    const E = (n) => { const e = new T.EventEmitter(); this['_' + n] = e; return e.event; };
    this.onDidChangeSelection = E('sel');
    this.onDidChangeVisibility = E('vis');
    this.onDidExpandElement = E('exp');
    this.onDidCollapseElement = E('col');
    this.onDidChangeCheckboxState = E('chk');
    this.onDidChangeActiveItem = E('act');
    this._sub = this._provider && typeof this._provider.onDidChangeTreeData === 'function'
      ? this._provider.onDidChangeTreeData((el) => this._changed(el)) : null;
  }

  get rpc() { return this._svc.host.rpc; }
  get title() { return this._title; }
  set title(v) { this._title = v; this.rpc.notify('tree/update', { viewId: this.viewId, title: v === undefined ? null : String(v) }); }
  get description() { return this._description; }
  set description(v) { this._description = v; this.rpc.notify('tree/update', { viewId: this.viewId, description: v === undefined ? null : String(v) }); }
  get message() { return this._message; }
  set message(v) { this._message = v; this.rpc.notify('tree/update', { viewId: this.viewId, message: C.markdownText(v) || '' }); }
  get badge() { return this._badge; }
  set badge(v) { this._badge = v; this.rpc.notify('tree/update', { viewId: this.viewId, badge: v ? { value: v.value, tooltip: v.tooltip } : null }); }
  get activeItem() { return undefined; }

  _changed(el) {
    const list = el === undefined || el === null ? null : (Array.isArray(el) ? el : [el]);
    if (!list) { this.rpc.notify('tree/changed', { viewId: this.viewId }); return; }
    const handles = list.map((e) => this._nodes.get(e)).filter(Boolean).map((n) => n.handle);
    this.rpc.notify('tree/changed', { viewId: this.viewId, handles: handles.length === list.length ? handles : undefined });
  }

  _handleFor(element, item, parentHandle) {
    if (item.id) return `1/${item.id}`;
    const old = this._nodes.get(element);
    const label = typeof item.label === 'string' ? item.label : (item.label && item.label.label) || (item.resourceUri ? path.basename(item.resourceUri.fsPath || item.resourceUri.path) : '');
    const prefix = parentHandle || '0';
    const elementId = String(label).replace('/', '//');
    let n = 0; let h;
    do { h = `${prefix}/${n}:${elementId}`; n++; } while (this._handles.has(h) && this._handles.get(h) !== element && (!old || old.handle !== h));
    return h;
  }

  async _item(element) {
    const item = await withTimeout(this._provider.getTreeItem(element), PROVIDER_TIMEOUT, undefined);
    return item || new T.TreeItem('');
  }

  _serialize(h, item) {
    const label = typeof item.label === 'string' ? item.label : (item.label && item.label.label) || (item.resourceUri ? path.basename(item.resourceUri.fsPath || item.resourceUri.path) : '');
    const host = this._svc.host;
    return {
      handle: h, label,
      highlights: item.label && typeof item.label === 'object' ? item.label.highlights : undefined,
      description: typeof item.description === 'string' ? item.description : (item.description === true && item.resourceUri ? path.dirname(host.asRelativePath(item.resourceUri, false)) : ''),
      tooltip: item.tooltip === undefined ? undefined : C.markdownText(item.tooltip),
      collapsible: item.collapsibleState || 0,
      command: item.command ? host.cmdCache.put(item.command) : undefined,
      icon: iconOf(item.iconPath, item.resourceUri, item.collapsibleState),
      resource: item.resourceUri ? (item.resourceUri.scheme === 'file' ? item.resourceUri.fsPath : item.resourceUri.toString()) : undefined,
      contextValue: item.contextValue,
      checkbox: item.checkboxState === undefined ? undefined : (typeof item.checkboxState === 'object' ? item.checkboxState.state : item.checkboxState),
      checkboxTooltip: item.checkboxState && typeof item.checkboxState === 'object' ? item.checkboxState.tooltip : undefined,
      path: item.resourceUri && item.resourceUri.scheme === 'file' ? item.resourceUri.fsPath : undefined,
      accessibility: item.accessibilityInformation ? item.accessibilityInformation.label : undefined,
    };
  }

  async children(handle) {
    if (!this._provider) return [];
    const parent = handle ? this._handles.get(handle) : undefined;
    if (handle && parent === undefined) return [];
    const kids = (await withTimeout(this._provider.getChildren(parent), PROVIDER_TIMEOUT, [])) || [];
    const out = [];
    const list = [];
    for (const el of kids) {
      let item;
      try { item = await this._item(el); } catch (e) { this._svc.host.log(this._ext, `getTreeItem failed: ${e && e.stack || e}`); continue; }
      const h = this._handleFor(el, item, handle || '');
      const old = this._nodes.get(el);
      if (old && old.handle !== h) this._handles.delete(old.handle);
      this._handles.set(h, el);
      this._nodes.set(el, { handle: h, parent: handle || null, item });
      list.push(h);
      out.push(this._serialize(h, item));
    }
    this._children.set(handle || '', list);
    return out;
  }

  async resolve(handle) {
    const el = this._handles.get(handle);
    const node = el !== undefined ? this._nodes.get(el) : undefined;
    if (!node || typeof this._provider.resolveTreeItem !== 'function') return node ? this._serialize(handle, node.item) : null;
    try {
      const r = await withTimeout(this._provider.resolveTreeItem(node.item, el, T.CancellationTokenNone), PROVIDER_TIMEOUT, undefined);
      if (r) node.item = r;
    } catch (_) { /* */ }
    return this._serialize(handle, node.item);
  }

  async reveal(element, options) {
    options = options || { select: true, focus: false };
    const o = { select: options.select === undefined || options.select === null ? true : !!options.select, focus: !!options.focus, expand: options.expand === undefined || options.expand === null ? false : options.expand };
    if (element === undefined) { this.rpc.notify('tree/reveal', { viewId: this.viewId, chain: [], options: o }); return; }
    if (typeof this._provider.getParent !== 'function') throw new Error("Required registered TreeDataProvider to implement 'getParent' method to access 'reveal' method");
    // parent chain from the root, loading each level so the handles exist
    const chain = [];
    for (let el = element; el !== undefined && el !== null; el = await this._provider.getParent(el)) chain.unshift(el);
    let parentHandle = '';
    const handles = [];
    for (const el of chain) {
      if (!this._nodes.has(el) || this._nodes.get(el).parent !== (parentHandle || null)) await this.children(parentHandle || undefined);
      const n = this._nodes.get(el);
      if (!n) break;
      handles.push(n.handle);
      parentHandle = n.handle;
    }
    this.rpc.notify('tree/reveal', { viewId: this.viewId, chain: handles, options: o });
  }

  // IDE -> host
  selectionChanged(handles) {
    this.selection = (handles || []).map((h) => this._handles.get(h)).filter((e) => e !== undefined);
    this._sel.fire({ selection: this.selection });
  }
  visibilityChanged(visible) {
    if (this.visible === !!visible) return;
    this.visible = !!visible;
    this._vis.fire({ visible: this.visible });
  }
  expanded(handle, expanded) {
    const el = this._handles.get(handle);
    if (el === undefined) return;
    (expanded ? this._exp : this._col).fire({ element: el });
  }
  checkbox(items) {
    const changed = [];
    for (const [h, state] of items || []) {
      const el = this._handles.get(h);
      if (el === undefined) continue;
      const n = this._nodes.get(el);
      if (n && n.item) n.item.checkboxState = state;
      changed.push([el, state]);
    }
    if (changed.length) this._chk.fire({ items: changed });
  }
  element(handle) { return this._handles.get(handle); }

  dispose() {
    if (this._sub) this._sub.dispose();
    this._svc.views.delete(this.viewId);
    this.rpc.notify('tree/disposed', { viewId: this.viewId });
  }
}

class TreeViews {
  constructor(host) {
    this.host = host;
    this.views = new Map();     // viewId -> TreeView
  }

  _make(ext, viewId, options) {
    const old = this.views.get(viewId);
    if (old && old._sub) old._sub.dispose();
    const tv = new TreeView(this, ext, viewId, options);
    this.views.set(viewId, tv);
    const o = options || {};
    this.host.rpc.notify('tree/registered', { viewId, ext: ext ? ext.id : '', options: { canSelectMany: !!o.canSelectMany, showCollapseAll: !!o.showCollapseAll, manageCheckboxStateManually: !!o.manageCheckboxStateManually, dragAndDrop: !!o.dragAndDropController } });
    return tv;
  }

  register(ext, viewId, provider) {
    const tv = this._make(ext, viewId, { treeDataProvider: provider });
    return new T.Disposable(() => tv.dispose());
  }

  create(ext, viewId, options) {
    if (!options || !options.treeDataProvider) throw new Error('Options with treeDataProvider is mandatory');
    const tv = this._make(ext, viewId, options);
    // the public object: VS Code's TreeView shape (properties are live)
    return tv;
  }

  async children({ viewId, handle }) {
    if (!this.views.has(viewId)) await this.host.activateByEvent('onView:' + viewId);
    const tv = this.views.get(viewId);
    return tv ? tv.children(handle || undefined) : [];
  }

  // the arguments a tree item's context-menu / title command receives: (element) or (element, selection[])
  commandArgs(viewId, handle, selected) {
    const tv = this.views.get(viewId);
    if (!tv) return [];
    const el = handle ? tv.element(handle) : undefined;
    if (!tv._options.canSelectMany || !selected || selected.length < 2) return el === undefined ? [] : [el];
    return [el, selected.map((h) => tv.element(h)).filter((e) => e !== undefined)];
  }

  register_rpc(R, N) {
    R('tree/children', (p) => this.children(p));
    R('tree/resolve', async (p) => { const tv = this.views.get(p.viewId); return tv ? tv.resolve(p.handle) : null; });
    R('tree/command', async (p) => {
      // a view/item/context or view/title command: run it with the tree element(s) as arguments
      const args = this.commandArgs(p.viewId, p.handle, p.selected);
      return C.plain(await this.host.executeCommand(p.command, args));
    });
    N('tree/selection', (p) => { const tv = this.views.get(p.viewId); if (tv) tv.selectionChanged(p.handles); });
    N('tree/visible', (p) => { const tv = this.views.get(p.viewId); if (tv) tv.visibilityChanged(p.visible); });
    N('tree/expand', (p) => { const tv = this.views.get(p.viewId); if (tv) tv.expanded(p.handle, p.expanded); });
    N('tree/checkbox', (p) => { const tv = this.views.get(p.viewId); if (tv) tv.checkbox(p.items); });
  }
}

module.exports = { TreeViews, TreeView };
