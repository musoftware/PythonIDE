/* C64HelloC - a Commodore 64 program in C (cc65), written with RAD IDE.
   Prints with conio, moves a ball with the cursor keys / W A S D; Q quits. F5 builds C64HelloC.prg. */
#include <conio.h>
#include <c64.h>

int main(void)
{
    unsigned char x = 20, y = 12, key;

    bordercolor(COLOR_BLUE);
    bgcolor(COLOR_BLACK);
    textcolor(COLOR_YELLOW);
    clrscr();
    cputsxy(2, 1, "Hello from C64HelloC!");
    cputsxy(2, 2, "W A S D moves the ball, Q quits");
    for (;;) {
        cputcxy(x, y, 'O');
        key = cgetc();
        cputcxy(x, y, ' ');
        if ((key == 'd' || key == CH_CURS_RIGHT) && x < 39) ++x;
        if ((key == 'a' || key == CH_CURS_LEFT) && x > 0) --x;
        if ((key == 's' || key == CH_CURS_DOWN) && y < 24) ++y;
        if ((key == 'w' || key == CH_CURS_UP) && y > 4) --y;
        if (key == 'q') break;
    }
    clrscr();
    return 0;
}
