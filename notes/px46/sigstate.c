/* px46: what a program pelt starts inherits of SIGPIPE: its disposition
 * and whether it is blocked; then a write to a pipe with no reader.
 * Written for this lane. */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(void) {
    struct sigaction sa;
    sigaction(SIGPIPE, NULL, &sa);
    sigset_t m;
    sigprocmask(SIG_SETMASK, NULL, &m);
    printf("SIGPIPE: %s, %s\n", sa.sa_handler == SIG_IGN ? "ignored" : sa.sa_handler == SIG_DFL ? "default" : "handled",
           sigismember(&m, SIGPIPE) ? "blocked" : "not blocked");
    int p[2];
    pipe(p);
    close(p[0]);
    fflush(stdout);
    ssize_t n = write(p[1], "x", 1);
    printf("write to a pipe with no reader: %zd %s\n", n, n < 0 ? strerror(errno) : "");
    return 0;
}
