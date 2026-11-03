/* px88: getrusage (pax#185, #248), asked of the kernel and of Linux by a
 * static musl program: RUSAGE_SELF, RUSAGE_CHILDREN and RUSAGE_THREAD,
 * the refusals, every field of struct rusage, and wait4's rusage. The
 * numbers differ between any two machines, so each row says what a
 * number did (`grew by at least …: yes`) and the line is the same on
 * both kernels when the kernel keeps the field as Linux does. A `~` line
 * is a field PAX does not keep where Linux does (ru_minflt: Linux counts
 * a fault at each first touch; PAX maps anonymous memory at the call and
 * takes none): its value is printed there, and tests/mpx5-forks holds
 * PAX's to its text.
 *
 *   usage              every row, then `usage: done`
 *   usage exec N       the exec row's new image (internal)
 *   usage peek         the vfork row's new image (internal)
 *
 * No pid, time or address is printed. Built by tools/mkforks with
 * Ubuntu's musl-gcc (`-static -no-pie`), never from musl's source.
 *
 * Written from getrusage(2) (the fields, which Linux leaves unmaintained,
 * RUSAGE_THREAD, RUSAGE_CHILDREN's waited-for descendants and their
 * largest resident set, the SIGCHLD rule), wait4(2), fork(2) (a child's
 * usage starts at zero), execve(2), POSIX.1-2024 (XSH getrusage,
 * sys/resource.h, sched_yield) and black-box Linux (notes/px88/linux/:
 * the exploration probe's numbers on hasu's kernel). No C library's or
 * kernel's source was read. Written for this lane. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;
static const char *self = "/bin/usage";

static void say(const char *fmt, ...) {
    char b[1024];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1) n = sizeof b - 1;
    int o = 0;
    while (o < n) {
        ssize_t w = write(1, b + o, n - o);
        if (w <= 0) break;
        o += w;
    }
}

static const char *yes(int c) { return c ? "yes" : "no"; }

/* getrusage as the system call answers it: 0, or -errno. */
static long ru(long who, struct rusage *r) {
    long v = syscall(SYS_getrusage, who, r);
    return v == -1 ? -errno : v;
}
static struct rusage get(int who) {
    struct rusage r;
    memset(&r, 0x55, sizeof r);
    ru(who, &r);
    return r;
}
static long ms(struct timeval t) { return t.tv_sec * 1000 + t.tv_usec / 1000; }

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}
/* Spin in ring 3 for `s` seconds of CLOCK_MONOTONIC: user work between
 * the clock's reads (PAX has no vDSO, so each read is a system call). */
static volatile unsigned long sink;
static void spin(double s) {
    double e = now() + s;
    do {
        for (unsigned long i = 0; i < 200000; i++) sink += i;
    } while (now() < e);
}
static void touch(char *p, size_t n) {
    for (size_t i = 0; i < n; i += 4096) p[i] = 1;
}

/* The fields getrusage(2) calls unmaintained on Linux. */
static int unmaintained_zero(struct rusage r) {
    return r.ru_ixrss == 0 && r.ru_idrss == 0 && r.ru_isrss == 0 && r.ru_nswap == 0 && r.ru_msgsnd == 0 &&
           r.ru_msgrcv == 0 && r.ru_nsignals == 0;
}
static int all_zero(struct rusage r) {
    return ms(r.ru_utime) == 0 && ms(r.ru_stime) == 0 && r.ru_maxrss == 0 && r.ru_minflt == 0 &&
           r.ru_majflt == 0 && r.ru_inblock == 0 && r.ru_oublock == 0 && r.ru_nvcsw == 0 && r.ru_nivcsw == 0 &&
           unmaintained_zero(r);
}

