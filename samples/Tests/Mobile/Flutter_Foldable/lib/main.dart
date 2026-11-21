// RAD IDE foldable sample: the TwoPane rule of docs/CONTRACTS.md 10.8 written with plain Flutter.
// A separating hinge / fold (MediaQuery.displayFeatures) splits the screen exactly at its edges; without
// one, a wide window (>= 600 dp) shows both panes at `ratio` and a narrow one shows only the first pane.
import 'dart:ui' show DisplayFeature, DisplayFeatureState, DisplayFeatureType;

import 'package:flutter/material.dart';

void main() => runApp(const FoldApp());

class FoldApp extends StatelessWidget {
  const FoldApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Foldable',
        theme: ThemeData(colorSchemeSeed: Colors.deepPurple),
        home: const MailScreen(),
      );
}

/// Which panes are shown and where (in the TwoPane's own coordinates).
class PaneSplit {
  const PaneSplit(this.mode, this.first, this.second, {this.atHinge = false});
  final String mode; // single | horizontal | vertical
  final Rect first;
  final Rect? second;
  final bool atHinge;
}

PaneSplit splitPanes(Size size, List<DisplayFeature> features,
    {double ratio = 0.5, double minDual = 600}) {
  final box = Offset.zero & size;
  for (final f in features) {
    final separating = f.type == DisplayFeatureType.hinge ||
        f.state == DisplayFeatureState.postureHalfOpened;
    if (!separating || f.type == DisplayFeatureType.cutout) continue;
    final b = f.bounds;
    final vertical = b.width <= b.height;
    if (vertical && b.left > 0 && b.right < size.width) {
      return PaneSplit('horizontal', Rect.fromLTRB(0, 0, b.left, size.height),
          Rect.fromLTRB(b.right, 0, size.width, size.height),
          atHinge: true);
    }
    if (!vertical && b.top > 0 && b.bottom < size.height) {
      return PaneSplit('vertical', Rect.fromLTRB(0, 0, size.width, b.top),
          Rect.fromLTRB(0, b.bottom, size.width, size.height),
          atHinge: true);
    }
  }
  if (size.width < minDual) return PaneSplit('single', box, null);
  final a = (size.width * ratio).roundToDouble();
  return PaneSplit('horizontal', Rect.fromLTRB(0, 0, a, size.height),
      Rect.fromLTRB(a, 0, size.width, size.height));
}

class TwoPane extends StatelessWidget {
  const TwoPane({super.key, required this.start, required this.end, this.ratio = 0.5});
  final Widget start;
  final Widget end;
  final double ratio;

  @override
  Widget build(BuildContext context) {
    final features = MediaQuery.displayFeaturesOf(context);
    return LayoutBuilder(builder: (context, c) {
      final size = Size(c.maxWidth, c.maxHeight);
      final s = splitPanes(size, features, ratio: ratio);
      final second = s.second;
      return Stack(children: [
        Positioned.fromRect(rect: s.first, child: KeyedSubtree(key: const Key('pane1'), child: start)),
        if (second != null)
          Positioned.fromRect(rect: second, child: KeyedSubtree(key: const Key('pane2'), child: end)),
      ]);
    });
  }
}

class MailScreen extends StatelessWidget {
  const MailScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        body: TwoPane(
          start: ListView(children: const [
            ListTile(title: Text('Item 1'), subtitle: Text('First item')),
            ListTile(title: Text('Item 2'), subtitle: Text('Second item')),
          ]),
          end: const Center(child: Text('Message details')),
        ),
      );
}
