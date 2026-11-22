# Temperature Converter (FASM + form)

Celsius/Fahrenheit converter in FASM x64: rounded integer division, a CMP/Jcc chain describing the weather and a ProgressBar.

## What it shows

* FASM forms (`format MS64 COFF` object linked by gcc with the GUI Bridge client)
* `rad_set_int barHeat, 'Value', rbx` moves a ProgressBar
* rounding integer division (halves away from zero), clamping 0..100
* FASM note: the `rad_*` macros define labels, so jump targets after them are global names

## Run / build / publish

F5 builds (FASM is downloaded on the first build) and shows the form; type a temperature and choose a direction. Build > Publish: bridge program folder.

Language / project type: `asm-fasm`. Files: `Form1.asm`, `Form1.form`, `Form1.inc`, `project.radproj`, `radasm.c`, `radgui.c`, `radgui.h`, `radgui_fasm.inc`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the form driven in the IDE's bridge host / the console program fed through stdin).

---

<div dir="rtl">

## محول درجات الحرارة (FASM + نموذج)

محول بين المئوية والفهرنهايت بلغة FASM x64: قسمة صحيحة مع التقريب، سلسلة CMP/Jcc لوصف الطقس، وشريط تقدم.

### ماذا يعرض

* نماذج FASM (كائن `format MS64 COFF` يُربط بـ gcc مع عميل GUI Bridge)
* `rad_set_int barHeat, 'Value', rbx` يحرك شريط التقدم
* قسمة صحيحة مع التقريب وحصر القيمة بين 0 و100
* ملاحظة FASM: الماكروهات `rad_*` تعرّف تسميات، لذلك أهداف القفز بعدها أسماء عامة

### التشغيل والبناء والنشر

F5 يبني (يُنزَّل FASM في أول بناء) ويعرض النموذج؛ اكتب درجة الحرارة واختر الاتجاه. Build > Publish: مجلد برنامج بالجسر.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
