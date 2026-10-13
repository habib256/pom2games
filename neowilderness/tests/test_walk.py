#!/usr/bin/env python3
"""A long real WALK: bounded module loads, MAP progress, no disk access.

overlay_reads counts module loads. Since lots 1-2 each one is a copy from
auxiliary RAM (memory.s), not a DOS read: the same per-step counts as the
HGR version are checked, then that every load was a RAM transfer
(xfer_count) and that no MLI call happened (mli_calls).
"""
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
            first_load = previous
            transfers = int.from_bytes(s.step(L.peek('xfer_count', 2)).data, 'little')
            calls = s.step(L.peek('mli_calls', 2)).data
            s.step('key:4\r')
            s.step('wait:1')
            # Native half-cell pace: the health/weather update after step 13
            # slows this flat-ground fixture from 9 to 10 minutes per step.
            # Three minutes remain after step 25, below floor(10/2).
            step_minutes = (9,) * 13 + (10,) * 12
            elapsed = 0
            for step, duration in enumerate(step_minutes, 1):
                elapsed += duration
                cell_x = 10 + step // 2
                s.step(L.until('walk_progress', 6000))
                reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
                # Module loads (RAM copies): TRAVEL replaces MAP for each
                # step. The first step also prepares the raster and loads
                # SIM. A health update loads MEDICAL and restores the
                # environment/travel modules.
                medical_read = int(bool(s.step(L.peek('health_due')).data[0]))
                assert medical_read == int(step in (2, 13, 23))
                expected = 1 + 2 * int(step == 1) + 4 * medical_read
                assert reads - previous == expected, (step, previous, reads, expected)
                previous = reads
                assert s.step(L.peek('stepmin')).data == bytes((duration,))
                assert state(s.step(L.peek('px', 6)).data) == (10 * 256 + step * 128, 40 * 256, 140)
                assert int.from_bytes(s.step(L.peek('journey_halfcells', 2)).data, 'little') == step
                assert abs(fp(s.step(L.peek('s_elap', 5)).data) * 60 - elapsed) < 1e-5
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
                assert writes == changes, (step, writes, changes, 'unchanged MAP characters were rewritten')
                assert s.step('peek:0036:2').data == vector, 'MAP must restore the output vector'
                reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
                assert reads - previous == 1, (step, previous, reads)
                previous = reads
                screen = text_screen(s.step('peek:0400:1024').data)
                assert screen[1].startswith(f'CELL {cell_x},40'), screen
                rows = screen[4:18]
                origin_x = max(0, cell_x - 16)
                assert rows[6][cell_x - origin_x] == 'P', rows
                assert screen[20:] == before_text[20:], ('MAP overwrote the progress area', before_text[20:], screen[20:])
                assert s.step('peek:2000:8192').data == before_sim, 'MAP touched simulation/HGR RAM'
                s.step(L.until('at_goal', 6000))
                screen = text_screen(s.step('peek:0400:1024').data)
                assert f'TRAVELLING: {elapsed} MIN.' in '\n'.join(screen), screen
                assert s.step(L.peek('shown')).data == b'\0'
                s.step('wait:1')
            s.step(L.until('idle', 6000))
            assert int.from_bytes(s.step(L.peek('minutes', 2)).data, 'little') == 3
            screen = text_screen(s.step('peek:0400:1024').data)
            assert 'TRAVEL: 237 MINUTES.' in '\n'.join(screen), screen
            # Every load was a RAM transfer, never an MLI call.
            loads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little') - first_load
            copies = int.from_bytes(s.step(L.peek('xfer_count', 2)).data, 'little') - transfers
            assert loads == copies, (loads, copies)
            assert s.step(L.peek('mli_calls', 2)).data == calls, 'WALK called the MLI'
            # The game stays at the command prompt without loading more modules.
            before = s.step(L.peek('overlay_reads', 2)).data
            s.step('wait:600')
            assert s.step(L.peek('overlay_reads', 2)).data == before
    print(f'WALK 4: 25 native half-step map updates write exactly the changed characters; messages, simulation '
          f'and output vector preserved; {loads} module loads, all RAM transfers, no MLI call OK')


if __name__ == '__main__':
    main()
