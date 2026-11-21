# الدرس 12: المشروع النهائي: تطبيق قائمة المهام

في هذا الدرس نجمع كل ما تعلمناه في تطبيق حقيقي: **قائمة مهام** (To-do). المستخدم يكتب مهمة ويضيفها، ويلمسها ليعلّمها «تمّت»، ويخفي المهام المنتهية بمفتاح، ويحذفها كلها بزر في الشريط العلوي بعد التأكيد.

## الخطوة 1: المشروع والتصميم

1. **File > New Project... > Mobile > Flutter App** باسم `TodoApp`.
2. احذف أدوات القالب، ثم ضع هذه الأدوات (من أعلى لأسفل) وغيّر أسماءها من نافذة الخصائص:

| الأداة | الاسم | خصائص مهمة |
|---|---|---|
| `AppBar` | `AppBar1` | `Title` = `مهامي`، و`Actions` = `delete_sweep` |
| `MTextField` | `txtTask` | `Hint` = `مهمة جديدة`، و`Anchor` = `Top, Left, Right` |
| `Button` | `btnAdd` | `Text` = `إضافة` |
| `Switch` | `swHide` | (إخفاء المنتهية) |
| `Label` | `lblStats` | |
| `MListView` | `lstTasks` | `ItemTemplate` = `icon|title`، و`Items` فارغة |

3. انقر نقرًا مزدوجًا على كل أداة لتنشئ أحداثها: `btnAdd_Click` و `lstTasks_Tap` و `swHide_Changed` و `AppBar1_Click`، ثم حدث الشاشة `MainScreen_Load`.

## الخطوة 2: نموذج البيانات

نحتفظ بالمهام في **قائمة Dart** من كائنات فئة صغيرة اسمها `Task`، ونعيد بناء صفوف `lstTasks` منها كلما تغيّر شيء. هذا أنظف من تخزين البيانات داخل نصوص الصفوف:

```dart
class Task {
  Task(this.title);       // المُنشئ: Task('شراء خبز')
  final String title;
  bool done = false;
}
```

> **تشبيه:** القائمة `tasks` هي **الدفتر** الذي نكتب فيه الحقيقة، والأداة `lstTasks` هي **السبورة** التي ننقل إليها ما في الدفتر. نعدّل الدفتر دائمًا، ثم نعيد كتابة السبورة بالدالة `refreshList()`.

## الخطوة 3: الكود كاملًا

<!-- test: {"controls": {"AppBar1": {"Title": "مهامي", "Actions": "delete_sweep"}, "lstTasks": {"ItemTemplate": "icon|title"}}, "do": ["txtTask.text = 'شراء خبز'", "btnAdd_Click()", "txtTask.text = 'مذاكرة Flutter'", "btnAdd_Click()", "txtTask.text = 'رياضة'", "btnAdd_Click()", "lstTasks_Tap(const RadEvent(Index: 0))", "swHide.checked = true", "swHide_Changed()", "AppBar1_Click(const RadEvent(Action: 'delete_sweep'))", "@yes"], "expect": {"lstTasks.count": "2", "lblStats.text": "0 من 2 تمّت"}, "toast": ["حُذفت 1 مهمة منتهية"]} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class Task {
  Task(this.title);
  final String title;
  bool done = false;
}

class MainScreenCode extends MainScreenDesigner {
  final List<Task> tasks = [];
  List<Task> shown = [];            // المهام الظاهرة الآن في القائمة

  void MainScreen_Load() {
    refreshList();
  }

  void btnAdd_Click() {
    final title = txtTask.text.trim();
    if (title.isEmpty) {
      Toast('اكتب المهمة أولًا');
      return;
    }
    tasks.add(Task(title));
    txtTask.text = '';
    refreshList();
  }

  void lstTasks_Tap(RadEvent e) {
    final t = shown[e.Index];
    t.done = !t.done;               // اعكس الحالة
    refreshList();
  }

  void swHide_Changed() {
    refreshList();
  }

  Future<void> AppBar1_Click(RadEvent e) async {
    if (e.Action != 'delete_sweep') return;
    final n = tasks.where((t) => t.done).length;
    if (n == 0) {
      Toast('لا توجد مهام منتهية');
      return;
    }
    if (await Confirm('حذف $n من المهام المنتهية؟')) {
      tasks.removeWhere((t) => t.done);
      refreshList();
      Toast('حُذفت $n مهمة منتهية');
    }
  }

