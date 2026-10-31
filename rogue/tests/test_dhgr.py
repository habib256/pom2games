#!/usr/bin/env python3
"""ROGUE.DHGR (the game on the //e / //c double hi-res screen), headless.

    python3 tests/test_dhgr.py [--shots DIR]

Runs build/rogue_dhgr.bin from a one-file DOS 3.3 disk (HELLO = BRUN
ROGUE.DHGR; the launcher's choice is test_rogue.py's business) in a2shot:

  //e (live session, 128 KB enhanced //e):
    - boot, title, briefing (then the PRNG pinned: the same dungeons for
      every build), first dungeon; soft switches: graphics, full
      screen, page 1, HIRES, 80COL, 80STORE off (DHGR shown);
    - the oracle at every checkpoint: both banks of page 1 equal the picture
      tools/tiles_dhgr.py renders from the back-end's own copy of the
      virtual TMS9918 screen ($1800 names + $1B00 sprites): every pixel,
      every screen hole;
    - a scripted 100-move game: IJKL walks and bumps, rests, the bag (B) and
      using its first item, help (H), dagger throws (T), the stairs (the
      player is put next to them): no crash, every turn ends at the key wait,
      HUD text on rows 20-23 of the model and on screen;
    - the red flash: the player's colour set to 8 and back, vid_idle after
      each: the page is different, then byte-identical to before;
    - write-once (a2shot storewatch) over the full redraw, one move and
      three random screens (random names 0..255, random sprites, poked into
      the virtual screen): each byte of page 1 stored at most once a
      vid_idle, with its final value, aux stores with IRQs masked;
    - ESC + Y: back to the DOS on the 40-column text page;
    - cycles: vid_idle after every row dirtied (full redraw), a sprite
      recoloured, and key -> next key wait of each move (printed).
  //c (one-shot script): boot, a few moves, the oracle.

--shots DIR: PNGs of checkpoints (dhgr_*.png, the model's colours, x4/x2).
Golden: tests/dhgr_screens.txt = the sha1 of the virtual screen (names +
sprite table) at each //e checkpoint (with one after every bump / rest and
every modal closed), from the build before the 2026-10-31 turn-speed lots;
every build must match it (--golden rewrites it after an intended change).
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
import tiles_dhgr  # noqa: E402

BIN = GAME / 'build/rogue_dhgr.bin'
SEED = 0x1983                     # PRNG state after the briefing
LBL = GAME / 'build/rogue_dhgr.lbl'
LOAD = 0x4000
TILE_EMPTY, TILE_STAIRS_DOWN = 0, 3
MON_COUNT, MON_SIZE, MON_TYPE, MON_COL, MON_ROW = 16, 8, 0, 2, 3

_, DATA = tiles_dhgr.load_data()
FAIL = []
GOLDEN = GAME / 'tests/dhgr_screens.txt'   # sha1 of each checkpoint's virtual screen
SCREENS = []                               # (tag, sha1 of names + sprite table)


def check(cond, what):
    if not cond:
        FAIL.append(what)
        print('FAIL:', what)
    return cond


def screen_steps():
    """Soft switches, the virtual screen, both banks of page 1 (RAMRD aux for
    the second dump, main again before the CPU runs)."""
    return ['peek:C018:8', 'peek:1800:896', 'peek:2000:8192',
            'poke:C003:0', 'peek:2000:8192', 'poke:C002:0']


def decode_screen(out):
    """(switches, names, sat, main, aux) from the output of screen_steps()."""
    lines = re.findall(r'(?m)^([0-9A-F]{4}): ((?:[0-9A-F]{2} ?)+)$', out)
    blocks, cur, last = [], None, None
    for addr, hexes in lines:
        a = int(addr, 16)
        b = bytes.fromhex(hexes)
        if cur is None or a != last:
            cur = [a, bytearray()]
            blocks.append(cur)
        cur[1] += b
        last = a + len(b)
    sw = next(bytes(b) for a, b in blocks if a == 0xC018)
    vram = next(bytes(b) for a, b in blocks if a == 0x1800)
    pages = [bytes(b) for a, b in blocks if a == 0x2000]
    return sw, vram[:768], vram[768:896], pages[-2], pages[-1]


def model_pages(names, sat):
    px = tiles_dhgr.render(names, sat, DATA)
    main, aux = apple2img.dhgr_from_colors(px)
    return bytes(main), bytes(aux), px


def oracle(out, tag, shots=None):
    """Compare the screen with the model of its virtual screen."""
    sw, names, sat, main, aux = decode_screen(out)
    ok = check(sw[0] < 0x80 and sw[2] < 0x80 and sw[3] < 0x80 and sw[4] < 0x80
               and sw[5] >= 0x80 and sw[7] >= 0x80,
               f'{tag}: switches 80STORE/TEXT/MIXED/PAGE2/HIRES/80COL = {sw.hex()}')
    SCREENS.append((tag, hashlib.sha1(names + sat).hexdigest()))
    emain, eaux, px = model_pages(names, sat)
    for bank, got, exp in (('main', main, emain), ('aux', aux, eaux)):
        if got != exp:
            first = next(i for i in range(8192) if got[i] != exp[i])
            n = sum(1 for i in range(8192) if got[i] != exp[i])
            ok = check(False, f'{tag}: {bank} bank differs from the model at '
                       f'${0x2000 + first:04X} ({n} bytes)')
    if shots:
        rgb = apple2img.dhgr_to_rgb(main, aux)
        apple2img.png_write(Path(shots) / f'dhgr_{tag}.png', rgb, scale=(4, 2))
        if not ok:
            apple2img.png_write(Path(shots) / f'dhgr_{tag}_model.png',
                                apple2img.dhgr_to_rgb(emain, eaux), scale=(4, 2))
    return ok, names, sat, main, aux


def text_rows(names, first=20, last=23):
    return [bytes(c if 32 <= c < 127 else 32 for c in names[32 * r:32 * r + 32]).decode()
            for r in range(first, last + 1)]


STORE = re.compile(r'^store ([0-9A-F]{4}) ([0-9A-F]{4}) \S+ A=([0-9A-F]{2}) X=[0-9A-F]{2} '
                   r'Y=[0-9A-F]{2} S=[0-9A-F]{2} P=([0-9A-F]{2}) LC=\d\d\d(\d)(\d)')


def write_once(out, main, aux, tag):
    """storewatch lines of one update: every (bank, address) of page 1 once,
    with the value the page ends with, RAMRD off; aux stores with IRQs
    masked (the core keeps them masked anyway)."""
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


def test_iie(shots):
    L = a2test.labels(LBL)
    wk = L['wait_key'] + 3            # @wk: LDA KBD (after JSR vid_idle)
    got_key = wk + 5                  # STA KBDSTRB: a key was there
    rng = random.Random(1983)
    stats = {'checks': 0, 'moves': 0, 'turns': [], 'flash': 0, 'slow': []}
    with tempfile.TemporaryDirectory(prefix='rogue-dhgr-') as work:
        disk = a2test.build_disk(work, 'ROGUE.DHGR', BIN, load=LOAD)
        with a2test.Session(disk, iie=True, timeout=300) as s:
            def wait_turn(tag):
                r = s.step(f'until:{wk:04X}:900')
                return check('PC=' in r.out and f'PC={wk:04X}' in r.out, f'{tag}: key wait reached')

            def peek(name, n=1):
                return s.step(L.peek(name, n)).dumps[0]

            def checkpoint(tag):
                out = ''.join(s.step(st).out for st in screen_steps())
                stats['checks'] += 1
                return oracle(out, tag, shots)

            def play(key, tag, watch=False):
                s.step(f'press:{key}')
                r1 = s.step(f'until:{got_key:04X}:300')
                c0 = cycles_of(r1.out)
                if watch:
                    s.step('storewatch:2000:3FFF')
                r2 = s.step(f'until:{wk:04X}:900')
                if watch:
                    s.step('unstorewatch')
                    stats['watched'] = r2.out
                ok = check(f'PC={wk:04X}' in r2.out, f'{tag}: back at the key wait after {key!r}')
                if ok and c0:
                    stats['turns'].append(cycles_of(r2.out) - c0)
                    stats['slow'].append((cycles_of(r2.out) - c0, tag, key))
                return ok

            # boot -> title (its own key loop) -> briefing -> game
            s.step(f'until:{L["wait_kb_choice"]:04X}:3000')
            s.step(f'until:{L["vid_idle"] + 7:04X}:600')     # the title drawn
            ok, names, *_ = checkpoint('title')
            check(any('ROGUE' in t for t in text_rows(names, 0, 23)), 'title text in the names')
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
            ok, names, sat, main, aux = checkpoint('dungeon1')
            hud = text_rows(names)
            check('DEPTH' in hud[0] and 'HP' in ''.join(hud), f'HUD text: {hud}')
            check(any(main) or any(aux), 'something drawn')

            # full redraw cost + the red flash (sprite 0 = the player)
            r = s.step(f'call:{L["dg_dirty_all"]:04X}:5')
            r = s.step(f'call:{L["vid_idle"]:04X}:200')
            stats['full'] = elapsed(r.out)
            s.step(f'call:{L["dg_dirty_all"]:04X}:5')
            s.step('storewatch:2000:3FFF')
            stores = s.step(f'call:{L["vid_idle"]:04X}:400').out
            s.step('unstorewatch')
            ok, names, sat, before_m, before_a = checkpoint('redrawn')
            check(before_m == main and before_a == aux, 'full redraw = same picture')
            check(len(write_once(stores, before_m, before_a, 'full redraw')) == 2 * 7680,
                  'full redraw: every screen byte of the picture stored once')
            colour = sat[3]
            s.step(f'poke:1B03:08')
            s.step(f'poke:{L["dg_satd"]:04X}:01')
            r = s.step(f'call:{L["vid_idle"]:04X}:50')
            stats['flash'] = elapsed(r.out)
            ok, names, sat, fm, fa = checkpoint('flash')
            check(sat[3] == 8 and (fm != before_m or fa != before_a), 'flash: the player turned red')
            s.step(f'poke:1B03:{colour:02X}')
            s.step(f'poke:{L["dg_satd"]:04X}:01')
            s.step(f'call:{L["vid_idle"]:04X}:50')
            ok, names, sat, am, aa = checkpoint('unflash')
            check(am == before_m and aa == before_a, 'flash: page restored byte for byte')

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
                        if not play(k, tag, watch=watch):
                            break
                        if peek('player_col', 2) == where:
                            checkpoint(f'{tag}_bump')   # a wall or a monster
                    if watch:           # the first move from 5 on that draws
                        ok, names, sat, wm, wa = checkpoint(f'{tag}_watched')
                        n = len(write_once(stats.pop('watched', ''), wm, wa, f'{tag} (write-once)'))
                        stats['watched_ok'] = n > 0
                stats['moves'] += 1
                sat = peek('dg_drawn', 4) if 'dg_drawn' in L else b''
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
            # random virtual screens: every character, sprites anywhere
            for k in range(3):
                vram = [rng.randrange(256) for _ in range(768)]
                for e in range(32):
                    y = rng.choice((rng.randrange(192), rng.randrange(176, 256)))
                    vram += [0xD1 if y == 0xD0 else y, rng.randrange(253),
                             4 * rng.randrange(20), rng.randrange(16)]
                if k:
                    vram[768 + 4 * rng.randrange(8, 32)] = 0xD0
                for a, v in enumerate(vram):
                    s.step(f'poke:{0x1800 + a:04X}:{v:02X}')
                for row in range(24):
                    s.step(f'poke:{L["dg_touch"] + row:04X}:01')
                s.step(f'poke:{L["dg_satd"]:04X}:01')
                s.step('storewatch:2000:3FFF')
                stores = s.step(f'call:{L["vid_idle"]:04X}:400').out
                s.step('unstorewatch')
                ok, names, sat, rm, ra = checkpoint(f'random{k}')
                write_once(stores, rm, ra, f'random{k}')
            stats['seen_hurt'] = seen_hurt
            # ESC, Y: DHGR off, 40-column text, the DOS prompt
            s.step('key:\x1b')
            s.step('wait:30')
            s.step('key:Y')
            s.step('wait:120')
            sw = s.step('peek:C018:8').dumps[0]
            check(sw[2] >= 0x80 and sw[7] < 0x80 and sw[0] < 0x80,
                  f'quit: text, 40 columns, 80STORE off ({sw.hex()})')
    return stats


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
        disk = a2test.build_disk(work, 'ROGUE.DHGR', BIN, load=LOAD)
        steps = [f'until:{L["wait_kb_choice"]:04X}:3000', 'wait:30', 'key: ', 'wait:200',
                 'key: ', f'until:{wk:04X}:900']
        for k in 'LLKKJJII.':
            steps += [f'press:{k}', 'wait:2', f'until:{wk:04X}:900']
        steps += screen_steps()
        r = a2test.subprocess.run([str(a2test.A2SHOT), '--iic', '--disk', str(disk)] + steps,
                                  capture_output=True, text=True, timeout=300)
        check(r.returncode == 0, f'//c run: exit {r.returncode} {r.stderr[-300:]}')
        if r.returncode:
            return 0
        check(r.stdout.count(f'PC={wk:04X}') == 10, '//c: every move back at the key wait')
        ok, names, *_ = oracle(r.stdout, 'iic', shots)
        check('DEPTH' in text_rows(names)[0], '//c HUD')
        return 1


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
    got = [tuple(l.split()) for l in lines]
    bad = [w[0] for w, g in zip(want, got) if w != g]
    check(len(want) == len(got) and not bad,
          f'{GOLDEN.name}: {len(got)} screens, {len(want)} expected, different: {bad[:5]}')
    if not bad and len(want) == len(got):
        print(f'{GOLDEN.name}: the {len(got)} checkpoint screens unchanged')


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
    turns = st['turns']
    print(f'//e: {st["moves"]} moves, {st["checks"]} screens = model; '
          f'full redraw {st["full"]} cycles, sprite recolour {st["flash"]} cycles, '
          f'turn (key -> key wait) median {sorted(turns)[len(turns) // 2] if turns else 0} '
          f'max {max(turns) if turns else 0} cycles over {len(turns)} turns')
    print('slowest turns (cycles, move, key):', sorted(st['slow'], reverse=True)[:4])
    golden(args.golden)
    test_iic(args.shots)
    if FAIL:
        print(f'{len(FAIL)} failure(s)')
        sys.exit(1)
    print('ROGUE.DHGR: all checks passed (//e + //c)')


if __name__ == '__main__':
    main()
