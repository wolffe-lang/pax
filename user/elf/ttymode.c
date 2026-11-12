/* ttymode.c — px124: the terminal modes a session finds, read from its
 * standard input: `lflag 0xHEX echo|-echo icanon|-icanon isig|-isig`
 * (termios(3)'s c_lflag and three of its bits, as stty(1) names them).
 * tests/mpx5-init types it in a session after one that left the console
 * with its echo off (`stty -echo; exit`): /bin/init puts the boot's modes
 * back between sessions. Exit 1, with one line on standard error, when
 * standard input is no terminal.
 *
 * Written from termios(3) and tcgetattr(3) (man-pages 6.7). No kernel's
 * or C library's source. */
#include <stdio.h>
#include <termios.h>

int main(void)
{
    struct termios t;
    if (tcgetattr(0, &t) != 0) {
        perror("ttymode: tcgetattr");
        return 1;
    }
    printf("lflag 0x%x %secho %sicanon %sisig\n", (unsigned)t.c_lflag, (t.c_lflag & ECHO) ? "" : "-",
           (t.c_lflag & ICANON) ? "" : "-", (t.c_lflag & ISIG) ? "" : "-");
    return 0;
}
