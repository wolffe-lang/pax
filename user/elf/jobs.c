/* px48: job control, asked of the kernel — process groups and sessions,
 * the controlling terminal and its ioctls, kill to a group, stops and
 * continues and the waits that report them, the terminal's signals to
 * the foreground group and the background rules, and hangup and the
 * orphaned group. Run as the first program on a terminal (PAX's console
 * as pid 1; a Linux pseudo-terminal as its session leader, notes/px48's
 * guest and tools/linux-tty), as root and as a user (through `as`).
 *
 * The program as started (`main`) gives its terminal up (TIOCNOTTY) and
 * starts `R`, which makes a session of its own and asks everything from
 * there, so the shape is the same on both systems whatever is above
 * them: R's parent is in another session (R's own group is orphaned),
 * R's children's groups are not. Every line is `case: answer`; no pid,
 * time or address is printed, and what several processes heard is
 * printed sorted, each once. Where it wants a key typed, R writes the prompt `$ `
 * and waits (tools/qemu-halt --type, tools/linux-tty, notes/px48's
 * vmjob): five keys, ^C ^\ ^Z ^Z ^C, then the keys of V (VMIN and VTIME,
 * pax#66): x, y 1.5 s later, ab, q 1.5 s later (user/console/jobs.keys).
 *
 *   jobs            every section, G K S T V H
 *   jobs soak N     N rounds: a group made, stopped, continued, given the
 *                   terminal and back, signalled, reaped (P5)
 *   jobs idle       (internal) a target that only waits, exec'd
 *
 * Written from POSIX.1-2024 (XBD 11, XBD 3's orphaned process group,
 * XSH setpgid, setsid, tcsetpgrp, tcgetpgrp, tcgetsid, waitpid, waitid,
 * kill) and the man pages (setpgid(2), setsid(2), wait4(2), waitid(2),
 * kill(2), signal(7), ioctl_tty(2), TIOCSCTTY(2const), termios(3),
 * proc_pid_stat(5)); the shapes of s240's grp.c and sess.c (wolf-lang
 * 211d28cb, the org's own black-box probes). No C library's, kernel's
 * or shell's source was read. Written for this lane. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static int rep[2];      /* what handlers heard: "TAG:SIG\n" */
static char tag[16] = "?";
static int root;

static const char *sname(int s) {
    switch (s) {
    case SIGHUP: return "HUP"; case SIGINT: return "INT"; case SIGQUIT: return "QUIT";
    case SIGUSR1: return "USR1"; case SIGTERM: return "TERM"; case SIGCHLD: return "CHLD";
    case SIGCONT: return "CONT"; case SIGSTOP: return "STOP"; case SIGTSTP: return "TSTP";
    case SIGTTIN: return "TTIN"; case SIGTTOU: return "TTOU"; case SIGWINCH: return "WINCH";
    case SIGKILL: return "KILL";
    default: return "?";
    }
}


static void heard(int sig) {
    char b[48];
    int n = 0;
    for (const char *p = tag; *p && n < 15; p++) b[n++] = *p;
    b[n++] = ':';
    for (const char *s = sname(sig); *s; s++) b[n++] = *s;
    b[n++] = '\n';
    (void)!write(rep[1], b, (size_t)n);
}

/* SIGCHLD with its code and status, for R. */
static void chld(int sig, siginfo_t *si, void *uc) {
    (void)sig; (void)uc;
    char b[48];
    const char *c = si->si_code == CLD_EXITED ? "EXITED" : si->si_code == CLD_KILLED ? "KILLED" :
                    si->si_code == CLD_STOPPED ? "STOPPED" : si->si_code == CLD_CONTINUED ? "CONTINUED" : "OTHER";
    int n = snprintf(b, sizeof b, "CHLD %s %s\n", c, si->si_code == CLD_EXITED ? "-" : sname(si->si_status));
    (void)!write(rep[1], b, (size_t)n);
}

static void on(int sig) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = heard;
    sa.sa_flags = SA_RESTART;
    sigemptyset(&sa.sa_mask);
    sigaction(sig, &sa, 0);
}


static void chld_on(int flags) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = chld;
    sa.sa_flags = SA_SIGINFO | SA_RESTART | flags;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGCHLD, &sa, 0);
}

static long now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void nap(int ms) {
    struct timespec ts = {ms / 1000, (long)(ms % 1000) * 1000000L};
    while (nanosleep(&ts, &ts) < 0 && errno == EINTR) {}
}

static const char *ename(int e) {
    switch (e) {
    case 0: return "0";
    case EPERM: return "EPERM"; case ESRCH: return "ESRCH"; case EINVAL: return "EINVAL";
    case EACCES: return "EACCES"; case ENXIO: return "ENXIO"; case ENOTTY: return "ENOTTY";
    case EIO: return "EIO"; case ECHILD: return "ECHILD"; case EAGAIN: return "EAGAIN";
    case EINTR: return "EINTR"; case EBADF: return "EBADF";
    default: { static char b[32]; snprintf(b, sizeof b, "errno%d", e); return b; }
    }
}

#define ANS(name, expr) do { errno = 0; long r_ = (long)(expr); printf("%s: %s\n", name, r_ < 0 ? ename(errno) : "0"); } while (0)

static int cmp_str(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }

/* What the handlers reported, sorted and joined with commas ("-" for
 * nothing): waits until `want` lines came or `ms` passed, then a little
 * longer for anything not expected. */
static void heard_list(char *out, size_t cap, int want, int ms) {
    char buf[4096];
    size_t len = 0;
    long end = now_ms() + ms, extra = -1;
    for (;;) {
        ssize_t r = read(rep[0], buf + len, sizeof buf - 1 - len);
        if (r > 0) { len += (size_t)r; continue; }
        int lines = 0;
        for (size_t i = 0; i < len; i++) if (buf[i] == '\n') lines++;
        if (extra < 0 && want > 0 && lines >= want) extra = now_ms() + 150;
        long t = now_ms();
        if ((extra >= 0 && t >= extra) || t >= end) break;
        nap(10);
    }
    buf[len] = 0;
    char *v[128];
    int n = 0;
    for (char *s = strtok(buf, "\n"); s && n < 128; s = strtok(NULL, "\n")) v[n++] = s;
    qsort(v, (size_t)n, sizeof v[0], cmp_str);
    out[0] = 0;
    size_t k = 0;
    for (int i = 0, m = 0; i < n; i++) {
        if (i && strcmp(v[i], v[i - 1]) == 0) continue; /* a signal heard twice is told once: a standard signal may merge */
        k += (size_t)snprintf(out + k, cap > k ? cap - k : 0, "%s%s", m++ ? "," : "", v[i]);
    }
    if (!n) snprintf(out, cap, "-");
}

static void flush_heard(void) { char b[4096]; while (read(rep[0], b, sizeof b) > 0) {} }

/* A child that waits until killed. `pg`: 0 a new group, > 0 join that
 * group, -1 stay, -2 a new session. `sigs`: the signals it reports.
 * `tick`: when not -1, the write end it sends a byte to every 20 ms. */
static pid_t idle_t(pid_t pg, const char *name, const int *sigs, int tick) {
    int s[2];
    (void)!pipe(s);
    pid_t p = fork();
    if (p == 0) {
        close(s[0]);
        snprintf(tag, sizeof tag, "%s", name);
        static const int reset[] = {SIGHUP, SIGINT, SIGQUIT, SIGUSR1, SIGCONT, SIGTSTP, SIGTTIN, SIGTTOU, SIGWINCH, 0};
        for (const int *q = reset; *q; q++) signal(*q, SIG_DFL); /* nothing R ignores or handles is inherited */
        for (const int *q = sigs; q && *q; q++) on(*q);
        if (pg == -2) setsid();
        else if (pg >= 0) setpgid(0, pg);
        (void)!write(s[1], "k", 1);
        close(s[1]);
        for (;;) {
            if (tick >= 0) (void)!write(tick, "t", 1);
            nap(20);
        }
    }
    close(s[1]);
    if (pg >= 0) setpgid(p, pg ? pg : p);
    char c;
    (void)!read(s[0], &c, 1);
    close(s[0]);
    return p;
}

