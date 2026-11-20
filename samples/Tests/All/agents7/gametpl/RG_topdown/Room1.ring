# Room1 - your game code (Ring). Double-click an object in the scene designer to add its handler.
# Every object of the scene is a global by its name (Player.x, Coin1.visible, ScoreText.text).
# Helpers: game.score, game.lives, AddScore(n), RestartScene(), GoToScene(name), Quit(),
# ShowMessage(text, seconds), PlayGameSound(id), IsKeyHeld("left"), FindObject(name), FindGroup(group),
# AddTimer(name, ms), StopTimer(name). Object methods: destroy() show() hide() right() bottom() play(anim).

# the scene: the scene starts
func Scene_Load
    ShowMessage("Collect all the gems!", 2)

# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
func Scene_KeyDown key
    if key = "escape" Quit() ok

# Hero: touches another object (other)
func Hero_Collide oOther
    if oOther.group = "Enemy"
        game.score = 0
        RestartScene()
    but len(FindGroup("Gem")) = 0
        ShowMessage("All gems collected!", 3)
    ok
