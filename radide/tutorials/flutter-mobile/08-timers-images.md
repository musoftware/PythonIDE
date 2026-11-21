# الدرس 8: المؤقت والصور وصفحات الويب

**في هذا الدرس ستتعلم:**

- استخدام أداة `Timer` لتنفيذ كود كل فترة زمنية (ساعة إيقاف، عدّ تنازلي).
- عرض الصور بأداة `MImage`، من ملفات المشروع أو من الإنترنت.
- عرض صفحة ويب داخل التطبيق بأداة `MWebView`.

## أداة Timer

`Timer` أداة **لا تظهر** للمستخدم. ضعها على الشاشة من **Toolbox** فتظهر أسفل المصمم (مثل فيجوال بيسك). خصائصها:

| الخاصية أو الدالة | معناها |
|---|---|
| `Interval` | الفترة بالملّي ثانية: `1000` = ثانية واحدة |
| `Enabled` | هل يبدأ المؤقت وحده عند فتح الشاشة؟ |
| `tmrClock.start()` و `tmrClock.stop()` | تشغيل وإيقاف من الكود |
| `tmrClock.enabled` | قراءة الحالة أو تغييرها |
| `tmrClock.interval` | تغيير الفترة من الكود (ثم `start()` لتطبيقها) |
| الحدث `tmrClock_Tick()` | يحدث كل `Interval` ملّي ثانية |

> **تشبيه:** المؤقت مثل منبّه يرن كل ثانية. في كل رنّة يُنفَّذ الحدث `Tick`، ولا يتوقف حتى تطفئه بـ `stop()`.

## مثال: عدّ تنازلي

<!-- test: {"controls": {"tmrDown": {"Interval": 1000}}, "do": ["btnStart_Click()", "@wait:3100"], "expect": {"lblTime.text": "0", "btnStart.enabled": "true"}, "toast": ["انتهى الوقت!"]} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  int left = 0;

  void btnStart_Click() {
    left = 3;
    lblTime.text = '$left';
    btnStart.enabled = false;
    tmrDown.start();
  }

  void tmrDown_Tick() {
    left--;
    lblTime.text = '$left';
    print('باقي $left');
    if (left == 0) {
      tmrDown.stop();
      btnStart.enabled = true;
      Toast('انتهى الوقت!');
    }
  }
}
```

```text output
باقي 2
باقي 1
باقي 0
```

- لا تنسَ `stop()` عندما ينتهي العمل، وإلا استمر المؤقت في الرنين.
- أثناء العدّ نعطّل زر البدء لكي لا يضغطه المستخدم مرتين.

## مثال: ساعة إيقاف بكسور الثانية

مؤقت كل 100 ملّي ثانية، وزر واحد يبدأ ويوقف:

<!-- test: {"controls": {"tmrWatch": {"Interval": 100}}, "do": ["btnGo_Click()", "@wait:1250", "btnGo_Click()"], "expect": {"lblWatch.text": "1.4 ث", "btnGo.text": "ابدأ"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  int tenths = 0;

  void MainScreen_Load() {
    btnGo.text = 'ابدأ';
    lblWatch.text = '0.0 ث';
  }

  void btnGo_Click() {
    if (tmrWatch.enabled) {
      tmrWatch.stop();
      btnGo.text = 'ابدأ';
      print('توقف عند ${lblWatch.text}');
    } else {
      tmrWatch.start();
      btnGo.text = 'إيقاف';
    }
  }

  void tmrWatch_Tick() {
    tenths++;
    lblWatch.text = '${(tenths / 10).toStringAsFixed(1)} ث';
  }
}
```

```text output
توقف عند 1.4 ث
```

## الصور: أداة `MImage`

1. ضع `MImage` على الشاشة، واختر في الخاصية `Image` ملف صورة (`.png` أو `.jpg`) من جهازك.
2. ينسخ الـ IDE الصورة إلى مجلد `assets` في المشروع ويسجلها في `pubspec.yaml` تلقائيًا، فتُضمَّن داخل التطبيق.
3. الخاصية `Fit` تحدد كيف تملأ الصورة مربعها: `Cover` (تملأ وتقص الزيادة)، و`Contain` (تظهر كلها)، و`Fill` (تمطّها).

ومن الكود تغيّر الصورة بالخاصية `image`: مسار داخل `assets` أو رابط إنترنت يبدأ بـ `https://`:

<!-- test: {"controls": {"imgPet": {"type": "MImage"}}, "do": ["btnNext_Click()", "btnNext_Click()", "btnNext_Click()"], "expect": {"imgPet.image": "assets/cat.png", "lblCaption.text": "1 / 3"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final pictures = ['assets/cat.png', 'assets/dog.png', 'https://flutter.dev/images/flutter-logo-sharing.png'];
  int i = 0;

  void MainScreen_Load() {
    show();
  }

  void btnNext_Click() {
    i = (i + 1) % pictures.length;     // بعد الأخيرة نرجع إلى الأولى
    show();
  }

  void show() {
    imgPet.image = pictures[i];
    lblCaption.text = '${i + 1} / ${pictures.length}';
    print(imgPet.image);
  }
}
```

```text output
assets/cat.png
assets/dog.png
https://flutter.dev/images/flutter-logo-sharing.png
assets/cat.png
```

- `%` باقي القسمة: `3 % 3` يساوي `0`، فيرجع العدّ إلى البداية.
- إذا لم يوجد ملف الصورة يظهر مكانها مربع رمادي فيه علامة، ولا يتوقف التطبيق.

## صفحة ويب داخل التطبيق: `MWebView`

ضع `MWebView` واكتب الرابط في الخاصية `Url`. من الكود: `webNews.url = 'https://example.com';`. تضيف RAD IDE المكتبة اللازمة (`webview_flutter`) إلى `pubspec.yaml` تلقائيًا عند أول استخدام.

> **ملحوظة:** `MWebView` تعمل على Android و iOS والويب. على Windows تظهر رسالة بدل الصفحة، فجرّبها على هاتف أو محاكي (الدرس القادم).

## أخطاء شائعة

- **المؤقت لا يعمل**: نسيت `start()` والخاصية `Enabled` تساوي `False`.
- **المؤقت أسرع مما تتوقع**: `Interval` بالملّي ثانية، و`1` ليست ثانية بل جزء من ألف منها.
- **صورة لا تظهر بعد البناء**: كتبت مسارًا من جهازك مثل `C:\pics\cat.png` في الكود. استخدم الخاصية `Image` في المصمم لتنسخ الصورة إلى `assets` ثم اكتب `assets/cat.png`.

## تمرين

إشارة مرور: مؤقت `tmrLight` كل ثانية. عند الضغط على `btnRun` يبدأ، ومع كل `Tick` يتغير النص في `lblLight` بالترتيب: `أحمر` ثم `أصفر` ثم `أخضر` ثم يعود إلى `أحمر`. اطبع اللون في كل مرة.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final colors = ['أحمر', 'أصفر', 'أخضر'];
  int i = 0;

  void btnRun_Click() {
  }

  void tmrLight_Tick() {
  }
}
```

<!-- test: {"controls": {"tmrLight": {"Interval": 1000}}, "do": ["btnRun_Click()", "@wait:4050", "tmrLight.stop()"], "expect": {"lblLight.text": "أصفر"}} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final colors = ['أحمر', 'أصفر', 'أخضر'];
  int i = 0;

  void btnRun_Click() {
    lblLight.text = colors[i];
    tmrLight.start();
  }

  void tmrLight_Tick() {
    i = (i + 1) % colors.length;
    lblLight.text = colors[i];
    print(colors[i]);
  }
}
```

```text output
أصفر
أخضر
أحمر
أصفر
```

لاحظ أن الاختبار ينتظر 4 ثوانٍ فيرنّ المؤقت 4 مرات: أصفر، أخضر، أحمر، ثم أصفر من جديد. هذه قوة `%`: لا نحتاج `if` لنرجع إلى أول لون.

## اختبر نفسك

```quiz
{"question": "كم مرة يحدث Tick خلال 3 ثوانٍ إذا كان Interval = 500؟", "choices": ["3", "6", "500", "1"], "answer": 1, "explanation": "500 ملّي ثانية = نصف ثانية، أي مرتان كل ثانية."}
```

```quiz
{"question": "أين يضع الـ IDE الصورة التي تختارها في خاصية Image؟", "choices": ["في lib", "في مجلد assets ويسجلها في pubspec.yaml", "في build", "لا ينسخها"], "answer": 1, "explanation": "الصور تُنسخ إلى assets وتُسجَّل لكي تُضمَّن داخل التطبيق."}
```

```quiz
{"question": "ما ناتج `(4 + 1) % 5`؟", "choices": ["5", "0", "1", "4"], "answer": 1, "explanation": "باقي قسمة 5 على 5 صفر، وهكذا نرجع إلى أول عنصر."}
```

## الخلاصة

- `Timer` له `Interval` بالملّي ثانية، و`start()` و `stop()`، والحدث `Tick`.
- `MImage` يعرض صورة من `assets` أو من رابط، و`Fit` يحدد طريقة الملء.
- `MWebView` يعرض صفحة ويب، ويعمل على الهاتف والويب.
