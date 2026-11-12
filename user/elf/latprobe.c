/* px131: latprobe -- how late the kernel lets a process run while another
 * process makes long system calls, on PAX and on Linux.
 *
 *   latprobe [-d SECONDS] [-n ADDR:PORT] [-r ADDR:PORT] [-p PORT] LOAD[:ARG] ...
 *   latprobe true             exit 0 at once (the `exec` load's program)
 *
 * For each LOAD in turn: the load's child makes its setup and says it is
 * ready; the kernel's window is read and so started again
 * (/proc/pax-latency, PAX's instrument; absent on Linux); then for
 * SECONDS (3) three probes run beside the load:
 *   wake   a process that sleeps 1 ms (clock_nanosleep) in a loop and
 *          records how much longer than 1 ms each sleep took;
 *   lo     a UDP echo over loopback, a datagram every 5 ms to a child
 *          bound to 127.0.0.1:PORT (7171), the round trip of each;
 *   net    with -n, the same to ADDR:PORT through the network device (a
 *          host's echo: QEMU's user network forwards 10.0.2.2 to it).
 * Every time is the time-stamp counter's (RDTSC; PAX's CLOCK_MONOTONIC
 * moves in 10 ms ticks and loses the ticks a long call keeps out),
 * calibrated against CLOCK_MONOTONIC over an idle second first. Then the
 * kernel's window is read again and one line printed per load:
 *
 *   latprobe LOAD:ARG: wake n N p50 U p99 U max U; lo n N p50 U max U lost K;
 *     net n N p50 U max U lost K; ops N max U; irqoff U vector V nr N;
 *     schedgap U; ticks D of E; sys NR:U NR:U NR:U
 *
 * (one line, also sent as a datagram to -r's ADDR:PORT when given, for a
 * machine whose console nobody reads; U in microseconds; `net -` without -n; the kernel's fields
 * `-` where /proc/pax-latency is absent or off; `sys` the three system
 * calls with the longest interrupts-off interval in the window).
 *
 * The loads (ARG a size; the defaults in brackets):
 *   idle            nothing (the baseline)
 *   spin            a user-mode loop, no system call
 *   console:N       write(1) of N bytes of 80-column lines [65536]
 *   pty:N           write of N bytes to a pseudo-terminal's slave, a child
 *                   reading its master [16384]
 *   write:MIB       pwrite of MIB MiB to /tmp/latprobe.w, then ftruncate
 *                   to 0, each an op [64]
 *   fork:MIB        fork and wait of a process with MIB MiB touched [128]
 *   exec            fork, execve of /bin/latbig (a program with a large
 *                   loaded segment), wait
 *   mmap:MIB        mmap of MIB MiB anonymous, then munmap [128]
 *   hole:GIB        munmap of GIB GiB of address space where nothing is
 *                   mapped [64]
 *   procmem:MIB     pread of MIB MiB of its own memory through
 *                   /proc/self/mem [8]
 *   random:MIB      getrandom of MIB MiB [8]
 *   pipe:N          write of N bytes to a pipe, a child reading [65536]
 *   tcplo:N         write of N bytes on a loopback TCP connection, a
 *                   child reading [65536]
 *   dir:N           getdents64 over a directory of N names [4000]
 *   poll:N          poll of N descriptors (pipes' ends), no wait [1000]
 *
 * Exit 0 when every load ran, 1 when one could not be set up (named), 2
 * on a usage error. Written from the man pages of the calls named and the
 * Intel SDM vol. 2 (RDTSC); no kernel's source.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/random.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <x86intrin.h>

#ifndef LATBIG_MIB
#define LATBIG_MIB 0
#endif
#if LATBIG_MIB > 0
/* the `exec` load's program: a loaded segment of LATBIG_MIB MiB, bytes in
 * the file (not zeroes left to .bss), so execve reads it all */
