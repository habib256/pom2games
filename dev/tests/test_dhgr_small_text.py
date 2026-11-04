#!/usr/bin/env python3
"""Compact DHGR text: every input byte/phase, IRQ masks and relocated fonts."""
from pathlib import Path
import re
import tempfile

from test_hgr import DEV, run, a2test
from test_dhgr import color_pixel, offset


def glyphs():
    # The source bitmap is the oracle; no renderer masks or ink tables reused.
    source = (DEV / 'lib/hgrc/dhgr_small_font.inc').read_text()
    return [bytes(int(v, 16) for v in re.findall(r'\$([0-9A-F]{2})', line.split(';')[0]))
            for line in source.splitlines() if '.byte' in line]


def draw(banks, font, code, x, y):
    if x > 135 or y > 187:
        return
    if ord('a') <= code <= ord('z'):
        code -= 32
    if not 32 <= code < 96:
        code = ord('?')
    for dy, row in enumerate(font[code - 32][:5]):
        for dx in range(5):
            color_pixel(banks, x + dx, y + dy, 15 if row & (1 << dx) else 0)
        # DHGR text normalizes bit 7 on every byte touched by the cell.
        for byte in range(x * 4 // 7, (x * 4 + 19) // 7 + 1):
            banks[1 - byte % 2][offset(y + dy) + byte // 2] &= 127


def build(work, base):
    fixture = work / 'fixture.s'
    fixture.write_text('''
.import _dhgr_capabilities, _dhgr_small_char, _dhgr_small_string
.export _dhgr_base, _dhgr_display, _dhgr_small_x, _dhgr_small_y
.exportzp ptr1, ptr2, ptr3, ptr4
.export entry, phase, irq_mask, errors
.zeropage
ptr1: .res 2
ptr2: .res 2
ptr3: .res 2
ptr4: .res 2
.data
_dhgr_base: .byte $20
_dhgr_display: .byte 1
_dhgr_small_x: .byte 0
_dhgr_small_y: .byte 0
phase: .byte 0
irq_mask: .byte 0
errors: .byte 0
character: .byte 0
.rodata
text: .byte "aZ?",0
.code
entry:
    php
    cld
    jsr _dhgr_capabilities
    lda #0
    sta errors
    sta character
    sta _dhgr_small_y
    lda phase
    sta _dhgr_small_x
next:
    ldx irq_mask
    beq enabled
    sei
    jmp render
enabled:
    cli
render:
    lda character
    jsr _dhgr_small_char
    jsr check
    inc character
    beq edges
    lda character
    and #15
    beq next_row
    lda _dhgr_small_x
    clc
    adc #7
    sta _dhgr_small_x
    jmp next
next_row:
    lda phase
    sta _dhgr_small_x
    lda _dhgr_small_y
    clc
    adc #11
    sta _dhgr_small_y
    jmp next
edges:
    lda #130
    sta _dhgr_small_x
    lda #187
    sta _dhgr_small_y
    lda #<text
    ldx #>text
    jsr _dhgr_small_string
    jsr check
    ; The first two cells fit; the third must stop at x=140.
    lda _dhgr_small_x
    cmp #140
    beq :+
    inc errors
:
''' + ''.join(f'''
    lda #{x}
    sta _dhgr_small_x
    lda #{y}
    sta _dhgr_small_y
    lda #'W'
    jsr _dhgr_small_char
    jsr check
''' for x, y in ((136, 175), (139, 175), (255, 175), (0, 188), (0, 191), (0, 255))) + '''
    plp
    rts
check:
    php
    pla
    and #4
    cmp irq_mask
    bne failed
    lda $c013
    ora $c014
    bmi failed
    rts
failed:
    lda #1
    sta errors
    rts
''')
    cfg = work / 'test.cfg'
    cfg.write_text('''MEMORY {
 ZP: start=$80, size=$80, type=rw;
 RAM: start=$6000, size=$2000, file=%O;
 BSS: start=$1000, size=$1000, type=rw;
}
SEGMENTS {
 ZEROPAGE: load=ZP, type=zp;
 CODE: load=RAM, type=ro;
 RODATA: load=RAM, type=ro;
 DATA: load=RAM, type=rw;
 BSS: load=BSS, type=bss;
}
''')
    objects = []
    for source in (fixture, *(DEV / 'lib/hgrc' / name for name in
                             ('dhgr_asm.s', 'dhgr_small_asm.s', 'dhgr_small_string.s'))):
        obj = work / (source.stem + '.o')
        defines = [] if base is None else ['-D', 'DHGR_SMALL_FONT_EXTERNAL=1',
                                           '-D', f'DHGR_SMALL_FONT_BASE={base}']
        run(['ca65', *defines, '-I', DEV / 'lib/hgrc', '-I', DEV / 'lib/apple2',
             '-o', obj, source])
        objects.append(obj)
    binary = work / 'test.bin'
    run(['ld65', '-C', cfg, '-Ln', work / 'test.lbl', '-o', binary, *objects])
    labels = a2test.labels(work / 'test.lbl')
    disk = a2test.build_disk(work, 'TEST', binary)
    steps = [labels.until('entry')]
    if base is not None:
        font = work / 'font.bin'
        run(['python3', DEV / 'tools/build_dhgr_font.py', '--out', font, '--base', hex(base)])
        steps.append(f'load:{font}@{base:04X}')
    return disk, labels, steps


def main():
    font = glyphs()
    # Distinct nonuniform bytes also check untouched bits, holes and bit 7.
    initial = [bytes((i * 37 + bank * 53) & 255 for i in range(16384)) for bank in (0, 1)]
    with tempfile.TemporaryDirectory(prefix='dhgr-small-') as directory:
        work = Path(directory)
        for bank in (0, 1):
            (work / f'bank{bank}.bin').write_bytes(initial[bank])
        for base in (None, 0x800, 0x8d3):
            disk, labels, prefix = build(work, base)
            for page in (0, 1):
                for irq in (0, 4):
                    steps = list(prefix)
                    for phase in range(7):
                        steps += [f'load:{work}/bank0.bin@2000', 'poke:C005:0',
                                  f'load:{work}/bank1.bin@2000', 'poke:C004:0',
                                  labels.poke('_dhgr_base', 0x20 + page * 0x20),
                                  labels.poke('phase', phase), labels.poke('irq_mask', irq),
                                  f'call:{labels["entry"]:04X}:100', labels.peek('errors', 1),
                                  'peek:2000:16384', 'poke:C003:0', 'peek:2000:16384',
                                  'poke:C002:0']
                    result = a2test.run(disk, steps, iie=True)
                    for phase in range(7):
                        status, main, aux = result.dumps[phase*3:phase*3+3]
                        assert status == b'\0', (base, page, irq, phase, 'IRQ/bank/edge state')
                        banks = [bytearray(data[page*8192:(page+1)*8192]) for data in initial]
                        for code in range(256):
                            draw(banks, font, code, phase + 7 * (code % 16), 11 * (code // 16))
                        draw(banks, font, ord('a'), 130, 187)
                        draw(banks, font, ord('Z'), 135, 187)
                        for bank, actual in enumerate((main, aux)):
                            expected = bytearray(initial[bank])
                            expected[page*8192:(page+1)*8192] = banks[bank]
                            if actual != expected:
                                index = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
                                raise AssertionError((base, page, irq, phase, bank, hex(0x2000+index),
                                                      actual[index], expected[index]))
    print('Compact DHGR text: 256 inputs × 7 phases × 2 pages × 2 IRQ masks;')
    print('linked/relocated/unaligned fonts, clipping, neighbours, holes and banks OK.')


if __name__ == '__main__':
    main()
