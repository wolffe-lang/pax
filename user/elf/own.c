/* own.c — px42: who a file belongs to. What px38's `perm` did not ask
 * of Linux about owners: what a new name is stamped with, the four
 * calls of the `chown` family by root and by a user, what `stat`,
 * `statx` and /proc report, and a soak. Static; every call under test
 * is a raw syscall; root builds each case and a fresh child that has
 * become a user tries it and prints the kernel's answer.
 *
 *   own DIR           DIR is made (mode 0777) on a tmpfs; removed again
 *   own soak N DIR    N rounds of making, chown and removing
 *   own self          (what the probe execs of itself: its /proc lines)
 *
 * Started by a process that is not root (`as 1000 1000 own DIR`) it
 * asks only what a user can set up for himself. A line that starts
 * with `~` is what PAX answers by rule and is not compared.
 *
 * Written from chown(2), fchownat(2), stat(2), statx(2), inode(7),
 * mkdir(2), open(2), symlink(2), link(2), unix(7), proc(5) and the uapi
 * headers; no kernel's or libc's source. */
#include "px38.h"
#include <sys/socket.h>
#include <sys/sysmacros.h>
#include <sys/un.h>
#include <time.h>

static const char *D;
static char SELF[256];
static char PB[8][600];
static int pbi;
static const char *in(const char *n)
{
    char *p = PB[pbi++ & 7];
    snprintf(p, 600, "%s/%s", D, n);
    return p;
}

struct who { const char *name; unsigned uid, gid; int ng; unsigned gs[2]; };
static const struct who W[] = {
    { "own ", 1000, 2999, 0, { 0, 0 } },      /* the owner, not in the group */
    { "mem ", 1000, 2999, 2, { 2000, 2001 } }, /* the owner, in the group and in 2001 */
    { "grp ", 1001, 2000, 0, { 0, 0 } },      /* in the group, not the owner */
    { "oth ", 1002, 2999, 0, { 0, 0 } },
    { "root", 0, 0, 0, { 0, 0 } },
};
enum { OWN, MEM, GRP, OTH, ROOT, NW };
static const char *cur;

static void as(int a, void (*fn)(long), long arg)
{
    pid_t p = fork();
    if (p == 0) {
        if (W[a].uid != 0) become(W[a].uid, W[a].gid, W[a].ng, W[a].gs);
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        cur = W[a].name;
        fn(arg);
        _exit(0);
    }
    int st = reap(p);
    if (st != 0) say("! actor %s failed (%d)\n", W[a].name, st);
}

static const char *om(const char *p)
{
    static char o[8][96];
    static int k;
    char *s = o[k++ & 7];
    snprintf(s, 96, "%s %04o", own_of(p), mode_of(p));
    return s;
}

static long ctime_ns(const char *p)
{
    struct stat s;
    if (lstat(p, &s) != 0) return -1;
    return (long)s.st_ctim.tv_sec * 1000000000L + s.st_ctim.tv_nsec;
}

static void nap(void)
{
    struct timespec t = { 0, 30000000 };
    nanosleep(&t, NULL);
}

static int bind_at(const char *p)
{
    struct sockaddr_un a;
    memset(&a, 0, sizeof a);
    a.sun_family = AF_UNIX;
    snprintf(a.sun_path, sizeof a.sun_path, "%s", p);
    int s = socket(AF_UNIX, SOCK_STREAM, 0);
    if (s < 0) return -errno;
    if (bind(s, (struct sockaddr *)&a, sizeof a) != 0) { int e = errno; close(s); return -e; }
    return s;
}

