#!/usr/bin/env python3
"""src/dhgr_cols.s on the POM2 IIe core (a2shot --iie), byte for byte.

The bench src/dhgr_test.s (ProDOS, loaded by NEODHGR.SYSTEM) interprets a script loaded at $4000 (page-1
build) or $2000 (page-2 build). After each checkpoint the harness peeks
main $2000-$3FFF, then aux through PAGE2 (80STORE on) or RAMRD (page 2),
and compares the visible rows with a Python model of the primitives and
with tools/dhgr_ref.py frames. Cycles come from a2shot's `until` counters:
elapsed = arrival at checkpoint k+1 - resumption after checkpoint k
(script interpretation included; the interpreter cost is reported).

  test_dhgr_cols.py [--map build/dhgr/map.bin]      run the IIe tests
  test_dhgr_cols.py --demo-po OUT.po --map MAP     ProDOS demo disk for dhgr.mk
"""
import argparse, bisect, random, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402
import dhgr_ref as R  # noqa: E402
import dhgr_palette as P  # noqa: E402

BUILD = HERE / 'build/dhgr'
DEMO = ROOT / 'dist/NEODHGR_TEST.po'
CPU_HZ = a2test.CPU_HZ


# ---------------------------------------------------------------------------
class Script:
    """Commands of src/dhgr_test.s; 140-byte band tables follow the commands."""

    def __init__(self, base=0x4000):
        self.base, self.cmds, self.tables, self.patches = base, bytearray(), [], []
        self.checks = 0

    def clear(self, c): self.cmds += bytes((1, c))
    def span(self, x, y0, y1, c): self.cmds += bytes((2, x, y0, y1, c))
    def check(self): self.cmds.append(4); self.checks += 1
    def devclear(self, c): self.cmds += bytes((5, c))
    def group(self, y0, y1, g, c): self.cmds += bytes((8, y0, y1, g, c))

    def column(self, x, runs):
        if not runs:
            self.cmds += bytes((7, x, 0))
        for k in range(0, len(runs), 255):
            part = runs[k:k + 255]
            self.cmds += bytes((7, x, len(part))) + b''.join(bytes(r) for r in part)

    def band(self, x0, x1, c, top, bot):
        self.cmds += bytes((3, x0, x1, c))
        for t in (top, bot):
            self.patches.append((len(self.cmds), len(self.tables)))
            self.tables.append(bytes(t))
            self.cmds += b'\0\0'

    def bufclr(self): self.cmds.append(10)
    def flush(self, g, y0, y1): self.cmds += bytes((12, g, y0, y1))

    def bufcol(self, g, k, runs):
        """runs: (y0, y1, packed a << 4 | b) as from pair_runs."""
        assert len(runs) < 256
        self.cmds += bytes((11, g, k, len(runs))) + b''.join(bytes(r) for r in runs)

    def key(self): self.cmds.append(13)

    def load(self, name):
        self.cmds += bytes((14, len(name))) + name.encode('ascii')

    def bank(self, x, y0, y1, c):
        self.cmds += bytes((9, 2, x, y0, y1, c))
        self.checks += 1

    def text(self, lines):
        self.cmds += bytes((6, len(lines)))
        for line in lines:
            self.cmds += line.ljust(80)[:80].encode('ascii')

    def end(self):
        self.cmds.append(0)
        out = bytearray(self.cmds)
        addr = self.base + len(out)
        where = []
        for t in self.tables:
            where.append(addr)
            out += t
            addr += len(t)
        for at, k in self.patches:
            out[at:at + 2] = where[k].to_bytes(2, 'little')
        return bytes(out)


