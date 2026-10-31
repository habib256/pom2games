#!/usr/bin/env python3
"""lib/apple2/savehdr.asm in a2run: magic_check against the first and the
second magic of MAGIC_TABLE (C = 0 on a match, C = 1 for a difference in
any one byte), magic_put writing the second magic over garbage, and a
MAGIC_LEN = 2 build."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

SRC = '''{options}
MAGIC_TABLE = magics
.code
        LDX     #0
@c:     STX     k               ; data k at buf + 4 * k, k = 0..7, checked
        TXA                     ; against the first magic (k < 4) or the
        ASL     A               ; second
        ASL     A
        ADC     #<buf
        STA     tmp
        LDA     #>buf
        ADC     #0
        TAY
        LDX     #MAGIC_LEN-1
        LDA     k
        CMP     #4
        BCC     @first
        LDX     #2*MAGIC_LEN-1
@first: LDA     tmp
        JSR     magic_check
        LDX     k
        LDA     #0
        ROL     A
        STA     res,X
        INX
        CPX     #8
        BNE     @c
        LDA     #<target                ; magic_put: the second magic
        LDY     #>target
        LDX     #2*MAGIC_LEN-1
        JSR     magic_put
done:   JMP     done
magics: .byte   {magics}
buf:    .byte   {buf}
target: .byte   $EE, $EE, $EE, $EE, $EE
.bss
tmp:    .res 1
k:      .res 1
res:    .res 8
.code
.include "savehdr.asm"
.export done, res, target
'''


def run(work, name, options, length, magics):
    first, second = magics[:length], magics[length:]
    rows = []
    for k in range(8):
        m = bytearray(first if k < 4 else second)
        if k % 4:                       # k = 1..3, 5..7: one byte changed
            m[(k % 4 - 1) % length] ^= 0x20
        rows.append(bytes(m).ljust(4, b'\0'))
    src = work / (name + '.s')
    src.write_text(SRC.format(options=options, magics=', '.join(str(b) for b in magics),
                              buf=', '.join(str(b) for b in b''.join(rows))))
    obj, binary, lbl = (src.with_suffix(e) for e in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(lbl),
                    '-o', str(binary), str(obj)], check=True)
    L = a2test.labels(lbl)
    r = a2test.run(None, a2test.bin_steps(binary) + [L.until('done', 10), L.peek('res', 8), L.peek('target', 5)])
    res, target = r.mem(L['res'], 8), r.mem(L['target'], 5)
    assert list(res) == [0, 1, 1, 1, 0, 1, 1, 1], f'{name}: magic_check C per case {list(res)}'
    assert target == second + b'\xEE' * (5 - length), f'{name}: magic_put wrote {target.hex()}'


def main():
    with tempfile.TemporaryDirectory(prefix='savehdr-') as tmp:
        work = Path(tmp)
        run(work, 'four', '', 4, b'MZS\x01MZP\x01')
        run(work, 'two', 'MAGIC_LEN = 2', 2, b'ABCD')
    print('savehdr: magic_check matches / rejects a change in every byte of two magics, '
          'magic_put writes the chosen one; MAGIC_LEN 4 and 2.')


if __name__ == '__main__':
    main()
