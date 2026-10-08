#!/usr/bin/env python3
"""Build PCS's fixed-sector DOS 3.3 disk with the shared DEVBENCH writer."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
from dos33 import Dos33Image


def tables():
    data = bytearray(0x1700)  # loaded at $0800, ending at $1EFF
    for shift in range(1, 7):
        for value in range(256):
            sign = value & 0x80
            bits = (value & 0x7f) << shift
            low = (bits & 0x7f) | sign
            high = (bits >> 7) | sign
            data[(shift-1)*256+value] = low if low != 0x80 else 0
            data[0x600+(shift-1)*256+value] = high if high != 0x80 else 0
    for i in range(256):
        data[0xc00+i] = i//7
        data[0xd00+i] = i%7
    for y in range(192):
        addr = 0x2000 + (y%8)*1024 + (y//8%8)*128 + (y//64)*40
        data[0xe00+y] = addr & 255
        data[0xec0+y] = addr >> 8
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build', type=Path, default=Path('build'))
    ap.add_argument('--assets', type=Path, default=Path('assets'))
    ap.add_argument('--master', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    image = Dos33Image(args.master)
    image.data[:] = bytes(len(image.data))
    image._init_catalog()
    # Fixed-sector modules occupy tracks 0-15. The normal DOS catalog and
    # allocation bitmap keep them unavailable to the editor's SAVE command.
    for t in range(16):
        for s in range(16):
            image.free[t, s] = False
    def put(sector, data, capacity):
        assert len(data) <= capacity, (sector, len(data), capacity)
        offset = sector * 256
        image.data[offset:offset+len(data)] = data
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
