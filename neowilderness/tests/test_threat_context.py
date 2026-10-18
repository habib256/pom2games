#!/usr/bin/env python3
"""Encounter continuations through the game port preserve native rules/goals."""
import tempfile
from common import L, disk_with, fp
from test_forest import map_fixture
from test_fit_quantities import boot
from test_animal_reactions import prepare, seed_for, rng
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, grid, duration_control, IDLE, READY


def snapshot(s):
    fields = [('animal_kind', 4), ('fauna_rng', 1), ('weather_seed', 4),
              ('fg_use', 1), ('camp_use', 1), ('care_tools', 1),
              ('injury_active', 13), ('travel_pending', 1), ('route_active', 1)]
    return saved_state(s), tuple(s.step(L.peek(name, size)).data for name, size in fields)


def open_threat(s):
    grid(s, 'WAIT', '1 MIN', ready=L.until('module_threat', 60000))
    before = snapshot(s)
    s.step(READY)
    assert 'BEAR HERE' in ' '.join(rows(s)), rows(s)
    assert byte(s, 'th_present') == 1
    assert snapshot(s) == before
    return before


def choose(s, cursor):
    for _ in range(7):
        if byte(s, 'th_cursor') == cursor:
            return
        event(s, 'right', READY)
    raise AssertionError(rows(s))


