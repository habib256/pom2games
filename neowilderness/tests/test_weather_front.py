#!/usr/bin/env python3
"""Front timeline, visibility/cadence and Lehmer state against original ROM."""
import json
import subprocess
import sys
from common import HERE, L, DISK, a2test, fp
from gendata import fp as encode
from test_thermal import call, poke
from test_weather_cycle import probe_disk

SEEDS = [1, 2, 8191, 8192, 67099546, 66279098, 1234567]
CASES = [(t, span, short, old_short) for t in
         (0, 150, 190, 200, 229, 230, 231, 250, 270, 300, 350, 355, 356)
         for span, short, old_short in ((125, 0, 0), (90, 1, 0), (125, 0, 1))]


def wind_walk(original):
    cases = [(seed,wind,maximum) for seed in SEEDS for wind in (0,1,2,3,7,29,30,255)
             for maximum in (2,30)]
    idle = L.until('idle',20000); done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle]+call(['env_hour'])+[done,idle]+call(['weather_step'])
    for seed,wind,maximum in cases:
        steps += [L.poke('weather_seed',b,i) for i,b in enumerate(seed.to_bytes(4,'little'))]
        steps += [L.poke('wind',wind),f'poke:700F:{maximum:02X}']
        steps += poke('s_step',0)+poke('weather_clock',0)+poke('weather_start',1000)
        steps += poke('weather_previous',-1000)
        steps += [done,L.peek('wind'),L.peek('weather_seed',4),idle]
    r = a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=900)
    actual = [(r.mem(L['wind'],1,k)[0],r.mem(L['weather_seed'],4,k)) for k in range(len(cases))]
    if original:
        module = (HERE/'build/re_env/ch/t0As0C.bin').read_bytes()
        rng = (HERE/'build/re/smalldos_lo.bin').read_bytes()[0x21:0x9D]
        # Stop after the wind store, before the independent front timeline.
        disk = probe_disk(HERE/'build/re_weather_wind_walk',module,bytes.fromhex('20 64 58 4C 00 08'),
                          [('RNG',rng,0x0321),('RETURN',b'\x60',0x5898)])
        steps = ['until:0800:20000']
        for seed,wind,maximum in cases:
            steps += [f'poke:{0x03B9+i:04X}:{b:02X}' for i,b in enumerate(seed.to_bytes(4,'little'))]
            steps += [f'poke:4B9F:{wind:02X}',f'poke:60B9:{maximum:02X}',
                      'until:0803:1000','peek:4B9F:1','peek:03B9:4','until:0800:1000']
        native = a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=900)
        for k,(case,value) in enumerate(zip(cases,actual)):
            expected = native.mem(0x4B9F,1,k)[0],native.mem(0x03B9,4,k)
            assert value == expected,(case,value,expected)
    assert all(2 <= value[0] <= case[2] for case,value in zip(cases,actual))
    print(f'{len(cases)} wind random-walk/clamping cases OK'+(' (native ROM)' if original else ''))


