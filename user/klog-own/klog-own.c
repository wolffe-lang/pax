#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

static int put(const char *s) {
    size_t n = strlen(s);
    while (n) {
        ssize_t w = write(STDOUT_FILENO, s, n);
        if (w < 0 && errno == EINTR) continue;
        if (w <= 0) return -1;
        s += w; n -= (size_t)w;
    }
    return 0;
}
static int one(int fd, char *c) {
    ssize_t n;
    do { n = read(fd, c, 1); } while (n < 0 && errno == EINTR);
    return n == 1 ? 0 : -1;
}
static int setting(const char *path, const char *tag) {
    char b[1024]; int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t n = read(fd, b, sizeof b - 1); close(fd);
    if (n < 0 || n == (ssize_t)sizeof b - 1) return -1;
    while (n && (b[n-1] == '\r' || b[n-1] == '\n')) --n;
    b[n] = 0;
    return put(tag) || put(b) || put("\r\n");
}
int main(void) {
    struct termios saved, raw; struct winsize ws; int p[2]; char b[256], c;
    if (tcgetattr(0, &saved) || ioctl(0, TIOCGWINSZ, &ws)) return 2;
    raw = saved; cfmakeraw(&raw);
    if (tcsetattr(0, TCSANOW, &raw)) return 2;
    if (pipe(p)) { tcsetattr(0, TCSANOW, &saved); return 2; }
    pid_t child = fork();
    if (child < 0) { close(p[0]); close(p[1]); tcsetattr(0, TCSANOW, &saved); return 2; }
    if (!child) {
        close(p[1]);
        int ok = one(p[0], &c) == 0 && c == 'x';
        close(p[0]);
        _exit(ok ? 0 : 2); /* No terminal write from this child. */
    }
    close(p[0]);
    int rc = 0;
    if (put("\r\n") || setting("/proc/cmdline", "KLOG-CMDLINE ") ||
        setting("/proc/sys/kernel/printk", "KLOG-PRINTK ")) rc = 2;
    snprintf(b, sizeof b, "KLOG-META parent=%ld child=%ld rows=%u cols=%u\r\n",
             (long)getpid(), (long)child, (unsigned)ws.ws_row, (unsigned)ws.ws_col);
    if (put(b)) rc = 2;
    if (!rc && put("\033[?1049h\033[?25l\033[0;37;40m\033[2J\033[2;7HKLOG_OWNER_MARKER\033[2;7H")) rc = 2;
    if (!rc && (one(0, &c) || c != 'x' || write(p[1], "x", 1) != 1)) rc = 2;
    close(p[1]);
    /* The harness sees the real child kernel line before sending q. */
    if (!rc && (one(0, &c) || c != 'q')) rc = 2;
    int status = 0; pid_t done;
    do { done = waitpid(child, &status, 0); } while (done < 0 && errno == EINTR);
    int code = done == child && WIFEXITED(status) ? WEXITSTATUS(status) : 255;
    if (code) rc = 2;
    if (put("\033[?1049l\033[?25h")) rc = 2;
    if (tcsetattr(0, TCSANOW, &saved)) rc = 2;
    snprintf(b, sizeof b, "\nKLOG-DONE child=%ld status=%d\n", (long)child, code);
    if (put(b)) rc = 2;
    return rc;
}
