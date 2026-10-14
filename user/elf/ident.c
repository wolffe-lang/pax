/* ident.c — px39: what px38's cred does not ask of a kernel's
 * credentials. One static program, run on Linux and on PAX, as root and
 * again by a process that first became 1000:1000 (user/elf/as.c); every
 * line is the answer to one raw call or what one file reads.
 *
 *   ident [SETID]     the rows. SETID: a copy of this program with the
 *                     set-user-ID and set-group-ID bits, owned by root,
 *                     where the kernel does not honour them (a nosuid
 *                     mount on Linux; anywhere on PAX, ruling R5); `-`
 *                     or nothing leaves those rows out
 *   ident show TAG    (what the probe execs of itself)
 *   ident soak N      N rounds of id changes and N / 10 children that
 *                     drop for good, then one line
 *
 * A line that starts with `~` is not compared between the two systems:
 * what PAX answers by a ruling of its own (33 groups, R4), what differs
 * by design and is named (ids are a process's on PAX, a thread's on
 * Linux), what a later lane owns (who a file of /proc belongs to: U2),
 * and the free memory a soak reads.
 *
 * Written from credentials(7), capabilities(7), setresuid(2),
 * getgroups(2), prctl(2), getauxval(3), proc_pid_status(5) and the uapi
 * headers; no kernel's or libc's source. */
#include "px38.h"
#include <pthread.h>
#include <sys/auxv.h>
#include <sys/prctl.h>

#define M1 (-1L)
static char SELF[256];
static const char *SETID;

/* One line of a status file, whole: tabs written `\t`, its end `$`. */
static const char *raw(const char *path, const char *name)
{
    static char buf[8192], out[512];
    snprintf(out, sizeof out, "(no %s)", name);
    int fd = open(path, O_RDONLY);
    if (fd < 0) { snprintf(out, sizeof out, "(%s: %d)", path, -errno); return out; }
    int n = 0, k;
    while (n < (int)sizeof buf - 1 && (k = read(fd, buf + n, sizeof buf - 1 - n)) > 0) n += k;
    close(fd);
    buf[n] = 0;
    size_t l = strlen(name);
    for (char *p = buf; p && *p; p = strchr(p, '\n'), p = p ? p + 1 : p) {
        if (strncmp(p, name, l) == 0 && p[l] == ':') {
            int i = 0;
            for (; *p && *p != '\n' && i < (int)sizeof out - 4; p++) {
                if (*p == '\t') { out[i++] = '\\'; out[i++] = 't'; }
                else out[i++] = *p;
            }
            out[i++] = '$';
            out[i] = 0;
            return out;
        }
    }
    return out;
}

static const char *const LINES[] = { "Uid", "Gid", "Groups", "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs" };

/* What the calls that read an identity answer, in one line. */
static void getters(const char *tag)
{
    unsigned u[3] = { 77, 77, 77 }, g[3] = { 77, 77, 77 }, gl[40];
    long a = rc(SYS_getuid, 0, 0, 0, 0, 0), b = rc(SYS_geteuid, 0, 0, 0, 0, 0);
    long c = rc(SYS_getgid, 0, 0, 0, 0, 0), d = rc(SYS_getegid, 0, 0, 0, 0, 0);
    long ru = rc(SYS_getresuid, (long)&u[0], (long)&u[1], (long)&u[2], 0, 0);
    long rg = rc(SYS_getresgid, (long)&g[0], (long)&g[1], (long)&g[2], 0, 0);
    long n0 = rc(SYS_getgroups, 0, 0, 0, 0, 0), n = rc(SYS_getgroups, 40, (long)gl, 0, 0, 0);
    char list[512] = "";
    int o = 0;
    for (long i = 0; i < n && o < (int)sizeof list - 12; i++) o += snprintf(list + o, sizeof list - o, "%s%u", i ? " " : "", gl[i]);
    say("get %s: getuid %ld geteuid %ld getgid %ld getegid %ld | getresuid %ld (%u %u %u) | getresgid %ld (%u %u %u) | getgroups(0) %ld, getgroups(40) %ld (%s)\n",
        tag, a, b, c, d, ru, u[0], u[1], u[2], rg, g[0], g[1], g[2], n0, n, list);
}

static void status_rows(const char *tag)
{
    for (unsigned i = 0; i < sizeof LINES / sizeof *LINES; i++) say("status %s: %s\n", tag, raw("/proc/self/status", LINES[i]));
    getters(tag);
}

