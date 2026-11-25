/* (c) 2026 Musoftware - https://musoftwares.com - MIT License
 *
 * Star Catcher - a small arcade game in C (RAD IDE GUI Bridge, radgui.h; Build > Publish = native exe).
 *
 * Move the blue paddle with Left / Right (or the mouse), catch the yellow stars (+10) and dodge the red
 * rocks (-1 life). Shows: a Timer game loop, keyboard events on the form (KeyDown / KeyUp, the form sees
 * the keys of its controls), MouseMove on a Panel, moving controls with Left / Top, rectangle collision,
 * a score / lives display and a best score saved to a file.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "radgui.h"

#define FIELD_W 456
#define FIELD_H 330
#define PLAYER_W 76
#define PLAYER_Y 300
#define ITEM 24
#define BEST_FILE "starcatcher.best"

static int player_x = 190, star_x, star_y, rock_x, rock_y;
static int star_speed = 4, rock_speed = 5;
static int score = 0, lives = 3, best = 0;
static int left_down = 0, right_down = 0, running = 0, paused = 0;

static void set_int(const char *obj, const char *prop, int v) { rad_set_num(obj, prop, v); }

static void show_score(void)
{
    char s[64];
    snprintf(s, sizeof s, "Score: %d", score);
    rad_set("lblScore", "Caption", s);
    snprintf(s, sizeof s, "Lives: %d", lives);
    rad_set("lblLives", "Caption", s);
    snprintf(s, sizeof s, "Best: %d", best);
    rad_set("lblBest", "Caption", s);
}

static void new_star(void) { star_x = rand() % (FIELD_W - ITEM); star_y = -ITEM; }
static void new_rock(void) { rock_x = rand() % (FIELD_W - ITEM); rock_y = -ITEM - rand() % 200; }

/* do the two rectangles overlap? */
static int hit(int ax, int ay, int aw, int ah, int bx, int by, int bw, int bh)
{
    return ax < bx + bw && bx < ax + aw && ay < by + bh && by < ay + ah;
}

static void message(const char *text)
{
    rad_set("lblMessage", "Caption", text);
    rad_set("lblMessage", "Visible", *text ? "True" : "False");
}

static void game_over(void)
{
    char s[100];
    running = 0;
    rad_set("tmrGame", "Enabled", "False");
    if (score > best) {
        FILE *f = fopen(BEST_FILE, "w");
        best = score;
        if (f) { fprintf(f, "%d\n", best); fclose(f); }
        snprintf(s, sizeof s, "Game over - new best score %d!", score);
    } else {
        snprintf(s, sizeof s, "Game over - score %d. Press Start.", score);
    }
    message(s);
    show_score();
    rad_set("btnStart", "Caption", "Start");
}

/* ------------------------------------------------------------------ events */
void frmGame_Load(void)
{
    FILE *f = fopen(BEST_FILE, "r");
    srand((unsigned)time(NULL));
    if (f) { if (fscanf(f, "%d", &best) != 1) best = 0; fclose(f); }
    show_score();
}

void btnStart_Click(void)
{
    score = 0;
    lives = 3;
    star_speed = 4;
    rock_speed = 5;
    player_x = (FIELD_W - PLAYER_W) / 2;
    new_star();
    new_rock();
    running = 1;
    paused = 0;
    message("");
    show_score();
    rad_set("btnStart", "Caption", "Restart");
    rad_set("tmrGame", "Enabled", "True");
}

void btnPause_Click(void)
{
    if (!running) return;
    paused = !paused;
    rad_set("tmrGame", "Enabled", paused ? "False" : "True");
    rad_set("btnPause", "Caption", paused ? "Resume" : "Pause");
    message(paused ? "Paused - press P or Resume" : "");
}

/* one frame of the game loop */
void tmrGame_Tick(void)
{
    if (!running) return;
    if (left_down) player_x -= 9;
    if (right_down) player_x += 9;
    if (player_x < 0) player_x = 0;
    if (player_x > FIELD_W - PLAYER_W) player_x = FIELD_W - PLAYER_W;
    star_y += star_speed;
    rock_y += rock_speed;

    if (hit(star_x, star_y, ITEM, ITEM, player_x, PLAYER_Y, PLAYER_W, 14)) {
        score += 10;
        if (score % 50 == 0) { star_speed++; rock_speed++; }      /* faster every 5 stars */
        new_star();
        show_score();
    } else if (star_y > FIELD_H) {
        new_star();                                                 /* missed: no penalty */
    }
    if (hit(rock_x, rock_y, ITEM, ITEM, player_x, PLAYER_Y, PLAYER_W, 14)) {
        lives--;
        new_rock();
        show_score();
        if (lives <= 0) { game_over(); return; }
    } else if (rock_y > FIELD_H) {
        new_rock();
    }
    set_int("pnlPlayer", "Left", player_x);
    set_int("lblStar", "Left", star_x);
    set_int("lblStar", "Top", star_y);
    set_int("lblRock", "Left", rock_x);
    set_int("lblRock", "Top", rock_y);
}

/* KeyDown / KeyUp args: "X Y Button KeyCode KeyChar"; KeyCode = Windows key code (37 Left, 39 Right, 80 P) */
void frmGame_KeyDown(void)
{
    const char *k = rad_arg(3);
    if (strcmp(k, "37") == 0 || strcmp(k, "Left") == 0) left_down = 1;
    else if (strcmp(k, "39") == 0 || strcmp(k, "Right") == 0) right_down = 1;
    else if (strcmp(k, "80") == 0 || strcmp(k, "p") == 0 || strcmp(k, "P") == 0) btnPause_Click();
}

void frmGame_KeyUp(void)
{
    const char *k = rad_arg(3);
    if (strcmp(k, "37") == 0 || strcmp(k, "Left") == 0) left_down = 0;
    else if (strcmp(k, "39") == 0 || strcmp(k, "Right") == 0) right_down = 0;
}

/* the mouse moves the paddle too (X is relative to pnlField) */
void pnlField_MouseMove(void)
{
    if (!running || paused) return;
    player_x = atoi(rad_arg(0)) - PLAYER_W / 2;
}
