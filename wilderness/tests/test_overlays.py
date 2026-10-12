#!/usr/bin/env python3
"""Real DOS overlay reads: state preservation, caching and module switching."""
import sys
from common import HERE, L, DISK, a2test, fp


def main():
    idle = L.until('idle', 20000)
    snap = [L.peek('overlay_current'), L.peek('overlay_reads', 2), L.peek('px', 6)]
    # Stop immediately before BLOAD and immediately after the preservation
    # code, so command handling cannot mask damaged ZP, text or game state.
    size = L['it_kcal'] + 76 - L['px']
    preservation = ['peek:0000:256', 'peek:0400:1024', L.peek('px', size), 'peek:2000:8192']
    steps = [L.until('game_start', 4000), L.poke('scenes_enabled', 0), idle] + snap + ['key:LOOK R', 'press:\r', L.until('overlay_before_dos', 6000)]
    steps += preservation + [L.until('overlay_ready', 6000)] + preservation
    steps += [idle] + snap + ['key:LOOK L\r', 'wait:1', idle] + snap
    steps += ['key:STATUS\r', L.until('wait_key', 6000)] + snap
    steps += ['key: ', 'wait:1', idle, 'key:GET PARKA\r', 'wait:1', idle] + snap
    steps += ['key:REST', 'press:\r', L.until('number_idle', 6000), 'key:3\r', 'wait:1', idle] + snap
    steps += [L.peek('s_hour', 5), L.peek('s_elap', 5)]
    # Environment -> vocabulary -> text screens -> vocabulary again.
    steps += ['key:INVENTORY\r', 'wait:1', L.until('wait_key', 6000)] + snap
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    failures = []

    def check(name, ok):
        print(f'  {name}: {"OK" if ok else "FAIL"}')
        if not ok:
            failures.append(name)

    check('BLOAD preserves all 256 zero-page bytes', r.mem(0, 256) == r.mem(0, 256, 1))
    # DOS uses the eight screen-hole bytes in each 128-byte block as
    # scratch. Compare the 24 visible rows, including character attributes.
    before, after = r.mem(0x400, 1024), r.mem(0x400, 1024, 1)
    check('BLOAD preserves all 24 visible text rows', all(
        before[o:o + 40] == after[o:o + 40]
        for row in range(24)
        for o in [(row % 8) * 128 + (row // 8) * 40]))
    # px was already dumped once in the initial short snapshot.
    check('BLOAD preserves every resident item and simulation field',
          r.mem(L['px'], size, 1) == r.mem(L['px'], size, 2))
    check('BLOAD preserves the HGR image', r.mem(0x2000, 8192) == r.mem(0x2000, 8192, 1))
    current = [r.mem(L['overlay_current'], 1, k)[0] for k in range(7)]
    reads = [int.from_bytes(r.mem(L['overlay_reads'], 2, k), 'little') for k in range(7)]
    check('resident LOOK and screen shortcuts avoid redundant overlays', current == [15, 1, 1, 16, 15, 15, 2])
    print(f'  cumulative overlay reads: {reads}')
    # Measured on both pre-transition and current native-rule builds.
    check('module reads stay bounded across LOOK, STATUS, transfers and REST',
          reads == [4, 5, 5, 8, 12, 22, 24])
    check('clock remains correct through module swaps',
          abs(fp(r.mem(L['s_hour'], 5)) - 10) < 1e-6
          and abs(fp(r.mem(L['s_elap'], 5)) - 3) < 1e-6)
    check('display/parser/input overlays fit the 2 KB window',
          all(0 < (HERE / f'build/wild{name}.bin').stat().st_size <= 2048
              for name in ('voc', 'scr', 'sta', 'hud', 'sit', 'prj', 'inp', 'itm', 'trv', 'med', 'mvi', 'tre', 'adv', 'out')))
    check('simulation fits the 8 KB HGR window', 0 < (HERE/'build/wildsim.bin').stat().st_size <= 8192)
    print(f'{len(failures)} failures')
    sys.exit(bool(failures))


if __name__ == '__main__':
    main()
