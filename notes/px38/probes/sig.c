/* sig.c — px38, item 2(d): who may signal whom, and what /proc/<pid>
 * shows to whom. Root starts target processes in chosen states; senders
 * and viewers are fresh children that became someone for good.
 *
 *   sig DIR           DIR on a tmpfs without nosuid (a set-ID copy is made)
 *   sig wait          (a target: sleeps until killed)
 *   sig show TAG      (unused; kept for symmetry)
 */
#include "px38.h"
#include <dirent.h>
#include <sys/prctl.h>

static const char *D;
static char self[256];

/* A target: root forks; the child takes (r, e, s), then (how 1) execs
 * `self wait` so it is an ordinary dumpable process, or (how 0) just
 * sleeps, or (how 2) is uid 1000 and execs a set-user-ID copy owned by
 * 1001. Returns its pid once it is settled. */
static pid_t target(long r, long e, long s, int how)
{
    int pfd[2];
    if (pipe(pfd) != 0) _exit(95);
    pid_t p = fork();
    if (p == 0) {
        close(pfd[0]);
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
        if (rc(SYS_setresuid, r, e, s, 0, 0) != 0) _exit(99);
        if (how == 0) {
            if (write(pfd[1], "k", 1) != 1) _exit(94);
            for (;;) pause();
        }
        char fdarg[16], path[600];
        snprintf(fdarg, sizeof fdarg, "%d", pfd[1]);
        snprintf(path, sizeof path, "%s", how == 2 ? D : self);
        if (how == 2) snprintf(path, sizeof path, "%s/sig-suid", D);
        char *av[] = { path, (char *)"wait", fdarg, NULL };
        char *ev[] = { (char *)"SECRET=px38", NULL };
        execve(path, av, ev);
        _exit(98);
    }
    close(pfd[1]);
    char c;
    if (read(pfd[0], &c, 1) != 1) say("! a target did not settle\n");
    close(pfd[0]);
    return p;
}

static void send_row(const long S[3], pid_t t, const char *tname)
{
    pid_t p = fork();
    if (p == 0) {
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
        if (rc(SYS_setresuid, S[0], S[1], S[2], 0, 0) != 0) _exit(99);
        long a = rc(SYS_kill, t, 0, 0, 0, 0);
        long b = rc(SYS_tgkill, t, t, 0, 0, 0);
        long c = rc(SYS_kill, t, SIGCONT, 0, 0, 0);
        long d = rc(SYS_kill, t, SIGURG, 0, 0, 0); /* ignored by default: harmless when it lands */
        say("sender (%4ld %4ld %4ld) -> target %s: kill(pid, 0) %ld, tgkill(pid, pid, 0) %ld, SIGCONT %ld, SIGURG %ld\n", S[0], S[1], S[2],
            tname, a, b, c, d);
        _exit(0);
    }
    reap(p);
}

static long rd(const char *p)
{
    char b[64];
    int fd = open(p, O_RDONLY);
    if (fd < 0) return -(long)errno;
    long n = read(fd, b, sizeof b);
    long e = n < 0 ? -(long)errno : 0;
    close(fd);
    return e;
}
static long rl(const char *p)
{
    char b[256];
    return readlink(p, b, sizeof b) < 0 ? -(long)errno : 0;
}

static void view_row(long uid, pid_t t, const char *tname)
{
    pid_t p = fork();
    if (p == 0) {
        if (uid != 0) { rc(SYS_setgroups, 0, 0, 0, 0, 0); rc(SYS_setresgid, 2999, 2999, 2999, 0, 0); rc(SYS_setresuid, uid, uid, uid, 0, 0); }
        char b[96], o[14][64];
        struct stat s;
        snprintf(b, sizeof b, "/proc/%d", t);
        if (stat(b, &s) == 0) snprintf(o[0], 64, "%u:%u %o", s.st_uid, s.st_gid, s.st_mode & 07777);
        else snprintf(o[0], 64, "%d", -errno);
        const char *files[] = { "status", "stat", "cmdline", "environ", "maps", "mem", "auxv", "io", "limits" };
        long r[9];
        for (int i = 0; i < 9; i++) { snprintf(b, sizeof b, "/proc/%d/%s", t, files[i]); r[i] = rd(b); }
        snprintf(b, sizeof b, "/proc/%d/exe", t); long le = rl(b);
        snprintf(b, sizeof b, "/proc/%d/cwd", t); long lc = rl(b);
        snprintf(b, sizeof b, "/proc/%d/root", t); long lr = rl(b);
        snprintf(b, sizeof b, "/proc/%d/fd", t);
        int fd = open(b, O_RDONLY | O_DIRECTORY);
        long lf = fd < 0 ? -(long)errno : 0;
        if (fd >= 0) close(fd);
        snprintf(b, sizeof b, "/proc/%d/environ", t);
        if (stat(b, &s) == 0) snprintf(o[1], 64, "%u:%u %o", s.st_uid, s.st_gid, s.st_mode & 07777);
        else snprintf(o[1], 64, "%d", -errno);
        say("viewer %4ld of %s: /proc/<pid> is %s; read status %ld stat %ld cmdline %ld environ %ld maps %ld mem %ld auxv %ld io %ld limits %ld; readlink exe %ld cwd %ld root %ld; open fd/ %ld; environ is %s\n",
            uid, tname, o[0], r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], le, lc, lr, lf, o[1]);
        _exit(0);
    }
    reap(p);
}