/* --- S: the stamps ---------------------------------------------------------- */
static void made_in(const char *d, const char *what)
{
    char f[64], dd[64], l[64], s[64], x[64], g[64], h[64];
    snprintf(f, sizeof f, "%s/f", d); snprintf(dd, sizeof dd, "%s/d", d); snprintf(l, sizeof l, "%s/l", d);
    snprintf(s, sizeof s, "%s/s", d); snprintf(x, sizeof x, "%s/x", d); snprintf(g, sizeof g, "%s/g", d);
    snprintf(h, sizeof h, "%s/h", d);
    int fd = open(in(f), O_WRONLY | O_CREAT | O_EXCL, 0666); if (fd >= 0) close(fd);
    mkdir(in(dd), 0777);
    symlink("f", in(l));
    int sk = bind_at(in(s));
    say("made %s in %s: a file %s; a directory %s; a symbolic link %s; a socket %s\n", cur, what, om(in(f)), om(in(dd)), om(in(l)), om(in(s)));
    if (sk >= 0) close(sk);
    char y[64], z[64];
    snprintf(y, sizeof y, "%s/y", d); snprintf(z, sizeof z, "%s/z", d);
    fd = open(in(x), O_WRONLY | O_CREAT | O_EXCL, 06777); if (fd >= 0) close(fd);
    fd = open(in(y), O_WRONLY | O_CREAT | O_EXCL, 02666); if (fd >= 0) close(fd);
    fd = open(in(z), O_WRONLY | O_CREAT | O_EXCL, 01644); if (fd >= 0) close(fd);
    mkdir(in(g), 02777);
    mkdir(in(h), 01777);
    say("made %s in %s: a file with mode 06777 %s, with 02666 %s, with 01644 %s; a directory with mode 02777 %s, with 01777 %s\n", cur, what,
        om(in(x)), om(in(y)), om(in(z)), om(in(g)), om(in(h)));
    unlink(in(f)); rmdir(in(dd)); unlink(in(l)); unlink(in(s)); unlink(in(x)); unlink(in(y)); unlink(in(z)); rmdir(in(g)); rmdir(in(h));
}

static void stamp_row(long unused)
{
    (void)unused;
    umask(022);
    made_in("p0", "a 0777 directory of 0:2000");
    made_in("pg", "a 2777 directory of 0:2000");
}

static void stamp_fs(long unused)
{
    (void)unused;
    /* the file-system ids apart from the effective ones: (1001 1001 1002), fs 1002; groups the same way */
    rc(SYS_setgroups, 0, 0, 0, 0, 0);
    rc(SYS_setresgid, 2001, 2001, 2002, 0, 0);
    rc(SYS_setresuid, 1001, 1001, 1002, 0, 0);
    rc(SYS_setfsuid, 1002, 0, 0, 0, 0);
    rc(SYS_setfsgid, 2002, 0, 0, 0, 0);
    umask(022);
    mkdir(in("p0/d"), 0777);
    symlink("f", in("p0/l"));
    int sk = bind_at(in("p0/s"));
    say("made by uid %s", uids());
    say(" gid %s: a directory %s; a symbolic link %s; a socket %s\n", gids(), om(in("p0/d")), om(in("p0/l")), om(in("p0/s")));
    if (sk >= 0) close(sk);
    rmdir(in("p0/d")); unlink(in("p0/l")); unlink(in("p0/s"));
}

static void stamp_kept(long unused)
{
    (void)unused;
    /* root's file 1000:2000; what oth does to it changes no owner */
    long a = link(in("p0/k"), in("p0/k2")) == 0 ? 0L : -(long)errno;
    const char *o1 = om(in("p0/k2"));
    long b = rename(in("p0/k"), in("p0/k3")) == 0 ? 0L : -(long)errno;
    const char *o2 = om(in("p0/k3"));
    int fd = open(in("p0/k3"), O_WRONLY | O_APPEND);
    long c = fd >= 0 ? write(fd, "x", 1) : -(long)errno;
    if (fd >= 0) close(fd);
    say("kept %s: a hard link to 1000:2000's file %ld: %s; renamed %ld: %s; written %ld: %s\n", cur, a, o1, b, o2, c, om(in("p0/k3")));
    unlink(in("p0/k2"));
    rename(in("p0/k3"), in("p0/k"));
}

/* --- C: the chown family ------------------------------------------------------ */
static const long T[][2] = { { -1, -1 }, { 1000, -1 }, { -1, 2000 }, { -1, 2999 }, { -1, 2001 }, { 1001, -1 }, { 0, 0 } };
#define NT 7

static void reset_fo(void)
{
    put_file(in("fo"), "o\n", 06755, 1000, 2000);
    chown(in("fo"), 1000, 2000);
    chmod(in("fo"), 06755);
    unlink(in("lo"));
    symlink("fo", in("lo"));
    lchown(in("lo"), 1000, 2000);
}

/* which: form * 16 + target */
static void family_row(long which)
{
    int form = which / 16, t = which % 16;
    long u = T[t][0], g = T[t][1], r = 0;
    const char *f = in("fo"), *name = "";
    int fd = -1;
    switch (form) {
    case 0: name = "fchown"; fd = open(f, O_RDONLY); r = fd < 0 ? 7000 + errno : rc(SYS_fchown, fd, u, g, 0, 0); break;
    case 1: name = "lchown"; r = rc(SYS_lchown, (long)f, u, g, 0, 0); break;
    case 2: name = "fchownat(0)"; r = rc(SYS_fchownat, AT_FDCWD, (long)f, u, g, 0); break;
    case 3: name = "fchownat(AT_SYMLINK_NOFOLLOW)"; r = rc(SYS_fchownat, AT_FDCWD, (long)f, u, g, AT_SYMLINK_NOFOLLOW); break;
    case 4: name = "fchownat(AT_EMPTY_PATH)"; fd = open(f, O_RDONLY); r = fd < 0 ? 7000 + errno : rc(SYS_fchownat, fd, (long)"", u, g, AT_EMPTY_PATH); break;
    }
    if (fd >= 0) close(fd);
    say("%s %s (file 1000:2000 mode 6755): (%ld, %ld) = %ld (%s)\n", name, cur, u, g, r, om(f));
}

