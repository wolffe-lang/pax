/* nodes.c — px79's probe of the block device nodes: one static glibc
   program run unmodified on Linux (the guest under QEMU with one, two or
   three virtio disks: tools/linux-nodes) and on PAX (kmain_console with
   the same disks), the two outputs compared line for line
   (tests/mpx6-nodes).

     nodes stat PATH...      lstat's fields of each: the type and mode in
                             octal, st_rdev's major and minor (and as
                             `stat -c %t,%T` prints them), the size, the
                             blocks, st_blksize, the links, the owner;
                             st_dev and the times are not printed (each
                             system's /dev is its own file system)
     nodes dev               every block device in /dev (readdir, sorted):
                             its name, mode, numbers and owner
     nodes sys               /proc/partitions as it is; for each entry of
                             /sys/block (sorted) its dev, size, ro and
                             removable, and each partition directory in it
                             (sorted) its dev, start, size, partition and
                             ro; then /sys/class/block/<name>/dev for every
                             name there (sorted)
     nodes ioctl PATH        the block ioctls on PATH opened read-only:
                             each one's answer and the bytes it wrote (the
                             buffer is filled with 0xa5 first, so the width
                             the kernel writes is seen), then requests a
                             block device does not serve (-ENOTTY)
     nodes io PATH           reads, opened read-only: lseek's three ways,
                             a 100-byte read at offset 3, reads across and
                             at the end, pread at an odd offset, an
                             O_DIRECT open and an aligned read; each
                             answer and the FNV-1a 64 of what came back
     nodes wio PATH          writes, opened read-write: 100 bytes at
                             offset 3 and read back, a write across the
                             end, one at the end, one past it, fsync; the
                             bytes it overwrote are put back
     nodes pattern PATH SEED every 512-byte sector written with the
                             pattern (sector << 32 | word) ^ SEED in 64 KiB
                             writes, fsync, then read back: the count and
                             how many differ
     nodes check PATH SEED   the read back alone
     nodes put PATH OFF FILE FILE's bytes written at byte OFF, fsync
     nodes rewrite PATH OFF LEN   LEN bytes at OFF read and written back
                             (the same bytes: a raw write that changes
                             nothing), fsync
     nodes mark PATH OFF SEED     one 512-byte sector of the pattern (its
                             sector number OFF / 512) at OFF, fsync
     nodes rd PATH OFF LEN   LEN bytes at OFF: the count and their FNV-1a 64
     nodes send PATH OFF FILE HOW  FILE's bytes onto PATH from byte OFF
                             by sendfile(2) (HOW `sendfile`), through a
                             pipe by splice(2) (`splice`: the file into
                             the pipe, the pipe onto PATH) or by
                             copy_file_range(2) (`cfr`), fsync: each
                             call's last answer and the bytes moved
     nodes copy SRC DST      every byte of SRC written to DST from its start
                             (as much as both hold), fsync
     nodes sync              sync(2)
     nodes rrpart PATH       ioctl(BLKRRPART)
     nodes add PATH PNO START LEN   BLKPG_ADD_PARTITION (bytes)
     nodes del PATH PNO      BLKPG_DEL_PARTITION
     nodes excl PATH         open(O_RDWR | O_EXCL)
     nodes hold PATH CMD...  PATH opened read-only and held while CMD runs
                             (holdx: O_RDONLY | O_EXCL)
                             (this program again, by fork and exec of its
                             argv[0]: call it by its full path)
     nodes mount SRC DIR [TYPE]   mount(2) (default ext2), no flags
     nodes umount DIR        umount2(2)
     nodes mounts            /proc/mounts' lines whose source is in /dev

   Every answer is the call's value or `-errno NAME`. Built with the
   host's cc: `cc -static -O1` (tools/mkdiskprobe). Written from the man
   pages (ioctl(2), ioctl_list(2), sd(4), open(2), lseek(2), read(2),
   write(2), mount(2), proc(5), sysfs(5), sendfile(2), splice(2),
   copy_file_range(2)) and the uapi headers
   linux/fs.h, linux/blkpg.h and linux/hdreg.h for the requests' numbers
   and structures; no kernel's source, no libc's source, no util-linux
   source. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/blkpg.h>
#include <linux/fs.h>
#include <linux/hdreg.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/sendfile.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

static void say(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    fflush(stdout);
}

/* A call's answer: its value, or `-errno NAME`. */
static char ansbuf[8][64];
static int ansk;
static const char *ans(long r) {
    char *b = ansbuf[ansk++ & 7];
    if (r >= 0) {
        snprintf(b, 64, "%ld", r);
    } else {
        const char *n = strerrorname_np(errno);
        snprintf(b, 64, "-%d %s", errno, n ? n : "?");
    }
    return b;
}

