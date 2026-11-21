// RAD IDE animation presets of classic Flutter forms (copied into lib/ by the IDE - do not edit, it is
// replaced). The form designer lists its storyboards (RadSb: keyframe channels relative to the designed
// look, made from the Animations window) and RadMotion plays them:
//   BeginAnimation('fx1')   StopAnimation('fx1')   SetVisible('lblInfo', false)  (On show / On hide)
// Channels: tx / ty (offset in pixels), sx / sy (scale), rot (degrees), opacity, reveal (typewriter share
// of the text), visible (1 / 0); colours bg / fg (null = the colour the control had when it started).
// Triggers: load, click, hover, timer, after (chains), show, hide, manual. Reduced motion
// (MediaQuery.disableAnimations) shows the end at once.
import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/scheduler.dart';
import 'package:flutter/widgets.dart';

import 'radapp.dart';

/// A colour keyframe; [value] null = the start colour.
class RadMKey {
  const RadMKey(this.ms, this.value, [this.curve = Curves.linear]);

  final int ms;
  final Color? value;
  final Curve curve;
}

/// One animation of the form (an entry of the Animations window).
class RadSb {
  const RadSb(
    this.id,
    this.target,
    this.durationMs, {
    this.tracks = const {},
    this.colors = const {},
    this.count = 1,
    this.forever = false,
    this.autoreverse = false,
    this.delayMs = 0,
    this.chain = const [],
    this.trigger = 'load',
    this.source = '',
    this.intervalMs = 0,
    this.leave = 'reverse',
  });

  final String id;

  /// Control name ('' = the whole screen).
  final String target;
  final int durationMs;
  final Map<String, List<RadKey>> tracks;
  final Map<String, List<RadMKey>> colors;
  final int count;
  final bool forever;
  final bool autoreverse;
  final int delayMs;

  /// Animations started when this one completes.
  final List<String> chain;
  final String trigger;
  final String source;
  final int intervalMs;
  final String leave;
}

/// The look a control gets from the animations running on it.
class RadLook {
  double tx = 0, ty = 0, sx = 1, sy = 1, rot = 0, opacity = 1;
}

class _Run {
  _Run(this.sb, this.started, this.hideAfter);

  final RadSb sb;
  final Duration started;
  final bool hideAfter;
  double backFrom = -1; // hover left: plays back from this position (ms)
  Duration backStart = Duration.zero;
  Color? bg0, fg0;
  String text0 = '';
}

double _at(List<RadKey> keys, double ms) {
  if (keys.isEmpty) return 0;
  if (ms <= keys.first.ms) return keys.first.value;
  for (var i = 1; i < keys.length; i++) {
    final a = keys[i - 1], b = keys[i];
    if (ms <= b.ms) {
      final span = (b.ms - a.ms).toDouble();
      final t = span <= 0 ? 1.0 : ((ms - a.ms) / span).clamp(0.0, 1.0);
      return a.value + (b.value - a.value) * b.curve.transform(t);
    }
  }
  return keys.last.value;
}

Color? _colorAt(List<RadMKey> keys, double ms, Color? start) {
  if (keys.isEmpty) return start;
  Color? v(RadMKey k) => k.value ?? start;
  if (ms <= keys.first.ms) return v(keys.first);
  for (var i = 1; i < keys.length; i++) {
    final a = keys[i - 1], b = keys[i];
    if (ms <= b.ms) {
      final span = (b.ms - a.ms).toDouble();
      final t = span <= 0 ? 1.0 : ((ms - a.ms) / span).clamp(0.0, 1.0);
      final ca = v(a), cb = v(b);
      if (ca == null || cb == null) return t >= 1 ? cb : ca;
      return Color.lerp(ca, cb, b.curve.transform(t));
    }
  }
  return v(keys.last);
}

/// Back / elastic / bounce / sine easings of the RAD IDE presets.
class RadEase {
  static const Curve back = Cubic(0.34, 1.56, 0.64, 1);
  static const Curve elastic = Curves.elasticOut;
  static const Curve bounce = Curves.bounceOut;
  static const Curve sine = Curves.easeInOutSine;
}

/// Plays the storyboards of a form (one ticker for all of them).
class RadMotion extends ChangeNotifier {
  RadMotion(this.vsync, this.sbs, this.controls, {this.respectReducedMotion = true});

