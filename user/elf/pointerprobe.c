/* px117: an original black-box probe of the console's pointer and of the
 * mouse reports it types. No terminal emulator's, kernel's or C library's
 * source was consulted. The modes and the report encoding are read only as
 * the XTerm Control Sequences document gives them ("Mouse Tracking":
 * button-event tracking, 1002; SGR, 1006); the program prints every byte it
 * reads as hex, so tools/pointer-session judges them by the document
 * independently of this program. Results go to stdout (the console).
 *
 * The console's input is put in raw mode (its output keeps OPOST and ONLCR,
 * so the screen's lines start at the left). `PTRWIN <rows> <cols>` first, then for
 * each row `PTRREADY <i> <label>`, and for each step of a row `PTRSTEP <i>
 * <k>`: the host does the step's injections, then types `.` (on the USB
 * keyboard, and from keys-interleaved's second step on the PS/2 one).
 * Whoever reads for the step reads the console until that `.` (8 s at
 * most) and prints `PTRIN <i> <k> <hex>` (`-` for no byte; `+<hex>`
 * after it for bytes read past the `.` in the same read; ` TIMEOUT` when no
 * `.` came). `PTRROW <label>` ends a row, `PTRDONE` the run.
 *
 * The rows (tools/pointer-session's ROWS, in this order):
 *   pointer-drawn     no mode; the host reads the screen before the first
 *                     motion and with the pointer on two cells (step 0)
 *   pointer-scroll    no mode; the pointer on a cell (0), the screen
 *                     scrolled under it, then read (1)
 *   no-mode           a click with no mode set (0); with 1002 and 1006 (1)
 *   sgr-buttons       left, middle and right at three cells (0)
 *   drag              a left drag with a move inside one cell (0); a right
 *                     drag (1)
 *   wheel             up, down, up (0)
 *   modifiers         Shift, Ctrl, Alt, Shift+Ctrl with left; Ctrl with
 *                     the wheel (0)
 *   relative          the relative mouse: to the corner, then a known
 *                     number of pixels (0); far past the far corner (1)
 *   reset             a click (0); after DECRST 1002 and 1006 (1); set
 *                     again (2); after RIS, ESC c (3)
 *   unserved          1002 alone (0); 1006 alone (1); 1000 with 1006 (2);
 *                     1003 with 1006 (3); 9 with 1006 (4); 1006 then 1002
 *                     (5); then DECRST 1000, not the selected one (6);
 *                     then 1005 in 1006's place (7)
 *   owner-exits       the probe's own mode (0); a child's that exits
 *                     without resetting it (1); a child's killed by
 *                     SIGKILL (2); the probe's own again (3)
 *   owner-background  a child's mode set from its own background group,
 *                     the probe in the foreground (0); that child given the
 *                     foreground, reading (1); after it ended (2); the
 *                     probe's own (3)
 *   keys-interleaved  clicks, the wheel and keys 20 ms apart on the USB
 *                     keyboard (0); 3 ms apart on the PS/2 keyboard (1)
 *   pty               a child on a pty's slave sets the modes there; the
 *                     master's bytes printed; a click on the console (0);
 *                     a report the master writes, read on the slave; then
 *                     the probe's own mode (1)
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static const char *labels[] = {
    "pointer-drawn", "pointer-scroll", "no-mode", "sgr-buttons", "drag", "wheel",
    "modifiers", "relative", "reset", "unserved", "owner-exits", "owner-background",
    "keys-interleaved", "pty"
};
enum {
    DRAWN, SCROLL, NOMODE, BUTTONS, DRAG, WHEEL, MODS, REL, RESET, UNSERVED,
    EXITS, BACKGROUND, KEYS, PTY, ROWS
};

#define ON "\033[?1002h\033[?1006h"
#define OFF "\033[?1002l\033[?1006l"
#define ALLOFF "\033[?9l\033[?1000l\033[?1001l\033[?1002l\033[?1003l\033[?1005l\033[?1006l\033[?1015l\033[?1016l"

static long long now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (long long)t.tv_sec * 1000000000LL + t.tv_nsec;
}

static void out(int fd, const char *s) {
    size_t n = strlen(s), done = 0;
    while (done < n) {
        ssize_t k = write(fd, s + done, n - done);
        if (k < 0) { if (errno == EINTR) continue; return; }
        done += (size_t)k;
    }
}

static void hex(const unsigned char *b, int n) {
    for (int i = 0; i < n; i++) printf("%02x", b[i]);
}

/* Read `fd` until the byte `.` (at most `ms`), then print the step's
 * PTRIN line: the bytes before the `.`, any read past it in the same read,
 * and TIMEOUT when no `.` came. */
