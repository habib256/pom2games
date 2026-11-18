#!/usr/bin/env python3
"""lib/apple2/fm.asm in a2run, on a real DOS 3.3 (48 KB, MAXFILES 3).

Main run, with $00-$FF full of garbage during the calls: a binary file
created (A = 6: new), written (BLOAD header + 300 bytes), closed; opened
again with another type (kept: binary), read back in two pieces (no byte
past the range), a seek past its last sector then a read (END OF DATA), a
seek + 2-byte rewrite in the middle; lock (DELETE and a write refused,
fm_type shows the lock), unlock, verify; a missing file with FM_MUST_EXIST; a text file
created, deleted, deleted again (not found); all three DOS buffers taken
(the 4th open: NO BUFFER), closed through their saved handles; fm_bsave
then fm_bload of a whole binary file (and of a missing one); then a DOS
BLOAD of the file. The disk saved after the run is read with dos33.py:
contents, nothing written past the range, every DOS buffer free again.
The zero page bytes the calls changed must be the ones fm.asm lists.

Other runs: a write-protected disk (open: error 4, the image untouched), a
full disk (error 9, close still answers and DOS's catalog stays sane),
and FM_KEEP_ZP ($20-$4F) + FM_SEI, where the zero page must not change."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402
import dos33  # noqa: E402

N = 300                                 # payload bytes
FM_ZP = {0x26, 0x27, *range(0x2A, 0x30), 0x35, *range(0x3C, 0x40), *range(0x42, 0x4A)}   # documented in fm.asm

PROGRAM = '''
.include "apple2.inc"
.macro  RES     ix                      ; res[ix] = A, res2[ix] = C
        STA     res+ix
        LDA     #0
        ROL     A
        STA     res2+ix
.endmacro
.macro  NAME    str
        LDA     #<(str)
        LDY     #>(str)
.endmacro
.macro  LEN     n
        LDA     #<(n)
        STA     fm_len
        LDA     #>(n)
        STA     fm_len+1
.endmacro
.code
        JSR     apple2_zp_save
        LDX     #0
@p:     TXA                             ; payload: X ^ $C3
        EOR     #$C3
        STA     data+4,X
        STA     data+4+256,X
        INX
        BNE     @p
        LDX     #39
        LDA     #$FF
@f:     STA     res,X                   ; BSS is not cleared
        STA     res2,X
        DEX
        BPL     @f
        LDA     #$EE
        STA     guard
        LDA     #<$4000                 ; BLOAD header: address, length
        STA     data
        LDA     #>$4000
        STA     data+1
        LDA     #<{N}
        STA     data+2
        LDA     #>{N}
        STA     data+3
        LDX     #0
@g:     TXA                             ; zero page garbage
        EOR     #ZPX
        STA     $00,X
        STA     zp_before,X
        INX
        BNE     @g
        ; 1. create + write + close
        NAME    n_save
        LDX     #FM_BINARY
        JSR     fm_open
        RES     0
.if MODE = 1
        BCS     done
.endif
        LEN     {N}+4
        NAME    data
        JSR     fm_write
        RES     1
        JSR     fm_close
        RES     2
.if MODE = 0
        ; 2. open again (create allowed, another type), read 4 then the rest
        NAME    n_save
        LDX     #FM_TEXT
        JSR     fm_open
        RES     3
        LDA     fm_type
        STA     res+4
        LEN     4
        NAME    back
        JSR     fm_read
        RES     5
        LEN     {N}
        NAME    back+4
        JSR     fm_read
        RES     6
        NAME    600                     ; past the file's 2 sectors
        JSR     fm_seek
        RES     7
        LEN     1
        NAME    tail
        JSR     fm_read
        RES     8
        NAME    4+10                    ; rewrite payload bytes 10-11
        JSR     fm_seek
        RES     9
        LEN     2
        NAME    patch
        JSR     fm_write
        RES     10
        JSR     fm_close
        RES     11
        ; 3. lock, delete refused, the lock in fm_type, unlock, verify
        NAME    n_save
        JSR     fm_lock
        RES     12
        NAME    n_save
        JSR     fm_delete
        RES     13
        NAME    n_save
        LDX     #FM_MUST_EXIST
        JSR     fm_open
        RES     29
        LDA     fm_type
        STA     res+30
        LEN     2
        NAME    patch
        JSR     fm_write
        RES     28
        JSR     fm_close
        RES     31
        NAME    n_save
        JSR     fm_unlock
        RES     14
        NAME    n_save
        JSR     fm_verify
        RES     15
        ; 4. a missing file (must exist), a text file created then deleted
        NAME    n_none
        LDX     #FM_MUST_EXIST
        JSR     fm_open
        RES     16
        NAME    n_tmp
        LDX     #FM_TEXT
        JSR     fm_open
        RES     17
        JSR     fm_close
        RES     18
        NAME    n_tmp
        JSR     fm_delete
        RES     19
        NAME    n_tmp
        JSR     fm_delete
        RES     20
        ; 5. every DOS buffer: A, B, C (MAXFILES 3), then D
        LDX     #0
@many:  STX     many
        LDA     names_lo,X
        LDY     names_hi,X
        LDX     #FM_TEXT
        JSR     fm_open
        LDX     many
        STA     res+21,X
        LDA     #0
        ROL     A
        STA     res2+21,X
        LDA     fm_file
        STA     handles,X
        LDA     fm_file+1
        STA     handles+4,X
        INX
        CPX     #4
        BNE     @many
        LDX     #2                      ; close the three, last first
@shut:  STX     many
        LDA     handles,X
        STA     fm_file
        LDA     handles+4,X
        STA     fm_file+1
        JSR     fm_close
        LDX     many
        STA     res+25,X
        DEX
        BPL     @shut
        ; 5b. whole files: fm_bsave, then fm_bload after wiping the source
        LDX     #99
@bs:    TXA
        EOR     #$3C
        STA     bsrc,X
        DEX
        BPL     @bs
        LDA     #<bsrc
        STA     fm_hdr
        LDA     #>bsrc
        STA     fm_hdr+1
        LDA     #100
        STA     fm_hdr+2
        LDA     #0
        STA     fm_hdr+3
        NAME    n_bs
        JSR     fm_bsave
        RES     32
        LDX     #101
        LDA     #$EE
@wipe:  STA     bsrc,X
        DEX
        BPL     @wipe
        NAME    n_bs
        JSR     fm_bload
        RES     33
        NAME    n_none
        JSR     fm_bload
        RES     34
.endif
        LDX     #0                      ; zero page after the calls
@z:     LDA     $00,X
        STA     zp_after,X
        INX
        BNE     @z
.if MODE = 0
        NAME    c_bload                 ; 6. DOS: BLOAD SAVE,A$4000
        JSR     dos_cmd_line
.endif
done:   JMP     done

n_save: .byte   "SAVE", 0
n_none: .byte   "NONE,D1"
n_tmp:  .byte   "TMP", 0
n_bs:   .byte   "BS", 0
n_a:    .byte   "A", 0
n_b:    .byte   "B", 0
n_c:    .byte   "C", 0
n_d:    .byte   "D", 0
names_lo: .lobytes n_a, n_b, n_c, n_d
names_hi: .hibytes n_a, n_b, n_c, n_d
c_bload: .byte  "BLOAD SAVE,A$4000", 0
patch:  .byte   $11, $22
.bss
res:    .res    40
res2:   .res    40
bsrc:   .res    102
many:   .res    1
handles: .res   8
data:   .res    {N}+4+256
back:   .res    {N}+4
guard:  .res    1
tail:   .res    1
zp_before: .res 256
zp_after:  .res 256
.code
.include "fm.asm"
.if MODE = 0
.include "dos.asm"
.endif
.include "exit.asm"
.export done, res, res2, back, guard, zp_before, zp_after, bsrc
'''


def build(work, defines):
    (work / 't.s').write_text(defines + PROGRAM.replace('{N}', str(N)))
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(work / 't.o'), str(work / 't.s')],
                   check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 't.lbl'),
                    '-o', str(work / 't.bin'), str(work / 't.o')], check=True)
    return a2test.labels(work / 't.lbl'), work / 't.bin'


def free_sectors(image):
    vtoc = dos33._sector(image, 17, 0)
    return sum(bin(vtoc[0x38 + 4 * t] << 8 | vtoc[0x39 + 4 * t]).count('1') for t in range(35))


def run(work, defines, disk=None, extra=(), wp=False):
    L, binary = build(work, defines)
    disk = disk or a2test.build_disk(work, 'FMTEST', binary, extra=extra)
    r = a2test.run(disk, ['wait:200', L.until('done', 6000), L.peek('res', 40), L.peek('res2', 40), L.peek('bsrc', 102),
                          L.peek('back', N + 6), L.peek('zp_before', 256), L.peek('zp_after', 256),
                          'peek:4000:304', 'peek:9600:1794', f'dsk:{work / "after.dsk"}'], wp=wp)
    before, after = r.mem(L['zp_before'], 256), r.mem(L['zp_after'], 256)
    zp = [i for i in range(256) if before[i] != after[i]]
    return L, r, list(r.mem(L['res'], 40)), list(r.mem(L['res2'], 40)), set(zp), \
        disk.read_bytes(), (work / 'after.dsk').read_bytes()


def check_main(defines, label):
    with tempfile.TemporaryDirectory(prefix='fm-') as tmp:
        L, r, res, c, zp, _, image = run(Path(tmp), defines + 'MODE = 0\n')
        expect = {0: (6, 0), 1: (0, 0), 2: (0, 0),             # created: A = 6, C = 0
                  3: (0, 0), 4: (4, None),                     # exists, binary kept
                  5: (0, 0), 6: (0, 0), 7: (0, 0), 8: (5, 1),   # END OF DATA
                  9: (0, 0), 10: (0, 0), 11: (0, 0),
                  12: (0, 0), 13: (10, 1), 29: (0, 0), 30: (0x84, None), 28: (10, 1), 31: (0, 0),
                  14: (0, 0), 15: (0, 0),
                  16: (6, 1), 17: (6, 0), 18: (0, 0), 19: (0, 0), 20: (6, 1),
                  21: (6, 0), 22: (6, 0), 23: (6, 0), 24: (12, 1),   # NO BUFFER
                  25: (0, None), 26: (0, None), 27: (0, None),
                  32: (0, 0), 33: (0, 0), 34: (6, 1)}             # fm_bsave, fm_bload, missing
        for ix, (a, carry) in expect.items():
            assert res[ix] == a and (carry is None or c[ix] == carry), \
                f'{label}: step {ix}: A={res[ix]} C={c[ix]}, expected A={a} C={carry}'
        payload = bytes((i & 255) ^ 0xC3 for i in range(N))
        header = bytes([0x00, 0x40, N & 255, N >> 8])
        back = r.mem(L['back'], N + 5)
        assert back[:N + 4] == header + payload, f'{label}: read back differs'
        assert back[N + 4] == 0xEE, f'{label}: fm_read wrote past its range'
        patched = payload[:10] + b'\x11\x22' + payload[12:]
        assert r.mem(0x4000, N) == patched, f'{label}: DOS BLOAD of the file differs'
        assert dos33.read_file(image, 'SAVE') == patched, f'{label}: SAVE on the disk differs'
        raw = b''.join(image[s:s + 256] for s in dos33.file_sectors(image, 'SAVE'))
        assert len(raw) == 512 and raw[N + 4:] == bytes(512 - N - 4), f'{label}: bytes written past the range'
        whole = bytes(i ^ 0x3C for i in range(100))
        assert r.mem(L['bsrc'], 102) == whole + b'\xEE\xEE', f'{label}: fm_bload'
        assert dos33.read_file(image, 'BS') == whole, f'{label}: fm_bsave on the disk'
        names = [e[0] for e in dos33.catalog(image)]
        assert 'SAVE' in names and 'TMP' not in names and 'NONE' not in names, names
        assert {'A', 'B', 'C'} <= set(names) and 'D' not in names, names
        mem = r.mem(0x9600, 1794)
        f = mem[0x700] | mem[0x701] << 8                    # ($9D00): buffer 1's name field
        used = []
        while f:
            used.append(mem[f - 0x9600])
            f = mem[f - 0x9600 + 36] | mem[f - 0x9600 + 37] << 8
        assert used == [0, 0, 0], f'{label}: DOS buffers still marked in use: {used}'
        return zp


def main():
    for zpx in (0x5A, 0xA5):
        zp = check_main(f'ZPX = ${zpx:02X}\n', f'garbage ^ ${zpx:02X}')
        assert zp <= FM_ZP, 'zero page outside the documented bytes: ' + ' '.join(f'{i:02X}' for i in sorted(zp - FM_ZP))
    zp = check_main('ZPX = $5A\nFM_KEEP_ZP = 1\nFM_SEI = 1\nDOS_ZP_START = $20\nDOS_ZP_LEN = $30\n', 'KEEP_ZP')
    assert not zp, 'FM_KEEP_ZP: zero page changed: ' + ' '.join(f'{i:02X}' for i in sorted(zp))
    print('fm: create (A=6), write, read back exact, seek, END OF DATA, rewrite, lock/delete refused/unlock, '
          'verify, missing file, delete twice, NO BUFFER at the 4th open, handles, DOS BLOAD agrees, '
          'buffers free; zero page as documented; FM_KEEP_ZP + FM_SEI.')

    with tempfile.TemporaryDirectory(prefix='fm-wp-') as tmp:
        L, r, res, c, zp, before, after = run(Path(tmp), 'ZPX = $5A\nMODE = 1\n', wp=True)
        assert (res[0], c[0]) == (4, 1), f'write protected: open A={res[0]} C={c[0]}'
        assert after == before, 'write protected: the image changed'
    print('fm: write-protected disk: open answers 4, nothing written.')

    with tempfile.TemporaryDirectory(prefix='fm-full-') as tmp:
        work = Path(tmp)
        L, binary = build(work, 'ZPX = $5A\nMODE = 1\n')
        free = free_sectors(a2test.build_disk(work, 'FMTEST', binary).read_bytes())
        keep = 2                                    # SAVE's T/S list + 1 of its 2 data sectors
        extra, n = [], 0
        while free - keep > 0:
            data = min(120, free - keep - 1)        # + its T/S list
            path = work / f'fill{n}.bin'
            path.write_bytes(bytes(data * 256 - 4))
            extra.append(f'FILL{n}={path}@0x4000')
            free -= data + 1
            n += 1
        disk = a2test.build_disk(work, 'FMTEST', binary, extra=extra)
        assert free_sectors(disk.read_bytes()) == keep, free_sectors(disk.read_bytes())
        L, r, res, c, zp, before, after = run(work, 'ZPX = $5A\nMODE = 1\n', disk=disk)
        assert (res[0], c[0]) == (6, 0), f'full disk: open A={res[0]} C={c[0]}'
        assert (res[1], c[1]) == (9, 1) or (res[2], c[2]) == (9, 1), \
            f'full disk: write A={res[1]} C={c[1]}, close A={res[2]} C={c[2]}'
        assert free_sectors(after) == 0, free_sectors(after)
        names = [e[0] for e in dos33.catalog(after)]
        assert 'SAVE' in names and all(f'FILL{i}' in names for i in range(n)), names
        print(f'fm: full disk: write A={res[1]}, close A={res[2]}; catalog intact.')


if __name__ == '__main__':
    main()
