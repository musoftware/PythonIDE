# الدرس 2: أول برنامج QBasic مع FreeBASIC

**في هذا الدرس ستتعلم:**

- إنشاء مشروع **QBasic / QuickBASIC** وبناء برنامج DOS حقيقي بالمترجم المجاني FreeBASIC.
- الطباعة والإدخال: `PRINT` و`INPUT`.
- المتغيرات وأنواعها، والشروط `IF` و`SELECT CASE`، والحلقات `FOR` و`DO`.
- البرامج الفرعية `SUB` و`FUNCTION` والمصفوفات `DIM`.
- الألوان والمؤشر: `COLOR` و`LOCATE` و`INKEY$`.
- قراءة أخطاء البناء في **Error List** (قائمة الأخطاء).

## QBasic و FreeBASIC

**QBasic** لغة BASIC بسيطة أتت مجانًا مع MS-DOS 5 عام 1991، وأختها الأكبر **QuickBASIC 4.5** كانت تُنتج ملفات `.EXE`. تعلّم عليها جيل كامل من المبرمجين. لكنهما من برامج مايكروسوفت التجارية، فلا تنزّلهما RAD IDE.

بدلًا منهما تستخدم RAD IDE المترجم الحر **FreeBASIC** بنسخته لنظام DOS، مع الخيار `-lang qb` الذي يجعله يفهم لهجة QBasic. يعمل المترجم نفسه داخل DOSBox-X دون نافذة، وينتج ملف `.EXE` حقيقيًّا لنظام DOS (ومعه `CWSDPMI.EXE` الذي يحتاجه البرنامج ليعمل بذاكرة 32 بت).

## مشروعك الأول

1. **File > New Project...** (ملف > مشروع جديد)، ثم مجموعة **DOS** ثم **QBasic / QuickBASIC**، والقالب **Hello (QBasic)**.
2. سمِّ المشروع `QbHello` واضغط **OK**.
3. افتح `MAIN.BAS` من مستكشف الحل، وامسح ما فيه واكتب:

```dos-qbasic run
' My first QBasic program
CLS
PRINT "Hello, DOS!"
PRINT "2 + 3 ="; 2 + 3
PRINT "Done."
END
```

```text output
Hello, DOS!
2 + 3 = 5
Done.
```

اضغط `Ctrl+F5`: تبني RAD IDE البرنامج ثم تشغّله في DOSBox-X. أول بناء يأخذ وقتًا أطول لأن المترجم يُنزَّل.

- `'` بداية تعليق.
- `CLS` يمسح الشاشة.
- `PRINT` يطبع؛ الفاصلة المنقوطة `;` تلصق القيمة التالية في نفس السطر. لاحظ أن QBasic يطبع الأعداد الموجبة بمسافة قبلها (مكان الإشارة).
- `END` نهاية البرنامج.

> **ملاحظة:** RAD IDE تحفظ ملفات DOS بترميز **CP437** ونهايات أسطر `CR LF` كما يتوقعها DOS، فلا تكتب فيها حروفًا عربية: DOS الأصلي لا يعرضها.

## الإدخال والمتغيرات

<!-- test: {"keys": "Ali~25~"} -->
```dos-qbasic run
DEFINT A-Z
INPUT "Your name"; N$
INPUT "Your age"; AGE
PRINT "Hello, "; N$; "!"
PRINT "In ten years you will be"; AGE + 10
END
```

```text output
Hello, Ali!
In ten years you will be 35
```

- `INPUT "سؤال"; متغير` يطبع السؤال وعلامة `?` ثم ينتظر أن يكتب المستخدم ويضغط Enter.
- نوع المتغير من آخر حرف في اسمه: `N$` نص، و`AGE%` عدد صحيح، و`X!` عدد عشري، و`X#` عشري مضاعف الدقة.
- `DEFINT A-Z` يجعل كل متغير بلا علامة عددًا صحيحًا، فـ `AGE` هنا صحيح.

لتجربة برنامج يقرأ لوحة المفاتيح دون نافذة، استخدم **Tools > Retro > DOS Programming > Run with Captured Output...** واكتب المفاتيح التي «يضغطها» المستخدم: `~` تعني Enter، و`` ` `` تعني Esc، و`_` تعني مسافة. مثلًا `Ali~25~`.

## الشروط والحلقات

```dos-qbasic run
DEFINT A-Z
FOR I = 1 TO 5
    IF I MOD 2 = 0 THEN
        PRINT I; "is even"
    ELSE
        PRINT I; "is odd"
    END IF
NEXT I
SCORE = 85
SELECT CASE SCORE
    CASE IS >= 90: PRINT "Excellent"
    CASE 75 TO 89: PRINT "Very good"
    CASE ELSE: PRINT "Keep going"
END SELECT
N = 1
DO WHILE N < 100
    N = N * 3
LOOP
PRINT "First power of 3 above 100:"; N
END
```

```text output
 1 is odd
 2 is even
 3 is odd
 4 is even
 5 is odd
