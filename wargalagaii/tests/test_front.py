#!/usr/bin/env python3
"""WARGALAGA II lot 9: the title screen, the attract mode, the records.

    title       page 1 = tools/title.py's picture over the menu; J switches
                keyboard / joystick, H the help, another key the menu
    idle        menu, then the high scores, then the demo
    demo        the attract mode's game == tools/model.py fed src/demo.inc,
                from level 1 to its end (then the title); a key or a button
                stops it at once, and the demo's score is no record
    record      a game's score enters the table (tools/records.py's rules):
                initials typed, HIGHSCORES written then read back; with the
                stick (letters picked up / down, the button), on a
                write-protected disk (an error, the table kept in memory)

    tests/test_front.py --disk ../dist/WARGALAGAII.po --labels build/game.lbl
"""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'wargalagaii'
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test
from block import Block
from hgr_tables import hgr_offset
import demo
import model as M
import records as R
import test_screen

PANEL_TOP = 88                       # front.s
MENU, SCORES, HELP, ENTRY = range(4)
GLYPHS = test_screen.font()
# Until the menu waits (fr_loop): the first HIGHSCORES read takes ~60 frames,
# more or less a disk turn depending on where the code before it sits.
START = lambda L: [L.until('main', 3000), L.until('front_main', 3000), L.until('fr_loop', 300), 'wait:2']


def text_at(page, line, col, text):
    """True when page 1 shows text at (line, column), glyphs as glyph_sta."""
    return all(page[hgr_offset(8 * line + r) + col + k] == GLYPHS[ord(ch)][r]
               for k, ch in enumerate(text) for r in range(8))


def records_model():
    t = R.DEFAULTS
    assert [s for _, s, _ in t] == sorted((s for _, s, _ in t), reverse=True)
    assert R.rank(t, 50001) == 0 and R.rank(t, 50000) == 1, 'an equal score goes below'
    assert R.rank(t, 2000) is None and R.rank(t, 2001) == 7
    new = R.insert(t, 'XYZ', 19999, 7)
    assert new[4] == ('XYZ', 19999, 7) and new[5] == t[4] and len(new) == R.REC_N
    assert R.decode(R.encode(new, 1)) == (new, 1)
    assert R.level_reached(6, 0) == 7 and R.level_reached(99, 2) == 255 and R.level_reached(54, 2) == 255
    assert R.level_reached(53, 2) == 254
    print('PASS records rules: order, ties below, insert, file round trip, level reached')


def title(disk, L):
    hgr = (GAME / 'build/title.hgr').read_bytes()
    steps = START(L) + [L.peek('fr_panel'), 'peek:2000:8192', 'peek:C01A', 'peek:C01C', 'peek:C01D',
                        'key:J', 'wait:20', L.peek('joy_mode'), 'peek:2000:8192',
                        'key:H', 'wait:20', L.peek('fr_panel'), 'peek:2000:8192',
                        'key:Q', 'wait:20', L.peek('fr_panel'), 'key:J', 'wait:20', L.peek('joy_mode')]
    r = a2test.run(disk, steps, iie=True)
    page = r.mem(0x2000, 8192, 0)
    assert r.mem(L['fr_panel'], 1, 0)[0] == MENU
    assert not r.mem(0xC01A, 1)[0] & 0x80 and not r.mem(0xC01C, 1)[0] & 0x80 and r.mem(0xC01D, 1)[0] & 0x80, \
        'HGR page 1 shown'
    for y in range(PANEL_TOP):
        a = hgr_offset(y)
        assert page[a:a + 40] == hgr[a:a + 40], f'title row {y}'
    assert text_at(page, 12, 6, 'RETURN OR FIRE TO PLAY') and text_at(page, 14, 22, 'KEYBOARD')
    assert text_at(page, 15, 22, 'ON ') and text_at(page, 20, 9, 'WAR   50000  L 10')
    assert r.mem(L['joy_mode'], 1, 0)[0] == 1 and text_at(r.mem(0x2000, 8192, 1), 14, 22, 'JOYSTICK')
    assert r.mem(L['fr_panel'], 1, 1)[0] == HELP and text_at(r.mem(0x2000, 8192, 2), 11, 2, '<- -> OR J L')
    assert r.mem(L['fr_panel'], 1, 2)[0] == MENU and r.mem(L['joy_mode'], 1, 1)[0] == 0
    print('PASS title: the picture (LZ4FH) on page 1, the menu, J joystick / keyboard, H help, a key: menu')


