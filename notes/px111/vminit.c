/* notes/px111/vminit.c — px111: the first program of a real Linux under
 * QEMU (the host's installed kernel image, booted as a guest and never
 * read), the reference tests/mpx5-pty's transcripts are held to. It
 * mounts /proc, a devtmpfs at /dev and a devpts at /dev/pts with no
 * options (the defaults: slaves 0600 and the opener's group,
 * /dev/pts/ptmx 0000; R-px111-1), makes /dev/console its descriptors 0,
 * 1 and 2, runs each line of /px111/run (words separated by single
 * spaces, the first the program's path) as a child with HOME=/
 * TERM=linux PAX=1 PATH=/bin, PAX's console's environment, and reports
 * each one's end; then powers the machine off. Every line it writes
 * starts `=== px111 vm: `. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static void line(const char *a, const char *b) {
    char buf[512];
    int n = snprintf(buf, sizeof buf, "=== px111 vm: %s%s\n", a, b);
    (void)!write(1, buf, (size_t)n);
}

int main(void) {
    mkdir("/proc", 0555);
    mount("proc", "/proc", "proc", 0, 0);
    mkdir("/dev", 0755);
    mount("devtmpfs", "/dev", "devtmpfs", 0, 0);
    mkdir("/dev/pts", 0755);
    int pr = mount("devpts", "/dev/pts", "devpts", 0, 0);
    int c = open("/dev/console", O_RDWR | O_NOCTTY);
    if (c >= 0) { dup2(c, 0); dup2(c, 1); dup2(c, 2); if (c > 2) close(c); }
    line("begin", pr == 0 ? " (devpts mounted)" : " (devpts NOT mounted)");
    FILE *f = fopen("/px111/run", "r");
    char cmd[512];
    while (f && fgets(cmd, sizeof cmd, f)) {
        size_t l = strlen(cmd);
        if (l && cmd[l - 1] == '\n') cmd[--l] = 0;
        if (!l || cmd[0] == '#') continue;
        char copy[512];
        snprintf(copy, sizeof copy, "%s", cmd);
        char *argv[32];
        int n = 0;
        for (char *w = strtok(copy, " "); w && n < 31; w = strtok(0, " ")) argv[n++] = w;
        argv[n] = 0;
        line("run ", cmd);
        pid_t p = fork();
        if (p == 0) {
            char *envp[] = {"HOME=/", "TERM=linux", "PAX=1", "PATH=/bin", 0};
            execve(argv[0], argv, envp);
            _exit(127);
        }
        int st = 0;
        while (waitpid(p, &st, 0) < 0 && errno == EINTR) {}
        char how[64];
        if (WIFEXITED(st)) snprintf(how, sizeof how, "exited %d", WEXITSTATUS(st));
        else snprintf(how, sizeof how, "killed by signal %d", WTERMSIG(st));
        line("status ", how);
    }
    line("done", "");
    sync();
    reboot(RB_POWER_OFF);
    return 0;
}
