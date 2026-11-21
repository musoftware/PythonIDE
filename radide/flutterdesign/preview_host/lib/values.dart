// JSON property values (docs/FLUTTER_DESIGNER.md section 2) -> Flutter objects.
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'icons_gen.dart';

/// Per-build context of the decoders: theme, asset base URL and a sink for warnings of the current node.
class VCtx {
  VCtx(this.context, this.assetBase, this.warn);
  final BuildContext context;
  final String assetBase;
  final void Function(String) warn;

  ColorScheme get scheme => Theme.of(context).colorScheme;
  Size get screen => MediaQuery.sizeOf(context);
}

bool isCode(dynamic v) => v is Map && v.length == 1 && v.containsKey(r'$code');

// --------------------------------------------------------------------------------------------- numbers
/// A number, "infinity", or a small numeric Dart expression in a $code value
/// (literals, + - * / ( ), double.infinity, MediaQuery size width / height).
double? numV(dynamic v, [VCtx? c]) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  if (v == 'infinity') return double.infinity;
  if (v is String) return double.tryParse(v) ?? (c == null ? null : _Expr(v, c).parse());
  if (isCode(v) && c != null) {
    final r = _Expr(v[r'$code'] as String, c).parse();
    if (r == null) c.warn('code value ${v[r'$code']} not evaluated');
    return r;
  }
  return null;
}

int? intV(dynamic v, [VCtx? c]) => numV(v, c)?.round();

bool? boolV(dynamic v) {
  if (v is bool) return v;
  if (isCode(v)) {
    final s = (v[r'$code'] as String).trim();
    if (s == 'true') return true;
    if (s == 'false') return false;
  }
  return null;
}

String? strV(dynamic v) {
  if (v == null) return null;
  if (v is String) return v;
  if (isCode(v)) {
    var s = (v[r'$code'] as String).trim();
    final m = RegExp(r'''^(['"])(.*)\1$''', dotAll: true).firstMatch(s);
    if (m != null) return m.group(2);
    return s;
  }
  return '$v';
}

class _Expr {
  _Expr(this.src, this.c);
  final String src;
  final VCtx c;
  int i = 0;

  double? parse() {
    try {
      final v = _sum();
      _ws();
      return i == src.length ? v : null;
    } catch (_) {
      return null;
    }
  }

  void _ws() {
    while (i < src.length && src[i].trim().isEmpty) {
      i++;
    }
  }

  double _sum() {
    var v = _prod();
    while (true) {
      _ws();
      if (i < src.length && (src[i] == '+' || src[i] == '-')) {
        final op = src[i++];
        final r = _prod();
        v = op == '+' ? v + r : v - r;
      } else {
        return v;
      }
    }
  }

  double _prod() {
    var v = _atom();
    while (true) {
      _ws();
      if (i < src.length && (src[i] == '*' || src[i] == '/')) {
        final op = src[i++];
        final r = _atom();
        v = op == '*' ? v * r : v / r;
      } else {
        return v;
      }
    }
  }

  static final _num = RegExp(r'\d*\.?\d+(e[+-]?\d+)?');
  static final _mq = RegExp(
      r'MediaQuery\s*\.\s*(?:of\s*\(\s*context\s*\)\s*\.\s*size|sizeOf\s*\(\s*context\s*\))\s*\.\s*(width|height)');

  double _atom() {
    _ws();
    if (src[i] == '(') {
      i++;
      final v = _sum();
      _ws();
      if (src[i] != ')') throw const FormatException();
      i++;
      return v;
    }
    if (src[i] == '-') {
      i++;
      return -_atom();
    }
    final rest = src.substring(i);
    final m = _num.matchAsPrefix(rest);
    if (m != null) {
      i += m.end;
      return double.parse(m.group(0)!);
    }
    if (rest.startsWith('double.infinity')) {
      i += 15;
      return double.infinity;
    }
    final q = _mq.matchAsPrefix(rest);
    if (q != null) {
      i += q.end;
      return q.group(1) == 'width' ? c.screen.width : c.screen.height;
    }
    throw const FormatException();
  }
}

