# الدرس 3: الشروط وحلقات التكرار

السكربت المفيد **يقرر** (الشروط) و**يكرر** (الحلقات): «لكل ملف في المجلد، إذا كان أقدم من شهر فانقله إلى الأرشيف». هذا بالضبط ما نتعلمه اليوم.

> **تشبيه:** حلقة التكرار مثل **ساعي البريد** الذي يمر على البيوت بيتًا بيتًا، والشرط مثل قراره عند كل بيت: «هل لهذا البيت رسالة؟ إذا نعم فاتركها».

## `if` و`elseif` و`else`

```powershell run
$score = 88
if ($score -ge 90) {
    "ممتاز"
} elseif ($score -ge 75) {
    "جيد جدًا"
} elseif ($score -ge 50) {
    "مقبول"
} else {
    "راسب"
}
```

```text output
جيد جدًا
```

الشرط بين قوسين `( )`، والجسم بين أقواس معقوصة `{ }`، وتُكتب `elseif` كلمة واحدة.

## العوامل المنطقية

```powershell run
$age = 20
$member = $true
if ($age -ge 18 -and $member) { "مسموح بالدخول" }
$day = "الجمعة"
if ($day -eq "الجمعة" -or $day -eq "السبت") { "عطلة" }
if (-not ($age -lt 18)) { "بالغ" }
if (!$false) { "علامة ! تعني not أيضًا" }
```

```text output
مسموح بالدخول
عطلة
بالغ
علامة ! تعني not أيضًا
```

## `switch`: اختيار من قيم كثيرة

```powershell run
$month = 4
switch ($month) {
    { $_ -in 12, 1, 2 } { "الشتاء" }
    { $_ -in 3..5 }     { "الربيع" }
    { $_ -in 6..8 }     { "الصيف" }
    default             { "الخريف" }
}

$file = "photo.JPG"
switch -Wildcard ($file) {
    "*.txt" { "ملف نصي" }
    "*.jpg" { "صورة" }
    default { "نوع آخر" }
}
```

```text output
الربيع
صورة
```

- داخل `switch` يمثل `$_` القيمة التي نفحصها.
- الشرط يمكن أن يكون قيمة ثابتة، أو كتلة `{ }` فيها شرط، أو نمطًا مع `-Wildcard`.
- `3..5` **مدى** يعطي 3 و4 و5، و`-in` تفحص هل القيمة داخل القائمة.

## حلقة `for`

```powershell run
for ($i = 1; $i -le 3; $i++) {
    "الدورة $i"
}
for ($i = 10; $i -gt 0; $i -= 4) {
    Write-Host $i -NoNewline
    Write-Host " " -NoNewline
}
Write-Host ""
```

```text output
الدورة 1
الدورة 2
الدورة 3
10 6 2 
```

الصيغة: `for (بداية; شرط; خطوة) { ... }`.

## حلقة `foreach`

```powershell run
foreach ($fruit in "تفاح", "موز", "عنب") {
    "أحب $fruit"
}
$total = 0
foreach ($n in 1..100) {
    $total += $n
}
"مجموع 1 إلى 100 = $total"
```

```text output
أحب تفاح
أحب موز
أحب عنب
مجموع 1 إلى 100 = 5050
```

`foreach ($item in قائمة)` أشهر حلقة في PowerShell، لأن السكربتات تمر عادة على قوائم: ملفات، مستخدمين، أجهزة.

## `while` و`do ... until`

```powershell run
$balance = 1000
$years = 0
while ($balance -lt 2000) {
    $balance *= 1.1
    $years++
}
"يتضاعف المبلغ بعد $years سنوات"

$n = 3
do {
    "العد: $n"
    $n--
} until ($n -eq 0)
"انطلق!"
```

```text output
يتضاعف المبلغ بعد 8 سنوات
العد: 3
العد: 2
العد: 1
انطلق!
```

