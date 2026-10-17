#!/usr/bin/env python3
"""Gauge semantics, native boundaries and captions via game-port navigation."""
import math
import re
import tempfile
from common import L, disk_with
from test_forest import map_fixture
from test_fit_quantities import boot
from test_thermal import poke
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, IDLE

CAPTIONS = {9: 'HIGH BARS = BETTER RESERVES'}


def put(s, name, value):
    for step in poke(name, value):
        s.step(step)


def open_status(s):
    event(s, 'up')
    screen = rows(s)
    for row, label in ((3, 'HEALTH'), (4, 'ENERGY'), (5, 'MEAL'),
                       (6, 'WATER'), (7, 'BODY')):
        assert label in screen[row][:41], (row, screen[row])
    for row, text in CAPTIONS.items():
        assert text in screen[row][:41], (row, text, screen[row])
        assert len(screen[row]) == 80
    assert 'MEDICAL' in screen[15] and 'LOCAL' in screen[2]
    return screen


def gauge(screen, row, cells, percent, word=''):
    line = screen[row][:41]
    assert line.count('─') == cells and line.count('▒') == 10-cells, line
    assert re.search(rf'\b{percent}%', line), line
    if word:
        assert word in line, line


def hours_cells(hours):
    return max(0, min(10, 10-math.floor(hours*2/3)))


def main():
    with tempfile.TemporaryDirectory() as tmp, GamePortSession(disk_with(tmp, map_fixture()), menu=False) as s:
        boot(s)
        open_status(s); event(s, 'cancel', IDLE)
        put(s, 'f_hmax', 100)
        for health in (0, 4.4, 4.6, 14.4, 14.6, 19.9, 20.1, 39.9, 40.1, 59.9, 60.1, 79.9, 80.1, 100):
            put(s, 's_health', health)
            screen = open_status(s)
            percent = math.floor(health+.5)
            gauge(screen, 3, min(10, (percent+5)//10), percent)
            condition = ('MISERABLE', 'POOR', 'OKAY', 'GOOD', 'FANTASTIC')[min(4, int(health/20))]
            assert condition in screen[2], (health, condition, screen[2])
            event(s, 'cancel', IDLE)
        for maximum, health, percent, condition in ((200, 150, 75, 'GOOD'), (50, 25, 50, 'OKAY')):
            put(s, 'f_hmax', maximum); put(s, 's_health', health)
            screen = open_status(s)
            gauge(screen, 3, min(10, (percent+5)//10), percent)
            assert condition in screen[2], (maximum, health, screen[2])
            event(s, 'cancel', IDLE)
        put(s, 'f_hmax', 100)
        print('  Health share, varying maximum, rounding, ten cells and condition thresholds: 16 cases OK', flush=True)
        put(s, 's_health', 100)
        for rest, debt in ((0, -3), (0, 0), (0, 1.4), (0, 1.6), (0, 7),
                           (0, 7.1), (0, 12), (0, 12.1), (0, 15), (16, 0), (16.1, 0)):
            put(s, 's_rest', rest); put(s, 's_defr', debt)
            screen = open_status(s)
            cells = 0 if rest > 16 else hours_cells(debt)
            word = 'BEAT' if rest > 16 else 'TIRED' if debt > 12 else 'OKAY' if debt > 7 else 'GREAT'
            gauge(screen, 4, cells, 10*cells, word)
            event(s, 'cancel', IDLE)
        print('  Rest debt scale, negative credit, labels and >16-hour exhaustion override: 11 cases OK', flush=True)
        put(s, 's_rest', 0); put(s, 's_defr', 0)
        for name, row in (('s_eat', 5), ('s_drink', 6)):
            for hours in (0, 1.4, 1.6, 6, 6.1, 12, 12.1, 15, 18):
                put(s, name, hours)
                screen = open_status(s)
                cells = hours_cells(hours)
                word = 'VERY' if hours > 12 else 'SO-SO' if hours > 6 else 'OKAY'
                gauge(screen, row, cells, 10*cells, word)
                event(s, 'cancel', IDLE)
        print('  Meal/drink recency, six/twelve-hour words and empty scale: 18 cases OK', flush=True)
        for body, mode, label in ((95, 2, 'SHIVERING'), (98.6, 0, ''), (98.6, 2, 'SHIVERING'), (101, 1, 'SWEATING')):
            put(s, 's_body', body); s.step(L.poke('thermal_mode', mode))
            screen = open_status(s)
            assert f'{body:.1f}F' in screen[7], screen[7]
            assert '%' not in screen[7] and label in screen[7]
            if not mode:
                assert 'SHIVERING' not in screen[7] and 'SWEATING' not in screen[7]
            event(s, 'cancel', IDLE)
        print('  Body heat is Fahrenheit with its reference and thermal sign: 4 cases OK', flush=True)
        # Entering and leaving the care focus must keep every caption and state.
        s.step(L.poke('injury_active', 1, 0))
        open_status(s)
        before = saved_state(s)
        event(s, 'down'); event(s, 'right'); event(s, 'left'); event(s, 'up')
        assert byte(s, 'pg_focus') == 0
        for row, text in CAPTIONS.items():
            assert text in rows(s)[row][:41]
        event(s, 'cancel', IDLE)
        assert saved_state(s) == before
        open_status(s)
        assert saved_state(s) == before
        print('  Captions remain legible while browsing/cancelling care, without stock/time/RNG writes: OK', flush=True)
    print('STATUS gauges: OK')


if __name__ == '__main__':
    main()
