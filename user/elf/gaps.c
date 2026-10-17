/* px49: the small gaps, asked of the kernel — pause (pax#73),
 * rt_sigsuspend across a stop and when another thread takes the signal
 * (pax#75), TIOCSTI, TCFLSH and TCSBRK on the terminal (pax#74), the
 * background rule for sendfile and splice to the terminal under TOSTOP
 * (pax#76), fstat's owner of an AF_INET datagram socket, a TCP socket,
 * an accepted end, an eventfd and an epoll object (pax#58),
 * faccessat2's AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH (pax#60),
 * fallocate's modes on a regular file (pax#63), and unlink of /dev,
 * /proc and /sys (pax#70: root's rows; a user's are tests/mpx3-tree's,
 * where `/` is root's 0755 on both sides). Run as the first program on
 * a terminal (PAX's console; a Linux pseudo-terminal as its session
 * leader, notes/px49's guest and tools/linux-tree), as root and as a
 * user (through `as`), with /g a 1777 directory and /g/r644 and
 * /g/r600 root's files of those modes in the archive.
 *
 * Every line is `case: answer`; no pid, time or address is printed. The
 * program (`main`) keeps its terminal and its group in the foreground;
 * every child it asks things of is put in a group of its own (so a
 * stop at its default is not discarded: the child's parent is in the
 * same session and another group) and tells main what it saw through a
 * pipe. It writes the prompt `$ ` once and waits for one line typed
 * (user/console/gaps.keys: `zap`), which TCFLSH then discards.
 *
 *   gaps            every section, P U I B O A F D
 *
 * Written from POSIX.1-2024 (XSH pause, sigsuspend, tcflush, tcdrain,
 * tcsendbreak, faccessat, unlink; XBD 11.1.4) and the man pages
 * (pause(2), sigsuspend(2), signal(7), ioctl_tty(2), TIOCSTI(2const),
 * TCFLSH(2const), TCSBRK(2const), termios(3), sendfile(2), splice(2),
 * fallocate(2), access(2), unlink(2), stat(2), socket(7), eventfd(2),
 * epoll_create(2), accept(2), setfsuid(2), credentials(7)); the uapi
 * headers' numbers (linux/falloc.h, asm-generic/ioctls.h,
 * linux/fcntl.h). No C library's, kernel's or terminal driver's source
 * was read. Written for this lane. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <sys/fsuid.h>
#include <sys/ioctl.h>
#include <sys/sendfile.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static int rep[2]; /* what children report: one line each */
static int root;

static const char *sname(int s) {
    switch (s) {
    case SIGHUP: return "HUP"; case SIGINT: return "INT"; case SIGUSR1: return "USR1"; case SIGUSR2: return "USR2";
    case SIGTERM: return "TERM"; case SIGCHLD: return "CHLD"; case SIGCONT: return "CONT"; case SIGSTOP: return "STOP";
    case SIGTSTP: return "TSTP"; case SIGTTIN: return "TTIN"; case SIGTTOU: return "TTOU"; case SIGKILL: return "KILL";
    case SIGURG: return "URG";
    default: return "?";
    }
}

static const char *ename(int e) {
    switch (e) {
    case 0: return "0";
    case EPERM: return "EPERM"; case ENOENT: return "ENOENT"; case ESRCH: return "ESRCH"; case EINTR: return "EINTR";
    case EIO: return "EIO"; case EBADF: return "EBADF"; case EAGAIN: return "EAGAIN"; case EACCES: return "EACCES";
    case EISDIR: return "EISDIR"; case EINVAL: return "EINVAL"; case ENOTTY: return "ENOTTY"; case ESPIPE: return "ESPIPE";
    case EOPNOTSUPP: return "EOPNOTSUPP"; case ENODEV: return "ENODEV"; case EBUSY: return "EBUSY"; case EROFS: return "EROFS";
    case ENOSYS: return "ENOSYS"; case EFBIG: return "EFBIG"; case ENOTDIR: return "ENOTDIR"; case EFAULT: return "EFAULT";
    default: { static char b[32]; snprintf(b, sizeof b, "errno%d", e); return b; }
    }
}

static const char *rc(long r) { return r < 0 ? ename(errno) : "0"; }
/* The answer of a call whose errno was kept at once (`e`): a printf
 * that calls something else too must not read errno after it. */
static const char *rc_e(long r, int e) { return r < 0 ? ename(e) : "0"; }

static long now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void nap(int ms) {
    struct timespec ts = {ms / 1000, (long)(ms % 1000) * 1000000L};
    while (nanosleep(&ts, &ts) < 0 && errno == EINTR) {}
}

