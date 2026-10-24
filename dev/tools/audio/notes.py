#!/usr/bin/env python3
"""Notes for the Apple II's sound routines, shared by the games' generators.

    midi('G#5') -> 80        hz(69) -> 440.0
    tone_x(hz)               dev/lib/apple2/sound.asm's half period X
    tone_flips(x, cycles)    flips of that tone filling `cycles`
    half_period(hz, turn)    a half period in turns of a counted loop
                             (duet.asm: DUET_TURN; a game's own wait loop)
    duet_encode(tune, tempo) events of dev/lib/apple2/duet.asm, in just
                             intonation (DUET_COUNTS, C4 = 60 turns)
    parse('C5:1 R:2')        [('C5', 1), ('R', 2)]
    byte_block(label, data)  ca65 lines: label, then .byte rows

Note names: a letter, an optional '#', the octave (C4 = MIDI 60, A4 = 440
Hz). The clock is a parameter where the games differ (CPU: the NTSC Apple
II's 1,020,484 Hz; the breakout games time their slices on 1,023,000).
"""
from math import log2

CPU = 1_020_484
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
TONE_FLIP = 12                  # sound.asm tone: 12 + 5 X cycles a flip
DUET_TURN = 33                  # duet.asm: cycles of one turn
DUET_TURNS = 255                # turns of a slice
DUET_LOOK = 34                  # cycles a slice adds (the keyboard look)
DUET_SLICE = DUET_TURNS * DUET_TURN + DUET_LOOK


def midi(name):
    """'C4' -> 60, 'G#5' -> 80."""
    return 12 * (int(name[-1]) + 1) + NAMES.index(name[:-1])


def hz(m):
    """Equal temperament, A4 (MIDI 69) = 440 Hz."""
    return 440 * 2 ** ((m - 69) / 12)


def tone_x(f, clock=CPU):
    """sound.asm's X for frequency f: a flip every 12 + 5 X cycles."""
    x = round((clock / (2 * f) - TONE_FLIP) / 5)
    assert 1 <= x <= 255, f
    return x


def tone_flips(x, cycles):
    """Flips of tone X that fill `cycles`."""
    return round(cycles / (TONE_FLIP + 5 * x))


def half_period(f, turn, clock=CPU):
    """Half period of f in turns of `turn` cycles (0 for no note)."""
    return round(clock / (2 * f * turn)) if f else 0


def parse(text):
    """'A4:1 R:2 ...' -> [('A4', 1), ('R', 2), ...] (R: a rest)."""
    out = []
    for tok in text.split():
        name, n = tok.split(':')
        out.append((name, int(n)))
    return out


# duet.asm counts are whole numbers, so its tunes use just intonation: the
# scale of C whose periods are whole (C4 = 60 turns, a fifth of a semitone
# under concert pitch), plus the nearest counts for the sharps of D, E and
# A major. A note whose count would fall between two turns (F5, D6, C7...)
# is not available: melodies are written around them.
DUET_COUNTS = {
    'C2': 240, 'F2': 180, 'G2': 160, 'A2': 144, 'B2': 128,
    'C3': 120, 'D3': 108, 'E3': 96, 'F3': 90, 'F#3': 86, 'G3': 80, 'A3': 72,
    'C4': 60, 'D4': 54, 'E4': 48, 'F#4': 43, 'F4': 45, 'G4': 40, 'G#4': 38, 'A4': 36, 'B4': 32,
    'C5': 30, 'C#5': 29, 'D5': 27, 'E5': 24, 'G5': 20, 'G#5': 19, 'A5': 18, 'B5': 16,
    'C6': 15, 'E6': 12, 'G6': 10, 'A6': 9,
}


def cents_from_equal(note):
    """How far DUET_COUNTS[note] is from equal temperament (C4 = 60 turns)."""
    return 1200 * log2(60 / DUET_COUNTS[note]) - 100 * (midi(note) - 60)


# Pure thirds and sixths are up to 16 cents under the tempered ones, the low D
# of the scale (10/9) 18; a rounded sharp adds a few more. C#5 is the worst:
# 12 cents under a pure third above A, where 28 turns would be 49 over.
for _name in DUET_COUNTS:
    assert abs(cents_from_equal(_name)) < (42 if _name == 'C#5' else 24), (_name, cents_from_equal(_name))


def duet_encode(tune, tempo, clock=1_023_000):
    """tune: (melody, bass, beats); '-' is a silence -> duet events: melody
    count (0 = silence), bass count, slices; three zeros end the tune. Two
    equal melody notes in a row are parted by a short silence taken from the
    first."""
    out, at, done = [], 0.0, 0
    for i, (melody, bass, beats) in enumerate(tune):
        at += beats * 60.0 / tempo * clock / DUET_SLICE
        slices = round(at) - done
        done += slices
        assert 0 < slices < 256, (melody, beats)
        if melody == '-':
            out += [0, 1, slices]
            continue
        again = i + 1 < len(tune) and tune[i + 1][0] == melody
        if again:
            slices -= 2
        out += [DUET_COUNTS[melody], DUET_COUNTS[bass], slices]
        if again:
            out += [0, 1, 2]
    return out + [0, 0, 0]


def byte_block(label, data, per_line=18):
    """ca65 lines: 'label:', then '.byte a,b,...' rows."""
    return [label + ':'] + ['.byte ' + ','.join(map(str, data[i:i + per_line]))
                            for i in range(0, len(data), per_line)]
