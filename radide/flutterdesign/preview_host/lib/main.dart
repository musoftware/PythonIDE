// RAD IDE Flutter designer - preview host.
//
// A Flutter web app that renders a *.fscreen.json widget tree (docs/FLUTTER_DESIGNER.md) with REAL widgets inside
// a device frame, and talks to RAD IDE (radide/flutterdesign/live.py) through web/index.html's window.radHost:
//
//  IDE -> host  {"type": "screen", "screen": {...}, "seq": n}       whole screen
//               {"type": "patch", "ops": [...], "seq": n}           model.py patch (put / set / screen ops)
//               {"type": "select", "id": "w7"|null, "reveal": bool} {"type": "hover", "id": ...}
//               {"type": "device", "width", "height", "textScale", "dark", "frame", "platform", "rtl", "zoom"}
//               {"type": "mode", "mode": "design"|"interact"}        {"type": "play"}  {"type": "stop"}
//               {"type": "config", "assetBase": "/project/", "appTheme": {...}|null}
//               {"type": "ping", "seq": n}                            {"type": "rects"} (force a rect report)
//  host -> IDE  {"type": "ready"} {"type": "rendered", "seq", "ms", "nodes"} {"type": "pong", "seq"}
//               {"type": "rects", "rects": {id: [x, y, w, h]}, "hidden": [...], "device": [x, y, w, h], "scale"}
//               {"type": "click"|"dblclick"|"context", "id", "path": [deepest .. root], "x", "y", "shift", "ctrl"}
//               {"type": "hover", "id"}  {"type": "issues", "issues": [{"id", "level", "message"}]}
//               {"type": "event", "id", "event", "handler", "value"}  {"type": "log", "level", "text"}
// Rects are in page CSS pixels (= QWebEngineView logical pixels at zoom 1).
import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import 'bridge.dart';
import 'factory.dart';
import 'nodebox.dart';
import 'theme.dart';

const hostVersion = 1;

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final host = HostState();
  ErrorWidget.builder = (details) => HostErrorBox(message: details.exceptionAsString());
  FlutterError.onError = host.frameworkError;
  runApp(HostApp(host: host));
  Bridge.init(host.onMessage);
  Bridge.send({'type': 'ready', 'version': hostVersion});
}

// ============================================================================================== state
class HostState extends ChangeNotifier implements FactoryHost {
  Map<String, dynamic>? screen;
  String? selected, hovered;
  double devW = 390, devH = 844, textScale = 1;
  bool dark = false, frame = true, rtl = false;
  String platform = 'android';
  double? zoom;
  String mode = 'design';
  Map? appThemeSpec;
  int _epoch = 0;
  bool _playing = false;
  String _assetBase = '/project/';
  int seq = 0;
  int _sentAt = 0;

  final contentKey = GlobalKey();
  final messengerKey = GlobalKey<ScaffoldMessengerState>();
  final deviceKey = GlobalKey();
  final repaint = ValueNotifier<int>(0);

  final Map<String, TextEditingController> _controllers = {};
  final Map<String, dynamic> _values = {};
  final Map<String, String> _seeds = {};
  final Map<String, GlobalKey<ScaffoldState>> _scaffolds = {};
  final Map<String, Set<String>> _drawerIds = {};
  final Map<String, Set<String>> issues = {}; // id -> "level\tmessage"
  final Set<String> _fonts = {};
  String _lastRects = '';
  String _lastIssues = '';
  Timer? _timer;

  HostState() {
    _timer = Timer.periodic(const Duration(milliseconds: 120), (_) => _tick());
  }

  // ---- FactoryHost
  @override
  bool get interactive => mode == 'interact';
  @override
  bool get playing => _playing;
  @override
  int get epoch => _epoch;
  @override
  String get assetBase => _assetBase;

  @override
  dynamic value(String id, dynamic designValue) {
    if (!interactive) return designValue;
    final seed = jsonEncode(designValue);
    if (_seeds[id] != seed) {
      _seeds[id] = seed;
      _values[id] = designValue;
    }
    return _values[id];
  }

  @override
  void setValue(String id, dynamic v) {
    if (!interactive) return;
    _values[id] = v;
    notifyListeners();
  }

  @override
  TextEditingController controller(String id) => _controllers.putIfAbsent(id, TextEditingController.new);

