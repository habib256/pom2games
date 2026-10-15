#!/usr/bin/env python3
"""Night stars in the game (lot 7 step 5, docs/STARS.md section 10).

On dist/NEOWILDERNESS.po (Sierra Nevada, start position, real map): the
night of 6 May at 23 h, looking north (Polaris) and south; the same night
under clouds, at noon, and under a full Moon; then turns right and left.
After each view:
  - the resident list (st_a, st_row, st_bucket, in bank 2 of the main
    language card, read through $C080) equals
    tools/stars_ref.resident(visible(day, minute, lat, lon, Moon)) of the
    game's own date, hour and Moon (sky_bearing, sky_y);
  - the mood is the game's, and the view equals tools/dhgr_ref.view with
    that list (threshold of the mood: none by day, twilight or clouds;
    the figures under the bright Moon; all in the dark night);
  - no MLI call: module 25 and the catalogue's head (24) are RAM copies
    from the module store into the SIM window.
The Sun and Moon discs are switched off (sky_enabled 0, as in
test_moonlight.py) so that the comparison isolates the stars; the Moon still
masks the stars of its disc in the list.
"""
from common import idle_bytes, HERE, L, DISK, a2test, dhgr_view, mood_name, dhgr
from test_thermal import call, poke
from test_moonlight import phase_shape
import stars_ref

MAY_6 = 125                     # day of the year, 0 = 1 January


def signed(b):
    return b - 256 if b > 127 else b


