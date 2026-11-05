#!/usr/bin/env python3
"""Native DHGR damage merging against the original ordered-list model.

Check disjoint lists, overlaps, deletion by swapping, and bounding-box
bridges back into earlier entries. The test exposes private labels only
in its temporary assembly member; the library ABI stays unchanged.
"""
import argparse
import itertools
import random
import tempfile
from pathlib import Path

from test_hgr import DEV, build, a2test
from test_dhgr_spr import DMAX, SOURCES, merge


def cases():
    yield []
    bridge = [(0, 0, 0, 0), (0, 1, 1, 1), (1, 1, 0, 1)]
    yield from map(list, itertools.permutations(bridge))
    yield [(i % 20, i % 20, 8*(i // 20), 8*(i // 20)) for i in range(DMAX)]
    chain = [(i, i+1, 10, 10) for i in range(19)]
    yield chain
    yield chain[::-1]
    # All ordered triples of the nine boxes on a 2x2 grid.
    boxes = [(x0, x1, y0, y1)
             for x0 in range(2) for x1 in range(x0, 2)
             for y0 in range(2) for y1 in range(y0, 2)]
    yield from map(list, itertools.product(boxes, repeat=3))
    rng = random.Random(34032)
    for size in range(DMAX+1):
        for mode in range(16):
            rectangles = []
            for _ in range(size):
                if mode & 1:
                    x0, x1 = sorted(rng.randrange(20) for _ in range(2))
                    y0, y1 = sorted(rng.randrange(192) for _ in range(2))
                else:
                    x0, y0 = rng.randrange(20), rng.randrange(192)
                    x1 = min(19, x0+rng.randrange(3))
                    y1 = min(191, y0+rng.randrange(6))
                rectangles.append((x0, x1, y0, y1))
            yield rectangles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEV/'lib/hgrc/dhgr_spr_update.s',
                        help='optional old or candidate assembly member')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-merge-') as directory:
        work = Path(directory)
        probe = work/'probe.s'
        probe.write_text(args.source.read_text()+'''
.export _probe_merge, _probe_count, _probe_g0
_probe_merge=merge
_probe_count=_dhgr_spr_dn
_probe_g0=d_g0
''')
        fixture = work/'fixture.c'
        fixture.write_text('''void ready(void); void done(void); void probe_merge(void);
int main(void) {
    for (;;) { ready(); probe_merge(); done(); }
    return 0;
}
''')
        marker = work/'marker.s'
        marker.write_text('.export _ready, _done\n.code\n_ready: rts\n_done: rts\n')
        extra = [probe, marker]+[DEV/'lib/hgrc'/s for s in SOURCES
                                 if s != 'dhgr_spr_update.s']
        disk = build(work, fixture, extra_sources=extra)
        labels = a2test.labels(work/'test.lbl')
        batches = list(cases())
        for iie in (False, True):
            # Bound the debugger's command-line length and emulator output.
            for first in range(0, len(batches), 64):
                chunk = batches[first:first+64]
                steps = []
                for rectangles in chunk:
                    steps += [labels.until('_ready'),
                              labels.poke('_probe_count', len(rectangles))]
                    for field in range(4):
                        steps += labels.poke('_probe_g0', [r[field] for r in rectangles],
                                             offset=DMAX*field)
                    steps += [labels.until('_done'), labels.peek('_probe_count'),
                              labels.peek('_probe_g0', 4*DMAX)]
                result = a2test.run(disk, steps, iie=iie)
                assert len(result.dumps) == 2*len(chunk)
                for index, rectangles in enumerate(chunk):
                    expected = rectangles.copy()
                    merge(expected)
                    count = result.dumps[index*2][0]
                    assert count <= DMAX, ('invalid damage count', count)
                    raw = result.dumps[index*2+1]
                    actual = [tuple(raw[field*DMAX+j] for field in range(4))
                              for j in range(count)]
                    assert actual == expected, (iie, first+index, rectangles,
                                                 actual, expected)
            cpu = 'IIe 65C02' if iie else 'NMOS 6502'
            print(f'DHGR merge: {len(batches):,} exact ordered lists on {cpu}; '
                  'exhaustive triples, sparse/dense lists, bridges, both chains '
                  'and full capacity OK.')


if __name__ == '__main__':
    main()
