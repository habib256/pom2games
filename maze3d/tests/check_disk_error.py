#!/usr/bin/env python3
"""A file the game cannot go on without cannot be read: MAZETITLE is renamed
in the catalog of a copy of the disk. The game must reach disk_retry (the
message on the text screen, a key, another try) and not go on with what is
in memory. On the untouched disk the retry screen is never reached."""
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test

L = a2test.labels(ROOT / 'maze3d/build/maze3d.lbl')
DISK = ROOT / 'dist/MAZE3D.dsk'


def main():
    image = bytearray(DISK.read_bytes())
    name = bytes(c | 0x80 for c in b'MAZETITLE') + b'\xA0' * 21
    at = image.find(name)
    assert at > 0 and image.find(name, at + 1) < 0, 'MAZETITLE not found once in the catalog'
    image[at] = ord('X') | 0x80                         # FILE NOT FOUND
    with tempfile.TemporaryDirectory(prefix='maze3d-disk-') as tmp:
        broken = Path(tmp) / 'broken.dsk'
        broken.write_bytes(image)
        r = a2test.run(broken, [L.until('disk_retry', 3000), 'wait:30', 'peek:0400:1024',
                                'key: ', L.until('disk_retry', 600)])
        assert len(r.cycles) == 2 and r.cycles[1] > r.cycles[0], 'no second try after the key'
        rows = [bytes(c & 0x7F for c in row).decode('ascii') for row in a2test.text_rows(r)]
        assert rows[0].startswith('CANNOT READ THE DISK.'), rows[:3]
        assert rows[1].startswith('CHECK IT, THEN PRESS A KEY.'), rows[:3]
    ok = a2test.run(DISK, [L.until('disk_retry', 2500)], check=False)
    assert 'PC=%04X' % L['disk_retry'] not in ok.out, 'retry screen reached on a good disk'
    print('disk error: a missing MAZETITLE shows the retry text, a key tries again; a good disk never does.')


if __name__ == '__main__':
    main()
