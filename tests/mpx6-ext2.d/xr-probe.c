/* xr-probe: the guest half of tests/mpx6-ext2's extent read rows (XR).
 *
 * It reads /etc/xr/plan, one operation a line, and prints what each one
 * observed, `XRO <op> <args> rc=<r> errno=<e> ...`, never a verdict: the
 * host (tests/mpx6-ext2.d/xr-judge.py) holds every expectation. Built
 * static with the same Ubuntu toolchain as the other probes. SHA-256 is
 * FIPS 180-4's, written from the standard.
 *
 * Operations:
 *   mount SRC DST TYPE ro|rw     mount(2)
 *   umount DST                   umount2(2)
 *   remount DST                  mount(2) with MS_REMOUNT, read-write
 *   mounts TAG                   /proc/self/mounts and mountinfo, each line
 *   file PATH                    open, then read to the end in 3000-byte
 *                                pieces: bytes and sha256 (at=open|read)
 *   read PATH OFF LEN            pread from OFF until LEN bytes or the end
 *   stat PATH                    lstat: mode, size, nlink
 *   list DIR                     every name (sorted), then the count; a
 *                                readdir error is the list's errno
 *   readlink PATH                the target
 *   mmap PATH LEN                in a child: map LEN bytes and hash them;
 *                                the parent says how the child ended
 *   tries DIR                    every mutation a read-only mount refuses
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

typedef struct { uint32_t h[8]; uint64_t n; uint8_t b[64]; size_t k; } sha;

static const uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

static uint32_t ror(uint32_t x, int r) { return (x >> r) | (x << (32 - r)); }

static void block(sha *s, const uint8_t *p) {
    uint32_t w[64], a, b, c, d, e, f, g, h;
    for (int i = 0; i < 16; i++)
        w[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 | (uint32_t)p[4 * i + 2] << 8 | p[4 * i + 3];
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ror(w[i - 15], 7) ^ ror(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ror(w[i - 2], 17) ^ ror(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t t1 = h + (ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i];
        uint32_t t2 = (ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}

static void sha_init(sha *s) {
    static const uint32_t iv[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                                   0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    memcpy(s->h, iv, sizeof iv);
    s->n = 0;
    s->k = 0;
}

static void sha_add(sha *s, const uint8_t *p, size_t len) {
    s->n += len;
    while (len) {
        size_t take = 64 - s->k < len ? 64 - s->k : len;
        memcpy(s->b + s->k, p, take);
        s->k += take; p += take; len -= take;
        if (s->k == 64) { block(s, s->b); s->k = 0; }
    }
}

static void sha_hex(sha *s, char out[65]) {
    uint64_t bits = s->n * 8;
    uint8_t pad = 0x80, zero = 0, len[8];
    sha_add(s, &pad, 1);
    while (s->k != 56) sha_add(s, &zero, 1);
    for (int i = 0; i < 8; i++) len[i] = (uint8_t)(bits >> (56 - 8 * i));
    sha_add(s, len, 8);
    for (int i = 0; i < 8; i++) sprintf(out + 8 * i, "%08x", s->h[i]);
}

static char buf[3000];

static void say(const char *what, int rc, int err, const char *more) {
    printf("XRO %s rc=%d errno=%d%s%s\n", what, rc, rc < 0 ? err : 0, more[0] ? " " : "", more);
    fflush(stdout);
}

/* Read fd from off (or the current offset when off < 0) until want bytes
 * or the end; the hash and count in *s, *got. 0 or the failing errno. */
static int drain(int fd, long long off, long long want, sha *s, long long *got) {
    *got = 0;
    for (;;) {
        size_t ask = sizeof buf;
        if (want >= 0 && want - *got < (long long)ask) ask = (size_t)(want - *got);
        if (ask == 0) return 0;
        errno = 0;
        ssize_t n = off < 0 ? read(fd, buf, ask) : pread(fd, buf, ask, off + *got);
        if (n < 0) return errno ? errno : EIO;
        if (n == 0) return 0;
        sha_add(s, (uint8_t *)buf, (size_t)n);
        *got += n;
    }
}