def idle(disk, L):
    """Nobody: menu (~10 s), scores (~8 s), the demo."""
    r = a2test.run(disk, START(L) + ['wait:700', L.peek('fr_panel'), 'peek:2000:8192',
                                     L.until('demo_init', 900), L.peek('demo')], iie=True)
    page = r.mem(0x2000, 8192)
    assert r.mem(L['fr_panel'], 1)[0] == SCORES and text_at(page, 11, 14, 'HIGH SCORES')
    for k, (name, score, level) in enumerate(R.DEFAULTS):
        assert text_at(page, 13 + k, 6, f'{k + 1}. {name}  {score:6d}  L{level:3d}'), (k, name)
    print('PASS idle title: menu, then the high scores (defaults), then the demo')


def state_names(L):
    names = [n for n in M.Game().state() if n != 'prng']
    return names, Block(L, {n: len(v) for n, v in M.Game().state().items() if n != 'prng'})


def demo_oracle(disk, L):
    """The whole demo == the model: the script's moves, fire held, then the
    steps past its end (no input) until the title."""
    names, blk = state_names(L)
    checkpoints = []
    for refreshes in (400, 1000, 1200, 1000, 1400):
        checkpoints += [f'wait:{refreshes}', L.peek('level'), L.peek('lkind'), L.peek('a_state', M.NALIENS)]
    r = a2test.run(disk, [L.until('main', 3000), L.until('demo_init', 4000), L.peek('step_count', 2),
                          *checkpoints,
                          L.until('front_main', 7000), L.peek('step_count', 2),
                          *blk.peeks(), L.peek('prng_lo', 2), L.peek('demo_end'),
                          'wait:60', L.peek('fr_panel'), 'key: ', 'wait:40',
                          L.peek('level'), L.peek('demo')], iie=True, timeout=600)
    assert [r.mem(L['level'], 1, k)[0] for k in range(5)] == [0, 2, 3, 7, 24]
    assert [r.mem(L['lkind'], 1, k)[0] for k in range(5)] == [M.NORMAL, M.BIG, M.KAMIKAZE, M.BONUS, M.BOSS]
    assert M.PASS in r.mem(L['a_state'], M.NALIENS, 3), 'the bonus stage actually displays passing aliens'
    assert r.mem(L['level'], 1, 5) == b'\0' and r.mem(L['demo'], 1) == b'\0', 'a real game starts at level 1'
    n = int.from_bytes(r.mem(L['step_count'], 2, 1), 'little') - int.from_bytes(r.mem(L['step_count'], 2, 0), 'little')
    script = demo.decode(bytes(int(v[1:], 16) for line in (GAME / 'src/demo.inc').read_text().split('demo_script:')[1].splitlines()
                               if line.strip().startswith('.byte') for v in line.split()[1].split(',')))
    assert len(script) == demo.DEMO_STEPS and r.mem(L['demo_end'], 1)[0] == 1
    assert demo.DEMO_STEPS < n <= demo.DEMO_STEPS + 2, n
    game = M.Game(0)
    kinds = set()
    for k in range(n):
        if k < len(script):
            demo.play(game, script[k])
        else:
            game.step(0, False, False)
        kinds.add(game.lkind)
    got, state = blk.read(r), game.state()
    for name in names:
        have = got[name]
        assert have == state[name], f'{name}: 6502 {have.hex()} model {state[name].hex()}'
    assert r.mem(L['prng_lo'], 2) == state['prng']
    assert r.mem(L['fr_panel'], 1)[0] == MENU, 'the demo is no record'
    assert kinds == {M.NORMAL, M.BIG, M.KAMIKAZE, M.BONUS, M.BOSS} and not game.game_over, kinds
    print(f'PASS demo: {n} steps == model (level {game.level + 1}, score {game.score}, '
          f'{game.lives} lives), then the title')


def demo_stop(disk, L):
    for refreshes, how in ((300, ['key:A']), (300, ['btn:0,1', 'wait:4', 'btn:0,0']),
                           (3600, ['key:A']), (3600, ['btn:0,1', 'wait:4', 'btn:0,0'])):
        r = a2test.run(disk, [L.until('main', 3000), L.until('demo_init', 4000), f'wait:{refreshes}', *how,
                              L.until('front_main', 30), 'wait:60', L.peek('fr_panel'), L.peek('score', 3)],
                       iie=True)
        assert r.mem(L['fr_panel'], 1)[0] == MENU and r.mem(L['score'], 3) != b'\0\0\0'
    print('PASS demo stopped by a key, by the button: the title, no record')


def play_and_quit(L, score, level, loop='rn_loop'):
    """From the menu: play, poke the score and level, ESC: the title, until
    its loop (the initials': rn_loop; the menu's: fr_loop). (Not a fixed
    wait: reading HIGHSCORES again takes ~60 frames.)"""
    return ['key:\\r', L.until('game_tick', 600), 'wait:30', L.poke('score', score & 255),
            L.poke('score', score >> 8 & 255, 1), L.poke('score', score >> 16, 2), L.poke('level', level),
            'key:\\e', L.until('front_main', 300), L.until('fb_wait', 300), 'key: ',   # GAME BONUSES
            L.until(loop, 300)]


