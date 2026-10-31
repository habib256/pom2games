#!/usr/bin/env python3
"""AYS: a compact Mockingboard song format for games, its encoder/decoder
and the bit-exact reference player of dev/lib/apple2/aysong.asm.

    song = load_text(open('tune.ays.txt').read())   # or from_json(...)
    data = encode(song)                             # the bytes a game loads
    p = Player(data); frame = p.tick()              # one 50 Hz tick: the AY
                                                    # registers (14 a chip)
    python3 aysong.py tune.ays.txt -o TUNE.AYS      # binary
    python3 aysong.py tune.ays.txt --asm tune.inc   # ca65 .byte rows
    python3 aysong.py --demo --asm demo.inc         # the demo song

The asm player and Player() compute the same registers tick for tick
(dev/tests/test_aysong.py compares them). The format is documented in
dev/lib/apple2/AYSONG_FORMAT.md; the summary below is the reference.

FORMAT (version 1; every offset is from the song's first byte, little
endian; a song is relocatable and at most 64 KB)

  header, 20 bytes
    0  'A' 'Y' 'S'      magic                3  version = 1
    4  voices           3 (one AY) or 6 (two: voices 3-5 on the second chip)
    5  rows             rows of every pattern, 1..64
    6  speed            ticks per row, 1..255 (a tick = one ays_tick call)
    7  rate             ticks a second the song is written for (50; the
                        player does not read it: the caller's timer)
    8  order length     1..255 entries
    9  loop             order index played after the last entry; $FF: the
                        song stops (silence) after the last row
    10 instruments      1..15
    11 patterns         1..255
    12 order offset     the order list: one pattern number a byte
    14 pattern offset   the pattern table: a word a pattern -> a block of
                        `voices` words, each the offset of that voice's track
                        (tracks may be shared between patterns)
    16 instrument offset  the instrument table: a word an instrument (1 first)
    18 text offset      0 = none, else NUL-terminated strings: song name,
                        author, then one name an instrument (editor only)

  track: the rows of one voice in one pattern, a byte stream; each row is
  zero or more prefixes then one row byte
    $00-$5F  note 0..95 (C0..B7; note 57 = A4 = 440 Hz)      row byte
    $60      note off: the voice silent                       row byte
    $61-$6F  instrument 1..15 for the next notes              prefix
    $70      effect off                                       prefix
    $71-$77  effect 1..7, then its parameter byte             prefix
    $80-$BF  1..64 empty rows (hold: the note goes on)         row byte
    $C0-$FF  reserved
  A track holds exactly `rows` rows.

  effects (a voice has one; it runs every tick the voice is on, until the
  next note or effect prefix)
    1 arpeggio  $xy   note, note + x, note + y semitones, one a tick (the
                      sum capped at 95)
    2 slide up  p     slide -= p every tick (pitch up)
    3 slide down p    slide += p every tick (slide: 16 bits; the period
                      register = (table + slide) & $FFF, it wraps)
    4 fade      p     volume offset -1 on every p-th tick (down to -15)
    5 swell     p     volume offset +1 on every p-th tick (up to +15)
                      (p >= 1; the first step on the p-th tick)
    6 noise     p     the chip's noise period (R6) = p & 31, every tick
    7 env period p    the chip's envelope period: R12 = p, R11 = 0
  A note without an effect prefix on its row: effect none; it resets the
  slide, the volume offset and starts its instrument at its first tick.
  An effect prefix restarts the effect's counter (arpeggio step 0); on an
  empty row it replaces the effect and keeps the slide / volume offset.
  An instrument prefix selects the instrument of the following notes (a
  note reads the instrument table when it starts).

  instrument: a 4-byte header then the tick list (offsets in the block)
    0 end      4 + the bytes of tick data (5..254): just past the last tick
    1 loop     where the macro goes on after its last tick, 4..end-1 (the
               last tick's own offset: it holds)
    2 shape    envelope shape 0..15 written to R13 when a note starts,
               $FF = none
    3 period   envelope period (R12, R11 = 0) set with that shape
    then, a tick each: %XENT VVVV  V volume 0..15, T tone on, N noise on,
    E hardware envelope (volume register = $10), X = a second byte
    follows: the chip's noise period (bits 0-4) from this tick on.

PLAYER (per tick, what Player.tick() and ays_tick do)
  1. the row: the first tick after ays_init and every `speed` ticks later,
     every voice reads its row (a voice inside an empty run just counts it
     down); then the row advances; past the last row, the next order entry
     (the loop entry after the last one, or the end: silence, stopped).
  2. every voice, in order 0..voices-1: its effect, then its instrument
     tick, then its registers:
       on:  period = (table(note + arpeggio) + slide) & $FFF  -> R0-R5;
            volume = $10 if E, else clamp(V + offset, 0, 15) (0 if muted)
            mixer tone bit = not T, noise bit = not N (bits 6-7 = 0)
       off: period registers kept, volume 0, tone and noise bits set (off)
     the noise period and the envelope period/shape are the chip's: the
     last voice (in order) that set them this tick wins; they persist.
  3. the frame: R0..R13 of each chip; R13 = the shape on the tick a note
     with a shaped instrument starts, else $FF (= do not write R13: a
     write restarts the envelope).
  Period table: octave 0 (C0..B0) = round(1020484 / (16 f)), f in equal
  temperament from A4 = 440 Hz (dev/tools/audio/notes.py, the NTSC Apple
  II clock that drives the Mockingboard's AYs; a PAL machine, 1,015,657
  Hz, plays 0.47 % = 8 cents flat). Octave k = the octave 0 period >> k,
  rounded half up: (p + 2^(k-1)) >> k. C0 = 3901 ... B7 = 16.
  ays_init: registers 0 except R7 = $3F (all off) and R13 = $FF, every
  voice off with instrument 1, mute mask 0, order 0 row 0.
  ays_set_pos(order, row): the voices are silent (off) until their next
  note; instrument prefixes of the skipped rows are kept, the rest is not
  played; the next tick reads `row`.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notes  # noqa: E402

MAGIC = b'AYS'
VERSION = 1
HEADER = 20
OFF = 96                        # Cell.note: note off (None = empty / hold)
NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
FX_LETTERS = 'OAUDFSNE'         # effect 0..7 in the text format
FX_NAMES = ['off', 'arpeggio', 'slide up', 'slide down', 'fade', 'swell', 'noise', 'env period']

# Octave 0 periods, C0 (MIDI 12) .. B0, for the NTSC Apple II clock.
PERIODS = [round(notes.CPU / (16 * notes.hz(12 + i))) for i in range(12)]


def period(note):
    """The AY period of note 0..95 (the asm's table and shifts)."""
    octave, semi = divmod(note, 12)
    p = PERIODS[semi]
    if octave:
        y = p >> (octave - 1)
        p = (y >> 1) + (y & 1)
    return p


# ---------------------------------------------------------------- the model
@dataclass
class Tick:
    vol: int = 15               # 0..15
    tone: bool = True
    noise: bool = False
    env: bool = False           # hardware envelope (volume register $10)
    noise_period: int | None = None   # 0..31: the chip's R6 from this tick


@dataclass
class Instrument:
    ticks: list[Tick] = field(default_factory=lambda: [Tick()])
    loop: int | None = None     # tick index the macro loops to; None = hold the last
    env_shape: int | None = None   # 0..15: R13 at each note
    env_period: int = 0         # R12 with that shape
    name: str = ''


@dataclass
class Cell:
    note: int | None = None     # 0..95, OFF, or None (empty: hold)
    ins: int | None = None      # 1..15: instrument from this note on
    fx: int | None = None       # 0..7 (0 = effect off)
    param: int = 0


@dataclass
class Pattern:
    tracks: list[list[Cell]]    # [voice][row]


@dataclass
class Song:
    patterns: list[Pattern]
    instruments: list[Instrument]
    order: list[int]
    voices: int = 3
    rows: int = 64
    speed: int = 6
    rate: int = 50
    loop: int | None = 0        # order index after the end, None = stop
    name: str = ''
    author: str = ''


# ---------------------------------------------------------------- encoding
def _check(song):
    assert song.voices in (3, 6), 'voices: 3 or 6'
    assert 1 <= song.rows <= 64, 'rows: 1..64'
    assert 1 <= song.speed <= 255
    assert 1 <= len(song.order) <= 255 and 1 <= len(song.patterns) <= 255
    assert 1 <= len(song.instruments) <= 15, 'instruments: 1..15'
    assert all(0 <= p < len(song.patterns) for p in song.order)
    assert song.loop is None or 0 <= song.loop < len(song.order)
    for p in song.patterns:
        assert len(p.tracks) == song.voices and all(len(t) == song.rows for t in p.tracks)


def encode_track(cells):
    out = bytearray()
    run = 0

    def flush():
        nonlocal run
        while run:
            k = min(run, 64)
            out.append(0x80 + k - 1)
            run -= k
    for c in cells:
        if c.ins is None and c.fx is None and c.note is None:
            run += 1
            continue
        flush()
        if c.ins is not None:
            assert 1 <= c.ins <= 15
            out.append(0x60 + c.ins)
        if c.fx is not None:
            assert 0 <= c.fx <= 7
            out.append(0x70 + c.fx)
            if c.fx:
                assert 0 <= c.param <= 255
                assert c.fx not in (4, 5) or c.param, 'fade/swell: p >= 1'
                out.append(c.param)
        if c.note is None:
            run = 1
        else:
            assert 0 <= c.note <= OFF
            out.append(0x60 if c.note == OFF else c.note)
    flush()
    return bytes(out)


def encode_instrument(ins):
    data = bytearray()
    starts = []
    for t in ins.ticks:
        starts.append(len(data))
        assert 0 <= t.vol <= 15
        b = t.vol | (0x10 if t.tone else 0) | (0x20 if t.noise else 0) | (0x40 if t.env else 0)
        if t.noise_period is not None:
            data += bytes([b | 0x80, t.noise_period & 31])
        else:
            data.append(b)
    assert 1 <= len(data) <= 250
    loop = starts[-1] if ins.loop is None else starts[ins.loop]
    shape = 0xFF if ins.env_shape is None else ins.env_shape & 15
    return bytes([4 + len(data), 4 + loop, shape, ins.env_period & 255]) + data


def encode(song: Song) -> bytes:
    _check(song)
    body = bytearray()
    tracks = {}

    def place(blob):
        at = HEADER + len(body)
        body.extend(blob)
        return at
    order_at = place(bytes(song.order))
    track_at = []
    for p in song.patterns:          # tracks first (shared when identical)
        for t in p.tracks:
            b = encode_track(t)
            if b not in tracks:
                tracks[b] = place(b)
            track_at.append(tracks[b])
    blocks = []
    for i in range(len(song.patterns)):
        offs = track_at[i * song.voices:(i + 1) * song.voices]
        blocks.append(place(b''.join(o.to_bytes(2, 'little') for o in offs)))
    pat_at = place(b''.join(o.to_bytes(2, 'little') for o in blocks))
    ins_blobs = [place(encode_instrument(i)) for i in song.instruments]
    ins_at = place(b''.join(o.to_bytes(2, 'little') for o in ins_blobs))
    text_at = 0
    if song.name or song.author or any(i.name for i in song.instruments):
        strings = [song.name, song.author] + [i.name for i in song.instruments]
        text_at = place(b''.join(s.encode('ascii') + b'\0' for s in strings))
    head = MAGIC + bytes([VERSION, song.voices, song.rows, song.speed, song.rate, len(song.order),
                          0xFF if song.loop is None else song.loop, len(song.instruments),
                          len(song.patterns)])
    for o in (order_at, pat_at, ins_at, text_at):
        head += o.to_bytes(2, 'little')
    assert len(head) == HEADER
    return bytes(head + body)


def _w(d, at):
    return d[at] | d[at + 1] << 8


def decode_track(d, at, rows):
    cells = []
    while len(cells) < rows:
        c = Cell()
        while True:
            b = d[at]
            at += 1
            if 0x61 <= b <= 0x6F:
                c.ins = b - 0x60
            elif 0x70 <= b <= 0x77:
                c.fx = b - 0x70
                if c.fx:
                    c.param = d[at]
                    at += 1
            elif b < 0x60:
                c.note = b
                break
            elif b == 0x60:
                c.note = OFF
                break
            elif 0x80 <= b <= 0xBF:
                cells.append(c)
                cells += [Cell() for _ in range(b - 0x80)]
                c = None
                break
            else:
                raise ValueError(f'track byte ${b:02X}')
        if c is not None:
            cells.append(c)
    assert len(cells) == rows, 'a run past the pattern end'
    return cells


def decode(data: bytes) -> Song:
    d = bytes(data)
    assert d[:3] == MAGIC and d[3] == VERSION, 'not an AYS v1 song'
    voices, rows, speed, rate, nord, loop, nins, npat = d[4:12]
    order_at, pat_at, ins_at, text_at = (_w(d, 12 + 2 * i) for i in range(4))
    order = list(d[order_at:order_at + nord])
    patterns = []
    for p in range(npat):
        blk = _w(d, pat_at + 2 * p)
        patterns.append(Pattern([decode_track(d, _w(d, blk + 2 * v), rows) for v in range(voices)]))
    names = []
    if text_at:
        names = d[text_at:].split(b'\0')
    instruments = []
    for i in range(nins):
        at = _w(d, ins_at + 2 * i)
        n, lp, shape, eper = d[at:at + 4]
        n, lp = n - 4, lp - 4
        data_ = d[at + 4:at + 4 + n]
        ticks, starts, k = [], [], 0
        while k < n:
            starts.append(k)
            b = data_[k]
            t = Tick(b & 15, bool(b & 0x10), bool(b & 0x20), bool(b & 0x40))
            k += 1
            if b & 0x80:
                t.noise_period = data_[k] & 31
                k += 1
            ticks.append(t)
        li = starts.index(lp)
        instruments.append(Instrument(ticks, None if li == len(ticks) - 1 else li,
                                      None if shape == 0xFF else shape, eper,
                                      names[2 + i].decode() if len(names) > 2 + i else ''))
    return Song(patterns, instruments, order, voices, rows, speed, rate, None if loop == 0xFF else loop,
                names[0].decode() if names else '', names[1].decode() if len(names) > 1 else '')


# ---------------------------------------------------------------- the player
class _Voice:
    def __init__(self):
        self.ptr = 0        # track read offset
        self.wait = 0       # empty rows still to count
        self.ins = 1        # instrument for the next note
        self.on = False
        self.trig = False   # a note started this row (R13)
        self.note = 0
        self.ibase = 0      # instrument block offset (its header)
        self.ipos = 4       # its next tick, offset in the block
        self.fx = 0
        self.param = 0
        self.cnt = 0        # arpeggio step 0..2 / fade, swell ticks
        self.slide = 0      # period offset (16-bit two's complement)
        self.voff = 0       # volume offset -15..15


class Player:
    """Reads the encoded bytes like ays_tick: tick() -> the frame, 14
    registers a chip (28 for 6 voices: chip 2 = frame[14:28]). max_voices:
    the asm's AYSONG_VOICES (a 6-voice song under a 3-voice player: its
    first chip only)."""

    def __init__(self, data, max_voices=6):
        d = self.d = bytes(data)
        assert d[:3] == MAGIC and d[3] == VERSION
        self.voices, self.rows, self.speed = min(d[4], max_voices), d[5], d[6]
        self.nord, self.loop = d[8], d[9]
        self.order_at, self.pat_at, self.ins_at = _w(d, 12), _w(d, 14), _w(d, 16)
        self.chips = self.voices // 3
        self.mute = 0                   # ays_mute: bit v = voice v silent
        self.v = [_Voice() for _ in range(self.voices)]
        self.regs = []
        for _ in range(self.chips):
            r = [0] * 14
            r[7] = 0x3F
            r[13] = 0xFF
            self.regs.append(r)
        self.set_pos(0, 0)

    def pos(self):
        """ays_pos: (order index, row) of the next row to be read."""
        return self.order, self.row

    def set_pos(self, order, row):
        """ays_set_pos (also ays_init's start): silent voices, `row` rows
        skipped (instrument prefixes kept), the next tick reads `row`."""
        self.order = order
        self._pattern()
        for v in self.v:
            v.on = False
        self.row = 0
        while self.row < row:
            self._read_row(skip=True)
            self.row += 1
        self.count = 1
        self.playing = True

    def stop(self):
        """ays_stop: every voice off, no more rows (the frames go on: silent)."""
        self.playing = False
        for v in self.v:
            v.on = False

    def _pattern(self):
        d = self.d
        blk = _w(d, self.pat_at + 2 * d[self.order_at + self.order])
        for i, v in enumerate(self.v):
            v.ptr = _w(d, blk + 2 * i)
            v.wait = 0

    def _read_row(self, skip=False):
        d = self.d
        for v in self.v:
            v.trig = False
            if v.wait:
                v.wait -= 1
                continue
            newfx = False
            while True:
                b = d[v.ptr]
                v.ptr += 1
                if b >= 0x80:                   # empty rows
                    v.wait = b - 0x80
                    break
                if b < 0x60:                    # a note
                    if not skip:
                        if not newfx:
                            v.fx = 0
                        v.note, v.on, v.trig = b, True, True
                        v.ibase = _w(d, self.ins_at + 2 * (v.ins - 1))
                        v.ipos, v.slide, v.voff = 4, 0, 0
                    break
                if b == 0x60:                   # note off
                    v.on = False
                    break
                if b < 0x70:
                    v.ins = b - 0x60
                    continue
                fx, par = b - 0x70, 0
                if fx:
                    par = d[v.ptr]
                    v.ptr += 1
                if not skip:
                    v.fx, v.param, v.cnt = fx, par, 0
                    newfx = True

    def tick(self):
        """One tick: the row if it is due, then every voice -> the frame."""
        for r in self.regs:
            r[13] = 0xFF
        if self.playing:
            self.count -= 1
            if not self.count:
                self.count = self.speed
                if self.row == self.rows:       # the next order entry
                    self.row = 0
                    self.order += 1
                    if self.order == self.nord:
                        self.order = self.loop
                        if self.loop == 0xFF:
                            self.order = 0
                            self.stop()
                    if self.playing:
                        self._pattern()
                if self.playing:
                    self._read_row()
                    self.row += 1
        d = self.d
        for i, v in enumerate(self.v):
            r = self.regs[i // 3]
            c = i % 3
            if not v.on:
                r[8 + c] = 0
                r[7] |= 9 << c
                continue
            arp = 0                             # the effect
            fx, p = v.fx, v.param
            if fx == 1:
                arp = (0, p >> 4, p & 15)[v.cnt]
                v.cnt = (v.cnt + 1) % 3
            elif fx == 2:
                v.slide = (v.slide - p) & 0xFFFF
            elif fx == 3:
                v.slide = (v.slide + p) & 0xFFFF
            elif fx in (4, 5):
                v.cnt += 1
                if v.cnt >= p:
                    v.cnt = 0
                    v.voff = max(v.voff - 1, -15) if fx == 4 else min(v.voff + 1, 15)
            elif fx == 6:
                r[6] = p & 31
            elif fx == 7:
                r[11], r[12] = 0, p
            ib = v.ibase                        # the instrument
            b = d[ib + v.ipos]
            v.ipos += 1
            if b & 0x80:
                r[6] = d[ib + v.ipos] & 31
                v.ipos += 1
            if v.ipos >= d[ib]:
                v.ipos = d[ib + 1]
            if v.trig:
                v.trig = False
                if d[ib + 2] != 0xFF:
                    r[11], r[12], r[13] = 0, d[ib + 3], d[ib + 2]
            per = (period(min(v.note + arp, 95)) + v.slide) & 0xFFF
            r[2 * c], r[2 * c + 1] = per & 255, per >> 8
            if self.mute >> i & 1:
                vol = 0
            elif b & 0x40:
                vol = 0x10
            else:
                vol = min(max((b & 15) + v.voff, 0), 15)
            r[8 + c] = vol
            mix = r[7] & ~(9 << c)
            if not b & 0x10:
                mix |= 1 << c
            if not b & 0x20:
                mix |= 8 << c
            r[7] = mix
        return [x for r in self.regs for x in r]


# ---------------------------------------------------------------- text import
def note_name(n):
    if n is None:
        return '---'
    if n == OFF:
        return '==='
    return NOTE_NAMES[n % 12] + str(n // 12)


def parse_note(tok):
    if tok in ('---', '...'):
        return None
    if tok in ('===', 'OFF', 'off'):
        return OFF
    name = tok[:2].upper()
    n = NOTE_NAMES.index(name if name[1] in '-#' else name[0] + '-') + 12 * int(tok[-1])
    assert 0 <= n <= 95, tok
    return n


def parse_tick(tok):
    """'15t', '12tn/5', '0', 'e' (envelope), volume decimal 0..15."""
    np_ = None
    if '/' in tok:
        tok, np_ = tok.split('/')
        np_ = int(np_)
    digits = ''.join(ch for ch in tok if ch.isdigit())
    flags = tok[len(digits):]
    assert set(flags) <= set('tne'), tok
    return Tick(int(digits or 0), 't' in flags, 'n' in flags, 'e' in flags, np_)


def load_text(text):
    """The hand-written song format:

        song "Name" "Author" voices 3 rows 16 speed 6 loop 0
        order 0 1 0 2
        ins 1 "lead" shape 10 period 3: 15t 13t | 12t 11t
        pattern 0
        C-4 1 .   | --- . .   | C-2 2 N05
        --- . A37 | ...

    One line a row, voices split by '|'; a cell = note (C-4, C#4, ---
    empty, === off), instrument (1-F hex, '.'), effect (letter + 2 hex
    digits: O off, A arpeggio, U slide up, D slide down, F fade, S swell,
    N noise, E env period; '.' none). Missing cells/rows are empty. ';'
    starts a comment. `loop -` = stop at the end. Instrument ticks: volume
    + t (tone) n (noise) e (envelope) [/noise period]; '|' marks the loop
    tick (none: the last tick holds)."""
    import shlex
    head = {}
    order, ins, pats = [], {}, {}
    cur = None
    for raw in text.splitlines():
        line = raw.split(';', 1)[0].rstrip()
        if not line.strip():
            continue
        word = line.split()[0]
        if word == 'song':
            t = shlex.split(line)[1:]
            names = []
            while t and not t[0] in ('voices', 'rows', 'speed', 'loop', 'rate'):
                names.append(t.pop(0))
            head['name'] = names[0] if names else ''
            head['author'] = names[1] if len(names) > 1 else ''
            for k, v in zip(t[::2], t[1::2]):
                head[k] = None if v == '-' else int(v)
            cur = None
        elif word == 'order':
            order += [int(x) for x in line.split()[1:]]
            cur = None
        elif word == 'ins':
            left, ticks = line.split(':', 1)
            t = shlex.split(left)[1:]
            num = int(t.pop(0))
            i = Instrument(ticks=[])
            if t and t[0] not in ('shape', 'period'):
                i.name = t.pop(0)
            for k, v in zip(t[::2], t[1::2]):
                if k == 'shape':
                    i.env_shape = int(v)
                elif k == 'period':
                    i.env_period = int(v)
            for tok in ticks.split():
                if tok == '|':
                    i.loop = len(i.ticks)
                else:
                    i.ticks.append(parse_tick(tok))
            ins[num] = i
            cur = None
        elif word == 'pattern':
            cur = pats.setdefault(int(line.split()[1]), [])
        else:
            assert cur is not None, f'row outside a pattern: {raw}'
            cur.append(line)
    voices = head.get('voices', 3)
    rows = head.get('rows', 64)
    patterns = []
    for k in range(max(pats) + 1):
        tracks = [[Cell() for _ in range(rows)] for _ in range(voices)]
        for r, line in enumerate(pats.get(k, [])):
            assert r < rows, f'pattern {k}: more than {rows} rows'
            for v, cell in enumerate(line.split('|')):
                toks = cell.split()
                if not toks:
                    continue
                c = tracks[v][r]
                c.note = parse_note(toks[0])
                if len(toks) > 1 and toks[1] != '.':
                    c.ins = int(toks[1], 16)
                if len(toks) > 2 and toks[2] != '.':
                    c.fx = FX_LETTERS.index(toks[2][0].upper())
                    c.param = int(toks[2][1:] or '0', 16)
        patterns.append(Pattern(tracks))
    instruments = [ins[k] for k in range(1, max(ins) + 1)]
    return Song(patterns, instruments, order or [0], voices, rows, head.get('speed', 6), head.get('rate', 50),
                head.get('loop', 0), head.get('name', ''), head.get('author', ''))


def to_json(song):
    return json.dumps(asdict(song), indent=1)


def from_json(text):
    j = json.loads(text)
    ins = [Instrument([Tick(**t) for t in i.pop('ticks')], **i) for i in j.pop('instruments')]
    pats = [Pattern([[Cell(**c) for c in t] for t in p['tracks']]) for p in j.pop('patterns')]
    return Song(pats, ins, **j)


def asm_rows(label, data):
    return notes.byte_block(label, data)


# ---------------------------------------------------------------- the demo
DEMO = ''';AYS demo (original, 2026-10-31): a short loop for the tests and the editor.
song "AYS demo" "pom2games" voices 3 rows 16 speed 5 loop 1
order 0 1 2 1 3
ins 1 "lead" : 13t 15t 14t 13t | 12t 12t 11t 12t
ins 2 "bass" : 15t 14t 12t 11t 10t
ins 3 "kick" : 15tn/2 13t 10t 6t 2t 0
ins 4 "hat" : 9n/1 6n 3n 0
ins 5 "buzz" shape 10 period 2: e
ins 6 "pad" : 4t 6t 8t 9t | 10t 9t
pattern 0
C-4 1 .   | C-2 2 .   | C-3 3 .
---       | ---       | ---
E-4       | ---       | --- 4
---       | C-3 2     | ---
G-4       | G-2       | C-3 3
---       | ---       | ---
C-5 . A47 | ---       | --- 4
---       | G-2       | ---
B-4       | A#2       | C-3 3
---       | ---       | ---
G-4 . O00 | ---       | --- 4
---       | A#2       | ---
E-4 . F01 | F-2       | C-3 3
---       | ---       | --- 4
===       | F-2       | C-3 3
---       | ===       | --- 4
pattern 1
A-3 6 .   | A-1 2 .   | C-3 3
---       | ---       | --- 4
C-4 6     | ---       | C-3 3
---       | A-2       | --- 4
E-4 1 U02 | ---       | C-3 3
---       | ---       | --- 4 N03
D-4 . D02 | G-1       | C-3 3
---       | ---       | --- 4
C-4       | G-2       | C-3 3
---       | ---       | --- 4
B-3 . S01 | ---       | C-3 3
---       | E-2       | --- 4
G#3       | ---       | C-3 3
---       | E-1       | --- 4
A-3 . F02 | ---       | C-3 3
---       | ===       | C-3 3
pattern 2
C-2 5 E03 | C-4 1 A37 | C-3 3
---       | ---       | ---
---       | ---       | --- 4
---       | ---       | ---
D#2       | D#4 . A37 | C-3 3
---       | ---       | ---
---       | ---       | --- 4
===       | ---       | ---
pattern 3
C-4 1 .   | E-4 6     | G-4 6
---       | ---       | ---
---       | ---       | ---
---       | ---       | ---
---       | ---       | ---
---       | ---       | ---
---       | ---       | ---
---       | ---       | ---
--- . F01 | --- . F01 | --- . F01
'''


def demo():
    return load_text(DEMO)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('song', nargs='?', help='a text song (.txt) or JSON (.json); --demo for the demo')
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('-o', '--out', help='binary AYS file')
    ap.add_argument('--asm', help='ca65 include: LABEL then .byte rows')
    ap.add_argument('--label', default='ays_song')
    ap.add_argument('--json', help='write the song as JSON')
    ap.add_argument('--frames', type=int, default=0, help='print N ticks of registers')
    a = ap.parse_args(argv)
    if a.demo:
        song = demo()
    else:
        text = Path(a.song).read_text()
        song = from_json(text) if a.song.endswith('.json') else load_text(text)
    data = encode(song)
    assert encode(decode(data)) == data
    if a.out:
        Path(a.out).write_bytes(data)
    if a.asm:
        Path(a.asm).write_text(f'; Generated by dev/tools/audio/aysong.py -- do not edit.\n'
                               f'; {song.name or "song"}: {len(data)} bytes, AYS v{VERSION}\n'
                               + '\n'.join(asm_rows(a.label, data)) + '\n')
    if a.json:
        Path(a.json).write_text(to_json(song))
    p = Player(data)
    for k in range(a.frames):
        print(k, ' '.join(f'{x:02X}' for x in p.tick()))
    print(f'{len(data)} bytes, {song.voices} voices, {len(song.patterns)} patterns, '
          f'{len(song.order)} orders, {len(song.instruments)} instruments', file=sys.stderr)


if __name__ == '__main__':
    main()
