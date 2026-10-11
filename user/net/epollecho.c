/* epollecho — a TCP echo server on epoll (px24), and what drives it.

     epollecho PORT READY-IP READY-PORT   the server: listen on PORT on
                                          every address, say "ready" to
                                          READY-IP:READY-PORT in one UDP
                                          datagram, serve until told to quit
     epollecho storm HOST PORT N SOAK     the driver: N connections held at
                                          once, two storms, then SOAK more
                                          connections eight at a time
     epollecho loop PORT N SOAK           both over 127.0.0.1: the server
                                          here, the driver its child

   The server is one thread and one epoll object. The listener is
   registered level-triggered; every connection edge-triggered
   (EPOLLIN|EPOLLRDHUP|EPOLLET), read until -EAGAIN and echoed; what a
   send cannot take is kept and the registration modified to add
   EPOLLOUT until it has gone. The end of a connection's stream closes
   it, which is also what takes it out of the epoll object.

   A connection whose first bytes are "ctl\n" is the driver's control
   connection, and is not echoed. Its lines:
     stat       -> "stat A O M B": connections accepted, open now, the
                   most open at once, bytes echoed
     hold       -> "held O", and the server serves nothing until `go`;
                   meanwhile
     peek       -> "peek K": K connections have bytes waiting (looked
                   at with MSG_PEEK, left unread), so the driver knows
                   every one of its messages has arrived before it says
     go MAX     -> the storm: with every connection's bytes already
                   waiting, epoll_wait(…, MAX, 0) until it answers 0:
                   "storm W waits, E events, D distinct, R repeated";
                   then the events are served
     quit       -> "bye", and the server ends
   A storm is the test of the two things an edge-triggered registration
   must do when many become ready together: answer each once (E = D =
   the connections, R = 0) and answer none again without new bytes (the
   last wait is the one that answers 0).

   Both ends print totals only, so the output is the same whatever
   order the kernel answered in. */
#define _GNU_SOURCE
#include "say.h"
#pragma GCC diagnostic ignored "-Wunused-result"
#include <fcntl.h>
#include <signal.h>
#include <stdlib.h>
#include <sys/epoll.h>
#include <sys/wait.h>
#include <time.h>

#define MAXFD 1024
#define LISTENER 0xffffffffULL

struct conn {
    int used, ctl, fresh, eof, want_out;
    char *out;
    size_t out_len, out_off;
};

static struct conn conns[MAXFD];
static int ep, ctl_fd = -1;
static unsigned long accepted, open_now, most, echoed, storms;

static int ctl_op(int op, int fd, unsigned events)
{
    struct epoll_event e;
    memset(&e, 0, sizeof e);
    e.events = events;
    e.data.u64 = (unsigned)fd;
    return epoll_ctl(ep, op, fd, &e);
}

static void drop(int fd)
{
    struct conn *c = &conns[fd];
    if (!c->ctl)
        open_now--;
    free(c->out);
    memset(c, 0, sizeof *c);
    close(fd); /* its registration goes with its last descriptor */
}

/* Send what is kept for `fd`; 0 when it has all gone, 1 when some is
   left (EPOLLOUT asked for), -1 when the connection is over. */
static int flush(int fd)
{
    struct conn *c = &conns[fd];
    while (c->out_off < c->out_len) {
        ssize_t w = send(fd, c->out + c->out_off, c->out_len - c->out_off, MSG_NOSIGNAL);
        if (w < 0) {
            if (errno != EAGAIN)
                return -1;
            if (!c->want_out) {
                c->want_out = 1;
                ctl_op(EPOLL_CTL_MOD, fd, EPOLLIN | EPOLLOUT | EPOLLRDHUP | EPOLLET);
            }
            return 1;
        }
        c->out_off += w;
    }
    c->out_len = c->out_off = 0;
    if (c->want_out) {
        c->want_out = 0;
        ctl_op(EPOLL_CTL_MOD, fd, EPOLLIN | EPOLLRDHUP | EPOLLET);
    }
    return 0;
}

static int keep(int fd, const char *p, size_t n)
{
    struct conn *c = &conns[fd];
    if (c->out_off == c->out_len)
        c->out_len = c->out_off = 0;
    char *q = realloc(c->out, c->out_len + n);
    if (!q)
        return -1;
    c->out = q;
    memcpy(q + c->out_len, p, n);
    c->out_len += n;
    return 0;
}

