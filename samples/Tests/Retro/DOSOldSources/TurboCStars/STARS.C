/* STARS.C - old Turbo C style: conio colours, BGI graphics with a .BGI path (original RAD IDE sample) */
#include <stdio.h>
#include <stdlib.h>
#include <conio.h>
#include <dos.h>
#include <graphics.h>

int main(void)
{
    int gd = DETECT, gm, i, x, y;

    clrscr();
    textcolor(YELLOW);
    gotoxy(10, 5);
    cprintf("Turbo C star field - press a key");
    getch();

    initgraph(&gd, &gm, "C:\\TC\\BGI");
    randomize();
    for (i = 0; i < 400; i++) {
        x = random(getmaxx());
        y = random(getmaxy());
        putpixel(x, y, 1 + random(15));
    }
    setcolor(WHITE);
    rectangle(0, 0, getmaxx(), getmaxy());
    outtextxy(200, 20, "STARS");
    getch();
    closegraph();
    printf("Stars done.\n");
    return 0;
}