static uint64_t fnv(const unsigned char *p, size_t n) {
    uint64_t h = 0xcbf29ce484222325ULL;
    for (size_t i = 0; i < n; i++) {
        h ^= p[i];
        h *= 0x100000001b3ULL;
    }
    return h;
}

static const char *kind(mode_t m) {
    switch (m & S_IFMT) {
    case S_IFBLK: return "blk";
    case S_IFCHR: return "chr";
    case S_IFDIR: return "dir";
    case S_IFREG: return "reg";
    case S_IFLNK: return "lnk";
    case S_IFIFO: return "fifo";
    case S_IFSOCK: return "sock";
    default: return "?";
    }
}

static void stat_one(const char *p) {
    struct stat st;
    if (lstat(p, &st) < 0) {
        say("stat %s: %s\n", p, ans(-1));
        return;
    }
    say("stat %s: %s mode %06o rdev %u:%u (%x,%x) size %ld blocks %ld blksize %ld links %lu owner %u:%u\n", p, kind(st.st_mode),
        (unsigned)st.st_mode, major(st.st_rdev), minor(st.st_rdev), major(st.st_rdev), minor(st.st_rdev), (long)st.st_size,
        (long)st.st_blocks, (long)st.st_blksize, (unsigned long)st.st_nlink, st.st_uid, st.st_gid);
}

static int cmpstr(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }

/* The names in DIR (not . and ..), sorted; *n their count. */
static char **names(const char *dir, int *n) {
    *n = 0;
    DIR *d = opendir(dir);
    if (!d) return NULL;
    int cap = 32;
    char **v = malloc(sizeof *v * (size_t)cap);
    struct dirent *e;
    while ((e = readdir(d))) {
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, "..")) continue;
        if (*n == cap) { cap *= 2; v = realloc(v, sizeof *v * (size_t)cap); }
        v[(*n)++] = strdup(e->d_name);
    }
    closedir(d);
    qsort(v, (size_t)*n, sizeof *v, cmpstr);
    return v;
}

static void dev_list(void) {
    int n;
    char **v = names("/dev", &n);
    char p[512];
    for (int i = 0; i < n; i++) {
        snprintf(p, sizeof p, "/dev/%s", v[i]);
        struct stat st;
        if (lstat(p, &st) == 0 && S_ISBLK(st.st_mode))
            say("dev %s: mode %06o rdev %u:%u owner %u:%u\n", v[i], (unsigned)st.st_mode, major(st.st_rdev), minor(st.st_rdev), st.st_uid, st.st_gid);
    }
}

/* A sysfs attribute's text, its newline dropped. */
static const char *attr(const char *dir, const char *name) {
    static char b[8][256];
    static int k;
    char *o = b[k++ & 7];
    char p[512];
    snprintf(p, sizeof p, "%s/%s", dir, name);
    int fd = open(p, O_RDONLY);
    if (fd < 0) { snprintf(o, 256, "(%s)", ans(-1)); return o; }
    ssize_t r = read(fd, o, 255);
    int e = errno;
    close(fd);
    if (r < 0) { errno = e; snprintf(o, 256, "(read %s)", ans(-1)); return o; }
    o[r] = 0;
    if (r > 0 && o[r - 1] == '\n') o[r - 1] = 0;
    return o;
}

static void cat(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) { say("%s: %s\n", path, ans(-1)); return; }
    static char b[65536];
    ssize_t t = 0, r;
    while ((r = read(fd, b + t, sizeof b - 1 - (size_t)t)) > 0) t += r;
    close(fd);
    b[t] = 0;
    say("%s", b);
}

