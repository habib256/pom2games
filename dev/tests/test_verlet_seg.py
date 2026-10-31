#!/usr/bin/env python3
"""lib/physics verlet_seg.asm in a2run against dev/tools/verlet/segments.py,
bit for bit.

Configuration A (y 8.8, 3 points, 22 segments: a floor, a 45 degree slope,
a vertical wall and a ceiling joined in one polyline, a 76 degree slope, a
lone plank (its ends), a closed 16-segment loop of radius 30 at x 570..630 (16-bit
boxes)): single vl_seg_ground calls from states placed along every segment
(before its start, after its end, both sides, deep behind it, far away),
the hooks (tangent friction, after counter); then 3 points riding the loop
for 600 ticks (integrate + the segment ground), one of them going round.
Configuration B: the same shapes 200 rows lower with VL_Y_HIGH (y 16.8,
16-bit row boxes), a wall across row 256, points above row 0. Configuration
C: VL_GROUND_KIND (vl_ground_any: point 0 on a height map, 1 and 2 on the
segments). Then the switch errors and the cycles of a call (a2run call:).

    python3 dev/tests/test_verlet_seg.py [--cycles]
"""
from pathlib import Path
import math
import random
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
from verlet import Points, HeightMap, SegmentGround, harness, emit  # noqa: E402
from verlet.fixed import le  # noqa: E402
import a2test  # noqa: E402

N = 3
G, VMAX = 0x0008, 0x0800
LOOP_R = 30
RADIUS, DEPTH, BOUNCE, TANGENT = 0x0300, 0x0400, 48, 7
CACHE = 0x0200                              # VL_SEG_CACHE: 2 px from the ends


def world(dy=0, y_high=False, cache=None):
    """The test segments (rows + dy)."""
    kw = dict(radius=RADIUS, depth=DEPTH, bounce=BOUNCE, y_high=y_high, cache=cache)
    parts = [SegmentGround.from_polyline([(20, 200 + dy), (80, 200 + dy), (120, 160 + dy), (120, 100 + dy),
                                          (60, 100 + dy)], **kw),
             SegmentGround.from_polyline([(200, 230 + dy), (210, 190 + dy)], **kw),
             SegmentGround.from_polyline([(300, 150 + dy), (340, 150 + dy)], **kw),
             SegmentGround.from_polyline([(600 + LOOP_R * math.sin(2 * math.pi * k / 16),
                                           120 + dy + LOOP_R * math.cos(2 * math.pi * k / 16)) for k in range(16)],
                                         closed=True, **kw)]
    if y_high:                              # a wall across row 256
        parts.append(SegmentGround.from_polyline([(400, 300), (400, 230)], **kw))
    return SegmentGround([s for g in parts for s in g.specs()], **kw)


LOOP0 = 6                                   # the loop's first segment in world()


def prelude(g, extra=''):
    yh = ('VL_Y_HIGH = 1\n' if g.y_high else '') + (f'VL_SEG_CACHE = {g.cache}\n' if g.cache is not None else '')
    return f'''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
VL_NPOINTS = {N}
VL_GRAVITY = {G}
VL_VMAX_X = {VMAX}
VL_VMAX_Y = {VMAX}
VL_GROUND = {N}
VL_RADIUS = {RADIUS}
VL_BOUNCE = {BOUNCE}
VL_GROUND_SEGMENTS = {g.n}
VL_SEG_DEPTH = {DEPTH}
{yh}{extra}.include "verlet.inc"
.macro VL_GROUND_TANGENT
        LDY     #8 - {TANGENT}
        JSR     vl_damp
.endmacro
.macro VL_GROUND_AFTER
        INC     t_after
.endmacro
.segment "ZEROPAGE"
t_pt:   .res 1
.segment "BSS"
t_after: .res 1
.segment "RODATA"
''' + '\n'.join(g.table_lines()) + '\n.code\n'


