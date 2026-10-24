#!/usr/bin/env python3
"""WARGALAGA II records (lot 9): the HIGHSCORES file and its rules.

HIGHSCORES (ProDOS BIN, REC_SIZE bytes), as src/front.s reads and writes it:
  0     'W' (a file of this game)
  1     REC_VERSION
  2     controls: 0 keyboard, 1 joystick
  3..   REC_N entries of 7 bytes, best first: initials (3 ASCII), score
        (3 BCD bytes, low first), level reached (1..255)
  rest  zeros

A new score enters the table when it beats an entry (an equal score goes
below the old one); the entries under it move down, the last one leaves.

    tools/records.py OUT        the HIGHSCORES of a new disk
"""
from pathlib import Path
import sys

REC_N = 8
REC_ENTRY = 7
REC_SIZE = 64
REC_VERSION = 1
DEFAULTS = [('WAR', 50000, 10), ('GAL', 40000, 8), ('AGA', 30000, 6), ('POM', 20000, 5),
            ('APL', 15000, 4), ('HGR', 10000, 3), ('ZAP', 5000, 2), ('ACE', 2000, 1)]


def bcd(v):
    return bytes(int(f'{v:06d}'[k:k + 2], 16) for k in (4, 2, 0))


def unbcd(b):
    return int(f'{b[2]:02x}{b[1]:02x}{b[0]:02x}')


def encode(table, joy=0):
    assert len(table) == REC_N
    out = b'W' + bytes([REC_VERSION, joy])
    for name, score, level in table:
        out += name.encode() + bcd(score) + bytes([level])
    return out.ljust(REC_SIZE, b'\0')


def decode(data):
    """-> (table, joy)."""
    table = []
    for k in range(REC_N):
        e = data[3 + REC_ENTRY * k:3 + REC_ENTRY * (k + 1)]
        table.append((e[:3].decode('latin-1'), unbcd(e[3:6]), e[6]))
    return table, data[2]


def rank(table, score):
    """Where score enters (0..REC_N-1), or None."""
    for k, (_, s, _) in enumerate(table):
        if score > s:
            return k
    return None


def insert(table, name, score, level):
    k = rank(table, score)
    if k is None:
        return list(table)
    return (table[:k] + [(name, score, level)] + table[k:])[:REC_N]


def level_reached(level, loop):
    """The level number shown (level 0..99, loops past 100), at most 255."""
    return min(255, 100 * loop + level + 1)


def main():
    Path(sys.argv[1]).write_bytes(encode(DEFAULTS))


if __name__ == '__main__':
    main()
