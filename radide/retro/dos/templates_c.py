"""Turbo C-style templates (Open Watcom v2 wcl, 16-bit DOS). Original RAD IDE code."""

HELLO = r"""/* {name} - a Turbo C-style DOS program (RAD IDE)
 * Build: Open Watcom wcl, 16-bit small model -> a real DOS .EXE. Run: Ctrl+F5 (DOSBox-X). */
#include <stdio.h>
#include <string.h>

int main(void)
{
    char name[40];
    int i;

    printf("Hello from {name}!\n\n");
    printf("What is your name? ");
    if (fgets(name, sizeof name, stdin) == NULL || name[0] == '\n')
        strcpy(name, "friend\n");
    name[strcspn(name, "\r\n")] = '\0';
    printf("Welcome to DOS programming, %s!\n", name);
    for (i = 1; i <= 5; i++)
        printf("%3d x %d = %d\n", i, i, i * i);
    printf("Done.\n");
    return 0;
}
"""

MENU = r"""/* {name} - a text-mode menu with Turbo C style conio (arrow keys / 1-4 / Enter / Esc).
 * tcconio.h (in the project) adds clrscr, gotoxy, textcolor ... to Open Watcom's conio. */
#include <dos.h>
#include "tcconio.h"

static const char *items[4] = { "1  Say hello", "2  Show the time", "3  Count to ten", "4  Quit" };
static int sel = 0, done = 0;

static void draw_box(int x1, int y1, int x2, int y2)
{
    int i;
    textcolor(YELLOW);
    gotoxy(x1, y1); putch(0xC9);
    for (i = x1 + 1; i < x2; i++) putch(0xCD);
    putch(0xBB);
    for (i = y1 + 1; i < y2; i++) {
        gotoxy(x1, i); putch(0xBA);
        gotoxy(x2, i); putch(0xBA);
    }
    gotoxy(x1, y2); putch(0xC8);
    for (i = x1 + 1; i < x2; i++) putch(0xCD);
    putch(0xBC);
}

static void show_menu(void)
{
    int i;
    for (i = 0; i < 4; i++) {
        gotoxy(27, 7 + i);
        if (i == sel) { textcolor(BLACK); textbackground(CYAN); }
        else { textcolor(WHITE); textbackground(BLUE); }
        cprintf(" %-24s", items[i]);
    }
    textcolor(WHITE);
    textbackground(BLUE);
}

static void run_item(void)
{
    struct dostime_t t;
    int i;
    gotoxy(10, 15); clreol();
    switch (sel) {
    case 0: cputs("Hello! This menu was written in C."); break;
    case 1: _dos_gettime(&t); cprintf("The time is %02d:%02d:%02d", t.hour, t.minute, t.second); break;
    case 2: for (i = 1; i <= 10; i++) cprintf("%d ", i); break;
    case 3: done = 1; break;
    }
}

int main(void)
{
    int k;
    textbackground(BLUE);
    clrscr();
    textcolor(WHITE);
    gotoxy(28, 2); cputs("RAD IDE  -  DOS MENU");
    draw_box(24, 5, 55, 12);
    while (!done) {
        show_menu();
        k = getch();
        if (k == 0 || k == 0xE0) {
            k = getch();
            if (k == 72) sel = (sel + 3) % 4;
            if (k == 80) sel = (sel + 1) % 4;
        } else if (k >= '1' && k <= '4') {
            sel = k - '1'; show_menu(); run_item();
        } else if (k == 13) {
            run_item();
        } else if (k == 27) {
            done = 1;
        }
    }
    normvideo();
    clrscr();
    cputs("Goodbye!\r\n");
    return 0;
}
"""

MODE13 = r"""/* {name} - mode 13h graphics (320 x 200, 256 colours) through a far pointer to A000:0000. Any key quits. */
#include <conio.h>
#include <i86.h>
#include <stdio.h>
#include <stdlib.h>

static unsigned char __far *vga;

static void set_mode(unsigned char mode)
{
    union REGS r;
    r.h.ah = 0x00;
    r.h.al = mode;
    int86(0x10, &r, &r);
}

static void put_pixel(int x, int y, unsigned char c)
{
    if (x >= 0 && x < 320 && y >= 0 && y < 200)
        vga[(unsigned)y * 320u + (unsigned)x] = c;
}

static void box(int x1, int y1, int x2, int y2, unsigned char c)
{
    int x, y;
    for (y = y1; y <= y2; y++)
        for (x = x1; x <= x2; x++)
            put_pixel(x, y, c);
}

int main(void)
{
    int x, y, i;
    vga = (unsigned char __far *)MK_FP(0xA000, 0);
    set_mode(0x13);
    for (x = 0; x < 256; x++)                       /* colour bars */
        for (y = 150; y < 200; y++)
            put_pixel(x + 32, y, (unsigned char)x);
    for (i = 0; i < 100; i++)                       /* a diagonal pattern */
        for (x = 0; x < 100; x++)
            put_pixel(110 + x, 20 + i, (unsigned char)(32 + ((x ^ i) & 15)));
    box(20, 20, 80, 60, 4);
    box(240, 20, 300, 60, 2);
    srand(1);
    for (i = 0; i < 300; i++)
        put_pixel(rand() % 320, rand() % 140, (unsigned char)(16 + rand() % 16));
    getch();
    set_mode(0x03);
    printf("Back in text mode.\n");
    return 0;
}
"""

