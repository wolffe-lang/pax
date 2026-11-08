/* px108: bench -- the microbenchmarks of den's clone, on PAX and on Linux.
 *
 *   bench syscall            getppid(2), the bare system call
 *   bench pingpong SIZE      a round trip of SIZE bytes between two processes
 *                            over two pipes (pipe(2), fork(2))
 *   bench files DIR [nosync] den's loose install of a 300-byte object (at
 *                            most 6,000 of them: PAX's tree holds 16,384 inodes):
 *                            open(O_CREAT|O_EXCL) a temporary, write, fsync,
 *                            close, link it into DIR/<xx>/, unlink it, fsync
 *                            the two directories (open, fsync, close); a
 *                            subdirectory made per 64 objects
 *   bench miss DIR           stat(2) of a name that is not there, in DIR
 *   bench mmap KIB [BG_MIB]  mmap(2) KIB of anonymous memory, touch a byte a
 *                            page, munmap(2); with BG_MIB of touched memory
 *                            mapped first, so a space-sized cost shows
 *   bench brk KIB [BG_MIB]   sbrk(+KIB), touch, sbrk(-KIB)
 *   bench malloc KIB [BG_MIB] malloc(3), touch, free(3): glibc's choice
 *   bench tcp ADDR PORT      connect(2), read(2) to the end: MB/s
 *   bench cpu                a user-mode integer loop (no system call)
 *
 * Every row first pins itself (and so pingpong's child) to the CPU it is
 * on (sched_getcpu(3), sched_setaffinity(2)): PAX has one CPU, and a
 * Linux reference on one CPU is the fair comparison. A kernel that answers
 * neither (PAX at px108: sched_setaffinity is not served) runs unpinned;
 * the row's line says `cpu <n>` or `cpu -`.
 *
 * Each row repeats its step in batches until at least a second has passed
 * on CLOCK_MONOTONIC (PAX's moves in 10 ms ticks, pax#299), then prints
 *
 *   bench NAME: N in S s: R /s (U us each); user U sys S vcs V ics I
 *
 * user, sys and the switches are getrusage(2)'s, RUSAGE_SELF plus
 * RUSAGE_CHILDREN for pingpong's child. Exit 0, 1 on a failed call (named),
 * 2 on a usage error. Written from the man pages of the calls named.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <sched.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}

static double tv(struct timeval t) { return (double)t.tv_sec + (double)t.tv_usec / 1e6; }

static void die(const char *what) {
    fprintf(stderr, "bench: %s: %s\n", what, strerror(errno));
    exit(1);
}

struct usage { double user, sys; long vcs, ics; };

static struct usage usage_now(int children) {
    struct rusage a, b;
    memset(&b, 0, sizeof b);
    getrusage(RUSAGE_SELF, &a);
    if (children) getrusage(RUSAGE_CHILDREN, &b);
    struct usage u = {tv(a.ru_utime) + tv(b.ru_utime), tv(a.ru_stime) + tv(b.ru_stime),
                      a.ru_nvcsw + b.ru_nvcsw, a.ru_nivcsw + b.ru_nivcsw};
    return u;
}

static int g_cpu = -1;

static void pin(void) {
    int c = sched_getcpu();
    if (c < 0) return;
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(c, &set);
    if (sched_setaffinity(0, sizeof set, &set) == 0) g_cpu = c;
}

static void report(const char *name, long n, double s, struct usage a, struct usage b) {
    char cpu[16];
    if (g_cpu >= 0) snprintf(cpu, sizeof cpu, "%d", g_cpu); else snprintf(cpu, sizeof cpu, "-");
    printf("bench %s: %ld in %.3f s: %.0f /s (%.2f us each); user %.3f sys %.3f vcs %ld ics %ld cpu %s\n", name, n, s,
           (double)n / s, s * 1e6 / (double)n, b.user - a.user, b.sys - a.sys, b.vcs - a.vcs, b.ics - a.ics, cpu);
    fflush(stdout);
}

/* Run step(i) in batches of `batch` until a second has passed. */
typedef void (*step_fn)(long i);

/* Run step(i) in batches of `batch` until a second has passed, or `cap`
 * steps (0: none) have run, whichever is first. */
