// RAD IDE - declarative VS Code contributions inside a Monaco page (editor.html).
// Python side: radide/vsx/contrib_runtime.py (channel object "vsxc") + contrib_languages / contrib_themes.
//
//   vsxInit(spec)        languages + language configurations, TextMate grammars (vscode-textmate +
//                        vscode-oniguruma, bundled here, MIT), snippets, keybindings, the current theme
//   vsxSetTheme(theme)   the VS Code colour theme behind the IDE theme (null = a built-in IDE theme)
//
// Tokens: vscode-textmate tokenises with the active theme (Registry.setTheme) and returns, per token, a
// foreground colour id + font style + standard token type. They reach Monaco as token names
// "tm<fg>[_<fontStyle>][.comment|.string|.regexp]" and the Monaco theme gets one rule per colour/style.
(function () {
  'use strict';
  const S = {
    spec: null, theme: null, requested: 'vs', builtinRaw: {}, tm: null, tmLoading: null, grammars: new Map(),
    providers: new Map(), tmLangs: new Set(), langNums: new Map(), disposables: [], snippetCache: new Map(),
    builtinLangs: null, keyDisposables: [], defined: new Set(), lastName: '',
  };
  window.vsxState = S;
  const log = (...a) => console.log('[vsx] ' + a.join(' '));
  const err = (...a) => console.error('[vsx] ' + a.join(' '));

  function channel() { return window.radChannel && window.radChannel.objects && window.radChannel.objects.vsxc; }
  function call(method, ...args) {
    return new Promise(res => {
      const ch = channel();
      if (!ch || typeof ch[method] !== 'function') { res(''); return; }
      ch[method](...args, r => res(r));
    });
  }

  // ------------------------------------------------------------------ language configuration
  function rx(v) {
    try {
      if (!v) return undefined;
      if (typeof v === 'string') return new RegExp(v);
      if (typeof v === 'object' && typeof v.pattern === 'string') return new RegExp(v.pattern, (v.flags || '').replace(/[^gimsuy]/g, ''));
    } catch (e) { /* VS Code (Oniguruma-ish) patterns JavaScript cannot parse are dropped */ }
    return undefined;
  }
  function pairs(list) {
    if (!Array.isArray(list)) return undefined;
    return list.map(p => Array.isArray(p) ? { open: p[0], close: p[1] } :
      (p && typeof p === 'object' ? { open: p.open, close: p.close, notIn: p.notIn } : null)).filter(p => p && p.open);
  }
  const INDENT = { none: 0, indent: 1, indentoutdent: 2, outdent: 3 };
  function convertConfig(c) {
    if (!c || typeof c !== 'object') return null;
    const out = {};
    if (c.comments) {
      out.comments = {};
      if (typeof c.comments.lineComment === 'string') out.comments.lineComment = c.comments.lineComment;
      else if (c.comments.lineComment && c.comments.lineComment.comment) out.comments.lineComment = c.comments.lineComment.comment;
      if (Array.isArray(c.comments.blockComment)) out.comments.blockComment = c.comments.blockComment;
    }
    if (Array.isArray(c.brackets)) out.brackets = c.brackets.filter(b => Array.isArray(b) && b.length === 2);
    if (Array.isArray(c.colorizedBracketPairs)) out.colorizedBracketPairs = c.colorizedBracketPairs;
    const acp = pairs(c.autoClosingPairs); if (acp) out.autoClosingPairs = acp;
    const sp = pairs(c.surroundingPairs); if (sp) out.surroundingPairs = sp;
    if (typeof c.autoCloseBefore === 'string') out.autoCloseBefore = c.autoCloseBefore;
    const wp = rx(c.wordPattern); if (wp) out.wordPattern = wp;
    if (c.folding) {
      out.folding = { offSide: !!c.folding.offSide };
      if (c.folding.markers) {
        const s = rx(c.folding.markers.start), e = rx(c.folding.markers.end);
        if (s && e) out.folding.markers = { start: s, end: e };
      }
    }
    if (c.indentationRules) {
      const r = c.indentationRules, inc = rx(r.increaseIndentPattern), dec = rx(r.decreaseIndentPattern);
      if (inc && dec) {
        out.indentationRules = { increaseIndentPattern: inc, decreaseIndentPattern: dec };
        const n = rx(r.indentNextLinePattern), u = rx(r.unIndentedLinePattern);
        if (n) out.indentationRules.indentNextLinePattern = n;
        if (u) out.indentationRules.unIndentedLinePattern = u;
      }
    }
    if (Array.isArray(c.onEnterRules)) {
      out.onEnterRules = c.onEnterRules.map(r => {
        const before = rx(r.beforeText); if (!before || !r.action) return null;
        const a = r.action, act = { indentAction: INDENT[String(a.indent || a.indentAction || 'none').toLowerCase()] || 0 };
        if (typeof a.appendText === 'string') act.appendText = a.appendText;
        if (typeof a.removeText === 'number') act.removeText = a.removeText;
        const rule = { beforeText: before, action: act };
        const after = rx(r.afterText), prev = rx(r.previousLineText);
        if (after) rule.afterText = after;
        if (prev) rule.previousLineText = prev;
        return rule;
      }).filter(Boolean);
    }
    return out;
  }

  // ------------------------------------------------------------------ TextMate machinery
  function loadTextMate() {
    if (S.tm) return Promise.resolve(S.tm);
    if (S.tmLoading) return S.tmLoading;
    S.tmLoading = new Promise((resolve, reject) => {
      require.config({ paths: { 'vscode-textmate': 'vsx/vscode-textmate/main', 'vscode-oniguruma': 'vsx/vscode-oniguruma/main' } });
      require(['vscode-oniguruma', 'vscode-textmate'], (onig, vsctm) => {
        wasmBytes().then(buf => onig.loadWASM(buf)).then(() => {
          const onigLib = Promise.resolve({
            createOnigScanner: p => new onig.OnigScanner(p), createOnigString: s => new onig.OnigString(s) });
          const registry = new vsctm.Registry({
            onigLib: onigLib,
            loadGrammar: async scope => {
              const txt = await call('grammar', scope);
              if (!txt) return null;
              try { const g = JSON.parse(txt); return vsctm.parseRawGrammar(g.content, g.path); }
              catch (e) { err('grammar ' + scope + ': ' + e); return null; }
            },
            getInjections: scope => (S.spec && S.spec.injections && S.spec.injections[scope]) || undefined,
          });
          S.tm = { vsctm: vsctm, onig: onig, registry: registry };
          applyRawTheme();
          resolve(S.tm);
        }).catch(e => { err('oniguruma: ' + e); reject(e); });
      }, e => { err('textmate modules: ' + e); reject(e); });
    });
    return S.tmLoading;
  }
  function wasmBytes() {
    return new Promise((res, rej) => {
      const x = new XMLHttpRequest();
      x.open('GET', new URL('vsx/vscode-oniguruma/onig.wasm', location.href).href, true);
      x.responseType = 'arraybuffer';
      x.onload = () => (x.response && x.response.byteLength) ? res(x.response) : rej(new Error('onig.wasm: empty (' + x.status + ')'));
      x.onerror = () => rej(new Error('onig.wasm: cannot read'));
      x.send();
    });
  }

  class TmState {
    constructor(stack) { this.stack = stack; }
    clone() { return new TmState(this.stack); }
    equals(o) { return o instanceof TmState && (o.stack === this.stack || (this.stack && this.stack.equals(o.stack))); }
  }
  const TYPE_SUFFIX = ['', '.comment', '.string', '.regexp'];
  function makeProvider(grammar) {
    const INITIAL = S.tm.vsctm.INITIAL;
    return {
      getInitialState: () => new TmState(INITIAL),
      tokenize: (line, state) => {
        if (line.length > 20000) return { tokens: [{ startIndex: 0, scopes: '' }], endState: state };
        const r = grammar.tokenizeLine2(line, state.stack, 500);
        const t = r.tokens, tokens = [];
        for (let i = 0; i < t.length; i += 2) {
          const m = t[i + 1];
          const fg = (m & 16744448) >>> 15, fs = (m & 30720) >>> 11, type = (m & 768) >>> 8;
          tokens.push({ startIndex: t[i], scopes: 'tm' + fg + (fs ? '_' + fs : '') + TYPE_SUFFIX[type] });
        }
        return { tokens: tokens, endState: new TmState(r.ruleStack) };
      },
    };
  }
  function langNumber(id) {
    if (!S.langNums.has(id)) S.langNums.set(id, S.langNums.size + 1);
    return S.langNums.get(id);
  }
  // Load the grammar of an IDE language and make it the language's tokenizer.
  function ensureGrammar(langId) {
    if (!S.spec || !S.tmLangs.has(langId)) return Promise.resolve(false);
    if (S.grammars.has(langId)) return S.grammars.get(langId);
    const L = S.spec.languages.find(l => l.id === langId || (l.monaco === langId && l.scope));
    if (!L || !L.scope) return Promise.resolve(false);
    const p = loadTextMate().then(tm => {
      const embedded = {};
      Object.keys(L.embedded || {}).forEach(sc => { embedded[sc] = langNumber(L.embedded[sc]); });
      const tokenTypes = {};
      const TT = { other: 0, comment: 1, string: 2, regex: 3 };
      Object.keys(L.tokenTypes || {}).forEach(sc => { tokenTypes[sc] = TT[L.tokenTypes[sc]] || 0; });
      return tm.registry.loadGrammarWithConfiguration(L.scope, langNumber(langId),
        { embeddedLanguages: embedded, tokenTypes: tokenTypes,
          balancedBracketSelectors: L.balanced && L.balanced.length ? L.balanced : ['*'],
          unbalancedBracketSelectors: L.unbalanced || [] });
    }).then(grammar => {
      if (!grammar) { err('no grammar for ' + langId); return false; }
      setProvider(langId, grammar);
      return true;
    }).catch(e => { err('grammar ' + langId + ': ' + e); return false; });
    S.grammars.set(langId, p);
    return p;
  }
  function setProvider(langId, grammar) {
    const old = S.providers.get(langId);
    if (old && old.disp) old.disp.dispose();
    const disp = origSetTokens(langId, makeProvider(grammar));
    S.providers.set(langId, { grammar: grammar, disp: disp });
    window.vsxTokenizedBy = window.vsxTokenizedBy || {};
    window.vsxTokenizedBy[langId] = 'textmate';
  }
  // the colour ids of the tokens depend on the theme: re-register every provider -> Monaco re-tokenises
  function retokenize() {
    S.providers.forEach((p, langId) => setProvider(langId, p.grammar));
  }

  // Monarch must not replace a TextMate tokenizer (Monaco's built-in languages register theirs lazily)
  let origSetTokens = null;
  function hookMonaco() {
    if (origSetTokens) return;
    origSetTokens = monaco.languages.setTokensProvider.bind(monaco.languages);
    const origSetMonarch = monaco.languages.setMonarchTokensProvider.bind(monaco.languages);
    monaco.languages.setMonarchTokensProvider = function (langId, def) {
      if (S.tmLangs.has(langId) && S.providers.has(langId)) return { dispose() {} };
      return origSetMonarch(langId, def);
    };
  }

  // ------------------------------------------------------------------ themes
  function baseOf(t) { return (t === true) ? 'vs-dark' : (t === false || !t) ? 'vs' : String(t); }
  function activeTheme() {
    const t = S.theme;
    if (t && (S.requested === t.base || S.requested === 'vsx')) return t;
    return null;
  }
  function applyRawTheme() {
    const t = activeTheme();
    const raw = t ? t.raw : S.builtinRaw[S.requested] || S.builtinRaw['vs'];
    if (S.tm && raw) {
      try { S.tm.registry.setTheme(raw); } catch (e) { err('setTheme: ' + e); }
    }
  }
  function tmRules(bg) {
    if (!S.tm) return [];
    const cm = S.tm.registry.getColorMap() || [], rules = [];
    const STYLES = ['', 'italic', 'bold', 'italic bold', 'underline', 'italic underline', 'bold underline',
                    'italic bold underline'];
    for (let i = 1; i < cm.length; i++) {
      if (!cm[i]) continue;
      const c = String(cm[i]).replace('#', '').substring(0, 6);
      rules.push({ token: 'tm' + i, foreground: c });
      for (let fs = 1; fs < 16; fs++) {
        let style = STYLES[fs & 7] || '';
        if (fs & 8) style = (style + ' strikethrough').trim();
        rules.push({ token: 'tm' + i + '_' + fs, foreground: c, fontStyle: style });
      }
    }
    return rules;
  }
  function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); }
  // Define + set the Monaco theme for the current state (vsx theme or built-in base, plus TextMate rules).
  function applyTheme() {
    const t = activeTheme();
    applyRawTheme();
    const useTm = !!S.tm && S.providers.size > 0;
    if (!t && !useTm) {
      if (S.lastName && S.lastName !== S.requested) { monaco.editor.setTheme(S.requested); S.lastName = S.requested; }
      return S.requested;
    }
    const data = t ? JSON.parse(JSON.stringify(t.monaco)) : { base: S.requested, inherit: true, rules: [], colors: {} };
    if (useTm) data.rules = (data.rules || []).concat(tmRules());
    const name = (t ? 'vsx-' + hash(t.id) : S.requested + '-tm') + (useTm ? '-' + (S.tm.registry.getColorMap() || []).length : '');
    try {
      monaco.editor.defineTheme(name, data);
      monaco.editor.setTheme(name);
      S.lastName = name;
    } catch (e) { err('theme: ' + e); monaco.editor.setTheme(S.requested); S.lastName = S.requested; }
    if (t && t.background) document.body.style.background = t.background;
    if (useTm) retokenize();
    return name;
  }
  window.vsxSetTheme = function (theme) {
    S.theme = theme || null;
    if (S.theme && S.requested !== S.theme.base) S.requested = S.theme.base;
    return applyTheme();
  };
  window.vsxThemeName = () => S.lastName;

  function wrapSetTheme() {
    if (window.radSetTheme && window.radSetTheme._vsx) return;
    const prev = window.radSetTheme;
    const wrapped = function (t) {
      S.requested = baseOf(t);
      if (prev) prev(t);                    // editor.html + editor_extras.js (chrome colours)
      applyTheme();
    };
    wrapped._vsx = true;
    window.radSetTheme = wrapped;
  }
  function wrapSetLanguage() {
    if (!window.radSetLanguage || window.radSetLanguage._vsx) return;
    const prev = window.radSetLanguage;
    const wrapped = function (lang) {
      prev(lang);
      if (lang && S.tmLangs.has(lang)) ensureGrammar(lang).then(ok => { if (ok) applyTheme(); });
    };
    wrapped._vsx = true;
    window.radSetLanguage = wrapped;
  }

  // ------------------------------------------------------------------ snippets
  function registerSnippets(langs) {
    langs.forEach(lang => {
      S.disposables.push(monaco.languages.registerCompletionItemProvider(lang, {
        provideCompletionItems: async (model, pos) => {
          let items = S.snippetCache.get(lang);
          if (!items) {
            const txt = await call('snippets', lang);
            try { items = JSON.parse(txt || '[]'); } catch (e) { items = []; }
            S.snippetCache.set(lang, items);
          }
          const w = model.getWordUntilPosition(pos);
          const line = model.getLineContent(pos.lineNumber).substring(0, pos.column - 1);
          return { suggestions: items.map(s => {
            // prefixes with non-word characters ("!", "#region", "log.") replace what was typed of them
            let start = w.startColumn;
            for (let n = Math.min(s.prefix.length, line.length); n > 0; n--) {
              if (s.prefix.substring(0, n) === line.substring(line.length - n) && pos.column - n < start) { start = pos.column - n; break; }
            }
            return { label: { label: s.prefix, description: s.name }, kind: monaco.languages.CompletionItemKind.Snippet,
              detail: s.description, documentation: { value: '```\n' + s.body + '\n```' }, insertText: s.body,
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet, filterText: s.prefix,
              range: new monaco.Range(pos.lineNumber, start, pos.lineNumber, pos.column), sortText: '~' + s.prefix };
          }) };
        } }));
    });
  }
  window.vsxSnippets = async lang => {        // tests: the snippet items of a language
    const txt = await call('snippets', lang);
    try { return JSON.parse(txt || '[]'); } catch (e) { return []; }
  };
  window.vsxInsertSnippet = function (prefix) {
    const ed = window.radEditor, lang = ed.getModel().getLanguageId();
    return window.vsxSnippets(lang).then(items => {
      const s = items.find(i => i.prefix === prefix);
      if (!s) return false;
      ed.focus();
      ed.getContribution('snippetController2').insert(s.body);
      return true;
    });
  };

  // ------------------------------------------------------------------ keybindings
  const KC = () => monaco.KeyCode;
  function keyCode(k) {
    const c = KC();
    k = k.toLowerCase();
    if (/^[a-z]$/.test(k)) return c['Key' + k.toUpperCase()];
    if (/^[0-9]$/.test(k)) return c['Digit' + k];
    if (/^f([1-9]|1[0-9])$/.test(k)) return c['F' + k.substring(1)];
    if (/^numpad[0-9]$/.test(k)) return c['Numpad' + k.substring(6)];
    const M = { enter: 'Enter', escape: 'Escape', esc: 'Escape', tab: 'Tab', space: 'Space', backspace: 'Backspace',
      delete: 'Delete', insert: 'Insert', home: 'Home', end: 'End', pageup: 'PageUp', pagedown: 'PageDown',
      up: 'UpArrow', down: 'DownArrow', left: 'LeftArrow', right: 'RightArrow', ';': 'Semicolon', '=': 'Equal',
      ',': 'Comma', '-': 'Minus', '.': 'Period', '/': 'Slash', '`': 'Backquote', '[': 'BracketLeft',
      '\\': 'Backslash', ']': 'BracketRight', "'": 'Quote', numpad_add: 'NumpadAdd', numpad_subtract: 'NumpadSubtract',
      numpad_multiply: 'NumpadMultiply', numpad_divide: 'NumpadDivide', numpad_decimal: 'NumpadDecimal',
      pausebreak: 'PauseBreak', capslock: 'CapsLock', contextmenu: 'ContextMenu' };
    return M[k] !== undefined ? c[M[k]] : undefined;
  }
  function parseChord(part) {
    let mods = 0, code;
    const keys = part.split('+');
    // "ctrl++" -> the key is "+": handled as Equal with shift by VS Code; keep it simple
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i].trim().toLowerCase();
      if (!k) continue;
      if (k === 'ctrl' || k === 'cmd') mods |= monaco.KeyMod.CtrlCmd;
      else if (k === 'shift') mods |= monaco.KeyMod.Shift;
      else if (k === 'alt') mods |= monaco.KeyMod.Alt;
      else if (k === 'meta' || k === 'win') mods |= monaco.KeyMod.WinCtrl;
      else code = keyCode(k);
    }
    return code === undefined ? null : (mods | code);
  }
  function parseKey(key) {
    const parts = String(key || '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length || parts.length > 2) return null;
    const a = parseChord(parts[0]); if (a === null) return null;
    if (parts.length === 1) return a;
    const b = parseChord(parts[1]); if (b === null) return null;
    return monaco.KeyMod.chord(a, b);
  }
  window.vsxParseKey = parseKey;
  function registerKeybindings(list) {
    S.keyDisposables.forEach(d => { try { d.dispose(); } catch (e) { /* ignore */ } });
    S.keyDisposables = [];
    S.keyActions = new Map();
    const ed = window.radEditor;
    if (!ed || !Array.isArray(list)) return 0;
    let n = 0;
    list.forEach(kb => {
      const code = parseKey(kb.key);
      if (code === null) return;
      const run = () => {
        if (kb.target === 'monaco') ed.trigger('vsx', kb.command, kb.args === undefined ? null : kb.args);
        else { const ch = channel(); if (ch && ch.runCommand) ch.runCommand(kb.command, JSON.stringify(kb.args === undefined ? null : kb.args)); }
      };
      try {
        // the when clause is a Monaco context key expression (editorTextFocus, editorLangId == x ...)
        const id = 'vsx.kb.' + (n++) + '.' + kb.command;
        S.keyDisposables.push(ed.addAction({ id: id, label: kb.title || kb.command, keybindings: [code],
          precondition: kb.when || undefined, run: run }));
        S.keyActions.set(kb.key, id);
      } catch (e) { err('keybinding ' + kb.key + ': ' + e); }
    });
    return n;
  }
  window.vsxRunKeybinding = function (key) {   // tests: run the binding of a key string
    const id = S.keyActions && S.keyActions.get(key);
    const action = id && window.radEditor.getAction(id);
    if (!action) return false;
    action.run();
    return true;
  };

  // ------------------------------------------------------------------ init
  window.vsxInit = function (spec) {
    hookMonaco();
    if (!S.builtinLangs) S.builtinLangs = new Set(monaco.languages.getLanguages().map(l => l.id));
    S.disposables.forEach(d => { try { d.dispose(); } catch (e) { /* ignore */ } });
    S.disposables = [];
    S.snippetCache.clear();
    const oldScopes = S.spec ? JSON.stringify(S.spec.languages.map(l => [l.id, l.scope])) : '';
    S.spec = spec || { languages: [] };
    S.builtinRaw = spec.builtinRaw || S.builtinRaw;
    if (oldScopes && oldScopes !== JSON.stringify(S.spec.languages.map(l => [l.id, l.scope]))) {
      S.grammars.clear();                     // grammars changed (install / uninstall): a new registry
      S.tm = null;
      S.tmLoading = null;
    }
    const known = new Set(monaco.languages.getLanguages().map(l => l.id));
    const tmLangs = new Set();
    (S.spec.languages || []).forEach(L => {
      const ids = [L.id];
      if (L.monaco && L.monaco !== L.id) ids.push(L.monaco);
      ids.forEach(id => {
        if (!known.has(id)) {
          const def = { id: id, extensions: L.extensions || [], aliases: L.aliases || [], filenames: L.filenames || [],
                        mimetypes: L.mimetypes || [] };
          if (L.firstLine) def.firstLine = L.firstLine;
          monaco.languages.register(def);
          known.add(id);
        }
        if (L.configuration && !S.builtinLangs.has(id)) {
          const conf = convertConfig(L.configuration);
          if (conf) { try { S.disposables.push(monaco.languages.setLanguageConfiguration(id, conf)); } catch (e) { err('config ' + id + ': ' + e); } }
        }
        if (L.scope) tmLangs.add(id);
      });
    });
    // languages that lost their grammar go back to Monarch / plain text
    S.providers.forEach((p, id) => { if (!tmLangs.has(id)) { p.disp.dispose(); S.providers.delete(id); } });
    S.tmLangs = tmLangs;
    registerSnippets(S.spec.snippetLanguages || []);
    wrapSetTheme();
    wrapSetLanguage();
    if (spec.theme !== undefined) S.theme = spec.theme;
    if (spec.requested) S.requested = baseOf(spec.requested);
    else if (S.theme) S.requested = S.theme.base;
    registerKeybindings(S.spec.keybindings || []);
    // lazily load grammars when a model of the language appears
    tmLangs.forEach(id => {
      S.disposables.push(monaco.languages.onLanguage(id, () => ensureGrammar(id).then(ok => { if (ok) applyTheme(); })));
    });
    const model = window.radEditor && window.radEditor.getModel();
    const cur = model ? model.getLanguageId() : '';
    applyTheme();
    if (cur && tmLangs.has(cur)) return ensureGrammar(cur).then(ok => { if (ok) applyTheme(); return ok; });
    return Promise.resolve(false);
  };

  // tests / diagnostics: the TextMate tokens of a line of the current model
  window.vsxTokens = function (lineNumber) {
    const ed = window.radEditor, model = ed.getModel();
    const p = S.providers.get(model.getLanguageId());
    if (!p) return null;
    let state = new TmState(S.tm.vsctm.INITIAL);
    let r = null;
    for (let i = 1; i <= lineNumber; i++) {
      r = p.grammar.tokenizeLine(model.getLineContent(i), state.stack);
      state = new TmState(r.ruleStack);
    }
    return r.tokens.map(t => ({ start: t.startIndex, end: t.endIndex, scopes: t.scopes }));
  };
  window.vsxInfo = () => ({ tmLangs: Array.from(S.tmLangs), providers: Array.from(S.providers.keys()),
    theme: S.lastName, requested: S.requested, vsxTheme: S.theme ? S.theme.id : null, textmate: !!S.tm });
  log('ready');
})();
