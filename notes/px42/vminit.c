/* vminit.c — px42: pid 1 of a real Linux booted under QEMU (as
 * notes/px39/vminit.c): root of the initial user namespace with every
 * capability, the "vm" root. It mounts /proc, /dev and a tmpfs /t
 * (mode 0777), runs each session named on the kernel command line
 * after `px42=` (comma-separated) between marker lines, and powers
 * off.
 *
 *   own        /own /t/ownw                     root
 *   own-user   /as 1000 1000 /own /t/ownu       dropped to 1000:1000 first
 *   perm       /perm /t/perm                    root (px38's probe)
 *   soak       /own soak 100000 /t/soak         root
 *   soak-user  /as 1000 1000 /own soak 100000 /t/soaku
 *   ls         /bin/ls -ln /home /home/pax /home/pax/notes   the image's own archive is the root
 *   ls-names   /bin/ls -l  /home /home/pax /home/pax/notes
 *
 * For `ls` and `ls-names` the initramfs is PAX's image archive itself
 * (tests/mpx5-users builds it) with this program in a second archive
 * after it: Linux unpacks both, so the tree `ls` reads is what Linux
 * made of the same bytes PAX's kernel/tree adopts. /t is not mounted
 * for them and nothing under /home is touched. */
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
    char *w = strstr(cmd, "px42=");
    char list[256];
    snprintf(list, sizeof list, "%s", w ? w + 5 : "own,own-user,perm,soak,soak-user");
    list[strcspn(list, " \n")] = 0;
    int image = strncmp(list, "ls", 2) == 0;
    if (!image) {
        mkdir("/t", 0777);
        if (mount("t", "/t", "tmpfs", 0, "mode=0777") != 0) say("! mount /t: %d\n", -errno);
    }
    umask(022);
    struct utsname u;
    uname(&u);
    say("=== px42 vm: %s %s %s; pid %d uid %s gid %s groups '%s' CapEff ", u.sysname, u.release, u.machine, getpid(), uids(), gids(), groups());
    say("%s CapBnd ", status_line("/proc/self/status", "CapEff"));
    say("%s\n", status_line("/proc/self/status", "CapBnd"));
    {
        char b[256] = "?";
        int s = open("/proc/mounts", O_RDONLY);
        if (s >= 0) { long k = read(s, b, sizeof b - 1); if (k > 0) b[k] = 0; close(s); }
        b[strcspn(b, "\n")] = 0;
        say("=== px42 vm: the root is '%s'\n", b);
    }
    for (char *t = strtok(list, ","); t; t = strtok(NULL, ",")) {
        if (!strcmp(t, "own")) run(t, (char *[]){ "/own", "/t/ownw", NULL });
        else if (!strcmp(t, "own-user")) run(t, (char *[]){ "/as", "1000", "1000", "/own", "/t/ownu", NULL });
        else if (!strcmp(t, "perm")) { mkdir("/t/perm", 0777); chmod("/t/perm", 0777); run(t, (char *[]){ "/perm", "/t/perm", NULL }); }
        else if (!strcmp(t, "soak")) run(t, (char *[]){ "/own", "soak", "100000", "/t/soak", NULL });
        else if (!strcmp(t, "soak-user")) run(t, (char *[]){ "/as", "1000", "1000", "/own", "soak", "100000", "/t/soaku", NULL });
        else if (!strcmp(t, "ls")) run(t, (char *[]){ "/bin/ls", "-ln", "/home", "/home/pax", "/home/pax/notes", NULL });
        else if (!strcmp(t, "ls-names")) run(t, (char *[]){ "/bin/ls", "-l", "/home", "/home/pax", "/home/pax/notes", NULL });
        else say("! no session %s\n", t);
    }
    say("=== px42 vm: done\n");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