  final TickerProvider vsync;
  final List<RadSb> sbs;

  /// Name -> control object of the form (colours, text, visible).
  final Map<String, RadControl> Function() controls;
  final bool respectReducedMotion;
  final Map<String, RadLook> looks = {};
  final Map<String, _Run> _runs = {};
  final List<Timer> _timers = [];
  Ticker? _ticker;
  // time of the animations: ticker time, kept across the ticker's stops (works with the test clock too)
  Duration _base = Duration.zero;
  Duration _now = Duration.zero;
  BuildContext? _context;
  bool _disposed = false;

  RadSb? _sb(String id) {
    for (final s in sbs) {
      if (s.id == id) return s;
    }
    return null;
  }

  bool get _reduced =>
      respectReducedMotion && _context != null && (MediaQuery.maybeDisableAnimationsOf(_context!) ?? false);

  /// Starts the On load animations and the timers (called once the screen is shown).
  void start(BuildContext context) {
    _context = context;
    for (final s in sbs) {
      if (s.trigger == 'load') begin(s.id);
      if (s.trigger == 'timer' && s.intervalMs > 0) {
        _timers.add(Timer.periodic(Duration(milliseconds: s.intervalMs), (_) => begin(s.id)));
      }
    }
  }

  void begin(String id, {bool hideAfter = false}) {
    final sb = _sb(id);
    if (sb == null || _disposed) return;
    final old = _runs.remove(id);
    final r = _Run(sb, _now, hideAfter);
    final c = controls()[sb.target];
    r.bg0 = old?.bg0 ?? c?.backColor;
    r.fg0 = old?.fg0 ?? c?.foreColor;
    r.text0 = old?.text0 ?? c?.text ?? '';
    if (_reduced || sb.durationMs <= 0) {
      _apply(r, sb.autoreverse ? 0 : sb.durationMs.toDouble());
      _finish(r);
      return;
    }
    _runs[id] = r;
    if (sb.delayMs <= 0) _apply(r, 0);
    _ticker ??= vsync.createTicker(_tick);
    if (!_ticker!.isActive) _ticker!.start();
    notifyListeners();
  }

  void stop(String id) {
    _runs.remove(id);
    notifyListeners();
  }

  /// Hover left: 'reverse' plays back from where it is, 'stop' stops, 'none' lets it finish.
  void leave(String id, String mode) {
    final sb = _sb(id);
    if (sb == null || mode == 'none') return;
    if (mode == 'stop') {
      stop(id);
      return;
    }
    var r = _runs[id];
    if (r == null) {
      // already at its end: play it back from there
      if (sb.autoreverse || !looks.containsKey(sb.target)) return;
      r = _runs[id] = _Run(sb, _now, false)..backFrom = sb.durationMs.toDouble();
      r.backStart = _now;
      _ticker ??= vsync.createTicker(_tick);
      if (!_ticker!.isActive) _ticker!.start();
      return;
    }
    final t = _time(r);
    r.backFrom = t < 0 ? 0 : t;
    r.backStart = _now;
  }

  /// Visible with the On show / On hide animations of [name].
  void setVisible(String name, bool on) {
    final c = controls()[name];
    final hide = [for (final s in sbs) if (s.target == name && s.trigger == 'hide') s.id];
    final show = [for (final s in sbs) if (s.target == name && s.trigger == 'show') s.id];
    if (on) {
      c?.visible = true;
      for (final id in show) {
        begin(id);
      }
    } else if (hide.isEmpty) {
      c?.visible = false;
    } else {
      for (var i = 0; i < hide.length; i++) {
        begin(hide[i], hideAfter: i == hide.length - 1);
      }
    }
  }

  /// A control was clicked / entered / left (from the wrapper made by [wrap]).
  void event(String name, String what) {
    for (final s in sbs) {
      final src = s.source.isEmpty ? s.target : s.source;
      if (src != name) continue;
      if (what == 'click' && s.trigger == 'click') begin(s.id);
      if (what == 'enter' && s.trigger == 'hover') begin(s.id);
      if (what == 'exit' && s.trigger == 'hover') leave(s.id, s.leave);
    }
  }

