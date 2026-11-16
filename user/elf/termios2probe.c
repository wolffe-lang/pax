/* Linux x86-64 termios2 ABI, observed through ioctls, never kernel or
 * libc source. Also linked statically against glibc 2.44 for its public
 * tcgetattr/tcsetattr/isatty path. ioctl_tty(2), TCGETS(2const), termios(3).
 * Run with no arguments for a new PTY; with 'console' for fd 0. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <termios.h>
#include <unistd.h>

#define GET2 0x802c542aUL
#define SET2 0x402c542bUL
#define SETW2 0x402c542cUL
#define SETF2 0x402c542dUL
#define BAUD 0x100fU
#define OTHER 0x1000U
struct t2 { uint32_t i,o,c,l; unsigned char line,cc[19]; uint32_t is,os; };
_Static_assert(sizeof(struct t2)==44, "x86-64 termios2");
static int bad;
static void row(const char *id, int ok) {
    printf("%s %s\n", id, ok ? "ok" : "FAIL");
    if (!ok) bad = 1;
}
static uint32_t rates[] = {0,50,75,110,134,150,200,300,600,1200,1800,
    2400,4800,9600,19200,38400,0,57600,115200,230400,460800,500000,
    576000,921600,1000000,1152000,1500000,2000000,2500000,3000000,
    3500000,4000000};
static unsigned code(unsigned b) { return b<16 ? b : 0x1000+b-16; }
static int get(int s, struct t2 *t) { memset(t,0,sizeof *t); return ioctl(s,GET2,t); }
int main(int argc, char **argv) {
    (void)argv;
    setvbuf(stdout,0,_IONBF,0);
    int m=-1,s=0;
    if (argc==1) {
        m=posix_openpt(O_RDWR|O_NOCTTY);
        if (m<0 || grantpt(m) || unlockpt(m) ||
            (s=open(ptsname(m),O_RDWR|O_NOCTTY))<0) {
            row("Z0-open",0); return 1;
        }
    }
    struct t2 saved,t,u;
    int r=get(s,&saved);
    row("Z1-get2",r==0);
    if (r) return 1;
    row("Z2-default-speeds",saved.is==38400 && saved.os==38400);
    unsigned char guard[60]; memset(guard,0xa5,sizeof guard);
    r=ioctl(s,GET2,guard+8);
    int ok=r==0;
    for (int k=0;k<8;k++) ok &= guard[k]==0xa5 && guard[52+k]==0xa5;
    row("Z3-layout-44",ok && !memcmp(guard+8,&saved,44));
    if (m>=0) row("Z4-master-shares",!get(m,&u) && !memcmp(&u,&saved,44));
    for(unsigned b=0;b<32;b++) {
        t=saved; t.c=(t.c&~BAUD)|code(b);t.is=12345;t.os=54321;
        r=ioctl(s,SET2,&t);
        unsigned want=b==16?54321:rates[b];
        char id[64];snprintf(id,sizeof id,"Z5-baud-%u",b);
        row(id,r==0 && !get(s,&u) && u.is==want && u.os==want && u.c==t.c);
    }
    for(unsigned b=0;b<32;b++) {
        t=saved;t.c=(t.c&~(BAUD|(BAUD<<16)))|13|(code(b)<<16);
        t.is=12345;t.os=54321;r=ioctl(s,SET2,&t);
        unsigned want=b==0?9600:b==16?12345:rates[b];
        char id[64];snprintf(id,sizeof id,"Z6-input-%u",b);
        row(id,r==0 && !get(s,&u) && u.is==want && u.os==9600 && u.c==t.c);
    }
    /* All actions import the same 44 bytes, including line and last cc. */
    unsigned long reqs[]={SET2,SETW2,SETF2};
    for(unsigned j=0;j<3;j++) {
        t=saved;t.c=(t.c&~(BAUD|(BAUD<<16)))|OTHER|(OTHER<<16);
        t.is=12345+j;t.os=54321+j;t.line=37;t.cc[18]=91;
        r=ioctl(s,reqs[j],&t);
        char id[64];snprintf(id,sizeof id,"Z7-action-%u",j);
        row(id,r==0 && !get(s,&u) && !memcmp(&u,&t,44));
    }
    if (m>=0) {
        for(unsigned j=0;j<3;j++) {
            t=saved;t.c=(t.c&~(BAUD|(BAUD<<16)))|OTHER|(OTHER<<16);
            t.is=12345+j;t.os=54321+j;t.cc[18]=91;t.l^=ECHO;
            r=ioctl(m,reqs[j],&t);
            char id[64];snprintf(id,sizeof id,"Z7-master-action-%u",j);
            row(id,r==0 && !get(s,&u) && !memcmp(&u,&t,44) &&
                !get(m,&u) && !memcmp(&u,&t,44));
        }
    }
    /* Legacy TCGETS has only 36 bytes; TCSETS retains BOTHER speeds. */
    memset(guard,0xa5,sizeof guard);r=ioctl(s,0x5401,guard+8);
    ok=r==0 && !memcmp(guard+8,&t,36);
    for(int k=44;k<60;k++)ok &=guard[k]==0xa5;
    row("Z8-legacy-get",ok);
    t.l^=ECHO;r=ioctl(s,0x5402,&t);
    row("Z9-legacy-set-other",r==0 && !get(s,&u) && !memcmp(&t,&u,44));
    t.c=(t.c&~(BAUD|(BAUD<<16)))|14;r=ioctl(s,0x5402,&t);
    row("Z10-legacy-set-standard",r==0 && !get(s,&u) && u.is==19200 && u.os==19200);
    /* Linux PTYs keep CS8/CREAD and clear PARENB and ADDRB. */
    if(m>=0) {
        unsigned flags[]={0,0x10,0x20,0x30,0x100,0x200,0xffffffffU};
        for(unsigned j=0;j<sizeof flags/sizeof *flags;j++) {
            t=saved;t.c=flags[j];t.is=12345;t.os=54321;
            r=ioctl(s,SET2,&t);
            unsigned want=(t.c&~0x200001b0U)|0xb0U;
            char id[64];snprintf(id,sizeof id,"Z11-flags-%u",j);
            row(id,r==0 && !get(s,&u) && u.c==want);
        }
    }
    ioctl(s,SET2,&saved);
    unsigned char *p=mmap(0,8192,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(p==MAP_FAILED){row("Z12-mapping",0);return 1;}
    mprotect(p+4096,4096,PROT_NONE);
    for(unsigned j=0;j<4;j++) {
        unsigned long q=j==0?GET2:reqs[j-1];
        errno=0;r=ioctl(s,q,p+4096-40);
        char id[64];snprintf(id,sizeof id,"Z12-short-%u",j);
        row(id,r==-1 && errno==EFAULT);
    }
    row("Z13-fault-atomic",!get(s,&u) && !memcmp(&u,&saved,44));
    memcpy(p+4096-36,&saved,36);
    row("Z14-legacy-short",ioctl(s,0x5402,p+4096-36)==0);
    memcpy(p,&saved,44);
    mprotect(p,4096,PROT_READ);
    errno=0;r=ioctl(s,GET2,p);
    row("Z14-readonly-get",r==-1 && errno==EFAULT);
    for(unsigned j=0;j<3;j++) {
        char id[64];snprintf(id,sizeof id,"Z14-readonly-set-%u",j);
        row(id,ioctl(s,reqs[j],p)==0);
    }
    munmap(p,8192);
    struct termios lib;
    row("Z15-tcgetattr",tcgetattr(s,&lib)==0);
    for(int action=TCSANOW;action<=TCSAFLUSH;action++) {
        cfsetispeed(&lib,B57600);cfsetospeed(&lib,B57600);
        char id[64];snprintf(id,sizeof id,"Z16-tcsetattr-%d",action);
        r=tcsetattr(s,action,&lib);
        row(id,r==0 && tcgetattr(s,&lib)==0 &&
            cfgetispeed(&lib)==B57600 && cfgetospeed(&lib)==B57600);
    }
    if(m>=0) {
        struct winsize win={.ws_row=24,.ws_col=40};ioctl(s,TIOCSWINSZ,&win);
        memset(&win,0,sizeof win);
        int columns=isatty(s) && ioctl(s,TIOCGWINSZ,&win)==0 ? win.ws_col/10 : 1;
        row("Z17-terminal-columns",columns==4);
        if(columns<1)columns=1;
        const char *names[]={"ant","bee","cat","dog"};
        printf("Z17-layout ");
        for(int j=0;j<4;j++) {
            if(j==3) printf("%s\n",names[j]);
            else printf("%-10s%s",names[j],(j+1)%columns==0 ? "\n" : "");
        }
        /* A queued raw byte survives NOW/DRAIN, but FLUSH discards it. */
        for(unsigned j=0;j<6;j++) {
            t=saved;t.l=0;t.i=0;t.cc[6]=1;t.cc[5]=0;ioctl(s,SET2,&t);
            (void)!write(m,"q",1);struct pollfd f={s,POLLIN,0};poll(&f,1,1000);
            r=ioctl(j<3?s:m,reqs[j%3],&t);f.revents=0;poll(&f,1,100);
            char id[64];snprintf(id,sizeof id,"Z18-flush-%u",j);
            row(id,r==0 && !!(f.revents&POLLIN)==(j%3!=2));
            if(j%3!=2){char c;(void)!read(s,&c,1);}
        }
    }
    ioctl(s,SET2,&saved);
    if(m>=0){close(s);close(m);}
    return bad;
}
