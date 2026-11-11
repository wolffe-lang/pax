/* sudoppid.c — px121: sudo's timestamp record made with no terminal, asked
 * of PAX's sudo (user/sudo) with -S, bob's password on standard input. The
 * run list of tests/mpx5-sudo's `sudoppid` image is two commands, each
 * started by the kernel as root:
 *
 *   /bin/sudoppid          init (pid 1): forks session D's leader, which
 *                          starts a session of its own (no terminal) and
 *                          forks two callers; init then ends, and the
 *                          leader ends after it. The callers have no parent
 *                          from then on: kernel/sched gives an ending
 *                          process's children to nobody once pid 1 has
 *                          ended, so getppid(2) says 0, and /proc/0/stat
 *                          names no process. kmain_console runs the next
 *                          command only when every process has ended.
 *   /bin/sudoppid report   what session D's two sudo runs did, then
 *                          session E, whose callers' parent is alive.
 *
 * Session D (P10): the first caller becomes bob and execs
 * `sudo -S /bin/id -u`; the second waits for that run to end (a pipe's end
 * the first holds through its exec) and does the same. With no terminal
 * and the parent's start time unreadable, sudo has no key for a record
 * (`ppid 0 start -1 sid SID` would be the key of every parentless caller
 * in the session), so it honours none and writes none: both runs are
 * asked, and there is no record file afterwards.
 *
 * Session E (P11): the report's child starts a session of its own (no
 * terminal) and forks two callers in turn, each `sudo -S /bin/id -u` as
 * bob, each waited for. The first is asked and leaves the record
 * `ppid <E> start <E's start time> sid <E> time <ms>`; the second, inside
 * the timeout and with the same parent, is not asked (px115's key, as
 * before).
 *
 * Every line is `ROW text`; no pid, time or address is printed unless a row
 * fails, when the evidence is shown. Each caller writes what it saw
 * (getppid, its session, its terminal) to a file under /root/px121 before
 * its exec, and sudo's standard output and error go to files there, which
 * the report reads.
 *
 * Written from sudoers_timestamp(5), sudo(8), getppid(2), setsid(2),
 * proc_pid_stat(5) and credentials(7) (man-pages 6.7), and PAX's own
 * kernel/sched (reparent) and kernel/kmain_console (the run list); the
 * shape of px119's user/elf/sudotty.c. No kernel's, C library's or sudo's
 * source. Written for this lane. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <poll.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define BOB 1001
#define RECORD "/var/run/sudo/ts/1001"
#define PROMPT "password for bob: "
#define HERE "/root/px121"

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
    static char o[2][2048];
    static int which;
    char *d = o[which ^= 1];
    size_t k = 0;
    d[k++] = '"';
    for (long i = 0; i < n && k + 8 < sizeof o[0]; i++) {
        unsigned char c = (unsigned char)b[i];
        if (c == '\n') { d[k++] = '\\'; d[k++] = 'n'; }
        else if (c == '\r') { d[k++] = '\\'; d[k++] = 'r'; }
        else if (c == '"' || c == '\\') { d[k++] = '\\'; d[k++] = (char)c; }
        else if (c < 32 || c > 126) k += (size_t)snprintf(d + k, sizeof o[0] - k, "\\x%02x", c);
        else d[k++] = (char)c;
    }
    d[k++] = '"';
    d[k] = 0;
    return d;
}

/* A file's bytes into `b` (at most cap - 1, NUL-terminated): the length,
 * or -1 when it cannot be opened. */
static long slurp(const char *path, char *b, long cap) {
    b[0] = 0;
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    long n = 0;
    for (;;) {
        ssize_t k = read(fd, b + n, (size_t)(cap - 1 - n));
        if (k <= 0) break;
        n += k;
    }
    close(fd);
    b[n] = 0;
    return n;
}

/* proc_pid_stat(5)'s field `want` of the file at `path` (session 6,
 * tty_nr 7, starttime 22); -1 when it cannot be read. Fields are counted
 * after the name's closing parenthesis, the state being field 3. */
static long stat_field(const char *path, int want) {
    char b[1024];
    if (slurp(path, b, sizeof b) <= 0) return -1;
    char *p = strrchr(b, ')');
    if (!p) return -1;
    int field = 2;
    for (char *t = strtok(p + 1, " \n"); t; t = strtok(0, " \n"))
        if (++field == want) return atol(t);
    return -1;
}

