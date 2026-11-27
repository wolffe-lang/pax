/* tests/mpx6-smp.d/bench.c: SMP-BUILD's batches (the processor census's baseline, again). One job,
 * then JOBS at once, three interleaved rounds, each job the pinned den's real pack and index
 * construction (`pack-objects --window=0`) over 2 MiB of incompressible objects in a repository of
 * its own (tests/mpx6-smp.d/fixture.py). The host times each batch from its BENCH BEGIN and END lines
 * (tests/mpx6-smp.d/build.py, the census's method); the END line also carries the guest's own wall from
 * the TSC (calibrated against CLOCK_MONOTONIC over 300 ms), the children's CPU time and peak RSS.
 * Every pack and index is named with its stored trailer; rows.py holds them to the host oracle.
 * On a test kernel (tests/mpx6-smp's SMP_BUILD_KERNEL=test) /proc/pax-klock holds the kernel lock's ledger: it is read
 * just before each batch's BEGIN line and just after its END line, and both reads are printed after the END line
 * (BENCH KLOCK blocks), outside the host's timing; rows.py prints the batches' spin and holds. On a shipped kernel the
 * file is one line and nothing more is printed.
 *
 *   /bin/bench [JOBS]          (4 by default; the fixture holds batches of 1 and 4)
 */
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <time.h>

static void fail(const char *why) { perror(why); exit(2); }
static unsigned long rdtsc(void) { unsigned lo, hi; __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi)); return lo | (unsigned long)hi << 32; }
static unsigned long mono_ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000000000ul + t.tv_nsec; }
static unsigned long tsc_hz = 1;

static void child(const char *dir) {
    if (chdir(dir)) fail("chdir");
    int in = open("list", O_RDONLY);
    if (in < 0 || dup2(in, 0) < 0) fail("input");
    close(in);
    char *args[] = { "/bin/den", "pack-objects", "--window=0", ".git/objects/pack/pack", 0 };
    execv(args[0], args);
    fail("exec");
}
static void identity(const char *dir) {
    char path[256];
    snprintf(path, sizeof path, "%.63s/.git/objects/pack", dir);
    DIR *d = opendir(path);
    if (!d) fail("opendir");
    struct dirent *e;
    int files = 0;
    while ((e = readdir(d))) {
        size_t n = strlen(e->d_name);
        if (n < 5 || (strcmp(e->d_name + n - 4, ".idx") && strcmp(e->d_name + n - 5, ".pack"))) continue;
        char file[512];
        snprintf(file, sizeof file, "%s/%s", path, e->d_name);
        int fd = open(file, O_RDONLY);
        unsigned char digest[20];
        if (fd < 0 || lseek(fd, -20, SEEK_END) < 0 || read(fd, digest, 20) != 20) fail("trailer");
        close(fd);
        printf("OUTPUT %s %s trailer-sha1=", dir, e->d_name);
        for (int k = 0; k < 20; k++) printf("%02x", digest[k]);
        puts("");
        files++;
    }
    closedir(d);
    if (files != 2) fail("pack pair");
}
static char kl_before[16384], kl_after[16384];
static int klock_read(char *b) {
    int fd = open("/proc/pax-klock", O_RDONLY);
    size_t n = 0;
    if (fd < 0) { b[0] = 0; return 0; }
    for (;;) {
        ssize_t k = read(fd, b + n, sizeof kl_before - 1 - n);
        if (k <= 0) break;
        n += (size_t)k;
        if (n >= sizeof kl_before - 1) break;
    }
    close(fd);
    b[n] = 0;
    return strncmp(b, "klock-ledger tsc ", 17) == 0;
}
static void klock_print(int round, int j, const char *at, const char *b) {
    printf("BENCH KLOCK round=%d jobs=%d at=%s begin\n", round, j, at);
    fputs(b, stdout);
    printf("BENCH KLOCK round=%d jobs=%d at=%s end\n", round, j, at);
}
static void active(void) {
    char b[4096];
    int fd = open("/proc/pax-cpus", O_RDONLY);
    ssize_t n = fd < 0 ? -1 : read(fd, b, sizeof b - 1);
    if (fd >= 0) close(fd);
    if (n <= 0) { puts("BENCH ACTIVE -"); return; }
    b[n] = 0;
    char *a = strstr(b, "\nactive ");
    printf("BENCH ACTIVE %ld\n", a ? strtol(a + 8, 0, 10) : -1L);
}
int main(int argc, char **argv) {
    setvbuf(stdout, 0, _IONBF, 0);
    int jobs = argc > 1 ? atoi(argv[1]) : 4;
    if (jobs != 4) jobs = 4; /* the fixture holds batches of 1 and 4 */
    unsigned long a = mono_ns(), b, c;
    do { b = mono_ns(); } while (b == a);
    unsigned long t0 = rdtsc();
    do { c = mono_ns(); } while (c < b + 300000000ul);
    tsc_hz = (rdtsc() - t0) * 1000000000ul / (c - b);
    printf("BENCH TSC-HZ %lu\n", tsc_hz);
    active();
    for (int round = 0; round < 3; round++)
        for (int j = 1; j <= jobs; j += jobs - 1) {
            pid_t p[4];
            char dirs[4][64];
            int ledger = klock_read(kl_before);
            printf("BENCH BEGIN round=%d jobs=%d\n", round, j);
            unsigned long s = rdtsc();
            for (int i = 0; i < j; i++) {
                snprintf(dirs[i], sizeof dirs[i], "/bench/r%d-j%d-%d", round, j, i);
                p[i] = fork();
                if (p[i] < 0) fail("fork");
                if (!p[i]) child(dirs[i]);
            }
            long user = 0, sys = 0, rss = 0;
            for (int i = 0; i < j; i++) {
                int status;
                struct rusage r;
                if (wait4(p[i], &status, 0, &r) != p[i] || !WIFEXITED(status) || WEXITSTATUS(status)) fail("child");
                user += r.ru_utime.tv_sec * 1000000 + r.ru_utime.tv_usec;
                sys += r.ru_stime.tv_sec * 1000000 + r.ru_stime.tv_usec;
                if (r.ru_maxrss > rss) rss = r.ru_maxrss;
            }
            unsigned long wall = (rdtsc() - s) / (tsc_hz / 1000000);
            printf("BENCH END round=%d jobs=%d user_us=%ld sys_us=%ld maxrss_kib=%ld guest_wall_us=%lu\n", round, j, user, sys, rss, wall);
            if (ledger && klock_read(kl_after)) {
                klock_print(round, j, "before", kl_before);
                klock_print(round, j, "after", kl_after);
            }
            for (int i = 0; i < j; i++) identity(dirs[i]);
            if (j == jobs) break;
        }
    active();
    puts("BENCH DONE");
    return 0;
}
