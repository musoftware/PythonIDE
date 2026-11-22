# Sales Chart - Fortran

A bar chart of six months drawn with Panels: set a value, click inside the chart to set a bar with the mouse, animate the bars with a timer, choose the bar colour, save / load the data as CSV.

## What it shows

* moving / resizing controls at run time (`Top`, `Height`) to draw a chart
* `MouseDown` with coordinates (X picks the bar, Y the value)
* a Timer animation whose speed comes from a TrackBar; a CheckBox turns it on / off
* ColorDialog (`ShowColor`, `Color` = "#RRGGBB") and `BackColor`
* NumericUpDown + ComboBox input, statistics (total / average / best month), CSV file I/O
* Array intrinsics (`sum`, `maxloc`), `random_number`, `open` / `read` with `iostat`.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the Fortran code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with `rad_set` / `rad_get` / `rad_call` / `rad_arg` (module radgui)
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native Win32 exe (gfortran + radforms), about 470 KB, no Python

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs gfortran (MinGW-w64; found or downloaded by the IDE).
3. Try: F5 (the bars grow), click high in the chart above Mar, press Random data, Bar colour..., Save, Load.

## Publish

Build > Publish: a native Win32 exe (gfortran + radforms), about 470 KB, no Python. The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmChart.f90`
* `frmChart.form`
* `frmChart_designer.f90`
* `project.radproj`

---

## مخطط المبيعات - Fortran

مخطط أعمدة لستة أشهر مرسوم بعناصر Panel: اضبط قيمة، أو انقر داخل المخطط لضبط عمود بالماوس، حرّك الأعمدة بمؤقت، اختر لون الأعمدة، واحفظ البيانات أو حمّلها كملف CSV.

### ماذا يعرض

* تحريك العناصر وتغيير أحجامها أثناء التشغيل (`Top` و`Height`) لرسم المخطط
* حدث `MouseDown` مع الإحداثيات (X يحدد العمود وY القيمة)
* حركة بمؤقت سرعتها من شريط TrackBar، ومربع اختيار يشغّلها أو يوقفها
* حوار الألوان (`ShowColor` و`Color` = "#RRGGBB") و`BackColor`
* إدخال بـ NumericUpDown وقائمة منسدلة، وإحصاءات (المجموع / المتوسط / أفضل شهر)، وملف CSV
* دوال المصفوفات (`sum` و`maxloc`) و`random_number` و`open` / `read` مع `iostat`.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود Fortran يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر `rad_set` / `rad_get` / `rad_call` / `rad_arg` (module radgui)
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف exe أصلي لويندوز (gfortran + radforms) بحجم 470 ك.ب تقريبًا، بدون بايثون

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج gfortran (MinGW-w64؛ يجده الـ IDE أو ينزّله).
3. جرّب: F5 (تنمو الأعمدة)، انقر عاليًا في المخطط فوق Mar، ثم بيانات عشوائية، ولون الأعمدة، وحفظ ثم تحميل.

### النشر

البناء > النشر: ملف exe أصلي لويندوز (gfortran + radforms) بحجم 470 ك.ب تقريبًا، بدون بايثون.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
