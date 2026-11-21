# الدرس 7: نافذة الخيارات والإعدادات

**في هذا الدرس ستتعلم:**

- ألسنة نافذة **Tools > Options...** واحدًا واحدًا، وما يهمك في كل لسان.
- النسخ الاحتياطي التلقائي واستعادة العمل بعد انقطاع الكهرباء.
- اختيار مفسّر أو مترجم كل لغة، وخوادم اللغات والمصححات.
- أدوات إعداد أخرى: الإضافات، وقصاصات الكود، وإعدادات الذكاء الاصطناعي.

## لوحة التحكم في السيارة

نافذة الخيارات مثل **لوحة التحكم** بجانب مقعد السائق: تضبط المرايا والمقعد والتكييف مرة واحدة، ثم تقود براحة.
افتحها من **Tools > Options...** (أدوات > خيارات...). في الأسفل أربعة أزرار:

| الزر | الاسم العربي | وظيفته |
|---|---|---|
| **OK** | موافق | يحفظ ويغلق |
| **Cancel** | إلغاء | يغلق بدون حفظ |
| **Apply** | تطبيق | يحفظ ويطبّق فورًا والنافذة مفتوحة، لتجرّب |
| **Restore Defaults** | استعادة الافتراضيات | يعيد القيم الأصلية |

كل التغييرات تُطبّق **مباشرة** على المحررات والمصممات المفتوحة، بدون إعادة تشغيل.

## لسان Environment (البيئة)

| الإعداد | الاسم العربي | المعنى |
|---|---|---|
| **Color theme:** | سمة الألوان | System / Light / Blue / Dark / High Contrast |
| **Workbench layout:** | تخطيط منطقة العمل | Visual Studio / VS Code / Agent |
| **Menu and window font size:** | حجم خط القوائم والنوافذ | من 7 إلى 16 نقطة |
| **Language:** | اللغة | English أو العربية |
| **Show the Start Page on startup** | عرض صفحة البدء عند التشغيل | صفحة البدء عند كل تشغيل |
| **Reopen the last solution on startup** | إعادة فتح آخر حل عند بدء التشغيل | يكمل من حيث توقفت |
| **Ask before closing with unsaved changes** | اسأل قبل الإغلاق عند وجود تغييرات غير محفوظة | إذا أزلت العلامة تحفظ البيئة تلقائيًا عند الإغلاق |
| **Auto-save backup every:** | نسخة احتياطية تلقائية كل | عدد الثواني بين النسخ الاحتياطية (0 = إيقاف) |
| **Windows integration** | التكامل مع ويندوز | ربط الملفات وقوائم مستكشف ويندوز (الدرس التالي) |

### النسخ الاحتياطي التلقائي: حزام الأمان

النسخة الاحتياطية **لا تحفظ ملفاتك**؛ ملفاتك لا تُكتب إلا بـ **Save**. لكنها تكتب كل ما لم تحفظه في مجلد مخفي اسمه `.radide_backup` داخل المشروع.
إذا انقطعت الكهرباء أو أُغلقت البيئة فجأة، تسألك عند الفتح التالي: هل تريد استعادة التغييرات؟

## لسان Text Editor (محرر النصوص)

- **Font:** (الخط:) خط الكود. اختر خطًا ثابت العرض مثل `Consolas` أو `Cascadia Mono`.
- **Size:** (الحجم:) حجم الخط.
- **Tab / indent width:** (عرض Tab / المسافة البادئة:) عدد المسافات لكل مستوى إزاحة.
- **Preview:** معاينة فورية للخط.

> 💡 داخل المحرر يمكنك التكبير المؤقت بـ `Ctrl` + عجلة الفأرة.

## لسان Windows Forms Designer (مصمم نماذج Windows)

- **Grid size:** (حجم الشبكة:) المسافة بين نقاط الشبكة في المصمم.
- **Snap controls to the grid** (التصاق عناصر التحكم بالشبكة): الأدوات تقفز إلى أقرب نقطة، فتصطف بسهولة.

## لسان Languages (اللغات)

لكل لغة سطر فيه مسار **المفسّر أو المترجم** الذي يشغّلها. الخانة الفارغة تعني "ابحث تلقائيًا"، والنص الرمادي داخلها يريك ما وجدته البيئة، أو `(not found)` إذا لم تجد شيئًا.
زر **...** يفتح نافذة لاختيار الملف التنفيذي، مثل `python.exe` من بيئة افتراضية لمشروع Python.

> 💡 هناك طريق مختصر للمشروع الحالي: **Tools > Interpreter Path...** (أدوات > مسار المفسّر...).

## ألسنة أخرى

| اللسان | الاسم العربي | ماذا فيه؟ |
|---|---|---|
| **AI** | الذكاء الاصطناعي | مزوّدو الذكاء الاصطناعي، ومفاتيح API، والنموذج المستخدم لكل غرض: المحادثة، والإكمال، والتعديل بـ `Ctrl+I`، والوكلاء، ورسائل الإيداع |
| **Keyboard** | لوحة المفاتيح | **Editor keymap:** (اختصارات المحرر:) Visual Studio أو VS Code أو Vim أو Emacs |
| **Formatting** | التنسيق | المنسّق المستخدم لكل لغة، وخيار **Format on Save** (التنسيق عند الحفظ) |
| **Web** | ويب | إعدادات مواقع الويب، مثل تصحيح JavaScript داخل المعاينة |

## أدوات إعداد في قائمة Tools

