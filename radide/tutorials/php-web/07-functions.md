# الدرس 7: الدوال والتعامل مع النصوص

**في هذا الدرس ستتعلم:**

- كتابة **دوال** خاصة بك: المعاملات، والقيمة المرجعة، والقيم الافتراضية.
- تحديد **الأنواع** للمعاملات والنتائج.
- **نطاق المتغيرات**: لماذا لا ترى الدالة متغيرات الخارج؟
- أهم دوال النصوص، ولماذا نستخدم دوال `mb_` مع العربية.
- تنسيق الأرقام والأسعار بـ `number_format` و`sprintf`.

## الدالة: وصفة مكتوبة مرة واحدة

**الدالة** (function) مثل وصفة طبخ: تكتب الخطوات مرة واحدة، ثم «تطبخها» كلما احتجت بمقادير (معاملات) مختلفة:

```php run
<?php
function greet(string $name): string
{
    return "أهلًا يا $name!";
}

echo greet("ليلى"), "\n";
echo greet("مازن"), "\n";
```

```text output
أهلًا يا ليلى!
أهلًا يا مازن!
```

- `function` الكلمة التي تعرّف الدالة، ثم اسمها `greet`.
- بين القوسين **المعاملات** (parameters): `string $name` معامل نوعه نص.
- `: string` بعد القوسين نوع **القيمة المرجعة**.
- `return` تُرجع النتيجة لمن استدعى الدالة وتنهيها.

## معاملات متعددة وقيم افتراضية

```php run
<?php
function price(float $amount, float $taxRate = 0.14, string $currency = "جنيه"): string
{
    $total = $amount * (1 + $taxRate);
    return $total . " " . $currency;
}

echo price(100), "\n";
echo price(100, 0.0), "\n";
echo price(50, 0.1, "دولار"), "\n";
echo price(200, currency: "ريال"), "\n";
```

```text output
114 جنيه
100 جنيه
55 دولار
228 ريال
```

- المعامل الذي له قيمة افتراضية (`= 0.14`) يصبح **اختياريًا**.
- السطر الأخير يستخدم **المعاملات المسمّاة** (named arguments) منذ PHP 8: نذكر اسم المعامل `currency:` فنتخطى ما قبله.

## الأنواع الصارمة

PHP تحاول تحويل الأنواع تلقائيًا. إذا أردت أن تكون صارمة (وهذا أفضل)، ضع في **أول سطر** من الملف `declare(strict_types=1);`:

```php run
<?php
declare(strict_types=1);

function square(int $n): int
{
    return $n * $n;
}

echo square(9), "\n";
try {
    echo square("9"), "\n";
} catch (TypeError $e) {
    echo "خطأ في النوع: المعامل يجب أن يكون int\n";
}
```

```text output
81
خطأ في النوع: المعامل يجب أن يكون int
```

سنشرح `try` و`catch` في درس الأصناف. المهم الآن: مع الأنواع الصارمة تكتشف الأخطاء مبكرًا بدل أن تختبئ.

## نطاق المتغيرات

ما يُعرّف **داخل** الدالة لا يُرى خارجها، وما **خارجها** لا تراه الدالة. الدالة غرفة مغلقة لا يدخلها إلا ما تمرره لها كمعاملات:

```php run
<?php
$site = "متجري";

function showSite(): void
{
    echo isset($site) ? "أرى المتغير\n" : "لا أرى \$site من داخل الدالة\n";
}

function showSite2(string $site): void
{
    echo "الموقع: $site\n";
}

showSite();
showSite2($site);
```

```text output
لا أرى $site من داخل الدالة
الموقع: متجري
```

`void` تعني أن الدالة لا تُرجع شيئًا. والحل الصحيح دائمًا: **مرّر ما تحتاجه كمعامل**، وتجنّب الكلمة `global`.

## دوال النصوص

```php run
<?php
$s = "  Hello PHP World  ";
echo "[" . trim($s) . "]\n";
echo strtoupper(trim($s)), "\n";
echo strtolower("RAD IDE"), "\n";
echo str_replace("World", "Developers", $s), "\n";
var_dump(str_contains($s, "PHP"));
var_dump(str_starts_with("index.php", "index"));
echo ucfirst("ahmed"), "\n";
echo str_repeat("=-", 5), "\n";
```

```text output
[Hello PHP World]
HELLO PHP WORLD
rad ide
  Hello PHP Developers  
bool(true)
bool(true)
Ahmed
=-=-=-=-=-
```

## النصوص العربية ودوال mb_

PHP العادية تعدّ **البايتات** لا الحروف، والحرف العربي في UTF-8 يأخذ بايتين. لذلك نستخدم دوال تبدأ بـ `mb_` (multibyte) مع العربية:

```php run
<?php
$word = "مرحبا";
echo "strlen: ", strlen($word), "\n";
echo "mb_strlen: ", mb_strlen($word), "\n";
echo "أول حرفين: ", mb_substr($word, 0, 2), "\n";

$title = "تعلم البرمجة بلغة PHP خطوة بخطوة";
$short = mb_strlen($title) > 15 ? mb_substr($title, 0, 15) . "..." : $title;
echo $short, "\n";
```

```text output
strlen: 10
mb_strlen: 5
أول حرفين: مر
تعلم البرمجة بل...
```

> **قاعدة:** مع أي نص قد يحتوي عربيًا استخدم `mb_strlen` و`mb_substr` و`mb_strtoupper`... وإلا قد تقطع الحرف من منتصفه فيظهر رمز غريب.

