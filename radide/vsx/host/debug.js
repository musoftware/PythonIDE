'use strict';
// vscode.debug: configuration providers, debug adapter descriptor factories and inline adapters.
// The IDE runs the adapter itself (radide/dap.py DapSession); the host only resolves *what* to run:
//   executable  -> the IDE starts it on stdio
//   server/pipe -> the IDE starts relay.js which pipes stdio <-> the socket
//   inline      -> the host serves the in-process implementation on a local TCP port (then like server)

const net = require('net');
const os = require('os');
const path = require('path');
const T = require('./types');

class Debug {
  constructor(host) {
    this.host = host;
    this.configProviders = [];        // {ext, type, provider, triggerKind}
    this.factories = new Map();       // type -> {ext, factory}
    this.trackers = [];
    this.sessions = new Map();        // id -> session object
    this.activeSession = undefined;
    this.events = { start: new T.EventEmitter(), terminate: new T.EventEmitter(), active: new T.EventEmitter(), custom: new T.EventEmitter() };
    this._consoles = new Map();
    this._servers = [];
    this._n = 0;
  }

  registerConfigProvider(ext, type, provider, triggerKind) {
    const e = { ext, type, provider, triggerKind: triggerKind || T.DebugConfigurationProviderTriggerKind.Initial };
    this.configProviders.push(e);
    return new T.Disposable(() => { const i = this.configProviders.indexOf(e); if (i >= 0) this.configProviders.splice(i, 1); });
  }

  registerDescriptorFactory(ext, type, factory) {
    this.factories.set(type, { ext, factory });
    return new T.Disposable(() => { if (this.factories.get(type) && this.factories.get(type).factory === factory) this.factories.delete(type); });
  }

  registerTrackerFactory(ext, type, factory) {
    const e = { ext, type, factory };
    this.trackers.push(e);
    return new T.Disposable(() => { const i = this.trackers.indexOf(e); if (i >= 0) this.trackers.splice(i, 1); });
  }

  console(ext) {
    const out = this.host.createOutputChannel(ext, 'Debug Console');
    return { append: (v) => out.append(String(v)), appendLine: (v) => out.appendLine(String(v)) };
  }

  // debuggers contributed by the enabled extensions: [{type, label, languages, ext, contribution}]
  contributed() {
    const out = [];
    for (const ext of this.host.extensionList()) {
      for (const d of ((ext.packageJSON.contributes || {}).debuggers || [])) {
        if (d && d.type) out.push({ type: d.type, label: d.label || d.type, languages: d.languages || [], ext, contribution: d });
      }
    }
    return out;
  }

  _contribution(type) {
    // a debugger may be declared by several extensions (one with the program, others only adding config)
    const all = this.contributed().filter((d) => d.type === type);
    const withProgram = all.find((d) => d.contribution.program || d.contribution.runtime || d.contribution.windows);
    return withProgram || all[0];
  }

  _executable(type) {
    const d = this._contribution(type);
    if (!d) return undefined;
    let c = d.contribution;
    const plat = process.platform === 'win32' ? 'windows' : process.platform === 'darwin' ? 'osx' : 'linux';
    if (c[plat]) c = { ...c, ...c[plat] };
    if (!c.program) return undefined;
    const program = path.isAbsolute(c.program) ? c.program : path.join(d.ext.path, c.program);
    const args = c.args || [];
    if (c.runtime) {
      const runtime = c.runtime === 'node' ? process.execPath : c.runtime;
      return new T.DebugAdapterExecutable(runtime, [...(c.runtimeArgs || []), program, ...args]);
    }
    return new T.DebugAdapterExecutable(program, args);
  }

  async _activate(type, initial) {
    const h = this.host;
    await h.activateByEvent('onDebug');
    await h.activateByEvent('onDebugResolve:' + type);
    if (initial) { await h.activateByEvent('onDebugInitialConfigurations'); await h.activateByEvent('onDebugDynamicConfigurations:' + type); await h.activateByEvent('onDebugDynamicConfigurations'); }
  }

  _providers(type) { return this.configProviders.filter((p) => p.type === type || p.type === '*'); }

  // ---------------------------------------------------------------------------- variables
  async substitute(value, ctx, type) {
    if (typeof value === 'string') return this._substituteString(value, ctx, type);
    if (Array.isArray(value)) { const out = []; for (const v of value) out.push(await this.substitute(v, ctx, type)); return out; }
    if (value && typeof value === 'object') { const out = {}; for (const k of Object.keys(value)) out[k] = await this.substitute(value[k], ctx, type); return out; }
    return value;
  }

