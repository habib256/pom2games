#!/usr/bin/env python3
"""Measure guest cycles, disk and RAM-transfer costs, and fingerprint outcomes.

An older disk must be paired with its own ld65 label file (the frozen HGR
reference: build/reference-hgr). JSON output can be compared before/after
without relying on host speed or shifted addresses. A .po volume runs on the
enhanced //e; its profile separates the RAM transfers (memory.s and the
stack-page loop) from compute, and counts every MLI call. On a native map
(fine geography, lot 5) it also counts, per command, the geography queries
and the tiles decoded by src/geoaux.s (geo_queries, geo_decodes). The
decoder runs from the auxiliary language card ($D480 and up), which the
profile cannot tell from the ROM by address: it is counted under ROM.
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


# Raw keys measured from turn_view to the next command prompt.
TURN_KEYS = {'RIGHT': '\\>', 'LEFT': '\\<'}


def measure(disk, labels, command, setup=(), profile=False):
    L = a2test.labels(labels)
    resident = 'mem_fetch' in L
    counters = (('mli_calls', 2), ('xfer_count', 2), ('xfer_bytes', 3)) if resident else ()
    if 'geo_decodes' in L:
        counters += (('geo_queries', 3), ('geo_decodes', 2))
    with a2test.Session(disk, iie=str(disk).endswith('.po')) as s:
        if 'menu_key' in L:
            # Lot 7 start menu: the Sierra Nevada at level 4 (tests/common.py).
            s.step(L.until('menu_key', 40000))
            s.step('key:1\\r')
        s.step(L.until('idle', 20000))
        s.step(L.poke('nature_frequency', 0))
        for preceding in setup:
            s.step(f'key:{preceding}\\r')
            s.step(L.until('idle', 20000))
        if command in TURN_KEYS:
            # Arrow turns on the empty command line never reach do_command.
            s.step(f'press:{TURN_KEYS[command]}')
            start = s.step(L.until('turn_view', 20000)).cycles[-1]
        else:
            s.step(f'key:{command}')
            s.step('press:\\r')
            start = s.step(L.until('do_command', 20000)).cycles[-1]
        reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
        before = {n: int.from_bytes(s.step(L.peek(n, k)).data, 'little') for n, k in counters}
        target = dict(STATUS='status_key', INVENTORY='inventory_key',
                      HELP='help_key', TOPO='graphical_topo_key', T='graphical_topo_key',
                      MAP='topo_key').get(command, 'idle')
        breakdown = None
        if profile:
            result = s.step(f'pcprof:{L[target]:04X}:20000')
            end = start + result.cycles[-1]
            if resident:
                breakdown = dict(resident=0, simulation=0, overlays=0, transfers=0, ROM=0)
            else:
                breakdown = dict(resident=0, simulation=0, overlays=0, DOS=0, ROM=0)
            for address, cycles in a2profile.pcs(result.out).items():
                if resident:
                    # No MLI call happens during commands (test_resident.py):
                    # $D000+ is the Applesoft/Monitor ROM only.
                    region = ('ROM' if address >= 0xD000 else
                              'transfers' if 0xB600 <= address < 0xBA00 or 0x0100 <= address < 0x0200 else
                              'simulation' if 0x9600 <= address < 0xB600 else
                              'overlays' if 0x5800 <= address < 0x6000 else 'resident')
                else:
                    region = ('ROM' if address >= 0xD000 else
                              'DOS' if address >= 0x9600 else
                              'overlays' if 0x5800 <= address < 0x6000 else
                              'simulation' if 0x2000 <= address < 0x4000 else 'resident')
                breakdown[region] += cycles
            assert sum(breakdown.values()) == end - start
        else:
            end = s.step(L.until(target, 20000)).cycles[-1]
        reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little') - reads
        deltas = {n: int.from_bytes(s.step(L.peek(n, k)).data, 'little') - before[n]
                  for n, k in counters}
        back = None
        if target != 'idle':
            # Return to the view (lot 4: no raycast after a screen).
            s.step('press:\\e')
            back = s.step(L.until('idle', 20000)).cycles[-1]
        fields = {name: s.step(L.peek(name, length)).data.hex() for name, length in
                  (('px', 6), ('s_hour', L['s_t0'] + 5 - L['s_hour']),
                   ('it_place', 76), ('it_pack_lo', 76), ('it_pack_hi', 76),
                   ('it_gnd_lo', 76), ('it_gnd_hi', 76), ('injury_active', 15))}
        page = s.step('peek:2000:8192').data
        visible = b''.join(page[a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for y in range(176))
        if 'dhgr_frame' in L:
            # DHGR: the auxiliary bank too (PAGE2 under 80STORE).
            s.step('poke:C055:00')
            aux = s.step('peek:2000:8192').data
            s.step('poke:C054:00')
            visible += b''.join(aux[a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for y in range(176))
        fields['picture'] = hashlib.sha256(visible).hexdigest()
        value = dict(cycles=end-start, seconds=round((end-start)/a2test.CPU_HZ, 3),
                     reads=reads, outcome=fields)
        if back is not None:
            value['return_seconds'] = round((back - end) / a2test.CPU_HZ, 3)
        if resident:
            value.update(disk_calls=deltas['mli_calls'], transfers=deltas['xfer_count'],
                         transfer_bytes=deltas['xfer_bytes'])
        if 'geo_decodes' in deltas:
            value.update(geo_queries=deltas['geo_queries'], geo_decodes=deltas['geo_decodes'])
        if breakdown is not None:
            value['profile'] = breakdown
        return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--disk', type=Path, default=HERE.parent/'dist/NEOWILDERNESSXL.po')
    p.add_argument('--labels', type=Path, default=HERE/'build/wild.lbl')
    p.add_argument('--out', type=Path)
    p.add_argument('--profile', action='store_true', help='count guest instruction cycles by memory region')
    p.add_argument('--setup', action='append', default=[], help='preceding inline action, e.g. REST 1 H')
    p.add_argument('commands', nargs='*', default=['VIEW', 'LOOK R', 'STATUS', 'REST 1 H', 'SLEEP 8 H', 'WALK 1 H'])
    args = p.parse_args()
    results = {}
    for command in args.commands:
        results[command] = value = measure(args.disk, args.labels, command, args.setup, args.profile)
        back = f'  return {value["return_seconds"]:6.3f} s' if 'return_seconds' in value else ''
        geo = (f'  {value["geo_queries"]} geography queries, {value["geo_decodes"]} tiles decoded'
               if value.get('geo_queries') else '')
        print(f'{command:12} {value["cycles"]:10} cycles  {value["seconds"]:7.3f} s  {value["reads"]} reads{back}{geo}',
              flush=True)
        if args.profile:
            for region, cycles in value['profile'].items():
                print(f'  {region:12} {cycles/a2test.CPU_HZ:7.3f} s  {100*cycles/value["cycles"]:5.1f}%', flush=True)
    if args.out:
        args.out.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    main()
