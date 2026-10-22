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
import a2profile


def measure(disk, labels, command, setup=(), profile=False):
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
        breakdown = None
        if profile:
            result = s.step(f'pcprof:{L[target]:04X}:20000')
            end = start + result.cycles[-1]
            breakdown = dict(resident=0, simulation=0, overlays=0, DOS=0, ROM=0)
            for address, cycles in a2profile.pcs(result.out).items():
                region = ('ROM' if address >= 0xD000 else
                          'DOS' if address >= 0x9600 else
                          'overlays' if 0x5800 <= address < 0x6000 else
                          'simulation' if 0x2000 <= address < 0x4000 else 'resident')
                breakdown[region] += cycles
            assert sum(breakdown.values()) == end - start
        else:
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
        value = dict(cycles=end-start, seconds=round((end-start)/a2test.CPU_HZ, 3),
                     reads=reads, outcome=fields)
        if breakdown is not None:
            value['profile'] = breakdown
        return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--disk', type=Path, default=HERE/'build/WILDERNESS.dsk')
    p.add_argument('--labels', type=Path, default=HERE/'build/wild.lbl')
    p.add_argument('--out', type=Path)
    p.add_argument('--profile', action='store_true', help='count guest instruction cycles by memory region')
    p.add_argument('--setup', action='append', default=[], help='preceding inline action, e.g. REST 1 H')
    p.add_argument('commands', nargs='*', default=['VIEW', 'LOOK R', 'STATUS', 'REST 1 H', 'SLEEP 8 H', 'WALK 1 H'])
    args = p.parse_args()
    results = {}
    for command in args.commands:
        results[command] = value = measure(args.disk, args.labels, command, args.setup, args.profile)
        print(f'{command:12} {value["cycles"]:10} cycles  {value["seconds"]:7.3f} s  {value["reads"]} reads', flush=True)
        if args.profile:
            for region, cycles in value['profile'].items():
                print(f'  {region:12} {cycles/a2test.CPU_HZ:7.3f} s  {100*cycles/value["cycles"]:5.1f}%', flush=True)
    if args.out:
        args.out.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    main()
