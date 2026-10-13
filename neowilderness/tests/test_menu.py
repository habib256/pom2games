#!/usr/bin/env python3
"""The start menu of NEOWILD.SYSTEM and the region packs (lot 7, steps 2-3).

For each of the six scenarios, chosen with the keyboard:
- the map of its pack is at $7000 with the region byte (+32), the level
  (+22) and the journey kind (+33); the region texts at REGIONTEXT;
- the module directory is the one of tools/build_disk.py for this pack, and
  every animal sprite (modules 6, 7, 8 and 23) and the region's patches of
  TRAVEL, SITES, OUTDOOR, PROJECT and SUMMARY (rates, filters, reactions,
  sprite sizes, hint) come back exactly through overlay_load, the TRAVEL
  and SITES animal tables being equal;
- lot 7 step 4: the region's DHGR mood/shade/sprite colour tables in RAM
  equal build/dhgr/dhgr_tables_rN.bin; the species names and fauna
  sentence of REGIONTEXT; the first message names the region and its
  wildlife;
- the first view matches tools/dhgr_ref.py (terrain, forest, sky and
  sprites off, as in test_view.py) for the region's own map and palette;
- each species of the region (the fourth one through module 23) drawn next
  to the crash matches the reference with the region's sprite colours, and
  IGNORE names it in its result;
- no MLI call after start: a turn, STATUS and the module copies.
Then the free journey (7, region, level: random seeds, MAP+33 = 1), the
level entry (10, ESC back to the choice), H (placeholder, no file access)
and Q (ProDOS launcher).
"""
import json
from common import (HERE, L, DISK, a2test, menu_keys, text_screen, DHGR_BANKS,
                    dhgr, dhgr_view, mood_name, state, view_diff)
from test_boot import expected_map
from test_sprites import expected_dhgr
import dhgr_palette as P

LAYOUT = json.loads((HERE / 'build/layout.json').read_text())
SLOTS = (6, 7, 8, 23)


def counters(s):
    return int.from_bytes(s.step(L.peek('mli_calls', 2)).data, 'little')


def fetch(s, index):
    """overlay_load `index` from the idle loop; the $5800 window afterwards."""
    entry = L['idle']
    code = (0xA9, index, 0x20, L['overlay_load'] & 255, L['overlay_load'] >> 8,
            0x4C, entry & 255, entry >> 8)
    for i, b in enumerate(code):
        s.step(f'poke:{entry + i:04X}:{b:02X}')
    s.step(L.poke('overlay_current', 0))
    s.step(f'until:{entry + 5:04X}:200')
    window = s.step('peek:5800:2048').data
    s.step(L.until('idle', 100))        # back before the patched call
    return window


