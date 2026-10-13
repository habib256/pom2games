#!/usr/bin/env python3
"""Sierra monthly precipitation frequency, optionally against original ROM."""
import sys
from common import HERE, L, DISK, a2test, fp
from gendata import fp as encode
from test_thermal import call, poke
from test_weather_cycle import probe_disk


def main():
    dates = [k/24 for k in range(24)]
    idle = L.until('idle', 20000)
    done = f'until:{L["idle"]+3:04X}:6000'
    steps = [idle] + call(['env_hour']) + [done, idle] + call(['weather_daily'])
    for date in dates:
        steps += poke('s_date', date) + [done, L.peek('weather_frequency', 5), idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    values = [r.mem(L['weather_frequency'], 5, i) for i in range(len(dates))]
    assert all(.1 <= fp(v) <= 6.2 for v in values)
    if '--original' in sys.argv:
        out = HERE/'build/re_weather_frequency'
        disk = probe_disk(out, (HERE/'build/re_env/ch/t0Cs03.bin').read_bytes(),
                          bytes.fromhex('20 E6 59 4C 00 08'))
        steps = ['until:0800:20000', 'poke:601F:1F']
        for addr, data in ((0x60B0, bytes.fromhex('02003C002F00')), (0x4C52, encode(1))):
            steps += [f'poke:{addr+i:04X}:{b:02X}' for i, b in enumerate(data)]
        for date in dates:
            steps += [f'poke:{0x4C89+i:04X}:{b:02X}' for i, b in enumerate(encode(date))]
            steps += ['until:0803:1000', 'peek:4C43:5', 'until:0800:1000']
        r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
        native = [r.mem(0x4C43, 5, i) for i in range(len(dates))]
        assert values == native, [(d, a.hex(), b.hex()) for d, a, b in zip(dates, values, native) if a != b]
    print('24 Sierra precipitation frequencies OK'+(' (byte-exact original ROM)' if '--original' in sys.argv else ''))


if __name__ == '__main__':
    main()
