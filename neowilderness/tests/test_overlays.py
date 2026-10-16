#!/usr/bin/env python3
"""Module loads (RAM transfers): state preservation, caching and module switching."""
import sys
from common import HERE, L, DISK, a2test, fp


def main():
    idle = L.until('idle', 20000)
    snap = [L.peek('overlay_current'), L.peek('overlay_reads', 2), L.peek('px', 6)]
    # Stop immediately before the transfer and immediately after it, so
    # command handling cannot mask damaged ZP, text or game state.
    size = L['it_kcal'] + 76 - L['px']
    preservation = ['peek:0000:256', 'peek:0400:1024', L.peek('px', size), 'peek:2000:8192']
    steps = [L.until('game_start', 4000), L.poke('scenes_enabled', 0), idle] + snap + ['key:LOOK R', 'press:\r', L.until('overlay_before_transfer', 6000)]
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

    check('module transfer preserves all 256 zero-page bytes', r.mem(0, 256) == r.mem(0, 256, 1))
    # Compare the 24 visible rows, including character attributes.
    before, after = r.mem(0x400, 1024), r.mem(0x400, 1024, 1)
    check('module transfer preserves all 24 visible text rows', all(
        before[o:o + 40] == after[o:o + 40]
        for row in range(24)
        for o in [(row % 8) * 128 + (row // 8) * 40]))
    # px was already dumped once in the initial short snapshot.
    check('module transfer preserves every resident item and simulation field',
          r.mem(L['px'], size, 1) == r.mem(L['px'], size, 2))
    # Each page dump reads main, then aux (PAGE2): occurrences 0/1 before, 2/3 after.
    check('module transfer preserves both DHGR banks',
          r.mem(0x2000, 8192, 0) == r.mem(0x2000, 8192, 2) and r.mem(0x2000, 8192, 1) == r.mem(0x2000, 8192, 3))
    current = [r.mem(L['overlay_current'], 1, k)[0] for k in range(7)]
    reads = [int.from_bytes(r.mem(L['overlay_reads'], 2, k), 'little') for k in range(7)]
    # STATUS runs in the SIM window (direct mem_fetch, not counted): the $5800
    # window keeps MEDICAL (17), which gave it the percentages of its MEDICAL
    # rows after ADVENTURE (21) gave the route progress (15 October 2026).
    # INVENTORY shares that module: only its load totals (SIM) count; $5800
    # keeps HUD.
    check('resident LOOK and screen shortcuts avoid redundant overlays', current == [15, 1, 1, 17, 15, 15, 15])
    print(f'  overlay windows: {current}, cumulative overlay reads: {reads}')
    # Measured on both pre-transition and current native-rule builds.
    check('module reads stay bounded across LOOK, STATUS, transfers and REST',
          # RAM module loads; the frozen HGR build's disk reads, plus the
          # health alerts module (lot 13, ID 27) after REST's health update.
          # (STATUS: ADVENTURE and MEDICAL since 15 October 2026)
          reads == [4, 5, 5, 7, 11, 22, 23])
    check('clock remains correct through module swaps',
          abs(fp(r.mem(L['s_hour'], 5)) - 10) < 1e-6
          and abs(fp(r.mem(L['s_elap'], 5)) - 3) < 1e-6)
    check('display/parser/input overlays fit the 2 KB window',
          all(0 < (HERE / f'build/wild{name}.bin').stat().st_size <= 2048
              for name in ('voc', 'hud', 'sit', 'prj', 'inp', 'itm', 'trv', 'med', 'mvi', 'tre', 'adv', 'out')))
    # Since 16 October 2026 (the OBJECTS page of transfers) STATUS runs over
    # the grid's image too, as SIM and XL's tail do (get_line gathers it), up
    # to STATX, XL's tail ($B100).
    check('STATUS, OBJECTS and HELP fit the SIM window below XL\'s tail ($9600-$B0FF)',
          0 < (HERE / 'build/wildsta.bin').stat().st_size <= L['stx_base'] - 0x9600)
    check('simulation fits the 8 KB SIM window', 0 < (HERE/'build/wildsim.bin').stat().st_size <= 8192)
    print(f'{len(failures)} failures')
    sys.exit(bool(failures))


if __name__ == '__main__':
    main()