// ---------------------------------------------------------------------------------------------- colors
final Map<String, Color> _named = {
  'transparent': Colors.transparent, 'black': Colors.black, 'white': Colors.white,
  'black87': Colors.black87, 'black54': Colors.black54, 'black45': Colors.black45, 'black38': Colors.black38,
  'black26': Colors.black26, 'black12': Colors.black12, 'white70': Colors.white70, 'white60': Colors.white60,
  'white54': Colors.white54, 'white38': Colors.white38, 'white30': Colors.white30, 'white24': Colors.white24,
  'white12': Colors.white12, 'white10': Colors.white10,
};
final Map<String, ColorSwatch<int>> _swatches = {
  'red': Colors.red, 'pink': Colors.pink, 'purple': Colors.purple, 'deepPurple': Colors.deepPurple,
  'indigo': Colors.indigo, 'blue': Colors.blue, 'lightBlue': Colors.lightBlue, 'cyan': Colors.cyan,
  'teal': Colors.teal, 'green': Colors.green, 'lightGreen': Colors.lightGreen, 'lime': Colors.lime,
  'yellow': Colors.yellow, 'amber': Colors.amber, 'orange': Colors.orange, 'deepOrange': Colors.deepOrange,
  'brown': Colors.brown, 'grey': Colors.grey, 'blueGrey': Colors.blueGrey,
  'redAccent': Colors.redAccent, 'pinkAccent': Colors.pinkAccent, 'purpleAccent': Colors.purpleAccent,
  'deepPurpleAccent': Colors.deepPurpleAccent, 'indigoAccent': Colors.indigoAccent,
  'blueAccent': Colors.blueAccent, 'lightBlueAccent': Colors.lightBlueAccent, 'cyanAccent': Colors.cyanAccent,
  'tealAccent': Colors.tealAccent, 'greenAccent': Colors.greenAccent, 'lightGreenAccent': Colors.lightGreenAccent,
  'limeAccent': Colors.limeAccent, 'yellowAccent': Colors.yellowAccent, 'amberAccent': Colors.amberAccent,
  'orangeAccent': Colors.orangeAccent, 'deepOrangeAccent': Colors.deepOrangeAccent,
};
final Map<String, Color> _cupertino = {
  'activeBlue': CupertinoColors.activeBlue, 'activeGreen': CupertinoColors.activeGreen,
  'activeOrange': CupertinoColors.activeOrange, 'white': CupertinoColors.white, 'black': CupertinoColors.black,
  'lightBackgroundGray': CupertinoColors.lightBackgroundGray, 'extraLightBackgroundGray':
      CupertinoColors.extraLightBackgroundGray, 'darkBackgroundGray': CupertinoColors.darkBackgroundGray,
  'inactiveGray': CupertinoColors.inactiveGray, 'destructiveRed': CupertinoColors.destructiveRed,
  'systemBlue': CupertinoColors.systemBlue, 'systemGreen': CupertinoColors.systemGreen,
  'systemRed': CupertinoColors.systemRed, 'systemOrange': CupertinoColors.systemOrange,
  'systemYellow': CupertinoColors.systemYellow, 'systemPink': CupertinoColors.systemPink,
  'systemPurple': CupertinoColors.systemPurple, 'systemTeal': CupertinoColors.systemTeal,
  'systemIndigo': CupertinoColors.systemIndigo, 'systemGrey': CupertinoColors.systemGrey,
  'systemGrey2': CupertinoColors.systemGrey2, 'systemGrey3': CupertinoColors.systemGrey3,
  'systemGrey4': CupertinoColors.systemGrey4, 'systemGrey5': CupertinoColors.systemGrey5,
  'systemGrey6': CupertinoColors.systemGrey6, 'label': CupertinoColors.label,
  'secondaryLabel': CupertinoColors.secondaryLabel, 'systemBackground': CupertinoColors.systemBackground,
  'separator': CupertinoColors.separator,
};

