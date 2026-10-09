#!/usr/bin/env python3
"""Derive shared HGR configuration: reserve song buffers and align audio code."""
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text()
for old, new in (
    ('start = $1000, size = $1000', 'start = $1200, size = $0E00'),
    ('CODE:     load = RAM,    type = ro;',
     'CODE:     load = RAM,    type = ro, align = $100;'),
    ('BSS:      load = RAM,    type = bss, define = yes;',
     'BSS:      load = LOWRAM, type = bss, define = yes;'),
):
    assert text.count(old) == 1, f'Unexpected shared linker configuration: {old}'
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text)
