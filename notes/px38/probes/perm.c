/* perm.c — px38, item 2(b): Linux's permission checks, measured on a
 * tmpfs. Root builds each case; one of five actors, a fresh child that
 * has become that user for good, tries each thing and prints the
 * kernel's answer (0 or -errno).
 *
 *   perm DIR        DIR is an empty directory on a tmpfs, mode 0777
 *   perm hello      (what the probe execs of itself: exit 7)
 *
 * The actors, against a thing owned 1000:2000:
 *   own   uid 1000, gid 2999, no other group      (the owner, not in the group)
 *   grp   uid 1001, gid 2000                      (in the group by its effective gid)
 *   sup   uid 1001, gid 2999, groups {2000}       (in the group by a supplementary gid)
 *   oth   uid 1002, gid 2999                      (neither)
 *   root  uid 0, gid 0
 */
#include "px38.h"
#include <dirent.h>
#include <sys/time.h>

static const char *D;
static char self_path[256];
static char PB[8][600];
static int pbi;
static const char *in(const char *n)
{
    char *p = PB[pbi++ & 7];
    snprintf(p, 600, "%s/%s", D, n);
    return p;
}

struct actor { const char *name; unsigned uid, gid; int ng; unsigned gs[2]; };
static const struct actor A[] = {
    { "own ", 1000, 2999, 0, { 0, 0 } },
    { "grp ", 1001, 2000, 0, { 0, 0 } },
    { "sup ", 1001, 2999, 1, { 2000, 0 } },
    { "oth ", 1002, 2999, 0, { 0, 0 } },
    { "root", 0, 0, 0, { 0, 0 } },
};
#define NA 5
enum { OWN, GRP, SUP, OTH, ROOT };

/* Run fn(arg) as actor a; fn prints. */
static void as(int a, void (*fn)(long), long arg)
{
    pid_t p = fork();
    if (p == 0) {
        if (A[a].uid != 0) become(A[a].uid, A[a].gid, A[a].ng, A[a].gs);
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        fn(arg);
        _exit(0);
    }
    int st = reap(p);
    if (st != 0) say("! actor %s failed (%d)\n", A[a].name, st);
}

static long op(const char *p, int flags)
{
    int fd = open(p, flags, 0666);
    if (fd < 0) return -(long)errno;
    close(fd);
    return 0;
}

static long try_exec(const char *p)
{
    pid_t q = fork();
    if (q == 0) {
        char *av[] = { (char *)p, (char *)"hello", NULL };
        char *ev[] = { NULL };
        execve(p, av, ev);
        _exit(100 + errno);
    }
    int st = reap(q);
    return st == 7 ? 0 : st >= 100 && st < 240 ? -(long)(st - 100) : 9000 + st;
}

/* --- A: a file's three classes ------------------------------------------- */
static const char *cur_actor;
static void file_row(long mode)
{
    /* one call at a time, in this order: the truncation last, since it empties the program */
    const char *f = in("fa");
    long r = op(f, O_RDONLY), w = op(f, O_WRONLY), rw = op(f, O_RDWR), x = try_exec(f);
    long ar = rc(SYS_access, (long)f, 4, 0, 0, 0), aw = rc(SYS_access, (long)f, 2, 0, 0, 0), ax = rc(SYS_access, (long)f, 1, 0, 0, 0);
    long tr = rc(SYS_truncate, (long)f, 0, 0, 0, 0);
    say("file %04lo %s: open r %ld, w %ld, rw %ld; execve %ld; access r %ld w %ld x %ld; truncate %ld\n", mode, cur_actor, r, w, rw, x, ar,
        aw, ax, tr);
}

