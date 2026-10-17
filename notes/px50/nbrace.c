/* px50 (pax#79): why tests/mpx4-ready's nbprobe row `a write of 1 then`
 * races on Linux, measured. Each round does what nbprobe does — a TCP
 * connection over loopback, the accepted end made non-blocking, `send`
 * of 65536-byte blocks until -EAGAIN — and then, in mode `old`, asks
 * `write(s, "z", 1)` at once (nbprobe's row), counting how often it is
 * not -EAGAIN; in mode `watch`, it does not write but samples what the
 * end says after the -EAGAIN (poll's POLLOUT at once and after 1, 10
 * and 100 ms, the bytes not yet sent, SIOCOUTQ, and the peer's unread
 * bytes, SIOCINQ, `tcp(7)`); in mode `new`, it settles first — sends
 * again while poll(POLLOUT) says writable within 200 ms, until it stays
 * unwritable that long — and then asks the write, as the fixed nbprobe
 * does; `when` times the first fall of SIOCOUTQ; `old-slow` and
 * `new-slow` wait 60 ms before the write (a runner slow to the row).
 * Written from tcp(7), socket(7), poll(2), send(2); no kernel's
 * source.   nbrace old|old-slow|watch|when|new|new-slow ROUNDS PORT */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/sockios.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static char buf[65536];
static int hist[11];

static void nap(int ms) {
    struct timespec ts = {ms / 1000, (long)(ms % 1000) * 1000000L};
    nanosleep(&ts, 0);
}

static int writable(int s, int ms) {
    struct pollfd p = {s, POLLOUT, 0};
    return poll(&p, 1, ms) == 1 && (p.revents & POLLOUT);
}

static long fill(int s) {
    long put = 0, w;
    while ((w = send(s, buf, sizeof buf, MSG_NOSIGNAL)) > 0) put += w;
    return put;
}

int main(int argc, char **argv) {
    if (argc < 4) return 2;
    const char *mode = argv[1];
    int rounds = atoi(argv[2]);
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(0x7f000001);
    a.sin_port = htons((unsigned short)atoi(argv[3]));
    int one = 1;
    int l = socket(AF_INET, SOCK_STREAM, 0);
    setsockopt(l, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    if (bind(l, (struct sockaddr *)&a, sizeof a) || listen(l, 8)) { perror("listen"); return 2; }
    int racy = 0, again_later = 0, settle_rounds_max = 0;
    long more_max = 0;
    int w_now = 0, w1 = 0, w10 = 0, w100 = 0;
    long outq_drop = 0, inq_grow = 0, taken_late = 0, late_max = 0;
    for (int r = 0; r < rounds; r++) {
        int c = socket(AF_INET, SOCK_STREAM, 0);
        if (connect(c, (struct sockaddr *)&a, sizeof a)) { perror("connect"); return 2; }
        int s = accept(l, 0, 0);
        fcntl(s, F_SETFL, fcntl(s, F_GETFL) | O_NONBLOCK);
        fill(s);
        if (strncmp(mode, "old", 3) == 0) {
            if (strcmp(mode, "old-slow") == 0) nap(60); /* a runner that is slow to the row */
            long w = write(s, "z", 1);
            if (w == 1) racy++;
        } else if (strcmp(mode, "when") == 0) {
            /* the first time, in 2 ms steps up to 400 ms, that SIOCOUTQ
             * falls after the -EAGAIN */
            int q0 = 0, q = 0, t = -1;
            ioctl(s, SIOCOUTQ, &q0);
            for (int ms = 0; ms <= 400; ms += 2) {
                ioctl(s, SIOCOUTQ, &q);
                if (q < q0) { t = ms; break; }
                nap(2);
            }
            int b = t < 0 ? 10 : t / 10 > 9 ? 9 : t / 10;
            hist[b]++;
        } else if (strcmp(mode, "watch") == 0) {
            int q0 = 0, qa = 0, qb = 0, q1 = 0, i0 = 0, i1 = 0;
            ioctl(s, SIOCOUTQ, &q0);
            ioctl(c, SIOCINQ, &i0);
            if (writable(s, 0)) w_now++;
            nap(1); if (writable(s, 0)) w1++;
            ioctl(s, SIOCOUTQ, &qa);
            nap(9); if (writable(s, 0)) w10++;
            ioctl(s, SIOCOUTQ, &qb);
            nap(90); if (writable(s, 0)) w100++;
            ioctl(s, SIOCOUTQ, &q1);
            ioctl(c, SIOCINQ, &i1);
            if (q1 < q0) outq_drop++;
            if (i1 > i0) inq_grow++;
            long w = write(s, "z", 1);
            if (w == 1) taken_late++;
            long more = fill(s);
            if (more > late_max) late_max = more;
            if (r < 3) printf("watch round %d: after -EAGAIN SIOCOUTQ %d, 1 ms %d, 10 ms %d, 100 ms %d; the peer's SIOCINQ %d -> %d; a write of 1 then %ld, then %ld bytes more\n", r, q0, qa, qb, q1, i0, i1, w, more);
        } else {
            /* nbprobe's settling: wait 100 ms (past the peer's delayed
             * acknowledgement, 30-49 ms here: `when`) and fill again,
             * until a fill after the wait takes nothing. */
            int k = 0;
            long more = 0, m;
            for (;;) { nap(100); m = fill(s); if (m <= 0) break; more += m; k++; }
            if (k > settle_rounds_max) settle_rounds_max = k;
            if (more > more_max) more_max = more;
            if (k > 0) again_later++;
            if (strcmp(mode, "new-slow") == 0) nap(60);
            long w = write(s, "z", 1);
            if (w == 1) racy++;
        }
        close(s);
        close(c);
    }
    if (strcmp(mode, "when") == 0) {
        printf("when: %d rounds; SIOCOUTQ first fell after the -EAGAIN at:", rounds);
        for (int i = 0; i < 9; i++) printf(" %d-%d ms %d;", i * 10, i * 10 + 9, hist[i]);
        printf(" 90-400 ms %d; not within 400 ms %d\n", hist[9], hist[10]);
    } else if (strcmp(mode, "watch") == 0)
        printf("watch: %d rounds; writable (POLLOUT) again after the -EAGAIN: at once %d, 1 ms %d, 10 ms %d, 100 ms %d; SIOCOUTQ fell %ld, the peer's SIOCINQ grew %ld; a write of 1 after 100 ms taken %ld, then at most %ld bytes more\n",
               rounds, w_now, w1, w10, w100, outq_drop, inq_grow, taken_late, late_max);
    else if (strncmp(mode, "old", 3) == 0)
        printf("%s: %d rounds; a write of 1 after the -EAGAIN%s was taken %d times\n", mode, rounds, strcmp(mode, "old-slow") == 0 ? " and 60 ms" : " at once", racy);
    else
        printf("%s: %d rounds; a fill after 100 ms took more in %d (at most %d more fills, %ld more bytes); a write of 1 after settling%s taken %d times\n",
               mode, rounds, again_later, settle_rounds_max, more_max, strcmp(mode, "new-slow") == 0 ? " and 60 ms" : "", racy);
    return 0;
}
