# الدرس 5: الدوال والمراجع

**الدالة** في Perl اسمها **sub** (اختصار subroutine، أي «روتين فرعي»). و**المرجع** (reference) طريقة لصنع بيانات متداخلة: قائمة داخل قائمة، أو قاموس داخل قاموس.

> **تشبيه:** المرجع مثل **عنوان منزل مكتوب على ورقة**: الورقة صغيرة وسهلة الحمل، لكنها توصلك إلى المنزل الحقيقي بكل ما فيه.

## تعريف دالة واستدعاؤها

```perl run
use strict;
use warnings;

sub greet {
    my ($name) = @_;
    print "أهلًا يا $name!\n";
}

sub add {
    my ($x, $y) = @_;
    return $x + $y;
}

greet("سارة");
my $total = add(3, 4);
print "المجموع: $total\n";
print "مباشرة: ", add(10, 20), "\n";
```

```text output
أهلًا يا سارة!
المجموع: 7
مباشرة: 30
```

- المعاملات تصل في المصفوفة الخاصة `@_`، والعادة أن ننسخها فورًا في متغيرات بأسماء: `my ($x, $y) = @_;`.
- `return` تُرجع القيمة. وبدونها تُرجع الدالة قيمة آخر تعبير.

## القيم الافتراضية وعدد غير محدد من المعاملات

```perl run
use strict;
use warnings;

sub power {
    my ($base, $exp) = @_;
    $exp //= 2;                 # إذا لم يُمرر فاجعله 2
    return $base ** $exp;
}

sub sum_all {
    my $total = 0;
    $total += $_ for @_;
    return $total;
}

print power(5), "\n";
print power(2, 10), "\n";
print sum_all(1, 2, 3, 4), "\n";
```

```text output
25
1024
10
```

## إرجاع قائمة

```perl run
use strict;
use warnings;

sub min_max {
    my @sorted = sort { $a <=> $b } @_;
    return ($sorted[0], $sorted[-1]);
}

my ($lo, $hi) = min_max(7, 2, 9, 4);
print "الأصغر $lo والأكبر $hi\n";
```

```text output
الأصغر 2 والأكبر 9
```

## المتغيرات المحلية بـ `my`

```perl run
use strict;
use warnings;

my $x = 10;
sub change {
    my $x = 99;      # متغير جديد داخل الدالة
    return $x;
}
print change(), " ", $x, "\n";
```

```text output
99 10
```

## المراجع: لماذا نحتاجها؟

إذا مررت مصفوفتين لدالة فإنهما **تندمجان** في `@_` واحدة! والحل: نمرر **مرجعًا** لكل مصفوفة.

```perl run
use strict;
use warnings;

my @a = (1, 2, 3);
my %h = (name => "علي", age => 20);

my $aref = \@a;           # مرجع لمصفوفة
my $href = \%h;           # مرجع لقاموس

print "$$aref[0] ${$aref}[1] $aref->[2]\n";
print "$href->{name} عمره $href->{age}\n";
print "العدد: ", scalar(@$aref), "\n";
push @$aref, 4;
print "@a\n";
```

```text output
1 2 3
علي عمره 20
العدد: 3
1 2 3 4
```

- `\@a` تعطي **مرجعًا** للمصفوفة (عنوانها)، و`\%h` لقاموس.
- `$aref->[0]` تصل للعنصر عبر المرجع، و`$href->{name}` للقيمة.
- `@$aref` المصفوفة كاملة عبر المرجع. وتعديلها يعدّل الأصل (لأنه نفس المنزل!).

## المصفوفات والقواميس المجهولة

الطريقة الأكثر استخدامًا: نصنع المرجع مباشرة بـ `[ ]` للمصفوفة و`{ }` للقاموس:

```perl run
use strict;
use warnings;

my $students = [
    { name => "علي", scores => [80, 90] },
    { name => "منى", scores => [95, 85] },
];

for my $s (@$students) {
    my @sc = @{ $s->{scores} };
    my $sum = 0;
    $sum += $_ for @sc;
    printf("%s: المتوسط %.1f\n", $s->{name}, $sum / @sc);
}
print $students->[1]{scores}[0], "\n";
```

```text output
علي: المتوسط 85.0
منى: المتوسط 90.0
95
```

`$students->[1]{scores}[0]` تقرأ: «الطالب الثاني ← درجاته ← الأولى».

## تمرير مصفوفات لدالة بالمراجع

```perl run
use strict;
use warnings;

sub compare_totals {
    my ($first, $second) = @_;     # مرجعان
    my ($t1, $t2) = (0, 0);
    $t1 += $_ for @$first;
    $t2 += $_ for @$second;
    return $t1 <=> $t2;
}

my @x = (1, 2, 3);
my @y = (10, 1);
my $r = compare_totals(\@x, \@y);
print $r == -1 ? "الأولى أصغر\n" : $r == 1 ? "الأولى أكبر\n" : "متساويتان\n";
```

