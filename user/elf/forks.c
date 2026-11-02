/* px88: a static musl program that forks (pax#175), asked of the kernel
 * and of Linux: musl's fork() asks system call 57 where x86-64 has it,
 * glibc and wolf ask clone (56), so before px88 every static musl program
 * that forked got -ENOSYS on PAX. What fork(2) promises a forking caller,
 * row by row: the child's 0 and the parent's pid, the parent's pid as the
 * child's parent, the address space copied (static data, the heap, the
 * stack), the descriptors shared (a pipe, a file's offset, FD_CLOEXEC),
 * the dispositions and the mask kept, the pending set emptied, the exit
 * status and the killing signal, waitpid's WNOHANG and ECHILD; exec after
 * fork (argv, an inherited pipe, an ignored signal kept and a handler
 * reset, the mask, a missing path); vfork (58, the child's write seen by
 * the parent; exec from it); posix_spawn (musl's clone with CLONE_VM and
 * CLONE_VFORK) with a file action; a hundred children one at a time,
 * eight at once, and a fork from a second thread.
 *
 *   forks              every row, then `forks: done`
 *   forks exec A B     the exec rows' new image (internal)
 *
 * Every line is `case: answer`; no pid, time or address is printed. A
 * child prints only while its parent waits for it, so the lines' order is
 * the program's. Built by tools/mkforks with Ubuntu's musl-gcc (`-static
 * -no-pie`), never from musl's source.
 *
 * Written from POSIX.1-2024 (XSH fork, _Exit, execve, vfork's rationale,
 * posix_spawn, posix_spawn_file_actions_adddup2, waitpid, sigaction,
 * sigprocmask, sigpending, pthread_create) and the man pages (fork(2),
 * vfork(2), execve(2), wait(2), signal(7), sigaction(2), fcntl(2),
 * pipe(2), lseek(2), posix_spawn(3), pthread_create(3)). No C library's
 * or kernel's source was read. Written for this lane. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <spawn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;
static const char *self = "/bin/forks";

static void say(const char *fmt, ...) {
    char b[1024];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1) n = sizeof b - 1;
    int o = 0;
    while (o < n) {
        ssize_t w = write(1, b + o, n - o);
        if (w <= 0) break;
        o += w;
    }
}

static const char *yes(int c) { return c ? "yes" : "no"; }

/* A wait status as words: `exited N` or `signalled N`. */
static const char *how(int st) {
    static char b[4][40];
    static int k;
    char *o = b[k++ & 3];
    if (WIFEXITED(st)) snprintf(o, 40, "exited %d", WEXITSTATUS(st));
    else if (WIFSIGNALED(st)) snprintf(o, 40, "signalled %d", WTERMSIG(st));
    else snprintf(o, 40, "status 0x%x", st);
    return o;
}

/* Wait for `p`, answering its status in words, or `-E`. */
static const char *reap(pid_t p) {
    int st = 0;
    pid_t w = waitpid(p, &st, 0);
    if (w != p) {
        static char e[24];
        snprintf(e, sizeof e, "waitpid %d", w < 0 ? -errno : 0);
        return e;
    }
    return how(st);
}

static int global[3] = { 1, 2, 3 };
static volatile sig_atomic_t usr1;
static void on_usr1(int s) { (void)s; usr1 = 1; }

static int blocked(int sig) {
    sigset_t m;
    sigprocmask(SIG_BLOCK, 0, &m);
    return sigismember(&m, sig);
}
static int pending(int sig) {
    sigset_t m;
    sigpending(&m);
    return sigismember(&m, sig);
}
static void (*disp(int sig))(int) {
    struct sigaction a;
    sigaction(sig, 0, &a);
    return a.sa_handler;
}

