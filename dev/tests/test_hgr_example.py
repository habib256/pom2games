#!/usr/bin/env python3
"""Boot the starter, exercise pause/resume and arrows, and return to DOS."""
from pathlib import Path
import argparse
import re
import tempfile
from test_hgr import DEV, offset, run


def sprite_area(snapshot):
    return bytes(snapshot[page + offset(y) + col]
                 for page in (0,8192) for y in range(60,169) for col in range(40))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='pom2-hgr-example-') as temp:
        work = Path(temp)
        run(['make','-s','-C',DEV/'examples/hgr',f'BUILD={work}/build',f'DIST={work}'])
        if not args.iie: run(['make','-s','-C',DEV/'tools/a2run'])
        emulator = DEV/'tools'/('a2shot/a2shot' if args.iie else 'a2run/a2run')
        # Pause long enough for the two pages to converge, then exercise resume
        # and all four direction controls. Snapshot comparison ignores the HUD.
        steps = ['wait:1100','peek:2000:16384','wait:20','peek:2000:16384',
                 'key: ','wait:20','peek:2000:16384','wait:30','peek:2000:16384',
                 'key: ','key:\\<\\>\\^\\v','wait:30','peek:2000:16384',
                 'key:\\e','wait:30','peek:03F2:3']
        if not args.iie: steps += ['text']
        output = run([emulator,*(['--iie'] if args.iie else []),'--disk',work/'HGR.dsk',*steps])
        chunks = re.split(r'(?m)^2000:',output)[1:]
        assert len(chunks) == 5, 'missing example snapshots'
        pages = [bytes.fromhex(chunk.splitlines()[0] + ' ' + ' '.join(re.findall(r'(?m)^[2345][0-9A-F]{3}: ([0-9A-F ]+)$',chunk))) for chunk in chunks]
        assert all(len(p) == 16384 for p in pages)
        areas = [sprite_area(p) for p in pages]
        assert areas[0] != areas[1], 'animation did not advance'
        assert areas[2] == areas[3], 'pause did not keep the scene stable'
        assert areas[3] != areas[4], 'animation did not resume'
        # Restore should return the original DOS reset vector, not library code.
        vector = bytes.fromhex(re.search(r'(?m)^03F2: ([0-9A-F ]+)$',output)[1])
        assert vector[:2] == bytes((0xBF,0x9D)), ('RESET vector not restored',vector)
        if not args.iie: assert re.search(r'\|.*\].*\|',output), 'DOS prompt not visible'
    print('HGR starter: boot, animation, pause/resume, arrows, ESC and DOS restoration passed' + (' (IIe).' if args.iie else ' (II+).'))


if __name__ == '__main__':
    main()
