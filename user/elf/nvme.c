/* nvme.c — px75's probe of an NVMe namespace's node: one static glibc
   program run unmodified on Linux (the guest under QEMU with QEMU's
   `nvme` controller: tools/linux-nodes --nvme) and on PAX (kmain_console
   with the same disks), the two outputs compared line for line and the
   disks they leave compared byte for byte (tests/mpx6-nvme).

     nvme sizes PATH SEED    writes of 22 lengths at 22 offsets (one
                             sector, one page, two pages, three, 64 and
                             128 KiB, past the largest request, 1 MiB, odd
                             lengths at odd offsets, across page and
                             request boundaries), each piece's bytes
                             (byte x of the disk: the FNV-1a 64 of
                             SEED ^ x / 8, its byte x % 8), fsync; then
                             each piece read back at another length and
                             offset that covers it: the count and how
                             many bytes differ, and the FNV-1a 64 of what
                             came back
     nvme speed PATH MIB     MIB MiB written from byte 0 in writes of 1
                             MiB with tools/blk-pattern's pattern (sector
                             s, word w: (s << 32 | w) ^ "paxdisk\0"),
                             fsync, BLKFLSBUF (so the read-back is the
                             device's, not a page cache's), then read back
                             in reads of 1 MiB and checked; the times (CLOCK_MONOTONIC) and the
                             rates in MB/s (10^6 bytes) last, after a
                             line `== time` of their own, so a session's
                             comparison leaves them out
     nvme sum PATH OFF LEN   LEN bytes at OFF read in 128 KiB reads: the
                             count and their FNV-1a 64

   Every answer is the call's value or `-errno NAME`. Built with the
   host's cc: `cc -static -O1` (tools/mknvme). Written from the man pages
   (open(2), read(2), write(2), pread(2), pwrite(2), fsync(2),
   clock_gettime(2)); no kernel's source, no libc's source. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/fs.h>

static void say(const char *f, ...) __attribute__((format(printf, 1, 2)));
#include <stdarg.h>
static void say(const char *f, ...) {
    char b[512];
    va_list ap;
    va_start(ap, f);
    int n = vsnprintf(b, sizeof b, f, ap);
    va_end(ap);
    if (n > 0) {
        ssize_t r = write(1, b, (size_t)n < sizeof b ? (size_t)n : sizeof b - 1);
        (void)r;
    }
}

static const char *ename(int e) {
    switch (e) {
    case EIO: return "EIO";
    case ENOSPC: return "ENOSPC";
    case EINVAL: return "EINVAL";
    case EBADF: return "EBADF";
    case EFAULT: return "EFAULT";
    case ENXIO: return "ENXIO";
    case EPERM: return "EPERM";
    case ENOENT: return "ENOENT";
    case ENOMEM: return "ENOMEM";
    case EACCES: return "EACCES";
    default: return "E?";
    }
}

static char ansbuf[64];
static const char *ans(long r) {
    if (r < 0) snprintf(ansbuf, sizeof ansbuf, "-%d %s", errno, ename(errno));
    else snprintf(ansbuf, sizeof ansbuf, "%ld", r);
    return ansbuf;
}

static uint64_t fnv(uint64_t h, const unsigned char *p, size_t n) {
    for (size_t i = 0; i < n; i++) { h ^= p[i]; h *= 0x100000001b3ULL; }
    return h;
}
#define FNV0 0xcbf29ce484222325ULL

/* Byte x of the disk in `sizes`: the FNV-1a 64 of the 8 bytes of
   SEED ^ (x / 8), its byte x % 8. */
static unsigned char pat(uint64_t seed, uint64_t x) {
    uint64_t v = seed ^ (x / 8);
    uint64_t h = fnv(FNV0, (const unsigned char *)&v, 8);
    return (unsigned char)(h >> ((x % 8) * 8));
}

static unsigned char *buf;
#define BUFSZ (2u << 20)

