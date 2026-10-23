/* disk.c — px63's probe of a file system on a disk: one static glibc
   program run unmodified on Linux (the ext2 image on a virtio disk of a
   Linux guest under QEMU, mounted by the ext4 driver: tools/linux-blk)
   and on PAX (the same image mounted by kernel/fstab), the two outputs
   compared byte for byte (tests/mpx6-ext2).

     disk read DIR      every name under DIR, walked by getdents64 and
                        sorted: its type, lstat's fields (st_dev's major
                        and minor, st_ino, the mode, the links, the
                        owner, the size, st_blocks, st_blksize, the three
                        times to the nanosecond), a link's target, and a
                        regular file's bytes as their FNV-1a 64 and their
                        count; then statfs of DIR
     disk sum FILE...   each file's size and FNV-1a 64, read 64 KiB at a
                        time (the host computes the same sum of the bytes
                        it put there)
     disk write DIR     the write session's system calls, in DIR (which
                        it makes): files made, written (pwrite past the
                        end, a hole), grown through the single and into
                        the double indirect range, cut and grown again;
                        fsync, fdatasync, syncfs; directories made, moved
                        and removed; names renamed over others; hard and
                        symbolic links; chmod, chown, utimensat to fixed
                        times; a file unlinked while open and read after;
                        every errno the calls name (EEXIST, ENOENT,
                        ENOTEMPTY, EISDIR, ENOTDIR, EXDEV between DIR and
                        the root, ENAMETOOLONG); statfs before and after

   No inode number, block number or free count is printed by `write`
   (each kernel allocates its own); `read` prints inode numbers, since it
   reads an image both sides read unchanged, mounted read-only. Built
   with the host's cc: `cc -static -O1` (tools/mkdiskprobe). Nothing here
   reads a kernel's, a libc's or a file system's source: the calls are
   the man pages', the structures the public headers'. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

static void say(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
#include <stdarg.h>
static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    fflush(stdout);
}

static long rc(long r) { return r < 0 ? -errno : r; }

static uint64_t fnv(const unsigned char *p, size_t n, uint64_t h) {
    for (size_t i = 0; i < n; i++) {
        h ^= p[i];
        h *= 0x100000001b3ULL;
    }
    return h;
}

static unsigned char buf[65536];

/* A file's bytes: (count, FNV-1a 64), or -errno in the count. */
static long sum(const char *path, uint64_t *h) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -errno;
    long total = 0;
    *h = 0xcbf29ce484222325ULL;
    for (;;) {
        ssize_t n = read(fd, buf, sizeof buf);
        if (n < 0) { long e = -errno; close(fd); return e; }
        if (n == 0) break;
        *h = fnv(buf, (size_t)n, *h);
        total += n;
    }
    close(fd);
    return total;
}

static const char *tname(unsigned char t) {
    switch (t) {
    case DT_REG: return "reg";
    case DT_DIR: return "dir";
    case DT_LNK: return "lnk";
    case DT_FIFO: return "fifo";
    case DT_SOCK: return "sock";
    case DT_CHR: return "chr";
    case DT_BLK: return "blk";
    default: return "unknown";
    }
}

/* Every name under DIR, depth first, each directory's names sorted. The
   names are kept on the heap: PAX gives a process 128 KiB of stack
   (kernel/process's ELF_STACK_PAGES), Linux 8 MiB. */
struct ent { char *name; unsigned char type; };
static int cmpent(const void *a, const void *b) { return strcmp(((const struct ent *)a)->name, ((const struct ent *)b)->name); }