static const char *yesno(int c) { return c ? "yes" : "no"; }

/* A child's report line (no newline). */
static void say(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void say(const char *fmt, ...) {
    char b[160];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b - 1, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n > (int)sizeof b - 2) n = (int)sizeof b - 2;
    b[n++] = '\n';
    (void)!write(rep[1], b, (size_t)n);
}

/* The reports that came within `ms` (or as soon as `want` lines came),
 * joined with "; ", or "-" for none. */
static const char *reports(int want, int ms) {
    static char out[1024];
    char buf[1024];
    size_t len = 0;
    long end = now_ms() + ms;
    for (;;) {
        ssize_t r = read(rep[0], buf + len, sizeof buf - 1 - len);
        if (r > 0) { len += (size_t)r; continue; }
        int lines = 0;
        for (size_t i = 0; i < len; i++) if (buf[i] == '\n') lines++;
        if ((want > 0 && lines >= want) || now_ms() >= end) break;
        nap(10);
    }
    buf[len] = 0;
    out[0] = 0;
    size_t k = 0;
    int m = 0;
    for (char *s = strtok(buf, "\n"); s; s = strtok(NULL, "\n"))
        k += (size_t)snprintf(out + k, sizeof out > k ? sizeof out - k : 0, "%s%s", m++ ? "; " : "", s);
    if (!m) snprintf(out, sizeof out, "-");
    return out;
}

/* How a waited-for child changed. */
static const char *how(pid_t w, int st) {
    static char b[64];
    if (w == 0) return "nothing new";
    if (w < 0) return ename(errno);
    if (WIFSTOPPED(st)) snprintf(b, sizeof b, "stopped by %s", sname(WSTOPSIG(st)));
    else if (WIFCONTINUED(st)) snprintf(b, sizeof b, "continued");
    else if (WIFEXITED(st)) snprintf(b, sizeof b, "exited %d", WEXITSTATUS(st));
    else if (WIFSIGNALED(st)) snprintf(b, sizeof b, "killed by %s", sname(WTERMSIG(st)));
    else snprintf(b, sizeof b, "status 0x%x", st);
    return b;
}

/* waitpid with `fl`, giving up (nothing new) after `ms`. */
static const char *wait_for(pid_t p, int fl, int ms) {
    int st = 0;
    long end = now_ms() + ms;
    for (;;) {
        pid_t w = waitpid(p, &st, fl | WNOHANG);
        if (w != 0 || now_ms() >= end) return how(w, st);
        nap(10);
    }
}

static volatile sig_atomic_t handled;
static void on_usr1(int s) { (void)s; handled++; }

static void handle(int sig, void (*fn)(int), int flags) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = fn;
    sa.sa_flags = flags;
    sigemptyset(&sa.sa_mask);
    sigaction(sig, &sa, 0);
}

static void block(int sig, int how_) {
    sigset_t s;
    sigemptyset(&s);
    sigaddset(&s, sig);
    sigprocmask(how_, &s, 0);
}

/* A child in a group of its own (made on both sides, so neither races
 * the other), its signal actions back at their defaults; `ready` gets a
 * byte once it has run `fn` up to its first report point. */
static pid_t child(void (*fn)(void)) {
    pid_t p = fork();
    if (p == 0) {
        setpgid(0, 0);
        static const int reset[] = {SIGHUP, SIGINT, SIGUSR1, SIGUSR2, SIGCONT, SIGTSTP, SIGTTIN, SIGTTOU, SIGCHLD, SIGURG, 0};
        for (const int *q = reset; *q; q++) signal(*q, SIG_DFL);
        sigset_t none;
        sigemptyset(&none);
        sigprocmask(SIG_SETMASK, &none, 0);
        fn();
        _exit(0);
    }
    setpgid(p, p);
    return p;
}

static void reap(pid_t p) { kill(p, SIGKILL); waitpid(p, 0, 0); }

/* ---- P: pause (pax#73) ---------------------------------------------- */

static void pauser(void) {
    handle(SIGUSR1, on_usr1, 0);
    signal(SIGUSR2, SIG_IGN);
    say("ready");
    for (;;) {
        int h = handled;
        long r = syscall(SYS_pause);
        int e = errno;
        say("pause returned %s, %s", r < 0 ? ename(e) : "0", handled > h ? "after its handler" : "with no handler run");
        if (r < 0 && e == ENOSYS) nap(1000); /* a kernel without pause: one report a second, not a flood */
    }
}

