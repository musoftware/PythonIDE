'use strict';
/*
 * RAD IDE - RAD Hub worker for JavaScript / TypeScript modules.
 *
 *   node radworker.js <module file>        (absolute, or relative to RAD_PROJECT / cwd)
 *
 * Loads the module in the global scope and serves its top-level functions:
 *   stdin : {"id": 7, "func": "add", "args": [2, 3]}
 *   stdout: {"id": 7, "result": 5}   or   {"id": 7, "error": "message"}
 * radcall() inside a worker (RAD_WORKER=1) goes through stdout/stdin:
 *   stdout: {"id": "w1", "call": "Other.f", "args": [...]}  ->  stdin: {"id": "w1", "result": ...}
 * and keeps serving "func" requests while it waits (so call-backs cannot deadlock).
 * Logs (console.log too) go to stderr so stdout stays clean JSON lines.
 * Functions may return a Promise; it is awaited.
 */
const fs = require('fs');
const path = require('path');
const rad = require('./radgui.js');

const file = process.argv[2];
if (!file) {
  process.stderr.write('usage: node radworker.js <module file>\n');
  process.exit(2);
}
// the module's own project folder (a referenced library may live outside RAD_PROJECT)
const modulePath = path.resolve(process.env.RAD_PROJECT || process.cwd(), file);
const folder = path.dirname(modulePath);
rad.patchConsole(2);
rad._setWorkerMode();        // GUI helpers have no form in a worker
rad.installGlobals(folder);

// ------------------------------------------------------------------ protocol
function send(obj) {
  let text;
  try {
    text = JSON.stringify(obj);
  } catch (e) {
    text = JSON.stringify({ id: obj.id, error: `result is not JSON serializable: ${e.message}` });
  }
  rad.writeFd(1, text + '\n');
}

function toJson(v) {
  if (v === undefined) return null;
  if (typeof v === 'number' && !Number.isFinite(v)) return null;
  return v;
}

const errText = (e) => (e && e.message ? e.message : String(e));
const answers = new Map();       // answers to our own nested radcalls
let nextCall = 1;
let loadError = null;

/** Handle one stdin line. Returns a Promise when the function is async (reply comes later). */
function processLine(line) {
  let msg;
  try {
    msg = JSON.parse(line);
  } catch (e) {
    send({ id: null, error: `bad request: ${e.message}` });
    return null;
  }
  if (!msg || typeof msg !== 'object') {
    send({ id: null, error: 'bad request: not a JSON object' });
    return null;
  }
  if (!Object.prototype.hasOwnProperty.call(msg, 'func')) {      // answer to a nested radcall
    answers.set(msg.id, msg);
    return null;
  }
  const id = msg.id === undefined ? null : msg.id;
  try {
    if (loadError) throw new Error(`module ${file} failed to load: ${loadError}`);
    const name = String(msg.func || '').split('.').pop();
    const fn = rad.findHandler(name);
    if (!fn) throw new Error(`function '${name}' not found in ${file}`);
    const result = fn(...(Array.isArray(msg.args) ? msg.args : []));
    if (result && typeof result.then === 'function') {
      return Promise.resolve(result).then((r) => send({ id, result: toJson(r) }),
                                          (e) => send({ id, error: errText(e) }));
    }
    send({ id, result: toJson(result) });
  } catch (e) {
    send({ id, error: errText(e) });
  }
  return null;
}

/** radcall for workers: ask the hub on stdout, serve requests until our answer arrives. */
function workerRadcall(name, ...args) {
  const id = `w${nextCall++}`;
  send({ id, call: String(name), args });
  for (;;) {
    if (answers.has(id)) {
      const reply = answers.get(id);
      answers.delete(id);
      if (reply.error !== undefined && reply.error !== null) throw new Error(`radcall ${name}: ${reply.error}`);
      return reply.result === undefined ? null : reply.result;
    }
    const line = rad.readLine();
    if (line === null) throw new Error(`radcall ${name}: RAD Hub closed the worker's input`);
    if (line.trim()) processLine(line);
  }
}
if (process.env.RAD_WORKER === '1') globalThis.radcall = workerRadcall;

// ------------------------------------------------------------------ load the module
function projectModules() {
  try {
    const proj = JSON.parse(fs.readFileSync(path.join(folder, 'project.radproj'), 'utf8'));
    return Array.isArray(proj.modules) ? proj.modules : [];
  } catch (e) {
    return [];
  }
}

try {
  // a form's code file may use functions of the project's modules: load those first
  const mods = projectModules();
  const ext = path.extname(file).toLowerCase();
  if (!mods.some((m) => m.toLowerCase() === path.basename(modulePath).toLowerCase())) {
    for (const m of mods) {
      if (path.extname(m).toLowerCase() !== ext) continue;
      try { rad.loadScript(path.resolve(folder, m)); } catch (e) {
        process.stderr.write(`[radworker] error loading ${m}: ${errText(e)}\n`);
      }
    }
  }
  rad.loadReferences(folder, ext === '.ts' ? '.ts' : '.js');   // libraries this project references
  rad.loadScript(modulePath);
} catch (e) {
  loadError = errText(e);
  process.stderr.write(`[radworker] error loading ${file}: ${e && e.stack ? e.stack : e}\n`);
}

// ------------------------------------------------------------------ serve
// Synchronous reads keep nested radcalls simple; when a function returns a Promise
// the loop yields to the event loop until it settles (requests wait in the pipe).
function pump() {
  for (;;) {
    const line = rad.readLine();
    if (line === null) {
      process.exit(0);
    }
    if (!line.trim()) continue;
    const pending = processLine(line);
    if (pending) {
      pending.then(() => setImmediate(pump));
      return;
    }
  }
}
pump();