# ---------------------------------------------------------------------------
class Model:
    """Expected effect of the primitives on a 192 x 140 colour page."""

    def __init__(self):
        self.page = [[0] * 140 for _ in range(192)]

    def clear(self, c):
        self.page = [[c] * 140 for _ in range(192)]

    def span(self, x, y0, y1, c):
        for y in range(y0, min(y1, 192)):
            self.page[y][x] = c

    def band(self, x0, x1, c, top, bot):
        for x in range(x0, x1):
            self.span(x, top[x], bot[x], c)

    def group(self, y0, y1, g, c):
        for x in range(7 * g, 7 * g + 7):
            self.span(x, y0, y1, c)


def visible(bank):
    return b''.join(bank[hgr_offset(y):hgr_offset(y) + 40] for y in range(192))


def first_difference(actual, expected):
    for y in range(192):
        for name, i in (('main', 0), ('aux', 1)):
            a = actual[i][hgr_offset(y):hgr_offset(y) + 40]
            e = expected[i][hgr_offset(y):hgr_offset(y) + 40]
            if a != e:
                b = next(k for k in range(40) if a[k] != e[k])
                return f'row {y} {name} byte {b}: {a[b]:02X} != {e[b]:02X}'
    return None


# ---------------------------------------------------------------------------
PRODOS = ROOT / 'dev/tools/prodos'
BENCH_LOAD = 0x7400


def build_po(out, binary, files, volume='NEODHGR', work=None):
    """Bootable ProDOS 5.25" image: PRODOS, NEODHGR.SYSTEM (src/bench_boot.s)
    and the bench DHGRTEST at $7400, plus {name: (bytes, load address)}."""
    with tempfile.TemporaryDirectory(prefix='dhgr-stage-') as stage:
        stage = Path(stage)
        (stage / 'PRODOS#FF0000').write_bytes((PRODOS / 'PRODOS').read_bytes())
        (stage / 'NEODHGR.SYSTEM#FF2000').write_bytes((BUILD / 'NEODHGR.SYSTEM').read_bytes())
        (stage / f'DHGRTEST#06{BENCH_LOAD:04X}').write_bytes(Path(binary).read_bytes())
        for name, (data, addr) in files.items():
            (stage / f'{name}#06{addr:04X}').write_bytes(data)
        subprocess.run(['python3', str(PRODOS / 'build_volume.py'), str(stage), str(out),
                        '--volume', volume, '--boot', str(PRODOS / 'boot.bin'), '--blocks', '280'],
                       check=True, capture_output=True)
    return Path(out)


def build_disk(work, binary, script, load):
    return build_po(Path(work) / 'test.po', binary, {'SCENE': (script, load)})


def segments(mapfile):
    """{name: (start, end)} of an ld65 map file."""
    out = {}
    text = Path(mapfile).read_text().split('Segment list:')[1]
    for line in text.splitlines()[4:]:
        parts = line.split()
        if len(parts) < 4:
            break
        out[parts[0]] = (int(parts[1], 16), int(parts[2], 16) + 1)
    return out


