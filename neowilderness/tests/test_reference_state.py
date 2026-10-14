#!/usr/bin/env python3
"""Simulation state of the ProDOS/128 KB build against the frozen HGR build.

The same ordinary-play script (tests/scenario.py) runs on
build/reference-hgr/WILDERNESS.dsk (II+, DOS 3.3, its own wild.lbl) and on
dist/NEOWILDERNESS.po (enhanced //e). After every step, every named variable
of the resident game state (segments GDATA and BSS) and of the game zero page
must hold the same bytes in both builds, located through each label file.
"""
import re
import sys
from pathlib import Path
from common import HERE, L, DISK, REFERENCE, REFERENCE_DISK, a2test, reference_labels, fp
from scenario import REFERENCE_SCRIPT as SCRIPT, play

# Address-valued data, not simulation state: tables of code/text addresses
# (relocated by the new memory map, checked constant below), the game's
# pointer scratch and linker symbols.
ADDRESS_TABLES = {'verb_lo', 'verb_hi', 'cdef_lo', 'cdef_hi', 'ctol_lo', 'ctol_hi'}
# The verb list grows with the port's commands (lot 9: SAVE, RESTORE): a
# constant table too, checked constant below, not simulation state.
ADDRESS_TABLES |= {'verbs'}
POINTERS = {'gp1', 'gp2'}
# Module-cache bookkeeping, not simulation state: lot 4 returns from TOPO
# by copying back a snapshot of the view instead of redrawing it, so the
# window holds another module and fewer module copies are counted.
LOADING = {'overlay_reads', 'overlay_current', 'overlay_wanted'}


def segments(path):
    text = Path(path).read_text()
    return {name: (int(start, 16), int(end, 16) + 1) for name, start, end in
            re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]{6}', text, re.M)}


def fields(labels, segs):
    """{name: (address, size)} for the labels of the state segments."""
    ranges = [segs[name] for name in ('GDATA', 'BSS', 'GZP') if name in segs]
    found = sorted((address, name) for name, address in labels.items()
                   if any(lo <= address < hi for lo, hi in ranges))
    result = {}
    for k, (address, name) in enumerate(found):
        end = next(hi for lo, hi in ranges if lo <= address < hi)
        following = [a for a, _ in found[k + 1:] if a > address]
        if following and following[0] < end:
            end = following[0]
        result[name] = (address, end - address)
    return result


def common_fields():
    new = fields(L, segments(HERE / 'build/wild.map'))
    old = fields(reference_labels(), segments(REFERENCE / 'wild.map'))
    names = sorted(n for n in set(new) & set(old) - POINTERS - LOADING if not n.startswith('__'))
    sizes = {name: min(new[name][1], old[name][1]) for name in names}
    # Aliases share an address: keep one name per address in each build.
    keep, seen_new, seen_old = [], set(), set()
    for name in names:
        if new[name][0] in seen_new or old[name][0] in seen_old:
            continue
        seen_new.add(new[name][0])
        seen_old.add(old[name][0])
        keep.append(name)
    return keep, new, old, sizes


def snapshots(disk, labels, plan):
    """Run the script; after each step dump every field of `plan`."""
    spans = sorted({(address, size) for address, size in plan.values()})
    out = []
    with a2test.Session(disk, timeout=600) as s:
        def dump(step):
            memory = {}
            for address, size in spans:
                memory[address] = s.step(f'peek:{address:04X}:{size}').data
            out.append({name: memory[address] for name, (address, size) in plan.items()})
        play(s, labels, SCRIPT, dump)
    return out


def main():
    names, new, old, sizes = common_fields()
    reference = snapshots(REFERENCE_DISK, reference_labels(),
                          {n: (old[n][0], sizes[n]) for n in names})
    current = snapshots(DISK, L, {n: (new[n][0], sizes[n]) for n in names})
    failures = 0
    for run in (reference, current):
        for name in ADDRESS_TABLES & set(names):
            assert all(snap[name] == run[0][name] for snap in run), (name, 'address table changed')
    names = [n for n in names if n not in ADDRESS_TABLES]
    total = sum(sizes[n] for n in names)
    for step, before, after in zip(SCRIPT, reference, current):
        differ = [n for n in names if before[n] != after[n]]
        label = step[0].replace('\r', '').replace('\\', '')
        if differ:
            failures += 1
            print(f'  {label:18} DIFFER: ' + ', '.join(
                f'{n} {before[n].hex()} != {after[n].hex()}' for n in differ[:6]))
        else:
            print(f'  {label:18} identical')
    print(f'  {len(names)} state variables, {total} bytes, compared after each of '
          f'{len(SCRIPT)} steps (reference II+/DOS 3.3 vs //e/ProDOS)')
    # The script must cross midnight (start 7:00) and update health.
    elapsed = fp(current[-1]['s_elap'][:5])
    assert elapsed > 17, ('no day change', elapsed)
    assert current[-1]['s_health'] != current[0]['s_health'], 'no health update'
    print(f'  {elapsed:.2f} elapsed hours (day change at 17 h), health updated')
    if failures:
        print(f'{failures} steps differ')
        sys.exit(1)
    print('Reference state: OK')


if __name__ == '__main__':
    main()
