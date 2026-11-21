# الدرس 8: التكامل مع ويندوز وسطر الأوامر والتعليمات

**في هذا الدرس ستتعلم:**

- ربط ملفات RAD IDE بالبيئة، وإضافتها إلى "فتح باستخدام" وقوائم مستكشف ويندوز، واختصارات قائمة ابدأ وسطح المكتب.
- لماذا لا يحتاج هذا إلى صلاحيات المسؤول، وكيف تتراجع عنه تمامًا.
- تشغيل البيئة من سطر الأوامر: فتح ملف على سطر معيّن، ونافذة جديدة.
- مصادر المساعدة: `F1`، والدليل، والدروس، وملفات CHM، والتحديثات.

## البيئة جزء من ويندوز

بعد التكامل يصبح التعامل مع البيئة مثل التعامل مع Word أو المفكرة:
تنقر ملف `.radsln` مرتين فيُفتح، أو تنقر مجلدًا بالزر الأيمن وتختار **Open folder in RAD IDE**.

### خطوة بخطوة

1. افتح **Tools > Options...** (أدوات > خيارات...)، لسان **Environment** (البيئة).
2. في مجموعة **Windows integration** (التكامل مع ويندوز) اختر ما تريد:

| الخيار | الاسم العربي | ماذا يفعل؟ |
|---|---|---|
| **File associations for RAD IDE files (.radsln, .radproj, .form ...)** | ربط ملفات RAD IDE به | النقر المزدوج على ملفات البيئة يفتحها في RAD IDE |
| **"Open with" RAD IDE for source and text files** | إضافة RAD IDE إلى "فتح باستخدام" | يظهر RAD IDE في قائمة "فتح باستخدام" لملفات `.py` و `.cpp` و `.txt` ... **دون** أن يأخذ مكان برنامجها الافتراضي |
| **Explorer context menus** | قوائم مستكشف الملفات | **Open with RAD IDE** على الملفات، و **Open folder in RAD IDE** على المجلدات |
| **Start Menu shortcut** | اختصار في قائمة ابدأ | RAD IDE في قائمة ابدأ |
| **Desktop shortcut** | اختصار على سطح المكتب | أيقونة على سطح المكتب |

3. اضغط **Register** (تسجيل). يظهر سطر **Status:** يخبرك بما سُجّل.
4. للتراجع اضغط **Unregister** (إلغاء التسجيل).

### آمن وقابل للتراجع

- يُكتب كل شيء **للمستخدم الحالي فقط** (في جزء `HKCU` من السجل)، فلا يحتاج صلاحيات المسؤول ولا يؤثر في مستخدمين آخرين.
- البيئة تسجّل **قائمة بكل قيمة كتبتها**. عند **Unregister** تحذف ما كتبته فقط، و**تعيد** أي قيمة قديمة كانت موجودة قبلها.
- ملفات الكود (`.py` و `.cpp` ...) لا تُسلب من برامجها: RAD IDE يُضاف إلى "فتح باستخدام" فقط.

### نافذة واحدة أم نوافذ كثيرة؟

الخيار **Open files in the running RAD IDE window** (فتح الملفات في نافذة RAD IDE المفتوحة بالفعل) يجعل أي ملف تفتحه من ويندوز يذهب إلى النافذة المفتوحة.
وإذا احتجت نافذة أخرى استخدم **File > New Window** (`Ctrl+Alt+N`).

## سطر الأوامر

يمكن تشغيل البيئة من موجه الأوامر أو من اختصار مع خيارات:

| الأمر | المعنى |
|---|---|
| `python -m radide` | تشغيل البيئة (من مجلد المصدر) |
| `python -m radide D:\Work\App` | فتح مجلد أو مشروع أو حل |
| `python -m radide Form1.py --line 25` | فتح ملف على السطر 25 |
| `python -m radide --new-window` | نافذة جديدة حتى لو كانت هناك نافذة مفتوحة |
| `python -m radide --register` / `--unregister` | التكامل مع ويندوز بدون فتح نافذة (للمثبّتات) |

في النسخة المثبّتة استبدل `python -m radide` بـ `RADIDE.exe`. وبرنامج التثبيت نفسه يستدعي `--register` بعد التثبيت و `--unregister` قبل الإزالة.

## مصادر المساعدة

| المصدر | القائمة | الاختصار |
|---|---|---|
| مساعدة حسب السياق: الكلمة تحت المؤشر أو الأداة المحددة | **Help > Context Help** (تعليمات حسب السياق) | `F1` |
| دليل RAD IDE | **Help > RAD IDE Help** (تعليمات RAD IDE) | `Ctrl+F1` |
| الدروس العربية (هذا الدليل) | **Help > Tutorials (Arabic lessons)...** | `Ctrl+Shift+F1` |
| ملفات المساعدة للقراءة بدون البيئة | **Help > Help Files (CHM)** (ملفات المساعدة) | — |
| مراجع اللغات | **Help > VB6 Language Reference**، **Python Documentation** ... | — |
| التحديثات | **Help > Check for Updates...** | — |

### F1 الذكي

ضع المؤشر على كلمة في الكود واضغط `F1`:

- في BASIC يفتح مرجع VB6 المرفق (الكلمات المحجوزة، والدوال، وخصائص الأدوات).
- في Python يفتح توثيق Python أو Tkinter أو Qt for Python.
- في Ring يفتح توثيق Ring.

وفي المصمم: حدد أداة واضغط `F1` لتعليمات تلك الأداة.

### ملفات CHM

كل دورة ودليل من هذه الدروس يُبنى أيضًا ملف مساعدة ويندوز (`.chm`). تجدها في **Help > Help Files (CHM)**، وتفتح في عارض تعليمات ويندوز، وفيها فهرس وبحث.
أي دورة جديدة تُبنى لها نسخة CHM تظهر في القائمة تلقائيًا.

## مثال: قراءة خيارات سطر الأوامر

البرامج تقرأ ما يُكتب بعد اسمها كما تفعل البيئة مع `--line`. هذا مثال يفكك سطر أوامر جاهزًا:

```vb run
Sub Main()
    Dim cmd As String
    Dim parts() As String
    Dim i As Integer
    cmd = "Form1.py --line 25 --new-window"
    parts = Split(cmd, " ")
    For i = 0 To UBound(parts)
        If Left(parts(i), 2) = "--" Then
            Debug.Print "خيار: " & parts(i)
        Else
            Debug.Print "قيمة: " & parts(i)
        End If
    Next i
End Sub
```

```text output
قيمة: Form1.py
خيار: --line
قيمة: 25
خيار: --new-window
```

## أخطاء شائعة

- **توقع أن التسجيل يأخذ ملفات `.py` من برنامجها:** لا، يضيف RAD IDE إلى "فتح باستخدام" فقط.
- **نقل مجلد البيئة بعد التسجيل:** الاختصارات تشير إلى المكان القديم. اضغط **Register** مرة أخرى من المكان الجديد.
- **البحث عن ملف CHM غير مبني:** إذا ظهرت رسالة "is not built yet" فشغّل `python tools\build_chm.py` من مجلد المصدر.

## تمرين

### تمرين 1: عدّ الخيارات

عدّل البرنامج ليطبع في النهاية عدد الخيارات (الكلمات التي تبدأ بـ `--`) بهذا الشكل: `عدد الخيارات: 2`، بدون طباعة الأسطر الأخرى.

```vb exercise
Sub Main()
    Dim cmd As String
    Dim parts() As String
    Dim i As Integer
    Dim count As Integer
    cmd = "Form1.py --line 25 --new-window"
    parts = Split(cmd, " ")
    ' أكمل
End Sub
```

```vb solution
Sub Main()
    Dim cmd As String
    Dim parts() As String
    Dim i As Integer
    Dim count As Integer
    cmd = "Form1.py --line 25 --new-window"
    parts = Split(cmd, " ")
    For i = 0 To UBound(parts)
        If Left(parts(i), 2) = "--" Then count = count + 1
    Next i
    Debug.Print "عدد الخيارات: " & count
End Sub
```

```text output
عدد الخيارات: 2
```

### مهمة عملية: انقر مرتين

1. فعّل **File associations** و **Explorer context menus** واضغط **Register**.
2. في مستكشف ويندوز انقر مجلد أي مشروع بالزر الأيمن واختر **Open folder in RAD IDE**.
3. انقر ملف `.radsln` مرتين ولاحظ أنه يُفتح في النافذة المفتوحة.
4. إن أردت، اضغط **Unregister** لإرجاع كل شيء كما كان.

## اختبر نفسك

```quiz
{"question": "هل يحتاج التكامل مع ويندوز إلى صلاحيات المسؤول؟", "choices": ["نعم دائمًا", "لا، يُكتب للمستخدم الحالي فقط (HKCU)", "فقط في ويندوز 11", "فقط لاختصار سطح المكتب"], "answer": 1, "explanation": "كل القيم تُكتب للمستخدم الحالي، و Unregister يحذفها ويعيد القيم القديمة."}
```

```quiz
{"question": "تريد فتح `Form1.py` على السطر 25 من سطر الأوامر. ماذا تكتب؟", "choices": ["`python -m radide Form1.py --line 25`", "`python Form1.py 25`", "`radide --goto 25`", "لا يمكن"], "answer": 0, "explanation": "الخيار `--line` (أو `-l`) يحدد السطر."}
```

```quiz
{"question": "وضعت المؤشر على كلمة `MsgBox` في كود BASIC. ماذا يفعل `F1`؟", "choices": ["يشغّل البرنامج", "يفتح مرجع VB6 على صفحة MsgBox", "يحذف الكلمة", "يفتح لوحة الأوامر"], "answer": 1, "explanation": "F1 مساعدة حسب السياق: الكلمة تحت المؤشر."}
```

## الخلاصة

- **Options > Environment > Windows integration**: ربط الملفات، و"فتح باستخدام"، وقوائم المستكشف، والاختصارات، ثم **Register**.
- آمن: للمستخدم الحالي فقط، و **Unregister** يعيد كل شيء.
- سطر الأوامر: مسار + `--line N` + `--new-window`.
- المساعدة: `F1` للسياق، و `Ctrl+F1` للدليل، و `Ctrl+Shift+F1` للدروس، و **Help Files (CHM)** للقراءة بدون البيئة.