static void sys_list(void) {
    say("-- /proc/partitions\n");
    cat("/proc/partitions");
    say("-- /sys/block\n");
    int n;
    char **v = names("/sys/block", &n);
    for (int i = 0; i < n; i++) {
        char d[512];
        snprintf(d, sizeof d, "/sys/block/%s", v[i]);
        say("%s: dev %s size %s ro %s removable %s\n", v[i], attr(d, "dev"), attr(d, "size"), attr(d, "ro"), attr(d, "removable"));
        int m;
        char **w = names(d, &m);
        for (int j = 0; j < m; j++) {
            if (strncmp(w[j], v[i], strlen(v[i]))) continue;
            char e[600];
            snprintf(e, sizeof e, "%s/%s", d, w[j]);
            say("%s/%s: dev %s start %s size %s partition %s ro %s\n", v[i], w[j], attr(e, "dev"), attr(e, "start"), attr(e, "size"),
                attr(e, "partition"), attr(e, "ro"));
        }
    }
    say("-- /sys/class/block\n");
    v = names("/sys/class/block", &n);
    for (int i = 0; i < n; i++) {
        char d[512];
        snprintf(d, sizeof d, "/sys/class/block/%s", v[i]);
        say("%s: dev %s\n", v[i], attr(d, "dev"));
    }
}

static unsigned char buf[1 << 16];

/* One ioctl with a buffer of `len` bytes filled with 0xa5 first: its
   answer and the bytes after it. */
static void probe_req(int fd, const char *name, unsigned long req, size_t len) {
    unsigned char b[32];
    memset(b, 0xa5, sizeof b);
    long r = ioctl(fd, req, b);
    char hex[80] = "";
    for (size_t i = 0; i < len; i++) snprintf(hex + 2 * i, 3, "%02x", b[i]);
    say("ioctl %s: %s bytes %s\n", name, ans(r), hex);
}

static void ioctls(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) { say("open %s: %s\n", path, ans(-1)); return; }
    say("ioctls %s\n", path);
    probe_req(fd, "BLKGETSIZE64", BLKGETSIZE64, 16);
    probe_req(fd, "BLKGETSIZE", BLKGETSIZE, 16);
    probe_req(fd, "BLKSSZGET", BLKSSZGET, 8);
    probe_req(fd, "BLKPBSZGET", BLKPBSZGET, 8);
    probe_req(fd, "BLKIOMIN", BLKIOMIN, 8);
    probe_req(fd, "BLKIOOPT", BLKIOOPT, 8);
    probe_req(fd, "BLKALIGNOFF", BLKALIGNOFF, 8);
    probe_req(fd, "BLKDISCARDZEROES", BLKDISCARDZEROES, 8);
    probe_req(fd, "BLKROGET", BLKROGET, 8);
    probe_req(fd, "BLKBSZGET", BLKBSZGET, 16);
    probe_req(fd, "BLKSECTGET", BLKSECTGET, 8);
    probe_req(fd, "BLKRAGET", BLKRAGET, 16);
    probe_req(fd, "BLKFRAGET", BLKFRAGET, 16);
    probe_req(fd, "BLKROTATIONAL", BLKROTATIONAL, 8);
    probe_req(fd, "BLKGETDISKSEQ", BLKGETDISKSEQ, 16);
    probe_req(fd, "HDIO_GETGEO", HDIO_GETGEO, 24);
    say("ioctl BLKFLSBUF: %s\n", ans(ioctl(fd, BLKFLSBUF, 0)));
    /* not a block device's: */
    probe_req(fd, "TCGETS", TCGETS, 8);
    probe_req(fd, "FIONREAD", FIONREAD, 8);
    probe_req(fd, "FS_IOC_GETFLAGS", FS_IOC_GETFLAGS, 8);
    probe_req(fd, "0x1234", 0x1234, 8);
    probe_req(fd, "_IO(0x12,200)", _IO(0x12, 200), 8);
    close(fd);
}

