/* W2: a traced set-ID exec reports its ids and retains its trace. The
   privileged control only reports ids and synchronizes with its parent. */
#include "common.h"

static void report_ids(char **argv) {
    int ready = argv[1][0] - '0', release = argv[2][0] - '0';
    out("security: W2 ids mode "); out(argv[3]);
    out(" uid "); dec(sys(102, 0, 0, 0)); out(" euid "); dec(sys(107, 0, 0, 0));
    out(" gid "); dec(sys(104, 0, 0, 0)); out(" egid "); dec(sys(108, 0, 0, 0));
    out(" nnp "); dec(sys6(157, 39, 0, 0, 0, 0, 0)); out("\n");
    char byte = 'x';
    require(sys(1, ready, (i64)&byte, 1) == 1);
    require(sys(0, release, (i64)&byte, 1) == 1);
    finish(0);
}

static void setid_user(int mode) {
    int traced = mode & 1;
    int ready[2], release[2];
    require(sys(22, (i64)ready, 0, 0) == 0 && sys(22, (i64)release, 0, 0) == 0);
    require(ready[1] < 10 && release[0] < 10);
    if (mode & 2) require(sys6(157, 38, 1, 0, 0, 0, 0) == 0);
    i64 child = sys6(56, SIGCHLD, 0, 0, 0, 0, 0);
    require(child >= 0);
    if (!child) {
        require(sys(3, ready[0], 0, 0) == 0 && sys(3, release[1], 0, 0) == 0);
        if (traced) require(sys6(101, 0, 0, 0, 0, 0, 0) == 0);
        char r[2] = {'0' + ready[1], 0}, w[2] = {'0' + release[0], 0}, m[2] = {'0' + mode, 0};
        char *argv[] = {"/bin/euid", r, w, m, 0}, *envp[] = {0};
        sys(59, (i64)argv[0], (i64)argv, (i64)envp);
        finish(99);
    }
    require(sys(3, ready[1], 0, 0) == 0 && sys(3, release[0], 0, 0) == 0);
    if (traced) {
        int status = 0;
        require(sys6(61, child, (i64)&status, 0, 0, 0, 0) == child);
        require(status == (5 << 8 | 0x7f));
        i64 cont = sys6(101, 7, child, 0, 0, 0, 0);
        out("security: W2 trace mode "); dec(mode); out(" stop "); dec(status);
        out(" continue "); dec(cont); out("\n");
        require(cont == 0);
    }
    char byte = 0;
    require(sys(0, ready[0], (i64)&byte, 1) == 1);
    if (mode == 0) {
        i64 attach = sys6(101, 16, child, 0, 0, 0, 0);
        out("security: attach-after-setid result "); dec(attach); out("\n");
        require(attach == -1);
    }
    require(sys(1, release[1], (i64)&byte, 1) == 1);
    int status = 0;
    require(sys6(61, child, (i64)&status, 0, 0, 0, 0) == child);
    out("security: W2 exit mode "); dec(mode); out(" status "); dec(status); out("\n");
    require(status == 0);
    finish(0);
}

void wit_main(i64 *sp) {
    char **argv = (char **)(sp + 1);
    if (streq(argv[0], "/bin/euid")) { require(sp[0] == 4); report_ids(argv); }
    if (sp[0] == 3 && streq(argv[1], "setid-user")) setid_user(argv[2][0] - '0');
    for (int mode = 0; mode < 4; mode++) {
        i64 child = sys6(56, SIGCHLD, 0, 0, 0, 0, 0);
        require(child >= 0);
        if (!child) {
            require(sys(116, 0, 0, 0) == 0);
            require(sys(119, 1000, 1000, 1000) == 0 && sys(117, 1000, 1000, 1000) == 0);
            char m[2] = {'0' + mode, 0};
            char *av[] = {"/bin/wit", "setid-user", m, 0}, *envp[] = {0};
            sys(59, (i64)av[0], (i64)av, (i64)envp);
            finish(99);
        }
        int status = 0;
        require(sys6(61, child, (i64)&status, 0, 0, 0, 0) == child && status == 0);
    }
    finish(0);
}
