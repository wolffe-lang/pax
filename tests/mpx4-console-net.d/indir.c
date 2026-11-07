/* indir DIR PROG [ARG...] (px105): chdir(DIR), then execv(PROG, PROG ARG...).
   The console's run list starts every command in /, and tests/mpx4-console-net's
   https row runs den inside the repository it cloned. Static, as user/net's
   witnesses are built. */
#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc < 3) {
        fputs("usage: indir DIR PROG [ARG...]\n", stderr);
        return 2;
    }
    if (chdir(argv[1]) != 0) {
        perror("indir: chdir");
        return 1;
    }
    execv(argv[2], argv + 2);
    perror("indir: execv");
    return 1;
}
