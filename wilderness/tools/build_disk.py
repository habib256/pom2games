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


def build_disk(out, map_path=None, build=None, master=None):
    build = Path(build) if build else HERE / 'build'
    out = Path(out)
    # Alternate-map tests keep their packages alongside their temporary disk.
    packages = write_packages(build, out.parent / 'boot-packages' if map_path else build / 'boot-packages',
                              Path(map_path).read_bytes() if map_path else None)
    disk = Dos33Image(master or HERE.parent / 'dev/tools/dos33_system.bin', read_fast=True)
    program = tokenize_applesoft((HERE / 'src/hello.bas').read_text())
    disk.add_file('HELLO', TYPE_A, struct.pack('<H', len(program)) + program)

    def binary(name, path, address):
        data = path.read_bytes()
        disk.add_file(name, TYPE_B, struct.pack('<HH', address, len(data)) + data)

    binary('WILDBOOT', build / 'boot.bin', 0x5800)
    for index, path in enumerate(packages, 1):
        binary(f'WILDPAK{index}', path, 0x2000)
    for name, path, address in [
            ('WILDTRE', build / 'wildtre.bin', 0x5800),
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
        binary(name, path, address)
    disk.save(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--map')
    parser.add_argument('--build')
    parser.add_argument('--master')
    args = parser.parse_args()
    build_disk(args.out, args.map, args.build, args.master)
