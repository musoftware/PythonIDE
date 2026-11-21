# الدرس 4: المصفوفات وجداول التجزئة (Hashtables)

نحتاج كثيرًا إلى حفظ **مجموعة** من القيم: قائمة أسماء، أو إعدادات برنامج. في PowerShell أداتان: **المصفوفة** (array) و**جدول التجزئة** (hashtable، وهو قاموس: مفتاح وقيمة).

> **تشبيه:** المصفوفة مثل **رف كتب مرقم**، تأخذ الكتاب رقم 3. وجدول التجزئة مثل **فهرس المكتبة**: تبحث باسم الكتاب فتجد مكانه.

## المصفوفة

```powershell run
$fruits = "تفاح", "موز", "برتقال"
$fruits[0]
$fruits[-1]
$fruits.Count
$fruits -join " | "
$nums = @(5, 3, 8)
$empty = @()
"عدد العناصر: $($nums.Count) و $($empty.Count)"
```

```text output
تفاح
برتقال
3
تفاح | موز | برتقال
عدد العناصر: 3 و 0
```

- القيم المفصولة بفواصل تصنع مصفوفة، و`@( )` طريقة صريحة لذلك (و`@()` مصفوفة فارغة).
- الفهرس يبدأ من **0**، و`-1` للأخير، و`.Count` العدد.
- `-join` تلصق العناصر بفاصل، وعكسها `-split`.

## الإضافة والتعديل

```powershell run
$nums = @(5, 3, 8)
$nums += 10
$nums[0] = 50
"$nums"
$nums -contains 8
8 -in $nums
$sorted = $nums | Sort-Object
"$sorted"
$desc = $nums | Sort-Object -Descending
"$desc"
"$($nums[1..2])"
```

```text output
50 3 8 10
True
True
3 8 10 50
50 10 8 3
3 8
```

- `+=` تضيف عنصرًا (في الحقيقة تنشئ مصفوفة جديدة؛ هذا بطيء مع الآلاف، لكنه مريح للقوائم الصغيرة).
- `-contains` و`-in` لفحص وجود قيمة.
- `$nums[1..2]` شريحة من العنصر 1 إلى 2.
- `"$nums"` داخل علامتي التنصيص تطبع العناصر بينها مسافات.

## قائمة قابلة للنمو: `List`

إذا كنت ستضيف عناصر كثيرة، فاستخدم قائمة من .NET:

```powershell run
$list = [System.Collections.Generic.List[string]]::new()
$list.Add("علي")
$list.Add("منى")
$list.Insert(0, "خالد")
[void]$list.Remove("علي")
$list.Count
$list -join ", "
```

```text output
2
خالد, منى
```

`[void]` تتجاهل القيمة التي يُرجعها `Remove` (وإلا ستُطبع `True`).

## جدول التجزئة (`Hashtable`)

```powershell run
$ages = @{ "علي" = 20; "منى" = 22 }
$ages["خالد"] = 19
$ages.Count
$ages["منى"]
$ages.ContainsKey("سعيد")
$ages.Remove("علي")
foreach ($name in $ages.Keys | Sort-Object) {
    "$name => $($ages[$name])"
}
```

```text output
3
22
False
خالد => 19
منى => 22
```

- الصيغة: `@{ مفتاح = قيمة; مفتاح = قيمة }`.
- `$h["key"]` للقراءة والكتابة، و`.Keys` و`.Values` و`.ContainsKey()` و`.Remove()`.
- ترتيب المفاتيح غير مضمون؛ لذلك رتبناها بـ `Sort-Object`.

### المفاتيح الإنجليزية والنقطة

```powershell run
$config = @{ Server = "db01"; Port = 5432; Debug = $false }
$config.Server
$config.Port + 1
$config.Debug = $true
"Debug = $($config.Debug)"
```

```text output
db01
5433
Debug = True
```

مع المفاتيح الإنجليزية يمكنك أن تكتب `$config.Server` بدل `$config["Server"]`.

## جدول مرتب: `[ordered]`

```powershell run
$week = [ordered]@{ "السبت" = 3; "الأحد" = 5; "الاثنين" = 2 }
foreach ($day in $week.Keys) {
    "$day : $($week[$day]) مهام"
}
```

```text output
السبت : 3 مهام
الأحد : 5 مهام
الاثنين : 2 مهام
```

`[ordered]@{ }` يحفظ ترتيب الإضافة.

