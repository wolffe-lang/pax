/* inject-wrap — stand in for one boreutils binary under tools/difftest and
 * run the real one under strace with one system call answered ENOSYS.
 * The wrapper is copied to <dir>/<util>; it execs
 *   strace -f -qq -o /dev/null -e trace=NAME [-e inject=NAME:error=ENOSYS]
 *          --argv0=<its own argv[0]> <REAL>/<util> args...
 * so the program sees exactly the argv[0] difftest gave (its stderr is
 * normalized on it). The file `.census-inject` beside the wrapper holds two
 * lines: the call's NAME ("none" traces nothing and injects nothing: the
 * baseline) and the directory of the real binaries. A file, not the
 * environment: difftest builds every child's environment from scratch.
 * A call answered ENOSYS can leave a program spinning (tee with no write),
 * so the wrapper arms a 60 s alarm that survives the exec: strace dies of
 * SIGALRM, and --kill-on-exit takes the tracee with it, so difftest's
 * pipes close and the case is decided (a FAIL) instead of hanging. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>

int main(int argc, char **argv) {
    char self[PATH_MAX], real[PATH_MAX], conf[PATH_MAX + 32], a0[PATH_MAX + 16];
    char name[96], dir[4096], tr[128], inj[160];
    ssize_t n = readlink("/proc/self/exe", self, sizeof self - 1);
    if (n < 0) { fprintf(stderr, "inject-wrap: no /proc/self/exe\n"); return 125; }
    self[n] = 0;
    char *slash = strrchr(self, '/');
    const char *base = slash + 1;
    *slash = 0;
    snprintf(conf, sizeof conf, "%s/.census-inject", self);
    FILE *f = fopen(conf, "r");
    if (!f || fscanf(f, "%95s %4095s", name, dir) != 2) {
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
    alarm(60);
    execvp("strace", v);
    perror("inject-wrap: strace");
    return 126;
}