static pid_t idle(pid_t pg, const char *name, const int *sigs) { return idle_t(pg, name, sigs, -1); }

static void reap(pid_t p) { kill(p, SIGKILL); waitpid(p, 0, 0); }

/* /proc/<pid>/stat: the state and fields 5 to 8. */
struct pstat { char state; long pgrp, sess, tty, tpgid; int ok; };
static struct pstat pstat_of(pid_t p) {
    struct pstat r = {'?', 0, 0, 0, 0, 0};
    char path[64], b[1024];
    snprintf(path, sizeof path, "/proc/%d/stat", (int)p);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return r;
    ssize_t n = read(fd, b, sizeof b - 1);
    close(fd);
    if (n <= 0) return r;
    b[n] = 0;
    char *q = strrchr(b, ')');
    if (!q) return r;
    long ppid;
    if (sscanf(q + 2, "%c %ld %ld %ld %ld %ld", &r.state, &ppid, &r.pgrp, &r.sess, &r.tty, &r.tpgid) == 6) r.ok = 1;
    return r;
}

static long tty_number(int fd) {
    struct stat st;
    if (fstat(fd, &st) != 0) return -1;
    unsigned ma = major(st.st_rdev), mi = minor(st.st_rdev);
    return (long)((mi & 0xff) | (ma << 8) | ((mi & ~0xffu) << 12));
}

static const char *yesno(int c) { return c ? "yes" : "no"; }

/* How a waited-for child changed: "stopped by X", "continued",
 * "exited N", "killed by X", "0 (nothing new)", or an errno. */
static const char *how(pid_t w, int st) {
    static char b[64];
    if (w == 0) return "0 (nothing new)";
    if (w < 0) return ename(errno);
    if (WIFSTOPPED(st)) snprintf(b, sizeof b, "stopped by %s (status 0x%x)", sname(WSTOPSIG(st)), st);
    else if (WIFCONTINUED(st)) snprintf(b, sizeof b, "continued (status 0x%x)", st);
    else if (WIFEXITED(st)) snprintf(b, sizeof b, "exited %d", WEXITSTATUS(st));
    else if (WIFSIGNALED(st)) snprintf(b, sizeof b, "killed by %s", sname(WTERMSIG(st)));
    else snprintf(b, sizeof b, "status 0x%x", st);
    return b;
}

/* Whether a ticking child is running: bytes came in `ms`. */
static int ticking(int rd, int ms) {
    char b[512];
    while (read(rd, b, sizeof b) > 0) {}
    nap(ms);
    int n = 0;
    ssize_t r;
    while ((r = read(rd, b, sizeof b)) > 0) n += (int)r;
    return n > 0;
}

static void *thread_ids(void *arg) {
    pid_t *v = arg;
    v[0] = getpgrp(); v[1] = getsid(0); v[2] = getpgid(0);
    return 0;
}

/* --- G: groups and sessions --------------------------------------------- */
static void groups_and_sessions(void) {
    printf("G: R leads its session and group: %s\n", yesno(getsid(0) == getpid() && getpgrp() == getpid()));
    ANS("G: setsid by a session leader", setsid());
    ANS("G: setpgid(0, 0) by a session leader", setpgid(0, 0));
    ANS("G: setpgid(getpid(), getpid()) by a session leader", setpgid(getpid(), getpid()));
    printf("G: getpgid(0) and getsid(0) are getpgrp() and the pid: %s\n", yesno(getpgid(0) == getpgrp() && getsid(0) == getpid()));
    {
        pid_t c = fork();
        if (c == 0) {
            printf("G: a child is in its parent's group and session: %s\n", yesno(getpgrp() == getpgid(getppid()) && getsid(0) == getsid(getppid())));
            setpgid(0, 0);
            errno = 0;
            int r = setsid();
            printf("G: setsid by a group leader (not a session leader): %s\n", r < 0 ? ename(errno) : "0");
            _exit(0);
        }
        waitpid(c, 0, 0);
    }
    {
        pid_t c = fork();
        if (c == 0) {
            pid_t sid = setsid();
            int fd = open("/dev/tty", O_RDWR);
            int e = fd < 0 ? errno : 0;
            errno = 0;
            pid_t g = tcgetpgrp(0);
            int e2 = errno;
            struct pstat ps = pstat_of(getpid());
            printf("G: setsid by a non-leader: sid is the pid %s, pgid is the pid %s, /dev/tty %s, tcgetpgrp(0) %s\n",
                   yesno(sid == getpid()), yesno(getpgrp() == getpid()), fd < 0 ? ename(e) : "opened", g < 0 ? ename(e2) : "a group");
            printf("G: its /proc stat: read %s, pgrp %s, session %s, tty_nr 0 %s, tpgid -1 %s, state %c\n", yesno(ps.ok),
                   yesno(ps.pgrp == getpid()), yesno(ps.sess == getpid()), yesno(ps.tty == 0), yesno(ps.tpgid == -1), ps.state);
            _exit(0);
        }
        waitpid(c, 0, 0);
    }
    {
        pid_t other = idle(-2, "X", 0); /* leads a group in another session */
        pid_t c = idle(-1, "c", 0);
        pid_t d = idle(-1, "d", 0);
        printf("G: getsid of another session's leader is its pid, getpgid too: %s\n", yesno(getsid(other) == other && getpgid(other) == other));
        ANS("G: setpgid(child, a group of another session)", setpgid(c, other));
        ANS("G: setpgid(child, a group that does not exist)", setpgid(c, 999999));
        ANS("G: setpgid(child, -1)", setpgid(c, -1));
        ANS("G: setpgid(child, 0) before its exec", setpgid(c, 0));
        printf("G: the child leads a group of its own now: %s\n", yesno(getpgid(c) == c));
        ANS("G: setpgid(other child, the first child's group)", setpgid(d, c));
        printf("G: the other child is in it: %s\n", yesno(getpgid(d) == c));
        ANS("G: setpgid(child, the caller's group) back", setpgid(d, getpgrp()));
        ANS("G: setpgid(another session's leader, 0)", setpgid(other, 0));
        struct pstat ps = pstat_of(c);
        printf("G: the child's /proc stat: pgrp %s, session %s, tty_nr 0 %s, tpgid -1 %s, state %c\n",
               yesno(ps.pgrp == c), yesno(ps.sess == getpid()), yesno(ps.tty == 0), yesno(ps.tpgid == -1), ps.state);
        reap(c); reap(d); reap(other);
    }
    {
        int s[2];
        (void)!pipe(s);
        pid_t c = fork();
        if (c == 0) {
            close(s[0]);
            fcntl(s[1], F_SETFD, FD_CLOEXEC);
            execl("/bin/jobs", "jobs", "idle", (char *)0);
            _exit(127);
        }
        close(s[1]);
        char b;
        (void)!read(s[0], &b, 1); /* end of file once the exec has happened */
        close(s[0]);
        ANS("G: setpgid(child, 0) after the child's exec", setpgid(c, 0));
        reap(c);
    }
    {
        int s[2];
        (void)!pipe(s);
        pid_t c = fork();
        if (c == 0) {
            close(s[0]);
            pid_t g = fork();
            if (g == 0) { for (;;) nap(100); }
            (void)!write(s[1], &g, sizeof g);
            for (;;) nap(100);
        }
        close(s[1]);
        pid_t g = 0;
        (void)!read(s[0], &g, sizeof g);
        close(s[0]);
        ANS("G: setpgid(grandchild, 0)", setpgid(g, 0));
        ANS("G: setpgid(the parent, 0)", setpgid(getppid(), 0));
        kill(g, SIGKILL);
        reap(c);
    }
    ANS("G: getpgid(a pid nobody has)", getpgid(999999));
    ANS("G: getsid(a pid nobody has)", getsid(999999));
    ANS("G: setpgid(a pid nobody has, 0)", setpgid(999999, 0));
    printf("G: the parent is in another session: %s\n", yesno(getsid(getppid()) != getsid(0)));
    {
        pid_t v[3] = {0, 0, 0};
        pthread_t t;
        pthread_create(&t, 0, thread_ids, v);
        pthread_join(t, 0);
        printf("G: a thread's getpgrp, getsid and getpgid are its process's: %s\n", yesno(v[0] == getpgrp() && v[1] == getsid(0) && v[2] == getpgrp()));
    }
    {
        struct pstat ps = pstat_of(getpid());
        printf("G: R's /proc stat: pgrp %s, session %s, tty_nr 0 %s, tpgid -1 %s, state %c\n",
               yesno(ps.pgrp == getpid()), yesno(ps.sess == getpid()), yesno(ps.tty == 0), yesno(ps.tpgid == -1), ps.state);
    }
}

