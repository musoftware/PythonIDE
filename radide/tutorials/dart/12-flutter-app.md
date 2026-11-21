# الدرس 12: مشروع Flutter: محوّل العملات بمصمم الشاشات

مشروعنا الأخير تطبيق موبايل حقيقي: **محوّل عملات** يكتب فيه المستخدم مبلغًا بالجنيه المصري، ويختار العملة، فيظهر المبلغ المحوّل، ويُحفظ كل تحويل في **سجل**. سنستخدم فيه الأصناف والقوائم والقواميس والأمان من `null`، كلها معًا.

> **تشبيه:** التطبيق مثل **شباك الصرافة** في البنك: تعطيه المبلغ وتقول «بالدولار من فضلك»، فيحسب ويعطيك الإيصال، ويحتفظ بنسخة منه في دفتره.

## 1) المنطق أولًا بلغة Dart الصرفة

القاعدة نفسها التي اتبعناها طوال الدورة: نجرّب المنطق في الكونسول قبل الواجهة.

```dart run
class Currency {
  final String code;
  final String name;
  final double rate;       // كم جنيهًا تساوي وحدة واحدة
  const Currency(this.code, this.name, this.rate);

  double fromEgp(double egp) => egp / rate;
}

const currencies = [
  Currency('USD', 'دولار أمريكي', 50),
  Currency('EUR', 'يورو', 54),
  Currency('SAR', 'ريال سعودي', 13.3),
];

String convert(String amountText, int index) {
  final amount = double.tryParse(amountText.trim());
  if (amount == null || amount <= 0) return 'مبلغ غير صحيح';
  final c = currencies[index];
  return '${amount.toStringAsFixed(2)} جنيه = ${c.fromEgp(amount).toStringAsFixed(2)} ${c.code}';
}

void main() {
  print(convert('1000', 0));
  print(convert(' 270 ', 1));
  print(convert('abc', 2));
  print(convert('-5', 0));
}
```

```text output
1000.00 جنيه = 20.00 USD
270.00 جنيه = 5.00 EUR
مبلغ غير صحيح
مبلغ غير صحيح
```

> **ملاحظة:** الأسعار هنا للتعلم فقط وليست أسعار الصرف الحقيقية. في تطبيق حقيقي تجلبها من خدمة على الإنترنت بـ `async` و`await` (الدرس 8).

## 2) تصميم الشاشة

1. **File > New Project...** ثم **Mobile > Flutter App** باسم `CurrencyApp`.
2. احذف أدوات القالب من الشاشة، وارسم من **Toolbox** بالترتيب من أعلى لأسفل:

| الأداة | Name | خصائص |
|---|---|---|
| `Label` | `lblTitle` | `Text` = `محوّل العملات`، خط كبير |
| `MTextField` | `txtAmount` | `Hint` = `المبلغ بالجنيه` |
| `Button` | `btnUsd` | `Text` = `دولار` |
| `Button` | `btnEur` | `Text` = `يورو` |
| `Button` | `btnSar` | `Text` = `ريال` |
| `Label` | `lblResult` | النتيجة |
| `MListView` | `lstHistory` | سجل التحويلات |
| `Button` | `btnClear` | `Text` = `امسح السجل` |

## 3) الكود

نضع الصنف والأسعار في ملف وحدة منفصل `lib/currency.dart`، وكود الشاشة في `lib/main_screen.dart`:

