# الدرس 10: مشروع: قائمة المهام بنافذة رسومية

نجمع في هذا المشروع كل ما تعلمناه: **فئة** للمهمة، و**قائمة** من الكائنات، و**دوال** صغيرة، و**أحداث** النافذة، وحفظ المهام في **ملف JSON** لكي تبقى بعد إغلاق البرنامج.

> **تشبيه:** البرنامج مثل **دفتر صغير على مكتبك**: تكتب فيه المهمة، وتشطب ما أنجزته، وتمزق الصفحات المشطوبة، ويبقى الدفتر في مكانه غدًا.

## 1) النموذج (Model) أولًا في الكونسول

نفصل **البيانات والمنطق** عن **الواجهة**. نبدأ بفئة `Task` ونجربها في الكونسول:

```dart run
import 'dart:convert';

class Task {
  final String title;
  bool done;

  Task(this.title, {this.done = false});

  String get display => done ? '✓ $title' : '○ $title';

  Map<String, dynamic> toJson() => {'title': title, 'done': done};

  factory Task.fromJson(Map<String, dynamic> json) =>
      Task(json['title'] as String, done: json['done'] as bool);
}

void main() {
  final tasks = [Task('شراء الخبز'), Task('مذاكرة Dart'), Task('الاتصال بجدتي')];
  tasks[1].done = true;
  for (final t in tasks) {
    print(t.display);
  }
  final left = tasks.where((t) => !t.done).length;
  print('المتبقي: $left من ${tasks.length}');

  final text = jsonEncode(tasks.map((t) => t.toJson()).toList());
  print(text);
  final back = (jsonDecode(text) as List).map((j) => Task.fromJson(j)).toList();
  print(back.last.title);
}
```

```text output
○ شراء الخبز
✓ مذاكرة Dart
○ الاتصال بجدتي
المتبقي: 2 من 3
[{"title":"شراء الخبز","done":false},{"title":"مذاكرة Dart","done":true},{"title":"الاتصال بجدتي","done":false}]
الاتصال بجدتي
```

- `toJson` تحوّل الكائن إلى `Map`، و`jsonEncode` تحوّل الـ Map إلى نص JSON يُحفظ في ملف.
- `factory Task.fromJson` **باني مصنع**: ينشئ الكائن من الـ Map بعد قراءته من الملف.
- `Map<String, dynamic>`: المفاتيح نصوص، والقيم من أي نوع (`dynamic`).

## 2) تصميم النافذة

أنشئ مشروعًا: **File > New Project...** ثم من مجموعة **Scripting** اختر **Dart (GUI Bridge)** باسم `TodoDart`، وارسم:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtTask` | (فارغ) |
| `Button` | `btnAdd` | `أضف` |
| `ListBox` | `lstTasks` | |
| `Button` | `btnToggle` | `أنجزت / لم أنجز` |
| `Button` | `btnDelete` | `احذف` |
| `Button` | `btnClearDone` | `احذف المنجزة` |
| `Label` | `lblStats` | (فارغ) |

## 3) الكود

اكتب الفئة `Task` في ملف منفصل `task.dart`: من **Project > Add Module...** (أو انقر بالزر الأيمن على المشروع في **Solution Explorer**) أضف وحدة اسمها `task`، ثم استوردها في `Form1.dart`:

<!-- test: {"events": [{"set": {"txtTask.Text": "شراء الخبز"}}, "btnAdd.Click", {"set": {"txtTask.Text": "مذاكرة Dart"}}, "btnAdd.Click", {"set": {"txtTask.Text": "   "}}, "btnAdd.Click", {"set": {"txtTask.Text": "الرياضة"}}, "btnAdd.Click", {"set": {"lstTasks.ListIndex": "1"}}, "btnToggle.Click", {"set": {"lstTasks.ListIndex": "0"}}, "btnToggle.Click", "btnClearDone.Click", {"set": {"lstTasks.ListIndex": "-1"}}, "btnDelete.Click"], "expect": {"lstTasks.items": "○ الرياضة", "lblStats.Text": "المتبقي: 1 من 1"}, "msgbox": ["اكتب المهمة أولًا", "اختر مهمة من القائمة"], "captions": {"btnAdd": "أضف", "btnToggle": "أنجزت / لم أنجز", "btnDelete": "احذف", "btnClearDone": "احذف المنجزة"}} -->
```dart form run
// #file: task.dart
class Task {
  final String title;
  bool done;