  void refreshList() {
    shown = swHide.checked ? tasks.where((t) => !t.done).toList() : List.of(tasks);
    lstTasks.setItems(shown.map((t) => '${t.done ? 'check_box' : 'check_box_outline_blank'}|${t.title}'));
    final done = tasks.where((t) => t.done).length;
    lblStats.text = '$done من ${tasks.length} تمّت';
    print(lblStats.text);
  }
}
```

```text output
0 من 0 تمّت
0 من 1 تمّت
0 من 2 تمّت
0 من 3 تمّت
1 من 3 تمّت
1 من 3 تمّت
0 من 2 تمّت
```

## شرح الأجزاء المهمة

- `final List<Task> tasks = [];` الدفتر: كل المهام. `final` معناها أن المتغير يشير دائمًا إلى نفس القائمة، لكن محتواها يتغير.
- `shown` المهام الظاهرة فعلًا. نحتاجها لأن رقم الصف `e.Index` في القائمة الظاهرة قد يختلف عن رقمه في `tasks` عندما نخفي المنتهية.
- `t.done = !t.done;` يعكس القيمة: `true` تصبح `false` والعكس.
- `tasks.where((t) => t.done).length` عدد المهام المنتهية.
- `tasks.removeWhere((t) => t.done)` يحذف كل مهمة منتهية مرة واحدة.
- `shown.map((t) => '...')` يحوّل كل مهمة إلى نص صف: أيقونة `check_box` أو `check_box_outline_blank`، ثم العنوان.
- `AppBar1_Click` يستقبل `e.Action`، وهو اسم الزر الذي ضُغط في الشريط العلوي.

## الخطوة 4: شغّل وجرّب وابنِ

1. اختر الجهاز من قائمة **Device:** واضغط `F5`.
2. أضف مهامًا، والمسها، وجرّب المفتاح وزر الحذف.
3. عدّل نصًّا واحفظ: لاحظ Hot Reload والمهام ما زالت موجودة.
4. ابنِ `APK` من **Build > Mobile App > Android APK** وثبّته على هاتفك.

## تمرين 1: منع التكرار

عدّل `btnAdd_Click` بحيث إذا كانت المهمة موجودة مسبقًا (بنفس العنوان) لا تُضاف، ويظهر `Toast('المهمة موجودة')`.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final List<String> tasks = [];

  void btnAdd_Click() {
    final title = txtTask.text.trim();
    if (title.isEmpty) return;
    // إذا كانت tasks.contains(title) ...
    tasks.add(title);
    lstTasks.setItems(tasks);
  }
}
```

<!-- test: {"do": ["txtTask.text = 'رياضة'", "btnAdd_Click()", "txtTask.text = 'رياضة'", "btnAdd_Click()", "txtTask.text = 'قراءة'", "btnAdd_Click()"], "expect": {"lstTasks.count": "2"}, "toast": ["المهمة موجودة"]} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final List<String> tasks = [];

  void btnAdd_Click() {
    final title = txtTask.text.trim();
    if (title.isEmpty) return;
    if (tasks.contains(title)) {
      Toast('المهمة موجودة');
      return;
    }
    tasks.add(title);
    lstTasks.setItems(tasks);
  }
}
```

## تمرين 2: العدد في العنوان

اجعل عنوان الشريط العلوي يعرض عدد المهام الباقية بالشكل `مهامي (2)`. الأداة `AppBar1` لها الخاصية `text` مثل أي أداة. اطبع العنوان بعد كل تغيير.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final List<String> tasks = [];

  void btnAdd_Click() {
    tasks.add(txtTask.text);
    // AppBar1.text = ...
  }

  void lstTasks_Tap(RadEvent e) {
    tasks.removeAt(e.Index);       // لمسة = انتهت المهمة
    // AppBar1.text = ...
  }
}
```

<!-- test: {"controls": {"AppBar1": {"Title": "مهامي", "Actions": ""}}, "do": ["txtTask.text = 'a'", "btnAdd_Click()", "txtTask.text = 'b'", "btnAdd_Click()", "lstTasks_Tap(const RadEvent(Index: 0))"], "expect": {"AppBar1.text": "مهامي (1)"}} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final List<String> tasks = [];

  void btnAdd_Click() {
    tasks.add(txtTask.text);
    update();
  }

  void lstTasks_Tap(RadEvent e) {
    tasks.removeAt(e.Index);
    update();
  }

  void update() {
    lstTasks.setItems(tasks);
    AppBar1.text = 'مهامي (${tasks.length})';
    print(AppBar1.text);
  }
}
```

```text output
مهامي (1)
مهامي (2)
مهامي (1)
```

## أفكار لتطوير التطبيق

- شاشة ثانية `EditScreen` تفتح بـ `ShowForm` لتعديل عنوان المهمة (الدرس 7).
- حفظ المهام بعد إغلاق التطبيق: مكتبة `shared_preferences` (أضفها في `pubspec.yaml`).
- تاريخ لكل مهمة، وترتيبها بالتاريخ.

## اختبر نفسك

```quiz
{"question": "لماذا نحتفظ بالقائمة shown بجانب tasks؟", "choices": ["للسرعة فقط", "لأن e.Index يشير إلى الصف الظاهر، وقد يختلف عن مكانه في tasks عند الإخفاء", "لأن Flutter يطلب ذلك", "لا حاجة لها"], "answer": 1, "explanation": "عند إخفاء المنتهية تتغير أرقام الصفوف، فنحتاج القائمة الظاهرة لنعرف المهمة الصحيحة."}
```

```quiz
{"question": "ماذا يفعل `tasks.removeWhere((t) => t.done)`؟", "choices": ["يحذف أول مهمة منتهية", "يحذف كل المهام المنتهية", "يحذف كل المهام", "يعلّم كل المهام منتهية"], "answer": 1, "explanation": "removeWhere يحذف كل عنصر يتحقق فيه الشرط."}
```

```quiz
{"question": "ما قيمة done بعد `done = !done;` إذا كانت true؟", "choices": ["true", "false", "null", "خطأ"], "answer": 1, "explanation": "العامل ! يعكس القيمة المنطقية."}
```

## الخلاصة

- صمّم الشاشة بالأدوات، واكتب الأحداث، واحتفظ بالبيانات في كائنات Dart ثم اعرضها في الأدوات.
- `where` و `map` و `removeWhere` و `contains` أدوات قوية للتعامل مع القوائم.
- مبروك! أنت الآن تصنع تطبيقات موبايل حقيقية وتبنيها لـ Android و Windows والويب.
