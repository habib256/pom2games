#!/usr/bin/env python3
"""Print the NEOWILD.DAT records and the auxiliary placement of build/layout.json."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def main():
    layout = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else HERE / 'build/layout.json').read_text())
    dat = layout['dat']
    print(f'NEOWILD.DAT ({layout["packing"]}): {dat["raw"]} bytes -> {dat["stored"]} stored, '
          f'{dat["records"]} records, file {dat["file"]} bytes; volume '
          f'{layout["blocks_used"]}/{layout["blocks"]} blocks')
    for index, module in sorted(layout['modules'].items(), key=lambda kv: int(kv[0])):
        print(f'  module {int(index):2} {module["bank"]:3} ${module["address"]:04X} '
              f'{module["length"]:5} -> ${module["window"]:04X}  {module["image"]}')
    for free in layout['aux_free']:
        print(f'  free {free["bank"]:3} ${free["start"]:04X}-${free["end"]-1:04X} {free["free"]:5} bytes')


if __name__ == '__main__':
    main()
