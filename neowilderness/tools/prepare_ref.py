#!/usr/bin/env python3
"""prepare_ref.py: the journey preparation of the original (GO1, GO2), in Python.

Lot 1 of docs/ORIGINAL_GAP.md (P1, P2), docs/SCENARIOS.md section 11. Every
formula below was read in the disassembly of GO1 ($5800), GO2 ($2000) and
GO3 ($3000) of the Sierra Nevadas side and checked on the original by
tools/re_prepare_probe.py (imposed RND, fixed answers). src/prepare.s
computes the same values with the same ROM floating point operations;
tests/test_prepare.py compares the three.

Body (GO2 $2119, $2337):
  ideal weight W0 = (223 + h (0.073 h - 5.98) - 10 [female]) (1 + 0.065 frame)
                    (h inches, frame -1 small, 0 medium, 1 large)
  overweight ow   = INT(w - W0)                         ($4BBE, floor)
  metabolism      = w / 100 kcal/min                    ($4C20 = $4C25)
  ratio           = w / W0 if ow > 0 else W0 / w
  Hmax            = 10 / (0.022 pulse ratio^1.5) x sqrt(0.033 age) (age < 31)
                    10 / (0.022 pulse ratio^1.5) / (0.033 age)     (age >= 31)
                    ($4C2F; health $4C34 = Hmax before the clamp to [1.1, 10]
                    of normal play; verdict 0..4 by < 1.7, < 3.5, then
                    INT(Hmax + .5) < 6, < 8)
  surface         S = 0.00919928 sqrt(h w); thermal Q = 2 INT(1335 S)
                    + INT(800 S) + 2630                 ($4C1A, 6058 at 165 lb)
  research mode   no questions: 175 lb, 73 in, 25 years, pulse 42, medium
                    male; no clamp, no verdict, no crash injury.
Level L and RND (GO1, GO2):
  date (random)   d = .05 + .05 L r; north: .55 + .05 L r (r > .5), else
                  .55 + .05 L r - .05 L; south: .05 + .05 L r + .025 L
                  (r <= .5), else 1.05 + .05 L r - .075 L; then min(., .997)
  date (chosen)   (month - 1) .085 + .065 r, hour as typed (0..24)
  hour (random)   12 + 1.2 L r (r > .5), else 12 + 1.2 L r - 1.2 L
  crash injury    n = INT(.45 r L - .3), 0..3: none, cuts, arm, leg
                  (scenario 1, normal play)
  wreck lot       nine groups of the 75 items (21, 1, 15, 3, 11, 5, 3, 3,
                  13): start a = INT(r (s-1) + .5) + 1, stride b = INT(r (s-2)
                  + .5) + 1 (groups 1 and 3: no multiple of 3, 5, 7, 10, 14
                  -> 4), k = INT((11 - L) s / 10 + .5) items from a by b
                  (mod s); always DOWN PARKA, BACKPACK, WATER, MATCHES, TOPO
                  MAP, KNIFE, 2QT CANTEEN, CANDYBARS; BOOTS, JERSEY, JEANS,
                  COTTN SOCKS worn; STAR CHART, BINOCULARS, GOLD absent;
                  research: COMPASS, WATCH, ALTIMETER, FLASHLGHT, THERMOMETER
  uses            W8 of items 38..66, W5 and W6 of FUEL x 1/sqrt(L) (INT)
  precipitation   F = max(.1, .1 storm (2 + 29 (1 + sin(360 date + 47)deg)))
                  (Sierra header; the port's module_weather_daily)
  first front     start 3000 / (L F) + 20 (4-minute units), duration
                  INT(min(540, 20 + 10 L F r)); wind INT(16 r) + 2 mph;
                  temperature wave phase 2 pi r; moon 60 - 18 L (not ported)
  words           terrain MODERATE (L < 4), VARIED (< 8), PUNISHING;
                  difficulty LOW (1), LENIENT (2-3), RESPECTABLE (4-5),
                  CHALLENGING (6-7), BACK-BREAKING (8-10)
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
from gendata import fp as encode  # noqa: E402,F401  (Applesoft 5-byte float)


def decode(b):
    if len(b) < 5 or b[0] == 0:
        return 0.0
    mant = ((b[1] | 0x80) << 24) | (b[2] << 16) | (b[3] << 8) | b[4]
    v = mant / 2 ** 32 * 2 ** (b[0] - 128)
    return -v if b[1] & 0x80 else v


SIZES = (21, 1, 15, 3, 11, 5, 3, 3, 13)          # GO2 $26B5
ALWAYS = (2, 21, 22, 38, 52, 59, 64, 25)          # GO2 $26AC
WORN = (5, 14, 15, 18)
ABSENT = (56, 68, 75)
RESEARCH_ITEMS = (53, 54, 55, 66, 69)
# Uses (W8) of items 38..66 in the Journey template (T$21, before GO2 $26C2).
USES = (48, 0, 16, 0, 0, 0, 14, 21, 24, 24, 24, 35, 28, 63, 0, 0, 0, 0, 0, 36,
        0, 0, 0, 0, 0, 0, 0, 0, 12)
FUEL_OZ, FUEL_VOL = 16, 138                        # W5, W6 of FUEL (40)
FOOD = range(22, 38)                               # all on the ground: W7 = W5, W8 = 0
RESEARCH_BODY = dict(sex='M', weight=175, frame='M', height=73, age=25, pulse=42)
FROZEN_BODY = dict(sex='M', weight=165, frame='M', height=70, age=31, pulse=55)   # Hmax 7.8666, Q 6058, ow 2
TERRAIN = ('MODERATE', 'VARIED', 'PUNISHING')
DIFFICULTY = ('LOW', 'LENIENT', 'RESPECTABLE', 'CHALLENGING', 'BACK-BREAKING')
INJURY = ('NOT BEEN INJURED', 'RECEIVED SEVERAL BAD CUTS', 'RECEIVED A BROKEN ARM',
          'RECEIVED A BROKEN LEG')
VERDICT = ('YOU SHOULD SEE A DOCTOR IMMEDIATELY!', 'YOUR PHYSICAL CONDITION IS TERRIBLE!',
           'YOU COULD BENEFIT FROM A PHYSICAL FITNESS PROGRAM.',
           'YOU ARE REALLY IN PRETTY GOOD SHAPE.', 'YOU ARE OLYMPIC ATHLETE MATERIAL!')

# Probe and test cases: Sierra Nevada, plane crash.
CASES = [
    dict(name='body250', level=4, rnd=0.5, date=(5, 7), research=False,
         sex='M', weight=250, frame='M', height=70, age=30, pulse=70, wildlife='1', storm='1'),
    dict(name='female', level=4, rnd=0.25, date=(1, 23), research=False,
         sex='F', weight=120, frame='S', height=62, age=45, pulse=80, wildlife='.5', storm='2.5'),
    dict(name='large', level=6, rnd=0.625, date=(11, 0), research=False,
         sex='M', weight=330, frame='L', height=85, age=8, pulse=35, wildlife='100', storm='.1'),
    dict(name='research', level=4, rnd=0.75, date=None, research=True, wildlife='3', storm='.2'),
    dict(name='l1r3', level=1, rnd=0.3, date=None, research=False, **FROZEN_BODY, wildlife='1', storm='1'),
    dict(name='l1r9', level=1, rnd=0.9, date=None, research=False, **FROZEN_BODY, wildlife='1', storm='1'),
    dict(name='l4r3', level=4, rnd=0.3, date=None, research=False, **FROZEN_BODY, wildlife='1', storm='1'),
    dict(name='l4r9', level=4, rnd=0.9, date=None, research=False, **FROZEN_BODY, wildlife='1', storm='1'),
    dict(name='l7r9', level=7, rnd=0.9, date=None, research=False, **FROZEN_BODY, wildlife='1', storm='1'),
    dict(name='l10r3', level=10, rnd=0.3, date=None, research=False, **FROZEN_BODY, wildlife='1', storm='1'),
    dict(name='l10r9', level=10, rnd=0.9, date=None, research=False, **FROZEN_BODY, wildlife='1', storm='1'),
]


def port_answers(case):
    """Keys typed after P, the region and the level at the port's menu."""
    out = ['Y', str(case['date'][0]), str(case['date'][1])] if case['date'] else ['N']
    if case['research']:
        out.append('R')
    else:
        out += ['P', case['sex'], str(case['weight']), case['frame'], str(case['height']),
                str(case['age']), str(case['pulse'])]
    return out + [case['wildlife'], case['storm']]