/* F: fork itself. */
static void fork_rows(void) {
    /* ligature's pax-fork row (pax#175), as it reads on Linux. */
    pid_t p = fork();
    if (p < 0) {
        say("fork: %d\n", -errno);
        return;
    }
    if (p == 0) {
        say("fork: child\n");
        _exit(7);
    }
    int st = 0;
    waitpid(p, &st, 0);
    say("fork: child status %d\n", WEXITSTATUS(st));

    /* the two answers, and who the child's parent is */
    int fd[2];
    pipe(fd);
    pid_t me = getpid();
    p = fork();
    if (p == 0) {
        pid_t mine = getpid();
        int ok = getppid() == me;
        write(fd[1], &mine, sizeof mine);
        write(fd[1], &ok, sizeof ok);
        _exit(0);
    }
    pid_t told = 0;
    int ok = 0;
    read(fd[0], &told, sizeof told);
    read(fd[0], &ok, sizeof ok);
    reap(p);
    close(fd[0]);
    close(fd[1]);
    say("fork: the parent's answer is the child's pid: %s\n", yes(p > 0 && told == p));
    say("fork: the child's parent is the caller: %s\n", yes(ok));
    say("fork: the child's pid is not the caller's: %s\n", yes(told != me));

    /* the child's answer itself: the child is told apart by its pid, not
     * by what fork answered it, and reports that answer */
    pipe(fd);
    pid_t r = fork();
    if (r >= 0 && getpid() != me) {
        long z = r;
        write(fd[1], &z, sizeof z);
        _exit(0);
    }
    long z = -1;
    read(fd[0], &z, sizeof z);
    reap(r);
    close(fd[0]);
    close(fd[1]);
    say("fork: what fork answered the child: %ld\n", z);

    /* memory copied: static data, the heap, the stack */
    int *heap = malloc(3 * sizeof *heap);
    int stack[3] = { 4, 5, 6 };
    heap[0] = 7, heap[1] = 8, heap[2] = 9;
    pipe(fd);
    p = fork();
    if (p == 0) {
        char b[64];
        int n = snprintf(b, sizeof b, "%d %d %d %d %d %d %d %d %d", global[0], global[1], global[2],
                         heap[0], heap[1], heap[2], stack[0], stack[1], stack[2]);
        global[0] = global[1] = global[2] = 0;
        heap[0] = heap[1] = heap[2] = 0;
        stack[0] = stack[1] = stack[2] = 0;
        write(fd[1], b, n);
        _exit(0);
    }
    char seen[64] = { 0 };
    read(fd[0], seen, sizeof seen - 1);
    reap(p);
    close(fd[0]);
    close(fd[1]);
    say("fork: the child saw %s\n", seen);
    say("fork: the parent's after the child zeroed its own: %d %d %d %d %d %d %d %d %d\n", global[0], global[1],
        global[2], heap[0], heap[1], heap[2], stack[0], stack[1], stack[2]);
    free(heap);

    /* a pipe made before the fork */
    pipe(fd);
    p = fork();
    if (p == 0) {
        close(fd[0]);
        write(fd[1], "hello", 5);
        _exit(0);
    }
    close(fd[1]);
    char hb[16] = { 0 }, one;
    ssize_t got = read(fd[0], hb, sizeof hb - 1);
    ssize_t more = read(fd[0], &one, 1);
    reap(p);
    close(fd[0]);
    say("fork: the child's bytes through a pipe made before: %zd %s, then end of file %zd\n", got, hb, more);

    /* a file's offset is the open file's, shared */
    int f = open("forks-offset", O_RDWR | O_CREAT | O_TRUNC, 0644);
    p = fork();
    if (p == 0) {
        write(f, "abc", 3);
        _exit(0);
    }
    reap(p);
    say("fork: the parent's offset after the child wrote 3 bytes: %ld\n", (long)lseek(f, 0, SEEK_CUR));
    close(f);
    unlink("forks-offset");

    /* FD_CLOEXEC is the descriptor's, kept */
    pipe(fd);
    fcntl(fd[0], F_SETFD, FD_CLOEXEC);
    int pr[2];
    pipe(pr);
    p = fork();
    if (p == 0) {
        int a = fcntl(fd[0], F_GETFD), b = fcntl(fd[1], F_GETFD);
        write(pr[1], &a, sizeof a);
        write(pr[1], &b, sizeof b);
        _exit(0);
    }
    int a = -1, b = -1;
    read(pr[0], &a, sizeof a);
    read(pr[0], &b, sizeof b);
    reap(p);
    close(fd[0]), close(fd[1]), close(pr[0]), close(pr[1]);
    say("fork: FD_CLOEXEC in the child: %d on the flagged, %d on the other\n", a, b);

    /* dispositions kept, the handler runs in the child */
    signal(SIGUSR1, on_usr1);
    signal(SIGUSR2, SIG_IGN);
    pipe(fd);
    p = fork();
    if (p == 0) {
        int kept = disp(SIGUSR1) == on_usr1 && disp(SIGUSR2) == SIG_IGN && disp(SIGHUP) == SIG_DFL;
        raise(SIGUSR1);
        raise(SIGUSR2);
        int ran = usr1;
        write(fd[1], &kept, sizeof kept);
        write(fd[1], &ran, sizeof ran);
        _exit(0);
    }
    int kept = 0, ran = 0;
    read(fd[0], &kept, sizeof kept);
    read(fd[0], &ran, sizeof ran);
    say("fork: SIGUSR1's handler, SIGUSR2's SIG_IGN and SIGHUP's SIG_DFL kept: %s\n", yes(kept));
    say("fork: the handler ran in the child, the ignored signal did nothing: %s %s\n", yes(ran), reap(p));
    say("fork: the parent's handler did not run: %s\n", yes(!usr1));
    close(fd[0]), close(fd[1]);

    /* the mask kept, the pending set not */
    sigset_t m, old;
    sigemptyset(&m);
    sigaddset(&m, SIGUSR1);
    sigaddset(&m, SIGUSR2);
    sigprocmask(SIG_BLOCK, &m, &old);
    signal(SIGUSR2, SIG_DFL);
    raise(SIGUSR2);
    pipe(fd);
    p = fork();
    if (p == 0) {
        int bl = blocked(SIGUSR1) && blocked(SIGUSR2), pe = pending(SIGUSR2);
        write(fd[1], &bl, sizeof bl);
        write(fd[1], &pe, sizeof pe);
        _exit(0);
    }
    int bl = 0, pe = 1;
    read(fd[0], &bl, sizeof bl);
    read(fd[0], &pe, sizeof pe);
    reap(p);
    close(fd[0]), close(fd[1]);
    say("fork: the mask kept: SIGUSR1 and SIGUSR2 blocked in the child: %s\n", yes(bl));
    say("fork: a pending SIGUSR2: the child's pending %s, the parent's %s\n", pe ? "yes" : "none",
        pending(SIGUSR2) ? "yes" : "none");
    signal(SIGUSR2, SIG_IGN); /* discards the pending one */
    sigprocmask(SIG_SETMASK, &old, 0);
    signal(SIGUSR2, SIG_DFL);
    signal(SIGUSR1, SIG_DFL);

    /* the end of a child */
    p = fork();
    if (p == 0) {
        raise(SIGTERM);
        _exit(1);
    }
    say("fork: a child that raised SIGTERM: %s\n", reap(p));
    p = fork();
    if (p == 0) _exit(255);
    say("fork: a child's _exit(255): %s\n", reap(p));

    /* WNOHANG while the child waits, then ECHILD */
    pipe(fd);
    p = fork();
    if (p == 0) {
        char c;
        close(fd[1]);
        read(fd[0], &c, 1);
        _exit(9);
    }
    close(fd[0]);
    int st2 = 0;
    pid_t w = waitpid(p, &st2, WNOHANG);
    say("fork: waitpid WNOHANG while the child waits: %d\n", w);
    write(fd[1], "x", 1);
    close(fd[1]);
    say("fork: then waitpid: %s\n", reap(p));
    errno = 0;
    w = waitpid(-1, &st2, WNOHANG);
    say("fork: waitpid with no child left: %d %d\n", w, -errno);
}

