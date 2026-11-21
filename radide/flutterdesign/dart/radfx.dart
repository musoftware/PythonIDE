// RAD IDE animation helper for designed screens (written by the Flutter designer - do not edit,
// it is replaced). Wrap any widget: RadFx(type: RadFxType.fadeInUp, delayMs: 300, child: ...).
//
// Triggers: load (default), tap, hover, longPress, visible (first time on screen), manual
// (RadFxController.forward()) and state (play: <bool field> - forward when true, back when false).
// repeat: 1 = once, 0 = forever; reverse: play back after each run. Keyframes: RadKeyframes tracks
// (opacity, offsetX, offsetY, scale, rotation in turns, color). Reduced motion
// (MediaQuery.disableAnimations) shows the final state at once. RadRoute gives page transitions and
// radDrive / radPlay drive explicit transitions (FadeTransition ...) from a screen timeline.
import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/widgets.dart';

enum RadFxType {
  fadeIn,
  fadeInUp,
  fadeInDown,
  fadeInLeft,
  fadeInRight,
  slideUp,
  slideDown,
  slideLeft,
  slideRight,
  scaleIn,
  zoomIn,
  bounceIn,
  shake,
  pulse,
  bounce,
  flipX,
  flipY,
  rotate,
  swing,
  heartBeat,
  typewriter,
  colorTo,
  keyframes,
}

/// What starts the animation.
enum RadFxTrigger { load, tap, hover, longPress, visible, manual, state }

/// Entrance types are hidden before they play; the others (attention seekers) rest at their normal look.
bool radFxIsEntrance(RadFxType t) =>
    t.index <= RadFxType.bounceIn.index ||
    t == RadFxType.flipX ||
    t == RadFxType.flipY ||
    t == RadFxType.typewriter;

/// One keyframe: [value] reached at [ms], eased by [curve] from the previous key.
class RadKey {
  const RadKey(this.ms, this.value, [this.curve = Curves.linear]);

  final int ms;
  final double value;
  final Curve curve;
}

/// A colour keyframe (the child is tinted with the colour).
class RadColorKey {
  const RadColorKey(this.ms, this.value, [this.curve = Curves.linear]);

  final int ms;
  final Color value;
  final Curve curve;
}

/// Keyframe tracks of a RadFxType.keyframes animation (rotation in turns, offsets in pixels).
class RadKeyframes {
  const RadKeyframes({this.opacity, this.offsetX, this.offsetY, this.scale, this.rotation, this.color});

  final List<RadKey>? opacity;
  final List<RadKey>? offsetX;
  final List<RadKey>? offsetY;
  final List<RadKey>? scale;
  final List<RadKey>? rotation;
  final List<RadColorKey>? color;

  /// The last key time of all tracks.
  int get durationMs {
    var d = 0;
    for (final t in [opacity, offsetX, offsetY, scale, rotation]) {
      for (final k in t ?? const <RadKey>[]) {
        d = math.max(d, k.ms);
      }
    }
    for (final k in color ?? const <RadColorKey>[]) {
      d = math.max(d, k.ms);
    }
    return d;
  }

  static double? valueAt(List<RadKey>? keys, double ms) {
    if (keys == null || keys.isEmpty) return null;
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

  static Color? colorAt(List<RadColorKey>? keys, double ms) {
    if (keys == null || keys.isEmpty) return null;
    if (ms <= keys.first.ms) return keys.first.value;
    for (var i = 1; i < keys.length; i++) {
      final a = keys[i - 1], b = keys[i];
      if (ms <= b.ms) {
        final span = (b.ms - a.ms).toDouble();
        final t = span <= 0 ? 1.0 : ((ms - a.ms) / span).clamp(0.0, 1.0);
        return Color.lerp(a.value, b.value, b.curve.transform(t));
      }
    }
    return keys.last.value;
  }
}

/// The look of an animated widget at one moment (see [radFxFrame]).
class RadFxFrame {
  double opacity = 1;
  double dx = 0;
  double dy = 0;
  double scaleX = 1;
  double scaleY = 1;

  /// Turns (1 = 360 degrees) around [origin].
  double rotation = 0;
  double rotateX = 0;
  double rotateY = 0;

