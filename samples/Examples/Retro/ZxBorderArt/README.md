# Border & Attribute Art (ZX Spectrum)

Moving rainbow stripes made only of colour attributes, border bands after HALT, keys 1-4 change the width, P pauses, Space returns to BASIC.

## What it shows

* attribute memory (22528, PAPER / INK / BRIGHT), port $FE border colour
* reading the keyboard half-rows with `in a, (c)`, key-down edge for P
* ROM calls (CLS, channel 2, RST $10 with AT codes)
* sjasmplus + a .tap with a BASIC loader made by the IDE

## Run / build / publish

F5 builds ZxBorderArt.tap; it runs in the ZX emulator named by RADIDE_ZX_EMULATOR (Fuse / ZEsarUX) - the IDE's emulator catalog has no ZX Spectrum emulator yet.

Language / project type: `retro-zx`. Files: `main.asm`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run ((.tap format check; no ZX emulator in the IDE)).

---

<div dir="rtl">

## فن الإطار والسمات (ZX Spectrum)

خطوط قوس قزح متحركة مصنوعة من سمات الألوان فقط، وأشرطة في الإطار بعد HALT، والمفاتيح 1-4 تغير العرض، و P إيقاف مؤقت، والمسافة للرجوع إلى BASIC.

### ماذا يعرض

* ذاكرة السمات (22528 و PAPER و INK و BRIGHT) ولون الإطار عبر المنفذ $FE
* قراءة صفوف لوحة المفاتيح بـ `in a, (c)` واكتشاف ضغطة P
* استدعاءات ROM (CLS والقناة 2 و RST $10 مع رموز AT)
* sjasmplus وملف .tap مع محمّل BASIC تصنعه البيئة

### التشغيل والبناء والنشر

F5 يبني ZxBorderArt.tap؛ ويعمل في محاكي ZX المحدد في RADIDE_ZX_EMULATOR (Fuse أو ZEsarUX) - كتالوج المحاكيات في البيئة لا يحتوي محاكي ZX Spectrum بعد.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
