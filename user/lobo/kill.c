/* user/lobo/kill.c — px25: kill(1)'s POSIX shape, for typing a signal at
 * lobo's processes from pelt (pelt has no `kill` builtin, boreutils no
 * `kill`): `kill -s NAME pid…`, `kill -NAME pid…`, `kill -N pid…`,
 * `kill pid…` (TERM). Each pid gets kill(2); a failure prints
 * `kill: <pid>: <strerror>` and the status is 1. The same static file
 * runs on Linux and on PAX (tests/mpx4-lobo). Written from kill(1p),
 * kill(2) and signal(7). */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const struct { const char *name; int sig; } SIGS[] = {
    {"HUP", SIGHUP}, {"INT", SIGINT}, {"QUIT", SIGQUIT}, {"KILL", SIGKILL},
    {"USR1", SIGUSR1}, {"USR2", SIGUSR2}, {"PIPE", SIGPIPE}, {"TERM", SIGTERM},
    {"CHLD", SIGCHLD}, {"CONT", SIGCONT},
};

static int by_name(const char *s) {
    if (strncmp(s, "SIG", 3) == 0) s += 3;
    for (size_t i = 0; i < sizeof SIGS / sizeof SIGS[0]; i++)
        if (strcmp(s, SIGS[i].name) == 0) return SIGS[i].sig;
    char *end;
    long v = strtol(s, &end, 10);
    if (*s && !*end && v >= 0 && v <= 64) return (int)v;
    return -1;
}

int main(int argc, char **argv) {
    int sig = SIGTERM, i = 1;
    if (i < argc && strcmp(argv[i], "-s") == 0 && i + 1 < argc) {
        sig = by_name(argv[i + 1]);
        i += 2;
    } else if (i < argc && argv[i][0] == '-' && argv[i][1] && strcmp(argv[i], "--") != 0) {
        sig = by_name(argv[i] + 1);
        i += 1;
    }
    if (i < argc && strcmp(argv[i], "--") == 0) i++;
    if (sig < 0 || i >= argc) {
        fprintf(stderr, "usage: kill [-s NAME | -NAME | -N] pid...\n");
        return 2;
    }
    int rc = 0;
    for (; i < argc; i++) {
        char *end;
        long pid = strtol(argv[i], &end, 10);
        if (!*argv[i] || *end) {
            fprintf(stderr, "kill: %s: not a pid\n", argv[i]);
            rc = 1;
            continue;
        }
        if (kill((pid_t)pid, sig) != 0) {
            fprintf(stderr, "kill: %ld: %s\n", pid, strerror(errno));
            rc = 1;
        }
    }
    return rc;
}
