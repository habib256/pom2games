/* Run the real NMOS assembly against a traceable RGB/VIA/AY bus model. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu6502.h"
static unsigned char ram[65536], via[2][16], ay[2][16], selected[2];
static unsigned slot, machine, awake, col80, latch, an3=1;
static uint64_t deadline;
static unsigned period;
static Cpu cpu;
static int card(uint16_t a) { return slot && (a>>8)==0xC0+slot && (machine!=2 || slot!=4 || awake); }
static uint8_t read_byte(void *ctx, uint16_t a)
{
    unsigned chip=(a>>7)&1, reg=a&15;
    (void)ctx;
    if (a>=0xC050 && a<=0xC05F) {
        printf("R %04X 00 %02X\n",a,cpu.p);
        if(a==0xC05E) an3=0;
        if(a==0xC05F) { if(!an3) latch=((latch<<1)|col80)&3; an3=1; }
    }
    if(card(a)) {
        if(reg==4) { via[chip][13]&=~0x40; return (uint8_t)(0xFFFF-cpu.cycles); }
        if(reg==13 && !chip && period && cpu.cycles>=deadline) {
            via[chip][13]|=0x40;
            do { deadline+=period; } while(cpu.cycles>=deadline);
        }
        if(reg==14) return via[chip][14]|0x80;
        return via[chip][reg];
    }
    if(a>=0xC100 && a<0xC800) return 0xEA; /* stable absent slot ROM */
    return ram[a];
}
static void write_byte(void *ctx, uint16_t a, uint8_t v)
{
    unsigned chip=(a>>7)&1, reg=a&15;
    (void)ctx;
    if(a>=0xC000 && a<0xC800) printf("W %04X %02X %02X\n",a,v,cpu.p);
    if(a==0xC00D) col80=1;
    if(a==0xC00C) col80=0;
    if(a==0xC05E) an3=0;
    if(a==0xC05F) { if(!an3) latch=((latch<<1)|col80)&3; an3=1; }
    if(machine==2 && slot==4 && a==0xC403) awake=1;
    if(card(a)) {
        if(reg==14) {
            if(v&0x80) via[chip][14]|=v&0x7F;
            else via[chip][14]&=~v;
        } else {
            via[chip][reg]=v;
            if(reg==0) {
                if(v==0) memset(ay[chip],0,sizeof(ay[chip]));
                if(v==7) selected[chip]=via[chip][1]&15;
                if(v==6) ay[chip][selected[chip]]=via[chip][1];
            }
            if(reg==5 && !chip) {
                period=(via[chip][4]|((unsigned)v<<8))+2;
                deadline=cpu.cycles+period;
                via[chip][13]&=~0x40;
            }
        }
        return;
    }
    if(a>=0xC000 && a<0xC800) return;
    ram[a]=v;
    if(a==0x10FE) printf("S %u\n",v);
}
int main(int argc, char **argv)
{
    unsigned steps,chip,i;
    FILE *f;
    (void)argc;
    machine=atoi(argv[2]); slot=atoi(argv[3]);
    f=fopen(argv[1],"rb"); assert(f);
    assert(fread(ram+0x6000,1,0x3600,f)>0); fclose(f);
    ram[0xFBB3]=machine?6:0; ram[0xFBC0]=machine==2?0:0xE0;
    for(chip=0;chip<2;++chip) { via[chip][11]=0x20; via[chip][14]=0x55; }
    cpu.pc=0x6000; cpu.s=0xFF; cpu.p=FU|(atoi(argv[4])?FI:0);
    cpu.read=read_byte;cpu.write=write_byte;
    for(steps=0;!ram[0x10FF]&&steps<100000;++steps) cpu_step(&cpu);
    assert(ram[0x10FF]);
    printf("STATE"); for(i=0x1020;i<0x1030;++i) printf(" %02X",ram[i]); puts("");
    printf("RGB %u %u %u\n",latch,col80,an3);
    for(chip=0;chip<2;++chip) {
        printf("AY%u",chip); for(i=0;i<16;++i) printf(" %02X",ay[chip][i]); puts("");
        printf("VIA%u %02X %02X\n",chip,via[chip][11],via[chip][14]);
    }
    return 0;
}
