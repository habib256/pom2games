#!/usr/bin/env python3
"""lib/apple2/initials.asm ini_key in a2run against a Python model: every
key of a script (letters, lowercase, arrows, DELETE, out-of-set keys,
RETURN / ESC) gives the same A, C, Z, cursor and buffer. Built three ways:
default (3 letters A-Z by arithmetic), INI_LEN = 4 with an INI_CHARS table
(letters, digits, space, '-'), and INI_DELETE moved."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

KC_LEFT, KC_RIGHT, KC_UP, KC_DOWN, KC_RET, KC_ESC = 0x08, 0x15, 0x0B, 0x0A, 0x0D, 0x1B

SRC = '''.include "apple2.inc"
{options}
.code
        LDX     #INI_LEN-1
@init:  LDA     start,X
        STA     ini_buf,X
        DEX
        BPL     @init
        LDA     #0
        STA     ini_pos
        STA     n
loop:   LDX     n
        LDA     keys,X
        BEQ     done
        JSR     ini_key
        PHP
        LDX     n
        STA     out_a,X
        PLA
        AND     #$03            ; Z (bit 1), C (bit 0)
        STA     out_p,X
        LDA     ini_pos
        STA     out_pos,X
        TXA
        ASL     A
        ASL     A
        TAY
        LDX     #0
@cp:    LDA     ini_buf,X
        STA     out_buf,Y
        INY
        INX
        CPX     #INI_LEN
        BNE     @cp
        INC     n
        BNE     loop
done:   JMP     done
start:  .byte   {start}
keys:   .byte   {keys}, 0
{chars}
.bss
n:      .res 1
out_a:  .res 64
out_p:  .res 64
out_pos: .res 64
out_buf: .res 256
.code
.include "initials.asm"
.export done, out_a, out_p, out_pos, out_buf
'''


def model(keys, start, length, chars, delete):
    buf, pos, out = list(start), 0, []
    for k in keys:
        a, c = 0, 0
        if k in (KC_RET, KC_ESC):
            a, c = k, 1
        elif k in (KC_LEFT, delete):
            if pos > 0:
                pos, a = pos - 1, 1
        elif k == KC_RIGHT:
            if pos < length - 1:
                pos, a = pos + 1, 1
        elif k in (KC_UP, KC_DOWN):
            cur = buf[pos]
            if cur in chars:
                i = (chars.index(cur) + (1 if k == KC_UP else -1)) % len(chars)
            else:
                i = 0 if k == KC_UP else len(chars) - 1
            buf[pos], a = chars[i], 1
        else:
            if ord('a') <= k <= ord('z'):
                k &= 0xDF
            if k in chars:
                buf[pos], a = k, 1
                pos = min(pos + 1, length - 1)
        # Z: set with A = 0, and on RETURN / ESC (from their CMP; C = 1 decides)
        out.append((a, c | (2 if a == 0 or c else 0), pos, bytes(buf)))
    return out


def run(work, name, options, start, keys, length, chars, delete, table=None):
    chars_src = f'charset: .byte {",".join(str(c) for c in table)}' if table else ''
    src = work / (name + '.s')
    src.write_text(SRC.format(options=options, start=','.join(str(c) for c in start),
                              keys=','.join(str(k) for k in keys), chars=chars_src))
    obj, binary, lbl = (src.with_suffix(e) for e in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(lbl),
                    '-o', str(binary), str(obj)], check=True)
    L = a2test.labels(lbl)
    r = a2test.run(None, a2test.bin_steps(binary) + [L.until('done', 100), L.peek('out_a', 64),
                                                    L.peek('out_p', 64), L.peek('out_pos', 64),
                                                    L.peek('out_buf', 256)])
    a, p, pos, buf = (r.mem(L[n], k) for n, k in (('out_a', 64), ('out_p', 64), ('out_pos', 64), ('out_buf', 256)))
    expect = model(keys, start, length, chars, delete)
    for i, (k, e) in enumerate(zip(keys, expect)):
        got = (a[i], p[i], pos[i], bytes(buf[i * 4:i * 4 + length]))
        assert got == e, f'{name}: key {i} ({k:#04x}) gave {got}, expected {e}'


def main():
    az = [ord(c) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
    script = [KC_LEFT, ord('b'), ord('O'), ord('B'), ord('X'), ord('1'), KC_RIGHT, KC_UP, KC_UP,
              KC_LEFT, KC_LEFT, KC_LEFT, 0x7F, KC_DOWN, KC_DOWN, KC_RIGHT, KC_DOWN, ord(' '),
              ord('z'), KC_UP, KC_RIGHT, KC_RIGHT, ord('-'), KC_ESC, KC_RET, 0x80 | ord('A')]
    with tempfile.TemporaryDirectory(prefix='initials-') as tmp:
        work = Path(tmp)
        run(work, 'az', '', b'AAZ', script, 3, az, 0x7F)
        run(work, 'odd', '', b'@[a', [KC_UP, KC_RIGHT, KC_DOWN, KC_RIGHT, KC_UP, KC_LEFT, KC_UP],
            3, az, 0x7F)
        table = az + [ord(c) for c in '0123456789 -']
        run(work, 'tab', 'INI_LEN = 4\nINI_CHARS = charset\nINI_CHARS_N = 38', b'A9-?',
            script + [KC_RIGHT, KC_RIGHT, KC_RIGHT, KC_DOWN, KC_UP, KC_UP, KC_UP, ord('9'), KC_UP],
            4, table, 0x7F, table)
        run(work, 'del', 'INI_DELETE = $1F', b'ABC', [KC_RIGHT, KC_RIGHT, 0x7F, 0x1F, 0x1F, 0x1F],
            3, az, 0x1F)
    print('ini_key: letters, lowercase, arrows, wrap, DELETE, RETURN/ESC, out-of-set keys; '
          'A-Z, INI_LEN/INI_CHARS table and INI_DELETE builds match the model.')


if __name__ == '__main__':
    main()
