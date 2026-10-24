#!/usr/bin/env python3
"""SNAKE on the shipped disk in a2run (Apple II+): speeds, wrap, turn queue,
walls, apples and bonus with their sounds, joystick, pause and quit, the
levels (walls, growth, pace, the win) and the record saved on the disk (or
kept in memory on a write-protected one).

Each scenario boots the disk, picks a speed on the title, then moves the
apple off the snake's path with a poke so the random sequence does not
matter; the game is followed tick by tick at the entry of tick()."""
import argparse
from pathlib import Path
import sys
import tempfile

GAME = Path(__file__).resolve().parents[1]
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402
import dos33  # noqa: E402

COLS, ROWS, MAXLEN = 35, 24, 660
SPEEDS = {'1': 3565, '2': 2565, '3': 1565}


def start(L, key='1', pre=(), food=(1, 21)):
    """Boot, press `key` on the title, stop after the first full draw with the
    apple moved to `food` (bottom-left, away from row 12)."""
    return [*pre, L.until('main', 3000), L.until('throttle', 600), f'key:{key}',
            L.until('redraw', 600), 'wait:1',
            L.poke('foodx', food[0]), L.poke('foody', food[1])]


def ticks(L, n):
    """Run until the entry of the n-th next tick() (a frame first, so a
    second until: does not stop where the previous one did). Keys pressed at
    a tick's entry are read in the throttle after it: they steer the move
    after next."""
    return ['wait:1', L.until('tick', 200)] * n


def snap(L):
    return [L.peek('head', 2), L.peek('slen', 2), L.peek('alive'), L.peek('score', 2),
            L.peek('sx', MAXLEN), L.peek('sy', MAXLEN), 'spk']


class Snaps:
    """The snap() dumps of one run, in order."""

    def __init__(self, r, L, count):
        self.r, self.L, self.spk = r, L, r.spk[-count:]

    def __call__(self, i):
        m = lambda name, n: self.r.mem(self.L[name], n, i)  # noqa: E731
        head = int.from_bytes(m('head', 2), 'little')
        return dict(head=(m('sx', MAXLEN)[head], m('sy', MAXLEN)[head]),
                    slen=int.from_bytes(m('slen', 2), 'little'), alive=m('alive', 1)[0],
                    score=int.from_bytes(m('score', 2), 'little'), spk=self.spk[i])


def run(disk, steps, **kw):
    return a2test.run(disk, steps, **kw)


def speeds(disk, L):
    for key, want in [*SPEEDS.items(), ('X', 3565)]:
        r = run(disk, start(L, key) + [L.peek('speed_spins', 2), L.peek('tick_spins', 2)])
        got = [int.from_bytes(d, 'little') for d in r.dumps]
        assert got == [want, want], (key, got)
    print('PASS speeds: title keys 1 2 3 start at 3565 / 2565 / 1565 spins, any other key at 3565')


def wrap(disk, L):
    # head at column 17 heading right: column 33 after 16 moves, 1 after 17
    steps = start(L, '3') + ticks(L, 17) + snap(L) + ticks(L, 1) + snap(L)
    s = Snaps(run(disk, steps), L, 2)
    assert s(0)['head'] == (33, 12) and s(1)['head'] == (1, 12), (s(0), s(1))
    assert s(1)['alive'] == 1
    print('PASS wrap: column 33 -> column 1 through the open right edge')


def turns(disk, L):
    # two quick turns within one tick: up on the next move, left on the one
    # after; a reversal (left while heading right) is refused
    steps = start(L) + ticks(L, 1) + ['press:IJ'] + ticks(L, 2) + snap(L) + ticks(L, 1) + snap(L)
    s = Snaps(run(disk, steps), L, 2)
    assert s(0)['head'] == (18, 11) and s(1)['head'] == (17, 11), (s(0), s(1))
    steps = start(L) + ticks(L, 1) + ['press:J'] + ticks(L, 2) + snap(L)
    s = Snaps(run(disk, steps), L, 1)
    assert s(0)['head'] == (19, 12), s(0)
    print('PASS turns: two queued turns on two moves, a reversal refused')


