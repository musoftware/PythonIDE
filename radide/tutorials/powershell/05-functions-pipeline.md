# الدرس 5: الدوال وخط الأنابيب (Pipeline)

**الدالة** (function) مجموعة أوامر لها اسم. و**خط الأنابيب** (pipeline) هو قلب PowerShell: العلامة `|` تمرر ناتج أمر إلى أمر آخر، فتبني من أوامر صغيرة عملًا كبيرًا.

> **تشبيه:** خط الأنابيب مثل **خط الإنتاج في مصنع**: العامل الأول يقطع الخشب، ويمرره للثاني فيصقله، ثم للثالث فيدهنه. كل عامل يتقن شيئًا واحدًا، والنتيجة كرسي كامل.

## دالة بسيطة

```powershell run
function Say-Hello {
    "أهلًا بك!"
}

function Get-Square($x) {
    return $x * $x
}

Say-Hello
Get-Square 7
Get-Square -x 9
```

```text output
أهلًا بك!
49
81
```

- العُرف أن يكون اسم الدالة **فعل-اسم** مثل الأوامر الجاهزة.
- **مهم:** الاستدعاء بدون أقواس ولا فواصل: `Get-Square 7`. أما `Get-Square(7)` فتعمل هنا بالصدفة، لكن `Add-Numbers(2, 3)` ستمرر **مصفوفة واحدة** وليس رقمين!

## المعاملات بـ `param`

```powershell run
function Get-Total {
    param(
        [double]$Price,
        [int]$Quantity = 1,
        [switch]$WithTax
    )
    $total = $Price * $Quantity
    if ($WithTax) { $total *= 1.14 }
    return [math]::Round($total, 2)
}

Get-Total -Price 100
Get-Total -Price 100 -Quantity 3
Get-Total -Price 100 -Quantity 3 -WithTax
Get-Total 50 2
```

```text output
100
300
342
100
```

- `param( ... )` تعرّف المعاملات بأنواعها وقيمها الافتراضية.
- `[switch]` معامل مفتاح: وجوده يعني `$true` (مثل `-WithTax`).
- يمكن تمرير القيم بالاسم `-Price 100` أو بالترتيب `50 2`.

## كل ما يُطبع يُرجَع!

نقطة تفاجئ المبتدئين: الدالة في PowerShell تُرجع **كل** ما يخرج منها، وليس فقط ما بعد `return`:

```powershell run
function Test-Output {
    "سطر أول"
    $x = 5          # الإسناد لا يُخرج شيئًا
    "سطر ثانٍ"
    return 42
}

$result = Test-Output
$result.Count
$result[0]
$result[-1]
```

```text output
3
سطر أول
42
```

لذلك: إذا استدعيت داخل دالتك أمرًا يُرجع قيمة لا تريدها، اكتب قبله `[void]` أو `$null =`.

## خط الأنابيب `|`

```powershell run
1..10 | Where-Object { $_ % 2 -eq 0 }
"---"
1..5 | ForEach-Object { $_ * $_ }
"---"
5, 3, 9, 1 | Sort-Object -Descending | Select-Object -First 2
"---"
1..100 | Measure-Object -Sum -Average -Maximum | ForEach-Object { "المجموع $($_.Sum)، المتوسط $($_.Average)، الأكبر $($_.Maximum)" }
```

```text output
2
4
6
8
10
---
1
4
9
16
25
---
9
5
---
المجموع 5050، المتوسط 50.5، الأكبر 100
```

| الأمر | وظيفته |
|---|---|
| `Where-Object { شرط }` | يمرر العناصر التي تحقق الشرط فقط (فلترة) |
| `ForEach-Object { ... }` | ينفذ الكتلة على كل عنصر |
| `Sort-Object` | يرتب |
| `Select-Object -First n` | يأخذ أول `n` عناصر |
| `Measure-Object -Sum -Average` | يحسب الإحصائيات |

و`$_` (أو `$PSItem`) هي **العنصر الحالي** الذي يمر في الأنبوب.

## اختصارات شائعة

ستجد في سكربتات الآخرين أسماء مختصرة: `?` تعني `Where-Object`، و`%` تعني `ForEach-Object`، و`sort` تعني `Sort-Object`. هي مريحة في الطرفية، لكن **اكتب الأسماء الكاملة في السكربتات** لتكون مقروءة.

## دالة تستقبل من الأنبوب

```powershell run
function Add-Tax {
    param([Parameter(ValueFromPipeline)][double]$Price)
    process {
        [math]::Round($Price * 1.14, 2)
    }
}

100, 250, 80 | Add-Tax
"---"
100, 250, 80 | Add-Tax | Measure-Object -Sum | ForEach-Object { "الإجمالي بعد الضريبة: $($_.Sum)" }
```

