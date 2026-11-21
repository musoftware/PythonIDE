# الدرس 6: الكائنات والأوامر الجاهزة (Cmdlets)

في معظم لغات سطر الأوامر يمرر كل أمر **نصًا** للأمر التالي، فتضطر إلى تقطيع النص لتستخرج ما تريد. أما في PowerShell فكل أمر يمرر **كائنات** لها **خصائص** (properties) و**دوال** (methods). هذه أهم فكرة في اللغة.

> **تشبيه:** النص مثل **وصف شفهي** لسيارة: «سيارة حمراء موديل 2020». أما الكائن فمثل **السيارة نفسها**: تفتح الباب، وتقرأ عداد الكيلومترات، وتعرف لونها بدقة دون أن تفسر كلامًا.

## خصائص الكائن ودواله

```powershell run
$d = Get-Date -Year 2026 -Month 11 -Day 21 -Hour 9 -Minute 30
$d.Year
$d.Month
$d.DayOfYear
$d.AddDays(10).ToString("yyyy-MM-dd")
$d.ToString("HH:mm")
$text = "PowerShell"
$text.Length
$text.ToUpper()
$text.Substring(0, 5)
$text.Replace("Shell", " Tools")
```

```text output
2026
11
325
2026-12-01
09:30
10
POWERSHELL
Power
Power Tools
```

- `$obj.Property` تقرأ خاصية، و`$obj.Method(...)` تستدعي دالة (والدوال تحتاج أقواسًا).
- `Get-Member` تعرض كل خصائص ودوال أي كائن: جرّب في **Terminal**: `Get-Date | Get-Member`.

## صنع كائناتك: `[pscustomobject]`

```powershell run
$students = @(
    [pscustomobject]@{ Name = "علي";  Score = 80; City = "القاهرة" }
    [pscustomobject]@{ Name = "منى";  Score = 95; City = "الإسكندرية" }
    [pscustomobject]@{ Name = "خالد"; Score = 67; City = "القاهرة" }
)

$students[1].Name
$students | Where-Object { $_.Score -ge 70 } | ForEach-Object { "$($_.Name) ناجح بتقدير عالٍ" }
$best = $students | Sort-Object Score -Descending | Select-Object -First 1
"الأول: $($best.Name) ($($best.Score))"
$avg = ($students | Measure-Object -Property Score -Average).Average
"المتوسط: {0:F1}" -f $avg
```

```text output
منى
علي ناجح بتقدير عالٍ
منى ناجح بتقدير عالٍ
الأول: منى (95)
المتوسط: 80.7
```

لاحظ كيف نرتب ونفلتر **بأسماء الخصائص** مباشرة: `Sort-Object Score` و`Measure-Object -Property Score`. لا تقطيع نصوص!

## `Select-Object` و`Group-Object`

```powershell run
$students = @(
    [pscustomobject]@{ Name = "علي";  Score = 80; City = "القاهرة" }
    [pscustomobject]@{ Name = "منى";  Score = 95; City = "الإسكندرية" }
    [pscustomobject]@{ Name = "خالد"; Score = 67; City = "القاهرة" }
)

$students | Select-Object -ExpandProperty Name
"---"
$students | Group-Object City | ForEach-Object { "$($_.Name): $($_.Count) طالب" }
"---"
$students | Select-Object Name, @{ Name = "Grade"; Expression = { if ($_.Score -ge 90) { "A" } else { "B" } } } |
    ForEach-Object { "$($_.Name) = $($_.Grade)" }
```

```text output
علي
منى
خالد
---
القاهرة: 2 طالب
الإسكندرية: 1 طالب
---
علي = B
منى = A
خالد = B
```

- `Select-Object -ExpandProperty Name` تُخرج قيم خاصية واحدة.
- `Group-Object City` تجمع الكائنات حسب قيمة خاصية، ولكل مجموعة `Name` و`Count` و`Group`.
- `@{ Name = "..."; Expression = { ... } }` تضيف **خاصية محسوبة** جديدة.

## العرض في جدول: `Format-Table`

```powershell run
$items = @(
    [pscustomobject]@{ Item = "Pen"; Qty = 10; Price = 5 }
    [pscustomobject]@{ Item = "Book"; Qty = 4; Price = 20 }
)
$items | Format-Table -AutoSize | Out-String -Width 60
```

```text output
Item Qty Price
---- --- -----
Pen   10     5
Book   4    20
```

`Format-Table` و`Format-List` للعرض على الشاشة فقط، وتأتي في **آخر** خط الأنابيب (بعدها لا تبقى كائنات حقيقية). وPowerShell تعرض الكائنات كجدول تلقائيًا إذا كتبت `$items` وحدها.

## أوامر جاهزة مفيدة

| الأمر | وظيفته |
|---|---|
| `Get-Date` | التاريخ والوقت |
| `Get-ChildItem` | محتويات مجلد (ملفات ومجلدات) |
| `Get-Content` / `Set-Content` | قراءة ملف / كتابته |
| `Get-Process` | البرامج التي تعمل |
| `Get-Service` | خدمات ويندوز |
| `Get-Random` | رقم عشوائي |
| `Test-Path` | هل المسار موجود؟ |
| `Get-Command` | ابحث عن أمر: `Get-Command *file*` |
| `Get-Help` | شرح أي أمر: `Get-Help Get-ChildItem -Examples` |

## مثال: الملفات في مجلد

