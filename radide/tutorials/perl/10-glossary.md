# الدرس 10: قاموس المصطلحات (إنجليزي - عربي)

أهم المصطلحات التي مرت بك في دورة Perl.

## أساسيات

| English | العربية | مثال في Perl |
|---|---|---|
| scalar | قيمة مفردة (رقم أو نص) | `$age` |
| array | مصفوفة | `@names` |
| hash | قاموس (مفتاح وقيمة) | `%price` |
| sigil | الرمز قبل اسم المتغير | `$` `@` `%` |
| lexical variable | متغير محلي | `my $x` |
| undef | قيمة غير معرّفة | `undef` |
| interpolation | استيفاء (متغير داخل نص) | `"Hi $name"` |
| concatenation | لصق النصوص | `"a" . "b"` |
| repetition operator | عامل التكرار | `"-" x 10` |
| context (scalar / list) | السياق (مفرد / قائمة) | `scalar(@a)` |
| default variable | المتغير الافتراضي | `$_` |

## التحكم والدوال

| English | العربية | مثال |
|---|---|---|
| condition | شرط | `if (...) { }` |
| statement modifier | شرط أو حلقة في آخر السطر | `print "x" if $ok;` |
| loop | حلقة تكرار | `foreach my $x (@a)` |
| range | مدى | `1 .. 10` |
| next / last | الدورة التالية / اخرج من الحلقة | |
| subroutine | دالة (روتين فرعي) | `sub add { }` |
| argument list | قائمة المعاملات | `@_` |
| return value | القيمة المرجعة | `return $x;` |

## المراجع والبيانات المتداخلة

| English | العربية | مثال |
|---|---|---|
| reference | مرجع | `\@a` / `\%h` |
| dereference | الوصول عبر المرجع | `@$ref` / `$ref->[0]` |
| anonymous array / hash | مصفوفة / قاموس مجهول | `[1, 2]` / `{a => 1}` |
| code reference | مرجع دالة | `sub { ... }` |
| arrow operator | عامل السهم | `$p->{name}` |

## التعابير النمطية

| English | العربية | مثال |
|---|---|---|
| regular expression (regex) | تعبير نمطي | `/\d+/` |
| match / binding operator | مطابقة / عامل الربط | `$s =~ /x/` |
| substitution | استبدال | `s/old/new/g` |
| capture group | مجموعة التقاط | `(\d+)` ثم `$1` |
| character class | مجموعة حروف | `[a-z]` |
| quantifier | مكرِّر | `+` `*` `?` `{3}` |
| anchor | مرساة (بداية / نهاية) | `^` `$` |
| modifier / flag | معدِّل | `/i` `/g` `/x` |
| greedy / non-greedy | طمّاع / غير طمّاع | `.*` / `.*?` |

## الملفات والأخطاء

| English | العربية |
|---|---|
| filehandle | مقبض ملف |
| open mode (read / write / append) | وضع الفتح (قراءة / كتابة / إضافة) |
| die / warn | أوقف برسالة / حذّر |
| eval block | كتلة التقاط الأخطاء |
| error variable | متغير الخطأ (`$@` و`$!`) |

## الواجهات الرسومية

| English | العربية |
|---|---|
| form / control | نموذج / أداة (عنصر تحكم) |
| event / event handler | حدث / معالج حدث |
| property | خاصية |
| Toolbox / Properties | صندوق الأدوات / الخصائص |
| GUI Bridge | جسر الواجهة |

## اختبر نفسك

```quiz
{"question": "ما الترجمة الأنسب لـ capture group؟", "choices": ["مجموعة أخطاء", "مجموعة التقاط في التعبير النمطي", "قائمة ملفات", "مجموعة متغيرات"], "answer": 1, "explanation": "الأقواس في التعبير النمطي تلتقط الجزء المطابق ليُستخدم في $1 و$2."}
```

## إلى أين بعد ذلك؟

- **CPAN** (cpan.org): أكثر من 200 ألف وحدة جاهزة لكل شيء تقريبًا. في RAD IDE: **Project > Manage Packages...** (مشروع > إدارة الحزم...).
- **perldoc**: التوثيق الرسمي، مثل `perldoc perlretut` لشرح التعابير النمطية.
- جرّب دورات أخرى في **Help > Tutorials (Arabic lessons)...**.