static void rd(int fd, off_t off, size_t n, const char *what) {
    off_t s = lseek(fd, off, SEEK_SET);
    if (s < 0) { say("%s: lseek %ld: %s\n", what, (long)off, ans(-1)); return; }
    memset(buf, 0, n);
    ssize_t r = read(fd, buf, n);
    if (r < 0) { say("%s: read %zu at %ld: %s\n", what, n, (long)off, ans(-1)); return; }
    say("%s: read %zu at %ld: %zd fnv %016llx; offset now %s\n", what, n, (long)off, r, (unsigned long long)fnv(buf, (size_t)r),
        ans(lseek(fd, 0, SEEK_CUR)));
}

static void io(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) { say("open %s: %s\n", path, ans(-1)); return; }
    off_t size = lseek(fd, 0, SEEK_END);
    say("io %s: SEEK_END %s\n", path, ans(size));
    say("io %s: SEEK_CUR -512 %s\n", path, ans(lseek(fd, -512, SEEK_CUR)));
    say("io %s: SEEK_SET 4096 %s\n", path, ans(lseek(fd, 4096, SEEK_SET)));
    say("io %s: SEEK_CUR 3 %s\n", path, ans(lseek(fd, 3, SEEK_CUR)));
    say("io %s: SEEK_SET -1 %s\n", path, ans(lseek(fd, -1, SEEK_SET)));
    say("io %s: SEEK_SET size+512 %s\n", path, ans(lseek(fd, size + 512, SEEK_SET)));
    say("io %s: SEEK_END 512 %s\n", path, ans(lseek(fd, 512, SEEK_END)));
    say("io %s: SEEK_DATA 0 %s\n", path, ans(lseek(fd, 0, SEEK_DATA)));
    say("io %s: whence 9 %s\n", path, ans(lseek(fd, 0, 9)));
    rd(fd, 3, 100, "io 100 at 3");
    rd(fd, 0, 512, "io sector 0");
    rd(fd, 1000, 5000, "io 5000 at 1000");
    if (size > 0) {
        rd(fd, size - 100, 512, "io across the end");
        rd(fd, size, 512, "io at the end");
        rd(fd, size - 512, 512, "io the last sector");
    }
    ssize_t r = pread(fd, buf, 1000, 7);
    say("io pread 1000 at 7: %s fnv %016llx; offset %s\n", ans(r), (unsigned long long)fnv(buf, r > 0 ? (size_t)r : 0), ans(lseek(fd, 0, SEEK_CUR)));
    r = pread(fd, buf, 512, size + 4096);
    say("io pread past the end: %s\n", ans(r));
    r = pread(fd, buf, 512, -1);
    say("io pread at -1: %s\n", ans(r));
    r = read(fd, buf, 0);
    say("io read 0: %s\n", ans(r));
    close(fd);
    fd = open(path, O_RDONLY | O_DIRECT);
    say("io O_DIRECT open: %s\n", fd < 0 ? ans(-1) : "ok");
    if (fd >= 0) {
        void *al;
        if (posix_memalign(&al, 4096, 4096) == 0) {
            r = read(fd, al, 4096);
            say("io O_DIRECT read 4096 aligned: %s fnv %016llx\n", ans(r), (unsigned long long)fnv(al, r > 0 ? (size_t)r : 0));
            free(al);
        }
        close(fd);
    }
    fd = open(path, O_WRONLY | O_TRUNC);
    say("io O_WRONLY|O_TRUNC open: %s\n", fd < 0 ? ans(-1) : "ok");
    if (fd >= 0) close(fd);
    fd = open(path, O_RDWR);
    say("io O_RDWR open: %s\n", fd < 0 ? ans(-1) : "ok");
    if (fd >= 0) {
        long w1 = pwrite(fd, buf, 0, 0);
        say("io O_RDWR pwrite 0 bytes: %s\n", ans(w1));
        close(fd);
    }
    fd = open(path, O_RDONLY | O_DIRECTORY);
    say("io O_DIRECTORY open: %s\n", fd < 0 ? ans(-1) : "ok");
    if (fd >= 0) close(fd);
    struct stat st;
    fd = open(path, O_RDONLY);
    if (fd >= 0 && fstat(fd, &st) == 0)
        say("io fstat: %s mode %06o rdev %u:%u size %ld blksize %ld\n", kind(st.st_mode), (unsigned)st.st_mode, major(st.st_rdev),
            minor(st.st_rdev), (long)st.st_size, (long)st.st_blksize);
    if (fd >= 0) {
        say("io fsync read-only: %s\n", ans(fsync(fd)));
        say("io write read-only: %s\n", ans(write(fd, "x", 1)));
        close(fd);
    }
}