static void step_in(int fd, int row, int k, int ms) {
    unsigned char got[4096], past[256];
    int n = 0, extra = 0, seen = 0;
    long long end = now() + (long long)ms * 1000000LL;
    while (!seen) {
        long long left = end - now();
        if (left <= 0) break;
        struct pollfd p = {fd, POLLIN, 0};
        int r = poll(&p, 1, (int)(left / 1000000) + 1);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) break;
        unsigned char c[256];
        ssize_t m = read(fd, c, sizeof c);
        if (m < 0 && (errno == EINTR || errno == EAGAIN)) continue;
        if (m <= 0) break;
        for (ssize_t i = 0; i < m; i++) {
            if (seen) { if (extra < (int)sizeof past) past[extra++] = c[i]; }
            else if (c[i] == '.') seen = 1;
            else if (n < (int)sizeof got) got[n++] = c[i];
        }
    }
    printf("PTRIN %d %d ", row, k);
    if (n) hex(got, n); else printf("-");
    if (extra) { printf(" +"); hex(past, extra); }
    printf("%s\n", seen ? "" : " TIMEOUT");
}

static void step(int row, int k) {
    printf("PTRSTEP %d %d\n", row, k);
}

/* One step the probe itself reads: the modes `pre` written first. */
static void own(int row, int k, const char *pre) {
    if (pre) out(1, pre);
    step(row, k);
    step_in(0, row, k, 8000);
}

static void reap(pid_t c, const char *what) {
    int st = 0;
    if (waitpid(c, &st, 0) != c) { printf("PTRNOTE %s waitpid errno=%d\n", what, errno); return; }
    if (WIFSIGNALED(st)) printf("PTRNOTE %s signal %d\n", what, WTERMSIG(st));
    else printf("PTRNOTE %s exit %d\n", what, WEXITSTATUS(st));
}

static void row_owner_exits(int row) {
    own(row, 0, ON);
    out(1, OFF);
    pid_t c = fork();
    if (c == 0) { out(1, ON); _exit(0); }
    reap(c, "exit-child");
    own(row, 1, 0);
    c = fork();
    if (c == 0) { out(1, ON); raise(SIGKILL); _exit(9); }
    reap(c, "killed-child");
    own(row, 2, 0);
    own(row, 3, ON);
    out(1, OFF);
}

static void row_background(int row) {
    int set[2], go[2];
    if (pipe(set) || pipe(go)) { printf("PTRNOTE pipe errno=%d\n", errno); return; }
    pid_t c = fork();
    if (c == 0) {
        close(set[0]); close(go[1]);
        setpgid(0, 0);
        out(1, ON); /* from a background group: TOSTOP is clear */
        if (write(set[1], "s", 1) != 1) _exit(3);
        char b;
        if (read(go[0], &b, 1) != 1) _exit(4);
        step(row, 1);
        step_in(0, row, 1, 8000);
        _exit(0); /* without resetting the modes */
    }
    close(set[1]); close(go[0]);
    setpgid(c, c);
    char b;
    if (read(set[0], &b, 1) != 1) printf("PTRNOTE background child did not set its mode\n");
    printf("PTRNOTE foreground %d, the child's group %d\n", (int)tcgetpgrp(0), (int)c);
    own(row, 0, 0);
    if (tcsetpgrp(0, c)) printf("PTRNOTE tcsetpgrp child errno=%d\n", errno);
    if (write(go[1], "g", 1) != 1) printf("PTRNOTE go errno=%d\n", errno);
    reap(c, "background-child");
    signal(SIGTTOU, SIG_IGN);
    if (tcsetpgrp(0, getpgrp())) printf("PTRNOTE tcsetpgrp back errno=%d\n", errno);
    signal(SIGTTOU, SIG_DFL);
    close(set[0]); close(go[1]);
    own(row, 2, 0);
    own(row, 3, ON);
    out(1, OFF);
}

