#!/usr/bin/env python3
"""game_shots.py: captures of the real DHGR game (lot 3) in build/dhgr/game_*.png.

Boots ../dist/NEOWILDERNESS.po in a2shot (enhanced //e) and photographs the
view: the crash site by day, after turns, at the golden hour, at sunset, in
civil twilight, under a high full Moon (and facing it), in the woods, and
after returning from STATUS and TOPO (game_topo.png: the DHGR TOPO itself, lot 4).
Times are set like tests/test_moonlight.py: the clock
floats are poked, then env_hour and show_view are called from the idle loop
(no command, no random draw). Prints the mood of each frame.

  python3 tools/game_shots.py [--out build/dhgr]
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tests'))
from common import L, DISK, a2test, mood_name  # noqa: E402
from test_thermal import call, poke  # noqa: E402
from test_moonlight import phase_shape  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', type=Path, default=HERE / 'build/dhgr')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    full_day = next(day for day in range(365) if phase_shape(day) == 11)
    idle = L['idle']
    original = (HERE / 'build/wildgame.bin').read_bytes()[idle - 0x4000:idle - 0x4000 + 9]
    shots = []
    with a2test.Session(DISK, timeout=900) as s:
        s.step(L.until('idle', 30000))
        s.step(L.poke('nature_frequency', 0))

        def shot(name):
            s.step('wait:3')
            s.step(f'shot:{a.out / f"game_{name}.png"}')
            mood = s.step(L.peek('sky_mood')).data
            shots.append((name, mood_name(mood)))
            print(f'  game_{name}.png  {mood_name(mood)}', flush=True)

        def key(text, until='idle'):
            s.step(f'key:{text}')
            s.step('wait:1')
            s.step(L.until(until, 60000))

        def at_time(day, hour, x=None, y=None, heading=None):
            s.step(L.until('idle', 60000))      # patch the loop from its first byte
            for st in poke('s_date', (day + .01) / 365) + poke('s_hour', hour):
                s.step(st)
            for name, value in (('px', x), ('py', y), ('heading', heading)):
                if value is not None:
                    s.step(L.poke(name, value))
                    s.step(L.poke(name, value >> 8, 1))
            s.step(L.poke('ui_dirty', 1))
            for st in call(['env_hour', 'show_view']):
                s.step(st)
            s.step(f'until:{idle + 6:04X}:60000')
            for i, b in enumerate(original):
                s.step(L.poke('idle', b, i))
            s.step(L.until('idle', 60000))

        shot('crash_day')
        key('\\>')
        shot('turn_right')
        key('LOOK L\\r')
        shot('look_left')
        key('STATUS\\r', 'wait_key')
        s.step('key: ')
        s.step('wait:1')
        s.step(L.until('idle', 60000))
        shot('after_status')
        key('TOPO\\r', 'graphical_topo_key')
        s.step('wait:3')
        s.step(f'shot:{a.out / "game_topo.png"}')
        print('  game_topo.png', flush=True)
        s.step('key:\\r')
        s.step('wait:1')
        s.step(L.until('idle', 60000))
        shot('after_topo')
        start = [s.step(L.peek(n, 2)).data for n in ('px', 'py', 'heading')]
        x, y, h = (int.from_bytes(v, 'little') for v in start)
        at_time(160, 18.5, x, y, h)
        shot('golden')
        at_time(160, 19.2, x, y, h)
        shot('sunset')
        at_time(160, 19.6, x, y, h)
        shot('civil')
        at_time(full_day, 22, x, y, h)
        shot('night_full_moon')
        at_time(full_day, 22, x, y, (h + 280) % 560)
        shot('night_full_moon_back')
        for hour, name in ((20, 'night_moon_disk'), (5, 'dawn_nautical')):
            at_time(full_day, hour, x, y, h)     # the Moon's bearing at that hour
            moon = int.from_bytes(s.step(L.peek('sky_bearing', 2)).data, 'little')
            at_time(full_day, hour, x, y, moon)
            shot(name)
        at_time(160, 12, 41 * 256 + 128, 27 * 256 + 128, 140)
        shot('woods_noon')
        at_time(160, 18.5, 41 * 256 + 128, 27 * 256 + 128, 140)
        shot('woods_golden')
    return shots


if __name__ == '__main__':
    main()
