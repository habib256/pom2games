#!/usr/bin/env python3
"""lib/physics circle contacts (verlet_circ.asm) in a2run against
dev/tools/verlet/contact.py, bit for bit.

Configuration A (4 points, y 8.8, Q = 5, restitution 96/256 above a
minimum speed, heavy points, pins, friction, 3 boxes): one call per row
from a random or edge state -- vl_contact_pair (head-on, glancing, a
resting stack, coincident centres, the fast path far apart and across the
256-px and 256-row wraps, every pin and heavy case, radii up to R = 127),
vl_contact_all (clusters of 4), vl_contact_box (faces, corners, inside,
within a unit, far, beyond x 255). Configuration B (VL_Y_HIGH, Q = 6, no
restitution, no friction, no pins: the plain code) the same way.
Configuration C: a stack of 3 balls on a box and a ball rolling into it,
300 ticks of vl_integrate_all + 2 x (vl_contact_all + vl_contact_box).
Then the cycles of each case (a2run call:), and the switches.

    python3 dev/tests/test_verlet_contact.py [--cycles]
"""
from pathlib import Path
import random
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
from verlet import Points, contact, harness  # noqa: E402
import a2test  # noqa: E402

OPS = ['pair', 'all', 'box', 'sleep']


class Conf:
    def __init__(self, name, n, q, bounce, vmin, heavy, friction, pins, y_high, boxes, sleep=0):
        self.name, self.n, self.q, self.bounce, self.vmin = name, n, q, bounce, vmin
        self.sleep = sleep
        self.heavy, self.friction, self.pins, self.y_high, self.boxes = heavy, friction, pins, y_high, boxes
        self.k = 12 if y_high else 10

    def prelude(self):
        defs = [f'VL_NPOINTS = {self.n}', f'VL_CIRC = {self.n}', f'VL_CIRC_Q = {self.q}',
                'VL_GRAVITY = $0010', 'VL_VMAX_X = $0800', 'VL_VMAX_Y = $0800', f'VL_NBOX = {len(self.boxes)}']
        if self.bounce:
            defs += [f'VL_CIRC_BOUNCE = {self.bounce}', f'VL_CIRC_VMIN = {self.vmin}']
        if self.heavy:
            defs.append(f'VL_CIRC_HEAVY = {self.heavy}')
        if self.friction:
            defs.append(f'VL_CIRC_FRICTION = {self.friction}')
        if self.pins:
            defs.append('VL_PIN = 1')
        if self.sleep:
            defs.append(f'VL_CIRC_SLEEP = {self.sleep}')
        if self.y_high:
            defs.append('VL_Y_HIGH = 1')
        bx = self.boxes
        return ('MUL_TABLES = $0800\nMUL_ACC = 1\n.include "math.inc"\n' + '\n'.join(defs) +
                '\n.include "verlet.inc"\n.segment "ZEROPAGE"\nt_op: .res 1\nt_pt: .res 1\n'
                '.segment "BSS"\nt_c: .res 1\n.segment "RODATA"\n' +
                ''.join(f'{lab}: .byte {", ".join(str(b[k]) for b in bx)}\n'
                        for k, lab in enumerate(('vl_box_x0', 'vl_box_y0', 'vl_box_x1', 'vl_box_y1'))) +
                '.code\n')

    EPILOGUE = '''
init:   JSR     mul_init
        JMP     sqrt_init
tick:   LDA     #0
        STA     vl_chits
        LDA     t_op
        BEQ     @pair
        CMP     #1
        BEQ     @all
        LDX     t_pt
        CMP     #2
        BEQ     @box
.ifdef VL_CIRC_SLEEP
        JSR     vl_circ_sleep
.endif
        JMP     @c
@box:   JSR     vl_contact_box
        JMP     @c
@pair:  LDX     vl_cb
        LDY     vl_ca
        LDA     vl_rad,X
        CLC
        ADC     vl_rad,Y
        JSR     vl_contact_pair
        JMP     @c
@all:   JSR     vl_contact_all
        CLC
@c:     LDA     #0
        ROL     A
        STA     t_c
        RTS
.include "verlet_circ.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "sqrt.asm"
.include "mul.asm"
'''

    def inputs(self):
        arrs = ['xf', 'xl', 'xh', 'yf', 'yh'] + (['yu'] if self.y_high else []) + \
            ['oxf', 'oxl', 'oxh', 'oyf', 'oyh'] + (['oyu'] if self.y_high else [])
        names = [f'vl_{a}+{i}' for a in arrs for i in range(self.n)]
        names += [f'vl_rad+{i}' for i in range(self.n)]
        if self.pins:
            names += [f'vl_pin+{i}' for i in range(self.n)]
        if self.heavy:
            names += [f'vl_cheavy+{i}' for i in range(self.n)]
        if self.sleep:
            names += [f'vl_still+{i}' for i in range(self.n)]
        return names + ['t_op', 't_pt', 'vl_ca', 'vl_cb']

    def snaps(self):
        return [('vl_xf', self.k * self.n)] + ([('vl_pin', self.n)] if self.pins else []) + \
            ([('vl_still', self.n)] if self.sleep else []) + [('vl_chits', 1), ('t_c', 1)]

    # a row: (points, rad, pin, hv, op, pt, ca, cb, still)
    def row_bytes(self, r):
        p, rad, pin, hv, op, pt, ca, cb, still = r
        out = list(p.soa_bytes()) + list(rad)
        if self.pins:
            out += pin
        if self.heavy:
            out += hv
        if self.sleep:
            out += still
        return out + [op, pt, ca, cb]

    def model(self, r):
        p0, rad, pin, hv, op, pt, ca, cb, still = r
        p = Points.from_soa(p0.soa_bytes(), self.n, self.y_high)
        still = list(still)
        if self.pins:
            p.pin = list(pin)
        kw = dict(Q=self.q, bounce=self.bounce, vmin=self.vmin)
        hits, c = 0, 0
        if OPS[op] == 'pair':
            c = int(contact.pair(p, ca, cb, rad[ca] + rad[cb], heavy=self.heavy, hv=hv, sleep=self.sleep, **kw))
        elif OPS[op] == 'all':
            hits = contact.contact_all(p, rad, heavy=self.heavy, hv=hv, sleep=self.sleep, **kw)
        elif OPS[op] == 'box':
            hits = contact.boxes(p, pt, rad[pt], self.boxes, friction=self.friction, **kw)
            c = int(hits > 0)
        else:
            c = int(contact.sleep_check(p, pt, still, self.sleep))
        return p.soa_bytes() + (bytes(p.pin) if self.pins else b'') + (bytes(still) if self.sleep else b'') + \
            bytes([hits, c])


