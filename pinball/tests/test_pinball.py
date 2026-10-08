#!/usr/bin/env python3
"""Boot, edit a ball, play, switch overlays, and save/reload a native table."""
from pathlib import Path
import hashlib
import json
import struct
import sys

GAME = Path(__file__).resolve().parents[1]
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
import dos33

build = GAME / 'build'
disk = ROOT / 'dist/PINBALL.dsk'
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
steps += click(260, 180) + [D.until('pcs_MAIN', 500)]
steps += click(174, 120) + [D.until('pcs_GETNAME', 120), 'wait:3', 'key:GAME\\r',
                          D.until('pcs_WAIT1', 120), 'key: ', E.until('pcs_MAIN', 2000),
                          f'dsk:{build / "made.dsk"}']
result = a2test.run(disk, steps, emulator=a2test.A2RUN)
assert result.dumps[0] == bytes([3, 0x1b, 0x0b, 0x22]), result.out
assert result.dumps[1] != result.dumps[2], 'Ball did not move during play'
assert result.dumps[3] == result.dumps[0], 'Reload did not restore the three objects'
saved = (build / 'saved.dsk').read_bytes()
assert [entry[0] for entry in dos33.catalog(saved)] == ['TEST.PB']
assert len(dos33.read_file(saved, 'TEST.PB')) > 69
assert saved[:16*4096] == original[:16*4096], 'SAVE overwrote an engine track'
assert disk.read_bytes() == original, 'Tests modified the distributed disk'

# Tables made with the original memory layout can exceed the reduced
# workspace. LOAD must reject them before overwriting the resident adapter.
oversized = build / 'oversized.dsk'
image = dos33.Dos33Image(disk)
image.data[:] = original
for t in range(16):
    for s in range(16):
        image.free[t, s] = False
payload = bytes([0xCC]) * 0x2400
image.add_file('LARGE.PB', dos33.TYPE_B, struct.pack('<HH', 0x4000, len(payload)) + payload)
image.save(oversized)
steps = [E.until('pcs_MAIN', 1600), 'joy:0,0', 'peek:6300:1280', 'peek:4000:8960']
steps += click(260, 180) + [D.until('pcs_MAIN', 500)]
steps += click(174, 78) + [D.until('pcs_GETNAME', 120), 'wait:3', 'key:LARGE\\r',
                         D.until('pcs_WAIT1', 120), 'key: ', D.until('pcs_ERR7', 2000),
                         'peek:B5C5:1', 'peek:6300:1280', 'peek:4000:8960', 'key: ',
                         D.until('pcs_MAIN', 500)]
rejected = a2test.run(oversized, steps)
assert rejected.dumps[2] == bytes([14]), 'Oversized LOAD must report PROGRAM TOO LARGE'
assert rejected.dumps[3] == rejected.dumps[0], 'LOAD damaged the resident adapter'
assert rejected.dumps[4] == rejected.dumps[1], 'Rejected LOAD changed the table'
# MAKE must produce a runnable game with the relocated collision tables.
made = (build / 'made.dsk').read_bytes()
game = dos33.read_file(made, 'GAME')
assert game[:3] == bytes([0x4C, 0x54, 0x85])
assert made[:16*4096] == original[:16*4096], 'MAKE overwrote an engine track'
(build / 'standalone.bin').write_bytes(game)
standalone = a2test.build_disk(build, 'GAME', build / 'standalone.bin', load=0x177D)
U = a2test.labels(build / 'RUN2.lbl')
played = a2test.run(standalone, [U.until('pcs_GETPL3', 2000), 'btn:0,1', 'wait:2',
                                'btn:0,0', U.until('pcs_PLAY7', 500), 'peek:00D8:4',
                                'wait:40', 'peek:00D8:4'])
assert played.dumps[0] != played.dumps[1], 'Standalone ball did not move'
print('PASS: MAKE creates a standalone game that boots and moves the ball')
print('PASS: oversized LOAD rejected without changing the table or resident adapter')

# Exercise SAVE when geometry leaves only one byte for compressed graphics.
# The second output byte would cross $6300, including through (MIDBTM),Y.
steps = [E.until('pcs_MAIN', 1600), 'joy:0,0', 'peek:6300:1280', 'peek:4000:69']
steps += click(260, 180) + [D.until('pcs_MAIN', 500)]
steps += click(174, 90) + [D.until('pcs_GETNAME', 120), 'wait:3', 'key:FULL\\r',
                         D.until('pcs_WAIT1', 120), 'key: ', D.until('pcs_COMPRESS', 500),
                         D.poke('pcs_MIDBTM', 0xFF), D.poke('pcs_MIDBTM', 0x62, 1),
                         D.until('pcs_ERR7', 500), 'peek:B5C5:1', 'peek:6300:1280',
                         'peek:4000:69', 'key: ', D.until('pcs_MAIN', 500)]
steps += click(174, 90) + [D.until('pcs_GETNAME', 120), 'wait:3', 'key:SMALL\\r',
                         D.until('pcs_WAIT1', 120), 'key: ', D.until('pcs_MAIN', 2000),
                         f'dsk:{build / "compression-limit.dsk"}']
full = a2test.run(disk, steps)
assert full.dumps[2] == bytes([14]), 'SAVE overflow must report PROGRAM TOO LARGE'
assert full.dumps[3] == full.dumps[0], 'Compression damaged the resident adapter'
assert full.dumps[4] == full.dumps[1], 'Compression failure changed table geometry'
assert [entry[0] for entry in dos33.catalog((build / 'compression-limit.dsk').read_bytes())] == ['SMALL.PB']
print('PASS: full SAVE rejected, adapter and geometry preserved, subsequent SAVE succeeds')
print('PASS: boot, ball drag and motion, ESC, wiring overlay, SAVE/LOAD, editor return, reserved tracks')
