// Themes of the preview: the project theme (screens/app.ftheme.json, the same ThemeData as the generated
// lib/theme/app_theme.dart of radide/flutterdesign/themes.py) and the per-screen "theme" (codegen._theme_wrap).
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'values.dart';

const _headingKeys = [
  'displayLarge', 'displayMedium', 'displaySmall', 'headlineLarge', 'headlineMedium', 'headlineSmall', 'titleLarge'
];

TextTheme _font(String family, String source, TextTheme base) {
  if (source == 'asset') return base.apply(fontFamily: family);
  try {
    return GoogleFonts.getTextTheme(family, base);
  } catch (_) {
    return base;
  }
}

TextStyle? _get(TextTheme t, String k) {
  switch (k) {
    case 'displayLarge': return t.displayLarge;
    case 'displayMedium': return t.displayMedium;
    case 'displaySmall': return t.displaySmall;
    case 'headlineLarge': return t.headlineLarge;
    case 'headlineMedium': return t.headlineMedium;
    case 'headlineSmall': return t.headlineSmall;
    case 'titleLarge': return t.titleLarge;
  }
  return null;
}

TextTheme _withHeadings(TextTheme t, TextStyle? Function(String k) f) => t.copyWith(
      displayLarge: f('displayLarge'), displayMedium: f('displayMedium'), displaySmall: f('displaySmall'),
      headlineLarge: f('headlineLarge'), headlineMedium: f('headlineMedium'), headlineSmall: f('headlineSmall'),
      titleLarge: f('titleLarge'));

ColorScheme _override(ColorScheme s, Map? o) {
  if (o == null || o.isEmpty) return s;
  Color? g(String k) => colorV(o[k]);
  return s.copyWith(
    primary: g('primary'), onPrimary: g('onPrimary'), primaryContainer: g('primaryContainer'),
    onPrimaryContainer: g('onPrimaryContainer'), secondary: g('secondary'), onSecondary: g('onSecondary'),
    secondaryContainer: g('secondaryContainer'), tertiary: g('tertiary'), onTertiary: g('onTertiary'),
    error: g('error'), onError: g('onError'), surface: g('surface'), onSurface: g('onSurface'),
    surfaceContainerHighest: g('surfaceContainerHighest'), outline: g('outline'), outlineVariant: g('outlineVariant'),
  );
}

