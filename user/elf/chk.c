/* chk.c — px43: the file checks. What a process may open, truncate,
 * ask `access` about, run and walk through, by the class rule (owner,
 * group, other, chosen by the file-system ids; the access family by
 * the real ids, or with AT_EACCESS by the file-system ones), and what
 * a descriptor already open keeps. Static; every call under test is a
 * raw `syscall(2)` (px38.h's `rc`) or a plain wrapper whose answer is
 * the kernel's.
 *
 *   chk          as root: the image's cases (/k, built with owners and
 *                modes into the archive, the same archive on PAX and as
 *                Linux's root), each row by px38's five actors (a child
 *                that has become that user for good) or by a state of
 *                ids root sets up first
 *   chk user     the rows a user can make alone, as whoever runs it
 *                (tests/mpx5-users: `as 1000 1000 /bin/chk user`)
 *   chk soak N   N rounds of opens, refusals, walks, access, truncation,
 *                a file made and removed; every 1,000th round two execs;
 *                px44: names made and moved where the directory refuses,
 *                a rename in a sticky directory, a hard link and an
 *                O_CREAT open the protected settings refuse, a chmod and
 *                a time set on root's file, a set-ID file written
 *
 * px44 adds the rules on names and metadata (sections N, K, P, M, T, B, U
 * and R, after px43's; notes/px44-the-names.md).
 *
 * Written from the man pages named in notes/px43-the-file-checks.md and
 * notes/px44-the-names.md; no kernel's or libc's source. */
#include "px38.h"
#include <dirent.h>
#include <sys/socket.h>
#include <sys/uio.h>
#include <sys/un.h>

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
static const char *cur = "self";
static int alone; /* `chk user`: every row as whoever runs it */
static char LONGNAME[257];

