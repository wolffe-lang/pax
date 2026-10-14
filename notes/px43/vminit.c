/* vminit.c — px43: pid 1 of a real Linux booted under QEMU (as
 * notes/px42/vminit.c): root of the initial user namespace with every
 * capability, the "vm" root. The initramfs is PAX's own image archive
 * for the `chk` sessions (tests/mpx5-users builds it: /k carries the
 * cases, with owners and modes), followed by a second archive holding
 * only this program as /init, so the tree the probe walks is what Linux
 * made of the same bytes PAX's kernel/tree adopts. It mounts /proc and
 * /dev, runs each session named on the kernel command line after `px43=`
 * (comma-separated) between marker lines, and powers off.
 *
 *   chk            /bin/chk                                root
 *   chk-user       /bin/as 1000 1000 /bin/chk user         dropped to 1000:1000 first
 *   chk-soak       /bin/chk soak 100000                    root
 *   chk-soak-user  /bin/as 1000 1000 /bin/chk soak 100000
 *
 * Each session gets a fresh boot (the probe changes the image's files:
 * a truncation, a mode made 0000), so the recorder boots once a session. */
#include "px38.h"
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/utsname.h>

static void run(const char *name, char *const av[])
{
    say("=== BEGIN %s\n", name);
    pid_t p = fork();
    if (p == 0) {
        char *ev[] = { NULL };
        execve(av[0], av, ev);
        say("! execve %s: %d\n", av[0], -errno);
        _exit(127);
    }
    int st = reap(p);
    say("=== END %s status %d\n", name, st);
}

int main(void)
{
    mkdir("/proc", 0555); mkdir("/dev", 0755);
    mount("proc", "/proc", "proc", 0, NULL);
    mount("dev", "/dev", "devtmpfs", 0, NULL);
    int fd = open("/dev/console", O_RDWR);
    if (fd >= 0) { dup2(fd, 0); dup2(fd, 1); dup2(fd, 2); if (fd > 2) close(fd); }
    char cmd[2048] = "";
    fd = open("/proc/cmdline", O_RDONLY);
    if (fd >= 0) { long n = read(fd, cmd, sizeof cmd - 1); if (n > 0) cmd[n] = 0; close(fd); }
    char *w = strstr(cmd, "px43=");
    char list[256];
    snprintf(list, sizeof list, "%s", w ? w + 5 : "chk");
    list[strcspn(list, " \n")] = 0;
    umask(022);
    struct utsname u;
    uname(&u);
    say("=== px43 vm: %s %s %s; pid %d uid %s gid %s groups '%s' CapEff ", u.sysname, u.release, u.machine, getpid(), uids(), gids(), groups());
    say("%s CapBnd ", status_line("/proc/self/status", "CapEff"));
    say("%s\n", status_line("/proc/self/status", "CapBnd"));
    {
        char b[256] = "?";
        int s = open("/proc/mounts", O_RDONLY);
        if (s >= 0) { long k = read(s, b, sizeof b - 1); if (k > 0) b[k] = 0; close(s); }
        b[strcspn(b, "\n")] = 0;
        say("=== px43 vm: the root is '%s'\n", b);
    }
    for (char *t = strtok(list, ","); t; t = strtok(NULL, ",")) {
        if (!strcmp(t, "chk")) run(t, (char *[]){ "/bin/chk", NULL });
        else if (!strcmp(t, "chk-user")) run(t, (char *[]){ "/bin/as", "1000", "1000", "/bin/chk", "user", NULL });
        else if (!strcmp(t, "chk-soak")) run(t, (char *[]){ "/bin/chk", "soak", "100000", NULL });
        else if (!strcmp(t, "chk-soak-user")) run(t, (char *[]){ "/bin/as", "1000", "1000", "/bin/chk", "soak", "100000", NULL });
        else say("! no session %s\n", t);
    }
    say("=== px43 vm: done\n");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
