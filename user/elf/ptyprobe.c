/* px111: pseudo-terminals, asked of the kernel. `/dev/ptmx` and
 * `/dev/pts`, the lock and the number, the slave's name, mode, owner and
 * group; termios on a pty (canonical and raw input, the echo, the
 * terminal's signal keys, VMIN and VTIME, OPOST and ONLCR, IXON); the
 * controlling terminal (setsid, TIOCSCTTY, TIOCNOTTY, /dev/tty), the
 * foreground group and the background rules; the window size and
 * SIGWINCH; the hangup a master's close is; poll and O_NONBLOCK on both
 * sides and a full buffer each way; many ptys at once and none left
 * after they close. Run as the first program on PAX's console (as root,
 * then through `as 1000 1000`) and on a real Linux under QEMU
 * (notes/px111/vminit.c: devtmpfs at /dev, devpts at /dev/pts with no
 * options), its transcript held line for line.
 *
 *   ptyprobe          every section: O T C W H P M
 *   ptyprobe drive    the session row: pelt (/bin/sh -i) on a pty this
 *                     program drives from the master side (S)
 *
 * The program as started ignores SIGHUP, gives up whatever terminal it
 * was started with (TIOCNOTTY; PAX's first programs have the console,
 * Linux's init's children have none) and starts R, which makes a session
 * of its own; every section runs in a child of R that makes its own
 * session too, so the shape is the same on both systems whatever is
 * above them. Every line is `section.case: answer`; no pid, time or
 * address is printed, bytes are printed escaped in quotes, and what
 * several processes heard is printed sorted, each once. A wait for
 * bytes the other side has not yet handed over settles: it reads until
 * nothing more comes for 150 ms (a Linux pty hands bytes to its line
 * discipline after the write returns).
 *
 * Written from pty(7), pts(4), ioctl_tty(2) and the TIOC*(2const) pages,
 * termios(3), posix_openpt(3), grantpt(3), unlockpt(3), ptsname(3),
 * ttyname(3), credentials(7), proc_pid_stat(5), proc_sys_kernel(5)
 * (man-pages 6.7) and POSIX.1-2024's General Terminal Interface (XBD
 * chapter 11), XSH posix_openpt, grantpt, unlockpt, ptsname, tcsetpgrp,
 * tcgetsid; the shapes of px48's user/elf/jobs.c. No C library's,
 * kernel's or shell's source was read. Written for this lane. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#ifndef TIOCGPTPEER
#define TIOCGPTPEER 0x5441
#endif
#ifndef TIOCGPTLCK
#define TIOCGPTLCK 0x80045439
#endif

static int rep[2];      /* what handlers heard: "TAG:SIG\n" */
static char tag[16] = "?";
static int root;

static const char *sname(int s) {
    switch (s) {
    case SIGHUP: return "HUP"; case SIGINT: return "INT"; case SIGQUIT: return "QUIT";
    case SIGTERM: return "TERM"; case SIGCHLD: return "CHLD"; case SIGCONT: return "CONT";
    case SIGSTOP: return "STOP"; case SIGTSTP: return "TSTP"; case SIGTTIN: return "TTIN";
    case SIGTTOU: return "TTOU"; case SIGWINCH: return "WINCH"; case SIGKILL: return "KILL";
    case SIGUSR1: return "USR1"; case SIGPIPE: return "PIPE";
    default: { static char b[16]; snprintf(b, sizeof b, "SIG%d", s); return b; }
    }
}

static const char *ename(int e) {
    switch (e) {
    case 0: return "0";
    case EPERM: return "EPERM"; case ENOENT: return "ENOENT"; case ESRCH: return "ESRCH";
    case EINTR: return "EINTR"; case EIO: return "EIO"; case ENXIO: return "ENXIO";
    case EBADF: return "EBADF"; case ECHILD: return "ECHILD"; case EAGAIN: return "EAGAIN";
    case EACCES: return "EACCES"; case EFAULT: return "EFAULT"; case EINVAL: return "EINVAL";
    case ENOTTY: return "ENOTTY"; case ENOSPC: return "ENOSPC"; case EPIPE: return "EPIPE";
    case EMFILE: return "EMFILE"; case ENODEV: return "ENODEV"; case EOPNOTSUPP: return "EOPNOTSUPP";
    default: { static char b[32]; snprintf(b, sizeof b, "errno%d", e); return b; }
    }
}

static const char *yesno(int c) { return c ? "yes" : "no"; }

static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap); /* line-buffered: each row reaches the console whole, in one write */
    va_end(ap);
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

/* The answer of a call that gives -1 and errno, or 0/a count. */
static const char *rv(long r, int e) {
    static char b[32];
    if (r < 0) return ename(e);
    snprintf(b, sizeof b, "%ld", r);
    return b;
}

#define ANS(name, expr) do { errno = 0; long r_ = (long)(expr); int e_ = errno; say("%s: %s\n", name, rv(r_, e_)); } while (0)

/* Bytes as a quoted C-like string. */
static const char *esc(const unsigned char *b, long n) {
    static char o[8192];
    size_t k = 0;
    o[k++] = '"';
    for (long i = 0; i < n && k < sizeof o - 8; i++) {
        unsigned c = b[i];
        if (c == '\r') { o[k++] = '\\'; o[k++] = 'r'; }
        else if (c == '\n') { o[k++] = '\\'; o[k++] = 'n'; }
        else if (c == '\t') { o[k++] = '\\'; o[k++] = 't'; }
        else if (c == '\b') { o[k++] = '\\'; o[k++] = 'b'; }
        else if (c == '"' || c == '\\') { o[k++] = '\\'; o[k++] = (char)c; }
        else if (c < 32 || c >= 127) k += (size_t)snprintf(o + k, 8, "\\x%02x", c);
        else o[k++] = (char)c;
    }
    o[k++] = '"';
    o[k] = 0;
    return o;
}

/* --- what handlers heard ------------------------------------------------- */

static void heard(int sig) {
    char b[48];
    int n = 0;
    for (const char *p = tag; *p && n < 15; p++) b[n++] = *p;
    b[n++] = ':';
    for (const char *s = sname(sig); *s; s++) b[n++] = *s;
    b[n++] = '\n';
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

static int cmp_str(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }

/* What the handlers reported, sorted, each once, joined with commas ("-"
 * for nothing): waits until `want` lines came or `ms` passed, then 150 ms
 * longer for anything not expected. */
static const char *heard_list(int want, int ms) {
    static char out[1024];
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
        if (i && strcmp(v[i], v[i - 1]) == 0) continue;
        k += (size_t)snprintf(out + k, sizeof out > k ? sizeof out - k : 0, "%s%s", m++ ? "," : "", v[i]);
    }
    if (!n) snprintf(out, sizeof out, "-");
    return out;
}

static void flush_heard(void) { char b[4096]; while (read(rep[0], b, sizeof b) > 0) {} }

static const char *how(pid_t w, int st) {
    static char b[64];
    if (w == 0) return "0 (nothing new)";
    if (w < 0) return ename(errno);
    if (WIFSTOPPED(st)) snprintf(b, sizeof b, "stopped by %s", sname(WSTOPSIG(st)));
    else if (WIFCONTINUED(st)) snprintf(b, sizeof b, "continued");
    else if (WIFEXITED(st)) snprintf(b, sizeof b, "exited %d", WEXITSTATUS(st));
    else if (WIFSIGNALED(st)) snprintf(b, sizeof b, "killed by %s", sname(WTERMSIG(st)));
    else snprintf(b, sizeof b, "status 0x%x", st);
    return b;
}

/* --- ptys ------------------------------------------------------------------ */

static int mopen(int extra) { return open("/dev/ptmx", O_RDWR | O_NOCTTY | extra); }

static int sopen(int m, int flags) {
    char name[64];
    if (ptsname_r(m, name, sizeof name) != 0) return -1;
    return open(name, O_RDWR | flags);
}

/* A pair, unlocked, the slave opened with O_NOCTTY. 0 or -1. */
static int pair(int *m, int *s) {
    *m = mopen(0);
    if (*m < 0) return -1;
    if (unlockpt(*m) != 0) { close(*m); return -1; }
    *s = sopen(*m, O_NOCTTY);
    if (*s < 0) { close(*m); return -1; }
    return 0;
}

static int ptn(int m) { unsigned n = 0; return ioctl(m, TIOCGPTN, &n) == 0 ? (int)n : -1; }

static void raw(int s) {
    struct termios t;
    tcgetattr(s, &t);
    cfmakeraw(&t);
    tcsetattr(s, TCSANOW, &t);
}

static void lset(int fd, tcflag_t on_, tcflag_t off) {
    struct termios t;
    tcgetattr(fd, &t);
    t.c_lflag = (t.c_lflag | on_) & ~off;
    tcsetattr(fd, TCSANOW, &t);
}

static void oset(int fd, tcflag_t on_, tcflag_t off) {
    struct termios t;
    tcgetattr(fd, &t);
    t.c_oflag = (t.c_oflag | on_) & ~off;
    tcsetattr(fd, TCSANOW, &t);
}

static void iset(int fd, tcflag_t on_, tcflag_t off) {
    struct termios t;
    tcgetattr(fd, &t);
    t.c_iflag = (t.c_iflag | on_) & ~off;
    tcsetattr(fd, TCSANOW, &t);
}

static void ccset(int fd, int i, int v) {
    struct termios t;
    tcgetattr(fd, &t);
    t.c_cc[i] = (cc_t)v;
    tcsetattr(fd, TCSANOW, &t);
}

/* Read what `fd` gives: wait up to `first` ms for a first byte, then go on
 * while bytes come within 150 ms. The count, or -errno of a failed read
 * when nothing was read. */
static long settle(int fd, unsigned char *buf, long cap, int first) {
    long n = 0;
    int wait = first;
    for (;;) {
        struct pollfd p = {fd, POLLIN, 0};
        int r = poll(&p, 1, wait);
        if (r <= 0) break;
        if (!(p.revents & POLLIN)) {
            if (n == 0 && (p.revents & (POLLHUP | POLLERR))) {
                errno = 0;
                ssize_t k = read(fd, buf, (size_t)cap);
                if (k < 0) return -errno;
                return k;
            }
            break;
        }
        ssize_t k = read(fd, buf + n, (size_t)(cap - n));
        if (k < 0) { if (n == 0) return -errno; break; }
        if (k == 0) break;
        n += k;
        if (n >= cap) break;
        wait = 150;
    }
    return n;
}

/* `name: <count> "<bytes>"` of what settles from fd, or the errno. */
static void got(const char *name, int fd, int first) {
    unsigned char b[4096];
    long n = settle(fd, b, sizeof b, first);
    if (n < 0) say("%s: %s\n", name, ename((int)-n));
    else say("%s: %ld %s\n", name, n, esc(b, n));
}

static void put(int fd, const char *s) { (void)!write(fd, s, strlen(s)); }

