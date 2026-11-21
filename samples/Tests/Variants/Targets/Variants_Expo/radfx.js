// RAD IDE animations / layout sizes / TwoPane for React Native (Expo) screens - copied into the project by
// the IDE (do not edit: it is replaced).
//   this.BeginAnimation('fx1')   this.StopAnimation('fx1')   this.SetVisible('lblInfo', false)   this.CurrentSizes
// Offsets / scale / rotation / opacity run on Animated values (useNativeDriver on Android / iOS); colours,
// the typewriter text and Visible follow a JavaScript clock. Reduced motion: AccessibilityInfo.
// Layout sizes match the window size and orientation (Expo Go has no foldable API: posture 'flat', one screen).
import React from 'react';
import { AccessibilityInfo, Animated, Dimensions, Easing, Platform, View } from 'react-native';

const NATIVE = Platform.OS !== 'web';
const EASE = {
  '': Easing.linear, linear: Easing.linear, in: Easing.in(Easing.quad), out: Easing.out(Easing.quad),
  inout: Easing.inOut(Easing.quad), back: Easing.out(Easing.back(1.7)), elastic: Easing.elastic(1),
  bounce: Easing.bounce, sine: Easing.inOut(Easing.sin),
};
const START = { tx: 0, ty: 0, sx: 1, sy: 1, rot: 0, opacity: 1 };
export const FILL = { position: 'absolute', left: 0, top: 0, right: 0, bottom: 0 };

function rgb(c) {
  const m = /^#?([0-9a-f]{6})([0-9a-f]{2})?$/i.exec(String(c || ''));
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function mixColor(a, b, f) {
  if (f <= 0) return a;
  if (f >= 1) return b;
  const ca = rgb(a), cb = rgb(b);
  if (!ca || !cb) return f >= 1 ? b : a;
  return '#' + ca.map((x, i) => Math.round(x + (cb[i] - x) * f).toString(16).padStart(2, '0')).join('');
}
function at(keys, t, start, color) {
  const v = (k) => (k[1] === 'start' || k[1] === null ? start : k[1]);
  if (!keys.length) return start;
  if (t <= keys[0][0]) return v(keys[0]);
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1], b = keys[i];
    if (t <= b[0]) {
      const f = b[0] > a[0] ? (t - a[0]) / (b[0] - a[0]) : 1;
      const e = (EASE[b[2]] || EASE.linear)(Math.max(0, Math.min(1, f)));
      if (color) return mixColor(v(a), v(b), e);
      if (typeof v(a) === 'boolean' || typeof v(b) === 'boolean') return f >= 1 ? v(b) : v(a);
      return v(a) + (v(b) - v(a)) * e;
    }
  }
  return v(keys[keys.length - 1]);
}

