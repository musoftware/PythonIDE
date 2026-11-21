# الدرس 6: المصفوفات

**في هذا الدرس ستتعلم:**

- **المصفوفة المرقّمة**: قائمة قيم بأرقام تبدأ من 0.
- **المصفوفة الترابطية**: مفاتيح بأسماء مثل `"name"` و`"price"`.
- المرور على المصفوفات بالحلقة `foreach`.
- أهم دوال المصفوفات: `count` و`in_array` و`sort` و`implode` و`explode` و`array_map` و`array_filter`.
- المصفوفات المتداخلة: قائمة منتجات تُعرض كجدول HTML.

## المصفوفة: خزانة بأدراج مرقّمة

المتغير العادي صندوق فيه قيمة واحدة. أما **المصفوفة** (array) فهي **خزانة بأدراج**، كل درج فيه قيمة، ولكل درج رقم يبدأ من **صفر**:

```php run
<?php
$fruits = ["تفاح", "موز", "برتقال"];
echo $fruits[0], "\n";
echo $fruits[2], "\n";

$fruits[] = "عنب";          // إضافة في آخر المصفوفة
$fruits[1] = "مانجو";       // تغيير عنصر
echo "عدد العناصر: ", count($fruits), "\n";
echo implode("، ", $fruits), "\n";
```

```text output
تفاح
برتقال
عدد العناصر: 4
تفاح، مانجو، برتقال، عنب
```

- `$fruits[0]` العنصر الأول، و`$fruits[2]` الثالث.
- `$fruits[] = ...` (أقواس فارغة) تضيف عنصرًا في النهاية.
- `implode` تلصق العناصر في نص واحد بفاصل نختاره.

## الحلقة foreach

`foreach` مصممة للمصفوفات: تمر على كل عنصر بالترتيب دون أن تقلق من الأرقام والحدود:

```php run
<?php
$colors = ["أحمر", "أخضر", "أزرق"];

foreach ($colors as $color) {
    echo "- $color\n";
}

foreach ($colors as $index => $color) {
    echo ($index + 1) . ". $color\n";
}
```

```text output
- أحمر
- أخضر
- أزرق
1. أحمر
2. أخضر
3. أزرق
```

## المصفوفة الترابطية: أدراج عليها أسماء

بدل الأرقام، نعطي كل درج **مفتاحًا** (key) باسم مفهوم. هذا مثل بطاقة بيانات شخص:

```php run
<?php
$student = [
    "name" => "يوسف",
    "age" => 19,
    "city" => "أسيوط",
];
echo "الاسم: {$student['name']}\n";
$student["grade"] = "A";              // مفتاح جديد

foreach ($student as $key => $value) {
    echo "$key = $value\n";
}
var_dump(isset($student["phone"]));
echo $student["phone"] ?? "لا يوجد هاتف", "\n";
```

```text output
الاسم: يوسف
name = يوسف
age = 19
city = أسيوط
grade = A
bool(false)
لا يوجد هاتف
```

- `isset` تسأل: هل المفتاح موجود وقيمته ليست `null`؟
- `??` مفيد جدًا مع المفاتيح التي قد لا توجد.
- داخل النص نكتب العنصر بين أقواس معقوصة: `{$student['name']}`.

## دوال مفيدة

```php run
<?php
$nums = [42, 7, 19, 3, 25];

echo "الأكبر: ", max($nums), " والأصغر: ", min($nums), "\n";
echo "المجموع: ", array_sum($nums), "\n";
var_dump(in_array(19, $nums));

sort($nums);                       // ترتيب تصاعدي (يغيّر المصفوفة نفسها)
echo implode(", ", $nums), "\n";
rsort($nums);                      // تنازلي
echo implode(", ", $nums), "\n";

$csv = "أحمد,سارة,خالد";
$names = explode(",", $csv);       // عكس implode: نص -> مصفوفة
echo count($names), " أسماء، أولها ", $names[0], "\n";
```

```text output
الأكبر: 42 والأصغر: 3
المجموع: 96
bool(true)
3, 7, 19, 25, 42
42, 25, 19, 7, 3
3 أسماء، أولها أحمد
```

## array_map و array_filter

- `array_map` **تحوّل** كل عنصر وتُرجع مصفوفة جديدة (مثل آلة تمر عليها كل القطع).
- `array_filter` **تختار** العناصر التي تحقق شرطًا (مثل مصفاة).

```php run
<?php
$prices = [100, 250, 40, 600];

$withTax = array_map(fn($p) => $p * 1.14, $prices);
echo implode(" | ", $withTax), "\n";

$expensive = array_filter($prices, fn($p) => $p >= 200);
echo implode(" | ", $expensive), "\n";
```

```text output
114 | 285 | 45.6 | 684
250 | 600
```

الصيغة `fn($p) => $p * 1.14` **دالة سهمية** (arrow function): دالة صغيرة بلا اسم تأخذ `$p` وتُرجع الناتج. سنشرح الدوال بالتفصيل في الدرس القادم.

## مصفوفة من مصفوفات: جدول منتجات

البيانات الحقيقية غالبًا **قائمة سجلات**: كل سجل مصفوفة ترابطية. هكذا ستصلنا الصفوف من قاعدة البيانات لاحقًا:

```php web run
<?php
$products = [
    ["name" => "قلم", "price" => 5, "qty" => 100],
    ["name" => "دفتر", "price" => 20, "qty" => 0],
    ["name" => "حقيبة", "price" => 350, "qty" => 4],
];
?>
<table>
    <tr><th>المنتج</th><th>السعر</th><th>الحالة</th></tr>
<?php foreach ($products as $p): ?>
    <tr>
        <td><?= $p['name'] ?></td>
        <td><?= $p['price'] ?></td>
        <td><?= $p['qty'] > 0 ? "متوفر" : "نفد" ?></td>
    </tr>
<?php endforeach; ?>
</table>
<p>عدد المنتجات: <?= count($products) ?></p>
```

```text output
<table>
    <tr><th>المنتج</th><th>السعر</th><th>الحالة</th></tr>
    <tr>
        <td>قلم</td>
        <td>5</td>
        <td>متوفر</td>
    </tr>
    <tr>
        <td>دفتر</td>
        <td>20</td>
        <td>نفد</td>
    </tr>
    <tr>
        <td>حقيبة</td>
        <td>350</td>
        <td>متوفر</td>
    </tr>
</table>
<p>عدد المنتجات: 3</p>
```

## الترتيب حسب مفتاح

لترتيب السجلات حسب السعر نستخدم `usort` مع العامل `<=>` الذي تعرفنا عليه في درس الشروط:

```php run
<?php
$products = [
    ["name" => "حقيبة", "price" => 350],
    ["name" => "قلم", "price" => 5],
    ["name" => "دفتر", "price" => 20],
];
usort($products, fn($a, $b) => $a["price"] <=> $b["price"]);
foreach ($products as $p) {
    echo "{$p['name']}: {$p['price']}\n";
}
echo implode(", ", array_column($products, "name")), "\n";
```

```text output
قلم: 5
دفتر: 20
حقيبة: 350
قلم, دفتر, حقيبة
```

`array_column` تأخذ عمودًا واحدًا من كل السجلات.

## أخطاء شائعة

- **نسيان أن العد يبدأ من صفر:** آخر عنصر هو `$a[count($a) - 1]` وليس `$a[count($a)]`.
- **مفتاح غير موجود:** `$student["phone"]` بدون فحص يعطي `Warning: Undefined array key`. استخدم `??` أو `isset`.
- **طباعة مصفوفة بـ `echo`:** `echo $fruits;` تطبع كلمة `Array` فقط مع تحذير. استخدم `implode` أو `print_r` أو `var_dump`.
- **`sort` لا تُرجع المصفوفة:** `$x = sort($a);` يضع في `$x` القيمة `true`! الترتيب يحدث على `$a` نفسها.

## تمارين

### تمرين 1: متوسط الدرجات

احسب متوسط الدرجات `[80, 95, 70, 85]` واطبع: `المتوسط: 82.5`.

```php exercise
<?php
$grades = [80, 95, 70, 85];
// array_sum و count
```

```php solution
<?php
$grades = [80, 95, 70, 85];
$avg = array_sum($grades) / count($grades);
echo "المتوسط: $avg\n";
```

```text output
المتوسط: 82.5
```

### تمرين 2: دليل الهاتف

لديك مصفوفة ترابطية (الاسم => الرقم). اطبع كل سطر بالشكل `علي: 0100`.

```php exercise
<?php
$phones = ["علي" => "0100", "منى" => "0111", "كريم" => "0122"];
// foreach ($phones as $name => $number)
```

```php solution
<?php
$phones = ["علي" => "0100", "منى" => "0111", "كريم" => "0122"];
foreach ($phones as $name => $number) {
    echo "$name: $number\n";
}
```

```text output
علي: 0100
منى: 0111
كريم: 0122
```

### تمرين 3: الناجحون فقط

من المصفوفة التالية اختر الطلاب الذين درجاتهم 50 فأكثر واطبع أسماءهم مفصولة بفاصلة ومسافة.

```php exercise
<?php
$results = ["هدى" => 88, "سامي" => 45, "ريم" => 73, "عمر" => 30];
```

```php solution
<?php
$results = ["هدى" => 88, "سامي" => 45, "ريم" => 73, "عمر" => 30];
$passed = array_filter($results, fn($d) => $d >= 50);
echo implode(", ", array_keys($passed)), "\n";
```

```text output
هدى, ريم
```

## اختبر نفسك

```quiz
{"question": "ما هو `$a[1]` إذا كانت `$a = [\"x\", \"y\", \"z\"]` ؟", "choices": ["x", "y", "z", "خطأ"], "answer": 1, "explanation": "الترقيم يبدأ من صفر: $a[0] = x و $a[1] = y."}
```

```quiz
{"question": "أي دالة تحوّل النص \"a,b,c\" إلى مصفوفة؟", "choices": ["implode", "explode", "array_map", "count"], "answer": 1, "explanation": "explode تقسم النص عند الفاصل، و implode تفعل العكس."}
```

```quiz
{"question": "ماذا تفعل array_filter ؟", "choices": ["ترتّب العناصر", "تختار العناصر التي تحقق شرطًا", "تحذف المصفوفة", "تحوّل كل عنصر"], "answer": 1, "explanation": "array_filter مصفاة: تُبقي العناصر التي تُرجع لها الدالة true."}
```

## الخلاصة

- المصفوفة المرقّمة تبدأ من 0، والترابطية مفاتيحها أسماء.
- `foreach ($arr as $key => $value)` أسهل طريقة للمرور على أي مصفوفة.
- `count` و`in_array` و`sort` و`implode` و`explode` و`array_map` و`array_filter` من أكثر الدوال استخدامًا.
- قائمة من المصفوفات الترابطية = جدول بيانات، وهي الشكل الذي ستصلنا به صفوف قاعدة البيانات.