static const char *revents(int fd, short ev, int ms) {
    static char b[64];
    struct pollfd p = {fd, ev, 0};
    int r = poll(&p, 1, ms);
    if (r < 0) return ename(errno);
    if (r == 0) return "-";
    b[0] = 0;
    if (p.revents & POLLIN) strcat(b, "IN ");
    if (p.revents & POLLPRI) strcat(b, "PRI ");
    if (p.revents & POLLOUT) strcat(b, "OUT ");
    if (p.revents & POLLERR) strcat(b, "ERR ");
    if (p.revents & POLLHUP) strcat(b, "HUP ");
    if (p.revents & POLLNVAL) strcat(b, "NVAL ");
    size_t l = strlen(b);
    if (l) b[l - 1] = 0;
    return b;
}

static const char *ftype(mode_t m) {
    return S_ISCHR(m) ? "chr" : S_ISDIR(m) ? "dir" : S_ISREG(m) ? "reg" : S_ISLNK(m) ? "lnk" : "other";
}

static void stat_row(const char *name, const char *path) {
    struct stat st;
    if (stat(path, &st) != 0) { say("%s: %s\n", name, ename(errno)); return; }
    if (S_ISCHR(st.st_mode))
        say("%s: %s %u:%u mode %04o uid %u gid %u\n", name, ftype(st.st_mode), major(st.st_rdev), minor(st.st_rdev),
            st.st_mode & 07777, st.st_uid, st.st_gid);
    else
        say("%s: %s mode %04o uid %u gid %u\n", name, ftype(st.st_mode), st.st_mode & 07777, st.st_uid, st.st_gid);
}

static void fstat_row(const char *name, int fd) {
    struct stat st;
    if (fstat(fd, &st) != 0) { say("%s: %s\n", name, ename(errno)); return; }
    say("%s: %s %u:%u mode %04o\n", name, ftype(st.st_mode), major(st.st_rdev), minor(st.st_rdev), st.st_mode & 07777);
}

/* The names in a directory, sorted, space-separated. */
static const char *listing(const char *path) {
    static char out[4096];
    DIR *d = opendir(path);
    if (!d) return ename(errno);
    char *v[512];
    int n = 0;
    struct dirent *e;
    while ((e = readdir(d)) && n < 512) v[n++] = strdup(e->d_name);
    closedir(d);
    qsort(v, (size_t)n, sizeof v[0], cmp_str);
    size_t k = 0;
    out[0] = 0;
    for (int i = 0; i < n; i++) {
        if (k < sizeof out - 64) k += (size_t)snprintf(out + k, sizeof out - k, "%s%s", i ? " " : "", v[i]);
        free(v[i]);
    }
    return out;
}

/* /dev/pts's entries other than ., .. and ptmx: how many. */
static int pts_count(void) {
    DIR *d = opendir("/dev/pts");
    if (!d) return -1;
    int n = 0;
    struct dirent *e;
    while ((e = readdir(d)))
        if (strcmp(e->d_name, ".") && strcmp(e->d_name, "..") && strcmp(e->d_name, "ptmx")) n++;
    closedir(d);
    return n;
}

static const char *pty_nr(void) {
    static char b[64];
    int fd = open("/proc/sys/kernel/pty/nr", O_RDONLY);
    if (fd < 0) return ename(errno);
    ssize_t n = read(fd, b, sizeof b - 1);
    close(fd);
    if (n <= 0) return "unread";
    b[n] = 0;
    if (n && b[n - 1] == '\n') b[n - 1] = 0;
    return b;
}

static const char *link_of(int fd) {
    static char b[256];
    char p[64];
    snprintf(p, sizeof p, "/proc/self/fd/%d", fd);
    ssize_t n = readlink(p, b, sizeof b - 1);
    if (n < 0) return ename(errno);
    b[n] = 0;
    return b;
}

/* /proc/<pid>/stat: fields 5 to 8. */
struct pstat { long pgrp, sess, tty, tpgid; int ok; };
static struct pstat pstat_of(pid_t p) {
    struct pstat r = {0, 0, 0, 0, 0};
    char path[64], b[1024];
    snprintf(path, sizeof path, "/proc/%d/stat", (int)p);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return r;
    ssize_t n = read(fd, b, sizeof b - 1);
    close(fd);
    if (n <= 0) return r;
    b[n] = 0;
    char *q = strrchr(b, ')');
    char st;
    long ppid;
    if (q && sscanf(q + 2, "%c %ld %ld %ld %ld %ld", &st, &ppid, &r.pgrp, &r.sess, &r.tty, &r.tpgid) == 6) r.ok = 1;
    return r;
}

/* --- children -------------------------------------------------------------- */

/* A child that waits until killed: `pg` 0 a new group, > 0 that group, -1
 * stay; `sigs` the signals it reports under `name`. */
static pid_t idle(pid_t pg, const char *name, const int *sigs) {
    int s[2];
    (void)!pipe(s);
    fflush(stdout);
    pid_t p = fork();
    if (p == 0) {
        close(s[0]);
        snprintf(tag, sizeof tag, "%s", name);
        static const int reset[] = {SIGHUP, SIGINT, SIGQUIT, SIGCONT, SIGTSTP, SIGTTIN, SIGTTOU, SIGWINCH, 0};
        for (const int *q = reset; *q; q++) signal(*q, SIG_DFL);
        for (const int *q = sigs; q && *q; q++) on(*q);
        if (pg >= 0) setpgid(0, pg);
        (void)!write(s[1], "k", 1);
        close(s[1]);
        for (;;) nap(20);
    }
    close(s[1]);
    if (pg >= 0) setpgid(p, pg ? pg : p);
    char c;
    (void)!read(s[0], &c, 1);
    close(s[0]);
    return p;
}

static void reap(pid_t p) { kill(p, SIGKILL); waitpid(p, 0, 0); }

/* Run `fn` in a child that leads a session of its own; wait for it. */
static void section(void (*fn)(void)) {
    fflush(stdout);
    pid_t c = fork();
    if (c == 0) {
        setsid();
        flush_heard();
        fn();
        fflush(stdout);
        _exit(0);
    }
    int st;
    pid_t w = waitpid(c, &st, 0);
    if (!(w == c && WIFEXITED(st) && WEXITSTATUS(st) == 0)) say("section: ended %s\n", how(w, st));
}

/* --- O: opening ------------------------------------------------------------ */

