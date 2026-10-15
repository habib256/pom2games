#!/usr/bin/env python3
"""Resident fine geography (lot 5): exact queries, tile cache, no disk access.

Native maps carry the 224 x 168 fine geography as a compressed atlas in the
auxiliary language card (src/geoaux.s, tools/geo_atlas.atlas_bytes). Checks:

* build_disk.py places code + atlas and refuses an atlas over the budget;
* every cell of a generated native map (mkmap --native) is returned exactly
  by the real cell_native: level, water, river/lake bit and woodland
  (tests/test_geography.py does the same against the Sierra ROM samples);
* query and decode costs in guest cycles, every tile measured;
* the 4-tile LRU cache decodes exactly as the model of tools/geo_atlas.py
  along the modelled crash -> rangers routes (direct and meandering);
* real play from the crash toward the rangers (WALK, SWIM, SLEEP) and a
  water collection on a shore cell where four tiles meet: zero MLI call
  (counters and an a2shot watch on $BF00), decodes counted per command;
* a legacy map (the default disk) never queries the fine geography;
* TOPO on a native map keeps the atlas: the snapshot of the view, which
  shares the language card with it on legacy maps, is not taken there
  (src/topo_dhgr.s tp_save), and queries stay exact afterwards.

The Sierra comparison map is used when the local original data exist
(build/files/TOPO.B, build/re_geography, build/game.bin); the generated
native map always runs. `--measure` prints the cost of every tile.
"""
import math
import sys
import tempfile
from pathlib import Path

from common import HERE, L, DISK, a2test, disk_with, text_screen
import build_disk
import geo_atlas
import mkmap

LIMIT = 40000
IDLE = L.until('idle', LIMIT)
COUNTERS = (('mli_calls', 2), ('geo_decodes', 2), ('geo_queries', 3))
ROWS, COLS, OUT, WOOD, KIND = 0x2000, 0x2100, 0x2200, 0x2300, 0x2400


def have_sierra():
    return all((HERE / p).exists() for p in ('build/files/TOPO.B', 'build/re_geography/heights.bin',
                                             'build/re_geography/types.bin', 'build/game.bin'))


