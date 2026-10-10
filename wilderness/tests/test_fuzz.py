#!/usr/bin/env python3
"""Differential fuzz of the 6502 view against tools/view_ref.py.

Synthetic maps stress what the generated ones rarely reach: levels 0..125
(the format's limit), cliffs, water anywhere. Each frame pokes a random
position (edges and corners included) and heading (the four axes included,
where a ray step is exactly one cell), presses V and compares HGR rows
0..159 bit for bit. Usage: test_fuzz.py [SEED] [MAPS] [FRAMES]
"""
from pathlib import Path
import random, subprocess, sys, tempfile

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test       # noqa: E402
import view_ref     # noqa: E402

L = a2test.labels(HERE / 'build/wild.lbl')
GW, GH = 112, 84


def synthetic(rnd, kind):
    hdr = bytearray(64)
    hdr[0:2] = b'W\x01'
    hdr[10], hdr[11] = 24, rnd.choice((48, 0, 126))
    grid = bytearray()
    for j in range(GH):
        for i in range(GW):
            if kind == 'noise':
                v = rnd.randrange(126)
            elif kind == 'cliffs':
                v = 125 if (i // 7 + j // 5) % 3 == 0 else rnd.randrange(4)
            else:                         # smooth bowl with a high rim
                v = min(125, int(((i - 56) ** 2 + (j - 42) ** 2) ** 0.5 * 1.8))
            if rnd.random() < 0.05:
                v |= 0x80
            grid.append(v)
    return bytes(hdr + grid)


def disk_with(tmp, mapbin):
    m = Path(tmp) / 'map.bin'
    m.write_bytes(mapbin)
    d = Path(tmp) / 'f.dsk'
    subprocess.run(['python3', str(HERE.parent / 'dev/tools/dos33.py'),
                    '--master', str(HERE.parent / 'dev/tools/dos33_system.bin'),
                    '--out', str(d), '--bas', f'HELLO={HERE / "src/hello.bas"}',
                    '--bin', f'WILDERNESS={HERE / "build/wild.bin"}@0x6000',
                    '--bin', f'WILDLO={HERE / "build/wildlo.bin"}@0x1000',
                    '--bin', f'WILDMAP={m}@0x7000'], check=True, capture_output=True)
    return d


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    maps = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    rnd = random.Random(seed)
    fails = 0
    for k in range(maps):
        kind = ('noise', 'cliffs', 'bowl')[k % 3]
        mapbin = synthetic(rnd, kind)
        cases = []
        for f in range(frames):
            edge = rnd.random() < 0.4
            cx = rnd.choice((0, 1, GW - 2, GW - 1)) if edge else rnd.randrange(GW)
            cy = rnd.choice((0, 1, GH - 2, GH - 1)) if edge and rnd.random() < .5 else rnd.randrange(GH)
            px, py = cx << 8 | rnd.randrange(256), cy << 8 | rnd.randrange(256)
            head = rnd.choice((0, 140, 280, 420, rnd.randrange(560)))
            cases.append((px, py, head))
        steps = [L.until('idle', 4000)]
        for px, py, head in cases:
            for name, val in (('px', px), ('py', py), ('heading', head)):
                steps += [L.poke(name, val & 255), L.poke(name, val >> 8, 1)]
            steps += ['key:V', 'wait:1', L.until('idle', 4000), 'peek:2000:8192']
        with tempfile.TemporaryDirectory() as tmp:
            r = a2test.run(disk_with(tmp, mapbin), steps, emulator=a2test.A2SHOT, timeout=1800)
        for (px, py, head), page in zip(cases, r.dumps):
            got = b''.join(page[a2test.hgr_offset(y):a2test.hgr_offset(y) + 40] for y in range(160))
            bad = sum(a != b for a, b in zip(got, view_ref.render(mapbin, px, py, head)))
            if bad:
                fails += 1
                print(f'  {kind}: pos {px:04X},{py:04X} head {head}: {bad} bytes differ')
        print(f'{kind}: {frames} frames, {fails} failures so far')
    print('FAIL' if fails else 'OK')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
