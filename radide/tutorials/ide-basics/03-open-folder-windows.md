# الدرس 3: فتح مجلد، وفتح ملف، ونافذة جديدة

**في هذا الدرس ستتعلم:**

- الفرق بين **Open Project** و **Open Folder** و **Open File**.
- ماذا تفعل البيئة عندما تفتح مجلدًا ليس فيه ملف مشروع: نافذة **Detect Project Type**.
- فتح مشروعات البيئات الأخرى "في مكانها" (Visual Studio، VB6، Cargo، Laravel ...).
- العمل بعدة نوافذ مستقلة: **File > New Window**، وإعداد "نافذة واحدة".

## ثلاثة أبواب للدخول

تخيّل مكتبة لها ثلاثة أبواب:

| الأمر | الاختصار | متى أستخدمه؟ |
|---|---|---|
| **File > Open Project...** (ملف > فتح مشروع...) | `Ctrl+Shift+O` | عندك ملف `project.radproj` أو `.radsln`، أو ملف مشروع من بيئة أخرى مثل `.sln` أو `.vbp` |
| **File > Open Folder...** (ملف > فتح مجلد...) | `Ctrl+K` ثم `Ctrl+O` | عندك مجلد كامل، سواء كان مشروعًا أم مجرد ملفات |
| **File > Open File...** (ملف > فتح ملف...) | `Ctrl+O` | تريد ملفًا واحدًا فقط في لسان جديد |

> 💡 الاختصار `Ctrl+K Ctrl+O` اسمه **اختصار مزدوج** (Chord): اضغط `Ctrl+K`، ارفع يدك، ثم اضغط `Ctrl+O`.

## Open Folder خطوة بخطوة

1. اختر **File > Open Folder...** واختر المجلد.
2. البيئة تفحص المجلد:
   - إذا وجدت فيه `project.radproj` أو ملف `.radsln` تفتحه مباشرة كمشروع RAD IDE.
   - إذا تعرّفت على نوع المشروع (مثل موقع Laravel، أو تطبيق Flutter، أو مشروع Cargo) تظهر نافذة **Detect Project Type** (اكتشاف نوع المشروع).
   - إذا لم تتعرف على شيء تفتحه **كمجلد عادي** (Folder workspace)، مثل VS Code.

### نافذة Detect Project Type

فيها سطر **Detected:** يصف ما وجدته البيئة، مثلًا: `Laravel site (Laravel 11.x, PHP ^8.2)`، ثم ثلاثة أزرار:

| الزر | الاسم العربي | ماذا يحدث؟ |
|---|---|---|
| **Create RAD IDE project** | إنشاء مشروع RAD IDE | يكتب `project.radproj` في المجلد، فتعمل كل مزايا البيئة (المصمم، و F5، والقوالب...) |
| **Open in place without project file** | فتح في مكانه بدون ملف مشروع | يفتح المشروع كما هو، ولا يكتب أي ملف في مجلدك. ملفات البيئة الأخرى تبقى هي المرجع |
| **Open as plain folder** | فتح كمجلد عادي | شجرة ملفات فقط، مع البحث و Git والطرفية |

وفي الأسفل خانة **Don't ask again for this folder** (لا تسأل مرة أخرى عن هذا المجلد) لتتذكر البيئة اختيارك.

إذا وجدت البيئة **أكثر من مشروع** في مجلد واحد (مثلًا `backend/` بلغة PHP و `app/` بلغة Flutter) تعرض قائمة بها خانات اختيار، ثم تنشئ **حلًا** فيه مشروع لكل مجلد.

> 💡 يمكنك طلب الفحص لاحقًا: انقر المجلد في مستكشف الحلول بالزر الأيمن > **Detect Project Type...**.

### "في مكانه" يعني ماذا؟