static void show(const char *tag)
{
    unsigned u[3] = { 77, 77, 77 }, g[3] = { 77, 77, 77 };
    rc(SYS_getresuid, (long)&u[0], (long)&u[1], (long)&u[2], 0, 0);
    rc(SYS_getresgid, (long)&g[0], (long)&g[1], (long)&g[2], 0, 0);
    say("%s: uid %s | gid %s | groups %s", tag, uids(), gids(), groups());
    say(" | CapPrm %s", status_line("/proc/self/status", "CapPrm"));
    say(" CapEff %s", status_line("/proc/self/status", "CapEff"));
    say(" | AT_UID %lu AT_EUID %lu AT_GID %lu AT_EGID %lu AT_SECURE %lu | dumpable %ld | getresuid (%u %u %u) getresgid (%u %u %u)\n",
        getauxval(AT_UID), getauxval(AT_EUID), getauxval(AT_GID), getauxval(AT_EGID), getauxval(AT_SECURE),
        rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0), u[0], u[1], u[2], g[0], g[1], g[2]);
}

/* --- A: the status lines and the getters, state by state ----------------- */

struct state { const char *tag; long ng; unsigned gl[4]; long g[3], u[3], fsu; };
static const struct state STATES[] = {
    { "root", -1, { 0 }, { M1, M1, M1 }, { M1, M1, M1 }, M1 },
    { "root, groups 2000 2001", 2, { 2000, 2001 }, { M1, M1, M1 }, { M1, M1, M1 }, M1 },
    { "(1000 1000 1000) gid (2000 2000 2000) groups 7", 1, { 7 }, { 2000, 2000, 2000 }, { 1000, 1000, 1000 }, M1 },
    { "(1000 1001 1002) gid (2000 2001 2002)", 0, { 0 }, { 2000, 2001, 2002 }, { 1000, 1001, 1002 }, M1 },
    { "(1000 0 1000), fs 1000", 0, { 0 }, { M1, M1, M1 }, { 1000, 0, 1000 }, 1000 },
    { "(0 1000 0), fs 0", 0, { 0 }, { M1, M1, M1 }, { 0, 1000, 0 }, 0 },
    { "(1000 1000 0)", 0, { 0 }, { M1, M1, M1 }, { 1000, 1000, 0 }, M1 },
    { "(0 1000 1000)", 0, { 0 }, { M1, M1, M1 }, { 0, 1000, 1000 }, M1 },
    { "(1000 1000 0), fs 0", 0, { 0 }, { M1, M1, M1 }, { 1000, 1000, 0 }, 0 },
};

/* Put the caller in a state; the first step refused, or 0. */
static long enter(const struct state *s)
{
    long r;
    if (s->ng >= 0 && (r = rc(SYS_setgroups, s->ng, (long)s->gl, 0, 0, 0)) != 0) return r;
    if ((r = rc(SYS_setresgid, s->g[0], s->g[1], s->g[2], 0, 0)) != 0) return r;
    if ((r = rc(SYS_setresuid, s->u[0], s->u[1], s->u[2], 0, 0)) != 0) return r;
    if (s->fsu != M1) rc(SYS_setfsuid, s->fsu, 0, 0, 0, 0);
    return 0;
}

static void section_states(void)
{
    say("== the status lines and the getters, state by state\n");
    for (unsigned i = 0; i < sizeof STATES / sizeof *STATES; i++) {
        pid_t p = fork();
        if (p == 0) {
            long r = enter(&STATES[i]);
            if (r != 0) { say("status %s: cannot (%ld)\n", STATES[i].tag, r); _exit(0); }
            status_rows(STATES[i].tag);
            _exit(0);
        }
        reap(p);
    }
}

/* --- C: pointers the caller may not use ------------------------------------ */

