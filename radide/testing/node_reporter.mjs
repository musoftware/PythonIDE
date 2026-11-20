// RAD IDE Test Explorer reporter for "node --test" (radide/testing/__init__.py).
// One JSON line per finished test: @@RADTEST@@{"file", "line", "name", "state", "duration", "message"}
export default async function* reporter(source) {
  for await (const ev of source) {
    if (ev.type === 'test:pass' || ev.type === 'test:fail') {
      const d = ev.data || {};
      const det = d.details || {};
      if (det.type === 'suite') continue;
      const err = det.error;
      let state = ev.type === 'test:pass' ? 'passed' : 'failed';
      if (d.skip !== undefined || d.todo !== undefined) state = 'skipped';
      let message = '';
      if (err) {
        const c = err.cause || err;
        message = String((c && (c.stack || c.message)) || err.message || err);
      }
      yield '\n@@RADTEST@@' + JSON.stringify({ file: d.file || '', line: d.line || 0, name: d.name || '',
        state, duration: (det.duration_ms || 0) / 1000, message }) + '\n';
    } else if (ev.type === 'test:stdout' || ev.type === 'test:stderr') {
      yield (ev.data && ev.data.message) || '';
    }
  }
}
