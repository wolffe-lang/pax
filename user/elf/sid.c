/* sid.c — px103: set-ID execution, as execve(2) and credentials(7) say
 * it. One static program, run on Linux and on PAX; every line is the
 * answer to one raw call or what one file reads, and the two systems'
 * lines are held byte for byte.
 *
 *   sid DIR       the driver, run as root: makes DIR's files (copies of
 *                 itself with set-ID modes and owners, scripts), then
 *                 runs each case: a child becomes an actor (root, or
 *                 1000:1000 with or without a supplementary group),
 *                 optionally sets no_new_privs, and execs a file; the
 *                 program run prints who it became (the `h:TAG` form
 *                 below). Cases that need a second system's help (a
 *                 traced exec, an attach after a set-ID exec) are px102's
 *                 and are not here: tests/mpx5-sudo prints their SKIPs.
 *   sid h:TAG     what a program run by the driver prints: its three
 *                 user ids and three group ids, the file-system ids, the
 *                 supplementary groups, AT_SECURE, dumpable,
 *                 no_new_privs, the capabilities that follow the ids,
 *                 and who owns /proc/self.
 *
 * Written from execve(2), credentials(7), setuid(2), setresuid(2),
 * capabilities(7), prctl(2), PR_SET_NO_NEW_PRIVS(2const),
 * PR_SET_DUMPABLE(2const), proc_pid(5), ptrace(2), getauxval(3),
 * mount(8) and chmod(2); no kernel's or libc's source. */
#include "px38.h"
#include <sys/auxv.h>
#include <sys/mount.h>
#include <sys/reboot.h>

#ifndef PR_SET_NO_NEW_PRIVS
#define PR_SET_NO_NEW_PRIVS 38
#endif
#define PR_GET_DUMPABLE_ 3
#define PR_GET_NNP 39

static char DIR[256];
static const char *SELF;

/* What the program run by the driver prints. */
static int helper(const char *tag)
{
    unsigned ru, eu, su, rg, eg, sg;
    long a = rc(SYS_getresuid, (long)&ru, (long)&eu, (long)&su, 0, 0);
    long b = rc(SYS_getresgid, (long)&rg, (long)&eg, (long)&sg, 0, 0);
    long fu = rc(SYS_setfsuid, -1, 0, 0, 0, 0), fg = rc(SYS_setfsgid, -1, 0, 0, 0, 0);
    unsigned gl[40];
    long n = rc(SYS_getgroups, 40, (long)gl, 0, 0, 0);
    char list[256] = "";
    int o = 0;
    for (long i = 0; i < n && o < (int)sizeof list - 12; i++) o += snprintf(list + o, sizeof list - o, "%s%u", i ? " " : "", gl[i]);
    struct stat s;
    char own[64] = "?";
    if (stat("/proc/self", &s) == 0) snprintf(own, sizeof own, "%u:%u", s.st_uid, s.st_gid);
    char own2[64] = "?";
    if (stat("/proc/self/status", &s) == 0) snprintf(own2, sizeof own2, "%u:%u", s.st_uid, s.st_gid);
    char capp[64], cape[64], nnp[16];
    snprintf(capp, sizeof capp, "%s", status_line("/proc/self/status", "CapPrm"));
    snprintf(cape, sizeof cape, "%s", status_line("/proc/self/status", "CapEff"));
    snprintf(nnp, sizeof nnp, "%s", status_line("/proc/self/status", "NoNewPrivs"));
    say("h %s: uid %ld %u %u %u fs %ld | gid %ld %u %u %u fs %ld | groups %ld [%s] | secure %lu | dumpable %ld | nnp %ld (%s) | CapPrm %s CapEff %s | /proc/self %s status %s\n",
        tag, a, ru, eu, su, fu, b, rg, eg, sg, fg, n, list, getauxval(AT_SECURE), rc(SYS_prctl, PR_GET_DUMPABLE_, 0, 0, 0, 0),
        rc(SYS_prctl, PR_GET_NNP, 0, 0, 0, 0), nnp, capp, cape, own, own2);
    return 0;
}

/* One case: who runs (uid -1: stays root), with which supplementary
 * group (0: none), with no_new_privs (1) or not, and the file. */
struct kase { const char *tag; int uid; unsigned grp; int nnp; const char *file; };

