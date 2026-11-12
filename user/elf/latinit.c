/* px131: latinit -- the init of tests/mpx6-latency's Linux guest, the
 * comparison column: a Linux kernel booted under QEMU with an initramfs of
 * this program, latprobe and latbig, and the modules its network needs.
 *
 * It mounts proc at /proc, a tmpfs at /tmp and devtmpfs at /dev; loads each
 * module named in /lib/modules/order (one name a line, /lib/modules/NAME.ko,
 * finit_module(2)); brings lo up and eth0 up at 10.0.2.15/24 (QEMU's user
 * network; SIOCSIFADDR, SIOCSIFNETMASK, SIOCSIFFLAGS); runs /bin/latprobe
 * with the words of /etc/latprobe-args, its output on the console; prints
 * `latinit: end status N`; and powers the machine off (reboot(2)). Black
 * box: the kernel is run, never read. Written from the man pages of the
 * calls named and netdevice(7).
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <arpa/inet.h>
#include <fcntl.h>
#include <net/if.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void say(const char *s) { fputs(s, stdout); fflush(stdout); }

static int addr(int fd, const char *ifn, unsigned long req, const char *a) {
    struct ifreq r;
    memset(&r, 0, sizeof r);
    snprintf(r.ifr_name, sizeof r.ifr_name, "%s", ifn);
    struct sockaddr_in *s = (struct sockaddr_in *)&r.ifr_addr;
    s->sin_family = AF_INET;
    inet_pton(AF_INET, a, &s->sin_addr);
    return ioctl(fd, req, &r);
}

static int up(int fd, const char *ifn) {
    struct ifreq r;
    memset(&r, 0, sizeof r);
    snprintf(r.ifr_name, sizeof r.ifr_name, "%s", ifn);
    if (ioctl(fd, SIOCGIFFLAGS, &r)) return -1;
    r.ifr_flags |= IFF_UP | IFF_RUNNING;
    return ioctl(fd, SIOCSIFFLAGS, &r);
}

int main(void) {
    mount("proc", "/proc", "proc", 0, NULL);
    mount("tmpfs", "/tmp", "tmpfs", 0, "mode=1777");
    mount("dev", "/dev", "devtmpfs", 0, NULL);
    FILE *o = fopen("/lib/modules/order", "r");
    char name[128], path[256];
    while (o && fgets(name, sizeof name, o)) {
        name[strcspn(name, "\n")] = 0;
        if (!*name) continue;
        snprintf(path, sizeof path, "/lib/modules/%s.ko", name);
        int m = open(path, O_RDONLY);
        if (m < 0 || syscall(SYS_finit_module, m, "", 0)) printf("latinit: module %s not loaded\n", name);
        if (m >= 0) close(m);
    }
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    up(s, "lo");
    int tries = 0;
    struct timespec t = {0, 100000000};
    while (addr(s, "eth0", SIOCSIFADDR, "10.0.2.15") && tries++ < 50) nanosleep(&t, NULL);
    addr(s, "eth0", SIOCSIFNETMASK, "255.255.255.0");
    printf("latinit: eth0 %s\n", up(s, "eth0") ? "not up" : "up at 10.0.2.15/24");
    fflush(stdout);
    char line[4096] = "";
    FILE *a = fopen("/etc/latprobe-args", "r");
    if (!a || !fgets(line, sizeof line, a)) say("latinit: no /etc/latprobe-args\n");
    char *argv[256];
    int n = 0;
    argv[n++] = "/bin/latprobe";
    for (char *w = strtok(line, " \n"); w && n < 255; w = strtok(NULL, " \n")) argv[n++] = w;
    argv[n] = NULL;
    pid_t p = fork();
    if (p == 0) {
        char *env[] = {"HOME=/", "TERM=linux", "PATH=/bin", NULL};
        chdir("/");
        execve(argv[0], argv, env);
        _exit(127);
    }
    int st = 0;
    while (waitpid(p, &st, 0) < 0) {}
    printf("latinit: end status %d\n", WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st));
    fflush(stdout);
    sync();
    reboot(RB_POWER_OFF);
    return 0;
}
