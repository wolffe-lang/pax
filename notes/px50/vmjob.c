/* px50: the real-root Linux side of the fdtab probe: px49's vmjob.c
 * (notes/px49/vmjob.c) unchanged but for one thing before the session:
 * `/` is made root's 0755 (chmod), as PAX's root is (ruling #85; the
 * initramfs's root is 1777 on Linux), so a user's rmdir and rename of
 * /proc and /sys (pax#80) meet the same `/` on both. The answer is
 * printed as a `=== px46 vm:` line (the meta keeps it).
 *
 * px49's comment follows.
 */
/* px49: the real-root Linux side of the gaps probe: px48's vmjob.c
 * (notes/px48/vmjob.c) unchanged but for two things before the session:
 * the loopback interface is brought up (SIOCGIFFLAGS, SIOCSIFFLAGS with
 * IFF_UP: linux/sockios.h's and net/if.h's numbers), so the probe's TCP
 * rows have a peer at 127.0.0.1 as PAX's loopback does and the
 * container's has; and sysfs is mounted at /sys, as PAX has a /sys. Each
 * answer is printed as a `=== px46 vm:` line (the meta keeps it).
 *
 * px48's comment follows.
 */
/* px48: the real-root Linux side of the job-control probe and the shell
 * session: px46's vmtty.c (notes/px46/vmtty.c) with the program and its
 * arguments read from /px46/argv (one per line) rather than /bin/pelt,
 * and `^Z` typed too. pid 1 of a real Linux booted under QEMU (kasumi's
 * own kernel image, run as a guest and never read), root of the initial
 * user namespace with every capability, in session 0 with no terminal.
 * The program runs on the slave of a fresh pseudo-terminal: a session
 * leader with it as its controlling terminal (setsid, TIOCSCTTY), IXON
 * cleared, PAX's environment HOME=/ TERM=linux PAX=1 PATH=/bin, in /;
 * the keys of /px46/keys typed with tools/qemu-halt's rules (before step
 * k wait until the prompt has been shown k times; `^C ^D ^U ^W ^\ ^Z ^?
 * ^^` control characters; Enter unless the step ends `^D` or `^.`; a
 * step starting `^~` typed 1.5 s after the one before; 20 ms a byte),
 * and every byte the terminal showed kept. At the end it writes them to
 * the console as hex lines between markers, then the program's status,
 * and powers off. Before the session it writes 1 to the four
 * fs.protected_* settings (ruling #75 R7). The program's orphans are
 * reparented to this pid 1, in session 0: another session than the
 * program's, as PAX's pid 1 is another session than the probe's R.
 *   kernel command line: rdinit=/px46/vmjob */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <net/if.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static char buf[1 << 20];
static size_t len;
static int master = -1, alive = 1;

static long now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void pump(long ms) {
    long end = now_ms() + ms;
    while (alive && now_ms() < end) {
        struct pollfd p = { master, POLLIN, 0 };
        if (poll(&p, 1, 20) > 0) {
            ssize_t n = read(master, buf + len, sizeof buf - len);
            if (n <= 0) { alive = 0; return; }
            len += (size_t)n;
        }
    }
}

static int count(const char *pr) {
    int c = 0;
    size_t k = strlen(pr);
    for (size_t i = 0; i + k <= len; i++)
        if (memcmp(buf + i, pr, k) == 0) c++;
    return c;
}

static void put(const char *path, const char *v) {
    int fd = open(path, O_WRONLY);
    if (fd >= 0) { if (write(fd, v, strlen(v)) < 0) {} close(fd); }
    else printf("=== px46 vm: cannot write %s: %s\n", path, strerror(errno));
}

static char *slurp(const char *path) {
    static char s[1 << 16];
    int fd = open(path, O_RDONLY);
    if (fd < 0) return NULL;
    ssize_t n = read(fd, s, sizeof s - 1);
    close(fd);
    s[n < 0 ? 0 : n] = 0;
    return s;
}

