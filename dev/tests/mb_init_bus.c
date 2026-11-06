#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu6502.h"
static uint8_t ram[65536],image[4096];static unsigned load,entry,slot_addr,chip_addr,active_addr,ptr,sites[12],io_count;static Cpu cpu;
static uint16_t ports[8];static uint8_t values[8];
static uint8_t rd(void*p,uint16_t a){(void)p;assert(a<0xC000||a>=0xD000);return ram[a];}
static void wr(void*p,uint16_t a,uint8_t v){
 (void)p;if(a>=0xC000&&a<0xD000){assert(io_count<8&&cpu.p&FI);ports[io_count]=a;values[io_count++]=v;return;}
 if(a<0x100||a>0x1FF){unsigned valid=a==slot_addr||a==chip_addr||a==active_addr||a==ptr||a==ptr+1;for(unsigned j=0;j<12;++j)valid|=a==sites[j]+2;assert(valid);}
 ram[a]=v;
}
int main(int argc,char**argv){
 assert(argc==20);unsigned *args[]={&load,&entry,&slot_addr,&chip_addr,&active_addr,&ptr};for(unsigned i=0;i<6;++i)*args[i]=strtoul(argv[i+2],0,16);for(unsigned i=0;i<12;++i)sites[i]=strtoul(argv[i+8],0,16);
 FILE*f=fopen(argv[1],"rb");assert(f);size_t n=fread(image,1,sizeof image,f);fclose(f);assert(n&&n<sizeof image);
 for(unsigned slot=1;slot<8;++slot)if(slot!=3)for(unsigned flags=0;flags<16;++flags){
  memset(ram,0xA5,sizeof ram);memcpy(ram+load,image,n);io_count=0;
  cpu=(Cpu){0};cpu.read=rd;cpu.write=wr;cpu.pc=entry;cpu.s=0xFD;cpu.a=slot;cpu.x=0x5A;cpu.y=0xA5;cpu.p=FU|((flags&1)?FC:0)|((flags&2)?FI:0)|((flags&4)?FV:0)|((flags&8)?FD:0);
  ram[0x1FF]=0x4F;ram[0x1FE]=0xFF;unsigned steps=0,minimum=0xFD;while(cpu.pc!=0x5000&&steps++<512){cpu_step(&cpu);if(cpu.s<minimum)minimum=cpu.s;}
  assert(steps<512&&cpu.s==0xFF&&minimum==0xF8&&cpu.a==slot&&cpu.x==0&&cpu.y==0);
  unsigned expected=FZ|((flags&2)?FI:0)|((flags&4)?FV:0)|((flags&8)?FD:0)|(slot>3?FC:0);assert((cpu.p&0xCF)==expected);
  assert(ram[slot_addr]==slot&&ram[chip_addr]==0&&ram[active_addr]==0&&ram[ptr]==0x80&&ram[ptr+1]==0xC0+slot);
  assert(io_count==8);unsigned offs[]={3,2,0,0,0x83,0x82,0x80,0x80},val[]={255,255,0,4,255,255,0,4};for(unsigned j=0;j<8;++j)assert(ports[j]==0xC000+slot*256+offs[j]&&values[j]==val[j]);
  for(unsigned j=0;j<12;++j){assert(ram[sites[j]+2]==0xC0+slot);unsigned reg=j%6;assert(ram[sites[j]]==(reg==0?0x8E:reg==3?0x8D:0x8C));assert(ram[sites[j]+1]==(reg==0||reg==3?1:0)+(j>=6?0x80:0));}
  printf("%u %u %llu\n",slot,flags,(unsigned long long)cpu.cycles);
 }
}
