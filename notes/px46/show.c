/* px46: a probe shell. su(1) runs it as the target's shell (or by -s);
 * it prints what it was given and who it is, one fact a line, and exits
 * with the status named by PX46_STATUS (default 0). Written for this lane. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <grp.h>
#include <fcntl.h>
#include <errno.h>
extern char **environ;
static int cmp(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
int main(int argc, char **argv) {
    for (int i = 0; i < argc; i++) printf("argv[%d]=%s\n", i, argv[i]);
    char cwd[4096];
    printf("cwd=%s\n", getcwd(cwd, sizeof cwd) ? cwd : "?");
    uid_t r, e, s; gid_t gr, ge, gs;
    getresuid(&r, &e, &s); getresgid(&gr, &ge, &gs);
    printf("uids=%u %u %u gids=%u %u %u\n", r, e, s, gr, ge, gs);
    gid_t g[256]; int n = getgroups(256, g);
    printf("groups=");
    for (int i = 0; i < n; i++) printf("%s%u", i ? "," : "", g[i]);
    printf("\n");
    mode_t m = umask(0); umask(m);
    printf("umask=%04o\n", m);
    printf("sid==pid %d pgid==pid %d\n", getsid(0) == getpid(), getpgid(0) == getpid());
    for (int fd = 0; fd < 8; fd++) if (fcntl(fd, F_GETFD) != -1) printf("fd %d open\n", fd);
    int k = 0; for (char **p = environ; *p; p++) k++;
    char **v = malloc(sizeof(char *) * (k + 1));
    for (int i = 0; i < k; i++) v[i] = environ[i];
    qsort(v, k, sizeof(char *), cmp);
    for (int i = 0; i < k; i++) printf("env %s\n", v[i]);
    const char *st = getenv("PX46_STATUS");
    return st ? atoi(st) : 0;
}
