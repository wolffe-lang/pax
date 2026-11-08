/* px108: ptime -- one command timed, for den's clones on PAX and on Linux.
 *
 *   ptime [-o FILE] NAME PROG [ARG...]
 *
 * Forks, execs PROG with ARGs (the path as given, no search), waits for it
 * with wait4 and prints one line, to standard error or appended to FILE:
 *
 *   ptime NAME: wall <s> s user <s> sys <s> maxrss <KiB> vcs <n> ics <n> exit <code>
 *
 * wall is CLOCK_MONOTONIC across the fork and the wait (PAX's moves in
 * 10 ms ticks, pax#299: rows read it in seconds); user, sys, maxrss and the
 * switches are wait4's rusage of the child, its reaped children folded in
 * (getrusage(2), wait4(2)); exit is the child's status, or 128 + the signal
 * that ended it. ptime's own status is the child's. Written from
 * clock_gettime(2), fork(2), execve(2), wait4(2) and getrusage(2).
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}

static double tv(struct timeval t) { return (double)t.tv_sec + (double)t.tv_usec / 1e6; }

int main(int argc, char **argv) {
    const char *out = NULL;
    int i = 1;
    if (i + 1 < argc && strcmp(argv[i], "-o") == 0) {
        out = argv[i + 1];
        i += 2;
    }
    if (argc - i < 2) {
        fprintf(stderr, "usage: ptime [-o FILE] NAME PROG [ARG...]\n");
        return 2;
    }
    const char *name = argv[i];
    char **child = argv + i + 1;
    double t0 = now();
    pid_t pid = fork();
    if (pid < 0) {
        fprintf(stderr, "ptime %s: fork: %s\n", name, strerror(errno));
        return 2;
    }
    if (pid == 0) {
        execv(child[0], child);
        fprintf(stderr, "ptime %s: exec %s: %s\n", name, child[0], strerror(errno));
        _exit(127);
    }
    int status = 0;
    struct rusage ru;
    memset(&ru, 0, sizeof ru);
    while (wait4(pid, &status, 0, &ru) < 0) {
        if (errno != EINTR) {
            fprintf(stderr, "ptime %s: wait4: %s\n", name, strerror(errno));
            return 2;
        }
    }
    double wall = now() - t0;
    int code = WIFEXITED(status) ? WEXITSTATUS(status) : WIFSIGNALED(status) ? 128 + WTERMSIG(status) : 255;
    char line[512];
    int n = snprintf(line, sizeof line,
                     "ptime %s: wall %.3f s user %.3f sys %.3f maxrss %ld vcs %ld ics %ld exit %d\n", name, wall,
                     tv(ru.ru_utime), tv(ru.ru_stime), ru.ru_maxrss, ru.ru_nvcsw, ru.ru_nivcsw, code);
    if (out) {
        int fd = open(out, O_WRONLY | O_CREAT | O_APPEND, 0644);
        if (fd >= 0) {
            ssize_t w = write(fd, line, (size_t)n);
            (void)w;
            close(fd);
        }
    } else {
        ssize_t w = write(2, line, (size_t)n);
        (void)w;
    }
    return code;
}
