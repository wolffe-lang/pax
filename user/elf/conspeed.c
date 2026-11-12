/* px129: conspeed -- how fast the terminal this runs on draws.
 *
 *   conspeed [-q] [-n REPS] [-t SECONDS] [-T SECONDS] [-g MS] [-r FILE] [-o TTY] [DIR...]
 *
 * Writes test frames to the terminal (TTY, default /dev/tty, else
 * standard error when it is a terminal) inside the alternate screen
 * (`CSI ? 1049 h`) with the cursor hidden, then puts the terminal back as
 * it found it (main screen, cursor shown, rendition and margins reset,
 * the mouse modes and the palette reset) and prints one table on
 * standard output. It reads no input, needs no privilege and writes
 * nothing else. Ctrl-C puts the terminal back too.
 *
 * Every frame is one write(2) (repeated until all of it is taken), timed
 * with RDTSC, whose rate is measured against CLOCK_MONOTONIC over an idle
 * second spun before the tests and another after (PAX's CLOCK_MONOTONIC
 * moves in 10 ms ticks, pax#299, so it alone cannot time a frame, and it
 * loses the ticks that arrive while a console write runs with interrupts
 * off, so it is short across the tests: the `kept` figure).
 *
 * The run is bounded by the TSC, at the rate the idle second before the
 * tests gave (version 4, after version 3 ran for many minutes at a real
 * machine's console: its bound was CLOCK_MONOTONIC's, which the long
 * console writes starved): the whole run at most -T SECONDS (default 60)
 * of tests, each test at most -t SECONDS (default 4) and its share of
 * what is left. A test's first frame is timed alone; it then runs as many
 * frames as fit its budget, at most REPS (default 100), at least the one.
 * A test that no time is left for is skipped (0 frames). Between frames it
 * sleeps -g MS (default 10; 0 for none), so other processes and the
 * network get the CPU between two writes (a console write runs with
 * interrupts off). With -r FILE each test's line is written to FILE as
 * the test ends, the header first; an interrupted run leaves the tests
 * that ended there, and a line saying so. The tests, the grid being the
 * terminal's TIOCGWINSZ (COLS x ROWS):
 *
 *   unit    no write: 2^21 dependent multiply-adds in user mode, the unit
 *           the rows compare the console's costs with on one boot
 *   bytes   COLS*ROWS bytes of `ESC [ m` that draw nothing (the parse
 *           and the write path alone)
 *   cell    one cell: a cursor position and one character, one write
 *   plain   (a) the whole grid: a cursor position a row and the row's
 *           characters; every frame shifts the text by one, so every cell
 *           changes every frame
 *   same    `plain`'s first frame again and again over itself: nothing
 *           changes
 *   sgr     (b) the same with an SGR foreground and background before
 *           every cell (`ESC [ 3f ; 4b m`), shifted likewise
 *   scroll1 (c) one full-width line and CR LF at the bottom row: one
 *           scroll a frame, from a screen full of text
 *   scroll10 (c) ten such lines in one write: ten scrolls a frame
 *   clear   (d) `ESC [ H ESC [ 2 J` and then `plain`'s frame
 *   cursor  `plain` with the cursor shown during the write
 *   DIR     (e) a recorded stream: DIR/setup written once untimed (when
 *           there is one), then DIR/1, DIR/2, ... replayed in rotation,
 *           one frame each; the test is named by DIR's last component
 *
 * A line a test: its frames, the bytes and the cells (printed characters)
 * of a frame, the mean and the least milliseconds a frame, the bytes a
 * second, and the microseconds a cell. Then two derived lines: the cost
 * of a byte (the `bytes` test) and the cost of drawing a cell (`plain`
 * less its bytes at that rate), with the pixel bytes a second that
 * implies for an 8x16 cell of 32-bit pixels (doubled when the
 * framebuffer is wider than 2560: PAX's scale).
 *
 * -q is a quick check: 3 frames or 1 s a test. -o names where the frames
 * go (a terminal, or /dev/null for a dry run). Exit 0; 1 on a failed call
 * (named); 2 on a usage error.
 *
 * Written from the man pages of the calls named, console_codes(4) and
 * ECMA-48 for the sequences, and the Intel SDM vol. 2 for RDTSC.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define VERSION "conspeed 4 (px129)"
#define MAXREPS 100000

static int g_fd = -1;
static volatile sig_atomic_t g_entered = 0;
/* What puts the terminal back: the rendition, the margins, the mouse
 * modes, the palette (`ESC ] R`, console_codes(4), only for TERM=linux:
 * another terminal reads it as an unended OSC), the cursor, the main
 * screen. */
