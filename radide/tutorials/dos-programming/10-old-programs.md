# الدرس 10: تشغيل برامج DOS وألعابها القديمة التي تملكها

**في هذا الدرس ستتعلم:**

- فتح مجلد فيه مصادر قديمة (QBasic بأرقام أسطر، Turbo Pascal، Turbo C، TASM) وبناؤها دون تعديلها.
- تحذيرات التوافق: ما الذي لا تستطيعه المترجمات المجانية وكيف تتصرف.
- تشغيل برنامج أو لعبة DOS جاهزة تملكها في DOSBox-X، وضبط السرعة والصوت والأقراص.
- استعمال نسختك الأصلية من QBasic أو Turbo Pascal أو Turbo C.
- ملف دفعي يشغّل البرامج.

## مصادر قديمة: File > Open Folder

عندك مجلد قديم فيه `GAME.BAS` أو `SORT.PAS` أو `STARS.C`؟ افتحه من **File > Open Folder...** (ملف > فتح مجلد). تتعرف RAD IDE على نوعه:

- `.BAS` بلهجة QBasic أو بأرقام أسطر (ملفات Visual Basic 6 لا تُخلط بها).
- `.PAS` بأسلوب Turbo Pascal (وحدات Delphi لا تُخلط بها).
- `.C` يستعمل `conio.h` أو `dos.h` أو `graphics.h` أو مؤشرات `far`.
- `.ASM` بصيغة MASM أو TASM لـ 16 بت، و`.BAT`.

تقترح النافذة إنشاء مشروع DOS في المكان نفسه: تكتب ملف `project.radproj` فقط، **ولا تغيّر ملفاتك**. بعدها `Ctrl+F5` يبني ويشغّل كأي مشروع.

جرّب المثال `samples/Tests/Retro/DOSOldSources/MoonLander`: لعبة هبوط على القمر بأسلوب BASIC القديم ذي أرقام الأسطر. وهذا برنامج صغير بالأسلوب نفسه:

<!-- test: {"keys": "3~"} -->

```dos-qbasic run
10 REM OLD-STYLE BASIC WITH LINE NUMBERS
20 DIM P(5)
30 FOR I = 1 TO 5: READ P(I): NEXT I
40 INPUT "WHICH ITEM (1-5)"; N
50 IF N < 1 OR N > 5 THEN PRINT "NO SUCH ITEM": GOTO 40
60 GOSUB 1000
70 PRINT "THANK YOU"
80 END
1000 REM ---- PRICE ----
1010 PRINT "ITEM"; STR$(N); " COSTS"; STR$(P(N)); " POUNDS"
1020 RETURN
2000 DATA 15, 40, 25, 60, 10
```

```text output
ITEM 3 COSTS 25 POUNDS
THANK YOU
```

- `GOTO 40` يقفز إلى السطر 40، و`GOSUB 1000` يقفز ثم يعود عند `RETURN`.
- `DATA` يخزن قيمًا داخل البرنامج، و`READ` يقرؤها بالترتيب.
- `STR$(N)` يحوّل العدد إلى نص بمسافة قبله. لماذا لم نكتب `PRINT "ITEM"; N; "COSTS"`؟ لأن QBasic الأصلي يطبع بعد كل عدد مسافة أيضًا، أما FreeBASIC فيطبعها بعد الأعداد الصحيحة فقط. والمتغير `N` هنا عدد عشري (البرنامج القديم لا يكتب `DEFINT`)، فيلتصق `3COSTS`. مع `STR$` والمسافة داخل النص يتطابق الناتج في الاثنين.
- اضغط `F12` على `1000` في `GOSUB 1000` لتنتقل إلى السطر 1000، ويظهر في المخطط (Outline) كل سطر مرقّم يُقفز إليه.

## تحذيرات التوافق

FreeBASIC و Free Pascal و Open Watcom تبني أغلب المصادر القديمة كما هي، لكن بعض الأشياء كانت خاصة بالمترجمات التجارية. تظهر عند البناء في **Error List** كتحذيرات مع السطر:

| ما في المصدر | ماذا يحدث |
|---|---|
| رسوم BGI في Turbo C (`initgraph` وملفات `.BGI`) | تُستبدل بمكتبة RAD IDE `graphics.h` (640 × 480 بـ 16 لونًا)، ويُتجاهل مسار ملفات BGI |
| `clrscr` و`gotoxy` و`textcolor` | تأتي من `tcconio.h` الخاص بـ RAD IDE، ويُضاف تلقائيًّا |
| وحدة Turbo Pascal موجودة كملف `.TPU` فقط | لا يمكن بناؤها دون مصدرها `.PAS` |
| `Overlay` و`inline($..)` في باسكال | غير مدعومة في Free Pascal |
| `PLAY` و`SOUND` و`CALL INTERRUPT` و`ON TIMER` في QBasic | محدودة أو غير متاحة في FreeBASIC |
| `PRINT` لعدد عشري بين نصين | QBasic يطبع مسافة بعد العدد و FreeBASIC لا (إلا للأعداد الصحيحة): استعمل `STR$` (انظر المثال أعلاه) |
| كتل `asm` والمسجلات الوهمية `_AX` في Turbo C | تحتاج تعديلًا لصيغة Open Watcom |
| وضع IDEAL في TASM | اكتبه بصيغة MASM لـ JWasm |

