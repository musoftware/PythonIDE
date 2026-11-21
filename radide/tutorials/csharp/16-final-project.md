# الدرس 16: المشروع النهائي: قائمة المهام

حان وقت جمع كل ما تعلمته في برنامج حقيقي مفيد: **قائمة مهام** (To-Do List) بنافذة رسومية، تضيف فيها المهام وتعلّمها كمنجزة وتحذفها، وتحفظها في ملف لتجدها عند فتح البرنامج مرة أخرى.

سنستخدم: الأصناف (درس 10)، والقوائم `List<T>` وLINQ (درس 8)، والنصوص (درس 9)، والملفات والاستثناءات (درس 12)، والنماذج والأحداث (الدرسان 13 و14).

## 1) التخطيط قبل الكود

قبل أن تكتب سطرًا واحدًا، اسأل: ما **البيانات**؟ وما **الأفعال**؟

- **البيانات:** مهمة لها عنوان (`Title`) وحالة (منجزة أم لا: `Done`).
- **الأفعال:** إضافة مهمة، وتعليمها كمنجزة، وحذفها، وحفظ الكل في ملف، وتحميلها عند البدء، وعرض عدد المهام الباقية.

> **نصيحة:** افصل **البيانات والمنطق** عن **الواجهة**. صنف `TaskItem` لا يعرف شيئًا عن الأزرار، والنموذج لا يعرف كيف تُحفظ المهام في الملف. هكذا يسهل تعديل كل جزء وحده.

## 2) إنشاء المشروع ورسم النافذة

1. **File > New Project...**، ثم **C# (GUI Bridge, .NET)** و**Windows Application**، واسم المشروع `TodoApp`.
2. اجعل خاصية **Text** للنموذج `قائمة المهام`.
3. ارسم الأدوات التالية:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtTask` | (فارغ) |
| `Button` | `btnAdd` | `إضافة` |
| `ListBox` | `lstTasks` | |
| `Button` | `btnDone` | `تمت ✓` |
| `Button` | `btnDelete` | `حذف` |
| `Button` | `btnClearDone` | `حذف المنجزة` |
| `Label` | `lblStatus` | (فارغ) |

4. أضف ملف كود جديدًا للصنف: **Project > Add Module...** (مشروع > إضافة وحدة برمجية...) باسم `TaskItem`، فيصبح عندك `TaskItem.cs`.

## 3) صنف البيانات والتخزين: `TaskItem.cs`

```csharp
// TaskItem.cs - مهمة واحدة + الحفظ والتحميل من ملف
public class TaskItem
{
    public string Title { get; set; }
    public bool Done { get; set; }

    public override string ToString() => (Done ? "✓ " : "☐ ") + Title;

    // سطر في الملف: 1|اشتر الخبز   أو   0|ذاكر الدرس
    public string ToLine() => (Done ? "1" : "0") + "|" + Title;

    public static TaskItem FromLine(string line)
    {
        string[] parts = line.Split('|', 2);
        return new TaskItem { Done = parts[0] == "1", Title = parts.Length > 1 ? parts[1] : "" };
    }

    public static List<TaskItem> Load(string path)
    {
        var list = new List<TaskItem>();
        try
        {
            foreach (string line in File.ReadAllLines(path))
                if (line.Trim() != "")
                    list.Add(FromLine(line));
        }
        catch (FileNotFoundException)
        {
            // أول تشغيل: لا يوجد ملف بعد
        }
        return list;
    }

    public static void Save(string path, List<TaskItem> tasks)
    {
        File.WriteAllLines(path, tasks.Select(t => t.ToLine()));
    }
}
```

لاحظ `Split('|', 2)`: الرقم 2 يعني «قسّم إلى جزأين فقط»، فإذا احتوى عنوان المهمة على `|` لا يتلف.

## 4) كود النموذج: `Form1.cs`

اضغط **جرّبه** لترى المشروع كاملًا بالملفين (السطر `// #file: TaskItem.cs` يفصل بينهما في الدرس):

