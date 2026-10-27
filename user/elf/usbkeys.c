/* px74 original black-box console probe. No kernel/driver sources used.
 * Same static binary on Linux's tty1 and PAX stdin; results go to COM1.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <sys/ioctl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static const char *labels[] = {
    "first-a", "shift-a", "shift-up", "ctrl-left", "six-keys",
    "caps-on", "caps-a", "caps-off", "keypad-enter", "alt-x",
    "repeat-a", "after-unplug", "after-replug", "ring-wrap", "finish"
};
static long long now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) _exit(4);
    return (long long)t.tv_sec * 1000000000LL + t.tv_nsec;
}
int main(void) {
    int output=1, input=0, linux_guest=0;
    mkdir("/dev",0755);
    if (mount("devtmpfs","/dev","devtmpfs",0,0)==0) {
        linux_guest=1;
        output=open("/dev/console",O_WRONLY|O_NOCTTY);
        input=open("/dev/tty1",O_RDWR|O_NOCTTY);
        /* Let USB enumeration complete before the ready line. */
        struct timespec settle={2,0}; nanosleep(&settle,0);
    }
    if(input<0 || output<0) return 2;
    if(linux_guest) {
        for(int i=0;i<32;i++) {
            char name[64]; snprintf(name,sizeof name,"/dev/input/event%d",i);
            int event=open(name,O_RDONLY|O_NONBLOCK);
            unsigned repeat[2];
            if(event>=0) {
                if(ioctl(event,EVIOCGREP,repeat)==0)
                    dprintf(output,"USBCONFIG event%d delay_ms=%u period_ms=%u\n",i,repeat[0],repeat[1]);
                close(event);
            }
        }
    }
    struct termios raw;
    if(tcgetattr(input,&raw)) return 2;
    cfmakeraw(&raw); raw.c_cc[VMIN]=1; raw.c_cc[VTIME]=0;
    if(tcsetattr(input,TCSANOW,&raw)) return 2;
    for(unsigned row=0;row<sizeof labels/sizeof labels[0];row++) {
        if(tcflush(input,TCIFLUSH)) return 2;
        dprintf(output,"USBREADY %u %s\n",row,labels[row]);
        struct pollfd p={input,POLLIN,0};
        unsigned char bytes[1024]; long long times[1024]; unsigned n=0;
        int timeout=(row==11 || row==12)?6000:3000;
        if(poll(&p,1,timeout)>0) {
            do {
                unsigned char b;
                int k=read(input,&b,1);
                if(k!=1) return 3;
                bytes[n]=b; times[n]=now(); n++;
            } while(n<1024 && poll(&p,1,row==10?400:180)>0);
        }
        dprintf(output,"USBROW %s",labels[row]);
        for(unsigned i=0;i<n;i++) dprintf(output," %02x",bytes[i]);
        if(!n) dprintf(output," none");
        dprintf(output,"\n");
        if(row==10) {
            dprintf(output,"USBTIMES");
            for(unsigned i=0;i<n;i++) dprintf(output," %lld",times[i]-times[0]);
            dprintf(output,"\n");
        }
    }
    dprintf(output,"USBDONE\n");
    if(linux_guest) { sync(); reboot(RB_POWER_OFF); }
    return 0;
}
