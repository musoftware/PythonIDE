<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# Ring Pong (RingRayLib game)

Pong made with the scene designer and RingRayLib: keyboard paddle, AI paddle, score, timer.

## What it shows

- Scene designer file `Court.scene` (shape sprites + text objects in a UI layer)
- `keyboard_move` behaviour (Up/Down or W/S) for the player paddle
- `Scene_Update dt`: own ball physics, paddle collisions with spin, simple computer player
- `Scene_KeyDown`, `ShowMessage`, `AddTimer` / `ServeTimer_Tick` / `StopTimer`
- Test hooks: RADGAME_FRAMES / RADGAME_KEYS / RADGAME_SCREENSHOT

**Language / project type:** `ring-game`

## Run

F5 runs main.ring with RingRayLib (ships with Ring). Up/Down to play, R restarts, Esc quits.

## Publish

Build > Publish (ring2exe) makes `RingPong.exe` with the raylib runtime.

<div dir="rtl">

# لعبة بونج بـ Ring

لعبة بونج بمصمم المشاهد و RingRayLib: مضرب بلوحة المفاتيح ومضرب آلي ونقاط ومؤقت.

## ماذا يوضح

- ملف المشهد Court.scene من مصمم المشاهد
- سلوك الحركة بلوحة المفاتيح للمضرب
- فيزياء الكرة والاصطدام ولاعب آلي في Scene_Update
- أحداث المفاتيح والرسائل والمؤقتات
- متغيرات الاختبار RADGAME_*

## التشغيل

اضغط F5. الأسهم للعب و R لإعادة البدء و Esc للخروج.

## النشر

من القائمة Build > Publish لإنشاء ملف تنفيذي (انظر جدول النتائج).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License. Tested by `samples/Tests/Examples/test_examples_scripting.py --group ring`.
