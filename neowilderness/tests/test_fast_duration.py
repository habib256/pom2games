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


def expected_column(x, ang):
    """dpa_off, dpa_and, dpa_bits, dpb_off, dpb_and, dpb_bits and the bank,
    pattern and dither patches of src/dhgr.s column_setup for pixel x."""
    g, k = divmod(x, 7)
    bits = 0xF << (4 * k)
    ja = (4 * k) // 7
    parts = [ja] + ([ja + 1] if (4 * k + 3) // 7 != ja else [])
    out = []
    for j in parts:
        b = (bits >> (7 * j)) & 0x7F
        out.append((2 * g + j // 2, b ^ 0x7F, b, 0x55 if j % 2 == 0 else 0x54, L['dc_pat'] + 16 * j))
    return out, (L['dca'], L['dcb']) if ang % 2 == 0 else (L['dcb'], L['dca'])


def columns():
    """column_setup: the bytes, masks and banks of each DHGR colour pixel, and
    the dither phase from the azimuth (both parities of every column)."""
    steps = [L.until('idle', 20000)] + call(['column_setup'])
    cases = [(x, ang) for x in range(140) for ang in (2 * x + 6, 2 * x + 7)]
    patch = ('dspan_ba', 'dspan_pa0', 'dspan_bb', 'dspan_pb0', 'dspan_ea0', 'dspan_ea1')
    for x, ang in cases:
        steps += [L.poke('col', x), L.poke('ang', ang), L.poke('ang', ang >> 8, 1),
                  f'until:{L["idle"]+3:04X}:100', L.peek('dpa_off', 6)]
        steps += [L.peek(name, 2, 1) for name in patch]
        steps += [L.until('idle', 100)]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=300)
    d = result.dumps
    for i, (x, ang) in enumerate(cases):
        zp, ba, pa, bb, pb, ea0, ea1 = d[7 * i:7 * i + 7]
        parts, (even, odd) = expected_column(x, ang)
        (aoff, aand, abits, abank, apat) = parts[0]
        assert zp[:3] == bytes((aoff, aand, abits)), (x, 'part A', zp.hex())
        assert ba[0] == abank and int.from_bytes(pa, 'little') == apat, (x, 'part A bank/pattern')
        if len(parts) == 2:
            (boff, band, bbits, bbank, bpat) = parts[1]
            assert zp[3:] == bytes((boff, band, bbits)), (x, 'part B', zp.hex())
            assert bb[0] == bbank and int.from_bytes(pb, 'little') == bpat, (x, 'part B bank/pattern')
        else:
            assert zp[3] == 0xFF, (x, 'one byte')
        assert (ea0[0], ea1[0]) == (even, odd), (x, ang, 'dither phase')
    print(f'  140 DHGR colour columns x 2 azimuth parities: bytes, masks, banks, '
          f'pattern rows and dither phase, including the aux/main straddles: OK')


if __name__ == '__main__':
    durations()
    columns()