static void sec_open(void) {
    struct stat a, b;
    stat_row("O1 stat /dev/ptmx", "/dev/ptmx");
    stat_row("O2 stat /dev/pts", "/dev/pts");
    stat_row("O3 stat /dev/pts/ptmx", "/dev/pts/ptmx");
    say("O4 /dev/pts is a file system of its own: %s\n", yesno(stat("/dev", &a) == 0 && stat("/dev/pts", &b) == 0 && a.st_dev != b.st_dev));
    if (stat("/dev/pts", &a) == 0 && stat("/dev/pts/ptmx", &b) == 0)
        say("O5 inodes: /dev/pts %lu, /dev/pts/ptmx %lu\n", (unsigned long)a.st_ino, (unsigned long)b.st_ino);
    else say("O5 inodes: %s\n", ename(errno));
    say("O6 /dev/pts lists: %s\n", listing("/dev/pts"));
    say("O7 /proc/sys/kernel/pty/nr: %s\n", pty_nr());
    errno = 0;
    int m = open("/dev/ptmx", O_RDWR | O_NOCTTY);
    say("O8 open /dev/ptmx: %s\n", m >= 0 ? "a descriptor" : ename(errno));
    if (m < 0) return;
    fstat_row("O9 fstat of the master", m);
    unsigned n = 99;
    errno = 0;
    int r = ioctl(m, TIOCGPTN, &n);
    say("O10 TIOCGPTN: %s, number %u\n", rv(r, errno), n);
    char name[64] = "";
    errno = 0;
    r = ptsname_r(m, name, sizeof name);
    say("O11 ptsname_r: %s %s\n", r ? ename(r) : "0", name);
    char *pn = ptsname(m);
    say("O12 ptsname: %s\n", pn ? pn : ename(errno));
    int lk = 99;
    errno = 0;
    r = ioctl(m, TIOCGPTLCK, &lk);
    say("O13 TIOCGPTLCK of a new master: %s, locked %d\n", rv(r, errno), lk);
    stat_row("O14 stat of its slave", name);
    if (stat(name, &a) == 0) say("O15 the slave's inode: %lu\n", (unsigned long)a.st_ino);
    say("O16 /dev/pts lists: %s\n", listing("/dev/pts"));
    say("O17 /proc/sys/kernel/pty/nr: %s\n", pty_nr());
    errno = 0;
    int s = open(name, O_RDWR | O_NOCTTY);
    say("O18 open the slave while locked: %s\n", s >= 0 ? "a descriptor" : ename(errno));
    if (s >= 0) close(s);
    errno = 0;
    r = grantpt(m);
    say("O19 grantpt: %s\n", rv(r, errno));
    stat_row("O20 stat of its slave after grantpt", name);
    ANS("O21 unlockpt", unlockpt(m));
    lk = 99;
    errno = 0;
    r = ioctl(m, TIOCGPTLCK, &lk);
    say("O22 TIOCGPTLCK after: %s, locked %d\n", rv(r, errno), lk);
    errno = 0;
    s = open(name, O_RDWR | O_NOCTTY);
    say("O23 open the slave: %s\n", s >= 0 ? "a descriptor" : ename(errno));
    if (s < 0) { close(m); return; }
    fstat_row("O24 fstat of the slave", s);
    say("O25 isatty: master %d, slave %d\n", isatty(m), isatty(s));
    char *tn = ttyname(s);
    say("O26 ttyname of the slave: %s\n", tn ? tn : ename(errno));
    errno = 0;
    tn = ttyname(m);
    say("O27 ttyname of the master: %s\n", tn ? tn : ename(errno));
    {
        char lm[256];
        snprintf(lm, sizeof lm, "%s", link_of(m));
        say("O28 /proc/self/fd links: master %s, slave %s\n", lm, link_of(s));
    }
    n = 99;
    errno = 0;
    r = ioctl(s, TIOCGPTN, &n);
    say("O29 TIOCGPTN on the slave: %s\n", rv(r, errno));
    lk = 0;
    errno = 0;
    r = ioctl(s, TIOCSPTLCK, &lk);
    say("O30 TIOCSPTLCK on the slave: %s\n", rv(r, errno));
    errno = 0;
    int pe = ioctl(m, TIOCGPTPEER, O_RDWR | O_NOCTTY);
    say("O31 TIOCGPTPEER: %s\n", pe >= 0 ? "a descriptor" : ename(errno));
    if (pe >= 0) {
        fstat_row("O32 fstat of the peer", pe);
        tn = ttyname(pe);
        say("O33 ttyname of the peer: %s\n", tn ? tn : ename(errno));
        put(m, "p\n");
        got("O34 the peer reads", pe, 1000);
        close(pe);
    }
    errno = 0;
    pe = ioctl(s, TIOCGPTPEER, O_RDWR | O_NOCTTY);
    say("O35 TIOCGPTPEER on the slave: %s\n", pe >= 0 ? "a descriptor" : ename(errno));
    if (pe >= 0) close(pe);
    {
        int one = 1;
        errno = 0;
        int r2 = ioctl(m, TIOCPKT, &one);
        say("O36 TIOCPKT 1 on the master (packet mode): %s\n", rv(r2, errno));
        one = 0;
        if (r2 == 0) ioctl(m, TIOCPKT, &one);
    }
    (void)settle(m, (unsigned char[4096]){0}, 4096, 200);
    lk = 1;
    ANS("O37 TIOCSPTLCK 1 on the master (locked again)", ioctl(m, TIOCSPTLCK, &lk));
    put(m, "k\n");
    got("O38 the open slave reads", s, 1000);
    errno = 0;
    int s2 = open(name, O_RDWR | O_NOCTTY);
    say("O39 open the slave while locked again: %s\n", s2 >= 0 ? "a descriptor" : ename(errno));
    if (s2 >= 0) close(s2);
    put(m, "j\n");
    got("O40 then the open slave reads", s, 1000);
    lk = 0;
    ANS("O41 TIOCSPTLCK 0", ioctl(m, TIOCSPTLCK, &lk));
    errno = 0;
    s2 = open(name, O_RDWR | O_NOCTTY);
    say("O42 open the slave again: %s\n", s2 >= 0 ? "a descriptor" : ename(errno));
    if (s2 >= 0) {
        put(m, "n\n");
        got("O43 the new descriptor reads", s2, 1000);
        close(s2);
    }
    close(s);
    s = sopen(m, O_NOCTTY);
    put(m, "o\n");
    got("O44 every slave descriptor closed, then one opened: it reads", s, 1000);
    (void)settle(m, (unsigned char[4096]){0}, 4096, 200);
    /* numbers: the lowest free */
    int x[3];
    for (int i = 0; i < 3; i++) x[i] = mopen(0);
    say("O45 three more masters: numbers %d %d %d\n", ptn(x[0]), ptn(x[1]), ptn(x[2]));
    say("O46 /dev/pts lists: %s\n", listing("/dev/pts"));
    say("O47 /proc/sys/kernel/pty/nr: %s\n", pty_nr());
    close(x[1]);
    say("O48 the second closed, /dev/pts lists: %s\n", listing("/dev/pts"));
    x[1] = mopen(0);
    say("O49 a new master's number: %d\n", ptn(x[1]));
    for (int i = 0; i < 3; i++) close(x[i]);
    /* a master closed under an open slave */
    close(m);
    say("O50 the master closed, its slave open: /dev/pts lists %s\n", listing("/dev/pts"));
    stat_row("O51 stat of the slave's name", name);
    errno = 0;
    s2 = open(name, O_RDWR | O_NOCTTY);
    say("O52 open the slave's name: %s\n", s2 >= 0 ? "a descriptor" : ename(errno));
    if (s2 >= 0) close(s2);
    say("O53 /proc/sys/kernel/pty/nr: %s\n", pty_nr());
    close(s);
    say("O54 the slave closed too: /dev/pts lists %s\n", listing("/dev/pts"));
    say("O55 /proc/sys/kernel/pty/nr: %s\n", pty_nr());
    errno = 0;
    s2 = open(name, O_RDWR | O_NOCTTY);
    say("O56 open the name now: %s\n", s2 >= 0 ? "a descriptor" : ename(errno));
    if (s2 >= 0) close(s2);
    /* a user, and root's slave */
    if (root) {
        int m2, s3;
        if (pair(&m2, &s3) == 0) {
            char nm[64];
            ptsname_r(m2, nm, sizeof nm);
            fflush(stdout);
            pid_t c = fork();
            if (c == 0) {
                if (setgid(1000) || setuid(1000)) _exit(9);
                errno = 0;
                int f = open(nm, O_RDWR | O_NOCTTY);
                say("O57 a user opens root's slave: %s\n", f >= 0 ? "a descriptor" : ename(errno));
                errno = 0;
                f = open("/dev/ptmx", O_RDWR | O_NOCTTY);
                say("O58 a user opens /dev/ptmx: %s\n", f >= 0 ? "a descriptor" : ename(errno));
                if (f >= 0) {
                    char un[64];
                    ptsname_r(f, un, sizeof un);
                    stat_row("O59 stat of the user's slave", un);
                }
                _exit(0);
            }
            waitpid(c, 0, 0);
            close(s3);
            close(m2);
        }
    } else {
        say("O57 a user opens root's slave: (root's run)\n");
        say("O58 a user opens /dev/ptmx: (root's run)\n");
        say("O59 stat of the user's slave: (root's run)\n");
    }
    errno = 0;
    int po = posix_openpt(O_RDWR | O_NOCTTY);
    say("O60 posix_openpt: %s, number %d\n", po >= 0 ? "a descriptor" : ename(errno), po >= 0 ? ptn(po) : -1);
    if (po >= 0) close(po);
    errno = 0;
    int ro = open("/dev/ptmx", O_RDONLY | O_NOCTTY);
    say("O61 open /dev/ptmx read-only: %s\n", ro >= 0 ? "a descriptor" : ename(errno));
    if (ro >= 0) {
        errno = 0;
        ssize_t w = write(ro, "x", 1);
        say("O62 a write to it: %s\n", rv(w, errno));
        close(ro);
    }
    say("O63 at the end: /dev/pts lists %s, pty/nr %s\n", listing("/dev/pts"), pty_nr());
}

/* --- T: termios ------------------------------------------------------------ */

static void tline(const char *name, int fd) {
    struct termios t;
    errno = 0;
    if (tcgetattr(fd, &t) != 0) { say("%s: %s\n", name, ename(errno)); return; }
    say("%s: iflag 0x%x oflag 0x%x cflag 0x%x lflag 0x%x line %u cc", name, t.c_iflag, t.c_oflag, t.c_cflag, t.c_lflag, t.c_line);
    for (int i = 0; i < 19; i++) say(" %u", t.c_cc[i]);
    say("\n");
}

