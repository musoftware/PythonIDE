// Test helper (MIT): a fake Claude Code CLI for the Claude Code extension running in RAD IDE.
//   node claude_mcp_client.js <claude config dir> [workspace folder that the lock file must list]
// Picks the newest <config>/ide/*.lock (written by the extension) - the one whose workspaceFolders contain the
// given folder when one is given -, connects to the extension's MCP WebSocket server with the auth token and
// then works as a pipe: every stdin line is a JSON request
//   {"id": 1, "tool": "openFile", "args": {...}}     -> tools/call
//   {"id": 2, "method": "tools/list", "params": {}}  -> any MCP request
//   {"quit": true}
// and every stdout line is a JSON event:
//   {"event":"connected","lock":{...}}  {"event":"reply","id":1,"result":...|"error":"..."}
//   {"event":"notification","method":"selection_changed","params":{...}}
// No real Claude conversation is started (nothing talks to Anthropic's servers).
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const [cfg, wantFolder] = process.argv.slice(2);
const out = (o) => process.stdout.write(JSON.stringify(o) + '\n');
const norm = (p) => path.resolve(String(p || '')).toLowerCase();

function lockFile() {
  const dir = path.join(cfg, 'ide');
  const files = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.lock')) : [];
  const locks = files.map((x) => path.join(dir, x)).map((f) => {
    try { return { file: f, mtime: fs.statSync(f).mtimeMs, port: parseInt(path.basename(f), 10), ...JSON.parse(fs.readFileSync(f, 'utf8')) }; } catch (_) { return null; }
  }).filter(Boolean).sort((a, b) => b.mtime - a.mtime);
  const hit = wantFolder ? locks.find((l) => (l.workspaceFolders || []).some((w) => norm(w) === norm(wantFolder))) : locks[0];
  if (!hit) throw new Error('no matching lock file in ' + dir + ': ' + JSON.stringify(locks.map((l) => l.workspaceFolders)));
  return hit;
}

(async () => {
  const lock = lockFile();
  const ws = new WebSocket(`ws://127.0.0.1:${lock.port}`, { headers: { 'x-claude-code-ide-authorization': lock.authToken } });
  let id = 0;
  const pending = new Map();
  const send = (method, params) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ jsonrpc: '2.0', id: i, method, params })); });
  ws.onmessage = (ev) => {
    const msg = JSON.parse(typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString('utf8'));
    if (msg.id !== undefined && pending.has(msg.id)) {
      const p = pending.get(msg.id); pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error.message || JSON.stringify(msg.error))); else p.resolve(msg.result);
    } else if (msg.method) out({ event: 'notification', method: msg.method, params: msg.params });
    else if (msg.id !== undefined) ws.send(JSON.stringify({ jsonrpc: '2.0', id: msg.id, result: {} }));   // server -> client request (ping ...)
  };
  ws.onerror = (e) => { out({ event: 'error', error: String(e && e.message || e) }); process.exit(2); };
  ws.onclose = () => { out({ event: 'closed' }); process.exit(0); };
  await new Promise((r) => { ws.onopen = r; });
  const init = await send('initialize', { protocolVersion: '2025-06-18', capabilities: { roots: {} }, clientInfo: { name: 'claude-code', version: '2.1.330' } });
  ws.send(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }));
  const { authToken, ...shown } = lock; void authToken;
  out({ event: 'connected', lock: shown, server: init && init.serverInfo });
  const rl = readline.createInterface({ input: process.stdin });
  rl.on('line', async (line) => {
    let req;
    try { req = JSON.parse(line); } catch (_) { return; }
    if (req.quit) { ws.close(); setTimeout(() => process.exit(0), 100); return; }
    try {
      const result = req.tool ? await send('tools/call', { name: req.tool, arguments: req.args || {} }) : await send(req.method, req.params || {});
      out({ event: 'reply', id: req.id, result });
    } catch (e) { out({ event: 'reply', id: req.id, error: String(e && e.message || e) }); }
  });
})().catch((e) => { out({ event: 'error', error: String(e && e.stack || e) }); process.exit(1); });
