# الدرس 6: النصوص (Strings)

**في هذا الدرس ستتعلم:**

- أهم دوال النصوص: `len` و`upper` و`lower` و`left` و`right` و`substr` و`trim`.
- الوصول إلى حرف معيّن والمرور على حروف النص.
- البحث والاستبدال وتقسيم النص إلى قائمة.
- ملاحظة مهمة عن طول النص العربي.

## النص سلسلة من الحروف

**النص** (string) سلسلة من الحروف. ويمكنك الوصول إلى أي حرف برقمه كما في القوائم، والترقيم يبدأ من 1:

```ring run
cWord = "Ring"
see cWord[1] + nl
see "عدد الحروف: " + len(cWord) + nl
for cChar in cWord
    see cChar + "-"
next
see nl
```

```text output
R
عدد الحروف: 4
R-i-n-g-
```

## أهم دوال النصوص

| الدالة | العمل | مثال | الناتج |
|---|---|---|---|
| `len(c)` | الطول | `len("Hello")` | `5` |
| `upper(c)` | أحرف كبيرة | `upper("ring")` | `RING` |
| `lower(c)` | أحرف صغيرة | `lower("RING")` | `ring` |
| `left(c, n)` | أول `n` حروف | `left("Hello", 2)` | `He` |
| `right(c, n)` | آخر `n` حروف | `right("Hello", 3)` | `llo` |
| `trim(c)` | حذف المسافات من الطرفين | `trim("  hi  ")` | `hi` |
| `copy(c, n)` | تكرار النص `n` مرة | `copy("=", 5)` | `=====` |
| `reverse(c)` | عكس النص | `reverse("abc")` | `cba` |

```ring run
cName = "  Mohammed Fayed  "
cName = trim(cName)
see "[" + cName + "]" + nl
see upper(cName) + nl
see lower(cName) + nl
see left(cName, 8) + nl
see right(cName, 5) + nl
see copy("=", 15) + nl
```

```text output
[Mohammed Fayed]
MOHAMMED FAYED
mohammed fayed
Mohammed
Fayed
===============
```

## الدالة متعددة الوجوه: `substr`

الدالة `substr` تعمل ثلاثة أعمال حسب ما تعطيها:

| الصيغة | العمل |
|---|---|
| `substr(c, n)` | النص من الحرف رقم `n` حتى النهاية |
| `substr(c, n, count)` | `count` حروف بدءًا من الحرف رقم `n` |
| `substr(c, "كلمة")` | **مكان** الكلمة داخل النص (أو `0` إذا لم توجد) |
| `substr(c, "قديم", "جديد")` | **استبدال** كل «قديم» بـ «جديد» |

```ring run
cText = "I love Ring language"
see substr(cText, 8) + nl
see substr(cText, 8, 4) + nl
see substr(cText, "Ring")
see nl
see substr(cText, "Python")
see nl
see substr(cText, "love", "enjoy") + nl
```

```text output
Ring language
Ring
8
0
I enjoy Ring language
```

## تقسيم النص إلى قائمة

الدالة `str2list(c)` تقسم النص إلى قائمة، كل **سطر** في عنصر. فإذا أردنا التقسيم عند الفاصلة، نستبدل الفاصلة بسطر جديد أولًا:

```ring run
cLine = "علي,90,القاهرة"
aParts = str2list(substr(cLine, ",", nl))
see "الاسم: " + aParts[1] + nl
see "الدرجة بعد المكافأة: " + (number(aParts[2]) + 5) + nl
see "المدينة: " + aParts[3] + nl
```

```text output
الاسم: علي
الدرجة بعد المكافأة: 95
المدينة: القاهرة
```

والعكس: `list2str(aList)` تجمع القائمة في نص واحد، كل عنصر في سطر.

> **ملحوظة:** في المكتبة القياسية `stdlib.ring` دالة جاهزة `split(c, ",")` تفعل نفس الشيء. لاستخدامها اكتب في أول الملف `load "stdlib.ring"`.

## مقارنة النصوص

```ring run
cAnswer = "YES"
if cAnswer = "yes"
    see "متطابقة تمامًا" + nl
ok
if lower(cAnswer) = "yes"
    see "متطابقة بعد توحيد حالة الأحرف" + nl
ok
see strcmp("Ali", "Sara")
see nl
```

```text output
متطابقة بعد توحيد حالة الأحرف
-1
```

`strcmp(a, b)` تُرجع رقمًا سالبًا إذا كان `a` قبل `b` أبجديًا، و`0` إذا تساويا، وموجبًا إذا كان بعده.

## حروف وأرقامها

كل حرف له رقم في جدول ASCII. `ascii(c)` تعطي رقم الحرف، و`char(n)` تعطي الحرف من رقمه:

```ring run
see ascii("A")
see nl
see char(66) + nl
see isdigit("2026")
see nl
see isalpha("Ring2")
see nl
```

```text output
65
B
1
0
```

## ملاحظة مهمة: النص العربي

النصوص في Ring تُخزَّن بترميز **UTF-8**، والدالة `len()` تعدّ **البايتات** وليس الحروف. الحرف الإنجليزي بايت واحد، أما الحرف العربي فبايتان:

```ring run
see len("Ring")
see nl
see len("مرحبا")
see nl
```

```text output
4
10
```

لهذا لا تستخدم `left()` و`right()` و`cText[n]` على النص العربي، لأنها قد تقطع الحرف من منتصفه. أما **البحث والاستبدال والمقارنة والطباعة** فتعمل مع العربية بلا مشكلة.

ولعدّ الحروف الحقيقية نعدّ البايتات التي **تبدأ** حرفًا (كل بايت رقمه أقل من 128 أو من 192 فما فوق):

```ring run
cText = "مرحبا Ring"
nChars = 0
for cByte in cText
    if ascii(cByte) < 128 or ascii(cByte) >= 192
        nChars++
    ok
next
see "عدد الحروف: " + nChars + nl
see "عدد البايتات: " + len(cText) + nl
```

```text output
عدد الحروف: 10
عدد البايتات: 15
```

> في النوافذ الرسومية (RingQt) التي سنتعلمها لاحقًا يتعامل مربع النص مع العربية حرفًا حرفًا بشكل صحيح.

## أخطاء شائعة

- **نسيان أن `substr` بثلاثة نصوص تستبدل:** `substr(c, "a", "b")` لا تقطع النص بل تستبدل.
- **استخدام `left()` على نص عربي:** قد تظهر علامات استفهام أو رموز غريبة لأن الحرف قُطع.
- **مقارنة نصين بحالة أحرف مختلفة:** وحّدهما بـ `lower()` أولًا.

## تمارين

### التمرين 1: الاسم المختصر

اطبع أول حرف من الاسم الأول وأول حرف من اسم العائلة، مثلًا `Mohammed Fayed` يعطي `M.F.`.

```ring exercise
cFirst = "Mohammed"
cLast = "Fayed"
# اطبع M.F.
```

```ring solution
cFirst = "Mohammed"
cLast = "Fayed"
see left(cFirst, 1) + "." + left(cLast, 1) + "." + nl
```

```text output
M.F.
```

### التمرين 2: عدّ الحرف

احسب كم مرة يظهر الحرف `a` في النص (بعد تحويل النص إلى أحرف صغيرة).

```ring exercise
cText = "Ring is A small and fast language"
# عدّ الحرف a
```

```ring solution
cText = "Ring is A small and fast language"
nCount = 0
for c in lower(cText)
    if c = "a"
        nCount++
    ok
next
see "عدد مرات a: " + nCount + nl
```

```text output
عدد مرات a: 6
```

### التمرين 3: هل هي متناظرة؟

الكلمة المتناظرة (palindrome) تُقرأ من الجهتين نفس القراءة، مثل `level`. اطبع هل الكلمة متناظرة.

```ring exercise
cWord = "level"
# استخدم reverse()
```

```ring solution
cWord = "level"
if reverse(cWord) = cWord
    see cWord + " متناظرة" + nl
else
    see cWord + " غير متناظرة" + nl
ok
```

```text output
level متناظرة
```

## اختبر نفسك

```quiz
{"question": "ما ناتج `substr(\"Hello World\", \"World\")`؟", "choices": ["World", "7", "Hello", "0"], "answer": 1, "explanation": "مع نص واحد للبحث تُرجع substr مكانه: الحرف رقم 7."}
```

```quiz
{"question": "لماذا تعطي `len(\"سلام\")` الرقم 8؟", "choices": ["خطأ في Ring", "لأن len تعدّ البايتات والحرف العربي بايتان في UTF-8", "لأنها تعدّ المسافات", "لأن العربية تُكتب من اليمين"], "answer": 1, "explanation": "النص مخزن بترميز UTF-8، وlen تعدّ البايتات."}
```

```quiz
{"question": "كيف تستبدل كل \"-\" في النص c بمسافة؟", "choices": ["`replace(c, \"-\", \" \")`", "`substr(c, \"-\", \" \")`", "`c - \"-\"`", "`trim(c, \"-\")`"], "answer": 1, "explanation": "substr مع نصين بعد النص الأصلي تستبدل."}
```

## الخلاصة

- `len` و`upper` و`lower` و`left` و`right` و`trim` و`copy` و`reverse`.
- `substr` تقطع، وتبحث، وتستبدل حسب ما تعطيها.
- `str2list` و`list2str` للتحويل بين النص والقائمة.
- `len` تعدّ البايتات: انتبه مع النص العربي.
