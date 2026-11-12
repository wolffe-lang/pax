/* px125: what a terminal multiplexer's server asks of the kernel. One
 * process holding many pseudo-terminals, each with a shell of its own
 * session, all read by one epoll loop; a flood through one while the
 * others answer; a pane nobody reads; the window's size and a pty inside
 * a pty; the terminal's signal keys; a child that leaves its starter's
 * session; Unix-domain sockets for the clients (the path's owner and
 * mode, sixteen clients beside the panes, the peer's credentials, a
 * stale socket, descriptor passing); non-blocking writes and the timers
 * a loop has; termios raw and back, and after a client's SIGKILL.
 *
 *   muxprobe            every section: A1 A6 A2 A3 A4, A1.9, A5 A6 A7 A8, as init
 *   muxprobe flood N    (a pane's program) N bytes of the stream on its
 *                       terminal put raw, after a header
 *   muxprobe pane       (a pane's program, one thread) a line at a time:
 *                       `echo TEXT` writes TEXT, `exec PROG ARG...` runs it
 *   muxprobe spew       (a pane's program) writes 1 KiB blocks for ever
 *   muxprobe hold       (a pane's program) its terminal raw, reads nothing
 *   muxprobe winch      (a pane's program) `winch ROWS COLS` at its start
 *                       and at each SIGWINCH; ends at end of input
 *   muxprobe relay      (a pane's program) a pty inside its own: the
 *                       inner program `muxprobe winch`, its output
 *                       copied out, the outer size copied in at SIGWINCH
 *   muxprobe sig        (a pane's program) `heard INT` and so on for the
 *                       three keys' signals; ends at end of input
 *   muxprobe rawkill    (a pane's program) its terminal raw, then waits
 *                       for the SIGKILL
 *   muxprobe keys       the console put raw: each read's bytes as hex,
 *                       `keys: done` after a lone `Q` (tests/mpx7-mux B5)
 *   muxprobe paint      full screens drawn on the console, timed (B7)
 *
 * Run as the first program on PAX's console and as pid 1 of a fresh pid
 * namespace on a pseudo-terminal in a throwaway Ubuntu container
 * (tools/linux-tree), the same static binary; the transcripts are held
 * line for line (tests/mpx7-mux.d/check.py). A line that starts with `~`
 * is a measurement (a time, a rate, a count the kernels choose
 * differently) and is held to bounds, not to Linux's line. Every other
 * line is `ROW text`, no pid, time or address in it.
 *
 * Written from pty(7), pts(4), ioctl_tty(2), termios(3), unix(7),
 * socket(7), epoll(7), eventfd(2), timerfd_create(2), signalfd(2),
 * poll(2), credentials(7), cmsg(3), proc_pid_stat(5), signal(7) and
 * POSIX.1-2024's General Terminal Interface (man-pages 6.7); the shapes
 * of px111's user/elf/ptyprobe.c. No C library's, kernel's, shell's or
 * multiplexer's source was read. Written for this lane. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define PANES 32
#define MAXP 48
#define LOOP "while read -r l; do eval \"$l\"; done"
#define FLOOD_BYTES 50000000L
#define HEADER "<<px125 flood>>"

/* --- small things -------------------------------------------------------- */

static const char *ename(int e) {
    switch (e) {
    case 0: return "0";
    case EPERM: return "EPERM"; case ENOENT: return "ENOENT"; case ESRCH: return "ESRCH";
    case EINTR: return "EINTR"; case EIO: return "EIO"; case ENXIO: return "ENXIO";
    case EBADF: return "EBADF"; case ECHILD: return "ECHILD"; case EAGAIN: return "EAGAIN";
    case EACCES: return "EACCES"; case EFAULT: return "EFAULT"; case EINVAL: return "EINVAL";
    case ENOTTY: return "ENOTTY"; case ENOSPC: return "ENOSPC"; case EPIPE: return "EPIPE";
    case EMFILE: return "EMFILE"; case ENOSYS: return "ENOSYS"; case EOPNOTSUPP: return "EOPNOTSUPP";
    case EADDRINUSE: return "EADDRINUSE"; case ECONNREFUSED: return "ECONNREFUSED";
    case ESOCKTNOSUPPORT: return "ESOCKTNOSUPPORT"; case EAFNOSUPPORT: return "EAFNOSUPPORT";
    case EPROTONOSUPPORT: return "EPROTONOSUPPORT"; case ENOPROTOOPT: return "ENOPROTOOPT";
    case ENOTSOCK: return "ENOTSOCK"; case EEXIST: return "EEXIST"; case ENOTCONN: return "ENOTCONN";
    default: { static char b[32]; snprintf(b, sizeof b, "errno%d", e); return b; }
    }
}

static const char *sname(int s) {
    switch (s) {
    case SIGHUP: return "HUP"; case SIGINT: return "INT"; case SIGQUIT: return "QUIT";
    case SIGTERM: return "TERM"; case SIGKILL: return "KILL"; case SIGTSTP: return "TSTP";
    case SIGCONT: return "CONT"; case SIGWINCH: return "WINCH"; case SIGPIPE: return "PIPE";
    default: { static char b[16]; snprintf(b, sizeof b, "SIG%d", s); return b; }
    }
}

static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap); /* line-buffered: each row reaches the console in one write */
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

static const char *how(pid_t w, int st) {
    static char b[64];
    if (w == 0) return "running";
    if (w < 0) return ename(errno);
    if (WIFSTOPPED(st)) snprintf(b, sizeof b, "stopped by %s", sname(WSTOPSIG(st)));
    else if (WIFEXITED(st)) snprintf(b, sizeof b, "exited %d", WEXITSTATUS(st));
    else if (WIFSIGNALED(st)) snprintf(b, sizeof b, "killed by %s", sname(WTERMSIG(st)));
    else snprintf(b, sizeof b, "status 0x%x", st);
    return b;
}

/* Wait up to `ms` for `p` to change (an end or a stop): how. */
static const char *settle_child(pid_t p, int ms) {
    int st = 0;
    long end = now_ms() + ms;
    for (;;) {
        pid_t w = waitpid(p, &st, WNOHANG | WUNTRACED);
        if (w != 0 || now_ms() >= end) return how(w, st);
        nap(10);
    }
}

/* /proc/<pid>/stat: the state, the parent, the session and tty_nr. */
struct pstat { char state; long ppid, pgrp, sess, tty; int ok; };
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
    if (q && sscanf(q + 2, "%c %ld %ld %ld %ld", &r.state, &r.ppid, &r.pgrp, &r.sess, &r.tty) == 5) r.ok = 1;
    return r;
}

static int pty_nr(void) {
    char b[32];
    int fd = open("/proc/sys/kernel/pty/nr", O_RDONLY);
    if (fd < 0) return -1;
    ssize_t n = read(fd, b, sizeof b - 1);
    close(fd);
    if (n <= 0) return -1;
    b[n] = 0;
    return atoi(b);
}

static void raw_fd(int fd) {
    struct termios t;
    if (tcgetattr(fd, &t) != 0) return;
    cfmakeraw(&t);
    tcsetattr(fd, TCSANOW, &t);
}

static void nonblock(int fd) { fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) | O_NONBLOCK); }

static int putall(int fd, const void *p, size_t n) {
    const char *c = p;
    while (n > 0) {
        ssize_t k = write(fd, c, n);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) return -1;
        c += k;
        n -= (size_t)k;
    }
    return 0;
}

static void puts_fd(int fd, const char *s) { (void)putall(fd, s, strlen(s)); }

/* Bytes as a quoted C-like string, the last 160 at most. */
static const char *esc(const unsigned char *b, long n) {
    static char o[1024];
    size_t k = 0;
    long i = n > 160 ? n - 160 : 0;
    o[k++] = '"';
    for (; i < n && k < sizeof o - 8; i++) {
        unsigned c = b[i];
        if (c == '\r') { o[k++] = '\\'; o[k++] = 'r'; }
        else if (c == '\n') { o[k++] = '\\'; o[k++] = 'n'; }
        else if (c == '"' || c == '\\') { o[k++] = '\\'; o[k++] = (char)c; }
        else if (c < 32 || c >= 127) k += (size_t)snprintf(o + k, 8, "\\x%02x", c);
        else o[k++] = (char)c;
    }
    o[k++] = '"';
    o[k] = 0;
    return o;
}

/* --- the flood's stream: xorshift64*, eight bytes a step ------------------ */

struct stream { uint64_t x; uint64_t w; int left; };
static void stream_init(struct stream *s) { s->x = 0x9e3779b97f4a7c15ULL; s->left = 0; }
static inline unsigned char stream_next(struct stream *s) {
    if (s->left == 0) {
        s->x ^= s->x >> 12; s->x ^= s->x << 25; s->x ^= s->x >> 27;
        s->w = s->x * 0x2545f4914f6cdd1dULL;
        s->left = 8;
    }
    unsigned char b = (unsigned char)s->w;
    s->w >>= 8;
    s->left--;
    return b;
}

/* --- the pane programs ---------------------------------------------------- */

static int mode_flood(long n) {
    raw_fd(1);
    struct stream s;
    stream_init(&s);
    static unsigned char buf[65536];
    if (putall(1, HEADER, strlen(HEADER)) < 0) return 3;
    while (n > 0) {
        long k = n < (long)sizeof buf ? n : (long)sizeof buf;
        for (long i = 0; i < k; i++) buf[i] = stream_next(&s);
        if (putall(1, buf, (size_t)k) < 0) return 3;
        n -= k;
    }
    return 0;
}

