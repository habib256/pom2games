#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu6502.h"
static uint8_t ram[65536],image[4096];
static unsigned entry,slot_addr,active_addr,acr_addr,ier_addr,ptr_addr,probe_addr,period_addr,period_size;
static unsigned active,irq,word,io_count,minimum,in_irq;
static uint64_t cases,min_cycles=9999,max_cycles;
static Cpu cpu;
static struct{unsigned address,value,write;}io[8];
static unsigned acr,ier;
static void access(unsigned a,unsigned v,unsigned w){assert(io_count<8);io[io_count++]=(typeof(io[0])){a,v,w};assert(cpu.p&FI);}
static uint8_t rd(void*p,uint16_t a){(void)p;if(a==0xC40B){access(a,acr,0);return acr;}if(a==0xC40E){access(a,ier|0x80,0);return ier|0x80;}assert(a<0xC000||a>=0xD000);return ram[a];}
static void wr(void*p,uint16_t a,uint8_t v){
 (void)p;if(a>=0xC000&&a<0xD000){access(a,v,1);assert(a==0xC40B||a==0xC40E||a==0xC404||a==0xC405);return;}
 if(a<0x100||a>0x1FF){
  assert(a==ptr_addr||a==ptr_addr+1||a==probe_addr||a==active_addr||a==acr_addr||a==ier_addr||(period_addr&&a>=period_addr&&a<period_addr+period_size));
  if(a==probe_addr)assert(cpu.p&FI); // shared scratch must remain masked
 }
 ram[a]=v;
}
static void interrupt(void){
 unsigned pc=cpu.pc,sp=cpu.s;uint8_t p=cpu.p;
 ram[0x100|cpu.s--]=pc>>8;ram[0x100|cpu.s--]=pc;ram[0x100|cpu.s--]=p&~FB;cpu.p|=FI;cpu.pc=0x4000;in_irq=1;
 unsigned n=0;while((cpu.pc!=pc||cpu.s!=sp)&&n++<32){cpu_step(&cpu);if(cpu.s<minimum)minimum=cpu.s;}assert(n<32);in_irq=0;
}
static void check(unsigned inject){
 ram[slot_addr]=4;ram[active_addr]=active;ram[acr_addr]=0x25;ram[ier_addr]=0x93;ram[ptr_addr]=ram[ptr_addr+1]=0xA5;ram[probe_addr]=0xAA;
 if(period_addr)memset(ram+period_addr,0xA5,period_size);
 acr=(word^0x31)&255;ier=((word>>8)^0x55)&0x7F;io_count=0;minimum=0xFD;
 cpu=(Cpu){0};cpu.read=rd;cpu.write=wr;cpu.pc=entry;cpu.a=word;cpu.x=word>>8;cpu.y=0x5A;cpu.s=0xFD;cpu.p=FU|(irq?FI:0)|((word&1)?FC:0)|((word&2)?FV:0);
 unsigned expected_p=cpu.p;ram[0x1FE]=0xFF;ram[0x1FF]=0x4F;unsigned n;
 for(n=0;cpu.pc!=0x5000&&n<128;++n){if(n==inject&&!(cpu.p&FI))interrupt();cpu_step(&cpu);if(cpu.s<minimum)minimum=cpu.s;}
 assert(n<128&&cpu.s==0xFF&&cpu.a==1&&cpu.x==(word>>8)&&cpu.y==5&&(cpu.p&0xCF)==(expected_p&0xCF));
 assert(io_count==(active?4:6));unsigned j=0;
 if(!active){assert(io[j].address==0xC40B&&!io[j].write&&io[j].value==acr);++j;assert(io[j].address==0xC40E&&!io[j].write&&io[j].value==(ier|0x80));++j;}
 unsigned addresses[]={0xC40B,0xC40E,0xC404,0xC405};unsigned values[]={active?0x65:(acr|0x40),0x40,word&255,word>>8};
 for(unsigned k=0;k<4;++k,++j)assert(io[j].write&&io[j].address==addresses[k]&&io[j].value==values[k]);
 assert(ram[active_addr]==1&&ram[ptr_addr]==0&&ram[ptr_addr+1]==0xC4);
 assert(ram[acr_addr]==(active?0x25:acr)&&ram[ier_addr]==(active?0x93:(ier|0x80)));
 if(inject==999){assert(minimum==0xFA);if(cpu.cycles<min_cycles)min_cycles=cpu.cycles;if(cpu.cycles>max_cycles)max_cycles=cpu.cycles;}
 ++cases;
}
int main(int argc,char**argv){
 assert(argc==11);unsigned *args[]={&entry,&slot_addr,&active_addr,&acr_addr,&ier_addr,&ptr_addr,&probe_addr,&period_addr,&period_size};
 for(unsigned i=0;i<9;++i)*args[i]=strtoul(argv[i+2],0,16);
 FILE*f=fopen(argv[1],"rb");assert(f);size_t n=fread(image,1,sizeof image,f);fclose(f);assert(n&&n<sizeof image);memset(ram,0xA5,sizeof ram);memcpy(ram+0x6000,image,n);
 uint8_t isr[]={0x48,0x8A,0x48,0x98,0x48,0xA9,0xEE,0x8D,probe_addr&255,probe_addr>>8,0x68,0xA8,0x68,0xAA,0x68,0x40};memcpy(ram+0x4000,isr,sizeof isr);
 for(active=0;active<2;++active)for(irq=0;irq<2;++irq)for(word=0;word<65536;++word)check(999);
 unsigned samples[]={0,1,255,256,0x1234,0x7FFF,0x8000,0xFFFF};
 for(active=0;active<2;++active)for(irq=0;irq<2;++irq)for(unsigned k=0;k<8;++k){word=samples[k];for(unsigned at=0;at<64;++at)check(at);}
 printf("%llu reload cases: exactlow/high,portorder,ACR/IERsnapshot,A/X/Y/P,I/D/stack/guards; IRQscratchaliases safe; cycles %llu..%llu\n",(unsigned long long)cases,(unsigned long long)min_cycles,(unsigned long long)max_cycles);
}