/* offset, length of the writes, and the read that checks each (offset, length) */
static const uint64_t W[][4] = {
    {0, 512, 0, 512},                       /* one sector */
    {4096, 4096, 4096, 4096},               /* one page */
    {8192, 8192, 8192, 8192},               /* two pages: PRP2 is the second */
    {20480, 12288, 20480, 12288},           /* three pages: a PRP list */
    {65536, 65536, 61440, 73728},           /* 64 KiB, read across both ends */
    {131072, 131072, 131072, 131072},       /* 128 KiB: the largest request */
    {262144, 135168, 262144, 139264},       /* past the largest request */
    {524288, 1048576, 524288, 1048576},     /* 1 MiB: eight requests */
    {1572867, 1000, 1572864, 4096},         /* odd length at an odd offset */
    {1581055, 2, 1576960, 8192},            /* across a page boundary, two bytes */
    {1589248, 4095, 1589248, 8192},         /* one byte short of a page */
    {1597441, 4096, 1597440, 8192},         /* a page, one byte late */
    {1609728, 131073, 1609728, 135168},     /* the largest request and a byte */
    {1744896, 12289, 1740800, 20480},       /* three pages and a byte, mid-page */
    {1798143, 70000, 1794048, 77824},       /* odd 70000 bytes */
    {1900544, 512, 1900032, 1536},          /* a sector between neighbours */
    {1901056, 511, 1900032, 2048},          /* a sector less a byte */
    {1966080, 262144, 1966080, 262144},     /* two largest requests */
    {2359296, 196608, 2359296, 196608},     /* a request and a half */
    {2621440, 4096, 2617344, 12288},        /* a page among unwritten ones */
    {3145728, 1048575, 3145728, 1048576},   /* 1 MiB less a byte */
    {4194303, 1, 4190208, 8192},            /* the last byte of 4 MiB */
};
#define NW (sizeof W / sizeof W[0])

static void sizes(const char *path, uint64_t seed) {
    int fd = open(path, O_RDWR);
    if (fd < 0) { say("sizes %s: open %s\n", path, ans(fd)); return; }
    for (size_t i = 0; i < NW; i++) {
        uint64_t off = W[i][0], len = W[i][1];
        for (uint64_t k = 0; k < len; k++) buf[k] = pat(seed, off + k);
        ssize_t r = pwrite(fd, buf, len, (off_t)off);
        say("sizes %s: write %llu at %llu: %s\n", path, (unsigned long long)len, (unsigned long long)off, ans(r));
    }
    say("sizes %s: fsync %s\n", path, ans(fsync(fd)));
    for (size_t i = 0; i < NW; i++) {
        uint64_t roff = W[i][2], rlen = W[i][3];
        memset(buf, 0xa5, rlen);
        ssize_t r = pread(fd, buf, rlen, (off_t)roff);
        uint64_t bad = 0;
        if (r == (ssize_t)rlen) {
            /* the bytes of every write this read covers are the pattern's */
            for (size_t j = 0; j < NW; j++) {
                uint64_t a = W[j][0] > roff ? W[j][0] : roff;
                uint64_t e = W[j][0] + W[j][1] < roff + rlen ? W[j][0] + W[j][1] : roff + rlen;
                for (uint64_t x = a; x < e; x++)
                    if (buf[x - roff] != pat(seed, x)) bad++;
            }
        }
        say("sizes %s: read %llu at %llu: %s, %llu bytes differ, fnv %016llx\n", path, (unsigned long long)rlen,
            (unsigned long long)roff, ans(r), (unsigned long long)bad,
            (unsigned long long)(r > 0 ? fnv(FNV0, buf, (size_t)r) : FNV0));
    }
    close(fd);
}

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}

