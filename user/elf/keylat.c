/* px129: keylat -- how long a full-screen program takes from a key to its
 * frame, on a pseudo-terminal of the system it runs on.
 *
 *   keylat [-n KEYS] [-q QUIET_MS] [-r ROWS] [-c COLS] [-k HEX]... -- PROGRAM [ARG...]
 *
 * Opens a pseudo-terminal (posix_openpt(3)), gives it ROWS x COLS (default
 * 90 x 256, the console's grid at 2560 x 1440), and runs PROGRAM on its
 * slave as a new session's controlling terminal with TERM=linux. It
 * answers the queries the console answers (DA1 and DECID `ESC [ ? 6 c`,
 * DSR 5 `ESC [ 0 n`, DSR 6 `ESC [ 1 ; 1 R`), reads the program's opening
 * until QUIET_MS pass with no output, then types each key (-k, hex bytes,
 * in rotation; default Down then Up, `1b5b42` and `1b5b41`) KEYS times
 * (default 40), each after the last key's output went quiet, and times with
 * RDTSC from the key's write to the first and to the last byte of the
 * program's answer read on the master. The TSC's rate is measured against
 * CLOCK_MONOTONIC over an idle second. Prints a line a key and a summary:
 *
 *   keylat: key N: first F ms, last L ms, B bytes
 *   keylat: KEYS keys: first ms min/median/max ..., last ms ..., bytes ...
 *
 * `last` is when the frame was all written (its last byte read here
 * within the quiet window), so it is the program's whole turn plus the
 * pseudo-terminal's two crossings. The program is killed (its pid) at
 * the end. Exit 0; 1 on a failed call (named); 2 on a usage error.
 *
 * Written from the man pages of the calls named (posix_openpt(3),
 * ptsname(3), setsid(2), TIOCSCTTY and TIOCSWINSZ in ioctl_tty(2)),
 * console_codes(4) for the answers, and the Intel SDM vol. 2 for RDTSC.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static void die(const char *what) {
    fprintf(stderr, "keylat: %s: %s\n", what, strerror(errno));
    exit(1);
}

static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static uint64_t mono_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

static double tsc_per_ms(void) {
    uint64_t m0 = mono_ns(), m;
    do { m = mono_ns(); } while (m == m0);
    uint64_t a = m, ta = rdtsc();
    do { m = mono_ns(); } while (m - a < 1000000000ull);
    uint64_t m1 = m;
    do { m = mono_ns(); } while (m == m1);
    uint64_t tb = rdtsc();
    return (double)(tb - ta) / ((double)(m - a) / 1e6);
}

static int g_m = -1;
static char g_tail[16];
static size_t g_tail_n;

/* Answer the queries in what the program wrote (a query split across two
 * reads is caught by keeping the last bytes). */
static void answer(const char *p, size_t n) {
    char buf[16 + 65536];
    size_t k = g_tail_n;
    memcpy(buf, g_tail, k);
    if (n > 65536) { p += n - 65536; n = 65536; }
    memcpy(buf + k, p, n);
    k += n;
    for (size_t i = g_tail_n > 0 ? 0 : 0; i + 2 < k; i++) {
        if (buf[i] != 27) continue;
        if (buf[i + 1] == 'Z' && i >= g_tail_n) { if (write(g_m, "\033[?6c", 5) < 0) die("write"); continue; }
        if (buf[i + 1] != '[') continue;
        size_t j = i + 2;
        while (j < k && ((buf[j] >= '0' && buf[j] <= '9') || buf[j] == ';' || buf[j] == '?' || buf[j] == '>')) j++;
        if (j >= k || j < g_tail_n) continue;
        size_t len = j - (i + 2);
        const char *ps = buf + i + 2;
        if (buf[j] == 'c' && (len == 0 || (len == 1 && ps[0] == '0'))) { if (write(g_m, "\033[?6c", 5) < 0) die("write"); }
        else if (buf[j] == 'n' && len == 1 && ps[0] == '5') { if (write(g_m, "\033[0n", 4) < 0) die("write"); }
        else if (buf[j] == 'n' && ((len == 1 && ps[0] == '6') || (len == 2 && ps[0] == '?' && ps[1] == '6'))) {
            if (write(g_m, "\033[1;1R", 6) < 0) die("write");
        }
    }
    g_tail_n = k < sizeof g_tail ? k : sizeof g_tail;
    memcpy(g_tail, buf + k - g_tail_n, g_tail_n);
}

/* Read until `quiet_ms` pass with nothing; the TSC of the first and the
 * last byte, and the count. */
static size_t drain(int quiet_ms, uint64_t *first, uint64_t *last) {
    size_t total = 0;
    *first = *last = 0;
    char buf[65536];
    for (;;) {
        struct pollfd p = {g_m, POLLIN, 0};
        int r = poll(&p, 1, quiet_ms);
        if (r < 0) { if (errno == EINTR) continue; die("poll"); }
        if (r == 0) break;
        ssize_t n = read(g_m, buf, sizeof buf);
        uint64_t t = rdtsc();
        if (n < 0) { if (errno == EINTR || errno == EAGAIN) continue; if (errno == EIO) break; die("read"); }
        if (n == 0) break;
        if (!*first) *first = t;
        *last = t;
        total += (size_t)n;
        answer(buf, (size_t)n);
    }
    return total;
}

