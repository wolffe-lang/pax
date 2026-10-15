/* rights.c — px45: who may signal whom, and what only root may do. The
 * rules px38's `sig` and `priv` probes hold whole, asked again where PAX
 * can show them (a target in the state a set-ID run leaves, made by
 * `setresuid` and `execve` without a bit; a zombie; `tkill`), and the
 * rest of U5's: what a signal's handler is told of its sender, a child's
 * end, ports, priority and the scheduler, root's calls, the speaker's
 * ioctls, /dev's modes as `open` meets them, /proc/<pid>'s `status`,
 * `cmdline`, `environ` and `fd/` by owner and dumpable, and SO_PEERCRED.
 * Static; every call under test is a raw `syscall(2)` (px38.h's `rc`).
 *
 *   rights           as root: each row by a child that took a state of
 *                    ids for good (the actors), against targets root
 *                    started in chosen states
 *   rights user      the rows a user can make alone, as whoever runs it
 *                    (tests/mpx5-users: `as 1000 1000 /bin/rights user`)
 *   rights soak N [UID]
 *                    N rounds of signals, a low port, a priority, a
 *                    0600 node, another process's environ, SO_PEERCRED,
 *                    chroot and reboot; with UID, root starts a target
 *                    of its own and then becomes UID:UID for good
 *   rights wait      (a target: sleeps until it is killed)
 *
 * No line carries a pid: a sender's or a peer's pid is printed as whose
 * it is. Written from kill(2), tgkill(2), signal(7), sigaction(2),
 * wait(2), bind(2), ip(7), raw(7), setpriority(2), sched_setscheduler(2),
 * chroot(2), reboot(2), sethostname(2), settimeofday(2), clock_settime(2),
 * mount(2), umount(2), mknod(2), ioctl_console(2), null(4), random(4),
 * proc(5), proc_pid_environ(5), proc_pid_fd(5), ptrace(2), unix(7),
 * socket(7) and the uapi headers; no kernel's or libc's source. */
#include "px38.h"
#include <arpa/inet.h>
#include <dirent.h>
#include <linux/kd.h>
#include <netinet/in.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/sysmacros.h>
#include <sys/time.h>
#include <sys/un.h>
#include <time.h>

static const char *SELF = "/bin/rights";
static int alone; /* `rights user` */

static void nap(long ms)
{
    struct timespec t = { ms / 1000, (ms % 1000) * 1000000L };
    rc(SYS_nanosleep, (long)&t, 0, 0, 0, 0);
}

/* --- targets ---------------------------------------------------------------- */

struct target { long r, e, s; int how; const char *name; pid_t pid; };
/* how: 1 execs `rights wait`, 0 sleeps as it is, 2 ends at once (a zombie) */
static struct target T[] = {
    { 1000, 1000, 1000, 1, "(1000 1000 1000) exec'd ", 0 },
    { 1000, 1001, 1002, 1, "(1000 1001 1002) exec'd ", 0 }, /* (1000 1001 1001) after it: the state a set-ID run of 1001's file by 1000 leaves */
    { 1000, 1001, 1002, 0, "(1000 1001 1002) no exec", 0 },
    { 1002, 1000, 1001, 0, "(1002 1000 1001) no exec", 0 },
    { 0, 0, 0, 1, "(   0    0    0) exec'd ", 0 },
    { 1000, 1000, 1000, 2, "zombie (1000 1000 1000) ", 0 },
    { 1000, 1001, 1002, 2, "zombie (1000 1001 1002) ", 0 },
};
enum { NT = sizeof T / sizeof *T };

/* Start target t: root forks; the child takes its ids (groups none, gids
 * 2999) and execs `rights wait FD` (environment SECRET=px45), sleeps, or
 * ends. Returns once it is settled. */
static pid_t start(struct target *t)
{
    int pfd[2];
    if (pipe(pfd) != 0) _exit(95);
    pid_t p = fork();
    if (p == 0) {
        close(pfd[0]);
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
        if (rc(SYS_setresuid, t->r, t->e, t->s, 0, 0) != 0) _exit(99);
        if (t->how == 2) _exit(3);
        if (t->how == 0) {
            if (write(pfd[1], "k", 1) != 1) _exit(94);
            close(pfd[1]);
            for (;;) nap(100000);
        }
        char fdarg[16];
        snprintf(fdarg, sizeof fdarg, "%d", pfd[1]);
        char *av[] = { (char *)SELF, (char *)"wait", fdarg, NULL };
        char *ev[] = { (char *)"SECRET=px45", (char *)"PATH=/bin", NULL };
        execve(SELF, av, ev);
        _exit(98);
    }
    close(pfd[1]);
    char c;
    long n = read(pfd[0], &c, 1);
    close(pfd[0]);
    if (t->how == 2) {
        /* a zombie: it has ended (its end of the pipe closed) and is not waited for */
        if (n != 0) say("! a zombie wrote\n");
        nap(100);
    } else if (n != 1) say("! a target did not settle\n");
    return p;
}

static void stop_all(void)
{
    for (int i = 0; i < NT; i++) {
        if (T[i].pid <= 0) continue;
        if (T[i].how != 2) kill(T[i].pid, SIGKILL);
        reap(T[i].pid);
        T[i].pid = 0;
    }
}

/* --- S: who may signal whom ------------------------------------------------- */

static const long SND[][3] = {
    { 1000, 1000, 1000 }, { 1001, 1001, 1001 }, { 1002, 1002, 1002 }, { 1003, 1003, 1003 },
    { 1003, 1000, 1003 }, { 1003, 1001, 1003 }, { 1003, 1002, 1003 },
    { 1000, 1003, 1003 }, { 1001, 1003, 1003 }, { 1002, 1003, 1003 },
    { 1003, 1003, 1000 }, { 1003, 1003, 1001 }, { 1003, 1003, 1002 },
    { 0, 0, 0 }, { 1003, 0, 1003 }, { 0, 1003, 0 }, { 0, 1003, 1003 },
};
enum { NS = sizeof SND / sizeof *SND };

