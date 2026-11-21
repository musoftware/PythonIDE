// RatingBar - Flutter runtime of the RatingBar component package.
// Copied into lib/ and exported from lib/radapp.dart (phone forms) or imported by the screen (Flutter designer)
// by RAD IDE; the generated screen creates
//   RatingBar(value: rate1.value, maxStars: rate1.maxStars, readOnly: rate1.readOnly, starColor: rate1.starColor,
//             emptyColor: rate1.emptyColor, onChanged: (v) { rate1['Value'] = v; _code.rate1_ValueChanged(); })
// where rate1 is the control's state object: user code reads rate1.value and sets rate1.value = 4.
import 'package:flutter/material.dart';

Color _radColor(String hex, Color fallback) {
  var h = hex.replaceAll('#', '');
  if (h.length == 6) h = 'FF$h';
  final v = int.tryParse(h, radix: 16);
  return v == null ? fallback : Color(v);
}

class RatingBar extends StatefulWidget {
  const RatingBar({super.key, this.value = 3, this.maxStars = 5, this.readOnly = false,
      this.starColor = '#FFB400', this.emptyColor = '#C8CDD5', this.onChanged});

  final int value;
  final int maxStars;
  final bool readOnly;
  final String starColor;
  final String emptyColor;

  /// Called with the new value when the user taps a star (or code calls setValue / reset).
  final ValueChanged<int>? onChanged;

  @override
  State<RatingBar> createState() => RatingBarState();
}

class RatingBarState extends State<RatingBar> {
  late int value = widget.value;

  @override
  void didUpdateWidget(RatingBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.value != oldWidget.value) value = widget.value;     // set from code (rate1.value = 4)
  }

  void setValue(int v) {
    v = v.clamp(0, widget.maxStars);
    if (v == value) return;
    setState(() => value = v);
    widget.onChanged?.call(v);
  }

  void reset() => setValue(0);

  @override
  Widget build(BuildContext context) {
    final on = _radColor(widget.starColor, Colors.amber);
    final off = _radColor(widget.emptyColor, Colors.grey);
    return LayoutBuilder(builder: (context, box) {
      final size = (box.maxWidth / widget.maxStars).clamp(8.0, box.maxHeight.isFinite ? box.maxHeight : 48.0);
      return Row(mainAxisSize: MainAxisSize.min, children: [
        for (var i = 1; i <= widget.maxStars; i++)
          GestureDetector(
            key: ValueKey('star$i'),
            onTap: widget.readOnly ? null : () => setValue(i == value && i == 1 ? 0 : i),
            child: Icon(Icons.star, size: size, color: i <= value ? on : off),
          ),
      ]);
    });
  }
}