/* A pane's program in one thread (a shell would take two on PAX: a
 * wolf program's runtime starts a thread beside main): reads a line at a
 * time on its terminal; `echo TEXT` writes TEXT, `exec PROG ARG...` runs
 * PROG in its place. */
static int mode_pane(void) {
    char line[4096];
    size_t n = 0;
    for (;;) {
        ssize_t r = read(0, line + n, sizeof line - 1 - n);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) return 0;
        n += (size_t)r;
        char *nl;
        while ((nl = memchr(line, '\n', n)) != 0) {
            *nl = 0;
            if (strncmp(line, "echo ", 5) == 0) {
                char out[4200];
                snprintf(out, sizeof out, "%s\n", line + 5);
                puts_fd(1, out);
            } else if (strncmp(line, "exec ", 5) == 0) {
                char *av[16];
                int ac = 0;
                for (char *w = strtok(line + 5, " "); w && ac < 15; w = strtok(0, " ")) av[ac++] = w;
                av[ac] = 0;
                if (ac) execv(av[0], av);
                puts_fd(1, "exec failed\n");
            }
            size_t used = (size_t)(nl - line) + 1;
            memmove(line, line + used, n - used);
            n -= used;
        }
        if (n == sizeof line - 1) n = 0;
    }
}

static int mode_spew(void) {
    static char buf[1024];
    memset(buf, 'x', sizeof buf);
    raw_fd(1);
    for (;;)
        if (putall(1, buf, sizeof buf) < 0) return 3;
}

static int mode_hold(void) {
    raw_fd(0);
    for (;;) pause();
    return 0;
}

static volatile sig_atomic_t winched;
static int wpipe[2] = {-1, -1};
static void on_winch(int s) { (void)s; winched = 1; if (wpipe[1] >= 0) (void)!write(wpipe[1], "w", 1); }

static void winch_line(int fd) {
    struct winsize w;
    char b[64];
    if (ioctl(fd, TIOCGWINSZ, &w) != 0) snprintf(b, sizeof b, "winch %s\n", ename(errno));
    else snprintf(b, sizeof b, "winch %u %u\n", w.ws_row, w.ws_col);
    puts_fd(1, b);
}

static int mode_winch(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_winch;
    sigaction(SIGWINCH, &sa, 0); /* no SA_RESTART: the read below is torn */
    winch_line(0);
    for (;;) {
        char b[256];
        ssize_t k = read(0, b, sizeof b);
        if (winched) { winched = 0; winch_line(0); }
        if (k == 0 || (k < 0 && errno != EINTR)) return 0;
    }
}

static volatile sig_atomic_t heard_sig;
static void on_sig(int s) { heard_sig = s; }

static int mode_sig(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_sig;
    sigaction(SIGINT, &sa, 0);
    sigaction(SIGQUIT, &sa, 0);
    sigaction(SIGTSTP, &sa, 0);
    puts_fd(1, "sig: ready\n");
    for (;;) {
        char b[256];
        ssize_t k = read(0, b, sizeof b);
        if (heard_sig) {
            char m[32];
            snprintf(m, sizeof m, "heard %s\n", sname(heard_sig));
            heard_sig = 0;
            puts_fd(1, m);
        }
        if (k == 0 || (k < 0 && errno != EINTR)) return 0;
    }
}

static int mode_rawkill(void) {
    raw_fd(0);
    puts_fd(1, "raw: set\r\n");
    for (;;) pause();
    return 0;
}

/* A pty in a pty: the inner program on a pty this one holds, its output
 * copied to ours, ours to it, our size given to it at each SIGWINCH. */
static int mode_relay(void) {
    if (pipe(wpipe) < 0) return 3;
    nonblock(wpipe[0]);
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_winch;
    sa.sa_flags = SA_RESTART;
    sigaction(SIGWINCH, &sa, 0);
    int m = posix_openpt(O_RDWR | O_NOCTTY);
    if (m < 0 || unlockpt(m) != 0) { puts_fd(1, "relay: no pty\n"); return 3; }
    char name[64];
    if (ptsname_r(m, name, sizeof name) != 0) return 3;
    struct winsize w;
    if (ioctl(0, TIOCGWINSZ, &w) == 0) ioctl(m, TIOCSWINSZ, &w);
    pid_t g = fork();
    if (g == 0) {
        setsid();
        int s = open(name, O_RDWR);
        if (s < 0) _exit(3);
        dup2(s, 0); dup2(s, 1); dup2(s, 2);
        if (s > 2) close(s);
        close(m);
        execl("/bin/muxprobe", "muxprobe", "winch", (char *)0);
        _exit(127);
    }
    for (;;) {
        struct pollfd p[3] = {{m, POLLIN, 0}, {0, POLLIN, 0}, {wpipe[0], POLLIN, 0}};
        if (poll(p, 3, -1) < 0) { if (errno == EINTR) continue; break; }
        if (p[2].revents & POLLIN) {
            char c[16];
            while (read(wpipe[0], c, sizeof c) > 0) {}
            if (ioctl(0, TIOCGWINSZ, &w) == 0) ioctl(m, TIOCSWINSZ, &w);
        }
        if (p[0].revents & (POLLIN | POLLHUP | POLLERR)) {
            char b[4096];
            ssize_t k = read(m, b, sizeof b);
            if (k <= 0) break;
            if (putall(1, b, (size_t)k) < 0) break;
        }
        if (p[1].revents & (POLLIN | POLLHUP | POLLERR)) {
            char b[4096];
            ssize_t k = read(0, b, sizeof b);
            if (k <= 0) break;
            (void)putall(m, b, (size_t)k);
        }
    }
    close(m);
    int st;
    waitpid(g, &st, 0);
    return 0;
}

/* --- panes ------------------------------------------------------------------ */

struct pane {
    int m;          /* the master, non-blocking; -1 once closed */
    pid_t pid;      /* its program, the session's leader */
    int num;        /* the pty's number */
    char buf[8192]; /* the last bytes read, for matching */
    size_t len;
    long total;     /* bytes read since it was made */
    int flood;      /* 1 while its bytes are the flood's stream */
    struct stream s;
    long fseen;     /* flood bytes checked */
    long fbad;      /* the offset of the first wrong one + 1 (0: none) */
    int hdr;        /* the header seen */
    int shell;      /* a shell of A1 or A3, ended by close_all */
    int reaped;     /* its program waited for */
};

static struct pane P[MAXP];
static long flood_done_ms = -1; /* when the flood's last byte was checked */
static char *SH[] = {"/bin/sh", "-c", LOOP, 0};
static char *PANE[] = {"/bin/muxprobe", "pane", 0};
#define NEED(k, row) do { if ((k) < 0) { say("%s no pane: %s\n", row, ename(errno)); fflush(stdout); return; } } while (0)
static int np;
static int ep = -1;
static int rep[2]; /* children's reports before exec: one line each */

static void pane_add(int k) {
    struct epoll_event e;
    memset(&e, 0, sizeof e);
    e.events = EPOLLIN;
    e.data.u32 = (uint32_t)k;
    epoll_ctl(ep, EPOLL_CTL_ADD, P[k].m, &e);
}

static void pane_del(int k) { epoll_ctl(ep, EPOLL_CTL_DEL, P[k].m, 0); }

/* A pane: a pty and `argv` in a session of its own on it. ign: the child
 * ignores SIGINT and SIGQUIT before exec (1), or ignores and then resets
 * them to the default (2), as a server that resets its panes would. */
static int pane_start(char *const argv[], int ign, int addloop) {
    int k = np;
    if (k >= MAXP) return -1;
    struct pane *p = &P[k];
    memset(p, 0, sizeof *p);
    p->m = posix_openpt(O_RDWR | O_NOCTTY);
    if (p->m < 0) return -1;
    if (unlockpt(p->m) != 0) { close(p->m); return -1; }
    unsigned n = 0;
    ioctl(p->m, TIOCGPTN, &n);
    p->num = (int)n;
    char name[64];
    if (ptsname_r(p->m, name, sizeof name) != 0) { close(p->m); return -1; }
    fflush(stdout);
    pid_t c = fork();
    if (c == 0) {
        if (setsid() < 0) _exit(120);
        int s = open(name, O_RDWR); /* no O_NOCTTY: the session takes it */
        if (s < 0) _exit(121);
        int ok = 1;
        pid_t sid = 0;
        if (ioctl(s, TIOCGSID, &sid) != 0 || sid != getpid()) ok = 0;
        if (tcgetpgrp(s) != getpgrp()) ok = 0;
        char line[64];
        snprintf(line, sizeof line, "%d %s\n", k, ok ? "ok" : "bad");
        (void)!write(rep[1], line, strlen(line));
        dup2(s, 0); dup2(s, 1); dup2(s, 2);
        if (s > 2) close(s);
        for (int fd = 3; fd < 256; fd++) close(fd);
        signal(SIGPIPE, SIG_DFL); /* this probe ignores it; its panes do not */
        if (ign) { signal(SIGINT, SIG_IGN); signal(SIGQUIT, SIG_IGN); }
        if (ign == 2) { signal(SIGINT, SIG_DFL); signal(SIGQUIT, SIG_DFL); }
        execv(argv[0], argv);
        _exit(127);
    }
    if (c < 0) { close(p->m); return -1; }
    p->pid = c;
    p->shell = argv == SH || argv == PANE;
    nonblock(p->m);
    np++;
    if (addloop) pane_add(k);
    return k;
}

