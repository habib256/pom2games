#!/usr/bin/env python3
"""Full Moon reveals terrain, foliage and sprites against a black night sky."""
import math
import tempfile

from common import HERE, L, a2test, disk_with, view_rows, hgr_rows, view_ref
from sky_ephemeris import entry
from test_thermal import call, poke
from test_forest import map_fixture, reference as forest_reference
import scene_ref


def phase_shape(day, hour=0):
    interval = (day + hour / 24 + 120 / 360) / 2
    sample = math.floor(interval)
    a, b = entry(sample * 2)[2], entry((sample + 1) * 2)[2]
    phase = a + ((b - a + 128) % 256 - 128) * (interval - sample)
    return math.floor(5.5 * (1 - math.cos(phase * 2 * math.pi / 256)) + .5)


def main():
    full_day = next(day for day in range(365) if phase_shape(day) == 11)
    partial_day = next(day for day in range(365) if phase_shape(day) == 5)
    m = bytearray((HERE / 'build/map.bin').read_bytes())
    m[2:8] = bytes((0, 20, 0, 20, 140, 0))
    m[16:22] = bytes((1, 30, 20, 140, 0, 11))
    m[26] = 0
    m[64:64 + 9408] = bytes([10]) * 9408
    frames = [
        ('wreck', 20, 20, 140, 0),
        ('cabin', 30, 20, 140, 0),
        ('bear', 40, 20, 140, 6),
        ('cougar', 40, 20, 140, 7),
        ('rattlesnake', 40, 20, 140, 8),
        ('terrain', 60, 40, 140, 0),
    ]
    original = (HERE / 'build/wildgame.bin').read_bytes()[
        L['idle'] - 0x4000:L['idle'] - 0x4000 + 9]

    def steps_for(cases, forest=False):
        steps = [L.until('game_start', 20000), L.poke('sky_enabled', 0),
                 L.poke('ui_enabled', 0), L.poke('forest_enabled', int(forest)),
                 L.poke('scenes_enabled', int(not forest)),
                 L.until('idle', 20000)]
        for label, x, y, heading, animal, day, sky in cases:
            steps += poke('s_date', (day + .01) / 365) + poke('s_hour', 0)
            for name, value in [('px', x * 256), ('py', y * 256),
                                ('heading', heading), ('animal_bearing', heading)]:
                steps += [L.poke(name, value), L.poke(name, value >> 8, 1)]
            steps += [L.poke('animal_kind', animal), L.poke('animal_x', x),
                      L.poke('animal_y', y), L.poke('weather_sky', sky)]
            steps += call(['env_hour', 'show_view'])
            steps += [f'until:{L["idle"] + 6:04X}:20000',
                      L.peek('night'), L.peek('view_dark'), 'peek:2000:8192',
                      L.until('idle', 20000)]
            steps += [L.poke('idle', b, i) for i, b in enumerate(original)]
        return steps

    cases = [(label, x, y, h, animal, full_day, sky)
             for sky in (0, 1) for label, x, y, h, animal in frames]
    cases += [('partial moon', 60, 40, 140, 0, partial_day, 0)]
    cases += [('bear before turns', 40, 20, 140, 6, full_day, 0)]
    steps = steps_for(cases)
    for _ in range(8):
        steps += ['press:\\>', L.until('idle', 20000), 'peek:2000:8192',
                  'key:V\\r', 'wait:1', L.until('idle', 20000), 'peek:2000:8192']
    with tempfile.TemporaryDirectory() as tmp:
        result = a2test.run(disk_with(tmp, bytes(m)), steps,
                           emulator=a2test.A2SHOT, timeout=900)
    previous_sky = view_ref.SKY
    view_ref.SKY = (0, 0)
    try:
        for i, (label, x, y, h, animal, day, sky) in enumerate(cases):
            night, dark, page = result.dumps[3*i:3*i+3]
            assert night == b'\x01', (label, 'night physiology changed')
            assert dark == bytes([int(day == partial_day)]), (label, dark)
            a = (animal, x * 256, y * 256, h) if animal else None
            expected = bytes(6400) if day == partial_day else scene_ref.render(m, x*256, y*256, h, a)
            assert view_rows(page) == expected, (label, sky, 'night scene differs')
        for i in range(8):
            p = len(cases)*3 + i*2
            assert hgr_rows(result.dumps[p]) == hgr_rows(result.dumps[p+1]), ('full Moon pan/redraw', i)
        woods = map_fixture()
        woods[2:6] = bytes((0, 20, 0, 20))
        case = [('woods', 20, 20, 140, 0, full_day, 0)]
        with tempfile.TemporaryDirectory() as tmp:
            result = a2test.run(disk_with(tmp, bytes(woods)), steps_for(case, True),
                               emulator=a2test.A2SHOT, timeout=900)
        assert view_rows(result.dumps[2]) == forest_reference(woods, 20*256, 20*256, 140)
    finally:
        view_ref.SKY = previous_sky
    print('  full Moon: black sky, terrain, woods, wreck, cabin and all fauna; partial Moon dark: OK')


if __name__ == '__main__':
    main()