static void become_state(const long S[3])
{
    rc(SYS_setgroups, 0, 0, 0, 0, 0);
    rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
    if (rc(SYS_setresuid, S[0], S[1], S[2], 0, 0) != 0) _exit(99);
}

static void send_rows(void)
{
    say("== S: who may signal whom: sender (real effective saved) -> target\n");
    for (int s = 0; s < NS; s++)
        for (int i = 0; i < NT; i++) {
            pid_t p = fork();
            if (p == 0) {
                become_state(SND[s]);
                pid_t t = T[i].pid;
                long a = rc(SYS_kill, t, 0, 0, 0, 0);
                long b = rc(SYS_tgkill, t, t, 0, 0, 0);
                long c = rc(SYS_tkill, t, 0, 0, 0, 0);
                long d = rc(SYS_kill, t, SIGCONT, 0, 0, 0);
                long e = rc(SYS_kill, t, SIGURG, 0, 0, 0);
                long f = rc(SYS_tgkill, t, t, SIGWINCH, 0, 0);
                say("sender (%4ld %4ld %4ld) -> %s: kill 0 %ld, tgkill 0 %ld, tkill 0 %ld, SIGCONT %ld, SIGURG %ld, tgkill SIGWINCH %ld\n", SND[s][0],
                    SND[s][1], SND[s][2], T[i].name, a, b, c, d, e, f);
                _exit(0);
            }
            reap(p);
        }
}

/* The calls that name no one process, and the order of their answers. */
static void other_rows(void)
{
    say("== K: kill(-1), kill(0), and what is answered first\n");
    static const long K[][3] = { { 1000, 1000, 1000 }, { 1003, 1003, 1003 }, { 1003, 1000, 1003 }, { 0, 1003, 0 }, { 1003, 0, 1003 } };
    for (unsigned k = 0; k < sizeof K / sizeof *K; k++) {
        pid_t p = fork();
        if (p == 0) {
            become_state(K[k]);
            pid_t t1 = T[0].pid, t4 = T[3].pid, t5 = T[4].pid;
            long a = rc(SYS_kill, -1, 0, 0, 0, 0);
            long b = rc(SYS_kill, -1, SIGWINCH, 0, 0, 0);
            long c = rc(SYS_kill, 0, 0, 0, 0, 0);
            long d = rc(SYS_kill, 0, SIGWINCH, 0, 0, 0);
            long e = rc(SYS_kill, 999999, 0, 0, 0, 0);
            long f = rc(SYS_kill, t5, 65, 0, 0, 0);
            long g = rc(SYS_tgkill, t1, t4, 0, 0, 0);
            long h = rc(SYS_tgkill, t5, t5, 65, 0, 0);
            long i = rc(SYS_tgkill, 999999, t5, 0, 0, 0);
            long j = rc(SYS_tkill, 999999, 0, 0, 0, 0);
            say("sender (%4ld %4ld %4ld): kill(-1, 0) %ld, kill(-1, SIGWINCH) %ld; kill(0, 0) %ld, kill(0, SIGWINCH) %ld; kill(999999, 0) %ld; "
                "root's target, signal 65: kill %ld, tgkill %ld; tgkill of a thread not in the group %ld, of no group %ld; tkill(999999) %ld\n",
                K[k][0], K[k][1], K[k][2], a, b, c, d, e, f, h, g, i, j);
            _exit(0);
        }
        reap(p);
    }
}

/* --- H: what a handler is told, and a child's end --------------------------- */

static int hpipe[2];
static void on_sig(int sig, siginfo_t *si, void *uc)
{
    (void)uc;
    long w[5] = { sig, si->si_code, si->si_pid, (long)si->si_uid, si->si_status };
    if (write(hpipe[1], w, sizeof w) != (long)sizeof w) _exit(93);
}
static void catch(int sig)
{
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = on_sig;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;
    sigaction(sig, &sa, NULL);
}
static const char *whose(long pid, pid_t a, const char *an, pid_t b, const char *bn)
{
    static char o[32];
    if (pid == a) return an;
    if (pid == b) return bn;
    snprintf(o, sizeof o, "%s", pid == 0 ? "0" : "another");
    return o;
}

