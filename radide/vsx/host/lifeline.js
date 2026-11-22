'use strict';
// The extension host must never outlive RAD IDE (an IDE crash, os._exit in a test, Task Manager): orphaned hosts
// keep their language servers / terminals / debug adapters alive and exhaust the machine.
//   * stdin (the JSON-RPC pipe from the IDE) ends or closes, or a write to stdout fails (EPIPE) -> shut down;
//   * parent watchdog: RADIDE_PARENT_PID (set by radide/vsx/bridge.py; process.ppid otherwise) is checked every
//     WATCH_MS with process.kill(pid, 0); gone -> shut down (the stdin pipe can stay open when a grandchild
//     inherited its handle);
//   * every child process an extension starts (child_process.spawn / fork / exec / execFile) is tracked and its
//     whole tree killed on shutdown (taskkill /T /F on Windows, SIGKILL of the process group elsewhere).
// shutdown(reason) deactivates the extensions with a short timeout first (VS Code gives deactivate() 5 s).
const cp = require('child_process');

const WATCH_MS = 2000;
const DEACTIVATE_MS = 2500;
const children = new Set();
let state = { down: false, deactivate: null, log: () => {} };

function track(child) {
  if (!child || typeof child.pid !== 'number') return child;
  children.add(child);
  const drop = () => children.delete(child);
  child.once('exit', drop);
  child.once('error', drop);
  return child;
}

// wrap the spawning functions once (extensions and the libraries they bundle get the wrapped ones)
function patchChildProcess() {
  if (cp.__radideTracked) return;
  cp.__radideTracked = true;
  for (const name of ['spawn', 'fork', 'exec', 'execFile']) {
    const orig = cp[name];
    if (typeof orig !== 'function') continue;
    cp[name] = function (...args) { return track(orig.apply(this, args)); };
  }
}

function killTree(pid) {
  if (!pid) return;
  try {
    if (process.platform === 'win32') {
      cp.spawnSync('taskkill', ['/T', '/F', '/PID', String(pid)], { windowsHide: true, stdio: 'ignore', timeout: 5000 });
    } else {
      try { process.kill(-pid, 'SIGKILL'); } catch (_) { process.kill(pid, 'SIGKILL'); }
    }
  } catch (_) { /* already gone */ }
}

function killChildren() {
  for (const c of [...children]) {
    if (c.exitCode === null && c.signalCode === null) killTree(c.pid);
    children.delete(c);
  }
}

function alive(pid) {
  try { process.kill(pid, 0); return true; } catch (e) { return e && e.code === 'EPERM'; }
}

async function shutdown(reason, code = 0) {
  if (state.down) return;
  state.down = true;
  try { state.log(`extension host shutting down: ${reason}`); } catch (_) { /* */ }
  const hardStop = setTimeout(() => { killChildren(); process.exit(code); }, DEACTIVATE_MS + 1500);
  try {
    if (state.deactivate) {
      await Promise.race([Promise.resolve().then(state.deactivate), new Promise((r) => setTimeout(r, DEACTIVATE_MS))]);
    }
  } catch (_) { /* */ }
  killChildren();
  clearTimeout(hardStop);
  process.exit(code);
}

function install({ deactivate, log } = {}) {
  state.deactivate = deactivate || null;
  state.log = log || state.log;
  patchChildProcess();
  process.stdin.on('end', () => shutdown('the IDE closed the pipe'));
  process.stdin.on('close', () => shutdown('the IDE closed the pipe'));
  process.stdout.on('error', (e) => shutdown('cannot write to the IDE (' + (e && e.code) + ')'));
  const parent = parseInt(process.env.RADIDE_PARENT_PID || '', 10) || process.ppid;
  if (parent && parent > 0) {
    const t = setInterval(() => { if (!alive(parent)) shutdown(`the IDE process ${parent} is gone`); }, WATCH_MS);
    if (t.unref) t.unref();
  }
  process.on('exit', () => killChildren());
  for (const sig of ['SIGTERM', 'SIGINT', 'SIGHUP', 'SIGBREAK']) {
    try { process.on(sig, () => shutdown('signal ' + sig)); } catch (_) { /* not on this platform */ }
  }
}

module.exports = { install, shutdown, killChildren, track, children, patch: patchChildProcess };
