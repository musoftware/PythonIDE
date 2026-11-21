# الدرس 9: مشروع: محلل النصوص بنافذة رسومية

نبني في هذا المشروع أداة تليق بـ Perl: **محلل نصوص**. يلصق المستخدم نصًا إنجليزيًا، فيعرض البرنامج عدد الكلمات والجمل والحروف، والكلمات الأكثر تكرارًا، ويستخرج الأرقام والروابط وعناوين البريد.

سنستخدم: التعابير النمطية، والقواميس، والترتيب، والدوال، والأحداث.

## 1) تصميم النافذة

أنشئ مشروعًا: **File > New Project... > Perl (GUI Bridge)** باسم `TextAnalyzer`، وارسم:

| الأداة | Name | ملاحظات |
|---|---|---|
| `TextBox` | `txtInput` | اجعل `Multiline` = `True` وكبّره |
| `Button` | `btnAnalyze` | `حلّل` |
| `Label` | `lblStats` | الإحصائيات |
| `ListBox` | `lstTop` | الكلمات الأكثر تكرارًا |
| `ListBox` | `lstFound` | الأرقام والبريد والروابط |
| `Button` | `btnClear` | `امسح` |

## 2) المنطق أولًا في الكونسول

نكتب دالة `analyze` تُرجع مرجعًا لقاموس فيه كل النتائج، ونجربها على نص ثابت:

```perl run
use strict;
use warnings;

sub analyze {
    my ($text) = @_;
    my %r;
    $r{emails} = [ $text =~ /([\w.]+@[\w.]+\.\w+)/g ];
    (my $plain = $text) =~ s/[\w.]+@[\w.]+\.\w+//g;     # البريد ليس كلمات
    my @words = map { lc } $plain =~ /([A-Za-z']+)/g;
    $r{words} = scalar @words;
    $r{chars} = () = $text =~ /\S/g;
    $r{sentences} = () = $plain =~ /[.!?]+(?:\s|$)/g;
    my %freq;
    $freq{$_}++ for grep { length > 2 } @words;
    $r{top} = [ (sort { $freq{$b} <=> $freq{$a} || $a cmp $b } keys %freq)[0 .. 2] ];
    $r{freq} = \%freq;
    $r{numbers} = [ $plain =~ /\b(\d+(?:\.\d+)?)\b/g ];
    return \%r;
}

my $sample = "Perl is great. Perl handles text! Contact ali\@mail.com or call 0100 before 5.30. Text text.";
my $r = analyze($sample);
print "كلمات: $r->{words}، جمل: $r->{sentences}، حروف: $r->{chars}\n";
print "الأكثر تكرارًا: ", join(", ", map { "$_ ($r->{freq}{$_})" } @{ $r->{top} }), "\n";
print "أرقام: @{ $r->{numbers} }\n";
print "بريد: @{ $r->{emails} }\n";
```

```text output
كلمات: 12، جمل: 4، حروف: 77
الأكثر تكرارًا: text (3), perl (2), before (1)
أرقام: 0100 5.30
بريد: ali@mail.com
```

بعض الحيل في هذا الكود:

- `map { lc } ...` تحوّل كل الكلمات إلى حروف صغيرة لكي تُعد `Text` و`text` كلمة واحدة.
- `$r{chars} = () = $text =~ /\S/g;` تعد التطابقات (حيلة «العدّ» التي رأيناها في درس التعابير النمطية).
- `(sort ...)[0 .. 2]` تأخذ أول ثلاثة عناصر من القائمة المرتبة.
- `(?:...)` أقواس **لا تلتقط**: تجمع جزءًا من النمط دون أن يظهر في النتائج. و`[.!?]+(?:\s|$)` تعد علامة نهاية الجملة فقط إذا جاءت بعدها مسافة أو نهاية النص، فلا تُحسب النقطة في `5.30` جملة.
- نستخرج البريد أولًا ثم نحذفه من نسخة النص `$plain`، لكي لا تُعد أجزاء مثل `mail` و`com` كلمات.
- في الكونسول كتبنا `\@` داخل النص لكي لا تظن Perl أن `@mail` مصفوفة.

## 3) ربط المنطق بالنافذة

<!-- test: {"set": {"txtInput.Text": "Perl is great. Perl handles text! Mail ali@mail.com or sara@site.org now. Text text."}, "events": ["btnAnalyze.Click"], "expect": {"lblStats.Text": "الكلمات: 11 | الجمل: 4 | الحروف: 72", "lstTop.items": "text × 3|perl × 2|great × 1", "lstFound.items": "بريد: ali@mail.com|بريد: sara@site.org"}, "captions": {"btnAnalyze": "حلّل", "btnClear": "امسح"}} -->
```perl form run
use strict;
use warnings;
use RadGUI;

sub analyze {
    my ($text) = @_;
    my %r;
    $r{emails} = [ $text =~ /([\w.]+@[\w.]+\.\w+)/g ];
    (my $plain = $text) =~ s/[\w.]+@[\w.]+\.\w+//g;     # البريد ليس كلمات
    my @words = map { lc } $plain =~ /([A-Za-z']+)/g;
    $r{words} = scalar @words;
    $r{chars} = () = $text =~ /\S/g;
    $r{sentences} = () = $plain =~ /[.!?]+(?:\s|$)/g;
    my %freq;
    $freq{$_}++ for grep { length > 2 } @words;
    my @sorted = sort { $freq{$b} <=> $freq{$a} || $a cmp $b } keys %freq;
    $r{top} = [ grep { defined } @sorted[0 .. 2] ];
    $r{freq} = \%freq;
    $r{numbers} = [ $plain =~ /\b(\d+(?:\.\d+)?)\b/g ];
    return \%r;
}

sub btnAnalyze_Click {
    my $text = rad_get("txtInput", "Text");
    if ($text !~ /\S/) {
        rad_msgbox("الصق نصًا أولًا");
        return;
    }
    my $r = analyze($text);
    rad_set("lblStats", "Text",
            "الكلمات: $r->{words} | الجمل: $r->{sentences} | الحروف: $r->{chars}");
    rad_call("lstTop", "Clear");
    rad_call("lstTop", "AddItem", "$_ × $r->{freq}{$_}") for @{ $r->{top} };
    rad_call("lstFound", "Clear");
    rad_call("lstFound", "AddItem", "رقم: $_") for @{ $r->{numbers} };
    rad_call("lstFound", "AddItem", "بريد: $_") for @{ $r->{emails} };
}

sub btnClear_Click {
    rad_set("txtInput", "Text", "");
    rad_set("lblStats", "Text", "");
    rad_call($_, "Clear") for qw(lstTop lstFound);
}

1;
```

