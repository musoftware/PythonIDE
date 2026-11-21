# الدرس 5: الرسائل والأسئلة: MsgBox و Toast و InputBox و Confirm

**في هذا الدرس ستتعلم:**

- عرض رسالة في نافذة بـ `MsgBox`، ورسالة قصيرة أسفل الشاشة بـ `Toast`.
- سؤال المستخدم عن نص بـ `InputBox`، وعن «نعم أو لا» بـ `Confirm`.
- الكلمتين `async` و `await`: كيف ينتظر الكود إجابة المستخدم.

## أربع طرق للكلام مع المستخدم

| الدالة | الشكل | متى تستخدمها؟ |
|---|---|---|
| `MsgBox('نص', 'عنوان')` | نافذة في وسط الشاشة وزر **OK** | معلومة مهمة يجب أن يقرأها |
| `Toast('نص')` | شريط صغير أسفل الشاشة يختفي وحده | تأكيد سريع: «تم الحفظ» |
| `await InputBox('سؤال')` | نافذة فيها حقل كتابة و **OK** و **Cancel** | تحتاج نصًّا من المستخدم |
| `await Confirm('سؤال')` | نافذة فيها **Yes** و **No** | قبل عمل خطير مثل الحذف |

> **تشبيه:** `Toast` مثل إشعار صغير يمر أمامك، و`MsgBox` مثل موظف يوقفك ليقول لك شيئًا ولا يتركك حتى تقول «حسنًا».

## MsgBox و Toast

<!-- test: {"do": ["btnSave_Click()", "btnAbout_Click()"], "msgbox": ["RAD IDE + Flutter\nالإصدار 1.0"], "toast": ["تم الحفظ"]} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnSave_Click() {
    Toast('تم الحفظ');
  }

  void btnAbout_Click() {
    MsgBox('RAD IDE + Flutter\nالإصدار 1.0', 'حول التطبيق');
  }
}
```

- الرمز `\n` داخل النص ينزل سطرًا جديدًا في الرسالة.
- المعامل الثاني لـ `MsgBox` (العنوان) اختياري.

## الانتظار: async و await

`InputBox` يفتح نافذة ثم **ينتظر** المستخدم. لو كان الكود لا ينتظر، لأكمل قبل أن يكتب المستخدم شيئًا! لذلك:

1. نكتب `await` قبل الاستدعاء: «انتظر هنا حتى تأتي الإجابة».
2. وأي دالة فيها `await` يجب أن تكون `async`، ونوعها `Future<void>` بدل `void`.

```dart
Future<void> btnName_Click() async {
  final name = await InputBox('ما اسمك؟');
  // هنا وصلت الإجابة
}
```

> **تشبيه:** `await` مثل أن تطلب طعامًا في مطعم وتنتظر على الطاولة. لا تأكل قبل أن يصل الطبق. و`Future` هي «إيصال الطلب»: وعد بأن النتيجة ستأتي لاحقًا.

## InputBox

`InputBox` يرجع **النص** إذا ضغط المستخدم **OK**، أو `null` إذا ضغط **Cancel**. لذلك نوع النتيجة `String?` (علامة `?` معناها: قد تكون `null`):

<!-- test: {"do": ["btnName_Click()", "@input:Ahmed", "btnName_Click()", "@cancel"], "expect": {"lblHello.text": "أهلًا يا Ahmed"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  Future<void> btnName_Click() async {
    final name = await InputBox('ما اسمك؟', 'تعارف');
    if (name == null) {
      print('ألغى المستخدم');
      return;
    }
    lblHello.text = 'أهلًا يا $name';
    print(lblHello.text);
  }
}
```

```text output
أهلًا يا Ahmed
ألغى المستخدم
```

يمكنك أيضًا إعطاء قيمة مبدئية تظهر في الحقل: `await InputBox('الكمية؟', 'طلب', '1')`.

## Confirm

`Confirm` يرجع `true` عند **Yes** و `false` عند **No**. مثال: حذف كل العناصر بعد التأكيد فقط:

