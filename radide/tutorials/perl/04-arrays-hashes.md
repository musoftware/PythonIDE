# الدرس 4: المصفوفات والقواميس (Hashes)

**المصفوفة** (`@`) قائمة مرتبة من القيم، و**القاموس** (`%`، ويسمى في Perl «hash») مجموعة أزواج من مفتاح وقيمة.

> **تشبيه:** المصفوفة مثل **طابور** في البنك: لكل شخص رقم دوره. والقاموس مثل **لوحة المفاتيح في الفندق**: كل مفتاح معلق تحت رقم الغرفة.

## المصفوفة

```perl run
use strict;
use warnings;

my @fruits = ("تفاح", "موز", "برتقال");
print "$fruits[0]\n";
print "$fruits[-1]\n";
print "العدد: ", scalar(@fruits), "\n";
print "آخر فهرس: $#fruits\n";
print "@fruits\n";
```

```text output
تفاح
برتقال
العدد: 3
آخر فهرس: 2
تفاح موز برتقال
```

- المصفوفة كلها `@fruits`، لكن **العنصر الواحد** `$fruits[0]` (بالرمز `$` لأنه قيمة مفردة!).
- الفهرس يبدأ من **0**، و`-1` للأخير.
- `scalar(@fruits)` عدد العناصر، و`$#fruits` آخر فهرس.
- `"@fruits"` داخل علامتي التنصيص تطبع العناصر بينها مسافات.

## الإضافة والحذف

```perl run
use strict;
use warnings;

my @nums = (5, 3, 8);
push @nums, 10;          # في الآخر
unshift @nums, 0;        # في الأول
my $last = pop @nums;    # احذف الأخير
my $first = shift @nums; # احذف الأول
print "@nums | حُذف $first و $last\n";
my @part = @nums[0, 1];  # شريحة
print "@part\n";
splice(@nums, 1, 1);     # احذف عنصرًا من الموضع 1
print "@nums\n";
```

```text output
5 3 8 | حُذف 0 و 10
5 3
5 8
```

| الدالة | وظيفتها |
|---|---|
| `push @a, x` | أضف في الآخر |
| `pop @a` | احذف الأخير وأرجعه |
| `unshift @a, x` | أضف في الأول |
| `shift @a` | احذف الأول وأرجعه |
| `splice(@a, i, n)` | احذف `n` عناصر من الموضع `i` |

## دوال القوائم: `sort` و`reverse` و`join` و`split`

```perl run
use strict;
use warnings;

my @scores = (70, 95, 8, 60);
my @sorted_text = sort @scores;
my @sorted_num = sort { $a <=> $b } @scores;
my @desc = sort { $b <=> $a } @scores;
print "@sorted_text\n";
print "@sorted_num\n";
print "@desc\n";
print join(", ", reverse @sorted_num), "\n";
my @parts = split /,/, "علي,منى,خالد";
print scalar(@parts), " أسماء، الثاني: $parts[1]\n";
```

```text output
60 70 8 95
8 60 70 95
95 70 60 8
95, 70, 60, 8
3 أسماء، الثاني: منى
```

> **انتبه:** `sort` بدون كتلة ترتب **كنصوص**، فيأتي `8` بعد `70`! للأرقام اكتب `sort { $a <=> $b }`. و`<=>` عامل مقارنة الأرقام، و`cmp` للنصوص.

## `map` و`grep`

```perl run
use strict;
use warnings;

my @nums = (1 .. 6);
my @squares = map { $_ * $_ } @nums;
my @even = grep { $_ % 2 == 0 } @nums;
my $count = grep { $_ > 3 } @nums;
print "@squares\n";
print "@even\n";
print "أكبر من 3: $count\n";
```

```text output
1 4 9 16 25 36
2 4 6
أكبر من 3: 3
```

- `map { ... } @list` تطبق الكتلة على كل عنصر وتُرجع قائمة جديدة.
- `grep { ... } @list` تُرجع العناصر التي تجعل الكتلة صحيحة.
- `$_` **المتغير الافتراضي**: العنصر الحالي. ستراه كثيرًا في Perl.

## القاموس (Hash)

```perl run
use strict;
use warnings;

my %age = ("علي" => 20, "منى" => 22);
$age{"خالد"} = 19;
print "عمر منى: $age{'منى'}\n";
print exists $age{"سعيد"} ? "موجود\n" : "سعيد غير موجود\n";
delete $age{"علي"};
for my $name (sort keys %age) {
    print "$name => $age{$name}\n";
}
print "العدد: ", scalar(keys %age), "\n";
```

```text output
عمر منى: 22
سعيد غير موجود
خالد => 19
منى => 22
العدد: 2
```