def walls(disk, L):
    # one move right, then up from row 12: row 3 is the last playable row,
    # row 2 the wall (no tick() after the death: wait instead)
    steps = start(L) + ticks(L, 1) + ['press:I'] + ticks(L, 10) + snap(L) + [
        'wait:40', L.peek('alive'), 'spk']
    r = run(disk, steps)
    s = Snaps(r, L, 1)
    assert s(0)['head'] == (18, 3) and s(0)['alive'] == 1, s(0)
    assert r.mem(L['alive'], 1, 1) == b'\0', 'the wall kills'
    assert r.spk[-1] >= 0x30 + 0x18, f'death sound: {r.spk[-1]} toggles'
    print(f'PASS walls: alive on row 3, dead on the wall row, death sound ({r.spk[-1]} toggles)')


def apples(disk, L):
    # the apple right in front, the 4th apple: it grows, scores, speeds up,
    # blips and drops the bonus gem; the gem in front is worth 20
    steps = start(L, food=(18, 12)) + [L.poke('apples', 3)] + ticks(L, 1) + snap(L) + \
        ticks(L, 1) + snap(L) + [L.peek('apples'), L.peek('bonus_active'), L.peek('bonus_ttl'),
                                 L.peek('tick_spins', 2), L.poke('bonusx', 19), L.poke('bonusy', 12),
                                 L.poke('foodx', 1), L.poke('foody', 21)] + \
        ticks(L, 1) + snap(L) + [L.peek('bonus_active')]
    r = run(disk, steps)
    s = Snaps(r, L, 3)
    before, after, gem = s(0), s(1), s(2)
    assert (after['slen'], after['score']) == (before['slen'] + 1, 5), (before, after)
    assert after['head'] == (18, 12)
    apples_n, bonus, ttl = (r.mem(L[n], 1, 0)[0] for n in ('apples', 'bonus_active', 'bonus_ttl'))
    spins = int.from_bytes(r.mem(L['tick_spins'], 2), 'little')
    assert (apples_n, bonus, ttl, spins) == (4, 1, 35, 3365), (apples_n, bonus, ttl, spins)
    assert after['spk'] >= 0x18 + 0x10, f'apple blip and bonus chirp: {after["spk"]} toggles'
    assert gem['score'] == 25 and gem['slen'] == after['slen'], gem
    assert r.mem(L['bonus_active'], 1, 1) == b'\0'
    assert gem['spk'] >= 0x20 + 0x30, f'bonus chime: {gem["spk"]} toggles'
    print(f'PASS apples: +1 cell, 5 points, 3565 -> 3365 spins, blip + chirp ({after["spk"]} toggles); '
          f'bonus out for 35 more ticks, worth 20 ({gem["spk"]} toggles)')


def joystick(disk, L):
    # a stick on the game port (a2run's default, centred): up steers; held up,
    # it does not undo a keyboard turn right. Nothing plugged in: no reads.
    steps = start(L) + [L.peek('stick')] + ticks(L, 1) + ['joy:0,-1'] + ticks(L, 2) + snap(L) + \
        ['press:L'] + ticks(L, 3) + snap(L)
    r = run(disk, steps)
    s = Snaps(r, L, 2)
    assert r.mem(L['stick'], 1) == b'\1'
    assert s(0)['head'] == (18, 11), s(0)         # read before tick(): up at once
    assert s(1)['head'] == (20, 10), s(1)         # up, then right, and right again
    r = run(disk, start(L, pre=['joy:9,9']) + [L.peek('stick')] + ticks(L, 2) + snap(L))
    assert r.mem(L['stick'], 1) == b'\0' and Snaps(r, L, 1)(0)['head'] == (18, 12)
    print('PASS joystick: detected, steers up, a held stick does not fight the keyboard; '
          'none plugged in: keyboard only')


def pause_quit(disk, L):
    steps = start(L) + ticks(L, 1) + ['key:P', 'wait:30', L.peek('paused'), 'key:Q',
                                      'until:FD1B:300', 'text']
    r = run(disk, steps)
    assert r.mem(L['paused'], 1) == b'\1'
    assert any(line.startswith('|]') for line in r.text_screens()[-1].splitlines()), 'DOS prompt'
    print('PASS pause: P stops the snake, Q from the pause returns to the DOS prompt')


