#!/usr/bin/env python3
"""Build PCS's fixed-sector DOS 3.3 disk with the shared DEVBENCH writer."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
from dos33 import Dos33Image
from hgr_tables import scanline_tables, division_tables, shift_tables


def tables():
    data = bytearray(0x1700)  # loaded at $0800, ending at $1EFF
    low, high = shift_tables()
    quotient, remainder = division_tables()
    rows_low, rows_high = scanline_tables()
    data[0:0x600] = low
    data[0x600:0xc00] = high
    data[0xc00:0xd00] = quotient
    data[0xd00:0xe00] = remainder
    data[0xe00:0xec0] = rows_low
    data[0xec0:0xf80] = rows_high
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build', type=Path, default=Path('build'))
    ap.add_argument('--assets', type=Path, default=Path('assets'))
    ap.add_argument('--master', type=Path, help='legacy CLI option; boot.bin already contains the shared loader')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    image = Dos33Image.blank()
    # Fixed-sector modules occupy tracks 0-15; DOS saves cannot reuse them.
    image.reserve_sectors(0, 16 * 16)
    def put(sector, data, capacity):
        image.write_fixed(sector, data, capacity)
    def binary(name):
        return (args.build / (name + '.bin')).read_bytes()
    def asset(name):
        return (args.assets / (name + '.bin')).read_bytes()
    def module(memory, origin, name):
        code = binary(name)
        offset = origin - 0x7000
        assert 0 <= offset and offset+len(code) <= len(memory), name
        memory[offset:offset+len(code)] = code
    low = tables()
    for origin, name in [(0x1780, 'CDRAW'), (0x1e00, 'SWAP')]:
        code = binary(name)
        offset = origin - 0x800
        assert offset+len(code) <= len(low)
        low[offset:offset+len(code)] = code
    editor = bytearray(0x3900)
    editor[:0x700] = asset('bitmaps')
    module(editor, 0x7700, 'RUN')
    module(editor, 0x8e20, 'PPAK')
    module(editor, 0x9500, 'EDIT')
    user = bytearray(editor[0x1500:0x1f00])
    user[0x54:0x54+len(binary('RUN2'))] = binary('RUN2')
    put(0, binary('boot'), 256)
    put(1, binary('BOOT2'), 256)
    put(2, asset('dos-rwts'), 0x800)
    put(16, asset('dos-file-manager'), 0xd00)
    put(32, low, 0x1700)
    put(56, asset('initial-table')[:69], 256)
    put(128, editor, 0x3900)
    put(192, binary('WIRE'), 0xa00)
    put(208, binary('DISK'), 0x800)
    put(224, user, 0xa00)
    put(240, binary('mouse'), 0x800)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f'{args.out}: {len(image.data)} bytes, {image.free_sectors()} free sectors')

if __name__ == '__main__':
    main()
