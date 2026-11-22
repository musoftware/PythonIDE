# Raster Scroller (Commodore 64)

Raster bars by busy-waiting on $D012, a smooth fine-scroll text row ($D016 just for that row), and a balloon sprite moved by joystick or W A S D.

## What it shows

* a BASIC SYS line + ca65 program
* raster timing without interrupts, VIC-II fine X scroll and 38-column mode
* a hardware sprite (pointer, colour, enable, position), KERNAL GETIN / CHROUT
* F5 runs it in VICE; the IDE's VICE monitor link can read memory and type keys

## Run / build / publish

F5 builds C64RasterScroller.prg and runs it in VICE. Joystick 2 or W A S D, Space flashes the border, Q returns to BASIC.

Language / project type: `retro-c64`. Files: `c64.cfg`, `main.s`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the emulator hooks (Mesen 2 headless frames, VICE monitor, Stella window)).

---

<div dir="rtl">

## التمرير والخطوط النقطية (كومودور 64)

خطوط ملونة بانتظار $D012، وسطر نص يتحرك بنعومة ($D016 لهذا السطر فقط)، وكائن بالون يتحرك بعصا التحكم أو W A S D.

### ماذا يعرض

* سطر BASIC SYS مع برنامج ca65
* توقيت الخطوط النقطية بدون مقاطعات، والتمرير الدقيق في VIC-II ووضع 38 عمودا
* كائن عتادي (المؤشر واللون والتفعيل والموضع) و KERNAL GETIN / CHROUT
* F5 يشغله في VICE؛ وصلة مراقب VICE في البيئة تقرأ الذاكرة وتكتب المفاتيح

### التشغيل والبناء والنشر

F5 يبني C64RasterScroller.prg ويشغله في VICE. عصا التحكم 2 أو W A S D، المسافة تومض الإطار، Q للرجوع إلى BASIC.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
