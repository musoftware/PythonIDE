"""New Project > Games templates: Platformer, Top-down, Empty pygame game and Godot 2D.

``create_game_project(folder, name, plugin_id, template)`` writes a complete, runnable project
(scene + art + code + runtime) and returns the radide.model.Project.  ``platformer_scene`` builds
the level of samples/HelloGame.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..model import Project
from . import art, codegen


@dataclass
class GameTemplate:
    id: str
    title: str
    description: str
    plugins: tuple[str, ...]
    icon: str = "SP_MediaPlay"


TEMPLATES = [
    GameTemplate("platformer", "Platformer",
                 "A side-scrolling level: tile map with collision, an animated player that runs and jumps, "
                 "coins with a score, an enemy that patrols and a goal flag. F5 plays it.", ("pygame", "godot")),
    GameTemplate("topdown", "Top-down Game",
                 "A room seen from above: the hero walks in 4 directions with walk animations, collects gems "
                 "and avoids a patrolling enemy; walls block the way.", ("pygame", "godot")),
    GameTemplate("empty", "Empty Game",
                 "One empty scene (800x600) with a sprites layer and a UI layer - draw your own game.",
                 ("pygame", "godot")),
]


def templates_for(plugin_id: str) -> list[GameTemplate]:
    return [t for t in TEMPLATES if plugin_id in t.plugins]


# ====================================================================== level helpers
def _tiles_from_map(rows: list[str], legend: dict[str, int], width: int) -> list[list[int]]:
    return [[legend.get(ch, -1) for ch in row.ljust(width, ".")[:width]] for row in rows]


def _obj(name: str, kind: str = "sprite", x: float = 0, y: float = 0, w: float = 32, h: float = 32, **kw) -> dict:
    d = {"name": name, "kind": kind, "x": x, "y": y, "w": w, "h": h, "scale": 1, "rotation": 0, "z": kw.pop("z", 0),
         "visible": kw.pop("visible", True)}
    d.update({k: v for k, v in kw.items() if k not in ("behaviours", "props")})
    d["behaviours"] = kw.get("behaviours", [])
    d["props"] = kw.get("props", {})
    return d


PLATFORMER_MAP = [
    "............................................................",
    "............................................................",
    "............................................................",
    "..............................c.c.c.........................",
    ".............................BBBBBBB........................",
    "...........c.c......................................cc......",
    "..........BBBBB.................?...?..............BBBB.....",
    "......................c.c...............e.c.c.c.............",
    "...................?B?..BBBBBB..........BBBBBBBB............",
    ".................................................BBB..........",
    "....c.c.c.............................................c.c...",
    "..........................................................F.",
    ".P.............e...................e........................",
    "GGGGGGGGGGGGGGGGGGGGGGGG...GGGGGGGGGGGGGGGGG...GGGGGGGGGGGGGG",
    "DDDDDDDDDDDDDDDDDDDDDDDD...DDDDDDDDDDDDDDDDD...DDDDDDDDDDDDDD",
]


def platformer_scene(name: str = "Level1", assets: dict | None = None, title: str = "") -> dict:
    """The platformer level (60x15 tiles of 32 px, window 800x480, camera follows the player)."""
    cols = 60
    tiles = _tiles_from_map(PLATFORMER_MAP, {"G": art.GRASS, "D": art.DIRT, "B": art.BRICK, "?": art.BLOCK}, cols)
    sprites, coin_n, enemy_n = [], 0, 0
    player = None
    for r, row in enumerate(PLATFORMER_MAP):
        for c, ch in enumerate(row):
            x, y = c * 32, r * 32
            if ch == "c":
                coin_n += 1
                sprites.append(_obj(f"Coin{coin_n}", x=x + 4, y=y + 4, w=24, h=24, spritesheet="coin",
                                    animation="spin", behaviours=[{"type": "collectible", "score": 1,
                                                                   "sound": "coin"}]))
            elif ch == "e":
                enemy_n += 1
                sprites.append(_obj(f"Enemy{enemy_n}", x=x, y=y, spritesheet="enemy", animation="walk",
                                    behaviours=[{"type": "enemy_patrol", "speed": 70, "distance": 128,
                                                 "axis": "x"}]))
            elif ch == "F":
                sprites.append(_obj("Goal", x=x, y=y, w=32, h=64, image="flag", z=-1))
            elif ch == "P":
                player = _obj("Player", x=x, y=y, w=32, h=32, spritesheet="player", animation="idle", z=5,
                              behaviours=[{"type": "platformer", "speed": 220, "jump": 560}])
    sprites.append(player)
    clouds = [_obj(f"Cloud{i + 1}", x=x, y=y, w=96, h=40, image="cloud", z=-5)
              for i, (x, y) in enumerate(((60, 40), (420, 80), (900, 30), (1350, 70), (1700, 40)))]
    ui = [_obj("ScoreText", "text", 16, 10, 0, 0, text="Score: {score}", props={"FontSize": 26,
                                                                                "ForeColor": "#FFFFFF"}),
          _obj("LivesText", "text", 16, 42, 0, 0, text="Lives: {lives}", props={"FontSize": 22,
                                                                                "ForeColor": "#FFF3B0"}),
          _obj("HelpText", "text", 450, 12, 334, 24, text=title or "Arrows move - Space jumps - R restarts",
               props={"FontSize": 18, "ForeColor": "#FFFFFF", "Align": "right"})]
    return {"name": name, "width": 800, "height": 480, "background": "#6EC1E4", "fps": 60, "gravity": 900,
            "camera": {"follow": "Player"},
            "assets": assets or {},
            "layers": [{"name": "Background", "type": "sprites", "tileset": "", "data": [], "collision": False,
                        "objects": clouds},
                       {"name": "Ground", "type": "tiles", "tileset": "tiles", "data": tiles, "collision": True,
                        "objects": []},
                       {"name": "Sprites", "type": "sprites", "tileset": "", "data": [], "collision": False,
                        "objects": sprites},
                       {"name": "UI", "type": "ui", "tileset": "", "data": [], "collision": False, "objects": ui}]}


PLATFORMER_CODE = {
    "Scene_Load": ['game.vars["start_score"] = game.score       # score when the level started',
                   'ShowMessage(game.vars.pop("message", "Collect the coins and reach the flag!"), 2)'],
    "Scene_KeyDown": ['if key == "escape":', '    Quit()', 'elif key == "r":', '    RestartScene()'],
    "Player_Jump": ['PlaySound("jump")'],
    "Player_Collide": ['if other.group == "Enemy":',
                       '    if Player.vy > 0 and Player.bottom - other.y < 14:   # landed on its head: stomp',
                       '        other.destroy()',
                       '        Player.vy = -320',
                       '        AddScore(5)',
                       '    else:',
                       '        LoseLife()',
                       'elif other.name == "Goal":',
                       '    ShowMessage(f"You win! Score: {game.score}", 3)',
                       '    Player.behaviours.clear()                     # stop the player',
                       '    AddTimer("WinTimer", 3000)'],
    "Player_OutOfWorld": ["LoseLife()"],
    "WinTimer_Tick": ['game.score = 0', 'game.lives = 3', 'RestartScene()'],
}

LOSE_LIFE = '''

def LoseLife():
    """Back to the start of the level with one life less (and the score it started with)."""
    game.lives -= 1
    game.score = game.vars.get("start_score", 0)
    if game.lives <= 0:
        game.vars["message"] = "Game over - try again!"
        game.lives = 3
        game.score = 0
    RestartScene()
'''


def platformer_code(name: str) -> str:
    handlers = [(None, "Load"), (None, "KeyDown"), ("Player", "Jump"), ("Player", "Collide"),
                ("Player", "OutOfWorld"), ("WinTimer", "Tick")]
    code = codegen.new_scene_code({"name": name}, handlers, PLATFORMER_CODE)
    return code + LOSE_LIFE


TOPDOWN_MAP = [
    "SSSSSSSSSSSSSSSSSSSSSSSSS",
    "S.......................S",
    "S..g.......g........g...S",
    "S.......................S",
    "S....SSSS.......SSSS....S",
    "S....S..............g...S",
    "S.g..S.....e............S",
    "S....S..........S.......S",
    "S...............S...g...S",
    "S..........H....S.......S",
    "S.......................S",
    "S..g......SSSSSS.....g..S",
    "S.......................S",
    "S.................e.....S",
    "SSSSSSSSSSSSSSSSSSSSSSSSS",
]


def topdown_scene(name: str = "Room1", assets: dict | None = None) -> dict:
    cols = 25
    floor = _tiles_from_map(["".join("F" for _ in range(cols))] * len(TOPDOWN_MAP), {"F": art.FLOOR}, cols)
    walls = _tiles_from_map(TOPDOWN_MAP, {"S": art.STONE}, cols)
    sprites, gn, en = [], 0, 0
    for r, row in enumerate(TOPDOWN_MAP):
        for c, ch in enumerate(row):
            x, y = c * 32, r * 32
            if ch == "g":
                gn += 1
                sprites.append(_obj(f"Gem{gn}", x=x + 6, y=y + 6, w=20, h=20, image="gem",
                                    behaviours=[{"type": "collectible", "score": 10, "sound": "pickup"}]))
            elif ch == "e":
                en += 1
                sprites.append(_obj(f"Enemy{en}", x=x, y=y, spritesheet="enemy", animation="walk",
                                    behaviours=[{"type": "enemy_patrol", "speed": 90, "distance": 160,
                                                 "axis": "y" if en % 2 else "x", "gravity": False}]))
            elif ch == "H":
                sprites.append(_obj("Hero", x=x + 2, y=y + 2, w=28, h=28, spritesheet="hero",
                                    animation="idle_down", z=5,
                                    behaviours=[{"type": "top_down", "speed": 180, "rotate": False}]))
    ui = [_obj("ScoreText", "text", 40, 6, 0, 0, text="Gems: {score}", props={"FontSize": 22,
                                                                              "ForeColor": "#FFFFFF"})]
    return {"name": name, "width": 800, "height": 480, "background": "#202830", "fps": 60, "gravity": 0,
            "camera": {"follow": "Hero"},
            "assets": assets or {},
            "layers": [{"name": "Floor", "type": "tiles", "tileset": "tiles", "data": floor, "collision": False,
                        "objects": []},
                       {"name": "Walls", "type": "tiles", "tileset": "tiles", "data": walls, "collision": True,
                        "objects": []},
                       {"name": "Sprites", "type": "sprites", "tileset": "", "data": [], "collision": False,
                        "objects": sprites},
                       {"name": "UI", "type": "ui", "tileset": "", "data": [], "collision": False, "objects": ui}]}


TOPDOWN_CODE = {
    "Scene_Load": ['ShowMessage("Collect all the gems!", 2)'],
    "Scene_KeyDown": ['if key == "escape":', '    Quit()'],
    "Hero_Collide": ['if other.group == "Enemy":',
                     '    game.score = 0',
                     '    RestartScene()',
                     'elif not FindGroup("Gem"):',
                     '    ShowMessage("All gems collected!", 3)'],
}


def topdown_code(name: str) -> str:
    return codegen.new_scene_code({"name": name}, [(None, "Load"), (None, "KeyDown"), ("Hero", "Collide")],
                                  TOPDOWN_CODE)


def empty_scene(name: str = "Scene1") -> dict:
    return {"name": name, "width": 800, "height": 600, "background": "#6EC1E4", "fps": 60, "gravity": 900,
            "camera": {"follow": None},
            "assets": {"images": {}, "sounds": {}, "spritesheets": {}, "tilesets": {}},
            "layers": [{"name": "Sprites", "type": "sprites", "tileset": "", "data": [], "collision": False,
                        "objects": []},
                       {"name": "UI", "type": "ui", "tileset": "", "data": [], "collision": False, "objects": []}]}


# ====================================================================== projects
def write_scene(folder: Path, scene: dict) -> Path:
    import json
    p = Path(folder) / f"{scene['name']}.scene"
    p.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
    return p


def build_game_files(folder: Path, name: str, template: str = "platformer") -> tuple[str, list[str]]:
    """Scene(s), art and the pygame code of a template. Returns (first scene, scene names)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if template == "platformer":
        scene = platformer_scene("Level1", art.write_platformer_assets(folder))
        code = platformer_code("Level1")
    elif template == "topdown":
        scene = topdown_scene("Room1", art.write_topdown_assets(folder))
        code = topdown_code("Room1")
    elif template == "empty":
        scene = empty_scene("Scene1")
        code = codegen.new_scene_code(scene)
    else:
        raise ValueError(f"unknown game template {template!r}")
    write_scene(folder, scene)
    (folder / f"{scene['name']}.py").write_text(code, encoding="utf-8")
    return scene["name"], [scene["name"]]