/* settle_child for pane k's program, marking it waited for once it ended. */
static const char *pane_settle(int k, int ms) {
    const char *r = settle_child(P[k].pid, ms);
    if (strncmp(r, "exited", 6) == 0 || strncmp(r, "killed", 6) == 0) P[k].reaped = 1;
    return r;
}

/* Take what pane k has; 0, or -1 once it reads EIO or end of file. */
static int pane_read(int k) {
    struct pane *p = &P[k];
    static unsigned char b[65536];
    for (;;) {
        ssize_t r = read(p->m, b, sizeof b);
        if (r < 0 && errno == EINTR) continue;
        if (r < 0 && errno == EAGAIN) return 0;
        if (r <= 0) return -1;
        p->total += r;
        ssize_t i = 0;
        if (p->flood && !p->hdr) {
            /* the header, then the stream: keep text until it shows */
            size_t room = sizeof p->buf - 1 - p->len;
            size_t take = (size_t)r < room ? (size_t)r : room;
            memcpy(p->buf + p->len, b, take);
            p->len += take;
            p->buf[p->len] = 0;
            char *h = strstr(p->buf, HEADER);
            if (!h) continue;
            p->hdr = 1;
            size_t after = (size_t)(h - p->buf) + strlen(HEADER);
            /* what of this read lies past the header */
            i = (ssize_t)take - (ssize_t)(p->len - after);
            p->len = 0;
        }
        if (p->flood && p->hdr) {
            for (; i < r; i++) {
                unsigned char want = stream_next(&p->s);
                if (b[i] != want && !p->fbad) p->fbad = p->fseen + 1;
                p->fseen++;
            }
            if (p->fseen >= FLOOD_BYTES && flood_done_ms < 0) flood_done_ms = now_ms();
            continue;
        }
        if ((size_t)r >= sizeof p->buf - 1) {
            memcpy(p->buf, b + r - (sizeof p->buf - 1), sizeof p->buf - 1);
            p->len = sizeof p->buf - 1;
        } else {
            if (p->len + (size_t)r > sizeof p->buf - 1) {
                size_t drop = p->len + (size_t)r - (sizeof p->buf - 1);
                memmove(p->buf, p->buf + drop, p->len - drop);
                p->len -= drop;
            }
            memcpy(p->buf + p->len, b, (size_t)r);
            p->len += (size_t)r;
        }
        p->buf[p->len] = 0;
    }
}

/* One turn of the loop: wait up to ms, read every ready pane; the
 * other descriptors' events are handed to `other`. */
static void (*other)(uint32_t tag, uint32_t ev);
static int turn(int ms) {
    struct epoll_event ev[64];
    int n = epoll_wait(ep, ev, 64, ms);
    for (int i = 0; i < n; i++) {
        uint32_t t = ev[i].data.u32;
        if (t < MAXP) {
            if (pane_read((int)t) < 0) pane_del((int)t);
        } else if (other) {
            other(t, ev[i].events);
        }
    }
    return n;
}

static int has(int k, const char *s) { return strstr(P[k].buf, s) != 0; }
static void forget(int k) { P[k].len = 0; P[k].buf[0] = 0; }

/* Turn until pane k shows s, or ms pass: 1 when it showed. */
static int until(int k, const char *s, int ms) {
    long end = now_ms() + ms;
    while (!has(k, s)) {
        long left = end - now_ms();
        if (left <= 0) return 0;
        turn(left < 20 ? (int)left : 20);
    }
    return 1;
}

static void type(int k, const char *s) { (void)putall(P[k].m, s, strlen(s)); }

/* The children's reports so far: how many said ok. */
static int reports_ok(int want, int ms) {
    char b[8192];
    size_t len = 0;
    long end = now_ms() + ms;
    int lines = 0;
    while (lines < want && now_ms() < end) {
        ssize_t r = read(rep[0], b + len, sizeof b - 1 - len);
        if (r > 0) {
            for (ssize_t i = 0; i < r; i++) if (b[len + (size_t)i] == '\n') lines++;
            len += (size_t)r;
        } else {
            nap(10);
        }
    }
    b[len] = 0;
    int ok = 0;
    for (char *s = strtok(b, "\n"); s; s = strtok(0, "\n")) if (strstr(s, " ok")) ok++;
    return ok;
}

static int cmp_long(const void *a, const void *b) {
    long x = *(const long *)a, y = *(const long *)b;
    return (x > y) - (x < y);
}

/* --- A1: 32 panes, one loop, a flood --------------------------------------- */

static int nr0;

/* How many processes can be at once: children that wait on a pipe until
 * a fork fails or 100 are made. */
static void sec_a10(void) {
    int gate[2];
    if (pipe2(gate, O_CLOEXEC) < 0) return;
    pid_t kids[100];
    int n = 0, e = 0;
    fflush(stdout);
    while (n < 100) {
        pid_t c = fork();
        if (c == 0) { char b; close(gate[1]); (void)!read(gate[0], &b, 1); _exit(0); }
        if (c < 0) { e = errno; break; }
        kids[n++] = c;
    }
    close(gate[1]);
    for (int i = 0; i < n; i++) { int st; waitpid(kids[i], &st, 0); }
    close(gate[0]);
    if (n == 100) say("A1.0 100 processes at once besides this one: yes\n");
    else say("A1.0 100 processes at once besides this one: NO, fork %s after %d\n", ename(e), n);
    say("~A1.0 processes made at once: %d%s\n", n, n == 100 ? " (the most asked)" : "");
}

/* /proc/<pid>/status's Threads line. */
static int threads_of(pid_t p) {
    char path[64], b[4096];
    snprintf(path, sizeof path, "/proc/%d/status", (int)p);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t n = read(fd, b, sizeof b - 1);
    close(fd);
    if (n <= 0) return -1;
    b[n] = 0;
    char *t = strstr(b, "\nThreads:");
    return t ? atoi(t + 9) : -2;
}

