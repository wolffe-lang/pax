/* dw02: entropy -- what PAX's random source answers a program, and whether
 * the program can tell what it got.
 *
 *   entropy           the measurement, then `entropy later` run two seconds on
 *   entropy later     the later process's part
 *
 * One line a fact on standard output, each `entropy: <phase> ...`, phase
 * `early` (the boot's first program, before anything else draws) or `later`:
 *
 *   entropy: early begin pid P
 *   entropy: early cpuid vendor V rdrand 0|1 rdseed 0|1
 *   entropy: early auxv at_random 0|1 nonzero 0|1 hieq 0|1
 *   entropy: early cap absent | entropy: early cap <a line of /proc/pax-random>
 *   entropy: early getrandom flags F n N ret R errno E words W hirep H
 *   entropy: early read PATH [nonblock] n N ret R errno E words W hirep H
 *   entropy: early malloc ok
 *   entropy: early child status S
 *   entropy: early end
 *
 * F is 0, NONBLOCK, RANDOM, RANDOM|NONBLOCK, INSECURE, INSECURE|NONBLOCK,
 * RANDOM|INSECURE or 0x8 (a bit getrandom(2) does not define); R the call's
 * return, E its errno's name (0 on success); W the whole 8-byte words
 * returned and H how many of them have the same top 32 bits as the word
 * before. Independent words repeat their top half once in 2^32; a word made
 * from a counter repeats it nearly always, so H tells the two sources apart
 * without printing a byte. `hieq` is the same test on AT_RANDOM's two halves.
 * No random byte is ever printed.
 *
 * Exit 0 when every line was printed, 1 when a call the probe needs to go on
 * failed (named). Written from getrandom(2), random(4), getauxval(3) and the
 * Intel SDM vol. 2 (CPUID); no kernel's or C library's source.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef GRND_NONBLOCK
#define GRND_NONBLOCK 0x1
#endif
#ifndef GRND_RANDOM
#define GRND_RANDOM 0x2
#endif
#ifndef GRND_INSECURE
#define GRND_INSECURE 0x4
#endif

static const char *phase = "early";
static unsigned char buf[1048576 + 64];

static const char *ename(int e) {
    switch (e) {
    case 0: return "0";
    case EAGAIN: return "EAGAIN";
    case EIO: return "EIO";
    case EINVAL: return "EINVAL";
    case EFAULT: return "EFAULT";
    case EINTR: return "EINTR";
    case ENOSYS: return "ENOSYS";
    case ENOENT: return "ENOENT";
    case EPERM: return "EPERM";
    case EACCES: return "EACCES";
    default: {
        static char n[16];
        snprintf(n, sizeof n, "%d", e);
        return n;
    }
    }
}

static const char *fname(unsigned f) {
    switch (f) {
    case 0: return "0";
    case GRND_NONBLOCK: return "NONBLOCK";
    case GRND_RANDOM: return "RANDOM";
    case GRND_RANDOM | GRND_NONBLOCK: return "RANDOM|NONBLOCK";
    case GRND_INSECURE: return "INSECURE";
    case GRND_INSECURE | GRND_NONBLOCK: return "INSECURE|NONBLOCK";
    case GRND_RANDOM | GRND_INSECURE: return "RANDOM|INSECURE";
    default: {
        static char n[16];
        snprintf(n, sizeof n, "0x%x", f);
        return n;
    }
    }
}

static uint64_t word(const unsigned char *p) {
    uint64_t w;
    memcpy(&w, p, 8);
    return w;
}

/* The whole words in [0, len) and how many repeat the top half of the one before. */
static void stats(long len, long *words, long *hirep) {
    long w = len > 0 ? len / 8 : 0, h = 0;
    for (long i = 1; i < w; i++)
        if ((word(buf + 8 * i) >> 32) == (word(buf + 8 * (i - 1)) >> 32))
            h++;
    *words = w;
    *hirep = h;
}

static void getrandom_row(long n, unsigned flags) {
    memset(buf, 0, (size_t)(n > 0 ? n : 0) + 8);
    long r = syscall(SYS_getrandom, buf, (size_t)n, flags);
    int e = r < 0 ? errno : 0;
    long w, h;
    stats(r, &w, &h);
    printf("entropy: %s getrandom flags %s n %ld ret %ld errno %s words %ld hirep %ld\n",
           phase, fname(flags), n, r, ename(e), w, h);
}

static void read_row(const char *path, int nonblock, long n) {
    int fd = open(path, O_RDONLY | O_CLOEXEC | (nonblock ? O_NONBLOCK : 0));
    if (fd < 0) {
        printf("entropy: %s read %s%s n %ld ret -1 errno %s open\n", phase, path, nonblock ? " nonblock" : "", n,
               ename(errno));
        return;
    }
    memset(buf, 0, (size_t)n + 8);
    long r = read(fd, buf, (size_t)n);
    int e = r < 0 ? errno : 0;
    close(fd);
    long w, h;
    stats(r, &w, &h);
    printf("entropy: %s read %s%s n %ld ret %ld errno %s words %ld hirep %ld\n", phase, path,
           nonblock ? " nonblock" : "", n, r, ename(e), w, h);
}