/* G: the call itself. */
static void call_rows(void) {
    struct rusage r;
    say("getrusage: RUSAGE_SELF %ld, RUSAGE_CHILDREN %ld, RUSAGE_THREAD %ld\n", ru(RUSAGE_SELF, &r),
        ru(RUSAGE_CHILDREN, &r), ru(RUSAGE_THREAD, &r));
    say("getrusage: who 5 %ld, who -2 %ld, who 2 %ld\n", ru(5, &r), ru(-2, &r), ru(2, &r));
    say("getrusage: who 0x100000000 %ld, who 0xffffffff %ld\n", ru(0x100000000L, &r), ru(0xffffffffL, &r));
    say("getrusage: a NULL buffer %ld, a buffer at 8 %ld, who 5 with a NULL buffer %ld\n", ru(RUSAGE_SELF, 0),
        ru(RUSAGE_CHILDREN, (struct rusage *)8), ru(5, 0));
    struct rusage s = get(RUSAGE_SELF), c = get(RUSAGE_CHILDREN), t = get(RUSAGE_THREAD);
    say("getrusage: the unmaintained fields 0 (ixrss idrss isrss nswap msgsnd msgrcv nsignals): self %s, children %s, thread %s\n",
        yes(unmaintained_zero(s)), yes(unmaintained_zero(c)), yes(unmaintained_zero(t)));
    say("getrusage: majflt, inblock and oublock 0: self %s, children %s, thread %s\n",
        yes(s.ru_majflt == 0 && s.ru_inblock == 0 && s.ru_oublock == 0),
        yes(c.ru_majflt == 0 && c.ru_inblock == 0 && c.ru_oublock == 0),
        yes(t.ru_majflt == 0 && t.ru_inblock == 0 && t.ru_oublock == 0));
    say("getrusage: before any child, the children's all 0: %s\n", yes(all_zero(c)));
    say("getrusage: the times' microseconds below a second: %s\n",
        yes(s.ru_utime.tv_usec >= 0 && s.ru_utime.tv_usec < 1000000 && s.ru_stime.tv_usec >= 0 &&
            s.ru_stime.tv_usec < 1000000));
    say("~minflt: self %ld\n", s.ru_minflt);
}

/* M: the largest resident set. */
static void maxrss_rows(void) {
    /* A process's peak outlives exec (the exec rows), so the start is the
     * peak of whatever ran before this image in the process: on Linux's side
     * tools/linux-tree's Python, on PAX nothing (the kernel starts it) or
     * `as`. The rows below hold the peak itself, not its growth from there. */
    long b0 = get(RUSAGE_SELF).ru_maxrss;
    say("maxrss: at the start, more than 0 and under 48 MiB: %s\n", yes(b0 > 0 && b0 < 49152));
    char *p = malloc(64 << 20);
    touch(p, 64 << 20);
    long b1 = get(RUSAGE_SELF).ru_maxrss;
    /* Linux counts resident pages approximately (64 MiB touched read as
     * 64700 KiB more on hasu's 7.2.4, notes/px88/linux/): 4 MiB each way */
    say("maxrss: 64 MiB touched: at least 60 MiB %s, at most 68 MiB above the start %s\n", yes(b1 >= 61440),
        yes(b1 <= b0 + 69632));
    free(p);
    long b2 = get(RUSAGE_SELF).ru_maxrss;
    say("maxrss: after the 64 MiB was freed, unchanged: %s\n", yes(b2 == b1));
    p = malloc(16 << 20);
    touch(p, 16 << 20);
    long b3 = get(RUSAGE_SELF).ru_maxrss;
    free(p);
    say("maxrss: 16 MiB more after the free, unchanged: %s\n", yes(b3 == b1));
    long t = get(RUSAGE_THREAD).ru_maxrss;
    say("maxrss: RUSAGE_THREAD's is RUSAGE_SELF's: %s\n", yes(t == b3));
}

