#!/usr/bin/env python3
"""Probe the original encounter rules of every region on the Apple II.

Only the Sierra Nevada map exists, so each region is reproduced the way the
original's own "Country Disk" did: the region sector replaces the region
bytes of TOPO in memory (records $6000-$607E except $603F/$605F, $60A4-$60A7,
$60AA-$60BA, names $60D0-$60FF, plus the latitude and declination TMAKE0
would choose at mid-range). The poke happens when GO1 is entered at $5800,
after MENU option 2 has loaded TOPO and before any game code read it; the
whole journey preparation (GO1/GO2/GO3, Journey disk) then runs natively.

1. journey: answers the preparation questions (plane crash, 6 May 7 h ...),
   keeps both introduction pages, the start state, the INVENTORY pages.
2. filters: T0A/S00 $5A2F on that native start state, success at $5AA3
   recorded, cases on both sides of every bound of the 13 types.
3. probability and water gate: T0A/S00 $5AA3 up to $5B46 (before RND).
4. reactions: T06/S04 and T0F/S07 thresholds stopped before RND, as
   re_animal_reactions_probe.py does for the Sierra; New Guinea trinkets.

Results: build/re_regions/, and build/regions/fauna.json (data for the
region packages). Original bytes stay in build/. Region 2 is run twice,
patched and unpatched, as a control of the method.
"""
import json, math, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE.parent / 'dev/tools'), str(HERE / 'tools')]
import a2test, smalldos, regions  # noqa: E402
from gendata import fp as encode  # noqa: E402
from re_env_fp import mbf  # noqa: E402

OUT = HERE / 'build/re_regions'
ANSWERS = ('P', 'Y', '5', '7', 'P', 'M', '160', 'M', '70', '30', '70', '1', '1')
STATE = (0x4000, 0x8000)


def text_page(mem):
    rows = []
    for r in range(24):
        o = (r % 8) * 0x80 + (r // 8) * 0x28
        line = ''
        for b in mem[o:o + 40]:
            c = b & 0x7F
            line += chr(c) if c >= 0x20 else chr(c + 0x40)
        rows.append(line.rstrip())
    while rows and not rows[-1]:
        rows.pop()
    return rows


def patch(region, header):
    """(address, byte) pokes that turn the Sierra TOPO into region `region`."""
    pokes = [(0x6000 + o, header[o]) for o in range(0x7F) if o not in (0x3F, 0x5F)]
    pokes += [(0x6000 + o, header[o]) for o in range(0xA4, 0xA8)]
    pokes += [(0x6000 + o, header[o]) for o in range(0xAA, 0xBB)]
    pokes += [(0x6000 + o, header[o]) for o in range(0xD0, 0x100)]
    if region != 2:   # keep the Sierra map's own 38 / 17
        c = regions.climate(header)
        lat = regions.tmake0_latitude(c['latitude_min'], c['latitude_max'], .5)
        dec = regions.tmake0_declination(c['latitude_min'], c['latitude_max'],
                                         c['declination'], lat)
        pokes += [(0x60A8, lat & 255), (0x60A9, dec & 255)]
    return pokes


def journey(pokes):
    steps = ['wait:5400', 'key:2\r', 'until:5800:3000']
    steps += [f'poke:{a:04X}:{v:02X}' for a, v in pokes]
    steps += ['wait:300', f'insert:{HERE / "build/JOURNEY.dsk"}', 'key:\r', 'wait:1500']
    for answer in ANSWERS:
        steps += [f'key:{answer}\r', 'wait:100']
    steps += ['wait:1400', 'peek:0400:1024', 'key:\r', 'wait:300', 'peek:0400:1024',
              'key:\r', 'wait:3000', 'peek:0000:49152', 'key:INV\r', 'wait:1500', 'peek:0400:1024']
    for _ in range(4):
        steps += ['key: ', 'wait:400', 'peek:0400:1024']
    steps += ['key:\r', 'wait:600']
    r = a2test.run(HERE / 'build/SIERRA.woz', steps, emulator=a2test.A2SHOT, timeout=900)
    d = r.dumps
    assert len(d) == 8, len(d)
    pages = []
    for mem in d[3:]:
        page = text_page(mem)
        if page not in pages:
            pages.append(page)
    return {'intro': [text_page(d[0]), text_page(d[1])], 'ram': d[2], 'inventory': pages}


def probe_disk(out, state, module, driver, extra=()):
    (out / 'state.bin').write_bytes(state)
    (out / 'module.bin').write_bytes(module)
    (out / 'driver.bin').write_bytes(driver)
    lines = ['10 PRINT CHR$(4);"BLOAD STATE"', '20 PRINT CHR$(4);"BLOAD MODULE"']
    args = ['--bin', f'STATE={out / "state.bin"}@0x4000', '--bin', f'MODULE={out / "module.bin"}@0x5800',
            '--bin', f'DRIVER={out / "driver.bin"}@0x0800']
    for k, (name, data, addr) in enumerate(extra):
        (out / f'{name.lower()}.bin').write_bytes(data)
        lines.append(f'{30 + k} PRINT CHR$(4);"BLOAD {name}"')
        args += ['--bin', f'{name}={out / (name.lower() + ".bin")}@0x{addr:04X}']
    lines.append('90 PRINT CHR$(4);"BRUN DRIVER"')
    (out / 'hello.bas').write_text('\n'.join(lines) + '\n')
    disk = out / 'probe.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'), '--out', str(disk),
                    '--bas', f'HELLO={out / "hello.bas"}', *args], check=True, capture_output=True)
    return disk


