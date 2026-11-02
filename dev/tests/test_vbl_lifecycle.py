#!/usr/bin/env python3
"""Real 65C02 VBL lifecycle with controlled MLI and mouse firmware replies."""
from pathlib import Path
import subprocess
import tempfile
from test_hgr import DEV, a2test


def check(work):
    src = work/'lifecycle.s'
    src.write_text('''
.setcpu "65C02"
.import _a2_vbl_init, _a2_vbl_irq_init, _a2_vbl_close, _a2_vbl_mode
.export _a2_frame_init, _mouse_timing_mode, _mouse_serve_irq, _mouse_slot
.export entry, result
.data
_mouse_slot: .byte 4
allocs: .byte 0
frees: .byte 0
mouse_error: .byte 0
alloc_error: .byte 0
result: .res 16,0
.code
entry:
    sei
    cld
    lda #$4c
    sta $bf00
    lda #<mli
    sta $bf01
    lda #>mli
    sta $bf02
    stz _a2_vbl_mode
    jsr _a2_vbl_irq_init
    sta result
    jsr _a2_vbl_irq_init
    sta result+1
    lda allocs
    sta result+2
    jsr _a2_vbl_close
    lda frees
    sta result+3
    lda _a2_vbl_mode
    sta result+4
    jsr _a2_vbl_irq_init
    jsr _a2_vbl_init
    sta result+5
    lda _a2_vbl_mode
    sta result+6
    lda frees
    sta result+7
    jsr _a2_vbl_close
    jsr _a2_vbl_close
    lda #1
    sta mouse_error
    jsr _a2_vbl_irq_init
    sta result+8
    lda _a2_vbl_mode
    sta result+9
    lda allocs
    sta result+10
    lda frees
    sta result+11
    stz mouse_error
    inc alloc_error
    jsr _a2_vbl_irq_init
    sta result+12
    lda _a2_vbl_mode
    sta result+13
    lda frees
    sta result+14
    sei
    inc result+15
    rts
_a2_frame_init:
    lda #1
    ldx #0
    rts
_mouse_timing_mode:
    lda mouse_error
    cmp #1
    rts
_mouse_serve_irq:
    clc
    rts
mli:
    tsx
    lda $0101,x
    sta fetch+1
    clc
    adc #3
    sta $0101,x
    lda $0102,x
    sta fetch+2
    adc #0
    sta $0102,x
    ldy #1
    jsr fetch
    cmp #$40
    bne release
    inc allocs
    lda alloc_error
    bne failed
    iny
    jsr fetch
    sta $50
    iny
    jsr fetch
    sta $51
    ldy #1
    lda #7
    sta ($50),y
    bra success
release:
    inc frees
success:
    lda #0
    clc
    rts
failed:
    sec
    rts
fetch:
    lda $ffff,y
    rts
''')
    cfg = work/'test.cfg'
    cfg.write_text('MEMORY { RAM: start=$6000,size=$3600,file=%O; }\n'
                   'SEGMENTS { CODE: load=RAM,type=ro; DATA: load=RAM,type=rw; BSS: load=RAM,type=bss; }\n')
    objects = []
    for index,path in enumerate((src,DEV/'lib/apple2c/apple2vbl.s')):
        obj = work/f'{index}.o'
        subprocess.run(['ca65','-o',str(obj),str(path)],check=True)
        objects.append(str(obj))
    binary = work/'test.bin'
    subprocess.run(['ld65','-C',str(cfg),'-Ln',str(work/'test.lbl'),'-o',str(binary),*objects],check=True)
    labels = a2test.labels(work/'test.lbl')
    disk = work/'blank.dsk'; disk.write_bytes(bytes(143360))
    result = a2test.run(disk,[f'load:{binary}@6000', f'call:{labels["entry"]:04X}:5',labels.peek('result',16)],iie=True)
    actual = result.mem(labels['result'],16)
    expected = bytes([2,2,1,1,0,1,1,2,0,0,3,3,0,0,3,1])
    assert actual == expected, ('VBL allocation/release lifecycle', list(actual), list(expected))
    print('VBL lifecycle: repeated init/close, IRQ-to-poll transition, firmware/MLI failures OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='vbl-lifecycle-') as tmp:
        check(Path(tmp))
