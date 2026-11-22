# Desert Runner (Atari 2600)

A tiny endless runner: jump over cacti with fire, gravity with a signed velocity, playfield score bar, hardware collision flashes the sky.

## What it shows

* an NTSC frame kernel (VSYNC / VBLANK timer / 192 lines / overscan) split into three loops
* two players positioned with SetHorizPos + HMOVE
* CXPPMM collision latch and CXCLR, PF1/PF2 bit order for a score bar
* DASM build; F5 runs it in Stella

## Run / build / publish

F5 builds Atari2600Runner.bin with DASM and runs it in Stella (Tools > Retro > Emulators downloads it). Fire (Space in Stella) jumps.

Language / project type: `retro-atari2600`. Files: `atari2600.h`, `main.asm`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the emulator hooks (Mesen 2 headless frames, VICE monitor, Stella window)).

---

<div dir="rtl">

## العدّاء في الصحراء (أتاري 2600)

لعبة جري لا تنتهي: اقفز فوق الصبار بزر الإطلاق، جاذبية بسرعة لها إشارة، شريط نقاط من الـ playfield، والتصادم العتادي يومض السماء.

### ماذا يعرض

* نواة إطار NTSC (VSYNC ومؤقت VBLANK و192 سطرا و overscan) مقسمة إلى ثلاث حلقات
* لاعبان يوضعان بـ SetHorizPos و HMOVE
* مزلاج التصادم CXPPMM و CXCLR وترتيب بتات PF1/PF2 لشريط النقاط
* البناء بـ DASM؛ و F5 يشغله في Stella

### التشغيل والبناء والنشر

F5 يبني Atari2600Runner.bin بـ DASM ويشغله في Stella (أدوات > ريترو > المحاكيات تنزّله). زر الإطلاق (المسافة في Stella) للقفز.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
