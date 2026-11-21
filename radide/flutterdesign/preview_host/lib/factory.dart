// Widget factory: a node of the *.fscreen.json tree (docs/FLUTTER_DESIGNER.md) -> the real Flutter widget.
// Every node is wrapped in a NodeBox (rects / hit tests / errors); parent-data widgets (Positioned, Expanded,
// Flexible, Spacer) stay direct children of their Stack / Flex and wrap their child instead.
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import 'fx.dart';
import 'nodebox.dart';
import 'values.dart';

/// What the factory needs from the host (implemented by HostState in main.dart).
abstract class FactoryHost {
  bool get interactive;
  bool get playing;
  int get epoch;
  String get assetBase;
  dynamic value(String id, dynamic designValue);
  void setValue(String id, dynamic v);
  TextEditingController controller(String id);
  void event(String id, String event, String? handler, [dynamic arg]);
  void nodeIssue(String id, String level, String message);
  GlobalKey<ScaffoldState> scaffoldKey(String id);
  void drawerNodes(String scaffoldId, Set<String> ids);
}

const _flexParents = {'Row', 'Column', 'Flex'};

class WidgetFactory {
  WidgetFactory(this.host);
  final FactoryHost host;

  /// Builds [n] (a node map) for a parent of type [parent] ('' = root / slot of a non-flex widget).
  Widget node(BuildContext context, dynamic n, {String parent = ''}) {
    if (n is! Map) return const SizedBox.shrink();
    final id = '${n['id'] ?? ''}';
    final type = '${n['type'] ?? ''}';
    final warns = <String>[];
    final c = VCtx(context, host.assetBase, warns.add);
    Widget w;

    // ---- parent-data widgets: no NodeBox around them (it would break the Stack / Flex parent data)
    if (type == 'Positioned' || type == 'Expanded' || type == 'Flexible' || type == 'Spacer') {
      final props = (n['props'] as Map?) ?? const {};
      final slots = (n['slots'] as Map?) ?? const {};
      Widget inner = slots['child'] != null ? node(context, slots['child']) : const SizedBox.shrink();
      if (n['anim'] is Map) inner = _fx(n['anim'] as Map, inner, id);
      inner = NodeBox(key: ValueKey('rad:$id'), id: id, type: type, child: inner);
      final okParent = type == 'Positioned' ? parent == 'Stack' : _flexParents.contains(parent);
      if (!okParent) {
        host.nodeIssue(id, 'warning',
            type == 'Positioned' ? 'Positioned must be a child of a Stack' : '$type must be a child of a Row / Column / Flex');
        return inner;
      }
      try {
        switch (type) {
          case 'Positioned':
            if (n['ctor'] == 'fill') {
              w = Positioned.fill(left: numV(props['left'], c), top: numV(props['top'], c),
                  right: numV(props['right'], c), bottom: numV(props['bottom'], c), child: inner);
            } else {
              final l = numV(props['left'], c), r = numV(props['right'], c), wd = numV(props['width'], c);
              final t = numV(props['top'], c), b = numV(props['bottom'], c), ht = numV(props['height'], c);
              w = Positioned(left: l, top: t, right: (l != null && wd != null) ? null : r,
                  bottom: (t != null && ht != null) ? null : b, width: (l != null && r != null) ? null : wd,
                  height: (t != null && b != null) ? null : ht, child: inner);
            }
          case 'Expanded':
            w = Expanded(flex: intV(props['flex'], c) ?? 1, child: inner);
          case 'Flexible':
            w = Flexible(flex: intV(props['flex'], c) ?? 1, fit: enumV(FlexFit.values, props['fit']) ?? FlexFit.loose,
                child: inner);
          default: // Spacer = Expanded with an empty child (so it gets a rect)
            w = Expanded(flex: intV(props['flex'], c) ?? 1, child: inner);
        }
      } catch (e) {
        host.nodeIssue(id, 'error', '$e');
        w = inner;
      }
      for (final m in warns) {
        host.nodeIssue(id, 'warning', m);
      }
      return w;
    }

    try {
      w = _build(context, n, id, type, c);
    } catch (e) {
      host.nodeIssue(id, 'error', '$e');
      w = HostErrorBox(message: '$type: $e');
    }
    for (final m in warns) {
      host.nodeIssue(id, 'warning', m);
    }
    if (n['anim'] is Map) w = _fx(n['anim'] as Map, w, id);
    return NodeBox(key: ValueKey('rad:$id'), id: id, type: type, child: w);
  }

  Widget _fx(Map anim, Widget w, String id) =>
      HostFx(key: ValueKey('fx:$id:${host.epoch}'), anim: anim, playing: host.playing, child: w);

  // ------------------------------------------------------------------------------------------- helpers
  Widget? _slot(BuildContext context, Map n, String name, {String parent = ''}) {
    final s = (n['slots'] as Map?)?[name];
    if (s == null || s is List) return null;
    return node(context, s, parent: parent);
  }

  List<Widget> _slotList(BuildContext context, Map n, String name) {
    final s = (n['slots'] as Map?)?[name];
    if (s is List) return [for (final x in s) node(context, x)];
    if (s is Map) return [node(context, s)];
    return const [];
  }

  List<Widget> _children(BuildContext context, Map n, String type) {
    final ch = n['children'];
    if (ch is! List) return const [];
    return [for (final x in ch) node(context, x, parent: type)];
  }

  /// A PreferredSizeWidget slot (Scaffold.appBar / AppBar.bottom): built, then wrapped keeping its size.
  PreferredSizeWidget? _preferred(BuildContext context, Map n, String name) {
    final s = (n['slots'] as Map?)?[name];
    if (s is! Map) return null;
    final w = node(context, s);
    return PreferredNodeBox(preferredSize: _prefSize(s), child: w);
  }

