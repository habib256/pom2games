#!/usr/bin/env python3
"""ROGUE on a2run --ezcolor=N (E-Z Color card, TMS9918A) and a2shot --iie.

Launcher decisions: card in slot 4 -> ROGUE.TMS; no card on a II+ -> the
"cannot run" page and back to DOS; no card on a //e 128 KB (a2shot) ->
ROGUE.DHGR. ROGUE.TMS: the Apple text notice, the VDP registers of the
game's mode, the title and the first dungeon in VRAM (rendered to
build/tests/*.png, --shots also to screenshots/), detection in slots 1, 2,
5, 7, a scripted 200-key game (moves, bumps, bag, throw, help, sound key)
with vdp_fast_writes == 0, a walk to the stairs (depth 2), the boss room
(B at the title), the bump sound
(heard with the sound on, silent after S), ESC at the title back to DOS.
"""
from collections import deque
from pathlib import Path
import random
import re
import sys

GAME = Path(__file__).resolve().parents[1]
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

DISK = ROOT / 'dist/ROGUE.dsk'
OUT = GAME / 'build/tests'
L = a2test.labels(GAME / 'build/rogue_tms.lbl')
LL = a2test.labels(GAME / 'build/launcher.lbl')
BOOT = ['wait:1500']                          # DOS boot + launcher + ROGUE.TMS
START = BOOT + ['key:X', 'wait:30', 'key:X', 'wait:60']   # title, briefing
GAME_REGS = [0x00, 0xC2, 0x06, 0x80, 0x00, 0x36, 0x07, 0x01]
DIRS = {'I': (0, -1), 'K': (0, 1), 'J': (-1, 0), 'L': (1, 0)}
fails = 0


def check(cond, what):
    global fails
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        fails += 1


def run(steps, slot=4, **kw):
    return a2test.run(DISK, steps, ezcolor=slot, **kw)


def screen(r, i=-1):
    s = r.text_screens()
    return s[i].split('\n') if s else []