  /// Share of the child shown from the start edge (typewriter).
  double reveal = 1;

  /// Tint strength towards the target colour (colorTo) or a keyframe colour.
  double tint = 0;
  Color? color;
  Alignment origin = Alignment.center;
}

/// The frame of [type] at controller value [v] (0..1). Same maths in the designer's live preview.
RadFxFrame radFxFrame(
  RadFxType type,
  double v, {
  double? offsetX,
  double? offsetY,
  double? scale,
  double? turns,
  Curve curve = Curves.easeOut,
  RadKeyframes? keyframes,
  int durationMs = 500,
}) {
  final f = RadFxFrame();
  final t = curve.transform(v.clamp(0.0, 1.0));
  switch (type) {
    case RadFxType.fadeIn:
      f.opacity = t;
    case RadFxType.fadeInUp:
      f.opacity = t;
      f.dy = (offsetY ?? 30) * (1 - t);
    case RadFxType.slideUp:
      f.dy = (offsetY ?? 30) * (1 - t);
    case RadFxType.fadeInDown:
      f.opacity = t;
      f.dy = (offsetY ?? -30) * (1 - t);
    case RadFxType.slideDown:
      f.dy = (offsetY ?? -30) * (1 - t);
    case RadFxType.fadeInLeft:
      f.opacity = t;
      f.dx = (offsetX ?? -30) * (1 - t);
    case RadFxType.slideRight:
      f.dx = (offsetX ?? -30) * (1 - t);
    case RadFxType.fadeInRight:
      f.opacity = t;
      f.dx = (offsetX ?? 30) * (1 - t);
    case RadFxType.slideLeft:
      f.dx = (offsetX ?? 30) * (1 - t);
    case RadFxType.scaleIn:
      final from = scale ?? 0.8;
      f.opacity = t;
      f.scaleX = f.scaleY = from + (1 - from) * t;
    case RadFxType.zoomIn:
      final from = scale ?? 0.3;
      f.opacity = t;
      f.scaleX = f.scaleY = from + (1 - from) * t;
    case RadFxType.bounceIn:
      final from = scale ?? 0.3;
      f.scaleX = f.scaleY = from + (1 - from) * Curves.elasticOut.transform(v);
      f.opacity = (v * 2).clamp(0.0, 1.0);
    case RadFxType.shake:
      f.dx = math.sin(v * math.pi * 8) * (offsetX ?? 10) * (1 - v);
    case RadFxType.pulse:
      f.scaleX = f.scaleY = 1 + ((scale ?? 1.1) - 1) * math.sin(math.pi * v);
    case RadFxType.bounce:
      f.dy = -(offsetY ?? 20).abs() * math.sin(math.pi * v * 2).abs() * (1 - v * 0.5);
    case RadFxType.flipX:
      f.rotateX = (1 - t) * math.pi / 2;
      f.opacity = (v * 2).clamp(0.0, 1.0);
    case RadFxType.flipY:
      f.rotateY = (1 - t) * math.pi / 2;
      f.opacity = (v * 2).clamp(0.0, 1.0);
    case RadFxType.rotate:
      f.rotation = (turns ?? 1) * t;
    case RadFxType.swing:
      f.rotation = math.sin(v * math.pi * 6) * (turns ?? 0.04) * (1 - v);
      f.origin = Alignment.topCenter;
    case RadFxType.heartBeat:
      final double p;
      if (v < 0.14) {
        p = v / 0.14;
      } else if (v < 0.28) {
        p = 1 - (v - 0.14) / 0.14;
      } else if (v < 0.42) {
        p = (v - 0.28) / 0.14;
      } else if (v < 0.7) {
        p = 1 - (v - 0.42) / 0.28;
      } else {
        p = 0;
      }
      f.scaleX = f.scaleY = 1 + ((scale ?? 1.3) - 1) * p;
    case RadFxType.typewriter:
      f.reveal = t;
    case RadFxType.colorTo:
      f.tint = t;
    case RadFxType.keyframes:
      final k = keyframes;
      if (k != null) {
        final total = k.durationMs > 0 ? k.durationMs : durationMs;
        final ms = v * total;
        f.opacity = RadKeyframes.valueAt(k.opacity, ms) ?? 1;
        f.dx = RadKeyframes.valueAt(k.offsetX, ms) ?? 0;
        f.dy = RadKeyframes.valueAt(k.offsetY, ms) ?? 0;
        f.scaleX = f.scaleY = RadKeyframes.valueAt(k.scale, ms) ?? 1;
        f.rotation = RadKeyframes.valueAt(k.rotation, ms) ?? 0;
        final c = RadKeyframes.colorAt(k.color, ms);
        if (c != null) {
          f.color = c;
          f.tint = 1;
        }
      }
  }
  return f;
}

/// [child] drawn with frame [f]; [color] is the colorTo target.
Widget radFxApply(RadFxFrame f, Widget child, {Color? color}) {
  var w = child;
  final tint = f.color ?? color;
  if (tint != null && f.tint > 0) {
    w = ColorFiltered(
      colorFilter: ColorFilter.mode(tint.withValues(alpha: tint.a * f.tint.clamp(0.0, 1.0)), BlendMode.srcATop),
      child: w,
    );
  }
  if (f.reveal < 1) {
    w = ClipRect(
      child: Align(alignment: AlignmentDirectional.centerStart, widthFactor: f.reveal.clamp(0.0, 1.0), child: w),
    );
  }
  if (f.rotateX != 0 || f.rotateY != 0) {
    w = Transform(
      alignment: Alignment.center,
      transform: Matrix4.identity()
        ..setEntry(3, 2, 0.002)
        ..rotateX(f.rotateX)
        ..rotateY(f.rotateY),
      child: w,
    );
  }
  if (f.rotation != 0) {
    w = Transform.rotate(angle: f.rotation * 2 * math.pi, alignment: f.origin, child: w);
  }
  if (f.scaleX != 1 || f.scaleY != 1) {
    w = Transform.scale(scaleX: f.scaleX, scaleY: f.scaleY, child: w);
  }
  if (f.dx != 0 || f.dy != 0) w = Transform.translate(offset: Offset(f.dx, f.dy), child: w);
  if (f.opacity < 1) w = Opacity(opacity: f.opacity.clamp(0.0, 1.0), child: w);
  return w;
}

/// Starts / reverses a RadFx from code (trigger: RadFxTrigger.manual, or any other trigger).
class RadFxController {
  _RadFxState? _state;