/* E: exec after fork. The new image is this program again (`exec`). */
static int exec_image(int argc, char **argv) {
    say("exec: argv %s %s %s, %d words\n", argv[1], argc > 2 ? argv[2] : "-", argc > 3 ? argv[3] : "-", argc);
    int w = write(3, "written", 7);
    say("exec: the pipe kept across exec (descriptor 3): %s\n", yes(w == 7));
    say("exec: SIGUSR2 ignored across exec: %s; SIGUSR1's handler reset to SIG_DFL: %s\n",
        yes(disp(SIGUSR2) == SIG_IGN), yes(disp(SIGUSR1) == SIG_DFL));
    say("exec: the mask across exec: SIGUSR1 blocked: %s\n", yes(blocked(SIGUSR1)));
    say("exec: the parent is the forking process: %s\n", yes(argc > 4 && getppid() == (pid_t)atol(argv[4])));
    return 3;
}

static void exec_rows(void) {
    int fd[2];
    pipe(fd);
    signal(SIGUSR1, on_usr1);
    signal(SIGUSR2, SIG_IGN);
    sigset_t m, old;
    sigemptyset(&m);
    sigaddset(&m, SIGUSR1);
    sigprocmask(SIG_BLOCK, &m, &old);
    char ppid[24];
    snprintf(ppid, sizeof ppid, "%d", getpid());
    pid_t p = fork();
    if (p == 0) {
        close(fd[0]);
        if (fd[1] != 3) {
            dup2(fd[1], 3);
            close(fd[1]);
        }
        char *av[] = { "forks", "exec", "1", "2", ppid, 0 };
        execve(self, av, environ);
        say("exec: execve %d\n", -errno);
        _exit(99);
    }
    close(fd[1]);
    const char *s = reap(p);
    char b[16] = { 0 };
    read(fd[0], b, sizeof b - 1);
    close(fd[0]);
    say("exec: %s; the new image wrote %s\n", s, b);
    sigprocmask(SIG_SETMASK, &old, 0);
    signal(SIGUSR1, SIG_DFL);
    signal(SIGUSR2, SIG_DFL);

    p = fork();
    if (p == 0) {
        char *av[] = { "nowhere", 0 };
        execve("/bin/nowhere", av, environ);
        say("exec: a missing path: %d\n", -errno);
        _exit(4);
    }
    say("exec: then %s\n", reap(p));
}

