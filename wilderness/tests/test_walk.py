#!/usr/bin/env python3
"""A long real WALK makes bounded DOS reads, reports progress and terminates."""
import tempfile
import re
from common import HERE, L, a2test, disk_with, fp, state, text_screen


def main():
    m = bytearray((HERE / 'build/map.bin').read_bytes())
    m[2:8] = bytes((0, 10, 0, 40, 140, 0))
    m[8:12] = bytes((100, 70, 0, 90))
    m[13:17] = bytes((90, 90, 20, 0))
    m[23] = 100  # Climate outside all encounter ranges; still execute fauna.
    m[64:] = bytes([10]) * 9408
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, m)
        with a2test.Session(disk) as s:
            s.step(L.until('idle', 20000))
            for step in ('key:WALK', 'press:\r', L.until('number_idle', 6000)):
                s.step(step)
            previous = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
            s.step('key:4\r')
            s.step('wait:1')
            for cell in range(1, 13):
                s.step(L.until('walk_progress', 6000))
                reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
                # SIM is loaded once. A due health update replaces live
                # TOPO with the medical image in the shared 2 KB window.
                medical_read = int(bool(s.step(L.peek('health_due')).data[0]))
                expected = medical_read + int(cell == 1)
                assert reads - previous == expected, (cell, previous, reads, expected)
                previous = reads
                assert state(s.step(L.peek('px', 6)).data) == ((10 + cell) * 256, 40 * 256, 140)
                assert abs(fp(s.step(L.peek('s_elap', 5)).data) * 60 - cell * 19) < 1e-5
                before_page = s.step('peek:0400:1024').data
                before_text = text_screen(before_page)
                before_sim = s.step('peek:2000:8192').data
                vector = s.step('peek:0036:2').data
                profile = s.step(f'pcprof:{L["topo_moving_done"]:04X}:6000')
                pcs = {int(a,16): int(c) for a,c in re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile.out, re.M)}
                writes = sum(pcs.get(L[label],0)//6 for label in ('topo_store','topo_clear_store'))
                after_page = s.step('peek:0400:1024').data
                changes = sum(before_page[o+c] != after_page[o+c]
                              for row in range(20)
                              for o in [(row%8)*128+(row//8)*40]
                              for c in range(40))
                assert writes == changes, (cell, writes, changes, 'unchanged TOPO characters were rewritten')
                assert s.step('peek:0036:2').data == vector, 'TOPO must restore the output vector'
                reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
                assert reads - previous == max(medical_read, int(cell == 1)), (cell, previous, reads)
                previous = reads
                screen = text_screen(s.step('peek:0400:1024').data)
                assert screen[1].startswith(f'CELL {10 + cell},40'), screen
                rows = screen[4:18]
                origin_x = max(0, 10 + cell - 16)
                assert rows[6][10 + cell - origin_x] == 'P', rows
                assert screen[20:] == before_text[20:], ('TOPO overwrote the progress area', before_text[20:], screen[20:])
                assert s.step('peek:2000:8192').data == before_sim, 'TOPO touched simulation/HGR RAM'
                s.step(L.until('at_goal', 6000))
                screen = text_screen(s.step('peek:0400:1024').data)
                assert f'TRAVELLING: {cell * 19} MIN.' in '\n'.join(screen), screen
                assert s.step(L.peek('shown')).data == b'\0'
                s.step('wait:1')
            s.step(L.until('idle', 6000))
            assert int.from_bytes(s.step(L.peek('minutes', 2)).data, 'little') == 12
            screen = text_screen(s.step('peek:0400:1024').data)
            assert 'TRAVEL: 228 MINUTES.' in '\n'.join(screen), screen
            # The game stays at the command prompt without more disk work.
            before = s.step(L.peek('overlay_reads', 2)).data
            s.step('wait:600')
            assert s.step(L.peek('overlay_reads', 2)).data == before
    print('WALK 4: 12 live map updates write exactly the changed characters; messages, simulation and output vector preserved OK')


if __name__ == '__main__':
    main()