/* Run fn(arg) as actor a in a child (alone: in this process, as itself). */
static void as(int a, void (*fn)(long), long arg)
{
    if (alone) { cur = "self"; fn(arg); return; }
    cur = A[a].name;
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
static void each(void (*fn)(long), long arg)
{
    if (alone) { as(0, fn, arg); return; }
    for (int a = 0; a < NA; a++) as(a, fn, arg);
}

static long st(const char *p)
{
    struct stat s;
    return rc(SYS_newfstatat, AT_FDCWD, (long)p, (long)&s, 0, 0);
}
static long op(const char *p, int flags)
{
    long fd = rc(SYS_openat, AT_FDCWD, (long)p, flags, 0640, 0);
    if (fd < 0) return fd;
    close((int)fd);
    return 0;
}
static long cd(const char *p)
{
    long r = rc(SYS_chdir, (long)p, 0, 0, 0, 0);
    if (r == 0 && chdir("/") != 0) _exit(97);
    return r;
}
/* execve(p) in a child: 0 when the program ran (seven exits 7), else -errno. */
static long run7(const char *p)
{
    pid_t q = fork();
    if (q == 0) {
        char *av[] = { (char *)p, NULL };
        char *ev[] = { NULL };
        rc(SYS_execve, (long)p, (long)av, (long)ev, 0, 0);
        _exit(100 + errno);
    }
    int s = reap(q);
    return s == 7 ? 0 : s >= 100 && s < 240 ? -(long)(s - 100) : 9000 + s;
}
static long size_of(const char *p)
{
    struct stat s;
    if (stat(p, &s) != 0) return -errno;
    return (long)s.st_size;
}
static const char *path(const char *a, const char *b)
{
    static char o[8][700];
    static int i;
    char *r = o[i++ & 7];
    snprintf(r, 700, "%s/%s", a, b);
    return r;
}

/* --- the image, as the process finds it ------------------------------------ */
static void census(void)
{
    static const char *P[] = { "/k", "/k/w/o", "/k/w/g", "/k/w/t", "/k/w/n", "/k/w/r", "/k/w/o/f", "/k/w/o/s", "/k/w/o/seven",
                               "/k/w/deep/mid", "/k/o/ro", "/k/o/rw", "/k/o/g", "/k/o/e0", "/k/c/a", "/k/c/rx", "/k/c/wx", "/k/c/gw",
                               "/k/c/nx", "/k/a/u1001", "/k/a/root", "/k/a/g2000", "/k/a/d1001", "/k/a/x644", "/k/a/x100", "/k/a/dir0",
                               "/k/x/m0000", "/k/x/m0754", "/k/x/dir", "/k/h/own", "/k/h/ownd", "/k/h/mine", "/k/h/mined", NULL };
    say("image:");
    for (int i = 0; P[i]; i++) say(" %s %04o %s", P[i], mode_of(P[i]), own_of(P[i]));
    say("\n");
}

/* --- W: the search of every directory a path passes ------------------------ */
static const char *const WD[] = { "/k/w/o", "/k/w/g", "/k/w/t", "/k/w/n", "/k/w/r" };
static const char *const WM[] = { "0100", "0010", "0001", "0000", "0444" };
static void walk_row(long i)
{
    const char *D = WD[i];
    char slash[64];
    snprintf(slash, sizeof slash, "%s/", D);
    say("walk %s %s of 1000:2000 %s: stat it %ld, it/ %ld; f %ld, s/f %ld, a missing name %ld, . %ld, .. %ld, f/x %ld, a 256-byte name %ld; open f %ld; "
        "access(F_OK) f %ld; chdir %ld; execve seven %ld\n",
        D, WM[i], cur, st(D), st(slash), st(path(D, "f")), st(path(D, "s/f")), st(path(D, "nothere")), st(path(D, ".")), st(path(D, "..")),
        st(path(D, "f/x")), st(path(D, LONGNAME)), op(path(D, "f"), O_RDONLY), rc(SYS_access, (long)path(D, "f"), 0, 0, 0, 0),
        cd(D), run7(path(D, "seven")));
}
static void deep_row(long unused)
{
    (void)unused;
    say("walk /k/w/deep/mid 0700 of 1001:2000 %s: stat mid %ld, mid/end %ld, mid/end/f %ld; open mid/end/f %ld; chdir mid/end %ld; a missing directory "
        "on the way %ld\n",
        cur, st("/k/w/deep/mid"), st("/k/w/deep/mid/end"), st("/k/w/deep/mid/end/f"), op("/k/w/deep/mid/end/f", O_RDONLY),
        cd("/k/w/deep/mid/end"), st("/k/w/deep/none/f"));
}

/* A working directory the process may not search: root goes in, then the
 * child becomes the actor. */
static void cwd_row(long i)
{
    char b[512];
    long g = rc(SYS_getcwd, (long)b, sizeof b, 0, 0, 0);
    long f = st("f"), dot = st("."), dd = st(".."), sf = st("s/f"), o = op(".", O_RDONLY | O_DIRECTORY);
    long c1 = rc(SYS_chdir, (long)"s", 0, 0, 0, 0), c2 = rc(SYS_chdir, (long)"..", 0, 0, 0, 0);
    say("cwd %s %s: stat f %ld, . %ld, .. %ld, s/f %ld; open . %ld; getcwd %s (%ld); chdir s %ld, then .. %ld\n", WD[i], cur, f, dot, dd, sf, o,
        g > 0 ? b : "-", g > 0 ? 0 : g, c1, c2);
}
static void dirfd_row(long i)
{
    /* descriptor 9: the directory, opened by root before the drop */
    struct stat s;
    char b[1024];
    long g = rc(SYS_getdents64, 9, (long)b, sizeof b, 0, 0);
    long f = rc(SYS_newfstatat, 9, (long)"f", (long)&s, 0, 0), e = rc(SYS_newfstatat, 9, (long)"", (long)&s, AT_EMPTY_PATH, 0);
    long u = rc(SYS_newfstatat, 9, (long)"..", (long)&s, 0, 0), o = rc(SYS_openat, 9, (long)"f", O_RDONLY, 0, 0);
    long x = rc(SYS_faccessat, 9, (long)"f", 0, 0, 0), c = rc(SYS_fchdir, 9, 0, 0, 0, 0);
    say("dirfd %s %s: fstatat f %ld, \"\" AT_EMPTY_PATH %ld, .. %ld; openat f %ld; faccessat(F_OK) f %ld; getdents64 %ld; fchdir %ld\n", WD[i], cur, f, e,
        u, o >= 0 ? 0 : o, x, g > 0 ? 0 : g, c);
}
static void root_then(int a, const char *dir, int asfd, void (*fn)(long), long arg)
{
    cur = A[a].name;
    pid_t p = fork();
    if (p == 0) {
        if (asfd) {
            int fd = open(dir, O_RDONLY | O_DIRECTORY);
            if (fd < 0 || dup2(fd, 9) != 9) { say("! %s: %d\n", dir, -errno); _exit(93); }
        } else if (chdir(dir) != 0) { say("! chdir %s: %d\n", dir, -errno); _exit(93); }
        if (A[a].uid != 0) become(A[a].uid, A[a].gid, A[a].ng, A[a].gs);
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        fn(arg);
        _exit(0);
    }
    int s = reap(p);
    if (s != 0) say("! actor %s failed (%d)\n", A[a].name, s);
}

/* Symbolic links, made where the actor may search: what they lead through. */
static const char *LK;
static void link_row(long unused)
{
    (void)unused;
    struct stat s;
    char b[64];
    long rl = rc(SYS_readlink, (long)path(LK, "ln"), (long)b, sizeof b, 0, 0);
    say("links %s: stat ln (to /k/w/n/f) %ld, lstat ln %ld, readlink ln %ld; stat lo (to /k/w/o/f) %ld; lt (to ../../k/w/t/f) %ld; ldn (to /k/w/n) "
        "%ld, ldn/f %ld; chdir ldn %ld\n",
        cur, st(path(LK, "ln")), rc(SYS_newfstatat, AT_FDCWD, (long)path(LK, "ln"), (long)&s, AT_SYMLINK_NOFOLLOW, 0), rl,
        st(path(LK, "lo")), st(path(LK, "lt")), st(path(LK, "ldn")), st(path(LK, "ldn/f")), cd(path(LK, "ldn")));
}

/* --- O: open and truncate ---------------------------------------------------- */
static void open_row(long unused)
{
    (void)unused;
    long o1 = op("/k/o/ro", O_RDONLY | O_TRUNC), s1 = size_of("/k/o/ro");
    long o2 = op("/k/o/ro", O_WRONLY | O_TRUNC), s2 = size_of("/k/o/ro");
    long o3 = op("/k/o/e0", O_RDONLY | O_TRUNC);
    long o4 = op("/k/o/ro", O_RDONLY | O_CREAT), o5 = op("/k/o/ro", O_WRONLY | O_CREAT);
    long o6 = op("/k/o/g", O_RDWR), o7 = op("/k/o/g", O_RDONLY);
    long t1 = rc(SYS_truncate, (long)"/k/o/ro", 7, 0, 0, 0), t2 = rc(SYS_truncate, (long)"/k/o/rw", 7, 0, 0, 0);
    long t3 = rc(SYS_truncate, (long)"/k/o", 0, 0, 0, 0);
    long o8 = op("/k/o", O_WRONLY), o9 = op("/k/o", O_RDONLY);
    long f1, f2;
    int fd = open("/k/o/rw", O_RDONLY);
    f1 = fd < 0 ? 7000 + errno : rc(SYS_ftruncate, fd, 7, 0, 0, 0);
    if (fd >= 0) close(fd);
    fd = open("/k/o/rw", O_WRONLY);
    f2 = fd < 0 ? 7000 + errno : rc(SYS_ftruncate, fd, 7, 0, 0, 0);
    if (fd >= 0) close(fd);
    say("open %s: ro (0444) O_RDONLY|O_TRUNC %ld, size %ld; O_WRONLY|O_TRUNC %ld, size %ld; an empty 0444 file O_RDONLY|O_TRUNC %ld; ro O_RDONLY|O_CREAT "
        "%ld, O_WRONLY|O_CREAT %ld; the 0060 file O_RDWR %ld, O_RDONLY %ld; truncate ro %ld, rw (0666) %ld, the directory %ld; the directory (0755 root's) "
        "O_WRONLY %ld, O_RDONLY %ld; ftruncate rw on a read-only descriptor %ld, a write-only one %ld; sizes after: ro %ld, rw %ld\n",
        cur, o1, s1, o2, s2, o3, o4, o5, o6, o7, t1, t2, t3, o8, o9, f1, f2, size_of("/k/o/ro"), size_of("/k/o/rw"));
}

/* --- C: a name made in a directory ------------------------------------------- */
static long make_in(const char *d)
{
    char n[96];
    snprintf(n, sizeof n, "%s/n%u", d, (unsigned)getuid());
    long fd = rc(SYS_openat, AT_FDCWD, (long)n, O_WRONLY | O_CREAT | O_EXCL, 0640, 0);
    if (fd < 0) return fd;
    close((int)fd);
    if (unlink(n) != 0) return 8000 + errno;
    return 0;
}
static void create_row(long unused)
{
    (void)unused;
    say("create %s: in a 0777 directory of root %ld, 0555 of root %ld, 0300 of 1000:2000 %ld, 0030 of 1000:2000 %ld, 0666 of root %ld; in the 0555 one, "
        "O_CREAT|O_EXCL of a name that exists %ld, O_CREAT alone %ld\n",
        cur, make_in("/k/c/a"), make_in("/k/c/rx"), make_in("/k/c/wx"), make_in("/k/c/gw"), make_in("/k/c/nx"),
        op("/k/c/rx/e", O_RDONLY | O_CREAT | O_EXCL), op("/k/c/rx/e", O_RDONLY | O_CREAT));
}

/* --- A: the access family: whose ids ----------------------------------------- */
static void access_lines(const char *who)
{
    static const char *F[] = { "/k/a/u1001", "/k/a/root", "/k/a/g2000" };
    static const char *FN[] = { "1001's 0600", "root's 0600", "1002:2000's 0040" };
    for (int k = 0; k < 3; k++)
        say("access %s, %s file: access(R_OK) %ld, faccessat(R_OK) %ld, faccessat2(R_OK, 0) %ld, faccessat2(R_OK, AT_EACCESS) %ld, open %ld\n", who, FN[k],
            rc(SYS_access, (long)F[k], 4, 0, 0, 0), rc(SYS_faccessat, AT_FDCWD, (long)F[k], 4, 0, 0),
            rc(SYS_faccessat2, AT_FDCWD, (long)F[k], 4, 0, 0), rc(SYS_faccessat2, AT_FDCWD, (long)F[k], 4, AT_EACCESS, 0), op(F[k], O_RDONLY));
    say("access %s, through 1001's 0700 directory: access(F_OK) %ld, faccessat2(F_OK, AT_EACCESS) %ld, open %ld; X_OK of root's 0644 file %ld, 0100 file "
        "%ld, 0000 directory %ld, AT_EACCESS %ld %ld %ld; R_OK|W_OK of the 0000 directory %ld\n",
        who, rc(SYS_access, (long)"/k/a/d1001/f", 0, 0, 0, 0), rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/d1001/f", 0, AT_EACCESS, 0),
        op("/k/a/d1001/f", O_RDONLY), rc(SYS_access, (long)"/k/a/x644", 1, 0, 0, 0), rc(SYS_access, (long)"/k/a/x100", 1, 0, 0, 0),
        rc(SYS_access, (long)"/k/a/dir0", 1, 0, 0, 0), rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/x644", 1, AT_EACCESS, 0),
        rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/x100", 1, AT_EACCESS, 0), rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/dir0", 1, AT_EACCESS, 0),
        rc(SYS_access, (long)"/k/a/dir0", 6, 0, 0, 0));
}
struct state { long r, e, s, fsu, gr, ge, gs, fsg; int ng; unsigned gl[2]; };
static void access_state(const struct state *S)
{
    pid_t p = fork();
    if (p == 0) {
        if (rc(SYS_setgroups, S->ng, (long)S->gl, 0, 0, 0) != 0) _exit(91);
        if (rc(SYS_setresgid, S->gr, S->ge, S->gs, 0, 0) != 0) _exit(91);
        if (S->fsg >= 0) rc(SYS_setfsgid, S->fsg, 0, 0, 0, 0);
        if (rc(SYS_setresuid, S->r, S->e, S->s, 0, 0) != 0) _exit(91);
        if (S->fsu >= 0) rc(SYS_setfsuid, S->fsu, 0, 0, 0, 0);
        char who[160];
        snprintf(who, sizeof who, "uid %s gid %s groups '%s'", uids(), gids(), groups());
        access_lines(who);
        _exit(0);
    }
    int s = reap(p);
    if (s != 0) say("! access state failed (%d)\n", s);
}