def create_game_project(folder: Path, name: str, plugin_id: str = "pygame", template: str = "platformer",
                        title: str = "") -> Project:
    """A new game project (plugin "pygame" or "godot") made from *template*."""
    folder = Path(folder)
    first, scenes = build_game_files(folder, name, template)
    extra = {"scenes": scenes, "game": {"title": title or name, "start_scene": first}}
    if plugin_id == "godot":
        from . import godot_export
        for s in scenes:
            (folder / f"{s}.py").unlink(missing_ok=True)
        godot_export.write_user_scripts(folder, scenes, template)
        project = Project(folder, name, "godot", [], first, [f"{s}.gd" for s in scenes], extra=extra)
        project.save()
        godot_export.export_project(folder, title or name)
        return project
    (folder / "main.py").write_text(codegen.main_code(first, title or name), encoding="utf-8")
    codegen.sync_project(folder)
    project = Project(folder, name, "pygame", [], "main", ["main.py"] + [f"{s}.py" for s in scenes], extra=extra)
    project.save()
    (folder / "requirements.txt").write_text("pygame-ce>=2.4\n", encoding="utf-8")
    return project


__all__ = ["GameTemplate", "TEMPLATES", "templates_for", "platformer_scene", "topdown_scene", "empty_scene",
           "platformer_code", "topdown_code", "build_game_files", "create_game_project", "write_scene"]
