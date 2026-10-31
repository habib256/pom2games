#!/usr/bin/env python3
"""lib/apple2/rwts.asm rwts_sectors and rwts_write_tslist in a2run, on a
scratch DOS 3.3 disk: a save file's data sectors (tables filled by
dev/tools/dos33patch.py --sectors) written from three pages then read back;
rwts_write_tslist bounded by rwts_count (two pages of a four-sector file:
the rest unchanged, read back through rwts_read_tslist), and asked for more
pages than the file has (rwts_count = pages left over)."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402
import dos33  # noqa: E402
import dos33patch  # noqa: E402

PROGRAM = '''
.include "apple2.inc"
RWTS_SEC_T = sec_t
RWTS_SEC_S = sec_s
.code
        LDX     #15
        LDA     #0
@r:     STA     res,X
        DEX
        BPL     @r
        LDA     #$1E                    ; 1. pattern in $1E00-$20FF
        LDX     #$C3
        JSR     fill3
        LDA     #$1E
        STA     rwts_page
        LDA     #2
        LDX     #3
        JSR     rwts_sectors            ; write SAVE's three data sectors
        ROL     res+0
        LDA     rwts_page
        STA     res+1
        LDA     #$1E                    ; 2. clear, read them back
        LDX     #0
        JSR     clear3
        LDA     #$1E
        STA     rwts_page
        LDA     #1
        LDX     #3
        JSR     rwts_sectors
        ROL     res+2
        JSR     find2                   ; 3. SAVE2: two of its four sectors
        LDA     #$40
        LDX     #$5A
        JSR     fill3
        LDA     #$40
        STA     rwts_page
        LDA     #2
        STA     rwts_count
        JSR     rwts_write_tslist
        ROL     res+3
        LDA     rwts_count
        STA     res+4
        LDA     rwts_page
        STA     res+5
        JSR     find2                   ; 4. read SAVE2 whole into $5000..
        LDA     #$50
        STA     rwts_page
        JSR     rwts_read_tslist
        ROL     res+6
        LDA     rwts_count
        STA     res+7
        JSR     find2                   ; 5. six pages asked, four written
        LDA     #$60
        STA     rwts_page
        LDA     #6
        STA     rwts_count
        JSR     rwts_write_tslist
        ROL     res+8
        LDA     rwts_count
        STA     res+9
        LDA     rwts_page
        STA     res+10
done:   JMP     done

find2:  LDA     #$10
        STA     rwts_page
        STA     rwts_tsl
        LDA     #<n2
        LDY     #>n2
        JSR     rwts_find_file
        ROL     res+11
        RTS
; three pages from page A: byte i of page k = i EOR (X + k * $35)
fill3:  STA     @st+2
        STX     tmp
        LDY     #3
@pg:    LDX     #0
@by:    TXA
        EOR     tmp
@st:    STA     $FF00,X
        INX
        BNE     @by
        INC     @st+2
        LDA     tmp
        CLC
        ADC     #$35
        STA     tmp
        DEY
        BNE     @pg
        RTS
clear3: STA     @c+2
        LDY     #3
@cp:    TXA
@c:     STA     $FF00,X
        INX
        BNE     @c
        INC     @c+2
        DEY
        BNE     @cp
        RTS
n2:     .byte   "SAVE2", 0
sec_t:  .byte   0, 0, 0
sec_s:  .byte   0, 0, 0
.bss
tmp:    .res    1
res:    .res    16
.code
.include "rwts.asm"
.export done, res, sec_t, sec_s
'''


def pattern(seed):
    return bytes(i ^ ((seed + 0x35 * k) & 255) for k in range(3) for i in range(256))


def main():
    save = bytes((i * 11 + 1) & 255 for i in range(3 * 256 - 4))
    save2 = bytes((i * 5 + 9) & 255 for i in range(4 * 256 - 4))
    with tempfile.TemporaryDirectory(prefix='rwts-sectors-') as tmp:
        work = Path(tmp)
        (work / 't.s').write_text(PROGRAM)
        subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(work / 't.o'), str(work / 't.s')],
                       check=True)
        subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 't.lbl'),
                        '-o', str(work / 't.bin'), str(work / 't.o')], check=True)
        L = a2test.labels(work / 't.lbl')
        (work / 'SAVE').write_bytes(save)
        (work / 'SAVE2').write_bytes(save2)
        disk = a2test.build_disk(work, 'RWTSSEC', work / 't.bin',
                                 extra=[f'SAVE={work / "SAVE"}@0x4000', f'SAVE2={work / "SAVE2"}@0x4000'])
        image = bytearray(disk.read_bytes())
        dos33patch.patch(image, 'RWTSSEC', dict(L), sectors=[('sec_t', 'sec_s', 'SAVE')])
        disk.write_bytes(image)
        r = a2test.run(disk, ['wait:200', L.until('done', 4000), L.peek('res', 16),
                              'peek:1E00:768', 'peek:5000:1024', f'dsk:{work / "after.dsk"}'])
        after = (work / 'after.dsk').read_bytes()
        on_disk = b''.join(after[o:o + 256] for o in dos33.file_sectors(after, 'SAVE'))
        res = r.mem(L['res'], 16)
        p1, p2 = pattern(0xC3), pattern(0x5A)
        raw2 = bytes([0, 0x40, len(save2) & 255, len(save2) >> 8]) + save2
        assert res[0] == 0 and res[1] == 0x21, f'rwts_sectors write: C {res[0]}, next page {res[1]:02X}'
        assert res[2] == 0 and r.mem(0x1E00, 768) == p1, f'rwts_sectors read back: C {res[2]}'
        assert on_disk == p1, 'rwts_sectors did not write SAVE\'s own data sectors'
        assert res[11] == 0, 'SAVE2 not found'
        assert res[3] == 0 and res[4] == 0 and res[5] == 0x42, \
            f'rwts_write_tslist bounded: C {res[3]} left {res[4]} next page {res[5]:02X}'
        assert res[6] == 0 and res[7] == 4, f'read back SAVE2: C {res[6]} pages {res[7]}'
        assert r.mem(0x5000, 1024) == p2[:512] + raw2[512:], 'SAVE2: two pages written, two kept'
        assert res[8] == 0 and res[9] == 2 and res[10] == 0x64, \
            f'rwts_write_tslist past the end: C {res[8]} left {res[9]} next page {res[10]:02X}'
    print('rwts_sectors: three save sectors written and read back (dos33patch --sectors tables); '
          'rwts_write_tslist bounded by rwts_count and past the file end.')


if __name__ == '__main__':
    main()