def run(script, page2=False, shots=()):
    """Run a script. Returns ([(main, aux, switches)] per checkpoint, costs):
    costs[k] = (total, library) cycles between checkpoints k and k+1, where
    library counts only PCs in CODE (dev dhgr_clear_asm), DCCODE and DCROWS."""
    suffix = '4' if page2 else ''
    L = a2test.labels(BUILD / f'dhgr_test{suffix}.lbl')
    seg = segments(BUILD / f'dhgr_test{suffix}.map')
    lib = [seg[n] for n in ('CODE', 'DCCODE', 'DCROWS')]
    base = 0x4000 if page2 else 0x2000
    aux_on, aux_off = (('poke:C003:00', 'poke:C002:00') if page2 else ('poke:C055:00', 'poke:C054:00'))
    steps = []
    for k in range(script.checks):
        steps.append(L.until('checkpoint', 4000) if k == 0 else f'pcprof:{L["checkpoint"]:04X}:4000')
        steps += ['peek:C013:2', 'peek:C018:8', f'peek:{base:04X}:8192', aux_on,
                  f'peek:{base:04X}:8192', aux_off]
        for when, path in shots:
            if when == k:               # let the beam scan the new modes first
                steps += ['wait:2', f'shot:{path}']
        steps += [L.poke('dt_go', 1), L.until('cp_resume', 100)]
    data = script.end()
    limit = 0x2000 if page2 else 0x7400 - 0x4000
    assert len(data) <= limit, f'script too large: {len(data)} > {limit}'
    with tempfile.TemporaryDirectory(prefix='dhgr-cols-') as work:
        disk = build_disk(work, BUILD / f'dhgr_test{suffix}.bin', data, 0x2000 if page2 else 0x4000)
        r = a2test.run(disk, steps, iie=True, timeout=900)
    costs = []
    names = sorted((v, k) for k, v in L.items() if k.startswith(('dc_', '_dhgr')) and v >= 0x200)
    starts = [v for v, _ in names]
    global BREAKDOWN
    BREAKDOWN = []
    for line in r.out.splitlines():
        if line.startswith('pcprof '):
            costs.append([int(line.split('cycles=')[1]), 0])
            BREAKDOWN.append({})
        elif line.startswith('pc '):
            _, addr, spent = line.split()
            a = int(addr, 16)
            if any(lo <= a < hi for lo, hi in lib):
                costs[-1][1] += int(spent)
                i = bisect.bisect_right(starts, a) - 1
                name = names[i][1] if i >= 0 else '?'
                BREAKDOWN[-1][name] = BREAKDOWN[-1].get(name, 0) + int(spent)
    dumps = r.dumps
    out = []
    for k in range(script.checks):
        banks, flags, main, aux = dumps[4 * k:4 * k + 4]
        out.append((main, aux, banks + flags))
    return out, [tuple(c) for c in costs]


def expect(model):
    return R.encode(model.page)


def compare(label, got, model_or_banks):
    exp = expect(model_or_banks) if isinstance(model_or_banks, Model) else model_or_banks
    diff = first_difference(got[:2], exp)
    assert diff is None, f'{label}: {diff}'


# ---------------------------------------------------------------------------
def palette_bars(s, m):
    """16 bars of 8 columns (column 128..139 white), all rows, via dc_band."""
    for c in range(16):
        x0, x1 = 8 * c, 8 * c + 8
        s.band(x0, x1, c, [0] * 140, [192] * 140)
        m.band(x0, x1, c, [0] * 140, [192] * 140)
    s.band(128, 140, 15, [0] * 140, [192] * 140)
    m.band(128, 140, 15, [0] * 140, [192] * 140)


def demo_frame(mapbin):
    px, py, h = (int.from_bytes(mapbin[o:o + 2], 'little') for o in (2, 4, 6))
    h = (h + 140) % 560                      # golden hour over the eastern ridges
    return R.frame(mapbin, px, py, h, R.Sky(body=((h + 10) % 560, 84), sun8=12))


def frame_by_columns(s, page):
    for x, runs in enumerate(R.column_runs(page)):
        s.column(x, runs)


def frame_by_bands(s, page, sky):
    """Solid zenith sky as one dc_band layer, everything else as column spans."""
    zen = P.MOOD[sky.mood]['sky'][0]
    bots = []
    for x in range(140):
        y = 16
        limit = P.SKY_ROWS[0] if not isinstance(zen, tuple) else 16
        while y < limit and page[y][x] == zen:
            y += 1
        bots.append(y)
    s.band(0, 140, zen if not isinstance(zen, tuple) else 0, [16] * 140, bots)
    rest = [[page[y][x] if (y < 16 or y >= bots[x]) else P.BLACK for x in range(140)]
            for y in range(192)]
    for x, runs in enumerate(R.column_runs(rest)):
        s.column(x, runs)


