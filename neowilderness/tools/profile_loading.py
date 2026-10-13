#!/usr/bin/env python3
"""Measure the ProDOS boot and preload in the POM2 core (enhanced //e).

Usage: python3 tools/profile_loading.py [--packings raw,lz,auto] [--out FILE]

For each NEOWILD.DAT packing a volume is built in build/profile-boot/ and
booted: ProDOS boot until NEOWILD.SYSTEM's loader, then the preload split
into MLI/disk (ProDOS code at $BF00 and above), LZ decoding (ld_decode) and
loader copies, then game start until the first playable screen (the command
line idle loop, with the view drawn). Also the bytes read and MLI calls.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tests'))
sys.path.insert(0, str(HERE / 'tools'))
from common import L, a2test   # noqa: E402
from build_disk import build_disk   # noqa: E402

HZ = a2test.CPU_HZ


def measure(disk):
    steps = [L.until('loader_main', 20000), f'pcprof:{L["start"]:04X}:20000',
             L.until('idle', 20000)]
    steps += [L.peek(name, size) for name, size in
              (('mli_calls', 2), ('mli_reads', 2), ('mli_bytes', 3))]
    result = a2test.run(disk, steps, timeout=900)
    boot, preload_end, idle = result.cycles[0], None, result.cycles[-1]
    split = dict(disk=0, decode=0, loader=0)
    total = 0
    for address, cycles in re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', result.out, re.M):
        address, cycles = int(address, 16), int(cycles)
        total += cycles
        key = ('decode' if L['ld_decode'] <= address < L['ld_decode_end'] else
               'disk' if address >= 0xBF00 else 'loader')
        split[key] += cycles
    preload_end = boot + total
    calls, reads, read_bytes = (int.from_bytes(result.mem(L[n], k), 'little') for n, k in
                                (('mli_calls', 2), ('mli_reads', 2), ('mli_bytes', 3)))
    return dict(prodos_boot=round(boot / HZ, 3), preload=round(total / HZ, 3),
                preload_disk=round(split['disk'] / HZ, 3),
                preload_decode=round(split['decode'] / HZ, 3),
                preload_copies=round(split['loader'] / HZ, 3),
                start_to_playable=round((idle - preload_end) / HZ, 3),
                first_playable=round(idle / HZ, 3),
                mli_calls=calls, mli_reads=reads, bytes_read=read_bytes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packings', default='raw,lz,auto')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--map', type=Path, help='another map, e.g. a native map with its '
                        'fine geography (mkmap.py --native): its atlas is preloaded too')
    args = parser.parse_args()
    work = HERE / 'build/profile-boot'
    work.mkdir(parents=True, exist_ok=True)
    results = {}
    for packing in args.packings.split(','):
        disk = work / f'{packing}.po'
        info = build_disk(disk, args.map, packing=packing)
        value = measure(disk)
        value.update(dat_raw=info['dat']['raw'], dat_stored=info['dat']['stored'],
                     records=info['dat']['records'], volume_blocks=info['blocks_used'])
        results[packing] = value
        print(f'{packing:5} ' + ', '.join(f'{k} {v}' for k, v in value.items()), flush=True)
    if args.out:
        args.out.write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
