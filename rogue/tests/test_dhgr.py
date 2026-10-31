#!/usr/bin/env python3
"""ROGUE.DHGR (the game on the //e / //c double hi-res screen), headless.

    python3 tests/test_dhgr.py [--shots DIR] [--golden]

Runs build/rogue_dhgr.bin from a one-file DOS 3.3 disk (HELLO = BRUN
ROGUE.DHGR; the launcher's choice is test_rogue.py's business) in a2shot:

  //e (live session, 128 KB enhanced //e):
    - boot, title (its big banner), briefing (then the PRNG pinned: the same
      dungeons for every build), first dungeon; soft switches: graphics,
      full screen, HIRES, 80COL, 80STORE off (DHGR shown);
    - the oracle at every checkpoint: both banks of the page SHOWN equal the
      picture tools/x2_dhgr.py renders from the back-end's own copy of the
      virtual TMS9918 screen ($1800 names + $1B00 sprites; its camera when
      sprite 0 is not the hero): the game view the X2 way (9 x 5 cells
      centre-locked on the hero, HUD rows below) or a full page; at a key
      wait in the game view the HIDDEN page too (it caught up): every pixel,
      every screen hole;
    - a scripted 100-move game: IJKL walks and bumps, rests, the bag (B) and
      using its first item, help (H), dagger throws (T), the stairs (the
      player is put next to them): no crash, every turn ends at the key wait,
      HUD text on rows 20-23 of the model and on screen;
    - the red flash: the player's colour set to 8 and back, vid_idle after
      each: the page shown is different, then byte-identical to before;
    - write-once (a2shot storewatch over both pages): each byte of each page
      stored at most once an update (a turn: the frame on the hidden page,
      shown, then the other page catching up), with its final value, aux
      stores with IRQs masked: over the full redraw, one move, the random
      screens;
    - random virtual screens: three full pages (names 0..255, sprites
      anywhere) and seven game views (random tiles, sprites on the grid, the
      hero anywhere: the window past every map edge; once with a key
      waiting: the hidden page's catch-up waits);
    - ESC + Y: the mark "QU" at $0FFE and the boot ROM ($C600, the reboot);
    - cycles: the full redraw, a sprite recoloured, and for each move: key
      -> picture shown (the core's vid_idle in main_loop), key -> next key
      wait (+ the sound and the other page catching up) (printed).
  //c (one-shot script): boot, a few moves, the oracle (both pages).
  dist/ROGUE.dsk on a //e: the launcher, ROGUE.DHGR, ESC at the title: the
  disk boots again, HELLO says "ROGUE: BYE!" and stops (BASIC + DOS back).

--shots DIR: PNGs of checkpoints (dhgr_*.png, the page shown, x4/x2).
Golden: tests/dhgr_screens.txt = the sha1 of the virtual screen (names +
sprite table) at each //e checkpoint (with one after every bump / rest and
every modal closed), from the build before the 2026-10-31 turn-speed lots;
every build must match it (the core is unchanged; --golden rewrites it after
an intended change).
"""
import argparse
import hashlib
import random
import re
import sys
import tempfile
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test  # noqa: E402
import apple2img  # noqa: E402
import x2_dhgr  # noqa: E402

BIN = GAME / 'build/rogue_dhgr.bin'
DISK = ROOT / 'dist/ROGUE.dsk'
SEED = 0x1983                     # PRNG state after the briefing
LBL = GAME / 'build/rogue_dhgr.lbl'
TILE_EMPTY, TILE_STAIRS_DOWN = 0, 3
MON_COUNT, MON_SIZE, MON_TYPE, MON_COL, MON_ROW = 16, 8, 0, 2, 3
QUIT_MARK = 0x0FFE
PAGE = 8192
MEASURE = True                    # key -> picture of each move (tools/profile_dhgr.py: off)

