# الدرس 7: الشاشات المتعددة: ShowForm و CloseForm

**في هذا الدرس ستتعلم:**

- إضافة شاشة ثانية إلى المشروع.
- فتح شاشة بـ `ShowForm`، وإغلاقها بـ `CloseForm`، والرجوع بزر الرجوع.
- إرسال قيمة إلى الشاشة الجديدة (`FormArgs`) واستقبال نتيجة منها.
- مشاركة القيم بين كل الشاشات بـ `RadApp.data`.

## إضافة شاشة

1. من القائمة **Project > Add Windows Form...** (مشروع > إضافة نموذج Windows...). في مشروع الموبايل يصبح النموذج الجديد **شاشة** داخل إطار هاتف.
2. سمِّ الشاشة باسم واضح ينتهي بـ `Screen`، مثل `DetailsScreen`.
3. يضيف الـ IDE الملفات `DetailsScreen.form` و `lib/details_screen.dart` و `lib/details_screen_designer.dart`، ويضيف للشاشة **مسارًا** (route) اسمه `/DetailsScreen` في `lib/main.dart`.

الشاشة التي يبدأ بها التطبيق هي **شاشة البدء** (startup). غيّرها من **Solution Explorer** بالنقر بالزر الأيمن على الشاشة.

> **تشبيه:** الشاشات مثل أوراق مكدّسة فوق بعضها. `ShowForm` تضع ورقة جديدة فوق الكومة، و`CloseForm` (أو زر الرجوع في الهاتف) ترفع الورقة العليا فتظهر التي تحتها كما تركتها.

## الدوال

| الكود | ماذا يفعل؟ |
|---|---|
| `ShowForm('DetailsScreen')` | يفتح الشاشة فوق الحالية |
| `ShowForm('DetailsScreen', قيمة)` | يفتحها ويرسل لها قيمة |
| `await ShowForm(...)` | ينتظر حتى تُغلق الشاشة ويرجع **نتيجتها** |
| `CloseForm()` أو `CloseForm(نتيجة)` | يغلق الشاشة الحالية (ويرجع نتيجة) |
| `FormArgs` | القيمة التي أُرسلت إلى هذه الشاشة |
| `SwitchForm('HomeScreen')` | يستبدل الشاشة الحالية (لا رجوع إليها)، مثل الانتقال من شاشة الدخول |
| `RadApp.data['key']` | مخزن قيم مشترك بين كل الشاشات |

## مثال: تعديل ملاحظة في شاشة ثانية

الكتلة التالية فيها **ملفان**: السطر `// #file: ...` يفصل بينهما. الشاشة الأولى ترسل النص الحالي إلى الثانية وتنتظر، والثانية تعرضه للتعديل ثم ترجع النص الجديد:

<!-- test: {"do": ["btnEdit_Click()", "@screen:EditScreen", "txtNote.text = 'اشترِ خبزًا'", "btnSave_Click()", "@screen:MainScreen", "btnEdit_Click()", "@screen:EditScreen", "btnCancel_Click()", "@screen:MainScreen"], "expect": {"lblNote.text": "اشترِ خبزًا"}, "toast": ["تم الحفظ"]} -->
```flutter run
// #file: lib/main_screen.dart
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    lblNote.text = '(لا توجد ملاحظة)';
  }

  Future<void> btnEdit_Click() async {
    final result = await ShowForm('EditScreen', lblNote.text);
    if (result is String) {
      lblNote.text = result;
      Toast('تم الحفظ');
    }
    print('رجعت النتيجة: $result');
  }
}
// #file: lib/edit_screen.dart
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'edit_screen_designer.dart';

class EditScreenCode extends EditScreenDesigner {
  void EditScreen_Load() {
    txtNote.text = FormArgs as String? ?? '';
  }

  void btnSave_Click() {
    CloseForm(txtNote.text);
  }

  void btnCancel_Click() {
    CloseForm();          // بلا نتيجة: ترجع null
  }
}
```

```text output
رجعت النتيجة: اشترِ خبزًا
رجعت النتيجة: null
```

- `result is String` تفحص **نوع** النتيجة: إذا أُغلقت الشاشة بلا نتيجة (أو بزر الرجوع) تكون `null`.
- `FormArgs as String? ?? ''`: اعتبر القيمة المرسلة نصًّا (قد يكون `null`)، وإذا كانت `null` فاستخدم نصًّا فارغًا.
- في الحدث `EditScreen_Load` نقرأ `FormArgs`، لأن الشاشة تكون جاهزة عندها.

## القيم المشتركة: `RadApp.data`

