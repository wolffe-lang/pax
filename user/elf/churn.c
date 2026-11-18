/* churn.c — px164's probe of the block cache under a write-back ext2 mount:
   one static glibc program that keeps the cache turning over while inodes
   change, the way a large `status` beside a log writer does, so that a
   change ext2 makes to an inode's buffer can be checked on the disk
   afterwards (tests/mpx6-ext2-cache).

     churn scene TREE LOG SECS [HOLD]
                        an appender (a child) adds one numbered line to LOG
                        (O_APPEND, one write each, `line NNNNNNNN\n`) every
                        2 ms; the parent walks TREE once (getdents64,
                        lstat of every name, every regular file read to its
                        end: each read moves the file's access time, and each
                        directory read its own), then sleeps until SECS
                        seconds from the start (the flusher's turns with only
                        the appender running); then the appender is stopped
                        (SIGTERM, which it takes between two lines), waited
                        for, and sync(2) is called. With HOLD (MiB), the
                        parent first takes and touches anonymous memory until
                        /proc/meminfo's MemFree is at most HOLD MiB, and keeps
                        it to the end (the cache cannot grow past what it
                        holds then). Prints `scene: walked F files, D
                        directories, B bytes in MS ms`, `scene: appended N
                        lines`, `scene: held K MiB, MemFree M kB` and `scene:
                        end`.
     churn modes TREE MODE
                        chmod(2) of every regular file under TREE to MODE
                        (octal), one call each, in getdents64's order: each a
                        change to one inode; then sync(2). Prints `modes: F
                        files to MODE in MS ms` and `modes: end`.

   A line the program cannot finish is `churn: <what>: <errno name>` on
   stderr, and the exit status is 1. Built with the host's cc: `cc -static
   -O1` (tools/mkdiskprobe). The calls are the man pages'; nothing here
   reads a kernel's, a libc's or a file system's source. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

struct ent64 {
    uint64_t ino;
    int64_t off;
    unsigned short reclen;
    unsigned char type;
    char name[];
};

static long long now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static int fail(const char *what) {
    fprintf(stderr, "churn: %s: %s\n", what, strerrorname_np(errno) ? strerrorname_np(errno) : "?");
    return 1;
}

static long long files, dirs, bytes, changed;
static char buf[65536];

/* Every name under `path` (a directory): lstat'd; a regular file read to
   its end, or (mode != 0) chmod'ed to `mode`; a directory walked. */
static int walk(const char *path, mode_t mode) {
    int fd = open(path, O_RDONLY | O_DIRECTORY);
    if (fd < 0) return fail(path);
    dirs++;
    char db[8192];
    for (;;) {
        long n = syscall(SYS_getdents64, fd, db, sizeof db);
        if (n < 0) { close(fd); return fail("getdents64"); }
        if (n == 0) break;
        for (long at = 0; at < n;) {
            struct ent64 *e = (struct ent64 *)(db + at);
            at += e->reclen;
            if (strcmp(e->name, ".") == 0 || strcmp(e->name, "..") == 0) continue;
            char sub[4096];
            snprintf(sub, sizeof sub, "%s/%s", path, e->name);
            struct stat st;
            if (lstat(sub, &st) != 0) { close(fd); return fail(sub); }
            if (S_ISDIR(st.st_mode)) {
                if (walk(sub, mode) != 0) { close(fd); return 1; }
            } else if (S_ISREG(st.st_mode)) {
                files++;
                if (mode != 0) {
                    if (chmod(sub, mode) != 0) { close(fd); return fail(sub); }
                    changed++;
                    continue;
                }
                int f = open(sub, O_RDONLY);
                if (f < 0) { close(fd); return fail(sub); }
                for (;;) {
                    ssize_t r = read(f, buf, sizeof buf);
                    if (r < 0) { close(f); close(fd); return fail(sub); }
                    if (r == 0) break;
                    bytes += r;
                }
                close(f);
            }
        }
    }
    close(fd);
    return 0;
}

static volatile sig_atomic_t stop;
static void on_term(int s) { (void)s; stop = 1; }

/* The appender: one numbered line every 2 ms until SIGTERM; its count as
   its exit status's companion line on stdout. */
static int appender(const char *log) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_term;
    sigaction(SIGTERM, &sa, NULL);
    int f = open(log, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (f < 0) return fail(log);
    long n = 0;
    while (!stop) {
        char line[32];
        int k = snprintf(line, sizeof line, "line %08ld\n", n);
        if (write(f, line, (size_t)k) != k) { close(f); return fail("append"); }
        n++;
        struct timespec t = { 0, 2000000 };
        nanosleep(&t, NULL);
    }
    close(f);
    printf("scene: appended %ld lines\n", n);
    fflush(stdout);
    return 0;
}

static long mem_free_kb(void) {
    FILE *m = fopen("/proc/meminfo", "r");
    if (!m) return -1;
    char line[128];
    long kb = -1;
    while (fgets(line, sizeof line, m)) {
        if (sscanf(line, "MemFree: %ld kB", &kb) == 1) break;
    }
    fclose(m);
    return kb;
}

static int scene(const char *tree, const char *log, long secs, long hold) {
    long long t0 = now_ms();
    long held = 0;
    if (hold > 0) {
        long kb;
        while ((kb = mem_free_kb()) > hold * 1024) {
            char *p = mmap(NULL, 1 << 20, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if (p == MAP_FAILED) break;
            for (long i = 0; i < (1 << 20); i += 4096) p[i] = 1;
            held++;
        }
        printf("scene: held %ld MiB, MemFree %ld kB\n", held, mem_free_kb());
        fflush(stdout);
    }
    fflush(stdout);
    pid_t kid = fork();
    if (kid < 0) return fail("fork");
    if (kid == 0) _exit(appender(log));
    long long w0 = now_ms();
    if (walk(tree, 0) != 0) {
        kill(kid, SIGTERM);
        waitpid(kid, NULL, 0);
        return 1;
    }
    printf("scene: walked %lld files, %lld directories, %lld bytes in %lld ms\n", files, dirs, bytes, now_ms() - w0);
    fflush(stdout);
    while (now_ms() - t0 < secs * 1000) {
        struct timespec t = { 0, 100000000 };
        nanosleep(&t, NULL);
    }
    kill(kid, SIGTERM);
    int st = 0;
    if (waitpid(kid, &st, 0) != kid) return fail("waitpid");
    if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) {
        fprintf(stderr, "churn: the appender ended with status 0x%x\n", st);
        return 1;
    }
    sync();
    printf("scene: end\n");
    return 0;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc >= 5 && strcmp(argv[1], "scene") == 0) {
        return scene(argv[2], argv[3], atol(argv[4]), argc >= 6 ? atol(argv[5]) : 0);
    }
    if (argc == 4 && strcmp(argv[1], "modes") == 0) {
        mode_t m = (mode_t)strtol(argv[3], NULL, 8);
        if (m == 0) { fprintf(stderr, "churn: a mode of 0\n"); return 2; }
        long long t0 = now_ms();
        if (walk(argv[2], m) != 0) return 1;
        printf("modes: %lld files to %o in %lld ms\n", changed, (unsigned)m, now_ms() - t0);
        sync();
        printf("modes: end\n");
        return 0;
    }
    fprintf(stderr, "usage: churn scene TREE LOG SECS [HOLD] | churn modes TREE MODE\n");
    return 2;
}
