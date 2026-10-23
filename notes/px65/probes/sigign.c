/* px65 scratch probe: a child exec'd with SIGSEGV ignored installs a
 * SA_SIGINFO|SA_ONSTACK handler on SIGSEGV and SIGBUS, as wolf 0.2.35's
 * runtime does at start, and reads its dispositions back and
 * /proc/self/status's SigIgn and SigCgt. */
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
static void h(int s, siginfo_t *i, void *c) { (void)s; (void)i; (void)c; }
static void masks(const char *when) {
    FILE *f = fopen("/proc/self/status", "r");
    char l[256];
    while (f && fgets(l, sizeof l, f))
        if (!strncmp(l, "SigIgn:", 7) || !strncmp(l, "SigCgt:", 7)) printf("%s %s", when, l);
    if (f) fclose(f);
}
static const char *disp(int sig) {
    struct sigaction o;
    sigaction(sig, NULL, &o);
    return o.sa_handler == SIG_IGN ? "ignored" : o.sa_handler == SIG_DFL ? "default" : "a handler";
}
int main(int argc, char **argv) {
    if (argc > 1) {
        stack_t ss = {0}, old;
        sigaltstack(NULL, &old);
        printf("child: altstack flags %d\n", old.ss_flags);
        ss.ss_sp = malloc(32768); ss.ss_size = 32768;
        printf("child: sigaltstack %d\n", sigaltstack(&ss, NULL));
        printf("child: SEGV %s, BUS %s at start\n", disp(SIGSEGV), disp(SIGBUS));
        masks("child: at start");
        struct sigaction sa;
        memset(&sa, 0, sizeof sa);
        sa.sa_sigaction = h; sa.sa_flags = SA_SIGINFO | SA_ONSTACK; sigemptyset(&sa.sa_mask);
        printf("child: install SEGV %d BUS %d\n", sigaction(SIGSEGV, &sa, NULL), sigaction(SIGBUS, &sa, NULL));
        printf("child: SEGV %s, BUS %s after\n", disp(SIGSEGV), disp(SIGBUS));
        masks("child: after");
        return 0;
    }
    signal(SIGSEGV, SIG_IGN);
    masks("parent:");
    fflush(stdout);
    pid_t p = fork();
    if (p == 0) { execl("/proc/self/exe", argv[0], "child", (char *)0); execl(argv[0], argv[0], "child", (char *)0); _exit(127); }
    int st; waitpid(p, &st, 0);
    printf("parent: child status %d\n", st);
    return 0;
}
