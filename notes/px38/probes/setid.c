/* setid.c — px38, item 2(c): set-user-ID and set-group-ID execution, and
 * what takes the bits away. Root copies the probe under several owners
 * and modes; a user (1000:2000, groups {2999}) runs each copy, which
 * prints the ids it finds itself with.
 *
 *   setid DIR [NOSUIDDIR]   DIR on a tmpfs mounted without nosuid and
 *                           without noexec; NOSUIDDIR on one with nosuid
 *   setid show TAG          (the copy's job)
 */
#include "px38.h"
#include <sys/auxv.h>
#include <sys/prctl.h>

static const char *D;
static char PB[8][600];
static int pbi;
static const char *in2(const char *d, const char *n)
{
    char *p = PB[pbi++ & 7];
    snprintf(p, 600, "%s/%s", d, n);
    return p;
}
static const char *in(const char *n) { return in2(D, n); }

static void show(const char *tag)
{
    say("%s: uid %s | gid %s | groups %s | cap %s | AT_SECURE %lu AT_UID %lu AT_EUID %lu AT_GID %lu AT_EGID %lu | dumpable %ld\n", tag,
        uids(), gids(), groups(), capeff(), getauxval(AT_SECURE), getauxval(AT_UID), getauxval(AT_EUID), getauxval(AT_GID),
        getauxval(AT_EGID), rc(SYS_prctl, PR_GET_DUMPABLE, 0, 0, 0, 0));
}

static const unsigned G2999[1] = { 2999 };