  @override
  void event(String id, String event, String? handler, [dynamic arg]) {
    if (!interactive) return;
    final v = (arg is num || arg is bool || arg is String || arg == null) ? arg : '$arg';
    Bridge.send({'type': 'event', 'id': id, 'event': event, 'handler': handler, 'value': v});
    if (handler == null || handler.isEmpty) return;
    final text = handler == 'back'
        ? 'Navigator.pop()'
        : handler.contains(':')
            ? '${handler.split(':').first} -> ${handler.substring(handler.indexOf(':') + 1)}'
            : '$handler(${v == null ? '' : v is String ? "'$v'" : v})';
    messengerKey.currentState
      ?..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text), duration: const Duration(milliseconds: 1400)));
  }

  @override
  void nodeIssue(String id, String level, String message) {
    issues.putIfAbsent(id, () => <String>{}).add('$level\t$message');
  }

  @override
  GlobalKey<ScaffoldState> scaffoldKey(String id) => _scaffolds.putIfAbsent(id, GlobalKey<ScaffoldState>.new);

  @override
  void drawerNodes(String scaffoldId, Set<String> ids) => _drawerIds[scaffoldId] = ids;

  // ---- messages
  void onMessage(Map<String, dynamic> m) {
    try {
      _handle(m);
    } catch (e, st) {
      Bridge.send({'type': 'log', 'level': 'error', 'text': '${m['type']}: $e\n$st'});
    }
  }

  void _handle(Map<String, dynamic> m) {
    switch (m['type']) {
      case 'screen':
        final s = m['screen'];
        screen = s is Map ? Map<String, dynamic>.from(s) : null;
        _changed(m['seq']);
        _loadFonts();
      case 'patch':
        final s = screen;
        if (s == null) return;
        for (final op in (m['ops'] as List? ?? const [])) {
          _applyOp(s, op as Map);
        }
        _changed(m['seq']);
        if ((m['ops'] as List? ?? const []).any((o) => o is Map && o['op'] == 'screen' && o['key'] == 'fonts')) {
          _loadFonts();
        }
      case 'select':
        selected = m['id'] as String?;
        repaint.value++;
        WidgetsBinding.instance.addPostFrameCallback((_) => _afterSelect(m['reveal'] == true));
        WidgetsBinding.instance.scheduleFrame();
      case 'hover':
        hovered = m['id'] as String?;
        repaint.value++;
      case 'device':
        devW = _d(m['width'], devW);
        devH = _d(m['height'], devH);
        textScale = _d(m['textScale'], textScale);
        if (m['dark'] is bool) dark = m['dark'] as bool;
        if (m['frame'] is bool) frame = m['frame'] as bool;
        if (m['rtl'] is bool) rtl = m['rtl'] as bool;
        if (m['platform'] is String) platform = m['platform'] as String;
        if (m.containsKey('zoom')) zoom = m['zoom'] is num ? (m['zoom'] as num).toDouble() : null;
        _changed(m['seq']);
      case 'mode':
        mode = m['mode'] == 'interact' ? 'interact' : 'design';
        NodeRegistry.designHit = mode == 'design';
        _values.clear();
        _seeds.clear();
        hovered = null;
        _changed(m['seq']);
      case 'play':
        _epoch++;
        _playing = true;
        _changed(m['seq']);
      case 'stop':
        _epoch++;
        _playing = false;
        _changed(m['seq']);
      case 'config':
        if (m['assetBase'] is String) _assetBase = m['assetBase'] as String;
        if (m.containsKey('appTheme')) appThemeSpec = m['appTheme'] is Map ? m['appTheme'] as Map : null;
        _changed(m['seq']);
        _loadFonts();
      case 'ping':
        Bridge.send({'type': 'pong', 'seq': m['seq']});
      case 'rects':
        _lastRects = '';
        _tick();
    }
  }

  static double _d(dynamic v, double def) => v is num ? v.toDouble() : def;

  void _changed(dynamic s) {
    if (s is int) seq = s;
    _sentAt = DateTime.now().millisecondsSinceEpoch;
    issues.clear();
    final mySeq = seq;
    notifyListeners();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // a second post-frame callback: lazily built children (lists, layout builders) are done by then
      WidgetsBinding.instance.addPostFrameCallback((_) {});
      Bridge.send({
        'type': 'rendered',
        'seq': mySeq,
        'ms': DateTime.now().millisecondsSinceEpoch - _sentAt,
        'nodes': NodeRegistry.nodes.length,
      });
      _lastRects = '';
      _tick();
    });
    WidgetsBinding.instance.scheduleFrame();
  }

  // ---- patches (same semantics as model.apply_patch)
  static Map? _find(Map node, String id) {
    if (node['id'] == id) return node;
    final sl = node['slots'];
    if (sl is Map) {
      for (final v in sl.values) {
        if (v is Map) {
          final r = _find(v, id);
          if (r != null) return r;
        } else if (v is List) {
          for (final c in v) {
            if (c is Map) {
              final r = _find(c, id);
              if (r != null) return r;
            }
          }
        }
      }
    }
    final ch = node['children'];
    if (ch is List) {
      for (final c in ch) {
        if (c is Map) {
          final r = _find(c, id);
          if (r != null) return r;
        }
      }
    }
    return null;
  }

  void _applyOp(Map<String, dynamic> scr, Map op) {
    switch (op['op']) {
      case 'put':
        final pid = op['parent'] as String?;
        final nw = op['new'];
        final where = (op['where'] as Map?) ?? const {};
        if (pid == null) {
          if (nw != null) scr['tree'] = nw;
          return;
        }
        final parent = _find(scr['tree'] as Map, pid);
        if (parent == null) throw StateError('patch: no node $pid');
        final slot = where['slot'] as String?;
        final index = where['index'] as int?;
        if (slot != null && index == null) {
          final slots = (parent['slots'] ??= <String, dynamic>{}) as Map;
          if (nw == null) {
            slots.remove(slot);
          } else {
            slots[slot] = nw;
          }
          return;
        }
        List lst;
        if (slot != null) {
          final slots = (parent['slots'] ??= <String, dynamic>{}) as Map;
          lst = (slots[slot] ??= []) as List;
        } else {
          lst = (parent['children'] ??= []) as List;
        }
        final i = index ?? lst.length;
        if (op['old'] == null) {
          lst.insert(i.clamp(0, lst.length), nw);
        } else if (nw == null) {
          if (i < lst.length) lst.removeAt(i);
        } else {
          lst[i] = nw;
        }
        if (slot != null && lst.isEmpty) (parent['slots'] as Map).remove(slot);
      case 'set':
        final node = _find(scr['tree'] as Map, op['id'] as String);
        if (node == null) throw StateError('patch: no node ${op['id']}');
        final f = op['field'] as String;
        final v = op['new'];
        if (f == 'props' || f == 'events') {
          final d = (node[f] ??= <String, dynamic>{}) as Map;
          if (v == null) {
            d.remove(op['key']);
          } else {
            d[op['key']] = v;
          }
        } else if (v == null) {
          node.remove(f);
        } else {
          node[f] = v;
        }
      case 'screen':
        if (op['new'] == null) {
          scr.remove(op['key']);
        } else {
          scr[op['key'] as String] = op['new'];
        }
    }
  }

  // ---- fonts of the screen (asset fonts are fetched from the project folder)
  Future<void> _loadFonts() async {
    final fonts = screen?['fonts'];
    if (fonts is! List) return;
    for (final f in fonts) {
      if (f is! Map || f['source'] != 'asset' || f['family'] is! String) continue;
      final family = f['family'] as String;
      final files = (f['files'] as List? ?? const []).whereType<Map>().toList();
      final key = '$family|${files.map((e) => e['asset']).join(',')}|$_assetBase';
      if (_fonts.contains(key) || files.isEmpty) continue;
      _fonts.add(key);
      try {
        final loader = FontLoader(family);
        for (final file in files) {
          final url = _assetBase + '${file['asset']}'.replaceFirst(RegExp(r'^/+'), '');
          loader.addFont(http.get(Uri.base.resolve(url)).then((r) {
            if (r.statusCode != 200) throw StateError('HTTP ${r.statusCode} for $url');
            return ByteData.sublistView(r.bodyBytes);
          }));
        }
        await loader.load();
        notifyListeners();
      } catch (e) {
        Bridge.send({'type': 'log', 'level': 'warning', 'text': 'font $family: $e'});
      }
    }
  }

  // ---- selection helpers
  void _afterSelect(bool reveal) {
    final id = selected;
    for (final e in _drawerIds.entries) {
      final st = _scaffolds[e.key]?.currentState;
      if (st == null) continue;
      if (id != null && e.value.contains(id)) {
        if (!st.isDrawerOpen && !st.isEndDrawerOpen) {
          final scr = _find(screen?['tree'] as Map? ?? const {}, e.key);
          final end = scr != null && _inSlot(scr, 'endDrawer', id);
          end ? st.openEndDrawer() : st.openDrawer();
        }
      } else if (st.isDrawerOpen || st.isEndDrawerOpen) {
        st.closeDrawer();
        st.closeEndDrawer();
      }
    }
    if (reveal && id != null) _reveal(id);
  }

  /// Scrolls the node into view - also when it is not built yet (lazy ListView / GridView children): the
  /// nearest built ancestor's scroll view is moved page by page until the node exists.
  Future<void> _reveal(String id) async {
    final path = _pathTo(screen?['tree'], id);
    var wrapped = false;
    for (var tries = 0; tries < 80 && selected == id; tries++) {
      final n = NodeRegistry.nodes[id];
      if (n != null) {
        try {
          if (n.hasSize && n.size.isFinite) n.showOnScreen(duration: const Duration(milliseconds: 150));
        } catch (_) {}
        return;
      }
      RenderNode? anc;
      for (final pid in path.reversed) {
        anc = NodeRegistry.nodes[pid];
        if (anc != null) break;
      }
      if (anc == null) return;
      final vp = _viewportIn(anc);
      final pos = vp?.offset;
      if (pos is! ScrollPosition || !pos.hasContentDimensions) {
        Bridge.send({'type': 'log', 'level': 'info', 'text': 'reveal $id: no scroll view under ${anc.id} ($pos)'});
        return;
      }
      if (pos.pixels >= pos.maxScrollExtent - 0.5) {
        if (wrapped) return;
        wrapped = true;
        pos.jumpTo(pos.minScrollExtent);
      } else {
        pos.jumpTo(math.min(pos.pixels + pos.viewportDimension * 0.8, pos.maxScrollExtent));
      }
      await WidgetsBinding.instance.endOfFrame;
    }
  }

  static List<String> _pathTo(dynamic node, String id) {
    if (node is! Map) return const [];
    if (node['id'] == id) return [id];
    final kids = <dynamic>[];
    final sl = node['slots'];
    if (sl is Map) {
      for (final v in sl.values) {
        v is List ? kids.addAll(v) : kids.add(v);
      }
    }
    final ch = node['children'];
    if (ch is List) kids.addAll(ch);
    for (final k in kids) {
      final r = _pathTo(k, id);
      if (r.isNotEmpty) return ['${node['id']}', ...r];
    }
    return const [];
  }

  static RenderViewportBase? _viewportIn(RenderObject o) {
    RenderViewportBase? found;
    void visit(RenderObject c) {
      if (found != null) return;
      if (c is RenderViewportBase) {
        found = c;
        return;
      }
      c.visitChildren(visit);
    }
    visit(o);
    return found;
  }

  static bool _inSlot(Map scaffold, String slot, String id) {
    final s = (scaffold['slots'] as Map?)?[slot];
    return s is Map && _find(s, id) != null;
  }

  // ---- hit testing (design mode)
  List<String> hitPath(Offset global) {
    final box = contentKey.currentContext?.findRenderObject();
    if (box is! RenderBox || !box.hasSize) return const [];
    final r = BoxHitTestResult();
    box.hitTest(r, position: box.globalToLocal(global));
    return [
      for (final e in r.path)
        if (e.target is RenderNode) (e.target as RenderNode).id
    ];
  }

  void forwardSignal(PointerSignalEvent ev) {
    final box = contentKey.currentContext?.findRenderObject();
    if (box is! RenderBox) return;
    final r = BoxHitTestResult();
    box.hitTest(r, position: box.globalToLocal(ev.position));
    for (final e in r.path) {
      try {
        e.target.handleEvent(ev.transformed(e.transform), e);
      } catch (_) {}
    }
  }

  // ---- reports
  void _tick() {
    final rects = <String, List<double>>{};
    final hidden = <String>[];
    double r1(double v) => (v * 10).roundToDouble() / 10;
    for (final e in NodeRegistry.nodes.entries) {
      final ro = e.value;
      if (ro.attached && ro.hasSize && (ro.unbounded || !ro.size.isFinite)) {
        // what a debug build reports as "unbounded constraints": release builds lay it out silently
        issues.putIfAbsent(e.key, () => <String>{}).add(
            'error	${ro.type} has an infinite size (it is inside a scroll view / Row / Column that does not bound '
            'it): give it a width / height or wrap it in SizedBox / Expanded');
        if (!ro.size.isFinite) continue;
      }
      final r = ro.globalRect();
      if (r == null || !r.isFinite) continue;
      if (!e.value.visible) {
        hidden.add(e.key);
        continue;
      }
      rects[e.key] = [r1(r.left), r1(r.top), r1(r.width), r1(r.height)];
    }
    // render errors (ErrorWidget) -> nearest node
    for (final err in RenderHostError.live) {
      final id = err.nodeId;
      if (id != null) issues.putIfAbsent(id, () => <String>{}).add('error\t${err.message}');
    }
    final dev = deviceKey.currentContext?.findRenderObject();
    List<double>? devRect;
    double scale = 1;
    if (dev is RenderBox && dev.hasSize) {
      final m = dev.getTransformTo(null);
      final r = MatrixUtils.transformRect(m, Offset.zero & dev.size);
      devRect = [r1(r.left), r1(r.top), r1(r.width), r1(r.height)];
      scale = dev.size.width == 0 ? 1 : r.width / dev.size.width;
    }
    final text = jsonEncode({'rects': rects, 'hidden': hidden, 'device': devRect, 'scale': scale});
    if (text != _lastRects) {
      _lastRects = text;
      Bridge.send({'type': 'rects', 'seq': seq, 'rects': rects, 'hidden': hidden, 'device': devRect, 'scale': scale});
      repaint.value++;
    }
    final iss = [
      for (final e in issues.entries)
        for (final s in e.value) {'id': e.key, 'level': s.split('\t').first, 'message': s.split('\t').last}
    ];
    final it = jsonEncode(iss);
    if (it != _lastIssues) {
      _lastIssues = it;
      Bridge.send({'type': 'issues', 'seq': seq, 'issues': iss});
    }
  }

  void frameworkError(FlutterErrorDetails d) {
    final text = d.exceptionAsString();
    final m = RegExp(r"rad:(w\d+)").firstMatch('${d.context ?? ''} ${d.informationCollector?.call().join(' ') ?? ''}');
    if (m != null) nodeIssue(m.group(1)!, 'error', text);
    Bridge.send({'type': 'log', 'level': 'error', 'text': text});
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

// ================================================================================================ app
class HostApp extends StatelessWidget {
  const HostApp({super.key, required this.host});
  final HostState host;

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.ltr,
      child: ColoredBox(
        color: const Color(0xFF2B2D31),
        child: Stack(children: [
          Positioned.fill(
            child: ListenableBuilder(
              listenable: host,
              builder: (context, _) => LayoutBuilder(builder: (context, cons) => _device(context, cons)),
            ),
          ),
          Positioned.fill(
            child: IgnorePointer(child: CustomPaint(painter: _OverlayPainter(host))),
          ),
        ]),
      ),
    );
  }

  Widget _device(BuildContext context, BoxConstraints cons) {
    final ios = host.platform == 'ios';
    final bezel = host.frame ? 12.0 : 0.0;
    final fw = host.devW + 2 * bezel, fh = host.devH + 2 * bezel;
    var scale = host.zoom ?? math.min(1.0, math.min((cons.maxWidth - 24) / fw, (cons.maxHeight - 24) / fh));
    if (!scale.isFinite || scale <= 0.05) scale = 0.05;
    final landscape = host.devW > host.devH;
    final statusH = host.frame ? (landscape ? 0.0 : (ios ? 47.0 : 24.0)) : 0.0;
    final homeH = host.frame && ios ? (landscape ? 21.0 : 34.0) : 0.0;
    final brightness = host.dark ? Brightness.dark : Brightness.light;
    final view = View.of(context);
    final mq = MediaQueryData(
      size: Size(host.devW, host.devH),
      devicePixelRatio: view.devicePixelRatio,
      textScaler: TextScaler.linear(host.textScale),
      platformBrightness: brightness,
      padding: EdgeInsets.only(top: statusH, bottom: homeH),
      viewPadding: EdgeInsets.only(top: statusH, bottom: homeH),
    );
    final spec = host.appThemeSpec;
    final mode = '${spec?['mode'] ?? 'system'}';
    final effDark = mode == 'dark' || (mode != 'light' && host.dark);
    final app = MaterialApp(
      key: const ValueKey('device-app'),
      debugShowCheckedModeBanner: false,
      scaffoldMessengerKey: host.messengerKey,
      theme: appTheme(spec, effDark ? Brightness.dark : Brightness.light),
      themeMode: ThemeMode.light,
      builder: (context, child) => Directionality(
        textDirection: host.rtl ? TextDirection.rtl : TextDirection.ltr,
        child: Theme(
          data: Theme.of(context).copyWith(platform: ios ? TargetPlatform.iOS : TargetPlatform.android),
          child: child!,
        ),
      ),
      home: _ScreenRoot(host: host),
    );
    Widget screen = SizedBox(
      width: host.devW,
      height: host.devH,
      child: MediaQuery(
        data: mq,
        child: Stack(children: [
          Positioned.fill(child: RepaintBoundary(key: host.contentKey, child: app)),
          if (statusH > 0) Positioned(left: 0, right: 0, top: 0, height: statusH, child: _StatusBar(host: host, ios: ios)),
          if (homeH > 0)
            Positioned(
              left: 0, right: 0, bottom: 0, height: homeH,
              child: IgnorePointer(
                child: Center(
                  child: Container(width: 134, height: 5, decoration: BoxDecoration(
                      color: host.dark ? Colors.white70 : Colors.black87, borderRadius: BorderRadius.circular(3))),
                ),
              ),
            ),
          if (!host.interactive) Positioned.fill(child: _DesignInput(host: host)),
        ]),
      ),
    );
    final device = Container(
      key: host.deviceKey,
      width: fw,
      height: fh,
      padding: EdgeInsets.all(bezel),
      decoration: host.frame
          ? BoxDecoration(
              color: const Color(0xFF111111),
              borderRadius: BorderRadius.circular(ios ? 54 : 34),
              boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 24, offset: Offset(0, 8))],
            )
          : const BoxDecoration(color: Color(0xFFFFFFFF)),
      child: ClipRRect(borderRadius: BorderRadius.circular(host.frame ? (ios ? 44 : 24) : 0), child: screen),
    );
    return Center(
      child: SizedBox(
        width: fw * scale,
        height: fh * scale,
        child: FittedBox(fit: BoxFit.fill, child: device),
      ),
    );
  }
}