static long start_of(pid_t pid) {
    char path[64];
    snprintf(path, sizeof path, "/proc/%d/stat", (int)pid);
    return stat_field(path, 22);
}

static int put_file(const char *path, const char *text) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) return -1;
    size_t n = strlen(text);
    int ok = write(fd, text, n) == (ssize_t)n;
    close(fd);
    return ok ? 0 : -1;
}

/* --- the callers ---------------------------------------------------------- */

/* Wait, at most `ms`, until this process has no parent (getppid 0). */
static void orphaned(int ms) {
    long limit = now_ms() + ms;
    while (getppid() != 0 && now_ms() < limit) nap(10);
}

/* What caller `k` sees, to HERE/cK.txt: its parent, its session, its
 * terminal (proc_pid_stat(5)'s session and tty_nr), its parent's start. */
static void facts(int k) {
    char path[64], b[160];
    pid_t pp = getppid();
    snprintf(path, sizeof path, HERE "/c%d.txt", k);
    snprintf(b, sizeof b, "ppid %d sid %ld tty %ld pstart %ld\n", (int)pp, stat_field("/proc/self/stat", 6),
             stat_field("/proc/self/stat", 7), start_of(pp));
    put_file(path, b);
}

/* Caller `k`: standard input the password, standard output and error
 * HERE/runK.out and .err, bob, then `sudo -S /bin/id -u`. Never returns. */
