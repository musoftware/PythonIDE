# الدرس 1: ما هو Flutter؟ وتجهيز الأدوات

**في هذا الدرس ستتعرف على:**

- ما هو **Flutter** ولماذا تستخدمه RAD IDE لتطبيقات الموبايل.
- كيف تصنع RAD IDE تطبيق موبايل بنفس طريقة فيجوال بيسك: نموذج (شاشة) + أدوات + أحداث.
- البرامج التي تحتاجها على جهازك، وكيف تتأكد أنها تعمل.

## تطبيق واحد لكل الأجهزة

**Flutter** مكتبة مجانية من Google تكتب بها تطبيقًا **مرة واحدة** بلغة **Dart**، ثم تشغّله على:

| المنصة | كيف يعمل التطبيق |
|---|---|
| Android | ملف `APK` أو `App Bundle` يُثبَّت على الهاتف أو يُرفع إلى Google Play |
| Windows | برنامج `.exe` عادي |
| الويب | موقع يعمل في المتصفح (Chrome أو Edge) |
| iOS و macOS | تحتاج جهاز Mac للبناء |

> **تشبيه:** Flutter مثل مطبخ مركزي يطبخ وجبة واحدة ثم يغلّفها في علب مختلفة: علبة للهاتف، وعلبة لويندوز، وعلبة للمتصفح. أنت تطبخ مرة واحدة فقط.

## كيف تفكر RAD IDE في تطبيق الموبايل؟

لو جرّبت دورة BASIC، فأنت تعرف الفكرة مسبقًا:

| في فيجوال بيسك | في تطبيق Flutter داخل RAD IDE |
|---|---|
| **النموذج** (Form) | **الشاشة** (Screen)، وتُرسم داخل إطار هاتف |
| **الأداة** أو عنصر التحكم: `Button` و `TextBox` و `Label` | نفس الأدوات، إضافة إلى أدوات الموبايل: `MTextField` و `MListView` و `AppBar` و `Switch` ... |
| **الحدث** `Command1_Click` | الحدث `btnHello_Click()` |
| `MsgBox "مرحبًا"` | `MsgBox('مرحبًا');` |
| `Text1.Text` | `txtName.text` |

أنت ترسم الشاشة بالفأرة في **المصمم**، وتنقر نقرًا مزدوجًا على زر فيفتح لك الـ IDE **دالة الحدث** لتكتب فيها الكود. خلف الكواليس تكتب RAD IDE كود Flutter الحقيقي (ملفات `.dart`) وتشغّله بالأداة `flutter`.

## لغة Dart في سطور

ستكتب الكود بلغة **Dart**. هي قريبة جدًا من C# و Java و JavaScript. هذه أهم الأشياء التي ستراها في الأمثلة:

```dart
// تعليق من سطر واحد
var count = 0;                      // متغير، ونوعه يُستنتج تلقائيًا (int)
final name = 'سارة';                // متغير لا تتغير قيمته بعد إعطائه أول قيمة
String greeting = 'Hello, $name!';  // $name يضع قيمة المتغير داخل النص
if (count > 3) {
  print('كبير');                    // print يكتب في نافذة المخرجات
}
for (var i = 1; i <= 3; i++) {      // حلقة تكرار
  print(i);
}
```

- كل **تعليمة** تنتهي بفاصلة منقوطة `;`.
- النصوص بين علامتي تنصيص مفردتين `'...'`، و`$name` أو `${a + b}` تضع قيمة داخل النص.
- اللغة **حساسة لحالة الأحرف**: `txtName` غير `TxtName`.

## ما الذي تحتاجه على جهازك؟

1. **Flutter SDK**: نزّله من الموقع `flutter.dev` وفك ضغطه في مجلد مثل `C:\flutter`. تبحث RAD IDE عن `flutter` في متغير `PATH` أولًا، ثم في المجلدات المعتادة مثل `C:\flutter\bin` و `C:\src\flutter\bin`.
2. **Android SDK** (اختياري، للهاتف والمحاكي): يأتي مع **Android Studio**. تجده RAD IDE في `%LOCALAPPDATA%\Android\Sdk` أو من متغير `ANDROID_HOME`.
3. **Visual Studio** مع مكوّن "Desktop development with C++" (اختياري، لتشغيل التطبيق كبرنامج Windows).
4. متصفح **Chrome** أو **Edge** (اختياري، لتشغيله كموقع ويب).