static void link_row(long t)
{
    long u = T[t][0], g = T[t][1];
    long a = rc(SYS_lchown, (long)in("lo"), u, g, 0, 0);
    const char *l1 = om(in("lo")), *f1 = om(in("fo"));
    long b = rc(SYS_fchownat, AT_FDCWD, (long)in("lo"), u, g, AT_SYMLINK_NOFOLLOW);
    long c = rc(SYS_chown, (long)in("lo"), u, g, 0, 0);
    say("link %s (a link 1000:2000 to a file 1000:2000 mode 6755): lchown(%ld, %ld) = %ld (the link %s, the file %s); fchownat(AT_SYMLINK_NOFOLLOW) %ld; chown through it %ld (the link %s, the file %s)\n",
        cur, u, g, a, l1, f1, b, c, om(in("lo")), om(in("fo")));
}

static void ctime_row(long unused)
{
    (void)unused;
    const char *f = in("fo");
    long c0 = ctime_ns(f);
    nap();
    long a = rc(SYS_chown, (long)f, -1, -1, 0, 0);
    long c1 = ctime_ns(f);
    nap();
    long b = rc(SYS_chown, (long)f, 1001, 2001, 0, 0);
    long c2 = ctime_ns(f);
    nap();
    long c = rc(SYS_chown, (long)f, -1, 2999, 0, 0);
    long c3 = ctime_ns(f);
    say("ctime %s: chown(-1, -1) = %ld moved it %d; chown(1001, 2001) = %ld moved it %d; chown(-1, 2999) = %ld moved it %d\n", cur, a, c1 > c0, b,
        c2 > c1, c, c3 > c2);
}

static void error_row(long unused)
{
    (void)unused;
    char longname[400];
    memset(longname, 'n', sizeof longname - 1);
    longname[sizeof longname - 1] = 0;
    char lp[1100];
    snprintf(lp, sizeof lp, "%s/%s", D, longname);
    say("errors %s: a missing name %ld; a name under a file %ld; a bad pointer %ld; a name of 399 bytes %ld; an empty name %ld; fchown of a closed descriptor %ld; fchownat with a flag that is not one %ld; with AT_EMPTY_PATH and a closed descriptor %ld\n",
        cur, rc(SYS_chown, (long)in("nope"), -1, -1, 0, 0), rc(SYS_chown, (long)in("fo/x"), -1, -1, 0, 0), rc(SYS_chown, 8, -1, -1, 0, 0),
        rc(SYS_chown, (long)lp, -1, -1, 0, 0), rc(SYS_chown, (long)"", -1, -1, 0, 0), rc(SYS_fchown, 99, -1, -1, 0, 0),
        rc(SYS_fchownat, AT_FDCWD, (long)in("fo"), -1, -1, 0x8000), rc(SYS_fchownat, 99, (long)"", -1, -1, AT_EMPTY_PATH));
}

static void other_row(long unused)
{
    (void)unused;
    /* a directory 1000:2000 mode 6755 and a socket's name 1000:2000, each by chown(-1, 2999) */
    long a = rc(SYS_chown, (long)in("do"), -1, 2999, 0, 0);
    const char *o1 = om(in("do"));
    long b = rc(SYS_chown, (long)in("so"), -1, 2999, 0, 0);
    say("other %s: a directory 1000:2000 mode 6755, chown(-1, 2999) = %ld (%s); a socket's name 1000:2000, chown(-1, 2999) = %ld (%s)\n", cur, a,
        o1, b, om(in("so")));
}

/* a chown that asks for nothing, or for what the file already has */
static void noop_reset(void)
{
    put_file(in("n0"), "n\n", 0644, 1000, 2000);
    put_file(in("n2"), "n\n", 02644, 1000, 2000);
    put_file(in("n4"), "n\n", 04644, 1000, 2000);
    mkdir(in("nd"), 0755); chown(in("nd"), 1000, 2000); chmod(in("nd"), 06755);
}

