#!/usr/bin/env python3
"""ROGUE's sounds: speaker effects and three tunes -> src/music.inc.

    python3 tools/music.py src/music.inc

Effects (sfx.inc's sfx_play): a list of (tone X, tone A) pairs ended by 0,
i.e. sound.asm `tone` calls: X the half period (12 + 5 X cycles a flip),
A the flips. Written here as 'NOTE:ms' (C6:30 = C6 for 30 ms). The ids are
ordered by importance: in one turn the highest queued id is the one heard.

Tunes (dev/lib/apple2/tune.asm, encoder dev/tools/audio/tune.py): the
title's (played once while the title waits), the death dirge, the victory
fanfare. A unit = 1/60 s ticks given per tune.

Mockingboard (sfx.inc with SND_MB = 1): the same effects and tunes as AYS
songs (dev/tools/audio/aysong.py) for aysong.asm on mb_irq.asm's 50 Hz
tick, in segment SNDDATA: an effect is one voice, a row a tick (its
milliseconds rounded to 20 ms ticks, at least one), a tune is its melody
plus the same line an octave lower, a row a unit. ays_sfx_lo/hi index the
effects by id (1 first); ays_title, ays_death, ays_win are the tunes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools/audio'))
from notes import CPU, hz, midi, tone_x  # noqa: E402
from tune import asm, parse, tune  # noqa: E402
import aysong  # noqa: E402
from aysong import OFF, Cell, Instrument, Pattern, Song, Tick  # noqa: E402

# id order = priority (1 lowest)
SFX = [
    ('BUMP',   'A4:14 A4:14'),                      # into a wall: a low thud
    ('DOOR',   'C5:15 G5:20'),                      # edge door: next room
    ('PICKUP', 'E6:25 B6:35'),                      # an item into the bag
    ('HIT',    'A5:12 F5:18'),                      # you strike a monster
    ('THROW',  'C7:8 G6:8 D6:8 A5:8'),              # a dagger flies
    ('KILL',   'E5:15 C5:15 A4:30'),                # a monster dies
    ('BUFF',   'C6:30 E6:30 G6:45'),                # sword / tunic / amulet / torch
    ('HEAL',   'G5:30 C6:30 E6:30 G6:60'),          # ration / potion
    ('SCROLL', 'C7:20 G6:20 E7:20 C7:20 G7:60'),    # the map revealed
    ('HURT',   'B4:25 A4:45'),                      # a monster bites you
    ('PIT',    'C6:30 A5:30 F5:30 D5:30 B4:30 A4:60'),  # you fall in a pit
    ('STAIRS', 'G5:40 E5:40 C5:40 B4:40 A4:80'),    # down the stairs
    ('LEVEL',  'C5:40 E5:40 G5:40 C6:100'),         # a level-up
    ('BOSS',   'A4:80 A#4:80 A4:80 A#4:80 A4:200'), # the demon's room
]

# tunes: unit = ticks of ~1/60 s
TITLE = ('A4:2 C5:2 E5:2 A5:4 G5:2 E5:2 F5:2 D5:2 E5:6 R:2 '
         'A4:2 C5:2 E5:2 A5:2 C6:2 B5:2 G#5:2 B5:2 A5:8', 6)
DEATH = ('E5:3 D#5:3 D5:3 C#5:3 C5:6 R:2 A4:3 A4:1 A4:8', 8)
WIN = ('C5:2 E5:2 G5:2 C6:4 G5:2 C6:8 R:2 E6:2 D6:2 C6:2 G6:10', 6)


def effect(text):
    out = bytearray()
    for item in text.split():
        name, ms = item.split(':')
        x = tone_x(hz(midi(name)))
        assert 11 <= x <= 255, item
        flips = round(int(ms) * CPU / 1000 / (12 + 5 * x))
        assert flips >= 1, item
        while flips:                    # tone's A is one byte: split
            out += bytes([x, min(flips, 255)])
            flips -= min(flips, 255)
    return out + b'\0'


# AY instruments: a decaying note restarts at each new note (articulation)
def _ins(vols, name):
    return Instrument(ticks=[Tick(vol=v) for v in vols], name='')


AY_SFX = _ins([15, 14, 13, 12, 11, 10, 9, 8, 7, 6], 'sfx')
AY_LEAD = _ins([15, 14, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 8], 'lead')
AY_BASS = _ins([11, 10, 9, 9, 8, 8, 7], 'bass')
AY_TICK_MS = 20                         # mb_irq.asm at MB_IRQ_HZ = 50


def ay_note(name):
    return midi(name) - 12              # AYS note 57 = A4 = MIDI 69


def ay_song(voices_rows, instruments, speed):
    rows = len(voices_rows[0])
    assert 1 <= rows <= 64, rows
    tracks = voices_rows + [[Cell() for _ in range(rows)] for _ in range(3 - len(voices_rows))]
    return aysong.encode(Song(patterns=[Pattern(tracks)], instruments=instruments, order=[0],
                              voices=3, rows=rows, speed=speed, loop=None))


def ay_effect(text):
    track = []
    for item in text.split():
        name, ms = item.split(':')
        ticks = max(1, round(int(ms) / AY_TICK_MS))
        track += [Cell(note=ay_note(name), ins=1 if not track else None)] + [Cell()] * (ticks - 1)
    return ay_song([track], [AY_SFX], 1)


def ay_tune(text, unit):
    speed = round(unit * 50 / 60)       # a unit of 1/60 s ticks -> 50 Hz ticks
    lead, bass = [], []
    for name, n in parse(text):
        rest = name == 'R'
        lead += [Cell(note=OFF if rest else ay_note(name), ins=None if rest or lead else 1)]
        bass += [Cell(note=OFF if rest else ay_note(name) - 12, ins=None if rest or bass else 2)]
        lead += [Cell()] * (n - 1)
        bass += [Cell()] * (n - 1)
    return ay_song([lead, bass], [AY_LEAD, AY_BASS], speed)


def ay_asm():
    out = ['', '; Mockingboard: AYS songs (sfx.inc, SND_MB = 1)', '.if SND_MB',
           '.segment "SNDDATA"']
    labels = [f'ays_sfx_{name.lower()}' for name, _ in SFX]
    out.append('ays_sfx_lo:  .byte ' + ', '.join(f'<{l}' for l in labels))
    out.append('ays_sfx_hi:  .byte ' + ', '.join(f'>{l}' for l in labels))
    total = 0
    for label, (_, text) in zip(labels, SFX):
        data = ay_effect(text)
        total += len(data)
        out += aysong.asm_rows(label, data)
    for label, (notes_, unit) in (('ays_title', TITLE), ('ays_death', DEATH), ('ays_win', WIN)):
        data = ay_tune(notes_, unit)
        total += len(data)
        out += aysong.asm_rows(label, data)
    out += ['.endif', '']
    return '\n'.join(out), total


def main():
    data, start = bytearray(), []
    for _, text in SFX:
        start.append(len(data))
        data += effect(text)
    assert len(data) <= 256, len(data)
    lines = ['; generated by tools/music.py -- do not edit', '']
    lines += [f'SND_{name:<7}= {i}' for i, (name, _) in enumerate(SFX, 1)]
    lines += ['', '.segment "RODATA"', 'sfx_start:']
    lines += [f'        .byte {", ".join(str(v) for v in start)}']
    lines += ['sfx_data:']
    lines += [f'        .byte {", ".join(f"${b:02X}" for b in data[i:i + 16])}'
              for i in range(0, len(data), 16)]
    text = '\n'.join(lines) + '\n'
    for label, (notes, unit) in (('tune_title', TITLE), ('tune_death', DEATH), ('tune_win', WIN)):
        text += asm(label, tune(notes, unit))
    ay, _ = ay_asm()
    text += ay + '.segment "CODE"\n'
    Path(sys.argv[1]).write_text(text)


if __name__ == '__main__':
    main()
