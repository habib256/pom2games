#!/usr/bin/env python3
"""Two-voice tunes for the one-bit speaker player (src/duet.inc, sound.s play_tune).

An event is 3 bytes: melody count (0 = silence), bass count, slices. A count
is a half period in turns of the player's loop (33 cycles); a slice is 255
turns, about 8.3 ms. A zero third byte ends the tune.

Counts are whole numbers, so the tunes use just intonation: the scale of C
whose periods are whole (C4 = 60 turns, a fifth of a semitone under concert
pitch), plus the nearest counts for the sharps of D, E and A major. A note
whose count would fall between two turns (F5, D6, C7...) is not available:
the melodies are written around them."""
from math import log2
from pathlib import Path
CLOCK = 1023000
TURN, TURNS, LOOK = 33, 255, 34
SLICE = TURNS * TURN + LOOK

COUNTS = {
    'C2': 240, 'F2': 180, 'G2': 160, 'A2': 144, 'B2': 128,
    'C3': 120, 'D3': 108, 'E3': 96, 'F3': 90, 'F#3': 86, 'G3': 80, 'A3': 72,
    'C4': 60, 'D4': 54, 'E4': 48, 'F#4': 43, 'F4': 45, 'G4': 40, 'G#4': 38, 'A4': 36, 'B4': 32,
    'C5': 30, 'C#5': 29, 'D5': 27, 'E5': 24, 'G5': 20, 'G#5': 19, 'A5': 18, 'B5': 16,
    'C6': 15, 'E6': 12, 'G6': 10, 'A6': 9,
}
SEMITONES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

def cents_from_equal(note):
    """How far the count is from equal temperament, with C4 = 60 turns."""
    semis = SEMITONES[note[0]] + note.count('#') + 12 * (int(note[-1]) - 4)
    return 1200 * log2(60 / COUNTS[note]) - 100 * semis

# Pure thirds and sixths are up to 16 cents under the tempered ones, the low D
# of the scale (10/9) 18; a rounded sharp adds a few more. C#5 is the worst:
# 12 cents under a pure third above A, where 28 turns would be 49 over.
for name in COUNTS:
    assert abs(cents_from_equal(name)) < (42 if name == 'C#5' else 24), (name, cents_from_equal(name))

def encode(tune, tempo):
    """tune: (melody, bass, beats); '-' is a silence. Two equal melody notes
    in a row are parted by a short silence taken from the first."""
    out, at, done = [], 0.0, 0
    for i, (melody, bass, beats) in enumerate(tune):
        at += beats * 60.0 / tempo * CLOCK / SLICE
        slices = round(at) - done
        done += slices
        assert 0 < slices < 256, (melody, beats)
        if melody == '-':
            out += [0, 1, slices]
            continue
        again = i + 1 < len(tune) and tune[i + 1][0] == melody
        if again:
            slices -= 2
        out += [COUNTS[melody], COUNTS[bass], slices]
        if again:
            out += [0, 1, 2]
    return out + [0, 0, 0]

_ = '-'
# Title theme (about 5 s): the I-vi-IV-V progression in rising arpeggios over
# root and fifth, then a short tune that lands on the tonic while the bass
# walks up to the dominant.
TITLE = [('C5', 'C3', .5), ('E5', 'C3', .5), ('G5', 'G2', .5), ('C6', 'G2', .5),
         ('A4', 'A2', .5), ('C5', 'A2', .5), ('E5', 'E3', .5), ('A5', 'E3', .5),
         ('F4', 'F2', .5), ('A4', 'F2', .5), ('C5', 'C3', .5), ('A5', 'C3', .5),
         ('G4', 'G2', .5), ('B4', 'G2', .5), ('D5', 'D3', .5), ('G5', 'B2', .5),
         ('E5', 'C3', 1), ('D5', 'D3', .5), ('C5', 'E3', .5), ('D5', 'F3', 1), ('G4', 'G2', 1), ('C5', 'C3', 2)]
