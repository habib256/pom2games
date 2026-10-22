#!/usr/bin/env python3
"""a2profile.py -- a2shot's pcprof reply, attributed and summed.

a2shot's step `pcprof:ADDR:N` runs until PC = ADDR (at most N frames) and
prints "pcprof ADDR cycles=TOTAL", then "pc ADDR CYCLES" for every PC that
ran. The games' profile tools share what follows:

    pcs(out)                    {pc: cycles}
    total(out)                  the TOTAL of the last pcprof reply
    by_label(prof, labels)      {routine: cycles}: each PC goes to the
                                nearest label at or below it (labels: an
                                ld65 -Ln path or {name: address}; @locals
                                and __linker symbols skipped); PCs from
                                `rom` up are named by `rom_name`, or $ADDR
    by_region(prof, region)     {key: cycles}, key = region(pc)
    grouped(per, groups)        {group: cycles}: groups = [(group, name
                                prefixes)], the rest under 'other'
    report(per, total, ...)     the table, most expensive first: share of
                                `total`, cycles per `unit` (frames, calls...)
"""
import bisect
import re
from pathlib import Path

_PC = re.compile(r'^pc ([0-9A-F]{4}) (\d+)$', re.M)
_TOTAL = re.compile(r'^pcprof [0-9A-F]{4} cycles=(\d+)$', re.M)
_LABEL = re.compile(r'^al ([0-9A-F]+) \.(\S+)$', re.M)


def pcs(out):
    prof = {}
    for pc, cycles in _PC.findall(out):
        prof[int(pc, 16)] = prof.get(int(pc, 16), 0) + int(cycles)
    return prof


def total(out):
    return int(_TOTAL.findall(out)[-1])


def _routines(labels):
    if isinstance(labels, (str, Path)):
        labels = {n: int(a, 16) for a, n in _LABEL.findall(Path(labels).read_text())}
    names = {}
    for name, address in labels.items():
        if not name.startswith(('@', '__')):
            names.setdefault(address, name)
    return sorted(names), names


def by_label(prof, labels, rom=0xC000, rom_name=None):
    addrs, names = _routines(labels)
    per = {}
    for pc, cycles in prof.items():
        i = bisect.bisect_right(addrs, pc) - 1
        if pc >= rom:
            name = rom_name or f'${pc:04X}'
        else:
            name = names[addrs[i]] if i >= 0 else f'${pc:04X}'
        per[name] = per.get(name, 0) + cycles
    return per


def by_region(prof, region):
    per = {}
    for pc, cycles in prof.items():
        key = region(pc)
        per[key] = per.get(key, 0) + cycles
    return per


def grouped(per, groups):
    out = {}
    for name, cycles in per.items():
        g = next((g for g, prefixes in groups if name.startswith(tuple(prefixes))), 'other')
        out[g] = out.get(g, 0) + cycles
    return out


def report(per, total, unit=1, top=25, brackets=False, out=print):
    for name, cycles in sorted(per.items(), key=lambda kv: -kv[1])[:top]:
        label = f'[{name}]' if brackets else name
        out(f'{cycles * 100 / max(total, 1):5.1f}% {cycles // max(unit, 1):8}  {label}')