class _ScreenRoot extends StatelessWidget {
  const _ScreenRoot({required this.host});
  final HostState host;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: host,
      builder: (context, _) {
        final scr = host.screen;
        final tree = scr?['tree'];
        if (tree is! Map) {
          return const Material(child: Center(child: Text('Waiting for a screen...')));
        }
        final theme = screenTheme(scr?['theme'] as Map?, Theme.of(context));
        return Theme(
          data: theme,
          child: Builder(builder: (context) {
            final f = WidgetFactory(host);
            final root = f.node(context, tree);
            final t = tree['type'];
            if (t == 'Scaffold' || t == 'CupertinoPageScaffold') return root;
            return Material(color: Theme.of(context).scaffoldBackgroundColor, child: root);
          }),
        );
      },
    );
  }
}

class _StatusBar extends StatelessWidget {
  const _StatusBar({required this.host, required this.ios});
  final HostState host;
  final bool ios;

  @override
  Widget build(BuildContext context) {
    final c = host.dark ? Colors.white : Colors.black;
    final style = TextStyle(color: c, fontSize: ios ? 15 : 13, fontWeight: FontWeight.w600,
        decoration: TextDecoration.none, fontFamily: 'Roboto');
    return IgnorePointer(
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: ios ? 28 : 14),
        child: Row(crossAxisAlignment: ios ? CrossAxisAlignment.end : CrossAxisAlignment.center, children: [
          Padding(padding: EdgeInsets.only(bottom: ios ? 10 : 0), child: Text(ios ? '9:41' : '12:30', style: style)),
          const Spacer(),
          Padding(
            padding: EdgeInsets.only(bottom: ios ? 12 : 0),
            child: Row(mainAxisSize: MainAxisSize.min, spacing: 3, children: [
              Icon(Icons.signal_cellular_alt, size: 15, color: c),
              Icon(Icons.wifi, size: 15, color: c),
              Icon(ios ? Icons.battery_full : Icons.battery_full, size: 15, color: c),
            ]),
          ),
        ]),
      ),
    );
  }
}

