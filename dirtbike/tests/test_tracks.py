#!/usr/bin/env python3
"""The game loads tracks exactly: menu -> track k -> RWTS + LZ4FH -> RAM.

For a few tracks, drives the menu in a2run, waits for the race to start and
compares the loaded data (heights, pattern ids, pattern tables, pool, finish
line) with tools/track.py's compilation.

    python3 tests/test_tracks.py [k ...]
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test  # noqa: E402
import track  # noqa: E402
import tracks  # noqa: E402

DISK = ROOT / 'dist/DIRTBIKE.dsk'


TITLE = ['key: ', 'wait:60']          # from the title page to the menu


def menu_keys(k):
    keys = ([] if k <= 15 else ['L']) + ['K'] * ((k - 1) % 15)
    return [s for c in keys for s in (f'key:{c}', 'wait:3')] + ['key:\r']


def main():
    L = a2test.labels(GAME / 'build/dirtbike.lbl')
    global TITLE                        # every track finished: all open in the menu
    TITLE = [L.until('tick_wait', 3000)] + [L.poke('rec_min', 0, i) for i in range(30)] + TITLE
    ks = [int(a) for a in sys.argv[1:]] or [1, 9, 17, 30]
    bad = 0
    for k in ks:
        h, fin = tracks.build(k)
        ids, pats, pool, offs = track.compile_patterns(h)
        n = len(pats)
        steps = ['wait:1300'] + TITLE + menu_keys(k) + [L.until('new_race', 600),
                 L.peek('finish_x', 2), L.peek('pat_k', n), L.peek('pat_rel0', n),
                 L.peek('pat_plo', n), L.peek('pat_phi', n), L.peek('__OVL_START__', len(pool)),
                 'peek:9600:4096', 'peek:A600:4096']
        r = a2test.run(DISK, steps)
        fx, pk, pr = r.mem(L['finish_x'], 2), r.mem(L['pat_k'], n), r.mem(L['pat_rel0'], n)
        plo, phi, pl = r.mem(L['pat_plo'], n), r.mem(L['pat_phi'], n), r.mem(L['__OVL_START__'], len(pool))
        hh, ii = r.mem(0x9600, 4096), r.mem(0xA600, 4096)
        pool_at = L['__OVL_START__']        # pool = the OVL area (dirtbike.cfg)
        want_addr = [pool_at + o for o in offs]
        checks = [
            ('finish', int.from_bytes(fx, 'little') == fin),
            ('k', list(pk) == [p[0] for p in pats]),
            ('rel0', list(pr) == [p[1] for p in pats]),
            ('addresses', [a | b << 8 for a, b in zip(plo, phi)] == want_addr),
            ('pool', pl == pool),
            ('heights', list(hh) == h),
            ('ids', list(ii) == ids),
        ]
        failed = [c for c, ok in checks if not ok]
        bad += bool(failed)
        print(f'track {k:2} {tracks.NAMES[k - 1]:15} ' + ('ok' if not failed else 'DIFF ' + ' '.join(failed)))
    # a second load in the same session: DOS's file manager is gone by then
    h, fin = tracks.build(30)
    steps = ['wait:1300'] + TITLE + menu_keys(1) + [L.until('new_race', 600), 'wait:60', 'key:\\e', L.until('main_menu', 300),
                                             'key:1', L.until('tick_wait', 900), 'key: ', 'wait:60'] + \
        menu_keys(30) + [L.until('new_race', 900), L.peek('finish_x', 2), 'peek:9600:4096']
    r = a2test.run(DISK, steps)
    ok = int.from_bytes(r.mem(L['finish_x'], 2), 'little') == fin and list(r.mem(0x9600, 4096)) == h
    bad += not ok
    print('track 30 after track 1, ESC, the main menu and the title: ' + ('ok' if ok else 'DIFF'))
    if bad:
        sys.exit('tracks: the game loads differently')


if __name__ == '__main__':
    main()