# Sector cleared: ten endings, one for each sector of a decade, a little over
# two seconds each. The roots climb the scale of C (C, D minor, E minor, F, G,
# A minor), then come the brighter D, E and A major, and the tenth sector of
# a decade gets a longer fanfare. Each has its own cadence in the bass.
JINGLES = [
    # 1: C major, I - V - IV V - I.
    (200, [('C5', 'C3', .5), ('E5', 'C3', .5), ('G5', 'E3', .5), ('C6', 'C4', .5),
           ('B5', 'G3', .5), ('G5', 'G3', .5), ('E5', 'C3', .5), ('G5', 'E3', .5),
           ('A5', 'F3', .5), ('B5', 'G3', .5), ('C6', 'C3', 2.5)]),
    # 2: D minor, down through C and A minor.
    (200, [('D4', 'D3', .5), ('F4', 'D3', .5), ('A4', 'F3', .5), ('D5', 'D3', .5),
           ('C5', 'C3', .5), ('E5', 'C3', .5), ('C5', 'E3', .5), ('G4', 'C3', .5),
           ('A4', 'A2', .5), ('C5', 'A2', .5), ('D5', 'D3', 2.5)]),
    # 3: E minor, a sweep up the chord, then G, C and back.
    (200, [('E4', 'E3', .25), ('G4', 'E3', .25), ('B4', 'E3', .25), ('E5', 'E3', .25), ('G5', 'E3', .5), ('E5', 'E3', .5),
           ('D5', 'D3', .5), ('B4', 'G3', .5), ('C5', 'C3', .5), ('E5', 'C3', .5),
           ('A4', 'A2', .5), ('B4', 'G2', .5), ('E5', 'E3', 2.5)]),
    # 4: F major, I - V - I with the fifth on top.
    (200, [('F4', 'F3', .25), ('A4', 'F3', .25), ('C5', 'F3', .25), ('D5', 'F3', .25), ('C5', 'A2', .5), ('A5', 'F3', .5),
           ('G5', 'C3', .5), ('E5', 'C3', .5), ('G5', 'E3', .5), ('A5', 'F3', .5), ('G5', 'C3', .5),
           ('C6', 'F2', 2.5)]),
    # 5: G major, up the chord and down the scale from the fourth.
    (200, [('G4', 'G3', .25), ('B4', 'G3', .25), ('D5', 'D4', .25), ('G5', 'G3', .25), ('B5', 'G3', .5), ('G5', 'B2', .5),
           ('E5', 'C3', .5), ('G5', 'E3', .5), ('C6', 'C3', .5),
           ('B5', 'G3', .5), ('A5', 'D3', .5), ('G5', 'G2', 2.5)]),
    # 6: A minor, with the major dominant before the last note.
    (200, [('A4', 'A3', .25), ('C5', 'A3', .25), ('E5', 'A3', .25), ('A5', 'A3', .25), ('C6', 'A3', .5), ('A5', 'A3', .5),
           ('G5', 'C3', .5), ('E5', 'C3', .5), ('D5', 'D3', .5), ('B5', 'E3', .5), ('G#5', 'E3', .5),
           ('A5', 'A2', 2.5)]),
    # 7: D major, I - IV - V - I.
    (200, [('D4', 'D3', .25), ('F#4', 'D3', .25), ('A4', 'F#3', .25), ('D5', 'D3', .25), ('A4', 'A3', .5), ('D5', 'D3', .5),
           ('B4', 'G3', .5), ('D5', 'D3', .5), ('E5', 'A2', .5), ('C#5', 'A2', .5),
           ('D5', 'D3', .5), ('A5', 'D3', 2.5)]),
    # 8: E major, a plagal close up to the high E.
    (200, [('E4', 'E3', .25), ('G#4', 'E3', .25), ('B4', 'E3', .25), ('E5', 'E3', .25), ('G#5', 'E3', .5), ('E5', 'E3', .5),
           ('A4', 'A2', .5), ('C#5', 'A2', .5), ('E5', 'A2', .5), ('B5', 'B2', .5), ('G#5', 'E3', .5),
           ('E6', 'E3', 2.5)]),
    # 9: A minor turns major and climbs two octaves.
    (200, [('A4', 'A3', .25), ('C5', 'A3', .25), ('E5', 'A3', .25), ('A5', 'A3', .5), (_, _, .25),
           ('A4', 'A2', .25), ('C#5', 'A2', .25), ('E5', 'E3', .25), ('A5', 'A3', .25),
           ('B5', 'E3', .5), ('G#5', 'E3', .5), ('A5', 'A2', .25), ('E6', 'E3', .25), ('A6', 'A2', 2.5)]),
    # 10: the decade is done: a call on one note, the scale down and back,
    # and the chord up to the top over a held C.
    (200, [('C5', 'C3', .25), ('C5', 'C3', .25), ('C5', 'C3', .5), ('E5', 'C3', .5), ('G5', 'E3', .5),
           ('C6', 'E3', 1), ('B5', 'G3', .5), ('A5', 'F3', .5),
           ('G5', 'E3', 1), ('E5', 'C3', .5), ('G5', 'G2', .5),
           ('A5', 'F2', .5), ('B5', 'G2', .5),
           ('C6', 'C3', .5), ('E6', 'C3', .5), ('G6', 'C3', .5), ('C6', 'C2', 2.5)]),
]
# All sixty sectors: a fanfare (about 8 s).
FANFARE = [('G4', 'G2', .5), ('G4', 'G2', .5), ('G4', 'G2', .5), ('C5', 'C3', 2), (_, _, .5),
           ('E5', 'C3', .5), ('D5', 'F3', .5), ('C5', 'E3', .5), ('E5', 'C3', .5), ('G5', 'G2', 2), (_, _, .5),
           ('A5', 'F2', .5), ('G5', 'C3', .5), ('E5', 'C3', .5), ('G5', 'E3', .5), ('D5', 'F3', .5), ('E5', 'G2', .5),
           ('C5', 'C3', 2), (_, _, .5),
           ('C5', 'C3', .25), ('E5', 'C3', .25), ('G5', 'C3', .25), ('C6', 'C3', .25), ('E6', 'C3', .25),
           ('G6', 'C3', .25), ('C6', 'C2', 3)]

def block(label, data):
    return [label + ':'] + ['.byte ' + ','.join(map(str, data[i:i + 18])) for i in range(0, len(data), 18)]

root = Path(__file__).resolve().parents[1] / 'src'
# Title theme and jingles live in the AUX bank after the font (startup.s
# copies them; play_tune reads them there); the fanfare is in the overlay.
data, offsets = encode(TITLE, 180), ['TUNE_TITLE_OFS = 0']
for d, (tempo, jingle) in enumerate(JINGLES):
    offsets.append('TUNE_JINGLE%d_OFS = %d' % (d, len(data)))
    data += encode(jingle, tempo)
offsets.append('TUNES_SIZE = %d' % len(data))
aux = block('tunes_aux', data)
for name, lines in (('music_aux.inc', aux), ('music_offsets.inc', offsets),
                    ('music_fanfare.inc', block('_tune_fanfare', encode(FANFARE, 200)))):
    text = '; Generated by tools/generate_music.py. GPL-3.0.\n' + '\n'.join(lines) + '\n'
    path = root / name
    if not path.exists() or path.read_text() != text:
        path.write_text(text)
