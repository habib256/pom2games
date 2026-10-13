#!/usr/bin/env python3
"""Measure the ProDOS boot and preload in the POM2 core (enhanced //e).

Usage: python3 tools/profile_loading.py [--packings raw,lz,auto] [--out FILE]

For each packing a volume is built in build/profile-boot/ and booted:
ProDOS boot until NEOWILD.SYSTEM's loader, then the preload of the common
trunk NEOWILD.DAT until the start menu, split into MLI/disk (ProDOS code at
$BF00 and above), LZ decoding (ld_decode) and loader copies; then, after
the choice (Sierra Nevada, level 4 by default; --choice N), the region pack
until start and the initialisation until the first playable screen (the
command line idle loop, with the view drawn). Also the bytes read and MLI
calls (lot 7).
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


def split(result, profile):
    """Cycles of one pcprof reply: MLI/disk, LZ decoding, loader copies."""
    out = dict(disk=0, decode=0, loader=0)
    for address, cycles in re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', profile, re.M):
        address, cycles = int(address, 16), int(cycles)
        key = ('decode' if L['ld_decode'] <= address < L['ld_decode_end'] else
               'disk' if address >= 0xBF00 else 'loader')
        out[key] += cycles
    return out


def measure(disk, choice='2'):
    """Boot to the menu (trunk preload), answer it, then the pack and the
    first view. Lot 7: the menu waits for a key, so the preload ends at
    menu_key and the latency choice -> first view starts at the RETURN."""
    with a2test.Session(disk, timeout=900, menu=False) as s:
        boot = s.step(L.until('loader_main', 20000)).cycles[-1]
        trunk = s.step(f'pcprof:{L["menu_key"]:04X}:20000')
        menu = boot + trunk.cycles[-1]
        s.step(f'key:{choice}')
        ret = s.step(L.until('menu_key', 100)).cycles[-1]     # level prompt waits
        s.step('press:\\r')
        chosen = s.step(L.until('loader_pack', 2000)).cycles[-1]
        pack = s.step(f'pcprof:{L["start"]:04X}:20000')
        start = chosen + pack.cycles[-1]
        idle = s.step(L.until('idle', 20000)).cycles[-1]
        calls, reads, read_bytes = (int.from_bytes(s.step(L.peek(n, k)).data, 'little') for n, k in
                                    (('mli_calls', 2), ('mli_reads', 2), ('mli_bytes', 3)))
    t, p = split(None, trunk.out), split(None, pack.out)
    # The RETURN is read at `ret`; the introduction is printed again before
    # the pack (`chosen`): both are in choice_to_view.
    return dict(prodos_boot=round(boot / HZ, 3), preload=round((menu - boot) / HZ, 3),
                preload_disk=round(t['disk'] / HZ, 3), preload_decode=round(t['decode'] / HZ, 3),
                preload_copies=round(t['loader'] / HZ, 3), menu=round(menu / HZ, 3),
                pack=round((start - chosen) / HZ, 3), pack_disk=round(p['disk'] / HZ, 3),
                pack_decode=round(p['decode'] / HZ, 3),
                start_to_playable=round((idle - start) / HZ, 3),
                introduction=round((chosen - ret) / HZ, 3),
                choice_to_view=round((idle - ret) / HZ, 3),
                first_playable_without_menu_wait=round((menu + idle - ret) / HZ, 3),
                mli_calls=calls, mli_reads=reads, bytes_read=read_bytes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packings', default='raw,lz,auto')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--choice', default='2', help='menu key: 1-6 (RETURN: level 4)')
    parser.add_argument('--map', type=Path, help='another Sierra Nevada map, e.g. a native map with its '
                        'fine geography (mkmap.py --native): its atlas is preloaded with the pack')
    args = parser.parse_args()
    work = HERE / 'build/profile-boot'
    work.mkdir(parents=True, exist_ok=True)
    results = {}
    for packing in args.packings.split(','):
        disk = work / f'{packing}.po'
        info = build_disk(disk, args.map, packing=packing)
        value = measure(disk, args.choice)
        pack = info['packs'][args.choice]
        value.update(dat_raw=info['dat']['raw'], dat_stored=info['dat']['stored'],
                     records=info['dat']['records'], pack_raw=pack['raw'],
                     pack_stored=pack['stored'], pack_records=pack['records'],
                     pack_blocks=pack['blocks'], volume_blocks=info['blocks_used'])
        results[packing] = value
        print(f'{packing:5} ' + ', '.join(f'{k} {v}' for k, v in value.items()), flush=True)
    if args.out:
        args.out.write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
