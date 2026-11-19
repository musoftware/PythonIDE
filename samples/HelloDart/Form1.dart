// Hello Dart - event handlers for Form1 (GUI Bridge).
// Rad.set / Rad.get / Rad.call work with the controls drawn by the IDE;
// await radcall('Module.func', [args]) calls functions of any project module (any language).
import 'radgui.dart';

int clicks = 0;

void Form1_Load(RadEvent e) {
  Rad.set('lblOut', 'Caption', 'Type a name and press Greet.');
}

Future<void> cmdGreet_Click(RadEvent e) async {
  final name = Rad.get('txtName', 'Text').trim();
  if (name.isEmpty) {
    Rad.msgbox('Please type a name first.');
    return;
  }
  clicks++;
  // Greeter.dart runs in its own worker process, reached through the RAD Hub
  final text = await radcall('Greeter.greet', [name, clicks]);
  Rad.set('lblOut', 'Caption', text);
  Rad.call('lstLog', 'AddItem', ['$clicks: $text']);
}

void cmdClear_Click(RadEvent e) {
  Rad.call('lstLog', 'Clear');
  clicks = 0;
  Rad.set('lblOut', 'Caption', 'Cleared.');
}
