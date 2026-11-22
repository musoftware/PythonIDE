'use strict';
// Probes RAD IDE's real `vscode` module (radide/vsx/host/api.js on a real Host from main.js) against
// vscode_api.json and prints one JSON object {name: status} to stdout.
//   node api_probe.js <vscode_api.json>
// status: implemented | stub (present, does nothing / never fires) | missing (soft-stubbed by api.js) |
//         consumed (extension-implemented interface whose method RAD IDE calls) | not-consumed |
//         honoured / ignored (data/option interfaces: the member name is read somewhere in RAD IDE)
const fs = require('fs');
const path = require('path');
const os = require('os');

const apiFile = process.argv[2];
const HOST = path.resolve(__dirname, '..', 'host');
const VSX = path.resolve(__dirname, '..');
const write = process.stdout.write.bind(process.stdout);
// main.js redirects stdout and starts an Rpc on stdin: give it a quiet stdin and keep our real stdout
const { host } = require(path.join(HOST, 'main.js'));
host.rpc.notify = () => {};
host.rpc.request = () => new Promise(() => {});
host.storageRoot = path.join(os.tmpdir(), 'radide-api-probe');
const T = require(path.join(HOST, 'types.js'));
const { createApi, createContext } = require(path.join(HOST, 'api.js'));

const ext = { id: 'probe.probe', idOriginal: 'probe.probe', path: __dirname, packageJSON: { name: 'probe', publisher: 'probe', version: '0.0.0', contributes: {} }, active: true };
host.extensions.set(ext.id, ext);
const api = createApi(host, ext);
const raw = (o) => o;   // namespaces are Proxies whose `in` falls through to the real object

// all RAD IDE source text (JS host + Python IDE side) for the "is this member read anywhere" heuristics
const srcText = [];
for (const f of fs.readdirSync(HOST)) if (f.endsWith('.js')) srcText.push(fs.readFileSync(path.join(HOST, f), 'utf8'));
const jsText = srcText.join('\n');
for (const f of fs.readdirSync(VSX)) if (f.endsWith('.py')) srcText.push(fs.readFileSync(path.join(VSX, f), 'utf8'));
const allText = srcText.join('\n');

