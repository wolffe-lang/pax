#include <stdio.h>
#include <stdlib.h>
#include "util.h"

int main(int argc, char **argv) {
    const char *who = argc > 1 ? argv[1] : "world";
    char *up = util_upper(who);
    if (!up) return 1;
    printf("hello, %s (%zu e's)\n", up, util_count(who, 'e'));
    free(up);
    return 0;
}
