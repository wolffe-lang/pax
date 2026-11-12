/* conflood — a console flood with a network echo beside it (px129, R-px129-13).
 *
 *   conflood MODE [IDLE FLOOD AFTER]
 *
 * MODE is what each console write is: `scroll` (ten full lines, the
 * screen scrolled ten times: conspeed's scroll10), `screen` (the cursor
 * home and a whole screen of changed text, conspeed's plain) or `big`
 * (256 KiB of text with an SGR before every character, conspeed's sgr
 * four times over in one write). IDLE, FLOOD and AFTER are seconds (6,
 * 12 and 6 by default).
 *
 * A child answers UDP datagrams to port 7 with the same bytes (an echo
 * server: a process that has to be scheduled to answer, as an ssh
 * server does for a keystroke). The parent says each phase in a UDP
 * datagram to 10.0.2.100 port 9 (`conflood: idle`, `conflood: flood`,
 * `conflood: after …`, `conflood: end`), sleeps IDLE seconds, writes
 * MODE's frame to its standard output (the console) back to back for
 * FLOOD seconds by the TSC (its rate taken over an idle second first:
 * PAX's tick clock loses the ticks that fall inside a console write),
 * sleeps AFTER seconds, ends the child and exits 0. The other end of the
 * network (tests/mpx3-conflood.d/peer.py) pings the machine and times
 * the echo through all three phases.
 *
 * Written from the Linux man pages (socket(7), udp(7), ip(7), console
 * ioctls) and the SDM's RDTSC. No other source.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static double mono(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}

static void nap(double s) {
    struct timespec t = {(time_t)s, (long)((s - (double)(time_t)s) * 1e9)};
    while (nanosleep(&t, &t) < 0 && errno == EINTR) {
    }
}

static int marker_fd = -1;
static struct sockaddr_in peer;

static void mark(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void mark(const char *fmt, ...) {
    char b[200];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n >= (int)sizeof b) n = (int)sizeof b - 1;
    (void)!sendto(marker_fd, b, (size_t)n, 0, (struct sockaddr *)&peer, sizeof peer);
}

static void echo(void) {
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    if (s < 0) _exit(2);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(7);
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(s, (struct sockaddr *)&a, sizeof a) < 0) _exit(3);
    static char buf[2048];
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof from;
        ssize_t k = recvfrom(s, buf, sizeof buf, 0, (struct sockaddr *)&from, &fl);
        if (k < 0) {
            if (errno == EINTR) continue;
            _exit(4);
        }
        (void)!sendto(s, buf, (size_t)k, 0, (struct sockaddr *)&from, fl);
    }
}

static char *frame;
static size_t frame_len, frame_cap;

static void put(const char *s, size_t n) {
    if (frame_len + n > frame_cap) {
        frame_cap = (frame_len + n) * 2;
        frame = realloc(frame, frame_cap);
        if (!frame) exit(5);
    }
    memcpy(frame + frame_len, s, n);
    frame_len += n;
}

static void build(const char *mode, int cols, int rows) {
    char line[1024];
    if (cols > 1000) cols = 1000;
    if (strcmp(mode, "scroll") == 0) {
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < cols; c++) line[c] = (char)(33 + (r * 7 + c) % 94);
            line[cols] = '\n';
            put(line, (size_t)cols + 1);
        }
    } else if (strcmp(mode, "screen") == 0) {
        put("\033[H", 3);
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) line[c] = (char)(33 + (r * 13 + c) % 94);
            put(line, (size_t)cols);
            if (r + 1 < rows) put("\r\n", 2);
        }
    } else {
        int i = 0;
        while (frame_len < 262144) {
            char e[16];
            int n = snprintf(e, sizeof e, "\033[3%dm%c", i % 8, (char)(33 + i % 94));
            put(e, (size_t)n);
            if (++i % cols == 0) put("\n", 1);
        }
        put("\033[m", 3);
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: conflood scroll|screen|big [IDLE FLOOD AFTER]\n");
        return 2;
    }
    const char *mode = argv[1];
    double idle = argc > 2 ? atof(argv[2]) : 6, flood = argc > 3 ? atof(argv[3]) : 12, after = argc > 4 ? atof(argv[4]) : 6;
    struct winsize w = {0};
    if (ioctl(1, TIOCGWINSZ, &w) < 0 || w.ws_col == 0) w.ws_col = 80, w.ws_row = 25;
    build(mode, w.ws_col, w.ws_row);

    marker_fd = socket(AF_INET, SOCK_DGRAM, 0);
    peer.sin_family = AF_INET;
    peer.sin_port = htons(9);
    inet_pton(AF_INET, "10.0.2.100", &peer.sin_addr);
    pid_t child = fork();
    if (child == 0) echo();

    /* the TSC's rate over an idle second */
    double m0 = mono();
    uint64_t t0 = rdtsc();
    nap(1.0);
    double hz = (double)(rdtsc() - t0) / (mono() - m0);

    printf("conflood: %s, %zu bytes a write, %dx%d cells, TSC %.1f MHz; idle %.0f s, flood %.0f s, after %.0f s\n",
           mode, frame_len, w.ws_col, w.ws_row, hz / 1e6, idle, flood, after);
    fflush(stdout);
    mark("conflood: idle");
    nap(idle);
    mark("conflood: flood");
    uint64_t end = rdtsc() + (uint64_t)(flood * hz), start = rdtsc();
    unsigned long writes = 0;
    while (rdtsc() < end) {
        size_t off = 0;
        while (off < frame_len) {
            ssize_t k = write(1, frame + off, frame_len - off);
            if (k <= 0) break;
            off += (size_t)k;
        }
        writes++;
    }
    double took = (double)(rdtsc() - start) / hz;
    mark("conflood: after %lu writes of %zu bytes in %.2f s", writes, frame_len, took);
    printf("\033[m\033[2J\033[Hconflood: %s: %lu writes of %zu bytes in %.2f s\n", mode, writes, frame_len, took);
    fflush(stdout);
    nap(after);
    mark("conflood: end");
    kill(child, SIGKILL);
    waitpid(child, 0, 0);
    printf("conflood: end\n");
    return 0;
}