static void pause_rows(void) {
    pid_t p = child(pauser);
    printf("P: the child is ready: %s\n", reports(1, 3000));
    kill(p, SIGCHLD);
    printf("P: SIGCHLD at its default: %s\n", reports(1, 500));
    kill(p, SIGURG);
    printf("P: SIGURG at its default: %s\n", reports(1, 500));
    kill(p, SIGCONT);
    printf("P: SIGCONT to a running child: %s\n", reports(1, 500));
    kill(p, SIGUSR2);
    printf("P: SIGUSR2 ignored: %s\n", reports(1, 500));
    kill(p, SIGSTOP);
    printf("P: SIGSTOP: %s\n", wait_for(p, WUNTRACED, 3000));
    kill(p, SIGCONT);
    printf("P: SIGCONT: %s; the child said %s\n", wait_for(p, WCONTINUED, 3000), reports(1, 500));
    kill(p, SIGUSR1);
    printf("P: SIGUSR1 with a handler: %s\n", reports(1, 3000));
    kill(p, SIGUSR1);
    printf("P: SIGUSR1 again: %s\n", reports(1, 3000));
    kill(p, SIGKILL);
    printf("P: SIGKILL: %s\n", wait_for(p, 0, 3000));
}

/* ---- U: rt_sigsuspend (pax#75) -------------------------------------- */

static void suspender(void) {
    handle(SIGUSR1, on_usr1, 0);
    block(SIGUSR1, SIG_BLOCK);
    say("ready");
    sigset_t none;
    sigemptyset(&none);
    for (;;) {
        int h = handled;
        int r = sigsuspend(&none);
        int e = errno;
        say("sigsuspend returned %s, %s", r < 0 ? ename(e) : "0", handled > h ? "after its handler" : "with no handler run");
    }
}

/* A SIGTSTP blocked and pending at its default when sigsuspend unblocks it. */
static void stop_suspender(void) {
    handle(SIGUSR1, on_usr1, 0);
    block(SIGUSR1, SIG_BLOCK);
    block(SIGTSTP, SIG_BLOCK);
    kill(getpid(), SIGTSTP);
    sigset_t p;
    sigpending(&p);
    say("ready, SIGTSTP pending %s", yesno(sigismember(&p, SIGTSTP)));
    sigset_t none;
    sigemptyset(&none);
    for (;;) {
        int h = handled;
        int r = sigsuspend(&none);
        int e = errno;
        say("sigsuspend returned %s, %s", r < 0 ? ename(e) : "0", handled > h ? "after its handler" : "with no handler run");
    }
}

/* Two threads: the main thread B and A, which waits in sigsuspend. */
static __thread int mine;   /* handlers run in this thread */
static volatile int a_wait, a_bad, a_ret, total;
static void on_usr1_t(int s) { (void)s; mine++; __sync_fetch_and_add(&total, 1); }

static void *thread_a(void *x) {
    (void)x;
    sigset_t none;
    sigemptyset(&none);
    for (;;) {
        int h = mine;
        a_wait = 1;
        sigsuspend(&none);
        a_wait = 0;
        a_ret++;
        if (mine == h) a_bad++;
    }
    return 0;
}

static void two_threads(void) {
    handle(SIGUSR1, on_usr1_t, 0);
    block(SIGUSR1, SIG_BLOCK);
    pthread_t a;
    pthread_create(&a, 0, thread_a, 0);
    long end = now_ms() + 3000;
    while (!a_wait && now_ms() < end) nap(5);
    nap(50);
    const int n = 20;
    for (int i = 0; i < n; i++) {
        /* B sends the process a signal it blocks and then unblocks it:
         * B or A takes it, whichever does first. */
        block(SIGUSR1, SIG_BLOCK);
        kill(getpid(), SIGUSR1);
        block(SIGUSR1, SIG_UNBLOCK);
        end = now_ms() + 2000;
        while (total < i + 1 && now_ms() < end) nap(2);
        end = now_ms() + 2000;
        while (!a_wait && now_ms() < end) nap(2);
        nap(20);
    }
    say("%d signals sent, each handled once %s; A left sigsuspend without its own handler %d times; A waits at the end %s",
        n, yesno(total == n), a_bad, yesno(a_wait));
    /* A thread-directed signal to B while A waits: A keeps waiting. */
    int ret = a_ret;
    block(SIGUSR1, SIG_UNBLOCK);
    syscall(SYS_tgkill, getpid(), syscall(SYS_gettid), SIGUSR1);
    nap(200);
    say("tgkill to B: B's handler ran %s; A left sigsuspend %d times", yesno(total == n + 1), a_ret - ret);
}

