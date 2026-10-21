#!/usr/bin/env python3
"""Title page, attract demo, hall of fame on the disk.

  * the title picture on page 1 is build/title.hgr (outside the prompt rows);
  * left alone, the title starts the first demo ride after ~15 s: it ends at
    the finish line with the model's points (tools/tricks.py), then the hall
    of fame;
  * a record (the finish line moved near the start, points set): initials
    XYZ typed, both records written into DIRTHOF on the disk, read back by
    the next boot;
  * on a write-protected disk the game says so and goes on to the menu;
  * the countdown holds the bike; after a crash it restarts at rest at the
    last safe point (both wheels down, level), clock running on.
"""
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test  # noqa: E402
import dos33  # noqa: E402
import packtrack  # noqa: E402
import trackcheck  # noqa: E402
import tracks  # noqa: E402
import tricks  # noqa: E402

DISK = GAME.parent / 'dist/DIRTBIKE.dsk'
NT = 30
PROMPT = range(148, 160)


def record_steps(L):
    """Title -> track 1; last lap, finish line behind the bike (x 40), 1200 points; the record's
    initials XYZ."""
    return ['wait:1300', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900), L.until('main_loop', 60),
            L.poke('finish_x', 40), L.poke('finish_x', 0, 1), L.poke('laps', 2),
            L.poke('score', 0x00), L.poke('score', 0x12, 1), L.poke('score', 0x00, 2),
            'wait:220', L.peek('state', 1), 'key: ', 'wait:30',
            'key:X', 'wait:5', 'key:Y', 'wait:5', 'key:Z', 'wait:5', 'key:\r']


def main():
    L = a2test.labels(GAME / 'build/dirtbike.lbl')
    bad = 0

    # the title
    r = a2test.run(DISK, ['wait:600', L.until('tick_wait', 3000), 'peek:2000:8192'])
    page, want = r.mem(0x2000, 8192), (GAME / 'build/title.hgr').read_bytes()
    rows = [y for y in range(192) if y not in PROMPT and
            page[a2test.hgr_offset(y):a2test.hgr_offset(y) + 40] != want[a2test.hgr_offset(y):a2test.hgr_offset(y) + 40]]
    print('title page: ' + ('ok' if not rows else f'DIFF rows {rows[:8]}'))
    bad += bool(rows)

    # the attract demo
    k = packtrack.DEMOS[0]
    h, fin = tracks.build(k)
    _, t = tricks.ride(h, trackcheck.solutions()[k], fin)
    r = a2test.run(DISK, ['wait:600', L.until('demo_start', 3000), L.until('new_race', 900),
                          L.until('demo_end', 8000), L.peek('score', 3), L.peek('state', 1),
                          L.until('hof_page', 60)])
    score = r.mem(L['score'], 3)
    got = int(f'{score[2]:02x}{score[1]:02x}{score[0]:02x}')
    ok = got == t.score and r.mem(L['state'], 1)[0] == 2
    print(f'demo: track {k} finished with {got} points (model {t.score}), then the hall of fame: '
          + ('ok' if ok else 'DIFF'))
    bad += not ok

    # a record, saved
    with tempfile.TemporaryDirectory(prefix='dirtbike-hof-') as tmp:
        saved = Path(tmp) / 'saved.dsk'
        r = a2test.run(DISK, record_steps(L) + [L.until('menu', 900), f'dsk:{saved}'])
        image = saved.read_bytes()
        hof = dos33.read_file(image, 'DIRTHOF')
        rec_min, ini = hof[4], hof[4 + 3 * NT:4 + 3 * NT + 3]
        pts = hof[4 + 6 * NT:4 + 6 * NT + 3]
        pini = hof[4 + 9 * NT:4 + 9 * NT + 3]
        ok = (r.mem(L['state'], 1)[0] == 3 and rec_min != 0xFF and ini == b'XYZ' and
              pts == bytes([0x00, 0x12, 0x00]) and pini == b'XYZ' and hof[-3:] == b'XYZ')
        print(f'record saved: time {rec_min}:{hof[4 + NT]:02x}.{hof[4 + 2 * NT] >> 4} {ini.decode()}, '
              f'points {pts[2]:02x}{pts[1]:02x}{pts[0]:02x} {pini.decode()}: ' + ('ok' if ok else 'DIFF'))
        bad += not ok
        r = a2test.run(saved, ['wait:600', L.until('tick_wait', 3000), L.peek('rec_ini', 3), L.peek('rec_pts', 3)])
        ok = r.mem(L['rec_ini'], 3) == b'XYZ' and r.mem(L['rec_pts'], 3) == bytes([0x00, 0x12, 0x00])
        print('next boot reads it back: ' + ('ok' if ok else 'DIFF'))
        bad += not ok

        # write protected: said, not written, on to the menu
        prot = Path(tmp) / 'prot.dsk'
        r = a2test.run(DISK, record_steps(L) + [L.until('menu', 900), f'dsk:{prot}'], wp=True)
        ok = dos33.read_file(prot.read_bytes(), 'DIRTHOF') == dos33.read_file(DISK.read_bytes(), 'DIRTHOF')
        print('write-protected disk: not written, back to the menu: ' + ('ok' if ok else 'DIFF'))
        bad += not ok
    # countdown, then a crash: the restart point
    st = ['wait:1300', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900), 'wait:40',
          L.peek('count_t', 1), L.peek('pt_xl', 1), 'wait:100'] + \
        [s for _ in range(8) for s in ('key:A', 'wait:3')] + \
        ['wait:200', L.peek('t_sec', 1), L.poke('crashed', 1), 'wait:40', L.peek('state', 1),
         L.until('respawn', 600), 'wait:4',      # in the short count: still at the point
         L.peek('state', 1), L.peek('pt_xl', 1), L.peek('pt_xh', 1), L.peek('safe_x', 2), L.peek('t_sec', 1),
         L.peek('crashed', 1), L.peek('count_t', 1)]
    r = a2test.run(DISK, st)
    d = r.dumps
    held = d[0][0] > 0 and d[1][0] == 48
    x, safe = d[5][0] | d[6][0] << 8, d[7][0] | d[7][1] << 8
    ok = (held and d[3][0] == 1 and d[4][0] == 0 and x == safe and safe > 300 and d[8][0] > d[2][0]
          and d[9][0] == 0 and d[10][0] > 0)
    print(f'countdown holds the bike, crash -> restart at x {x} (safe point {safe}), clock on: '
          + ('ok' if ok else f'DIFF {[v.hex() for v in d]}'))
    bad += not ok
    if bad:
        sys.exit('attract / hall of fame: failures')


if __name__ == '__main__':
    main()
