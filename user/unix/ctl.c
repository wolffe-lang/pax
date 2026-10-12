/* ctl — lobo's control channel, both ends (px34, item 5): a server
   shaped as lobo's (`notes/px34/linux/`: a socket bound to
   logs/control.sock relative to the working directory, `listen(fd, -1)`,
   FIONBIO, its name written into logs/lobo.pid, a poll loop of 250 ms,
   accept4 with SOCK_CLOEXEC|SOCK_NONBLOCK, a verb of at most 512 bytes,
   an answer sent with MSG_NOSIGNAL, the connection closed; at `stop` the
   listener closed and its name unlinked), and lobo's own client run
   against it as a child: `/bin/lobo -c conf/lobo.conf status` (lobo at
   user/lobo.pin, built by tools/mklobo), which prints what the server
   answered. Then this program's own client asks `status` and `reload`,
   and `stop`. Its output on PAX must be its output on Linux. */
#define _GNU_SOURCE
#include "../net/say.h"
#pragma GCC diagnostic ignored "-Wunused-result"
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stddef.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <time.h>

#define NAME "logs/control.sock"
#define ANSWER "lobo status\ncurrent generation: 1\nquitting: false\nworkers: 0\ncontrol: unix:" NAME " (px34's server, on this machine)\n"

static void nap(long ms)
{
    struct timespec t = { ms / 1000, (ms % 1000) * 1000000L };
    nanosleep(&t, 0);
}

static socklen_t un_of(struct sockaddr_un *a, const char *path)
{
    memset(a, 0, sizeof *a);
    a->sun_family = AF_UNIX;
    strncpy(a->sun_path, path, sizeof a->sun_path - 1);
    return (socklen_t)(offsetof(struct sockaddr_un, sun_path) + strlen(path) + 1);
}

/* The server: lobo's control loop, in a process of its own. */
static int server(void)
{
    struct sockaddr_un a;
    socklen_t al = un_of(&a, NAME);
    int l = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (l < 0 || bind(l, (struct sockaddr *)&a, al) < 0 || listen(l, -1) < 0) {
        say("server: %s\n", ename(errno));
        return 1;
    }
    int on = 1;
    ioctl(l, FIONBIO, &on);
    int pf = open("logs/lobo.pid.new", O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    write(pf, "unix:" NAME "\n", strlen("unix:" NAME "\n"));
    close(pf);
    rename("logs/lobo.pid.new", "logs/lobo.pid");
    int asked = 0, waits = 0, polls = 0;
    for (;;) {
        struct pollfd p = { l, POLLIN, 0 };
        polls++;
        if (poll(&p, 1, 250) <= 0)
            continue;
        int c = accept4(l, 0, 0, SOCK_CLOEXEC | SOCK_NONBLOCK);
        if (c < 0)
            continue;
        char v[512];
        long n;
        while ((n = recv(c, v, sizeof v, 0)) < 0 && errno == EAGAIN) {
            struct pollfd q = { c, POLLIN, 0 };
            waits++;
            poll(&q, 1, 250);
        }
        asked++;
        const char *ans = "unknown verb\n";
        int stop = 0;
        if (n == 7 && !memcmp(v, "status\n", 7))
            ans = ANSWER;
        else if (n == 7 && !memcmp(v, "reload\n", 7))
            ans = "reload complete (generation 2)\n";
        else if (n == 5 && !memcmp(v, "stop\n", 5)) {
            ans = "stop: shutting down (generation 2)\n";
            stop = 1;
        }
        send(c, ans, strlen(ans), MSG_NOSIGNAL);
        close(c);
        if (stop)
            break;
    }
    close(l);
    unlink(NAME);
    unlink("logs/lobo.pid");
    say("server: %d verbs answered; it waited for a verb %s; its name unlinked\n", asked, waits ? "at least once" : "never");
    (void)polls;
    return 0;
}

/* This program's own client: the verb, and what came back. */
static void ask(const char *verb)
{
    struct sockaddr_un a;
    socklen_t al = un_of(&a, NAME);
    int c = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (connect(c, (struct sockaddr *)&a, al) < 0) {
        say("ask %s: connect %s\n", verb, ename(errno));
        close(c);
        return;
    }
    char v[32];
    int m = snprintf(v, sizeof v, "%s\n", verb);
    send(c, v, m, MSG_NOSIGNAL);
    char b[512];
    size_t t = 0;
    long n;
    while (t < sizeof b - 1 && (n = recv(c, b + t, sizeof b - 1 - t, 0)) > 0)
        t += n;
    b[t] = 0;
    say("ask %s: %zu bytes: %s", verb, t, b);
    close(c);
}

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    signal(SIGPIPE, SIG_IGN);
    say("ctl: lobo's control channel\n");
    mkdir("logs", 0755);
    pid_t sv = fork();
    if (sv == 0)
        _exit(server());
    int k = 0;
    struct stat st;
    while (stat("logs/lobo.pid", &st) < 0 && k++ < 500)
        nap(10);
    say("the server's pid file: %s\n", k <= 500 ? "there" : "never came");
    stat(NAME, &st);
    say("its name: %s\n", S_ISSOCK(st.st_mode) ? "a socket" : "not a socket");

    /* lobo's own client. */
    pid_t lc = fork();
    if (lc == 0) {
        char *av[] = { "/bin/lobo", "-c", "conf/lobo.conf", "status", 0 };
        char *ev[] = { "HOME=/", "TERM=linux", "PAX=1", "PATH=/bin", 0 };
        execve(av[0], av, ev);
        say("execve /bin/lobo: %s\n", ename(errno));
        _exit(127);
    }
    int s = -1;
    waitpid(lc, &s, 0);
    say("lobo -c conf/lobo.conf status: %s %d\n", WIFEXITED(s) ? "exit" : "signal", WIFEXITED(s) ? WEXITSTATUS(s) : WTERMSIG(s));

    ask("status");
    ask("reload");
    ask("stop");
    waitpid(sv, &s, 0);
    say("the server ended %d\n", WIFEXITED(s) ? WEXITSTATUS(s) : -1);
    say("its name after: %s\n", stat(NAME, &st) < 0 ? ename(errno) : "still there");
    struct sockaddr_un a;
    socklen_t al = un_of(&a, NAME);
    int c = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    say("connect after stop: %s\n", connect(c, (struct sockaddr *)&a, al) < 0 ? ename(errno) : "ok");
    close(c);
    rmdir("logs");
    say("ctl: done\n");
    return 0;
}
