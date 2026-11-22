// TaskList screen - event handlers (written in the RAD IDE code editor).
part of 'task_list.dart';

class TaskListEvents extends TaskListDesigner {
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() => tasks = prefs.getStringList('tasks') ?? <String>[]);
  }

  @override
  void openTask(int index) {
    Navigator.pushNamed(context, '/detail', arguments: tasks[index]);
  }

  @override
  void onAdd() async {
    await Navigator.pushNamed(context, '/add');
    await _load();
  }
}
