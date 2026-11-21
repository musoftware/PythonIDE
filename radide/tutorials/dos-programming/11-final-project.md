# الدرس 11: المشروع النهائي: اختبار سريع في وضع النص

**في هذا المشروع ستجمع ما تعلمته:**

- برنامج QBasic كامل منظم بالبرامج الفرعية (`SUB`) والمصفوفات و`DATA`.
- واجهة ملونة بإطارات CP437 في وضع النص.
- قراءة المفاتيح بـ `INKEY$` والتحقق من الإجابة.
- بناؤه ببرنامج DOS حقيقي وتوزيعه.
- ثم إعادة بنائه بمصمم الشاشات ولغة أخرى.

## الفكرة

برنامج «اختبار سريع» عن DOS: يعرض كل سؤال في إطار مع ثلاث إجابات، فيضغط المستخدم `1` أو `2` أو `3`، وفي النهاية تظهر النتيجة. أنشئ مشروع **QBasic / QuickBASIC** باسم `DosQuiz`.

## الخطوة 1: البيانات

الأسئلة والإجابات ورقم الإجابة الصحيحة في أسطر `DATA` في آخر البرنامج، فتضيف سؤالًا جديدًا دون أن تلمس باقي الكود:

```qb
DATA "Which interrupt gives the DOS services?", "INT 10h", "INT 21h", "INT 16h", 2
```

ونقرؤها في مصفوفات في أول البرنامج:

```qb
FOR I = 1 TO NQ
    READ Q$(I), A$(I, 1), A$(I, 2), A$(I, 3), ANS(I)
NEXT I
```

## الخطوة 2: الإطار

`Frame` يرسم إطارًا مزدوجًا وعنوانًا في وسط حافته العليا، و`Center` يكتب نصًّا في وسط سطر:

```qb
SUB Frame (R, C, W, H, T$)
    LOCATE R, C: PRINT CHR$(201); STRING$(W - 2, 205); CHR$(187);
    FOR Y = R + 1 TO R + H - 2
        LOCATE Y, C: PRINT CHR$(186); SPACE$(W - 2); CHR$(186);
    NEXT Y
    LOCATE R + H - 1, C: PRINT CHR$(200); STRING$(W - 2, 205); CHR$(188);
    LOCATE R, C + (W - LEN(T$)) \ 2: PRINT T$;
END SUB
```

## البرنامج كاملًا

<!-- test: {"keys": "231", "screen": true} -->

```dos-qbasic run
' DosQuiz - the final project of the DOS programming course
DEFINT A-Z
DECLARE SUB Frame (R, C, W, H, T$)
DECLARE SUB Center (R, T$)
CONST NQ = 3
DIM Q$(1 TO NQ), A$(1 TO NQ, 1 TO 3), ANS(1 TO NQ)

FOR I = 1 TO NQ
    READ Q$(I), A$(I, 1), A$(I, 2), A$(I, 3), ANS(I)
NEXT I

SCORE = 0
FOR I = 1 TO NQ
    COLOR 15, 1
    CLS
    Frame 3, 10, 60, 12, " Question" + STR$(I) + " of" + STR$(NQ) + " "
    COLOR 14, 1
    LOCATE 5, 13: PRINT Q$(I);
    COLOR 15, 1
    FOR J = 1 TO 3
        LOCATE 6 + J * 1, 15: PRINT CHR$(48 + J); ") "; A$(I, J);
    NEXT J
    LOCATE 12, 13: PRINT "Your answer (1-3): ";
    DO
        K$ = INKEY$
    LOOP UNTIL K$ >= "1" AND K$ <= "3"
    IF VAL(K$) = ANS(I) THEN SCORE = SCORE + 1
NEXT I

COLOR 15, 1
CLS
Frame 8, 20, 40, 7, " Result "
COLOR 10, 1
Center 10, "You scored" + STR$(SCORE) + " out of" + STR$(NQ)
IF SCORE = NQ THEN T$ = "Excellent!" ELSE T$ = "Read the lessons again!"
COLOR 14, 1
Center 12, T$
COLOR 7, 0
LOCATE 20, 1
END

DATA "Which interrupt gives the DOS services?", "INT 10h", "INT 21h", "INT 16h", 2
DATA "Where is the text screen in memory?", "A000:0000", "0000:0100", "B800:0000", 3
DATA "How many pixels has mode 13h?", "320 x 200", "640 x 480", "80 x 25", 1

SUB Center (R, T$)
    LOCATE R, (80 - LEN(T$)) \ 2 + 1: PRINT T$;
END SUB

SUB Frame (R, C, W, H, T$)
    LOCATE R, C: PRINT CHR$(201); STRING$(W - 2, 205); CHR$(187);
    FOR Y = R + 1 TO R + H - 2
        LOCATE Y, C: PRINT CHR$(186); SPACE$(W - 2); CHR$(186);
    NEXT Y
    LOCATE R + H - 1, C: PRINT CHR$(200); STRING$(W - 2, 205); CHR$(188);
    LOCATE R, C + (W - LEN(T$)) \ 2: PRINT T$;
END SUB
```

