# الدرس 2: تطبيقك الأول: مشروع Flutter App

**في هذا الدرس ستتعلم:**

- إنشاء مشروع موبايل جديد من قالب **Flutter App**.
- ما هي الملفات التي تصنعها RAD IDE، وأيها تكتب فيه وأيها لا تلمسه.
- تشغيل التطبيق بالمفتاح `F5`.
- قراءة كود الشاشة سطرًا سطرًا.

## الخطوة 1: مشروع جديد

1. من القائمة **File > New Project...** (ملف > مشروع جديد...).
2. في الجهة اليسرى اختر المجموعة **Mobile** (موبايل).
3. اختر القالب **Flutter App**، واكتب اسم المشروع (مثلًا `FlutterApp1`) ومكانه، ثم **OK**.

يوجد قالب ثانٍ اسمه **Flutter App (tabs + drawer)**: شريط تنقل سفلي بثلاث صفحات، وقائمة جانبية، وزر عائم، وشاشة ثانية. جرّبه لاحقًا.

## الخطوة 2: تعرّف على الملفات

افتح **Solution Explorer** (مستكشف الحلول) وسترى:

| الملف | ما هو؟ | هل تعدّله؟ |
|---|---|---|
| `MainScreen.form` | تصميم الشاشة (الأدوات وأماكنها) | نعم، من **المصمم** فقط |
| `lib/main_screen.dart` | **كودك**: دوال الأحداث | نعم، هنا تكتب |
| `lib/main_screen_designer.dart` | كود Flutter الذي يرسم الشاشة، يُولَّد من التصميم | لا، يُعاد كتابته عند كل حفظ |
| `lib/main.dart` | بداية التطبيق وقائمة الشاشات | لا، يُولَّد تلقائيًا |
| `lib/radapp.dart` | مكتبة RAD IDE الصغيرة: `MsgBox` و `Toast` و `ShowForm` ... | لا |
| `pubspec.yaml` | اسم التطبيق والمكتبات التي يستخدمها | نادرًا |

> **تشبيه:** ملف `_designer.dart` مثل نسخة مطبوعة من رسم المهندس: كلما عدّلت الرسم (المصمم) طُبعت نسخة جديدة. لو كتبت على النسخة المطبوعة بالقلم ستضيع كتابتك مع الطبعة التالية. اكتب دائمًا في `main_screen.dart`.

## الخطوة 3: شغّل التطبيق

1. في شريط **Mobile** أعلى النافذة ستجد قائمة **Device:** (الجهاز). اختر `Windows` (أسرع خيار للتجربة) أو متصفحًا.
2. اضغط `F5`.
3. اكتب اسمك في الحقل واضغط **Say hello**: تظهر تحية جديدة في القائمة.

## الكود سطرًا سطرًا

هذا هو كود الشاشة الذي يكتبه القالب في `lib/main_screen.dart` (مختصرًا قليلًا):

