// Animations of the designer ("anim" of a node) - the maths of the generated lib/radfx.dart (radFxFrame /
// radFxApply, copied into the host as lib/radfx.dart by live.py), plus a design-time switch: when not playing,
// the widget shows its resting look (entrance types: the final state). "Play" plays every trigger once.
import 'dart:async';

import 'package:flutter/widgets.dart';

import 'radfx.dart';
import 'values.dart';

RadFxType? _type(dynamic v) {
  for (final t in RadFxType.values) {
    if (t.name == '$v') return t;
  }
  return null;
}

RadKeyframes? _keyframes(dynamic tracks) {
  if (tracks is! Map) return null;
  List<RadKey>? keys(String n) {
    final l = tracks[n];
    if (l is! List) return null;
    return [
      for (final k in l)
        if (k is List && k.length >= 2)
          RadKey((numV(k[0]) ?? 0).round(), numV(k[1]) ?? 0, k.length > 2 ? curveV(k[2]) ?? Curves.linear : Curves.linear),
    ];
  }
  final cl = tracks['color'];
  return RadKeyframes(
    opacity: keys('opacity'),
    offsetX: keys('offsetX'),
    offsetY: keys('offsetY'),
    scale: keys('scale'),
    rotation: keys('rotation'),
    color: cl is List
        ? [
            for (final k in cl)
              if (k is List && k.length >= 2)
                RadColorKey((numV(k[0]) ?? 0).round(), colorV(k[1]) ?? const Color(0x00000000),
                    k.length > 2 ? curveV(k[2]) ?? Curves.linear : Curves.linear),
          ]
        : null,
  );
}

class HostFx extends StatefulWidget {
  const HostFx({super.key, required this.anim, required this.playing, required this.child});

  final Map anim;
  final bool playing;
  final Widget child;

  @override
  State<HostFx> createState() => _HostFxState();
}

class _HostFxState extends State<HostFx> with SingleTickerProviderStateMixin {
  late final RadFxType _t = _type(widget.anim['type']) ?? RadFxType.fadeIn;
  late final RadKeyframes? _kf = _keyframes(widget.anim['tracks']);
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: _duration()),
    value: widget.playing ? 0.0 : _rest,
  );
  Timer? _timer;

  int _duration() {
    final k = _kf;
    if (_t == RadFxType.keyframes && k != null && k.durationMs > 0) return k.durationMs;
    return (numV(widget.anim['durationMs']) ?? 500).round().clamp(1, 60000);
  }

  double get _rest => radFxIsEntrance(_t) || '${widget.anim['trigger']}'.startsWith('state:') ? 1.0 : 0.0;

  @override
  void initState() {
    super.initState();
    if (widget.playing) {
      final d = (numV(widget.anim['delayMs']) ?? 0).round();
      if (d <= 0) {
        _run();
      } else {
        _timer = Timer(Duration(milliseconds: d), () {
          if (mounted) _run();
        });
      }
    }
  }

  Future<void> _run() async {
    final runs = (numV(widget.anim['repeat']) ?? 1).round();
    final rev = widget.anim['reverse'] == true;
    try {
      for (var i = 0; i < (runs <= 0 ? 3 : runs) && mounted; i++) {
        await _c.forward(from: 0).orCancel;
        if (rev && mounted) await _c.reverse().orCancel;
      }
    } on TickerCanceled {
      // disposed
    }
  }

  @override
  void didUpdateWidget(HostFx old) {
    super.didUpdateWidget(old);
    _c.duration = Duration(milliseconds: _duration());
    if (!widget.playing && old.playing) {
      _timer?.cancel();
      _c.value = _rest;
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
    return AnimatedBuilder(
      animation: _c,
      child: widget.child,
      builder: (context, child) {
        final f = radFxFrame(
          _t,
          _c.value,
          offsetX: numV(a['offsetX']),
          offsetY: numV(a['offsetY']),
          scale: numV(a['scale']),
          turns: numV(a['turns']),
          curve: curveV(a['curve']) ?? Curves.easeOut,
          keyframes: _kf,
          durationMs: _duration(),
        );
        return radFxApply(f, child!, color: colorV(a['color']));
      },
    );
  }
}
