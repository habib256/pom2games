/* Check the real keyboard routines against a read/strobe bus model. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu6502.h"
static uint8_t ram[65536], code[4096], latch;
static unsigned reads, strobes, delay, delivered, port_count, writes;
static uint16_t ports[16];
static uint8_t incoming;
static uint8_t read_byte(void *ctx,uint16_t address) {
 (void)ctx;
 if(address==0xC000) {
  assert(port_count<16);ports[port_count++]=address;++reads;
  if(!delivered&&reads>delay){latch=incoming;delivered=1;}
  return latch;
 }
 if(address==0xC010) {
  assert(port_count<16);ports[port_count++]=address;++strobes;latch&=127;return 0x40;
 }
 assert(address<0xC000||address>=0xC100);
 return ram[address];
}
static void write_byte(void *ctx,uint16_t address,uint8_t value) {
 (void)ctx;
 if(address<0x100||address>0x1FF)++writes;
 ram[address]=value;
}
static void call(Cpu *cpu,unsigned target) {
 unsigned steps;
 cpu->pc=target;cpu->s=0xFD;ram[0x1FF]=0x4F;ram[0x1FE]=0xFF;
 for(steps=0;cpu->pc!=0x5000&&steps<1000;++steps){cpu_step(cpu);assert(cpu->s>=0xFD);}
 assert(cpu->pc==0x5000&&cpu->s==0xFF);
}
int main(int argc,char **argv) {
 unsigned target[3],kind,flags,value,lag,count=0;size_t size;FILE *f;
 assert(argc==5);f=fopen(argv[1],"rb");assert(f);size=fread(code,1,sizeof(code),f);fclose(f);assert(size>0&&size<sizeof(code));
 for(kind=0;kind<3;++kind)target[kind]=(unsigned)strtoul(argv[kind+2],NULL,16);
 for(kind=0;kind<3;++kind)if(target[kind])for(flags=0;flags<16;++flags)
 for(value=0;value<(kind==0?128u:256u);++value)for(lag=0;lag<(kind==0?2u:1u);++lag){
  Cpu cpu={0};unsigned i,character,expected,carry,overflow,expected_p,expected_reads,expected_strobes;
  memset(ram,0xA5,sizeof(ram));memcpy(ram+0x6000,code,size);
  incoming=kind==0?(value|128):value;delay=lag?2:0;delivered=kind==2;latch=lag?(incoming&127):incoming;
  reads=strobes=port_count=writes=0;
  cpu.a=value;cpu.x=0x5A;cpu.y=0xA5;cpu.p=FU|((flags&8)?FD:0)|((flags&1)?FC:0)|((flags&2)?FI:0)|((flags&4)?FV:0);
  cpu.read=read_byte;cpu.write=write_byte;call(&cpu,target[kind]);
  character=kind==2?value:(incoming&128)?incoming&127:0;expected=character>=97&&character<=122?character-32:character;
  carry=kind==2||(incoming&128)?1:flags&1;overflow=kind!=2&&(incoming&128)?FV:(flags&4)?FV:0;
  expected_p=FU|((flags&8)?FD:0)|((flags&2)?FI:0)|carry|overflow|(expected&128)|(expected==0?FZ:0);
  assert(cpu.a==expected&&cpu.x==0x5A&&cpu.y==0xA5&&cpu.p==expected_p);
  expected_reads=kind==2?0:lag?3:1;expected_strobes=kind!=2&&(incoming&128)?1:0;
  assert(reads==expected_reads&&strobes==expected_strobes&&port_count==expected_reads+expected_strobes&&!writes);
  for(i=0;i<expected_reads;++i)assert(ports[i]==0xC000);
  if(expected_strobes)assert(ports[port_count-1]==0xC010);
  for(i=0;i<256;++i)assert(ram[i]==0xA5);
  if(expected_strobes&&target[1]){
   reads=strobes=port_count=0;call(&cpu,target[1]);assert(cpu.a==0&&reads==1&&strobes==0&&port_count==1&&ports[0]==0xC000);
  }
  ++count;
 }
 printf("%u bus cases: exact key reads/strobe order, delayed wait, consumed key, A/X/Y/P, ZP and stack OK\n",count);
 return 0;
}
