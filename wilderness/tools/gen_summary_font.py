#!/usr/bin/env python3
"""Byte-aligned 7 x 7 mono glyphs for the two side panels of the compass."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'dev/tools'))
from fonts import glyph,asm_bytes
out=['.segment "SUMMARY"','summary_font:']
for code in range(32,91):out.append(asm_bytes(glyph(chr(code))[:7]))
Path(sys.argv[1]).write_text('\n'.join(out)+'\n')