def state(steps):
    """Run, then read the map, the player, the monsters, depth and hp."""
    r = run(steps + [L.peek('map_buffer', 80), L.peek('player_col', 2),
                     L.peek('monsters', 128), L.peek('depth'), L.peek('hp')])
    d = r.dumps[-5:]
    cells = {}
    for row in range(10):
        for col in range(16):
            b = d[0][row * 8 + col // 2]
            cells[col, row] = (b >> (4 * (col & 1))) & 7
    mons = {(d[2][k + 2], d[2][k + 3]) for k in range(0, 128, 8) if d[2][k]}
    return r, cells, (d[1][0], d[1][1]), mons, d[3][0], d[4][0]


def path_to(cells, start, goal_tile):
    """BFS over the interior (no walls, no pits) to a cell of goal_tile."""
    seen, q = {start: None}, deque([start])
    while q:
        c = q.popleft()
        if cells[c] == goal_tile and c != start:
            out = []
            while seen[c] is not None:
                out.append(seen[c][1])
                c = seen[c][0]
            return out[::-1]
        for k, (dx, dy) in DIRS.items():
            n = (c[0] + dx, c[1] + dy)
            if not (1 <= n[0] <= 14 and 1 <= n[1] <= 8) or n in seen:
                continue
            if cells[n] in (0, 2, 3):
                seen[n] = (c, k)
                q.append(n)
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    shots = '--shots' in sys.argv

    # --- launcher, card in slot 4: chains to ROGUE.TMS -------------------
    r = run(['until:%04X:3000' % LL['chain'], 'pc'])
    m = re.search(r'A=([0-9A-F]{2}) X=[0-9A-F]{2} Y=([0-9A-F]{2})', r.out)
    check(m and int(m.group(2) + m.group(1), 16) == LL['cmd_tms'],
          'launcher, card in slot 4: BRUN ROGUE.TMS')

    # --- ROGUE.TMS up: Apple notice, registers, title in VRAM -----------
    r = run(BOOT + ['text', 'vregs'] + a2test.VDP_SHOT_STEPS)
    page = screen(r)
    check('ROGUE PLAYS ON THE E-Z COLOR MONITOR' in page[0], 'Apple page: notice on row 0')
    check('E-Z COLOR CARD IN SLOT 4' in page[1], 'Apple page: slot 4 named')
    check('SOUND: ON' in page[22], 'Apple page: SOUND: ON')
    check(r.vregs == GAME_REGS, 'VDP registers: Graphics I, 16x16 sprites, display on')
    names = r.vram[0x1800:0x1B00]
    check(b'ROGUE' in names and b'APPLE II E-Z COLOR ROGUELIKE' in names, 'title in the name table')
    check(any(r.vram[0x0000:0x0800]) and any(r.vram[0x3800:0x3A40]), 'pattern and sprite tables loaded')
    check(r.vram[0x2000:0x2004] == bytes([0xE1, 0xA1, 0xB1, 0x71]), 'colour table loaded')
    a2test.vdp_shot(r, OUT / 'title.png', border=True)
    if shots:
        a2test.vdp_shot(r, GAME / 'screenshots/title.png', border=True)
    check(r.vdp_fast == 0, 'boot: vdp_fast_writes == 0')

    # --- first dungeon -----------------------------------------------------
    r = run(START + ['text'] + a2test.VDP_SHOT_STEPS)
    names = r.vram[0x1800:0x1B00]
    check(b'DEPTH 001' in names and b'HP 14' in names, 'HUD: DEPTH 001, HP 14')
    check(any(c in names[:640] for c in (4, 5, 6, 7)), 'walls in the playfield')
    check(r.vram[0x1B00] < 0xD0 and r.vram[0x1B02] == 0, 'player sprite in SAT[0]')
    check('ROGUE PLAYS ON THE E-Z COLOR MONITOR' in screen(r)[0], 'Apple notice kept in play')
    a2test.vdp_shot(r, OUT / 'dungeon.png', border=True)
    if shots:
        a2test.vdp_shot(r, GAME / 'screenshots/dungeon.png', border=True)

    # --- other slots -------------------------------------------------------
    for slot in (1, 2, 5, 7):
        r = run(BOOT + ['text', 'vregs'], slot=slot)
        check(f'E-Z COLOR CARD IN SLOT {slot}' in screen(r)[1] and r.vregs == GAME_REGS,
              f'card in slot {slot}: found, game up')

    # --- no card on a II+: the page, a key, back to DOS --------------------
    r = a2test.run(DISK, BOOT + ['text', 'key:X', 'wait:60', 'text'])
    before, after = screen(r, 0), screen(r, -1)
    check('ROGUE CANNOT RUN ON THIS APPLE' in before[0], 'no card, II+: "CANNOT RUN" page')
    check(any('E-Z COLOR GRAPHICS INTERFACE' in row for row in before)
          and any('128K' in row for row in before), 'no card, II+: says what is needed')
    check(any(row.startswith('|]') for row in after), 'no card, II+: back at the DOS prompt')

    # --- no card on a //e 128 KB: ROGUE.DHGR ----------------------------------
    if a2test.have_a2shot('//e no-card launcher test'):
        r = a2test.run(DISK, ['wait:1', 'until:%04X:3000' % LL['chain'], 'peek:0400:40'], iie=True)
        row0 = ''.join(chr(c if c >= 0x20 else c + 0x40) for c in (b & 0x7F if b >= 0x80 else b
                                                                      for b in r.dumps[-1]))
        check('NO E-Z COLOR CARD: DHGR' in row0 and 'until %04X' % LL['chain'] in r.out,
              'launcher, //e 128K without card: chains to ROGUE.DHGR')

    # --- ESC at the title: back to DOS, card picture blanked --------------
    r = run(BOOT + ['key:\x1b', 'wait:60', 'text', 'vregs'])
    check(any(row.startswith('|]') for row in screen(r)) and not r.vregs[1] & 0x40,
          'ESC at the title: DOS prompt, card display off')

    # --- ESC in play: N stays, Y leaves -----------------------------------
    r = run(START + ['key:\x1b', 'wait:5', 'key:N', 'wait:5', 'key:\x1b', 'wait:5'] + a2test.VDP_SHOT_STEPS)
    check(b'QUIT TO DOS? Y OR N' in r.vram[0x1AE0:0x1B00] and r.vregs == GAME_REGS,
          'ESC in play: asks, N keeps playing')
    r = run(START + ['key:\x1b', 'key:Y', 'wait:60', 'text'])
    check(any(row.startswith('|]') for row in screen(r)), 'ESC then Y in play: DOS prompt')

    # --- bump sound: on, then off after S ------------------------------------
    r, cells, me, mons, depth, hp = state(START)
    walk = None                 # a straight walk over free floor to a wall
    for k, (dx, dy) in DIRS.items():
        c, n = me, 0
        while cells[c[0] + dx, c[1] + dy] == 0 and (c[0] + dx, c[1] + dy) not in mons:
            c, n = (c[0] + dx, c[1] + dy), n + 1
        if cells[c[0] + dx, c[1] + dy] == 1 and (walk is None or n < len(walk)):
            walk = [k] * n
            wall = k
    check(walk is not None, 'bump test: a wall in reach')
    START2 = START + [f'key:{k}' for k in walk]
    r = run(START2 + ['wait:10', 'spk', f'key:{wall}', 'wait:10', 'spk', 'key:S', 'wait:10', 'spk',
                     f'key:{wall}', 'wait:10', 'spk'])
    check(r.spk[1] > 10, f'bump into a wall: the speaker sounds ({r.spk[1]} flips)')
    check(r.spk[3] == 0, 'sound off (S): the bump is silent')

    # --- POM1's hidden B at the title: the demon's room, its sound --------
    r = run(BOOT + ['key:B', 'wait:30', 'spk', 'key:X', 'wait:120', 'spk'] + a2test.VDP_SHOT_STEPS)
    check(b'DEPTH 013' in r.vram[0x1A80:0x1AA0] and r.spk[1] > 100 and r.vdp_fast == 0,
          f'B at the title: depth 13, the boss sound ({r.spk[1]} flips)')

    # --- scripted 200-key game: no fast VDP access ---------------------------
    rnd = random.Random(1982)
    keys = []
    while len(keys) < 200:
        x = rnd.random()
        if x < 0.75:
            keys.append(rnd.choice('IJKL'))
        elif x < 0.82:
            keys.append('.')
        elif x < 0.88:
            keys += ['B', rnd.choice('ABC')]
        elif x < 0.93:
            keys += ['T', rnd.choice('IJKL')]
        elif x < 0.97:
            keys += ['H', 'X']
        else:
            keys += ['S', 'S']
    r = run(START + [s for k in keys for s in (f'key:{k}', 'wait:2')] + ['text', 'vregs', 'pc'])
    check(r.vdp_fast == 0, f'200 keys of play: vdp_fast_writes == {r.vdp_fast}')
    check(r.vregs == GAME_REGS and 'ROGUE PLAYS' in screen(r)[0], '200 keys of play: still running')

    # --- to the stairs: depth 2 ------------------------------------------------
    moves = []
    for _ in range(80):
        r, cells, me, mons, depth, hp = state(START + [f'key:{k}' for k in moves])
        if depth == 2 or hp == 0:
            break
        p = path_to(cells, me, 3)
        if not p:
            moves.append('.')
            continue
        moves.append(p[0])
    check(depth == 2, f'walked to the stairs in {len(moves)} keys: depth 2')
    r = run(START + [f'key:{k}' for k in moves] + ['wait:30'] + a2test.VDP_SHOT_STEPS)
    check(b'DEPTH 002' in r.vram[0x1800:0x1B00] and r.vdp_fast == 0, 'HUD: DEPTH 002, no fast access')
    a2test.vdp_shot(r, OUT / 'depth2.png', border=True)

    print('rogue: %s' % ('PASS' if not fails else f'{fails} FAILED'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