def original_answers(case):
    return ['P'] + port_answers(case)       # 1. plane crash [P] or lost city [L]


def body(sex, weight, frame, height, age, pulse, research=False):
    f = {'S': -1, 'M': 0, 'L': 1}[frame]
    w0 = (223 + height * (0.073 * height - 5.98) - 10 * (sex == 'F')) * (1 + 0.065 * f)
    ow = math.floor(weight - w0)
    ratio = weight / w0 if ow > 0 else w0 / weight
    p = 10 / (0.022 * pulse * ratio ** 1.5)
    hmax = math.sqrt(0.033 * age) * p if age < 31 else p / (0.033 * age)
    s = 0.00919928474468179 * math.sqrt(height * weight)
    q = 2 * int(1335 * s) + int(800 * s) + 2630
    health = hmax
    verdict = None
    if not research:
        hmax = min(10.0, max(1.1, hmax))
        verdict = (0 if hmax < 1.7 else 1 if hmax < 3.5 else
                   2 if int(hmax + .5) < 6 else 3 if int(hmax + .5) < 8 else 4)
    return dict(w0=w0, overweight=ow, rate=weight / 100, hmax=hmax, health=health, q=q,
                verdict=verdict, eat=weight / 100 + 0.004 * weight,
                composition=1 - ow / weight, gold=(2 * weight + 40, weight // 2))


def random_date(level, r, north=True):
    d = .05 + .05 * level * r
    if north:
        date = .55 + .05 * level * r if r > .5 else .55 + .05 * level * r - .05 * level
    else:
        date = d + .025 * level if r <= .5 else 1 + d - .075 * level
    return min(date, .997)


def random_hour(level, r):
    return 12 + 1.2 * level * r if r > .5 else 12 + 1.2 * level * r - 1.2 * level


def injury(level, r):
    return max(0, min(3, math.floor(.45 * r * level - .3)))


def wreck(level, r, research=False):
    """B1 (placement) of items 0..75 for an imposed RND r."""
    b1 = [0xFF] * 76
    b1[0] = b1[52] = 0
    for i in ALWAYS:
        b1[i] = 0
    base = 0
    for g, s in enumerate(SIZES, 1):
        a = math.floor(r * (s - 1) + .5) + 1
        b = (math.floor(r * (s - 2) + .5) + 1) & 255
        if g in (1, 3):
            if b in (3, 6, 9, 12, 15, 18):
                b -= 1
            if b in (5, 7, 10, 14):
                b = 4
        k = int((11 - level) * s / 10 + .5)
        if k:
            pos, count = a, 1
            while True:
                if pos - s > 0:
                    pos -= s
                b1[base + pos] = 0
                if count == k:
                    break
                count += 1
                pos += b
        base += s
    for i in WORN:
        b1[i] = 1
    for i in ABSENT:
        b1[i] = 0xFF
    if research:
        for i in RESEARCH_ITEMS:
            b1[i] = 0
    return b1


def uses(level):
    """(W8 of 38..66, FUEL W5, FUEL W6), with the values whose product lands
    within 1e-6 of an integer (the ROM's SQR may fall on either side)."""
    k = 1 / math.sqrt(level)
    out, edges = [], set()
    for i, u in enumerate(list(USES) + [FUEL_OZ, FUEL_VOL]):
        v = u * k
        if abs(v - round(v)) < 1e-6 and round(v) != v:
            edges.add(i)
        out.append(int(v + 1e-9) if abs(v - round(v)) < 1e-9 else int(v))
    return out, edges


def precipitation(date, storm):
    f = .1 * storm * (2 + 29 * (1 + math.sin(math.radians(360 * date + 47))))
    return max(.1, f)


def front(level, freq, r):
    return 3000 / (level * freq) + 20, int(min(540, 20 + 10 * level * freq * r))


def words(level):
    terrain = 0 if level < 4 else 1 if level < 8 else 2
    difficulty = 0 if level < 2 else 1 if level < 4 else 2 if level < 6 else 3 if level < 8 else 4
    return TERRAIN[terrain], DIFFICULTY[difficulty]


def frequency(text):
    return min(100.0, float(text))


def expected(case, north=True):
    """Every value of a case, as the original computes it."""
    L, r = case['level'], case['rnd']
    if case['date']:
        date, hour = (case['date'][0] - 1) * .085 + .065 * r, float(case['date'][1])
        date = min(date, .997)
    else:
        date, hour = random_date(L, r, north), random_hour(L, r)
    research = case['research']
    b = body(**(RESEARCH_BODY if research else {k: case[k] for k in FROZEN_BODY}), research=research)
    storm, wildlife = frequency(case['storm']), frequency(case['wildlife'])
    freq = precipitation(date, storm)
    start, duration = front(L, freq, r)
    out = dict(date=date, hour=hour, injury=0 if research else injury(L, r),
               b1=wreck(L, r, research), uses=uses(L), precipitation=freq, front=start,
               duration=duration, wind=int(16 * r) + 2, phase=2 * math.pi * r,
               moon=int(60 - 18 * L), wildlife=wildlife, storm=storm, words=words(L),
               weight=(RESEARCH_BODY if research else case)['weight'], **b)
    return out


def from_original(page3, state):
    """Decode the probe's dumps ($0300-$03FF, $4000-$4FFF)."""
    def f(a):
        return decode(state[a - 0x4000:a - 0x4000 + 5])

    def w(a, signed=False):
        v = state[a - 0x4000] | state[a - 0x3FFF] << 8
        return v - 65536 if signed and v >= 32768 else v

    def row(base):
        return [state[base - 0x4000 + 2 * i] | state[base - 0x3FFF + 2 * i] << 8 for i in range(76)]
    w5, w6, w7, w8 = row(0x417C), row(0x4214), row(0x42AC), row(0x4344)
    return dict(injury=page3[0x0B], b1=list(state[0x4C:0x4C + 76]), w5=w5, w6=w6, w7=w7, w8=w8,
                weight=w(0x4BF6), overweight=w(0x4BBE, True), rate=f(0x4C20), base=f(0x4C25),
                hmax=f(0x4C2F), health=f(0x4C34), q=w(0x4C1A), date=f(0x4C89), hour=f(0x4C57),
                front=f(0x4C9D), duration=w(0x4BFE), wind=state[0x4B9F - 0x4000],
                phase=f(0x4CCF), moon=w(0x4BC0, True), wildlife=f(0x4C4D), storm=f(0x4C52),
                precipitation=f(0x4C43), research=state[0x4B59 - 0x4000],
                terrain=page3[0x07], difficulty=page3[0x11], score_factor=state[0x4B99 - 0x4000],
                conditions=list(state[0x4821 - 0x4000:0x4821 - 0x4000 + 15]),
                raw=dict(rate=state[0xC20:0xC25].hex(), hmax=state[0xC2F:0xC34].hex(),
                         health=state[0xC34:0xC39].hex(), date=state[0xC89:0xC8E].hex(),
                         hour=state[0xC57:0xC5C].hex(), front=state[0xC9D:0xCA2].hex(),
                         phase=state[0xCCF:0xCD4].hex(), precipitation=state[0xC43:0xC48].hex()))


if __name__ == '__main__':
    for c in CASES:
        e = expected(c)
        print(c['name'], {k: (round(v, 6) if isinstance(v, float) else v) for k, v in e.items()
                          if k not in ('b1', 'uses')})
    print('frozen body:', body(**FROZEN_BODY))