static int cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return x < y ? -1 : x > y;
}

static void summary(const char *what, double *v, int n) {
    qsort(v, (size_t)n, sizeof *v, cmp_d);
    printf(" %s ms min %.3f median %.3f max %.3f;", what, v[0], v[n / 2], v[n - 1]);
}

int main(int argc, char **argv) {
    int keys_n = 40, quiet = 300, rows = 90, cols = 256;
    char keys[16][64];
    size_t keylen[16];
    int nkeys = 0;
    int opt;
    while ((opt = getopt(argc, argv, "n:q:r:c:k:")) != -1) {
        if (opt == 'n') keys_n = atoi(optarg);
        else if (opt == 'q') quiet = atoi(optarg);
        else if (opt == 'r') rows = atoi(optarg);
        else if (opt == 'c') cols = atoi(optarg);
        else if (opt == 'k' && nkeys < 16) {
            size_t L = strlen(optarg) / 2;
            if (L == 0 || L > 63) { fprintf(stderr, "keylat: -k takes hex bytes\n"); return 2; }
            for (size_t i = 0; i < L; i++) {
                unsigned v;
                if (sscanf(optarg + 2 * i, "%2x", &v) != 1) { fprintf(stderr, "keylat: -k takes hex bytes\n"); return 2; }
                keys[nkeys][i] = (char)v;
            }
            keylen[nkeys++] = L;
        } else {
            fprintf(stderr, "usage: keylat [-n KEYS] [-q QUIET_MS] [-r ROWS] [-c COLS] [-k HEX]... -- PROGRAM [ARG...]\n");
            return 2;
        }
    }
    if (optind >= argc || keys_n < 1 || keys_n > 10000) {
        fprintf(stderr, "usage: keylat [-n KEYS] [-q QUIET_MS] [-r ROWS] [-c COLS] [-k HEX]... -- PROGRAM [ARG...]\n");
        return 2;
    }
    if (nkeys == 0) {
        memcpy(keys[0], "\033[B", 3); keylen[0] = 3;
        memcpy(keys[1], "\033[A", 3); keylen[1] = 3;
        nkeys = 2;
    }
    double per_ms = tsc_per_ms();
    g_m = posix_openpt(O_RDWR | O_NOCTTY);
    if (g_m < 0) die("posix_openpt");
    if (grantpt(g_m) < 0) die("grantpt");
    if (unlockpt(g_m) < 0) die("unlockpt");
    const char *sn = ptsname(g_m);
    if (!sn) die("ptsname");
    struct winsize ws = {(unsigned short)rows, (unsigned short)cols, 0, 0};
    if (ioctl(g_m, TIOCSWINSZ, &ws) < 0) die("TIOCSWINSZ");
    pid_t pid = fork();
    if (pid < 0) die("fork");
    if (pid == 0) {
        if (setsid() < 0) die("setsid");
        int s = open(sn, O_RDWR);
        if (s < 0) die(sn);
        ioctl(s, TIOCSCTTY, 0);
        dup2(s, 0); dup2(s, 1); dup2(s, 2);
        if (s > 2) close(s);
        close(g_m);
        setenv("TERM", "linux", 1);
        execvp(argv[optind], argv + optind);
        die(argv[optind]);
    }
    uint64_t f, l;
    size_t opening = drain(1500, &f, &l);
    printf("keylat: %s on %s at %dx%d, TSC %.1f MHz; its opening %zu bytes\n", argv[optind], sn, cols, rows,
           per_ms / 1e3, opening);
    double *fv = calloc((size_t)keys_n, sizeof *fv), *lv = calloc((size_t)keys_n, sizeof *lv), *bv = calloc((size_t)keys_n, sizeof *bv);
    if (!fv || !lv || !bv) die("calloc");
    int got = 0;
    for (int i = 0; i < keys_n; i++) {
        int k = i % nkeys;
        uint64_t t0 = rdtsc();
        if (write(g_m, keys[k], keylen[k]) != (ssize_t)keylen[k]) die("write key");
        size_t b = drain(quiet, &f, &l);
        double fm = f ? (double)(f - t0) / per_ms : -1, lm = l ? (double)(l - t0) / per_ms : -1;
        printf("keylat: key %d: first %.3f ms, last %.3f ms, %zu bytes\n", i + 1, fm, lm, b);
        if (b) { fv[got] = fm; lv[got] = lm; bv[got] = (double)b; got++; }
    }
    printf("keylat: %d keys, %d answered:", keys_n, got);
    if (got) { summary("first", fv, got); summary("last", lv, got); }
    printf("\n");
    kill(pid, SIGKILL);
    waitpid(pid, NULL, 0);
    return 0;
}