  /// Preferred size of an AppBar / TabBar node (without building it twice).
  static Size _prefSize(Map s) {
    final props = (s['props'] as Map?) ?? const {};
    if (s['type'] == 'TabBar') {
      var withIcon = false, withText = false;
      for (final t in (s['children'] as List? ?? const [])) {
        if (t is! Map) continue;
        if ((t['slots'] as Map?)?['icon'] != null) withIcon = true;
        if ((t['props'] as Map?)?['text'] != null || (t['slots'] as Map?)?['child'] != null) withText = true;
      }
      return Size.fromHeight(withIcon && withText ? 72 : 46);
    }
    if (s['type'] == 'AppBar') {
      final h = numV(props['toolbarHeight']) ?? kToolbarHeight;
      final bottom = (s['slots'] as Map?)?['bottom'];
      return Size.fromHeight(h + (bottom is Map ? _prefSize(bottom).height : 0));
    }
    if (s['type'] == 'CupertinoNavigationBar') return const Size.fromHeight(44);
    return const Size.fromHeight(kToolbarHeight);
  }

  VoidCallback _cb(Map n, String ev) {
    final h = (n['events'] as Map?)?[ev] as String?;
    final id = '${n['id']}';
    return () => host.event(id, ev, h);
  }

  VoidCallback? _cbOpt(Map n, String ev) {
    final h = (n['events'] as Map?)?[ev] as String?;
    if (h == null || h.isEmpty) return null;
    return _cb(n, ev);
  }

  void Function(T) _vcb<T>(Map n, String ev, {bool store = true}) {
    final h = (n['events'] as Map?)?[ev] as String?;
    final id = '${n['id']}';
    return (T v) {
      if (store) host.setValue(id, v);
      host.event(id, ev, h, v);
    };
  }

  static final _kbd = {
    'text': TextInputType.text, 'multiline': TextInputType.multiline, 'number': TextInputType.number,
    'phone': TextInputType.phone, 'datetime': TextInputType.datetime, 'emailAddress': TextInputType.emailAddress,
    'url': TextInputType.url, 'visiblePassword': TextInputType.visiblePassword, 'name': TextInputType.name,
    'streetAddress': TextInputType.streetAddress,
  };
  static final _fabLoc = {
    'endFloat': FloatingActionButtonLocation.endFloat, 'centerFloat': FloatingActionButtonLocation.centerFloat,
    'startFloat': FloatingActionButtonLocation.startFloat, 'endDocked': FloatingActionButtonLocation.endDocked,
    'centerDocked': FloatingActionButtonLocation.centerDocked, 'endTop': FloatingActionButtonLocation.endTop,
    'startTop': FloatingActionButtonLocation.startTop, 'centerTop': FloatingActionButtonLocation.centerTop,
  };

  static String _tail(dynamic v) => v is String ? v.split('.').last : '';