static void section_faults(void)
{
    say("== a pointer the caller cannot use (8: nothing is mapped there; text: mapped, not writable)\n");
    long bad = 8, text = (long)(void *)&section_faults;
    unsigned v[3];
    static const char *const nm[] = { "getresuid", "getresgid" };
    static const long nr[] = { SYS_getresuid, SYS_getresgid };
    for (int k = 0; k < 2; k++) {
        long r;
        v[0] = v[1] = v[2] = 77;
        r = rc(nr[k], bad, (long)&v[1], (long)&v[2], 0, 0);
        say("fault: %s(8, &e, &s) = %ld (e %u s %u)\n", nm[k], r, v[1], v[2]);
        v[0] = v[1] = v[2] = 77;
        r = rc(nr[k], (long)&v[0], bad, (long)&v[2], 0, 0);
        say("fault: %s(&r, 8, &s) = %ld (r %u s %u)\n", nm[k], r, v[0], v[2]);
        v[0] = v[1] = v[2] = 77;
        r = rc(nr[k], (long)&v[0], (long)&v[1], bad, 0, 0);
        say("fault: %s(&r, &e, 8) = %ld (r %u e %u)\n", nm[k], r, v[0], v[1]);
        v[0] = v[1] = v[2] = 77;
        r = rc(nr[k], (long)&v[0], (long)&v[1], text, 0, 0);
        say("fault: %s(&r, &e, text) = %ld (r %u e %u)\n", nm[k], r, v[0], v[1]);
        v[0] = v[1] = v[2] = 77;
        r = rc(nr[k], (long)&v[0], (long)&v[0], (long)&v[0], 0, 0);
        say("fault: %s(&x, &x, &x) = %ld (x %u)\n", nm[k], r, v[0]);
    }
    pid_t p = fork();
    if (p == 0) {
        unsigned two[2] = { 2000, 2001 }, got[4] = { 77, 77, 77, 77 };
        long s = rc(SYS_setgroups, 2, (long)two, 0, 0, 0);
        long n = rc(SYS_getgroups, 0, 0, 0, 0, 0);
        say("fault: with setgroups(2, {2000, 2001}) = %ld, getgroups(0, NULL) = %ld:", s, n);
        say(" getgroups(2, 8) = %ld,", rc(SYS_getgroups, 2, bad, 0, 0, 0));
        say(" getgroups(2, text) = %ld,", rc(SYS_getgroups, 2, text, 0, 0, 0));
        say(" getgroups(0, 8) = %ld,", rc(SYS_getgroups, 0, bad, 0, 0, 0));
        say(" getgroups(1, 8) = %ld,", rc(SYS_getgroups, 1, bad, 0, 0, 0));
        n = rc(SYS_getgroups, 0x100000004L, (long)got, 0, 0, 0); /* the call, then the reading of what it left */
        say(" getgroups(0x100000004, list) = %ld (%u %u %u)\n", n, got[0], got[1], got[2]);
        say("fault: setgroups(2, 8) = %ld,", rc(SYS_setgroups, 2, bad, 0, 0, 0));
        say(" setgroups(0, 8) = %ld,", rc(SYS_setgroups, 0, bad, 0, 0, 0));
        say(" then getgroups(0, NULL) = %ld;", rc(SYS_getgroups, 0, 0, 0, 0, 0));
        say(" setgroups(0x100000001, {2000}) = %ld,", rc(SYS_setgroups, 0x100000001L, (long)two, 0, 0, 0));
        say(" then groups '%s'\n", groups());
        say("fault: setgroups(-1, list) = %ld,", rc(SYS_setgroups, -1, (long)two, 0, 0, 0));
        say(" setgroups(65537, 8) = %ld,", rc(SYS_setgroups, 65537, bad, 0, 0, 0));
        say(" setgroups(1, NULL) = %ld\n", rc(SYS_setgroups, 1, 0, 0, 0, 0));
        _exit(0);
    }
    reap(p);
}

/* --- D: an id is 32 bits -------------------------------------------------------- */

static void one(const char *label, long nr, long a, long b, long c, int group)
{
    pid_t p = fork();
    if (p == 0) {
        long r = rc(nr, a, b, c, 0, 0);
        say("width: %s = %ld -> %s\n", label, r, group ? gids() : uids());
        _exit(0);
    }
    reap(p);
}

static void section_width(void)
{
    say("== an id argument is 32 bits of its register\n");
    one("setuid(0x1000003e8)", SYS_setuid, 0x1000003e8L, 0, 0, 0);
    one("setgid(0x1000007d0)", SYS_setgid, 0x1000007d0L, 0, 0, 1);
    one("setreuid(0x1ffffffff, 0x1000003e8)", SYS_setreuid, 0x1ffffffffL, 0x1000003e8L, 0, 0);
    one("setresuid(0x1ffffffff, 0x1000003e8, 0x1ffffffff)", SYS_setresuid, 0x1ffffffffL, 0x1000003e8L, 0x1ffffffffL, 0);
    one("setresgid(0x1000007d0, 0x1ffffffff, 0x1ffffffff)", SYS_setresgid, 0x1000007d0L, 0x1ffffffffL, 0x1ffffffffL, 1);
    one("setfsuid(0x1000003e8)", SYS_setfsuid, 0x1000003e8L, 0, 0, 0);
    one("setfsgid(0x1000007d0)", SYS_setfsgid, 0x1000007d0L, 0, 0, 1);
    one("setuid(4294967295)", SYS_setuid, 4294967295L, 0, 0, 0);
    one("setfsuid(4294967295)", SYS_setfsuid, 4294967295L, 0, 0, 0);
    one("setuid(4294967294)", SYS_setuid, 4294967294L, 0, 0, 0);
    {
        pid_t p = fork();
        if (p == 0) {
            long a = rc(SYS_setfsuid, 4294967294L, 0, 0, 0, 0), b = rc(SYS_setfsuid, 0, 0, 0, 0, 0);
            say("width: setfsuid(4294967294) = %ld, then setfsuid(0) = %ld -> %s\n", a, b, uids());
            _exit(0);
        }
        reap(p);
    }
}

