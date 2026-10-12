#!/usr/bin/env python3
"""Resident inline durations and derived HGR column geometry."""
from common import DISK, L, a2test
from test_thermal import call


def durations():
    # Direct native calls isolate the parser without spending hundreds of
    # simulated hours. Full command behavior is also covered by test_sleep.
    cases = [(f'REST {n}{unit}', 1 <= n <= 255, n, code)
             for n in range(261) for unit, code in (('', 1), (' H', 1), (' MIN', 2))]
    cases += [(text, False, 0, 0) for text in
              ('REST ', 'REST -1 H', 'REST 1 OZ', 'REST 1 SEC', 'REST 1 HR',
               'REST 1 H X', 'REST 1 MIN X', 'REST 65536 H', 'REST 256 H',
               'REST 15300 MIN', 'REST 1.5 H', 'REST 1-2 H', 'REST 1 H 2')]
    cases += [(text, True, n, unit) for text, n, unit in
              (('REST 0001 H', 1, 1), ('REST   19MIN   ', 19, 2), ('REST 255H', 255, 1))]
    entry = L['idle']
    address = L['fast_duration']
    # Capture carry and X before returning to the next fixture.
    code = bytes((0xA2, 0x5A, 0xA0, 4, 0x20, address & 255, address >> 8,
                  0x08, 0x68, 0x8D, 0, 0x95, 0x8E, 1, 0x95,
                  0x4C, entry & 255, entry >> 8))
    for first in range(0, len(cases), 64):
        batch = cases[first:first + 64]
        steps = [L.until('idle', 20000)]
        steps += [f'poke:{entry+i:04X}:{b:02X}' for i, b in enumerate(code)]
        for text, *_ in batch:
            steps += [L.poke('inbuf', b, i) for i, b in enumerate(text.encode() + b'\0')]
            steps += [L.poke('linelen', len(text)), L.poke('g2', 4),
                      L.poke('input_argument', 0), f'until:{entry+15:04X}:100',
                      'peek:9500:2', L.peek('msgnum', 2), L.peek('input_unit'),
                      L.peek('input_argument'), L.peek('inbuf', len(text) + 1),
                      L.until('idle', 100)]
        result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=180)
        for i, (text, valid, n, unit) in enumerate(batch):
            status, x = result.mem(0x9500, 2, i)
            assert bool(status & 1) == (not valid) and x == 0x5A, text
            actual = result.mem(L['inbuf'], len(text) + 1, i)
            if valid:
                assert result.mem(L['msgnum'], 2, i) == n.to_bytes(2, 'little'), text
                assert result.mem(L['input_unit'], 1, i) == bytes((unit,)), text
                assert result.mem(L['input_argument'], 1, i) == b'\x02', text
                assert actual[:5] == b'REST\0', text
            else:
                assert actual == text.encode() + b'\0', text
                assert result.mem(L['input_argument'], 1, i) == b'\0', text
    print(f'  {len(cases)} native inline durations: bounds, units, overflow and untouched fallback: OK')


def columns():
    steps = [L.until('idle', 20000)] + call(['column_masks'])
    for column in range(140):
        steps += [L.poke('col', column), f'until:{L["idle"]+3:04X}:100',
                  L.peek('be', 4), L.until('idle', 100)]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=180)
    for column in range(140):
        even, odd = 2 * column, 2 * column + 1
        expected = bytes((even // 7, odd // 7,
                          255 ^ (1 << (even % 7)), 255 ^ (1 << (odd % 7))))
        assert result.mem(L['be'], 4, column) == expected, column
    print('  140 native column pairs: identical bytes/masks, including byte/phase crossings: OK')


if __name__ == '__main__':
    durations()
    columns()