/* --- B: a directory's three classes --------------------------------------- */
static void dir_row(long mode)
{
    const char *d = in("da");
    long list, st, cd, cr, ul, rn, mk, rmd;
    int fd = open(d, O_RDONLY | O_DIRECTORY);
    if (fd < 0) list = -(long)errno;
    else {
        char b[1024];
        list = rc(SYS_getdents64, fd, (long)b, sizeof b, 0, 0);
        if (list > 0) list = 0;
        close(fd);
    }
    struct stat s;
    st = stat(in("da/in"), &s) == 0 ? 0L : -(long)errno;
    cd = chdir(d) == 0 ? 0L : -(long)errno;
    if (chdir("/") != 0) _exit(97);
    fd = open(in("da/new"), O_WRONLY | O_CREAT | O_EXCL, 0666);
    cr = fd >= 0 ? 0L : -(long)errno;
    if (fd >= 0) close(fd);
    ul = unlink(in("da/victim")) == 0 ? 0L : -(long)errno;
    rn = rename(in("da/in"), in("da/in2")) == 0 ? 0L : -(long)errno;
    mk = mkdir(in("da/sub"), 0777) == 0 ? 0L : -(long)errno;
    rmd = rmdir(in("da/gone")) == 0 ? 0L : -(long)errno;
    say("dir %04lo %s: list %ld, stat of a name %ld, chdir %ld, create %ld, unlink %ld, rename %ld, mkdir %ld, rmdir %ld\n", mode,
        cur_actor, list, st, cd, cr, ul, rn, mk, rmd);
}

static void dir_reset(unsigned mode)
{
    /* root: the directory as every actor finds it */
    const char *d = in("da");
    chmod(d, 0777);
    unlink(in("da/new")); rmdir(in("da/sub"));
    rename(in("da/in2"), in("da/in"));
    put_file(in("da/in"), "in\n", 0666, 1000, 2000);
    put_file(in("da/victim"), "v\n", 0000, 0, 0);
    mkdir(in("da/gone"), 0777);
    chmod(d, mode);
}

/* --- C: the sticky bit ---------------------------------------------------- */
static void sticky_row(long dirkind)
{
    const char *dn = dirkind ? "st" : "ns";
    char a[64], b[64], c[64], sub[64], mine[64], over[64];
    snprintf(a, sizeof a, "%s/f1000", dn); snprintf(b, sizeof b, "%s/f1001", dn); snprintf(c, sizeof c, "%s/f1002", dn);
    snprintf(sub, sizeof sub, "%s/d1002", dn); snprintf(mine, sizeof mine, "%s/mine", dn); snprintf(over, sizeof over, "%s/moved", dn);
    int fd = open(in(mine), O_WRONLY | O_CREAT, 0666);
    long mk = fd >= 0 ? 0L : -(long)errno;
    if (fd >= 0) close(fd);
    long u0 = unlink(in(a)) == 0 ? 0L : -(long)errno;
    long u1 = unlink(in(b)) == 0 ? 0L : -(long)errno;
    long r2 = rename(in(c), in(over)) == 0 ? 0L : -(long)errno;
    if (r2 == 0) rename(in(over), in(c));
    long o2 = rename(in(mine), in(c)) == 0 ? 0L : -(long)errno;
    long rd = rmdir(in(sub)) == 0 ? 0L : -(long)errno;
    say("%s %s: a file of its own made %ld; unlink 1000's file %ld, 1001's %ld; rename 1002's away %ld; rename its own over 1002's %ld; rmdir 1002's directory %ld\n",
        dirkind ? "sticky 1777 dir of 1000" : "plain  0777 dir of 1000", cur_actor, mk, u0, u1, r2, o2, rd);
}

static void sticky_reset(const char *dn, unsigned mode)
{
    char p[64];
    mkdir(in(dn), 0777);
    chown(in(dn), 1000, 2000);
    chmod(in(dn), 0777);
    snprintf(p, sizeof p, "%s/mine", dn); unlink(in(p));
    snprintf(p, sizeof p, "%s/moved", dn); unlink(in(p));
    snprintf(p, sizeof p, "%s/f1000", dn); put_file(in(p), "a\n", 0644, 1000, 2000);
    snprintf(p, sizeof p, "%s/f1001", dn); put_file(in(p), "b\n", 0644, 1001, 2000);
    snprintf(p, sizeof p, "%s/f1002", dn); put_file(in(p), "c\n", 0644, 1002, 2999);
    snprintf(p, sizeof p, "%s/d1002", dn); mkdir(in(p), 0755); chown(in(p), 1002, 2999);
    chmod(in(dn), mode);
}

