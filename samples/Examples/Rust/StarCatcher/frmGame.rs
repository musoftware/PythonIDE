// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Star Catcher - an arcade game in Rust (RAD IDE GUI Bridge: module radgui; Build > Publish makes an exe).
//
// Catch the yellow stars (+10), dodge the red rocks (-1 life); every 5 stars the game gets faster.
// Shows: a Timer game loop, KeyDown / KeyUp on the form (event_arg(3) = key name), MouseMove on a Panel
// (event_arg(0) = X), moving controls with Left / Top, rectangle collision, a tiny random generator
// (xorshift - no crates needed), a best score kept in a file.
use crate::radgui::*;
use std::cell::RefCell;
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

const FIELD_W: i32 = 456;
const FIELD_H: i32 = 330;
const BEST_FILE: &str = "starcatcher.best";

#[derive(Clone, Copy)]
struct Sprite {
    x: i32,
    y: i32,
    w: i32,
    h: i32,
}

impl Sprite {
    fn hits(&self, o: &Sprite) -> bool {
        self.x < o.x + o.w && o.x < self.x + self.w && self.y < o.y + o.h && o.y < self.y + self.h
    }
}

struct Game {
    player: Sprite,
    star: Sprite,
    rock: Sprite,
    star_speed: i32,
    rock_speed: i32,
    score: i32,
    lives: i32,
    best: i32,
    left: bool,
    right: bool,
    running: bool,
    paused: bool,
    seed: u64,
}

impl Game {
    fn rand(&mut self, n: i32) -> i32 {
        // xorshift64: good enough for a game
        self.seed ^= self.seed << 13;
        self.seed ^= self.seed >> 7;
        self.seed ^= self.seed << 17;
        (self.seed % n.max(1) as u64) as i32
    }

    fn drop_star(&mut self) {
        self.star.x = self.rand(FIELD_W - self.star.w);
        self.star.y = -self.star.h;
    }

    fn drop_rock(&mut self) {
        self.rock.x = self.rand(FIELD_W - self.rock.w);
        self.rock.y = -self.rock.h - self.rand(200);
    }
}

thread_local! {
    static GAME: RefCell<Game> = RefCell::new(Game {
        player: Sprite { x: 190, y: 300, w: 76, h: 14 },
        star: Sprite { x: 100, y: -24, w: 24, h: 24 },
        rock: Sprite { x: 300, y: -24, w: 24, h: 24 },
        star_speed: 4, rock_speed: 5, score: 0, lives: 3, best: 0,
        left: false, right: false, running: false, paused: false,
        seed: SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos() as u64).unwrap_or(1) | 1,
    });
}

fn show_score(g: &Game) {
    set("lblScore", "Caption", format!("Score: {}", g.score));
    set("lblLives", "Caption", format!("Lives: {}", g.lives));
    set("lblBest", "Caption", format!("Best: {}", g.best));
}

fn message(text: &str) {
    set("lblMessage", "Caption", text);
    set("lblMessage", "Visible", if text.is_empty() { "False" } else { "True" });
}

fn game_over(g: &mut Game) {
    g.running = false;
    set("tmrGame", "Enabled", "False");
    if g.score > g.best {
        g.best = g.score;
        let _ = fs::write(BEST_FILE, g.best.to_string()); // the best score is only a bonus
        message(&format!("Game over - new best score {}!", g.score));
    } else {
        message(&format!("Game over - score {}. Press Start.", g.score));
    }
    show_score(g);
    set("btnStart", "Caption", "Start");
}

pub fn frmGame_Load() {
    GAME.with(|g| {
        let mut g = g.borrow_mut();
        g.best = fs::read_to_string(BEST_FILE).ok().and_then(|s| s.trim().parse().ok()).unwrap_or(0);
        show_score(&g);
    });
}

pub fn btnStart_Click() {
    GAME.with(|g| {
        let mut g = g.borrow_mut();
        g.score = 0;
        g.lives = 3;
        g.star_speed = 4;
        g.rock_speed = 5;
        g.player.x = (FIELD_W - g.player.w) / 2;
        g.drop_star();
        g.drop_rock();
        g.running = true;
        g.paused = false;
        message("");
        show_score(&g);
    });
    set("btnStart", "Caption", "Restart");
    set("tmrGame", "Enabled", "True");
}

pub fn btnPause_Click() {
    GAME.with(|g| {
        let mut g = g.borrow_mut();
        if !g.running {
            return;
        }
        g.paused = !g.paused;
        set("tmrGame", "Enabled", if g.paused { "False" } else { "True" });
        set("btnPause", "Caption", if g.paused { "Resume" } else { "Pause" });
        message(if g.paused { "Paused - press P or Resume" } else { "" });
    });
}

/// One frame of the game loop.
pub fn tmrGame_Tick() {
    GAME.with(|g| {
        let mut g = g.borrow_mut();
        if !g.running {
            return;
        }
        let dx = if g.right { 9 } else { 0 } - if g.left { 9 } else { 0 };
        g.player.x = (g.player.x + dx).clamp(0, FIELD_W - g.player.w);
        g.star.y += g.star_speed;
        g.rock.y += g.rock_speed;
        if g.star.hits(&g.player) {
            g.score += 10;
            if g.score % 50 == 0 {
                g.star_speed += 1;
                g.rock_speed += 1;
            }
            g.drop_star();
            show_score(&g);
        } else if g.star.y > FIELD_H {
            g.drop_star();
        }
        if g.rock.hits(&g.player) {
            g.lives -= 1;
            g.drop_rock();
            show_score(&g);
            if g.lives <= 0 {
                game_over(&mut g);
                return;
            }
        } else if g.rock.y > FIELD_H {
            g.drop_rock();
        }
        set("pnlPlayer", "Left", g.player.x);
        set("lblStar", "Left", g.star.x);
        set("lblStar", "Top", g.star.y);
        set("lblRock", "Left", g.rock.x);
        set("lblRock", "Top", g.rock.y);
    });
}

/// The key name ("Left") in the IDE's bridge; a key code ("37") in a native exe.
fn key() -> String {
    match event_arg(3).as_str() {
        "37" => "Left".into(),
        "39" => "Right".into(),
        "80" | "p" => "P".into(),
        k => k.to_string(),
    }
}

pub fn frmGame_KeyDown() {
    let k = key();
    if k == "P" {
        btnPause_Click();
        return;
    }
    GAME.with(|g| {
        let mut g = g.borrow_mut();
        match k.as_str() {
            "Left" => g.left = true,
            "Right" => g.right = true,
            _ => {}
        }
    });
}

pub fn frmGame_KeyUp() {
    let k = key();
    GAME.with(|g| {
        let mut g = g.borrow_mut();
        match k.as_str() {
            "Left" => g.left = false,
            "Right" => g.right = false,
            _ => {}
        }
    });
}

/// The mouse moves the paddle too (X is relative to pnlField).
pub fn pnlField_MouseMove() {
    let x: i32 = event_arg(0).parse().unwrap_or(0);
    GAME.with(|g| {
        let mut g = g.borrow_mut();
        if g.running && !g.paused {
            g.player.x = x - g.player.w / 2;
        }
    });
}