def pair_runs(page, x):
    """Column x as runs (y0, y1, a << 4 | b) of solid colours or checkerboard
    pairs (a on even row + column, b on odd), black runs omitted."""
    out, y = [], 0
    while y < 192:
        c0 = page[y][x]
        c1 = page[y + 1][x] if y + 1 < 192 else c0
        a, b = (c0, c1) if (y + x) % 2 == 0 else (c1, c0)
        y1 = y + 1
        while y1 < 192 and page[y1][x] == (a if (y1 + x) % 2 == 0 else b):
            y1 += 1
        if y1 == y + 1:
            a = b = c0
        if a or b:
            out.append((y, y1, a << 4 | b))
        y = y1
    return out


def frame_by_groups(s, page):
    """Column buffers + dc_flush: 7 columns of (dithered) runs, one group write."""
    for g in range(20):
        s.bufclr()
        for k in range(7):
            s.bufcol(g, k, pair_runs(page, 7 * g + k))
        s.flush(g, 0, 192)


MOOD_TEXT = {
    'day': ('sun >= 10 deg (S8 >= 22), clear', 'blue sky, light dithered horizon; far ridges dark blue, far snow grey'),
    'overcast': ('sun >= 10 deg, weather_sky != 0', 'grey sky and haze; no sun; water grey'),
    'golden': ('sun 2..10 deg (S8 4..21)', 'peach horizon, orange/brown ground, purple peaks, pink snow, orange sun'),
    'sunset': ('sun -1..2 deg (S8 -2..3)', 'purple-pink-orange sky, red ground, black silhouettes, red sun'),
    'overcast dusk': ('sun -1..10 deg, clouds', 'dark blue / grey / pink haze, dim brown ground'),
    'civil': ('sun -6..-1 deg (S8 -13..-3)', 'dark blue to pink sky, near-black land, pink water'),
    'nautical': ('sun -12..-6 deg (S8 -27..-14)', 'black sky with a blue horizon; only snow and water show'),
    'night bright': ('moonlight >= 9: full Moon (low: -2, clouds: -3)', 'black sky, blue horizon glow, dark green land, Moon glint on water'),
    'night dim': ('moonlight 6..8', 'dithered dark blue foreground, the rest black'),
    'night dark': ('moonlight < 6 (or Moon set)', 'black landscape, only the Moon (engine view_dark)'),
}


def text_lines(name='golden', k=2):
    when, look = MOOD_TEXT[name]
    lines = [f'NEOWILDERNESS DHGR  -  mood {k + 1}/10: {name.upper()}',
             f'When: {when}', look,
             'Any key: next mood    ESC or Q: quit to ProDOS    (80-column mixed-mode text)']
    assert all(len(line) <= 80 for line in lines), lines
    return lines


def demo_view(mapbin, name):
    """Golden-hour viewpoint (eastern ridges), the body in view, any mood."""
    import test_dhgr_ref as TR
    px, py, h = (int.from_bytes(mapbin[o:o + 2], 'little') for o in (2, 4, 6))
    h = (h + 140) % 560
    return R.frame(mapbin, px, py, h, TR.mood_sky(name, (h + 10) % 560))


def demo_files(mapbin):
    """SCENE (starts at the golden hour) and MOOD0..MOOD9, each drawing its
    frame, printing its name, waiting for a key and loading the next."""
    files = {}
    for k, name in enumerate(P.MOODS):
        s = Script()
        frame_by_groups(s, demo_view(mapbin, name))
        s.text(text_lines(name, k))
        s.key()
        s.load(f'MOOD{(k + 1) % len(P.MOODS)}')
        data = s.end()
        assert len(data) <= BENCH_LOAD - 0x4000, (name, len(data))
        files[f'MOOD{k}'] = (data, 0x4000)
    s = Script()
    s.clear(0)
    s.load(f'MOOD{P.MOODS.index("golden")}')
    files['SCENE'] = (s.end(), 0x4000)
    return files


def demo_frame(mapbin):
    return demo_view(mapbin, 'golden')