static void sec_a1(void) {
    nr0 = pty_nr();
    /* 32 ptys at once, held by this process alone */
    int held[PANES], nheld = 0, first = -1, consecutive = 1;
    for (int i = 0; i < PANES; i++) {
        int m = posix_openpt(O_RDWR | O_NOCTTY);
        if (m < 0) break;
        unsigned n = 0;
        ioctl(m, TIOCGPTN, &n);
        if (first < 0) first = (int)n;
        else if ((int)n != first + i) consecutive = 0;
        held[nheld++] = m;
    }
    say("A1.1 %d ptys open at once in one process, %s numbers\n", nheld, consecutive ? "consecutive" : "scattered");
    for (int i = 0; i < nheld; i++) close(held[i]);
    /* a program on each, in a session of its own: one thread each (pelt's
     * second thread is A1.9's question) */
    char cmd[64], want[32];
    int made = 0, forkfail = 0, ferr = 0, silent = 0;
    int alive[PANES], nalive = 0;
    for (int i = 0; i < PANES; i++) {
        int k = pane_start(PANE, 0, 1);
        if (k < 0) { forkfail++; ferr = errno; continue; }
        made++;
        snprintf(cmd, sizeof cmd, "echo pong %d\n", k);
        snprintf(want, sizeof want, "pong %d\r\n", k);
        type(k, cmd);
        if (!until(k, want, 10000)) { silent++; continue; }
        forget(k);
        alive[nalive++] = k;
    }
    say("A1.2 %d children each lead a session of their own, their slave its controlling terminal, their group its foreground\n",
        reports_ok(made, 5000));
    say("A1.2 %d of 32 panes' programs answered a typed line%s%s\n", nalive, forkfail ? "; fork " : "", forkfail ? ename(ferr) : "");
    if (silent) say("A1.2 %d never answered\n", silent);
    say("A1.3 one epoll object holds the %d masters\n", nalive);
    fflush(stdout);
    /* every running pane answers again, all typed at once */
    for (int j = 0; j < nalive; j++) {
        snprintf(cmd, sizeof cmd, "echo pong again %d\n", alive[j]);
        type(alive[j], cmd);
    }
    long end = now_ms() + 20000;
    int answered = 0;
    while (now_ms() < end) {
        turn(20);
        answered = 0;
        for (int j = 0; j < nalive; j++) {
            snprintf(want, sizeof want, "pong again %d\r\n", alive[j]);
            if (has(alive[j], want)) answered++;
        }
        if (answered == nalive) break;
    }
    say("A1.4 typed at once, every pane answered through the one loop: %s\n", answered == nalive ? "yes" : "NO");
    for (int k = 0; k < np; k++) forget(k);
    fflush(stdout);
    /* the flood through pane 0, the others pinged while it runs */
    struct termios t;
    tcgetattr(P[0].m, &t);
    t.c_lflag &= (tcflag_t)~ECHO;
    tcsetattr(P[0].m, TCSANOW, &t);
    P[0].flood = 1;
    stream_init(&P[0].s);
    char fl[96];
    snprintf(fl, sizeof fl, "exec /bin/muxprobe flood %ld\n", FLOOD_BYTES);
    type(0, fl);
    long t0 = now_ms(), tf = -1, lat[4096];
    int nl = 0, missed = 0, seq = 0;
    end = t0 + 600000;
    while (now_ms() < end && P[0].fseen < FLOOD_BYTES && nalive > 1) {
        int k = alive[1 + seq % (nalive - 1)];
        snprintf(cmd, sizeof cmd, "echo pong p%d\n", seq);
        snprintf(want, sizeof want, "pong p%d\r\n", seq);
        long s0 = now_ms();
        type(k, cmd);
        if (until(k, want, 10000)) { if (nl < 4096) lat[nl++] = now_ms() - s0; }
        else {
            missed++;
            struct pstat ps = pstat_of(P[k].pid);
            say("~A1.6 missed: pane %d ping %d after 10 s; its shell's state %c; the master shows %ld bytes: %s\n", k, seq,
                ps.state, (long)P[k].len, esc((unsigned char *)P[k].buf, (long)P[k].len));
            int late = until(k, want, 20000);
            say("~A1.6 then: %s after %ld ms in all\n", late ? "answered" : "still no answer", now_ms() - s0);
            fflush(stdout);
        }
        forget(k);
        seq++;
        long pause_end = now_ms() + 20;
        while (now_ms() < pause_end && P[0].fseen < FLOOD_BYTES) turn(10);
        if (P[0].hdr && tf < 0) tf = now_ms();
    }
    long t1 = now_ms();
    say("A1.5 the flood: %ld bytes through one master, %s\n", P[0].fseen,
        P[0].fseen == FLOOD_BYTES && !P[0].fbad ? "in order, none lost" : "WRONG");
    if (P[0].fbad) say("~A1.5 the first wrong byte at %ld\n", P[0].fbad - 1);
    long ms = (flood_done_ms < 0 ? t1 : flood_done_ms) - (tf < 0 ? t0 : tf);
    say("~A1.5 flood: %ld bytes in %ld ms, %ld kB/s\n", P[0].fseen, ms, ms > 0 ? P[0].fseen / ms : 0);
    qsort(lat, (size_t)nl, sizeof lat[0], cmp_long);
    say("A1.6 the other panes answered during the flood: %s\n", nl >= 1 && missed == 0 ? "every ping" : "NOT every ping");
    say("~A1.6 pings %d answered, %d missed; latency median %ld ms, p90 %ld ms, max %ld ms\n", nl, missed,
        nl ? lat[nl / 2] : -1, nl ? lat[nl * 9 / 10] : -1, nl ? lat[nl - 1] : -1);
    /* the flood's pane ends with its program */
    say("A1.7 the flood's program: %s\n", pane_settle(0, 5000));
    /* half the panes closed: their shells hear the hangup */
    int hup = 0, odd = 0, shut = 0;
    for (int k = PANES / 2; k < made; k++) if (P[k].m >= 0) { close(P[k].m); P[k].m = -1; shut++; }
    for (int k = PANES / 2; k < made; k++) {
        if (P[k].reaped) continue;
        const char *h = pane_settle(k, 5000);
        if (strcmp(h, "killed by HUP") == 0) hup++;
        else { odd++; say("~A1.7 pane %d's shell: %s\n", k, h); }
    }
    say("A1.7 the last %d panes' masters closed: their %d running shells ended by SIGHUP%s\n", shut, hup, odd ? ", and OTHERS otherwise" : "");
    fflush(stdout);
}

/* --- A6.3: sixteen clients on one listener, in the panes' loop ------------- */

#define SOCKDIR "/tmp/mux"
#define TAG_LISTEN 1000u
#define TAG_CONN 2000u

static int lfd = -1;
static int conns[32], nconn, answered_c, credok, credusr, forkfail, forkerr;
static pid_t cpids[32];
static char cbuf[32][128];
static size_t clen[32];

static void on_other(uint32_t tag, uint32_t ev) {
    (void)ev;
    if (tag == TAG_LISTEN) {
        for (;;) {
            int c = accept4(lfd, 0, 0, SOCK_NONBLOCK | SOCK_CLOEXEC);
            if (c < 0) break;
            int i = nconn++;
            conns[i] = c;
            clen[i] = 0;
            struct epoll_event e;
            memset(&e, 0, sizeof e);
            e.events = EPOLLIN;
            e.data.u32 = TAG_CONN + (uint32_t)i;
            epoll_ctl(ep, EPOLL_CTL_ADD, c, &e);
        }
        return;
    }
    if (tag >= TAG_CONN && tag < TAG_CONN + 32) {
        int i = (int)(tag - TAG_CONN);
        ssize_t r = read(conns[i], cbuf[i] + clen[i], sizeof cbuf[i] - 1 - clen[i]);
        if (r <= 0) { epoll_ctl(ep, EPOLL_CTL_DEL, conns[i], 0); close(conns[i]); conns[i] = -1; return; }
        clen[i] += (size_t)r;
        cbuf[i][clen[i]] = 0;
        int k, pid;
        if (strchr(cbuf[i], '\n') && sscanf(cbuf[i], "hello %d %d", &k, &pid) == 2) {
            struct ucred u;
            socklen_t ul = sizeof u;
            if (getsockopt(conns[i], SOL_SOCKET, SO_PEERCRED, &u, &ul) == 0 && u.pid == pid) {
                credok++;
                if (k == 0 && u.uid == 1000 && u.gid == 1000) credusr = 1;
                if (k != 0 && u.uid == 0 && u.gid == 0) {}
            }
            char a[32];
            snprintf(a, sizeof a, "ok %d\n", k);
            (void)putall(conns[i], a, strlen(a));
            answered_c++;
            clen[i] = 0;
        }
    }
}

static int as_user(void) {
    if (setgroups(0, 0) != 0 && errno != EPERM) return -1;
    if (setresgid(1000, 1000, 1000) != 0) return -1;
    if (setresuid(1000, 1000, 1000) != 0) return -1;
    return 0;
}

static int connect_path(const char *path) {
    int s = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (s < 0) return -1;
    struct sockaddr_un a;
    memset(&a, 0, sizeof a);
    a.sun_family = AF_UNIX;
    strncpy(a.sun_path, path, sizeof a.sun_path - 1);
    if (connect(s, (struct sockaddr *)&a, sizeof a) != 0) { int e = errno; close(s); errno = e; return -1; }
    return s;
}

static int bind_path(const char *path, int listen_too) {
    int s = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (s < 0) return -1;
    struct sockaddr_un a;
    memset(&a, 0, sizeof a);
    a.sun_family = AF_UNIX;
    strncpy(a.sun_path, path, sizeof a.sun_path - 1);
    if (bind(s, (struct sockaddr *)&a, sizeof a) != 0) { int e = errno; close(s); errno = e; return -1; }
    if (listen_too && listen(s, 64) != 0) { int e = errno; close(s); errno = e; return -1; }
    return s;
}

static const char *stat_sock(const char *path) {
    static char b[96];
    struct stat st;
    if (stat(path, &st) != 0) return ename(errno);
    snprintf(b, sizeof b, "%s mode %04o uid %u gid %u", S_ISSOCK(st.st_mode) ? "socket" : "not a socket",
             st.st_mode & 07777, st.st_uid, st.st_gid);
    return b;
}

