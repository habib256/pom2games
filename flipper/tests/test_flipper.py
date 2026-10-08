#!/usr/bin/env python3
"""Boot, edit a ball, play, switch overlays, and save/reload a native table."""
from pathlib import Path
import hashlib
import json
import sys

GAME = Path(__file__).resolve().parents[1]
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
import dos33

build = GAME / 'build'
disk = ROOT / 'dist/FLIPPER.dsk'
E, R, W, D = [a2test.labels(build / (name + '.lbl')) for name in ('EDIT', 'RUN', 'WIRE', 'DISK')]

def cursor(x, y):
    # Position the joystick cursor deterministically; selection, drag, and
    # commands still execute the original editor and game-port button code.
    return [f'poke:0082:{y:02X}', f'poke:0083:{x//7:02X}', f'poke:0084:{x%7:02X}']

def click(x, y):
    return cursor(x, y) + ['btn:0,1', 'wait:10', 'btn:0,0']

original = disk.read_bytes()
assert len(original) == 143360
manifest = json.loads((GAME / 'assets/origin.json').read_text())
for name, spec in manifest['assets'].items():
    assert hashlib.sha256((GAME / 'assets' / name).read_bytes()).hexdigest() == spec['sha256'], name
# Every engine track must be reserved in the DOS allocation bitmap.
vtoc = original[17*4096:17*4096+256]
assert all(vtoc[0x38+t*4:0x3c+t*4] == bytes(4) for t in range(16))

steps = [E.until('pcs_MAIN', 1600), 'joy:0,0']
steps += cursor(246, 7) + ['btn:0,1', E.until('pcs_DRAGOBJ2', 60), 'wait:2']
for x in range(236, 75, -10):
    steps += cursor(x, 70) + ['wait:2']
steps += ['btn:0,0', E.until('pcs_MAIN', 60), 'peek:401C:4']
steps += click(260, 120) + [R.until('pcs_PLAY7', 120), 'peek:00D8:4', 'wait:40', 'peek:00D8:4',
                          f'shot:{build / "play.png"}', 'key:\\e', E.until('pcs_MAIN', 120)]
steps += click(260, 160) + [W.until('pcs_MAIN', 500), f'shot:{build / "wire.png"}']
steps += click(260, 58) + [W.until('pcs_QUIT', 120), E.until('pcs_MAIN', 800)]
steps += click(260, 180) + [D.until('pcs_MAIN', 500), f'shot:{build / "disk-menu.png"}']
steps += click(174, 90) + [D.until('pcs_GETNAME', 120), 'wait:3', 'key:TEST\\r',
                         D.until('pcs_WAIT1', 120), 'key: ', D.until('pcs_MAIN', 2000),
                         f'dsk:{build / "saved.dsk"}']
steps += click(174, 78) + [D.until('pcs_GETNAME', 120), 'wait:3', 'key:TEST\\r',
                         D.until('pcs_WAIT1', 120), 'key: ', D.until('pcs_MAIN', 2000), 'peek:401C:4']
steps += click(174, 100) + [E.until('pcs_MAIN', 800), f'shot:{build / "editor.png"}']
result = a2test.run(disk, steps, emulator=a2test.A2RUN)
assert result.dumps[0] == bytes([3, 0x1b, 0x0b, 0x22]), result.out
assert result.dumps[1] != result.dumps[2], 'Ball did not move during play'
assert result.dumps[3] == result.dumps[0], 'Reload did not restore the three objects'
saved = (build / 'saved.dsk').read_bytes()
assert [entry[0] for entry in dos33.catalog(saved)] == ['TEST.PB']
assert len(dos33.read_file(saved, 'TEST.PB')) > 69
assert saved[:16*4096] == original[:16*4096], 'SAVE overwrote an engine track'
assert disk.read_bytes() == original, 'Tests modified the distributed disk'
print('PASS: boot, ball drag and motion, ESC, wiring overlay, SAVE/LOAD, editor return, reserved tracks')
