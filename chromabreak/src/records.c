/* Five ProDOS records. Disk errors leave a usable table in memory. */
#include <string.h>
#include "prodos.h"
#include "records.h"
#pragma bss-name(push, "IOBUF")
static unsigned char file_buffer[1024];
#pragma bss-name(pop)
#pragma bss-name(push, "LOWBSS")
ChromaRecord records[5];
static unsigned char raw[38], pathname[65], volume[16];
#pragma bss-name(pop)
static struct { unsigned char count; void *path; void *buffer; unsigned char reference; } opened;
static struct { unsigned char count, reference; void *buffer; unsigned requested, actual; } transfer;
static struct { unsigned char count, reference; } closed;
static struct { unsigned char count; void *path; } prefix;
static struct { unsigned char count, unit; void *buffer; } online;
static struct { unsigned char count; void *path; unsigned char access, type; unsigned aux; unsigned char storage; unsigned date, time; } created;
unsigned char records_error;
static unsigned char call(unsigned char command, void *params)
{
    unsigned char error;
    prodos_command=command; prodos_params=params; error=prodos_call();
    if(error) records_error=error;
    return error;
}
static unsigned checksum(void)
{
    unsigned sum=0; unsigned char i;
    for(i=0;i<36u;++i) sum+=raw[i];
    return sum;
}
static void defaults(void)
{
    unsigned char i;
    memset(records,0,sizeof(records));
    for(i=0;i<5u;++i) memcpy(records[i].initials,"---",3);
}
static unsigned char path(void)
{
    unsigned char len;
    prefix.count=1; prefix.path=pathname;
    if(call(PD_GET_PREFIX,&prefix)) return 0;
    len=pathname[0];
    if(!len) {
        online.count=2; online.unit=*(unsigned char *)0xBF30; online.buffer=volume;
        if(call(PD_ONLINE,&online)) return 0;
        len=volume[0]&15u; if(!len) return 0;
        pathname[1]='/'; memcpy(pathname+2,volume+1,len); ++len;
    }
    if(len>53u) return 0;
    if(pathname[len]!='/') pathname[++len]='/';
    memcpy(pathname+len+1,"HIGHSCORES",10);
    pathname[0]=len+10u;
    return 1;
}
static unsigned char open_file(void)
{
    opened.count=3; opened.path=pathname; opened.buffer=file_buffer; opened.reference=0;
    return call(PD_OPEN,&opened);
}
static unsigned char close_file(void)
{
    closed.count=1; closed.reference=opened.reference;
    return call(PD_CLOSE,&closed);
}
static unsigned char move_file(unsigned char command)
{
    transfer.count=4; transfer.reference=opened.reference;
    transfer.buffer=raw; transfer.requested=sizeof(raw); transfer.actual=0;
    return call(command,&transfer);
}
void records_load(void)
{
    unsigned char i,j,error;
    unsigned sum;
    defaults(); pathname[0]=0;
    if(!path()) { pathname[0]=0; return; }
    if(open_file()) return;
    error=move_file(PD_READ); close_file();
    if(error || transfer.actual!=sizeof(raw)) return;
    if(memcmp(raw,"CBR1",4) || raw[4]!=1u || raw[5]) return;
    sum=checksum(); if(raw[36]!=(unsigned char)sum || raw[37]!=(unsigned char)(sum>>8)) return;
    memcpy(records,raw+6,sizeof(records));
    for(i=0;i<5u;++i) {
        if(records[i].score>59990u || records[i].mode>2u ||
           (i && records[i].score>records[i-1u].score)) { defaults(); return; }
        for(j=0;j<3u;++j) {
            char c=records[i].initials[j];
            if((c<'A' || c>'Z') && !(c=='-' && !records[i].score)) { defaults(); return; }
        }
    }
}
unsigned char __fastcall__ records_rank(unsigned score)
{
    unsigned char i;
    for(i=0;i<5u;++i) if(score>records[i].score) return i;
    return 255;
}
unsigned char records_submit(unsigned score, const char *initials, unsigned char mode)
{
    unsigned char rank=records_rank(score), i, error, close_error;
    unsigned sum;
    records_error=0;
    if(rank==255u) return 1;
    for(i=4;i>rank;--i) records[i]=records[i-1u];
    records[rank].score=score; memcpy(records[rank].initials,initials,3); records[rank].mode=mode;
    if(!pathname[0]) return 0;
    memcpy(raw,"CBR1",4); raw[4]=1; raw[5]=0;
    memcpy(raw+6,records,sizeof(records));
    sum=checksum(); raw[36]=sum; raw[37]=sum>>8;
    error=open_file();
    if(error==0x46u) {
        created.count=7; created.path=pathname; created.access=0xC3;
        created.type=6; created.aux=0; created.storage=1; created.date=created.time=0;
        if(call(PD_CREATE,&created)) return 0;
        error=open_file();
    }
    if(error) return 0;
    error=move_file(PD_WRITE); close_error=close_file();
    return !error && !close_error && transfer.actual==sizeof(raw);
}
