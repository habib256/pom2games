#!/usr/bin/env python3
"""topo2map.py: convert an original TOPO file to the game's MAP format.

For local comparison with the original only: the TOPO data is copyrighted
and never goes on a distributed disk. Start = crash site, heading = the
128 degrees of the original's first view.

Usage: topo2map.py TOPO.B OUT.bin
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkmap, topo  # noqa: E402

t = open(sys.argv[1], 'rb').read()
h = [[round(v) for v in r] for r in topo.heightmap(t)]
water = [[False] * mkmap.W for _ in range(mkmap.H)]
for y, items in enumerate(topo.rows(t)):
    for x, v, f in items:
        if isinstance(f, tuple):
            for xx in range(x, min(f[1], mkmap.W - 1) + 1):
                water[y][xx] = True
                h[y][xx] = v
        elif f is not None:
            water[y][x] = True
start, goal = (t[0x84], t[0x83]), (t[0x81], t[0x80])
open(sys.argv[2], 'wb').write(mkmap.map_bin(h, water, start, goal, round(128 * mkmap.UNITS / 360)))
