#!/usr/bin/env python3
"""Measure guest cycles/DOS reads and fingerprint outcomes of common actions.

An older disk must be paired with its own ld65 label file. JSON output can
be compared before/after without relying on host speed or shifted addresses.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import a2test


def measure(disk, labels, command, setup=()):
    L = a2test.labels(labels)
    with a2test.Session(disk) as s:
        s.step(L.until('idle', 20000))
        s.step(L.poke('nature_frequency', 0))
        for preceding in setup:
            s.step(f'key:{preceding}\\r')
            s.step(L.until('idle', 20000))
        s.step(f'key:{command}')
        s.step('press:\\r')
        start = s.step(L.until('do_command', 20000)).cycles[-1]
        reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
        target = dict(STATUS='status_key', INVENTORY='inventory_key',
                      HELP='help_key', TOPO='topo_key').get(command, 'idle')
        end = s.step(L.until(target, 20000)).cycles[-1]
        reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little') - reads
        if target != 'idle':
            s.step('key:\\e')
            s.step(L.until('idle', 20000))
        fields = {name: s.step(L.peek(name, length)).data.hex() for name, length in
                  (('px', 6), ('s_hour', L['s_t0'] + 5 - L['s_hour']),
                   ('it_place', 76), ('it_pack_lo', 76), ('it_pack_hi', 76),
                   ('it_gnd_lo', 76), ('it_gnd_hi', 76), ('injury_active', 15))}
        page = s.step('peek:2000:8192').data
        visible = b''.join(page[a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for y in range(176))
        fields['picture'] = hashlib.sha256(visible).hexdigest()
        return dict(cycles=end-start, seconds=round((end-start)/a2test.CPU_HZ, 3),
                    reads=reads, outcome=fields)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--disk', type=Path, default=HERE.parent/'dist/WILDERNESS.dsk')
    p.add_argument('--labels', type=Path, default=HERE/'build/wild.lbl')
    p.add_argument('--out', type=Path)
    p.add_argument('--setup', action='append', default=[], help='preceding inline action, e.g. REST 1 H')
    p.add_argument('commands', nargs='*', default=['VIEW', 'LOOK R', 'STATUS', 'REST 1 H', 'SLEEP 8 H', 'WALK 1 H'])
    args = p.parse_args()
    results = {}
    for command in args.commands:
        results[command] = value = measure(args.disk, args.labels, command, args.setup)
        print(f'{command:12} {value["cycles"]:10} cycles  {value["seconds"]:7.3f} s  {value["reads"]} reads', flush=True)
    if args.out:
        args.out.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    main()