static void sec_a6_clients(int panes) {
    mkdir(SOCKDIR, 0755);
    chmod(SOCKDIR, 0755);
    mode_t old = umask(077);
    lfd = bind_path(SOCKDIR "/srv", 1);
    umask(old);
    say("A6.1 a stream socket bound at a path under umask 077: %s\n", lfd < 0 ? ename(errno) : stat_sock(SOCKDIR "/srv"));
    if (lfd < 0) return;
    nonblock(lfd);
    /* who may connect: the mode, then the owner */
    fflush(stdout);
    pid_t u = fork();
    if (u == 0) {
        if (as_user() != 0) _exit(2);
        int s = connect_path(SOCKDIR "/srv");
        _exit(s >= 0 ? 0 : errno == EACCES ? 13 : 1);
    }
    int st;
    waitpid(u, &st, 0);
    say("A6.2 a user's connect to root's 0700 socket: %s\n",
        WIFEXITED(st) && WEXITSTATUS(st) == 13 ? "EACCES" : WIFEXITED(st) && WEXITSTATUS(st) == 0 ? "connected" : how(u, st));
    int ch = chown(SOCKDIR "/srv", 1000, 1000);
    say("A6.2 chown to 1000:1000: %s; now %s\n", ch == 0 ? "0" : ename(errno), stat_sock(SOCKDIR "/srv"));
    /* drain the refused try's queue entry, if any reached it */
    struct epoll_event e;
    memset(&e, 0, sizeof e);
    e.events = EPOLLIN;
    e.data.u32 = TAG_LISTEN;
    epoll_ctl(ep, EPOLL_CTL_ADD, lfd, &e);
    other = on_other;
    /* sixteen clients: client 0 a user's, the rest root's */
    fflush(stdout);
    for (int k = 0; k < 16; k++) {
        pid_t c = fork();
        if (c == 0) {
            if (k == 0 && as_user() != 0) _exit(2);
            int s = connect_path(SOCKDIR "/srv");
            if (s < 0) _exit(3);
            char h[64], a[64];
            snprintf(h, sizeof h, "hello %d %d\n", k, (int)getpid());
            if (putall(s, h, strlen(h)) < 0) _exit(4);
            size_t n = 0;
            while (n < sizeof a - 1) {
                ssize_t r = read(s, a + n, sizeof a - 1 - n);
                if (r <= 0) break;
                n += (size_t)r;
                if (memchr(a, '\n', n)) break;
            }
            a[n] = 0;
            char w[32];
            snprintf(w, sizeof w, "ok %d\n", k);
            _exit(strcmp(a, w) == 0 ? 0 : 5);
        }
        cpids[k] = c;
        if (c < 0) { forkfail++; forkerr = errno; }
    }
    if (forkfail) say("~A6.3 %d clients not made: fork %s\n", forkfail, ename(forkerr));
    /* the loop serves them while the panes still answer */
    long end = now_ms() + 20000;
    int pinged = 0, pongs = 0;
    while (now_ms() < end && answered_c < 16 - forkfail) {
        if (pinged < panes - 1) {
            char cmd[64], want[32];
            int k = 1 + pinged;
            if (P[k].reaped || P[k].m < 0) { pinged++; pongs++; continue; }
            snprintf(cmd, sizeof cmd, "echo pong c%d\n", pinged);
            snprintf(want, sizeof want, "pong c%d\r\n", pinged);
            type(k, cmd);
            if (until(k, want, 5000)) pongs++;
            forget(k);
            pinged++;
        } else {
            turn(20);
        }
    }
    int good = 0;
    for (int k = 0; k < 16; k++) {
        int s2;
        if (cpids[k] > 0 && waitpid(cpids[k], &s2, 0) == cpids[k] && WIFEXITED(s2) && WEXITSTATUS(s2) == 0) good++;
    }
    say("A6.3 16 clients on one listener in the loop beside the panes: %d accepted, %d answered, %d ended well; the panes asked meanwhile %s\n",
        nconn, answered_c, good, pongs == pinged ? "all answered" : "did NOT all answer");
    say("~A6.3 %d of %d panes pinged meanwhile answered\n", pongs, pinged);
    say("A6.4 SO_PEERCRED: %d of 16 name the client's own pid; the user's: %s\n", credok, credusr ? "uid 1000 gid 1000" : "NOT the user's ids");
    for (int i = 0; i < nconn; i++) if (conns[i] >= 0) { epoll_ctl(ep, EPOLL_CTL_DEL, conns[i], 0); close(conns[i]); }
    epoll_ctl(ep, EPOLL_CTL_DEL, lfd, 0);
    close(lfd);
    say("A6.5 the listener closed: the file %s\n", access(SOCKDIR "/srv", F_OK) == 0 ? "stays (close does not unlink)" : "is gone");
    unlink(SOCKDIR "/srv");
    fflush(stdout);
}

/* --- A2: back-pressure ------------------------------------------------------- */

static long fionread(int fd) { int n = -1; if (ioctl(fd, FIONREAD, &n) != 0) return -1; return n; }

static void sec_a2(int panes) {
    char *spew[] = {"/bin/muxprobe", "spew", 0};
    int k = pane_start(spew, 0, 0); /* not in the loop: nobody reads it */
    NEED(k, "A2.1");
    nap(300);
    long q1 = fionread(P[k].m);
    nap(300);
    long q2 = fionread(P[k].m);
    struct pstat ps = pstat_of(P[k].pid);
    say("A2.1 a pane nobody reads: its writer %s, the master's queue %s\n",
        ps.ok && ps.state == 'S' ? "asleep" : "NOT asleep", q1 == q2 && q1 > 0 ? "full and still" : "NOT still");
    say("~A2.1 the queue holds %ld bytes; the writer's state %c\n", q2, ps.state);
    int pongs = 0;
    int asked = 0;
    for (int i = 1; i < panes; i++) {
        char cmd[64], want[32];
        if (P[i].reaped || P[i].m < 0) continue;
        asked++;
        snprintf(cmd, sizeof cmd, "echo pong b%d\n", i);
        snprintf(want, sizeof want, "pong b%d\r\n", i);
        type(i, cmd);
        if (until(i, want, 5000)) pongs++;
        forget(i);
    }
    say("A2.2 meanwhile the other panes asked %s\n", pongs == asked ? "all answered" : "did NOT all answer");
    say("~A2.2 %d of %d answered\n", pongs, asked);
    /* read it: the writer goes on */
    long before = P[k].total;
    pane_add(k);
    long end = now_ms() + 500;
    while (now_ms() < end) turn(20);
    pane_del(k);
    say("A2.3 read again: the writer %s\n", P[k].total - before > q2 ? "went on" : "did NOT go on");
    kill(P[k].pid, SIGKILL);
    pane_settle(k, 2000);
    close(P[k].m);
    P[k].m = -1;
    /* the other way: a master written faster than its program reads */
    char *hold[] = {"/bin/muxprobe", "hold", 0};
    int h = pane_start(hold, 0, 0);
    NEED(h, "A2.4");
    nap(300);
    static char chunk[1000];
    memset(chunk, 'a', sizeof chunk);
    long took = 0;
    int e = 0;
    for (;;) {
        ssize_t r = write(P[h].m, chunk, sizeof chunk);
        if (r < 0) { e = errno; break; }
        took += r;
        if (took > 1 << 22) break;
    }
    struct pollfd pf = {P[h].m, POLLOUT, 0};
    poll(&pf, 1, 0);
    struct pollfd po = {P[1].m, POLLOUT, 0};
    poll(&po, 1, 0);
    say("A2.4 a master its program never reads, written non-blocking: %s, POLLOUT %s; another master POLLOUT %s\n",
        ename(e), pf.revents & POLLOUT ? "set" : "clear", po.revents & POLLOUT ? "set" : "clear");
    say("~A2.4 it took %ld bytes first\n", took);
    kill(P[h].pid, SIGKILL);
    pane_settle(h, 2000);
    close(P[h].m);
    P[h].m = -1;
    fflush(stdout);
}

/* --- A3: the window's size ------------------------------------------------- */

static void setsize(int m, int r, int c) {
    struct winsize w = {(unsigned short)r, (unsigned short)c, 0, 0};
    ioctl(m, TIOCSWINSZ, &w);
}

static void sec_a3(void) {
    char *wi[] = {"/bin/muxprobe", "winch", 0};
    int a = pane_start(wi, 0, 1);
    NEED(a, "A3.1");
    int b = pane_start(wi, 0, 1);
    NEED(b, "A3.1");
    until(a, "winch 0 0", 3000);
    until(b, "winch 0 0", 3000);
    forget(a);
    forget(b);
    setsize(P[a].m, 41, 120);
    int got = until(a, "winch 41 120", 3000);
    long end = now_ms() + 300;
    while (now_ms() < end) turn(20);
    say("A3.1 TIOCSWINSZ on a master: its program %s; another pane's %s\n", got ? "heard SIGWINCH and read 41 120" : "did NOT read 41 120",
        has(b, "winch") ? "heard it TOO" : "heard nothing");
    type(a, "\004");
    type(b, "\004");
    /* stty in a shell pane */
    int s = pane_start(SH, 0, 1);
    NEED(s, "A3.2");
    setsize(P[s].m, 33, 97);
    type(s, "stty size\n");
    say("A3.2 stty size in a shell pane sized 33 x 97: %s\n", until(s, "33 97\r\n", 5000) ? "33 97" : "NOT 33 97");
    /* a pty inside a pty */
    char *re[] = {"/bin/muxprobe", "relay", 0};
    int r = pane_start(re, 0, 1);
    NEED(r, "A3.3");
    until(r, "winch 0 0", 5000);
    forget(r);
    setsize(P[r].m, 33, 97);
    int one = until(r, "winch 33 97", 5000);
    forget(r);
    setsize(P[r].m, 41, 120);
    int two = until(r, "winch 41 120", 5000);
    say("A3.3 a pty inside a pty: the inner program read %s, then %s\n", one ? "33 97" : "NOT 33 97", two ? "41 120" : "NOT 41 120");
    type(r, "\004");
    say("A3.4 the relay's end: %s; the winch panes' %s, %s\n", pane_settle(r, 5000), pane_settle(a, 3000),
        pane_settle(b, 3000));
    fflush(stdout);
}

/* --- A4: the keys' signals through a master --------------------------------- */

static void sec_a4(void) {
    char *sg[] = {"/bin/muxprobe", "sig", 0};
    int k = pane_start(sg, 0, 1);
    NEED(k, "A4.1");
    until(k, "sig: ready", 3000);
    type(k, "\003");
    int i = until(k, "heard INT", 3000);
    type(k, "\034");
    int q = until(k, "heard QUIT", 3000);
    type(k, "\032");
    int z = until(k, "heard TSTP", 3000);
    say("A4.1 0x03, 0x1c, 0x1a to a master, its program handling them: %s, %s, %s\n", i ? "heard INT" : "NOT INT",
        q ? "heard QUIT" : "NOT QUIT", z ? "heard TSTP" : "NOT TSTP");
    type(k, "\004");
    pane_settle(k, 3000);
    char *sl[] = {"/bin/sleep", "30", 0};
    const char *what[3];
    const char key[3] = {3, 0x1c, 0x1a};
    for (int j = 0; j < 3; j++) {
        int p = pane_start(sl, 0, 1);
        NEED(p, "A4.2");
        nap(200);
        char c[2] = {key[j], 0};
        type(p, c);
        what[j] = strdup(pane_settle(p, 3000));
        kill(P[p].pid, SIGKILL);
        pane_settle(p, 2000);
    }
    say("A4.2 at their defaults, sleep 30: 0x03 %s, 0x1c %s, 0x1a %s\n", what[0], what[1], what[2]);
    for (int mode = 1; mode <= 2; mode++) {
        for (int j = 0; j < 2; j++) {
            int p = pane_start(sl, mode, 1);
            NEED(p, "A4.3");
            nap(200);
            char c[2] = {key[j], 0};
            type(p, c);
            what[j] = strdup(pane_settle(p, 600));
            kill(P[p].pid, SIGKILL);
            pane_settle(p, 2000);
        }
        say("A4.%d %s: 0x03 %s, 0x1c %s\n", mode + 2,
            mode == 1 ? "SIGINT and SIGQUIT ignored by the parent and inherited across exec"
                      : "ignored by the parent, reset to the default in the child before exec",
            what[0], what[1]);
    }
    fflush(stdout);
}

