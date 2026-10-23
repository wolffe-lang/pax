/* maps.c — px62's probe of mappings (pax#127, pax#128): one static glibc
   program that prints what it sees, run unmodified as the first program
   on Linux (its root a tmpfs, inside a throwaway container) and on PAX
   (tests/mpx3-maps), the two outputs compared byte for byte.

     maps          every row, in order (it works in /t/m, which it makes
                   and removes; /t is the image's)

   The rows, each something a kernel decides:
     mremap:  an anonymous mapping grown in place into a hole, shrunk,
              refused growth over a neighbour without MREMAP_MAYMOVE,
              moved with it (its bytes kept, the old range gone, the
              neighbour untouched), the allocator's own shape (151552
              to 299008 bytes, what px60 saw wolf's musl ask), a
              MAP_NORESERVE range and a PROT_NONE one moved, a file
              mapping grown, and the errnos mremap(2) names;
     private: MAP_PRIVATE of a regular file the way a linker reads its
              inputs (map, read sections, write a private patch, unmap):
              offsets, the partial last page, SIGBUS past the end,
              copy-on-write against the file and against a second
              mapping, a later write(2) seen by pages not yet copied,
              msync, fork, and the errnos mmap(2) names;
     shared:  MAP_SHARED of a file between a parent and a forked child
              (a counter both increment in turn, 2000 times), a write
              through the descriptor seen in the mapping, msync,
              MAP_SHARED|MAP_ANONYMOUS and /dev/zero across fork, two
              mappings of one file, and the file read back by
              /bin/cat after the child has ended;
     cut:     a file truncated under its mappings: SIGBUS past the new
              end in a shared, a private and a copied page, the partial
              page's tail zeroed, and the pages back when it grows.

   Built with the host's cc: `cc -static -O1` (tools/mkprobes). No address
   is printed (each kernel chooses its own); a line that starts with `~`
   is what PAX answers by name where Linux does something else (the two
   mremap flags PAX refuses), held to PAX's own text by the suite and
   not compared. Nothing here reads a kernel's or a libc's source: the
   calls are the man pages', the structures the public headers'. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <setjmp.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef MREMAP_DONTUNMAP
#define MREMAP_DONTUNMAP 4
#endif

#define P 4096L

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
/* a mapping call's answer: "-E", or "ok" */
static const char *m(void *p) {
    static char b[8][24];
    static int k;
    char *o = b[k++ & 7];
    if (p == MAP_FAILED) snprintf(o, 24, "%d", -errno);
    else snprintf(o, 24, "ok");
    return o;
}

static uint32_t fnv(const volatile unsigned char *p, long n) {
    uint32_t h = 2166136261u;
    for (long i = 0; i < n; i++) h = (h ^ p[i]) * 16777619u;
    return h;
}
static void fill(char *p, long n, int seed) {
    for (long i = 0; i < n; i++) p[i] = (char)((i * 7 + seed) & 0xff);
}
static int filled(const char *p, long n, int seed) {
    for (long i = 0; i < n; i++)
        if (p[i] != (char)((i * 7 + seed) & 0xff)) return 0;
    return 1;
}
static int zeros(const char *p, long n) {
    for (long i = 0; i < n; i++)
        if (p[i] != 0) return 0;
    return 1;
}
static const char *yes(int b) { return b ? "yes" : "no"; }

/* A touch of one byte: "ok", or the signal and its si_code. */
static sigjmp_buf jb;
static volatile int got_sig, got_code;
static void on_fault(int s, siginfo_t *i, void *u) {
    (void)u;
    got_sig = s;
    got_code = i->si_code;
    siglongjmp(jb, 1);
}
static const char *touch(volatile char *p, int wr) {
    static char b[8][48];
    static int k;
    char *o = b[k++ & 7];
    got_sig = 0;
    if (sigsetjmp(jb, 1) == 0) {
        if (wr) *p = *p;
        else (void)*p;
        snprintf(o, 48, "ok");
    } else {
        snprintf(o, 48, "signal %d code %d", got_sig, got_code);
    }
    return o;
}

static void ms(int n) {
    struct timespec t = { n / 1000, (n % 1000) * 1000000L };
    while (nanosleep(&t, &t) != 0 && errno == EINTR) {}
}

