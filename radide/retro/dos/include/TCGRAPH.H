/* TCGRAPH.H - a small Borland BGI compatible subset for Open Watcom 16-bit DOS programs.
 * Written for RAD IDE (original code, free to use in your programs).
 *
 * Old Turbo C programs call initgraph() with a path to EGAVGA.BGI. Those .BGI drivers are Borland's and are not
 * needed here: initgraph() switches the VGA to 640x480x16 (mode 12h, like VGAHI) and everything is drawn through
 * the video BIOS. Supported: initgraph closegraph graphresult grapherrormsg getmaxx getmaxy getmaxcolor
 * setcolor getcolor setbkcolor cleardevice putpixel getpixel line lineto linerel moveto moverel getx gety
 * rectangle bar bar3d circle ellipse(full) setfillstyle floodfill(simple) outtextxy outtext settextstyle(no-op)
 * textwidth textheight delay. Not supported: fonts (.CHR), arcs, pie slices, palettes, image functions.
 * Include it once:   #include "tcgraph.h"
 */
#ifndef RAD_TCGRAPH_H
#define RAD_TCGRAPH_H

#ifdef __WATCOMC__
#pragma disable_message(202)   /* helpers the program does not use are fine */
#endif

#include <dos.h>
#include <i86.h>
#include <stdlib.h>

#define DETECT 0
#define VGA 9
#define VGALO 0
#define VGAMED 1
#define VGAHI 2
#define grOk 0
#define grNotDetected (-2)
#define SOLID_FILL 1
#define EMPTY_FILL 0
#define DEFAULT_FONT 0
#define HORIZ_DIR 0

#ifndef RAD_COLORS_DEFINED
#define RAD_COLORS_DEFINED
enum BGI_COLORS { BG_BLACK, BG_BLUE, BG_GREEN, BG_CYAN, BG_RED, BG_MAGENTA, BG_BROWN, BG_LIGHTGRAY, BG_DARKGRAY,
                  BG_LIGHTBLUE, BG_LIGHTGREEN, BG_LIGHTCYAN, BG_LIGHTRED, BG_LIGHTMAGENTA, BG_YELLOW, BG_WHITE };
#endif
#ifndef RAD_TCCONIO_H
#define BLACK 0
#define BLUE 1
#define GREEN 2
#define CYAN 3
#define RED 4
#define MAGENTA 5
#define BROWN 6
#define LIGHTGRAY 7
#define DARKGRAY 8
#define LIGHTBLUE 9
#define LIGHTGREEN 10
#define LIGHTCYAN 11
#define LIGHTRED 12
#define LIGHTMAGENTA 13
#define YELLOW 14
#define WHITE 15
#endif

static int bgi_color = 15, bgi_fill = 15, bgi_x = 0, bgi_y = 0, bgi_result = grOk;

static void putpixel(int x, int y, int c)
{
    union REGS r;
    if (x < 0 || y < 0 || x > 639 || y > 479) return;
    r.h.ah = 0x0C; r.h.al = (unsigned char)c; r.h.bh = 0; r.x.cx = (unsigned)x; r.x.dx = (unsigned)y;
    int86(0x10, &r, &r);
}

static unsigned getpixel(int x, int y)
{
    union REGS r;
    r.h.ah = 0x0D; r.h.bh = 0; r.x.cx = (unsigned)x; r.x.dx = (unsigned)y;
    int86(0x10, &r, &r);
    return r.h.al;
}

static void bgi_mode(unsigned char mode)
{
    union REGS r;
    r.h.ah = 0; r.h.al = mode;
    int86(0x10, &r, &r);
}

static void initgraph(int *driver, int *mode, const char *path)
{
    (void)path;                 /* no .BGI driver needed */
    bgi_mode(0x12);
    if (driver) *driver = VGA;
    if (mode) *mode = VGAHI;
    bgi_color = 15; bgi_fill = 15; bgi_x = bgi_y = 0; bgi_result = grOk;
}

static void closegraph(void)               { bgi_mode(0x03); }
static int graphresult(void)               { int r = bgi_result; bgi_result = grOk; return r; }
static const char *grapherrormsg(int code) { return code == grOk ? "No error" : "Graphics error"; }
static int getmaxx(void)                   { return 639; }
static int getmaxy(void)                   { return 479; }
static int getmaxcolor(void)               { return 15; }
static void setcolor(int c)                { bgi_color = c & 15; }
static int getcolor(void)                  { return bgi_color; }
static int getx(void)                      { return bgi_x; }
static int gety(void)                      { return bgi_y; }
static void moveto(int x, int y)           { bgi_x = x; bgi_y = y; }
static void moverel(int dx, int dy)        { bgi_x += dx; bgi_y += dy; }
static void setfillstyle(int pattern, int c) { (void)pattern; bgi_fill = c & 15; }
static void settextstyle(int f, int d, int s) { (void)f; (void)d; (void)s; }
static int textwidth(const char *s)        { int n = 0; while (s[n]) n++; return n * 8; }
static int textheight(const char *s)       { (void)s; return 16; }

