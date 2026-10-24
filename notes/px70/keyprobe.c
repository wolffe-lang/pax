/* px70 own black-box keyboard probe; public terminal interfaces only. */
#define main px59_unused_main
#include "../px59/vtprobe2.c"
#undef main
#include "keys70.h"
int main(void) {
    mkdir("/dev",0755); mount("devtmpfs","/dev","devtmpfs",0,0);
    out=open("/dev/console",O_RDWR|O_NOCTTY); vt=open("/dev/tty1",O_RDWR|O_NOCTTY);
    if (out<0 || vt<0 || tcgetattr(vt,&raw)<0) return 2;
    cfmakeraw(&raw); if (tcsetattr(vt,TCSANOW,&raw)<0) return 2;
    for (unsigned i=0;i<sizeof labels/sizeof labels[0];i++) {
        tcflush(vt,TCIFLUSH); dprintf(out,"KEYREADY %u %s\n",i,labels[i]);
        unsigned char b[256]; int n=0; struct pollfd p={vt,POLLIN,0};
        if (poll(&p,1,3000)>0) {
            do { int k=read(vt,b+n,sizeof b-n); if(k<=0)break; n+=k; }
            while(n<(int)sizeof b && poll(&p,1,200)>0);
        }
        dprintf(out,"KEY %s",labels[i]);
        for(int j=0;j<n;j++)dprintf(out," %02x",b[j]);
        dprintf(out,"%s\n",n?"":" none");
    }
    dprintf(out,"DONE px70 keys\n"); sync(); reboot(RB_POWER_OFF); return 0;
}
