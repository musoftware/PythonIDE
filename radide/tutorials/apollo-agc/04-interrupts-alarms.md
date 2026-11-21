# الدرس 4: المقاطعات وإنذارات العتاد وتصحيح الأخطاء

**في هذا الدرس:**

- **متجهات المقاطعة** عند العنوان 4000، و`T3RUPT` (المؤقت) و`KEYRUPT1` (لوحة المفاتيح).
- حفظ المسجلات واستعادتها بـ `DXCH ARUPT` ثم `RESUME`.
- **إنذارات العتاد** التي تعيد تشغيل الحاسوب: Night Watchman و Rupt Lock و TC Trap.
- رسائل الأخطاء في **Error List**.

## متجهات المقاطعة

عند التشغيل يبدأ المعالج من **4000**. وكل 4 كلمات بعدها «متجه» لمقاطعة:

| العنوان | المقاطعة | المصدر |
|---|---|---|
| 4000 | GOJAM | التشغيل أو إعادة التشغيل |
| 4004 | T6RUPT | مؤقت المحركات النفاثة |
| 4010 | T5RUPT | الطيار الآلي |
| 4014 | **T3RUPT** | فيضان العداد `TIME3` (قائمة الانتظار Waitlist) |
| 4020 | T4RUPT | DSKY وفحوص دورية |
| 4024 | **KEYRUPT1** | ضغطة مفتاح في DSKY |
| 4030 ... 4050 | KEYRUPT2 و UPRUPT و DOWNRUPT و RADAR و HANDRUPT | |

```agc
                SETLOC  4000
                INHINT                  # 4000: GOJAM
                TCF     START
                NOOP
                NOOP
                ...
                DXCH    ARUPT           # 4014: T3RUPT - احفظ A و L في ARUPT و LRUPT
                TCF     T3HAND
                NOOP
                NOOP
```

والمعالِج نفسه:

```agc
T3HAND          CAF     T3LOAD          # 37777: فيضان جديد بعد جزء من مئة من الثانية
                TS      TIME3
                INCR    CENTI
                ...
                DXCH    ARUPT           # استعد A و L
                RESUME                  # ارجع إلى حيث قُطع البرنامج
```

العدادات `TIME1` و`TIME3` و`TIME4` و`TIME5` تزيد **كل جزء من مئة من الثانية** (centisecond). عندما يفيض `TIME3` (يتجاوز 37777 ثماني) تحدث المقاطعة `T3RUPT`. لهذا نضع فيه 37777 لتأتي المقاطعة بعد 10 ميلي ثانية.

## العتاد يراقب البرنامج

صُمّم AGC بحيث لا «يتجمد» أبدًا. في العتاد دوائر تعيد تشغيل الحاسوب (GOJAM) إذا بدا أن البرنامج عَلِق:

| الإنذار | الشرط | الحل في برنامجك |
|---|---|---|
| **NIGHT WATCHMAN** | لم يُقرأ العنوان 67 (`NEWJOB`) خلال 0.64 ثانية | اقرأ `NEWJOB` في الحلقة الرئيسية: `CA NEWJOB` |
| **RUPT LOCK** / NO RUPT | بقي البرنامج داخل مقاطعة 140 ميلي ثانية، أو لم تحدث أي مقاطعة 140 ميلي ثانية | اجعل `T3RUPT` تأتي باستمرار، واجعل المعالِجات قصيرة |
| **TC TRAP** / NO TC | لم تُنفَّذ `TC` أو `TCF` خلال 5 ميلي ثانية، أو لم يُنفَّذ غيرهما (قفز إلى النفس) | أنهِ الحلقات بـ `TCF` |

محاكي RAD IDE يطبّق هذه الإنذارات مثل الحاسوب الحقيقي ومثل yaAGC تمامًا، ويكتب في نافذة **Output** سبب إعادة التشغيل ويضيء مصباح **RESTART**. جرّب: احذف السطر `CA NEWJOB` من الحلقة `MAIN` وشغّل البرنامج: ستجد الساعة ترجع إلى الصفر كل ثانية تقريبًا.

إن أردت إيقاف الإنذارات أثناء التعلم فقط، أضف في `project.radproj`:

```json
"agc": {"alarms": false}
```

> **من التاريخ:** فكرة «إعادة التشغيل مع حماية البيانات» هي التي أنقذت هبوط أبولو 11 أثناء إنذارات 1202: أعاد الحاسوب تشغيل نفسه عدة مرات في ثوانٍ دون أن يفقد حالة الهبوط.

## جرّب: برنامج يتنفس

هذا برنامج كامل فيه متجهات المقاطعة ومعالج `T3RUPT` وحلقة رئيسية تقرأ `NEWJOB`. المدقق يشغّله **مع إنذارات العتاد** نصف ثانية:

<!-- test: {"seconds": 0.5, "alarms": true, "show": ["TICKS"], "restarts": true} -->
```agc run
TIME3           EQUALS  26
NEWJOB          EQUALS  67
ARUPT           EQUALS  10
ZERO            EQUALS  7

                SETLOC  100
TICKS           ERASE                   # يزيد كل جزء من مئة من الثانية

                SETLOC  4000
                INHINT                  # 4000 GOJAM: التشغيل
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
                DXCH    ARUPT           # 4014 T3RUPT: احفظ A و L
                TCF     T3HAND
                NOOP
                NOOP

START           CA      ZERO
                TS      TICKS
                CAF     T3LOAD          # أول T3RUPT بعد جزء من مئة من الثانية
                TS      TIME3
                RELINT                  # شغّل المقاطعات
LOOP            CA      NEWJOB          # «أنا حي» لدائرة Night Watchman
                TCF     LOOP

T3HAND          CAF     T3LOAD
                TS      TIME3
                INCR    TICKS
                DXCH    ARUPT           # استعد A و L
                RESUME

T3LOAD          OCT     37777
```

```text output
TICKS = 50
restarts: 0
```

50 مقاطعة في نصف ثانية (واحدة كل جزء من مئة من الثانية)، ولا إعادة تشغيل. والآن احذف قراءة `NEWJOB` من الحلقة وشغّل 3 ثوانٍ:

<!-- test: {"seconds": 3, "alarms": true, "show": ["TICKS"], "restarts": true} -->
```agc run
TIME3           EQUALS  26
NEWJOB          EQUALS  67
ARUPT           EQUALS  10
ZERO            EQUALS  7

                SETLOC  100
TICKS           ERASE                   # يزيد كل جزء من مئة من الثانية

                SETLOC  4000
                INHINT                  # 4000 GOJAM: التشغيل
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
                DXCH    ARUPT           # 4014 T3RUPT: احفظ A و L
                TCF     T3HAND
                NOOP
                NOOP

START           CA      ZERO
                TS      TICKS
                CAF     T3LOAD          # أول T3RUPT بعد جزء من مئة من الثانية
                TS      TIME3
                RELINT                  # شغّل المقاطعات
LOOP            CA      TICKS           # نسينا قراءة NEWJOB!
                TCF     LOOP

T3HAND          CAF     T3LOAD
                TS      TIME3
                INCR    TICKS
                DXCH    ARUPT           # استعد A و L
                RESUME

T3LOAD          OCT     37777
```

```text output
TICKS = 44
restarts: 2
```

أعاد العتاد تشغيل الحاسوب (GOJAM) **مرتين** في 3 ثوانٍ (الدائرة تفحص كل 1.28 ثانية تقريبًا)، وفي كل مرة يبدأ البرنامج من جديد ويصفّر `TICKS`؛ لذلك `TICKS` = 44 فقط: الأجزاء من مئة الثانية منذ آخر إعادة تشغيل. في RAD IDE ترى في نافذة Output سطرًا مثل `NIGHT WATCHMAN alarm ... the AGC restarted` ويضيء مصباح **RESTART** في DSKY.

## الأخطاء في Error List

احفظ الملف بعد كتابة خطأ، مثل `TS KEYZ` (اسم غير معرّف) أو `FOO 1` (عملية غير معروفة): يظهر الخطأ في **Error List** مع اسم الملف ورقم السطر، وانقر عليه مرتين لتذهب إليه. وتظهر الرسائل بالعربية إذا كانت الواجهة بالعربية.

```quiz
{"question": "ماذا يحدث في AGC الحقيقي إذا لم يقرأ البرنامج العنوان NEWJOB لمدة طويلة؟", "choices": ["لا شيء", "يضيء مصباح TEMP فقط", "إنذار NIGHT WATCHMAN ويعاد تشغيل الحاسوب (GOJAM)", "يتوقف الحاسوب نهائيًا"], "answer": 2, "explanation": "دائرة Night Watchman تفترض أن البرنامج عَلِق فتعيد التشغيل."}
```

```quiz
{"question": "لماذا نكتب DXCH ARUPT في بداية المقاطعة ونهايتها؟", "choices": ["لحفظ A و L ثم استعادتهما حتى لا يتلف البرنامج المقطوع", "لتشغيل المؤقت", "لمنع المقاطعات الأخرى", "لقراءة لوحة المفاتيح"], "answer": 0, "explanation": "العتاد يحفظ Z والتعليمة المقطوعة فقط؛ أما A و L فعلى البرنامج حفظهما."}
```
