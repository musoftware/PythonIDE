"""The JavaScript runtime of React Native (Expo) projects - copied into the project as ``radapp.js``.

It gives the generated screens (``<Form>_designer.jsx``) VB-like control objects (``this.lblHello.Text = 'Hi'``
redraws the screen), the base class ``RadForm`` (``ShowForm`` / ``CloseForm`` / ``MsgBox`` / ``InputBox`` /
``Confirm`` / ``Toast`` / ``FormArgs``), the widgets (``R.Button``, ``R.ListView`` ...) and the dialog host.
Only React Native core + @expo/vector-icons + @react-navigation are used, so it runs on the web, Android
(Expo Go) and iOS.
"""

RADAPP_JS = r"""// RAD IDE runtime for React Native (Expo) apps - copied into the project by the IDE (do not edit: it is
// replaced). Screens: <Form>_designer.jsx (generated) + <Form>.jsx (your code, VB-style handlers).
import React from 'react';
import {
  Image, Linking, Platform, Pressable, ScrollView, Switch as RNSwitch, Text, TextInput, View,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { createNavigationContainerRef } from '@react-navigation/native';

export const navigationRef = createNavigationContainerRef();
export const RadApp = { data: {} };               // values shared by every screen: RadApp.data.user = 'Ann'
export const Theme = {
  primary: '#6750A4', onPrimary: '#FFFFFF', primaryContainer: '#EADDFF', onPrimaryContainer: '#21005D',
  surface: '#FFFBFE', surfaceVariant: '#F3EDF7', outline: '#79747E', text: '#1C1B1F', muted: '#49454F',
};

export class RadEvent {
  constructor(o) { this.Index = -1; this.Text = ''; this.Value = null; this.Action = ''; Object.assign(this, o || {}); }
}

// ------------------------------------------------------------------ icons
const SYN = {
  profile: 'person', account: 'person', user: 'person', me: 'person', favorites: 'favorite', likes: 'favorite',
  cart: 'shopping_cart', shop: 'store', messages: 'message', about: 'info', photos: 'photo', camera: 'camera_alt',
  music: 'music_note', videos: 'videocam', news: 'article', calendar: 'calendar_today', new: 'add', back: 'arrow_back',
  next: 'arrow_forward', alerts: 'notifications', tasks: 'task_alt', library: 'library_books', flutter_dash: 'flutter-dash',
};
function iconKey(name) {
  let s = String(name || '').trim().replace(/[^0-9a-zA-Z]+/g, '_').replace(/^_+|_+$/g, '').toLowerCase();
  s = SYN[s] || s;
  return s.replace(/_/g, '-');
}
export const RadIcons = {
  // "Label:icon" items: the icon after ':'; else the label itself when it is an icon name
  parse(item) {
    const s = String(item || '');
    const i = s.lastIndexOf(':');
    if (i > 0) return { label: s.slice(0, i).trim(), icon: iconKey(s.slice(i + 1)) };
    return { label: s.trim(), icon: iconKey(s) };
  },
  has(item) { return !!MaterialIcons.glyphMap[RadIcons.parse(item).icon]; },
  name(item, fallback = 'circle') { const k = RadIcons.parse(item).icon; return MaterialIcons.glyphMap[k] ? k : fallback; },
  label(item) {
    const p = RadIcons.parse(item);
    const s = p.label.replace(/[_-]+/g, ' ');
    return s ? s[0].toUpperCase() + s.slice(1) : s;
  },
};
export function Icon({ name, size = 24, color = Theme.text, style }) {
  const k = MaterialIcons.glyphMap[iconKey(name)] ? iconKey(name) : 'circle';
  return <MaterialIcons name={k} size={size} color={color} style={style} />;
}

// ------------------------------------------------------------------ controls (VB-like objects)
export class RadControl {
  constructor(form, name, props) {
    this._form = form;
    this.Name = name;
    this._p = Object.assign({ Text: '', Visible: true, Enabled: true, BackColor: null, ForeColor: null,
      FontSize: null, Tag: null, Checked: false, Value: 0, Minimum: 0, Maximum: 100, Items: [], SelectedIndex: -1,
      Image: '', Url: '' }, props || {});
  }
  _set(k, v) { if (this._p[k] !== v) { this._p[k] = v; this._form._radRefresh(); } }
  // list helpers (ListView, ListBox, ComboBox, BottomNav, Drawer, TabBar)
  get Count() { return this._p.Items.length; }
  get SelectedItem() { const i = this._p.SelectedIndex; return i >= 0 && i < this._p.Items.length ? this._p.Items[i] : ''; }
  AddItem(item) { this.Items = [...this._p.Items, String(item)]; return this._p.Items.length - 1; }
  InsertItem(index, item) { const a = [...this._p.Items]; a.splice(index, 0, String(item)); this.Items = a; }
  RemoveAt(index) { const a = [...this._p.Items]; a.splice(index, 1); this.Items = a;
    if (this._p.SelectedIndex >= a.length) this.SelectedIndex = a.length - 1; }
  Clear() { this.Items = []; this.SelectedIndex = -1; }
  SetItems(list) { this.Items = (list || []).map(String); }
  Field(i, n) { const it = this._p.Items[i]; if (it === undefined) return ''; const f = String(it).split('|'); return n < f.length ? f[n] : ''; }
  Focus() { if (this._input && this._input.focus) this._input.focus(); }
  Refresh() { this._form._radRefresh(); }
}
const PROPS = ['Text', 'Visible', 'Enabled', 'BackColor', 'ForeColor', 'FontSize', 'Tag', 'Checked', 'Value', 'Minimum',
  'Maximum', 'Items', 'SelectedIndex', 'Image', 'Url'];
function alias(cls, names, accessor) {
  for (const n of names) {
    const lc = n[0].toLowerCase() + n.slice(1);
    const d = accessor ? accessor(n) : Object.getOwnPropertyDescriptor(cls.prototype, n);
    Object.defineProperty(cls.prototype, n, Object.assign({ configurable: true }, d));
    if (lc !== n) Object.defineProperty(cls.prototype, lc, Object.assign({ configurable: true }, d));
  }
}
alias(RadControl, PROPS, (n) => ({ get() { return this._p[n]; }, set(v) { this._set(n, v); } }));
alias(RadControl, ['Count', 'SelectedItem', 'AddItem', 'InsertItem', 'RemoveAt', 'Clear', 'SetItems', 'Field', 'Focus',
  'Refresh']);

export class RadTimer {
  constructor(form, name, interval, enabled) {
    this._form = form; this.Name = name; this._interval = interval; this._enabled = enabled; this._id = null; this.Tag = null;
  }
  get Interval() { return this._interval; }
  set Interval(v) { this._interval = Math.max(1, Number(v) || 1); if (this._id) { this._stop(); this._start(); } }
  get Enabled() { return this._enabled; }
  set Enabled(v) { this._enabled = !!v; if (this._form._mounted) { this._enabled ? this._start() : this._stop(); } }
  Start() { this.Enabled = true; }
  Stop() { this.Enabled = false; }
  _start() { if (!this._id) this._id = setInterval(() => this._form.fire(this.Name + '_Tick'), this._interval); }
  _stop() { if (this._id) { clearInterval(this._id); this._id = null; } }
}
alias(RadTimer, ['Interval', 'Enabled', 'Start', 'Stop']);

// ------------------------------------------------------------------ dialogs (work on the web too)
const host = { items: [], listeners: new Set(), seq: 0 };
function notify() { host.listeners.forEach((f) => f([...host.items])); }
function push(d) { return new Promise((resolve) => { host.items.push({ ...d, id: ++host.seq, resolve }); notify(); }); }
function close(item, value) { host.items = host.items.filter((x) => x !== item); notify(); item.resolve(value); }

export function MsgBox(text, title = '') { return push({ kind: 'msg', text: String(text), title: String(title || '') }); }
export function Confirm(text, title = '') { return push({ kind: 'confirm', text: String(text), title: String(title || '') }); }
export function InputBox(prompt, title = '', value = '') {
  return push({ kind: 'input', text: String(prompt), title: String(title || ''), value: String(value || '') });
}
export function Choose(items, title = '') { return push({ kind: 'choose', items: items || [], title: String(title || '') }); }
export function Toast(text, ms = 2500) {
  const item = { kind: 'toast', text: String(text), id: ++host.seq, resolve: () => {} };
  host.items.push(item); notify();
  setTimeout(() => close(item), ms);
}

export class RadHost extends React.Component {
  constructor(p) { super(p); this.state = { items: [], input: '' }; this._l = (items) => this.setState({ items }); }
  componentDidMount() { host.listeners.add(this._l); }
  componentWillUnmount() { host.listeners.delete(this._l); }
  render() {
    const items = this.state.items;
    const dlg = items.find((x) => x.kind !== 'toast');
    const toasts = items.filter((x) => x.kind === 'toast');
    return (
      <View pointerEvents="box-none" style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0 }}>
        {dlg ? this.dialog(dlg) : null}
        {toasts.length ? (
          <View pointerEvents="none" style={{ position: 'absolute', left: 16, right: 16, bottom: 32, alignItems: 'center' }}>
            {toasts.map((t) => (
              <View key={t.id} style={{ backgroundColor: '#323232', borderRadius: 8, paddingHorizontal: 16, paddingVertical: 10, marginTop: 6 }}>
                <Text style={{ color: '#fff', fontSize: 14 }}>{t.text}</Text>
              </View>))}
          </View>) : null}
      </View>);
  }
  dialog(d) {
    const btn = (label, value, primary) => (
      <Pressable key={label} onPress={() => close(d, value === '$input' ? this.state.input : value)}
        style={{ paddingHorizontal: 14, paddingVertical: 8, marginLeft: 8, borderRadius: 20,
          backgroundColor: primary ? Theme.primary : 'transparent' }}>
        <Text style={{ color: primary ? Theme.onPrimary : Theme.primary, fontWeight: '600' }}>{label}</Text>
      </Pressable>);
    let body = null;
    let buttons = [btn('OK', undefined, true)];
    if (d.kind === 'confirm') buttons = [btn('No', false), btn('Yes', true, true)];
    if (d.kind === 'input') {
      if (d._init !== true) { d._init = true; setTimeout(() => this.setState({ input: d.value }), 0); }
      body = (<TextInput autoFocus value={this.state.input} onChangeText={(v) => this.setState({ input: v })}
        onSubmitEditing={() => close(d, this.state.input)}
        style={{ borderWidth: 1, borderColor: Theme.outline, borderRadius: 4, padding: 8, marginTop: 12, fontSize: 16 }} />);
      buttons = [btn('Cancel', null), btn('OK', '$input', true)];
    }
    if (d.kind === 'choose') {
      body = (<ScrollView style={{ maxHeight: 320, marginTop: 8 }}>{d.items.map((it, i) => (
        <Pressable key={i} onPress={() => close(d, i)} style={{ paddingVertical: 12 }}>
          <Text style={{ fontSize: 16, color: Theme.text }}>{String(it)}</Text></Pressable>))}</ScrollView>);
      buttons = [btn('Cancel', -1)];
    }
    return (
      <View style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.4)',
        alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <View style={{ backgroundColor: Theme.surface, borderRadius: 24, padding: 24, width: '100%', maxWidth: 360 }}>
          {d.title ? <Text style={{ fontSize: 22, color: Theme.text, marginBottom: 12 }}>{d.title}</Text> : null}
          {d.text ? <Text style={{ fontSize: 15, color: Theme.muted }}>{d.text}</Text> : null}
          {body}
          <View style={{ flexDirection: 'row', justifyContent: 'flex-end', marginTop: 20 }}>{buttons}</View>
        </View>
      </View>);
  }
}

// ------------------------------------------------------------------ the form (screen) base class
export class RadForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = { cw: 0, ch: 0, drawer: false, rev: 0 };
    this._mounted = false;
    this._pending = false;
  }
  _radRefresh() {
    if (!this._mounted || this._pending) return;
    this._pending = true;
    Promise.resolve().then(() => { this._pending = false; if (this._mounted) this.setState((s) => ({ rev: s.rev + 1 })); });
  }
  get radTimers() { return Object.values(this).filter((v) => v instanceof RadTimer); }
  componentDidMount() {
    this._mounted = true;
    this.radTimers.forEach((t) => { if (t._enabled) t._start(); });
    this.fire(this.constructor.formName + '_Load');
  }
  componentWillUnmount() { this._mounted = false; this.radTimers.forEach((t) => t._stop()); }
  // calls the handler <name> of your code when it exists; errors are shown in a message box
  fire(name, e) {
    const fn = this[name];
    if (typeof fn !== 'function') return false;
    try {
      const r = fn.call(this, e || new RadEvent());
      if (r && typeof r.catch === 'function') r.catch((err) => this._error(name, err));
    } catch (err) { this._error(name, err); }
    return true;
  }
  fireAny(c, events, e) {
    for (const ev of events) if (this.fire(c.Name + '_' + ev, e)) return true;
    return false;
  }
  hasHandler(c, events) { return events.some((ev) => typeof this[c.Name + '_' + ev] === 'function'); }
  _error(name, err) {
    console.error(err);
    MsgBox(String(err && err.stack ? err.stack.split('\n').slice(0, 3).join('\n') : err), 'Error in ' + name);
  }
  // screens
  ShowForm(name, args) { const n = this.props.navigation; if (n) n.push(name, { args }); }
  SwitchForm(name, args) { const n = this.props.navigation; if (n) n.replace(name, { args }); }
  CloseForm(result) {
    const n = this.props.navigation;
    if (result !== undefined) RadApp.data.lastResult = result;
    if (n && this.props.route && routeIndex(n, this.props.route) > 0) n.goBack();
  }
  get FormArgs() { const r = this.props.route; return r && r.params ? r.params.args : undefined; }
  MsgBox(text, title) { return MsgBox(text, title); }
  Confirm(text, title) { return Confirm(text, title); }
  InputBox(prompt, title, value) { return InputBox(prompt, title, value); }
  Toast(text, ms) { return Toast(text, ms); }
  OpenDrawer() { this.setState({ drawer: true }); }
  CloseDrawer() { this.setState({ drawer: false }); }
  // place of a control: design value + share of the screen size (Anchor)
  P(x, rx, y, ry, w, rw, h, rh) {
    const cw = this.state.cw || this.constructor.designWidth, ch = this.state.ch || this.constructor.designHeight;
    return { position: 'absolute', left: x + rx * cw, top: y + ry * ch, width: Math.max(0, w + rw * cw),
      height: Math.max(0, h + rh * ch) };
  }
}

// ------------------------------------------------------------------ widgets
const font = (c, extra) => Object.assign({ color: c.ForeColor || Theme.text }, c.FontSize ? { fontSize: c.FontSize } : {}, extra || {});
const box = (c, style) => [style, c.BackColor ? { backgroundColor: c.BackColor } : null];
const dim = (c) => (c.Enabled ? null : { opacity: 0.45 });

function Tappable({ form, c, events = ['Click', 'Tap'], style, children, onPress }) {
  const tap = onPress || (form.hasHandler(c, events) ? () => form.fireAny(c, events) : null);
  const dbl = form.hasHandler(c, ['DoubleClick']);
  const lp = form.hasHandler(c, ['LongPress']);
  if (!tap && !dbl && !lp) return <View style={style}>{children}</View>;
  return (
    <Pressable style={({ pressed }) => [style, pressed ? { opacity: 0.7 } : null]} disabled={!c.Enabled}
      onPress={tap || undefined} onLongPress={lp || dbl ? () => form.fireAny(c, lp ? ['LongPress'] : ['DoubleClick']) : undefined}>
      {children}
    </Pressable>);
}

function Button({ form, c, style }) {
  return (
    <Pressable disabled={!c.Enabled} onPress={() => form.fireAny(c, ['Click', 'Tap'])}
      style={({ pressed }) => [style, { backgroundColor: c.BackColor || Theme.primary, borderRadius: 22,
        alignItems: 'center', justifyContent: 'center', paddingHorizontal: 12, opacity: pressed ? 0.8 : 1 }, dim(c)]}>
      <Text numberOfLines={1} style={font(c, { color: c.ForeColor || Theme.onPrimary, fontWeight: '600' })}>{c.Text}</Text>
    </Pressable>);
}

function Label({ form, c, style, align = 'left', bold, italic }) {
  const jc = { left: 'flex-start', center: 'center', right: 'flex-end' }[align];
  return (
    <Tappable form={form} c={c} style={box(c, [style, { justifyContent: 'center', alignItems: jc }])}>
      <Text style={font(c, { textAlign: align, fontWeight: bold ? 'bold' : 'normal', fontStyle: italic ? 'italic' : 'normal' })}>{c.Text}</Text>
    </Tappable>);
}

function TextField({ form, c, style, hint = '', password = false, multiline = false, readOnly = false, maxLength, outlined = true }) {
  const showLabel = outlined && hint && String(c.Text).length > 0;
  return (
    <View style={[style, dim(c)]}>
      <TextInput ref={(r) => { c._input = r; }} value={String(c.Text)} editable={c.Enabled && !readOnly}
        placeholder={hint} placeholderTextColor={Theme.muted} secureTextEntry={password} multiline={multiline}
        maxLength={maxLength} onChangeText={(v) => { c._p.Text = v; form._radRefresh(); form.fireAny(c, ['Changed', 'TextChanged'], new RadEvent({ Text: v })); }}
        onSubmitEditing={() => form.fireAny(c, ['Submitted'], new RadEvent({ Text: c.Text }))}
        style={[{ flex: 1, borderWidth: 1, borderColor: Theme.outline, borderRadius: 4, paddingHorizontal: 12,
          fontSize: c.FontSize || 16, color: c.ForeColor || Theme.text, backgroundColor: c.BackColor || 'transparent' },
          multiline ? { textAlignVertical: 'top', paddingTop: 8 } : null]} />
      {showLabel ? <Text style={{ position: 'absolute', left: 8, top: -8, fontSize: 12, color: Theme.primary,
        backgroundColor: Theme.surface, paddingHorizontal: 4 }}>{hint}</Text> : null}
    </View>);
}

function Check({ form, c, style, radio, group }) {
  const toggle = () => {
    if (radio) { (group || []).forEach((n) => { if (form[n] && n !== c.Name) form[n]._p.Checked = false; }); c.Checked = true; }
    else c.Checked = !c.Checked;
    form.fireAny(c, ['Changed', 'CheckedChanged', 'Click'], new RadEvent({ Value: c.Checked }));
  };
  const icon = radio ? (c.Checked ? 'radio-button-checked' : 'radio-button-unchecked') : (c.Checked ? 'check-box' : 'check-box-outline-blank');
  return (
    <Pressable disabled={!c.Enabled} onPress={toggle} style={box(c, [style, { flexDirection: 'row', alignItems: 'center' }, dim(c)])}>
      <MaterialIcons name={icon} size={24} color={c.Checked ? Theme.primary : Theme.muted} />
      <Text style={font(c, { marginLeft: 8 })}>{c.Text}</Text>
    </Pressable>);
}

function Switch({ form, c, style }) {
  const sw = (<RNSwitch value={!!c.Checked} disabled={!c.Enabled} trackColor={{ true: Theme.primary }}
    onValueChange={(v) => { c.Checked = v; form.fireAny(c, ['Changed', 'CheckedChanged'], new RadEvent({ Value: v })); }} />);
  if (!c.Text || c.Text === c.Name) return <View style={[style, { justifyContent: 'center' }]}>{sw}</View>;
  return (
    <View style={box(c, [style, { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }])}>
      <Text style={font(c)}>{c.Text}</Text>{sw}
    </View>);
}

class Slider extends React.Component {
  constructor(p) { super(p); this.state = { w: 1 }; }
  set(x) {
    const c = this.props.c;
    if (!c.Enabled) return;
    const f = Math.min(1, Math.max(0, (x - 10) / Math.max(1, this.state.w - 20)));
    const v = Math.round(c.Minimum + f * (c.Maximum - c.Minimum));
    if (v !== c.Value) { c.Value = v; this.props.form.fireAny(c, ['Changed', 'ValueChanged'], new RadEvent({ Value: v })); }
  }
  render() {
    const { c, style } = this.props;
    const span = Math.max(1, c.Maximum - c.Minimum);
    const f = Math.min(1, Math.max(0, (c.Value - c.Minimum) / span));
    return (
      <View style={[style, { justifyContent: 'center' }, dim(c)]} onLayout={(e) => this.setState({ w: e.nativeEvent.layout.width })}
        onStartShouldSetResponder={() => true} onMoveShouldSetResponder={() => true}
        onResponderGrant={(e) => this.set(e.nativeEvent.locationX)} onResponderMove={(e) => this.set(e.nativeEvent.locationX)}>
        <View pointerEvents="none" style={{ marginHorizontal: 10, height: 4, borderRadius: 2, backgroundColor: Theme.primaryContainer }}>
          <View style={{ width: `${f * 100}%`, height: 4, borderRadius: 2, backgroundColor: Theme.primary }} />
        </View>
        <View pointerEvents="none" style={{ position: 'absolute', left: f * Math.max(0, this.state.w - 20),
          width: 20, height: 20, borderRadius: 10, backgroundColor: Theme.primary }} />
      </View>);
  }
}

function ListView({ form, c, style, template = ['title'], simple = false }) {
  const idx = (role) => template.indexOf(role);
  const select = (i) => {
    c.SelectedIndex = i;
    form.fireAny(c, ['Tap', 'Click', 'Changed', 'SelectedIndexChanged', 'ItemTap', 'ItemClick'],
      new RadEvent({ Index: i, Text: c.Items[i] }));
  };
  return (
    <ScrollView style={box(c, [style, simple ? { borderWidth: 1, borderColor: Theme.outline } : null])}>
      {c.Items.map((it, i) => {
        const sel = i === c.SelectedIndex;
        const title = simple ? it : c.Field(i, Math.max(0, idx('title')));
        return (
          <Pressable key={i} disabled={!c.Enabled} onPress={() => select(i)}
            onLongPress={() => form.fireAny(c, ['DoubleClick', 'LongPress'], new RadEvent({ Index: i, Text: it }))}
            style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', paddingHorizontal: simple ? 8 : 16,
              paddingVertical: simple ? 6 : 12, borderBottomWidth: simple ? 0 : 1, borderBottomColor: '#E7E0EC',
              backgroundColor: sel ? Theme.primaryContainer : pressed ? Theme.surfaceVariant : 'transparent' })}>
            {idx('icon') >= 0 ? <Icon name={c.Field(i, idx('icon'))} color={Theme.muted} style={{ marginRight: 16 }} /> : null}
            <View style={{ flex: 1 }}>
              <Text style={font(c, { fontSize: c.FontSize || (simple ? 14 : 16) })}>{title}</Text>
              {idx('subtitle') >= 0 && c.Field(i, idx('subtitle')) ? <Text style={{ color: Theme.muted, fontSize: 14 }}>{c.Field(i, idx('subtitle'))}</Text> : null}
            </View>
            {idx('trailing') >= 0 ? <Text style={{ color: Theme.muted }}>{c.Field(i, idx('trailing'))}</Text> : null}
          </Pressable>);
      })}
    </ScrollView>);
}

function ComboBox({ form, c, style }) {
  const open = async () => {
    const i = await Choose(c.Items, c.Text && c.Text !== c.Name ? c.Text : '');
    if (i >= 0) { c.SelectedIndex = i; form.fireAny(c, ['SelectedIndexChanged', 'Changed'], new RadEvent({ Index: i, Text: c.Items[i] })); }
  };
  return (
    <Pressable disabled={!c.Enabled} onPress={open} style={box(c, [style, { flexDirection: 'row', alignItems: 'center',
      borderBottomWidth: 1, borderBottomColor: Theme.outline, paddingHorizontal: 4 }, dim(c)])}>
      <Text style={font(c, { flex: 1 })} numberOfLines={1}>{c.SelectedItem}</Text>
      <MaterialIcons name="arrow-drop-down" size={24} color={Theme.muted} />
    </Pressable>);
}

function Progress({ c, style }) {
  const span = Math.max(1, c.Maximum - c.Minimum);
  const f = Math.min(1, Math.max(0, (c.Value - c.Minimum) / span));
  return (<View style={[style, { justifyContent: 'center' }]}><View style={{ height: 6, borderRadius: 3, backgroundColor: Theme.primaryContainer }}>
    <View style={{ width: `${f * 100}%`, height: 6, borderRadius: 3, backgroundColor: c.ForeColor || Theme.primary }} /></View></View>);
}

function Numeric({ form, c, style }) {
  const step = (d) => { const v = Math.min(c.Maximum, Math.max(c.Minimum, c.Value + d));
    if (v !== c.Value) { c.Value = v; form.fireAny(c, ['ValueChanged', 'Changed'], new RadEvent({ Value: v })); } };
  return (<View style={[style, { flexDirection: 'row', alignItems: 'center' }, dim(c)]}>
    <Text style={font(c, { flex: 1 })}>{String(c.Value)}</Text>
    <Pressable onPress={() => step(-1)} style={{ padding: 6 }}><MaterialIcons name="remove" size={22} color={Theme.text} /></Pressable>
    <Pressable onPress={() => step(1)} style={{ padding: 6 }}><MaterialIcons name="add" size={22} color={Theme.text} /></Pressable>
  </View>);
}

function Picture({ form, c, style, fit = 'contain' }) {
  const src = typeof c.Image === 'number' ? c.Image : (c.Image ? { uri: String(c.Image) } : null);
  return (<Tappable form={form} c={c} style={box(c, [style, { overflow: 'hidden' }])}>
    {src ? <Image source={src} resizeMode={fit} style={{ width: '100%', height: '100%' }} /> : null}</Tappable>);
}

function IconCtrl({ form, c, style, icon, size }) {
  return (<Tappable form={form} c={c} style={[style, { alignItems: 'center', justifyContent: 'center' }]}>
    <Icon name={icon} size={size} color={c.ForeColor || Theme.text} /></Tappable>);
}

function WebView({ c, style }) {
  if (Platform.OS === 'web') {
    return <View style={style}>{React.createElement('iframe', { src: c.Url, style: { border: 0, width: '100%', height: '100%' } })}</View>;
  }
  return (<Pressable onPress={() => Linking.openURL(c.Url)} style={[style, { alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Theme.outline }]}><MaterialIcons name="public" size={32} color={Theme.primary} />
    <Text style={{ color: Theme.primary, marginTop: 6 }}>{c.Url}</Text></Pressable>);
}

function TabBar({ form, c, style }) {
  return (<View style={box(c, [style, { flexDirection: 'row', backgroundColor: c.BackColor || Theme.surface }])}>
    {c.Items.map((it, i) => (
      <Pressable key={i} onPress={() => { c.SelectedIndex = i; form.fireAny(c, ['Changed', 'SelectedIndexChanged'], new RadEvent({ Index: i, Text: RadIcons.label(it) })); }}
        style={{ flex: 1, alignItems: 'center', justifyContent: 'center', borderBottomWidth: 3,
          borderBottomColor: i === c.SelectedIndex ? Theme.primary : 'transparent' }}>
        <Text style={{ color: i === c.SelectedIndex ? Theme.primary : Theme.muted, fontWeight: '600' }}>{RadIcons.label(it)}</Text>
      </Pressable>))}
  </View>);
}

function Container({ form, c, style, card, elevation = 1, children }) {
  const st = card ? { backgroundColor: c.BackColor || Theme.surfaceVariant, borderRadius: 12, overflow: 'hidden',
    elevation, shadowColor: '#000', shadowOpacity: 0.15 + elevation * 0.03, shadowRadius: 1 + elevation * 2,
    shadowOffset: { width: 0, height: elevation } } : (c.BackColor ? { backgroundColor: c.BackColor } : null);
  return <Tappable form={form} c={c} style={[style, st]}>{children}</Tappable>;
}

function Group({ c, style, children }) {
  return (<View style={[style, { borderWidth: 1, borderColor: Theme.outline, borderRadius: 4 }]}>
    {children}<Text style={{ position: 'absolute', left: 8, top: -9, fontSize: 12, color: Theme.muted,
      backgroundColor: Theme.surface, paddingHorizontal: 4 }}>{c.Text}</Text></View>);
}

function Flex({ c, style, dir, spacing = 0, align = 'start', padding = 0, children }) {
  const ai = { center: 'center', end: 'flex-end', stretch: 'stretch' }[align] || 'flex-start';
  const jc = { between: 'space-between', around: 'space-around' }[align] || 'flex-start';
  const inner = (<View style={{ flexDirection: dir, alignItems: ai, justifyContent: jc, gap: spacing, padding,
    flexGrow: 1 }}>{children}</View>);
  if (jc !== 'flex-start') return <View style={box(c, [style])}>{inner}</View>;
  return (<ScrollView horizontal={dir === 'row'} style={box(c, [style])} contentContainerStyle={{ flexGrow: 1 }}>{inner}</ScrollView>);
}

// position of this screen in the stack (navigation.canGoBack() is true on every screen of a 2-screen stack)
function routeIndex(nav, route) {
  const st = nav.getState ? nav.getState() : null;
  return st && st.routes ? st.routes.findIndex((r) => r.key === route.key) : 0;
}

function AppBar({ form, c, height = 56, title, drawer }) {
  const nav = form.props.navigation;
  const back = !drawer && nav && form.props.route && routeIndex(nav, form.props.route) > 0;
  const press = (i) => { c.SelectedIndex = i; form.fireAny(c, ['Click', 'Tap', 'Changed'], new RadEvent({ Index: i, Action: c.Items[i], Text: c.Items[i] })); };
  const fg = c.ForeColor || Theme.onPrimaryContainer;
  return (
    <View style={{ height, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 4,
      backgroundColor: c.BackColor || Theme.primaryContainer }}>
      {drawer ? <Pressable onPress={() => form.OpenDrawer()} style={{ padding: 12 }}><MaterialIcons name="menu" size={24} color={fg} /></Pressable> : null}
      {back ? <Pressable onPress={() => nav.goBack()} style={{ padding: 12 }}><MaterialIcons name="arrow-back" size={24} color={fg} /></Pressable> : null}
      <Text numberOfLines={1} style={{ flex: 1, marginLeft: drawer || back ? 4 : 12, fontSize: c.FontSize || 22, color: fg }}>{c.Text || title}</Text>
      {c.Items.map((it, i) => (RadIcons.has(it)
        ? <Pressable key={i} onPress={() => press(i)} style={{ padding: 12 }}><MaterialIcons name={RadIcons.name(it)} size={24} color={fg} /></Pressable>
        : <Pressable key={i} onPress={() => press(i)} style={{ padding: 12 }}><Text style={{ color: fg, fontWeight: '600' }}>{it}</Text></Pressable>))}
    </View>);
}

function BottomNav({ form, c, height = 80 }) {
  if (c.Items.length < 2) return null;
  return (
    <View style={{ height, flexDirection: 'row', backgroundColor: c.BackColor || Theme.surfaceVariant }}>
      {c.Items.map((it, i) => {
        const sel = i === c.SelectedIndex;
        return (
          <Pressable key={i} style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
            onPress={() => { c.SelectedIndex = i; form.fireAny(c, ['Changed', 'SelectedIndexChanged', 'Tap', 'Click'], new RadEvent({ Index: i, Text: RadIcons.label(it) })); }}>
            <View style={{ paddingHorizontal: 20, paddingVertical: 4, borderRadius: 16, backgroundColor: sel ? Theme.primaryContainer : 'transparent' }}>
              <MaterialIcons name={RadIcons.name(it)} size={24} color={sel ? Theme.onPrimaryContainer : Theme.muted} />
            </View>
            <Text style={{ fontSize: 12, marginTop: 4, color: sel ? Theme.text : Theme.muted, fontWeight: sel ? '700' : '400' }}>{RadIcons.label(it)}</Text>
          </Pressable>);
      })}
    </View>);
}

function Fab({ form, c, icon = 'add', bottom = 16 }) {
  const ext = c.Text && c.Text !== c.Name;
  return (
    <Pressable disabled={!c.Enabled} onPress={() => form.fireAny(c, ['Click', 'Tap'])}
      style={({ pressed }) => ({ position: 'absolute', right: 16, bottom, height: 56, minWidth: 56, borderRadius: 16,
        paddingHorizontal: ext ? 16 : 0, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        backgroundColor: c.BackColor || Theme.primaryContainer, elevation: 6, shadowColor: '#000', shadowOpacity: 0.3,
        shadowRadius: 6, shadowOffset: { width: 0, height: 3 }, opacity: pressed ? 0.85 : 1 })}>
      <Icon name={icon} color={c.ForeColor || Theme.onPrimaryContainer} />
      {ext ? <Text style={{ marginLeft: 8, fontWeight: '600', color: c.ForeColor || Theme.onPrimaryContainer }}>{c.Text}</Text> : null}
    </Pressable>);
}

function Drawer({ form, c, width = 280 }) {
  if (!form.state.drawer) return null;
  return (
    <View style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, flexDirection: 'row' }}>
      <View style={{ width, backgroundColor: Theme.surface, elevation: 16 }}>
        <View style={{ height: 140, justifyContent: 'flex-end', padding: 16, backgroundColor: c.BackColor || Theme.primary }}>
          <Text style={{ fontSize: 22, color: c.ForeColor || Theme.onPrimary }}>{c.Text}</Text>
        </View>
        {c.Items.map((it, i) => (
          <Pressable key={i} onPress={() => { c.SelectedIndex = i; form.CloseDrawer(); form.fireAny(c, ['Tap', 'Click', 'Changed', 'SelectedIndexChanged'], new RadEvent({ Index: i, Text: RadIcons.label(it) })); }}
            style={{ flexDirection: 'row', alignItems: 'center', padding: 16, backgroundColor: i === c.SelectedIndex ? Theme.primaryContainer : 'transparent' }}>
            <MaterialIcons name={RadIcons.name(it)} size={24} color={Theme.muted} />
            <Text style={{ marginLeft: 24, fontSize: 15, color: Theme.text }}>{RadIcons.label(it)}</Text>
          </Pressable>))}
      </View>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.35)' }} onPress={() => form.CloseDrawer()} />
    </View>);
}

function Screen({ form, backColor, designHeight, appBar, bottom, fab, drawer, children }) {
  return (
    <View style={{ flex: 1, backgroundColor: backColor || Theme.surface }}>
      {appBar}
      <View style={{ flex: 1 }} onLayout={(e) => { const { width, height } = e.nativeEvent.layout;
        if (width !== form.state.cw || height !== form.state.ch) form.setState({ cw: width, ch: Math.max(height, designHeight) }); }}>
        <ScrollView contentContainerStyle={{ minHeight: Math.max(form.state.ch, designHeight) }}>
          <View style={{ height: Math.max(form.state.ch, designHeight) }}>{children}</View>
        </ScrollView>
        {fab}
      </View>
      {bottom}
      {drawer}
    </View>);
}

function Unknown({ c, style, type }) {
  return (<View style={[style, { borderWidth: 1, borderColor: '#999', alignItems: 'center', justifyContent: 'center' }]}>
    <Text style={{ color: '#666' }}>{type + ' ' + c.Name}</Text></View>);
}

export const R = {
  Screen, AppBar, BottomNav, Fab, Drawer, Button, Label, TextField, Check, Switch, Slider, ListView, ComboBox, Progress,
  Numeric, Picture, Icon: IconCtrl, WebView, TabBar, Container, Group, Flex, Unknown, Tappable,
};
"""


# ======================================================================================== radfx.js
# Animations (motion presets), layout sizes and TwoPane of React Native screens (plan MOTION_VARIANTS_FOLDABLES,
# slice D) - copied into the project as radfx.js only when a form uses them (radapp.js stays the same).
RADFX_JS = r"""// RAD IDE animations / layout sizes / TwoPane for React Native (Expo) screens - copied into the project by
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
"""
