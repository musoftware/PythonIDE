// RAD IDE runtime for Flutter apps (copied into lib/ by the IDE - do not edit, it is replaced).
// Controls are objects with VB-like properties; setting a property redraws the screen:
//   lblOut.text = 'Hello ${txtName.text}';   chkAgree.checked   sldVolume.value   lstItems.addItem('x')
// Screens (forms):  ShowForm('Details', args)   CloseForm()   FormArgs
// Dialogs:          MsgBox('text')   await InputBox('Your name?')   Toast('Saved')
// ignore_for_file: non_constant_identifier_names
import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
export 'radfx.dart' show RadKey;      // RAD IDE animations / layout sizes
export 'radmotion.dart';      // RAD IDE animations / layout sizes

/// Values shared by every screen of the app (like VB module-level variables).
class RadApp {
  static final Map<String, Object?> data = {};
}

/// What happened: e.Index (list row / tab / drawer item), e.Action (AppBar action), e.Text, e.Value.
class RadEvent {
  const RadEvent({this.Index = -1, this.Action = '', this.Text = '', this.Value});
  final int Index;
  final String Action;
  final String Text;
  final Object? Value;

  int get index => Index;
  String get action => Action;
  String get text => Text;
  Object? get value => Value;

  @override
  String toString() => 'RadEvent(Index: $Index, Action: $Action, Text: $Text, Value: $Value)';
}

class RadControl extends ChangeNotifier {
  RadControl(this.name, {String text = '', bool visible = true, bool enabled = true, this.backColor,
      this.foreColor, this.fontSize})
      : _text = text,
        _visible = visible,
        _enabled = enabled;

  final String name;
  String _text;
  bool _visible;
  bool _enabled;
  Color? backColor;
  Color? foreColor;
  double? fontSize;
  Object? tag;

  String get text => _text;
  set text(String v) {
    _text = v;
    notifyListeners();
  }

  bool get visible => _visible;
  set visible(bool v) {
    _visible = v;
    notifyListeners();
  }

  bool get enabled => _enabled;
  set enabled(bool v) {
    _enabled = v;
    notifyListeners();
  }

  /// Redraw after changing backColor / foreColor / fontSize.
  void refresh() => notifyListeners();

  void setColors({Color? back, Color? fore}) {
    backColor = back ?? backColor;
    foreColor = fore ?? foreColor;
    notifyListeners();
  }
}

class RadTextControl extends RadControl {
  RadTextControl(super.name, {super.text, super.visible, super.enabled, super.backColor, super.foreColor,
      super.fontSize}) {
    controller.text = super.text;
  }

  final TextEditingController controller = TextEditingController();

  @override
  String get text => controller.text;
  @override
  set text(String v) {
    controller.text = v;
    notifyListeners();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }
}

class RadCheckControl extends RadControl {
  RadCheckControl(super.name, {super.text, super.visible, super.enabled, super.backColor, super.foreColor,
      super.fontSize, bool checked = false})
      : _checked = checked;
  bool _checked;
  bool get checked => _checked;
  set checked(bool v) {
    _checked = v;
    notifyListeners();
  }
}

class RadValueControl extends RadControl {
  RadValueControl(super.name, {super.text, super.visible, super.enabled, super.backColor, super.foreColor,
      super.fontSize, num minimum = 0, num maximum = 100, num value = 0})
      : minimum = minimum.toDouble(),
        maximum = maximum.toDouble(),
        _value = value.toDouble();
  double minimum;
  double maximum;
  double _value;
  double get value => _value;
  set value(num v) {
    _value = v.toDouble();
    notifyListeners();
  }
}

class RadListControl extends RadControl {
  RadListControl(super.name, {super.text, super.visible, super.enabled, super.backColor, super.foreColor,
      super.fontSize, List<String>? items, int selectedIndex = -1})
      : items = items ?? <String>[],
        _selectedIndex = selectedIndex;
  final List<String> items;
  int _selectedIndex;

  int get selectedIndex => _selectedIndex;
  set selectedIndex(int v) {
    _selectedIndex = v;
    notifyListeners();
  }

  /// The selected item ('' when nothing is selected).
  String get selectedItem =>
      _selectedIndex >= 0 && _selectedIndex < items.length ? items[_selectedIndex] : '';
  int get count => items.length;

