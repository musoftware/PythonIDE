// AddTask screen - event handlers (written in the RAD IDE code editor).
part of 'add_task.dart';

class AddTaskEvents extends AddTaskDesigner {
  @override
  void onSave() async {
    final title = txtTitle.text.trim();
    if (title.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter a title')));
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    final list = prefs.getStringList('tasks') ?? <String>[];
    await prefs.setStringList('tasks', [...list, title]);
    if (mounted) Navigator.pop(context);
  }
}