int main(int argc, char **argv)
{
    if (argc > 2 && strcmp(argv[1], "wait") == 0) {
        int fd = atoi(argv[2]);
        if (write(fd, "k", 1) != 1) return 94;
        close(fd);
        for (;;) pause();
    }
    if (argc < 2) { say("usage: sig DIR\n"); return 2; }
    D = argv[1];
    long n = readlink("/proc/self/exe", self, sizeof self - 1);
    if (n <= 0) return 2;
    self[n] = 0;
    chmod(D, 0755);
    char suid[600];
    snprintf(suid, sizeof suid, "%s/sig-suid", D);
    if (copy_file(self, suid, 0700) != 0 || chown(suid, 1001, 2999) != 0 || chmod(suid, 04755) != 0) { say("! set-ID copy\n"); return 1; }
    {
        static char b[65536];
        int fd = open("/proc/self/mountinfo", O_RDONLY);
        long k = 0, r;
        while (fd >= 0 && k < (long)sizeof b - 1 && (r = read(fd, b + k, sizeof b - 1 - k)) > 0) k += r;
        if (fd >= 0) close(fd);
        b[k] = 0;
        char *l = strstr(b, " /proc ");
        char opt[128] = "?", sup[128] = "?";
        if (l) {
            sscanf(l, " /proc %127s", opt);
            char *dash = strstr(l, " - proc ");
            if (dash) sscanf(dash, " - proc %*s %127s", sup);
        }
        say("/proc is mounted %s (%s)\n", opt, sup);
    }

    struct { long r, e, s; int how; const char *name; } T[] = {
        { 1000, 1000, 1000, 1, "(1000 1000 1000) exec'd " },
        { 1000, 1001, 1002, 1, "(1000 1001 1002) exec'd " }, /* after the execve its saved id is 1001 */
        { 1000, 1001, 1002, 0, "(1000 1001 1002) no exec" },
        { 1002, 1000, 1001, 0, "(1002 1000 1001) no exec" },
        { 1000, 1000, 1000, 2, "1000 ran 04755 of 1001  " }, /* (1000 1001 1001) */
        { 0, 0, 0, 1, "(   0    0    0) exec'd " },
    };
    enum { NT = sizeof T / sizeof *T };
    pid_t pid[NT];
    for (int i = 0; i < NT; i++) {
        pid[i] = target(T[i].r, T[i].e, T[i].s, T[i].how);
        char b[64];
        snprintf(b, sizeof b, "/proc/%d/status", pid[i]);
        char u[256];
        snprintf(u, sizeof u, "%s", status_line(b, "Uid"));
        say("target %s: uid %s\n", T[i].name, u);
    }

    say("== who may signal whom: sender (real effective saved)\n");
    static const long S[][3] = {
        { 1000, 1000, 1000 }, { 1001, 1001, 1001 }, { 1002, 1002, 1002 }, { 1003, 1003, 1003 },
        { 1003, 1000, 1003 }, { 1003, 1001, 1003 }, { 1003, 1002, 1003 },
        { 1000, 1003, 1003 }, { 1001, 1003, 1003 }, { 1002, 1003, 1003 },
        { 1003, 1003, 1000 }, { 1003, 1003, 1001 }, { 1003, 1003, 1002 },
        { 0, 0, 0 }, { 1003, 0, 1003 }, { 0, 1003, 0 }, { 0, 1003, 1003 },
    };
    for (unsigned s = 0; s < sizeof S / sizeof *S; s++)
        for (int i = 0; i < NT; i++) send_row(S[s], pid[i], T[i].name);
    {
        pid_t p = fork();
        if (p == 0) {
            rc(SYS_setresuid, 1003, 1003, 1003, 0, 0);
            say("sender (1003 1003 1003): kill(1, 0) %ld; kill(999999, 0) %ld; kill(-1, 0) %ld; kill(0, 0) %ld; kill(pid, 65) %ld\n",
                rc(SYS_kill, 1, 0, 0, 0, 0), rc(SYS_kill, 999999, 0, 0, 0, 0), rc(SYS_kill, -1, 0, 0, 0, 0), rc(SYS_kill, 0, 0, 0, 0, 0),
                rc(SYS_kill, pid[0], 65, 0, 0, 0));
            _exit(0);
        }
        reap(p);
        p = fork();
        if (p == 0) {
            rc(SYS_setresuid, 1000, 1000, 1000, 0, 0);
            say("sender (1000 1000 1000): kill(1, 0) %ld; kill(-1, 0) %ld (some process may be signalled)\n", rc(SYS_kill, 1, 0, 0, 0, 0),
                rc(SYS_kill, -1, 0, 0, 0, 0));
            _exit(0);
        }
        reap(p);
    }

    say("== what /proc/<pid> shows to whom\n");
    static const long VW[] = { 1000, 1001, 1002, 1003, 0 };
    for (int i = 0; i < NT; i++)
        for (unsigned v = 0; v < sizeof VW / sizeof *VW; v++) view_row(VW[v], pid[i], T[i].name);

    for (int i = 0; i < NT; i++) { kill(pid[i], SIGKILL); reap(pid[i]); }
    unlink(suid);
    say("sig: done\n");
    return 0;
}