static void run_capped(const char *name, step_fn step, long batch, long cap) {
    struct usage a = usage_now(0);
    double t0 = now(), t = 0;
    long n = 0;
    do {
        for (long k = 0; k < batch; k++) step(n++);
        t = now() - t0;
    } while (t < 1.0 && (cap == 0 || n < cap));
    report(name, n, t, a, usage_now(0));
}

static void run(const char *name, step_fn step, long batch) { run_capped(name, step, batch, 0); }

static void s_syscall(long i) { (void)i; (void)getppid(); }

static char g_dir[512];
static int g_sync = 1;

static void fsync_path(const char *p) {
    int fd = open(p, O_RDONLY | O_DIRECTORY);
    if (fd < 0) die("open directory");
    if (fsync(fd) < 0) die("fsync directory");
    close(fd);
}

static void s_files(long i) {
    static char body[300];
    char sub[600], tmp[700], dst[700];
    snprintf(sub, sizeof sub, "%s/%02lx", g_dir, (i / 64) & 0xffff);
    if (i % 64 == 0 && mkdir(sub, 0777) < 0 && errno != EEXIST) die("mkdir");
    snprintf(tmp, sizeof tmp, "%s/tmp_obj", sub);
    snprintf(dst, sizeof dst, "%s/obj%ld", sub, i);
    int fd = open(tmp, O_WRONLY | O_CREAT | O_EXCL, 0444);
    if (fd < 0) die("open O_EXCL");
    if (write(fd, body, sizeof body) != (ssize_t)sizeof body) die("write");
    if (g_sync && fsync(fd) < 0) die("fsync");
    if (close(fd) < 0) die("close");
    if (link(tmp, dst) < 0) die("link");
    if (unlink(tmp) < 0) die("unlink");
    if (g_sync) {
        fsync_path(sub);
        fsync_path(g_dir);
    }
}

static void s_miss(long i) {
    char p[600];
    struct stat st;
    snprintf(p, sizeof p, "%s/no-such-%ld", g_dir, i & 1023);
    if (stat(p, &st) == 0 || errno != ENOENT) die("stat of a missing name");
}

static size_t g_bytes;

static void touch(char *p, size_t n) {
    for (size_t k = 0; k < n; k += 4096) p[k] = 1;
}

static void s_mmap(long i) {
    (void)i;
    char *p = mmap(NULL, g_bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) die("mmap");
    touch(p, g_bytes);
    if (munmap(p, g_bytes) < 0) die("munmap");
}

static void s_brk(long i) {
    (void)i;
    char *p = sbrk((intptr_t)g_bytes);
    if (p == (void *)-1) die("sbrk up");
    touch(p, g_bytes);
    if (sbrk(-(intptr_t)g_bytes) == (void *)-1) die("sbrk down");
}

static void s_malloc(long i) {
    (void)i;
    char *p = malloc(g_bytes);
    if (!p) die("malloc");
    touch(p, g_bytes);
    free(p);
}

static volatile uint64_t g_sink;

static void s_cpu(long i) {
    uint64_t x = (uint64_t)i * 0x9e3779b97f4a7c15ull;
    for (int k = 0; k < 1000; k++) x = (x ^ (x >> 29)) * 0xbf58476d1ce4e5b9ull + (uint64_t)k;
    g_sink += x;
}

static void background(const char *mib) {
    if (!mib) return;
    size_t b = (size_t)atol(mib) << 20;
    char *p = mmap(NULL, b, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) die("mmap background");
    touch(p, b);
}

static void full(int fd, char *buf, size_t n, int writing) {
    size_t d = 0;
    while (d < n) {
        ssize_t r = writing ? write(fd, buf + d, n - d) : read(fd, buf + d, n - d);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) die(writing ? "pipe write" : "pipe read");
        d += (size_t)r;
    }
}