/* --- K: kill to a group ----------------------------------------------------- */
static const int USR1[] = {SIGUSR1, 0};

static void kill_groups(void) {
    char h[1024];
    on(SIGUSR1);
    snprintf(tag, sizeof tag, "R");
    flush_heard();
    {
        pid_t a = idle(0, "A", USR1);
        pid_t b = idle(a, "B", USR1);
        pid_t c = idle(-1, "C", USR1);
        pid_t s = fork();
        if (s == 0) {
            snprintf(tag, sizeof tag, "S");
            setpgid(0, a);
            int r = kill(0, SIGUSR1);
            printf("K: kill(0) from a member of A={A,B}, C apart: %s", r < 0 ? ename(errno) : "0");
            fflush(stdout);
            nap(50);
            _exit(0);
        }
        setpgid(s, a);
        waitpid(s, 0, 0);
        heard_list(h, sizeof h, 3, 1500);
        printf(", heard %s\n", h);
        errno = 0;
        int r = kill(-a, SIGUSR1);
        heard_list(h, sizeof h, 2, 1500);
        printf("K: kill(-A) from outside A: %s, heard %s\n", r < 0 ? ename(errno) : "0", h);
        r = kill(-a, 0);
        heard_list(h, sizeof h, 0, 200);
        printf("K: kill(-A, 0): %s, heard %s\n", r < 0 ? ename(errno) : "0", h);
        reap(a);
        r = kill(-a, SIGUSR1);
        heard_list(h, sizeof h, 1, 1500);
        printf("K: kill(-A) with its leader reaped, B alive: %s, heard %s\n", r < 0 ? ename(errno) : "0", h);
        kill(b, SIGKILL);
        nap(100);
        r = kill(-a, 0);
        printf("K: kill(-A, 0) with its one member a zombie: %s\n", r < 0 ? ename(errno) : "0");
        r = kill(-a, SIGUSR1);
        printf("K: kill(-A) with its one member a zombie: %s\n", r < 0 ? ename(errno) : "0");
        waitpid(b, 0, 0);
        r = kill(-a, 0);
        printf("K: kill(-A, 0) with every member reaped: %s\n", r < 0 ? ename(errno) : "0");
        r = kill(-a, SIGUSR1);
        printf("K: kill(-A) with every member reaped: %s\n", r < 0 ? ename(errno) : "0");
        reap(c);
        flush_heard();
    }
    ANS("K: kill(-999999, 0)", kill(-999999, 0));
    ANS("K: kill(INT_MIN, 0)", kill(INT_MIN, 0));
    ANS("K: kill(-INT_MAX, 0)", kill(-INT_MAX, 0));
    ANS("K: kill(0, 0)", kill(0, 0));
    ANS("K: kill(-getpgrp(), 0)", kill(-getpgrp(), 0));
    if (!root) {
        printf("K: the mixed groups: skipped by name (not root)\n");
        return;
    }
    /* As root, a group with a root member and a user member, signalled
     * by an actor that has become 1000 for good. */
    {
        pid_t x = idle(0, "Xroot", USR1);
        int s[2];
        (void)!pipe(s);
        pid_t y = fork();
        if (y == 0) {
            snprintf(tag, sizeof tag, "Yuser");
            on(SIGUSR1);
            setpgid(0, x);
            if (setresgid(1000, 1000, 1000) || setresuid(1000, 1000, 1000)) _exit(1);
            (void)!write(s[1], "k", 1);
            for (;;) nap(20);
        }
        setpgid(y, x);
        char c;
        (void)!read(s[0], &c, 1);
        close(s[0]); close(s[1]);
        pid_t other = idle(-2, "Zroot", (const int[]){SIGCONT, SIGUSR1, 0});
        pid_t act = fork();
        if (act == 0) {
            if (setresgid(1000, 1000, 1000) || setresuid(1000, 1000, 1000)) _exit(1);
            int r = kill(-x, SIGUSR1);
            printf("K: as 1000, kill(-G) G={a root member, a 1000 member}: %s", r < 0 ? ename(errno) : "0");
            fflush(stdout);
            _exit(0);
        }
        waitpid(act, 0, 0);
        heard_list(h, sizeof h, 1, 1500);
        printf(", heard %s\n", h);
        kill(y, SIGKILL);
        waitpid(y, 0, 0);
        act = fork();
        if (act == 0) {
            if (setresgid(1000, 1000, 1000) || setresuid(1000, 1000, 1000)) _exit(1);
            int r = kill(-x, SIGUSR1);
            printf("K: as 1000, kill(-G) G={a root member}: %s\n", r < 0 ? ename(errno) : "0");
            r = kill(-x, 0);
            printf("K: as 1000, kill(-G, 0) G={a root member}: %s\n", r < 0 ? ename(errno) : "0");
            r = kill(-x, SIGCONT);
            printf("K: as 1000, kill(-G, SIGCONT) G={a root member}, the same session: %s\n", r < 0 ? ename(errno) : "0");
            r = kill(-other, SIGCONT);
            printf("K: as 1000, kill(-G, SIGCONT) G={a root member}, another session: %s\n", r < 0 ? ename(errno) : "0");
            r = kill(other, SIGCONT);
            printf("K: as 1000, kill(pid, SIGCONT) of root's, another session: %s\n", r < 0 ? ename(errno) : "0");
            fflush(stdout);
            _exit(0);
        }
        waitpid(act, 0, 0);
        heard_list(h, sizeof h, 0, 300);
        printf("K: those five, heard %s\n", h);
        reap(x); reap(other);
        flush_heard();
    }
}

/* --- S: stops, continues, and the waits ------------------------------------- */

