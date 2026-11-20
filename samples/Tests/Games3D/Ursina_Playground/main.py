"""Ursina_Playground - a 3D game made with Ursina (https://www.ursinaengine.org, MIT licence) in RAD IDE.

The scene (Scene1.scene3d) is edited in the IDE's 3D scene view; Scene1_designer.py is generated from it.
Write your game code here - VB-style handlers are called by rad3d.py:
    Scene_Load()          once, before the first frame
    Scene_Update(dt)      every frame
    Player_Collect(item)  the player touched a "collectible" entity
Keys: WASD / arrows move, Space jumps.
"""
import rad3d

app = rad3d.start('Ursina_Playground')
scene = rad3d.load_scene('Scene1')


def Scene_Load():
    print("Collect the coins!", flush=True)


def Scene_Update(dt):
    pass


def Player_Collect(item):
    print(f"Collected {item.name} - score {rad3d.score}", flush=True)


rad3d.run(globals())
