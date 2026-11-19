'use strict';
/*
 * RAD IDE - GUI Bridge client for JavaScript and TypeScript (Node.js).
 *
 * The IDE draws the forms; this program talks to it over stdin/stdout
 * (protocol in docs/CONTRACTS.md, section 1). Everything here is synchronous:
 * a handler that calls get() blocks until the IDE answers.
 *
 * Globals available to form code and modules:
 *   set(obj, prop, value)        SET a property            set("lblOut", "Caption", "Hi")
 *   get(obj, prop)       -> str  GET a property            get("txtA", "Text")
 *   getNum(obj, prop)    -> num  GET a property as a number
 *   call(obj, method, ...args)   CALL a method             call("lstLog", "AddItem", "line")
 *   msgbox(text)                 message box (waits for OK)
 *   input(prompt)        -> str  input box
 *   show(form) / hide(form)      show or hide a form
 *   end()                        quit the program
 *   ui.<control>.<Prop>          property access sugar: ui.lblOut.Caption = "x"; ui.txtA.Text
 *   ui.<control>.<Method>(...)   method sugar: ui.lstLog.AddItem("x"); ui.lstLog.Clear()
 *   radcall("Module.func", ...args) -> value   call a function of any project module (RAD Hub)
 *   require(name)                loads npm packages from the project's node_modules
 * Handlers are plain functions named <Control>_<Event>; they receive one argument
 * e = { X, Y, Button, KeyCode, KeyChar, args } (mouse/key events, otherwise zeros).
 */
const fs = require('fs');
const path = require('path');
const util = require('util');
const vm = require('vm');
const { createRequire } = require('module');

// ------------------------------------------------------------------ sync I/O
const SLEEP = new Int32Array(new SharedArrayBuffer(4));
const CHUNK = Buffer.alloc(65536);
let inBuf = Buffer.alloc(0);
let inEof = false;

function sleepMs(ms) { Atomics.wait(SLEEP, 0, 0, ms); }

/** Read one line from stdin (blocking). Returns null at end of input. */
function readLine() {
  for (;;) {
    const nl = inBuf.indexOf(10);
    if (nl >= 0) {
      let line = inBuf.subarray(0, nl).toString('utf8');
      inBuf = inBuf.subarray(nl + 1);
      if (line.endsWith('\r')) line = line.slice(0, -1);
      return line;
    }
    if (inEof) {
      if (inBuf.length) {
        const rest = inBuf.toString('utf8');
        inBuf = Buffer.alloc(0);
        return rest;
      }
      return null;
    }
    let n = 0;
    try {
      n = fs.readSync(0, CHUNK, 0, CHUNK.length, null);
    } catch (e) {
      if (e.code === 'EAGAIN') { sleepMs(5); continue; }
      if (e.code === 'EOF' || e.code === 'EPIPE') n = 0; else throw e;
    }
    if (n === 0) inEof = true;
    else inBuf = Buffer.concat([inBuf, CHUNK.subarray(0, n)]);
  }
}

function writeFd(fd, text) {
  const b = Buffer.from(text, 'utf8');
  let off = 0;
  while (off < b.length) {
    try {
      off += fs.writeSync(fd, b, off, b.length - off);
    } catch (e) {
      if (e.code === 'EAGAIN') { sleepMs(1); continue; }
      if (e.code === 'EPIPE' || e.code === 'EOF') return;
      throw e;
    }
  }
}

let outFd = 1;          // the worker sends its logs to stderr (fd 2)
function writeLine(text) { writeFd(outFd, text + '\n'); }

/** console.* must be synchronous: the program blocks in readSync between events. */
function patchConsole(fd) {
  const out = (...a) => writeFd(fd, util.format(...a) + '\n');
  const err = (...a) => writeFd(2, util.format(...a) + '\n');
  console.log = console.info = console.debug = out;
  console.warn = console.error = console.trace = err;
}

// ------------------------------------------------------------------ protocol
const oneLine = (v) => String(v === undefined || v === null ? '' : v).replace(/\r?\n|\r/g, ' ');

function set(obj, prop, value) {
  if (typeof value === 'boolean') value = value ? 'True' : 'False';
  writeLine(`SET ${obj} ${prop} ${oneLine(value)}`);
}

function get(obj, prop) {
  writeLine(`GET ${obj} ${prop}`);
  const r = readLine();
  return r === null ? '' : r;
}

function getNum(obj, prop) {
  const n = Number(String(get(obj, prop)).trim().replace(',', '.'));
  return Number.isFinite(n) ? n : 0;
}