static char RESTORE[128];
static size_t g_restore_n;

static void set_restore(const char *term) {
    int linux_ = !term || strcmp(term, "linux") == 0;
    g_restore_n = (size_t)snprintf(RESTORE, sizeof RESTORE, "%s%s%s", "\033[0m\033[r\033[?1000l\033[?1002l\033[?1003l\033[?1006l",
                                   linux_ ? "\033]R" : "", "\033[?25h\033[?1049l");
}

static void die(const char *what) {
    int e = errno;
    if (g_entered && g_fd >= 0) { ssize_t r = write(g_fd, RESTORE, g_restore_n); (void)r; }
    fprintf(stderr, "conspeed: %s: %s\n", what, strerror(e));
    exit(1);
}

static int g_res = -1; /* -r FILE */

static void on_signal(int sig) {
    if (g_entered && g_fd >= 0) { ssize_t r = write(g_fd, RESTORE, g_restore_n); (void)r; }
    if (g_res >= 0) {
        static const char m[] = "conspeed: interrupted by a signal; the tests above are those that ended\n";
        ssize_t r = write(g_res, m, sizeof m - 1);
        (void)r;
    }
    signal(sig, SIG_DFL);
    raise(sig);
}

/* --- the clock ------------------------------------------------------------ */

static sigjmp_buf g_jb;
static int g_tsc = 0;

static void on_fault(int sig) { (void)sig; siglongjmp(g_jb, 1); }

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

/* Whether RDTSC runs here (CR4.TSD would fault it in user mode). */
static int probe_tsc(void) {
    struct sigaction sa, os, oi;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_fault;
    sigaction(SIGSEGV, &sa, &os);
    sigaction(SIGILL, &sa, &oi);
    int ok = 0;
    if (sigsetjmp(g_jb, 1) == 0) {
        uint64_t a = rdtsc(), b = rdtsc();
        ok = b >= a;
    }
    sigaction(SIGSEGV, &os, NULL);
    sigaction(SIGILL, &oi, NULL);
    return ok;
}

/* The next change of CLOCK_MONOTONIC, and the TSC read with it. */
static void edge(uint64_t *ns, uint64_t *tsc) {
    uint64_t m0 = mono_ns(), m;
    do { m = mono_ns(); } while (m == m0);
    *ns = m;
    *tsc = g_tsc ? rdtsc() : 0;
}

/* A second of CLOCK_MONOTONIC spun in user mode, edge to edge, and the
 * TSC at both edges. */
static void idle_rate(uint64_t *n0, uint64_t *t0, uint64_t *n1, uint64_t *t1) {
    edge(n0, t0);
    uint64_t m;
    do { m = mono_ns(); } while (m - *n0 < 1000000000ull);
    edge(n1, t1);
}

/* A stamp: the TSC when it runs, else nanoseconds. */
static inline uint64_t stamp(void) { return g_tsc ? rdtsc() : mono_ns(); }

/* --- buffers -------------------------------------------------------------- */

struct buf { char *p; size_t n, cap; };

static void put(struct buf *b, const char *s, size_t n) {
    if (b->n + n > b->cap) {
        size_t c = b->cap ? b->cap * 2 : 65536;
        while (c < b->n + n) c *= 2;
        b->p = realloc(b->p, c);
        if (!b->p) die("realloc");
        b->cap = c;
    }
    memcpy(b->p + b->n, s, n);
    b->n += n;
}

static void puts_(struct buf *b, const char *s) { put(b, s, strlen(s)); }

