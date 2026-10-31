#!/usr/bin/env python3
"""DHGR ACTION (dev/examples/dhgr_action) on the //e and the //c (a2shot).

Boots the ProDOS volume, lets the demo run without input (the enemies
bounce, the ship stays put), then:
- after SETTLE frames, watches every screen store for WATCHED frames: each
  goes to the page not shown (the shown page never changes between two
  dhgr_spr_present calls), and the enemies' boxes moved;
- at the last frame, the shown page's arena (rows 16..191, both banks)
  equals a Python model of the demo's deterministic motion (fixed start,
  bounces on the walls, two-frame animation, mirrored when going left);
- the frame cost: cycles between two frames, cycles of work (frame_end to
  dhgr_spr_present), the clock mode (//e: $C019 polled; //c: the mouse
  VBL interrupt).
"""
import argparse
import re
import subprocess
from pathlib import Path
import sys

DEV = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEV / 'tools'))
import a2test                                   # noqa: E402

EXAMPLE = DEV / 'examples/dhgr_action'
BUILD = EXAMPLE / 'build'
SOURCE = (EXAMPLE / 'src/action.c').read_text()
SETTLE, WATCHED = 12, 8
FRAME = 17030

COLOURS = dict(C=0x80, W=15, L=7, O=9, R=1, G=12, Y=13, P=11, V=3, A=14, K=0)


def nib(c):
    return ((c >> 1) | (c << 3)) & 15


def pack(n):
    """Seven nibbles -> aux even, main even, aux odd, main odd."""
    return ((n[0] | (n[1] & 7) << 4) & 0x7F,
            (n[1] >> 3 | n[2] << 1 | (n[3] & 3) << 5) & 0x7F,
            (n[3] >> 2 | n[4] << 2 | (n[5] & 1) << 6) & 0x7F,
            (n[5] >> 1 | n[6] << 3) & 0x7F)


def c_array(name):
    """The letters of a C colour array of action.c (C, W, L...)."""
    body = re.search(r'\b%s\[[^=]*=\s*\{(.*?)\};' % re.escape(name), SOURCE, re.S)[1]
    return [COLOURS[t] for t in re.findall(r'\b([A-Z])\b', body)]


def c_numbers(name):
    body = re.search(r'\b%s\[[^=]*=\s*\{(.*?)\};' % re.escape(name), SOURCE, re.S)[1]
    return [int(t) for t in re.findall(r'-?\d+', body)]


SHIP = c_array('ship_d')
BUG = c_array('bug_d')
SAUCER = c_array('saucer_d')
ENEMY = [BUG[:36], BUG[36:], SAUCER[:36], SAUCER[36:]]
WALL = [{'NA': nib(10), 'N5': nib(5), 'N0': nib(0)}[t] for t in re.findall(
    r'\b(N[A-Z0-9])\b', re.search(r'wall_d\[56\] = \{(.*?)\};', SOURCE, re.S)[1])]
XMIN, XEND, YMIN, YEND = 7, 133, 24, 184
SHIP_X, SHIP_Y = 66, 170


def tile_nibble(x, y):
    """The arena's background at colour pixel x, row y (16..191)."""
    col, row, cx, cy = x // 7, (y - 16) // 8, x % 7, (y - 16) % 8
    if row in (0, 21) or col in (0, 19):
        return WALL[cy * 7 + cx]
    if (row + col) & 1:
        return nib(0)                           # floor_b: black
    if cx == 3 and 3 <= cy < 5:
        return nib(6)                           # floor_a's dot
    return nib(2)


def play(frames):
    """Enemy states after `frames` calls of play(): x, y, dx, dy."""
    ex, ey = c_numbers('ex0'), c_numbers('ey0')
    dx, dy = c_numbers('edx0'), c_numbers('edy0')
    for f in range(frames):
        for i in range(5):
            n = ex[i] + dx[i]
            if n < XMIN or n > XEND - 6:
                dx[i] = -dx[i]
                n = ex[i] + dx[i]
            ex[i] = n
            n = ey[i] + dy[i]
            if n < YMIN or n > YEND - 6:
                dy[i] = -dy[i]
                n = ey[i] + dy[i]
            ey[i] = n
            assert not (SHIP_X < ex[i] + 6 and ex[i] < SHIP_X + 7 and SHIP_Y < ey[i] + 6
                        and ey[i] < SHIP_Y + 7), ('model: an enemy reaches the ship', f + 1)
    return ex, ey, dx, dy