def generated_native(seed=1985, level=4):
    """mkmap --native: header byte 37 set, fine geography appended."""
    m = mkmap.Map(seed, level)
    head = mkmap.heading_to(*m.start, mkmap.W // 2, mkmap.H // 2)
    data = bytearray(mkmap.map_bin(m.h, m.water, m.start, m.goal, head, level, woods=m.forest))
    data[37] = 1
    return bytes(data + mkmap.fine_bytes(m.h, m.water, m.forest, m.lake)), m.start, m.goal


def patchy_native(level=10, tiles=(0, 153)):
    """mkmap seed 1985 (level 10: 2 417 lake cells) with tiles of uniform
    noise (by default the first one and one in the 8-row last tile row):
    those are stored raw, the others coded; the resident grid is rebuilt
    from the patched fine cells. Six tiles until lot 7 (docs/ORIENTATION.md):
    with its trunk the 140 KB volume holds the level-10 atlas and one raw
    tile (two until the STATUS pages of 14 October 2026). The bootable variant (level 4, tiles 0 and 153) keeps a first and
    a last raw tile within the 280 blocks of the volume (lot 13)."""
    mapdata, start, goal = generated_native(1985, level)
    data = bytearray(mapdata)
    fine = mkmap.MAP_BYTES + mkmap.FOREST_BYTES
    rnd = __import__('random').Random(5)
    for tile in tiles:
        x0, y0 = (tile % 14) * 16, (tile // 14) * 16
        for y in range(y0, min(y0 + 16, 168)):
            for x in range(x0, x0 + 16):
                water = rnd.random() < .2
                data[fine + y * 224 + x] = (0x80 | rnd.randrange(64) | (0x40 if rnd.random() < .5 else 0)
                                            if water else rnd.randrange(126))
            for k in range(2):
                data[fine + 224 * 168 + y * 28 + x0 // 8 + k] = rnd.randrange(256)
    cells = bytes(data[fine:fine + 224 * 168])
    woods = bytes(data[fine + 224 * 168:])
    data[64:mkmap.MAP_BYTES] = geo_atlas.Fine('patchy', cells, woods, start, goal, True).coarse()
    data[21] = 1 + max(v & 0x7F for v in data[64:mkmap.MAP_BYTES])
    return bytes(data)


def native_maps():
    out = [('generated s1985-L4',) + generated_native()]
    if have_sierra():
        from test_adventure import original_map
        raw = (HERE / 'build/files/TOPO.B').read_bytes()
        start, goal = geo_atlas.topo_ends(raw)
        out.append(('Sierra', original_map(), start, goal))
    return out


def fine_of(mapdata):
    fine = mapdata[mkmap.MAP_BYTES + mkmap.FOREST_BYTES:]
    return fine[:224 * 168], fine[224 * 168:]


# scene_asset of the site sprites (src/project.s): blocks of the raw image.
SITE_BLOCKS = {33: 3, 34: 3, 35: 5}


def counters(s):
    return {n: int.from_bytes(s.step(L.peek(n, k)).data, 'little') for n, k in COUNTERS}


def delta(after, before):
    return {k: after[k] - before[k] for k in after}


# ------------------------------------------------------------------ harnesses
# Both replace the idle loop (the game never returns there) and stop on their
# final JMP, like tests/test_geography.py.

def row_harness(start):
    """X = poked row; Y = 0..223 -> $2200/$2300/$2400 (cell, woods, kind)."""
    code = bytearray((0xA0, 0, 0xA2, 0))                           # LDY #0, LDX #row
    loop = start + len(code)
    code += bytes((0x8C, (start + 60) & 255, (start + 60) >> 8,     # STY col
                   0x20, L['cell_native'] & 255, L['cell_native'] >> 8,
                   0xAC, (start + 60) & 255, (start + 60) >> 8,     # LDY col
                   0x99, OUT & 255, OUT >> 8,
                   0xAD, L['geo_wooded'] & 255, L['geo_wooded'] >> 8,
                   0x99, WOOD & 255, WOOD >> 8,
                   0xAD, L['geo_water_kind'] & 255, L['geo_water_kind'] >> 8,
                   0x99, KIND & 255, KIND >> 8,
                   0xAE, (start + 3) & 255, (start + 3) >> 8,       # LDX row (operand)
                   0xC8, 0xC0, 224))                                # INY, CPY #224
    code += bytes((0xD0, (loop - (start + len(code) + 2)) & 255))
    stop = start + len(code)
    code += bytes((0x4C, start & 255, start >> 8))
    assert len(code) <= 60
    return code, stop


def list_harness(start, target=None):
    """Queries ($2000+i, $2100+i) for i < count -> $2200+i (count 0 = 256)."""
    target = L['cell_native'] if target is None else target
    idx, cnt = start + 62, start + 63
    code = bytearray((0xA9, 0, 0x8D, idx & 255, idx >> 8))          # LDA #0, STA idx
    loop = start + len(code)
    code += bytes((0xAC, idx & 255, idx >> 8,
                   0xB9, ROWS & 255, ROWS >> 8, 0xAA,
                   0xB9, COLS & 255, COLS >> 8, 0xA8,
                   0x20, target & 255, target >> 8,
                   0xAC, idx & 255, idx >> 8,
                   0x99, OUT & 255, OUT >> 8,
                   0xEE, idx & 255, idx >> 8,
                   0xAD, idx & 255, idx >> 8,
                   0xCD, cnt & 255, cnt >> 8))
    code += bytes((0xD0, (loop - (start + len(code) + 2)) & 255))
    stop = start + len(code)
    code += bytes((0x4C, start & 255, start >> 8))
    assert len(code) <= 61
    return code, stop, cnt


class Harness:
    def __init__(self, session, kind='list'):
        self.s, self.start = session, L['idle']
        if kind == 'list':
            code, self.stop, self.cnt = list_harness(self.start)
            code += bytes((0x60,))                                  # RTS at start+61
            self.empty = self.start + len(code) - 1
        else:
            code, self.stop = row_harness(self.start)
        for i, v in enumerate(code):
            self.s.step(f'poke:{self.start + i:04X}:{v:02X}')
        self.target = L['cell_native']

    def run(self, queries):
        """[(row, col)] (<= 256) -> (cells, guest cycles of the batch)."""
        assert 0 < len(queries) <= 256
        for i, (row, col) in enumerate(queries):
            self.s.step(f'poke:{ROWS + i:04X}:{row:02X}')
            self.s.step(f'poke:{COLS + i:04X}:{col:02X}')
        self.s.step(f'poke:{self.cnt:04X}:{len(queries) & 255:02X}')
        begin = self.s.step(f'until:{self.start:04X}:{LIMIT}').cycles[-1]
        end = self.s.step(f'until:{self.stop:04X}:{LIMIT}').cycles[-1]
        cells = self.s.step(f'peek:{OUT:04X}:{len(queries)}').data
        return cells, end - begin

    def call_target(self, target):
        """Point the JSR at `target` (cell_native, or the RTS of the harness)."""
        jsr = self.start + 5 + 11
        self.s.step(f'poke:{jsr + 1:04X}:{target & 255:02X}')
        self.s.step(f'poke:{jsr + 2:04X}:{target >> 8:02X}')

    def many(self, queries):
        cells = b''
        for k in range(0, len(queries), 256):
            cells += self.run(queries[k:k + 256])[0]
        return cells


def session(disk):
    s = a2test.Session(disk, timeout=1800)
    s.__enter__()
    s.step(IDLE)
    s.step(L.poke('nature_frequency', 0))
    return s


# ------------------------------------------------------------------ checks

def check_build(maps):
    for name, mapdata, *_ in maps:
        cells, woods = fine_of(mapdata)
        stats = {}
        atlas = geo_atlas.atlas_bytes(cells, woods, mapdata[64:mkmap.MAP_BYTES], L['geo_atlas'], stats)
        assert geo_atlas.atlas_decode(atlas, L['geo_atlas'], mapdata[64:mkmap.MAP_BYTES]) == (cells, woods)
        budget = geo_atlas.ATLAS_END - L['geo_atlas']
        print(f'  {name}: atlas {len(atlas)} bytes (index {stats["index"]}, worst tile '
              f'{stats["worst"]}, {stats["raw_tiles"]} raw), budget {budget}, free {budget - len(atlas)}')
    # The guard: incompressible fine data (its own coarse grid) is refused.
    base = bytearray((HERE / 'build/map.bin').read_bytes()[:mkmap.MAP_BYTES + mkmap.FOREST_BYTES])
    rough = geo_atlas.noise(1)
    noise = geo_atlas.Fine('noise', bytes(c & 0xBF for c in rough.cells), rough.woods,
                           rough.start, rough.goal, True)
    base[37] = 1
    base[64:mkmap.MAP_BYTES] = noise.coarse()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'noise.bin'
        path.write_bytes(bytes(base) + noise.cells + noise.woods)
        try:
            build_disk.build_disk(Path(tmp) / 'noise.po', path)
        except SystemExit as refused:
            assert 'too large' in str(refused), refused
            print(f'  noise map refused: {refused}')
        else:
            raise AssertionError('an atlas over the budget was accepted')


def check_exact(name, mapdata):
    cells, woods = fine_of(mapdata)
    with tempfile.TemporaryDirectory() as tmp:
        s = session(disk_with(tmp, mapdata))
        try:
            h = Harness(s, 'row')
            before = counters(s)
            for y in range(168):
                s.step(f'poke:{h.start + 3:04X}:{y:02X}')
                s.step(f'until:{h.stop:04X}:{LIMIT}')
                got = s.step(f'peek:{OUT:04X}:224').data
                wood = s.step(f'peek:{WOOD:04X}:224').data
                kind = s.step(f'peek:{KIND:04X}:224').data
                s.step(f'until:{h.start:04X}:{LIMIT}')
                for x in range(224):
                    c = cells[y * 224 + x]
                    expected = c & 0xBF if c & 0x80 else c
                    assert got[x] == expected, (name, 'cell', x, y, got[x], c)
                    assert bool(wood[x]) == bool(woods[y * 28 + x // 8] >> (x % 8) & 1), (name, 'woods', x, y)
                    if c & 0x80:
                        assert kind[x] == c & 0x40, (name, 'river/lake', x, y)
            after = delta(counters(s), before)
        finally:
            s.__exit__(None, None, None)
    assert after['mli_calls'] == 0 and after['geo_queries'] == 168 * 224
    print(f'  {name}: 37632 cells exact (level, water, river/lake, woodland), '
          f'{after["geo_decodes"]} tiles decoded row by row, no MLI call')


SWITCHES = 'C011 C012 C013 C014 C016 C018 C01C'.split()   # LC bank/RAM, RAMRD/WRT, ALTZP, 80STORE, PAGE2


def machine_state(s):
    """Soft switches, main zero page, auxiliary $0200-$03FF (/RAM driver)."""
    switches = [s.step(f'peek:{a}').data[0] >> 7 for a in SWITCHES]
    zero = s.step('peek:0000:256').data
    s.step('poke:C003:00')                                  # RAMRD on: read aux
    driver = s.step('peek:0200:512').data
    s.step('poke:C002:00')
    return switches, zero, driver


def check_costs(name, mapdata, every_tile=False):
    with tempfile.TemporaryDirectory() as tmp:
        s = session(disk_with(tmp, mapdata))
        try:
            h = Harness(s)
            state = machine_state(s)
            # Harness overhead: the same batch with the JSR on an RTS.
            h.call_target(h.empty)
            _, empty1 = h.run([(0, 0)])
            _, empty4 = h.run([(0, 0)] * 4)
            h.call_target(L['cell_native'])
            tiles = [(y0, x0) for y0 in range(0, 168, 16) for x0 in range(0, 224, 16)]
            chosen = tiles if every_tile else tiles[::7]
            miss = []
            for row, col in chosen:
                before = counters(s)['geo_decodes']
                _, cycles = h.run([(row, col)])
                if counters(s)['geo_decodes'] == before + 1:   # not cached at boot
                    miss.append(cycles - empty1 + 12)
            row, col = chosen[-1]
            _, mru = h.run([(row, col)] * 4)
            mru = (mru - empty4) / 4 + 12
            # Four tiles in cache: query the least recent one (a hit, moved front).
            for r, c in chosen[-4:]:
                h.run([(r, c)])
            before = counters(s)['geo_decodes']
            _, other = h.run([chosen[-4]])
            assert counters(s)['geo_decodes'] == before
            other = other - empty1 + 12
            after = machine_state(s)
            assert after[0] == state[0], ('soft switches', state[0], after[0])
            assert after[1] == state[1], 'main zero page changed'
            assert after[2] == state[2], 'auxiliary $0200-$03FF (/RAM driver) changed'
        finally:
            s.__exit__(None, None, None)
    hit = mru
    print(f'  {name}: query {hit:.0f} cycles (same tile), {other} (other cached tile), '
          f'miss {min(miss)}-{max(miss)} cycles (mean {sum(miss) / len(miss):.0f}, '
          f'{len(miss)} tiles{", all" if every_tile else ""}), '
          f'worst {max(miss) / a2test.CPU_HZ * 1000:.1f} ms; soft switches, main zero page '
          f'and auxiliary $0200-$03FF unchanged')
    assert hit < 250 and other < 400 and max(miss) < 60000, (hit, other, max(miss))
    return dict(hit=hit, other=other, miss_min=min(miss), miss_max=max(miss),
                miss_mean=sum(miss) / len(miss))


def route_queries(path):
    """tools/geo_atlas.simulate's order: the 3 x 3 around here, then next."""
    out = []
    for here, nxt in zip(path, path[1:]):
        out += [(j, i) for i, j in geo_atlas.neighbourhood(*here)] + [(nxt[1], nxt[0])]
    return out


def check_routes(name, mapdata, start, goal):
    fine = geo_atlas.Fine(name, *fine_of(mapdata), start, goal, True)
    paths = geo_atlas.routes(fine)
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        s = session(disk_with(tmp, mapdata))
        try:
            h = Harness(s)
            for route in ('direct', 'meander'):
                path = paths[route]
                touched = {geo_atlas.block_index('tile16', x, y) for p in path
                           for x, y in geo_atlas.neighbourhood(*p)}
                # Flush the cache with four tiles the route never touches.
                far = [k for k in range(154) if k not in touched][:4]
                for k in far:
                    h.run([((k // 14) * 16, (k % 14) * 16)])
                queries = route_queries(path)
                before = counters(s)
                h.many(queries)
                got = delta(counters(s), before)
                model = geo_atlas.simulate('tile16', path, 4)[0]
                assert got['mli_calls'] == 0 and got['geo_queries'] == len(queries)
                assert got['geo_decodes'] == model, (name, route, got, model)
                results[route] = (len(path) - 1, len(touched), got['geo_decodes'])
                print(f'  {name} {route}: {len(path) - 1} half-steps, {len(queries)} queries, '
                      f'{got["geo_decodes"]} decodes (model {model}, {len(touched)} tiles touched)')
        finally:
            s.__exit__(None, None, None)
    return results


def command(s, text, answers=()):
    """Type a command; answer numeric prompts, acknowledge messages."""
    s.step('key:' + text)
    s.step('press:\\r')
    s.step('wait:1')
    answers = list(answers)
    lines = []
    for _ in range(20):
        r = s.step(f'until:{L["idle"]:04X},{L["wait_key"]:04X},{L["number_idle"]:04X}:{LIMIT}')
        lines.append(' / '.join(text_screen(s.step('peek:0400:1024').data)[20:]))
        pc = r.out.rstrip()[-4:]
        if pc == f'{L["idle"]:04X}':
            break
        if pc == f'{L["number_idle"]:04X}' and answers:
            s.step('key:' + answers.pop(0) + '\r')
            continue
        s.step('press: ')
        s.step('wait:1')
    return ' // '.join(lines)


def position(s):
    d = s.step(L.peek('px', 4)).data
    return int.from_bytes(d[0:2], 'little') / 128, int.from_bytes(d[2:4], 'little') / 128


def set_position(s, x, y):
    for name, v in (('px', round(x * 128)), ('py', round(y * 128))):
        s.step(L.poke(name, v & 255))
        s.step(L.poke(name, v >> 8, 1))


def shore_corner(cells):
    """A water cell next to land whose 3 x 3 spans four tiles."""
    def water(x, y):
        return cells[y * 224 + x] & 0x80
    for y in range(17, 160):
        for x in range(17, 207):
            near = geo_atlas.neighbourhood(x, y)
            if (water(x, y) and any(not water(i, j) for i, j in near)
                    and len({geo_atlas.block_index('tile16', i, j) for i, j in near}) == 4):
                return x, y
    raise AssertionError('no shore cell at a tile corner')


def check_play(name, mapdata, start, goal, legs=60):
    cells, _ = fine_of(mapdata)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        s = session(disk_with(tmp, mapdata))
        try:
            # Lot 4 (docs/MEMORY.md 16): a comparison disk whose atlas leaves
            # too little store reads CAMP from NEOWILD.BLK (tools/build_disk.py):
            # FILL CANTEEN then makes its READ_BLOCK calls, nothing else does.
            camp = s.step(L.peek('module_dir', 1, 4 * 7)).data[0] == 0x40
            camp_reads = -(-len((HERE / 'build/wildcamp.bin').read_bytes()) // 512) if camp else 0
            s.step('watch:BF00')
            watched = len(s.out)
            first = counters(s)
            visited = set()
            site_reads = []

            def run(text, answers=()):
                before = counters(s)
                x0, y0 = position(s)
                message = command(s, text, answers)
                x1, y1 = position(s)
                got = delta(counters(s), before)
                # Lot 6: a view showing a site sprite (the outpost near the
                # goal) reads its blocks once, when the SIM window lost it.
                site = SITE_BLOCKS.get(s.step(L.peek('scene_asset')).data[0], 0)
                extra = got['mli_calls'] - (camp_reads if text.startswith('FILL') else 0)
                assert extra in (0, site), (text, extra, site)
                site_reads.append(extra)
                visited.update(geo_atlas.block_index('tile16', int(x), int(y))
                               for x, y in ((x0, y0), (x1, y1)))
                rows.append((text, got, (x1, y1)))
                return message

            for _ in range(legs):
                x, y = position(s)
                if math.dist((x, y), goal) < 12:      # the ending would leave the game
                    break
                h = round(math.degrees(math.atan2(goal[0] - x, goal[1] - y)) % 360 * 560 / 360) % 560
                s.step(L.poke('heading', h & 255))
                s.step(L.poke('heading', h >> 8, 1))
                message = run('WALK 2 H')
                if 'USE SWIM' in message:
                    run('SWIM 30 MIN')
                if 'TOO DARK' in message:
                    run('SLEEP 10 H')
                    run('EAT CHEESE 4 OZ')
                    run('DRINK WATER 8 OZ')
            journey = delta(counters(s), first)
            journey_sites = sum(site_reads)
            reached = position(s)
            # Shore collection where four tiles meet: FILL (one query), then
            # REST (fauna's 3 x 3 around the player: four tiles).
            x, y = shore_corner(cells)
            set_position(s, x + .5, y + .5)
            shore_before = counters(s)
            run('DRINK WATER 16 OZ')
            fill = run('FILL CANTEEN', ('16',))
            run('REST 1 H')
            shore = delta(counters(s), shore_before)
            hits = s.out[watched:].count('watch BF00')
        finally:
            s.__exit__(None, None, None)
    walks = [r for r in rows if r[0].startswith(('WALK', 'SWIM'))]
    worst = max(r[1]['geo_decodes'] for r in rows)
    print(f'  {name}: crash {start} -> {tuple(round(v) for v in reached)} (rangers {goal}): '
          f'{len(rows) - 3} commands, {len(walks)} WALK/SWIM, {journey["geo_queries"]} queries, '
          f'{journey["geo_decodes"]} decodes for {len(visited)} tiles crossed, '
          f'at most {worst} per command')
    print(f'  {name}: shore cell ({x}, {y}) at a tile corner: {fill.split(" // ")[-1].strip()[:60]!r}; '
          f'{shore["geo_queries"]} queries, {shore["geo_decodes"]} decodes')
    sites = sum(site_reads)
    if sites:
        print(f'  {name}: site sprites read from NEOWILD.BLK: {sites} READ_BLOCK')
    assert hits == camp_reads + sites, f'{hits} ProDOS MLI entries during play ({camp_reads + sites} expected)'
    assert journey['mli_calls'] == journey_sites and shore['mli_calls'] == camp_reads + sites - journey_sites
    assert math.dist(reached, goal) < 40, ('journey stopped early', reached)
    assert worst <= 4 and shore['geo_decodes'] <= 4, rows
    assert journey['geo_decodes'] <= 2 * len(visited) + 4, (journey, len(visited))
    return dict(journey=journey, shore=shore, worst=worst, tiles=len(visited))


def check_topo(name, mapdata):
    """TOPO twice, then a sample of every tile queried: still exact."""
    cells, _ = fine_of(mapdata)
    with tempfile.TemporaryDirectory() as tmp:
        s = session(disk_with(tmp, mapdata))
        try:
            command(s, 'WALK 30 MIN')       # some tiles cached before TOPO
            for _ in range(2):
                s.step('key:TOPO')
                s.step('press:\\r')
                s.step(L.until('graphical_topo_key', LIMIT))
                s.step('press:\\e')
                s.step(IDLE)
            h = Harness(s)
            before = counters(s)
            queries = [(y, x) for y in range(0, 168, 5) for x in range(0, 224, 7)]
            got = h.many(queries)
            after = delta(counters(s), before)
        finally:
            s.__exit__(None, None, None)
    for (y, x), v in zip(queries, got):
        c = cells[y * 224 + x]
        assert v == (c & 0xBF if c & 0x80 else c), (name, 'cell after TOPO', x, y, v, c)
    assert after['mli_calls'] == 0
    print(f'  {name}: TOPO twice (no snapshot, view redrawn), then {len(queries)} queries over '
          f'every tile exact ({after["geo_decodes"]} decodes): atlas intact')


def check_legacy():
    s = session(DISK)
    try:
        before = counters(s)
        command(s, 'WALK 1 H')
        command(s, 'REST 1 H')
        got = delta(counters(s), before)
    finally:
        s.__exit__(None, None, None)
    assert got == dict(mli_calls=0, geo_decodes=0, geo_queries=0), got
    print('  legacy map (default disk): WALK/REST read the resident grid, no fine query')


def main():
    every_tile = '--measure' in sys.argv
    maps = native_maps()
    if len(maps) == 1:
        print('  (no local Sierra data: generated native map only)')
    # The STATUS pages (14 October 2026) took the room of the second raw
    # tile at level 10 (104 bytes short): one noise tile, the last row's.
    patchy = ('generated s1985-L10 + 1 noise tile', patchy_native(10, (153,)))
    check_build(maps + [patchy])
    check_legacy()
    check_exact(*maps[0][:2])
    # The six-tile stress map (atlas 8 108 bytes) no longer fits a 280-block
    # disk with the lot-13 modules: its decoding is checked on a lighter one.
    check_exact('generated s1985-L4 + 2 noise tiles', patchy_native(4, (0, 153)))
    check_topo(*maps[0][:2])
    for name, mapdata, start, goal in maps:
        check_costs(name, mapdata, every_tile)
        check_routes(name, mapdata, start, goal)
        check_play(name, mapdata, start, goal)
    print('Resident fine geography: OK')


if __name__ == '__main__':
    main()