export class RadFx {
  constructor(form, sbs, respect = true) {
    this.form = form; this.sbs = sbs; this.respect = respect; this.vals = {}; this.runs = {}; this.timers = [];
    this.reduced = false; this.started = false;
  }
  sb(id) { return this.sbs.find((s) => s.id === id); }
  values(name) {
    if (!this.vals[name]) {
      const v = {};
      for (const k of Object.keys(START)) v[k] = new Animated.Value(START[k]);
      this.vals[name] = v;
    }
    return this.vals[name];
  }
  // the animated style of a control ('' = the screen)
  style(name) {
    const v = this.values(name);
    return { opacity: v.opacity, transform: [{ translateX: v.tx }, { translateY: v.ty },
      { rotate: v.rot.interpolate({ inputRange: [0, 360], outputRange: ['0deg', '360deg'], extrapolate: 'extend' }) },
      { scaleX: v.sx }, { scaleY: v.sy }] };
  }
  start() {
    if (this.started) return;
    this.started = true;
    const go = () => {
      for (const s of this.sbs) {
        if (s.trigger === 'load') this.begin(s.id);
        if (s.trigger === 'timer' && s.interval > 0) this.timers.push(setInterval(() => this.begin(s.id), s.interval));
      }
    };
    if (!this.respect || !AccessibilityInfo.isReduceMotionEnabled) { go(); return; }
    AccessibilityInfo.isReduceMotionEnabled().then((r) => { this.reduced = !!r; go(); }, go);
  }
  stopAll() {
    this.timers.forEach(clearInterval); this.timers = [];
    Object.keys(this.runs).forEach((id) => this.stop(id));
    this.started = false;
  }
  control(name) { return name ? this.form[name] : null; }
  // a click / hover of control [name] (from RadForm.fireAny and FxBox)
  wants(name, events) {
    return events.some((e) => e === 'Click' || e === 'Tap') &&
      this.sbs.some((s) => s.trigger === 'click' && (s.source || s.target) === name);
  }
  event(name, what) {
    for (const s of this.sbs) {
      if ((s.source || s.target) !== name) continue;
      if (what === 'click' && s.trigger === 'click') this.begin(s.id);
      if (what === 'enter' && s.trigger === 'hover') this.begin(s.id);
      if (what === 'leave' && s.trigger === 'hover') this.leave(s.id, s.leave || 'reverse');
    }
  }
  begin(id, hideAfter = false) {
    const s = this.sb(id);
    if (!s) return;
    const old = this.runs[id];
    if (old) this._cancel(old);
    const c = this.control(s.target);
    const run = { s, hideAfter, anims: [], t0: Date.now(),
      start: old ? old.start : { bg: c ? c._p.BackColor : null, fg: c ? c._p.ForeColor : null, text: c ? String(c._p.Text) : '' } };
    this.runs[id] = run;
    const total = s.duration * (s.autoreverse ? 2 : 1);
    if (this.reduced) { this._jsAt(run, s.autoreverse ? 0 : s.duration); this._nativeEnd(run); this._finish(run); return; }
    const v = this.values(s.target);
    const native = [];
    for (const [ch, keys] of Object.entries(s.channels)) {
      if (!(ch in START)) continue;
      v[ch].setValue(keys[0][1]);
      let pts = keys;
      if (s.autoreverse) {
        pts = keys.concat(keys.slice(0, -1).reverse().map((k, i, arr) => [2 * keys[keys.length - 1][0] - k[0], k[1],
          keys[keys.length - 1 - i][2] || '']));
      }
      const seq = [];
      let prev = 0;
      for (const k of pts.slice(1)) {
        seq.push(Animated.timing(v[ch], { toValue: k[1], duration: Math.max(1, k[0] - prev), easing: EASE[k[2]] || EASE.linear,
          useNativeDriver: NATIVE }));
        prev = k[0];
      }
      if (prev < total) seq.push(Animated.delay(total - prev));
      native.push(Animated.sequence(seq));
    }
    const js = Object.keys(s.channels).some((ch) => !(ch in START));
    const parts = [];
    let left = 0;
    const done = () => { left -= 1; if (left === 0 && this.runs[id] === run) this._finish(run); };
    const wrap = (a) => {
      let x = a;
      if (s.forever) x = Animated.loop(a);
      else if (s.count > 1) x = Animated.loop(a, { iterations: s.count });
      return s.delay ? Animated.sequence([Animated.delay(s.delay), x]) : x;
    };
    if (native.length) parts.push(wrap(Animated.parallel(native)));
    if (js) {
      const clock = new Animated.Value(0);
      run.clock = clock;
      run.listener = clock.addListener(({ value }) => {
        const t = s.autoreverse && value > s.duration ? 2 * s.duration - value : value;
        this._jsAt(run, t);
      });
      parts.push(wrap(Animated.timing(clock, { toValue: total, duration: total, easing: Easing.linear, useNativeDriver: false })));
    }
    if (!parts.length) { this._finish(run); return; }
    left = parts.length;
    for (const p of parts) {
      run.anims.push(p);
      p.start(({ finished }) => { if (finished) done(); });
    }
  }
  _jsAt(run, t) {
    const s = run.s, c = this.control(s.target);
    if (!c) return;
    const ch = s.channels;
    if (ch.bg) c._p.BackColor = at(ch.bg.map((k) => [k[0], k[1] === 'parent' ? s.parent : k[1], k[2]]), t, run.start.bg, true);
    if (ch.fg) c._p.ForeColor = at(ch.fg.map((k) => [k[0], k[1] === 'parent' ? s.parent : k[1], k[2]]), t, run.start.fg, true);
    if (ch.reveal) {
      const f = Math.max(0, Math.min(1, at(ch.reveal, t, 1)));
      c._p.Text = run.start.text.slice(0, Math.round(run.start.text.length * f));
    }
    if (ch.visible) c._p.Visible = !!at(ch.visible, t, true);
    this.form._radRefresh();
  }
  _nativeEnd(run) {
    const s = run.s, v = this.values(s.target);
    for (const [ch, keys] of Object.entries(s.channels)) {
      if (ch in START) v[ch].setValue(s.autoreverse ? keys[0][1] : keys[keys.length - 1][1]);
    }
  }
  _finish(run) {
    const s = run.s, c = this.control(s.target);
    if (this.runs[s.id] === run) delete this.runs[s.id];
    if (s.trigger === 'hover') { this.last = this.last || {}; this.last[s.id] = run; }
    if (run.listener && run.clock) run.clock.removeListener(run.listener);
    if (c && s.channels.reveal) c._p.Text = run.start.text;
    if (c && run.hideAfter) c._p.Visible = false;
    this.form._radRefresh();
    for (const n of s.chain || []) this.begin(n);
  }
  _cancel(run) {
    run.anims.forEach((a) => a.stop());
    if (run.listener && run.clock) run.clock.removeListener(run.listener);
  }
  stop(id) { const r = this.runs[id]; if (r) { delete this.runs[id]; this._cancel(r); } }
  // hover left: 'reverse' goes back to the start look, 'stop' stops, 'none' lets it finish
  leave(id, mode) {
    const r = this.runs[id] || (this.last || {})[id];
    if (!r || mode === 'none') return;
    if (this.last) delete this.last[id];
    this.stop(id);
    if (mode === 'stop') return;
    const s = r.s, v = this.values(s.target);
    const back = Math.max(50, Math.min(Date.now() - r.t0, s.duration));
    Animated.parallel(Object.entries(s.channels).filter(([ch]) => ch in START).map(([ch, keys]) =>
      Animated.timing(v[ch], { toValue: keys[0][1], duration: back, useNativeDriver: NATIVE }))).start();
  }
  setVisible(name, on) {
    const c = this.control(name);
    const show = this.sbs.filter((s) => s.target === name && s.trigger === 'show');
    const hide = this.sbs.filter((s) => s.target === name && s.trigger === 'hide');
    if (on) { if (c) c.Visible = true; show.forEach((s) => this.begin(s.id)); }
    else if (!hide.length) { if (c) c.Visible = false; }
    else hide.forEach((s, i) => this.begin(s.id, i === hide.length - 1));
  }
}

