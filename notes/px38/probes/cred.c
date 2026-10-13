/* cred.c — px38, item 2(a): Linux's credential rules, measured.
 *
 * Every row is one raw call made by a fresh child that root first put
 * in a state (real, effective, saved); the row prints the answer and
 * the four ids afterwards (real effective saved file-system, as
 * /proc/self/status's Uid: or Gid: line gives them) and whether the
 * thread then holds capabilities. The whole matrix is the oracle a PAX
 * credentials lane is held to, line for line.
 *
 *   cred            the matrices, the groups, fork and execve
 *   cred show TAG   (what the probe execs of itself: prints its ids)
 */
#include "px38.h"
#include <sys/auxv.h>
#include <sys/prctl.h>

#define NV 6
static const long V[NV] = { -1, 0, 1000, 1001, 1002, 1003 };
static const long GV[NV] = { -1, 0, 2000, 2001, 2002, 2003 };

static void show(const char *tag)
{
    say("%s: uid %s | gid %s | groups %s | cap %s | AT_SECURE %lu | dumpable %ld\n", tag, uids(), gids(), groups(), capeff(),
        getauxval(AT_SECURE), rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0));
}

/* One row. `set`: the child first puts itself in state `st` (it is
 * root); otherwise the caller already is in it and the row is tagged. */
static void row(int user, int set, const char *tag, const long st[3], const char *name, long nr, int na, long a, long b, long c)
{
    pid_t p = fork();
    if (p == 0) {
        if (set) {
            long s = rc(user ? SYS_setresuid : SYS_setresgid, st[0], st[1], st[2], 0, 0);
            if (s != 0) { say("! state (%ld %ld %ld): %ld\n", st[0], st[1], st[2], s); _exit(99); }
        }
        long r = rc(nr, a, b, c, 0, 0);
        char args[64];
        if (na == 1) snprintf(args, sizeof args, "%ld", a);
        else if (na == 2) snprintf(args, sizeof args, "%ld, %ld", a, b);
        else snprintf(args, sizeof args, "%ld, %ld, %ld", a, b, c);
        say("%s(%ld %ld %ld) %s(%s) = %ld -> %s cap %s\n", tag, st[0], st[1], st[2], name, args, r, user ? uids() : gids(), capeff());
        _exit(0);
    }
    if (reap(p) != 0) say("! a row's child failed\n");
}

static void matrix(int user, int set, const char *tag, const long st[3], const long *v)
{
    const char *u = user ? "uid" : "gid";
    char n[32];
    snprintf(n, sizeof n, "set%s", u);
    for (int i = 0; i < NV; i++) row(user, set, tag, st, n, user ? SYS_setuid : SYS_setgid, 1, v[i], 0, 0);
    snprintf(n, sizeof n, "setfs%s", u);
    for (int i = 0; i < NV; i++) row(user, set, tag, st, n, user ? SYS_setfsuid : SYS_setfsgid, 1, v[i], 0, 0);
    snprintf(n, sizeof n, "setre%s", u);
    for (int i = 0; i < NV; i++)
        for (int j = 0; j < NV; j++) row(user, set, tag, st, n, user ? SYS_setreuid : SYS_setregid, 2, v[i], v[j], 0);
    snprintf(n, sizeof n, "setres%s", u);
    for (int i = 0; i < NV; i++)
        for (int j = 0; j < NV; j++)
            for (int k = 0; k < NV; k++) row(user, set, tag, st, n, user ? SYS_setresuid : SYS_setresgid, 3, v[i], v[j], v[k]);
}

