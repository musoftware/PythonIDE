# الدرس 8: المشروع النهائي - عدّ تنازلي على DSKY

**ستكتب برنامج AGC كاملًا يجمع كل ما تعلمته:**

- متجهات المقاطعة، ومقاطعة المؤقت `T3RUPT` كل جزء من مئة من الثانية (الدرس 4).
- حلقة رئيسية «تتنفس» لدائرة Night Watchman، فيعمل **مع إنذارات العتاد** دون إعادة تشغيل.
- عدّ تنازلي من 10 ثوانٍ بالتعليمة `CCS` (الدرس 2).
- قسمة على 10 بالطرح المتكرر، وجداول رموز الأرقام بـ `INDEX` (الدرس 3).
- عرض الثواني في السجل **R1** بكلمات المرحِّلات، وإضاءة المصباح **OPR ERR** عند الصفر (الدرس 5).

## الفكرة

```text
 T3RUPT (كل 0.01 ث)  ->  CENTI + 1،  وعند 100: TICKED = 1
 الحلقة الرئيسية     ->  إذا TICKED: SECS - 1، ثم SHOW
 SHOW                ->  TENS = SECS / 10، REM = SECS mod 10، ثم الكلمة 6 في القناة 10
 عند SECS = 0        ->  WRITE 11 ببت OPR ERR
```

## البرنامج

أنشئ مشروع **Apollo AGC Program** بالقالب **Empty AGC Program** باسم `Countdown`، والصق في `MAIN.agc` (هذا البرنامج لا يحتاج إيقاف الإنذارات):