static void op_file(const char *what, const char *path, long long off, long long want) {
    char hex[65], more[160];
    sha s;
    errno = 0;
    int fd = open(path, O_RDONLY);
    if (fd < 0) { say(what, -1, errno, "at=open"); return; }
    sha_init(&s);
    long long got;
    int e = drain(fd, off, want, &s, &got);
    close(fd);
    sha_hex(&s, hex);
    snprintf(more, sizeof more, "at=read bytes=%lld sha256=%s", got, hex);
    say(what, e ? -1 : 0, e, more);
}

static int cmp(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }

static void op_list(const char *what, const char *dir) {
    char *names[4096];
    int n = 0, err = 0;
    errno = 0;
    DIR *d = opendir(dir);
    if (!d) { say(what, -1, errno, "at=open"); return; }
    for (;;) {
        errno = 0;
        struct dirent *e = readdir(d);
        if (!e) { err = errno; break; }
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, "..")) continue;
        if (n < 4096) names[n++] = strdup(e->d_name);
    }
    closedir(d);
    qsort(names, (size_t)n, sizeof names[0], cmp);
    for (int i = 0; i < n; i++) { printf("XRO ent %s %s\n", dir, names[i]); free(names[i]); }
    char more[64];
    snprintf(more, sizeof more, "count=%d", n);
    say(what, err ? -1 : 0, err, more);
}

static void op_mmap(const char *what, const char *path, long long len) {
    fflush(stdout);
    pid_t c = fork();
    if (c == 0) {
        int fd = open(path, O_RDONLY);
        if (fd < 0) _exit(100);
        void *p = mmap(NULL, (size_t)len, PROT_READ, MAP_PRIVATE, fd, 0);
        if (p == MAP_FAILED) _exit(101);
        sha s;
        char hex[65];
        sha_init(&s);
        sha_add(&s, p, (size_t)len);
        sha_hex(&s, hex);
        printf("XRO mmap-bytes %s sha256=%s\n", path, hex);
        fflush(stdout);
        _exit(0);
    }
    int st = 0;
    waitpid(c, &st, 0);
    char more[64];
    snprintf(more, sizeof more, "exit=%d signal=%d", WIFEXITED(st) ? WEXITSTATUS(st) : -1,
             WIFSIGNALED(st) ? WTERMSIG(st) : 0);
    say(what, 0, 0, more);
}

static void try1(const char *dir, const char *name, int rc, int err) {
    char what[600];
    snprintf(what, sizeof what, "try %s %s", dir, name);
    say(what, rc < 0 ? -1 : 0, err, "");
}

/* errno is read at once, before anything else can move it. */
#define TRY(name, expr) do { errno = 0; int r_ = (expr); int e_ = errno; try1(dir, name, r_, e_); } while (0)

static void op_tries(const char *dir) {
    char a[512], b[512], f[512];
    snprintf(a, sizeof a, "%s/xr-new", dir);
    snprintf(b, sizeof b, "%s/xr-new2", dir);
    snprintf(f, sizeof f, "%s/small", dir);
    struct timespec ts[2] = {{1, 0}, {1, 0}};
    int fd;
    errno = 0; fd = open(a, O_WRONLY | O_CREAT | O_EXCL, 0644); try1(dir, "create", fd, errno); if (fd >= 0) close(fd);
    errno = 0; fd = open(f, O_WRONLY); try1(dir, "open-write", fd, errno); if (fd >= 0) close(fd);
    TRY("truncate", truncate(f, 0));
    TRY("chmod", chmod(f, 0600));
    TRY("utimens", utimensat(AT_FDCWD, f, ts, 0));
    TRY("rename", rename(f, b));
    TRY("unlink", unlink(f));
    TRY("mkdir", mkdir(a, 0755));
    TRY("symlink", symlink("small", a));
    TRY("link", link(f, a));
    errno = 0;
    fd = open(f, O_RDONLY);
    if (fd >= 0) {
        errno = 0;
        void *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        try1(dir, "mmap-shared-write", p == MAP_FAILED ? -1 : 0, errno);
        if (p != MAP_FAILED) munmap(p, 4096);
        close(fd);
    } else {
        try1(dir, "mmap-shared-write", -1, errno);
    }
}