#define PAD (LATBIG_MIB * 1048576)
__attribute__((used)) static const unsigned char pad[PAD] = {1, 2, 3, 4};
#endif

#define MAXS (1 << 17)

static uint64_t per_us = 1; /* TSC cycles per microsecond */
static int seconds = 3;
static int lo_port = 7171;
static struct sockaddr_in net_to, report_to;
static int have_net, have_report;
static volatile sig_atomic_t stop;

static uint64_t tsc(void) { return __rdtsc(); }
static uint64_t us_of(uint64_t c) { return c / per_us; }

static void on_term(int s) { (void)s; stop = 1; }

static void calibrate(void) {
    struct timespec a, b, d = {1, 0};
    clock_gettime(CLOCK_MONOTONIC, &a);
    uint64_t t0 = tsc();
    nanosleep(&d, NULL);
    clock_gettime(CLOCK_MONOTONIC, &b);
    uint64_t t1 = tsc();
    uint64_t ns = (uint64_t)(b.tv_sec - a.tv_sec) * 1000000000ull + (uint64_t)b.tv_nsec - (uint64_t)a.tv_nsec;
    per_us = ns >= 1000 ? (t1 - t0) / (ns / 1000) : 1;
    if (per_us == 0) per_us = 1;
}

/* A probe's or a load's summary, through a pipe to the parent. */
struct sum {
    uint64_t n, p50, p99, max, lost;
};

static int cmp32(const void *a, const void *b) {
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return x < y ? -1 : x > y;
}

static struct sum summarize(uint32_t *s, uint64_t n, uint64_t lost) {
    struct sum r = {n, 0, 0, 0, lost};
    if (n) {
        qsort(s, n, sizeof *s, cmp32);
        r.p50 = s[n / 2];
        r.p99 = s[(n * 99) / 100];
        r.max = s[n - 1];
    }
    return r;
}

static void send_sum(int fd, struct sum r) {
    if (write(fd, &r, sizeof r) != (ssize_t)sizeof r) _exit(3);
}

static void sleep_us(long us) {
    struct timespec d = {us / 1000000, (us % 1000000) * 1000};
    nanosleep(&d, NULL);
}

/* wake: 1 ms sleeps until told to stop. */
static void probe_wake(int out) {
    static uint32_t s[MAXS];
    uint64_t n = 0;
    struct timespec d = {0, 1000000};
    while (!stop) {
        uint64_t a = tsc();
        if (clock_nanosleep(CLOCK_MONOTONIC, 0, &d, NULL) != 0 && stop) break;
        uint64_t b = tsc();
        uint64_t took = us_of(b - a);
        if (n < MAXS) s[n++] = (uint32_t)(took > 1000 ? took - 1000 : 0);
    }
    send_sum(out, summarize(s, n, 0));
    _exit(0);
}

/* lo's other end: an echo on 127.0.0.1:lo_port until killed. */
static void echo_server(int ready) {
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in a = {.sin_family = AF_INET, .sin_port = htons((uint16_t)lo_port)};
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    char ok = fd >= 0 && bind(fd, (struct sockaddr *)&a, sizeof a) == 0 ? 'y' : 'n';
    if (write(ready, &ok, 1) != 1 || ok != 'y') _exit(1);
    char b[64];
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof from;
        ssize_t k = recvfrom(fd, b, sizeof b, 0, (struct sockaddr *)&from, &fl);
        if (k > 0) sendto(fd, b, (size_t)k, 0, (struct sockaddr *)&from, fl);
    }
}

/* lo and net: a datagram every 5 ms to `to`, its round trip; 1 s and
 * it is lost. */
