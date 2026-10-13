/* ids.c — px38, item 1: what a kernel answers about identity TODAY,
 * number by number, and whether anything checks a mode or an owner.
 * One static program, the first program on PAX and pid 1 (or a child of
 * it) on Linux, run as root on both. Every line is one question.
 *
 *   ids [WORKDIR]      WORKDIR (default /px38w) is made and removed
 *   ids hello          (what the probe execs of itself: exit 7)
 */
#include "px38.h"
#include <dirent.h>
#include <sys/auxv.h>
#include <sys/prctl.h>
#include <sys/socket.h>

static const char *W = "/px38w";
static char P[512];
static const char *in(const char *n) { snprintf(P, sizeof P, "%s/%s", W, n); return P; }

/* A call that may change the caller for good runs in a child, which
 * prints the answer. */
static void in_child(const char *label, long nr, long a, long b, long c)
{
    pid_t p = fork();
    if (p == 0) {
        long r = rc(nr, a, b, c, 0, 0);
        say("ask: %-26s %3ld = %ld\n", label, nr, r);
        _exit(0);
    }
    if (p < 0) { say("ask: %-26s %3ld : no child (%d)\n", label, nr, -errno); return; }
    reap(p);
}

static void ask(const char *label, long nr, long a, long b, long c)
{
    say("ask: %-26s %3ld = %ld\n", label, nr, rc(nr, a, b, c, 0, 0));
}

static void who(const char *p)
{
    struct stat s;
    if (stat(p, &s) != 0) { say("stat: %-22s %d\n", p, -errno); return; }
    say("stat: %-22s uid %u gid %u mode %o\n", p, s.st_uid, s.st_gid, s.st_mode);
}

static int run_self(const char *path)
{
    pid_t p = fork();
    if (p == 0) {
        char *argv[] = { (char *)path, (char *)"hello", NULL };
        char *envp[] = { NULL };
        execve(path, argv, envp);
        _exit(100 + errno);
    }
    return reap(p);
}