static void walk(const char *dir) {
    int fd = open(dir, O_RDONLY | O_DIRECTORY);
    if (fd < 0) { say("%s: open %d\n", dir, -errno); return; }
    int cap = 64, n = 0;
    struct ent *e = malloc(sizeof *e * (size_t)cap);
    static char dbuf[8192];
    for (;;) {
        long k = syscall(SYS_getdents64, fd, dbuf, sizeof dbuf);
        if (k < 0) { say("%s: getdents64 %d\n", dir, -errno); break; }
        if (k == 0) break;
        for (long o = 0; o < k;) {
            struct { uint64_t ino; int64_t off; unsigned short reclen; unsigned char type; char name[]; } *d = (void *)(dbuf + o);
            if (strcmp(d->name, ".") && strcmp(d->name, "..")) {
                if (n == cap) { cap *= 2; e = realloc(e, sizeof *e * (size_t)cap); }
                e[n].name = strdup(d->name);
                e[n].type = d->type;
                n++;
            }
            o += d->reclen;
        }
    }
    close(fd);
    qsort(e, (size_t)n, sizeof *e, cmpent);
    char *p = malloc(4096), *tgt = malloc(4096);
    for (int i = 0; i < n; i++) {
        snprintf(p, 4096, "%s/%s", dir, e[i].name);
        struct stat st;
        if (lstat(p, &st) < 0) { say("%s: lstat %d\n", p, -errno); continue; }
        say("%s %s dev %u:%u ino %lu mode %06o links %lu owner %u:%u size %ld blocks %ld blksize %ld atime %ld.%09ld mtime %ld.%09ld ctime %ld.%09ld",
            p, tname(e[i].type), major(st.st_dev), minor(st.st_dev), (unsigned long)st.st_ino, st.st_mode, (unsigned long)st.st_nlink,
            st.st_uid, st.st_gid, (long)st.st_size, (long)st.st_blocks, (long)st.st_blksize,
            (long)st.st_atim.tv_sec, st.st_atim.tv_nsec, (long)st.st_mtim.tv_sec, st.st_mtim.tv_nsec,
            (long)st.st_ctim.tv_sec, st.st_ctim.tv_nsec);
        if (S_ISLNK(st.st_mode)) {
            ssize_t k = readlink(p, tgt, 4095);
            if (k < 0) say(" readlink %d\n", -errno);
            else { tgt[k] = 0; say(" -> %s\n", tgt); }
        } else if (S_ISREG(st.st_mode)) {
            uint64_t h;
            long k = sum(p, &h);
            say(" bytes %ld fnv %016llx\n", k, (unsigned long long)h);
        } else say("\n");
        if (S_ISDIR(st.st_mode)) {
            char *sub = strdup(p);
            walk(sub);
            free(sub);
        }
    }
    free(p);
    free(tgt);
    for (int i = 0; i < n; i++) free(e[i].name);
    free(e);
}

static void fs(const char *dir) {
    struct statfs f;
    if (statfs(dir, &f) < 0) { say("statfs %s %d\n", dir, -errno); return; }
    say("statfs %s: type %lx bsize %ld blocks %lu bfree %lu bavail %lu files %lu ffree %lu fsid %08x:%08x namelen %ld frsize %ld flags %lx\n",
        dir, (long)f.f_type, (long)f.f_bsize, (unsigned long)f.f_blocks, (unsigned long)f.f_bfree, (unsigned long)f.f_bavail,
        (unsigned long)f.f_files, (unsigned long)f.f_ffree, (unsigned)f.f_fsid.__val[0], (unsigned)f.f_fsid.__val[1],
        (long)f.f_namelen, (long)f.f_frsize, (long)f.f_flags);
}

/* The write session's helpers: each prints its call and its answer. */
static char D[1024];
static const char *at(const char *name) {
    static char p[4][2048];
    static int k;
    k = (k + 1) % 4;
    snprintf(p[k], sizeof p[k], "%s/%s", D, name);
    return p[k];
}

static long writeall(const char *name, int flags, const void *b, size_t n) {
    int fd = open(at(name), O_WRONLY | O_CREAT | flags, 0644);
    if (fd < 0) return -errno;
    long w = rc(write(fd, b, n));
    close(fd);
    return w;
}

static void show(const char *name) {
    struct stat st;
    if (lstat(at(name), &st) < 0) { say("  %s: lstat %d\n", name, -errno); return; }
    say("  %s: mode %06o links %lu owner %u:%u size %ld blocks %ld", name, st.st_mode, (unsigned long)st.st_nlink,
        st.st_uid, st.st_gid, (long)st.st_size, (long)st.st_blocks);
    if (S_ISREG(st.st_mode)) {
        uint64_t h;
        long k = sum(at(name), &h);
        say(" bytes %ld fnv %016llx", k, (unsigned long long)h);
    }
    say("\n");
}

