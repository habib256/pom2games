#!/usr/bin/env python3
"""ROGUE on the POM2 core: a2shot --ezcolor=N, POM2's own E-Z Color card
(TMS9918A, silicon-strict access window: an access the chip cannot serve
yet is dropped and counted, as on the part).

Launcher: card in slot 4 -> ROGUE.TMS (the Apple page names the slot);
cards in slots 1, 2, 5, 7 found; slot 6 holds the Disk II, so POM2 refuses
a card there; no card on a ][+ -> the "cannot run" page; no card on a //e
128 KB -> ROGUE.DHGR. ROGUE.TMS: the title and the first dungeon rendered
by POM2's card monitor (build/tests/pom2_*.png), their VRAM and registers
byte-identical to a2run's model at the same checkpoint (the dungeon seed
pinned at gen_dungeon: the PRNG counts the player's reaction time), and no
dropped access over the title, the scripted 200-key game of test_rogue.py
and the walk to the stairs (depth 2). Skipped without a2shot.
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
# Title key, briefing key, then the seed pinned when the first level starts.
SEEDED = BOOT + ['key:X', 'wait:30', 'press:X', L.until('gen_dungeon', 300),
                 L.poke('prng_lo', 0x5A), L.poke('prng_hi', 0x19), 'wait:60']
GAME_REGS = [0x00, 0xC2, 0x06, 0x80, 0x00, 0x36, 0x07, 0x01]
DIRS = {'I': (0, -1), 'K': (0, 1), 'J': (-1, 0), 'L': (1, 0)}
TABLES = (('pattern', 0x0000, 0x0800), ('name', 0x1800, 0x0300), ('SAT', 0x1B00, 0x80),
          ('colour', 0x2000, 0x20), ('sprite patterns', 0x3800, 0x0800))
fails = 0


def check(cond, what):
    global fails
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        fails += 1


def pom2(steps, slot=4, **kw):
    return a2test.run(DISK, steps, emulator=a2test.A2SHOT, ezcolor=slot, **kw)


def model(steps, slot=4):
    return a2test.run(DISK, steps, ezcolor=slot)


def screen(r, i=-1):
    s = r.text_screens()
    return s[i].split('\n') if s else []


def same_vram(a, b, what):
    bad = [name for name, at, n in TABLES if a.vmem(at, n) != b.vmem(at, n)]
    whole = sum(x != y for x, y in zip(a.vram, b.vram))
    check(not bad and whole == 0 and a.vregs == b.vregs,
          f'{what}: POM2 VRAM (16 KB) and registers = a2run\'s'
          + (f' (differ: {bad}, {whole} bytes)' if bad or whole else ''))


def cells_of(mapbuf):
    return {(c, r): (mapbuf[r * 8 + c // 2] >> (4 * (c & 1))) & 7 for r in range(10) for c in range(16)}


def path_to(cells, start, goal_tile, mons):
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
    if not a2test.have_a2shot('ROGUE on POM2'):
        return 0
    OUT.mkdir(parents=True, exist_ok=True)

    # --- launcher, card in slot 4: chains to ROGUE.TMS -------------------
    r = pom2(['until:%04X:3000' % LL['chain'], 'cpu'])
    m = re.search(r'cpu PC=[0-9A-F]{4} A=([0-9A-F]{2}) X=[0-9A-F]{2} Y=([0-9A-F]{2})', r.out)
    check(m and int(m.group(2) + m.group(1), 16) == LL['cmd_tms'],
          'launcher, POM2 card in slot 4: BRUN ROGUE.TMS')

    # --- title: Apple page, registers, POM2 picture, VRAM = a2run --------
    title = BOOT + ['text', 'vregs'] + a2test.VDP_SHOT_STEPS
    r = pom2(title + [f'vshot:{OUT / "pom2_title.png"}'])
    page = screen(r)
    check('ROGUE PLAYS ON THE E-Z COLOR MONITOR' in page[0] and 'E-Z COLOR CARD IN SLOT 4' in page[1],
          'Apple page: notice, slot 4 named')
    check(r.vregs == GAME_REGS, f'VDP registers: Graphics I, 16 KB, 16x16 sprites, display on {r.vregs}')
    check(b'APPLE II E-Z COLOR ROGUELIKE' in r.vmem(0x1800, 0x300), 'title in the name table')
    check(r.vdp_dropped == 0, f'boot + title: vdp_dropped == {r.vdp_dropped}')
    same_vram(r, model(title), 'title')
    print(f'     {OUT / "pom2_title.png"}')

    # --- first dungeon, seed pinned ----------------------------------------
    r = pom2(SEEDED + a2test.VDP_SHOT_STEPS + [f'vshot:{OUT / "pom2_dungeon.png"}'])
    check(b'DEPTH 001' in r.vmem(0x1800, 0x300), 'first dungeon: HUD DEPTH 001')
    check(r.vdp_dropped == 0, f'first dungeon: vdp_dropped == {r.vdp_dropped}')
    same_vram(r, model(SEEDED + a2test.VDP_SHOT_STEPS), 'first dungeon (seed 195A)')
    print(f'     {OUT / "pom2_dungeon.png"}')

    # --- scripted 200-key game (test_rogue.py's) ----------------------------
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
    # press + 15 frames (key: runs differently in the two emulators): every
    # turn ends back in wait_key, so both machines play the same game even
    # though their cycle counts (Disk II boot) and so the VDP frame phase differ.
    play = SEEDED + [s for k in keys for s in (f'press:{k}', 'wait:15')] + ['wait:30', 'text'] \
        + a2test.VDP_SHOT_STEPS
    r = pom2(play + [f'vshot:{OUT / "pom2_play200.png"}'])
    check(r.vdp_dropped == 0, f'200 keys of play: vdp_dropped == {r.vdp_dropped}')
    check(r.vregs == GAME_REGS and 'ROGUE PLAYS' in screen(r)[0], '200 keys of play: still running')
    same_vram(r, model(play), '200 keys of play')

    # --- to the stairs: depth 2 (one live session) -------------------------
    with a2test.Session(DISK, ezcolor=4) as s:
        for step in SEEDED:
            s.step(step)
        depth, moves = 1, 0
        for _ in range(80):
            q = s.step(L.peek('map_buffer', 80))
            mapbuf = q.dumps[0]
            me = tuple(s.step(L.peek('player_col', 2)).dumps[0][:2])
            mons = s.step(L.peek('monsters', 128)).dumps[0]
            depth = s.step(L.peek('depth')).dumps[0][0]
            hp = s.step(L.peek('hp')).dumps[0][0]
            if depth == 2 or hp == 0:
                break
            mset = {(mons[k + 2], mons[k + 3]) for k in range(0, 128, 8) if mons[k]}
            p = path_to(cells_of(mapbuf), me, 3, mset)
            s.step(f'key:{p[0] if p else "."}')
            moves += 1
        s.step('wait:30')
        v = s.step('vregs')
        s.step(f'vshot:{OUT / "pom2_depth2.png"}')
        names = s.step('vpeek:1800:768').vmem(0x1800, 768)
    check(depth == 2 and b'DEPTH 002' in names, f'walked to the stairs in {moves} keys: depth 2')
    check(v.vregs_dropped == 0, f'stairs walk: dropped == {v.vregs_dropped}')

    # --- other slots; slot 6 is the Disk II's --------------------------------
    for slot in (1, 2, 5, 7):
        r = pom2(BOOT + ['text', 'vregs'], slot=slot)
        check(f'E-Z COLOR CARD IN SLOT {slot}' in screen(r)[1] and r.vregs == GAME_REGS
              and r.vdp_dropped == 0, f'POM2 card in slot {slot}: found, game up, nothing dropped')
    r = pom2(BOOT, slot=6, check=False)
    check(r.vdp_dropped is None, 'card in slot 6: refused by POM2 (the Disk II boots from slot 6)')

    # --- no card -------------------------------------------------------------
    r = a2test.run(DISK, BOOT + ['text'], emulator=a2test.A2SHOT)
    check('ROGUE CANNOT RUN ON THIS APPLE' in screen(r)[0], 'no card, ][+ (POM2): "CANNOT RUN" page')
    r = a2test.run(DISK, ['wait:1', 'until:%04X:3000' % LL['chain'], 'text'], iie=True)
    check('NO E-Z COLOR CARD: DHGR' in screen(r)[0], 'no card, //e 128K (POM2): chains to ROGUE.DHGR')

    print('rogue (POM2): %s' % ('PASS' if not fails else f'{fails} FAILED'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
