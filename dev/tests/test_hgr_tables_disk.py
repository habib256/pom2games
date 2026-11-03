#!/usr/bin/env python3
"""Check shared HGR lookups and fixed DOS-sector placement invariants."""
import sys
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import hgr_tables as hgr
import dos33
import dos33patch
from dos33 import Dos33Image, catalog, read_file, TYPE_B


class Tables(unittest.TestCase):
    def test_scanlines_and_pixel_columns(self):
        offsets = [hgr.hgr_offset(y) for y in range(192)]
        self.assertEqual([offsets[y] for y in (0,1,7,8,63,64,128,191)],
                         [0,1024,7168,128,8064,40,80,8144])
        pixels = {offset + col for offset in offsets for col in range(40)}
        self.assertEqual(len(pixels), 7680)
        self.assertLess(max(pixels), 8192)
        for page in (0x2000,0x4000):
            low, high = hgr.scanline_tables(page)
            self.assertEqual([a | b << 8 for a,b in zip(low,high)],
                             [page + offset for offset in offsets])
        quotient, remainder = hgr.division_tables(280)
        self.assertTrue(all(q*7+r == x and 0 <= r < 7
                            for x,(q,r) in enumerate(zip(quotient,remainder))))
        self.assertEqual((quotient[279],remainder[279]),(39,6))
        for fn,arg in ((hgr.hgr_offset,-1),(hgr.hgr_offset,192),
                       (hgr.scanline_tables,0x3000),(hgr.division_tables,281)):
            with self.assertRaises(ValueError):
                fn(arg)

    def test_shift_pixels_and_palette(self):
        low, high = hgr.shift_tables()
        self.assertEqual((len(low),len(high)),(1536,1536))
        for phase in range(1,7):
            for value in range(256):
                a,b=low[(phase-1)*256+value], high[(phase-1)*256+value]
                self.assertEqual((a&127) | (b&127)<<7,(value&127)<<phase)
                for byte in (a,b):
                    self.assertEqual(byte&128,128 if value&128 and byte&127 else 0)


class FixedDisk(unittest.TestCase):
    def test_placement_and_saved_allocation(self):
        image=Dos33Image.blank()
        image.reserve_sectors(0,256)
        image.reserve_sectors(0,256)  # repeat is harmless
        image.write_fixed(0,b'BOOT',256)
        image.write_fixed(32,b'CODE',512)
        image.add_file('DATA',TYPE_B,struct.pack('<HH',0x6000,7)+b'payload')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixed.dsk'
            image.save(path)
            disk=path.read_bytes()
        self.assertEqual(len(disk),143360)
        self.assertEqual(disk[:256],b'BOOT'+bytes(252))
        self.assertEqual(disk[8192:8704],b'CODE'+bytes(508))
        vtoc=disk[17*4096:17*4096+256]
        self.assertTrue(all(vtoc[0x38+t*4:0x3c+t*4] == bytes(4) for t in range(16)))
        self.assertEqual([entry[0] for entry in catalog(disk)],['DATA'])
        self.assertEqual(read_file(disk,'DATA'),b'payload')

    def test_rejections_do_not_mutate(self):
        image=Dos33Image.blank()
        image.reserve_sectors(0,16)
        image.write_fixed(2,b'OK',256)
        calls=[lambda: image.reserve_sectors(-1,1),
               lambda: image.reserve_sectors(559,2),
               lambda: image.write_fixed(3,bytes(257),256),
               lambda: image.write_fixed(3,b'',255),
               lambda: image.write_fixed(16,b'',256),
               lambda: image.write_fixed(2,b'',256),
               lambda: image.write_fixed(559,b'',512),
               lambda: image.write_fixed(272,b'',256)]
        for call in calls:
            before=(bytes(image.data),image.free.copy(),image._fixed_reserved.copy(),image._fixed_regions.copy())
            with self.assertRaises(ValueError):
                call()
            self.assertEqual(before,(bytes(image.data),image.free,image._fixed_reserved,image._fixed_regions))
        image.add_file('DATA',TYPE_B,struct.pack('<HH',0x6000,7)+b'payload')
        allocated=next(t*16+s for t,s,*_ in image.catalog)
        with self.assertRaises(ValueError):
            image.reserve_sectors(allocated,1)


class DiskValidation(unittest.TestCase):
    def setUp(self):
        image = Dos33Image.blank()
        image.add_file('GAME', TYPE_B, struct.pack('<HH', 0x6000, 16) + bytes(16))
        image.write_vtoc()
        self.disk = bytearray(image.data)

    def test_catalog_cycle(self):
        t, s = self.disk[17 * 4096 + 1:17 * 4096 + 3]
        off = (t * 16 + s) * 256
        self.disk[off + 1:off + 3] = bytes((t, s))
        with self.assertRaisesRegex(ValueError, 'cyclic DOS catalog'):
            catalog(self.disk)

    def test_sector_list_cycle(self):
        *_, t, s = catalog(self.disk)[0]
        off = (t * 16 + s) * 256
        self.disk[off + 1:off + 3] = bytes((t, s))
        with self.assertRaisesRegex(ValueError, 'cyclic DOS track'):
            read_file(self.disk, 'GAME')

    def test_invalid_data_sector(self):
        *_, t, s = catalog(self.disk)[0]
        off = (t * 16 + s) * 256
        self.disk[off + 12:off + 14] = bytes((35, 0))
        with self.assertRaises(ValueError):
            read_file(self.disk, 'GAME')

    def test_truncated_sector(self):
        with self.assertRaisesRegex(ValueError, 'truncated'):
            catalog(self.disk[:100])

    def test_patch_bounds_and_atomicity(self):
        original = bytes(self.disk)
        for start in (0x5ffe, 0x600f, 0x6010):
            with self.subTest(start=start):
                with self.assertRaises(SystemExit):
                    dos33patch.patch(self.disk, 'GAME',
                                     {'T': start, 'S': start + 1},
                                     tslists=[('T', 'S', 'GAME')])
                self.assertEqual(bytes(self.disk), original)
        dos33patch.patch(self.disk, 'GAME', {'T': 0x600e, 'S': 0x600f},
                         tslists=[('T', 'S', 'GAME')])
        self.assertEqual(read_file(self.disk, 'GAME')[14:],
                         bytes(catalog(self.disk)[0][-2:]))


if __name__ == '__main__':
    unittest.main()