أحيانًا تحتاج قيمة تراها كل الشاشات، مثل اسم المستخدم بعد الدخول. `RadApp.data` قاموس (`Map`) مشترك، مثل متغير `Public` في وحدة فيجوال بيسك:

<!-- test: {"do": ["txtUser.text = 'mona'", "btnLogin_Click()", "@screen:HomeScreen"], "expect": {"lblWelcome.text": "مرحبًا mona"}} -->
```flutter run
// #file: lib/main_screen.dart
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnLogin_Click() {
    if (txtUser.text.isEmpty) return;
    RadApp.data['user'] = txtUser.text;
    SwitchForm('HomeScreen');     // لا نريد الرجوع إلى شاشة الدخول
  }
}
// #file: lib/home_screen.dart
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'home_screen_designer.dart';

class HomeScreenCode extends HomeScreenDesigner {
  void HomeScreen_Load() {
    lblWelcome.text = 'مرحبًا ${RadApp.data['user']}';
    print(lblWelcome.text);
  }
}
```

```text output
مرحبًا mona
```

## أخطاء شائعة

- **اسم شاشة خطأ** في `ShowForm('Detail')`: يظهر خطأ `Could not find a generator for route`. الاسم يجب أن يطابق اسم النموذج تمامًا.
- **قراءة `FormArgs` في متغير الصنف** (خارج الدوال): لا يكون السياق جاهزًا بعد. اقرأه في حدث `Load`.
- **استخدام `ShowForm` بعد الدخول**: يبقى زر الرجوع عائدًا إلى شاشة الدخول. استخدم `SwitchForm`.

## تمرين

في الشاشة الأولى زر `btnPick` يفتح الشاشة `ColorScreen` وينتظر. في `ColorScreen` زرّان: `btnRed` يغلق الشاشة بالنتيجة `'أحمر'`، و`btnBlue` بالنتيجة `'أزرق'`. اكتب النتيجة في `lblColor` بالشكل `اللون: أحمر`.

```flutter exercise
// #file: lib/main_screen.dart
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  Future<void> btnPick_Click() async {
    // final c = await ShowForm(...);
  }
}
// #file: lib/color_screen.dart
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'color_screen_designer.dart';

class ColorScreenCode extends ColorScreenDesigner {
  void btnRed_Click() {
  }

  void btnBlue_Click() {
  }
}
```

<!-- test: {"do": ["btnPick_Click()", "@screen:ColorScreen", "btnBlue_Click()", "@screen:MainScreen"], "expect": {"lblColor.text": "اللون: أزرق"}} -->
```flutter solution
// #file: lib/main_screen.dart
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  Future<void> btnPick_Click() async {
    final c = await ShowForm('ColorScreen');
    if (c is String) lblColor.text = 'اللون: $c';
  }
}
// #file: lib/color_screen.dart
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'color_screen_designer.dart';

class ColorScreenCode extends ColorScreenDesigner {
  void btnRed_Click() {
    CloseForm('أحمر');
  }

  void btnBlue_Click() {
    CloseForm('أزرق');
  }
}
```

## اختبر نفسك

```quiz
{"question": "ماذا يرجع `await ShowForm('X')` إذا رجع المستخدم بزر الرجوع؟", "choices": ["نصًّا فارغًا", "null", "false", "اسم الشاشة"], "answer": 1, "explanation": "الإغلاق بلا نتيجة يرجع null، لذلك نفحص النوع بـ is String."}
```

```quiz
{"question": "أي دالة تستبدل الشاشة الحالية بحيث لا يمكن الرجوع إليها؟", "choices": ["ShowForm", "SwitchForm", "CloseForm", "FormArgs"], "answer": 1, "explanation": "SwitchForm مناسبة بعد شاشة الدخول أو شاشة البداية."}
```

```quiz
{"question": "أين تقرأ القيمة المرسلة إلى الشاشة (FormArgs)؟", "choices": ["في متغير الصنف", "في حدث Load للشاشة", "في main.dart", "في ملف _designer.dart"], "answer": 1, "explanation": "في Load تكون الشاشة جاهزة وتعرف من فتحها."}
```

## الخلاصة

- **Project > Add Windows Form...** يضيف شاشة جديدة، ولها مسار باسمها.
- `ShowForm(name, args)` يفتح، و`await` ينتظر النتيجة، و`CloseForm(result)` يغلق ويرجع النتيجة.
- `FormArgs` لقراءة المرسَل، و`RadApp.data` للقيم المشتركة، و`SwitchForm` للانتقال بلا رجوع.
