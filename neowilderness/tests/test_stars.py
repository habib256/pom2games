#!/usr/bin/env python3
"""src/stars.s + src/stars_draw.s on the POM2 IIe core (a2shot --iie).

The bench src/stars_test.s (ProDOS, NEOSTARS.SYSTEM) runs case records
(SCENE at $A000): the module stars_compute (at $8000), then a frame
drawn with the real dhgr_frame / column_setup / dspan of src/dhgr.s, the
render_sky zone loop and stars_column. At the first checkpoint of a case the
harness reads the resident list (st_a, st_row, st_bucket); at the
second, both DHGR banks. Both are compared with tools/stars_ref.py byte for
byte. Cycles come from a2shot pcprof between checkpoints, attributed to the
module (src/stars.s) and to stars_draw.s by PC.

  test_stars.py                    run the IIe tests
  test_stars.py --demo-po OUT.po   ProDOS demo disk for stars.mk
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402
import stars_ref as R  # noqa: E402
import dhgr_ref  # noqa: E402

BUILD = HERE / 'build/stars'
PRODOS = ROOT / 'dev/tools/prodos'
CASES, CASE_SIZE, CASE_TOP = 0xA000, 160, 20
STARS_ON, WAIT_KEY = 2, 0x10
MODE_FULL, MODE_BACK, MODE_TURN = 0, 4, 8
LIST_BYTES = 2 * R.LIST_MAX + R.BUCKETS


class Case:
    """One bench record and its expected list and frame."""

    def __init__(self, label, region=2, day=125, minute=23 * 60, heading=0, stars=True,
                 night=True, view_dark=True, clouds=False, sun8=-128, moon8=-20, phase=0,
                 moon=None, mode=MODE_FULL, c0=0, c1=140, tops=None, key=False, lat=None, lon=None,
                 tilt=0):
        name, rlat, rlon = R.REGIONS[region]
        self.label, self.region = label, name
        self.lat = rlat if lat is None else lat
        self.lon = rlon if lon is None else lon
        self.day, self.minute, self.heading = day, minute, heading
        self.stars, self.night, self.view_dark, self.clouds = stars, night, view_dark, clouds
        self.sun8, self.moon8, self.phase = sun8, moon8, phase
        self.moon = moon                        # (sky_bearing, sky_y) or None
        self.mode, self.c0, self.c1, self.key = mode, c0, c1, key
        self.tilt = tilt                        # LOOK UP 1, LOOK DOWN -1 (flags bits 5-6)
        self.tops = tops if tops is not None else R.ridge(heading)
        self.mood = R.engine_mood(night, view_dark, clouds, sun8, moon8, phase)
        self.thr = R.threshold(self.mood, clouds) if stars else 0
        self.vis = R.visible(day, minute, self.lat, self.lon, moon)

    def record(self):
        bearing, y = self.moon if self.moon else (0, 255)
        flags = (1 | (STARS_ON if self.stars else 0) | self.mode | (WAIT_KEY if self.key else 0)
                 | (self.tilt & 3) << 5)
        rec = bytes((flags, self.day & 255, self.day >> 8, self.minute & 255, self.minute >> 8,
                     self.lat & 255, self.lon & 255, bearing & 255, bearing >> 8, y,
                     int(self.night), int(self.view_dark), int(self.clouds), self.sun8 & 255,
                     self.moon8 & 255, self.phase, self.heading & 255, self.heading >> 8,
                     self.c0, self.c1)) + bytes(self.tops)
        assert len(rec) == CASE_SIZE
        return rec

    def expected_list(self):
        attr, row, buckets, srt = R.resident(self.vis)
        return attr + row + buckets, srt

    def columns(self):
        if self.mode == MODE_BACK:
            return range(self.c1 - 1, self.c0 - 1, -1)
        return range(140)

    def expected_page(self):
        _, srt = self.expected_list()
        return R.frame(self.heading, self.tops, self.mood, srt, self.thr, self.columns(), self.tilt)

    def drawn(self):
        _, srt = self.expected_list()
        px = R.star_pixels(self.heading, self.tops, srt, self.thr, self.tilt)
        cols = set(self.columns())
        return {k: v for k, v in px.items() if k[0] in cols}


def scene(cases):
    data = b''.join(c.record() for c in cases) + b'\0'
    assert len(data) <= 0xB900 - CASES, len(data)
    return data


def build_po(out, cases, volume='NEOSTARS'):
    with tempfile.TemporaryDirectory(prefix='stars-stage-') as stage:
        stage = Path(stage)
        (stage / 'PRODOS#FF0000').write_bytes((PRODOS / 'PRODOS').read_bytes())
        (stage / 'NEOSTARS.SYSTEM#FF2000').write_bytes((BUILD / 'NEOSTARS.SYSTEM').read_bytes())
        (stage / 'STARTEST#064000').write_bytes((BUILD / 'stars_test.bin').read_bytes())
        (stage / f'SCENE#06{CASES:04X}').write_bytes(scene(cases))
        subprocess.run(['python3', str(PRODOS / 'build_volume.py'), str(stage), str(out),
                        '--volume', volume, '--boot', str(PRODOS / 'boot.bin'), '--blocks', '280'],
                       check=True, capture_output=True)
    return Path(out)


def ranges(L):
    return {'module': (L['stars_compute'], L['stars_module_end']),
            'draw': (L['stars_frame'], L['stars_draw_end'])}


def run(cases, shots=None):
    """[(list bytes, (main, aux), {range: cycles} module, {range: cycles} frame,
    total frame cycles)] per case."""
    L = a2test.labels(BUILD / 'stars_test.lbl')
    steps = [L.until('stars_compute', 6000)]       # boot, then every interval is profiled
    for k in range(2 * len(cases)):
        steps.append(f'pcprof:{L["checkpoint"]:04X}:6000')
        if k % 2 == 0:
            steps.append(L.peek('st_a', LIST_BYTES))
        else:
            steps += ['peek:C018:8', 'peek:2000:8192', 'poke:C055:00', 'peek:2000:8192', 'poke:C054:00']
            if shots and k // 2 in shots:   # let the beam scan the frame first
                steps += ['wait:2', f'shot:{shots[k // 2]}']
        steps += [L.poke('dt_go', 1), L.until('cp_resume', 100)]
    with tempfile.TemporaryDirectory(prefix='stars-') as work:
        disk = build_po(Path(work) / 'test.po', cases)
        r = a2test.run(disk, steps, iie=True, timeout=1200)
    spans = ranges(L)
    profiles, cur = [], None
    for line in r.out.splitlines():
        if line.startswith('pcprof '):
            cur = {'total': int(line.split('cycles=')[1]), 'module': 0, 'draw': 0}
            profiles.append(cur)
        elif line.startswith('pc ') and cur is not None:
            _, addr, spent = line.split()
            a = int(addr, 16)
            for name, (lo, hi) in spans.items():
                if lo <= a < hi:
                    cur[name] += int(spent)
    out = []
    dumps = r.dumps
    for i in range(len(cases)):
        lst, flags, main, aux = dumps[4 * i:4 * i + 4]
        assert flags[0] & 0x80 and not flags[6] & 0x80, (cases[i].label, '80STORE on, main selected')
        # profile 2i ends at the list checkpoint (module), 2i + 1 at the frame one
        mod, frm = profiles[2 * i], profiles[2 * i + 1]
        out.append((lst, (main, aux), mod, frm))
    return out


def first_difference(actual, expected):
    for y in range(192):
        for name, i in (('main', 0), ('aux', 1)):
            a = actual[i][hgr_offset(y):hgr_offset(y) + 40]
            e = expected[i][hgr_offset(y):hgr_offset(y) + 40]
            if a != e:
                b = next(k for k in range(40) if a[k] != e[k])
                return f'row {y} {name} byte {b}: {a[b]:02X} != {e[b]:02X}'
    return None


def describe_list(lst):
    m = R.LIST_MAX
    return [(v['az'], v['row'], v['attr'])
            for v in R.decode_resident(lst[:m], lst[m:2 * m], lst[2 * m:])]


# ---------------------------------------------------------------------------
def moon_on_star(region=2, day=125, minute=23 * 60, heading=280):
    """A Moon centred on the brightest star of the view (to hide it)."""
    _, lat, lon = R.REGIONS[region]
    vis = R.visible(day, minute, lat, lon)
    inview = [v for v in vis if (v['az'] - heading + 70) % 560 < 140 and v['row'] < 80]
    v = inview[0]
    return (v['az'], v['row']), v


def cases():
    sierra_moon, hidden = moon_on_star()
    flat_high = [40] * 140
    out = [
        Case('Sierra, 6 May 23 h, north (Polaris), dark night', heading=0),
        Case('Sierra, 6 May 23 h, north, stars off (cost pair)', heading=0, stars=False),
        Case('Sierra, 6 May 23 h, south, dark night', heading=280),
        Case('Sierra, south, full Moon high (night bright: class 0, the figures)', heading=280,
             view_dark=False, moon8=60, phase=11, moon=sierra_moon),
        Case('Sierra, south, night dim (classes 0-1)', heading=280, view_dark=False, moon8=60,
             phase=8, moon=(0, 255)),
        Case('Sierra, south, overcast night: none', heading=280, clouds=True),
        Case('Sierra, 6 May 13 h, day: none', heading=280, minute=13 * 60, night=False,
             view_dark=False, sun8=60, moon8=-128),
        Case('Sierra, civil twilight: none', heading=280, minute=20 * 60, night=False,
             view_dark=False, sun8=-5, moon8=-128),
        Case('Sierra, nautical twilight: none', heading=280, minute=20 * 60 + 40, night=False,
             view_dark=False, sun8=-20, moon8=-128),
        Case('Sierra, south, high ridge (top 40): below the ridge', heading=280, tops=flat_high),
        Case('Bolivia, 6 May 21 h, south: Southern Cross', region=5, minute=21 * 60, heading=280),
        Case('Chile, 1 Jan 2 h, south-east', region=6, day=0, minute=2 * 60, heading=210),
        Case('New Guinea, 15 Aug 22 h, west', region=4, day=226, minute=22 * 60, heading=420),
        Case('Burma, 20 Nov 4 h, east', region=3, day=323, minute=4 * 60, heading=140),
        Case('British Columbia, 21 Dec 1 h, north', region=1, day=354, minute=60, heading=0),
        Case('British Columbia, 21 Dec 1 h, south-west', region=1, day=354, minute=60, heading=350),
        Case('Sierra, left turn columns 34..0 (backward)', heading=280, mode=MODE_BACK, c0=0, c1=35),
        Case('Sierra, right turn: scroll + columns 105..139', heading=280, mode=MODE_TURN),
        Case('Bolivia, right turn across north (azimuth wrap)', region=5, minute=21 * 60, heading=20,
             mode=MODE_TURN),
        Case('Sierra, 1 Jan 0 h, south (Sirius culminates)', day=0, minute=0, heading=280),
        # LOOK UP / DOWN (docs/LOOK_UPDOWN.md): rows + 96 * tilt, clipped to 0..159.
        Case('Sierra, north, looking up', heading=0, tilt=1, tops=[160] * 140),
        Case('Sierra, south, looking up, ridge', heading=280, tilt=1, tops=R.ridge(280, 150, 8)),
        Case('Sierra, south, looking down', heading=280, tilt=-1, tops=[160] * 140),
        Case('Bolivia, south, looking up: Southern Cross', region=5, minute=21 * 60, heading=280,
             tilt=1, tops=[160] * 140),
        Case('Sierra, looking up, right turn', heading=280, mode=MODE_TURN, tilt=1, tops=[160] * 140),
    ]
    out[3].hidden = hidden
    return out


def demo_cases():
    out = []
    for r, (name, lat, lon) in R.REGIONS.items():
        heading = 0 if lat > 0 else 280
        out.append(Case(f'{name} demo', region=r, minute=22 * 60, heading=heading, key=True))
    out.append(Case('Sierra south demo', heading=280, key=True))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo-po', type=Path, help='build the ProDOS demo disk and exit')
    a = ap.parse_args()
    if a.demo_po:
        build_po(a.demo_po, demo_cases())
        return
    if sys.platform != 'darwin' or not a2test.A2SHOT.exists():
        print('SKIP: a2shot (IIe POM2 core) is required')
        return
    cs = cases()
    BUILD.mkdir(parents=True, exist_ok=True)
    shots = {i: BUILD / f'pom2_shot_{i}.png' for i, c in enumerate(cs)
             if c.label.startswith(('Bolivia, 6 May', 'Sierra, 6 May 23 h, north (Polaris)'))}
    results = run(cs, shots)
    module_cycles, costs = [], {}
    for c, (lst, banks, mod, frm) in zip(cs, results):
        exp, srt = c.expected_list()
        assert lst == exp, (c.label, 'list', describe_list(lst), describe_list(exp))
        exp_banks = dhgr_ref.encode(c.expected_page())
        diff = first_difference(banks, exp_banks)
        assert diff is None, f'{c.label}: {diff}'
        drawn = c.drawn()
        module_cycles.append(mod['module'])
        costs[c.label] = (frm['total'], frm['draw'])
        extra = ''
        if c.thr == 0:
            assert not drawn, c.label
            extra = 'no star drawn'
        else:
            extra = f'{len(drawn)} star pixels'
        if hasattr(c, 'hidden'):
            assert all(v['index'] != c.hidden['index'] for v in srt), 'star behind the Moon kept'
            extra += f", {c.hidden['star']['name']} hidden by the Moon"
        print(f'  {c.label}: list {len(srt)}, mood {c.mood}, {extra}; module '
              f'{mod["module"]} cycles, frame {frm["total"]} '
              f'(stars_draw {frm["draw"]}): OK')
    # Specific facts on the reference side.
    bolivia = next(c for c in cs if c.label.startswith('Bolivia, 6 May'))
    names = {v['star']['name'] for v in bolivia.vis}
    assert {'ACRUX', 'MIMOSA', 'GACRUX', 'IMAI'} <= names, names
    north = cs[0]
    pol = [v for v in north.vis if v['star']['name'] == 'POLARIS']
    assert pol and (pol[0]['az'] - 0 + 70) % 560 < 140, 'Polaris in the northern view'
    on, off = costs[cs[0].label], costs[cs[1].label]
    full = cs[0]
    print(f'  module stars_compute: {min(module_cycles)}..{max(module_cycles)} cycles '
          f'({max(module_cycles) / a2test.CPU_HZ * 1000:.0f} ms worst)')
    print(f'  full view with stars: +{on[0] - off[0]} cycles over the same view without '
          f'({len(full.drawn())} pixels; stars_draw.s itself {on[1]}, stars off {off[1]})')
    print(f'  a2shot captures: {", ".join(str(p.relative_to(HERE)) for p in shots.values())}')
    print('Stars bench: OK')


if __name__ == '__main__':
    main()
