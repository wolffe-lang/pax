/* px126: how many processes and threads PAX holds at once, and what it
 * costs to run among many. PAX's own limits, asked of the kernel; no Linux
 * side (Linux's limits are its own: pid_max, threads-max, RLIMIT_NPROC).
 * Run as the first program on PAX's console, one mode an image
 * (tests/mpx5-slots).
 *
 *   slotprobe threads          threads (raw clone, small stacks) until one
 *                              is refused; three more asked; all joined;
 *                              the table filled a second time
 *   slotprobe forks N          N children alive at once, each blocked on a
 *                              pipe; released; reaped with their statuses
 *   slotprobe fill             children until a fork is refused (the
 *                              machine's memory or the table, whichever
 *                              comes first); released; reaped
 *   slotprobe reuse R B        R rounds of B forks alive at once, then R
 *                              rounds of B threads: each reaped or joined;
 *                              pids never reused
 *   slotprobe wolf N           N wolf programs (/bin/sha256sum) alive at
 *                              once, each on its own pipe; each fed 64 KiB;
 *                              every digest read and every one reaped
 *   slotprobe ptys N           N ptys, each a session whose leader is pelt
 *                              (/bin/sh -c 'cat; echo bye<i>') with cat in
 *                              its foreground; a line through each cat,
 *                              then end of file; every leader reaped
 *   slotprobe switch M         N processes yielding, N = 16, 64 and M,
 *                              three interleaved rounds: the children's
 *                              CPU time (getrusage) a yield
 *   slotprobe herd M           a pipe ping-pong's round trip with W
 *                              processes parked in a pipe read, W = 0, 64
 *                              and M (measured)
 *
 * Every result line starts with its mode's name and a colon. No time is
 * asserted by the probe: tests/mpx5-slots reads the numbers.
 *
 * Written from clone(2), fork(2), wait(2), futex(2), pipe(2),
 * sched_yield(2), getrusage(2), clock_gettime(2), pty(7), posix_openpt(3),
 * unlockpt(3), ptsname(3), ioctl_tty(2), proc_pid_status(5),
 * proc_pid_stat(5) (man-pages 6.7) and POSIX.1-2024 (XSH fork, waitpid,
 * setsid, XBD chapter 11); the pty idioms of px111's user/elf/ptyprobe.c.
 * No C library's, kernel's or shell's source was read. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/futex.h>
#include <poll.h>
#include <sched.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static const char *ename(int e) {
    switch (e) {
    case EAGAIN: return "EAGAIN";
    case ENOMEM: return "ENOMEM";
    case EINVAL: return "EINVAL";
    case ENOSYS: return "ENOSYS";
    case EPERM: return "EPERM";
    case EMFILE: return "EMFILE";
    case ENFILE: return "ENFILE";
    case ECHILD: return "ECHILD";
    case EINTR: return "EINTR";
    case EIO: return "EIO";
    default: {
        static char b[16];
        snprintf(b, sizeof b, "errno %d", e);
        return b;
    }
    }
}

static void say(const char *f, ...) {
    va_list a;
    va_start(a, f);
    vprintf(f, a);
    va_end(a);
    fflush(stdout);
}

static long now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000000000L + t.tv_nsec;
}

static void nap(int ms) {
    struct timespec ts = {ms / 1000, (long)(ms % 1000) * 1000000L};
    while (nanosleep(&ts, &ts) < 0 && errno == EINTR) {}
}

/* The children's CPU time so far (getrusage RUSAGE_CHILDREN), ns. */
static long kids_cpu_ns(void) {
    struct rusage u;
    getrusage(RUSAGE_CHILDREN, &u);
    return (u.ru_utime.tv_sec + u.ru_stime.tv_sec) * 1000000000L + (u.ru_utime.tv_usec + u.ru_stime.tv_usec) * 1000L;
}

/* --- raw system calls, for threads that share the caller's TLS (no errno) -- */

