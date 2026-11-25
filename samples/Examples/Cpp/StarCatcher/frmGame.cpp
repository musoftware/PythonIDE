// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Star Catcher - an arcade game in C++ (RAD IDE GUI Bridge, radgui.hpp; Build > Publish = native exe).
//
// Each moving thing is a Sprite (a control name + a rectangle); the Timer is the game loop.
// Catch the yellow stars (+10), dodge the red rocks (-1 life), every 5 stars the game gets faster.
// Shows: a Timer game loop, KeyDown / KeyUp on the form (it sees the keys of its controls), MouseMove on a
// Panel, moving controls (Left / Top), rectangle collision, <random>, a best score in a file (fstream).
#include <fstream>
#include <random>
#include <string>
#include "radgui.hpp"

namespace {

const int kFieldW = 456, kFieldH = 330;

struct Sprite {
    std::string name;
    int x, y, w, h;
    void draw() const
    {
        rad::set(name, "Left", x);
        rad::set(name, "Top", y);
    }
    bool hits(const Sprite &o) const { return x < o.x + o.w && o.x < x + w && y < o.y + o.h && o.y < y + h; }
};

Sprite player{"pnlPlayer", 190, 300, 76, 14};
Sprite star{"lblStar", 100, -24, 24, 24};
Sprite rock{"lblRock", 300, -24, 24, 24};
std::mt19937 rng{std::random_device{}()};
int star_speed = 4, rock_speed = 5, score = 0, lives = 3, best = 0;
bool left_key = false, right_key = false, running = false, paused = false;
const char *kBestFile = "starcatcher.best";

int random_x() { return std::uniform_int_distribution<int>(0, kFieldW - 24)(rng); }

void drop(Sprite &s, int extra_height)
{
    s.x = random_x();
    s.y = -s.h - std::uniform_int_distribution<int>(0, extra_height)(rng);
}

void showScore()
{
    rad::set("lblScore", "Caption", "Score: " + std::to_string(score));
    rad::set("lblLives", "Caption", "Lives: " + std::to_string(lives));
    rad::set("lblBest", "Caption", "Best: " + std::to_string(best));
}

void message(const std::string &text)
{
    rad::set("lblMessage", "Caption", text);
    rad::set("lblMessage", "Visible", text.empty() ? "False" : "True");
}

void gameOver()
{
    running = false;
    rad::set("tmrGame", "Enabled", "False");
    if (score > best) {
        best = score;
        std::ofstream(kBestFile) << best << "\n";
        message("Game over - new best score " + std::to_string(score) + "!");
    } else {
        message("Game over - score " + std::to_string(score) + ". Press Start.");
    }
    showScore();
    rad::set("btnStart", "Caption", "Start");
}

}  // namespace

void frmGame_Load()
{
    std::ifstream in(kBestFile);
    if (!(in >> best)) best = 0;
    showScore();
}

void btnStart_Click()
{
    score = 0;
    lives = 3;
    star_speed = 4;
    rock_speed = 5;
    player.x = (kFieldW - player.w) / 2;
    drop(star, 0);
    drop(rock, 200);
    running = true;
    paused = false;
    message("");
    showScore();
    rad::set("btnStart", "Caption", "Restart");
    rad::set("tmrGame", "Enabled", "True");
}

void btnPause_Click()
{
    if (!running) return;
    paused = !paused;
    rad::set("tmrGame", "Enabled", paused ? "False" : "True");
    rad::set("btnPause", "Caption", paused ? "Resume" : "Pause");
    message(paused ? "Paused - press P or Resume" : "");
}

void tmrGame_Tick()
{
    if (!running) return;
    player.x += (right_key ? 9 : 0) - (left_key ? 9 : 0);
    if (player.x < 0) player.x = 0;
    if (player.x > kFieldW - player.w) player.x = kFieldW - player.w;
    star.y += star_speed;
    rock.y += rock_speed;
    if (star.hits(player)) {
        score += 10;
        if (score % 50 == 0) { star_speed++; rock_speed++; }
        drop(star, 0);
        showScore();
    } else if (star.y > kFieldH) {
        drop(star, 0);
    }
    if (rock.hits(player)) {
        lives--;
        drop(rock, 200);
        showScore();
        if (lives <= 0) { gameOver(); return; }
    } else if (rock.y > kFieldH) {
        drop(rock, 200);
    }
    rad::set(player.name, "Left", player.x);
    star.draw();
    rock.draw();
}

// KeyDown / KeyUp args: "X Y Button KeyCode KeyChar"; KeyCode = Windows key code (37 Left, 39 Right, 80 P)
void frmGame_KeyDown()
{
    std::string k = rad::arg(3);
    if (k == "37" || k == "Left") left_key = true;
    else if (k == "39" || k == "Right") right_key = true;
    else if (k == "80" || k == "p" || k == "P") btnPause_Click();
}

void frmGame_KeyUp()
{
    std::string k = rad::arg(3);
    if (k == "37" || k == "Left") left_key = false;
    else if (k == "39" || k == "Right") right_key = false;
}

void pnlField_MouseMove()
{
    if (running && !paused) player.x = std::stoi("0" + rad::arg(0)) - player.w / 2;
}
