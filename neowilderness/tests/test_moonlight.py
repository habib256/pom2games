#!/usr/bin/env python3
"""Full Moon reveals terrain, foliage and sprites against a night sky.

DHGR: the HGR rule decides whether the night is lit (view_dark: only a full
lunar disk; game logic depends on it), then the light is graded by the Moon
(docs/DHGR.md 3.1): high full Moon -> night bright, low or veiled -> night
dim, below the horizon -> night dark (terrain, woods and sprites black). The
mood the game chose must be dhgr_palette.select_mood of its own altitudes,
and every frame equals tools/dhgr_ref.view in that mood.
"""
import math
import tempfile

from common import HERE, L, a2test, disk_with, hgr_rows, dhgr, dhgr_view, mood_name
from sky_ephemeris import entry
from test_thermal import call, poke
from test_forest import map_fixture
import dhgr_palette as P
import stars_ref


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
                      L.peek('night'), L.peek('view_dark'), L.peek('sky_mood'),
                      L.peek('sun_alt8', 3), 'peek:2000:8192', L.peek('sky_bearing', 3),
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
    R = dhgr()

    def check(m_, dumps, label, x, y, h, animal, day, sky, forest=False):
        night, dark, mood, alt, page, moon = dumps
        assert night == b'\x01', (label, 'night physiology changed')
        assert dark == bytes([int(day == partial_day)]), (label, dark)
        moon8 = (alt[1] + 128) % 256 - 128
        want = 'night dark' if dark[0] else P.select_mood(-128, moon8, alt[2], bool(sky))
        mood = mood_name(mood)
        assert mood == want, (label, sky, mood, want, alt.hex())
        a = (animal, x * 256, y * 256, h) if animal else None
        # Lot 7 step 5: the stars of that night (0 h), the Moon's disc removed.
        lat, lon = ((b + 128) % 256 - 128 for b in (m_[12], m_[25]))
        stars = stars_ref.visible(day, 0, lat, lon, (moon[0] | moon[1] << 8, moon[2]))
        lit = R.Sky(night=True, mood_name=mood, moon8=moon8, phase=alt[2], clouds=bool(sky),
                    stars=tuple(stars))
        expected = R.view(m_, x*256, y*256, h, lit, a, forest=forest, sprites=not forest)
        assert dhgr_view(page) == expected, (label, sky, mood, 'night scene differs')
        return mood

    seen = set()
    for i, case in enumerate(cases):
        seen.add(check(m, result.dumps[6*i:6*i+6], *case))
    assert {'night bright', 'night dim', 'night dark'} <= seen, seen
    for i in range(8):
        p = len(cases)*6 + i*2
        assert hgr_rows(result.dumps[p]) == hgr_rows(result.dumps[p+1]), ('full Moon pan/redraw', i)
    woods = map_fixture()
    woods[2:6] = bytes((0, 20, 0, 20))
    case = ('woods', 20, 20, 140, 0, full_day, 0)
    with tempfile.TemporaryDirectory() as tmp:
        result = a2test.run(disk_with(tmp, bytes(woods)), steps_for([case], True),
                           emulator=a2test.A2SHOT, timeout=900)
    check(woods, result.dumps[:6], *case, forest=True)
    print(f'  full Moon: {", ".join(sorted(seen))}; terrain, woods, wreck, cabin and all fauna; '
          f'partial Moon dark: OK')


if __name__ == '__main__':
    main()