// a control drawn with its animated look; reports hover for the "On hover" triggers
export function FxBox({ fx, name, style, children }) {
  const hover = fx.sbs.some((s) => s.trigger === 'hover' && (s.source || s.target) === name);
  const ev = hover ? { onPointerEnter: () => fx.event(name, 'enter'), onPointerLeave: () => fx.event(name, 'leave'),
    onMouseEnter: () => fx.event(name, 'enter'), onMouseLeave: () => fx.event(name, 'leave') } : {};
  return <Animated.View style={[style, fx.style(name)]} {...ev}>{children}</Animated.View>;
}

// ------------------------------------------------------------------ layout sizes
function posture(v) {
  const s = String(v || '').trim().toLowerCase().replace(/[-_ ]/g, '');
  if (['halfopened', 'halfopen', 'half', 'tabletop', 'book'].includes(s)) return 'half-opened';
  if (['folded', 'closed', 'fold', 'cover'].includes(s)) return 'folded';
  if (['flat', 'open', 'opened'].includes(s)) return 'flat';
  return '';
}
export function radMatch(sizes, w, h, env = {}) {
  const orient = w > h ? 'landscape' : 'portrait';
  const out = [];
  for (const s of sizes) {
    const c = s.when || {};
    let ok = true;
    for (const [k, v] of Object.entries(c)) {
      if (v === null || v === '') continue;
      if (k === 'minWidth' && w < Number(v)) ok = false;
      if (k === 'maxWidth' && w > Number(v)) ok = false;
      if (k === 'minHeight' && h < Number(v)) ok = false;
      if (k === 'maxHeight' && h > Number(v)) ok = false;
      if (k === 'orientation' && String(v).toLowerCase().slice(0, 4) !== orient.slice(0, 4)) ok = false;
      if (k === 'posture' && posture(v) !== (env.posture || 'flat')) ok = false;
      if (k === 'span' && String(v).toLowerCase() !== (env.span || 'single')) ok = false;
      if (k === 'fold' && String(v).toLowerCase() !== String(env.fold || '').toLowerCase()) ok = false;
    }
    if (ok) out.push(s.id);
  }
  return out;
}
// the sizes that apply to a form now (its body width, the window height)
export function radSizes(form, sizes) {
  const win = Dimensions.get('window');
  return radMatch(sizes, form.state.cw || win.width, win.height);
}
// place of a control: the base spec, or the spec of the last matching size that moves it
export function placeV(form, active, base, alts) {
  let p = base;
  for (const id of active) if (alts[id]) p = alts[id];
  return form.P(...p);
}
// control properties of the sizes; the designed value comes back when no size sets it
export function useSizes(form, active, props) {
  const key = active.join('|');
  if (form._radActive === key) return;
  form._radActive = key;
  for (const [name, byProp] of Object.entries(props)) {
    const c = form[name];
    if (!c) continue;
    for (const [prop, [base, alts]] of Object.entries(byProp)) {
      let v = base;
      for (const id of active) if (id in alts) v = alts[id];
      c._p[prop] = v;
    }
  }
}

