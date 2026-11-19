/* RAD IDE Design View - GrapesJS host page. Python (radide/web_site/design.py) talks to it
   through QWebChannel object `rad` (JS -> Python) and the window.rad* functions (Python -> JS). */
(function () {
  'use strict';
  let rad = null;
  let editorLoaded = false, channelReady = false;
  let lastPayload = null;
  let initHtml = '', initCss = '';
  let muted = 0;

  const RAW_CSS =
    'rad-raw{display:inline-block;vertical-align:middle;margin:1px 2px;padding:1px 6px;border:1px dashed #b8860b;' +
    'border-radius:3px;background:#fff8dc;color:#7a5200;font:11px/16px Consolas,monospace;max-width:100%;' +
    'overflow:hidden;white-space:nowrap;text-overflow:ellipsis;cursor:default;user-select:none}' +
    'rad-raw::before{content:attr(data-rad-label)}' +
    'rad-raw[data-rad-label^="<script"],rad-raw[data-rad-label^="<style"]{background:#eef4ff;border-color:#4a78c2;color:#24457a}';

  const P = m => (m && m.default) || m;
  const plugins = [window.radBlocks];
  // PostCSS parser: keeps shorthands (padding: 2px) and unknown at-rules instead of the browser's CSSOM expansion
  if (window['grapesjs-parser-postcss']) plugins.unshift(ed => P(window['grapesjs-parser-postcss'])(ed, {}));
  if (window['gjs-blocks-basic'])
    plugins.push(ed => P(window['gjs-blocks-basic'])(ed, { category: 'Basic', flexGrid: true }));
  if (window['grapesjs-plugin-forms'])
    plugins.push(ed => P(window['grapesjs-plugin-forms'])(ed, { category: 'Forms' }));
  // the forms plugin's <button> type replaces the button's content by a 'text' trait (would drop <?= ... ?> labels)
  plugins.push(ed => { if (ed.Components.getType('button')) ed.Components.removeType('button'); });

  const editor = grapesjs.init({
    container: '#gjs', height: '100%', width: 'auto', fromElement: false,
    storageManager: false, noticeOnUnload: false, avoidInlineStyle: true, keepUnusedStyles: true,
    protectedCss: '', canvasCss: RAW_CSS,
    parser: { optionsHtml: { keepEmptyTextNodes: true, allowScripts: false, allowUnsafeAttr: true, allowUnsafeAttrValue: true } },
    panels: { defaults: [] },
    blockManager: { appendTo: '#pane-blocks' },
    layerManager: { appendTo: '#pane-layers' },
    selectorManager: { appendTo: '#selectors' },
    styleManager: { appendTo: '#styles' },
    traitManager: { appendTo: '#traits' },
    plugins,
  });
  window.radEditor = editor;

  // ---------------------------------------------------------------- side panel tabs
  function showPane(name) {
    document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.pane === name));
    document.querySelectorAll('.pane').forEach(p => p.classList.toggle('on', p.id === 'pane-' + name));
  }
  document.querySelectorAll('#tabs button').forEach(b => b.addEventListener('click', () => showPane(b.dataset.pane)));
  window.radShowPane = showPane;
  // The panel has a fixed width; in a narrow tab it folds away by itself so the canvas keeps a usable width
  // (the user's own choice - the strip or the Panels button - wins until the next automatic change).
  const side = document.getElementById('side'), sideToggle = document.getElementById('side-toggle');
  const AUTO_FOLD = 640;                 // fold the panel when the whole view is narrower than this
  let sideWanted = true, sideAuto = false;
  function applySide() {
    const fold = sideWanted && sideAuto;
    const on = sideWanted && !fold;
    side.classList.toggle('hidden', !on);
    sideToggle.innerHTML = on ? '&#9656;' : '&#9666;';
    sideToggle.title = on ? 'Hide the Toolbox / Layers / CSS / Attributes panel'
                          : 'Show the Toolbox / Layers / CSS / Attributes panel';
    if (editor && editor.refresh) setTimeout(() => editor.refresh(), 0);
  }
  function checkWidth() {
    const narrow = window.innerWidth < AUTO_FOLD;
    if (narrow !== sideAuto) { sideAuto = narrow; applySide(); }
  }
  sideToggle.addEventListener('click', () => {
    const on = !side.classList.contains('hidden');
    sideWanted = !on; sideAuto = false; applySide();
  });
  window.addEventListener('resize', checkWidth);
  window.radToggleSide = on => { sideWanted = !!on; sideAuto = false; applySide(); };
  window.radSideVisible = () => !side.classList.contains('hidden');
  // IDE theme: CSS custom properties (--rad-* for this page, --gjs-* for the GrapesJS panels)
  window.radTheme = function (css, dark) {
    document.getElementById('rad-theme').textContent = css;
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
    document.body.classList.toggle('rad-dark', !!dark);
    document.body.classList.toggle('rad-light', !dark);
  };

  // ---------------------------------------------------------------- helpers
  const innerHtml = () => editor.getWrapper().getInnerHTML();
  const curCss = () => editor.getCss({ avoidProtected: true, keepUnusedStyles: true }) || '';

  function injectHead() {
    const doc = editor.Canvas.getDocument();
    const p = lastPayload;
    if (!doc || !doc.head || !p) return;
    doc.querySelectorAll('.rad-inj').forEach(e => e.remove());
    if (p.base) {
      const b = doc.createElement('base');
      b.href = p.base; b.className = 'rad-inj';
      doc.head.insertBefore(b, doc.head.firstChild);
    }
    (p.styles || []).forEach(href => {
      const l = doc.createElement('link');
      l.rel = 'stylesheet'; l.href = href; l.className = 'rad-inj';
      doc.head.appendChild(l);
    });
    if (p.extraCss) {
      const s = doc.createElement('style');
      s.className = 'rad-inj'; s.textContent = p.extraCss;
      doc.head.appendChild(s);
    }
    watchInlineStyles(doc);
  }

  // Inline style="" attributes are protected as data-radstyle (see design.py protect()): show them in the canvas.
  function applyInline(el) {
    if (!el || el.nodeType !== 1) return;
    const v = el.getAttribute('data-radstyle');
    if (v !== null && v.indexOf('__RADPHP_') < 0 && el.getAttribute('style') !== v) el.setAttribute('style', v);
  }
  let watchedDoc = null;
  function watchInlineStyles(doc) {
    doc.querySelectorAll('[data-radstyle]').forEach(applyInline);
    if (watchedDoc === doc) return;
    watchedDoc = doc;
    new MutationObserver(ms => ms.forEach(m => {
      if (m.type === 'attributes') applyInline(m.target);
      else m.addedNodes.forEach(n => {
        if (n.nodeType !== 1) return;
        applyInline(n);
        n.querySelectorAll('[data-radstyle]').forEach(applyInline);
      });
    })).observe(doc.documentElement, { subtree: true, childList: true, attributes: true,
                                        attributeFilter: ['data-radstyle', 'style'] });
  }

  let changeTimer = null;
  function changed() {
    if (muted) return;
    clearTimeout(changeTimer);
    changeTimer = setTimeout(() => { if (rad) rad.jsChanged(); }, 250);
  }

  function describe(c) {
    if (!c) return '';
    const a = c.getAttributes();
    let s = '<' + (c.get('tagName') || c.get('type')) + '>';
    if (a.id) s += ' #' + a.id;
    const cls = (c.getClasses ? c.getClasses() : []).map(x => String(x).indexOf('__RADPHP_') >= 0 ? '(php)' : x);
    if (cls.length) s += ' .' + cls.join('.');
    return s + '  (' + (c.getName ? c.getName() : c.get('type')) + ')';
  }

  // ---------------------------------------------------------------- Python -> JS
  // classes produced by PHP (class="a <?= $x ?>") must never become CSS selectors: hide + deactivate them
  function hideSelector(sel) {
    if (sel && String(sel.get('name')).indexOf('__RADPHP_') >= 0) sel.set({ active: false, private: true, protected: true });
  }
  function hideTokenSelectors() { editor.Selectors.getAll().forEach(hideSelector); }
  editor.on('selector:add', hideSelector);

  window.radLoad = function (payload) {
    lastPayload = payload;
    muted++;
    try {
      editor.select(null);
      editor.setComponents(payload.html || '');
      editor.setStyle(payload.css || '');
      const w = editor.getWrapper();
      if (payload.bodyClass) w.setClass(payload.bodyClass.split(/\s+/).filter(Boolean));
      hideTokenSelectors();
      injectHead();
      editor.UndoManager.clear();
      if (editor.clearDirtyCount) editor.clearDirtyCount();
      initHtml = innerHtml();
      initCss = curCss();
    } finally {
      muted--;
    }
    return true;
  };
  window.radSetStyles = function (styles, extraCss, base) {
    if (!lastPayload) lastPayload = {};
    lastPayload.styles = styles; lastPayload.extraCss = extraCss;
    if (base !== undefined) lastPayload.base = base;
    injectHead();
  };
  window.radExport = function () {
    const html = innerHtml(), css = curCss();
    return JSON.stringify({ html, css, htmlChanged: html !== initHtml, cssChanged: css !== initCss });
  };
  window.radMarkSaved = function () { initHtml = innerHtml(); initCss = curCss(); };
  window.radUndo = () => { editor.UndoManager.undo(); };
  window.radRedo = () => { editor.UndoManager.redo(); };
  window.radHasUndo = () => [editor.UndoManager.hasUndo(), editor.UndoManager.hasRedo()];
  window.radDevice = name => { editor.setDevice(name); };
  window.radBorders = on => { on ? editor.runCommand('core:component-outline') : editor.stopCommand('core:component-outline'); };
  window.radPreview = on => { on ? editor.runCommand('core:preview') : editor.stopCommand('core:preview'); };
  window.radSetRaw = function (cid, code, label) {
    const m = editor.getWrapper().find('rad-raw').find(x => x.cid === cid);
    if (!m) return false;
    const attrs = Object.assign({}, m.getAttributes(), { 'data-rad-code': code, 'data-rad-label': label });
    delete attrs['data-rad-id'];
    m.setAttributes(attrs);                    // one undo step
    m.set('name', 'PHP: ' + label.slice(0, 40));
    changed();
    return true;
  };
  window.radSelected = () => describe(editor.getSelected());
  

  window.radEditRaw = function (cid, id, code) { if (rad) rad.jsEditRaw(cid, id, code == null ? '' : code, code != null); };

  // ---------------------------------------------------------------- events -> Python
  // storageManager is off, so 'update' does not fire: listen to the edit events themselves
  editor.on('update component:add component:remove component:update component:styleUpdate styleable:change ' +
            'selector:add selector:remove rule:update undo redo canvas:drop block:drag:stop rte:disable', changed);
  editor.UndoManager.getStack().on('add remove reset', changed);
  // "Inline style" trait for every element (edits the protected style="" attribute)
  editor.on('component:selected', c => {
    if (c && c.get('type') !== 'rad-raw' && c.get('type') !== 'textnode' && c.getTrait && !c.getTrait('data-radstyle'))
      c.addTrait({ type: 'text', name: 'data-radstyle', label: 'Inline style', placeholder: 'color: red; margin: 4px' },
                 { at: 0 });
  });
  editor.on('component:selected', c => {
    document.getElementById('sel-info').textContent = describe(c);
    if (rad) rad.jsSelected(describe(c));
  });
  editor.on('component:deselected', () => { document.getElementById('sel-info').textContent = ''; });
  editor.on('canvas:frame:load', injectHead);

  function ready() {
    if (editorLoaded && channelReady) rad.jsReady();
  }
  editor.on('load', () => {
    editorLoaded = true;
    editor.runCommand('core:component-outline');
    checkWidth();
    ready();
  });
  if (typeof QWebChannel !== 'undefined' && window.qt && qt.webChannelTransport) {
    new QWebChannel(qt.webChannelTransport, ch => { rad = ch.objects.rad; channelReady = true; ready(); });
  }
})();
