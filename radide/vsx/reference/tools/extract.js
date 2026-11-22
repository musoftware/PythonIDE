'use strict';
// Extracts machine-readable inventories from a microsoft/vscode checkout (TypeScript AST, no type check).
//   node extract.js <vscode checkout> <dts dir with vscode-<ver>.d.ts> <out dir>
const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const [, , ROOT, DTS_DIR, OUT] = process.argv;
const SRC = path.join(ROOT, 'src');
fs.mkdirSync(OUT, { recursive: true });

function walk(dir, out) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== 'test' && e.name !== 'node_modules') walk(p, out); } else if (e.name.endsWith('.ts') && !e.name.endsWith('.d.ts')) out.push(p);
  }
  return out;
}
const rel = (f) => path.relative(ROOT, f).replace(/\\/g, '/');
const files = walk(path.join(SRC, 'vs'), []);
console.error('files', files.length);

// ---------------------------------------------------------------- pass 1: string constants
// NAME -> value (top-level / namespace consts), Class.STATIC -> value, Namespace.NAME -> value
const consts = new Map();
const objConsts = new Map();
const fileConsts = new Map();     // file -> Map(name -> value)
const fileImports = new Map();    // file -> Map(localName -> {file, name}) | Map(nsName -> {file, ns: true})
const fkey = (f) => path.resolve(f).toLowerCase();
function setFC(f, k, v) { f = fkey(f); let m = fileConsts.get(f); if (!m) fileConsts.set(f, m = new Map()); m.set(k, v); }
function resolveImport(from, spec) {
  if (!spec.startsWith('.')) return null;
  return path.resolve(path.dirname(from), spec.replace(/\.js$/, '.ts'));
}
const parsed = [];
function strOf(node) {
  if (!node) return undefined;
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
  return undefined;
}
for (const f of files) {
  const text = fs.readFileSync(f, 'utf8');
  const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true);
  parsed.push(sf);
  const visit = (node, scope) => {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name)) {
      const v = strOf(node.initializer);
      if (v !== undefined) {
        consts.set(node.name.text, v); setFC(f, node.name.text, v);
        if (scope) { consts.set(scope + '.' + node.name.text, v); setFC(f, scope + '.' + node.name.text, v); }
      }
    } else if (ts.isPropertyDeclaration(node) && node.name && ts.isIdentifier(node.name)) {
      const v = strOf(node.initializer);
      const cls = node.parent && node.parent.name ? node.parent.name.text : null;
      if (v !== undefined && cls) { consts.set(cls + '.' + node.name.text, v); setFC(f, cls + '.' + node.name.text, v); }
    } else if (ts.isEnumMember(node) && ts.isIdentifier(node.name)) {
      const v = strOf(node.initializer);
      if (v !== undefined && node.parent.name) { consts.set(node.parent.name.text + '.' + node.name.text, v); setFC(f, node.parent.name.text + '.' + node.name.text, v); }
    } else if (ts.isImportDeclaration(node) && node.importClause && ts.isStringLiteral(node.moduleSpecifier)) {
      const target = resolveImport(f, node.moduleSpecifier.text);
      if (target) {
        let m = fileImports.get(fkey(f)); if (!m) fileImports.set(fkey(f), m = new Map());
        const nb = node.importClause.namedBindings;
        if (nb && ts.isNamespaceImport(nb)) m.set(nb.name.text, { file: target, ns: true });
        else if (nb && ts.isNamedImports(nb)) for (const el of nb.elements) m.set(el.name.text, { file: target, name: (el.propertyName || el.name).text });
      }
    }
    let s = scope;
    if ((ts.isModuleDeclaration(node) || ts.isClassDeclaration(node)) && node.name) s = node.name.text;
    ts.forEachChild(node, (c) => visit(c, s));
  };
  visit(sf, null);
}
console.error('consts', consts.size);