CONF_A = Conf('A', 4, 5, 96, 0x30, 2, 3, True, False, [(40, 100, 80, 110), (100, 60, 110, 140), (150, 150, 200, 152)],
              sleep=0x40)
CONF_B = Conf('B', 4, 6, 0, 0, 0, 0, False, True, [(30, 120, 90, 130), (120, 40, 128, 100)])


def pts(conf, xs, ys, vxs, vys):
    p = Points(conf.n, y_high=conf.y_high)
    for i in range(conf.n):
        p.x[i] = xs[i] & 0xFFFFFF
        p.ox[i] = (xs[i] - vxs[i]) & 0xFFFFFF
        if conf.y_high:
            p.y[i] = ys[i]
            p.oy[i] = ys[i] - vys[i]
        else:
            p.y[i] = ys[i] & 0xFFFF
            p.oy[i] = (ys[i] - vys[i]) & 0xFFFF
    return p


def cases(conf, rng):
    n, Q, U = conf.n, conf.q, 1 << conf.q            # U: a radius unit in 8.8
    rows = []

    def flags():
        pin = [0] * n
        hv = [0] * n
        if conf.pins and rng.random() < 0.4:
            pin[rng.randrange(n)] = rng.choice([1, 0x80, 0x80]) if conf.sleep else 1
            if rng.random() < 0.2:
                pin = [rng.choice([1, 0x80]) if conf.sleep else 1 for _ in range(n)]
        if conf.heavy and rng.random() < 0.4:
            hv = [int(rng.random() < 0.5) for _ in range(n)]
        return pin, hv

    def base():
        xs = [rng.randrange(0x2000, 0xF000) for _ in range(n)]
        ys = [rng.randrange(0x2000, 0xE000) for _ in range(n)]
        vxs = [rng.randrange(-0x180, 0x180) for _ in range(n)]
        vys = [rng.randrange(-0x180, 0x180) for _ in range(n)]
        if conf.y_high:
            ys = [y + rng.choice([0, 0, 0x10000, -0x8000]) for y in ys]
        return xs, ys, vxs, vys

    def radii():
        big = rng.random() < 0.15
        return [rng.randrange(40, 64) if big else rng.randrange(8, 48) for _ in range(n)]

    for k in range(700):
        xs, ys, vxs, vys = base()
        rad = radii()
        a, b = rng.sample(range(n), 2)
        R = rad[a] + rad[b]
        kind = k % 7
        if kind == 0:                                   # head-on along x or y
            d = int(R * U * rng.uniform(0.2, 1.05))
            if rng.random() < 0.5:
                xs[b], ys[b] = xs[a] + d * rng.choice([1, -1]), ys[a] + rng.randrange(-U, U)
                v = rng.randrange(0, 0x300)
                vxs[a], vxs[b] = (v, -v) if xs[b] > xs[a] else (-v, v)
            else:
                xs[b], ys[b] = xs[a] + rng.randrange(-U, U), ys[a] + d * rng.choice([1, -1])
                v = rng.randrange(0, 0x300)
                vys[a], vys[b] = (v, -v) if ys[b] > ys[a] else (-v, v)
        elif kind == 1:                                 # glancing, anywhere in 1.1 R
            ang = rng.uniform(0, 6.2832)
            d = R * U * rng.uniform(0, 1.1)
            import math
            xs[b], ys[b] = xs[a] + int(d * math.cos(ang)), ys[a] + int(d * math.sin(ang))
        elif kind == 2:                                 # resting stack: b on a
            xs[b] = xs[a] + rng.randrange(-U, U)
            ys[b] = ys[a] - R * U + rng.randrange(0, 3 * U)
            vxs[a] = vys[a] = vxs[b] = 0
            vys[b] = rng.randrange(0, 0x40)
        elif kind == 3:                                 # coincident, within a unit
            xs[b], ys[b] = xs[a] + rng.randrange(-U + 1, U), ys[a] + rng.randrange(-U + 1, U)
        elif kind == 4:                                 # far: the fast paths, wraps
            w = rng.randrange(5)
            if w == 0:
                xs[b] = xs[a] + rng.choice([1, -1]) * rng.randrange(R * U, 0x9000)
            elif w == 1:                                # 256 px apart (+- a little)
                xs[b] = xs[a] + rng.choice([1, -1]) * (0x10000 + rng.randrange(-R * U, R * U))
                ys[b] = ys[a] + rng.randrange(-R * U, R * U) // 2
            elif w == 2:                                # 256 rows apart
                ys[b] = (ys[a] + 0x10000 + rng.randrange(-R * U, R * U)) if not conf.y_high else \
                    ys[a] + rng.choice([0x10000, -0x10000]) + rng.randrange(-R * U, R * U)
                xs[b] = xs[a] + rng.randrange(-R * U, R * U) // 2
            elif w == 3:                                # 128 px: the 16-bit edge
                xs[b] = xs[a] + rng.choice([0x8000, -0x8000, 0x7FFF, -0x7FFF, 0x8100])
                ys[b] = ys[a]
            else:                                       # just out on one axis
                xs[b] = xs[a] + rng.choice([1, -1]) * (R * U + rng.randrange(0, 2 * U))
                ys[b] = ys[a] + rng.randrange(-U, U)
        elif kind == 5:                                 # fast and deep: big speeds
            d = int(R * U * rng.uniform(0, 0.6))
            ang = rng.uniform(0, 6.2832)
            import math
            xs[b], ys[b] = xs[a] + int(d * math.cos(ang)), ys[a] + int(d * math.sin(ang))
            vxs = [rng.randrange(-0x800, 0x800) for _ in range(n)]
            vys = [rng.randrange(-0x800, 0x800) for _ in range(n)]
        else:                                           # radii at the limit
            rad[a], rad[b] = rng.choice([(63, 64), (127, 0), (0, 127), (64, 63), (1, 0), (60, 60)])
            R = rad[a] + rad[b]
            d = int(R * U * rng.uniform(0.5, 1.02))
            xs[b], ys[b] = xs[a] + d * rng.choice([1, -1]), ys[a] + rng.randrange(-2 * U, 2 * U)
        if not conf.y_high:
            ys = [max(0, min(0xFFFF, y)) if i != b or kind != 4 else y for i, y in enumerate(ys)]
        xs = [max(0, x) if i != b or kind != 4 else x for i, x in enumerate(xs)]
        pin, hv = flags()
        rows.append((pts(conf, xs, ys, vxs, vys), rad, pin, hv, 0, 0, a, b, [0] * n))
    for k in range(150):                                # all: a cluster of 4
        rad = radii()
        cx, cy = rng.randrange(0x3000, 0xC000), rng.randrange(0x3000, 0xC000)
        spread = rng.choice([0x300, 0x800, 0x1400])
        xs = [cx + rng.randrange(-spread, spread) for _ in range(n)]
        ys = [cy + rng.randrange(-spread, spread) for _ in range(n)]
        vxs = [rng.randrange(-0x200, 0x200) for _ in range(n)]
        vys = [rng.randrange(-0x200, 0x200) for _ in range(n)]
        if k % 5 == 0:
            rad[rng.randrange(n)] = 0
        pin, hv = flags()
        rows.append((pts(conf, xs, ys, vxs, vys), rad, pin, hv, 1, 0, 0, 0, [0] * n))
    for k in range(450):                                # boxes
        xs, ys, vxs, vys = base()
        rad = radii()
        i = k % n
        x0, y0, x1, y1 = conf.boxes[k % len(conf.boxes)]
        r = rad[i]
        kind = k % 6
        if kind == 0:                                   # a face, from outside
            f = rng.randrange(4)
            o = rng.randrange(-r * U, r * U + 2 * U)
            if f == 0:
                xs[i], ys[i] = rng.randrange(x0 << 8, (x1 << 8) + 1), (y0 << 8) - o
            elif f == 1:
                xs[i], ys[i] = (x0 << 8) - o, rng.randrange(y0 << 8, (y1 << 8) + 1)
            elif f == 2:
                xs[i], ys[i] = (x1 << 8) + o, rng.randrange(y0 << 8, (y1 << 8) + 1)
            else:
                xs[i], ys[i] = rng.randrange(x0 << 8, (x1 << 8) + 1), (y1 << 8) + o
        elif kind == 1:                                 # a corner
            cxv, cyv = rng.choice([x0, x1]) << 8, rng.choice([y0, y1]) << 8
            xs[i] = cxv + rng.randrange(-r * U - U, r * U + U)
            ys[i] = cyv + rng.randrange(-r * U - U, r * U + U)
        elif kind == 2:                                 # inside
            xs[i] = rng.randrange(x0 << 8, (x1 << 8) + 1)
            ys[i] = rng.randrange(y0 << 8, (y1 << 8) + 1)
        elif kind == 3:                                 # within a unit outside
            f = rng.randrange(4)
            e = rng.randrange(1, U)
            if f == 0:
                xs[i], ys[i] = rng.randrange(x0 << 8, (x1 << 8) + 1), (y0 << 8) - e
            elif f == 1:
                xs[i], ys[i] = (x0 << 8) - e, rng.randrange(y0 << 8, (y1 << 8) + 1)
            elif f == 2:
                xs[i], ys[i] = (x1 << 8) + e, rng.randrange(y0 << 8, (y1 << 8) + 1)
            else:
                xs[i], ys[i] = rng.randrange(x0 << 8, (x1 << 8) + 1), (y1 << 8) + e
        elif kind == 4:                                 # far, or beyond x 255
            xs[i] = rng.choice([rng.randrange(0x0100, 0xFF00), 0x10000 + rng.randrange(0x9000),
                                (x0 << 8) - 0x2000])
            ys[i] = rng.randrange(0x0100, 0xFF00)
        else:                                           # resting on top, slow
            xs[i] = rng.randrange(x0 << 8, (x1 << 8) + 1)
            ys[i] = (y0 << 8) - r * U + rng.randrange(-U, 2 * U)
            vxs[i] = rng.randrange(-0x60, 0x60)
            vys[i] = rng.randrange(-0x10, 0x60)
        if kind != 4 or rng.random() < 0.5:
            vxs[i], vys[i] = vxs[i] * rng.choice([1, 3]), vys[i] * rng.choice([1, 3])
        if rng.random() < 0.1:
            rad[i] = 0
        pin, hv = flags()
        rows.append((pts(conf, xs, ys, vxs, vys), rad, pin, hv, 2, i, 0, 0, [0] * n))
    if conf.sleep:                                      # vl_circ_sleep
        for k in range(160):
            xs, ys, vxs, vys = base()
            i = k % n
            sp = rng.choice([conf.sleep, conf.sleep + 1, 0, 1, 0x7F, 0x800])
            vxs[i] = rng.choice([1, -1]) * (sp if k % 3 == 0 else rng.randrange(0, sp + 1))
            vys[i] = rng.choice([1, -1]) * (sp if k % 3 == 1 else rng.randrange(0, sp + 1))
            if k % 11 == 0:
                vxs[i] = -0x8000
            pin, hv = flags()
            if k % 4:
                pin[i] = 0
            still = [rng.choice([0, 3, 14, 15, 16, 200]) for _ in range(n)]
            rows.append((pts(conf, xs, ys, vxs, vys), radii(), pin, hv, 3, i, 0, 0, still))
    return rows