<!-- test: {"controls": {"lblTitle": {"Text": "محوّل العملات"}, "txtAmount": {"Text": ""}, "btnUsd": {"Text": "دولار"}, "btnEur": {"Text": "يورو"}, "btnSar": {"Text": "ريال"}, "lblResult": {"Text": ""}, "lstHistory": {"ItemTemplate": "title|subtitle"}, "btnClear": {"Text": "امسح السجل"}}, "do": ["btnUsd_Click()", "txtAmount.text = '1000'", "btnUsd_Click()", "txtAmount.text = '540'", "btnEur_Click()", "btnClear_Click()", "@yes", "txtAmount.text = '133'", "btnSar_Click()"], "expect": {"lblResult.text": "133.00 جنيه = 10.00 SAR", "lstHistory.count": "1", "lstHistory.field(0, 0)": "10.00 SAR"}, "toast": ["اكتب مبلغًا صحيحًا"]} -->
```flutter run
// #file: lib/currency.dart
class Currency {
  final String code;
  final String name;
  final double rate;
  const Currency(this.code, this.name, this.rate);

  double fromEgp(double egp) => egp / rate;
}

const currencies = {
  'USD': Currency('USD', 'دولار أمريكي', 50),
  'EUR': Currency('EUR', 'يورو', 54),
  'SAR': Currency('SAR', 'ريال سعودي', 13.3),
};

// #file: lib/main_screen.dart
import 'package:flutter/material.dart';

import 'currency.dart';
import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  int conversions = 0;

  void MainScreen_Load() {
    lblResult.text = 'اكتب المبلغ ثم اختر العملة';
  }

  void convertTo(String code) {
    final amount = double.tryParse(txtAmount.text.trim());
    if (amount == null || amount <= 0) {
      Toast('اكتب مبلغًا صحيحًا');
      return;
    }
    final c = currencies[code]!;
    final result = c.fromEgp(amount).toStringAsFixed(2);
    lblResult.text = '${amount.toStringAsFixed(2)} جنيه = $result ${c.code}';
    lstHistory.addItem('$result ${c.code}|${amount.toStringAsFixed(0)} جنيه إلى ${c.name}');
    conversions++;
    print('تحويل رقم $conversions: $result ${c.code}');
  }

  void btnUsd_Click() => convertTo('USD');
  void btnEur_Click() => convertTo('EUR');
  void btnSar_Click() => convertTo('SAR');

  void btnClear_Click() async {
    if (await Confirm('هل تريد مسح السجل؟')) {
      lstHistory.clear();
      print('مُسح السجل');
    }
  }
}
```

```text output
تحويل رقم 1: 20.00 USD
تحويل رقم 2: 10.00 EUR
مُسح السجل
تحويل رقم 3: 10.00 SAR
```

اختر الجهاز من **Device:** ثم اضغط **F5**. جرّب مبلغًا فارغًا، ثم `1000` و**دولار**، ثم امسح السجل.

## 4) ماذا استخدمنا من الدورة؟

| في المشروع | الدرس |
|---|---|
| `class Currency` بباني `const` وخصائص `final` | 7 |
| `const currencies = {...}` قاموس من الكائنات | 5 |
| `double.tryParse` و`amount == null` و`currencies[code]!` | 2 و6 |
| `toStringAsFixed(2)` واستيفاء النص `${...}` | 2 و6 |
| `void btnUsd_Click() => convertTo('USD');` دالة سهمية | 4 |
| `async` و`await Confirm(...)` | 8 |
| `// #file:` كود موزع على وحدتين، و`import 'currency.dart';` | 10 |
| معالجات الأحداث والمتغير `conversions` داخل الصنف | 9 و11 |

- `Confirm('...')` تعرض سؤالًا بزرين (نعم / لا) وتُرجع `Future<bool>`، لذلك نكتب `await` ونجعل الحدث `async`.
- `currencies[code]!`: القاموس يُرجع `Currency?`، والعلامة `!` تقول إننا متأكدون أن المفتاح موجود (نحن من كتب الأكواد الثلاثة).
- `lstHistory.addItem('عنوان|عنوان فرعي')`: العلامة `|` تفصل سطري الصف في القائمة.

## 5) خطوتك التالية

- أضف عملة جديدة (مثل `KWD`) بسطر واحد في القاموس وزر جديد.
- اجعل الضغط على صف في السجل (`lstHistory_Tap`) يعرض تفاصيله في `MsgBox`.
- ابنِ التطبيق لهاتفك: دليل **«دليل تطبيقات الموبايل بـ Flutter في RAD IDE»** يشرح الأجهزة و**Hot Reload** والبناء (APK) بالتفصيل، ويشرح أيضًا **Flutter Designer** لتصميم الشاشات بودجات Flutter الأصلية.