static void run_sudo(int k) {
    char out[64], err[64];
    snprintf(out, sizeof out, HERE "/run%d.out", k);
    snprintf(err, sizeof err, HERE "/run%d.err", k);
    int i = open(HERE "/pw", O_RDONLY);
    int o = open(out, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    int e = open(err, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (i < 3 || o < 3 || e < 3) _exit(95);
    if (dup2(i, 0) != 0 || dup2(o, 1) != 1 || dup2(e, 2) != 2) _exit(96);
    close(i); close(o); close(e);
    gid_t g = BOB;
    if (setgroups(1, &g) != 0 || setresgid(BOB, BOB, BOB) != 0 || setresuid(BOB, BOB, BOB) != 0) _exit(94);
    char *argv[] = {"sudo", "-S", "/bin/id", "-u", 0};
    char *envp[] = {"HOME=/home/bob", "USER=bob", "LOGNAME=bob", "PATH=/bin:/usr/bin", 0};
    execve("/bin/sudo", argv, envp);
    _exit(127);
}

/* Session D's leader: a session of its own, two callers, then (init
 * ended) its own end, after which the callers have no parent. `ready`
 * tells init the session is made, so init's end (its terminal's hangup)
 * reaches none of them. Never returns. */
static void session_d(int ready) {
    if (setsid() < 0) _exit(90);
    int g[2];
    if (pipe(g) != 0) _exit(91);
    pid_t c1 = fork();
    if (c1 == 0) {
        close(ready);
        close(g[0]);
        orphaned(60000);
        facts(1);
        run_sudo(1); /* g[1] held through the exec: closed when the run has ended */
    }
    pid_t c2 = fork();
    if (c2 == 0) {
        close(ready);
        close(g[1]);
        orphaned(60000);
        long limit = now_ms() + 300000; /* three scrypt checks under TCG at the most */
        char c;
        struct pollfd p = {g[0], POLLIN, 0};
        while (now_ms() < limit) {
            if (poll(&p, 1, 1000) > 0 && read(g[0], &c, 1) <= 0) break;
        }
        close(g[0]);
        facts(2);
        run_sudo(2);
    }
    close(g[0]);
    close(g[1]);
    if (c1 < 0 || c2 < 0) _exit(92);
    (void)!write(ready, "x", 1);
    close(ready);
    orphaned(60000);
    _exit(0);
}

/* --- the report ------------------------------------------------------------ */

/* One run as its files tell it, and its wait status when known (`st` -1:
 * nobody could wait for it). */
static const char *told(int k, int st) {
    static char b[4600];
    char path[64], out[512], err[1024];
    snprintf(path, sizeof path, HERE "/run%d.out", k);
    long no = slurp(path, out, sizeof out);
    snprintf(path, sizeof path, HERE "/run%d.err", k);
    long ne = slurp(path, err, sizeof err);
    int asks = 0;
    for (char *q = err; (q = strstr(q, PROMPT)); q += strlen(PROMPT)) asks++;
    int ran0 = strcmp(out, "0\n") == 0;
    if (no < 0 || ne < 0) {
        snprintf(b, sizeof b, "it did not run (no output files)");
    } else if ((st == -1 || st == 0) && ran0 && asks == 1) {
        snprintf(b, sizeof b, "asked, the password read, ran as uid 0");
    } else if ((st == -1 || st == 0) && ran0 && asks == 0) {
        snprintf(b, sizeof b, "not asked, ran as uid 0");
    } else {
        snprintf(b, sizeof b, "asked %d time(s), status %d, standard output %s, standard error %s", asks, st, esc(out, no),
                 esc(err, ne));
    }
    return b;
}

static int read_facts(int k, int *pp, long *sid, long *tty, long *pstart, char *raw, long cap) {
    char path[64];
    snprintf(path, sizeof path, HERE "/c%d.txt", k);
    if (slurp(path, raw, cap) <= 0) return -1;
    return sscanf(raw, "ppid %d sid %ld tty %ld pstart %ld", pp, sid, tty, pstart) == 4 ? 0 : -1;
}

/* The record's lines as `ppid <P> start <S> sid <D> time <ms>`, each part
 * named when it is what it should be: `pp`, `ps`, `sid` (`ps` -1: the
 * shared key `start -1`). "none" when there is no record file. Lines of
 * other sessions are left out when `only` is set. */
static const char *record(pid_t pp, long ps, long sid, int only, const char *pp_name, const char *ps_name) {
    static char b[4600];
    char rec[2048];
    long n = slurp(RECORD, rec, sizeof rec);
    if (n < 0) {
        snprintf(b, sizeof b, errno == ENOENT ? "none" : "a record file that cannot be read");
        return b;
    }
    size_t k = 0;
    b[0] = 0;
    for (char *l = rec; *l;) {
        char *nl = strchr(l, '\n');
        long len = nl ? nl - l : (long)strlen(l);
        char line[256];
        snprintf(line, sizeof line, "%.*s", (int)(len < 255 ? len : 255), l);
        l += len + (nl ? 1 : 0);
        int p = -2;
        long s = -2, d = -2, t = -2;
        char tail[64];
        int mine = sscanf(line, "ppid %d start %ld sid %ld time %ld%63s", &p, &s, &d, &t, tail) == 4 && t > 0;
        if (only && !(mine && d == sid)) continue;
        if (mine && p == (int)pp && s == ps && d == sid)
            k += (size_t)snprintf(b + k, sizeof b - k, "%sppid %s start %s sid <the session> time <ms>", k ? "; " : "", pp_name,
                                  ps_name);
        else
            k += (size_t)snprintf(b + k, sizeof b - k, "%s%s", k ? "; " : "", esc(line, (long)strlen(line)));
        if (k >= sizeof b - 1) break;
    }
    if (!b[0]) snprintf(b, sizeof b, only ? "no line for this session: %s" : "an empty file%s", only ? esc(rec, n) : "");
    return b;
}

static int report(void) {
    say("T2 the report, after every process of init's run had ended\n");
    /* Session D: the callers had no parent. */
    int p1 = -2, p2 = -2;
    long s1 = -2, s2 = -2, t1 = -2, t2 = -2, ps1 = -2, ps2 = -2;
    char f1[160], f2[160], z[64];
    int ok1 = read_facts(1, &p1, &s1, &t1, &ps1, f1, sizeof f1) == 0, ok2 = read_facts(2, &p2, &s2, &t2, &ps2, f2, sizeof f2) == 0;
    int zero_read = slurp("/proc/0/stat", z, sizeof z) >= 0;
    if (ok1 && ok2 && p1 == 0 && p2 == 0 && s1 > 0 && s1 == s2 && t1 == 0 && t2 == 0 && ps1 == -1 && ps2 == -1 && !zero_read)
        say("T3 session D's two callers: no terminal, one session, no parent (getppid 0; /proc/0/stat cannot be read)\n");
    else
        say("T3 session D's two callers: %s and %s; /proc/0/stat %s\n", esc(f1, (long)strlen(f1)), esc(f2, (long)strlen(f2)),
            zero_read ? "read" : "cannot be read");
    say("T4 the first sudo -S in session D: %s\n", told(1, -1));
    say("P10 a second sudo -S in session D, inside the timeout, its parent unreadable too: %s\n", told(2, -1));
    say("T5 the record after session D: %s\n", record(0, -1, s1, 0, "0", "-1"));

    /* Session E: the callers' parent alive. */
    fflush(stdout);
    int gate[2];
    if (pipe(gate) != 0) return 1;
    pid_t e = fork();
    if (e == 0) {
        close(gate[1]);
        if (setsid() < 0) _exit(90);
        char x;
        if (read(gate[0], &x, 1) != 1) _exit(93); /* the report has read this leader's start */
        close(gate[0]);
        char path[64], b[32];
        for (int k = 3; k <= 4; k++) {
            pid_t kid = fork();
            if (kid == 0) {
                facts(k);
                run_sudo(k);
            }
            int st = 0;
            if (kid < 0 || waitpid(kid, &st, 0) != kid) st = 0xff00;
            snprintf(path, sizeof path, HERE "/e%d.st", k);
            snprintf(b, sizeof b, "%d\n", WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st));
            put_file(path, b);
        }
        _exit(0);
    }
    close(gate[0]);
    long te = start_of(e);
    (void)!write(gate[1], "x", 1);
    close(gate[1]);
    int st = 0;
    if (e < 0 || waitpid(e, &st, 0) != e) st = 0xff00;
    int p3 = -2, p4 = -2;
    long s3 = -2, s4 = -2, t3 = -2, t4 = -2, ps3 = -2, ps4 = -2;
    char f3[160], f4[160], sb[32];
    int ok3 = read_facts(3, &p3, &s3, &t3, &ps3, f3, sizeof f3) == 0, ok4 = read_facts(4, &p4, &s4, &t4, &ps4, f4, sizeof f4) == 0;
    if (ok3 && ok4 && p3 == e && p4 == e && s3 == e && s4 == e && t3 == 0 && t4 == 0 && te >= 0 && ps3 == te && ps4 == te)
        say("T6 session E's two callers: no terminal, one session, the parent its leader, alive (its /proc/PID/stat read)\n");
    else
        say("T6 session E's two callers: %s and %s; the leader's start %ld\n", esc(f3, (long)strlen(f3)), esc(f4, (long)strlen(f4)), te);
    int st3 = slurp(HERE "/e3.st", sb, sizeof sb) > 0 ? atoi(sb) : -2;
    int st4 = slurp(HERE "/e4.st", sb, sizeof sb) > 0 ? atoi(sb) : -2;
    say("T7 the first sudo -S in session E: %s\n", told(3, st3));
    say("P11 a second sudo -S in session E, inside the timeout, its parent the same: %s\n", told(4, st4));
    say("T8 the record after session E: %s\n", record(e, te, e, 1, "<the parent's pid>", "<the parent's start time>"));
    say("T9 session E ended: its leader exited %d\n", WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st));
    say("done\n");
    return 0;
}

