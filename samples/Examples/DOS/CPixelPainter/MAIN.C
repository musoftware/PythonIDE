/* (c) 2026 Musoftware - https://musoftwares.com - MIT License
 *
 * CPixelPainter - a keyboard paint program for DOS in C (mode 13h: 320 x 200, 256 colours).
 *   Arrow keys   move the pen and paint a line behind it (the pen is the blinking-free white cross)
 *   1 - 9        choose the colour from the palette strip at the bottom
 *   R            a random rectangle in the current colour      B   a filled box around the pen
 *   C            clear the canvas                              Esc back to text mode (statistics are printed)
 * It writes straight into the VGA memory through a far pointer to A000:0000, switches modes with INT 10h
 * (int86) and reads the keyboard with getch() (extended keys arrive as 0 / 0xE0 + scan code).
 * RAD IDE builds it with OpenWatcom (wcl -bt=dos -ms) into a real-mode DOS .EXE and runs it in DOSBox-X. */
#include <conio.h>
#include <i86.h>
#include <stdio.h>
#include <stdlib.h>

#define W 320
#define H 200
#define CANVAS_H 180               /* rows 180..199: the palette strip */

static unsigned char __far *vga;
static int pen_x = 160, pen_y = 90;
static unsigned char colour = 14;
static long painted = 0;
static int moves = 0, boxes = 0;
static const unsigned char palette[9] = { 4, 2, 1, 14, 13, 11, 12, 10, 15 };

static void set_mode(unsigned char mode)
{
    union REGS r;
    r.h.ah = 0x00;
    r.h.al = mode;
    int86(0x10, &r, &r);
}

static void put_pixel(int x, int y, unsigned char c)
{
    if (x >= 0 && x < W && y >= 0 && y < CANVAS_H) {
        vga[(unsigned)y * W + (unsigned)x] = c;
        painted++;
    }
}

static void fill_rect(int x1, int y1, int x2, int y2, unsigned char c)
{
    int x, y;
    for (y = y1; y <= y2; y++)
        for (x = x1; x <= x2; x++)
            put_pixel(x, y, c);
}

static void frame_rect(int x1, int y1, int x2, int y2, unsigned char c)
{
    int i;
    for (i = x1; i <= x2; i++) { put_pixel(i, y1, c); put_pixel(i, y2, c); }
    for (i = y1; i <= y2; i++) { put_pixel(x1, i, c); put_pixel(x2, i, c); }
}

static void draw_palette(void)
{
    int i, x, y;
    for (i = 0; i < 9; i++)                         /* nine swatches with a white frame on the chosen one */
        for (y = CANVAS_H + 2; y < H; y++)
            for (x = 0; x < 34; x++) {
                unsigned char c = palette[i];
                if (palette[i] == colour && (y == CANVAS_H + 2 || y == H - 1 || x == 0 || x == 33))
                    c = 15;
                vga[(unsigned)y * W + (unsigned)(i * 35 + x)] = c;
            }
}

static void clear_canvas(void)
{
    unsigned i;
    for (i = 0; i < (unsigned)W * CANVAS_H; i++)
        vga[i] = 0;
    for (i = 0; i < W; i++)                         /* the line above the palette */
        vga[(unsigned)(CANVAS_H) * W + i] = 8;
}

static void move_pen(int dx, int dy)
{
    int i;
    for (i = 0; i < 6; i++) {                       /* a 2-pixel thick line, 6 steps */
        pen_x += dx;
        pen_y += dy;
        if (pen_x < 1) pen_x = 1;
        if (pen_x > W - 2) pen_x = W - 2;
        if (pen_y < 1) pen_y = 1;
        if (pen_y > CANVAS_H - 2) pen_y = CANVAS_H - 2;
        put_pixel(pen_x, pen_y, colour);
        put_pixel(pen_x + 1, pen_y, colour);
        put_pixel(pen_x, pen_y + 1, colour);
        put_pixel(pen_x + 1, pen_y + 1, colour);
    }
    moves++;
}

int main(void)
{
    int k, done = 0;
    vga = (unsigned char __far *)MK_FP(0xA000, 0);
    srand(2026);
    set_mode(0x13);
    clear_canvas();
    frame_rect(0, 0, W - 1, CANVAS_H - 1, 7);
    draw_palette();
    while (!done) {
        k = getch();
        if (k == 0 || k == 0xE0) {                  /* an extended key: the scan code follows */
            switch (getch()) {
            case 72: move_pen(0, -1); break;        /* up */
            case 80: move_pen(0, 1); break;         /* down */
            case 75: move_pen(-1, 0); break;        /* left */
            case 77: move_pen(1, 0); break;         /* right */
            }
            continue;
        }
        if (k >= '1' && k <= '9') {
            colour = palette[k - '1'];
            draw_palette();
        } else if (k == 'r' || k == 'R') {
            int x = rand() % (W - 60) + 4, y = rand() % (CANVAS_H - 50) + 4;
            frame_rect(x, y, x + 20 + rand() % 36, y + 12 + rand() % 30, colour);
            boxes++;
        } else if (k == 'b' || k == 'B') {
            fill_rect(pen_x - 8, pen_y - 8, pen_x + 8, pen_y + 8, colour);
            boxes++;
        } else if (k == 'c' || k == 'C') {
            clear_canvas();
            frame_rect(0, 0, W - 1, CANVAS_H - 1, 7);
        } else if (k == 27) {
            done = 1;
        }
    }
    set_mode(0x03);
    printf("CPixelPainter - %d pen moves, %d boxes, %ld pixels painted.\n", moves, boxes, painted);
    printf("Pen ended at %d,%d. Goodbye!\n", pen_x, pen_y);
    return 0;
}