DATA = x2_dhgr.load()
FAIL = []
GOLDEN = GAME / 'tests/dhgr_screens.txt'   # sha1 of each checkpoint's virtual screen
SCREENS = []                               # (tag, sha1 of names + sprite table)


def check(cond, what):
    if not cond:
        FAIL.append(what)
        print('FAIL:', what)
    return cond


def screen_steps(L):
    """Soft switches, the virtual screen, the camera, both banks of both
    pages (RAMRD aux for the second dump, main again before the CPU runs)."""
    return ['peek:C018:8', 'peek:1800:896', L.peek('x2_camc', 2),
            'peek:2000:16384', 'poke:C003:0', 'peek:2000:16384', 'poke:C002:0']


def decode_screen(out, L):
    """(switches, names, sat, cam, main, aux) from screen_steps(); main / aux:
    both pages (16 KB)."""
    r = a2test.Result(out)
    sw = r.mem(0xC018, 8)
    vram = r.mem(0x1800, 896)
    cam = r.mem(L['x2_camc'], 2)
    cam = tuple(v - 256 if v >= 128 else v for v in cam)
    main = r.mem(0x2000, 2 * PAGE, 0)
    aux = r.mem(0x2000, 2 * PAGE, 1)
    return sw, vram[:768], vram[768:896], cam, main, aux


def model(names, sat, cam):
    px, mode, cam = x2_dhgr.render_screen(names, sat, DATA, cam)
    main, aux = apple2img.dhgr_from_colors(px)
    return bytes(main), bytes(aux), mode


def oracle(out, L, tag, shots=None, record=True, hidden=None):
    """Compare the page shown (and the hidden one: hidden=True, or None =
    when the model says game view) with the model of the virtual screen."""
    sw, names, sat, cam, main, aux = decode_screen(out, L)
    ok = check(sw[0] < 0x80 and sw[2] < 0x80 and sw[3] < 0x80 and sw[5] >= 0x80
               and sw[7] >= 0x80,
               f'{tag}: switches 80STORE/TEXT/MIXED/HIRES/80COL = {sw.hex()}')
    vis = 1 if sw[4] >= 0x80 else 0
    if record:
        SCREENS.append((tag, hashlib.sha1(names + sat).hexdigest()))
    emain, eaux, mode = model(names, sat, cam)
    pages = [vis] + ([1 - vis] if hidden or (hidden is None and mode == 'game') else [])
    for p in pages:
        for bank, got, exp in (('main', main[p * PAGE:(p + 1) * PAGE], emain),
                               ('aux', aux[p * PAGE:(p + 1) * PAGE], eaux)):
            if got != exp:
                first = next(i for i in range(PAGE) if got[i] != exp[i])
                n = sum(1 for i in range(PAGE) if got[i] != exp[i])
                ok = check(False, f'{tag}: page {p + 1} ({"shown" if p == vis else "hidden"}, '
                           f'{mode}) {bank} bank differs from the model at '
                           f'${0x2000 + first:04X} ({n} bytes)')
    smain, saux = main[vis * PAGE:(vis + 1) * PAGE], aux[vis * PAGE:(vis + 1) * PAGE]
    if shots:
        apple2img.png_write(Path(shots) / f'dhgr_{tag}.png',
                            apple2img.dhgr_to_rgb(smain, saux), scale=(4, 2))
        if not ok:
            apple2img.png_write(Path(shots) / f'dhgr_{tag}_model.png',
                                apple2img.dhgr_to_rgb(emain, eaux), scale=(4, 2))
    return ok, names, sat, smain, saux, mode


def text_rows(names, first=20, last=23):
    return [bytes(c if 32 <= c < 127 else 32 for c in names[32 * r:32 * r + 32]).decode()
            for r in range(first, last + 1)]


STORE = re.compile(r'^store ([0-9A-F]{4}) ([0-9A-F]{4}) \S+ A=([0-9A-F]{2}) X=[0-9A-F]{2} '
                   r'Y=[0-9A-F]{2} S=[0-9A-F]{2} P=([0-9A-F]{2}) LC=\d\d\d(\d)(\d)')


