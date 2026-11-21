# الدرس 7: فورتران IV/66/77 للبرامج العلمية والبطاقات المثقبة

**في هذا الدرس:**

- **الصيغة الثابتة** (Fixed Form) لفورتران القديمة: الأعمدة 1-5 و 6 و 7-72 و 73-80.
- برامج علمية حقيقية الطابع: جدول المدارات الدائرية، وسرعة الإفلات.
- التراكيب القديمة: `IF` الحسابية، و`GO TO` المحسوبة، وثوابت **هوليريث**، و`COMMON`، والأنواع الضمنية.
- مشروع **Fortran 66/77** وإعدادات المترجم، و**رزمة البطاقات**، و**التحويل إلى الصيغة الحرة**.

## لماذا فورتران القديمة؟

الحاسوب AGC في المركبة بُرمج بلغة التجميع، لكن على الأرض كانت حسابات ناسا - المدارات، ونوافذ الإطلاق، وديناميكا الموائع، والهياكل - تُكتب بـ **FORTRAN IV** ثم **Fortran 66** و**Fortran 77** على حواسيب IBM الكبيرة، وما زال بعضها يعمل حتى اليوم. كان كل سطر **بطاقة مثقبة** من 80 عمودًا:

| الأعمدة | المعنى |
|---|---|
| 1 | `C` أو `*` = سطر تعليق كله |
| 1-5 | رقم العبارة (Label) |
| 6 | علامة الاستمرار: أي حرف غير المسافة والصفر يعني «تكملة السطر السابق» |
| 7-72 | العبارة نفسها |
| 73-80 | رقم تسلسل البطاقة (يتجاهله المترجم) |

في محرر RAD IDE ترى **مساطر** عند الأعمدة 5 و 6 و 72، والأعمدة 73-80 **رمادية**. مرّر الفأرة على أي عمود لتعرف معناه.

> الأمثلة هنا تبدأ بالسطر `! #file: orbit.f`: الامتداد `.f` يجعل المترجم gfortran يقرأ الصيغة الثابتة، و`!` في العمود الأول تعليق. انتبه للمسافات: **6 مسافات** قبل كل عبارة.

## جدول المدارات الدائرية (بأسلوب Fortran 66)

سرعة القمر الصناعي في مدار دائري نصف قطره r: `v = sqrt(GM / r)`، وزمن الدورة `T = 2 pi r / v`:

```fortran run
! #file: orbit.f
C     CIRCULAR ORBITS OF EARTH - FORTRAN 66 STYLE (RAD IDE, CC0)
C     I-N = INTEGER, OTHER LETTERS = REAL (IMPLICIT TYPING)
      DIMENSION ALT(4)
      DATA ALT /200.0, 400.0, 20200.0, 35786.0/
      GM = 398600.44
      RE = 6378.14
      PI = 3.1415926536
      WRITE (6,100)
  100 FORMAT (1X, 8HALTITUDE, 4X, 8HVELOCITY, 4X, 6HPERIOD)
      DO 10 I = 1, 4
      R = RE + ALT(I)
      V = SQRT(GM/R)
      T = 2.0*PI*R/V/60.0
      WRITE (6,101) ALT(I), V, T
  101 FORMAT (1X, F8.1, 4X, F8.3, 4X, F7.1)
   10 CONTINUE
      STOP
      END
```

```text output
 ALTITUDE    VELOCITY    PERIOD
    200.0       7.784       88.5
    400.0       7.669       92.6
  20200.0       3.873      718.7
  35786.0       3.075     1436.1
```

- `8HALTITUDE`: ثابت **هوليريث**: الرقم 8 ثم H ثم 8 حروف بالضبط (هكذا كانت النصوص قبل علامات التنصيص).
- `DO 10 I = 1, 4` تكرر حتى العبارة رقم 10 (`CONTINUE`).
- لا تعريف للمتغيرات: `ALT` و`GM` حقيقية لأنها لا تبدأ بـ I-N، و`I` صحيح.
- المدار 20200 كم مدار أقمار GPS (دورته نحو 12 ساعة)، والمدار 35786 كم هو **المدار الثابت بالنسبة للأرض**: دورته يوم نجمي (1436 دقيقة).

## IF الحسابية و GO TO المحسوبة و COMMON

```fortran run
! #file: kinds.f
      PROGRAM KINDS
      COMMON /EARTH/ GM, RE
      GM = 398600.44
      RE = 6378.14
      CALL ESCAPE(400.0)
      CALL ESCAPE(-10.0)
      DO 30 J = 1, 3
C     COMPUTED GO TO: J=1 -> 31, J=2 -> 32, J=3 -> 33
      GO TO (31, 32, 33), J
   31 WRITE (6,201)
      GO TO 30
   32 WRITE (6,202)
      GO TO 30
   33 WRITE (6,203)
   30 CONTINUE
  201 FORMAT (1X, 13HLOW EARTH ORB)
  202 FORMAT (1X, 13HMEDIUM ORBIT )
  203 FORMAT (1X, 13HGEOSTATIONARY)
      STOP
      END
C
      SUBROUTINE ESCAPE(H)
      COMMON /EARTH/ GM, RE
C     ARITHMETIC IF: NEGATIVE -> 1, ZERO -> 2, POSITIVE -> 2
      IF (H) 1, 2, 2
    1 WRITE (6,101) H
      RETURN
    2 VE = SQRT(2.0*GM/(RE + H))
      WRITE (6,102) H, VE
      RETURN
  101 FORMAT (1X, 17HBAD ALTITUDE (KM), F8.1)
  102 FORMAT (1X, 16HESCAPE SPEED AT , F7.1, 4H KM:, F7.3, 5H KM/S)
      END
```