/* The four "protected" settings (proc_sys_fs(5)): each changes an answer
 * in a sticky world-writable directory, so each run says what it had. */
static void protected_row(long unused)
{
    (void)unused;
    /* st/rootfile is root's, 0666; st/l1002 is 1002's symbolic link to it; st/h is a new hard link */
    long cr = op(in("st/rootfile"), O_WRONLY | O_CREAT);
    long wr = op(in("st/rootfile"), O_WRONLY);
    long sl = op(in("st/l1002"), O_RDONLY);
    /* the new names go in the plain directory: in the sticky one the actor could not remove them again */
    long hl = link(in("st/secret"), in("ns/h")) == 0 ? 0L : -(long)errno;
    if (hl == 0) unlink(in("ns/h"));
    long hw = link(in("st/rootfile"), in("ns/h2")) == 0 ? 0L : -(long)errno;
    if (hw == 0) unlink(in("ns/h2"));
    say("protected %s: root's 0666 file in a sticky directory opened O_CREAT %ld, without O_CREAT %ld; opened through 1002's link %ld; a hard link to root's 0600 file %ld, to root's 0666 file %ld\n",
        cur_actor, cr, wr, sl, hl, hw);
}

/* --- D: chmod ------------------------------------------------------------- */
static void chmod_row(long unused)
{
    (void)unused;
    const char *f = in("fm");
    long a = rc(SYS_chmod, (long)f, 0640, 0, 0, 0);
    /* the file is 0644 to begin with, so anyone may open it to read: the answer is fchmod's, not open's */
    int fd = open(f, O_RDONLY);
    long b = fd >= 0 ? rc(SYS_fchmod, fd, 0644, 0, 0, 0) : 7000 + errno;
    if (fd >= 0) close(fd);
    long c = rc(SYS_chmod, (long)f, 04755, 0, 0, 0);
    unsigned mc = mode_of(f);
    long d = rc(SYS_chmod, (long)f, 02755, 0, 0, 0);
    unsigned md = mode_of(f);
    long e = rc(SYS_chmod, (long)in("dm"), 02755, 0, 0, 0);
    unsigned me = mode_of(in("dm"));
    long g = rc(SYS_chmod, (long)f, 01644, 0, 0, 0);
    unsigned mg = mode_of(f);
    say("chmod %s (file 1000:2000): chmod 0640 %ld; fchmod on a read-only descriptor %ld; 04755 %ld mode %04o; 02755 %ld mode %04o; a directory 02755 %ld mode %04o; a file 01644 %ld mode %04o\n",
        cur_actor, a, b, c, mc, d, md, e, me, g, mg);
}

/* --- E: chown ------------------------------------------------------------- */
static long chown_then(const char *f, long u, long g, char *out, int n)
{
    long r = rc(SYS_chown, (long)f, u, g, 0, 0);
    snprintf(out, n, "%ld (%s %04o)", r, own_of(f), mode_of(f));
    return r;
}

static void chown_reset(void)
{
    put_file(in("fo"), "o\n", 06755, 1000, 2000);
    chown(in("fo"), 1000, 2000);
    chmod(in("fo"), 06755);
}

static void chown_row(long which)
{
    const char *f = in("fo");
    static const long T[][2] = { { -1, -1 }, { 1000, -1 }, { 1000, 2000 }, { -1, 2000 }, { -1, 2999 }, { -1, 2001 }, { 1001, -1 },
                                 { 1002, 2999 }, { 0, 0 }, { 70000, 70000 } };
    char o[96];
    chown_then(f, T[which][0], T[which][1], o, sizeof o);
    say("chown %s (file 1000:2000 mode 6755): chown(%ld, %ld) = %s\n", cur_actor, T[which][0], T[which][1], o);
}