static void stops(void) {
    char h[1024];
    int st;
    pid_t w;
    snprintf(tag, sizeof tag, "R");
    chld_on(0);
    flush_heard();
    int tp[2];
    (void)!pipe(tp);
    fcntl(tp[0], F_SETFL, O_NONBLOCK);
    fcntl(tp[1], F_SETFL, O_NONBLOCK);
    pid_t a = idle_t(0, "A", 0, tp[1]);
    pid_t b = idle_t(a, "B", 0, tp[1]);
    printf("S: a group of two, ticking: %s\n", yesno(ticking(tp[0], 200)));
    ANS("S: kill(-G, SIGSTOP)", kill(-a, SIGSTOP));
    int n = 0;
    for (int i = 0; i < 2; i++) {
        w = waitpid(-a, &st, WUNTRACED);
        if (w > 0 && WIFSTOPPED(st) && WSTOPSIG(st) == SIGSTOP && st == 0x137f) n++;
    }
    printf("S: waitpid(-G, WUNTRACED) reported stopped by SIGSTOP (status 0x137f): %d of 2\n", n);
    heard_list(h, sizeof h, 2, 1500);
    printf("S: R heard %s\n", h);
    w = waitpid(-a, &st, WNOHANG | WUNTRACED);
    printf("S: a second waitpid(-G, WNOHANG|WUNTRACED): %s\n", how(w, st));
    printf("S: a stopped group runs nothing: %s\n", yesno(!ticking(tp[0], 300)));
    struct pstat ps = pstat_of(a);
    printf("S: a stopped member's /proc stat state: %c\n", ps.state);
    {
        char path[64], b[512], st_line[64] = "?";
        snprintf(path, sizeof path, "/proc/%d/status", (int)a);
        int fd = open(path, O_RDONLY);
        ssize_t k = fd >= 0 ? read(fd, b, sizeof b - 1) : -1;
        if (fd >= 0) close(fd);
        if (k > 0) {
            b[k] = 0;
            char *q = strstr(b, "State:");
            if (q) { char *e = strchr(q, '\n'); if (e) *e = 0; snprintf(st_line, sizeof st_line, "%s", q); }
        }
        for (char *t = st_line; *t; t++) if (*t == '\t') *t = ' ';
        printf("S: its /proc status: %s\n", st_line);
    }
    w = waitpid(-a, &st, WNOHANG);
    printf("S: waitpid(-G, WNOHANG) of a stopped group without WUNTRACED: %s\n", how(w, st));
    ANS("S: kill(-G, SIGCONT)", kill(-a, SIGCONT));
    n = 0;
    for (int i = 0; i < 2; i++) {
        w = waitpid(-a, &st, WCONTINUED);
        if (w > 0 && WIFCONTINUED(st) && st == 0xffff) n++;
    }
    printf("S: waitpid(-G, WCONTINUED) reported continued (status 0xffff): %d of 2\n", n);
    heard_list(h, sizeof h, 2, 1500);
    printf("S: R heard %s\n", h);
    printf("S: a continued group runs again: %s\n", yesno(ticking(tp[0], 200)));
    w = waitpid(-a, &st, WNOHANG | WCONTINUED | WUNTRACED);
    printf("S: waitpid(-G, WNOHANG|WCONTINUED|WUNTRACED) once both are reported: %s\n", how(w, st));
    ANS("S: kill(a, SIGTSTP)", kill(a, SIGTSTP));
    w = waitpid(a, &st, WUNTRACED);
    printf("S: SIGTSTP at its default: %s\n", how(w, st));
    {
        siginfo_t si;
        memset(&si, 0, sizeof si);
        ANS("S: kill(b, SIGTTIN)", kill(b, SIGTTIN));
        int r = waitid(P_PGID, (id_t)a, &si, WSTOPPED | WNOWAIT);
        printf("S: waitid(P_PGID, G, WSTOPPED|WNOWAIT): %s, code %s, status %s, the pid b's %s\n", r < 0 ? ename(errno) : "0",
               si.si_code == CLD_STOPPED ? "CLD_STOPPED" : "other", sname(si.si_status), yesno(si.si_pid == b));
        memset(&si, 0, sizeof si);
        r = waitid(P_PID, (id_t)b, &si, WSTOPPED);
        printf("S: waitid(P_PID, b, WSTOPPED) after WNOWAIT, the same: %s, code %s, status %s\n", r < 0 ? ename(errno) : "0",
               si.si_code == CLD_STOPPED ? "CLD_STOPPED" : "other", sname(si.si_status));
        memset(&si, 0, sizeof si);
        r = waitid(P_PGID, (id_t)a, &si, WSTOPPED | WNOHANG);
        printf("S: waitid(P_PGID, G, WSTOPPED|WNOHANG) after: %s, pid 0 %s\n", r < 0 ? ename(errno) : "0", yesno(si.si_pid == 0));
        kill(-a, SIGCONT);
        memset(&si, 0, sizeof si);
        r = waitid(P_PID, (id_t)b, &si, WCONTINUED);
        printf("S: waitid(P_PID, b, WCONTINUED): %s, code %s, status %s\n", r < 0 ? ename(errno) : "0",
               si.si_code == CLD_CONTINUED ? "CLD_CONTINUED" : "other", sname(si.si_status));
        w = waitpid(a, &st, WCONTINUED);
        printf("S: waitpid(a, WCONTINUED): %s\n", how(w, st));
        heard_list(h, sizeof h, 6, 1500);
        printf("S: R heard %s\n", h);
    }
    /* SA_NOCLDSTOP: no SIGCHLD for a stop or a continue; the waits still report. */
    chld_on(SA_NOCLDSTOP);
    kill(a, SIGSTOP);
    w = waitpid(a, &st, WUNTRACED);
    kill(a, SIGCONT);
    pid_t w2 = waitpid(a, &st, WCONTINUED);
    heard_list(h, sizeof h, 0, 300);
    printf("S: under SA_NOCLDSTOP a stop and a continue: reported %s and %s, R heard %s\n", w == a ? "yes" : "no", w2 == a ? "yes" : "no", h);
    chld_on(0);
    /* The selectors. */
    {
        pid_t d = fork();
        if (d == 0) { nap(100); _exit(7); }
        w = waitpid(-a, &st, WNOHANG);
        printf("S: waitpid(-G, WNOHANG) while a child of another group ends: %s\n", how(w, st));
        nap(400);
        w = waitpid(-a, &st, WNOHANG);
        printf("S: waitpid(-G, WNOHANG) after it ended: %s\n", how(w, st));
        w = waitpid(0, &st, 0);
        printf("S: waitpid(0) (the caller's group) for it: %s, its pid %s\n", how(w, st), yesno(w == d));
        w = waitpid(-999999, &st, WNOHANG);
        printf("S: waitpid(-999999, WNOHANG): %s\n", how(w, st));
        w = waitpid(0, &st, WNOHANG);
        printf("S: waitpid(0, WNOHANG) with no child in the caller's group: %s\n", how(w, st));
        siginfo_t si;
        memset(&si, 0, sizeof si);
        int r = waitid(P_PGID, 0, &si, WEXITED | WNOHANG);
        printf("S: waitid(P_PGID, 0, WEXITED|WNOHANG) the same: %s\n", r < 0 ? ename(errno) : "0");
        heard_list(h, sizeof h, 1, 600);
        printf("S: R heard %s\n", h);
    }
    /* A stop that is blocked waits; SIGCONT discards a stop pending. */
    {
        int s[2], g[2];
        (void)!pipe(s);
        (void)!pipe(g);
        pid_t c = fork();
        if (c == 0) {
            setpgid(0, 0); /* R's own group is orphaned, where SIGTSTP would not stop */
            sigset_t m;
            sigemptyset(&m);
            sigaddset(&m, SIGTSTP);
            sigprocmask(SIG_BLOCK, &m, 0);
            (void)!write(s[1], "k", 1);
            char x;
            (void)!read(g[0], &x, 1);
            sigprocmask(SIG_UNBLOCK, &m, 0);
            (void)!write(s[1], "u", 1);
            (void)!read(g[0], &x, 1);
            sigprocmask(SIG_BLOCK, &m, 0);
            (void)!write(s[1], "v", 1);
            (void)!read(g[0], &x, 1);
            sigprocmask(SIG_UNBLOCK, &m, 0);
            (void)!write(s[1], "w", 1);
            for (;;) nap(20);
        }
        setpgid(c, c);
        char x;
        (void)!read(s[0], &x, 1);
        kill(c, SIGTSTP);
        w = waitpid(c, &st, WNOHANG | WUNTRACED);
        printf("S: SIGTSTP blocked: %s\n", how(w, st));
        (void)!write(g[1], "g", 1);
        w = waitpid(c, &st, WUNTRACED);
        printf("S: SIGTSTP unblocked: %s\n", how(w, st));
        kill(c, SIGCONT);
        w = waitpid(c, &st, WCONTINUED);
        (void)!read(s[0], &x, 1); /* "u" */
        (void)!write(g[1], "g", 1);
        (void)!read(s[0], &x, 1); /* "v": blocked again */
        kill(c, SIGTSTP);
        kill(c, SIGCONT);
        (void)!write(g[1], "g", 1);
        (void)!read(s[0], &x, 1); /* "w": unblocked */
        nap(200);
        w = waitpid(c, &st, WNOHANG | WUNTRACED);
        printf("S: SIGTSTP pending, then SIGCONT, then unblocked: %s\n", how(w, st));
        kill(c, SIGSTOP);
        waitpid(c, &st, WUNTRACED);
        kill(c, SIGKILL);
        w = waitpid(c, &st, 0);
        printf("S: SIGKILL to a stopped child: %s\n", how(w, st));
        close(s[0]); close(s[1]); close(g[0]); close(g[1]);
        heard_list(h, sizeof h, 0, 300);
        flush_heard();
    }
    /* A handler for SIGTSTP runs and nothing stops. */
    {
        pid_t c = idle(-1, "T", (const int[]){SIGTSTP, 0});
        kill(c, SIGTSTP);
        heard_list(h, sizeof h, 1, 1500);
        w = waitpid(c, &st, WNOHANG | WUNTRACED);
        printf("S: SIGTSTP with a handler: heard %s, %s\n", h, how(w, st));
        reap(c);
        flush_heard();
    }
    /* A sleep keeps its deadline across a stop; a read keeps waiting. */
    {
        int s[2];
        (void)!pipe(s);
        pid_t c = fork();
        if (c == 0) {
            long t0 = now_ms();
            struct timespec ts = {0, 900 * 1000000L};
            int r = nanosleep(&ts, &ts);
            long d = now_ms() - t0;
            char b[96];
            int k = snprintf(b, sizeof b, "S: nanosleep(900 ms) stopped at 200 ms for 300 ms: %d, %s\n", r,
                             d < 850 ? "early" : d > 3000 ? "late" : "at its deadline");
            (void)!write(s[1], b, (size_t)k);
            _exit(0);
        }
        nap(200);
        kill(c, SIGSTOP);
        waitpid(c, &st, WUNTRACED);
        nap(300);
        kill(c, SIGCONT);
        waitpid(c, &st, 0);
        char b[128];
        ssize_t k = read(s[0], b, sizeof b - 1);
        b[k > 0 ? k : 0] = 0;
        printf("%s", b);
        close(s[0]); close(s[1]);
    }
    {
        int s[2], o[2];
        (void)!pipe(s);
        (void)!pipe(o);
        pid_t c = fork();
        if (c == 0) {
            char x;
            ssize_t r = read(s[0], &x, 1);
            char b[96];
            int k = snprintf(b, sizeof b, "S: a read stopped and continued, then given a byte: %zd%s\n", r, r < 0 ? ename(errno) : "");
            (void)!write(o[1], b, (size_t)k);
            _exit(0);
        }
        nap(100);
        kill(c, SIGSTOP);
        waitpid(c, &st, WUNTRACED);
        kill(c, SIGCONT);
        waitpid(c, &st, WCONTINUED);
        nap(100);
        (void)!write(s[1], "x", 1);
        waitpid(c, &st, 0);
        char b[128];
        ssize_t k = read(o[0], b, sizeof b - 1);
        b[k > 0 ? k : 0] = 0;
        printf("%s", b);
        close(s[0]); close(s[1]); close(o[0]); close(o[1]);
    }
    /* An orphaned group: SIGTSTP discarded at its default, SIGSTOP stops. */
    {
        int up[2], down[2], tq[2];
        (void)!pipe(up);
        (void)!pipe(down);
        (void)!pipe(tq);
        fcntl(tq[0], F_SETFL, O_NONBLOCK);
        fcntl(tq[1], F_SETFL, O_NONBLOCK);
        pid_t m = fork();
        if (m == 0) {
            setpgid(0, 0);
            pid_t m2 = fork();
            if (m2 == 0) {
                for (;;) { (void)!write(tq[1], "t", 1); nap(20); }
            }
            (void)!write(up[1], &m2, sizeof m2);
            char x;
            (void)!read(down[0], &x, 1);
            _exit(0);
        }
        pid_t m2 = 0;
        (void)!read(up[0], &m2, sizeof m2);
        (void)!write(down[1], "q", 1);
        waitpid(m, 0, 0); /* m2's group is orphaned now: its parent is pid 1, another session's */
        nap(100);
        printf("S: an orphaned group's member, ticking: %s\n", yesno(ticking(tq[0], 300)));
        kill(m2, SIGTSTP);
        printf("S: SIGTSTP to a process of an orphaned group: it runs on %s\n", yesno(ticking(tq[0], 300)));
        kill(m2, SIGTTIN);
        printf("S: SIGTTIN likewise: it runs on %s\n", yesno(ticking(tq[0], 300)));
        kill(m2, SIGSTOP);
        int on2 = ticking(tq[0], 300);
        printf("S: SIGSTOP to it: it runs on %s, state %c\n", yesno(on2), pstat_of(m2).state);
        kill(m2, SIGCONT);
        printf("S: SIGCONT to it: it runs on %s\n", yesno(ticking(tq[0], 300)));
        kill(m2, SIGKILL);
        nap(200);
        close(up[0]); close(up[1]); close(down[0]); close(down[1]); close(tq[0]); close(tq[1]);
    }
    reap(a); reap(b);
    close(tp[0]); close(tp[1]);
    heard_list(h, sizeof h, 0, 300);
    signal(SIGCHLD, SIG_DFL);
    flush_heard();
}