/// Design mode: an invisible layer over the device screen that turns clicks / hovers into node ids.
class _DesignInput extends StatefulWidget {
  const _DesignInput({required this.host});
  final HostState host;

  @override
  State<_DesignInput> createState() => _DesignInputState();
}

class _DesignInputState extends State<_DesignInput> {
  int _lastDown = 0;
  Offset _lastPos = Offset.zero;
  String? _hover;

  Map<String, dynamic> _msg(String type, PointerEvent e, List<String> path) => {
        'type': type,
        'id': path.isEmpty ? null : path.first,
        'path': path,
        'x': e.position.dx,
        'y': e.position.dy,
        'shift': HardwareKeyboard.instance.isShiftPressed,
        'ctrl': HardwareKeyboard.instance.isControlPressed,
      };

  @override
  Widget build(BuildContext context) {
    final host = widget.host;
    return MouseRegion(
      cursor: SystemMouseCursors.basic,
      onExit: (_) {
        if (_hover != null) {
          _hover = null;
          host.hovered = null;
          host.repaint.value++;
          Bridge.send({'type': 'hover', 'id': null});
        }
      },
      child: Listener(
        behavior: HitTestBehavior.opaque,
        onPointerDown: (e) {
          final path = host.hitPath(e.position);
          if (e.buttons & kSecondaryButton != 0) {
            Bridge.send(_msg('context', e, path));
            return;
          }
          final now = DateTime.now().millisecondsSinceEpoch;
          final dbl = now - _lastDown < 400 && (e.position - _lastPos).distance < 6;
          _lastDown = dbl ? 0 : now;
          _lastPos = e.position;
          host.selected = path.isEmpty ? null : path.first;
          host.repaint.value++;
          Bridge.send(_msg(dbl ? 'dblclick' : 'click', e, path));
        },
        onPointerHover: (e) {
          final path = host.hitPath(e.position);
          final id = path.isEmpty ? null : path.first;
          if (id != _hover) {
            _hover = id;
            host.hovered = id;
            host.repaint.value++;
            Bridge.send({'type': 'hover', 'id': id});
          }
        },
        onPointerSignal: (e) {
          GestureBinding.instance.pointerSignalResolver.register(e, (ev) {});
          host.forwardSignal(e);
        },
        child: const SizedBox.expand(),
      ),
    );
  }
}

