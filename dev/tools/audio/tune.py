#!/usr/bin/env python3
"""Tunes for dev/lib/apple2/tune.asm: notes as text -> 3-byte events.

    tick_cycles(wait_a)          cycles of one tick (the Monitor's WAIT, A)
    note('G#5', tick)            (half period X, toggles a tick); 'R' -> (0, 0)
    tune('A4:1 R:1', unit, tick) the events, ended by a 0
    asm(label, data)             ca65 lines: label, then one .byte row a note

An event is `.byte ticks, half_period, toggles`: ticks of ~1/60 s (the last
one silent, so repeated notes stay apart), sound.asm tone's X (0: a rest)
and the speaker flips that fill one tick at that pitch; a 0 ends the tune.
Notes come from notes.parse ('C5:2' = two units); unit = ticks a unit.
From DIRTBIKE's tools/music.py (which keeps its songs and imports this).
"""
from notes import hz, midi, parse, tone_flips, tone_x

REST_WAIT = 79                  # tune.asm TUNE_REST_WAIT (default)


def tick_cycles(wait_a=REST_WAIT):
    """The Monitor's WAIT with A: (26 + 27 A + 5 A^2) / 2 cycles."""
    return (26 + 27 * wait_a + 5 * wait_a * wait_a) // 2


TICK = tick_cycles()


def note(name, tick=TICK):
    """'G#5' -> (X, flips a tick); 'R' -> (0, 0)."""
    if name == 'R':
        return 0, 0
    x = tone_x(hz(midi(name)))
    assert x >= 11, name
    return x, tone_flips(x, tick)


def tune(text, unit, tick=TICK):
    out = bytearray()
    for name, n in parse(text):
        x, flips = note(name, tick)
        assert 1 <= n * unit <= 255, (name, n)
        out += bytes([n * unit, x, flips])
    return out + b'\0'


def asm(label, data):
    rows = [', '.join(f'${b:02X}' for b in data[i:i + 3]) for i in range(0, len(data) - 1, 3)]
    return f'{label}:\n' + ''.join(f'        .byte {r}\n' for r in rows) + '        .byte 0\n'
