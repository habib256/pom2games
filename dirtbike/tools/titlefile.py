#!/usr/bin/env python3
"""The TITLE file: tune, text pages, the main menu overlay, picture.

    python3 tools/titlefile.py OUT tune.bin pages.bin menu.bin title.lz4

The menu overlay is linked to run at MENU_AT (src/mainmenu.inc): padding
puts it there once the file is in LOADBUF + 4 (after DOS's header).
"""
import sys
from pathlib import Path

LOADBUF = 0x9600
MENU_AT = 0x9C00                # = src/mainmenu.inc, src/dirtbike.cfg

out, tune, pages, menu, lz4 = sys.argv[1:6]
head = Path(tune).read_bytes() + Path(pages).read_bytes()
gap = MENU_AT - (LOADBUF + 4) - len(head)
assert gap >= 0, f'TITLE: tune + pages {len(head)} bytes, past MENU_AT'
data = head + bytes(gap) + Path(menu).read_bytes() + Path(lz4).read_bytes()
assert LOADBUF + 4 + len(data) <= 0xB500, 'TITLE: past HOFBUF'
Path(out).write_bytes(data)
