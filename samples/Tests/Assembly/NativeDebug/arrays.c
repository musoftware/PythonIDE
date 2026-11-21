/* arrays.c - a small C program for the native debugger windows (gcc -g -O0). */
#include <stdio.h>

static long long table[4] = {11, 22, 33, 44};

long long add_all(const long long *p, int n)
{
    long long sum = 0;
    for (int i = 0; i < n; i++)
        sum += p[i];                       /* breakpoint: Registers / Disassembly / Memory (&table) */
    return sum;
}

int main(void)
{
    long long total = add_all(table, 4);
    printf("Total = %lld\n", total);
    return 0;
}