**في مكانه** (In place) يعني أن البيئة تقرأ ملفات المشروع الأصلية (`.sln` أو `.vbp` أو `Cargo.toml` أو `pom.xml` ...) ولا تنسخها ولا تحوّلها.
مثل ضيف يقرأ كتابك على مكتبك دون أن ينقله إلى بيته. إذا عدت إلى Visual Studio غدًا ستجد مشروعك كما تركته.

### المجلد العادي و VS Code

إذا كان في المجلد `.vscode/tasks.json` أو `launch.json` فإن البيئة تقرؤها: المهام تصبح أوامر، وإعدادات التشغيل تصبح أهدافًا للتشغيل والتصحيح.
وملف `.code-workspace` يُفتح كحل فيه مجلد لكل جزء.

## Open File: ملف واحد

**File > Open File...** يفتح أي ملف في لسان. وإذا كان الملف نموذجًا (`.form`) أو تقريرًا أو مشهدًا، تفتح البيئة مشروعه أولًا ثم الملف.
ملفات المشروعات (`.radproj`، `.radsln`، `.sln`، `.vbp` ...) تُفتح كمشروعات.

## نافذة جديدة: File > New Window

أحيانًا تريد مشروعين أمامك في وقت واحد، مثل تطبيق سطح المكتب وموقع الويب الخاص به.

1. اختر **File > New Window** (ملف > نافذة جديدة) أو `Ctrl+Alt+N`.
2. تفتح نافذة RAD IDE **مستقلة تمامًا**: لها مشروعها، ونوافذها، وتشغيلها الخاص.
3. افتح فيها المشروع الثاني.

كل نافذة تعمل في عملية (Process) منفصلة، فإذا توقف برنامج في نافذة لا تتأثر الأخرى.

### "نافذة واحدة" عند الفتح من ويندوز

عندما تنقر مرتين على ملف `.radsln` في مستكشف ويندوز والبيئة مفتوحة، فإن الافتراضي أن يُفتح الملف **في النافذة المفتوحة** بدل تشغيل نسخة جديدة.
هذا الإعداد في **Tools > Options... > Environment** (أدوات > خيارات... > البيئة) ضمن **Windows integration** (التكامل مع ويندوز):
**Open files in the running RAD IDE window** (فتح الملفات في نافذة RAD IDE المفتوحة بالفعل). أزل العلامة إذا أردت نافذة جديدة لكل ملف.

## إغلاق الحل والمشروعات الحديثة

- **File > Close Solution** (ملف > إغلاق الحل) يغلق كل المشروعات المفتوحة. إذا كانت هناك تغييرات غير محفوظة تسألك البيئة.
- **File > Recent Projects and Solutions** (ملف > المشروعات والحلول الحديثة) يعرض آخر ما فتحت.
- إذا أردت أن يعود آخر حل تلقائيًا عند التشغيل: **Tools > Options... > Environment** > **Reopen the last solution on startup** (إعادة فتح آخر حل عند بدء التشغيل).

## مثال: برنامج تجرّبه ثم تفتح مجلده

اضغط «جرّبه»، ثم اختر **Project > Open Project Folder** (مشروع > فتح مجلد المشروع) لترى الملفات التي كتبتها البيئة في مجلد الدروس:

```vb run
Sub Main()
    Dim kinds(2) As String
    Dim i As Integer
    kinds(0) = "Open Project: ملف مشروع"
    kinds(1) = "Open Folder: مجلد كامل"
    kinds(2) = "Open File: ملف واحد"
    For i = 0 To 2
        Debug.Print (i + 1) & ") " & kinds(i)
    Next i
End Sub
```

```text output
1) Open Project: ملف مشروع
2) Open Folder: مجلد كامل
3) Open File: ملف واحد
```

## أخطاء شائعة

