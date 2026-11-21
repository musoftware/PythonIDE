# الدرس 6: القوائم: أداة MListView

**في هذا الدرس ستتعلم:**

- عرض قائمة صفوف بأداة `MListView`، وتحديد شكل الصف بالخاصية `ItemTemplate`.
- إضافة الصفوف وحذفها وتعديلها من الكود.
- معرفة الصف الذي لمسه المستخدم بالحدث `Tap` و `e.Index`.
- البحث في القائمة (تصفية الصفوف).

## صف القائمة: حقول تفصلها العلامة |

كل صف في `MListView` نص واحد، والعلامة `|` تقسمه إلى **حقول**. الخاصية `ItemTemplate` تقول ما معنى كل حقل:

| `ItemTemplate` | مثال صف | كيف يظهر |
|---|---|---|
| `title` | `'شاي'` | سطر واحد |
| `title|subtitle` | `'شاي|10 جنيهات'` | عنوان وتحته سطر رمادي |
| `icon|title|subtitle` | `'coffee|قهوة|15 جنيهًا'` | أيقونة ثم عنوان وعنوان فرعي |
| `title|subtitle|trailing` | `'شاي|مشروب ساخن|10'` | ونص صغير في آخر الصف |

الأيقونة اسم من أيقونات Material مثل `home` و `person` و `star` و `shopping_cart`.

في المصمم: اختر القائمة، ثم اكتب في الخاصية `Items` الصفوف مفصولة بفاصلة منقوطة `;`، مثل `شاي|10;قهوة|15`.

## دوال القائمة في الكود

| الكود | ماذا يفعل؟ |
|---|---|
| `lstMenu.addItem('شاي|10')` | يضيف صفًّا في الآخر |
| `lstMenu.insertItem(0, 'ماء|5')` | يضيف صفًّا في مكان معيّن |
| `lstMenu.removeAt(2)` | يحذف الصف رقم 2 |
| `lstMenu.clear()` | يحذف كل الصفوف |
| `lstMenu.count` | عدد الصفوف |
| `lstMenu.items` | قائمة الصفوف (`List<String>`) |
| `lstMenu.field(i, n)` | الحقل رقم `n` من الصف رقم `i` |
| `lstMenu.setItems(list)` | يستبدل كل الصفوف بقائمة جديدة |
| `lstMenu.selectedIndex` | الصف المختار (`-1` = لا شيء) |

تذكر: الترقيم يبدأ من **صفر**. الصف الأول رقمه `0`.

## مثال: قائمة مشتريات

<!-- test: {"controls": {"lstShop": {"ItemTemplate": "title|subtitle"}}, "do": ["txtItem.text = 'خبز'", "txtQty.text = '2'", "btnAdd_Click()", "txtItem.text = 'لبن'", "txtQty.text = '1'", "btnAdd_Click()", "txtItem.text = 'جبن'", "txtQty.text = ''", "btnAdd_Click()", "lstShop_Tap(const RadEvent(Index: 0))"], "expect": {"lstShop.count": "2", "lstShop.field(0, 0)": "لبن", "lblCount.text": "2 عنصر"}, "msgbox": ["حذف: خبز (الكمية: 2)"]} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnAdd_Click() {
    final item = txtItem.text.trim();
    final qty = int.tryParse(txtQty.text) ?? 1;
    if (item.isEmpty) return;
    lstShop.addItem('$item|الكمية: $qty');
    txtItem.text = '';
    txtQty.text = '';
    showCount();
  }

  // لمسة على صف: نحذفه
  void lstShop_Tap(RadEvent e) {
    final name = lstShop.field(e.Index, 0);
    final qty = lstShop.field(e.Index, 1);
    lstShop.removeAt(e.Index);
    MsgBox('حذف: $name ($qty)');
    showCount();
  }

  void showCount() {
    lblCount.text = '${lstShop.count} عنصر';
    print(lstShop.items);
  }
}
```

```text output
[خبز|الكمية: 2]
[خبز|الكمية: 2, لبن|الكمية: 1]
[خبز|الكمية: 2, لبن|الكمية: 1, جبن|الكمية: 1]
[لبن|الكمية: 1, جبن|الكمية: 1]
```

- `int.tryParse(txtQty.text) ?? 1`: إذا كانت الكمية فارغة أو ليست رقمًا نعتبرها `1`.
- `print(lstShop.items)` يطبع القائمة كلها بين قوسين مربعين، وهذا مفيد جدًا لتتبع الكود.

## البحث في القائمة

لكي نبحث، نحتفظ بكل الصفوف في **قائمة Dart** عادية (`List<String>`)، ونعرض في الأداة الصفوف التي تحتوي نص البحث فقط. هذه نفس فكرة عيّنة **HelloMobile** في مجلد `samples`:

<!-- test: {"controls": {"lstNames": {"Items": "Ahmed;Mona;Mohamed;Sara"}}, "do": ["@enter:txtFilter=mo", "@enter:txtFilter=sa", "@enter:txtFilter="], "expect": {"lstNames.count": "4"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final List<String> all = [];

  void MainScreen_Load() {
    all.addAll(lstNames.items);      // نحفظ نسخة من كل الأسماء
  }

  void txtFilter_Changed(RadEvent e) {
    final q = e.Text.trim().toLowerCase();
    lstNames.setItems(all.where((n) => n.toLowerCase().contains(q)));
    print('$q -> ${lstNames.items}');
  }
}
```