def record(disk, L, work):
    # one apple then the wall: 5 points, a new record saved in HISCORE
    die = start(L, food=(18, 12)) + ticks(L, 2) + ['press:I', L.until('keep_record', 600),
                                                   'wait:120', L.peek('hiscore', 2), L.peek('new_record')]
    saved = work / 'saved.dsk'
    r = run(disk, die + [L.until('redraw', 1200), f'dsk:{saved}'])
    assert r.mem(L['hiscore'], 2) == b'\5\0' and r.mem(L['new_record'], 1) == b'\1'
    assert dos33.read_file(saved.read_bytes(), 'HISCORE') == b'\5\0', 'HISCORE on the disk'
    r = run(saved, [L.until('main', 3000), L.until('throttle', 600), L.peek('hiscore', 2)])
    assert r.mem(L['hiscore'], 2) == b'\5\0', 'the record read back at start'
    # write-protected: the record stays in memory, the disk keeps 0, the game goes on
    kept = work / 'kept.dsk'
    r = run(disk, die + [L.until('redraw', 1200), f'dsk:{kept}'], wp=True)
    assert r.mem(L['hiscore'], 2) == b'\5\0'
    assert dos33.read_file(kept.read_bytes(), 'HISCORE') == b'\0\0'
    print('PASS record: 5 points saved to HISCORE and read back at start; '
          'write-protected disk: kept in memory, game goes on')


def level_end(L, level, food=(18, 12)):
    """Start, then make the next apple (right in front) the last of `level`
    (0 = level 1): its tick ends the level."""
    return start(L, food=food) + [L.poke('level', level), L.poke('level_apples', 9)]