```text output
                   ╔═══════════════ Result ═══════════════╗
                   ║                                      ║
                   ║         You scored 3 out of 3        ║
                   ║                                      ║
                   ║               Excellent!             ║
                   ║                                      ║
                   ╚══════════════════════════════════════╝
```

جرّبه بـ `Ctrl+F5`، ثم بـ **Run with Captured Output...** مع المفاتيح `231` (إجابات صحيحة كلها) و`111` لترى النتيجتين.

### كيف يعمل؟

- `CONST NQ = 3` ثابت لعدد الأسئلة؛ غيّره وأضف سطر `DATA` لتزيد الأسئلة.
- `DIM A$(1 TO NQ, 1 TO 3)` مصفوفة بُعدين: لكل سؤال ثلاث إجابات.
- `CHR$(48 + J)` يعطي الحرف `1` أو `2` أو `3` (رمز `0` في ASCII هو 48).
- الحلقة `DO ... LOOP UNTIL` تتجاهل كل مفتاح غير `1` و`2` و`3`.
- الفاصلة المنقوطة في آخر `PRINT` تمنع النزول إلى سطر جديد، فلا تتحرك الشاشة عند الكتابة في السطر الأخير من الإطار.

## التوزيع

بعد البناء تجد في مجلد المشروع `DOSQUIZ.EXE` و`CWSDPMI.EXE` (يحتاجه كل برنامج يبنيه FreeBASIC لـ DOS). انسخهما معًا إلى أي حاسوب DOS أو FreeDOS أو إلى مجلد في DOSBox-X، واكتب `DOSQUIZ`. برامج Free Pascal و Open Watcom والتجميع لا تحتاج ملفًا إضافيًّا.

## المرحلة الثانية: بالمصمم

أعد البرنامج نفسه بأسلوب Visual Basic:

1. **File > New Project...** ثم **DOS** ثم **DOS Text-Mode Forms App**، واختر هذه المرة لغة أخرى: **Forms App - Pascal (Crt)** أو **Forms App - C (OpenWatcom / Turbo C)**.
2. ارسم نافذة فيها تسمية للسؤال وثلاثة أزرار خيار (Option) وزر **Next** وشريط تقدم (ProgressBar) لعدد الأسئلة.
3. في حدث `Click` للزر **Next** اقرأ قيمة الخيارات بـ `TuiGetValue`، وزد النتيجة، واكتب السؤال التالي بـ `TuiSetText`، وحرّك شريط التقدم بـ `TuiSetValue`.
4. اعرض النتيجة في النهاية بـ `TuiMsgBox`، واجعل شاشة ANSI من رسمك شاشة افتتاحية (الدرس 8).

الفأرة تعمل في البرنامج المولّد أيضًا: انقر الخيارات والزر مباشرة في نافذة DOSBox-X.

## أفكار للتوسع

- اقرأ الأسئلة من ملف نصي بـ `OPEN "QUIZ.TXT" FOR INPUT AS #1` و`INPUT #1`.
- أضف مؤقتًا بالدالة `TIMER` (عدد الثواني منذ منتصف الليل) لكل سؤال.
- أضف صوتًا للإجابة الصحيحة بـ `SOUND 880, 2` (يعمل في QBasic الأصلي، وFreeBASIC يحذّرك منه).
- حوّله إلى لعبة رسومية في الوضع 13h بمصمم **New DOS Mode 13h Screen...** (الدرس 9).

مبروك! أنهيت دورة برمجة DOS: من سطر الأوامر والملفات الدفعية، إلى QBasic وباسكال و C والتجميع، إلى التصميم المرئي للشاشات والألعاب.

```quiz
{"question": "لماذا نضع الأسئلة في أسطر DATA؟", "choices": ["لأنها أسرع في التنفيذ", "لنضيف أسئلة دون تغيير منطق البرنامج", "لأن PRINT لا يطبع النصوص"], "answer": 1, "explanation": "فصل البيانات عن الكود يجعل إضافة سؤال سطرًا واحدًا مع زيادة NQ."}
```

```quiz
{"question": "ما الملف الذي يجب نسخه مع برنامج FreeBASIC لـ DOS؟", "choices": ["CWSDPMI.EXE", "COMMAND.COM", "QBASIC.EXE"], "answer": 0, "explanation": "برامج FreeBASIC لـ DOS تعمل بذاكرة 32 بت وتحتاج خادم DPMI مثل CWSDPMI.EXE."}
```