function call(obj, method, ...args) {
  const a = args.map((x) => oneLine(typeof x === 'boolean' ? (x ? 'True' : 'False') : x).replace(/\t/g, ' '));
  writeLine(`CALL ${obj} ${method}${a.length ? ' ' + a.join('\t') : ''}`);
  const r = readLine();
  return r === null ? '' : r;
}

function msgbox(text) {
  writeLine(`MSGBOX ${oneLine(text)}`);
  return readLine();
}

function input(prompt) {
  writeLine(`INPUT ${oneLine(prompt)}`);
  const r = readLine();
  return r === null ? '' : r;
}

function show(form) { writeLine(`SHOW ${form}`); }
function hide(form) { writeLine(`HIDE ${form}`); }

let ended = false;
function end() {
  if (!ended) { ended = true; writeLine('END'); }
}

const METHODS = new Set(['additem', 'removeitem', 'clear', 'list', 'setfocus', 'move', 'show', 'hide',
  'refresh', 'showdialog', 'zorder', 'item', 'selectall', 'cls', 'print']);

/** ui.txtA.Text (GET), ui.lblOut.Caption = 1 (SET), ui.lstLog.AddItem("x") (CALL). */
const ui = new Proxy({}, {
  get(_t, objName) {
    if (typeof objName !== 'string') return undefined;
    return new Proxy({}, {
      get(_t2, prop) {
        if (typeof prop !== 'string') return undefined;
        if (METHODS.has(prop.toLowerCase())) return (...args) => call(objName, prop, ...args);
        return get(objName, prop);
      },
      set(_t2, prop, value) { set(objName, String(prop), value); return true; },
    });
  },
});

// ------------------------------------------------------------------ RAD Hub client
let hub = null;   // { worker, port, flag, nextId }

function hubConnect() {
  if (hub) return hub;
  const addr = process.env.RAD_HUB || '';
  const i = addr.lastIndexOf(':');
  if (i < 0) throw new Error('radcall: RAD Hub is not running (RAD_HUB is not set)');
  const { Worker, MessageChannel } = require('worker_threads');
  const flag = new Int32Array(new SharedArrayBuffer(4));
  const { port1, port2 } = new MessageChannel();
  // a helper thread owns the TCP socket; the main thread waits on `flag` (Atomics) for each answer
  const code = `
    const { workerData } = require('worker_threads');
    const net = require('net');
    const { port, flag, host, portNo } = workerData;
    let buf = '', sock = null, failed = null;
    const pending = [];
    function answer(obj) { port.postMessage(obj); Atomics.store(flag, 0, 1); Atomics.notify(flag, 0); }
    function connect() {
      sock = net.createConnection({ host, port: portNo });
      sock.setEncoding('utf8');
      sock.on('data', (d) => {
        buf += d;
        let k;
        while ((k = buf.indexOf('\\n')) >= 0) {
          const line = buf.slice(0, k); buf = buf.slice(k + 1);
          if (!line.trim()) continue;
          let obj; try { obj = JSON.parse(line); } catch (e) { obj = { error: 'bad reply from RAD Hub: ' + line }; }
          pending.shift(); answer(obj);
        }
      });
      sock.on('error', (e) => { failed = e.message; while (pending.length) { pending.shift(); answer({ error: 'RAD Hub: ' + failed }); } });
      sock.on('close', () => { if (!failed) failed = 'connection closed'; while (pending.length) { pending.shift(); answer({ error: 'RAD Hub: ' + failed }); } sock = null; });
    }
    port.on('message', (req) => {
      if (!sock) { failed = null; connect(); }
      pending.push(req.id);
      sock.write(JSON.stringify(req) + '\\n');
    });
  `;
  const worker = new Worker(code, {
    eval: true,
    workerData: { port: port2, flag, host: addr.slice(0, i) || '127.0.0.1', portNo: Number(addr.slice(i + 1)) },
    transferList: [port2],
  });
  worker.unref();
  port1.unref();
  hub = { worker, port: port1, flag, nextId: 1 };
  return hub;
}

/** Call "<Module>.<function>" in any language of the project; returns the JSON result. */
function radcall(name, ...args) {
  const h = hubConnect();
  const { receiveMessageOnPort } = require('worker_threads');
  const id = h.nextId++;
  Atomics.store(h.flag, 0, 0);
  h.port.postMessage({ id, call: String(name), args });
  const deadline = Date.now() + 60000;
  for (;;) {
    Atomics.wait(h.flag, 0, 0, 50);
    const msg = receiveMessageOnPort(h.port);
    if (msg) {
      const reply = msg.message;
      if (reply && reply.error !== null && reply.error !== undefined)
        throw new Error(`radcall ${name}: ${reply.error}`);
      return reply ? reply.result : null;
    }
    if (Date.now() > deadline) throw new Error(`radcall ${name}: RAD Hub did not answer within 60 s`);
  }
}