def model(frames):
    """Main and aux bytes of rows 16..191 shown after `frames` frames."""
    ex, ey, dx, _ = play(frames)
    anim = ((frames - 1) >> 3) & 1
    sprites = [(ENEMY[(i & 1) * 2 + anim], 6, 6, ex[i], ey[i], dx[i] < 0) for i in range(5)]
    sprites.append((SHIP, 7, 7, SHIP_X, SHIP_Y, False))
    main, aux = {}, {}
    for y in range(16, 192):
        px = [tile_nibble(x, y) for x in range(140)]
        for data, w, h, sx, sy, mirror in sprites:
            if not sy <= y < sy + h:
                continue
            for c in range(w):
                v = data[(y - sy) * w + (w - 1 - c if mirror else c)]
                if not v & 0x80:
                    px[sx + c] = nib(v)
        base = a2test.hgr_offset(y)
        for g in range(20):
            b = pack(px[7 * g:7 * g + 7])
            aux[base + 2 * g], main[base + 2 * g] = b[0], b[1]
            aux[base + 2 * g + 1], main[base + 2 * g + 1] = b[2], b[3]
    return main, aux


STORE = re.compile(r'^store [0-9A-F]{4} ([0-9A-F]{4}) .* cycles=(\d+)$')


def check(machine):
    labels = a2test.labels(BUILD / 'action.lbl')
    fe, present = labels['_frame_end'], labels['_dhgr_spr_present']
    disk = BUILD / 'DHGRACTION.po'
    # (tracepc counts the address it stands on: + 1 after a stop there)
    steps = [labels.until('_main'), 'tracepc:%04X:%d:3000' % (fe, SETTLE),
             labels.peek('_dhgr_display'),
             'watch:%04X:%04X:1' % (fe, labels['_dhgr_display']), 'storewatch:2000:5FFF',
             'tracepc:%04X:%d:3000' % (fe, WATCHED + 1), 'unstorewatch', 'unwatch',
             labels.peek('_frame', 2), labels.peek('_dhgr_display'), labels.peek('_a2_vbl_mode'),
             'peek:2000:16384', 'poke:C003:0', 'peek:2000:16384', 'poke:C002:0']
    # The frame cost: frame_end -> present (work), frame_end -> frame_end.
    for _ in range(6):
        steps += ['until:%04X:100' % present, 'until:%04X:100' % fe]
    out = subprocess.run([str(a2test.A2SHOT), machine, '--disk', str(disk), *steps],
                         capture_output=True, text=True, timeout=900)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    out = out.stdout
    result = a2test.Result(out)
    # Stores between two frame_end watches: never into the shown page.
    shown, frames_seen, stores = result.dumps[0][0], 0, 0
    for line in out.split('\n'):
        if line.startswith('watch '):
            shown = int(line.rsplit('mem=', 1)[1], 16)
            frames_seen += 1
            continue
        m = STORE.match(line)
        if m:
            addr = int(m[1], 16)
            page = 1 if addr < 0x4000 else 2
            assert page != shown, (machine, 'store into the shown page', hex(addr), frames_seen)
            stores += 1
    assert frames_seen == WATCHED, ('frames watched', frames_seen)
    frame = int.from_bytes(result.dumps[1], 'little')
    shown = result.dumps[2][0]
    mode = result.dumps[3][0]
    assert frame == SETTLE + WATCHED, ('frame counter', frame)
    want = {'--iie': 1, '--iic': 2}[machine]
    assert mode == want, ('VBL clock mode', mode, want)
    main, aux = result.dumps[4], result.dumps[5]
    at = (shown - 1) * 8192
    want_main, want_aux = model(frame)
    for bank, got, ref in (('main', main, want_main), ('aux', aux, want_aux)):
        diff = [a for a in ref if got[at + a] != ref[a]]
        assert not diff, (machine, bank, 'shown page != model', len(diff),
                          [(hex(0x2000 * shown + a), got[at + a], ref[a]) for a in diff[:6]])
    # The enemies moved between the first and the last watched frame.
    first, last = play(SETTLE), play(frame)
    assert all((first[0][i], first[1][i]) != (last[0][i], last[1][i]) for i in range(5))
    marks = [int(c) for c in re.findall(r'(?m)^until \S+ cycles=(\d+)', out)][-12:]
    # marks: present, frame_end, present, frame_end...
    work = [marks[k + 1] - marks[k] for k in range(1, 11, 2)]
    period = [marks[k + 2] - marks[k] for k in range(1, 10, 2)]
    return dict(stores=stores, work=work, period=period, frame=frame)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iic', action='store_true', help='the //c only')
    args = ap.parse_args()
    if not a2test.have_a2shot():
        print('DHGR action: a2shot unavailable on this host, skipped.')
        return
    for machine in (['--iic'] if args.iic else ['--iie', '--iic']):
        r = check(machine)
        work, period = r['work'], r['period']
        print(f'DHGR action {machine[2:]}: {r["frame"]} frames, the shown page == model; '
              f'{r["stores"]} stores in {WATCHED} frames, none into the shown page; '
              f'work {min(work)}-{max(work)} cycles a frame, a frame every '
              f'{min(period)}-{max(period)} cycles ({min(period) / FRAME:.1f}-'
              f'{max(period) / FRAME:.1f} refreshes).')


if __name__ == '__main__':
    main()
