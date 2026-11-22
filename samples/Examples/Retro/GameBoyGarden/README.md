# Garden Planter (Game Boy)

Walk the gardener and press A to plant flowers on the grass; the count uses DAA; Start clears the garden.

## What it shows

* cartridge header filled by rgbfix, LCD off/on only in vblank
* a background map built by code (fence, path, tufts), map writes in vblank
* both joypad groups with edge detection; `daa` for BCD
* original tiles in `tiles.inc`; RGBDS (rgbasm, rgblink, rgbfix)

## Run / build / publish

F5 builds GameBoyGarden.gb and runs it in mGBA / Mesen. D-pad walks, A plants, Start clears.

Language / project type: `retro-gameboy`. Files: `gb.inc`, `main.asm`, `project.radproj`, `tiles.inc`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the emulator hooks (Mesen 2 headless frames, VICE monitor, Stella window)).

---

<div dir="rtl">

## زارع الحديقة (جيم بوي)

حرّك البستاني واضغط A لزراعة الزهور على العشب؛ العداد يستخدم DAA؛ و Start يمسح الحديقة.

### ماذا يعرض

* رأس الخرطوشة يملؤه rgbfix، وإطفاء الشاشة وتشغيلها في vblank فقط
* خريطة خلفية تُبنى بالكود (سياج وممر وعشب) والكتابة فيها أثناء vblank
* مجموعتا أزرار التحكم مع اكتشاف الضغطة؛ و`daa` لنظام BCD
* بلاطات أصلية في `tiles.inc`؛ و RGBDS (rgbasm و rgblink و rgbfix)

### التشغيل والبناء والنشر

F5 يبني GameBoyGarden.gb ويشغله في mGBA أو Mesen. الأسهم للمشي، A للزراعة، Start للمسح.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
