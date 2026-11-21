// RAD IDE animation helper for designed screens (written by the Flutter designer - do not edit,
// it is replaced). Wrap any widget: RadFx(type: RadFxType.fadeInUp, delayMs: 300, child: ...).
import 'dart:async';

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
}

/// Plays an entrance animation once, after [delayMs].
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
    required this.child,
  });

  final RadFxType type;
  final int delayMs;
  final int durationMs;

  /// Start offset in pixels (null = 30 px from the side the type names).
  final double? offsetX;
  final double? offsetY;

  /// Start scale for scaleIn / zoomIn / bounceIn (null = 0.8 / 0.3 / 0.3).
  final double? scale;
  final Curve curve;
  final Widget child;

  @override
  State<RadFx> createState() => _RadFxState();
}

class _RadFxState extends State<RadFx> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: widget.durationMs),
  );
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    if (widget.delayMs <= 0) {
      _controller.forward();
    } else {
      _timer = Timer(Duration(milliseconds: widget.delayMs), () {
        if (mounted) _controller.forward();
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      child: widget.child,
      builder: (context, child) {
        final v = _controller.value;
        final t = widget.curve.transform(v);
        var opacity = t;
        var dx = 0.0;
        var dy = 0.0;
        var s = 1.0;
        switch (widget.type) {
          case RadFxType.fadeIn:
            break;
          case RadFxType.fadeInUp:
          case RadFxType.slideUp:
            dy = (widget.offsetY ?? 30) * (1 - t);
          case RadFxType.fadeInDown:
          case RadFxType.slideDown:
            dy = (widget.offsetY ?? -30) * (1 - t);
          case RadFxType.fadeInLeft:
          case RadFxType.slideRight:
            dx = (widget.offsetX ?? -30) * (1 - t);
          case RadFxType.fadeInRight:
          case RadFxType.slideLeft:
            dx = (widget.offsetX ?? 30) * (1 - t);
          case RadFxType.scaleIn:
            final from = widget.scale ?? 0.8;
            s = from + (1 - from) * t;
          case RadFxType.zoomIn:
            final from = widget.scale ?? 0.3;
            s = from + (1 - from) * t;
          case RadFxType.bounceIn:
            final from = widget.scale ?? 0.3;
            s = from + (1 - from) * Curves.elasticOut.transform(v);
            opacity = (v * 2).clamp(0.0, 1.0);
        }
        if (widget.type == RadFxType.slideUp ||
            widget.type == RadFxType.slideDown ||
            widget.type == RadFxType.slideLeft ||
            widget.type == RadFxType.slideRight) {
          opacity = 1;
        }
        Widget w = child!;
        if (s != 1) w = Transform.scale(scale: s, child: w);
        if (dx != 0 || dy != 0) w = Transform.translate(offset: Offset(dx, dy), child: w);
        return Opacity(opacity: opacity.clamp(0.0, 1.0), child: w);
      },
    );
  }
}
