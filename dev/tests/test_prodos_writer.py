#!/usr/bin/env python3
"""Validate volume bounds and repeated allocation bitmap generation."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/prodos'))
from build_volume import Volume, BLOCK
from read_volume import Image


class WriterTests(unittest.TestCase):
    def volume(self, blocks=280, boot=b''):
        return Volume('TEST', blocks, boot, (0, 0))

    def test_volume_bounds(self):
        for blocks in (-1, 0, 6, 65536):
            with self.subTest(blocks=blocks), self.assertRaises(SystemExit):
                self.volume(blocks)
        for blocks in (7, 280, 65535):
            self.assertEqual(len(self.volume(blocks).image), blocks * BLOCK)

    def test_boot_cannot_overwrite_directory(self):
        with self.assertRaises(SystemExit):
            self.volume(boot=bytes(1025))
        self.assertEqual(self.volume(boot=b'A' * 1024).image[:1024], b'A' * 1024)

    def test_failed_alloc_does_not_change_state(self):
        volume = self.volume()
        for count in (-1, 0, 280):
            before = volume.next_free
            with self.subTest(count=count), self.assertRaises(SystemExit):
                volume.alloc(count)
            self.assertEqual(volume.next_free, before)
        self.assertEqual(volume.alloc(), 7)

    def test_negative_block(self):
        with self.assertRaises(SystemExit):
            self.volume().block(-1)

    def test_eof_overflow_rejected_before_allocation(self):
        volume = self.volume()
        before = volume.next_free
        with self.assertRaisesRegex(SystemExit, 'EOF'):
            volume.write_file(bytes(0x1000000))
        self.assertEqual(volume.next_free, before)

    def test_bitmap_refresh(self):
        # Also exercise a second bitmap block (volumes over 2 MiB).
        for blocks in (280, 4200):
            with self.subTest(blocks=blocks), tempfile.TemporaryDirectory() as tmp:
                volume = self.volume(blocks)
                volume.build(Path(tmp))
                old_free = Image(volume.image).free_blocks()
                volume.alloc(4)
                volume.write_bitmap()
                self.assertEqual(Image(volume.image).free_blocks(), old_free - 4)
                bitmap = bytes(volume.image)
                volume.write_bitmap()
                self.assertEqual(bytes(volume.image), bitmap)


if __name__ == '__main__':
    unittest.main()
