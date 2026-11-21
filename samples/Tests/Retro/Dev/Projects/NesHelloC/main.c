/* NesHelloC - an NES program in C (cc65), written with RAD IDE.
   The D-pad moves the '@', Start clears the screen. F5 builds NesHelloC.nes with cl65 -t nes. */
#include <conio.h>
#include <nes.h>
#include <joystick.h>

int main(void)
{
    unsigned char x = 14, y = 12, ox, oy, pad;

    joy_install(joy_static_stddrv);
    clrscr();
    gotoxy(5, 2);
    cprintf("Hello from %s!", "NesHelloC");
    gotoxy(5, 4);
    cputs("Move with the D-pad");

    for (;;) {
        ox = x;
        oy = y;
        waitvsync();
        pad = joy_read(JOY_1);
        if (JOY_RIGHT(pad) && x < 29) ++x;
        if (JOY_LEFT(pad) && x > 1) --x;
        if (JOY_DOWN(pad) && y < 26) ++y;
        if (JOY_UP(pad) && y > 6) --y;
        if (x != ox || y != oy) {
            cputcxy(ox, oy, ' ');
        }
        cputcxy(x, y, '@');
    }
}