```text output
الأولى أصغر
```

## مراجع الدوال

```perl run
use strict;
use warnings;

my %ops = (
    "+" => sub { $_[0] + $_[1] },
    "*" => sub { $_[0] * $_[1] },
);

for my $op (sort keys %ops) {
    print "6 $op 7 = ", $ops{$op}->(6, 7), "\n";
}
```

```text output
6 * 7 = 42
6 + 7 = 13
```

`sub { ... }` دالة مجهولة، ونخزن مرجعها في قاموس، ونستدعيها بـ `->( )`. هذه الطريقة مفيدة جدًا للأوامر والأحداث.

## أخطاء شائعة

### نسيان `my (...) = @_`

`my $x = @_;` تعطي **عدد** المعاملات وليس أولها! اكتب `my ($x) = @_;` بالأقواس، أو `my $x = shift;`.

### طباعة المرجع مباشرة

`print $aref;` تطبع شيئًا مثل `ARRAY(0x55d1c2a8)`، وهو عنوان المرجع. اكتب `print "@$aref"`.

## تمارين

### التمرين 1

اكتب دالة `average` تأخذ قائمة أعداد وتُرجع متوسطها، ودالة `above_average` تُرجع الأعداد الأكبر من المتوسط.

```perl exercise
use strict;
use warnings;

sub average {
}

sub above_average {
}

my @n = (4, 8, 15, 16, 23, 42);
printf("المتوسط: %.2f\n", average(@n));
print "أكبر من المتوسط: @{[ above_average(@n) ]}\n";
```

```perl solution
use strict;
use warnings;

sub average {
    my $sum = 0;
    $sum += $_ for @_;
    return $sum / @_;
}

sub above_average {
    my $avg = average(@_);
    return grep { $_ > $avg } @_;
}

my @n = (4, 8, 15, 16, 23, 42);
printf("المتوسط: %.2f\n", average(@n));
print "أكبر من المتوسط: @{[ above_average(@n) ]}\n";
```

```text output
المتوسط: 18.00
أكبر من المتوسط: 23 42
```

`@{[ ... ]}` حيلة لوضع ناتج دالة داخل نص بين علامتي تنصيص.

### التمرين 2

لديك مرجع لقائمة كتب (كل كتاب قاموس فيه `title` و`pages`). اطبع عنوان أطول كتاب ومجموع الصفحات.

```perl exercise
use strict;
use warnings;
my $books = [
    { title => "Perl للمبتدئين", pages => 220 },
    { title => "التعابير النمطية", pages => 340 },
    { title => "مشاريع صغيرة", pages => 150 },
];
```

```perl solution
use strict;
use warnings;
my $books = [
    { title => "Perl للمبتدئين", pages => 220 },
    { title => "التعابير النمطية", pages => 340 },
    { title => "مشاريع صغيرة", pages => 150 },
];
my ($longest) = sort { $b->{pages} <=> $a->{pages} } @$books;
my $total = 0;
$total += $_->{pages} for @$books;
print "الأطول: $longest->{title}\n";
print "مجموع الصفحات: $total\n";
```

```text output
الأطول: التعابير النمطية
مجموع الصفحات: 710
```

## اختبر نفسك

```quiz
{"question": "أين تصل معاملات الدالة في Perl؟", "choices": ["في $args", "في المصفوفة @_", "في %params", "في $0"], "answer": 1, "explanation": "المعاملات في @_ وننسخها عادة بـ my ($a, $b) = @_;"}
```

```quiz
{"question": "ما الذي تصنعه [1, 2, 3]؟", "choices": ["مصفوفة عادية", "مرجعًا لمصفوفة مجهولة", "قاموسًا", "نصًا"], "answer": 1, "explanation": "الأقواس المربعة تصنع مرجعًا لمصفوفة، والمعقوصة { } مرجعًا لقاموس."}
```

```quiz
{"question": "كيف تصل للمفتاح name عبر المرجع $p؟", "choices": ["$p{name}", "$p->{name}", "@p{name}", "p.name"], "answer": 1, "explanation": "السهم -> يصل إلى البيانات عبر المرجع."}
```

## الخلاصة

- `sub name { my (...) = @_; ... return ...; }`.
- `//=` لقيمة افتراضية، والدالة تُرجع قائمة أيضًا.
- المرجع `\@a` و`\%h`، والمجهول `[ ]` و`{ }`، والوصول بـ `->`.
- مرر المصفوفات للدوال بالمراجع، و`sub { }` لدوال مجهولة.
