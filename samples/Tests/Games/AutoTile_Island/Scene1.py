"""Scene1 - AutoTile Island: the island (47-tile blob terrain "grass") and the walls (16-tile terrain
"wall", a collision layer) were painted with the terrain brush of the Tiles tab - only "grass" / "wall" was
chosen, every edge and corner tile was picked automatically. B / N add / remove wall blocks at run time (SetTerrain auto-tiles them too)."""
from radgame import *  # noqa: F401,F403 - the game helpers
from Scene1_designer import *  # noqa: F401,F403 - the objects of the scene



def Scene_KeyDown(key):
    col, row = int((Hero.x + Hero.width / 2) // 32), int((Hero.y + Hero.height + 16) // 32)
    if key == "b":                        # a wall block below the hero: its neighbours re-tile too
        SetTerrain("Walls", col, row, "wall")
    elif key == "n":
        SetTerrain("Walls", col, row, "wall", False)
    elif key == "escape":
        Quit()