static void setbkcolor(int c)
{
    union REGS r;               /* palette register 0 */
    r.x.ax = 0x1000; r.h.bl = 0; r.h.bh = (unsigned char)(c & 15);
    int86(0x10, &r, &r);
}

static void bgi_hline(int x1, int x2, int y, int c)
{
    int x;
    if (x1 > x2) { x = x1; x1 = x2; x2 = x; }
    for (x = x1; x <= x2; x++) putpixel(x, y, c);
}

static void line(int x1, int y1, int x2, int y2)
{
    int dx = abs(x2 - x1), sx = x1 < x2 ? 1 : -1;
    int dy = -abs(y2 - y1), sy = y1 < y2 ? 1 : -1;
    int err = dx + dy, e2;
    for (;;) {
        putpixel(x1, y1, bgi_color);
        if (x1 == x2 && y1 == y2) break;
        e2 = 2 * err;
        if (e2 >= dy) { err += dy; x1 += sx; }
        if (e2 <= dx) { err += dx; y1 += sy; }
    }
}

static void lineto(int x, int y)           { line(bgi_x, bgi_y, x, y); bgi_x = x; bgi_y = y; }
static void linerel(int dx, int dy)        { lineto(bgi_x + dx, bgi_y + dy); }

static void rectangle(int l, int t, int r, int b)
{
    line(l, t, r, t); line(r, t, r, b); line(r, b, l, b); line(l, b, l, t);
}

static void bar(int l, int t, int r, int b)
{
    int y;
    for (y = t; y <= b; y++) bgi_hline(l, r, y, bgi_fill);
}

static void bar3d(int l, int t, int r, int b, int depth, int top)
{
    bar(l, t, r, b);
    rectangle(l, t, r, b);
    if (depth) {
        line(r, b, r + depth, b - depth);
        line(r + depth, b - depth, r + depth, t - depth);
        if (top) { line(l, t, l + depth, t - depth); line(l + depth, t - depth, r + depth, t - depth); }
    }
}

static void ellipse_full(int cx, int cy, int rx, int ry)
{
    long x = 0, y = ry, rx2 = (long)rx * rx, ry2 = (long)ry * ry;
    long px = 0, py = 2 * rx2 * y, p;
    p = ry2 - rx2 * ry + rx2 / 4;
    while (px < py) {
        putpixel(cx + (int)x, cy + (int)y, bgi_color); putpixel(cx - (int)x, cy + (int)y, bgi_color);
        putpixel(cx + (int)x, cy - (int)y, bgi_color); putpixel(cx - (int)x, cy - (int)y, bgi_color);
        x++; px += 2 * ry2;
        if (p < 0) p += ry2 + px;
        else { y--; py -= 2 * rx2; p += ry2 + px - py; }
    }
    p = (long)(ry2 * (x * x + x) + rx2 * (y - 1) * (y - 1) - rx2 * ry2);
    while (y >= 0) {
        putpixel(cx + (int)x, cy + (int)y, bgi_color); putpixel(cx - (int)x, cy + (int)y, bgi_color);
        putpixel(cx + (int)x, cy - (int)y, bgi_color); putpixel(cx - (int)x, cy - (int)y, bgi_color);
        y--; py -= 2 * rx2;
        if (p > 0) p += rx2 - py;
        else { x++; px += 2 * ry2; p += rx2 - py + px; }
    }
}

static void circle(int x, int y, int radius)  { ellipse_full(x, y, radius, radius); }

static void ellipse(int x, int y, int start, int end, int rx, int ry)
{
    (void)start; (void)end;     /* arcs are drawn as full ellipses */
    ellipse_full(x, y, rx, ry);
}

static void floodfill(int x, int y, int border)
{
    /* scan-line fill limited to the rows above and below: enough for closed convex shapes */
    int l, r, yy, dir;
    for (dir = -1; dir <= 1; dir += 2) {
        for (yy = (dir < 0 ? y : y + 1); yy >= 0 && yy <= 479; yy += dir) {
            if ((int)getpixel(x, yy) == border) break;
            for (l = x; l > 0 && (int)getpixel(l - 1, yy) != border; l--) ;
            for (r = x; r < 639 && (int)getpixel(r + 1, yy) != border; r++) ;
            bgi_hline(l, r, yy, bgi_fill);
        }
    }
}

static void cleardevice(void)
{
    union REGS r;
    r.x.ax = 0x0600; r.h.bh = 0; r.x.cx = 0; r.x.dx = (29 << 8) | 79;
    int86(0x10, &r, &r);
    bgi_x = bgi_y = 0;
}

static void outtextxy(int x, int y, const char *s)
{
    union REGS r;
    r.h.ah = 0x02; r.h.bh = 0; r.h.dl = (unsigned char)(x / 8); r.h.dh = (unsigned char)(y / 16);
    int86(0x10, &r, &r);
    while (*s) {
        r.h.ah = 0x0E; r.h.al = (unsigned char)*s++; r.h.bh = 0; r.h.bl = (unsigned char)bgi_color;
        int86(0x10, &r, &r);
    }
}

static void outtext(const char *s)          { outtextxy(bgi_x, bgi_y, s); bgi_x += textwidth(s); }

#endif /* RAD_TCGRAPH_H */
