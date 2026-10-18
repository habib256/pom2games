#!/usr/bin/env python3
"""Night checklist via real game-port input: inspection and native forms."""
import math
from common import DISK, L, fp, a2test
from test_guidance import start, state
from test_joystick_journey import GamePortSession, event, byte, rows, IDLE, READY


def open_night(s):
    event(s, 'up')
    for _ in range(7):
        if byte(s, 'pg_cur') == 6:
            break
        event(s, 'left')
    assert byte(s, 'pg_cur') == 6
    while byte(s, 'pg_focus') < 6:
        event(s, 'down')
    before = state(s)
    event(s, 'ok')
    assert 'PREPARE NIGHT' in ' '.join(rows(s)), rows(s)
    return before


def rest_followup(s):
    for _ in range(16):
        s.step(READY)
        if 'REST FOLLOW-UP' in ' '.join(rows(s)):
            s.step('wait:6')  # sample the released button before a new acceptance
            s.step(READY)
            return
        event(s, 'ok', READY)  # acknowledge native alert paging only
    raise AssertionError(('Missing deliberate rest follow-up', rows(s)))


def inspection():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        before = open_night(s)
        screen = ' '.join(rows(s))
        for word in ('SHELTER:', 'BODY:', 'SLEEPING BAG:', 'MEAL:', 'WATER:',
                     'REST:', 'ACTUAL / REQUESTED', 'SECOND BUTTON'):
            assert word in screen, (word, rows(s))
        for _ in range(7):
            event(s, 'down')
            assert state(s) == before, 'Browsing night preparation changes simulation'
        assert byte(s, 'night_cursor') == 0
        event(s, 'cancel', IDLE)
        assert state(s) == before
    print('Night review: all seven actions visible; joystick browsing/cancel preserve native state and RNG')


def bag_states():
    for place, hint in ((255, 'NOT ACCESSIBLE'), (2, 'UNAVAILABLE: NO NATIVE WEAR / USE ACTION'),
                        (1, 'READY: WORN NATIVE PROTECTION')):
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            s.step(L.poke('it_place', place, 1))
            before = open_night(s)
            assert hint in ' '.join(rows(s)), rows(s)
            assert state(s) == before
            event(s, 'cancel', IDLE)
            assert state(s) == before
    print('Sleeping bag: inaccessible, owned and worn are distinguished without activation')


def wear_clothes():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('it_place', 2, 1))  # Bag is owned, never advertised as wearable.
        s.step(L.poke('it_place', 2, 2))  # Accessible native garment for acceptance.
        before = open_night(s)
        event(s, 'down'); event(s, 'down')
        assert 'ACTION: WEAR CLOTHES' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', IDLE)
        assert byte(s, 'mn_verb') == 8 and byte(s, 'mn_items'), rows(s)
        entries = [entry & 127 for entry in s.step(L.peek('overlay_text', byte(s, 'mn_count'))).data]
        assert 1 not in entries and 2 in entries, entries
        assert state(s) == before, 'Opening WEAR activates equipment'
        event(s, 'cancel', IDLE)
        assert state(s) == before, 'Cancelling WEAR changes native state'
        # Reopen and deliberately accept a garment the native list offers.
        open_night(s)
        event(s, 'down'); event(s, 'down'); event(s, 'ok', IDLE)
        clock = s.step(L.peek('s_elap', 5)).data
        rng = s.step(L.peek('weather_seed', 4)).data
        from test_survival_flows import choose_source
        choose_source(s, 2, READY)
        assert byte(s, 'it_place', 2) == 1, 'Native WEAR did not wear DOWN PARKA'
        assert byte(s, 'it_place', 1) == 2, 'Night silently activated sleeping bag'
        assert s.step(L.peek('s_elap', 5)).data == clock
        assert s.step(L.peek('weather_seed', 4)).data == rng
    print('Night WEAR offers actual garments, excludes unsupported sleeping bag; cancel inert, accepted parka worn')


