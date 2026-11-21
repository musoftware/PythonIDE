# الدرس 5: لوحة الأوامر والتنقل السريع والاختصارات

**في هذا الدرس ستتعلم:**

- **لوحة الأوامر** (`Ctrl+Shift+P`): تشغيل أي أمر من أوامر البيئة بكتابة جزء من اسمه.
- **الفتح السريع** (`Ctrl+P`): الوصول إلى أي ملف في الحل، وإلى سطر معيّن فيه.
- البحث والاستبدال، والبحث في الملفات، والانتقال إلى سطر وإلى التعريف.
- قائمة الاختصارات، وتغيير مجموعة الاختصارات (Keymap) إلى Visual Studio أو VS Code أو Vim.

## مساعد يحفظ كل الأزرار

في البيئة مئات الأوامر. لا أحد يحفظ مكانها كلها في القوائم.
**لوحة الأوامر** مثل موظف استقبال ذكي: تقول له "أريد تنسيق الملف" فيأخذك إلى الأمر مباشرة، حتى لو كتبت جزءًا من الكلمة فقط.

## مربع واحد بأربعة أوضاع

افتح **View > Command Palette...** (عرض > لوحة الأوامر...) أو اضغط `Ctrl+Shift+P`. يظهر مربع إدخال في أعلى النافذة.
**الحرف الأول** الذي تكتبه يحدد الوضع:

| تبدأ بـ | الوضع | مثال | النتيجة |
|---|---|---|---|
| `>` | **أوامر** | `>format doc` | ينفّذ **Format Document** |
| (لا شيء) | **فتح سريع** للملفات | `form1` | يفتح `Form1.py` |
| `:` | **الانتقال إلى سطر** في الملف الحالي | `:42` أو `:42:7` | السطر 42 (والعمود 7) |
| `?` | **مساعدة** | `?` | يشرح الأوضاع |

`Ctrl+Shift+P` يفتح المربع وفيه `>` جاهزة، و `Ctrl+P` (**View > Quick Open (Go to File)...**: فتح سريع) يفتحه فارغًا للملفات.

### البحث الضبابي (Fuzzy)

لا تحتاج أن تكتب الاسم كاملًا ولا بالترتيب الحرفي. أمثلة:

- `>tgbp` يجد **Toggle Breakpoint** (الحروف الأولى من الكلمات).
- `>git push` يجد **Push** من قائمة Git.
- `>layout` يعرض أوامر التخطيط كلها.

الأوامر التي استخدمتها مؤخرًا تظهر **في أول القائمة**، فبعد أيام تصبح أوامرك المفضلة على بعد ضغطتين.

### الفتح السريع مع رقم السطر

اكتب اسم الملف ثم نقطتين ورقم السطر: `Module1:12` يفتح `Module1.bas` على السطر 12. البحث يشمل **كل مشروعات الحل**.

## البحث والتنقل في الكود

| الأمر | القائمة | الاختصار |
|---|---|---|
| بحث في الملف | **Edit > Find...** (تحرير > بحث...) | `Ctrl+F` |
| استبدال | **Edit > Replace...** (استبدال...) | `Ctrl+H` |
| التالي / السابق | **Edit > Find Next / Find Previous** | `F3` / `Shift+F3` |
| بحث في كل الملفات | **Edit > Find in Files...** (البحث في الملفات...) | `Ctrl+Shift+F` |
| الانتقال إلى سطر | **Edit > Go to Line...** (الانتقال إلى سطر...) | `Ctrl+G` |
| الانتقال إلى التعريف | **Edit > Go to Definition** (الانتقال إلى التعريف) | `F12` |
| كل المراجع | **Edit > Refactor > Find All References** | `Shift+F12` |
| إدراج قصاصة كود جاهزة | **Edit > Insert Snippet...** (إدراج قصاصة...) | — |
| تعليق / إلغاء تعليق | — | `Ctrl+/` |

نتائج **Find in Files** تظهر في نافذة **Find Results** (نتائج البحث). انقر أي نتيجة مرتين لتقفز إليها.

## جرّب الانتقال إلى التعريف

اضغط «افتح في المحرر»، ثم ضع المؤشر على كلمة `Greeting` داخل `Sub Main` واضغط `F12`: ستنتقل إلى الوحدة `Helpers.bas` حيث عُرّفت الدالة.
ثم جرّب `Ctrl+P` واكتب `helpers` لتفتح الملف مباشرة.

```vb run
'#file: Module1.bas
Sub Main()
    Debug.Print Greeting("سارة")
    Debug.Print Greeting("يوسف")
End Sub
'#file: Helpers.bas
Public Function Greeting(name As String) As String
    Greeting = "صباح الخير يا " & name
End Function
```

```text output
صباح الخير يا سارة
صباح الخير يا يوسف
```

## قائمة الاختصارات و Keymap

