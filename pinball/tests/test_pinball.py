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

open_menu = [E.until('pcs_MAIN', 1600), 'joy:0,0'] + click(260, 180)
menu = open_menu + [D.until('pcs_MAIN', 500)]
for x, y in [(230, 90), (230, 140), (230, 67), (218, 140)]:
    menu += click(x, y) + [D.until('pcs_MAIN', 120), D.peek('pcs_DRIVE', 2)]
menu += click(174, 90) + [D.until('pcs_GETN3', 120), 'key:\\e',
                          D.until('pcs_MAIN', 500), D.peek('pcs_DRIVE', 2)]
assert a2test.run(disk, menu).dumps == [bytes([1, 5])] + [bytes([2, 5])] * 4, \
    'Cancelling a disk selection or filename changed the selected drive/slot'
# Supply the boot slot at overlay entry. Slots below four have no menu row.
low_slot = open_menu + ['until:9500:500', 'poke:B7C3:20', D.until('pcs_MAIN', 120),
                        D.peek('pcs_SLOT'), D.peek('pcs_SLOTBOX')]
assert a2test.run(disk, low_slot).dumps == [bytes([2]), bytes([0])], \
    'A low boot slot must stay selected without drawing a stray highlight'

# SCORE feeds pending byte-sized awards into two decimal accumulators.
# Check the carry at 999 + 255 in the editor and the standalone overlay.
for module, origin, base in [('RUN', 0x7700, 'pcs_SCB'), ('RUN2', 0x8554, 'pcs_SCBASE')]:
    labels = a2test.labels(build / f'{module}.lbl')
    for accumulator, column in [('pcs_SCORE1', 7), ('pcs_BONUS', 5)]:
        address = labels[accumulator]
        steps = [f'load:{build / (module + ".bin")}@{origin:04X}']
        steps += labels.poke(accumulator, [9, 9, 9], column - 2)
        steps += labels.poke(base, address.to_bytes(2, 'little'))
        steps += [f'regs:FF:00:{column:02X}', f'go:{labels["pcs_DOSCORE2"]:04X}',
                  labels.until('pcs_PRSCORE2', 5), labels.peek(accumulator, 4, column - 3)]
        assert a2test.run(None, steps).dumps == [bytes([1, 2, 5, 4])], (module, accumulator)

# RUN2 stores captured balls in records with fields at offsets 0 through 22.
U = a2test.labels(build / 'RUN2.lbl')
setup = [f'load:{build / "RUN2.bin"}@8554', f'go:{U["pcs_MAKETBLS"]:04X}',
         U.until('pcs_SETUP2', 100)]
slots = a2test.run(None, setup + [U.peek('pcs_SLEEPLO', 2), U.peek('pcs_SLEEPHI', 2)]).dumps
first, second = [lo + 256 * hi for lo, hi in zip(*slots)]
# The first callback reports a drained ball, the second a moving ball.
steps = setup + [U.poke('pcs_SLEEPCNT', 2), U.poke('pcs_PLAYER', 0),
                 U.poke('pcs_LASTY', 1), U.poke('pcs_Y2', 0), U.poke('pcs_LIVEBALLS', 0),
                 f'poke:{U["pcs_DRAWBALL"]:04X}:60']
steps += U.poke('pcs_SLEEPCODE', [0, 0])
for record, callback, status in [(first, 0x6000, 0x80), (second, 0x6010, 0)]:
    steps += a2test.pokes(record + 10, callback.to_bytes(2, 'little'))
    steps += a2test.pokes(callback, [0xA9, status, 0x85, U['pcs_BSTAT'], 0x60])
steps += [f'go:{U["pcs_SLEEP"]:04X}', U.until('pcs_SLEEP7', 10),
          U.peek('pcs_SLEEPCNT'), U.peek('pcs_LIVEBALLS')]
observed = a2test.run(None, steps).dumps
assert observed == [b'\x01', b'\xff'], ('Remaining ball skipped after removal', observed)
assert second - first == 23, ('Overlapping captured ball records', second - first)

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
                         D.until('pcs_WAIT1', 120), 'key: ', D.until('pcs_COMPRESS', 500)]
save_steps = steps.copy()
steps += [D.until('pcs_MAIN', 2000), f'dsk:{build / "saved.dsk"}']
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
saved_table = dos33.read_file(saved, 'TEST.PB')
assert len(saved_table) > 69
# Repeat the same SAVE with exactly enough workspace for its compressed graphics.
object_count = saved_table[0x1C]
geometry_end = 0x1D + object_count + sum(saved_table[0x1D:0x1D + object_count])
graphics = saved_table[geometry_end:]
start = 0x6300 - len(graphics)
packed = a2test.run(disk, save_steps + D.poke('pcs_MIDBTM', start.to_bytes(2, 'little')) + [
    D.until('pcs_BSAVE', 500), f'peek:{start:04X}:{len(graphics)}', D.peek('pcs_MIDBTM', 2),
    D.until('pcs_MAIN', 2000), f'dsk:{build / "exact-fit.dsk"}'])
assert packed.dumps[-2] == graphics, 'Exact-fit SAVE changed the compressed graphics'
assert packed.dumps[-1] == bytes([0, 0x63]), 'Exact-fit SAVE used the wrong amount of space'
exact_fit = dos33.read_file((build / 'exact-fit.dsk').read_bytes(), 'TEST.PB')
assert len(exact_fit) == 0x2300 and exact_fit.endswith(graphics)
print('PASS: SAVE writes the complete table when compressed graphics exactly fill the workspace')
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
