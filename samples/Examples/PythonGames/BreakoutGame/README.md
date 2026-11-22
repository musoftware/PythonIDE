# BreakoutGame - Breakout (pygame)

**Language / project type:** `pygame` (created with File > New Project, then customised)

Paddle, ball and 50 bricks drawn from a scene; score, lives, saved best score.

## What it shows
- Scene designer project (Arena.scene): sprites with colours, UI text objects with {score} / {lives} / {best}
- VB-style handlers in Arena.py: Scene_Load, Scene_Update(dt), Scene_KeyDown(key)
- Keyboard (IsKeyDown), collisions (obj.overlaps), destroy(), FindGroup("Brick"), AddScore, ShowMessage, RestartScene
- SaveData / LoadData (best score in savegame.json)

## Run
Open the folder (File > Open Project), double-click Arena.scene to see the level, press F5. Left/Right move, Space launches the ball.

## Publish
Build > Publish: a PyInstaller program folder (~64 MB, Python inside).

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py PythonGames/BreakoutGame` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# لعبة تكسير الطوب (pygame)

مضرب وكرة و50 طوبة مرسومة في مصمم المشاهد؛ نقاط وأرواح وحفظ أعلى نتيجة.

## ماذا يوضح
- مشروع بمصمم المشاهد: كائنات ملوّنة ونصوص تعرض النقاط والأرواح
- معالجات أحداث على طريقة VB في Arena.py
- لوحة المفاتيح والتصادم وحذف الكائنات وإضافة النقاط والرسائل
- حفظ أعلى نتيجة SaveData / LoadData

## التشغيل
افتح المجلد (File > Open Project) وافتح Arena.scene لرؤية المرحلة ثم اضغط F5. الأسهم للتحريك والمسافة لإطلاق الكرة.

## النشر
Build > Publish: a PyInstaller program folder (~64 MB, Python inside).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