  double _time(_Run r) {
    final sb = r.sb;
    final d = sb.durationMs.toDouble();
    if (r.backFrom >= 0) {
      final t = r.backFrom - (_now - r.backStart).inMicroseconds / 1000.0;
      return t <= 0 ? -2 : t;
    }
    final e = (_now - r.started).inMicroseconds / 1000.0 - sb.delayMs;
    if (e < 0) return -1;
    final cycle = sb.autoreverse ? d * 2 : d;
    final iter = (e / cycle).floor();
    if (!sb.forever && iter >= sb.count) return -2;
    final lt = e - iter * cycle;
    return sb.autoreverse && lt > d ? 2 * d - lt : lt;
  }

  void _tick(Duration elapsed) {
    _now = _base + elapsed;
    final done = <_Run>[];
    for (final r in _runs.values.toList()) {
      final t = _time(r);
      if (t == -2) {
        done.add(r);
      } else if (t >= 0) {
        _apply(r, t);
      }
    }
    for (final r in done) {
      _runs.remove(r.sb.id);
      if (r.backFrom >= 0) {
        _apply(r, 0);
      } else {
        _apply(r, r.sb.autoreverse ? 0 : r.sb.durationMs.toDouble());
        _finish(r);
      }
    }
    if (_runs.isEmpty) {
      _ticker?.stop();
      _base = _now;
    }
    notifyListeners();
  }

  void _apply(_Run r, double t) {
    final sb = r.sb;
    final look = looks.putIfAbsent(sb.target, RadLook.new);
    final c = controls()[sb.target];
    sb.tracks.forEach((ch, keys) {
      final v = _at(keys, t);
      switch (ch) {
        case 'tx':
          look.tx = v;
        case 'ty':
          look.ty = v;
        case 'sx':
          look.sx = v;
        case 'sy':
          look.sy = v;
        case 'rot':
          look.rot = v;
        case 'opacity':
          look.opacity = v.clamp(0.0, 1.0);
        case 'reveal':
          if (c != null) {
            final n = (r.text0.length * v.clamp(0.0, 1.0)).round();
            final s = r.text0.substring(0, n);
            if (c.text != s) c.text = s;
          }
        case 'visible':
          if (c != null && c.visible != (v >= 0.5)) c.visible = v >= 0.5;
      }
    });
    if (c != null && sb.colors.isNotEmpty) {
      final bg = sb.colors['bg'], fg = sb.colors['fg'];
      if (bg != null) c.backColor = _colorAt(bg, t, r.bg0);
      if (fg != null) c.foreColor = _colorAt(fg, t, r.fg0);
      c.refresh();
    }
  }

  void _finish(_Run r) {
    if (r.hideAfter) controls()[r.sb.target]?.visible = false;
    if (r.sb.tracks.containsKey('reveal')) controls()[r.sb.target]?.text = r.text0;
    for (final id in r.sb.chain) {
      begin(id);
    }
  }

  /// [child] drawn with the look of [name]; also reports its clicks / hover for the triggers.
  Widget wrap(String name, Widget child) {
    final clicks = sbs.any((s) => s.trigger == 'click' && (s.source.isEmpty ? s.target : s.source) == name);
    final hovers = sbs.any((s) => s.trigger == 'hover' && (s.source.isEmpty ? s.target : s.source) == name);
    Widget w = ListenableBuilder(
      listenable: this,
      child: child,
      builder: (context, child) {
        final l = looks[name];
        if (l == null) return child!;
        Widget out = child!;
        if (l.sx != 1 || l.sy != 1) {
          out = Transform(
            alignment: Alignment.center,
            transform: Matrix4.diagonal3Values(l.sx, l.sy, 1),
            child: out,
          );
        }
        if (l.rot != 0) out = Transform.rotate(angle: l.rot * math.pi / 180, child: out);
        if (l.tx != 0 || l.ty != 0) out = Transform.translate(offset: Offset(l.tx, l.ty), child: out);
        if (l.opacity < 1) out = Opacity(opacity: l.opacity, child: out);
        return out;
      },
    );
    if (clicks) {
      w = Listener(behavior: HitTestBehavior.translucent, onPointerUp: (_) => event(name, 'click'), child: w);
    }
    if (hovers) {
      w = MouseRegion(onEnter: (_) => event(name, 'enter'), onExit: (_) => event(name, 'exit'), child: w);
    }
    return w;
  }

  @override
  void dispose() {
    _disposed = true;
    for (final t in _timers) {
      t.cancel();
    }
    _ticker?.dispose();
    super.dispose();
  }
}