/* C: children, and wait4's rusage. */
static void child_rows(void) {
    long mine = get(RUSAGE_SELF).ru_maxrss;
    int fd[2];
    pipe(fd);
    pid_t p = fork();
    if (p == 0) {
        struct rusage s = get(RUSAGE_SELF), c = get(RUSAGE_CHILDREN);
        int r[4] = { ms(s.ru_utime) < 10 && ms(s.ru_stime) < 10, all_zero(c), s.ru_maxrss < mine,
                     s.ru_nvcsw + s.ru_nivcsw < 5 };
        write(fd[1], r, sizeof r);
        char *q = malloc(32 << 20);
        touch(q, 32 << 20);
        spin(0.2);
        _exit(3);
    }
    int r[4] = { 0 };
    close(fd[1]); /* the child's end only: a kernel that cannot fork ends the read, never hangs it */
    read(fd[0], r, sizeof r);
    close(fd[0]);
    struct rusage w, c0 = get(RUSAGE_CHILDREN);
    memset(&w, 0x55, sizeof w);
    int st = 0;
    pid_t got = wait4(p, &st, 0, &w);
    struct rusage c1 = get(RUSAGE_CHILDREN);
    say("fork: the child's own times under 10 ms at its start: %s; its children's all 0: %s\n", yes(r[0]), yes(r[1]));
    say("fork: the child's maxrss at its start under the parent's peak: %s; under 5 switches: %s\n", yes(r[2]),
        yes(r[3]));
    say("wait4: %s, status %d\n", yes(got == p), WEXITSTATUS(st));
    say("wait4: the child's rusage: maxrss at least 28 MiB %s, utime at least 100 ms %s, unmaintained 0 %s\n",
        yes(w.ru_maxrss >= 28672), yes(ms(w.ru_utime) >= 100), yes(unmaintained_zero(w)));
    say("children: before the wait, all 0: %s\n", yes(all_zero(c0)));
    say("children: after it, maxrss the child's %s, utime the child's %s, stime the child's %s\n",
        yes(c1.ru_maxrss == w.ru_maxrss), yes(ms(c1.ru_utime) == ms(w.ru_utime)), yes(ms(c1.ru_stime) == ms(w.ru_stime)));
    say("children: the switches the child's: %s\n", yes(c1.ru_nvcsw == w.ru_nvcsw && c1.ru_nivcsw == w.ru_nivcsw));

    /* a grandchild larger than its parent */
    pipe(fd);
    p = fork();
    if (p == 0) {
        pid_t q = fork();
        if (q == 0) {
            char *m = malloc(48 << 20);
            touch(m, 48 << 20);
            _exit(0);
        }
        struct rusage before = get(RUSAGE_CHILDREN);
        waitpid(q, 0, 0);
        struct rusage after = get(RUSAGE_CHILDREN);
        int v[2] = { before.ru_maxrss == 0, after.ru_maxrss >= 45056 };
        write(fd[1], v, sizeof v);
        _exit(0);
    }
    int v[2] = { 0 };
    close(fd[1]); /* as above */
    read(fd[0], v, sizeof v);
    close(fd[0]);
    memset(&w, 0x55, sizeof w);
    wait4(p, &st, 0, &w);
    struct rusage c2 = get(RUSAGE_CHILDREN);
    say("grandchild: the middle child's children before its wait 0 %s, after it at least 44 MiB %s\n", yes(v[0]),
        yes(v[1]));
    say("grandchild: wait4 of the middle child: maxrss at least 44 MiB %s, under 28 MiB %s\n",
        yes(w.ru_maxrss >= 45056), yes(w.ru_maxrss < 28672));
    say("grandchild: the top's children: maxrss at least 44 MiB %s\n", yes(c2.ru_maxrss >= 45056));
}

/* X: exec. The new image is this program again (`exec` or `small`). */
static int exec_image(int argc, char **argv) {
    (void)argc;
    struct rusage s = get(RUSAGE_SELF);
    long big = atol(argv[2]);
    say("exec: the old image's maxrss at least 36 MiB: %s; the new image's at least the old one's: %s\n",
        yes(big >= 36864), yes(s.ru_maxrss >= big));
    say("exec: the new image's utime at least the old one's 100 ms spin: %s\n", yes(ms(s.ru_utime) >= 100));
    return 0;
}