static void row_pty(int row) {
    int m = posix_openpt(O_RDWR | O_NOCTTY);
    if (m < 0 || grantpt(m) || unlockpt(m)) { printf("PTRNOTE ptmx errno=%d\n", errno); own(row, 0, 0); own(row, 1, ON); out(1, OFF); return; }
    char name[64];
    if (ptsname_r(m, name, sizeof name)) { printf("PTRNOTE ptsname errno=%d\n", errno); return; }
    pid_t c = fork();
    if (c == 0) {
        setsid();
        int s = open(name, O_RDWR | O_NOCTTY);
        if (s < 0) { printf("PTRNOTE slave open errno=%d\n", errno); _exit(2); }
        struct termios t;
        if (tcgetattr(s, &t) == 0) { cfmakeraw(&t); t.c_cc[VMIN] = 1; t.c_cc[VTIME] = 0; tcsetattr(s, TCSANOW, &t); }
        out(s, ON);
        unsigned char got[256];
        int n = 0, seen = 0;
        long long end = now() + 10000000000LL;
        while (!seen && now() < end) {
            struct pollfd p = {s, POLLIN, 0};
            if (poll(&p, 1, 200) <= 0) continue;
            unsigned char ch[64];
            ssize_t k = read(s, ch, sizeof ch);
            for (ssize_t i = 0; i < k; i++) {
                if (ch[i] == '.') { seen = 1; break; }
                if (n < (int)sizeof got) got[n++] = ch[i];
            }
        }
        printf("PTRPTY slave ");
        if (n) hex(got, n); else printf("-");
        printf("%s\n", seen ? "" : " TIMEOUT");
        _exit(0);
    }
    /* The master: what the slave wrote, until 16 bytes or 3 s. */
    unsigned char got[256];
    int n = 0;
    long long end = now() + 3000000000LL;
    while (n < 16 && now() < end) {
        struct pollfd p = {m, POLLIN, 0};
        if (poll(&p, 1, 100) <= 0) continue;
        ssize_t k = read(m, got + n, sizeof got - n);
        if (k > 0) n += (int)k;
    }
    printf("PTRPTY master ");
    if (n) hex(got, n); else printf("-");
    printf("\n");
    own(row, 0, 0);
    out(m, "\033[<0;3;4M.");
    reap(c, "pty-child");
    close(m);
    own(row, 1, ON);
    out(1, OFF);
}

int main(void) {
    setvbuf(stdout, 0, _IONBF, 0);
    struct termios raw;
    if (tcgetattr(0, &raw) == 0) {
        cfmakeraw(&raw);
        raw.c_oflag |= OPOST | ONLCR; /* the screen keeps its lines; the input is raw */
        raw.c_cc[VMIN] = 1;
        raw.c_cc[VTIME] = 0;
        if (tcsetattr(0, TCSANOW, &raw)) printf("PTRNOTE tcsetattr errno=%d\n", errno);
    } else {
        printf("PTRNOTE tcgetattr errno=%d\n", errno);
    }
    struct winsize w = {0};
    ioctl(0, TIOCGWINSZ, &w);
    printf("PTRWIN %d %d\n", w.ws_row, w.ws_col);
    out(1, ALLOFF);
    for (int row = 0; row < ROWS; row++) {
        tcflush(0, TCIFLUSH);
        printf("PTRREADY %d %s\n", row, labels[row]);
        switch (row) {
        case DRAWN:
            own(row, 0, 0);
            break;
        case SCROLL:
            own(row, 0, 0);
            for (int i = 0; i < 60; i++) printf("PTRFILL %d the screen scrolls under the pointer\n", i);
            own(row, 1, 0);
            break;
        case NOMODE:
            own(row, 0, 0);
            own(row, 1, ON);
            out(1, OFF);
            break;
        case BUTTONS: case WHEEL: case MODS:
            own(row, 0, ON);
            out(1, OFF);
            break;
        case DRAG: case REL:
            own(row, 0, ON);
            own(row, 1, 0);
            out(1, OFF);
            break;
        case RESET:
            own(row, 0, ON);
            own(row, 1, OFF);
            own(row, 2, ON);
            own(row, 3, "\033c");
            out(1, ALLOFF);
            break;
        case UNSERVED:
            own(row, 0, ALLOFF "\033[?1002h");
            own(row, 1, ALLOFF "\033[?1006h");
            own(row, 2, ALLOFF "\033[?1000h\033[?1006h");
            own(row, 3, ALLOFF "\033[?1003h\033[?1006h");
            own(row, 4, ALLOFF "\033[?9h\033[?1006h");
            own(row, 5, ALLOFF "\033[?1006h\033[?1002h");
            own(row, 6, "\033[?1000l");
            own(row, 7, "\033[?1005h");
            out(1, ALLOFF);
            break;
        case EXITS:
            row_owner_exits(row);
            break;
        case BACKGROUND:
            row_background(row);
            break;
        case KEYS:
            own(row, 0, ON);
            own(row, 1, 0);
            out(1, OFF);
            break;
        case PTY:
            row_pty(row);
            break;
        }
        printf("PTRROW %s\n", labels[row]);
    }
    out(1, ALLOFF);
    printf("PTRDONE\n");
    return 0;
}