SPEAKER = r"""/* {name} - PC speaker music with sound(), delay() and nosound() (Open Watcom <i86.h>, like Turbo C <dos.h>). */
#include <i86.h>
#include <stdio.h>

static const unsigned notes[] = { 523, 587, 659, 698, 784, 784, 880, 880, 880, 880, 784 };
static const unsigned lens[]  = { 150, 150, 150, 150, 300, 300, 150, 150, 150, 150, 450 };

int main(void)
{
    int i;
    printf("Playing a little tune on the PC speaker...\n");
    for (i = 0; i < 11; i++) {
        sound(notes[i]);
        delay(lens[i]);
        nosound();
        delay(20);
    }
    printf("Finished.\n");
    return 0;
}
"""

MOUSE = r"""/* {name} - the mouse driver (INT 33h) in text mode. Right button or any key quits. */
#include <conio.h>
#include <i86.h>
#include "tcconio.h"

static union REGS r;

static void mouse(unsigned ax)
{
    r.x.ax = ax;
    int86(0x33, &r, &r);
}

int main(void)
{
    int x, y, b, ox = -1, oy = -1;
    clrscr();
    mouse(0);                                   /* reset: AX = FFFFh when a driver is present */
    if (r.x.ax != 0xFFFF) {
        cputs("No mouse driver found.\r\n");
        return 1;
    }
    cprintf("Mouse found (%u buttons). Left button: draw a star, right button: quit.", r.x.bx);
    mouse(1);                                   /* show the cursor */
    for (;;) {
        mouse(3);                               /* CX, DX = position in pixels, BX = buttons */
        x = r.x.cx / 8 + 1; y = r.x.dx / 8 + 1; b = r.x.bx;
        if (x != ox || y != oy) {
            mouse(2);
            gotoxy(1, 25); cprintf("Column %2d  Row %2d   ", x, y);
            mouse(1);
            ox = x; oy = y;
        }
        if (b & 1) {
            mouse(2);
            gotoxy(x, y); textcolor(YELLOW); putch('*'); textcolor(LIGHTGRAY);
            mouse(1);
        }
        if ((b & 2) || kbhit()) break;
    }
    mouse(2);
    normvideo();
    clrscr();
    cputs("Mouse demo finished.\r\n");
    return 0;
}
"""

BGI = r"""/* {name} - Borland BGI style graphics (initgraph / line / circle / outtextxy) with RAD IDE's tcgraph.h.
 * No EGAVGA.BGI is needed: tcgraph.h draws in 640 x 480 x 16 (mode 12h) through the video BIOS. */
#include <conio.h>
#include <stdio.h>
#include "tcgraph.h"

int main(void)
{
    int gd = DETECT, gm, i;
    initgraph(&gd, &gm, "");
    if (graphresult() != grOk) {
        printf("Graphics error\n");
        return 1;
    }
    setcolor(YELLOW);
    rectangle(20, 20, getmaxx() - 20, getmaxy() - 20);
    for (i = 0; i < 15; i++) {
        setcolor(i + 1);
        circle(320, 240, 20 + i * 12);
    }
    setfillstyle(SOLID_FILL, RED);
    bar(40, 40, 140, 100);
    setcolor(WHITE);
    line(40, 400, 600, 400);
    outtextxy(240, 440, "BGI subset in Open Watcom");
    getch();
    closegraph();
    printf("Back in text mode.\n");
    return 0;
}
"""

TEMPLATES = [
    ("dostc_hello", "Hello (Turbo C style)", "printf / fgets. Open Watcom builds a 16-bit small-model DOS .EXE.",
     {"MAIN.C": HELLO}),
    ("dostc_menu", "Text-Mode Menu", "clrscr, gotoxy, textcolor, cprintf, getch (tcconio.h adds the Borland "
     "conio extras).", {"MAIN.C": MENU, "TCCONIO.H": "@include/TCCONIO.H"}),
    ("dostc_mode13", "Mode 13h Graphics", "int86(0x10) and a __far pointer to the VGA memory at A000:0000.",
     {"MAIN.C": MODE13}),
    ("dostc_speaker", "PC Speaker Music", "sound(), delay(), nosound().", {"MAIN.C": SPEAKER}),
    ("dostc_mouse", "Mouse (INT 33h)", "int86(0x33) - reset, show, read the mouse.",
     {"MAIN.C": MOUSE, "TCCONIO.H": "@include/TCCONIO.H"}),
    ("dostc_bgi", "BGI Graphics (initgraph)", "Old Turbo C graphics.h code with RAD IDE's BGI subset (tcgraph.h, "
     "no .BGI drivers).", {"MAIN.C": BGI, "TCGRAPH.H": "@include/TCGRAPH.H"}),
]