/* --- E: dumpable, call by call ------------------------------------------------- */

static void dump_row(const char *label, long nr, long a, long b, long c)
{
    pid_t p = fork();
    if (p == 0) {
        long before = rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0);
        long r = rc(nr, a, b, c, 0, 0);
        say("dump: %s = %ld: dumpable %ld -> %ld\n", label, r, before, rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0));
        _exit(0);
    }
    reap(p);
}

static void section_dump(void)
{
    long u = rc(SYS_getuid, 0, 0, 0, 0, 0), g = rc(SYS_getgid, 0, 0, 0, 0, 0);
    char l[96];
    unsigned two[2] = { 2000, 2001 };
    say("== prctl, and which call clears dumpable (the caller's ids are %ld and %ld: `me` and `mine`)\n", u, g);
    say("prctl: PR_GET_DUMPABLE %ld", rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0));
    say(" PR_GET_KEEPCAPS %ld", rc(SYS_prctl, PR_GET_KEEPCAPS, 0, 0, 0, 0));
    say(" PR_GET_NO_NEW_PRIVS %ld", rc(SYS_prctl, PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0));
    say(" PR_GET_SECUREBITS %ld\n", rc(SYS_prctl, PR_GET_SECUREBITS, 0, 0, 0, 0));
    say("prctl: with a second argument of 1: PR_GET_DUMPABLE %ld", rc(SYS_prctl, PR_GET_DUMPABLE, 1, 0, 0, 0));
    say(" PR_GET_KEEPCAPS %ld", rc(SYS_prctl, PR_GET_KEEPCAPS, 1, 0, 0, 0));
    say(" PR_GET_NO_NEW_PRIVS %ld", rc(SYS_prctl, PR_GET_NO_NEW_PRIVS, 1, 0, 0, 0));
    say(" PR_GET_SECUREBITS %ld;", rc(SYS_prctl, PR_GET_SECUREBITS, 1, 0, 0, 0));
    say(" with a fifth of 1: PR_GET_NO_NEW_PRIVS %ld\n", rc(SYS_prctl, PR_GET_NO_NEW_PRIVS, 0, 0, 0, 1));
    /* what leaves every id as it was */
    dump_row("setuid(me)", SYS_setuid, u, 0, 0);
    dump_row("setreuid(me, me)", SYS_setreuid, u, u, 0);
    dump_row("setreuid(-1, -1)", SYS_setreuid, -1, -1, 0);
    dump_row("setresuid(me, me, me)", SYS_setresuid, u, u, u);
    dump_row("setresuid(-1, -1, -1)", SYS_setresuid, -1, -1, -1);
    dump_row("setfsuid(me)", SYS_setfsuid, u, 0, 0);
    dump_row("setfsuid(-1)", SYS_setfsuid, -1, 0, 0);
    dump_row("setgid(mine)", SYS_setgid, g, 0, 0);
    dump_row("setregid(mine, mine)", SYS_setregid, g, g, 0);
    dump_row("setresgid(mine, mine, mine)", SYS_setresgid, g, g, g);
    dump_row("setfsgid(mine)", SYS_setfsgid, g, 0, 0);
    dump_row("setgroups(0, NULL)", SYS_setgroups, 0, 0, 0);
    dump_row("setgroups(2, {2000, 2001})", SYS_setgroups, 2, (long)two, 0);
    /* one id at a time */
    static const struct { const char *l; long nr, a, b, c; } R[] = {
        { "setresuid(1000, -1, -1)", SYS_setresuid, 1000, -1, -1 },
        { "setresuid(-1, 1000, -1)", SYS_setresuid, -1, 1000, -1 },
        { "setresuid(-1, -1, 1000)", SYS_setresuid, -1, -1, 1000 },
        { "setreuid(1000, -1)", SYS_setreuid, 1000, -1, 0 },
        { "setreuid(-1, 1000)", SYS_setreuid, -1, 1000, 0 },
        { "setuid(1000)", SYS_setuid, 1000, 0, 0 },
        { "setfsuid(1000)", SYS_setfsuid, 1000, 0, 0 },
        { "setresgid(2000, -1, -1)", SYS_setresgid, 2000, -1, -1 },
        { "setresgid(-1, 2000, -1)", SYS_setresgid, -1, 2000, -1 },
        { "setresgid(-1, -1, 2000)", SYS_setresgid, -1, -1, 2000 },
        { "setregid(2000, -1)", SYS_setregid, 2000, -1, 0 },
        { "setregid(-1, 2000)", SYS_setregid, -1, 2000, 0 },
        { "setgid(2000)", SYS_setgid, 2000, 0, 0 },
        { "setfsgid(2000)", SYS_setfsgid, 2000, 0, 0 },
        { "setuid(-1)", SYS_setuid, -1, 0, 0 },
    };
    for (unsigned i = 0; i < sizeof R / sizeof *R; i++) dump_row(R[i].l, R[i].nr, R[i].a, R[i].b, R[i].c);
    /* there and back: is it the value or the call? */
    pid_t p = fork();
    if (p == 0) {
        long a = rc(SYS_setresuid, -1, 1000, -1, 0, 0), d1 = rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0);
        long b = rc(SYS_setresuid, -1, u, -1, 0, 0), d2 = rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0);
        snprintf(l, sizeof l, "setresuid(-1, 1000, -1) = %ld: dumpable %ld; back, setresuid(-1, me, -1) = %ld: dumpable %ld", a, d1, b, d2);
        say("dump: %s\n", l);
        _exit(0);
    }
    reap(p);
}