static void noop_row(long unused)
{
    (void)unused;
    static const char *N[] = { "n0", "n2", "n4", "nd" };
    long r[4];
    int mv[4];
    char o[4][96];
    for (int i = 0; i < 4; i++) {
        long c0 = ctime_ns(in(N[i]));
        nap();
        r[i] = rc(SYS_chown, (long)in(N[i]), -1, -1, 0, 0);
        mv[i] = ctime_ns(in(N[i])) > c0;
        snprintf(o[i], sizeof o[i], "%s", om(in(N[i])));
    }
    say("nothing asked %s, chown(-1, -1): of a 0644 file 1000:2000 %ld, ctime moved %d (%s); of a 2644 file %ld, %d (%s); of a 4644 file %ld, %d (%s); of a 6755 directory %ld, %d (%s)\n",
        cur, r[0], mv[0], o[0], r[1], mv[1], o[1], r[2], mv[2], o[2], r[3], mv[3], o[3]);
    const char *f = in("n0");
    long c0 = ctime_ns(f);
    nap();
    long a = rc(SYS_chown, (long)f, 1000, -1, 0, 0);
    long c1 = ctime_ns(f);
    nap();
    long b = rc(SYS_chown, (long)f, -1, 2000, 0, 0);
    long c2 = ctime_ns(f);
    nap();
    long c = rc(SYS_lchown, (long)f, 1000, 2000, 0, 0);
    long c3 = ctime_ns(f);
    say("what it has %s (a 0644 file 1000:2000): chown(1000, -1) = %ld, ctime moved %d; chown(-1, 2000) = %ld, %d; lchown(1000, 2000) = %ld, %d (%s)\n", cur,
        a, c1 > c0, b, c2 > c1, c, c3 > c2, om(f));
    /* a set-group-ID bit without group execute, and a new group the caller is in or is not */
    long d = rc(SYS_chown, (long)in("n2"), -1, 2999, 0, 0);
    const char *o1 = om(in("n2"));
    chmod(in("n2"), 02644); /* the owner's and root's only */
    long e = rc(SYS_chown, (long)in("n2"), -1, 2000, 0, 0);
    say("a 2644 file %s: chown(-1, 2999) = %ld (%s); made 2644 again, chown(-1, 2000) = %ld (%s)\n", cur, d, o1, e, om(in("n2")));
}

static void width_row(long unused)
{
    (void)unused;
    const char *f = in("fo");
    long a = rc(SYS_chown, (long)f, 0x1000003e9L, 0x1000007d1L, 0, 0);
    const char *o1 = om(f);
    long b = rc(SYS_chown, (long)f, 0x1ffffffffL, 0x2ffffffffL, 0, 0);
    const char *o2 = om(f);
    long c = rc(SYS_chown, (long)f, 4294967294L, 4294967294L, 0, 0);
    say("width root: chown(0x1000003e9, 0x1000007d1) = %ld (%s); chown(0x1ffffffff, 0x2ffffffff) = %ld (%s); chown(4294967294, 4294967294) = %ld (%s)\n",
        a, o1, b, o2, c, om(f));
}

