# الدرس 4: حلقات التكرار

**في هذا الدرس ستتعلم:**

- حلقة العدّ `for ... next` والخطوة `step`.
- حلقة `for ... in` للمرور على عناصر قائمة.
- حلقة `while ... end` وحلقة `do ... again`.
- التحكم في الحلقة بـ `exit` و`loop`.

## لماذا نحتاج حلقات التكرار؟

تخيّل أنك تريد طباعة الأرقام من 1 إلى 100. هل ستكتب 100 سطر؟ **حلقة التكرار** (loop) تكرر مجموعة من التعليمات عددًا من المرات نحدده نحن.

> **تشبيه:** حلقة التكرار مثل العدّاء في مضمار دائري: يكرر نفس اللفة حتى يصل إلى العدد المطلوب ثم يتوقف.

## حلقة `for ... next`

```ring
for المتغير = البداية to النهاية
    التعليمات
next
```

```ring run
for i = 1 to 5
    see "اللفة رقم " + i + nl
next
```

```text output
اللفة رقم 1
اللفة رقم 2
اللفة رقم 3
اللفة رقم 4
اللفة رقم 5
```

### الخطوة `step`

`step` تحدد مقدار الزيادة في كل لفة، ويمكن أن تكون سالبة للعدّ التنازلي:

```ring run
for i = 0 to 10 step 2
    see "" + i + " "
next
see nl
for i = 5 to 1 step -1
    see "" + i + " "
next
see "انطلق!" + nl
```

```text output
0 2 4 6 8 10 
5 4 3 2 1 انطلق!
```

لاحظ `"" + i`: بدأنا بنص فارغ لأن `i` رقم، والرقم + نص يعطي خطأ كما تعلمنا في الدرس 2.

### مثال: مجموع الأرقام

```ring run
nSum = 0
for i = 1 to 100
    nSum += i
next
see "مجموع الأرقام من 1 إلى 100 = " + nSum + nl
```

```text output
مجموع الأرقام من 1 إلى 100 = 5050
```

### جدول الضرب: حلقة داخل حلقة

```ring run
for i = 1 to 3
    for j = 1 to 3
        see "" + i + "x" + j + "=" + (i * j) + "  "
    next
    see nl
next
```

```text output
1x1=1  1x2=2  1x3=3
2x1=2  2x2=4  2x3=6
3x1=3  3x2=6  3x3=9
```

## حلقة `for ... in`

تمر على كل عنصر في **قائمة** (سنتعلم القوائم بالتفصيل في الدرس القادم):

```ring run
aFruits = ["تفاح", "موز", "برتقال"]
for cFruit in aFruits
    see "أحب " + cFruit + nl
next
```

```text output
أحب تفاح
أحب موز
أحب برتقال
```

## حلقة `while ... end`

تكرر **ما دام** الشرط صحيحًا. مناسبة عندما لا نعرف عدد اللفات مسبقًا:

```ring run
nMoney = 100
nYear = 0
while nMoney < 200
    nMoney = nMoney * 1.10
    nYear++
end
see "يتضاعف المبلغ بعد " + nYear + " سنوات" + nl
```

```text output
يتضاعف المبلغ بعد 8 سنوات
```

## حلقة `do ... again`

تنفّذ الجسم **مرة واحدة على الأقل** ثم تختبر الشرط في الآخر: تعيد ما دام الشرط بعد `again` صحيحًا.

```ring run
n = 1
do
    see "" + n + " "
    n *= 3
again n < 100
see nl
```

```text output
1 3 9 27 81
```

## `exit` و`loop`

- `exit` تخرج من الحلقة فورًا (مثل `break` في لغات أخرى).
- `loop` تقفز إلى اللفة التالية (مثل `continue`).

```ring run
for i = 1 to 10
    if i = 8
        exit          # توقف تمامًا عند 8
    ok
    if i % 2 = 0
        loop          # تجاهل الأرقام الزوجية
    ok
    see "" + i + " "
next
see nl
```

```text output
1 3 5 7
```

## مثال: لعبة تخمين الرقم

البرنامج يكرر السؤال حتى يخمّن المستخدم الرقم الصحيح:

```ring run
nSecret = 7
nTries = 0
while true
    see "خمّن رقمًا من 1 إلى 10: "
    give cGuess
    nTries++
    nGuess = number(cGuess)
    if nGuess = nSecret
        see "أحسنت! عرفته في " + nTries + " محاولات" + nl
        exit
    but nGuess < nSecret
        see "أكبر من ذلك" + nl
    else
        see "أصغر من ذلك" + nl
    ok
end
```

```text input
3
9
7
```

```text output
خمّن رقمًا من 1 إلى 10: أكبر من ذلك
خمّن رقمًا من 1 إلى 10: أصغر من ذلك
خمّن رقمًا من 1 إلى 10: أحسنت! عرفته في 3 محاولات
```

> **نصيحة:** لتجعل الرقم السري عشوائيًا استخدم `random(9) + 1`، فالدالة `random(n)` تعطي رقمًا من 0 إلى n.

## أخطاء شائعة

- **الحلقة التي لا تنتهي:** نسيان تغيير المتغير داخل `while` فيبقى الشرط صحيحًا للأبد. إذا حدث هذا اضغط `Shift+F5` (**Debug > Stop Debugging**) لإيقاف البرنامج.
- **نسيان `next` أو `end`:** يعطي خطأ «Unclosed control structure».
- **الخلط بين نهاية الحلقات:** `for` تنتهي بـ `next`، و`while` بـ `end`، و`do` بـ `again`.

## تمارين

### التمرين 1: جدول ضرب الرقم 7

اطبع جدول ضرب 7 من 1 إلى 5 بالشكل `7 x 1 = 7`.

```ring exercise
for i = 1 to 5
    # أكمل
next
```

```ring solution
for i = 1 to 5
    see "7 x " + i + " = " + (7 * i) + nl
next
```

```text output
7 x 1 = 7
7 x 2 = 14
7 x 3 = 21
7 x 4 = 28
7 x 5 = 35
```

### التمرين 2: مضروب العدد

المضروب (factorial) للعدد 5 هو `5 x 4 x 3 x 2 x 1`. احسبه بحلقة `for`.

```ring exercise
n = 5
nResult = 1
# احسب المضروب
```

```ring solution
n = 5
nResult = 1
for i = 1 to n
    nResult *= i
next
see "مضروب " + n + " = " + nResult + nl
```

```text output
مضروب 5 = 120
```

### التمرين 3: مجموع حتى الصفر

اقرأ أرقامًا من المستخدم حتى يكتب `0`، ثم اطبع مجموعها.

```ring exercise
nSum = 0
# استخدم while أو do ... again مع give
```

```ring solution
nSum = 0
do
    give cNum
    nSum += number(cNum)
again number(cNum) != 0
see "المجموع = " + nSum + nl
```

```text input
5
10
20
0
```

```text output
المجموع = 35
```

## اختبر نفسك

```quiz
{"question": "بأي كلمة تنتهي حلقة for في Ring؟", "choices": ["end", "next", "again", "ok"], "answer": 1, "explanation": "for تنتهي بـ next، وwhile بـ end، وdo بـ again."}
```

```quiz
{"question": "ما الفرق بين while و do ... again؟", "choices": ["لا فرق", "do ... again تنفذ الجسم مرة واحدة على الأقل", "while أسرع دائمًا", "do ... again لا تقبل شرطًا"], "answer": 1, "explanation": "do ... again تختبر الشرط في النهاية، فتنفذ الجسم مرة على الأقل."}
```

```quiz
{"question": "ماذا تفعل الكلمة loop داخل حلقة؟", "choices": ["تخرج من الحلقة", "تنتقل إلى اللفة التالية", "تعيد البرنامج من أوله", "توقف البرنامج"], "answer": 1, "explanation": "loop مثل continue: تتجاهل باقي اللفة الحالية وتبدأ اللفة التالية."}
```

## الخلاصة

- `for i = 1 to n step s ... next` للعدّ.
- `for x in aList ... next` للمرور على القائمة.
- `while شرط ... end` و`do ... again شرط`.
- `exit` للخروج، و`loop` للفة التالية.