  void addItem(String item) {
    items.add(item);
    notifyListeners();
  }

  void insertItem(int index, String item) {
    items.insert(index, item);
    notifyListeners();
  }

  void removeAt(int index) {
    if (index >= 0 && index < items.length) {
      items.removeAt(index);
      if (_selectedIndex >= items.length) _selectedIndex = items.length - 1;
      notifyListeners();
    }
  }

  void clear() {
    items.clear();
    _selectedIndex = -1;
    notifyListeners();
  }

  void setItems(Iterable<String> values) {
    items
      ..clear()
      ..addAll(values);
    notifyListeners();
  }

  /// Field [index] of item [i] when items are written as "title|subtitle|...".
  String field(int i, int index) {
    final parts = items[i].split('|');
    return index < parts.length ? parts[index].trim() : '';
  }
}

class RadImageControl extends RadControl {
  RadImageControl(super.name, {super.text, super.visible, super.enabled, super.backColor, super.foreColor,
      super.fontSize, String image = ''})
      : _image = image;
  String _image;
  String get image => _image;
  set image(String v) {
    _image = v;
    notifyListeners();
  }
}

class RadWebControl extends RadControl {
  RadWebControl(super.name, {super.text, super.visible, super.enabled, super.backColor, super.foreColor,
      super.fontSize, String url = ''})
      : _url = url;
  String _url;
  String get url => _url;
  set url(String v) {
    _url = v;
    notifyListeners();
  }
}

/// VB Timer: Interval in milliseconds, Enabled starts / stops it, onTick runs the Tick handler.
class RadTimer {
  RadTimer({this.interval = 100, bool enabled = false, this.onTick}) : _enabled = enabled;
  int interval;
  bool _enabled;
  void Function()? onTick;
  Timer? _timer;

  bool get enabled => _enabled;
  set enabled(bool v) {
    _enabled = v;
    v ? start() : stop();
  }

  void attach() {
    if (_enabled) start();
  }

  void start() {
    _timer?.cancel();
    _enabled = true;
    _timer = Timer.periodic(Duration(milliseconds: interval < 1 ? 1 : interval), (_) => onTick?.call());
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
    _enabled = false;
  }
}

/// Screen helpers mixed into every generated form.
mixin RadForm<T extends StatefulWidget> on State<T> {
  List<RadControl> get radControls;

  @override
  void initState() {
    super.initState();
    for (final c in radControls) {
      c.addListener(_radChanged);
    }
  }

  void _radChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    for (final c in radControls) {
      c.removeListener(_radChanged);
      c.dispose();
    }
    super.dispose();
  }

  /// Open another screen (form) by name: ShowForm('Details') or ShowForm('Details', someValue).
  Future<Object?> ShowForm(String name, [Object? args]) =>
      Navigator.of(context).pushNamed(name.startsWith('/') ? name : '/$name', arguments: args);

  /// Replace the current screen with another one.
  Future<Object?> SwitchForm(String name, [Object? args]) =>
      Navigator.of(context).pushReplacementNamed(name.startsWith('/') ? name : '/$name', arguments: args);

  /// Close this screen and go back (optionally returning a result to ShowForm).
  void CloseForm([Object? result]) => Navigator.of(context).maybePop(result);

  /// The value passed to ShowForm(name, args).
  Object? get FormArgs => ModalRoute.of(context)?.settings.arguments;

  Future<void> MsgBox(String text, [String title = '']) => showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: title.isEmpty ? null : Text(title),
          content: Text(text),
          actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('OK'))],
        ),
      );

  /// Ask a Yes / No question: true = Yes.
  Future<bool> Confirm(String text, [String title = '']) async {
    final r = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: title.isEmpty ? null : Text(title),
        content: Text(text),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Yes')),
        ],
      ),
    );
    return r ?? false;
  }

  /// Ask for a text: null when cancelled.
  Future<String?> InputBox(String prompt, [String title = '', String value = '']) {
    final ctl = TextEditingController(text: value);
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: title.isEmpty ? null : Text(title),
        content: TextField(controller: ctl, autofocus: true, decoration: InputDecoration(labelText: prompt)),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(context).pop(ctl.text), child: const Text('OK')),
        ],
      ),
    );
  }

  /// A short message at the bottom of the screen (Android toast / snackbar).
  void Toast(String text) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));
  }
}