def write_once(out, main, aux, tag):
    """storewatch lines of one update (or turn): every (bank, address) of
    both pages once, with the value the page ends with, RAMRD off; aux
    stores with IRQs masked (the core keeps them masked anyway)."""
    seen = {}
    for line in out.splitlines():
        m = STORE.match(line)
        if not m:
            continue
        addr, value = int(m[2], 16), int(m[3], 16)
        bank = 'aux' if m[6] == '1' else 'main'
        key = (bank, addr)
        if not check(key not in seen, f'{tag}: {bank} ${addr:04X} stored twice'):
            return seen
        seen[key] = value
        final = (aux if bank == 'aux' else main)[addr - 0x2000]
        if not check(value == final, f'{tag}: {bank} ${addr:04X} stored ${value:02X}, '
                     f'ends ${final:02X}'):
            return seen
        if not check(m[5] == '0' and (bank == 'main' or int(m[4], 16) & 4),
                     f'{tag}: IRQ mask / RAMRD around the store: {line}'):
            return seen
    return seen


def cycles_of(out, verb='until'):
    m = re.findall(rf'(?m)^{verb} \S+ cycles=(\d+)', out)
    return int(m[-1]) if m else None


def elapsed(out):
    return int(re.search(r'elapsed=(\d+)', out).group(1))


def pages_now(s, L, tag):
    """Both pages, both banks, as they are (for write_once)."""
    out = ''.join(s.step(st).out for st in screen_steps(L))
    return decode_screen(out, L)