- القاموس كله `%age`، والقيمة الواحدة `$age{"منى"}` بأقواس معقوصة.
- `keys %h` المفاتيح، و`values %h` القيم، و`exists` للفحص، و`delete` للحذف.
- ترتيب المفاتيح في القاموس **عشوائي**؛ لذلك نكتب `sort keys %age` لنحصل على ترتيب ثابت.

## مثال: عدّ الكلمات

```perl run
use strict;
use warnings;

my $text = "the cat and the dog and the bird";
my %count;
$count{$_}++ for split / /, $text;
for my $w (sort { $count{$b} <=> $count{$a} || $a cmp $b } keys %count) {
    print "$w: $count{$w}\n";
}
```

```text output
the: 3
and: 2
bird: 1
cat: 1
dog: 1
```

- `$count{$_}++ for ...` حلقة في سطر واحد: لكل كلمة زد عدّادها (القيمة غير المعرّفة تبدأ من صفر).
- الترتيب: الأكثر تكرارًا أولًا، وعند التساوي أبجديًا (`||` تنتقل للمقارنة الثانية عند التساوي).

## أخطاء شائعة

### `@a[0]` بدل `$a[0]`

العنصر الواحد يُكتب `$a[0]`. أما `@a[0]` فهي «شريحة من عنصر واحد» وتعطي تحذيرًا `Scalar value @a[0] better written as $a[0]`.

### الترتيب النصي للأرقام

`sort (10, 9, 100)` تعطي `10 100 9`. استخدم `sort { $a <=> $b }`.

### الاعتماد على ترتيب القاموس

اطبع المفاتيح دائمًا بعد `sort` إذا كان الترتيب مهمًا.

## تمارين

### التمرين 1

اقرأ أعدادًا (كل عدد في سطر حتى نهاية الإدخال) في مصفوفة، ثم اطبعها مرتبة تصاعديًا، والأكبر، والمتوسط بمنزلة واحدة.

```perl exercise
use strict;
use warnings;
my @nums;
while (my $line = <STDIN>) {
    chomp $line;
    push @nums, $line;
}
```

```perl solution
use strict;
use warnings;
my @nums;
while (my $line = <STDIN>) {
    chomp $line;
    push @nums, $line;
}
my @sorted = sort { $a <=> $b } @nums;
my $sum = 0;
$sum += $_ for @nums;
print "مرتبة: @sorted\n";
print "الأكبر: $sorted[-1]\n";
printf("المتوسط: %.1f\n", $sum / @nums);
```

```text input
12
7
30
3
```

```text output
مرتبة: 3 7 12 30
الأكبر: 30
المتوسط: 13.0
```

لاحظ `$sum / @nums`: المصفوفة في سياق رقمي تعطي عدد عناصرها.

### التمرين 2

لديك قاموس أسعار. اطبع المنتجات مرتبة من الأغلى للأرخص بالشكل `المنتج: السعر`.

```perl exercise
use strict;
use warnings;
my %price = ("قلم" => 5, "حقيبة" => 150, "دفتر" => 20);
```

```perl solution
use strict;
use warnings;
my %price = ("قلم" => 5, "حقيبة" => 150, "دفتر" => 20);
for my $item (sort { $price{$b} <=> $price{$a} } keys %price) {
    print "$item: $price{$item}\n";
}
```

```text output
حقيبة: 150
دفتر: 20
قلم: 5
```

## اختبر نفسك

```quiz
{"question": "كيف تكتب العنصر الأول من المصفوفة @list؟", "choices": ["@list[0]", "$list[0]", "%list[0]", "list(0)"], "answer": 1, "explanation": "العنصر الواحد قيمة مفردة فيبدأ بـ $."}
```

```quiz
{"question": "ما ناتج sort { $a <=> $b } (10, 9, 100)؟", "choices": ["10 100 9", "9 10 100", "100 10 9", "خطأ"], "answer": 1, "explanation": "<=> يقارن رقميًا فيكون الترتيب 9 ثم 10 ثم 100."}
```

```quiz
{"question": "ماذا يمثل $_ داخل map وgrep؟", "choices": ["عدد العناصر", "العنصر الحالي", "آخر عنصر", "اسم المصفوفة"], "answer": 1, "explanation": "$_ هو المتغير الافتراضي ويحمل العنصر الحالي."}
```

## الخلاصة

- `@a` مصفوفة وعنصرها `$a[i]`، و`%h` قاموس وقيمته `$h{key}`.
- `push` و`pop` و`shift` و`unshift` و`splice` للتعديل.
- `sort { $a <=> $b }` للأرقام و`sort` أو `cmp` للنصوص.
- `map` و`grep` مع `$_`، و`keys` و`values` و`exists` و`delete` للقواميس.
