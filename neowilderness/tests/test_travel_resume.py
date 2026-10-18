#!/usr/bin/env python3
"""A native swimming step cannot overspend; explicit resume/cancel is inert."""
import tempfile
from common import HERE, L, a2test, disk_with, fp, state, text_screen
from test_thermal import poke
from test_shore import lake, command as shore_command, terrain
from test_joystick_journey import GamePortSession, event, grid, saved_state


def main():
    m = bytearray((HERE / 'build/map.bin').read_bytes())
    m[2:8] = (10 << 8).to_bytes(2, 'little') * 2 + (140).to_bytes(2, 'little')
    m[8:10] = bytes((80, 70))
    m[10] = 0
    m[13:16] = bytes((60, 60, 0))
    m[64:] = bytes([128]) * 9408
    idle = L.until('idle', 20000)
    ready = L.until('keyboard_wait', 6000)
    with tempfile.TemporaryDirectory() as tmp:
        with a2test.Session(disk_with(tmp, m)) as s:
            s.step(L.until('game_start', 20000))
            s.step(L.poke('scenes_enabled', 0))
            s.step(idle)
            for op in poke('s_health', 4):
                s.step(op)
            s.step('key:SWIM\r')
            s.step(ready)
            s.step('key:1\r')
            s.step('wait:1')
            s.step(idle)
            position = s.step(L.peek('px', 6)).data
            elapsed = s.step(L.peek('s_elap', 5)).data
            assert state(position) == ((10 << 8)+128, 10 << 8, 140)
            assert abs(fp(elapsed)*60-39) < 1e-5
            assert s.step(L.peek('travel_remaining', 2)).data == bytes((21, 0))
            assert s.step(L.peek('travel_next_minutes')).data == bytes((28,))
            screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert 'LEFT 21 MIN.' in screen and 'NEXT STEP 28 MIN.' in screen, screen
            s.step('key:SAVE 1\r')
            s.step(idle)
            # A resource alert from the previous action cannot masquerade
            # as a fresh encounter when the next whole step will not fit.
            s.step(L.poke('travel_next_minutes', 0))
            s.step(L.poke('fauna_alert', 1))
            animal = s.step(L.peek('animal_kind')).data
            s.step('key:SWIM\r')
            s.step(ready)
            s.step('press:\\r')
            s.step('wait:1')
            s.step(idle)
            assert s.step(L.peek('px', 6)).data == position
            assert s.step(L.peek('s_elap', 5)).data == elapsed
            assert s.step(L.peek('used', 2)).data == bytes((0, 0))
            assert s.step(L.peek('travel_reason')).data == bytes((9,))
            assert s.step(L.peek('fauna_alert')).data == bytes((0,))
            assert s.step(L.peek('animal_kind')).data == animal
            s.step('key:SWIM\r')
            s.step(ready)
            screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert 'NEXT STEP NEEDS 28 MIN' in screen, screen
            s.step('press:\\e')
            s.step('wait:1')
            s.step(idle)
            assert s.step(L.peek('px', 6)).data == position
            assert s.step(L.peek('s_elap', 5)).data == elapsed
            assert s.step(L.peek('travel_remaining', 2)).data == bytes((21, 0))
            # A rotated heading does not silently redirect a resumed trip.
            s.step(L.poke('heading', 0))
            s.step('key:SWIM\r')
            s.step(ready)
            s.step('press:\\r')
            s.step('wait:1')
            s.step(idle)
            assert state(s.step(L.peek('px', 6)).data) == (11 << 8, 10 << 8, 140)
            assert abs(fp(s.step(L.peek('s_elap', 5)).data)*60-67) < 1e-5
            assert s.step(L.peek('travel_pending')).data == b'\0'
            s.step('key:RESTORE 1\r')
            s.step(idle)
            assert s.step(L.peek('px', 6)).data == position
            assert s.step(L.peek('travel_pending')).data == b'\0'
    with tempfile.TemporaryDirectory() as tmp:
        with GamePortSession(disk_with(tmp, m)) as s:
            s.step(L.until('game_start', 20000))
            s.step(L.poke('scenes_enabled', 0))
            s.step(idle)
            for op in poke('s_health', 4):
                s.step(op)
            grid(s, 'SWIM', ready=ready)
            assert s.step(L.peek('input_value', 2)).data == bytes((60, 0))
            event(s, 'ok', idle)
            before = saved_state(s)
            grid(s, 'SWIM', ready=ready)
            event(s, 'cancel', idle)
            assert saved_state(s) == before
            grid(s, 'SWIM', ready=ready)
            event(s, 'right')
            assert 'NEW TRIP?' in '\n'.join(text_screen(s.step('peek:0400:1024').data))
            event(s, 'cancel', idle)
            assert saved_state(s) == before
            grid(s, 'SWIM', ready=ready)
            event(s, 'right')
            event(s, 'right')
            assert 'ABANDON TRIP?' in '\n'.join(text_screen(s.step('peek:0400:1024').data))
            event(s, 'cancel', idle)
            assert saved_state(s) == before
            grid(s, 'SWIM', ready=ready)
            event(s, 'ok', idle)
            assert state(s.step(L.peek('px', 6)).data) == (11 << 8, 10 << 8, 140)
            assert s.step(L.peek('travel_pending')).data == b'\0'
    with tempfile.TemporaryDirectory() as tmp:
        mixed = lake()
        with a2test.Session(disk_with(tmp, mixed)) as s:
            s.step(idle)
            bank, t0, _ = shore_command(s, 'WALK 1 H')
            assert not terrain(mixed, bank)
            assert s.step(L.peek('travel_pending')).data != b'\0'
            s.step('key:SWIM\r')
            s.step(ready)
            s.step('press:\\r')
            s.step('wait:1')
            s.step(idle)
            approach = state(s.step(L.peek('px', 6)).data)
            assert approach != bank
            assert fp(s.step(L.peek('s_elap', 5)).data)*60 > t0
            far, t1, message = shore_command(s, 'SWIM 4 H')
            assert not terrain(mixed, far) and 'REACHED LAND' in message
            assert s.step(L.peek('travel_pending')).data != b'\0'
            s.step('key:WALK\r')
            s.step(ready)
            s.step('press:\\r')
            s.step('wait:1')
            s.step(ready)
            s.step("key:\\e")
            s.step("wait:1")
            s.step(idle)
            inland = state(s.step(L.peek('px', 6)).data)
            assert inland != far and not terrain(mixed, inland)
            assert fp(s.step(L.peek('s_elap', 5)).data)*60 > t1
    print('Travel: strict budget, visible remainder/next step, inert cancel and explicit resume: OK')


if __name__ == '__main__':
    main()
