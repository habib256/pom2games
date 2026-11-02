#!/usr/bin/env python3
"""Execute PT3 register conversion: all noise and 16-bit envelope periods."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from test_hgr import DEV, a2test


def check(work, conversion):
    define = '' if conversion is None else f'PT3_FREQ_CONVERSION = {conversion}\n'
    source = define + '''PT3_ZP = $60
PT3_LOC = $4000
.code
    jmp entry
.include "pt3.s"
entry:
    lda #0
    sta $1000
    sta $1001
    sta pt3_noise_add_smc+1
    sta pt3_envelope_period_l_smc+1
    sta pt3_envelope_period_h_smc+1
    sta pt3_envelope_add_smc+1
    sta pt3_envelope_slide_l_smc+1
    sta pt3_envelope_slide_h_smc+1
    sta pt3_envelope_delay_smc+1
noise:
    lda $1000
    sta pt3_noise_period_smc+1
    clc
    jsr pt3_noise_period_smc
    ldx $1000
    lda AY_REGISTERS+6
    sta $1400,x
    inc $1000
    lda $1000
    cmp #32
    bne noise
batch_begin:
    lda #0
    sta $1000
    sta $50
    lda #$20
    sta $51
envelope:
    lda $1000
    sta pt3_envelope_period_l_smc+1
    sta note_a+NOTE_TONE_L
    sta note_b+NOTE_TONE_L
    sta note_c+NOTE_TONE_L
    lda $1001
    sta pt3_envelope_period_h_smc+1
    and #15
    sta note_a+NOTE_TONE_H
    sta note_b+NOTE_TONE_H
    sta note_c+NOTE_TONE_H
    clc
    jsr pt3_emit_registers
    ldy #0
    ldx #0
copy_tones:
    lda AY_REGISTERS,x
    sta ($50),y
    iny
    inx
    cpx #6
    bne copy_tones
    lda AY_REGISTERS+11
    sta ($50),y
    iny
    lda AY_REGISTERS+12
    sta ($50),y
    clc
    lda $50
    adc #8
    sta $50
    bcc :+
    inc $51
:   inc $1000
    bne envelope
batch_end:
    inc $1001
    bne batch_begin
done: jmp done
.export batch_begin, batch_end, done
'''
    src = work/'pt3_test.s'; src.write_text(source)
    cfg = work/'pt3.cfg'
    cfg.write_text('MEMORY { RAM: start=$6000,size=$3600,file=%O; }\n'
                   'SEGMENTS { CODE: load=RAM,type=ro; }\n')
    subprocess.run(['ca65', '-I', str(DEV/'lib/apple2/pt3'), '-o', str(work/'pt3.o'), str(src)], check=True)
    binary = work/'pt3.bin'
    subprocess.run(['ld65', '-C', str(cfg), '-Ln', str(work/'pt3.lbl'), '-o', str(binary), str(work/'pt3.o')], check=True)
    labels = a2test.labels(work/'pt3.lbl')
    steps = a2test.bin_steps(binary) + [labels.until('batch_begin'), 'peek:1400:32']
    for index in range(256):
        if index: steps.append(labels.until('batch_begin'))
        steps += [labels.until('batch_end'), 'peek:2000:2048']
    result = a2test.run(None, steps)
    data = result.data
    scale = (lambda n: n*9//16) if conversion else (lambda n: n)
    assert data[:32] == bytes(scale(n) for n in range(32)), ('noise conversion', conversion, data[:32])
    expected = b''.join(scale(n & 4095).to_bytes(2, 'little')*3 +
                        scale(n).to_bytes(2, 'little') for n in range(65536))
    assert data[32:] == expected, ('16-bit envelope conversion', conversion,
                                 next(n for n in range(65536) if data[32+n*8:40+n*8] != expected[n*8:n*8+8]))
    ticks = result.cycles
    cycles = sum(ticks[i+1]-ticks[i] for i in range(0,512,2))
    print(f'PT3 conversion={conversion}: all noise/tone/envelope periods OK (65536 frames); '
          f'{binary.stat().st_size} bytes, {cycles} envelope-fixture cycles.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conversion', type=int, choices=(0,1))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='pt3-registers-') as tmp:
        check(Path(tmp), args.conversion)