def main():
    R = dhgr()
    m = bytearray((HERE / 'build/map.bin').read_bytes())
    lat, lon = signed(m[12]), signed(m[25])
    full_day = next(d for d in range(100, 365) if phase_shape(d) == 11)
    original = idle_bytes(12)    # three calls and the JMP back
    # (label, day, hour, heading, clouds)
    cases = [('north, Polaris', MAY_6, 23, 0, 0),
             ('south', MAY_6, 23, 280, 0),
             ('south under clouds', MAY_6, 23, 280, 1),
             ('noon', MAY_6, 12, 280, 0),
             ('Sirius, 1 January 0 h', 0, 0, 280, 0),
             ('full Moon night', full_day, 23, 280, 0)]
    # Turns after a case: every night turn scrolls and draws the revealed
    # columns only (35 per turn; the dark night too since the figures lot),
    # across north from 280: 315 ... 245.
    turns = {'Sirius, 1 January 0 h': ['>', '<'],
             'full Moon night': ['>', '>', '<', '<', '<']}
    list_bytes = 2 * stars_ref.LIST_MAX + stars_ref.BUCKETS
    peeks = [L.peek('night'), L.peek('view_dark'), L.peek('sky_mood'),
             L.peek('sky_bearing', 2), L.peek('sky_y'), L.peek('heading', 2),
             L.peek('px', 2), L.peek('py', 2), (L.peek('st_a', list_bytes),),
             L.peek('mli_calls', 2), 'peek:2000:8192']
    groups, done = [], []
    with a2test.Session(DISK, timeout=900) as s:
        def run(steps):
            for step in steps:
                s.step(step)

        def card(step):         # main language card, bank 2, read only
            s.step('peek:C080')
            data = s.step(step).data
            s.step('peek:C082')
            return data

        def dump():
            groups.append([card(p[0]) if isinstance(p, tuple) else s.step(p).data for p in peeks])
        run([L.until('game_start', 20000), L.poke('sky_enabled', 0),
             L.poke('forest_enabled', 0), L.until('idle', 20000)])
        mli0 = s.step(L.peek('mli_calls', 2)).data
        for label, day, hour, heading, clouds in cases:
            run(poke('s_date', (day + .01) / 365) + poke('s_hour', hour))
            run([L.poke('heading', heading), L.poke('heading', heading >> 8, 1),
                 L.poke('weather_sky', clouds)])
            # env_hour loads SIM, whose THERMAL tail covers the menu's
            # MENUSWAP ($B000, level1...): menu_gather brings it back, as
            # get_line does at every prompt, before the turns use it.
            run(call(['env_hour', 'show_view', 'menu_gather']) + [f'until:{L["idle"] + 9:04X}:20000'])
            dump()
            done.append((label, day, hour, clouds))
            run([L.until('idle', 20000)] + [L.poke('idle', b, i) for i, b in enumerate(original)])
            for key in turns.get(label, ()):
                run([f'press:\\{key}', L.until('turn_view', 20000), L.until('idle', 20000)])
                dump()
                done.append((f'{label}, turn {key}', day, hour, clouds))
        # LOOK UP on a clear night: the list is recomputed in the projection
        # of the raised view (stars_ref TU), the sky above 45 degrees fills
        # the top of the view instead of staying empty.
        run(poke('s_date', (MAY_6 + .01) / 365) + poke('s_hour', 23)
            + [L.poke('heading', 0), L.poke('heading', 0, 1), L.poke('weather_sky', 0), L.poke('tilt', 1)])
        run(call(['env_hour', 'show_view', 'menu_gather']) + [f'until:{L["idle"] + 9:04X}:20000'])
        up_list = card(L.peek('st_a', list_bytes))
        hb = int.from_bytes(s.step(L.peek('sky_hb', 2)).data, 'little')
        hy = s.step(L.peek('sky_hy')).data[0]
        up_mli = s.step(L.peek('mli_calls', 2)).data
        run([L.until('idle', 20000)] + [L.poke('idle', b, i) for i, b in enumerate(original)]
            + [L.poke('tilt', 0)])

    def check(label, day, hour, clouds, d):
        night, dark, mood, bearing, sky_y, head, x, y, lst, mli, page = d
        head = int.from_bytes(head, 'little')
        moon = (int.from_bytes(bearing, 'little'), sky_y[0])
        vis = stars_ref.visible(day, hour * 60, lat, lon, moon)
        attr, row, buckets, _ = stars_ref.resident(vis)
        if night[0]:            # by day the list of the last night stays, unused
            assert bytes(lst) == attr + row + buckets, (label, 'resident list')
        mood = mood_name(mood)
        thr = stars_ref.threshold(mood, bool(clouds))
        sky = R.Sky(night=bool(night[0]), mood_name=mood, clouds=bool(clouds), stars=tuple(vis))
        want = R.view(m, int.from_bytes(x, 'little'), int.from_bytes(y, 'little'), head, sky,
                      None, forest=False)
        got = dhgr_view(page)
        assert got == want, (label, mood, 'view differs')
        assert mli == mli0, (label, 'MLI call during play')
        drawn = stars_ref.star_pixels(head, [160] * 140, vis, thr)
        shown = {v['star']['name'] for v in vis for (c, r) in drawn
                 if v['az'] == stars_ref.column_az(head, c) and v['row'] == r
                 and want[r][c] == drawn[c, r]}
        return mood, thr, len(vis), head, shown

    report = []
    for (label, day, hour, clouds), group in zip(done, groups):
        report.append((label,) + check(label, day, hour, clouds, group))
    by = {r[0]: r for r in report}
    assert by['north, Polaris'][2] == 0xC0 and by['south'][2] == 0xC0, 'dark night: every star'
    assert by['south under clouds'][2] == 0 and by['noon'][2] == 0, 'no star by day or under clouds'
    assert 'POLARIS' in by['north, Polaris'][5], 'Polaris drawn'
    assert by['full Moon night'][2] == 0x40, 'full Moon: class 0 (figures) only'
    up_vis = stars_ref.visible(MAY_6, 23 * 60, lat, lon, (hb, hy), look_up=True)
    attr, row, buckets, _ = stars_ref.resident(up_vis)
    assert bytes(up_list) == attr + row + buckets, 'LOOK UP: resident list'
    high = [v for v in up_vis if (v['row'] + 96) & 255 < 96]
    assert high and up_mli == mli0, ('LOOK UP: stars in the upper half of the view', len(high))
    print(f'  LOOK UP, north: list {len(up_vis)}, {len(high)} entries in the upper half of the view: OK')
    for label, mood, thr, count, head, shown in report:
        print(f'  {label}: {mood}, heading {head}, threshold ${thr:02X}, list {count}, '
              f'{len(shown)} stars drawn ({", ".join(sorted(shown)) or "-"}): OK')
    print('Stars in the game: list, views, turns and zero MLI: OK')


if __name__ == '__main__':
    main()