def demo_script(mapbin):
    """One-shot golden-hour frame with its text (palette/capture checks)."""
    s = Script()
    s.clear(0)
    frame_by_groups(s, demo_frame(mapbin))
    s.text(text_lines())
    s.check()
    return s


def test_demo(disk, mapbin):
    """Boot the demo .po: every mood byte for byte, then ESC back to ProDOS."""
    L = a2test.labels(BUILD / 'dhgr_test.lbl')
    steps = []
    first = P.MOODS.index('golden')
    order = [P.MOODS[(first + i) % len(P.MOODS)] for i in range(len(P.MOODS))]
    for i, name in enumerate(order):
        if i:
            steps.append('key: ')
        steps += [L.until('op_key', 4000), 'wait:2', 'peek:C018:8', 'peek:2000:8192', 'poke:C055:00',
                  'peek:2000:8192', 'poke:C054:00', f"shot:{BUILD / ('pom2_mood_' + name.replace(' ', '_') + '.png')}"]
    steps += ['key:\\e', 'wait:120', 'peek:C013:2', 'peek:C018:8', 'peek:C07E:2']
    r = a2test.run(disk, steps, iie=True, timeout=900)
    for i, name in enumerate(order):
        flags, main, aux = r.dumps[3 * i:3 * i + 3]
        assert flags[0] & 0x80 and flags[3] & 0x80, (name, '80STORE / mixed mode')
        compare(f'demo {name}', (main, aux), R.encode(demo_view(mapbin, name)))
    banks, flags, dh = r.dumps[-3:]
    assert not (banks[0] | banks[1]) & 0x80, 'RAMRD/RAMWRT left on after QUIT'
    assert not flags[0] & 0x80 and flags[2] & 0x80 and not flags[7] & 0x80, \
        ('QUIT must leave 40-column text, 80STORE off', flags.hex())
    print(f'  demo .po: boots, {len(order)} moods byte for byte (key cycles), ESC -> ProDOS text: OK')


# ---------------------------------------------------------------------------
def test_primitives(page2=False):
    s, m, labels = Script(0x2000 if page2 else 0x4000), Model(), []

    def check(label):
        s.check()
        labels.append((label, [row[:] for row in m.page]))

    s.clear(0); m.clear(0); check('dc_clear 0')
    s.clear(9); m.clear(9); check('dc_clear 9 (orange)')
    s.devclear(0); m.clear(0); check('dev dhgr_clear_asm 0')
    s.clear(0); m.clear(0)
    palette_bars(s, m); check('palette bars (dc_band)')
    s.clear(0); m.clear(0)
    for x in range(140):                     # every phase, both banks, all rows
        s.span(x, x % 3, 192 - x % 5, x % 16)
        m.span(x, x % 3, 192 - x % 5, x % 16)
    for x, y0, y1 in ((0, 5, 5), (7, 9, 3), (139, 191, 192), (70, 0, 1)):
        s.span(x, y0, y1, 15); m.span(x, y0, y1, 15)
    check('dc_vspan every column, edges, empty spans')
    rnd = random.Random(1985)
    count = 200 if page2 else 400           # the page-2 script holds 8 KB
    for _ in range(count):                   # neighbours must survive RMW
        x, y0 = rnd.randrange(140), rnd.randrange(192)
        y1, c = rnd.randrange(y0, 193), rnd.randrange(16)
        s.span(x, y0, y1, c); m.span(x, y0, y1, c)
    check(f'{count} random overlapping spans')
    s.clear(0); m.clear(0)
    for g, c in ((0, 1), (9, 12), (19, 15)):
        s.group(10 + g, 150 - g, g, c); m.group(10 + g, 150 - g, g, c)
    check('dc_group')
    for trial in range(3):                   # band: grouped and ragged parts
        x0, x1 = rnd.randrange(0, 20), rnd.randrange(100, 141)
        top = [rnd.randrange(0, 40) if trial else 20 + (x % 3) for x in range(140)]
        bot = [rnd.randrange(60, 193) if trial else 120 - (x % 4) for x in range(140)]
        c = rnd.randrange(1, 16)
        s.band(x0, x1, c, top, bot); m.band(x0, x1, c, top, bot)
    check('dc_band random profiles')
    s.bank(3, 0, 50, 6); m.span(3, 0, 50, 6)
    labels.append(('bank contract (aux selected by caller)', [row[:] for row in m.page]))
    check('after bank contract')
    results, cycles = run(s, page2)
    print(f'  page {2 if page2 else 1} ({"RAMRD/RAMWRT + aux mirror" if page2 else "80STORE + PAGE2"}):')
    for (label, page), (main, aux, flags) in zip(labels, results):
        if label.startswith('bank contract'):
            ramrd, ramwrt, store80, page2_flag = flags[0], flags[1], flags[2], flags[6]
            if page2:
                assert ramwrt & 0x80 and not ramrd & 0x80, 'caller RAMWRT aux not restored'
            else:
                assert store80 & 0x80 and page2_flag & 0x80, 'caller PAGE2 not restored'
            print(f'    {label}: restored OK')
            continue
        compare(label, (main, aux), R.encode(page))
        ramrd, ramwrt, store80, page2_flag = flags[0], flags[1], flags[2], flags[6]
        assert not (ramrd | ramwrt) & 0x80, (label, 'RAMRD/RAMWRT left on')
        assert bool(store80 & 0x80) != page2, (label, '80STORE')
        assert bool(page2_flag & 0x80) == page2, (label, 'PAGE2 / bank selection')
        print(f'    {label}: OK')
    return dict(zip([l for l, _ in labels], [(0, 0)] + cycles))