function resolve(node) {
  if (!node) return undefined;
  const s = strOf(node);
  if (s !== undefined) return s;
  const file = node.getSourceFile ? node.getSourceFile().fileName : null;
  const local = (f, k, depth = 0) => {
    const fc = fileConsts.get(fkey(f));
    if (fc && fc.has(k)) return fc.get(k);
    const im = fileImports.get(fkey(f));
    if (!im || depth > 4) return undefined;
    const head = k.split('.')[0];
    const imp = im.get(head);
    if (!imp) return undefined;
    if (imp.ns) return local(imp.file, k.split('.').slice(1).join('.'), depth + 1);
    return local(imp.file, [imp.name].concat(k.split('.').slice(1)).join('.'), depth + 1);
  };
  if (ts.isIdentifier(node)) { const v = file ? local(file, node.text) : undefined; return v !== undefined ? v : consts.get(node.text); }
  if (ts.isPropertyAccessExpression(node)) {
    const full = node.getText().replace(/\s+/g, '');
    const lv = file ? local(file, full) : undefined;
    if (lv !== undefined) return lv;
    if (consts.has(full)) return consts.get(full);
    const parts = full.split('.');
    return consts.get(parts.slice(-2).join('.'));
  }
  if (ts.isTemplateExpression(node)) {
    let out = node.head.text;
    for (const sp of node.templateSpans) { const v = resolve(sp.expression); if (v === undefined) return undefined; out += v + sp.literal.text; }
    return out;
  }
  if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    const a = resolve(node.left); const b = resolve(node.right);
    return a !== undefined && b !== undefined ? a + b : undefined;
  }
  if (ts.isParenthesizedExpression(node) || ts.isAsExpression(node)) return resolve(node.expression);
  return undefined;
}
// localize('k', "text") / localize2(...) / nls.localize(...) / { value, original } -> text
function textOf(node) {
  if (!node) return undefined;
  const s = resolve(node);
  if (s !== undefined) return s;
  if (ts.isCallExpression(node)) {
    const callee = node.expression.getText();
    if (/localize2?$/.test(callee) && node.arguments.length >= 2) return textOf(node.arguments[1]);
  }
  if (ts.isObjectLiteralExpression(node)) {
    const v = prop(node, 'value') || prop(node, 'original');
    if (v) return textOf(v);
  }
  return undefined;
}
function prop(obj, name) {
  if (!obj || !ts.isObjectLiteralExpression(obj)) return undefined;
  for (const p of obj.properties) {
    if (ts.isPropertyAssignment(p) && p.name && (p.name.text === name || (p.name.getText && p.name.getText() === name))) return p.initializer;
    if (ts.isShorthandPropertyAssignment(p) && p.name.text === name) return p.name;
  }
  return undefined;
}
const exprText = (n) => (n ? n.getText().replace(/\s+/g, ' ').slice(0, 400) : undefined);

// keybinding: { primary: KeyMod.CtrlCmd | KeyCode.KeyP, when, mac: {...} } -> "ctrl+p"
const KEYNAMES = { CtrlCmd: 'ctrl', Shift: 'shift', Alt: 'alt', WinCtrl: 'ctrl' };
function keyText(node) {
  if (!node) return undefined;
  const t = node.getText();
  if (/KeyChord\(/.test(t)) {
    const m = /KeyChord\(([^,]+),([^)]+)\)/.exec(t);
    return m ? keyText1(m[1]) + ' ' + keyText1(m[2]) : t;
  }
  return keyText1(t);
}
function keyText1(t) {
  const parts = t.split('|').map((s) => s.trim());
  const out = [];
  for (const p of parts) {
    let m;
    if ((m = /KeyMod\.(\w+)/.exec(p))) out.push(KEYNAMES[m[1]] || m[1].toLowerCase());
    else if ((m = /KeyCode\.(\w+)/.exec(p))) out.push(m[1].replace(/^Key|^Digit/, '').replace(/^Numpad/, 'numpad').toLowerCase());
    else if (p) out.push(p);
  }
  return out.join('+');
}
function keybindingInfo(kb) {
  if (!kb) return undefined;
  const list = ts.isArrayLiteralExpression(kb) ? kb.elements : [kb];
  const out = [];
  for (const k of list) {
    if (!ts.isObjectLiteralExpression(k)) continue;
    const e = {};
    const pr = prop(k, 'primary'); if (pr) e.key = keyText(pr);
    const w = prop(k, 'when'); if (w) e.when = whenText(w);
    const mac = prop(k, 'mac'); if (mac && prop(mac, 'primary')) e.mac = keyText(prop(mac, 'primary'));
    if (e.key || e.when) out.push(e);
  }
  return out.length ? out : undefined;
}
// ContextKeyExpr.and(EditorContextKeys.focus, ...) -> best effort when-clause text
function whenText(node) {
  if (!node) return undefined;
  const t = node.getText();
  if (ts.isCallExpression(node)) {
    const c = node.expression.getText();
    const args = node.arguments;
    if (/ContextKeyExpr\.and$/.test(c)) return args.map(whenText).filter(Boolean).map((x) => (/\|\|/.test(x) ? `(${x})` : x)).join(' && ');
    if (/ContextKeyExpr\.or$/.test(c)) return args.map(whenText).filter(Boolean).join(' || ');
    if (/ContextKeyExpr\.not$/.test(c)) return '!' + (resolve(args[0]) || exprText(args[0]));
    if (/ContextKeyExpr\.has$/.test(c)) return resolve(args[0]) || exprText(args[0]);
    if (/ContextKeyExpr\.(equals|notEquals|regex|in|notIn|greater|smaller)$/.test(c)) {
      const op = { equals: '==', notEquals: '!=', regex: '=~', in: 'in', notIn: 'not in', greater: '>', smaller: '<' }[c.split('.').pop()];
      const k = resolve(args[0]) || exprText(args[0]);
      const v = args[1] ? (resolve(args[1]) !== undefined ? `'${resolve(args[1])}'` : exprText(args[1])) : '';
      return `${k} ${op} ${v}`;
    }
    if (/\.(isEqualTo|notEqualsTo)$/.test(c)) {
      const k = rawKeyOf(node.expression.expression);
      const v = resolve(args[0]);
      return `${k} ${c.endsWith('isEqualTo') ? '==' : '!='} ${v !== undefined ? `'${v}'` : exprText(args[0])}`;
    }
    if (/\.negate$/.test(c)) { const inner = whenText(node.expression.expression); return inner ? `!(${inner})` : undefined; }
    if (/\.toNegated$/.test(c)) { const k = rawKeyOf(node.expression.expression); return k ? '!' + k : undefined; }
  }
  if (ts.isIdentifier(node) || ts.isPropertyAccessExpression(node)) { const k = rawKeyOf(node); if (k) return k; }
  return t.replace(/\s+/g, ' ').slice(0, 300);
}
// RawContextKey variable -> its key (filled in pass 2)
const rawKeyByVar = new Map();
function rawKeyOf(node) {
  if (!node) return undefined;
  const t = node.getText().replace(/\s+/g, '');
  if (rawKeyByVar.has(t)) return rawKeyByVar.get(t);
  const last2 = t.split('.').slice(-2).join('.');
  if (rawKeyByVar.has(last2)) return rawKeyByVar.get(last2);
  const last = t.split('.').pop();
  return rawKeyByVar.get(last);
}