/* the file-system ids decide, not the effective ones */
static void fsid_rows(void)
{
    pid_t p;
    reset_fo();
    p = fork();
    if (p == 0) {
        long a = rc(SYS_setfsuid, 1002, 0, 0, 0, 0);
        long r1 = rc(SYS_chown, (long)in("fo"), 1001, -1, 0, 0);
        const char *o1 = om(in("fo"));
        long r2 = rc(SYS_chown, (long)in("f2"), -1, 0, 0, 0);
        const char *o2 = om(in("f2"));
        long r3 = rc(SYS_chown, (long)in("f2"), -1, 2001, 0, 0);
        say("fsid: root after setfsuid(1002) = %ld (uid %s): chown(1001, -1) of 1000's file %ld (%s);", a, uids(), r1, o1);
        say(" chown(-1, 0) of 1002's file %ld (%s); chown(-1, 2001) of it %ld (%s)\n", r2, o2, r3, om(in("f2")));
        _exit(0);
    }
    reap(p);
    reset_fo();
    p = fork();
    if (p == 0) {
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
        rc(SYS_setresuid, 0, 1002, 0, 0, 0);
        long a = rc(SYS_setfsuid, 0, 0, 0, 0, 0);
        long r1 = rc(SYS_chown, (long)in("fo"), 1001, 2001, 0, 0);
        say("fsid: (0 1002 0) after setfsuid(0) = %ld (uid %s): chown(1001, 2001) of 1000's file %ld (%s)\n", a, uids(), r1, om(in("fo")));
        _exit(0);
    }
    reap(p);
    reset_fo();
    p = fork();
    if (p == 0) {
        /* the owner; real group 2000, effective and saved 2999; then the file-system group back to 2000 */
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2001, 2999, 2999, 0, 0);
        rc(SYS_setresuid, 1000, 1000, 1000, 0, 0);
        long a = rc(SYS_chown, (long)in("fo"), -1, 2001, 0, 0);
        const char *o1 = om(in("fo"));
        long s = rc(SYS_setfsgid, 2001, 0, 0, 0, 0);
        long b = rc(SYS_chown, (long)in("fo"), -1, 2001, 0, 0);
        const char *o2 = om(in("fo"));
        long c = rc(SYS_chown, (long)in("fo"), -1, 2999, 0, 0);
        say("fsid: the owner with gid %s: chown(-1, 2001) = %ld (%s); after setfsgid(2001) = %ld: chown(-1, 2001) = %ld (%s); chown(-1, 2999) = %ld (%s)\n",
            gids(), a, o1, s, b, o2, c, om(in("fo")));
        _exit(0);
    }
    reap(p);
    reset_fo();
    p = fork();
    if (p == 0) {
        /* 1000's file, by one whose effective id is 1000 and file-system id 1001, and the reverse */
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
        rc(SYS_setresuid, 1001, 1000, 1001, 0, 0);
        long s = rc(SYS_setfsuid, 1001, 0, 0, 0, 0);
        long a = rc(SYS_chown, (long)in("fo"), -1, 2999, 0, 0);
        const char *o1 = om(in("fo"));
        rc(SYS_setresuid, 1000, 1001, 1000, 0, 0);
        long s2 = rc(SYS_setfsuid, 1000, 0, 0, 0, 0);
        long b = rc(SYS_chown, (long)in("fo"), -1, 2999, 0, 0);
        say("fsid: effective 1000, setfsuid(1001) = %ld: chown(-1, 2999) of 1000's file %ld (%s); effective 1001, setfsuid(1000) = %ld: %ld (%s)\n", s,
            a, o1, s2, b, om(in("fo")));
        _exit(0);
    }
    reap(p);
}

/* --- R: what is reported ------------------------------------------------------- */
static void report_row(long unused)
{
    (void)unused;
    const char *f = in("fo");
    struct stat s;
    unsigned char sx[256];
    memset(sx, 0, sizeof sx);
    unsigned su = 77, sg = 77, lu = 77, lg = 77, fu = 77, fg = 77, au = 77, ag = 77;
    if (stat(f, &s) == 0) { su = s.st_uid; sg = s.st_gid; }
    if (lstat(in("lo"), &s) == 0) { lu = s.st_uid; lg = s.st_gid; }
    int fd = open(f, O_RDONLY);
    if (fd >= 0 && fstat(fd, &s) == 0) { fu = s.st_uid; fg = s.st_gid; }
    if (fd >= 0) close(fd);
    if (fstatat(AT_FDCWD, f, &s, 0) == 0) { au = s.st_uid; ag = s.st_gid; }
    long x = rc(SYS_statx, AT_FDCWD, (long)f, 0, 0x7ff, (long)sx);
    unsigned xu, xg, xm;
    memcpy(&xm, sx, 4); memcpy(&xu, sx + 20, 4); memcpy(&xg, sx + 24, 4);
    say("report: a file 1001:2001: stat %u:%u; lstat of a link 1002:2002 to it %u:%u; fstat %u:%u; newfstatat %u:%u; statx %ld %u:%u, its mask has STATX_UID %d and STATX_GID %d\n",
        su, sg, lu, lg, fu, fg, au, ag, x, xu, xg, (xm & 8) != 0, (xm & 16) != 0);
}

static void desc_row(long unused)
{
    (void)unused;
    int p[2] = { -1, -1 }, sp[2] = { -1, -1 };
    struct stat a, b, c;
    memset(&a, 0, sizeof a); memset(&b, 0, sizeof b); memset(&c, 0, sizeof c);
    if (pipe(p) != 0) say("! pipe %d\n", errno);
    else fstat(p[0], &a);
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sp) != 0) say("! socketpair %d\n", errno);
    else fstat(sp[0], &b);
    int s = socket(AF_UNIX, SOCK_STREAM, 0);
    if (s >= 0) fstat(s, &c);
    say("~desc %s: a pipe it made is %u:%u, a socketpair %u:%u, a socket %u:%u\n", cur, a.st_uid, a.st_gid, b.st_uid, b.st_gid, c.st_uid, c.st_gid);
}

