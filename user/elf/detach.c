/* detach.c — px124: a process that leaves its session, as a server does
 * (a terminal multiplexer's, which must outlive the shell that started
 * it). tests/mpx5-init types it at an installed-shaped console:
 *
 *     detach FILE SECONDS
 *
 * forks; the child calls setsid(2), so it leads a session and a group of
 * its own with no controlling terminal, writes `PID SID\n` (its pid and
 * the session getsid(0) then answers) to FILE, moves its standard
 * descriptors to /dev/null, tells the parent through a pipe, sleeps
 * SECONDS and exits 0. The parent waits for that word, so FILE is whole
 * when the command line returns, and exits 0 (1 when the fork, the pipe
 * or the child failed, with one line on standard error). Once its parent
 * has ended the child is pid 1's (kernel/sched's reparent), and the suite
 * reads its /proc/PID/stat: alive and pid 1's after the console's logout,
 * gone (reaped, not a zombie) after SECONDS.
 *
 * Written from setsid(2), getsid(2), fork(2), pipe(2), dup2(2) and
 * sleep(3) (man-pages 6.7). No kernel's or C library's source. */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    int p[2];
    if (argc != 3) {
        fprintf(stderr, "usage: detach FILE SECONDS\n");
        return 2;
    }
    unsigned secs = (unsigned)atoi(argv[2]);
    if (pipe(p) != 0) {
        perror("detach: pipe");
        return 1;
    }
    pid_t c = fork();
    if (c < 0) {
        perror("detach: fork");
        return 1;
    }
    if (c == 0) {
        close(p[0]);
        char ok = 'n';
        if (setsid() >= 0) {
            FILE *f = fopen(argv[1], "w");
            if (f) {
                fprintf(f, "%d %d\n", (int)getpid(), (int)getsid(0));
                if (fclose(f) == 0)
                    ok = 'y';
            }
        }
        int null = open("/dev/null", O_RDWR);
        if (null >= 0) {
            dup2(null, 0);
            dup2(null, 1);
            dup2(null, 2);
            if (null > 2)
                close(null);
        }
        if (write(p[1], &ok, 1) != 1)
            _exit(1);
        close(p[1]);
        if (ok != 'y')
            _exit(1);
        sleep(secs);
        _exit(0);
    }
    close(p[1]);
    char got = 0;
    if (read(p[0], &got, 1) != 1 || got != 'y') {
        fprintf(stderr, "detach: the child did not start a session of its own\n");
        return 1;
    }
    return 0;
}