/* --- A1.9: 32 pelt shells at once, idle between their lines ------------------- */

static void sec_a19(void) {
    char cmd[64], want[48];
    int ks[PANES], started = 0, once = 0, again = 0, ended = 0, forkfail = 0, ferr = 0;
    char ends[256] = "";
    for (int i = 0; i < PANES; i++) {
        int k = pane_start(SH, 0, 1);
        if (k < 0) { forkfail++; ferr = errno; continue; }
        ks[started++] = k;
        long idle = now_ms() + 100; /* a pane's shell waits for its line */
        while (now_ms() < idle) turn(20);
        snprintf(cmd, sizeof cmd, "echo pong %d\n", k);
        snprintf(want, sizeof want, "pong %d\r\n", k);
        type(k, cmd);
        if (until(k, want, 10000)) once++;
        forget(k);
    }
    int th = started ? threads_of(P[ks[0]].pid) : -1;
    long end = now_ms() + 5000;
    while (now_ms() < end) turn(50);
    for (int j = 0; j < started; j++) {
        int k = ks[j];
        snprintf(cmd, sizeof cmd, "echo pong again %d\n", k);
        snprintf(want, sizeof want, "pong again %d\r\n", k);
        type(k, cmd);
        if (until(k, want, 5000)) { again++; continue; }
        const char *h = pane_settle(k, 1000);
        ended++;
        if (strlen(ends) < 200) { strcat(ends, " "); strcat(ends, h); }
    }
    say("A1.9 32 pelt shells at once, each idle between its lines: %s\n", again == PANES ? "every one answered twice" : "NOT every one answered twice");
    say("~A1.9 %d started (fork %s for %d), %d answered once, %d again after 5 s idle; %d did not:%s; the first shell's Threads line %d\n",
        started, forkfail ? ename(ferr) : "-", forkfail, once, again, ended, ends, th);
    for (int j = 0; j < started; j++) {
        int k = ks[j];
        if (P[k].m >= 0) { pane_del(k); close(P[k].m); P[k].m = -1; }
    }
    for (int j = 0; j < started; j++) {
        int k = ks[j];
        if (!P[k].reaped) { const char *h = pane_settle(k, 5000); if (strncmp(h, "running", 7) == 0) { kill(P[k].pid, SIGKILL); pane_settle(k, 2000); } }
    }
    fflush(stdout);
}

/* --- A5: a child that leaves its starter's session --------------------------- */

static void sec_a5(void) {
    int dp[2];
    if (pipe(dp) < 0) return;
    int m = posix_openpt(O_RDWR | O_NOCTTY);
    unlockpt(m);
    char name[64];
    ptsname_r(m, name, sizeof name);
    fflush(stdout);
    pid_t S = fork();
    if (S == 0) {
        setsid();
        int s = open(name, O_RDWR);
        if (s < 0) _exit(3);
        pid_t D = fork();
        if (D == 0) {
            setsid();
            close(s);
            pid_t me = getpid();
            (void)!write(dp[1], &me, sizeof me);
            for (;;) pause();
        }
        /* the starter ends only once the daemon has its own session, or
         * the starter's end would hang its group up first */
        for (int i = 0; i < 500 && getsid(D) != D; i++) nap(2);
        _exit(0);
    }
    close(dp[1]);
    dp[1] = -1;
    pid_t D = 0;
    if (read(dp[0], &D, sizeof D) != sizeof D) { say("A5.1 the daemon never said its pid\n"); fflush(stdout); return; }
    int st;
    waitpid(S, &st, 0);
    nap(200);
    struct pstat ps = pstat_of(D);
    say("A5.1 a daemon (setsid) whose starter ended: its parent is %s; its own session %s, no terminal %s\n",
        ps.ok && ps.ppid == 1 ? "pid 1" : ps.ok && ps.ppid == getpid() ? "this probe (not pid 1)" : "SOMETHING ELSE",
        ps.ok && ps.sess == D ? "yes" : "NO", ps.ok && ps.tty == 0 ? "yes" : "NO");
    say("~A5.1 this probe is pid %d; the daemon's parent %ld\n", (int)getpid(), ps.ppid);
    close(m); /* the starter's terminal hangs up */
    nap(300);
    ps = pstat_of(D);
    say("A5.2 after its starter's terminal hung up: %s\n", ps.ok && ps.state != 'Z' && kill(D, 0) == 0 ? "still running" : "GONE");
    kill(D, SIGTERM);
    nap(300);
    ps = pstat_of(D);
    say("A5.3 ended by SIGTERM: until its parent waits it is %s; then %s\n", ps.ok && ps.state == 'Z' ? "a zombie" : "NOT a zombie",
        settle_child(D, 2000));
    close(dp[0]);
    fflush(stdout);
}

/* The last thing init does: leave a daemon running (the suite reads
 * what the kernel does with it when init ends). */
static void leave_daemon(void) {
    fflush(stdout);
    pid_t S = fork();
    if (S == 0) {
        pid_t D = fork();
        if (D == 0) {
            setsid();
            for (;;) pause();
        }
        _exit(0);
    }
    int st;
    waitpid(S, &st, 0);
    say("A5.4 init ends now and leaves a daemon running\n");
    fflush(stdout);
}

/* --- A6: the rest of the sockets --------------------------------------------- */

static void sec_a6(void) {
    int rp[2];
    if (pipe(rp) < 0) return;
    fflush(stdout);
    pid_t Z = fork();
    if (Z == 0) {
        int s = bind_path(SOCKDIR "/stale", 1);
        (void)!write(rp[1], s >= 0 ? "r" : "x", 1);
        for (;;) pause();
    }
    char c = 0;
    (void)!read(rp[0], &c, 1);
    kill(Z, SIGKILL);
    int st;
    waitpid(Z, &st, 0);
    say("A6.6 a server killed by SIGKILL: its file %s\n", access(SOCKDIR "/stale", F_OK) == 0 ? stat_sock(SOCKDIR "/stale") : "is gone");
    int s = connect_path(SOCKDIR "/stale");
    const char *ce = s < 0 ? strdup(ename(errno)) : "connected";
    if (s >= 0) close(s);
    s = bind_path(SOCKDIR "/stale", 1);
    const char *be = s < 0 ? strdup(ename(errno)) : "0";
    if (s >= 0) close(s);
    int u = unlink(SOCKDIR "/stale");
    s = bind_path(SOCKDIR "/stale", 1);
    say("A6.6 then connect %s, bind %s; unlink %s, bind %s\n", ce, be, u == 0 ? "0" : ename(errno), s >= 0 ? "0" : ename(errno));
    if (s >= 0) close(s);
    unlink(SOCKDIR "/stale");
    /* descriptor passing */
    int sp[2], pp[2];
    socketpair(AF_UNIX, SOCK_STREAM, 0, sp);
    if (pipe(pp) < 0) return;
    (void)!write(pp[1], "x", 1);
    struct msghdr mh;
    struct iovec io;
    char one = '1';
    union { char buf[CMSG_SPACE(sizeof(int))]; struct cmsghdr align; } cu;
    memset(&mh, 0, sizeof mh);
    memset(&cu, 0, sizeof cu);
    io.iov_base = &one;
    io.iov_len = 1;
    mh.msg_iov = &io;
    mh.msg_iovlen = 1;
    mh.msg_control = cu.buf;
    mh.msg_controllen = sizeof cu.buf;
    struct cmsghdr *cm = CMSG_FIRSTHDR(&mh);
    cm->cmsg_level = SOL_SOCKET;
    cm->cmsg_type = SCM_RIGHTS;
    cm->cmsg_len = CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(cm), &pp[0], sizeof(int));
    ssize_t r = sendmsg(sp[0], &mh, 0);
    const char *se = r < 0 ? strdup(ename(errno)) : "1";
    const char *got = "nothing";
    if (r == 1) {
        char rb;
        union { char buf[CMSG_SPACE(sizeof(int))]; struct cmsghdr align; } cr;
        struct msghdr rh;
        struct iovec ri = {&rb, 1};
        memset(&rh, 0, sizeof rh);
        rh.msg_iov = &ri;
        rh.msg_iovlen = 1;
        rh.msg_control = cr.buf;
        rh.msg_controllen = sizeof cr.buf;
        ssize_t q = recvmsg(sp[1], &rh, 0);
        struct cmsghdr *c2 = CMSG_FIRSTHDR(&rh);
        if (q == 1 && c2 && c2->cmsg_type == SCM_RIGHTS) {
            int fd;
            memcpy(&fd, CMSG_DATA(c2), sizeof fd);
            char x = 0;
            got = read(fd, &x, 1) == 1 && x == 'x' ? "the descriptor arrived and reads the pipe" : "a descriptor that does not read";
            close(fd);
        } else {
            got = q < 0 ? strdup(ename(errno)) : "no descriptor";
        }
    }
    say("A6.7 SCM_RIGHTS over a socketpair: sendmsg %s; %s\n", se, got);
    close(sp[0]); close(sp[1]); close(pp[0]); close(pp[1]);
    /* the shapes PAX has not */
    int a = socket(AF_UNIX, SOCK_STREAM, 0);
    struct sockaddr_un an;
    memset(&an, 0, sizeof an);
    an.sun_family = AF_UNIX;
    memcpy(an.sun_path, "\0px125", 6);
    int ab = bind(a, (struct sockaddr *)&an, (socklen_t)(offsetof(struct sockaddr_un, sun_path) + 6));
    say("A6.8 an abstract name: bind %s\n", ab == 0 ? "0" : ename(errno));
    close(a);
    a = socket(AF_UNIX, SOCK_SEQPACKET, 0);
    say("A6.8 a SOCK_SEQPACKET socket for a path: %s\n", a >= 0 ? "made" : ename(errno));
    if (a >= 0) close(a);
    a = socket(AF_UNIX, SOCK_DGRAM, 0);
    say("A6.8 a SOCK_DGRAM socket for a path: %s\n", a >= 0 ? "made" : ename(errno));
    if (a >= 0) close(a);
    rmdir(SOCKDIR); /* the tree as it was made */
    fflush(stdout);
}