/* V: a vfork child that execs (posix_spawn's way): the space it borrowed
 * is its parent's, and Linux counts that space's peak in the child
 * (measured: the exploration's vfork child read its parent's 65440 KiB). */
static int peek_image(void) {
    say("vfork: the exec'd child's maxrss at least 60 MiB, its parent's peak: %s\n",
        yes(get(RUSAGE_SELF).ru_maxrss >= 61440));
    return 0;
}

static void vfork_rows(void) {
    long peak = get(RUSAGE_SELF).ru_maxrss;
    long kids = get(RUSAGE_CHILDREN).ru_maxrss;
    pid_t p = vfork();
    if (p == 0) {
        char *av[] = { "usage", "peek", 0 };
        execve(self, av, environ);
        _exit(99);
    }
    int st = 0;
    waitpid(p, &st, 0);
    struct rusage c = get(RUSAGE_CHILDREN);
    say("vfork: the parent's peak at least 60 MiB %s, its children's under it before %s; status %d\n",
        yes(peak >= 61440), yes(kids < 61440), WEXITSTATUS(st));
    say("vfork: then the children's maxrss at least 60 MiB: %s\n", yes(c.ru_maxrss >= 61440));
}

static void exec_rows(void) {
    pid_t p = fork();
    if (p == 0) {
        char *q = malloc(40 << 20);
        touch(q, 40 << 20);
        spin(0.15);
        char big[24];
        snprintf(big, sizeof big, "%ld", get(RUSAGE_SELF).ru_maxrss);
        char *av[] = { "usage", "exec", big, 0 };
        execve(self, av, environ);
        _exit(99);
    }
    int st = 0;
    waitpid(p, &st, 0);
    say("exec: %d\n", WEXITSTATUS(st));
}

/* T: the times. */
static void time_rows(void) {
    struct rusage a = get(RUSAGE_SELF);
    double t0 = now();
    spin(0.3);
    double wall = (now() - t0) * 1000;
    struct rusage b = get(RUSAGE_SELF);
    long du = ms(b.ru_utime) - ms(a.ru_utime), ds = ms(b.ru_stime) - ms(a.ru_stime);
    say("utime: a 300 ms spin: grew by at least 150 ms %s, by at most its wall time and 20 ms %s\n", yes(du >= 150),
        yes(du <= wall + 20));
    say("stime: the spin: grew by under 50 ms %s\n", yes(ds < 50));
    int z = open("/dev/zero", O_RDONLY);
    char *buf = malloc(1 << 20);
    a = get(RUSAGE_SELF);
    t0 = now();
    long n = 0;
    while (now() < t0 + 0.3) {
        if (read(z, buf, 1 << 20) == 1 << 20) n++;
    }
    b = get(RUSAGE_SELF);
    close(z);
    free(buf);
    du = ms(b.ru_utime) - ms(a.ru_utime);
    ds = ms(b.ru_stime) - ms(a.ru_stime);
    say("stime: 300 ms of 1 MiB reads of /dev/zero: grew by at least 100 ms %s, more than utime %s, reads %s\n",
        yes(ds >= 100), yes(ds > du), yes(n > 0));
}

/* S: the switches. */
static void switch_rows(void) {
    struct rusage a = get(RUSAGE_SELF);
    for (int i = 0; i < 10; i++) {
        struct timespec d = { 0, 5000000 };
        nanosleep(&d, 0);
    }
    struct rusage b = get(RUSAGE_SELF);
    say("nvcsw: ten 5 ms sleeps: grew by at least 10 %s\n", yes(b.ru_nvcsw - a.ru_nvcsw >= 10));
    cpu_set_t set;
    CPU_ZERO(&set);
    int cpus = sched_getaffinity(0, sizeof set, &set) == 0 ? CPU_COUNT(&set) : 1;
    int k = 2 * cpus;
    if (k > 32) k = 32;
    pid_t kid[32];
    for (int i = 0; i < k; i++) {
        kid[i] = fork();
        if (kid[i] == 0) {
            spin(0.6);
            _exit(0);
        }
    }
    a = get(RUSAGE_SELF);
    spin(0.4);
    b = get(RUSAGE_SELF);
    for (int i = 0; i < k; i++) waitpid(kid[i], 0, 0);
    say("nivcsw: a 400 ms spin beside two spinners a CPU: grew by at least 2 %s\n",
        yes(b.ru_nivcsw - a.ru_nivcsw >= 2));
    struct rusage c = get(RUSAGE_CHILDREN);
    say("children: the spinners' utime counted: %s\n", yes(ms(c.ru_utime) >= 300));
}

