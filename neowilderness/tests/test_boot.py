#!/usr/bin/env python3
"""NEOWILD.SYSTEM must restore every resident main-RAM byte before start.

Auxiliary RAM is checked through the transfers in test_overlay_codec.py.
A little-compressible map exercises raw records, LZ literals and the
chunking of the map into several records.
"""
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
    # RESIDENT: the module directory is filled in by tools/build_disk.py.
    resident = bytearray((HERE / 'build/wildres.bin').read_bytes())
    start = L['module_dir'] - 0xB600
    directory = slice(start, start + 23 * 7)
    steps = [L.until('start', 20000)]
    steps += [f'peek:{address:04X}:{len(data)}' for address, data in expected]
    steps += [f'peek:B600:{len(resident)}']
    result = a2test.run(disk, steps, timeout=900)
    memory = {address + i: byte for address, row in result.rows
              for i, byte in enumerate(row)}
    for address, data in expected:
        actual = bytes(memory[address + i] for i in range(len(data)))
        assert actual == data, f'resident bytes differ at ${address:04X}'
    actual = bytearray(memory[0xB600 + i] for i in range(len(resident)))
    loaded_directory = bytes(actual[directory])
    actual[directory] = resident[directory]
    assert actual == resident, 'RESIDENT image differs'
    for index in range(23):
        bank, source, length, window = (loaded_directory[index*7],
            int.from_bytes(loaded_directory[index*7+1:index*7+3], 'little'),
            int.from_bytes(loaded_directory[index*7+3:index*7+5], 'little'),
            int.from_bytes(loaded_directory[index*7+5:index*7+7], 'little'))
        assert bank in (0, 1, 2) and 0 < length <= 0x2000 and window in (0x2000, 0x5800, 0x9600), index
        assert bank or not (0x2000 <= source < 0x4000 or source < 0x0800), (index, 'reserved aux')
    print(f'  {disk.name}: every resident byte restored, directory sane, '
          f'{result.cycles[0] / a2test.CPU_HZ:.2f} s to start')


def main():
    mapbin = (HERE / 'build/map.bin').read_bytes()
    check(DISK, mapbin)
    noise = bytearray(mapbin)
    noise[64:] = random.Random(9408).randbytes(len(mapbin) - 64)
    with tempfile.TemporaryDirectory() as tmp:
        check(disk_with(tmp, noise), bytes(noise))
    print('ProDOS preload: OK')


if __name__ == '__main__':
    main()