def scenario(region, level_keys='', level=4):
    pack = LAYOUT['packs'][str(region)]
    mapbin = (HERE / ('build/map.bin' if region == 2 else f'build/maps/r{region}.bin')).read_bytes()
    want_map = expected_map(mapbin, level, region)
    with a2test.Session(DISK, timeout=900, menu=False) as s:
        for step in menu_keys(str(region), level_keys):
            s.step(step)
        s.step(L.until('game_start', 20000))
        for name in ('forest_enabled', 'sky_enabled', 'scenes_enabled'):
            s.step(L.poke(name, 0))
        s.step(L.until('idle', 20000))
        start = counters(s)
        s.step('watch:BF00')
        header = s.step('peek:7000:64').data
        assert header == want_map[:64], (region, header.hex(), want_map[:64].hex())
        texts = s.step(L.peek('region_name', 128)).data
        assert texts[:16].rstrip(b'\0').decode() == pack['name'] and texts[104] == region
        assert texts[105] == len(pack['sprites']), (region, texts[105])
        regions = json.loads((HERE / 'build/regions/regions.json').read_text())['regions']
        entry = next(e for e in regions if e['region'] == region)
        fauna = json.loads((HERE / 'build/regions/fauna.json').read_text())['regions'][str(region)]
        names = [texts[56 + 12*k:68 + 12*k].rstrip(b'\0').decode() for k in range(4)]
        assert names == [x['name'] for x in fauna['species']] + [''] * (4 - len(fauna['species'])), names
        sentence = texts[16:56].rstrip(b'\0').decode()
        intro = texts[106:128].rstrip(b'\0').decode()
        assert sentence == entry['fauna_sentence'] and intro == entry['intro_name'], (sentence, intro)
        rows = text_screen(s.step('peek:0400:1024').data)
        assert rows[21].startswith(f'> CRASH IN {intro}. REACH THE RANGERS.'), rows[20:]
        assert rows[22].startswith(f'WILDLIFE: {sentence}'), rows[20:]
        tables = s.step(L.peek('dhgr_moods', L['dhgr_tables_end'] - L['dhgr_moods'])).data
        assert tables == (HERE / f'build/dhgr/dhgr_tables_r{region}.bin').read_bytes(), (region, 'colours')
        # First view: geometry and palette of the region's own map.
        pos = s.step(L.peek('px', 6)).data
        mood = s.step(L.peek('sky_mood')).data
        main = s.step(DHGR_BANKS[0]).data
        s.step(DHGR_BANKS[1])
        aux = s.step(DHGR_BANKS[2]).data
        s.step(DHGR_BANKS[3])
        px, py, h = state(pos)
        R = dhgr()
        ref = R.view(want_map, px, py, h, R.Sky(mood_name=mood_name(mood), region=region),
                     forest=False, sprites=False)
        bad, first = view_diff(dhgr_view(main, aux), ref)
        assert not bad, (region, bad, first)
        # Play a little: zero MLI calls.
        s.step('key:\\>')
        s.step(L.until('idle', 20000))
        s.step('key:STATUS\\r')
        s.step(L.until('status_key', 20000))
        s.step('key:\\e')
        s.step(L.until('idle', 20000))
        # Each species next to the crash (the wreck has priority on its own
        # cell), with the region's colours; IGNORE names it.
        s.step(L.poke('scenes_enabled', 1))
        s.step(L.poke('nature_frequency', 0))
        px, py, h = state(s.step(L.peek('px', 6)).data)     # after the turn
        x, y = (px >> 8) + 1, py >> 8
        s.step(L.poke('px', x, 1))
        for k, name in enumerate(pack['sprites']):
            kind = 6 + k
            for field, value in (('animal_kind', kind), ('animal_x', x), ('animal_y', y),
                                 ('animal_age', 0), ('animal_bearing', h & 255)):
                s.step(L.poke(field, value))
            s.step(L.poke('animal_bearing', h >> 8, 1))
            s.step('key:V\\r')
            s.step(L.until('idle', 20000))
            mood = s.step(L.peek('sky_mood')).data
            main = s.step(DHGR_BANKS[0]).data
            s.step(DHGR_BANKS[1])
            aux = s.step(DHGR_BANKS[2]).data
            s.step(DHGR_BANKS[3])
            want = expected_dhgr(x << 8 | (px & 255), py, h, name, h, want_map, mood_name(mood), region)
            bad, first = view_diff(dhgr_view(main, aux), want)
            assert not bad, (region, name, bad, first)
            s.step('key:IGNORE\\r')
            s.step(L.until('idle', 20000))
            rows = text_screen(s.step('peek:0400:1024').data)
            assert any(fauna['species'][k]['name'] in row for row in rows[21:24]), (region, name, rows[20:])
        # The woods with the region's crowns (and the wreck's billboard).
        s.step(L.poke('animal_kind', 0))
        s.step(L.poke('forest_enabled', 1))
        s.step('key:V\\r')
        s.step(L.until('idle', 20000))
        mood = s.step(L.peek('sky_mood')).data
        main = s.step(DHGR_BANKS[0]).data
        s.step(DHGR_BANKS[1])
        aux = s.step(DHGR_BANKS[2]).data
        s.step(DHGR_BANKS[3])
        px, py, h = state(s.step(L.peek('px', 6)).data)
        woods = want_map[:9472] + mapbin[9472:9472 + 294]      # with the woodland mask
        ref = R.view(woods, px, py, h, R.Sky(mood_name=mood_name(mood), region=region))
        bad, first = view_diff(dhgr_view(main, aux), ref)
        assert not bad, (region, 'woods', bad, first)
        # Directory, sprites and module patches through overlay_load (the
        # patched idle loop no longer reads the keyboard).
        directory = s.step(L.peek('module_dir', 26 * 7)).data
        for k, index in enumerate(SLOTS):
            entry = directory[index * 7:index * 7 + 7]
            if k >= len(pack['sprites']):
                if index == 23:
                    assert entry == bytes(7), (region, index, 'empty slot')
                else:       # two species: a one-byte empty sprite (build_disk)
                    assert entry[3:5] == b'\1\0' and fetch(s, index)[0] == 0, (region, index)
                continue
            module = pack['modules'][str(index)]
            assert int.from_bytes(entry[1:3], 'little') == module['address'], (region, index)
            image = (HERE / 'build' / module['image']).read_bytes()
            assert fetch(s, index)[:len(image)] == image, (region, index, module['image'])
        windows = {}
        for symbol, patch in pack['patches'].items():
            window = windows.setdefault(patch['module'], fetch(s, patch['module']))
            data = bytes.fromhex(patch['data'])
            offset = L[symbol] - 0x5800
            assert window[offset:offset + len(data)] == data, (region, symbol)
        assert pack['patches']['fauna_travel']['data'] == pack['patches']['fauna_table']['data']
        travel = bytes.fromhex(pack['patches']['fauna_travel']['data'])
        assert list(travel[:4]) == [x['rate'] for x in fauna['species']] + [0] * (4 - len(fauna['species']))
        calls = counters(s) - start
        watched = s.out.count('watch BF00')
    assert calls == 0 and watched == 0, (region, calls, watched)
    print(f'  {region} {pack["name"]:16} level {level:2}: map +32/+22/+33, texts and first message, '
          f'colours, directory, {len(pack["sprites"])} sprites drawn and named, fauna patches, '
          f'first view and woods, 0 MLI after start: OK')


