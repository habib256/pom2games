#!/usr/bin/env python3
"""dos33patch.py -- write where files lie on a DOS 3.3 disk into a program
on that disk, for a game that reads them through RWTS once DOS is gone.

    python3 dos33patch.py DISK PROGRAM LABELS
            [--tslist LABEL_T LABEL_S FILE...]...
            [--sectors LABEL_T LABEL_S FILE]...

The locations are known only once the disk is built, so this patches the
binary file PROGRAM in place on DISK (same length, nothing else moves).
LABELS is its ld65 -Ln file; PROGRAM's load address comes from its DOS
header. Each option fills two byte tables, track at LABEL_T, sector at
LABEL_S:
  --tslist   entry k = the T/S list of the k-th FILE (lib/apple2/rwts.asm's
             rwts_read_tslist reads the whole file from it);
  --sectors  entry k = the k-th data sector of FILE (rwts_read / rwts_write
             it in place: a save file).
LABEL_S must follow LABEL_T: the gap between them is the table's size, and
the entries must fill it exactly (a missing file or a longer save file
would leave the game a wrong table).
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dos33  # noqa: E402


def patch(image, program, labels, tslists=(), sectors=()):
    """image: bytearray of the disk, changed in place."""
    raw = b''.join(bytes(image[s:s + dos33.SEC_SIZE]) for s in dos33.file_sectors(bytes(image), program))
    load = int.from_bytes(raw[0:2], 'little')
    game = bytearray(dos33.read_file(bytes(image), program))
    where = {name: (ts, ss) for name, _, _, _, ts, ss in dos33.catalog(bytes(image))}

    def fill(lt, ls, entries, what):
        size = labels[ls] - labels[lt]
        if len(entries) != size:
            raise SystemExit(f'{lt}/{ls}: {len(entries)} {what} for a table of {size}')
        for k, (t, s) in enumerate(entries):
            game[labels[lt] - load + k] = t
            game[labels[ls] - load + k] = s

    for lt, ls, *files in tslists:
        missing = [f for f in files if f not in where]
        if missing:
            raise SystemExit(f'not on the disk: {" ".join(missing)}')
        fill(lt, ls, [where[f] for f in files], 'files')
    for lt, ls, name in sectors:
        offs = dos33.file_sectors(bytes(image), name)
        fill(lt, ls, [(off // dos33.SEC_SIZE // 16, off // dos33.SEC_SIZE % 16) for off in offs],
             f'sectors of {name}')
    dos33.replace_file(image, program, bytes(game))


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('disk', type=Path)
    p.add_argument('program')
    p.add_argument('labels', type=Path)
    p.add_argument('--tslist', nargs='+', action='append', default=[], metavar='X')
    p.add_argument('--sectors', nargs=3, action='append', default=[], metavar='X')
    a = p.parse_args()
    if any(len(t) < 3 for t in a.tslist):
        p.error('--tslist LABEL_T LABEL_S FILE...')
    labels = {n: int(v, 16) for v, n in re.findall(r'^al ([0-9A-F]+) \.(\w+)$', a.labels.read_text(), re.M)}
    image = bytearray(a.disk.read_bytes())
    patch(image, a.program, labels, a.tslist, a.sectors)
    a.disk.write_bytes(bytes(image))


if __name__ == '__main__':
    main()
