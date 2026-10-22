#!/usr/bin/env python3
"""ASM exit must restore main-bank DOS state after extended video modes."""
from pathlib import Path
import tempfile
from test_asm_boundaries import a2test, fixture


def check(work, iie, saved, shared=False):
    source = '''.include "apple2.inc"
.code
entry:
    lda SOFTEV
    sta $1000
    lda SOFTEV+1
    sta $1001
    lda SOFTEV+2
    sta $1002
    lda #$5A
    sta $60
''' + ('    jsr apple2_zp_save\n    lda #$A5\n    sta $60\n' if saved else '') + '''
    lda $FBB3
    cmp #$06
    bne @classic
    lda #0
    sta STORE80ON
    sta COL80ON
    bit DHIRES_ON
    bit HIRES
    bit HISCR
    bit TXTCLR
    bit MIXSET
    sta $C005                 ; auxiliary writes, main code and stack
@classic:
    jmp apple2_exit
''' + ('''    jsr hgr_init               ; references native_video
.include "hgr.asm"
EXIT_USE_NATIVE_VIDEO = 1
''' if shared else '') + '''.include "exit.asm"
'''
    result = fixture(work, f'exit{int(iie)}{int(saved)}{int(shared)}', source,
                     lambda labels: ['until:03D0:3000', 'peek:C013:2',
                                     'peek:C018:8', 'peek:0060:1',
                                     'peek:1000:3', 'peek:03F2:3'], iie=iie)
    banks, flags, zp, original, vector = result.dumps
    if iie:
        assert not any(v & 128 for v in banks), ('exit left auxiliary banking active', banks.hex())
        assert not any(flags[i] & 128 for i in (0,3,4,5,7)), ('exit video mode',flags.hex())
        assert flags[2] & 128, 'exit did not select TEXT'
    assert zp == b'\x5A', ('DOS zero page not restored in main bank',zp.hex())
    assert vector == original, ('RESET vector not restored in main bank',vector.hex(),original.hex())
    print(f'ASM exit: {"IIe" if iie else "II+"}, snapshot={saved}, '
          f'{"hgr.asm native_video, " if shared else ""}banking/video and DOS state OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='exit-modes-') as tmp:
        for iie in (True, False):
            if iie and not a2test.have_a2shot('ASM exit on the IIe'):
                continue
            for saved in (True, False):
                check(Path(tmp), iie, saved)
            check(Path(tmp), iie, True, shared=True)
