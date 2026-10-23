#!/usr/bin/env python3
"""WARGALAGA II music -> build/song.pt3 (Vortex Tracker II module, played
by dev/lib/apple2/pt3 on the first AY of the Mockingboard).

The tune is tools/sound.py's (MELODY, BASS: original, A minor), one PT3
line a sixteenth, SPEED ticks a line at sound.MUS_HZ. Channel A melody, B bass,
C silent. The player converts nothing: the periods are frequency table 1
(PT3NoteTable_ST, made for a 2 MHz AY) on a 1.023 MHz Mockingboard: an
octave lower than written, plus ~40 cents. The notes are written an octave
up: PT3 note n (0 = C-1) sounds MIDI n + 12, ~40 cents sharp (A4 450 Hz).

    tools/pt3.py OUT.pt3          write the module
    tools/pt3.py --table          print table 1 as the player builds it
"""
from pathlib import Path
import sys

import sound

SPEED = round(sound.MUS_HZ * 0.12)  # ticks a line (a sixteenth, ~0.12 s)
TABLE = 1
# Samples: (b0, b1, tone) per tick, then the loop index. b1 = $80 | volume:
# tone on, noise off. A short attack then a held level.
SAMPLES = {
    1: ([15, 14, 13, 12, 12, 11, 11, 10], 7),          # melody
    2: ([15, 14, 13, 13, 12, 12, 12, 12], 7),          # bass
}
BASE1 = [0x0EF8, 0x0E10, 0x0D60, 0x0C80, 0x0BD8, 0x0B28, 0x0A88, 0x09F0, 0x0960, 0x08E0, 0x0858, 0x07E0]


def note_table():
    """The 96 periods pt3_init_song builds for table 1."""
    t = BASE1 + [0] * 84
    for i in range(84):
        t[i + 12] = t[i] >> 1
    t[23] = (t[23] & 0xFF00) | 0xFD
    t[46] -= 1
    return t


def pt3_note(name):
    """PT3 note number (0 = C-1) sounding the MIDI note of `name`."""
    n = sound.midi(name) - 12
    assert 0 <= n < 96, name
    return n


def channel(notes, sample):
    out = [0xF0, sample * 2]                    # ornament 0, the sample
    skip = None
    for name, sixteenths in notes:
        if sixteenths != skip:
            out += [0xB1, sixteenths]
            skip = sixteenths
        out.append(0x50 + pt3_note(name) if name else 0xC0)
    return out + [0]


def module():
    lines = sum(d for _, d in sound.MELODY)
    assert lines == sum(d for _, d in sound.BASS) == 64
    head = bytearray(0xC9)
    text = b'ProTracker 3.6 compilation of ' + b'WARGALAGA II'.ljust(32) + b' by ' + b'pom2games'.ljust(32)
    head[0:len(text)] = text
    head[0x63], head[0x64], head[0x65], head[0x66] = TABLE, SPEED, 1, 0
    data = bytearray(head) + bytes([0, 0xFF])   # position list: pattern 0 (x3), end
    patterns = len(data)
    data += bytes(6)                            # pattern 0: A, B, C pointers
    chans = [channel(sound.MELODY, 1), channel(sound.BASS, 2), [0xB1, 64, 0xC0, 0]]
    for k, c in enumerate(chans):
        data[patterns + 2 * k:patterns + 2 * k + 2] = len(data).to_bytes(2, 'little')
        data += bytes(c)
    data[0x67:0x69] = patterns.to_bytes(2, 'little')
    orn = len(data)
    data += bytes([0, 1, 0])                    # ornament 0: loop 0, length 1, +0
    for i in range(16):
        data[0xA9 + 2 * i:0xAB + 2 * i] = orn.to_bytes(2, 'little')
    at = {}
    for i, (vols, loop) in SAMPLES.items():
        at[i] = len(data)
        data += bytes([loop, len(vols)])
        for v in vols:
            data += bytes([0, 0x80 | v, 0, 0])
    for i in range(32):                         # (unused ones: sample 1)
        data[0x69 + 2 * i:0x6B + 2 * i] = at.get(i, at[1]).to_bytes(2, 'little')
    return bytes(data)


def main():
    if '--table' in sys.argv:
        print(note_table())
        return
    out = Path(sys.argv[1])
    data = module()
    if not out.exists() or out.read_bytes() != data:
        out.write_bytes(data)


if __name__ == '__main__':
    main()
