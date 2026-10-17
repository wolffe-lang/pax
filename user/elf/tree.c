/* tree.c — px27's probe of a writable file tree: one static glibc
   program that prints what it sees, run unmodified as the first program
   on Linux (its root a tmpfs, inside a throwaway container) and on PAX
   (tests/mpx3-tree), the two outputs compared byte for byte. Every line
   is something a kernel decides: what `open` makes and refuses, where
   `O_APPEND` puts a write, what a hole reads as and what it costs, what
   `ftruncate` gives back, what is left of a file whose name is gone
   while it is open, what `rename` replaces and refuses, a directory's
   size and link count, what a reading of a directory returns while the
   directory changes, a working directory that has been removed, which
   times move and when, and the errnos. px36 adds the changes after a
   file is made: hard links (counts, a name removed, a rename between
   two names of one file), symbolic links (what follows them and what
   does not, ELOOP, O_NOFOLLOW, what a target costs), modes, times set
   to the nanosecond, owners as root sees them, and what PAX keeps
   fixed.

     tree             every probe, in order (it works in /t, which it
                      makes and removes)
     tree soak        10,000 rounds of create, write, rename, unlink
                      (and mkdir, rmdir; px36: link, symlink, chmod,
                      utimensat and two renames over names), then a
                      fill to ENOSPC and
                      back, twice: the second time with 120 MiB of the
                      program's own memory held
     tree noop        (a role the probe starts: exit 7)
     tree speed       16 MiB written and read back, then 64 more
                      passes over it (1 GiB each way), timed

   Built with the host's cc: `cc -static -O1` (tools/mkprobes). Lines
   that depend on the host and not on the ABI (how many megabytes fit, a
   time in milliseconds, what PAX refuses by name and Linux does) start
   with `~` and are not compared. Nothing here reads a kernel's or a
   libc's source: the calls are the man pages', the structures the
   public headers'. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/sendfile.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void say(const char *fmt, ...) {
    char b[1024];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1) n = sizeof b - 1;
    int o = 0;
    while (o < n) {
        ssize_t w = write(1, b + o, n - o);
        if (w <= 0) break;
        o += w;
    }
}

/* -1 with errno E as "-E", else the value */
static long r(long v) { return v == -1 ? -errno : v; }
static void ms(int n) {
    struct timespec t = { n / 1000, (n % 1000) * 1000000L };
    while (nanosleep(&t, &t) != 0 && errno == EINTR) {}
}
static long long ns_of(struct timespec t) { return t.tv_sec * 1000000000LL + t.tv_nsec; }
static long long wall(void) {
    struct timespec t;
    clock_gettime(CLOCK_REALTIME, &t);
    return ns_of(t);
}
static long mono_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

/* "mode 100644 links 1 size 5 blocks 8", or "-2" */
static const char *st(const char *path) {
    static char b[4][96];
    static int k;
    struct stat s;
    char *o = b[k++ & 3];
    if (stat(path, &s) != 0) snprintf(o, 96, "%d", -errno);
    else snprintf(o, 96, "mode %o links %lu size %lld blocks %lld", s.st_mode, (unsigned long)s.st_nlink,
                  (long long)s.st_size, (long long)s.st_blocks);
    return o;
}
static const char *fst(int fd) {
    static char b[4][96];
    static int k;
    struct stat s;
    char *o = b[k++ & 3];
    if (fstat(fd, &s) != 0) snprintf(o, 96, "%d", -errno);
    else snprintf(o, 96, "mode %o links %lu size %lld blocks %lld", s.st_mode, (unsigned long)s.st_nlink,
                  (long long)s.st_size, (long long)s.st_blocks);
    return o;
}
static long put(const char *path, const char *text) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) return -errno;
    long w = r(write(fd, text, strlen(text)));
    close(fd);
    return w;
}
/* a file's whole text (at most 255 bytes), or "-E" */
static const char *get(const char *path) {
    static char b[4][256];
    static int k;
    char *o = b[k++ & 3];
    int fd = open(path, O_RDONLY);
    if (fd < 0) { snprintf(o, 256, "%d", -errno); return o; }
    ssize_t n = read(fd, o, 255);
    if (n < 0) snprintf(o, 256, "%d", -errno); else o[n] = 0;
    close(fd);
    return o;
}

static ino_t ino_of(const char *p) {
    struct stat s;
    return stat(p, &s) == 0 ? s.st_ino : 0;
}

/* Every answer is taken in a statement of its own, in the order the
   line names it: C leaves the order of a call's arguments open. */

/* ---- making: mkdir, open with O_CREAT, the mode and umask ----------------- */
static void making(void) {
    mode_t um = umask(022);
    umask(um);
    long a = r(mkdir("/t", 0777)), b = r(mkdir("/t", 0777));
    say("make: umask %03o; mkdir /t %ld, again %ld, /t: %s\n", um, a, b, st("/t"));
    put("/t/f", "x");
    a = r(mkdir("/t/no/such", 0777));
    b = r(mkdir("/t/f/d", 0777));
    long c = r(mkdir("/t/slash/", 0777));
    const char *s1 = st("/t/slash");
    long d = r(mkdir("/t/.", 0777)), e = r(mkdir("/", 0777)), f = r(mkdir("/dev", 0777));
    say("make: mkdir /t/no/such %ld, under a file %ld, with a trailing slash %ld (%s), of . %ld, of / %ld, of /dev %ld\n", a, b, c,
        s1, d, e, f);
    int fd = open("/t/a", O_WRONLY | O_CREAT | O_EXCL, 0666);
    s1 = fst(fd);
    a = r(open("/t/a", O_WRONLY | O_CREAT | O_EXCL, 0666));
    int fd2 = open("/t/a", O_WRONLY | O_CREAT, 0666);
    say("create: O_CREAT|O_EXCL makes it %d, %s; again %ld; O_CREAT alone opens it %d\n", fd >= 0, s1, a, fd2 >= 0);
    close(fd2);
    a = r(write(fd, "hello", 5));
    s1 = fst(fd);
    b = r(lseek(fd, 0, SEEK_CUR));
    char ch = 0;
    c = r(read(fd, &ch, 1));
    say("create: write 5 bytes %ld, %s, the offset %ld; a read on it %ld\n", a, s1, b, c);
    close(fd);
    fd = open("/t/a", O_RDONLY);
    s1 = get("/t/a");
    a = r(write(fd, &ch, 1));
    say("create: read back '%s'; a write on a descriptor opened to read %ld\n", s1, a);
    close(fd);
    fd = open("/t/a", O_WRONLY | O_TRUNC);
    say("create: O_TRUNC leaves %s\n", fst(fd));
    close(fd);
    put("/t/a", "hello");
    fd = open("/t/a", O_RDONLY | O_TRUNC);
    say("create: O_RDONLY|O_TRUNC opens %d and leaves %s\n", fd >= 0, st("/t/a"));
    close(fd);
    a = r(open("/t", O_WRONLY));
    b = r(open("/t", O_RDWR));
    c = r(open("/t", O_RDONLY | O_CREAT, 0666));
    d = r(open("/t/a/", O_RDONLY));
    e = r(open("/t/a", O_RDONLY | O_DIRECTORY));
    say("create: a directory opened to write %ld, to read and write %ld, with O_CREAT %ld; a file with a trailing slash %ld; O_DIRECTORY on a file %ld\n",
        a, b, c, d, e);
    a = r(open("/t/no/x", O_WRONLY | O_CREAT, 0666));
    b = r(open("/t/a/x", O_WRONLY | O_CREAT, 0666));
    c = r(open("/t/new/", O_WRONLY | O_CREAT, 0666));
    d = r(open("/t/none", O_WRONLY));
    say("create: in a missing directory %ld, under a file %ld, a new name with a trailing slash %ld, a missing name without O_CREAT %ld\n",
        a, b, c, d);
    mode_t old = umask(027);
    close(open("/t/m1", O_WRONLY | O_CREAT, 0666));
    mkdir("/t/md", 0777);
    s1 = st("/t/m1");
    say("mode: under umask 027 (the old one %03o): %s; %s\n", old, s1, st("/t/md"));
    umask(0);
    close(open("/t/m2", O_WRONLY | O_CREAT, 0666));
    close(open("/t/m3", O_WRONLY | O_CREAT, 0));
    fd = open("/t/m3", O_RDWR);
    s1 = st("/t/m2");
    say("mode: under umask 0: %s; made with mode 0: %s, and root opens it to write %d\n", s1, st("/t/m3"), fd >= 0);
    close(fd);
    say("mode: umask answers the old mask %03o\n", umask(022));
    a = r(unlink("/t/f")); b = r(unlink("/t/a")); c = r(unlink("/t/m1")); d = r(unlink("/t/m2")); e = r(unlink("/t/m3"));
    f = r(rmdir("/t/md"));
    long g = r(rmdir("/t/slash"));
    say("make: unlink the five %ld %ld %ld %ld %ld, rmdir the two %ld %ld\n", a, b, c, d, e, f, g);
}

/* ---- O_APPEND -------------------------------------------------------------- */
static void appending(void) {
    int a = open("/t/log", O_WRONLY | O_CREAT | O_APPEND, 0666);
    int b = open("/t/log", O_WRONLY | O_APPEND);
    int p = open("/t/log", O_WRONLY);
    write(a, "one\n", 4);
    write(b, "two\n", 4);
    write(a, "three\n", 6);
    const char *g = get("/t/log");
    say("append: two descriptors, three writes: '%s' (%s)\n", g, st("/t/log"));
    write(p, "ONE", 3);
    say("append: a third without O_APPEND writes at its own offset: '%s'\n", get("/t/log"));
    long at = r(lseek(a, 0, SEEK_SET));
    write(a, "four\n", 5);
    const char *s1 = st("/t/log") + 20;
    long off = r(lseek(a, 0, SEEK_CUR));
    say("append: after lseek to %ld the appending one still appends: %s, its offset %ld\n", at, s1, off);
    long pw = r(pwrite(a, "five\n", 5, 0));
    g = get("/t/log");
    say("append: pwrite at 0 on it %ld: the file starts '%.3s' and is %s\n", pw, g, st("/t/log") + 20);
    close(a); close(b); close(p);
    /* two processes, 200 lines each of 32 bytes: every line whole */
    unlink("/t/log");
    pid_t k = fork();
    int fd = open("/t/log", O_WRONLY | O_CREAT | O_APPEND, 0666);
    char line[33];
    memset(line, k == 0 ? 'c' : 'p', 31);
    line[31] = '\n';
    for (int i = 0; i < 200; i++) {
        if (write(fd, line, 32) != 32) _exit(9);
        if (i % 16 == 0) sched_yield();
    }
    close(fd);
    if (k == 0) _exit(0);
    int ws = 0;
    waitpid(k, &ws, 0);
    fd = open("/t/log", O_RDONLY);
    int whole = 1, nc = 0, np = 0;
    char got[32];
    while (read(fd, got, 32) == 32) {
        for (int i = 1; i < 31; i++) if (got[i] != got[0]) whole = 0;
        if (got[31] != '\n') whole = 0;
        if (got[0] == 'c') nc++; else if (got[0] == 'p') np++; else whole = 0;
    }
    close(fd);
    say("append: two processes, 200 lines each: the child's status %d, %s, the child's lines %d, the parent's %d, every line whole %d\n",
        ws, st("/t/log") + 20, nc, np, whole);
    unlink("/t/log");
}

