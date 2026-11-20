// RAD IDE test debug adapter (MIT): "runs" a text file line by line. Each line "name = value" sets a
// variable. Works on stdio (node adapter.js) or in-process (MiniDebugSession for DebugAdapterInlineImplementation).
'use strict';
const fs = require('fs');

class MiniDebugSession {
  constructor(send) {
    this._send = send;           // (message) => void
    this._seq = 1;
    this.lines = [];
    this.line = 0;
    this.breakpoints = new Map();   // path -> Set(line 1-based)
    this.program = '';
    this.vars = {};
    this.stopOnEntry = false;
  }

  event(event, body) { this._send({ seq: this._seq++, type: 'event', event, body }); }
  respond(req, body, success = true, message) { this._send({ seq: this._seq++, type: 'response', request_seq: req.seq, command: req.command, success, message, body }); }

  handle(req) {
    const a = req.arguments || {};
    switch (req.command) {
      case 'initialize':
        this.respond(req, { supportsConfigurationDoneRequest: true, supportsEvaluateForHovers: true, exceptionBreakpointFilters: [] });
        this.event('initialized');
        break;
      case 'launch':
        this.program = a.program;
        this.stopOnEntry = !!a.stopOnEntry;
        try { this.lines = fs.readFileSync(this.program, 'utf8').split(/\r?\n/); } catch (e) { this.respond(req, undefined, false, 'cannot read ' + this.program); return; }
        this.respond(req);
        this.event('output', { category: 'console', output: `mini-debug: running ${this.program} (${this.lines.length} lines)\n` });
        break;
      case 'setBreakpoints': {
        const lines = (a.breakpoints || []).map((b) => b.line);
        this.breakpoints.set(String(a.source && a.source.path).toLowerCase(), new Set(lines));
        this.respond(req, { breakpoints: lines.map((l) => ({ verified: true, line: l })) });
        break;
      }
      case 'setExceptionBreakpoints': this.respond(req, {}); break;
      case 'configurationDone':
        this.respond(req);
        this.line = 0;
        if (this.stopOnEntry) this.stop('entry'); else this.run(false);
        break;
      case 'threads': this.respond(req, { threads: [{ id: 1, name: 'main' }] }); break;
      case 'stackTrace':
        this.respond(req, { stackFrames: [{ id: 1, name: 'main', line: this.line + 1, column: 1, source: { path: this.program, name: require('path').basename(this.program) } }], totalFrames: 1 });
        break;
      case 'scopes': this.respond(req, { scopes: [{ name: 'Locals', variablesReference: 1, expensive: false }] }); break;
      case 'variables':
        this.respond(req, { variables: Object.entries(this.vars).map(([name, value]) => ({ name, value: String(value), type: typeof value, variablesReference: 0 })) });
        break;
      case 'continue': this.respond(req, { allThreadsContinued: true }); this.run(false); break;
      case 'next': case 'stepIn': case 'stepOut': this.respond(req); this.run(true); break;
      case 'evaluate': {
        const v = this.vars[a.expression];
        this.respond(req, { result: v === undefined ? `undefined (${a.expression})` : String(v), variablesReference: 0 });
        break;
      }
      case 'miniDebug/lineCount': this.respond(req, { lines: this.lines.length }); break;
      case 'disconnect': case 'terminate': this.respond(req); this.event('terminated'); break;
      default: this.respond(req, undefined, false, 'unsupported request ' + req.command);
    }
  }

  exec(i) {
    const m = /^\s*(\w+)\s*=\s*(.*)$/.exec(this.lines[i] || '');
    if (m) this.vars[m[1]] = isNaN(Number(m[2])) ? m[2] : Number(m[2]);
  }

  stop(reason) { this.event('stopped', { reason, threadId: 1, allThreadsStopped: true }); }

  run(step) {
    const bps = this.breakpoints.get(String(this.program).toLowerCase()) || new Set();
    this.exec(this.line);
    for (let i = this.line + 1; i < this.lines.length; i++) {
      if (step || bps.has(i + 1)) { this.line = i; this.stop(step ? 'step' : 'breakpoint'); return; }
      this.exec(i);
    }
    this.event('output', { category: 'console', output: 'mini-debug: done ' + JSON.stringify(this.vars) + '\n' });
    this.event('custom/finished', { vars: this.vars });
    this.event('exited', { exitCode: 0 });
    this.event('terminated');
  }
}

// VS Code's inline adapter interface (vscode.DebugAdapter)
class InlineAdapter {
  constructor(vscode) {
    this._emitter = new vscode.EventEmitter();
    this.onDidSendMessage = this._emitter.event;
    this.session = new MiniDebugSession((m) => this._emitter.fire(m));
  }
  handleMessage(m) { this.session.handle(m); }
  dispose() {}
}

module.exports = { MiniDebugSession, InlineAdapter };

if (require.main === module) {          // stdio adapter
  let buf = Buffer.alloc(0);
  const s = new MiniDebugSession((m) => { const b = Buffer.from(JSON.stringify(m)); process.stdout.write('Content-Length: ' + b.length + '\r\n\r\n'); process.stdout.write(b); if (m.event === 'terminated') setTimeout(() => process.exit(0), 50); });
  process.stdin.on('data', (c) => {
    buf = Buffer.concat([buf, c]);
    for (;;) {
      const he = buf.indexOf('\r\n\r\n');
      if (he < 0) return;
      const len = parseInt(/content-length:\s*(\d+)/i.exec(buf.slice(0, he).toString())[1], 10);
      if (buf.length < he + 4 + len) return;
      const msg = JSON.parse(buf.slice(he + 4, he + 4 + len).toString());
      buf = buf.slice(he + 4 + len);
      s.handle(msg);
    }
  });
}
