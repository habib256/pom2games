#!/usr/bin/env python3
"""Independent ProDOS name validation: byte classes, lengths, pointers and stack."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, compile_source, run, a2test

NAMES=(b'A',b'DEMO.AYS',b'A123456789ABCD.',b'A123456789ABCDEF',b'',b'a',b'A/B',b'A..09Z')


def valid(data):
    name=data.split(b'\0',1)[0]
    return int(1<=len(name)<=15 and 65<=name[0]<=90 and
               all(65<=c<=90 or 48<=c<=57 or c==46 for c in name[1:]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--reference',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='prodos-name-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text(r'''#include <string.h>
unsigned char __fastcall__ prodos_name_valid(const char *);
unsigned char align_call(void);void page_done(void);void finished(void);
unsigned char records[256],buffer[17],index;const char *nameptr;
static const char *const names[]={"A","DEMO.AYS","A123456789ABCD.","A123456789ABCDEF","","a","A/B","A..09Z"};
int main(void) {
    unsigned v;unsigned char pos,which;volatile unsigned guard=0xa55a;
    v=0;do {
        index=(unsigned char)v;buffer[0]=v>>8;buffer[1]=index;buffer[2]=0;
        records[index]=prodos_name_valid((char*)buffer);
        if(guard!=0xa55a)for(;;) {}++v;if((unsigned char)v==0)page_done();
    }while(v);
    for(pos=0;pos<16;++pos) {
        index=0;do {memset(buffer,'A',15);buffer[15]=0;buffer[16]=0xa5;
            buffer[pos]=index;records[index]=prodos_name_valid((char*)buffer);
            if(guard!=0xa55a||buffer[16]!=0xa5)for(;;) {}++index;
        }while(index);page_done();
    }
    for(which=0;which<8;++which) {
        index=0;do {nameptr=(char*)(0x9000u+index);strcpy((char*)nameptr,names[which]);
            records[index]=align_call();++index;
        }while(index);page_done();
    }
    finished();for(;;) {}return 0;
}
''')
        helper=work/'helper.s';helper.write_text('''.export _page_done,resume,_finished,_align_call
.import _prodos_name_valid,_nameptr,_index
.importzp sp
.bss
saved_sp: .res 2
result: .res 1
.code
_page_done: nop
resume: rts
_finished: rts
_align_call:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 lda _index
 sta sp
 lda #$91
 sta sp+1
 ldy #0
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda _nameptr
 ldx _nameptr+1
 jsr _prodos_name_valid
 sta result
 lda sp
 cmp _index
 bne fail
 lda sp+1
 cmp #$91
 bne fail
 ldy #0
 lda (sp),y
 cmp #$a5
 bne fail
 iny
 lda (sp),y
 cmp #$a5
 bne fail
 lda saved_sp
 sta sp
 lda saved_sp+1
 sta sp+1
 lda result
 ldx #0
 rts
fail: jmp fail
''')
        build(work,source,extra_sources=(helper,DEV/'lib/prodos/dir.c',DEV/'lib/prodos/name_valid.s'))
        linked=(work/'test.map').read_text().split('Segment list:')[0]
        assert 'name_valid.o):' in linked and 'dir.o):' not in linked
        assert '_prodos_mli' not in a2test.labels(work/'test.lbl')
        if args.reference:
            text=(DEV/'lib/prodos/dir.c').read_text();start=text.index('unsigned char __fastcall__ prodos_name_valid(')
            end=text.index('\n#endif',start);ref=work/'reference.c';ref.write_text(text[start:end]+'\n')
            compile_source(ref,work/'reference.o',['-t','none','-Oirs'])
            run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',work/'test.lbl','-o',work/'test.bin',
                 work/'crt0_apple2.o',work/'entry.o',work/'apple2io_asm.o',work/'helper.o',work/'reference.o',work/'hgrc.lib'])
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        assert labels['__BSS_RUN__']+labels['__BSS_SIZE__']<0x9000
        steps=[]
        for _ in range(280):steps.extend((labels.until('_page_done'),labels.peek('_records',256),labels.until('resume')))
        steps.append(labels.until('_finished'));result=a2test.run(disk,steps,iie=args.iie)
        wanted=[]
        for first in range(256):wanted.append(bytes(valid(bytes((first,second,0))) for second in range(256)))
        for pos in range(16):
            values=[]
            for c in range(256):
                data=bytearray(b'A'*15+b'\0\xa5');data[pos]=c;values.append(valid(data))
            wanted.append(bytes(values))
        wanted.extend(bytes([valid(name)])*256 for name in NAMES)
        assert result.dumps==wanted
        print(f'ProDOS names: 71,680 calls, all first/second bytes and byte classes at all 16 positions, '
              f'2,048 pointer/stack placements, guards and independent archive extraction; IIe={args.iie}, reference={args.reference}.')


if __name__=='__main__':main()
