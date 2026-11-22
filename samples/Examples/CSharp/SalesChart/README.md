# Sales Chart - C#

A bar chart of six months drawn with Panels: set a value, click inside the chart to set a bar with the mouse, animate the bars with a timer, choose the bar colour, save / load the data as CSV.

## What it shows

* moving / resizing controls at run time (`Top`, `Height`) to draw a chart
* `MouseDown` with coordinates (X picks the bar, Y the value)
* a Timer animation whose speed comes from a TrackBar; a CheckBox turns it on / off
* ColorDialog (`ShowColor`, `Color` = "#RRGGBB") and `BackColor`
* NumericUpDown + ComboBox input, statistics (total / average / best month), CSV file I/O

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the C# code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed)

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs the .NET SDK (dotnet).
3. Try: F5 (the bars grow), click high in the chart above Mar, press Random data, Bar colour..., Save, Load.

## Publish

Build > Publish: a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed). The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmChart.cs`
* `frmChart.form`
* `frmChart_designer.cs`
* `project.radproj`

---

## مخطط المبيعات - C#

مخطط أعمدة لستة أشهر مرسوم بعناصر Panel: اضبط قيمة، أو انقر داخل المخطط لضبط عمود بالماوس، حرّك الأعمدة بمؤقت، اختر لون الأعمدة، واحفظ البيانات أو حمّلها كملف CSV.

### ماذا يعرض

* تحريك العناصر وتغيير أحجامها أثناء التشغيل (`Top` و`Height`) لرسم المخطط
* حدث `MouseDown` مع الإحداثيات (X يحدد العمود وY القيمة)
* حركة بمؤقت سرعتها من شريط TrackBar، ومربع اختيار يشغّلها أو يوقفها
* حوار الألوان (`ShowColor` و`Color` = "#RRGGBB") و`BackColor`
* إدخال بـ NumericUpDown وقائمة منسدلة، وإحصاءات (المجموع / المتوسط / أفضل شهر)، وملف CSV

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود C# يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء)

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج .NET SDK (dotnet).
3. جرّب: F5 (تنمو الأعمدة)، انقر عاليًا في المخطط فوق Mar، ثم بيانات عشوائية، ولون الأعمدة، وحفظ ثم تحميل.

### النشر

البناء > النشر: ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