## مثال: عدّ تكرار الكلمات

```powershell run
$text = "قط كلب قط عصفور كلب قط"
$counts = [ordered]@{}
foreach ($w in $text -split " ") {
    if ($counts.Contains($w)) { $counts[$w]++ } else { $counts[$w] = 1 }
}
foreach ($w in $counts.Keys) { "${w}: $($counts[$w])" }
```

```text output
قط: 3
كلب: 2
عصفور: 1
```

لاحظ `"${w}: ..."`: الأقواس المعقوصة حول اسم المتغير تمنع PowerShell من ظن أن `w:` جزء من الاسم (لأن `:` لها معنى خاص بعد اسم المتغير).

## أخطاء شائعة

### مصفوفة من عنصر واحد

إذا أرجع أمر عنصرًا واحدًا فقد تحصل على العنصر نفسه وليس مصفوفة، فيصبح `.Count` غير متوقع في الإصدارات القديمة. اكتب `@(...)` حول الناتج لتضمن مصفوفة: `$files = @(Get-ChildItem *.txt)`.

### الخلط بين `-contains` و`-like`

`"تفاح موز" -contains "موز"` تعطي `False`، لأن `-contains` للمصفوفات وليست للنصوص. للبحث في نص استخدم `-like "*موز*"` أو `.Contains("موز")`.

## تمارين

### التمرين 1

اقرأ 5 أعداد (كل عدد في سطر) في مصفوفة، واطبع الأكبر والأصغر والمتوسط بمنزلة واحدة. (`Measure-Object` ستأتي في درس قادم؛ استخدم حلقة هنا.)

```powershell exercise
$nums = @()
foreach ($i in 1..5) { $nums += [int][Console]::ReadLine() }
```

```powershell solution
$nums = @()
foreach ($i in 1..5) { $nums += [int][Console]::ReadLine() }
$max = $nums[0]; $min = $nums[0]; $sum = 0
foreach ($n in $nums) {
    if ($n -gt $max) { $max = $n }
    if ($n -lt $min) { $min = $n }
    $sum += $n
}
"الأكبر: $max"
"الأصغر: $min"
"المتوسط: {0:F1}" -f ($sum / $nums.Count)
```

```text input
12
5
30
18
9
```

```text output
الأكبر: 30
الأصغر: 5
المتوسط: 14.8
```

### التمرين 2

جدول تجزئة لأسعار المنتجات. اقرأ اسم منتج واطبع سعره أو `غير موجود`.

```powershell exercise
$prices = @{ "قلم" = 5; "دفتر" = 20; "حقيبة" = 150 }
$item = [Console]::ReadLine()
```

```powershell solution
$prices = @{ "قلم" = 5; "دفتر" = 20; "حقيبة" = 150 }
$item = [Console]::ReadLine()
if ($prices.ContainsKey($item)) {
    "سعر $item = $($prices[$item]) جنيه"
} else {
    "غير موجود"
}
```

```text input
حقيبة
```

```text output
سعر حقيبة = 150 جنيه
```

## اختبر نفسك

```quiz
{"question": "كيف تنشئ جدول تجزئة في PowerShell؟", "choices": ["{ a = 1 }", "@{ a = 1 }", "[ a = 1 ]", "( a = 1 )"], "answer": 1, "explanation": "جدول التجزئة يُكتب @{ مفتاح = قيمة }."}
```

```quiz
{"question": "ما ناتج (1, 2, 3) -contains 2؟", "choices": ["True", "False", "2", "خطأ"], "answer": 0, "explanation": "-contains تفحص وجود قيمة في مصفوفة."}
```

```quiz
{"question": "لماذا نستخدم [ordered]@{ }؟", "choices": ["لتسريع الجدول", "ليحفظ ترتيب إضافة المفاتيح", "لترتيبه أبجديًا", "لمنع التعديل"], "answer": 1, "explanation": "الجدول العادي لا يضمن الترتيب، و[ordered] يحفظ ترتيب الإضافة."}
```

## الخلاصة

- المصفوفة `1, 2, 3` أو `@(...)`، وفهرسها من 0، و`.Count` و`+=` و`-join` و`-contains`.
- للقوائم الكبيرة استخدم `List[...]` من .NET.
- جدول التجزئة `@{ k = v }`، و`[ordered]` لحفظ الترتيب.
- `.Keys` و`.ContainsKey()` و`.Remove()`، و`"${var}:"` عند الحاجة.
