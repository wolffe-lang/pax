/* sudotty.c — px119: sudo's timestamp record made on a pseudo-terminal,
 * asked of PAX's sudo (user/sudo) from the master side. Run as root, as
 * the first program of tests/mpx5-sudo's `sudotty` image.
 *
 * Session A: a new pty, a child that starts a session on its slave as the
 * controlling terminal (setsid, TIOCSCTTY), becomes bob (1001:1001, a
 * password rule in tests/mpx5-sudo.d/sudoers.pw) and runs
 * `sudo /bin/id -u` twice; this program types bob's password at the
 * master when sudo's prompt shows. The second run, seconds after the
 * first and in the same session, is the P9 row: not asked.
 *
 * Session B: A's leader exits, the master is closed, and a new pty takes
 * the same number (the lowest free, pty(7)); a second child starts a
 * session on it the same way. kernel/sched never reuses a pid, so B's
 * leader cannot have A's leader's pid; the row stubs it instead: before
 * B's sudo runs, the record A's sudo wrote is given B's leader's pid where
 * it named A's, everything else kept, which is the file a reused pid
 * would meet. Then B runs `sudo /bin/id -u` once: the P8 row, asked again
 * (sudoers_timestamp(5): a terminal's record keeps the session leader's
 * start time, so a later leader with the same pid matches nothing).
 *
 * Every line is `ROW text`; no pid, time or address is printed unless a
 * row fails, when the record's own line is shown. Child and parent agree
 * through marks the child writes on the terminal (`@@go K`, `@@end K
 * st=N`), which the transcript of the master holds in order.
 *
 * Written from sudoers_timestamp(5), sudo(8), proc_pid_stat(5), pty(7),
 * pts(4), ioctl_tty(2), setsid(2), credentials(7), posix_openpt(3),
 * unlockpt(3), ptsname(3) (man-pages 6.7); the shape of px111's
 * user/elf/ptyprobe.c. No kernel's, C library's or sudo's source.
 * Written for this lane. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define BOB 1001
#define RECORD "/var/run/sudo/ts/1001"
#define PROMPT "password for bob: "

static char pw[128];

static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap); /* line-buffered: one write a row */
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

/* Bytes as a quoted C-like string (a failing row's evidence). */
static const char *esc(const char *b, long n) {
    static char o[4096];
    size_t k = 0;
    o[k++] = '"';
    for (long i = 0; i < n && k + 8 < sizeof o; i++) {
        unsigned char c = (unsigned char)b[i];
        if (c == '\n') { o[k++] = '\\'; o[k++] = 'n'; }
        else if (c == '\r') { o[k++] = '\\'; o[k++] = 'r'; }
        else if (c == '"' || c == '\\') { o[k++] = '\\'; o[k++] = (char)c; }
        else if (c < 32 || c > 126) k += (size_t)snprintf(o + k, sizeof o - k, "\\x%02x", c);
        else o[k++] = (char)c;
    }
    o[k++] = '"';
    o[k] = 0;
    return o;
}

/* proc_pid_stat(5)'s field 22, starttime (clock ticks since the boot), of
 * `pid`; -1 when it cannot be read. Fields are counted after the name's
 * closing parenthesis, the state being field 3. */
