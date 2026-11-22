/* (c) 2026 Musoftware - https://musoftwares.com - MIT License
 *
 * Sales Chart - a bar chart drawn with Panels, in C (RAD IDE GUI Bridge, radgui.h; Build > Publish = native exe).
 *
 * Each bar is a Panel whose Top / Height follow the value (0..100). Shows: mouse events with coordinates
 * (click inside the chart to set the bar under the mouse), a Timer that animates the bars towards their
 * values, a TrackBar for the speed, the ColorDialog, NumericUpDown + ComboBox input, saving / loading
 * the data as CSV, and statistics (total / average / best month).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "radgui.h"

#define BARS 6
#define BASE 280        /* y of the bars' bottom inside pnlChart */
#define SCALE 2.4       /* pixels per unit: value 100 = 240 px */
#define BAR_W 44
#define FIRST_X 14
#define STEP_X 60

static const char *months[BARS] = {"Jan", "Feb", "Mar", "Apr", "May", "Jun"};
static double value[BARS] = {50, 65, 40, 80, 70, 90};    /* the data */
static double drawn[BARS];                               /* what the bars show now (animation) */
static char bar_color[16] = "#3B7DD8";

static const char *ctl(const char *prefix, int i)
{
    static char name[32];
    snprintf(name, sizeof name, "%s%d", prefix, i + 1);
    return name;
}

static void draw_bar(int i)
{
    int h = (int)(drawn[i] * SCALE + 0.5);
    if (h < 1) h = 1;
    rad_set_num(ctl("pnlBar", i), "Top", BASE - h);
    rad_set_num(ctl("pnlBar", i), "Height", h);
    rad_set_num(ctl("lblVal", i), "Top", BASE - h - 20);
    rad_set(ctl("lblVal", i), "Caption", rad_str((int)(drawn[i] + 0.5)));
}

static void update_stats(void)
{
    double total = 0;
    int i, best = 0;
    char text[200];
    for (i = 0; i < BARS; i++) {
        total += value[i];
        if (value[i] > value[best]) best = i;
    }
    snprintf(text, sizeof text, "Total: %s   Average: %.1f   Best month: %s (%s)", rad_str(total), total / BARS,
             months[best], rad_str(value[best]));
    rad_set("lblStats", "Caption", text);
}

/* show the data: animated when the check box is on, at once otherwise */
static void refresh(void)
{
    int i;
    update_stats();
    if (rad_get_num("chkAnimate", "Value") == 1) {
        rad_set("tmrAnim", "Enabled", "True");
        return;
    }
    for (i = 0; i < BARS; i++) {
        drawn[i] = value[i];
        draw_bar(i);
    }
}

static void set_value(int i, double v)
{
    if (v < 0) v = 0;
    if (v > 100) v = 100;
    value[i] = (int)(v + 0.5);
    rad_set_num("cboMonth", "ListIndex", i);
    rad_set_num("nudValue", "Value", value[i]);
    refresh();
}

/* ------------------------------------------------------------------ events */
void frmChart_Load(void)
{
    int i;
    srand((unsigned)time(NULL));
    for (i = 0; i < BARS; i++) drawn[i] = 0;
    rad_set_num("chkAnimate", "Value", 1);
    rad_set_num("cboMonth", "ListIndex", 0);
    refresh();
}

void tmrAnim_Tick(void)
{
    double speed = rad_get_num("trkSpeed", "Value");      /* 1..10 units per tick */
    int i, moving = 0;
    for (i = 0; i < BARS; i++) {
        double d = value[i] - drawn[i];
        if (d == 0) continue;
        if (d > speed) d = speed;
        if (d < -speed) d = -speed;
        drawn[i] += d;
        draw_bar(i);
        moving = 1;
    }
    if (!moving) rad_set("tmrAnim", "Enabled", "False");
}

void btnSet_Click(void)
{
    int i = (int)rad_get_num("cboMonth", "ListIndex");
    if (i < 0) { rad_msgbox("Choose a month first."); return; }
    set_value(i, rad_get_num("nudValue", "Value"));
}

void cboMonth_SelectedIndexChanged(void)
{
    int i = (int)rad_get_num("cboMonth", "ListIndex");
    if (i >= 0) rad_set_num("nudValue", "Value", value[i]);
}

void btnRandom_Click(void)
{
    int i;
    for (i = 0; i < BARS; i++) value[i] = 10 + rand() % 91;
    refresh();
}

void btnColor_Click(void)
{
    int i;
    rad_set("dlgColor", "Color", bar_color);
    if (strcmp(rad_call("dlgColor", "ShowColor", ""), "OK") != 0) return;
    snprintf(bar_color, sizeof bar_color, "%s", rad_get("dlgColor", "Color"));
    for (i = 0; i < BARS; i++) rad_set(ctl("pnlBar", i), "BackColor", bar_color);
}

/* mouse: X picks the bar, Y the value. Args: "X Y Button KeyCode KeyChar" */
void pnlChart_MouseDown(void)
{
    int x = atoi(rad_arg(0)), y = atoi(rad_arg(1));
    int i = (x - FIRST_X + (STEP_X - BAR_W) / 2) / STEP_X;
    if (i < 0 || i >= BARS) return;
    set_value(i, (BASE - y) / SCALE);
}

void btnSave_Click(void)
{
    FILE *f = fopen("sales.csv", "w");
    int i;
    if (!f) { rad_msgbox("Cannot write sales.csv"); return; }
    fprintf(f, "month,value\n");
    for (i = 0; i < BARS; i++) fprintf(f, "%s,%s\n", months[i], rad_str(value[i]));
    fclose(f);
    rad_msgbox("Saved sales.csv");
}

void btnLoad_Click(void)
{
    FILE *f = fopen("sales.csv", "r");
    char line[100];
    int i;
    if (!f) { rad_msgbox("sales.csv not found - press Save first."); return; }
    while (fgets(line, sizeof line, f)) {
        char *comma = strchr(line, ',');
        if (!comma) continue;
        *comma = 0;
        for (i = 0; i < BARS; i++)
            if (strcmp(line, months[i]) == 0) value[i] = rad_num(comma + 1);
    }
    fclose(f);
    refresh();
}

void chkAnimate_CheckedChanged(void) { refresh(); }
