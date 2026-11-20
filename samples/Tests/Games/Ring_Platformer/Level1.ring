# Level1 - your game code (Ring). Double-click an object in the scene designer to add its handler.
# Every object of the scene is a global by its name (Player.x, Coin1.visible, ScoreText.text).
# Helpers: game.score, game.lives, AddScore(n), RestartScene(), GoToScene(name), Quit(),
# ShowMessage(text, seconds), PlayGameSound(id), IsKeyHeld("left"), FindObject(name), FindGroup(group),
# AddTimer(name, ms), StopTimer(name). Object methods: destroy() show() hide() right() bottom() play(anim).

StartScore = 0
NextMessage = "Collect the coins and reach the flag!"

# the scene: the scene starts
func Scene_Load
    StartScore = game.score          # score when the level started
    ShowMessage(NextMessage, 2)
    NextMessage = "Collect the coins and reach the flag!"

# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
func Scene_KeyDown key
    if key = "escape"
        Quit()
    but key = "r"
        RestartScene()
    ok

# Player: jumps (platformer)
func Player_Jump
    PlayGameSound("jump")

# Player: touches another object (other)
func Player_Collide oOther
    if oOther.group = "Enemy"
        if Player.vy > 0 and Player.bottom() - oOther.y < 14     # landed on its head: stomp
            oOther.destroy()
            Player.vy = -320
            AddScore(5)
        else
            LoseLife()
        ok
    but oOther.name = "Goal"
        ShowMessage("You win! Score: " + game.score, 3)
        Player.clear_behaviours()                  # stop the player
        AddTimer("WinTimer", 3000)
    ok

# Player: fell below the level
func Player_OutOfWorld
    LoseLife()

# WinTimer: the timer interval elapsed
func WinTimer_Tick
    StopTimer("WinTimer")
    game.score = 0
    game.lives = 3
    RestartScene()

# back to the start of the level with one life less (and the score it started with)
func LoseLife
    game.lives -= 1
    game.score = StartScore
    if game.lives <= 0
        NextMessage = "Game over - try again!"
        game.lives = 3
        game.score = 0
    ok
    RestartScene()
