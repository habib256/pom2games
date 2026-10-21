#!/usr/bin/env python3
"""Write the T/S-list location of every track file into the game on the disk.

    python3 tools/patchdir.py DISK LABELS

The game reads its tracks with RWTS once DOS is gone (src/loader.inc). It
needs, for T01..T30, the track and sector of the file's T/S list: they are
known only once the disk is built, so this patches trackdir_t / trackdir_s
inside DIRTBIKE on the disk (same length, nothing else moves); likewise the
title's T/S list (titledir_t / _s) and the two data sectors of the hall of
fame (hof_t / hof_s), which the game rewrites in place.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import dos33  # noqa: E402

LOAD = 0x6000


def main():
    disk, lbl = Path(sys.argv[1]), Path(sys.argv[2])
    labels = {n: int(a, 16) for a, n in re.findall(r'^al ([0-9A-F]+) \.(\w+)$', lbl.read_text(), re.M)}
    image = bytearray(disk.read_bytes())
    where = {name: (ts, ss) for name, _, _, _, ts, ss in dos33.catalog(bytes(image))}
    game = bytearray(dos33.read_file(bytes(image), 'DIRTBIKE'))
    n = 0
    while f'T{n + 1:02}' in where:
        ts, ss = where[f'T{n + 1:02}']
        game[labels['trackdir_t'] - LOAD + n] = ts
        game[labels['trackdir_s'] - LOAD + n] = ss
        n += 1
    assert n == 30, n

    def put(label, value):
        game[labels[label] - LOAD] = value
    ts, ss = where['TITLE']                    # the title: its T/S list
    put('titledir_t', ts)
    put('titledir_s', ss)
    hof = dos33.file_sectors(bytes(image), 'DIRTHOF')
    assert len(hof) == 2, hof                  # the hall of fame: both data sectors
    for i, off in enumerate(hof):
        game[labels['hof_t'] - LOAD + i] = off // 256 // 16
        game[labels['hof_s'] - LOAD + i] = off // 256 % 16
    dos33.replace_file(image, 'DIRTBIKE', bytes(game))
    disk.write_bytes(bytes(image))


if __name__ == '__main__':
    main()
