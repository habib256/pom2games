#!/usr/bin/env python3
"""game_shots.py: captures of the real DHGR game in build/dhgr/game_*.png.

Lot 4 adds the interface: game_ui_*.png (band and panels by day, a warning,
at night, an action result in the 80-column rows, STATUS, INVENTORY, HELP,
MAP, TOPO and the view after TOPO).

Boots ../dist/NEOWILDERNESS.po in a2shot (enhanced //e) and photographs the
view: the crash site by day, after turns, at the golden hour, at sunset, in
civil twilight, under a high full Moon (and facing it), in the woods, and
after returning from STATUS and TOPO (game_topo.png: the DHGR TOPO sheet). Times are set like tests/test_moonlight.py: the clock
floats are poked, then env_hour and show_view are called from the idle loop
(no command, no random draw). Prints the mood of each frame.

Lot 7 (--regions): for each of the six scenarios chosen at the start
menu, game_region_rN_start.png (the first view, 7 h on May 6: already the
golden hour in the southern autumn of Bolivia and Chile), the same place at
11 h (game_region_rN_day.png) and at the evening golden hour
(game_region_rN_golden.png), and in Burma and Bolivia the fourth species
next to the crash (game_region_rN_species4.png).

Lot 7 step 5 (--stars): night skies, game_stars_*.png: the Sierra Nevada on
6 May at 23 h facing north (Polaris, Kochab, Cassiopeia, Cepheus, Draco)
and south (Scorpius, Libra, Centaurus, Corvus), the same south under the
full Moon (first magnitude only), and Bolivia on 6 May at 21 h facing south
(the Southern Cross); prints the number of stars drawn in each.

  python3 tools/game_shots.py [--out build/dhgr] [--regions | --stars]
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tests'))
from common import idle_bytes, L, DISK, a2test, mood_name, menu_keys, dhgr_view  # noqa: E402
from test_thermal import call, poke  # noqa: E402
from test_moonlight import phase_shape  # noqa: E402


def region_shots(out):
    """The six scenarios: first view, golden hour, fourth species."""
    idle = L['idle']
    original = idle_bytes()
    shots = []
    for region in range(1, 7):
        with a2test.Session(DISK, timeout=900, menu=False) as s:
            for step in menu_keys(str(region)):
                s.step(step)
            s.step(L.until('idle', 30000))
            s.step(L.poke('nature_frequency', 0))

            def shot(name):
                s.step('wait:3')
                s.step(f'shot:{out / f"game_region_r{region}_{name}.png"}')
                mood = mood_name(s.step(L.peek('sky_mood')).data)
                shots.append((region, name, mood))
                print(f'  game_region_r{region}_{name}.png  {mood}', flush=True)
                return mood

            def at_hour(hour):
                s.step(L.until('idle', 60000))
                for st in poke('s_hour', hour):
                    s.step(st)
                s.step(L.poke('ui_dirty', 1))
                for st in call(['env_hour', 'show_view']):
                    s.step(st)
                s.step(f'until:{idle + 6:04X}:60000')
                for i, b in enumerate(original):
                    s.step(L.poke('idle', b, i))
                s.step(L.until('idle', 60000))
                return mood_name(s.step(L.peek('sky_mood')).data)

            shot('start')
            at_hour(11)
            shot('day')
            for tenth in range(160, 200):            # the evening golden hour
                if at_hour(tenth / 10) == 'golden':
                    break
            shot('golden')
            if region in (3, 5):
                at_hour(9.5)
                px, py, h = (int.from_bytes(s.step(L.peek(n, 2)).data, 'little')
                             for n in ('px', 'py', 'heading'))
                x, y = (px >> 8) + 1, py >> 8
                s.step(L.poke('px', x, 1))
                for name, value in (('animal_kind', 9), ('animal_x', x), ('animal_y', y),
                                    ('animal_age', 0), ('animal_bearing', h & 255)):
                    s.step(L.poke(name, value))
                s.step(L.poke('animal_bearing', h >> 8, 1))
                s.step('key:V\\r')
                s.step('wait:1')
                s.step(L.until('idle', 60000))
                shot('species4')
    return shots


def stars_drawn(s, mood):
    """Stars of the list (main language card, bank 2) that are on screen:
    in the view, admitted by the mood, their pixel in their colour."""
    import stars_ref
    m = stars_ref.LIST_MAX
    s.step('peek:C080')
    lst = s.step(L.peek('st_a', 2 * m + stars_ref.BUCKETS)).data
    s.step('peek:C082')
    head = int.from_bytes(s.step(L.peek('heading', 2)).data, 'little')
    view = dhgr_view(s.step('peek:2000:8192').data)
    thr = stars_ref.threshold(mood, False)
    return sum(1 for v in stars_ref.decode_resident(lst[:m], lst[m:2 * m], lst[2 * m:])
               if v['attr'] < thr and (v['az'] - head + 70) % 560 < 140
               and view[v['row']][(v['az'] - head + 70) % 560] == v['colour'])


def star_shots(out):
    """Night skies of the Sierra Nevada and Bolivia (docs/STARS.md)."""
    idle = L['idle']
    original = idle_bytes()
    full_day = next(day for day in range(100, 365) if phase_shape(day) == 11)
    shots = []
    for region, views in ((2, (('sierra_polaris', 125, 23, 0), ('sierra_south', 125, 23, 280),
                               ('sierra_full_moon', full_day, 23, 280))),
                          (5, (('bolivia_cross', 125, 21, 280),))):
        with a2test.Session(DISK, timeout=900, menu=False) as s:
            for step in menu_keys(str(region)):
                s.step(step)
            s.step(L.until('idle', 30000))
            s.step(L.poke('nature_frequency', 0))
            for name, day, hour, heading in views:
                s.step(L.until('idle', 60000))
                for st in poke('s_date', (day + .01) / 365) + poke('s_hour', hour):
                    s.step(st)
                s.step(L.poke('heading', heading))
                s.step(L.poke('heading', heading >> 8, 1))
                s.step(L.poke('weather_sky', 0))
                s.step(L.poke('ui_dirty', 1))
                for st in call(['env_hour', 'show_view']):
                    s.step(st)
                s.step(f'until:{idle + 6:04X}:60000')
                for i, b in enumerate(original):
                    s.step(L.poke('idle', b, i))
                s.step(L.until('idle', 60000))
                s.step('wait:3')
                s.step(f'shot:{out / f"game_stars_{name}.png"}')
                mood = mood_name(s.step(L.peek('sky_mood')).data)
                drawn = stars_drawn(s, mood)
                shots.append((name, mood, drawn))
                print(f'  game_stars_{name}.png  {mood}, {drawn} stars drawn', flush=True)
    return shots


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', type=Path, default=HERE / 'build/dhgr')
    ap.add_argument('--regions', action='store_true', help='lot 7: the six scenarios only')
    ap.add_argument('--stars', action='store_true', help='lot 7: night skies only')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.regions:
        return region_shots(a.out)
    if a.stars:
        return star_shots(a.out)
    full_day = next(day for day in range(365) if phase_shape(day) == 11)
    idle = L['idle']
    original = idle_bytes()
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
        # Interface (lot 4), back at the crash site by day.
        at_time(160, 9.5, x, y, h)

        def ui(name, wait=3):
            s.step(f'wait:{wait}')
            s.step(f'shot:{a.out / f"game_ui_{name}.png"}')
            print(f'  game_ui_{name}.png', flush=True)
        ui('day')
        key('EAT CHEESE 2 OZ\\r')
        ui('message')
        for name, value, offset in (('ui_previous', 1, 5), ('ui_pending', 3, 0), ('ui_dirty', 1, 0)):
            s.step(L.poke(name, value, offset))
        key('VIEW\\r')
        ui('warning')
        for screen, until, name in (('STATUS', 'status_key', 'status'), ('INVENTORY', 'inventory_key', 'inventory'),
                                    ('HELP', 'help_key', 'help'), ('MAP', 'topo_key', 'map'),
                                    ('TOPO', 'graphical_topo_key', 'topo')):
            key(f'{screen}\\r', until)
            ui(name)
            s.step('key:\\e')
            s.step('wait:1')
            s.step(L.until('idle', 60000))
        ui('after_topo')
        s.step(L.poke('ui_previous', 0, 5))     # no condition: the night hint
        at_time(full_day, 22, x, y, h)
        ui('night')
    return shots


if __name__ == '__main__':
    main()
