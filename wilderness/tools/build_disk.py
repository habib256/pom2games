#!/usr/bin/env python3
"""Build Wilderness with packed boot files and DOS-compatible overlays."""
import argparse
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
from dos33 import Dos33Image, TYPE_A, TYPE_B, tokenize_applesoft
from pack_boot import write_packages
from pack_overlay import pack, MAGIC
from smalldos import DOS_P2L

# Measured on the Disk II path: small code overlays cost more to decode than
# they save. Keep the large simulation and the three useful sprite streams.
PACKED_MODULES = frozenset(('WILDSIM', 'WILDPLN', 'WILDBER', 'WILDHUT'))


class WildernessDisk(Dos33Image):
    """DOS files with nine-sector interleave and a measured track skew."""

    def __init__(self, master, track_skew=1):
        if not 0 <= track_skew < 16:
            raise ValueError('track skew must be between 0 and 15')
        super().__init__(master, read_fast=True)
        self.track_skew = track_skew

    def alloc(self):
        for track in (*range(18, 35), *range(16, 2, -1)):
            for index in range(16):
                physical = (15 + self.track_skew * (track - 18) + 9 * index) % 16
                sector = DOS_P2L[physical]
                if self.free[track, sector]:
                    self.free[track, sector] = False
                    return track, sector
        raise SystemExit('disk full')


def build_disk(out, map_path=None, build=None, master=None, track_skew=1):
    build = Path(build) if build else HERE / 'build'
    out = Path(out)
    # Alternate-map tests keep their packages alongside their temporary disk.
    packages = write_packages(build, out.parent / 'boot-packages' if map_path else build / 'boot-packages',
                              Path(map_path).read_bytes() if map_path else None)
    disk = WildernessDisk(master or HERE.parent / 'dev/tools/dos33_system.bin', track_skew)
    program = tokenize_applesoft((HERE / 'src/hello.bas').read_text())
    disk.add_file('HELLO', TYPE_A, struct.pack('<H', len(program)) + program)

    def binary(name, path, address, packed=False):
        original = path.read_bytes()
        data = original
        if packed:
            data = pack(data)
        payload = struct.pack('<HH', address, len(data)) + data
        # The binary header limits BLOAD to the packed bytes. Reserve the old
        # extent, owned by this file, so subsequent overlays retain their
        # physical placement and rotational timing. Padding is never loaded.
        payload += bytes(len(original) - len(data))
        disk.add_file(name, TYPE_B, payload)

    binary('WILDBOOT', build / 'boot.bin', 0x5800)
    for index, path in enumerate(packages, 1):
        binary(f'WILDPAK{index}', path, 0x2000)
    for name, path, address in [
            ('WILDTRE', build / 'wildtre.bin', 0x5800),
            ('WILDADV', build / 'wildadv.bin', 0x5800),
            ('WILDOUT', build / 'wildout.bin', 0x5800),
            ('WILDWAT', build / 'wildwat.bin', 0x5800),
            ('WILDSIM', build / 'wildsim.bin', 0x2000),
            ('WILDPLN', build / 'original_graphics/wreck.bin', 0x5800),
            ('WILDVOC', build / 'wildvoc.bin', 0x5800),
            ('WILDSCR', build / 'wildscr.bin', 0x5800),
            ('WILDSTA', build / 'wildsta.bin', 0x5800),
            ('WILDHUD', build / 'wildhud.bin', 0x5800),
            ('WILDINP', build / 'wildinp.bin', 0x5800),
            ('WILDITM', build / 'wilditm.bin', 0x5800),
            ('WILDTRV', build / 'wildtrv.bin', 0x5800),
            ('WILDMED', build / 'wildmed.bin', 0x5800),
            ('WILDMVI', build / 'wildmvi.bin', 0x5800),
            ('WILDSIT', build / 'wildsit.bin', 0x5800),
            ('WILDPRJ', build / 'wildprj.bin', 0x5800),
            ('WILDBER', build / 'original_graphics/bear.bin', 0x5800),
            ('WILDCOU', build / 'original_graphics/cougar.bin', 0x5800),
            ('WILDRAT', build / 'original_graphics/rattlesnake.bin', 0x5800),
            ('WILDHUT', build / 'original_graphics/cabin.bin', 0x5800)]:
        assert not path.read_bytes().startswith(MAGIC), f'{name}: raw compression marker collision'
        binary(name, path, address, packed=name in PACKED_MODULES)
    if map_path:
        from mkmap import MAP_BYTES, FOREST_BYTES
        mapdata = Path(map_path).read_bytes()
        if mapdata[37]:
            fine = mapdata[MAP_BYTES+FOREST_BYTES:]
            assert len(fine) == 224*168 + 28*168, 'incomplete native geography'
            heights, woods = fine[:224*168], fine[224*168:]
            lookup = (build / 'wildgeo.bin').read_bytes()[0x700:]
            for bank in range(24):
                row = bank*7
                data = heights[row*224:(row+7)*224] + woods[row*28:(row+7)*28]
                payload = data + bytes(0x700-len(data)) + lookup
                disk.add_file('WILDG'+chr(ord('A')+bank), TYPE_B,
                              struct.pack('<HH', 0x5800, len(payload)) + payload)
    disk.save(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--map')
    parser.add_argument('--build')
    parser.add_argument('--master')
    parser.add_argument('--track-skew', type=int, choices=range(16), default=1)
    args = parser.parse_args()
    build_disk(args.out, args.map, args.build, args.master, args.track_skew)
