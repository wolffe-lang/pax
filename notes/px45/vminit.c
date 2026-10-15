/* vminit.c — px45: pid 1 of a real Linux booted under QEMU (as
 * notes/px44/vminit.c, whose copy this is): root of the initial user
 * namespace with every capability, the "vm" root — and, before any
 * session runs, the four protected settings (proc_sys_fs(5):
 * fs.protected_hardlinks, _symlinks, _regular, _fifos) written to 1, as
 * ruling #75 R7 fixes them on PAX and as px38's vm-protected run set them:
 * the "vm-protected" root. The initramfs is PAX's own image archive
 * for the `rights` sessions (tests/mpx5-users builds it), followed by a
 * second archive holding only this program as /init, so the tree the
 * probe walks is what Linux made of the same bytes PAX's kernel/tree
 * adopts. It mounts /proc and /dev (devtmpfs, no udev: the kernel's own
 * modes and owners), runs each session named on the kernel command line
 * after `px45=` (comma-separated) between marker lines, and powers off.
 *
 *   rights            /bin/rights                         root
 *   rights-user       /bin/as 1000 1000 /bin/rights user  dropped to 1000:1000 first
 *   rights-soak       /bin/rights soak 100000             root
 *   rights-soak-user  /bin/rights soak 100000 1000        root starts its target, then is 1000:1000 for good
 *   sig               /bin/sig /t/sig                     px38's probe (its reference is px38's recording)
 *   priv              /bin/priv /t/priv                   px38's probe
 *
 * One boot a session, as px44's recorder does. */
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
    char *w = strstr(cmd, "px45=");
    char list[256];
    snprintf(list, sizeof list, "%s", w ? w + 5 : "rights");
    list[strcspn(list, " \n")] = 0;
    {
        static const char *N[] = { "protected_hardlinks", "protected_symlinks", "protected_regular", "protected_fifos" };
        for (int i = 0; i < 4; i++) {
            char p[96];
            snprintf(p, sizeof p, "/proc/sys/fs/%s", N[i]);
            int s = open(p, O_WRONLY);
            if (s < 0 || write(s, "1\n", 2) != 2) say("=== px45 vm: ! %s: %d\n", p, -errno);
            if (s >= 0) close(s);
        }
    }
    umask(022);
    struct utsname u;
    uname(&u);
    say("=== px45 vm: %s %s %s; pid %d uid %s gid %s groups '%s' CapEff ", u.sysname, u.release, u.machine, getpid(), uids(), gids(), groups());
    say("%s CapBnd ", status_line("/proc/self/status", "CapEff"));
    say("%s\n", status_line("/proc/self/status", "CapBnd"));
    {
        char b[256] = "?";
        int s = open("/proc/mounts", O_RDONLY);
        if (s >= 0) { long k = read(s, b, sizeof b - 1); if (k > 0) b[k] = 0; close(s); }
        b[strcspn(b, "\n")] = 0;
        say("=== px45 vm: the root is '%s'\n", b);
        say("=== px45 vm: settings");
        static const char *N[] = { "protected_hardlinks", "protected_symlinks", "protected_regular", "protected_fifos" };
        for (int i = 0; i < 4; i++) {
            char p[96], v[16] = "?";
            snprintf(p, sizeof p, "/proc/sys/fs/%s", N[i]);
            int s = open(p, O_RDONLY);
            if (s >= 0) { long k = read(s, v, sizeof v - 1); if (k > 0) v[k - 1] = 0; close(s); }
            say(" %s %s", N[i], v);
        }
        say("\n");
    }
    for (char *t = strtok(list, ","); t; t = strtok(NULL, ",")) {
        if (!strcmp(t, "rights")) run(t, (char *[]){ "/bin/rights", NULL });
        else if (!strcmp(t, "rights-user")) run(t, (char *[]){ "/bin/as", "1000", "1000", "/bin/rights", "user", NULL });
        else if (!strcmp(t, "rights-soak")) run(t, (char *[]){ "/bin/rights", "soak", "100000", NULL });
        else if (!strcmp(t, "rights-soak-user")) run(t, (char *[]){ "/bin/rights", "soak", "100000", "1000", NULL });
        else if (!strcmp(t, "sig")) run(t, (char *[]){ "/bin/sig", "/t/sig", NULL });
        else if (!strcmp(t, "priv")) run(t, (char *[]){ "/bin/priv", "/t/priv", NULL });
        else say("! no session %s\n", t);
    }
    say("=== px45 vm: done\n");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