int main(int argc, char **argv)
{
    if (argc > 1 && strcmp(argv[1], "hello") == 0) return 7;
    if (argc > 1) W = argv[1];
    unsigned ids3[3] = { 77, 77, 77 }, gl[4] = { 77, 77, 77, 77 }, one[1] = { 0 };
    unsigned long cap[3] = { 0x20080522, 0, 0 }, capd[6] = { 0 }; /* _LINUX_CAPABILITY_VERSION_3, pid 0 */

    say("ids: the calls, each as root, each a raw syscall\n");
    ask("getuid()", SYS_getuid, 0, 0, 0);
    ask("getgid()", SYS_getgid, 0, 0, 0);
    ask("geteuid()", SYS_geteuid, 0, 0, 0);
    ask("getegid()", SYS_getegid, 0, 0, 0);
    ask("getppid()", SYS_getppid, 0, 0, 0);
    ask("setuid(0)", SYS_setuid, 0, 0, 0);
    ask("setgid(0)", SYS_setgid, 0, 0, 0);
    ask("setreuid(-1, -1)", SYS_setreuid, -1, -1, 0);
    ask("setregid(-1, -1)", SYS_setregid, -1, -1, 0);
    ask("setresuid(-1, -1, -1)", SYS_setresuid, -1, -1, -1);
    ask("setresgid(-1, -1, -1)", SYS_setresgid, -1, -1, -1);
    {
        long r = rc(SYS_getresuid, (long)&ids3[0], (long)&ids3[1], (long)&ids3[2], 0, 0);
        say("ask: %-26s %3d = %ld (%u %u %u)\n", "getresuid(&r, &e, &s)", (int)SYS_getresuid, r, ids3[0], ids3[1], ids3[2]);
        ids3[0] = ids3[1] = ids3[2] = 77;
        r = rc(SYS_getresgid, (long)&ids3[0], (long)&ids3[1], (long)&ids3[2], 0, 0);
        say("ask: %-26s %3d = %ld (%u %u %u)\n", "getresgid(&r, &e, &s)", (int)SYS_getresgid, r, ids3[0], ids3[1], ids3[2]);
    }
    ask("setfsuid(-1)", SYS_setfsuid, -1, 0, 0);
    ask("setfsgid(-1)", SYS_setfsgid, -1, 0, 0);
    ask("getgroups(0, NULL)", SYS_getgroups, 0, 0, 0);
    {
        long r = rc(SYS_getgroups, 4, (long)gl, 0, 0, 0);
        say("ask: %-26s %3d = %ld (first %u)\n", "getgroups(4, list)", (int)SYS_getgroups, r, gl[0]);
    }
    in_child("setgroups(1, {0})", SYS_setgroups, 1, (long)one, 0);
    in_child("setgroups(0, NULL)", SYS_setgroups, 0, 0, 0);
    {
        long r = rc(SYS_capget, (long)cap, (long)capd, 0, 0, 0);
        say("ask: %-26s %3d = %ld (effective %08lx%08lx)\n", "capget(v3, self)", (int)SYS_capget, r,
            (unsigned long)(((unsigned *)capd)[3]), (unsigned long)(((unsigned *)capd)[0]));
    }
    ask("prctl(PR_GET_DUMPABLE)", SYS_prctl, PR_GET_DUMPABLE, 0, 0);
    ask("prctl(PR_GET_KEEPCAPS)", SYS_prctl, PR_GET_KEEPCAPS, 0, 0);
    ask("prctl(PR_GET_NO_NEW_PRIVS)", SYS_prctl, PR_GET_NO_NEW_PRIVS, 0, 0);
    ask("prctl(PR_GET_SECUREBITS)", SYS_prctl, PR_GET_SECUREBITS, 0, 0);
    ask("getpgrp()", SYS_getpgrp, 0, 0, 0);
    ask("getpgid(0)", SYS_getpgid, 0, 0, 0);
    ask("getsid(0)", SYS_getsid, 0, 0, 0);
    in_child("setpgid(0, 0)", SYS_setpgid, 0, 0, 0);
    in_child("setsid()", SYS_setsid, 0, 0, 0);
    say("ids: the calls a user who is not root would be made by, each in a child\n");
    in_child("setuid(1000)", SYS_setuid, 1000, 0, 0);
    in_child("setgid(1000)", SYS_setgid, 1000, 0, 0);
    in_child("setreuid(1000, 1000)", SYS_setreuid, 1000, 1000, 0);
    in_child("setregid(1000, 1000)", SYS_setregid, 1000, 1000, 0);
    in_child("setresuid(1000,1000,1000)", SYS_setresuid, 1000, 1000, 1000);
    in_child("setresgid(1000,1000,1000)", SYS_setresgid, 1000, 1000, 1000);
    in_child("setfsuid(1000)", SYS_setfsuid, 1000, 0, 0);
    in_child("setfsgid(1000)", SYS_setfsgid, 1000, 0, 0);
    {
        pid_t p = fork();
        if (p == 0) {
            long a = rc(SYS_setuid, 1000, 0, 0, 0, 0);
            say("after setuid(1000) = %ld: getuid %ld geteuid %ld\n", a,
                rc(SYS_getuid, 0, 0, 0, 0, 0), rc(SYS_geteuid, 0, 0, 0, 0, 0));
            _exit(0);
        }
        reap(p);
    }

    say("ids: what a process is told\n");
    say("auxv: AT_UID %lu AT_EUID %lu AT_GID %lu AT_EGID %lu AT_SECURE %lu\n", getauxval(AT_UID), getauxval(AT_EUID),
        getauxval(AT_GID), getauxval(AT_EGID), getauxval(AT_SECURE));
    {
        const char *names[] = { "Uid", "Gid", "Groups", "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs" };
        for (unsigned i = 0; i < sizeof names / sizeof *names; i++) {
            const char *v = status_line("/proc/self/status", names[i]);
            /* the highest capability a kernel has differs by version: a full set is said as one */
            say("status: %s: %s\n", names[i], v);
        }
    }
    {
        int sv[2];
        long r = rc(SYS_socketpair, AF_UNIX, SOCK_STREAM, 0, (long)sv, 0);
        if (r == 0) {
            unsigned uc[3] = { 77, 77, 77 };
            unsigned len = sizeof uc;
            r = rc(SYS_getsockopt, sv[0], SOL_SOCKET, SO_PEERCRED, (long)uc, (long)&len);
            say("peer: SO_PEERCRED on a socketpair %ld (uid %u gid %u)\n", r, uc[1], uc[2]);
            close(sv[0]); close(sv[1]);
        } else say("peer: socketpair %ld\n", r);
    }

    say("ids: what a file is said to belong to\n");
    who("/");
    who("/bin");
    who("/dev/null");
    who("/proc");
    who("/proc/self");
    who("/proc/self/status");
    who("/proc/1");

    say("ids: whether anything checks (as root: Linux lets root past every check but one)\n");
    rmdir(W);
    if (mkdir(W, 0755) != 0) { say("! mkdir %s: %d\n", W, -errno); return 1; }
    {
        int fd = open(in("f"), O_WRONLY | O_CREAT | O_EXCL, 0644);
        if (fd < 0 || write(fd, "x\n", 2) != 2) { say("! file: %d\n", -errno); return 1; }
        close(fd);
        struct stat s;
        stat(in("f"), &s);
        say("made: a file is owned %u:%u\n", s.st_uid, s.st_gid);
        say("chown: to 1000:1000 %ld", rc(SYS_chown, (long)in("f"), 1000, 1000, 0, 0));
        stat(in("f"), &s);
        say(", then owned %u:%u\n", s.st_uid, s.st_gid);
        say("chown: back to 0:0 %ld\n", rc(SYS_chown, (long)in("f"), 0, 0, 0, 0));
        chmod(in("f"), 0);
        say("mode 0000 file: open O_RDONLY %ld", (fd = open(in("f"), O_RDONLY)) >= 0 ? 0L : -(long)errno);
        if (fd >= 0) close(fd);
        say(", O_WRONLY %ld", (fd = open(in("f"), O_WRONLY)) >= 0 ? 0L : -(long)errno);
        if (fd >= 0) close(fd);
        say(", access(R_OK|W_OK) %ld, access(X_OK) %ld\n", rc(SYS_access, (long)in("f"), 6, 0, 0, 0),
            rc(SYS_access, (long)in("f"), 1, 0, 0, 0));
        mkdir(in("d"), 0755);
        fd = open(in("d/in"), O_WRONLY | O_CREAT, 0644);
        if (fd >= 0) close(fd);
        chmod(in("d"), 0);
        say("mode 0000 directory: stat of a name in it %ld", stat(in("d/in"), &s) == 0 ? 0L : -(long)errno);
        say(", a file made in it %ld", (fd = open(in("d/new"), O_WRONLY | O_CREAT, 0644)) >= 0 ? 0L : -(long)errno);
        if (fd >= 0) close(fd);
        say(", opened to list %ld\n", (fd = open(in("d"), O_RDONLY | O_DIRECTORY)) >= 0 ? 0L : -(long)errno);
        if (fd >= 0) close(fd);
        chmod(in("d"), 0755);
        unlink(in("d/new")); unlink(in("d/in")); rmdir(in("d"));
        unlink(in("f"));
    }
    {
        /* execve and the mode: the probe's own file (a program written
         * since boot is refused on PAX whatever its mode). */
        char self[256];
        long n = readlink("/proc/self/exe", self, sizeof self - 1);
        if (n > 0) {
            self[n] = 0;
            struct stat s;
            stat(self, &s);
            unsigned was = s.st_mode & 07777;
            long c0 = chmod(self, 0644) == 0 ? 0L : -(long)errno;
            int r0 = run_self(self);
            long c1 = chmod(self, 0001) == 0 ? 0L : -(long)errno;
            int r1 = run_self(self);
            long c2 = chmod(self, 04755) == 0 ? 0L : -(long)errno;
            int r2 = run_self(self);
            chmod(self, was);
            say("execve by mode (7: it ran; 113: -EACCES): chmod 0644 %ld then %d; chmod 0001 %ld then %d; chmod 04755 %ld then %d\n",
                c0, r0, c1, r1, c2, r2);
        } else say("execve by mode: no /proc/self/exe (%d)\n", -errno);
    }
    say("kill: kill(1, 0) %ld, kill(getppid(), 0) %ld\n", rc(SYS_kill, 1, 0, 0, 0, 0),
        getppid() ? rc(SYS_kill, getppid(), 0, 0, 0, 0) : 0L);
    {
        char b[512];
        int fd = open("/etc/passwd", O_RDONLY);
        long n = fd >= 0 ? read(fd, b, sizeof b - 1) : -1;
        if (fd >= 0) close(fd);
        if (n < 0) say("accounts: /etc/passwd %d\n", -errno);
        else {
            b[n] = 0;
            char *e = strchr(b, '\n');
            if (e) *e = 0;
            say("accounts: /etc/passwd's first line: %s\n", b);
        }
        fd = open("/etc/shadow", O_RDONLY);
        say("accounts: /etc/shadow %ld\n", fd >= 0 ? 0L : -(long)errno);
        if (fd >= 0) close(fd);
    }
    rmdir(W);
    say("ids: done\n");
    return 0;
}