def test_iie(shots):
    L = a2test.labels(LBL)
    wk = L['wait_key'] + 3            # @wk: LDA KBD (after JSR vid_idle)
    got_key = wk + 5                  # STA KBDSTRB: a key was there
    pic = L['main_loop'] + 6          # main_loop's JSR sfx_flush: the picture is shown
    rng = random.Random(1983)
    stats = {'checks': 0, 'moves': 0, 'turns': [], 'pics': [], 'pic_move': [], 'pic_free': [],
             'flash': 0, 'slow': []}
    with tempfile.TemporaryDirectory(prefix='rogue-dhgr-') as work:
        disk = a2test.build_disk(work, 'ROGUE.DHGR', BIN, load=L['entry'])
        with a2test.Session(disk, iie=True, timeout=600) as s:
            def wait_turn(tag):
                r = s.step(f'until:{wk:04X}:900')
                return check('PC=' in r.out and f'PC={wk:04X}' in r.out, f'{tag}: key wait reached')

            def peek(name, n=1):
                return s.step(L.peek(name, n)).dumps[0]

            def checkpoint(tag, record=True, hidden=None):
                out = ''.join(s.step(st).out for st in screen_steps(L))
                stats['checks'] += 1
                return oracle(out, L, tag, shots, record, hidden)

            def play(key, tag, watch=False, measure=False):
                s.step(f'press:{key}')
                r1 = s.step(f'until:{got_key:04X}:300')
                c0 = cycles_of(r1.out)
                if watch:
                    s.step('storewatch:2000:5FFF')
                c1 = None
                if measure and MEASURE:
                    r = s.step(f'until:{pic:04X},{wk:04X}:900')
                    if f'PC={pic:04X}' in r.out:
                        c1 = cycles_of(r.out)
                r2 = s.step(f'until:{wk:04X}:900')
                if watch:
                    s.step('unstorewatch')
                    stats['watched'] = r2.out
                ok = check(f'PC={wk:04X}' in r2.out, f'{tag}: back at the key wait after {key!r}')
                if ok and c0:
                    stats['turns'].append(cycles_of(r2.out) - c0)
                    stats['slow'].append((cycles_of(r2.out) - c0, tag, key))
                    if c1:
                        stats['pics'].append(c1 - c0)
                return ok

            # boot -> title (its own key loop) -> briefing -> game
            s.step(f'until:{L["wait_kb_choice"]:04X}:3000')
            s.step(f'until:{L["vid_idle"] + 7:04X}:600')     # the title drawn
            ok, names, *_ = checkpoint('title')
            check(any('ROGUE' in t for t in text_rows(names, 0, 23)), 'title text in the names')
            check(x2_dhgr.banner_on(names), 'title: the banner condition holds')
            s.step('key: ')
            s.step('wait:200')
            # the briefing's key; then the PRNG pinned (its state depends on
            # the time the title and briefing took): every build plays the
            # same dungeons, the timing lines compare
            s.step('press: ')
            s.step(f'until:{L["key_xlate"]:04X}:300')
            s.step(L.poke('prng_lo', SEED & 255))
            s.step(L.poke('prng_hi', SEED >> 8))
            wait_turn('first dungeon')
            ok, names, sat, main, aux, mode = checkpoint('dungeon1')
            hud = text_rows(names)
            check(mode == 'game', 'first dungeon: the game view')
            check('DEPTH' in hud[0] and 'HP' in ''.join(hud), f'HUD text: {hud}')
            check(any(main) or any(aux), 'something drawn')

            # full redraw cost (the hidden page, then shown) + the red flash
            # (sprite 0 = the player)
            s.step(f'call:{L["dg_redraw_all"]:04X}:5')
            r = s.step(f'call:{L["vid_idle"]:04X}:200')
            stats['full'] = elapsed(r.out)
            r = s.step(f'call:{L["vid_idle"]:04X}:200')
            stats['full2'] = elapsed(r.out)
            s.step(f'call:{L["dg_redraw_all"]:04X}:5')
            s.step('storewatch:2000:5FFF')
            stores = s.step(f'call:{L["vid_idle"]:04X}:400').out
            stores += s.step(f'call:{L["vid_idle"]:04X}:400').out
            s.step('unstorewatch')
            ok, names, sat, before_m, before_a, _ = checkpoint('redrawn')
            check(before_m == main and before_a == aux, 'full redraw = same picture')
            _, _, _, _, pm, pa = pages_now(s, L, 'redrawn')
            n = len(write_once(stores, pm, pa, 'full redraw'))
            want = 2 * 2 * (160 * 36 + 32 * 40)
            check(n == want, f'full redraw: {n} stores, {want} expected (every byte of '
                  f'the window and the HUD of both pages once)')
            colour = sat[3]
            s.step('poke:1B03:08')
            s.step(f'poke:{L["dg_chg"]:04X}:01')
            s.step(f'poke:{L["dg_satdp"]:04X}:01')
            s.step(f'poke:{L["dg_satdp"] + 1:04X}:01')
            r = s.step(f'call:{L["vid_idle"]:04X}:50')
            stats['flash'] = elapsed(r.out)
            ok, names, sat, fm, fa, _ = checkpoint('flash', hidden=False)
            check(sat[3] == 8 and (fm != before_m or fa != before_a), 'flash: the player turned red')
            s.step(f'poke:1B03:{colour:02X}')
            s.step(f'poke:{L["dg_chg"]:04X}:01')
            s.step(f'poke:{L["dg_satdp"]:04X}:01')
            s.step(f'poke:{L["dg_satdp"] + 1:04X}:01')
            s.step(f'call:{L["vid_idle"]:04X}:50')
            ok, names, sat, am, aa, _ = checkpoint('unflash', hidden=False)
            check(am == before_m and aa == before_a, 'flash: page restored byte for byte')
            s.step(f'call:{L["vid_idle"]:04X}:50')      # the other page catches up

            # 100 moves
            hp_addr = L['hp']
            plan = []
            for i in range(100):
                if i in (12, 47):
                    plan.append('B')
                elif i in (20, 70):
                    plan.append('BA')
                elif i == 30:
                    plan.append('H')
                elif i in (40, 85):
                    plan.append('T' + rng.choice('IJKL'))
                elif i in (55, 90):
                    plan.append('STAIRS')
                elif i % 9 == 4:
                    plan.append('.')
                else:
                    plan.append(rng.choice('IJKL') * rng.choice((1, 1, 2)))
            # a full bag (sword, tunic, amulet, potion, ration, torch) and 5
            # daggers: the bag shows its icons, 'BA' / throws do something
            inv = L['inventory']
            for slot, typ in enumerate((1, 2, 3, 4, 6, 8)):
                for off, val in ((0, typ), (1, 0), (2, 1), (3, 2)):
                    s.step(f'poke:{inv + 8 * slot + off:04X}:{val:02X}')
            s.step(L.poke('dagger_qty', 5))
            seen_hurt = False
            depth0 = peek('depth')[0]
            for i, act in enumerate(plan):
                s.step(f'poke:{hp_addr:04X}:0E')      # keep the hero alive (14 HP)
                tag = f'move{i:03d}'
                if act == 'STAIRS':
                    if not stairs_jump(s, L, tag):
                        continue
                elif act in ('B', 'BA', 'H'):
                    if not play(act[0], tag):
                        break
                    ok, names, *_ = checkpoint(f'{tag}_{act[0]}')
                    title = ' '.join(text_rows(names, 0, 3))
                    check(('INVENTORY' if act[0] == 'B' else 'HELP') in title,
                          f'{tag}: modal title in {title!r}')
                    if not play(act[1] if len(act) > 1 else ' ', tag):
                        break
                    checkpoint(f'{tag}_closed')     # the game view back
                elif act[0] == 'T':
                    if not play('T', tag) or not play(act[1], tag):
                        break
                else:
                    watch = i >= 5 and not stats.get('watched_ok') and len(act) == 1
                    for k in act:
                        where = peek('player_col', 2)
                        n0 = len(stats['pics'])
                        if not play(k, tag, watch=watch, measure=True):
                            break
                        moved = peek('player_col', 2) != where
                        if len(stats['pics']) > n0:
                            stats['pic_move' if moved else 'pic_free'].append(stats['pics'][-1])
                        if not moved:
                            checkpoint(f'{tag}_bump')   # a wall or a monster
                    if watch:           # the first move from 5 on that draws
                        ok, names, sat, wm, wa, _ = checkpoint(f'{tag}_watched')
                        _, _, _, _, pm, pa = pages_now(s, L, tag)
                        n = len(write_once(stats.pop('watched', ''), pm, pa, f'{tag} (write-once)'))
                        stats['watched_ok'] = n > 0
                        stats['watched_n'] = n
                stats['moves'] += 1
                sat = peek('dg_drawn', 4)
                if sat and sat[3] == 8:
                    seen_hurt = True
                if i % 10 == 9 or act == 'STAIRS':
                    checkpoint(tag)
            check(stats.get('watched_ok'), 'write-once: no move redrew anything')
            depth1 = peek('depth')[0]
            check(depth1 > depth0, f'stairs: depth {depth0} -> {depth1}')
            ok, names, *_ = checkpoint('end')
            hud = text_rows(names)
            check('DEPTH' in hud[0], f'HUD at the end: {hud}')
            # random virtual screens: full pages (every character, sprites
            # anywhere), then game views (the window past every map edge)
            for k in range(3):
                vram = [rng.randrange(256) for _ in range(768)]
                for e in range(32):
                    y = rng.choice((rng.randrange(192), rng.randrange(176, 256)))
                    vram += [0xD1 if y == 0xD0 else y, rng.randrange(253),
                             4 * rng.randrange(20), rng.randrange(16)]
                if k:
                    vram[768 + 4 * rng.randrange(8, 32)] = 0xD0
                random_screen(s, L, work, vram, f'random{k}', checkpoint)
            heroes = [(0, 0), (15, 9), (7, 0), (0, 5), (15, 2), (8, 9), (rng.randrange(16), rng.randrange(10))]
            for k, (hc, hr) in enumerate(heroes):
                vram = [0] * 768
                for r in range(10):
                    for c in range(16):
                        b = 4 * rng.choice((0, 0, 0, 1, 1, 2, 3, 4, 5, 6, 7))
                        for d, (dr, dc) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
                            vram[32 * (2 * r + dr) + 2 * c + dc] = b + d if b or rng.random() < .5 else 0
                for r in range(20, 24):
                    for c in range(32):
                        vram[32 * r + c] = rng.choice((0, 0, 32, 48, 65, 72, 90))
                sat = [16 * hr, 16 * hc, 0, rng.choice((5, 8))]
                for e in range(1, 32):
                    if rng.random() < .1:
                        sat += [rng.choice((160, 176)), 32 * rng.randrange(8), 4 * rng.randrange(14), rng.randrange(1, 16)]
                    else:
                        sat += [16 * rng.randrange(10), 16 * rng.randrange(16), 4 * rng.randrange(18),
                                rng.choice((0, 8, 8, 2, 5, 7, 9, 10, 13, 14, 15))]
                if k % 2:
                    sat[4 * rng.randrange(4, 32)] = 0xD0
                random_screen(s, L, work, vram + sat, f'x2random{k}', checkpoint, game=True,
                              interrupt=k == 3)
            stats['seen_hurt'] = seen_hurt
            # ESC, Y: the quit mark, then the boot ROM (the disk boots again)
            s.step('key:\x1b')
            s.step('wait:30')
            s.step('press:Y')
            r = s.step('until:C600:120')
            mark = s.step(f'peek:{QUIT_MARK:04X}:2').dumps[0]
            check('PC=C600' in r.out and mark == b'QU',
                  f'quit: reboot with the mark ({mark!r}, {r.out.strip()[-40:]})')
            sw = s.step('peek:C018:8').dumps[0]
            check(sw[2] >= 0x80 and sw[7] < 0x80 and sw[0] < 0x80,
                  f'quit: text, 40 columns, 80STORE off ({sw.hex()})')
    return stats