/* --- A7: non-blocking writes and timers -------------------------------------- */

static int chld[2] = {-1, -1};
static void on_chld(int s) { (void)s; if (chld[1] >= 0) (void)!write(chld[1], "c", 1); }

static void sec_a7(void) {
    int sp[2];
    socketpair(AF_UNIX, SOCK_STREAM, 0, sp);
    nonblock(sp[0]);
    static char big[100000];
    memset(big, 'b', sizeof big);
    ssize_t first = write(sp[0], big, sizeof big);
    long took = first > 0 ? first : 0;
    int e = 0;
    for (;;) {
        ssize_t r = write(sp[0], big, 4096);
        if (r < 0) { e = errno; break; }
        took += r;
        if (took > 1 << 24) break;
    }
    say("A7.1 a non-blocking unix stream: a 100000-byte write %s; then %s\n",
        first > 0 && first < (ssize_t)sizeof big ? "partial" : first == (ssize_t)sizeof big ? "taken whole" : ename(errno), ename(e));
    say("~A7.1 the first write took %ld, %ld in all\n", (long)first, took);
    int e2 = epoll_create1(EPOLL_CLOEXEC);
    struct epoll_event ev;
    memset(&ev, 0, sizeof ev);
    ev.events = EPOLLOUT;
    ev.data.u32 = 1;
    epoll_ctl(e2, EPOLL_CTL_ADD, sp[0], &ev);
    struct epoll_event got[4];
    int full = epoll_wait(e2, got, 4, 0);
    char sink[65536];
    nonblock(sp[1]);
    while (read(sp[1], sink, sizeof sink) > 0) {}
    int after = epoll_wait(e2, got, 4, 100);
    say("A7.2 EPOLLOUT while full: %s; after the peer drained: %s\n", full == 0 ? "none" : "SET", after == 1 && (got[0].events & EPOLLOUT) ? "set" : "NOT set");
    close(sp[0]); close(sp[1]);
    errno = 0;
    int tf = (int)syscall(SYS_timerfd_create, CLOCK_MONOTONIC, 0);
    say("A7.3 timerfd_create: %s\n", tf >= 0 ? "a descriptor" : ename(errno));
    if (tf >= 0) close(tf);
    sigset_t ss;
    sigemptyset(&ss);
    int sf = (int)syscall(SYS_signalfd4, -1, &ss, (size_t)8, 0);
    say("A7.3 signalfd4: %s\n", sf >= 0 ? "a descriptor" : ename(errno));
    if (sf >= 0) close(sf);
    struct timespec z = {0, 0};
    int pp = (int)syscall(SYS_ppoll, (void *)0, 0, &z, (void *)0, (size_t)8);
    say("A7.3 ppoll: %s\n", pp >= 0 ? "answered" : ename(errno));
    int e3 = epoll_create1(EPOLL_CLOEXEC); /* an empty object: only the deadline ends the wait */
    long t0 = now_ms();
    int w = epoll_wait(e3, got, 4, 100);
    long dt = now_ms() - t0;
    say("A7.4 epoll_wait with nothing to wait for and 100 ms: %d, %s\n", w, dt >= 100 ? "no earlier than its deadline" : "EARLY");
    say("~A7.4 it took %ld ms\n", dt);
    int efd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC);
    memset(&ev, 0, sizeof ev);
    ev.events = EPOLLIN;
    ev.data.u32 = 7;
    epoll_ctl(e3, EPOLL_CTL_ADD, efd, &ev);
    fflush(stdout);
    pid_t c = fork();
    if (c == 0) { nap(50); uint64_t one = 1; (void)!write(efd, &one, sizeof one); _exit(0); }
    w = epoll_wait(e3, got, 4, 3000);
    say("A7.5 an eventfd another process writes wakes the loop: %s\n", w == 1 && got[0].data.u32 == 7 ? "yes" : "NO");
    uint64_t drained;
    (void)!read(efd, &drained, sizeof drained);
    int st;
    waitpid(c, &st, 0);
    /* SIGCHLD through a self-pipe */
    if (pipe2(chld, O_NONBLOCK | O_CLOEXEC) < 0) return;
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_chld;
    sa.sa_flags = SA_RESTART | SA_NOCLDSTOP;
    sigaction(SIGCHLD, &sa, 0);
    memset(&ev, 0, sizeof ev);
    ev.events = EPOLLIN;
    ev.data.u32 = 8;
    epoll_ctl(e3, EPOLL_CTL_ADD, chld[0], &ev);
    fflush(stdout);
    c = fork();
    if (c == 0) { nap(50); _exit(0); }
    for (;;) {
        w = epoll_wait(e3, got, 4, 3000);
        if (w < 0 && errno == EINTR) continue;
        break;
    }
    int byp = 0;
    for (int i = 0; i < w; i++) if (got[i].data.u32 == 8) byp = 1;
    say("A7.6 SIGCHLD through a self-pipe wakes the loop: %s\n", byp ? "yes" : "NO");
    waitpid(c, &st, 0);
    signal(SIGCHLD, SIG_DFL);
    close(chld[0]); close(chld[1]);
    chld[0] = chld[1] = -1;
    close(efd); close(e2); close(e3);
    fflush(stdout);
}

/* --- A8: termios ------------------------------------------------------------- */

/* Which of termios' fields two settings differ in ("every field as
 * saved" when none): the four flag words, the line discipline, each of
 * the 19 control characters a kernel keeps, the speeds. */
static const char *tdiff(const struct termios *a, const struct termios *b) {
    static char out[256];
    out[0] = 0;
    if (a->c_iflag != b->c_iflag) strcat(out, " iflag");
    if (a->c_oflag != b->c_oflag) strcat(out, " oflag");
    if (a->c_cflag != b->c_cflag) strcat(out, " cflag");
    if (a->c_lflag != b->c_lflag) strcat(out, " lflag");
    if (a->c_line != b->c_line) strcat(out, " c_line");
    for (int i = 0; i < 19; i++)
        if (a->c_cc[i] != b->c_cc[i]) { char t[32]; snprintf(t, sizeof t, " c_cc[%d] %u->%u", i, a->c_cc[i], b->c_cc[i]); strcat(out, t); }
    if (cfgetispeed(a) != cfgetispeed(b)) strcat(out, " ispeed");
    if (cfgetospeed(a) != cfgetospeed(b)) strcat(out, " ospeed");
    return out[0] ? out + 1 : "every field as saved";
}

static void flags_row(const char *row, int fd) {
    struct termios t;
    if (tcgetattr(fd, &t) != 0) { say("%s %s\n", row, ename(errno)); return; }
    say("%s iflag 0x%x oflag 0x%x cflag 0x%x lflag 0x%x vmin %u vtime %u\n", row, (unsigned)t.c_iflag, (unsigned)t.c_oflag,
        (unsigned)t.c_cflag, (unsigned)t.c_lflag, t.c_cc[VMIN], t.c_cc[VTIME]);
}

/* What a full-screen client sets: cfmakeraw's flags. */
static void client_raw(int fd) {
    struct termios t;
    tcgetattr(fd, &t);
    t.c_iflag &= (tcflag_t)~(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL | IXON);
    t.c_oflag &= (tcflag_t)~OPOST;
    t.c_lflag &= (tcflag_t)~(ECHO | ECHONL | ICANON | ISIG | IEXTEN);
    t.c_cflag &= (tcflag_t)~(CSIZE | PARENB);
    t.c_cflag |= CS8;
    t.c_cc[VMIN] = 1;
    t.c_cc[VTIME] = 0;
    tcsetattr(fd, TCSANOW, &t);
}