/* ---- holes, pwrite, truncation ----------------------------------------------- */
static void holes(void) {
    int fd = open("/t/h", O_RDWR | O_CREAT, 0666);
    long at = r(lseek(fd, 1048576, SEEK_SET));
    const char *s1 = fst(fd) + 20;
    write(fd, "x", 1);
    say("hole: lseek past the end %ld leaves %s; one byte written there: %s\n", at, s1, fst(fd) + 20);
    char z[16] = "................";
    long n = r(pread(fd, z, 16, 4000));
    int zero = 1;
    for (int i = 0; i < 16; i++) if (z[i] != 0) zero = 0;
    long a = r(pread(fd, z, 16, 1048576)), b = r(pread(fd, z, 16, 2000000));
    say("hole: 16 bytes read from the hole %ld, all zero %d; read at the end %ld, past it %ld\n", n, zero, a, b);
    a = r(pwrite(fd, "abc", 3, 12288));
    say("hole: pwrite of 3 bytes at 12288: %ld, %s\n", a, fst(fd) + 20);
    a = r(ftruncate(fd, 5000));
    s1 = fst(fd) + 20;
    b = r(ftruncate(fd, 10000));
    say("hole: ftruncate to 5000: %ld, %s; to 10000: %ld, %s\n", a, s1, b, fst(fd) + 20);
    char w[20];
    memset(w, 'q', 20);
    a = r(pwrite(fd, w, 20, 4086));
    say("hole: 20 bytes across the page boundary at 4086: %ld, %s\n", a, fst(fd) + 20);
    ftruncate(fd, 4090);
    ftruncate(fd, 10000);
    char back[20];
    pread(fd, back, 20, 4086);
    int tail = 1;
    for (int i = 4; i < 20; i++) if (back[i] != 0) tail = 0;
    say("hole: cut to 4090 and grown again: the four bytes kept '%.4s', what was cut reads zero %d, %s\n", back, tail, fst(fd) + 20);
    a = r(ftruncate(fd, 0));
    s1 = fst(fd) + 20;
    b = r(ftruncate(fd, -1));
    say("hole: ftruncate to 0: %ld, %s; to -1: %ld\n", a, s1, b);
    int rd = open("/t/h", O_RDONLY);
    write(fd, "0123456789", 10);
    a = r(ftruncate(rd, 0));
    b = r(truncate("/t/h", 7));
    s1 = st("/t/h") + 20;
    long c = r(truncate("/t", 0)), d = r(truncate("/t/none", 0));
    say("hole: ftruncate on a descriptor opened to read %ld; truncate by path to 7: %ld (%s), of a directory %ld, of a missing name %ld\n",
        a, b, s1, c, d);
    a = r(pwrite(rd, "x", 1, 0));
    close(rd);
    rd = open("/t/h", O_WRONLY);
    b = r(pread(rd, z, 1, 0));
    c = r(pwrite(fd, "x", 1, -1));
    say("hole: pwrite on a descriptor opened to read %ld, pread on one opened to write %ld, pwrite at a negative offset %ld\n", a, b, c);
    close(rd);
    a = r(fsync(fd));
    b = r(fdatasync(fd));
    rd = open("/t", O_RDONLY);
    c = r(fsync(rd));
    close(rd);
    d = r(fsync(rd));
    say("sync: fsync %ld, fdatasync %ld, of a directory %ld, of a closed descriptor %ld\n", a, b, c, d);
    close(fd);
    unlink("/t/h");
    /* a larger file (two levels of index on PAX): cut in the middle,
       cut again, written past the cut, a byte far out */
    static char mbuf[1 << 20];
    memset(mbuf, 'M', sizeof mbuf);
    fd = open("/t/h5", O_RDWR | O_CREAT, 0666);
    long wr = 0;
    for (int i = 0; i < 5; i++) wr += write(fd, mbuf, sizeof mbuf);
    s1 = fst(fd) + 20;
    a = r(ftruncate(fd, 3 * 1048576 + 100));
    const char *s2 = fst(fd) + 20;
    b = r(ftruncate(fd, 1048576));
    const char *s3 = fst(fd) + 20;
    say("hole: 5 MiB written %ld, %s; cut to 3 MiB and 100 bytes %ld, %s; to 1 MiB %ld, %s\n", wr, s1, a, s2, b, s3);
    ftruncate(fd, 5 * 1048576);
    char probe[8];
    n = r(pread(fd, probe, 8, 2 * 1048576));
    zero = 1;
    for (int i = 0; i < 8; i++) if (probe[i] != 0) zero = 0;
    a = r(pread(fd, probe, 8, 1048576 - 8));
    int kept = probe[0] == 'M' && probe[7] == 'M';
    b = r(pwrite(fd, "far", 3, 4 * 1048576 + 5));
    s1 = fst(fd) + 20;
    long c2 = r(pwrite(fd, "x", 1, 700 * 1048576L));
    say("hole: grown back to 5 MiB: what was cut reads zero %d (%ld), what was kept is there %d (%ld); 3 bytes written at 4 MiB %ld, %s; one byte at 700 MiB %ld, %s\n",
        zero, n, kept, a, b, s1, c2, fst(fd) + 20);
    close(fd);
    unlink("/t/h5");
}

/* ---- a file whose name is gone while it is open -------------------------------- */
static void unlinked(void) {
    int fd = open("/t/u", O_RDWR | O_CREAT, 0666);
    char page[4096];
    memset(page, 'u', sizeof page);
    for (int i = 0; i < 3; i++) write(fd, page, sizeof page);
    int d = dup(fd);
    const char *s1 = fst(fd);
    long a = r(unlink("/t/u"));
    const char *s2 = st("/t/u");
    say("unlinked: %s; unlink %ld; by name %s; by descriptor %s\n", s1, a, s2, fst(fd));
    char b[8];
    long n = r(pread(fd, b, 8, 8000));
    a = r(write(d, page, sizeof page));
    s1 = fst(d) + 20;
    put("/t/u", "new");
    say("unlinked: still read %ld '%.8s', written %ld, %s; the name made again is another file: %s\n", n, b, a, s1, st("/t/u"));
    close(fd);
    say("unlinked: after one close the other descriptor still reads %ld; then closed\n", r(pread(d, b, 8, 12288)));
    close(d);
    unlink("/t/u");
    mkdir("/t/d", 0777);
    put("/t/d/x", "x");
    a = r(unlink("/t/d"));
    long c = r(unlink("/t/none")), e = r(unlink("/t/d/x/")), f = r(unlink("/t/d/."));
    say("remove: unlink of a directory %ld, of a missing name %ld, of a file with a trailing slash %ld, of . %ld\n", a, c, e, f);
    a = r(rmdir("/t/d/x")); c = r(rmdir("/t/d")); e = r(rmdir("/t/none")); f = r(rmdir("/t/d/."));
    long g = r(rmdir("/t/d/..")), h = r(rmdir("/")), i = r(rmdir("/dev"));
    say("remove: rmdir of a file %ld, of a directory with an entry %ld, of a missing name %ld, of d/. %ld, of d/.. %ld, of / %ld, of /dev %ld\n",
        a, c, e, f, g, h, i);
    /* px49 (pax#70): /dev and /proc are names in `/`: a user who may not
     * write `/` is told -EACCES before what they are (root -EISDIR). */
    a = r(unlink("/dev")); c = r(unlink("/proc"));
    say("remove: unlink of /dev %ld, of /proc %ld\n", a, c);
    a = r(unlinkat(AT_FDCWD, "/t/d/x", AT_REMOVEDIR));
    c = r(unlinkat(AT_FDCWD, "/t/d", 0));
    e = r(unlinkat(AT_FDCWD, "/t/d/x", 0));
    f = r(unlinkat(AT_FDCWD, "/t/d", AT_REMOVEDIR));
    say("remove: unlinkat with AT_REMOVEDIR on a file %ld, without it on a directory %ld; then the file %ld and the directory %ld\n", a,
        c, e, f);
}

/* ---- a working directory that is removed ------------------------------------- */
static void workdir(void) {
    char p[256];
    mkdir("/t/w", 0777);
    int dfd = open("/t/w", O_RDONLY | O_DIRECTORY);
    long a = r(chdir("/t/w"));
    char *g = getcwd(p, sizeof p);
    say("cwd: chdir %ld, getcwd '%s'; ", a, g ? p : "?");
    say("rmdir of it from inside %ld; ", r(rmdir("../w")));
    g = getcwd(p, sizeof p);
    long ge = g ? 0 : -errno;
    char buf[256];
    long gd = syscall(SYS_getdents64, dfd, buf, sizeof buf);
    gd = gd == -1 ? -errno : gd;
    const char *s1 = st(".");
    say("then getcwd %ld, . is %s, by descriptor %s, a reading of it %ld\n", ge, s1, fst(dfd), gd);
    a = r(open("f", O_WRONLY | O_CREAT, 0666));
    long b = r(mkdir("d", 0777));
    int o = open(".", O_RDONLY);
    int up = ino_of("..") == ino_of("/t");
    say("cwd: a file made in it %ld, a directory %ld, . opened %d, .. is /t %d, the name is gone %s\n", a, b, o >= 0, up, st("/t/w"));
    close(o);
    a = r(chdir(".."));
    g = getcwd(p, sizeof p);
    say("cwd: chdir .. %ld, getcwd '%s'; /t: %s\n", a, g ? p : "?", st("/t"));
    close(dfd);
    chdir("/");
}

/* ---- rename ---------------------------------------------------------------------- */
static void renaming(void) {
    char p[256];
    put("/t/a", "aaa");
    put("/t/b", "bbbbb");
    ino_t ia = ino_of("/t/a");
    int fb = open("/t/b", O_RDONLY);
    int fa = open("/t/a", O_RDWR);
    long a = r(rename("/t/a", "/t/c"));
    const char *s1 = st("/t/a");
    const char *g = get("/t/c");
    say("rename: a to c %ld: a %s, c '%s', the same inode %d\n", a, s1, g, ino_of("/t/c") == ia);
    a = r(rename("/t/c", "/t/b"));
    g = get("/t/b");
    s1 = st("/t/c");
    say("rename: c over b %ld: b '%s', c %s; the replaced file by its descriptor: %s", a, g, s1, fst(fb));
    char old[8] = "";
    read(fb, old, 5);
    a = r(pwrite(fa, "Z", 1, 0));
    say(", read '%.5s'; the moved file's descriptor writes on: %ld, b '%s'\n", old, a, get("/t/b"));
    close(fa); close(fb);
    a = r(rename("/t/b", "/t/b"));
    long b = r(rename("/t/b", "/t/./b"));
    s1 = st("/t/b");
    long c = r(rename("/t/none", "/t/x")), d = r(rename("/t/b", "/t/no/x")), e = r(rename("/t/b", "/t/nodir/"));
    say("rename: b to b %ld, to ./b %ld (%s); a missing name %ld; into a missing directory %ld; a file to a missing name with a slash %ld\n",
        a, b, s1, c, d, e);
    mkdir("/t/d1", 0777);
    mkdir("/t/d1/in", 0777);
    put("/t/d1/in/f", "f");
    mkdir("/t/d2", 0777);
    mkdir("/t/e", 0777);
    s1 = st("/t") + 11;
    say("rename: /t %s, d1 %s; ", s1, st("/t/d1") + 11);
    a = r(rename("/t/b", "/t/e"));
    b = r(rename("/t/e", "/t/b"));
    c = r(rename("/t/e", "/t/d1"));
    d = r(rename("/t/d1", "/t/d1/sub"));
    e = r(rename("/t/d1", "/t/d1/in/deep"));
    say("a file onto a directory %ld, a directory onto a file %ld, a directory onto one with an entry %ld, into itself %ld, below itself %ld\n",
        a, b, c, d, e);
    ia = ino_of("/t/e");
    a = r(rename("/t/e", "/t/d2"));
    int same = ino_of("/t/d2") == ia;
    s1 = st("/t/e");
    b = r(rename("/t/d2", "/t/d3/"));
    say("rename: a directory onto an empty one %ld (d2's inode is now e's %d, e %s); to a new name with a slash %ld\n", a, same, s1, b);
    chdir("/t/d1/in");
    a = r(rename("/t/d1/in", "/t/d3/moved"));
    s1 = st("/t") + 11;
    const char *s2 = st("/t/d3") + 11;
    say("rename: a directory moved under another %ld: /t %s, d3 %s, d1 %s; ", a, s1, s2, st("/t/d1") + 11);
    char *cw = getcwd(p, sizeof p);
    int up = ino_of("..") == ino_of("/t/d3");
    say("a process working in it is now in '%s', its .. is d3 %d, its file '%s'\n", cw ? p : "?", up, get("f"));
    chdir("/");
    a = r(rename("/t/d1/.", "/t/x"));
    b = r(rename("/t/d1/..", "/t/x"));
    c = r(rename("/t/d1", "/t/."));
    d = r(rename("/", "/t/x"));
    e = r(rename("/dev", "/t/x"));
    long f = r(rename("/t/d1", "/dev"));
    long h = r(rename("/t/b", "/dev/px27-probe"));
    long i = r(rename("/dev/null", "/t/null"));
    say("rename: of . %ld, of .. %ld, onto . %ld, of / %ld, of /dev %ld, onto /dev %ld, into /dev %ld, out of /dev %ld\n", a, b, c, d, e,
        f, h, i);
    fa = open("/t", O_RDONLY | O_DIRECTORY);
    a = r(renameat(fa, "b", fa, "y"));
    b = r(syscall(SYS_renameat2, fa, "y", AT_FDCWD, "/t/z", 0));
    s1 = st("/t/b");
    say("rename: renameat by descriptors %ld, renameat2 with no flag %ld; b %s, z '%s'\n", a, b, s1, get("/t/z"));
    close(fa);
    unlink("/t/d3/moved/f");
    a = r(rmdir("/t/d3/moved")); b = r(rmdir("/t/d3")); c = r(rmdir("/t/d1")); d = r(unlink("/t/z"));
    say("rename: removed: %ld %ld %ld %ld\n", a, b, c, d);
}

