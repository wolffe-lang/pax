/* inject-wrap — stand in for one boreutils binary under tools/difftest and
 * run the real one under strace with one system call answered ENOSYS.
 * The wrapper is copied to <dir>/<util>; it execs
 *   strace -f -qq -o /dev/null -e trace=NAME [-e inject=NAME:error=ENOSYS]
 *          --argv0=<its own argv[0]> <REAL>/<util> args...
 * so the program sees exactly the argv[0] difftest gave (its stderr is
 * normalized on it). The file `.census-inject` beside the wrapper holds two
 * lines: the call's NAME, or several joined by commas (strace's syscall-set
 * syntax), or "none" (traces nothing, injects nothing: the baseline); and
 * the directory of the real binaries. A file, not the
 * environment: difftest builds every child's environment from scratch.
 * A call answered ENOSYS can leave a program spinning (tee with no write),
 * and strace blocks SIGALRM, so the wrapper stays as strace's parent: after
 * 60 s it SIGKILLs strace, --kill-on-exit takes the tracee with it, and
 * difftest's pipes close, so the case is decided (a FAIL) instead of
 * hanging. Otherwise the wrapper exits as strace did: the same status, or
 * the same signal re-raised (strace re-raises its tracee's). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>
#include <signal.h>
#include <sys/wait.h>

static pid_t child;
static void on_alarm(int sig) { (void)sig; kill(child, SIGKILL); }

int main(int argc, char **argv) {
    char self[PATH_MAX], real[PATH_MAX], conf[PATH_MAX + 32], a0[PATH_MAX + 16];
    char name[1024], dir[4096], tr[1100], inj[1140];
    ssize_t n = readlink("/proc/self/exe", self, sizeof self - 1);
    if (n < 0) { fprintf(stderr, "inject-wrap: no /proc/self/exe\n"); return 125; }
    self[n] = 0;
    char *slash = strrchr(self, '/');
    const char *base = slash + 1;
    *slash = 0;
    snprintf(conf, sizeof conf, "%s/.census-inject", self);
    FILE *f = fopen(conf, "r");
    if (!f || fscanf(f, "%1023s %4095s", name, dir) != 2) {
        fprintf(stderr, "inject-wrap: cannot read %s\n", conf);
        return 125;
    }
    fclose(f);
    snprintf(real, sizeof real, "%s/%s", dir, base);
    snprintf(a0, sizeof a0, "--argv0=%s", argv[0]);
    char **v = calloc(argc + 16, sizeof *v);
    int k = 0;
    v[k++] = "strace"; v[k++] = "-f"; v[k++] = "-qq"; v[k++] = "--kill-on-exit";
    v[k++] = "-o"; v[k++] = "/dev/null";
    if (strcmp(name, "none") == 0) {
        v[k++] = "-e"; v[k++] = "trace=none";
    } else {
        snprintf(tr, sizeof tr, "trace=%s", name);
        snprintf(inj, sizeof inj, "inject=%s:error=ENOSYS", name);
        v[k++] = "-e"; v[k++] = tr; v[k++] = "-e"; v[k++] = inj;
    }
    v[k++] = a0; v[k++] = real;
    for (int i = 1; i < argc; i++) v[k++] = argv[i];
    v[k] = NULL;
    child = fork();
    if (child < 0) { perror("inject-wrap: fork"); return 126; }
    if (child == 0) {
        execvp("strace", v);
        perror("inject-wrap: strace");
        _exit(126);
    }
    signal(SIGALRM, on_alarm);
    alarm(60);
    int st;
    while (waitpid(child, &st, 0) < 0) {}
    alarm(0);
    if (WIFEXITED(st)) return WEXITSTATUS(st);
    int sig = WTERMSIG(st);
    signal(sig, SIG_DFL);
    sigset_t m;
    sigemptyset(&m);
    sigaddset(&m, sig);
    sigprocmask(SIG_UNBLOCK, &m, NULL);
    raise(sig);
    return 128 + sig;
}
