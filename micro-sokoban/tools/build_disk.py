#!/usr/bin/env python3
"""Game-specific layout: DOS boot reads, then cached direct-sector game I/O."""
import argparse
import importlib.util
from pathlib import Path
import shlex
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('dos33', ROOT / 'dev/tools/dos33.py')
dos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dos)

# Physical interleave 3, measured with the resident RWTS loop in POM2.
DIRECT_ORDER = [15, 14, 5, 11, 2, 8, 7, 13, 4, 10, 1, 0, 6, 12, 3, 9]


class GameDisk(dos.Dos33Image):
    direct = False
    sector_order = DIRECT_ORDER

    def alloc(self):
        if not self.direct:
            return super().alloc()
        for track in list(range(18, 35)) + list(range(16, 2, -1)):
            for sector in self.sector_order:
                if self.free[track, sector]:
                    self.free[track, sector] = False
                    return track, sector
        raise SystemExit('disk full')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--boot-step', type=int, default=2, choices=range(1, 5))
    ap.add_argument('--build', type=Path, default=Path('build'))
    ap.add_argument('--master', type=Path, default=ROOT / 'dev/tools/dos33_system.bin')
    args = ap.parse_args()
    disk = GameDisk(args.master, read_fast=True)
    hello = dos.tokenize_applesoft(Path('src/hello.bas').read_text())
    disk.add_file('HELLO', dos.TYPE_A, struct.pack('<H', len(hello)) + hello)

    def binary(name, path, address=0):
        data = path.read_bytes()
        disk.add_file(name, dos.TYPE_B, struct.pack('<HH', address, len(data)) + data)

    binary('MICRO-SOKOBAN', args.build / 'unpack.bin', 0x800)
    disk.direct = True
    physical = [0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15]
    sequence, index = [], 15
    while len(sequence) < 16:
        while index in sequence:
            index = (index + 1) % 16
        sequence.append(index)
        index = (index + args.boot_step) % 16
    disk.sector_order = [physical[i] for i in sequence]
    binary('MICRODATA', args.build / 'micro_sokoban.lz', 0x1004)
    disk.sector_order = DIRECT_ORDER
    # Bind the small bootstrap's read-only map to this newly built image.
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', (args.build / 'unpack.lbl').read_text(), re.M)}
    def sectors(name):
        track, sector, *_ = next(row for row in disk.catalog if row[3] == name)
        listing = disk.sector(track, sector)
        return [(listing[i], listing[i+1]) for i in range(12, 256, 2) if listing[i]]
    data_sectors = sectors('MICRODATA')
    assert len(data_sectors) <= 60
    loader = bytearray((args.build / 'unpack.bin').read_bytes())
    loader[labels['boot_count'] - 0x800] = 2 * len(data_sectors)
    offset = labels['boot_sectors'] - 0x800
    loader[offset:offset + 2 * len(data_sectors)] = bytes(v for pair in data_sectors for v in pair)
    raw = struct.pack('<HH', 0x800, len(loader)) + loader
    for i, (track, sector) in enumerate(sectors('MICRO-SOKOBAN')):
        chunk = raw[i*256:(i+1)*256]
        disk.sector(track, sector)[:len(chunk)] = chunk

    binary('MICROHOF', args.build / 'lv/microhof.bin')
    binary('MICROSAVE', args.build / 'lv/microsave.bin')
    for item in shlex.split((args.build / 'lv/packs.args').read_text()):
        if item == '--bin':
            continue
        name, path, address = dos.parse_spec(item, True)
        binary(name, Path(path), address)
    for i in range(1, 10):
        binary(f'MICROSAV{i}', args.build / 'lv/microsave.bin')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    disk.save(args.out)
    print(f'{disk.free_sectors()} sectors free -> {args.out}')


if __name__ == '__main__':
    main()