/* ---- directories: sizes, link counts, a reading while it changes --------------- */
struct ent { uint64_t ino; int64_t off; unsigned short len; unsigned char type; char name[]; };
static int cmp(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
static int names(const char *dir, char out[][64], int max, size_t bufsize) {
    int fd = open(dir, O_RDONLY | O_DIRECTORY);
    char buf[4096];
    int n = 0;
    for (;;) {
        long got = syscall(SYS_getdents64, fd, buf, bufsize);
        if (got <= 0) break;
        for (long o = 0; o < got;) {
            struct ent *e = (struct ent *)(buf + o);
            if (n < max) snprintf(out[n++], 64, "%s%c", e->name, e->type == DT_DIR ? '/' : e->type == DT_REG ? ' ' : '?');
            o += e->len;
        }
    }
    close(fd);
    static char *p[1024];
    static char tmp[1024][64];
    for (int i = 0; i < n; i++) { memcpy(tmp[i], out[i], 64); p[i] = tmp[i]; }
    qsort(p, n, sizeof p[0], cmp);
    for (int i = 0; i < n; i++) memcpy(out[i], p[i], 64);
    return n;
}
static void directories(void) {
    static char nm[512][64];
    char list[512] = "";
    mkdir("/t/d", 0777);
    say("dir: empty %s; ", st("/t/d"));
    put("/t/d/one", "1");
    put("/t/d/two", "22");
    put("/t/d/three", "333");
    mkdir("/t/d/s1", 0777);
    mkdir("/t/d/s2", 0777);
    say("with three files and two directories %s; ", st("/t/d"));
    int n = names("/t/d", nm, 512, 4096);
    for (int i = 0; i < n; i++) { strcat(list, nm[i]); strcat(list, i + 1 < n ? "," : ""); }
    say("its names, sorted: %s\n", list);
    int fd = open("/t/d", O_RDONLY | O_DIRECTORY);
    char buf[512];
    long got = syscall(SYS_getdents64, fd, buf, sizeof buf);
    ino_t dot = 0, dotdot = 0;
    for (long o = 0; o < got;) {
        struct ent *e = (struct ent *)(buf + o);
        if (!strcmp(e->name, ".")) dot = e->ino;
        if (!strcmp(e->name, "..")) dotdot = e->ino;
        o += e->len;
    }
    lseek(fd, 0, SEEK_SET);
    long small = r(syscall(SYS_getdents64, fd, buf, 8));
    lseek(fd, 0, SEEK_SET);
    int again = syscall(SYS_getdents64, fd, buf, sizeof buf) == got;
    long rd = r(read(fd, buf, 8));
    say("dir: . is the directory's inode %d, .. its parent's %d; a buffer too small for one entry %ld; after lseek to 0 it reads again %d; read() on it %ld\n",
        dot == ino_of("/t/d"), dotdot == ino_of("/t"), small, again, rd);
    close(fd);
    unlink("/t/d/two");
    const char *s1 = st("/t/d");
    rmdir("/t/d/s2");
    say("dir: one file removed %s, one directory removed %s\n", s1, st("/t/d"));
    unlink("/t/d/one"); unlink("/t/d/three"); rmdir("/t/d/s1");
    /* a reading while the directory changes: 40 names, read a few at a
       time; between two readings some names are removed (ones already
       returned and ones not yet) and new ones made */
    char p[64];
    for (int i = 0; i < 40; i++) { snprintf(p, sizeof p, "/t/d/k%02d", i); put(p, "k"); }
    fd = open("/t/d", O_RDONLY | O_DIRECTORY);
    int seen[40] = { 0 }, gone[40] = { 0 }, seen_then[40] = { 0 }, rounds = 0;
    for (;;) {
        got = syscall(SYS_getdents64, fd, buf, 120);
        if (got <= 0) break;
        for (long o = 0; o < got;) {
            struct ent *e = (struct ent *)(buf + o);
            if (e->name[0] == 'k') {
                int i = atoi(e->name + 1);
                if (i >= 0 && i < 40) seen[i]++;
            }
            o += e->len;
        }
        if (++rounds == 3) {
            for (int i = 0; i < 40; i += 3) {
                snprintf(p, sizeof p, "/t/d/k%02d", i);
                seen_then[i] = seen[i];
                unlink(p);
                gone[i] = 1;
            }
            for (int i = 0; i < 10; i++) { snprintf(p, sizeof p, "/t/d/new%02d", i); put(p, "n"); }
        }
    }
    close(fd);
    int once = 1, twice = 0, late = 0;
    for (int i = 0; i < 40; i++) {
        if (!gone[i] && seen[i] != 1) once = 0;
        if (seen[i] > 1) twice++;
        if (gone[i] && seen[i] > seen_then[i]) late++;
    }
    say("dir: read while it changes: every name that stayed was returned exactly once %d, a name returned twice %d, a removed name returned after its removal %d\n",
        once, twice, late);
    n = names("/t/d", nm, 512, 256);
    int left = 0;
    for (int i = 0; i < n; i++) if (nm[i][0] == 'k' || nm[i][0] == 'n') left++;
    say("dir: then %d names, %s\n", left, st("/t/d"));
    for (int i = 0; i < 40; i++) { snprintf(p, sizeof p, "/t/d/k%02d", i); unlink(p); }
    for (int i = 0; i < 10; i++) { snprintf(p, sizeof p, "/t/d/new%02d", i); unlink(p); }
    s1 = st("/t/d");
    say("dir: emptied %s, removed %ld\n", s1, r(rmdir("/t/d")));
    /* a directory of many names (more than one page of them on PAX),
       and of long ones */
    static char many[1024][64];
    mkdir("/t/big", 0777);
    int made = 0;
    for (int i = 0; i < 600; i++) {
        snprintf(p, sizeof p, "/t/big/a-name-of-some-length-%04d", i);
        if (put(p, "m") == 1) made++;
    }
    n = names("/t/big", many, 1024, 4096);
    s1 = st("/t/big");
    int gone3 = 0;
    for (int i = 0; i < 600; i += 3) {
        snprintf(p, sizeof p, "/t/big/a-name-of-some-length-%04d", i);
        if (unlink(p) == 0) gone3++;
    }
    for (int i = 0; i < 100; i++) { snprintf(p, sizeof p, "/t/big/later-%03d", i); put(p, "l"); }
    int n2 = names("/t/big", many, 1024, 512);
    int dup = 0;
    for (int i = 1; i < n2; i++) if (!strcmp(many[i], many[i - 1])) dup++;
    say("dir: 600 names made %d, listed with . and .. %d, %s; a third removed %d and 100 more made: listed %d, the same name twice %d, %s\n",
        made, n, s1, gone3, n2, dup, st("/t/big"));
    snprintf(p, sizeof p, "/t/big/a-name-of-some-length-%04d", 599);
    const char *g599 = get(p);
    long miss = r(access("/t/big/a-name-of-some-length-0000", F_OK));
    static char longname[300];
    int longs = 0;
    for (int i = 0; i < 40; i++) {
        int o = snprintf(longname, sizeof longname, "/t/big/%02d-", i);
        memset(longname + o, 'L', 240);
        longname[o + 240] = 0;
        if (put(longname, "x") == 1) longs++;
    }
    int n3 = names("/t/big", many, 1024, 4096);
    say("dir: the last of the 600 still reads '%s', the first is gone %ld; 40 names of 250 bytes made %d: listed %d, %s\n", g599, miss,
        longs, n3, st("/t/big"));
    int fdb = open("/t/big", O_RDONLY | O_DIRECTORY);
    static char eb[4096];
    int removed = 0;
    for (;;) {
        got = syscall(SYS_getdents64, fdb, eb, sizeof eb);
        if (got <= 0) break;
        for (long o = 0; o < got;) {
            struct ent *e = (struct ent *)(eb + o);
            if (strcmp(e->name, ".") && strcmp(e->name, "..") && unlinkat(fdb, e->name, 0) == 0) removed++;
            o += e->len;
        }
    }
    close(fdb);
    s1 = st("/t/big");
    say("dir: every name removed while the directory is read: %d; %s; rmdir %ld\n", removed, s1, r(rmdir("/t/big")));
}

/* ---- names and the errnos -------------------------------------------------------- */
static void errnos(void) {
    static char big[5000];
    strcpy(big, "/t/");
    memset(big + 3, 'n', 255);
    big[258] = 0;
    int fd = open(big, O_WRONLY | O_CREAT, 0666);
    long ok255 = fd >= 0;
    close(fd);
    long un = r(unlink(big));
    memset(big + 3, 'n', 256);
    big[259] = 0;
    put("/t/a", "a");
    long a = r(open(big, O_WRONLY | O_CREAT, 0666)), b = r(mkdir(big, 0777));
    const char *s1 = st(big);
    long c = r(rename("/t/a", big));
    say("names: 255 bytes made %ld and removed %ld; 256 bytes: open %ld, mkdir %ld, stat %s, rename onto it %ld\n", ok255, un, a, b, s1, c);
    /* "/t" and "/." until the path is 4095 bytes (the longest: PATH_MAX
       counts the NUL), then one byte more */
    int o = sprintf(big, "/t/");
    while (o < 4095) o += sprintf(big + o, o + 2 <= 4095 ? "./" : ".");
    long l1 = strlen(big);
    a = r(access(big, F_OK));
    strcat(big, "/");
    long l2 = strlen(big);
    b = r(access(big, F_OK));
    say("names: a path of %ld bytes %ld, of %ld bytes %ld\n", l1, a, l2, b);
    mkdir("/t/d", 0777);
    put("/t/d/x", "x");
    a = r(open("/proc/self/exe", O_RDONLY | O_NOFOLLOW));
    b = r(rename("/t/a", "/dev/px27-probe"));
    c = r(rmdir("/t/d"));
    long d = r(mkdir("/t/d", 0777)), e = r(open("/t/d", O_WRONLY)), f = r(open("/t/a/b", O_RDONLY));
    long g = r(rename("/t/d", "/t/d/e")), h = r(rmdir("/"));
    say("errno: ELOOP: /proc/self/exe opened with O_NOFOLLOW %ld; EXDEV: a file renamed into /dev %ld; ENOTEMPTY %ld; EEXIST %ld; EISDIR %ld; ENOTDIR %ld; EINVAL %ld; EBUSY %ld\n",
        a, b, c, d, e, f, g, h);
    a = r(access("/t/a", R_OK | W_OK));
    b = r(access("/t/a", X_OK));
    c = r(access("/t/d", X_OK));
    d = r(access("/t/none", F_OK));
    e = r(access("/t/a", 8));
    f = r(faccessat(AT_FDCWD, "/t/a", R_OK, 0));
    g = r(syscall(SYS_faccessat, AT_FDCWD, "/t/a", X_OK));
    say("access: a 0644 file to read and write %ld, to execute %ld (root); a directory to execute %ld; a missing name %ld; a bad mode %ld; faccessat (glibc's, and the call itself) %ld %ld\n",
        a, b, c, d, e, f, g);
    pid_t k = fork();
    if (k == 0) {
        char *argv[] = { "/t/a", 0 };
        execve("/t/a", argv, argv + 1);
        _exit(errno);
    }
    int ws = 0;
    waitpid(k, &ws, 0);
    say("errno: EACCES: execve of a file with no execute bit %d; EBADF: write to a closed descriptor %ld\n", -WEXITSTATUS(ws),
        r(write(99, "x", 1)));
    unlink("/t/d/x"); rmdir("/t/d"); unlink("/t/a");
}

/* ---- paths: .., descriptors as directories, devices ------------------------------- */
static void paths(void) {
    struct stat a, b, c;
    mkdir("/t/p", 0777);
    put("/t/p/f", "pf");
    stat("/", &a);
    stat("/..", &b);
    stat("/t/p/../..", &c);
    long m = r(access("/t/none/../p/f", F_OK));
    long n = r(access("/t/p/f/..", F_OK));
    say("paths: /.. is / %d, /t/p/../.. is / %d; through a missing directory and back %ld; .. of a file %ld; a directory with a trailing slash %ld, with /. %ld\n",
        a.st_ino == b.st_ino && a.st_dev == b.st_dev, a.st_ino == c.st_ino, m, n, r(access("/t/p/", F_OK)), r(access("/t/p/.", F_OK)));
    stat("/t", &b);
    stat("/dev", &c);
    struct stat d;
    stat("/dev/null", &d);
    say("paths: / and /t are one file system %d and two files %d; /dev is another %d, /dev/null is on it %d\n", a.st_dev == b.st_dev,
        a.st_ino != b.st_ino, c.st_dev != a.st_dev, d.st_dev == c.st_dev);
    int dfd = open("/t/p", O_RDONLY | O_DIRECTORY);
    int fd = openat(dfd, "g", O_WRONLY | O_CREAT | O_EXCL, 0666);
    long w = r(write(fd, "pg", 2));
    close(fd);
    long mk = r(mkdirat(dfd, "sub", 0777));
    long ac = r(faccessat(dfd, "sub", F_OK, 0));
    long nd = r(openat(dfd, "f/x", O_RDONLY));
    fd = open("/t/p/f", O_RDONLY);
    long bad = r(openat(fd, "x", O_RDONLY));
    close(fd);
    const char *g = get("/t/p/g");
    say("paths: openat in a directory descriptor writes %ld ('%s'), mkdirat %ld, faccessat %ld; under a file %ld; with a file as the directory %ld\n",
        w, g, mk, ac, nd, bad);
    long fc = r(fchdir(dfd));
    char p[64];
    char *cw = getcwd(p, sizeof p);
    long un = r(unlinkat(dfd, "g", 0)), rm = r(unlinkat(dfd, "sub", AT_REMOVEDIR));
    say("paths: fchdir %ld, getcwd '%s'; unlinkat there %ld, with AT_REMOVEDIR %ld; an empty path %ld\n", fc, cw ? p : "?", un, rm,
        r(access("", F_OK)));
    chdir("/");
    close(dfd);
    /* one file, two descriptors: a truncation under a reader */
    put("/t/p/f", "0123456789");
    int rd = open("/t/p/f", O_RDONLY);
    char two[2];
    read(rd, two, 2);
    truncate("/t/p/f", 1);
    long after = r(read(rd, two, 2));
    long back = r(lseek(rd, -1, SEEK_END));
    say("paths: a reader at offset 2 of a file cut to 1 byte reads %ld; SEEK_END - 1 is %ld; lseek before the start %ld, whence 9 %ld\n",
        after, back, r(lseek(rd, -5, SEEK_SET)), r(lseek(rd, 0, 9)));
    close(rd);
    unlink("/t/p/f");
    rmdir("/t/p");
}

/* ---- a file of the initramfs: written, cut, renamed, removed; a program run ------ */
static void initram(const char *self) {
    char keep[64] = "";
    int fd = open("/etc/pax-run", O_RDWR);
    long n = r(read(fd, keep, sizeof keep - 1));
    const char *s0 = fst(fd);
    long w = r(pwrite(fd, "X", 1, 1));
    char now[64] = "";
    pread(fd, now, sizeof now - 1, 0);
    int same = n > 2 && now[0] == keep[0] && now[1] == 'X' && !strcmp(now + 2, keep + 2);
    say("initramfs: /etc/pax-run read %d, %s; one byte written in it %ld: the rest unchanged %d\n", n > 0, s0 + 12, w, same);
    long t = r(ftruncate(fd, 3));
    long g = r(ftruncate(fd, 9));
    memset(now, '?', sizeof now);
    long m = r(pread(fd, now, sizeof now, 0));
    int cutok = m == 9 && now[0] == keep[0] && now[1] == 'X' && now[2] == keep[2] && now[3] == 0 && now[8] == 0;
    say("initramfs: cut to 3 %ld and grown to 9 %ld: three bytes kept and six zeros %d\n", t, g, cutok);
    close(fd);
    long mv = r(rename("/etc/pax-run", "/etc/run2"));
    long un = r(unlink("/etc/run2"));
    fd = open("/etc/pax-run", O_WRONLY | O_CREAT | O_EXCL, 0644);
    write(fd, keep, strlen(keep));
    close(fd);
    say("initramfs: renamed %ld, removed %ld, made again with what it held '%.9s'\n", mv, un, get("/etc/pax-run"));
    /* the running program, renamed, still starts (its bytes are where
       they were); a copy of it is a new file */
    long r1 = r(rename(self, "/bin/renamed"));
    pid_t k = fork();
    if (k == 0) {
        char *argv[] = { "/bin/renamed", "noop", 0 };
        execve("/bin/renamed", argv, argv + 2);
        _exit(100 + errno);
    }
    int ws = 0;
    waitpid(k, &ws, 0);
    long r2 = r(rename("/bin/renamed", self));
    say("initramfs: the program renamed %ld, run by its new name: status %d; renamed back %ld\n", r1, WEXITSTATUS(ws), r2);
    int in = open(self, O_RDONLY);
    int out = open("/t/copy", O_WRONLY | O_CREAT, 0755);
    long total = 0, c;
    while ((c = copy_file_range(in, 0, out, 0, 1 << 30, 0)) > 0) total += c;
    struct stat a, b;
    fstat(in, &a);
    fstat(out, &b);
    close(in); close(out);
    say("initramfs: the program copied: every byte %d, %s\n", total == a.st_size && b.st_size == a.st_size, st("/t/copy") + 12 - 12);
    k = fork();
    if (k == 0) {
        char *argv[] = { "/t/copy", "noop", 0 };
        execve("/t/copy", argv, argv + 2);
        _exit(100 + errno);
    }
    ws = 0;
    waitpid(k, &ws, 0);
    say("~exec: a program copied since boot, run: status %d (7: it ran; 113: -EACCES)\n", WEXITSTATUS(ws));
    unlink("/t/copy");
}

/* ---- rename replaces at once: a reader never finds the name missing ------------- */
static void atomic(void) {
    put("/t/x", "0");
    int pp[2];
    pipe(pp);
    pid_t k = fork();
    if (k == 0) {
        struct stat s;
        int missing = 0, n = 0;
        char c;
        close(pp[1]);
        fcntl(pp[0], F_SETFL, O_NONBLOCK);
        while (read(pp[0], &c, 1) != 0) {
            if (stat("/t/x", &s) != 0) missing++;
            int fd = open("/t/x", O_RDONLY);
            if (fd < 0) missing++; else { if (read(fd, &c, 1) != 1) missing++; close(fd); }
            n++;
            if (n % 8 == 0) sched_yield();
        }
        _exit(missing ? 1 : n > 0 ? 0 : 2);
    }
    close(pp[0]);
    int bad = 0;
    for (int i = 0; i < 500; i++) {
        if (put("/t/x.new", "1") != 1) bad++;
        if (rename("/t/x.new", "/t/x") != 0) bad++;
        sched_yield();
    }
    close(pp[1]);
    int ws = 0;
    waitpid(k, &ws, 0);
    say("atomic: 500 renames over a name while another process opens it: the renames failed %d times, the reader's status %d (0: it never found the name missing or empty)\n",
        bad, WEXITSTATUS(ws));
    unlink("/t/x");
}

/* ---- times -------------------------------------------------------------------------- */
static void times(void) {
    struct stat a, b, d0, d1;
    long long t0 = wall();
    ms(30);
    put("/t/tm", "x");
    ms(30);
    long long t1 = wall();
    stat("/t/tm", &a);
    say("times: a new file's times lie between the clock before and after: mtime %d, ctime %d, atime %d; mtime is ctime %d\n",
        ns_of(a.st_mtim) >= t0 - 20000000 && ns_of(a.st_mtim) <= t1, ns_of(a.st_ctim) >= t0 - 20000000 && ns_of(a.st_ctim) <= t1,
        ns_of(a.st_atim) >= t0 - 20000000 && ns_of(a.st_atim) <= t1, ns_of(a.st_mtim) == ns_of(a.st_ctim));
    stat("/t", &d0);
    ms(30);
    int fd = open("/t/tm", O_WRONLY | O_APPEND);
    write(fd, "y", 1);
    close(fd);
    stat("/t/tm", &b);
    stat("/t", &d1);
    say("times: a write moves mtime %d and ctime %d, and leaves the directory's alone %d\n", ns_of(b.st_mtim) > ns_of(a.st_mtim),
        ns_of(b.st_ctim) > ns_of(a.st_ctim), ns_of(d1.st_mtim) == ns_of(d0.st_mtim));
    ms(30);
    get("/t/tm");
    stat("/t/tm", &a);
    ms(30);
    get("/t/tm");
    struct stat a2;
    stat("/t/tm", &a2);
    say("times: a read leaves mtime %d and ctime %d; it moves an atime that was not after them %d, and a second read does not move it again %d\n",
        ns_of(a.st_mtim) == ns_of(b.st_mtim), ns_of(a.st_ctim) == ns_of(b.st_ctim), ns_of(a.st_atim) > ns_of(b.st_atim),
        ns_of(a2.st_atim) == ns_of(a.st_atim));
    ms(30);
    rename("/t/tm", "/t/tn");
    stat("/t/tn", &b);
    stat("/t", &d0);
    say("times: a rename leaves the file's mtime %d, moves its ctime %d and the directory's mtime %d\n",
        ns_of(b.st_mtim) == ns_of(a.st_mtim), ns_of(b.st_ctim) > ns_of(a.st_ctim), ns_of(d0.st_mtim) > ns_of(d1.st_mtim));
    ms(30);
    truncate("/t/tn", 0);
    stat("/t/tn", &a);
    ms(30);
    unlink("/t/tn");
    stat("/t", &d1);
    say("times: a truncation moves mtime %d; an unlink moves the directory's mtime %d and ctime %d\n",
        ns_of(a.st_mtim) > ns_of(b.st_mtim), ns_of(d1.st_mtim) > ns_of(d0.st_mtim), ns_of(d1.st_ctim) > ns_of(d0.st_ctim));
}

/* ---- copies in the kernel --------------------------------------------------------- */
static void copies(void) {
    static char src[10000], back[10000];
    for (int i = 0; i < 10000; i++) src[i] = 'a' + i % 23;
    int in = open("/t/src", O_RDWR | O_CREAT, 0666);
    write(in, src, sizeof src);
    lseek(in, 0, SEEK_SET);
    int out = open("/t/dst", O_RDWR | O_CREAT, 0666);
    long n1 = r(copy_file_range(in, 0, out, 0, 1 << 30, 0));
    long n2 = r(copy_file_range(in, 0, out, 0, 1 << 30, 0));
    pread(out, back, sizeof back, 0);
    long a = r(lseek(in, 0, SEEK_CUR)), b = r(lseek(out, 0, SEEK_CUR));
    say("copy: copy_file_range of 10000 bytes %ld, then %ld; the same bytes %d; offsets %ld and %ld\n", n1, n2,
        memcmp(src, back, sizeof src) == 0, a, b);
    loff_t oi = 100, oo = 20000;
    long n3 = r(copy_file_range(in, &oi, out, &oo, 50, 0));
    pread(out, back, 50, 20000);
    int kept = lseek(in, 0, SEEK_CUR) == 10000 && lseek(out, 0, SEEK_CUR) == 10000;
    say("copy: with offsets %ld: they moved to %lld and %lld, the descriptors' did not %d, the bytes are the source's %d, %s\n", n3,
        (long long)oi, (long long)oo, kept, memcmp(back, src + 100, 50) == 0, fst(out) + 20);
    int ap = open("/t/dst", O_WRONLY | O_APPEND);
    int pp[2];
    pipe(pp);
    loff_t z = 0;
    a = r(copy_file_range(in, &z, ap, 0, 10, 0));
    b = r(copy_file_range(pp[0], 0, out, 0, 10, 0));
    oi = 0; oo = 5;
    long c = r(copy_file_range(in, &oi, in, &oo, 10, 0));
    oi = 0; oo = 9000;
    long d = r(copy_file_range(in, &oi, in, &oo, 10, 0));
    z = 0;
    long e = r(copy_file_range(in, &z, out, 0, 10, 1));
    int dfd = open("/t", O_RDONLY);
    long f = r(copy_file_range(dfd, 0, out, 0, 10, 0));
    close(dfd);
    say("copy: onto an O_APPEND descriptor %ld; from a pipe %ld; a file onto itself, overlapping %ld, apart %ld; with a flag %ld; from a directory %ld\n",
        a, b, c, d, e, f);
    off_t so = 0;
    lseek(out, 0, SEEK_SET);
    ftruncate(out, 0);
    long s1 = r(sendfile(out, in, &so, 1 << 20));
    const char *s2 = fst(out) + 20;
    so = 0;
    a = r(sendfile(ap, in, &so, 10));
    lseek(in, 0, SEEK_SET);
    b = r(splice(in, 0, out, 0, 10, 0));
    say("copy: sendfile file to file %ld, %s; onto an O_APPEND descriptor %ld; splice file to file %ld\n", s1, s2, a, b);
    close(in); close(out); close(ap); close(pp[0]); close(pp[1]);
    unlink("/t/src"); unlink("/t/dst");
}

/* ==== px36: the changes after a file is made ====================================== */

/* lstat's "mode 120777 links 1 size 1 blocks 0", or "-2" */
static const char *lst(const char *path) {
    static char b[4][96];
    static int k;
    struct stat s;
    char *o = b[k++ & 3];
    if (lstat(path, &s) != 0) snprintf(o, 96, "%d", -errno);
    else snprintf(o, 96, "mode %o links %lu size %lld blocks %lld", s.st_mode, (unsigned long)s.st_nlink,
                  (long long)s.st_size, (long long)s.st_blocks);
    return o;
}
/* readlink's answer: the bytes and the count, or "-E" */
static const char *rl(const char *path, size_t size) {
    static char b[4][128];
    static int k;
    char *o = b[k++ & 3];
    char t[100];
    ssize_t n = readlink(path, t, size < sizeof t ? size : sizeof t);
    if (n < 0) snprintf(o, 128, "%d", -errno);
    else snprintf(o, 128, "'%.*s' %ld", (int)n, t, (long)n);
    return o;
}
/* a program run: its exit status, or 100 + errno when execve failed */
static int run(const char *path) {
    pid_t k = fork();
    if (k == 0) {
        char *argv[] = { (char *)path, "noop", 0 };
        execve(path, argv, argv + 2);
        _exit(100 + errno);
    }
    int ws = 0;
    waitpid(k, &ws, 0);
    return WEXITSTATUS(ws);
}
static long long sec_of(struct timespec t) { return (long long)t.tv_sec; }
static int lies(long long t, long long lo, long long hi) { return t >= lo - 20000000 && t <= hi; }

/* ---- hard links ------------------------------------------------------------------ */
static void hardlinks(void) {
    struct stat a, b;
    mkdir("/t/h", 0777);
    put("/t/h/a", "abc");
    stat("/t/h/a", &a);
    ms(30);
    long l1 = r(link("/t/h/a", "/t/h/b"));
    stat("/t/h/b", &b);
    say("link: link a b %ld; a %s; b %s; one inode %d; its ctime moved %d, its mtime did not %d\n", l1, st("/t/h/a"), st("/t/h/b"),
        ino_of("/t/h/a") == ino_of("/t/h/b"), ns_of(b.st_ctim) > ns_of(a.st_ctim), ns_of(b.st_mtim) == ns_of(a.st_mtim));
    long l2 = r(link("/t/h/a", "/t/h/b"));
    long l3 = r(link("/t/h/nope", "/t/h/c"));
    long l4 = r(link("/t/h/a", "/t/h/no/c"));
    long l5 = r(link("/t/h/a", "/t/h/c/"));
    long l6 = r(link("/t/h/a/", "/t/h/c"));
    long l7 = r(link("/t/h/a/x", "/t/h/c"));
    long l8 = r(linkat(AT_FDCWD, "/t/h/a", AT_FDCWD, "/t/h/c", 0x8000));
    long l9 = r(link("/t/h/a", "/dev/px36"));
    long l10 = r(link("/dev/null", "/t/h/null"));
    say("link: again %ld; a missing name %ld; into a missing directory %ld; a new name with a trailing slash %ld, an old one %ld; through a file %ld; a flag %ld; into /dev %ld; out of /dev %ld\n",
        l2, l3, l4, l5, l6, l7, l8, l9, l10);
    int fd = open("/t/h/b", O_WRONLY | O_APPEND);
    write(fd, "def", 3);
    close(fd);
    say("link: written through b, read through a: %s; the directory %s\n", get("/t/h/a"), st("/t/h"));
    long u1 = r(unlink("/t/h/a"));
    say("link: unlink a %ld; b %s, %s; a %s\n", u1, st("/t/h/b"), get("/t/h/b"), st("/t/h/a"));
    char nm[64];
    int ok = 0;
    for (int i = 0; i < 100; i++) {
        snprintf(nm, sizeof nm, "/t/h/m%d", i);
        if (link("/t/h/b", nm) == 0) ok++;
    }
    say("link: 100 more names %d; b %s; the directory %s\n", ok, st("/t/h/b"), st("/t/h"));
    int o = open("/t/h/m7", O_RDONLY);
    for (int i = 0; i < 100; i++) {
        snprintf(nm, sizeof nm, "/t/h/m%d", i);
        unlink(nm);
    }
    long u2 = r(unlink("/t/h/b"));
    char back[16] = "";
    long rd = r(pread(o, back, sizeof back - 1, 0));
    say("link: every name removed while it is open %ld: %s; still reads %ld '%s'\n", u2, fst(o), rd, back);
    long e1 = r(linkat(o, "", AT_FDCWD, "/t/h/back", AT_EMPTY_PATH));
    close(o);
    put("/t/h/p", "p");
    int po = open("/t/h/p", O_RDONLY);
    long e2 = r(linkat(po, "", AT_FDCWD, "/t/h/p2", AT_EMPTY_PATH));
    close(po);
    say("link: AT_EMPTY_PATH of a file with no name %ld; of one with a name %ld, %s\n", e1, e2, st("/t/h/p2"));
    unlink("/t/h/p2");
    link("/t/h/p", "/t/h/q");
    long rn = r(rename("/t/h/p", "/t/h/q"));
    say("link: a rename of one name over another of the same file %ld; p %s; q %s\n", rn, st("/t/h/p"), st("/t/h/q"));
    long x1 = r(link("/bin/tree", "/t/h/tl"));
    int s1 = run("/t/h/tl");
    say("link: /bin/tree linked %ld, run by its second name: status %d; /bin/tree %s\n", x1, s1, st("/bin/tree") + 12);
    unlink("/t/h/tl");
    say("link: /bin/tree again %s\n", st("/bin/tree") + 12);
    unlink("/t/h/p");
    unlink("/t/h/q");
    say("link: gone: rmdir %ld\n", r(rmdir("/t/h")));
}

/* ---- symbolic links ------------------------------------------------------------- */
static void symlinks(void) {
    struct stat a;
    char nm[64];
    mkdir("/t/y", 0777);
    put("/t/y/f", "eff");
    long long t0 = wall();
    ms(30);
    long s1 = r(symlink("f", "/t/y/s"));
    ms(30);
    long long t1 = wall();
    lstat("/t/y/s", &a);
    say("symlink: s -> f %ld; lstat %s; stat %s; reads %s; its times lie between the clock before and after %d %d %d\n", s1, lst("/t/y/s"),
        st("/t/y/s"), get("/t/y/s"), lies(ns_of(a.st_mtim), t0, t1), lies(ns_of(a.st_ctim), t0, t1), lies(ns_of(a.st_atim), t0, t1));
    const char *k1 = rl("/t/y/s", 64);
    const char *k2 = rl("/t/y/s", 1);
    const char *k3 = rl("/t/y/f", 64);
    say("symlink: readlink s %s, with room for 1 %s; of f %s\n", k1, k2, k3);
    k1 = rl("/t/y/nope", 64);
    k2 = rl("/t/y/s/", 64);
    k3 = rl("/", 64);
    say("symlink: readlink of a missing name %s; of s/ %s; of / %s\n", k1, k2, k3);
    char t[8];
    long z = r(readlink("/t/y/s", t, 0));
    int dfd = open("/t/y", O_RDONLY | O_DIRECTORY);
    long sa = r(symlinkat("../y/f", dfd, "s2"));
    ssize_t n = readlinkat(dfd, "s2", nm, sizeof nm);
    say("symlink: readlink with no room %ld; symlinkat %ld; readlinkat %ld '%.*s'; reads %s\n", z, sa, (long)n, n > 0 ? (int)n : 0, nm,
        get("/t/y/s2"));
    long e1 = r(symlink("", "/t/y/e"));
    long e2 = r(symlink("x", "/t/y/f"));
    long e3 = r(symlink("x", "/t/y/s"));
    long e4 = r(symlink("x", "/t/y/no/e"));
    long e5 = r(symlink("x", "/t/y/f/e"));
    long e6 = r(symlink("x", "/t/y/e/"));
    say("symlink: an empty target %ld; over a file %ld; over a link %ld; in a missing directory %ld; under a file %ld; a name with a trailing slash %ld\n",
        e1, e2, e3, e4, e5, e6);
    static char longt[5000];
    memset(longt, 'z', sizeof longt);
    longt[4095] = 0;
    long g1 = r(symlink(longt, "/t/y/long"));
    const char *g1s = lst("/t/y/long");
    unlink("/t/y/long");
    longt[4095] = 'z';
    longt[4096] = 0;
    long g2 = r(symlink(longt, "/t/y/long"));
    say("symlink: a target of 4095 bytes %ld, %s; of 4096 %ld\n", g1, g1s, g2);
    /* what a link costs, by its target's length */
    int lens[] = { 1, 59, 60, 61, 127, 128, 129, 255, 256, 1000, 4095 };
    char costs[256] = "";
    for (unsigned i = 0; i < sizeof lens / sizeof lens[0]; i++) {
        memset(longt, 'q', lens[i]);
        longt[lens[i]] = 0;
        symlink(longt, "/t/y/cost");
        struct stat c;
        lstat("/t/y/cost", &c);
        unlink("/t/y/cost");
        snprintf(costs + strlen(costs), sizeof costs - strlen(costs), " %d:%lld", lens[i], (long long)c.st_blocks);
    }
    say("symlink: blocks by the target's length%s\n", costs);
    /* a link that leads nowhere */
    symlink("nowhere", "/t/y/d");
    int o1 = open("/t/y/d", O_RDONLY);
    long d1 = o1 < 0 ? -errno : 0;
    long d2 = r(access("/t/y/d", F_OK));
    int o3 = open("/t/y/d", O_WRONLY | O_CREAT | O_EXCL, 0644);
    long d3 = o3 < 0 ? -errno : 0;
    int o4 = open("/t/y/d", O_WRONLY | O_CREAT, 0644);
    long d4 = o4 < 0 ? -errno : 0;
    if (o4 >= 0) { write(o4, "made", 4); close(o4); }
    say("symlink: d -> nowhere: open %ld, access %ld, O_CREAT|O_EXCL %ld; O_CREAT %ld: nowhere %s '%s'; d %s\n", d1, d2, d3, d4,
        st("/t/y/nowhere"), get("/t/y/nowhere"), lst("/t/y/d"));
    int o5 = open("/t/y/s", O_RDONLY | O_NOFOLLOW);
    long d5 = o5 < 0 ? -errno : 0;
    int o6 = open("/t/y/f", O_RDONLY | O_NOFOLLOW);
    long d6 = o6 < 0 ? -errno : 0;
    if (o6 >= 0) close(o6);
    int o7 = open("/t/y/s", O_RDONLY | O_NOFOLLOW | O_DIRECTORY);
    long d7 = o7 < 0 ? -errno : 0;
    say("symlink: O_NOFOLLOW on a link %ld, on a file %ld, with O_DIRECTORY on a link %ld\n", d5, d6, d7);
    /* links to directories, relative and absolute; .. after one */
    mkdir("/t/y/sub", 0777);
    mkdir("/t/y/sub/in", 0777);
    put("/t/y/sub/in/x", "deep");
    symlink("sub", "/t/y/ds");
    symlink("sub/in", "/t/y/di");
    symlink("/t/y/sub/in/x", "/t/y/abs");
    symlink("../y/./sub//in/", "/t/y/odd");
    struct stat p, q;
    stat("/t/y/di/..", &p);
    stat("/t/y/sub", &q);
    say("symlink: through a link to a directory %s; an absolute one %s; one with dots and slashes %s; .. after one is the target's parent %d\n",
        get("/t/y/ds/in/x"), get("/t/y/abs"), get("/t/y/odd/x"), p.st_ino == q.st_ino);
    say("symlink: ds %s; ds/ %s (lstat); s/ %s; s/x %s\n", lst("/t/y/ds"), lst("/t/y/ds/"), st("/t/y/s/"), st("/t/y/s/x"));
    long mk = r(mkdir("/t/y/ds", 0777));
    long mk2 = r(mkdir("/t/y/d", 0777));
    long mk3 = r(mkdir("/t/y/ds/new", 0777));
    long rd1 = r(rmdir("/t/y/ds"));
    long rd2 = r(rmdir("/t/y/ds/new"));
    say("symlink: mkdir over a link to a directory %ld, over one that leads nowhere %ld, through one %ld; rmdir of the link %ld, through it %ld\n",
        mk, mk2, mk3, rd1, rd2);
    /* a trailing slash after a link: which calls follow it then */
    symlink("nowhere3", "/t/y/dd");
    long ts1 = r(mkdir("/t/y/dd/", 0777));
    const char *ts1s = lst("/t/y/nowhere3");
    symlink("sub/in", "/t/y/dj");
    long ts2 = r(rmdir("/t/y/dj/"));
    long ts3 = r(unlink("/t/y/dj/"));
    put("/t/y/tf", "t");
    long ts4 = r(rename("/t/y/tf", "/t/y/dj/"));
    long ts5 = r(rename("/t/y/dj/", "/t/y/dk"));
    say("symlink: with a trailing slash: mkdir through a link that leads nowhere %ld (%s); rmdir of a link to a directory %ld, unlink %ld; a file renamed onto one %ld, the link renamed %ld; dj %s, in %s\n",
        ts1, ts1s, ts2, ts3, ts4, ts5, lst("/t/y/dj") + 12, st("/t/y/sub/in") + 11);
    rmdir("/t/y/nowhere3");
    unlink("/t/y/dd");
    unlink("/t/y/dj");
    unlink("/t/y/dk");
    unlink("/t/y/tf");
    chdir("/t/y/di");
    char cw[64];
    char *c = getcwd(cw, sizeof cw);
    say("symlink: chdir through a link, getcwd '%s'; ../x %s\n", c ? cw : "?", get("../in/x"));
    chdir("/");
    /* how many links one path may follow */
    put("/t/y/c0", "end");
    for (int i = 1; i <= 41; i++) {
        char to[16];
        snprintf(to, sizeof to, "c%d", i - 1);
        snprintf(nm, sizeof nm, "/t/y/c%d", i);
        symlink(to, nm);
    }
    say("symlink: a chain: 39 links %s, 40 %s, 41 %s; lstat of the 41st %s\n", get("/t/y/c39"), get("/t/y/c40"), get("/t/y/c41"),
        lst("/t/y/c41") + 12);
    symlink("loop", "/t/y/loop");
    symlink("l2", "/t/y/l1");
    symlink("l1", "/t/y/l2");
    say("symlink: a link to itself %s, a loop of two %s, through it %s; stat %s; lstat %s\n", get("/t/y/loop"), get("/t/y/l1"),
        get("/t/y/l1/x"), st("/t/y/loop"), lst("/t/y/loop") + 12);
    /* the calls that do not follow a last link */
    long r1 = r(rename("/t/y/s", "/t/y/s3"));
    say("symlink: rename of a link %ld: s3 %s, f %s\n", r1, rl("/t/y/s3", 64), st("/t/y/f"));
    symlink("nowhere2", "/t/y/v");
    long r2 = r(rename("/t/y/v", "/t/y/s3"));
    say("symlink: rename over a link %ld: s3 %s, f %s\n", r2, rl("/t/y/s3", 64), get("/t/y/f"));
    long h1 = r(link("/t/y/s2", "/t/y/hs"));
    long h2 = r(linkat(AT_FDCWD, "/t/y/s2", AT_FDCWD, "/t/y/hf", AT_SYMLINK_FOLLOW));
    say("symlink: a hard link to a link %ld: %s, %s; with AT_SYMLINK_FOLLOW %ld: %s\n", h1, lst("/t/y/hs"), rl("/t/y/hs", 64), h2,
        lst("/t/y/hf"));
    long un = r(unlink("/t/y/s2"));
    say("symlink: unlink of one of them %ld: hs %s; f %s\n", un, lst("/t/y/hs") + 12, st("/t/y/f") + 12);
    long tr = r(truncate("/t/y/ds/in/x", 2));
    say("symlink: truncate through a link %ld: %s\n", tr, get("/t/y/sub/in/x"));
    /* a directory's entries: DT_LNK */
    int dd = open("/t/y", O_RDONLY | O_DIRECTORY);
    char db[4096];
    long nb = syscall(SYS_getdents64, dd, db, sizeof db);
    int lnk = 0, reg = 0, dir = 0;
    for (long off = 0; off < nb;) {
        unsigned short rlen = *(unsigned short *)(db + off + 16);
        unsigned char ty = *(unsigned char *)(db + off + 18);
        if (ty == DT_LNK) lnk++;
        else if (ty == DT_REG) reg++;
        else if (ty == DT_DIR) dir++;
        off += rlen;
    }
    close(dd);
    say("symlink: the directory %s: %d links, %d files, %d directories\n", st("/t/y"), lnk, reg, dir);
    /* gone */
    for (int i = 0; i <= 41; i++) {
        snprintf(nm, sizeof nm, "/t/y/c%d", i);
        unlink(nm);
    }
    const char *names[] = { "f", "s3", "e", "long", "d", "nowhere", "ds", "di", "abs", "odd", "loop", "l1", "l2", "hs", "hf" };
    for (unsigned i = 0; i < sizeof names / sizeof names[0]; i++) {
        snprintf(nm, sizeof nm, "/t/y/%s", names[i]);
        unlink(nm);
    }
    unlink("/t/y/sub/in/x");
    rmdir("/t/y/sub/in");
    rmdir("/t/y/sub");
    close(dfd);
    say("symlink: gone: rmdir %ld\n", r(rmdir("/t/y")));
}

/* ---- modes -------------------------------------------------------------------------- */
static void modes(void) {
    struct stat a, b;
    mkdir("/t/m", 0777);
    put("/t/m/f", "m");
    stat("/t/m/f", &a);
    ms(30);
    long c1 = r(chmod("/t/m/f", 0600));
    stat("/t/m/f", &b);
    say("mode: chmod 0600 %ld: %s; ctime moved %d, mtime did not %d\n", c1, st("/t/m/f"), ns_of(b.st_ctim) > ns_of(a.st_ctim),
        ns_of(b.st_mtim) == ns_of(a.st_mtim));
    long c2 = r(chmod("/t/m/f", 07777));
    const char *m2 = st("/t/m/f");
    long c3 = r(chmod("/t/m/f", 0170644));
    const char *m3 = st("/t/m/f");
    long c4 = r(chmod("/t/m/f", 0));
    const char *m4 = st("/t/m/f");
    int fd = open("/t/m/f", O_RDWR);
    long o4 = fd < 0 ? -errno : 0;
    if (fd >= 0) close(fd);
    say("mode: 07777 %ld %s; with type bits %ld %s; 0 %ld %s, and root still opens it to read and write %ld\n", c2, m2, c3, m3, c4, m4, o4);
    fd = open("/t/m/f", O_RDONLY);
    long c5 = r(fchmod(fd, 0640));
    const char *m5 = fst(fd);
    long c6 = r(fchmodat(AT_FDCWD, "/t/m/f", 0444, 0));
    const char *m6 = fst(fd);
    close(fd);
    int dfd = open("/t/m", O_RDONLY | O_DIRECTORY);
    long c7 = r(fchmodat(dfd, "f", 0664, 0));
    const char *m7 = st("/t/m/f");
    say("mode: fchmod %ld %s; fchmodat %ld %s; relative to a directory %ld %s\n", c5, m5, c6, m6, c7, m7);
    symlink("f", "/t/m/s");
    long c8 = r(chmod("/t/m/s", 0604));
    say("mode: chmod through a link %ld: f %s, s %s\n", c8, st("/t/m/f"), lst("/t/m/s"));
    long c9 = r(fchmodat(AT_FDCWD, "/t/m/s", 0600, AT_SYMLINK_NOFOLLOW));
    long c10 = r(fchmodat(AT_FDCWD, "/t/m/f", 0600, AT_SYMLINK_NOFOLLOW));
    say("mode: fchmodat with AT_SYMLINK_NOFOLLOW on a link %ld: s %s, f %s; on a file %ld: f %s\n", c9, lst("/t/m/s") + 12,
        st("/t/m/f") + 12, c10, st("/t/m/f") + 12);
    long c11 = r(chmod("/t/m/nope", 0600));
    long c12 = r(chmod("/t/m/f/x", 0600));
    long c13 = r(fchmod(99, 0600));
    long c14 = r(syscall(SYS_fchmodat, AT_FDCWD, "/t/m/f", 0600, 0x8000));
    long c15 = r(chmod("/t/m", 01700));
    say("mode: a missing name %ld; through a file %ld; a closed descriptor %ld; a fourth argument to fchmodat %ld (it has three); a directory %ld %s\n",
        c11, c12, c13, c14, c15, st("/t/m"));
    chmod("/t/m", 0755);
    /* set-id bits and a write by root */
    chmod("/t/m/f", 06755);
    fd = open("/t/m/f", O_WRONLY | O_APPEND);
    write(fd, "w", 1);
    close(fd);
    say("~mode: 06755 and a write by root: %s\n", st("/t/m/f"));
    /* the bits decide execve and access */
    long x0 = r(chmod("/bin/tree", 0644));
    int s0 = run("/bin/tree");
    long a0 = r(access("/bin/tree", X_OK));
    long x1 = r(chmod("/bin/tree", 0100));
    int s1 = run("/bin/tree");
    long a1 = r(access("/bin/tree", X_OK));
    long x2 = r(chmod("/bin/tree", 0755));
    int s2 = run("/bin/tree");
    say("mode: /bin/tree 0644 %ld: run %d, X_OK %ld; 0100 %ld: run %d, X_OK %ld; 0755 again %ld: run %d\n", x0, s0, a0, x1, s1, a1, x2, s2);
    unlink("/t/m/s");
    unlink("/t/m/f");
    close(dfd);
    say("mode: gone: rmdir %ld\n", r(rmdir("/t/m")));
}

/* ---- times, set ------------------------------------------------------------------------ */
static const char *tm(const char *path, int nofollow) {
    static char b[4][160];
    static int k;
    struct stat s;
    char *o = b[k++ & 3];
    if ((nofollow ? lstat(path, &s) : stat(path, &s)) != 0) snprintf(o, 160, "%d", -errno);
    else snprintf(o, 160, "atime %lld.%09ld mtime %lld.%09ld", sec_of(s.st_atim), s.st_atim.tv_nsec, sec_of(s.st_mtim), s.st_mtim.tv_nsec);
    return o;
}
static void stamps(void) {
    struct stat a, b;
    mkdir("/t/u", 0777);
    put("/t/u/f", "u");
    struct timespec ts[2] = { { 1, 123456789 }, { 2, 987654321 } };
    stat("/t/u/f", &a);
    ms(30);
    long long t0 = wall();
    long u1 = r(utimensat(AT_FDCWD, "/t/u/f", ts, 0));
    long long t1 = wall();
    stat("/t/u/f", &b);
    say("time: set to the nanosecond %ld: %s; ctime moved to now %d\n", u1, tm("/t/u/f", 0), lies(ns_of(b.st_ctim), t0, t1));
    struct timespec om[2] = { { 0, UTIME_OMIT }, { 0, UTIME_OMIT } };
    ms(30);
    stat("/t/u/f", &a);
    long u2 = r(utimensat(AT_FDCWD, "/t/u/f", om, 0));
    stat("/t/u/f", &b);
    say("time: both UTIME_OMIT %ld: %s; ctime moved %d\n", u2, tm("/t/u/f", 0), ns_of(b.st_ctim) != ns_of(a.st_ctim));
    struct timespec n1[2] = { { 5, UTIME_NOW }, { 3, 300 } };
    ms(30);
    t0 = wall();
    long u3 = r(utimensat(AT_FDCWD, "/t/u/f", n1, 0));
    t1 = wall();
    stat("/t/u/f", &b);
    say("time: atime UTIME_NOW, mtime 3.000000300 %ld: atime now %d, mtime %lld.%09ld\n", u3, lies(ns_of(b.st_atim), t0, t1),
        sec_of(b.st_mtim), b.st_mtim.tv_nsec);
    ms(30);
    t0 = wall();
    long u4 = r(utimensat(AT_FDCWD, "/t/u/f", 0, 0));
    t1 = wall();
    stat("/t/u/f", &b);
    say("time: no times %ld: atime now %d, mtime now %d, ctime now %d\n", u4, lies(ns_of(b.st_atim), t0, t1), lies(ns_of(b.st_mtim), t0, t1),
        lies(ns_of(b.st_ctim), t0, t1));
    struct timespec bad1[2] = { { 1, 1000000000 }, { 1, 0 } };
    struct timespec bad2[2] = { { 1, 0 }, { 1, -1 } };
    long b1 = r(utimensat(AT_FDCWD, "/t/u/f", bad1, 0));
    long b2 = r(utimensat(AT_FDCWD, "/t/u/f", bad2, 0));
    long b3 = r(utimensat(AT_FDCWD, "/t/u/f", ts, 0x8000));
    long b4 = r(utimensat(AT_FDCWD, "/t/u/nope", ts, 0));
    long b5 = r(utimensat(AT_FDCWD, "/t/u/f/x", ts, 0));
    say("time: a nanosecond of 10^9 %ld, of -1 %ld; a flag %ld; a missing name %ld; through a file %ld\n", b1, b2, b3, b4, b5);
    struct timespec old[2] = { { -2208988800LL, 5 }, { -1, 999999999 } };
    long p1 = r(utimensat(AT_FDCWD, "/t/u/f", old, 0));
    say("time: before 1970 %ld: %s\n", p1, tm("/t/u/f", 0));
    struct timespec far[2] = { { 32503680000LL, 1 }, { 4102444800LL, 2 } };
    long p2 = r(utimensat(AT_FDCWD, "/t/u/f", far, 0));
    stat("/t/u/f", &b);
    say("time: 2100 %ld: mtime %lld.%09ld\n", p2, sec_of(b.st_mtim), b.st_mtim.tv_nsec);
    say("~time: the year 3000 as atime: %s\n", tm("/t/u/f", 0));
    int fd = open("/t/u/f", O_RDONLY);
    long p3 = r(futimens(fd, ts));
    say("time: futimens %ld: %s\n", p3, tm("/t/u/f", 0));
    close(fd);
    symlink("f", "/t/u/s");
    struct timespec lt[2] = { { 100, 1 }, { 200, 2 } };
    long q1 = r(utimensat(AT_FDCWD, "/t/u/s", lt, AT_SYMLINK_NOFOLLOW));
    say("time: a link's own %ld: s %s; f %s\n", q1, tm("/t/u/s", 1), tm("/t/u/f", 0));
    struct timespec tt[2] = { { 300, 3 }, { 400, 4 } };
    ms(30);
    t0 = wall();
    long q2 = r(utimensat(AT_FDCWD, "/t/u/s", tt, 0));
    t1 = wall();
    lstat("/t/u/s", &b);
    say("time: through the link %ld: f %s; s's mtime %lld.%09ld, its atime moved to now by the walk through it %d\n", q2, tm("/t/u/f", 0),
        sec_of(b.st_mtim), b.st_mtim.tv_nsec, lies(ns_of(b.st_atim), t0, t1));
    ms(30);
    t0 = wall();
    char lb[8];
    readlink("/t/u/s", lb, sizeof lb);
    t1 = wall();
    lstat("/t/u/s", &a);
    say("time: a readlink after it moves the link's atime %d\n", ns_of(a.st_atim) != ns_of(b.st_atim) && lies(ns_of(a.st_atim), t0, t1));
    utimensat(AT_FDCWD, "/t/u/s", lt, AT_SYMLINK_NOFOLLOW);
    ms(30);
    t0 = wall();
    readlink("/t/u/s", lb, sizeof lb);
    t1 = wall();
    lstat("/t/u/s", &a);
    say("time: a readlink of a link whose atime is before its mtime moves it to now %d\n", lies(ns_of(a.st_atim), t0, t1));
    long q3 = r(utimensat(AT_FDCWD, "/t/u", ts, 0));
    say("time: a directory %ld: %s\n", q3, tm("/t/u", 0));
    /* a read moves atime by relatime's rule from a time that was set */
    struct timespec rt[2] = { { 1000, 0 }, { 2000, 0 } };
    utimensat(AT_FDCWD, "/t/u/f", rt, 0);
    get("/t/u/f");
    stat("/t/u/f", &b);
    say("time: an atime before mtime, then a read: atime moved %d\n", sec_of(b.st_atim) > 2000);
    unlink("/t/u/s");
    unlink("/t/u/f");
    say("time: gone: rmdir %ld\n", r(rmdir("/t/u")));
}

/* ---- owners (every process here is root; px42's user/elf/own.c asks as a user) ----------------------------------------------- */
static void owners(void) {
    struct stat a, b;
    mkdir("/t/o", 0777);
    put("/t/o/f", "o");
    stat("/t/o/f", &a);
    ms(30);
    long w1 = r(chown("/t/o/f", 0, 0));
    stat("/t/o/f", &b);
    say("owner: chown 0 0 %ld: uid %d gid %d; ctime moved %d\n", w1, (int)b.st_uid, (int)b.st_gid, ns_of(b.st_ctim) > ns_of(a.st_ctim));
    ms(30);
    long w2 = r(chown("/t/o/f", -1, -1));
    stat("/t/o/f", &a);
    say("owner: chown -1 -1 %ld: ctime moved %d\n", w2, ns_of(a.st_ctim) > ns_of(b.st_ctim));
    chmod("/t/o/f", 06755);
    long w3 = r(chown("/t/o/f", 0, 0));
    const char *m3 = st("/t/o/f");
    chmod("/t/o/f", 06755);
    long w4 = r(chown("/t/o/f", -1, -1));
    const char *m4 = st("/t/o/f");
    chmod("/t/o/f", 06745);
    long w5 = r(chown("/t/o/f", 0, -1));
    const char *m5 = st("/t/o/f");
    chmod("/t/o/f", 06644);
    long w6 = r(chown("/t/o/f", -1, 0));
    const char *m6 = st("/t/o/f");
    say("owner: 06755 and chown 0 0 %ld: %s; 06755 and -1 -1 %ld: %s; 06745 and 0 -1 %ld: %s; 06644 and -1 0 %ld: %s\n", w3, m3, w4, m4, w5,
        m5, w6, m6);
    chmod("/t/o", 02755);
    long w7 = r(chown("/t/o", 0, 0));
    say("owner: a directory 02755 and chown 0 0 %ld: %s\n", w7, st("/t/o"));
    chmod("/t/o", 0755);
    int fd = open("/t/o/f", O_RDONLY);
    long w8 = r(fchown(fd, 0, 0));
    close(fd);
    symlink("f", "/t/o/s");
    long w9 = r(lchown("/t/o/s", 0, 0));
    long w10 = r(fchownat(AT_FDCWD, "/t/o/s", 0, 0, AT_SYMLINK_NOFOLLOW));
    long w11 = r(fchownat(AT_FDCWD, "/t/o/f", 0, 0, 0x8000));
    long w12 = r(chown("/t/o/nope", 0, 0));
    long w13 = r(fchown(99, 0, 0));
    say("owner: fchown %ld; lchown %ld; fchownat with AT_SYMLINK_NOFOLLOW %ld; a flag %ld; a missing name %ld; a closed descriptor %ld\n", w8,
        w9, w10, w11, w12, w13);
    long w14 = r(chown("/t/o/f", 1000, 1000));
    stat("/t/o/f", &a);
    say("owner: chown 1000 1000 %ld: uid %d\n", w14, (int)a.st_uid); /* px42: PAX keeps any id */
    chown("/t/o/f", 0, 0);
    unlink("/t/o/s");
    unlink("/t/o/f");
    say("owner: gone: rmdir %ld\n", r(rmdir("/t/o")));
}

/* ---- what PAX keeps fixed and Linux changes (not compared) ------------------------------- */
static void fixed(void) {
    /* /dev itself, never a device: on Linux it is the container's own */
    struct stat d;
    stat("/dev", &d);
    long a = r(chmod("/dev", d.st_mode & 07777));
    long b = r(utimensat(AT_FDCWD, "/dev", 0, 0));
    long c = r(symlink("null", "/dev/px36-link"));
    if (c == 0) unlink("/dev/px36-link");
    say("~fixed: chmod of /dev %ld, its times %ld, a symbolic link made in /dev %ld\n", a, b, c);
}

/* ---- what PAX refuses by name and Linux does (not compared) ------------------------ */
static void refused(void) {
    put("/t/a", "a");
    long a = r(link("/t/a", "/t/l")), b = r(symlink("a", "/t/s")), c = r(chmod("/t/a", 0600)), d = r(chown("/t/a", 0, 0));
    long e = r(utimensat(AT_FDCWD, "/t/a", 0, 0));
    int f1 = open("/t/a", O_RDONLY | O_SYNC);
    long f = f1 < 0 ? -errno : 0;
    if (f1 >= 0) close(f1);
    int g1 = open("/t", O_TMPFILE | O_RDWR, 0600);
    long g = g1 < 0 ? -errno : 0;
    if (g1 >= 0) close(g1);
    long h = r(syscall(SYS_renameat2, AT_FDCWD, "/t/a", AT_FDCWD, "/t/b", 1));
    say("~refused: link %ld, symlink %ld, chmod %ld, chown %ld, utimensat %ld, O_SYNC %ld, O_TMPFILE %ld, RENAME_NOREPLACE %ld\n", a, b,
        c, d, e, f, g, h);
    unlink("/t/l"); unlink("/t/s"); unlink("/t/b");
    /* PAX's /dev is fixed; its largest file is 1 GiB */
    int dv = open("/dev/px27-probe", O_WRONLY | O_CREAT | O_EXCL, 0600);
    long mk = dv < 0 ? -errno : 0;
    if (dv >= 0) { close(dv); unlink("/dev/px27-probe"); }
    long md = r(mkdir("/dev/px27-probe.d", 0700));
    if (md == 0) rmdir("/dev/px27-probe.d");
    put("/t/a", "a");
    int big = open("/t/a", O_WRONLY);
    long far = r(pwrite(big, "x", 1, (off_t)1 << 30));
    long grow = r(ftruncate(big, (off_t)1 << 31));
    close(big);
    say("~limits: a file made in /dev %ld, a directory %ld; a byte written at 1 GiB %ld, a file grown to 2 GiB %ld\n", mk, md, far, grow);
    unlink("/t/a");
    mkdir("/t/d", 0777);
    a = r(link("/t/d", "/t/dl"));
    rmdir("/t/d");
    say("errno: EPERM: a hard link to a directory %ld\n", a);
}

/* ---- the soak and the fill --------------------------------------------------------- */
static char mb[1 << 20];
/* 1 MiB files /t/s/fillN until one cannot be written whole: how many
   were made, how many bytes the last one took, and the errno that
   stopped it */
static long fill(int *files, long *last) {
    char a[64];
    long err = 0;
    int n = 0;
    memset(mb, 'm', sizeof mb);
    for (; n < 4096 && err == 0; n++) {
        snprintf(a, sizeof a, "/t/s/fill%d", n);
        int fd = open(a, O_WRONLY | O_CREAT, 0666);
        if (fd < 0) { err = -errno; break; }
        long w = write(fd, mb, sizeof mb);
        if (w < 0) err = -errno;
        else if (w < (long)sizeof mb) { *last = w; err = r(write(fd, mb, sizeof mb)); }
        close(fd);
    }
    *files = n;
    return err;
}
static void empty(int files) {
    char a[64];
    for (int i = 0; i < files; i++) { snprintf(a, sizeof a, "/t/s/fill%d", i); unlink(a); }
}
static int soak(void) {
    static char block[8192], back[8192];
    char a[64], b[64], h[64], l[64];
    int bad = 0;
    for (int i = 0; i < 8192; i++) block[i] = 'A' + i % 26;
    mkdir("/t", 0777);
    mkdir("/t/s", 0777);
    char *brk0 = sbrk(0);
    for (int i = 0; i < 10000; i++) {
        snprintf(a, sizeof a, "/t/s/f%d", i % 7);
        snprintf(b, sizeof b, "/t/s/g%d", i % 5);
        int fd = open(a, O_WRONLY | O_CREAT | O_EXCL, 0666);
        if (fd < 0) { bad++; continue; }
        if (write(fd, block, sizeof block) != (ssize_t)sizeof block) bad++;
        close(fd);
        if (rename(a, b) != 0) bad++;
        if (i % 100 == 0) {
            fd = open(b, O_RDONLY);
            if (read(fd, back, sizeof back) != (ssize_t)sizeof back || memcmp(block, back, sizeof block)) bad++;
            close(fd);
        }
        if (mkdir("/t/s/d", 0777) != 0 || rmdir("/t/s/d") != 0) bad++;
        /* px36: a second name, a symbolic link, a mode and the times;
           then the link renamed over the first name and that over the
           second, so one unlink a round removes the last name */
        snprintf(h, sizeof h, "/t/s/h%d", i % 3);
        snprintf(l, sizeof l, "/t/s/l%d", i % 4);
        if (link(b, h) != 0 || symlink(b, l) != 0) bad++;
        if (chmod(b, 0600) != 0 || utimensat(AT_FDCWD, l, 0, 0) != 0) bad++;
        if (rename(l, b) != 0 || rename(b, h) != 0) bad++;
        if (unlink(h) != 0) bad++;
    }
    say("soak: 10000 rounds of create, write 8192 bytes, rename, mkdir, rmdir, link, symlink, chmod, utimensat, two renames over names, unlink: %d errors; /t/s: %s; the program's break moved %ld bytes\n",
        bad, st("/t/s"), (long)((char *)sbrk(0) - brk0));
    /* the fill: 1 MiB files until ENOSPC, then back */
    int files = 0;
    long last = 0;
    long err = fill(&files, &last);
    say("~fill: %d files of 1 MiB, the last one took %ld bytes\n", files, last);
    int fd = open("/t/s/after", O_WRONLY | O_CREAT, 0666);
    long full = fd >= 0 ? r(write(fd, mb, 8192)) : -errno;
    if (fd >= 0) close(fd);
    unlink("/t/s/fill0");
    fd = open("/t/s/after", O_WRONLY | O_CREAT, 0666);
    long room = r(write(fd, mb, 8192));
    close(fd);
    say("fill: stopped by %ld; 8192 more bytes then %ld; after one file is removed %ld\n", err, full, room);
    empty(files);
    unlink("/t/s/after");
    fd = open("/t/s/again", O_WRONLY | O_CREAT, 0666);
    long again = r(write(fd, mb, sizeof mb));
    close(fd);
    long u = r(unlink("/t/s/again"));
    say("fill: everything removed; a megabyte written again %ld, removed %ld\n", again, u);
    /* again with 120 MiB of the program's own memory held: on PAX the
       machine reaches the frames the tree never takes before the tree
       reaches its cap */
    size_t big = (size_t)120 << 20;
    char *held = mmap(0, big, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int got = held != MAP_FAILED;
    for (size_t o = 0; got && o < big; o += 4096) held[o] = 1;
    files = 0;
    last = 0;
    err = fill(&files, &last);
    say("~fill: with 120 MiB held: %d files of 1 MiB, the last one took %ld bytes\n", files, last);
    char *one = mmap(0, 65536, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int own = one != MAP_FAILED;
    for (size_t o = 0; own && o < 65536; o += 4096) one[o] = 1;
    say("fill: with 120 MiB of the program's own memory held %d: stopped by %ld; 64 KiB more of its own memory after that %d\n", got, err,
        own);
    if (own) munmap(one, 65536);
    if (got) munmap(held, big);
    empty(files);
    long d1 = r(rmdir("/t/s")), d2 = r(rmdir("/t"));
    say("fill: everything removed again: %ld %ld\n", d1, d2);
    return bad != 0;
}

static int speed(void) {
    memset(mb, 's', sizeof mb);
    mkdir("/t", 0777);
    int fd = open("/t/big", O_RDWR | O_CREAT, 0666);
    long t0 = mono_ms();
    long w = 0, g = 0, w8 = 0, g8 = 0;
    for (int i = 0; i < 16; i++) w += write(fd, mb, sizeof mb);
    long t1 = mono_ms();
    lseek(fd, 0, SEEK_SET);
    for (int i = 0; i < 16; i++) g += read(fd, mb, sizeof mb);
    long t2 = mono_ms();
    /* 64 more passes over the same 16 MiB (its frames are there now):
       1 GiB each way, long enough for a clock that steps 10 ms */
    for (int p = 0; p < 64; p++) {
        lseek(fd, 0, SEEK_SET);
        for (int i = 0; i < 16; i++) w8 += write(fd, mb, sizeof mb);
    }
    long t3 = mono_ms();
    for (int p = 0; p < 64; p++) {
        lseek(fd, 0, SEEK_SET);
        for (int i = 0; i < 16; i++) g8 += read(fd, mb, sizeof mb);
    }
    long t4 = mono_ms();
    say("speed: 16 MiB written %ld, read back %ld, %s; 64 more passes: written %ld, read %ld\n", w, g, fst(fd) + 20, w8, g8);
    say("~speed: 16 MiB first written in %ld ms, read in %ld ms; 1 GiB rewritten in %ld ms, read in %ld ms\n", t1 - t0, t2 - t1,
        t3 - t2, t4 - t3);
    close(fd);
    long u = r(unlink("/t/big")), d = r(rmdir("/t"));
    say("speed: removed %ld %ld\n", u, d);
    return 0;
}

int main(int argc, char **argv) {
    if (argc > 1 && !strcmp(argv[1], "soak")) return soak();
    if (argc > 1 && !strcmp(argv[1], "speed")) return speed();
    if (argc > 1 && !strcmp(argv[1], "noop")) return 7;
    making();
    appending();
    holes();
    unlinked();
    workdir();
    renaming();
    directories();
    errnos();
    paths();
    initram("/bin/tree");
    atomic();
    times();
    copies();
    hardlinks();
    symlinks();
    modes();
    stamps();
    owners();
    fixed();
    refused();
    say("end: rmdir /t %ld; / still has it %s\n", r(rmdir("/t")), st("/t"));
    return 0;
}
