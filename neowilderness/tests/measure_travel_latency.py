#!/usr/bin/env python3
"""Compare a native WALK with identical starting data and no state injection."""
import argparse
import json
from pathlib import Path
import common

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline', type=Path)
p.add_argument('--output', type=Path)
a = p.parse_args()
disk = common.DISK
if a.baseline:
    disk = a.baseline / 'NEOWILDERNESSXL.po'
    common.L.clear()
    common.L.update(common.a2test.labels(a.baseline / 'wild.lbl'))
from common import L, a2test
from test_save import Game, LIMIT

with a2test.Session(disk) as s:
    s.step(L.until('idle', LIMIT))
    g = Game(s)
    seconds, calls = g.type('WALK 1 H')
    result = dict(command='WALK 1 H', mli_calls=calls,
                  emulated_seconds=round(seconds, 6),
                  state={name: s.step(L.peek(name, length)).data.hex()
                         for name, length in (
                             ('px', 4), ('heading', 2), ('s_elap', 5),
                             ('s_health', 5), ('s_rest', 5),
                             ('weather_seed', 4), ('it_pack_lo', 76),
                             ('it_pack_hi', 76), ('travel_remaining', 6))})
    assert result['state']['s_elap'] != '0000000000'
out = json.dumps(result, indent=2) + '\n'
if a.output:
    a.output.write_text(out)
print(out, end='')
