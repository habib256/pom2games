#!/usr/bin/env python3
"""Preshift setup arithmetic: source offsets, clipping and preserved mode scratch."""
import argparse
import subprocess
import tempfile
from pathlib import Path
from test_hgr import DEV, a2test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full',action='store_true',help='all 910,350 nonzero dimension/phase/placement pairs')
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    heights=range(1,256) if args.full else (1,2,3,7,8,9,10,11,15,16,31,32,63,64,127,128,254,255)
    with tempfile.TemporaryDirectory(prefix='preshift-setup-') as directory:
        work=Path(directory)
        source=work/'fixture.s'
        source.write_text('''
.exportzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4, height, stride
.export _hgr_rowlo, _hgr_rowhi, _hgr_preshift_xor_run
.import _hgr_xs_setup, _hgr_build_columns, _hgr_build_phases
.importzp _hgr_xs_x, _hgr_xs_y, _hgr_xs_spr
.importzp _hgr_b_col, _hgr_b_y, _hgr_b_w, _hgr_b_h, _hgr_b_stride, _hgr_b_src, _hgr_b_mode
_hgr_rowlo=$0800
_hgr_rowhi=$0900
.zeropage
ptr1: .res 2
ptr2: .res 2
tmp1: .res 1
tmp2: .res 1
tmp3: .res 1
tmp4: .res 1
height: .res 1
stride: .res 1
.bss
descriptor: .res 4
results: .res 7*256
.code
start:
 sei
 cld
 jsr init
 lda #1
 sta stride
sweep_start:
loop:
 lda stride
 sta descriptor+2
 lda #$A5
 sta tmp4
setup_start:
 jsr _hgr_xs_setup
setup_done:
 lda tmp4
 cmp #$A5
 bne fail
 lda _hgr_b_mode
 cmp #$D3
 bne fail
 ldx stride
 lda _hgr_b_src
 sta results,x
 lda _hgr_b_src+1
 sta results+256,x
 lda _hgr_b_w
 sta results+512,x
 lda _hgr_b_h
 sta results+768,x
 lda _hgr_b_col
 sta results+1024,x
 lda _hgr_b_y
 sta results+1280,x
 lda _hgr_b_stride
 sta results+1536,x
 inc stride
 bne loop
done: jmp done
fail: jmp fail
single:
 sei
 cld
 jsr init
 jmp loop
init:
 lda #0
 ldx #0
clear:
 .repeat 16, page
 sta $4000+page*256,x
 .endrepeat
 inx
 bne clear
 lda #$93
 sta descriptor
 lda #$BF
 sta descriptor+1
 lda height
 sta descriptor+3
 lda #<descriptor
 sta _hgr_xs_spr
 lda #>descriptor
 sta _hgr_xs_spr+1
 lda #$D3
 sta _hgr_b_mode
 jsr _hgr_build_columns
 jsr _hgr_build_phases
 rts
_hgr_preshift_xor_run: rts
.export start, single, sweep_start, setup_start, setup_done, done, results
''')
        cfg=work/'fixture.cfg'
        cfg.write_text('''MEMORY {
 ZP: start=$50, size=$B0, type=rw;
 MAIN: start=$6000, size=$3000, type=rw, file=%O;
 TABLE: start=$4000, size=$1000, type=rw;
}
SEGMENTS {
 ZEROPAGE: load=ZP, type=zp;
 CODE: load=MAIN, type=ro;
 BSS: load=TABLE, type=bss;
}
''')
        sources=[source]+[DEV/'lib/hgrc'/name for name in
                          ('hgr_preshift_asm.s','hgr_sprite_params.s','hgr_columns.s','hgr_phases.s')]
        objects=[]
        for src in sources:
            obj=work/(src.stem+'.o');objects.append(obj)
            subprocess.run(['ca65','-o',str(obj),str(src)],check=True)
        binary,labels=work/'fixture.bin',work/'fixture.lbl'
        subprocess.run(['ld65','-C',str(cfg),'-Ln',str(labels),'-o',str(binary),*map(str,objects)],check=True)
        L=a2test.labels(labels)
        disk=a2test.build_disk(work,'TEST',binary) if args.iie else None
        total=0
        for xbase,y in ((28,0),(273,189)):
            for phase in range(7):
                x=xbase+phase
                for h in heights:
                    steps=a2test.bin_steps(binary)+[L.poke('height',h),L.poke('_hgr_xs_x',x&255),
                          f'poke:{L["_hgr_xs_x"]+1:04X}:{x>>8:02X}',L.poke('_hgr_xs_y',y),
                          L.until('sweep_start'),L.until('done'),L.peek('results',7*256)]
                    result=a2test.run(disk,steps,iie=args.iie)
                    expected=bytearray(7*256)
                    for stride in range(1,256):
                        pointer=(0xBF93+phase*h*stride)&65535
                        values=(pointer&255,pointer>>8,min(stride,40-x//7),min(h,192-y),x//7,y,stride)
                        for field,value in enumerate(values):expected[field*256+stride]=value
                    assert result.mem(L['results'],7*256)==expected,(x,y,h)
                    total+=result.cycles[1]-result.cycles[0]
        print(f'Preshift setup: {len(heights)*255*14:,} stride/height/phase/placement pairs; '
              f'full 16-bit phase offsets, clipping, tmp4/mode preserved; '
              f'{L["_hgr_xs_run"]-L["_hgr_xs_setup"]} setup code bytes; sweeps {total} cycles; IIe={args.iie}.')
        for phase,stride,h in ((0,2,16),(1,2,1),(3,2,16),(6,3,255),(6,255,255),(3,255,1),(3,8,8)):
            steps=a2test.bin_steps(binary,start=L['single'])+[L.poke('height',h),L.poke('stride',stride),
                   L.poke('_hgr_xs_x',28+phase),f'poke:{L["_hgr_xs_x"]+1:04X}:00',L.poke('_hgr_xs_y',0),
                   L.until('setup_start'),L.until('setup_done'),L.peek('_hgr_b_src',2)]
            result=a2test.run(disk,steps,iie=args.iie)
            expected_pointer=(0xBF93+phase*h*stride)&65535
            assert result.mem(L['_hgr_b_src'],2)==expected_pointer.to_bytes(2,'little'),(phase,stride,h)
            print(f'Phase {phase}, stride {stride}, height {h}: '
                  f'{result.cycles[1]-result.cycles[0]} setup cycles including JSR/RTS.')


if __name__=='__main__':
    main()