static void fill_mib(uint64_t mib) {
    uint64_t *w = (uint64_t *)buf;
    for (uint64_t k = 0; k < (1u << 20) / 8; k++) {
        uint64_t s = mib * 2048 + k / 64;
        w[k] = ((s << 32) | (k % 64)) ^ 0x7061786469736b00ULL;
    }
}

static void speed(const char *path, uint64_t mibs) {
    int fd = open(path, O_RDWR);
    if (fd < 0) { say("speed %s: open %s\n", path, ans(fd)); return; }
    double t0 = now();
    uint64_t wrote = 0;
    for (uint64_t m = 0; m < mibs; m++) {
        fill_mib(m);
        ssize_t r = pwrite(fd, buf, 1u << 20, (off_t)(m << 20));
        if (r != (1 << 20)) { say("speed %s: write at %llu MiB: %s\n", path, (unsigned long long)m, ans(r)); break; }
        wrote++;
    }
    int f = fsync(fd);
    double t1 = now();
    say("speed %s: wrote %llu MiB in 1 MiB writes, fsync %s\n", path, (unsigned long long)wrote, ans(f));
    /* the read-back from the device, not the guest's page cache */
    say("speed %s: BLKFLSBUF %s\n", path, ans(ioctl(fd, BLKFLSBUF, 0)));
    uint64_t got = 0, bad = 0;
    unsigned char *want = buf + (1u << 20);
    for (uint64_t m = 0; m < mibs; m++) {
        ssize_t r = pread(fd, want, 1u << 20, (off_t)(m << 20));
        if (r != (1 << 20)) { say("speed %s: read at %llu MiB: %s\n", path, (unsigned long long)m, ans(r)); break; }
        fill_mib(m);
        for (uint64_t s = 0; s < 2048; s++)
            if (memcmp(buf + s * 512, want + s * 512, 512)) bad++;
        got++;
    }
    double t2 = now();
    say("speed %s: read back %llu MiB in 1 MiB reads, %llu sectors differ\n", path, (unsigned long long)got, (unsigned long long)bad);
    double mb = (double)(wrote << 20) / 1e6, mr = (double)(got << 20) / 1e6;
    say("== time\n");
    say("speed %s: time: write %.3f s, %.1f MB/s; read and check %.3f s, %.1f MB/s\n", path, t1 - t0,
        t1 > t0 ? mb / (t1 - t0) : 0.0, t2 - t1, t2 > t1 ? mr / (t2 - t1) : 0.0);
    close(fd);
}

static void sum(const char *path, uint64_t off, uint64_t len) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) { say("sum %s: open %s\n", path, ans(fd)); return; }
    uint64_t h = FNV0, done = 0;
    long last = 0;
    while (done < len) {
        uint64_t n = len - done < 131072 ? len - done : 131072;
        ssize_t r = pread(fd, buf, n, (off_t)(off + done));
        if (r <= 0) { last = r; break; }
        h = fnv(h, buf, (size_t)r);
        done += (uint64_t)r;
    }
    say("sum %s: %llu at %llu: %llu read%s%s, fnv %016llx\n", path, (unsigned long long)len, (unsigned long long)off,
        (unsigned long long)done, last < 0 ? ", then " : "", last < 0 ? ans(last) : "", (unsigned long long)h);
    close(fd);
}

int main(int argc, char **argv) {
    buf = malloc(BUFSZ);
    if (!buf) return 2;
    if (argc == 4 && !strcmp(argv[1], "sizes")) { sizes(argv[2], strtoull(argv[3], 0, 0)); return 0; }
    if (argc == 4 && !strcmp(argv[1], "speed")) { speed(argv[2], strtoull(argv[3], 0, 0)); return 0; }
    if (argc == 5 && !strcmp(argv[1], "sum")) { sum(argv[2], strtoull(argv[3], 0, 0), strtoull(argv[4], 0, 0)); return 0; }
    fprintf(stderr, "usage: nvme sizes PATH SEED | speed PATH MIB | sum PATH OFF LEN\n");
    return 2;
}