/* --- X: execve of an archive file, by mode and by who asks ------------------- */
static const unsigned XM[] = { 0000, 0400, 0200, 0100, 0040, 0020, 0010, 0004, 0002, 0001, 0700, 0070, 0007,
                               0077, 0707, 0770, 0777, 0644, 0755, 0750, 0754 };
#define NXM (sizeof XM / sizeof *XM)
static void exec_row(long i)
{
    char p[32];
    snprintf(p, sizeof p, "/k/x/m%04o", XM[i]);
    say("exec %04o %s: execve %ld; access(X_OK) %ld, AT_EACCESS %ld\n", XM[i], cur, run7(p), rc(SYS_access, (long)p, 1, 0, 0, 0),
        rc(SYS_faccessat2, AT_FDCWD, (long)p, 1, AT_EACCESS, 0));
}
static void exec_more(long unused)
{
    (void)unused;
    say("exec %s: a directory %ld; /k/w/n/seven (0755, in a 0000 directory) %ld; /k/w/o/seven (in a 0100 one of 1000) %ld\n", cur, run7("/k/x/dir"),
        run7("/k/w/n/seven"), run7("/k/w/o/seven"));
}

/* --- H: a descriptor that outlives a change of mode -------------------------- */
static void held_after(const char *f, const char *d, int rw, int ro, int dd)
{
    char b[1024];
    struct stat s;
    long r = lseek(ro, 0, SEEK_SET) == 0 && read(ro, b, 1) == 1 ? 0L : -(long)errno;
    long w = write(rw, "h", 1) == 1 ? 0L : -(long)errno;
    long t = rc(SYS_ftruncate, rw, 2, 0, 0, 0);
    long wo = rc(SYS_write, ro, (long)"h", 1, 0, 0);
    long fs = rc(SYS_fstat, rw, (long)&s, 0, 0, 0);
    unsigned fm = fs == 0 ? (unsigned)(s.st_mode & 07777) : 0u;
    long g = rc(SYS_getdents64, dd, (long)b, sizeof b, 0, 0);
    long cw = rc(SYS_getcwd, (long)b, sizeof b, 0, 0, 0);
    say("held %s: a file and a directory opened at 0666 and 0755, then made 0000: read on the old read descriptor %ld, write on the old O_RDWR one %ld, "
        "ftruncate %ld, write on the read one %ld, fstat %ld mode %04o; a new open O_RDONLY %ld, O_WRONLY %ld; the directory: getdents64 %ld, fstatat "
        "f %ld, fchdir %ld; in it as the working directory: stat f %ld, getcwd %ld\n",
        cur, r, w, t, wo, fs, fm, op(f, O_RDONLY), op(f, O_WRONLY), g > 0 ? 0 : g,
        rc(SYS_newfstatat, dd, (long)"f", (long)&s, 0, 0), rc(SYS_fchdir, dd, 0, 0, 0, 0), st("f"), cw > 0 ? 0 : cw);
    (void)d;
}
static void held_by(int a)
{
    char f[64], d[72];
    snprintf(f, sizeof f, "/k/h/%.4s", A[a].name);
    for (char *q = f; *q; q++) if (*q == ' ') *q = 0;
    snprintf(d, sizeof d, "%sd", f);
    int p1[2], p2[2];
    if (pipe(p1) || pipe(p2)) { say("! pipe\n"); return; }
    cur = A[a].name;
    pid_t p = fork();
    if (p == 0) {
        close(p1[0]); close(p2[1]);
        if (A[a].uid != 0) become(A[a].uid, A[a].gid, A[a].ng, A[a].gs);
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        int rw = open(f, O_RDWR), ro = open(f, O_RDONLY), dd = open(d, O_RDONLY | O_DIRECTORY);
        if (rw < 0 || ro < 0 || dd < 0 || chdir(d) != 0) { say("! held %s: %d\n", cur, -errno); _exit(93); }
        char c = 'r';
        if (write(p1[1], &c, 1) != 1 || read(p2[0], &c, 1) != 1) _exit(94);
        held_after(f, d, rw, ro, dd);
        _exit(0);
    }
    close(p1[1]); close(p2[0]);
    char c;
    if (read(p1[0], &c, 1) == 1) {
        long a1 = rc(SYS_chmod, (long)f, 0, 0, 0, 0), a2 = rc(SYS_chmod, (long)d, 0, 0, 0, 0);
        if (a1 || a2) say("! chmod by root %ld %ld\n", a1, a2);
    } else say("! the holder did not open\n");
    c = 'g';
    if (write(p2[1], &c, 1) != 1) say("! pipe\n");
    close(p1[0]); close(p2[1]);
    int s = reap(p);
    if (s != 0) say("! actor %s failed (%d)\n", A[a].name, s);
}
static void held_alone(void)
{
    /* the user's own file and directory: it opens them, then makes them 0000 itself */
    const char *f = "/k/h/mine", *d = "/k/h/mined";
    int rw = open(f, O_RDWR), ro = open(f, O_RDONLY), dd = open(d, O_RDONLY | O_DIRECTORY);
    if (rw < 0 || ro < 0 || dd < 0 || chdir(d) != 0) { say("! held: %d\n", -errno); return; }
    long a1 = rc(SYS_chmod, (long)f, 0, 0, 0, 0), a2 = rc(SYS_chmod, (long)d, 0, 0, 0, 0);
    say("held self: its own file and directory made 0000 by itself: chmod %ld, %ld\n", a1, a2);
    held_after(f, d, rw, ro, dd);
    if (chdir("/") != 0) _exit(97);
    close(rw); close(ro); close(dd);
}

/* --- S: a socket's name -------------------------------------------------------- */
static void sock_row(long unused)
{
    (void)unused;
    say("socket's name 0000 of root %s: open O_RDONLY %ld, O_WRONLY %ld; stat %ld\n", cur, op("/t/chk/sock", O_RDONLY), op("/t/chk/sock", O_WRONLY),
        st("/t/chk/sock"));
}

/* ===== px44 (U4): names and metadata ============================================
 * Each actor works on cases of its own (/k/n/<tag>, /k/s/<tag>, /k/m/<tag>,
 * /k/t/<tag>, /k/b/<tag>; <tag> own, grp, sup, oth, root, or self for
 * `chk user`), built into the archive with owners and modes; what the
 * archive cannot carry — a symbolic link, a socket's name — is made at run
 * time by the user who is to own it. Written from proc_sys_fs(5),
 * rename(2), unlink(2), rmdir(2), link(2), symlink(7), chmod(2),
 * utimensat(2), write(2), fallocate(2), unix(7) and POSIX; no kernel's
 * source. */
static char TAGB[8];
static const char *tag(void)
{
    if (alone) return "self";
    snprintf(TAGB, sizeof TAGB, "%s", cur);
    TAGB[strcspn(TAGB, " ")] = 0;
    return TAGB;
}
static const char *at(const char *area, const char *rest)
{
    static char o[8][160];
    static int i;
    char *r = o[i++ & 7];
    snprintf(r, 160, "/k/%s/%s/%s", area, tag(), rest);
    return r;
}
/* A raw call with six arguments (copy_file_range, splice). */
static long rc6(long nr, long a, long b, long c, long d, long e, long f)
{
    long r = syscall(nr, a, b, c, d, e, f);
    return r == -1 ? -(long)errno : r;
}
static long ul(const char *p) { return rc(SYS_unlink, (long)p, 0, 0, 0, 0); }
static long rd(const char *p) { return rc(SYS_rmdir, (long)p, 0, 0, 0, 0); }
static long md(const char *p) { return rc(SYS_mkdir, (long)p, 0755, 0, 0, 0); }
static long sl(const char *t, const char *p) { return rc(SYS_symlink, (long)t, (long)p, 0, 0, 0); }
static long ln(const char *o, const char *n) { return rc(SYS_link, (long)o, (long)n, 0, 0, 0); }
static long rn(const char *o, const char *n) { return rc(SYS_rename, (long)o, (long)n, 0, 0, 0); }
static long cm(const char *p, long m) { return rc(SYS_chmod, (long)p, m, 0, 0, 0); }
static long sock_at(const char *p, int *keep)
{
    struct sockaddr_un a;
    memset(&a, 0, sizeof a);
    a.sun_family = AF_UNIX;
    snprintf(a.sun_path, sizeof a.sun_path, "%s", p);
    int s = socket(AF_UNIX, SOCK_STREAM, 0);
    if (s < 0) return -errno;
    long r = rc(SYS_bind, s, (long)&a, sizeof a, 0, 0);
    if (keep && r == 0) *keep = s;
    else close(s);
    return r;
}
static long conn(const char *p)
{
    struct sockaddr_un a;
    memset(&a, 0, sizeof a);
    a.sun_family = AF_UNIX;
    snprintf(a.sun_path, sizeof a.sun_path, "%s", p);
    int s = socket(AF_UNIX, SOCK_STREAM, 0);
    if (s < 0) return -errno;
    long r = rc(SYS_connect, s, (long)&a, sizeof a, 0, 0);
    close(s);
    return r;
}
/* Fork, become (uid, gid) unless 0, run fn; for links and sockets that
 * must be that user's. */