Color? _schemeColor(ColorScheme s, String n) {
  switch (n) {
    case 'primary': return s.primary;
    case 'onPrimary': return s.onPrimary;
    case 'primaryContainer': return s.primaryContainer;
    case 'onPrimaryContainer': return s.onPrimaryContainer;
    case 'secondary': return s.secondary;
    case 'onSecondary': return s.onSecondary;
    case 'secondaryContainer': return s.secondaryContainer;
    case 'onSecondaryContainer': return s.onSecondaryContainer;
    case 'tertiary': return s.tertiary;
    case 'onTertiary': return s.onTertiary;
    case 'tertiaryContainer': return s.tertiaryContainer;
    case 'onTertiaryContainer': return s.onTertiaryContainer;
    case 'error': return s.error;
    case 'onError': return s.onError;
    case 'errorContainer': return s.errorContainer;
    case 'onErrorContainer': return s.onErrorContainer;
    case 'surface': return s.surface;
    case 'onSurface': return s.onSurface;
    case 'onSurfaceVariant': return s.onSurfaceVariant;
    case 'surfaceContainer': return s.surfaceContainer;
    case 'surfaceContainerLow': return s.surfaceContainerLow;
    case 'surfaceContainerLowest': return s.surfaceContainerLowest;
    case 'surfaceContainerHigh': return s.surfaceContainerHigh;
    case 'surfaceContainerHighest': return s.surfaceContainerHighest;
    case 'surfaceTint': return s.surfaceTint;
    case 'inverseSurface': return s.inverseSurface;
    case 'onInverseSurface': return s.onInverseSurface;
    case 'inversePrimary': return s.inversePrimary;
    case 'outline': return s.outline;
    case 'outlineVariant': return s.outlineVariant;
    case 'shadow': return s.shadow;
    case 'scrim': return s.scrim;
  }
  return null;
}

final _hex = RegExp(r'^(?:#|0x)([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$');
final _suffix = RegExp(
    r'\.(withOpacity|withAlpha|withValues)\(\s*(?:alpha\s*:\s*)?([0-9.]+)\s*\)\s*$');

/// "#AARRGGBB", "Colors.x", "Colors.x.shade300", "Colors.x[300]", "CupertinoColors.x", "scheme.primary",
/// "Theme.of(context).colorScheme.x", "Color(0xFF...)", "Color.fromRGBO(r, g, b, o)", "Color.fromARGB(a, r, g, b)",
/// optionally followed by .withOpacity(o) / .withValues(alpha: o) / .withAlpha(a).
Color? colorV(dynamic v, [VCtx? c]) {
  if (v == null) return null;
  if (isCode(v)) {
    final r = _colorStr((v[r'$code'] as String).trim(), c);
    if (r == null) c?.warn('colour ${v[r'$code']} not evaluated');
    return r;
  }
  if (v is String) return _colorStr(v.trim(), c);
  if (v is int) return Color(v);
  return null;
}

Color? _colorStr(String s, VCtx? c) {
  s = s.replaceFirst(RegExp(r'^const\s+'), '');
  final sm = _suffix.firstMatch(s);
  if (sm != null) {
    final base = _colorStr(s.substring(0, sm.start), c);
    final n = double.tryParse(sm.group(2)!) ?? 1;
    if (base == null) return null;
    if (sm.group(1) == 'withAlpha') return base.withAlpha(n.round());
    return base.withValues(alpha: n);
  }
  final h = _hex.firstMatch(s);
  if (h != null) {
    var x = h.group(1)!;
    if (x.length == 3) x = x.split('').map((e) => '$e$e').join();
    if (x.length == 6) x = 'FF$x';
    return Color(int.parse(x, radix: 16));
  }
  var m = RegExp(r'^Color\(\s*(0x[0-9a-fA-F]+|\d+)\s*\)$').firstMatch(s);
  if (m != null) return Color(int.parse(m.group(1)!));
  m = RegExp(r'^Color\.fromRGBO\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)$').firstMatch(s);
  if (m != null) {
    return Color.fromRGBO(int.parse(m.group(1)!), int.parse(m.group(2)!), int.parse(m.group(3)!),
        double.parse(m.group(4)!));
  }
  m = RegExp(r'^Color\.fromARGB\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$').firstMatch(s);
  if (m != null) {
    return Color.fromARGB(int.parse(m.group(1)!), int.parse(m.group(2)!), int.parse(m.group(3)!),
        int.parse(m.group(4)!));
  }
  if (s.startsWith('scheme.') || s.startsWith('Theme.of(context).colorScheme.')) {
    if (c == null) return null;
    return _schemeColor(c.scheme, s.split('.').last);
  }
  if (s.startsWith('Theme.of(context).')) {
    if (c == null) return null;
    final t = Theme.of(c.context);
    switch (s.substring(18)) {
      case 'primaryColor': return t.primaryColor;
      case 'scaffoldBackgroundColor': return t.scaffoldBackgroundColor;
      case 'canvasColor': return t.canvasColor;
      case 'cardColor': return t.cardColor;
      case 'dividerColor': return t.dividerColor;
      case 'hintColor': return t.hintColor;
    }
    return null;
  }
  if (s.startsWith('CupertinoColors.')) return _cupertino[s.substring(16)];
  m = RegExp(r'^Colors\.(\w+)(?:\.shade(\d+)|\[(\d+)\])?$').firstMatch(s);
  if (m != null) {
    final name = m.group(1)!;
    final shade = int.tryParse(m.group(2) ?? m.group(3) ?? '');
    final named = _named[name];
    if (named != null) return named;
    final sw = _swatches[name];
    if (sw == null) return null;
    return shade == null ? sw : sw[shade];
  }
  return null;
}