static void chown_bits_row(long which)
{
    /* which set-ID bits a chown that succeeds takes away */
    static const unsigned M[] = { 04755, 02755, 06755, 02745, 06711, 04644, 01777 };
    const char *f = in(which == 100 ? "do" : "fo");
    char o[96];
    if (which == 100) {
        chown_then(f, -1, 2000, o, sizeof o);
        say("chown %s: a directory 1000:2000 mode 6755, chown(-1, 2000) = %s\n", cur_actor, o);
        return;
    }
    chown_then(f, -1, 2000, o, sizeof o);
    say("chown %s: a file 1000:2000 mode %04o, chown(-1, 2000) = %s\n", cur_actor, M[which], o);
}

/* --- F: utimensat --------------------------------------------------------- */
static void utimens_row(long wr)
{
    const char *f = in(wr ? "tw" : "tr");
    struct timespec now2[2] = { { 0, UTIME_NOW }, { 0, UTIME_NOW } }, exp[2] = { { 1, 0 }, { 2, 0 } },
                    nowomit[2] = { { 0, UTIME_NOW }, { 0, UTIME_OMIT } }, omit2[2] = { { 0, UTIME_OMIT }, { 0, UTIME_OMIT } },
                    expomit[2] = { { 5, 0 }, { 0, UTIME_OMIT } };
    long a = rc(SYS_utimensat, AT_FDCWD, (long)f, 0, 0, 0);
    long b = rc(SYS_utimensat, AT_FDCWD, (long)f, (long)now2, 0, 0);
    long c = rc(SYS_utimensat, AT_FDCWD, (long)f, (long)exp, 0, 0);
    long d = rc(SYS_utimensat, AT_FDCWD, (long)f, (long)nowomit, 0, 0);
    long e = rc(SYS_utimensat, AT_FDCWD, (long)f, (long)omit2, 0, 0);
    long g = rc(SYS_utimensat, AT_FDCWD, (long)f, (long)expomit, 0, 0);
    say("utimensat %s (file 1000:2000 mode %s): times NULL %ld; {NOW, NOW} %ld; {1, 2} %ld; {NOW, OMIT} %ld; {OMIT, OMIT} %ld; {5, OMIT} %ld\n",
        cur_actor, wr ? "0666" : "0644", a, b, c, d, e, g);
}

/* --- H: who owns what is made --------------------------------------------- */
static void create_row(long unused)
{
    (void)unused;
    umask(022);
    int fd;
    char o1[64], o2[64], o3[64], o4[64], o5[64];
    fd = open(in("c0/f"), O_WRONLY | O_CREAT | O_EXCL, 0666); if (fd >= 0) close(fd);
    snprintf(o1, sizeof o1, "%s %04o", own_of(in("c0/f")), mode_of(in("c0/f")));
    fd = open(in("cg/f"), O_WRONLY | O_CREAT | O_EXCL, 0666); if (fd >= 0) close(fd);
    snprintf(o2, sizeof o2, "%s %04o", own_of(in("cg/f")), mode_of(in("cg/f")));
    mkdir(in("cg/d"), 0777);
    snprintf(o3, sizeof o3, "%s %04o", own_of(in("cg/d")), mode_of(in("cg/d")));
    mkdir(in("c0/d"), 0777);
    snprintf(o4, sizeof o4, "%s %04o", own_of(in("c0/d")), mode_of(in("c0/d")));
    fd = open(in("cg/x"), O_WRONLY | O_CREAT | O_EXCL, 02775); if (fd >= 0) close(fd);
    snprintf(o5, sizeof o5, "%s %04o", own_of(in("cg/x")), mode_of(in("cg/x")));
    say("made by %s, umask 022: a file in a 0777 directory of 0:2000: %s; in a 2777 one: %s; a directory in the 2777 one: %s; in the 0777 one: %s; a file made with mode 02775 in the 2777 one: %s\n",
        cur_actor, o1, o2, o3, o4, o5);
    symlink("x", in("c0/l"));
    say("made by %s: a symbolic link %s %04o\n", cur_actor, own_of(in("c0/l")), mode_of(in("c0/l")));
    umask(0);
    fd = open(in("c0/u0"), O_WRONLY | O_CREAT | O_EXCL, 0666); if (fd >= 0) close(fd);
    umask(027);
    fd = open(in("c0/u27"), O_WRONLY | O_CREAT | O_EXCL, 0666); if (fd >= 0) close(fd);
    mkdir(in("c0/ud27"), 0777);
    umask(0777);
    fd = open(in("c0/u777"), O_WRONLY | O_CREAT | O_EXCL, 0666);
    long w = fd >= 0 ? write(fd, "x", 1) : -1;
    if (fd >= 0) close(fd);
    say("made by %s: with umask 000 mode %04o; umask 027 a file %04o, a directory %04o; umask 0777 a file %04o, and its first descriptor wrote %ld\n",
        cur_actor, mode_of(in("c0/u0")), mode_of(in("c0/u27")), mode_of(in("c0/ud27")), mode_of(in("c0/u777")), w);
    unlink(in("c0/f")); unlink(in("cg/f")); rmdir(in("cg/d")); rmdir(in("c0/d")); unlink(in("cg/x")); unlink(in("c0/l"));
    unlink(in("c0/u0")); unlink(in("c0/u27")); rmdir(in("c0/ud27")); unlink(in("c0/u777"));
}