static void handler_rows(void)
{
    say("== H: what a handler is told of its sender (siginfo's code, pid and uid)\n");
    if (pipe(hpipe) != 0) _exit(95);
    int go[2];
    if (pipe(go) != 0) _exit(95);
    pid_t h = fork();
    if (h == 0) {
        /* the handler target: (1000 1000 1000), SIGUSR1 and SIGUSR2 caught */
        close(go[1]);
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
        if (rc(SYS_setresuid, 1000, 1000, 1000, 0, 0) != 0) _exit(99);
        catch(SIGUSR1);
        catch(SIGUSR2);
        if (write(hpipe[1], "ready...........................................", 40) != 40) _exit(94);
        char c;
        while (read(go[0], &c, 1) != 0) ;
        _exit(0);
    }
    close(go[0]);
    {
        char b[40];
        if (read(hpipe[0], b, 40) != 40) say("! the handler did not settle\n");
    }
    static const long HS[][3] = { { 1000, 1000, 1000 }, { 1003, 1000, 1003 }, { 1000, 1003, 1003 }, { 1003, 1003, 1000 }, { 0, 0, 0 }, { 1003, 0, 1003 }, { 0, 1003, 0 } };
    for (unsigned k = 0; k < sizeof HS / sizeof *HS; k++)
        for (int how = 0; how < 2; how++) {
            int done[2];
            if (pipe(done) != 0) _exit(95);
            pid_t p = fork();
            if (p == 0) {
                close(done[0]);
                become_state(HS[k]);
                long r = how == 0 ? rc(SYS_kill, h, SIGUSR1, 0, 0, 0) : rc(SYS_tgkill, h, h, SIGUSR2, 0, 0);
                if (write(done[1], &r, sizeof r) != (long)sizeof r) _exit(93);
                for (;;) nap(100000);
            }
            close(done[1]);
            long r = -999;
            if (read(done[0], &r, sizeof r) != (long)sizeof r) say("! no answer\n");
            close(done[0]);
            char got[96] = "nothing";
            if (r == 0) {
                long w[5];
                if (read(hpipe[0], w, sizeof w) == (long)sizeof w)
                    snprintf(got, sizeof got, "signal %ld, code %ld, pid %s, uid %ld", w[0], w[1], whose(w[2], p, "the sender's", h, "its own"), w[3]);
            }
            say("sender (%4ld %4ld %4ld) %s to (1000 1000 1000): %ld; the handler is told %s\n", HS[k][0], HS[k][1], HS[k][2],
                how == 0 ? "kill SIGUSR1   " : "tgkill SIGUSR2 ", r, got);
            kill(p, SIGKILL);
            reap(p);
        }
    close(go[1]);
    reap(h);

    say("== E: a child's end: SIGCHLD reaches its parent whatever their ids\n");
    static const long PC[][4] = { /* parent's ids after the fork, child's ids, how the child ends (0: exit 3, 1: SIGTERM) */
        { 0, 1000, 0, 0 }, { 1002, 1000, 0, 0 }, { 1002, 1001, 1, 0 }, { 0, 1001, 1, 1 }, { 1003, 0, 0, 1 },
    };
    for (unsigned k = 0; k < sizeof PC / sizeof *PC; k++) {
        pid_t p = fork();
        if (p == 0) {
            int cp[2], gp[2];
            if (pipe(cp) != 0 || pipe(hpipe) != 0 || pipe(gp) != 0) _exit(95);
            catch(SIGCHLD);
            pid_t c = fork();
            if (c == 0) {
                close(gp[1]);
                rc(SYS_setgroups, 0, 0, 0, 0, 0);
                rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
                long cu = PC[k][1];
                if (rc(SYS_setresuid, cu, PC[k][3] ? 1003 : cu, cu, 0, 0) != 0) _exit(99);
                char ch;
                while (read(gp[0], &ch, 1) > 0) ;
                if (PC[k][2]) { signal(SIGTERM, SIG_DFL); kill(getpid(), SIGTERM); }
                _exit(3);
            }
            close(gp[0]);
            if (PC[k][0] != 0) {
                rc(SYS_setgroups, 0, 0, 0, 0, 0);
                rc(SYS_setresgid, 2998, 2998, 2998, 0, 0);
                if (rc(SYS_setresuid, PC[k][0], PC[k][0], PC[k][0], 0, 0) != 0) _exit(99);
            }
            close(gp[1]); /* the child goes */
            long w[5] = { 0, 0, 0, 0, 0 };
            long n = read(hpipe[0], w, sizeof w);
            int stt = 0;
            long r = rc(SYS_wait4, c, (long)&stt, 0, 0, 0);
            say("parent %4ld, child (%4ld %4ld %4ld) %s: SIGCHLD %s, code %ld, pid %s, uid %ld, status %ld; wait4 %s, status 0x%x\n", PC[k][0],
                PC[k][1], PC[k][3] ? 1003L : PC[k][1], PC[k][1], PC[k][2] ? "killed by SIGTERM" : "exit 3        ",
                n == (long)sizeof w ? "taken" : "not taken", w[1], whose(w[2], c, "the child's", getpid(), "its own"), w[3], w[4],
                r == c ? "the child" : "?", stt);
            _exit(0);
        }
        reap(p);
    }
}

/* --- P: what only root may do ------------------------------------------------ */

static long bind_port(int type, int port, int keep)
{
    int s = socket(AF_INET, type, 0);
    if (s < 0) return -(long)errno;
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    long r = bind(s, (struct sockaddr *)&a, sizeof a) == 0 ? 0L : -(long)errno;
    if (keep && r == 0) return s;
    close(s);
    return r;
}

struct pstate { long r, e, s; const char *name; };
static const struct pstate PS[] = {
    { 0, 0, 0, "root          " },
    { 1000, 1000, 1000, "user          " },
    { 1000, 0, 1000, "(1000 0 1000) " },
    { 0, 1000, 0, "(0 1000 0)    " },
};
enum { NPS = sizeof PS / sizeof *PS };

static int tty0 = -1;

