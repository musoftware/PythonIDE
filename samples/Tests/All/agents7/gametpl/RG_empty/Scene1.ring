# Scene1 - your game code (Ring). Double-click an object in the scene designer to add its handler.
# Every object of the scene is a global by its name (Player.x, Coin1.visible, ScoreText.text).
# Helpers: game.score, game.lives, AddScore(n), RestartScene(), GoToScene(name), Quit(),
# ShowMessage(text, seconds), PlayGameSound(id), IsKeyHeld("left"), FindObject(name), FindGroup(group),
# AddTimer(name, ms), StopTimer(name). Object methods: destroy() show() hide() right() bottom() play(anim).

# the scene: the scene starts
func Scene_Load


# the scene: every frame (dt = seconds since the last frame)
func Scene_Update dt


# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
func Scene_KeyDown key

