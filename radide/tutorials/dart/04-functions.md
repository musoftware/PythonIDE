# الدرس 4: الدوال: المعاملات المسماة والاختيارية والسهمية

عندما يتكرر جزء من الكود، أو يصبح البرنامج طويلًا، نقسمه إلى **دوال**: كل دالة لها اسم وتقوم بعمل واحد.

> **تشبيه:** الدالة مثل **ماكينة العصير**: تضع فيها فاكهة (المعاملات)، فتُخرج لك عصيرًا (القيمة المرجعة). لا يهمك ما يحدث بداخلها، يكفي أن تعرف ماذا تضع وماذا تأخذ.

## تعريف دالة واستدعاؤها

```dart run
void greet(String name) {
  print('أهلًا يا $name');
}

int square(int x) {
  return x * x;
}

void main() {
  greet('ليلى');
  greet('عمر');
  print(square(6));
  final total = square(3) + square(4);
  print(total);
}
```

```text output
أهلًا يا ليلى
أهلًا يا عمر
36
25
```

- قبل اسم الدالة نكتب **نوع القيمة المرجعة**: `int` للدالة `square`، و`void` إذا لم تُرجع شيئًا.
- بين القوسين **المعاملات** (parameters) مع أنواعها.
- `return` تُرجع النتيجة وتنهي الدالة فورًا.

## الدوال السهمية (Arrow functions)

إذا كانت الدالة تعبيرًا واحدًا، نكتبها مختصرة بـ `=>`:

```dart run
int square(int x) => x * x;
bool isEven(int n) => n % 2 == 0;
String fullName(String first, String last) => '$first $last';

void main() {
  print(square(9));
  print(isEven(7));
  print(fullName('أحمد', 'سالم'));
}
```

```text output
81
false
أحمد سالم
```

`=> تعبير` تعني `{ return تعبير; }`. ستراها في Flutter في كل مكان.

## المعاملات المسماة (Named parameters)

عندما تكثر المعاملات يصعب تذكر ترتيبها. المعاملات المسماة تُكتب بين `{ }` وتُمرر **باسمها**:

```dart run
void bookTicket({required String name, required String city, int seats = 1, bool vip = false}) {
  final kind = vip ? 'VIP' : 'عادي';
  print('$name: $seats مقعد إلى $city ($kind)');
}

void main() {
  bookTicket(name: 'سارة', city: 'الأقصر');
  bookTicket(city: 'دهب', name: 'خالد', seats: 3, vip: true);
}
```

```text output
سارة: 1 مقعد إلى الأقصر (عادي)
خالد: 3 مقعد إلى دهب (VIP)
```

- `required` تعني أن المعامل إجباري.
- `seats = 1` **قيمة افتراضية** تُستخدم إذا لم يُمرر المعامل.
- الترتيب لا يهم عند الاستدعاء، والكود يُقرأ كجملة واضحة.

> **لماذا هذا مهم؟** Flutter كلها معاملات مسماة: `Text('مرحبا', style: ...)` و`Padding(padding: ..., child: ...)`. إذا فهمت هذه الفقرة فهمت نصف كود Flutter!

## المعاملات الموضعية الاختيارية

تُكتب بين `[ ]` ويمكن حذفها من آخر الاستدعاء:

```dart run
String hello(String name, [String greeting = 'مرحبًا', String mark = '!']) {
  return '$greeting يا $name$mark';
}

void main() {
  print(hello('نور'));
  print(hello('نور', 'صباح الخير'));
  print(hello('نور', 'تصبح على خير', '.'));
}
```

```text output
مرحبًا يا نور!
صباح الخير يا نور!
تصبح على خير يا نور.
```

## الدوال قيم: الدوال المجهولة

في Dart يمكن وضع الدالة في متغير أو تمريرها لدالة أخرى:

```dart run
void repeat(int times, void Function(int) action) {
  for (var i = 1; i <= times; i++) {
    action(i);
  }
}

void main() {
  final twice = (int x) => x * 2;       // دالة مجهولة في متغير
  print(twice(21));

  repeat(3, (i) {
    print('المرة $i');
  });

  final numbers = [3, 8, 1];
  numbers.forEach((n) => print('العدد $n'));
}
```

