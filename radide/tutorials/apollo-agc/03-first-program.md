# الدرس 3: أول برنامج AGC - الإجراءات والجداول والتصحيح

**في هذا الدرس:**

- شكل السطر في صيغة **yaYUL** (صيغة Virtual AGC لمصدر أبولو) وقاعدة الأرقام الثمانية.
- أهم التعليمات: `CA` و`CS` و`TS` و`AD` و`INCR` و`XCH` و`TC` و`TCF` و`INDEX`.
- **الإجراءات** (Subroutines): `TC` و`Q` و`RETURN`.
- **الجداول** بالتعليمة `INDEX`، والتعليمات **الموسَّعة** بعد `EXTEND`.
- التشغيل خطوة خطوة في نافذة **Apollo AGC**.

## شكل السطر

```agc
LABEL           OPCODE  OPERAND         # تعليق
COUNT           ERASE                   # كلمة في الذاكرة المتغيرة اسمها COUNT
                CA      COUNT           # A = COUNT
ONE             DEC     1               # ثابت في الذاكرة الثابتة
```

- **التسمية** (Label) تبدأ في العمود الأول. إن بدأ السطر بمسافة فلا تسمية فيه.
- `#` يبدأ تعليقًا، و`##` تعليق توضيحي في ملفات أبولو المنقولة.
- **الأرقام ثمانية** إلا إذا احتوت 8 أو 9 أو انتهت بحرف `D`: `SETLOC 4000` ثماني، و`ERASE +20D` عشري. أما `DEC 100` فعشري دائمًا، و`OCT 37777` ثماني دائمًا.
- `$FILE.agc` يضمّ ملفًا آخر في هذا المكان (برنامج أبولو 11 نحو 90 ملفًا اسمها «أقسام السجل» Log Sections).

## أهم التعليمات

| التعليمة | المعنى |
|---|---|
| `CA K` | A = K (ومثلها `CAF` للثوابت و`CAE` للمتغيرة) |
| `CS K` | A = -K |
| `TS K` | K = A (وعند الفيضان تتخطى التعليمة التالية) |
| `AD K` | A = A + K |
| `INCR K` | K = K + 1 |
| `XCH K` | تبديل A مع K |
| `MASK K` | A = A AND K |
| `TC K` | استدعاء إجراء: Q = عنوان الرجوع ثم القفز إلى K؛ الرجوع بـ `RETURN` |
| `TCF K` | قفز إلى K |
| `CCS K` | عدّ ومقارنة وتخطٍّ رباعي (الدرس 2) |
| `INDEX K` | يضيف قيمة K إلى عنوان التعليمة التالية (للجداول) |
| `EXTEND` | التعليمة التالية **موسَّعة**: `READ` و`WRITE` (القنوات) و`DCA` و`SU` (طرح) و`BZF` (قفز إذا صفر) و`BZMF` (قفز إذا صفر أو سالب) و`MP` و`DV` |

مرّر الفأرة فوق أي تعليمة في المحرر لترى شرحها بالعربية، واضغط `F12` على أي اسم لتنتقل إلى تعريفه ولو كان في ملف آخر.

## جدول وإجراء

هذا البرنامج يجمع جدولًا من 5 أعداد بالتعليمة `INDEX`، ويستدعي إجراءً يضاعف النتيجة. لاحظ أن `TC` تضع عنوان الرجوع في `Q`، وأن `RETURN` تعني «اقفز إلى Q»:

<!-- test: {"show": ["TOTAL", "DOUBLED"]} -->
```agc run
Q               EQUALS  2               # RETURN = TC Q: يجب تعريف Q (كما في ملفات أبولو)
ZERO            EQUALS  7

                SETLOC  100
TOTAL           ERASE
DOUBLED         ERASE
I               ERASE                   # فهرس الجدول: 4 ثم 3 ... ثم 0

                SETLOC  4000
                INHINT
                TCF     START

START           CA      ZERO
                TS      TOTAL
                CAF     FOUR
                TS      I               # ابدأ من آخر عنصر

LOOP            INDEX   I               # العنوان التالي + I
                CA      TABLE           # A = TABLE[I]
                AD      TOTAL
                TS      TOTAL
                CCS     I
                TCF     NEXT            # I > 0
                TCF     SUMMED          # I = 0: انتهى الجدول
                TCF     SUMMED
                TCF     SUMMED
NEXT            TS      I
                TCF     LOOP

SUMMED          TC      DOUBLE          # استدعاء: Q = عنوان السطر التالي
                TS      DOUBLED
DONE            TCF     DONE

DOUBLE          CA      TOTAL           # إجراء: A = 2 × TOTAL
                AD      TOTAL
                RETURN                  # ارجع إلى Q

FOUR            DEC     4
TABLE           DEC     3               # TABLE[0]
                DEC     1
                DEC     4
                DEC     1
                DEC     5               # TABLE[4]
```

