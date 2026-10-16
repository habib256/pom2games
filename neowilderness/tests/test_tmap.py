#!/usr/bin/env python3
"""TMAP on Apple II: scenario loading, topology, repeatability and gameplay."""
from collections import deque
import random
import sys

from common import HERE, L, DISK, DISK140, a2test, text_screen, dhgr_view
from gendata import fp as encode
from scenario import manifest

T = a2test.labels(HERE / 'build/tmap.lbl')
LIMIT = 12000


def poke(s, address, data):
    for i, value in enumerate(data):
        s.step(f'poke:{address+i:04X}:{value:02X}')


def text(s):
    return '\n'.join(text_screen(s.step('peek:0400:1024').data))


def choose(s, count=3, seed='1985'):
    for step in (L.until('menu_key', LIMIT), 'key:T', L.until('menu_key', 1000),
                 'key:\\r', T.until('getkey', LIMIT), f'key:{count}',
                 T.until('getkey', 1000), f'key:{seed}\\r', T.until('getkey', 2000)):
        s.step(step)
    assert f'SEED {seed.upper():0>4}' in text(s)


def components(cells):
    remaining = {i for i, v in enumerate(cells) if v < 128}
    found = []
    while remaining:
        first = remaining.pop()
        part = {first}
        pending = deque([first])
        while pending:
            p = pending.popleft()
            x, y = p % 112, p // 112
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if 0 <= x+dx < 112 and 0 <= y+dy < 84:
                    q = (y+dy)*112+x+dx
                    if q in remaining:
                        remaining.remove(q)
                        part.add(q)
                        pending.append(q)
        found.append(part)
    return sorted(found, key=lambda c: min(i % 112 for i in c))