static void reply(int fd, const char *fmt, ...)
{
    char b[160];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    keep(fd, b, n);
    flush(fd);
}

static void serve_fd(int fd);

/* The storm: every event the object has, taken with room for `max` at
   a time and nothing served in between, then served. */
static void storm(int max)
{
    static struct epoll_event got[MAXFD];
    static unsigned char seen[MAXFD];
    static int order[MAXFD];
    int waits = 0, events = 0, distinct = 0, repeated = 0;
    memset(seen, 0, sizeof seen);
    if (max < 1 || max > MAXFD)
        max = MAXFD;
    for (;;) {
        int n = epoll_wait(ep, got, max, 0);
        waits++;
        if (n <= 0)
            break;
        for (int i = 0; i < n; i++) {
            int fd = (int)got[i].data.u64;
            if (got[i].data.u64 == LISTENER || fd == ctl_fd)
                continue;
            events++;
            if (seen[fd])
                repeated++;
            else {
                seen[fd] = 1;
                order[distinct++] = fd;
            }
        }
    }
    storms++;
    reply(ctl_fd, "storm %d waits, %d events, %d distinct, %d repeated\n", waits, events, distinct, repeated);
    for (int i = 0; i < distinct; i++)
        serve_fd(order[i]);
}

/* A line of the control connection. Returns 1 for "quit". */
static int command(int fd, char *line)
{
    if (strcmp(line, "stat") == 0)
        reply(fd, "stat %lu %lu %lu %lu\n", accepted, open_now, most, echoed);
    else if (strcmp(line, "hold") == 0) {
        /* Out of the object and blocking while it holds: the next line
           is read here, not waited for with the rest. */
        epoll_ctl(ep, EPOLL_CTL_DEL, fd, 0);
        fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) & ~O_NONBLOCK);
        reply(fd, "held %lu\n", open_now);
        char b[32];
        for (;;) {
            int n = 0;
            while (n < (int)sizeof b - 1) {
                if (recv(fd, b + n, 1, 0) != 1)
                    return 1;
                if (b[n] == '\n')
                    break;
                n++;
            }
            b[n] = 0;
            if (strcmp(b, "peek") != 0)
                break;
            /* How many connections have bytes waiting, looked at and
               left where they are. */
            int waiting = 0;
            char one;
            for (int k = 0; k < MAXFD; k++)
                if (conns[k].used && !conns[k].ctl && recv(k, &one, 1, MSG_PEEK | MSG_DONTWAIT) == 1)
                    waiting++;
            reply(fd, "peek %d\n", waiting);
        }
        fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) | O_NONBLOCK);
        ctl_op(EPOLL_CTL_ADD, fd, EPOLLIN | EPOLLRDHUP | EPOLLET);
        storm(strncmp(b, "go ", 3) == 0 ? atoi(b + 3) : MAXFD);
    } else if (strcmp(line, "quit") == 0) {
        reply(fd, "bye\n");
        return 1;
    } else
        reply(fd, "what\n");
    return 0;
}

static int quitting;

/* Everything `fd` has to give, until -EAGAIN. */
static void serve_fd(int fd)
{
    static char buf[16384];
    struct conn *c = &conns[fd];
    if (!c->used)
        return;
    if (flush(fd) < 0) {
        drop(fd);
        return;
    }
    for (;;) {
        ssize_t n = recv(fd, buf, sizeof buf - 1, 0);
        if (n < 0) {
            if (errno == EAGAIN)
                break;
            drop(fd);
            return;
        }
        if (n == 0) {
            c->eof = 1;
            break;
        }
        if (c->fresh) {
            c->fresh = 0;
            if (n >= 4 && memcmp(buf, "ctl\n", 4) == 0) {
                c->ctl = 1;
                ctl_fd = fd;
                accepted--;
                open_now--;
                memmove(buf, buf + 4, n - 4);
                n -= 4;
            }
        }
        if (c->ctl) {
            /* Whole lines; the driver sends one and waits for its
               answer. Copied out: a command may serve other
               connections through this buffer. */
            char lines[256], *s = lines, *e;
            if (n > (ssize_t)sizeof lines - 1)
                n = sizeof lines - 1;
            memcpy(lines, buf, n);
            lines[n] = 0;
            while ((e = strchr(s, '\n')) != 0) {
                *e = 0;
                if (command(fd, s))
                    quitting = 1;
                if (!conns[fd].used)
                    return;
                s = e + 1;
            }
            continue;
        }
        echoed += n;
        if (keep(fd, buf, n) < 0 || flush(fd) < 0) {
            drop(fd);
            return;
        }
    }
    if (c->eof && c->out_off == c->out_len)
        drop(fd);
}

