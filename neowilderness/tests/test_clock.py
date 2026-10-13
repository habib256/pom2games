#!/usr/bin/env python3
"""Clock display agrees with integer action minutes, without changing time."""
import tempfile
from common import L, a2test, disk_with, fp, text_screen
from test_input import flat, command, IDLE
from test_interface import panels
from gendata import fp as encode


def displays(s, header, status):
    before = s.step(L.peek('s_hour', 5)).data
    s.step(L.poke('ui_dirty', 1))
    command(s, 'VIEW')
    actual = panels(s.step('peek:2000:8192').data)[2]
    assert actual == header + ' DAY 1', (header, actual)
    s.step('key:STATUS')
    s.step('press:\\r')
    s.step(L.until('status_key', 20000))
    text = '\n'.join(text_screen(s.step('peek:0400:1024').data))
    assert 'TIME ' + status in text, (status, text)
    assert s.step(L.peek('s_hour', 5)).data == before
    s.step('key:\\e')
    s.step(IDLE)


def main():
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp, flat())) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        command(s, 'WALK 19 MIN')
        assert abs(fp(s.step(L.peek('s_elap', 5)).data) * 60 - 18) < 1e-5
        # Two native nine-minute half-steps consume eighteen of the nineteen requested.
        displays(s, '7:18', '7:18A')
        for hour, header, status in (
                (7 + 1/60, '7:01', '7:01A'),
                (7 + 59/60, '7:59', '7:59A'),
                (7.99999999, '8:00', '8:00A'),
                (11.99999999, '12:00', '12:00P'),
                (18 + 59/60, '18:59', '6:59P'),
                (23.99999999, '0:00', '12:00A'),
                (0, '0:00', '12:00A')):
            for offset, value in enumerate(encode(hour)):
                s.step(L.poke('s_hour', value, offset))
            displays(s, header, status)
        # Journey day of the right panel: day of year - 125, + 365 across
        # New Year (the crash of May 6 is day 1); 16-bit from September 12.
        for date, expected in ((0.34442, 1), (299.5 / 365, 175), (364.5 / 365, 240), (0, 241)):
            for offset, value in enumerate(encode(date)):
                s.step(L.poke('s_date', value, offset))
            s.step(L.poke('ui_dirty', 1))
            command(s, 'VIEW')
            actual = panels(s.step('peek:2000:8192').data)[2]
            assert actual == f'0:00 DAY {expected}', (date, actual)
    print('Clock: real 18-minute walk (19 requested), minute/hour/noon/midnight boundaries; HUD and STATUS agree; time preserved; journey day')


if __name__ == '__main__':
    main()