/* R: a second thread. */
static long spun_ms;
static void *spinner(void *u) {
    (void)u;
    struct rusage a = get(RUSAGE_THREAD);
    spin(0.2);
    struct rusage b = get(RUSAGE_THREAD);
    spun_ms = ms(b.ru_utime) - ms(a.ru_utime);
    return 0;
}
static void thread_rows(void) {
    struct rusage s0 = get(RUSAGE_SELF), t0 = get(RUSAGE_THREAD);
    pthread_t t;
    int c = pthread_create(&t, 0, spinner, 0);
    pthread_join(t, 0);
    struct rusage s1 = get(RUSAGE_SELF), t1 = get(RUSAGE_THREAD);
    long d = spun_ms;
    say("thread: pthread_create %d; the second thread's own utime over its 200 ms spin: at least 100 ms %s\n", c,
        yes(d >= 100));
    say("thread: the joining thread's own utime grew by under 50 ms %s; the process's by at least 100 ms %s\n",
        yes(ms(t1.ru_utime) - ms(t0.ru_utime) < 50), yes(ms(s1.ru_utime) - ms(s0.ru_utime) >= 100));
    say("thread: RUSAGE_THREAD's utime at most RUSAGE_SELF's: %s\n", yes(ms(t1.ru_utime) <= ms(s1.ru_utime)));
}

/* I: children whose SIGCHLD is ignored are reaped by the kernel and not
 * counted (getrusage(2)). */
static void ignored_rows(void) {
    struct rusage c0 = get(RUSAGE_CHILDREN);
    signal(SIGCHLD, SIG_IGN);
    pid_t p = fork();
    if (p == 0) {
        char *m = malloc(64 << 20);
        touch(m, 64 << 20);
        spin(0.2);
        _exit(0);
    }
    int st = 0;
    errno = 0;
    long w = waitpid(p, &st, 0);
    say("ignored: SIGCHLD ignored: waitpid %ld %d\n", w, -errno);
    struct rusage c1 = get(RUSAGE_CHILDREN);
    signal(SIGCHLD, SIG_DFL);
    say("ignored: the child not counted: maxrss unchanged %s, utime unchanged %s\n", yes(c1.ru_maxrss == c0.ru_maxrss),
        yes(ms(c1.ru_utime) == ms(c0.ru_utime)));
}

int main(int argc, char **argv) {
    if (argc > 2 && strcmp(argv[1], "exec") == 0) return exec_image(argc, argv);
    if (argc > 1 && strcmp(argv[1], "peek") == 0) return peek_image();
    say("usage: as %s\n", getuid() == 0 ? "root" : "a user");
    call_rows();
    maxrss_rows();
    child_rows();
    exec_rows();
    vfork_rows();
    time_rows();
    switch_rows();
    thread_rows();
    ignored_rows();
    struct rusage s = get(RUSAGE_SELF), c = get(RUSAGE_CHILDREN), t = get(RUSAGE_THREAD);
    say("getrusage: at the end, the unmaintained fields still 0: %s %s %s\n", yes(unmaintained_zero(s)),
        yes(unmaintained_zero(c)), yes(unmaintained_zero(t)));
    say("~minflt: at the end, self %s, children %s\n", s.ru_minflt > 0 ? "counted" : "0", c.ru_minflt > 0 ? "counted" : "0");
    say("usage: done\n");
    return 0;
}
