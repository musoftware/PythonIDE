// Message bridge to RAD IDE (see web/index.html: window.radHost).
import 'dart:convert';
import 'dart:js_interop';

@JS('radHost')
external _RadHost? get _radHost;

extension type _RadHost._(JSObject _) implements JSObject {
  external set onMessage(JSFunction? f);
  external void flush();
  external void send(JSString msg);
}

class Bridge {
  static void Function(Map<String, dynamic> msg)? _handler;

  /// Starts receiving messages (queued ones are delivered right away).
  static void init(void Function(Map<String, dynamic> msg) handler) {
    _handler = handler;
    final h = _radHost;
    if (h == null) return;
    h.onMessage = ((JSString s) {
      try {
        final v = jsonDecode(s.toDart);
        if (v is Map<String, dynamic>) _handler?.call(v);
      } catch (e) {
        send({'type': 'log', 'level': 'error', 'text': 'bad message: $e'});
      }
    }).toJS;
    h.flush();
  }

  static void send(Map<String, dynamic> msg) {
    final h = _radHost;
    final text = jsonEncode(msg);
    if (h == null) {
      // ignore: avoid_print
      print('RADHOST:$text');
      return;
    }
    h.send(text.toJS);
  }
}
