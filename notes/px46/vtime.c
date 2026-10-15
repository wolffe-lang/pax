/* px46: how a terminal answers poll and read in non-canonical mode with
 * VMIN 0 (pelt's editor since sh11: VMIN 0, VTIME 1, a poll first). Run
 * on fd 0 as a terminal: a Linux pseudo-terminal (tools/linux-tty) and
 * PAX's console. Times are printed as classes, not milliseconds. Keys:
 * at the first "key? " type x, at the second y. Written for this lane. */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <poll.h>
#include <time.h>
static long ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000 + t.tv_nsec / 1000000; }
static struct termios base;
static void mode(int vmin, int vtime) {
    struct termios t = base;
    t.c_lflag &= ~(ICANON | ECHO | ISIG);
    t.c_cc[VMIN] = vmin; t.c_cc[VTIME] = vtime;
    tcsetattr(0, TCSANOW, &t);
}
static const char *cls(long d, long lo, long hi) { return d < lo ? "early" : d > hi ? "late" : "in band"; }
int main(void) {
    char b[64];
    if (tcgetattr(0, &base) != 0) { printf("not a terminal\n"); return 1; }
    int vm[3][2] = { {0, 0}, {0, 1}, {1, 0} };
    for (int i = 0; i < 3; i++) {
        mode(vm[i][0], vm[i][1]);
        struct pollfd p = { 0, POLLIN, 0 };
        long t0 = ms(); int r = poll(&p, 1, 300); long d = ms() - t0;
        printf("VMIN %d VTIME %d, nothing typed: poll 300 ms gives %d revents 0x%x, %s (250..2000 ms)\n", vm[i][0], vm[i][1], r, r > 0 ? p.revents : 0, cls(d, 250, 2000));
    }
    mode(0, 0);
    long t0 = ms(); ssize_t n = read(0, b, sizeof b); long d = ms() - t0;
    printf("VMIN 0 VTIME 0, nothing typed: read gives %zd, %s (0..50 ms)\n", n, cls(d, -1, 50));
    mode(0, 2);
    t0 = ms(); n = read(0, b, sizeof b); d = ms() - t0;
    printf("VMIN 0 VTIME 2, nothing typed: read gives %zd, %s (150..1500 ms)\n", n, cls(d, 150, 1500));
    mode(0, 1);
    printf("key? "); fflush(stdout);
    struct pollfd p = { 0, POLLIN, 0 };
    int r = poll(&p, 1, -1);
    n = read(0, b, sizeof b);
    printf("VMIN 0 VTIME 1, a key typed: poll gives %d revents 0x%x, read gives %zd: ", r, p.revents, n);
    for (ssize_t k = 0; k < n; k++) printf("%02x", (unsigned char)b[k]);
    printf("\n");
    mode(0, 100);
    printf("key? "); fflush(stdout);
    t0 = ms(); n = read(0, b, sizeof b); d = ms() - t0;
    printf("VMIN 0 VTIME 100, a key typed during the wait: read gives %zd, %s (before 10 s)\n", n, d < 10000 ? "ended by the key" : "ended by the time");
    tcsetattr(0, TCSANOW, &base);
    return 0;
}