/* V: vfork (58). The child borrows the parent's memory until it execs
 * or ends (vfork(2): Linux's, which the rows hold to). */
static volatile int borrowed;

static void vfork_rows(void) {
    borrowed = 1;
    pid_t p = vfork();
    if (p == 0) {
        borrowed = 2;
        _exit(6);
    }
    say("vfork: %s; the child's write seen by the parent: %s\n", reap(p), yes(borrowed == 2));
    int fd[2];
    pipe(fd);
    char ppid[24];
    snprintf(ppid, sizeof ppid, "%d", getpid());
    p = vfork();
    if (p == 0) {
        dup2(fd[1], 3);
        char *av[] = { "forks", "exec", "v", "-", ppid, 0 };
        execve(self, av, environ);
        _exit(99);
    }
    close(fd[1]);
    const char *s = reap(p);
    char b[16] = { 0 };
    read(fd[0], b, sizeof b - 1);
    close(fd[0]);
    say("vfork: exec from the child: %s; the new image wrote %s\n", s, b);
}

/* S: posix_spawn, its output through a pipe made its standard output. */
static void spawn_rows(void) {
    int fd[2], w[2];
    pipe(fd);
    pipe(w);
    posix_spawn_file_actions_t fa;
    posix_spawn_file_actions_init(&fa);
    /* the read ends first: one of them may be the 3 the next dup2 makes */
    posix_spawn_file_actions_addclose(&fa, fd[0]);
    posix_spawn_file_actions_addclose(&fa, w[0]);
    posix_spawn_file_actions_adddup2(&fa, fd[1], 1);
    posix_spawn_file_actions_adddup2(&fa, w[1], 3);
    char ppid[24];
    snprintf(ppid, sizeof ppid, "%d", getpid());
    char *av[] = { "forks", "exec", "s", "-", ppid, 0 };
    pid_t p = 0;
    int r = posix_spawn(&p, self, &fa, 0, av, environ);
    posix_spawn_file_actions_destroy(&fa);
    close(fd[1]);
    close(w[1]);
    char out[1024] = { 0 };
    ssize_t n = 0, k;
    while ((k = read(fd[0], out + n, sizeof out - 1 - n)) > 0) n += k;
    close(fd[0]);
    char b[16] = { 0 };
    read(w[0], b, sizeof b - 1);
    close(w[0]);
    say("spawn: posix_spawn %d; %s; the new image wrote %s\n", r, reap(p), b);
    /* the child's lines, each marked */
    char *line = out;
    int lines = 0;
    while (*line) {
        char *e = strchr(line, '\n');
        if (!e) break;
        *e = 0;
        say("spawn: | %s\n", line);
        lines++;
        line = e + 1;
    }
    say("spawn: %d lines through the pipe\n", lines);
    pid_t q = 0;
    char *bad[] = { "nowhere", 0 };
    r = posix_spawn(&q, "/bin/nowhere", 0, 0, bad, environ);
    say("spawn: a missing path: %d\n", r);
}