int main(int argc, char **argv)
{
    if (argc > 1 && strcmp(argv[1], "hello") == 0) return 7;
    if (argc < 2) { say("usage: perm DIR\n"); return 2; }
    D = argv[1];
    long n = readlink("/proc/self/exe", self_path, sizeof self_path - 1);
    if (n <= 0) return 2;
    umask(0);
    chmod(D, 0777);
    {
        const char *names[] = { "protected_hardlinks", "protected_symlinks", "protected_regular", "protected_fifos" };
        say("settings:");
        for (int i = 0; i < 4; i++) {
            char p[96], b[16] = "?";
            snprintf(p, sizeof p, "/proc/sys/fs/%s", names[i]);
            int fd = open(p, O_RDONLY);
            if (fd >= 0) { long k = read(fd, b, sizeof b - 1); if (k > 0) b[k - 1] = 0; close(fd); }
            say(" %s %s", names[i], b);
        }
        say("\n");
    }

    say("== A: a file 1000:2000, by mode and by who asks\n");
    {
        static const unsigned M[] = { 0000, 0400, 0200, 0100, 0040, 0020, 0010, 0004, 0002, 0001, 0700, 0070, 0007,
                                      0077, 0707, 0770, 0777, 0644, 0755, 0750, 0754 };
        if (copy_file(self_path, in("fa"), 0755) != 0) { say("! copy\n"); return 1; }
        chown(in("fa"), 1000, 2000);
        for (unsigned i = 0; i < sizeof M / sizeof *M; i++)
            for (int a = 0; a < NA; a++) {
                chmod(in("fa"), M[i]);
                cur_actor = A[a].name;
                as(a, file_row, M[i]);
                /* a truncation that was let through emptied it: put the program back */
                struct stat s;
                if (stat(in("fa"), &s) == 0 && s.st_size == 0) {
                    chmod(in("fa"), 0700);
                    copy_file(self_path, in("fa"), M[i]);
                    chown(in("fa"), 1000, 2000);
                }
            }
        unlink(in("fa"));
    }

    say("== B: a directory 1000:2000, by mode and by who asks (it holds root's mode-0000 file `victim`, an empty directory `gone`, and 1000's file `in`)\n");
    {
        static const unsigned M[] = { 0000, 0400, 0200, 0100, 0300, 0500, 0600, 0700, 0070, 0050, 0030, 0010, 0007, 0005, 0003, 0001,
                                      0755, 0711, 0733, 0077, 0707 };
        mkdir(in("da"), 0777);
        chown(in("da"), 1000, 2000);
        for (unsigned i = 0; i < sizeof M / sizeof *M; i++)
            for (int a = 0; a < NA; a++) {
                dir_reset(M[i]);
                cur_actor = A[a].name;
                as(a, dir_row, M[i]);
            }
        dir_reset(0777);
        unlink(in("da/in")); unlink(in("da/victim")); rmdir(in("da/gone")); rmdir(in("da"));
    }

    say("== C: the sticky bit\n");
    for (int kind = 1; kind >= 0; kind--)
        for (int a = 0; a < NA; a++) {
            if (a == SUP) continue;
            sticky_reset(kind ? "st" : "ns", kind ? 01777 : 0777);
            cur_actor = A[a].name;
            as(a, sticky_row, kind);
        }
    sticky_reset("st", 01777);
    put_file(in("st/rootfile"), "r\n", 0666, 0, 0);
    put_file(in("st/secret"), "s\n", 0600, 0, 0);
    symlink("rootfile", in("st/l1002"));
    lchown(in("st/l1002"), 1002, 2999);
    for (int a = 0; a < NA; a++) {
        if (a == SUP) continue;
        cur_actor = A[a].name;
        as(a, protected_row, 0);
    }

    say("== D: chmod\n");
    for (int a = 0; a < NA; a++) {
        put_file(in("fm"), "m\n", 0644, 1000, 2000);
        mkdir(in("dm"), 0755); chown(in("dm"), 1000, 2000); chmod(in("dm"), 0755);
        cur_actor = A[a].name;
        as(a, chmod_row, 0);
    }
    {
        /* the owner IN the file's group: uid 1000, gid 2000 */
        put_file(in("fm"), "m\n", 0600, 1000, 2000);
        pid_t p = fork();
        if (p == 0) {
            become(1000, 2000, 0, A[0].gs);
            long r = rc(SYS_chmod, (long)in("fm"), 02755, 0, 0, 0);
            say("chmod by the owner in the file's group: 02755 %ld mode %04o\n", r, mode_of(in("fm")));
            _exit(0);
        }
        reap(p);
    }

    say("== E: chown\n");
    for (int a = 0; a < NA; a++)
        for (long t = 0; t < 10; t++) {
            chown_reset();
            cur_actor = A[a].name;
            as(a, chown_row, t);
        }
    {
        /* the owner with the group as a supplementary one: uid 1000, gid 2999, groups {2000, 2001} */
        static const long T[][2] = { { -1, 2000 }, { -1, 2001 }, { -1, 2002 }, { 1000, 2001 }, { -1, 2999 } };
        for (unsigned t = 0; t < 5; t++) {
            chown_reset();
            pid_t p = fork();
            if (p == 0) {
                unsigned gs[2] = { 2000, 2001 };
                become(1000, 2999, 2, gs);
                char o[96];
                chown_then(in("fo"), T[t][0], T[t][1], o, sizeof o);
                say("chown by the owner with groups {2000, 2001} (file 1000:2000 mode 6755): chown(%ld, %ld) = %s\n", T[t][0], T[t][1], o);
                _exit(0);
            }
            reap(p);
        }
        static const unsigned M[] = { 04755, 02755, 06755, 02745, 06711, 04644, 01777 };
        for (int who = 0; who < 2; who++)
            for (long i = 0; i < 7; i++) {
                put_file(in("fo"), "o\n", M[i], 1000, 2000);
                pid_t p = fork();
                if (p == 0) {
                    unsigned gs[2] = { 2000, 2001 };
                    if (who == 0) become(1000, 2999, 2, gs);
                    cur_actor = who == 0 ? "by its owner" : "by root";
                    chown_bits_row(i);
                    _exit(0);
                }
                reap(p);
            }
        for (int who = 0; who < 2; who++) {
            mkdir(in("do"), 0755); chown(in("do"), 1000, 2000); chmod(in("do"), 06755);
            pid_t p = fork();
            if (p == 0) {
                unsigned gs[2] = { 2000, 2001 };
                if (who == 0) become(1000, 2999, 2, gs);
                cur_actor = who == 0 ? "by its owner" : "by root";
                chown_bits_row(100);
                _exit(0);
            }
            reap(p);
        }
        rmdir(in("do"));
    }

    say("== F: utimensat\n");
    for (int wr = 1; wr >= 0; wr--)
        for (int a = 0; a < NA; a++) {
            if (a == SUP) continue;
            put_file(in("tw"), "t\n", 0666, 1000, 2000);
            put_file(in("tr"), "t\n", 0644, 1000, 2000);
            cur_actor = A[a].name;
            as(a, utimens_row, wr);
        }

    say("== G: access asks for the real ids, open for the file-system ids\n");
    {
        put_file(in("g1001"), "g\n", 0600, 1001, 2999);
        put_file(in("g1002"), "g\n", 0600, 1002, 2999);
        put_file(in("groot"), "g\n", 0600, 0, 0);
        static const long S[][3] = { { 1000, 1001, 1001 }, { 1001, 1000, 1000 }, { 0, 1000, 0 }, { 1000, 0, 0 }, { 1000, 1000, 1000 } };
        for (unsigned i = 0; i < 5; i++) {
            pid_t p = fork();
            if (p == 0) {
                rc(SYS_setgroups, 0, 0, 0, 0, 0);
                rc(SYS_setresgid, 2999, 2999, 2999, 0, 0);
                rc(SYS_setresuid, S[i][0], S[i][1], S[i][2], 0, 0);
                const char *fs[] = { "g1001", "groot" };
                for (int k = 0; k < 2; k++) {
                    const char *f = in(fs[k]);
                    say("ids (%ld %ld %ld), %s 0600 file: access(R_OK) %ld, faccessat(R_OK) %ld, faccessat2(R_OK, AT_EACCESS) %ld, faccessat2(R_OK, 0) %ld, open %ld\n",
                        S[i][0], S[i][1], S[i][2], k ? "root's" : "1001's", rc(SYS_access, (long)f, 4, 0, 0, 0),
                        rc(SYS_faccessat, AT_FDCWD, (long)f, 4, 0, 0), rc(SYS_faccessat2, AT_FDCWD, (long)f, 4, AT_EACCESS, 0),
                        rc(SYS_faccessat2, AT_FDCWD, (long)f, 4, 0, 0), op(f, O_RDONLY));
                }
                _exit(0);
            }
            reap(p);
        }
        /* the file-system id apart from the effective id */
        pid_t p = fork();
        if (p == 0) {
            long a = rc(SYS_setfsuid, 1002, 0, 0, 0, 0);
            say("root after setfsuid(1002) = %ld (uid %s, cap %s): open of root's 0600 file %ld, of 1002's %ld, of 1001's %ld; a file it makes is owned %s",
                a, uids(), capeff(), op(in("groot"), O_RDONLY), op(in("g1002"), O_RDONLY), op(in("g1001"), O_RDONLY), "");
            int fd = open(in("gnew"), O_WRONLY | O_CREAT, 0644);
            if (fd >= 0) close(fd);
            say("%s; kill(1, 0) %ld\n", own_of(in("gnew")), rc(SYS_kill, 1, 0, 0, 0, 0));
            _exit(0);
        }
        reap(p);
        unlink(in("gnew"));
    }

    say("== H: who owns what is made, and the umask\n");
    mkdir(in("c0"), 0777); chown(in("c0"), 0, 2000); chmod(in("c0"), 0777);
    mkdir(in("cg"), 0777); chown(in("cg"), 0, 2000); chmod(in("cg"), 02777);
    for (int a = 0; a < NA; a++) {
        if (a == SUP) continue;
        cur_actor = A[a].name;
        as(a, create_row, 0);
    }
    {
        pid_t p = fork();
        if (p == 0) {
            /* (1001 1001 1002) with file-system ids moved to the saved ones */
            rc(SYS_setgroups, 0, 0, 0, 0, 0);
            rc(SYS_setresgid, 2001, 2001, 2002, 0, 0);
            rc(SYS_setresuid, 1001, 1001, 1002, 0, 0);
            long a = rc(SYS_setfsuid, 1002, 0, 0, 0, 0), b = rc(SYS_setfsgid, 2002, 0, 0, 0, 0);
            int fd = open(in("c0/fs"), O_WRONLY | O_CREAT, 0644);
            if (fd >= 0) close(fd);
            say("made by uid %s gid %s after setfsuid(1002) = %ld and setfsgid(2002) = %ld: %s\n", uids(), gids(), a, b, own_of(in("c0/fs")));
            _exit(0);
        }
        reap(p);
        unlink(in("c0/fs"));
    }
    say("perm: done\n");
    return 0;
}
