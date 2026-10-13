/* vminit.c — px39: pid 1 of a real Linux booted under QEMU with the
 * credentials programs in its initramfs (as notes/px38/probes/vminit.c):
 * root of the initial user namespace with every capability, the "vm"
 * root. It mounts /proc, /dev, a tmpfs /t and a tmpfs /tn with nosuid,
 * puts a set-ID copy of /ident on /tn (where Linux does not honour the
 * bits, as PAX honours them nowhere: ruling R5), runs each session named
 * on the kernel command line after `px39=` (comma-separated) between
 * marker lines, and powers off.
 *
 *   cred        /cred                         root
 *   cred-user   /as 1000 1000 /cred           dropped to 1000:1000 first
 *   ident       /ident /tn/ident-setid        root
 *   ident-user  /as 1000 1000 /ident /tn/ident-setid
 *   ids         /ids /t/idsw                  root (px38's)
 *   soak        /ident soak 100000            root
 *   soak-user   /as 1000 1000 /ident soak 100000
 */
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
    mkdir("/proc", 0555); mkdir("/dev", 0755); mkdir("/t", 0777); mkdir("/tn", 0777); mkdir("/etc", 0755);
    mount("proc", "/proc", "proc", 0, NULL);
    mount("dev", "/dev", "devtmpfs", 0, NULL);
    int fd = open("/dev/console", O_RDWR);
    if (fd >= 0) { dup2(fd, 0); dup2(fd, 1); dup2(fd, 2); if (fd > 2) close(fd); }
    if (mount("t", "/t", "tmpfs", 0, "mode=0777") != 0) say("! mount /t: %d\n", -errno);
    if (mount("tn", "/tn", "tmpfs", MS_NOSUID, "mode=0777") != 0) say("! mount /tn: %d\n", -errno);
    umask(022);
    long c = copy_file("/ident", "/tn/ident-setid", 06755);
    if (c != 0) say("! the set-ID copy: %ld\n", c);
    struct utsname u;
    uname(&u);
    say("=== px39 vm: %s %s %s; pid %d uid %s gid %s groups '%s' CapEff ", u.sysname, u.release, u.machine, getpid(), uids(), gids(), groups());
    say("%s CapBnd ", status_line("/proc/self/status", "CapEff"));
    say("%s\n", status_line("/proc/self/status", "CapBnd"));
    {
        char b[16] = "?";
        int s = open("/proc/sys/fs/suid_dumpable", O_RDONLY);
        if (s >= 0) { long k = read(s, b, sizeof b - 1); if (k > 0) b[k - 1] = 0; close(s); }
        say("=== px39 vm: fs.suid_dumpable %s; /tn/ident-setid mode %o owned %s\n", b, mode_of("/tn/ident-setid"), own_of("/tn/ident-setid"));
    }
    char cmd[2048] = "";
    fd = open("/proc/cmdline", O_RDONLY);
    if (fd >= 0) { long n = read(fd, cmd, sizeof cmd - 1); if (n > 0) cmd[n] = 0; close(fd); }
    char *w = strstr(cmd, "px39=");
    char list[256];
    snprintf(list, sizeof list, "%s", w ? w + 5 : "cred,cred-user,ident,ident-user,ids,soak,soak-user");
    list[strcspn(list, " \n")] = 0;
    for (char *t = strtok(list, ","); t; t = strtok(NULL, ",")) {
        if (!strcmp(t, "cred")) run(t, (char *[]){ "/cred", NULL });
        else if (!strcmp(t, "cred-user")) run(t, (char *[]){ "/as", "1000", "1000", "/cred", NULL });
        else if (!strcmp(t, "ident")) run(t, (char *[]){ "/ident", "/tn/ident-setid", NULL });
        else if (!strcmp(t, "ident-user")) run(t, (char *[]){ "/as", "1000", "1000", "/ident", "/tn/ident-setid", NULL });
        else if (!strcmp(t, "ids")) run(t, (char *[]){ "/ids", "/t/idsw", NULL });
        else if (!strcmp(t, "soak")) run(t, (char *[]){ "/ident", "soak", "100000", NULL });
        else if (!strcmp(t, "soak-user")) run(t, (char *[]){ "/as", "1000", "1000", "/ident", "soak", "100000", NULL });
        else say("! no session %s\n", t);
    }
    say("=== px39 vm: done\n");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
