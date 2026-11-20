// Level1 - your game code (JavaScript). Double-click an object in the scene designer to add its
// event handler. Every object of the scene is a global by its name (Player.x, Coin1.visible,
// ScoreText.text). Helpers: game.score, game.lives, game.vars, GoToScene(name), RestartScene(),
// PlaySound(id), ShowMessage(text, seconds), AddScore(n), IsKeyDown("left"), Find(name),
// FindGroup("Coin"), Clone(obj, x, y), AddTimer(name, ms), Random(a, b), Quit().

// the scene: the scene starts
function Scene_Load() {
    game.vars.start_score = game.score;       // score when the level started
    ShowMessage(game.vars.message || "Collect the coins and reach the flag!", 2);
    delete game.vars.message;
}

// the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
function Scene_KeyDown(key) {
    if (key === "escape") {
        Quit();
    } else if (key === "r") {
        RestartScene();
    }
}

// Player: jumps (platformer)
function Player_Jump() {
    PlaySound("jump");
}

// Player: touches another object (other)
function Player_Collide(other) {
    if (other.group === "Enemy") {
        if (Player.vy > 0 && Player.bottom - other.y < 14) {   // landed on its head: stomp
            other.destroy();
            Player.vy = -320;
            AddScore(5);
        } else {
            LoseLife();
        }
    } else if (other.name === "Goal") {
        ShowMessage("You win! Score: " + game.score, 3);
        Player.behaviours.length = 0;                  // stop the player
        AddTimer("WinTimer", 3000);
    }
}

// Player: fell below the level
function Player_OutOfWorld() {
    LoseLife();
}

// WinTimer: the timer interval elapsed
function WinTimer_Tick() {
    game.score = 0;
    game.lives = 3;
    RestartScene();
}

// back to the start of the level with one life less (and the score it started with)
function LoseLife() {
    game.lives -= 1;
    game.score = game.vars.start_score || 0;
    if (game.lives <= 0) {
        game.vars.message = "Game over - try again!";
        game.lives = 3;
        game.score = 0;
    }
    RestartScene();
}

// Player: is clicked
function Player_Click() {

}
