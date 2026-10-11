#!/usr/bin/env python3
"""The real DOS boot must restore every resident byte before entering start."""
import random
import tempfile
from common import HERE, L, DISK, a2test, disk_with


def check(disk, mapbin):
    regions = [('wildforest.bin', 0x0926), ('wildtxt.bin', 0x0A00), ('wildlo.bin', 0x1000),
               ('wildgame.bin', 0x4000), ('wild.bin', 0x6000)]
    expected = [(address, (HERE / 'build' / name).read_bytes()) for name, address in regions]
    from mkmap import MAP_BYTES, FOREST_BYTES
    expected.append((0x7000, mapbin[:MAP_BYTES]))
    mask = mapbin[MAP_BYTES:MAP_BYTES+FOREST_BYTES] if mapbin[26] else b''
    expected.append((0x0800, mask if len(mask)==FOREST_BYTES else bytes(FOREST_BYTES)))
    steps = [L.until('start', 20000)]
    steps += [f'peek:{address:04X}:{len(data)}' for address, data in expected]
    result = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    # Adjacent regions can be joined by the dump decoder (MAIN now ends at
    # $7000, where MAP starts). Compare by address instead of dump grouping.
    memory = {address + i: byte for address, row in result.rows
              for i, byte in enumerate(row)}
    for address, data in expected:
        actual = bytes(memory[address + i] for i in range(len(data)))
        assert actual == data, f'resident bytes differ at ${address:04X}'
    print(f'  {disk.name}: every resident byte restored, {result.cycles[0] / a2test.CPU_HZ:.2f} s')


def main():
    mapbin = (HERE / 'build/map.bin').read_bytes()
    check(DISK, mapbin)
    # Little-compressible maps require another packed file and exercise the
    # literal path, input page crossings and output across all three map chunks.
    noise = bytearray(mapbin)
    noise[64:] = random.Random(9408).randbytes(len(mapbin) - 64)
    with tempfile.TemporaryDirectory() as tmp:
        check(disk_with(tmp, noise), bytes(noise))
    print('Packed DOS boot: OK')


if __name__ == '__main__':
    main()
