# الدرس 3: الشروط وحلقات التكرار

نتعلم اليوم كيف **يختار** البرنامج (الشروط) وكيف **يكرر** (الحلقات). وPerl تعطيك طرقًا كثيرة، بعضها يُقرأ كالإنجليزية تمامًا.

> **تشبيه:** الشرط مثل **حارس البوابة**: يفحص التذكرة ثم يقرر. والحلقة مثل **آلة التعبئة في المصنع**: تعبئ زجاجة بعد زجاجة حتى تنتهي الزجاجات.

## `if` و`elsif` و`else`

```perl run
use strict;
use warnings;

my $score = 67;
if ($score >= 90) {
    print "ممتاز\n";
} elsif ($score >= 75) {
    print "جيد جدًا\n";
} elsif ($score >= 50) {
    print "مقبول\n";
} else {
    print "راسب\n";
}
```

```text output
مقبول
```

- الشرط بين قوسين `( )`، والجسم بين أقواس معقوصة `{ }` **إجباريًا** حتى لو كان سطرًا واحدًا.
- تُكتب `elsif` (وليس `else if` ولا `elseif`).

## `unless` والشرط في آخر السطر

```perl run
use strict;
use warnings;

my $balance = 30;
my $price = 50;
print "الرصيد لا يكفي\n" if $balance < $price;
print "تم الشراء\n" unless $balance < $price;

unless ($balance > 100) {
    print "رصيدك أقل من 100\n";
}
```

```text output
الرصيد لا يكفي
رصيدك أقل من 100
```

`unless` تعني «إلا إذا» (عكس `if`). وفي آخر السطر لا تحتاج أقواسًا ولا `{ }`.

## العوامل المنطقية

```perl run
use strict;
use warnings;

my ($age, $member) = (20, 1);
print "مسموح\n" if $age >= 18 && $member;
print "عطلة\n" if "الجمعة" eq "الجمعة" || 0;
print "ليس صفرًا\n" if !0;
print "and وor بكلمات أيضًا\n" if $age > 10 and not $age > 50;
```

```text output
مسموح
عطلة
ليس صفرًا
and وor بكلمات أيضًا
```

### ما هو «الخطأ» في Perl؟

القيم **الخاطئة** في Perl هي: `0` و`"0"` والنص الفارغ `""` و`undef`. كل ما عداها صحيح:

```perl run
use strict;
use warnings;

for my $v (0, "0", "", "0.0", "00", 1, "abc") {
    print "'$v' => ", ($v ? "صحيح" : "خطأ"), "\n";
}
```

```text output
'0' => خطأ
'0' => خطأ
'' => خطأ
'0.0' => صحيح
'00' => صحيح
'1' => صحيح
'abc' => صحيح
```

لاحظ أن `"0.0"` و`"00"` صحيحان لأنهما ليسا النص `"0"` بالضبط!

## حلقة `for` بأسلوب C و`foreach`

```perl run
use strict;
use warnings;

for (my $i = 1; $i <= 3; $i++) {
    print "الدورة $i\n";
}

foreach my $n (1 .. 5) {
    print $n * $n, " ";
}
print "\n";

for my $fruit ("تفاح", "موز") {
    print "أحب $fruit\n";
}
```

```text output
الدورة 1
الدورة 2
الدورة 3
1 4 9 16 25 
أحب تفاح
أحب موز
```

- `1 .. 5` **مدى** يعطي القائمة 1، 2، 3، 4، 5.
- `foreach` و`for` كلمتان بنفس المعنى في Perl.
- `foreach my $x (قائمة)` الأكثر استخدامًا وأوضح من أسلوب C.

## `while` و`until`

```perl run
use strict;
use warnings;

my ($balance, $years) = (1000, 0);
while ($balance < 2000) {
    $balance *= 1.1;
    $years++;
}
print "يتضاعف بعد $years سنوات\n";

my $n = 3;
until ($n == 0) {
    print "العد: $n\n";
    $n--;
}
```

```text output
يتضاعف بعد 8 سنوات
العد: 3
العد: 2
العد: 1
```