// ----------------------------------------------------------------------------------------------- enums
String _tail(dynamic v) => v is String ? v.split('.').last : (isCode(v) ? (v[r'$code'] as String).split('.').last.trim() : '');

T? enumV<T extends Enum>(List<T> values, dynamic v) {
  if (v == null) return null;
  final n = _tail(v);
  for (final e in values) {
    if (e.name == n) return e;
  }
  return null;
}

FontWeight? fontWeightV(dynamic v) {
  if (v == null) return null;
  switch (_tail(v)) {
    case 'w100': return FontWeight.w100;
    case 'w200': return FontWeight.w200;
    case 'w300': return FontWeight.w300;
    case 'w400': case 'normal': return FontWeight.w400;
    case 'w500': return FontWeight.w500;
    case 'w600': return FontWeight.w600;
    case 'w700': case 'bold': return FontWeight.w700;
    case 'w800': return FontWeight.w800;
    case 'w900': return FontWeight.w900;
  }
  if (v is int) return FontWeight.values.firstWhere((w) => w.value == v, orElse: () => FontWeight.w400);
  return null;
}

TextDecoration? textDecorationV(dynamic v) {
  switch (_tail(v)) {
    case 'none': return TextDecoration.none;
    case 'underline': return TextDecoration.underline;
    case 'overline': return TextDecoration.overline;
    case 'lineThrough': return TextDecoration.lineThrough;
  }
  return null;
}

Curve? curveV(dynamic v) {
  switch (_tail(v)) {
    case 'linear': return Curves.linear;
    case 'ease': return Curves.ease;
    case 'easeIn': return Curves.easeIn;
    case 'easeOut': return Curves.easeOut;
    case 'easeInOut': return Curves.easeInOut;
    case 'easeOutCubic': return Curves.easeOutCubic;
    case 'easeInOutCubic': return Curves.easeInOutCubic;
    case 'fastOutSlowIn': return Curves.fastOutSlowIn;
    case 'decelerate': return Curves.decelerate;
    case 'bounceOut': return Curves.bounceOut;
    case 'elasticOut': return Curves.elasticOut;
    case 'easeOutBack': return Curves.easeOutBack;
    case 'easeInBack': return Curves.easeInBack;
    case 'bounceIn': return Curves.bounceIn;
    case 'elasticIn': return Curves.elasticIn;
  }
  return null;
}

ScrollPhysics? physicsV(dynamic v) {
  final s = v is String ? v : (isCode(v) ? v[r'$code'] as String : '');
  if (s.contains('NeverScrollable')) return const NeverScrollableScrollPhysics();
  if (s.contains('Bouncing')) return const BouncingScrollPhysics();
  if (s.contains('Clamping')) return const ClampingScrollPhysics();
  if (s.contains('AlwaysScrollable')) return const AlwaysScrollableScrollPhysics();
  return null;
}

Duration? durationV(dynamic v, [VCtx? c]) {
  final n = numV(v, c);
  return n == null ? null : Duration(milliseconds: n.round());
}