def check(conf, rng):
    rows = cases(conf, rng)
    inputs, snaps = conf.inputs(), conf.snaps()
    counts, hit = {}, {}
    chunk = 60
    for at in range(0, len(rows), chunk):
        part = rows[at:at + chunk]
        script = [(1, conf.row_bytes(r), 1) for r in part]
        got = harness.run(conf.prelude(), Conf.EPILOGUE, inputs, snaps, script, init='init', snap_seg='LOWBSS')
        for k, (r, have) in enumerate(zip(part, got)):
            want = conf.model(r)
            name = OPS[r[4]]
            if want != have:
                raise SystemExit(f'config {conf.name}, {name} row {at + k}: rad {r[1]} pin {r[2]} hv {r[3]} '
                                 f'pt {r[5]} ca {r[6]} cb {r[7]}\n  in   {r[0].soa_bytes().hex(" ")}\n'
                                 f'  want {want.hex(" ")}\n  have {have.hex(" ")}')
            counts[name] = counts.get(name, 0) + 1
            hit[name] = hit.get(name, 0) + (want[-1] or want[-2] > 0)
            if name == 'pair' and conf.sleep and want[conf.k * conf.n:conf.k * conf.n + conf.n] != bytes(r[2]):
                hit['wake'] = hit.get('wake', 0) + 1
    print(f'lib/physics contacts, config {conf.name}: {len(rows)} calls == verlet.contact ('
          + ', '.join(f'{k} {v} ({hit[k]} in contact)' for k, v in counts.items())
          + (f'; {hit.get("wake", 0)} wakes' if conf.sleep else '') + ')')
    return hit