def topology(m, count):
    cells = m[64:]
    parts = components(cells)
    assert len(parts) == count, [len(p) for p in parts]
    assert all(len(p) >= 500 for p in parts)
    assert all(cells[y*112+x] == 128 for y in range(84) for x in range(112)
               if x < 4 or x >= 108 or y < 4 or y >= 80), 'ocean at every boundary'
    assert m[5]*112+m[3] in parts[0], 'dry crash on first island'
    assert m[9]*112+m[8] in parts[-1], 'dry goal on last island'
    # Independent shore search: every successive island has a straight
    # east/west crossing of at most three coarse cells (six world units).
    routes = []
    for left, right in zip(parts, parts[1:]):
        best = None
        for y in range(4, 80):
            a = [p % 112 for p in left if p // 112 == y]
            b = [p % 112 for p in right if p // 112 == y]
            if a and b:
                gap = min(b)-max(a)-1
                if best is None or gap < best[0]:
                    best = (gap, max(a), min(b), y)
        assert best is not None and 1 <= best[0] <= 3, best
        routes.append(best)
    return routes


def generation():
    seeds = [0, 1, 0xA700, 0xFFFF, 0x1985]
    seeds += random.Random(1985).sample(range(65536), 43)
    with a2test.Session(DISK) as s:
        choose(s)
        m = s.step('peek:7000:9472').data
        topology(m, 3)
        # Re-enter only the separate generator; the engine is not running.
        # A driver in free $3500 RAM calls the public regeneration entry.
        poke(s, 0x3500, [0x20, 0x03, 0x20, 0x4C, 0, 0x35])
        poke(s, T['getkey'], [0x4C, 0, 0x35])
        snapshots = {}
        for count in (2, 3):
            for seed in seeds:
                poke(s, 0x7034, [seed & 255, seed >> 8, count, 4])
                s.step('until:3500:2000')
                s.step('until:3503:2000')
                m = s.step('peek:7000:9472').data
                topology(m, count)
                snapshots[count, seed] = m
                # Repeated generation must not retain any old geography.
                s.step('until:3500:2000')
                s.step('until:3503:2000')
                assert s.step('peek:7000:9472').data == m
        assert len({m[64:] for m in snapshots.values()}) >= 80
    print('  96 generated archipelagos: dry sites, 2/3 islands, ocean border, short crossings, reproducible')


def launch_and_play():
    with a2test.Session(DISK) as s:
        choose(s)
        m = s.step('peek:7000:9472').data
        routes = topology(m, 3)
        assert not manifest()['decor']['enabled']
        assert m[26] == 0 and s.step('peek:0800:294').data == bytes(294), 'trees removed'
        assert m[1] & 128, 'open-sea background'
        assert max(m[64:]) == 128 and max(v for v in m[64:] if v < 128) >= 49, 'strong relief'
        assert s.step('peek:5780:16').data.startswith(b'ARCHIPELAGO\0')
        s.step('key:\\r')
        s.step(L.until('idle', LIMIT))
        assert s.step('peek:7030:8').data == b'TG\x80\x01\x85\x19\x03\x04'
        assert s.step(L.peek('journey_kind')).data == b'\x01'
        s.step('shot:build/tmap-game.png')
        from test_camp import say
        assert 'GAME 1 SAVED' in say(s, 'SAVE 1')
        initial = s.step(L.peek('px', 4)).data
        poke(s, 0x7034, [0x84])
        assert 'SAME TERRAIN AND TMAP SEED' in say(s, 'RESTORE 1')
        assert s.step(L.peek('px', 4)).data == initial
        poke(s, 0x7034, [0x85])
        poke(s, L['px'], [0, 10])
        assert 'GAME 1 RESTORED' in say(s, 'RESTORE 1')
        assert s.step(L.peek('px', 4)).data == initial
        assert s.step('peek:7040:9408').data == m[64:]
        # A ray looking out of the western map edge has only a few samples.
        # The remaining space below row 95 must still be sea, not sky.
        poke(s, L['scenes_enabled'], [0])
        poke(s, L['sky_enabled'], [0])
        for name, value in (('px', 2*256+128), ('py', 40*256), ('heading', 420)):
            poke(s, L[name], value.to_bytes(2, 'little'))
        say(s, 'VIEW')
        page = dhgr_view(s.step('peek:2000:8192').data)
        far = s.step(L.peek('cur_pal', 1, 13)).data[0]
        assert all(page[r][c] == (far >> 4 if (r+420-70+c) & 1 else far & 15)
                   for r in range(96, 112) for c in range(140)), 'ocean reaches the horizon'
        assert any(page[94][c] not in (far >> 4, far & 15) for c in range(140)), 'sky above horizon'
        s.step('shot:build/tmap-sea-horizon.png')
        say(s, 'LOOK DOWN')
        down = dhgr_view(s.step('peek:2000:8192').data)
        assert all(down[16][c] in (far >> 4, far & 15) for c in range(140)), 'sea looking down'
        say(s, 'LOOK AHEAD')
        # Check actual hydration query, including the UI's WATER gate. The
        # first channel is sea, neither collectable nor counted untreated.
        _, left, right, y = routes[0]
        for name, value in (('px', (left+1)*256), ('py', y*256)):
            poke(s, L[name], value.to_bytes(2, 'little'))
        poke(s, L['camp_untreated'], [0])
        poke(s, L['weather_sky'], [0])
        # Existing test technique: replace idle by JSR + a self-loop.
        driver = [0x20, L['water_here'] & 255, L['water_here'] >> 8,
                  0x08, 0x68, 0x8D, 0, 0x95, 0x4C, (L['idle']+8) & 255, (L['idle']+8) >> 8]
        original = s.step(L.peek('idle', len(driver))).data
        poke(s, L['idle'], driver)
        s.step(f'until:{L["idle"]+8:04X}:1000')
        assert not (s.step('peek:9500:1').data[0] & 1), 'sea is not a drinking source'
        assert s.step(L.peek('camp_untreated')).data == b'\0'
        poke(s, L['idle'], original)
        # Rejoin idle from the loop, without changing the stack.
        poke(s, L['idle']+8, [0x4C, L['idle'] & 255, L['idle'] >> 8])
        s.step(L.until('idle', 1000))
        poke(s, L['idle'], original)
        # Real shore-to-shore SWIM, with a healthy swimmer at the first beach.
        for name, value in (('px', left*256), ('py', y*256), ('heading', 140)):
            poke(s, L[name], value.to_bytes(2, 'little'))
        poke(s, L['s_health'], encode(7.866609670221806))
        poke(s, L['night'], [0])
        poke(s, L['resource_seen'], [0])
        s.step('key:SWIM 4 H\\r')
        s.step(L.until('idle', LIMIT))
        x = int.from_bytes(s.step(L.peek('px', 2)).data, 'little') / 256
        assert right <= x < right+1, (left, right, x, text(s))
        assert s.step(L.peek('travel_reason')).data == b'\x02', text(s)
    print('  XL: no trees, high relief, sea horizon/tilt, SAVE/RESTORE, salt sea, real SWIM to next island')


def cancel_and_editions():
    with a2test.Session(DISK) as s:
        choose(s)
        s.step('key:\\e')
        s.step(L.until('menu_key', LIMIT))
        assert s.step(L.peek('ld_tmap')).data == b'\0'
        s.step('key:1')
        s.step(L.until('menu_key', 1000))
        s.step('key:\\r')
        s.step(L.until('idle', LIMIT))
        assert s.step('peek:5780:16').data.startswith(b'SIERRA NEVADA\0')
        assert s.step(L.peek('forest_crown_floor')).data == b'\x20'
        assert s.step('peek:7030:8').data == bytes(8)
    for disk, expected in ((DISK, True), (DISK140, False)):
        sys.path.insert(0, str(HERE.parent / 'dev/tools/prodos'))
        from read_volume import Image
        volume = Image(disk.read_bytes())
        names = {bytes(e[1:1+(e[0] & 15)]).decode('ascii') for e in volume.entries(2) if e[0] & 15}
        assert ('NEOWILD.TMP' in names) == expected
        assert ('NEOWILD.SCN' in names) == expected
        assert {f'NEOWILD.S{i}' for i in range(1, 6)} <= names
    print('  cancel to Sierra restores original scenery; TMAP/scenario on XL only; five saves on both')


if __name__ == '__main__':
    generation()
    launch_and_play()
    cancel_and_editions()
    print('TMAP: OK')