EPI_TAIL = '''
.include "verlet_seg.asm"
.include "verlet_hmap.asm"
.include "verlet.asm"
.include "mul.asm"
'''
EPI_CALL = f'''
tick:   LDA     #0
        STA     vl_vt
        STA     vl_vt+1
        STA     t_after
        LDX     #{N - 1}
:       STA     vl_gnd,X
        DEX
        BPL     :-
        LDX     t_pt
        JMP     vl_seg_ground
cyc:    LDX     t_pt
        JMP     vl_seg_ground
''' + EPI_TAIL


def hook(i, v):
    return v - (v >> TANGENT)


def model_call(g, st, pt, sgi):
    p = Points.from_soa(bytes(st), N, g.y_high)
    gnd, sgi, vt, after = [0] * N, list(sgi), 0, 0
    g.sgi = dict(enumerate(sgi))
    r = g.contact(p, pt, hook)
    sgi[pt] = g.sgi[pt]
    if r is not None:
        gnd[pt], vt, after = 1, r, 1
    return p.soa_bytes() + bytes(gnd + sgi) + bytes(le(vt, 2)) + bytes([after])


def snaps(g):
    return [('vl_xf', (12 if g.y_high else 10) * N), ('vl_gnd', 2 * N), ('vl_vt', 2), ('t_after', 1)]


def at(sg, s, d):
    """8.8 point s px along segment sg's tangent and d px along its normal."""
    ln = math.hypot(sg.nx, sg.ny)
    tx, ty = -sg.ny / ln, sg.nx / ln
    nx, ny = sg.nx / ln, sg.ny / ln
    return sg.x0 + int(round((tx * s + nx * d) * 256)), sg.y0 + int(round((ty * s + ny * d) * 256))


def cases(g, rng):
    """(state bytes, point) rows: along every segment, its ends, both sides,
    behind it, far away."""
    rows = []
    seglen = [sg.smax / 256 for sg in g.segs]
    for k, sg in enumerate(g.segs):
        for j in range(26):
            i = rng.randrange(N)
            if j < 4:                           # around the ends
                s = rng.choice([-1, 1]) * rng.uniform(0, 3) + (0 if j < 2 else seglen[k])
            else:
                s = rng.uniform(-2, seglen[k] + 2)
            d = rng.choice([rng.uniform(-1, 3.5), rng.uniform(-6, 6), rng.uniform(-0.5, 0.5),
                            rng.uniform(2.5, 3.2)])
            x, y = at(sg, s, d)
            rows.append((state(g, rng, i, x, y), i, last(g, rng, i, k)))
    for j in range(60):                         # anywhere: mostly no box, no contact
        i = rng.randrange(N)
        x = rng.randrange(0, 700 << 8)
        y = rng.randrange(-0x3000 if g.y_high else 0, (0x1C000 if g.y_high else 0xFF00))
        rows.append((state(g, rng, i, x, y), i, last(g, rng, i, rng.randrange(g.n))))
    return rows


def last(g, rng, i, k):
    """vl_sgi before the call: point i's segment k (or another, or none),
    the others anything (0x80: out of range)."""
    out = [rng.choice([0xFF, 0x80, rng.randrange(g.n)]) for _ in range(N)]
    out[i] = rng.choice([k, k, k, rng.randrange(g.n), 0xFF])
    return out


def state(g, rng, i, x, y):
    p = Points(N, y_high=g.y_high)
    for k in range(N):
        px, py = rng.randrange(0x1000, 0x40000), rng.randrange(0x1000, 0xE000)
        p.place(k, px, py)
    p.place(i, x, y)
    sp = rng.choice([0x80, 0x300, 0x600])
    for k in range(N):
        p.ox[k] = p.x[k] - rng.randrange(-sp, sp)
        p.oy[k] = p.y[k] - rng.randrange(-sp, sp)
    return list(p.soa_bytes())