/// Material icon by name ('home', 'Search', 'shopping cart'); items may be written "Label:icon".
class RadIcons {
  static const Map<String, IconData> _icons = {
    'home': Icons.home, 'search': Icons.search, 'person': Icons.person, 'profile': Icons.person,
    'account': Icons.account_circle, 'settings': Icons.settings, 'star': Icons.star, 'favorite': Icons.favorite,
    'favorites': Icons.favorite, 'info': Icons.info, 'about': Icons.info, 'help': Icons.help, 'menu': Icons.menu,
    'close': Icons.close, 'check': Icons.check, 'delete': Icons.delete, 'edit': Icons.edit, 'save': Icons.save,
    'share': Icons.share, 'add': Icons.add, 'list': Icons.list, 'map': Icons.map, 'refresh': Icons.refresh,
    'notifications': Icons.notifications, 'cart': Icons.shopping_cart, 'shopping_cart': Icons.shopping_cart,
    'store': Icons.store, 'shop': Icons.store, 'message': Icons.message, 'messages': Icons.message,
    'chat': Icons.chat, 'photo': Icons.photo, 'photos': Icons.photo, 'camera': Icons.camera_alt,
    'music': Icons.music_note, 'video': Icons.videocam, 'news': Icons.article, 'calendar': Icons.calendar_today,
    'logout': Icons.logout, 'login': Icons.login, 'contacts': Icons.contacts, 'phone': Icons.phone,
    'email': Icons.email, 'mail': Icons.email, 'lock': Icons.lock, 'dashboard': Icons.dashboard,
    'explore': Icons.explore, 'tasks': Icons.task_alt, 'web': Icons.public, 'cloud': Icons.cloud,
    'folder': Icons.folder, 'event': Icons.event, 'send': Icons.send, 'more_vert': Icons.more_vert,
    'more': Icons.more_horiz, 'play': Icons.play_arrow, 'pause': Icons.pause, 'stop': Icons.stop,
    'back': Icons.arrow_back, 'next': Icons.arrow_forward, 'image': Icons.image, 'library': Icons.library_books,
  };

  static String _key(String item) {
    final i = item.lastIndexOf(':');
    final s = (i >= 0 ? item.substring(i + 1) : item).trim().toLowerCase();
    return s.replaceAll(RegExp(r'[^a-z0-9]+'), '_').replaceAll(RegExp(r'^_+|_+$'), '');
  }

  static bool has(String item) => _icons.containsKey(_key(item));
  static IconData byName(String item) => _icons[_key(item)] ?? Icons.circle_outlined;

  /// "Home:home" -> "Home".
  static String label(String item) {
    final i = item.lastIndexOf(':');
    return (i > 0 ? item.substring(0, i) : item).trim();
  }
}

/// Image from assets/, a URL or nothing (a placeholder).
class RadImage extends StatelessWidget {
  const RadImage(this.source, {super.key, this.fit = BoxFit.contain});
  final String source;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) {
    final placeholder = Container(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      alignment: Alignment.center,
      child: const Icon(Icons.image_outlined, size: 40),
    );
    if (source.isEmpty) return placeholder;
    if (source.startsWith('http://') || source.startsWith('https://')) {
      return Image.network(source, fit: fit, errorBuilder: (_, __, ___) => placeholder);
    }
    return Image.asset(source, fit: fit, errorBuilder: (_, __, ___) => placeholder);
  }
}

/// Web page placeholder for platforms without an embedded browser (Windows / web builds).
class RadWebView extends StatelessWidget {
  const RadWebView({super.key, required this.url});
  final String url;

  @override
  Widget build(BuildContext context) {
    final factory = radWebViewFactory;
    if (factory != null && !kIsWeb &&
        (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS)) {
      return factory(url);
    }
    return Container(
      decoration: BoxDecoration(border: Border.all(color: Colors.black26)),
      alignment: Alignment.center,
      padding: const EdgeInsets.all(8),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.public, size: 36),
        SelectableText(url, textAlign: TextAlign.center),
        const Text('(web pages show on Android / iOS)', style: TextStyle(fontSize: 11)),
      ]),
    );
  }
}

/// Set by lib/radwebview.dart when the project uses webview_flutter.
Widget Function(String url)? radWebViewFactory;
