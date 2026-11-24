/* The init restart row: timestamp immediately before signalling its recorded
 * guest manager pid. CLOCK_MONOTONIC and /proc/PID/stat starttime share a base
 * (proc_pid_stat(5), clock_gettime(2), kill(2)); PAX stat ticks are 100 Hz.
 * No host processes are inspected or signalled by this guest-only probe. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    char *end = NULL;
    errno = 0;
    long pid = argc == 2 ? strtol(argv[1], &end, 10) : 0;
    if (argc != 2 || errno || !end || *end || pid <= 1 || pid > INT_MAX) {
        fprintf(stderr, "init-clock: one recorded guest pid greater than 1 required\n");
        return 2;
    }
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0) {
        perror("init-clock: clock_gettime");
        return 1;
    }
    if (kill((pid_t)pid, SIGKILL) != 0) {
        perror("init-clock: kill");
        return 1;
    }
    printf("KILL-MS %lld\n", (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000);
    return 0;
}