static void suspend_rows(void) {
    pid_t p = child(suspender);
    printf("U: the child is ready: %s\n", reports(1, 3000));
    kill(p, SIGSTOP);
    printf("U: SIGSTOP to a child in sigsuspend: %s\n", wait_for(p, WUNTRACED, 3000));
    kill(p, SIGCONT);
    printf("U: SIGCONT: %s; the child said %s\n", wait_for(p, WCONTINUED, 3000), reports(1, 500));
    kill(p, SIGUSR1);
    printf("U: SIGUSR1 with a handler: %s\n", reports(1, 3000));
    reap(p);

    p = child(stop_suspender);
    printf("U: a second child, SIGTSTP blocked and sent to itself: %s\n", reports(1, 3000));
    printf("U: sigsuspend unblocks the SIGTSTP at its default: %s\n", wait_for(p, WUNTRACED, 3000));
    kill(p, SIGCONT);
    printf("U: SIGCONT: %s; the child said %s\n", wait_for(p, WCONTINUED, 3000), reports(1, 500));
    kill(p, SIGUSR1);
    printf("U: SIGUSR1 with a handler: %s\n", reports(1, 3000));
    reap(p);

    p = child(two_threads);
    printf("U: two threads, a process signal: %s\n", reports(1, 20000));
    printf("U: %s\n", reports(1, 3000));
    reap(p);
}

/* ---- I: TIOCSTI, TCFLSH, TCSBRK (pax#74) ------------------------------ */

static struct termios saved;

static void raw_input(void) {
    struct termios t = saved;
    t.c_lflag &= ~(tcflag_t)(ICANON | ECHO);
    t.c_cc[VMIN] = 0;
    t.c_cc[VTIME] = 0;
    tcsetattr(0, TCSANOW, &t);
}

static const char *read_now(void) {
    static char b[64];
    char c[16];
    errno = 0;
    ssize_t n = read(0, c, sizeof c);
    if (n < 0) snprintf(b, sizeof b, "%s", ename(errno));
    else if (n == 0) snprintf(b, sizeof b, "0 bytes");
    else {
        int k = snprintf(b, sizeof b, "%zd bytes \"", n);
        for (ssize_t i = 0; i < n && k < 56; i++)
            k += c[i] >= 32 && c[i] < 127 ? snprintf(b + k, sizeof b - (size_t)k, "%c", c[i]) : snprintf(b + k, sizeof b - (size_t)k, "\\%03o", (unsigned char)c[i]);
        snprintf(b + k, sizeof b - (size_t)k, "\"");
    }
    return b;
}

static int bg_op; /* which call the background child makes */

static void bg_caller(void) {
    errno = 0;
    long r = 0;
    switch (bg_op) {
    case 0: r = ioctl(0, TCFLSH, TCIFLUSH); break;
    case 1: r = ioctl(0, TCSBRK, 1); break;
    case 2: r = ioctl(0, TCSBRK, 0); break;
    case 3: signal(SIGTTOU, SIG_IGN); r = ioctl(0, TCFLSH, TCIFLUSH); break;
    case 4: signal(SIGTTOU, SIG_IGN); r = ioctl(0, TCSBRK, 1); break;
    }
    say("its call answered %s", rc(r));
}

static void bg_row(const char *what, int op) {
    bg_op = op;
    pid_t p = child(bg_caller);
    const char *w = wait_for(p, WUNTRACED, 3000);
    char first[64];
    snprintf(first, sizeof first, "%s", w);
    if (strncmp(first, "stopped", 7) == 0) {
        kill(p, SIGCONT);
        (void)wait_for(p, WCONTINUED, 3000);
        const char *again = wait_for(p, WUNTRACED, 3000);
        printf("I: %s from a background group: %s; continued in the background: %s\n", what, first, again);
        reap(p);
        (void)reports(0, 100);
        return;
    }
    printf("I: %s from a background group: %s, %s\n", what, reports(1, 1000), first);
}

/* A child that makes a session of its own (so the terminal is not its
 * controlling terminal) and puts a byte in the terminal's input. */
static pid_t sti_child(void) {
    pid_t p = fork();
    if (p == 0) {
        setsid();
        char c = 'w';
        errno = 0;
        long r = ioctl(0, TIOCSTI, &c);
        say("TIOCSTI by a process of another session (not its terminal): %s", rc(r));
        _exit(0);
    }
    return p;
}

