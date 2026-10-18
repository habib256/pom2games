#!/usr/bin/env python3
"""Bound UI costs while preserving native drink effects and map contents."""
from common import DISK, L, a2test, dhgr_view, text_screen
from test_joystick_journey import saved_state

IDLE = L.until('idle', 60000)
READY = L.until('keyboard_wait', 60000)
NAV = L.until('nav_key', 60000)


def clean_drink_case(force_redraw=False):
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        s.step(L.poke('water_untreated', 0))
        stock = int.from_bytes(s.step(L.peek('it_pack_lo', 1, 22)).data, 'little')
        assert stock > 1
        before = dhgr_view(s.step('peek:2000:8192').data)[16:]
        elapsed = s.step(L.peek('s_elap', 5)).data
        seed = s.step(L.peek('weather_seed', 4)).data
        hydration = s.step(L.peek('s_defw', 5)).data
        s.step('key:DRINK WATER 1 OZ')
        s.step('press:\\r')
        start = s.step(L.until('do_command', 60000)).cycles[-1]
        s.step(L.until('finish_simulation', 60000))
        assert s.step(L.peek('sim_quiet')).data == b'\x01'
        if force_redraw:
            s.step(L.poke('sim_quiet', 0))  # same completed native action; force old renderer
        end = s.step(IDLE).cycles[-1]
        if not force_redraw:
            assert end-start < 2_000_000, ('clean canteen drink redraws terrain', end-start)
        assert dhgr_view(s.step('peek:2000:8192').data)[16:] == before
        assert s.step(L.peek('s_elap', 5)).data == elapsed
        assert s.step(L.peek('weather_seed', 4)).data == seed
        assert s.step(L.peek('it_pack_lo', 1, 22)).data == bytes((stock-1,))
        assert s.step(L.peek('s_defw', 5)).data != hydration
        fields = {name: s.step(L.peek(name, size)).data for name, size in (
            ('px', 6), ('s_hour', L['s_t0']+5-L['s_hour']), ('weather_seed', 4),
            ('it_place', 76), ('it_pack_lo', 76), ('it_pack_hi', 76),
            ('it_gnd_lo', 76), ('it_gnd_hi', 76), ('injury_active', 15))}
        fields['picture'] = s.step('peek:2000:8192').data
        assert len(fields['picture']) == 16384, 'Both DHGR banks must be compared'
        fields['saved_state'] = saved_state(s)
        fields['result'] = [row[:39] for row in text_screen(s.step('peek:0400:1024').data)[20:]]
        return end-start, fields


def clean_drink():
    fast, outcome = clean_drink_case()
    slow, reference = clean_drink_case(force_redraw=True)
    assert outcome == reference, 'Cached drink differs from same-binary forced redraw'
    assert fast < slow/2, (fast, slow)
    print(f'Clean canteen drink: {fast:,} vs {slow:,} forced-redraw cycles; identical state/image')


def map_review_case(force_redraw=False):
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        s.step('key:MAP\\r')
        s.step(READY)
        s.step('press:\\r')
        s.step(L.until('nav_menu_key', 60000))
        s.step('press:\\r')
        s.step(NAV)
        # Choose a neighbouring point, then keep that map window for review.
        s.step('press:\\>')
        s.step(NAV)
        terrain = text_screen(s.step('peek:0400:1024').data)[2:23]
        elapsed = s.step(L.peek('s_elap', 5)).data
        position = s.step(L.peek('px', 4)).data
        costs = []
        outcomes = []
        for key in ('\\r', '\\e'):
            if force_redraw:
                s.step(L.poke('nav_frame_valid', 0))
            start = s.step(READY).cycles[-1]
            s.step('press:'+key)
            end = s.step(NAV).cycles[-1]
            costs.append(end-start)
            if not force_redraw:
                assert end-start < 400_000, ('map review recomputes terrain', end-start)
            assert text_screen(s.step('peek:0400:1024').data)[2:23] == terrain
            assert s.step(L.peek('s_elap', 5)).data == elapsed
            assert s.step(L.peek('px', 4)).data == position
            outcomes.append((s.step('peek:0400:1024').data, saved_state(s),
                             s.step(L.peek('weather_seed', 4)).data))
    return costs, outcomes


def map_review():
    fast, outcome = map_review_case()
    slow, reference = map_review_case(force_redraw=True)
    assert outcome == reference, 'Cached MAP differs from same-binary forced redraw'
    assert all(a < b/2 for a, b in zip(fast, slow)), (fast, slow)
    print(f'MAP review/back: {fast} vs {slow} forced-redraw cycles; identical map/state/RNG')


def other_water_keeps_redraw():
    for source in ('untreated canteen', 'ground'):
        with a2test.Session(DISK) as s:
            s.step(IDLE)
            s.step(L.poke('nature_frequency', 0))
            s.step(L.poke('water_untreated', int(source != 'ground')))
            if source == 'ground':
                s.step(L.poke('it_pack_lo', 0, 22))
                s.step(L.poke('it_pack_hi', 0, 22))
                s.step(L.poke('it_gnd_lo', 8, 22))
                s.step(L.poke('it_gnd_hi', 0, 22))
                for axis in ('x', 'y'):
                    cell = s.step(L.peek('p'+axis, 1, 1)).data[0]
                    s.step(L.poke('it_'+axis, cell, 22))
            s.step('key:DRINK WATER 1 OZ\\r')
            s.step(L.until('finish_simulation', 60000))
            assert s.step(L.peek('sim_quiet')).data == b'\x00', source
            s.step(IDLE)
    print('Ground and untreated water retain the ordinary rendering path')


if __name__ == '__main__':
    clean_drink()
    map_review()
    other_water_keeps_redraw()