static void sec_termios(void) {
    int m, s;
    if (pair(&m, &s)) { say("T: no pair: %s\n", ename(errno)); return; }
    tline("T1 the slave's settings", s);
    tline("T2 the master's settings", m);
    {
        struct termios t;
        tcgetattr(s, &t);
        say("T3 the slave's speeds: in %u out %u\n", (unsigned)cfgetispeed(&t), (unsigned)cfgetospeed(&t));
    }
    /* canonical input */
    put(m, "ab\x7f" "c\n");
    got("T5 canonical: the slave reads", s, 1000);
    got("T6 canonical: the echo", m, 1000);
    put(m, "xyz");
    nap(200);
    say("T7 a part of a line: the slave polls %s\n", revents(s, POLLIN, 100));
    int v = -1;
    errno = 0;
    int r = ioctl(s, FIONREAD, &v);
    say("T8 FIONREAD on the slave: %s, %d\n", rv(r, errno), v);
    v = -1;
    errno = 0;
    r = ioctl(m, FIONREAD, &v);
    say("T9 FIONREAD on the master (the echo): %s, %d\n", rv(r, errno), v);
    put(m, "\n");
    got("T10 the line ended: the slave reads", s, 1000);
    got("T11 the echo", m, 1000);
    put(m, "ab\x04");
    got("T12 VEOF after ab: the slave reads", s, 1000);
    put(m, "\x04");
    got("T13 VEOF on an empty line: the slave reads", s, 1000);
    put(m, "q\n");
    got("T14 then a line: the slave reads", s, 1000);
    got("T15 the echo of all three", m, 1000);
    put(m, "abc\x15x\n");
    got("T16 VKILL: the slave reads", s, 1000);
    got("T17 the echo", m, 1000);
    put(m, "ab cd\x17" "e\n");
    got("T18 VWERASE: the slave reads", s, 1000);
    got("T19 the echo", m, 1000);
    put(m, "\x01\x1b\n");
    got("T20 control bytes: the slave reads", s, 1000);
    got("T21 the echo (ECHOCTL)", m, 1000);
    lset(s, 0, ECHO);
    put(m, "hi\n");
    got("T22 ECHO clear: the slave reads", s, 1000);
    got("T23 the echo", m, 300);
    lset(s, ECHONL, 0);
    put(m, "hi\n");
    got("T24 ECHONL set: the slave reads", s, 1000);
    got("T25 the echo", m, 1000);
    lset(s, ECHO, ECHONL);
    /* the output */
    put(s, "a\nb\n");
    got("T26 OPOST ONLCR: the master reads", m, 1000);
    oset(s, 0, ONLCR);
    put(s, "a\nb\n");
    got("T27 ONLCR clear: the master reads", m, 1000);
    oset(s, ONLCR, OPOST);
    put(s, "a\nb\n");
    got("T28 OPOST clear: the master reads", m, 1000);
    oset(s, OPOST, 0);
    /* the input flags */
    put(m, "a\rb\r");
    got("T29 ICRNL: the slave reads", s, 1000);
    got("T30 the echo", m, 1000);
    iset(s, IGNCR, 0);
    put(m, "a\rb\n");
    got("T31 IGNCR: the slave reads", s, 1000);
    got("T32 the echo", m, 1000);
    iset(s, INLCR, IGNCR | ICRNL);
    put(m, "a\nb\r");
    got("T33 INLCR without ICRNL: the slave reads", s, 300);
    got("T34 the echo", m, 1000);
    iset(s, ICRNL, INLCR);
    tcflush(s, TCIFLUSH);
    (void)settle(m, (unsigned char[4096]){0}, 4096, 200);
    /* the settings, from the master's side */
    lset(m, 0, ECHO);
    {
        struct termios t;
        tcgetattr(s, &t);
        say("T35 ECHO cleared through the master: the slave's lflag 0x%x\n", t.c_lflag);
    }
    lset(m, ECHO, 0);
    /* raw */
    raw(s);
    tline("T36 cfmakeraw", s);
    put(m, "a\rb\x03\x7f");
    got("T37 raw: the slave reads", s, 1000);
    got("T38 raw: the echo", m, 300);
    {
        int fl = fcntl(s, F_GETFL);
        fcntl(s, F_SETFL, fl | O_NONBLOCK);
        errno = 0;
        unsigned char b[16];
        ssize_t k = read(s, b, sizeof b);
        say("T39 raw, nothing there, O_NONBLOCK: %s\n", rv(k, errno));
        fcntl(s, F_SETFL, fl);
    }
    ccset(s, VMIN, 0);
    ccset(s, VTIME, 0);
    {
        long t0 = now_ms();
        unsigned char b[16];
        errno = 0;
        ssize_t k = read(s, b, sizeof b);
        say("T40 VMIN 0 VTIME 0, nothing there: %s at once %s\n", rv(k, errno), yesno(now_ms() - t0 < 100));
    }
    ccset(s, VTIME, 3);
    {
        long t0 = now_ms();
        unsigned char b[16];
        errno = 0;
        ssize_t k = read(s, b, sizeof b);
        long d = now_ms() - t0;
        say("T41 VMIN 0 VTIME 3, nothing comes: %s after 0.3 s %s\n", rv(k, errno), yesno(d >= 250 && d < 1500));
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) { nap(100); put(m, "z"); _exit(0); }
        t0 = now_ms();
        k = read(s, b, sizeof b);
        d = now_ms() - t0;
        say("T42 VMIN 0 VTIME 3, a byte comes at 0.1 s: %s before 0.3 s %s\n", rv(k, errno), yesno(d < 280));
        waitpid(c, 0, 0);
    }
    ccset(s, VTIME, 0);
    ccset(s, VMIN, 3);
    put(m, "ab");
    nap(200);
    say("T43 VMIN 3, two bytes there: the slave polls %s\n", revents(s, POLLIN, 100));
    {
        int fl = fcntl(s, F_GETFL);
        fcntl(s, F_SETFL, fl | O_NONBLOCK);
        unsigned char b[16];
        errno = 0;
        ssize_t k = read(s, b, sizeof b);
        say("T44 VMIN 3, two bytes there, O_NONBLOCK: %s %s\n", rv(k, errno), k > 0 ? esc(b, k) : "");
        fcntl(s, F_SETFL, fl);
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) { nap(100); put(m, "c"); nap(100); put(m, "de"); _exit(0); }
        errno = 0;
        k = read(s, b, sizeof b);
        say("T45 VMIN 3, bytes coming one then two: %s %s\n", rv(k, errno), k > 0 ? esc(b, k) : "");
        waitpid(c, 0, 0);
        got("T46 what is left", s, 300);
    }
    ccset(s, VMIN, 2);
    ccset(s, VTIME, 3);
    {
        long t0 = now_ms();
        put(m, "a");
        unsigned char b[16];
        errno = 0;
        ssize_t k = read(s, b, sizeof b);
        long d = now_ms() - t0;
        say("T47 VMIN 2 VTIME 3, one byte: %s %s after 0.3 s %s\n", rv(k, errno), k > 0 ? esc(b, k) : "", yesno(d >= 250 && d < 1500));
    }
    ccset(s, VMIN, 1);
    ccset(s, VTIME, 0);
    /* flushes */
    put(m, "abc");
    nap(200);
    {
        struct termios t;
        tcgetattr(s, &t);
        tcsetattr(s, TCSAFLUSH, &t);
    }
    say("T48 TCSETSF discards the input: the slave polls %s\n", revents(s, POLLIN, 200));
    put(m, "abc");
    nap(200);
    ANS("T49 tcflush TCIFLUSH on the slave", tcflush(s, TCIFLUSH));
    say("T50 then the slave polls %s\n", revents(s, POLLIN, 200));
    put(s, "out");
    nap(200);
    ANS("T51 tcflush TCOFLUSH on the slave, output unread", tcflush(s, TCOFLUSH));
    got("T52 then the master reads", m, 300);
    put(s, "out");
    nap(200);
    ANS("T53 tcflush TCIFLUSH on the master, the slave's output unread", tcflush(m, TCIFLUSH));
    got("T54 then the master reads", m, 300);
    put(m, "in");
    nap(200);
    ANS("T55 tcflush TCOFLUSH on the master, the slave's input unread", tcflush(m, TCOFLUSH));
    got("T56 then the slave reads", s, 300);
    ANS("T57 tcflush 7", tcflush(s, 7));
    ANS("T58 tcdrain on the slave", tcdrain(s));
    ANS("T59 tcsendbreak on the slave", tcsendbreak(s, 0));
    ANS("T60 tcdrain on the master", tcdrain(m));
    /* counts */
    put(s, "hello");
    nap(200);
    v = -1;
    errno = 0;
    r = ioctl(m, FIONREAD, &v);
    say("T61 FIONREAD on the master, five bytes written: %s, %d\n", rv(r, errno), v);
    v = -1;
    errno = 0;
    r = ioctl(s, TIOCOUTQ, &v);
    say("T62 TIOCOUTQ on the slave then: %s, %d\n", rv(r, errno), v);
    got("T63 the master reads", m, 300);
    put(m, "abc");
    nap(200);
    v = -1;
    errno = 0;
    r = ioctl(s, FIONREAD, &v);
    say("T64 FIONREAD on the slave (raw), three bytes: %s, %d\n", rv(r, errno), v);
    v = -1;
    errno = 0;
    r = ioctl(m, TIOCOUTQ, &v);
    say("T65 TIOCOUTQ on the master then: %s, %d\n", rv(r, errno), v);
    got("T66 the slave reads", s, 300);
    /* IXON */
    close(s);
    close(m);
    if (pair(&m, &s)) return;
    put(m, "\x13");
    nap(200);
    fcntl(s, F_SETFL, fcntl(s, F_GETFL) | O_NONBLOCK);
    errno = 0;
    ssize_t w = write(s, "held\n", 5);
    say("T67 IXON: after ^S a write of five, O_NONBLOCK: %s\n", rv(w, errno));
    fcntl(s, F_SETFL, fcntl(s, F_GETFL) & ~O_NONBLOCK);
    got("T68 the master reads", m, 300);
    put(m, "\x11");
    nap(200);
    errno = 0;
    w = write(s, "go\n", 3);
    say("T69 after ^Q a write of three: %s\n", rv(w, errno));
    got("T69a the master reads", m, 1000);
    put(m, "a\x13" "b\x11" "c\n");
    got("T70 ^S and ^Q inside a line: the slave reads", s, 1000);
    got("T71 the echo", m, 1000);
    close(s);
    close(m);
}

/* --- C: the controlling terminal --------------------------------------------- */

static pid_t fg_after; /* the group the leader hands the terminal back to after a read */

/* The leader reads its terminal in the foreground, then hands it back. */
static void fgot(const char *name, int s, int first) {
    tcsetpgrp(s, getpgrp());
    got(name, s, first);
    tcsetpgrp(s, fg_after);
}