static int serve(int lfd)
{
    static struct epoll_event ev[64];
    struct epoll_event le;
    signal(SIGPIPE, SIG_IGN);
    ep = epoll_create1(EPOLL_CLOEXEC);
    if (ep < 0) {
        say("epollecho: epoll_create1: %s\n", ename(errno));
        return 1;
    }
    memset(&le, 0, sizeof le);
    le.events = EPOLLIN;
    le.data.u64 = LISTENER;
    fcntl(lfd, F_SETFL, O_NONBLOCK);
    if (epoll_ctl(ep, EPOLL_CTL_ADD, lfd, &le) < 0) {
        say("epollecho: epoll_ctl: %s\n", ename(errno));
        return 1;
    }
    while (!quitting) {
        int n = epoll_wait(ep, ev, 64, -1);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            say("epollecho: epoll_wait: %s\n", ename(errno));
            return 1;
        }
        for (int i = 0; i < n && !quitting; i++) {
            if (ev[i].data.u64 != LISTENER) {
                serve_fd((int)ev[i].data.u64);
                continue;
            }
            for (;;) {
                int fd = accept4(lfd, 0, 0, SOCK_NONBLOCK | SOCK_CLOEXEC);
                if (fd < 0)
                    break;
                if (fd >= MAXFD) {
                    close(fd);
                    continue;
                }
                memset(&conns[fd], 0, sizeof conns[fd]);
                conns[fd].used = conns[fd].fresh = 1;
                accepted++;
                open_now++;
                if (open_now > most)
                    most = open_now;
                if (ctl_op(EPOLL_CTL_ADD, fd, EPOLLIN | EPOLLRDHUP | EPOLLET) < 0) {
                    say("epollecho: epoll_ctl add: %s\n", ename(errno));
                    drop(fd);
                }
            }
        }
    }
    for (int fd = 0; fd < MAXFD; fd++)
        if (conns[fd].used)
            drop(fd);
    close(ep);
    return 0;
}

/* The server's last line: after its driver's, when the driver is its
   child, so the two never race for the console. */
static void totals(void)
{
    say("epollecho: %lu connections, %lu at once at most, %lu bytes echoed, %lu storms held\n", accepted, most, echoed, storms);
}

/* --- the driver ---------------------------------------------------------- */

static int ask(int ctl, const char *line, char *answer, size_t cap)
{
    size_t n = 0;
    if (send_all(ctl, line, strlen(line)) < 0)
        return -1;
    while (n < cap - 1) {
        if (recv(ctl, answer + n, 1, 0) != 1)
            return -1;
        if (answer[n] == '\n')
            break;
        n++;
    }
    answer[n] = 0;
    return 0;
}

static void message(char *b, int round, int i)
{
    memset(b, '.', 48);
    int n = snprintf(b, 48, "storm %d connection %d ", round, i);
    b[n] = '.';
    b[47] = '\n';
}

/* The server's "stat" until it holds `want` connections: 0, or -1. */
static int holds(int ctl, unsigned long want)
{
    char a[96];
    for (int tries = 0; tries < 2000; tries++) {
        unsigned long acc, op, mx, by;
        if (ask(ctl, "stat\n", a, sizeof a) < 0 || sscanf(a, "stat %lu %lu %lu %lu", &acc, &op, &mx, &by) != 4)
            return -1;
        if (op == want)
            return 0;
        struct timespec nap = { 0, 5 * 1000000L };
        nanosleep(&nap, 0);
    }
    return -1;
}

