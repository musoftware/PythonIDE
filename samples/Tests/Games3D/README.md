# 3D games (round 7)

Two projects made with **File > New Project > Games**:

| Folder | Template | Engine |
| --- | --- | --- |
| `Ursina_Playground` | Python 3D (Ursina) > Ursina 3D Playground | Ursina 8.3 (`pip install ursina`, in the IDE's .venv) |
| `Godot3D_Playground` | Godot 3D (GDScript) > Godot 3D Playground | Godot 4.2.2 |

**What they show:** a 3D scene file `Scene1.scene3d` (ground, sun, camera, a capsule player, crates, spinning
coins). Open it from the Solution Explorer: the **3D scene view** opens (Hierarchy list, wireframe viewport,
inspector with Position / Rotation / Scale / Colour / Behaviours). Saving regenerates `Scene1_designer.py`
(Ursina) or `Scene1.tscn` (Godot). Your code goes in `main.py` / `Scene1.gd` (VB-style handlers
`Scene_Load`, `Scene_Update`, `Player_Collect`).

**Try it:** open the folder (`project.radproj`) in RAD IDE, double-click `Scene1.scene3d`, move an entity
(drag it in the viewport or type in the inspector), press **F5**. WASD / arrows move the player, Space jumps;
touch the coins.

**Headless check (what the tests ran):**

```
cd Ursina_Playground
set RAD3D_HEADLESS=1 & set RAD3D_FRAMES=150 & set RAD3D_KEYS=w:5-120
..\..\..\..\.venv\Scripts\python.exe main.py
  -> Collected Coin4 - score 1 / rad3d-test: 150 frames score=1 player=(0.00,1.00,9.58)

cd Godot3D_Playground
set RAD3D_FRAMES=150 & set RAD3D_KEYS=w:5-120
godot --headless --fixed-fps 60 --path .
  -> Collected Coin4 - score 1 / rad3d-test: 150 frames score=1 player=(0.00,1.00,-9.58)
```

(Godot uses right-handed axes, so Z is mirrored; the scene file uses Ursina's axes.)