def random_screen(s, L, work, vram, tag, checkpoint, game=False, interrupt=False):
    """Poke a virtual screen (names + sprite table), flag every row and the
    sprite table for both pages, two updates (game view: draw + flip, then
    the catch-up) under storewatch: write-once, the oracle."""
    f = Path(work) / 'vram.bin'
    f.write_bytes(bytes(vram))
    s.step(f'load:{f}@1800')
    s.step(f'poke:{L["dg_txt"]:04X}:{0 if game else 1:02X}')
    s.step(f'poke:{L["dg_chg"]:04X}:01')
    for page in (0, 0x400):
        for row in range(24):
            s.step(f'poke:{L["dg_touch"] + page + row:04X}:01')
    s.step(f'poke:{L["dg_satdp"]:04X}:01')
    s.step(f'poke:{L["dg_satdp"] + 1:04X}:01')
    s.step('storewatch:2000:5FFF')
    stores = s.step(f'call:{L["vid_idle"]:04X}:400').out
    if game and interrupt:
        # a key waiting: the catch-up stops (the page shown is the frame)
        s.step('press:Z')
        r = s.step(f'call:{L["vid_idle"]:04X}:400')
        check('store ' not in r.out, f'{tag}: a key pending: no catch-up')
        s.step('peek:C010:1')                   # the key taken
    if game:
        stores += s.step(f'call:{L["vid_idle"]:04X}:400').out
    s.step('unstorewatch')
    ok, names, sat, *_ = checkpoint(tag, record=not game, hidden=game)
    _, _, _, _, pm, pa = pages_now(s, L, tag)
    write_once(stores, pm, pa, tag)
    if game:
        check(x2_dhgr.render_screen(names, sat, DATA)[1] == 'game', f'{tag}: a game view')