// ------------------------------------------------------------------------------------------- geometry
EdgeInsets? edgeV(dynamic v, [VCtx? c]) {
  if (v == null) return null;
  if (v is num) return EdgeInsets.all(v.toDouble());
  if (isCode(v)) {
    final s = (v[r'$code'] as String).trim();
    if (s == 'EdgeInsets.zero') return EdgeInsets.zero;
    c?.warn('insets $s not evaluated');
    return null;
  }
  if (v is! Map) return null;
  double g(String k) => numV(v[k], c) ?? 0;
  if (v.containsKey('all')) return EdgeInsets.all(g('all'));
  if (v.containsKey('h') || v.containsKey('v')) {
    return EdgeInsets.symmetric(horizontal: g('h'), vertical: g('v'));
  }
  return EdgeInsets.only(left: g('l'), top: g('t'), right: g('r'), bottom: g('b'));
}

BorderRadius? radiusV(dynamic v, [VCtx? c]) {
  if (v == null) return null;
  if (v is num) return BorderRadius.circular(v.toDouble());
  if (isCode(v)) {
    final n = numV(v, c);
    return n == null ? null : BorderRadius.circular(n);
  }
  if (v is! Map) return null;
  Radius r(String k) => Radius.circular(numV(v[k], c) ?? 0);
  return BorderRadius.only(topLeft: r('tl'), topRight: r('tr'), bottomLeft: r('bl'), bottomRight: r('br'));
}

const _aligns = {
  'topLeft': Alignment.topLeft, 'topCenter': Alignment.topCenter, 'topRight': Alignment.topRight,
  'centerLeft': Alignment.centerLeft, 'center': Alignment.center, 'centerRight': Alignment.centerRight,
  'bottomLeft': Alignment.bottomLeft, 'bottomCenter': Alignment.bottomCenter, 'bottomRight': Alignment.bottomRight,
};

Alignment? alignV(dynamic v, [VCtx? c]) {
  if (v == null) return null;
  if (v is Map && !isCode(v)) return Alignment(numV(v['x'], c) ?? 0, numV(v['y'], c) ?? 0);
  if (isCode(v)) {
    final m = RegExp(r'^Alignment\(\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*\)$').firstMatch((v[r'$code'] as String).trim());
    if (m != null) return Alignment(double.parse(m.group(1)!), double.parse(m.group(2)!));
  }
  return _aligns[_tail(v)];
}

Offset? offsetV(dynamic v, [VCtx? c]) {
  if (v is List && v.length == 2) return Offset(numV(v[0], c) ?? 0, numV(v[1], c) ?? 0);
  return null;
}

Size? sizeV(dynamic v, [VCtx? c]) {
  if (v is List && v.length == 2) return Size(numV(v[0], c) ?? 0, numV(v[1], c) ?? 0);
  return null;
}

BoxConstraints? constraintsV(dynamic v, [VCtx? c]) {
  if (v is! Map || isCode(v)) return null;
  return BoxConstraints(
    minWidth: numV(v['minWidth'], c) ?? 0,
    maxWidth: numV(v['maxWidth'], c) ?? double.infinity,
    minHeight: numV(v['minHeight'], c) ?? 0,
    maxHeight: numV(v['maxHeight'], c) ?? double.infinity,
  );
}

// -------------------------------------------------------------------------------------------- icons
IconData? iconV(dynamic v) {
  final s = v is String ? v : (isCode(v) ? (v[r'$code'] as String).trim() : null);
  if (s == null) return null;
  final m = RegExp(r'^(Icons|CupertinoIcons)\.(\w+)$').firstMatch(s);
  if (m == null) return null;
  if (m.group(1) == 'Icons') {
    final e = materialIcons[m.group(2)];
    if (e == null) return null;
    return IconData(e & 0xFFFFF, fontFamily: 'MaterialIcons', matchTextDirection: e > 0xFFFFF);
  }
  final e = cupertinoIcons[m.group(2)];
  if (e == null) return null;
  return IconData(e & 0xFFFFF, fontFamily: 'CupertinoIcons', fontPackage: 'cupertino_icons',
      matchTextDirection: e > 0xFFFFF);
}

// -------------------------------------------------------------------------------------------- images
String imageUrl(String src, VCtx c) {
  if (src.startsWith('http://') || src.startsWith('https://') || src.startsWith('data:')) return src;
  return c.assetBase + src.replaceFirst(RegExp(r'^/+'), '');
}

