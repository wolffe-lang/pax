/* vtcases — px59's VT cases played on PAX's console (tests/mpx5-screen S1).
 *
 *   vtcases [FILE]          (default /etc/vtcases)
 *
 * FILE is tests/mpx5-screen.d/vtcases.py's two probes, the bytes each of
 * px59's VT probes (notes/px59/vtprobe.c, vtprobe2.c) sent a Linux VT, as
 * records: a kind byte, a NUL-terminated name, a four-byte little-endian
 * length, the bytes. In the VT probes' order, on descriptor 0 put in raw
 * mode as they put the VT (cfmakeraw), each record is what the probe did:
 *   s  a screen: ESC[0m ESC[2J ESC[H, the bytes, then an OSC string that
 *      names it (`ESC ] px59;NAME BEL`, which the screen consumes and the
 *      serial log keeps), and one byte read: the suite's keyboard key,
 *      sent once it has taken the screen
 *   e  the bytes alone
 *   p  the palette: the clear, 256 cells `ESC[0;38;5;iX` (FG) or
 *      `ESC[0;48;5;iX` (BG), the OSC string, one byte read
 *   a  a query: the input flushed, the bytes, then what comes back until
 *      300 ms pass with nothing more; kept, and printed only at the end
 *      (`QUERY NAME hex...|none`), so the screen holds what the VT's did
 *   c  a query in canonical mode with ECHO and ECHOCTL (the terminal as
 *      found): the bytes, 400 ms, the OSC string; then raw again, one
 *      byte read, the input flushed
 *   r  the start of the next probe: a fresh VT; the screen's own state is
 *      reset as far as bytes can (ESC[?1049l, ESC[0m, ESC[?25h, ESC[2J,
 *      ESC[H, DECSC at home)
 * Before the first record it prints `vtcases: ready` and reads one byte
 * (the keyboard's: the device last typed at, so the screen's answers
 * are typed into the input); at the end `vtcases: done`.
 *
 * termios(3), poll(2), tcflush(3). Built by tools/mkvtcases (static, as
 * user/elf/as.c). Exit 0, 1 on a short or unreadable FILE. */
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static struct termios cooked, raw;
static char answers[16384];
static size_t alen;

static void put(const void *p, size_t n) {
    const char *c = p;
    while (n > 0) {
        ssize_t k = write(1, c, n);
        if (k <= 0) _exit(3);
        c += k;
        n -= (size_t)k;
    }
}

static void puts1(const char *s) { put(s, strlen(s)); }

static void marker(const char *name) {
    puts1("\033]px59;");
    puts1(name);
    puts1("\007");
}

static void key(void) {
    unsigned char b;
    if (read(0, &b, 1) < 0) _exit(4);
}

static void nap(long ms) {
    struct timespec t = {ms / 1000, (ms % 1000) * 1000000L};
    nanosleep(&t, NULL);
}

static const char CLEAR[] = "\033[0m\033[2J\033[H";

int main(int argc, char **argv) {
    const char *path = argc > 1 ? argv[1] : "/etc/vtcases";
    int fd = open(path, O_RDONLY);
    if (fd < 0) { perror(path); return 1; }
    static unsigned char buf[1 << 16];
    ssize_t n = read(fd, buf, sizeof buf);
    close(fd);
    if (n <= 0) { fprintf(stderr, "vtcases: %s: empty\n", path); return 1; }
    tcgetattr(0, &cooked);
    raw = cooked;
    cfmakeraw(&raw);
    tcsetattr(0, TCSANOW, &raw);
    puts1("vtcases: ready\r\n");
    key();
    tcflush(0, TCIFLUSH);
    size_t i = 0;
    while (i < (size_t)n) {
        char kind = (char)buf[i++];
        const char *name = (const char *)buf + i;
        i += strlen(name) + 1;
        if (i + 4 > (size_t)n) { fprintf(stderr, "vtcases: short record\n"); return 1; }
        size_t len = buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | ((size_t)buf[i + 3] << 24);
        i += 4;
        if (i + len > (size_t)n) { fprintf(stderr, "vtcases: short bytes\n"); return 1; }
        const unsigned char *data = buf + i;
        i += len;
        switch (kind) {
        case 's':
            puts1(CLEAR);
            put(data, len);
            marker(name);
            key();
            break;
        case 'e':
            put(data, len);
            break;
        case 'p':
            puts1(CLEAR);
            for (int k = 0; k < 256; k++) {
                char s[32];
                snprintf(s, sizeof s, "\033[0;%d;5;%dmX", name[0] == 'B' ? 48 : 38, k);
                puts1(s);
            }
            marker(name);
            key();
            break;
        case 'a': {
            unsigned char got[256];
            int m = 0;
            tcflush(0, TCIFLUSH);
            put(data, len);
            struct pollfd p = {0, POLLIN, 0};
            while (m < (int)sizeof got && poll(&p, 1, 300) > 0) {
                ssize_t k = read(0, got + m, sizeof got - m);
                if (k <= 0) break;
                m += (int)k;
            }
            alen += snprintf(answers + alen, sizeof answers - alen, "QUERY %s", name);
            for (int k = 0; k < m; k++) alen += snprintf(answers + alen, sizeof answers - alen, " %02x", got[k]);
            alen += snprintf(answers + alen, sizeof answers - alen, "%s\r\n", m ? "" : " none");
            break;
        }
        case 'c':
            tcsetattr(0, TCSANOW, &cooked);
            put(data, len);
            nap(400);
            marker(name);
            tcsetattr(0, TCSANOW, &raw);
            key();
            tcflush(0, TCIFLUSH);
            break;
        case 'r':
            puts1("\033[?1049l\033[0m\033[?25h\033[2J\033[H\0337");
            break;
        default:
            fprintf(stderr, "vtcases: kind %c\n", kind);
            return 1;
        }
    }
    tcsetattr(0, TCSANOW, &cooked);
    puts1(CLEAR);
    put(answers, alen);
    puts1("vtcases: done\r\n");
    return 0;
}
