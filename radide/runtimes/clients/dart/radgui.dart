// RAD IDE - GUI Bridge client for Dart (copied into the project when it runs).
//
// The IDE draws the forms; this program talks to it over stdin/stdout
// (protocol: docs/CONTRACTS.md section 1). GUI calls are synchronous.
//
//   Rad.set(obj, prop, value)            set a property     Rad.set('lblOut', 'Caption', 'Hi')
//   Rad.get(obj, prop)        -> String  read a property    Rad.get('txtA', 'Text')
//   Rad.getNum(obj, prop)     -> num     read a property as a number
//   Rad.call(obj, method, [args])        call a method      Rad.call('lstLog', 'AddItem', ['line'])
//   Rad.msgbox(text) / msgbox(text)      message box (waits for OK)
//   Rad.input(prompt)         -> String  input box
//   Rad.show(form) / Rad.hide(form)      show or hide a form
//   Rad.end()                            quit the program
//   await radcall('Module.func', [args]) -> value
//        call a function of any project module, in any language, through the RAD Hub
//        (arguments and result are JSON values). radcall is async: use it in an
//        `async` handler (Future<void> cmdGo_Click(RadEvent e) async { ... }).
// Handlers are top-level functions named <Control>_<Event> taking an optional
// RadEvent e (e.x, e.y, e.button, e.keyCode, e.keyChar, e.args).
library radgui;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// Event arguments (mouse/key events; zeros otherwise).
class RadEvent {
  final String object;
  final String event;
  final String args;
  final int x, y, button, keyCode;
  final String keyChar;
  RadEvent(this.object, this.event, this.args, this.x, this.y, this.button, this.keyCode, this.keyChar);

  // VB-style aliases
  int get X => x;
  int get Y => y;
  int get Button => button;
  int get KeyCode => keyCode;
  String get KeyChar => keyChar;

  factory RadEvent.parse(String object, String event, String rest) {
    final p = rest.split(' ');
    int n(int i) => i < p.length ? (int.tryParse(p[i]) ?? double.tryParse(p[i])?.toInt() ?? 0) : 0;
    final keyChar = p.length > 4 ? p.sublist(4).join(' ') : '';
    return RadEvent(object, event, rest, n(0), n(1), n(2), n(3), keyChar);
  }

  @override
  String toString() => 'RadEvent($object.$event $args)';
}

typedef RadHandler = FutureOr<void> Function(RadEvent e);

/// GUI Bridge commands.
class Rad {
  /// true inside a RAD Hub worker: there is no IDE on stdin/stdout.
  static bool worker = false;

  static String _clean(Object? v) => (v ?? '').toString().replaceAll(RegExp(r'\r?\n'), ' ');

  static void _send(String line) {
    if (worker) {
      stderr.writeln(line);
    } else {
      stdout.writeln(line);
    }
  }

  static String _readLine() {
    if (worker) return '';
    final line = stdin.readLineSync(encoding: utf8);
    if (line == null) exit(0); // the IDE went away
    return line.endsWith('\r') ? line.substring(0, line.length - 1) : line;
  }

  // "ESC <command>" (radide/runtimes/bridge.py): \ newline CR escaped in the values (multi-line text)
  static String _esc(String s) => s.replaceAll('\\', '\\\\').replaceAll('\n', '\\n').replaceAll('\r', '\\r');

  static String _unesc(String s) => s.replaceAllMapped(
      RegExp(r'\\([\\nr])'), (m) => m.group(1) == 'n' ? '\n' : (m.group(1) == 'r' ? '\r' : '\\'));

  static void set(String obj, String prop, Object? value) {
    final s = (value ?? '').toString();
    if (s.contains('\n') || s.contains('\r')) {
      _send('ESC SET $obj $prop ${_esc(s)}'); // multi-line text
    } else {
      _send('SET $obj $prop $s');
    }
  }

  static String get(String obj, String prop) {
    _send('ESC GET $obj $prop');
    return _unesc(_readLine());
  }

