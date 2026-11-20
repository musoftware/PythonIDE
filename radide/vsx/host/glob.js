'use strict';
// Minimal glob matching for document selectors, findFiles and file system watchers:
// **, *, ?, {a,b}, [abc], [!abc]; paths are compared with forward slashes, case-insensitive on Windows.

const cache = new Map();

function globToRegExp(glob) {
  const key = glob;
  if (cache.has(key)) return cache.get(key);
  let re = '';
  let inGroup = 0;
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*') {
      if (glob[i + 1] === '*') {
        // "**/" matches zero or more folders, "**" at the end matches everything
        i++;
        if (glob[i + 1] === '/') { i++; re += '(?:.*/)?'; } else re += '.*';
      } else re += '[^/]*';
    } else if (c === '?') re += '[^/]';
    else if (c === '{') { inGroup++; re += '(?:'; } else if (c === '}' && inGroup) { inGroup--; re += ')'; } else if (c === ',' && inGroup) re += '|';
    else if (c === '[') {
      const j = glob.indexOf(']', i + 1);
      if (j < 0) { re += '\\['; continue; }
      let cls = glob.substring(i + 1, j);
      if (cls[0] === '!') cls = '^' + cls.substring(1);
      re += '[' + cls.replace(/\\/g, '\\\\') + ']';
      i = j;
    } else if ('\\^$.|+()'.includes(c)) re += '\\' + c;
    else if (c === '/') re += '/';
    else re += c;
  }
  const r = new RegExp('^' + re + '$', process.platform === 'win32' ? 'i' : '');
  cache.set(key, r);
  return r;
}

function norm(p) { return String(p).replace(/\\/g, '/'); }

// pattern: string glob or {base|baseUri, pattern}; path: absolute fs path
function matchGlob(pattern, fsPath) {
  if (!pattern) return false;
  const p = norm(fsPath);
  if (typeof pattern === 'string') {
    const g = norm(pattern);
    const re = globToRegExp(g);
    if (re.test(p)) return true;
    if (!g.startsWith('/') && !/^[a-zA-Z]:/.test(g) && !g.startsWith('**')) {
      // relative globs ("*.yaml", "src/**") are matched against any path suffix (like VS Code selectors)
      const re2 = globToRegExp('**/' + g);
      return re2.test(p);
    }
    return false;
  }
  const base = norm(pattern.baseUri ? pattern.baseUri.fsPath : (pattern.base || ''));
  if (!base) return matchGlob(pattern.pattern, fsPath);
  const bl = base.replace(/\/$/, '');
  const cmp = process.platform === 'win32' ? (a, b) => a.toLowerCase().startsWith(b.toLowerCase()) : (a, b) => a.startsWith(b);
  if (!cmp(p, bl + '/')) return false;
  return globToRegExp(norm(pattern.pattern)).test(p.substring(bl.length + 1));
}

module.exports = { globToRegExp, matchGlob };