<!-- test: {"controls": {"lstItems": {"Items": "شاي;قهوة;عصير"}}, "do": ["btnClear_Click()", "@no", "btnClear_Click()", "@yes"], "expect": {"lstItems.count": "0"}, "toast": ["تم حذف 3 عناصر"]} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  Future<void> btnClear_Click() async {
    final n = lstItems.count;
    if (!await Confirm('حذف $n عناصر؟', 'تأكيد')) {
      print('لم يُحذف شيء');
      return;
    }
    lstItems.clear();
    Toast('تم حذف $n عناصر');
  }
}
```

```text output
لم يُحذف شيء
```

- `!` معناها «ليس»: `!await Confirm(...)` صحيحة إذا كانت الإجابة **No**.

## أخطاء شائعة

- **نسيان `await`**: تصبح `name` من نوع `Future` وليست نصًّا، فيظهر خطأ مثل `The argument type 'Future<String?>' can't be assigned...`.
- **`await` داخل دالة بدون `async`**: خطأ ترجمة `'await' can only be used in 'async' functions`.
- **عدم فحص `null`** بعد `InputBox`: إذا ضغط المستخدم **Cancel** سيظهر في العنوان النص `null`.
- **كثرة `MsgBox`**: تزعج المستخدم. استخدم `Toast` للتأكيدات البسيطة.

## تمرين

اسأل المستخدم بـ `InputBox` عن عمره عند الضغط على `btnAge`. إذا أدخل رقمًا أكبر من أو يساوي 18 اعرض `MsgBox('مرحبًا بك')`، وإذا كان أقل اعرض `MsgBox('عذرًا، للكبار فقط')`، وإذا لم يكن رقمًا اعرض `Toast('أدخل رقمًا')`.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  Future<void> btnAge_Click() async {
    // final text = await InputBox('كم عمرك؟');
    // final age = int.tryParse(text ?? '');
  }
}
```

<!-- test: {"do": ["btnAge_Click()", "@input:20", "btnAge_Click()", "@input:12", "btnAge_Click()", "@input:abc"], "msgbox": ["مرحبًا بك", "عذرًا، للكبار فقط"], "toast": ["أدخل رقمًا"]} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  Future<void> btnAge_Click() async {
    final text = await InputBox('كم عمرك؟');
    final age = int.tryParse(text ?? '');
    if (age == null) {
      Toast('أدخل رقمًا');
    } else if (age >= 18) {
      MsgBox('مرحبًا بك');
    } else {
      MsgBox('عذرًا، للكبار فقط');
    }
  }
}
```

`text ?? ''` معناها: «استخدم `text`، وإذا كانت `null` فاستخدم نصًّا فارغًا».

## اختبر نفسك

```quiz
{"question": "ماذا يرجع InputBox إذا ضغط المستخدم Cancel؟", "choices": ["نصًّا فارغًا", "null", "false", "0"], "answer": 1, "explanation": "Cancel يرجع null، لذلك نفحص if (name == null)."}
```

```quiz
{"question": "دالة فيها await يجب أن تُعلَن بالشكل:", "choices": ["void f()", "Future<void> f() async", "async void f", "await void f()"], "answer": 1, "explanation": "await تحتاج دالة async ترجع Future."}
```

```quiz
{"question": "أفضل طريقة لإخبار المستخدم بأن الحفظ تم بنجاح:", "choices": ["MsgBox", "Toast", "Confirm", "InputBox"], "answer": 1, "explanation": "Toast رسالة سريعة لا توقف المستخدم."}
```

```quiz
{"question": "ما قيمة `x ?? 'بلا اسم'` إذا كانت x تساوي null؟", "choices": ["null", "بلا اسم", "x", "خطأ"], "answer": 1, "explanation": "العامل ?? يعطي القيمة البديلة عندما يكون الطرف الأيسر null."}
```

## الخلاصة

- `MsgBox` نافذة بزر OK، و`Toast` رسالة سريعة أسفل الشاشة.
- `await InputBox(...)` يرجع النص أو `null`، و`await Confirm(...)` يرجع `true` أو `false`.
- `await` يحتاج دالة `async` نوعها `Future<void>`.