static void wio(const char *path) {
    int fd = open(path, O_RDWR);
    if (fd < 0) { say("open %s rw: %s\n", path, ans(-1)); return; }
    off_t size = lseek(fd, 0, SEEK_END);
    static unsigned char keep[8192], mark[8192];
    say("wio %s: size %s\n", path, ans(size));
    /* the first 8 KiB and the last 8 KiB kept, put back at the end */
    ssize_t k0 = pread(fd, keep, 4096, 0);
    for (int i = 0; i < 8192; i++) mark[i] = (unsigned char)(i * 7 + 1);
    say("wio pwrite 100 at 3: %s\n", ans(pwrite(fd, mark, 100, 3)));
    memset(buf, 0, 512);
    ssize_t r = pread(fd, buf, 512, 0);
    say("wio read back sector 0: %s fnv %016llx (the 100 bytes %s)\n", ans(r), (unsigned long long)fnv(buf, 512),
        memcmp(buf + 3, mark, 100) == 0 ? "there" : "not there");
    long a1 = lseek(fd, 1, SEEK_SET);
    long a2 = write(fd, mark, 7);
    long a3 = lseek(fd, 0, SEEK_CUR);
    say("wio lseek 1 then write 7: %s %s, offset %s\n", ans(a1), ans(a2), ans(a3));
    say("wio pwrite 0 bytes: %s\n", ans(pwrite(fd, mark, 0, 0)));
    say("wio fsync: %s\n", ans(fsync(fd)));
    say("wio fdatasync: %s\n", ans(fdatasync(fd)));
    if (k0 == 4096) say("wio put back the first 4096: %s\n", ans(pwrite(fd, keep, 4096, 0)));
    static unsigned char tail[8192];
    ssize_t kt = pread(fd, tail, 8192, size - 8192);
    say("wio keep the last 8192: %s\n", ans(kt));
    say("wio pwrite 512 across the end (100 left): %s\n", ans(pwrite(fd, mark, 512, size - 100)));
    say("wio pwrite 512 at the end: %s\n", ans(pwrite(fd, mark, 512, size)));
    say("wio pwrite 512 past the end: %s\n", ans(pwrite(fd, mark, 512, size + 4096)));
    long e1 = lseek(fd, 0, SEEK_END);
    long e2 = write(fd, mark, 1);
    say("wio lseek end, write 1: %s %s\n", ans(e1), ans(e2));
    r = pread(fd, buf, 100, size - 100);
    say("wio the last 100 read back: %s (%s)\n", ans(r), r == 100 && memcmp(buf, mark, 100) == 0 ? "the mark" : "not the mark");
    if (kt == 8192) say("wio put back the last 8192: %s\n", ans(pwrite(fd, tail, 8192, size - 8192)));
    say("wio fsync: %s\n", ans(fsync(fd)));
    say("wio close: %s\n", ans(close(fd)));
}

static uint64_t pat(uint64_t s, uint64_t w, uint64_t seed) { return ((s << 32) | w) ^ seed; }