static int drive(const char *host, int port, int n, int soak)
{
    static int fds[MAXFD];
    static char got[MAXFD][48];
    static int have[MAXFD];
    struct sockaddr_in a = sin_of(host, port);
    char line[160], msg[48];
    struct epoll_event ev[64], e;
    signal(SIGPIPE, SIG_IGN);
    if (n < 1 || n > 250) {
        say("epollecho storm: N is 1 to 250\n");
        return 2;
    }
    int ctl = socket(AF_INET, SOCK_STREAM, 0);
    if (ctl < 0 || connect(ctl, (struct sockaddr *)&a, sizeof a) < 0 || send_all(ctl, "ctl\n", 4) < 0) {
        say("epollecho storm: the control connection: %s\n", ename(errno));
        return 1;
    }
    /* An answer on it first, so the server knows which connection this
       is before the others arrive (it counts the rest). */
    if (ask(ctl, "stat\n", line, sizeof line) < 0) {
        say("epollecho storm: the control connection: no answer\n");
        return 1;
    }
    /* N connections begun at once, each watched for the end of its
       handshake by an epoll object of this end's own. */
    int mine = epoll_create1(0), pending = 0, failed = 0;
    for (int i = 0; i < n; i++) {
        fds[i] = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
        int r = connect(fds[i], (struct sockaddr *)&a, sizeof a);
        if (fds[i] < 0 || (r < 0 && errno != EINPROGRESS)) {
            say("epollecho storm: connection %d: %s\n", i, ename(errno));
            return 1;
        }
        memset(&e, 0, sizeof e);
        e.events = EPOLLOUT | EPOLLONESHOT;
        e.data.u64 = i;
        epoll_ctl(mine, EPOLL_CTL_ADD, fds[i], &e);
        pending++;
    }
    while (pending > 0) {
        int k = epoll_wait(mine, ev, 64, 20000);
        if (k <= 0) {
            say("epollecho storm: %d connections never finished their handshake\n", pending);
            return 1;
        }
        for (int j = 0; j < k; j++) {
            int err = -1;
            socklen_t el = sizeof err;
            getsockopt(fds[ev[j].data.u64], SOL_SOCKET, SO_ERROR, &err, &el);
            failed += err != 0;
            pending--;
        }
    }
    say("epollecho storm: %d connections made at once, %d failed\n", n, failed);
    if (holds(ctl, n) < 0) {
        say("epollecho storm: the server never held %d\n", n);
        return 1;
    }
    int bad = 0;
    for (int round = 1; round <= 2; round++) {
        if (ask(ctl, "hold\n", line, sizeof line) < 0) {
            say("epollecho storm: hold: no answer\n");
            return 1;
        }
        say("epollecho storm: the server %s\n", line);
        for (int i = 0; i < n; i++) {
            message(msg, round, i);
            if (send(fds[i], msg, 48, MSG_NOSIGNAL) != 48)
                bad++;
            have[i] = 0;
            memset(&e, 0, sizeof e);
            e.events = EPOLLIN;
            e.data.u64 = i;
            epoll_ctl(mine, EPOLL_CTL_MOD, fds[i], &e);
        }
        int there = -1;
        for (int tries = 0; tries < 4000 && there != n; tries++) {
            if (ask(ctl, "peek\n", line, sizeof line) < 0 || sscanf(line, "peek %d", &there) != 1)
                break;
            if (there != n) {
                struct timespec nap = { 0, 5 * 1000000L };
                nanosleep(&nap, 0);
            }
        }
        say("epollecho storm: %d of them have bytes waiting\n", there);
        if (ask(ctl, round == 1 ? "go 1024\n" : "go 16\n", line, sizeof line) < 0) {
            say("epollecho storm: go: no answer\n");
            return 1;
        }
        say("epollecho storm: room for %s: %s\n", round == 1 ? "all" : "16", line);
        int left = n, exact = 0;
        while (left > 0) {
            int k = epoll_wait(mine, ev, 64, 20000);
            if (k <= 0)
                break;
            for (int j = 0; j < k; j++) {
                int i = (int)ev[j].data.u64;
                ssize_t r = recv(fds[i], got[i] + have[i], 48 - have[i], 0);
                if (r <= 0) {
                    left--;
                    epoll_ctl(mine, EPOLL_CTL_DEL, fds[i], 0);
                    continue;
                }
                have[i] += r;
                if (have[i] == 48) {
                    message(msg, round, i);
                    exact += memcmp(msg, got[i], 48) == 0;
                    left--;
                    memset(&e, 0, sizeof e);
                    e.data.u64 = i;
                    epoll_ctl(mine, EPOLL_CTL_MOD, fds[i], &e); /* asks nothing until the next round */
                }
            }
        }
        say("epollecho storm: %d echoes exact of %d\n", exact, n);
        bad += exact != n;
    }
    for (int i = 0; i < n; i++)
        close(fds[i]);
    close(mine);
    if (holds(ctl, 0) < 0) {
        say("epollecho storm: the server did not let go of them\n");
        return 1;
    }
    say("epollecho storm: all %d closed, the server holds 0\n", n);
    /* The soak: eight at a time, each echoed and closed. */
    int done = 0, right = 0;
    while (done < soak) {
        int batch = soak - done < 8 ? soak - done : 8, s[8];
        for (int i = 0; i < batch; i++) {
            s[i] = socket(AF_INET, SOCK_STREAM, 0);
            if (s[i] < 0 || connect(s[i], (struct sockaddr *)&a, sizeof a) < 0) {
                say("epollecho storm: soak connection %d: %s\n", done + i, ename(errno));
                return 1;
            }
        }
        for (int i = 0; i < batch; i++) {
            message(msg, 3, done + i);
            send(s[i], msg, 48, MSG_NOSIGNAL);
        }
        for (int i = 0; i < batch; i++) {
            char back[48];
            message(msg, 3, done + i);
            right += recv_all(s[i], back, 48) == 48 && memcmp(back, msg, 48) == 0;
            close(s[i]);
        }
        done += batch;
    }
    say("epollecho storm: %d connections more, eight at a time, %d echoed exact and closed\n", soak, right);
    bad += right != soak;
    if (holds(ctl, 0) < 0 || ask(ctl, "stat\n", line, sizeof line) < 0) {
        say("epollecho storm: the last count: no answer\n");
        return 1;
    }
    unsigned long acc = 0, op = 0, mx = 0, by = 0;
    sscanf(line, "stat %lu %lu %lu %lu", &acc, &op, &mx, &by);
    say("epollecho storm: the server counted %lu connections, %lu open, %lu at once at most, %lu bytes\n", acc, op, mx, by);
    if (ask(ctl, "quit\n", line, sizeof line) < 0)
        return 1;
    say("epollecho storm: the server said %s\n", line);
    close(ctl);
    return bad || failed ? 1 : 0;
}