```text output
mo -> [Mona, Mohamed]
sa -> [Sara]
 -> [Ahmed, Mona, Mohamed, Sara]
```

- `all.where((n) => ...)` تختار العناصر التي يتحقق فيها الشرط. الجزء `(n) => ...` **دالة صغيرة بلا اسم** تأخذ عنصرًا وترجع صحيح أو خطأ.
- `toLowerCase()` تجعل البحث لا يفرّق بين الحروف الكبيرة والصغيرة.

## أخطاء شائعة

- **`RangeError (index)`**: طلبت صفًّا غير موجود، مثل `removeAt(5)` والقائمة فيها 3 صفوف. افحص `e.Index < lstShop.count`.
- **حقل غير موجود**: `field(i, 2)` على صف ليس فيه إلا حقلان يرجع نصًّا فارغًا.
- **نسيان النسخة الأصلية** في البحث: إذا صفّيت `lstNames` نفسها ضاعت الأسماء المحذوفة من العرض للأبد.

## تمرين

قائمة درجات: عند الضغط على `btnAdd` أضف الصف `<الاسم>|<الدرجة>` من الحقلين `txtName` و `txtScore`، ثم اكتب في `lblAvg` متوسط الدرجات بالشكل `المتوسط: 85.0` واطبعه. (اجمع الحقل رقم 1 من كل الصفوف بحلقة تكرار.)

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnAdd_Click() {
    // lstScores.addItem(...)
    // for (var i = 0; i < lstScores.count; i++) { ... lstScores.field(i, 1) ... }
  }
}
```

<!-- test: {"do": ["txtName.text = 'Ali'", "txtScore.text = '80'", "btnAdd_Click()", "txtName.text = 'Mona'", "txtScore.text = '90'", "btnAdd_Click()"], "expect": {"lblAvg.text": "المتوسط: 85.0", "lstScores.count": "2"}} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnAdd_Click() {
    lstScores.addItem('${txtName.text}|${txtScore.text}');
    var sum = 0.0;
    for (var i = 0; i < lstScores.count; i++) {
      sum += double.tryParse(lstScores.field(i, 1)) ?? 0;
    }
    lblAvg.text = 'المتوسط: ${sum / lstScores.count}';
    print(lblAvg.text);
  }
}
```

```text output
المتوسط: 80.0
المتوسط: 85.0
```

## اختبر نفسك

```quiz
{"question": "ما رقم الصف الأول في MListView؟", "choices": ["1", "0", "-1", "حسب ItemTemplate"], "answer": 1, "explanation": "الترقيم يبدأ من صفر، و -1 معناها لا يوجد صف مختار."}
```

```quiz
{"question": "صف القائمة 'قهوة|15|coffee'. ماذا يرجع field(i, 1)؟", "choices": ["قهوة", "15", "coffee", "قهوة|15"], "answer": 1, "explanation": "الحقول مرقمة من صفر: 0 قهوة، 1 هي 15، 2 هي coffee."}
```

```quiz
{"question": "أي حدث يخبرك بالصف الذي لمسه المستخدم؟", "choices": ["Changed مع e.Text", "Tap مع e.Index", "Click مع e.Action", "Load"], "answer": 1, "explanation": "Tap لأداة MListView ومعه e.Index رقم الصف."}
```

## الخلاصة

- الصف نص واحد، والعلامة `|` تقسمه إلى حقول يحدد معناها `ItemTemplate`.
- `addItem` و `removeAt` و `clear` و `setItems` و `field` و `count` تكفي لمعظم القوائم.
- `Tap` و `e.Index` لمعرفة الصف الملموس، والبحث يحتاج نسخة أصلية من الصفوف.