def inspection_and_failure(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        seed = seed_for((129, 256), (52, 256))
        prepare(s, 6, seed)
        s.step(L.poke('camp_use', 0))
        s.step(L.poke('fg_use', 0))
        s.step(L.poke('care_tools', 0))
        s.step(L.poke('it_place', 3, 58))
        before = open_threat(s)
        assert 'BLADE AVAILABLE, NOT IN USE' in ' '.join(rows(s)), rows(s)
        assert 'FIRE OFF' in ' '.join(rows(s)), rows(s)
        for cursor in range(1, 7):
            choose(s, cursor)
        assert snapshot(s) == before
        event(s, 'cancel', IDLE)
        assert snapshot(s) == before
        assert byte(s, 'threat_context') == 0
        open_threat(s)
        choose(s, 1)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', READY)
        assert byte(s, 'animal_kind') == 6
        assert byte(s, 'fauna_rng') == rng(rng(seed))
        assert not any(s.step(L.peek('injury_active', 13)).data)
        assert abs(fp(s.step(L.peek('s_elap', 5)).data) - elapsed - 5/60) < 1e-6
        assert 'NOISE FAILS' in ' '.join(rows(s)), rows(s)
        assert 'BEAR STILL HERE' in ' '.join(rows(s)), rows(s)
        after = snapshot(s)
        choose(s, 2)
        event(s, 'cancel', IDLE)
        assert snapshot(s) == after


def fire_before_flee(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        prepare(s, 6, seed_for((129, 256), (52, 256)))
        s.step(L.poke('travel_pending', 22))
        s.step(L.poke('fire_on', 1))
        s.step(L.poke('fire_near', 1))
        before = open_threat(s)
        choose(s, 4)
        assert '> DOUSE FIRE (BEFORE MOVING)' in ' '.join(rows(s)), rows(s)
        assert snapshot(s) == before
        event(s, 'cancel', IDLE)
        assert snapshot(s) == before
        open_threat(s)
        choose(s, 4)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        random_before = tuple(s.step(L.peek(name, size)).data for name, size
                              in (('fauna_rng', 1), ('weather_seed', 4)))
        event(s, 'ok', READY)
        assert not byte(s, 'fire_on') and not byte(s, 'fire_near')
        assert fp(s.step(L.peek('s_elap', 5)).data) == elapsed
        assert random_before == tuple(s.step(L.peek(name, size)).data for name, size
                                      in (('fauna_rng', 1), ('weather_seed', 4)))
        assert byte(s, 'animal_kind') == 6 and byte(s, 'travel_pending') == 22
        assert 'BEAR STILL HERE' in ' '.join(rows(s)), rows(s)
        assert 'FIRE OFF' in ' '.join(rows(s)), rows(s)
        after = snapshot(s)
        choose(s, 5)
        event(s, 'ok', READY)
        assert 'RESUME 0 MIN LEFT, SAME CAP. RETURN GO.' in ' '.join(rows(s)), rows(s)
        assert snapshot(s) == after
        event(s, 'cancel', READY)
        assert snapshot(s) == after


def resolved_trip(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        seed = seed_for((0, 129))
        prepare(s, 6, seed)
        s.step(L.poke('travel_pending', 22))
        before = open_threat(s)
        assert 'TRIP KEPT' in ' '.join(rows(s)), rows(s)
        assert snapshot(s) == before
        choose(s, 1)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', READY)
        assert byte(s, 'animal_kind') == 0
        assert byte(s, 'fauna_rng') == rng(seed)
        assert byte(s, 'travel_pending') == 22
        assert abs(fp(s.step(L.peek('s_elap', 5)).data) - elapsed - 5/60) < 1e-6
        assert 'THREAT NO LONGER HERE' in ' '.join(rows(s)), rows(s)
        assert '> REVIEW ROUTE / RESUME' in ' '.join(rows(s)), rows(s)
        after = snapshot(s)
        event(s, 'ok', READY)
        assert byte(s, 'threat_context') == 0
        assert snapshot(s) == after
        assert 'PLAN A DIRECTION - SELECT DESTINATION' in ' '.join(rows(s)), rows(s)
        event(s, 'cancel', READY)
        assert 'RETURN PLAN  ESC VIEW' in ' '.join(rows(s)), rows(s)
        event(s, 'cancel', IDLE)
        assert byte(s, 'travel_pending') == 22
        assert snapshot(s) == after


def resolved_rest(disk):
    with GamePortSession(disk, menu=False) as s:
        boot(s)
        # A real one-minute REST crosses the native 60-minute encounter age
        # boundary; its bear reaction interrupts the proposed camp rest.
        prepare(s, 6, seed_for((0, 6), (0, 52)))
        s.step(L.poke('animal_age', 59))
        grid(s, 'REST', ready=READY)
        while True:
            current = int.from_bytes(s.step(L.peek('input_value', 2)).data, 'little')
            if current == 1:
                break
            event(s, duration_control(current, 1), READY)
        s.step(L.poke('dep_running', 0x84))
        s.step(L.poke('camp_pending', 0xC5))
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        event(s, 'ok', L.until('module_threat', 60000))
        assert byte(s, 'animal_kind') == 6
        assert any(s.step(L.peek('injury_active', 13)).data)
        assert abs(fp(s.step(L.peek('s_elap', 5)).data) - elapsed - 1/60) < 1e-6
        assert byte(s, 'threat_context') == 2
        # Fix only the next native SCARE draw after the real interruption.
        s.step(L.poke('fauna_rng', seed_for((0, 129))))
        before = snapshot(s)
        s.step(READY)
        assert snapshot(s) == before
        choose(s, 1)
        assert 'REST KEPT' in ' '.join(rows(s)), rows(s)
        event(s, 'ok', READY)
        assert byte(s, 'animal_kind') == 0
        assert '> REVIEW REST / CAMP' in ' '.join(rows(s)), rows(s)
        after = snapshot(s)
        event(s, 'ok', READY)
        assert 'PREPARE NIGHT' in ' '.join(rows(s)), rows(s)
        assert byte(s, 'threat_context') == 0
        assert byte(s, 'dep_running') != 0x84
        assert not byte(s, 'camp_pending') & 0x80
        assert snapshot(s) == after
        event(s, 'cancel', IDLE)
        assert snapshot(s) == after


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        inspection_and_failure(disk)
        fire_before_flee(disk)
        resolved_trip(disk)
        resolved_rest(disk)
    print('Threat: atomic inspection, native failed/successful SCARE, retained route/rest review: OK')
