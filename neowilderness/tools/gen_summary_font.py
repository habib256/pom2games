#!/usr/bin/env python3
"""The 7-row DHGR font of the survival panels (tools/dhgr_font.py), ' '..'Z':
7 bytes per glyph, row bits 0..4 (pixel 0 = bit 0), width in bits 5..7 of
row 0. src/summary.s draws it one colour pixel per bit."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhgr_font import table

data = table()
out = ['.segment "SUMMARY"', 'summary_font:']
for i in range(0, len(data), 7):
    out.append('        .byte ' + ','.join(f'${b:02X}' for b in data[i:i + 7]))
Path(sys.argv[1]).write_text('\n'.join(out) + '\n')