  /// Plays the animation (from the start when [from] is 0).
  void forward({double? from}) => _state?._play(from: from);

  /// Plays it backwards.
  void reverse() => _state?._controller.reverse();

  /// Stops it where it is.
  void stop() => _state?._controller.stop();

  bool get isAnimating => _state?._controller.isAnimating ?? false;
}

/// Plays an animation on [child] (entrance, attention seeker, keyframes) when [trigger] fires.
class RadFx extends StatefulWidget {
  const RadFx({
    super.key,
    required this.type,
    this.delayMs = 0,
    this.durationMs = 500,
    this.offsetX,
    this.offsetY,
    this.scale,
    this.curve = Curves.easeOut,
    this.trigger = RadFxTrigger.load,
    this.repeat = 1,
    this.reverse = false,
    this.play,
    this.turns,
    this.color,
    this.keyframes,
    this.controller,
    required this.child,
  });

  final RadFxType type;
  final int delayMs;
  final int durationMs;

  /// Start offset in pixels (null = 30 px from the side the type names; shake 10, bounce 20).
  final double? offsetX;
  final double? offsetY;

  /// Start scale for scaleIn / zoomIn / bounceIn (null = 0.8 / 0.3 / 0.3), peak for pulse / heartBeat.
  final double? scale;
  final Curve curve;
  final RadFxTrigger trigger;

  /// Runs: 1 = once, 0 = forever.
  final int repeat;

  /// Play back after each run (auto reverse).
  final bool reverse;

  /// trigger: state - true plays forward, false plays back.
  final bool? play;

  /// rotate: turns (1 = one full turn); swing: amplitude in turns.
  final double? turns;

  /// colorTo: the colour the child is tinted with.
  final Color? color;
  final RadKeyframes? keyframes;
  final RadFxController? controller;
  final Widget child;

