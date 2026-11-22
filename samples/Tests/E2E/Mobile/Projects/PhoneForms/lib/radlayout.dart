// RAD IDE responsive layout helper for designed screens (written by the Flutter designer - do not edit,
// it is replaced).
//
// A screen lists its sizes (RadSize: width / height ranges, orientation, foldable posture, dual screen);
// build() computes `final rv = RadVariant.of(context, _radSizes);` and a property that differs on some
// sizes is written `rv.pick(base, [RadV('tablet', value), ...])` - every matching size applies in list
// order, the later one wins (like CSS). RadShow hides a widget on some sizes and RadTwoPane lays out two
// panes side by side / stacked, split at the hinge of a foldable or dual-screen device.
import 'dart:ui' show DisplayFeature, DisplayFeatureState, DisplayFeatureType;

import 'package:flutter/widgets.dart';

/// Foldable posture: flat (open / not foldable), halfOpened (book or tabletop), folded (cover screen).
enum RadPosture { flat, halfOpened, folded }

/// One screen or two screens (a hinge / a fold between the panes).
enum RadSpan { single, dual }

/// A named size of a designed screen and when it applies (all given conditions must match).
class RadSize {
  const RadSize(
    this.id, {
    this.minWidth,
    this.maxWidth,
    this.minHeight,
    this.maxHeight,
    this.orientation,
    this.posture,
    this.span,
    this.fold,
  });

  final String id;
  final double? minWidth;
  final double? maxWidth;
  final double? minHeight;
  final double? maxHeight;
  final Orientation? orientation;
  final RadPosture? posture;
  final RadSpan? span;

  /// Direction of the fold / hinge line: Axis.vertical = left | right panes, Axis.horizontal = top / bottom.
  final Axis? fold;

  bool matches(Size size, Orientation o, RadPosture p, RadSpan s, Axis? f) =>
      (minWidth == null || size.width >= minWidth!) &&
      (maxWidth == null || size.width <= maxWidth!) &&
      (minHeight == null || size.height >= minHeight!) &&
      (maxHeight == null || size.height <= maxHeight!) &&
      (orientation == null || orientation == o) &&
      (posture == null || posture == p) &&
      (span == null || span == s) &&
      (fold == null || fold == f);
}

/// A value of a property on one size (see [RadVariant.pick]).
class RadV<T> {
  const RadV(this.id, this.value);

  final String id;
  final T value;
}

/// The sizes that apply now, with the device facts they were computed from.
class RadVariant {
  RadVariant({
    required this.size,
    required this.orientation,
    this.posture = RadPosture.flat,
    this.span = RadSpan.single,
    this.fold,
    this.hinge,
    this.active = const [],
  });

  final Size size;
  final Orientation orientation;
  final RadPosture posture;
  final RadSpan span;
  final Axis? fold;

  /// The hinge / fold rectangle in screen coordinates (null = none or a seamless crease).
  final Rect? hinge;

  /// Matching size ids, in list order.
  final List<String> active;

  /// Posture used when the platform cannot tell (tests, previews of a folded cover screen).
  static RadPosture? debugPosture;

  /// Set once a fold / hinge display feature was reported: the device is a foldable (or dual screen), so a
  /// window without one is shown on its cover screen (or on one screen only) - the folded posture.
  /// Flutter has no "folded" display feature: Android reports a fold only on the inner screen.
  static bool foldableSeen = false;

  /// When no fold was seen yet (the app started folded) guess the cover screen from its shape: a very
  /// narrow, tall window (see [looksLikeCoverScreen]). Set false when the app runs on tall phones only.
  static bool coverScreenHeuristic = true;

  /// The cover screen of a book foldable (Galaxy Z Fold ~ 23:9): shortest side below 400 dp and the
  /// longest at least 2.3 times as long. Ordinary phones (19.5:9 - 21:9, 360 - 430 dp wide) do not match.
  static bool looksLikeCoverScreen(Size s) {
    final short = s.shortestSide, long = s.longestSide;
    return short > 0 && short < 400 && long / short >= 2.3;
  }

  /// Forget what [compute] learnt about the device (tests).
  static void resetFoldMemory() {
    foldableSeen = false;
  }

  /// The sizes of [sizes] that match the window of [context] (MediaQuery size + display features).
  static RadVariant of(BuildContext context, List<RadSize> sizes) =>
      compute(MediaQuery.sizeOf(context), MediaQuery.displayFeaturesOf(context), sizes);

  /// The pure computation behind [of].
  static RadVariant compute(Size size, List<DisplayFeature> features, List<RadSize> sizes) {
    var posture = RadPosture.flat;
    var span = RadSpan.single;
    Axis? fold;
    Rect? hinge;
    var folds = false;
    for (final f in features) {
      if (f.type != DisplayFeatureType.hinge && f.type != DisplayFeatureType.fold) continue;
      folds = true;
      final b = f.bounds;
      fold = b.height >= b.width ? Axis.vertical : Axis.horizontal;
      if (f.type == DisplayFeatureType.hinge) {
        span = RadSpan.dual;
        hinge = b;
      } else {
        if (f.state == DisplayFeatureState.postureHalfOpened) {
          posture = RadPosture.halfOpened;
          span = RadSpan.dual;
        }
        if (!b.isEmpty) hinge = b;
      }
    }
    if (folds) {
      foldableSeen = true;
    } else if (foldableSeen || (coverScreenHeuristic && looksLikeCoverScreen(size))) {
      posture = RadPosture.folded; // no fold reported: the cover screen of a foldable
    }
    posture = debugPosture ?? posture;
    final o = size.width > size.height ? Orientation.landscape : Orientation.portrait;
    final active = [
      for (final s in sizes)
        if (s.matches(size, o, posture, span, fold)) s.id,
    ];
    return RadVariant(
      size: size,
      orientation: o,
      posture: posture,
      span: span,
      fold: fold,
      hinge: hinge,
      active: active,
    );
  }

