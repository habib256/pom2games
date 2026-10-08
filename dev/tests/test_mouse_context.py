#!/usr/bin/env python3
"""Standalone workspace preservation without the optional DOS client."""
import sys
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test


def main():
    with tempfile.TemporaryDirectory(prefix='mouse-context-') as tmp:
        work=Path(tmp)
        src=work/'context.s'
        src.write_text('''
.code
entry:
    sei
    ldx #0
@zp:
    txa
    eor #$55
    sta $00,x
    inx
    bne @zp
    lda #0
    sta mouse_context_native_mouse
    ldx #7
@holes:
.repeat 8, row
    txa
    clc
    adc #(row*8)
    sta $0478+row*$80,x
.endrepeat
    dex
    bpl @holes
    jsr mouse_context_capture_holes
    jsr mouse_context_save_workspace
    ldx #0
    lda #$EE
@overwrite:
    sta $00,x
    inx
    bne @overwrite
    lda #$AA
    jsr fill_holes
    jsr mouse_context_restore_workspace
    lda #$BB
    jsr fill_holes
    jsr mouse_context_install_holes
finished:
    jmp finished
fill_holes:
    ldx #7
@loop:
.repeat 8, row
    sta $0478+row*$80,x
.endrepeat
    dex
    bpl @loop
    rts
.include "mouse_context.asm"
''')
        cfg=work/'context.cfg'
        cfg.write_text('''MEMORY { RAM: start=$6000, size=$3600, file=%O; }
SEGMENTS { CODE: load=RAM, type=ro; BSS: load=RAM, type=bss; }
''')
        obj=work/'context.o'; binary=work/'context.bin'; lbl=work/'context.lbl'
        subprocess.run(['ca65','-g','-I',str(ROOT/'dev/lib/mouse'),'-o',str(obj),str(src)],check=True)
        subprocess.run(['ld65','-C',str(cfg),'-Ln',str(lbl),'-o',str(binary),str(obj)],check=True)
        labels=a2test.labels(lbl)
        disk=a2test.build_disk(work,'CONTEXT',binary)
        result=a2test.run(disk,[labels.until('finished'),'peek:0000:256','peek:0478:904'])
        assert result.dumps[0] == bytes(x^0x55 for x in range(256)), 'caller ZP not restored'
        assert all(result.dumps[1][row*128:row*128+8] == bytes([0xAA])*8 for row in range(8)), 'firmware mailbox changes not retained'
        assert not any('dos_holes' in name for name in labels), 'DOS storage linked without opting in'
        print('Mouse context: standalone ZP restoration and mailbox shadow, no DOS client or ZP allocation')


if __name__ == '__main__':
    main()