static void priv_rows(const struct pstate *P, int others)
{
    const char *w = P->name;
    say("%s: bind TCP 80 %ld, 1023 %ld, 1024 %ld, 0 %ld, 81 held by root %ld; UDP 53 %ld, 1024 %ld\n", w, bind_port(SOCK_STREAM, 80, 0),
        bind_port(SOCK_STREAM, 1023, 0), bind_port(SOCK_STREAM, 1024, 0), bind_port(SOCK_STREAM, 0, 0), bind_port(SOCK_STREAM, 81, 0),
        bind_port(SOCK_DGRAM, 53, 0), bind_port(SOCK_DGRAM, 1024, 0));
    {
        int s = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
        long r = s < 0 ? -(long)errno : 0;
        if (s >= 0) close(s);
        say("%s: socket(AF_INET, SOCK_RAW, ICMP) %ld\n", w, r);
    }
    {
        long g0 = rc(SYS_getpriority, PRIO_PROCESS, 0, 0, 0, 0);
        long a = rc(SYS_setpriority, PRIO_PROCESS, 0, 5, 0, 0);
        long g1 = rc(SYS_getpriority, PRIO_PROCESS, 0, 0, 0, 0);
        long b = rc(SYS_setpriority, PRIO_PROCESS, 0, 4, 0, 0);
        long c = rc(SYS_setpriority, PRIO_PROCESS, 0, 25, 0, 0);
        long g2 = rc(SYS_getpriority, PRIO_PROCESS, 0, 0, 0, 0);
        long d = rc(SYS_setpriority, PRIO_PROCESS, 0, -3, 0, 0);
        long g3 = rc(SYS_getpriority, PRIO_PROCESS, 0, 0, 0, 0);
        long h = rc(SYS_setpriority, PRIO_PROCESS, 999999, 6, 0, 0);
        long i = rc(SYS_setpriority, 7, 0, 6, 0, 0);
        say("%s: getpriority %ld; setpriority 5 %ld (%ld), 4 %ld, 25 %ld (%ld), -3 %ld (%ld); of no process %ld, which 7 %ld\n", w, g0, a, g1, b, c, g2,
            d, g3, h, i);
        if (others) {
            /* setpriority(2): another process's, by whose ids; each set back by root after the row */
            long e = rc(SYS_setpriority, PRIO_PROCESS, T[0].pid, 6, 0, 0);
            long e2 = rc(SYS_setpriority, PRIO_PROCESS, T[2].pid, 6, 0, 0);
            long f = rc(SYS_setpriority, PRIO_PROCESS, T[3].pid, 6, 0, 0);
            long g = rc(SYS_setpriority, PRIO_PROCESS, T[4].pid, 6, 0, 0);
            long g4 = rc(SYS_getpriority, PRIO_PROCESS, T[0].pid, 0, 0, 0);
            long g5 = rc(SYS_getpriority, PRIO_PROCESS, T[4].pid, 0, 0, 0);
            long z = rc(SYS_setpriority, PRIO_PROCESS, T[5].pid, 6, 0, 0);
            say("%s: setpriority 6 of (1000 1000 1000) %ld, of (1000 1001 1002) %ld, of (1002 1000 1001) %ld, of root's %ld, of a zombie %ld; "
                "getpriority of (1000 1000 1000) %ld, of root's %ld\n",
                w, e, e2, f, g, z, g4, g5);
        }
    }
    {
        struct sched_param one = { 1 }, zero = { 0 };
        long a = rc(SYS_sched_getscheduler, 0, 0, 0, 0, 0);
        long b = rc(SYS_sched_setscheduler, 0, SCHED_FIFO, (long)&one, 0, 0);
        long c = rc(SYS_sched_getscheduler, 0, 0, 0, 0, 0);
        long d = rc(SYS_sched_setscheduler, 0, SCHED_RR, (long)&one, 0, 0);
        long e = rc(SYS_sched_setscheduler, 0, SCHED_OTHER, (long)&zero, 0, 0);
        long f = rc(SYS_sched_getscheduler, 0, 0, 0, 0, 0);
        long g = rc(SYS_sched_setscheduler, 0, SCHED_OTHER, (long)&one, 0, 0);
        long h = rc(SYS_sched_setscheduler, 999999, SCHED_OTHER, (long)&zero, 0, 0);
        say("%s: sched_getscheduler %ld; SCHED_FIFO 1 %ld (%ld), SCHED_RR 1 %ld, SCHED_OTHER 0 %ld (%ld), SCHED_OTHER 1 %ld, of no process %ld\n", w, a, b,
            c, d, e, f, g, h);
        if (others) {
            long i = rc(SYS_sched_setscheduler, T[0].pid, SCHED_OTHER, (long)&zero, 0, 0);
            long i2 = rc(SYS_sched_setscheduler, T[2].pid, SCHED_OTHER, (long)&zero, 0, 0);
            long k = rc(SYS_sched_setscheduler, T[4].pid, SCHED_OTHER, (long)&zero, 0, 0);
            long j = rc(SYS_sched_getscheduler, T[4].pid, 0, 0, 0, 0);
            say("%s: SCHED_OTHER 0 of (1000 1000 1000) %ld, of (1000 1001 1002) %ld, of root's %ld; root's policy %ld\n", w, i, i2, k, j);
        }
    }
    {
        long a = rc(SYS_chroot, (long)"/", 0, 0, 0, 0);
        long b = rc(SYS_chroot, (long)"/no/such", 0, 0, 0, 0);
        long c = rc(SYS_chroot, (long)"/etc/passwd", 0, 0, 0, 0);
        long d = rc(SYS_reboot, 1, 2, 3, 0, 0);
        long e = rc(SYS_sethostname, (long)"px45", 100, 0, 0, 0);
        struct timespec ts = { 1, 0 };
        long f = rc(SYS_clock_settime, CLOCK_MONOTONIC, (long)&ts, 0, 0, 0);
        long g = rc(SYS_umount2, (long)"/no/such", 0, 0, 0, 0);
        say("%s: chroot(\"/\") %ld, of a missing directory %ld, of a file %ld; reboot with a bad magic %ld; sethostname of 100 bytes %ld; "
            "clock_settime(CLOCK_MONOTONIC) %ld; umount2 of a missing path %ld\n",
            w, a, b, c, d, e, f, g);
    }
    if (P->e != 0) {
        /* refused for a user; for root each would change the machine */
        struct timespec ts = { 1, 0 };
        struct timeval tv = { 1, 0 };
        long a = rc(SYS_clock_settime, CLOCK_REALTIME, (long)&ts, 0, 0, 0);
        long b = rc(SYS_settimeofday, (long)&tv, 0, 0, 0, 0);
        long c = rc(SYS_sethostname, (long)"px45", 4, 0, 0, 0);
        long d = rc(SYS_reboot, 0xfee1dead, 672274793, 0x4321fedc, 0, 0); /* LINUX_REBOOT_CMD_POWER_OFF */
        long e = rc(SYS_reboot, 0xfee1dead, 672274793, 0x01234567, 0, 0); /* LINUX_REBOOT_CMD_RESTART */
        long f = rc(SYS_mount, (long)"none", (long)"/t", (long)"tmpfs", 0, 0);
        long g = rc(SYS_umount2, (long)"/t", 0, 0, 0, 0);
        long h = rc(SYS_mknod, (long)"/t/px45-node", S_IFCHR | 0666, makedev(1, 3), 0, 0);
        say("%s: clock_settime %ld, settimeofday %ld, sethostname %ld, reboot (power off) %ld, (restart) %ld, mount %ld, umount2 %ld, "
            "mknod of a character device %ld\n",
            w, a, b, c, d, e, f, g, h);
    }
    if (tty0 >= 0) {
        long a = rc(SYS_ioctl, tty0, KIOCSOUND, 0, 0, 0);
        long b = rc(SYS_ioctl, tty0, KDMKTONE, 0, 0, 0);
        long c = rc(SYS_open, (long)"/dev/tty0", O_RDWR | O_NOCTTY | O_NONBLOCK, 0, 0, 0);
        if (c >= 0) close((int)c);
        say("%s: on /dev/tty0 as root opened it: KIOCSOUND 0 %ld, KDMKTONE 0 %ld; its own open of /dev/tty0 %ld\n", w, a, b, c >= 0 ? 0 : c);
    } else say("%s: no /dev/tty0 (%d)\n", w, tty0);
}