  async _substituteString(s, ctx, type) {
    const re = /\$\{([^}]+)\}/g;
    let m; let out = ''; let last = 0;
    while ((m = re.exec(s))) {
      out += s.substring(last, m.index); last = re.lastIndex;
      out += await this._variable(m[1], ctx, type, m[0]);
    }
    return out + s.substring(last);
  }

  async _variable(name, ctx, type, raw) {
    const file = ctx.file || '';
    const folder = ctx.folder || '';
    switch (name) {
      case 'workspaceFolder': case 'workspaceRoot': return folder;
      case 'workspaceFolderBasename': return path.basename(folder);
      case 'file': return file;
      case 'fileBasename': return path.basename(file);
      case 'fileBasenameNoExtension': return path.basename(file, path.extname(file));
      case 'fileDirname': return path.dirname(file);
      case 'fileExtname': return path.extname(file);
      case 'fileWorkspaceFolder': return folder;
      case 'relativeFile': return folder && file ? path.relative(folder, file) : file;
      case 'relativeFileDirname': return folder && file ? path.relative(folder, path.dirname(file)) : path.dirname(file);
      case 'cwd': return folder || process.cwd();
      case 'lineNumber': return String((ctx.line || 0) + 1);
      case 'selectedText': return ctx.selectedText || '';
      case 'pathSeparator': case '/': return path.sep;
      case 'userHome': return os.homedir();
      case 'execPath': return process.execPath;
      case 'defaultBuildTask': return '';
      default: break;
    }
    if (name.startsWith('env:')) return process.env[name.substring(4)] || '';
    if (name.startsWith('config:')) { const v = this.host.getConfiguration().get(name.substring(7)); return v === undefined ? '' : String(v); }
    if (name.startsWith('command:')) {
      let cmd = name.substring(8);
      const d = this._contribution(type);
      const vars = d && d.contribution.variables;
      if (vars && vars[cmd]) cmd = vars[cmd];
      const r = await this.host.executeCommand(cmd, [ctx.config || {}]);
      if (r === undefined || r === null) throw new Error('cancelled');
      return String(r);
    }
    if (name.startsWith('input:')) return raw;
    return raw;
  }

  // ---------------------------------------------------------------------------- resolve what to run
  async resolve(params) {
    const h = this.host;
    let type = params.type || (params.config && params.config.type) || '';
    let config = params.config ? { ...params.config } : null;
    const folder = params.folder ? h.workspaceFolderOf(T.Uri.file(params.folder)) || { uri: T.Uri.file(params.folder), name: path.basename(params.folder), index: 0 } : h.workspaceFolders()[0];
    const token = new T.CancellationTokenSource().token;
    if (type) await this._activate(type, !config);
    let resolved = false;
    if (!config) {
      // like F5 without launch.json: providers fill an empty configuration from the active editor
      for (const p of this._providers(type)) {
        if (typeof p.provider.resolveDebugConfiguration !== 'function') continue;
        try {
          const r = await p.provider.resolveDebugConfiguration(folder, {}, token);
          if (r && r.type) { config = r; resolved = true; break; }
        } catch (e) { h.log(p.ext, 'resolveDebugConfiguration failed: ' + (e && e.stack || e)); }
      }
    }
    if (!config) {
      for (const p of this._providers(type)) {
        if (typeof p.provider.provideDebugConfigurations !== 'function' || p.triggerKind !== T.DebugConfigurationProviderTriggerKind.Initial) continue;
        try { const list = await p.provider.provideDebugConfigurations(folder, token); if (list && list.length) { config = list[0]; break; } } catch (e) { h.log(p.ext, 'provideDebugConfigurations failed: ' + e); }
      }
    }
    if (!config) {
      const d = this._contribution(type);
      const init = d && d.contribution.initialConfigurations;
      if (Array.isArray(init) && init.length) config = { ...init[0] };
    }
    if (!config) return { error: 'no debug configuration for type ' + type };
    type = config.type || type;
    if (!config.type) config.type = type;
    if (!config.request) config.request = 'launch';
    if (!config.name) config.name = type;
    if (!resolved) {
      for (const p of this._providers(type)) {
        if (typeof p.provider.resolveDebugConfiguration !== 'function') continue;
        try {
          const r = await p.provider.resolveDebugConfiguration(folder, config, token);
          if (r === undefined || r === null) return { cancelled: true };
          config = r;
        } catch (e) { h.log(p.ext, 'resolveDebugConfiguration failed: ' + e); }
      }
    }
    const ctx = { folder: folder ? folder.uri.fsPath : '', file: params.file || '', line: params.line || 0, selectedText: params.selectedText || '', config };
    try { config = await this.substitute(config, ctx, type); } catch (e) { return { cancelled: true, error: String(e && e.message || e) }; }
    for (const p of this._providers(type)) {
      if (typeof p.provider.resolveDebugConfigurationWithSubstitutedVariables !== 'function') continue;
      try {
        const r = await p.provider.resolveDebugConfigurationWithSubstitutedVariables(folder, config, token);
        if (r === undefined || r === null) return { cancelled: true };
        config = r;
      } catch (e) { h.log(p.ext, 'resolveDebugConfigurationWithSubstitutedVariables failed: ' + e); }
    }
    const sessionId = 'vsxdbg-' + (++this._n);
    const session = this._session(sessionId, config, folder);
    let desc = this._executable(type);
    const f = this.factories.get(type);
    if (f) {
      try {
        const d = await f.factory.createDebugAdapterDescriptor(session, desc);
        if (d) desc = d;
      } catch (e) { h.log(f.ext, 'createDebugAdapterDescriptor failed: ' + (e && e.stack || e)); return { error: 'debug adapter factory failed: ' + e }; }
    }
    if (!desc) return { error: `the debugger '${type}' has no adapter RAD IDE can run` };
    this.sessions.set(sessionId, session);
    return { sessionId, config, adapter: await this._adapter(desc, sessionId) };
  }

  _session(id, config, folder) {
    const host = this.host;
    return {
      id, type: config.type, name: config.name, configuration: config, workspaceFolder: folder, parentSession: undefined,
      customRequest: (command, args) => host.rpc.request('debug/customRequest', { sessionId: id, command, args: args || {} }),
      getDebugProtocolBreakpoint: () => Promise.resolve(undefined),
    };
  }

  async _adapter(desc, sessionId) {
    if (desc instanceof T.DebugAdapterExecutable || (desc.command && !desc.implementation)) {
      const o = desc.options || {};
      return { kind: 'executable', command: desc.command === 'node' ? process.execPath : desc.command, args: desc.args || [], cwd: o.cwd, env: o.env };
    }
    if (desc instanceof T.DebugAdapterServer || desc.port) return { kind: 'server', host: desc.host || '127.0.0.1', port: desc.port };
    if (desc instanceof T.DebugAdapterNamedPipeServer || desc.path) return { kind: 'pipe', path: desc.path };
    if (desc instanceof T.DebugAdapterInlineImplementation || desc.implementation) return { kind: 'server', host: '127.0.0.1', port: await this._serveInline(desc.implementation, sessionId) };
    throw new Error('unknown debug adapter descriptor');
  }

  _serveInline(impl, sessionId) {
    return new Promise((resolve, reject) => {
      const server = net.createServer((sock) => {
        let buf = Buffer.alloc(0);
        const sub = impl.onDidSendMessage((m) => {
          if (m && m.type === 'event' && m.event && !['output', 'stopped', 'continued', 'initialized', 'terminated', 'exited', 'thread', 'breakpoint', 'module', 'loadedSource', 'process', 'capabilities', 'progressStart', 'progressUpdate', 'progressEnd', 'invalidated', 'memory'].includes(m.event)) {
            this.events.custom.fire({ session: this.sessions.get(sessionId), event: m.event, body: m.body });
          }
          const b = Buffer.from(JSON.stringify(m), 'utf8');
          try { sock.write('Content-Length: ' + b.length + '\r\n\r\n'); sock.write(b); } catch (_) { /* closed */ }
        });
        sock.on('data', (chunk) => {
          buf = Buffer.concat([buf, chunk]);
          for (;;) {
            const he = buf.indexOf('\r\n\r\n');
            if (he < 0) return;
            const mm = /content-length:\s*(\d+)/i.exec(buf.slice(0, he).toString('ascii'));
            const len = mm ? parseInt(mm[1], 10) : 0;
            if (buf.length < he + 4 + len) return;
            const body = buf.slice(he + 4, he + 4 + len).toString('utf8');
            buf = buf.slice(he + 4 + len);
            try { impl.handleMessage(JSON.parse(body)); } catch (e) { this.host.logHost('inline debug adapter: ' + (e && e.stack || e)); }
          }
        });
        const done = () => { try { sub.dispose(); } catch (_) { /* */ } try { impl.dispose && impl.dispose(); } catch (_) { /* */ } server.close(); };
        sock.on('close', done);
        sock.on('error', done);
      });
      server.on('error', reject);
      server.listen(0, '127.0.0.1', () => resolve(server.address().port));
      this._servers.push(server);
    });
  }

  // ---------------------------------------------------------------------------- sessions (from the IDE)
  started(p) {
    const s = this.sessions.get(p.sessionId) || this._session(p.sessionId, p.config || {}, this.host.workspaceFolders()[0]);
    this.sessions.set(p.sessionId, s);
    this.activeSession = s;
    this.events.start.fire(s);
    this.events.active.fire(s);
  }

  terminated(p) {
    const s = this.sessions.get(p.sessionId);
    if (!s) return;
    this.sessions.delete(p.sessionId);
    if (this.activeSession === s) { this.activeSession = undefined; this.events.active.fire(undefined); }
    this.events.terminate.fire(s);
  }

  customEvent(p) {
    const s = this.sessions.get(p.sessionId);
    if (s) this.events.custom.fire({ session: s, event: p.event, body: p.body });
  }

  async start(folder, nameOrConfig, _options) {
    let config = nameOrConfig;
    if (typeof nameOrConfig === 'string') config = { name: nameOrConfig };
    const ok = await this.host.rpc.request('debug/start', { config, folder: folder && folder.uri ? folder.uri.fsPath : undefined });
    return !!ok;
  }

  dispose() { for (const s of this._servers) { try { s.close(); } catch (_) { /* */ } } }
}

module.exports = { Debug };