def main():
    original = '--original' in sys.argv
    idle = L.until('idle', 20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle] + call(['env_hour']) + [done, idle] + call(['weather_random'])
    expected = []
    for seed in SEEDS:
        steps += [L.poke('weather_seed', b, i) for i, b in enumerate(seed.to_bytes(4, 'little'))]
        for _ in range(8):
            seed = seed * 8192 % 67099547
            expected.append(seed)
            steps += [done, L.peek('weather_seed', 4), 'peek:009D:6', idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    states = [int.from_bytes(r.mem(L['weather_seed'], 4, i), 'little') for i in range(len(expected))]
    assert states == expected, list(zip(states, expected))
    # FAC has an unpacked mantissa; normalize through a tiny MOVMF driver
    # for native RNG comparison rather than decoding the live accumulator.
    steps = [idle] + call(['env_hour']) + [done, idle] + call(['weather_front', 'weather_conditions'])
    end = f'until:{L["idle"]+6:04X}:6000'
    for t, span, short, old_short in CASES:
        steps += poke('weather_clock', t) + poke('weather_start', 231) + poke('weather_previous', -150)
        steps += poke('weather_frequency', 3.5)
        steps += [L.poke('weather_seed', b, i) for i, b in enumerate((1).to_bytes(4,'little'))]
        steps += [L.poke('weather_duration', span), L.poke('weather_duration', 0, 1),
                  L.poke('weather_previous_duration', 100), L.poke('weather_previous_duration', 0, 1),
                  L.poke('weather_short', short), L.poke('weather_previous_short', old_short),
                  L.poke('airtemp', 42), end, L.peek('weather_cap', 3),
                  L.peek('weather_sky', 1), L.peek('weather_trend', 1),
                  L.peek('weather_inside_front', 1),
                  L.peek('weather_start', 14), L.peek('weather_seed', 4), idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    # cap (2), visibility, sky, trend, inside_front: read by label, since
    # weather_day_level sits between visibility and sky in the engine.
    observations = [r.mem(L['weather_cap'], 3, i) + r.mem(L['weather_sky'], 1, i)
                    + r.mem(L['weather_trend'], 1, i) + r.mem(L['weather_inside_front'], 1, i)
                    for i in range(len(CASES))]
    timelines = [r.mem(L['weather_start'], 14, i) for i in range(len(CASES))]
    seeds = [r.mem(L['weather_seed'], 4, i) for i in range(len(CASES))]
    if original:
        out = HERE / 'build/re_weather_front'
        module = bytearray((HERE / 'build/re_env/ch/t0As0C.bin').read_bytes())
        rng = (HERE / 'build/re/smalldos_lo.bin').read_bytes()[0x21:0x9D]
        disk = probe_disk(out, module, bytes.fromhex('20 B6 58 20 1D 5A 4C 00 08'), [('RNG', rng, 0x0321)])
        steps = ['until:0800:20000', 'poke:4B49:FF', 'poke:00D4:00', 'poke:60A1:00']
        for t, span, short, old_short in CASES:
            for addr, data in ((0xF6, encode(t)), (0x4C9D, encode(231)), (0x4CA2, encode(-150)),
                               (0x4BFE, span.to_bytes(2, 'little')), (0x4C00, (100).to_bytes(2, 'little')),
                               (0x4B7F, bytes([short])), (0x4B7E, bytes([old_short])),
                               (0x4C43, encode(3.5)), (0x03B9, (1).to_bytes(4,'little')),
                               (0x4C0C, (40).to_bytes(2, 'little')), (0x4B9B, bytes([42]))):
                steps += [f'poke:{addr+i:04X}:{b:02X}' for i, b in enumerate(data)]
            steps += ['until:0806:1000', 'peek:4C1C:2', 'peek:4B91:1', 'peek:4B4C:2',
                      'peek:4B06:1', 'peek:4C9D:10', 'peek:4BFE:2', 'peek:4C00:2',
                      'peek:03B9:4', 'until:0800:1000']
        native = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
        values = []
        for i in range(len(CASES)):
            # Native front presence is 1 before and 2 inside; port stores 0/1.
            sky_phase = native.mem(0x4B4C, 2, i)
            values.append(native.mem(0x4C1C, 2, i) + native.mem(0x4B91, 1, i) +
                          sky_phase[:1] + native.mem(0x4B06, 1, i) + bytes([sky_phase[1]-1]))
        assert observations == values, [(c, a.hex(), b.hex()) for c, a, b in zip(CASES, observations, values) if a != b]
        for i, case in enumerate(CASES):
            native_timeline = native.mem(0x4C9D, 10, i)+native.mem(0x4BFE, 2, i)+native.mem(0x4C00, 2, i)
            assert timelines[i] == native_timeline, (case, timelines[i].hex(), native_timeline.hex())
            assert seeds[i] == native.mem(0x03B9, 4, i), (case, seeds[i].hex(), native.mem(0x03B9, 4, i).hex())
        (out / 'results.json').write_text(json.dumps([
            dict(case=c, state=v.hex()) for c, v in zip(CASES, values)], indent=2)+'\n')
    assert all(24 <= v[2] <= 240 and int.from_bytes(v[:2], 'little') in (30,120,360) for v in observations)
    print(f'{len(expected)} Lehmer states and {len(CASES)} front/visibility/health-cap cases OK' +
          (' (fronts compared to original ROM)' if original else ''))
    wind_walk(original)


if __name__ == '__main__':
    main()
