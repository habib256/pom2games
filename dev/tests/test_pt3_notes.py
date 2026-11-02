#!/usr/bin/env python3
"""PT3 effects checked against scalar models of Vortex Tracker trfuncs.pas.
Reference: https://github.com/oisee/vti/blob/master/trfuncs.pas
Ornament sums intentionally wrap to a byte before the signed clamp.
"""
from pathlib import Path
import subprocess
import tempfile
from test_hgr import DEV, a2test


def execute(work, source, size, batches=1):
    src = work/'notes.s'; src.write_text(source)
    cfg = work/'notes.cfg'
    cfg.write_text('MEMORY { RAM: start=$6000,size=$3600,file=%O; }\n'
                   'SEGMENTS { CODE: load=RAM,type=ro; }\n')
    subprocess.run(['ca65','-I',str(DEV/'lib/apple2/pt3'),'-o',str(work/'notes.o'),str(src)],check=True)
    binary = work/'notes.bin'
    subprocess.run(['ld65','-C',str(cfg),'-Ln',str(work/'notes.lbl'),'-o',str(binary),str(work/'notes.o')],check=True)
    labels = a2test.labels(work/'notes.lbl')
    steps = a2test.bin_steps(binary)
    for _ in range(batches):
        if batches > 1: steps.append(labels.until('batch_begin'))
        steps += [labels.until('done'),f'peek:2000:{size}']
    result = a2test.run(None,steps)
    return result.data


def check_amplitude(work):
    cases = [(control, slide, base) for control in (0, 0x80, 0xC0)
             for slide in range(-15, 16) for base in range(16)]
    source = '''PT3_ZP = $60
PT3_LOC = $4000
.code
    jmp entry
.include "pt3.s"
entry:
    ldx #0
    txa
clear:
    sta note_a,x
    inx
    cpx #NOTE_STRUCT_SIZE
    bne clear
    ldx #15
volume:
    txa
    sta VolumeTable,x
    dex
    bpl volume
    lda #1
    sta note_a+NOTE_ENABLED
    sta note_a+NOTE_SAMPLE_LENGTH
    sta note_a+NOTE_ORNAMENT_LENGTH
    lda #$15
    sta note_a+NOTE_SAMPLE_POINTER_H
    sta note_a+NOTE_ORNAMENT_POINTER_H
    lda #$10
    sta note_a+NOTE_ORNAMENT_POINTER_L
    lda #0
    sta $1502
    sta $1503
    sta $1510
    sta $52
    lda #$20
    sta $53
    lda #<inputs
    sta $50
    lda #>inputs
    sta $51
next:
    ldy #0
    lda ($50),y
    sta $1500
    iny
    lda ($50),y
    sta note_a+NOTE_AMPLITUDE_SLIDING
    iny
    lda ($50),y
    sta $1501
    ldx #0
    jsr calculate_note
    ldy #0
    lda note_a+NOTE_AMPLITUDE_SLIDING
    sta ($52),y
    iny
    lda note_a+NOTE_AMPLITUDE
    sta ($52),y
    clc
    lda $52
    adc #2
    sta $52
    bcc :+
    inc $53
:   clc
    lda $50
    adc #3
    sta $50
    bcc :+
    inc $51
:   lda $50
    cmp #<inputs_end
    bne next
    lda $51
    cmp #>inputs_end
    bne next
done: jmp done
inputs:
'''
    source += ''.join(f'    .byte {c},{s & 255},{b}\n' for c,s,b in cases)
    source += 'inputs_end:\n.export done\n'
    data = execute(work, source, len(cases)*2)
    errors = []
    for i,(control,slide,base) in enumerate(cases):
        delta = 1 if control == 0xC0 else -1 if control == 0x80 else 0
        expected_slide = min(15,max(-15,slide+delta))
        expected = bytes((expected_slide & 255, min(15,max(0,base+expected_slide))))
        if data[2*i:2*i+2] != expected:
            errors.append(((control,slide,base),data[2*i:2*i+2].hex(),expected.hex()))
    assert not errors, (len(errors),errors[:20])
    print(f'PT3 amplitude: {len(cases)} combinations of base, slide and direction OK.')


def check_vibrato(work):
    source = '''PT3_ZP = $60
PT3_LOC = $4000
.code
    jmp entry
.include "pt3.s"
entry:
    lda #1
    sta note_a+NOTE_ENABLED
    lda #3
    sta note_a+NOTE_ONOFF
    sta note_a+NOTE_ONOFF_DELAY
    lda #2
    sta note_a+NOTE_OFFON_DELAY
    lda #0
    sta $1000
next:
    ldx #0
    jsr handle_onoff
    ldx $1000
    lda note_a+NOTE_ENABLED
    sta $2000,x
    inx
    lda note_a+NOTE_ONOFF
    sta $2000,x
    inx
    stx $1000
    cpx #40
    bne next
done: jmp done
.export done
'''
    data = execute(work,source,40)
    enabled, counter = 1, 3
    expected = bytearray()
    for _ in range(20):
        counter -= 1
        if counter == 0:
            enabled ^= 1
            counter = 3 if enabled else 2
        expected.extend((enabled,counter))
    assert data == expected, ('vibrato countdown',data.hex(),expected.hex())
    print('PT3 vibrato: 20 ticks, alternating three enabled/two disabled ticks OK.')