بعد التثبيت افتح نافذة أوامر واكتب:

```text
flutter doctor
```

سترى قائمة فيها علامة صح أمام كل جزء جاهز. لا تقلق من العلامات الحمراء أمام الأجزاء التي لا تحتاجها (مثلًا Xcode على ويندوز).

> **ملحوظة:** في المرة الأولى التي تشغّل فيها مشروعًا على منصة جديدة، تنشئ RAD IDE مجلد تلك المنصة (`android` أو `windows` أو `web`) تلقائيًا بالأمر `flutter create`. لذلك تأخذ أول مرة وقتًا أطول.

## جرّب الآن

هذا أصغر تطبيق: شاشة فيها عنوان (`Label`) اسمه `lblHello`. عند تحميل الشاشة يكتب الحدث `MainScreen_Load` فيها نصًّا، ويطبع سطرًا في نافذة المخرجات. اضغط «جرّبه» لتنشئ RAD IDE المشروع وتشغّله، أو «تحقق» لتشغّله في اختبار تلقائي بلا نافذة.

<!-- test: {"expect": {"lblHello.text": "أهلًا بك في Flutter!"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    lblHello.text = 'أهلًا بك في Flutter!';
    print('تم تحميل الشاشة');
  }
}
```

```text output
تم تحميل الشاشة
```

لا تهتم الآن بالأسطر الأولى (`import` و `part`)، فالـ IDE يكتبها لك في كل شاشة جديدة. سنشرحها في الدرس القادم.

## أخطاء شائعة

- **"Flutter SDK not found"**: لم تجد RAD IDE الأداة `flutter`. أضف المجلد `C:\flutter\bin` إلى `PATH` ثم أعد تشغيل الـ IDE.
- **أول تشغيل بطيء جدًا**: طبيعي. Flutter ينزّل ملفات ويبني المنصة أول مرة فقط.
- **نسيان الفاصلة المنقوطة** في آخر التعليمة: ستظهر رسالة مثل `Expected ';' after this.`

## اختبر نفسك

```quiz
{"question": "بأي لغة تكتب كود تطبيقات Flutter؟", "choices": ["Java", "Dart", "Python", "BASIC"], "answer": 1, "explanation": "Flutter يستخدم لغة Dart، وهي قريبة من C# و Java."}
```

```quiz
{"question": "ما الذي يقابل «النموذج» (Form) في فيجوال بيسك داخل تطبيق Flutter في RAD IDE؟", "choices": ["الحدث", "الشاشة (Screen)", "المتغير", "المكتبة"], "answer": 1, "explanation": "كل نموذج في مشروع Flutter هو شاشة تُرسم داخل إطار هاتف."}
```

```quiz
{"question": "ماذا يطبع الكود `print('Hello, $name!');` إذا كانت `name` تساوي Ali؟", "choices": ["Hello, $name!", "Hello, Ali!", "Hello, name!", "خطأ"], "answer": 1, "explanation": "الرمز $ داخل النص يضع قيمة المتغير مكانه."}
```

```quiz
{"question": "أي أمر يفحص أن Flutter وأدواته مثبتة بشكل صحيح؟", "choices": ["flutter run", "flutter doctor", "flutter build", "flutter clean"], "answer": 1, "explanation": "flutter doctor يعرض قائمة بكل جزء جاهز أو ناقص."}
```

## الخلاصة

- Flutter يصنع تطبيقًا واحدًا لـ Android و Windows والويب، بلغة Dart.
- في RAD IDE: الشاشة = النموذج، والأدوات تُرسم بالفأرة، والكود في دوال أحداث مثل `btnHello_Click()`.
- تحتاج Flutter SDK، و Android SDK للهاتف والمحاكي، و `flutter doctor` يتأكد من كل شيء.
