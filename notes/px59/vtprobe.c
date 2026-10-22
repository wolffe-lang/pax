/* Linux VT black-box measurements; console_codes(4), vcs(4), termios(3).
 * No kernel source. Static pid 1 in kasumi's Linux image under QEMU. */
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>
static int vt, out;
static void emit(const char *s) { if(write(vt,s,strlen(s))<0) _exit(3); }
static void answer(const char *name, const char *s) {
    unsigned char b[128]; tcflush(vt,TCIFLUSH); emit(s);
    struct pollfd p={vt,POLLIN,0}; int n=poll(&p,1,250)>0?read(vt,b,sizeof b):0;
    dprintf(out,"QUERY %s",name); for(int i=0;i<n;i++) dprintf(out," %02x",b[i]);
    dprintf(out,"%s\n",n?"":" none");
}
static void screen(const char *name,const char *s) {
    emit("\033[0m\033[2J\033[H"); emit(s);
    int v=open("/dev/vcsa1",O_RDONLY); unsigned char b[65536]; int n=read(v,b,sizeof b); close(v);
    if(n<4) {dprintf(out,"FAIL vcsa1 %d\n",n); return;}
    dprintf(out,"SCREEN %s cursor=%u,%u cells=",name,b[3]+1,b[2]+1);
    for(int i=4;i+1<n;i+=2) if(b[i]!=32 || b[i+1]!=7)
        dprintf(out," %d,%d:%02x/%02x",((i-4)/2)/b[1]+1,((i-4)/2)%b[1]+1,b[i],b[i+1]);
    dprintf(out,"\n");
}
int main(void) {
    mkdir("/dev",0755); mount("devtmpfs","/dev","devtmpfs",0,0);
    out=open("/dev/console",O_RDWR|O_NOCTTY); vt=open("/dev/tty1",O_RDWR|O_NOCTTY);
    if(out<0||vt<0) return 2;
    struct termios t; tcgetattr(vt,&t); cfmakeraw(&t); tcsetattr(vt,TCSANOW,&t);
    screen("CUP-HVP","\033[3;5HX\033[4;7fY");
    screen("CUU-CUD-CUF-CUB","\033[5;5H\033[2A\033[3C\033[B\033[DX");
    screen("HPA-VPA","\033[9G\033[4dX");
    screen("defaults-clamps","\033[999;999HX\033[0;0HY");
    screen("ED0","abc\033[2;1Hdef\033[1;2H\033[J");
    screen("ED1","abc\033[2;1Hdef\033[1;2H\033[1J");
    screen("ED2","abc\033[2J");
    screen("EL0","abcde\033[1;3H\033[K");
    screen("EL1","abcde\033[1;3H\033[1K");
    screen("EL2","abcde\033[1;3H\033[2K");
    screen("DECSC-DECRC","\033[31m\033[3;5H\0337\033[32m\033[H\0338X");
    screen("1049","MAIN\033[?1049h\033[Halt\033[?1049lX");
    screen("1049-enter","MAIN\033[?1049hA"); emit("\033[?1049l");
    screen("1049-nested","MAIN\033[?1049hA\033[?1049hB"); emit("\033[?1049l");
    screen("SGR22","\033[1mA\033[22mB");
    screen("SGR27","\033[7mA\033[27mB");
    screen("bright-background","\033[100m0\033[101m1\033[102m2\033[103m3\033[104m4\033[105m5\033[106m6\033[107m7");
    screen("indexed","\033[38;5;196mR\033[48;5;46mG\033[38;5;244mX");
    screen("OSC-BEL","A\033]52;c;eA==\007B");
    screen("OSC-ST","A\033]52;c;eA==\033\\B");
    screen("DECTCEM","\033[?25lA\033[?25hB");
    screen("DECSCUSR","\033[2 qA\033[6 qB\033[0 qC");
    screen("erase-attributes","\033[31;44mabc\033[1;2H\033[K");
    screen("1049-repeat","MAIN\033[?1049hA\033[?1049hB\033[?1049lC\033[?1049lD");
    screen("1049-attributes","\033[31mMAIN\033[?1049h\033[32mA\033[?1049lB");
    for(int bg=0;bg<2;bg++) {
        emit("\033[0m\033[2J\033[H");
        for(int i=0;i<256;i++) {char s[64]; snprintf(s,sizeof s,"\033[0;%d;5;%dmX",bg?48:38,i); emit(s);}
        int v=open("/dev/vcsa1",O_RDONLY); unsigned char b[516]; int n=read(v,b,sizeof b); close(v);
        dprintf(out,"PALETTE %s",bg?"BG":"FG");
        if(n!=516) dprintf(out," FAIL read=%d",n);
        else for(int i=0;i<256;i++) dprintf(out," %02x",b[5+i*2]);
        dprintf(out,"\n");
    }
    answer("DA1","\033[c"); answer("CPR","\033[3;5H\033[6n");
    answer("kitty","\033[?u"); answer("DECRQM2026","\033[?2026$p");
    const char *keys[]={"f1","f2","f3","f4","f5","f6","f7","f8","f9","f10","f11","f12","up","shift-up","ctrl-up","alt-up","shift-ctrl-up","alt-a","alt_r-a","dot"};
    for(unsigned i=0;i<sizeof(keys)/sizeof(keys[0]);i++) {
        tcflush(vt,TCIFLUSH); dprintf(out,"KEYREADY %u %s\n",i,keys[i]);
        unsigned char b[128]; struct pollfd p={vt,POLLIN,0};
        int n=poll(&p,1,10000)>0?read(vt,b,sizeof b):0;
        dprintf(out,"KEY %s",keys[i]); for(int j=0;j<n;j++) dprintf(out," %02x",b[j]);
        dprintf(out,"%s\n",n?"":" none");
    }
    dprintf(out,"DONE px59\n"); sync(); reboot(RB_POWER_OFF); return 0;
}