static void sec_ctty(void) {
    /* this process leads a session and has no terminal */
    int m = mopen(0);
    if (m < 0) { say("C: no master\n"); return; }
    unlockpt(m);
    char name[64];
    ptsname_r(m, name, sizeof name);
    int n = ptn(m);
    errno = 0;
    {
        pid_t g0 = tcgetpgrp(m);
        say("C1 a session leader without a terminal: tcgetpgrp(the master) before %s\n", g0 < 0 ? ename(errno) : g0 == 0 ? "0" : "a group");
    }
    errno = 0;
    int s = open(name, O_RDWR);
    say("C2 it opens the slave without O_NOCTTY: %s\n", s >= 0 ? "a descriptor" : ename(errno));
    if (s < 0) return;
    errno = 0;
    pid_t g = tcgetpgrp(s);
    say("C3 the slave is its terminal: tcgetsid %s, tcgetpgrp is its group %s\n", yesno(tcgetsid(s) == getpid()), g < 0 ? ename(errno) : yesno(g == getpgrp()));
    errno = 0;
    g = tcgetpgrp(m);
    say("C4 tcgetpgrp(the master): %s\n", g < 0 ? ename(errno) : g == getpgrp() ? "the slave's foreground group" : "another");
    {
        pid_t sid = 0;
        errno = 0;
        int r = ioctl(m, TIOCGSID, &sid);
        say("C5 TIOCGSID on the master: %s%s\n", rv(r, errno), r == 0 ? (sid == getpid() ? ", the slave's session" : ", another") : "");
    }
    errno = 0;
    int t = open("/dev/tty", O_RDWR);
    say("C6 /dev/tty: %s\n", t >= 0 ? "a descriptor" : ename(errno));
    if (t >= 0) {
        char *tn = ttyname(t);
        say("C7 ttyname of /dev/tty's descriptor: %s; its link %s\n", tn ? (strcmp(tn, name) == 0 ? "the slave's name" : tn) : ename(errno), link_of(t));
        fstat_row("C8 fstat of /dev/tty's descriptor", t);
        put(t, "via-tty\n");
        got("C9 written through /dev/tty, the master reads", m, 1000);
        close(t);
    }
    {
        struct pstat p = pstat_of(getpid());
        say("C10 /proc stat: tty_nr %s, tpgid is its group %s\n",
            p.ok ? ((p.tty == ((136 << 8) | n)) ? "136:N" : "other") : "unread", yesno(p.ok && p.tpgid == getpgrp()));
    }
    ANS("C11 TIOCSCTTY on its own terminal", ioctl(s, TIOCSCTTY, 0));
    {
        int m2 = mopen(0), s2 = -1;
        unlockpt(m2);
        s2 = sopen(m2, O_NOCTTY);
        ANS("C12 TIOCSCTTY on a second pty by a leader that has one", ioctl(s2, TIOCSCTTY, 0));
        errno = 0;
        int s3 = sopen(m2, 0);
        errno = 0;
        say("C13 opening the second's slave without O_NOCTTY: tcgetpgrp %s\n", tcgetpgrp(s3) < 0 ? ename(errno) : "a group");
        close(s3);
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) {
            ANS("C14 TIOCSCTTY by a member that is no leader", ioctl(s2, TIOCSCTTY, 0));
            _exit(0);
        }
        waitpid(c, 0, 0);
        /* another session's leader */
        fflush(stdout);
        c = fork();
        if (c == 0) {
            setsid();
            errno = 0;
            int f = open(name, O_RDWR);
            errno = 0;
            say("C15 another session's leader opens the first slave without O_NOCTTY: tcgetpgrp %s\n", tcgetpgrp(f) < 0 ? ename(errno) : "a group");
            ANS("C16 it asks TIOCSCTTY 0", ioctl(f, TIOCSCTTY, 0));
            _exit(0);
        }
        waitpid(c, 0, 0);
        close(s2);
        close(m2);
    }
    /* the foreground group */
    static const int jsigs[] = {SIGINT, SIGQUIT, SIGTSTP, SIGWINCH, SIGHUP, SIGCONT, SIGTTIN, SIGTTOU, 0};
    pid_t A = idle(0, "A", jsigs);
    pid_t B = idle(A, "B", jsigs);
    pid_t C = idle(0, "C", jsigs);
    signal(SIGTTOU, SIG_IGN);
    ANS("C17 tcsetpgrp to a child's group", tcsetpgrp(s, A));
    errno = 0;
    g = tcgetpgrp(s);
    say("C18 tcgetpgrp: the child's group %s\n", g < 0 ? ename(errno) : yesno(g == A));
    errno = 0;
    g = tcgetpgrp(m);
    say("C19 tcgetpgrp(the master): the child's group %s\n", g < 0 ? ename(errno) : yesno(g == A));
    ANS("C20 tcsetpgrp to a group that does not exist", tcsetpgrp(s, 999999));
    {
        fflush(stdout);
        pid_t o = fork();
        if (o == 0) { setsid(); for (;;) nap(50); }
        nap(50);
        ANS("C21 tcsetpgrp to another session's group", tcsetpgrp(s, o));
        reap(o);
    }
    ANS("C22 tcsetpgrp on the master", tcsetpgrp(m, getpgrp()));
    errno = 0;
    g = tcgetpgrp(s);
    say("C23 then the foreground group is its own %s\n", g < 0 ? ename(errno) : yesno(g == getpgrp()));
    tcsetpgrp(s, A);
    fg_after = A;
    /* the keys */
    flush_heard();
    put(m, "\x03");
    say("C24 ^C written to the master: heard %s\n", heard_list(2, 1500));
    got("C25 the echo", m, 1000);
    put(m, "\x1c");
    say("C26 ^\\: heard %s\n", heard_list(2, 1500));
    got("C27 the echo", m, 1000);
    put(m, "\x1a");
    say("C28 ^Z: heard %s\n", heard_list(2, 1500));
    got("C29 the echo", m, 1000);
    put(m, "ab\x03");
    (void)heard_list(2, 1500);
    put(m, "c\n");
    fgot("C30 ab ^C c: the slave reads", s, 1000);
    got("C31 the echo", m, 1000);
    lset(s, NOFLSH, 0);
    put(m, "ab\x03" "c\n");
    say("C32 NOFLSH: heard %s\n", heard_list(2, 1500));
    fgot("C33 ab ^C c: the slave reads", s, 1000);
    got("C34 the echo", m, 1000);
    lset(s, 0, NOFLSH | ISIG);
    put(m, "\x03\x1a\n");
    say("C35 ISIG clear: heard %s\n", heard_list(0, 400));
    fgot("C36 the slave reads", s, 1000);
    got("C37 the echo", m, 1000);
    lset(s, ISIG, 0);
    {
        static const int stop[] = {SIGINT, 0};
        pid_t D = idle(A, "D", stop);
        put(m, "\x1a");
        int st = 0;
        pid_t w = waitpid(D, &st, WUNTRACED);
        say("C38 ^Z to a foreground member with no handler for it: %s\n", how(w, st));
        say("C39 heard %s\n", heard_list(2, 1500));
        kill(D, SIGCONT);
        reap(D);
        (void)heard_list(0, 300);
        got("C40 the echo", m, 1000);
    }
    /* the background rules (C is a background group) */
    {
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) {
            setpgid(0, C);
            signal(SIGTTIN, SIG_DFL);
            char b[4];
            (void)!read(s, b, 1);
            _exit(0);
        }
        int st = 0;
        pid_t w = waitpid(c, &st, WUNTRACED);
        say("C41 a background read: %s\n", how(w, st));
        kill(c, SIGKILL);
        waitpid(c, 0, 0);
        c = fork();
        if (c == 0) {
            setpgid(0, C);
            signal(SIGTTIN, SIG_IGN);
            char b[4];
            errno = 0;
            ssize_t k = read(s, b, 1);
            say("C42 a background read, SIGTTIN ignored: %s\n", rv(k, errno));
            _exit(0);
        }
        waitpid(c, 0, 0);
        c = fork();
        if (c == 0) {
            setpgid(0, C);
            signal(SIGTTOU, SIG_DFL);
            errno = 0;
            ssize_t k = write(s, "bg\n", 3);
            say("C43 a background write, TOSTOP clear: %s\n", rv(k, errno));
            _exit(0);
        }
        waitpid(c, 0, 0);
        got("C44 the master reads", m, 1000);
        lset(s, TOSTOP, 0);
        c = fork();
        if (c == 0) {
            setpgid(0, C);
            signal(SIGTTOU, SIG_DFL);
            (void)!write(s, "bg\n", 3);
            _exit(0);
        }
        w = waitpid(c, &st, WUNTRACED);
        say("C45 a background write, TOSTOP set: %s\n", how(w, st));
        kill(c, SIGKILL);
        waitpid(c, 0, 0);
        lset(s, 0, TOSTOP);
        c = fork();
        if (c == 0) {
            setpgid(0, C);
            signal(SIGTTOU, SIG_DFL);
            struct termios tt;
            tcgetattr(s, &tt);
            tcsetattr(s, TCSANOW, &tt);
            _exit(0);
        }
        w = waitpid(c, &st, WUNTRACED);
        say("C46 a background tcsetattr: %s\n", how(w, st));
        kill(c, SIGKILL);
        waitpid(c, 0, 0);
        (void)settle(m, (unsigned char[4096]){0}, 4096, 200);
    }
    /* TIOCNOTTY */
    {
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) {
            ANS("C47 TIOCNOTTY by a member that is no leader", ioctl(s, TIOCNOTTY));
            errno = 0;
            say("C48 then its tcgetpgrp %s\n", tcgetpgrp(s) < 0 ? ename(errno) : "a group");
            _exit(0);
        }
        waitpid(c, 0, 0);
        errno = 0;
        say("C49 the leader's tcgetpgrp still %s\n", tcgetpgrp(s) < 0 ? ename(errno) : "a group");
    }
    ANS("C50 TIOCNOTTY on the master", ioctl(m, TIOCNOTTY));
    flush_heard();
    on(SIGHUP);
    on(SIGCONT);
    snprintf(tag, sizeof tag, "L");
    ANS("C51 TIOCNOTTY by the session leader", ioctl(s, TIOCNOTTY));
    say("C52 heard %s\n", heard_list(4, 1500));
    errno = 0;
    say("C53 then tcgetpgrp %s\n", tcgetpgrp(s) < 0 ? ename(errno) : "a group");
    errno = 0;
    t = open("/dev/tty", O_RDWR);
    say("C54 /dev/tty: %s\n", t >= 0 ? "a descriptor" : ename(errno));
    errno = 0;
    {
        pid_t g0 = tcgetpgrp(m);
        say("C55 tcgetpgrp(the master) %s\n", g0 < 0 ? ename(errno) : g0 == 0 ? "0" : "a group");
    }
    ANS("C56 TIOCSCTTY 0 again by the leader", ioctl(s, TIOCSCTTY, 0));
    errno = 0;
    g = tcgetpgrp(s);
    say("C57 its terminal again, the foreground its own group: %s\n", g < 0 ? ename(errno) : yesno(g == getpgrp()));
    /* steal */
    {
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) {
            setsid();
            snprintf(tag, sizeof tag, "T");
            int f = open(name, O_RDWR | O_NOCTTY);
            ANS("C58 another session's leader asks TIOCSCTTY 1", ioctl(f, TIOCSCTTY, 1));
            errno = 0;
            pid_t gg = tcgetpgrp(f);
            say("C59 then its tcgetpgrp: its own group %s\n", gg < 0 ? ename(errno) : yesno(gg == getpgrp()));
            if (gg >= 0) {
                say("C60 heard %s\n", heard_list(2, 1000));
                on(SIGHUP);
                on(SIGCONT);
                ANS("C61 the thief's TIOCNOTTY", ioctl(f, TIOCNOTTY));
                say("C62 heard %s\n", heard_list(2, 1000));
            } else {
                say("C60 heard %s\n", heard_list(0, 400));
                say("C61 the thief's TIOCNOTTY: (no steal)\n");
                say("C62 heard -\n");
            }
            _exit(0);
        }
        waitpid(c, 0, 0);
        say("C63 the first leader heard %s\n", heard_list(0, 400));
        errno = 0;
        say("C64 the first leader's tcgetpgrp %s\n", tcgetpgrp(s) < 0 ? ename(errno) : "a group");
    }
    reap(A); reap(B); reap(C);
    close(s);
    close(m);
}

/* --- W: the window size ---------------------------------------------------- */

static const char *wsz(int fd) {
    static char b[64];
    struct winsize w = {9, 9, 9, 9};
    errno = 0;
    if (ioctl(fd, TIOCGWINSZ, &w) != 0) return ename(errno);
    snprintf(b, sizeof b, "%u %u %u %u", w.ws_row, w.ws_col, w.ws_xpixel, w.ws_ypixel);
    return b;
}

static void sec_winsz(void) {
    int m, s;
    if (pair(&m, &s)) { say("W: no pair: %s\n", ename(errno)); return; }
    {
        char a1[64];
        snprintf(a1, sizeof a1, "%s", wsz(s));
        say("W1 a new pty: the slave %s, the master %s\n", a1, wsz(m));
    }
    ioctl(s, TIOCSCTTY, 0);
    static const int ws[] = {SIGWINCH, 0};
    pid_t A = idle(0, "A", ws);
    pid_t B = idle(A, "B", ws);
    pid_t C = idle(0, "C", ws);
    snprintf(tag, sizeof tag, "L");
    on(SIGWINCH);
    signal(SIGTTOU, SIG_IGN);
    tcsetpgrp(s, A);
    flush_heard();
    struct winsize w = {24, 80, 0, 0};
    ANS("W2 TIOCSWINSZ 24x80 on the master", ioctl(m, TIOCSWINSZ, &w));
    say("W3 heard %s\n", heard_list(2, 1500));
    {
        char a1[64];
        snprintf(a1, sizeof a1, "%s", wsz(s));
        say("W4 the slave %s, the master %s\n", a1, wsz(m));
    }
    ANS("W5 the same size again", ioctl(m, TIOCSWINSZ, &w));
    say("W6 heard %s\n", heard_list(0, 400));
    w.ws_row = 30; w.ws_col = 100;
    ANS("W7 TIOCSWINSZ 30x100 on the slave", ioctl(s, TIOCSWINSZ, &w));
    say("W8 heard %s\n", heard_list(2, 1500));
    say("W9 the master %s\n", wsz(m));
    w.ws_xpixel = 640; w.ws_ypixel = 480;
    ANS("W10 the pixel fields only", ioctl(m, TIOCSWINSZ, &w));
    say("W11 heard %s\n", heard_list(2, 1500));
    say("W12 the slave %s\n", wsz(s));
    {
        errno = 0;
        int r = ioctl(m, TIOCSWINSZ, (void *)8);
        say("W13 TIOCSWINSZ with a bad pointer: %s\n", rv(r, errno));
        errno = 0;
        r = ioctl(m, TIOCGWINSZ, (void *)8);
        say("W14 TIOCGWINSZ with a bad pointer: %s\n", rv(r, errno));
    }
    tcsetpgrp(s, getpgrp());
    w.ws_row = 40; w.ws_col = 120;
    ANS("W15 the leader in the foreground, 40x120", ioctl(m, TIOCSWINSZ, &w));
    say("W16 heard %s\n", heard_list(1, 1500));
    reap(A); reap(B); reap(C);
    {
        int m2, s2;
        if (pair(&m2, &s2) == 0) {
            flush_heard();
            ANS("W17 a pty nobody's terminal, TIOCSWINSZ", ioctl(m2, TIOCSWINSZ, &w));
            say("W18 heard %s; the slave %s\n", heard_list(0, 400), wsz(s2));
            close(s2);
            close(m2);
        }
    }
    signal(SIGHUP, SIG_IGN); /* its own terminal's master closes next: H's rows */
    close(s);
    close(m);
}

/* --- H: hangup ---------------------------------------------------------------- */

