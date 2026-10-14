#!/usr/bin/env python3
"""Print the NEOWILD.DAT records, the region packs and the auxiliary placement of build/layout.json."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def main():
    layout = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else HERE / 'build/layout.json').read_text())
    dat = layout['dat']
    print(f'NEOWILD.DAT ({layout["packing"]}): trunk {dat["raw"]} bytes -> {dat["stored"]} stored, '
          f'{dat["records"]} records, {dat["file"]} bytes; with the packs and the preparation '
          f'{layout["dat_file"]["bytes"]} bytes, {layout["dat_file"]["blocks"]} blocks; volume '
          f'{layout["blocks_used"]}/{layout["blocks"]} blocks')
    for index, module in sorted(layout['modules'].items(), key=lambda kv: int(kv[0])):
        lz = f' LZ {module["stored"]:4} (copy ${module["lz"]["copy"]:04X})' if 'lz' in module else ''
        print(f'  module {int(index):2} {module["bank"]:3} ${module["address"]:04X} '
              f'{module["length"]:5} -> ${module["window"]:04X}  {module["image"]}{lz}')
    for free in layout['aux_free']:
        print(f'  free {free["bank"]:3} ${free["start"]:04X}-${free["end"]-1:04X} {free["free"]:5} bytes'
              ' (with the Sierra Nevada pack)')
    area = layout['pack_area']
    print(f'pack sprite area ${area["start"]:04X}-${area["end"]-1:04X}; trunk leaves '
          f'{layout["aux_trunk_free"]} bytes; {layout["blocks_free"]} blocks free')
    for region, pack in layout['packs'].items():
        print(f'  R{region} @{pack["mark"]:6} {pack["name"]:16} {pack["raw"]:5} -> {pack["stored"]:5} bytes, '
              f'{pack["records"]} records; sprites {pack["sprite_bytes"]:4} '
              f'({", ".join(pack["sprites"])}); aux free {pack["aux_free"]}'
              f' (largest piece {pack["aux_free_largest"]})')
    geo = layout.get('geo')
    if isinstance(geo, dict):
        area = f'lc1 ${geo["cache"]:04X}-${geo.get("store_start", 0xFFFA) - 1:04X}'
        if geo['loaded']:
            print(f'  fine geography {area} (NEOWILD.R2): cache {geo["code_address"] - geo["cache"]}, '
                  f'code {geo["code"]}, atlas {geo["size"]} bytes ({geo["tiles"]} tiles, '
                  f'{geo["raw_tiles"]} raw), {geo["free"]} free; no TOPO snapshot')
        else:
            print(f'  fine geography {area}: legacy map, area used by the TOPO snapshot '
                  f'(native atlas budget {geo["budget"]} bytes, code {geo["code"]})')


if __name__ == '__main__':
    main()