  @override
  State<RadFx> createState() => _RadFxState();
}

class _RadFxState extends State<RadFx> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: _durationMs),
    value: _initialValue,
  );
  Timer? _timer;
  Timer? _press;
  bool _started = false;
  bool _seen = false;
  ScrollPosition? _scroll;

  int get _durationMs {
    final k = widget.keyframes;
    final d = widget.type == RadFxType.keyframes && k != null && k.durationMs > 0 ? k.durationMs : widget.durationMs;
    return d.clamp(1, 600000);
  }

  bool get _entrance => radFxIsEntrance(widget.type);

  double get _initialValue {
    switch (widget.trigger) {
      case RadFxTrigger.load:
      case RadFxTrigger.visible:
        return 0;
      case RadFxTrigger.state:
        return widget.play == true ? 1 : 0;
      default:
        return _entrance ? 1 : 0;
    }
  }

  bool get _reduced => MediaQuery.maybeDisableAnimationsOf(context) ?? false;

  @override
  void initState() {
    super.initState();
    widget.controller?._state = this;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (widget.trigger == RadFxTrigger.visible) {
      _scroll?.removeListener(_checkVisible);
      _scroll = Scrollable.maybeOf(context)?.position;
      _scroll?.addListener(_checkVisible);
      WidgetsBinding.instance.addPostFrameCallback((_) => _checkVisible());
    }
    if (_started) return;
    _started = true;
    if (widget.trigger == RadFxTrigger.load) _schedule();
  }

  @override
  void didUpdateWidget(RadFx old) {
    super.didUpdateWidget(old);
    if (old.controller != widget.controller) {
      if (old.controller?._state == this) old.controller?._state = null;
      widget.controller?._state = this;
    }
    _controller.duration = Duration(milliseconds: _durationMs);
    if (widget.trigger == RadFxTrigger.state && widget.play != old.play) {
      if (widget.play == true) {
        _play();
      } else {
        _back();
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _press?.cancel();
    _scroll?.removeListener(_checkVisible);
    if (widget.controller?._state == this) widget.controller?._state = null;
    _controller.dispose();
    super.dispose();
  }

  void _schedule() {
    if (widget.delayMs <= 0 || _reduced) {
      _play(from: 0);
    } else {
      _timer = Timer(Duration(milliseconds: widget.delayMs), () {
        if (mounted) _play(from: 0);
      });
    }
  }

  void _checkVisible() {
    if (_seen || !mounted) return;
    final ro = context.findRenderObject();
    if (ro is! RenderBox || !ro.attached || !ro.hasSize) return;
    final r = ro.localToGlobal(Offset.zero) & ro.size;
    if (r.overlaps(Offset.zero & MediaQuery.sizeOf(context))) {
      _seen = true;
      _schedule();
    }
  }

  Future<void> _play({double? from}) async {
    if (!mounted) return;
    if (_reduced) {
      _controller.value = _entrance || widget.trigger == RadFxTrigger.state ? 1 : 0;
      return;
    }
    try {
      if (widget.repeat <= 0) {
        if (from != null) _controller.value = from;
        await _controller.repeat(reverse: widget.reverse).orCancel;
        return;
      }
      for (var i = 0; i < widget.repeat && mounted; i++) {
        await _controller.forward(from: i == 0 ? from ?? (_controller.value >= 1 ? 0 : null) : 0).orCancel;
        if (widget.reverse && mounted) await _controller.reverse().orCancel;
      }
    } on TickerCanceled {
      // disposed while running
    }
  }

  void _back() {
    if (_reduced) {
      _controller.value = 0;
    } else {
      _controller.reverse();
    }
  }

  @override
  Widget build(BuildContext context) {
    Widget w = AnimatedBuilder(
      animation: _controller,
      child: widget.child,
      builder: (context, child) {
        final f = radFxFrame(
          widget.type,
          _controller.value,
          offsetX: widget.offsetX,
          offsetY: widget.offsetY,
          scale: widget.scale,
          turns: widget.turns,
          curve: widget.curve,
          keyframes: widget.keyframes,
          durationMs: widget.durationMs,
        );
        return radFxApply(f, child!, color: widget.color);
      },
    );
    switch (widget.trigger) {
      case RadFxTrigger.tap:
        w = Listener(behavior: HitTestBehavior.translucent, onPointerUp: (_) => _play(from: 0), child: w);
      case RadFxTrigger.longPress:
        w = Listener(
          behavior: HitTestBehavior.translucent,
          onPointerDown: (_) {
            _press?.cancel();
            _press = Timer(const Duration(milliseconds: 500), () => _play(from: 0));
          },
          onPointerUp: (_) => _press?.cancel(),
          onPointerCancel: (_) => _press?.cancel(),
          child: w,
        );
      case RadFxTrigger.hover:
        w = MouseRegion(onEnter: (_) => _play(from: 0), onExit: (_) => _back(), child: w);
      default:
        break;
    }
    return w;
  }
}

// =================================================================================== page transitions
enum RadTransition { fade, slideLeft, slideUp, scale, none }

/// A screen's page transition (static const transition of a designed screen).
class RadRouteSpec {
  const RadRouteSpec(this.transition, {this.durationMs = 300});

  final RadTransition transition;
  final int durationMs;
}

/// The page transition [t] around [child] driven by the route animation [a].
Widget radTransition(RadTransition t, Animation<double> a, Widget child) {
  final c = CurvedAnimation(parent: a, curve: Curves.easeOutCubic);
  switch (t) {
    case RadTransition.fade:
      return FadeTransition(opacity: c, child: child);
    case RadTransition.slideLeft:
      return SlideTransition(
        position: Tween<Offset>(begin: const Offset(1, 0), end: Offset.zero).animate(c),
        child: child,
      );
    case RadTransition.slideUp:
      return SlideTransition(
        position: Tween<Offset>(begin: const Offset(0, 1), end: Offset.zero).animate(c),
        child: child,
      );
    case RadTransition.scale:
      return ScaleTransition(
        scale: Tween<double>(begin: 0.9, end: 1).animate(c),
        child: FadeTransition(opacity: c, child: child),
      );
    case RadTransition.none:
      return child;
  }
}

/// A page route with a RAD IDE transition (Navigator.push(context, RadRoute(builder: ...))).
class RadRoute<T> extends PageRouteBuilder<T> {
  RadRoute({
    required WidgetBuilder builder,
    RadTransition transition = RadTransition.fade,
    int durationMs = 300,
    RadRouteSpec? spec,
    super.settings,
  }) : super(
          pageBuilder: (context, animation, secondary) => builder(context),
          transitionDuration: Duration(milliseconds: spec?.durationMs ?? durationMs),
          reverseTransitionDuration: Duration(milliseconds: spec?.durationMs ?? durationMs),
          transitionsBuilder: (context, animation, secondary, child) =>
              radTransition(spec?.transition ?? transition, animation, child),
        );
}

// ====================================================================================== timelines
/// [parent] (a screen timeline) mapped to [from]..[to] during [begin]..[end] of it, eased by [curve].
Animation<double> radDrive(
  Animation<double> parent,
  double from,
  double to, {
  double begin = 0,
  double end = 1,
  Curve curve = Curves.linear,
}) =>
    parent.drive(CurveTween(curve: Interval(begin, end, curve: curve))).drive(Tween<double>(begin: from, end: to));

/// [radDrive] for offsets (SlideTransition: fractions of the child's size).
Animation<Offset> radDriveOffset(
  Animation<double> parent,
  Offset from,
  Offset to, {
  double begin = 0,
  double end = 1,
  Curve curve = Curves.linear,
}) =>
    parent.drive(CurveTween(curve: Interval(begin, end, curve: curve))).drive(Tween<Offset>(begin: from, end: to));

/// Starts a screen timeline (reduced motion: jumps to the end).
void radPlay(AnimationController c, BuildContext context, {bool repeat = false, bool reverse = false}) {
  if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
    c.value = 1;
    return;
  }
  if (repeat) {
    c.repeat(reverse: reverse);
  } else if (reverse) {
    c.forward(from: 0).then((_) => c.reverse());
  } else {
    c.forward(from: 0);
  }
}
