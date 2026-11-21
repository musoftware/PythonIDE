# الدرس 6: الأمان من القيم الفارغة والنصوص

## ما هي null؟

`null` تعني «**لا شيء**»: قيمة غائبة. مثلًا: المستخدم لم يكتب رقم هاتفه، أو بحثت في قاموس عن مفتاح غير موجود. في لغات كثيرة يسبب استخدام `null` بالخطأ انهيار البرنامج، حتى سمّاه مخترعه «خطأ المليار دولار».

> **تشبيه:** المتغير الذي يقبل `null` مثل **صندوق بريد قد يكون فارغًا**. قبل أن تقرأ الرسالة يجب أن تفتح الصندوق وتتأكد أن فيه رسالة. Dart تجبرك على هذا التأكد، فلا تمد يدك في صندوق فارغ.

## الأنواع التي تقبل null: علامة ?

```dart run
void main() {
  String name = 'رنا';       // لا يقبل null أبدًا
  String? phone;             // قد يكون null (القيمة الابتدائية null)
  print(name.length);
  print(phone);
  phone = '0100000000';
  print(phone.length);       // Dart تعرف الآن أنه ليس null
}
```

```text output
3
null
10
```

- `String` نص مؤكد، و`String?` «نص أو لا شيء».
- `name = null;` خطأ **قبل التشغيل**: هذا هو «الأمان من القيم الفارغة» (Null Safety).
- بعد أن أعطينا `phone` قيمة، فهمت Dart وحدها أنه لم يعد `null`.

## أدوات التعامل مع null

```dart run
void main() {
  String? nickname;
  int? age = int.tryParse('25');
  final scores = <String, int>{'علي': 80};

  print(nickname ?? 'بدون لقب');        // ?? قيمة بديلة
  print(nickname?.length);              // ?. اطلب فقط إذا لم يكن null
  print(age! + 1);                      // ! أنا متأكد أنه ليس null

  nickname ??= 'البطل';                 // أعطه قيمة إذا كان null فقط
  print(nickname);

  final mona = scores['منى'] ?? 0;
  print('درجة منى: $mona');

  if (age != null && age > 18) {
    print('بالغ');
  }
}
```

```text output
بدون لقب
null
26
البطل
درجة منى: 0
بالغ
```

| الأداة | معناها |
|---|---|
| `a ?? b` | `a` إذا لم يكن `null`، وإلا `b` |
| `a?.b` | اطلب `b` من `a`، وإذا كان `a` فارغًا فالناتج `null` بدل الخطأ |
| `a!` | «أنا متأكد أنه ليس `null`» (إذا كنت مخطئًا يتوقف البرنامج!) |
| `a ??= b` | ضع `b` في `a` إذا كان `a` فارغًا |
| `if (a != null)` | بعد الفحص تعامل Dart `a` كقيمة مؤكدة داخل الشرط |

> **قاعدة ذهبية:** استخدم `??` و`if (x != null)` أولًا، واترك `!` للحالات التي أنت متأكد منها تمامًا.

## late: سأعطيه قيمة لاحقًا

```dart run
late String message;

void prepare() {
  message = 'جاهز!';
}

void main() {
  prepare();
  print(message);
}
```

```text output
جاهز!
```

`late` تقول لـ Dart: «هذا المتغير ليس `null`، لكني سأعطيه قيمته لاحقًا قبل أن أستخدمه». ستراها في Flutter مع المتغيرات التي تُجهز في `initState`.

## النصوص بالتفصيل

```dart run
void main() {
  final s = '  Dart و Flutter  ';
  print(s.trim());
  print(s.trim().length);
  print('flutter'.toUpperCase());
  print('Hello World'.toLowerCase());
  print('dart,flutter,firebase'.split(','));
  print('القاهرة'.contains('هر'));
  print('report.pdf'.endsWith('.pdf'));
  print('Flutter'.startsWith('Fl'));
  print('Flutter'.substring(0, 3));
  print('Flutter'.indexOf('t'));
  print('ha' * 3);
  print('2026-11-21'.replaceAll('-', '/'));
  print('7'.padLeft(3, '0'));
  print('Dart'[0]);
}
```

```text output
Dart و Flutter
14
FLUTTER
hello world
[dart, flutter, firebase]
true
true
true
Flu
3
hahaha
2026/11/21
007
D
```

## النصوص متعددة الأسطر والخام

```dart run
void main() {
  final name = 'هبة';
  final card = '''
بطاقة دعوة
الاسم: $name
المكان: القاعة الكبرى''';
  print(card);
  print('سطر1\nسطر2');
  print(r'المسار: C:\new\test');
  print('علامة \$ للدولار');
}
```