/* A session on a fresh pty: its leader L (the slave its terminal, the
 * foreground group F of one member, a background group G of one), with
 * every signal of interest reported. Returns the master; *ls the
 * leader's pid; *sl a slave descriptor the caller holds (O_NOCTTY). */
static int hsession(pid_t *ls, int *sl, int *ctl) {
    int m = mopen(0);
    if (m < 0) return -1;
    unlockpt(m);
    char name[64];
    ptsname_r(m, name, sizeof name);
    *sl = open(name, O_RDWR | O_NOCTTY);
    int c2p[2], p2c[2];
    (void)!pipe(c2p);
    (void)!pipe(p2c);
    fflush(stdout);
    pid_t L = fork();
    if (L == 0) {
        close(c2p[0]);
        close(p2c[1]);
        close(m);
        setsid();
        snprintf(tag, sizeof tag, "L");
        static const int hs[] = {SIGHUP, SIGCONT, SIGTERM, 0};
        for (const int *q = hs; *q; q++) on(*q);
        int s = open(name, O_RDWR);
        static const int fs[] = {SIGHUP, SIGCONT, SIGTERM, 0};
        pid_t F = idle(0, "F", fs);
        pid_t G = idle(0, "G", fs);
        signal(SIGTTOU, SIG_IGN);
        tcsetpgrp(s, F);
        (void)!write(c2p[1], "r", 1);
        /* commands from the parent: one byte each */
        char cmd;
        while (read(p2c[0], &cmd, 1) == 1) {
            char out[512];
            int k = 0;
            if (cmd == 'r') {
                unsigned char b[64];
                errno = 0;
                ssize_t r = read(s, b, sizeof b);
                k = snprintf(out, sizeof out, "%s", r > 0 ? esc(b, r) : rv(r, errno));
            } else if (cmd == 'w') {
                errno = 0;
                ssize_t r = write(s, "x", 1);
                k = snprintf(out, sizeof out, "%s", rv(r, errno));
            } else if (cmd == 'p') {
                k = snprintf(out, sizeof out, "%s", revents(s, POLLIN | POLLOUT, 200));
            } else if (cmd == 'g') {
                errno = 0;
                pid_t g = tcgetpgrp(s);
                k = snprintf(out, sizeof out, "%s", g < 0 ? ename(errno) : (g == F ? "F" : "another"));
            } else if (cmd == 't') {
                errno = 0;
                int t = open("/dev/tty", O_RDWR);
                k = snprintf(out, sizeof out, "%s", t >= 0 ? "a descriptor" : ename(errno));
                if (t >= 0) close(t);
            } else if (cmd == 'h') {
                k = snprintf(out, sizeof out, "%s", heard_list(0, 300));
            } else if (cmd == 'x') {
                reap(F);
                reap(G);
                _exit(0);
            } else if (cmd == 'f') {
                /* F and G: alive? */
                k = snprintf(out, sizeof out, "F %s, G %s", kill(F, 0) == 0 ? "alive" : "gone", kill(G, 0) == 0 ? "alive" : "gone");
            }
            out[k++] = '\n';
            (void)!write(c2p[1], out, (size_t)k);
        }
        reap(F);
        reap(G);
        _exit(0);
    }
    close(c2p[1]);
    close(p2c[0]);
    char r;
    (void)!read(c2p[0], &r, 1);
    *ls = L;
    ctl[0] = c2p[0];
    ctl[1] = p2c[1];
    return m;
}

static const char *ask(int *ctl, char c) {
    static char b[512];
    (void)!write(ctl[1], &c, 1);
    int k = 0;
    while (k < (int)sizeof b - 1) {
        ssize_t r = read(ctl[0], b + k, 1);
        if (r <= 0 || b[k] == '\n') break;
        k++;
    }
    b[k] = 0;
    return b;
}

static void sec_hangup(void) {
    pid_t L;
    int sl, ctl[2];
    int m = hsession(&L, &sl, ctl);
    if (m < 0) { say("H: no master: %s\n", ename(errno)); return; }
    say("H1 the session's foreground before: %s\n", ask(ctl, 'g'));
    put(m, "unread\n");
    nap(200);
    close(m);
    nap(300);
    say("H2 the master closed: the session heard %s\n", ask(ctl, 'h'));
    say("H3 F and G after: %s\n", ask(ctl, 'f'));
    say("H4 the leader reads its terminal: %s\n", ask(ctl, 'r'));
    say("H5 and again: %s\n", ask(ctl, 'r'));
    say("H6 the leader writes it: %s\n", ask(ctl, 'w'));
    say("H7 the leader polls it: %s\n", ask(ctl, 'p'));
    say("H8 the leader's tcgetpgrp: %s\n", ask(ctl, 'g'));
    say("H9 the leader opens /dev/tty: %s\n", ask(ctl, 't'));
    {
        unsigned char b[16];
        errno = 0;
        ssize_t k = read(sl, b, sizeof b);
        say("H10 a slave descriptor that is no one's terminal reads: %s\n", rv(k, errno));
        say("H11 it polls %s\n", revents(sl, POLLIN | POLLOUT, 200));
        errno = 0;
        k = write(sl, "x", 1);
        say("H12 it writes: %s\n", rv(k, errno));
        int v = -1;
        errno = 0;
        int r = ioctl(sl, FIONREAD, &v);
        say("H13 FIONREAD: %s\n", rv(r, errno));
        struct termios t;
        errno = 0;
        say("H14 tcgetattr: %s\n", tcgetattr(sl, &t) == 0 ? "0" : ename(errno));
    }
    close(sl);
    (void)ask(ctl, 'x');
    waitpid(L, 0, 0);
    close(ctl[0]);
    close(ctl[1]);
    /* the slave side closed under the master */
    int s;
    if (pair(&m, &s)) return;
    put(s, "left");
    nap(200);
    close(s);
    nap(100);
    say("H15 every slave descriptor closed, bytes unread: the master polls %s\n", revents(m, POLLIN | POLLOUT, 200));
    got("H16 the master reads", m, 300);
    got("H17 and again", m, 300);
    say("H18 then it polls %s\n", revents(m, POLLIN | POLLOUT, 200));
    {
        errno = 0;
        ssize_t k = write(m, "x\n", 2);
        say("H19 the master writes: %s\n", rv(k, errno));
    }
    s = sopen(m, O_NOCTTY);
    say("H20 the slave opened again: %s\n", s >= 0 ? "a descriptor" : ename(errno));
    nap(300);
    say("H21 the master polls %s\n", revents(m, POLLIN | POLLOUT, 200));
    got("H22 the slave reads what the master wrote", s, 300);
    got("H22a the master reads", m, 300);
    close(s);
    close(m);
    /* a master never given a slave */
    m = mopen(0);
    unlockpt(m);
    say("H23 a master whose slave was never opened polls %s\n", revents(m, POLLIN | POLLOUT, 200));
    {
        int fl = fcntl(m, F_GETFL);
        fcntl(m, F_SETFL, fl | O_NONBLOCK);
        unsigned char b[8];
        errno = 0;
        ssize_t k = read(m, b, sizeof b);
        say("H24 it reads (O_NONBLOCK): %s\n", rv(k, errno));
        errno = 0;
        k = write(m, "x", 1);
        say("H25 it writes: %s\n", rv(k, errno));
    }
    close(m);
    /* the session leader ends */
    {
        int c2p[2];
        (void)!pipe(c2p);
        m = mopen(0);
        unlockpt(m);
        char name[64];
        ptsname_r(m, name, sizeof name);
        fflush(stdout);
        pid_t L2 = fork();
        if (L2 == 0) {
            setsid();
            int s2 = open(name, O_RDWR);
            static const int fs[] = {SIGHUP, SIGCONT, 0};
            snprintf(tag, sizeof tag, "F");
            /* F reports through the parent's pipe */
            pid_t F = fork();
            if (F == 0) {
                setpgid(0, 0);
                signal(SIGHUP, SIG_DFL);
                for (const int *q = fs; *q; q++) on(*q);
                rep[1] = c2p[1];
                for (int i = 0; i < 100; i++) nap(20);
                _exit(0);
            }
            setpgid(F, F);
            signal(SIGTTOU, SIG_IGN);
            tcsetpgrp(s2, F);
            nap(200);
            _exit(0);
        }
        close(c2p[1]);
        waitpid(L2, 0, 0);
        nap(500);
        char b[256];
        int k = 0;
        long end = now_ms() + 1000;
        int fl = fcntl(c2p[0], F_GETFL);
        fcntl(c2p[0], F_SETFL, fl | O_NONBLOCK);
        while (now_ms() < end) {
            ssize_t r = read(c2p[0], b + k, sizeof b - 1 - (size_t)k);
            if (r > 0) k += (int)r;
            else if (r == 0) break;
            else nap(20);
        }
        b[k] = 0;
        while (k > 0 && b[k - 1] == '\n') b[--k] = 0;
        for (int i = 0; i < k; i++) if (b[i] == '\n') b[i] = ',';
        say("H26 the session leader ends: its foreground group heard %s\n", k ? b : "-");
        errno = 0;
        say("H27 the master then: tcgetpgrp %s\n", tcgetpgrp(m) < 0 ? ename(errno) : "a group");
        close(c2p[0]);
        close(m);
        /* F may be left: it was killed by HUP, or is an orphan; nothing to reap here */
    }
}

/* --- P: poll, O_NONBLOCK, full buffers -------------------------------------- */

/* Write `chunk` bytes at a time to a non-blocking `fd` until it takes no
 * more (with a pause for the other side's hand-over each time it takes
 * less): the total and the errno that ended it. */
static long fill(int fd, int chunk, int *err) {
    static unsigned char big[65536];
    memset(big, 'f', sizeof big);
    long total = 0;
    int stuck = 0;
    *err = 0;
    while (stuck < 2) {
        errno = 0;
        ssize_t k = write(fd, big, (size_t)chunk);
        if (k < 0) {
            *err = errno;
            if (errno != EAGAIN) break;
            stuck++;
            nap(200);
            continue;
        }
        total += k;
        stuck = 0;
    }
    return total;
}

/* Read everything `fd` gives (settling): the count. */
static long drain_all(int fd) {
    unsigned char b[4096];
    long n = 0;
    for (;;) {
        long k = settle(fd, b, sizeof b, 300);
        if (k <= 0) break;
        n += k;
    }
    return n;
}

