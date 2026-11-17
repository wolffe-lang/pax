/* orphan.c — an adopted child that exits only after the row observes it.
 *
 *   orphan RELEASE_FILE                 fork, setsid, print READY PID SID
 *   orphan inspect PID                  print PRESENT stat or GONE PID
 *   orphan release PID RELEASE_FILE     release, require gone within 5000 ms
 *
 * A pipe makes the start handshake explicit. The parent exits without waiting
 * for the child; it is adopted by pid 1. The child waits for RELEASE_FILE, then
 * exits. Inspection accepts only ENOENT as absence and first checks that
 * /proc/1/stat is readable. Errors never mean reaped. The release command polls
 * using guest CLOCK_MONOTONIC, while the console's original shell remains alive.
 *
 * Written from fork(2), setsid(2), pipe(2), open(2), read(2), clock_gettime(2),
 * proc_pid_stat(5) and POSIX. No other implementation's source was consulted.
 */
#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static int stat_text(pid_t pid, char *text, size_t size)
{
    char path[64];
    snprintf(path, sizeof(path), "/proc/%d/stat", (int)pid);
    FILE *f = fopen(path, "r");
    if (!f) {
        if (errno == ENOENT)
            return 0;
        perror(path);
        return -1;
    }
    if (!fgets(text, (int)size, f)) {
        fprintf(stderr, "orphan: unreadable %s\n", path);
        fclose(f);
        return -1;
    }
    int closed = fclose(f);
    char *end;
    long got = strtol(text, &end, 10);
    if (closed != 0 || got != pid || end[0] != ' ' || end[1] != '(' || !strrchr(end, ')')) {
        fprintf(stderr, "orphan: malformed %s\n", path);
        return -1;
    }
    return 1;
}

static int inspect(pid_t pid, char *text, size_t size)
{
    char init[1024];
    if (stat_text(1, init, sizeof(init)) != 1) {
        fprintf(stderr, "orphan: pid 1 cannot be observed\n");
        return -1;
    }
    return stat_text(pid, text, size);
}

static long long millis(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0)
        return -1;
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static int start(const char *release)
{
    if (access(release, F_OK) == 0 || errno != ENOENT) {
        fprintf(stderr, "orphan: release path must not exist\n");
        return 2;
    }
    int p[2];
    if (pipe(p) != 0) {
        perror("orphan: pipe");
        return 2;
    }
    pid_t c = fork();
    if (c < 0) {
        perror("orphan: fork");
        close(p[0]);
        close(p[1]);
        return 2;
    }
    if (c == 0) {
        close(p[0]);
        pid_t sid = setsid();
        int null = open("/dev/null", O_RDWR);
        if (sid < 0 || null < 0)
            _exit(2);
        if (dup2(null, 0) < 0 || dup2(null, 1) < 0 || dup2(null, 2) < 0)
            _exit(2);
        if (null > 2)
            close(null);
        if (write(p[1], &sid, sizeof(sid)) != sizeof(sid))
            _exit(2);
        close(p[1]);
        for (;;) {
            if (access(release, F_OK) == 0)
                _exit(0);
            if (errno != ENOENT)
                _exit(2);
            usleep(10000);
        }
    }
    close(p[1]);
    pid_t sid = 0;
    ssize_t n = read(p[0], &sid, sizeof(sid));
    close(p[0]);
    if (n != sizeof(sid) || sid != c) {
        fprintf(stderr, "orphan: child did not report its own session\n");
        return 2;
    }
    printf("READY %d %d\n", (int)c, (int)sid);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc == 2)
        return start(argv[1]);
    if ((argc != 3 || strcmp(argv[1], "inspect") != 0) &&
        (argc != 4 || strcmp(argv[1], "release") != 0)) {
        fprintf(stderr, "usage: orphan RELEASE_FILE | inspect PID | release PID RELEASE_FILE\n");
        return 2;
    }
    char *end;
    long value = strtol(argv[2], &end, 10);
    if (!argv[2][0] || *end || value <= 1 || value > INT_MAX)
        return 2;
    pid_t pid = (pid_t)value;
    char text[1024];
    int state = inspect(pid, text, sizeof(text));
    if (state < 0)
        return 2;
    if (argc == 3) {
        if (state)
            printf("PRESENT %s", text);
        else
            printf("GONE %d\n", (int)pid);
        return 0;
    }
    if (state != 1) {
        fprintf(stderr, "orphan: child disappeared before release\n");
        return 2;
    }
    int fd = open(argv[3], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0 || close(fd) != 0) {
        perror("orphan: release");
        return 2;
    }
    long long begin = millis();
    if (begin < 0)
        return 2;
    for (;;) {
        state = inspect(pid, text, sizeof(text));
        if (state < 0)
            return 2;
        if (!state) {
            printf("GONE %d\n", (int)pid);
            return 0;
        }
        long long now = millis();
        if (now < 0)
            return 2;
        if (now - begin >= 5000) {
            printf("TIMEOUT 5000 %s", text);
            return 1;
        }
        usleep(10000);
    }
}
