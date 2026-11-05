#!/usr/bin/env python3
"""Doubled sprites: every source/color byte, pointer alignments and rejection."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, build, compile_source, run, a2test


def inflate(source,w,h,color):
    out=bytearray(w*h*4)
    for row in range(h):
        for col in range(w):
            for bit in range(7):
                if not source[row*w+col]&(1<<bit):continue
                for side in (0,1):
                    if color!=1 and color not in ((2,4) if side==0 else (3,5)):continue
                    x=(col*7+bit)*2+side
                    for dy in (0,1):
                        out[(row*2+dy)*w*2+x//7] |= (1<<(x%7)) | (128 if color in (4,5) else 0)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--reference',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-x2-bytes-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "hgr.h"
#include "hgr_x2.h"
void page_done(void);void finished(void);
unsigned char records[4][256],input[272],output[296];
int main(void) {
    unsigned value,i;
    unsigned char color,index,w,h;
    volatile unsigned guard=0xA55Au;
    value=0;
    do {
        index=(unsigned char)value;input[0]=index;
        output[0]=output[5]=0xA5u;
        hgr_inflate_x2(input,1,1,(unsigned char)(value>>8),output+1);
        for(i=0;i<4;++i)records[i][index]=output[i+1];
        if(output[0]!=0xA5u||output[5]!=0xA5u||input[0]!=index||guard!=0xA55Au)for(;;) {}
        ++value;if((unsigned char)value==0)page_done();
    } while(value);
    for(color=0;color<6;++color) for(value=0;value<256;++value) {
        for(i=0;i<sizeof(input);++i)input[i]=0x5Au;
        for(i=0;i<9;++i)input[value+i]=(unsigned char)(i*13u+7u);
        for(i=0;i<sizeof(output);++i)output[i]=0xA5u;
        hgr_inflate_x2(input+value,3,3,color,output+255-value);
        if(guard!=0xA55Au)for(;;) {}
        page_done();
    }
    for(i=0;i<sizeof(output);++i)output[i]=0xA5u;
    value=0;
    do {
        w=(unsigned char)value;h=(unsigned char)(value>>8);
        if(!w||!h||(unsigned)w*h>16383u)hgr_inflate_x2(input,w,h,1,output+1);
        if(guard!=0xA55Au)for(;;) {}
        ++value;
    } while(value);
    page_done();finished();for(;;) {}return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done,resume,_finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        disk=build(work,source,extra_sources=(marker,))
        if args.reference:
            obj=work/'reference.o'
            compile_source(DEV/'lib/hgrc/hgr_x2_target.c',obj,
                           ['-t','none','-Oirs','-I',DEV/'lib/hgrc'])
            run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
                 '-Ln',work/'test.lbl','-o',work/'test.bin',work/'crt0_apple2.o',
                 work/'entry.o',work/'apple2io_asm.o',work/'marker.o',obj,work/'hgrc.lib'])
            disk=a2test.build_disk(work,'TEST',work/'test.bin')
        labels=a2test.labels(work/'test.lbl')
        steps=[]
        for _ in range(256):
            steps += [labels.until('_page_done'),labels.peek('_records',1024),labels.until('resume')]
        for _ in range(1536):
            steps += [labels.until('_page_done'),labels.peek('_input',272),labels.peek('_output',296),labels.until('resume')]
        steps += [labels.until('_page_done',limit=20000),labels.peek('_output',296),labels.until('resume'),labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        widths=[1024]*256+[272,296]*1536+[296]
        raw=result.data;assert len(raw)==sum(widths)
        dumps=[];offset=0
        for width in widths:
            dumps.append(raw[offset:offset+width]);offset+=width
        pos=0
        for color in range(256):
            want=bytearray(1024)
            for bits in range(256):
                pixels=inflate(bytes((bits,)),1,1,color)
                for plane,value in enumerate(pixels):want[plane*256+bits]=value
            assert dumps[pos]==want,('byte/color',color)
            pos+=1
        pattern=bytes(i*13+7 for i in range(9))
        for color in range(6):
            pixels=inflate(pattern,3,3,color)
            for alignment in range(256):
                expected_input=bytearray([0x5A]*272);expected_input[alignment:alignment+9]=pattern
                expected_output=bytearray([0xA5]*296);expected_output[255-alignment:291-alignment]=pixels
                assert dumps[pos]==expected_input,('source',color,alignment)
                assert dumps[pos+1]==expected_output,('pixels/guards',color,alignment)
                pos+=2
        assert dumps[pos]==bytes([0xA5]*296),'rejected dimensions wrote output'
        print(f'HGR x2 bytes: 65,536 source/color pairs, 1,536 source/output alignments, '
              f'all zero/overflow dimensions, source and output guards; IIe={args.iie}, reference={args.reference}.')


if __name__=='__main__':main()
