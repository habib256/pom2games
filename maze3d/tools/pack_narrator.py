#!/usr/bin/env python3
"""Losslessly pack narrator text into five-bit symbols to fit the 48 KB game."""
import re
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
ESCAPES = "'-?"

def pack(line):
    symbols = []
    for c in line:
        if c == ' ':
            symbols.append(1)
        elif 'A' <= c <= 'Z':
            symbols.append(ord(c) - ord('A') + 2)
        elif c in '!.,':
            symbols.append(28 + '!.,'.index(c))
        else:
            symbols.extend((31, ESCAPES.index(c)))
    symbols.append(0)
    bits = ''.join(f'{x:05b}' for x in symbols)
    bits += '0' * (-len(bits) % 8)
    packed = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
    # Independent decode checks every character, including escape punctuation.
    stream = ''.join(f'{x:08b}' for x in packed)
    it = iter(int(stream[i:i+5], 2) for i in range(0, len(stream)-4, 5))
    decoded = []
    for x in it:
        if x == 0:
            break
        decoded.append(' ' if x == 1 else chr(ord('A') + x - 2) if x < 28
                       else '!.,'[x-28] if x < 31 else ESCAPES[next(it)])
    assert ''.join(decoded) == line
    return packed

if __name__ == '__main__':
    source = (GAME / 'src/narrator.asm').read_text()
    def replace(match):
        label, line = match.groups()
        assert len(line) < 32
        return label + ': .byte ' + ','.join(f'${x:02X}' for x in pack(line))
    output = re.sub(r'(ph_\w+): .byte "([^"]*)",0', replace, source)
    (GAME / 'build/narrator_packed.inc').write_text(output)