- **Help > Keyboard Shortcuts** (تعليمات > اختصارات لوحة المفاتيح): جدول بكل اختصارات القوائم كما هي الآن.
- **Tools > Keymap** (أدوات > اختصارات لوحة المفاتيح): اختر مجموعة الاختصارات التي اعتدت عليها:

| الخيار | لمن؟ |
|---|---|
| **Visual Studio** | الافتراضي: `F5` للتشغيل، `F9` لنقطة التوقف ... |
| **VS Code** | اختصارات VS Code |
| **Vim** | أوضاع Vim في المحرر |
| **Emacs (basic)** | اختصارات Emacs الأساسية |

## أوامر تُسجَّل وتُعاد: الماكرو

إذا كررت نفس التعديل كثيرًا، سجّله مرة واحدة:

1. **Tools > Macros > Record Temporary Macro / Stop** (`Ctrl+Shift+R`) لبدء التسجيل.
2. نفّذ التعديل في المحرر.
3. اضغط `Ctrl+Shift+R` مرة أخرى للإيقاف.
4. **Run Temporary Macro** (`Ctrl+Alt+Shift+P`) يعيده حيث يقف المؤشر.

## أخطاء شائعة

- **نسيان `>` في أول المربع:** بدونها يبحث المربع عن **ملفات** لا عن أوامر. `Ctrl+Shift+P` يضعها لك.
- **`Ctrl+G` في مشروع لم يُفتح فيه ملف:** الانتقال إلى سطر يعمل على المحرر الحالي. افتح الملف أولًا.
- **`F12` على كلمة غير معرّفة في المشروع:** إذا كانت الدالة من مكتبة اللغة نفسها قد لا يوجد لها ملف تقفز إليه. استخدم `F1` للتعليمات بدلًا منه.

## تمرين

### تمرين 1: دالة جديدة في وحدة مستقلة

أضف إلى `Helpers.bas` دالة `Farewell(name)` تُرجع `"مع السلامة يا "` ثم الاسم، واطبع بها وداع "سارة".

```vb exercise
'#file: Module1.bas
Sub Main()
    Debug.Print Greeting("سارة")
    Debug.Print Farewell("سارة")
End Sub
'#file: Helpers.bas
Public Function Greeting(name As String) As String
    Greeting = "صباح الخير يا " & name
End Function
```

```vb solution
'#file: Module1.bas
Sub Main()
    Debug.Print Greeting("سارة")
    Debug.Print Farewell("سارة")
End Sub
'#file: Helpers.bas
Public Function Greeting(name As String) As String
    Greeting = "صباح الخير يا " & name
End Function

Public Function Farewell(name As String) As String
    Farewell = "مع السلامة يا " & name
End Function
```

```text output
صباح الخير يا سارة
مع السلامة يا سارة
```

### مهمة عملية: يوم بلا فأرة

1. اضغط `Ctrl+Shift+P` واكتب `>new proj` ثم `Enter` لإنشاء مشروع.
2. اضغط `Ctrl+P` واكتب اسم النموذج لفتحه.
3. اضغط `Ctrl+Shift+P` واكتب `>zen` لتدخل وضع التركيز، ثم اخرج منه.
4. افتح **Help > Keyboard Shortcuts** واكتب ثلاثة اختصارات جديدة تعلمتها.

## اختبر نفسك

```quiz
{"question": "كتبت `:25` في المربع بعد `Ctrl+P`. ماذا يحدث؟", "choices": ["يبحث عن ملف اسمه 25", "ينتقل إلى السطر 25 في الملف الحالي", "يفتح الدرس 25", "خطأ"], "answer": 1, "explanation": "البادئة `:` تعني الانتقال إلى سطر في المحرر الحالي."}
```

```quiz
{"question": "أي اختصار يبحث عن نص في كل ملفات المشروع؟", "choices": ["`Ctrl+F`", "`Ctrl+Shift+F`", "`Ctrl+H`", "`F3`"], "answer": 1, "explanation": "Edit > Find in Files هو Ctrl+Shift+F، والنتائج في نافذة Find Results."}
```

```quiz
{"question": "تحب اختصارات VS Code. أين تغيّرها؟", "choices": ["Tools > Keymap > VS Code", "File > New Window", "View > Layout > Agent", "لا يمكن تغييرها"], "answer": 0, "explanation": "Tools > Keymap يغيّر مجموعة الاختصارات: Visual Studio أو VS Code أو Vim أو Emacs."}
```

## الخلاصة

- `Ctrl+Shift+P` للأوامر (`>`)، و `Ctrl+P` للملفات (`اسم:سطر`)، و `:` للسطر، و `?` للمساعدة.
- البحث ضبابي، والأوامر الحديثة أولًا.
- `Ctrl+F` / `Ctrl+H` / `Ctrl+Shift+F` / `Ctrl+G` / `F12` / `Shift+F12` للبحث والتنقل.
- **Help > Keyboard Shortcuts** لقائمة الاختصارات، و **Tools > Keymap** لتغيير مجموعتها.