/* The full buffers by other write sizes, each on a fresh raw pair. */
static void fills(void) {
    static const int sizes[] = {1, 1000, 65536, 0};
    for (const int *z = sizes; *z; z++) {
        int m, s, e;
        if (pair(&m, &s)) return;
        raw(s);
        fcntl(m, F_SETFL, fcntl(m, F_GETFL) | O_NONBLOCK);
        fcntl(s, F_SETFL, fcntl(s, F_GETFL) | O_NONBLOCK);
        long t = fill(s, *z, &e);
        say("P10a the slave writes %d at a time: %ld taken, then %s; the master reads %ld\n", *z, t, ename(e), drain_all(m));
        t = fill(m, *z, &e);
        say("P10b the master writes %d at a time: %ld taken, then %s; the slave reads %ld\n", *z, t, ename(e), drain_all(s));
        close(s);
        close(m);
    }
    {
        /* canonical: whole lines nobody reads */
        int m, s, e;
        if (pair(&m, &s)) return;
        lset(s, 0, ECHO);
        fcntl(m, F_SETFL, fcntl(m, F_GETFL) | O_NONBLOCK);
        fcntl(s, F_SETFL, fcntl(s, F_GETFL) | O_NONBLOCK);
        static char line[100];
        memset(line, 'l', sizeof line);
        line[99] = '\n';
        long total = 0;
        int stuck = 0;
        e = 0;
        while (stuck < 2 && total < 1000000) {
            errno = 0;
            ssize_t k = write(m, line, sizeof line);
            if (k < 0) { e = errno; if (errno != EAGAIN) break; stuck++; nap(200); continue; }
            total += k;
            stuck = 0;
        }
        say("P10c canonical, 100-byte lines to the master, nobody reads: %ld taken, then %s; the slave reads %ld\n", total, ename(e), drain_all(s));
        close(s);
        close(m);
    }
}

static void sec_poll(void) {
    int m, s;
    if (pair(&m, &s)) { say("P: no pair: %s\n", ename(errno)); return; }
    {
        char a1[64];
        snprintf(a1, sizeof a1, "%s", revents(m, POLLIN | POLLOUT, 0));
        say("P1 a new pair: the master polls %s, the slave %s\n", a1, revents(s, POLLIN | POLLOUT, 0));
    }
    put(m, "x");
    nap(200);
    {
        char a1[64];
        snprintf(a1, sizeof a1, "%s", revents(s, POLLIN | POLLOUT, 0));
        say("P2 x written to the master: the slave polls %s, the master %s\n", a1, revents(m, POLLIN | POLLOUT, 0));
    }
    put(m, "\n");
    nap(200);
    say("P3 then a newline: the slave polls %s\n", revents(s, POLLIN | POLLOUT, 0));
    (void)settle(s, (unsigned char[64]){0}, 64, 300);
    (void)settle(m, (unsigned char[64]){0}, 64, 300);
    fcntl(m, F_SETFL, fcntl(m, F_GETFL) | O_NONBLOCK);
    fcntl(s, F_SETFL, fcntl(s, F_GETFL) | O_NONBLOCK);
    {
        unsigned char b[8];
        errno = 0;
        ssize_t k = read(m, b, sizeof b);
        char a1[32];
        snprintf(a1, sizeof a1, "%s", rv(k, errno));
        errno = 0;
        k = read(s, b, sizeof b);
        say("P4 O_NONBLOCK, nothing there: the master reads %s, the slave %s\n", a1, rv(k, errno));
    }
    raw(s);
    /* the slave's output fills */
    {
        static unsigned char big[65536];
        memset(big, 'o', sizeof big);
        long total = 0;
        int calls = 0;
        for (;;) {
            errno = 0;
            ssize_t k = write(s, big, 4096);
            if (k < 0) break;
            total += k;
            if (++calls > 10000) break;
            if (k < 4096) { nap(50); }
        }
        int e = errno;
        nap(300);
        for (;;) { errno = 0; ssize_t k = write(s, big, 4096); if (k < 0) break; total += k; }
        say("P5 the slave writes 4096 at a time, nobody reads: %ld taken, then %s\n", total, ename(e));
        say("P6 the slave then polls %s\n", revents(s, POLLOUT, 0));
        say("P7 the master polls %s\n", revents(m, POLLIN | POLLOUT, 0));
        unsigned char b[4096];
        ssize_t k = read(m, b, 1);
        nap(200);
        say("P8 the master reads %zd: the slave polls %s\n", k, revents(s, POLLOUT, 0));
        k = read(m, b, 4096);
        nap(200);
        say("P9 the master reads %zd more: the slave polls %s\n", k, revents(s, POLLOUT, 0));
        long got_ = 1 + (k > 0 ? k : 0);
        for (;;) {
            long n = settle(m, b, sizeof b, 300);
            if (n <= 0) break;
            got_ += n;
        }
        say("P10 the master reads it all: %ld, the slave polls %s\n", got_, revents(s, POLLOUT, 0));
    }
    /* the master's writes fill the slave's input (raw, nobody reads) */
    {
        static unsigned char big[65536];
        memset(big, 'i', sizeof big);
        long total = 0;
        int e = 0;
        for (int i = 0; i < 10000; i++) {
            errno = 0;
            ssize_t k = write(m, big, 4096);
            if (k < 0) { e = errno; break; }
            total += k;
            if (k < 4096) nap(50);
        }
        nap(300);
        for (;;) { errno = 0; ssize_t k = write(m, big, 4096); if (k < 0) { e = errno; break; } total += k; }
        say("P11 the master writes 4096 at a time, nobody reads: %ld taken, then %s\n", total, ename(e));
        say("P12 the master then polls %s\n", revents(m, POLLOUT, 0));
        unsigned char b[4096];
        long n = 0;
        for (;;) {
            long k = settle(s, b, sizeof b, 300);
            if (k <= 0) break;
            n += k;
        }
        say("P13 the slave reads it all: %ld, the master polls %s\n", n, revents(m, POLLOUT, 200));
    }
    fills();
    /* canonical: a line longer than the line discipline holds */
    {
        struct termios t;
        tcgetattr(s, &t);
        t.c_lflag |= ICANON | ECHO;
        t.c_oflag |= OPOST;
        t.c_iflag |= ICRNL;
        tcsetattr(s, TCSANOW, &t);
        lset(s, 0, ECHO);
        static unsigned char big[8192];
        memset(big, 'a', sizeof big);
        errno = 0;
        ssize_t k = write(m, big, 5000);
        say("P14 canonical, 5000 bytes with no newline written to the master: %s\n", rv(k, errno));
        nap(300);
        say("P15 the slave polls %s\n", revents(s, POLLIN, 0));
        errno = 0;
        k = write(m, "\n", 1);
        say("P16 a newline: %s\n", rv(k, errno));
        nap(300);
        unsigned char b[8192];
        errno = 0;
        k = read(s, b, sizeof b);
        say("P17 the slave reads: %s, ends with a newline %s\n", rv(k, errno), k > 0 ? yesno(b[k - 1] == '\n') : "-");
        errno = 0;
        k = read(s, b, sizeof b);
        say("P18 and again: %s\n", rv(k, errno));
        lset(s, ECHO, 0);
    }
    close(s);
    close(m);
    /* blocking: a writer waits for the reader */
    if (pair(&m, &s)) return;
    raw(s);
    {
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) {
            static unsigned char big[100000];
            for (int i = 0; i < (int)sizeof big; i++) big[i] = (unsigned char)('a' + i % 26);
            long n = 0;
            while (n < (long)sizeof big) {
                ssize_t k = write(s, big + n, sizeof big - (size_t)n);
                if (k <= 0) _exit(1);
                n += k;
            }
            _exit(0);
        }
        nap(300);
        unsigned char b[4096];
        long n = 0;
        int ok = 1;
        while (n < 100000) {
            long k = settle(m, b, sizeof b, 2000);
            if (k <= 0) break;
            for (long i = 0; i < k; i++) if (b[i] != (unsigned char)('a' + (n + i) % 26)) ok = 0;
            n += k;
        }
        int st;
        waitpid(c, &st, 0);
        say("P19 the slave writes 100000 bytes blocking, the master reads: %ld, intact %s, the writer %s\n", n, yesno(ok), how(c, st));
    }
    {
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) {
            static unsigned char big[100000];
            for (int i = 0; i < (int)sizeof big; i++) big[i] = (unsigned char)('A' + i % 26);
            long n = 0;
            while (n < (long)sizeof big) {
                ssize_t k = write(m, big + n, sizeof big - (size_t)n);
                if (k <= 0) _exit(1);
                n += k;
            }
            _exit(0);
        }
        nap(300);
        unsigned char b[4096];
        long n = 0;
        int ok = 1;
        while (n < 100000) {
            long k = settle(s, b, sizeof b, 2000);
            if (k <= 0) break;
            for (long i = 0; i < k; i++) if (b[i] != (unsigned char)('A' + (n + i) % 26)) ok = 0;
            n += k;
        }
        int st;
        waitpid(c, &st, 0);
        say("P20 the master writes 100000 bytes blocking, the slave reads: %ld, intact %s, the writer %s\n", n, yesno(ok), how(c, st));
    }
    /* waiters woken */
    {
        int p[2];
        (void)!pipe(p);
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) {
            unsigned char b[16];
            ssize_t k = read(s, b, sizeof b);
            dprintf(p[1], "%s\n", k > 0 ? esc(b, k) : rv(k, errno));
            _exit(0);
        }
        nap(300);
        put(m, "hi");
        char b[64] = "";
        ssize_t k = read(p[0], b, sizeof b - 1);
        if (k > 0) b[k - 1] = 0;
        say("P21 a reader waiting on the slave, the master writes: it read %s\n", b);
        waitpid(c, 0, 0);
        c = fork();
        if (c == 0) {
            unsigned char bb[16];
            ssize_t kk = read(m, bb, sizeof bb);
            dprintf(p[1], "%s\n", kk > 0 ? esc(bb, kk) : rv(kk, errno));
            _exit(0);
        }
        nap(300);
        put(s, "yo");
        k = read(p[0], b, sizeof b - 1);
        if (k > 0) b[k - 1] = 0;
        say("P22 a reader waiting on the master, the slave writes: it read %s\n", b);
        waitpid(c, 0, 0);
        c = fork();
        if (c == 0) {
            struct pollfd q = {s, POLLIN, 0};
            int r = poll(&q, 1, 5000);
            dprintf(p[1], "%d %s\n", r, (q.revents & POLLIN) ? "IN" : "-");
            _exit(0);
        }
        nap(300);
        put(m, "w");
        k = read(p[0], b, sizeof b - 1);
        if (k > 0) b[k - 1] = 0;
        say("P23 a poll waiting on the slave, the master writes: %s\n", b);
        waitpid(c, 0, 0);
        (void)settle(s, (unsigned char[64]){0}, 64, 200);
        close(p[0]);
        close(p[1]);
    }
    close(s);
    close(m);
}

/* --- M: many ---------------------------------------------------------------- */