int main(void) {
    mkdir("/proc", 0555);
    mount("proc", "/proc", "proc", 0, NULL);
    mkdir("/dev", 0755);
    mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
    mkdir("/dev/pts", 0755);
    mount("devpts", "/dev/pts", "devpts", 0, "ptmxmode=0666,mode=0620");
    mkdir("/sys", 0555);
    int sy = mount("sysfs", "/sys", "sysfs", 0, NULL);
    int lo = -1;
    int sk = socket(AF_INET, SOCK_DGRAM, 0);
    if (sk >= 0) {
        struct ifreq r;
        memset(&r, 0, sizeof r);
        strcpy(r.ifr_name, "lo");
        if (ioctl(sk, SIOCGIFFLAGS, &r) == 0) {
            r.ifr_flags |= IFF_UP;
            lo = ioctl(sk, SIOCSIFFLAGS, &r);
        }
        close(sk);
    }
    printf("\n=== px46 vm: px49: loopback up %d, sysfs %d\n", lo, sy);
    printf("=== px46 vm: px50: chmod / 0755 %d\n", chmod("/", 0755));
    put("/proc/sys/fs/protected_symlinks", "1");
    put("/proc/sys/fs/protected_hardlinks", "1");
    put("/proc/sys/fs/protected_fifos", "1");
    put("/proc/sys/fs/protected_regular", "1");
    printf("=== px46 vm: start\n");
    fflush(stdout);
    char prompt[64] = "$ ";
    char *pf = slurp("/px46/prompt");
    if (pf && *pf) { strncpy(prompt, pf, sizeof prompt - 1); prompt[strcspn(prompt, "\n")] = 0; }
    char *keys = slurp("/px46/keys");
    if (!keys) { printf("=== px46 vm: no /px46/keys\n"); reboot(RB_POWER_OFF); }
    keys = strdup(keys);
    char *as = slurp("/px46/argv");
    if (!as) { printf("=== px46 vm: no /px46/argv\n"); reboot(RB_POWER_OFF); }
    as = strdup(as);
    static char *av[64];
    int ac = 0;
    for (char *w = strtok(as, "\n"); w && ac < 63; w = strtok(NULL, "\n")) av[ac++] = w;
    av[ac] = NULL;
    if (!ac) { printf("=== px46 vm: an empty /px46/argv\n"); reboot(RB_POWER_OFF); }

    master = posix_openpt(O_RDWR | O_NOCTTY);
    if (master < 0 || grantpt(master) || unlockpt(master)) { printf("=== px46 vm: no pty: %s\n", strerror(errno)); reboot(RB_POWER_OFF); }
    char *name = ptsname(master);
    pid_t pid = fork();
    if (pid == 0) {
        setsid();
        int s = open(name, O_RDWR);
        ioctl(s, TIOCSCTTY, 0);
        struct termios t;
        tcgetattr(s, &t);
        t.c_iflag &= ~IXON;
        tcsetattr(s, TCSANOW, &t);
        dup2(s, 0); dup2(s, 1); dup2(s, 2);
        if (s > 2) close(s);
        close(master);
        if (chdir("/") != 0) _exit(126);
        char *envp[] = { "HOME=/", "TERM=linux", "PAX=1", "PATH=/bin", NULL };
        execve(av[0], av, envp);
        _exit(127);
    }
    int want = 0, ok = 1;
    for (char *line = strtok(keys, "\n"); line && ok; line = strtok(NULL, "\n")) {
        int late = strncmp(line, "^~", 2) == 0;
        if (late) { line += 2; pump(1500); }
        else {
            want++;
            long end = now_ms() + 300000;
            while (count(prompt) < want) {
                if (!alive || now_ms() > end) { printf("=== px46 vm: prompt %d did not come\n", want); ok = 0; break; }
                pump(50);
            }
            if (!ok) break;
            pump(200);
        }
        size_t L = strlen(line);
        int enter = !(L >= 2 && line[L - 2] == '^' && (line[L - 1] == 'D' || line[L - 1] == '.'));
        for (size_t i = 0; i < L; i++) {
            unsigned char c = (unsigned char)line[i];
            if (c == '^' && i + 1 < L && strchr("CDUWZ\\?^.", line[i + 1])) {
                char d = line[++i];
                int v = d == 'C' ? 3 : d == 'D' ? 4 : d == 'U' ? 21 : d == 'W' ? 23 : d == 'Z' ? 26 : d == '\\' ? 28 : d == '?' ? 127 : d == '^' ? 94 : -1;
                if (v < 0) continue;
                c = (unsigned char)v;
            }
            if (write(master, &c, 1) < 0) {}
            pump(20);
        }
        if (enter) { unsigned char cr = 13; if (write(master, &cr, 1) < 0) {} pump(20); }
    }
    int st = -1;
    long end = now_ms() + 300000;
    while (now_ms() < end) {
        pump(100);
        int w;
        if (waitpid(pid, &w, WNOHANG) == pid) { st = WIFEXITED(w) ? WEXITSTATUS(w) : 128 + WTERMSIG(w); pump(200); break; }
    }
    printf("=== px46 vm: begin %zu bytes\n", len);
    for (size_t i = 0; i < len; i += 64) {
        printf("H ");
        for (size_t j = i; j < len && j < i + 64; j++) printf("%02x", (unsigned char)buf[j]);
        printf("\n");
    }
    printf("=== px46 vm: status %d\n=== px46 vm: done\n", st);
    fflush(stdout);
    sync();
    reboot(RB_POWER_OFF);
    return 0;
}
