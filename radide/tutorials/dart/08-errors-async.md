# الدرس 8: الأخطاء والبرمجة غير المتزامنة (async / await)

في هذا الدرس موضوعان يحتاجهما كل تطبيق حقيقي: **ماذا نفعل عندما يفشل شيء؟** و**كيف ننتظر عملًا بطيئًا** (تحميل من الإنترنت، قراءة ملف) دون أن يتجمد البرنامج؟

## معالجة الأخطاء: `try` و `catch`

```dart run
void main() {
  final inputs = ['42', 'abc', '7'];
  for (final text in inputs) {
    try {
      final n = int.parse(text);
      print('الرقم ${n * 2}');
    } on FormatException {
      print('"$text" ليس رقمًا');
    } finally {
      print('--');
    }
  }
}
```

```text output
الرقم 84
--
"abc" ليس رقمًا
--
الرقم 14
--
```

- الكود الذي قد يفشل يوضع في `try`.
- `on FormatException` تلتقط نوعًا محددًا من الأخطاء، و`catch (e)` تلتقط أي خطأ وتعطيك تفاصيله في `e`.
- `finally` تعمل في كل الأحوال، نجح الكود أو فشل.

> **تشبيه:** `try / catch` مثل **شبكة الأمان تحت لاعب السيرك**: يحاول اللاعب الحركة الصعبة، فإذا سقط التقطته الشبكة، ويكمل العرض بدل أن ينتهي.

## رمي الأخطاء بنفسك: `throw`

```dart run
class InsufficientFunds implements Exception {
  final double needed;
  InsufficientFunds(this.needed);
  @override
  String toString() => 'الرصيد لا يكفي، ينقصك $needed';
}

double withdraw(double balance, double amount) {
  if (amount <= 0) throw ArgumentError('المبلغ يجب أن يكون موجبًا');
  if (amount > balance) throw InsufficientFunds(amount - balance);
  return balance - amount;
}

void main() {
  for (final amount in [50.0, -5.0, 500.0]) {
    try {
      print('الباقي: ${withdraw(100, amount)}');
    } on InsufficientFunds catch (e) {
      print(e);
    } catch (e) {
      print('خطأ: ${e is ArgumentError ? e.message : e}');
    }
  }
}
```

```text output
الباقي: 50.0
خطأ: المبلغ يجب أن يكون موجبًا
الرصيد لا يكفي، ينقصك 400.0
```

- `throw` ترمي خطأ يوقف الدالة فورًا ويصعد إلى أقرب `catch`.
- يمكنك صنع نوع خطأ خاص بك بصنف ينفذ `Exception`.
- ترتيب `on ... catch` مهم: الأكثر تحديدًا أولًا، ثم `catch (e)` العامة.

## لماذا البرمجة غير المتزامنة؟

بعض الأعمال **بطيئة**: تحميل صورة من الإنترنت قد يأخذ ثانيتين. لو انتظر البرنامج وتوقف عن كل شيء، لتجمدت الشاشة ولم يستجب أي زر. الحل: نبدأ العمل البطيء، ونكمل غيره، ثم نعود إليه عندما **يكتمل**.

> **تشبيه:** `Future` مثل **إيصال المطعم**: تطلب البيتزا فتأخذ إيصالًا (وعدًا بأن الطلب سيجهز)، وتجلس تتحدث مع أصدقائك. عندما ينادون رقمك تستلم البيتزا. و`await` تعني: «سأنتظر هنا حتى ينادوا رقمي».

## `Future` و `async` و `await`

```dart run
Future<String> downloadName() async {
  await Future.delayed(Duration(milliseconds: 300));   // نتظاهر بالتحميل
  return 'بيانات المستخدم';
}

Future<void> main() async {
  print('1) بدأ التحميل...');
  final data = await downloadName();
  print('2) وصل: $data');
  print('3) انتهى');
}
```

```text output
1) بدأ التحميل...
2) وصل: بيانات المستخدم
3) انتهى
```

- `Future<String>` نوع «نص سيصل في المستقبل».
- الدالة التي تستخدم `await` يجب أن تُعلم بـ `async`.
- `await` تنتظر الـ Future حتى يكتمل وتُرجع قيمته، دون أن تجمّد البرنامج كله.

## ماذا يحدث بدون `await`؟

```dart run
Future<void> task(String name, int ms) async {
  await Future.delayed(Duration(milliseconds: ms));
  print('انتهت المهمة $name');
}

Future<void> main() async {
  print('البداية');
  task('أ', 200);               // بدون await: لا ننتظرها
  print('الكود يكمل فورًا');
  await task('ب', 50);
  await Future.delayed(Duration(milliseconds: 300));
  print('النهاية');
}
```

```text output
البداية
الكود يكمل فورًا
انتهت المهمة ب
انتهت المهمة أ
النهاية
```

بدأت المهمة «أ» أولًا لكنها انتهت آخرًا، لأنها أبطأ ولم ننتظرها. هذا مفيد لتشغيل أعمال معًا، لكنه مصدر أخطاء إذا نسيت `await` وأنت تحتاج النتيجة.

## تشغيل عدة أعمال معًا و الأخطاء غير المتزامنة

```dart run
Future<int> fetchPrice(String item, int ms) async {
  await Future.delayed(Duration(milliseconds: ms));
  if (item == 'ذهب') throw Exception('الخادم لا يرد');
  return item.length * 10;
}

Future<void> main() async {
  final prices = await Future.wait([fetchPrice('شاي', 100), fetchPrice('بن', 50)]);
  print(prices);

  try {
    await fetchPrice('ذهب', 10);
  } catch (e) {
    print('فشل: $e');
  }
}
```