# --- configuration C: a stack on a box, a ball rolling into it -----------------------
NC = 4
BOX_C = [(40, 150, 200, 160), (36, 100, 40, 160), (200, 100, 204, 160)]
RAD_C = [contact.rad_q(5)] * 3 + [contact.rad_q(6)]
G_C, V_C, E_C, VMIN_C, F_C = 0x0010, 0x0600, 64, 0x0040, 4


def stack_c():
    p = Points(NC)
    r = 5 << 8
    for i in range(3):
        p.place(i, 120 << 8, (150 << 8) - r - i * 2 * r - 0x80 * i)
    p.place(3, 60 << 8, 120 << 8)
    p.ox[3] -= 0x0180                                    # rolls right
    return p


def tick_c(p):
    p.integrate_all(G_C, V_C, V_C)
    hits = 0
    for _ in range(2):
        hits += contact.contact_all(p, RAD_C, bounce=E_C, vmin=VMIN_C)
        for i in range(NC):
            hits += contact.boxes(p, i, RAD_C[i], BOX_C, bounce=E_C, vmin=VMIN_C, friction=F_C)
    return hits


def check_c():
    pre = (f'MUL_TABLES = $0800\nMUL_ACC = 1\n.include "math.inc"\nVL_NPOINTS = {NC}\nVL_CIRC = {NC}\n'
           f'VL_GRAVITY = {G_C}\nVL_VMAX_X = {V_C}\nVL_VMAX_Y = {V_C}\nVL_NBOX = {len(BOX_C)}\n'
           f'VL_CIRC_BOUNCE = {E_C}\nVL_CIRC_VMIN = {VMIN_C}\nVL_CIRC_FRICTION = {F_C}\n'
           '.include "verlet.inc"\n.segment "BSS"\nt_x: .res 1\n.segment "RODATA"\n' +
           ''.join(f'{lab}: .byte {", ".join(str(b[k]) for b in BOX_C)}\n'
                   for k, lab in enumerate(('vl_box_x0', 'vl_box_y0', 'vl_box_x1', 'vl_box_y1'))) +
           f't_init: .byte {", ".join(map(str, stack_c().soa_bytes()))}\n'
           f't_rad: .byte {", ".join(map(str, RAD_C))}\n.code\n')
    epi = f'''
init:   JSR     mul_init
        JSR     sqrt_init
        LDX     #10 * {NC} - 1
:       LDA     t_init,X
        STA     vl_xf,X
        DEX
        BPL     :-
        LDX     #{NC} - 1
:       LDA     t_rad,X
        STA     vl_rad,X
        DEX
        BPL     :-
        LDA     #0
        STA     vl_chits
        RTS
tick:   JSR     vl_integrate_all
        JSR     pass
pass:   JSR     vl_contact_all
        LDX     #{NC} - 1
:       JSR     vl_contact_box
        DEX
        BPL     :-
        RTS
.include "verlet_circ.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "sqrt.asm"
.include "mul.asm"
'''
    rows = [(10, [0], 1)] * 30
    got = harness.run(pre, epi, ['t_x'], [('vl_xf', 10 * NC), ('vl_chits', 1)], rows, init='init')
    p, hits = stack_c(), 0
    for k, (n, _, _) in enumerate(rows):
        for _ in range(n):
            hits += tick_c(p)
        want = p.soa_bytes() + bytes([hits & 0xFF])
        if want != got[k]:
            raise SystemExit(f'stack, snapshot {k}:\n  want {want.hex(" ")}\n  have {got[k].hex(" ")}')
    tops = [round((p.y[i] >> 8) + (p.y[i] & 255) / 256, 1) for i in range(3)]
    print(f'lib/physics contacts, config C (a stack of 3 on a box, a ball rolling into it): 300 ticks '
          f'== verlet.contact in 30 snapshots (ball rows {tops}, rolling ball at x {p.x[3] >> 8})')


