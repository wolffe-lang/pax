/* Raw console bytes, with explicit host-driven key-down and key-up. */
#define _GNU_SOURCE
#include <poll.h>
#include <stdio.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static long long millis(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) _exit(2);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
int main(void) {
    struct termios raw;
    if (tcgetattr(0, &raw)) return 2;
    cfmakeraw(&raw);
    if (tcsetattr(0, TCSANOW, &raw)) return 2;
    for (unsigned row = 0; row < 4; ++row) {
        if (tcflush(0, TCIFLUSH)) return 2;
        printf("TYPEMATIC_READY %u\n", row); fflush(stdout);
        struct pollfd p = {0, POLLIN, 0};
        unsigned char bytes[128]; long long stamps[128]; unsigned n = 0;
        if (poll(&p, 1, 10000) <= 0) return 3;
        long long begin = millis();
        do {
            if (read(0, &bytes[n], 1) != 1) return 3;
            stamps[n++] = millis() - begin;
        } while (n < sizeof bytes && millis() - begin < 1600
                 && poll(&p, 1, (int)(1600 - (millis() - begin))) > 0);
        printf("TYPEMATIC_BYTES %u", row);
        for (unsigned i = 0; i < n; ++i) printf(" %02x", bytes[i]);
        printf("\nTYPEMATIC_TIMES %u", row);
        for (unsigned i = 0; i < n; ++i) printf(" %lld", stamps[i]);
        printf("\n"); fflush(stdout);
    }
    puts("TYPEMATIC_DONE");
    return 0;
}