def use_tent():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        # Existing native tent rules reject the wreck and the outpost.
        # Move the test player to a different cell; preserve the native tent
        # metadata and setup cost, supplying only carried possession.
        wreck = s.step('peek:7003:3').data[::2]
        goal = s.step('peek:7008:2').data
        shelter = s.step('peek:7011:2').data
        cell = (wreck[0] + 3, wreck[1])
        while bytes(cell) in (goal, shelter):
            cell = (cell[0] + 1, cell[1])
        s.step(L.poke('px', cell[0], 1))
        s.step(L.poke('py', cell[1], 1))
        s.step(L.poke('fg_x', cell[0]))
        s.step(L.poke('fg_y', cell[1]))
        s.step(L.poke('shelter_inside', 0))
        s.step(L.poke('it_place', 2, 9))
        before = open_night(s)
        assert 'MISSING: ENTER SHELTER' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', IDLE)
        assert byte(s, 'mn_verb') == 10 and byte(s, 'mn_items'), rows(s)
        entries = [entry & 127 for entry in s.step(L.peek('overlay_text', byte(s, 'mn_count'))).data]
        assert 9 in entries, entries
        assert state(s) == before, 'Opening USE deploys tent'
        event(s, 'cancel', IDLE)
        assert state(s) == before, 'Cancelling USE deploys tent or spends time'
        open_night(s)
        event(s, 'ok', IDLE)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        from test_survival_flows import choose_source
        choose_source(s, 9, READY)
        assert byte(s, 'shelter_inside') == 1, rows(s)
        assert byte(s, 'it_place', 9) == 0
        assert (byte(s, 'it_x', 9), byte(s, 'it_y', 9)) == cell
        spent = fp(s.step(L.peek('s_elap', 5)).data) - elapsed
        assert abs(spent - .5) < .0001, ('Native tent setup duration', spent, rows(s))
    print('Night USE lists carried tent; cancel inert, acceptance deploys it and enters shelter in native 30 minutes')


def rest_duration():
    # Deterministic native rise 7: next end of darkness is 6:15.
    cases = ((1, 315), (3, 195), (5, 75))
    for hour, expected in cases:
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            s.step(L.poke('night', 1))
            # Exact positive integer Applesoft floats (1 <= hour <= 31).
            exponent = hour.bit_length() - 1
            s.step(L.poke('s_hour', 129 + exponent,
                          0))
            s.step(L.poke('s_hour', ((hour << (7-exponent)) & 127), 1))
            for offset in (2, 3, 4):
                s.step(L.poke('s_hour', 0, offset))
            s.step(L.poke('s_rise', 131))
            s.step(L.poke('s_rise', 96, 1))
            for offset in (2, 3, 4):
                s.step(L.poke('s_rise', 0, offset))
            before = open_night(s)
            assert int.from_bytes(s.step(L.peek('night_default', 2)).data, 'little') == expected, (hour, rows(s))
            assert f'{expected} MIN (' in ' '.join(rows(s)), rows(s)
            for _ in range(5):
                event(s, 'down')
            event(s, 'ok', READY)
            assert byte(s, 'mn_verb') == 3, rows(s)
            assert int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') == expected, rows(s)
            assert 'DURATION' in ' '.join(rows(s)), rows(s)
            event(s, 'right')
            assert int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') == expected + 1
            event(s, 'left')
            assert int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') == expected
            event(s, 'up')
            presets = (1, 5, 10, 20, 30, 60, 120, 240, 480, 960, 1440, 2880, 5760, 10080, 15300)
            assert int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') == next(n for n in presets if n > expected)
            assert state(s) == before, 'Opening proposed rest executes it'
            event(s, 'cancel', IDLE)
            assert state(s) == before
    print('Night rest adapts to clock; opens editable native durations with no time spent')


def daylight_rest():
    from test_thermal import poke
    # Exact ENERGY boundary comparisons: native thresholds are strictly >.
    for since, deficit, expected in ((4, 0, 30), (16, 7, 30),
                                      (4, 8, 120), (4, 12, 120),
                                      (17, 0, 480), (4, 13, 480)):
        with GamePortSession(DISK, menu=False) as s:
            start(s)
            s.step(L.poke('night', 0))
            for name, value in (('s_rest', since), ('s_defr', deficit)):
                for operation in poke(name, value):
                    s.step(operation)
            before = open_night(s)
            assert int.from_bytes(s.step(L.peek('night_default', 2)).data, 'little') == expected
            assert 'DAYLIGHT: SHORT REST BY ENERGY' in ' '.join(rows(s)), rows(s)
            for _ in range(6):
                event(s, 'down')
            assert 'PLAN NEXT DAWN REST' in ' '.join(rows(s)), rows(s)
            assert state(s) == before
            event(s, 'ok', READY)
            assert int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little') > expected
            assert state(s) == before
            event(s, 'cancel', IDLE)
            assert state(s) == before
    print('Daylight: ENERGY thresholds suggest short/medium/full rest; next dawn is explicit and inert')


