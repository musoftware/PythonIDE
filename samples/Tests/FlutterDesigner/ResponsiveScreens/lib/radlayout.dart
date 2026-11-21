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

  /// The sizes of [sizes] that match the window of [context] (MediaQuery size + display features).
  static RadVariant of(BuildContext context, List<RadSize> sizes) =>
      compute(MediaQuery.sizeOf(context), MediaQuery.displayFeaturesOf(context), sizes);

  /// The pure computation behind [of].
  static RadVariant compute(Size size, List<DisplayFeature> features, List<RadSize> sizes) {
    var posture = RadPosture.flat;
    var span = RadSpan.single;
    Axis? fold;
    Rect? hinge;
    for (final f in features) {
      if (f.type != DisplayFeatureType.hinge && f.type != DisplayFeatureType.fold) continue;
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

/// Two panes: side by side / stacked, split at the hinge or fold of the device when [hingeAware] (the
/// widget is assumed to fill the window then), else at [ratio]. On a narrow single screen only
/// [singlePane] is shown.
class RadTwoPane extends StatelessWidget {
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

  @override
  Widget build(BuildContext context) {
    final features = MediaQuery.displayFeaturesOf(context);
    return LayoutBuilder(
      builder: (context, box) {
        Rect? hinge;
        Axis? fold;
        if (hingeAware) {
          for (final f in features) {
            final separating = f.type == DisplayFeatureType.hinge ||
                (f.type == DisplayFeatureType.fold && f.state == DisplayFeatureState.postureHalfOpened);
            if (separating) {
              hinge = f.bounds;
              fold = f.bounds.height >= f.bounds.width ? Axis.vertical : Axis.horizontal;
            }
          }
        }
        final w = box.maxWidth.isFinite ? box.maxWidth : MediaQuery.sizeOf(context).width;
        final h = box.maxHeight.isFinite ? box.maxHeight : MediaQuery.sizeOf(context).height;
        if (hinge != null && fold != null) {
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
        var mode = paneMode;
        if (mode == RadPaneMode.auto) {
          if (w < minDualWidth) return singlePane == RadPane.start ? start : end;
          mode = RadPaneMode.horizontal;
        }
        final r = ratio.clamp(0.05, 0.95);
        final a = (r * 1000).round(), b = 1000 - a;
        final kids = <Widget>[Expanded(flex: a, child: start), Expanded(flex: b, child: end)];
        return mode == RadPaneMode.horizontal ? Row(children: kids) : Column(children: kids);
      },
    );
  }
}