```text output
[30, 20]
فشل: Exception: الخادم لا يرد
```

- `Future.wait` تشغل الأعمال **معًا** وتنتظرها كلها، فالوقت الكلي وقت أبطأها فقط.
- مع `await` تعمل `try / catch` على الأخطاء غير المتزامنة كالعادة.

## Stream: قيم تصل واحدة بعد الأخرى

```dart run
Stream<int> countdown(int from) async* {
  for (var i = from; i >= 1; i--) {
    await Future.delayed(Duration(milliseconds: 50));
    yield i;
  }
}

Future<void> main() async {
  await for (final n in countdown(3)) {
    print('$n...');
  }
  print('انطلق!');
}
```

```text output
3...
2...
1...
انطلق!
```

الـ `Future` قيمة **واحدة** في المستقبل، والـ `Stream` **سلسلة** قيم تصل تباعًا (مثل رسائل محادثة أو موقع GPS). `async*` و`yield` تصنع Stream، و`await for` تقرؤها.

## قراءة ملف وكتابته

```dart run
import 'dart:io';

Future<void> main() async {
  final file = File('notes.txt');
  await file.writeAsString('السطر الأول\nالسطر الثاني\n');
  await file.writeAsString('السطر الثالث\n', mode: FileMode.append);
  final lines = await file.readAsLines();
  print('عدد الأسطر: ${lines.length}');
  for (final line in lines) {
    print('- $line');
  }
  await file.delete();
  print(await file.exists());
}
```

```text output
عدد الأسطر: 3
- السطر الأول
- السطر الثاني
- السطر الثالث
false
```

عمليات الملفات في `dart:io` غير متزامنة (تُرجع Future)، لأن القرص أبطأ كثيرًا من المعالج.

## أخطاء شائعة

- **نسيان `await`**: تحصل على `Instance of 'Future<String>'` بدل القيمة.
- **`await` في دالة بدون `async`**: خطأ قبل التشغيل. أضف `async` واجعل نوعها `Future<...>`.
- **`catch` فارغة**: `catch (e) {}` تخفي الخطأ فلا تعرف لماذا لم يعمل البرنامج. اطبع الخطأ على الأقل.

## تمارين

### التمرين 1

اكتب دالة `double safeDivide(double a, double b)` ترمي `ArgumentError('لا قسمة على صفر')` إذا كان `b` صفرًا. استدعها داخل `try` للأزواج `(10, 4)` و`(5, 0)`.

```dart exercise
void main() {
  for (final pair in [[10.0, 4.0], [5.0, 0.0]]) {
  }
}
```

```dart solution
double safeDivide(double a, double b) {
  if (b == 0) throw ArgumentError('لا قسمة على صفر');
  return a / b;
}

void main() {
  for (final pair in [[10.0, 4.0], [5.0, 0.0]]) {
    try {
      print(safeDivide(pair[0], pair[1]));
    } on ArgumentError catch (e) {
      print('خطأ: ${e.message}');
    }
  }
}
```

```text output
2.5
خطأ: لا قسمة على صفر
```

### التمرين 2

اكتب دالة غير متزامنة `Future<String> cook(String dish, int ms)` تنتظر `ms` ملّي ثانية ثم تُرجع `جاهز: <الطبق>`. اطبخ `شوربة` (100) و`أرز` (50) **معًا** بـ `Future.wait` واطبع النتائج، ثم اطبع `بالهناء!`.

```dart exercise
Future<void> main() async {
}
```

```dart solution
Future<String> cook(String dish, int ms) async {
  await Future.delayed(Duration(milliseconds: ms));
  return 'جاهز: $dish';
}

Future<void> main() async {
  final meals = await Future.wait([cook('شوربة', 100), cook('أرز', 50)]);
  for (final m in meals) {
    print(m);
  }
  print('بالهناء!');
}
```

```text output
جاهز: شوربة
جاهز: أرز
بالهناء!
```

`Future.wait` تُرجع النتائج **بترتيب القائمة**، لا بترتيب الانتهاء.

## اختبر نفسك

```quiz
{"question": "ما وظيفة finally؟", "choices": ["تعمل فقط عند الخطأ", "تعمل دائمًا بعد try سواء نجح أو فشل", "تنهي البرنامج", "ترمي خطأ"], "answer": 1, "explanation": "finally مكان مناسب للتنظيف (إغلاق ملف مثلًا) لأنها تعمل في كل الأحوال."}
```

```quiz
{"question": "ماذا تطبع print(fetch()) إذا كانت fetch دالة async تُرجع Future<String> ونسيت await؟", "choices": ["النص", "Instance of 'Future<String>'", "null", "خطأ قبل التشغيل"], "answer": 1, "explanation": "بدون await تحصل على الوعد نفسه (Future) لا على قيمته."}
```

```quiz
{"question": "ما الفرق بين Future وStream؟", "choices": ["لا فرق", "Future قيمة واحدة مستقبلية، وStream سلسلة قيم تصل تباعًا", "Stream أسرع", "Future للملفات فقط"], "answer": 1, "explanation": "Stream مثل نهر من القيم، وFuture قيمة واحدة."}
```

## الخلاصة

- `try / on / catch / finally` لمعالجة الأخطاء، و`throw` لرميها، وصنف ينفذ `Exception` لخطأ خاص.
- `Future` و`async` و`await` لانتظار الأعمال البطيئة دون تجميد البرنامج، و`Future.wait` لتشغيلها معًا.
- `Stream` و`async*` و`yield` و`await for` لسلسلة قيم.
- `File` من `dart:io`: `writeAsString` و`readAsLines` و`delete`.