static void putf(struct buf *b, const char *fmt, int x, int y) {
    char t[64];
    int n = snprintf(t, sizeof t, fmt, x, y);
    put(b, t, (size_t)n);
}

static void write_all(const char *p, size_t n) {
    while (n > 0) {
        ssize_t r = write(g_fd, p, n);
        if (r < 0) {
            if (errno == EINTR || errno == EAGAIN) continue;
            die("write");
        }
        p += r;
        n -= (size_t)r;
    }
}

/* Characters, ASCII or UTF-8 code points, printed outside escape
 * sequences: the cells a stream writes (an estimate: controls such as
 * ED/EL also draw cells, and the console may draw a cell twice). */
static size_t cells_of(const char *p, size_t n) {
    size_t c = 0;
    int st = 0; /* 0 ground, 1 after ESC, 2 CSI, 3 OSC, 4 OSC after ESC */
    for (size_t i = 0; i < n; i++) {
        unsigned char b = (unsigned char)p[i];
        if (st == 1) { st = b == '[' ? 2 : b == ']' ? 3 : 0; continue; }
        if (st == 2) { if (b >= 0x40 && b <= 0x7e) st = 0; continue; }
        if (st == 3) { if (b == 7) st = 0; else if (b == 27) st = 4; continue; }
        if (st == 4) { st = 0; continue; }
        if (b == 27) { st = 1; continue; }
        if (b < 32 || b == 127) continue;
        if ((b & 0xc0) == 0x80) continue;
        c++;
    }
    return c;
}

/* --- the tests ------------------------------------------------------------ */

struct test {
    char name[64];
    struct buf setup;      /* written once, untimed */
    struct buf *frames;    /* replayed in rotation */
    int nframes;
    size_t bytes, cells;   /* of the first frame (the mean over a rotation for streams) */
    int unit;              /* the CPU's unit of work, no write */
    long reps;
    double ms_mean, ms_min, mbps, us_cell;
    uint64_t total, least;
};

static int g_cols = 80, g_rows = 24;

static void text_row(struct buf *b, int r, int shift) {
    char line[1024];
    for (int c = 0; c < g_cols; c++) line[c] = (char)(33 + (r * 7 + c + shift) % 94);
    put(b, line, (size_t)g_cols);
}

static void frame_plain(struct buf *b, int shift) {
    for (int r = 0; r < g_rows; r++) {
        putf(b, "\033[%d;%dH", r + 1, 1);
        text_row(b, r, shift);
    }
}

static void frame_sgr(struct buf *b, int shift) {
    for (int r = 0; r < g_rows; r++) {
        putf(b, "\033[%d;%dH", r + 1, 1);
        for (int c = 0; c < g_cols; c++) {
            int f = (c + shift) % 8, g = (r + c / 8 + shift + 3) % 8;
            if (g == f) g = (g + 1) % 8;
            putf(b, "\033[3%d;4%dm", f, g);
            char ch = (char)(33 + (r * 7 + c + shift) % 94);
            put(b, &ch, 1);
        }
        puts_(b, "\033[m");
    }
}

static struct test *g_tests;
static int g_ntests, g_captests;

static struct test *add_test(const char *name, int nframes) {
    if (g_ntests == g_captests) {
        g_captests = g_captests ? g_captests * 2 : 16;
        g_tests = realloc(g_tests, sizeof *g_tests * (size_t)g_captests);
        if (!g_tests) die("realloc");
    }
    struct test *t = &g_tests[g_ntests++];
    memset(t, 0, sizeof *t);
    snprintf(t->name, sizeof t->name, "%s", name);
    t->frames = calloc((size_t)nframes, sizeof *t->frames);
    if (!t->frames) die("calloc");
    t->nframes = nframes;
    return t;
}