def test_frames(mapbin, shots_dir=None):
    """Full reference frames: per-column spans, then sky bands + spans."""
    px, py, h = (int.from_bytes(mapbin[o:o + 2], 'little') for o in (2, 4, 6))
    sky = lambda **k: R.Sky(**k)
    scenes = [('day, sun ahead, wreck', sky(body=((h + 20) % 560, 60), sun8=60), h),
              ('golden hour, heading +140', sky(body=((h + 150) % 560, 84), sun8=12), (h + 140) % 560),
              ('moonlit bright, heading +280', sky(night=True, body=((h + 290) % 560, 50), phase=11,
                                                    sun8=-60, moon8=80), (h + 280) % 560),
              ('moonlit dim, heading +140', sky(night=True, body=((h + 120) % 560, 40), phase=7,
                                                 sun8=-60, moon8=80), (h + 140) % 560)]
    cost = {}
    for label, sky, heading in scenes:
        page = R.frame(mapbin, px, py, heading, sky)
        exp = R.encode(page)
        stem = label.split(',')[0].replace(' ', '_')
        cycles = []
        for how, fill in (('spans', frame_by_columns), ('bands', lambda s, p: frame_by_bands(s, p, sky)),
                          ('groups', frame_by_groups)):
            s = Script()
            s.clear(0); s.check()
            fill(s, page); s.check()
            if how != 'groups' and len(s.end()) > 0x7400 - 0x4000:
                cycles.append(None)         # dithered rows: one span per row
                print(f'    {label}: {how} skipped, script {len(s.end())} bytes')
                continue
            shots = [(1, shots_dir / f'pom2_{stem}.png')] if shots_dir and how == 'groups' else []
            results, c = run(s, shots=shots)
            compare(f'{label}: {how}', results[1], exp)
            cycles.append(c[0])
            if how == 'groups':
                parts = BREAKDOWN[0]
                flush = parts.get('dc_flush', 0)
                bspan = parts.get('dc_bspan', 0)
        runs = sum(len(r) for r in R.column_runs(page))
        cost[label] = (cycles[0], cycles[1], cycles[2], runs)
        lib = lambda c: c[1] if c else '-'
        print(f'  {label}: {runs} runs; library cycles: column spans {lib(cycles[0])}, '
              f'zenith band + spans {lib(cycles[1])}, column buffers {bspan} + dc_flush {flush}: OK')
    return cost