<!-- test: {"template": "flutter_app", "do": ["txtName.text = 'Sara'", "btnHello_Click()", "txtName.text = 'Omar'", "btnHello_Click()"], "expect": {"lstGreetings.count": "2", "lstGreetings.field(0, 0)": "Hello, Sara!", "txtName.text": ""}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    lblHello.text = 'Welcome! Type your name and tap the button.';
  }

  void btnHello_Click() {
    final name = txtName.text.trim();
    if (name.isEmpty) {
      Toast('Please type your name first');
      return;
    }
    lstGreetings.addItem('Hello, $name!|from RAD IDE');
    txtName.text = '';
  }
}
```

### `import` و `part`

- `import 'package:flutter/material.dart';` يحضر مكتبة **Material** (أزرار Google وألوانها وخطوطها).
- `import 'radapp.dart';` يحضر مكتبة RAD IDE: فيها `MsgBox` و `Toast` و `ShowForm` وأنواع الأدوات.
- `part 'main_screen_designer.dart';` يقول: «الملف المولَّد جزء من هذا الملف». لذلك ترى الأدوات (`txtName` مثلًا) في كودك دون أن تعرّفها.

### `class MainScreenCode extends MainScreenDesigner`

هذه **فئة** (class) الشاشة. الجزء المولَّد `MainScreenDesigner` يحتوي الأدوات ورسم الشاشة، وفئتك `MainScreenCode` **ترث** منه وتضيف الأحداث. الفكرة نفسها في فيجوال بيسك: النموذج فيه الأدوات، وأنت تضيف الكود.

### دوال الأحداث

- `void MainScreen_Load()` يُنفَّذ مرة واحدة عند ظهور الشاشة، مثل `Form_Load` في فيجوال بيسك.
- `void btnHello_Click()` يُنفَّذ عند الضغط على الزر `btnHello`. الاسم دائمًا **اسم الأداة + `_` + اسم الحدث**.

### داخل الحدث

- `txtName.text` النص المكتوب في الحقل، و`.trim()` تحذف المسافات من الطرفين.
- `name.isEmpty` صحيحة إذا كان النص فارغًا.
- `Toast('...')` رسالة قصيرة تظهر أسفل الشاشة ثم تختفي وحدها.
- `return;` تخرج من الدالة فورًا.
- `lstGreetings.addItem('Hello, $name!|from RAD IDE')` تضيف صفًّا إلى القائمة. العلامة `|` تفصل **العنوان** عن **العنوان الفرعي** (سنفهمها في درس القوائم).

> **لاحظ:** تغيير خاصية أداة مثل `lblHello.text = '...'` يعيد رسم الشاشة وحده. في Flutter العادي تكتب `setState(...)`، أما مكتبة RAD IDE فتفعلها لك.

## كيف يعمل زر «تحقق»؟

يشغّل الـ IDE شاشتك في **اختبار Flutter** (بلا نافذة): يكتب في الحقول، ويستدعي الأحداث، ثم يقارن خصائص الأدوات بالمطلوب. في المثال السابق كتب الاختبار `Sara` ثم ضغط الزر، ثم `Omar` ثم ضغط الزر، وتأكد أن في القائمة صفّين وأن الحقل فارغ.

## أخطاء شائعة

- **الكتابة في ملف `_designer.dart`**: يضيع كودك عند الحفظ التالي.
- **تغيير اسم الدالة يدويًا** (مثلًا `btnhello_Click`): لن يربطها الـ IDE بالزر. Dart حساسة لحالة الأحرف.
- **نسيان `return;`** بعد رسالة الخطأ، فيكمل الكود ويضيف تحية فارغة.

## تمرين

عدّل الحدث ليكتب التحية بالعربية: `أهلًا يا <الاسم>!`، ويطبع في نافذة المخرجات عدد التحيات بعد كل إضافة بالشكل `عدد التحيات: 1`.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnHello_Click() {
    final name = txtName.text.trim();
    if (name.isEmpty) {
      Toast('اكتب اسمك أولًا');
      return;
    }
    // أضف التحية بالعربية ثم اطبع عدد التحيات (lstGreetings.count)
  }
}
```

<!-- test: {"template": "flutter_app", "do": ["txtName.text = 'منى'", "btnHello_Click()", "txtName.text = 'علي'", "btnHello_Click()"], "expect": {"lstGreetings.field(1, 0)": "أهلًا يا علي!"}} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnHello_Click() {
    final name = txtName.text.trim();
    if (name.isEmpty) {
      Toast('اكتب اسمك أولًا');
      return;
    }
    lstGreetings.addItem('أهلًا يا $name!');
    print('عدد التحيات: ${lstGreetings.count}');
  }
}
```

```text output
عدد التحيات: 1
عدد التحيات: 2
```

## اختبر نفسك

```quiz
{"question": "في أي ملف تكتب كود الأحداث؟", "choices": ["lib/main_screen_designer.dart", "lib/main_screen.dart", "lib/main.dart", "pubspec.yaml"], "answer": 1, "explanation": "ملف الشاشة نفسه (بدون _designer) هو ملفك، والباقي يولّده الـ IDE."}
```

```quiz
{"question": "ما اسم دالة حدث الضغط على زر اسمه btnSave؟", "choices": ["Click_btnSave()", "btnSave_Click()", "onSaveClick()", "btnSave.Click()"], "answer": 1, "explanation": "الاسم دائمًا: اسم الأداة ثم _ ثم اسم الحدث."}
```

```quiz
{"question": "ماذا يحدث لكود كتبته داخل ملف _designer.dart؟", "choices": ["يبقى للأبد", "يضيع عند الحفظ التالي للتصميم", "يتحول إلى تعليق", "يظهر خطأ فورًا"], "answer": 1, "explanation": "الملف يُعاد توليده من التصميم في كل حفظ أو تشغيل."}
```

## الخلاصة

- **File > New Project... > Mobile > Flutter App** ينشئ مشروعًا جاهزًا للتشغيل بـ `F5`.
- تكتب في `lib/<screen>.dart` فقط، والملفات المولَّدة لا تُعدَّل.
- الحدث = دالة اسمها `اسم_الأداة_الحدث`، والخصائص مثل `txtName.text` تقرأ وتكتب وتعيد رسم الشاشة.
