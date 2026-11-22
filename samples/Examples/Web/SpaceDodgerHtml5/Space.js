// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Space - the code of the Space Dodger scene (HTML5 Canvas game, RAD IDE radgame.js runtime).
// Shows: keyboard input (IsKeyDown, Scene_KeyDown), Scene_Update(dt), cloning hidden template objects
// (Bullet, Meteor) with Clone(), a repeating timer (AddTimer + SpawnTimer_Tick), overlaps() collision tests,
// destroy(), score / lives / best in UI text ({score} {lives} {best}), the best score saved in localStorage,
// difficulty that grows with the score, and ShowMessage / RestartScene.
// Keys: Left/Right (A/D) move, Space fires, P pauses, Escape quits.

var SHIP_SPEED = 420, BULLET_SPEED = 620, BEST_KEY = "spacedodger.best";
var state = { cooldown: 0, paused: false, meteorSpeed: 160 };

function loadBest() {
    try { return parseInt(localStorage.getItem(BEST_KEY) || "0", 10) || 0; } catch (e) { return 0; }
}
function saveBest(v) {
    try { localStorage.setItem(BEST_KEY, String(v)); } catch (e) { /* storage blocked */ }
}

// the scene: the scene starts
function Scene_Load() {
    if (!game.vars.playing) { game.score = 0; game.lives = 3; }
    game.vars.playing = true;
    game.vars.best = loadBest();
    state.meteorSpeed = 160;
    AddTimer("SpawnTimer", 650, true);
    ShowMessage("Left / Right to move, Space to fire", 2);
}

// SpawnTimer: a new meteor at a random place above the screen
function SpawnTimer_Tick() {
    if (state.paused) return;
    var m = Clone(Meteor, Random(10, 754), -40);
    m.data.speed = state.meteorSpeed + Random(0, 80);
    m.data.spin = Random(-3, 3);
}

// the scene: a key goes down
function Scene_KeyDown(key) {
    if (key === "p") { state.paused = !state.paused; ShowMessage(state.paused ? "Paused" : "Go!", 1); }
    if (key === "escape") Quit();
}

function live(group) {
    return FindGroup(group).filter(function (o) { return o.visible; });   // not the hidden templates
}

// the scene: every frame (dt = seconds since the last frame)
function Scene_Update(dt) {
    if (state.paused) return;
    // ship
    if (IsKeyDown("left") || IsKeyDown("a")) Ship.x -= SHIP_SPEED * dt;
    if (IsKeyDown("right") || IsKeyDown("d")) Ship.x += SHIP_SPEED * dt;
    Ship.x = Math.max(0, Math.min(800 - Ship.width, Ship.x));
    // firing (held Space fires every 0.25 s)
    state.cooldown -= dt;
    if (IsKeyDown("space") && state.cooldown <= 0) {
        Clone(Bullet, Ship.x + Ship.width / 2 - 3, Ship.y - 14);
        state.cooldown = 0.25;
    }
    var bullets = live("Bullet"), meteors = live("Meteor");
    bullets.forEach(function (b) {
        b.y -= BULLET_SPEED * dt;
        if (b.y < -20) b.destroy();
    });
    meteors.forEach(function (m) {
        m.y += (m.data.speed || 160) * dt;
        m.rotation += (m.data.spin || 0);
        if (m.y > 620) m.destroy();
        if (m.alive && m.overlaps(Ship)) {
            m.destroy();
            game.lives -= 1;
            console.log("SHIP HIT lives=" + game.lives);
            if (game.lives <= 0) return gameOver();
            ShowMessage("Ouch! " + game.lives + " lives left", 1);
        }
        bullets.forEach(function (b) {
            if (b.alive && m.alive && b.overlaps(m)) {
                b.destroy(); m.destroy();
                AddScore(10);
                console.log("METEOR DOWN score=" + game.score);
                if (game.score % 100 === 0) { state.meteorSpeed += 40; ShowMessage("Faster!", 1); }
            }
        });
    });
}

function gameOver() {
    var best = Math.max(loadBest(), game.score);
    saveBest(best);
    console.log("GAMEOVER score=" + game.score + " best=" + best);
    ShowMessage("Game over - score " + game.score, 3);
    game.vars.playing = false;
    RestartScene();
}