static long start_of(pid_t pid) {
    char path[64], b[1024];
    snprintf(path, sizeof path, "/proc/%d/stat", (int)pid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t n = read(fd, b, sizeof b - 1);
    close(fd);
    if (n <= 0) return -1;
    b[n] = 0;
    char *p = strrchr(b, ')');
    if (!p) return -1;
    int field = 2;
    for (char *t = strtok(p + 1, " \n"); t; t = strtok(0, " \n"))
        if (++field == 22) return atol(t);
    return -1;
}

/* --- the master's transcript ------------------------------------------- */

static char tr[65536];
static long tr_len;

/* Read what the master has, waiting at most about `ms`. A master whose
 * slave no one holds open yet (or any more) polls HUP and reads EIO
 * (pty(7)); that is waited out the same way, the callers' limits bound it. */
static void pump(int m, int ms) {
    struct pollfd p = {m, POLLIN, 0};
    if (poll(&p, 1, ms) <= 0) return;
    if (p.revents & POLLIN) {
        ssize_t k = read(m, tr + tr_len, sizeof tr - 1 - (size_t)tr_len);
        if (k > 0) { tr_len += k; tr[tr_len] = 0; return; }
    }
    nap(ms);
}

/* Where `want` starts in the transcript at or after `from`, or -1. */
static long find(const char *want, long from) {
    if (from >= tr_len) return -1;
    char *p = memmem(tr + from, (size_t)(tr_len - from), want, strlen(want));
    return p ? p - tr : -1;
}

/* One sudo run of a session's leader, read from the master: whether
 * sudo asked (and how often), its status, and whether `0` (id -u) came. */
struct run {
    int asks, status, ran0;
    long at, end;
    const char *why;
};

static long mark; /* the transcript read up to the last run's end */

static struct run watch(int m, int k) {
    struct run r = {0, -1, 0, -1, -1, 0};
    char go[32], end[32];
    snprintf(go, sizeof go, "@@go %d\r\n", k);
    snprintf(end, sizeof end, "@@end %d st=", k);
    long limit = now_ms() + 30000;
    while ((r.at = find(go, mark)) < 0) {
        if (now_ms() > limit) { r.why = "no start mark"; return r; }
        pump(m, 50);
    }
    limit = now_ms() + 180000; /* three scrypt checks under TCG at the most */
    long body = r.at + (long)strlen(go), seen = body;
    for (;;) {
        long q = find(PROMPT, seen);
        if (q >= 0) {
            r.asks++;
            seen = q + (long)strlen(PROMPT);
            nap(500); /* sudo turns the echo off after its prompt is written */
            (void)!write(m, pw, strlen(pw));
            (void)!write(m, "\r", 1);
            continue;
        }
        long e = find(end, body);
        if (e >= 0 && find("\r\n", e) >= 0) {
            r.end = e;
            r.status = atoi(tr + e + strlen(end));
            mark = find("\r\n", e) + 2;
            break;
        }
        if (now_ms() > limit) { r.why = "no end mark"; return r; }
        pump(m, 50);
    }
    /* id -u's line: `0` alone on a line between the marks */
    for (long i = body; i + 3 <= r.end; i++)
        if ((i == body || tr[i - 1] == '\n') && strncmp(tr + i, "0\r\n", 3) == 0) r.ran0 = 1;
    return r;
}

static const char *told(struct run r) {
    static char b[4600];
    if (r.why) {
        snprintf(b, sizeof b, "%s; the master read %s", r.why, esc(tr + mark, tr_len - mark));
    } else if (r.status == 0 && r.ran0 && r.asks == 1) {
        snprintf(b, sizeof b, "asked, the password typed, ran as uid 0");
    } else if (r.status == 0 && r.ran0 && r.asks == 0) {
        snprintf(b, sizeof b, "not asked, ran as uid 0");
    } else {
        snprintf(b, sizeof b, "asked %d time(s), status %d, the terminal %s", r.asks, r.status,
                 esc(tr + r.at, r.end - r.at));
    }
    return b;
}

/* --- a session's leader ------------------------------------------------- */

/* The child: a session of its own on `slave`, the terminal its own, bob,
 * then `runs` sudo runs, each between its marks. With `gate` >= 0 it
 * waits for one byte there first (the stub done). */
static void leader(const char *slave, int runs, int gate) {
    if (setsid() < 0) _exit(90);
    int s = open(slave, O_RDWR | O_NOCTTY);
    if (s < 0) _exit(91);
    if (ioctl(s, TIOCSCTTY, 0) != 0) _exit(92);
    dup2(s, 0); dup2(s, 1); dup2(s, 2);
    if (s > 2) close(s);
    if (gate >= 0) {
        char c;
        if (read(gate, &c, 1) != 1) _exit(93);
        close(gate);
    }
    gid_t g = BOB;
    if (setgroups(1, &g) != 0 || setresgid(BOB, BOB, BOB) != 0 || setresuid(BOB, BOB, BOB) != 0) _exit(94);
    char *envp[] = {"HOME=/home/bob", "USER=bob", "LOGNAME=bob", "TERM=linux", "PATH=/bin:/usr/bin", 0};
    for (int k = 1; k <= runs; k++) {
        printf("@@go %d\n", k);
        fflush(stdout);
        pid_t c = fork();
        if (c == 0) {
            char *argv[] = {"sudo", "/bin/id", "-u", 0};
            execve("/bin/sudo", argv, envp);
            _exit(127);
        }
        int st = 0;
        if (c < 0 || waitpid(c, &st, 0) != c) st = 0xff00;
        printf("@@end %d st=%d\n", k, WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st));
        fflush(stdout);
    }
    _exit(0);
}

/* A new pty, unlocked; its number and its slave's name. -1 on failure. */
static int pty(int *n, char *name, size_t cap) {
    int m = open("/dev/ptmx", O_RDWR | O_NOCTTY);
    if (m < 0) return -1;
    unsigned u = 0;
    if (unlockpt(m) != 0 || ioctl(m, TIOCGPTN, &u) != 0 || ptsname_r(m, name, cap) != 0) { close(m); return -1; }
    *n = (int)u;
    return m;
}

/* --- the record ---------------------------------------------------------- */

static char rec[4096];

static void read_record(void) {
    rec[0] = 0;
    int fd = open(RECORD, O_RDONLY);
    if (fd < 0) return;
    ssize_t n = read(fd, rec, sizeof rec - 1);
    close(fd);
    rec[n > 0 ? n : 0] = 0;
}

/* What the record's line for terminal `nr` says, in words: its key's
 * parts named for what they are when they are what they should be. */
