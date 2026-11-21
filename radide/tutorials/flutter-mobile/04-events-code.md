# الدرس 4: الأحداث والكود: الأزرار والحقول والمفاتيح

**في هذا الدرس ستتعلم:**

- كيف تفتح دالة الحدث من المصمم بنقرة مزدوجة.
- أحداث الموبايل: `Click` و `Changed` و `Submitted` و `Tap` و `Load`.
- معامل الحدث `RadEvent e` وما فيه: `e.Text` و `e.Value` و `e.Index`.
- قراءة الأرقام من حقول الكتابة بأمان.

## من المصمم إلى الكود بنقرة مزدوجة

1. في المصمم انقر نقرًا مزدوجًا على زر اسمه `btnPlus`.
2. يفتح الـ IDE الملف `lib/main_screen.dart` ويضيف دالة فارغة في آخر الفئة:

```dart
  void btnPlus_Click() {
    
  }
```

3. اكتب الكود داخلها. للأحداث الأخرى: اختر الأداة، ثم افتح قائمة **Events** (الأحداث) في نافذة الخصائص وانقر نقرًا مزدوجًا على اسم الحدث.

| الحدث | الأدوات | متى يحدث؟ |
|---|---|---|
| `Click` | `Button` و `Fab` و `AppBar` و `Label` | ضغطة على الأداة |
| `Changed` | `MTextField` و `Switch` و `MSlider` و `CheckBox` و `BottomNav` | تغيّرت القيمة |
| `Submitted` | `MTextField` | ضغط المستخدم زر **Done** أو **Enter** في لوحة المفاتيح |
| `Tap` | `MListView` و `Card` و `MImage` و `Drawer` | لمسة على الأداة أو على صف منها |
| `Load` | الشاشة نفسها: `MainScreen_Load` | ظهور الشاشة أول مرة |

## مثال 1: عدّاد

ثلاثة أزرار وعنوان. لاحظ أن المتغير `count` معرّف **داخل الفئة** وخارج الدوال، لكي تبقى قيمته بين ضغطة وأخرى (مثل متغير على مستوى النموذج في فيجوال بيسك):