/* --- F: execve ------------------------------------------------------------------------ */

struct ecase { long u[3], g[3], fsu, fsg; long ng; unsigned gl[2]; };
static const struct ecase ECASES[] = {
    { { 1000, 1000, 1000 }, { 2000, 2000, 2000 }, M1, M1, 2, { 2000, 2001 } },
    { { 1000, 1001, 1002 }, { 2000, 2001, 2002 }, M1, M1, 2, { 2000, 2001 } },
    { { 1000, 0, 1000 }, { 2000, 2000, 2000 }, M1, M1, 2, { 2000, 2001 } },
    { { 0, 1000, 0 }, { 2000, 2000, 2000 }, M1, M1, 2, { 2000, 2001 } },
    { { 0, 0, 0 }, { 0, 0, 0 }, M1, M1, 2, { 2000, 2001 } },
    { { 0, 0, 0 }, { 0, 0, 0 }, 1000, M1, 2, { 2000, 2001 } },   /* 5: only the file-system user id apart */
    { { 0, 0, 0 }, { 0, 0, 0 }, M1, 2000, 2, { 2000, 2001 } },   /* 6: only the file-system group id apart; the effective group not in the list */
    { { 1000, 1000, 0 }, { 2000, 2000, 2000 }, M1, M1, 2, { 2000, 2001 } }, /* 7: only the saved id apart: the way back to root */
    { { 0, 0, 1000 }, { 0, 0, 2000 }, M1, M1, 2, { 2000, 2001 } },
    { { 0, 1000, 1000 }, { 2000, 2000, 2000 }, M1, M1, 2, { 2000, 2001 } },
    { { 1000, 1000, 1000 }, { 2000, 2000, 2001 }, M1, M1, 2, { 2000, 2001 } },
    { { 1000, 1000, 1000 }, { 2000, 2001, 2000 }, M1, M1, 2, { 2000, 2001 } },
    /* 12 on: which of the file-system ids, the list and being root decide AT_SECURE and dumpable */
    { { 1000, 1000, 1001 }, { 2000, 2000, 2000 }, 1001, M1, 2, { 2000, 2001 } }, /* a user's file-system user id apart */
    { { 1000, 1000, 1000 }, { 2000, 2000, 2002 }, M1, 2002, 2, { 2000, 2001 } }, /* a user's file-system group id apart; the effective group in the list */
    { { 1000, 1000, 1000 }, { 2000, 2000, 2002 }, M1, 2002, 1, { 7 } },          /* the same; not in the list */
    { { 0, 0, 0 }, { 0, 0, 0 }, M1, 2000, 2, { 0, 2000 } },      /* 6 with the effective group in the list */
    { { 0, 0, 0 }, { 2000, 2000, 0 }, M1, 0, 2, { 2000, 2001 } },
    { { 0, 0, 0 }, { 2000, 2000, 0 }, M1, 0, 1, { 7 } },
    { { 0, 0, 0 }, { 0, 0, 0 }, M1, M1, 0, { 0 } },
    { { 0, 0, 0 }, { 0, 0, 0 }, 1000, M1, 0, { 0 } },
    { { 0, 0, 0 }, { 0, 0, 0 }, M1, 2000, 0, { 0 } },
    { { 0, 0, 0 }, { 2000, 2000, 2000 }, M1, M1, 0, { 0 } },   /* the effective group in no list, nothing apart */
    { { 1000, 1000, 1000 }, { 2000, 2000, 2000 }, M1, M1, 0, { 0 } },
};