/* --- D: /dev's nodes ------------------------------------------------------------ */

static const char *const DEV[] = { "/dev/null", "/dev/zero", "/dev/full", "/dev/random", "/dev/urandom", "/dev/tty", "/dev/tty0", "/dev/console", "/dev/ttyS0" };
enum { ND = sizeof DEV / sizeof *DEV };

static void dev_modes(void)
{
    say("== D: /dev's nodes\n");
    for (int i = 0; i < ND; i++) {
        struct stat s;
        if (stat(DEV[i], &s) == 0) say("node %s: %u:%u %o, %u:%u\n", DEV[i], s.st_uid, s.st_gid, s.st_mode, major(s.st_rdev), minor(s.st_rdev));
        else say("node %s: %d\n", DEV[i], -errno);
    }
}

static void dev_rows(const char *w)
{
    char line[1024];
    int n = snprintf(line, sizeof line, "%s: open read, write, access(R|W):", w);
    for (int i = 0; i < ND; i++) {
        if (i == 5) continue; /* /dev/tty: Linux's probe has no controlling terminal, and every PAX process's is the console */
        long r = rc(SYS_open, (long)DEV[i], O_RDONLY | O_NOCTTY | O_NONBLOCK, 0, 0, 0);
        if (r >= 0) { close((int)r); r = 0; }
        long x = rc(SYS_open, (long)DEV[i], O_WRONLY | O_NOCTTY | O_NONBLOCK, 0, 0, 0);
        if (x >= 0) { close((int)x); x = 0; }
        long a = rc(SYS_access, (long)DEV[i], R_OK | W_OK, 0, 0, 0);
        n += snprintf(line + n, sizeof line - n, " %s %ld %ld %ld", DEV[i] + 5, r, x, a);
    }
    say("%s\n", line);
    {
        unsigned char b[16];
        memset(b, 7, sizeof b);
        int fd = open("/dev/zero", O_RDONLY);
        long r = fd < 0 ? -errno : read(fd, b, sizeof b);
        int z = 1;
        for (int i = 0; i < 16; i++) z &= b[i] == 0;
        if (fd >= 0) close(fd);
        fd = open("/dev/full", O_RDWR);
        long f = fd < 0 ? -errno : rc(SYS_write, fd, (long)"x", 1, 0, 0);
        memset(b, 7, sizeof b);
        long fr = fd < 0 ? -errno : read(fd, b, 4);
        int fz = b[0] == 0 && b[3] == 0;
        if (fd >= 0) close(fd);
        fd = open("/dev/urandom", O_RDONLY);
        long u = fd < 0 ? -errno : read(fd, b, sizeof b);
        if (fd >= 0) close(fd);
        fd = open("/dev/random", O_RDONLY | O_NONBLOCK);
        long rr = fd < 0 ? -errno : read(fd, b, 8);
        if (fd >= 0) close(fd);
        fd = open("/dev/null", O_WRONLY);
        long nw = fd < 0 ? -errno : rc(SYS_write, fd, (long)"abc", 3, 0, 0);
        if (fd >= 0) close(fd);
        say("%s: read /dev/zero %ld (%s), write /dev/full %ld, read it %ld (%s), read /dev/urandom %ld, /dev/random %ld, write /dev/null %ld\n", w,
            r, z ? "zeros" : "not zeros", f, fr, fz ? "zeros" : "not zeros", u, rr, nw);
    }
}

/* --- R: /proc/<pid> by owner -------------------------------------------------- */

static long rdall(const char *p, char *b, long cap)
{
    int fd = open(p, O_RDONLY);
    if (fd < 0) return -(long)errno;
    long k = 0, r = 0;
    while (k < cap && (r = read(fd, b + k, cap - k)) > 0) k += r;
    long e = r < 0 ? -(long)errno : k;
    close(fd);
    return e;
}
static const char *own(const char *p)
{
    static char o[4][48];
    static int i;
    char *s = o[i++ & 3];
    struct stat st;
    if (lstat(p, &st) == 0) snprintf(s, 48, "%u:%u %o", st.st_uid, st.st_gid, st.st_mode & 07777);
    else snprintf(s, 48, "%d", -errno);
    return s;
}
static void text(char *o, long cap, const char *b, long n)
{
    long k = 0;
    for (long i = 0; i < n && k < cap - 1; i++) o[k++] = b[i] == 0 ? '|' : (b[i] < 32 || b[i] > 126) ? '?' : b[i];
    o[k] = 0;
}

