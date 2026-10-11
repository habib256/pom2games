#!/usr/bin/env python3
"""Measure real DOS loading in the POM2 core, in emulated cycles/seconds.

Usage: python3 tools/profile_loading.py [disk.dsk ...]
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tests'))
from common import L, DISK, a2test


def measure(disk):
    steps = [L.until('game_start', 20000), L.until('idle', 20000)]
    for command, target in [('LOOK R', 'idle'), ('STATUS', 'wait_key')]:
        steps += [f'key:{command}\\r', 'wait:1',
                  L.until('overlay_before_dos', 20000),
                  L.until('overlay_ready', 20000), L.until(target, 20000)]
    result = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    c = result.cycles
    values = {'boot + resident files': c[0], 'ready to play': c[1],
              'vocabulary BLOAD': c[3] - c[2], 'status BLOAD': c[6] - c[5]}
    print(disk)
    for label, cycles in values.items():
        print(f'  {label:24} {cycles:10} cycles  {cycles / a2test.CPU_HZ:.2f} s')
    return values


if __name__ == '__main__':
    for disk in sys.argv[1:] or [DISK]:
        measure(disk)