/* --- T: the terminal ------------------------------------------------------------- */
static const int KEYS[] = {SIGINT, SIGQUIT, SIGTSTP, SIGWINCH, SIGHUP, SIGCONT, 0};

static int bgp[2]; /* a background child's answer, which it cannot always write to the terminal */

static pid_t bg_child(int own, int act, int (*what)(void), const char *name) {
    /* A child that asks `what` with SIGTTOU/SIGTTIN as `act` says (0
     * default, 1 ignored, 2 blocked), in its own group (`own`) or in R's. */
    pid_t b = fork();
    if (b == 0) {
        if (own) setpgid(0, 0);
        int sigs[] = {SIGTTOU, SIGTTIN};
        for (int i = 0; i < 2; i++) {
            if (act == 0) signal(sigs[i], SIG_DFL);
            else if (act == 1) signal(sigs[i], SIG_IGN);
        }
        if (act == 2) {
            sigset_t m;
            sigemptyset(&m);
            sigaddset(&m, SIGTTOU);
            sigaddset(&m, SIGTTIN);
            sigprocmask(SIG_BLOCK, &m, 0);
        }
        errno = 0;
        int r = what();
        char m[256];
        int k = snprintf(m, sizeof m, "T: %s: %s\n", name, r < 0 ? ename(errno) : "0");
        (void)!write(bgp[1], m, (size_t)k);
        _exit(0);
    }
    if (own) setpgid(b, b);
    return b;
}