<!-- test: {"events": [{"txtTask.Text": "Buy bread"}, "btnAdd Click", {"txtTask.Text": "Study C#"}, "btnAdd Click", {"txtTask.Text": "Call Mom"}, "btnAdd Click", {"lstTasks.ListIndex": "0"}, "btnDone Click", "btnClearDone Click"], "expect": {"lstTasks.ListCount": "2", "lstTasks.Items": "☐ Study C#|☐ Call Mom", "lblStatus.Text": "المهام: 2، الباقي: 2"}} -->
```csharp form run
public static partial class Form1
{
    const string FileName = "tasks.txt";
    static List<TaskItem> tasks = new List<TaskItem>();

    static void Form1_Load(RadEvent e)
    {
        File.Delete(FileName);              // نبدأ هذا المثال بقائمة فارغة
        tasks = TaskItem.Load(FileName);
        RefreshList();
    }

    // يعيد ملء القائمة من البيانات ويحدّث العنوان ثم يحفظ
    static void RefreshList()
    {
        lstTasks.Clear();
        foreach (TaskItem t in tasks)
            lstTasks.AddItem(t.ToString());
        int left = tasks.Count(t => !t.Done);
        lblStatus.Text = $"المهام: {tasks.Count}، الباقي: {left}";
        TaskItem.Save(FileName, tasks);
    }

    static void btnAdd_Click(RadEvent e)
    {
        string title = txtTask.Text.Trim();
        if (title == "")
        {
            MsgBox("اكتب المهمة أولًا");
            return;
        }
        if (tasks.Any(t => t.Title.Equals(title, StringComparison.OrdinalIgnoreCase)))
        {
            MsgBox("هذه المهمة موجودة بالفعل");
            return;
        }
        tasks.Add(new TaskItem { Title = title });
        txtTask.Text = "";
        txtTask.SetFocus();
        RefreshList();
    }

    static TaskItem Selected()
    {
        int i = lstTasks.ListIndex;
        if (i < 0 || i >= tasks.Count)
        {
            MsgBox("اختر مهمة من القائمة أولًا");
            return null;
        }
        return tasks[i];
    }

    static void btnDone_Click(RadEvent e)
    {
        TaskItem t = Selected();
        if (t == null)
            return;
        t.Done = !t.Done;                   // ضغطة ثانية تلغي العلامة
        RefreshList();
    }

    static void btnDelete_Click(RadEvent e)
    {
        TaskItem t = Selected();
        if (t == null)
            return;
        tasks.Remove(t);
        RefreshList();
    }

    static void btnClearDone_Click(RadEvent e)
    {
        int removed = tasks.RemoveAll(t => t.Done);
        Console.WriteLine($"حُذفت {removed} مهمة منجزة");
        RefreshList();
    }
}
// #file: TaskItem.cs
public class TaskItem
{
    public string Title { get; set; }
    public bool Done { get; set; }

    public override string ToString() => (Done ? "✓ " : "☐ ") + Title;

    public string ToLine() => (Done ? "1" : "0") + "|" + Title;

    public static TaskItem FromLine(string line)
    {
        string[] parts = line.Split('|', 2);
        return new TaskItem { Done = parts[0] == "1", Title = parts.Length > 1 ? parts[1] : "" };
    }

    public static List<TaskItem> Load(string path)
    {
        var list = new List<TaskItem>();
        try
        {
            foreach (string line in File.ReadAllLines(path))
                if (line.Trim() != "")
                    list.Add(FromLine(line));
        }
        catch (FileNotFoundException)
        {
        }
        return list;
    }

    public static void Save(string path, List<TaskItem> tasks)
    {
        File.WriteAllLines(path, tasks.Select(t => t.ToLine()));
    }
}
```

```text output
حُذفت 1 مهمة منجزة
```

> **ملحوظة:** في المثال يحذف `Form1_Load` الملف عند البدء لكي يبدأ المثال دائمًا بقائمة فارغة. في برنامجك الحقيقي **احذف** السطر `File.Delete(FileName);` لكي تبقى مهامك محفوظة بين مرة وأخرى.

## 5) كيف يعمل البرنامج؟

1. **عند البدء** (`Form1_Load`): تُحمّل المهام من `tasks.txt` إلى القائمة `tasks`.
2. **مصدر الحقيقة** هو `List<TaskItem> tasks` وليس `ListBox`. الـ `ListBox` مجرد **عرض** لها، تعيد `RefreshList()` بناءه بعد كل تغيير.
3. **رقم العنصر في `ListBox`** يطابق رقمه في `tasks` لأننا نملؤهما بنفس الترتيب، لذلك `tasks[lstTasks.ListIndex]` هي المهمة المختارة.
4. **الحفظ التلقائي:** كل تغيير يمر عبر `RefreshList()` التي تحفظ الملف، فلا تضيع المهام إذا أُغلق البرنامج فجأة.

## 6) جرّب وصحّح

- ضع نقطة توقف (F9) في `btnDone_Click` واضغط F5، ثم اختر مهمة واضغط «تمت ✓»، وراقب في **Locals** قيمة `t.Done` قبل السطر وبعده (F10).
- افتح الملف `tasks.txt` من مجلد المشروع لترى كيف تُخزّن المهام.

## 7) أفكار للتطوير (تحدَّ نفسك)

1. **البحث:** مربع نص `txtSearch` وحدث `txtSearch_TextChanged` يعرض فقط المهام التي تحتوي النص (`Where` و`Contains`).
2. **الأولوية:** أضف للصنف خاصية `Priority` (عالية / عادية) و`ComboBox` لاختيارها، ورتّب القائمة بها (`OrderByDescending`).
3. **تاريخ الإضافة:** خاصية `DateTime Created` تُحفظ في الملف وتظهر في `ToString()`.
4. **التأكيد قبل الحذف:** اسأل المستخدم بـ `InputBox("اكتب نعم للتأكيد")` قبل حذف مهمة.
5. **JSON:** استبدل صيغة الملف بـ JSON باستخدام `System.Text.Json` أو حزمة `Newtonsoft.Json` (درس 15).

