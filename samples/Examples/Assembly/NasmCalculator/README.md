# Integer Calculator (NASM x64 + form)

A RAD form whose event handlers are x64 NASM: + - x / remainder power, overflow (JO) and divide-by-zero checks, sprintf, a history ListBox and menus.

## What it shows

* Windows Forms for assembly: the form is designed in the designer, `Form1.inc` (the control names) is generated, `handler ... endhandler` blocks react to events (GUI Bridge)
* `rad_get_int`, `rad_set`, `rad_call lstHistory, "AddItem"`, `rad_msgbox`, `rad_end` from `radgui.inc`
* 64-bit arithmetic in registers: `imul`/`idiv`/`cqo`, overflow detection with `jo`, a power loop
* calling the C runtime (`sprintf` with 6 arguments: shadow space + stack arguments)
* menus: File > Clear history / Exit, Help > About

## Run / build / publish

Open the folder (File > Open Project), press F5: the IDE assembles with NASM (downloaded on the first build), links with MinGW gcc and shows the form. Type two numbers and press an operator. Build > Publish makes a program folder (bridge host + the assembled exe).

Language / project type: `asm-nasm`. Files: `Form1.asm`, `Form1.form`, `Form1.inc`, `project.radproj`, `radasm.c`, `radgui.c`, `radgui.h`, `radgui.inc`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the form driven in the IDE's bridge host / the console program fed through stdin).

---

<div dir="rtl">

## آلة حاسبة للأعداد الصحيحة (NASM x64 + نموذج)

نموذج مرئي معالجات أحداثه مكتوبة بلغة التجميع NASM x64: جمع وطرح وضرب وقسمة وباقي وأس، فحص الفيض والقسمة على صفر، sprintf، قائمة سجل وقوائم.

### ماذا يعرض

* نماذج ويندوز للغة التجميع: النموذج يُصمَّم في المصمم، ويُولَّد الملف `Form1.inc` بأسماء الأدوات، وكتل `handler ... endhandler` تستجيب للأحداث (GUI Bridge)
* الماكروهات `rad_get_int` و`rad_set` و`rad_call` و`rad_msgbox` و`rad_end` من `radgui.inc`
* حساب 64 بت في المسجلات: `imul` و`idiv` و`cqo`، واكتشاف الفيض بـ `jo`، وحلقة للأس
* استدعاء مكتبة C (`sprintf` بستة معاملات: مساحة الظل ومعاملات على المكدس)
* قوائم: ملف > مسح السجل / خروج، مساعدة > حول

### التشغيل والبناء والنشر

افتح المجلد (ملف > فتح مشروع) واضغط F5: تجمّع البيئة بـ NASM (يُنزَّل في أول بناء) وتربط بـ MinGW gcc وتعرض النموذج. اكتب رقمين واضغط عملية. Build > Publish يصنع مجلد برنامج (مضيف الجسر + الملف التنفيذي المجمَّع).

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