## تمارين

### التمرين 1

(بلغة Dart الصرفة) اكتب دالة `String bestDeal(Map<String, double> offers)` تُرجع اسم المحل صاحب أقل سعر، بالشكل `أرخص سعر: <المحل> (<السعر>)`. استخدم `entries` و`reduce`.

```dart exercise
String bestDeal(Map<String, double> offers) {
  return '';
}

void main() {
  print(bestDeal({'محل النور': 120.5, 'سوق الخير': 99.0, 'البركة': 105.0}));
}
```

```dart solution
String bestDeal(Map<String, double> offers) {
  final best = offers.entries.reduce((a, b) => a.value <= b.value ? a : b);
  return 'أرخص سعر: ${best.key} (${best.value})';
}

void main() {
  print(bestDeal({'محل النور': 120.5, 'سوق الخير': 99.0, 'البركة': 105.0}));
}
```

```text output
أرخص سعر: سوق الخير (99.0)
```

`reduce` تقارن العناصر اثنين اثنين وتحتفظ بواحد في كل مرة، حتى يبقى عنصر واحد.

### التمرين 2

شاشة فيها `txtKm` و`btnConvert` و`lblMiles`: حوّل الكيلومترات إلى أميال (الميل = 1.609 كم) بخانتين عشريتين: `10 كم = 6.22 ميل`. وإذا كان المدخل غير صحيح اعرض `Toast('رقم غير صحيح')`.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnConvert_Click() {
  }
}
```

<!-- test: {"controls": {"txtKm": {"Text": ""}, "btnConvert": {"Text": "حوّل"}, "lblMiles": {"Text": ""}}, "do": ["txtKm.text = 'x'", "btnConvert_Click()", "txtKm.text = '10'", "btnConvert_Click()"], "expect": {"lblMiles.text": "10 كم = 6.22 ميل"}, "toast": ["رقم غير صحيح"]} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnConvert_Click() {
    final km = double.tryParse(txtKm.text.trim());
    if (km == null) {
      Toast('رقم غير صحيح');
      return;
    }
    final miles = (km / 1.609).toStringAsFixed(2);
    lblMiles.text = '${txtKm.text.trim()} كم = $miles ميل';
  }
}
```

## اختبر نفسك

```quiz
{"question": "لماذا جعلنا الحدث btnClear_Click دالة async؟", "choices": ["لأن كل الأحداث يجب أن تكون async", "لأن Confirm تُرجع Future<bool> ونحتاج await لانتظار إجابة المستخدم", "لتسريع المسح", "لأن القائمة فارغة"], "answer": 1, "explanation": "await لا تُستخدم إلا داخل دالة async."}
```

```quiz
{"question": "لماذا نجرّب منطق التحويل في الكونسول أولًا؟", "choices": ["لأن Flutter لا تقبل الدوال", "لأنه أسرع وأسهل في اكتشاف الأخطاء، ثم نربطه بالواجهة وهو سليم", "لأن الكونسول أجمل", "لا فائدة من ذلك"], "answer": 1, "explanation": "فصل المنطق عن الواجهة يجعل اختباره وإصلاحه أسهل."}
```

## الخلاصة

- بنيت تطبيق موبايل كاملًا يجمع كل ما تعلمته في Dart: الأصناف والقواميس والأمان من `null` والدوال والبرمجة غير المتزامنة.
- مصمم الشاشات يكتب كود الواجهة، وأنت تكتب الأحداث في `lib/main_screen.dart` ووحداتك في `lib/`.
- مبروك! أنهيت دورة Dart. تابع **«دليل تطبيقات الموبايل بـ Flutter في RAD IDE»** لتتعمق في Flutter.
