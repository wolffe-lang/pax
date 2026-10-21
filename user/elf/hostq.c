/* hostq.c — px57 (pax#107): what s253's calls ask of a kernel, at the
 * system-call level, before wolf has them. s253 (wolf-lang#847, for
 * wolf 0.2.35) adds `os_name` and `os_arch` (uname(2)'s sysname and
 * machine, lowercased), `os_core_limit` and `os_set_core_limit`
 * (prlimit64(2) of RLIMIT_CORE, read and set), `os_core_off`
 * (prctl(PR_SET_DUMPABLE, 0)) and `fs_adopt` (an inherited descriptor:
 * F_GETFD, then F_SETFD FD_CLOEXEC). Its spec reads PAX's answers from
 * PAX's source; this probe asks them of the running kernel, on PAX and
 * on Linux, as root and as a user. One static program; every row is
 * the answer of one raw call (px38.h's `rc`: the result or -errno).
 *
 *   hostq           the rows; re-runs itself as `hostq adopt` with a
 *                   file open at descriptor 5, not close-on-exec, as a
 *                   supervisor hands a child one
 *   hostq adopt     (what the probe execs of itself)
 *
 * A line that starts with `~` is left out of the comparison with Linux
 * by name (tests/mpx5-jobs' J13): the kernel's name (`PAX`, `Linux`)
 * and a set of the core limit, which Linux allows a process (to its own
 * values, or lower) and PAX refuses whatever the values (pax#93's
 * table). The hard limit's line is the container's own on the
 * container's side (its --ulimit core=0:0), as sigwolf's is.
 *
 * Written from uname(2), getrlimit(2) (prlimit64), prctl(2)
 * (PR_SET_DUMPABLE, PR_GET_DUMPABLE), fcntl(2) (F_GETFD, F_SETFD,
 * FD_CLOEXEC), proc(5) (/proc/self/fd) and the uapi headers; no
 * kernel's or libc's source. */
#include "px38.h"
#include <sys/prctl.h>
#include <sys/utsname.h>

#define RLIMIT_CORE_NR 4

static const char *lim(unsigned long v)
{
    static char b[2][32];
    static int k;
    k ^= 1;
    if (v == ~0UL) return "unlimited";
    snprintf(b[k], sizeof b[k], "%lu", v);
    return b[k];
}

static const char *link5(void)
{
    static char b[512];
    long n = rc(SYS_readlink, (long)"/proc/self/fd/5", (long)b, sizeof b - 1, 0, 0);
    if (n < 0) {
        snprintf(b, sizeof b, "(readlink %ld)", n);
        return b;
    }
    b[n] = 0;
    return b;
}

static int adopt(void)
{
    say("H: an inherited descriptor 5: F_GETFD %ld (open, not close-on-exec)\n", rc(SYS_fcntl, 5, F_GETFD, 0, 0, 0));
    say("H: /proc/self/fd/5 before the adoption: %s\n", link5());
    long set = rc(SYS_fcntl, 5, F_SETFD, FD_CLOEXEC, 0, 0);
    long get = rc(SYS_fcntl, 5, F_GETFD, 0, 0, 0);
    say("H: F_SETFD FD_CLOEXEC: %ld; F_GETFD then: %ld\n", set, get);
    say("H: /proc/self/fd/5 after: %s\n", link5());
    say("H: a descriptor never opened (9): F_GETFD %ld\n", rc(SYS_fcntl, 9, F_GETFD, 0, 0, 0));
    return 0;
}

int main(int argc, char **argv)
{
    if (argc > 1 && strcmp(argv[1], "adopt") == 0) return adopt();
    long uid = rc(SYS_getuid, 0, 0, 0, 0, 0);
    say("hostq: px57's probe of s253's calls (pax#107), as %s\n", uid == 0 ? "root" : "a user");

    struct utsname u;
    long r = rc(SYS_uname, (long)&u, 0, 0, 0, 0);
    say("~H: uname: %ld, sysname %s (os_name: the sysname lowercased)\n", r, r == 0 ? u.sysname : "-");
    say("H: uname: machine %s (os_arch)\n", r == 0 ? u.machine : "-");

    unsigned long old[2] = { 0, 0 };
    r = rc(SYS_prlimit64, 0, RLIMIT_CORE_NR, 0, (long)old, 0);
    say("H: prlimit64 RLIMIT_CORE read: %ld, soft %s (os_core_limit's first)\n", r, lim(old[0]));
    say("H: the core limit, hard: %s\n", lim(old[1]));
    unsigned long same[2] = { old[0], old[1] };
    say("~H: prlimit64 RLIMIT_CORE set to itself: %ld (os_set_core_limit)\n",
        rc(SYS_prlimit64, 0, RLIMIT_CORE_NR, (long)same, 0, 0));
    unsigned long zero[2] = { 0, 0 };
    say("~H: prlimit64 RLIMIT_CORE set to soft 0, hard 0 (a lowering): %ld\n",
        rc(SYS_prlimit64, 0, RLIMIT_CORE_NR, (long)zero, 0, 0));

    say("H: prctl PR_GET_DUMPABLE: %ld\n", rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0));
    say("H: prctl PR_SET_DUMPABLE 0: %ld (os_core_off)\n", rc(SYS_prctl, PR_SET_DUMPABLE, 0, 0, 0, 0));
    say("H: prctl PR_GET_DUMPABLE then: %ld\n", rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0));
    rc(SYS_prctl, PR_SET_DUMPABLE, 1, 0, 0, 0);

    /* fs_adopt: a descriptor 5 handed across exec. */
    char dir[64], path[96];
    snprintf(dir, sizeof dir, "/tmp/hq-%ld", uid);
    snprintf(path, sizeof path, "%s/five", dir);
    rc(SYS_mkdir, (long)dir, 0755, 0, 0, 0);
    long fd = rc(SYS_open, (long)path, O_WRONLY | O_CREAT | O_TRUNC, 0644, 0, 0);
    if (fd < 0) {
        say("H: open %s: %ld\n", path, fd);
        return 1;
    }
    if (fd != 5) {
        rc(SYS_dup2, fd, 5, 0, 0, 0);
        rc(SYS_close, fd, 0, 0, 0, 0);
    }
    pid_t c = fork();
    if (c == 0) {
        char *av[] = { "hostq", "adopt", 0 };
        execv(argv[0], av); /* the run list's absolute path (not
                               /proc/self/exe: pax#106) */
        _exit(127);
    }
    int st = 0;
    waitpid(c, &st, 0);
    say("hostq: the adopting child exit %d\n", WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st));
    return 0;
}