static void run_case(const struct kase *k)
{
    char path[300], tag[64];
    snprintf(path, sizeof path, "%s/%s", DIR, k->file);
    snprintf(tag, sizeof tag, "h:%s", k->tag);
    pid_t p = fork();
    if (p < 0) { say("! fork: %d\n", errno); return; }
    if (p == 0) {
        if (k->uid >= 0) {
            unsigned g = k->grp;
            become(k->uid, k->uid, g ? 1 : 0, &g);
        }
        if (k->nnp && rc(SYS_prctl, PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) { say("! nnp: %d\n", errno); _exit(97); }
        char *av[] = { path, tag, NULL };
        char *ev[] = { NULL };
        execve(path, av, ev);
        say("case %s: execve %s: %d\n", k->tag, k->file, -errno);
        _exit(98);
    }
    int st = reap(p);
    if (st != 0) say("case %s: status %d\n", k->tag, st);
}

static void make(const char *name, unsigned mode, unsigned uid, unsigned gid)
{
    char p[300];
    snprintf(p, sizeof p, "%s/%s", DIR, name);
    int r = copy_file(SELF, p, 0700);
    if (r != 0) { say("! copy %s: %d\n", p, r); _exit(98); }
    if (chown(p, uid, gid) != 0) { say("! chown %s: %d\n", p, errno); _exit(98); }
    if (chmod(p, mode) != 0) { say("! chmod %s: %d\n", p, errno); _exit(98); }
}

static void script(const char *name, const char *interp, unsigned mode, unsigned uid, unsigned gid)
{
    char p[300], text[400];
    snprintf(p, sizeof p, "%s/%s", DIR, name);
    snprintf(text, sizeof text, "#!%s/%s\n", DIR, interp);
    put_file(p, text, mode, uid, gid);
}

/* The calls that set no_new_privs, and what each answers. */
static void nnp_calls(void)
{
    pid_t p = fork();
    if (p == 0) {
        become(1000, 1000, 0, NULL);
        long g0 = rc(SYS_prctl, PR_GET_NNP, 0, 0, 0, 0);
        long g1 = rc(SYS_prctl, PR_GET_NNP, 1, 0, 0, 0);
        long s0 = rc(SYS_prctl, PR_SET_NO_NEW_PRIVS, 0, 0, 0, 0);
        long s2 = rc(SYS_prctl, PR_SET_NO_NEW_PRIVS, 2, 0, 0, 0);
        long s3 = rc(SYS_prctl, PR_SET_NO_NEW_PRIVS, 1, 1, 0, 0);
        long g2 = rc(SYS_prctl, PR_GET_NNP, 0, 0, 0, 0);
        long s1 = rc(SYS_prctl, PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
        long g3 = rc(SYS_prctl, PR_GET_NNP, 0, 0, 0, 0);
        long u0 = rc(SYS_prctl, PR_SET_NO_NEW_PRIVS, 0, 0, 0, 0);
        long s1b = rc(SYS_prctl, PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
        long g4 = rc(SYS_prctl, PR_GET_NNP, 0, 0, 0, 0);
        say("nnp: get %ld get(1) %ld | set(0) %ld set(2) %ld set(1,1) %ld | get %ld | set(1) %ld | get %ld | set(0) %ld set(1) %ld | get %ld\n",
            g0, g1, s0, s2, s3, g2, s1, g3, u0, s1b, g4);
        /* a child of a process that set it has it, and so does what it execs */
        pid_t c = fork();
        if (c == 0) {
            char path[300];
            snprintf(path, sizeof path, "%s/%s", DIR, "u2");
            char *av[] = { path, "h:nnp-child", NULL };
            char *ev[] = { NULL };
            execve(path, av, ev);
            _exit(98);
        }
        int st = reap(c);
        if (st != 0) say("case nnp-child: status %d\n", st);
        _exit(0);
    }
    reap(p);
}

int main(int argc, char **argv)
{
    for (int i = 1; i < argc; i++)
        if (strncmp(argv[i], "h:", 2) == 0) return helper(argv[i] + 2);
    if (getpid() == 1 && argc == 1) { /* a real Linux's init (the recording): /proc, the console, the driver, power off */
        mkdir("/proc", 0755);
        mkdir("/dev", 0755);
        mount("proc", "/proc", "proc", 0, "");
        mount("devtmpfs", "/dev", "devtmpfs", 0, "");
        int c = open("/dev/console", O_RDWR);
        if (c >= 0) { dup2(c, 0); dup2(c, 1); dup2(c, 2); }
        {
            char b[16] = "?";
            int f = open("/proc/sys/fs/suid_dumpable", O_RDONLY);
            if (f >= 0) { long k = read(f, b, 15); b[k > 0 ? k : 0] = 0; close(f); }
            say("suid_dumpable %s", b);
        }
        char *iv[] = { "/bin/sid", "/t/sid", NULL };
        pid_t d = fork();
        if (d == 0) { mkdir("/t", 0777); execve("/bin/sid", iv, NULL); _exit(98); }
        int st = reap(d);
        say("sid: exit %d\n", st);
        sync();
        reboot(RB_POWER_OFF);
        return 0;
    }
    if (argc != 2) { say("usage: sid DIR | sid h:TAG\n"); return 2; }
    SELF = argv[0];
    snprintf(DIR, sizeof DIR, "%s", argv[1]);
    umask(022);
    mkdir(DIR, 0755);
    chmod(DIR, 0755);
    /* the files: owner 0 or 2000:3000, mode by the case */
    make("plain", 0755, 0, 0);
    make("u0", 04755, 0, 0);
    make("u2", 04755, 2000, 3000);
    make("g0", 02755, 0, 0);
    make("g2", 02755, 2000, 3000);
    make("gn", 02705, 2000, 3000);   /* set-group-ID without group-execute: no effect */
    make("ug", 06755, 2000, 3000);
    make("own", 04755, 1000, 1000);  /* a set-ID file owned by the actor: no change */
    make("c0", 00755, 0, 0);         /* chmod'ed to 4755 below, before it is run */
    make("ro", 04711, 2000, 3000);
    script("su", "plain", 04755, 2000, 3000); /* a script's own bits are ignored */
    script("ints", "u2", 00755, 0, 0);        /* its interpreter's bits are honoured */
    script("ints0", "u0", 00755, 0, 0);
    /* a nosuid mount: the same file there is not set-ID */
    char n[300], np[300];
    snprintf(n, sizeof n, "%s/n", DIR);
    mkdir(n, 0755);
    long m = rc(SYS_mount, (long)"tmpfs", (long)n, (long)"tmpfs", MS_NOSUID, (long)"mode=755");
    say("mount nosuid tmpfs: %ld\n", m);
    if (m == 0) {
        snprintf(np, sizeof np, "%s/n/u2", DIR);
        int r = copy_file(SELF, np, 0700);
        if (r == 0) { if (chown(np, 2000, 3000) != 0 || chmod(np, 04755) != 0) say("! nosuid copy: %d\n", errno); }
        else say("! nosuid copy: %d\n", r);
        snprintf(np, sizeof np, "%s/n/u0", DIR);
        r = copy_file(SELF, np, 0700);
        if (r == 0) { if (chown(np, 0, 0) != 0 || chmod(np, 04755) != 0) say("! nosuid copy: %d\n", errno); }
    }
    static const char *const NAMES[] = { "plain", "u0", "u2", "g0", "g2", "gn", "ug", "own", "ro", "su", "ints", "n/u2", "n/u0" };
    for (unsigned i = 0; i < sizeof NAMES / sizeof *NAMES; i++) {
        char q[300];
        snprintf(q, sizeof q, "%s/%s", DIR, NAMES[i]);
        say("file %s: %o %s\n", NAMES[i], mode_of(q), own_of(q));
    }
    static const struct kase cases[] = {
        /* tag            uid   grp  nnp  file */
        { "plain-root",   -1,   0,   0,  "plain" },
        { "plain-user",   1000, 0,   0,  "plain" },
        { "u0-root",      -1,   0,   0,  "u0" },
        { "u0-user",      1000, 0,   0,  "u0" },
        { "u2-root",      -1,   0,   0,  "u2" },
        { "u2-user",      1000, 0,   0,  "u2" },
        { "u2-user-nnp",  1000, 0,   1,  "u2" },
        { "u0-user-nnp",  1000, 0,   1,  "u0" },
        { "g0-user",      1000, 0,   0,  "g0" },
        { "g0-root",      -1,   0,   0,  "g0" },
        { "g2-user",      1000, 0,   0,  "g2" },
        { "g2-user-sup",  1000, 3000, 0, "g2" },
        { "g2-user-nnp",  1000, 0,   1,  "g2" },
        { "gn-user",      1000, 0,   0,  "gn" },
        { "gn-root",      -1,   0,   0,  "gn" },
        { "ug-user",      1000, 0,   0,  "ug" },
        { "ug-user-sup",  1000, 3000, 0, "ug" },
        { "ug-root",      -1,   0,   0,  "ug" },
        { "own-user",     1000, 0,   0,  "own" },
        { "ro-user",      1000, 0,   0,  "ro" },
        { "su-user",      1000, 0,   0,  "su" },
        { "ints-user",    1000, 0,   0,  "ints" },
        { "ints0-user",   1000, 0,   0,  "ints0" },
        { "ints-user-nnp", 1000, 0,  1,  "ints" },
        { "nosuid-u2",    1000, 0,   0,  "n/u2" },
        { "nosuid-u0",    1000, 0,   0,  "n/u0" },
        { "nosuid-u2-root", -1, 0,   0,  "n/u2" },
    };
    for (unsigned i = 0; i < sizeof cases / sizeof *cases; i++) run_case(&cases[i]);
    /* chmod then exec: the mode is read at the exec */
    {
        char p[300];
        snprintf(p, sizeof p, "%s/c0", DIR);
        static const struct kase c0 = { "c0-plain", 1000, 0, 0, "c0" };
        run_case(&c0);
        say("chown c0 2000:3000 %ld, chmod c0 4755 %ld\n", (long)chown(p, 2000, 3000), (long)chmod(p, 04755));
        static const struct kase c1 = { "c0-set", 1000, 0, 0, "c0" };
        run_case(&c1);
        say("chown c0 1000:1000 (clears the bit) %ld\n", (long)chown(p, 1000, 1000));
        static const struct kase c2 = { "c0-chowned", 1000, 0, 0, "c0" };
        run_case(&c2);
    }
    nnp_calls();
    say("sid: done\n");
    return 0;
}