| الأمر | الاسم العربي | وظيفته |
|---|---|---|
| **Tools > Language Servers and Debuggers...** | خوادم اللغات والمصححات... | تثبيت وتشغيل خوادم اللغات (IntelliSense الذكي، والانتقال إلى التعريف، وإعادة التسمية) والمصححات لكل لغة |
| **Tools > Extensions...** | الإضافات... | إضافات RAD IDE (`.radext`) |
| **Tools > VS Code Extensions (Open VSX)...** | إضافات VS Code | تثبيت إضافات VS Code من سوق Open VSX |
| **Tools > Code Snippets Manager...** | مدير قصاصات الكود... | القصاصات الجاهزة التي تدرجها بـ **Edit > Insert Snippet...** |
| **Tools > AI Settings...** | إعدادات الذكاء الاصطناعي... | اختصار للسان AI |

## مثال: ما الذي تخزنه الإعدادات؟

الإعدادات أزواج من **مفتاح** و**قيمة**، تمامًا مثل هذا المثال الذي يحاكي بعضها:

```vb run
Sub Main()
    Dim keys(3) As String
    Dim values(3) As String
    Dim i As Integer
    keys(0) = "theme": values(0) = "Dark"
    keys(1) = "editor_font_size": values(1) = "12"
    keys(2) = "grid_size": values(2) = "8"
    keys(3) = "autosave_seconds": values(3) = "60"
    For i = 0 To 3
        Debug.Print keys(i) & " = " & values(i)
    Next i
End Sub
```

```text output
theme = Dark
editor_font_size = 12
grid_size = 8
autosave_seconds = 60
```

## أخطاء شائعة

- **ظن أن النسخ الاحتياطي يحفظ الملفات:** لا. احفظ بـ `Ctrl+S`. النسخة الاحتياطية للطوارئ فقط.
- **كتابة مسار مفسّر خاطئ:** اللغة لن تعمل. امسح الخانة لتعود البيئة إلى البحث التلقائي.
- **تغيير إعدادات كثيرة مرة واحدة ثم نسيان الأصل:** استخدم **Restore Defaults**.

## تمرين

### تمرين 1: إعداد خامس

أضف إعدادًا خامسًا `ui_language = ar` إلى المصفوفتين، واطبع الإعدادات الخمسة.

```vb exercise
Sub Main()
    Dim keys(3) As String
    Dim values(3) As String
    Dim i As Integer
    keys(0) = "theme": values(0) = "Dark"
    keys(1) = "editor_font_size": values(1) = "12"
    keys(2) = "grid_size": values(2) = "8"
    keys(3) = "autosave_seconds": values(3) = "60"
    For i = 0 To 3
        Debug.Print keys(i) & " = " & values(i)
    Next i
End Sub
```

```vb solution
Sub Main()
    Dim keys(4) As String
    Dim values(4) As String
    Dim i As Integer
    keys(0) = "theme": values(0) = "Dark"
    keys(1) = "editor_font_size": values(1) = "12"
    keys(2) = "grid_size": values(2) = "8"
    keys(3) = "autosave_seconds": values(3) = "60"
    keys(4) = "ui_language": values(4) = "ar"
    For i = 0 To 4
        Debug.Print keys(i) & " = " & values(i)
    Next i
End Sub
```

```text output
theme = Dark
editor_font_size = 12
grid_size = 8
autosave_seconds = 60
ui_language = ar
```

### مهمة عملية: اضبط بيئتك

1. في **Text Editor** اجعل حجم الخط 12 واضغط **Apply**. لاحظ المحرر.
2. في **Windows Forms Designer** اجعل **Grid size** يساوي 16، وافتح نموذجًا لترى الشبكة الأوسع.
3. في **Environment** اجعل **Auto-save backup every** يساوي 60 ثانية.
4. اضغط **OK**.

## اختبر نفسك

```quiz
{"question": "ماذا يفعل **Auto-save backup every**؟", "choices": ["يحفظ ملفاتك تلقائيًا", "يكتب التغييرات غير المحفوظة في `.radide_backup` لاستعادتها بعد انهيار", "يرسل المشروع إلى الإنترنت", "يحذف الملفات القديمة"], "answer": 1, "explanation": "النسخة الاحتياطية للطوارئ فقط؛ ملفاتك لا تُكتب إلا بـ Save."}
```

```quiz
{"question": "خانة مفسّر Python في لسان Languages فارغة. ماذا يعني هذا؟", "choices": ["Python معطّل", "البيئة تبحث عن المفسّر تلقائيًا", "خطأ يجب إصلاحه", "سيُحذف المشروع"], "answer": 1, "explanation": "الفراغ يعني الكشف التلقائي، والنص الرمادي يريك ما وُجد."}
```

```quiz
{"question": "أي زر يطبّق الإعدادات والنافذة ما زالت مفتوحة؟", "choices": ["OK", "Cancel", "Apply", "Restore Defaults"], "answer": 2, "explanation": "Apply يطبّق فورًا لتجرّب قبل الإغلاق."}
```

## الخلاصة

- **Tools > Options...**: Environment، و Text Editor، و Windows Forms Designer، و Languages، و AI، و Keyboard، و Formatting، و Web.
- **Apply** للتجربة، و **Restore Defaults** للعودة إلى الأصل.
- النسخ الاحتياطي التلقائي في `.radide_backup` للطوارئ، والحفظ الحقيقي بـ `Ctrl+S`.
- مسار مفسّر كل لغة في لسان **Languages**، وخوادم اللغات في **Tools > Language Servers and Debuggers...**.
