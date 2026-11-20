"""Scene1 - AutoTile Island: the island (47-tile blob terrain "grass") and the walls (16-tile terrain
"wall", a collision layer) were painted with the terrain brush of the Tiles tab - only "grass" / "wall" was
chosen, every edge and corner tile was picked automatically. B builds a wall block at run time."""
from radgame import *  # noqa: F401,F403 - the game helpers
from Scene1_designer import *  # noqa: F401,F403 - the objects of the scene

WALL_FULL = 15          # the 16-tile layout: tile = neighbour mask (N 1 + E 2 + S 4 + W 8)


def Scene_KeyDown(key):
    if key == "b":
        col, row = int((Hero.x + Hero.width / 2) // 32), int((Hero.y + Hero.height + 16) // 32)
        SetTile("Walls", col, row, WALL_FULL)
    elif key == "escape":
        Quit()