int main(int argc, char **argv)
{
    if (argc > 2 && strcmp(argv[1], "show") == 0) { show(argv[2]); return 0; }
    static const long US[][3] = { { 0, 0, 0 }, { 1000, 1000, 1000 }, { 1000, 1001, 1002 }, { 1000, 1001, 1000 },
                                  { 1000, 0, 1000 }, { 0, 1000, 0 } };
    static const long GS[][3] = { { 2000, 2001, 2002 }, { 2000, 2000, 2000 } };
    unsigned g2[2] = { 2000, 2001 };

    show("start");
    say("== user ids: (real effective saved) call = answer -> real effective saved fs\n");
    for (unsigned i = 0; i < sizeof US / sizeof *US; i++) matrix(1, 1, "", US[i], V);

    say("== group ids, the caller's user ids (0 0 0)\n");
    for (unsigned i = 0; i < sizeof GS / sizeof *GS; i++) matrix(0, 1, "", GS[i], GV);
    say("== group ids, the caller's user ids (1000 1000 1000)\n");
    for (unsigned i = 0; i < sizeof GS / sizeof *GS; i++) {
        pid_t p = fork();
        if (p == 0) {
            /* the group state first (root may), then the user ids for good; the rows then run as that user */
            if (rc(SYS_setresgid, GS[i][0], GS[i][1], GS[i][2], 0, 0) != 0 || rc(SYS_setresuid, 1000, 1000, 1000, 0, 0) != 0) _exit(99);
            matrix(0, 0, "u1000 ", GS[i], GV);
            _exit(0);
        }
        reap(p);
    }

    say("== an id the caller's user namespace may not map\n");
    {
        /* one call, then the reading of what it left: never both in one argument list */
        pid_t p = fork();
        if (p == 0) { long r = rc(SYS_setuid, 70000, 0, 0, 0, 0); say("root setuid(70000) = %ld -> %s\n", r, uids()); _exit(0); }
        reap(p);
        p = fork();
        if (p == 0) { long r = rc(SYS_setgid, 70000, 0, 0, 0, 0); say("root setgid(70000) = %ld -> %s\n", r, gids()); _exit(0); }
        reap(p);
        p = fork();
        if (p == 0) { long r = rc(SYS_setuid, 4294967294L, 0, 0, 0, 0); say("root setuid(4294967294) = %ld -> %s\n", r, uids()); _exit(0); }
        reap(p);
        p = fork();
        if (p == 0) {
            long a = rc(SYS_setresuid, -1, -1, -1, 0, 0), b = rc(SYS_setuid, -1, 0, 0, 0, 0), c = rc(SYS_setgid, -1, 0, 0, 0, 0);
            say("root setresuid(-1, -1, -1) = %ld; setuid(-1) = %ld; setgid(-1) = %ld -> uid %s", a, b, c, uids());
            say(" gid %s\n", gids());
            _exit(0);
        }
        reap(p);
    }

    say("== supplementary groups\n");
    {
        int fd = open("/proc/self/setgroups", O_RDONLY);
        char b[32] = "";
        if (fd >= 0) { long n = read(fd, b, sizeof b - 1); if (n > 0) b[n - (b[n - 1] == '\n')] = 0; close(fd); }
        say("/proc/self/setgroups: %s\n", fd >= 0 ? b : "(none)");
        unsigned big[4] = { 2000, 2001, 2001, 0 }, got[8] = { 77, 77, 77, 77, 77, 77, 77, 77 };
        unsigned *many = calloc(65537, 4);
        long r, r2, r3;
        pid_t p = fork();
        if (p == 0) {
            r = rc(SYS_getgroups, 0, 0, 0, 0, 0);
            say("root getgroups(0, NULL) = %ld (groups '%s')\n", r, groups());
            r = rc(SYS_setgroups, 2, (long)g2, 0, 0, 0);
            say("root setgroups(2, {2000, 2001}) = %ld -> groups '%s'\n", r, groups());
            r = rc(SYS_getgroups, 0, 0, 0, 0, 0);
            r2 = rc(SYS_getgroups, 1, (long)got, 0, 0, 0);
            r3 = rc(SYS_getgroups, 2, (long)got, 0, 0, 0);
            say("root getgroups(0, NULL) = %ld, getgroups(1, list) = %ld, getgroups(2, list) = %ld (%u %u)", r, r2, r3, got[0], got[1]);
            r = rc(SYS_getgroups, 8, (long)got, 0, 0, 0);
            say(", getgroups(8, list) = %ld, getgroups(-1, list) = %ld\n", r, rc(SYS_getgroups, -1, (long)got, 0, 0, 0));
            r = rc(SYS_setgroups, 4, (long)big, 0, 0, 0);
            say("root setgroups(4, {2000, 2001, 2001, 0}) = %ld -> groups '%s'\n", r, groups());
            r = rc(SYS_setgroups, 1, 0, 0, 0, 0);
            say("root setgroups(1, NULL) = %ld -> groups '%s'\n", r, groups());
            r = rc(SYS_setgroups, 65537, (long)many, 0, 0, 0);
            r2 = rc(SYS_setgroups, -1, (long)g2, 0, 0, 0);
            say("root setgroups(65537, list) = %ld, setgroups(-1, list) = %ld -> groups '%s'\n", r, r2, groups());
            r = rc(SYS_setgroups, 65536, (long)many, 0, 0, 0);
            r2 = rc(SYS_getgroups, 0, 0, 0, 0, 0);
            say("root setgroups(65536, list) = %ld, then getgroups(0, NULL) = %ld\n", r, r2);
            r = rc(SYS_setgroups, 0, 0, 0, 0, 0);
            say("root setgroups(0, NULL) = %ld -> groups '%s'\n", r, groups());
            _exit(0);
        }
        reap(p);
        p = fork();
        if (p == 0) {
            rc(SYS_setgroups, 2, (long)g2, 0, 0, 0);
            rc(SYS_setresuid, 1000, 1000, 1000, 0, 0);
            r = rc(SYS_setgroups, 2, (long)g2, 0, 0, 0);
            r2 = rc(SYS_setgroups, 0, 0, 0, 0, 0);
            r3 = rc(SYS_getgroups, 0, 0, 0, 0, 0);
            say("user (1000 1000 1000) setgroups(2, the same two) = %ld, setgroups(0, NULL) = %ld, getgroups(0, NULL) = %ld -> groups '%s'\n", r, r2,
                r3, groups());
            _exit(0);
        }
        reap(p);
        p = fork();
        if (p == 0) {
            /* saved id 0, effective 1000: no privilege now, and the way back */
            rc(SYS_setresuid, 1000, 1000, 0, 0, 0);
            r = rc(SYS_setgroups, 2, (long)g2, 0, 0, 0);
            say("(1000 1000 0) setgroups(2, list) = %ld cap %s", r, capeff());
            r = rc(SYS_setresuid, -1, 0, -1, 0, 0);
            say("; then setresuid(-1, 0, -1) = %ld cap %s", r, capeff());
            r = rc(SYS_setgroups, 2, (long)g2, 0, 0, 0);
            say("; then setgroups(2, list) = %ld\n", r);
            _exit(0);
        }
        reap(p);
    }

    say("== fork and execve\n");
    {
        char self[256];
        long n = readlink("/proc/self/exe", self, sizeof self - 1);
        if (n <= 0) { say("! no /proc/self/exe\n"); return 1; }
        self[n] = 0;
        static const long cases[][6] = {
            /* uids r e s, gids r e s */
            { 1000, 1000, 1000, 2000, 2000, 2000 },
            { 1000, 1001, 1002, 2000, 2001, 2002 },
            { 1000, 1001, 1000, 2000, 2000, 2000 },
            { 1000, 1000, 1000, 2000, 2001, 2000 },
            { 1000, 0, 1000, 2000, 2000, 2000 },
            { 0, 1000, 0, 2000, 2000, 2000 },
            { 0, 0, 0, 0, 0, 0 },
        };
        for (unsigned i = 0; i < sizeof cases / sizeof *cases; i++) {
            pid_t p = fork();
            if (p == 0) {
                rc(SYS_setgroups, 2, (long)g2, 0, 0, 0);
                if (rc(SYS_setresgid, cases[i][3], cases[i][4], cases[i][5], 0, 0) != 0) _exit(99);
                if (rc(SYS_setresuid, cases[i][0], cases[i][1], cases[i][2], 0, 0) != 0) _exit(99);
                rc(SYS_setfsuid, cases[i][0], 0, 0, 0, 0); /* the file-system id set apart from the effective id, where allowed */
                char tag[64];
                snprintf(tag, sizeof tag, "case %u before  ", i);
                show(tag);
                pid_t q = fork();
                if (q == 0) { snprintf(tag, sizeof tag, "case %u forked  ", i); show(tag); _exit(0); }
                reap(q);
                snprintf(tag, sizeof tag, "case %u execve'd", i);
                char *av[] = { self, (char *)"show", tag, NULL };
                char *ev[] = { NULL };
                execve(self, av, ev);
                say("! execve %d\n", -errno);
                _exit(98);
            }
            reap(p);
        }
    }
    say("cred: done\n");
    return 0;
}
