/* tcpsoak — N connections opened and closed, one at a time (px23): each
   is a connect, 16 bytes out (the first four its number), the same 16
   back, and a close. One line at the end.

     tcpsoak to IP PORT N    against an echo server at IP:PORT
     tcpsoak loop N          against a server of its own, across fork,
                             over 127.0.0.1 port 4050; the server
                             closes first on every other connection, so
                             each end is in turn the one that waits */
#include "say.h"
#include <stdlib.h>
#include <sys/wait.h>

static long client(const char *ip, int port, long n, long *good)
{
    struct sockaddr_in srv = sin_of(ip, port);
    unsigned char out[16], in[16];
    long i;
    for (i = 0; i < n; i++) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0 || connect(fd, (struct sockaddr *)&srv, sizeof srv) < 0) {
            say("tcpsoak: socket or connect %ld: %s\n", i, ename(errno));
            return i;
        }
        for (int k = 0; k < 16; k++)
            out[k] = (unsigned char)(i * 7 + k * 13);
        out[0] = i >> 24, out[1] = i >> 16, out[2] = i >> 8, out[3] = i;
        if (send_all(fd, out, 16) != 16) {
            say("tcpsoak: send %ld: %s\n", i, ename(errno));
            return i;
        }
        ssize_t m = recv_all(fd, in, 16);
        if (m < 0) {
            say("tcpsoak: recv %ld: %s\n", i, ename(errno));
            return i;
        }
        *good += m == 16 && memcmp(in, out, 16) == 0;
        if (i & 1) {
            /* The server closes first: wait for the end of its stream. */
            char x;
            if (recv(fd, &x, 1, 0) != 0) {
                say("tcpsoak: connection %ld: no end of stream: %s\n", i, ename(errno));
                return i;
            }
        }
        close(fd);
    }
    return i;
}

int main(int argc, char **argv)
{
    long good = 0;
    if (argc == 5 && strcmp(argv[1], "to") == 0) {
        long n = atol(argv[4]);
        /* An echo server that waits for this end to close: never the odd branch. */
        struct sockaddr_in srv = sin_of(argv[2], atoi(argv[3]));
        unsigned char out[16], in[16];
        long i;
        for (i = 0; i < n; i++) {
            int fd = socket(AF_INET, SOCK_STREAM, 0);
            if (fd < 0 || connect(fd, (struct sockaddr *)&srv, sizeof srv) < 0) {
                say("tcpsoak: socket or connect %ld: %s\n", i, ename(errno));
                break;
            }
            for (int k = 0; k < 16; k++)
                out[k] = (unsigned char)(i * 7 + k * 13);
            out[0] = i >> 24, out[1] = i >> 16, out[2] = i >> 8, out[3] = i;
            if (send_all(fd, out, 16) != 16 || recv_all(fd, in, 16) != 16) {
                say("tcpsoak: connection %ld: %s\n", i, ename(errno));
                close(fd);
                break;
            }
            good += memcmp(in, out, 16) == 0;
            close(fd);
        }
        say("tcpsoak: %ld connections opened, %ld answered right, each closed\n", i, good);
        return good == n ? 0 : 1;
    }
    if (argc == 3 && strcmp(argv[1], "loop") == 0) {
        long n = atol(argv[2]);
        int one = 1, fd = socket(AF_INET, SOCK_STREAM, 0);
        struct sockaddr_in me = sin_of("127.0.0.1", 4050);
        if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one) < 0
            || bind(fd, (struct sockaddr *)&me, sizeof me) < 0 || listen(fd, 8) < 0) {
            say("tcpsoak: socket, bind or listen: %s\n", ename(errno));
            return 1;
        }
        pid_t pid = fork();
        if (pid < 0) {
            say("tcpsoak: fork: %s\n", ename(errno));
            return 1;
        }
        if (pid == 0) {
            close(fd);
            long done = client("127.0.0.1", 4050, n, &good);
            _exit(done == n && good == n ? 0 : 1);
        }
        long served = 0;
        unsigned char buf[16];
        for (long i = 0; i < n; i++) {
            int c = accept(fd, 0, 0);
            if (c < 0) {
                say("tcpsoak: accept %ld: %s\n", i, ename(errno));
                break;
            }
            if (recv_all(c, buf, 16) == 16 && send_all(c, buf, 16) == 16)
                served++;
            if (!(i & 1)) {
                /* The client closes first: wait for the end of its stream. */
                char x;
                (void)!recv(c, &x, 1, 0);
            }
            close(c);
        }
        int st = 0;
        waitpid(pid, &st, 0);
        say("tcpsoak: %ld connections served over loopback, each closed (the client first on the even ones, the server first on the odd); the client ended with status %d\n",
            served, WIFEXITED(st) ? WEXITSTATUS(st) : -1);
        close(fd);
        return served == n && WIFEXITED(st) && WEXITSTATUS(st) == 0 ? 0 : 1;
    }
    say("usage: tcpsoak to IP PORT N | loop N\n");
    return 2;
}