static int pingpong(size_t size) {
    int a[2], b[2];
    if (pipe(a) < 0 || pipe(b) < 0) die("pipe");
    char *buf = malloc(size);
    if (!buf) die("malloc");
    memset(buf, 7, size);
    pid_t pid = fork();
    if (pid < 0) die("fork");
    if (pid == 0) {
        close(a[1]);
        close(b[0]);
        for (;;) {
            size_t d = 0;
            while (d < size) {
                ssize_t r = read(a[0], buf + d, size - d);
                if (r < 0 && errno == EINTR) continue;
                if (r == 0) _exit(0);
                if (r < 0) _exit(1);
                d += (size_t)r;
            }
            full(b[1], buf, size, 1);
        }
    }
    close(a[0]);
    close(b[1]);
    struct usage u0 = usage_now(0);
    double t0 = now(), t = 0;
    long n = 0;
    do {
        for (int k = 0; k < 64; k++, n++) {
            full(a[1], buf, size, 1);
            full(b[0], buf, size, 0);
        }
        t = now() - t0;
    } while (t < 1.0);
    close(a[1]);
    int st;
    waitpid(pid, &st, 0);
    char name[64];
    snprintf(name, sizeof name, "pingpong %zu", size);
    report(name, n, t, u0, usage_now(1));
    return 0;
}

static int tcp(const char *addr, const char *port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) die("socket");
    struct sockaddr_in sa;
    memset(&sa, 0, sizeof sa);
    sa.sin_family = AF_INET;
    sa.sin_port = htons((uint16_t)atoi(port));
    if (inet_pton(AF_INET, addr, &sa.sin_addr) != 1) { errno = EINVAL; die("address"); }
    struct usage u0 = usage_now(0);
    double t0 = now();
    if (connect(fd, (struct sockaddr *)&sa, sizeof sa) < 0) die("connect");
    static char buf[65536];
    long total = 0;
    for (;;) {
        ssize_t r = read(fd, buf, sizeof buf);
        if (r < 0 && errno == EINTR) continue;
        if (r < 0) die("read");
        if (r == 0) break;
        total += r;
    }
    double t = now() - t0;
    struct usage u1 = usage_now(0);
    printf("bench tcp: %ld bytes in %.3f s: %.2f MB/s; user %.3f sys %.3f vcs %ld ics %ld cpu %d\n", total, t,
           (double)total / t / 1e6, u1.user - u0.user, u1.sys - u0.sys, u1.vcs - u0.vcs, u1.ics - u0.ics, g_cpu);
    close(fd);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) goto usage;
    pin();
    const char *w = argv[1];
    if (strcmp(w, "syscall") == 0) { run("syscall", s_syscall, 1000); return 0; }
    if (strcmp(w, "cpu") == 0) { run("cpu", s_cpu, 1000); return 0; }
    if (strcmp(w, "pingpong") == 0 && argc == 3) return pingpong((size_t)atol(argv[2]));
    if (strcmp(w, "tcp") == 0 && argc == 4) return tcp(argv[2], argv[3]);
    if ((strcmp(w, "files") == 0 || strcmp(w, "miss") == 0) && argc >= 3) {
        snprintf(g_dir, sizeof g_dir, "%s", argv[2]);
        if (mkdir(g_dir, 0777) < 0 && errno != EEXIST) die("mkdir DIR");
        if (w[0] == 'm') { run("miss", s_miss, 100); return 0; }
        g_sync = !(argc >= 4 && strcmp(argv[3], "nosync") == 0);
        /* At most 6,000 objects a row (two rows: 12,000 and their
         * directories): PAX's file tree holds 16,384 inodes in all
         * (kernel/tree), and the row is a rate, not a capacity. */
        run_capped(g_sync ? "files" : "files nosync", s_files, 64, 6000);
        return 0;
    }
    if ((strcmp(w, "mmap") == 0 || strcmp(w, "brk") == 0 || strcmp(w, "malloc") == 0) && argc >= 3) {
        g_bytes = (size_t)atol(argv[2]) << 10;
        background(argc >= 4 ? argv[3] : NULL);
        char name[64];
        snprintf(name, sizeof name, "%s %s KiB%s%s%s", w, argv[2], argc >= 4 ? " over " : "",
                 argc >= 4 ? argv[3] : "", argc >= 4 ? " MiB" : "");
        run(name, w[0] == 'm' && w[1] == 'm' ? s_mmap : w[0] == 'b' ? s_brk : s_malloc, 16);
        return 0;
    }
usage:
    fprintf(stderr, "usage: bench syscall|cpu|pingpong SIZE|files DIR [nosync]|miss DIR|mmap KIB [BG]|brk KIB [BG]|malloc KIB [BG]|tcp ADDR PORT\n");
    return 2;
}