// ---------------------------------------------------------------- pass 2a: RawContextKeys
const contextKeys = new Map();
for (const sf of parsed) {
  const visit = (node, scope) => {
    if (ts.isNewExpression(node) && /RawContextKey$/.test(node.expression.getText()) && node.arguments && node.arguments.length) {
      const key = resolve(node.arguments[0]);
      if (key) {
        const ta = node.typeArguments && node.typeArguments[0] ? node.typeArguments[0].getText() : undefined;
        const dflt = node.arguments[1] ? exprText(node.arguments[1]) : undefined;
        let desc; let type = ta;
        const meta = node.arguments[2];
        if (meta) {
          if (ts.isObjectLiteralExpression(meta)) { desc = textOf(prop(meta, 'description')); type = (prop(meta, 'type') && resolve(prop(meta, 'type'))) || type; } else if (meta.kind !== ts.SyntaxKind.TrueKeyword) desc = textOf(meta);
        }
        const hidden = meta && meta.kind === ts.SyntaxKind.TrueKeyword;
        const entry = contextKeys.get(key) || { key, type, default: dflt, description: desc, files: [] };
        if (!entry.description && desc) entry.description = desc;
        if (hidden) entry.internal = true;
        if (!entry.files.includes(rel(sf.fileName))) entry.files.push(rel(sf.fileName));
        contextKeys.set(key, entry);
        // variable name -> key
        let p = node.parent;
        if (p && (ts.isVariableDeclaration(p) || ts.isPropertyDeclaration(p) || ts.isPropertyAssignment(p)) && p.name) {
          const name = p.name.getText();
          rawKeyByVar.set(name, key);
          const owner = scope || (p.parent && p.parent.name ? p.parent.name.getText() : null);
          if (owner) rawKeyByVar.set(owner + '.' + name, key);
        }
      }
    }
    let s = scope;
    if ((ts.isModuleDeclaration(node) || ts.isClassDeclaration(node)) && node.name) s = node.name.text;
    ts.forEachChild(node, (c) => visit(c, s));
  };
  visit(sf, null);
}
// keys created directly: contextKeyService.createKey('key', ...) / setContext
for (const sf of parsed) {
  const visit = (node) => {
    if (ts.isCallExpression(node) && /\.createKey$/.test(node.expression.getText()) && node.arguments.length) {
      const key = resolve(node.arguments[0]);
      if (key && !contextKeys.has(key) && /^[\w.:-]+$/.test(key)) contextKeys.set(key, { key, default: exprText(node.arguments[1]), files: [rel(sf.fileName)], via: 'createKey' });
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
console.error('context keys', contextKeys.size);

// ---------------------------------------------------------------- pass 2b: commands
const commands = new Map();
function addCmd(id, info, sf) {
  if (!id || typeof id !== 'string' || !/^[\w$][\w.:\-/$]*$/.test(id)) return;
  const e = commands.get(id) || { id, sources: [], files: [] };
  for (const [k, v] of Object.entries(info)) {
    if (v === undefined || v === null || k === 'source') continue;
    if (e[k] === undefined) e[k] = v;
  }
  if (info.source && !e.sources.includes(info.source)) e.sources.push(info.source);
  const fr = rel(sf.fileName);
  if (!e.files.includes(fr)) e.files.push(fr);
  commands.set(id, e);
}
function descFromAction(obj) {
  // the descriptor object of registerAction2 / EditorAction / registerCommand({...})
  const info = {};
  info.title = textOf(prop(obj, 'title')) || textOf(prop(obj, 'label'));
  const cat = prop(obj, 'category'); if (cat) info.category = textOf(cat) || exprText(cat);
  const f1 = prop(obj, 'f1'); if (f1) info.f1 = f1.kind === ts.SyntaxKind.TrueKeyword;
  const pre = prop(obj, 'precondition'); if (pre) info.precondition = whenText(pre);
  const kb = keybindingInfo(prop(obj, 'keybinding')); if (kb) info.keybinding = kb;
  const meta = prop(obj, 'metadata');
  if (meta && ts.isObjectLiteralExpression(meta)) {
    info.description = textOf(prop(meta, 'description'));
    const args = prop(meta, 'args');
    if (args && ts.isArrayLiteralExpression(args)) {
      info.args = args.elements.filter(ts.isObjectLiteralExpression).map((a) => {
        const r = { name: textOf(prop(a, 'name')) || exprText(prop(a, 'name')) };
        const d = prop(a, 'description'); if (d) r.description = textOf(d) || exprText(d);
        const c = prop(a, 'constraint'); if (c) r.constraint = exprText(c);
        const isOpt = prop(a, 'isOptional'); if (isOpt) r.optional = isOpt.kind === ts.SyntaxKind.TrueKeyword;
        const sc = prop(a, 'schema'); if (sc) r.schema = literal(sc);
        return r;
      });
    }
    const ret = prop(meta, 'returns'); if (ret) info.returns = textOf(ret) || exprText(ret);
  }
  const menu = prop(obj, 'menu');
  if (menu) {
    const list = ts.isArrayLiteralExpression(menu) ? menu.elements : [menu];
    info.menus = list.filter(ts.isObjectLiteralExpression).map((m) => {
      const r = { id: exprText(prop(m, 'id')) };
      const w = prop(m, 'when'); if (w) r.when = whenText(w);
      const g = prop(m, 'group'); if (g) r.group = resolve(g) || exprText(g);
      return r;
    });
  }
  return info;
}
for (const sf of parsed) {
  const visit = (node) => {
    if (ts.isCallExpression(node)) {
      const callee = node.expression.getText();
      const a0 = node.arguments[0];
      // CommandsRegistry.registerCommand('id', handler) | registerCommand({ id, handler, metadata })
      if (/CommandsRegistry\.registerCommand$/.test(callee) && a0) {
        if (ts.isObjectLiteralExpression(a0)) addCmd(resolve(prop(a0, 'id')), { ...descFromAction(a0), source: 'CommandsRegistry' }, sf);
        else addCmd(resolve(a0), { source: 'CommandsRegistry' }, sf);
      } else if (/registerCommandAndKeybindingRule$/.test(callee) && a0 && ts.isObjectLiteralExpression(a0)) {
        const info = descFromAction(a0);
        const pr = prop(a0, 'primary'); const w = prop(a0, 'when');
        if (pr || w) info.keybinding = [{ key: pr ? keyText(pr) : undefined, when: w ? whenText(w) : undefined }];
        addCmd(resolve(prop(a0, 'id')), { ...info, source: 'KeybindingsRegistry' }, sf);
      } else if (/registerKeybindingRule$/.test(callee) && a0 && ts.isObjectLiteralExpression(a0)) {
        // a keybinding for an existing command (no new command)
      } else if (/registerAction2$/.test(callee) && a0) {
        // registerAction2(class extends Action2 { constructor() { super({ id ... }) } }) or registerAction2(SomeClass)
        let obj;
        const findSuper = (n) => {
          if (obj) return;
          if (ts.isCallExpression(n) && n.expression.kind === ts.SyntaxKind.SuperKeyword) { const o = n.arguments.find((a) => ts.isObjectLiteralExpression(a) && prop(a, 'id')); if (o) { obj = o; return; } }
          ts.forEachChild(n, findSuper);
        };
        if (ts.isClassExpression(a0)) findSuper(a0);
        if (obj) addCmd(resolve(prop(obj, 'id')), { ...descFromAction(obj), source: 'Action2' }, sf);
      } else if (/MenuRegistry\.appendMenuItems?$/.test(callee) && node.arguments.length >= 2) {
        const items = /appendMenuItems$/.test(callee) && ts.isArrayLiteralExpression(a0) ? a0.elements.map((e) => ({ id: prop(e, 'id'), item: prop(e, 'item') })) : [{ id: a0, item: node.arguments[1] }];
        for (const { id: mid, item } of items) {
          const cmd = item && prop(item, 'command');
          if (cmd && ts.isObjectLiteralExpression(cmd)) {
            const info = { title: textOf(prop(cmd, 'title')), source: 'MenuRegistry' };
            const cat = prop(cmd, 'category'); if (cat) info.category = textOf(cat) || exprText(cat);
            const pre = prop(cmd, 'precondition'); if (pre) info.precondition = whenText(pre);
            const menuEntry = { id: exprText(mid) };
            const w = prop(item, 'when'); if (w) menuEntry.when = whenText(w);
            info.menus = [menuEntry];
            addCmd(resolve(prop(cmd, 'id')), info, sf);
          }
        }
      } else if (/MenuRegistry\.addCommand$/.test(callee) && a0 && ts.isObjectLiteralExpression(a0)) {
        addCmd(resolve(prop(a0, 'id')), { title: textOf(prop(a0, 'title')), category: textOf(prop(a0, 'category')), source: 'MenuRegistry' }, sf);
      } else if (/registerEditorAction$|registerEditorCommand$|registerInstantiatedEditorAction$/.test(callee)) {
        // class FooAction extends EditorAction { constructor() { super({ id }) } } registered by class name -> handled via class scan below
      }
    }
    // editor actions / workbench actions defined as classes (EditorAction, EditorCommand, Action2 subclasses registered elsewhere)
    if (ts.isClassDeclaration(node) && node.heritageClauses) {
      const base = node.heritageClauses.map((h) => h.types.map((t) => t.expression.getText()).join(',')).join(',');
      if (/(EditorAction2?|EditorCommand|Action2|ViewAction|EditorAction2|MultiCommand|AbstractEditorCommand|ViewPaneAction|ToggleTitleBarConfigAction|Action)\b/.test(base)) {
        let obj;
        const findSuper = (n) => {
          if (obj) return;
          if (ts.isCallExpression(n) && n.expression.kind === ts.SyntaxKind.SuperKeyword) { const o = n.arguments.find((a) => ts.isObjectLiteralExpression(a) && prop(a, 'id')); if (o) { obj = o; return; } }
          ts.forEachChild(n, findSuper);
        };
        findSuper(node);
        if (obj) {
          const id = resolve(prop(obj, 'id'));
          if (id) addCmd(id, { ...descFromAction(obj), source: /EditorAction|EditorCommand/.test(base) ? 'EditorAction' : 'Action2' }, sf);
        }
      }
    }
    // registerTerminalAction({ id, ... }) / registerActiveInstanceAction / register*Action({ id }) helpers
    if (ts.isCallExpression(node) && /(^|\.)register\w*(Action|Command)$/.test(node.expression.getText()) && !/registerAction2$|CommandsRegistry|registerCommandAndKeybindingRule$/.test(node.expression.getText()) && node.arguments[0] && ts.isObjectLiteralExpression(node.arguments[0]) && prop(node.arguments[0], 'id')) {
      addCmd(resolve(prop(node.arguments[0], 'id')), { ...descFromAction(node.arguments[0]), source: 'Action2' }, sf);
    }
    // registerOverwritableCommand(Handler.Type, meta) -> 'type' and 'default:type'
    if (ts.isCallExpression(node) && /registerOverwritableCommand$/.test(node.expression.getText()) && node.arguments[0]) {
      const h = resolve(node.arguments[0]);
      const meta = node.arguments[1] && ts.isObjectLiteralExpression(node.arguments[1]) ? descFromAction(ts.factory.createObjectLiteralExpression([])) : {};
      if (node.arguments[1] && ts.isObjectLiteralExpression(node.arguments[1])) { meta.description = textOf(prop(node.arguments[1], 'description')); }
      addCmd(h, { ...meta, source: 'EditorCommand' }, sf);
      addCmd('default:' + h, { ...meta, source: 'EditorCommand' }, sf);
    }
    // new SomethingCommand({ id: ... }) / new XAction({ id: ... }) (editor core commands)
    if (ts.isNewExpression(node) && node.arguments && node.arguments[0] && ts.isObjectLiteralExpression(node.arguments[0]) && /(Command|Action)\w*$/.test(node.expression.getText()) && !/ApiCommand/.test(node.expression.getText())) {
      const id = resolve(prop(node.arguments[0], 'id'));
      if (id && prop(node.arguments[0], 'precondition') !== undefined || id && /Command/.test(node.expression.getText())) addCmd(id, { ...descFromAction(node.arguments[0]), source: 'EditorCommand' }, sf);
    }
    // view containers / views: openCommandActionDescriptor { id } -> "Show <container>" command
    if (ts.isPropertyAssignment(node) && node.name && node.name.getText() === 'openCommandActionDescriptor' && ts.isObjectLiteralExpression(node.initializer)) {
      const owner = node.parent;
      let id = resolve(prop(node.initializer, 'id'));
      const idExpr = exprText(prop(node.initializer, 'id')) || '';
      if (id === undefined && /^\w+\.id$/.test(idExpr)) {
        const vname = idExpr.split('.')[0];
        const findVar = (n) => {
          if (id !== undefined) return;
          if (ts.isVariableDeclaration(n) && n.name.getText() === vname && n.initializer && ts.isCallExpression(n.initializer)) {
            const o = n.initializer.arguments.find((a) => ts.isObjectLiteralExpression(a) && prop(a, 'id'));
            if (o) id = resolve(prop(o, 'id'));
          }
          ts.forEachChild(n, findVar);
        };
        findVar(sf);
        if (id === undefined) id = resolve(prop(owner, 'id'));
      }
      const title = textOf(prop(node.initializer, 'title')) || textOf(prop(owner, 'title')) || textOf(prop(owner, 'name'));
      const info = { title: title ? 'Show ' + title : undefined, source: 'ViewContainer' };
      const kb = keybindingInfo(prop(node.initializer, 'keybindings')); if (kb) info.keybinding = kb;
      addCmd(id, info, sf);
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
// "literal" JSON-ish conversion of an expression (schemas)
function literal(node, depth = 0) {
  if (!node || depth > 12) return undefined;
  const s = resolve(node);
  if (s !== undefined) return s;
  switch (node.kind) {
    case ts.SyntaxKind.TrueKeyword: return true;
    case ts.SyntaxKind.FalseKeyword: return false;
    case ts.SyntaxKind.NullKeyword: return null;
    case ts.SyntaxKind.NumericLiteral: return Number(node.text);
    default: break;
  }
  if (ts.isPrefixUnaryExpression(node) && ts.isNumericLiteral(node.operand)) return -Number(node.operand.text);
  if (ts.isArrayLiteralExpression(node)) return node.elements.map((e) => literal(e, depth + 1));
  if (ts.isObjectLiteralExpression(node)) {
    const o = {};
    for (const p of node.properties) {
      if (ts.isPropertyAssignment(p)) {
        const k = p.name && (ts.isStringLiteral(p.name) || ts.isIdentifier(p.name) || ts.isNumericLiteral(p.name)) ? p.name.text : (p.name ? (resolve(p.name.expression) || p.name.getText()) : '?');
        o[k] = literal(p.initializer, depth + 1);
      } else if (ts.isSpreadAssignment(p)) {
        const v = literal(p.expression, depth + 1);
        if (v && typeof v === 'object' && !Array.isArray(v)) Object.assign(o, v); else o['...'] = exprText(p.expression);
      }
    }
    return o;
  }
  const t = textOf(node);
  if (t !== undefined) return t;
  if (ts.isIdentifier(node)) {
    // an object constant of the same file, or one imported by name
    const f = fkey(node.getSourceFile().fileName);
    let o = objConsts.get(f + '#' + node.text);
    if (!o) { const imp = (fileImports.get(f) || new Map()).get(node.text); if (imp && !imp.ns) o = objConsts.get(fkey(imp.file) + '#' + imp.name); }
    if (o) return literal(o, depth + 1);
  }
  if (ts.isAsExpression(node) || ts.isParenthesizedExpression(node) || ts.isSatisfiesExpression && ts.isSatisfiesExpression(node)) return literal(node.expression, depth + 1);
  return '<' + exprText(node) + '>';
}


// ---------------------------------------------------------------- API commands (extension host)
const argStatics = {};
const apiCommands = [];
for (const sf of parsed) {
  const fr = rel(sf.fileName);
  if (!fr.includes('/api/common/')) continue;
  const visit = (node) => {
    if (fr.endsWith('extHostCommands.ts') && ts.isPropertyDeclaration(node) && node.initializer && ts.isNewExpression(node.initializer) && /ApiCommandArgument/.test(node.initializer.expression.getText())) {
      const a = node.initializer.arguments;
      argStatics['ApiCommandArgument.' + node.name.getText()] = { name: resolve(a[0]), description: resolve(a[1]) };
    }
    if (ts.isNewExpression(node) && node.expression.getText() === 'ApiCommand' && node.arguments && node.arguments.length >= 4) {
      const [id, internal, desc, args, result] = node.arguments;
      const e = { id: resolve(id), internalId: resolve(internal), description: textOf(desc), args: [], file: fr };
      if (args && ts.isArrayLiteralExpression(args)) {
        for (const a of args.elements) {
          const t = a.getText();
          const inner = ts.isCallExpression(a) && /\.optional$/.test(a.expression.getText()) && ts.isPropertyAccessExpression(a.expression) && ts.isNewExpression(a.expression.expression) ? a.expression.expression : null;
          if (inner && inner.arguments) e.args.push({ name: resolve(inner.arguments[0]) || exprText(inner.arguments[0]), description: textOf(inner.arguments[1]) || '', optional: true });
          else if (ts.isNewExpression(a) && a.arguments) e.args.push({ name: resolve(a.arguments[0]) || exprText(a.arguments[0]), description: textOf(a.arguments[1]) || '' });
          else if (/^ApiCommandArgument\.\w+\.with\(/.test(t)) {
            const m = /^(ApiCommandArgument\.\w+)\.with\(\s*'(.*?)'\s*,\s*'(.*)'\s*\)(\.optional\(\))?$/s.exec(t.replace(/\s+/g, ' '));
            if (m) e.args.push({ name: m[2], description: m[3].split("\'").join("'"), type: (argStatics[m[1]] || {}).name, optional: !!m[4] || undefined });
            else e.args.push({ name: t });
          } else if (/\.optional\(\)$/.test(t)) e.args.push({ ...(argStatics[t.replace(/\.optional\(\)$/, '')] || { name: t }), optional: true });
          else if (/ApiCommandArgument\.Arr\(/.test(t)) { const inner = /Arr\(([\w.]+)\)/.exec(t); const b = argStatics[inner && inner[1]] || { name: inner && inner[1] }; e.args.push({ name: b.name + '_array', description: 'Array of ' + b.name + ', ' + (b.description || '') }); } else e.args.push(argStatics[t] || { name: t });
        }
      }
      if (result && ts.isNewExpression(result) && result.arguments) {
        e.returns = textOf(result.arguments[0]);
        if (result.typeArguments && result.typeArguments[1]) e.returnType = result.typeArguments[1].getText().replace(/\s+/g, ' ');
      } else if (result) e.returns = exprText(result);
      apiCommands.push(e);
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
// argStatics may be filled after the first file: re-resolve names
for (const c of apiCommands) for (const a of c.args) if (a.name && a.name.startsWith('ApiCommandArgument.') && argStatics[a.name]) Object.assign(a, argStatics[a.name]);
console.error('api commands', apiCommands.length, 'commands', commands.size);

// ---------------------------------------------------------------- contribution points
// object-literal constants for schema resolution
for (const sf of parsed) {
  const visit = (node) => {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer && ts.isObjectLiteralExpression(node.initializer) && node.parent && node.parent.parent && node.parent.parent.parent && ts.isSourceFile(node.parent.parent.parent)) objConsts.set(fkey(sf.fileName) + '#' + node.name.text, node.initializer);
    ts.forEachChild(node, visit);
  };
  const fr = rel(sf.fileName);
  void fr; visit(sf);
}
const contributionPoints = [];
for (const sf of parsed) {
  const visit = (node) => {
    if (ts.isCallExpression(node) && /registerExtensionPoint$/.test(node.expression.getText()) && node.arguments[0] && ts.isObjectLiteralExpression(node.arguments[0])) {
      const o = node.arguments[0];
      const name = resolve(prop(o, 'extensionPoint'));
      const schema = literal(prop(o, 'jsonSchema'));
      const deps = prop(o, 'deps');
      contributionPoints.push({ extensionPoint: name, file: rel(sf.fileName), description: schema && typeof schema === 'object' ? schema.description : undefined, deps: deps ? exprText(deps) : undefined, jsonSchema: schema });
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
console.error('contribution points', contributionPoints.length);
// menu ids extensions may contribute to (menusExtensionPoint.ts apiMenus)
const apiMenus = [];
{
  const sf = parsed.find((s) => rel(s.fileName).endsWith('menusExtensionPoint.ts'));
  const visit = (node) => {
    if (ts.isVariableDeclaration(node) && node.name.getText() === 'apiMenus' && node.initializer && ts.isArrayLiteralExpression(node.initializer)) {
      for (const e of node.initializer.elements) {
        if (!ts.isObjectLiteralExpression(e)) continue;
        apiMenus.push({ key: resolve(prop(e, 'key')), id: exprText(prop(e, 'id')), description: textOf(prop(e, 'description')), proposed: resolve(prop(e, 'proposed')), supportsSubmenus: prop(e, 'supportsSubmenus') ? prop(e, 'supportsSubmenus').getText() !== 'false' : true });
      }
    }
    ts.forEachChild(node, visit);
  };
  if (sf) visit(sf);
}
console.error('api menus', apiMenus.length);

// ---------------------------------------------------------------- vscode.d.ts
const dtsVersions = fs.readdirSync(DTS_DIR).map((f) => /^vscode-(.+)\.d\.ts$/.exec(f)).filter(Boolean).map((m) => m[1])
  .sort((a, b) => { const pa = a.split('.').map(Number); const pb = b.split('.').map(Number); return pa[0] - pb[0] || pa[1] - pb[1] || pa[2] - pb[2]; });
function dtsInventory(file) {
  const text = fs.readFileSync(file, 'utf8');
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true);
  const items = [];
  const docOf = (n) => { const j = n.jsDoc && n.jsDoc[0]; if (!j) return undefined; const c = typeof j.comment === 'string' ? j.comment : (j.comment || []).map((x) => x.text || '').join(''); return c ? c.split('\n')[0].trim().slice(0, 240) : undefined; };
  const deprecated = (n) => !!(n.jsDoc && n.jsDoc.some((j) => (j.tags || []).some((t) => t.tagName.text === 'deprecated')));
  const sig = (n) => n.getText().replace(/\/\*\*[\s\S]*?\*\//g, '').replace(/\s+/g, ' ').trim().slice(0, 600);
  const memberKind = (m) => {
    if (ts.isMethodSignature(m) || ts.isMethodDeclaration(m)) return 'method';
    if (ts.isConstructorDeclaration(m) || ts.isConstructSignatureDeclaration(m)) return 'constructor';
    if (ts.isPropertySignature(m) || ts.isPropertyDeclaration(m)) return /^(readonly\s+)?on(Did|Will)[A-Z]/.test(m.name ? m.name.getText() : '') ? 'event' : 'property';
    if (ts.isGetAccessor(m)) return 'property';
    if (ts.isEnumMember(m)) return 'member';
    if (ts.isCallSignatureDeclaration(m)) return 'call';
    if (ts.isIndexSignatureDeclaration(m)) return 'index';
    return 'other';
  };
  const walkNs = (block, prefix) => {
    for (const st of block.statements || []) {
      const name = st.name ? st.name.getText() : undefined;
      const full = prefix ? prefix + '.' + name : name;
      if (ts.isModuleDeclaration(st)) {
        items.push({ name: full, kind: 'namespace', doc: docOf(st) });
        if (st.body) walkNs(st.body, full);
      } else if (ts.isFunctionDeclaration(st)) {
        items.push({ name: full, kind: 'function', signature: sig(st), doc: docOf(st), deprecated: deprecated(st) || undefined });
      } else if (ts.isVariableStatement(st)) {
        for (const d of st.declarationList.declarations) {
          const n = (prefix ? prefix + '.' : '') + d.name.getText();
          const isEvent = /^on(Did|Will)[A-Z]/.test(d.name.getText());
          items.push({ name: n, kind: isEvent ? 'event' : (st.declarationList.flags & ts.NodeFlags.Const ? 'const' : 'variable'), signature: sig(d), doc: docOf(st), deprecated: deprecated(st) || undefined });
        }
      } else if (ts.isClassDeclaration(st) || ts.isInterfaceDeclaration(st) || ts.isEnumDeclaration(st)) {
        const kind = ts.isClassDeclaration(st) ? 'class' : ts.isInterfaceDeclaration(st) ? 'interface' : 'enum';
        const heritage = st.heritageClauses ? st.heritageClauses.map((h) => h.getText()).join(' ') : undefined;
        items.push({ name: full, kind, doc: docOf(st), heritage, deprecated: deprecated(st) || undefined });
        for (const m of st.members) {
          const mk = memberKind(m);
          const mn = mk === 'constructor' ? 'constructor' : m.name ? m.name.getText() : '(' + mk + ')';
          const e = { name: full + '.' + mn, kind: mk, owner: full, signature: sig(m), doc: docOf(m), deprecated: deprecated(m) || undefined };
          if (mk === 'member' && m.initializer) e.value = m.initializer.getText();
          if (m.modifiers && m.modifiers.some((x) => x.kind === ts.SyntaxKind.StaticKeyword)) e.static = true;
          if (m.questionToken) e.optional = true;
          items.push(e);
        }
      } else if (ts.isTypeAliasDeclaration(st)) {
        items.push({ name: full, kind: 'type', signature: sig(st), doc: docOf(st) });
      }
    }
  };
  ts.forEachChild(sf, (n) => {
    if (ts.isModuleDeclaration(n) && n.body) walkNs(n.body, '');
  });
  return items;
}
const latest = dtsInventory(path.join(SRC, 'vscode-dts', 'vscode.d.ts'));
const since = {};
for (const v of dtsVersions) for (const it of dtsInventory(path.join(DTS_DIR, `vscode-${v}.d.ts`))) if (!(it.name in since)) since[it.name] = v;
for (const it of latest) { it.since = since[it.name] ? (since[it.name] === dtsVersions[0] ? '<=' + dtsVersions[0] : since[it.name]) : 'main'; }
console.error('vscode.d.ts items', latest.length);

// API commands are commands too (setContext, vscode.execute*Provider ...)
for (const a of apiCommands) {
  const e = commands.get(a.id) || { id: a.id, sources: [], files: [] };
  if (!e.sources.includes('ApiCommand')) e.sources.push('ApiCommand');
  if (!e.files.includes(a.file)) e.files.push(a.file);
  e.description = e.description || a.description; e.args = e.args || a.args; e.returns = e.returns || a.returns;
  commands.set(a.id, e);
}
// command ids VS Code creates at run time per view / view container (src/vs/workbench/services/views/browser/viewsService.ts,
// src/vs/workbench/api/browser/viewsExtensionPoint.ts)
const dynamicCommands = [
  { pattern: '${viewId}.focus', description: 'Focus on {view name} View: opens the view (and its container) and focuses it.', args: [{ name: 'focusOptions', schema: { type: 'object', properties: { preserveFocus: { type: 'boolean', default: false } } } }], file: 'src/vs/workbench/services/views/browser/viewsService.ts' },
  { pattern: '${viewId}.open', description: 'Opens view {name}; when the view already has focus: side bar -> focus the editor, other parts -> hide the part.', args: [{ name: 'options', schema: { type: 'object', properties: { preserveFocus: { type: 'boolean', default: false } } } }], file: 'src/vs/workbench/services/views/browser/viewsService.ts' },
  { pattern: '${viewId}.resetViewLocation', description: 'Reset Location (moves the view back to its default container).', file: 'src/vs/workbench/services/views/browser/viewsService.ts' },
  { pattern: '${viewId}.toggleVisibility', description: 'Toggles the view in its container.', file: 'src/vs/workbench/browser/parts/views/viewPaneContainer.ts' },
  { pattern: '${viewId}.removeView', description: 'Hides the view from its container.', file: 'src/vs/workbench/browser/parts/views/viewPaneContainer.ts' },
  { pattern: 'workbench.view.extension.${viewsContainerId}', description: 'Show/Toggle an extension view container (contributes.viewsContainers): side bar / secondary side bar -> open + focus, or focus the editor when it is already focused; panel -> toggle.', file: 'src/vs/workbench/api/browser/viewsExtensionPoint.ts' },
];
// ---------------------------------------------------------------- write
const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));
const meta = { source: 'https://github.com/microsoft/vscode', commit: process.env.VSCODE_COMMIT || '', version: pkg.version, license: 'MIT', generatedBy: 'radide/vsx/reference/extract.js', dtsVersionsCompared: dtsVersions };
const clean = (o) => JSON.parse(JSON.stringify(o));
const sortById = (a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
fs.writeFileSync(path.join(OUT, 'commands.json'), JSON.stringify(clean({ meta, apiCommands: apiCommands.sort(sortById), dynamicCommands, commands: [...commands.values()].sort(sortById) }), null, 1));
fs.writeFileSync(path.join(OUT, 'context_keys.json'), JSON.stringify(clean({ meta, contextKeys: [...contextKeys.values()].sort((a, b) => (a.key < b.key ? -1 : 1)) }), null, 1));
fs.writeFileSync(path.join(OUT, 'contribution_points.json'), JSON.stringify(clean({ meta, menus: apiMenus, contributionPoints: contributionPoints.sort((a, b) => (String(a.extensionPoint) < String(b.extensionPoint) ? -1 : 1)) }), null, 1));
fs.writeFileSync(path.join(OUT, 'vscode_api.json'), JSON.stringify(clean({ meta, items: latest }), null, 1));
console.error('done');
