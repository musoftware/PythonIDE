/* A long-running native program to try Debug > Attach to Process (gdb) on. */
#include <stdio.h>
#ifdef _WIN32
#include <windows.h>
#define SLEEP_MS(ms) Sleep(ms)
#else
#include <unistd.h>
#define SLEEP_MS(ms) usleep((ms) * 1000)
#endif

struct point { int x; int y; };

int tick(int count) {
    struct point p = { count, count * 2 };
    int sum = p.x + p.y;
    printf("tick %d sum %d\n", count, sum);
    fflush(stdout);
    return sum;
}

int main(void) {
    int n = 0;
    for (;;) {
        n++;
        tick(n);
        SLEEP_MS(500);
    }
    return 0;
}