def free_journey():
    with a2test.Session(DISK, timeout=900, menu=False) as s:
        s.step(L.until('menu_key', 40000))
        s.step('key:7')
        prompt = text_screen(s.step('peek:0400:1024').data)
        assert prompt[22].startswith('FREE JOURNEY: REGION'), prompt[22]
        s.step('key:\\e')           # ESC: back to the choice
        prompt = text_screen(s.step('peek:0400:1024').data)
        assert prompt[22].startswith('YOUR CHOICE'), prompt[22]
        s.step('key:73')
        s.step('key:7\\r')
        s.step(L.until('loader_pack', 2000))
        s.step('wait:2')
        intro = text_screen(s.step('peek:0400:1024').data)
        assert any(row.startswith('BURMA, LEVEL 7 (FREE)') for row in intro), intro
        s.step(L.until('game_start', 20000))
        header = s.step('peek:7000:64').data
        seeds = (s.step(L.peek('weather_seed', 4)).data, s.step(L.peek('fauna_rng')).data,
                 s.step(L.peek('water_rng')).data)
    assert header[32] == 3 and header[22] == 7 and header[33] == 1, header.hex()
    weather = (HERE / 'build/wildgame.bin').read_bytes()
    default = weather[L['weather_seed'] - 0x4000:L['weather_seed'] - 0x4000 + 4]
    assert seeds[0] != default and seeds[1] != b'\xB7' and seeds[1] != b'\0' and seeds[2] != b'\0', seeds
    print(f'  7 free journey: ESC back, Burma level 7, MAP+33 = 1, seeds {seeds[0].hex()} '
          f'{seeds[1].hex()} {seeds[2].hex()} instead of {default.hex()} b7 b7: OK')


def level_entry():
    """Two digits, an out-of-range level refused, ESC back to the choice."""
    # The bell of a refused key lasts about six frames: wait before typing on.
    steps = [L.until('menu_key', 40000), 'key:2', 'key:0\\r', 'wait:10', 'peek:0400:1024',
             'key:\\e', 'peek:0400:1024', 'key:610\\r', L.until('game_start', 20000), 'peek:7000:64']
    r = a2test.run(DISK, steps, menu=False, timeout=900)
    refused, back = text_screen(r.mem(0x400, 1024, 0)), text_screen(r.mem(0x400, 1024, 1))
    assert refused[22].startswith('LEVEL 1-10') and back[22].startswith('YOUR CHOICE'), (refused, back)
    header = r.mem(0x7000, 64)
    assert header[32] == 6 and header[22] == 10 and header[33] == 0, header.hex()
    print('  level entry: 0 refused, ESC back to the choice, Chile level 10: OK')


def hall_and_quit():
    steps = [L.until('menu_key', 40000), L.peek('mli_calls', 2), 'key:H', 'peek:0400:1024',
             'key: ', L.until('menu_key', 40000), 'peek:0400:1024', L.peek('mli_calls', 2), 'key:Q', 'wait:900', 'peek:0400:1024']
    r = a2test.run(DISK, steps, menu=False, timeout=900)
    hall, menu, launcher = (text_screen(r.mem(0x400, 1024, k)) for k in range(3))
    assert 'HALL OF FAME' in hall[0] and 'CHOOSE A JOURNEY' in menu[0], (hall, menu)
    # Lot 7 step 6: NEOWILD.HOF is read once before the menu (hm_load); the
    # volume's file is empty: six empty tables, no journey, every BEST "-".
    assert any('SCENARIO JOURNEYS: 0' in row for row in hall), hall
    assert sum(row.count(' -') for row in hall) >= 30, hall
    assert sum('BEST -' in row for row in menu) == 6, menu
    assert r.mem(L['mli_calls'], 2, 0) == r.mem(L['mli_calls'], 2, 1), 'H reads no file'
    assert any('BITSY' in row for row in launcher), launcher
    print('  H: empty hall of fame read before the menu, no file access, six BEST -, '
          'back to the menu; Q: ProDOS: OK')


def main():
    level_entry()
    hall_and_quit()
    free_journey()
    for region in range(1, 7):
        scenario(region)
    print('Start menu and region packs: OK')


if __name__ == '__main__':
    main()