static void as_ids(unsigned uid, unsigned gid, void (*fn)(long), long arg)
{
    pid_t p = fork();
    if (p == 0) {
        if (uid != 0) become(uid, gid, 0, NULL);
        fn(arg);
        _exit(0);
    }
    int s = reap(p);
    if (s != 0) say("! maker %u failed (%d)\n", uid, s);
}

/* --- N: making, removing and renaming names; the directory's write ----------- */
static void names_row(long unused)
{
    (void)unused;
    const char *r = at("n", "r"), *w = at("n", "w");
    char rf[160], rd_[160], rfull[160], rmiss[160], rnew[160], rsl[160], rhl[160], rsock[160], rg[160], wf[160], wg[160], wsk[160], rb2[160];
    snprintf(rf, sizeof rf, "%s/f", r); snprintf(rd_, sizeof rd_, "%s/d", r); snprintf(rfull, sizeof rfull, "%s/full", r);
    snprintf(rmiss, sizeof rmiss, "%s/missing", r); snprintf(rnew, sizeof rnew, "%s/new", r); snprintf(rsl, sizeof rsl, "%s/sl", r);
    snprintf(rhl, sizeof rhl, "%s/hl", r); snprintf(rsock, sizeof rsock, "%s/sock", r); snprintf(rg, sizeof rg, "%s/g", r);
    snprintf(wf, sizeof wf, "%s/f", w); snprintf(wg, sizeof wg, "%s/g", w); snprintf(wsk, sizeof wsk, "%s/sk", w);
    snprintf(rb2, sizeof rb2, "%s/b2", r);
    /* names that exist, and one that does not: what is answered first */
    long e1 = md(rd_), e2 = sl("x", rf), e3 = ln(wf, rf), e4 = sock_at(rf, NULL), e5 = ul(rmiss), e6 = rn(rmiss, rg);
    /* names that are there, of the wrong kind */
    long k1 = rd(rfull), k2 = rd(rf), k3 = ul(rd_), k4 = rn(rf, rf);
    say("names in a 0555 directory of 1000:2000 %s: an existing name: mkdir %ld, symlink %ld, link %ld, bind %ld; a missing one: unlink %ld, rename %ld; "
        "rmdir of a full directory %ld, of a file %ld; unlink of a directory %ld; rename of a name onto itself %ld\n",
        cur, e1, e2, e3, e4, e5, e6, k1, k2, k3, k4);
    /* new names, and names moved: each undone when it was let through */
    long n1 = md(rnew); if (n1 == 0) rd(rnew);
    long n2 = sl("x", rsl); if (n2 == 0) ul(rsl);
    long n3 = ln(wf, rhl); if (n3 == 0) ul(rhl);
    long n4 = sock_at(rsock, NULL); if (n4 == 0) ul(rsock);
    long n5 = rn(rf, rg); if (n5 == 0) rn(rg, rf);
    long n6 = rn(rf, wg); if (n6 == 0) rn(wg, rf);
    long n7 = rn(wf, rg); if (n7 == 0) rn(rg, wf);
    int bs = -1;
    long b1 = sock_at(wsk, &bs), b2 = -9999;
    if (bs >= 0) {
        struct sockaddr_un a;
        memset(&a, 0, sizeof a);
        a.sun_family = AF_UNIX;
        snprintf(a.sun_path, sizeof a.sun_path, "%.100s", rb2);
        b2 = rc(SYS_bind, bs, (long)&a, sizeof a, 0, 0);
        close(bs);
        ul(wsk);
        if (b2 == 0) ul(rb2);
    }
    long d1 = rc(SYS_unlinkat, AT_FDCWD, (long)rd_, AT_REMOVEDIR, 0, 0);
    long d2 = rn(wf, rf);
    long d3 = ul(rf);
    say("names in a 0555 directory of 1000:2000 %s: made: mkdir %ld, symlink %ld, link %ld, bind %ld; renamed in it %ld, out of it %ld, into it %ld; "
        "a socket bound in a 0777 one %ld, then bound again into the 0555 one %ld; removed: unlinkat(AT_REMOVEDIR) %ld; a rename over a name in it %ld; "
        "unlink %ld\n",
        cur, n1, n2, n3, n4, n5, n6, n7, b1, b2, d1, d2, d3);
}
static void dirs_row(long unused)
{
    (void)unused;
    const char *dd = at("n", "w/dd"), *dd2 = at("n", "w/dd2"), *sdd = at("n", "w/sub/dd"), *dO = at("n", "w/do"), *sdo = at("n", "w/sub/do");
    const char *dw = at("n", "w/dw"), *sdw = at("n", "w/sub/dw");
    long a = rn(dd, dd2), b = a == 0 ? rn(dd2, dd) : -9999;
    long c = rn(dd, sdd); if (c == 0) rn(sdd, dd);
    long d = rn(dO, sdo); if (d == 0) rn(sdo, dO);
    long e = rn(dw, sdw); if (e == 0) rn(sdw, dw);
    say("directories moved in a 0777 directory %s: its 0555 one renamed in place %ld and back %ld, moved to another directory %ld; its 0755 one (1000's) "
        "moved %ld; its 0777 one moved %ld\n",
        cur, a, b, c, d, e);
}

/* --- K: the sticky bit -------------------------------------------------------- */
static void sticky_rows(long unused)
{
    (void)unused;
    char m[160];
    snprintf(m, sizeof m, "%s", at("s", "st/mine"));
    long a = ul(at("s", "st/f1000")), b = ul(at("s", "st/f1001")), c = ul(at("s", "st/f0"));
    long d = rn(at("s", "st/g1002"), at("s", "st/x")); if (d == 0) rn(at("s", "st/x"), at("s", "st/g1002"));
    long e = rd(at("s", "st/d1001"));
    long fd = rc(SYS_openat, AT_FDCWD, (long)m, O_WRONLY | O_CREAT | O_EXCL, 0644, 0);
    if (fd >= 0) close((int)fd);
    long f = rn(m, at("s", "st/f1002"));
    if (f != 0) ul(m);
    long g = ul(at("s", "rt/f1000")), h = ul(at("s", "rt/f1002"));
    long i = ul(at("s", "sg/f1001")), j = ul(at("s", "sg/f1002"));
    say("sticky %s: in its 1777 directory st: unlink 1000's %ld, 1001's %ld, root's %ld; rename 1002's away %ld; rmdir 1001's %ld; a file of its own made %ld "
        "and renamed over 1002's %ld; in root's 1777 one: unlink 1000's %ld, 1002's %ld; in a 1771 one of 1000:2000: unlink 1001's %ld, 1002's %ld\n",
        cur, a, b, c, d, e, fd >= 0 ? 0L : fd, f, g, h, i, j);
}