```text output
 ESCAPE SPEED AT   400.0 KM: 10.845 KM/S
 BAD ALTITUDE (KM)   -10.0
 LOW EARTH ORB
 MEDIUM ORBIT
 GEOSTATIONARY
```

- `IF (H) 1, 2, 2`: **IF الحسابية**: سالب إلى 1، صفر إلى 2، موجب إلى 2. حُذفت من فورتران الحديثة لكن ملايين الأسطر القديمة تستخدمها.
- `GO TO (31, 32, 33), J`: يقفز إلى العنوان رقم J في القائمة.
- `COMMON /EARTH/`: منطقة ذاكرة مشتركة بين البرنامج والإجراءات (قبل الوحدات Modules).

### تمرين

اكتب برنامجًا بالصيغة الثابتة يطبع زمن دورة المدار الدائري (بالدقائق) للارتفاعات 300 و 1000 كم، كل سطر `PERIOD AT xxxx.x KM = xxxx.x MIN`:

```fortran exercise
! #file: period.f
      GM = 398600.44
      RE = 6378.14
      PI = 3.1415926536
C     اكتب الحلقة هنا
      STOP
      END
```

```fortran solution
! #file: period.f
      DIMENSION ALT(2)
      DATA ALT /300.0, 1000.0/
      GM = 398600.44
      RE = 6378.14
      PI = 3.1415926536
      DO 10 I = 1, 2
      R = RE + ALT(I)
      T = 2.0*PI*SQRT(R**3/GM)/60.0
      WRITE (6,100) ALT(I), T
  100 FORMAT (1X, 10HPERIOD AT , F6.1, 6H KM = , F6.1, 4H MIN)
   10 CONTINUE
      STOP
      END
```

```text output
 PERIOD AT  300.0 KM =   90.5 MIN
 PERIOD AT 1000.0 KM =  105.1 MIN
```

## المشروع في RAD IDE

**File > New Project... > Space & Science > Fortran 66/77** ثم القالب **Orbit Table (Fortran 66)** (أو **Hello, Fortran 77**). اضغط `Ctrl+F5`. القالب يضيف إلى الجدول مدارًا إهليلجيًا تُحل فيه **معادلة كبلر** بطريقة نيوتن.

**Tools > Retro > Legacy Fortran > Compiler Preset...**

| الإعداد | الخيارات | متى |
|---|---|---|
| Fortran 77 (legacy) | `-std=legacy -ffixed-form -ffixed-line-length-72` | معظم الكود القديم |
| FORTRAN IV / 66 | + `-fno-automatic -finit-local-zero` | البرامج القديمة كانت تحتفظ بقيم المتغيرات المحلية بين الاستدعاءات |
| DEC / VAX | `-fdec` | امتدادات DEC مثل STRUCTURE و RECORD |
| Check against F95 | `-std=f95 -Wall -pedantic` | لمعرفة ما حذفته فورتران الحديثة قبل التحويل |

- **Explain Legacy Constructs**: يكتب في نافذة Output كل تركيب قديم في الملف مع شرحه بالعربية.
- **Card Deck View**: البطاقة كما كانت تثقبها آلة IBM 029 (`A` = ثقبا 12 و 1، و`Z` = 0 و 9).
- **Convert to Free Form...**: `C` تصبح `!`، وأسطر الاستمرار تُضم، وثوابت هوليريث تصبح نصوصًا `'...'`، مع معاينة الفروق قبل الحفظ. الناتج يُترجم كـ Fortran 90 ويطبع **نفس الجدول**.

```quiz
{"question": "ما معنى حرف في العمود السادس من سطر فورتران بالصيغة الثابتة؟", "choices": ["رقم العبارة", "تعليق", "السطر تكملة للسطر السابق", "رقم البطاقة"], "answer": 2, "explanation": "العمود 6: أي حرف غير المسافة والصفر يجعل السطر استمرارًا للسابق."}
```

```quiz
{"question": "إلى أين تقفز IF (X) 10, 20, 30 عندما تكون X سالبة؟", "choices": ["10", "20", "30", "لا تقفز"], "answer": 0, "explanation": "IF الحسابية: سالب -> الأول، صفر -> الثاني، موجب -> الثالث."}
```

```quiz
{"question": "ما نوع المتغير KOUNT في فورتران 66 إن لم يُعرَّف؟", "choices": ["حقيقي", "صحيح لأنه يبدأ بحرف بين I و N", "نصي", "خطأ ترجمة"], "answer": 1, "explanation": "الأنواع الضمنية: الأسماء التي تبدأ بـ I إلى N صحيحة، والبقية حقيقية."}
```
