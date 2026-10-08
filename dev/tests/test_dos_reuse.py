#!/usr/bin/env python3
"""A completed DOS command remains intact and accepts subsequent appends."""
import tempfile
import subprocess
from pathlib import Path
from test_asm_boundaries import fixture, ROOT


def check(work, partial=False):
    source = '''.include "apple2.inc"
.code
entry:
    ldx #0
@save:
    lda $00,x
    sta apple2_zp_buf,x
    inx
    bne @save
    ldx #$50
    lda #$A5
@pattern:
    sta $00,x
    inx
    bne @pattern
    jsr dos_cmd_new
    lda #<command
    ldy #>command
    jsr dos_cmd_add
    jsr dos_cmd_run
first_done:
    jsr dos_cmd_run
second_done:
    lda #<suffix
    ldy #>suffix
    jsr dos_cmd_add
    lda #$FF
    jsr dos_cmd_hex
append_done:
    jmp append_done
command: .byte "CATALOG",0
suffix: .byte ",S",0
.bss
apple2_zp_buf: .res 256
.code
.include "dos.asm"
'''
    if partial:
        source = 'DOS_ZP_START=$50\nDOS_ZP_LEN=$B0\n' + source
    stages = ('first_done', 'second_done', 'append_done')
    result = fixture(work, 'dosreuse', source, lambda labels: [step
        for name in stages for step in (labels.until(name), labels.peek('dos_cmd_ix'),
                                        labels.peek('dos_cmd_buf', 12), 'peek:0050:176')])
    for index, (length, command) in enumerate(((7,b'CATALOG\0'), (7,b'CATALOG\0'), (11,b'CATALOG,SFF\0'))):
        assert result.dumps[index*3] == bytes([length]), (stages[index], 'command length changed during run', result.dumps[index*3])
        assert result.dumps[index*3+1][:len(command)] == command, (stages[index], 'append overwrote existing command')
        assert result.dumps[index*3+2] == bytes([0xA5])*176, 'DOS corrupted caller ZP'
    print('DOS command reuse: repeated real CATALOG, append string/hex, caller ZP preserved.')


def configurations(work):
    for start, length, valid in ((0,256,True), (80,176,True), (255,1,True),
                                  (0,0,False), (250,10,False), (256,1,False),
                                  (-1,1,False), (0,257,False)):
        source = work / 'range.s'
        source.write_text(f'''.include "apple2.inc"
DOS_ZP_START={start}
DOS_ZP_LEN={length}
.bss
apple2_zp_buf: .res 256
.include "dos.asm"
''')
        result = subprocess.run(['ca65', '-I', str(ROOT/'dev/lib/apple2'),
                                 '-o', str(work/'range.o'), str(source)],
                                capture_output=True, text=True)
        assert (result.returncode == 0) == valid, (start,length,result.stderr)
    print('DOS zero-page configuration: valid ranges accepted, empty/out-of-page ranges rejected.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='dos-reuse-') as tmp:
        check(Path(tmp))
        check(Path(tmp), partial=True)
        configurations(Path(tmp))
