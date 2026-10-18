#!/usr/bin/env python3
"""A nearby tracked point offers one paid native half-step and inert cancel."""
import tempfile
from common import HERE, L, a2test, disk_with, fp, state, text_screen
from test_thermal import poke
from test_joystick_journey import GamePortSession, saved_state, event, grid


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
            s.step(L.poke('route_x', 11))
            s.step(L.poke('route_y', 10))
            s.step(L.poke('route_active', 1))
            before = saved_state(s)
            s.step('key:SWIM\r')
            s.step(ready)
            screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert 'ONE NATIVE STEP' in screen and '11,10 1.0 CELLS' in screen, screen
            s.step('press:\\e')
            s.step('wait:1')
            s.step(idle)
            assert saved_state(s) == before
            # Readjusting opens the existing planner, with no walk continuation
            # hiding below its return address. Cancelling preserves the world.
            s.step('key:SWIM\r')
            s.step(ready)
            event(s, 'right', ready)
            event(s, 'ok', L.until('nav_key', 6000))
            event(s, 'cancel', ready)
            event(s, 'cancel', idle)
            assert saved_state(s) == before
            elapsed = fp(s.step(L.peek('s_elap', 5)).data)
            for expected_x, distance in (((10 << 8) + 128, '0.5'), (11 << 8, '0.0')):
                s.step('key:SWIM\r')
                s.step(ready)
                s.step('press:\\r')
                s.step('wait:1')
                s.step(idle)
                assert state(s.step(L.peek('px', 6)).data) == (expected_x, 10 << 8, 140)
                now = fp(s.step(L.peek('s_elap', 5)).data)
                assert now > elapsed
                elapsed = now
                screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
                assert f'11,10 {distance} CELLS' in screen, screen
            before = saved_state(s)
            s.step('key:SWIM\r')
            s.step('wait:1')
            s.step(idle)
            assert saved_state(s) == before
            screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert 'AT TARGET' in screen, screen
    print('Tracked arrival: fractional distance, inert cancel, paid half-steps, exact arrival: OK')
    joystick_near_walk()


def joystick_near_walk():
    m = bytearray((HERE / 'build/map.bin').read_bytes())
    m[2:8] = (10 << 8).to_bytes(2, 'little') * 2 + (140).to_bytes(2, 'little')
    m[8:10] = bytes((80, 70))
    m[10] = 0
    m[13:16] = bytes((60, 60, 0))
    m[23] = 100  # Isolate the navigation gesture from random encounters.
    m[64:] = bytes([10]) * 9408
    idle = L.until('idle', 20000)
    ready = L.until('keyboard_wait', 6000)
    with tempfile.TemporaryDirectory() as tmp:
        with GamePortSession(disk_with(tmp, m)) as s:
            s.step(L.until('game_start', 20000))
            s.step(L.poke('scenes_enabled', 0))
            s.step(idle)
            s.step(L.poke('nature_frequency', 0))
            s.step(L.poke('route_x', 11))
            s.step(L.poke('route_y', 10))
            s.step(L.poke('route_active', 1))
            assert s.step(L.peek('travel_pending')).data == bytes((0,))
            before = saved_state(s)
            rng = s.step(L.peek('weather_seed', 4)).data
            # Enter WALK from the real game-port grid. A tracked target
            # without a pending trip must open the short native-step offer.
            grid(s, 'WALK', ready=ready)
            screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert 'ONE NATIVE STEP' in screen and '11,10 1.0 CELLS' in screen, screen
            assert saved_state(s) == before and s.step(L.peek('weather_seed', 4)).data == rng
            event(s, 'cancel', idle)
            assert saved_state(s) == before and s.step(L.peek('weather_seed', 4)).data == rng
            elapsed = fp(s.step(L.peek('s_elap', 5)).data)
            grid(s, 'WALK', ready=ready)
            event(s, 'ok', idle)
            assert state(s.step(L.peek('px', 6)).data) == ((10 << 8) + 128, 10 << 8, 140)
            assert fp(s.step(L.peek('s_elap', 5)).data) > elapsed
            screen = '\n'.join(text_screen(s.step('peek:0400:1024').data))
            assert '11,10 0.5 CELLS' in screen, screen
    print('Tracked WALK game port: near-step offer reachable, cancel inert, acceptance pays one native half-step: OK')


if __name__ == '__main__':
    main()