  Task(this.title, {this.done = false});

  String get display => done ? '✓ $title' : '○ $title';

  Map<String, dynamic> toJson() => {'title': title, 'done': done};

  factory Task.fromJson(Map<String, dynamic> json) =>
      Task(json['title'] as String, done: json['done'] as bool);
}

// #file: Form1.dart
import 'dart:convert';
import 'dart:io';

import 'radgui.dart';
import 'task.dart';

final tasks = <Task>[];
final dataFile = File('tasks.json');

void Form1_Load(RadEvent e) {
  if (dataFile.existsSync()) {
    final list = jsonDecode(dataFile.readAsStringSync()) as List;
    tasks.addAll(list.map((j) => Task.fromJson(j)));
  }
  refresh();
}

/// يعيد رسم القائمة والإحصاء من البيانات، ثم يحفظ الملف.
void refresh() {
  Rad.call('lstTasks', 'Clear');
  for (final t in tasks) {
    Rad.call('lstTasks', 'AddItem', [t.display]);
  }
  final left = tasks.where((t) => !t.done).length;
  Rad.set('lblStats', 'Text', 'المتبقي: $left من ${tasks.length}');
  dataFile.writeAsStringSync(jsonEncode(tasks.map((t) => t.toJson()).toList()));
}

int? selectedIndex() {
  final i = Rad.getNum('lstTasks', 'ListIndex').toInt();
  if (i < 0 || i >= tasks.length) {
    msgbox('اختر مهمة من القائمة');
    return null;
  }
  return i;
}

void btnAdd_Click(RadEvent e) {
  final title = Rad.get('txtTask', 'Text').trim();
  if (title.isEmpty) {
    msgbox('اكتب المهمة أولًا');
    return;
  }
  tasks.add(Task(title));
  Rad.set('txtTask', 'Text', '');
  print('أُضيفت: $title');
  refresh();
}

void btnToggle_Click(RadEvent e) {
  final i = selectedIndex();
  if (i == null) return;
  tasks[i].done = !tasks[i].done;
  refresh();
}

void btnDelete_Click(RadEvent e) {
  final i = selectedIndex();
  if (i == null) return;
  tasks.removeAt(i);
  refresh();
}

void btnClearDone_Click(RadEvent e) {
  final before = tasks.length;
  tasks.removeWhere((t) => t.done);
  print('حُذفت ${before - tasks.length} مهام منجزة');
  refresh();
}
```

```text output
أُضيفت: شراء الخبز
أُضيفت: مذاكرة Dart
أُضيفت: الرياضة
حُذفت 2 مهام منجزة
```

اضغط **F5**: أضف مهام، اختر واحدة واضغط **أنجزت**، ثم أغلق البرنامج وشغله من جديد: المهام ما زالت موجودة! تجد الملف `tasks.json` في مجلد المشروع.

## 4) كيف يعمل البرنامج؟

1. القائمة `tasks` (على مستوى الملف) هي **مصدر الحقيقة**: كل زر يغيّر البيانات فقط.
2. بعد كل تغيير نستدعي `refresh()` التي **تعيد رسم** القائمة والإحصاء من البيانات، وتحفظ الملف.
3. `selectedIndex()` دالة مساعدة تُرجع `int?`: رقم المهمة المختارة، أو `null` مع رسالة إذا لم يختر المستخدم شيئًا. لاحظ كيف يستخدمها زران بسطر `if (i == null) return;`.
4. `removeWhere` تحذف كل المهام التي تحقق الشرط دفعة واحدة.

> **هذه هي فكرة Flutter نفسها!** في Flutter أيضًا تغيّر **البيانات** ثم تطلب إعادة الرسم (`setState`)، فتُبنى الواجهة من البيانات من جديد. إذا فهمت `refresh()` هنا فهمت قلب Flutter.

## 5) أفكار للتطوير

- أضف `CheckBox` باسم `chkHideDone` يخفي المهام المنجزة من القائمة.
- رتّب المهام بحيث تظهر غير المنجزة أولًا.
- أضف تاريخ الإضافة لكل مهمة بـ `DateTime.now()`.

## تمارين

### التمرين 1

أضف إلى `Task` خاصية `priority` (رقم من 1 إلى 3، والافتراضي 2) واجعل `display` تبدأ بنجوم بعددها. ثم رتّب قائمة المهام تنازليًا حسب الأولوية واطبعها.

```dart exercise
class Task {
  final String title;
  bool done;
  Task(this.title, {this.done = false});
  String get display => done ? '✓ $title' : '○ $title';
}