int main(int argc, char **argv) {
    setvbuf(stdout, 0, _IOLBF, 0);
    if (argc > 1 && strcmp(argv[1], "report") == 0) return report();
    say("sudoppid: px121's probe, sudo's record made with no terminal\n");
    char pw[160] = "";
    {
        FILE *f = fopen("/root/passwords.txt", "r");
        char line[160];
        while (f && fgets(line, sizeof line, f))
            if (strncmp(line, "bob ", 4) == 0) { snprintf(pw, sizeof pw - 1, "%s", line + 4); pw[strcspn(pw, "\r\n")] = 0; }
        if (f) fclose(f);
        if (!pw[0]) { say("T0 no password for bob in /root/passwords.txt\n"); return 1; }
    }
    strcat(pw, "\n");
    if ((mkdir(HERE, 0700) != 0 && errno != EEXIST) || put_file(HERE "/pw", pw) != 0) {
        say("T0 cannot write %s: %s\n", HERE "/pw", strerror(errno));
        return 1;
    }
    unlink(RECORD);
    int ready[2];
    if (pipe(ready) != 0) return 1;
    fflush(stdout);
    pid_t m = fork();
    if (m == 0) {
        close(ready[0]);
        session_d(ready[1]);
    }
    close(ready[1]);
    char c;
    int ok = m > 0 && read(ready[0], &c, 1) == 1;
    say("T1 session D: its leader in a session of its own with two callers; init ends: %s\n", ok ? "made" : "not made");
    return ok ? 0 : 1;
}