static void ioctl_rows(void) {
    tcgetattr(0, &saved);
    /* TCFLSH: what was typed and not read is discarded. */
    printf("I: type a line\n$ ");
    fflush(stdout);
    nap(4000);
    errno = 0;
    printf("I: TCFLSH(TCIFLUSH) with a typed line unread: %s\n", rc(ioctl(0, TCFLSH, TCIFLUSH)));
    raw_input();
    printf("I: a read after it: %s\n", read_now());
    /* An output flush discards what the terminal's reader has not taken
     * yet (seen in a container: lines lost): wait for it to take all. */
    nap(1500);
    errno = 0;
    long o1 = ioctl(0, TCFLSH, TCOFLUSH);
    int e1 = errno;
    nap(1500);
    errno = 0;
    long o2 = ioctl(0, TCFLSH, TCIOFLUSH);
    int e2 = errno;
    printf("I: TCFLSH(TCOFLUSH): %s; TCFLSH(TCIOFLUSH): %s\n", o1 < 0 ? ename(e1) : "0", o2 < 0 ? ename(e2) : "0");
    errno = 0;
    printf("I: TCFLSH(3): %s\n", rc(ioctl(0, TCFLSH, 3)));
    errno = 0;
    printf("I: tcflush(TCIFLUSH): %s\n", rc(tcflush(0, TCIFLUSH)));
    /* TIOCSTI: a byte put in the input as if typed. */
    char c = 'q';
    errno = 0;
    long r = ioctl(0, TIOCSTI, &c);
    int e = errno;
    char got[64];
    snprintf(got, sizeof got, "%s", read_now());
    printf("I: TIOCSTI 'q' on its own terminal: %s; a read then: %s\n", rc_e(r, e), got);
    errno = 0;
    r = ioctl(0, TIOCSTI, (char *)0);
    printf("I: TIOCSTI with a bad pointer: %s\n", rc(r));
    pid_t p = sti_child();
    (void)wait_for(p, 0, 3000);
    printf("I: %s; a read then: %s\n", reports(1, 1000), read_now());
    tcsetattr(0, TCSANOW, &saved);
    /* TCSBRK: tcdrain (arg non-zero) and tcsendbreak (arg 0). */
    errno = 0;
    printf("I: TCSBRK(1), tcdrain: %s\n", rc(ioctl(0, TCSBRK, 1)));
    errno = 0;
    printf("I: tcdrain(): %s\n", rc(tcdrain(0)));
    errno = 0;
    long t0 = now_ms();
    r = ioctl(0, TCSBRK, 0);
    long dt = now_ms() - t0;
    (void)dt; /* a pseudo-terminal answers at once (measured); not printed: a time */
    printf("I: TCSBRK(0), a break: %s\n", rc(r));
    errno = 0;
    printf("I: tcsendbreak(0): %s\n", rc(tcsendbreak(0, 0)));
    bg_row("TCFLSH(TCIFLUSH)", 0);
    bg_row("TCSBRK(1)", 1);
    bg_row("TCSBRK(0)", 2);
    bg_row("TCFLSH(TCIFLUSH) with SIGTTOU ignored", 3);
    bg_row("TCSBRK(1) with SIGTTOU ignored", 4);
}

/* ---- B: sendfile and splice to the terminal from the background (pax#76) */

static int bw_op; /* 0 sendfile, 1 splice; +2 SIGTTOU ignored */

static void bg_writer(void) {
    if (bw_op >= 2) signal(SIGTTOU, SIG_IGN);
    errno = 0;
    long r;
    if (bw_op % 2 == 0) {
        int f = open("/g/sf", O_RDONLY);
        r = sendfile(1, f, 0, 64);
        say("sendfile answered %s", r < 0 ? ename(errno) : r == 0 ? "0" : "its count");
    } else {
        int q[2];
        (void)!pipe(q);
        (void)!write(q[1], "B: the splice reached the terminal\n", 35);
        r = splice(q[0], 0, 1, 0, 64, 0);
        say("splice answered %s", r < 0 ? ename(errno) : r == 0 ? "0" : "its count");
    }
}

static void bw_row(const char *what, int op) {
    bw_op = op;
    pid_t p = child(bg_writer);
    const char *w = wait_for(p, WUNTRACED, 3000);
    char first[64];
    snprintf(first, sizeof first, "%s", w);
    if (strncmp(first, "stopped", 7) != 0) {
        printf("B: %s: %s, %s\n", what, reports(1, 1000), first);
        return;
    }
    kill(p, SIGCONT);
    (void)wait_for(p, WCONTINUED, 3000);
    char again[64];
    snprintf(again, sizeof again, "%s", wait_for(p, WUNTRACED, 3000));
    printf("B: %s: %s; continued in the background: %s\n", what, first, again);
    /* In the foreground it writes. */
    signal(SIGTTOU, SIG_IGN);
    tcsetpgrp(0, p);
    kill(p, SIGCONT);
    (void)wait_for(p, WCONTINUED, 3000);
    const char *end = wait_for(p, 0, 3000);
    tcsetpgrp(0, getpgrp());
    signal(SIGTTOU, SIG_DFL);
    printf("B: %s, given the foreground and continued: %s, %s\n", what, reports(1, 1000), end);
}