static const char *dump(void)
{
    static char o[16];
    snprintf(o, sizeof o, "%ld", rc(SYS_prctl, 3 /* PR_GET_DUMPABLE */, 0, 0, 0, 0));
    return o;
}

static void proc_self(const char *when)
{
    char d[64], st[64], sg[64];
    snprintf(d, sizeof d, "/proc/%d", getpid());
    snprintf(st, sizeof st, "/proc/%d/status", getpid());
    snprintf(sg, sizeof sg, "/proc/%d/setgroups", getpid());
    struct stat s;
    unsigned mu = 77, mg = 77;
    if (stat("/proc/self", &s) == 0) { mu = s.st_uid; mg = s.st_gid; }
    say("proc %s (uid %s", when, uids());
    say(" gid %s dumpable %s): /proc/self %u:%u, /proc/<pid> %s, its status %s, its setgroups %s, /proc/self/status %s\n", gids(), dump(), mu, mg,
        om(d), om(st), om(sg), om("/proc/self/status"));
}

static void proc_rows(void)
{
    pid_t p;
    proc_self("root");
    p = fork();
    if (p == 0) {
        become(1000, 2000, 0, W[0].gs);
        proc_self("a user, ids just changed");
        char *av[] = { SELF, (char *)"self", (char *)"a user, after execve", NULL };
        char *ev[] = { NULL };
        execve(SELF, av, ev);
        _exit(98);
    }
    reap(p);
    p = fork();
    if (p == 0) {
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        rc(SYS_setresgid, 2000, 2001, 2002, 0, 0);
        rc(SYS_setresuid, 1000, 1001, 1002, 0, 0);
        proc_self("ids apart, just changed");
        char *av[] = { SELF, (char *)"self", (char *)"ids apart, after execve", NULL };
        char *ev[] = { NULL };
        execve(SELF, av, ev);
        _exit(98);
    }
    reap(p);
    /* another process's: a user's child, read by root while it waits */
    int go[2], back[2];
    if (pipe(go) != 0 || pipe(back) != 0) { say("! pipe\n"); return; }
    p = fork();
    if (p == 0) {
        close(go[1]); close(back[0]);
        become(1001, 2001, 0, W[0].gs);
        char *av[] = { SELF, (char *)"wait", NULL };
        char *ev[] = { NULL };
        dup2(go[0], 0); dup2(back[1], 1);
        execve(SELF, av, ev);
        _exit(98);
    }
    close(go[0]); close(back[1]);
    char b;
    if (read(back[0], &b, 1) != 1) say("! the child did not start\n");
    char d[64], st[64], sg[64];
    snprintf(d, sizeof d, "/proc/%d", p); snprintf(st, sizeof st, "/proc/%d/status", p); snprintf(sg, sizeof sg, "/proc/%d/setgroups", p);
    say("proc of another, read by root: a child that is 1001:2001 after execve: /proc/<pid> %s, its status %s, its setgroups %s\n", om(d), om(st),
        om(sg));
    say("proc, the fixed names: /proc %s, /proc/meminfo %s, /dev/null %s\n", om("/proc"), om("/proc/meminfo"), om("/dev/null"));
    close(go[1]);
    reap(p);
    close(back[0]);
}

