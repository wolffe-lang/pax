/* vminit.c — px38: pid 1 of a real Linux booted under QEMU with the
 * probes in its initramfs. It is root of the initial user namespace with
 * every capability: the "vm" root of notes/px38-the-users.md. It mounts
 * /proc, /dev and two tmpfs (/t; /tn with nosuid), runs each probe named
 * on the kernel command line after `px38=` (comma-separated; default
 * all), each between marker lines on the console, and powers off. */
#include "px38.h"
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/utsname.h>

static void run(const char *path, const char *a1, const char *a2)
{
    say("=== BEGIN %s\n", path + 1);
    pid_t p = fork();
    if (p == 0) {
        char *av[] = { (char *)path, (char *)a1, (char *)a2, NULL };
        char *ev[] = { (char *)"HOME=/", NULL };
        execve(path, av, ev);
        say("! execve %s: %d\n", path, -errno);
        _exit(127);
    }
    int st = reap(p);
    say("=== END %s status %d\n", path + 1, st);
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
    struct utsname u;
    uname(&u);
    say("=== px38 vm: %s %s %s; pid %d uid %s gid %s groups '%s' CapEff ", u.sysname, u.release, u.machine, getpid(), uids(), gids(), groups());
    say("%s CapBnd ", status_line("/proc/self/status", "CapEff"));
    say("%s\n", status_line("/proc/self/status", "CapBnd"));
    char cmd[2048] = "";
    fd = open("/proc/cmdline", O_RDONLY);
    if (fd >= 0) { long n = read(fd, cmd, sizeof cmd - 1); if (n > 0) cmd[n] = 0; close(fd); }
    if (strstr(cmd, "px38prot=1")) {
        /* the four settings a distribution turns on (proc_sys_fs(5)); the kernel's own default is 0 */
        const char *f[] = { "/proc/sys/fs/protected_hardlinks", "/proc/sys/fs/protected_symlinks", "/proc/sys/fs/protected_regular",
                            "/proc/sys/fs/protected_fifos" };
        for (int i = 0; i < 4; i++) {
            int s = open(f[i], O_WRONLY);
            if (s < 0 || write(s, "1\n", 2) != 2) say("! cannot set %s: %d\n", f[i], -errno);
            if (s >= 0) close(s);
        }
    }
    {
        char b[16] = "?";
        int s = open("/proc/sys/fs/suid_dumpable", O_RDONLY);
        if (s >= 0) { long k = read(s, b, sizeof b - 1); if (k > 0) b[k - 1] = 0; close(s); }
        say("=== px38 vm: fs.suid_dumpable %s\n", b);
    }
    char *w = strstr(cmd, "px38=");
    const char *want = w ? w + 5 : "ids,cred,perm,setid,sig";
    char list[256];
    snprintf(list, sizeof list, "%s", want);
    list[strcspn(list, " \n")] = 0;
    for (char *t = strtok(list, ","); t; t = strtok(NULL, ",")) {
        if (!strcmp(t, "ids")) run("/ids", "/t/idsw", NULL);
        else if (!strcmp(t, "cred")) run("/cred", NULL, NULL);
        else if (!strcmp(t, "perm")) { mkdir("/t/perm", 0777); run("/perm", "/t/perm", NULL); }
        else if (!strcmp(t, "setid")) { mkdir("/t/setid", 0777); mkdir("/tn/setid", 0777); run("/setid", "/t/setid", "/tn/setid"); }
        else if (!strcmp(t, "sig")) { mkdir("/t/sig", 0777); run("/sig", "/t/sig", NULL); }
    }
    say("=== px38 vm: done\n");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
