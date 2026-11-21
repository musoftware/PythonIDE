# الدرس 7: الملفات ومعالجة الأخطاء

Perl وُلدت لمعالجة الملفات: تقرأ ملفًا، وتبحث فيه، وتكتب تقريرًا. وفي هذا الدرس نتعلم أيضًا كيف يتعامل البرنامج مع الأخطاء بهدوء بدل أن يتوقف فجأة.

> **تشبيه:** فتح الملف مثل **استعارة كتاب من المكتبة**: تأخذ الكتاب (تفتح الملف)، وتقرأ أو تكتب، ثم **تعيده** (تغلقه). وإذا لم يكن الكتاب موجودًا، يخبرك أمين المكتبة بالسبب بدل أن تنتظر إلى الأبد.

## الكتابة في ملف

```perl run
use strict;
use warnings;

open(my $out, '>', 'notes.txt') or die "لا يمكن إنشاء الملف: $!";
print $out "السطر الأول\n";
print $out "السطر الثاني\n";
close($out);

open(my $add, '>>', 'notes.txt') or die "لا يمكن الفتح: $!";
print $add "السطر الثالث\n";
close($add);

open(my $in, '<', 'notes.txt') or die "لا يمكن القراءة: $!";
while (my $line = <$in>) {
    chomp $line;
    print "$.: $line\n";
}
close($in);
unlink 'notes.txt';
print -e 'notes.txt' ? "ما زال موجودًا\n" : "تم حذف الملف\n";
```

```text output
1: السطر الأول
2: السطر الثاني
3: السطر الثالث
تم حذف الملف
```

| الوضع | معناه |
|---|---|
| `'<'` | قراءة |
| `'>'` | كتابة (يمسح المحتوى القديم) |
| `'>>'` | إضافة في آخر الملف |

- `open(my $fh, MODE, PATH)` تفتح الملف وتضع **مقبضه** (filehandle) في `$fh`.
- `print $fh "..."` تكتب فيه (لاحظ: لا فاصلة بين `$fh` والنص).
- `<$fh>` تقرأ سطرًا، و`$.` رقم السطر الحالي.
- `-e PATH` هل الملف موجود؟ و`unlink` تحذفه.

## `or die`: توقف برسالة واضحة

`open` تُرجع «خطأ» إذا فشلت، فنكتب بعدها `or die "رسالة"`. والمتغير الخاص `$!` يحمل سبب الفشل من نظام التشغيل:

```perl run
use strict;
use warnings;

if (open(my $fh, '<', 'missing.txt')) {
    print "فُتح الملف\n";
    close $fh;
} else {
    print "تعذر فتح الملف: $!\n";
}
```

```text output
تعذر فتح الملف: No such file or directory
```

## قراءة الملف كله دفعة واحدة

```perl run
use strict;
use warnings;

open(my $o, '>', 'data.txt') or die $!;
print $o "تفاح\nموز\nتفاح\nعنب\n";
close $o;

open(my $i, '<', 'data.txt') or die $!;
my @lines = <$i>;
close $i;
chomp @lines;
print "عدد الأسطر: ", scalar(@lines), "\n";
my %seen;
my @unique = grep { !$seen{$_}++ } @lines;
print "بدون تكرار: @unique\n";
unlink 'data.txt';
```

```text output
عدد الأسطر: 4
بدون تكرار: تفاح موز عنب
```

`<$fh>` في سياق قائمة تُرجع **كل الأسطر**. والسطر `grep { !$seen{$_}++ } @lines` حيلة Perl الشهيرة لحذف التكرار مع الحفاظ على الترتيب.

## مثال: تقرير من ملف CSV

```perl run
use strict;
use warnings;

open(my $o, '>', 'sales.csv') or die $!;
print $o "المنتج,الكمية,السعر\nقلم,10,5\nدفتر,4,20\nحقيبة,1,150\n";
close $o;

open(my $in, '<', 'sales.csv') or die $!;
my $header = <$in>;
my $total = 0;
while (my $line = <$in>) {
    chomp $line;
    my ($item, $qty, $price) = split /,/, $line;
    my $sum = $qty * $price;
    $total += $sum;
    print "$item: $qty × $price = $sum\n";
}
close $in;
print "الإجمالي: $total\n";
unlink 'sales.csv';
```

```text output
قلم: 10 × 5 = 50
دفتر: 4 × 20 = 80
حقيبة: 1 × 150 = 150
الإجمالي: 280
```

## التقاط الأخطاء: `eval`

`die` توقف البرنامج كله. لكي **نلتقط** الخطأ ونكمل نضع الكود داخل `eval { ... }`:

```perl run
use strict;
use warnings;

sub divide {
    my ($a1, $b1) = @_;
    die "لا يمكن القسمة على صفر\n" if $b1 == 0;
    return $a1 / $b1;
}

for my $pair ([10, 2], [5, 0], [9, 3]) {
    my $r = eval { divide(@$pair) };
    if ($@) {
        print "خطأ: $@";
    } else {
        print "الناتج: $r\n";
    }
}
print "البرنامج مستمر\n";
```

```text output
الناتج: 5
خطأ: لا يمكن القسمة على صفر
الناتج: 3
البرنامج مستمر
```

- `eval { ... }` تنفذ الكتلة؛ إذا حدث `die` بداخلها لا يتوقف البرنامج، بل توضع الرسالة في `$@`.
- إذا انتهت رسالة `die` بـ `\n` فلن تضيف Perl اسم الملف ورقم السطر.

## `warn`: تحذير دون توقف

`warn "رسالة\n"` تطبع الرسالة في مخرج الأخطاء (stderr) ويستمر البرنامج. في الـ IDE تظهر في نافذة **Output** أيضًا.

## أخطاء شائعة

### نسيان `or die`

بدون `or die` قد يفشل `open` بصمت، ثم تحاول القراءة من مقبض فارغ: `readline() on closed filehandle`.

### الفاصلة بعد المقبض

<!-- compile-error -->
```perl
open(my $fh, '>', 'x.txt') or die $!;
print $fh, "نص\n";
```

هذا يطبع **المقبض نفسه** على الشاشة (مثل `GLOB(0x...)`) بدل أن يكتب في الملف. اكتب `print $fh "نص\n";` بلا فاصلة.

### استخدام `>` بدل `>>`

`'>'` تمسح الملف القديم! إذا أردت الإضافة استخدم `'>>'`.

## تمارين

### التمرين 1

اكتب في ملف `words.txt` الكلمات `perl ruby lua perl dart perl` (كل كلمة في سطر)، ثم اقرأه واطبع كل كلمة وعدد مرات ظهورها مرتبة أبجديًا، ثم احذف الملف.

```perl exercise
use strict;
use warnings;
my @words = qw(perl ruby lua perl dart perl);
```

```perl solution
use strict;
use warnings;
my @words = qw(perl ruby lua perl dart perl);
open(my $o, '>', 'words.txt') or die $!;
print $o "$_\n" for @words;
close $o;

my %count;
open(my $i, '<', 'words.txt') or die $!;
while (my $w = <$i>) {
    chomp $w;
    $count{$w}++;
}
close $i;
print "$_: $count{$_}\n" for sort keys %count;
unlink 'words.txt';
```

```text output
dart: 1
lua: 1
perl: 3
ruby: 1
```

`qw(a b c)` اختصار لقائمة نصوص: `("a", "b", "c")`.

### التمرين 2

اكتب دالة `parse_age` تأخذ نصًا وتستخدم `die` إذا لم يكن عددًا صحيحًا بين 0 و150. استدعها داخل `eval` للقيم `"25"` و`"abc"` و`"200"`.

```perl exercise
use strict;
use warnings;

sub parse_age {
}

for my $v ("25", "abc", "200") {
}
```

```perl solution
use strict;
use warnings;

sub parse_age {
    my ($s) = @_;
    die "ليس عددًا: $s\n" unless $s =~ /^\d+$/;
    die "خارج المدى: $s\n" if $s > 150;
    return $s;
}

for my $v ("25", "abc", "200") {
    my $age = eval { parse_age($v) };
    print defined $age ? "العمر: $age\n" : "مرفوض: $@";
}
```

```text output
العمر: 25
مرفوض: ليس عددًا: abc
مرفوض: خارج المدى: 200
```

## اختبر نفسك

```quiz
{"question": "أي وضع يفتح الملف للإضافة في آخره؟", "choices": ["'<'", "'>'", "'>>'", "'+<'"], "answer": 2, "explanation": "'>>' للإضافة، و'>' للكتابة من جديد، و'<' للقراءة."}
```

```quiz
{"question": "أين تجد رسالة الخطأ بعد eval { die ... }؟", "choices": ["$!", "$@", "$_", "$0"], "answer": 1, "explanation": "$@ يحمل رسالة die التي التقطتها eval، أما $! فسبب فشل عمليات النظام مثل open."}
```

## الخلاصة

- `open(my $fh, '<' | '>' | '>>', $path) or die "...: $!";` ثم `close($fh)`.
- `<$fh>` لسطر، وفي سياق قائمة لكل الأسطر، و`$.` رقم السطر.
- `print $fh "..."` بلا فاصلة للكتابة في الملف.
- `die` لإيقاف، و`eval { }` مع `$@` لالتقاط الخطأ، و`warn` للتحذير.