static void probe_echo(int out, struct sockaddr_in to) {
    static uint32_t s[MAXS];
    uint64_t n = 0, lost = 0, seq = 0;
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    struct timeval tv = {1, 0};
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv) != 0 ||
        connect(fd, (struct sockaddr *)&to, sizeof to) != 0) {
        send_sum(out, (struct sum){0, 0, 0, 0, ~0ull});
        _exit(1);
    }
    while (!stop) {
        seq++;
        uint64_t a = tsc();
        if (send(fd, &seq, sizeof seq, 0) != (ssize_t)sizeof seq) { lost++; sleep_us(5000); continue; }
        int got = 0;
        while (!stop) {
            uint64_t v = 0;
            ssize_t k = recv(fd, &v, sizeof v, 0);
            if (k == (ssize_t)sizeof v && v == seq) { got = 1; break; }
            if (k < 0) break; /* the timeout, or a signal */
            if (us_of(tsc() - a) > 1000000) break;
        }
        uint64_t b = tsc();
        if (got) { if (n < MAXS) s[n++] = (uint32_t)us_of(b - a); } else if (!stop) lost++;
        sleep_us(5000);
    }
    send_sum(out, summarize(s, n, lost));
    _exit(0);
}

/* ---- the loads ---------------------------------------------------- */

static size_t arg_or(const char *arg, size_t dflt) { return arg && *arg ? (size_t)strtoull(arg, NULL, 10) : dflt; }

static char *filled(size_t n, int lines) {
    char *b = malloc(n ? n : 1);
    if (!b) return NULL;
    for (size_t i = 0; i < n; i++) b[i] = lines && i % 80 == 79 ? '\n' : (char)('a' + i % 26);
    return b;
}

static void drain_fd(int fd) {
    static char b[65536];
    for (;;) if (read(fd, b, sizeof b) < 0 && errno != EINTR) _exit(0);
}

struct load {
    const char *name, *arg;
    int fds[2048];
    int nfds;
    char *buf;
    size_t n;
    void *mem;
    int fd, sock;
    pid_t helper;
    struct pollfd *pfds;
};

/* Each load: its setup (before the window starts) and one op. A setup
 * returns 0, or -1 with a word on stderr. */
