/* pair — two programs at once, one line of the run list (px24): a
   server and the client that calls it, each a process of its own.

     pair SERVER ARGS… -- CLIENT ARGS…

   The server is started first, its standard output a pipe; when it has
   written its first line (it says so when it listens) the client is
   started, its output a pipe too. Both are waited for; then the
   server's lines are written, then the client's, then a line with the
   two exit statuses: the same bytes whichever of them ran first. The
   exit status is 0 when both ended with 0. */
#include "say.h"
#include <stdlib.h>
#include <sys/wait.h>

static pid_t start(char **argv, int *out)
{
    int p[2];
    if (!argv[0] || pipe(p) < 0)
        return -1;
    pid_t k = fork();
    if (k == 0) {
        dup2(p[1], 1);
        close(p[0]);
        close(p[1]);
        execv(argv[0], argv);
        say("pair: %s: %s\n", argv[0], ename(errno));
        _exit(127);
    }
    close(p[1]);
    *out = p[0];
    return k;
}

/* Read `fd` to its end into a growing buffer (or, with `first`, until
   the first newline). */
static size_t take(int fd, char **buf, size_t have, int first)
{
    for (;;) {
        *buf = realloc(*buf, have + 4096);
        ssize_t r = read(fd, *buf + have, first ? 1 : 4096);
        if (r <= 0)
            break;
        have += r;
        if (first && (*buf)[have - 1] == '\n')
            break;
    }
    return have;
}

int main(int argc, char **argv)
{
    int cut = 0;
    for (int i = 1; i < argc; i++)
        if (strcmp(argv[i], "--") == 0)
            cut = i;
    if (cut < 2 || cut == argc - 1) {
        say("usage: pair SERVER ARGS… -- CLIENT ARGS…\n");
        return 2;
    }
    argv[cut] = 0;
    int so = -1, co = -1, ss = 0, cs = 0;
    char *sb = 0, *cb = 0;
    pid_t s = start(argv + 1, &so);
    if (s < 0) {
        say("pair: the server: %s\n", ename(errno));
        return 1;
    }
    size_t sn = take(so, &sb, 0, 1);
    pid_t c = start(argv + cut + 1, &co);
    if (c < 0) {
        say("pair: the client: %s\n", ename(errno));
        return 1;
    }
    size_t cn = take(co, &cb, 0, 0);
    sn = take(so, &sb, sn, 0);
    waitpid(c, &cs, 0);
    waitpid(s, &ss, 0);
    size_t off = 0;
    while (off < sn) {
        ssize_t w = write(1, sb + off, sn - off);
        if (w <= 0)
            break;
        off += w;
    }
    off = 0;
    while (off < cn) {
        ssize_t w = write(1, cb + off, cn - off);
        if (w <= 0)
            break;
        off += w;
    }
    int a = WIFEXITED(ss) ? WEXITSTATUS(ss) : 128, b = WIFEXITED(cs) ? WEXITSTATUS(cs) : 128;
    say("pair: the server ended with status %d, the client with %d\n", a, b);
    return a || b;
}