- `while` تفحص الشرط أولًا (قد لا تُنفذ أبدًا).
- `do { } until (...)` تُنفذ مرة على الأقل ثم تكرر **حتى** يصبح الشرط صحيحًا. وتوجد أيضًا `do { } while (...)`.

## `break` و`continue`

```powershell run
foreach ($i in 1..10) {
    if ($i % 2 -eq 0) { continue }   # تخطَّ الزوجي
    if ($i -gt 7) { break }          # توقف
    Write-Host "$i " -NoNewline
}
Write-Host ""
```

```text output
1 3 5 7 
```

## مثال: لعبة تخمين

```powershell run
$secret = 42
$tries = 0
while ($true) {
    $guess = [int][Console]::ReadLine()
    $tries++
    if ($guess -eq $secret) {
        "أحسنت! عرفته في $tries محاولات"
        break
    }
    if ($guess -lt $secret) { "أكبر" } else { "أصغر" }
}
```

```text input
50
30
42
```

```text output
أصغر
أكبر
أحسنت! عرفته في 3 محاولات
```

## أخطاء شائعة

### `else if` بمسافة

`else if` تعمل في PowerShell، لكن `elseif` أوضح وهي المعتادة.

### نسيان أن `$_` خاصة بالحلقات والأنابيب

`$_` تعمل داخل `switch` و`ForEach-Object` و`Where-Object`، لكنها لا تعني شيئًا داخل `foreach ($x in ...)`؛ هناك استخدم اسم المتغير `$x`.

### المقارنة بالرموز

`if ($a == $b)` خطأ: `==` ليست عاملًا في PowerShell. استخدم `-eq`.

## تمارين

### التمرين 1

اطبع جدول الضرب للعدد المقروء من 1 إلى 5 بالشكل `6 x 3 = 18`.

```powershell exercise
$n = [int][Console]::ReadLine()
```

```powershell solution
$n = [int][Console]::ReadLine()
foreach ($i in 1..5) {
    "$n x $i = $($n * $i)"
}
```

```text input
6
```

```text output
6 x 1 = 6
6 x 2 = 12
6 x 3 = 18
6 x 4 = 24
6 x 5 = 30
```

### التمرين 2

FizzBuzz: اطبع الأعداد من 1 إلى 15، لكن اطبع `Fizz` بدل مضاعفات 3، و`Buzz` بدل مضاعفات 5، و`FizzBuzz` بدل مضاعفات الاثنين.

```powershell exercise
foreach ($i in 1..15) {
}
```

```powershell solution
foreach ($i in 1..15) {
    if ($i % 15 -eq 0) { "FizzBuzz" }
    elseif ($i % 3 -eq 0) { "Fizz" }
    elseif ($i % 5 -eq 0) { "Buzz" }
    else { $i }
}
```

```text output
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

## اختبر نفسك

```quiz
{"question": "ماذا يعطي المدى 2..5؟", "choices": ["2 و5", "2، 3، 4، 5", "2، 3، 4", "خطأ"], "answer": 1, "explanation": "المدى يشمل البداية والنهاية."}
```

```quiz
{"question": "ما الذي يمثله $_ داخل switch؟", "choices": ["آخر خطأ", "القيمة التي يفحصها switch", "رقم السطر", "لا شيء"], "answer": 1, "explanation": "$_ هو الكائن الحالي، وفي switch هو القيمة المفحوصة."}
```

```quiz
{"question": "أي حلقة تُنفذ مرة واحدة على الأقل؟", "choices": ["while", "for", "do ... until", "foreach"], "answer": 2, "explanation": "do تفحص الشرط في النهاية."}
```

## الخلاصة

- `if (...) { } elseif (...) { } else { }` مع `-and` و`-or` و`-not`.
- `switch` مع قيم أو شروط أو `-Wildcard`، و`$_` القيمة الحالية.
- `for` و`foreach ($x in ...)` و`while` و`do ... until`.
- `break` و`continue`، و`1..10` للمدى.