```powershell run
New-Item -ItemType Directory -Path "demo" -Force | Out-Null
Set-Content -Path "demo\a.txt" -Value "abc"
Set-Content -Path "demo\b.txt" -Value ("x" * 500)
Set-Content -Path "demo\c.log" -Value "log"

Get-ChildItem demo | Sort-Object Name | ForEach-Object { "{0} - {1} بايت" -f $_.Name, $_.Length }
"---"
$txt = @(Get-ChildItem demo -Filter *.txt)
"ملفات txt: $($txt.Count)"
$size = (Get-ChildItem demo | Measure-Object -Property Length -Sum).Sum
"الحجم الكلي: $size بايت"
Remove-Item demo -Recurse
Test-Path demo
```

```text output
a.txt - 5 بايت
b.txt - 502 بايت
c.log - 5 بايت
---
ملفات txt: 2
الحجم الكلي: 512 بايت
False
```

- `Get-ChildItem` تُرجع كائنات ملفات لها `Name` و`Length` (الحجم) و`Extension` و`LastWriteTime`.
- `Set-Content` يضيف سطرًا جديدًا (بايتين) في آخر الملف، لذلك `abc` حجمه 5.
- `| Out-Null` تخفي الناتج الذي لا نريده.

> **تنبيه:** `Remove-Item -Recurse` تحذف المجلد وكل ما فيه **نهائيًا** (لا تذهب إلى سلة المحذوفات). جرّب الأوامر الخطرة أولًا مع `-WhatIf` لترى ماذا ستفعل دون أن تفعله: `Remove-Item demo -Recurse -WhatIf`.

## أخطاء شائعة

### استخدام `Format-Table` في منتصف الأنبوب

`Get-ChildItem | Format-Table | Sort-Object Name` لا تعمل كما تتوقع، لأن `Format-Table` تحوّل الكائنات إلى أوامر عرض. ضع `Format-*` دائمًا في **النهاية**.

### نسيان الأقواس مع الدوال

`$text.ToUpper` بدون أقواس تعرض **وصف الدالة** بدل تنفيذها. اكتب `$text.ToUpper()`.

## تمارين

### التمرين 1

لديك قائمة منتجات. اطبع أسماء المنتجات التي سعرها أكثر من 50 مرتبة من الأغلى، ثم مجموع أسعارها.

```powershell exercise
$products = @(
    [pscustomobject]@{ Name = "شاشة"; Price = 3000 }
    [pscustomobject]@{ Name = "ماوس"; Price = 150 }
    [pscustomobject]@{ Name = "كابل"; Price = 40 }
    [pscustomobject]@{ Name = "لوحة مفاتيح"; Price = 400 }
)
```

```powershell solution
$products = @(
    [pscustomobject]@{ Name = "شاشة"; Price = 3000 }
    [pscustomobject]@{ Name = "ماوس"; Price = 150 }
    [pscustomobject]@{ Name = "كابل"; Price = 40 }
    [pscustomobject]@{ Name = "لوحة مفاتيح"; Price = 400 }
)
$expensive = $products | Where-Object { $_.Price -gt 50 } | Sort-Object Price -Descending
$expensive | ForEach-Object { $_.Name }
"المجموع: $(($expensive | Measure-Object -Property Price -Sum).Sum)"
```

```text output
شاشة
لوحة مفاتيح
ماوس
المجموع: 3550
```

### التمرين 2

جمّع الكلمات التالية حسب طولها بـ `Group-Object`، واطبع لكل طول عدد الكلمات وأسماءها: `3: cat, dog`.

```powershell exercise
$words = "cat", "horse", "dog", "bird", "fish", "lion"
```

```powershell solution
$words = "cat", "horse", "dog", "bird", "fish", "lion"
$words | Group-Object Length | Sort-Object { [int]$_.Name } | ForEach-Object {
    "$($_.Name): $($_.Group -join ', ')"
}
```

```text output
3: cat, dog
4: bird, fish, lion
5: horse
```

## اختبر نفسك

```quiz
{"question": "ما الذي يمرره الأمر في PowerShell عبر الأنبوب؟", "choices": ["نصوصًا فقط", "كائنات لها خصائص ودوال", "أرقامًا فقط", "ملفات"], "answer": 1, "explanation": "PowerShell تمرر كائنات .NET، فتصل إلى خصائصها مباشرة."}
```

```quiz
{"question": "كيف تعرف كل خصائص ودوال كائن ما؟", "choices": ["Get-Help", "Get-Member", "Get-Content", "Get-Date"], "answer": 1, "explanation": "Get-Member تعرض أعضاء الكائن: خصائصه ودواله."}
```

```quiz
{"question": "أين يوضع Format-Table في خط الأنابيب؟", "choices": ["في البداية", "في المنتصف", "في النهاية", "لا يهم"], "answer": 2, "explanation": "أوامر Format-* للعرض فقط وتأتي في النهاية."}
```

## الخلاصة

- كل شيء كائن: `$obj.Property` و`$obj.Method()`، و`Get-Member` لاكتشافه.
- `[pscustomobject]@{ ... }` لصنع كائناتك.
- `Sort-Object` و`Where-Object` و`Measure-Object` و`Group-Object` و`Select-Object` تعمل بأسماء الخصائص.
- `Get-ChildItem` و`Get-Content` و`Set-Content` و`Test-Path` للملفات، و`-WhatIf` للتجربة الآمنة.