/* --- U: started by a user ------------------------------------------------------- */
static int user_main(void)
{
    unsigned me = getuid(), g = getgid();
    say("own: started as uid %s", uids());
    say(" gid %s groups '%s'\n", gids(), groups());
    umask(022);
    if (mkdir(D, 0777) != 0) { say("! mkdir %s: %d\n", D, -errno); return 1; }
    chmod(D, 0777);
    cur = "user";
    int fd = open(in("f"), O_WRONLY | O_CREAT | O_EXCL, 0666); if (fd >= 0) close(fd);
    mkdir(in("d"), 0777);
    symlink("f", in("l"));
    int sk = bind_at(in("s"));
    say("made user: a file %s; a directory %s; a symbolic link %s; a socket %s\n", om(in("f")), om(in("d")), om(in("l")), om(in("s")));
    if (sk >= 0) close(sk);
    unlink(in("s"));
    chmod(in("f"), 06755);
    const char *f = in("f");
    long a = rc(SYS_chown, (long)f, -1, -1, 0, 0);
    const char *o1 = om(f);
    chmod(f, 06755);
    long b = rc(SYS_chown, (long)f, me, g, 0, 0);
    const char *o2 = om(f);
    chmod(f, 06755);
    long c = rc(SYS_chown, (long)f, -1, 2000, 0, 0);
    const char *o3 = om(f);
    long d = rc(SYS_chown, (long)f, 1001, -1, 0, 0);
    long e = rc(SYS_chown, (long)f, 0, 0, 0, 0);
    say("chown user (its own file, mode 6755 each time): (-1, -1) = %ld (%s); (its uid, its gid) = %ld (%s); (-1, 2000) = %ld (%s); (1001, -1) = %ld; (0, 0) = %ld (%s)\n",
        a, o1, b, o2, c, o3, d, e, om(f));
    fd = open(f, O_RDONLY);
    long h = rc(SYS_fchown, fd, -1, g, 0, 0), i = rc(SYS_fchown, fd, 0, -1, 0, 0);
    if (fd >= 0) close(fd);
    long j = rc(SYS_lchown, (long)in("l"), -1, g, 0, 0), k = rc(SYS_lchown, (long)in("l"), 0, -1, 0, 0);
    long m = rc(SYS_fchownat, AT_FDCWD, (long)in("d"), -1, g, 0), n = rc(SYS_fchownat, AT_FDCWD, (long)in("d"), -1, 0, 0);
    say("chown user: fchown(-1, its gid) %ld, (0, -1) %ld; lchown of its link (-1, its gid) %ld, (0, -1) %ld; fchownat of its directory (-1, its gid) %ld, (-1, 0) %ld\n",
        h, i, j, k, m, n);
    say("chown user, root's things: chown(-1, -1) of / %ld; of its own program %ld; chown(its uid, -1) of it %ld; a missing name %ld\n",
        rc(SYS_chown, (long)"/", -1, -1, 0, 0), rc(SYS_chown, (long)SELF, -1, -1, 0, 0), rc(SYS_chown, (long)SELF, me, -1, 0, 0),
        rc(SYS_chown, (long)in("nope"), -1, -1, 0, 0));
    proc_self("user");
    desc_row(0);
    unlink(in("f")); rmdir(in("d")); unlink(in("l"));
    say("own: gone: rmdir %ld\n", rmdir(D) == 0 ? 0L : -(long)errno);
    say("own: done\n");
    return 0;
}

/* --- the soak ------------------------------------------------------------------ */
static long memfree(void)
{
    const char *s = status_line("/proc/meminfo", "MemFree");
    return atol(s);
}

static int soak(long n)
{
    int root = getuid() == 0;
    unsigned me = getuid(), g = getgid();
    long wrong = 0, calls = 0, mem[5] = { 0, 0, 0, 0, 0 };
    struct stat s;
    umask(022);
    if (mkdir(D, 0777) != 0) { say("! mkdir %s: %d\n", D, -errno); return 1; }
    mem[0] = memfree();
    for (long i = 0; i < n; i++) {
        unsigned u = root ? 1000 + i % 7 : me, gg = root ? 2000 + i % 5 : g;
        const char *f = in("f"), *d = in("d"), *l = in("l");
        int fd = open(f, O_WRONLY | O_CREAT | O_EXCL, 04755);
        wrong += fd < 0;
        wrong += rc(SYS_fchown, fd, u, gg, 0, 0) != 0;
        if (fd >= 0) close(fd);
        wrong += stat(f, &s) != 0 || s.st_uid != u || s.st_gid != gg || (s.st_mode & 07777) != 0755;
        wrong += mkdir(d, 0755) != 0;
        wrong += rc(SYS_chown, (long)d, -1, gg, 0, 0) != 0;
        wrong += symlink("f", l) != 0;
        wrong += rc(SYS_lchown, (long)l, u, -1, 0, 0) != 0;
        wrong += lstat(l, &s) != 0 || s.st_uid != u;
        if (root) wrong += rc(SYS_fchownat, AT_FDCWD, (long)f, 0, 0, 0) != 0;
        else wrong += rc(SYS_fchownat, AT_FDCWD, (long)f, 0, 0, 0) != -1;
        wrong += unlink(l) != 0;
        wrong += rmdir(d) != 0;
        wrong += unlink(f) != 0;
        calls += 12;
        if (n >= 4 && (i + 1) % (n / 4) == 0 && (i + 1) / (n / 4) <= 4) mem[(i + 1) / (n / 4)] = memfree();
    }
    wrong += rmdir(D) != 0;
    say("soak: %ld rounds, %ld calls that make, chown and remove, %ld wrong answers, as uid %u\n", n, calls, wrong, me);
    say("~soak: MemFree before %ld kB, at each quarter %ld %ld %ld %ld kB\n", mem[0], mem[1], mem[2], mem[3], mem[4]);
    return wrong ? 1 : 0;
}

