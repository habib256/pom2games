#!/usr/bin/env python3
"""Shared minute selector: joystick edits/cancel and confirmed activity memory."""
import tempfile
from common import DISK, L, HERE, disk_with
from test_guidance import start, state
from test_joystick_journey import GamePortSession, event, grid, rows, IDLE, READY


def word(s, name):
    return int.from_bytes(s.step(L.peek(name, 2)).data, 'little')


def disk_selector():
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        # Activity memories are UI state, deliberately outside SAVE.
        for memory in ('duration_rest', 'duration_wait'):
            s.step(L.poke(memory, 61))
            s.step(L.poke(memory, 0, 1))
        before = state(s)
        for action in ('REST', 'WAIT'):
            memory = 'duration_rest' if action == 'REST' else 'duration_wait'
            grid(s, action, ready=READY)
            assert 'DURATION 61 MIN' in ' '.join(rows(s)), rows(s)
            event(s, 'right')
            event(s, 'up')
            assert word(s, 'input_value') == 120
            event(s, 'left')
            event(s, 'down')
            assert word(s, 'input_value') == 60
            event(s, 'down')
            assert word(s, 'input_value') == 30
            assert state(s) == before, 'Duration editing advances simulation or RNG'
            event(s, 'cancel', IDLE)
            assert word(s, memory) == 61, 'Cancel remembers an unconfirmed edit'
            assert state(s) == before
            assert 'ACTION CANCELLED.' in ' '.join(rows(s)), rows(s)
        grid(s, 'WAIT', ready=READY)
        event(s, 'right')
        event(s, 'ok', IDLE)
        assert word(s, 'duration_wait') == 62
        before_default = state(s)
        grid(s, 'REST', ready=READY)
        assert word(s, 'input_value') == 61, rows(s)
        event(s, 'ok', IDLE)  # no numeric key: RETURN confirms the recalled default
        assert word(s, 'duration_rest') == 61
        assert word(s, 'duration_wait') == 62
        assert state(s) != before_default, 'Confirming the default must execute the native command'
        grid(s, 'WAIT', '1 MIN', ready=IDLE)
        assert word(s, 'duration_wait') == 1
        grid(s, 'WALK', ready=READY)
        assert word(s, 'input_value') == 60, 'WAIT duration leaked into the travel family'
        event(s, 'cancel', IDLE)

    print('Duration: separate REST/WAIT memories; fine/fast editing inert; cancel preserves last confirmation')


def preset_bounds():
    presets = (1, 5, 10, 20, 30, 60, 120, 240, 480, 960, 1440,
               2880, 5760, 10080, 15300)
    with GamePortSession(DISK, menu=False) as s:
        start(s)
        s.step(L.poke('duration_wait', 1))
        s.step(L.poke('duration_wait', 0, 1))
        before = state(s)
        grid(s, 'WAIT', ready=READY)
        event(s, 'down')
        event(s, 'left')
        assert word(s, 'input_value') == 1
        for expected in presets[1:]:
            event(s, 'up')
            assert word(s, 'input_value') == expected
        event(s, 'up')
        event(s, 'right')
        assert word(s, 'input_value') == 15300
        for expected in reversed(presets[:-1]):
            event(s, 'down')
            assert word(s, 'input_value') == expected
        assert state(s) == before
        event(s, 'cancel', IDLE)
        assert word(s, 'duration_wait') == 1
        assert state(s) == before
    print('Duration: quick presets are ordered, bounded and inert; minute edits clamp at endpoints')


def travel_selectors():
    for terrain, verb in ((10, 'WALK'), (128, 'SWIM')):
        m = bytearray((HERE / 'build/map.bin').read_bytes())
        m[2:8] = (10 << 8).to_bytes(2, 'little') * 2 + (140).to_bytes(2, 'little')
        m[8:10] = bytes((80, 70))
        m[10] = 0
        m[13:16] = bytes((60, 60, 0))
        m[64:] = bytes([terrain]) * 9408
        with tempfile.TemporaryDirectory() as tmp:
            with GamePortSession(disk_with(tmp, m)) as s:
                s.step(L.until('game_start', 20000))
                s.step(L.poke('scenes_enabled', 0))
                s.step(IDLE)
                s.step(L.poke('duration_last', 77))
                s.step(L.poke('duration_last', 0, 1))
                before = state(s)
                grid(s, verb, ready=READY)
                assert word(s, 'input_value') == 77, rows(s)
                event(s, 'right')
                event(s, 'up')
                assert word(s, 'input_value') == 120
                assert state(s) == before
                event(s, 'cancel', IDLE)
                assert word(s, 'duration_last') == 77
                assert state(s) == before
                assert 'ACTION CANCELLED.' in ' '.join(rows(s)), rows(s)
    print('Duration: WALK/SWIM share remembered minute selector; editing/cancel preserve simulation and RNG')


def main():
    disk_selector()
    preset_bounds()
    travel_selectors()


if __name__ == '__main__':
    main()