def check_ornaments(work):
    source = '''PT3_ZP = $60
PT3_LOC = $4000
.code
    jmp entry
.include "pt3.s"
entry:
    ldx #0
    txa
clear:
    sta note_a,x
    inx
    cpx #NOTE_STRUCT_SIZE
    bne clear
    ldx #95
note_table:
    txa
    sta NoteTable_low,x
    lda #0
    sta NoteTable_high,x
    dex
    bpl note_table
    lda #1
    sta note_a+NOTE_ENABLED
    sta note_a+NOTE_SAMPLE_LENGTH
    sta note_a+NOTE_ORNAMENT_LENGTH
    lda #$15
    sta note_a+NOTE_SAMPLE_POINTER_H
    sta note_a+NOTE_ORNAMENT_POINTER_H
    lda #$10
    sta note_a+NOTE_ORNAMENT_POINTER_L
    lda #0
    sta $1500
    sta $1501
    sta $1502
    sta $1503
    sta $1510
batch_begin:
    ldx #0
    jsr calculate_note
    ldx $1510
    lda note_a+NOTE_TONE_L
    sta $2000,x
    lda note_a+NOTE_TONE_H
    sta $2100,x
    inc $1510
    bne batch_begin_loop
    jmp done
batch_begin_loop:
    jmp batch_begin
done:
    inc note_a+NOTE_NOTE
    lda note_a+NOTE_NOTE
    cmp #96
    bne batch_begin
halt: jmp halt
.export done, batch_begin
'''
    data = execute(work,source,512,96)
    # Vortex Tracker intentionally wraps the sum to a byte, then tests its sign.
    expected = b''.join(bytes(0 if (n+o) & 128 else min(95,(n+o) & 255) for o in range(256)) + bytes(256)
                        for n in range(96))
    assert data == expected, ('ornament clamp', next((i, a, b) for i,(a,b) in enumerate(zip(data,expected)) if a != b))
    print("PT3 ornaments: all 96 notes × 256 offsets preserve the tracker's byte-wrap/clamp semantics.")


def check_envelope_sliding(work):
    source = '''PT3_ZP = $60
PT3_LOC = $4000
.code
    jmp entry
.include "pt3.s"
entry:
    lda #0
    sta $1000
    sta $1001
batch_begin:
    lda $1001
    and #31
    asl
    sta sample_b0_smc+1
    lda $1001
    and #32
    ora #$80
    sta sample_b1_smc+1
next:
    lda #0
    sta pt3_envelope_add_smc+1
    lda $1000
    sta note_a+NOTE_ENVELOPE_SLIDING
    lda sample_b0_smc+1
    lsr
    tay
    ldx #0
    jsr envelope_slide
    ldx $1000
    lda pt3_envelope_add_smc+1
    sta $2000,x
    lda note_a+NOTE_ENVELOPE_SLIDING
    sta $2100,x
    inc $1000
    bne next
done:
    inc $1001
    lda $1001
    cmp #64
    bne batch_begin
halt: jmp halt
.export batch_begin, done
'''
    data = execute(work,source,512,64)
    expected = bytearray()
    for control in range(64):
        delta = control & 31
        if delta >= 16: delta -= 32
        sums = bytes((slide+delta) & 255 for slide in range(256))
        expected.extend(sums)
        expected.extend(sums if control & 32 else bytes(range(256)))
    assert data == expected, ('sample envelope slide',next((i,a,b) for i,(a,b) in enumerate(zip(data,expected)) if a != b))
    print('PT3 envelope slides: all 16384 signed deltas, accumulators and accumulation flags OK.')


def check_signed_envelope_add(work):
    source = '''PT3_ZP = $60
PT3_LOC = $4000
.code
    jmp entry
.include "pt3.s"
entry:
    lda #0
    sta $1000
    sta pt3_envelope_period_l_smc+1
    sta pt3_envelope_slide_l_smc+1
    sta pt3_envelope_slide_h_smc+1
    sta pt3_envelope_delay_smc+1
    lda #$12
    sta pt3_envelope_period_h_smc+1
next:
    lda $1000
    sta pt3_envelope_add_smc+1
    jsr pt3_emit_registers
    ldx $1000
    lda AY_REGISTERS+11
    sta $2000,x
    lda AY_REGISTERS+12
    sta $2100,x
    inc $1000
    bne next
done: jmp done
.export done
'''
    data = execute(work,source,512)
    values = [0x1200+(n if n < 128 else n-256) for n in range(256)]
    expected = bytes(n & 255 for n in values)+bytes(n >> 8 for n in values)
    assert data == expected, ('signed envelope add',next((i,a,b) for i,(a,b) in enumerate(zip(data,expected)) if a != b))
    print('PT3 envelope registers: all 256 signed sample additions OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='pt3-notes-') as tmp:
        check_amplitude(Path(tmp))
        check_vibrato(Path(tmp))
        check_ornaments(Path(tmp))
        check_envelope_sliding(Path(tmp))
        check_signed_envelope_add(Path(tmp))