static int setup(struct load *L) {
    const char *k = L->name;
    if (!strcmp(k, "idle") || !strcmp(k, "spin") || !strcmp(k, "exec")) return 0;
    if (!strcmp(k, "console")) { L->n = arg_or(L->arg, 65536); return (L->buf = filled(L->n, 1)) ? 0 : -1; }
    if (!strcmp(k, "pty")) {
        L->n = arg_or(L->arg, 16384);
        int m = posix_openpt(O_RDWR | O_NOCTTY);
        if (m < 0 || grantpt(m) || unlockpt(m)) { perror("latprobe: pty"); return -1; }
        L->fd = open(ptsname(m), O_RDWR | O_NOCTTY);
        if (L->fd < 0) { perror("latprobe: pty slave"); return -1; }
        if ((L->helper = fork()) == 0) drain_fd(m);
        close(m);
        return (L->buf = filled(L->n, 1)) ? 0 : -1;
    }
    if (!strcmp(k, "write")) {
        L->n = arg_or(L->arg, 64) << 20;
        L->fd = open("/tmp/latprobe.w", O_RDWR | O_CREAT | O_TRUNC, 0600);
        if (L->fd < 0) { perror("latprobe: /tmp/latprobe.w"); return -1; }
        return (L->buf = filled(L->n, 0)) ? 0 : -1;
    }
    if (!strcmp(k, "fork") || !strcmp(k, "mmap")) {
        L->n = arg_or(L->arg, 128) << 20;
        if (!strcmp(k, "mmap")) return 0;
        L->mem = mmap(NULL, L->n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (L->mem == MAP_FAILED) { perror("latprobe: mmap"); return -1; }
        memset(L->mem, 7, L->n);
        return 0;
    }
    if (!strcmp(k, "hole")) { L->n = arg_or(L->arg, 64) << 30; return 0; }
    if (!strcmp(k, "procmem")) {
        L->n = arg_or(L->arg, 8) << 20;
        L->fd = open("/proc/self/mem", O_RDONLY);
        if (L->fd < 0) { perror("latprobe: /proc/self/mem"); return -1; }
        L->buf = filled(L->n, 0);
        L->mem = malloc(L->n);
        return L->buf && L->mem ? (memset(L->mem, 1, L->n), 0) : -1;
    }
    if (!strcmp(k, "random")) { L->n = arg_or(L->arg, 8) << 20; L->buf = malloc(L->n); return L->buf ? (memset(L->buf, 0, L->n), 0) : -1; }
    if (!strcmp(k, "pipe")) {
        L->n = arg_or(L->arg, 65536);
        int p[2];
        if (pipe(p)) { perror("latprobe: pipe"); return -1; }
        if ((L->helper = fork()) == 0) { close(p[1]); drain_fd(p[0]); }
        close(p[0]);
        L->fd = p[1];
        return (L->buf = filled(L->n, 0)) ? 0 : -1;
    }
    if (!strcmp(k, "tcplo")) {
        L->n = arg_or(L->arg, 65536);
        int ls = socket(AF_INET, SOCK_STREAM, 0), one = 1;
        struct sockaddr_in a = {.sin_family = AF_INET, .sin_port = htons((uint16_t)(lo_port + 1))};
        a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
        if (ls < 0 || bind(ls, (struct sockaddr *)&a, sizeof a) || listen(ls, 1)) { perror("latprobe: tcp listen"); return -1; }
        if ((L->helper = fork()) == 0) { int c = accept(ls, NULL, NULL); if (c < 0) _exit(1); drain_fd(c); }
        L->fd = socket(AF_INET, SOCK_STREAM, 0);
        if (L->fd < 0 || connect(L->fd, (struct sockaddr *)&a, sizeof a)) { perror("latprobe: tcp connect"); return -1; }
        close(ls);
        return (L->buf = filled(L->n, 0)) ? 0 : -1;
    }
    if (!strcmp(k, "dir")) {
        L->n = arg_or(L->arg, 4000);
        char p[64];
        if (mkdir("/tmp/latprobe.d", 0700) && errno != EEXIST) { perror("latprobe: mkdir"); return -1; }
        for (size_t i = 0; i < L->n; i++) {
            snprintf(p, sizeof p, "/tmp/latprobe.d/name-%06zu", i);
            int f = open(p, O_WRONLY | O_CREAT, 0600);
            if (f < 0) { perror("latprobe: dir"); return -1; }
            close(f);
        }
        L->fd = open("/tmp/latprobe.d", O_RDONLY | O_DIRECTORY);
        L->buf = malloc(65536);
        return L->fd >= 0 && L->buf ? 0 : -1;
    }
    if (!strcmp(k, "poll")) {
        L->n = arg_or(L->arg, 1000);
        if (L->n > 2000) L->n = 2000;
        L->pfds = calloc(L->n, sizeof *L->pfds);
        for (size_t i = 0; i + 1 < L->n + 1 && L->pfds; i += 2) {
            int p[2];
            if (pipe(p)) { perror("latprobe: poll's pipes"); return -1; }
            L->pfds[i] = (struct pollfd){p[0], POLLIN, 0};
            if (i + 1 < L->n) L->pfds[i + 1] = (struct pollfd){p[1], POLLIN, 0};
        }
        return L->pfds ? 0 : -1;
    }
    fprintf(stderr, "latprobe: no load %s\n", k);
    return -1;
}

/* One op of the load. */
static void op(struct load *L) {
    const char *k = L->name;
    if (!strcmp(k, "idle")) { sleep_us(100000); return; }
    if (!strcmp(k, "spin")) { uint64_t e = tsc() + 1000 * per_us; while (tsc() < e) {} return; }
    if (!strcmp(k, "console") || !strcmp(k, "pty") || !strcmp(k, "pipe") || !strcmp(k, "tcplo")) {
        size_t done = 0;
        while (done < L->n) {
            ssize_t w = write(!strcmp(k, "console") ? 1 : L->fd, L->buf + done, L->n - done);
            if (w <= 0) break;
            done += (size_t)w;
        }
        return;
    }
    if (!strcmp(k, "write")) {
        if (pwrite(L->fd, L->buf, L->n, 0) < 0) perror("latprobe: pwrite");
        if (ftruncate(L->fd, 0)) perror("latprobe: ftruncate");
        return;
    }
    if (!strcmp(k, "fork") || !strcmp(k, "exec")) {
        pid_t p = fork();
        if (p == 0) {
            if (!strcmp(k, "exec")) { char *av[] = {"latbig", "true", NULL}; execv("/bin/latbig", av); _exit(127); }
            _exit(0);
        }
        if (p > 0) waitpid(p, NULL, 0);
        return;
    }
    if (!strcmp(k, "mmap")) {
        void *m = mmap(NULL, L->n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (m != MAP_FAILED) munmap(m, L->n);
        return;
    }
    if (!strcmp(k, "hole")) { munmap((void *)0x200000000000ull, L->n); return; }
    if (!strcmp(k, "procmem")) { if (pread(L->fd, L->buf, L->n, (off_t)(uintptr_t)L->mem) < 0) perror("latprobe: pread"); return; }
    if (!strcmp(k, "random")) {
        size_t done = 0;
        while (done < L->n) { ssize_t g = getrandom(L->buf + done, L->n - done, 0); if (g <= 0) break; done += (size_t)g; }
        return;
    }
    if (!strcmp(k, "dir")) {
        lseek(L->fd, 0, SEEK_SET);
        while (syscall(SYS_getdents64, L->fd, L->buf, 65536) > 0) {}
        return;
    }
    if (!strcmp(k, "poll")) { poll(L->pfds, L->n, 0); return; }
}

/* The load's child: setup, `r` to the parent, wait for `g`, ops until the
 * deadline, then its summary. */
static void run_load(struct load *L, int out, int go) {
    char c = setup(L) == 0 ? 'r' : 'x';
    if (write(out, &c, 1) != 1 || c != 'r') _exit(1);
    if (read(go, &c, 1) != 1) _exit(1);
    static uint32_t s[MAXS];
    uint64_t n = 0, end = tsc() + (uint64_t)seconds * 1000000ull * per_us;
    while (tsc() < end) {
        uint64_t a = tsc();
        op(L);
        uint64_t b = tsc();
        if (n < MAXS) s[n++] = (uint32_t)us_of(b - a);
    }
    if (L->helper > 0) { kill(L->helper, SIGKILL); waitpid(L->helper, NULL, 0); }
    if (!strcmp(L->name, "write")) unlink("/tmp/latprobe.w");
    send_sum(out, summarize(s, n, 0));
    _exit(0);
}

/* ---- the kernel's window ---------------------------------------- */

struct kwin {
    int have;
    uint64_t irq, vec, nr, gap, td, te;
    uint64_t sys[3][2];
};

static struct kwin read_window(void) {
    struct kwin w;
    memset(&w, 0, sizeof w);
    static char b[8192];
    int fd = open("/proc/pax-latency", O_RDONLY);
    if (fd < 0) return w;
    ssize_t n = 0, k;
    while (n < (ssize_t)sizeof b - 1 && (k = read(fd, b + n, sizeof b - 1 - (size_t)n)) > 0) n += k;
    close(fd);
    b[n > 0 ? n : 0] = 0;
    if (strncmp(b, "latency on", 10)) return w;
    w.have = 1;
    for (char *l = strtok(b, "\n"); l; l = strtok(NULL, "\n")) {
        unsigned long long a, v, r, x;
        if (strstr(l, "since the last read")) {
            if (sscanf(l, "irqoff %llu us vector 0x%llx nr %llu rip 0x%llx", &a, &v, &r, &x) == 4) { w.irq = a; w.vec = v; w.nr = r; }
            else if (sscanf(l, "schedgap %llu us", &a) == 1) w.gap = a;
            else if (sscanf(l, "ticks %llu of %llu", &a, &v) == 2) { w.td = a; w.te = v; }
        } else if (sscanf(l, "sys %llu %llu us", &r, &a) == 2) {
            for (int i = 0; i < 3; i++)
                if (a > w.sys[i][1]) {
                    for (int j = 2; j > i; j--) { w.sys[j][0] = w.sys[j - 1][0]; w.sys[j][1] = w.sys[j - 1][1]; }
                    w.sys[i][0] = r; w.sys[i][1] = a;
                    break;
                }
        }
    }
    return w;
}

/* ---- one load, measured ----------------------------------------- */

/* A line to stdout, and to -r's address when given. */
static void report(const char *line) {
    fputs(line, stdout);
    fflush(stdout);
    if (!have_report) return;
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) return;
    sendto(fd, line, strlen(line), 0, (struct sockaddr *)&report_to, sizeof report_to);
    close(fd);
}

static pid_t spawn(int *rd, void (*body)(int, struct sockaddr_in), struct sockaddr_in to, void (*wake)(int)) {
    int p[2];
    if (pipe(p)) return -1;
    pid_t c = fork();
    if (c == 0) {
        close(p[0]);
        signal(SIGTERM, on_term);
        if (wake) wake(p[1]); else body(p[1], to);
        _exit(0);
    }
    close(p[1]);
    *rd = p[0];
    return c;
}

static struct sum collect(pid_t c, int rd) {
    struct sum r = {0, 0, 0, 0, 0};
    if (c <= 0) return r;
    kill(c, SIGTERM);
    if (read(rd, &r, sizeof r) != (ssize_t)sizeof r) memset(&r, 0, sizeof r);
    waitpid(c, NULL, 0);
    close(rd);
    return r;
}

static int measure(const char *spec) {
    struct load *L = calloc(1, sizeof *L);
    char *name = strdup(spec), *colon = strchr(name, ':');
    if (colon) { *colon = 0; L->arg = colon + 1; }
    L->name = name;
    L->fd = L->sock = -1;
    int lp[2], gp[2];
    if (pipe(lp) || pipe(gp)) return -1;
    fflush(stdout);
    pid_t load = fork();
    if (load == 0) { close(lp[0]); close(gp[1]); run_load(L, lp[1], gp[0]); }
    close(lp[1]);
    close(gp[0]);
    char c = 0;
    if (read(lp[0], &c, 1) != 1 || c != 'r') {
        char l[256];
        snprintf(l, sizeof l, "latprobe %s: setup refused\n", spec);
        report(l);
        waitpid(load, NULL, 0);
        return -1;
    }
    (void)read_window(); /* the window starts here */
    struct sockaddr_in lo = {.sin_family = AF_INET, .sin_port = htons((uint16_t)lo_port)};
    lo.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    int rw, rl, rn = -1;
    pid_t pw = spawn(&rw, NULL, lo, probe_wake);
    pid_t pl = spawn(&rl, probe_echo, lo, NULL);
    pid_t pn = have_net ? spawn(&rn, probe_echo, net_to, NULL) : 0;
    sleep_us(100000);
    if (write(gp[1], "g", 1) != 1) return -1;
    struct sum ls = {0, 0, 0, 0, 0};
    if (read(lp[0], &ls, sizeof ls) != (ssize_t)sizeof ls) memset(&ls, 0, sizeof ls);
    waitpid(load, NULL, 0);
    sleep_us(100000);
    struct sum sw = collect(pw, rw), sl = collect(pl, rl), sn = collect(pn, rn);
    struct kwin k = read_window();
    char line[1024];
    int at = snprintf(line, sizeof line, "latprobe %s: wake n %llu p50 %llu p99 %llu max %llu; lo n %llu p50 %llu max %llu lost %llu; ", spec,
                      (unsigned long long)sw.n, (unsigned long long)sw.p50, (unsigned long long)sw.p99, (unsigned long long)sw.max,
                      (unsigned long long)sl.n, (unsigned long long)sl.p50, (unsigned long long)sl.max, (unsigned long long)sl.lost);
    if (have_net)
        at += snprintf(line + at, sizeof line - (size_t)at, "net n %llu p50 %llu max %llu lost %llu; ", (unsigned long long)sn.n,
                       (unsigned long long)sn.p50, (unsigned long long)sn.max, (unsigned long long)sn.lost);
    else
        at += snprintf(line + at, sizeof line - (size_t)at, "net -; ");
    at += snprintf(line + at, sizeof line - (size_t)at, "ops %llu max %llu; ", (unsigned long long)ls.n, (unsigned long long)ls.max);
    if (k.have)
        snprintf(line + at, sizeof line - (size_t)at, "irqoff %llu vector 0x%llx nr %llu; schedgap %llu; ticks %llu of %llu; sys %llu:%llu %llu:%llu %llu:%llu\n",
                 (unsigned long long)k.irq, (unsigned long long)k.vec, (unsigned long long)k.nr, (unsigned long long)k.gap,
                 (unsigned long long)k.td, (unsigned long long)k.te, (unsigned long long)k.sys[0][0], (unsigned long long)k.sys[0][1],
                 (unsigned long long)k.sys[1][0], (unsigned long long)k.sys[1][1], (unsigned long long)k.sys[2][0], (unsigned long long)k.sys[2][1]);
    else
        snprintf(line + at, sizeof line - (size_t)at, "irqoff -; schedgap -; ticks -; sys -\n");
    report(line);
    fflush(stdout);
    close(lp[0]);
    close(gp[1]);
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "true")) return 0;
    int i = 1;
    for (; i < argc && argv[i][0] == '-'; i += 2) {
        if (i + 1 >= argc) goto usage;
        if (!strcmp(argv[i], "-d")) seconds = atoi(argv[i + 1]);
        else if (!strcmp(argv[i], "-p")) lo_port = atoi(argv[i + 1]);
        else if (!strcmp(argv[i], "-n") || !strcmp(argv[i], "-r")) {
            struct sockaddr_in *to = argv[i][1] == 'n' ? &net_to : &report_to;
            char *h = strdup(argv[i + 1]), *p = strrchr(h, ':');
            if (!p) goto usage;
            *p = 0;
            to->sin_family = AF_INET;
            to->sin_port = htons((uint16_t)atoi(p + 1));
            if (inet_pton(AF_INET, h, &to->sin_addr) != 1) goto usage;
            if (argv[i][1] == 'n') have_net = 1; else have_report = 1;
        } else goto usage;
    }
    if (i >= argc || seconds < 1) goto usage;
    signal(SIGPIPE, SIG_IGN);
    calibrate();
    int rp[2];
    if (pipe(rp)) return 1;
    pid_t srv = fork();
    if (srv == 0) { close(rp[0]); echo_server(rp[1]); }
    close(rp[1]);
    char ok = 0;
    if (read(rp[0], &ok, 1) != 1 || ok != 'y') { printf("latprobe: the loopback echo did not bind port %d\n", lo_port); return 1; }
    char head[128];
    snprintf(head, sizeof head, "latprobe: tsc %llu per us, %d s a load%s\n", (unsigned long long)per_us, seconds, have_net ? ", net echo" : "");
    report(head);
    int bad = 0;
    for (; i < argc; i++)
        if (measure(argv[i])) bad = 1;
    kill(srv, SIGKILL);
    waitpid(srv, NULL, 0);
    report(bad ? "latprobe: end (a load refused)\n" : "latprobe: end\n");
    return bad;
usage:
    fprintf(stderr, "usage: latprobe [-d SECONDS] [-n ADDR:PORT] [-r ADDR:PORT] [-p PORT] LOAD[:ARG] ...\n");
    return 2;
}