```text output
بطاقة دعوة
الاسم: هبة
المكان: القاعة الكبرى
سطر1
سطر2
المسار: C:\new\test
علامة $ للدولار
```

- `'''...'''` نص من عدة أسطر.
- `\n` سطر جديد، و`\$` تطبع العلامة `$` نفسها بدل الاستيفاء.
- `r'...'` نص **خام** (raw): لا يفسر `\` ولا `$`، مفيد لمسارات ويندوز.

## StringBuffer: بناء نص كبير

```dart run
void main() {
  final buffer = StringBuffer();
  for (var i = 1; i <= 3; i++) {
    buffer.write('$i');
    if (i < 3) buffer.write(' → ');
  }
  buffer.writeln();
  buffer.write('انتهى');
  print(buffer.toString());
}
```

```text output
1 → 2 → 3
انتهى
```

عند جمع نص من أجزاء كثيرة داخل حلقة، `StringBuffer` أسرع من `+` المتكرر.

## أخطاء شائعة

- **استدعاء دالة على متغير يقبل null:**

<!-- compile-error -->
```dart
void main() {
  String? city;
  print(city.length);
}
```

تقول Dart: `The property 'length' can't be unconditionally accessed because the receiver can be 'null'.` الحل: `city?.length` أو `city ?? ''` أو فحص `if (city != null)`.

- **الإفراط في `!`:** `stdin.readLineSync()!` يتوقف إذا انتهى الإدخال. في البرامج الحقيقية استخدم `?? ''`.
- **نسيان أن النصوص لا تتغير:** `s.trim();` وحدها لا تغيّر `s`. اكتب `s = s.trim();`.

## تمارين

### التمرين 1

اقرأ سطرًا قد يكون فارغًا. إذا كان فارغًا اطبع `مرحبًا يا ضيف`، وإلا اطبع الاسم بعد حذف المسافات وعدد حروفه.

```dart exercise
import 'dart:convert';
import 'dart:io';

void main() {
  final input = stdin.readLineSync(encoding: utf8);
}
```

```dart solution
import 'dart:convert';
import 'dart:io';

void main() {
  final input = stdin.readLineSync(encoding: utf8);
  final name = input?.trim() ?? '';
  if (name.isEmpty) {
    print('مرحبًا يا ضيف');
  } else {
    print('مرحبًا يا $name (${name.length} حروف)');
  }
}
```

```text input
   ياسمين   
```

```text output
مرحبًا يا ياسمين (6 حروف)
```

### التمرين 2

اكتب دالة `String initials(String fullName)` تُرجع الحروف الأولى من كل كلمة بأحرف كبيرة مفصولة بنقاط: `'ada lovelace'` تصبح `A.L.`.

```dart exercise
String initials(String fullName) {
  return '';
}

void main() {
  print(initials('ada lovelace'));
  print(initials('grace brewster hopper'));
}
```

```dart solution
String initials(String fullName) {
  return fullName
      .trim()
      .split(' ')
      .where((w) => w.isNotEmpty)
      .map((w) => '${w[0].toUpperCase()}.')
      .join();
}

void main() {
  print(initials('ada lovelace'));
  print(initials('grace brewster hopper'));
}
```

```text output
A.L.
G.B.H.
```

## اختبر نفسك

```quiz
{"question": "ما ناتج: String? x; print(x ?? 'فارغ');", "choices": ["null", "فارغ", "خطأ", "x"], "answer": 1, "explanation": "x قيمته null، فيُرجع ?? القيمة البديلة."}
```

```quiz
{"question": "ما الفرق بين String وString؟", "choices": ["لا فرق", "String? يمكن أن تكون null وString لا", "String? للنصوص الطويلة", "String? أسرع"], "answer": 1, "explanation": "علامة ? بعد النوع تعني أنه يقبل null."}
```

```quiz
{"question": "متى يكون استخدام ! خطيرًا؟", "choices": ["دائمًا آمن", "عندما تكون القيمة null فعلًا، فيتوقف البرنامج", "مع الأرقام فقط", "داخل الحلقات"], "answer": 1, "explanation": "! تعِد Dart بأن القيمة ليست null، فإذا كانت null يحدث خطأ أثناء التشغيل."}
```

## الخلاصة

- `T?` نوع يقبل `null`، و`T` لا يقبله: Dart تكتشف الأخطاء قبل التشغيل.
- `??` و`?.` و`??=` و`if (x != null)` للتعامل الآمن، و`!` بحذر، و`late` لقيمة تأتي لاحقًا.
- دوال النصوص: `trim` و`split` و`contains` و`substring` و`replaceAll` و`padLeft`، و`'''` للأسطر المتعددة، و`r'...'` للنص الخام.
