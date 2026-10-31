#!/usr/bin/env python3
"""Title page, attract demo, hall of fame on the disk.

  * the title picture on page 1 is build/title.hgr (outside the prompt rows);
  * left alone, the title starts a demo ride when its tune ends: each of
    the six ends at the finish line with the model's points
    (tools/tricks.py), then the hall of fame;
  * a record (the finish line moved near the start, points set): initials
    XYZ typed, both records written into DIRTHOF on the disk, read back by
    the next boot; the game goes on to track 2;
  * on a write-protected disk the game says so and goes on;
  * a new disk: the menu opens track 1 only (the others are not finished);
  * ESC in a race opens the main menu: the input device changes, QUIT boots
    the disk again into BASIC (the stick: tests/test_input.py);
  * the title tune plays once, the demo starts when it ends; H on the title
    shows the help page; finishing track 30 shows the congratulations;
  * the countdown holds the bike; after a crash it restarts at rest at the
    last safe point (the start of a flat stretch, both wheels down), clock
    running on.
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
import music  # noqa: E402

DISK = GAME.parent / 'dist/DIRTBIKE.dsk'
NT = 30
PROMPT = range(64, 76)          # title.py TITLE_PROMPT - 2 .. + 10


SQ1 = [x * x // 4 for x in range(512)]
SQ2 = [SQ1[255 - x] if x < 256 else SQ1[x - 255] for x in range(512)]
MUL_TABLES = bytes(v & 255 for v in SQ1) + bytes(v >> 8 for v in SQ1) + bytes(v & 255 for v in SQ2) + bytes(v >> 8 for v in SQ2)


def hgr_rows():
    lo = bytes((((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28) & 255 for y in range(192))
    hi = bytes(0x20 + (y & 7) * 4 + ((y >> 3) & 7) // 2 for y in range(192))
    return lo + hi


HGR_LO = a2test.labels(GAME / 'build/dirtbike.lbl')['hgr_lo']      # hgr_lo, hgr_hi: SYSBSS
GUARD = [f'peek:{HGR_LO:04X}:384', 'peek:0800:2048']    # tables the drawing must never write over


def guarded(r):
    return r.mem(HGR_LO, 384) == hgr_rows() and r.mem(0x0800, 2048) == MUL_TABLES


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

    # the attract demos, all six: each ends at the finish line with the
    # model's points, then the hall of fame (a sprite drawn off screen once
    # broke the multiply tables in two of them: only one was checked)
    sols = trackcheck.solutions()
    for i, k in enumerate(packtrack.DEMOS):
        h, fin = tracks.build(k)
        _, t = tricks.ride(h, sols[k], fin)
        steps = ['wait:600', L.until('tick_wait', 3000), L.poke('demo_next', i), L.until('demo_start', 3000),
                 L.until('new_race', 900), L.until('demo_end', 9000), L.peek('score', 3), L.peek('state', 1),
                 L.peek('crashed', 1)]
        if i == 0:
            steps.append(L.until('hof_page', 60))
        r = a2test.run(DISK, steps + GUARD)
        score = r.mem(L['score'], 3)
        got = int(f'{score[2]:02x}{score[1]:02x}{score[0]:02x}')
        up = r.mem(L['crashed'], 1)[0] == 0      # still up when the hall of fame comes
        ok = got == t.score and r.mem(L['state'], 1)[0] == 2 and up and guarded(r)
        print(f'demo {i + 1}: track {k} finished with {got} points (model {t.score}), '
              f'{"still up" if up else "FELL"} after the line: ' + ('ok' if ok else 'DIFF'))
        bad += not ok

    # a record, saved
    with tempfile.TemporaryDirectory(prefix='dirtbike-hof-') as tmp:
        saved = Path(tmp) / 'saved.dsk'
        r = a2test.run(DISK, record_steps(L) + [L.until('new_race', 900), L.peek('sel', 1), f'dsk:{saved}'])
        image = saved.read_bytes()
        hof = dos33.read_file(image, 'DIRTHOF')
        rec_min, ini = hof[4], hof[4 + 3 * NT:4 + 3 * NT + 3]
        pts = hof[4 + 6 * NT:4 + 6 * NT + 3]
        pini = hof[4 + 9 * NT:4 + 9 * NT + 3]
        ok = (r.mem(L['sel'], 1)[0] == 1 and rec_min != 0xFF and ini == b'XYZ' and
              pts == bytes([0x00, 0x12, 0x00]) and pini == b'XYZ' and hof[-4:-1] == b'XYZ')
        print(f'record saved, then on to track 2: time {rec_min}:{hof[4 + NT]:02x}.{hof[4 + 2 * NT] >> 4} {ini.decode()}, '
              f'points {pts[2]:02x}{pts[1]:02x}{pts[0]:02x} {pini.decode()}: ' + ('ok' if ok else 'DIFF'))
        bad += not ok
        r = a2test.run(saved, ['wait:600', L.until('tick_wait', 3000), L.peek('rec_ini', 3), L.peek('rec_pts', 3)])
        ok = r.mem(L['rec_ini'], 3) == b'XYZ' and r.mem(L['rec_pts'], 3) == bytes([0x00, 0x12, 0x00])
        print('next boot reads it back: ' + ('ok' if ok else 'DIFF'))
        bad += not ok

        # R (restart) after a record: the initials first, the record saved
        # (R once started the race again, the record unsaved and nameless)
        rkey = Path(tmp) / 'rkey.dsk'
        steps = [s if s != 'key: ' else 'key:R' for s in record_steps(L)]
        r = a2test.run(DISK, steps + [L.until('new_race', 900), f'dsk:{rkey}'])
        hof = dos33.read_file(rkey.read_bytes(), 'DIRTHOF')
        ok = hof[4 + 3 * NT:4 + 3 * NT + 3] == b'XYZ'
        print('R after a record: the initials asked, the record saved: ' + ('ok' if ok else 'DIFF'))
        bad += not ok

        # write protected: said, not written, on to the menu
        prot = Path(tmp) / 'prot.dsk'
        r = a2test.run(DISK, record_steps(L) + [L.until('new_race', 900), f'dsk:{prot}'], wp=True)
        ok = dos33.read_file(prot.read_bytes(), 'DIRTHOF') == dos33.read_file(DISK.read_bytes(), 'DIRTHOF')
        print('write-protected disk: not written, on to the next track: ' + ('ok' if ok else 'DIFF'))
        bad += not ok
    # the title tune plays once; the demo starts when it ends
    T = sum(music.tune(music.TITLE, 8)[0::3])
    r = a2test.run(DISK, ['wait:600', L.until('tick_wait', 3000), f'wait:{T - 60}', L.peek('tune_ptr', 2),
                          'wait:120', L.peek('tune_ptr', 2)])
    ok = r.dumps[0][1] != 0 and r.dumps[1][1] == 0
    print(f'title tune ({T} ticks), then the demo: ' + ('ok' if ok else f'DIFF {[d.hex() for d in r.dumps]}'))
    bad += not ok

    # H on the title: the help page, a key: the title again
    def row_lit(page, y):
        return any(page[a2test.hgr_offset(y):a2test.hgr_offset(y) + 40])
    r = a2test.run(DISK, ['wait:1000', 'key:H', 'wait:200', 'peek:2000:8192', 'key: ', 'wait:300',
                          'peek:2000:8192'])
    page, back = r.dumps[0], r.dumps[1]
    title = [y for y in range(192) if y not in PROMPT and
             back[a2test.hgr_offset(y):a2test.hgr_offset(y) + 40] != want[a2test.hgr_offset(y):a2test.hgr_offset(y) + 40]]
    ok = row_lit(page, 8) and row_lit(page, 23 * 8) and not row_lit(page, 2 * 8) and not title
    print('title, H: the help page, then the title: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # track 30 finished: the congratulations page
    unlock = [L.poke('rec_min', 0, i) for i in range(30)]
    keys = [s for c in ['L'] + ['K'] * 14 for s in (f'key:{c}', 'wait:3')]
    r = a2test.run(DISK, ['wait:1000'] + unlock + ['key: ', 'wait:60'] + keys + ['key:\r', L.until('new_race', 900),
                          L.until('main_loop', 60), L.poke('finish_x', 40), L.poke('finish_x', 0, 1), L.poke('laps', 2),
                          'wait:220', L.peek('sel', 1), 'key: ', L.until('show_page', 600), 'wait:150', 'peek:2000:8192'])
    page = r.mem(0x2000, 8192)
    ok = r.mem(L['sel'], 1)[0] == 29 and row_lit(page, 3 * 8) and not row_lit(page, 8)
    print('track 30 finished: the congratulations page: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # the message in the HUD's middle: CRASH on both pages, then after the
    # restart's "1", "GO!", nothing left on either page
    r = a2test.run(DISK, ['wait:1000', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900), 'wait:300',
                          L.poke('crashed', 1), 'wait:30', 'peek:2000:8191', 'peek:4000:8191',
                          L.until('respawn', 600), 'wait:300', 'peek:2000:8191', 'peek:4000:8191'])

    def blank(p):
        return all(p[a2test.hgr_offset(y) + c] == 0 for y in range(8) for c in range(8, 32))
    ok = not blank(r.dumps[0]) and not blank(r.dumps[1]) and blank(r.dumps[2]) and blank(r.dumps[3])
    print('HUD message: shown on both pages, then no trace: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # a crash right after GO: CRASH, not the rest of GO! (a timed message
    # outlasted CRASH_FRAMES)
    r = a2test.run(DISK, ['wait:1000', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900),
                          L.until('main_loop', 60), L.poke('count_t', 1), 'wait:4', L.poke('crashed', 1),
                          'wait:30', L.peek('hud_sh', 2 * 26)])
    shown = bytes(c & 0x7F for c in r.mem(L['hud_sh'], 2 * 26)).decode('latin-1')
    ok = shown[12:26].strip() == 'CRASH !' and shown[38:52].strip() == 'CRASH !'
    print(f'crash after GO: {shown[12:26].strip()!r} / {shown[38:52].strip()!r}: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # ESC typed while the track loads: the race still starts (it once went
    # straight to the main menu)
    r = a2test.run(DISK, ['wait:1000', 'key: ', 'wait:60', 'key:\r', 'press:\x1b', L.until('main_loop', 900),
                          'wait:60', L.peek('count_t', 1)])
    ok = r.mem(L['count_t'], 1)[0] < 50
    print(f'ESC during the load: ignored, countdown at {r.mem(L["count_t"], 1)[0]}: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # a crashed bike sinking below the screen (rider forced to rows 196-205,
    # as a tumble can reach): drawn clamped, the tables stay untouched (a
    # sprite or line drawn off screen once wrote into them through hgr_lo /
    # hgr_hi; the demos check the top of the screen)
    steps = ['wait:1000', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900), 'wait:250']
    for y in (196, 200, 205):
        steps += [L.poke('crashed', 1), L.poke('pt_yh', y, 2), L.poke('pt_oyh', y, 2), 'wait:3']
    ok = guarded(a2test.run(DISK, steps + ['wait:60'] + GUARD))
    print('bike below the screen: the drawing never writes over the tables: ' + ('ok' if ok else 'DIFF'))
    bad += not ok

    # ESC in a race: the main menu (an overlay in TITLE); 3 changes the input
    # device (the joystick to the keyboard: tests/test_input.py); 5 quits: the
    # disk boots again and HELLO stops at BASIC
    r = a2test.run(DISK, ['wait:1000', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900), 'wait:100',
                          L.peek('inp_dev', 1), 'key:\x1b', L.until('main_menu', 300), 'wait:20', 'key:3', 'wait:20',
                          L.peek('inp_dev', 1), 'key:5', 'wait:800', 'peek:0400:40'])
    text = bytes(c & 0x7F for c in r.mem(0x0400, 40)).decode()
    ok = r.dumps[0] != r.dumps[1] and text.startswith('DIRTBIKE: BYE!')
    print(f'ESC: the main menu, input {r.dumps[0][0]} -> {r.dumps[1][0]}, quit to BASIC: ' + ('ok' if ok else f'DIFF {text!r}'))
    bad += not ok

    # ESC in a race, ESC in the main menu: the same race goes on (the track
    # read again over TITLE), after a countdown
    h1, _ = tracks.build(1)
    r = a2test.run(DISK, ['wait:1000', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900), 'wait:80'] +
                   [s for _ in range(10) for s in ('key:A', 'wait:3')] +
                   ['key:\x1b', L.until('mm_key', 300), L.peek('pt_xl', 2), L.peek('pt_xh', 2), L.peek('t_sec', 1),
                    'key:\x1b', L.until('main_loop', 600), L.peek('pt_xl', 2), L.peek('pt_xh', 2), L.peek('t_sec', 1),
                    L.peek('count_t', 1), 'peek:9600:4096', 'wait:120', L.peek('state', 1)])
    x0, x1 = (r.dumps[i][1] * 256 + r.dumps[i - 1][1] for i in (1, 4))
    ok = (x0 > 48 + 20 and x1 == x0 and r.dumps[2] == r.dumps[5] and r.dumps[6][0] > 0 and
          list(r.dumps[7]) == h1 and r.dumps[8][0] == 0)
    print(f'ESC, ESC: back to the race at x {x1} (left at {x0}), countdown {r.dumps[6][0]}, track read again: ' +
          ('ok' if ok else 'DIFF'))
    bad += not ok

    # a new disk: only track 1 open in the menu, the marker stays on it
    r = a2test.run(DISK, ['wait:1300', 'key: ', 'wait:60', 'key:K', 'wait:10', 'key:L', 'wait:10',
                          'key:K', 'wait:10', L.peek('sel', 1)])
    ok = r.mem(L['sel'], 1)[0] == 0
    print('menu: tracks not finished are locked: ' + ('ok' if ok else 'DIFF'))
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
    h1, _ = tracks.build(1)
    flat = len({h1[i] for i in range(safe - 6, safe + 24 + 7)}) == 1    # note_safe: SAFE_M, WHEELBASE
    # (safe > START_X 48: the restart point moved on from the start)
    ok = (held and d[3][0] == 1 and d[4][0] == 0 and x == safe and safe > 48 and d[8][0] > d[2][0]
          and d[9][0] == 0 and d[10][0] > 0 and flat)
    print(f'countdown holds the bike, crash -> restart at x {x} (safe point {safe}, flat {flat}), clock on: '
          + ('ok' if ok else f'DIFF {[v.hex() for v in d]}'))
    bad += not ok
    if bad:
        sys.exit('attract / hall of fame: failures')


if __name__ == '__main__':
    main()