static void sec_many(void) {
    enum { N = 64 };
    int m[N], s[N], ok = 1, order = 1;
    for (int i = 0; i < N; i++) {
        if (pair(&m[i], &s[i])) { ok = 0; m[i] = s[i] = -1; continue; }
        if (ptn(m[i]) != i) order = 0;
        raw(s[i]);
    }
    say("M1 %d pairs at once: all opened %s, numbered 0 to %d in order %s\n", N, yesno(ok), N - 1, yesno(order));
    say("M2 /dev/pts holds %d names, pty/nr %s\n", pts_count(), pty_nr());
    int right = 1;
    for (int i = 0; i < N; i++) {
        if (m[i] < 0) continue;
        char b[16];
        int k = snprintf(b, sizeof b, "%d.", i);
        (void)!write(m[i], b, (size_t)k);
    }
    nap(300);
    for (int i = 0; i < N; i++) {
        if (s[i] < 0) continue;
        unsigned char b[16];
        char want[16];
        int k = snprintf(want, sizeof want, "%d.", i);
        long n = settle(s[i], b, sizeof b, 500);
        if (n != k || memcmp(b, want, (size_t)k) != 0) right = 0;
    }
    say("M3 each slave reads what its own master wrote: %s\n", yesno(right));
    for (int i = 0; i < N; i++) { if (s[i] >= 0) close(s[i]); if (m[i] >= 0) close(m[i]); }
    say("M4 all closed: /dev/pts holds %d names, pty/nr %s\n", pts_count(), pty_nr());
    int same = 1, okr = 1;
    for (int r = 0; r < 1000; r++) {
        int a, b;
        if (pair(&a, &b)) { okr = 0; break; }
        if (ptn(a) != 0) same = 0;
        raw(b);
        (void)!write(a, "r", 1);
        unsigned char c;
        if (read(b, &c, 1) != 1 || c != 'r') okr = 0;
        close(b);
        close(a);
    }
    say("M5 1000 rounds of a pair opened, used, closed: all right %s, number 0 each time %s\n", yesno(okr), yesno(same));
    say("M6 after: /dev/pts holds %d names, pty/nr %s\n", pts_count(), pty_nr());
    {
        int a, b;
        if (pair(&a, &b) == 0) {
            fflush(stdout);
            pid_t c = fork();
            if (c == 0) _exit(0); /* a child's copies close when it ends */
            waitpid(c, 0, 0);
            close(b);
            close(a);
        }
    }
    say("M7 a pair shared with a child that ended, then closed: /dev/pts holds %d names, pty/nr %s\n", pts_count(), pty_nr());
}

/* --- S: the session row: pelt on a pty, driven from the master ---------------- */

static unsigned char tr_buf[262144];
static long tr_len;

/* Read the master into the transcript until `want` appears in it after
 * `from` (or `ms` pass). 1 when it came. */
static int until_seen(int m, const char *want, long from, int ms) {
    long end = now_ms() + ms;
    for (;;) {
        if (want && tr_len > from) {
            tr_buf[tr_len] = 0;
            if (memmem(tr_buf + from, (size_t)(tr_len - from), want, strlen(want))) return 1;
        }
        long t = end - now_ms();
        if (t <= 0) return 0;
        struct pollfd p = {m, POLLIN, 0};
        if (poll(&p, 1, (int)(t < 50 ? t : 50)) > 0 && (p.revents & POLLIN)) {
            ssize_t k = read(m, tr_buf + tr_len, sizeof tr_buf - 1 - (size_t)tr_len);
            if (k > 0) tr_len += k;
            else if (k < 0 && errno != EAGAIN && errno != EINTR) return 0;
        } else if (p.revents & (POLLHUP | POLLERR)) {
            return 0;
        }
    }
}

static void type(int m, const char *s) {
    for (const char *p = s; *p; p++) {
        (void)!write(m, p, 1);
        nap(20);
    }
}

/* Whether the foreground group of the master's slave is some group
 * other than `g`, within `ms`. */
static int fg_moved(int m, pid_t g, int ms) {
    long end = now_ms() + ms;
    while (now_ms() < end) {
        pid_t f = tcgetpgrp(m);
        if (f > 0 && f != g) return 1;
        nap(20);
    }
    return 0;
}

static int drive(void) {
    int m = mopen(0);
    if (m < 0) { say("S: no master: %s\n", ename(errno)); return 1; }
    unlockpt(m);
    char name[64];
    ptsname_r(m, name, sizeof name);
    fflush(stdout);
    pid_t sh = fork();
    if (sh == 0) {
        setsid();
        int s = open(name, O_RDWR);
        dup2(s, 0); dup2(s, 1); dup2(s, 2);
        if (s > 2) close(s);
        close(m);
        static const int reset[] = {SIGHUP, SIGINT, SIGQUIT, SIGCONT, SIGTSTP, SIGTTIN, SIGTTOU, SIGWINCH, SIGPIPE, 0};
        for (const int *q = reset; *q; q++) signal(*q, SIG_DFL);
        sigset_t none;
        sigemptyset(&none);
        sigprocmask(SIG_SETMASK, &none, 0);
        char *envp[] = {"HOME=/", "TERM=linux", "PAX=1", "PATH=/bin", 0};
        char *argv[] = {"/bin/sh", "-i", 0};
        execve("/bin/sh", argv, envp);
        _exit(127);
    }
    say("S0 pelt on a pty, its session's leader; the driver types at the master\n");
    long mark = 0;
    int ok = until_seen(m, "$ ", mark, 30000); /* pelt's prompt, root's too */
    say("S1 the first prompt came: %s\n", yesno(ok));
    /* 1: the size as stty reads it */
    mark = tr_len;
    type(m, "stty size; echo :do''ne1:\r");
    say("S2 stty size, then the marker: %s\n", yesno(until_seen(m, ":done1:", mark, 20000)));
    /* 2: a resize stty reads */
    struct winsize w = {30, 100, 0, 0};
    ioctl(m, TIOCSWINSZ, &w);
    nap(500);
    mark = tr_len;
    type(m, "stty size; echo :do''ne2:\r");
    say("S3 resized to 30x100, stty size: %s\n", yesno(until_seen(m, ":done2:", mark, 20000)));
    /* 3: a trap on WINCH sets COLUMNS */
    mark = tr_len;
    type(m, "trap 'COLUMNS=$(stty size | cut -d\" \" -f2)' WINCH; echo :do''ne3:\r");
    say("S4 a WINCH trap set: %s\n", yesno(until_seen(m, ":done3:", mark, 20000)));
    w.ws_row = 40; w.ws_col = 120;
    ioctl(m, TIOCSWINSZ, &w);
    nap(1000);
    mark = tr_len;
    type(m, "echo cols=$COLUMNS :do''ne4:\r");
    say("S5 resized to 40x120, $COLUMNS: %s\n", yesno(until_seen(m, ":done4:", mark, 20000)));
    /* 4: ^C reaches a foreground job */
    pid_t shg = sh; /* pelt leads its own group */
    mark = tr_len;
    type(m, "sleep 100\r");
    int moved = fg_moved(m, shg, 10000);
    say("S6 sleep 100 is the foreground job: %s\n", yesno(moved));
    nap(300);
    (void)!write(m, "\x03", 1);
    int back = 0;
    {
        long end = now_ms() + 10000;
        while (now_ms() < end) { pid_t f = tcgetpgrp(m); if (f == shg) { back = 1; break; } nap(20); }
    }
    say("S7 ^C written to the master: the shell has the terminal again %s\n", yesno(back));
    nap(500);
    mark = tr_len;
    type(m, "echo st=$? :do''ne5:\r");
    say("S8 the job's status: %s\n", yesno(until_seen(m, ":done5:", mark, 20000)));
    /* 5: the hangup */
    mark = tr_len;
    type(m, "echo :do''ne6:\r");
    (void)until_seen(m, ":done6:", mark, 20000);
    nap(300);
    (void)until_seen(m, 0, 0, 300);
    close(m);
    int st = 0;
    pid_t wr = 0;
    long end = now_ms() + 10000;
    while (now_ms() < end) { wr = waitpid(sh, &st, WNOHANG); if (wr == sh) break; nap(20); }
    say("S9 the master closed: the shell %s\n", wr == sh ? how(wr, st) : "still running");
    if (wr != sh) { kill(sh, SIGKILL); waitpid(sh, 0, 0); }
    /* the transcript, its escape sequences and carriage returns out */
    {
        static char clean[262144];
        long k = 0;
        for (long i = 0; i < tr_len; i++) {
            unsigned char c = tr_buf[i];
            if (c == 0x1b) {
                if (i + 1 < tr_len && tr_buf[i + 1] == '[') {
                    i += 2;
                    while (i < tr_len && !(tr_buf[i] >= 0x40 && tr_buf[i] <= 0x7e)) i++;
                } else if (i + 1 < tr_len) i++;
                continue;
            }
            if (c == '\r' || c == 7) continue;
            clean[k++] = (char)c;
        }
        clean[k] = 0;
        char *line = clean;
        for (;;) {
            char *nl = strchr(line, '\n');
            if (nl) *nl = 0;
            say("S| %s\n", esc((unsigned char *)line, (long)strlen(line)));
            if (!nl) break;
            line = nl + 1;
        }
    }
    return 0;
}

/* Linux only (root): the errno past /proc/sys/kernel/pty/max. Not part of
 * the compared transcript (PAX's bound is its own: R-px111-4). */
static int max_mode(void) {
    char old[32] = "";
    int fd = open("/proc/sys/kernel/pty/max", O_RDWR);
    if (fd < 0) { say("max: %s\n", ename(errno)); return 1; }
    ssize_t n = read(fd, old, sizeof old - 1);
    if (n > 0) old[n] = 0;
    say("max: pty/max %s", old);
    lseek(fd, 0, SEEK_SET);
    (void)!write(fd, "4\n", 2);
    int m[8], k = 0, e = 0;
    for (; k < 8; k++) { errno = 0; m[k] = mopen(0); if (m[k] < 0) { e = errno; break; } }
    say("max: with pty/max 4, opened %d, then %s\n", k, ename(e));
    for (int i = 0; i < k; i++) close(m[i]);
    lseek(fd, 0, SEEK_SET);
    (void)!write(fd, old, strlen(old));
    close(fd);
    return 0;
}

int main(int argc, char **argv) {
    setvbuf(stdout, 0, _IOLBF, 0);
    if (pipe(rep) < 0) return 2;
    fcntl(rep[0], F_SETFL, O_NONBLOCK);
    root = geteuid() == 0;
    signal(SIGHUP, SIG_IGN);
    (void)ioctl(0, TIOCNOTTY);
    signal(SIGHUP, SIG_DFL);
    if (argc > 1 && strcmp(argv[1], "max") == 0) return max_mode();
    if (argc > 1 && strcmp(argv[1], "drive") == 0) {
        fflush(stdout);
        pid_t R = fork();
        if (R == 0) { setsid(); _exit(drive()); }
        int st;
        waitpid(R, &st, 0);
        say("done: drive %s\n", how(R, st));
        return 0;
    }
    say("ptyprobe: px111's probe, as %s\n", root ? "root" : "a user");
    fflush(stdout);
    pid_t R = fork();
    if (R == 0) {
        setsid();
        section(sec_open);
        section(sec_termios);
        section(sec_ctty);
        section(sec_winsz);
        section(sec_hangup);
        section(sec_poll);
        section(sec_many);
        fflush(stdout);
        _exit(0);
    }
    int st;
    waitpid(R, &st, 0);
    say("done: R %s\n", how(R, st));
    return 0;
}