<!-- test: {"alarms": true, "dsky_at": [0.5, 3.5, 11.5], "show": ["SECS"], "restarts": true} -->
```agc run
# COUNTDOWN - عدّ تنازلي من 10 ثوانٍ على DSKY (برنامج أصلي لـ RAD IDE، CC0)

Q               EQUALS  2
ZERO            EQUALS  7
ARUPT           EQUALS  10
TIME3           EQUALS  26
NEWJOB          EQUALS  67

# ------------------------------------------------------------------ الذاكرة المتغيرة
                SETLOC  100
SECS            ERASE                   # الثواني الباقية
CENTI           ERASE                   # أجزاء من مئة من الثانية
TICKED          ERASE                   # 1 = مرت ثانية
TENS            ERASE                   # SECS / 10
REM             ERASE                   # SECS mod 10

# ------------------------------------------------------------------ متجهات المقاطعة
                SETLOC  4000
                INHINT                  # 4000 GOJAM
                TCF     START
                NOOP
                NOOP
                RESUME                  # 4004 T6RUPT
                NOOP
                NOOP
                NOOP
                RESUME                  # 4010 T5RUPT
                NOOP
                NOOP
                NOOP
                DXCH    ARUPT           # 4014 T3RUPT
                TCF     T3HAND
                NOOP
                NOOP

# ------------------------------------------------------------------ البداية
START           CAF     TEN
                TS      SECS
                CA      ZERO
                TS      CENTI
                TS      TICKED
                EXTEND
                WRITE   11              # كل المصابيح مطفأة
                CAF     VERBWORD        # VERB 16
                EXTEND
                WRITE   10
                CAF     NOUNWORD        # NOUN 36
                EXTEND
                WRITE   10
                CAF     R1WORD8         # R1: الرقم الأول 0
                EXTEND
                WRITE   10
                CAF     R1WORD7         # إشارة + والرقمان 0 0
                EXTEND
                WRITE   10
                TC      SHOW
                CAF     T3LOAD
                TS      TIME3
                RELINT

# ------------------------------------------------------------------ الحلقة الرئيسية
MAIN            CA      NEWJOB          # «أنا حي»
                CA      TICKED
                EXTEND
                BZF     IDLE            # لم تمر ثانية
                CA      ZERO
                TS      TICKED
                CCS     SECS            # SECS > 0: A = SECS - 1
                TCF     DOWN
                TCF     MAIN            # وصلنا إلى الصفر من قبل
                TCF     MAIN
                TCF     MAIN
DOWN            TS      SECS
                TC      SHOW
                CCS     SECS            # هل صار صفرًا الآن؟
                TCF     MAIN
                TCF     ALARMON
                TCF     MAIN
                TCF     MAIN
ALARMON         CAF     OPRBIT          # مصباح OPR ERR
                EXTEND
                WRITE   11
IDLE            TCF     MAIN            # كل دورة تمر بـ TCF (شرط TC Trap)

# ------------------------------------------------------------------ SHOW: SECS في R1
SHOW            CA      ZERO
                TS      TENS
                CA      SECS
                TS      REM
DIVLOOP         CA      REM
                AD      NEG10           # A = REM - 10
                EXTEND
                BZF     EXACT           # يساوي 10 تمامًا (والنتيجة -0)
                EXTEND
                BZMF    DIVDONE         # أصغر من 10
                TS      REM
                INCR    TENS
                TCF     DIVLOOP
EXACT           CA      ZERO            # +0 لا -0 (لأننا سنستخدمه فهرسًا)
                TS      REM
                INCR    TENS
DIVDONE         CAF     W6BASE          # الكلمة 6: الرقمان 4 و 5 في R1
                INDEX   TENS
                AD      DIGLEFT
                INDEX   REM
                AD      DIGRIGHT
                EXTEND
                WRITE   10
                RETURN

# ------------------------------------------------------------------ T3RUPT
T3HAND          CAF     T3LOAD
                TS      TIME3
                INCR    CENTI
                CA      CENTI
                AD      NEG100          # CENTI - 100
                EXTEND
                BZF     ONESEC
                TCF     T3DONE
ONESEC          CA      ZERO
                TS      CENTI
                CAF     ONE
                TS      TICKED
T3DONE          DXCH    ARUPT
                RESUME

# ------------------------------------------------------------------ ثوابت
ONE             DEC     1
TEN             DEC     10
NEG10           DEC     -10
NEG100          DEC     -100
T3LOAD          OCT     37777
OPRBIT          OCT     100             # القناة 11 البت 7
VERBWORD        OCT     50174
NOUNWORD        OCT     45574
R1WORD8         OCT     40025
R1WORD7         OCT     37265
W6BASE          OCT     30000           # الكلمة 6 بلا أرقام
DIGRIGHT        OCT     25              # رموز الأرقام 0-9 في الخانة اليمنى
                OCT     3
                OCT     31
                OCT     33
                OCT     17
                OCT     36
                OCT     34
                OCT     23
                OCT     35
                OCT     37
DIGLEFT         OCT     1240            # الرموز نفسها مزاحة 5 بتات (الخانة اليسرى)
                OCT     140
                OCT     1440
                OCT     1540
                OCT     740
                OCT     1700
                OCT     1600
                OCT     1140
                OCT     1640
                OCT     1740
```

المدقق يشغّل البرنامج **مع إنذارات العتاد** ويلتقط شاشة DSKY عند نصف ثانية و3.5 ثانية و11.5 ثانية:

```text output
t=0.5s DSKY: PROG     VERB 16  NOUN 36  R1 +00010  R2         R3
t=3.5s DSKY: PROG     VERB 16  NOUN 36  R1 +00007  R2         R3
t=11.5s DSKY: PROG     VERB 16  NOUN 36  R1 +00000  R2         R3         [OPR ERR]
SECS = 0
restarts: 0
```

## افهم الأجزاء الصعبة

