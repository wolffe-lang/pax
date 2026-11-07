/* gai — px104: names through the C library's resolver, as den and burrow
   find a host (their runtime dials a name through getaddrinfo(3)): for
   each NAME on the command line, one line with the stream addresses
   getaddrinfo answers for it (AF_UNSPEC, SOCK_STREAM, port 443), in its
   order, or the error it gives, by its EAI_ name. The resolver reads
   /etc/hosts and /etc/resolv.conf as it does on Linux; tests/mpx4-console-
   push's N2 gives the image a name in /etc/hosts alone and a DNS fixture
   for the rest.
     gai NAME... */
#define _GNU_SOURCE
#include "say.h"
#include <netdb.h>

static const char *eai(int e)
{
    switch (e) {
    case EAI_NONAME: return "EAI_NONAME";
    case EAI_AGAIN: return "EAI_AGAIN";
    case EAI_FAIL: return "EAI_FAIL";
    case EAI_NODATA: return "EAI_NODATA";
    case EAI_FAMILY: return "EAI_FAMILY";
    case EAI_SOCKTYPE: return "EAI_SOCKTYPE";
    case EAI_SERVICE: return "EAI_SERVICE";
    case EAI_ADDRFAMILY: return "EAI_ADDRFAMILY";
    case EAI_MEMORY: return "EAI_MEMORY";
    case EAI_SYSTEM: return "EAI_SYSTEM";
    }
    return "EAI_?";
}

int main(int argc, char **argv)
{
    for (int i = 1; i < argc; i++) {
        struct addrinfo hints, *res = 0;
        memset(&hints, 0, sizeof hints);
        hints.ai_family = AF_UNSPEC;
        hints.ai_socktype = SOCK_STREAM;
        int e = getaddrinfo(argv[i], "443", &hints, &res);
        if (e) {
            say("gai %s: %s\n", argv[i], eai(e));
            continue;
        }
        char line[512];
        int n = snprintf(line, sizeof line, "gai %s:", argv[i]);
        for (struct addrinfo *p = res; p && n < (int)sizeof line - 64; p = p->ai_next) {
            char ip[64] = "?";
            int port = 0;
            if (p->ai_family == AF_INET) {
                struct sockaddr_in *s = (struct sockaddr_in *)p->ai_addr;
                inet_ntop(AF_INET, &s->sin_addr, ip, sizeof ip);
                port = ntohs(s->sin_port);
            } else if (p->ai_family == AF_INET6) {
                struct sockaddr_in6 *s = (struct sockaddr_in6 *)p->ai_addr;
                inet_ntop(AF_INET6, &s->sin6_addr, ip, sizeof ip);
                port = ntohs(s->sin6_port);
            }
            n += snprintf(line + n, sizeof line - n, " %s %s:%d", p->ai_family == AF_INET6 ? "inet6" : "inet", ip, port);
        }
        freeaddrinfo(res);
        say("%s\n", line);
    }
    return 0;
}