int main(void) {
    FILE *plan = fopen("/etc/xr/plan", "r");
    if (!plan) { printf("XRO-END no-plan errno=%d\n", errno); return 1; }
    char line[1024];
    while (fgets(line, sizeof line, plan)) {
        line[strcspn(line, "\n")] = 0;
        char op[32] = "", x[512] = "", y[512] = "", z[64] = "", w[16] = "";
        long long n1 = -1, n2 = -1;
        if (sscanf(line, "%31s", op) != 1 || op[0] == '#') continue;
        errno = 0;
        if (!strcmp(op, "mount") && sscanf(line, "%*s %511s %511s %63s %15s", x, y, z, w) == 4) {
            int rc = mount(x, y, z, strcmp(w, "ro") ? 0 : MS_RDONLY, NULL);
            say(line, rc, errno, "");
        } else if (!strcmp(op, "umount") && sscanf(line, "%*s %511s", x) == 1) {
            int rc = umount2(x, 0);
            say(line, rc, errno, "");
        } else if (!strcmp(op, "remount") && sscanf(line, "%*s %511s", x) == 1) {
            int rc = mount(NULL, x, NULL, MS_REMOUNT, NULL);
            say(line, rc, errno, "");
        } else if (!strcmp(op, "mounts") && sscanf(line, "%*s %511s", x) == 1) {
            const char *src[2] = {"/proc/self/mounts", "/proc/self/mountinfo"};
            for (int i = 0; i < 2; i++) {
                FILE *m = fopen(src[i], "r");
                if (!m) { say(src[i], -1, errno, ""); continue; }
                while (fgets(line, sizeof line, m)) printf("XRO %s %s %s", i ? "mountinfo" : "mounts", x, line);
                fclose(m);
            }
            fflush(stdout);
        } else if (!strcmp(op, "file") && sscanf(line, "%*s %511s", x) == 1) {
            op_file(line, x, -1, -1);
        } else if (!strcmp(op, "read") && sscanf(line, "%*s %511s %lld %lld", x, &n1, &n2) == 3) {
            op_file(line, x, n1, n2);
        } else if (!strcmp(op, "stat") && sscanf(line, "%*s %511s", x) == 1) {
            struct stat st;
            int rc = lstat(x, &st);
            char more[128] = "";
            if (rc == 0)
                snprintf(more, sizeof more, "mode=%o size=%lld nlink=%lu", (unsigned)st.st_mode,
                         (long long)st.st_size, (unsigned long)st.st_nlink);
            say(line, rc, errno, more);
        } else if (!strcmp(op, "list") && sscanf(line, "%*s %511s", x) == 1) {
            op_list(line, x);
        } else if (!strcmp(op, "readlink") && sscanf(line, "%*s %511s", x) == 1) {
            ssize_t k = readlink(x, y, sizeof y - 1);
            int e = errno;
            char more[600] = "";
            if (k >= 0) { y[k] = 0; snprintf(more, sizeof more, "len=%zd target=%s", k, y); }
            say(line, k < 0 ? -1 : 0, e, more);
        } else if (!strcmp(op, "mmap") && sscanf(line, "%*s %511s %lld", x, &n1) == 2) {
            op_mmap(line, x, n1);
        } else if (!strcmp(op, "tries") && sscanf(line, "%*s %511s", x) == 1) {
            op_tries(x);
        } else {
            printf("XRO bad-plan-line %s\n", line);
        }
    }
    fclose(plan);
    sync();
    printf("XRO-END\n");
    fflush(stdout);
    return 0;
}
