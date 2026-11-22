# CrystalMaze3D - Crystal Maze 3D (Ursina)

**Language / project type:** `python-ursina` (created with File > New Project, then customised)

3D maze from the 3D scene view: solid walls, spinning collectible crystals, exit pad, HUD.

## What it shows
- Maze.scene3d edited in the IDE's 3D scene view (Maze_designer.py is generated)
- Behaviours: player, solid, collectible, spin
- Handlers: Scene_Load, Scene_Update(dt), Player_Collect(item); ursina Text HUD; win condition

## Run
Open the folder, F5. WASD / arrows move, Space jumps. Collect 4 crystals, then step on the red pad.

## Publish
Build > Publish: PyInstaller folder (~109 MB, Python + Panda3D inside).

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py PythonGames/CrystalMaze3D` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# متاهة الكريستال ثلاثية الأبعاد (Ursina)

متاهة ثلاثية الأبعاد من عارض المشاهد ثلاثية الأبعاد: جدران صلبة وكريستال يدور ومنصة خروج.

## ماذا يوضح
- مشهد ثلاثي الأبعاد يُحرَّر في عارض المشاهد
- سلوكيات اللاعب والجدار والجمع والدوران
- معالجات الأحداث وشاشة المعلومات وشرط الفوز

## التشغيل
افتح المجلد واضغط F5. اجمع 4 كريستالات ثم قف على المنصة الحمراء.

## النشر
Build > Publish: PyInstaller folder (~109 MB, Python + Panda3D inside).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
