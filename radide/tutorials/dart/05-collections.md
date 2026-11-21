# الدرس 5: القوائم والقواميس والمجموعات

متغير واحد يحفظ قيمة واحدة. لكن ماذا لو أردت حفظ أسماء 30 طالبًا؟ نستخدم **المجموعات** (collections): `List` و`Map` و`Set`.

> **تشبيه:** `List` مثل **قطار** عرباته مرقمة: العربة 0، العربة 1... و`Map` مثل **دليل الهاتف**: تبحث بالاسم فتجد الرقم. و`Set` مثل **ألبوم الملصقات**: لا يقبل الملصق نفسه مرتين.

## القوائم (List)

```dart run
void main() {
  final names = ['علي', 'منى', 'يوسف'];
  print(names);
  print(names[0]);           // أول عنصر رقمه 0
  print(names.length);
  names.add('هدى');
  names.insert(0, 'سامي');
  names.remove('منى');
  print(names);
  print(names.last);
  print(names.contains('علي'));
  print(names.indexOf('يوسف'));
}
```

```text output
[علي, منى, يوسف]
علي
3
[سامي, علي, يوسف, هدى]
هدى
true
2
```

- الترقيم يبدأ من **0**، فآخر عنصر رقمه `length - 1`.
- `final names` لا تمنع تغيير محتوى القائمة، بل تمنع أن يشير `names` إلى قائمة أخرى.
- نوع القائمة هنا `List<String>`: قائمة نصوص فقط. ويمكن كتابته صراحة: `List<int> scores = [90, 75];`.

## أدوات القوائم الذكية

```dart run
void main() {
  final scores = [72, 95, 48, 88, 60];

  final passed = scores.where((s) => s >= 60).toList();
  final doubled = scores.map((s) => s * 2).toList();
  final total = scores.fold(0, (sum, s) => sum + s);
  final sorted = [...scores]..sort();

  print(passed);
  print(doubled);
  print('المجموع = $total');
  print('المتوسط = ${total / scores.length}');
  print(sorted);
  print(scores.any((s) => s < 50));
  print(scores.every((s) => s > 40));
  print(scores.join(' - '));
}
```

```text output
[72, 95, 88, 60]
[144, 190, 96, 176, 120]
المجموع = 363
المتوسط = 72.6
[48, 60, 72, 88, 95]
true
true
72 - 95 - 48 - 88 - 60
```

| الدالة | وظيفتها |
|---|---|
| `where(شرط)` | تختار العناصر التي تحقق الشرط |
| `map(تحويل)` | تحوّل كل عنصر إلى شيء آخر |
| `fold(بداية, دالة)` | تجمع العناصر في قيمة واحدة |
| `any` / `every` | هل يحقق عنصر واحد / كل العناصر الشرط؟ |
| `sort()` | ترتب القائمة نفسها |
| `join(فاصل)` | تلصق العناصر في نص |

- `...scores` **عامل النشر** (spread): ينسخ العناصر في قائمة جديدة، فلا نغيّر الأصل عند الترتيب.
- `..sort()` **عامل التتالي** (cascade): ينفذ `sort` على القائمة ثم يُرجع القائمة نفسها.
- `map` و`where` تُرجعان `Iterable`، و`.toList()` تحوّلها إلى قائمة.

## القواميس (Map)

```dart run
void main() {
  final prices = {'شاي': 10, 'قهوة': 25, 'عصير': 18};
  print(prices['قهوة']);
  prices['كعك'] = 15;          // إضافة
  prices['شاي'] = 12;          // تعديل
  prices.remove('عصير');
  print(prices);
  print(prices.containsKey('شاي'));
  print(prices['ماء']);         // مفتاح غير موجود

  prices.forEach((item, price) {
    print('$item: $price جنيه');
  });

  for (final entry in prices.entries) {
    if (entry.value > 12) print('غالٍ: ${entry.key}');
  }
}
```

```text output
25
{شاي: 12, قهوة: 25, كعك: 15}
true
null
شاي: 12 جنيه
قهوة: 25 جنيه
كعك: 15 جنيه
غالٍ: قهوة
غالٍ: كعك
```

القاموس أزواج **مفتاح: قيمة**، ونوعه هنا `Map<String, int>`. وطلب مفتاح غير موجود يُرجع `null`.

## المجموعات (Set)

