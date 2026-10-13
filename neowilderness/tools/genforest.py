#!/usr/bin/env python3
"""Sierra crown heights, with a level underside and sixteen half-columns."""
from pathlib import Path
import sys
values=[]
for kind in range(2):
    for x in range(16):
        lo = (31 if x>=12 else 18+2*(x//2)) if not kind else max(31,42-2*((x+1)//2))
        hi = 24+8*x if not kind else 47+7*x
        # Native type 0 dips below the central canopy at its edges. Those
        # fringes become black hanging spikes beside the added central trunk.
        values += [max(31,lo),hi]
out=['.segment "TEXT"','forest_profiles:']
for i in range(0,len(values),16): out.append('        .byte '+','.join(map(str,values[i:i+16])))
Path(sys.argv[1]).write_text('\n'.join(out)+'\n')