<!-- test: {"do": ["btnPlus_Click()", "btnPlus_Click()", "btnPlus_Click()", "btnMinus_Click()"], "expect": {"lblCount.text": "2"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  int count = 0;

  void MainScreen_Load() {
    show();
  }

  void btnPlus_Click() {
    count++;
    show();
  }

  void btnMinus_Click() {
    if (count > 0) count--;
    show();
  }

  void btnReset_Click() {
    count = 0;
    show();
  }

  void show() {
    lblCount.text = '$count';
    btnMinus.enabled = count > 0;
    print('العدد = $count');
  }
}
```

```text output
العدد = 0
العدد = 1
العدد = 2
العدد = 3
العدد = 2
```

- `show()` دالة **مساعدة** كتبناها بأنفسنا لكي لا نكرر نفس الأسطر في كل زر.
- `btnMinus.enabled = count > 0;` يعطّل زر النقصان عندما يكون العدد صفرًا.

## معامل الحدث RadEvent

بعض الأحداث تحمل معلومات. اكتب الدالة مع المعامل `RadEvent e` لتقرأها:

| الخاصية | معناها |
|---|---|
| `e.Text` | النص (حقل الكتابة) |
| `e.Value` | القيمة (`true` أو `false` لـ `Switch`، ورقم لـ `MSlider`) |
| `e.Index` | رقم الصف أو الصفحة (يبدأ من 0) |
| `e.Action` | اسم زر `AppBar` الذي ضُغط |

يمكنك كتابة الدالة **بدون** المعامل إذا لم تحتجه، والـ IDE يستدعيها بالشكل الصحيح في الحالتين.

## مثال 2: حاسبة تتحدث وأنت تكتب

الحدث `Changed` لحقل الكتابة يحدث مع **كل حرف**. هنا نحسب السعر بعد الضريبة فورًا. الدالة `double.tryParse` تحوّل النص إلى رقم، وترجع `null` (لا شيء) إذا لم يكن النص رقمًا، فلا يتوقف التطبيق:

<!-- test: {"do": ["@enter:txtPrice=200", "@enter:txtPrice=abc", "@enter:txtPrice=50"], "expect": {"lblTotal.text": "الإجمالي: 57.00"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void txtPrice_Changed(RadEvent e) {
    final price = double.tryParse(e.Text);
    if (price == null) {
      lblTotal.text = 'اكتب رقمًا';
    } else {
      lblTotal.text = 'الإجمالي: ${(price * 1.14).toStringAsFixed(2)}';
    }
    print(lblTotal.text);
  }
}
```

```text output
الإجمالي: 228.00
اكتب رقمًا
الإجمالي: 57.00
```

- `price * 1.14` يضيف ضريبة 14%.
- `.toStringAsFixed(2)` يكتب الرقم بخانتين عشريتين.
- `${...}` داخل النص تضع قيمة **تعبير** كامل، أما `$name` فلمتغير واحد.

## مثال 3: مفتاح ومنزلق

`Switch` له الخاصية `checked`، و`MSlider` له `value` و`minimum` و`maximum`:

<!-- test: {"controls": {"sldSize": {"Minimum": 10, "Maximum": 40, "Value": 16}}, "do": ["swBold.checked = true", "swBold_Changed(const RadEvent(Value: true))", "sldSize.value = 30", "sldSize_Changed()"], "expect": {"lblPreview.text": "حجم 30 - عريض"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    update();
  }

  void swBold_Changed(RadEvent e) {
    print('عريض؟ ${e.Value}');
    update();
  }

  void sldSize_Changed() {
    update();
  }

  void update() {
    final size = sldSize.value.round();
    final style = swBold.checked ? 'عريض' : 'عادي';
    lblPreview.text = 'حجم $size - $style';
    lblPreview.fontSize = size.toDouble();
    lblPreview.refresh();
  }
}
```

```text output
عريض؟ true
```

- `condition ? a : b` **العامل الشرطي**: إذا كان الشرط صحيحًا تكون القيمة `a`، وإلا `b`.
- `sldSize.value` رقم عشري (`double`)، و`.round()` تقرّبه لأقرب عدد صحيح.

## أخطاء شائعة

- **تعريف `count` داخل الدالة**: يرجع صفرًا مع كل ضغطة. ضعه داخل الفئة وخارج الدوال.
- **`double.parse` بدل `tryParse`**: لو كتب المستخدم حرفًا يتوقف التطبيق بخطأ `FormatException`.
- **نسيان القوسين** عند استدعاء دالة: `show;` لا تفعل شيئًا، والصحيح `show();`.

## تمرين

حوّل درجة الحرارة من مئوية إلى فهرنهايت عندما يضغط المستخدم **Enter** في الحقل `txtC` (الحدث `Submitted`). المعادلة: `f = c * 9 / 5 + 32`. اكتب الناتج في `lblF` بالشكل `F = 212.0`، وإذا لم يكن المدخل رقمًا اكتب `خطأ`.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void txtC_Submitted(RadEvent e) {
    // استخدم double.tryParse(e.Text)
  }
}
```

<!-- test: {"do": ["txtC_Submitted(const RadEvent(Text: 'x'))", "txtC_Submitted(const RadEvent(Text: '100'))"], "expect": {"lblF.text": "F = 212.0"}} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void txtC_Submitted(RadEvent e) {
    final c = double.tryParse(e.Text);
    if (c == null) {
      lblF.text = 'خطأ';
    } else {
      lblF.text = 'F = ${c * 9 / 5 + 32}';
    }
    print(lblF.text);
  }
}
```

```text output
خطأ
F = 212.0
```

## اختبر نفسك

```quiz
{"question": "أي حدث يقع مع كل حرف يكتبه المستخدم في MTextField؟", "choices": ["Submitted", "Changed", "Click", "Load"], "answer": 1, "explanation": "Changed مع كل تغيير، و Submitted عند الضغط على Enter أو Done."}
```

```quiz
{"question": "ماذا ترجع `double.tryParse('abc')`؟", "choices": ["0", "null", "خطأ يوقف التطبيق", "abc"], "answer": 1, "explanation": "tryParse ترجع null بدل أن تتوقف، فتفحصها بـ if (x == null)."}
```

```quiz
{"question": "أين تعرّف متغيرًا يحتفظ بقيمته بين ضغطات الزر؟", "choices": ["داخل دالة الحدث", "داخل الفئة وخارج الدوال", "في ملف _designer.dart", "في pubspec.yaml"], "answer": 1, "explanation": "متغير الفئة (field) يعيش ما دامت الشاشة مفتوحة."}
```

```quiz
{"question": "ماذا تحمل `e.Value` في حدث Changed لأداة Switch؟", "choices": ["نص المفتاح", "true أو false", "رقم الصف", "اسم الأداة"], "answer": 1, "explanation": "قيمة المفتاح: تشغيل (true) أو إيقاف (false)."}
```

## الخلاصة

- نقرة مزدوجة على الأداة تفتح حدثها الافتراضي، وقائمة **Events** في الخصائص تفتح الباقي.
- `RadEvent e` يحمل `e.Text` و `e.Value` و `e.Index` و `e.Action`.
- `double.tryParse` و `int.tryParse` يقرآن الأرقام بأمان، و`toStringAsFixed` ينسّقها.
