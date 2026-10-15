/* priv.c — px38: the things PAX already offers that Linux keeps for root
 * (beyond files, credentials and signals): each tried by a user and,
 * where trying is harmless, by root.
 *
 *   priv DIR         DIR on a tmpfs
 */
#include "px38.h"
#include <arpa/inet.h>
#include <linux/kd.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/sysmacros.h>
#include <sys/time.h>
#include <time.h>

static const char *D;

static long bind_port(int type, int port)
{
    int s = socket(AF_INET, type, 0);
    if (s < 0) return -(long)errno;
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    long r = bind(s, (struct sockaddr *)&a, sizeof a) == 0 ? 0L : -(long)errno;
    close(s);
    return r;
}

static void rows(const char *who, int root, int tty)
{
    char p[600];
    say("%s: bind TCP 127.0.0.1:80 %ld, :1023 %ld, :1024 %ld, :8000 %ld; bind UDP :53 %ld, :5353 %ld\n", who, bind_port(SOCK_STREAM, 80),
        bind_port(SOCK_STREAM, 1023), bind_port(SOCK_STREAM, 1024), bind_port(SOCK_STREAM, 8000), bind_port(SOCK_DGRAM, 53),
        bind_port(SOCK_DGRAM, 5353));
    {
        int s = socket(AF_INET, SOCK_RAW, 1);
        long r = s < 0 ? -(long)errno : 0;
        if (s >= 0) close(s);
        say("%s: socket(AF_INET, SOCK_RAW, ICMP) %ld\n", who, r);
    }
    {
        long up = rc(SYS_setpriority, PRIO_PROCESS, 0, 5, 0, 0);
        long down = rc(SYS_setpriority, PRIO_PROCESS, 0, -5, 0, 0);
        say("%s: setpriority to 5 %ld, then to -5 %ld\n", who, up, down);
        rc(SYS_setpriority, PRIO_PROCESS, 0, 0, 0, 0);
    }
    {
        struct rlimit64 { unsigned long cur, max; } l;
        long g = rc(SYS_prlimit64, 0, RLIMIT_NOFILE, 0, (long)&l, 0);
        struct rlimit64 lower = { l.cur, l.max > 16 ? l.max - 1 : l.max }, raise = { l.cur, l.max };
        long a = rc(SYS_prlimit64, 0, RLIMIT_NOFILE, (long)&lower, 0, 0);
        long b = rc(SYS_prlimit64, 0, RLIMIT_NOFILE, (long)&raise, 0, 0);
        say("%s: prlimit64(RLIMIT_NOFILE) read %ld; the hard limit lowered by one %ld, raised back %ld\n", who, g, a, b);
    }
    snprintf(p, sizeof p, "%s/node-%d", D, root);
    say("%s: mknod of a character device (1, 3) %ld", who, rc(SYS_mknod, (long)p, S_IFCHR | 0666, makedev(1, 3), 0, 0));
    unlink(p);
    say(", of a FIFO %ld", rc(SYS_mknod, (long)p, S_IFIFO | 0666, 0, 0, 0));
    unlink(p);
    say("; chroot(\"/\") %ld\n", rc(SYS_chroot, (long)"/", 0, 0, 0, 0));
    if (tty >= 0) {
        long a = rc(SYS_ioctl, tty, KIOCSOUND, 0, 0, 0);
        long b = rc(SYS_ioctl, tty, KDMKTONE, 0, 0, 0);
        say("%s: on a virtual terminal opened by root: ioctl(KIOCSOUND, 0) %ld, ioctl(KDMKTONE, 0) %ld\n", who, a, b);
    } else say("%s: no virtual terminal here (/dev/tty0 %d)\n", who, tty);
    if (!root) {
        /* refused for a user: tried only by one, since for root they would change the machine */
        struct timespec ts = { 1, 0 };
        struct timeval tv = { 1, 0 };
        long a = rc(SYS_clock_settime, CLOCK_REALTIME, (long)&ts, 0, 0, 0);
        long b = rc(SYS_settimeofday, (long)&tv, 0, 0, 0, 0);
        long c = rc(SYS_sethostname, (long)"px38", 4, 0, 0, 0);
        long d = rc(SYS_reboot, 0xfee1dead, 672274793, 0x4321fedc, 0, 0); /* LINUX_REBOOT_CMD_POWER_OFF */
        long e = rc(SYS_mount, (long)"none", (long)D, (long)"tmpfs", 0, 0);
        long f = rc(SYS_umount2, (long)D, 0, 0, 0, 0);
        say("%s: clock_settime %ld, settimeofday %ld, sethostname %ld, reboot %ld, mount %ld, umount2 %ld\n", who, a, b, c, d, e, f);
        say("%s: kill(1, SIGTERM) %ld\n", who, rc(SYS_kill, 1, SIGTERM, 0, 0, 0));
    }
    {
        static const char *dev[] = { "/dev/null", "/dev/zero", "/dev/full", "/dev/console", "/dev/tty", "/dev/tty0", "/dev/ttyS0", "/dev/mem", "/dev/kmsg",
                                     "/dev/random", "/dev/urandom", "/dev/ptmx" };
        say("%s: open for writing:", who);
        for (unsigned i = 0; i < sizeof dev / sizeof *dev; i++) {
            int fd = open(dev[i], O_WRONLY | O_NOCTTY | O_NONBLOCK);
            say(" %s %ld", dev[i], fd < 0 ? -(long)errno : 0L);
            if (fd >= 0) close(fd);
        }
        say("\n");
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) { say("usage: priv DIR\n"); return 2; }
    D = argv[1];
    mkdir(D, 0777);
    chmod(D, 0777);
    {
        char b[16] = "?";
        int s = open("/proc/sys/net/ipv4/ip_unprivileged_port_start", O_RDONLY);
        if (s >= 0) { long k = read(s, b, sizeof b - 1); if (k > 0) b[k - 1] = 0; close(s); }
        say("settings: net.ipv4.ip_unprivileged_port_start %s\n", b);
        static const char *dev[] = { "/dev/null", "/dev/zero", "/dev/full", "/dev/console", "/dev/tty", "/dev/tty0", "/dev/ttyS0", "/dev/mem", "/dev/kmsg",
                                     "/dev/random", "/dev/urandom", "/dev/ptmx" };
        for (unsigned i = 0; i < sizeof dev / sizeof *dev; i++) {
            struct stat st;
            if (stat(dev[i], &st) == 0) say("device: %s %u:%u %o\n", dev[i], st.st_uid, st.st_gid, st.st_mode);
            else say("device: %s %d\n", dev[i], -errno);
        }
    }
    int tty = open("/dev/tty0", O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (tty < 0) tty = -errno;
    pid_t p = fork();
    if (p == 0) { rc(SYS_setgroups, 0, 0, 0, 0, 0); rows("root", 1, tty); _exit(0); }
    reap(p);
    p = fork();
    if (p == 0) {
        unsigned none[1] = { 0 };
        become(1000, 2000, 0, none);
        rows("user", 0, tty);
        _exit(0);
    }
    reap(p);
    say("priv: done\n");
    return 0;
}