static void run_show(const char *path, const char *tag)
{
    char *av[] = { (char *)path, (char *)"show", (char *)tag, NULL };
    char *ev[] = { NULL };
    execve(path, av, ev);
    say("! execve %d\n", -errno);
    _exit(98);
}

static void section_exec(void)
{
    unsigned g2[2] = { 2000, 2001 };
    char tag[64];
    say("== execve: what the new program is, and what it is told\n");
    for (unsigned i = 0; i < sizeof ECASES / sizeof *ECASES; i++) {
        const struct ecase *c = &ECASES[i];
        pid_t p = fork();
        if (p == 0) {
            long a = rc(SYS_setgroups, c->ng, (long)c->gl, 0, 0, 0);
            long b = rc(SYS_setresgid, c->g[0], c->g[1], c->g[2], 0, 0);
            long d = rc(SYS_setresuid, c->u[0], c->u[1], c->u[2], 0, 0);
            if (c->fsu != M1) rc(SYS_setfsuid, c->fsu, 0, 0, 0, 0);
            if (c->fsg != M1) rc(SYS_setfsgid, c->fsg, 0, 0, 0, 0);
            if (a || b || d) { say("exec %u: cannot (%ld %ld %ld)\n", i, a, b, d); _exit(0); }
            snprintf(tag, sizeof tag, "exec %u before  ", i);
            show(tag);
            snprintf(tag, sizeof tag, "exec %u execve'd", i);
            run_show(SELF, tag);
        }
        reap(p);
    }
    if (!SETID) return;
    say("== execve of a set-ID file where the bits are not honoured\n");
    say("setid: the file is mode %o, owned %s\n", mode_of(SETID), own_of(SETID));
    for (int k = 0; k < 2; k++) {
        pid_t p = fork();
        if (p == 0) {
            if (k == 1) {
                long a = rc(SYS_setgroups, 2, (long)g2, 0, 0, 0), b = rc(SYS_setresgid, 2000, 2000, 2000, 0, 0);
                long d = rc(SYS_setresuid, 1000, 1000, 1000, 0, 0);
                if (a || b || d) { say("setid as (1000 1000 1000): cannot (%ld %ld %ld)\n", a, b, d); _exit(0); }
            }
            show(k ? "setid as (1000 1000 1000) before  " : "setid as the caller before  ");
            run_show(SETID, k ? "setid as (1000 1000 1000) execve'd" : "setid as the caller execve'd");
        }
        reap(p);
    }
}

/* --- G, H, I, J, K ---------------------------------------------------------------------- */

static void *thread_body(void *arg)
{
    *(long *)arg = rc(SYS_setresuid, 1000, 1000, 1000, 0, 0);
    return NULL;
}

