#!/usr/bin/env python3
"""lib/physics in a2run against dev/tools/verlet, bit for bit.

Configuration 1 (3 points, every switch on, ground with hooks): vl_integrate
(clamps, sign edges, left wall), vl_constrain (q clamp 180, d8 +-4095, f
+-127, heavy rounding toward zero, the squash alarm, variant rows), vl_ground
on every slope -20..20 (clamped to +-15, the flat short cut, far above and
below), vl_pair_damp, vl_turn_pair, vl_shift_point, vl_wrap (and its hook),
vl_ceiling, vl_rest, vl_integrate_all, vl_con_pass, vl_delta_ab: one call per
row from a random or edge state. Configuration 2 (5-point rope, 4 links, no
ground, no switch): the library's own zero page (20 bytes) and points, 300
ticks of integrate_all + 2 passes + a moving pin. Then the switches: left
out, the code is the plain variant (or the routine that needs one stops
the assembly); defined, it changes the code. Configuration 3 (4 points,
the newer switches: VL_Y_HIGH with a ground base, VL_PIN, VL_CON_FIXED_K,
VL_CON_MIN_ONLY, VL_THRUST) runs 1,020 single calls the same way (y across
the 256-row boundaries and above row 0, every pin case of a link, the
ground far above / below in 24 bits); configuration 4 is a pinned 8-point
rope of fixed-gain links (its end pinned for a while), 320 ticks;
configuration 5 a 3-point lander in a 16.8 world, thrust and turns from an
autopilot run on the model, 850 ticks down to the ground.

    python3 dev/tests/test_verlet.py
"""
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
from verlet import Points, Constraint, HeightMap, constrain, tables, emit  # noqa: E402
from verlet import harness  # noqa: E402
from verlet.fixed import l2q, le  # noqa: E402

N1 = 3
G, VX, VY = 0x0030, 0x1200, 0x0800
WALL, CEIL, MARGIN = 0x1000, 0x0800, 128
RADIUS, PROBE, SLOPE_MAX, FAR, BOUNCE = 0x0600, 2, 15, 0x2000, 64
HEAVY, PAIR, SHIFT_PT, TANGENT = 3, 4, 2, 5
NV = 2
CONS1 = [Constraint(0, 1, 24, 1.0, variants=[24, 30]),
         Constraint(0, 2, 20, 0.9, heavy=HEAVY, minlen=10, variants=[20, 40]),
         Constraint(1, 2, 21.6, 1.5, heavy=HEAVY, minlen=10, variants=[21.6, 50])]
TAB1 = tables(CONS1, NV)
MINLEN = l2q(10)
OPS = ['int', 'con', 'gnd', 'pd', 'turn', 'shift', 'wrap', 'ceil', 'rest', 'iall', 'pass', 'delta']