static void fixed_times(const char *name, long at_s, long mt_s) {
    struct timespec ts[2] = { { at_s, 250000000 }, { mt_s, 500000000 } };
    long r = rc(utimensat(AT_FDCWD, at(name), ts, AT_SYMLINK_NOFOLLOW));
    struct stat st;
    lstat(at(name), &st);
    say("utimensat %s: %ld; atime %ld.%09ld mtime %ld.%09ld\n", name, r, (long)st.st_atim.tv_sec, st.st_atim.tv_nsec,
        (long)st.st_mtim.tv_sec, st.st_mtim.tv_nsec);
}

static void session(const char *dir) {
    snprintf(D, sizeof D, "%s", dir);
    say("mkdir %s: %ld\n", dir, rc(mkdir(dir, 0755)));
    struct statfs f0;
    statfs(dir, &f0);
    /* files made, written, read back */
    say("write a: %ld\n", writeall("a", O_TRUNC, "hello, disk\n", 12));
    say("write a again O_EXCL: %ld\n", writeall("a", O_EXCL, "x", 1));
    say("append a: %ld\n", writeall("a", O_APPEND, "and more\n", 9));
    show("a");
    /* a hole: pwrite past the end */
    int fd = open(at("sparse"), O_RDWR | O_CREAT, 0600);
    say("pwrite sparse at 1 MiB: %ld\n", rc(pwrite(fd, "end", 3, 1 << 20)));
    say("pwrite sparse at 0: %ld\n", rc(pwrite(fd, "start", 5, 0)));
    say("fsync sparse: %ld fdatasync: %ld syncfs: %ld\n", rc(fsync(fd)), rc(fdatasync(fd)), rc(syncfs(fd)));
    close(fd);
    show("sparse");
    /* through the single and into the double indirect range (4 KiB
       blocks: 12 direct, 1024 single), 64 KiB writes */
    fd = open(at("big"), O_WRONLY | O_CREAT | O_TRUNC, 0644);
    long tw = 0;
    for (int i = 0; i < 96; i++) {
        for (size_t k = 0; k < sizeof buf; k++) buf[k] = (unsigned char)(i * 7 + k * 13 + (k >> 8));
        tw += write(fd, buf, sizeof buf);
    }
    say("write big: %ld bytes, fsync %ld\n", tw, rc(fsync(fd)));
    close(fd);
    show("big");
    say("truncate big to 100000: %ld\n", rc(truncate(at("big"), 100000)));
    show("big");
    say("truncate big to 300000: %ld\n", rc(truncate(at("big"), 300000)));
    show("big");
    say("truncate big to 0: %ld\n", rc(truncate(at("big"), 0)));
    show("big");
    /* directories */
    say("mkdir d1: %ld d1/d2: %ld d1/d2/d3: %ld\n", rc(mkdir(at("d1"), 0755)), rc(mkdir(at("d1/d2"), 0750)), rc(mkdir(at("d1/d2/d3"), 0700)));
    say("mkdir d1 again: %ld\n", rc(mkdir(at("d1"), 0755)));
    say("write d1/d2/f: %ld\n", writeall("d1/d2/f", 0, "in d2\n", 6));
    show("d1");
    show("d1/d2");
    say("rmdir d1/d2: %ld (not empty)\n", rc(rmdir(at("d1/d2"))));
    say("rmdir a: %ld (no directory)\n", rc(rmdir(at("a"))));
    say("unlink d1: %ld (a directory)\n", rc(unlink(at("d1"))));
    say("rename d1/d2 to e2: %ld\n", rc(rename(at("d1/d2"), at("e2"))));
    show("d1");
    show("e2");
    show("e2/f");
    say("rename e2 into itself: %ld\n", rc(rename(at("e2"), at("e2/d3/x"))));
    say("rmdir e2/d3: %ld\n", rc(rmdir(at("e2/d3"))));
    show("e2");
    /* renames over names */
    say("write b: %ld c: %ld\n", writeall("b", O_TRUNC, "bee\n", 4), writeall("c", O_TRUNC, "sea\n", 4));
    say("rename b over c: %ld\n", rc(rename(at("b"), at("c"))));
    show("b");
    show("c");
    say("rename c over d1: %ld (a directory)\n", rc(rename(at("c"), at("d1"))));
    say("mkdir g: %ld; rename g over d1: %ld\n", rc(mkdir(at("g"), 0755)), rc(rename(at("g"), at("d1"))));
    show("d1");
    /* hard and symbolic links */
    say("link c to c2: %ld\n", rc(link(at("c"), at("c2"))));
    show("c");
    say("unlink c: %ld\n", rc(unlink(at("c"))));
    show("c2");
    say("symlink short: %ld\n", rc(symlink("c2", at("s-short"))));
    char longt[200];
    memset(longt, 'x', sizeof longt);
    longt[0] = '.'; longt[1] = '/';
    longt[sizeof longt - 1] = 0;
    say("symlink long: %ld\n", rc(symlink(longt, at("s-long"))));
    char tb[512];
    long k = rc(readlink(at("s-short"), tb, sizeof tb));
    say("readlink s-short: %ld %.*s\n", k, (int)(k > 0 ? k : 0), tb);
    k = rc(readlink(at("s-long"), tb, sizeof tb));
    say("readlink s-long: %ld\n", k);
    show("s-short");
    show("s-long");
    uint64_t h;
    say("read through s-short: %ld\n", sum(at("s-short"), &h));
    /* modes, owners, times */
    say("chmod c2 0640: %ld chown c2 1000:1000: %ld\n", rc(chmod(at("c2"), 0640)), rc(chown(at("c2"), 1000, 1000)));
    say("chown c2 70000:70001: %ld\n", rc(chown(at("c2"), 70000, 70001)));
    show("c2");
    say("chmod a 04755: %ld\n", rc(chmod(at("a"), 04755)));
    show("a");
    fixed_times("c2", 1000000000, 1234567890);
    fixed_times("e2", 2000000000, 2200000000L);
    fixed_times("s-short", 1500000000, 1500000001);
    /* a file unlinked while open */
    fd = open(at("ghost"), O_RDWR | O_CREAT, 0644);
    say("write ghost: %ld unlink: %ld\n", rc(write(fd, "boo", 3)), rc(unlink(at("ghost"))));
    char gb[8] = { 0 };
    say("pread ghost after unlink: %ld %s\n", rc(pread(fd, gb, sizeof gb, 0)), gb);
    struct stat st;
    fstat(fd, &st);
    say("fstat ghost: links %lu size %ld\n", (unsigned long)st.st_nlink, (long)st.st_size);
    close(fd);
    show("ghost");
    /* names */
    char nm[300];
    memset(nm, 'n', sizeof nm);
    nm[255] = 0;
    say("a 255-byte name: %ld\n", writeall(nm, 0, "", 0));
    nm[255] = 'n';
    nm[256] = 0;
    say("a 256-byte name: %ld\n", writeall(nm, 0, "", 0));
    say("write \"with space\": %ld\n", writeall("with space", 0, "sp\n", 3));
    /* between file systems */
    say("rename a to /a-moved: %ld\n", rc(rename(at("a"), "/a-moved")));
    say("link a to /a-linked: %ld\n", rc(link(at("a"), "/a-linked")));
    /* what is left, and statfs's counts moved */
    struct statfs f1;
    statfs(dir, &f1);
    say("statfs: type %lx bsize %ld namelen %ld; blocks used %s, inodes used %s\n", (long)f1.f_type, (long)f1.f_bsize,
        (long)f1.f_namelen, f1.f_bfree < f0.f_bfree ? "more" : "not more", f1.f_ffree < f0.f_ffree ? "more" : "not more");
    say("sync\n");
    sync();
    say("disk: done\n");
}

int main(int argc, char **argv) {
    if (argc >= 3 && !strcmp(argv[1], "read")) {
        walk(argv[2]);
        fs(argv[2]);
        say("disk: done\n");
        return 0;
    }
    if (argc >= 3 && !strcmp(argv[1], "sum")) {
        for (int i = 2; i < argc; i++) {
            uint64_t h;
            long n = sum(argv[i], &h);
            say("%s: %ld bytes fnv %016llx\n", argv[i], n, (unsigned long long)h);
        }
        return 0;
    }
    if (argc >= 3 && !strcmp(argv[1], "write")) {
        session(argv[2]);
        return 0;
    }
    fprintf(stderr, "usage: disk read DIR | disk sum FILE... | disk write DIR\n");
    return 2;
}