void main() {
  final tasks = [Task('قراءة'), Task('دواء الجد'), Task('ألعاب')];
  for (final t in tasks) {
    print(t.display);
  }
}
```

```dart solution
class Task {
  final String title;
  bool done;
  final int priority;
  Task(this.title, {this.done = false, this.priority = 2});
  String get display => '${'*' * priority} ${done ? '✓' : '○'} $title';
}

void main() {
  final tasks = [Task('قراءة'), Task('دواء الجد', priority: 3), Task('ألعاب', priority: 1)];
  tasks.sort((a, b) => b.priority.compareTo(a.priority));
  for (final t in tasks) {
    print(t.display);
  }
}
```

```text output
*** ○ دواء الجد
** ○ قراءة
* ○ ألعاب
```

`sort((a, b) => b.priority.compareTo(a.priority))` ترتب تنازليًا: نقارن `b` بـ `a` بدل `a` بـ `b`.

### التمرين 2

في نافذة: زر `btnSort` يرتب عناصر القائمة `lstNames` أبجديًا. اقرأ العناصر بـ `Rad.call('lstNames', 'List', [i])` لكل `i` من 0 إلى `ListCount - 1`، ثم امسح القائمة وأضفها مرتبة، واكتب في `lblInfo`: `رُتّبت 3 عناصر`.

<!-- test: {"lists": {"lstNames": ["Mona", "Ali", "Zaid"]}, "events": ["btnSort.Click"], "expect": {"lstNames.items": "Ali|Mona|Zaid", "lblInfo.Text": "رُتّبت 3 عناصر"}} -->
```dart form exercise
import 'radgui.dart';

void btnSort_Click(RadEvent e) {
}
```

<!-- test: {"lists": {"lstNames": ["Mona", "Ali", "Zaid"]}, "events": ["btnSort.Click"], "expect": {"lstNames.items": "Ali|Mona|Zaid", "lblInfo.Text": "رُتّبت 3 عناصر"}, "captions": {"btnSort": "رتّب"}} -->
```dart form solution
import 'radgui.dart';

void btnSort_Click(RadEvent e) {
  final count = Rad.getNum('lstNames', 'ListCount').toInt();
  final names = [for (var i = 0; i < count; i++) Rad.call('lstNames', 'List', [i])];
  names.sort();
  Rad.call('lstNames', 'Clear');
  for (final n in names) {
    Rad.call('lstNames', 'AddItem', [n]);
  }
  Rad.set('lblInfo', 'Text', 'رُتّبت ${names.length} عناصر');
}
```

## اختبر نفسك

```quiz
{"question": "لماذا نستدعي refresh() بعد كل تغيير في المهام؟", "choices": ["لتسريع البرنامج", "لكي تُبنى القائمة الظاهرة من البيانات فتبقى الواجهة مطابقة لها", "لأن الأزرار لا تعمل بدونها", "لحذف الملف"], "answer": 1, "explanation": "البيانات مصدر الحقيقة، والواجهة تُرسم منها. هذا هو مبدأ Flutter أيضًا."}
```

```quiz
{"question": "ما وظيفة jsonEncode؟", "choices": ["تقرأ ملفًا", "تحوّل قائمة أو Map إلى نص JSON", "تحذف المهام", "تطبع على الشاشة"], "answer": 1, "explanation": "jsonEncode تحوّل البيانات إلى نص يمكن حفظه، وjsonDecode تعكس العملية."}
```

## الخلاصة

- نفصل النموذج (فئة `Task`) عن الواجهة، ونجربه في الكونسول أولًا.
- البيانات مصدر الحقيقة، و`refresh()` تعيد رسم الواجهة منها بعد كل تغيير.
- `jsonEncode` / `jsonDecode` و`File` لحفظ البيانات بين مرات التشغيل.
- `// #file:` في المثال تعني أن الكود موزع على ملفين: `task.dart` و`Form1.dart`.
