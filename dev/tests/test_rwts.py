#!/usr/bin/env python3
"""lib/apple2/rwts.asm in a2run: the IOB kept after the first call ($03E3
broken after it, as when a game takes the file manager's memory), catalog look-up (a longer name sharing the
prefix, one that goes on after a space, a comma-ended name, a missing file), whole files through their T/S
lists, a sector written then read back. Built twice: plain, and with
RWTS_KEEP_ZP + RWTS_RETRIES."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402
import dos33  # noqa: E402

PROGRAM = '''
.include "apple2.inc"
.code
        LDX     #10
        LDA     #0
@r:     STA     res,X                   ; BSS is not cleared
        DEX
        BPL     @r
        LDX     #15
@z:     TXA
        EOR     #$A5
        STA     $50,X                   ; zero-page sentinel
        DEX
        BPL     @z
        LDA     #$10                    ; 1. DATA1 -> $1100..
        STA     rwts_page
        LDA     #<n1
        LDY     #>n1
        JSR     rwts_find_file
        ROL     res+0
        LDA     #$10
        STA     rwts_tsl
        LDA     #$11
        STA     rwts_page
        JSR     rwts_read_tslist
        ROL     res+1
        LDA     rwts_count
        STA     res+2
        LDA     rwts_page
        STA     res+3
        LDX     #4                      ; the file manager's memory is gone:
@fm:    LDA     fake_iob,X              ; $03E3 now answers garbage
        STA     $03E3,X
        DEX
        BPL     @fm
        LDA     #$10                    ; 2. "DATA2,D1" -> $4000..
        STA     rwts_page
        LDA     #<n2
        LDY     #>n2
        JSR     rwts_find_file
        ROL     res+4
        LDA     #$10
        STA     rwts_tsl
        LDA     #$40
        STA     rwts_page
        JSR     rwts_read_tslist
        ROL     res+5
        LDA     rwts_count
        STA     res+6
        LDA     #$10                    ; 3. missing
        STA     rwts_page
        LDA     #<n3
        LDY     #>n3
        JSR     rwts_find_file
        ROL     res+7
        LDX     #0                      ; 4. DATA2's first sector: write, read back
@fill:  TXA
        EOR     #$5A
        STA     $1F00,X
        INX
        BNE     @fill
        LDA     $100C                   ; (DATA2's T/S list is still at $1000)
        STA     rwts_track
        LDA     $100D
        STA     rwts_sector
        LDA     #$1F
        STA     rwts_page
        JSR     rwts_write
        ROL     res+8
        LDA     #0
@clr:   STA     $1F00,X
        INX
        BNE     @clr
        JSR     rwts_read
        ROL     res+9
        LDX     #15
@zc:    TXA
        EOR     #$A5
        CMP     $50,X
        BEQ     @zok
        INC     res+10
@zok:   DEX
        BPL     @zc
done:   JMP     done
fake_iob: LDA   #0
        LDY     #0
        RTS
n1:     .byte   "DATA1", 0
n2:     .byte   "DATA2,D1"
n3:     .byte   "DATA3", 0
.bss
res:    .res    11
.code
.include "rwts.asm"
.export done, res
'''


def run(defines, files, work):
    (work / 't.s').write_text(defines + PROGRAM)
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(work / 't.o'), str(work / 't.s')],
                   check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 't.lbl'),
                    '-o', str(work / 't.bin'), str(work / 't.o')], check=True)
    L = a2test.labels(work / 't.lbl')
    extra = []
    for name, data in files:
        (work / name).write_bytes(data)
        extra.append(f'{name}={work / name}@0x4000')
    disk = a2test.build_disk(work, 'RWTSTEST', work / 't.bin', extra=extra)
    image = disk.read_bytes()
    r = a2test.run(disk, ['wait:200', L.until('done', 4000), L.peek('res', 11),
                          'peek:1100:768', 'peek:4000:5120', 'peek:1F00:256'])
    return image, r, L


def main():
    files = [('DATA10', bytes([0xEE]) * 300),                     # same prefix, listed first
             ('DATA1 X', bytes([0xDD]) * 300),                   # "DATA1" then a space: not DATA1
             ('DATA1', bytes((i * 7) & 0xFF for i in range(700))),   # 3 sectors with the header
             ('DATA2', bytes((i * 13 + 5) & 0xFF for i in range(20 * 256 - 4)))]
    for label, defines in (('plain', ''),
                           ('RWTS_KEEP_ZP', 'RWTS_KEEP_ZP = 1\nDOS_ZP_START = $50\nDOS_ZP_LEN = $10\n'
                                            'RWTS_RETRIES = 4\n')):
        with tempfile.TemporaryDirectory(prefix='rwts-') as tmp:
            image, r, L = run(defines, files, Path(tmp))
            res = r.mem(L['res'], 11)
            d1 = dos33.read_file(image, 'DATA1')
            d2 = dos33.read_file(image, 'DATA2')
            assert res[0] == 0 and res[1] == 0, f'{label}: DATA1 not found / not read {list(res)}'
            assert res[2] == 3 and res[3] == 0x14, f'{label}: DATA1 pages {res[2]}, next page {res[3]:02X}'
            assert r.mem(0x1100, 4 + len(d1)) == bytes([0, 0x40, len(d1) & 255, len(d1) >> 8]) + d1, f'{label}: DATA1 content (DATA10 or "DATA1 X" matched?)'
            assert res[4] == 0 and res[5] == 0 and res[6] == 20, f'{label}: DATA2 {list(res[4:7])}'
            assert r.mem(0x4000, 4 + len(d2))[4:] == d2, f'{label}: DATA2 content'
            assert res[7] == 1, f'{label}: DATA3 should be missing'
            assert res[8] == 0 and res[9] == 0, f'{label}: write/read error {list(res[8:10])}'
            assert r.mem(0x1F00, 256) == bytes(i ^ 0x5A for i in range(256)), f'{label}: read back'
            assert res[10] == 0, f'{label}: zero page $50-$5F changed'
    print('RWTS: catalog look-up (prefix, name + space + more, comma, missing), T/S-list file reads, '
          'write + read back; plain and RWTS_KEEP_ZP/RETRIES builds.')


if __name__ == '__main__':
    main()
