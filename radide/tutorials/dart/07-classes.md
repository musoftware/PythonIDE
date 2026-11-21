# الدرس 7: الفئات والكائنات والوراثة

في Dart **كل شيء كائن**: الأرقام والنصوص والقوائم، وفي Flutter كل زر وكل شاشة. في هذا الدرس نتعلم أن نصنع كائناتنا بأنفسنا.

> **تشبيه:** **الفئة** (class) مثل **قالب الكعك**، و**الكائن** (object) هو الكعكة نفسها. من قالب واحد تصنع كعكات كثيرة، لكل واحدة نكهتها (خصائصها)، وكلها لها الشكل نفسه.

## أول فئة

```dart run
class Student {
  String name;
  int grade;

  Student(this.name, this.grade);       // الباني (constructor)

  void introduce() {
    print('أنا $name في الصف $grade');
  }

  bool get isSenior => grade >= 10;     // خاصية محسوبة (getter)
}

void main() {
  final s1 = Student('مريم', 11);
  final s2 = Student('زياد', 8);
  s1.introduce();
  s2.introduce();
  print(s1.isSenior);
  s2.grade++;
  print(s2.grade);
}
```

```text output
أنا مريم في الصف 11
أنا زياد في الصف 8
true
9
```

- **الخصائص** (fields): `name` و`grade`، متغيرات داخل الفئة لكل كائن نسخته منها.
- **الباني** `Student(this.name, this.grade)` ينشئ الكائن، و`this.name` اختصار يعني «ضع المعامل الأول في الخاصية `name`».
- **الدوال** (methods): مثل `introduce`، أفعال يقوم بها الكائن.
- **getter**: `get isSenior` تُقرأ كخاصية (`s1.isSenior` بلا أقواس) لكنها تُحسب كل مرة.

## الباني بمعاملات مسماة و final

هذا هو الشكل الذي ستراه في Flutter كثيرًا:

```dart run
class Product {
  final String name;
  final double price;
  final int quantity;

  const Product({required this.name, required this.price, this.quantity = 1});

  double get total => price * quantity;

  @override
  String toString() => '$name × $quantity = ${total.toStringAsFixed(2)}';
}

void main() {
  const tea = Product(name: 'شاي', price: 12.5, quantity: 4);
  final bread = Product(name: 'خبز', price: 3);
  print(tea);
  print(bread);
  print(tea.total + bread.total);
}
```

```text output
شاي × 4 = 50.00
خبز × 1 = 3.00
53.0
```

- خصائص `final` تجعل الكائن **غير قابل للتغيير** بعد إنشائه: آمن وسهل الفهم.
- `const` قبل الباني تسمح بإنشاء كائنات ثابتة توفر الذاكرة (مثل `const Text('...')` في Flutter).
- `@override String toString()` تحدد كيف يُطبع الكائن.

## الخصائص الخاصة والـ setter

الاسم الذي يبدأ بـ `_` **خاص** بالملف، لا يُرى من خارجه:

```dart run
class BankAccount {
  final String owner;
  double _balance = 0;            // خاص: لا يُعدّل مباشرة من الخارج

  BankAccount(this.owner);

  double get balance => _balance;

  void deposit(double amount) {
    if (amount <= 0) {
      print('مبلغ غير صحيح');
      return;
    }
    _balance += amount;
  }

  bool withdraw(double amount) {
    if (amount > _balance) return false;
    _balance -= amount;
    return true;
  }
}

void main() {
  final acc = BankAccount('سلمى');
  acc.deposit(500);
  acc.deposit(-20);
  print(acc.withdraw(200));
  print(acc.withdraw(1000));
  print('رصيد ${acc.owner}: ${acc.balance}');
}
```

```text output
مبلغ غير صحيح
true
false
رصيد سلمى: 300.0
```

هذا يسمى **التغليف** (encapsulation): نحمي البيانات ونسمح بتغييرها فقط بطرق نتحكم فيها، فلا يصبح الرصيد سالبًا أبدًا.

## الوراثة (Inheritance)

```dart run
class Animal {
  final String name;
  Animal(this.name);

  void speak() => print('$name يصدر صوتًا');
  void sleep() => print('$name نائم... zzz');
}

class Cat extends Animal {
  Cat(super.name);

  @override
  void speak() => print('$name: مياو');
}

class Dog extends Animal {
  final String breed;
  Dog(super.name, this.breed);

  @override
  void speak() => print('$name ($breed): هاو هاو');
}

void main() {
  final animals = <Animal>[Cat('مشمش'), Dog('ركس', 'جيرمن'), Animal('ببغاء')];
  for (final a in animals) {
    a.speak();
  }
  animals.first.sleep();
  print(animals[1] is Dog);
}
```

```text output
مشمش: مياو
ركس (جيرمن): هاو هاو
ببغاء يصدر صوتًا
مشمش نائم... zzz
true
```

- `extends` تعني «يرث من»: `Cat` يأخذ كل ما في `Animal` (مثل `sleep`).
- `super.name` تمرر المعامل إلى باني الفئة الأم.
- `@override` تعيد تعريف دالة موروثة بسلوك جديد.
- قائمة من نوع `Animal` تحمل قططًا وكلابًا، وكل منها يتكلم بطريقته: هذا هو **تعدد الأشكال** (polymorphism).
- `is` تفحص نوع الكائن.

> **في Flutter:** كل شاشة تكتبها هي فئة ترث من `StatelessWidget` أو `StatefulWidget`، وتعيد تعريف الدالة `build` بـ `@override`. الآن تعرف ماذا تعني هذه الكلمات!

