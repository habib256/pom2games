#!/usr/bin/env python3
"""Vortex Tracker II (.pt3) -> AYS v1 song (dev/lib/apple2/AYSONG_FORMAT.md).

    song, report = convert(open('song.pt3', 'rb').read())   # aysong.Song
    print(report)                                           # what mapped, what did not
    python3 pt3import.py IN.pt3 -o OUT.AYS [--clock apple|native] [--report]
                         [--asm OUT.inc --label L] [--json OUT.json]

How: the module is played by pt3play.PT3Player (the bit-exact model of
dev/lib/apple2/pt3, checked against the asm by dev/tests/test_pt3_import.py)
and every decoded line is turned into AYS cells, so the PT3 semantics
(note lengths, speed effects, three-channel pattern ends, line 64, the
loop position, state carried across patterns) come from the player, not
from a second parser. Then:

  timeline  the lines of the first pass, plus whole passes from the loop
            position until one plays the cells of the one before (state
            carried over the loop, e.g. a volume set at the song's end);
            line durations in ticks -> AYS speed = their gcd, a line = d /
            speed rows (speed effects: exact); rows cut into patterns of R
            rows (R divides the length and the loop row; the R giving the
            smallest encoded song), identical patterns shared.
  instruments  a key (sample, start position, channel volume, envelope
            on + shape/period when the note's line sets it, noise base) ->
            the sample unrolled tick by tick through pt3_lib's own
            amplitude code (volume table, amplitude slides, envelope bit,
            tone / noise masks, noise offsets + slides: R6 per tick, as
            pt3_lib converts it), loop = where the state repeats, then the
            shortest prefix + period; at most 64 ticks (MB TRACKER) else
            truncated (reported). More than 15 keys: the least used merge
            into their nearest (reported).
  ornaments  exact as a transposition c plus the arpeggio effect A $xy when
            the unrolled offsets are c, c+x, c+y, c, ... (0 <= x, y <= 15);
            else the first offset only (reported, notes counted).
  notes     --clock apple (default): the AYS note closest to what pt3_lib
            plays (the raw table period on the 1,020,484 Hz Mockingboard);
            native: to what the composer heard (1.7734 MHz; table 1 ST: 2
            MHz). One transposition for the song (keeps the intervals), the
            worst error reported in cents.
  envelopes shape + period on the note that sets them (AYS instruments
            write R13 at their notes); AYS periods are R12 with R11 = 0:
            periods with a low byte are rounded (reported); a set without
            a note on that line restarts at the next envelope note
            (reported).
  effects   1 tone slide -> U / D (p = step / delay; AYS slides one tick
            earlier than PT3: approximated), 3 sample position -> the
            instrument's start (exact), 4 ornament position -> the
            ornament's start (as ornaments), 9 speed -> timing (exact);
            2 portamento -> the target note at once, 5 vibrato, 8 envelope
            slide: reported lost. Mid-note channel volume / sample /
            envelope / noise base changes: reported lost (AYS picks the
            instrument at the note). Sample tone offsets: lost (reported).
  validate  renders both players (PT3Player, aysong.Player) over the song
            plus a loop and counts agreement: volumes, mixer, noise period,
            envelope (on the ticks they are heard), periods as cents.
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aysong  # noqa: E402
import pt3play  # noqa: E402
from aysong import OFF, Cell, Instrument, Pattern, Song, Tick  # noqa: E402

APPLE = 1_020_484
MBT_PATTERNS, MBT_INSTRUMENTS, MBT_TICKS, MBT_BYTES = 64, 15, 64, 12 * 1024


def cents(f1, f2):
    return 1200 * math.log2(f1 / f2)


def ays_hz(note):
    return APPLE / (16 * max(aysong.period(note), 1))


# ---------------------------------------------------------------- report
class Report:
    """Counters and lines; str() is the summary the CLI prints."""

    def __init__(self):
        self.info = {}
        self.lost = Counter()           # feature -> occurrences (lines / notes)
        self.approx = Counter()
        self.exact = Counter()
        self.notes = []                 # free text lines
        self.validation = {}
        self.limits = []

    def __str__(self):
        out = []
        i = self.info
        out.append(f"PT3 \"{i.get('title', '')}\" by \"{i.get('author', '')}\": version 3.{i.get('version')}, "
                   f"table {i.get('table')} ({i.get('table_name')}), speed {i.get('pt3_speed')}, "
                   f"{i.get('positions')} positions, loop {i.get('pt3_loop')}")
        out.append(f"AYS: {i.get('bytes')} bytes, {i.get('patterns')} patterns of {i.get('rows')} rows, "
                   f"order {i.get('order')} (loop {i.get('loop')}), speed {i.get('speed')}, "
                   f"{i.get('instruments')} instruments; {i.get('lines')} lines = {i.get('ticks')} ticks "
                   f"({i.get('passes')} pass(es))")
        out.append(f"notes: clock {i.get('clock')}, PT3 note n -> AYS note n {i.get('shift'):+d}, "
                   f"worst pitch error {i.get('worst_cents', 0):.1f} cents (mean {i.get('mean_cents', 0):.1f})")
        for title, c in (('exact', self.exact), ('approximated', self.approx), ('lost', self.lost)):
            if c:
                out.append(f'{title}: ' + ', '.join(f'{k} x{v}' for k, v in sorted(c.items())))
        out += self.notes
        if self.limits:
            out.append('MB TRACKER limits exceeded: ' + '; '.join(self.limits))
        else:
            out.append('MB TRACKER limits: within (64 patterns, 15 instruments, 64 ticks, 12 KB)')
        v = self.validation
        if v:
            out.append(f"validation over {v['ticks']} ticks (PT3Player vs aysong.Player):")
            for k in ('volume', 'mixer', 'noise', 'env_shape', 'env_period', 'period'):
                g = v[k]
                if not g['n']:
                    out.append(f'  {k:10} (never heard)')
                    continue
                line = f"  {k:10} {g['ok']}/{g['n']} = {100 * g['ok'] / g['n']:.2f} %"
                if k == 'period':
                    line += (f" within {v['tolerance']:.1f} cents; worst {g['worst']:.1f} cents, "
                             f"mean {g['mean']:.1f}")
                out.append(line)
        return '\n'.join(out)


# ---------------------------------------------------------------- pieces
def orn_values(m, ptr, start, n):
    lp, ln = m.b(ptr - 2), m.b(ptr - 1)
    out, pos = [], start
    for _ in range(n):
        out.append(pt3play.s8(m.b(ptr + pos)))
        pos = (pos + 1) & 0xFF
        if pos >= ln:
            pos = lp
    return out


def ornament_map(m, ptr, start):
    """(c, x, y, exact): offsets = c, c+x, c+y cycling (0 <= x, y <= 15)."""
    ln = max(m.b(ptr - 1), 1)
    seq = orn_values(m, ptr, start, 4 * ln + 6)
    c = seq[0]
    x, y = seq[1] - c, seq[2] - c
    ok = 0 <= x <= 15 and 0 <= y <= 15 and all(v == c + (0, x, y)[t % 3] for t, v in enumerate(seq))
    if not ok:
        x = y = 0
    return c, x, y, ok


class _Ch:
    """A bare channel for sample_tick (an instrument's unrolling)."""

    def __init__(self, m, ptr, pos, volume, env):
        self.sample_ptr, self.sample_pos = ptr, pos
        self.sample_loop, self.sample_len = m.b(ptr - 2), m.b(ptr - 1)
        self.volume, self.env_enabled = volume, env
        self.acc = self.amp_sliding = self.env_sliding = self.noise_sliding = 0
        self.orn_pos, self.orn_len, self.orn_loop = 0, 1, 0
        self.amplitude = 0


def sample_has_noise(m, ptr):
    ln = m.b(ptr - 1)
    return any(not m.b(ptr + 4 * k + 1) & 0x80 for k in range(ln))


def unroll(m, vt, key, max_ticks):
    """The AYS ticks of an instrument key -> (ticks, loop, stats)."""
    ptr, pos, volume, env, _shape, noise_base = key
    ch = _Ch(m, ptr, pos, volume, env)
    seen = {}
    ticks = []
    stats = Counter()
    out = {'env_add': 0, 'noise_add': 0, 'mixer': 0}
    loop = None
    for _ in range(4096):
        state = (ch.sample_pos, ch.amp_sliding, ch.noise_sliding & 31)   # (what the ticks depend on)
        if state in seen:
            loop = seen[state]
            break
        seen[state] = len(ticks)
        out['env_add'] = 0
        b0, b1, toff = pt3play.sample_tick(m, ch, vt, out)
        a = ch.amplitude
        noise = not b1 & 0x80
        np_ = ((9 * ((noise_base + out['noise_add']) & 31)) >> 4) & 31 if noise else None
        ticks.append(Tick(a & 15, not b1 & 0x10, noise, bool(a & 0x10), np_))
        if toff:
            stats['tone_offset'] += 1
        if out['env_add'] and a & 0x10:
            stats['env_offset'] += 1
    if loop is None:
        loop = len(ticks) - 1
    # the shortest prefix + period giving the same ticks
    per = len(ticks) - loop
    tail = ticks[loop:]
    for p in range(1, per + 1):
        if per % p == 0 and all(tail[i] == tail[i % p] for i in range(per)):
            per = p
            break
    while loop > 0 and ticks[loop - 1] == ticks[loop - 1 + per]:
        loop -= 1
    ticks = ticks[:loop + per]
    if max_ticks and len(ticks) > max_ticks:
        stats['truncated'] = len(ticks)
        ticks = ticks[:max_ticks]
        loop = len(ticks) - 1
    while sum(2 if t.noise_period is not None else 1 for t in ticks) > 250:
        ticks.pop()
        loop = min(loop, len(ticks) - 1)
        stats['truncated'] = stats['truncated'] or 1
    return ticks, loop, stats


def _distance(a, b, n=64):
    def expand(ins):
        t, lp = ins
        out = list(t)
        while len(out) < n:
            out += t[lp:]
        return out[:n]
    d = 0
    for x, y in zip(expand(a), expand(b)):
        d += abs(x.vol - y.vol) + 8 * (x.tone != y.tone) + 8 * (x.noise != y.noise) + 16 * (x.env != y.env)
    return d


def env_r12(period, clock_scale):
    """AYS envelope period (R12, R11 = 0) for a PT3 16-bit period."""
    p = period * clock_scale
    return min(255, max(0, round(p / 256)))


# ---------------------------------------------------------------- convert
def _simulate(data, passes, zp, max_ticks=400_000):
    p = pt3play.PT3Player(data, zp=zp)
    p.record = True
    while p.passes < passes and p.ticks < max_ticks:
        p.tick()
    lines = p.lines
    # merge aborted lines (the $00 decode) into the line that follows
    merged, carry = [], None
    for ln in lines:
        if ln.get('aborted'):
            carry = ln
            continue
        if carry:
            evs = []
            for a, b in zip(carry['ev'], ln['ev']):
                e = dict(a or {})
                e.pop('end', None)
                e.update(b or {})
                evs.append(e if (a or b) is not None else None)
            ln = dict(ln, ev=evs)
            carry = None
        merged.append(ln)
    for k in range(len(merged) - 1):
        merged[k]['dur'] = merged[k + 1]['tick'] - merged[k]['tick']
    if merged:
        merged[-1]['dur'] = p.ticks - merged[-1]['tick']
    return p, merged


def convert(pt3_bytes, clock='apple', zp=False, max_passes=4, max_ticks=None, validate=True,
            validate_ticks=20000, rate=50):
    """A .pt3's bytes -> (aysong.Song, Report). max_ticks: cut instruments
    to that many ticks (64: MB TRACKER's limit; None: as long as the AYS
    format allows, 250 bytes, MB TRACKER's limit reported). rate: the AYS
    header's ticks a second (a PT3 does not say; informative)."""
    data = bytes(pt3_bytes)
    rep = Report()
    m = pt3play.Module(data)
    T = pt3play.note_table(m.table)
    vt = pt3play.volume_table(m.version >= 5)
    tname = pt3play.TABLE_NAMES[min(m.table, 3)]
    rep.info.update(title=m.title, author=m.author, version=m.version, table=m.table, table_name=tname,
                    pt3_speed=m.speed, positions=len(m.positions), pt3_loop=m.loop, clock=clock)
    pclock = APPLE if clock == 'apple' else pt3play.NATIVE_CLOCK[min(m.table, 3)]
    scale = APPLE / pclock              # PT3 period units -> Apple II AY periods
    p, lines = _simulate(data, max_passes + 1, zp)
    if not m.positions:
        raise ValueError('no positions')
    # ---- pass 1: abstract cells (instrument keys) per line and channel
    cur = [dict(on=False, ins=None, c=0, x=0, y=0, fx=None, noise=None) for _ in range(3)]
    pending_env = None
    used_notes = Counter()
    abstract = []                       # per line: (dur, (cell, cell, cell))
    counts = []                         # per line: report Counter (merged for the chosen lines)

    for ln in lines:
        cnt = Counter()
        cells = [None, None, None]
        evs = ln['ev']
        env_ev = None
        for k in range(3):
            e = evs[k] or {}
            if 'env' in e:
                env_ev = e['env']
        if env_ev:
            pending_env = env_ev
        for k in range(3):
            e = evs[k]
            st = ln['state'][k]
            cs = cur[k]
            if e is None:
                cells[k] = None
                continue
            fx = e.get('fx')
            if 'note' in e:
                note = e['note']
                if fx and fx[0] == 2:
                    note = fx[1][2]
                    cnt['lost', 'portamento (-> the target note at once)'] += 1
                ptr = st['sample_ptr']
                env = st['env_enabled']
                shape = None
                if env and pending_env is not None:
                    shape = pending_env
                    pending_env = None
                nb = ln['noise'] if sample_has_noise(m, ptr) else 0
                key = (ptr, st['sample_pos'], st['volume'], env, shape, nb)
                c, x, y, ok = ornament_map(m, st['orn_ptr'], st['orn_pos'])
                if not ok:
                    cnt['lost', 'ornament not an arpeggio (first offset kept)'] += 1
                elif x or y:
                    cnt['exact', 'ornament -> arpeggio'] += 1
                elif c:
                    cnt['exact', 'ornament -> transposition'] += 1
                if st['sample_pos']:
                    cnt['exact', 'sample position (effect 3) -> instrument start'] += 1
                base = min(max(note + c, 0), 95)
                used_notes[base] += 1
                for off in {x, y} - {0}:
                    used_notes[min(base + off, 95)] += 1
                afx = (1, x << 4 | y) if (x or y) else None
                if fx and fx[0] == 1:
                    afx = _slide(fx, afx, cnt, scale)
                cs.update(on=True, c=c, x=x, y=y, fx=afx, noise=nb, key=key)
                cells[k] = ('note', base, key, afx)
            elif 'off' in e:
                cs.update(on=False, fx=None)
                cells[k] = ('off',)
            else:
                cell = None
                if cs['on'] and st['enabled']:
                    if 'volume' in e and e['volume'] != cs['key'][2]:
                        cnt['lost', 'volume change mid-note'] += 1
                    if 'sample' in e and st['sample_ptr'] != cs['key'][0]:
                        cnt['lost', 'sample change mid-note'] += 1
                    if ('env' in e or 'env_off' in e) and st['env_enabled'] != cs['key'][3]:
                        cnt['lost', 'envelope on/off mid-note'] += 1
                    if 'orn' in e or 'orn_reset' in e or (fx and fx[0] == 4):
                        c, x, y, ok = ornament_map(m, st['orn_ptr'], st['orn_pos'])
                        if not ok:
                            cnt['lost', 'ornament not an arpeggio (first offset kept)'] += 1
                        if c != cs['c']:
                            cnt['lost', 'ornament transposition change mid-note'] += 1
                        elif x or y or cs['x'] or cs['y']:
                            afx = (1, x << 4 | y) if (x or y) else (0, 0)
                            cell = ('fx', afx)
                            cs.update(x=x, y=y, fx=afx)
                    if fx and fx[0] == 1:
                        afx = _slide(fx, cs['fx'] if cs['fx'] and cs['fx'][0] == 1 else None, cnt, scale)
                        if afx and afx[0] != 1:
                            cell = ('fx', afx)
                            cs['fx'] = afx
                    if fx and fx[0] == 2:
                        cnt['lost', 'portamento without a note'] += 1
                    if fx and fx[0] == 3:
                        cnt['lost', 'sample position mid-note'] += 1
                if cs['on'] and sample_has_noise(m, cs['key'][0]) and ln['noise'] != cs['noise']:
                    cnt['lost', 'noise base change mid-note'] += 1
                    cs['noise'] = ln['noise']
                cells[k] = cell
            if fx:
                n = fx[0]
                if n == 5:
                    cnt['lost', 'vibrato (effect 5)'] += 1
                elif n == 8:
                    cnt['lost', 'envelope slide (effect 8)'] += 1
                elif n == 9:
                    cnt['exact', 'speed (effect 9) -> timing'] += 1
            if 'env' in e:
                pt = e['env'][1]
                if abs(env_r12(pt, scale) * 256 - pt * scale) >= 0.5:
                    cnt['approx', 'envelope period rounded to R12 (R11 = 0)'] += 1
                else:
                    cnt['exact', 'envelope shape + period'] += 1
        if env_ev and pending_env is env_ev:
            cnt['approx', 'envelope set without a note (restarts at the next envelope note)'] += 1
        abstract.append((ln['dur'], tuple(cells), ln['pass'], ln['pos']))
        counts.append(cnt)

    # ---- the timeline: pass 0 plus the passes until the loop section repeats
    def section(ps):
        return [a[:2] for a in abstract if a[2] == ps]
    first_loop = next((i for i, a in enumerate(abstract) if a[2] == 0 and a[3] == m.loop), 0)
    prev = [a[:2] for a in abstract[first_loop:] if a[2] == 0]
    end_pass, stable = 0, False
    for ps in range(1, max_passes + 1):
        sec = section(ps)
        if sec == prev:
            stable = True
            break
        end_pass, prev = ps, sec
    if not stable:
        rep.notes.append(f'loop: the passes still differ after {max_passes}: the last one loops (approximated)')
    chosen = [i for i, a in enumerate(abstract) if a[2] <= end_pass]
    loop_line = first_loop if end_pass == 0 else next(i for i, a in enumerate(abstract) if a[2] == end_pass)
    total = Counter()
    for i in chosen:
        total.update(counts[i])
    for (cat, k), v in total.items():
        {'exact': rep.exact, 'approx': rep.approx, 'lost': rep.lost}[cat][k] += v

    # ---- note mapping: one transposition for the song
    def pt3_hz(n):
        return pclock / (16 * max(T[n], 1))
    best = None
    for shift in (range(-36, 37) if used_notes else [0]):
        errs = []
        for n, w in used_notes.items():
            a = min(max(n + shift, 0), 95)
            errs.append((abs(cents(ays_hz(a), pt3_hz(n))), w))
        score = sum(e * w for e, w in errs) / max(1, sum(w for _, w in errs))
        if best is None or score < best[0]:
            best = (score, shift, max((e for e, _ in errs), default=0))
    _, shift, worst = best
    rep.info.update(shift=shift, worst_cents=worst, mean_cents=best[0])

    # ---- instruments
    durs = [abstract[i][0] for i in chosen]
    speed = 0
    for d in durs:
        speed = math.gcd(speed, d)
    speed = max(speed, 1)
    if speed > 255:
        speed = math.gcd(speed, 255) or 1
    used = Counter()
    for i in chosen:
        for c in abstract[i][1]:
            if c and c[0] == 'note':
                used[c[2]] += 1
    keys = list(used)                   # (first use first: Counter keeps insertion order)
    unrolled = {}
    istats = Counter()
    for k in keys:
        t, lp, st = unroll(m, vt, k, max_ticks)
        unrolled[k] = (t, lp)
        if st['tone_offset']:
            istats['sample tone offsets (instruments)'] += 1
        if st['env_offset']:
            istats['sample envelope offsets (instruments)'] += 1
        if st['truncated']:
            istats['instrument longer than ' + (f'{max_ticks} ticks' if max_ticks else '250 bytes')
                   + ' (truncated)'] += 1
    for k, v in istats.items():
        (rep.approx if 'truncated' in k else rep.lost)[k] += v
    alias = {k: k for k in keys}
    live = list(keys)
    while len(live) > 15:
        victim = min(live, key=lambda k: used[k])
        live.remove(victim)
        target = min(live, key=lambda k: _distance(unrolled[victim], unrolled[k]))
        for a, b in alias.items():
            if b == victim:
                alias[a] = target
        used[target] += used[victim]
        rep.approx['instrument merged into its nearest (notes)'] += used[victim]
    if not live:
        live = [None]
    index = {k: i + 1 for i, k in enumerate(live)}
    instruments = []
    for k in live:
        if k is None:
            instruments.append(Instrument([Tick(0, False)], None, None, 0, 'silence'))
            continue
        t, lp = unrolled[k]
        ptr, pos, vol, env, shape, nb = k
        name = f's{_sample_no(m, ptr)}v{vol}' + ('e' if env else '') + (f'p{pos}' if pos else '')
        ins = Instrument(t, None if lp == len(t) - 1 else lp, None, 0, name)
        if shape is not None:
            ins.env_shape = shape[0] & 15
            ins.env_period = env_r12(shape[1], scale)
        instruments.append(ins)

    # ---- rows
    rows_cells = [[], [], []]
    for i in chosen:
        dur, cells, _, _ = abstract[i]
        n = max(1, dur // speed)
        for k in range(3):
            rows_cells[k].append(cells[k])
            rows_cells[k] += [None] * (n - 1)
    loop_row = 0
    for i in chosen:
        if i == loop_line:
            break
        loop_row += max(1, abstract[i][0] // speed)
    total_rows = len(rows_cells[0])
    loop_len = total_rows - loop_row

    def make_tracks(nrows, lrow):
        """AYS cells of rows 0..nrows-1, the rows past the end repeating the
        loop section (so the loop may start later, on a pattern boundary)."""
        tracks = [[], [], []]
        for k in range(3):
            cur_ins = 1
            forced = False
            for r in range(nrows):
                c = rows_cells[k][r if r < total_rows else loop_row + (r - loop_row) % loop_len]
                cell = Cell()
                if r == lrow:
                    forced = True
                if c is None:
                    pass
                elif c[0] == 'note':
                    _, base, key, afx = c
                    cell.note = min(max(base + shift, 0), 95)
                    ins = index[alias[key]]
                    if ins != cur_ins or forced:
                        cell.ins = ins
                        cur_ins = ins
                        forced = False
                    if afx:
                        cell.fx, cell.param = afx
                elif c[0] == 'off':
                    cell.note = OFF
                elif c[0] == 'fx':
                    cell.fx, cell.param = c[1]
                tracks[k].append(cell)
        return tracks

    # ---- patterns: R rows; the loop row moved by d (< R) rows and the loop
    # section repeated k times when R does not divide them; the longest R
    # whose song is within 10 % of the smallest
    best_song = None
    cands = []
    memo = {}
    for R in range(64, 0, -1):
        d = -loop_row % R
        k = R // math.gcd(R, loop_len)
        nrows = loop_row + d + k * loop_len
        if nrows // R > 255:
            continue
        if (nrows, d) not in memo:
            memo[nrows, d] = make_tracks(nrows, loop_row + d)
        tracks = memo[nrows, d]
        pats, order, seen = [], [], {}
        for s in range(0, nrows, R):
            chunk = tuple(tuple(_cell_key(c) for c in tracks[v][s:s + R]) for v in range(3))
            if chunk not in seen:
                seen[chunk] = len(pats)
                pats.append(Pattern([list(tracks[v][s:s + R]) for v in range(3)]))
            order.append(seen[chunk])
        if len(pats) > 255:
            continue
        song = Song(pats, instruments, order, 3, R, speed, rate, (loop_row + d) // R,
                    _ascii(m.title)[:40], _ascii(m.author)[:40])
        cands.append((len(aysong.encode(song)), song, d, k))
    if cands:
        least = min(c[0] for c in cands)
        best_song = next(c for c in cands if c[0] <= least * 1.1 + 16)   # (R descending)
        if best_song[2] or best_song[3] > 1:
            rep.notes.append(f'loop: {best_song[3]} loop section(s) of {loop_len} rows, the loop entry '
                             f'{best_song[2]} rows later (pattern boundary)')
    else:                               # too long: 255 patterns of 64 rows
        nrows = 255 * 64
        tracks = make_tracks(nrows, loop_row if loop_row < nrows else 0)
        pats = [Pattern([tracks[v][s:s + 64] for v in range(3)]) for s in range(0, nrows, 64)]
        song = Song(pats, instruments, list(range(255)), 3, 64, speed, rate,
                    loop_row // 64 if loop_row < nrows and not loop_row % 64 else 0,
                    _ascii(m.title)[:40], _ascii(m.author)[:40])
        best_song = (len(aysong.encode(song)), song)
        rep.limits.append(f'{total_rows} rows: cut to {nrows} (255 order entries of 64 rows)')
    size, song = best_song[:2]
    rep.info.update(bytes=size, patterns=len(song.patterns), rows=song.rows, order=len(song.order), loop=song.loop,
                    speed=speed, instruments=len(song.instruments), lines=len(chosen),
                    ticks=sum(durs), passes=end_pass + 1, loop_ticks=sum(abstract[i][0] for i in chosen
                                                                         if i >= loop_line))
    if len(song.patterns) > MBT_PATTERNS:
        rep.limits.append(f'{len(song.patterns)} patterns > {MBT_PATTERNS}')
    if len(keys) > MBT_INSTRUMENTS:
        rep.limits.append(f'{len(keys)} instrument variants > {MBT_INSTRUMENTS} (merged)')
    longest = max(len(i.ticks) for i in song.instruments)
    if longest > MBT_TICKS:
        rep.limits.append(f'an instrument of {longest} ticks > {MBT_TICKS}')
    if size > MBT_BYTES:
        rep.limits.append(f'{size} bytes > {MBT_BYTES}')
    if validate:
        n = min(validate_ticks, rep.info['ticks'] + rep.info['loop_ticks'])
        rep.validation = compare(data, aysong.encode(song), n, clock=clock, zp=zp,
                                 tolerance=worst + 0.5)
    return song, rep


def _slide(fx, afx, cnt, scale):
    """Effect 1 (delay, step) -> an AYS slide unless the arpeggio holds the slot."""
    delay, step = fx[1][0], fx[1][1]
    if afx and afx[0] == 1 and afx[1]:
        cnt['lost', 'tone slide dropped (the arpeggio keeps the effect)'] += 1
        return afx
    if not delay:
        return (0, 0)
    p = round(abs(step) * scale / delay)
    if not p:
        cnt['lost', 'tone slide too slow for AYS (dropped)'] += 1
        return (0, 0)
    cnt['approx', 'tone slide -> slide (a tick early' + ('' if delay == 1 and p * delay == abs(step) * scale
                                                          and p <= 255 else ', step rounded') + ')'] += 1
    return (3 if step > 0 else 2, min(p, 255))


def _sample_no(m, ptr):
    for s in range(32):
        if (m.sample_at(s) + 2) & 0xFFFF == ptr:
            return s
    return '?'


def _ascii(s):
    return ''.join(ch if 32 <= ord(ch) < 127 else '?' for ch in s).strip()


def _cell_key(c):
    return (c.note, c.ins, c.fx, c.param if c.fx else 0)


# ---------------------------------------------------------------- validation
def compare(pt3_bytes, ays_bytes, ticks, clock='apple', zp=False, tolerance=50.0):
    """Both players for `ticks` ticks: agreement per register group, on the
    ticks where it is heard (a channel's mixer, period: when its volume is
    not 0 in the PT3; noise: when a PT3 channel plays noise; envelope
    period: when one plays the envelope; R13: when either writes it)."""
    m = pt3play.Module(pt3_bytes)
    pclock = APPLE if clock == 'apple' else pt3play.NATIVE_CLOCK[min(m.table, 3)]
    a = pt3play.PT3Player(pt3_bytes, zp=zp)
    b = aysong.Player(ays_bytes, 3)
    g = {k: {'ok': 0, 'n': 0} for k in ('volume', 'mixer', 'noise', 'env_shape', 'env_period', 'period')}
    errs = []
    first_bad = {}

    def tally(k, ok, t):
        g[k]['n'] += 1
        if ok:
            g[k]['ok'] += 1
        elif k not in first_bad:
            first_bad[k] = t
    for t in range(ticks):
        x, y = a.tick(), b.tick()
        noise_heard = env_heard = False
        for c in range(3):
            vx, vy = x[8 + c], y[8 + c]
            ex = 0x10 if vx & 0x10 else vx
            ey = 0x10 if vy & 0x10 else vy
            tally('volume', ex == ey, t)
            if not ex:
                continue
            tx, nx = not x[7] >> c & 1, not x[7] >> (3 + c) & 1
            ty, ny = not y[7] >> c & 1, not y[7] >> (3 + c) & 1
            tally('mixer', (tx, nx) == (ty, ny), t)
            noise_heard |= nx
            env_heard |= ex == 0x10
            if tx:
                px = max(x[2 * c] | x[2 * c + 1] << 8, 1)
                py = max(y[2 * c] | y[2 * c + 1] << 8, 1)
                e = abs(cents(pclock / px, APPLE / py))
                errs.append(e)
                tally('period', e <= tolerance, t)
        if noise_heard:
            tally('noise', x[6] == y[6], t)
        if env_heard:
            px = x[11] | x[12] << 8
            py = y[11] | y[12] << 8
            tally('env_period', round(px * APPLE / pclock) == py, t)
        if x[13] != 0xFF or y[13] != 0xFF:
            tally('env_shape', x[13] == y[13], t)
    g['period']['worst'] = max(errs, default=0.0)
    g['period']['mean'] = sum(errs) / len(errs) if errs else 0.0
    return dict(g, ticks=ticks, tolerance=tolerance, first_bad=first_bad)


# ---------------------------------------------------------------- CLI
def retime(song, k):
    """A song written for a k times slower tick (WARGALAGA II: 25 Hz) for
    the 50 Hz of MB TRACKER and mb_irq: speed x k, every instrument tick k
    times (the loop index too), fade / swell every k x p ticks, slides p / k
    (rounded; arpeggios cycle k times faster: not expressible)."""
    if k == 1:
        return song
    song.speed *= k
    song.rate *= k
    for ins in song.instruments:
        ins.ticks = [t for t in ins.ticks for _ in range(k)]
        if ins.loop is not None:
            ins.loop *= k
    for pat in song.patterns:
        for track in pat.tracks:
            for c in track:
                if c.fx in (4, 5):
                    c.param = min(255, c.param * k)
                elif c.fx in (2, 3):
                    c.param = max(1, round(c.param / k))
    return song


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pt3')
    ap.add_argument('-o', '--out', help='binary AYS file')
    ap.add_argument('--asm', help='ca65 include: LABEL then .byte rows')
    ap.add_argument('--label', default='ays_song')
    ap.add_argument('--json', help='write the song as JSON')
    ap.add_argument('--clock', choices=('apple', 'native'), default='apple',
                    help="apple: the pitch pt3_lib plays on the Mockingboard; native: the composer's")
    ap.add_argument('--zp', action='store_true', help="pt3_lib's zero-page build (the real vibrato)")
    ap.add_argument('--report', action='store_true', help='the full report (else a one-line summary)')
    ap.add_argument('--no-validate', action='store_true')
    ap.add_argument('--max-ticks', type=int, help='cut instruments to N ticks (64: MB TRACKER)')
    ap.add_argument('--rate', type=int, default=50, help="the AYS header's ticks a second (WARGALAGA II: 25)")
    ap.add_argument('--to-50hz', action='store_true',
                    help='a 25 Hz song (--rate 25) retimed for a 50 Hz player (MB TRACKER): speed and '
                         'instrument ticks doubled')
    a = ap.parse_args(argv)
    song, rep = convert(Path(a.pt3).read_bytes(), clock=a.clock, zp=a.zp, validate=not a.no_validate,
                        max_ticks=a.max_ticks, rate=a.rate)
    if a.to_50hz:
        assert a.rate * 2 == 50, '--to-50hz: from --rate 25'
        song = retime(song, 2)
    data = aysong.encode(song)
    assert aysong.encode(aysong.decode(data)) == data
    if a.out:
        Path(a.out).write_bytes(data)
    if a.asm:
        Path(a.asm).write_text(f'; Generated by dev/tools/audio/pt3import.py from {Path(a.pt3).name} -- do not edit.\n'
                               f'; {song.name or "song"}: {len(data)} bytes, AYS v{aysong.VERSION}\n'
                               + '\n'.join(aysong.asm_rows(a.label, data)) + '\n')
    if a.json:
        Path(a.json).write_text(aysong.to_json(song))
    if a.report:
        print(rep)
    else:
        i = rep.info
        lost = sum(rep.lost.values())
        print(f"{Path(a.pt3).name}: {len(data)} bytes, {i['patterns']} patterns x {i['rows']} rows, "
              f"{i['instruments']} instruments, speed {i['speed']}, worst pitch {i['worst_cents']:.1f} cents, "
              f"{lost} lost feature uses" + (f"; limits: {'; '.join(rep.limits)}" if rep.limits else ''))


if __name__ == '__main__':
    main()