# --- cycles -----------------------------------------------------------------------------
def cycles():
    """a2run call: of each routine on config A states (the JSR included)."""
    conf = CONF_A
    U = 1 << conf.q
    text = harness.source(conf.prelude(), Conf.EPILOGUE, conf.inputs(), [('t_c', 1)], [(1, [0] * len(conf.inputs()), 0)],
                          init='init')
    r40 = [40, 40, 40, 40]

    def st(xs, ys, vxs=(0,) * 4, vys=(0,) * 4):
        return pts(conf, list(xs), list(ys), list(vxs), list(vys)).soa_bytes()
    R = 80
    probes = [
        ('pair: far apart (whole-pixel reject)', 'pair', st([0x4000, 0x8000, 0x2000, 0xA000], [0x4000] * 4), 0, 1),
        ('pair: close, not touching (q2 >= R^2)', 'pair',
         st([0x4000, 0x4000 + 0x780, 0x2000, 0xA000], [0x4000, 0x4000 + 0x780, 0x2000, 0xA000]), 0, 1),
        ('pair: head-on, closing (push + impulse)', 'pair',
         st([0x4000, 0x4000 + R * U - 0x100, 0x2000, 0xA000], [0x4000, 0x4010, 0x2000, 0xA000],
            [0x100, -0x100, 0, 0]), 0, 1),
        ('pair: glancing, closing', 'pair',
         st([0x4000, 0x4000 + 0x600, 0x2000, 0xA000], [0x4000, 0x4000 + 0x700, 0x2000, 0xA000],
            [0x80, -0x40, 0, 0], [0x40, -0x80, 0, 0]), 0, 1),
        ('pair: resting stack (vertical, slow)', 'pair',
         st([0x4000, 0x4000, 0x2000, 0xA000], [0x5000, 0x5000 - R * U + 0x20, 0x2000, 0xA000], vys=[0, 0x10, 0, 0]), 0, 1),
        ('pair: separating (push, no impulse)', 'pair',
         st([0x4000, 0x4000 + 0x800, 0x2000, 0xA000], [0x4000, 0x4100, 0x2000, 0xA000],
            [-0x80, 0x80, 0, 0]), 0, 1),
        ('all: 4 apart (6 pairs, none)', 'all',
         st([0x2000, 0x5000, 0x8000, 0xB000], [0x2000, 0x5000, 0x8000, 0xB000]), 0, 0),
        ('all: 4 in a row touching (3 contacts)', 'all',
         st([0x4000, 0x4000 + 0x480, 0x4000 + 0x900, 0x4000 + 0xD80], [0x4000] * 4, [0x40, 0, 0, -0x40]), 0, 0),
        ('box: far from the 3 boxes', 'box', st([0x1000, 0, 0, 0], [0x1000, 0, 0, 0]), 0, 0),
        ('box: on a top face, falling', 'box',
         st([60 << 8, 0, 0, 0], [(100 << 8) - 40 * U + 0x40, 0, 0, 0], vys=[0x80, 0, 0, 0]), 0, 0),
        ('box: a corner', 'box',
         st([(80 << 8) + 0x180, 0, 0, 0], [(100 << 8) - 0x180, 0, 0, 0], [-0x40, 0, 0, 0], [0x80, 0, 0, 0]), 0, 0),
        ('box: centre inside', 'box', st([(105 << 8), 0, 0, 0], [(90 << 8), 0, 0, 0], vys=[0x40, 0, 0, 0]), 0, 0),
    ]
    out = []
    with tempfile.TemporaryDirectory(prefix='contact-cyc-') as tmp:
        lab, binary = harness.build(tmp, text)
        steps = a2test.bin_steps(binary, 0x6000, lab['init'])[:1] + [f'call:{lab["init"]:04X}:20']
        for name, op, state, a, b in probes:
            steps += [lab.poke('vl_xf', v, k) for k, v in enumerate(state)]
            steps += [lab.poke('vl_rad', v, k) for k, v in enumerate(r40)]
            steps += [lab.poke('vl_pin', 0, k) for k in range(4)] + [lab.poke('vl_cheavy', 0, k) for k in range(4)]
            steps += [lab.poke('vl_ca', a), lab.poke('vl_cb', b), lab.poke('vl_chits', 0)]
            if op == 'pair':
                steps += ['regs:50:00:00', f'call:{lab["vl_contact_pair"]:04X}:5']
            elif op == 'all':
                steps += [f'call:{lab["vl_contact_all"]:04X}:5']
            else:
                steps += ['regs:00:00:00', f'call:{lab["vl_contact_box"]:04X}:5']
            steps += [lab.peek('vl_chits')]
        r = a2test.run(None, steps)
    el = [int(v) for v in re.findall(r'elapsed=(\d+)', r.out)][1:]
    print('contact cycles (a2run call:, the JSR included):')
    for (name, *_), e in zip(probes, el):
        out.append((name, e))
        print(f'  {name}: {e:,}')
    return out