  bool has(String id) => active.contains(id);

  /// [base], replaced by the value of every matching size of [values] (in order: the last match wins).
  T pick<T>(T base, List<RadV<T>> values) {
    var v = base;
    for (final o in values) {
      if (active.contains(o.id)) v = o.value;
    }
    return v;
  }

  /// Is any of [ids] active?
  bool hides(List<String> ids) => ids.any(active.contains);
}

/// [child], or nothing when [hidden] - generated as `hidden: rv.pick(false, [RadV('compact', true), ...])`
/// so a later size can show the widget again.
class RadShow extends StatelessWidget {
  const RadShow({super.key, required this.hidden, required this.child});

  final bool hidden;
  final Widget child;

  @override
  Widget build(BuildContext context) => hidden ? const SizedBox.shrink() : child;
}

enum RadPaneMode { auto, horizontal, vertical }

enum RadPane { start, end }

/// Two panes: side by side / stacked, split at the hinge or fold of the device when [hingeAware] and the
/// hinge crosses the widget (its window rectangle is converted to the widget's own coordinates, so the
/// widget does not have to fill the window), else at [ratio]. On a narrow single screen only [singlePane]
/// is shown.
class RadTwoPane extends StatefulWidget {
  const RadTwoPane({
    super.key,
    required this.start,
    required this.end,
    this.paneMode = RadPaneMode.auto,
    this.ratio = 0.5,
    this.singlePane = RadPane.start,
    this.hingeAware = true,
    this.minDualWidth = 600,
  });

  final Widget start;
  final Widget end;
  final RadPaneMode paneMode;
  final double ratio;
  final RadPane singlePane;
  final bool hingeAware;

  /// Width from which Auto shows both panes on a single screen.
  final double minDualWidth;

  /// The part of [hinge] (window coordinates) that splits a box of [w] x [h] at [origin] (its top-left
  /// corner in the window): (local hinge, fold direction), or null when the hinge does not cross the box
  /// from one side to the other with room for a pane on each side. Pure (tests).
  static (Rect, Axis)? localHinge(Rect hinge, Axis fold, Offset origin, double w, double h) {
    final r = hinge.shift(-origin);
    if (fold == Axis.vertical) {
      final inside = r.left > 0 && r.right < w, crosses = r.top < h && r.bottom > 0;
      return inside && crosses ? (Rect.fromLTWH(r.left, 0, r.width, h), fold) : null;
    }
    final inside = r.top > 0 && r.bottom < h, crosses = r.left < w && r.right > 0;
    return inside && crosses ? (Rect.fromLTWH(0, r.top, w, r.height), fold) : null;
  }

  @override
  State<RadTwoPane> createState() => _RadTwoPaneState();
}

class _RadTwoPaneState extends State<RadTwoPane> {
  /// Where the widget is in the window (its top-left corner), measured after each layout.
  Offset _origin = Offset.zero;
  bool _measured = false;

  void _measure(Duration _) {
    if (!mounted) return;
    final box = context.findRenderObject();
    if (box is! RenderBox || !box.hasSize || !box.attached) return;
    final o = box.localToGlobal(Offset.zero);
    if (!_measured || (o - _origin).distanceSquared > 0.25) {
      setState(() {
        _origin = o;
        _measured = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final start = widget.start, end = widget.end;
    final features = MediaQuery.displayFeaturesOf(context);
    Rect? windowHinge;
    Axis? windowFold;
    if (widget.hingeAware) {
      for (final f in features) {
        final separating = f.type == DisplayFeatureType.hinge ||
            (f.type == DisplayFeatureType.fold && f.state == DisplayFeatureState.postureHalfOpened);
        if (separating) {
          windowHinge = f.bounds;
          windowFold = f.bounds.height >= f.bounds.width ? Axis.vertical : Axis.horizontal;
        }
      }
      // the hinge is in window coordinates: measure where this widget is after the frame
      if (windowHinge != null) WidgetsBinding.instance.addPostFrameCallback(_measure);
    }
    return LayoutBuilder(
      builder: (context, box) {
        final w = box.maxWidth.isFinite ? box.maxWidth : MediaQuery.sizeOf(context).width;
        final h = box.maxHeight.isFinite ? box.maxHeight : MediaQuery.sizeOf(context).height;
        final local = windowHinge != null && windowFold != null
            ? RadTwoPane.localHinge(windowHinge, windowFold, _origin, w, h)
            : null;
        if (local != null) {
          final (hinge, fold) = local;
          if (fold == Axis.vertical) {
            final a = hinge.left.clamp(0.0, w), gap = hinge.width.clamp(0.0, w - a);
            return Row(
              children: [
                SizedBox(width: a, child: start),
                SizedBox(width: gap),
                Expanded(child: end),
              ],
            );
          }
          final a = hinge.top.clamp(0.0, h), gap = hinge.height.clamp(0.0, h - a);
          return Column(
            children: [
              SizedBox(height: a, child: start),
              SizedBox(height: gap),
              Expanded(child: end),
            ],
          );
        }
        var mode = widget.paneMode;
        if (mode == RadPaneMode.auto) {
          if (w < widget.minDualWidth) return widget.singlePane == RadPane.start ? start : end;
          mode = RadPaneMode.horizontal;
        }
        final r = widget.ratio.clamp(0.05, 0.95);
        final a = (r * 1000).round(), b = 1000 - a;
        final kids = <Widget>[Expanded(flex: a, child: start), Expanded(flex: b, child: end)];
        return mode == RadPaneMode.horizontal ? Row(children: kids) : Column(children: kids);
      },
    );
  }
}
