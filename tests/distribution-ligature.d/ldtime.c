/* ldtime — px128's measuring linker for tests/distribution-ligature: a cc-shaped
 * WOLF_LD that runs LDTIME_REAL (an absolute path: /usr/bin/ligature, or
 * the image's link-only /usr/bin/cc, which execs /usr/bin/ld.lld in the
 * same process) with its own argv as its one child, then appends one line
 * to LDTIME_LOG:
 *
 *   ldtime LABEL wall_ms=W user_ms=U sys_ms=S maxrss_kib=R status=N
 *
 * W from CLOCK_MONOTONIC around the child; U, S and R from wait4's
 * rusage of that child (PAX: ru_maxrss the peak of the space's mapped
 * pages; Linux: the peak resident set). It exits with the child's
 * status (128 + the signal for a killed child), so `wolf build` sees
 * exactly what the linker did. Static, built on the host by the suite
 * with `cc -static`, never shipped in an image.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static long ms(struct timeval t) { return t.tv_sec * 1000L + t.tv_usec / 1000L; }

int main(int argc, char **argv) {
    const char *real = getenv("LDTIME_REAL"), *log = getenv("LDTIME_LOG");
    const char *label = getenv("LDTIME_LABEL");
    if (!real || real[0] != '/' || !log) {
        fprintf(stderr, "ldtime: LDTIME_REAL (an absolute path) and LDTIME_LOG are required\n");
        return 2;
    }
    (void)argc;
    struct timespec a, b;
    clock_gettime(CLOCK_MONOTONIC, &a);
    pid_t pid = fork();
    if (pid < 0) {
        fprintf(stderr, "ldtime: fork: %s\n", strerror(errno));
        return 2;
    }
    if (pid == 0) {
        argv[0] = (char *)real;
        execv(real, argv);
        fprintf(stderr, "ldtime: exec %s: %s\n", real, strerror(errno));
        _exit(127);
    }
    int st = 0;
    struct rusage ru;
    memset(&ru, 0, sizeof ru);
    while (wait4(pid, &st, 0, &ru) < 0) {
        if (errno != EINTR) {
            fprintf(stderr, "ldtime: wait4: %s\n", strerror(errno));
            return 2;
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &b);
    long wall = (b.tv_sec - a.tv_sec) * 1000L + (b.tv_nsec - a.tv_nsec) / 1000000L;
    int code = WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st);
    FILE *f = fopen(log, "a");
    if (f) {
        fprintf(f, "ldtime %s wall_ms=%ld user_ms=%ld sys_ms=%ld maxrss_kib=%ld status=%d\n",
                label ? label : real, wall, ms(ru.ru_utime), ms(ru.ru_stime), ru.ru_maxrss, code);
        fclose(f);
    }
    return code;
}