/* --- P: the four protected settings (proc_sys_fs(5)), on -------------------- */
static void settings_row(void)
{
    static const char *N[] = { "protected_hardlinks", "protected_symlinks", "protected_regular", "protected_fifos" };
    say("settings:");
    for (int i = 0; i < 4; i++) {
        char p[96], b[16] = "?";
        snprintf(p, sizeof p, "/proc/sys/fs/%s", N[i]);
        int fd = open(p, O_RDONLY);
        if (fd >= 0) { long k = read(fd, b, sizeof b - 1); if (k > 0) b[k - 1] = 0; close(fd); }
        say(" %s %s %04o %s", N[i], b, mode_of(p), own_of(p));
    }
    say("\n");
}
static const char *LT;
static void mk_link(long which) { (void)which; if (sl("/k/p/t/f", LT) != 0) say("! symlink %s: %d\n", LT, -errno); }
static void mk_dlink(long which) { (void)which; if (sl("/k/p/t/d", LT) != 0) say("! symlink %s: %d\n", LT, -errno); }
static void links_made(void)
{
    static const struct { const char *p; unsigned u, g; int dir; } L[] = {
        { "/k/p/st/l1000", 1000, 2999, 0 }, { "/k/p/st/l1001", 1001, 2000, 0 }, { "/k/p/st/l1002", 1002, 2999, 0 }, { "/k/p/st/l0", 0, 0, 0 },
        { "/k/p/st/ld1002", 1002, 2999, 1 }, { "/k/p/sg/l1001", 1001, 2000, 0 }, { "/k/p/ww/l1002", 1002, 2999, 0 }, { "/k/p/rt/l0", 0, 0, 0 },
        { "/k/p/rt/l1002", 1002, 2999, 0 },
    };
    for (unsigned i = 0; i < sizeof L / sizeof *L; i++) {
        LT = L[i].p;
        as_ids(L[i].u, L[i].g, L[i].dir ? mk_dlink : mk_link, 0);
    }
    say("links made:");
    for (unsigned i = 0; i < sizeof L / sizeof *L; i++) say(" %s %s", L[i].p, own_of(L[i].p));
    say("\n");
}
static void symlinks_row(long unused)
{
    (void)unused;
    struct stat s;
    char b[64];
    say("protected_symlinks %s: in 1000's 1777 directory, stat through 1000's link %ld, 1001's %ld, 1002's %ld, root's %ld; 1002's: lstat %ld, readlink %ld, "
        "open %ld, access(F_OK) %ld, a link to a directory in the middle of a path %ld, chdir through it %ld; 1001's in a 1771 directory %ld; 1002's in a "
        "0777 one %ld; in root's 1777 one, root's %ld, 1002's %ld\n",
        cur, st("/k/p/st/l1000"), st("/k/p/st/l1001"), st("/k/p/st/l1002"), st("/k/p/st/l0"),
        rc(SYS_newfstatat, AT_FDCWD, (long)"/k/p/st/l1002", (long)&s, AT_SYMLINK_NOFOLLOW, 0), rc(SYS_readlink, (long)"/k/p/st/l1002", (long)b, sizeof b, 0, 0),
        op("/k/p/st/l1002", O_RDONLY), rc(SYS_access, (long)"/k/p/st/l1002", 0, 0, 0, 0), st("/k/p/st/ld1002/f"), cd("/k/p/st/ld1002"),
        st("/k/p/sg/l1001"), st("/k/p/ww/l1002"), st("/k/p/rt/l0"), st("/k/p/rt/l1002"));
}
static void regular_row(long unused)
{
    (void)unused;
    char nn[96];
    snprintf(nn, sizeof nn, "/k/p/st/n%s", tag());
    long n = op(nn, O_WRONLY | O_CREAT);
    if (n == 0) ul(nn);
    say("protected_regular %s: in 1000's 1777 directory, O_WRONLY|O_CREAT of 1000's 0666 file %ld, 1001's %ld, 1002's %ld, root's %ld; root's O_RDONLY|O_CREAT "
        "%ld, O_WRONLY %ld, O_CREAT|O_EXCL %ld; a new name %ld; in root's 1777 one, root's %ld, 1002's %ld; 1001's in a 1771 one %ld; 1002's in a 0777 one %ld\n",
        cur, op("/k/p/st/r1000", O_WRONLY | O_CREAT), op("/k/p/st/r1001", O_WRONLY | O_CREAT), op("/k/p/st/r1002", O_WRONLY | O_CREAT),
        op("/k/p/st/r0", O_WRONLY | O_CREAT), op("/k/p/st/r0", O_RDONLY | O_CREAT), op("/k/p/st/r0", O_WRONLY),
        op("/k/p/st/r0", O_WRONLY | O_CREAT | O_EXCL), n, op("/k/p/rt/r0", O_WRONLY | O_CREAT), op("/k/p/rt/r1002", O_WRONLY | O_CREAT),
        op("/k/p/sg/r1001", O_WRONLY | O_CREAT), op("/k/p/ww/r1002", O_WRONLY | O_CREAT));
}
static long hl(const char *src, int follow)
{
    const char *n = at("n", "w/h");
    long r = rc(SYS_linkat, AT_FDCWD, (long)src, AT_FDCWD, (long)n, follow ? 0x400 : 0);
    if (r == 0) ul(n);
    return r;
}
static void hardlinks_row(long unused)
{
    (void)unused;
    say("protected_hardlinks %s: a hard link to root's 0600 file %ld, 0666 %ld, 0644 %ld, 04777 %ld, 02777 %ld, 02767 %ld, 0:2000's 0660 %ld; to 1000:2000's "
        "0000 file %ld; to a directory %ld; to 1002's symbolic link itself %ld, through it (AT_SYMLINK_FOLLOW) %ld\n",
        cur, hl("/k/p/h/m0600", 0), hl("/k/p/h/m0666", 0), hl("/k/p/h/m0644", 0), hl("/k/p/h/s4777", 0), hl("/k/p/h/g2777", 0), hl("/k/p/h/g2767", 0),
        hl("/k/p/h/m0660g", 0), hl("/k/p/h/m0000o", 0), hl("/k/p/h/d", 0), hl("/k/p/ww/l1002", 0), hl("/k/p/ww/l1002", 1));
}

/* --- M: chmod ----------------------------------------------------------------- */
static void chmod_row(long unused)
{
    (void)unused;
    const char *f = at("m", "f"), *d = at("m", "d"), *r = at("m", "r");
    long a = cm(f, 0640);
    unsigned ma = mode_of(f);
    long b = rc(SYS_fchmodat, AT_FDCWD, (long)f, 0644, 0, 0);
    int fd = open(f, O_RDONLY);
    long c = fd >= 0 ? rc(SYS_fchmod, fd, 0644, 0, 0, 0) : 7000 + errno;
    if (fd >= 0) close(fd);
    fd = open(r, O_RDONLY);
    long c2 = fd >= 0 ? rc(SYS_fchmod, fd, 0644, 0, 0, 0) : 7000 + errno;
    if (fd >= 0) close(fd);
    long e = cm(r, 0600), g = cm(d, 0750);
    long h = cm(f, 02644);
    unsigned mh = mode_of(f);
    long i = cm(d, 02755);
    unsigned mi = mode_of(d);
    long j = cm(f, 04644);
    unsigned mj = mode_of(f);
    long k = cm(f, 01644);
    unsigned mk = mode_of(f);
    long l = cm("/k/w/n/f", 0644);
    say("chmod %s: its 1000:2000 file 0640 %ld mode %04o; fchmodat 0644 %ld; fchmod on a read-only descriptor %ld, of root's file %ld; root's file 0600 %ld; "
        "the directory 0750 %ld; the file 02644 %ld mode %04o, the directory 02755 %ld mode %04o, the file 04644 %ld mode %04o, 01644 %ld mode %04o; a file "
        "in a 0000 directory %ld\n",
        cur, a, ma, b, c, c2, e, g, h, mh, i, mi, j, mj, k, mk, l);
}