Very good
First power of 3 above 100: 243
```

| التعليمة | العمل |
|---|---|
| `FOR I = 1 TO 5 ... NEXT I` | تكرار بعدد معروف (و`STEP 2` لخطوة أخرى) |
| `IF ... THEN ... ELSE ... END IF` | شرط |
| `SELECT CASE` | اختيار بين حالات كثيرة: قيمة، أو مدى `75 TO 89`، أو `IS >= 90` |
| `DO WHILE ... LOOP` و`DO ... LOOP UNTIL` | تكرار حتى يتحقق شرط |
| `MOD` | باقي القسمة |

## البرامج الفرعية والمصفوفات

```dos-qbasic run
DEFINT A-Z
DECLARE FUNCTION Total (A())
DECLARE SUB Stars (N)

DIM MARKS(1 TO 4)
MARKS(1) = 70: MARKS(2) = 95: MARKS(3) = 80: MARKS(4) = 55
PRINT "Total:"; Total(MARKS())
FOR I = 1 TO 4
    PRINT USING "Student # "; I;
    Stars MARKS(I) \ 10
NEXT I
END

FUNCTION Total (A())
    S = 0
    FOR I = LBOUND(A) TO UBOUND(A)
        S = S + A(I)
    NEXT I
    Total = S
END FUNCTION

SUB Stars (N)
    PRINT STRING$(N, "*")
END SUB
```

```text output
Total: 300
Student 1 *******
Student 2 *********
Student 3 ********
Student 4 *****
```

- `DIM MARKS(1 TO 4)` مصفوفة من أربعة أعداد.
- `FUNCTION` تُرجع قيمة بإسنادها إلى اسمها (`Total = S`)، و`SUB` لا تُرجع شيئًا وتُستدعى باسمها.
- `DECLARE` في أول الملف تعرّف البرامج الفرعية قبل استعمالها، كما كان محرر QBasic يكتبها تلقائيًّا.
- `\` قسمة صحيحة، و`STRING$(N, "*")` نص من N نجمة، و`PRINT USING` يطبع بقالب (`#` مكان رقم).

## الألوان والمؤشر ولوحة المفاتيح

برامج DOS الجميلة ترسم بالألوان في أماكن محددة من الشاشة:

<!-- test: {"keys": "q", "screen": true} -->
```dos-qbasic run
DEFINT A-Z
COLOR 15, 1
CLS
LOCATE 3, 30: PRINT "RAD IDE - QBasic"
COLOR 14, 1
LOCATE 5, 26: PRINT CHR$(201); STRING$(26, 205); CHR$(187)
LOCATE 6, 26: PRINT CHR$(186); " Press any key to finish  "; CHR$(186)
LOCATE 7, 26: PRINT CHR$(200); STRING$(26, 205); CHR$(188)
DO
    K$ = INKEY$
LOOP WHILE K$ = ""
COLOR 10, 1
LOCATE 9, 30: PRINT "You pressed: "; K$
END
```

```text output
                             RAD IDE - QBasic

                         ╔══════════════════════════╗
                         ║ Press any key to finish  ║
                         ╚══════════════════════════╝

                             You pressed: q
```

- `COLOR أمامي, خلفية`: 16 لونًا للحرف (0 أسود، 1 أزرق، 2 أخضر، 4 أحمر، 7 رمادي، 10 أخضر فاتح، 14 أصفر، 15 أبيض) و8 للخلفية.
- `LOCATE سطر, عمود` ينقل المؤشر (الشاشة 25 سطرًا و80 عمودًا، والعدّ من 1).
- `CHR$(201)` حرف من جدول CP437: `201` = `╔` و`205` = `═` و`187` = `╗` و`186` = `║` و`200` = `╚` و`188` = `╝`. نكتبها بأرقامها ليبقى الملف نصًّا بسيطًا.
- `INKEY$` يقرأ مفتاحًا دون انتظار (نص فارغ إن لم يُضغط شيء)، فنكرره في حلقة حتى يضغط المستخدم.

## أخطاء البناء

اكتب خطأ عمدًا ثم ابنِ من **Tools > Retro > DOS Programming > Build DOS Program** (أو `Ctrl+Shift+B`):

<!-- test: {"error_line": 3} -->
```dos-qbasic run
PRINT "Line 1"
X = 5
PRINT "Value: " X +
END
```

يظهر في نافذة **Error List** صف فيه رسالة FreeBASIC واسم الملف `MAIN.BAS` ورقم السطر 3. انقره نقرًا مزدوجًا ليقفز المحرر إلى السطر.

> **تمرين:** اكتب برنامجًا يسأل عن عدد ثم يطبع جدول ضربه من 1 إلى 10 بالصيغة `7 x 3 = 21`، ولوّن السطر الذي ناتجه أكبر من 50 بالأحمر (`COLOR 12`).

```quiz
{"question": "ماذا يطبع PRINT \"A\"; 5 في QBasic؟", "choices": ["A5", "A 5 (مسافة قبل العدد)", "A, 5"], "answer": 1, "explanation": "QBasic يحجز مكان الإشارة قبل العدد الموجب، فتظهر مسافة: A 5."}
```

```quiz
{"question": "أي دالة تقرأ مفتاحًا دون أن تنتظر المستخدم؟", "choices": ["INPUT", "INKEY$", "LINE INPUT"], "answer": 1, "explanation": "INKEY$ تُرجع المفتاح المضغوط أو نصًّا فارغًا فورًا، أما INPUT فينتظر Enter."}
```
