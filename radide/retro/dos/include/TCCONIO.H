/* TCCONIO.H - Turbo C style console functions for Open Watcom 16-bit DOS programs.
 * Written for RAD IDE (original code, free to use in your programs).
 *
 * Open Watcom's <conio.h> has getch / kbhit / cputs / cprintf but not the Borland extras. This header adds
 * clrscr, clreol, gotoxy, wherex, wherey, textcolor, textbackground, textattr, highvideo, lowvideo, normvideo,
 * window, random, randomize - through the video BIOS (INT 10h), so text is written in colour like Turbo C.
 * Include it once (it defines static functions):   #include "tcconio.h"
 */
#ifndef RAD_TCCONIO_H
#define RAD_TCCONIO_H

#ifdef __WATCOMC__
#pragma disable_message(202)   /* helpers the program does not use are fine */
#endif

#include <conio.h>
#include <dos.h>
#include <i86.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <time.h>

#ifndef BLACK                       /* tcgraph.h included first defines them as macros */
enum COLORS { BLACK, BLUE, GREEN, CYAN, RED, MAGENTA, BROWN, LIGHTGRAY, DARKGRAY, LIGHTBLUE, LIGHTGREEN,
              LIGHTCYAN, LIGHTRED, LIGHTMAGENTA, YELLOW, WHITE };
#endif
#define BLINK 128

static unsigned char tc_attr = 0x07;
static unsigned char tc_win_l = 0, tc_win_t = 0, tc_win_r = 79, tc_win_b = 24;

static void tc_setcursor(int col, int row)          /* 0-based screen position */
{
    union REGS r;
    r.h.ah = 0x02; r.h.bh = 0; r.h.dl = (unsigned char)col; r.h.dh = (unsigned char)row;
    int86(0x10, &r, &r);
}

static void tc_getcursor(int *col, int *row)
{
    union REGS r;
    r.h.ah = 0x03; r.h.bh = 0;
    int86(0x10, &r, &r);
    *col = r.h.dl; *row = r.h.dh;
}

static void tc_scroll(int lines, int l, int t, int rr, int b)
{
    union REGS r;
    r.h.ah = 0x06; r.h.al = (unsigned char)lines; r.h.bh = tc_attr;
    r.h.cl = (unsigned char)l; r.h.ch = (unsigned char)t; r.h.dl = (unsigned char)rr; r.h.dh = (unsigned char)b;
    int86(0x10, &r, &r);
}

static void textcolor(int c)      { tc_attr = (unsigned char)((tc_attr & 0x70) | (c & 0x8F)); }
static void textbackground(int c) { tc_attr = (unsigned char)((tc_attr & 0x8F) | ((c & 7) << 4)); }
static void textattr(int a)       { tc_attr = (unsigned char)a; }
static void highvideo(void)       { tc_attr |= 0x08; }
static void lowvideo(void)        { tc_attr &= 0xF7; }
static void normvideo(void)       { tc_attr = 0x07; }

static void window(int left, int top, int right, int bottom)     /* 1-based, like Turbo C */
{
    tc_win_l = (unsigned char)(left - 1); tc_win_t = (unsigned char)(top - 1);
    tc_win_r = (unsigned char)(right - 1); tc_win_b = (unsigned char)(bottom - 1);
    tc_setcursor(tc_win_l, tc_win_t);
}

static void clrscr(void)
{
    tc_scroll(0, tc_win_l, tc_win_t, tc_win_r, tc_win_b);
    tc_setcursor(tc_win_l, tc_win_t);
}

static void gotoxy(int x, int y)  { tc_setcursor(tc_win_l + x - 1, tc_win_t + y - 1); }
static int wherex(void)           { int c, r; tc_getcursor(&c, &r); return c - tc_win_l + 1; }
static int wherey(void)           { int c, r; tc_getcursor(&c, &r); return r - tc_win_t + 1; }

static int tc_putch(int ch)
{
    union REGS r;
    int col, row;
    tc_getcursor(&col, &row);
    if (ch == '\n') {
        row++;
    } else if (ch == '\r') {
        col = tc_win_l;
    } else if (ch == '\b') {
        if (col > tc_win_l) col--;
    } else if (ch == '\a') {
        r.h.ah = 0x0E; r.h.al = 7; r.h.bh = 0; int86(0x10, &r, &r);
    } else {
        r.h.ah = 0x09; r.h.al = (unsigned char)ch; r.h.bh = 0; r.h.bl = tc_attr; r.x.cx = 1;
        int86(0x10, &r, &r);
        col++;
        if (col > tc_win_r) { col = tc_win_l; row++; }
    }
    if (row > tc_win_b) {
        tc_scroll(1, tc_win_l, tc_win_t, tc_win_r, tc_win_b);
        row = tc_win_b;
    }
    tc_setcursor(col, row);
    return ch;
}

static int tc_cputs(const char *s)
{
    while (*s) tc_putch((unsigned char)*s++);
    return 0;
}

static int tc_cprintf(const char *fmt, ...)
{
    char buf[256];
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = vsprintf(buf, fmt, ap);
    va_end(ap);
    tc_cputs(buf);
    return n;
}

static void clreol(void)
{
    union REGS r;
    int col, row;
    tc_getcursor(&col, &row);
    r.h.ah = 0x09; r.h.al = ' '; r.h.bh = 0; r.h.bl = tc_attr; r.x.cx = (unsigned)(tc_win_r - col + 1);
    int86(0x10, &r, &r);                 /* AH=09h writes CX copies without moving the cursor */
}

#define putch(c)      tc_putch(c)
#define cputs(s)      tc_cputs(s)
#define cprintf       tc_cprintf
#ifndef random
#define random(n)     (rand() % (n))
#endif
#ifndef randomize
#define randomize()   srand((unsigned)time(NULL))
#endif

#endif /* RAD_TCCONIO_H */