static const char *form(long nr, pid_t sid, long start) {
    static char b[512];
    char want[64];
    snprintf(want, sizeof want, "tty %ld sid %d ", nr, (int)sid);
    char *l = strstr(rec, want);
    if (!l) { snprintf(b, sizeof b, "no line for this terminal and session: %s", esc(rec, (long)strlen(rec))); return b; }
    char *nl = strchr(l, '\n');
    long len = nl ? nl - l : (long)strlen(l);
    char line[256];
    snprintf(line, sizeof line, "%.*s", (int)(len < 255 ? len : 255), l);
    long s = -2, t = -2;
    char tail[64];
    if (sscanf(line + strlen(want), "start %ld time %ld%63s", &s, &t, tail) == 2 && s == start && t > 0) {
        snprintf(b, sizeof b, "tty %ld sid <the leader's pid> start <the leader's start time> time <ms>", nr);
    } else if (sscanf(line + strlen(want), "time %ld%63s", &t, tail) == 1 && t > 0) {
        snprintf(b, sizeof b, "tty %ld sid <the leader's pid> time <ms> (no start time)", nr);
    } else {
        snprintf(b, sizeof b, "%s (the leader's start time %ld)", esc(line, (long)strlen(line)), start);
    }
    return b;
}

/* The stub: every line of terminal `nr` and session `from` names session
 * `to` instead, all else kept. The number of lines changed. */
static int stub(long nr, pid_t from, pid_t to) {
    read_record();
    char was[64], now[64], out[4200];
    snprintf(was, sizeof was, "tty %ld sid %d ", nr, (int)from);
    snprintf(now, sizeof now, "tty %ld sid %d ", nr, (int)to);
    size_t k = 0;
    int changed = 0;
    for (char *l = rec; *l;) {
        char *nl = strchr(l, '\n');
        size_t len = nl ? (size_t)(nl - l) + 1 : strlen(l);
        if (strncmp(l, was, strlen(was)) == 0) {
            k += (size_t)snprintf(out + k, sizeof out - k, "%s%.*s", now, (int)(len - strlen(was)), l + strlen(was));
            changed++;
        } else {
            k += (size_t)snprintf(out + k, sizeof out - k, "%.*s", (int)len, l);
        }
        l += len;
    }
    int fd = open(RECORD, O_WRONLY | O_TRUNC);
    if (fd < 0) return -1;
    if (write(fd, out, k) != (ssize_t)k) changed = -1;
    close(fd);
    return changed;
}

int main(void) {
    setvbuf(stdout, 0, _IOLBF, 0);
    say("sudotty: px119's probe, sudo's record made on a pseudo-terminal\n");
    {
        FILE *f = fopen("/root/passwords.txt", "r");
        char line[160];
        while (f && fgets(line, sizeof line, f))
            if (strncmp(line, "bob ", 4) == 0) { snprintf(pw, sizeof pw, "%s", line + 4); pw[strcspn(pw, "\r\n")] = 0; }
        if (f) fclose(f);
        if (!pw[0]) { say("T0 no password for bob in /root/passwords.txt\n"); return 1; }
    }
    unlink(RECORD);

    /* Session A: two runs. */
    int n = -1;
    char name[64];
    int m = pty(&n, name, sizeof name);
    if (m < 0) { say("T1 no pty: %s\n", strerror(errno)); return 1; }
    long nr = ((136L + n / 256) << 8) | (n % 256); /* proc_pid_stat(5)'s tty_nr: the major in bits 15-8 */
    say("T1 a pty: /dev/pts/%d\n", n);
    fflush(stdout);
    pid_t a = fork();
    if (a == 0) { close(m); leader(name, 2, -1); }
    long ta = start_of(a);
    struct run r1 = watch(m, 1);
    say("T2 the first sudo in session A: %s\n", told(r1));
    read_record();
    say("T3 the record it left: %s\n", form(nr, a, ta));
    struct run r2 = watch(m, 2);
    say("P9 a second sudo in the same session, inside the timeout: %s\n", told(r2));
    int st = 0;
    waitpid(a, &st, 0);
    say("T4 session A ended: its leader exited %d\n", WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st));
    close(m);

    /* Session B: the same pty number, the record stubbed, one run. */
    int n2 = -1;
    char name2[64];
    m = pty(&n2, name2, sizeof name2);
    if (m < 0) { say("T5 no pty: %s\n", strerror(errno)); return 1; }
    say("T5 the pair closed and a new one opened: /dev/pts/%d, %s\n", n2, n2 == n ? "the same number" : "another number");
    int gate[2];
    if (pipe(gate) != 0) return 1;
    tr_len = 0, mark = 0, tr[0] = 0;
    fflush(stdout);
    pid_t b = fork();
    if (b == 0) { close(m); close(gate[1]); leader(name2, 1, gate[0]); }
    close(gate[0]);
    long tb = start_of(b);
    int k = stub(nr, a, b);
    say("T6 the stub (PAX never reuses a pid): session A's record given session B's leader's pid, %d line(s); B's leader started %s A's\n",
        k, tb > ta ? "later than" : tb == ta ? "in the same tick as" : "before");
    (void)!write(gate[1], "x", 1);
    close(gate[1]);
    struct run r3 = watch(m, 1);
    say("P8 a new session on the same pty number, its leader with the earlier leader's pid: %s\n", told(r3));
    waitpid(b, &st, 0);
    say("T7 session B ended: its leader exited %d\n", WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st));
    close(m);
    say("done\n");
    return 0;
}
