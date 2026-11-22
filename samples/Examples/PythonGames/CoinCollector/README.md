# CoinCollector - Coin Collector (arcade)

**Language / project type:** `python-arcade` (created with File > New Project, then customised)

arcade.Window game: collect coins, dodge meteors, countdown, pause, high score file.

## What it shows
- arcade.Window: on_draw / on_update / on_key_press / on_key_release
- SpriteList + SpriteCircle (no image files), check_for_collision_with_list
- Countdown timer, difficulty that grows, P = pause, R = restart
- highscore.txt next to main.py; RAD IDE test hooks RADGAME_FRAMES / RADGAME_KEYS

## Run
Open the folder, F5. Arrow keys / WASD move, P pauses, Esc quits.

## Publish
Build > Publish: PyInstaller program folder (~72 MB, Python inside).

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py PythonGames/CoinCollector` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# جامع العملات (arcade)

لعبة بمكتبة arcade: اجمع العملات وتجنب النيازك مع عدّ تنازلي وإيقاف مؤقت وحفظ أعلى نتيجة.

## ماذا يوضح
- نافذة arcade مع دوال الرسم والتحديث ولوحة المفاتيح
- قوائم كائنات وتصادمات بدون صور
- مؤقت وصعوبة متزايدة وإيقاف مؤقت
- ملف أعلى نتيجة

## التشغيل
افتح المجلد واضغط F5. الأسهم للحركة وP للإيقاف المؤقت.

## النشر
Build > Publish: PyInstaller program folder (~72 MB, Python inside).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
