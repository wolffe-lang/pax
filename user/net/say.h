/* say.h — what the network witnesses share (px22): one line to
   descriptor 1 with write(2) and no stdio buffer (a fork must not copy
   unwritten text), errno by its name, and sockaddr_in helpers. */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static void say(const char *fmt, ...)
{
    char b[768];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1)
        n = sizeof b - 1;
    int off = 0;
    while (off < n) {
        ssize_t w = write(1, b + off, n - off);
        if (w <= 0)
            break;
        off += w;
    }
}

static const char *ename(int e)
{
    switch (e) {
    case 0: return "0";
    case EBADF: return "EBADF";
    case EAGAIN: return "EAGAIN";
    case EFAULT: return "EFAULT";
    case EINVAL: return "EINVAL";
    case ESPIPE: return "ESPIPE";
    case EPIPE: return "EPIPE";
    case ENOTSOCK: return "ENOTSOCK";
    case EDESTADDRREQ: return "EDESTADDRREQ";
    case EMSGSIZE: return "EMSGSIZE";
    case EPROTOTYPE: return "EPROTOTYPE";
    case ENOPROTOOPT: return "ENOPROTOOPT";
    case EPROTONOSUPPORT: return "EPROTONOSUPPORT";
    case ESOCKTNOSUPPORT: return "ESOCKTNOSUPPORT";
    case EOPNOTSUPP: return "EOPNOTSUPP";
    case EAFNOSUPPORT: return "EAFNOSUPPORT";
    case EADDRINUSE: return "EADDRINUSE";
    case EADDRNOTAVAIL: return "EADDRNOTAVAIL";
    case ENETDOWN: return "ENETDOWN";
    case ENETUNREACH: return "ENETUNREACH";
    case ENOBUFS: return "ENOBUFS";
    case EISCONN: return "EISCONN";
    case ENOTCONN: return "ENOTCONN";
    case ECONNREFUSED: return "ECONNREFUSED";
    case EHOSTUNREACH: return "EHOSTUNREACH";
    case ENOSYS: return "ENOSYS";
    case EACCES: return "EACCES";
    case EPERM: return "EPERM";
    case ENOMEM: return "ENOMEM";
    case EMFILE: return "EMFILE";
    case ENFILE: return "ENFILE";
    case EINTR: return "EINTR";
    }
    return "E?";
}

/* "ok" or "<n>" for a call that worked, "-ENAME" for one that did not. */
__attribute__((unused)) static const char *res(long r, char *buf, size_t cap, int show)
{
    if (r < 0)
        snprintf(buf, cap, "-%s", ename(errno));
    else if (show)
        snprintf(buf, cap, "%ld", r);
    else
        snprintf(buf, cap, "ok");
    return buf;
}

__attribute__((unused)) static struct sockaddr_in sin_of(const char *ip, int port)
{
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    inet_pton(AF_INET, ip, &a.sin_addr);
    return a;
}

/* a.b.c.d:port, with the port as "ephemeral" when it lies in Linux's
   default local range (ip(7): 32768 to 60999), whose pick differs from
   run to run. */
__attribute__((unused)) static const char *aname(const struct sockaddr_in *a, char *buf, size_t cap)
{
    char ip[32];
    int p = ntohs(a->sin_port);
    inet_ntop(AF_INET, &a->sin_addr, ip, sizeof ip);
    if (p >= 32768 && p <= 60999)
        snprintf(buf, cap, "%s:ephemeral", ip);
    else
        snprintf(buf, cap, "%s:%d", ip, p);
    return buf;
}
