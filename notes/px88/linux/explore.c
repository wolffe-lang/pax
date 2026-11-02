/* px88: black-box Linux, before the witness is written. A static musl
 * program (Ubuntu 24.04's musl-gcc) that prints raw numbers: what
 * getrusage answers for each `who` and each bad buffer, ru_maxrss across
 * an allocation, a free, a fork, an exec, a vfork child's exec and a
 * waited-for grandchild, the times for a spin and for system calls, the
 * context switches for sleeps and for a CPU shared with another spinner,
 * and wait4's rusage. Run under strace -f once so the system calls musl's
 * fork, vfork and posix_spawn make are on record.
 *
 * Written from getrusage(2), wait4(2), fork(2), vfork(2), execve(2),
 * posix_spawn(3) and sched_setaffinity(2). No C library's or kernel's
 * source was read. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

static long ms(struct timeval t) { return t.tv_sec * 1000 + t.tv_usec / 1000; }
static long us(struct timeval t) { return t.tv_sec * 1000000L + t.tv_usec; }

static void show(const char *tag, int who) {
    struct rusage r;
    memset(&r, 0x55, sizeof r);
    long rc = syscall(SYS_getrusage, who, &r);
    printf("%s who=%d rc=%ld utime=%ldus stime=%ldus maxrss=%ld ixrss=%ld idrss=%ld isrss=%ld minflt=%ld majflt=%ld nswap=%ld inblock=%ld oublock=%ld msgsnd=%ld msgrcv=%ld nsignals=%ld nvcsw=%ld nivcsw=%ld\n",
           tag, who, rc, us(r.ru_utime), us(r.ru_stime), r.ru_maxrss, r.ru_ixrss, r.ru_idrss, r.ru_isrss,
           r.ru_minflt, r.ru_majflt, r.ru_nswap, r.ru_inblock, r.ru_oublock, r.ru_msgsnd, r.ru_msgrcv,
           r.ru_nsignals, r.ru_nvcsw, r.ru_nivcsw);
    fflush(stdout);
}

static long maxrss(int who) { struct rusage r; getrusage(who, &r); return r.ru_maxrss; }

static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec / 1e9; }

static void spin(double s) { double e = now() + s; volatile unsigned long x = 0; while (now() < e) x++; }

static void touch(size_t n) {
    char *p = malloc(n);
    for (size_t i = 0; i < n; i += 4096) p[i] = 1;
    printf("touched %zu MiB at maxrss %ld\n", n >> 20, maxrss(RUSAGE_SELF));
    free(p);
}

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "after-exec") == 0) {
        printf("after exec: maxrss %ld\n", maxrss(RUSAGE_SELF));
        show("after-exec self", RUSAGE_SELF);
        show("after-exec children", RUSAGE_CHILDREN);
        return 0;
    }
    if (argc > 1 && strcmp(argv[1], "small") == 0) {
        printf("small: maxrss %ld\n", maxrss(RUSAGE_SELF));
        return 0;
    }
    if (argc > 1 && strcmp(argv[1], "strace") == 0) {
        pid_t p = fork();
        if (p == 0) _exit(7);
        int st; waitpid(p, &st, 0);
        p = vfork();
        if (p == 0) _exit(8);
        waitpid(p, &st, 0);
        char *av[] = { argv[0], "small", 0 };
        posix_spawn(&p, argv[0], 0, 0, av, environ);
        waitpid(p, &st, 0);
        return 0;
    }
    errno = 0; printf("getrusage(5, &r) = %ld errno %d\n", syscall(SYS_getrusage, 5, &(struct rusage){0}), errno);
    errno = 0; printf("getrusage(-2, &r) = %ld errno %d\n", syscall(SYS_getrusage, -2, &(struct rusage){0}), errno);
    errno = 0; printf("getrusage(0, NULL) = %ld errno %d\n", syscall(SYS_getrusage, 0, 0), errno);
    errno = 0; printf("getrusage(5, NULL) = %ld errno %d\n", syscall(SYS_getrusage, 5, 0), errno);
    errno = 0; printf("getrusage(-1, (void*)8) = %ld errno %d\n", syscall(SYS_getrusage, -1, (void *)8), errno);
    errno = 0; printf("getrusage(0x100000000, &r) = %ld errno %d\n", syscall(SYS_getrusage, 0x100000000L, &(struct rusage){0}), errno);
    errno = 0; printf("getrusage(0xffffffff, &r) = %ld errno %d\n", syscall(SYS_getrusage, 0xffffffffL, &(struct rusage){0}), errno);
    show("start self", RUSAGE_SELF);
    show("start children", RUSAGE_CHILDREN);
    show("start thread", RUSAGE_THREAD);
    touch(64 << 20);
    printf("after free: maxrss %ld\n", maxrss(RUSAGE_SELF));
    touch(16 << 20);
    show("after 64+16 self", RUSAGE_SELF);
    show("after 64+16 thread", RUSAGE_THREAD);
    /* a fork's child: what it starts with */
    pid_t p = fork();
    if (p == 0) {
        show("fork child at start self", RUSAGE_SELF);
        show("fork child at start children", RUSAGE_CHILDREN);
        touch(32 << 20);
        spin(0.2);
        _exit(3);
    }
    struct rusage wr; int st;
    memset(&wr, 0x55, sizeof wr);
    wait4(p, &st, 0, &wr);
    printf("wait4 rusage: utime %ldus stime %ldus maxrss %ld minflt %ld nvcsw %ld nivcsw %ld status %d\n",
           us(wr.ru_utime), us(wr.ru_stime), wr.ru_maxrss, wr.ru_minflt, wr.ru_nvcsw, wr.ru_nivcsw, WEXITSTATUS(st));
    show("after child children", RUSAGE_CHILDREN);
    /* a grandchild bigger than the child */
    p = fork();
    if (p == 0) {
        pid_t q = fork();
        if (q == 0) { touch(48 << 20); _exit(0); }
        waitpid(q, 0, 0);
        show("middle after grandchild children", RUSAGE_CHILDREN);
        _exit(0);
    }
    memset(&wr, 0x55, sizeof wr);
    wait4(p, &st, 0, &wr);
    printf("wait4 of middle: maxrss %ld\n", wr.ru_maxrss);
    show("after grandchild children", RUSAGE_CHILDREN);
    /* an exec after a big allocation, in a child */
    p = fork();
    if (p == 0) {
        char *q = malloc(40 << 20);
        for (size_t i = 0; i < (40u << 20); i += 4096) q[i] = 1;
        printf("before exec: maxrss %ld\n", maxrss(RUSAGE_SELF));
        fflush(stdout);
        spin(0.1);
        char *av[] = { argv[0], "after-exec", 0 };
        execve(argv[0], av, environ);
        _exit(99);
    }
    waitpid(p, &st, 0);
    /* a vfork child that execs */
    p = vfork();
    if (p == 0) {
        char *av[] = { argv[0], "small", 0 };
        execve(argv[0], av, environ);
        _exit(99);
    }
    waitpid(p, &st, 0);
    /* times */
    struct rusage a, b;
    getrusage(RUSAGE_SELF, &a);
    double t0 = now();
    spin(0.3);
    double t1 = now();
    getrusage(RUSAGE_SELF, &b);
    printf("spin %.0f ms: utime +%ld ms stime +%ld ms nvcsw +%ld nivcsw +%ld\n", (t1 - t0) * 1000,
           ms(b.ru_utime) - ms(a.ru_utime), ms(b.ru_stime) - ms(a.ru_stime), b.ru_nvcsw - a.ru_nvcsw, b.ru_nivcsw - a.ru_nivcsw);
    int z = open("/dev/zero", O_RDONLY);
    char *buf = malloc(1 << 20);
    getrusage(RUSAGE_SELF, &a);
    t0 = now();
    long n = 0;
    while (now() < t0 + 0.3) { read(z, buf, 1 << 20); n++; }
    t1 = now();
    getrusage(RUSAGE_SELF, &b);
    printf("reads %ld of 1 MiB in %.0f ms: utime +%ld ms stime +%ld ms\n", n, (t1 - t0) * 1000,
           ms(b.ru_utime) - ms(a.ru_utime), ms(b.ru_stime) - ms(a.ru_stime));
    getrusage(RUSAGE_SELF, &a);
    for (int i = 0; i < 10; i++) { struct timespec d = { 0, 5000000 }; nanosleep(&d, 0); }
    getrusage(RUSAGE_SELF, &b);
    printf("10 sleeps: nvcsw +%ld nivcsw +%ld\n", b.ru_nvcsw - a.ru_nvcsw, b.ru_nivcsw - a.ru_nivcsw);
    /* a CPU shared with a spinning child */
    cpu_set_t one; CPU_ZERO(&one); CPU_SET(sched_getcpu(), &one);
    sched_setaffinity(0, sizeof one, &one);
    p = fork();
    if (p == 0) { spin(0.5); _exit(0); }
    getrusage(RUSAGE_SELF, &a);
    t0 = now();
    spin(0.4);
    getrusage(RUSAGE_SELF, &b);
    printf("shared spin %.0f ms: utime +%ld ms nvcsw +%ld nivcsw +%ld\n", (now() - t0) * 1000,
           ms(b.ru_utime) - ms(a.ru_utime), b.ru_nvcsw - a.ru_nvcsw, b.ru_nivcsw - a.ru_nivcsw);
    getrusage(RUSAGE_SELF, &a);
    for (int i = 0; i < 20; i++) sched_yield();
    getrusage(RUSAGE_SELF, &b);
    printf("20 yields beside a spinner: nvcsw +%ld nivcsw +%ld\n", b.ru_nvcsw - a.ru_nvcsw, b.ru_nivcsw - a.ru_nivcsw);
    waitpid(p, &st, 0);
    show("children after spinner", RUSAGE_CHILDREN);
    /* SIGCHLD ignored: are the auto-reaped children counted? */
    struct rusage c0, c1;
    getrusage(RUSAGE_CHILDREN, &c0);
    signal(SIGCHLD, SIG_IGN);
    p = fork();
    if (p == 0) { spin(0.2); touch(96 << 20); _exit(0); }
    errno = 0;
    long w = waitpid(p, &st, 0);
    printf("ignored SIGCHLD: waitpid %ld errno %d\n", w, errno);
    getrusage(RUSAGE_CHILDREN, &c1);
    printf("ignored SIGCHLD: children utime +%ld ms maxrss %ld -> %ld\n", ms(c1.ru_utime) - ms(c0.ru_utime), c0.ru_maxrss, c1.ru_maxrss);
    signal(SIGCHLD, SIG_DFL);
    show("end self", RUSAGE_SELF);
    show("end thread", RUSAGE_THREAD);
    show("end children", RUSAGE_CHILDREN);
    return 0;
}