## `next` و`last`

```perl run
use strict;
use warnings;

for my $i (1 .. 10) {
    next if $i % 2 == 0;   # تخطَّ الزوجي
    last if $i > 7;        # توقف تمامًا
    print "$i ";
}
print "\n";
```

```text output
1 3 5 7 
```

في Perl: `next` للانتقال للدورة التالية، و`last` للخروج من الحلقة (بدل `continue` و`break` في لغات أخرى).

## قراءة كل الأسطر حتى النهاية

```perl run
use strict;
use warnings;

my ($count, $total) = (0, 0);
while (my $line = <STDIN>) {
    chomp $line;
    next if $line eq "";
    $count++;
    $total += $line;
}
print "قرأت $count أعداد، مجموعها $total\n";
```

```text input
5
10

20
```

```text output
قرأت 3 أعداد، مجموعها 35
```

`while (my $line = <STDIN>)` تقرأ سطرًا في كل دورة حتى ينتهي الإدخال، وهو من أشهر أسطر Perl.

## أخطاء شائعة

### نسيان الأقواس المعقوصة

<!-- compile-error -->
```perl
my $x = 5;
if ($x > 3)
    print "كبير\n";
```

في Perl الأقواس `{ }` إجبارية بعد `if`. أو استخدم الصيغة القصيرة: `print "كبير\n" if $x > 3;`.

### `break` بدل `last`

`break` ليست كلمة لإنهاء الحلقات في Perl. استخدم `last`.

## تمارين

### التمرين 1

اقرأ عددًا واطبع مجموع الأعداد الفردية من 1 حتى هذا العدد.

```perl exercise
use strict;
use warnings;
my $n = <STDIN>;
chomp $n;
my $sum = 0;
```

```perl solution
use strict;
use warnings;
my $n = <STDIN>;
chomp $n;
my $sum = 0;
for my $i (1 .. $n) {
    $sum += $i if $i % 2;
}
print "مجموع الأعداد الفردية حتى $n = $sum\n";
```

```text input
10
```

```text output
مجموع الأعداد الفردية حتى 10 = 25
```

### التمرين 2

اطبع جدولًا صغيرًا لدرجات الحرارة من 0 إلى 40 بخطوة 10، مع قيمتها بالفهرنهايت `F = C × 9 / 5 + 32`.

```perl exercise
use strict;
use warnings;
```

```perl solution
use strict;
use warnings;
for (my $c = 0; $c <= 40; $c += 10) {
    printf("%3d C = %5.1f F\n", $c, $c * 9 / 5 + 32);
}
```

```text output
  0 C =  32.0 F
 10 C =  50.0 F
 20 C =  68.0 F
 30 C =  86.0 F
 40 C = 104.0 F
```

## اختبر نفسك

```quiz
{"question": "أي القيم التالية صحيحة (true) في Perl؟", "choices": ["0", "\"0\"", "\"\"", "\"0.0\""], "answer": 3, "explanation": "الخاطئ فقط 0 و\"0\" و\"\" وundef. النص \"0.0\" ليس \"0\" فهو صحيح."}
```

```quiz
{"question": "ما الكلمة التي تخرج من الحلقة في Perl؟", "choices": ["break", "exit", "last", "stop"], "answer": 2, "explanation": "last تنهي الحلقة، وnext تنتقل للدورة التالية."}
```

```quiz
{"question": "ماذا يعطي المدى 3 .. 6؟", "choices": ["3 و6 فقط", "3، 4، 5، 6", "3، 4، 5", "خطأ"], "answer": 1, "explanation": "المدى يشمل البداية والنهاية."}
```

## الخلاصة

- `if (...) { } elsif (...) { } else { }` والأقواس المعقوصة إجبارية.
- `unless` عكس `if`، والشرط في آخر السطر: `print "x" if $ok;`.
- الخاطئ: `0` و`"0"` و`""` و`undef`.
- `foreach my $x (1 .. 10)` و`while` و`until`، و`next` و`last`.
- `while (my $line = <STDIN>)` لقراءة كل الإدخال.