def stairs_jump(s, L, tag):
    """Put the player on a floor cell next to the stairs, step onto them."""
    mp = s.step(L.peek('map_buffer', 80)).dumps[0]
    mon = s.step(L.peek('monsters', MON_COUNT * MON_SIZE)).dumps[0]
    taken = {(mon[i + MON_COL], mon[i + MON_ROW]) for i in range(0, len(mon), MON_SIZE)
             if mon[i + MON_TYPE]}

    def cell(c, r):
        b = mp[8 * r + c // 2]
        return (b >> 4 if c & 1 else b) & 7
    for r in range(10):
        for c in range(16):
            if cell(c, r) != TILE_STAIRS_DOWN:
                continue
            for dc, dr, key in ((-1, 0, 'L'), (1, 0, 'J'), (0, -1, 'K'), (0, 1, 'I')):
                pc, pr = c + dc, r + dr
                if 0 <= pc < 16 and 0 <= pr < 10 and cell(pc, pr) == TILE_EMPTY \
                        and (pc, pr) not in taken:
                    s.step(L.poke('player_col', pc))
                    s.step(L.poke('player_row', pr))
                    s.step(f'press:{key}')
                    s.step('wait:2')
                    r = s.step(f'until:{L["wait_key"] + 3:04X}:900')
                    return check(f'PC={L["wait_key"] + 3:04X}' in r.out, f'{tag}: stairs taken')
    return check(False, f'{tag}: no stairs with a free floor cell beside them')


def test_iic(shots):
    """One-shot //c run: boot, a few moves, the oracle."""
    L = a2test.labels(LBL)
    wk = L['wait_key'] + 3
    with tempfile.TemporaryDirectory(prefix='rogue-dhgr-c-') as work:
        disk = a2test.build_disk(work, 'ROGUE.DHGR', BIN, load=L['entry'])
        steps = [f'until:{L["wait_kb_choice"]:04X}:3000', 'wait:30', 'key: ', 'wait:200',
                 'key: ', f'until:{wk:04X}:900']
        for k in 'LLKKJJII.':
            steps += [f'press:{k}', 'wait:2', f'until:{wk:04X}:900']
        steps += screen_steps(L)
        r = a2test.subprocess.run([str(a2test.A2SHOT), '--iic', '--disk', str(disk)] + steps,
                                  capture_output=True, text=True, timeout=300)
        check(r.returncode == 0, f'//c run: exit {r.returncode} {r.stderr[-300:]}')
        if r.returncode:
            return 0
        check(r.stdout.count(f'PC={wk:04X}') == 10, '//c: every move back at the key wait')
        ok, names, *_ = oracle(r.stdout, L, 'iic', shots, record=False)
        check('DEPTH' in text_rows(names)[0], '//c HUD')
        return 1


def test_disk():
    """dist/ROGUE.dsk on a //e 128 KB without the card: the launcher chains to
    ROGUE.DHGR; ESC at the title reboots; HELLO sees the mark and ends."""
    if not DISK.exists():
        return check(False, f'{DISK} missing: make')
    L = a2test.labels(LBL)
    r = a2test.run(DISK, ['wait:1', f'until:{L["wait_kb_choice"]:04X}:6000', 'wait:30',
                          'press:\\e', 'until:C600:120', 'wait:600', 'peek:0400:1024'], iie=True,
                   timeout=300, check=False)
    check(f'PC={L["wait_kb_choice"]:04X}' in r.out, 'dist disk: the launcher started ROGUE.DHGR')
    page = r.dumps[-1]
    rows = []
    for row in range(24):
        a = (row & 7) * 128 + (row >> 3) * 40
        rows.append(''.join(chr(b & 0x7F) if (b & 0x7F) >= 0x20 else chr((b & 0x7F) + 0x40)
                            for b in page[a:a + 40]))
    check(any('ROGUE: BYE!' in t for t in rows) and any(t.startswith(']') for t in rows),
          f'dist disk: ESC at the title -> reboot -> "ROGUE: BYE!" + prompt ({rows[:3]})')
    # Ctrl-RESET in the game: the same way out
    wk = L['wait_key'] + 3
    r = a2test.run(DISK, ['wait:1', f'until:{L["wait_kb_choice"]:04X}:6000', 'wait:30', 'key: ',
                          'wait:200', 'press: ', f'until:{wk:04X}:900', 'press:L', f'until:{wk:04X}:900',
                          'reset', 'until:C600:120', 'wait:600', 'peek:0400:1024'], iie=True,
                   timeout=300, check=False)
    page = r.dumps[-1] if r.dumps else b''
    text = ''.join(chr(b & 0x7F) for b in page)
    check(f'PC={wk:04X}' in r.out and 'ROGUE: BYE!' in text,
          'dist disk: Ctrl-RESET in the game -> reboot -> "ROGUE: BYE!"')


def golden(write):
    """The //e game's checkpoints against GOLDEN: rendering changes (the
    core's render_map / HUD caching, the back-end) must not change what the
    virtual screen holds at any checkpoint (the game is the same: same
    SEED, same keys)."""
    lines = [f'{tag} {h}' for tag, h in SCREENS]
    if write:
        GOLDEN.write_text('\n'.join(lines) + '\n')
        print(f'{GOLDEN.name}: {len(lines)} screens written')
        return
    if not GOLDEN.exists():
        return
    want = GOLDEN.read_text().split()
    want = list(zip(want[::2], want[1::2]))
    got = [tuple(line.split()) for line in lines]
    bad = [w[0] for w, g in zip(want, got) if w != g]
    check(len(want) == len(got) and not bad,
          f'{GOLDEN.name}: {len(got)} screens, {len(want)} expected, different: {bad[:5]}')
    if not bad and len(want) == len(got):
        print(f'{GOLDEN.name}: the {len(got)} checkpoint screens unchanged')


def med(v):
    return sorted(v)[len(v) // 2] if v else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots')
    ap.add_argument('--golden', action='store_true',
                    help=f'write {GOLDEN.name} (the screens every later build must show)')
    args = ap.parse_args()
    if not BIN.exists():
        raise SystemExit('build first: make')
    if args.shots:
        Path(args.shots).mkdir(parents=True, exist_ok=True)
    st = test_iie(args.shots)
    turns, pics = st['turns'], st['pics']
    print(f'//e: {st["moves"]} moves, {st["checks"]} screens = model; '
          f'full redraw {st["full"]} cycles (hidden page + flip), {st["full2"]} (the other), '
          f'sprite recolour {st["flash"]} cycles; write-once turn: {st.get("watched_n")} stores')
    print(f'    key -> picture shown: median {med(pics)} 90% {sorted(pics)[len(pics) * 9 // 10] if pics else 0} '
          f'max {max(pics) if pics else 0} cycles over {len(pics)} moves; key -> next key wait '
          f'median {med(turns)} max {max(turns) if turns else 0} over {len(turns)} turns')
    for what, v in (('a move (the window scrolls)', st['pic_move']),
                    ('a bump (the window stays)', st['pic_free'])):
        if v:
            print(f'    key -> picture, {what}: median {med(v)} 90% '
                  f'{sorted(v)[len(v) * 9 // 10]} max {max(v)} over {len(v)}')
    print('slowest turns (cycles, move, key):', sorted(st['slow'], reverse=True)[:4])
    golden(args.golden)
    test_iic(args.shots)
    test_disk()
    if FAIL:
        print(f'{len(FAIL)} failure(s)')
        sys.exit(1)
    print('ROGUE.DHGR: all checks passed (//e + //c + the disk)')


if __name__ == '__main__':
    main()