def record_keyboard(disk, L):
    want = R.encode(R.insert(R.DEFAULTS, 'XYZ', 19999, 7))
    steps = START(L) + play_and_quit(L, 0x019999, 6) + [L.peek('fr_panel'), 'peek:2000:8192']
    steps += ['key:X', 'wait:6', 'key:Q', 'wait:6', 'key:\\<', 'wait:6', 'key:Y', 'wait:6', 'key:Z',
              'wait:200', L.peek('fr_panel'),
              L.peek('rec_buf', R.REC_SIZE), L.peek('rec_err'), 'peek:2000:8192']
    # read back: the table in memory spoilt, then a game (score 0) and ESC
    steps += [L.poke('rec_state', 0), L.poke('rec_buf', 0), L.poke('rec_buf', ord('Q'), 3)]
    steps += play_and_quit(L, 0, 0, 'fr_loop') + [L.peek('fr_panel'), L.peek('rec_buf', R.REC_SIZE)]
    r = a2test.run(disk, steps, iie=True, timeout=300)
    assert r.mem(L['fr_panel'], 1, 0)[0] == ENTRY
    page = r.mem(0x2000, 8192, 0)
    assert text_at(page, 12, 14, 'NEW RECORD!') and text_at(page, 14, 14, ' 19999  L  7'), 'entry panel'
    assert r.mem(L['fr_panel'], 1, 1)[0] == SCORES and text_at(r.mem(0x2000, 8192, 1), 17, 6, '5. XYZ   19999  L  7')
    assert r.mem(L['rec_buf'], R.REC_SIZE, 0) == want and r.mem(L['rec_err'], 1)[0] == 0
    assert r.mem(L['fr_panel'], 1, 2)[0] == MENU, 'score 0: no record'
    assert r.mem(L['rec_buf'], R.REC_SIZE, 1) == want, 'HIGHSCORES read back'
    print('PASS record, keyboard: 19999 at level 7 -> 5th, X Q <- Y Z typed (XYZ), HIGHSCORES written and read back')


def record_stick(disk, L):
    """Joystick chosen on the title; a write-protected disk: the controls
    and the record can't be saved (error $2B), the table stays in memory."""
    # (level 100 reached in EASY: NORMAL opens, byte 2 bit 1)
    want = R.encode(R.insert(R.DEFAULTS, 'BZA', 123456, 100), 1 | 2)
    down = ['joy:0,1', 'wait:4', 'joy:0,0', 'wait:4']
    up = ['joy:0,-1', 'wait:4', 'joy:0,0', 'wait:4']
    btn = ['btn:0,1', 'wait:4', 'btn:0,0', 'wait:4']
    steps = START(L) + ['key:J', 'wait:20'] + play_and_quit(L, 0x123456, 99)
    steps += [L.peek('rec_err'), L.peek('fr_panel')] + down + btn + up + btn + btn
    steps += ['wait:200', L.peek('fr_panel'), L.peek('rec_buf', R.REC_SIZE), L.peek('rec_err')]
    os.environ['POM2_MEDIA_WRITE_DEFAULT'] = 'protected'   # (a2shot has no --wp)
    try:
        r = a2test.run(disk, steps, iie=True, timeout=300)
    finally:
        del os.environ['POM2_MEDIA_WRITE_DEFAULT']
    assert r.mem(L['rec_err'], 1, 0)[0] == 0x2B, 'the controls: write-protected'
    assert r.mem(L['fr_panel'], 1, 0)[0] == ENTRY and r.mem(L['fr_panel'], 1, 1)[0] == SCORES
    assert r.mem(L['rec_buf'], R.REC_SIZE) == want, r.mem(L['rec_buf'], R.REC_SIZE)
    assert r.mem(L['rec_err'], 1, 1)[0] == 0x2B
    print('PASS record, stick: B Z A picked, 1st at level 100; write-protected disk: error $2B, '
          'table kept in memory')


