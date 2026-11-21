// Test helper (MIT): acts like the Claude Code CLI towards the Claude Code extension running in RAD IDE.
//   node claude_open_diff.js <claude config dir> <old file> <new contents file> <tab name>
// Reads <config>/ide/*.lock (written by the extension), connects to its MCP WebSocket server with the auth
// token, calls the "openDiff" tool and prints one JSON line per event:
//   {"event":"connected"} ... {"event":"result","result":{...}}  or {"event":"error","error":"..."}
const fs = require('fs');
const path = require('path');

const [cfg, oldFile, newContentsFile, tabName] = process.argv.slice(2);
const out = (o) => process.stdout.write(JSON.stringify(o) + '\n');

function lockFile() {
  const dir = path.join(cfg, 'ide');
  const files = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.lock')) : [];
  if (!files.length) throw new Error('no lock file in ' + dir);
  const f = files.map((x) => path.join(dir, x)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
  return { port: parseInt(path.basename(f), 10), ...JSON.parse(fs.readFileSync(f, 'utf8')) };
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
    } else if (msg.method) out({ event: 'notification', method: msg.method });
  };
  ws.onerror = (e) => { out({ event: 'error', error: String(e && e.message || e) }); process.exit(2); };
  ws.onclose = () => { out({ event: 'closed' }); };
  await new Promise((r) => { ws.onopen = r; });
  out({ event: 'connected', port: lock.port, ideName: lock.ideName });
  await send('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'radide-test', version: '1.0.0' } });
  ws.send(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }));
  const tools = await send('tools/list', {});
  out({ event: 'tools', names: (tools.tools || []).map((t) => t.name) });
  const contents = fs.readFileSync(newContentsFile, 'utf8');
  out({ event: 'calling' });
  const result = await send('tools/call', { name: 'openDiff', arguments: { old_file_path: oldFile, new_file_path: oldFile, new_file_contents: contents, tab_name: tabName } });
  out({ event: 'result', result });
  // the CLI writes the file itself and then closes the diff tab with the close_tab tool
  const closed = await send('tools/call', { name: 'close_tab', arguments: { tab_name: tabName } });
  out({ event: 'close_tab', result: closed });
  ws.close();
  setTimeout(() => process.exit(0), 100);
})().catch((e) => { out({ event: 'error', error: String(e && e.stack || e) }); process.exit(1); });