def native_night_completion():
    # Advance the native clock through actual rest; leave astronomy untouched.
    with a2test.Session(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('scenes_enabled', 0))
        hour = fp(s.step(L.peek('s_hour', 5)).data)
        preparation = round(((19 - hour) % 24) * 60)
        s.step(f'key:REST {preparation} MIN\\r')
        s.step(IDLE)
        hour = fp(s.step(L.peek('s_hour', 5)).data)
        assert abs(hour - 19) < 1 / 60, hour
        # Independently evaluate the native sunrise formula at next midnight.
        constant = lambda name: fp(s.step(L.peek(name, 5)).data)
        date = (constant('s_date') + (24 - hour) * 60 * constant('f_inv_year')) % 1
        latitude = int.from_bytes(s.step('peek:700C:1').data, 'little', signed=True)
        sin_decl = constant('f_0_398') * math.sin(constant('f_2pi') * date - constant('f_1_378'))
        excess = constant('f_12_pi') * math.asin(math.tan(latitude * constant('f_rad')) * sin_decl / math.sqrt(1 - sin_decl ** 2))
        boundary = 6 - excess - constant('f_twilight')
        expected = math.ceil(((boundary - hour) % 24) * 60) + 1
        s.step(L.poke('duration_rest', 62))
        s.step(L.poke('duration_rest', 0, 1))
        before = open_night(s)
        # 19:00 may still be native dusk. Planning next dawn is explicit
        # during daylight, and opens the same editable native REST form.
        cursor = 5 if byte(s, 'night') else 6
        for _ in range(cursor):
            event(s, 'down')
        event(s, 'ok', READY)
        requested = int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little')
        assert requested == expected and requested > 480, (requested, expected, rows(s))
        assert state(s) == before
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        # Confirm once, stop at the resident report handoff before native
        # hunger/thirst messages page their full result column.
        s.step('btn:0,1')
        s.step(L.until('module_rest_result', 60000))
        s.step('btn:0,0')
        assert int.from_bytes(s.step(L.peek('msgnum', 2)).data, 'little') == requested
        spent = (fp(s.step(L.peek('s_elap', 5)).data) - elapsed) * 60
        assert abs(spent - requested) < 1e-5, (spent, requested, rows(s))
        assert byte(s, 'night') == 0, rows(s)
        assert int.from_bytes(s.step(L.peek('duration_rest', 2)).data, 'little') == 62
        # Native alert paging asks for acknowledgement, without requesting
        # or simulating another REST. Its next alert replaces the result.
        rest_followup(s)
        assert 'CAMP DEPARTURE' in ' '.join(rows(s)), rows(s)
        event(s, 'cancel', IDLE)
        assert abs((fp(s.step(L.peek('s_elap', 5)).data) - elapsed) * 60 - requested) < 1e-5
    print('Night: one uncapped native rest completes the proposed night-end without a second request')


def interrupted_rest_followup():
    from test_thermal import poke
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        for operation in poke('s_hour', 1):
            s.step(operation)
        s.step(L.poke('night', 1))
        before = open_night(s)
        for _ in range(5):
            event(s, 'down')
        event(s, 'ok', READY)
        assert state(s) == before
        s.step('btn:0,1')
        s.step(L.until('module_rest_step', 60000))
        s.step('btn:0,0')
        s.step('btn:1,1')
        s.step(L.until('module_rest_result', 60000))
        s.step('btn:1,0')
        s.step('wait:6')
        assert byte(s, 'input_interrupted')
        assert byte(s, 'dep_running') == 0x84
        rest_followup(s)
        screen = ' '.join(rows(s))
        assert 'REVIEW REST TO DAWN' in screen, rows(s)
        assert 'STOPPED' in screen or 'RESTED' in screen, rows(s)
        after = state(s)
        event(s, 'ok', READY)
        assert 'PREPARE NIGHT' in ' '.join(rows(s)), rows(s)
        assert state(s) == after, 'Review continuation advances native simulation'
        event(s, 'cancel', IDLE)
        assert state(s) == after, 'Cancelling review replays the preceding REST'
        assert byte(s, 'dep_running') == 0
    print('Night interruption: native report retained; dawn review explicit, recomputed and cancellable')


def within_final_minute():
    from test_thermal import poke
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        boundary = fp(s.step(L.peek('s_rise', 5)).data) - fp(s.step(L.peek('f_twilight', 5)).data)
        for operation in poke('s_hour', boundary - 1 / 120):
            s.step(operation)
        s.step(L.poke('night', 1))
        before = open_night(s)
        assert int.from_bytes(s.step(L.peek('night_default', 2)).data, 'little') == 1
        for _ in range(5):
            event(s, 'down')
        event(s, 'ok', READY)
        assert state(s) == before
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', READY)
        rest_followup(s)
        assert 'CAMP DEPARTURE' in ' '.join(rows(s)), rows(s)
        after = state(s)
        event(s, 'ok', READY)
        assert 'CAMP - CHOOSE ONE ACTION' in ' '.join(rows(s)), rows(s)
        assert state(s) == after
        event(s, 'cancel', IDLE)
        assert state(s) == after
        assert abs((fp(s.step(L.peek('s_elap', 5)).data) - elapsed) * 60 - 1) < 1e-5
        assert byte(s, 'night') == 0, rows(s)
    print('Night final fractional minute: one native minute reaches the actual night-end')


if __name__ == '__main__':
    inspection()
    bag_states()
    wear_clothes()
    use_tent()
    daylight_rest()
    rest_duration()
    interrupted_rest_followup()
    within_final_minute()
    native_night_completion()