const NOOP_RE = /^(?:\([^)]*\)|\w+)\s*=>\s*(?:new T\.Disposable\(\(\)\s*=>\s*\{\s*\}\)|noopEvent|Promise\.resolve\((?:\[\]|undefined|true|false|null)?\)|\[\]|undefined|\{\s*\})\s*$/;
function isStubFn(f) {
  if (typeof f !== 'function') return false;
  const s = Function.prototype.toString.call(f).replace(/\/\*[\s\S]*?\*\//g, '').trim();
  return NOOP_RE.test(s) || /^noopEvent$/.test(s);
}

// host objects the probe can really create (interface name -> instance)
const inst = {};
function tryMake(name, fn) { try { const v = fn(); if (v) inst[name] = v; } catch (_) { /* */ } }
tryMake('OutputChannel', () => api.window.createOutputChannel('probe'));
tryMake('LogOutputChannel', () => api.window.createOutputChannel('probe-log', { log: true }));
tryMake('StatusBarItem', () => api.window.createStatusBarItem());
tryMake('LanguageStatusItem', () => api.languages.createLanguageStatusItem('probe', '*'));
tryMake('QuickPick', () => api.window.createQuickPick());
tryMake('InputBox', () => api.window.createInputBox());
tryMake('ExtensionContext', () => createContext(host, ext));
tryMake('Memento', () => inst.ExtensionContext && inst.ExtensionContext.globalState);
tryMake('SecretStorage', () => inst.ExtensionContext && inst.ExtensionContext.secrets);
tryMake('GlobalEnvironmentVariableCollection', () => inst.ExtensionContext && inst.ExtensionContext.environmentVariableCollection);
tryMake('EnvironmentVariableCollection', () => inst.GlobalEnvironmentVariableCollection);
tryMake('WorkspaceConfiguration', () => api.workspace.getConfiguration('editor'));
tryMake('DiagnosticCollection', () => api.languages.createDiagnosticCollection('probe'));
tryMake('TextEditorDecorationType', () => api.window.createTextEditorDecorationType({}));
tryMake('TreeView', () => api.window.createTreeView('probe.view', { treeDataProvider: { getChildren() { return []; }, getTreeItem(e) { return e; } } }));
tryMake('Extension', () => api.extensions.getExtension('probe.probe'));
tryMake('Clipboard', () => api.env.clipboard);
tryMake('FileSystem', () => api.workspace.fs);
tryMake('TabGroups', () => api.window.tabGroups);
tryMake('TabGroup', () => api.window.tabGroups.activeTabGroup);
tryMake('WebviewPanel', () => api.window.createWebviewPanel('probe', 'Probe', 1, {}));
tryMake('Webview', () => inst.WebviewPanel && inst.WebviewPanel.webview);
tryMake('CancellationToken', () => api.CancellationToken.None);
tryMake('SourceControl', () => api.scm.createSourceControl('probe', 'Probe'));
tryMake('SourceControlResourceGroup', () => inst.SourceControl && inst.SourceControl.createResourceGroup('g', 'G'));
tryMake('SourceControlInputBox', () => inst.SourceControl && inst.SourceControl.inputBox);
tryMake('CommentController', () => api.comments.createCommentController('probe', 'Probe'));
tryMake('TestController', () => api.tests.createTestController('probe', 'Probe'));
tryMake('TestItemCollection', () => inst.TestController && inst.TestController.items);
tryMake('TestItem', () => inst.TestController && inst.TestController.createTestItem('t', 'T'));
tryMake('TestRunProfile', () => inst.TestController && inst.TestController.createRunProfile('p', 1, () => {}));
tryMake('ChatParticipant', () => api.chat.createChatParticipant('probe', () => {}));
tryMake('TelemetryLogger', () => api.env.createTelemetryLogger({ sendEventData() {}, sendErrorData() {} }));
tryMake('NotebookController', () => api.notebooks.createNotebookController('probe', 'jupyter-notebook', 'Probe'));
tryMake('AuthenticationSession', () => null);
tryMake('LanguageModelAccessInformation', () => inst.ExtensionContext && inst.ExtensionContext.languageModelAccessInformation);
tryMake('WindowState', () => api.window.state);
tryMake('ColorTheme', () => api.window.activeColorTheme);
tryMake('TextDocument', () => { const d = host.docs.open(T.Uri.parse('untitled:probe'), 'plaintext', 1, 'probe\n'); return d; });
tryMake('TextEditor', () => inst.TextDocument && host._editorFor(inst.TextDocument));
tryMake('TextLine', () => inst.TextDocument && inst.TextDocument.lineAt(0));
tryMake('WorkspaceFolder', () => ({ uri: T.Uri.file(__dirname), name: 'probe', index: 0 }));

const EXT_IMPL = /(Provider|Factory|Serializer|Handler|Tracker|Resolver|Adapter|Controller2?|Participant2?Handler)$/;
const dts = JSON.parse(fs.readFileSync(apiFile, 'utf8')).items;
const byName = new Map(dts.map((i) => [i.name, i]));
const out = {};

function classSourceHas(cls, m) {
  for (let c = cls; c && c !== Function.prototype; c = Object.getPrototypeOf(c)) {
    let s = '';
    try { s = Function.prototype.toString.call(c); } catch (_) { break; }
    if (typeof m !== 'string') return false;
    const re = new RegExp(String.raw`(\bthis\.${m}\s*=|(^|[\s;{}])(static\s+)?(get\s+|set\s+|async\s+)?${m}\s*\(|(^|[\s;{}])${m}\s*=|this\._?${m}\b|Object\.assign\(this,\s*\{[^}]*\b${m}\b)`, 'm');
    if (re.test(s)) return true;
  }
  return false;
}
function memberIn(obj, m) {
  if (m === '(index)') return obj != null;                    // an index signature: any key
  if (obj == null) return false;
  try { return m in Object(obj); } catch (_) { return false; }
}
function wordIn(text, m) { return new RegExp(`[.'"\\s{,]${m.replace(/[$]/g, '\\$')}\\b`).test(text); }

for (const it of dts) {
  const name = it.name;
  const parts = name.split('.');
  let status;
  if (it.kind === 'namespace') {
    status = memberIn(api, name) && raw(api[name]) ? 'implemented' : 'missing';
  } else if (!it.owner) {
    // namespace member (window.showQuickPick) or a top level class / enum / interface / function
    if (parts.length >= 2 && byName.get(parts[0]) && byName.get(parts[0]).kind === 'namespace') {
      const ns = api[parts[0]];
      const m = parts.slice(1).join('.');
      if (!ns || !memberIn(ns, m)) status = 'missing';
      else {
        let v;
        try { v = ns[m]; } catch (_) { v = null; }
        status = isStubFn(v) ? 'stub' : 'implemented';
      }
    } else if (it.kind === 'class' || it.kind === 'enum') {
      status = Object.prototype.hasOwnProperty.call(T, name) || memberIn(api, name) ? 'implemented' : 'missing';
    } else if (it.kind === 'interface') {
      status = inst[name] ? 'implemented' : EXT_IMPL.test(name) ? 'extension-implemented' : 'data';
    } else if (it.kind === 'type') {
      status = 'type';
    } else if (it.kind === 'function' || it.kind === 'const' || it.kind === 'variable' || it.kind === 'event') {
      status = memberIn(api, parts[parts.length - 1]) ? 'implemented' : 'missing';
    } else status = 'n/a';
  } else {
    const owner = byName.get(it.owner);
    let m = parts[parts.length - 1];
    if (/^\[Symbol\.(\w+)\]$/.test(name.slice(it.owner.length + 1))) m = Symbol[/^\[Symbol\.(\w+)\]$/.exec(name.slice(it.owner.length + 1))[1]];
    if (!owner) status = 'n/a';
    else if (owner.kind === 'enum') {
      status = T[it.owner] && T[it.owner][m] !== undefined ? 'implemented' : 'missing';
    } else if (owner.kind === 'class') {
      const cls = T[it.owner];
      if (!cls) status = 'missing';
      else if (m === 'constructor') status = 'implemented';
      else if (it.static) status = memberIn(cls, m) ? 'implemented' : 'missing';
      else if (memberIn(cls.prototype, m) || classSourceHas(cls, m)) status = 'implemented';
      // a property the extension sets on its own object (CompletionItem.detail ...): RAD IDE has to read it
      else status = it.kind === 'property' && wordIn(allText, m) ? 'honoured' : 'missing';
    } else if (owner.kind === 'interface') {
      const o = inst[it.owner];
      if (o) {
        if (memberIn(o, m)) { let v; try { v = o[m]; } catch (_) { v = null; } status = isStubFn(v) ? 'stub' : 'implemented'; } else status = it.optional ? 'optional-missing' : 'missing';
      } else if (EXT_IMPL.test(it.owner) || /^(TreeDataProvider|TextDocumentContentProvider|FileSystemProvider|CustomTextEditorProvider|WebviewViewProvider|UriHandler|TerminalLinkProvider|TaskProvider|DebugConfigurationProvider|Pseudoterminal|NotebookSerializer)$/.test(it.owner)) {
        status = it.kind === 'method' || it.kind === 'event' ? (wordIn(jsText, m) ? 'consumed' : 'not-consumed') : (wordIn(allText, m) ? 'consumed' : 'not-consumed');
      } else {
        status = wordIn(allText, m) ? 'honoured' : 'ignored';
      }
    } else status = 'n/a';
  }
  out[name] = status;
}
write(JSON.stringify(out));
process.exit(0);
