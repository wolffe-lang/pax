/* px102's measurement program: a small static C program gdb is driven
   over under strace (break at a function, step, print, continue, exit). */
#include <stdio.h>
int counter = 0;
static int add(int a, int b)
{
    int c = a + b;
    counter += c;
    return c;
}
int main(void)
{
    int x = 3;
    int y = add(x, 4);
    y = add(y, 5);
    printf("y=%d counter=%d\n", y, counter);
    return 0;
}