- **لماذا `EXACT`؟** في المتمم الأحادي `10 + (-10)` = **-0** (`77777`). لو خزّناها في `REM` ثم استخدمناها فهرسًا لـ `INDEX` لأضافت 77777 إلى العنوان! لذلك نضع +0 بأنفسنا.
- **لماذا جدولان للرموز؟** لا توجد تعليمة إزاحة رخيصة؛ جدول ثانٍ فيه الرموز مضروبة في 32 أسرع وأوضح.
- **لماذا `restarts: 0`؟** الحلقة تقرأ `NEWJOB` (Night Watchman)، والمقاطعة تأتي كل 10 ميلي ثانية وتنتهي بسرعة (Rupt Lock)، وكل دورة للحلقة تمر بـ `IDLE TCF MAIN` (TC Trap). جرّب أن تكتب `BZF MAIN` بدل `BZF IDLE`: `BZF` ليست `TC` ولا `TCF`، فلا تُنفَّذ أي `TC`/`TCF` أثناء الانتظار، فيعيد العتاد تشغيل الحاسوب مئات المرات (**NO TC**)، ولا يتحرك العدّ أبدًا. هذا ما اكتشفه مدقق الدورة في أول نسخة من هذا البرنامج!
- **`CCS SECS` مرتين**: الأولى تنقص الثواني، والثانية تكتشف الوصول إلى الصفر (التعليمة الثانية من الأربع).

## شغّله في RAD IDE

1. `F5`: نافذة **Apollo AGC** وعليها DSKY: يعدّ R1 من 10 إلى 0 ثم يضيء **OPR ERR**.
2. ضع نقطة توقف على `ONESEC`: يتوقف كل ثانية؛ راقب `CENTI` و`SECS` في **Variables**.
3. **تحديات:**
   - اجعل البداية 99 ثانية (الثابت `TEN`)، وتحقق أن العرض يصبح `+00099`.
   - أضف لوحة المفاتيح: مقاطعة `KEYRUPT1` عند `4024`، واقرأ المفتاح من القناة 15؛ اجعل `RSET` (الرمز 22) يعيد العد من البداية. راجع `KEYBOARD.agc` في مشروع Hello DSKY.
   - ابنِ البرنامج بـ **yaYUL** (Tools > Retro > Apollo AGC > Build with yaYUL) وشغّله في **yaAGC**: الناتج مطابق، لأن مجمِّع RAD IDE يطابق yaYUL كلمة بكلمة (المدقق يتحقق من ذلك عندما يكون yaYUL مثبتًا).

## ماذا تعلمت في الدورة؟

| الدرس | المهارة |
|---|---|
| 1 | قصة AGC ولوحة DSKY والملكية العامة لبرامج أبولو |
| 2 | الكلمة 15 بت والمتمم الأحادي والذاكرة والمسجلات و `CCS` |
| 3 | صيغة yaYUL والإجراءات والجداول والتعليمات الموسَّعة والتصحيح |
| 4 | المقاطعات وإنذارات العتاد |
| 5 | DSKY والأفعال والأسماء وكلمات المرحِّلات |
| 6 | Virtual AGC وبرنامج أبولو 11 الحقيقي وقراءته |
| 7 | فورتران 66/77 للبرامج العلمية |

```quiz
{"question": "لماذا يضع البرنامج +0 في REM بدل ناتج الجمع عندما كان REM = 10؟", "choices": ["لأن الناتج -0 (77777) وإن استُخدم فهرسًا لـ INDEX أضاف 77777 إلى العنوان", "لتسريع البرنامج", "لأن yaYUL يرفض -0", "لا سبب"], "answer": 0, "explanation": "في المتمم الأحادي x + (-x) = -0، و INDEX يضيف القيمة كما هي."}
```

```quiz
{"question": "ما الذي يجعل هذا البرنامج يعمل مع إنذارات العتاد دون إعادة تشغيل؟", "choices": ["أنه قصير", "قراءة NEWJOB في الحلقة، ومقاطعة مؤقت منتظمة وقصيرة، ومرور كل دورة بـ TCF", "أنه لا يستخدم DSKY", "إيقاف الإنذارات في project.radproj"], "answer": 1, "explanation": "هذه شروط Night Watchman و Rupt Lock و TC Trap من الدرس 4."}
```
