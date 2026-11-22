// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Todo screen - event handlers. This file is yours: the Flutter designer only adds new handler
// stubs. Named widgets are fields (txtTask.text); call setState(() { ... }) after changing values
// shown on the screen.
part of 'todo.dart';

class TodoEvents extends TodoDesigner {
  /// The whole screen follows the language setting: right-to-left for Arabic.
  @override
  Widget build(BuildContext context) => Directionality(
        textDirection: store.arabic ? TextDirection.rtl : TextDirection.ltr,
        child: super.build(context),
      );

  @override
  void onAdd() {
    setState(() => store.add(txtTask.text));
    txtTask.clear();
  }

  @override
  void onSubmitted(String value) => onAdd();

  /// Called by the list item template (a Code widget in the designer): tap = done / not done.
  @override
  void onToggle(int index) {
    setState(() => store.visible()[index].done = !store.visible()[index].done);
  }

  @override
  void onDelete(int index) {
    final task = store.visible()[index];
    setState(() => store.todos.remove(task));
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(store.t('Deleted', 'تم الحذف'))));
  }

  @override
  void onSettings() {
    // back from Settings: rebuild with the new language / filter
    Navigator.pushNamed(context, Settings.route).then((_) => setState(() {}));
  }
}
