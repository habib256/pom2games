#!/usr/bin/env python3
"""Measure real POM2 CPU cycles (including Disk II rotation), never host time."""
from pathlib import Path
import argparse
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'
CPU_HZ = 1_021_800


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/MICRO-SOKOBAN.dsk')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/micro_sokoban.lbl')
    ap.add_argument('--legacy', action='store_true', help='measure an earlier DOS-command build')
    args = ap.parse_args()
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', args.labels.read_text(), re.M)}

    def until(name):
        return f'until:{labels[name]:04X}:3600'

    def measure(steps):
        result = subprocess.run([str(ROOT / 'dev/tools/a2shot/a2shot'), '--disk', str(args.disk), *steps],
                                check=True, text=True, capture_output=True, timeout=60)
        return [int(x) for x in re.findall(r'cycles=(\d+)', result.stdout)]

    # Stop at routine boundaries rather than peeking zero page during disk I/O.
    steps = [until('title_wait'), 'press:V', until('run_profiles'), 'wait:180',
             'key:N', 'wait:180', 'key:BEN', 'press:\r', until('activate_profile'),
             until('load_save'), until('calculate_score'), until('title_wait'),
             'key:G', 'wait:180', 'key:N', 'wait:180', 'press:\r',
             until('find_level'), until('decode_level')]
    cycles = measure(steps)
    assert len(cycles) == 8
    print('Startup %.3f s; first profile read %.3f s; first level-pack read %.3f s' % (
        cycles[0] / CPU_HZ, (cycles[4]-cycles[3]) / CPU_HZ, (cycles[7]-cycles[6]) / CPU_HZ))
    if not args.legacy:
        # A cold motor, cached file map, a real changed position, then ESC saves.
        steps = [until('title_wait'), 'key:G', 'wait:60', 'press:\r', until('move_loop'),
                 'key:K', 'wait:180', 'press:\x1b', until('save_position'), until('run_menu')]
        cycles = measure(steps)
        print('Position checkpoint %.3f s (including status and HUD redraw)' % ((cycles[-1]-cycles[-2])/CPU_HZ))
    # The normal success path saves records and the ranking.
    solution = next(row.split()[3] for row in (GAME / 'levels/solutions.txt').read_text().splitlines()
                    if row.startswith('I 1 '))
    keys = ''.join(dict(u='I', d='K', l='J', r='L')[c] for c in solution.lower())
    steps = [until('title_wait'), 'key:G', 'wait:60', 'press:\r', until('move_loop'),
             'key:' + keys, until('write_save'), until('wait_any')]
    cycles = measure(steps)
    print('Completed-level records and ranking %.3f s' % ((cycles[-1]-cycles[-2])/CPU_HZ))


if __name__ == '__main__':
    main()