  Widget _codeNode(BuildContext context, Map n, String id) {
    final code = '${(n['props'] as Map?)?['code'] ?? ''}'.replaceAll(RegExp(r'\s+'), ' ').trim();
    final slots = (n['slots'] as Map?) ?? const {};
    Widget? inner;
    for (final e in slots.entries) {
      final v = e.value;
      if (v is Map) {
        inner = node(context, v);
        break;
      }
      if (v is List && v.isNotEmpty) {
        inner = Column(mainAxisSize: MainAxisSize.min, children: [for (final x in v) node(context, x)]);
        break;
      }
    }
    final label = Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
      color: const Color(0xCCFF8F00),
      child: Text(code.length > 48 ? '${code.substring(0, 48)}...' : code,
          maxLines: 1, overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 10, color: Colors.white, fontFamily: 'monospace',
              decoration: TextDecoration.none)),
    );
    final border = BoxDecoration(border: Border.all(color: const Color(0xFFFF8F00), width: 1.2));
    if (inner == null) {
      return Container(
        constraints: const BoxConstraints(minWidth: 60, minHeight: 32),
        decoration: border.copyWith(color: const Color(0x14FF8F00)),
        alignment: Alignment.center,
        padding: const EdgeInsets.all(2),
        child: label,
      );
    }
    return Stack(clipBehavior: Clip.none, children: [
      DecoratedBox(position: DecorationPosition.foreground, decoration: border, child: inner),
      Positioned(left: 0, top: 0, child: IgnorePointer(child: label)),
    ]);
  }

  // --------------------------------------------------------------------------------------------- build
  Widget _build(BuildContext context, Map n, String id, String type, VCtx c) {
    final p = (n['props'] as Map?) ?? const {};
    final ctor = n['ctor'] as String?;
    Widget? child() => _slot(context, n, 'child');
    Widget? slot(String s) => _slot(context, n, s);
    double? d(String k) => numV(p[k], c);
    int? i(String k) => intV(p[k], c);
    bool? b(String k) => boolV(p[k]);
    String? s(String k) => strV(p[k]);
    Color? col(String k) => colorV(p[k], c);
    EdgeInsets? e(String k) => edgeV(p[k], c);
    TextStyle? ts(String k) => textStyleV(p[k], c);

    switch (type) {
      case 'Code':
        return _codeNode(context, n, id);

      // ------------------------------------------------------------------------------------ layout
      case 'Scaffold':
        final drawerIds = <String>{};
        for (final k in ['drawer', 'endDrawer']) {
          void walk(dynamic x) {
            if (x is! Map) return;
            if (x['id'] != null) drawerIds.add('${x['id']}');
            final sl = x['slots'];
            if (sl is Map) {
              for (final v in sl.values) {
                if (v is List) {
                  v.forEach(walk);
                } else {
                  walk(v);
                }
              }
            }
            final ch = x['children'];
            if (ch is List) ch.forEach(walk);
          }
          walk((n['slots'] as Map?)?[k]);
        }
        host.drawerNodes(id, drawerIds);
        final footer = _slotList(context, n, 'persistentFooterButtons');
        return Scaffold(
          key: host.scaffoldKey(id),
          appBar: _preferred(context, n, 'appBar'),
          body: slot('body'),
          floatingActionButton: slot('floatingActionButton'),
          drawer: slot('drawer'),
          endDrawer: slot('endDrawer'),
          bottomNavigationBar: slot('bottomNavigationBar'),
          bottomSheet: slot('bottomSheet'),
          persistentFooterButtons: footer.isEmpty ? null : footer,
          backgroundColor: col('backgroundColor'),
          extendBodyBehindAppBar: b('extendBodyBehindAppBar') ?? false,
          extendBody: b('extendBody') ?? false,
          resizeToAvoidBottomInset: b('resizeToAvoidBottomInset'),
          floatingActionButtonLocation: _fabLoc[_tail(p['floatingActionButtonLocation'])],
        );
      case 'SafeArea':
        return SafeArea(top: b('top') ?? true, bottom: b('bottom') ?? true, left: b('left') ?? true,
            right: b('right') ?? true, minimum: e('minimum') ?? EdgeInsets.zero, child: child() ?? const SizedBox());
      case 'Container':
      case 'AnimatedContainer':
        var deco = decorationV(p['decoration'], c);
        var color = col('color');
        if (deco != null && color != null) {
          c.warn('Container: color and decoration cannot both be set (use decoration.color)');
          color = null;
        }
        var clip = enumV(Clip.values, p['clipBehavior']) ?? Clip.none;
        if (clip != Clip.none && deco == null) clip = Clip.none;
        if (type == 'AnimatedContainer') {
          return AnimatedContainer(duration: durationV(p['duration'], c) ?? const Duration(milliseconds: 300),
              curve: curveV(p['curve']) ?? Curves.linear, alignment: alignV(p['alignment'], c),
              padding: e('padding'), margin: e('margin'), width: d('width'), height: d('height'), color: color,
              decoration: deco, constraints: constraintsV(p['constraints'], c), clipBehavior: clip, child: child());
        }
        return Container(alignment: alignV(p['alignment'], c), padding: e('padding'), margin: e('margin'),
            width: d('width'), height: d('height'), color: color, decoration: deco,
            constraints: constraintsV(p['constraints'], c), clipBehavior: clip, child: child());
      case 'Padding':
        return Padding(padding: e('padding') ?? EdgeInsets.zero, child: child());
      case 'Center':
        return Center(widthFactor: d('widthFactor'), heightFactor: d('heightFactor'), child: child());
      case 'Align':
        return Align(alignment: alignV(p['alignment'], c) ?? Alignment.center, widthFactor: d('widthFactor'),
            heightFactor: d('heightFactor'), child: child());
      case 'Column':
      case 'Row':
      case 'Flex':
        final dir = type == 'Column'
            ? Axis.vertical
            : type == 'Row'
                ? Axis.horizontal
                : (enumV(Axis.values, p['direction']) ?? Axis.horizontal);
        return Flex(
          direction: dir,
          mainAxisAlignment: enumV(MainAxisAlignment.values, p['mainAxisAlignment']) ?? MainAxisAlignment.start,
          crossAxisAlignment:
              enumV(CrossAxisAlignment.values, p['crossAxisAlignment']) ?? CrossAxisAlignment.center,
          mainAxisSize: enumV(MainAxisSize.values, p['mainAxisSize']) ?? MainAxisSize.max,
          textBaseline: enumV(CrossAxisAlignment.values, p['crossAxisAlignment']) == CrossAxisAlignment.baseline
              ? TextBaseline.alphabetic
              : null,
          spacing: d('spacing') ?? 0,
          children: _children(context, n, type),
        );
      case 'Wrap':
        return Wrap(
          direction: enumV(Axis.values, p['direction']) ?? Axis.horizontal,
          alignment: enumV(WrapAlignment.values, p['alignment']) ?? WrapAlignment.start,
          spacing: d('spacing') ?? 0,
          runSpacing: d('runSpacing') ?? 0,
          runAlignment: enumV(WrapAlignment.values, p['runAlignment']) ?? WrapAlignment.start,
          crossAxisAlignment: enumV(WrapCrossAlignment.values, p['crossAxisAlignment']) ?? WrapCrossAlignment.start,
          children: _children(context, n, type),
        );
      case 'Stack':
        return Stack(
          alignment: alignV(p['alignment'], c) ?? AlignmentDirectional.topStart,
          fit: enumV(StackFit.values, p['fit']) ?? StackFit.loose,
          clipBehavior: enumV(Clip.values, p['clipBehavior']) ?? Clip.hardEdge,
          children: _children(context, n, type),
        );
      case 'SizedBox':
        switch (ctor) {
          case 'expand':
            return SizedBox.expand(child: child());
          case 'shrink':
            return SizedBox.shrink(child: child());
          case 'square':
            return SizedBox.square(dimension: d('dimension'), child: child());
        }
        return SizedBox(width: d('width'), height: d('height'), child: child());
      case 'ConstrainedBox':
        return ConstrainedBox(constraints: constraintsV(p['constraints'], c) ?? const BoxConstraints(),
            child: child());
      case 'AspectRatio':
        return AspectRatio(aspectRatio: (d('aspectRatio') ?? 1).clamp(0.01, 1000.0), child: child());
      case 'FractionallySizedBox':
        return FractionallySizedBox(widthFactor: d('widthFactor'), heightFactor: d('heightFactor'),
            alignment: alignV(p['alignment'], c) ?? Alignment.center, child: child());
      case 'FittedBox':
        return FittedBox(fit: enumV(BoxFit.values, p['fit']) ?? BoxFit.contain,
            alignment: alignV(p['alignment'], c) ?? Alignment.center, child: child());
      case 'Transform':
        switch (ctor ?? 'rotate') {
          case 'scale':
            return Transform.scale(scale: d('scale') ?? 1, alignment: alignV(p['alignment'], c) ?? Alignment.center,
                child: child());
          case 'translate':
            return Transform.translate(offset: offsetV(p['offset'], c) ?? Offset.zero, child: child());
        }
        return Transform.rotate(angle: d('angle') ?? 0, alignment: alignV(p['alignment'], c) ?? Alignment.center,
            child: child());
      case 'Visibility':
        return Visibility(visible: b('visible') ?? true, child: child() ?? const SizedBox());
      case 'IntrinsicHeight':
        return IntrinsicHeight(child: child());

      // ------------------------------------------------------------------------------------ scroll
      case 'SingleChildScrollView':
        return SingleChildScrollView(scrollDirection: enumV(Axis.values, p['scrollDirection']) ?? Axis.vertical,
            padding: e('padding'), reverse: b('reverse') ?? false, physics: physicsV(p['physics']), child: child());
      case 'ListView':
        return ListView(scrollDirection: enumV(Axis.values, p['scrollDirection']) ?? Axis.vertical,
            padding: e('padding'), reverse: b('reverse') ?? false, physics: physicsV(p['physics']),
            shrinkWrap: b('shrinkWrap') ?? false, itemExtent: d('itemExtent'), children: _children(context, n, type));
      case 'GridView':
        final dir = enumV(Axis.values, p['scrollDirection']) ?? Axis.vertical;
        if (ctor == 'extent') {
          return GridView.extent(maxCrossAxisExtent: d('maxCrossAxisExtent') ?? 150, scrollDirection: dir,
              padding: e('padding'), reverse: b('reverse') ?? false, physics: physicsV(p['physics']),
              shrinkWrap: b('shrinkWrap') ?? false, mainAxisSpacing: d('mainAxisSpacing') ?? 0,
              crossAxisSpacing: d('crossAxisSpacing') ?? 0, childAspectRatio: d('childAspectRatio') ?? 1,
              children: _children(context, n, type));
        }
        return GridView.count(crossAxisCount: (i('crossAxisCount') ?? 2).clamp(1, 100), scrollDirection: dir,
            padding: e('padding'), reverse: b('reverse') ?? false, physics: physicsV(p['physics']),
            shrinkWrap: b('shrinkWrap') ?? false, mainAxisSpacing: d('mainAxisSpacing') ?? 0,
            crossAxisSpacing: d('crossAxisSpacing') ?? 0, childAspectRatio: d('childAspectRatio') ?? 1,
            children: _children(context, n, type));
      case 'PageView':
        return PageView(scrollDirection: enumV(Axis.values, p['scrollDirection']) ?? Axis.horizontal,
            physics: physicsV(p['physics']), pageSnapping: b('pageSnapping') ?? true, reverse: b('reverse') ?? false,
            onPageChanged: _vcb<int>(n, 'onPageChanged', store: false), children: _children(context, n, type));

      // ----------------------------------------------------------------------------------- content
      case 'Text':
        return Text(s('data') ?? '', style: ts('style'), textAlign: enumV(TextAlign.values, p['textAlign']),
            maxLines: i('maxLines'), overflow: enumV(TextOverflow.values, p['overflow']), softWrap: b('softWrap'));
      case 'SelectableText':
        return SelectableText(s('data') ?? '', style: ts('style'), textAlign: enumV(TextAlign.values, p['textAlign']),
            maxLines: i('maxLines'));
      case 'Icon':
        final icon = iconV(p['icon']);
        if (icon == null && p['icon'] != null) c.warn('unknown icon ${p['icon']}');
        return Icon(icon ?? Icons.help_outline, size: d('size'), color: col('color'));
      case 'Image':
        final src = s('src') ?? '';
        final url = imageUrl(src, c);
        return Image.network(url, width: d('width'), height: d('height'), fit: enumV(BoxFit.values, p['fit']),
            alignment: alignV(p['alignment'], c) ?? Alignment.center, color: col('color'),
            webHtmlElementStrategy: WebHtmlElementStrategy.fallback,
            errorBuilder: (ctx, err, st) => Container(
                  width: d('width'), height: d('height'), color: const Color(0x11000000),
                  alignment: Alignment.center,
                  child: const Icon(Icons.broken_image_outlined, color: Color(0x88000000)),
                ));
      case 'CircleAvatar':
        return CircleAvatar(radius: d('radius'), backgroundColor: col('backgroundColor'),
            foregroundColor: col('foregroundColor'), backgroundImage: imageV(p['backgroundImage'], c), child: child());
      case 'Divider':
        return Divider(height: d('height'), thickness: d('thickness'), indent: d('indent'), endIndent: d('endIndent'),
            color: col('color'));
      case 'VerticalDivider':
        return VerticalDivider(width: d('width'), thickness: d('thickness'), indent: d('indent'),
            endIndent: d('endIndent'), color: col('color'));
      case 'Placeholder':
        return Placeholder(color: col('color') ?? const Color(0xFF455A64), fallbackWidth: d('fallbackWidth') ?? 400,
            fallbackHeight: d('fallbackHeight') ?? 400, strokeWidth: d('strokeWidth') ?? 2);
      case 'CircularProgressIndicator':
        return CircularProgressIndicator(value: d('value'), color: col('color'),
            backgroundColor: col('backgroundColor'), strokeWidth: d('strokeWidth') ?? 4);
      case 'LinearProgressIndicator':
        return LinearProgressIndicator(value: d('value'), color: col('color'), backgroundColor: col('backgroundColor'),
            minHeight: d('minHeight'));
      case 'Chip':
        final del = _cbOpt(n, 'onDeleted');
        return Chip(label: slot('label') ?? const Text(''), avatar: slot('avatar'), deleteIcon: slot('deleteIcon'),
            onDeleted: del ?? (slot('deleteIcon') != null ? _cb(n, 'onDeleted') : null),
            backgroundColor: col('backgroundColor'), padding: e('padding'), labelStyle: ts('labelStyle'));
      case 'Badge':
        return Badge(label: slot('label'), backgroundColor: col('backgroundColor'), textColor: col('textColor'),
            isLabelVisible: b('isLabelVisible') ?? true, child: child());
      case 'Tooltip':
        return Tooltip(message: s('message') ?? '', child: child());
      case 'FlutterLogo':
        return FlutterLogo(size: d('size'));

      // ------------------------------------------------------------------------------------- input
      case 'TextField':
      case 'TextFormField':
        final obscure = b('obscureText') ?? false;
        final maxLines = obscure ? 1 : (p.containsKey('maxLines') ? i('maxLines') : 1);
        final minLines = obscure ? null : i('minLines');
        final common = (
          controller: host.controller(id),
          decoration: inputDecorationV(p['decoration'], c) ?? const InputDecoration(),
          kbd: _kbd[_tail(p['keyboardType'])],
          action: enumV(TextInputAction.values, p['textInputAction']),
        );
        if (type == 'TextFormField') {
          return TextFormField(controller: common.controller, decoration: common.decoration, obscureText: obscure,
              keyboardType: common.kbd, textInputAction: common.action, maxLines: maxLines,
              minLines: (minLines != null && maxLines != null && minLines > maxLines) ? null : minLines,
              maxLength: i('maxLength'), style: ts('style'),
              textAlign: enumV(TextAlign.values, p['textAlign']) ?? TextAlign.start, enabled: b('enabled'),
              autofocus: host.interactive && (b('autofocus') ?? false), readOnly: b('readOnly') ?? false,
              cursorColor: col('cursorColor'), onChanged: _vcb<String>(n, 'onChanged', store: false),
              onFieldSubmitted: _vcb<String>(n, 'onFieldSubmitted', store: false), onTap: _cbOpt(n, 'onTap'));
        }
        return TextField(controller: common.controller, decoration: common.decoration, obscureText: obscure,
            keyboardType: common.kbd, textInputAction: common.action, maxLines: maxLines,
            minLines: (minLines != null && maxLines != null && minLines > maxLines) ? null : minLines,
            maxLength: i('maxLength'), style: ts('style'),
            textAlign: enumV(TextAlign.values, p['textAlign']) ?? TextAlign.start, enabled: b('enabled'),
            autofocus: host.interactive && (b('autofocus') ?? false), readOnly: b('readOnly') ?? false,
            cursorColor: col('cursorColor'), onChanged: _vcb<String>(n, 'onChanged', store: false),
            onSubmitted: _vcb<String>(n, 'onSubmitted', store: false), onTap: _cbOpt(n, 'onTap'));
      case 'Checkbox':
        return Checkbox(value: host.value(id, boolV(p['value']) ?? false) as bool? ?? false,
            onChanged: _vcb<bool?>(n, 'onChanged'), activeColor: col('activeColor'), checkColor: col('checkColor'));
      case 'Switch':
        return Switch(value: host.value(id, boolV(p['value']) ?? false) as bool? ?? false,
            onChanged: _vcb<bool>(n, 'onChanged'), activeThumbColor: col('activeThumbColor'),
            activeTrackColor: col('activeTrackColor'), inactiveThumbColor: col('inactiveThumbColor'),
            inactiveTrackColor: col('inactiveTrackColor'));
      case 'Slider':
        final mn = d('min') ?? 0.0, mx0 = d('max') ?? 1.0;
        final mx = mx0 > mn ? mx0 : mn + 1;
        final v = (numV(host.value(id, d('value') ?? 0.5)) ?? mn).clamp(mn, mx).toDouble();
        final div = i('divisions');
        return Slider(value: v, min: mn, max: mx, divisions: (div != null && div > 0) ? div : null,
            label: s('label'), activeColor: col('activeColor'), inactiveColor: col('inactiveColor'),
            onChanged: _vcb<double>(n, 'onChanged'), onChangeEnd: _vcb<double>(n, 'onChangeEnd', store: false));
      case 'DropdownButton':
        final items = stringListV(p['items']);
        final uniq = <String>{...items}.toList();
        var v = host.value(id, s('value')) as String?;
        if (v != null && !uniq.contains(v)) v = null;
        return DropdownButton<String>(
          value: v,
          items: [for (final it in uniq) DropdownMenuItem<String>(value: it, child: Text(it))],
          hint: p['hint'] != null ? Text(s('hint') ?? '') : null,
          isExpanded: b('isExpanded') ?? false,
          onChanged: _vcb<String?>(n, 'onChanged'),
        );
      case 'CheckboxListTile':
        return CheckboxListTile(value: host.value(id, boolV(p['value']) ?? false) as bool? ?? false,
            onChanged: _vcb<bool?>(n, 'onChanged'), title: slot('title'), subtitle: slot('subtitle'),
            secondary: slot('secondary'),
            controlAffinity: enumV(ListTileControlAffinity.values, p['controlAffinity']) ??
                ListTileControlAffinity.platform,
            activeColor: col('activeColor'));
      case 'SwitchListTile':
        return SwitchListTile(value: host.value(id, boolV(p['value']) ?? false) as bool? ?? false,
            onChanged: _vcb<bool>(n, 'onChanged'), title: slot('title'), subtitle: slot('subtitle'),
            secondary: slot('secondary'),
            controlAffinity: enumV(ListTileControlAffinity.values, p['controlAffinity']) ??
                ListTileControlAffinity.platform,
            activeThumbColor: col('activeThumbColor'));
      case 'Form':
        return Form(child: child() ?? const SizedBox());
      case 'InkWell':
        return InkWell(borderRadius: radiusV(p['borderRadius'], c), splashColor: col('splashColor'),
            onTap: _cb(n, 'onTap'), onDoubleTap: _cbOpt(n, 'onDoubleTap'), onLongPress: _cbOpt(n, 'onLongPress'),
            child: child());
      case 'GestureDetector':
        return GestureDetector(behavior: enumV(HitTestBehavior.values, p['behavior']), onTap: _cb(n, 'onTap'),
            onDoubleTap: _cbOpt(n, 'onDoubleTap'), onLongPress: _cbOpt(n, 'onLongPress'), child: child());

      // ----------------------------------------------------------------------------------- buttons
      case 'ElevatedButton':
      case 'FilledButton':
      case 'TextButton':
      case 'OutlinedButton':
        final style = buttonStyleV(p['style'], c, type);
        final onP = _cb(n, 'onPressed');
        final onL = _cbOpt(n, 'onLongPress');
        final isIcon = ctor == 'icon' || ctor == 'tonalIcon';
        final label = isIcon ? (slot('label') ?? const Text('')) : null;
        final icon = isIcon ? slot('icon') : null;
        final ch = child() ?? const Text('');
        switch (type) {
          case 'ElevatedButton':
            return isIcon
                ? ElevatedButton.icon(onPressed: onP, onLongPress: onL, style: style, icon: icon, label: label!)
                : ElevatedButton(onPressed: onP, onLongPress: onL, style: style, child: ch);
          case 'FilledButton':
            if (ctor == 'tonal') return FilledButton.tonal(onPressed: onP, onLongPress: onL, style: style, child: ch);
            if (ctor == 'tonalIcon') {
              return FilledButton.tonalIcon(onPressed: onP, onLongPress: onL, style: style, icon: icon, label: label!);
            }
            return isIcon
                ? FilledButton.icon(onPressed: onP, onLongPress: onL, style: style, icon: icon, label: label!)
                : FilledButton(onPressed: onP, onLongPress: onL, style: style, child: ch);
          case 'TextButton':
            return isIcon
                ? TextButton.icon(onPressed: onP, onLongPress: onL, style: style, icon: icon, label: label!)
                : TextButton(onPressed: onP, onLongPress: onL, style: style, child: ch);
          default:
            return isIcon
                ? OutlinedButton.icon(onPressed: onP, onLongPress: onL, style: style, icon: icon, label: label!)
                : OutlinedButton(onPressed: onP, onLongPress: onL, style: style, child: ch);
        }
      case 'IconButton':
        final icon = slot('icon') ?? const Icon(Icons.help_outline);
        final onP = _cb(n, 'onPressed');
        switch (ctor) {
          case 'filled':
            return IconButton.filled(onPressed: onP, icon: icon, iconSize: d('iconSize'), color: col('color'),
                tooltip: s('tooltip'), padding: e('padding'));
          case 'filledTonal':
            return IconButton.filledTonal(onPressed: onP, icon: icon, iconSize: d('iconSize'), color: col('color'),
                tooltip: s('tooltip'), padding: e('padding'));
          case 'outlined':
            return IconButton.outlined(onPressed: onP, icon: icon, iconSize: d('iconSize'), color: col('color'),
                tooltip: s('tooltip'), padding: e('padding'));
        }
        return IconButton(onPressed: onP, icon: icon, iconSize: d('iconSize'), color: col('color'),
            tooltip: s('tooltip'), padding: e('padding'));
      case 'MaterialButton':
        return MaterialButton(onPressed: _cb(n, 'onPressed'), onLongPress: _cbOpt(n, 'onLongPress'),
            color: col('color'), textColor: col('textColor'), elevation: d('elevation'), padding: e('padding'),
            minWidth: d('minWidth'), height: d('height'), shape: shapeV(p['shape'], c), child: child());
      case 'FloatingActionButton':
        if (ctor == 'extended') {
          return FloatingActionButton.extended(onPressed: _cb(n, 'onPressed'), label: slot('label') ?? const Text(''),
              icon: slot('icon'), backgroundColor: col('backgroundColor'), foregroundColor: col('foregroundColor'),
              tooltip: s('tooltip'), elevation: d('elevation'), shape: shapeV(p['shape'], c),
              heroTag: 'fab:$id');
        }
        return FloatingActionButton(onPressed: _cb(n, 'onPressed'), backgroundColor: col('backgroundColor'),
            foregroundColor: col('foregroundColor'), tooltip: s('tooltip'), mini: b('mini') ?? false,
            elevation: d('elevation'), shape: shapeV(p['shape'], c), heroTag: 'fab:$id', child: child());

      // ---------------------------------------------------------------------------------- material
      case 'AppBar':
        final actions = _slotList(context, n, 'actions');
        return AppBar(title: slot('title'), leading: slot('leading'), actions: actions.isEmpty ? null : actions,
            flexibleSpace: slot('flexibleSpace'), bottom: _preferred(context, n, 'bottom'),
            backgroundColor: col('backgroundColor'), foregroundColor: col('foregroundColor'),
            elevation: d('elevation'), centerTitle: b('centerTitle'),
            automaticallyImplyLeading: b('automaticallyImplyLeading') ?? true, toolbarHeight: d('toolbarHeight'));
      case 'Card':
        return Card(color: col('color'), elevation: d('elevation'), margin: e('margin'), shape: shapeV(p['shape'], c),
            clipBehavior: enumV(Clip.values, p['clipBehavior']), shadowColor: col('shadowColor'), child: child());
      case 'ListTile':
        return ListTile(leading: slot('leading'), title: slot('title'), subtitle: slot('subtitle'),
            trailing: slot('trailing'), dense: b('dense'), contentPadding: e('contentPadding'),
            tileColor: col('tileColor'), selected: b('selected') ?? false, enabled: b('enabled') ?? true,
            onTap: _cbOpt(n, 'onTap'), onLongPress: _cbOpt(n, 'onLongPress'));
      case 'ExpansionTile':
        return ExpansionTile(title: slot('title') ?? const Text(''), subtitle: slot('subtitle'),
            leading: slot('leading'), trailing: slot('trailing'),
            initiallyExpanded: b('initiallyExpanded') ?? false, backgroundColor: col('backgroundColor'),
            collapsedBackgroundColor: col('collapsedBackgroundColor'),
            onExpansionChanged: _vcb<bool>(n, 'onExpansionChanged', store: false),
            children: _children(context, n, type));
      case 'Material':
        return Material(color: col('color'), elevation: d('elevation') ?? 0, borderRadius: radiusV(p['borderRadius'], c),
            shadowColor: col('shadowColor'), child: child());

      // -------------------------------------------------------------------------------- navigation
      case 'BottomNavigationBar':
        final items = _navItems(p['items'], c, false).cast<BottomNavigationBarItem>();
        if (items.length < 2) {
          c.warn('BottomNavigationBar needs at least 2 items');
          return HostErrorBox(message: 'BottomNavigationBar needs at least 2 items');
        }
        final cur = (intV(host.value(id, i('currentIndex') ?? 0)) ?? 0).clamp(0, items.length - 1);
        return BottomNavigationBar(items: items, currentIndex: cur, onTap: _vcb<int>(n, 'onTap'),
            type: enumV(BottomNavigationBarType.values, p['type']), backgroundColor: col('backgroundColor'),
            selectedItemColor: col('selectedItemColor'), unselectedItemColor: col('unselectedItemColor'),
            iconSize: d('iconSize') ?? 24, showUnselectedLabels: b('showUnselectedLabels'));
      case 'NavigationBar':
        final items = _navItems(p['destinations'], c, true);
        if (items.length < 2) {
          c.warn('NavigationBar needs at least 2 destinations');
          return HostErrorBox(message: 'NavigationBar needs at least 2 destinations');
        }
        final cur = (intV(host.value(id, i('selectedIndex') ?? 0)) ?? 0).clamp(0, items.length - 1);
        return NavigationBar(destinations: items.cast<Widget>(), selectedIndex: cur,
            onDestinationSelected: _vcb<int>(n, 'onDestinationSelected'), backgroundColor: col('backgroundColor'),
            indicatorColor: col('indicatorColor'));
      case 'Drawer':
        return Drawer(backgroundColor: col('backgroundColor'), width: d('width'), elevation: d('elevation'),
            child: child());
      case 'DrawerHeader':
        return DrawerHeader(decoration: decorationV(p['decoration'], c),
            padding: e('padding') ?? const EdgeInsets.fromLTRB(16, 16, 16, 8),
            margin: e('margin') ?? const EdgeInsets.only(bottom: 8), child: child());
      case 'TabBar':
        final tabs = _children(context, n, type);
        final bar = TabBar(tabs: tabs, isScrollable: b('isScrollable') ?? false, indicatorColor: col('indicatorColor'),
            labelColor: col('labelColor'), unselectedLabelColor: col('unselectedLabelColor'),
            indicatorSize: enumV(TabBarIndicatorSize.values, p['indicatorSize']), onTap: _vcb<int>(n, 'onTap', store: false));
        return _TabScope(length: tabs.length, child: bar);
      case 'Tab':
        final ch = child();
        final text = s('text');
        return Tab(text: ch == null ? text : null, height: d('height'), icon: slot('icon'), child: ch);
      case 'TabBarView':
        final pages = _children(context, n, type);
        return _TabScope(length: pages.length,
            child: TabBarView(physics: physicsV(p['physics']), children: pages));
      case 'DefaultTabController':
        var len = 0;
        void count(dynamic x) {
          if (x is! Map) return;
          if (x['type'] == 'TabBar' && len == 0) {
            len = (x['children'] as List?)?.length ?? 0;
            return;
          }
          final sl = x['slots'];
          if (sl is Map) {
            for (final v in sl.values) {
              if (v is List) {
                v.forEach(count);
              } else {
                count(v);
              }
            }
          }
          final ch = x['children'];
          if (ch is List) ch.forEach(count);
        }
        count(n);
        final want = i('length');
        if (len == 0) len = want ?? 2;
        if (want != null && want != len) c.warn('length is $want but the TabBar has $len tabs');
        return DefaultTabController(length: len, initialIndex: (i('initialIndex') ?? 0).clamp(0, len - 1),
            child: child() ?? const SizedBox());

      // ----------------------------------------------------------------------------------- effects
      case 'Opacity':
        return Opacity(opacity: (d('opacity') ?? 1).clamp(0.0, 1.0), child: child());
      case 'ClipRRect':
        return ClipRRect(borderRadius: radiusV(p['borderRadius'], c) ?? BorderRadius.zero,
            clipBehavior: enumV(Clip.values, p['clipBehavior']) ?? Clip.antiAlias, child: child());
      case 'ClipOval':
        return ClipOval(clipBehavior: enumV(Clip.values, p['clipBehavior']) ?? Clip.antiAlias, child: child());
      case 'Hero':
        return Hero(tag: '${s('tag') ?? 'hero'}#$id', child: child() ?? const SizedBox());
      case 'DecoratedBox':
        return DecoratedBox(decoration: decorationV(p['decoration'], c) ?? const BoxDecoration(), child: child());
      case 'RotatedBox':
        return RotatedBox(quarterTurns: i('quarterTurns') ?? 1, child: child());

      // --------------------------------------------------------------------------------- animation
      case 'AnimatedOpacity':
        return AnimatedOpacity(opacity: (d('opacity') ?? 1).clamp(0.0, 1.0),
            duration: durationV(p['duration'], c) ?? const Duration(milliseconds: 300),
            curve: curveV(p['curve']) ?? Curves.linear, child: child());
      case 'AnimatedSwitcher':
        return AnimatedSwitcher(duration: durationV(p['duration'], c) ?? const Duration(milliseconds: 300),
            child: child());

      // --------------------------------------------------------------------------------- cupertino
      case 'CupertinoPageScaffold':
        ObstructingPreferredSizeWidget? nav;
        final navNode = (n['slots'] as Map?)?['navigationBar'];
        if (navNode is Map) {
          final w = node(context, navNode);
          var size = const Size.fromHeight(44);
          var obstruct = true;
          if (navNode['type'] == 'CupertinoNavigationBar') {
            final bg = colorV((navNode['props'] as Map?)?['backgroundColor'], c);
            obstruct = bg == null || bg.a >= 1.0;
          }
          nav = ObstructingNodeBox(preferredSize: size, obstruct: obstruct, child: w);
        }
        return CupertinoPageScaffold(backgroundColor: col('backgroundColor'), navigationBar: nav,
            child: child() ?? const SizedBox());
      case 'CupertinoNavigationBar':
        return CupertinoNavigationBar(backgroundColor: col('backgroundColor'), leading: slot('leading'),
            middle: slot('middle'), trailing: slot('trailing'));
      case 'CupertinoButton':
        if (ctor == 'filled') {
          return CupertinoButton.filled(padding: e('padding'), onPressed: _cb(n, 'onPressed'),
              child: child() ?? const Text(''));
        }
        return CupertinoButton(color: col('color'), padding: e('padding'), onPressed: _cb(n, 'onPressed'),
            child: child() ?? const Text(''));
      case 'CupertinoTextField':
        return CupertinoTextField(controller: host.controller(id), placeholder: s('placeholder'),
            obscureText: b('obscureText') ?? false, padding: e('padding') ?? const EdgeInsets.all(7),
            keyboardType: _kbd[_tail(p['keyboardType'])], style: ts('style'),
            onChanged: _vcb<String>(n, 'onChanged', store: false),
            onSubmitted: _vcb<String>(n, 'onSubmitted', store: false));
      case 'CupertinoSwitch':
        return CupertinoSwitch(value: host.value(id, boolV(p['value']) ?? false) as bool? ?? false,
            onChanged: _vcb<bool>(n, 'onChanged'), activeTrackColor: col('activeTrackColor'));
      case 'CupertinoSlider':
        final mn = d('min') ?? 0.0, mx0 = d('max') ?? 1.0;
        final mx = mx0 > mn ? mx0 : mn + 1;
        final v = (numV(host.value(id, d('value') ?? 0.5)) ?? mn).clamp(mn, mx).toDouble();
        final div = i('divisions');
        return CupertinoSlider(value: v, min: mn, max: mx, divisions: (div != null && div > 0) ? div : null,
            activeColor: col('activeColor'), onChanged: _vcb<double>(n, 'onChanged'));
      case 'CupertinoActivityIndicator':
        return CupertinoActivityIndicator(radius: d('radius') ?? 10, color: col('color'),
            animating: b('animating') ?? true);
      case 'CupertinoListTile':
        return CupertinoListTile(title: slot('title') ?? const Text(''), subtitle: slot('subtitle'),
            leading: slot('leading'), trailing: slot('trailing'), backgroundColor: col('backgroundColor'),
            onTap: _cbOpt(n, 'onTap'));
    }
    c.warn('unknown widget type $type');
    return HostErrorBox(message: 'Unknown widget "$type"');
  }

  List<dynamic> _navItems(dynamic v, VCtx c, bool m3) {
    if (v is! List) return const [];
    final out = <dynamic>[];
    for (final it in v) {
      if (it is! Map || isCode(it)) continue;
      final icon = Icon(iconV(it['icon']) ?? Icons.circle_outlined);
      final active = it['activeIcon'] != null ? Icon(iconV(it['activeIcon']) ?? Icons.circle) : null;
      final label = strV(it['label']) ?? '';
      if (m3) {
        out.add(NavigationDestination(icon: icon, selectedIcon: active, label: label));
      } else {
        out.add(BottomNavigationBarItem(icon: icon, activeIcon: active, label: label));
      }
    }
    return m3 ? out.cast<Widget>() : out;
  }
}

/// Gives a TabBar / TabBarView a controller when no DefaultTabController is above it (designing a TabBar alone).
class _TabScope extends StatelessWidget {
  const _TabScope({required this.length, required this.child});
  final int length;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final ctl = DefaultTabController.maybeOf(context);
    if (ctl != null && ctl.length == length) return child;
    if (length == 0) return const SizedBox(height: 48);
    return DefaultTabController(length: length, child: child);
  }
}
