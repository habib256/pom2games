#!/usr/bin/env python3
"""Native arithmetic and nighttime redraw optimization contracts."""
import re
from common import HERE, DISK, L, a2test


def division():
    entry = L['idle']
    address = L['smalldiv']
    # Execute actual resident code; capture A and the preserved X/Y registers.
    code = bytes((0xA9, 0, 0xA2, 0x5A, 0xA0, 0xA5,
                  0x20, address & 255, address >> 8,
                  0x8D, 0, 0x95, 0x8E, 1, 0x95, 0x8C, 2, 0x95,
                  0x4C, entry & 255, entry >> 8))
    count = 0
    for first in range(1, 129, 16):
        cases = [(n, r) for n in range(first, first + 16) for r in range(n)]
        steps = [L.until('idle', 20000)]
        steps += [f'poke:{entry+i:04X}:{b:02X}' for i, b in enumerate(code)]
        for n, r in cases:
            steps += [f'poke:{entry+1:04X}:{r:02X}', L.poke('divisor', n),
                      L.poke('qlo', 0xA7), f'until:{entry+18:04X}:100',
                      'peek:9500:3', L.peek('qlo'), L.until('idle', 100)]
        result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=180)
        for i, (n, r) in enumerate(cases):
            expected = r * 256 // n
            assert result.mem(0x9500, 3, i) == bytes((expected, 0x5A, 0xA5)), (n, r)
            assert result.mem(L['qlo'], 1, i) == bytes((expected,)), (n, r, 'qlo')
        count += len(cases)
    print(f'  {count} native divisions: exact quotient, qlo and preserved X/Y: OK')


def loader_decode():
    """NEOWILD.SYSTEM's LZ decoder, re-entered after boot on crafted streams.

    The loader ran in the SIM window; put its image back there, place each
    stream at STAGE ($2000) and decode to a page-crossing destination:
    literals, distance-1 runs, 255-byte matches and the 4095-byte window.
    """
    import random
    from pack_boot import compress
    image = (HERE / 'build/NEOWILD.SYSTEM').read_bytes()
    size = int(re.search(r'^LOADER\s+[0-9A-F]{6}\s+[0-9A-F]{6}\s+([0-9A-F]{6})',
                         (HERE / 'build/wild.map').read_text(), re.M).group(1), 16)
    loader = image[-size:]                     # NEOWILD.SYSTEM = stub + loader
    entry = L['idle']
    rng = random.Random(4095)
    seed = rng.randbytes(4095)
    cases = [rng.randbytes(300), bytes(600), bytes(range(256)) * 3 + b'xyz' * 40,
             seed + seed[:255], seed[:17] * 30]
    steps = [L.until('idle', 20000)]
    steps += [f'poke:{0x9600+i:04X}:{b:02X}' for i, b in enumerate(loader)]
    expected = []
    for k, data in enumerate(cases):
        dest = (0x7100, 0x71FD)[k % 2]
        stream = compress(data)
        steps += [f'poke:{0x2000+i:04X}:{b:02X}' for i, b in enumerate(stream)]
        steps += [L.poke('hdr', len(data), 3), L.poke('hdr', len(data) >> 8, 4)]
        code = bytes((0xA9, dest & 255, 0xA2, dest >> 8, 0x20, L['ld_decode'] & 255,
                      L['ld_decode'] >> 8, 0x4C, entry & 255, entry >> 8))
        steps += [f'poke:{entry+i:04X}:{b:02X}' for i, b in enumerate(code)]
        steps += [f'until:{entry+7:04X}:600', f'peek:{dest:04X}:{len(data)}',
                  L.until('idle', 100)]
        expected.append(data)
    result = a2test.run(DISK, steps, timeout=900)
    for k, data in enumerate(expected):
        assert result.dumps[k] == data, (k, 'decoded bytes')
    print(f'  {len(cases)} native loader decodes: literals, runs, overlap, page crossing, '
          f'255-byte matches and 4 KB window: OK')


def night_redraw():
    with a2test.Session(DISK) as s:
        s.step(L.until('idle', 20000))
        s.step(L.poke('nature_frequency', 0))
        s.step('key:REST 16 H')
        s.step('press:\\r')
        s.step(L.until('do_command', 20000))
        s.step(L.until('idle', 20000))
        assert s.step(L.peek('night')).data == b'\x01'
        s.step('key:DRINK 1 OZ')
        s.step('press:\\r')
        s.step(L.until('do_command', 20000))
        result = s.step(f'pcprof:{L["idle"]:04X}:20000')
        pcs = {int(a, 16): int(c) for a, c in
               re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', result.out, re.M)}
        # Entry PHP takes three cycles. One clear suffices even when
        # a command restores its picture through finish_simulation.
        assert pcs.get(L['clear_rows'], 0) == 3, 'night picture cleared twice'
    print('  nighttime DRINK restores its picture with one terrain clear: OK')


if __name__ == '__main__':
    division()
    loader_decode()
    night_redraw()
