# الدرس 2: المتغيرات والأنواع والإدخال

البرامج تحتاج أن **تتذكر** أشياء: اسم المستخدم، السعر، عدد المحاولات. نحفظ هذه القيم في **متغيرات**.

> **تشبيه:** المتغير مثل **علبة عليها ملصق**: الملصق هو اسم المتغير، وما بداخلها هو القيمة. وفي Dart لكل علبة **نوع**: علبة للأرقام لا تضع فيها نصًا، مثل علبة البيض التي لا يدخلها البطيخ!

## تعريف المتغيرات

```dart run
void main() {
  String name = 'منى';
  int age = 21;
  double height = 1.65;
  bool isStudent = true;

  print(name);
  print(age);
  print(height);
  print(isStudent);
  print('$name عمرها $age سنة');
}
```

```text output
منى
21
1.65
true
منى عمرها 21 سنة
```

| النوع | معناه | أمثلة |
|---|---|---|
| `int` | عدد صحيح | `5`، `-12`، `2026` |
| `double` | عدد عشري | `3.14`، `0.5` |
| `num` | أي رقم (صحيح أو عشري) | |
| `String` | نص | `'سلام'` |
| `bool` | قيمة منطقية | `true` / `false` |

- `$name` داخل النص تضع قيمة المتغير، و`${...}` لتعبير كامل مثل `${age + 1}`.
- أسماء المتغيرات تبدأ بحرف صغير، وكل كلمة بعدها بحرف كبير: `isStudent`، `totalPrice`. هذا يسمى **camelCase**.

## var و final و const

```dart run
void main() {
  var city = 'الإسكندرية';     // Dart تستنتج النوع: String
  city = 'أسوان';               // يمكن تغييرها
  print(city);

  final birthYear = 2005;       // تُحدد مرة واحدة ولا تتغير
  const pi = 3.14159;           // ثابت معروف قبل التشغيل
  print(2026 - birthYear);
  print(pi * 2);
  print(city.runtimeType);
}
```

```text output
أسوان
21
6.28318
String
```

| الكلمة | متى تستخدمها؟ |
|---|---|
| `var` | متغير ستتغير قيمته، والنوع يُستنتج من أول قيمة |
| `final` | قيمة تُحدد **مرة واحدة** (ولو أثناء التشغيل) ثم لا تتغير |
| `const` | ثابت معروف وقت كتابة الكود، مثل `pi` |

> **نصيحة المحترفين:** استخدم `final` كلما استطعت. هكذا تمنع نفسك من تغيير قيمة بالخطأ. وستراها في كل مكان في كود Flutter.

`var` لا تعني «أي نوع»: بعد `var city = 'الإسكندرية';` صار `city` نصًا للأبد، و`city = 5;` خطأ.

## التحويل بين الأنواع

```dart run
void main() {
  int a = int.parse('42');
  double b = double.parse('2.5');
  String c = 100.toString();
  print(a + 1);
  print(b * 2);
  print(c + '!');
  print(7.9.toInt());
  print(7.5.round());
  print(10.toDouble());
  print(3.14159.toStringAsFixed(2));
  print(int.tryParse('abc'));
}
```

```text output
43
5.0
100!
7
8
10.0
3.14
null
```

- `int.parse` و`double.parse` تحوّل النص إلى رقم، وتتوقف بخطأ إذا لم يكن النص رقمًا.
- `int.tryParse` أكثر أمانًا: تُرجع `null` (لا شيء) بدل الخطأ. سنتعلم التعامل مع `null` في الدرس 6.
- `.toStringAsFixed(2)` تكتب الرقم بخانتين عشريتين، ممتازة للأسعار.

## قراءة إدخال المستخدم

نقرأ سطرًا من لوحة المفاتيح بـ `stdin.readLineSync()` من المكتبة `dart:io`:

```dart run
import 'dart:convert';
import 'dart:io';

void main() {
  stdout.write('ما اسمك؟ ');
  final name = stdin.readLineSync(encoding: utf8) ?? '';
  stdout.write('كم عمرك؟ ');
  final age = int.parse(stdin.readLineSync() ?? '0');
  print('');
  print('أهلًا يا $name!');
  print('بعد 10 سنوات سيكون عمرك ${age + 10}');
}
```

```text input
كريم
19
```

```text output
ما اسمك؟ كم عمرك؟ 
أهلًا يا كريم!
بعد 10 سنوات سيكون عمرك 29
```

- `import 'dart:io';` تجلب أدوات الإدخال والإخراج، و`dart:convert` تجلب `utf8` لقراءة الحروف العربية صحيحة.
- `stdout.write` تطبع **بدون** سطر جديد، فيكتب المستخدم بجانب السؤال.
- `?? ''` تعني: «إذا لم يكتب المستخدم شيئًا (`null`) فاستخدم نصًا فارغًا». شرحها في الدرس 6.
- عند الضغط على **«▶ جرّبه»** تكتب أنت الإدخال في نافذة **Output**. أما في هذا المثال فالمدخلات مكتوبة في مربع «الإدخال» لكي يُفحص الناتج.

## أخطاء شائعة

- **وضع نص في متغير رقمي:**

<!-- compile-error -->
```dart
void main() {
  int age = '21';
}
```

تقول Dart: `A value of type 'String' can't be assigned to a variable of type 'int'.` حوّل بـ `int.parse('21')`.

- **تغيير قيمة `final`:** `final x = 1; x = 2;` خطأ قبل التشغيل.
- **جمع نص ورقم:** `'العمر: ' + 21` خطأ في Dart. استخدم `'العمر: $age'` أو `21.toString()`.

## تمارين

### التمرين 1

اقرأ طول المستطيل وعرضه (عددين صحيحين في سطرين)، واطبع المساحة والمحيط:

```dart exercise
import 'dart:io';

void main() {
}
```

```dart solution
import 'dart:io';

void main() {
  final width = int.parse(stdin.readLineSync()!);
  final height = int.parse(stdin.readLineSync()!);
  print('المساحة = ${width * height}');
  print('المحيط = ${2 * (width + height)}');
}
```

```text input
5
3
```

```text output
المساحة = 15
المحيط = 16
```

العلامة `!` بعد `readLineSync()` تعني «أنا متأكد أنها ليست `null`». سنعود إليها في الدرس 6.

### التمرين 2

اقرأ سعر منتج (عدد عشري) واطبع السعر بعد ضريبة 14% بخانتين عشريتين: `الإجمالي: 114.00`.

```dart exercise
import 'dart:io';

void main() {
}
```

```dart solution
import 'dart:io';

void main() {
  final price = double.parse(stdin.readLineSync()!);
  final total = price * 1.14;
  print('الإجمالي: ${total.toStringAsFixed(2)}');
}
```

```text input
100
```

```text output
الإجمالي: 114.00
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين final وvar؟", "choices": ["لا فرق", "final لا يمكن تغيير قيمتها بعد تحديدها، وvar يمكن", "var للأرقام فقط", "final أسرع في الطباعة"], "answer": 1, "explanation": "final تُحدد مرة واحدة، أما var فمتغير عادي يمكن تغييره (بنفس النوع)."}
```

```quiz
{"question": "ما ناتج int.tryParse('abc')؟", "choices": ["0", "خطأ يوقف البرنامج", "null", "'abc'"], "answer": 2, "explanation": "tryParse تُرجع null إذا لم يكن النص رقمًا، بدل أن توقف البرنامج."}
```

## الخلاصة

- الأنواع الأساسية: `int` و`double` و`String` و`bool`.
- `var` يستنتج النوع، و`final` لقيمة لا تتغير، و`const` لثابت معروف مسبقًا.
- `int.parse` و`double.parse` و`.toString()` و`.toStringAsFixed()` للتحويل.
- `stdin.readLineSync()` لقراءة سطر، مع `import 'dart:io';`.