static long raw6(long n, long a, long b, long c, long d, long e, long f) {
    long r;
    register long r10 __asm__("r10") = d;
    register long r8 __asm__("r8") = e;
    register long r9 __asm__("r9") = f;
    __asm__ volatile("syscall" : "=a"(r) : "a"(n), "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8), "r"(r9) : "rcx", "r11", "memory");
    return r;
}

/* --- threads -------------------------------------------------------------- */

#define MAXT 1100
#define TSTACK 8192
static volatile int go_word;
static volatile int tids[MAXT];
static char *stacks;

/* A thread: waits on `go_word` until it is not 0, then ends (exit, 60:
 * this thread only). Raw calls only: it shares the caller's TLS. */
static int parked(void *arg) {
    (void)arg;
    while (__atomic_load_n(&go_word, __ATOMIC_ACQUIRE) == 0)
        raw6(SYS_futex, (long)&go_word, FUTEX_WAIT_PRIVATE, 0, 0, 0, 0);
    raw6(SYS_exit, 0, 0, 0, 0, 0, 0);
    return 0;
}

static const int TFLAGS = CLONE_VM | CLONE_FS | CLONE_FILES | CLONE_SIGHAND | CLONE_THREAD | CLONE_SYSVSEM |
                          CLONE_PARENT_SETTID | CLONE_CHILD_CLEARTID;

/* Threads into tids[from..] until `want` are made or one is refused: how
 * many; `*err` the refusal's errno (0 none). */
static int make_threads(int from, int want, int *err) {
    *err = 0;
    int n = 0;
    while (n < want && from + n < MAXT) {
        int i = from + n;
        tids[i] = -1;
        int r = clone(parked, stacks + (size_t)(i + 1) * TSTACK, TFLAGS, 0, (pid_t *)&tids[i], 0, (pid_t *)&tids[i]);
        if (r < 0) {
            *err = errno;
            tids[i] = 0;
            break;
        }
        n++;
    }
    return n;
}

/* Every thread made released and joined (its clear-child-tid word 0;
 * the wait has a timeout, so a wake the kernel does not send costs time,
 * never a hang). */
static int join_threads(int n) {
    __atomic_store_n(&go_word, 1, __ATOMIC_RELEASE);
    syscall(SYS_futex, &go_word, FUTEX_WAKE_PRIVATE, INT_MAX, 0, 0, 0);
    int joined = 0;
    for (int i = 0; i < n; i++) {
        int v;
        while ((v = tids[i]) != 0) {
            struct timespec ts = {0, 100000000L};
            syscall(SYS_futex, &tids[i], FUTEX_WAIT, v, &ts, 0, 0);
        }
        joined++;
    }
    go_word = 0;
    return joined;
}

static int threads_mode(void) {
    stacks = mmap(0, (size_t)(MAXT + 1) * TSTACK, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (stacks == MAP_FAILED) {
        say("threads: no stacks: %s\n", ename(errno));
        return 1;
    }
    for (int round = 1; round <= 2; round++) {
        int err;
        int n = make_threads(0, MAXT, &err);
        int again = 0, eagain = 0;
        if (err != 0) {
            for (int k = 0; k < 3; k++) {
                int e2;
                again++;
                if (make_threads(n, 1, &e2) == 1) n++; /* a slot came free: one more thread */
                else if (e2 == EAGAIN) eagain++;
            }
        }
        say("threads: round %d: made %d, then clone answered %s; %d more asked, %d answered EAGAIN\n", round, n,
            err ? ename(err) : "nothing (the probe's own limit)", again, eagain);
        int j = join_threads(n);
        say("threads: round %d: joined %d of %d\n", round, j, n);
    }
    return 0;
}

/* --- forks ------------------------------------------------------------------ */

static pid_t kids[8192];

/* Children blocked reading `rd` until it ends, each exiting with i % 100,
 * until `want` are made or a fork is refused: how many; `*err` its
 * errno. */
static int make_kids(int want, int rd, int wr, int *err) {
    *err = 0;
    int n = 0;
    while (n < want && n < (int)(sizeof kids / sizeof kids[0])) {
        pid_t p = fork();
        if (p == 0) {
            close(wr);
            char c;
            while (read(rd, &c, 1) < 0 && errno == EINTR) {}
            _exit(n % 100);
        }
        if (p < 0) {
            *err = errno;
            break;
        }
        kids[n++] = p;
    }
    return n;
}

/* Reap the n children: how many with the status they were made to give. */
static int reap_kids(int n) {
    int right = 0;
    for (int i = 0; i < n; i++) {
        int st;
        pid_t r;
        while ((r = waitpid(kids[i], &st, 0)) < 0 && errno == EINTR) {}
        if (r == kids[i] && WIFEXITED(st) && WEXITSTATUS(st) == i % 100) right++;
    }
    return right;
}

/* None of the n children has ended yet. */
static int all_alive(int n) {
    int st;
    for (int i = 0; i < n; i++)
        if (waitpid(kids[i], &st, WNOHANG) != 0) return 0;
    return 1;
}

static int forks_mode(int want, int fill) {
    int p[2];
    if (pipe(p) < 0) {
        say("forks: no pipe: %s\n", ename(errno));
        return 1;
    }
    int err;
    int n = make_kids(want, p[0], p[1], &err);
    const char *mode = fill ? "fill" : "forks";
    int alive = all_alive(n);
    if (fill)
        say("%s: %d children alive at once, then fork answered %s\n", mode, n, err ? ename(err) : "nothing");
    else
        say("%s: %d of %d asked alive at once (%s)%s%s\n", mode, n, want, alive ? "none ended" : "some ended",
            err ? ", then fork answered " : "", err ? ename(err) : "");
    close(p[1]);
    int right = reap_kids(n);
    close(p[0]);
    say("%s: released; %d of %d reaped with their own status\n", mode, right, n);
    return 0;
}

/* --- reuse ------------------------------------------------------------------- */

static int reuse_mode(int rounds, int batch) {
    pid_t lo = 0, hi = 0, last = 0;
    int rising = 1, made = 0, right = 0, short_rounds = 0;
    for (int r = 0; r < rounds; r++) {
        int p[2];
        if (pipe(p) < 0) {
            say("reuse: no pipe: %s\n", ename(errno));
            return 1;
        }
        int err;
        int n = make_kids(batch, p[0], p[1], &err);
        if (n < batch) short_rounds++;
        for (int i = 0; i < n; i++) {
            if (kids[i] <= last) rising = 0;
            last = kids[i];
            if (lo == 0) lo = kids[i];
            hi = kids[i];
        }
        made += n;
        close(p[1]);
        right += reap_kids(n);
        close(p[0]);
    }
    say("reuse: forks %d in %d rounds of %d (%d rounds short), %d reaped with their own status, pids %s from %d to %d\n",
        made, rounds, batch, short_rounds, right, rising ? "rising" : "NOT rising", (int)lo, (int)hi);
    stacks = mmap(0, (size_t)(MAXT + 1) * TSTACK, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (stacks == MAP_FAILED) {
        say("reuse: no stacks: %s\n", ename(errno));
        return 1;
    }
    int tmade = 0, joined = 0, tshort = 0;
    for (int r = 0; r < rounds; r++) {
        int err;
        int n = make_threads(0, batch, &err);
        if (n < batch) tshort++;
        tmade += n;
        joined += join_threads(n);
    }
    say("reuse: threads %d in %d rounds of %d (%d rounds short), %d joined\n", tmade, rounds, batch, tshort, joined);
    return 0;
}

/* --- /proc ------------------------------------------------------------------- */

/* proc_pid_status(5)'s `Threads:` of `pid`, -1 when unreadable; `name`
 * gets its `Name:`. */
static int threads_of(pid_t pid, char *name, size_t cap) {
    char path[64], buf[4096];
    snprintf(path, sizeof path, "/proc/%d/status", (int)pid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t k = read(fd, buf, sizeof buf - 1);
    close(fd);
    if (k <= 0) return -1;
    buf[k] = 0;
    if (name) {
        name[0] = 0;
        char *q = strstr(buf, "Name:");
        if (q) {
            q += 5;
            while (*q == ' ' || *q == '\t') q++;
            size_t i = 0;
            while (q[i] && q[i] != '\n' && i + 1 < cap) { name[i] = q[i]; i++; }
            name[i] = 0;
        }
    }
    char *t = strstr(buf, "Threads:");
    return t ? atoi(t + 8) : -1;
}

/* proc_pid_stat(5)'s session (field 6) of `pid`, -1 when unreadable. */
static int session_of(pid_t pid) {
    char path[64], buf[1024];
    snprintf(path, sizeof path, "/proc/%d/stat", (int)pid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t k = read(fd, buf, sizeof buf - 1);
    close(fd);
    if (k <= 0) return -1;
    buf[k] = 0;
    char *q = strrchr(buf, ')');
    if (!q) return -1;
    int ppid, pgrp, sid;
    char st;
    if (sscanf(q + 1, " %c %d %d %d", &st, &ppid, &pgrp, &sid) != 4) return -1;
    return sid;
}

/* --- wolf ------------------------------------------------------------------- */

#define WOLF_BYTES 65536

static int wolf_mode(int n) {
    static int in[512][2];
    int out[2];
    if (n > 512) n = 512;
    if (pipe(out) < 0) {
        say("wolf: no pipe: %s\n", ename(errno));
        return 1;
    }
    int made = 0, err = 0;
    for (int i = 0; i < n; i++) {
        if (pipe(in[i]) < 0) {
            err = errno;
            break;
        }
        pid_t p = fork();
        if (p == 0) {
            dup2(in[i][0], 0);
            dup2(out[1], 1);
            for (int fd = 3; fd < 2 * n + 8; fd++) close(fd);
            char *argv[] = {"sha256sum", 0};
            char *envp[] = {"PATH=/bin", 0};
            execve("/bin/sha256sum", argv, envp);
            _exit(127);
        }
        if (p < 0) {
            err = errno;
            close(in[i][0]);
            close(in[i][1]);
            break;
        }
        close(in[i][0]);
        kids[made++] = p;
    }
    close(out[1]);
    /* Every one running sha256sum, blocked on its pipe, with its threads. */
    int ready = 0, tmin = INT_MAX, tmax = 0, tsum = 0;
    long end = now_ns() + 120000000000L;
    while (now_ns() < end) {
        ready = 0;
        tmin = INT_MAX;
        tmax = 0;
        tsum = 0;
        for (int i = 0; i < made; i++) {
            char name[32];
            int t = threads_of(kids[i], name, sizeof name);
            if (t > 0 && strcmp(name, "sha256sum") == 0) {
                ready++;
                if (t < tmin) tmin = t;
                if (t > tmax) tmax = t;
                tsum += t;
            }
        }
        if (ready == made && tmin >= 2) break;
        nap(200);
    }
    int alive = all_alive(made);
    say("wolf: %d of %d asked running sha256sum at once (%s), threads %d to %d each, %d in all%s%s\n", ready, n,
        alive ? "none ended" : "some ended", ready ? tmin : 0, tmax, tsum, err ? "; then answered " : "",
        err ? ename(err) : "");
    /* The work: 64 KiB each, byte j being j mod 251, then end of file. */
    static unsigned char data[WOLF_BYTES];
    for (int j = 0; j < WOLF_BYTES; j++) data[j] = (unsigned char)(j % 251);
    for (int i = 0; i < made; i++) {
        size_t off = 0;
        while (off < WOLF_BYTES) {
            ssize_t k = write(in[i][1], data + off, WOLF_BYTES - off);
            if (k < 0 && errno == EINTR) continue;
            if (k <= 0) break;
            off += (size_t)k;
        }
        close(in[i][1]);
    }
    /* Each digest line, 64 hex digits, two spaces, `-`. */
    static char buf[512 * 80];
    size_t len = 0;
    for (;;) {
        ssize_t k = read(out[0], buf + len, sizeof buf - 1 - len);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) break;
        len += (size_t)k;
    }
    buf[len] = 0;
    close(out[0]);
    int lines = 0, same = 1;
    char first[80] = "";
    for (char *l = buf; *l;) {
        char *e = strchr(l, '\n');
        if (!e) break;
        *e = 0;
        if (lines == 0) snprintf(first, sizeof first, "%s", l);
        else if (strcmp(l, first) != 0) same = 0;
        lines++;
        l = e + 1;
    }
    int right = 0;
    for (int i = 0; i < made; i++) {
        int st;
        pid_t r;
        while ((r = waitpid(kids[i], &st, 0)) < 0 && errno == EINTR) {}
        if (r == kids[i] && WIFEXITED(st) && WEXITSTATUS(st) == 0) right++;
    }
    say("wolf: %d digests, %s: %s\n", lines, same ? "all the same" : "NOT all the same", first);
    say("wolf: %d of %d reaped with status 0\n", right, made);
    return 0;
}

/* --- ptys -------------------------------------------------------------------- */

#define MAXP 64
static char tr[MAXP][4096];
static int trn[MAXP];

/* Read what master `m` (pty i) has into its transcript until `want`
 * occurs `times` times past `from`, or `ms` pass: whether it did. */
static int seen(int i, int m, const char *want, int times, int from, int ms) {
    long end = now_ns() + (long)ms * 1000000L;
    for (;;) {
        int c = 0;
        tr[i][trn[i]] = 0;
        for (char *q = tr[i] + from; (q = strstr(q, want)); q += strlen(want)) c++;
        if (c >= times) return 1;
        long t = (end - now_ns()) / 1000000L;
        if (t <= 0) return 0;
        struct pollfd p = {m, POLLIN, 0};
        int r = poll(&p, 1, (int)(t < 100 ? t : 100));
        if (r > 0 && (p.revents & (POLLIN | POLLHUP))) {
            ssize_t k = read(m, tr[i] + trn[i], sizeof tr[i] - 1 - (size_t)trn[i]);
            if (k > 0) trn[i] += (int)k;
            else if (k == 0 || (k < 0 && errno == EIO)) {
                tr[i][trn[i]] = 0;
                c = 0;
                for (char *q = tr[i] + from; (q = strstr(q, want)); q += strlen(want)) c++;
                return c >= times;
            }
        }
    }
}

static int ptys_mode(int n) {
    static int ms[MAXP];
    static pid_t sh[MAXP];
    if (n > MAXP) n = MAXP;
    int made = 0, err = 0;
    for (int i = 0; i < n; i++) {
        int m = open("/dev/ptmx", O_RDWR | O_NOCTTY);
        if (m < 0) {
            err = errno;
            break;
        }
        unlockpt(m);
        char name[64];
        ptsname_r(m, name, sizeof name);
        pid_t p = fork();
        if (p == 0) {
            setsid();
            int s = open(name, O_RDWR);
            dup2(s, 0);
            dup2(s, 1);
            dup2(s, 2);
            for (int fd = 3; fd < 3 * n + 8; fd++) close(fd);
            char cmd[64];
            snprintf(cmd, sizeof cmd, "cat; echo bye%d", i);
            char *argv[] = {"sh", "-c", cmd, 0};
            char *envp[] = {"HOME=/", "TERM=linux", "PATH=/bin", "HISTFILE=/dev/null", 0};
            execve("/bin/sh", argv, envp);
            _exit(127);
        }
        if (p < 0) {
            err = errno;
            close(m);
            break;
        }
        ms[made] = m;
        sh[made] = p;
        made++;
    }
    /* A line through each cat: its echo and cat's copy. */
    for (int i = 0; i < made; i++) {
        char line[32];
        int k = snprintf(line, sizeof line, "line%d\n", i);
        (void)!write(ms[i], line, (size_t)k);
    }
    int through = 0;
    for (int i = 0; i < made; i++) {
        char want[32];
        snprintf(want, sizeof want, "line%d\r\n", i);
        if (seen(i, ms[i], want, 2, 0, 120000)) through++;
    }
    /* Who is in each session now: the shell and its child. */
    int procs = 0, threads = 0, pairs = 0;
    for (int i = 0; i < made; i++) {
        int in = 0;
        DIR *d = opendir("/proc");
        struct dirent *e;
        while (d && (e = readdir(d))) {
            int pid = atoi(e->d_name);
            if (pid <= 0) continue;
            if (session_of(pid) == sh[i]) {
                in++;
                int t = threads_of(pid, 0, 0);
                if (t > 0) threads += t;
            }
        }
        if (d) closedir(d);
        procs += in;
        if (in >= 2) pairs++;
    }
    say("ptys: %d of %d asked, each a session: %d with a line through its cat, %d with a shell and a child (%d processes, %d threads in them)%s%s\n",
        made, n, through, pairs, procs, threads, err ? "; then answered " : "", err ? ename(err) : "");
    /* End of file to each cat; the shell says bye and ends. */
    int byes = 0;
    for (int i = 0; i < made; i++) (void)!write(ms[i], "\x04", 1);
    for (int i = 0; i < made; i++) {
        char want[32];
        snprintf(want, sizeof want, "bye%d", i);
        int from = trn[i];
        if (seen(i, ms[i], want, 1, from, 120000)) byes++;
    }
    int right = 0;
    for (int i = 0; i < made; i++) {
        int st;
        pid_t r;
        while ((r = waitpid(sh[i], &st, 0)) < 0 && errno == EINTR) {}
        if (r == sh[i] && WIFEXITED(st) && WEXITSTATUS(st) == 0) right++;
        close(ms[i]);
    }
    say("ptys: %d byes; %d of %d shells reaped with status 0\n", byes, right, made);
    return 0;
}

/* --- switch ------------------------------------------------------------------- */

#define SWITCH_TOTAL 200000

/* N children released at once, each yielding k times: (the children's CPU
 * ns a yield, the wall ns a yield); -1 when not all N were made. */
static int yield_round(int n, long *cpu, long *wall) {
    int p[2];
    if (pipe(p) < 0) return -1;
    int k = SWITCH_TOTAL / n;
    int made = 0;
    for (; made < n; made++) {
        pid_t c = fork();
        if (c == 0) {
            close(p[1]);
            char b;
            while (read(p[0], &b, 1) < 0 && errno == EINTR) {}
            for (int j = 0; j < k; j++) sched_yield();
            _exit(0);
        }
        if (c < 0) break;
        kids[made] = c;
    }
    long c0 = kids_cpu_ns(), t0 = now_ns();
    close(p[1]);
    for (int i = 0; i < made; i++) {
        int st;
        while (waitpid(kids[i], &st, 0) < 0 && errno == EINTR) {}
    }
    long c1 = kids_cpu_ns(), t1 = now_ns();
    close(p[0]);
    if (made < n) return -1;
    long yields = (long)n * k;
    *cpu = (c1 - c0) / yields;
    *wall = (t1 - t0) / yields;
    return 0;
}

static int switch_mode(int big) {
    int ns[3] = {16, 64, big};
    long best[3] = {-1, -1, -1};
    for (int round = 1; round <= 3; round++) {
        for (int j = 0; j < 3; j++) {
            long cpu = 0, wall = 0;
            if (yield_round(ns[j], &cpu, &wall) < 0) {
                say("switch: round %d: N=%d: not all made\n", round, ns[j]);
                continue;
            }
            say("switch: round %d: N=%d: %ld ns cpu, %ld ns wall a yield\n", round, ns[j], cpu, wall);
            if (best[j] < 0 || cpu < best[j]) best[j] = cpu;
        }
    }
    say("switch: least cpu a yield: N=16 %ld ns, N=64 %ld ns, N=%d %ld ns\n", best[0], best[1], big, best[2]);
    return 0;
}

/* --- herd --------------------------------------------------------------------- */

static int herd_mode(int big) {
    int ws[3] = {0, 64, big};
    for (int j = 0; j < 3; j++) {
        int w = ws[j];
        int park[2];
        if (pipe(park) < 0) return 1;
        int err;
        int n = make_kids(w, park[0], park[1], &err);
        int a[2], b[2];
        if (pipe(a) < 0 || pipe(b) < 0) return 1;
        pid_t echo = fork();
        if (echo == 0) {
            close(park[1]);
            close(a[1]);
            close(b[0]);
            char c;
            while (read(a[0], &c, 1) == 1) (void)!write(b[1], &c, 1);
            _exit(0);
        }
        close(a[0]);
        close(b[1]);
        int trips = w >= 500 ? 40 : 400;
        long t0 = now_ns();
        int done = 0;
        for (int i = 0; i < trips; i++) {
            char c = 'x';
            if (write(a[1], &c, 1) != 1 || read(b[0], &c, 1) != 1) break;
            done++;
        }
        long t1 = now_ns();
        close(a[1]);
        close(b[0]);
        int st;
        waitpid(echo, &st, 0);
        close(park[1]);
        reap_kids(n);
        close(park[0]);
        say("herd: W=%d parked (%d made): %d round trips, %ld ns a round trip\n", w, n, done, done ? (t1 - t0) / done : -1);
    }
    return 0;
}

int main(int argc, char **argv) {
    const char *m = argc > 1 ? argv[1] : "";
    int a = argc > 2 ? atoi(argv[2]) : 0;
    int b = argc > 3 ? atoi(argv[3]) : 0;
    setvbuf(stdout, 0, _IOLBF, 0);
    if (strcmp(m, "threads") == 0) return threads_mode();
    if (strcmp(m, "forks") == 0) return forks_mode(a, 0);
    if (strcmp(m, "fill") == 0) return forks_mode(1 << 30, 1);
    if (strcmp(m, "reuse") == 0) return reuse_mode(a, b);
    if (strcmp(m, "wolf") == 0) return wolf_mode(a);
    if (strcmp(m, "ptys") == 0) return ptys_mode(a);
    if (strcmp(m, "switch") == 0) return switch_mode(a);
    if (strcmp(m, "herd") == 0) return herd_mode(a);
    say("slotprobe: no mode '%s'\n", m);
    return 2;
}