  static num getNum(String obj, String prop) {
    final m = RegExp(r'^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?').firstMatch(get(obj, prop));
    return m == null ? 0 : num.parse(m.group(0)!.trim());
  }

  static String call(String obj, String method, [List<Object?> args = const []]) {
    var line = 'CALL $obj $method';
    if (args.isNotEmpty) line += ' ' + args.map(_clean).join('\t');
    _send(line);
    return _readLine();
  }

  static String msgbox(Object? text) {
    _send('MSGBOX ${_clean(text)}');
    return _readLine();
  }

  static String input(Object? prompt) {
    _send('INPUT ${_clean(prompt)}');
    return _readLine();
  }

  static void show(String form) => _send('SHOW $form');
  static void hide(String form) => _send('HIDE $form');

  static Never end() {
    _send('END');
    exit(0);
  }
}

/// Message box (same as Rad.msgbox).
String msgbox(Object? text) => Rad.msgbox(text);

// ------------------------------------------------------------------ RAD Hub
Socket? _hub;
StreamIterator<String>? _hubLines;
int _hubId = 0;

/// Call a function of any project module through the RAD Hub:
/// `final r = await radcall('Helpers.add', [2, 3]);`
Future<dynamic> radcall(String name, [List<Object?> args = const []]) async {
  final addr = Platform.environment['RAD_HUB'] ?? '';
  if (addr.isEmpty) throw RadCallError('radcall($name): RAD Hub is not running (RAD_HUB is not set)');
  if (_hub == null) {
    final i = addr.lastIndexOf(':');
    try {
      _hub = await Socket.connect(addr.substring(0, i), int.parse(addr.substring(i + 1)));
    } catch (e) {
      throw RadCallError('radcall($name): cannot connect to RAD Hub at $addr: $e');
    }
    _hubLines = StreamIterator(_hub!.cast<List<int>>().transform(utf8.decoder).transform(const LineSplitter()));
  }
  final id = ++_hubId;
  _hub!.write('${jsonEncode({'id': id, 'call': name, 'args': args})}\n');
  await _hub!.flush();
  while (true) {
    if (!await _hubLines!.moveNext()) {
      _hub = null;
      _hubLines = null;
      throw RadCallError('radcall($name): RAD Hub closed the connection');
    }
    final line = _hubLines!.current.trim();
    if (line.isEmpty) continue;
    final Object? msg;
    try {
      msg = jsonDecode(line);
    } catch (_) {
      continue;
    }
    if (msg is! Map || msg['id'] != id) continue;
    if (msg['error'] != null) throw RadCallError('radcall($name): ${msg['error']}');
    return msg['result'];
  }
}

class RadCallError implements Exception {
  final String message;
  RadCallError(this.message);
  @override
  String toString() => message;
}

// ------------------------------------------------------------------ main loop
/// Read EVENT lines and run the matching handler; always answer DONE.
Future<void> radRun(Map<String, RadHandler> handlers) async {
  stdout.encoding = utf8;
  final lower = {for (final k in handlers.keys) k.toLowerCase(): handlers[k]!};
  while (true) {
    var line = stdin.readLineSync(encoding: utf8);
    if (line == null) break;
    if (line.endsWith('\r')) line = line.substring(0, line.length - 1);
    if (line == 'QUIT') break;
    if (!line.startsWith('EVENT ')) continue;
    final parts = line.substring(6).split(' ');
    if (parts.length < 2) {
      stdout.writeln('DONE');
      continue;
    }
    final obj = parts[0], ev = parts[1];
    final rest = parts.length > 2 ? parts.sublist(2).join(' ') : '';
    final h = handlers['${obj}_$ev'] ?? lower['${obj}_$ev'.toLowerCase()];
    if (h != null) {
      try {
        final r = h(RadEvent.parse(obj, ev, rest));
        if (r is Future) await r;
      } catch (e, st) {
        stderr.writeln('[Dart] error in ${obj}_$ev: $e\n$st');
      }
    }
    stdout.writeln('DONE');
  }
  await _hub?.close();
  exit(0);
}