```text output
TOTAL = 14
DOUBLED = 28
```

## التعليمات الموسَّعة: أكبر عدد في الجدول

`BZMF` (اقفز إذا كانت A صفرًا أو سالبة) و`SU` (اطرح) تعليمتان **موسَّعتان**: يجب أن تسبقهما `EXTEND`. السبب: رمز التعليمة 3 بتات فقط (8 تعليمات)، فاستُعملت `EXTEND` لتعطي الرموز نفسها معنى ثانيًا.

<!-- test: {"show": ["BEST"]} -->
```agc run
                SETLOC  100
BEST            ERASE
I               ERASE

                SETLOC  4000
                INHINT
                TCF     START

START           CAF     TABLE           # أفضل قيمة حتى الآن = أول عنصر
                TS      BEST
                CAF     FOUR
                TS      I

LOOP            INDEX   I
                CA      TABLE           # A = TABLE[I]
                EXTEND
                SU      BEST            # A = TABLE[I] - BEST
                EXTEND
                BZMF    SKIP            # ليس أكبر
                INDEX   I
                CA      TABLE
                TS      BEST            # عنصر أكبر
SKIP            CCS     I
                TCF     NEXT
                TCF     DONE
                TCF     DONE
                TCF     DONE
NEXT            TS      I
                TCF     LOOP

DONE            TCF     DONE

FOUR            DEC     4
TABLE           DEC     17
                DEC     250
                DEC     -40
                DEC     99
                DEC     251
```

```text output
BEST = 251
```

## شغّل خطوة خطوة

1. أنشئ مشروع **Apollo AGC Program** بالقالب **Empty AGC Program**، والصق البرنامج في `MAIN.agc`.
2. ضع نقطة توقف (`F9`) على سطر `LOOP` واضغط `F5`: يتوقف البرنامج وتظهر في **Locals** المسجلات `A` و`L` و`Q` و`Z` ومتغيراتك.
3. اضغط `F10` وراقب `A` في تبويب **Registers** و`BEST` في **Variables**، أو افتح **Erasable Memory** واختر البنك E0.
4. في نافذة **Watch** اكتب `BEST` أو `A` أو عنوانًا ثمانيًا مثل `100`.
5. **Tools > Retro > Apollo AGC > Assembly Listing** يعرض كل سطر وعنوانه (بنك، عنوان) وكلمته الثمانية.

## اختبر فهمك

```quiz
{"question": "ماذا تعني 20 في السطر SETLOC 20 بصيغة yaYUL؟", "choices": ["عشرون بالعشري", "ستة عشر (20 ثماني)", "خطأ لأن الرقم يجب أن ينتهي بـ D", "عنوان في الذاكرة الثابتة"], "answer": 1, "explanation": "الأرقام التي فيها 0-7 فقط ثمانية في yaYUL: 20 ثماني = 16 عشري."}
```

```quiz
{"question": "لماذا نكتب EXTEND قبل BZMF؟", "choices": ["لأن BZMF تعليمة موسَّعة لا تعمل إلا بعد EXTEND", "لتسريع القفز", "لأنها تمنع المقاطعات", "لا داعي لها"], "answer": 0, "explanation": "التعليمات الموسَّعة تشترك في رموز التعليمات الأساسية، و EXTEND تخبر المعالج بأن التالية موسَّعة."}
```

```quiz
{"question": "أين يحفظ TC عنوان الرجوع؟", "choices": ["في A", "في المكدس", "في المسجل Q", "في Z"], "answer": 2, "explanation": "لا يوجد مكدس عتادي: TC يضع عنوان الرجوع في Q و RETURN يقفز إليه. لذلك يحفظ الإجراء المتداخل Q بنفسه."}
```