/* --- T: utimensat --------------------------------------------------------------- */
#define NOWS { 0, UTIME_NOW }
#define OMITS { 0, UTIME_OMIT }
static long ut(int fd, const char *p, const struct timespec *t, int fl)
{
    return rc(SYS_utimensat, fd, (long)p, (long)t, fl, 0);
}
static long fut(const char *p, int mode, const struct timespec *t)
{
    int fd = open(p, mode);
    if (fd < 0) return 7000 + errno;
    long r = ut(fd, NULL, t, 0);
    close(fd);
    return r;
}
static void times_row(long unused)
{
    (void)unused;
    static const struct timespec now2[2] = { NOWS, NOWS }, exp[2] = { { 1, 0 }, { 2, 0 } }, omitnow[2] = { OMITS, NOWS }, now5[2] = { NOWS, { 5, 0 } };
    const char *w = at("t", "w"), *r = at("t", "r"), *d = at("t", "d"), *z = at("t", "z");
    say("times %s: futimens NULL on a read-only descriptor of the 0666 file %ld, of the 0644 file %ld; {1, 2} on the 0666 one %ld; {NOW, NOW} on a write-only "
        "one %ld; utimensat NULL of a 0777 directory %ld; root's 0666 file {NOW, NOW} %ld, {1, 2} %ld; the 0666 file {OMIT, NOW} %ld, {NOW, 5} %ld; a file in "
        "a 0000 directory %ld; 1002's link itself (AT_SYMLINK_NOFOLLOW) NULL %ld, {1, 2} %ld\n",
        cur, fut(w, O_RDONLY, NULL), fut(r, O_RDONLY, NULL), fut(w, O_RDONLY, exp), fut(w, O_WRONLY, now2), ut(AT_FDCWD, d, NULL, 0), ut(AT_FDCWD, z, now2, 0),
        ut(AT_FDCWD, z, exp, 0), ut(AT_FDCWD, w, omitnow, 0), ut(AT_FDCWD, w, now5, 0), ut(AT_FDCWD, "/k/w/n/f", NULL, 0),
        ut(AT_FDCWD, "/k/p/st/l1002", NULL, AT_SYMLINK_NOFOLLOW), ut(AT_FDCWD, "/k/p/st/l1002", exp, AT_SYMLINK_NOFOLLOW));
}

/* --- B: what takes the set-ID bits away ----------------------------------------- */
static unsigned wr1(const char *p, long *r)
{
    int fd = open(p, O_WRONLY);
    *r = fd < 0 ? -errno : rc(SYS_write, fd, (long)"X", 1, 0, 0);
    if (fd >= 0) close(fd);
    return mode_of(p);
}
static void bits_row(long unused)
{
    (void)unused;
    long r1, r2, r3, r4, r5, r6, r7, r8, r9, ra, rb, rc_, rd2, re;
    unsigned m1 = wr1(at("b", "w"), &r1), m2 = wr1(at("b", "g"), &r2), m3 = wr1(at("b", "u"), &r3);
    int fd = open(at("b", "v"), O_WRONLY);
    struct iovec iv = { (void *)"X", 1 };
    r4 = fd < 0 ? -errno : rc(SYS_writev, fd, (long)&iv, 1, 0, 0);
    if (fd >= 0) close(fd);
    unsigned m4 = mode_of(at("b", "v"));
    int src = open("/k/b/src", O_RDONLY);
    fd = open(at("b", "c"), O_WRONLY);
    r5 = fd < 0 || src < 0 ? -errno : rc6(SYS_copy_file_range, src, 0, fd, 0, 1, 0);
    if (fd >= 0) close(fd);
    unsigned m5 = mode_of(at("b", "c"));
    if (src >= 0) lseek(src, 0, SEEK_SET);
    fd = open(at("b", "s"), O_WRONLY);
    r6 = fd < 0 || src < 0 ? -errno : rc(SYS_sendfile, fd, src, 0, 1, 0);
    if (fd >= 0) close(fd);
    if (src >= 0) close(src);
    unsigned m6 = mode_of(at("b", "s"));
    int pp[2];
    r7 = -9999;
    fd = open(at("b", "p"), O_WRONLY);
    if (fd >= 0 && pipe(pp) == 0) {
        if (write(pp[1], "X", 1) == 1) r7 = rc6(SYS_splice, pp[0], 0, fd, 0, 1, 0);
        close(pp[0]); close(pp[1]);
    }
    if (fd >= 0) close(fd);
    unsigned m7 = mode_of(at("b", "p"));
    fd = open(at("b", "e"), O_WRONLY | O_TRUNC);
    r8 = fd < 0 ? -errno : 0;
    if (fd >= 0) close(fd);
    unsigned m8 = mode_of(at("b", "e"));
    fd = open(at("b", "t"), O_WRONLY);
    r9 = fd < 0 ? -errno : rc(SYS_ftruncate, fd, 64, 0, 0, 0);
    if (fd >= 0) close(fd);
    unsigned m9 = mode_of(at("b", "t"));
    ra = rc(SYS_truncate, (long)at("b", "x"), 2, 0, 0, 0);
    unsigned ma = mode_of(at("b", "x"));
    fd = open(at("b", "a"), O_RDONLY);
    rb = fd < 0 ? -errno : rc(SYS_fallocate, fd, 0, 0, 4096, 0);
    if (fd >= 0) close(fd);
    fd = open(at("b", "a"), O_WRONLY);
    rc_ = fd < 0 ? -errno : rc(SYS_fallocate, fd, 0, 0, 0, 0);
    unsigned mb = mode_of(at("b", "a"));
    rd2 = fd < 0 ? -errno : rc(SYS_fallocate, fd, 0, 0, 4096, 0);
    if (fd >= 0) close(fd);
    unsigned mc = mode_of(at("b", "a"));
    long sz = size_of(at("b", "a"));
    fd = open(at("b", "z"), O_WRONLY);
    re = fd < 0 ? -errno : rc(SYS_write, fd, (long)"X", 0, 0, 0);
    if (fd >= 0) close(fd);
    unsigned md2 = mode_of(at("b", "z"));
    fd = open(at("b", "n"), O_RDWR);
    if (fd >= 0) close(fd);
    unsigned me = mode_of(at("b", "n"));
    say("bits %s (files 1000:2000): a byte written to 06777 %ld mode %04o, to 02767 %ld mode %04o, to 06766 %ld mode %04o; writev %ld mode %04o; copy_file_range "
        "%ld mode %04o; sendfile %ld mode %04o; splice %ld mode %04o; O_TRUNC of an empty one %ld mode %04o; ftruncate to 64 %ld mode %04o; truncate %ld mode "
        "%04o; fallocate on a read-only descriptor %ld, of no bytes %ld mode %04o, of 4096 %ld mode %04o size %ld; a write of no bytes %ld mode %04o; an O_RDWR "
        "open mode %04o\n",
        cur, r1, m1, r2, m2, r3, m3, r4, m4, r5, m5, r6, m6, r7, m7, r8, m8, r9, m9, ra, ma, rb, rc_, mb, rd2, mc, sz, re, md2, me);
}
static void bits_held(long unused)
{
    (void)unused;
    /* descriptor 9: opened O_WRONLY by root before the drop (alone: by itself) */
    long r = rc(SYS_write, 9, (long)"X", 1, 0, 0);
    say("bits %s: a byte written on a descriptor %s %ld, mode %04o\n", cur, alone ? "it opened itself" : "root opened before the drop", r,
        mode_of(at("b", "h")));
}

/* --- U: AF_UNIX connect: write on the socket's name ------------------------------- */
static void unix_row(long unused)
{
    (void)unused;
    say("connect %s: root's listening sockets 0777 %ld, 0775 %ld, 0772 %ld, 0000 %ld; closed ones 0000 %ld, 0777 %ld; root's files 0000 %ld, 0666 %ld; a 0777 "
        "socket in root's 0700 directory %ld\n",
        cur, conn("/t/chk/u/s777"), conn("/t/chk/u/s775"), conn("/t/chk/u/s772"), conn("/t/chk/u/s000"), conn("/t/chk/u/dead0"), conn("/t/chk/u/dead7"),
        conn("/t/chk/u/f000"), conn("/t/chk/u/f666"), conn("/t/chk/u/x/s"));
}
static int listener(const char *p, long um)
{
    umask(um);
    int s = -1;
    long r = sock_at(p, &s);
    umask(022);
    if (r != 0 || listen(s, 64) != 0) { say("! listener %s: %ld %d\n", p, r, -errno); return -1; }
    return s;
}

