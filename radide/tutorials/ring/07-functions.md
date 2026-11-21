# الدرس 7: الدوال (Functions)

**في هذا الدرس ستتعلم:**

- تعريف **دالة** بالكلمة `func` وتمرير المعاملات إليها.
- إرجاع قيمة بـ `return`.
- الدالة الرئيسية `main`، والمتغيرات العامة والمحلية.
- الدوال المجهولة (Anonymous Functions) والاستدعاء الذاتي (Recursion).

## ما هي الدالة؟

**الدالة** (function) مجموعة تعليمات لها اسم، نكتبها مرة واحدة ونستدعيها كلما احتجنا إليها.

> **تشبيه:** الدالة مثل ماكينة العصير: تضع فيها فاكهة (المعاملات)، فتعطيك عصيرًا (القيمة المرجعة). لا تحتاج أن تعرف ما يحدث بداخلها في كل مرة.

## تعريف الدالة واستدعاؤها

```ring
func اسم_الدالة المعامل1, المعامل2
    التعليمات
```

لا توجد كلمة لإنهاء الدالة: الدالة تنتهي عندما تبدأ دالة أخرى أو ينتهي الملف. ولهذا نكتب الدوال في **آخر** الملف، بعد الكود الذي يُنفذ مباشرة:

```ring run
sayHello("سارة")
sayHello("يوسف")

func sayHello cName
    see "أهلًا يا " + cName + "!" + nl
```

```text output
أهلًا يا سارة!
أهلًا يا يوسف!
```

## إرجاع قيمة: `return`

```ring run
see "5 + 3 = " + add(5, 3) + nl
see "مساحة الدائرة = " + circleArea(2) + nl

func add a, b
    return a + b

func circleArea r
    return 3.14159 * r * r
```

```text output
5 + 3 = 8
مساحة الدائرة = 12.57
```

الدالة التي لا تحتوي `return` تُرجع نصًا فارغًا.

## الدالة الرئيسية `main`

إذا كتبت دالة اسمها `main`، فإن Ring تنفّذها تلقائيًا بعد الكود الموجود في أعلى الملف. هذا أسلوب منظّم: كل برنامجك داخل `main`، والكود العلوي للمتغيرات العامة فقط. قالب **Console Application (Ring)** في RAD IDE يستخدم هذا الأسلوب.

```ring run
cAppName = "حاسبة الدرجات"      # متغير عام

func main
    see cAppName + nl
    see "النتيجة: " + gradeName(85) + nl

func gradeName nScore
    if nScore >= 90 return "ممتاز" ok
    if nScore >= 75 return "جيد جدًا" ok
    if nScore >= 50 return "ناجح" ok
    return "راسب"
```

```text output
حاسبة الدرجات
النتيجة: جيد جدًا
```

لاحظ كيف استخدمنا `return` داخل `if` لنخرج من الدالة مبكرًا.

## المتغيرات العامة والمحلية

- **المتغير العام** (global): يُكتب في أعلى الملف خارج الدوال، وتراه كل الدوال.
- **المتغير المحلي** (local): يُنشأ داخل دالة، ويختفي عند انتهائها.

```ring run
nVisits = 0           # عام

func main
    visit()
    visit()
    visit()
    see "عدد الزيارات: " + nVisits + nl

func visit
    nTemp = 1         # محلي: يُنشأ من جديد في كل استدعاء
    nVisits += nTemp
```

```text output
عدد الزيارات: 3
```

> **نصيحة:** أكثر من المتغيرات المحلية، وأقلل من العامة. الكود الذي يعتمد على متغيرات عامة كثيرة يصعب فهمه وتتبع أخطائه.

## القوائم تمر بالمرجع

الأرقام والنصوص تُنسخ عند تمريرها للدالة، أما **القوائم والكائنات** فتمر **بالمرجع**: الدالة تعمل على القائمة الأصلية نفسها:

```ring run
aPrices = [100, 200, 300]
addDelivery(aPrices)
see aPrices

func addDelivery aList
    for i = 1 to len(aList)
        aList[i] += 15        # مصاريف التوصيل
    next
```

```text output
115
215
315
```

> **ملحوظة عن الكسور:** لو ضربنا في `1.1` لظهر `110.00` بدل `110`، لأن الحاسوب يخزن `100 * 1.1` كقيمة قريبة جدًا من 110 وليست 110 بالضبط، فتطبعها Ring برقمين عشريين.

## الاستدعاء الذاتي (Recursion)

الدالة يمكن أن تستدعي نفسها. المهم أن يكون لها **شرط توقف**:

```ring run
see "5! = " + factorial(5) + nl
countDown(3)

func factorial n
    if n <= 1 return 1 ok
    return n * factorial(n - 1)

func countDown n
    if n = 0
        see "انطلق!" + nl
        return
    ok
    see "" + n + "..." + nl
    countDown(n - 1)
```

```text output
5! = 120
3...
2...
1...
انطلق!
```

## الدوال المجهولة

يمكن وضع دالة داخل متغير بالصيغة `func المعاملات { ... }`، ثم استدعاؤها بالكلمة `call`. هذا مفيد لتمرير «سلوك» إلى دالة أخرى:

```ring run
fDouble = func x { return x * 2 }
see call fDouble(21)
see nl
see applyAll([1, 2, 3, 4], func n { return n * n })

func applyAll aList, f
    aResult = []
    for x in aList
        add(aResult, call f(x))
    next
    return aResult
```

```text output
42
1
4
9
16
```

## أخطاء شائعة

- **استدعاء دالة غير موجودة أو كتابة اسمها خطأ:** `R3 Calling Function without definition`.
- **كتابة كود عادي بعد الدوال:** أي سطر بعد `func` يُعتبر جزءًا منها. ضع الكود الرئيسي في الأعلى أو داخل `main`.
- **نسيان الأقواس عند الاستدعاء:** `sayHello "علي"` خطأ؛ الصحيح `sayHello("علي")`.
- **الدالة لا تُرجع قيمة:** نسيت `return` فحصلت على نص فارغ.

## تمارين

### التمرين 1: الأكبر من ثلاثة

اكتب دالة `maxOf3(a, b, c)` تُرجع أكبر الأرقام الثلاثة.

```ring exercise
see maxOf3(4, 19, 7)
see nl

func maxOf3 a, b, c
    # أكمل
```

```ring solution
see maxOf3(4, 19, 7)
see nl

func maxOf3 a, b, c
    nMax = a
    if b > nMax nMax = b ok
    if c > nMax nMax = c ok
    return nMax
```

```text output
19
```

### التمرين 2: هل العدد أولي؟

اكتب دالة `isPrime(n)` تُرجع `1` إذا كان العدد أوليًا و`0` إذا لم يكن، ثم اطبع الأعداد الأولية حتى 20.

```ring exercise
for i = 2 to 20
    if isPrime(i) see "" + i + " " ok
next
see nl

func isPrime n
    # العدد الأولي لا يقبل القسمة إلا على 1 وعلى نفسه
```

```ring solution
for i = 2 to 20
    if isPrime(i) see "" + i + " " ok
next
see nl

func isPrime n
    if n < 2 return 0 ok
    for d = 2 to n - 1
        if n % d = 0 return 0 ok
    next
    return 1
```

```text output
2 3 5 7 11 13 17 19
```

### التمرين 3: تصفية القائمة

اكتب دالة `filterList(aList, f)` تُرجع العناصر التي تجعل الدالة `f` تُرجع `1`، واستخدمها لاستخراج الأعداد الزوجية.

```ring exercise
see filterList(1:10, func n { return n % 2 = 0 })

func filterList aList, f
    # أكمل
```

```ring solution
see filterList(1:10, func n { return n % 2 = 0 })

func filterList aList, f
    aOut = []
    for x in aList
        if call f(x)
            add(aOut, x)
        ok
    next
    return aOut
```

```text output
2
4
6
8
10
```

## اختبر نفسك

```quiz
{"question": "بماذا تبدأ تعريف الدالة في Ring؟", "choices": ["def", "function فقط", "func", "sub"], "answer": 2, "explanation": "نعرّف الدالة بالكلمة func (ويمكن أيضًا def)."}
```

```quiz
{"question": "متى تُنفذ الدالة main؟", "choices": ["لا تُنفذ إلا إذا استدعيناها", "تلقائيًا بعد الكود الموجود في أعلى الملف", "قبل أي كود", "عند الخطأ فقط"], "answer": 1, "explanation": "Ring تنفذ الكود العلوي أولًا ثم تستدعي main تلقائيًا."}
```

```quiz
{"question": "إذا مررت قائمة إلى دالة وغيّرت الدالة عناصرها، ماذا يحدث للقائمة الأصلية؟", "choices": ["لا تتغير", "تتغير لأن القوائم تمر بالمرجع", "تُحذف", "تتحول إلى نص"], "answer": 1, "explanation": "القوائم والكائنات تمر بالمرجع إلى الدوال."}
```

## الخلاصة

- `func name a, b` لتعريف الدالة، و`return` لإرجاع قيمة.
- الدوال تُكتب في آخر الملف، و`main` تُنفذ تلقائيًا.
- المتغير العام في أعلى الملف، والمحلي داخل الدالة.
- القوائم تمر بالمرجع، و`func x { ... }` مع `call` للدوال المجهولة.
