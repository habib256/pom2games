#!/usr/bin/env python3
"""re_extract.py: split the original game engine into blocks and disassemble them.

Resident blocks come from a RAM dump taken at the first view (make dump-game,
build/game.bin); the overlays the engine loads at $5800 (table at SURV3D
$0E9F: track, $0EA6: sector, $0EAD: count, for overlays 3..9; $0E62 loads
track 6 sector 2) come from the Journey side, SMALLDOS track t = physical
34 - t. Output: build/re/NAME.bin and NAME.s (da65).
"""
import os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smalldos  # noqa: E402

OUT = 'build/re'
RESIDENT = {                       # name: (start, end) in the game RAM
    'smalldos_lo': (0x0300, 0x0400),
    'surv3d': (0x0800, 0x1F00),
    'page1f': (0x1F00, 0x2000),
    'core40': (0x4000, 0x4D00),
    'core4d': (0x4D00, 0x5000),
    'core50': (0x5000, 0x5800),
    'parser': (0xB000, 0xBA00),
    'smalldos_hi': (0xBA00, 0xC000),
}
OVERLAYS = {                       # overlay number: (track, sector, sectors)
    3: (0x05, 0x08, 4), 4: (0x01, 0x0B, 5), 5: (0x06, 0x0A, 7), 6: (0x07, 0x08, 8),
    7: (0x13, 0x00, 8), 8: (0x15, 0x00, 5), 9: (0x22, 0x01, 10), 'x': (0x06, 0x02, 2),
}


def da65(name, start, data):
    path = f'{OUT}/{name}.bin'
    open(path, 'wb').write(data)
    subprocess.run(['da65', '--start-addr', hex(start), '--comments', '4', '-o', f'{OUT}/{name}.s', path],
                   check=True, capture_output=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    ram = open('build/game.bin', 'rb').read()
    for name, (a, b) in RESIDENT.items():
        da65(name, a, ram[a:b])
    dk = smalldos.Disk(open('build/JOURNEY.dsk', 'rb').read())
    dk.flip = True
    for n, (t, s, c) in OVERLAYS.items():
        da65(f'ov{n}', 0x5800, dk.run(t, s, c))
    print('\n'.join(sorted(os.listdir(OUT))))


if __name__ == '__main__':
    main()