static void read_row(const long R[4], int i)
{
    pid_t p = fork();
    if (p == 0) {
        if (R[0] != 0 || R[1] != 0) { become_state(R); }
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        if (R[3] >= 0) rc(SYS_setfsuid, R[3], 0, 0, 0, 0);
        char d[64], f[96], b[512], cl[160], en[160];
        snprintf(d, sizeof d, "/proc/%d", T[i].pid);
        snprintf(f, sizeof f, "%s/status", d);
        long st = rdall(f, b, sizeof b);
        char so[48], co[48];
        snprintf(so, sizeof so, "%s", own(f));
        snprintf(f, sizeof f, "%s/cmdline", d);
        snprintf(co, sizeof co, "%s", own(f));
        long cm = rdall(f, b, sizeof b);
        text(cl, sizeof cl, b, cm > 0 ? cm : 0);
        snprintf(f, sizeof f, "%s/environ", d);
        long ev = rdall(f, b, sizeof b);
        text(en, sizeof en, b, ev > 0 ? ev : 0);
        char eo[48];
        snprintf(eo, sizeof eo, "%s", own(f));
        snprintf(f, sizeof f, "%s/fd", d);
        char fo[48];
        snprintf(fo, sizeof fo, "%s", own(f));
        int fd = open(f, O_RDONLY | O_DIRECTORY);
        long lf = fd < 0 ? -(long)errno : 0;
        int nent = 0;
        if (fd >= 0) {
            DIR *dd = fdopendir(fd);
            struct dirent *de;
            while (dd && (de = readdir(dd))) if (de->d_name[0] != '.') nent++;
            if (dd) closedir(dd);
        }
        if (T[i].how != 1 && ev > 0) snprintf(en, sizeof en, "(what %s holds)", SELF); /* inherited: the machine's own start */
        say("reader (%4ld %4ld %4ld fs %4ld) of %s: dir %s; status %s %s; cmdline %s %ld '%s'; environ %s %s '%s'; fd/ %s open %ld",
            R[0], R[1], R[2], R[3] >= 0 ? R[3] : R[1], T[i].name, own(d), so, st >= 0 ? "read" : "-", co, cm, cl, eo,
            ev > 0 && T[i].how != 1 ? "read" : (snprintf(f, sizeof f, "%ld", ev), f), en, fo, lf);
        if (T[i].how == 1 && lf == 0) say(" (%d entries)", nent);
        say("\n");
        if (st < 0) say("! status %ld\n", st);
        _exit(0);
    }
    reap(p);
}

static void proc_rows(void)
{
    say("== R: /proc/<pid> by owner: status, cmdline, environ, fd/\n");
    static const long RD[][4] = {
        { 1000, 1000, 1000, -1 }, { 1001, 1001, 1001, -1 }, { 1002, 1002, 1002, -1 }, { 0, 0, 0, -1 },
        { 1000, 1001, 1001, -1 }, { 1003, 1000, 1003, -1 }, { 1000, 1003, 1003, 1000 }, { 0, 1000, 0, -1 }, { 0, 0, 0, 1002 },
    };
    for (int i = 0; i < NT; i++)
        for (unsigned r = 0; r < sizeof RD / sizeof *RD; r++) read_row(RD[r], i);
}

/* --- C: SO_PEERCRED --------------------------------------------------------- */

static void peer_line(const char *what, int fd, pid_t mine, pid_t theirs, socklen_t want)
{
    unsigned uc[3] = { 7, 7, 7 };
    socklen_t len = want;
    long r = rc(SYS_getsockopt, fd, SOL_SOCKET, SO_PEERCRED, (long)uc, (long)&len);
    const char *pw = (pid_t)uc[0] == mine ? "its own" : (pid_t)uc[0] == theirs ? "the peer's" : uc[0] == 0 ? "0" : uc[0] == 7 ? "untouched" : "another";
    say("%s: SO_PEERCRED %ld, len %u: pid %s, uid %d, gid %d\n", what, r, (unsigned)len, pw, (int)uc[1], (int)uc[2]);
}