static void build_synthetic(void) {
    struct test *t;
    t = add_test("unit", 1);
    t->unit = 1;
    t = add_test("bytes", 1);
    for (int i = 0; i < g_cols * g_rows / 3; i++) puts_(&t->frames[0], "\033[m");
    t = add_test("cell", 64);
    for (int i = 0; i < 64; i++) {
        putf(&t->frames[i], "\033[%d;%dH", (i * 7) % g_rows + 1, (i * 13) % g_cols + 1);
        char ch = (char)(33 + i % 94);
        put(&t->frames[i], &ch, 1);
    }
    /* Two frames each, alternated, so every cell changes every frame. */
    t = add_test("plain", 2);
    frame_plain(&t->frames[0], 0);
    frame_plain(&t->frames[1], 1);
    t = add_test("same", 1);
    puts_(&t->setup, "\033[H\033[2J");
    frame_plain(&t->setup, 0);
    frame_plain(&t->frames[0], 0);
    t = add_test("sgr", 2);
    frame_sgr(&t->frames[0], 0);
    frame_sgr(&t->frames[1], 1);
    /* The scrolls start from a full screen of text, so every line they
     * scroll moves every cell from the first frame on. */
    t = add_test("scroll1", 2);
    puts_(&t->setup, "\033[H\033[2J");
    frame_plain(&t->setup, 50);
    for (int k = 0; k < 2; k++) {
        putf(&t->frames[k], "\033[%d;%dH", g_rows, 1);
        text_row(&t->frames[k], k, k);
        puts_(&t->frames[k], "\r\n");
    }
    t = add_test("scroll10", 2);
    puts_(&t->setup, "\033[H\033[2J");
    frame_plain(&t->setup, 50);
    for (int k = 0; k < 2; k++) {
        putf(&t->frames[k], "\033[%d;%dH", g_rows, 1);
        for (int l = 0; l < 10; l++) {
            text_row(&t->frames[k], l, k * 10 + l);
            puts_(&t->frames[k], "\r\n");
        }
    }
    t = add_test("clear", 2);
    for (int k = 0; k < 2; k++) {
        puts_(&t->frames[k], "\033[H\033[2J");
        frame_plain(&t->frames[k], k);
    }
    t = add_test("cursor", 2);
    for (int k = 0; k < 2; k++) {
        puts_(&t->frames[k], "\033[?25h");
        frame_plain(&t->frames[k], k);
        puts_(&t->frames[k], "\033[?25l");
    }
}

static int read_file(const char *path, struct buf *b) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    char tmp[65536];
    for (;;) {
        ssize_t r = read(fd, tmp, sizeof tmp);
        if (r < 0) { if (errno == EINTR) continue; close(fd); return -1; }
        if (r == 0) break;
        put(b, tmp, (size_t)r);
    }
    close(fd);
    return 0;
}

static void load_stream(const char *dir) {
    char path[4096];
    int n = 0;
    struct stat st;
    for (;;) {
        snprintf(path, sizeof path, "%s/%d", dir, n + 1);
        if (stat(path, &st) != 0) break;
        n++;
    }
    if (n == 0) {
        fprintf(stderr, "conspeed: %s: no frame %s/1\n", dir, dir);
        exit(2);
    }
    const char *base = strrchr(dir, '/');
    char name[256];
    snprintf(name, sizeof name, "%s", base && base[1] ? base + 1 : dir);
    size_t L = strlen(name);
    while (L > 1 && name[L - 1] == '/') name[--L] = 0;
    struct test *t = add_test(name, n);
    snprintf(path, sizeof path, "%s/setup", dir);
    if (stat(path, &st) == 0 && read_file(path, &t->setup) != 0) die(path);
    for (int i = 0; i < n; i++) {
        snprintf(path, sizeof path, "%s/%d", dir, i + 1);
        if (read_file(path, &t->frames[i]) != 0) die(path);
    }
}

/* The unit of work every console cost is compared with on one boot: a
 * chain of 2^21 dependent multiply-adds in user mode, no system call. */
static volatile uint64_t g_sink;

static void unit_work(void) {
    uint64_t x = g_sink | 1;
    for (int i = 0; i < (1 << 21); i++) x = x * 6364136223846793005ull + 1442695040888963407ull;
    g_sink = x;
}

/* Seconds since `from` (a stamp): by the TSC at the idle second's rate,
 * else CLOCK_MONOTONIC. */
static double g_stamps_per_s = 1e9;