static void cpuid(unsigned leaf, unsigned sub, unsigned r[4]) {
    __asm__ volatile("cpuid" : "=a"(r[0]), "=b"(r[1]), "=c"(r[2]), "=d"(r[3]) : "a"(leaf), "c"(sub));
}

static void cpuid_row(void) {
    unsigned r[4], v[4];
    char vendor[13];
    cpuid(0, 0, v);
    memcpy(vendor, &v[1], 4);
    memcpy(vendor + 4, &v[3], 4);
    memcpy(vendor + 8, &v[2], 4);
    vendor[12] = 0;
    cpuid(1, 0, r);
    unsigned rdrand = (r[2] >> 30) & 1, rdseed = 0;
    if (v[0] >= 7) {
        cpuid(7, 0, r);
        rdseed = (r[1] >> 18) & 1;
    }
    printf("entropy: %s cpuid vendor %s rdrand %u rdseed %u\n", phase, vendor, rdrand, rdseed);
}

static void auxv_row(void) {
    const unsigned char *p = (const unsigned char *)getauxval(AT_RANDOM);
    int nz = 0, hieq = 0;
    if (p) {
        for (int i = 0; i < 16; i++)
            nz |= p[i] != 0;
        hieq = (word(p) >> 32) == (word(p + 8) >> 32);
    }
    printf("entropy: %s auxv at_random %d nonzero %d hieq %d\n", phase, p != 0, nz, hieq);
}

static void cap_rows(void) {
    FILE *f = fopen("/proc/pax-random", "re");
    if (!f) {
        printf("entropy: %s cap absent errno %s\n", phase, ename(errno));
        return;
    }
    char line[256];
    while (fgets(line, sizeof line, f)) {
        line[strcspn(line, "\n")] = 0;
        printf("entropy: %s cap %s\n", phase, line);
    }
    fclose(f);
}

static const unsigned FLAGS[] = {
    0, GRND_NONBLOCK, GRND_RANDOM, GRND_RANDOM | GRND_NONBLOCK, GRND_INSECURE, GRND_INSECURE | GRND_NONBLOCK,
    GRND_RANDOM | GRND_INSECURE, 0x8,
};

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc > 1 && strcmp(argv[1], "later") == 0)
        phase = "later";
    /* The very first thing: a strict and an insecure draw, before the probe's
     * own lines. glibc's start-up has already drawn its malloc key by now only
     * if it allocated; the lines below say what each call answered. */
    long r0 = syscall(SYS_getrandom, buf, 32, 0);
    int e0 = r0 < 0 ? errno : 0;
    long w0, h0;
    stats(r0, &w0, &h0);
    printf("entropy: %s begin pid %d\n", phase, (int)getpid());
    printf("entropy: %s getrandom first flags 0 n 32 ret %ld errno %s words %ld hirep %ld\n", phase, r0, ename(e0),
           w0, h0);
    auxv_row();
    if (strcmp(phase, "later") == 0) {
        getrandom_row(32, 0);
        getrandom_row(32, GRND_INSECURE);
        read_row("/dev/urandom", 0, 32);
        cap_rows();
        printf("entropy: %s end\n", phase);
        return 0;
    }
    cpuid_row();
    cap_rows();
    for (size_t i = 0; i < sizeof FLAGS / sizeof FLAGS[0]; i++)
        getrandom_row(32, FLAGS[i]);
    getrandom_row(4096, 0);
    getrandom_row(4096, GRND_INSECURE);
    static const long SIZES[] = {0, 1, 7, 256, 16384, 65536, 1048576};
    for (size_t i = 0; i < sizeof SIZES / sizeof SIZES[0]; i++)
        getrandom_row(SIZES[i], 0);
    getrandom_row(65536, GRND_INSECURE);
    read_row("/dev/urandom", 0, 4096);
    read_row("/dev/urandom", 0, 1048576);
    read_row("/dev/random", 0, 4096);
    read_row("/dev/random", 1, 32);
    read_row("/dev/urandom", 1, 32);
    void *m = malloc(100000);
    if (!m) {
        printf("entropy: %s malloc FAILED\n", phase);
        return 1;
    }
    memset(m, 1, 100000);
    free(m);
    printf("entropy: %s malloc ok\n", phase);
    cap_rows();
    fflush(stdout);
    sleep(2);
    pid_t c = fork();
    if (c < 0) {
        printf("entropy: %s fork FAILED errno %s\n", phase, ename(errno));
        return 1;
    }
    if (c == 0) {
        execl(argv[0][0] == '/' ? argv[0] : "/bin/entropy", "entropy", "later", (char *)0);
        printf("entropy: later exec FAILED errno %s\n", ename(errno));
        _exit(127);
    }
    int st = 0;
    if (waitpid(c, &st, 0) != c) {
        printf("entropy: %s wait FAILED errno %s\n", phase, ename(errno));
        return 1;
    }
    printf("entropy: %s child status %d\n", phase, st);
    printf("entropy: %s end\n", phase);
    return 0;
}