def measure_spans():
    """Linear cost of dc_vspan: 140 columns of 1 row, then of 101 rows."""
    s = Script()
    s.clear(0); s.check()
    for x in range(140):
        s.column(x, [])
    s.check()
    for x in range(140):
        s.column(x, [(20, 21, 9)])
    s.check()
    for x in range(140):
        s.column(x, [(20, 121, 9)])
    s.check()
    for g in range(20):
        s.group(20, 121, g, 9)
    s.check()
    _, cycles = run(s)
    one, many, grouped = (c[1] for c in cycles[1:4])
    per_row = (many - one) / 100 / 140
    per_call = one / 140 - per_row
    print(f'  dc_vspan (library cycles): {per_call:.0f} per call + {per_row:.2f} per row and column '
          f'(1 or 2 banks: 15 per row and bank)')
    print(f'  dc_group, 20 groups x 101 rows: {grouped} cycles ({grouped / 20 / 101 / 7:.2f} per pixel and row)')
    return dict(per_call=per_call, per_row=per_row, grouped=grouped, one=one, many=many)


def palette_capture(path):
    """Measure the RGB of the 16 bars in an a2shot render (560 x 384 PNG)."""
    import zlib, struct
    raw = Path(path).read_bytes()
    pos, idat, w, h = 8, b'', 0, 0
    while pos < len(raw):
        n, kind = struct.unpack('>I4s', raw[pos:pos + 8])
        body = raw[pos + 8:pos + 8 + n]
        if kind == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', body[:10])
            bpp = {2: 3, 6: 4}[ctype]
        elif kind == b'IDAT':
            idat += body
        pos += 12 + n
    data = zlib.decompress(idat)
    stride = w * bpp
    prev = bytearray(stride)
    rows = []
    for y in range(h):
        f, line = data[y * (stride + 1)], bytearray(data[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], prev[i - bpp] if i >= bpp else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    y = h // 2
    out = []
    for c in range(16):
        x = (8 * c + 4) * w // 140
        out.append(tuple(rows[y][x * bpp:x * bpp + 3]))
    return tuple(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', type=Path, default=BUILD / 'map.bin')
    ap.add_argument('--demo-po', type=Path, help='build the ProDOS demo disk and exit')
    ap.add_argument('--shots', action='store_true', help='also save a2shot PNGs in build/dhgr')
    a = ap.parse_args()
    mapbin = a.map.read_bytes()
    if a.demo_po:
        build_po(a.demo_po, BUILD / 'dhgr_test.bin', demo_files(mapbin))
        return
    if sys.platform != 'darwin' or not a2test.A2SHOT.exists():
        print('SKIP: a2shot (IIe POM2 core) is required')
        return
    page1 = test_primitives()
    print(f'  dc_clear (both banks): {page1["dc_clear 9 (orange)"][1]} cycles; '
          f'dev/lib/hgrc dhgr_clear_asm: {page1["dev dhgr_clear_asm 0"][1]} cycles')
    test_primitives(page2=True)
    measure_spans()
    test_frames(mapbin, BUILD if a.shots else None)
    # Demo + palette measured on the POM2 renderer.
    s = Script()
    s.clear(0)
    palette_bars(s, Model())
    s.check()
    run(s, shots=[(0, BUILD / 'pom2_palette.png')])
    run(demo_script(mapbin), shots=[(0, BUILD / 'pom2_demo_mixed80.png')])
    test_demo(DEMO, mapbin)
    rgb = palette_capture(BUILD / 'pom2_palette.png')
    assert rgb == P.RGB, ('POM2 palette differs from dhgr_palette.RGB', rgb)
    print('  POM2 palette = dhgr_palette.RGB; captures in build/dhgr/pom2_*.png: OK')
    print('DHGR columns: OK')


if __name__ == '__main__':
    main()
