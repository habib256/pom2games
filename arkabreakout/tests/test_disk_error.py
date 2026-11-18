#!/usr/bin/env python3
"""A file the game needs cannot be read: MUSIC is renamed in the catalog of
a copy of the disk. The game must reach its retry screen (disk_retry: a
message, a key, another try) instead of DOS's prompt, and come back to it
after a key. On the untouched disk the retry screen is never reached."""
from pathlib import Path
import argparse
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/ARKABREAKOUT.dsk')
    ap.add_argument('--labels', type=Path, default=ROOT / 'arkabreakout/build/game.lbl')
    args = ap.parse_args()
    L = a2test.labels(args.labels)
    image = bytearray(args.disk.read_bytes())
    name = bytes(c | 0x80 for c in b'MUSIC') + b'\xA0' * 25
    at = image.find(name)
    assert at > 0 and image.find(name, at + 1) < 0, 'MUSIC not found once in the catalog'
    image[at] = ord('X') | 0x80                         # now XUSIC: FILE NOT FOUND
    with tempfile.TemporaryDirectory(prefix='arka-disk-') as tmp:
        broken = Path(tmp) / 'broken.dsk'
        broken.write_bytes(image)
        r = a2test.run(broken, [L.until('disk_retry', 3000), 'wait:30', 'key: ', L.until('disk_retry', 600)])
        assert len(r.cycles) == 2 and r.cycles[1] > r.cycles[0], 'no second try after the key'
    r = a2test.run(args.disk, [L.until('menu_loop', 3000)])
    ok = a2test.run(args.disk, [L.until('disk_retry', 1500)], check=False)
    assert 'PC=%04X' % L['disk_retry'] not in ok.out, 'retry screen reached on a good disk'
    print('disk error: a missing MUSIC shows the retry screen, a key tries again; a good disk never does.')


if __name__ == '__main__':
    main()