static void background_rows(void) {
    struct termios t;
    tcgetattr(0, &t);
    bw_row("sendfile without TOSTOP", 0);
    bw_row("splice without TOSTOP", 1);
    t.c_lflag |= TOSTOP;
    tcsetattr(0, TCSANOW, &t);
    bw_row("sendfile under TOSTOP", 0);
    bw_row("splice under TOSTOP", 1);
    bw_row("sendfile under TOSTOP, SIGTTOU ignored", 2);
    bw_row("splice under TOSTOP, SIGTTOU ignored", 3);
    t.c_lflag &= ~(tcflag_t)TOSTOP;
    tcsetattr(0, TCSANOW, &t);
}

/* ---- O: fstat's owner (pax#58) --------------------------------------- */

static const char *owner(int fd, unsigned u, unsigned g) {
    static char b[96];
    struct stat s;
    if (fstat(fd, &s) < 0) { snprintf(b, sizeof b, "fstat %s", ename(errno)); return b; }
    if (s.st_uid != u || s.st_gid != g) {
        /* An anonymous inode is the kernel's: 0:0 on real root's Linux,
         * the overflow id 65534 in a user namespace that does not map
         * the host's root (the container): its number is not printed. */
        snprintf(b, sizeof b, "not the maker's file-system ids");
        return b;
    }
    const char *rel = s.st_uid == u && s.st_gid == g ? "the maker's file-system ids" : s.st_uid == 0 && s.st_gid == 0 ? "0:0" : "other";
    snprintf(b, sizeof b, "%u:%u (%s)", (unsigned)s.st_uid, (unsigned)s.st_gid, rel);
    return b;
}

/* Run `make` under file-system ids u:g (root only: a user's are its own). */
static unsigned fu, fg;
static void as_fs(unsigned u, unsigned g) {
    if (root) { setfsgid(g); setfsuid(u); }
    fu = root ? u : getuid();
    fg = root ? g : getgid();
}
static void fs_back(void) { if (root) { setfsuid(0); setfsgid(0); } }