def accepted(row, e):
    """T0A/S00 $5A50-$5A98, 8-bit: d = |e - c| (two's complement), a = |w|."""
    for (c, w), v in zip(row, e):
        d = (v - c) & 255
        if d & 0x80:
            d = (-d) & 255
        a = (-w) & 255 if w < 0 else w
        if a >= d:          # inside |w|
            if w <= 0:
                return False
        elif w > 0:
            return False
    return True


def table_rows(state):
    raw = state[0x48B4 - 0x4000:0x48B4 - 0x4000 + 13 * 12]
    return [[(raw[12 * t + 2 * i], regions.signed(raw[12 * t + 2 * i + 1])) for i in range(6)]
            for t in range(13)]


def filter_cases(rows, climate, types):
    """Both sides of every bound of every dimension, from a passing base."""
    domain = ((0, 100), (0, 23), (0, 40), (0, 160), (0, 125), (0, 160))
    cases = []
    for t in types:
        row = rows[t - 1]
        base = []
        for i, (c, w) in enumerate(row):
            lo, hi = domain[i]
            if i == 2:
                choices = [v for v in (0, 10, 20, 30, 40) if accepted([(c, w)], [v])]
            elif i == 5:
                choices = [climate] if accepted([(c, w)], [climate]) else \
                    [v for v in range(lo, hi + 1) if accepted([(c, w)], [v])]
            else:
                choices = [v for v in range(lo, hi + 1) if accepted([(c, w)], [v])]
            base.append(choices[len(choices) // 2] if choices else c)
        for i, (c, w) in enumerate(row):
            a = abs(w)
            values = {0, c, c - a - 1, c - a, c + a, c + a + 1, domain[i][1]}
            if i == 2:
                values |= {0, 10, 20, 30, 40}
            if i == 5:
                values.add(climate)
            for v in sorted(x for x in values if 0 <= x <= 255):
                env = list(base)
                env[i] = v
                cases.append((t, env, accepted(row, env)))
    return cases


def run_filters(out, state, module0, rows, climate, types):
    module = bytearray(module0)
    module[0x2A3:0x2AB] = bytes.fromhex('A5 FD 8D 00 09 4C 9A 5A')
    disk = probe_disk(out, state, module, bytes.fromhex('A2 01 A0 02 20 2F 5A 4C 00 08'))
    cases = filter_cases(rows, climate, types)
    steps = ['until:0800:20000', 'poke:000A:00', 'poke:4B75:00']
    for t, env, _ in cases:
        steps += [f'poke:0801:{t:02X}', f'poke:0803:{t + 1:02X}', 'poke:0900:00']
        steps += [f'poke:{0x4ADA + i:04X}:{v:02X}' for i, v in enumerate(env)]
        steps += ['until:0807:1000', 'peek:0900:1', 'until:0800:1000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=1800)
    assert len(r.dumps) == len(cases)
    bad = [(t, env, exp, bool(d[0])) for (t, env, exp), d in zip(cases, r.dumps) if bool(d[0]) != exp]
    assert not bad, bad[:5]
    return len(cases)


def run_probability(out, state, module0, slots, rates):
    """Probability recorded at $5B46 before RND; water gate of byte 29."""
    module = bytearray(module0)
    module[0x346:0x34E] = bytes.fromhex('A2 A0 A0 09 20 2B EB 60')
    disk = probe_disk(out, state, module, bytes.fromhex('20 A3 5A 4C 00 08'))
    cases = []
    for slot in slots:
        for level, freq, minutes in ((4, 1, 60), (1, 1, 1), (10, 5, 255)):
            for terrain, shore in ((0, 0), (3, 0), (3, 1), (3, 3), (4, 0), (4, 2)):
                cases.append((slot, level, freq, minutes, terrain, shore))
    steps = ['until:0800:20000']
    for slot, level, freq, minutes, terrain, shore in cases:
        steps += [f'poke:00FD:{slot:02X}', f'poke:00FC:{slot + 1:02X}', f'poke:603F:{level:02X}',
                  f'poke:4BC6:{minutes:02X}', 'poke:4BC7:00', f'poke:4B56:{terrain:02X}',
                  f'poke:4B6B:{shore:02X}'] + [f'poke:{0x9A0 + i:04X}:00' for i in range(5)]
        steps += [f'poke:{0x4C4D + i:04X}:{v:02X}' for i, v in enumerate(encode(freq))]
        steps += ['until:0803:1000', 'peek:09A0:5', 'until:0800:1000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=1800)
    assert len(r.dumps) == len(cases)
    rows = []
    for (slot, level, freq, minutes, terrain, shore), d in zip(cases, r.dumps):
        got = mbf(d) if d[0] else None
        gate = rates[slot]['water_gate'] and terrain >= 3 and shore in (0, 3)
        expected = None if gate else minutes * freq * math.sqrt(level) * rates[slot]['rate'] * 1e-5
        ok = (got is None) == (expected is None) and (
            got is None or abs(got - expected) < max(1e-8, expected * 1e-8))
        assert ok, (slot, level, freq, minutes, terrain, shore, got, expected)
        rows.append(dict(slot=slot, level=level, frequency=freq, minutes=minutes,
                         terrain=terrain, shore=shore, probability=got))
    return rows


def run_reactions(out, state0, disk_j, species):
    """Thresholds of T0F/S07 and T06/S04, as re_animal_reactions_probe."""
    state = bytearray(state0)
    state[0xD2A] = 0x60   # $4D2A: no numbered messages
    rows = []
    slots = [s['slot'] for s in species]
    for name, track, sector, count, entry, stop, value in (
            ('noise', 15, 7, 6, 0x586E, 0x5898, 0x5C0B),
            ('injury', 6, 4, 6, 0x5800, 0x58C5, 0x98),
            ('posture', 6, 4, 6, 0x584A, 0x58C5, 0x98),
            ('defence', 6, 4, 6, 0x593A, 0x5968, 0xFB),
            ('theft', 6, 4, 6, 0x5A94, 0x5AC8, 0xFB)):
        module = bytearray(disk_j.run(track, sector, count))
        module[stop - 0x5800:stop - 0x5800 + 3] = bytes.fromhex('4C 03 08')
        disk = probe_disk(out, state, module, bytes((0x4C, entry & 255, entry >> 8, 0x4C, 0, 8)))
        if name == 'posture':
            cases = [(s, 16 if tree else (13 if command < 22 else 15), 0, tree, cover, command)
                     for s in slots for command in (20, 37) for tree in (0, 1) for cover in (0, 1)]
        elif name == 'theft':
            # $5A94 first tests record[28]; a species that never steals
            # leaves before the threshold (and would wait at a prompt).
            cases = [(s['slot'], 15, hung, tree, 0, 17) for s in species if s['theft']
                     for hung, tree in ((0, 0), (1, 0), (0, 1))]
            if not cases:
                continue
        elif name == 'injury':
            cases = [(s, tool, 0, 0, 0, 17) for s in slots for tool in (14, 15, 17, 18, 19, 20, 21)]
        elif name == 'defence':
            cases = [(s, tool, 0, 0, 0, 17) for s in slots for tool in (17, 18, 19, 20, 21)]
        else:
            cases = [(s, 15, 0, 0, 0, 17) for s in slots]
        steps = ['until:0800:20000']
        for s, tool, hung, tree, cover, command in cases:
            steps += [f'poke:0005:{s + 75:02X}', f'poke:0015:{s:02X}', f'poke:0004:{tool:02X}',
                      'poke:0019:02', f'poke:0003:{command:02X}', 'poke:0D5D:00', f'poke:0D5E:{cover:02X}',
                      'poke:0018:00', f'poke:4B71:{int(name == "posture"):02X}', 'poke:4B59:00',
                      'poke:00F6:81', 'poke:00F7:00', 'poke:00F8:00', 'poke:00F9:00', 'poke:00FA:00',
                      f'poke:4B40:{tree:02X}', f'poke:4B46:{tree:02X}', f'poke:4B4E:{hung:02X}',
                      'until:0803:2000', f'peek:{value:04X}:5', 'until:0800:1000']
        r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=1800)
        assert len(r.dumps) == len(cases), (name, len(r.dumps), len(cases))
        for (s, tool, hung, tree, cover, command), d in zip(cases, r.dumps):
            rows.append(dict(rule=name, slot=s, method=tool, hung=hung, tree=tree, cover=cover,
                             command=command, threshold=mbf(d)))
    return rows


def expected_threshold(row, rec):
    s, m = row['slot'], row['method']
    if row['rule'] == 'noise':
        return .8 - .03 * rec[14]
    if row['rule'] == 'injury':
        return .02 * rec[m]
    if row['rule'] == 'posture':
        return .02 * rec[m] * (.1 if row['cover'] else 1)
    if row['rule'] == 'defence':
        return .005 * rec[m + 6]
    return .01 if row['hung'] else (.1 if row['tree'] else .05)


def run_trinkets(out, state0, disk_j):
    """New Guinea, slot 1 (cannibal): T06/S04 $58DA-$5912 after the injury roll.

    RND ($0321) returns a fixed float. The injury branch $5912 (it would
    print message $45) is replaced by $4B7A = 1 and a stop; the no-injury
    branch $592A stops with $4B7A unchanged.
    """
    state = bytearray(state0)
    state[0xD2A] = 0x60
    module = bytearray(disk_j.run(6, 4, 6))
    module[0x112:0x11A] = bytes.fromhex('A9 01 8D 7A 4B 4C 03 08')   # $5912
    module[0x12A:0x12D] = bytes.fromhex('4C 03 08')   # $592A
    driver = bytearray(0x45)
    driver[:6] = bytes.fromhex('4C 00 58 4C 00 08')
    driver[0x20:0x28] = bytes.fromhex('A9 40 A0 08 20 F9 EA 60')
    disk = probe_disk(out, state, module, bytes(driver))
    cases = [(region, trinkets, rnd) for region in (4, 3) for trinkets in (0, 1) for rnd in (.01, .5)]
    steps = ['until:0800:20000', 'poke:0321:4C', 'poke:0322:20', 'poke:0323:08']
    for region, trinkets, rnd in cases:
        m, e = math.frexp(rnd)
        packed = bytes((e + 128,)) + ((round(m * 2 ** 32) & 0x7FFFFFFF).to_bytes(4, 'big'))
        steps += [f'poke:601F:{region:02X}', f'poke:40E2:{trinkets:02X}', 'poke:0005:4C', 'poke:0015:01',
                  'poke:0004:12', 'poke:0019:02', 'poke:0003:11', 'poke:0D5D:00', 'poke:0D5E:00',
                  'poke:0018:00', 'poke:4B71:00', 'poke:4B59:00', 'poke:4B40:00', 'poke:4B46:00',
                  'poke:4B56:00', 'poke:4B7A:00']
        steps += [f'poke:{0x840 + i:04X}:{b:02X}' for i, b in enumerate(packed)]
        steps += ['until:0803:2000', 'peek:4B7A:1', 'until:0800:1000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    assert len(r.dumps) == len(cases)
    return [dict(region=g, trinkets=t, rnd=v, injured=d[0]) for (g, t, v), d in zip(cases, r.dumps)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    headers = regions.read_headers(HERE / 'build/SIERRA.dsk')
    dj = smalldos.Disk((HERE / 'build/JOURNEY.dsk').read_bytes())
    dj.flip = True
    t0as00 = bytes(dj.run(0x0A, 0, 5))
    report = {'method': __doc__.split('\n\n')[1], 'answers': ANSWERS, 'regions': {}}
    starts = {}
    control = journey([])
    (OUT / 'r2_unpatched.bin').write_bytes(control['ram'])
    for r in range(1, 7):
        j = journey(patch(r, headers[r]))
        (OUT / f'r{r}_start.bin').write_bytes(j['ram'])
        starts[r] = j
        print(f'r{r}: journey start captured')
    if starts[2]['ram'][0x4000:0xC000] != control['ram'][0x4000:0xC000]:
        diff = [hex(a) for a in range(0x4000, 0xC000) if starts[2]['ram'][a] != control['ram'][a]]
        sys.exit(f'patched Sierra differs from the original journey at {diff[:20]}')
    sierra = starts[2]['ram']
    for r, j in starts.items():
        ram = j['ram']
        state = bytes(ram[STATE[0]:STATE[1]])
        h = headers[r]
        species = [s for s in regions.species(h) if s['rate']]
        rows = table_rows(state)
        for s in regions.species(h):
            got = state[0x48B4 - 0x4000 + 12 * (s['slot'] - 1):][:12]
            assert got == h[32 * (s['slot'] - 1):32 * (s['slot'] - 1) + 12], (r, s['slot'])
        out = OUT / f'r{r}'
        out.mkdir(exist_ok=True)
        climate = h[0xBA]
        nf = run_filters(out, state, t0as00, rows, climate, range(1, 14))
        prob = run_probability(out, state, t0as00, [s['slot'] for s in species],
                               {s['slot']: s for s in regions.species(h)})
        reactions = run_reactions(out, state, dj, species)
        for row in reactions:
            rec = h[32 * (row['slot'] - 1):32 * row['slot']]
            row['expected'] = expected_threshold(row, rec)
            assert abs(row['threshold'] - row['expected']) < 1e-8, (r, row)
        items = [a for a in range(0x4000, 0x4800) if ram[a] != sierra[a]]
        report['regions'][str(r)] = {
            'intro': j['intro'], 'inventory': j['inventory'],
            'latitude': regions.signed(ram[0x60A8]), 'declination': regions.signed(ram[0x60A9]),
            'january_temperature': regions.signed(ram[0x4BB0]), 'july_temperature': regions.signed(ram[0x4BB1]),
            'resource_rows': {str(t): rows[t - 1] for t in range(5, 14)},
            'filter_cases': nf, 'probability_cases': len(prob), 'reaction_cases': len(reactions),
            'item_bytes_differing_from_sierra': [f'${a:04X}' for a in items],
            'state_bytes_differing_from_sierra': sum(ram[a] != sierra[a] for a in range(0x4000, 0x4D00)),
        }
        (out / 'probability.json').write_text(json.dumps(prob, indent=1) + '\n')
        (out / 'reactions.json').write_text(json.dumps(reactions, indent=1) + '\n')
        line = regions.snowline(regions.signed(ram[0x60A8]), mbf(ram[0x4C89:0x4C8E]))
        assert line == ram[0x4C0A] | ram[0x4C0B] << 8, (r, line)
        assert ram[0xE8] == (line - ram[0x60A1]) // 2, (r, ram[0xE8])
        report['regions'][str(r)]['snowline'] = line
        t = regions.go2_temperatures(regions.signed(ram[0x60A8]))
        assert t == (ram[0x4BB0], ram[0x4BB1]), (r, t, ram[0x4BB0], ram[0x4BB1])
        print(f'r{r}: {nf} filter, {len(prob)} probability, {len(reactions)} reaction cases OK;'
              f' $4000-$47FF bytes unlike the Sierra: {len(items)}')
    (OUT / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    trinkets = run_trinkets(OUT / 'r4', bytes(starts[4]['ram'][STATE[0]:STATE[1]]), dj)
    for row in trinkets:
        expect = 1 if row['region'] != 4 or not row['trinkets'] or row['rnd'] < .02 else 0
        assert row['injured'] == expect, row
    report['trinkets'] = trinkets
    report['wreck'] = wreck(starts)
    (OUT / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    fauna = {'source': 'tools/re_region_fauna_probe.py (original code on a2shot)',
             'filter_rule': 'd = |e - c| and a = |w| in 8 bits; w > 0 needs d <= a, w < 0 needs d > a, w = 0 needs d > 0',
             'probability': 'minutes x frequency x sqrt(level) x rate x 1e-5, skipped when water_gate and terrain >= 3 and shore in (0, 3)',
             'thresholds': {'noise': '.8 - .03 x injury[14]', 'injury': '.02 x injury[method]',
                            'shelter': 'x .1', 'success': '.005 x success[method]',
                            'theft': '.05 outside, .01 hung, .10 in a tree, only if theft != 0',
                            'severity': 'INT(1 + 5 x RND ^ severity_exponent)',
                            'trinkets': 'New Guinea slot 1: with TRINKETS an injury needs RND < .02'},
             'regions': {}}
    for r in range(1, 7):
        h = headers[r]
        fauna['regions'][str(r)] = {
            'name': regions.NAMES[r], 'climate_index': h[0xBA],
            'species': [dict(s, sprite=regions.SPRITE_ORDER[a - 1] if a else None)
                        for s, a in zip(regions.species(h), sprite_ids(r)) if s['rate']],
            'resource_rows': report['regions'][str(r)]['resource_rows'],
        }
    (HERE / 'build/regions').mkdir(parents=True, exist_ok=True)
    (HERE / 'build/regions/fauna.json').write_text(json.dumps(fauna, indent=1) + '\n')
    print(f'trinkets: {len(trinkets)} cases OK; build/regions/fauna.json written')


def wreck(starts):
    """Is the wreck inventory a region table or a random draw?

    The item location table ($404C, one byte per item: $FF ground, 1 worn,
    0 absent) is compared between the region starts, then the Sierra is
    rerun with only the region byte changed, and with only the latitude
    changed to -21 (no Chile data at all).
    """
    table = lambda ram: bytes(ram[0x404C:0x4098])
    sierra = table(starts[2]['ram'])
    rows = {str(r): table(j['ram']) == sierra for r, j in starts.items()}
    region_only = {}
    for r in (1, 3, 4, 5, 6):
        region_only[str(r)] = table(journey([(0x601F, r)])['ram']) == sierra
    lat = journey([(0x60A8, (-21) & 255)])
    result = {'same_kit_as_sierra': rows, 'region_byte_only_same_kit': region_only,
              'sierra_latitude_-21_gives_chile_kit': table(lat['ram']) == table(starts[6]['ram']),
              'sierra_latitude_-21_date': lat['intro'][0][11],
              'items_present': {str(r): sum(b != 0 for b in table(j['ram'])) for r, j in starts.items()}}
    assert all(region_only.values()), region_only
    assert result['sierra_latitude_-21_gives_chile_kit']
    return result


def sprite_ids(region):
    """Global animal ids of the four slots (= .CIM id byte, sprite order)."""
    return {1: (1, 2, 3, 0), 2: (4, 5, 6, 0), 3: (7, 8, 9, 10), 4: (11, 12, 13, 0),
            5: (14, 15, 16, 17), 6: (14, 18, 0, 0)}[region]


if __name__ == '__main__':
    main()