/* --- R9: the file-system user id decides, not the effective one ------------------- */
struct ids { long r, e, s, fs; };
static void with_ids(const struct ids *I, const char *what, void (*fn)(void))
{
    pid_t p = fork();
    if (p == 0) {
        rc(SYS_setgroups, 0, 0, 0, 0, 0);
        if (rc(SYS_setresgid, 2999, 2999, 2999, 0, 0) != 0 || rc(SYS_setresuid, I->r, I->e, I->s, 0, 0) != 0) _exit(91);
        if (I->fs >= 0) rc(SYS_setfsuid, I->fs, 0, 0, 0, 0);
        say("ids %s (uid %s): ", what, uids());
        fn();
        _exit(0);
    }
    int s = reap(p);
    if (s != 0) say("! ids %s failed (%d)\n", what, s);
}
static void r9_fs1002(void)
{
    long a = ul("/k/s/fs1/st/f1001"), b = ul("/k/s/fs1/st/f1002");
    long c = st("/k/p/st/l0"), d = op("/k/p/st/r0", O_WRONLY | O_CREAT);
    long e = rc(SYS_link, (long)"/k/p/h/m0600", (long)"/k/n/root/w/fs", 0, 0, 0); if (e == 0) ul("/k/n/root/w/fs");
    long f = rc(SYS_link, (long)"/k/p/h/m0666", (long)"/k/n/root/w/fs", 0, 0, 0); if (f == 0) ul("/k/n/root/w/fs");
    long g = cm("/k/m/fs/f", 0600), h = cm("/k/m/fs/o", 0600);
    static const struct timespec exp[2] = { { 1, 0 }, { 2, 0 } };
    long i = ut(AT_FDCWD, "/k/t/fs/r", exp, 0), j = ut(AT_FDCWD, "/k/t/fs/r", NULL, 0), k = ut(AT_FDCWD, "/k/t/fs/w", NULL, 0);
    long l;
    unsigned ml = wr1("/k/b/fs/w", &l);
    say("in 1000's 1777 directory unlink 1001's %ld, 1002's %ld; follow root's link %ld; O_CREAT of root's file %ld; a hard link to root's 0600 file %ld, 0666 "
        "%ld; chmod 1000's file %ld, 1002's %ld; 1000's 0644 file's times {1, 2} %ld, NULL %ld, its 0666 file's NULL %ld; a byte written to 1000:2000's 06777 "
        "file %ld mode %04o\n",
        a, b, c, d, e, f, g, h, i, j, k, l, ml);
}
static void r9_eff1000(void)
{
    long a = cm("/k/m/fs/r", 0600);
    long l;
    unsigned ml = wr1("/k/b/fs/v", &l);
    long f = rc(SYS_setfsuid, 0, 0, 0, 0, 0);
    long b = cm("/k/m/fs/r", 0644), c = ul("/k/s/fs0/st/f1001");
    say("chmod root's file %ld; a byte written to 1000:2000's 06777 file %ld mode %04o; then setfsuid(0) = %ld: chmod root's file %ld, unlink 1001's in 1000's "
        "1777 directory %ld\n",
        a, l, ml, f, b, c);
}
static void r9_supgroup(long unused)
{
    (void)unused;
    long a = cm("/k/m/sg/f", 02644), b = cm("/k/m/sg/d", 02755);
    say("chmod by 1000 with 2000 a supplementary group: its file 02644 %ld mode %04o, its directory 02755 %ld mode %04o\n", a, mode_of("/k/m/sg/f"), b,
        mode_of("/k/m/sg/d"));
}

/* --- the image's new cases, as the process finds them ------------------------------ */
static void census44(void)
{
    static const char *P[] = { "/k/n/own/r", "/k/n/own/w", "/k/n/own/w/dd", "/k/s/own/st", "/k/s/own/rt", "/k/s/own/sg", "/k/p/st", "/k/p/sg", "/k/p/ww", "/k/p/rt",
                               "/k/p/h/s4777", "/k/p/h/g2777", "/k/p/h/g2767", "/k/m/own/f", "/k/b/own/w", "/k/b/own/g", "/k/b/own/u", "/k/b/own/h",
                               "/k/s/self/st", "/k/b/self/w", "/k/soak/st", "/k/soak/b", NULL };
    say("image (px44):");
    for (int i = 0; P[i]; i++) say(" %s %04o %s", P[i], mode_of(P[i]), own_of(P[i]));
    say("\n");
}

static void u4(void)
{
    say("== N: names made, removed and renamed (write and search of the directory)\n");
    census44();
    each(names_row, 0);
    each(dirs_row, 0);
    say("== K: the sticky bit\n");
    each(sticky_rows, 0);
    say("== P: the protected settings\n");
    settings_row();
    if (!alone) links_made();
    else {
        /* a user alone can make only its own link: in 1001's 1777 directory */
        long a = sl("/k/p/t/f", "/k/p/su/lself");
        say("protected_symlinks self: its own link in 1001's 1777 directory made %ld, followed %ld\n", a, st("/k/p/su/lself"));
    }
    if (!alone) each(symlinks_row, 0);
    each(regular_row, 0);
    each(hardlinks_row, 0);
    say("== M: chmod\n");
    each(chmod_row, 0);
    say("== T: utimensat\n");
    each(times_row, 0);
    say("== B: what takes the set-ID bits away\n");
    each(bits_row, 0);
    if (alone) {
        int fd = open(at("b", "h"), O_WRONLY);
        if (fd >= 0 && dup2(fd, 9) == 9) bits_held(0);
        if (fd >= 0) close(fd);
    } else
        for (int a = 0; a < NA; a++) {
            cur = A[a].name;
            pid_t p = fork();
            if (p == 0) {
                int fd = open(at("b", "h"), O_WRONLY);
                if (fd < 0 || dup2(fd, 9) != 9) { say("! bits held %s: %d\n", cur, -errno); _exit(93); }
                if (A[a].uid != 0) become(A[a].uid, A[a].gid, A[a].ng, A[a].gs);
                else rc(SYS_setgroups, 0, 0, 0, 0, 0);
                bits_held(0);
                _exit(0);
            }
            int s = reap(p);
            if (s != 0) say("! actor %s failed (%d)\n", A[a].name, s);
        }
    if (alone) return;
    say("== U: AF_UNIX connect\n");
    if (mkdir("/t/chk/u", 0755) != 0) say("! mkdir /t/chk/u: %d\n", -errno);
    int l1 = listener("/t/chk/u/s777", 0), l2 = listener("/t/chk/u/s775", 002), l3 = listener("/t/chk/u/s772", 005), l4 = listener("/t/chk/u/s000", 0777);
    int d0 = listener("/t/chk/u/dead0", 0777), d7 = listener("/t/chk/u/dead7", 0);
    if (d0 >= 0) close(d0);
    if (d7 >= 0) close(d7);
    umask(0777);
    int f = open("/t/chk/u/f000", O_WRONLY | O_CREAT | O_EXCL, 0666);
    if (f >= 0) close(f);
    umask(0);
    f = open("/t/chk/u/f666", O_WRONLY | O_CREAT | O_EXCL, 0666);
    if (f >= 0) close(f);
    umask(077);
    if (mkdir("/t/chk/u/x", 0777) != 0) say("! mkdir /t/chk/u/x: %d\n", -errno);
    umask(022);
    int l5 = listener("/t/chk/u/x/s", 0);
    say("made by root: s777 %04o, s775 %04o, s772 %04o, s000 %04o, dead0 %04o, dead7 %04o, f000 %04o, f666 %04o, x %04o, x/s %04o\n", mode_of("/t/chk/u/s777"),
        mode_of("/t/chk/u/s775"), mode_of("/t/chk/u/s772"), mode_of("/t/chk/u/s000"), mode_of("/t/chk/u/dead0"), mode_of("/t/chk/u/dead7"),
        mode_of("/t/chk/u/f000"), mode_of("/t/chk/u/f666"), mode_of("/t/chk/u/x"), mode_of("/t/chk/u/x/s"));
    each(unix_row, 0);
    int L[] = { l1, l2, l3, l4, l5 };
    for (int i = 0; i < 5; i++) if (L[i] >= 0) close(L[i]);
    say("== R: the file-system user id decides\n");
    static const struct ids F1002 = { 0, 0, 0, 1002 }, E1000 = { 0, 1000, 0, -1 };
    with_ids(&F1002, "(0 0 0) after setfsuid(1002)", r9_fs1002);
    with_ids(&E1000, "(0 1000 0)", r9_eff1000);
    {
        pid_t p = fork();
        if (p == 0) {
            unsigned gs[1] = { 2000 };
            become(1000, 2999, 1, gs);
            r9_supgroup(0);
            _exit(0);
        }
        reap(p);
    }
}