static void owner_rows(void) {
    as_fs(1001, 2001);
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    int t = socket(AF_INET, SOCK_STREAM, 0);
    int e = eventfd(0, 0);
    int p = epoll_create1(0);
    int pr[2];
    (void)!pipe(pr);
    fs_back();
    printf("O: an AF_INET datagram socket: %s\n", u < 0 ? ename(errno) : owner(u, fu, fg));
    printf("O: a TCP socket: %s\n", t < 0 ? ename(errno) : owner(t, fu, fg));
    printf("O: an eventfd: %s\n", owner(e, fu, fg));
    printf("O: an epoll object: %s\n", owner(p, fu, fg));
    printf("O: a pipe (px43's): %s\n", owner(pr[0], fu, fg));
    close(u); close(t); close(e); close(p); close(pr[0]); close(pr[1]);

    /* A listener made under 1001, a client under 1002, the accept under 1003. */
    as_fs(1001, 2001);
    int l = socket(AF_INET, SOCK_STREAM, 0);
    fs_back();
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(0x7f000001);
    a.sin_port = htons(4949);
    int one = 1;
    setsockopt(l, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    errno = 0;
    long b = bind(l, (struct sockaddr *)&a, sizeof a);
    int eb = errno;
    errno = 0;
    long li = listen(l, 1);
    int el = errno;
    printf("O: a listener bound to 127.0.0.1:4949: %s, listen %s\n", rc_e(b, eb), rc_e(li, el));
    as_fs(1002, 2002);
    int c = socket(AF_INET, SOCK_STREAM, 0);
    unsigned cu = fu, cg = fg;
    fs_back();
    errno = 0;
    long cr = connect(c, (struct sockaddr *)&a, sizeof a);
    int ec = errno;
    as_fs(1003, 2003);
    errno = 0;
    int k = cr < 0 ? -1 : accept(l, 0, 0);
    int ek = cr < 0 ? ec : errno;
    unsigned ku = fu, kg = fg;
    fs_back();
    printf("O: connect %s; the client end: %s\n", rc_e(cr, ec), owner(c, cu, cg));
    printf("O: the end accept made: %s\n", k < 0 ? ename(ek) : owner(k, ku, kg));
    close(k); close(c); close(l);
}

/* ---- A: faccessat2's flags (pax#60) ----------------------------------- */

#ifndef AT_EACCESS
#define AT_EACCESS 0x200
#endif
static long fa2(int dfd, const char *path, int mode, int flags) {
    return syscall(SYS_faccessat2, dfd, path, mode, flags);
}
#define FA(name, expr) do { errno = 0; long r_ = (expr); printf("A: %s: %s\n", name, rc(r_)); } while (0)

static void access_rows(void) {
    unlink("/g/lnk"); unlink("/g/dang");
    errno = 0;
    long s1 = symlink("/g/r600", "/g/lnk");
    int e1 = errno;
    errno = 0;
    long s2 = symlink("/g/none", "/g/dang");
    int e2 = errno;
    printf("A: a link to root's 0600 file and a dangling link made: %s, %s\n", rc_e(s1, e1), rc_e(s2, e2));
    FA("R_OK through the link", fa2(AT_FDCWD, "/g/lnk", R_OK, 0));
    FA("R_OK of the link, AT_SYMLINK_NOFOLLOW", fa2(AT_FDCWD, "/g/lnk", R_OK, AT_SYMLINK_NOFOLLOW));
    FA("W_OK of the link, AT_SYMLINK_NOFOLLOW", fa2(AT_FDCWD, "/g/lnk", W_OK, AT_SYMLINK_NOFOLLOW));
    FA("X_OK of the link, AT_SYMLINK_NOFOLLOW", fa2(AT_FDCWD, "/g/lnk", X_OK, AT_SYMLINK_NOFOLLOW));
    FA("X_OK of the link, AT_SYMLINK_NOFOLLOW|AT_EACCESS", fa2(AT_FDCWD, "/g/lnk", X_OK, AT_SYMLINK_NOFOLLOW | AT_EACCESS));
    FA("F_OK of the dangling link", fa2(AT_FDCWD, "/g/dang", F_OK, 0));
    FA("F_OK of the dangling link, AT_SYMLINK_NOFOLLOW", fa2(AT_FDCWD, "/g/dang", F_OK, AT_SYMLINK_NOFOLLOW));
    FA("R_OK of a file, AT_SYMLINK_NOFOLLOW", fa2(AT_FDCWD, "/g/r600", R_OK, AT_SYMLINK_NOFOLLOW));
    int f = open("/g/r644", O_RDONLY);
    int d = open("/g", O_RDONLY | O_DIRECTORY);
    FA("W_OK of root's 0644 file by its descriptor, AT_EMPTY_PATH", fa2(f, "", W_OK, AT_EMPTY_PATH));
    FA("R_OK of root's 0644 file by its descriptor, AT_EMPTY_PATH", fa2(f, "", R_OK, AT_EMPTY_PATH));
    FA("R_OK, an empty path without AT_EMPTY_PATH", fa2(f, "", R_OK, 0));
    FA("W_OK of the 1777 directory, AT_EMPTY_PATH", fa2(d, "", W_OK, AT_EMPTY_PATH));
    errno = 0;
    long cd = chdir("/g");
    FA("W_OK of the working directory /g, AT_FDCWD and AT_EMPTY_PATH", cd < 0 ? cd : fa2(AT_FDCWD, "", W_OK, AT_EMPTY_PATH));
    (void)!chdir("/");
    FA("R_OK of a name in the directory, AT_EMPTY_PATH", fa2(d, "r600", R_OK, AT_EMPTY_PATH));
    FA("R_OK of a closed descriptor, AT_EMPTY_PATH", fa2(99, "", R_OK, AT_EMPTY_PATH));
    FA("the flag 0x2", fa2(AT_FDCWD, "/g/r644", R_OK, 0x2));
    close(f); close(d);
    unlink("/g/lnk"); unlink("/g/dang");
}

/* ---- F: fallocate's modes (pax#63) ------------------------------------ */

#define KEEP 0x01
#define PUNCH 0x02
#define COLLAPSE 0x08
#define ZERO 0x10
#define INSERT 0x20
#define UNSHARE 0x40

static const char *content(int fd) {
    static char b[96];
    char c[32];
    struct stat s;
    fstat(fd, &s);
    ssize_t n = pread(fd, c, sizeof c, 0);
    int k = snprintf(b, sizeof b, "size %lld \"", (long long)s.st_size);
    for (ssize_t i = 0; i < n && k < 88; i++)
        k += c[i] ? snprintf(b + k, sizeof b - (size_t)k, "%c", c[i]) : snprintf(b + k, sizeof b - (size_t)k, ".");
    snprintf(b + k, sizeof b - (size_t)k, "\" mode %04o", (unsigned)(s.st_mode & 07777));
    return b;
}

static int fresh(void) {
    unlink("/g/fa");
    int fd = open("/g/fa", O_RDWR | O_CREAT | O_TRUNC, 0644);
    (void)!write(fd, "abcdefghij", 10);
    fchmod(fd, 06755);
    return fd;
}

static void fa_row(const char *name, int mode, long off, long len) {
    int fd = fresh();
    errno = 0;
    long r = syscall(SYS_fallocate, fd, mode, off, len);
    int e = errno;
    printf("F: %s (0x%x, %ld, %ld): %s; %s\n", name, mode, off, len, rc_e(r, e), content(fd));
    close(fd);
}

static void fallocate_rows(void) {
    fa_row("mode 0", 0, 0, 20);
    fa_row("KEEP_SIZE", KEEP, 0, 100);
    fa_row("KEEP_SIZE past the end", KEEP, 20, 10);
    fa_row("PUNCH_HOLE|KEEP_SIZE", PUNCH | KEEP, 2, 3);
    fa_row("PUNCH_HOLE|KEEP_SIZE over the end", PUNCH | KEEP, 8, 10);
    fa_row("PUNCH_HOLE|KEEP_SIZE past the end", PUNCH | KEEP, 20, 10);
    fa_row("PUNCH_HOLE alone", PUNCH, 2, 3);
    fa_row("ZERO_RANGE", ZERO, 2, 3);
    fa_row("ZERO_RANGE|KEEP_SIZE", ZERO | KEEP, 2, 3);
    fa_row("COLLAPSE_RANGE", COLLAPSE, 0, 4096);
    fa_row("COLLAPSE_RANGE|KEEP_SIZE", COLLAPSE | KEEP, 0, 4096);
    fa_row("INSERT_RANGE", INSERT, 0, 4096);
    fa_row("INSERT_RANGE|KEEP_SIZE", INSERT | KEEP, 0, 4096);
    fa_row("UNSHARE_RANGE", UNSHARE, 0, 10);
    fa_row("PUNCH_HOLE|ZERO_RANGE|KEEP_SIZE", PUNCH | ZERO | KEEP, 2, 3);
    fa_row("the bit 0x100", 0x100, 0, 10);
    fa_row("KEEP_SIZE, length 0", KEEP, 0, 0);
    fa_row("PUNCH_HOLE|KEEP_SIZE, offset -1", PUNCH | KEEP, -1, 3);
    int q[2];
    (void)!pipe(q);
    errno = 0;
    printf("F: KEEP_SIZE on a pipe: %s\n", rc(syscall(SYS_fallocate, q[1], KEEP, 0, 10)));
    errno = 0;
    printf("F: PUNCH_HOLE|KEEP_SIZE on a pipe: %s\n", rc(syscall(SYS_fallocate, q[1], PUNCH | KEEP, 0, 10)));
    close(q[0]); close(q[1]);
    int ro = open("/g/r644", O_RDONLY);
    errno = 0;
    printf("F: KEEP_SIZE on a read-only descriptor: %s\n", rc(syscall(SYS_fallocate, ro, KEEP, 0, 10)));
    close(ro);
    unlink("/g/fa");
}

/* ---- D: unlink of /dev, /proc and /sys (pax#70) ------------------------- */

static void unlink_rows(void) {
    errno = 0; long a = unlink("/dev"); int ea = errno;
    errno = 0; long b = unlink("/proc"); int eb = errno;
    errno = 0; long c = unlink("/sys"); int ec = errno;
    printf("D: unlink of /dev %s, /proc %s, /sys %s\n", a < 0 ? ename(ea) : "0", b < 0 ? ename(eb) : "0", c < 0 ? ename(ec) : "0");
}

int main(void) {
    setvbuf(stdout, 0, _IOLBF, 0);
    if (pipe(rep) < 0) return 2;
    fcntl(rep[0], F_SETFL, O_NONBLOCK);
    root = geteuid() == 0;
    printf("gaps: px49's probe, as %s\n", root ? "root" : "a user");
    printf("main: leads its session, with the terminal in its group's hands: %s\n", yesno(getsid(0) == getpid() && tcgetpgrp(0) == getpgrp()));
    pause_rows();
    suspend_rows();
    ioctl_rows();
    background_rows();
    owner_rows();
    access_rows();
    fallocate_rows();
    if (root) unlink_rows();
    else printf("D: unlink of /dev, /proc and /sys: tests/mpx3-tree's (a user's `/` differs here: ruling #85)\n");
    printf("gaps: done\n");
    return 0;
}