static void section_processes(void)
{
    say("== a vfork child's ids are its own\n");
    {
        pid_t p = vfork();
        if (p == 0) {
            syscall(SYS_setresuid, 1000, 1000, 1000);
            _exit(0);
        }
        reap(p);
        say("vfork: the child called setresuid(1000, 1000, 1000) and ended; the parent is %s\n", uids());
    }
    say("== another process's status\n");
    {
        int pp[2], back[2];
        if (pipe(pp) != 0 || pipe(back) != 0) { say("! pipe %d\n", -errno); return; }
        pid_t p = fork();
        if (p == 0) {
            unsigned gl[2] = { 6, 5 };
            char b;
            close(pp[1]); close(back[0]);
            rc(SYS_setgroups, 2, (long)gl, 0, 0, 0);
            rc(SYS_setresgid, 2001, 2001, 2001, 0, 0);
            rc(SYS_setresuid, 1001, 1001, 1001, 0, 0);
            write(back[1], "r", 1);
            read(pp[0], &b, 1);
            _exit(0);
        }
        char b, path[64];
        close(pp[0]); close(back[1]);
        read(back[0], &b, 1);
        snprintf(path, sizeof path, "/proc/%d/status", (int)p);
        static const char *const want[] = { "Uid", "Gid", "Groups", "CapPrm", "CapEff" };
        for (unsigned i = 0; i < sizeof want / sizeof *want; i++) say("other: %s\n", raw(path, want[i]));
        close(pp[1]); close(back[0]);
        reap(p);
    }
    say("== ids and threads\n");
    {
        pid_t p = fork();
        if (p == 0) {
            pthread_t t;
            long r = 99;
            if (pthread_create(&t, NULL, thread_body, &r) != 0) { say("! pthread_create\n"); _exit(1); }
            pthread_join(t, NULL);
            say("~thread: a second thread's raw setresuid(1000, 1000, 1000) = %ld; the first thread's getuid is then %ld\n", r,
                rc(SYS_getuid, 0, 0, 0, 0, 0));
            _exit(0);
        }
        reap(p);
    }
    say("== the order that drops, and the order that does not\n");
    {
        unsigned gl[2] = { 1000, 2000 };
        pid_t p = fork();
        if (p == 0) {
            long a = rc(SYS_setgroups, 2, (long)gl, 0, 0, 0), b = rc(SYS_setgid, 1000, 0, 0, 0, 0), c = rc(SYS_setuid, 1000, 0, 0, 0, 0);
            say("drop: setgroups(2, {1000, 2000}) = %ld, setgid(1000) = %ld, setuid(1000) = %ld -> uid %s", a, b, c, uids());
            say(" gid %s groups '%s'\n", gids(), groups());
            say("drop: then setuid(0) = %ld, setgid(0) = %ld, setgroups(0, NULL) = %ld\n", rc(SYS_setuid, 0, 0, 0, 0, 0),
                rc(SYS_setgid, 0, 0, 0, 0, 0), rc(SYS_setgroups, 0, 0, 0, 0, 0));
            _exit(0);
        }
        reap(p);
        p = fork();
        if (p == 0) {
            long c = rc(SYS_setuid, 1000, 0, 0, 0, 0), b = rc(SYS_setgid, 2000, 0, 0, 0, 0), a = rc(SYS_setgroups, 2, (long)gl, 0, 0, 0);
            say("drop: the other way, setuid(1000) = %ld, setgid(2000) = %ld, setgroups(2, {1000, 2000}) = %ld -> uid %s", c, b, a, uids());
            say(" gid %s groups '%s'\n", gids(), groups());
            _exit(0);
        }
        reap(p);
    }
    say("== how many groups\n");
    {
        pid_t p = fork();
        if (p == 0) {
            unsigned gl[33], got[40], few[4] = { 9, 3, 5, 3 };
            for (int i = 0; i < 33; i++) gl[i] = 3000 - i;
            long a = rc(SYS_setgroups, 4, (long)few, 0, 0, 0);
            say("groups: setgroups(4, {9, 3, 5, 3}) = %ld -> '%s'\n", a, groups());
            a = rc(SYS_setgroups, 32, (long)gl, 0, 0, 0);
            long n = rc(SYS_getgroups, 40, (long)got, 0, 0, 0);
            say("groups: setgroups(32, {3000 down to 2969}) = %ld, getgroups(40, list) = %ld", a, n);
            if (n == 32) say(" (%u to %u)", got[0], got[31]);
            say("\n");
            say("groups: %s\n", raw("/proc/self/status", "Groups"));
            a = rc(SYS_setgroups, 33, (long)gl, 0, 0, 0);
            say("~bound: setgroups(33, list) = %ld, then getgroups(0, NULL) = %ld\n", a, rc(SYS_getgroups, 0, 0, 0, 0, 0));
            _exit(0);
        }
        reap(p);
    }
}

/* --- the soak -------------------------------------------------------------------------- */

static long memfree(void)
{
    const char *s = status_line("/proc/meminfo", "MemFree");
    return *s ? atol(s) : -1;
}

