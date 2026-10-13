/* as.c — px39: become a user, then run a program. The way a test makes
 * a process that is not root, on Linux and on PAX alike, with no
 * account anywhere: the ids are numbers.
 *
 *   as UID GID PROG [ARG...]
 *
 * The order that works (px38): no supplementary group, then the three
 * group ids, then the three user ids, each a raw call; then `execve` of
 * PROG with the caller's environment. Exit 99 with a line when a step is
 * refused, 98 when PROG cannot be run. */
#include "px38.h"

int main(int argc, char **argv, char **envp)
{
    if (argc < 4) { say("usage: as UID GID PROG [ARG...]\n"); return 2; }
    long u = atol(argv[1]), g = atol(argv[2]), r;
    if ((r = rc(SYS_setgroups, 0, 0, 0, 0, 0)) != 0) { say("as: setgroups(0, NULL) = %ld\n", r); return 99; }
    if ((r = rc(SYS_setresgid, g, g, g, 0, 0)) != 0) { say("as: setresgid(%ld, %ld, %ld) = %ld\n", g, g, g, r); return 99; }
    if ((r = rc(SYS_setresuid, u, u, u, 0, 0)) != 0) { say("as: setresuid(%ld, %ld, %ld) = %ld\n", u, u, u, r); return 99; }
    execve(argv[3], argv + 3, envp);
    say("as: execve %s: %d\n", argv[3], -errno);
    return 98;
}
