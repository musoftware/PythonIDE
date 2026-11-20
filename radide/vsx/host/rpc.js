'use strict';
// JSON-RPC 2.0 over the host's real stdout / stdin with LSP-style "Content-Length" framing.
// Extensions never see this stream: main.js redirects process.stdout / console to stderr first.

class Rpc {
  constructor(input, write) {
    this._write = write;            // (string) => void, the real stdout writer
    this._buf = Buffer.alloc(0);
    this._id = 0;
    this._pending = new Map();      // id -> {resolve, reject, timer}
    this.requestHandlers = new Map();   // method -> async (params) => result
    this.notificationHandlers = new Map();
    this.onError = (e) => { try { process.stderr.write('[rpc] ' + (e && e.stack || e) + '\n'); } catch (_) { /* */ } };
    input.on('data', (chunk) => this._onData(chunk));
  }

  _onData(chunk) {
    this._buf = Buffer.concat([this._buf, chunk]);
    for (;;) {
      const headEnd = this._buf.indexOf('\r\n\r\n');
      if (headEnd < 0) return;
      const head = this._buf.slice(0, headEnd).toString('ascii');
      const m = /content-length:\s*(\d+)/i.exec(head);
      const len = m ? parseInt(m[1], 10) : 0;
      if (this._buf.length < headEnd + 4 + len) return;
      const body = this._buf.slice(headEnd + 4, headEnd + 4 + len).toString('utf8');
      this._buf = this._buf.slice(headEnd + 4 + len);
      let msg;
      try { msg = JSON.parse(body); } catch (e) { this.onError(e); continue; }
      this._dispatch(msg);
    }
  }

  _send(msg) {
    let body;
    try {
      body = JSON.stringify(msg, (k, v) => (typeof v === 'bigint' ? Number(v) : v));
    } catch (e) {             // circular structures from an extension: send what we can
      body = JSON.stringify({ jsonrpc: '2.0', id: msg.id, error: { code: -32603, message: 'unserializable: ' + e.message } });
    }
    const b = Buffer.from(body, 'utf8');
    this._write('Content-Length: ' + b.length + '\r\n\r\n');
    this._write(b);
  }

  async _dispatch(msg) {
    if (msg.id !== undefined && msg.method === undefined) {          // response
      const p = this._pending.get(msg.id);
      if (!p) return;
      this._pending.delete(msg.id);
      if (p.timer) clearTimeout(p.timer);
      if (msg.error) p.reject(new Error(msg.error.message || 'error')); else p.resolve(msg.result);
      return;
    }
    if (msg.id !== undefined) {                                        // request
      const h = this.requestHandlers.get(msg.method);
      if (!h) { this._send({ jsonrpc: '2.0', id: msg.id, error: { code: -32601, message: 'unknown method ' + msg.method } }); return; }
      try {
        const result = await h(msg.params || {});
        this._send({ jsonrpc: '2.0', id: msg.id, result: result === undefined ? null : result });
      } catch (e) {
        this.onError(e);
        this._send({ jsonrpc: '2.0', id: msg.id, error: { code: -32603, message: String(e && e.message || e) } });
      }
      return;
    }
    const h = this.notificationHandlers.get(msg.method);                // notification
    if (h) { try { await h(msg.params || {}); } catch (e) { this.onError(e); } }
  }

  request(method, params, timeoutMs) {
    const id = ++this._id;
    return new Promise((resolve, reject) => {
      const p = { resolve, reject, timer: null };
      if (timeoutMs) p.timer = setTimeout(() => { this._pending.delete(id); resolve(undefined); }, timeoutMs);
      this._pending.set(id, p);
      this._send({ jsonrpc: '2.0', id, method, params });
    });
  }

  notify(method, params) { this._send({ jsonrpc: '2.0', method, params }); }
}

module.exports = { Rpc };