static int soak(long n)
{
    unsigned gl[32];
    long wrong = 0, calls = 0, forks = 0, mem[5];
    for (int i = 0; i < 32; i++) gl[i] = 4000 + i;
    int root = rc(SYS_geteuid, 0, 0, 0, 0, 0) == 0;
    long me = rc(SYS_getuid, 0, 0, 0, 0, 0), mine = rc(SYS_getgid, 0, 0, 0, 0, 0);
    mem[0] = memfree();
    for (long i = 0; i < n; i++) {
        if (root) {
            /* out and back: the effective ids, the file-system id, the groups */
            wrong += rc(SYS_setresuid, -1, 1000, -1, 0, 0) != 0;
            wrong += rc(SYS_setgroups, 32, (long)gl, 0, 0, 0) != -1; /* no longer privileged */
            wrong += rc(SYS_setfsuid, 0, 0, 0, 0, 0) != 1000;
            wrong += rc(SYS_setresuid, -1, 0, -1, 0, 0) != 0;
            wrong += rc(SYS_setresgid, -1, 2000, -1, 0, 0) != 0;
            wrong += rc(SYS_setregid, -1, 0, 0, 0, 0) != 0;
            wrong += rc(SYS_setgroups, 32, (long)gl, 0, 0, 0) != 0;
            wrong += rc(SYS_getgroups, 0, 0, 0, 0, 0) != 32;
            wrong += rc(SYS_setgroups, 0, 0, 0, 0, 0) != 0;
            wrong += rc(SYS_geteuid, 0, 0, 0, 0, 0) != 0;
        } else {
            /* a user: what is allowed changes nothing, what would change something is refused */
            wrong += rc(SYS_setresuid, me, me, me, 0, 0) != 0;
            wrong += rc(SYS_setuid, 0, 0, 0, 0, 0) != -1;
            wrong += rc(SYS_setfsuid, 0, 0, 0, 0, 0) != me;
            wrong += rc(SYS_setreuid, me, -1, 0, 0, 0) != 0;
            wrong += rc(SYS_setresgid, mine, mine, mine, 0, 0) != 0;
            wrong += rc(SYS_setgid, 0, 0, 0, 0, 0) != -1;
            wrong += rc(SYS_setgroups, 32, (long)gl, 0, 0, 0) != -1;
            wrong += rc(SYS_getgroups, 0, 0, 0, 0, 0) != 0;
            wrong += rc(SYS_setfsgid, 0, 0, 0, 0, 0) != mine;
            wrong += rc(SYS_geteuid, 0, 0, 0, 0, 0) != me;
        }
        calls += 10;
        if (i % 10 == 9) {
            pid_t p = fork();
            if (p == 0) {
                long bad = 0;
                if (root) {
                    bad += rc(SYS_setgroups, 32, (long)gl, 0, 0, 0) != 0;
                    bad += rc(SYS_setresgid, 2000, 2000, 2000, 0, 0) != 0;
                    bad += rc(SYS_setresuid, 1000, 1000, 1000, 0, 0) != 0;
                    bad += rc(SYS_setuid, 0, 0, 0, 0, 0) != -1;
                }
                bad += rc(SYS_getuid, 0, 0, 0, 0, 0) != 1000;
                _exit(bad ? 1 : 0);
            }
            wrong += reap(p) != 0;
            wrong += rc(SYS_getuid, 0, 0, 0, 0, 0) != me; /* the child's change is the child's */
            forks++;
        }
        if (n >= 4 && (i + 1) % (n / 4) == 0 && (i + 1) / (n / 4) <= 4) mem[(i + 1) / (n / 4)] = memfree();
    }
    say("soak: %ld rounds, %ld calls, %ld children that changed their ids, %ld wrong answers -> uid %s", n, calls, forks, wrong, uids());
    say(" gid %s groups '%s'\n", gids(), groups());
    say("~soak: MemFree before %ld kB, at each quarter %ld %ld %ld %ld kB\n", mem[0], mem[1], mem[2], mem[3], mem[4]);
    return wrong ? 1 : 0;
}

int main(int argc, char **argv)
{
    if (argc > 2 && strcmp(argv[1], "show") == 0) { show(argv[2]); return 0; }
    if (argc > 2 && strcmp(argv[1], "soak") == 0) return soak(atol(argv[2]));
    long n = readlink("/proc/self/exe", SELF, sizeof SELF - 1);
    if (n <= 0) { say("! no /proc/self/exe\n"); return 1; }
    SELF[n] = 0;
    SETID = argc > 1 && strcmp(argv[1], "-") != 0 ? argv[1] : NULL;
    show("start");
    say("/proc/self/setgroups: mode %o\n", mode_of("/proc/self/setgroups"));
    say("owner: /proc/self/setgroups is owned %s\n", own_of("/proc/self/setgroups")); /* px42: a /proc file has its process's owner */
    section_states();
    section_faults();
    section_width();
    section_dump();
    section_exec();
    section_processes();
    say("ident: done\n");
    return 0;
}