static void bg_wait(pid_t b, const char *name) {
    int st;
    pid_t w = waitpid(b, &st, WUNTRACED);
    char m[256];
    ssize_t k = read(bgp[0], m, sizeof m - 1);
    if (k > 0) { m[k] = 0; printf("%s", m); }
    if (w == b && WIFSTOPPED(st)) {
        printf("T: %s: stopped by %s\n", name, sname(WSTOPSIG(st)));
        kill(b, SIGCONT);
        w = waitpid(b, &st, WUNTRACED | WCONTINUED);
        if (w == b && WIFCONTINUED(st)) w = waitpid(b, &st, WUNTRACED);
        printf("T: %s, continued: %s\n", name, how(w, st));
        if (!(WIFEXITED(st) || WIFSIGNALED(st))) { kill(b, SIGKILL); waitpid(b, 0, 0); }
        k = read(bgp[0], m, sizeof m - 1);
        if (k > 0) { m[k] = 0; printf("%s", m); }
    }
}

static pid_t jgroup;
static int ask_tcsetpgrp(void) { return tcsetpgrp(0, jgroup); }
static int ask_read(void) { char c; return (int)read(0, &c, 1); }
static int ask_write(void) { return (int)write(1, "T: a background write\n", 22) < 0 ? -1 : 0; }
static int ask_tcsetattr(void) { struct termios t; tcgetattr(0, &t); return tcsetattr(0, TCSANOW, &t); }

static void key(const char *what, int want, char *h, size_t cap) {
    flush_heard();
    printf("$ ");
    fflush(stdout);
    heard_list(h, cap, want, 8000);
    printf("\nT: %s: heard %s\n", what, h);
}

static void terminal(void) {
    char h[1024];
    int st;
    pid_t w;
    snprintf(tag, sizeof tag, "R");
    on(SIGINT); on(SIGQUIT); on(SIGHUP); on(SIGWINCH); on(SIGCONT);
    signal(SIGTSTP, SIG_IGN);
    (void)!pipe(bgp);
    fcntl(bgp[0], F_SETFL, O_NONBLOCK);
    flush_heard();
    errno = 0;
    w = tcgetpgrp(0);
    printf("T: before it is R's, tcgetpgrp(0): %s\n", w < 0 ? ename(errno) : "a group");
    pid_t sid;
    errno = 0;
    int r = ioctl(0, TIOCGSID, &sid);
    printf("T: before it is R's, TIOCGSID: %s\n", r < 0 ? ename(errno) : "0");
    {
        pid_t c = fork();
        if (c == 0) {
            errno = 0;
            int r2 = ioctl(0, TIOCSCTTY, 0);
            printf("T: TIOCSCTTY by a process that leads no session: %s\n", r2 < 0 ? ename(errno) : "0");
            _exit(0);
        }
        waitpid(c, 0, 0);
    }
    ANS("T: TIOCSCTTY(0) by R, a session leader with no terminal", ioctl(0, TIOCSCTTY, 0));
    printf("T: tcgetpgrp(0) is R's group: %s\n", yesno(tcgetpgrp(0) == getpgrp()));
    sid = 0;
    r = ioctl(0, TIOCGSID, &sid);
    printf("T: TIOCGSID: %s, R's session %s\n", r < 0 ? ename(errno) : "0", yesno(sid == getsid(0)));
    printf("T: tcgetsid(0) is R's session: %s\n", yesno(tcgetsid(0) == getsid(0)));
    ANS("T: TIOCSCTTY(0) again, its own terminal", ioctl(0, TIOCSCTTY, 0));
    {
        struct pstat ps = pstat_of(getpid());
        printf("T: R's /proc stat: tty_nr the terminal's number %s, tpgid R's group %s\n", yesno(ps.tty == tty_number(0) && ps.tty != 0), yesno(ps.tpgid == getpgrp()));
        int fd = open("/dev/tty", O_RDWR);
        printf("T: /dev/tty: %s\n", fd < 0 ? ename(errno) : "opened");
        if (fd >= 0) {
            printf("T: /dev/tty's tcgetpgrp is R's group: %s\n", yesno(tcgetpgrp(fd) == getpgrp()));
            close(fd);
        }
    }
    {
        pid_t x = fork();
        if (x == 0) {
            setsid();
            errno = 0;
            int r2 = ioctl(0, TIOCSCTTY, 0);
            printf("T: TIOCSCTTY(0) by another session's leader, R's terminal: %s\n", r2 < 0 ? ename(errno) : "0");
            errno = 0;
            r2 = tcgetpgrp(0);
            printf("T: tcgetpgrp(0) by another session's process: %s\n", r2 < 0 ? ename(errno) : "a group");
            pid_t s2;
            errno = 0;
            r2 = ioctl(0, TIOCGSID, &s2);
            printf("T: TIOCGSID by another session's process: %s\n", r2 < 0 ? ename(errno) : "0");
            errno = 0;
            r2 = tcsetpgrp(0, getpgrp());
            printf("T: tcsetpgrp(0, its group) by another session's process: %s\n", r2 < 0 ? ename(errno) : "0");
            _exit(0);
        }
        waitpid(x, 0, 0);
    }
    /* A job in its own group, handed the terminal. */
    pid_t j1 = idle(0, "J1", KEYS);
    pid_t j2 = idle(j1, "J2", KEYS);
    jgroup = j1;
    sigset_t ttou, old;
    sigemptyset(&ttou);
    sigaddset(&ttou, SIGTTOU);
    sigprocmask(SIG_BLOCK, &ttou, &old);
    ANS("T: tcsetpgrp(0, job) by R, SIGTTOU blocked", tcsetpgrp(0, j1));
    sigprocmask(SIG_SETMASK, &old, 0);
    printf("T: tcgetpgrp(0) is the job's group: %s\n", yesno(tcgetpgrp(0) == j1));
    {
        struct pstat ps = pstat_of(j2);
        printf("T: a job member's /proc stat: tty_nr the terminal's %s, tpgid the job's group %s\n", yesno(ps.tty == tty_number(0)), yesno(ps.tpgid == j1));
    }
    /* R itself is in the background now. */
    {
        signal(SIGTTOU, SIG_DFL);
        errno = 0;
        int r2 = tcsetpgrp(0, getpgrp());
        int e = errno;
        printf("T: tcsetpgrp(0, R's group) by R in the background (its group is orphaned), SIGTTOU default: %s\n", r2 < 0 ? ename(e) : "0");
        signal(SIGTTOU, SIG_IGN);
    }
    jgroup = j1;
    bg_wait(bg_child(1, 0, ask_tcsetpgrp, "tcsetpgrp from a background group that is not orphaned, SIGTTOU default"),
            "tcsetpgrp from a background group that is not orphaned, SIGTTOU default");
    bg_wait(bg_child(1, 1, ask_tcsetpgrp, "tcsetpgrp from the background, SIGTTOU ignored"), "tcsetpgrp from the background, SIGTTOU ignored");
    bg_wait(bg_child(1, 2, ask_tcsetpgrp, "tcsetpgrp from the background, SIGTTOU blocked"), "tcsetpgrp from the background, SIGTTOU blocked");
    bg_wait(bg_child(0, 0, ask_tcsetpgrp, "tcsetpgrp from the background, R's orphaned group, SIGTTOU default"),
            "tcsetpgrp from the background, R's orphaned group, SIGTTOU default");
    {
        pid_t other = idle(-2, "X", 0);
        ANS("T: tcsetpgrp(0, a group of another session)", tcsetpgrp(0, other));
        ANS("T: tcsetpgrp(0, a group that does not exist)", tcsetpgrp(0, 999999));
        ANS("T: tcsetpgrp(0, 0)", tcsetpgrp(0, 0));
        ANS("T: tcsetpgrp(0, -1)", tcsetpgrp(0, -1));
        reap(other);
    }
    /* Reads and writes from the background. */
    bg_wait(bg_child(1, 0, ask_read, "a background read, SIGTTIN default"), "a background read, SIGTTIN default");
    bg_wait(bg_child(1, 1, ask_read, "a background read, SIGTTIN ignored"), "a background read, SIGTTIN ignored");
    bg_wait(bg_child(1, 2, ask_read, "a background read, SIGTTIN blocked"), "a background read, SIGTTIN blocked");
    bg_wait(bg_child(0, 0, ask_read, "a background read from R's orphaned group, SIGTTIN default"), "a background read from R's orphaned group, SIGTTIN default");
    bg_wait(bg_child(1, 0, ask_write, "a background write without TOSTOP, SIGTTOU default"), "a background write without TOSTOP, SIGTTOU default");
    bg_wait(bg_child(1, 0, ask_tcsetattr, "tcsetattr from the background, SIGTTOU default"), "tcsetattr from the background, SIGTTOU default");
    bg_wait(bg_child(1, 1, ask_tcsetattr, "tcsetattr from the background, SIGTTOU ignored"), "tcsetattr from the background, SIGTTOU ignored");
    {
        struct termios t, t0;
        tcgetattr(0, &t0);
        t = t0;
        t.c_lflag |= TOSTOP;
        ANS("T: TOSTOP set by R (SIGTTOU ignored)", tcsetattr(0, TCSANOW, &t));
        bg_wait(bg_child(1, 0, ask_write, "a background write with TOSTOP, SIGTTOU default"), "a background write with TOSTOP, SIGTTOU default");
        bg_wait(bg_child(1, 1, ask_write, "a background write with TOSTOP, SIGTTOU ignored"), "a background write with TOSTOP, SIGTTOU ignored");
        bg_wait(bg_child(1, 2, ask_write, "a background write with TOSTOP, SIGTTOU blocked"), "a background write with TOSTOP, SIGTTOU blocked");
        bg_wait(bg_child(0, 0, ask_write, "a background write with TOSTOP from R's orphaned group, SIGTTOU default"), "a background write with TOSTOP from R's orphaned group, SIGTTOU default");
        tcsetattr(0, TCSANOW, &t0);
    }
    /* The window size: SIGWINCH for the foreground group when it changes. */
    {
        flush_heard();
        struct winsize ws0, ws;
        ioctl(0, TIOCGWINSZ, &ws0);
        ws = ws0;
        ws.ws_row = 33; ws.ws_col = 77;
        ANS("T: TIOCSWINSZ 33x77", ioctl(0, TIOCSWINSZ, &ws));
        heard_list(h, sizeof h, 2, 1500);
        printf("T: the window's change, heard %s\n", h);
        ioctl(0, TIOCSWINSZ, &ws);
        heard_list(h, sizeof h, 0, 300);
        printf("T: the same size again, heard %s\n", h);
        ioctl(0, TIOCSWINSZ, &ws0);
        heard_list(h, sizeof h, 2, 1500);
    }
    /* The keys, with the job in the foreground. */
    key("^C with the job in the foreground", 2, h, sizeof h);
    key("^\\ with the job in the foreground", 2, h, sizeof h);
    key("^Z with the job in the foreground, both handling it", 2, h, sizeof h);
    pid_t k = idle(0, "K", 0);
    sigprocmask(SIG_BLOCK, &ttou, &old);
    tcsetpgrp(0, k);
    sigprocmask(SIG_SETMASK, &old, 0);
    flush_heard();
    printf("$ ");
    fflush(stdout);
    w = waitpid(k, &st, WUNTRACED);
    printf("\nT: ^Z with a job at its default in the foreground: %s\n", how(w, st));
    kill(k, SIGCONT);
    waitpid(k, &st, WCONTINUED);
    printf("$ ");
    fflush(stdout);
    w = waitpid(k, &st, WUNTRACED);
    printf("\nT: ^C with that job continued in the foreground: %s\n", how(w, st));
    heard_list(h, sizeof h, 0, 300);
    printf("T: the jobs that were not in the foreground heard %s\n", h);
    sigprocmask(SIG_BLOCK, &ttou, &old);
    ANS("T: tcsetpgrp(0, R's group) back", tcsetpgrp(0, getpgrp()));
    sigprocmask(SIG_SETMASK, &old, 0);
    {
        pid_t c = fork();
        if (c == 0) {
            errno = 0;
            int r2 = ioctl(0, TIOCNOTTY);
            int e = errno;
            errno = 0;
            int g = tcgetpgrp(0);
            printf("T: TIOCNOTTY by a non-leader: %s; its tcgetpgrp(0) after: %s\n", r2 < 0 ? ename(e) : "0", g < 0 ? ename(errno) : "a group");
            _exit(0);
        }
        waitpid(c, 0, 0);
        heard_list(h, sizeof h, 0, 300);
        printf("T: R still has it: %s; heard %s\n", yesno(tcgetpgrp(0) == getpgrp()), h);
    }
    reap(j1); reap(j2);
    flush_heard();
    /* Taken by another session's leader with arg 1: privileged only. */
    {
        pid_t x = fork();
        if (x == 0) {
            setsid();
            errno = 0;
            int r2 = ioctl(0, TIOCSCTTY, 1);
            int e = errno;
            printf("T: TIOCSCTTY(1) by another session's leader: %s\n", r2 < 0 ? ename(e) : "0");
            if (r2 == 0) {
                printf("T: it leads the terminal's session now: %s\n", yesno(tcgetsid(0) == getsid(0)));
                ioctl(0, TIOCNOTTY);
            }
            _exit(0);
        }
        waitpid(x, 0, 0);
        heard_list(h, sizeof h, 0, 300);
        errno = 0;
        int g = tcgetpgrp(0);
        printf("T: R's tcgetpgrp(0) after: %s; heard %s\n", g < 0 ? ename(errno) : "a group", h);
        if (g < 0) ioctl(0, TIOCSCTTY, 0);
    }
}

