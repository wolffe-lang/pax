/* tcploop — a client and a forking server on one machine, over loopback
   (px23): the parent listens on PORT on every address and gives each
   connection to a child of its own, which reads the request to its end
   and answers "re: " and its text; another child, the client, asks it
   through 127.0.0.1, through the machine's own address and through
   127.0.0.1 again ("bye"), closing its half after each request and
   reading the answer to its end. Each waits for the other, so the
   lines come in one order. */
#include "say.h"
#include <stdlib.h>
#include <sys/wait.h>

#define PORT 4020
static char ab[64], bb[64];

static int client(const char *own)
{
    const char *to[] = {"127.0.0.1", own, "127.0.0.1"};
    const char *text[] = {"through 127.0.0.1", "through this machine's own address", "bye"};
    char got[256];
    for (int i = 0; i < 3; i++) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        struct sockaddr_in dst = sin_of(to[i], PORT), me, peer;
        if (connect(fd, (struct sockaddr *)&dst, sizeof dst) < 0) {
            say("client: connect %s: %s\n", to[i], ename(errno));
            return 1;
        }
        socklen_t l = sizeof me;
        getsockname(fd, (struct sockaddr *)&me, &l);
        l = sizeof peer;
        getpeername(fd, (struct sockaddr *)&peer, &l);
        if (send_all(fd, text[i], strlen(text[i])) < 0 || shutdown(fd, SHUT_WR) < 0) {
            say("client: send or shutdown: %s\n", ename(errno));
            return 1;
        }
        ssize_t n = recv_all(fd, got, sizeof got);
        if (n < 0) {
            say("client: recv: %s\n", ename(errno));
            return 1;
        }
        say("client: \"%.*s\" from %s; this end is %s\n", (int)n, got, aname(&peer, ab, sizeof ab), aname(&me, bb, sizeof bb));
        close(fd);
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *own = argc > 1 ? argv[1] : "10.0.2.15";
    int one = 1, fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in me = sin_of("0.0.0.0", PORT), from;
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one) < 0
        || bind(fd, (struct sockaddr *)&me, sizeof me) < 0 || listen(fd, 4) < 0) {
        say("server: socket, bind or listen: %s\n", ename(errno));
        return 1;
    }
    say("server: listening on %s\n", aname(&me, ab, sizeof ab));
    pid_t cl = fork();
    if (cl < 0) {
        say("server: fork: %s\n", ename(errno));
        return 1;
    }
    if (cl == 0) {
        close(fd); /* the child's copy: the parent's socket goes on listening */
        _exit(client(own));
    }
    pid_t kids[3];
    int n = 0, last = 0;
    while (!last && n < 3) {
        socklen_t l = sizeof from;
        int c = accept(fd, (struct sockaddr *)&from, &l);
        if (c < 0) {
            say("server: accept: %s\n", ename(errno));
            return 1;
        }
        struct sockaddr_in here;
        l = sizeof here;
        getsockname(c, (struct sockaddr *)&here, &l);
        say("server: a connection from %s to %s\n", aname(&from, ab, sizeof ab), aname(&here, bb, sizeof bb));
        /* The parent learns whether this was the last from the child's
           status, so it waits for each: one connection at a time. */
        pid_t pid = fork();
        if (pid < 0) {
            say("server: fork: %s\n", ename(errno));
            return 1;
        }
        if (pid == 0) {
            close(fd);
            char buf[256], out[300];
            ssize_t got = recv_all(c, buf, sizeof buf);
            if (got < 0) {
                say("handler: recv: %s\n", ename(errno));
                _exit(1);
            }
            say("handler: \"%.*s\", then the end of the stream\n", (int)got, buf);
            int m = snprintf(out, sizeof out, "re: %.*s", (int)got, buf);
            if (send_all(c, out, m) != m) {
                say("handler: send: %s\n", ename(errno));
                _exit(1);
            }
            close(c);
            _exit(got == 3 && memcmp(buf, "bye", 3) == 0 ? 7 : 0);
        }
        close(c);
        kids[n++] = pid;
        int st = 0;
        waitpid(pid, &st, 0);
        last = WIFEXITED(st) && WEXITSTATUS(st) == 7;
    }
    (void)kids;
    int st = 0;
    waitpid(cl, &st, 0);
    say("server: %d connections, each served by a child; the client ended with status %d\n", n, WIFEXITED(st) ? WEXITSTATUS(st) : -1);
    close(fd);
    return 0;
}