def check_switches():
    from test_verlet import listing  # noqa: E402
    base = '''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
VL_NPOINTS = 4
VL_CIRC = 4
VL_GRAVITY = $30
VL_VMAX_X = $1000
VL_VMAX_Y = $0800
VL_NBOX = 1
{defs}
.include "verlet.inc"
.code
        JSR vl_contact_all
        JSR vl_contact_box
.ifdef VL_CIRC_SLEEP
        JSR vl_circ_sleep
.endif
.include "verlet_circ.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "sqrt.asm"
.include "mul.asm"
.rodata
vl_box_x0: .byte 0
vl_box_y0: .byte 0
vl_box_x1: .byte 0
vl_box_y1: .byte 0
'''
    with tempfile.TemporaryDirectory(prefix='contact-sw-') as tmp:
        plain = listing(tmp, base.format(defs=''))
        assert not plain.startswith('error'), plain
        for defs in ('VL_CIRC_BOUNCE = 100', 'VL_CIRC_HEAVY = 2', 'VL_CIRC_FRICTION = 3', 'VL_PIN = 1',
                     'VL_Y_HIGH = 1', 'VL_CIRC_Q = 4', 'VL_CIRC_Q = 6'):
            on = listing(tmp, base.format(defs=defs))
            assert not on.startswith('error') and on != plain, f'{defs}: {on[:300]}'
        none = listing(tmp, base.format(defs='').replace('VL_CIRC = 4\n', ''))
        assert none.startswith('error'), 'vl_contact_* without VL_CIRC assembles'
        sizes = {}
        for defs in ('', 'VL_CIRC_BOUNCE = 100\nVL_CIRC_HEAVY = 2\nVL_CIRC_FRICTION = 3\nVL_PIN = 1\nVL_CIRC_SLEEP = $28'):
            src = Path(tmp) / 'z.s'
            src.write_text(base.format(defs=defs).replace('.include "verlet_con.asm"', 'vl_end:\n.include "verlet_con.asm"')
                           .replace('.include "verlet_circ.asm"', 'vl_beg:\n.include "verlet_circ.asm"'))
            import subprocess
            inc = [a for d in harness.INCLUDES for a in ('-I', str(d))]
            subprocess.run(['ca65', *inc, '-l', str(Path(tmp) / 'z.lst'), '-o', str(Path(tmp) / 'z.o'), str(src)],
                           check=True)
            lst = (Path(tmp) / 'z.lst').read_text()
            beg = int(re.search(r'^(\w{6})r \d\s+vl_beg:', lst, re.M).group(1), 16)
            end = int(re.search(r'^(\w{6})r \d\s+vl_end:', lst, re.M).group(1), 16)
            sizes['every switch' if defs else 'plain'] = end - beg
    print('switches: VL_CIRC_BOUNCE, _HEAVY, _FRICTION, VL_PIN, VL_Y_HIGH, VL_CIRC_Q 4/6 change the code; '
          'vl_contact_* stop the assembly without VL_CIRC; code ' +
          ', '.join(f'{k} {v} B' for k, v in sizes.items()) + ' (+ 256 B reciprocals in RODATA)')


def main():
    hit = check(CONF_A, random.Random(3))
    assert all(v > 30 for k, v in hit.items() if k != 'wake') and hit.get('wake', 0) > 5, hit
    check(CONF_B, random.Random(4))
    check_c()
    check_switches()
    if '--cycles' in sys.argv:
        cycles()


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'dev/tests'))
    main()