/// ThemeData of a project theme (app.ftheme.json) for [brightness]; null theme = the default app theme
/// (codegen.standalone_main: ThemeData(colorSchemeSeed: Colors.indigo)).
ThemeData appTheme(Map? t, Brightness brightness) {
  if (t == null || t.isEmpty) {
    return ThemeData(colorSchemeSeed: Colors.indigo, brightness: brightness);
  }
  final isDark = brightness == Brightness.dark;
  var scheme = ColorScheme.fromSeed(
    seedColor: colorV(t['seedColor']) ?? const Color(0xFF5B6CF9),
    brightness: brightness,
    dynamicSchemeVariant: enumV(DynamicSchemeVariant.values, t['variant']) ?? DynamicSchemeVariant.tonalSpot,
  );
  final colors = t['colors'] is Map ? t['colors'] as Map : const {};
  scheme = _override(scheme, (isDark ? colors['dark'] : colors['light']) as Map?);
  final base = ThemeData(colorScheme: scheme, useMaterial3: t['useMaterial3'] != false);
  final font = t['font'] is Map ? t['font'] as Map : const {};
  var textTheme = base.textTheme;
  if (font['family'] is String && (font['family'] as String).isNotEmpty) {
    textTheme = _font(font['family'] as String, '${font['source'] ?? 'google'}', textTheme);
  }
  final hw = fontWeightV(font['headingWeight']);
  if (font['headings'] is String && (font['headings'] as String).isNotEmpty) {
    final h = _font(font['headings'] as String, '${font['headingsSource'] ?? 'google'}', textTheme);
    textTheme = _withHeadings(textTheme, (k) => hw == null ? _get(h, k) : _get(h, k)?.copyWith(fontWeight: hw));
  } else if (hw != null) {
    final tt = textTheme;
    textTheme = _withHeadings(tt, (k) => _get(tt, k)?.copyWith(fontWeight: hw));
  }
  final bg = t['background'] is Map ? t['background'] as Map : const {};
  Color? bgc;
  if (bg.isNotEmpty) bgc = (isDark ? colorV(bg['dark']) : colorV(bg['light'])) ?? scheme.surface;

  final b = t['buttons'] is Map ? t['buttons'] as Map : const {};
  final h = numV(b['height']);
  final pad = edgeV(b['padding']);
  final r = numV(b['radius']);
  final shape = r == null ? null : RoundedRectangleBorder(borderRadius: BorderRadius.circular(r));
  final bts = b['textStyle'] is Map ? _plainStyle(b['textStyle'] as Map) : null;
  final minSize = h == null ? null : Size(64, h);

  final inp = t['inputs'] is Map ? t['inputs'] as Map : const {};
  final style = '${inp['style'] ?? 'outline'}';
  final ir = numV(inp['radius']) ?? 12;
  InputBorder border(String st, [Color? color, double? width]) {
    final side = (color != null || width != null) ? BorderSide(color: color ?? const Color(0xFF000000), width: width ?? 1) : null;
    if (st == 'underline') return side == null ? const UnderlineInputBorder() : UnderlineInputBorder(borderSide: side);
    if (st == 'filled') {
      return OutlineInputBorder(borderRadius: BorderRadius.circular(ir), borderSide: side ?? BorderSide.none);
    }
    return side == null
        ? OutlineInputBorder(borderRadius: BorderRadius.circular(ir))
        : OutlineInputBorder(borderRadius: BorderRadius.circular(ir), borderSide: side);
  }

  final filled = style == 'filled' || inp['fillColor'] != null;
  final card = t['cards'] is Map ? t['cards'] as Map : const {};
  final cr = numV(card['radius']);
  final bar = t['appBar'] is Map ? t['appBar'] as Map : const {};
  final barEl = numV(bar['elevation']);

  return base.copyWith(
    textTheme: textTheme,
    scaffoldBackgroundColor: bgc,
    elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(minimumSize: minSize, padding: pad, shape: shape, textStyle: bts,
            elevation: numV(b['elevation']))),
    filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(minimumSize: minSize, padding: pad, shape: shape, textStyle: bts)),
    outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(minimumSize: minSize, padding: pad, shape: shape, textStyle: bts)),
    textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom(padding: pad, shape: shape, textStyle: bts)),
    inputDecorationTheme: InputDecorationTheme(
      filled: filled ? true : null,
      fillColor: filled ? (colorV(inp['fillColor']) ?? scheme.surfaceContainerHighest) : null,
      contentPadding: edgeV(inp['contentPadding']),
      border: border(style),
      enabledBorder: style != 'filled' ? border(style, scheme.outlineVariant) : border(style),
      focusedBorder: border(style == 'filled' ? 'outline' : style, scheme.primary, 2),
    ),
    cardTheme: CardThemeData(
      elevation: numV(card['elevation']),
      color: colorV(card['color']),
      margin: edgeV(card['margin']),
      shape: cr == null ? null : RoundedRectangleBorder(borderRadius: BorderRadius.circular(cr)),
    ),
    appBarTheme: AppBarTheme(
      centerTitle: bar['centerTitle'] is bool ? bar['centerTitle'] as bool : null,
      elevation: barEl,
      scrolledUnderElevation: barEl == null ? null : (barEl > 2 ? barEl : 2),
      backgroundColor: bar['transparent'] == true ? Colors.transparent : bgc,
      titleTextStyle: (font['headings'] != null || font['family'] != null)
          ? textTheme.titleLarge?.copyWith(color: scheme.onSurface)
          : null,
    ),
  );
}

TextStyle _plainStyle(Map v) => TextStyle(
      fontSize: numV(v['fontSize']),
      fontWeight: fontWeightV(v['fontWeight']),
      letterSpacing: numV(v['letterSpacing']),
      color: colorV(v['color']),
    );

/// The per-screen theme ("theme" of the .fscreen.json) on top of [base] - codegen._theme_wrap.
ThemeData screenTheme(Map? theme, ThemeData base) {
  if (theme == null || theme.isEmpty) return base;
  final seed = colorV(theme['seedColor']);
  final bright = theme['brightness'] == 'dark'
      ? Brightness.dark
      : theme['brightness'] == 'light'
          ? Brightness.light
          : null;
  ThemeData data;
  if (seed != null) {
    data = ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: seed, brightness: bright ?? Brightness.light));
  } else if (bright != null) {
    data = ThemeData(brightness: bright);
  } else {
    data = ThemeData();
  }
  final bg = colorV(theme['background']);
  final ff0 = theme['fontFamily'];
  if (seed == null && bright == null && bg == null && !(ff0 is String && ff0.isNotEmpty)) return base;
  if (bg != null) data = data.copyWith(scaffoldBackgroundColor: bg);
  final ff = theme['fontFamily'];
  if (ff is String && ff.isNotEmpty) {
    try {
      data = data.copyWith(textTheme: GoogleFonts.getTextTheme(ff, data.textTheme));
    } catch (_) {}
  }
  return data;
}

/// Theme keys for the heading list (exported for tests).
List<String> get headingKeys => _headingKeys;
