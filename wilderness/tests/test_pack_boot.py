#!/usr/bin/env python3
"""Minimum-size LZ parses, long windows and DOS layout payload integrity."""
from functools import lru_cache
from pathlib import Path
import random
import tempfile
from common import HERE, DISK
from pack_boot import compress, decompress
from build_disk import build_disk
from dos33 import catalog, file_sectors


def minimum_size(data):
    # Independent exhaustive token enumeration, including overlapping copies.
    @lru_cache(None)
    def visit(pos, phase):
        if pos == len(data):
            return 0
        following = (phase + 1) % 8
        cost = 1 + visit(pos + 1, following)
        for previous in range(max(0, pos - 4095), pos):
            length = 0
            while length < min(255, len(data) - pos) and data[previous + length] == data[pos + length]:
                length += 1
            for count in range(3, length + 1):
                cost = min(cost, 2 + (count >= 18) + visit(pos + count, following))
        return cost + (phase == 0)
    return visit(0, 0)


def main():
    cases = 0
    for length in range(10):
        for value in range(1 << length):
            data = bytes((value >> bit) & 1 for bit in range(length))
            packed = compress(data)
            assert len(packed) == minimum_size(data), (length, value)
            assert decompress(packed, length) == data
            cases += 1
    for length, size in ((17, 4), (18, 4), (19, 5), (255, 5), (256, 5)):
        assert len(compress(bytes(length))) == size, length
    rng = random.Random(4095)
    prefix = rng.randbytes(4095)
    for data in (prefix + prefix[:255], prefix + b'x' + prefix[:255],
                 rng.randbytes(9472), bytes(9472), bytes(range(256)) * 37):
        assert decompress(compress(data), len(data)) == data
    print(f'  {cases} exhaustive shortest parses; flag, length and 4 KB window boundaries: OK')

    image = DISK.read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        reference = Path(tmp) / 'unskewed.dsk'
        build_disk(reference, track_skew=0)
        unskewed = reference.read_bytes()
        assert image[:3 * 16 * 256] == unskewed[:3 * 16 * 256], 'DOS system changed'
        assert [entry[:4] for entry in catalog(image)] == [entry[:4] for entry in catalog(unskewed)]
        for name, *_ in catalog(image):
            def raw(disk):
                return b''.join(disk[offset:offset + 256] for offset in file_sectors(disk, name))
            assert raw(image) == raw(unskewed), name
        assert sum(name.startswith('WILDPAK') for name, *_ in catalog(image)) == 2
    print('  skewed/unskewed DOS files identical; unchanged system tracks; default boot fits two files: OK')


if __name__ == '__main__':
    main()