// ------------------------------------------------------------------ TwoPane (Ratio; one pane below 600 dp)
export class TwoPane extends React.Component {
  constructor(p) { super(p); this.state = { w: 0, h: 0 }; }
  split(w, h) {
    const { mode = 'Auto', ratio = 0.5, single = 'Start' } = this.props;
    const r = Math.min(0.95, Math.max(0.05, Number(ratio) || 0.5));
    let m = mode;
    if (m === 'Auto') {
      if (w < 600) return single === 'End' ? [null, [0, 0, w, h]] : [[0, 0, w, h], null];
      m = 'Horizontal';
    }
    if (m === 'Vertical') { const a = Math.round(h * r); return [[0, 0, w, a], [0, a, w, h - a]]; }
    const a = Math.round(w * r);
    return [[0, 0, a, h], [a, 0, w - a, h]];
  }
  render() {
    const { style, backColor, children } = this.props;
    const kids = React.Children.toArray(children).slice(0, 2);
    const rects = this.split(this.state.w, this.state.h);
    return (
      <View style={[style, backColor ? { backgroundColor: backColor } : null, { overflow: 'hidden' }]}
        onLayout={(e) => { const { width, height } = e.nativeEvent.layout; this.setState({ w: width, h: height }); }}>
        {kids.map((k, i) => (rects[i] ? <View key={i} style={{ position: 'absolute', left: rects[i][0], top: rects[i][1],
          width: rects[i][2], height: rects[i][3] }}>{k}</View> : null))}
      </View>);
  }
}