def hmap():
    """Ramps of slope s over 4 px for s = 0, 1, -1, ..., 20, -20, 24 px each."""
    h, y = [128] * 16, 128 * 4
    for s in [0] + [v for k in range(1, 21) for v in (k, -k)]:
        for _ in range(24):
            y += s
            h.append(y // 4)
    return h + [h[-1]] * 16


HMAP = hmap()


def con_tables(tab):
    return [emit.table_line('vl_con_a', tab['con_a']), emit.table_line('vl_con_b', tab['con_b']),
            emit.table_line('vl_con_l2l', emit.lo(tab['con_l2'])),
            emit.table_line('vl_con_l2h', emit.hi(tab['con_l2'])),
            emit.table_line('vl_con_k8', tab['con_k8'])]


def prelude1():
    hm = HeightMap(HMAP, SLOPE_MAX, PROBE)
    return f'''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
VL_NPOINTS = {N1}
VL_NCON = {len(CONS1)}
VL_GRAVITY = {G}
VL_VMAX_X = {VX}
VL_VMAX_Y = {VY}
VL_GROUND = {N1}
VL_HEIGHTS = t_hmap
VL_RADIUS = {RADIUS}
VL_PROBE = {PROBE}
VL_SLOPE_MAX = {SLOPE_MAX}
VL_FAR = {FAR}
VL_BOUNCE = {BOUNCE}
VL_WRAP_MARGIN = {MARGIN}
VL_INTEGRATE_LEFTWALL = {WALL}
VL_CEILING_CLAMP = {CEIL}
VL_CON_VARIANTS = {NV}
VL_CON_HEAVY_POINT = 2
VL_CON_HEAVY_SHIFT = {HEAVY}
VL_CON_MINLEN_POINT = 2
VL_CON_MINLEN = {MINLEN}
VL_PAIR_DAMP = {PAIR}
VL_SHIFT_POINT = {SHIFT_PT}
.include "verlet.inc"
.macro VL_GROUND_TANGENT
        LDY     #8 - {TANGENT}
        JSR     vl_damp
.endmacro
.macro VL_WRAP_AFTER
        INC     t_wr
.endmacro
.segment "ZEROPAGE"
t_op:   .res 1
t_pt:   .res 1
.segment "BSS"
t_wr:   .res 1
.segment "RODATA"
''' + '\n'.join(con_tables(TAB1)) + '\n' + \
        emit.table_line('vl_norm_x', emit.sb(hm.nx)) + '\n' + emit.table_line('vl_norm_y', emit.sb(hm.ny)) + \
        '\nt_hmap: .byte ' + ', '.join(map(str, HMAP)) + '\n.code\n'


EPILOGUE1 = '''
tick:   LDA     #0                      ; the outputs, cleared
        STA     vl_dx
        STA     vl_dx+1
        STA     vl_dy
        STA     vl_dy+1
        STA     vl_vt
        STA     vl_vt+1
        STA     vl_gnd
        STA     vl_gnd+1
        STA     vl_gnd+2
        STA     vl_cidx
        STA     vl_squashed
        STA     t_wr
        LDA     t_op
        ASL     A
        TAX
        LDA     ops+1,X
        PHA
        LDA     ops,X
        PHA
        LDX     t_pt
        RTS
ops:    .word   vl_integrate-1, vl_constrain-1, vl_ground-1, vl_pair_damp-1, vl_turn_pair-1
        .word   vl_shift_point-1, vl_wrap-1, vl_ceiling-1, vl_rest-1, vl_integrate_all-1
        .word   vl_con_pass-1, vl_delta_ab-1
.include "verlet_hmap.asm"
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
'''
STATE = [f'vl_{a}+{i}' for a in ('xf', 'xl', 'xh', 'yf', 'yh', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh') for i in range(N1)]
INPUTS1 = STATE + ['t_op', 't_pt', 'vl_cur', 'vl_con_row', 'vl_turn', 'vl_lap_len', 'vl_lap_len+1',
                   'vl_ca', 'vl_cb']
# vl_gnd (3), vl_turn, vl_con_row, vl_cidx, vl_squashed are contiguous (verlet.inc)
SNAPS1 = [('vl_xf', 10 * N1), ('vl_gnd', N1 + 4), ('vl_dx', 4), ('vl_vt', 2), ('t_wr', 1)]


def s8(v):
    return v - 256 if v & 0x80 else v


def model1(row):
    """One row of configuration 1 in Python -> the expected snapshot."""
    st, op, pt, cur, crow, turn, lap, ca, cb = row
    p = Points.from_soa(bytes(st), N1)
    gnd, cidx, sq, dxy, vt, wr = [0] * N1, 0, 0, (0, 0), 0, 0
    hm = HeightMap(HMAP, SLOPE_MAX, PROBE, RADIUS, FAR, BOUNCE)

    def one(c):
        nonlocal dxy, sq, cidx
        a, b = TAB1['con_a'][c], TAB1['con_b'][c]
        cidx = c * NV + crow
        dxy = p.delta(a, b)
        if constrain(p, a, b, TAB1['con_l2'][cidx], TAB1['con_k8'][cidx],
                     HEAVY if b == 2 else 0, MINLEN if b == 2 else None):
            sq = 1
    name = OPS[op]
    if name == 'int':
        p.integrate(pt, G, VX, VY, WALL)
    elif name == 'con':
        one(cur)
    elif name == 'pass':
        for c in range(len(CONS1)):
            one(c)
    elif name == 'gnd':
        r = hm.contact(p, pt, lambda i, v: v - (v >> TANGENT))
        if r is not None:
            gnd[pt], vt = 1, r
    elif name == 'pd':
        p.pair_damp(0, 1, PAIR)
    elif name in ('turn', 'shift'):
        dxy = p.delta(0, 1)
        if name == 'turn':
            p.turn_pair(0, 1, s8(turn))
        else:
            p.shift_point(SHIFT_PT, 0, 1, s8(turn))
    elif name == 'wrap':
        wr = int(p.wrap(lap, MARGIN))
    elif name == 'ceil':
        p.ceiling(CEIL)
    elif name == 'rest':
        p.rest()
    elif name == 'iall':
        p.integrate_all(G, VX, VY, WALL)
    elif name == 'delta':
        dxy = p.delta(ca, cb)
    return (p.soa_bytes() + bytes(gnd + [turn & 0xFF, crow, cidx, sq]) + bytes(le(dxy[0], 2) + le(dxy[1], 2))
            + bytes(le(vt, 2)) + bytes([wr]))


def state(xs, ys, oxs, oys):
    p = Points(N1)
    p.x, p.y, p.ox, p.oy = [v & 0xFFFFFF for v in xs], [v & 0xFFFF for v in ys], \
        [v & 0xFFFFFF for v in oxs], [v & 0xFFFF for v in oys]
    return list(p.soa_bytes())


def row(st, op, pt=0, cur=0, crow=0, turn=0, lap=0, ca=0, cb=1):
    return (st, OPS.index(op), pt, cur, crow, turn & 0xFF, lap, ca, cb)


def cases(rng):
    rows = []
    edges = [0, 1, -1, VX - 1, VX, VX + 1, -VX + 1, -VX, -VX - 1, 0x7FFF, -0x8000, 0x7FD0, -0x7FFF]
    edges_y = [0, 1, -1, VY - G - 1, VY - G, VY - G + 1, -VY - G - 1, -VY - G, -VY, 0x7FD0, 0x7FCF, -0x8000]
    # integrate: clamps, sign edges, the wall (x stays >= 0 on the 6502 side)
    for k in range(150):
        i = k % N1
        xs = [rng.randrange(0x2000, 0xF00000) for _ in range(N1)]
        ys = [rng.randrange(0x1000, 0xF000) for _ in range(N1)]
        vx = edges[k % len(edges)] if k < 60 else rng.randrange(-0x2000, 0x2000)
        vy = edges_y[k % len(edges_y)] if k < 60 else rng.randrange(-0x1000, 0x1000)
        if k >= 100:                                    # around the wall
            xs[i] = rng.randrange(0x0800, 0x2400)
            vx = rng.randrange(-0x0800, 0x0400)
            if xs[i] + max(-VX, min(VX, vx)) < 0:
                vx = 0
        oxs, oys = list(xs), list(ys)
        oxs[i] = xs[i] - vx
        oys[i] = ys[i] - vy
        rows.append(row(state(xs, ys, oxs, oys), 'int', pt=i))
    # constraints: rest, stretched, squashed, q = 180 edges, both signs
    qedge = [11519, 11520, 11583, 11584, 11585, 20000, 32767, -32768, -11520, -11584, -11585]
    for k in range(260):
        cur, crow = k % 3, (k // 3) % NV
        a, b = TAB1['con_a'][cur], TAB1['con_b'][cur]
        xs = [rng.randrange(0x10000, 0x200000) for _ in range(N1)]
        ys = [rng.randrange(0x3000, 0xB000) for _ in range(N1)]
        kind = k % 5
        if kind == 0:
            dx, dy = rng.randrange(-0x7F00, 0x7F00), rng.randrange(-0x7F00, 0x7F00)
        elif kind == 1:
            dx, dy = qedge[k % len(qedge)], rng.choice([0, 64, -64, 11584, -11585])
        elif kind == 2:
            dx, dy = rng.randrange(-0x600, 0x600), rng.randrange(-0x600, 0x600)
        else:
            L = CONS1[cur].length * 256 * rng.uniform(0.8, 1.25)
            dx = int(rng.uniform(-1, 1) * L)
            dy = int(rng.choice([-1, 1]) * max(0, L * L - dx * dx) ** 0.5)
        xs[b] = xs[a] + dx
        ys[b] = ys[a] + dy
        oxs = [x - rng.randrange(-0x300, 0x300) for x in xs]
        oys = [y - rng.randrange(-0x300, 0x300) for y in ys]
        rows.append(row(state(xs, ys, oxs, oys), 'con', cur=cur, crow=crow))
    # ground: every slope, near / far / under the ground
    for k in range(420):
        i = k % N1
        px = rng.randrange(8, len(HMAP) - 8) if k >= 60 else 16 + 12 + 24 * (k % 41)
        off = rng.choice([rng.randrange(-0x0C00, 0x0C00), rng.randrange(-0x3000, 0x3000),
                          rng.randrange(-0x0700, 0x0100)])
        xs = [rng.randrange(0x1000, 0xF0000) for _ in range(N1)]
        ys = [rng.randrange(0x1000, 0xF000) for _ in range(N1)]
        xs[i] = px << 8 | rng.randrange(256)
        ys[i] = max(0, min(0xFFFF, (HMAP[px] << 8) + off))
        oxs = list(xs)
        oys = list(ys)
        oxs[i] -= rng.randrange(-0x1000, 0x1000)
        oys[i] -= rng.randrange(-0x0800, 0x0800)
        rows.append(row(state(xs, ys, oxs, oys), 'gnd', pt=i))
    # the rest: pair damping, turns, shifts, wrap, ceiling, rest, all points,
    # a whole pass, deltas
    for k in range(300):
        op = ['pd', 'turn', 'shift', 'wrap', 'ceil', 'rest', 'iall', 'pass', 'delta'][k % 9]
        x0 = rng.randrange(0x10000, 0x400000)
        xs = [x0 + rng.randrange(-0x4000, 0x4000) for _ in range(N1)]
        y0 = rng.randrange(0x2000, 0xC000)
        ys = [y0 + rng.randrange(-0x2000, 0x2000) for _ in range(N1)]
        if op == 'ceil':
            ys = [rng.randrange(0x0600, 0x0A00) for _ in range(N1)]
        lap = 0
        if op == 'wrap':
            lap = rng.choice([0, rng.randrange(200, 3000)])
            xs[0] = ((lap + MARGIN + rng.randrange(-2, 3)) << 8) + rng.randrange(256)
        oxs = [x - rng.randrange(-0x1400, 0x1400) for x in xs]
        oys = [y - rng.randrange(-0x0A00, 0x0A00) for y in ys]
        turn = rng.choice([rng.randrange(-128, 128), 1, -1, 4, -4, 64, -64, 127, -128])
        rows.append(row(state(xs, ys, oxs, oys), op, turn=turn, crow=rng.randrange(NV), lap=lap,
                        ca=rng.randrange(N1), cb=rng.randrange(N1)))
    return rows


def check1(rng):
    rows = cases(rng)
    slopes = set()
    hm = HeightMap(HMAP, SLOPE_MAX, PROBE)
    for r in rows:
        if OPS[r[1]] == 'gnd':
            p = Points.from_soa(bytes(r[0]), N1)
            slopes.add(hm.slope(p.x[r[2]] >> 8))
    assert slopes >= set(range(-SLOPE_MAX, SLOPE_MAX + 1)), sorted(set(range(-15, 16)) - slopes)
    pre, size, chunk = prelude1(), sum(n for _, n in SNAPS1), 85
    counts = {}
    for at in range(0, len(rows), chunk):
        part = rows[at:at + chunk]
        script = [(1, list(r[0]) + [r[1], r[2], r[3], r[4], r[5], r[6] & 0xFF, r[6] >> 8, r[7], r[8]], 1)
                  for r in part]
        got = harness.run(pre, EPILOGUE1, INPUTS1, SNAPS1, script, init='mul_init', snap_seg='LOWBSS')
        for k, (r, have) in enumerate(zip(part, got)):
            want = model1(r)
            if want != have:
                raise SystemExit(f'config 1, {OPS[r[1]]} row {at + k}: point {r[2]} cur {r[3]} row {r[4]} '
                                 f'turn {r[5]}\n  in   {bytes(r[0]).hex(" ")}\n  want {want.hex(" ")}\n'
                                 f'  have {have.hex(" ")}')
            counts[OPS[r[1]]] = counts.get(OPS[r[1]], 0) + 1
    assert len(want) == size
    print(f'lib/physics, 3 points, every switch: {len(rows)} calls == verlet '
          f'({", ".join(f"{k} {v}" for k, v in counts.items())}); slopes {min(slopes)}..{max(slopes)}')


# --- configuration 2: a rope, the library's own variables ---------------------------
N2 = 5
LINK = 12
CONS2 = [Constraint(i, i + 1, LINK, 1.0) for i in range(N2 - 1)]
G2, V2 = 0x0020, 0x0800
PIN_Y = 40


def prelude2():
    return f'''MUL_TABLES = $0800
.include "math.inc"
VL_NPOINTS = {N2}
VL_NCON = {len(CONS2)}
VL_GRAVITY = {G2}
VL_VMAX_X = {V2}
VL_VMAX_Y = {V2}
.include "verlet.inc"
.segment "BSS"
t_ax:   .res 1
.segment "RODATA"
''' + '\n'.join(con_tables(tables(CONS2))) + f'\nt_init: .byte {", ".join(map(str, rope0().soa_bytes()))}\n.code\n'


EPILOGUE2 = f'''
init:   JSR     mul_init
        LDX     #10 * {N2} - 1
:       LDA     t_init,X
        STA     vl_xf,X
        DEX
        BPL     :-
        RTS
tick:   JSR     vl_integrate_all
        JSR     vl_con_pass
        JSR     vl_con_pass
        LDA     t_ax                    ; the pin: point 0 at (t_ax, {PIN_Y}), at rest
        STA     vl_xl
        STA     vl_oxl
        LDA     #0
        STA     vl_xf
        STA     vl_oxf
        STA     vl_xh
        STA     vl_oxh
        STA     vl_yf
        STA     vl_oyf
        LDA     #{PIN_Y}
        STA     vl_yh
        STA     vl_oyh
        RTS
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
'''


def rope0():
    p = Points(N2)
    for i in range(N2):
        p.place(i, (60 + LINK * i) << 8, PIN_Y << 8)
    return p


def check2():
    rows = [(20, [ax], 1) for ax in (60, 60, 70, 90, 120, 120, 100, 60, 40, 40, 80, 140, 140, 100, 60)]
    with tempfile.TemporaryDirectory(prefix='verlet-rope-') as tmp:
        got = harness.run(prelude2(), EPILOGUE2, ['t_ax'], [('vl_xf', 10 * N2)], rows, init='init',
                          work=tmp)
        lbl = (Path(tmp) / 'h.lbl').read_text()
    zp = {line.split('.')[1] for line in lbl.splitlines() if line.split()[1] < '000100' and '.vl_' in line}
    tier2 = {'vl_val', 'vl_vx', 'vl_w0', 'vl_w1', 'vl_w2', 'vl_dx', 'vl_dy', 'vl_ca', 'vl_cb', 'vl_cur',
             'vl_qx', 'vl_fcoef', 'vl_pen', 'vl_vn'}
    assert zp == tier2, sorted(zp ^ tier2)
    assert '.vl_gnd' not in lbl and '.vl_vt' not in lbl, 'rope: ground variables allocated'
    p, k = rope0(), 0
    for n, (ax,), _ in rows:
        for _ in range(n):
            p.integrate_all(G2, V2, V2)
            for _ in range(2):
                for c in CONS2:
                    c.apply(p)
            p.place(0, ax << 8, PIN_Y << 8)
        want = p.soa_bytes()
        if want != got[k]:
            raise SystemExit(f'rope, snapshot {k}:\n  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
        k += 1
    sag = (p.y[N2 - 1] - p.y[0]) / 256
    print(f'lib/physics, a 5-point rope (4 links, no ground, no switch): {sum(r[0] for r in rows)} ticks '
          f'== verlet in {k} snapshots (end sags {sag:.1f} px); zero page = the 20-byte tier')


# --- configuration 3: the new switches, one call per row -----------------------------
# VL_Y_HIGH (y 16.8, ground base), VL_PIN, VL_CON_FIXED_K, VL_CON_MIN_ONLY,
# VL_THRUST (+ VL_PAIR_DAMP, VL_SHIFT_POINT, VL_CEILING_CLAMP on 24-bit y)
N3 = 4
FK3, TH3, BASE3 = 5, 3, 0x0140
CONS3 = [Constraint(0, 1, 16, fixed_k=FK3), Constraint(1, 2, 20, fixed_k=FK3, min_only=True),
         Constraint(2, 3, 12, fixed_k=FK3), Constraint(0, 3, 30, fixed_k=FK3, min_only=True)]
TAB3 = tables(CONS3)
OPS3 = ['int', 'con', 'gnd', 'pd', 'turn', 'shift', 'ceil', 'rest', 'iall', 'pass', 'delta',
        'thra', 'thrp', 'push', 'pall']


def prelude3():
    hm = HeightMap(HMAP, SLOPE_MAX, PROBE)
    return f'''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
VL_NPOINTS = {N3}
VL_NCON = {len(CONS3)}
VL_GRAVITY = {G}
VL_VMAX_X = {VX}
VL_VMAX_Y = {VY}
VL_GROUND = {N3}
VL_HEIGHTS = t_hmap
VL_RADIUS = {RADIUS}
VL_PROBE = {PROBE}
VL_SLOPE_MAX = {SLOPE_MAX}
VL_FAR = {FAR}
VL_BOUNCE = {BOUNCE}
VL_GROUND_BASE = {BASE3}
VL_Y_HIGH = 1
VL_PIN = 1
VL_CON_FIXED_K = {FK3}
VL_CON_MIN_ONLY = 1
VL_THRUST = {TH3}
VL_CEILING_CLAMP = {CEIL}
VL_PAIR_DAMP = {PAIR}
VL_SHIFT_POINT = {SHIFT_PT}
.include "verlet.inc"
.macro VL_GROUND_TANGENT
        LDY     #8 - {TANGENT}
        JSR     vl_damp
.endmacro
.segment "ZEROPAGE"
t_op:   .res 1
t_pt:   .res 1
.segment "RODATA"
''' + '\n'.join(con_tables(TAB3)[:4]) + '\n' + \
        emit.table_line('vl_norm_x', emit.sb(hm.nx)) + '\n' + emit.table_line('vl_norm_y', emit.sb(hm.ny)) + \
        '\nt_hmap: .byte ' + ', '.join(map(str, HMAP)) + '\n.code\n'


EPILOGUE3 = '''
tick:   LDA     #0
        LDX     #3
:       STA     vl_dx,X
        STA     vl_gnd,X
        DEX
        BPL     :-
        STA     vl_vt
        STA     vl_vt+1
        LDA     t_op
        ASL     A
        TAX
        LDA     ops+1,X
        PHA
        LDA     ops,X
        PHA
        LDX     t_pt
        RTS
ops:    .word   vl_integrate-1, vl_constrain-1, vl_ground-1, vl_pair_damp-1, vl_turn_pair-1
        .word   vl_shift_point-1, vl_ceiling-1, vl_rest-1, vl_integrate_all-1, vl_con_pass-1
        .word   vl_delta_ab-1, vl_thrust_axis-1, vl_thrust_perp-1, vl_push-1, vl_push_all-1
.include "verlet_hmap.asm"
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
'''
STATE3 = [f'vl_{a}+{i}' for a in ('xf', 'xl', 'xh', 'yf', 'yh', 'yu', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh', 'oyu')
          for i in range(N3)]
INPUTS3 = STATE3 + [f'vl_pin+{i}' for i in range(N3)] + ['t_op', 't_pt', 'vl_cur', 'vl_turn', 'vl_ca', 'vl_cb',
                                                          'vl_tx', 'vl_tx+1', 'vl_ty', 'vl_ty+1']
# vl_x* .. vl_oyu, vl_pin, vl_gnd, vl_turn are contiguous (verlet.inc)
SNAPS3 = [('vl_xf', 14 * N3 + 1), ('vl_dx', 4), ('vl_vt', 2), ('vl_tx', 4)]


def model3(row):
    st, pins, op, pt, cur, turn, ca, cb, tv = row
    p = Points.from_soa(bytes(st), N3, y_high=True)
    p.pin = list(pins)
    gnd, dxy, vt = [0] * N3, (0, 0), 0
    tx, ty = tv
    hm = HeightMap(HMAP, SLOPE_MAX, PROBE, RADIUS, FAR, BOUNCE, base=BASE3)

    def one(c):
        nonlocal dxy
        a, b = CONS3[c].a, CONS3[c].b
        dxy = p.delta(a, b)
        CONS3[c].apply(p)
    name = OPS3[op]
    k = s8(turn)
    if name == 'int':
        p.integrate(pt, G, VX, VY)
    elif name == 'con':
        one(cur)
    elif name == 'pass':
        for c in range(len(CONS3)):
            one(c)
    elif name == 'gnd':
        r = hm.contact(p, pt, lambda i, v: v - (v >> TANGENT))
        if r is not None:
            gnd[pt], vt = 1, r
    elif name == 'pd':
        p.pair_damp(0, 1, PAIR)
    elif name in ('turn', 'shift'):
        dxy = p.delta(0, 1)
        if name == 'turn':
            p.turn_pair(0, 1, k)
        else:
            p.shift_point(SHIFT_PT, 0, 1, k)
    elif name == 'ceil':
        p.ceiling(CEIL)
    elif name == 'rest':
        p.rest()
    elif name == 'iall':
        p.integrate_all(G, VX, VY)
    elif name == 'delta':
        dxy = p.delta(ca, cb)
    elif name in ('thra', 'thrp'):
        tx, ty = p.thrust(0, 1, k, TH3, perp=name == 'thrp')
        dx, dy = p.delta(0, 1)
        dxy = (dx, dy) if name == 'thra' else (-dy, dx)
    elif name == 'push':
        p.push(pt, (tx, ty))
    elif name == 'pall':
        p.push_all((tx, ty))
    return (p.soa_bytes() + bytes(pins) + bytes(gnd) + bytes([turn & 0xFF]) + bytes(le(dxy[0], 2) + le(dxy[1], 2))
            + bytes(le(vt, 2)) + bytes(le(tx, 2) + le(ty, 2)))


def cases3(rng):
    rows = []

    def st(xs, ys, oxs, oys):
        p = Points(N3, y_high=True)
        p.x, p.y, p.ox, p.oy = [v & 0xFFFFFF for v in xs], [v & 0xFFFFFF for v in ys], \
            [v & 0xFFFFFF for v in oxs], [v & 0xFFFFFF for v in oys]
        return list(p.soa_bytes())

    def add(s, op, pins=(0,) * N3, pt=0, cur=0, turn=0, ca=0, cb=1, tv=(0, 0)):
        rows.append((s, list(pins), OPS3.index(op), pt, cur, turn & 0xFF, ca, cb,
                     (tv[0] & 0xFFFF if tv[0] >= 0 else tv[0], tv[1])))

    def rpins():
        return [rng.random() < 0.3 for _ in range(N3)]
    # integrate: y across the 256-row boundaries (both ways), above row 0, pins
    ycross = [0xFF80, 0x10010, 0x1FFE0, 0x0040, -0x0100, -0x10000, 0x2FF00]
    for k in range(120):
        i = k % N3
        xs = [rng.randrange(0x2000, 0xF00000) for _ in range(N3)]
        ys = [rng.randrange(-0x8000, 0x30000) for _ in range(N3)]
        ys[i] = ycross[k % len(ycross)] + rng.randrange(-0x40, 0x40) if k < 70 else ys[i]
        vy = rng.choice([rng.randrange(-0x900, 0x900), 0x7F00, -0x8000, 0x200, -0x200])
        oxs = [x - rng.randrange(-0x1400, 0x1400) for x in xs]
        oys = [y - rng.randrange(-0x400, 0x400) for y in ys]
        oys[i] = ys[i] - vy
        add(st(xs, ys, oxs, oys), 'int', pins=[int(rng.random() < 0.25) for _ in range(N3)], pt=i)
    # constraints: min-only (stretched: no move), fixed gain, pins on either end
    for k in range(240):
        cur = k % len(CONS3)
        a, b = CONS3[cur].a, CONS3[cur].b
        xs = [rng.randrange(0x10000, 0x200000) for _ in range(N3)]
        ys = [rng.randrange(-0x4000, 0x30000) for _ in range(N3)]
        L = CONS3[cur].length * 256 * rng.choice([rng.uniform(0.5, 1.6), rng.uniform(0.95, 1.05), 4.0, 0.1])
        dx = int(rng.uniform(-1, 1) * L)
        dy = int(rng.choice([-1, 1]) * max(0, L * L - dx * dx) ** 0.5)
        if k % 7 == 0:
            dx, dy = rng.choice([32767, -32768, 11585, -11585]), rng.randrange(-0x7F00, 0x7F00)
        xs[b] = xs[a] + dx
        ys[b] = ys[a] + dy
        pins = [0] * N3
        pins[a], pins[b] = [(0, 0), (1, 0), (0, 1), (1, 1)][k // len(CONS3) % 4]
        oxs = [x - rng.randrange(-0x300, 0x300) for x in xs]
        oys = [y - rng.randrange(-0x300, 0x300) for y in ys]
        add(st(xs, ys, oxs, oys), 'con', pins=pins, cur=cur)
    # ground: the base row, near, far above (w >= 64K rows), deep below
    for k in range(300):
        i = k % N3
        px = rng.randrange(8, len(HMAP) - 8)
        g = (HMAP[px] + BASE3) << 8
        off = rng.choice([rng.randrange(-0x0C00, 0x0C00), rng.randrange(-0x3000, 0x3000),
                          rng.randrange(-0x0700, 0x0100), -g + rng.randrange(-0x2000, 0x800),
                          rng.randrange(0x10000, 0x30000), rng.randrange(-0x30000, -0x10000)])
        xs = [rng.randrange(0x1000, 0xF0000) for _ in range(N3)]
        ys = [rng.randrange(0x1000, 0x2F000) for _ in range(N3)]
        xs[i] = px << 8 | rng.randrange(256)
        ys[i] = g + off
        oxs, oys = list(xs), list(ys)
        oxs[i] -= rng.randrange(-0x1000, 0x1000)
        oys[i] -= rng.randrange(-0x0800, 0x0800)
        add(st(xs, ys, oxs, oys), 'gnd', pt=i)
    # the rest
    other = ['pd', 'turn', 'shift', 'ceil', 'rest', 'iall', 'pass', 'delta', 'thra', 'thrp', 'push', 'pall']
    for k in range(360):
        op = other[k % len(other)]
        x0 = rng.randrange(0x10000, 0x400000)
        xs = [x0 + rng.randrange(-0x4000, 0x4000) for _ in range(N3)]
        y0 = rng.choice([rng.randrange(0x2000, 0x2C000), 0xFFF0, 0x10000, 0x1FFF0, 0x40])
        ys = [y0 + rng.randrange(-0x2000, 0x2000) for _ in range(N3)]
        if op == 'ceil':
            ys = [rng.choice([rng.randrange(0x0600, 0x0A00), rng.randrange(-0x400, 0x200),
                              rng.randrange(0x10000, 0x10A00)]) for _ in range(N3)]
        oxs = [x - rng.randrange(-0x1400, 0x1400) for x in xs]
        oys = [y - rng.randrange(-0x0A00, 0x0A00) for y in ys]
        turn = rng.choice([rng.randrange(-128, 128), 1, -1, 4, -4, 64, -64, 127, -128])
        tv = (rng.randrange(-0x800, 0x800), rng.randrange(-0x800, 0x800))
        if k % 5 == 0:
            tv = (rng.choice([0x7FFF, -0x8000, -1]), rng.choice([0x7F00, -0x8000, 1]))
        add(st(xs, ys, oxs, oys), op, pins=rpins(), pt=rng.randrange(N3), turn=turn,
            ca=rng.randrange(N3), cb=rng.randrange(N3), tv=tv)
    return rows


def check3(rng):
    rows = cases3(rng)
    pre, chunk = prelude3(), 60
    counts = {}
    for at in range(0, len(rows), chunk):
        part = rows[at:at + chunk]
        script = [(1, list(r[0]) + [int(v) for v in r[1]] + [r[2], r[3], r[4], r[5], r[6], r[7]]
                   + le(r[8][0], 2) + le(r[8][1], 2), 1) for r in part]
        got = harness.run(pre, EPILOGUE3, INPUTS3, SNAPS3, script, init='mul_init', snap_seg='LOWBSS')
        for k, (r, have) in enumerate(zip(part, got)):
            r = (r[0], [int(v) for v in r[1]], *r[2:])
            want = model3(r)
            if want != have:
                raise SystemExit(f'config 3, {OPS3[r[2]]} row {at + k}: point {r[3]} cur {r[4]} turn {r[5]} '
                                 f'pins {r[1]}\n  in   {bytes(r[0]).hex(" ")}\n  want {want.hex(" ")}\n'
                                 f'  have {have.hex(" ")}')
            counts[OPS3[r[2]]] = counts.get(OPS3[r[2]], 0) + 1
    print(f'lib/physics, 4 points, Y_HIGH + PIN + CON_FIXED_K + CON_MIN_ONLY + THRUST + ground base: '
          f'{len(rows)} calls == verlet ({", ".join(f"{k} {v}" for k, v in counts.items())})')


# --- configuration 4: a pinned rope, fixed-gain links, 300 ticks ---------------------
N4 = 8
LINK4, FK4 = 10, 6
CONS4 = [Constraint(i, i + 1, LINK4, fixed_k=FK4) for i in range(N4 - 1)]
G4, V4, PIN4_Y = 0x0018, 0x0800, 30


def rope4():
    p = Points(N4, pins=True)
    for i in range(N4):
        p.place(i, (100 + LINK4 * i) << 8, PIN4_Y << 8)
    p.pin[0] = 1
    return p


def prelude4():
    return f'''MUL_TABLES = $0800
.include "math.inc"
VL_NPOINTS = {N4}
VL_NCON = {len(CONS4)}
VL_GRAVITY = {G4}
VL_VMAX_X = {V4}
VL_VMAX_Y = {V4}
VL_PIN = 1
VL_CON_FIXED_K = {FK4}
.include "verlet.inc"
.segment "BSS"
t_ax:   .res 1
.segment "RODATA"
''' + '\n'.join(con_tables(tables(CONS4))[:4]) + \
        f'\nt_init: .byte {", ".join(map(str, rope4().soa_bytes()))}\n.code\n'


EPILOGUE4 = f'''
init:   JSR     mul_init
        LDX     #10 * {N4} - 1
:       LDA     t_init,X
        STA     vl_xf,X
        DEX
        BPL     :-
        LDA     #0                      ; (BSS is not cleared)
        LDX     #{N4} - 1
:       STA     vl_pin,X
        DEX
        BPL     :-
        LDA     #1
        STA     vl_pin
        RTS
tick:   JSR     vl_integrate_all
        JSR     vl_con_pass
        JSR     vl_con_pass
        LDA     t_ax                    ; the pin follows the input (at rest)
        STA     vl_xl
        STA     vl_oxl
        RTS
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
'''


def check4():
    # t_ax, and the last point's pin (vl_pin+7): pinned in the middle of the run
    ax = [100, 100, 110, 130, 150, 150, 120, 90, 60, 60, 90, 140, 170, 170, 140, 100]
    rows = [(20, [a, int(5 <= k < 9)], 1) for k, a in enumerate(ax)]
    got = harness.run(prelude4(), EPILOGUE4, ['t_ax', f'vl_pin+{N4 - 1}'], [('vl_xf', 10 * N4)], rows,
                      init='init')
    p = rope4()
    for k, (n, (a, pl), _) in enumerate(rows):
        p.pin[N4 - 1] = pl
        for _ in range(n):
            p.integrate_all(G4, V4, V4)
            for _ in range(2):
                for c in CONS4:
                    c.apply(p)
            p.x[0] = p.ox[0] = a << 8 | (p.x[0] & 0xFF)
        want = p.soa_bytes()
        if want != got[k]:
            raise SystemExit(f'pinned rope, snapshot {k}:\n  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
    sag = (p.y[N4 - 1] - p.y[0]) / 256
    print(f'lib/physics, a pinned 8-point rope (VL_PIN, VL_CON_FIXED_K = {FK4}): {sum(r[0] for r in rows)} ticks '
          f'== verlet in {len(rows)} snapshots, the end pinned for 80 of them (it swings: end {sag:+.1f} px below the pin)')


# --- configuration 5: a lander, VL_Y_HIGH world, thrust, ground base -----------------
N5, FK5, TH5, BASE5 = 3, 6, 4, 0x0180
# a 6-8-10 triangle: on the quarter-pixel grid at rest (no spring force, no
# floor bias: it falls without turning)
CONS5 = [Constraint(0, 1, 12, fixed_k=FK5), Constraint(0, 2, 10, fixed_k=FK5), Constraint(1, 2, 10, fixed_k=FK5)]
G5, V5, DAMP5 = 0x0006, 0x0600, 3


def hmap5():
    """Hills with a flat pad (columns 40..200) at row 200 + base."""
    h = []
    for x in range(300):
        h.append(200 if 40 <= x < 200 else 200 - int(30 * abs(((x * 7) % 60) - 30) / 30))
    return h


HMAP5 = hmap5()


def lander5():
    p = Points(N5, y_high=True)
    for i, (x, y) in enumerate([(114, 250), (126, 250), (120, 242)]):
        p.place(i, x << 8, y << 8)
    return p


def prelude5():
    hm = HeightMap(HMAP5, SLOPE_MAX, PROBE)
    return f'''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
VL_NPOINTS = {N5}
VL_NCON = {len(CONS5)}
VL_GRAVITY = {G5}
VL_VMAX_X = {V5}
VL_VMAX_Y = {V5}
VL_GROUND = 2
VL_HEIGHTS = t_hmap
VL_RADIUS = $0200
VL_PROBE = {PROBE}
VL_SLOPE_MAX = {SLOPE_MAX}
VL_FAR = $1000
VL_BOUNCE = 32
VL_GROUND_BASE = {BASE5}
VL_Y_HIGH = 1
VL_CON_FIXED_K = {FK5}
VL_THRUST = {TH5}
VL_PAIR_DAMP = {DAMP5}
.include "verlet.inc"
.segment "BSS"
t_thr:  .res 1
t_rot:  .res 1
.segment "RODATA"
''' + '\n'.join(con_tables(tables(CONS5))[:4]) + '\n' + \
        emit.table_line('vl_norm_x', emit.sb(hm.nx)) + '\n' + emit.table_line('vl_norm_y', emit.sb(hm.ny)) + \
        '\nt_hmap: .byte ' + ', '.join(map(str, HMAP5)) + \
        f'\nt_init: .byte {", ".join(map(str, lander5().soa_bytes()))}\n.code\n'


EPILOGUE5 = f'''
init:   JSR     mul_init
        LDX     #12 * {N5} - 1
:       LDA     t_init,X
        STA     vl_xf,X
        DEX
        BPL     :-
        RTS
tick:   JSR     vl_integrate_all
        JSR     vl_pair_damp            ; the spin fades
        LDA     t_rot                   ; turn the legs
        BEQ     :+
        STA     vl_turn
        JSR     vl_turn_pair
:       LDA     t_thr                   ; thrust along the body (up: < 0)
        BEQ     :+
        STA     vl_turn
        JSR     vl_thrust_perp
        JSR     vl_push_all
:       JSR     vl_con_pass
        JSR     vl_con_pass
        LDX     #0
        JSR     vl_ground
        LDX     #1
        JSR     vl_ground
        JMP     vl_con_pass
.include "verlet_hmap.asm"
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
'''


def tick5(p, hm, thr, rot):
    p.integrate_all(G5, V5, V5)
    p.pair_damp(0, 1, DAMP5)
    if rot:
        p.turn_pair(0, 1, rot)
    if thr:
        p.push_all(p.thrust(0, 1, thr, TH5, perp=True))
    for _ in range(2):
        for c in CONS5:
            c.apply(p)
    gnd = [int(hm.contact(p, i) is not None) for i in range(2)]
    for c in CONS5:
        c.apply(p)
    return gnd


def script5(hm):
    """An autopilot on the model: a turn, then the legs kept level and the
    thrust on whenever they fall faster than 0.4 px a tick, down to the
    pad; the engine off once a leg touches. -> [(thr, rot)] a tick."""
    p, out, landed = lander5(), [], False
    for k in range(850):
        vy = p.y[0] - p.oy[0]
        tilt = p.y[1] - p.y[0]
        thr = -14 if vy > 0x66 and k > 60 and not landed else 0
        rot = 0 if landed else 3 if 70 <= k < 73 else -2 if tilt > 0x80 else 2 if tilt < -0x80 else 0
        landed |= any(tick5(p, hm, thr, rot))
        out.append((thr, rot))
    return out


def check5():
    hm = HeightMap(HMAP5, SLOPE_MAX, PROBE, 0x0200, 0x1000, 32, base=BASE5)
    seg = harness.segments(script5(hm))
    rows = [(n, [thr & 0xFF, rot & 0xFF], k % 5 == 4 or k == len(seg) - 1) for k, (n, (thr, rot)) in enumerate(seg)]
    got = harness.run(prelude5(), EPILOGUE5, ['t_thr', 't_rot'], [('vl_xf', 12 * N5), ('vl_gnd', 2)], rows,
                      init='init', snap_seg='LOWBSS')
    p = lander5()
    lowest, touched, snap = 0, 0, 0
    for n, (thr, rot), keep in rows:
        for _ in range(n):
            gnd = tick5(p, hm, s8(thr), s8(rot))
            lowest = max(lowest, p.y[0] >> 8)
            touched += any(gnd)
        if not keep:
            continue
        want = p.soa_bytes() + bytes(gnd)
        if want != got[snap]:
            raise SystemExit(f'lander, snapshot {snap}:\n  want {want.hex(" ")}\n  have {got[snap].hex(" ")}')
        snap += 1
    assert lowest > 256 and touched > 100 and abs(p.y[0] - p.oy[0]) < 0x20, (lowest, touched)
    print(f'lib/physics, a 3-point lander (VL_Y_HIGH, ground base {BASE5 >> 0}, VL_THRUST, fixed-gain links): '
          f'{sum(r[0] for r in rows)} ticks == verlet in {snap} snapshots (down to row {lowest}, '
          f'{touched} ticks on the ground)')


# --- switches -------------------------------------------------------------------------
def listing(work, source):
    src = Path(work) / 'o.s'
    src.write_text(source)
    inc = [a for d in harness.INCLUDES for a in ('-I', str(d))]
    r = subprocess.run(['ca65', *inc, '-l', str(Path(work) / 'o.lst'), '-o', str(Path(work) / 'o.o'), str(src)],
                       capture_output=True, text=True)
    if r.returncode:
        return 'error: ' + r.stderr
    return '\n'.join(line[:24] for line in (Path(work) / 'o.lst').read_text().splitlines()[4:]
                     if line[11:24].strip())


def check_switches():
    base = '''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
VL_NPOINTS = 3
VL_NCON = 3
VL_GRAVITY = $30
VL_VMAX_X = $1000
VL_VMAX_Y = $0800
{defs}
.include "verlet.inc"
.code
{calls}
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
.rodata
vl_con_a: .byte 0, 0, 1
vl_con_b: .byte 1, 2, 2
vl_con_l2l: .res 6
vl_con_l2h: .res 6
vl_con_k8: .res 6
'''
    cases = [('VL_INTEGRATE_LEFTWALL = $1000', 'JSR vl_integrate', False),
             ('VL_CON_VARIANTS = 2', 'JSR vl_con_pass', False),
             ('VL_CON_HEAVY_POINT = 2\nVL_CON_HEAVY_SHIFT = 3', 'JSR vl_con_pass', False),
             ('VL_CON_MINLEN_POINT = 2\nVL_CON_MINLEN = 100', 'JSR vl_con_pass', False),
             ('VL_PAIR_DAMP = 4', 'JSR vl_pair_damp', True),
             ('VL_CEILING_CLAMP = $0800', 'JSR vl_ceiling', True),
             ('VL_SHIFT_POINT = 2', 'JSR vl_shift_point', True),
             ('VL_PIN = 1', 'JSR vl_integrate_all\nJSR vl_con_pass', False),
             ('VL_CON_FIXED_K = 5', 'JSR vl_con_pass', False),
             ('VL_CON_MIN_ONLY = 1', 'JSR vl_con_pass', False),
             ('VL_Y_HIGH = 1', 'JSR vl_integrate\nJSR vl_rest', False),
             ('VL_THRUST = 4', 'JSR vl_thrust_axis', True),
             ('VL_THRUST = 4', 'JSR vl_thrust_perp\nJSR vl_push_all', True)]
    with tempfile.TemporaryDirectory(prefix='verlet-sw-') as tmp:
        for defs, call, needed in cases:
            off = listing(tmp, base.format(defs='', calls=call))
            on = listing(tmp, base.format(defs=defs, calls=call))
            assert not on.startswith('error'), (defs, on)
            if needed:
                assert off.startswith('error'), f'{call} without {defs.split()[0]} assembles'
            else:
                assert not off.startswith('error') and off != on, f'{defs.split()[0]} changes nothing'
        seg = listing(tmp, base.format(defs='VL_SHIFT_POINT = 2\n.define VL_ROT_SEG "XSEG"', calls='JSR vl_shift_point'))
        assert not seg.startswith('error'), seg
        # the fixed gain leaves the k8 table out: the program need not define it
        fk = listing(tmp, base.format(defs='VL_CON_FIXED_K = 5', calls='JSR vl_con_pass').replace(
            'vl_con_k8: .res 6\n', ''))
        assert not fk.startswith('error'), fk
    print('switches: left out, the plain code (vl_pair_damp, vl_ceiling, vl_shift_point, vl_thrust_*, '
          'vl_push_all stop the assembly without theirs); defined, LEFTWALL, CON_VARIANTS, CON_HEAVY, '
          'CON_MINLEN, PIN, CON_FIXED_K (no k8 table), CON_MIN_ONLY, Y_HIGH change the code.')


def main():
    check1(random.Random(7))
    check2()
    check3(random.Random(11))
    check4()
    check5()
    check_switches()


if __name__ == '__main__':
    main()