static double since(uint64_t from) { return (double)(stamp() - from) / g_stamps_per_s; }

static void gap(int ms) {
    if (ms <= 0) return;
    struct timespec t = {ms / 1000, (long)(ms % 1000) * 1000000L};
    while (nanosleep(&t, &t) < 0 && errno == EINTR) {
    }
}

/* One test: its first frame alone, then as many as fit `budget` seconds,
 * at most `reps`, `gap_ms` asleep between frames. */
static void run_test(struct test *t, long reps, double budget, int gap_ms, uint64_t *samples) {
    size_t bytes = 0, cells = 0;
    if (!t->unit) {
        for (int i = 0; i < t->nframes; i++) {
            bytes += t->frames[i].n;
            cells += cells_of(t->frames[i].p, t->frames[i].n);
        }
        t->bytes = bytes / (size_t)t->nframes;
        t->cells = cells / (size_t)t->nframes;
    }
    t->reps = 0;
    t->total = 0;
    t->least = UINT64_MAX;
    if (budget <= 0) return;
    if (!t->unit) {
        if (t->setup.n) write_all(t->setup.p, t->setup.n);
        else write_all("\033[H\033[2J", 7);
    }
    uint64_t start = stamp();
    long k = 0, target = reps;
    do {
        uint64_t a = stamp();
        if (t->unit) unit_work();
        else write_all(t->frames[k % t->nframes].p, t->frames[k % t->nframes].n);
        uint64_t b = stamp();
        samples[k++] = b - a;
        int pause = t->unit ? 0 : gap_ms;
        if (k == 1) {
            double one = (double)(b - a) / g_stamps_per_s + pause / 1000.0;
            long fit = one > 0 ? (long)(budget / one) : reps;
            if (fit < 1) fit = 1;
            if (fit < target) target = fit;
        }
        if (k < target) gap(pause);
    } while (k < target && since(start) < budget);
    t->reps = k;
    for (long i = 0; i < k; i++) {
        t->total += samples[i];
        if (samples[i] < t->least) t->least = samples[i];
    }
}

/* A test's line of the table, `per_ms` stamps a millisecond. */
static int test_line(char *o, size_t cap, struct test *t, double per_ms) {
    t->ms_mean = t->reps ? (double)t->total / (double)t->reps / per_ms : 0;
    t->ms_min = t->reps ? (double)t->least / per_ms : 0;
    t->mbps = t->ms_mean > 0 ? (double)t->bytes / (t->ms_mean * 1e3) : 0;
    t->us_cell = t->cells ? t->ms_mean * 1e3 / (double)t->cells : 0;
    char uc[32];
    if (t->cells && t->reps) snprintf(uc, sizeof uc, "%.3f", t->us_cell); else snprintf(uc, sizeof uc, "-");
    return snprintf(o, cap, "%-10s %6ld %9zu %7zu %10.3f %10.3f %8.2f %8s\n", t->name, t->reps, t->bytes, t->cells, t->ms_mean,
                    t->ms_min, t->mbps, uc);
}

static void res_put(const char *p, int n) {
    if (g_res < 0 || n <= 0) return;
    ssize_t r = write(g_res, p, (size_t)n);
    (void)r;
}

static void fb_line(char *out, size_t cap, long *fb_w) {
    out[0] = 0;
    *fb_w = 0;
    FILE *f = fopen("/proc/pax-boot", "r");
    if (!f) return;
    char line[512];
    while (fgets(line, sizeof line, f)) {
        if (strncmp(line, "framebuffer ", 12) == 0) {
            line[strcspn(line, "\n")] = 0;
            snprintf(out, cap, "%s", line);
            *fb_w = strtol(line + 12, NULL, 10);
            break;
        }
    }
    fclose(f);
}

static void usage(void) {
    fprintf(stderr, "usage: conspeed [-q] [-n REPS] [-t SECONDS] [-T SECONDS] [-g MS] [-r FILE] [-o TTY] [DIR...]\n");
    exit(2);
}