static void pattern(const char *path, uint64_t seed, int write_it) {
    int fd = open(path, write_it ? O_RDWR : O_RDONLY);
    if (fd < 0) { say("open %s: %s\n", path, ans(-1)); return; }
    off_t size = lseek(fd, 0, SEEK_END);
    uint64_t sectors = (uint64_t)size / 512, writes = 0;
    lseek(fd, 0, SEEK_SET);
    uint64_t *w = (uint64_t *)buf;
    if (write_it) {
        for (uint64_t s = 0; s < sectors;) {
            uint64_t n = sectors - s < 128 ? sectors - s : 128;
            for (uint64_t i = 0; i < n; i++)
                for (uint64_t j = 0; j < 64; j++) w[i * 64 + j] = pat(s + i, j, seed);
            ssize_t r = write(fd, buf, n * 512);
            if (r != (ssize_t)(n * 512)) { say("pattern %s: write at sector %llu: %s\n", path, (unsigned long long)s, ans(r)); close(fd); return; }
            writes++;
            s += n;
        }
        say("pattern %s: wrote %llu sectors in %llu writes, fsync %s\n", path, (unsigned long long)sectors, (unsigned long long)writes, ans(fsync(fd)));
    }
    lseek(fd, 0, SEEK_SET);
    uint64_t bad = 0, first = ~0ULL, got = 0;
    for (uint64_t s = 0; s < sectors;) {
        uint64_t n = sectors - s < 128 ? sectors - s : 128;
        ssize_t r = read(fd, buf, n * 512);
        if (r != (ssize_t)(n * 512)) { say("pattern %s: read at sector %llu: %s\n", path, (unsigned long long)s, ans(r)); break; }
        for (uint64_t i = 0; i < n; i++) {
            int ok = 1;
            for (uint64_t j = 0; j < 64; j++) if (w[i * 64 + j] != pat(s + i, j, seed)) ok = 0;
            if (!ok) { bad++; if (first == ~0ULL) first = s + i; }
        }
        got += n;
        s += n;
    }
    if (bad) say("pattern %s: read back %llu sectors, %llu differ, first %llu\n", path, (unsigned long long)got, (unsigned long long)bad, (unsigned long long)first);
    else say("pattern %s: read back %llu sectors, 0 differ\n", path, (unsigned long long)got);
    close(fd);
}

static void put(const char *path, long off, const char *file) {
    int in = open(file, O_RDONLY);
    if (in < 0) { say("put %s: open %s: %s\n", path, file, ans(-1)); return; }
    int fd = open(path, O_RDWR);
    if (fd < 0) { say("put %s: %s\n", path, ans(-1)); close(in); return; }
    long total = 0, w = 0;
    for (;;) {
        ssize_t n = read(in, buf, sizeof buf);
        if (n <= 0) break;
        w = pwrite(fd, buf, (size_t)n, off + total);
        if (w != n) break;
        total += n;
    }
    close(in);
    long f = fsync(fd);
    say("put %s: %ld bytes at %ld: %s, fsync %s\n", path, total, off, w < 0 ? ans(w) : "written", ans(f));
    close(fd);
}

static void rewrite(const char *path, long off, long len) {
    int fd = open(path, O_RDWR);
    if (fd < 0) { say("rewrite %s: %s\n", path, ans(-1)); return; }
    long done = 0, w = 0;
    while (done < len) {
        long n = len - done < (long)sizeof buf ? len - done : (long)sizeof buf;
        long r = pread(fd, buf, (size_t)n, off + done);
        if (r <= 0) { w = r; break; }
        w = pwrite(fd, buf, (size_t)r, off + done);
        if (w != r) break;
        done += r;
    }
    long f = fsync(fd);
    say("rewrite %s: %ld bytes at %ld: %s, fsync %s\n", path, done, off, w < 0 ? ans(w) : "written back", ans(f));
    close(fd);
}

static void mark(const char *path, long off, uint64_t seed) {
    int fd = open(path, O_RDWR);
    if (fd < 0) { say("mark %s: %s\n", path, ans(-1)); return; }
    uint64_t *w = (uint64_t *)buf;
    for (uint64_t j = 0; j < 64; j++) w[j] = pat((uint64_t)off / 512, j, seed);
    long r = pwrite(fd, buf, 512, off);
    long f = fsync(fd);
    say("mark %s: sector %ld: %s, fsync %s\n", path, off / 512, ans(r), ans(f));
    close(fd);
}