> **نصيحة:** إن احتجت ما لا تدعمه المترجمات المجانية، فاستخدم نسختك الأصلية من المترجم (القسم التالي)، والكود يبقى كما هو.

## نسختك الأصلية من QBasic و Turbo Pascal و Turbo C

RAD IDE لا تنزّل برامج مايكروسوفت و Borland التجارية أبدًا. إن كنت تملك نسخة منها، افتح **Tools > Retro > DOS Programming > DOS Toolchains...** واكتب مسار:

| البرنامج | الملف | الاستعمال |
|---|---|---|
| QBasic 1.1 | `QBASIC.EXE` | **Run in My QBasic**: يفتح مصدرك في QBasic نفسه داخل DOSBox-X ويشغّله (`/RUN`) |
| QuickBASIC 4.5 | `QB.EXE` و`BC.EXE` و`LINK.EXE` | مترجم بديل لـ FreeBASIC في **Project > DOS Project Settings...** |
| Turbo Pascal 7 | `TPC.EXE` | مترجم بديل لـ Free Pascal (يعمل داخل DOSBox-X) |
| Turbo C | `TCC.EXE` | مترجم بديل لـ Open Watcom |

ورسائل أخطاء هذه المترجمات تظهر أيضًا في **Error List** بالملف والسطر.

## تشغيل برنامج أو لعبة جاهزة

لبرنامج DOS جاهز (ملفات `.EXE` أو `.COM` بلا مصادر) طريقتان:

1. **File > Open Folder...** على مجلد البرنامج: تتعرف RAD IDE على ملفات DOS التنفيذية وتقترح **DOS program (DOSBox-X)**.
2. أو **File > New Project...** ثم **Retro** ثم **DOS Program** والقالب **Existing DOS Program**، وانسخ ملفات البرنامج إلى مجلد المشروع.

ثم من **Project > DOS Settings...** (المشروع > إعدادات DOS):

| الإعداد | المعنى |
|---|---|
| program و args | البرنامج الذي يبدأ (تخمنه RAD IDE: `GAME.EXE` أو الملف التنفيذي الوحيد) ومعاملاته |
| cycles | سرعة المعالج: `auto` أو `max` أو رقم ثابت. الألعاب القديمة جدًّا تحتاج سرعة منخفضة |
| machine | بطاقة الشاشة: `svga_s3` (الافتراضي) أو `vgaonly` أو `ega` أو `cga` أو `hercules`... |
| sound | كرت الصوت: `sb16` أو `sbpro2` أو `gus` أو بلا صوت |
| mounts | أقراص إضافية: مجلد، أو صورة قرص مدمج `ISO`، أو صورة قرص مرن `IMG` |

اضغط `F5`: تكتب RAD IDE ملف إعداد DOSBox-X في المجلد `.radide` وتشغّل البرنامج، ويغلقه زر **Stop**. ملفاتك لا تُمس.

> **حقوق النشر:** شغّل فقط البرامج والألعاب التي تملكها، أو التي نشرها أصحابها مجانًا (Freeware) أو كنسخة تجريبية (Shareware) تسمح بالتوزيع. كون اللعبة قديمة لا يجعل نسخها مباحًا.

## ملف دفعي يشغّل برامجك

الملف الدفعي مفيد لتجهيز البيئة قبل تشغيل برنامج: يتحقق من وجود الملفات ويضبط المتغيرات:

```dos-batch run
@ECHO OFF
SET GAMEDIR=C:\GAMES
IF EXIST GAME.EXE GOTO RUN
ECHO GAME.EXE was not found in this folder.
ECHO Copy your game here first.
GOTO END
:RUN
GAME.EXE
:END
ECHO Finished.
```

```text output
GAME.EXE was not found in this folder.
Copy your game here first.
Finished.
```

- `IF EXIST ملف أمر` ينفذ الأمر إن وُجد الملف.
- `:RUN` لافتة، و`GOTO RUN` يقفز إليها. عند البناء تتحقق RAD IDE أن كل `GOTO` و`CALL` يذهب إلى لافتة أو ملف موجود.

```quiz
{"question": "ماذا تفعل RAD IDE بملفاتك القديمة عند فتح مجلدها كمشروع DOS؟", "choices": ["تحوّلها إلى صيغة جديدة", "تكتب project.radproj فقط ولا تغيّر ملفاتك", "تنقلها إلى مجلد آخر"], "answer": 1, "explanation": "المشروع يُنشأ في المكان نفسه بملف project.radproj، والمصادر تبقى كما هي."}
```

```quiz
{"question": "لعبة DOS قديمة تعمل بسرعة كبيرة جدًّا في DOSBox-X. ما الحل؟", "choices": ["تخفيض cycles (السرعة) في إعدادات DOS", "تغيير بطاقة الصوت", "تشغيلها مرتين"], "answer": 0, "explanation": "كثير من الألعاب القديمة تقيس الوقت بعدّ الحلقات؛ اختر سرعة ثابتة منخفضة أو preset مثل 286."}
```