/* --- the soak ------------------------------------------------------------------ */
static long memfree(void)
{
    return atol(status_line("/proc/meminfo", "MemFree"));
}
static int soak(long n)
{
    unsigned me = getuid();
    int root = me == 0;
    long wrong = 0, calls = 0, execs = 0, mem[5] = { 0, 0, 0, 0, 0 };
    long no = root ? 0 : -13; /* what a user is told where root is let through */
    char mk[64];
    snprintf(mk, sizeof mk, "/k/c/a/s%u", me);
    static const struct timespec T12[2] = { { 1, 0 }, { 2, 0 } };
    int bfd = open("/k/soak/b", O_WRONLY);
    if (bfd < 0) { say("! soak: /k/soak/b %d\n", -errno); return 1; }
    mem[0] = memfree();
    for (long i = 0; i < n; i++) {
        wrong += op("/k/o/g", O_RDONLY) != no;
        wrong += op("/k/o/rw", O_RDWR) != 0;
        wrong += st("/k/w/n/f") != no;
        wrong += st("/k/w/o/f") != 0;
        wrong += rc(SYS_access, (long)"/k/a/root", 4, 0, 0, 0) != no;
        wrong += rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/root", 4, AT_EACCESS, 0) != no;
        long fd = rc(SYS_openat, AT_FDCWD, (long)mk, O_WRONLY | O_CREAT | O_EXCL, 0600, 0);
        wrong += fd < 0;
        if (fd >= 0) close((int)fd);
        wrong += unlink(mk) != 0;
        wrong += rc(SYS_truncate, (long)"/k/o/ro", 7, 0, 0, 0) != no;
        wrong += cd("/k/w/n") != no;
        /* px44: names, sticky, the protected settings, chmod, times, set-ID bits */
        long r = md("/k/soak/r/x");
        wrong += r != no;
        if (r == 0) rd("/k/soak/r/x");
        r = rn("/k/soak/w/f", "/k/soak/r/f");
        wrong += r != no;
        if (r == 0) rn("/k/soak/r/f", "/k/soak/w/f");
        r = rn("/k/soak/st/f1001", "/k/soak/st/g");
        wrong += r != (root ? 0 : -1);
        if (r == 0) rn("/k/soak/st/g", "/k/soak/st/f1001");
        r = ln("/k/soak/h0", "/k/soak/w/l");
        wrong += r != (root ? 0 : -1);
        if (r == 0) ul("/k/soak/w/l");
        wrong += op("/k/soak/st/r0", O_WRONLY | O_CREAT) != no;
        wrong += cm("/k/soak/m", 0644) != (root ? 0 : -1);
        wrong += ut(AT_FDCWD, "/k/soak/m", T12, 0) != (root ? 0 : -1);
        wrong += cm("/k/soak/b", 06777) != 0;
        wrong += rc(SYS_pwrite64, bfd, (long)"X", 1, 0, 0) != 1;
        wrong += mode_of("/k/soak/b") != (root ? 06777u : 0777u);
        calls += 20;
        if (i % 1000 == 0) {
            wrong += run7("/k/x/m0700") != 0;
            wrong += run7("/k/x/m0070") != no;
            execs += 2;
        }
        if (n >= 4 && (i + 1) % (n / 4) == 0 && (i + 1) / (n / 4) <= 4) mem[(i + 1) / (n / 4)] = memfree();
    }
    close(bfd);
    say("soak: %ld rounds, %ld calls that open, walk, ask access, truncate, make, remove, rename, link, chmod, set times and write set-ID files, %ld execs, "
        "%ld wrong answers, as uid %u\n", n, calls, execs,
        wrong, me);
    say("~soak: MemFree before %ld kB, at each quarter %ld %ld %ld %ld kB\n", mem[0], mem[1], mem[2], mem[3], mem[4]);
    return wrong ? 1 : 0;
}

int main(int argc, char **argv)
{
    memset(LONGNAME, 'a', 256);
    if (argc > 2 && strcmp(argv[1], "soak") == 0) return soak(atol(argv[2]));
    alone = argc > 1 && strcmp(argv[1], "user") == 0;
    if (!alone && getuid() != 0) { say("usage: chk (as root) | chk user | chk soak N\n"); return 2; }
    umask(022);
    say("chk: uid %s gid %s groups '%s'\n", uids(), gids(), groups());
    census();

    say("== W: the search of every directory a path passes\n");
    for (long i = 0; i < 5; i++) each(walk_row, i);
    each(deep_row, 0);
    if (!alone) {
        for (long i = 0; i < 5; i++)
            for (int a = 0; a < NA; a++) root_then(a, WD[i], 0, cwd_row, i);
        for (long i = 3; i < 5; i++)
            for (int a = 0; a < NA; a++) root_then(a, WD[i], 1, dirfd_row, i);
    }
    LK = alone ? "/t/chku" : "/t/chk";
    if (mkdir(LK, 0755) != 0) say("! mkdir %s: %d\n", LK, -errno);
    {
        long a = symlink("/k/w/n/f", path(LK, "ln")), b = symlink("/k/w/o/f", path(LK, "lo")), c = symlink("../../k/w/t/f", path(LK, "lt")),
             d = symlink("/k/w/n", path(LK, "ldn"));
        if (a || b || c || d) say("! symlink: %d\n", -errno);
    }
    each(link_row, 0);

    say("== O: open and truncate\n");
    each(open_row, 0);
    say("== C: a name made in a directory\n");
    each(create_row, 0);

    say("== A: the access family\n");
    if (alone) access_lines("self");
    else {
        static const struct state S[] = {
            { 1000, 1001, 1001, -1, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 1001, 1000, 1000, -1, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 0, 1000, 0, -1, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 1000, 0, 0, -1, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 0, 0, 0, 1002, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 0, 1000, 0, 0, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 1000, 0, 0, 1000, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 1003, 1003, 1003, -1, 2000, 2999, 2999, -1, 0, { 0, 0 } },
            { 1003, 1003, 1003, -1, 2999, 2000, 2000, -1, 0, { 0, 0 } },
            { 1003, 1003, 1003, -1, 2000, 2000, 2000, 2999, 0, { 0, 0 } },
            { 1003, 1003, 1003, -1, 2999, 2999, 2999, -1, 1, { 2000, 0 } },
            { 1002, 1002, 1002, -1, 2000, 2000, 2000, -1, 0, { 0, 0 } },
            { 0, 0, 0, -1, 0, 0, 0, -1, 0, { 0, 0 } },
        };
        for (unsigned i = 0; i < sizeof S / sizeof *S; i++) access_state(&S[i]);
    }

    say("== X: execve of an archive file 1000:2000, by mode and by who asks\n");
    for (long i = 0; i < (long)NXM; i++) each(exec_row, i);
    each(exec_more, 0);
    if (!alone) {
        pid_t p = fork();
        if (p == 0) {
            rc(SYS_setgroups, 0, 0, 0, 0, 0);
            long f = rc(SYS_setfsuid, 1002, 0, 0, 0, 0);
            say("exec root after setfsuid(1002) = %ld: m0700 %ld, m0070 %ld, m0007 %ld, m0001 %ld, m0000 %ld\n", f, run7("/k/x/m0700"), run7("/k/x/m0070"),
                run7("/k/x/m0007"), run7("/k/x/m0001"), run7("/k/x/m0000"));
            _exit(0);
        }
        reap(p);
    }

    say("== H: a descriptor that outlives a change of mode\n");
    if (alone) held_alone();
    else for (int a = 0; a < NA; a++) held_by(a);

    if (!alone) {
        say("== S: a socket's name\n");
        struct sockaddr_un a;
        memset(&a, 0, sizeof a);
        a.sun_family = AF_UNIX;
        snprintf(a.sun_path, sizeof a.sun_path, "/t/chk/sock");
        int s = socket(AF_UNIX, SOCK_STREAM, 0);
        umask(0777);
        long b = s < 0 ? -errno : bind(s, (struct sockaddr *)&a, sizeof a) == 0 ? 0L : -(long)errno;
        umask(022);
        say("bound by root with umask 0777: %ld, %04o %s\n", b, mode_of("/t/chk/sock"), own_of("/t/chk/sock"));
        each(sock_row, 0);
        if (s >= 0) close(s);
        unlink("/t/chk/sock");
    }
    u4();
    say("chk: done\n");
    return 0;
}