```text output
114
285
91.2
---
الإجمالي بعد الضريبة: 490.2
```

- `[Parameter(ValueFromPipeline)]` تقول: «هذا المعامل يأتي من الأنبوب».
- الكتلة `process { }` تُنفذ **مرة لكل عنصر** يصل من الأنبوب.

## النطاق: `$script:`

```powershell run
$count = 0
function Add-One { $count++ }            # تعدّل نسخة محلية!
function Add-OneScript { $script:count++ }

Add-One; Add-One
"بعد Add-One: $count"
Add-OneScript; Add-OneScript
"بعد Add-OneScript: $count"
```

```text output
بعد Add-One: 0
بعد Add-OneScript: 2
```

الدالة ترى متغيرات السكربت للقراءة، لكن إذا غيّرتها تنشئ نسخة محلية. لتعديل متغير السكربت نفسه اكتب `$script:count`. سنحتاج هذا كثيرًا في النوافذ الرسومية.

## أخطاء شائعة

### الاستدعاء بأقواس وفواصل

<!-- compile-error -->
```powershell
function Add-Numbers($a, $b) { $a + $b }
Add-Numbers(2, 3)
```

النتيجة ليست `5`! `(2, 3)` مصفوفة واحدة تذهب إلى `$a`. الصحيح: `Add-Numbers 2 3`.

### مخرجات غير مقصودة

إذا أرجعت دالتك أكثر مما تتوقع، فابحث عن أمر داخلها يُخرج قيمة (مثل `$list.Add(...)` في بعض القوائم)، وضع قبله `[void]`.

## تمارين

### التمرين 1

اكتب دالة `Get-Grade` تأخذ `-Score` وتُرجع `ممتاز` (90 فأكثر) أو `جيد` (70 فأكثر) أو `مقبول` (50 فأكثر) أو `راسب`. ثم استدعها لثلاث درجات.

```powershell exercise
function Get-Grade {
    param([int]$Score)
}

Get-Grade -Score 95
Get-Grade -Score 72
Get-Grade -Score 30
```

```powershell solution
function Get-Grade {
    param([int]$Score)
    if ($Score -ge 90) { return "ممتاز" }
    if ($Score -ge 70) { return "جيد" }
    if ($Score -ge 50) { return "مقبول" }
    return "راسب"
}

Get-Grade -Score 95
Get-Grade -Score 72
Get-Grade -Score 30
```

```text output
ممتاز
جيد
راسب
```

### التمرين 2

باستخدام خط أنابيب واحد: من الأعداد 1 إلى 20، خذ مضاعفات 3، وربّع كل منها، ثم اطبع مجموعها.

```powershell exercise
# 1..20 | ...
```

```powershell solution
1..20 | Where-Object { $_ % 3 -eq 0 } | ForEach-Object { $_ * $_ } |
    Measure-Object -Sum | ForEach-Object { "المجموع: $($_.Sum)" }
```

```text output
المجموع: 819
```

يمكن كسر خط الأنابيب الطويل على عدة أسطر بعد العلامة `|`.

## اختبر نفسك

```quiz
{"question": "كيف تستدعي الدالة Add-Numbers مع 2 و3؟", "choices": ["Add-Numbers(2, 3)", "Add-Numbers 2 3", "Add-Numbers[2, 3]", "Add-Numbers{2 3}"], "answer": 1, "explanation": "المعاملات تُمرر مفصولة بمسافات وبدون أقواس."}
```

```quiz
{"question": "ماذا تفعل Where-Object { $_ -gt 5 }؟", "choices": ["تحذف كل العناصر", "تمرر فقط العناصر الأكبر من 5", "ترتب العناصر", "تجمع العناصر"], "answer": 1, "explanation": "Where-Object فلتر يمرر العناصر التي تحقق الشرط."}
```

```quiz
{"question": "لماذا نكتب $script:count داخل الدالة؟", "choices": ["لتسريعها", "لتعديل متغير السكربت نفسه وليس نسخة محلية", "لطباعة المتغير", "لحذفه"], "answer": 1, "explanation": "بدون script: تنشئ الدالة متغيرًا محليًا بنفس الاسم."}
```

## الخلاصة

- `function Verb-Noun { param(...) ... }` واستدعاؤها بلا أقواس: `Verb-Noun -Name قيمة`.
- الدالة تُرجع كل ما يخرج منها؛ استخدم `[void]` لإخفاء ما لا تريد.
- `|` يمرر الكائنات: `Where-Object` و`ForEach-Object` و`Sort-Object` و`Select-Object` و`Measure-Object`.
- `$_` العنصر الحالي، و`process { }` لدوال الأنابيب، و`$script:` لمتغيرات السكربت.
