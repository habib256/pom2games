#!/usr/bin/env python3
"""The 6502 view (src/wild.s) must match tools/view_ref.py bit for bit.

Boots dist/WILDERNESS.dsk in a2shot, waits for each frame to finish (the key
loop `idle`), dumps HGR rows 0..159 and compares them with the reference
rendered at the same position and heading. Moves cover the four quadrants,
walking, and both map files: the generated map and, when it exists locally,
the original Sierra Nevada map (build/orig_map.bin, see tools/topo2map.py).
Also reports the cycles of each frame.
"""
from pathlib import Path
import shutil, subprocess, sys, tempfile

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test       # noqa: E402
import view_ref     # noqa: E402

DISK = HERE.parent / 'dist/WILDERNESS.dsk'
L = a2test.labels(HERE / 'build/wild.lbl')
KEYS = ['', 'K', 'Z', 'I', 'I', 'Z', 'J', 'M', 'Z', 'A']   # '' = first frame


def zp(mem, name, size=2):
    a = L[name]
    return int.from_bytes(mem[a:a + size], 'little')


def run(disk, mapbin):
    steps = [L.until('idle', 4000)]
    for k in KEYS[1:]:
        steps += [f'key:{k}', 'wait:1', L.until('idle', 4000)]
    # after each frame: position/heading, then rows 0..159
    out = []
    for s in steps:
        out.append(s)
        if s.startswith('until'):
            out += [L.peek('px', 6), 'peek:2000:8192']
    r = a2test.run(disk, out, emulator=a2test.A2SHOT, timeout=900)
    fails = 0
    for i, k in enumerate(KEYS):
        state = r.dumps[2 * i]
        page = r.dumps[2 * i + 1]
        px, py, head = (int.from_bytes(state[o:o + 2], 'little') for o in (0, 2, 4))
        got = b''.join(page[a2test.hgr_offset(y):a2test.hgr_offset(y) + 40] for y in range(160))
        want = view_ref.render(mapbin, px, py, head)
        bad = sum(a != b for a, b in zip(got, want))
        cyc = r.cycles[i] - (r.cycles[i - 1] if i else 0)
        print(f'  key {k or "-":2} pos {px / 256:6.2f},{py / 256:6.2f} head {head:3}  '
              f'{"ok" if not bad else f"{bad} bytes differ"}  ({cyc / 1e6:.2f} Mcycles)')
        fails += bool(bad)
    return fails


def main():
    fails = 0
    print('generated map')
    fails += run(DISK, (HERE / 'build/map.bin').read_bytes())
    orig = HERE / 'build/orig_map.bin'
    if orig.exists():
        print('original Sierra Nevada map (local only)')
        with tempfile.TemporaryDirectory() as tmp:
            disk = Path(tmp) / 'orig.dsk'
            shutil.copy(DISK, disk)
            subprocess.run(['python3', str(HERE.parent / 'dev/tools/dos33.py'),
                            '--master', str(HERE.parent / 'dev/tools/dos33_system.bin'),
                            '--out', str(disk), '--bas', f'HELLO={HERE / "src/hello.bas"}',
                            '--bin', f'WILDERNESS={HERE / "build/wild.bin"}@0x6000',
                            '--bin', f'WILDLO={HERE / "build/wildlo.bin"}@0x1000',
                            '--bin', f'WILDMAP={orig}@0x7000'], check=True, capture_output=True)
            fails += run(disk, orig.read_bytes())
    print('FAIL' if fails else 'OK')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