static void cred_rows(void)
{
    say("== C: SO_PEERCRED\n");
    {
        int sv[2];
        long r = rc(SYS_socketpair, AF_UNIX, SOCK_STREAM, 0, (long)sv, 0);
        if (r == 0) {
            peer_line("socketpair by root, end 0", sv[0], getpid(), -1, 12);
            peer_line("socketpair by root, end 1", sv[1], getpid(), -1, 12);
            peer_line("the same, a length of 8", sv[0], getpid(), -1, 8);
            peer_line("the same, a length of 16", sv[0], getpid(), -1, 16);
            pid_t p = fork();
            if (p == 0) {
                become_state((const long[3]){ 1002, 1002, 1002 });
                peer_line("its end held by a child that became 1002", sv[1], getpid(), getppid(), 12);
                _exit(0);
            }
            reap(p);
            close(sv[0]);
            close(sv[1]);
        } else say("socketpair %ld\n", r);
    }
    {
        pid_t p = fork();
        if (p == 0) {
            rc(SYS_setgroups, 0, 0, 0, 0, 0);
            rc(SYS_setresgid, 2001, 2002, 2003, 0, 0);
            rc(SYS_setresuid, 1001, 1002, 1003, 0, 0);
            int sv[2];
            long r = rc(SYS_socketpair, AF_UNIX, SOCK_SEQPACKET, 0, (long)sv, 0);
            if (r == 0) peer_line("a SOCK_SEQPACKET socketpair by (1001 1002 1003) gids (2001 2002 2003)", sv[0], getpid(), -1, 12);
            else say("socketpair seqpacket %ld\n", r);
            rc(SYS_setfsuid, 1003, 0, 0, 0, 0);
            rc(SYS_setfsgid, 2003, 0, 0, 0, 0);
            r = rc(SYS_socketpair, AF_UNIX, SOCK_STREAM, 0, (long)sv, 0);
            if (r == 0) peer_line("the same after setfsuid(1003), setfsgid(2003)", sv[0], getpid(), -1, 12);
            else say("socketpair %ld\n", r);
            _exit(0);
        }
        reap(p);
    }
    {
        int s = socket(AF_UNIX, SOCK_STREAM, 0);
        peer_line("an AF_UNIX socket never connected", s, getpid(), -1, 12);
        close(s);
    }
    {
        /* a listener that root made and then left (1001 1001 1001), and a connector (1002 1003 1002) */
        unlink("/t/px45-sock");
        int go[2], ready[2];
        if (pipe(go) != 0 || pipe(ready) != 0) _exit(95);
        pid_t l = fork();
        if (l == 0) {
            close(go[1]); close(ready[0]);
            rc(SYS_setgroups, 0, 0, 0, 0, 0);
            rc(SYS_setresgid, 2001, 2001, 2001, 0, 0);
            umask(0); /* the name 0777: anyone may connect (px44) */
            int s = socket(AF_UNIX, SOCK_STREAM, 0);
            struct sockaddr_un a;
            memset(&a, 0, sizeof a);
            a.sun_family = AF_UNIX;
            strcpy(a.sun_path, "/t/px45-sock");
            long b = bind(s, (struct sockaddr *)&a, sizeof a) == 0 ? 0 : -errno;
            long ls = listen(s, 4) == 0 ? 0 : -errno;
            rc(SYS_setresuid, 1001, 1001, 1001, 0, 0); /* after listen: a peer is told the ids it had then */
            peer_line("a listener before anyone connects", s, getpid(), -1, 12);
            if (write(ready[1], "k", 1) != 1) _exit(94);
            int c = accept(s, NULL, NULL);
            char ch;
            if (read(go[0], &ch, 1) != 1) _exit(94);
            say("listener (bound %ld, listening %ld as root, then 1001): ", b, ls);
            peer_line("its accepted end", c, getpid(), -2, 12);
            _exit(0);
        }
        close(go[0]); close(ready[1]);
        char ch;
        if (read(ready[0], &ch, 1) != 1) say("! the listener did not settle\n");
        pid_t k = fork();
        if (k == 0) {
            rc(SYS_setgroups, 0, 0, 0, 0, 0);
            rc(SYS_setresgid, 2002, 2003, 2002, 0, 0);
            rc(SYS_setresuid, 1002, 1003, 1002, 0, 0);
            int s = socket(AF_UNIX, SOCK_STREAM, 0);
            struct sockaddr_un a;
            memset(&a, 0, sizeof a);
            a.sun_family = AF_UNIX;
            strcpy(a.sun_path, "/t/px45-sock");
            long r = connect(s, (struct sockaddr *)&a, sizeof a) == 0 ? 0 : -errno;
            say("connector (1002 1003 1002) gids (2002 2003 2002), connect %ld: ", r);
            peer_line("its end", s, getpid(), l, 12);
            if (write(go[1], "k", 1) != 1) _exit(94);
            nap(200);
            _exit(0);
        }
        reap(k);
        reap(l);
        close(go[1]);
        close(ready[0]);
        unlink("/t/px45-sock");
    }
    {
        int s = socket(AF_INET, SOCK_STREAM, 0);
        peer_line("an AF_INET stream socket", s, getpid(), -1, 12);
        close(s);
        s = socket(AF_INET, SOCK_DGRAM, 0);
        peer_line("an AF_INET datagram socket", s, getpid(), -1, 12);
        close(s);
    }
}

/* --- the user's own rows ------------------------------------------------------ */

static void user_rows(void)
{
    struct pstate me = { getuid(), geteuid(), getuid(), "self          " };
    /* a target of its own, for the signal and /proc rows */
    T[0].pid = start(&T[0]);
    say("== P: what only root may do, asked by itself\n");
    tty0 = -1;
    priv_rows(&me, 0);
    say("== D: /dev's nodes, opened by itself\n");
    dev_rows("self");
    say("== R: /proc of its own child and of itself\n");
    {
        char f[96], b[256], o[160];
        snprintf(f, sizeof f, "/proc/%d/environ", T[0].pid);
        long n = rdall(f, b, sizeof b);
        text(o, sizeof o, b, n > 0 ? n : 0);
        say("its child's environ %s %ld '%s'; ", own(f), n, o);
        n = rdall("/proc/self/cmdline", b, sizeof b);
        text(o, sizeof o, b, n > 0 ? n : 0);
        say("its own cmdline %ld '%s'\n", n, o);
    }
    say("== S: signals to its own child\n");
    {
        pid_t t = T[0].pid;
        say("kill 0 %ld, tgkill 0 %ld, tkill 0 %ld, SIGWINCH %ld; kill(0, 0) %ld\n", rc(SYS_kill, t, 0, 0, 0, 0), rc(SYS_tgkill, t, t, 0, 0, 0),
            rc(SYS_tkill, t, 0, 0, 0, 0), rc(SYS_kill, t, SIGWINCH, 0, 0, 0), rc(SYS_kill, 0, 0, 0, 0, 0));
    }
    say("== C: SO_PEERCRED of its own socketpair\n");
    {
        int sv[2];
        if (rc(SYS_socketpair, AF_UNIX, SOCK_STREAM, 0, (long)sv, 0) == 0) {
            peer_line("its socketpair", sv[0], getpid(), -1, 12);
            close(sv[0]);
            close(sv[1]);
        }
    }
    kill(T[0].pid, SIGKILL);
    reap(T[0].pid);
}

/* --- the soak ------------------------------------------------------------------ */

