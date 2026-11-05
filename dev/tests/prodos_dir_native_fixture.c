/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
 * Controlled MLI implementation for directory reference/native comparisons.
 * Each trace records every request; parameter counts, prefix trim, reference,
 * I/O buffer and 512-byte request are checked independently of the parser.
 */
#include <string.h>
#include "prodos.h"
void bench_begin(void);void bench_end(void);void prepared(void);
void *prodos_file_iobuf=(void*)0x1000;
unsigned char prodos_command;void *prodos_params;
#pragma bss-name(push,"LOWBSS")
static unsigned char storage[4096];
#pragma bss-name(pop)
static unsigned char disk[2][512],suffix[256];
static unsigned char trace[16],trace_n,next_block,blocks,gotlo,gothi,header_len,header_per;
static unsigned char prefix_error,open_error,read_error,close_error,style;
unsigned result;
unsigned char scenario;
static const struct {unsigned char max,stride,suffix_len,elen,per,blocks,gotlo,gothi,pre,op,rd,cl,style;} cases[]={
#include "prodos_dir_cases.inc"
};
#define WORD(p,o) (*(unsigned*)((p)+(o)))
unsigned char prodos_call(void){
 unsigned char *p=(unsigned char*)prodos_params,*path;
 unsigned char command=prodos_command;
 trace[trace_n++]=command;
 switch(command){
 case PD_GET_PREFIX:
  if(prefix_error)return prefix_error;
  if(p[0]!=1)return 0x55;
  path=(unsigned char*)WORD(p,1);if(style==64){path[0]=1;path[1]=47;}else if(style==65){path[0]=4;memcpy(path+1,"/VOL",4);}else if(style==66)path[0]=0;else{path[0]=5;memcpy(path+1,"/VOL/",5);}break;
 case PD_OPEN:
  if(open_error)return open_error;
  path=(unsigned char*)WORD(p,1);
  if(p[0]!=3||((style==64)?(path[0]!=1||path[1]!=47):(style==66)?path[0]!=0:(path[0]!=4||memcmp(path+1,"/VOL",4)))||WORD(p,3)!=(unsigned)prodos_file_iobuf)return 0x55;
  p[5]=7;break;
 case PD_READ:
  if(read_error)return read_error;
  if(p[0]!=4||p[1]!=7||WORD(p,4)!=512)return 0x55;
  if(next_block==blocks)return 0x4C;
  memcpy((void*)WORD(p,2),disk[next_block++],512);
  p[6]=gotlo;p[7]=gothi;break;
 case PD_CLOSE:
  if(p[0]!=1||p[1]!=7)return 0x55;
  return close_error;
 default:return 0x55;
 }
 return 0;
}
static void entry(unsigned char page,unsigned char slot,unsigned char type,const char *name){
 unsigned char *p=disk[page]+4+(unsigned)slot*39;
 p[0]=type|strlen(name);memcpy(p+1,name,strlen(name));
}
static void setup(void){
 memset(storage,0xA5,sizeof(storage));memset(disk,0,sizeof(disk));memset(trace,0,sizeof(trace));
 trace_n=next_block=0;
 blocks=cases[scenario].blocks;gotlo=cases[scenario].gotlo;gothi=cases[scenario].gothi;
 header_len=cases[scenario].elen;header_per=cases[scenario].per;
 prefix_error=cases[scenario].pre;open_error=cases[scenario].op;
 read_error=cases[scenario].rd;close_error=cases[scenario].cl;style=cases[scenario].style;
 if(style>=128){disk[0][43]=((style&15)<<4)|1;disk[0][44]=65;}
 else if(style>=32&&style<48){memset(disk[0]+44,65,style-32);disk[0][43]=0x10|(style-32);}
 else if(style==2){disk[0][4]=disk[1][4]=0x11;disk[0][5]=disk[1][5]='A';}
 else{
 entry(0,1,0x10,"FIRST.AYS");entry(0,2,0xD0,"SUBDIR.AYS");entry(0,3,0x20,"SECOND.AYS");entry(0,4,0,"DELETED.AYS");
 entry(1,0,0x30,"THIRD.AYS");entry(1,1,0x10,"OTHER.BIN");
 if(style==1)entry(0,1,0x10,"A123456789ABCDE");
 }
 disk[0][0x23]=header_len;disk[0][0x24]=header_per;
 memset(suffix,'X',sizeof(suffix));suffix[cases[scenario].suffix_len]=0;
 if(cases[scenario].suffix_len==4)memcpy(suffix,".AYS",4);
 if(cases[scenario].suffix_len==5)memcpy(suffix,".NONE",5);
 if(cases[scenario].suffix_len==14)memcpy(suffix,"123456789ABCDE",14);
}
int main(void){
 for(scenario=0;scenario<sizeof(cases)/sizeof(cases[0]);++scenario){
  setup();bench_begin();
  result=prodos_dir_list((char*)storage+8,cases[scenario].stride,cases[scenario].max,(char*)suffix);
  bench_end();prepared();
 }
 for(;;){}return 0;
}