int main(int argc, char **argv)
{
    if (argc > 2 && strcmp(argv[1], "self") == 0) { proc_self(argv[2]); return 0; }
    if (argc > 1 && strcmp(argv[1], "wait") == 0) {
        char b = 'k';
        write(1, &b, 1);
        read(0, &b, 1);
        return 0;
    }
    if (argc > 3 && strcmp(argv[1], "soak") == 0) { D = argv[3]; return soak(atol(argv[2])); }
    if (argc < 2) { say("usage: own DIR | own soak N DIR\n"); return 2; }
    D = argv[1];
    long n = readlink("/proc/self/exe", SELF, sizeof SELF - 1);
    if (n <= 0) { say("! no /proc/self/exe\n"); return 1; }
    SELF[n] = 0;
    if (getuid() != 0) return user_main();
    umask(0);
    if (mkdir(D, 0777) != 0) { say("! mkdir %s: %d\n", D, -errno); return 1; }
    chmod(D, 0777);

    say("== S: what a new name is stamped with\n");
    mkdir(in("p0"), 0777); chown(in("p0"), 0, 2000); chmod(in("p0"), 0777);
    mkdir(in("pg"), 0777); chown(in("pg"), 0, 2000); chmod(in("pg"), 02777);
    for (int a = 0; a < NW; a++) as(a, stamp_row, 0);
    {
        pid_t p = fork();
        if (p == 0) { stamp_fs(0); _exit(0); }
        reap(p);
    }
    put_file(in("p0/k"), "k\n", 0666, 1000, 2000);
    as(OTH, stamp_kept, 0);
    as(ROOT, stamp_kept, 0);
    unlink(in("p0/k"));
    rmdir(in("p0")); rmdir(in("pg"));

    say("== C: fchown, lchown, fchownat\n");
    for (int form = 0; form < 5; form++)
        for (int a = 0; a < NW; a++)
            for (int t = 0; t < NT; t++) {
                reset_fo();
                as(a, family_row, form * 16 + t);
            }
    say("== C: a symbolic link's own owner\n");
    for (int a = 0; a < NW; a++)
        for (int t = 0; t < NT; t++) {
            if (t == 1) continue;
            reset_fo();
            as(a, link_row, t);
        }
    say("== C: what else a chown answers\n");
    for (int a = 0; a < NW; a++) {
        if (a == GRP) continue;
        reset_fo();
        as(a, ctime_row, 0);
    }
    for (int a = 0; a < NW; a++) {
        if (a == MEM || a == GRP) continue;
        reset_fo();
        as(a, error_row, 0);
    }
    for (int a = 0; a < NW; a++) {
        if (a == GRP) continue;
        mkdir(in("do"), 0755); chown(in("do"), 1000, 2000); chmod(in("do"), 06755);
        int sk = bind_at(in("so"));
        chown(in("so"), 1000, 2000);
        as(a, other_row, 0);
        if (sk >= 0) close(sk);
        unlink(in("so")); rmdir(in("do"));
    }
    for (int a = 0; a < NW; a++) {
        noop_reset();
        as(a, noop_row, 0);
    }
    unlink(in("n0")); unlink(in("n2")); unlink(in("n4")); rmdir(in("nd"));
    reset_fo();
    as(ROOT, width_row, 0);
    put_file(in("f2"), "2\n", 0644, 1002, 2999);
    fsid_rows();
    unlink(in("f2"));

    say("== R: what stat, statx and /proc report\n");
    reset_fo();
    chown(in("fo"), 1001, 2001);
    lchown(in("lo"), 1002, 2002);
    as(ROOT, report_row, 0);
    as(OTH, report_row, 0);
    proc_rows();
    as(OWN, desc_row, 0);
    as(ROOT, desc_row, 0);
    {
        struct stat a;
        long r1 = rc(SYS_chown, (long)"/dev/null", 0, 0, 0, 0);
        long r2 = rc(SYS_chown, (long)"/proc/self/status", 0, 0, 0, 0);
        int fd = open(D, O_RDWR | O_TMPFILE, 0600);
        long r3 = fd < 0 ? -(long)errno : 0;
        if (fd >= 0) { fstat(fd, &a); close(fd); }
        say("~fixed: chown(0, 0) of /dev/null %ld, of /proc/self/status %ld; open(O_TMPFILE) %ld\n", r1, r2, r3);
    }
    unlink(in("lo")); unlink(in("fo"));
    say("own: gone: rmdir %ld\n", rmdir(D) == 0 ? 0L : -(long)errno);
    say("own: done\n");
    return 0;
}
