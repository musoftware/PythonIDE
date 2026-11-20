// Room1 - your game code (JavaScript). Double-click an object in the scene designer to add its
// event handler. Every object of the scene is a global by its name (Player.x, Coin1.visible,
// ScoreText.text). Helpers: game.score, game.lives, game.vars, GoToScene(name), RestartScene(),
// PlaySound(id), ShowMessage(text, seconds), AddScore(n), IsKeyDown("left"), Find(name),
// FindGroup("Coin"), Clone(obj, x, y), AddTimer(name, ms), Random(a, b), Quit().

// the scene: the scene starts
function Scene_Load() {
    ShowMessage("Collect all the gems!", 2);
}

// the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
function Scene_KeyDown(key) {
    if (key === "escape") Quit();
}

// Hero: touches another object (other)
function Hero_Collide(other) {
    if (other.group === "Enemy") {
        game.score = 0;
        RestartScene();
    } else if (FindGroup("Gem").length === 0) {
        ShowMessage("All gems collected!", 3);
    }
}
