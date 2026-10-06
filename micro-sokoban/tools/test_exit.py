#!/usr/bin/env python3
"""Boot actual disk payloads, quit/reset to BASIC, LIST and RUN repeatedly."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
import dos33
import micro_sokoban_levels as levels


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', type=Path, default=ROOT / 'dev/tools/a2run/a2run')
    ap.add_argument('--a2shot', type=Path, default=ROOT / 'dev/tools/a2shot/a2shot')
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/MICRO-SOKOBAN.dsk')
    args = ap.parse_args()
    labels = a2test.labels(GAME / 'build/micro_sokoban.lbl')
    image = args.disk.read_bytes()
    assert dos33.read_file(image, 'MICRODATA') == (GAME / 'build/micro_sokoban.lz').read_bytes(), \
        'disk program differs from the build; regenerate and reload the disk in the emulator'
    hello = b''.join(image[offset:offset+256] for offset in dos33.file_sectors(image, 'HELLO'))
    hello = hello[2:2 + int.from_bytes(hello[:2], 'little')]

    for emulator in (args.a2run, args.a2shot):
        if not emulator.exists():
            continue
        enter = f'until:{labels["title_wait"]:04X}:3600'
        steps = [enter]
        # Both exit paths must restore HELLO, including its leading sentinel.
        for leave in (['key:\x1b', 'wait:90', 'key:Q'], ['reset'],
                      ['key:G', 'wait:90', 'key:\r', 'wait:600',
                       'key:L', 'wait:60', 'key:\x1b', 'wait:600', 'key:Q']):
            steps += leave + ['wait:600', f'peek:0800:{len(hello)+1}', 'peek:0067:6',
                              'key:LIST\r', 'wait:180', 'key:RUN\r', enter]
        raw = a2test.run(args.disk, steps, emulator=emulator, timeout=60).data
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