ImageProvider? imageV(dynamic v, VCtx c) {
  if (v == null) return null;
  if (isCode(v)) {
    final m = RegExp(r'''^(?:const\s+)?(AssetImage|NetworkImage)\(\s*['"]([^'"]+)['"]''')
        .firstMatch((v[r'$code'] as String).trim());
    if (m == null) {
      c.warn('image ${v[r'$code']} not evaluated');
      return null;
    }
    return NetworkImage(imageUrl(m.group(2)!, c), webHtmlElementStrategy: WebHtmlElementStrategy.fallback);
  }
  if (v is! Map) return null;
  final src = strV(v['src']) ?? '';
  if (src.isEmpty) return null;
  if (v['source'] == 'file') {
    c.warn('file images are not shown in the preview');
    return null;
  }
  return NetworkImage(imageUrl(src, c), webHtmlElementStrategy: WebHtmlElementStrategy.fallback);
}

// ------------------------------------------------------------------------------------------ painting
Gradient? gradientV(dynamic v, VCtx c) {
  if (v is! Map || isCode(v)) {
    if (v != null) c.warn('gradient not evaluated');
    return null;
  }
  final colors = <Color>[];
  for (final x in (v['colors'] as List? ?? const [])) {
    colors.add(colorV(x, c) ?? Colors.transparent);
  }
  if (colors.length < 2) {
    if (colors.length == 1) colors.add(colors.first);
    if (colors.isEmpty) return null;
  }
  List<double>? stops;
  final st = v['stops'];
  if (st is List && st.length == colors.length) stops = [for (final s in st) numV(s, c) ?? 0];
  switch (v['type']) {
    case 'radial':
      return RadialGradient(center: alignV(v['center'], c) ?? Alignment.center,
          radius: numV(v['radius'], c) ?? 0.5, colors: colors, stops: stops);
    case 'sweep':
      return SweepGradient(center: alignV(v['center'], c) ?? Alignment.center,
          startAngle: numV(v['startAngle'], c) ?? 0, endAngle: numV(v['endAngle'], c) ?? 6.283185307179586,
          colors: colors, stops: stops);
  }
  return LinearGradient(begin: alignV(v['begin'], c) ?? Alignment.centerLeft,
      end: alignV(v['end'], c) ?? Alignment.centerRight, colors: colors, stops: stops);
}

List<BoxShadow>? shadowsV(dynamic v, VCtx c) {
  if (v is! List) return null;
  final out = <BoxShadow>[];
  for (final s in v) {
    if (s is! Map || isCode(s)) continue;
    out.add(BoxShadow(color: colorV(s['color'], c) ?? const Color(0x33000000), blurRadius: numV(s['blur'], c) ?? 0,
        spreadRadius: numV(s['spread'], c) ?? 0, offset: offsetV(s['offset'], c) ?? Offset.zero));
  }
  return out;
}

BorderSide? sideV(dynamic v, VCtx c) {
  if (v is! Map || isCode(v)) return null;
  return BorderSide(color: colorV(v['color'], c) ?? const Color(0xFF000000), width: numV(v['width'], c) ?? 1.0);
}

BoxBorder? borderV(dynamic v, VCtx c) {
  if (v is! Map || isCode(v)) return null;
  if (v.containsKey('top') || v.containsKey('bottom') || v.containsKey('left') || v.containsKey('right')) {
    return Border(top: sideV(v['top'], c) ?? BorderSide.none, bottom: sideV(v['bottom'], c) ?? BorderSide.none,
        left: sideV(v['left'], c) ?? BorderSide.none, right: sideV(v['right'], c) ?? BorderSide.none);
  }
  return Border.all(color: colorV(v['color'], c) ?? const Color(0xFF000000), width: numV(v['width'], c) ?? 1.0);
}

DecorationImage? decorationImageV(dynamic v, VCtx c) {
  if (v == null) return null;
  final img = imageV(v, c);
  if (img == null) return null;
  return DecorationImage(image: img, fit: v is Map ? enumV(BoxFit.values, v['fit']) : null,
      alignment: (v is Map ? alignV(v['alignment'], c) : null) ?? Alignment.center,
      opacity: (v is Map ? numV(v['opacity'], c) : null) ?? 1.0);
}

