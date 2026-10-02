#!/usr/bin/env python3
"""Menu rendering must not depend on a string address's low byte."""
from pathlib import Path
import argparse
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', type=Path, default=ROOT / 'dev/tools/a2run/a2run')
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/MICRO-SOKOBAN.dsk')
    args = ap.parse_args()
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', (GAME / 'build/micro_sokoban.lbl').read_text(), re.M)}
    binary = (GAME / 'build/micro_sokoban.bin').read_bytes()
    start = labels['options_keys'] - 0x6000
    text = binary[start:binary.index(255, start)+1]
    relocated = 0x05FF                 # invisible text memory, across a page boundary
    patch = [f'poke:{relocated+i:04X}:{byte:02X}' for i, byte in enumerate(text)]
    patch += [f'poke:{labels["options_table"]+5:04X}:FF',
              f'poke:{labels["options_table"]+6:04X}:05']
    def screen(pokes, gameplay=False):
        steps = ['wait:1800']
        if gameplay:
            steps += ['key:G', 'wait:90', 'key:\r', 'wait:180', 'key:K', 'wait:60']
        steps += pokes + ['key:\x1b', 'wait:120', 'key:O', 'wait:120',
                          f'peek:{labels["front_page"]:04X}:1', 'peek:2000:16384']
        result = subprocess.run([str(args.a2run), '--disk',
                                 str(args.disk), *steps],
                                check=True, capture_output=True, text=True, timeout=30)
        raw = b''.join(bytes.fromhex(row) for row in re.findall(r'^[0-9A-F]{4}: (.+)$', result.stdout, re.M))
        offset = 1 + (8192 if raw[0] else 0)
        return raw[offset:offset+8192]
    baseline = screen([])
    assert baseline == screen(patch), 'text pointer ending in FF truncated the options table'
    assert baseline == screen([], True) == screen(patch, True)
    print('Complete options screen from title and gameplay, including string address $xxFF: ok')


if __name__ == '__main__':
    main()
