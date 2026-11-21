// Minimal stand-ins for react / react-native / expo modules: enough to run the generated screen classes and
// radfx.js in Node (check_targets.py bundles them with esbuild). Animated runs on real timers.
const listeners = new Set();
class Value {
  constructor(v) { this._v = v; this._l = {}; this._n = 0; }
  setValue(v) { this._v = v; for (const f of Object.values(this._l)) f({ value: v }); }
  addListener(f) { const id = String(++this._n); this._l[id] = f; return id; }
  removeListener(id) { delete this._l[id]; }
  interpolate(cfg) { return { _interp: cfg, _src: this }; }
}
function timing(val, cfg) {
  let h = null;
  return {
    start(cb) {
      const from = val._v, t0 = Date.now(), d = Math.max(1, cfg.duration || 1), e = cfg.easing || ((x) => x);
      h = setInterval(() => {
        const f = Math.min(1, (Date.now() - t0) / d);
        val.setValue(from + (cfg.toValue - from) * e(f));
        if (f >= 1) { clearInterval(h); h = null; cb && cb({ finished: true }); }
      }, 10);
    },
    stop() { if (h) { clearInterval(h); h = null; } },
  };
}
function delay(ms) {
  let h = null;
  return { start(cb) { h = setTimeout(() => cb && cb({ finished: true }), ms); }, stop() { clearTimeout(h); } };
}
function sequence(arr) {
  let i = 0, cur = null, stopped = false;
  return {
    start(cb) {
      const next = () => {
        if (stopped) return;
        if (i >= arr.length) { cb && cb({ finished: true }); return; }
        cur = arr[i++]; cur.start(({ finished }) => (finished ? next() : cb && cb({ finished: false })));
      };
      next();
    },
    stop() { stopped = true; if (cur) cur.stop(); },
  };
}
function parallel(arr) {
  return {
    start(cb) {
      let left = arr.length;
      if (!left) { cb && cb({ finished: true }); return; }
      arr.forEach((a) => a.start(() => { left -= 1; if (left === 0) cb && cb({ finished: true }); }));
    },
    stop() { arr.forEach((a) => a.stop()); },
  };
}
function loop(a, cfg) {
  const n = cfg && cfg.iterations ? cfg.iterations : Infinity;
  let k = 0, stopped = false;
  return {
    start(cb) { const go = () => { if (stopped) return; if (k++ >= n) { cb && cb({ finished: true }); return; } a.start(go); }; go(); },
    stop() { stopped = true; a.stop(); },
  };
}
const lin = (x) => x;
const Easing = {
  linear: lin, quad: (x) => x * x, sin: (x) => 1 - Math.cos((x * Math.PI) / 2), bounce: lin,
  in: (f) => f, out: (f) => (x) => 1 - f(1 - x), inOut: (f) => (x) => (x < 0.5 ? f(2 * x) / 2 : 1 - f(2 * (1 - x)) / 2),
  back: () => (x) => x, elastic: () => lin,
};
export const Animated = { Value, timing, delay, sequence, parallel, loop, View: 'Animated.View' };
export { Easing };
export const Platform = { OS: 'web' };
export const Dimensions = { get: () => ({ width: Number(globalThis.WIN_W || 412), height: Number(globalThis.WIN_H || 867) }) };
export const AccessibilityInfo = { isReduceMotionEnabled: () => Promise.resolve(!!globalThis.REDUCED) };
export const View = 'View', Text = 'Text', Image = 'Image', Pressable = 'Pressable', ScrollView = 'ScrollView',
  TextInput = 'TextInput', Switch = 'Switch', Linking = {}, Modal = 'Modal', FlatList = 'FlatList',
  ActivityIndicator = 'ActivityIndicator', StyleSheet = { create: (x) => x };
class Component { constructor(p) { this.props = p || {}; this.state = {}; } setState(u) { Object.assign(this.state, typeof u === 'function' ? u(this.state) : u); } }
function createElement(type, props, ...children) { return { type, props: props || {}, children }; }
const Children = { toArray: (c) => [].concat(c || []).flat() };
const React = { Component, createElement, Children, Fragment: 'Fragment' };
export default React;
export { Component, createElement, Children };
export const MaterialIcons = { glyphMap: {} };
export function createNavigationContainerRef() { return {}; }