/* N: many children. */
static void many_rows(void) {
    int right = 0;
    for (int i = 0; i < 100; i++) {
        pid_t p = fork();
        if (p == 0) _exit(i * 3 % 256);
        int st = 0;
        if (waitpid(p, &st, 0) == p && WIFEXITED(st) && WEXITSTATUS(st) == i * 3 % 256) right++;
    }
    say("many: 100 children one at a time, statuses right: %d\n", right);
    pid_t kids[8];
    int fd[2];
    pipe(fd);
    for (int i = 0; i < 8; i++) {
        kids[i] = fork();
        if (kids[i] == 0) {
            char c;
            close(fd[1]);
            read(fd[0], &c, 1); /* all eight alive at once */
            _exit(40 + i);
        }
    }
    close(fd[0]);
    close(fd[1]);
    right = 0;
    for (int i = 7; i >= 0; i--) {
        int st = 0;
        if (waitpid(kids[i], &st, 0) == kids[i] && WIFEXITED(st) && WEXITSTATUS(st) == 40 + i) right++;
    }
    say("many: 8 children at once, each waited for by pid, statuses right: %d\n", right);
}

/* T: a fork from a second thread. */
static void *forker(void *u) {
    (void)u;
    pid_t p = fork();
    if (p == 0) _exit(5);
    static char r[48];
    snprintf(r, sizeof r, "%s", reap(p));
    return r;
}

static void thread_rows(void) {
    pthread_t t;
    void *r = 0;
    int c = pthread_create(&t, 0, forker, 0);
    pthread_join(t, &r);
    say("thread: pthread_create %d; the child of the second thread: %s\n", c, c == 0 ? (char *)r : "-");
}

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "exec") == 0) return exec_image(argc, argv);
    say("forks: as %s\n", getuid() == 0 ? "root" : "a user");
    if (chdir("/t") != 0) say("forks: chdir /t %d\n", -errno);
    fork_rows();
    exec_rows();
    vfork_rows();
    spawn_rows();
    many_rows();
    thread_rows();
    say("forks: done\n");
    return 0;
}
