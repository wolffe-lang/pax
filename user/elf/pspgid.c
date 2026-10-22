/* px61 test helper, not a ps implementation. The upstream childstate
 * probe asks exactly `ps -o pgid= -p PID`; Busybox's ps lacks -p.
 * References: POSIX getpgid(2), ps(1)'s documented -o/-p interface.
 * No ps, libc or kernel implementation source was consulted. */
#define _XOPEN_SOURCE 700
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 5 || strcmp(argv[1], "-o") ||
        strcmp(argv[2], "pgid=") || strcmp(argv[3], "-p")) {
        fputs("ps-pgid: expected -o pgid= -p PID\n", stderr);
        return 2;
    }
    char *end;
    errno = 0;
    long n = strtol(argv[4], &end, 10);
    if (errno || end == argv[4] || *end || n < 1 || n > INT_MAX) {
        fputs("ps-pgid: invalid PID\n", stderr);
        return 2;
    }
    pid_t group = getpgid((pid_t)n);
    if (group < 0) {
        perror("ps-pgid: getpgid");
        return 1;
    }
    printf("%ld\n", (long)group);
    return 0;
}
