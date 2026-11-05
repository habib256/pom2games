#!/usr/bin/env python3
"""Masked-sprite setup: full products, clipped geometry and one-call hints."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, run, a2test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full',action='store_true')
    parser.add_argument('--source',type=Path,default=DEV/'lib/hgrc/hgr_sprmask.s')
    parser.add_argument('--cold',action='store_true',help='first setup builds its own tables')
    parser.add_argument('--folded',action='store_true',help='use HGRC_X7_FOLDED builders')
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    heights=range(1,256) if args.full else (1,2,3,7,8,9,10,16,31,32,63,64,127,128,254,255)
    with tempfile.TemporaryDirectory(prefix='sprmask-setup-') as directory:
        work=Path(directory)
        kernel=work/'kernel.s'
        kernel.write_text(args.source.read_text()+
            '\n.export ms_setup,ms_setup_under,ms_rowbase,ms_page\n'
            '.exportzp ms_col,ms_yy,ms_w,ms_h,ms_stride\n')
        source=work/'fixture.s'
        source.write_text(""".exportzp ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.export hgr_fixed_rowlo,hgr_fixed_rowhi,_hgr_base
.import ms_setup,ms_setup_under,_hgr_build_columns,_hgr_build_phases
.import ms_page,_hgr_ms_block
.importzp ms_col,ms_yy,ms_w,ms_h,ms_stride
.importzp _hgr_ms_x,_hgr_ms_y,_hgr_ms_spr,_hgr_ms_under
hgr_fixed_rowlo=$0800
hgr_fixed_rowhi=$0900
.zeropage
ptr1: .res 2
ptr2: .res 2
ptr3: .res 2
ptr4: .res 2
tmp1: .res 1
tmp2: .res 1
tmp3: .res 1
tmp4: .res 1
.bss
_hgr_base: .res 1
height: .res 1
under_mode: .res 1
hint_mode: .res 1
index: .res 1
descriptor: .res 6
results: .res 13*256
.code
start:
 sei
 cld
 lda #0
 ldx #0
clear:
 .repeat 13,P
 sta results+256*P,x
 .endrepeat
 inx
 bne clear
 lda #$93
 sta descriptor
 lda #$BF
 sta descriptor+1
 lda #$EC
 sta descriptor+2
 lda #$2F
 sta descriptor+3
 lda #<descriptor
 sta _hgr_ms_spr
 lda #>descriptor
 sta _hgr_ms_spr+1
 lda #$FA
 sta _hgr_ms_under
 lda #$5B
 sta _hgr_ms_under+1
 jsr _hgr_build_columns
 jsr _hgr_build_phases
prepare:
 lda height
 sta descriptor+5
 ldx #1
 lda hint_mode
 beq start_index
 dex
start_index:
 stx index
loop:
 lda hint_mode
 bne hints
 lda index
 sta descriptor+4
 lda #0
 beq hint_ready
hints:
 lda #3
 sta descriptor+4
 lda index
hint_ready:
 sta _hgr_ms_block
 ; Save/restore must not depend on source-pointer scratch from earlier draws.
 lda #$5a
 sta ptr2
 lda #$a5
 sta ptr2+1
 lda #$c3
 sta ptr3
 lda #$69
 sta ptr3+1
 lda under_mode
 bne under
 jsr ms_setup
 jmp record
under:
 jsr ms_setup_under
record:
 ldx index
""")
        fields=('ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1',
                'ms_col','ms_yy','ms_w','ms_h','ms_stride','_hgr_ms_block','ms_page')
        with source.open('a') as out:
            for plane,name in enumerate(fields):
                out.write(f' lda {name}\n sta results+{plane*256},x\n')
            out.write(""" inc index
 beq :+
 jmp loop
:
page_done: nop
resume: jmp prepare
.export start,height,under_mode,hint_mode,page_done,resume,results
""")
        if args.cold:
            source.write_text(source.read_text().replace(
                ' jsr _hgr_build_columns\n jsr _hgr_build_phases\nprepare:', 'prepare:'))
        cfg=work/'fixture.cfg'
        cfg.write_text("""MEMORY {
 ZP: start=$50,size=$B0,type=rw;
 MAIN: start=$6000,size=$3000,type=rw,file=%O;
 TABLE: start=$4000,size=$1000,type=rw;
}
SEGMENTS {
 ZEROPAGE: load=ZP,type=zp;
 CODE: load=MAIN,type=ro;
 BSS: load=TABLE,type=bss;
}
""")
        if args.folded:
            # The combined builder additionally reserves the unused mask table.
            cfg.write_text(cfg.read_text().replace('TABLE: start=$4000,size=$1000',
                                                   'TABLE: start=$4000,size=$2000'))
        objects=[]
        for src in (source,kernel,DEV/'lib/hgrc/hgr_columns.s',DEV/'lib/hgrc/hgr_phases.s'):
            obj=work/(src.stem+'.o');objects.append(obj)
            run(['ca65',*(['-D','HGRC_X7_FOLDED=1'] if args.folded else []),'-o',obj,src])
        binary=work/'fixture.bin';labels=work/'fixture.lbl'
        run(['ld65','-C',cfg,'-Ln',labels,'-o',binary,*objects])
        L=a2test.labels(labels);disk=a2test.build_disk(work,'TEST',binary) if args.iie else None
        zeros=work/'zeros.bin';zeros.write_bytes(bytes(4096))
        count=0
        for xbase,y,base in ((28,0,0),(273,189,0x40)):
            for phase in range(7):
                x=xbase+phase
                for under in (0,1):
                    for hints in (0,1):
                        hs=(16,) if hints else heights
                        steps=a2test.bin_steps(binary)+[f'load:{zeros}@4000',L.poke('_hgr_ms_x',x&255),
                            f'poke:{L["_hgr_ms_x"]+1:04X}:{x>>8:02X}',L.poke('_hgr_ms_y',y),
                            L.poke('_hgr_base',base),L.poke('under_mode',under),L.poke('hint_mode',hints)]
                        for h in hs:
                            steps.extend((L.poke('height',h),L.until('page_done',limit=30000),
                                          L.peek('results',13*256),L.until('resume')))
                        result=a2test.run(disk,steps,iie=args.iie,timeout=300)
                        for batch,h in enumerate(hs):
                            wanted=bytearray(13*256)
                            for index in range(0 if hints else 1,256):
                                stride=3 if hints else index;hint=index if hints else 0
                                delta=0 if under else phase*(hint or h*stride)
                                data=(0xBF93+delta)&65535;mask=(0x2FEC+delta)&65535
                                values=(data&255,data>>8,mask&255,mask>>8,0xFA,0x5B,
                                        x//7,y,min(stride,40-x//7),min(h,192-y),stride,
                                        hint if under else 0,base or 0x20)
                                for plane,v in enumerate(values):wanted[plane*256+index]=v
                                count+=1
                            # ptr2/ptr3 are volatile scratch, not outputs of an
                            # under-only operation. Check every geometry,
                            # under-pointer, hint and page field independently.
                            start=4*256 if under else 0
                            assert result.dumps[batch][start:]==wanted[start:],(x,y,under,hints,h,[(i//256,i%256,a,b) for i,(a,b) in enumerate(zip(result.dumps[batch][start:],wanted[start:]),start) if a!=b][:12])
        print(f'Masked setup: {count:,} calls, all strides/seven phases/two placements, '
              f'full offsets and clipping, both modes and all 256 hints; '
              f'{L["ms_rowbase"]-L["ms_setup"]} setup bytes; '
              f'IIe={args.iie}, cold={args.cold}, folded={args.folded}.')


if __name__=='__main__':main()
