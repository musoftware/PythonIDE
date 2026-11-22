// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// The app's data, shared by the designed screens (Todo, Settings): the task list and the settings.
// The designer screens read it in their Dart values ({"$code": "store.summary()"}) - see Screen
// properties > Imports (../app_store.dart).

class Task {
  Task(this.title, {this.done = false});

  final String title;
  bool done;
}

class AppStore {
  final List<Task> todos = [
    Task('Design the screen in RAD IDE'),
    Task('Write the event handlers'),
    Task('Run with F5', done: true),
  ];

  /// Arabic labels and a right-to-left layout (Settings screen).
  bool arabic = false;

  /// Hide the finished tasks in the list (Settings screen).
  bool hideDone = false;

  /// [en] or [ar], depending on the language setting.
  String t(String en, String ar) => arabic ? ar : en;

  List<Task> visible() => hideDone ? todos.where((x) => !x.done).toList() : todos;

  String summary() {
    final open = todos.where((x) => !x.done).length;
    return t('$open open of ${todos.length} tasks', '$open مفتوحة من ${todos.length} مهام');
  }

  void add(String title) {
    final clean = title.trim();
    if (clean.isNotEmpty) todos.add(Task(clean));
  }
}

/// The one store of the app.
final store = AppStore();