def modes(disk, L):
    """2026-10-30: a new player has EASY only (M keeps it); a game that
    beat the boss of level 25 opens NORMAL (named on the menu, saved in
    HIGHSCORES byte 2); M then cycles EASY / NORMAL; the mode is the
    game's (model.MODES)."""
    page = lambda r, k: r.mem(0x2000, 8192, k)
    steps = START(L) + [L.peek('mode'), 'peek:2000:8192', 'key:M', 'wait:20', L.peek('mode')]
    steps += play_and_quit(L, 0, 25, loop='fr_loop') + ['wait:10', L.peek('mode'), L.peek('rec_buf', 3),
                                                         'peek:2000:8192']
    steps += ['key:M', 'wait:20', L.peek('mode'), L.peek('rec_buf', 3), 'peek:2000:8192',
              'key:\\r', L.until('game_tick', 600), 'wait:30', L.peek('mode'), L.peek('dive_gap')]
    r = a2test.run(disk, steps, iie=True, timeout=300)
    assert r.mem(L['mode'], 1, 0)[0] == M.EASY and text_at(page(r, 0), 16, 22, 'EASY  ')
    assert text_at(page(r, 0), 16, 9, 'M  MODE') and r.mem(L['mode'], 1, 1)[0] == M.EASY, 'EASY only'
    assert r.mem(L['mode'], 1, 2)[0] == M.EASY and r.mem(L['rec_buf'], 3, 0)[2] == 0b00010
    assert text_at(page(r, 1), 19, 15, 'NOW OPEN:') and text_at(page(r, 1), 19, 25, 'NORMAL')
    assert r.mem(L['mode'], 1, 3)[0] == M.NORMAL and r.mem(L['rec_buf'], 3, 1)[2] == 0b01010
    assert text_at(page(r, 2), 16, 22, 'NORMAL')
    assert r.mem(L['mode'], 1, 4)[0] == M.NORMAL and r.mem(L['dive_gap'], 1, 0)[0] == M.level_params(0, 0)[0]
    print('PASS modes: EASY at first, level 26 reached opens NORMAL (NOW OPEN, saved), M chooses it, '
          'the game plays it')


def bonuses(disk, L):
    """Lot 10, GAME BONUSES (Warblade's end of game): credits x 100, rank x
    10 000, perfect bonus levels x 5 000, added to the score before the
    records: 1 000 + 12 300 + 70 000 + 10 000 = 93 300, a record (1st)."""
    steps = START(L) + ['key:\\r', L.until('game_tick', 600), 'wait:30', L.poke('score', 0x00),
                        L.poke('score', 0x10, 1), L.poke('score', 0, 2), L.poke('credits', 0x23),
                        L.poke('credits', 0x01, 1), L.poke('rank', 7), L.poke('perfects', 2),
                        'key:\\e', L.until('front_main', 300), L.until('fb_wait', 600), 'wait:10',
                        L.peek('fr_panel'), 'peek:2000:8192', L.peek('score', 3), 'key: ',
                        L.until('rn_loop', 300), L.peek('fr_panel')]
    r = a2test.run(disk, steps, iie=True, timeout=300)
    page = r.mem(0x2000, 8192)
    assert r.mem(L['fr_panel'], 1, 0)[0] == 4 and text_at(page, 11, 14, 'GAME BONUSES')
    def line(label, count, times, amount):     # front.s: columns 4, 17-20, 22, 30-35
        return f'{label:<13}{count:>4} {times:<7} {amount:>6}'
    for row, text in ((13, line('CASH LEFT', '123', 'X 100', '12300')),
                      (14, line('RANK', '7', 'X 10000', '70000')),
                      (15, line('PERFECTS', '2', 'X 5000', '10000')),
                      (17, line('BONUS POINTS', '', '', '92300')), (19, line('SCORE', '', '', '93300'))):
        assert text_at(page, row, 4, text), (row, text)
    assert r.mem(L['score'], 3) == bytes([0x00, 0x33, 0x09]), r.mem(L['score'], 3).hex()
    assert r.mem(L['fr_panel'], 1, 1)[0] == ENTRY, 'a record with the bonuses'
    print('PASS GAME BONUSES: 123 credits, rank 7, 2 perfects: +92 300, score 93 300 -> a record')


def hi_at_start(disk, L):
    """Bug hunt 2026-10-30: HI started every game at 000000 (hi_score was in
    game_vars, cleared by new_game): it is the best record (WAR 50000)."""
    r = a2test.run(disk, START(L) + ['key:\\r', L.until('game_tick', 600), 'wait:10', L.peek('hi_score', 3)],
                   iie=True)
    assert r.mem(L['hi_score'], 3) == bytes((0x00, 0x00, 0x05)), r.mem(L['hi_score'], 3).hex()
    print('PASS HI at the start of a game: the best record (50000)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/game.lbl')
    a = ap.parse_args()
    records_model()
    if not a2test.have_a2shot('title screen'):
        return
    L = a2test.labels(a.labels, strip=True)
    title(a.disk, L)
    idle(a.disk, L)
    demo_stop(a.disk, L)
    record_keyboard(a.disk, L)
    record_stick(a.disk, L)
    bonuses(a.disk, L)
    modes(a.disk, L)
    hi_at_start(a.disk, L)
    demo_oracle(a.disk, L)


if __name__ == '__main__':
    main()
