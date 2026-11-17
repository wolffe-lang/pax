/* A console-only witness: draw the promised glyphs, then report raw keys.
 * No shell, multiplexer, timer benchmark or additional program is needed. */
#define _DEFAULT_SOURCE
#include <errno.h>
#include <poll.h>
#include <stdio.h>
#include <termios.h>
#include <unistd.h>

static void glyph(unsigned cp) {
    if (cp < 0x800) {
        putchar(0xc0 | (cp >> 6));
        putchar(0x80 | (cp & 63));
    } else {
        putchar(0xe0 | (cp >> 12));
        putchar(0x80 | ((cp >> 6) & 63));
        putchar(0x80 | (cp & 63));
    }
}

int main(void) {
    struct termios old, raw;
    if (tcgetattr(0, &old)) return 2;
    raw = old;
    cfmakeraw(&raw);
    if (tcsetattr(0, TCSANOW, &raw)) return 2;
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("\033[0m\033[2J\033[H\033[?25l");
    /* Eight rows of box drawing, then arrows and powerline separators. */
    for (unsigned i = 0; i < 128; ++i) {
        printf("\033[%u;%uH", 1 + i / 16, 1 + i % 16);
        glyph(0x2500 + i);
    }
    printf("\033[9;1H");
    for (unsigned cp = 0x2190; cp <= 0x2193; ++cp) glyph(cp);
    printf("\033[10;1H");
    for (unsigned cp = 0xe0b0; cp <= 0xe0b3; ++cp) glyph(cp);
    printf("\033[11;1H");
    for (unsigned cp = 0xe0a0; cp <= 0xe0a2; ++cp) glyph(cp);
    printf("\033[13;1Hextent: ready\r\n");
    unsigned char bytes[32];
    size_t n = 0;
    int done = 0;
    /* A sentinel proves input arrived even when Ctrl-Space is dropped. */
    while (n < sizeof(bytes)) {
        struct pollfd p = {.fd = 0, .events = POLLIN};
        int r;
        do { r = poll(&p, 1, 30000); } while (r < 0 && errno == EINTR);
        if (r <= 0 || read(0, &bytes[n], 1) != 1) break;
        if (bytes[n++] == 'z') { done = 1; break; }
    }
    printf("extent: keys");
    for (size_t i = 0; i < n; ++i) printf(" %02x", bytes[i]);
    printf("\r\nextent: %s\r\n", done ? "done" : "timeout");
    if (tcsetattr(0, TCSANOW, &old)) return 2;
    return done ? 0 : 1;
}
