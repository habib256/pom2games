#!/usr/bin/env python3
"""Boot actual disk payloads, quit/reset to BASIC, LIST and RUN repeatedly."""
from pathlib import Path
import argparse
import re
import subprocess
from test_score import file_sectors, read_file

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', type=Path, default=ROOT / 'dev/tools/a2run/a2run')
    ap.add_argument('--a2shot', type=Path, default=ROOT / 'dev/tools/a2shot/a2shot')
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/MICRO-SOKOBAN.dsk')
    args = ap.parse_args()
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', (GAME / 'build/micro_sokoban.lbl').read_text(), re.M)}
    image = args.disk.read_bytes()
    assert read_file(image, 'MICRODATA') == (GAME / 'build/micro_sokoban.lz').read_bytes(), \
        'disk program differs from the build; regenerate and reload the disk in the emulator'
    hello = b''.join(image[offset:offset+256] for offset in file_sectors(image, 'HELLO'))
    hello = hello[2:2 + int.from_bytes(hello[:2], 'little')]

    for emulator in (args.a2run, args.a2shot):
        if not emulator.exists():
            continue
        native = emulator == args.a2shot
        enter = f'until:{labels["title_wait"]:04X}:3600'
        steps = [enter]
        # Both exit paths must restore HELLO, including its leading sentinel.
        for leave in (['key:\x1b', 'wait:90', 'key:Q'], ['reset'],
                      ['key:G', 'wait:90', 'key:\r', 'wait:600',
                       'key:L', 'wait:60', 'key:\x1b', 'wait:600', 'key:Q']):
            steps += leave + ['wait:600', f'peek:0800:{len(hello)+1}', 'peek:0067:6',
                              'key:LIST\r', 'wait:180', 'key:RUN\r', enter]
        if native:
            steps = [step.replace('\x1b', '\\e').replace('\r', '\\r') for step in steps]
        result = subprocess.run([str(emulator), '--disk', str(args.disk), *steps],
                                check=True, capture_output=True, text=True, timeout=60)
        rows = [bytes.fromhex(row) for row in re.findall(r'^[0-9A-F]{4}: (.+)$', result.stdout, re.M)]
        raw = b''.join(rows)
        size = len(hello) + 1 + 6
        assert len(raw) == 3 * size, (emulator, len(raw))
        for offset in range(0, len(raw), size):
            assert raw[offset:offset+len(hello)+1] == b'\0' + hello
            pointers = raw[offset+len(hello)+1:offset+size]
            assert pointers[:2] == b'\x01\x08', pointers
            assert int.from_bytes(pointers[2:4], 'little') == 0x801 + len(hello), pointers
        print(f'{emulator.name}: boot, QUIT/RESET, restored BASIC, LIST and three RUN restarts: ok')


if __name__ == '__main__':
    main()
