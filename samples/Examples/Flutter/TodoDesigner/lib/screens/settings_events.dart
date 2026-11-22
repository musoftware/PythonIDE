// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Settings screen - event handlers: the language (Arabic, right to left) and the "hide finished" filter.
part of 'settings.dart';

class SettingsEvents extends SettingsDesigner {
  @override
  void initState() {
    super.initState();
    swtArabic = store.arabic;
    swtHideDone = store.hideDone;
  }

  @override
  Widget build(BuildContext context) => Directionality(
        textDirection: store.arabic ? TextDirection.rtl : TextDirection.ltr,
        child: super.build(context),
      );

  @override
  void onArabicChanged(bool value) {
    setState(() => store.arabic = swtArabic = value);
  }

  @override
  void onHideDoneChanged(bool value) {
    setState(() => store.hideDone = swtHideDone = value);
  }

  @override
  void onClearAll() {
    setState(() => store.todos.clear());
  }
}
