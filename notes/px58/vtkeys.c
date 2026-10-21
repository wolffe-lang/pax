/* px58: the Linux side of the keyboard's keys and of a console's answers,
 * black-box: pid 1 of a real Linux booted under QEMU (kasumi's own kernel
 * image, run as a guest and never read; its VT, VGA console, i8042 and
 * atkbd built in, as /proc/config.gz says), with a VGA display and a PS/2
 * keyboard. It mounts devtmpfs, opens the first virtual terminal
 * (/dev/tty1), sets yew's raw mode there (ICANON ECHO ISIG IEXTEN IXON
 * off, VMIN 1 VTIME 0: notes/px58 §C's census), and on the serial console
 * (/dev/console, console=ttyS0):
 *   - the VT's window size (TIOCGWINSZ),
 *   - its answers to the queries yew and termwolf write (DA1 `CSI c`, the
 *     cursor's position `CSI 6n`, kitty's `CSI ? u`, DECRQM `CSI ? 2026 $
 *     p`), each read for half a second,
 *   - `ps2> `, then every byte the keyboard gives the VT up to a `.`
 *     (the host sends the keys through QEMU's monitor), as hex;
 * then powers off. Written from termios(3), ioctl_tty(2), console_codes(4)
 * (the queries' names), poll(2), mount(2), reboot(2). No kernel source. */
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static int out = 1;

static void say(const char *s) { (void)!write(out, s, strlen(s)); }

static void hex(const unsigned char *b, size_t n)
{
    char t[8];
    for (size_t i = 0; i < n; i++) {
        snprintf(t, sizeof t, i ? " %02x" : "%02x", b[i]);
        say(t);
    }
}

static long now_ms(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void query(int fd, const char *name, const char *q)
{
    unsigned char got[256];
    size_t n = 0;
    tcflush(fd, TCIFLUSH);
    (void)!write(fd, q, strlen(q));
    long end = now_ms() + 500;
    while (now_ms() < end && n < sizeof got) {
        struct pollfd p = { fd, POLLIN, 0 };
        if (poll(&p, 1, 50) > 0) {
            ssize_t r = read(fd, got + n, sizeof got - n);
            if (r > 0)
                n += (size_t)r;
        }
    }
    say("VT Q: ");
    say(name);
    say(": ");
    if (n == 0)
        say("no answer in half a second");
    else
        hex(got, n);
    say("\n");
}

int main(void)
{
    mkdir("/dev", 0755);
    mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
    int c = open("/dev/console", O_RDWR | O_NOCTTY);
    if (c >= 0)
        out = c;
    say("=== px58 vt: begin\n");
    int fd = open("/dev/tty1", O_RDWR | O_NOCTTY);
    if (fd < 0) {
        say("=== px58 vt: no /dev/tty1\n");
        reboot(RB_POWER_OFF);
        return 1;
    }
    struct termios t;
    tcgetattr(fd, &t);
    char line[256];
    snprintf(line, sizeof line, "VT S: iflag 0x%x oflag 0x%x cflag 0x%x lflag 0x%x\n",
             t.c_iflag, t.c_oflag, t.c_cflag, t.c_lflag);
    say(line);
    t.c_lflag &= ~(ICANON | ECHO | ISIG | IEXTEN);
    t.c_iflag &= ~IXON;
    t.c_cc[VMIN] = 1;
    t.c_cc[VTIME] = 0;
    tcsetattr(fd, TCSADRAIN, &t);
    struct winsize w = { 0 };
    int r = ioctl(fd, TIOCGWINSZ, &w);
    snprintf(line, sizeof line, "VT W: TIOCGWINSZ %d, %d rows %d columns\n", r, w.ws_row, w.ws_col);
    say(line);
    query(fd, "DA1 (CSI c)", "\033[c");
    query(fd, "the cursor's position (CSI 6n)", "\033[6n");
    query(fd, "kitty's keyboard (CSI ? u)", "\033[?u");
    query(fd, "DECRQM 2026 (CSI ? 2026 $ p)", "\033[?2026$p");
    tcflush(fd, TCIFLUSH);
    say("ps2> ");
    unsigned char got[512];
    size_t n = 0;
    long end = now_ms() + 120000;
    while (now_ms() < end && n < sizeof got) {
        struct pollfd p = { fd, POLLIN, 0 };
        if (poll(&p, 1, 200) <= 0)
            continue;
        ssize_t k = read(fd, got + n, sizeof got - n);
        if (k <= 0)
            break;
        n += (size_t)k;
        if (got[n - 1] == '.')
            break;
    }
    say("\nVT P: typed: ");
    hex(got, n);
    say("\n=== px58 vt: done\n");
    sync();
    reboot(RB_POWER_OFF);
    return 0;
}