static int listener(int port, const char *ip)
{
    int one = 1, fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in me = sin_of(ip, port);
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one) < 0
        || bind(fd, (struct sockaddr *)&me, sizeof me) < 0 || listen(fd, 128) < 0) {
        say("epollecho: socket, bind or listen: %s\n", ename(errno));
        return -1;
    }
    return fd;
}

int main(int argc, char **argv)
{
    if (argc == 6 && strcmp(argv[1], "storm") == 0)
        return drive(argv[2], atoi(argv[3]), atoi(argv[4]), atoi(argv[5]));
    if (argc == 5 && strcmp(argv[1], "loop") == 0) {
        int fd = listener(atoi(argv[2]), "127.0.0.1");
        if (fd < 0)
            return 1;
        say("epollecho: listening on 127.0.0.1:%d, the driver a child\n", atoi(argv[2]));
        pid_t k = fork();
        if (k == 0) {
            close(fd);
            _exit(drive("127.0.0.1", atoi(argv[2]), atoi(argv[3]), atoi(argv[4])));
        }
        int r = serve(fd), st = 0;
        waitpid(k, &st, 0);
        if (r == 0)
            totals();
        say("epollecho: the driver ended with status %d\n", WIFEXITED(st) ? WEXITSTATUS(st) : -1);
        return r || !WIFEXITED(st) || WEXITSTATUS(st) != 0;
    }
    if (argc != 4) {
        say("usage: epollecho PORT READY-IP READY-PORT | storm HOST PORT N SOAK | loop PORT N SOAK\n");
        return 2;
    }
    int fd = listener(atoi(argv[1]), "0.0.0.0");
    if (fd < 0)
        return 1;
    say("epollecho: listening on port %d\n", atoi(argv[1]));
    struct sockaddr_in ready = sin_of(argv[2], atoi(argv[3]));
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    if (u < 0 || sendto(u, "ready", 5, 0, (struct sockaddr *)&ready, sizeof ready) != 5) {
        say("epollecho: ready: %s\n", ename(errno));
        return 1;
    }
    close(u);
    int r = serve(fd);
    if (r == 0)
        totals();
    return r;
}