static void copy(const char *src, const char *dst) {
    int in = open(src, O_RDONLY);
    if (in < 0) { say("copy %s: %s\n", src, ans(-1)); return; }
    int out = open(dst, O_RDWR);
    if (out < 0) { say("copy %s: %s\n", dst, ans(-1)); close(in); return; }
    long total = 0, w = 0;
    for (;;) {
        ssize_t n = read(in, buf, sizeof buf);
        if (n <= 0) break;
        w = write(out, buf, (size_t)n);
        if (w <= 0) break;
        total += w;
        if (w != n) break;
    }
    long f = fsync(out);
    say("copy %s to %s: %ld bytes%s, fsync %s\n", src, dst, total, w < 0 ? ans(w) : "", ans(f));
    close(in);
    close(out);
}

static void rdsum(const char *path, long off, long len) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) { say("rd %s: %s\n", path, ans(-1)); return; }
    if (len > (long)sizeof buf) len = sizeof buf;
    long r = pread(fd, buf, (size_t)len, off);
    say("rd %s: %ld at %ld: %s fnv %016llx\n", path, len, off, ans(r), (unsigned long long)fnv(buf, r > 0 ? (size_t)r : 0));
    close(fd);
}

static void send(const char *path, long off, const char *file, const char *how) {
    int in = open(file, O_RDONLY);
    if (in < 0) { say("send %s: open %s: %s\n", path, file, ans(-1)); return; }
    int out = open(path, O_WRONLY);
    if (out < 0) { say("send %s: %s\n", path, ans(-1)); close(in); return; }
    struct stat st;
    fstat(in, &st);
    long at = lseek(out, off, SEEK_SET);
    long total = 0, r = 0;
    if (!strcmp(how, "sendfile")) {
        while (total < st.st_size) {
            r = sendfile(out, in, NULL, (size_t)(st.st_size - total));
            if (r <= 0) break;
            total += r;
        }
    } else if (!strcmp(how, "splice")) {
        int p[2];
        if (pipe(p) < 0) { say("send %s: pipe %s\n", path, ans(-1)); close(in); close(out); return; }
        while (total < st.st_size) {
            r = splice(in, NULL, p[1], NULL, 4096, 0);
            if (r <= 0) break;
            long got = r, moved = 0;
            while (moved < got) {
                r = splice(p[0], NULL, out, NULL, (size_t)(got - moved), 0);
                if (r <= 0) break;
                moved += r;
            }
            total += moved;
            if (r <= 0) break;
        }
        close(p[0]);
        close(p[1]);
    } else {
        r = copy_file_range(in, NULL, out, NULL, (size_t)st.st_size, 0);
        if (r > 0) total = r;
    }
    const char *last = ans(r);
    long f = fsync(out);
    long pos = lseek(out, 0, SEEK_CUR);
    say("send %s %s: lseek %s, last %s, %ld bytes, at %ld, fsync %s\n", how, path, ans(at), last, total, pos, ans(f));
    close(in);
    close(out);
}

static void blkpg(const char *path, int op, int pno, long long start, long long len) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) { say("blkpg %s: %s\n", path, ans(-1)); return; }
    struct blkpg_partition p;
    memset(&p, 0, sizeof p);
    p.start = start;
    p.length = len;
    p.pno = pno;
    struct blkpg_ioctl_arg a = { .op = op, .flags = 0, .datalen = sizeof p, .data = &p };
    say("blkpg %s %s %d %lld %lld: %s\n", path, op == BLKPG_ADD_PARTITION ? "add" : "del", pno, start, len, ans(ioctl(fd, BLKPG, &a)));
    close(fd);
}