int main(int argc, char **argv) {
    long reps = 100;
    double secs = 4, total = 60;
    int gap_ms = 10;
    const char *out = NULL, *res = NULL;
    int opt;
    while ((opt = getopt(argc, argv, "qn:t:T:g:r:o:")) != -1) {
        if (opt == 'q') { reps = 3; secs = 1; }
        else if (opt == 'n') { reps = strtol(optarg, NULL, 10); if (reps < 1 || reps > MAXREPS) usage(); }
        else if (opt == 't') { secs = strtod(optarg, NULL); if (!(secs > 0)) usage(); }
        else if (opt == 'T') { total = strtod(optarg, NULL); if (!(total > 0)) usage(); }
        else if (opt == 'g') { gap_ms = (int)strtol(optarg, NULL, 10); if (gap_ms < 0 || gap_ms > 1000) usage(); }
        else if (opt == 'r') res = optarg;
        else if (opt == 'o') out = optarg;
        else usage();
    }
    if (res) {
        g_res = open(res, O_WRONLY | O_CREAT | O_TRUNC | O_NOCTTY, 0644);
        if (g_res < 0) die(res);
    }
    if (out) {
        g_fd = open(out, O_WRONLY | O_NOCTTY);
        if (g_fd < 0) die(out);
    } else {
        g_fd = open("/dev/tty", O_WRONLY | O_NOCTTY);
        if (g_fd < 0 && isatty(2)) g_fd = 2;
        if (g_fd < 0) die("/dev/tty");
    }
    char ttyname_[512] = "?";
    {
        char p[64];
        snprintf(p, sizeof p, "/proc/self/fd/%d", g_fd);
        ssize_t r = readlink(p, ttyname_, sizeof ttyname_ - 1);
        if (r > 0) ttyname_[r] = 0; else snprintf(ttyname_, sizeof ttyname_, "?");
    }
    struct winsize ws;
    int sized = 0;
    int asks[4] = {g_fd, 0, 1, 2};
    for (int i = 0; i < 4 && !sized; i++) {
        if (ioctl(asks[i], TIOCGWINSZ, &ws) == 0 && ws.ws_col > 0 && ws.ws_row > 0) {
            g_cols = ws.ws_col;
            g_rows = ws.ws_row;
            sized = 1;
        }
    }
    if (g_cols > 1000) g_cols = 1000;
    char fb[512];
    long fb_w;
    fb_line(fb, sizeof fb, &fb_w);
    const char *term = getenv("TERM");
    set_restore(term);

    build_synthetic();
    for (int i = optind; i < argc; i++) load_stream(argv[i]);

    uint64_t *samples = malloc(sizeof *samples * (size_t)(reps + 1));
    if (!samples) die("malloc");
    g_tsc = probe_tsc();

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);
    signal(SIGHUP, on_signal);
    signal(SIGQUIT, on_signal);

    /* The TSC's rate is measured while nothing else runs: a second of
     * CLOCK_MONOTONIC spun in user mode before the tests and another after
     * (a console write runs with interrupts off, and ticks that arrive then
     * are lost: the clock is short across the tests themselves, which the
     * `kept` figure shows). */
    uint64_t a0, ac0, a1, ac1, b0, bc0, b1, bc1, m0, c0, m1, c1;
    idle_rate(&a0, &ac0, &a1, &ac1);
    /* The stamps a second, from the idle second before: the bound on the run. */
    double before = g_tsc ? (double)(ac1 - ac0) / ((double)(a1 - a0) / 1e6) : 1e6;
    g_stamps_per_s = before * 1e3;
    {
        char h[1024];
        int n = snprintf(h, sizeof h, "%s: frames to %s, %dx%d cells%s, TERM=%s\n%s%s"
                         "clock: %s %.1f MHz (the idle second before); bounds: the run %.0f s, a test %.1f s, %d ms between frames\n"
                         "%-10s %6s %9s %7s %10s %10s %8s %8s\n", VERSION, ttyname_, g_cols, g_rows,
                         sized ? "" : " (no TIOCGWINSZ: assumed)", term ? term : "(unset)", fb, fb[0] ? "\n" : "",
                         g_tsc ? "TSC at" : "CLOCK_MONOTONIC alone (RDTSC refused), nominal", before / 1e3, total, secs, gap_ms,
                         "test", "frames", "bytes", "cells", "ms mean", "ms least", "MB/s", "us/cell");
        res_put(h, n);
    }
    m0 = mono_ns();
    c0 = g_tsc ? rdtsc() : 0;
    uint64_t run0 = stamp();
    g_entered = 1;
    write_all("\033[?1049h\033[?25l\033[0m", 18);
    for (int i = 0; i < g_ntests; i++) {
        double left = total - since(run0), share = left / (double)(g_ntests - i);
        run_test(&g_tests[i], reps, share < secs ? share : secs, gap_ms, samples);
        char l[256];
        res_put(l, test_line(l, sizeof l, &g_tests[i], before));
    }
    write_all(RESTORE, g_restore_n);
    g_entered = 0;
    tcflush(g_fd, TCIFLUSH);
    m1 = mono_ns();
    c1 = g_tsc ? rdtsc() : 0;
    idle_rate(&b0, &bc0, &b1, &bc1);

    /* Ticks a millisecond: TSC cycles, or nanoseconds without it. */
    double after = g_tsc ? (double)(bc1 - bc0) / ((double)(b1 - b0) / 1e6) : 1e6;
    double per_ms = (before + after) / 2;
    printf("%s: frames to %s, %dx%d cells%s, TERM=%s\n", VERSION, ttyname_, g_cols, g_rows,
           sized ? "" : " (no TIOCGWINSZ: assumed)", term ? term : "(unset)");
    if (fb[0]) printf("%s\n", fb);
    if (g_tsc) {
        double tests_ms = (double)(c1 - c0) / per_ms;
        printf("clock: TSC at %.1f MHz (idle second before %.1f, after %.1f); the tests took %.2f s, of which "
               "CLOCK_MONOTONIC kept %.0f%%\n", per_ms / 1e3, before / 1e3, after / 1e3, tests_ms / 1e3,
               100.0 * ((double)(m1 - m0) / 1e6) / tests_ms);
    } else {
        printf("clock: CLOCK_MONOTONIC alone (RDTSC refused), %.2f s\n", (double)(m1 - m0) / 1e9);
    }
    printf("%-10s %6s %9s %7s %10s %10s %8s %8s\n", "test", "frames", "bytes", "cells", "ms mean", "ms least", "MB/s", "us/cell");
    double byte_us = -1, plain_ms = -1;
    size_t plain_bytes = 0, plain_cells = 0;
    for (int i = 0; i < g_ntests; i++) {
        struct test *t = &g_tests[i];
        char l[256];
        test_line(l, sizeof l, t, per_ms);
        fputs(l, stdout);
        if (!t->reps) continue;
        if (strcmp(t->name, "bytes") == 0) byte_us = t->ms_mean * 1e3 / (double)t->bytes;
        if (strcmp(t->name, "plain") == 0) { plain_ms = t->ms_mean; plain_bytes = t->bytes; plain_cells = t->cells; }
    }
    if (byte_us >= 0) printf("a byte (bytes): %.4f us\n", byte_us);
    if (byte_us >= 0 && plain_ms >= 0 && plain_cells) {
        double cell_us = (plain_ms * 1e3 - byte_us * (double)plain_bytes) / (double)plain_cells;
        int scale = fb_w > 2560 ? 2 : 1;
        double px = 8.0 * 16 * 4 * scale * scale;
        printf("a cell drawn (plain less its bytes): %.3f us, %.0f MB/s of %d-byte cells\n", cell_us,
               cell_us > 0 ? px / cell_us : 0, (int)px);
    }
    {
        char e[256];
        double tests_s = g_tsc ? (double)(c1 - c0) / per_ms / 1e3 : (double)(m1 - m0) / 1e9;
        int n = snprintf(e, sizeof e, "the tests took %.2f s (the TSC at %.1f MHz the idle second after); conspeed: done\n",
                         tests_s, after / 1e3);
        res_put(e, n);
    }
    return 0;
}
