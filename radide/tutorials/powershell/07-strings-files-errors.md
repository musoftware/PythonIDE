# الدرس 7: النصوص والملفات ومعالجة الأخطاء

الأتمتة الحقيقية تعني: قراءة ملفات، وتعديل نصوص، والتعامل مع ما يفشل. في هذا الدرس نجمع الثلاثة.

> **تشبيه:** معالجة الأخطاء مثل **خطة بديلة في الرحلة**: «إذا كان القطار متأخرًا، نأخذ الحافلة». السكربت الجيد لا يتوقف عند أول مشكلة، بل يعرف ماذا يفعل.

## عمليات النصوص

```powershell run
$s = "  PowerShell is great  "
$s.Trim()
$s.Trim().ToLower()
"a,b,,c" -split ","
("one two three" -split " ").Count
"2026-11-21" -replace "-", "/"
"Hello World".Contains("World")
"report_2026.txt".EndsWith(".txt")
"abc".PadLeft(6, "*")
"PowerShell".IndexOf("Shell")
```

```text output
PowerShell is great
powershell is great
a
b

c
3
2026/11/21
True
True
***abc
5
```

| العملية | مثال |
|---|---|
| `-split` | تقسيم نص إلى مصفوفة |
| `-join` | لصق مصفوفة في نص |
| `-replace` | استبدال (بتعبير نمطي) |
| `.Trim()` | حذف المسافات من الطرفين |
| `.ToUpper()` / `.ToLower()` | تغيير الحالة |
| `.Contains()` / `.StartsWith()` / `.EndsWith()` | فحص |
| `.Substring(i, n)` / `.IndexOf()` | قطع / بحث |

## التعابير النمطية: `-match` و`$Matches`

```powershell run
$line = "Order #1234 total: 250.75 EGP"
if ($line -match "#(\d+).*?([\d.]+) EGP") {
    "رقم الطلب: $($Matches[1])"
    "المبلغ: $($Matches[2])"
}
"010-1234-5678" -replace "\D", ""
$emails = "ali@mail.com, bad, sara@site.org" -split ",\s*" | Where-Object { $_ -match "^[\w.]+@\w+\.\w+$" }
$emails -join " | "
```

```text output
رقم الطلب: 1234
المبلغ: 250.75
01012345678
ali@mail.com | sara@site.org
```

بعد `-match` الناجحة يحفظ PowerShell الأجزاء الملتقطة في `$Matches[1]` و`$Matches[2]`...

## النص متعدد الأسطر: Here-String

```powershell run
$name = "منى"
$report = @"
التقرير
الاسم: $name
التاريخ: 2026-11-21
"@
$report
$report.Split("`n").Count
```

```text output
التقرير
الاسم: منى
التاريخ: 2026-11-21
3
```

`@" ... "@` نص من عدة أسطر يستبدل المتغيرات (و`@' ... '@` بدون استبدال). يجب أن تكون `"@` في **أول** سطرها.

## الكتابة في ملف والقراءة منه

```powershell run
Set-Content -Path "notes.txt" -Value "السطر الأول", "السطر الثاني" -Encoding UTF8
Add-Content -Path "notes.txt" -Value "السطر الثالث" -Encoding UTF8
$lines = Get-Content -Path "notes.txt" -Encoding UTF8
"عدد الأسطر: $($lines.Count)"
$i = 1
foreach ($l in $lines) { "${i}: $l"; $i++ }
(Get-Content "notes.txt" -Encoding UTF8 -Raw).Length -gt 0
Remove-Item "notes.txt"
Test-Path "notes.txt"
```

```text output
عدد الأسطر: 3
1: السطر الأول
2: السطر الثاني
3: السطر الثالث
True
False
```

| الأمر | وظيفته |
|---|---|
| `Set-Content` | يكتب الملف (ويمسح القديم) |
| `Add-Content` | يضيف في آخر الملف |
| `Get-Content` | يقرأ الملف كمصفوفة أسطر |
| `Get-Content -Raw` | يقرأ الملف كنص واحد |
| `Out-File` | يرسل ناتج الأنبوب إلى ملف |

> **العربية في الملفات:** في Windows PowerShell 5.1 أضف `-Encoding UTF8` عند الكتابة والقراءة، وإلا قد تتحول الحروف العربية إلى علامات استفهام. (في PowerShell 7 الترميز الافتراضي UTF-8.)

## ملفات CSV: كائنات جاهزة

```powershell run
$data = @(
    [pscustomobject]@{ Name = "Ali"; Score = 80 }
    [pscustomobject]@{ Name = "Mona"; Score = 95 }
)
$data | Export-Csv -Path "scores.csv" -NoTypeInformation -Encoding UTF8
Get-Content "scores.csv"
"---"
$back = Import-Csv "scores.csv"
$back | ForEach-Object { "$($_.Name) => $([int]$_.Score + 5)" }
Remove-Item "scores.csv"
```

```text output
"Name","Score"
"Ali","80"
"Mona","95"
---
Ali => 85
Mona => 100
```

`Export-Csv` تكتب الكائنات في ملف CSV، و`Import-Csv` تقرؤها كائنات من جديد (بقيم نصية، لذلك حولنا `Score` بـ `[int]`). وبنفس الطريقة: `ConvertTo-Json` و`ConvertFrom-Json`.