def levels(disk, L):
    # the 10th apple of level 1: the LEVEL 2 card and jingle, a fresh snake
    # among two bars, a faster start, the score kept
    steps = level_end(L, 0) + ticks(L, 1) + ['spk', L.until('next_level', 100), L.until('redraw', 600),
                                            'wait:1', 'spk', L.peek('level'), L.peek('occupied', COLS * ROWS),
                                            L.peek('tick_spins', 2), L.poke('foodx', 1), L.poke('foody', 21)] + \
        snap(L) + ['press:I', L.until('keep_record', 600), L.peek('head', 2), L.peek('sy', MAXLEN)]
    r = run(disk, steps)
    grid = r.mem(L['occupied'], COLS * ROWS)
    cells = {(i % COLS, i // COLS) for i, v in enumerate(grid) if v}
    bars = {(x, y) for y in (7, 17) for x in range(8, 27)}
    snake = {(15, 12), (16, 12), (17, 12)}
    s = Snaps(r, L, 1)
    assert r.mem(L['level'], 1) == b'\1' and cells == bars | snake, sorted(cells - bars - snake)
    assert s(0)['slen'] == 3 and s(0)['head'] == (17, 12) and s(0)['score'] == 5, s(0)
    assert int.from_bytes(r.mem(L['tick_spins'], 2), 'little') == 3565 - 300
    assert r.spk[-2] >= 0x30 + 0x40, f'level jingle: {r.spk[-2]} toggles'
    head = int.from_bytes(r.mem(L['head'], 2, 1), 'little')
    assert r.mem(L['sy'], MAXLEN, 1)[head] == 8, 'killed by the bar on row 7'
    print(f'PASS level 2: card and jingle ({r.spk[-2]} toggles), 38 wall cells, a fresh 3-cell snake, '
          '3265 spins, score kept; the bar kills')

    # level 2 apples grow the snake by two cells
    steps = level_end(L, 0) + ticks(L, 1) + [L.until('redraw', 600), 'wait:1', L.poke('foodx', 18),
                                            L.poke('foody', 12)] + ticks(L, 2) + snap(L) + ticks(L, 1) + snap(L)
    s = Snaps(run(disk, steps), L, 2)
    assert (s(0)['slen'], s(1)['slen']) == (4, 5), (s(0), s(1))
    print('PASS level 2: an apple grows the snake by two cells, one per move')

    # level 5: 100 apples placed in a row land on free cells only
    place = L['place_food']
    steps = level_end(L, 3) + ticks(L, 1) + [L.until('redraw', 600), 'wait:1'] + ticks(L, 1) + \
        [L.peek('level'), L.peek('occupied', COLS * ROWS)] + [f'call:{place:04X}:5', L.peek('foodx', 2)] * 100
    r = run(disk, steps)
    grid = r.mem(L['occupied'], COLS * ROWS)
    assert r.mem(L['level'], 1) == b'\4' and sum(grid) == 61 + 3, sum(grid)
    foods = [r.mem(L['foodx'], 2, i) for i in range(100)]
    assert all(not grid[y * COLS + x] and 1 <= x <= 33 and 3 <= y <= 22 for x, y in foods), foods
    print(f'PASS level 5: 61 wall cells; 100 apples in a row, {len(set(foods))} distinct cells, none on a wall '
          'or the snake')

    # the last apple of level 5: YOU WIN
    r = run(disk, level_end(L, 4) + ticks(L, 1) + ['spk', L.until('keep_record', 300), 'wait:30',
                                                   L.peek('won'), 'spk'])
    assert r.mem(L['won'], 1) == b'\1' and r.spk[-1] >= 0x40 + 0x50 + 0x60, r.spk
    print(f'PASS level 5 done: YOU WIN and its arpeggio ({r.spk[-1]} toggles)')


def periods(r, n):
    c = r.cycles[-n:]
    return [b - a for a, b in zip(c, c[1:])]


def pace(disk, L):
    # the vapor lock (a2run has the floating bus, as POM2): ticks of whole
    # frames, 25 at the slow start, 3 at the top speed; a marker gone: back
    # to the spin throttle, the game goes on
    fast = [L.poke('tick_spins', 365 & 255), L.poke('tick_spins', 365 >> 8, 1)]
    r = run(disk, start(L) + [L.peek('vapor'), L.peek('pal')] + ticks(L, 4) + fast + ticks(L, 4))
    assert r.mem(L['vapor'], 1) == b'\1' and r.mem(L['pal'], 1) == b'\0'
    slow, top = periods(r, 8)[1:3], periods(r, 3)      # (a lock is exact to one 13-cycle poll)
    assert all(abs(g - 25 * 17030) <= 30 for g in slow) and all(abs(g - 3 * 17030) <= 30 for g in top), \
        (slow, top)
    wipe = [f'poke:{0x3FD0 + i:04X}:00' for i in range(24)]
    r = run(disk, start(L) + ticks(L, 1) + wipe + ticks(L, 5) + [L.peek('vapor'), L.peek('alive')])
    spin = periods(r, 3)
    assert r.mem(L['vapor'], 1) == b'\0' and r.mem(L['alive'], 1) == b'\1'
    assert all(abs(g - 418200) < 2000 for g in spin), spin
    print('PASS pace: vapor lock, a tick every 25 frames (3 at top speed), exact; '
          f'marker gone: spin throttle ({spin[0]} cycles a tick)')
    if not a2test.have_a2shot('SNAKE pace on POM2 (PAL, //e)'):
        return
    for name, kw, frames, frame in (('PAL II+', dict(pal=True), 21, 20280), ('//e', dict(iie=True), 25, 17030)):
        r = run(disk, start(L) + [L.peek('vapor'), L.peek('pal')] + ticks(L, 4),
                emulator=a2test.A2SHOT, pad_until=True, **kw)
        got = periods(r, 3)
        assert r.mem(L['vapor'], 1) == b'\1' and r.mem(L['pal'], 1) == bytes([name.startswith('PAL')])
        assert all(abs(g - frames * frame) <= 30 for g in got), (name, got)
        print(f'PASS pace on POM2 {name}: vapor lock, {frames} frames of {frame} cycles a tick '
              f'({frames * frame / 1020484:.3f} s)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/SNAKE.dsk')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/snake.lbl')
    a = ap.parse_args()
    L = a2test.labels(a.labels, strip=True)
    assert dos33.read_file(a.disk.read_bytes(), 'HISCORE') == b'\0\0', 'a new disk has a zero record'
    speeds(a.disk, L)
    wrap(a.disk, L)
    turns(a.disk, L)
    walls(a.disk, L)
    apples(a.disk, L)
    joystick(a.disk, L)
    pause_quit(a.disk, L)
    levels(a.disk, L)
    pace(a.disk, L)
    with tempfile.TemporaryDirectory(prefix='snake-') as tmp:
        record(a.disk, L, Path(tmp))


if __name__ == '__main__':
    main()
