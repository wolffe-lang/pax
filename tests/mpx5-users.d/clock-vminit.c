/* clock-vminit.c — pid 1 of a real Linux booted under QEMU for the clock
 * sessions of tests/mpx5-users (tests/mpx5-users.d/clock-vm.sh): root of
 * the initial user namespace with every capability, no account anywhere,
 * no time daemon, nothing else that sets the clock. The initramfs is PAX's
 * own archive for the clock sessions followed by a second archive holding
 * only this program as /init, so the probe runs on what Linux made of the
 * same bytes. It mounts /proc and /dev, sets CLOCK_REALTIME to the date
 * the command line gives after `clockvm_now=` (seconds since the epoch: the
 * host's, when it boots; the guest's kernel may read no battery clock of its
 * own, and PAX reads one, so both start at the date), runs each session named
 * after `clockvm=` (comma-separated) between marker lines, and powers off.
 *
 *   clock        /bin/clock /t/clock                          root
 *   clock-user   /bin/as 1000 1000 /bin/clock user /t/clock   dropped to 1000:1000 first
 *
 * One boot a session: root's session sets the clock. */
#include "px38.h"
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/utsname.h>
#include <time.h>

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
    mkdir("/proc", 0555);
    mkdir("/dev", 0755);
    mount("proc", "/proc", "proc", 0, NULL);
    mount("dev", "/dev", "devtmpfs", 0, NULL);
    int fd = open("/dev/console", O_RDWR);
    if (fd >= 0) { dup2(fd, 0); dup2(fd, 1); dup2(fd, 2); if (fd > 2) close(fd); }
    char cmd[2048] = "";
    fd = open("/proc/cmdline", O_RDONLY);
    if (fd >= 0) { long n = read(fd, cmd, sizeof cmd - 1); if (n > 0) cmd[n] = 0; close(fd); }
    char *now = strstr(cmd, "clockvm_now=");
    if (now) {
        struct timespec t = { atol(now + 12), 0 };
        long r = rc(SYS_clock_settime, CLOCK_REALTIME, (long)&t, 0, 0, 0);
        say("=== clock vm: the clock set to the date the command line gives: %ld\n", r);
    }
    char *w = strstr(cmd, "clockvm=");
    char list[256];
    snprintf(list, sizeof list, "%s", w ? w + 8 : "clock");
    list[strcspn(list, " \n")] = 0;
    umask(022);
    struct utsname u;
    uname(&u);
    say("=== clock vm: %s %s %s; pid %d uid %s gid %s groups '%s' CapEff ", u.sysname, u.release, u.machine, getpid(), uids(), gids(),
        groups());
    say("%s\n", status_line("/proc/self/status", "CapEff"));
    for (char *t = strtok(list, ","); t; t = strtok(NULL, ",")) {
        if (!strcmp(t, "clock")) run(t, (char *[]){ "/bin/clock", "/t/clock", NULL });
        else if (!strcmp(t, "clock-user")) run(t, (char *[]){ "/bin/as", "1000", "1000", "/bin/clock", "user", "/t/clock", NULL });
        else say("! no session %s\n", t);
    }
    say("=== clock vm: done\n");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
