#!/usr/bin/env python3
"""PT3 (Vortex Tracker II) reference player: the semantics of
dev/lib/apple2/pt3 (Vince Weaver's pt3_lib 0.5, the Apple II port of the
Bulba / Ay_Emul player), tick for tick, register for register.

    p = PT3Player(open('song.pt3', 'rb').read())
    frame = p.tick()        # one tick: R0..R13 of the AY (R13 = $FF: no write)
    python3 pt3play.py SONG.pt3 [--frames N] [--info]

Module layout (offsets from the file's first byte, words little endian)
  $00  "ProTracker 3.x compilation of " title(32) " by " author(32)
  $0D  version digit ('0'-'8'; anything else = 6)
  $63  frequency table: 0 PT, 1 ST, 2 ASM, 3+ REAL (the 3.4+ tables)
  $64  speed (ticks a line)     $65 positions     $66 loop position
  $67  pattern table (a pattern = 3 words: the channel A, B, C streams)
  $69  32 sample words          $A9 16 ornament words
  $C9  positions: pattern * 3 each, $FF ends
  sample:   loop, length, then 4 bytes a tick (b0, b1, tone offset word)
  ornament: loop, length, then one signed semitone offset a tick
Channel stream (a line: commands, then one of the line-ending bytes)
  $00     end of the pattern (all three channels: pt3_lib counts three)
  $01-$0F effect number (its parameters follow the line-ending byte)
  $10     envelope off, sample = next/2    $1x: envelope type x, period
          hi, lo, sample = next/2
  $20-$3F noise period base (cmd - $20)    $40-$4F ornament
  $50-$AF note 0..95 (ends the line)       $B0 envelope off
  $B1 n   length: decode every n lines     $B2-$BF envelope type x-1, hi, lo
  $C0     note off (ends the line)         $C1-$CF channel volume
  $D0     empty (ends the line)            $D1-$EF sample 1..31
  $Fx s   envelope off, ornament x, sample s/2
Effects 1 tone slide (delay, step word), 2 portamento (delay, 2 skipped
bytes, step word), 3 sample position, 4 ornament position, 5 vibrato (on,
off delays), 8 envelope slide (delay, step word), 9 speed.

pt3_lib's behaviour (modelled, also where it differs from Vortex):
  - no 1.77 MHz conversion of the tone and envelope periods (pt3.s
    default; convert=True models PT3_FREQ_CONVERSION = 1: * 9/16), but
    the noise period is always converted: R6 = (9 n) >> 4 (its .ifndef
    tests PT3_DISABLE_ENABLE_FREQ_CONVERSION, which nothing defines);
  - a pattern ends at line 64 or when the three channels have read $00;
  - the 3.3/3.4 vs 3.5+ volume tables and the version >= 6 portamento
    (keeps the previous slide) by the version digit; the four 3.4+ note
    tables only;
  - envelope slide down from a sample adds one more (the asm's carry);
  - amplitude slide up from -1 to 0 gives amplitude 0 that tick;
  - the vibrato (effect 5) counter is never stored back in the
    non-zero-page build pt3.s uses (zp=False): an on/off delay of 1
    toggles the channel every tick, a longer one never does (zp=True:
    the PT3_USE_ZERO_PAGE build, the real vibrato).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------- tables
BASE = {
    0: ([0x0C, 0x0B, 0x0A, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06],
        [0x22, 0x73, 0xCF, 0x33, 0xA1, 0x17, 0x94, 0x19, 0xA4, 0x37, 0xCF, 0x6D]),
    1: ([0x0E, 0x0E, 0x0D, 0x0C, 0x0B, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07],
        [0xF8, 0x10, 0x60, 0x80, 0xD8, 0x28, 0x88, 0xF0, 0x60, 0xE0, 0x58, 0xE0]),
    2: ([0x0D, 0x0C, 0x0B, 0x0A, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06],
        [0x10, 0x55, 0xA4, 0xFC, 0x5F, 0xCA, 0x3D, 0xB8, 0x3B, 0xC5, 0x55, 0xEC]),
    3: ([0x0C, 0x0C, 0x0B, 0x0A, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06],   # (base2 high, [0]-1)
        [0xDA, 0x22, 0x73, 0xCF, 0x33, 0xA1, 0x17, 0x94, 0x19, 0xA4, 0x37, 0xCF]),
}
ADJUST = {
    0: [0x40, 0xe6, 0x9c, 0x66, 0x40, 0x2c, 0x20, 0x30, 0x48, 0x6c, 0x1c, 0x5a],
    2: [0x20, 0xa8, 0x40, 0xf8, 0xbc, 0x90, 0x78, 0x70, 0x74, 0x08, 0x2a, 0x50],
    3: [0xB4, 0x40, 0xe6, 0x9c, 0x66, 0x40, 0x2c, 0x20, 0x30, 0x48, 0x6c, 0x1c],
}
TABLE_NAMES = ['PT', 'ST', 'ASM', 'REAL']
# The clock each table is written for (what the composer heard).
NATIVE_CLOCK = {0: 1_773_400, 1: 2_000_000, 2: 1_773_400, 3: 1_773_400}


def note_table(n):
    """The 96 periods pt3_init_song builds for frequency table n (0..3)."""
    n = min(n, 3)
    hi, lo = BASE[n]
    t = [hi[i] << 8 | lo[i] for i in range(12)] + [0] * 84
    for i in range(84):
        t[i + 12] = t[i] >> 1
    if n in ADJUST:
        for x, bits in enumerate(ADJUST[n]):
            for k in range(8):
                if bits >> k & 1:
                    v = t[x + 12 * k]
                    t[x + 12 * k] = (v & 0xFF00) | ((v + 1) & 0xFF)   # (inc low only)
    else:
        t[23] = (t[23] & 0xFF00) | 0xFD
        t[46] = (t[46] & 0xFF00) | ((t[46] - 1) & 0xFF)
    return t


def volume_table(v35):
    """VolTableCreator (Ivan Roshin's, as the 6502 runs it): 16 x 16,
    [channel volume][sample amplitude]. v35: the 3.5+ table."""
    t = [0] * 256
    d = 0
    if v35:
        l, e, rol = 0x11, 0x00, True
    else:
        l, e, rol = 0x10, 0x10, False
    y = x = 16
    while True:
        s = l + e
        e, c = s & 0xFF, s >> 8
        s = d + c
        d, c = s & 0xFF, s >> 8
        s = 0xFF + c
        c = s >> 8
        h = lo = (s & 0xFF) ^ 0xFF
        while True:
            if rol:
                c = lo >> 7
            s = h + c
            t[y], c = s & 0xFF, s >> 8
            y += 1
            s = lo + e + c
            lo, c = s & 0xFF, s >> 8
            s = h + d + c
            h, c = s & 0xFF, s >> 8
            x = (x + 1) & 0xFF
            if not x & 15:
                break
        if e == 0x77:
            e += 1
        if not x:
            break
    return t


def s8(v):
    v &= 0xFF
    return v - 256 if v & 0x80 else v


def s16(v):
    v &= 0xFFFF
    return v - 65536 if v & 0x8000 else v


def _sbc(a, b, c):
    """6502 SBC: (result, carry, overflow)."""
    r = a - b - (1 - c)
    res = r & 0xFF
    v = bool(((a ^ b) & (a ^ res)) & 0x80)
    return res, int(r >= 0), v


# ---------------------------------------------------------------- the module
class Module:
    """The header of a .pt3 and its readers (bytes past the end read 0)."""

    def __init__(self, data):
        self.d = bytes(data)
        d = self.d
        assert len(d) > 0xCA, 'not a PT3 module'
        v = d[0x0D] - 0x30
        self.version = v if 0 <= v < 9 else 6
        self.table = d[0x63]
        self.speed = d[0x64]
        self.npos = d[0x65]
        self.loop = d[0x66]
        self.pattern_at = self.w(0x67)
        self.title = d[0x1E:0x3E].decode('latin-1').strip()
        self.author = d[0x42:0x62].decode('latin-1').strip() if d[0x3E:0x42] == b' by ' else ''
        self.positions = []
        k = 0
        while self.b(0xC9 + k) != 0xFF and k < 256:
            self.positions.append(self.b(0xC9 + k) // 3)
            k += 1

    def b(self, at):
        at &= 0xFFFF
        return self.d[at] if at < len(self.d) else 0

    def w(self, at):
        return self.b(at) | self.b(at + 1) << 8

    def sample_at(self, s):
        return self.w(0x69 + ((2 * s) & 0xFF))

    def ornament_at(self, o):
        return self.w(0xA9 + ((2 * o) & 0xFF))

    def sample(self, s):
        """(loop, length, [(b0, b1, tone)...]) of sample s."""
        at = self.sample_at(s)
        lp, ln = self.b(at), self.b(at + 1)
        return lp, ln, [(self.b(at + 2 + 4 * k), self.b(at + 3 + 4 * k), self.w(at + 4 + 4 * k)) for k in range(ln)]

    def ornament(self, o):
        at = self.ornament_at(o)
        lp, ln = self.b(at), self.b(at + 1)
        return lp, ln, [s8(self.b(at + 2 + k)) for k in range(ln)]


# ---------------------------------------------------------------- a channel
class Chan:
    FIELDS = ('volume', 'sliding', 'enabled', 'env_enabled', 'sample_ptr', 'sample_loop', 'sample_len', 'tone',
              'amplitude', 'note', 'len', 'len_count', 'addr', 'orn_ptr', 'orn_loop', 'orn_len', 'onoff',
              'acc', 'slide_count', 'orn_pos', 'sample_pos', 'env_sliding', 'noise_sliding', 'amp_sliding',
              'onoff_delay', 'offon_delay', 'step', 'slide_delay', 'simple_gliss', 'slide_to_note', 'delta')

    def __init__(self):
        for f in self.FIELDS:
            setattr(self, f, 0)
        self.volume = 15
        self.sample_no = 1          # (bookkeeping for the importer, not the asm)
        self.orn_no = 0


def sample_tick(m, ch, vt, out):
    """The sample part of calculate_note (amplitude, envelope bit, noise and
    envelope offsets, mixer bits), then the sample and ornament positions
    advance. out: the player's frame state dict (env_add, noise_add, mixer).
    Returns (b0, b1, tone offset word)."""
    pos = ch.sample_pos
    sp = ch.sample_ptr + ((pos << 2) & 0xFF)
    b0, b1 = m.b(sp), m.b(sp + 1)
    c = (pos >> 6) & 1
    s = m.b(sp + 2) + (ch.acc & 0xFF) + c
    tl, c = s & 0xFF, s >> 8
    s = m.b(sp + 3) + (ch.acc >> 8) + c
    th = s & 0xFF
    toff = th << 8 | tl
    if b1 & 0x40:
        ch.acc = toff
    # amplitude (the A register's path through amp_slide_up / _down)
    a = b1 & 15
    if b0 & 0x80:
        y = a
        sl = ch.amp_sliding & 0xFF
        if b0 & 0x40:
            r, cy, v = _sbc(sl, 15, 1)
            if not ((r >> 7) ^ v):              # sliding >= 15: skip
                a = r
            else:
                sl = (sl + 1) & 0xFF
                ch.amp_sliding = sl
                if sl:
                    a = y
                else:                            # (falls into the down code)
                    r2, cy2, v2 = _sbc(r, 0xF1, cy)
                    if (r2 >> 7) ^ v2:
                        a = r2
                    else:
                        ch.amp_sliding = (ch.amp_sliding - 1) & 0xFF
                        a = y
        else:
            r, cy, v = _sbc(sl, 0xF1, 1)
            if (r >> 7) ^ v:                     # sliding < -15: skip
                a = r
            else:
                ch.amp_sliding = (sl - 1) & 0xFF
                a = y
    a = (a + ch.amp_sliding) & 0xFF
    if a & 0x80:
        a = 0
    elif a >= 16:
        a = 15
    ch.amplitude = vt[((ch.volume << 4) & 0xFF) | a]
    if not b0 & 1 and ch.env_enabled:
        ch.amplitude |= 0x10
    y = b0 >> 1
    if b1 & 0x80:                               # envelope offset
        if b0 & 0x20:
            j = ((y | 0xF0) + ch.env_sliding + 1) & 0xFF
        else:
            j = ((y & 15) + ch.env_sliding) & 0xFF
        if b1 & 0x20:
            ch.env_sliding = j
        out['env_add'] = (j + out['env_add']) & 0xFF
    else:                                       # noise offset
        na = (y + ch.noise_sliding) & 0xFF
        out['noise_add'] = na
        if b1 & 0x20:
            ch.noise_sliding = na
    out['mixer'] |= (b1 >> 1) & 0x48
    ch.sample_pos = (ch.sample_pos + 1) & 0xFF
    if ch.sample_pos >= ch.sample_len:
        ch.sample_pos = ch.sample_loop
    ch.orn_pos = (ch.orn_pos + 1) & 0xFF
    if ch.orn_pos >= ch.orn_len:
        ch.orn_pos = ch.orn_loop
    return b0, b1, toff


# ---------------------------------------------------------------- the player
class PT3Player:
    """pt3_init_song then tick() = pt3_tick: the 14 AY registers of a tick."""

    def __init__(self, data, convert=False, zp=False):
        self.m = Module(data)
        m = self.m
        self.convert = convert
        self.zp = zp
        self.T = note_table(m.table)
        self.vt = volume_table(m.version >= 5)
        self.ch = [Chan() for _ in range(3)]
        self.noise_period = 0
        self.f = {'env_add': 0, 'noise_add': 0, 'mixer': 0}
        self.env_period = 0         # (hi << 8 | lo)
        self.env_slide = 0
        self.env_slide_add = 0
        self.env_type = 0
        self.env_type_old = 0
        self.env_delay = 0
        self.env_delay_orig = 0
        self.pattern = 0
        self.line = 0
        self.subframe = 0
        self.speed = m.speed
        self.loop = m.loop
        self.done = False
        self.pattern_done = 0
        self.regs = [0] * 14
        for c in self.ch:
            self._load_ornament(c, 0)
            self._load_sample(c, 1)
        # importer hooks: the lines decoded (ev per channel), the passes
        self.lines = []             # filled when record=True
        self.record = False
        self.passes = 0
        self.ticks = 0

    # -- loaders
    def _load_sample(self, c, s):
        at = self.m.sample_at(s & 0xFF)
        c.sample_loop, c.sample_len = self.m.b(at), self.m.b(at + 1)
        c.sample_ptr = (at + 2) & 0xFFFF
        c.sample_no = s

    def _load_ornament(self, c, o):
        at = self.m.ornament_at(o)
        c.orn_pos = 0
        c.orn_loop, c.orn_len = self.m.b(at), self.m.b(at + 1)
        c.orn_ptr = (at + 2) & 0xFFFF
        c.orn_no = o

    def _reset_note(self, c):
        c.sample_pos = c.amp_sliding = c.noise_sliding = c.env_sliding = c.orn_pos = 0
        c.slide_count = c.sliding = c.acc = c.onoff = 0

    def _set_envelope(self, c, typ, at, ev):
        m = self.m
        self.env_type = typ
        self.env_type_old = 0x78
        self.env_period = m.b(at + 1) << 8 | m.b(at + 2)
        c.env_enabled = 1
        c.orn_pos = 0
        self.env_delay = 0
        self.env_slide = 0
        ev['env'] = (typ, self.env_period)

    # -- the line
    def _decode_note(self, k):
        c = self.ch[k]
        m = self.m
        spec = 0
        ev = {}
        if c.len_count >= 2:
            c.len_count -= 1
            return None
        prev_note, prev_sliding = c.note, c.sliding
        a = c.addr
        y = 0
        while True:
            c.len_count = c.len
            cmd = m.b(a + y)
            hi, lo = cmd & 0xF0, cmd & 15
            if hi == 0:
                spec = lo
                if not lo:
                    c.len_count = 0
                    self.pattern_done = (self.pattern_done - 1) & 0xFF
                    ev['end'] = True
                    break
                y += 1
            elif hi == 0x10:
                if lo:
                    self._set_envelope(c, lo, a + y, ev)
                    y += 2
                else:
                    c.env_enabled = 0
                    ev['env_off'] = True
                y += 1
                self._load_sample(c, m.b(a + y) >> 1)
                ev['sample'] = c.sample_no
                c.orn_pos = 0
                ev['orn_reset'] = True
                y += 1
            elif cmd < 0x40:
                self.noise_period = (cmd + 0xE0) & 0xFF
                ev['noise'] = self.noise_period
                y += 1
            elif hi == 0x40:
                self._load_ornament(c, lo)
                ev['orn'] = lo
                y += 1
            elif cmd < 0xB0:
                c.note = cmd - 0x50
                self._reset_note(c)
                c.enabled = 1
                ev['note'] = c.note
                break
            elif hi == 0xB0:
                if lo == 0:
                    c.env_enabled = 0
                    c.orn_pos = 0
                    ev['env_off'] = ev['orn_reset'] = True
                elif lo == 1:
                    y += 1
                    c.len = c.len_count = m.b(a + y)
                else:
                    self._set_envelope(c, lo - 1, a + y, ev)
                    ev['orn_reset'] = True
                    y += 2
                y += 1
            elif hi == 0xC0:
                if lo == 0:
                    c.enabled = 0
                    self._reset_note(c)
                    ev['off'] = True
                    break
                c.volume = lo
                ev['volume'] = lo
                y += 1
            elif hi in (0xD0, 0xE0):
                if cmd == 0xD0:
                    break
                self._load_sample(c, cmd - 0xD0)
                ev['sample'] = c.sample_no
                y += 1
            else:
                c.env_enabled = 0
                self._load_ornament(c, lo)
                y += 1
                self._load_sample(c, m.b(a + y) >> 1)
                ev['env_off'] = True
                ev['orn'] = lo
                ev['sample'] = c.sample_no
                y += 1
        y += 1
        # the effect (its parameters after the line-ending byte)
        if spec:
            par = []
        if spec == 1:
            c.simple_gliss = 1
            c.onoff = 0
            c.slide_delay = c.slide_count = m.b(a + y)
            c.step = m.b(a + y + 1) | m.b(a + y + 2) << 8
            par = [c.slide_delay, s16(c.step)]
            y += 3
        elif spec == 2:
            c.simple_gliss = 0
            c.onoff = 0
            c.slide_delay = c.slide_count = m.b(a + y)
            h = m.b(a + y + 4)
            neg = h & 0x80
            if neg:
                h ^= 0xFF
            low = m.b(a + y + 3)
            cy = 0
            if neg:
                low ^= 0xFF
                cy = 1
            s = low + cy
            step = (h << 8 | (s & 0xFF)) + ((s >> 8) << 8)
            y += 5
            c.delta = (self._freq(c.note) - self._freq(prev_note)) & 0xFFFF
            c.slide_to_note = c.note
            c.note = prev_note
            if self.m.version >= 6:
                c.sliding = prev_sliding
            if (c.delta - c.sliding) & 0x8000:
                step = -step
            c.step = step & 0xFFFF
            par = [c.slide_delay, s16(c.step), c.slide_to_note]
        elif spec == 3:
            c.sample_pos = m.b(a + y)
            par = [c.sample_pos]
            y += 1
        elif spec == 4:
            c.orn_pos = m.b(a + y)
            par = [c.orn_pos]
            y += 1
        elif spec == 5:
            c.onoff_delay = c.onoff = m.b(a + y)
            c.offon_delay = m.b(a + y + 1)
            c.slide_count = c.sliding = 0
            par = [c.onoff_delay, c.offon_delay]
            y += 2
        elif spec == 8:
            self.env_delay = self.env_delay_orig = m.b(a + y)
            self.env_slide_add = m.b(a + y + 1) | m.b(a + y + 2) << 8
            par = [self.env_delay, s16(self.env_slide_add)]
            y += 3
        elif spec == 9:
            self.speed = m.b(a + y)
            par = [self.speed]
            y += 1
        if spec:
            ev['fx'] = (spec, par)
        c.addr = (a + y) & 0xFFFF
        return ev

    def _freq(self, n):
        """GetNoteFreq: the table entry of note n (the asm indexes a byte)."""
        n &= 0xFF
        return self.T[n] if n < 96 else 0      # (past the table: other data)

    def _decode_line(self):
        evs = [self._decode_note(k) for k in range(3)]
        if self.record:
            self.lines.append({'pass': self.passes, 'pos': self.pattern, 'line': self.line, 'ev': evs,
                               'noise': self.noise_period, 'tick': self.ticks,
                               'state': [self._snap(c) for c in self.ch]})

    @staticmethod
    def _snap(c):
        return {f: getattr(c, f) for f in ('volume', 'enabled', 'env_enabled', 'sample_no', 'orn_no',
                                            'sample_pos', 'orn_pos', 'note', 'sample_ptr', 'orn_ptr')}

    def _set_pattern(self):
        m = self.m
        p = m.b(0xC9 + self.pattern)
        if p == 0xFF:
            self.done = True
            return
        at = (m.pattern_at + 2 * p) & 0xFFFF
        for k, c in enumerate(self.ch):
            c.addr = m.w(at + 2 * k)
        self.noise_period = 0
        self.pattern_done = 3

    def _make_frame(self):
        if self.line == 0 and self.subframe == 0:
            self._set_pattern()
            if self.done:
                return
        while self.subframe == 0:
            self._decode_line()
            if self.pattern_done:
                break
            if self.record:
                self.lines[-1]['aborted'] = True
            self.pattern = (self.pattern + 1) & 0xFF
            self.line = self.subframe = 0
            self._set_pattern()
            if self.done:
                return
        self.subframe = (self.subframe + 1) & 0xFF
        if self.subframe == self.speed:
            self.subframe = 0
            self.line = (self.line + 1) & 0xFF
            if self.line == 64:
                self.line = 0
                self.pattern = (self.pattern + 1) & 0xFF
        self._do_frame()

    def _calculate_note(self, c):
        f = self.f
        if not c.enabled:
            c.amplitude = 0
        else:
            m = self.m
            orn = m.b(c.orn_ptr + c.orn_pos)
            sliding = c.sliding
            _, _, toff = sample_tick(m, c, self.vt, f)
            # (sample_tick advanced the ornament position: read before)
            j = (orn + c.note) & 0xFF
            if j & 0x80:
                j = 0
            elif j >= 96:
                j = 95
            c.tone = (((sliding + toff) & 0xFFFF) + self.T[j]) & 0xFFF
            if 0 < s8(c.slide_count):
                c.slide_count -= 1
                if not c.slide_count:
                    c.sliding = (c.sliding + c.step) & 0xFFFF
                    c.slide_count = c.slide_delay
                    if not c.simple_gliss:
                        sl, de = s16(c.sliding), s16(c.delta)
                        if (c.step & 0x8000 and sl <= de) or (not c.step & 0x8000 and sl >= de):
                            c.note = c.slide_to_note
                            c.slide_count = c.sliding = 0
        f['mixer'] >>= 1
        if c.onoff:
            y = c.onoff - 1
            if not y:
                c.enabled ^= 1
                y = c.onoff_delay if c.enabled else c.offon_delay
            if self.zp:
                c.onoff = y

    def _conv(self, p):
        return ((p * 9) >> 4) & 0xFFF if self.convert else p

    def _do_frame(self):
        f = self.f
        f['mixer'] = 0
        f['env_add'] = 0
        for c in self.ch:
            self._calculate_note(c)
        r = self.regs
        for k, c in enumerate(self.ch):
            t = self._conv(c.tone)
            r[2 * k], r[2 * k + 1] = t & 0xFF, t >> 8
        n = (self.noise_period + f['noise_add']) & 31
        r[6] = ((9 * n) >> 4) & 31     # (always: pt3_lib's noise conversion
        # is under PT3_DISABLE_ENABLE_FREQ_CONVERSION, a name nothing defines)
        r[7] = f['mixer']
        for k, c in enumerate(self.ch):
            r[8 + k] = c.amplitude
        lo = (self.env_period & 0xFF) + f['env_add']
        hi = (self.env_period >> 8) + (lo >> 8)
        e = ((hi & 0xFF) << 8 | (lo & 0xFF)) + self.env_slide
        e &= 0xFFFF
        if self.convert:
            s8_ = (e * 8) & 0xFFFF
            l2 = (s8_ & 0xFF) + (e & 0xFF)
            h2 = (s8_ >> 8) + (e >> 8) + (l2 >> 8)
            v = (h2 << 8 | (l2 & 0xFF)) >> 4
            e = (v & 0x0FFF)
        r[11], r[12] = e & 0xFF, e >> 8
        r[13] = 0xFF if self.env_type == self.env_type_old else self.env_type
        self.env_type_old = self.env_type
        if self.env_delay:
            self.env_delay -= 1
            if not self.env_delay:
                self.env_delay = self.env_delay_orig
                self.env_slide = (self.env_slide + self.env_slide_add) & 0xFFFF

    def tick(self):
        """pt3_tick: the frame (R0..R13), looping at the song's loop position."""
        while True:
            self._make_frame()
            if not self.done:
                break
            self.pattern, self.line, self.subframe, self.done = self.loop, 0, 0, False
            self.passes += 1
        self.ticks += 1
        return list(self.regs)


def build(samples, ornaments, patterns, positions, loop=0, speed=6, table=2, version=7,
          title='', author=''):
    """A .pt3 from parts (tests, generators):
      samples    {number 1..31: (loop, [(b0, b1, tone)...])}  (sample 1 is
                 the default of every channel; unset numbers -> sample 1)
      ornaments  {number 0..15: (loop, [offset...])}  (0: the default; unset
                 -> ornament 0, which defaults to [0])
      patterns   [(stream A, stream B, stream C)...]: channel byte lists,
                 each ending with its $00
      positions  pattern numbers; loop: the position played after the last."""
    head = bytearray(0xC9)
    text = (b'ProTracker 3.%d compilation of ' % version + title.encode('latin-1')[:32].ljust(32)
            + b' by ' + author.encode('latin-1')[:32].ljust(32))
    head[:len(text)] = text
    head[0x63], head[0x64], head[0x65], head[0x66] = table, speed, len(positions), loop
    d = bytearray(head) + bytes(3 * p for p in positions) + b'\xff'
    pt = len(d)
    d += bytes(6 * len(patterns))
    for i, chans in enumerate(patterns):
        for k, c in enumerate(chans):
            d[pt + 6 * i + 2 * k:pt + 6 * i + 2 * k + 2] = len(d).to_bytes(2, 'little')
            d += bytes(c)
    d[0x67:0x69] = pt.to_bytes(2, 'little')
    orns = dict(ornaments)
    orns.setdefault(0, (0, [0]))
    at = {}
    for o, (lp, vals) in sorted(orns.items()):
        at[o] = len(d)
        d += bytes([lp, len(vals)]) + bytes(v & 0xFF for v in vals)
    for o in range(16):
        d[0xA9 + 2 * o:0xAB + 2 * o] = at.get(o, at[0]).to_bytes(2, 'little')
    sams = dict(samples)
    sams.setdefault(1, (0, [(0, 0x8F, 0)]))
    at = {}
    for s, (lp, ticks) in sorted(sams.items()):
        at[s] = len(d)
        d += bytes([lp, len(ticks)])
        for b0, b1, tone in ticks:
            d += bytes([b0, b1]) + (tone & 0xFFFF).to_bytes(2, 'little')
    for s in range(32):
        d[0x69 + 2 * s:0x6B + 2 * s] = at.get(s, at[1]).to_bytes(2, 'little')
    return bytes(d)


def render(data, n, **kw):
    p = PT3Player(data, **kw)
    return [p.tick() for _ in range(n)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pt3')
    ap.add_argument('--frames', type=int, default=0)
    ap.add_argument('--info', action='store_true')
    ap.add_argument('--convert', action='store_true', help='model PT3_FREQ_CONVERSION = 1')
    a = ap.parse_args(argv)
    data = Path(a.pt3).read_bytes()
    p = PT3Player(data, convert=a.convert)
    if a.info:
        m = p.m
        print(f'"{m.title}" by "{m.author}": version 3.{m.version}, table {m.table} '
              f'({TABLE_NAMES[min(m.table, 3)]}), speed {m.speed}, positions {m.positions}, loop {m.loop}')
    for k in range(a.frames):
        print(k, ' '.join(f'{x:02X}' for x in p.tick()))


if __name__ == '__main__':
    main()
