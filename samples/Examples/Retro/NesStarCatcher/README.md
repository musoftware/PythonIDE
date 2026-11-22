# Star Catcher (NES)

Catch falling stars with a basket: background drawn at reset, BCD score written to the name table in vblank, LFSR random, speed-ups.

## What it shows

* iNES header, PPU warm-up, palettes, name + attribute tables
* OAM DMA in the NMI, a 16-pixel metasprite, controller reading (B = run)
* safe VRAM updates in vblank + scroll reset
* original CHR tiles in `tiles.inc` (the pixel art is in the comments); ca65 + ld65

## Run / build / publish

F5 builds NesStarCatcher.nes (cc65 is downloaded on the first build) and runs it in Mesen. Left / Right move, hold B to run.

Language / project type: `retro-nes`. Files: `main.s`, `nes.cfg`, `nes.inc`, `project.radproj`, `tiles.inc`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the emulator hooks (Mesen 2 headless frames, VICE monitor, Stella window)).

---

<div dir="rtl">

## صائد النجوم (نينتندو NES)

اصطد النجوم المتساقطة بسلة: الخلفية تُرسم عند البدء، والنقاط بنظام BCD تُكتب في جدول الأسماء أثناء vblank، وأرقام عشوائية بـ LFSR، وزيادة السرعة.

### ماذا يعرض

* رأس iNES وتسخين PPU ولوحات الألوان وجدولا الأسماء والسمات
* OAM DMA في NMI وكائن من 16 بكسل وقراءة وحدة التحكم (B للجري)
* تحديث VRAM بأمان أثناء vblank وإعادة ضبط التمرير
* بلاطات CHR أصلية في `tiles.inc` (الرسم في التعليقات)؛ ca65 و ld65

### التشغيل والبناء والنشر

F5 يبني NesStarCatcher.nes (يُنزَّل cc65 في أول بناء) ويشغله في Mesen. يسار/يمين للحركة، واضغط B للجري.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
