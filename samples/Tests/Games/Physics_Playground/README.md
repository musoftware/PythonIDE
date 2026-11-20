# Physics_Playground

**pygame + pymunk physics** - tests the optional physics mode of radgame (round 6).

What is in the scene (open `Scene1.scene` in the scene designer and look at the inspector):
- Scene inspector > **Physics (pymunk)**: physics on, gravity 0 / 900, collision tile layers are walls,
  **joints**: a *pivot* (the blue plank is a seesaw turning around a world point) and a *pin* (the red bob
  hangs from the `Anchor` area like a pendulum).
- Object inspector > **Physics body**: crates = dynamic boxes, the ball = dynamic circle (elasticity 0.8),
  the yellow wedge = static *poly* (its outline came from **Outline from picture**), the green lift =
  kinematic (moved by `Scene_Update` with `Lift.y = ...`), `CrateTemplate` = a hidden spawn template with
  a dynamic body.
- The ground is a 16-tile auto-tiled terrain ("dirt") on a collision layer.
- Code: click drops a crate (`Spawn` + `Burst("dust", x, y)`), Space kicks the ball with
  `ApplyImpulse(Ball, 120, -520)`, R restarts.

**Try it:** F5 (needs `pip install pymunk pygame-ce`). Headless check:
`set SDL_VIDEODRIVER=dummy & set RADGAME_FRAMES=150 & set RADGAME_SCREENSHOT=shot.png & python main.py`.
Game > **Export to Godot** builds RigidBody2D / StaticBody2D / AnimatableBody2D bodies and joints from the
same settings (Godot's own physics: similar, not identical - spring stiffness is mapped approximately).