## تنسيق الأرقام

```php run
<?php
$amount = 1234567.891;
echo number_format($amount), "\n";
echo number_format($amount, 2), "\n";
echo number_format($amount, 2, ".", " "), "\n";
echo sprintf("الفاتورة رقم %05d بقيمة %.2f جنيه", 42, 99.5), "\n";
printf("%-8s|%6s|\n", "اسم", "سعر");
```

```text output
1,234,568
1,234,567.89
1 234 567.89
الفاتورة رقم 00042 بقيمة 99.50 جنيه
اسم  |سعر|
```

في `sprintf`: `%d` عدد صحيح، و`%05d` بعرض 5 مع أصفار، و`%.2f` عشري برقمين، و`%s` نص. (لاحظ أن عرض `%-8s` يُحسب بالبايتات، فيبدو النص العربي أقصر من المتوقع.)

## دالة تُرجع مصفوفة

```php run
<?php
function stats(array $numbers): array
{
    return [
        "count" => count($numbers),
        "sum" => array_sum($numbers),
        "avg" => array_sum($numbers) / max(count($numbers), 1),
    ];
}

$r = stats([10, 20, 30, 40]);
echo "العدد {$r['count']}، المجموع {$r['sum']}، المتوسط {$r['avg']}\n";
['sum' => $total] = $r;          // فك المصفوفة إلى متغير
echo "المجموع مرة أخرى: $total\n";
```

```text output
العدد 4، المجموع 100، المتوسط 25
المجموع مرة أخرى: 100
```

## أخطاء شائعة

- **نسيان `return`:** الدالة تحسب ولا تُرجع شيئًا، فتحصل على `null`.
- **كود بعد `return`:** لا يُنفّذ أبدًا.
- **استخدام `strlen` مع العربية:** يعطي ضعف عدد الحروف. استخدم `mb_strlen`.
- **تعريف دالتين بنفس الاسم:** `Fatal error: Cannot redeclare`. وأسماء الدوال **غير** حساسة لحالة الأحرف: `Greet` و`greet` اسم واحد.

## تمارين

### تمرين 1: مساحة الدائرة

اكتب دالة `circleArea(float $r): float` تُرجع `pi() * $r ** 2`، واطبع مساحة دائرة نصف قطرها 3 مقربة لرقمين: `28.27`.

```php exercise
<?php
// function circleArea(...)
echo round(circleArea(3), 2), "\n";
```

```php solution
<?php
function circleArea(float $r): float
{
    return pi() * $r ** 2;
}
echo round(circleArea(3), 2), "\n";
```

```text output
28.27
```

### تمرين 2: اختصار العنوان

اكتب دالة `excerpt(string $text, int $max = 10): string` تقطع النص عند `$max` حرفًا وتضيف `...` إذا كان أطول، وتعمل مع العربية.

```php exercise
<?php
function excerpt(string $text, int $max = 10): string
{
    return $text;
}
echo excerpt("أهلا بكم في موقعنا الجديد"), "\n";
echo excerpt("قصير"), "\n";
```

```php solution
<?php
function excerpt(string $text, int $max = 10): string
{
    if (mb_strlen($text) <= $max) {
        return $text;
    }
    return mb_substr($text, 0, $max) . "...";
}
echo excerpt("أهلا بكم في موقعنا الجديد"), "\n";
echo excerpt("قصير"), "\n";
```

```text output
أهلا بكم ف...
قصير
```

### تمرين 3: تنسيق السعر

اكتب دالة `money(float $v): string` تُرجع الرقم بفاصل الآلاف ورقمين عشريين ثم ` ج.م`، واطبع `money(15750.5)`.

```php exercise
<?php
function money(float $v): string
{
    // number_format
}
echo money(15750.5), "\n";
```

```php solution
<?php
function money(float $v): string
{
    return number_format($v, 2) . " ج.م";
}
echo money(15750.5), "\n";
```

```text output
15,750.50 ج.م
```

## اختبر نفسك

```quiz
{"question": "ماذا يعني `= 0.14` في `function f(float $tax = 0.14)` ؟", "choices": ["المعامل إجباري", "قيمة افتراضية تجعل المعامل اختياريًا", "خطأ صياغة", "ثابت عام"], "answer": 1, "explanation": "إذا لم يُمرَّر المعامل تُستخدم القيمة الافتراضية."}
```

```quiz
{"question": "كم يُرجع `strlen(\"سلام\")` ؟", "choices": ["4", "8", "2", "خطأ"], "answer": 1, "explanation": "كل حرف عربي بايتان في UTF-8، فالنتيجة 8. أما mb_strlen فتُرجع 4."}
```

```quiz
{"question": "متغير عُرّف خارج الدالة، كيف تستخدمه داخلها بالطريقة الصحيحة؟", "choices": ["تكتبه مباشرة", "تمرره كمعامل", "تعيد تعريفه بنفس القيمة", "لا يمكن أبدًا"], "answer": 1, "explanation": "الدالة لا ترى متغيرات الخارج؛ مرّر ما تحتاجه كمعامل."}
```

## الخلاصة

- الدالة: `function name(type $param = default): returnType { ... return ...; }`.
- `declare(strict_types=1);` يجعل الأنواع صارمة، والمعاملات المسمّاة تسهّل الاستدعاء.
- متغيرات الدالة محلية؛ مرّر البيانات كمعاملات.
- مع العربية استخدم دوال `mb_`، ولتنسيق الأرقام `number_format` و`sprintf`.