/* Run `path show TAG` as (uid, gid); `nnp`: with no_new_privs set first. */
static void run_as(unsigned uid, unsigned gid, const char *path, const char *tag, int nnp)
{
    pid_t p = fork();
    if (p == 0) {
        if (uid != 0) become(uid, gid, 1, G2999);
        if (nnp && rc(SYS_prctl, PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) _exit(96);
        char *av[] = { (char *)path, (char *)"show", (char *)tag, NULL };
        char *ev[] = { NULL };
        execve(path, av, ev);
        say("%s: execve %d\n", tag, -errno);
        _exit(0);
    }
    int st = reap(p);
    if (st != 0) say("%s: ended %d\n", tag, st);
}

static void mk(const char *self, const char *name, unsigned uid, unsigned gid, unsigned mode)
{
    if (copy_file(self, name, 0700) != 0 || chown(name, uid, gid) != 0 || chmod(name, mode) != 0) {
        say("! cannot make %s (%d)\n", name, -errno);
        _exit(98);
    }
}

/* What a change by `who` does to the bits of a file 1000:2000. */
static void bits(const char *who, unsigned uid, unsigned mode, int what)
{
    static const char *W[] = { "write of one byte", "write of no bytes", "ftruncate to 0", "truncate(path) to its own size", "open with O_TRUNC",
                               "pwrite at 4096", "utimensat", "chmod to the same mode", "rename", "a hard link made", "fallocate",
                               "an O_RDWR open and close", "append (O_APPEND) of one byte" };
    const char *f = in("bits");
    put_file(f, "bits\n", 0666, 1000, 2000);
    chmod(f, mode);
    pid_t p = fork();
    if (p == 0) {
        unsigned gs[1] = { 2000 };
        if (uid != 0) become(uid, uid == 1000 ? 2000 : 2999, uid == 1000 ? 1 : 0, gs);
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        long r = -1;
        int fd;
        switch (what) {
        case 0: fd = open(f, O_WRONLY); r = fd < 0 ? -(long)errno : write(fd, "X", 1); break;
        case 1: fd = open(f, O_WRONLY); r = fd < 0 ? -(long)errno : write(fd, "X", 0); break;
        case 2: fd = open(f, O_WRONLY); r = fd < 0 ? -(long)errno : rc(SYS_ftruncate, fd, 0, 0, 0, 0); break;
        case 3: r = rc(SYS_truncate, (long)f, 5, 0, 0, 0); break;
        case 4: fd = open(f, O_WRONLY | O_TRUNC); r = fd < 0 ? -(long)errno : 0; break;
        case 5: fd = open(f, O_WRONLY); r = fd < 0 ? -(long)errno : pwrite(fd, "X", 1, 4096); break;
        case 6: r = rc(SYS_utimensat, AT_FDCWD, (long)f, 0, 0, 0); break;
        case 7: r = rc(SYS_chmod, (long)f, mode, 0, 0, 0); break;
        case 8: r = rename(f, in("bits2")) == 0 ? (rename(in("bits2"), f), 0L) : -(long)errno; break;
        case 9: r = link(f, in("bitsl")) == 0 ? (unlink(in("bitsl")), 0L) : -(long)errno; break;
        case 10: fd = open(f, O_WRONLY); r = fd < 0 ? -(long)errno : rc(SYS_fallocate, fd, 0, 0, 8192, 0); break;
        case 11: fd = open(f, O_RDWR); r = fd < 0 ? -(long)errno : 0; break;
        case 12: fd = open(f, O_WRONLY | O_APPEND); r = fd < 0 ? -(long)errno : write(fd, "X", 1); break;
        }
        say("bits: mode %04o, %s by %s: %ld, mode after %04o\n", mode, W[what], who, r, mode_of(f));
        _exit(0);
    }
    reap(p);
}

int main(int argc, char **argv)
{
    if (argc > 2 && strcmp(argv[1], "show") == 0) { show(argv[2]); return 0; }
    if (argc > 2 && strcmp(argv[1], "chain") == 0) {
        show("06755 of 1001:2001, itself");
        char *av[] = { argv[2], (char *)"show", (char *)"  and the plain program it runs", NULL };
        char *ev[] = { NULL };
        execve(argv[2], av, ev);
        return 1;
    }
    if (argc < 2) { say("usage: setid DIR [NOSUIDDIR]\n"); return 2; }
    D = argv[1];
    char self[256];
    long n = readlink("/proc/self/exe", self, sizeof self - 1);
    if (n <= 0) return 2;
    self[n] = 0;
    umask(0);
    chmod(D, 0755);
    for (int i = 1; i < argc && i < 3; i++) {
        /* how each directory is mounted, as /proc/self/mountinfo says */
        static char b[65536];
        int fd = open("/proc/self/mountinfo", O_RDONLY);
        long k = 0, r;
        while (fd >= 0 && k < (long)sizeof b - 1 && (r = read(fd, b + k, sizeof b - 1 - k)) > 0) k += r;
        if (fd >= 0) close(fd);
        b[k] = 0;
        /* the mount the directory is on: the longest mount point that is a prefix of its path */
        char best[256] = "", bopt[256] = "";
        for (char *l = strtok(b, "\n"); l; l = strtok(NULL, "\n")) {
            char mp[256], opt[256];
            if (sscanf(l, "%*d %*d %*s %*s %255s %255s", mp, opt) != 2) continue;
            size_t n = strlen(mp);
            if (strncmp(mp, argv[i], n) == 0 && (argv[i][n] == '/' || argv[i][n] == 0 || n == 1) && n >= strlen(best)) {
                snprintf(best, sizeof best, "%s", mp);
                snprintf(bopt, sizeof bopt, "%s", opt);
            }
        }
        say("mount: %s is on %s, mounted %s\n", argv[i], best, bopt);
    }

    say("== execve of a set-ID file, by 1000:2000 with groups {2999}\n");
    mk(self, in("plain"), 1001, 2001, 0755);
    mk(self, in("suid"), 1001, 2001, 04755);
    mk(self, in("sgid"), 1001, 2001, 02755);
    mk(self, in("both"), 1001, 2001, 06755);
    mk(self, in("suidroot"), 0, 0, 04755);
    mk(self, in("sgidroot"), 0, 0, 02755);
    mk(self, in("suid-nox"), 1001, 2001, 04655);  /* set-user-ID, no owner execute bit */
    mk(self, in("sgid-nogx"), 1001, 2001, 02745); /* set-group-ID, no group execute bit */
    mk(self, in("suid-self"), 1000, 2000, 06755); /* the caller's own */
    run_as(1000, 2000, in("plain"), "plain 0755 of 1001:2001   ", 0);
    run_as(1000, 2000, in("suid"), "04755 of 1001:2001        ", 0);
    run_as(1000, 2000, in("sgid"), "02755 of 1001:2001        ", 0);
    run_as(1000, 2000, in("both"), "06755 of 1001:2001        ", 0);
    run_as(1000, 2000, in("suidroot"), "04755 of 0:0              ", 0);
    run_as(1000, 2000, in("sgidroot"), "02755 of 0:0              ", 0);
    run_as(1000, 2000, in("suid-nox"), "04655 of 1001:2001        ", 0);
    run_as(1000, 2000, in("sgid-nogx"), "02745 of 1001:2001        ", 0);
    run_as(1000, 2000, in("suid-self"), "06755 of 1000:2000 (own)  ", 0);
    say("== the same, by root\n");
    run_as(0, 0, in("plain"), "root runs plain           ", 0);
    run_as(0, 0, in("suid"), "root runs 04755 of 1001   ", 0);
    run_as(0, 0, in("both"), "root runs 06755 of 1001   ", 0);
    say("== where the bits are not honoured\n");
    run_as(1000, 2000, in("both"), "06755 with no_new_privs   ", 1);
    {
        /* a #! script whose interpreter is the plain copy */
        char text[700];
        snprintf(text, sizeof text, "#!%s show\n", in("plain")); /* the kernel adds the script's path: the TAG */
        put_file(in("script"), text, 06755, 1001, 2001);
        pid_t p = fork();
        if (p == 0) {
            become(1000, 2000, 1, G2999);
            char *av[] = { (char *)in("script"), NULL };
            char *ev[] = { NULL };
            execve(av[0], av, ev);
            say("script: execve %d\n", -errno);
            _exit(0);
        }
        reap(p);
    }
    if (argc > 2) {
        mk(self, in2(argv[2], "both"), 1001, 2001, 06755);
        run_as(1000, 2000, in2(argv[2], "both"), "06755 on a nosuid mount   ", 0);
        unlink(in2(argv[2], "both"));
    }
    {
        /* a set-ID program that then runs a plain one: what the child keeps */
        pid_t p = fork();
        if (p == 0) {
            become(1000, 2000, 1, G2999);
            /* suid copy, told to exec the plain copy: done here by hand through `chain` */
            char *av[] = { (char *)in("both"), (char *)"chain", (char *)in("plain"), NULL };
            char *ev[] = { NULL };
            execve(av[0], av, ev);
            _exit(0);
        }
        reap(p);
    }

    say("== what takes the bits away (a file 1000:2000; `owner` is 1000 in group 2000, `other` is 1002, each with write permission)\n");
    chmod(D, 0777); /* so that a rename or a new link is the actor's to make */
    static const unsigned M[] = { 06777, 04777, 02777, 02767, 06766 };
    for (unsigned m = 0; m < sizeof M / sizeof *M; m++) {
        bits("its owner", 1000, M[m], 0);
        bits("another user", 1002, M[m], 0);
        bits("root", 0, M[m], 0);
    }
    for (int what = 1; what <= 12; what++) {
        bits("its owner", 1000, 06777, what);
        if (what != 7) bits("another user", 1002, 06777, what);
        bits("root", 0, 06777, what);
    }
    say("setid: done\n");
    return 0;
}