/* --- V: VMIN and VTIME (pax#66), R in the foreground, echo off ------------------- */
static void vread(const char *what, int vmin, int vtime, int prompt) {
    struct termios t0, t;
    tcgetattr(0, &t0);
    t = t0;
    t.c_lflag &= ~(ICANON | ECHO);
    t.c_cc[VMIN] = (cc_t)vmin;
    t.c_cc[VTIME] = (cc_t)vtime;
    tcsetattr(0, TCSANOW, &t);
    if (prompt) printf("$ "); /* the third read is typed at by a timed step, which waits for no prompt */
    fflush(stdout);
    char b[16];
    ssize_t n = read(0, b, sizeof b);
    tcsetattr(0, TCSANOW, &t0);
    printf("\nV: %s: read %zd bytes \"", what, n);
    for (ssize_t i = 0; i < n; i++) putchar(b[i] >= 32 && b[i] < 127 ? b[i] : '?');
    printf("\"\n");
}

static void vmin_vtime(void) {
    sigset_t ttou, old;
    sigemptyset(&ttou);
    sigaddset(&ttou, SIGTTOU);
    sigprocmask(SIG_BLOCK, &ttou, &old);
    printf("V: R has the terminal, in the foreground: %s\n", yesno(tcgetpgrp(0) == getpgrp()));
    vread("VMIN 2, VTIME 0, one key and a second 1.5 s later", 2, 0, 1);
    vread("VMIN 5, VTIME 5, two keys, then nothing", 5, 5, 1);
    vread("VMIN 5, VTIME 5, nothing for 1.5 s, then one key", 5, 5, 0);
    struct winsize ws;
    memset(&ws, 0, sizeof ws);
    int r = ioctl(0, TIOCGWINSZ, &ws);
    printf("V: TIOCGWINSZ after the keys: %s, %d rows %d cols\n", r < 0 ? ename(errno) : "0", ws.ws_row, ws.ws_col);
    sigprocmask(SIG_SETMASK, &old, 0);
}