static long memfree(void)
{
    return atol(status_line("/proc/meminfo", "MemFree"));
}
static int soak(long n, long as_uid)
{
    long tid = as_uid >= 0 ? 0 : 1002; /* root's target for a user's soak; 1002's for root's */
    int life[2];
    if (pipe(life) != 0) return 1;
    pid_t t = fork();
    if (t == 0) {
        close(life[1]);
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
        if (rc(SYS_setresuid, tid, tid, tid, 0, 0) != 0) _exit(99);
        char ch;
        while (read(life[0], &ch, 1) > 0) ; /* ends when the soak does */
        _exit(0);
    }
    close(life[0]);
    if (as_uid >= 0) {
        unsigned none[1] = { 0 };
        become(as_uid, as_uid, 0, none);
    }
    unsigned me = getuid();
    int root = geteuid() == 0;
    long wrong = 0, calls = 0, mem[5] = { 0, 0, 0, 0, 0 };
    char envp[64];
    snprintf(envp, sizeof envp, "/proc/%d/environ", t);
    int sv[2];
    if (rc(SYS_socketpair, AF_UNIX, SOCK_STREAM, 0, (long)sv, 0) != 0) { say("! soak: socketpair\n"); return 1; }
    mem[0] = memfree();
    for (long i = 0; i < n; i++) {
        wrong += rc(SYS_kill, t, SIGWINCH, 0, 0, 0) != (root ? 0 : -1);
        wrong += rc(SYS_tgkill, t, t, 0, 0, 0) != (root ? 0 : -1);
        wrong += rc(SYS_kill, getpid(), SIGWINCH, 0, 0, 0) != 0;
        wrong += bind_port(SOCK_STREAM, 80, 0) != (root ? 0 : -13);
        long p = rc(SYS_setpriority, PRIO_PROCESS, 0, -1, 0, 0);
        wrong += p != (root ? 0 : -13);
        rc(SYS_setpriority, PRIO_PROCESS, 0, 0, 0, 0);
        long c = rc(SYS_open, (long)"/dev/console", O_WRONLY | O_NOCTTY, 0, 0, 0);
        if (c >= 0) { close((int)c); c = 0; }
        wrong += c != (root ? 0 : -13);
        char b[64];
        wrong += (rdall(envp, b, sizeof b) >= 0) != root;
        unsigned uc[3];
        socklen_t len = 12;
        wrong += rc(SYS_getsockopt, sv[0], SOL_SOCKET, SO_PEERCRED, (long)uc, (long)&len) != 0 || uc[1] != geteuid();
        wrong += rc(SYS_chroot, (long)"/", 0, 0, 0, 0) != (root ? 0 : -1);
        wrong += rc(SYS_reboot, 1, 2, 3, 0, 0) != (root ? -22 : -1);
        calls += 10;
        if (n >= 4 && (i + 1) % (n / 4) == 0 && (i + 1) / (n / 4) <= 4) mem[(i + 1) / (n / 4)] = memfree();
    }
    close(sv[0]);
    close(sv[1]);
    close(life[1]);
    reap(t);
    say("soak: %ld rounds, %ld calls that signal, bind a low port, lower a priority, open a 0600 node, read another's environ, ask SO_PEERCRED, "
        "chroot and reboot, %ld wrong answers, as uid %u\n",
        n, calls, wrong, me);
    say("~soak: MemFree before %ld kB, at each quarter %ld %ld %ld %ld kB\n", mem[0], mem[1], mem[2], mem[3], mem[4]);
    return wrong ? 1 : 0;
}

int main(int argc, char **argv)
{
    if (argc > 2 && strcmp(argv[1], "wait") == 0) {
        int fd = atoi(argv[2]);
        if (write(fd, "k", 1) != 1) return 94;
        close(fd);
        for (;;) nap(100000);
    }
    if (argc > 2 && strcmp(argv[1], "soak") == 0) return soak(atol(argv[2]), argc > 3 ? atol(argv[3]) : -1);
    alone = argc > 1 && strcmp(argv[1], "user") == 0;
    if (!alone && getuid() != 0) { say("usage: rights (as root) | rights user | rights soak N [UID]\n"); return 2; }
    umask(022);
    say("rights: uid %s gid %s groups '%s'\n", uids(), gids(), groups());
    {
        char b[16] = "?";
        int s = open("/proc/sys/net/ipv4/ip_unprivileged_port_start", O_RDONLY);
        if (s >= 0) { long k = read(s, b, sizeof b - 1); if (k > 0) b[k - 1] = 0; close(s); }
        say("settings: net.ipv4.ip_unprivileged_port_start %s, %s\n", b, own("/proc/sys/net/ipv4/ip_unprivileged_port_start"));
    }
    if (alone) {
        user_rows();
        say("rights: done\n");
        return 0;
    }
    for (int i = 0; i < NT; i++) {
        T[i].pid = start(&T[i]);
        char b[64];
        snprintf(b, sizeof b, "/proc/%d/status", T[i].pid);
        say("target %s: uid %s\n", T[i].name, status_line(b, "Uid"));
    }
    send_rows();
    other_rows();
    handler_rows();

    say("== P: what only root may do\n");
    tty0 = open("/dev/tty0", O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (tty0 < 0) tty0 = -errno;
    {
        long h = bind_port(SOCK_STREAM, 81, 1); /* root holds 81: a user's bind of it is told the port first or the privilege first */
        for (int i = 0; i < NPS; i++) {
            pid_t p = fork();
            if (p == 0) {
                if (PS[i].r != 0 || PS[i].e != 0) become_state((const long[3]){ PS[i].r, PS[i].e, PS[i].s });
                else rc(SYS_setgroups, 0, 0, 0, 0, 0);
                priv_rows(&PS[i], 1);
                _exit(0);
            }
            reap(p);
        }
        if (h >= 0) close((int)h);
    }
    if (tty0 >= 0) close(tty0);

    dev_modes();
    for (int i = 0; i < 2; i++) {
        pid_t p = fork();
        if (p == 0) {
            if (i == 1) become_state((const long[3]){ 1000, 1000, 1000 });
            dev_rows(i == 0 ? "root" : "user");
            _exit(0);
        }
        reap(p);
    }

    proc_rows();
    cred_rows();
    stop_all();
    say("rights: done\n");
    return 0;
}