static void mounts(void) {
    FILE *f = fopen("/proc/mounts", "r");
    if (!f) { say("/proc/mounts: %s\n", ans(-1)); return; }
    char l[1024];
    while (fgets(l, sizeof l, f))
        if (!strncmp(l, "/dev/", 5)) say("mounts: %s", l);
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: nodes stat|dev|sys|ioctl|io|wio|pattern|check|put|rrpart|add|del|excl|hold|mount|umount|mounts ...\n"); return 2; }
    const char *c = argv[1];
    if (!strcmp(c, "stat")) { for (int i = 2; i < argc; i++) stat_one(argv[i]); return 0; }
    if (!strcmp(c, "dev")) { dev_list(); return 0; }
    if (!strcmp(c, "sys")) { sys_list(); return 0; }
    if (!strcmp(c, "ioctl") && argc == 3) { ioctls(argv[2]); return 0; }
    if (!strcmp(c, "io") && argc == 3) { io(argv[2]); return 0; }
    if (!strcmp(c, "wio") && argc == 3) { wio(argv[2]); return 0; }
    if (!strcmp(c, "pattern") && argc == 4) { pattern(argv[2], strtoull(argv[3], 0, 0), 1); return 0; }
    if (!strcmp(c, "check") && argc == 4) { pattern(argv[2], strtoull(argv[3], 0, 0), 0); return 0; }
    if (!strcmp(c, "put") && argc == 5) { put(argv[2], strtol(argv[3], 0, 0), argv[4]); return 0; }
    if (!strcmp(c, "rrpart") && argc == 3) {
        int fd = open(argv[2], O_RDONLY);
        if (fd < 0) { say("rrpart %s: %s\n", argv[2], ans(-1)); return 0; }
        say("rrpart %s: %s\n", argv[2], ans(ioctl(fd, BLKRRPART, 0)));
        close(fd);
        return 0;
    }
    if (!strcmp(c, "rewrite") && argc == 5) { rewrite(argv[2], strtol(argv[3], 0, 0), strtol(argv[4], 0, 0)); return 0; }
    if (!strcmp(c, "mark") && argc == 5) { mark(argv[2], strtol(argv[3], 0, 0), strtoull(argv[4], 0, 0)); return 0; }
    if (!strcmp(c, "rd") && argc == 5) { rdsum(argv[2], strtol(argv[3], 0, 0), strtol(argv[4], 0, 0)); return 0; }
    if (!strcmp(c, "send") && argc == 6) { send(argv[2], strtol(argv[3], 0, 0), argv[4], argv[5]); return 0; }
    if (!strcmp(c, "copy") && argc == 4) { copy(argv[2], argv[3]); return 0; }
    if (!strcmp(c, "sync") && argc == 2) { sync(); say("sync: done\n"); return 0; }
    if (!strcmp(c, "add") && argc == 6) { blkpg(argv[2], BLKPG_ADD_PARTITION, atoi(argv[3]), strtoll(argv[4], 0, 0), strtoll(argv[5], 0, 0)); return 0; }
    if (!strcmp(c, "del") && argc == 4) { blkpg(argv[2], BLKPG_DEL_PARTITION, atoi(argv[3]), 0, 0); return 0; }
    if (!strcmp(c, "excl") && argc == 3) {
        int fd = open(argv[2], O_RDWR | O_EXCL);
        say("excl %s: %s\n", argv[2], fd < 0 ? ans(-1) : "ok");
        if (fd >= 0) close(fd);
        return 0;
    }
    if ((!strcmp(c, "hold") || !strcmp(c, "holdx")) && argc >= 4) {
        int fd = open(argv[2], !strcmp(c, "holdx") ? O_RDONLY | O_EXCL : O_RDONLY);
        say("hold %s: %s\n", argv[2], fd < 0 ? ans(-1) : "open");
        argv[2] = argv[0];
        pid_t p = fork();
        if (p == 0) { execv(argv[0], argv + 2); _exit(127); }
        int s = 0;
        waitpid(p, &s, 0);
        if (fd >= 0) close(fd);
        say("hold %s: closed\n", argv[2]);
        return 0;
    }
    if (!strcmp(c, "mount") && (argc == 4 || argc == 5)) {
        say("mount %s %s: %s\n", argv[2], argv[3], ans(mount(argv[2], argv[3], argc == 5 ? argv[4] : "ext2", 0, NULL)));
        return 0;
    }
    if (!strcmp(c, "umount") && argc == 3) { say("umount %s: %s\n", argv[2], ans(umount2(argv[2], 0))); return 0; }
    if (!strcmp(c, "mounts")) { mounts(); return 0; }
    fprintf(stderr, "nodes: unknown command %s\n", c);
    return 2;
}