BoxDecoration? decorationV(dynamic v, VCtx c) {
  if (v == null) return null;
  if (v is! Map || isCode(v)) {
    c.warn('decoration not evaluated');
    return null;
  }
  final shape = enumV(BoxShape.values, v['shape']) ?? BoxShape.rectangle;
  return BoxDecoration(
    color: colorV(v['color'], c),
    image: decorationImageV(v['image'], c),
    border: borderV(v['border'], c),
    borderRadius: shape == BoxShape.circle ? null : radiusV(v['borderRadius'], c),
    boxShadow: shadowsV(v['boxShadow'], c),
    gradient: gradientV(v['gradient'], c),
    shape: shape,
  );
}

// ------------------------------------------------------------------------------------------------ text
TextStyle? textStyleV(dynamic v, VCtx c) {
  if (v == null) return null;
  if (v is! Map || isCode(v)) {
    final s = isCode(v) ? (v[r'$code'] as String) : '';
    final m = RegExp(r'Theme\.of\(context\)\.textTheme\.(\w+)').firstMatch(s);
    if (m != null) return _textTheme(Theme.of(c.context).textTheme, m.group(1)!);
    c.warn('text style not evaluated');
    return null;
  }
  List<Shadow>? shadows;
  if (v['shadows'] is List) {
    shadows = [
      for (final s in v['shadows'] as List)
        if (s is Map)
          Shadow(color: colorV(s['color'], c) ?? const Color(0x55000000), blurRadius: numV(s['blur'], c) ?? 0,
              offset: offsetV(s['offset'], c) ?? Offset.zero)
    ];
  }
  final st = TextStyle(
    color: colorV(v['color'], c),
    backgroundColor: colorV(v['backgroundColor'], c),
    fontSize: numV(v['fontSize'], c),
    fontWeight: fontWeightV(v['fontWeight']),
    fontStyle: enumV(FontStyle.values, v['fontStyle']),
    letterSpacing: numV(v['letterSpacing'], c),
    wordSpacing: numV(v['wordSpacing'], c),
    height: numV(v['height'], c),
    decoration: v['decoration'] == null ? null : textDecorationV(v['decoration']),
    decorationColor: colorV(v['decorationColor'], c),
    decorationThickness: numV(v['decorationThickness'], c),
    fontFamily: strV(v['fontFamily']),
    shadows: shadows,
  );
  final gf = strV(v['googleFont']);
  if (gf != null && gf.isNotEmpty) {
    try {
      return GoogleFonts.getFont(gf, textStyle: st);
    } catch (e) {
      c.warn('Google font "$gf" not found');
    }
  }
  return st;
}

TextStyle? _textTheme(TextTheme t, String n) {
  switch (n) {
    case 'displayLarge': return t.displayLarge;
    case 'displayMedium': return t.displayMedium;
    case 'displaySmall': return t.displaySmall;
    case 'headlineLarge': return t.headlineLarge;
    case 'headlineMedium': return t.headlineMedium;
    case 'headlineSmall': return t.headlineSmall;
    case 'titleLarge': return t.titleLarge;
    case 'titleMedium': return t.titleMedium;
    case 'titleSmall': return t.titleSmall;
    case 'bodyLarge': return t.bodyLarge;
    case 'bodyMedium': return t.bodyMedium;
    case 'bodySmall': return t.bodySmall;
    case 'labelLarge': return t.labelLarge;
    case 'labelMedium': return t.labelMedium;
    case 'labelSmall': return t.labelSmall;
  }
  return null;
}

// ------------------------------------------------------------------------------------------- shapes
ShapeBorder? shapeV(dynamic v, VCtx c) => outlinedShapeV(v, c);

OutlinedBorder? outlinedShapeV(dynamic v, VCtx c) {
  if (v is! Map || isCode(v)) return null;
  final side = sideV(v['side'], c) ?? BorderSide.none;
  switch (v['type']) {
    case 'circle': return CircleBorder(side: side);
    case 'stadium': return StadiumBorder(side: side);
    case 'beveled':
      return BeveledRectangleBorder(borderRadius: radiusV(v['radius'], c) ?? BorderRadius.zero, side: side);
  }
  return RoundedRectangleBorder(borderRadius: radiusV(v['radius'], c) ?? BorderRadius.zero, side: side);
}