/* --- H: hangup, and the orphaned group ------------------------------------------- */
static void hangup(void) {
    char h[1024];
    snprintf(tag, sizeof tag, "R");
    signal(SIGHUP, SIG_IGN);
    on(SIGCONT);
    flush_heard();
    errno = 0;
    int r = ioctl(0, TIOCNOTTY);
    int e = errno;
    heard_list(h, sizeof h, 0, 300);
    printf("H: TIOCNOTTY by R, the session leader (SIGHUP ignored): %s, R's group heard %s\n", r < 0 ? ename(e) : "0", h);
    signal(SIGCONT, SIG_DFL);
    int s[2];
    (void)!pipe(s);
    pid_t l = fork();
    if (l == 0) {
        snprintf(tag, sizeof tag, "L");
        setsid();
        int r2 = ioctl(0, TIOCSCTTY, 0);
        pid_t f = fork();
        if (f == 0) {
            snprintf(tag, sizeof tag, "F");
            on(SIGHUP); on(SIGCONT);
            (void)!write(s[1], "f", 1);
            nap(1500);
            int fl = fcntl(0, F_GETFL);
            fcntl(0, F_SETFL, fl | O_NONBLOCK);
            char c;
            errno = 0;
            ssize_t k = read(0, &c, 1);
            int e2 = errno;
            fcntl(0, F_SETFL, fl);
            errno = 0;
            pid_t g = tcgetpgrp(0);
            char b[160];
            int n = snprintf(b, sizeof b, "H: the foreground member after: a nonblocking read %s, tcgetpgrp %s\n",
                             k < 0 ? ename(e2) : k == 0 ? "0" : "a byte", g < 0 ? ename(errno) : "a group");
            (void)!write(rep[1], b, (size_t)n);
            _exit(0);
        }
        pid_t g2 = fork();
        if (g2 == 0) {
            snprintf(tag, sizeof tag, "G");
            on(SIGHUP); on(SIGCONT);
            setpgid(0, 0);
            (void)!write(s[1], "g", 1);
            raise(SIGSTOP);
            nap(1500);
            _exit(0);
        }
        setpgid(g2, g2);
        char c;
        (void)!read(s[0], &c, 1);
        (void)!read(s[0], &c, 1);
        int st;
        waitpid(g2, &st, WUNTRACED);
        char b[160];
        int n = snprintf(b, sizeof b, "H: L took the terminal: %s; its background member stopped: %s\n", r2 < 0 ? ename(errno) : "0", yesno(WIFSTOPPED(st)));
        (void)!write(rep[1], b, (size_t)n);
        _exit(0);
    }
    waitpid(l, 0, 0);
    nap(2500);
    char buf[4096];
    size_t len = 0;
    ssize_t k;
    while ((k = read(rep[0], buf + len, sizeof buf - 1 - len)) > 0) len += (size_t)k;
    buf[len] = 0;
    /* The report lines first, as they came; then what was heard, sorted. */
    char *heardv[64], *lines[16];
    int nh = 0, nl = 0;
    for (char *q = strtok(buf, "\n"); q; q = strtok(NULL, "\n")) {
        if (strncmp(q, "H: ", 3) == 0) { if (nl < 16) lines[nl++] = q; }
        else if (nh < 64) heardv[nh++] = q;
    }
    for (int i = 0; i < nl; i++) printf("%s\n", lines[i]);
    qsort(heardv, (size_t)nh, sizeof heardv[0], cmp_str);
    printf("H: after the leader L ended, heard ");
    for (int i = 0; i < nh; i++) printf("%s%s", i ? "," : "", heardv[i]);
    printf("%s\n", nh ? "" : "-");
    close(s[0]); close(s[1]);
    while (waitpid(-1, 0, WNOHANG) > 0) {}
}

static void soak(long n) {
    long wrong = 0;
    int st;
    sigset_t ttou;
    sigemptyset(&ttou);
    sigaddset(&ttou, SIGTTOU);
    sigprocmask(SIG_BLOCK, &ttou, 0);
    int have = ioctl(0, TIOCSCTTY, 0) == 0;
    for (long i = 0; i < n; i++) {
        pid_t c = fork();
        if (c == 0) { setpgid(0, 0); for (;;) nap(50); }
        setpgid(c, c);
        if (kill(-c, SIGSTOP) != 0) wrong++;
        if (waitpid(c, &st, WUNTRACED) != c || !WIFSTOPPED(st)) wrong++;
        if (have && tcsetpgrp(0, c) != 0) wrong++;
        if (have && tcgetpgrp(0) != c) wrong++;
        if (have && tcsetpgrp(0, getpgrp()) != 0) wrong++;
        if (kill(-c, SIGCONT) != 0) wrong++;
        if (waitpid(c, &st, WCONTINUED) != c || !WIFCONTINUED(st)) wrong++;
        if (kill(0, 0) != 0) wrong++;
        kill(c, SIGKILL);
        if (waitpid(c, &st, 0) != c || !WIFSIGNALED(st)) wrong++;
        if ((i + 1) % (n / 4 ? n / 4 : 1) == 0) {
            char b[256] = "";
            int fd = open("/proc/meminfo", O_RDONLY);
            if (fd >= 0) { ssize_t k = read(fd, b, sizeof b - 1); b[k > 0 ? k : 0] = 0; close(fd); }
            char *m = strstr(b, "MemFree:");
            char *e = m ? strchr(m, '\n') : 0;
            if (e) *e = 0;
            printf("~soak: %ld rounds, %ld wrong; %s\n", i + 1, wrong, m ? m : "MemFree: ?");
        }
    }
    printf("soak: %ld rounds of nine calls, %ld wrong answers\n", n, wrong);
}

int main(int argc, char **argv) {
    setvbuf(stdout, 0, _IOLBF, 0);
    if (argc > 1 && strcmp(argv[1], "idle") == 0) { for (;;) nap(100); }
    if (pipe(rep) < 0) return 2;
    fcntl(rep[0], F_SETFL, O_NONBLOCK);
    root = geteuid() == 0;
    snprintf(tag, sizeof tag, "main");
    on(SIGHUP); on(SIGCONT);
    printf("jobs: px48's probe, as %s\n", root ? "root" : "a user");
    printf("main: leads its session, with the terminal in its group's hands: %s\n", yesno(getsid(0) == getpid() && tcgetpgrp(0) == getpgrp()));
    errno = 0;
    int r = ioctl(0, TIOCNOTTY);
    int e = errno;
    char h[256];
    heard_list(h, sizeof h, 2, 1500);
    printf("main: TIOCNOTTY by the session leader: %s, heard %s\n", r < 0 ? ename(e) : "0", h);
    errno = 0;
    printf("main: tcgetpgrp(0) after: %s\n", tcgetpgrp(0) < 0 ? ename(errno) : "a group");
    signal(SIGHUP, SIG_IGN);
    signal(SIGCONT, SIG_DFL);
    pid_t R = fork();
    if (R == 0) {
        setsid();
        if (argc > 2 && strcmp(argv[1], "soak") == 0) {
            soak(atol(argv[2]));
            _exit(0);
        }
        groups_and_sessions();
        kill_groups();
        stops();
        terminal();
        vmin_vtime();
        hangup();
        fflush(stdout);
        _exit(0);
    }
    int st;
    waitpid(R, &st, 0);
    printf("done: R %s\n", how(R, st));
    return 0;
}
