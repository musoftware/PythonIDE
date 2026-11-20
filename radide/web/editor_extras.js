/* RAD IDE editor extras - Python side: radide/features/editor_extras.py (channel object "radex").
 *
 * Injected into radide/web/editor.html once Monaco is ready. Adds:
 *   - split view of the same file (side by side / top-bottom; both views share one model, so they
 *     are always in sync),
 *   - user snippets (VS Code snippet format, tab stops and placeholders by Monaco's snippet engine),
 *   - macro recording / replay of editor keystrokes and commands,
 *   - keymaps: Visual Studio, VS Code (Monaco default), Vim (monaco-vim, MIT, bundled in
 *     radide/web/monaco-vim/) and basic Emacs; one set of multi-cursor keys in every keymap.
 * Everything is reached through window.radex; the Python side calls it with runJavaScript.
 */
(function () {
  'use strict';
  if (window.radex || !window.radEditor || !window.monaco) return;
  const editor = window.radEditor;
  const ch = window.radChannel;
  const rad = ch && ch.objects.rad;
  const host = ch && ch.objects.radex;            // may be missing (tests without the feature)
  const KM = monaco.KeyMod, KC = monaco.KeyCode, KChord = monaco.KeyMod.chord;
  const radex = window.radex = { editors: [editor], active: editor, editor2: null, keymap: 'vscode',
                               split: 'none', version: 1 };

  // ------------------------------------------------------------------ layout (panes + status bars)
  const css = document.createElement('style');
  css.textContent = `
    #radex-root { position: absolute; left: 0; top: 0; right: 0; bottom: 0; display: flex; flex-direction: column; }
    #radex-panes { flex: 1 1 auto; display: flex; flex-direction: row; min-height: 0; min-width: 0; }
    #radex-panes.down { flex-direction: column; }
    .radex-pane { flex: 1 1 0; display: flex; flex-direction: column; min-width: 0; min-height: 0; overflow: hidden; }
    .radex-ed { flex: 1 1 0; min-height: 0; min-width: 0; }
    .radex-sash { flex: 0 0 5px; background: var(--radex-sash, rgba(128,128,128,.35)); cursor: col-resize; }
    #radex-panes.down > .radex-sash { cursor: row-resize; }
    .radex-status { flex: 0 0 auto; display: none; font: 12px Consolas, 'Cascadia Mono', monospace; padding: 2px 8px;
                   background: var(--radex-status-bg, #f3f3f3); color: var(--radex-status-fg, #000);
                   border-top: 1px solid var(--radex-sash, rgba(128,128,128,.35)); white-space: nowrap; overflow: hidden; }
    .radex-status input { font: inherit; background: transparent; color: inherit; border: 0; outline: none; width: 80%; }
    body.radex-vim .radex-status { display: block; }
    .radex-rec { position: absolute; right: 18px; top: 4px; z-index: 50; display: none; padding: 1px 8px; border-radius: 8px;
                font: 11px 'Segoe UI', sans-serif; background: #C42B1C; color: #fff; pointer-events: none; }
    body.radex-recording .radex-rec { display: block; }
  `;
  document.head.appendChild(css);
  const el1 = document.getElementById('editor');
  const root = document.createElement('div'); root.id = 'radex-root';
  const panes = document.createElement('div'); panes.id = 'radex-panes';
  const pane1 = document.createElement('div'); pane1.className = 'radex-pane';
  const status1 = document.createElement('div'); status1.className = 'radex-status';
  const recBadge = document.createElement('div'); recBadge.className = 'radex-rec'; recBadge.textContent = '● REC';
  el1.parentNode.insertBefore(root, el1);
  root.appendChild(panes); panes.appendChild(pane1); pane1.appendChild(el1); pane1.appendChild(status1);
  root.appendChild(recBadge);
  el1.classList.add('radex-ed');
  el1.style.width = 'auto'; el1.style.height = 'auto';
  let pane2 = null, sash = null, status2 = null;

  function focused() {
    return radex.editors.find(e => e.hasTextFocus()) || radex.active || editor;
  }
  radex.focused = focused;
  function track(ed) {
    ed.onDidFocusEditorText(() => { radex.active = ed; });
  }
  track(editor);

  function updateChrome() {
    const me = el1.querySelector('.monaco-editor');
    if (!me) return;
    const cs = getComputedStyle(me);
    const bg = (cs.getPropertyValue('--vscode-editorWidget-background') || cs.getPropertyValue('--vscode-editor-background')).trim();
    const fg = (cs.getPropertyValue('--vscode-editor-foreground') || '').trim();
    const bd = (cs.getPropertyValue('--vscode-editorWidget-border') || cs.getPropertyValue('--vscode-contrastBorder') || '').trim();
    if (bg) root.style.setProperty('--radex-status-bg', bg);
    if (fg) root.style.setProperty('--radex-status-fg', fg);
    if (bd) root.style.setProperty('--radex-sash', bd);
  }
  const origTheme = window.radSetTheme;
  if (origTheme) window.radSetTheme = function (t) { origTheme(t); setTimeout(updateChrome, 0); };
  setTimeout(updateChrome, 0);

  // options of the first view follow to the second one (font, theme size, read-only ...)
  const MIRROR = ['fontFamily', 'fontSize', 'readOnly', 'minimap', 'wordWrap', 'renderWhitespace', 'tabSize',
                  'lineNumbers', 'cursorStyle', 'cursorBlinking', 'multiCursorModifier'];
  editor.onDidChangeConfiguration(() => {
    if (!radex.editor2) return;
    const raw = editor.getRawOptions(), o = {};
    MIRROR.forEach(k => { if (raw[k] !== undefined) o[k] = raw[k]; });
    radex.editor2.updateOptions(o);
  });

  function makeSash() {
    const s = document.createElement('div'); s.className = 'radex-sash';
    s.addEventListener('mousedown', ev => {
      ev.preventDefault();
      const down = panes.classList.contains('down');
      const r = panes.getBoundingClientRect();
      const move = e => {
        const f = down ? (e.clientY - r.top) / r.height : (e.clientX - r.left) / r.width;
        const p = Math.max(0.1, Math.min(0.9, f));
        pane1.style.flex = p + ' 1 0'; pane2.style.flex = (1 - p) + ' 1 0';
      };
      const up = () => { document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up); };
      document.addEventListener('mousemove', move); document.addEventListener('mouseup', up);
    });
    return s;
  }

  function wireSecond(ed2) {
    track(ed2);
    ed2.onDidChangeCursorPosition(e => { if (ed2.hasTextFocus() && rad) rad.jsCursor(e.position.lineNumber - 1, e.position.column - 1); });
    ed2.onDidChangeCursorSelection(e => { if (!ed2.hasTextFocus() || !rad) return; const s = e.selection;
      rad.jsSelection(s.startLineNumber - 1, s.startColumn - 1, s.endLineNumber - 1, s.endColumn - 1); });
    ed2.onContextMenu(e => { const p = e.target.position;
      if (rad) rad.jsContextMenu(p ? p.lineNumber - 1 : 0, e.event.posx, e.event.posy); });
    ed2.onMouseDown(e => {
      if (rad && e.target.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN)
        rad.jsToggleBreakpoint(e.target.position.lineNumber - 1);
    });
  }

  /** mode: 'right' (side by side) | 'down' (top / bottom) | 'none' (one view) | 'toggle' */
  radex.setSplit = function (mode) {
    if (mode === 'toggle') mode = radex.split === 'none' ? 'right' : 'none';
    if (mode !== 'right' && mode !== 'down') mode = 'none';
    if (mode === 'none') {
      if (radex.editor2) {
        disposeKeymap(radex.editor2);
        radex.editor2.dispose();
        pane2.remove(); sash.remove();
        radex.editor2 = null; pane2 = null; sash = null; status2 = null;
        radex.editors = [editor]; radex.active = editor;
      }
      pane1.style.flex = '1 1 0';
      panes.classList.remove('down');
      radex.split = 'none';
      editor.focus();
      return radex.split;
    }
    panes.classList.toggle('down', mode === 'down');
    if (!radex.editor2) {
      sash = makeSash();
      pane2 = document.createElement('div'); pane2.className = 'radex-pane';
      const el2 = document.createElement('div'); el2.className = 'radex-ed'; el2.id = 'editor2';
      status2 = document.createElement('div'); status2.className = 'radex-status';
      pane2.appendChild(el2); pane2.appendChild(status2);
      panes.appendChild(sash); panes.appendChild(pane2);
      const raw = editor.getRawOptions(), o = {};
      Object.keys(raw).forEach(k => { if (k !== 'model' && k !== 'value' && k !== 'dimension') o[k] = raw[k]; });
      o.model = editor.getModel(); o.automaticLayout = true;
      const ed2 = monaco.editor.create(el2, o);
      const st = editor.saveViewState();
      if (st) ed2.restoreViewState(st);
      radex.editor2 = ed2;
      radex.editors = [editor, ed2];
      wireSecond(ed2);
      applyKeymap(ed2, status2);
      addCommonActions(ed2);
    }
    pane1.style.flex = '1 1 0'; pane2.style.flex = '1 1 0';
    radex.split = mode;
    return radex.split;
  };
  radex.splitInfo = () => ({ split: radex.split, views: radex.editors.length,
    sameModel: !!radex.editor2 && radex.editor2.getModel() === editor.getModel(),
    rects: radex.editors.map(e => { const r = e.getContainerDomNode().getBoundingClientRect();
      return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; }) });

  // actions every view gets (focus aware: with two views the shortcut runs on the focused one)
  function addCommonActions(ed) {
    const d = [];
    d.push(ed.addAction({ id: 'rad.definition', label: 'Go to Definition', keybindings: [KC.F12],
      run: () => { const t = focused(), p = t.getPosition(); if (rad) rad.jsDefinition(p.lineNumber - 1, p.column - 1); } }));
    d.push(ed.addAction({ id: 'radex.split.right', label: 'View: Split Editor Right',
      keybindings: [KM.CtrlCmd | KC.Backslash], run: () => radex.setSplit(radex.split === 'right' ? 'none' : 'right') }));
    d.push(ed.addAction({ id: 'radex.split.down', label: 'View: Split Editor Down', run: () => radex.setSplit('down') }));
    d.push(ed.addAction({ id: 'radex.split.none', label: 'View: Single Editor (remove split)', run: () => radex.setSplit('none') }));
    d.push(ed.addAction({ id: 'radex.snippet.insert', label: 'Snippets: Insert Snippet...',
      run: () => host && host.jsCommand('insertSnippet') }));
    d.push(ed.addAction({ id: 'radex.macro.toggle', label: 'Macros: Start/Stop Recording',
      run: () => host && host.jsCommand('macroToggle') }));
    d.push(ed.addAction({ id: 'radex.macro.play', label: 'Macros: Run Temporary Macro',
      run: () => host && host.jsCommand('macroPlay') }));
    return d;
  }
  addCommonActions(editor);

  // ------------------------------------------------------------------ user snippets
  let snipDisp = [];
  radex.snippets = {};
  /** map: languageId ('*' = every language) -> [{name, prefix, body, description}] */
  radex.setSnippets = function (map) {
    snipDisp.forEach(d => d.dispose()); snipDisp = [];
    radex.snippets = map || {};
    Object.keys(radex.snippets).forEach(lang => {
      const list = radex.snippets[lang] || [];
      if (!list.length) return;
      snipDisp.push(monaco.languages.registerCompletionItemProvider(lang, {
        provideCompletionItems: (model, pos) => {
          if (!radex.editors.some(e => e.getModel() === model)) return { suggestions: [] };
          const w = model.getWordUntilPosition(pos);
          const line = model.getLineContent(pos.lineNumber).substring(0, pos.column - 1);
          return { suggestions: list.map(s => {
            // prefixes such as "!html" or "#reg" start with non-word characters: replace them too
            let start = w.startColumn;
            const m = /[^\s]*$/.exec(line);
            if (m && s.prefix && s.prefix.startsWith(m[0]) && m[0].length) start = pos.column - m[0].length;
            return { label: { label: s.prefix, description: s.name }, kind: monaco.languages.CompletionItemKind.Snippet,
              detail: (s.description || s.name) + ' (user snippet)', documentation: { value: '```\n' + s.body + '\n```' },
              insertText: s.body, insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              range: new monaco.Range(pos.lineNumber, start, pos.lineNumber, pos.column), sortText: '!' + s.prefix,
              filterText: s.prefix };
          }) };
        } }));
    });
    return Object.keys(radex.snippets).length;
  };
  radex.insertSnippet = function (body) {
    const ed = focused();
    ed.focus();
    ed.getContribution('snippetController2').insert(body);
    return true;
  };

  // ------------------------------------------------------------------ macros
  const SKIP_CMD = /^(rad\.|radex\.|type$|compositionStart|compositionEnd|replacePreviousChar|paste$|cut$|editor\.action\.clipboard|editor\.action\.inlineSuggest|_|setContext|vim\.|workbench\.|editor\.action\.triggerParameterHints|hideSuggestWidget$|closeParameterHints$)/;
  const mac = { rec: false, events: [], hooked: new Set(), clip: '' };
  function cmdService(ed) { return ed._commandService; }
  function serializable(a) {
    if (a === undefined || a === null) return null;
    try { const s = JSON.stringify(a); return s && s.length < 2000 ? JSON.parse(s) : null; } catch (e) { return null; }
  }
  function push(ev) {
    if (!mac.rec) return;
    const last = mac.events[mac.events.length - 1];
    if (ev.t === 'type' && last && last.t === 'type' && ev.text !== '\n' && last.text.slice(-1) !== '\n') {
      last.text += ev.text; return;
    }
    mac.events.push(ev);
  }
  function hookRecorder(ed) {
    if (mac.hooked.has(ed)) return;
    mac.hooked.add(ed);
    const svc = cmdService(ed);
    if (svc && svc.executeCommand && !svc._radexWrapped) {
      // keybindings run their command through the command service: record the outermost ones
      svc._radexWrapped = true;
      const orig = svc.executeCommand;
      let depth = 0;
      svc.executeCommand = function (id, ...args) {
        if (mac.rec && depth === 0 && !SKIP_CMD.test(id) && radex.editors.indexOf(focused()) >= 0)
          push({ t: 'cmd', id: id, args: serializable(args[0]) });
        depth++;
        try { return orig.call(this, id, ...args); } finally { depth--; }
      };
    }
    if (ed.onDidType) ed.onDidType(text => { if (ed.hasTextFocus()) push({ t: 'type', text: text }); });
    ed.onDidPaste(e => {
      if (!mac.rec || !e || !e.range) return;
      push({ t: 'paste', text: ed.getModel().getValueInRange(e.range) });
    });
    ed.onKeyDown(e => {
      if (!mac.rec) return;
      const be = e.browserEvent;
      if ((be.ctrlKey || be.metaKey) && !be.altKey && !be.shiftKey) {
        const k = be.key.toLowerCase();
        if (k === 'x') push({ t: 'cut' });
        else if (k === 'c') push({ t: 'copy' });
      }
    });
  }
  radex.macroStart = function () {
    radex.editors.forEach(hookRecorder);
    mac.events = []; mac.rec = true;
    document.body.classList.add('radex-recording');
    focused().focus();
    return true;
  };
  radex.macroStop = function () {
    mac.rec = false;
    document.body.classList.remove('radex-recording');
    return JSON.stringify(mac.events);
  };
  radex.macroRecording = () => mac.rec;
  function tick() { return new Promise(r => setTimeout(r, 0)); }
  async function playOne(ed, e) {
    const model = ed.getModel();
    switch (e.t) {
      case 'type': ed.trigger('macro', 'type', { text: e.text }); break;
      case 'paste': ed.trigger('macro', 'paste', { text: e.text, pasteOnNewLine: false, multicursorText: null }); break;
      case 'copy': { const s = ed.getSelection(); mac.clip = s && !s.isEmpty() ? model.getValueInRange(s) : model.getLineContent(ed.getPosition().lineNumber) + '\n'; break; }
      case 'cut': {
        const s = ed.getSelection();
        if (s && !s.isEmpty()) { mac.clip = model.getValueInRange(s); ed.executeEdits('macro', [{ range: s, text: '' }]); }
        else { const l = ed.getPosition().lineNumber; mac.clip = model.getLineContent(l) + '\n';
          ed.executeEdits('macro', [{ range: new monaco.Range(l, 1, l + 1, 1), text: '' }]); }
        break;
      }
      case 'cmd': {
        ed.trigger('macro', e.id, e.args === null ? undefined : e.args);
        if (!/^(cursor|delete|tab$|outdent$|editor\.action\.(insertLine|copyLines|moveLines|deleteLines|indentLines|outdentLines|commentLine|addCommentLine|removeCommentLine|transpose|transformTo))/.test(e.id)) await tick();
        break;
      }
    }
  }
  /** events: the JSON list from macroStop(); times: how many times to run it */
  radex.macroPlay = async function (events, times) {
    if (typeof events === 'string') events = JSON.parse(events);
    const ed = focused();
    ed.focus();
    ed.pushUndoStop();
    for (let i = 0; i < (times || 1); i++)
      for (const e of events) await playOne(ed, e);
    ed.pushUndoStop();
    return true;
  };

  // ------------------------------------------------------------------ keymaps
  const kmDisp = new Map();          // editor -> [IDisposable]
  let vimLoading = null;
  function loadVim() {
    if (window.MonacoVim) return Promise.resolve(window.MonacoVim);
    if (vimLoading) return vimLoading;
    vimLoading = new Promise((resolve, reject) => {
      const amd = window.define;
      window.define = undefined;           // the UMD build must take its "global" branch, not AMD
      const s = document.createElement('script');
      s.src = 'monaco-vim/monaco-vim.umd.js';
      s.onload = () => { window.define = amd; resolve(window.MonacoVim); defineVimEx(); };
      s.onerror = e => { window.define = amd; vimLoading = null; reject(e); };
      document.head.appendChild(s);
    });
    return vimLoading;
  }
  function defineVimEx() {
    const Vim = window.MonacoVim && window.MonacoVim.VimMode && window.MonacoVim.VimMode.Vim;
    if (!Vim || radex._vimEx) return;
    radex._vimEx = true;
    Vim.defineEx('write', 'w', () => host && host.jsCommand('save'));
    Vim.defineEx('wq', 'wq', () => { if (host) { host.jsCommand('save'); host.jsCommand('close'); } });
    Vim.defineEx('quit', 'q', () => host && host.jsCommand('close'));
    Vim.defineEx('xit', 'x', () => { if (host) { host.jsCommand('save'); host.jsCommand('close'); } });
    Vim.defineEx('vsplit', 'vs', () => radex.setSplit('right'));
    Vim.defineEx('split', 'sp', () => radex.setSplit('down'));
    Vim.defineEx('only', 'on', () => radex.setSplit('none'));
  }
  function disposeKeymap(ed) {
    (kmDisp.get(ed) || []).forEach(d => { try { d.dispose(); } catch (e) { /* already gone */ } });
    kmDisp.delete(ed);
    ed._radexMark = false;
  }
  function act(ed, list, id, label, keys, run, when) {
    list.push(ed.addAction({ id: id, label: label, keybindings: keys, keybindingContext: when || 'editorTextFocus',
      run: () => run(focused()) }));
  }
  const cmd = id => ed => ed.trigger('keymap', id, null);

  // multi-cursor: the same keys in Visual Studio, VS Code and Emacs (Monaco already has
  // Ctrl+Alt+Up/Down, Alt+Click, Shift+Alt+drag, Shift+Alt+I and Ctrl+D/Ctrl+Shift+L for VS Code)
  function multiCursor(ed, list) {
    act(ed, list, 'radex.mc.next', 'Multi-cursor: Add Caret at Next Match', [KM.Shift | KM.Alt | KC.Period],
        cmd('editor.action.addSelectionToNextFindMatch'));
    act(ed, list, 'radex.mc.all', 'Multi-cursor: Add Carets at All Matches', [KM.Shift | KM.Alt | KC.Semicolon],
        cmd('editor.action.selectHighlights'));
    act(ed, list, 'radex.mc.prevRemove', 'Multi-cursor: Remove Last Caret', [KM.Shift | KM.Alt | KC.Comma],
        cmd('cursorUndo'));
  }

  function visualStudio(ed, list) {
    const A = (id, label, keys, run, when) => act(ed, list, 'radex.vs.' + id, label, keys, run, when);
    A('formatDoc', 'Format Document', [KChord(KM.CtrlCmd | KC.KeyK, KM.CtrlCmd | KC.KeyD), KChord(KM.CtrlCmd | KC.KeyE, KM.CtrlCmd | KC.KeyD)],
      cmd('editor.action.formatDocument'));
    A('cutLine', 'Line Cut', [KM.CtrlCmd | KC.KeyL], e => {
      const p = e.getPosition(), m = e.getModel();
      const r = p.lineNumber < m.getLineCount() ? new monaco.Range(p.lineNumber, 1, p.lineNumber + 1, 1)
                                               : new monaco.Range(p.lineNumber, 1, p.lineNumber, m.getLineMaxColumn(p.lineNumber));
      const text = m.getValueInRange(r);
      try { navigator.clipboard.writeText(text); } catch (ex) { /* no clipboard permission */ }
      radex.lastCut = text;
      e.executeEdits('vs', [{ range: r, text: '' }]);
    });
    A('deleteLine', 'Line Delete', [KM.CtrlCmd | KM.Shift | KC.KeyL], cmd('editor.action.deleteLines'));
    A('duplicate', 'Duplicate', [KM.CtrlCmd | KC.KeyD], cmd('editor.action.copyLinesDownAction'));
    A('brace', 'Go to Matching Brace', [KM.CtrlCmd | KC.BracketRight], cmd('editor.action.jumpToBracket'));
    A('foldToggle', 'Toggle Outlining Expansion', [KChord(KM.CtrlCmd | KC.KeyM, KM.CtrlCmd | KC.KeyM)], cmd('editor.toggleFold'));
    A('foldAll', 'Toggle All Outlining', [KChord(KM.CtrlCmd | KC.KeyM, KM.CtrlCmd | KC.KeyL)], e => {
      e._radexFolded = !e._radexFolded; e.trigger('vs', e._radexFolded ? 'editor.foldAll' : 'editor.unfoldAll', null); });
    A('foldDefs', 'Collapse to Definitions', [KChord(KM.CtrlCmd | KC.KeyM, KM.CtrlCmd | KC.KeyO)], cmd('editor.foldLevel2'));
    A('unfold', 'Stop Outlining', [KChord(KM.CtrlCmd | KC.KeyM, KM.CtrlCmd | KC.KeyP)], cmd('editor.unfoldAll'));
    A('lower', 'Make Lowercase', [KM.CtrlCmd | KC.KeyU], cmd('editor.action.transformToLowercase'));
    A('upper', 'Make Uppercase', [KM.CtrlCmd | KM.Shift | KC.KeyU], cmd('editor.action.transformToUppercase'));
    A('lineAbove', 'Line Open Above', [KM.CtrlCmd | KC.Enter], cmd('editor.action.insertLineBefore'));
    A('lineBelow', 'Line Open Below', [KM.CtrlCmd | KM.Shift | KC.Enter], cmd('editor.action.insertLineAfter'));
    A('members', 'List Members', [KM.CtrlCmd | KC.KeyJ], cmd('editor.action.triggerSuggest'));
    A('quickInfo', 'Quick Info', [KChord(KM.CtrlCmd | KC.KeyK, KM.CtrlCmd | KC.KeyI)], cmd('editor.action.showHover'));
    A('params', 'Parameter Info', [KChord(KM.CtrlCmd | KC.KeyK, KM.CtrlCmd | KC.KeyP)], cmd('editor.action.triggerParameterHints'));
    A('snippet', 'Insert Snippet', [KChord(KM.CtrlCmd | KC.KeyK, KM.CtrlCmd | KC.KeyX)], () => host && host.jsCommand('insertSnippet'));
    A('surround', 'Surround With', [KChord(KM.CtrlCmd | KC.KeyK, KM.CtrlCmd | KC.KeyS)], () => host && host.jsCommand('insertSnippet'));
    A('wordDelete', 'Delete Horizontal White Space', [KChord(KM.CtrlCmd | KC.KeyK, KM.CtrlCmd | KC.Backslash)], cmd('editor.action.trimTrailingWhitespace'));
    A('colUp', 'Box Selection Up', [KM.Shift | KM.Alt | KC.UpArrow], cmd('cursorColumnSelectUp'));
    A('colDown', 'Box Selection Down', [KM.Shift | KM.Alt | KC.DownArrow], cmd('cursorColumnSelectDown'));
    A('colLeft', 'Box Selection Left', [KM.Shift | KM.Alt | KC.LeftArrow], cmd('cursorColumnSelectLeft'));
    A('colRight', 'Box Selection Right', [KM.Shift | KM.Alt | KC.RightArrow], cmd('cursorColumnSelectRight'));
    A('incSearch', 'Incremental Search', [KM.CtrlCmd | KC.KeyI], cmd('actions.find'));
  }

  function emacs(ed, list) {
    const A = (id, label, keys, run, when) => act(ed, list, 'radex.emacs.' + id, label, keys, run, when);
    const kill = (e, range, append) => {
      const m = e.getModel(), text = m.getValueInRange(range);
      radex.killRing = (append && radex._lastKill === e.getModel().getAlternativeVersionId()) ? (radex.killRing || '') + text : text;
      e.executeEdits('emacs', [{ range: range, text: '' }]);
      radex._lastKill = e.getModel().getAlternativeVersionId();
      try { navigator.clipboard.writeText(radex.killRing); } catch (ex) { /* no clipboard permission */ }
    };
    const move = (plain) => e => {
      e.trigger('emacs', e._radexMark ? plain + 'Select' : plain, null);
    };
    A('fwd', 'Emacs: forward-char', [KM.CtrlCmd | KC.KeyF], move('cursorRight'));
    A('back', 'Emacs: backward-char', [KM.CtrlCmd | KC.KeyB], move('cursorLeft'));
    A('next', 'Emacs: next-line', [KM.CtrlCmd | KC.KeyN], move('cursorDown'), 'editorTextFocus && !suggestWidgetVisible');
    A('prev', 'Emacs: previous-line', [KM.CtrlCmd | KC.KeyP], move('cursorUp'), 'editorTextFocus && !suggestWidgetVisible');
    A('sugNext', 'Emacs: next suggestion', [KM.CtrlCmd | KC.KeyN], cmd('selectNextSuggestion'), 'suggestWidgetVisible');
    A('sugPrev', 'Emacs: previous suggestion', [KM.CtrlCmd | KC.KeyP], cmd('selectPrevSuggestion'), 'suggestWidgetVisible');
    A('bol', 'Emacs: move-beginning-of-line', [KM.CtrlCmd | KC.KeyA], move('cursorLineStart'));
    A('eol', 'Emacs: move-end-of-line', [KM.CtrlCmd | KC.KeyE], move('cursorLineEnd'));
    A('fwdWord', 'Emacs: forward-word', [KM.Alt | KC.KeyF], move('cursorWordEndRight'));
    A('backWord', 'Emacs: backward-word', [KM.Alt | KC.KeyB], move('cursorWordStartLeft'));
    A('pgDown', 'Emacs: scroll-up-command', [KM.CtrlCmd | KC.KeyV], move('cursorPageDown'));
    A('pgUp', 'Emacs: scroll-down-command', [KM.Alt | KC.KeyV], move('cursorPageUp'));
    A('top', 'Emacs: beginning-of-buffer', [KM.Alt | KM.Shift | KC.Comma], move('cursorTop'));
    A('bottom', 'Emacs: end-of-buffer', [KM.Alt | KM.Shift | KC.Period], move('cursorBottom'));
    A('delChar', 'Emacs: delete-char', [KM.CtrlCmd | KC.KeyD], cmd('deleteRight'));
    A('delWord', 'Emacs: kill-word', [KM.Alt | KC.KeyD], cmd('deleteWordRight'));
    A('delWordBack', 'Emacs: backward-kill-word', [KM.Alt | KC.Backspace], cmd('deleteWordLeft'));
    A('killLine', 'Emacs: kill-line', [KM.CtrlCmd | KC.KeyK], e => {
      const p = e.getPosition(), m = e.getModel(), end = m.getLineMaxColumn(p.lineNumber);
      const r = p.column >= end ? (p.lineNumber < m.getLineCount() ? new monaco.Range(p.lineNumber, p.column, p.lineNumber + 1, 1) : null)
                                : new monaco.Range(p.lineNumber, p.column, p.lineNumber, end);
      if (r) kill(e, r, true);
    });
    A('killRegion', 'Emacs: kill-region', [KM.CtrlCmd | KC.KeyW], e => {
      const s = e.getSelection(); if (s && !s.isEmpty()) kill(e, s, false); e._radexMark = false; });
    A('copyRegion', 'Emacs: kill-ring-save', [KM.Alt | KC.KeyW], e => {
      const s = e.getSelection();
      if (s && !s.isEmpty()) { radex.killRing = e.getModel().getValueInRange(s);
        try { navigator.clipboard.writeText(radex.killRing); } catch (ex) { /* no clipboard permission */ } }
      e._radexMark = false; const p = e.getPosition(); e.setSelection(new monaco.Range(p.lineNumber, p.column, p.lineNumber, p.column)); });
    A('yank', 'Emacs: yank', [KM.CtrlCmd | KC.KeyY], e => {
      if (!radex.killRing) return;
      e.pushUndoStop(); e.executeEdits('emacs', e.getSelections().map(s => ({ range: s, text: radex.killRing, forceMoveMarkers: true }))); e.pushUndoStop(); });
    A('mark', 'Emacs: set-mark-command', [KM.CtrlCmd | KC.Space], e => {
      e._radexMark = !e._radexMark; const p = e.getPosition();
      e.setSelection(new monaco.Range(p.lineNumber, p.column, p.lineNumber, p.column)); });
    A('quit', 'Emacs: keyboard-quit', [KM.CtrlCmd | KC.KeyG], e => {
      e._radexMark = false; const p = e.getPosition();
      e.setSelection(new monaco.Range(p.lineNumber, p.column, p.lineNumber, p.column));
      ['closeFindWidget', 'hideSuggestWidget', 'closeParameterHints', 'removeSecondaryCursors'].forEach(c => e.trigger('emacs', c, null)); });
    A('undo', 'Emacs: undo', [KM.CtrlCmd | KC.Slash, KChord(KM.CtrlCmd | KC.KeyX, KC.KeyU), KM.CtrlCmd | KM.Shift | KC.Minus], cmd('undo'));
    A('save', 'Emacs: save-buffer', [KChord(KM.CtrlCmd | KC.KeyX, KM.CtrlCmd | KC.KeyS)], () => host && host.jsCommand('save'));
    A('kill', 'Emacs: kill-buffer', [KChord(KM.CtrlCmd | KC.KeyX, KC.KeyK)], () => host && host.jsCommand('close'));
    A('selAll', 'Emacs: mark-whole-buffer', [KChord(KM.CtrlCmd | KC.KeyX, KC.KeyH)], cmd('editor.action.selectAll'));
    A('split2', 'Emacs: split-window-below', [KChord(KM.CtrlCmd | KC.KeyX, KC.Digit2)], () => radex.setSplit('down'));
    A('split3', 'Emacs: split-window-right', [KChord(KM.CtrlCmd | KC.KeyX, KC.Digit3)], () => radex.setSplit('right'));
    A('split1', 'Emacs: delete-other-windows', [KChord(KM.CtrlCmd | KC.KeyX, KC.Digit1)], () => radex.setSplit('none'));
    A('other', 'Emacs: other-window', [KChord(KM.CtrlCmd | KC.KeyX, KC.KeyO)], e => {
      const i = radex.editors.indexOf(e); radex.editors[(i + 1) % radex.editors.length].focus(); });
    A('isearch', 'Emacs: isearch-forward', [KM.CtrlCmd | KC.KeyS], cmd('actions.find'));
    A('isearchBack', 'Emacs: isearch-backward', [KM.CtrlCmd | KC.KeyR], cmd('actions.find'));
    A('replace', 'Emacs: query-replace', [KM.Alt | KM.Shift | KC.Digit5], cmd('editor.action.startFindReplaceAction'));
    A('mx', 'Emacs: execute-extended-command', [KM.Alt | KC.KeyX], cmd('editor.action.quickCommand'));
    A('gotoLine', 'Emacs: goto-line', [KChord(KM.Alt | KC.KeyG, KC.KeyG), KChord(KM.Alt | KC.KeyG, KM.Alt | KC.KeyG)], cmd('editor.action.gotoLine'));
    A('recenter', 'Emacs: recenter', [KM.CtrlCmd | KC.KeyL], e => e.revealLineInCenter(e.getPosition().lineNumber));
    A('openLine', 'Emacs: open-line', [KM.CtrlCmd | KC.KeyO], e => {
      const p = e.getPosition(); e.executeEdits('emacs', [{ range: new monaco.Range(p.lineNumber, p.column, p.lineNumber, p.column), text: '\n' }]);
      e.setPosition(p); });
    A('transpose', 'Emacs: transpose-chars', [KM.CtrlCmd | KC.KeyT], cmd('editor.action.transposeLetters'));
    A('upWord', 'Emacs: upcase-word', [KM.Alt | KC.KeyU], cmd('editor.action.transformToUppercase'));
    A('downWord', 'Emacs: downcase-word', [KM.Alt | KC.KeyL], cmd('editor.action.transformToLowercase'));
    A('comment', 'Emacs: comment-dwim', [KM.Alt | KC.Semicolon], cmd('editor.action.commentLine'));
  }

  function applyKeymap(ed, statusNode) {
    disposeKeymap(ed);
    const list = [];
    kmDisp.set(ed, list);
    const name = radex.keymap;
    if (name !== 'vim') multiCursor(ed, list);
    if (name === 'vs') visualStudio(ed, list);
    else if (name === 'emacs') emacs(ed, list);
    else if (name === 'vim') {
      loadVim().then(MV => {
        if (radex.keymap !== 'vim' || kmDisp.get(ed) !== list) return;      // switched away meanwhile
        const vm = MV.initVimMode(ed, statusNode);
        list.push({ dispose: () => vm.dispose() });
        radex.vimReady = true;
      }).catch(e => console.error('monaco-vim failed to load: ' + e));
    }
  }
  /** name: 'vs' | 'vscode' | 'vim' | 'emacs' */
  radex.setKeymap = function (name) {
    radex.keymap = ['vs', 'vscode', 'vim', 'emacs'].indexOf(name) >= 0 ? name : 'vscode';
    document.body.classList.toggle('radex-vim', radex.keymap === 'vim');
    radex.vimReady = false;
    applyKeymap(editor, status1);
    if (radex.editor2) applyKeymap(radex.editor2, status2);
    return radex.keymap;
  };
  radex.vimStatus = () => (status1.textContent || '').trim();

  // ------------------------------------------------------------------ init from Python
  radex.init = function (cfg) {
    cfg = cfg || {};
    if (cfg.snippets) radex.setSnippets(cfg.snippets);
    radex.setKeymap(cfg.keymap || 'vscode');
    if (cfg.split && cfg.split !== 'none') radex.setSplit(cfg.split);
    return true;
  };
  (window.__radexQ || []).splice(0).forEach(fn => { try { fn(); } catch (e) { console.error('radex queued call: ' + e); } });
})();