/// The `styleFrom` of the button class [owner].
ButtonStyle? buttonStyleV(dynamic v, VCtx c, String owner) {
  if (v is! Map || isCode(v)) return null;
  final bg = colorV(v['backgroundColor'], c);
  final fg = colorV(v['foregroundColor'], c);
  final pad = edgeV(v['padding'], c);
  final shape = outlinedShapeV(v['shape'], c);
  final el = numV(v['elevation'], c);
  final min = sizeV(v['minimumSize'], c);
  final ts = textStyleV(v['textStyle'], c);
  final side = sideV(v['side'], c);
  switch (owner) {
    case 'TextButton':
      return TextButton.styleFrom(backgroundColor: bg, foregroundColor: fg, padding: pad, shape: shape,
          elevation: el, minimumSize: min, textStyle: ts, side: side);
    case 'OutlinedButton':
      return OutlinedButton.styleFrom(backgroundColor: bg, foregroundColor: fg, padding: pad, shape: shape,
          elevation: el, minimumSize: min, textStyle: ts, side: side);
    case 'FilledButton':
      return FilledButton.styleFrom(backgroundColor: bg, foregroundColor: fg, padding: pad, shape: shape,
          elevation: el, minimumSize: min, textStyle: ts, side: side);
    case 'IconButton':
      return IconButton.styleFrom(backgroundColor: bg, foregroundColor: fg, padding: pad, shape: shape,
          elevation: el, minimumSize: min, side: side);
  }
  return ElevatedButton.styleFrom(backgroundColor: bg, foregroundColor: fg, padding: pad, shape: shape,
      elevation: el, minimumSize: min, textStyle: ts, side: side);
}

InputBorder? _inputBorder(String kind, dynamic radius, dynamic color, double? width, VCtx c) {
  final side = color != null ? BorderSide(color: colorV(color, c) ?? Colors.grey, width: width ?? 1.0) : null;
  switch (kind) {
    case 'none': return InputBorder.none;
    case 'underline': return side == null ? const UnderlineInputBorder() : UnderlineInputBorder(borderSide: side);
    case 'outline':
      final r = radiusV(radius, c) ?? const BorderRadius.all(Radius.circular(4));
      return side == null ? OutlineInputBorder(borderRadius: r) : OutlineInputBorder(borderRadius: r, borderSide: side);
  }
  return null;
}

InputDecoration? inputDecorationV(dynamic v, VCtx c) {
  if (v == null) return null;
  if (v is! Map || isCode(v)) {
    c.warn('input decoration not evaluated');
    return const InputDecoration();
  }
  final kind = v['border'] as String?;
  Widget? icon(dynamic x) {
    final d = iconV(x);
    return d == null ? null : Icon(d);
  }
  return InputDecoration(
    hintText: strV(v['hintText']),
    labelText: strV(v['labelText']),
    helperText: strV(v['helperText']),
    prefixIcon: icon(v['prefixIcon']),
    suffixIcon: icon(v['suffixIcon']),
    hintStyle: textStyleV(v['hintStyle'], c),
    labelStyle: textStyleV(v['labelStyle'], c),
    filled: boolV(v['filled']),
    fillColor: colorV(v['fillColor'], c),
    isDense: boolV(v['isDense']),
    contentPadding: edgeV(v['contentPadding'], c),
    border: kind == null ? null : _inputBorder(kind, v['borderRadius'], null, null, c),
    enabledBorder: kind == null || kind == 'none' || v['borderColor'] == null
        ? (kind == 'none' ? InputBorder.none : null)
        : _inputBorder(kind, v['borderRadius'], v['borderColor'], null, c),
    focusedBorder: kind == null || kind == 'none' || v['focusedBorderColor'] == null
        ? (kind == 'none' ? InputBorder.none : null)
        : _inputBorder(kind, v['borderRadius'], v['focusedBorderColor'], 2, c),
  );
}

List<String> stringListV(dynamic v) {
  if (v is List) return [for (final s in v) strV(s) ?? ''];
  return const [];
}