- **اختيار Create RAD IDE project لمشروع يعمل عليه زملاء ببيئة أخرى:** سيُضاف ملف `project.radproj` إلى المجلد. إذا لم ترد ذلك اختر **Open in place without project file**.
- **الضغط على `Ctrl+O` بدل `Ctrl+K Ctrl+O`:** الأول يفتح ملفًا واحدًا، والثاني مجلدًا.
- **انتظار نافذة جديدة عند النقر المزدوج على ملف:** الإعداد الافتراضي يفتحه في النافذة الحالية. استخدم `Ctrl+Alt+N` أولًا، أو غيّر الإعداد.

## تمرين

### تمرين 1: أكمل القائمة

أضف عنصرًا رابعًا للمصفوفة: `New Window: نافذة مستقلة`، واجعل الحلقة تطبع العناصر الأربعة.

```vb exercise
Sub Main()
    Dim kinds(2) As String
    Dim i As Integer
    kinds(0) = "Open Project: ملف مشروع"
    kinds(1) = "Open Folder: مجلد كامل"
    kinds(2) = "Open File: ملف واحد"
    For i = 0 To 2
        Debug.Print (i + 1) & ") " & kinds(i)
    Next i
End Sub
```

```vb solution
Sub Main()
    Dim kinds(3) As String
    Dim i As Integer
    kinds(0) = "Open Project: ملف مشروع"
    kinds(1) = "Open Folder: مجلد كامل"
    kinds(2) = "Open File: ملف واحد"
    kinds(3) = "New Window: نافذة مستقلة"
    For i = 0 To 3
        Debug.Print (i + 1) & ") " & kinds(i)
    Next i
End Sub
```

```text output
1) Open Project: ملف مشروع
2) Open Folder: مجلد كامل
3) Open File: ملف واحد
4) New Window: نافذة مستقلة
```

### مهمة عملية: مجلد بلا مشروع

1. أنشئ في مستكشف ويندوز مجلدًا جديدًا وضع فيه ملفًا نصيًا `notes.txt`.
2. افتحه بـ **File > Open Folder...**. لاحظ أنه يُفتح كمجلد عادي لأن البيئة لم تجد نوع مشروع.
3. اضغط `Ctrl+Alt+N` لفتح نافذة ثانية، وافتح فيها أي مشروع. صارت عندك نافذتان مستقلتان.

## اختبر نفسك

```quiz
{"question": "تريد فتح مشروع Visual Studio لزميلك دون إضافة أي ملف إلى مجلده. ماذا تختار في نافذة Detect Project Type؟", "choices": ["Create RAD IDE project", "Open in place without project file", "Cancel", "احذف ملف .sln أولًا"], "answer": 1, "explanation": "الفتح في المكان يقرأ ملفات المشروع الأصلية ولا يكتب شيئًا في المجلد."}
```

```quiz
{"question": "ما اختصار File > Open Folder...؟", "choices": ["`Ctrl+O`", "`Ctrl+K` ثم `Ctrl+O`", "`Ctrl+Shift+O`", "`Ctrl+Alt+N`"], "answer": 1, "explanation": "هو اختصار مزدوج: Ctrl+K ثم Ctrl+O. أما Ctrl+O وحده فيفتح ملفًا."}
```

```quiz
{"question": "ماذا يفعل `Ctrl+Alt+N`؟", "choices": ["ينشئ مشروعًا جديدًا", "يفتح نافذة RAD IDE مستقلة أخرى", "يضيف نموذجًا", "يغلق الحل"], "answer": 1, "explanation": "File > New Window تفتح نافذة مستقلة بمشروعها وتشغيلها الخاص."}
```

## الخلاصة

- **Open Project** لملف مشروع، و **Open Folder** (`Ctrl+K Ctrl+O`) لمجلد، و **Open File** (`Ctrl+O`) لملف واحد.
- عند فتح مجلد تكتشف البيئة نوعه وتعرض: إنشاء مشروع، أو فتح في المكان، أو مجلد عادي.
- **File > New Window** (`Ctrl+Alt+N`) تفتح نافذة مستقلة، وخيار "النافذة الواحدة" في **Options > Environment**.