/// Selection / hover / issue outlines over the device (page coordinates).
class _OverlayPainter extends CustomPainter {
  _OverlayPainter(this.host) : super(repaint: Listenable.merge([host.repaint, host]));
  final HostState host;

  @override
  void paint(Canvas canvas, Size size) {
    if (host.interactive) return;
    for (final id in host.issues.keys) {
      final r = NodeRegistry.rectOf(id);
      if (r == null || !host.issues[id]!.any((s) => s.startsWith('error'))) continue;
      canvas.drawRect(r.deflate(0.5), Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = const Color(0xFFE53935));
    }
    final h = host.hovered;
    if (h != null && h != host.selected) {
      final r = NodeRegistry.rectOf(h);
      if (r != null) {
        canvas.drawRect(r, Paint()..color = const Color(0x1A42A5F5));
        canvas.drawRect(r.deflate(0.5), Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = const Color(0xFF64B5F6));
      }
    }
    final s = host.selected;
    if (s != null) {
      final node = NodeRegistry.nodes[s];
      final r = node?.globalRect();
      if (r != null) {
        canvas.drawRect(r.deflate(1), Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = const Color(0xFF1E88E5));
        final tp = TextPainter(
          text: TextSpan(text: ' ${node!.type} ', style: const TextStyle(fontSize: 11, color: Colors.white)),
          textDirection: TextDirection.ltr,
        )..layout();
        var top = r.top - tp.height - 2;
        if (top < 0) top = r.top + 2;
        final lr = Rect.fromLTWH(r.left, top, tp.width, tp.height + 2);
        canvas.drawRRect(RRect.fromRectAndRadius(lr, const Radius.circular(3)), Paint()..color = const Color(0xFF1E88E5));
        tp.paint(canvas, Offset(r.left, top + 1));
        for (final c in [r.topLeft, r.topRight, r.bottomLeft, r.bottomRight]) {
          canvas.drawRect(Rect.fromCenter(center: c, width: 6, height: 6), Paint()..color = Colors.white);
          canvas.drawRect(Rect.fromCenter(center: c, width: 6, height: 6), Paint()
            ..style = PaintingStyle.stroke
            ..color = const Color(0xFF1E88E5));
        }
      }
    }
  }

  @override
  bool shouldRepaint(covariant _OverlayPainter old) => true;
}