```text output
42
المرة 1
المرة 2
المرة 3
العدد 3
العدد 8
العدد 1
```

- `(i) { ... }` دالة **بلا اسم** (anonymous function) نمررها مباشرة.
- `void Function(int)` نوع «دالة تأخذ `int` ولا تُرجع شيئًا».
- هذا بالضبط ما يحدث في Flutter مع `onPressed: () { ... }`: تمرر للزر دالة تعمل عند الضغط.

## النطاق (Scope)

```dart run
var counter = 0;          // متغير عام: تراه كل الدوال

void addOne() {
  counter++;
  final local = 'محلي';   // لا يُرى خارج الدالة
  print('$local: $counter');
}

void main() {
  addOne();
  addOne();
  print('العداد = $counter');
}
```

```text output
محلي: 1
محلي: 2
العداد = 2
```

## أخطاء شائعة

- **نسيان `return`** في دالة نوعها `int`: تقول Dart إن الدالة قد لا تُرجع قيمة.
- **تمرير معامل مسمى بلا اسمه:** `bookTicket('سارة', 'الأقصر')` خطأ، والصحيح `bookTicket(name: 'سارة', city: 'الأقصر')`.
- **نسيان القوسين:** `greet;` لا تستدعي الدالة. الصحيح `greet('ليلى');`.

## تمارين

### التمرين 1

اكتب دالة سهمية `celsiusToF(double c)` تحوّل الحرارة إلى فهرنهايت (`c * 9 / 5 + 32`)، واطبع تحويل 0 و37 و100.

```dart exercise
void main() {
  for (final c in [0.0, 37.0, 100.0]) {
  }
}
```

```dart solution
double celsiusToF(double c) => c * 9 / 5 + 32;

void main() {
  for (final c in [0.0, 37.0, 100.0]) {
    print('$c°C = ${celsiusToF(c).toStringAsFixed(1)}°F');
  }
}
```

```text output
0.0°C = 32.0°F
37.0°C = 98.6°F
100.0°C = 212.0°F
```

### التمرين 2

اكتب دالة `price({required double amount, double discount = 0, bool delivery = false})` تحسب السعر النهائي: تطرح نسبة الخصم المئوية، ثم تضيف 20 للتوصيل إذا كان `delivery` صحيحًا. اطبع نتيجة ثلاثة استدعاءات.

```dart exercise
void main() {
  print(price(amount: 100));
  print(price(amount: 100, discount: 10));
  print(price(amount: 200, discount: 25, delivery: true));
}
```

```dart solution
double price({required double amount, double discount = 0, bool delivery = false}) {
  var total = amount - amount * discount / 100;
  if (delivery) total += 20;
  return total;
}

void main() {
  print(price(amount: 100));
  print(price(amount: 100, discount: 10));
  print(price(amount: 200, discount: 25, delivery: true));
}
```

```text output
100.0
90.0
170.0
```

## اختبر نفسك

```quiz
{"question": "ما معنى int square(int x) => x * x;؟", "choices": ["دالة تطبع x * x", "دالة تُرجع x * x", "متغير اسمه square", "خطأ في الكتابة"], "answer": 1, "explanation": "=> تعبير تعني return تعبير."}
```

```quiz
{"question": "كيف تستدعي void f({required int a, int b = 2})؟", "choices": ["f(1, 2)", "f(a: 1)", "f(b: 3)", "f()"], "answer": 1, "explanation": "a إجباري ويُمرر باسمه، وb اختياري له قيمة افتراضية."}
```

## الخلاصة

- الدالة: نوع القيمة المرجعة، الاسم، المعاملات، ثم الجسم، و`=>` للدالة المختصرة.
- `{ }` للمعاملات المسماة (مع `required` أو قيمة افتراضية)، و`[ ]` للموضعية الاختيارية.
- الدوال قيم: نخزنها في متغيرات ونمررها لدوال أخرى، وهذا أساس الأحداث في Flutter.
