#!/usr/bin/env python3
"""ProDOS reader corruption checks and writer/reader round trips."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/prodos'))
from read_volume import Image, BLOCK
from build_volume import Volume


def entry(storage, key, size):
    e = bytearray(39)
    e[0] = storage << 4 | 1
    e[1] = ord('A')
    e[17:19] = key.to_bytes(2, 'little')
    e[21:24] = size.to_bytes(3, 'little')
    return e


class ReaderTests(unittest.TestCase):
    def test_round_trips(self):
        for size in (0, 1, 512, 513, 131072, 131073):
            with self.subTest(size=size):
                volume = Volume('TEST', 400, b'', (0, 0))
                data = bytes(i % 251 for i in range(size))
                storage, key, _ = volume.write_file(data)
                self.assertEqual(Image(volume.image).read(entry(storage, key, size)), data)

    def test_bad_block(self):
        for n in (-1, 1, 2):
            with self.subTest(n=n), self.assertRaises(ValueError):
                Image(bytes(700)).block(n)

    def test_cycle_in_chain(self):
        data = bytearray(3 * BLOCK)
        data[2 * BLOCK + 2:2 * BLOCK + 4] = (2).to_bytes(2, 'little')
        with self.assertRaisesRegex(ValueError, 'chain'):
            Image(data).entries(2)

    def test_cycle_in_hierarchy(self):
        data = bytearray(3 * BLOCK)
        data[2 * BLOCK + 43:2 * BLOCK + 82] = entry(13, 2, 0)
        with self.assertRaisesRegex(ValueError, 'hierarchy'):
            list(Image(data).walk())

    def test_size_overflow(self):
        for storage, size in ((1, 513), (2, 131073)):
            with self.subTest(storage=storage), self.assertRaisesRegex(ValueError, 'capacity'):
                Image(bytes(3 * BLOCK)).read(entry(storage, 1, size))

    def test_sparse_files(self):
        for storage in (2, 3):
            with self.subTest(storage=storage):
                data = b'X' * BLOCK + bytes(BLOCK)
                self.assertEqual(Image(data).read(entry(storage, 1, 1025)), bytes(1025))

    def test_short_entry(self):
        with self.assertRaises(ValueError):
            Image(bytes(BLOCK)).read(bytes(23))


if __name__ == '__main__':
    unittest.main()
