#!/usr/bin/env python3
"""preview.py [START]: decode the Robotropolis Preview script (side B).

The preview loads (call $45D5) a script at $8880-$8CBF (block $092) run by
a byte-code interpreter at $E470 (block $0A0, language card RAM):
JSR $E470 is followed by script bytes; each byte is an opcode whose
handler is in the tables $E60F (lo) / $E5F6 (hi). Opcode 6 resumes
6502 code inline (until the next JSR $E470). Recorded player input is
replayed by $E005 (A = stream number) from the table at $9000 (block $095).

Prints the script as a listing (addresses, opcode names, operands, texts).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'dev', 'tools'))
import memimg  # noqa: E402
from re6502.opcodes import decode, text  # noqa: E402

# opcode: (name, fixed operand count, trailing 0-terminated list/text)
OPS = {
    1: ('SAVEFRAME', 3, None),   # save text rows a..b of HGR1, draw a frame (colour c)
    2: ('RESTORE', 0, None),     # put the saved rows back
    3: ('DELAY', 1, None),       # wait, keys ignored
    4: ('FRAME', 1, None),       # redraw the frame in colour c
    5: ('PRINT', 1, 'text'),     # row (0 = keep) then text ending with 0
    6: ('NATIVE', 0, None),      # 6502 code follows, up to the next JSR $E470
    7: ('GETKEY', 1, 'keys'),    # wait for one of the keys listed
    8: ('IFKEY', 2, 'keys'),     # goto addr if the last key is listed
    9: ('GOTO', 2, None),
    10: ('NOP', 0, None),
    11: ('SHAPE', 4, None),      # x, y, shape address: EOR a shape on HGR1
    12: ('WAIT', 1, None),       # wait; SPACE skips, P pauses, ESC quits to menu
    13: ('SOUND', 2, None),      # address of (pitch, duration) pairs, 0 ends
    14: ('SPRITE', 4, None),
    15: ('INVERT', 4, None),     # EOR #$FF over bytes x1..x2, lines y1..y2
    16: ('POKE', 3, None),       # value, address
    17: ('ADD', 3, None),
    18: ('SUB', 3, None),
    19: ('IFEQ', 5, None),       # value, address, goto
    20: ('CALL', 2, None),
    21: ('RETURN', 0, None),
    22: ('IFNE', 5, None),
    23: ('MARQUEE', 3, 'text'),  # row, speed, flags, then text ending with 0
    24: ('SCROLL', 4, None),
}


def txt(b):
    return ''.join('/' if c == 0x8D else chr(c & 0x7F) if c >= 0xA0 else '\\x%02X' % c for c in b)


def script(m, a, end):
    while a < end:
        op = m[a]
        if op not in OPS:
            print('%04X: .byte $%02X' % (a, op))
            a += 1
            continue
        name, n, tail = OPS[op]
        ops = list(m[a + 1:a + 1 + n])
        start, a = a, a + 1 + n
        extra = ''
        if tail:
            j = a
            while m[j]:
                j += 1
            extra = ' "%s"' % txt(m[a:j]) if tail == 'text' else ' keys=%s' % txt(m[a:j])
            a = j + 1
        if n in (2, 3, 5) and name not in ('IFKEY',):
            pass
        opt = ' '.join('$%02X' % x for x in ops)
        if name in ('GOTO', 'CALL', 'SOUND', 'IFKEY'):
            opt = '$%04X' % (ops[0] | ops[1] << 8)
        elif name in ('POKE', 'ADD', 'SUB'):
            opt = '#$%02X, $%04X' % (ops[0], ops[1] | ops[2] << 8)
        elif name in ('IFEQ', 'IFNE'):
            opt = '($%04X) #$%02X -> $%04X' % (ops[1] | ops[2] << 8, ops[0], ops[3] | ops[4] << 8)
        print('%04X: %-9s %s%s' % (start, name, opt, extra))
        if name == 'NATIVE':
            a = native(m, a, end)


def native(m, a, end):
    while a < end:
        d = decode(m, a, cmos=False)
        if d is None:
            print('%04X:   .byte $%02X' % (a, m[a]))
            a += 1
            continue
        print('%04X:   %s' % (a, text(m, a)))
        if d[0] == 'jsr' and d[3] == 0xE470:
            return a + 3
        if d[0] == 'jsr' and d[3] == 0xE005:
            pass
        a += d[2]
    return a


def main():
    side, segs = memimg.LESSONS['preview']
    m = memimg.build(side, segs)
    start = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x8880
    end = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x8CC0
    native(m, start, end) if start == 0x8880 else None
    script(m, 0x888B if start == 0x8880 else start, end)
    streams = [(m[0x9000 + 2 * i] | m[0x9001 + 2 * i] << 8) for i in range(16)]
    print('\nflux d\'entrée enregistrés ($9000 + décalage) : %s' % ' '.join('%d:$%04X' % (i, 0x9000 + s) for i, s in enumerate(streams)))


if __name__ == '__main__':
    main()
