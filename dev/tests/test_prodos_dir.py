#!/usr/bin/env python3
"""Directory filtering/error propagation on host C and cc65, including overlays."""
from pathlib import Path
import subprocess
import tempfile
from test_hgr import DEV, compile_source, run, a2test

SOURCE = r'''
#include <string.h>
#include "dir.c"
void *prodos_file_iobuf;
static unsigned char disk[2][512], errors[256], calls[256], next_block;
static char names[3][16], suffix[257];
unsigned result;
void done(void);
unsigned char __fastcall__ prodos_mli(unsigned char command, void *params) {
    ++calls[command];
    if (errors[command]) return errors[command];
    switch (command) {
    case PD_GET_PREFIX: block[0]=5; memcpy(block+1,"/VOL/",5); break;
    case PD_OPEN:
        if (block[0]!=4 || memcmp(block+1,"/VOL",4)) return 0x40;
        p_open.ref=7; break;
    case PD_READ:
        if (p_read.ref!=7) return 0x43;
        if (next_block==2) return 0x4C;
        memcpy(p_read.buf,disk[next_block++],512); p_read.got=512; break;
    case PD_CLOSE: if (p_close.ref!=7) return 0x43; break;
    }
    return 0;
}
static void entry(unsigned char page, unsigned char slot, unsigned char type, const char *name) {
    unsigned char *p=disk[page]+4+slot*39;
    p[0]=type | strlen(name); memcpy(p+1,name,strlen(name));
}
static void setup(void) {
    memset(calls,0,sizeof calls); memset(errors,0,sizeof errors);
    memset(names,0xA5,sizeof names); memset(disk,0,sizeof disk);
    disk[0][0x23]=39; disk[0][0x24]=13; next_block=0;
    entry(0,1,0x10,"FIRST.AYS"); entry(0,2,0xD0,"SUBDIR.AYS");
    entry(0,3,0x20,"SECOND.AYS"); entry(0,4,0,"DELETED.AYS");
    entry(1,0,0x30,"THIRD.AYS"); entry(1,1,0x10,"OTHER.BIN");
}
#define CHECK(x) do { if (!(x)) return __LINE__; } while (0)
static unsigned checks(void) {
    unsigned i;
    setup();
    CHECK(prodos_dir_list(names[0],16,3,".AYS")==0);
    CHECK(prodos_dir_count==3);
    CHECK(!strcmp(names[0],"FIRST.AYS") && !strcmp(names[1],"SECOND.AYS") && !strcmp(names[2],"THIRD.AYS"));
    CHECK(calls[PD_CLOSE]==1);
    setup();
    CHECK(prodos_dir_list(names[0],16,1,".AYS")==0);
    CHECK(prodos_dir_count==1 && calls[PD_READ]==1 && calls[PD_CLOSE]==1);
    CHECK((unsigned char)names[1][0]==0xA5);
    setup(); memset(suffix,'X',256); suffix[256]=0;
    CHECK(prodos_dir_list(names[0],16,3,suffix)==0);
    CHECK(prodos_dir_count==0 && calls[PD_GET_PREFIX]==0);
    setup();
    CHECK(prodos_dir_list(names[0],16,0,"")==0);
    CHECK(prodos_dir_count==0 && calls[PD_GET_PREFIX]==0);
    setup(); errors[PD_CLOSE]=0x27;
    CHECK(prodos_dir_list(names[0],16,3,".NONE")==0x27);
    CHECK(calls[PD_CLOSE]==1);
    setup(); errors[PD_READ]=0x27; errors[PD_CLOSE]=0x43;
    CHECK(prodos_dir_list(names[0],16,3,"")==0x27);
    CHECK(calls[PD_CLOSE]==1);
    setup(); errors[PD_OPEN]=0x46;
    CHECK(prodos_dir_list(names[0],16,3,"")==0x46);
    CHECK(prodos_dir_count==0 && calls[PD_CLOSE]==0);
    setup(); entry(0,1,0x10,"A123456789ABCDE");
    CHECK(prodos_dir_list(names[0],16,1,"123456789ABCDE")==0 && prodos_dir_count==1);
    setup();
    CHECK(prodos_dir_list(names[0],16,3,"A123456789ABCDE")==0 && prodos_dir_count==0 && calls[PD_GET_PREFIX]==0);
    for (i=0;i<16;++i) {
        setup(); memset(disk,0,sizeof disk); disk[0][0x23]=39; disk[0][0x24]=13;
        entry(0,1,i<<4,"A");
        CHECK(prodos_dir_list(names[0],16,1,"")==0);
        if (i>=1 && i<=3) { CHECK(prodos_dir_count==1); }
        else { CHECK(prodos_dir_count==0); }
    }
    CHECK(prodos_name_valid("A") && prodos_name_valid("A123456789ABCD."));
    CHECK(!prodos_name_valid("") && !prodos_name_valid("1A") && !prodos_name_valid("a") && !prodos_name_valid("A123456789ABCDEF."));
    return 0;
}
int main(void) { result=checks(); done(); return result!=0; }
#ifdef HOST
#include <stdio.h>
void done(void) { if (result) fprintf(stderr,"failed source line %u\n", result); }
#endif
'''


def check(work, cpu="6502", overlay=False):
    src=work/'directory.c'; src.write_text(SOURCE)
    subprocess.run(['cc','-DHOST','-D__fastcall__=','-I',str(DEV/'lib/prodos'),str(src),'-o',str(work/'host')],check=True)
    subprocess.run([str(work/'host')],check=True)
    marker=work/'marker.s'; marker.write_text('.export _done\n.code\n_done: rts\n')
    objects=[]
    for i,path in enumerate((DEV/'cc65/crt0_apple2.s',src,marker,DEV/'lib/prodos/name_valid.s')):
        obj=work/f'{i}.o'
        flags=['-t','none','--cpu',cpu,'-Ors','--static-locals','-I',DEV/'lib/prodos']
        if overlay: flags += ['--rodata-name','CODE','--data-name','CODE']
        compile_source(path,obj,flags)
        objects.append(obj)
    binary=work/'directory.bin'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',work/'directory.lbl','-o',binary,*objects])
    labels=a2test.labels(work/'directory.lbl')
    disk=work/'blank.dsk'; disk.write_bytes(bytes(143360))
    data=a2test.run(disk,a2test.bin_steps(binary)+[labels.until('_done'),labels.peek('_result',2)],iie=cpu=="65c02").data
    assert data==b'\0\0', f'cc65 check failed at source line {int.from_bytes(data,"little")}'
    print(f'ProDOS directory: filtering, bounded scans, long suffixes, close/error priority and names OK ({cpu}, overlay={overlay}).')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='prodos-dir-') as tmp:
        check(Path(tmp))
        check(Path(tmp),"65c02",True)
