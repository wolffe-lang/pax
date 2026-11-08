/* px108: ptime -- one command timed, for den's clones on PAX and on Linux.
 *
 *   ptime [-o FILE] [-w DIR] NAME PROG [ARG...]
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
 * that ended it. ptime's own status is the child's.
 *
 * -w DIR (a clone's destination) also samples the clone's stages while it
 * runs, every 250 ms, printing a line when what it sees changes (the pack's
 * size at most once a second):
 *
 *   ptime NAME: +<s> s pack <bytes> idx <0|1> index.lock <0|1> index <0|1>
 *
 * read from DIR/.git/objects/pack (the largest file there that does not end
 * in .idx, .rev or .keep: the pack as it grows) and DIR/.git/index[.lock].
 * Each sample is a few stat(2) calls and one directory read. Written from
 * clock_gettime(2), fork(2), execve(2), wait4(2) and getrusage(2).
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
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

static int exists(const char *p) {
    struct stat st;
    return stat(p, &st) == 0;
}

static void emit(const char *out, const char *line, int n) {
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
}

struct seen { long long pack; int idx, lock, index; double at; };

static void sample(const char *out, const char *name, const char *dir, double t0, struct seen *last) {
    char p[4096];
    struct seen s = {0, 0, 0, 0, 0};
    snprintf(p, sizeof p, "%s/.git/objects/pack", dir);
    DIR *d = opendir(p);
    if (d) {
        struct dirent *e;
        while ((e = readdir(d)) != NULL) {
            size_t l = strlen(e->d_name);
            if (e->d_name[0] == '.') continue;
            if (l > 4 && strcmp(e->d_name + l - 4, ".idx") == 0) { s.idx = 1; continue; }
            if (l > 4 && (strcmp(e->d_name + l - 4, ".rev") == 0)) continue;
            if (l > 5 && strcmp(e->d_name + l - 5, ".keep") == 0) continue;
            char f[8192];
            struct stat st;
            snprintf(f, sizeof f, "%s/%s", p, e->d_name);
            if (stat(f, &st) == 0 && st.st_size > s.pack) s.pack = st.st_size;
        }
        closedir(d);
    }
    snprintf(p, sizeof p, "%s/.git/index.lock", dir);
    s.lock = exists(p);
    snprintf(p, sizeof p, "%s/.git/index", dir);
    s.index = exists(p);
    double t = now() - t0;
    int changed = s.idx != last->idx || s.lock != last->lock || s.index != last->index ||
                  (s.pack != last->pack && t - last->at >= 1.0) || (s.pack != 0 && last->pack == 0);
    if (!changed) return;
    char line[512];
    int n = snprintf(line, sizeof line, "ptime %s: +%.2f s pack %lld idx %d index.lock %d index %d\n", name, t, s.pack,
                     s.idx, s.lock, s.index);
    emit(out, line, n);
    s.at = t;
    *last = s;
}

int main(int argc, char **argv) {
    const char *out = NULL, *watch = NULL;
    int i = 1;
    for (;;) {
        if (i + 1 < argc && strcmp(argv[i], "-o") == 0) {
            out = argv[i + 1];
            i += 2;
        } else if (i + 1 < argc && strcmp(argv[i], "-w") == 0) {
            watch = argv[i + 1];
            i += 2;
        } else {
            break;
        }
    }
    if (argc - i < 2) {
        fprintf(stderr, "usage: ptime [-o FILE] [-w DIR] NAME PROG [ARG...]\n");
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
    struct seen last = {0, 0, 0, 0, -1.0};
    for (;;) {
        pid_t r = wait4(pid, &status, watch ? WNOHANG : 0, &ru);
        if (r == pid) break;
        if (r < 0 && errno != EINTR) {
            fprintf(stderr, "ptime %s: wait4: %s\n", name, strerror(errno));
            return 2;
        }
        if (r == 0) {
            sample(out, name, watch, t0, &last);
            struct timespec q = {0, 250000000};
            nanosleep(&q, NULL);
        }
    }
    double wall = now() - t0;
    int code = WIFEXITED(status) ? WEXITSTATUS(status) : WIFSIGNALED(status) ? 128 + WTERMSIG(status) : 255;
    char line[512];
    int n = snprintf(line, sizeof line,
                     "ptime %s: wall %.3f s user %.3f sys %.3f maxrss %ld vcs %ld ics %ld exit %d\n", name, wall,
                     tv(ru.ru_utime), tv(ru.ru_stime), ru.ru_maxrss, ru.ru_nvcsw, ru.ru_nivcsw, code);
    emit(out, line, n);
    return code;
}