static long put(const char *path, const char *bytes, long n) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return -errno;
    long w = r(write(fd, bytes, n));
    close(fd);
    return w;
}
static uint32_t file_fnv(const char *path, long *size) {
    static unsigned char b[65536];
    int fd = open(path, O_RDONLY);
    *size = -1;
    if (fd < 0) return 0;
    long n = read(fd, b, sizeof b);
    close(fd);
    *size = n;
    return n > 0 ? fnv(b, n) : 0;
}

/* --- mremap (pax#127) ---------------------------------------------------- */

static void mremap_rows(void) {
    char *R = mmap(NULL, 64 * P, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    say("mremap: a 64-page PROT_NONE reservation to lay mappings out in: %s\n", m(R));
    char *A = mmap(R, 4 * P, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
    char *B = mmap(R + 4 * P, 2 * P, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
    say("mremap: A (4 pages) and B (2 pages) after it, fixed: %s %s\n", m(A), m(B));
    fill(A, 4 * P, 1);
    fill(B, 2 * P, 2);
    say("mremap: a hole of 4 pages after B: munmap %ld\n", r(munmap(R + 6 * P, 4 * P)));

    char *p = mremap(A, 4 * P, 8 * P, 0);
    say("mremap: A grown to 8 pages over B without MREMAP_MAYMOVE: %s\n", m(p));
    p = mremap(B, 2 * P, 6 * P, 0);
    say("mremap: B grown to 6 pages into the hole, in place: %s, same address %s, its bytes kept %s, the new pages zero %s\n",
        m(p), yes(p == B), yes(p != MAP_FAILED && filled(B, 2 * P, 2)), yes(p != MAP_FAILED && zeros(B + 2 * P, 4 * P)));
    say("mremap: B grown to 7 pages, past the hole into the reservation, without MREMAP_MAYMOVE: %s\n", m(mremap(B, 6 * P, 7 * P, 0)));
    if (p != MAP_FAILED) B[5 * P] = 'z';
    p = mremap(B, 6 * P, 1 * P, 0);
    say("mremap: B shrunk to 1 page: %s, same address %s, its first page kept %s; its second page: %s; its last old page: %s\n",
        m(p), yes(p == B), yes(filled(B, P, 2)), touch(B + P, 0), touch(B + 5 * P, 0));
    p = mremap(A, 4 * P, 8 * P, MREMAP_MAYMOVE);
    say("mremap: A grown to 8 pages with MREMAP_MAYMOVE: %s, moved %s, its bytes kept %s, the new pages zero %s\n",
        m(p), yes(p != A), yes(p != MAP_FAILED && filled(p, 4 * P, 1)), yes(p != MAP_FAILED && zeros(p + 4 * P, 4 * P)));
    say("mremap: where A was: %s; B, its neighbour, still its own %s\n", touch(A, 0), yes(filled(B, P, 2)));
    char *A2 = p;
    if (A2 != MAP_FAILED) {
        p = mremap(A2, 8 * P, 8 * P, MREMAP_MAYMOVE);
        say("mremap: the same size again: %s, same address %s\n", m(p), yes(p == A2));
        p = mremap(A2, 8 * P, 6 * P, MREMAP_MAYMOVE);
        say("mremap: shrunk to 6 pages with MREMAP_MAYMOVE: %s, same address %s, bytes kept %s; past it: %s\n",
            m(p), yes(p == A2), yes(filled(A2, 4 * P, 1)), touch(A2 + 6 * P, 0));
        p = mremap(A2, 5 * P + 1, 5 * P + 2, 0);
        say("mremap: sizes rounded up to pages (5 pages and a byte, 5 and two): %s, same address %s\n", m(p), yes(p == A2));
        p = mremap(A2 + P, 2 * P, 3 * P, MREMAP_MAYMOVE);
        say("mremap: the middle of a mapping moved: %s, its bytes kept %s; the page before it %s, the old middle %s, the page after %s\n",
            m(p), yes(p != MAP_FAILED && filled(p, 2 * P, (int)((1 + P * 7) & 0xff))), touch(A2, 0), touch(A2 + 2 * P, 0), touch(A2 + 3 * P, 0));
    }

    /* the errnos */
    char *E = mmap(R + 30 * P, 2 * P, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
    char *C = mmap(R + 20 * P, P, PROT_READ, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
    char *D = mmap(R + 21 * P, P, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
    say("mremap: E (2 pages), C (read-only) and D (read-write) after it: %s %s %s\n", m(E), m(C), m(D));
    say("mremap: an address off a page: %s\n", m(mremap(E + 1, P, P, 0)));
    say("mremap: a new size of 0: %s\n", m(mremap(E, P, 0, MREMAP_MAYMOVE)));
    say("mremap: a flag that is none (8): %s\n", m(mremap(E, P, P, 8)));
    say("mremap: MREMAP_FIXED without MREMAP_MAYMOVE: %s\n", m(mremap(E, P, P, MREMAP_FIXED, R + 40 * P)));
    say("mremap: MREMAP_DONTUNMAP without MREMAP_MAYMOVE: %s\n", m(mremap(E, P, P, MREMAP_DONTUNMAP)));
    munmap(R + 50 * P, P);
    say("mremap: an old range with nothing mapped: %s\n", m(mremap(R + 50 * P, P, 2 * P, MREMAP_MAYMOVE)));
    say("mremap: an old range over two mappings of two protections: %s\n", m(mremap(C, 2 * P, 4 * P, MREMAP_MAYMOVE)));
    say("mremap: an old range past its mapping's end, into the reservation: %s\n", m(mremap(E, 3 * P, 4 * P, MREMAP_MAYMOVE)));
    {
        const char *z1 = m(mremap(E, 0, 2 * P, MREMAP_MAYMOVE));
        const char *z2 = m(mremap(E, 0, 2 * P, 0));
        say("mremap: an old size of 0 on a private mapping: %s, without MREMAP_MAYMOVE %s\n", z1, z2);
    }
    say("mremap: E grown into the reservation without MREMAP_MAYMOVE: %s\n", m(mremap(E, 2 * P, 3 * P, 0)));
    p = mremap(E, 2 * P, 2 * P, MREMAP_MAYMOVE | MREMAP_FIXED, R + 40 * P);
    if (p == MAP_FAILED) say("~fixed: MREMAP_FIXED to a new address: %d\n", -errno);
    else say("~fixed: MREMAP_FIXED to a new address: moved there %s\n", yes(p == R + 40 * P));
    p = mremap(D, P, P, MREMAP_MAYMOVE | MREMAP_DONTUNMAP);
    if (p == MAP_FAILED) say("~dontunmap: MREMAP_DONTUNMAP: %d\n", -errno);
    else say("~dontunmap: MREMAP_DONTUNMAP: moved %s, the old page %s\n", yes(p != D), touch(D, 0));

    /* the allocator's own shape (px60's census: musl's grow path) */
    char *M = mmap(NULL, 151552, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    fill(M, 151552, 5);
    p = mremap(M, 151552, 299008, MREMAP_MAYMOVE);
    say("mremap: 151552 bytes grown to 299008 with MREMAP_MAYMOVE: %s, bytes kept %s, the rest zero %s\n",
        m(p), yes(p != MAP_FAILED && filled(p, 151552, 5)), yes(p != MAP_FAILED && zeros(p + 151552, 299008 - 151552)));
    if (p != MAP_FAILED) say("mremap: and unmapped: %ld\n", r(munmap(p, 299008)));

    /* a range backed on touch, and a reservation */
    char *L = mmap(NULL, 4 * P, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
    L[0] = 'x';
    L[3 * P] = 'y';
    p = mremap(L, 4 * P, 16 * P, MREMAP_MAYMOVE);
    /* in place or moved is each kernel's choice (what lies above it): when
       it moved, its old range must be gone */
    int gone = p == L || strcmp(touch(L, 0), "signal 11 code 1") == 0;
    say("mremap: a MAP_NORESERVE range touched twice, grown to 16 pages: %s, its two bytes kept %s, an untouched page zero %s, its old range gone if it moved %s\n",
        m(p), yes(p != MAP_FAILED && p[0] == 'x' && p[3 * P] == 'y'), yes(p != MAP_FAILED && p[10 * P] == 0), yes(gone));
    char *N = mmap(NULL, 2 * P, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    p = mremap(N, 2 * P, 4 * P, MREMAP_MAYMOVE);
    {
        const char *g = m(p);
        const char *t1 = p != MAP_FAILED ? touch(p + 3 * P, 0) : "-";
        long pr = p != MAP_FAILED ? r(mprotect(p, 4 * P, PROT_READ | PROT_WRITE)) : 0L;
        const char *t2 = p != MAP_FAILED ? touch(p + 3 * P, 1) : "-";
        say("mremap: a PROT_NONE range grown: %s; a touch of it %s; made read-write %ld, then written and read %s\n", g, t1, pr, t2);
    }
    say("mremap: done: %ld\n", r(munmap(R, 64 * P)));
}

/* --- MAP_PRIVATE of a file (pax#128 a) ---------------------------------- */

#define OBJ 10000L

static void private_rows(void) {
    static char obj[OBJ];
    fill(obj, OBJ, 3);
    say("private: an object file of %ld bytes: %ld\n", OBJ, put("/t/m/obj", obj, OBJ));
    int fd = open("/t/m/obj", O_RDONLY);
    char *p = mmap(NULL, 3 * P, PROT_READ, MAP_PRIVATE, fd, 0);
    say("private: mapped read-only, 3 pages: %s\n", m(p));
    say("private: its sections: %08x %08x %08x (the file's: %08x %08x %08x)\n", fnv((unsigned char *)p, P),
        fnv((unsigned char *)p + P, P), fnv((unsigned char *)p + 2 * P, OBJ - 2 * P), fnv((unsigned char *)obj, P),
        fnv((unsigned char *)obj + P, P), fnv((unsigned char *)obj + 2 * P, OBJ - 2 * P));
    say("private: the last byte %d, the partial page's tail zero %s\n", p[OBJ - 1], yes(zeros(p + OBJ, 3 * P - OBJ)));
    say("private: a write to a read-only mapping: %s\n", touch(p, 1));
    char *q = mmap(NULL, 4 * P, PROT_READ, MAP_PRIVATE, fd, 0);
    say("private: mapped 4 pages: %s; its third page (the file ends in it) %s; its fourth (past the end) %s\n", m(q),
        touch(q + 2 * P + 100, 0), touch(q + 3 * P, 0));
    char *o = mmap(NULL, P, PROT_READ, MAP_PRIVATE, fd, P);
    say("private: from offset 4096: %s, its bytes the file's second page %s\n", m(o), yes(o != MAP_FAILED && fnv((unsigned char *)o, P) == fnv((unsigned char *)obj + P, P)));
    char *o3 = mmap(NULL, P, PROT_READ, MAP_PRIVATE, fd, 3 * P);
    say("private: from an offset past the end: %s, a touch %s\n", m(o3), o3 != MAP_FAILED ? touch(o3, 0) : "-");
    say("private: an offset off a page: %s; a length of 0: %s\n", m(mmap(NULL, P, PROT_READ, MAP_PRIVATE, fd, 1)),
        m(mmap(NULL, 0, PROT_READ, MAP_PRIVATE, fd, 0)));

    /* the linker's private patch */
    char *w = mmap(NULL, OBJ, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, 0);
    say("private: mapped read-write from a read-only descriptor: %s\n", m(w));
    memcpy(w + 5000, "PATCHED-SECTION!", 16);
    char b[32];
    long n = pread(fd, b, 16, 5000);
    say("private: patched at 5000: the mapping %.16s, the file %s, the other mapping %s\n", w + 5000,
        yes(n == 16 && memcmp(b, obj + 5000, 16) == 0) ? "unchanged" : "CHANGED", yes(memcmp(p + 5000, obj + 5000, 16) == 0) ? "unchanged" : "CHANGED");
    int rw = open("/t/m/obj", O_RDWR);
    say("private: written through a descriptor at 100 and 4100: %ld %ld\n", r(pwrite(rw, "LATER", 5, 100)), r(pwrite(rw, "LATE2", 5, 4100)));
    say("private: seen at 100 by the read-only mapping %s and the patched one %s; at 4100 by the read-only one %s, not by the patched page %s\n",
        yes(memcmp(p + 100, "LATER", 5) == 0), yes(memcmp(w + 100, "LATER", 5) == 0), yes(memcmp(p + 4100, "LATE2", 5) == 0),
        yes(memcmp(w + 4100, "LATE2", 5) != 0));
    say("private: msync MS_SYNC %ld, MS_ASYNC %ld, MS_INVALIDATE %ld\n", r(msync(w, OBJ, MS_SYNC)), r(msync(w, OBJ, MS_ASYNC)),
        r(msync(w, P, MS_INVALIDATE)));
    say("private: msync MS_SYNC|MS_ASYNC %ld, off a page %ld, a flag that is none %ld, a length of 0 %ld\n",
        r(msync(w, P, MS_SYNC | MS_ASYNC)), r(msync(w + 1, P, MS_SYNC)), r(msync(w, P, 8)), r(msync(w, 0, MS_SYNC)));
    pid_t c = fork();
    if (c == 0) {
        say("private: the child sees the patch %s\n", yes(memcmp(w + 5000, "PATCHED-SECTION!", 16) == 0));
        w[0] = 'C';
        w[4096 * 2] = 'D';
        _exit(0);
    }
    int st = 0;
    waitpid(c, &st, 0);
    say("private: the child wrote its copy: status %d; the parent's bytes unchanged %s %s\n", st, yes(w[0] == obj[0]),
        yes(w[2 * P] == obj[2 * P]));
    {
        long pr = r(mprotect(p, P, PROT_READ | PROT_WRITE));
        const char *t1 = touch(p + 7, 1);
        p[7] = 'W';
        int same = pread(fd, b, 1, 7) == 1 && b[0] == obj[7];
        say("private: mprotect of the read-only mapping to read-write %ld, then a write %s; the file unchanged %s\n", pr, t1, yes(same));
    }
    char *f = mmap(NULL, P, PROT_READ, MAP_PRIVATE, fd, 0);
    char *f2 = mremap(f, P, 2 * P, MREMAP_MAYMOVE);
    say("private: a 1-page file mapping grown to 2 by mremap: %s, its second page the file's %s\n", m(f2),
        yes(f2 != MAP_FAILED && memcmp(f2 + P + 10, obj + P + 10, 50) == 0));
    {
        long u1 = r(munmap(w, OBJ)), u2 = r(munmap(p, 3 * P)), u3 = r(munmap(q, 4 * P));
        long u4 = r(munmap(o, P)), u5 = r(munmap(o3, P)), u6 = r(munmap(f2, 2 * P));
        const char *t1 = touch(w + 5000, 0);
        say("private: unmapped: %ld %ld %ld %ld %ld %ld; where the patch was: %s\n", u1, u2, u3, u4, u5, u6, t1);
    }

    /* what may not be mapped */
    int wr = open("/t/m/obj", O_WRONLY);
    say("private: a write-only descriptor: %s\n", m(mmap(NULL, P, PROT_READ, MAP_PRIVATE, wr, 0)));
    say("private: MAP_SHARED and PROT_WRITE of a read-only descriptor: %s\n", m(mmap(NULL, P, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)));
    char *s = mmap(NULL, P, PROT_READ, MAP_SHARED, fd, 0);
    say("private: MAP_SHARED and PROT_READ of it: %s; then mprotect to write %ld\n", m(s), s != MAP_FAILED ? r(mprotect(s, P, PROT_READ | PROT_WRITE)) : 0L);
    if (s != MAP_FAILED) munmap(s, P);
    int dir = open("/t/m", O_RDONLY | O_DIRECTORY);
    int pp[2];
    if (pipe(pp) != 0) pp[0] = pp[1] = -1;
    int nul = open("/dev/null", O_RDWR);
    say("private: a directory %s, a pipe %s, /dev/null %s\n", m(mmap(NULL, P, PROT_READ, MAP_PRIVATE, dir, 0)),
        m(mmap(NULL, P, PROT_READ, MAP_PRIVATE, pp[0], 0)), m(mmap(NULL, P, PROT_READ, MAP_PRIVATE, nul, 0)));
    say("private: descriptor -1 without MAP_ANONYMOUS %s, a closed one %s\n", m(mmap(NULL, P, PROT_READ, MAP_PRIVATE, -1, 0)),
        m(mmap(NULL, P, PROT_READ, MAP_PRIVATE, 900, 0)));
    say("private: neither MAP_PRIVATE nor MAP_SHARED: %s\n", m(mmap(NULL, P, PROT_READ, 0, fd, 0)));
    int z = open("/dev/zero", O_RDWR);
    char *zp = mmap(NULL, 2 * P, PROT_READ | PROT_WRITE, MAP_PRIVATE, z, 0);
    say("private: /dev/zero: %s, zero %s, written %s\n", m(zp), yes(zp != MAP_FAILED && zeros(zp, 2 * P)), zp != MAP_FAILED ? touch(zp + P, 1) : "-");
    if (zp != MAP_FAILED) munmap(zp, 2 * P);
    close(z);
    close(nul);
    close(pp[0]);
    close(pp[1]);
    close(dir);
    close(wr);
    close(rw);
    close(fd);
    long size;
    uint32_t h = file_fnv("/t/m/obj", &size);
    memcpy(obj + 100, "LATER", 5);
    memcpy(obj + 4100, "LATE2", 5);
    say("private: the file afterwards: %ld bytes, %08x, its two writes and nothing else %s\n", size, h,
        yes(size == OBJ && h == fnv((unsigned char *)obj, OBJ)));
    say("private: removed: %ld\n", r(unlink("/t/m/obj")));
}

/* --- MAP_SHARED (pax#128 b) --------------------------------------------- */

static const char SHARED_TEXT[] = "count=000000\nchild: ......\nwrite: ......\n";
#define TURNS 1000

static int bump(char *c) {
    int v = atoi(c + 6);
    char t[16];
    snprintf(t, sizeof t, "%06d", v + 1);
    memcpy(c + 6, t, 6);
    return v + 1;
}

static void shared_rows(void) {
    long len = (long)strlen(SHARED_TEXT);
    say("shared: a file of %ld bytes: %ld\n", len, put("/t/m/shared.txt", SHARED_TEXT, len));
    int fd = open("/t/m/shared.txt", O_RDWR);
    char *c = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    char *c2 = mmap(NULL, len, PROT_READ, MAP_SHARED, fd, 0);
    say("shared: mapped twice: %s %s\n", m(c), m(c2));
    int ab[2], ba[2];
    if (pipe(ab) != 0 || pipe(ba) != 0) say("shared: pipe failed\n");
    pid_t k = fork();
    if (k == 0) {
        char t;
        int v = 0;
        for (int i = 0; i < TURNS; i++) {
            if (read(ab[0], &t, 1) != 1) _exit(3);
            v = bump(c);
            if (write(ba[1], &t, 1) != 1) _exit(4);
        }
        memcpy(c + 13 + 7, "hello!", 6);
        say("shared: the child's last count %d\n", v);
        _exit(0);
    }
    char t = 'x';
    int v = 0;
    for (int i = 0; i < TURNS; i++) {
        v = bump(c);
        if (write(ab[1], &t, 1) != 1 || read(ba[0], &t, 1) != 1) break;
    }
    int st = 0;
    waitpid(k, &st, 0);
    say("shared: the parent's last count %d, the child's status %d; the count now %.12s, in the second mapping %.12s\n", v, st, c, c2);
    say("shared: what the child wrote: %.13s\n", c + 13);
    char b[64];
    long n = pread(fd, b, len, 0);
    say("shared: the file through the descriptor: %ld bytes, the mapping's %s\n", n, yes(n == len && memcmp(b, c, len) == 0));
    {
        long pw = r(pwrite(fd, "fd!!!!", 6, 34));
        say("shared: written through the descriptor at 34: %ld; seen in both mappings %s %s\n", pw,
            yes(memcmp(c + 34, "fd!!!!", 6) == 0), yes(memcmp(c2 + 34, "fd!!!!", 6) == 0));
    }
    say("shared: msync MS_SYNC %ld, MS_ASYNC %ld, MS_INVALIDATE %ld, a range with nothing mapped %ld\n", r(msync(c, len, MS_SYNC)),
        r(msync(c, len, MS_ASYNC)), r(msync(c, len, MS_INVALIDATE)), r(msync(c + 64 * P, P, MS_SYNC)));
    say("shared: a write to the read-only mapping: %s\n", touch(c2, 1));
    say("shared: unmapped %ld %ld\n", r(munmap(c, len)), r(munmap(c2, len)));
    close(fd);

    /* anonymous, /dev/zero, and a private control */
    char *a = mmap(NULL, 2 * P, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    char *v2 = mmap(NULL, P, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int zf = open("/dev/zero", O_RDWR);
    char *zz = mmap(NULL, P, PROT_READ | PROT_WRITE, MAP_SHARED, zf, 0);
    say("shared: MAP_SHARED|MAP_ANONYMOUS %s, zero %s; MAP_SHARED of /dev/zero %s; a private one %s\n", m(a), yes(a != MAP_FAILED && zeros(a, 2 * P)), m(zz), m(v2));
    a[0] = 'p';
    pid_t k2 = fork();
    if (k2 == 0) {
        say("shared: the child sees the parent's byte %s\n", yes(a[0] == 'p'));
        a[P] = 'c';
        zz[9] = 'z';
        v2[0] = 'q';
        _exit(0);
    }
    waitpid(k2, &st, 0);
    say("shared: after the child: its anonymous byte %s, its /dev/zero byte %s, its private byte %s\n", yes(a[P] == 'c'),
        yes(zz[9] == 'z'), v2[0] == 'q' ? "seen (WRONG)" : "not seen");
    say("shared: unmapped %ld %ld %ld\n", r(munmap(a, 2 * P)), r(munmap(zz, P)), r(munmap(v2, P)));
    close(zf);

    /* the file read back by cat, after every process that mapped it has ended */
    say("shared: cat of the file:\n");
    pid_t k3 = fork();
    if (k3 == 0) {
        execl("/bin/cat", "cat", "/t/m/shared.txt", (char *)0);
        _exit(127);
    }
    waitpid(k3, &st, 0);
    say("shared: cat's status %d\n", st);
    say("shared: removed: %ld\n", r(unlink("/t/m/shared.txt")));
}

/* --- a file cut under its mappings -------------------------------------- */

static void cut_rows(void) {
    static char three[3 * P];
    fill(three, 3 * P, 9);
    say("cut: a file of 3 pages: %ld\n", put("/t/m/cut", three, 3 * P));
    int fd = open("/t/m/cut", O_RDWR);
    char *s = mmap(NULL, 3 * P, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    char *p = mmap(NULL, 3 * P, PROT_READ, MAP_PRIVATE, fd, 0);
    char *w = mmap(NULL, 3 * P, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, 0);
    say("cut: mapped shared, private and private read-write: %s %s %s\n", m(s), m(p), m(w));
    say("cut: every third page read %s %s, the copy written %s\n", touch(s + 2 * P, 0), touch(p + 2 * P, 0), touch(w + 2 * P, 1));
    s[P + 100] = 'S';
    say("cut: truncated to 4106 bytes: %ld\n", r(ftruncate(fd, P + 10)));
    say("cut: the third page now: shared %s, private %s, the copy %s\n", touch(s + 2 * P, 0), touch(p + 2 * P, 0), touch(w + 2 * P, 0));
    say("cut: the second page (the new end is in it): %s, its byte 9 kept %s, its tail zero %s %s\n", touch(s + P + 5, 0),
        yes(s[P + 9] == three[P + 9]), yes(zeros(s + P + 10, P - 10)), yes(zeros(p + P + 10, P - 10)));
    {
        long gr = r(ftruncate(fd, 3 * P));
        const char *t1 = touch(s + 2 * P, 0);
        say("cut: grown back to 3 pages: %ld; the third page %s, zero %s\n", gr, t1, yes(zeros(s + 2 * P, P) && zeros(p + 2 * P, P)));
    }
    say("cut: unmapped %ld %ld %ld\n", r(munmap(s, 3 * P)), r(munmap(p, 3 * P)), r(munmap(w, 3 * P)));
    close(fd);
    say("cut: removed: %ld\n", r(unlink("/t/m/cut")));
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = on_fault;
    sa.sa_flags = SA_SIGINFO | SA_NODEFER;
    sigaction(SIGSEGV, &sa, NULL);
    sigaction(SIGBUS, &sa, NULL);
    umask(022);
    say("maps: /t/m made: %ld\n", r(mkdir("/t/m", 0755)));
    mremap_rows();
    private_rows();
    shared_rows();
    cut_rows();
    say("maps: /t/m removed: %ld\n", r(rmdir("/t/m")));
    say("maps: done\n");
    (void)ms;
    return 0;
}