اضغط **F5** والصق فقرة من أي مقال إنجليزي، ثم اضغط «حلّل».

## 4) نظرة على التصميم

- الدالة `analyze` **لا تعرف شيئًا عن النافذة**: تأخذ نصًا وتُرجع نتائج. لذلك جربناها في الكونسول أولًا.
- الحدث `btnAnalyze_Click` يقرأ من النافذة، ويستدعي `analyze`، ثم يكتب النتائج.
- `grep { defined } @sorted[0 .. 2]` تمنع ظهور عناصر فارغة إذا كان في النص أقل من ثلاث كلمات مختلفة.

## 5) التتبع

- `print` داخل الحدث تكتب في **Output**: جرّب `print "words: $r->{words}\n";`.
- ضع نقطة توقف (**F9**) على سطر `my $r = analyze($text);` وشغّل بـ **F5**، ثم **F11** (**Step Into**، خطوة إلى الداخل) لتدخل داخل `analyze` وترى المتغيرات في **Locals**.

## أفكار للتطوير

- استخراج **الروابط** `https?://\S+` في `lstFound`.
- مربع اختيار `chkIgnoreShort` يتحكم في تجاهل الكلمات القصيرة.
- زر **حفظ التقرير** يكتب النتائج في ملف `report.txt` (درس الملفات).

## تمرين

أضف إلى `analyze` استخراج الروابط (التي تبدأ بـ `http://` أو `https://`)، وأضفها إلى `lstFound` بالشكل `رابط: ...`.

<!-- test: {"set": {"txtInput.Text": "Visit https://rad.dev and http://perl.org today"}, "events": ["btnAnalyze.Click"], "expect": {"lstFound.items": "رابط: https://rad.dev|رابط: http://perl.org"}} -->
```perl form exercise
use strict;
use warnings;
use RadGUI;

sub find_links {
    my ($text) = @_;
    # return ...;
}

sub btnAnalyze_Click {
    my $text = rad_get("txtInput", "Text");
    rad_call("lstFound", "Clear");
    rad_call("lstFound", "AddItem", "رابط: $_") for find_links($text);
}

1;
```

<!-- test: {"set": {"txtInput.Text": "Visit https://rad.dev and http://perl.org today"}, "events": ["btnAnalyze.Click"], "expect": {"lstFound.items": "رابط: https://rad.dev|رابط: http://perl.org"}, "captions": {"btnAnalyze": "حلّل"}} -->
```perl form solution
use strict;
use warnings;
use RadGUI;

sub find_links {
    my ($text) = @_;
    return $text =~ m{(https?://\S+)}g;
}

sub btnAnalyze_Click {
    my $text = rad_get("txtInput", "Text");
    rad_call("lstFound", "Clear");
    rad_call("lstFound", "AddItem", "رابط: $_") for find_links($text);
}

1;
```

`m{...}` نفس `/.../` لكن بأقواس مختلفة، مفيدة عندما يحتوي النمط على `/` مثل الروابط، فلا تحتاج إلى `\/`.

## اختبر نفسك

```quiz
{"question": "ما فائدة الأقواس (?:...) في التعبير النمطي؟", "choices": ["تلتقط الجزء في $1", "تجمع جزءًا من النمط دون التقاطه", "تجعل النمط اختياريًا", "تتجاهل حالة الأحرف"], "answer": 1, "explanation": "(?:...) للتجميع فقط، فلا يظهر الجزء في النتائج."}
```

```quiz
{"question": "لماذا فصلنا analyze عن أحداث النافذة؟", "choices": ["لأن Perl تشترط ذلك", "لنختبر المنطق في الكونسول ونعيد استخدامه دون النافذة", "لتسريع النافذة", "لا يوجد سبب"], "answer": 1, "explanation": "الدالة التي لا تعرف شيئًا عن الواجهة يسهل اختبارها وإعادة استخدامها."}
```

## الخلاصة

- بنينا محلل نصوص يعتمد على التعابير النمطية والقواميس.
- الدالة `analyze` تُرجع مرجعًا لقاموس فيه كل النتائج.
- الأحداث تقرأ من النافذة وتكتب النتائج بـ `rad_set` و`rad_call`.
- `m{...}` بديل لـ `/.../` عندما يحتوي النمط على شرطات مائلة.
