# Guess the Number (GNU as + form)

A game in GNU assembler (Intel syntax): RDTSC random number, too high / too low hints, tries counter, guesses ListBox, disabled button when won.

## What it shows

* GNU as forms with `.intel_syntax noprefix` and `radgui_intel.inc`
* `rdtsc` + `div` for a random number, `rad_set_int btnGuess, Enabled, 0`
* passing your own strings in registers (`lea rbx, [rip + buf]`)
* MsgBox for invalid input

## Run / build / publish

F5 builds with the MinGW `as` + gcc and shows the form; type guesses from 1 to 100. Build > Publish: bridge program folder.

Language / project type: `asm-gas`. Files: `Form1.form`, `Form1.inc`, `Form1.s`, `project.radproj`, `radasm.c`, `radgui.c`, `radgui.h`, `radgui_intel.inc`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the form driven in the IDE's bridge host / the console program fed through stdin).

---

<div dir="rtl">

## خمّن الرقم (GNU as + نموذج)

لعبة بمجمّع GNU (صيغة إنتل): رقم عشوائي من RDTSC، تلميحات أكبر/أصغر، عداد المحاولات، قائمة التخمينات، وتعطيل الزر عند الفوز.

### ماذا يعرض

* نماذج GNU as مع `.intel_syntax noprefix` و`radgui_intel.inc`
* `rdtsc` و`div` لرقم عشوائي، و`rad_set_int btnGuess, Enabled, 0`
* تمرير النصوص الخاصة في المسجلات (`lea rbx, [rip + buf]`)
* رسالة للإدخال غير الصحيح

### التشغيل والبناء والنشر

F5 يبني بـ `as` و gcc من MinGW ويعرض النموذج؛ خمّن أرقاما من 1 إلى 100. Build > Publish: مجلد برنامج بالجسر.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
