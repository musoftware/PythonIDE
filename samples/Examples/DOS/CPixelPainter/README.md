# Pixel Painter (C, mode 13h, DOS)

Keyboard paint program in C: arrow keys draw, 1-9 colours, R random rectangle, B box, C clear - straight into VGA memory at A000:0000.

## What it shows

* far pointers (`MK_FP`), `int86` for INT 10h mode changes
* extended keys with getch (0 / 0xE0 + scan code)
* a palette strip, clipping, statistics printed back in text mode
* OpenWatcom wcl -bt=dos -ms

## Run / build / publish

Ctrl+F5 builds CPIXELPA.EXE (OpenWatcom is downloaded on the first build) and runs it in DOSBox-X. Esc ends and prints the statistics.

Language / project type: `dos-c`. Files: `MAIN.C`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (DOSBox-X without a window, keys typed with RADKEYS, output and screen read back).

---

<div dir="rtl">

## رسام البكسلات (C، الوضع 13h، دوس)

برنامج رسم بلوحة المفاتيح بلغة C: الأسهم ترسم، 1-9 للألوان، R مستطيل عشوائي، B مربع، C مسح - مباشرة في ذاكرة VGA عند A000:0000.

### ماذا يعرض

* المؤشرات البعيدة (`MK_FP`) و`int86` لتغيير الوضع عبر INT 10h
* المفاتيح الممتدة مع getch (0 أو 0xE0 ثم رمز المسح)
* شريط ألوان وقص الرسم وإحصاءات تُطبع بعد الرجوع للوضع النصي
* OpenWatcom wcl -bt=dos -ms

### التشغيل والبناء والنشر

Ctrl+F5 يبني CPIXELPA.EXE (يُنزَّل OpenWatcom في أول بناء) ويشغله في DOSBox-X. Esc ينهي ويطبع الإحصاءات.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
