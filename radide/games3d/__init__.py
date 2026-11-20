"""3D games (round 7): Ursina (Python) and Godot 3D projects with a small 3D scene designer.

* ``model.py``      - the ``<Scene>.scene3d`` JSON file (entities with transforms, colours, behaviours)
* ``ursina_gen.py`` - .scene3d -> ``<Scene>_designer.py`` for Ursina + the user ``main.py``
* ``godot_gen.py``  - .scene3d -> ``<Scene>.tscn`` (Node3D, Camera3D, lights, meshes, CharacterBody3D player)
* ``templates.py``  - New Project > Games > "Python 3D (Ursina)" / "Godot 3D"
* ``editor.py``     - the 3D scene view tab (entity list, wireframe viewport, inspector)
* ``ide.py``        - opens ``.scene3d`` files in the editor (installed by radide/features/games3d.py)
"""
