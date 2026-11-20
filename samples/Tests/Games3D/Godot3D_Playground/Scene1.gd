# Scene1.gd - your code for the 3D scene Scene1 (RAD IDE).  The scene itself is Scene1.scene3d
# (3D scene view); Scene1.tscn is generated from it.  VB-style handlers called by rad3d_scene.gd:
extends "res://rad3d/rad3d_scene.gd"


func Scene_Load():
	print("Collect the coins!")


func Scene_Update(delta):
	pass


func Player_Collect(item):
	print("Collected %s - score %d" % [item.name, score])