// ------------------------------------------------------------------ loading user code
function stripTypes(code, file) {
  const mod = require('module');
  if (typeof mod.stripTypeScriptTypes === 'function') {
    try {
      return mod.stripTypeScriptTypes(code, { mode: 'transform', sourceUrl: file });
    } catch (e) {
      // 'transform' needs a newer Node in some versions; fall back to plain stripping
      if (!/mode|transform/i.test(String(e && e.message))) throw e;
      return mod.stripTypeScriptTypes(code, { mode: 'strip', sourceUrl: file });
    }
  }
  let ts = null;
  try { ts = createRequire(path.join(process.cwd(), 'package.json'))('typescript'); } catch (e) { ts = null; }
  if (ts) {
    return ts.transpileModule(code, { fileName: file,
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None } }).outputText;
  }
  throw new Error('TypeScript needs Node.js 22.13+ (module.stripTypeScriptTypes) or the "typescript" npm package ' +
                  'in the project (npm install typescript)');
}

let globalsInstalled = false;
function installGlobals(folder) {
  if (globalsInstalled) return;
  globalsInstalled = true;
  const g = globalThis;
  Object.assign(g, { set, get, getNum, call, msgbox, input, show, hide, end, ui, radcall });
  g.require = createRequire(path.join(folder, 'package.json'));
  g.__radfolder = folder;
}

/** Run a .js/.ts file in the global scope so its top-level functions become callable by name. */
function loadScript(file) {
  const full = path.resolve(file);
  let code = fs.readFileSync(full, 'utf8');
  if (code.charCodeAt(0) === 0xfeff) code = code.slice(1);
  if (/\.(ts|mts|cts)$/i.test(full)) {
    // TypeScript files are scripts too: drop module syntax that would make them modules
    code = code.replace(/^\s*export\s+(?=(function|const|let|var|class|async|enum|interface|type)\b)/gm, '');
    code = stripTypes(code, full);
  }
  if (code.startsWith('#!')) code = '//' + code;
  vm.runInThisContext(code, { filename: full });
}

function findHandler(name) {
  const g = globalThis;
  if (typeof g[name] === 'function') return g[name];
  const low = name.toLowerCase();       // the bridge's handler names are case-insensitive
  for (const k of Object.keys(g)) if (k.toLowerCase() === low && typeof g[k] === 'function') return g[k];
  try {
    const f = vm.runInThisContext(`typeof ${name} === 'function' ? ${name} : undefined`);
    if (f) return f;
  } catch (e) { /* not a valid identifier */ }
  return null;
}

function eventArgs(rest) {
  const p = rest ? rest.split(' ') : [];
  const num = (s) => { const n = Number(s); return Number.isFinite(n) ? n : 0; };
  return { X: num(p[0]), Y: num(p[1]), Button: num(p[2]), KeyCode: num(p[3]),
           KeyChar: p.length > 4 ? p.slice(4).join(' ') : '', args: rest || '' };
}

function report(where, e) {
  const msg = e && e.stack ? e.stack : String(e);
  writeFd(2, `[${where}] ${msg}\n`);
}

/** Entry point of the generated _radmain.js: load the code files, then serve events. */
function runMain(files, folder) {
  folder = folder || process.cwd();
  patchConsole(1);
  installGlobals(folder);
  for (const f of files) {
    try { loadScript(path.resolve(folder, f)); } catch (e) { report(`error loading ${f}`, e); }
  }
  for (;;) {
    const line = readLine();
    if (line === null || line.trim().toUpperCase() === 'QUIT') break;
    if (!line.startsWith('EVENT ')) continue;
    const [, obj = '', ev = '', ...rest] = line.split(' ');
    const name = `${obj}_${ev}`;
    try {
      const fn = findHandler(name);
      if (fn) {
        const r = fn(eventArgs(rest.join(' ')));
        if (r && typeof r.then === 'function')
          writeFd(2, `[${name}] async handlers are not awaited; make the handler synchronous\n`);
      }
    } catch (e) {
      report(name, e);
    } finally {
      writeLine('DONE');
    }
    if (ended) break;
  }
  process.exit(0);
}

module.exports = {
  set, get, getNum, call, msgbox, input, show, hide, end, ui, radcall,
  readLine, writeLine, writeFd, patchConsole, installGlobals, loadScript, findHandler, runMain,
  _setOutFd(fd) { outFd = fd; },
};