static void sec_a8(void) {
    int m = posix_openpt(O_RDWR | O_NOCTTY);
    unlockpt(m);
    char name[64];
    ptsname_r(m, name, sizeof name);
    int s = open(name, O_RDWR | O_NOCTTY);
    struct termios saved, back;
    tcgetattr(s, &saved);
    flags_row("A8.1 a pty as made:", s);
    client_raw(s);
    flags_row("A8.1 a pty raw:", s);
    tcsetattr(s, TCSANOW, &saved);
    tcgetattr(s, &back);
    say("A8.1 a pty put back: %s\n", tdiff(&saved, &back));
    close(s);
    close(m);
    /* a client killed by SIGKILL leaves its terminal raw; the master's holder puts it back */
    char *rk[] = {"/bin/muxprobe", "rawkill", 0};
    int k = pane_start(rk, 0, 1);
    NEED(k, "A8.2");
    struct termios before = saved; /* a new pty's settings: what the client found */
    until(k, "raw: set", 3000);
    kill(P[k].pid, SIGKILL);
    const char *end = pane_settle(k, 3000);
    struct termios after;
    tcgetattr(P[k].m, &after);
    int still = !(after.c_lflag & ICANON) && !(after.c_lflag & ECHO);
    say("A8.2 a client in raw mode %s: its terminal is %s\n", end, still ? "still raw (nobody restores it)" : "cooked again");
    tcsetattr(P[k].m, TCSANOW, &before);
    tcgetattr(P[k].m, &after);
    say("A8.2 the master's holder puts it back from the master: %s\n",
        (after.c_lflag & ICANON) && (after.c_lflag & ECHO) && (after.c_iflag & ICRNL) && (after.c_oflag & OPOST) ? "cooked" : "NOT cooked");
    close(P[k].m);
    P[k].m = -1;
    /* the console (on Linux: the pseudo-terminal the container types on) */
    if (tcgetattr(0, &saved) == 0) {
        flags_row("A8.3 the console as found:", 0);
        client_raw(0);
        flags_row("A8.3 the console raw:", 0);
        tcsetattr(0, TCSANOW, &saved);
        tcgetattr(0, &back);
        say("A8.3 the console put back: %s\n", tdiff(&saved, &back));
    } else {
        say("A8.3 the console: %s\n", ename(errno));
    }
    fflush(stdout);
}

/* --- the end of the panes --------------------------------------------------- */

static void close_all(void) {
    int open_ = 0;
    for (int k = 0; k < np; k++) if (P[k].m >= 0) { close(P[k].m); P[k].m = -1; open_++; }
    int hup = 0, other_ = 0, left = 0;
    char odd[256] = "";
    long end = now_ms() + 5000;
    for (int k = 0; k < np; k++) {
        int st;
        pid_t w;
        if (P[k].reaped) continue;
        if (!P[k].shell) { kill(P[k].pid, SIGKILL); waitpid(P[k].pid, &st, 0); P[k].reaped = 1; continue; }
        for (;;) {
            w = waitpid(P[k].pid, &st, WNOHANG);
            if (w != 0 || now_ms() >= end) break;
            nap(10);
        }
        if (w == P[k].pid) P[k].reaped = 1;
        if (w == P[k].pid && WIFSIGNALED(st) && WTERMSIG(st) == SIGHUP) hup++;
        else if (w == P[k].pid) { other_++; if (strlen(odd) < 200) { strcat(odd, " "); strcat(odd, how(w, st)); } }
        else if (w == 0) { left++; kill(P[k].pid, SIGKILL); waitpid(P[k].pid, &st, 0); }
    }
    say("A1.8 %d masters closed: %d shells ended by SIGHUP, %d otherwise, %d left running\n", open_, hup, other_, left);
    if (other_) say("~A1.8 the other ends:%s\n", odd);
    int nr = pty_nr();
    say("~A1.8 the pty count moved by %d (%d at the start; Linux's counts every pty on the host)\n", nr - nr0, nr0);
}

/* --- the console's own modes: B5's keys, B7's paint ---------------------------- */

static int mode_keys(void) {
    struct termios saved;
    tcgetattr(0, &saved);
    raw_fd(0);
    puts_fd(1, "keys: ready\r\n");
    for (;;) {
        unsigned char b[64];
        ssize_t n = read(0, b, sizeof b);
        if (n <= 0) break;
        if (n == 1 && b[0] == 'Q') break;
        char line[512];
        int k = snprintf(line, sizeof line, "key");
        for (ssize_t i = 0; i < n && k < (int)sizeof line - 8; i++) k += snprintf(line + k, sizeof line - (size_t)k, " %02x", b[i]);
        snprintf(line + k, sizeof line - (size_t)k, "\r\n");
        puts_fd(1, line);
    }
    tcsetattr(0, TCSANOW, &saved);
    puts_fd(1, "keys: done\r\n");
    return 0;
}

/* Full screens of the console's grid, each cell a CUP and a character
 * (the worst a renderer sends), as one run a row, and with a colour
 * change every cell; the time of each from the monotonic clock. */
static int mode_paint(int reps) {
    struct winsize w;
    if (ioctl(1, TIOCGWINSZ, &w) != 0 || w.ws_row == 0) { puts_fd(1, "paint: no size\r\n"); return 1; }
    int R = w.ws_row, C = w.ws_col;
    size_t cap = (size_t)R * (size_t)C * 24 + 64;
    char *b = malloc(cap);
    long res[3];
    /* one cell a write, a thousand writes: what one write costs */
    long w0 = now_ms();
    for (int i = 0; i < 1000; i++) {
        char one[32];
        int n1 = snprintf(one, sizeof one, "\033[%d;%dH%c", 1 + i % R, 1 + (i * 7) % (C - 1), 'a' + i % 26);
        (void)putall(1, one, (size_t)n1);
    }
    long w1 = now_ms() - w0;
    for (int way = 0; way < 3; way++) {
        long t0 = now_ms();
        for (int rep_ = 0; rep_ < reps; rep_++) {
            size_t n = 0;
            char ch = (char)('A' + (rep_ + way) % 26);
            for (int r = 1; r <= R; r++) {
                if (way == 1) n += (size_t)snprintf(b + n, cap - n, "\033[%d;1H", r);
                for (int c = 1; c <= C; c++) {
                    if (r == R && c == C) break; /* the last cell would scroll */
                    if (way == 0) n += (size_t)snprintf(b + n, cap - n, "\033[%d;%dH%c", r, c, ch);
                    else if (way == 1) b[n++] = ch;
                    else n += (size_t)snprintf(b + n, cap - n, "\033[3%dm%c", (r + c) % 8, ch);
                }
                if (way == 2 && r < R) n += (size_t)snprintf(b + n, cap - n, "\r\n");
            }
            if (way == 2) n += (size_t)snprintf(b + n, cap - n, "\033[0m\033[H");
            (void)putall(1, b, n);
        }
        res[way] = now_ms() - t0;
    }
    char line[256];
    snprintf(line, sizeof line, "\033[0m\033[2J\033[Hpaint: %d x %d, %d screens each: cells %ld ms, runs %ld ms, coloured %ld ms; 1000 one-cell writes %ld ms\r\n", C, R,
             reps, res[0], res[1], res[2], w1);
    puts_fd(1, line);
    free(b);
    return 0;
}

/* --- main ---------------------------------------------------------------------- */

int main(int argc, char **argv) {
    setvbuf(stdout, 0, _IOLBF, 0);
    if (argc > 1) {
        if (strcmp(argv[1], "flood") == 0) return mode_flood(argc > 2 ? atol(argv[2]) : FLOOD_BYTES);
        if (strcmp(argv[1], "spew") == 0) return mode_spew();
        if (strcmp(argv[1], "pane") == 0) return mode_pane();
        if (strcmp(argv[1], "hold") == 0) return mode_hold();
        if (strcmp(argv[1], "winch") == 0) return mode_winch();
        if (strcmp(argv[1], "relay") == 0) return mode_relay();
        if (strcmp(argv[1], "sig") == 0) return mode_sig();
        if (strcmp(argv[1], "rawkill") == 0) return mode_rawkill();
        if (strcmp(argv[1], "keys") == 0) return mode_keys();
        if (strcmp(argv[1], "paint") == 0) return mode_paint(argc > 2 ? atoi(argv[2]) : 10);
        fprintf(stderr, "muxprobe: no mode %s\n", argv[1]);
        return 2;
    }
    signal(SIGPIPE, SIG_IGN);
    say("muxprobe: px125's probe, as %s, %s\n", geteuid() == 0 ? "root" : "a user", getpid() == 1 ? "init" : "NOT init");
    if (getpid() != 1) prctl(PR_SET_CHILD_SUBREAPER, 1); /* the shape init has, for A5 */
    if (pipe2(rep, O_CLOEXEC) < 0) return 2;
    fcntl(rep[0], F_SETFL, O_NONBLOCK);
    ep = epoll_create1(EPOLL_CLOEXEC);
    if (ep < 0) { say("A1 epoll_create1: %s\n", ename(errno)); return 1; }
    sec_a10();
    sec_a1();
    sec_a6_clients(PANES / 2);
    sec_a2(PANES / 2);
    sec_a3();
    sec_a4();
    close_all();
    sec_a19();
    sec_a5();
    sec_a6();
    sec_a7();
    sec_a8();
    leave_daemon();
    return 0;
}
