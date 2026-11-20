// RAD IDE - RAD Hub worker for Dart modules.
//
// The IDE generates `_radworker_<Module>.dart`, which imports the module and calls
// radServe('<Module>', {'add': m.add, ...}). The worker serves the functions over
// stdin/stdout (JSON lines):
//   stdin : {"id": 7, "func": "add", "args": [2, 3]}
//   stdout: {"id": 7, "result": 5}   or   {"id": 7, "error": "message"}
// print() output goes to stderr so stdout stays clean. Functions may be async.
library radworker;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'radgui.dart';

Future<void> radServe(String module, Map<String, Function> funcs) async {
  Rad.worker = true;
  stdout.encoding = utf8;
  final lower = {for (final k in funcs.keys) k.toLowerCase(): funcs[k]!};
  void reply(Map<String, Object?> msg) {
    String text;
    try {
      text = jsonEncode(msg);
    } catch (e) {
      text = jsonEncode({'id': msg['id'], 'error': 'result is not JSON: $e'});
    }
    stdout.writeln(text);
  }

  await runZoned(() async {
    final lines = stdin.transform(utf8.decoder).transform(const LineSplitter());
    await for (final raw in lines) {
      final line = raw.trim();
      if (line.isEmpty) continue;
      Object? id;
      try {
        final req = jsonDecode(line);
        if (req is! Map) throw const FormatException('request is not an object');
        id = req['id'];
        final name = '${req['func'] ?? ''}';
        final fn = funcs[name] ?? lower[name.toLowerCase()];
        if (fn == null) {
          reply({'id': id, 'error': "$module has no function '$name'"});
          continue;
        }
        final args = req['args'] is List ? List<Object?>.from(req['args'] as List) : <Object?>[];
        var result = Function.apply(fn, args);
        if (result is Future) result = await result;
        reply({'id': id, 'result': result});
      } catch (e) {
        reply({'id': id, 'error': '$e'});
      }
    }
  }, zoneSpecification: ZoneSpecification(print: (self, parent, zone, line) => stderr.writeln(line)));
  exit(0);
}