## الفئات المجردة (abstract)

```dart run
abstract class Shape {
  double get area;
  String get name;
  void describe() => print('$name مساحته ${area.toStringAsFixed(2)}');
}

class Circle extends Shape {
  final double r;
  Circle(this.r);
  @override
  double get area => 3.14159 * r * r;
  @override
  String get name => 'الدائرة';
}

class Rect extends Shape {
  final double w, h;
  Rect(this.w, this.h);
  @override
  double get area => w * h;
  @override
  String get name => 'المستطيل';
}

void main() {
  final shapes = [Circle(2), Rect(3, 4)];
  for (final s in shapes) {
    s.describe();
  }
}
```

```text output
الدائرة مساحته 12.57
المستطيل مساحته 12.00
```

الفئة المجردة «عقد»: تقول ما يجب أن يوجد (`area` و`name`) دون أن تنفذه، ولا يمكن إنشاء كائن منها مباشرة.

## enum: قائمة قيم محددة

```dart run
enum Level { easy, medium, hard }

void main() {
  final level = Level.medium;
  print(level.name);
  print(Level.values.length);
  final text = switch (level) {
    Level.easy => 'سهل',
    Level.medium => 'متوسط',
    Level.hard => 'صعب',
  };
  print(text);
}
```

```text output
medium
3
متوسط
```

## أخطاء شائعة

- **نسيان `required`** مع معامل مسمى من نوع لا يقبل `null`: تقول Dart إن قيمته قد تكون `null`.
- **تعديل خاصية `final`**: `tea.price = 10;` خطأ. أنشئ كائنًا جديدًا بدلًا من ذلك.
- **نسيان `@override`**: ليست إجبارية، لكنها تحميك: إذا أخطأت في اسم الدالة تنبهك Dart.

## تمارين

### التمرين 1

اكتب فئة `Rectangle` بخاصيتين `width` و`height` (من نوع `double`) وباني بمعاملات مسماة، وخاصيتين محسوبتين `area` و`perimeter`، ودالة `isSquare`.

```dart exercise
void main() {
  final r = Rectangle(width: 4, height: 6);
  final sq = Rectangle(width: 5, height: 5);
  print('المساحة: ${r.area}');
  print('المحيط: ${r.perimeter}');
  print(r.isSquare());
  print(sq.isSquare());
}
```

```dart solution
class Rectangle {
  final double width;
  final double height;

  Rectangle({required this.width, required this.height});

  double get area => width * height;
  double get perimeter => 2 * (width + height);
  bool isSquare() => width == height;
}

void main() {
  final r = Rectangle(width: 4, height: 6);
  final sq = Rectangle(width: 5, height: 5);
  print('المساحة: ${r.area}');
  print('المحيط: ${r.perimeter}');
  print(r.isSquare());
  print(sq.isSquare());
}
```

```text output
المساحة: 24.0
المحيط: 20.0
false
true
```

### التمرين 2

اكتب فئة `Employee` (اسم وراتب) فيها دالة `double bonus()` تُرجع 10% من الراتب، وفئة `Manager` ترث منها وتعيد تعريف `bonus` لتُرجع 20% زائد 1000. اطبع مكافأة كل موظف في القائمة.

```dart exercise
void main() {
  final staff = [Employee('هاني', 8000), Manager('دينا', 15000)];
  for (final e in staff) {
    print('${e.name}: ${e.bonus()}');
  }
}
```

```dart solution
class Employee {
  final String name;
  final double salary;
  Employee(this.name, this.salary);

  double bonus() => salary * 0.10;
}

class Manager extends Employee {
  Manager(super.name, super.salary);

  @override
  double bonus() => salary * 0.20 + 1000;
}

void main() {
  final staff = [Employee('هاني', 8000), Manager('دينا', 15000)];
  for (final e in staff) {
    print('${e.name}: ${e.bonus()}');
  }
}
```

```text output
هاني: 800.0
دينا: 4000.0
```

## اختبر نفسك

```quiz
{"question": "ما العلاقة بين الفئة والكائن؟", "choices": ["لا علاقة", "الفئة قالب، والكائن نسخة مصنوعة منه", "الكائن قالب للفئة", "هما نفس الشيء"], "answer": 1, "explanation": "من فئة واحدة ننشئ كائنات كثيرة، لكل منها قيم خصائصه."}
```

```quiz
{"question": "ماذا يعني الاسم _balance داخل فئة؟", "choices": ["متغير ثابت", "خاصية خاصة لا تُرى خارج الملف", "خطأ في التسمية", "متغير عام"], "answer": 1, "explanation": "الشرطة السفلية في أول الاسم تجعله خاصًا بالملف (private)."}
```

```quiz
{"question": "ما وظيفة @override؟", "choices": ["تحذف الدالة", "تعلن أنك تعيد تعريف دالة موروثة من الفئة الأم", "تجعل الدالة خاصة", "تسرّع البرنامج"], "answer": 1, "explanation": "@override توضح أن الدالة تستبدل دالة الأم، وتنبهك إذا أخطأت في الاسم."}
```

## الخلاصة

- الفئة: خصائص + باني + دوال، و`get` للخصائص المحسوبة.
- الباني بمعاملات مسماة و`final` هو أسلوب Flutter، و`_` للخصائص الخاصة.
- `extends` للوراثة، و`super` للفئة الأم، و`@override` لإعادة التعريف، و`abstract` للعقود، و`enum` لقيم محددة.
