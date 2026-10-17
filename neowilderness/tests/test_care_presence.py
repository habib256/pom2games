#!/usr/bin/env python3
"""Joystick STATUS presence and native care acceptance: splint and fire."""
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE
from test_status_care_return import RESULT, returned


def preview(s, expected):
    event(s, 'up'); event(s, 'down')
    line = rows(s)[22]
    assert expected in line and 'DOSES' not in line, line
    before = saved_state(s)
    event(s, 'right'); event(s, 'left')
    assert rows(s)[22] == line and saved_state(s) == before
    event(s, 'cancel', IDLE)
    assert saved_state(s) == before
    event(s, 'up'); event(s, 'down')
    assert expected in rows(s)[22]
    return before


def splint(disk, place, local=True, condition=1, wrong_y=False):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('injury_active', 1, condition))
        s.step(L.poke('splint_place', place))
        s.step(L.poke('cr_cx', byte(s, 'px', 1)+(0 if local else 1), 2))
        s.step(L.poke('cr_cy', byte(s, 'py', 1)+int(wrong_y), 2))
        present = place != 255 and (place != 0 or (local and not wrong_y))
        preview(s, f'30 MIN; SPLINT REQUIRED; {"HERE" if present else "NOT HERE"}')
        before_time = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', RESULT)
        spent = fp(s.step(L.peek('s_elap', 5)).data)-before_time
        assert abs(spent-(.5 if present else 0)) < 1e-6
        assert byte(s, 'splint_place') == (1 if present else place)
        assert byte(s, 'medical_actions', 2) == (1 if present else 0)
        returned(s, condition, 0)
        assert ('; HERE' if present else '; NOT HERE') in rows(s)[22]
        print(f'  Splint place {place}, local={local}, wrong_y={wrong_y}, condition={condition}: read-only presence = native USE, {spent*60:.0f} MIN: OK', flush=True)


def fire(disk, burning, rain=False, immersed=False, inside=False):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        s.step(L.poke('injury_active', 1, 6))
        s.step(L.poke('fire_on', burning))
        s.step(L.poke('fire_near', 0))
        s.step(L.poke('weather_sky', 2 if rain else 0))
        s.step(L.poke('wind', 0)); s.step(L.poke('camp_use', 0))
        if immersed:
            # Native cell byte, with the fixture map using its legacy grid.
            address = 0x7040+byte(s, 'py', 1)*112+byte(s, 'px', 1)
            s.step(f'poke:{address:04X}:80')
        if inside:
            s.step(L.poke('shelter_inside', 1))
        preview(s, f'0 MIN; FIRE NEEDED; {"HERE" if burning else "NOT HERE"}')
        assert 'READY' not in rows(s)[22]
        before_time = s.step(L.peek('s_elap', 5)).data
        event(s, 'ok', RESULT)
        accepted = bool(burning) and not rain and not immersed
        assert byte(s, 'fire_near') == int(accepted)
        assert byte(s, 'medical_actions', 23) == int(accepted)
        assert s.step(L.peek('s_elap', 5)).data == before_time
        returned(s, 6, 0)
        print(f'  Fire {burning}, rain={rain}, immersed={immersed}, shelter={inside}: presence does not promise READY, native use={accepted}, 0 MIN: OK', flush=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        for place, local in ((255, True), (0, True), (0, False), (1, True), (2, True), (3, True), (5, True)):
            splint(disk, place, local)
        splint(disk, 2, condition=2)
        splint(disk, 0, wrong_y=True)
        fire(disk, 0)
        fire(disk, 1)
        fire(disk, 2)
        fire(disk, 1, rain=True)
        fire(disk, 1, inside=True)
        fire(disk, 1, immersed=True)
    print('Care presence: OK')
