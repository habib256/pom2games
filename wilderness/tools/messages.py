#!/usr/bin/env python3
"""messages.py: dump the original's numbered messages (local only).

Message X (1..256) is printed by core $4E78 (entry $4D21 / $4D2A): sector
k = (X-1) >> 2 of SMALLDOS track $18 + k / 16 (Journey side, physical track
34 - t), sector k mod 16, 64-byte slot (X-1) & 3. Characters have bit 7 set,
0 ends the message, other bytes are substitutions:
  1      the noun typed by the player ($0300)            -> {NOUN}
  2..3   animal name from the map table $60D0 + 12*(Y-1) -> {ANIMAL}
  4..127 a number ($0E low, $0F high, Applesoft LINPRT)  -> {N}
A space is printed before the text (after the '>' prompt on line 21).
In the dump a carriage return ($8D) is written \\n.

Usage: messages.py JOURNEY.dsk OUT.txt
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smalldos  # noqa: E402


def decode(slot):
    out = ''
    for b in slot:
        if b == 0:
            return out
        if b & 0x80:
            c = chr(b & 0x7F)
            out += c if c >= ' ' else ('\\n' if c == '\r' else f'\\x{ord(c):02x}')
        elif b >> 1 == 0:
            out += '{NOUN}'
        elif b >> 2 == 0:
            out += '{ANIMAL}'
        else:
            out += '{N}'
    return out + '{...}'          # no terminator inside the 64 bytes


def messages(disk):
    dk = smalldos.Disk(disk)
    dk.flip = True
    for x in range(1, 257):
        k = (x - 1) >> 2
        sec = dk.sector(0x18 + k // 16, k % 16)
        o = ((x - 1) & 3) * 64
        yield x, decode(sec[o:o + 64])


def main():
    with open(sys.argv[2], 'w') as f:
        for x, text in messages(open(sys.argv[1], 'rb').read()):
            f.write(f'{x:3d} ${x:02X}  {text}\n')


if __name__ == '__main__':
    main()
