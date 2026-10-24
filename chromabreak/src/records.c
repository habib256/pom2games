/* Five ProDOS records and the farthest sector reached (byte 5 of the file,
 * 0 in files from earlier versions). Scores count tens of points; byte 4 is
 * the format: 1 held points (up to 59990, converted on load), 2 holds tens.
 * Disk errors leave usable values. */
#include <string.h>
#include "layout.h"
#include "prodos.h"
#include "records.h"
#pragma bss-name(push, "IOBUF")
static unsigned char file_buffer[1024];
#pragma bss-name(pop)
#pragma bss-name(push, "LOWBSS")
ChromaRecord records[5];
static unsigned char raw[38], pathname[65], volume[16];
/* The file name in pathname, while the overlay's replaces it. */
static unsigned char *overlay_name;
#pragma bss-name(pop)
static struct { unsigned char count; void *path; } prefix;
static struct { unsigned char count, unit; void *buffer; } online;
unsigned char records_error, records_progress;
static unsigned char failed(unsigned char error)
{
    if(error) records_error=error;
    return error;
}
static unsigned char call(unsigned char command, void *params)
{
    prodos_command=command; prodos_params=params;
    return failed(prodos_call());
}
static unsigned checksum(void)
{
    static unsigned sum; static unsigned char i;
    for(sum=i=0;i<36u;++i) sum+=raw[i];
    return sum;
}
static void defaults(void)
{
    static unsigned char i;
    memset(records,0,sizeof(records)); records_progress=0;
    for(i=0;i<5u;++i) memcpy(records[i].initials,"---",3);
}
static unsigned char path(void)
{
    static unsigned char len;
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
/* The whole-file calls (dev/lib/prodos/file.s) on pathname. */
static void file(void *buffer, unsigned length)
{
    prodos_file_name=pathname; prodos_file_iobuf=file_buffer;
    prodos_file_buffer=buffer; prodos_file_length=length;
}
void records_load(void)
{
    static unsigned char i,j;
    static unsigned sum;
    defaults(); pathname[0]=0;
    if(!path()) { pathname[0]=0; return; }
    file(raw,sizeof(raw));
    if(failed(prodos_load()) || prodos_file_actual!=sizeof(raw)) return;
    if(memcmp(raw,"CBR1",4) || !raw[4] || raw[4]>2u || raw[5]>=CB_LEVELS) return;
    sum=checksum(); if(raw[36]!=(unsigned char)sum || raw[37]!=(unsigned char)(sum>>8)) return;
    memcpy(records,raw+6,sizeof(records));
    for(i=0;i<5u;++i) {
        if(raw[4]==1u) records[i].score/=10u;
        if(records[i].score>65000u || records[i].mode>2u ||
           (i && records[i].score>records[i-1u].score)) { defaults(); return; }
        for(j=0;j<3u;++j) {
            char c=records[i].initials[j];
            if((c<'A' || c>'Z') && !(c=='-' && !records[i].score)) { defaults(); return; }
        }
    }
    records_progress=raw[5];
}
unsigned char __fastcall__ records_rank(unsigned score)
{
    unsigned char i;
    for(i=0;i<5u;++i) if(score>records[i].score) return i;
    return 255;
}
unsigned char records_submit(unsigned score, const char *initials, unsigned char mode)
{
    unsigned char rank=records_rank(score), i;
    if(rank==255u) return 1;
    for(i=4;i>rank;--i) records[i]=records[i-1u];
    records[rank].score=score; memcpy(records[rank].initials,initials,3); records[rank].mode=mode;
    return records_save();
}
/* Write the records and records_progress; 0 = not saved. */
unsigned char records_save(void)
{
    static unsigned sum;
    records_error=0;
    if(!pathname[0]) return 0;
    memcpy(raw,"CBR1",4); raw[4]=2; raw[5]=records_progress;
    memcpy(raw+6,records,sizeof(records));
    sum=checksum(); raw[36]=sum; raw[37]=sum>>8;
    file(raw,sizeof(raw));
    return !failed(prodos_save()) && prodos_file_actual==sizeof(raw);
}
/* Load the ENDING overlay, kept next to HIGHSCORES, at dest; 0 = failure. */
unsigned char records_load_overlay(void *dest, unsigned size)
{
    static unsigned char error, len;
    if(!pathname[0]) return 0;
    len=pathname[0];
    overlay_name=pathname+len-9; memcpy(overlay_name,"ENDING",6); pathname[0]=len-4u;
    /* ProDOS refuses buffers in pages marked used (page 2 of the DHGR
     * memory): load_free frees them in the system bitmap for the read. */
    file(dest,size);
    error=failed(prodos_load_free());
    memcpy(overlay_name,"HIGHSCORES",10); pathname[0]=len;
    return !error && prodos_file_actual;
}
