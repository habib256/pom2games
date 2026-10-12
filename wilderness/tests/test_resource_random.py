#!/usr/bin/env python3
"""Stationary resource rolls share the native wind/compass random timeline."""
import sys
from common import HERE, L, DISK, a2test
from test_thermal import call
from test_weather_cycle import probe_disk


def main():
    seeds = (1, 2, 66279098, 9080894, 44385572, 1234567, 67099546)
    environments = ((34, 7, 10, 60, 0, 31), (34, 7, 40, 60, 0, 31),
                    (34, 7, 10, 60, 31, 31), (34, 23, 10, 60, 0, 31),
                    (34, 7, 10, 60, 0, 0), (34, 7, 10, 120, 0, 31))
    cases = [(seed, env, verb) for seed in seeds for env in environments
             for verb in (12, 19, 20, 21)]
    idle = L.until('idle', 20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle]+call(['env_hour'])+[done, idle]
    steps += call(['stationary_resources'])+[done, idle]+call(['resource_scan'])
    for seed, env, verb in cases:
        steps += [L.poke('weather_seed', b, i) for i, b in enumerate(seed.to_bytes(4, 'little'))]
        steps += [L.poke('fauna_env', b, i) for i, b in enumerate(env)]
        steps += [L.poke('act', 2), L.poke('verb', verb), L.poke('resource_seen', 0),
                  done, L.peek('weather_seed', 4), idle]
    port = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    if '--original' in sys.argv:
        rng = (HERE/'build/re/smalldos_lo.bin').read_bytes()[0x21:0x9D]
        module = (HERE/'build/re_surv/m0A5.bin').read_bytes()
        disk = probe_disk(HERE/'build/re_resource_random', module,
                          bytes.fromhex('A2 05 A0 07 20 1F 5D 4C 00 08'), [('RNG', rng, 0x0321)])
        steps = ['until:0800:20000', 'poke:000A:00', 'poke:4B75:00', 'poke:603F:04']
        for seed, env, verb in cases:
            steps += [f'poke:{0x03B9+i:04X}:{b:02X}' for i, b in enumerate(seed.to_bytes(4, 'little'))]
            steps += [f'poke:{0x4ADA+i:04X}:{b:02X}' for i, b in enumerate(env)]
            steps += [f'poke:0003:{verb:02X}', 'until:0807:1000', 'peek:03B9:4', 'until:0800:1000']
        native = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
        for i, case in enumerate(cases):
            assert port.mem(L['weather_seed'], 4, i) == native.mem(0x03B9, 4, i), case
    else:
        assert all(int.from_bytes(port.mem(L['weather_seed'], 4, i), 'little') == seed
                   for i, (seed, env, verb) in enumerate(cases) if verb in (20, 21))
    print(f'{len(cases)} resource eligibility/action/RNG cases OK'+(' (native ROM)' if '--original' in sys.argv else ''))


if __name__ == '__main__':
    main()
