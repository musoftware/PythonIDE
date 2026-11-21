// Entrance animations of the designer ("anim" of a node) - the same maths as the generated lib/radfx.dart
// (codegen.RADFX), plus a design-time switch: when not playing, the widget shows its final state.
import 'dart:async';

import 'package:flutter/widgets.dart';

import 'values.dart';

class HostFx extends StatefulWidget {
  const HostFx({super.key, required this.anim, required this.playing, required this.child});

  final Map anim;
  final bool playing;
  final Widget child;

  @override
  State<HostFx> createState() => _HostFxState();
}

class _HostFxState extends State<HostFx> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: (numV(widget.anim['durationMs']) ?? 500).round().clamp(1, 60000)),
    value: widget.playing ? 0.0 : 1.0,
  );
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    if (widget.playing) {
      final d = (numV(widget.anim['delayMs']) ?? 0).round();
      if (d <= 0) {
        _c.forward();
      } else {
        _timer = Timer(Duration(milliseconds: d), () {
          if (mounted) _c.forward();
        });
      }
    }
  }

  @override
  void didUpdateWidget(HostFx old) {
    super.didUpdateWidget(old);
    final d = (numV(widget.anim['durationMs']) ?? 500).round().clamp(1, 60000);
    _c.duration = Duration(milliseconds: d);
    if (!widget.playing && old.playing) {
      _timer?.cancel();
      _c.value = 1.0;
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final a = widget.anim;
    final type = '${a['type']}';
    final curve = curveV(a['curve']) ?? Curves.easeOut;
    final ox = numV(a['offsetX']);
    final oy = numV(a['offsetY']);
    final sc = numV(a['scale']);
    return AnimatedBuilder(
      animation: _c,
      child: widget.child,
      builder: (context, child) {
        final v = _c.value;
        final t = curve.transform(v);
        var opacity = t;
        var dx = 0.0, dy = 0.0, s = 1.0;
        switch (type) {
          case 'fadeInUp':
          case 'slideUp':
            dy = (oy ?? 30) * (1 - t);
          case 'fadeInDown':
          case 'slideDown':
            dy = (oy ?? -30) * (1 - t);
          case 'fadeInLeft':
          case 'slideRight':
            dx = (ox ?? -30) * (1 - t);
          case 'fadeInRight':
          case 'slideLeft':
            dx = (ox ?? 30) * (1 - t);
          case 'scaleIn':
            final from = sc ?? 0.8;
            s = from + (1 - from) * t;
          case 'zoomIn':
            final from = sc ?? 0.3;
            s = from + (1 - from) * t;
          case 'bounceIn':
            final from = sc ?? 0.3;
            s = from + (1 - from) * Curves.elasticOut.transform(v);
            opacity = (v * 2).clamp(0.0, 1.0);
        }
        if (type.startsWith('slide')) opacity = 1;
        Widget w = child!;
        if (s != 1) w = Transform.scale(scale: s, child: w);
        if (dx != 0 || dy != 0) w = Transform.translate(offset: Offset(dx, dy), child: w);
        return Opacity(opacity: opacity.clamp(0.0, 1.0), child: w);
      },
    );
  }
}