## تمرين: إحصائيات المهام

أضف زرًا `btnStats` يعرض في `lblStatus` نسبة المهام المنجزة بالشكل `أنجزت 1 من 3 (33%)`.

<!-- test: {"events": [{"txtTask.Text": "A"}, "btnAdd Click", {"txtTask.Text": "B"}, "btnAdd Click", {"txtTask.Text": "C"}, "btnAdd Click", {"lstTasks.ListIndex": "1"}, "btnDone Click", "btnStats Click"], "expect": {"lblStatus.Text": "أنجزت 1 من 3 (33%)"}} -->
```csharp form exercise
public static partial class Form1
{
    static List<TaskItem> tasks = new List<TaskItem>();

    static void btnAdd_Click(RadEvent e)
    {
        tasks.Add(new TaskItem { Title = txtTask.Text });
        lstTasks.AddItem(txtTask.Text);
        txtTask.Text = "";
    }

    static void btnDone_Click(RadEvent e)
    {
        int i = lstTasks.ListIndex;
        if (i >= 0)
            tasks[i].Done = true;
    }

    static void btnStats_Click(RadEvent e)
    {
        // اكتب هنا: أنجزت X من Y (Z%)
    }
}
// #file: TaskItem.cs
public class TaskItem
{
    public string Title { get; set; }
    public bool Done { get; set; }
}
```

<!-- test: {"events": [{"txtTask.Text": "A"}, "btnAdd Click", {"txtTask.Text": "B"}, "btnAdd Click", {"txtTask.Text": "C"}, "btnAdd Click", {"lstTasks.ListIndex": "1"}, "btnDone Click", "btnStats Click"], "expect": {"lblStatus.Text": "أنجزت 1 من 3 (33%)"}} -->
```csharp form solution
public static partial class Form1
{
    static List<TaskItem> tasks = new List<TaskItem>();

    static void btnAdd_Click(RadEvent e)
    {
        tasks.Add(new TaskItem { Title = txtTask.Text });
        lstTasks.AddItem(txtTask.Text);
        txtTask.Text = "";
    }

    static void btnDone_Click(RadEvent e)
    {
        int i = lstTasks.ListIndex;
        if (i >= 0)
            tasks[i].Done = true;
    }

    static void btnStats_Click(RadEvent e)
    {
        int done = tasks.Count(t => t.Done);
        int percent = tasks.Count == 0 ? 0 : done * 100 / tasks.Count;
        lblStatus.Text = $"أنجزت {done} من {tasks.Count} ({percent}%)";
    }
}
// #file: TaskItem.cs
public class TaskItem
{
    public string Title { get; set; }
    public bool Done { get; set; }
}
```

## اختبر نفسك

```quiz
{"question": "لماذا نحتفظ بالمهام في List<TaskItem> ولا نعتمد على ListBox وحدها؟", "choices": ["لأن ListBox بطيئة", "لأن القائمة هي مصدر البيانات الحقيقي والـ ListBox مجرد عرض لها", "لأن ListBox لا تقبل النصوص", "لا يوجد سبب"], "answer": 1, "explanation": "فصل البيانات عن العرض يجعل الحفظ والبحث والترتيب سهلًا."}
```

```quiz
{"question": "ما فائدة Split('|', 2) عند قراءة سطر المهمة؟", "choices": ["تسريع القراءة", "التقسيم إلى جزأين فقط حتى لا يتلف عنوان يحتوي على |", "حذف الرمز |", "لا فائدة"], "answer": 1, "explanation": "الجزء الأول هو الحالة، والباقي كله عنوان حتى لو احتوى على |."}
```

```quiz
{"question": "ماذا تفعل tasks.RemoveAll(t => t.Done)؟", "choices": ["تحذف كل المهام", "تحذف المهام المنجزة فقط وترجع عددها", "تعلّم كل المهام كمنجزة", "ترتب المهام"], "answer": 1, "explanation": "RemoveAll تحذف كل عنصر يحقق الشرط وترجع عدد العناصر المحذوفة."}
```

## مبروك!

أنهيت دورة C#. تعلمت المتغيرات والشروط والحلقات والدوال والمجموعات والنصوص والأصناف والوراثة والاستثناءات والملفات، وبنيت برامج رسومية كاملة، وأضفت حزم NuGet، واستخدمت المصحح.

**ماذا بعد؟**

- دليل **مشاريع Visual Studio في RAD IDE**: افتح مشاريع `.sln` و`.csproj` الحقيقية وصمم نماذج Windows Forms.
- تعمق في **LINQ** و**async/await** للبرمجة غير المتزامنة.
- جرّب **ASP.NET Core** لمواقع الويب، أو **Unity** للألعاب، وكلاهما بلغة C#.
