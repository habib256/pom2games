#!/usr/bin/env python3
"""The 6502 physics must match tools/physics.py bit for bit.

Builds tests/phystest.s with an input script, runs it in a2run and compares
the bike state after every segment with the Python model.

    python3 tests/test_physics.py            (make test runs it)
"""
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test  # noqa: E402
import physics  # noqa: E402
import track  # noqa: E402
import trackcheck  # noqa: E402
import tricks  # noqa: E402
import tracks  # noqa: E402

# (ticks, throttle, brake, lean)
# (stays on the 4096-pixel track at the x1.5 speeds; the crash at ~80 ticks
# keeps the tumbling bike in the comparison too)
SCRIPT = [
    (35, 6, 0, 0), (25, 6, 0, -2), (20, 4, 0, 4), (30, 6, 0, 0),
    (15, 0, 1, 0), (50, 6, 0, -2), (35, 4, 0, 3), (60, 6, 0, 0),
    (25, 0, 1, -4), (70, 4, 0, 1), (100, 6, 0, -1), (80, 4, 0, 2),
]


HEAD_SCRIPT = [(10, 4, 0, 2), (40, 4, 1, 2), (20, 0, 0, -4)]   # (found by a search: crash at tick 40)


def state(b):
    s = []
    for arr, sh in ((b.x, 0), (b.x, 8), (b.x, 16), (b.y, 0), (b.y, 8),
                    (b.ox, 0), (b.ox, 8), (b.ox, 16), (b.oy, 0), (b.oy, 8)):
        s += [(v >> sh) & 0xFF for v in arr]
    return bytes(s + b.ground + b.wheel_ang + [1 if b.crashed else 0, b.laps])


TRICK_LEN = 12                          # score .. tr_jmp in src/tricks.inc


def bcd(v, n):
    return bytes(int(f'{v:0{2 * n}d}'[2 * (n - 1 - i):2 * (n - i)], 16) for i in range(n))


def trick_state(t):
    return (bcd(t.score, 3) + bcd(t.pend, 2) +
            bytes([t.flips, t.air, t.rot & 0xFF, t.sector, t.safe, t.wh, t.jump]))


def segments(inputs):
    """Per-tick inputs -> run-length segments of at most 255 ticks."""
    out = []
    for thr, brk, lean in inputs:
        key = (thr, int(brk), lean)
        if out and out[-1][1:] == key and out[-1][0] < 255:
            out[-1] = (out[-1][0] + 1,) + key
        else:
            out.append((1,) + key)
    return out


def run(t, script):
    """Run [(segment, snapshot?)] in a2run, compare every snapshot."""
    snaps = sum(f for _, f in script)
    work = Path(tempfile.mkdtemp(prefix='dirtbike-phys-'))
    lap = getattr(t, 'lap_len', 0)
    lines = [f'NSNAPS = {snaps}', f'LAP_LEN = {lap}', 'script:']
    lines += [f'        .byte {seg[0]}, {seg[1]}, {seg[2]}, {seg[3] & 0xFF}, {f}' for seg, f in script]
    lines.append('        .byte 0')
    (work / 'physscript.inc').write_text('\n'.join(lines) + '\n')
    (work / 'track1.bin').write_bytes(bytes(t))
    cfg = work / 'p.cfg'                # the game's, BSS back in MAIN (the snapshots)
    text = (GAME / 'src/dirtbike.cfg').read_text()
    assert 'load = TXT6,   type = bss' in text
    cfg.write_text(text.replace('load = TXT6,   type = bss', 'load = MAIN,   type = bss')
                   .replace('"build/menu.bin"', f'"{work / "menu.bin"}"'))      # not the game's
    subprocess.run(['python3', str(GAME / 'tools/physconst.py'), str(work / 'physconst.inc')], check=True)
    subprocess.run(['ca65', '-g', '-I', str(work), '-I', str(GAME / 'src'), '-I', str(GAME.parent / 'dev/lib/math'), '--bin-include-dir', str(work),
                    '-o', str(work / 'p.o'), str(HERE / 'phystest.s')], check=True, cwd=work)
    subprocess.run(['ld65', '-C', str(cfg), '-Ln', str(work / 'p.lbl'), '-o', str(work / 'p.bin'),
                    str(work / 'p.o')], check=True)
    L = a2test.labels(work / 'p.lbl')
    disk = a2test.build_disk(work, 'PHYSTEST', work / 'p.bin')
    size = len(state(physics.Bike(t)))
    r = a2test.run(disk, ['wait:300', L.until('done', 20000), L.peek('snaps', size * snaps),
                          L.peek('score', TRICK_LEN)])
    got = r.mem(L['snaps'], size * snaps)

    b, tr = physics.Bike(t), tricks.Tricks()
    k = 0
    for (ticks, thr, brk, lean), snap in script:
        for _ in range(ticks):
            b.tick(thr, bool(brk), lean)
            tr.tick(b)
        if not snap:
            continue
        want = state(b)
        have = got[k * size:(k + 1) * size]
        ok = want == have
        print(f'snapshot {k:2}: x={b.x[0] / 256:7.1f} y={b.y[0] / 256:6.1f} '
              f'crashed={int(b.crashed)} {"ok" if ok else "DIFF"}')
        if not ok:
            print('   want', want.hex(' '))
            print('   have', have.hex(' '))
            sys.exit('physics: 6502 and model disagree')
        k += 1
    want = trick_state(tr)
    have = r.mem(L['score'], TRICK_LEN)
    print(f'tricks: score {tr.score}, banked {tr.banked} ' + ('ok' if want == have else 'DIFF'))
    if want != have:
        print('   want', want.hex(' '))
        print('   have', have.hex(' '))
        sys.exit('tricks: 6502 and model disagree')
    return sum(seg[0] for seg, _ in script)


def main():
    t = track.track1()
    ticks = run(t, [(s, 1) for s in SCRIPT])
    print(f'physics: 6502 == model on {ticks} scripted ticks')
    b = physics.Bike(t)                 # brake leaning forward: over the front, head first
    for n, thr, brk, lean in HEAD_SCRIPT:
        for _ in range(n):
            b.tick(thr, bool(brk), lean)
    assert b.crashed and b._head_hit(), 'HEAD_SCRIPT: the head hits the ground'
    run(t, [(s, 1) for s in HEAD_SCRIPT])
    print('physics: 6502 == model, head under the ground: crash')
    sols = trackcheck.solutions()
    for k in (1, 19, 30):               # whole proven rides: hills, a double flip, big jumps
        h, fin = tracks.build(k)
        res, n = trackcheck.replay(h, fin, sols[k])
        assert res == 'finish', (k, res, n)
        ride = segments(sols[k][:n])
        run(h, [(s, 0) for s in ride[:-1]] + [(ride[-1], 1)])
        print(f'physics: 6502 == model on the track {k} solution, finish in {n} ticks')


if __name__ == '__main__':
    main()
