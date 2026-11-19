'use strict';
/*
 * RAD IDE - RAD Hub worker for JavaScript / TypeScript modules.
 *
 *   node radworker.js <module file>        (cwd = project folder)
 *
 * Loads the module in the global scope and serves its top-level functions:
 *   stdin : {"id": 7, "func": "add", "args": [2, 3]}
 *   stdout: {"id": 7, "result": 5}   or   {"id": 7, "error": "message"}
 * Logs (console.log too) go to stderr so stdout stays clean JSON lines.
 * Functions may return a Promise; it is awaited.
 */
const path = require('path');
const readline = require('readline');
const rad = require('./radgui.js');

const file = process.argv[2];
if (!file) {
  process.stderr.write('usage: node radworker.js <module file>\n');
  process.exit(2);
}
const folder = process.env.RAD_PROJECT || process.cwd();
rad.patchConsole(2);
rad._setOutFd(2);            // GUI helpers have no IDE in a worker - keep stdout for replies
rad.installGlobals(folder);
let loadError = null;
try {
  rad.loadScript(path.resolve(folder, file));
} catch (e) {
  loadError = e && e.message ? e.message : String(e);
  process.stderr.write(`[radworker] error loading ${file}: ${e && e.stack ? e.stack : e}\n`);
}

function reply(obj) {
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

async function handle(line) {
  let req;
  try {
    req = JSON.parse(line);
  } catch (e) {
    reply({ id: null, error: `bad request: ${e.message}` });
    return;
  }
  const id = req.id === undefined ? null : req.id;
  try {
    if (loadError) throw new Error(`module ${file} failed to load: ${loadError}`);
    const name = String(req.func || '').split('.').pop();
    const fn = rad.findHandler(name);
    if (!fn) throw new Error(`function '${name}' not found in ${file}`);
    const args = Array.isArray(req.args) ? req.args : [];
    let result = fn(...args);
    if (result && typeof result.then === 'function') result = await result;
    reply({ id, result: toJson(result) });
  } catch (e) {
    reply({ id, error: e && e.message ? e.message : String(e) });
  }
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });
let chain = Promise.resolve();
rl.on('line', (line) => {
  if (!line.trim()) return;
  chain = chain.then(() => handle(line));          // keep replies in request order
});
rl.on('close', () => { chain.then(() => process.exit(0)); });