```dart run
void main() {
  final visited = {'القاهرة', 'أسوان'};
  visited.add('القاهرة');      // موجودة: لن تُضاف مرة ثانية
  visited.add('سيوة');
  print(visited);
  print(visited.length);

  final a = {1, 2, 3, 4};
  final b = {3, 4, 5};
  print(a.intersection(b));
  print(a.union(b));
  print(a.difference(b));

  final repeated = [5, 1, 5, 2, 1];
  print(repeated.toSet().toList());
}
```

```text output
{القاهرة, أسوان, سيوة}
3
{3, 4}
{1, 2, 3, 4, 5}
{1, 2}
[5, 1, 2]
```

`toSet()` طريقة سريعة لحذف التكرار من قائمة.

## بناء القوائم بـ if و for داخلها

```dart run
void main() {
  final isLoggedIn = true;
  final menu = [
    'الرئيسية',
    'المنتجات',
    if (isLoggedIn) 'حسابي' else 'تسجيل الدخول',
    for (var i = 1; i <= 2; i++) 'عرض $i',
  ];
  print(menu);
}
```

```text output
[الرئيسية, المنتجات, حسابي, عرض 1, عرض 2]
```

هذه الكتابة تُستخدم كثيرًا في Flutter لبناء قائمة الودجات (عناصر الواجهة): «أظهر زر الحساب **إذا** كان المستخدم مسجلًا».

## أخطاء شائعة

- **رقم خارج القائمة:** `names[10]` في قائمة من 3 عناصر يوقف البرنامج بخطأ `RangeError`.
- **تعديل القائمة أثناء المرور عليها** بـ `for-in` يسبب خطأ. أنشئ قائمة جديدة بـ `where` بدلًا من ذلك.
- **نسيان `.toList()`** بعد `map`: الناتج `Iterable` يُطبع بأقواس `( )` لا `[ ]`، ولا يمكن الإضافة إليه.

## تمارين

### التمرين 1

اقرأ أعدادًا مفصولة بمسافات في سطر واحد، واطبع أكبرها وأصغرها والأعداد الزوجية منها.

```dart exercise
import 'dart:io';

void main() {
  final numbers = stdin.readLineSync()!.split(' ').map(int.parse).toList();
}
```

```dart solution
import 'dart:io';

void main() {
  final numbers = stdin.readLineSync()!.split(' ').map(int.parse).toList();
  final sorted = [...numbers]..sort();
  print('الأكبر: ${sorted.last}');
  print('الأصغر: ${sorted.first}');
  print('الزوجية: ${numbers.where((n) => n.isEven).toList()}');
}
```

```text input
7 12 3 20 9
```

```text output
الأكبر: 20
الأصغر: 3
الزوجية: [12, 20]
```

`map(int.parse)` تمرر الدالة `int.parse` نفسها لتحوّل كل نص إلى رقم.

### التمرين 2

عدّ تكرار كل كلمة في الجملة `'قط كلب قط عصفور كلب قط'` باستخدام `Map`، واطبع كل كلمة وعددها.

```dart exercise
void main() {
  final words = 'قط كلب قط عصفور كلب قط'.split(' ');
  final counts = <String, int>{};
}
```

```dart solution
void main() {
  final words = 'قط كلب قط عصفور كلب قط'.split(' ');
  final counts = <String, int>{};
  for (final w in words) {
    counts[w] = (counts[w] ?? 0) + 1;
  }
  counts.forEach((word, n) => print('$word: $n'));
}
```

```text output
قط: 3
كلب: 2
عصفور: 1
```

`counts[w] ?? 0` تعني: القيمة الحالية، أو 0 إذا لم تكن الكلمة موجودة بعد (`null`).

## اختبر نفسك

```quiz
{"question": "ما ناتج [1, 2, 3, 4].where((n) => n > 2).toList()؟", "choices": ["[1, 2]", "[3, 4]", "[true, true]", "2"], "answer": 1, "explanation": "where تختار العناصر التي تحقق الشرط."}
```

```quiz
{"question": "أي مجموعة لا تسمح بتكرار العنصر نفسه؟", "choices": ["List", "Map", "Set", "String"], "answer": 2, "explanation": "Set تحفظ كل قيمة مرة واحدة فقط."}
```

## الخلاصة

- `List` قائمة مرتبة تبدأ من 0، مع `add` و`remove` و`where` و`map` و`fold`.
- `Map` أزواج مفتاح وقيمة، و`Set` مجموعة بلا تكرار.
- `...` لنسخ العناصر، و`..` للتتالي، و`if` و`for` داخل القائمة لبنائها بشروط.