def run_calls(g, rows, extra=''):
    names = [f'vl_{a}+{k}' for a in (('xf', 'xl', 'xh', 'yf', 'yh', 'yu', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh', 'oyu')
                                     if g.y_high else ('xf', 'xl', 'xh', 'yf', 'yh', 'oxf', 'oxl', 'oxh', 'oyf',
                                                       'oyh')) for k in range(N)] + \
        ['t_pt'] + [f'vl_sgi+{k}' for k in range(N)]
    pre, hits, chunk = prelude(g, extra), [0] * g.n, 90
    contacts = 0
    for at0 in range(0, len(rows), chunk):
        part = rows[at0:at0 + chunk]
        script = [(1, st + [pt] + sg, 1) for st, pt, sg in part]
        got = harness.run(pre, EPI_CALL, names, snaps(g), script, init='mul_init', snap_seg='LOWBSS')
        for k, ((st, pt, sg), have) in enumerate(zip(part, got)):
            want = model_call(g, st, pt, sg)
            if want != have:
                raise SystemExit(f'row {at0 + k}, point {pt} (segment {g.hit}):\n  in   {bytes(st).hex(" ")}\n'
                                 f'  want {want.hex(" ")}\n  have {have.hex(" ")}')
            if g.hit is not None:
                hits[g.hit] += 1
                contacts += 1
    return hits, contacts


def ride(g, starts, ticks):
    """The model: integrate every point, then the segment ground for each."""
    p = Points(N, y_high=g.y_high)
    for i, (x, y, vx, vy) in enumerate(starts):
        p.place(i, x, y)
        p.ox[i] -= vx
        p.oy[i] -= vy
    out = []
    for _ in range(ticks):
        p.integrate_all(G, VMAX, VMAX)
        for i in range(N):
            g.contact(p, i, hook)
        out.append(p.copy())
    return p, out


def ride_starts(g, dy=0):
    bottom = g.segs[LOOP0]                      # the loop's bottom: from its start
    x, y = at(bottom, 2, 3)
    x2, y2 = at(g.segs[LOOP0 + 3], 4, 3)
    return [(x, y, 0x0700, 0), (x2, y2, 0, -0x0200), (at(g.segs[0], 10, 3)[0], at(g.segs[0], 10, 3)[1], 0x0300, 0)]


def check_ride(g, ticks=600):
    starts = ride_starts(g)
    p0 = Points(N, y_high=g.y_high)
    for i, (x, y, vx, vy) in enumerate(starts):
        p0.place(i, x, y)
        p0.ox[i] -= vx
        p0.oy[i] -= vy
    init = p0.soa_bytes()
    epi = f'''
init:   JSR     mul_init
        LDA     #$FF
        LDX     #{N - 1}
:       STA     vl_sgi,X
        DEX
        BPL     :-
        LDX     #{len(init) - 1}
:       LDA     t_init,X
        STA     vl_xf,X
        DEX
        BPL     :-
        RTS
tick:   JSR     vl_integrate_all
        LDX     #0
        JSR     vl_seg_ground
        LDX     #1
        JSR     vl_seg_ground
        LDX     #2
        JMP     vl_seg_ground
.segment "RODATA"
t_init: .byte {", ".join(map(str, init))}
.code
''' + EPI_TAIL
    every = 20
    rows = [(every, [], 1) for _ in range(ticks // every)]
    got = harness.run(prelude(g), epi, [], [('vl_xf', (12 if g.y_high else 10) * N)], rows, init='init',
                      snap_seg='LOWBSS')
    p, states = ride(g, starts, ticks)
    for k in range(len(rows)):
        want = states[(k + 1) * every - 1].soa_bytes()
        if want != got[k]:
            raise SystemExit(f'ride, tick {(k + 1) * every}:\n  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
    # the first point goes round the loop: its angle around the centre
    cx, cy = 600 << 8, (120 << 8) + (g.segs[LOOP0].y0 - ((120 + LOOP_R) << 8))
    turns, last, most = 0.0, None, 0.0
    for s in states:
        a = math.atan2(s.y[0] - cy, s.x[0] - cx)
        if last is not None:
            turns += (a - last + math.pi) % (2 * math.pi) - math.pi
        last = a
        most = max(most, abs(turns))
    return len(rows), most / (2 * math.pi)


def kind_check(rng):
    """VL_GROUND_KIND: point 0 on a flat height map at row 180, 1 and 2 on
    the segments."""
    g = world()
    h = [180] * 1024
    hm = HeightMap(h, 15, 2, RADIUS, 0x2000, BOUNCE)
    extra = f'''VL_GROUND_KIND = t_kind
VL_HEIGHTS = t_hmap
VL_PROBE = 2
VL_SLOPE_MAX = 15
VL_FAR = $2000
'''
    tabs = (emit.table_line('vl_norm_x', emit.sb(hm.nx)) + '\n' + emit.table_line('vl_norm_y', emit.sb(hm.ny))
            + '\nt_kind: .byte 0, 1, 1\nt_hmap:\n.repeat 1024\n.byte 180\n.endrepeat\n')
    pre = prelude(g, extra).replace('.segment "RODATA"\n', '.segment "RODATA"\n' + tabs, 1)
    epi = EPI_CALL.replace('JMP     vl_seg_ground\ncyc:', 'JMP     vl_ground_any\ncyc:')
    rows = []
    for j in range(60):
        i = j % N
        if i == 0:
            x, y = rng.randrange(20 << 8, 900 << 8), (180 << 8) + rng.randrange(-0x600, 0x200)
        else:
            sg = g.segs[rng.randrange(g.n)]
            x, y = at(sg, rng.uniform(0, sg.smax / 256), rng.uniform(-1, 3.5))
        rows.append((state(g, rng, i, x, y), i))
    names = [f'vl_{a}+{k}' for a in ('xf', 'xl', 'xh', 'yf', 'yh', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh')
             for k in range(N)] + ['t_pt'] + [f'vl_sgi+{k}' for k in range(N)]
    got = harness.run(pre, epi, names, snaps(g), [(1, st + [pt] + [0xFF] * N, 1) for st, pt in rows],
                      init='mul_init', snap_seg='LOWBSS')
    n = 0
    for (st, pt), have in zip(rows, got):
        if pt == 0:
            p = Points.from_soa(bytes(st), N)
            gnd, sgi, vt, after = [0] * N, [0xFF] * N, 0, 0
            r = hm.contact(p, 0, hook)
            if r is not None:
                gnd[0], vt, after = 1, r, 1
            want = p.soa_bytes() + bytes(gnd + sgi) + bytes(le(vt, 2)) + bytes([after])
        else:
            want = model_call(g, st, pt, [0xFF] * N)
        assert want == have, (pt, bytes(st).hex(' '), want.hex(' '), have.hex(' '))
        n += 1
    return n


def switch_errors():
    """VL_GROUND_SEGMENTS without VL_GROUND, vl_seg_ground without
    VL_GROUND_SEGMENTS: the assembly stops."""
    base = 'MUL_TABLES = $0800\nMUL_ACC = 1\n.include "math.inc"\nVL_NPOINTS = 2\n'
    bad = {'segments without a ground': base + 'VL_GROUND_SEGMENTS = 4\n.include "verlet.inc"\n',
           'vl_seg_ground without segments': base + 'VL_GROUND = 2\nVL_RADIUS = $300\nVL_BOUNCE = 0\n'
           '.include "verlet.inc"\n JSR vl_seg_ground\n.include "verlet_seg.asm"\n'}
    inc = [a for d in harness.INCLUDES for a in ('-I', str(d))]
    with tempfile.TemporaryDirectory(prefix='verlet-seg-sw-') as tmp:
        for name, text in bad.items():
            (Path(tmp) / 's.s').write_text(text)
            r = subprocess.run(['ca65', *inc, '-o', str(Path(tmp) / 's.o'), str(Path(tmp) / 's.s')],
                               capture_output=True, text=True)
            assert r.returncode != 0 and 'VL_GROUND' in r.stderr, (name, r.stderr)
    return len(bad)


CYCLE_CASES = [('no box (empty sky)', None, 0, 0), ('in a box, above the line', 0, 20, 4.5),
               ('flat floor, contact', 0, 30, 2), ('45 degree slope, contact', 1, 20, 2),
               ('vertical wall, contact', 2, 30, 2), ('loop segment, contact', LOOP0 + 2, 6, 2),
               ('loop joint, contact', LOOP0 + 2, 11, 2), ('concave corner floor / slope', 1, 0.5, 2)]


def cycles(g):
    """a2run call: cycles of vl_seg_ground (X = the point; +7 for the LDX
    and the JMP) on chosen states; with g.cache, vl_sgi = the segment the
    point is on (the cached path when it is well inside it)."""
    rows = []
    for name, k, s, d in CYCLE_CASES:
        p = Points(N, y_high=g.y_high)
        for i in range(N):
            p.place(i, 0x1000, 0x1000)
        if k is None:
            p.place(0, 450 << 8, 20 << 8)
        else:
            x, y = at(g.segs[k], s, d)
            p.place(0, x, y)
        p.ox[0] -= 0x100
        p.oy[0] -= 0x080
        rows.append((name, list(p.soa_bytes()), [0xFF if k is None or g.cache is None else k] + [0xFF] * (N - 1)))
    text = harness.source(prelude(g), EPI_CALL, ['t_pt'], [('vl_xf', 1)], [(1, [0], 0)])
    with tempfile.TemporaryDirectory(prefix='verlet-seg-cyc-') as tmp:
        lab, binary = harness.build(tmp, text)
        steps = a2test.bin_steps(binary, 0x6000, lab['mul_init'])[:1] + [f'call:{lab["mul_init"]:04X}:20']
        for name, st, sg in rows:
            steps += [lab.poke('t_pt', 0)] + [lab.poke('vl_xf', v, k) for k, v in enumerate(st)]
            steps += [lab.poke('vl_sgi', v, k) for k, v in enumerate(sg)] + [f'call:{lab["cyc"]:04X}:5']
        r = a2test.run(None, steps)
        el = [int(v) for v in re.findall(r'elapsed=(\d+)', r.out)][1:]
    out = {}
    for (name, st, sg), c in zip(rows, el):
        want = model_call(g, st, 0, sg)
        out[name] = (c, want[(12 if g.y_high else 10) * N] == 1)
    return out


def main():
    rng = random.Random(31)
    g = world()
    assert max(abs(e) for e in g.end_errors()) <= 2, g.end_errors()
    rows = cases(g, rng)
    hits, contacts = run_calls(g, rows)
    assert all(hits), [k for k, h in enumerate(hits) if not h]
    print(f'lib/physics segments, y 8.8, {g.n} segments: {len(rows)} vl_seg_ground calls == segments.py '
          f'({contacts} contacts, every segment touched)')
    snaps_n, turns = check_ride(g)
    assert turns >= 1.0, turns
    print(f'  loop ride: 3 points, 600 ticks == model in {snaps_n} snapshots; point 0 goes round '
          f'{turns:.2f} times')
    gh = world(200, y_high=True, cache=CACHE)
    rows = cases(gh, rng)
    hits, contacts = run_calls(gh, rows)
    assert all(hits), [k for k, h in enumerate(hits) if not h]
    print(f'lib/physics segments, VL_Y_HIGH + VL_SEG_CACHE, {gh.n} segments (rows 270..430, a wall across '
          f'row 256): {len(rows)} calls == segments.py ({contacts} contacts)')
    snaps_n, turns = check_ride(gh)
    assert turns >= 1.0, turns
    print(f'  loop ride, VL_Y_HIGH + VL_SEG_CACHE: 600 ticks == model in {snaps_n} snapshots; {turns:.2f} turns')
    gc = world(cache=CACHE)
    rows = cases(gc, rng)
    run_calls(gc, rows)
    print(f'lib/physics segments, y 8.8 + VL_SEG_CACHE: {len(rows)} calls == segments.py')
    print(f'VL_GROUND_KIND (vl_ground_any): {kind_check(rng)} calls, height map and segments == models')
    print(f'switch errors: {switch_errors()} cases stop the assembly')
    if '--cycles' in sys.argv:
        a, b = cycles(g), cycles(gc)
        for name, (c, hit) in a.items():
            print(f'  vl_seg_ground {name}: {c:,} cycles, {b[name][0]:,} with the cache'
                  f'{" (contact)" if hit else ""}')


if __name__ == '__main__':
    main()
