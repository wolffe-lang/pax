/* tcpbulk — a transfer with a digest (px23). The stream is say.h's
   pattern, so both ends can make it.

     tcpbulk send IP PORT BYTES
         connect, send BYTES of the pattern, close this end's half, and
         read the one line the receiver says (what it got)
     tcpbulk recv PORT READY-IP READY-PORT [nap MS]
         listen on PORT, say "ready" to READY-IP:READY-PORT with one
         UDP datagram, take one connection, read to its end, say what
         came ("got N bytes, crc X") and close. With `nap MS` it reads
         nothing for MS milliseconds first: the sender fills this
         end's window and has to wait for it to open again
     tcpbulk leave IP PORT BYTES
         connect, write BYTES of the pattern and close at once, bytes
         still unsent: they and the FIN after them are the kernel's to
         deliver, with no process left
     tcpbulk loop BYTES
         both on this machine, across fork, over 127.0.0.1 port 4040

   Each prints the bytes and the CRC-32 it saw; `recv` also says
   whether every byte was the pattern's. */
#include "say.h"
#include <stdlib.h>
#include <sys/wait.h>
#include <time.h>

static unsigned char buf[65536], want[65536];

static int do_send(const char *ip, int port, unsigned long long bytes, const char *who, int leave)
{
    struct sockaddr_in srv = sin_of(ip, port);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0 || connect(fd, (struct sockaddr *)&srv, sizeof srv) < 0) {
        say("%s: socket or connect: %s\n", who, ename(errno));
        return 1;
    }
    unsigned long long off = 0;
    unsigned long crc = 0;
    size_t piece = 1000; /* the first write is not a multiple of anything */
    while (off < bytes) {
        size_t n = bytes - off < piece ? (size_t)(bytes - off) : piece;
        pattern_fill(buf, off, n);
        if (send_all(fd, buf, n) != (ssize_t)n) {
            say("%s: send at %llu: %s\n", who, off, ename(errno));
            return 1;
        }
        crc = crc32_of(crc, buf, n);
        off += n;
        piece = piece == 1000 ? 65536 : piece == 65536 ? 16384 : piece == 16384 ? 4099 : 65536;
    }
    if (leave) {
        close(fd);
        say("%s: wrote %llu bytes, crc %08lx, and closed at once\n", who, off, crc);
        return 0;
    }
    if (shutdown(fd, SHUT_WR) < 0) {
        say("%s: shutdown: %s\n", who, ename(errno));
        return 1;
    }
    char line[128];
    ssize_t t = recv_all(fd, line, sizeof line - 1);
    if (t < 0) {
        say("%s: the receiver's line: %s\n", who, ename(errno));
        return 1;
    }
    while (t > 0 && line[t - 1] == '\n')
        t--;
    say("%s: sent %llu bytes, crc %08lx; the receiver said \"%.*s\"\n", who, off, crc, (int)t, line);
    close(fd);
    return 0;
}

static int do_recv(int lfd, const char *who, long nap_ms)
{
    int c = accept(lfd, 0, 0);
    if (c < 0) {
        say("%s: accept: %s\n", who, ename(errno));
        return 1;
    }
    if (nap_ms > 0) {
        struct timespec ts = {nap_ms / 1000, (nap_ms % 1000) * 1000000L};
        nanosleep(&ts, 0);
    }
    unsigned long long off = 0;
    unsigned long crc = 0;
    int right = 1;
    for (;;) {
        ssize_t n = recv(c, buf, sizeof buf, 0);
        if (n < 0) {
            say("%s: recv at %llu: %s\n", who, off, ename(errno));
            return 1;
        }
        if (n == 0)
            break;
        pattern_fill(want, off, n);
        if (memcmp(buf, want, n) != 0)
            right = 0;
        crc = crc32_of(crc, buf, n);
        off += n;
    }
    /* Said before the line goes back: the sender prints only once it
       has read that line, so over loopback the two come in one order. */
    say("%s: received %llu bytes, crc %08lx, %s\n", who, off, crc, right ? "every byte the pattern's" : "NOT the pattern");
    char line[96];
    int m = snprintf(line, sizeof line, "got %llu bytes, crc %08lx\n", off, crc);
    if (send_all(c, line, m) != m) {
        say("%s: the line back: %s\n", who, ename(errno));
        return 1;
    }
    close(c);
    return right ? 0 : 1;
}

static int listener(int port)
{
    int one = 1, fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in me = sin_of("0.0.0.0", port);
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one) < 0
        || bind(fd, (struct sockaddr *)&me, sizeof me) < 0 || listen(fd, 1) < 0) {
        say("tcpbulk: socket, bind or listen on port %d: %s\n", port, ename(errno));
        return -1;
    }
    return fd;
}

int main(int argc, char **argv)
{
    if (argc == 5 && strcmp(argv[1], "send") == 0)
        return do_send(argv[2], atoi(argv[3]), strtoull(argv[4], 0, 10), "tcpbulk send", 0);
    if (argc == 5 && strcmp(argv[1], "leave") == 0)
        return do_send(argv[2], atoi(argv[3]), strtoull(argv[4], 0, 10), "tcpbulk leave", 1);
    if ((argc == 5 || (argc == 7 && strcmp(argv[5], "nap") == 0)) && strcmp(argv[1], "recv") == 0) {
        int fd = listener(atoi(argv[2]));
        if (fd < 0)
            return 1;
        struct sockaddr_in ready = sin_of(argv[3], atoi(argv[4]));
        int u = socket(AF_INET, SOCK_DGRAM, 0);
        if (u < 0 || sendto(u, "ready", 5, 0, (struct sockaddr *)&ready, sizeof ready) != 5) {
            say("tcpbulk recv: ready: %s\n", ename(errno));
            return 1;
        }
        close(u);
        int r = do_recv(fd, "tcpbulk recv", argc == 7 ? atol(argv[6]) : 0);
        close(fd);
        return r;
    }
    if (argc == 3 && strcmp(argv[1], "loop") == 0) {
        int fd = listener(4040);
        if (fd < 0)
            return 1;
        pid_t pid = fork();
        if (pid < 0) {
            say("tcpbulk loop: fork: %s\n", ename(errno));
            return 1;
        }
        if (pid == 0) {
            close(fd);
            _exit(do_send("127.0.0.1", 4040, strtoull(argv[2], 0, 10), "tcpbulk loop, the sender", 0));
        }
        int r = do_recv(fd, "tcpbulk loop, the receiver", 0);
        int st = 0;
        waitpid(pid, &st, 0);
        say("tcpbulk loop: the sender ended with status %d\n", WIFEXITED(st) ? WEXITSTATUS(st) : -1);
        close(fd);
        return r || !WIFEXITED(st) || WEXITSTATUS(st);
    }
    say("usage: tcpbulk send IP PORT BYTES | recv PORT READY-IP READY-PORT [nap MS] | leave IP PORT BYTES | loop BYTES\n");
    return 2;
}