## معالجة الأخطاء: `try` و`catch` و`finally`

```powershell run
function Divide($a, $b) {
    if ($b -eq 0) { throw "لا يمكن القسمة على صفر" }
    return $a / $b
}

try {
    "النتيجة: $(Divide 10 2)"
    "النتيجة: $(Divide 5 0)"
    "هذا السطر لن يُنفذ"
}
catch {
    "خطأ: $($_.Exception.Message)"
}
finally {
    "انتهت المحاولة"
}
"السكربت مستمر"
```

```text output
النتيجة: 5
خطأ: لا يمكن القسمة على صفر
انتهت المحاولة
السكربت مستمر
```

- `throw "رسالة"` تثير خطأ.
- داخل `catch` يمثل `$_` الخطأ، ورسالته في `$_.Exception.Message`.
- `finally` تُنفذ دائمًا.

### الأخطاء «غير القاطعة» و`-ErrorAction Stop`

كثير من الأوامر الجاهزة لا توقف السكربت عند الخطأ، بل تطبع رسالة وتكمل (خطأ غير قاطع). لكي يلتقطه `try` أضف `-ErrorAction Stop`:

```powershell run
try {
    Get-Content "missing-file.txt" -ErrorAction Stop
}
catch {
    "تعذر قراءة الملف: الملف غير موجود"
}

$content = Get-Content "missing-file.txt" -ErrorAction SilentlyContinue
"المحتوى فارغ؟ $($null -eq $content)"
```

```text output
تعذر قراءة الملف: الملف غير موجود
المحتوى فارغ؟ True
```

`-ErrorAction SilentlyContinue` تتجاهل الخطأ بصمت تمامًا.

## أخطاء شائعة

### نسيان `-ErrorAction Stop` مع `try`

`try { Get-Content "x.txt" } catch { ... }` قد لا يدخل إلى `catch` أبدًا، لأن الخطأ غير قاطع. أضف `-ErrorAction Stop`.

### `$null` على اليمين

اكتب `$null -eq $x` وليس `$x -eq $null`: إذا كانت `$x` مصفوفة فإن الصيغة الثانية تفلتر المصفوفة بدل أن تفحصها.

## تمارين

### التمرين 1

اقرأ سطرًا فيه أسماء مفصولة بفواصل ومسافات غير منتظمة مثل `علي , منى,خالد ,  سارة`، ونظّفه واطبع الأسماء مرتبة، كل اسم في سطر مع رقمه.

```powershell exercise
$line = [Console]::ReadLine()
```

```powershell solution
$line = [Console]::ReadLine()
$names = $line -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Sort-Object
$i = 1
foreach ($n in $names) { "$i. $n"; $i++ }
```

```text input
علي , منى,خالد ,  سارة
```

```text output
1. خالد
2. سارة
3. علي
4. منى
```

### التمرين 2

اكتب دالة `Read-Number` تحوّل نصًا إلى عدد بـ `[int]`، وإذا فشل التحويل ترمي الخطأ `ليس رقمًا: ...`. استدعها داخل `try` للقيم `"12"` و`"abc"`.

```powershell exercise
function Read-Number($text) {
}

foreach ($t in "12", "abc") {
}
```

```powershell solution
function Read-Number($text) {
    $n = 0
    if (-not [int]::TryParse($text, [ref]$n)) { throw "ليس رقمًا: $text" }
    return $n
}

foreach ($t in "12", "abc") {
    try {
        "الرقم: $(Read-Number $t)"
    }
    catch {
        "خطأ: $($_.Exception.Message)"
    }
}
```

```text output
الرقم: 12
خطأ: ليس رقمًا: abc
```

`[int]::TryParse(نص, [ref]$n)` دالة من .NET: تُرجع `$true` إذا نجح التحويل وتضع الرقم في `$n`.

## اختبر نفسك

```quiz
{"question": "ما ناتج \"a-b-c\" -split \"-\"؟", "choices": ["\"abc\"", "مصفوفة من 3 عناصر: a وb وc", "\"a b c\"", "خطأ"], "answer": 1, "explanation": "-split تقسم النص إلى مصفوفة."}
```

```quiz
{"question": "لماذا لا يلتقط try خطأ Get-Content لملف غير موجود أحيانًا؟", "choices": ["لأن try معطلة", "لأن الخطأ غير قاطع، ويحتاج -ErrorAction Stop", "لأن الملف موجود", "لأن catch يجب أن تأتي قبل try"], "answer": 1, "explanation": "أخطاء الأوامر الجاهزة غير قاطعة افتراضيًا، و-ErrorAction Stop تجعلها قاطعة."}
```

## الخلاصة

- `-split` و`-join` و`-replace` و`-match` مع `$Matches`، ودوال النص `.Trim()` و`.Contains()`.
- `@" ... "@` للنصوص متعددة الأسطر.
- `Set-Content` و`Add-Content` و`Get-Content` مع `-Encoding UTF8`، و`Export-Csv` و`Import-Csv`.
- `try { } catch { } finally { }` و`throw`، و`-ErrorAction Stop` للأوامر الجاهزة.
