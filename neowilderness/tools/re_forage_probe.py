#!/usr/bin/env python3
"""Hunting, fishing, foraging, meals and skinning of the original (lot 4).

Part 1 runs the Journey modules alone on the Apple II ROM, each copied to
$5800 over a pristine copy of the saved first-journey state (build/game.bin,
reset before every case), with RND ($0321) replaced by a table of imposed
values that also counts the draws, and the message, input, time-engine and
chain entries of the core stubbed:

  T0F/S07  CATCH/GET, KILL/ATTACK, SCARE, CUT on GAME/FISH/animals
  T12/S00  EAT and COOK of provisions and wild foods (INSECTS..PLANTS, NUTS)
  T11/S07  SKIN, EAT and COOK of game (animals 76-79, GAME, FISH)
  T12/S08  TASTE/SAMPLE (selector 35)
  T0D/S00  materialization of the discoveries (quantities, quality codes)
  T06/S04  the kill branch of an animal ($593A)

Part 2 plays the real game (build/SIERRA.woz + build/JOURNEY.dsk) with RAM
pokes and, for a few commands, RND forced to a constant: what the inventory
transaction does with the quantities (ground, pack), packing wild food,
cooking from the pack, the spoilage clock, a bear killed with the gun.

No original byte enters the repository: modules and disks stay in build/,
results go to build/re_forage/results.json (numbers quoted in docs/FORAGE.md).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE / 'tests'))
import a2test                       # noqa: E402
import smalldos                     # noqa: E402
from gendata import fp as encode   # noqa: E402
from re_surv_fp import fp           # noqa: E402

OUT = HERE / 'build/re_forage'

# Item tables of the original (docs/logic/state.md): first set (items 1-75)
B1, B2, B3, B4 = 0x404C, 0x4098, 0x40E4, 0x4130
W5, W7, W8, W9, W10, W11 = 0x417C, 0x42AC, 0x4344, 0x43DC, 0x4474, 0x450C
# second set (k = noun - 75: 1-4 animals, 5 GAME, 6 FISH, 7 INSECTS ... 11 PLANTS)
b1, b2, b3, b4 = 0x45C0, 0x45DC, 0x45F8, 0x4614
w5, w7, w8, w9, w10, w11 = 0x4630, 0x46A0, 0x46D8, 0x4710, 0x4748, 0x4780
A1 = lambda i: 0x4950 + 5 * (i - 1)                       # noqa: E731
A2 = lambda i: 0x49CD + 5 * (i - 1)                       # noqa: E731

MODULES = {  # name: (track, sector, sectors, page where the image is kept)
    't0fs07': (0x0F, 7, 6, 0x70), 't12s08': (0x12, 8, 6, 0x76),
    't12s00': (0x12, 0, 8, 0x30), 't11s07': (0x11, 7, 8, 0x38),
    't0ds00': (0x0D, 0, 7, 0x80), 't06s04': (0x06, 4, 6, 0x88),
}


def w(v):
    return [v & 255, (v >> 8) & 255]


def asm(org, code):
    return org, bytes.fromhex(code)


# Driver: $0800 reset (pristine state), stop A at $0803 (case pokes), $0806
# run (module copied to $5800, JMP (entry)), stop B at $0809 (peeks).
DRIVER = [
    asm(0x0800, '20 30 08  EA EA EA  20 A0 08  4C 00 08'),
    asm(0x0830, 'A9 00 85 3C 85 3E'
                ' A9 20 85 3D A9 40 85 3F A2 0D 20 80 08'     # $2000 -> $4000, 13 pages
                ' A9 2D 85 3D A9 60 85 3F A2 01 20 80 08'     # $2D00 -> $6000 (TOPO header)
                ' A9 2E 85 3D A9 0D 85 3F A2 01 20 80 08'     # $2E00 -> $0D00 (SURV3D flags)
                ' 60'),
    asm(0x0880, 'A0 00 B1 3C 91 3E C8 D0 F9 E6 3D E6 3F CA D0 F2 60'),
    asm(0x08A0, 'A9 00 85 3C 85 3E AD F4 09 85 3D A9 58 85 3F AE F5 09 20 80 08'
                ' A9 F0 85 36 A9 FD 85 37 BA 8E F0 09 6C F2 09'),
    asm(0x0A00, '8C 1F 09 AC 10 09 8A 99 11 09 EE 10 09 AC 1F 09 60'),   # log X
    asm(0x0A18, 'AE F0 09 9A 60'),                                       # back to stop B
    asm(0x0A20, '8E 00 09 20 00 0A 4C 18 0A'),                          # $4D21 final message
    asm(0x0A30, '85 0E 84 0F 4C 00 0A'),                                # $4D24
    asm(0x0A38, '84 0F 4C 00 0A'),                                      # $4D27
    asm(0x0A40, 'A9 01 8D 08 09 4C 18 0A'),                             # $4D00 time engine
    asm(0x0A48, 'A9 03 8D 08 09 4C 18 0A'),                             # $4D03
    asm(0x0A50, 'A9 09 8D 08 09 4C 18 0A'),                             # $4D09
    asm(0x0A58, '8D 09 09 8E 0A 09 8C 0B 09 A9 DB 8D 08 09 4C 18 0A'),  # $03DB chain
    asm(0x0A6A, 'AC 04 09 AD 05 09 84 0E 85 0F 60'),                    # $4D30 number
    asm(0x0A76, 'AD 02 09 60'),                                         # $4D39 key choice
    asm(0x0A7A, '60'),                                                  # $4D2D input line
    asm(0x0A7C, 'A9 FE 8D 00 09 4C 18 0A'),                             # $B000 parser
    asm(0x0A84, 'AE 40 09 86 97 BD 40 09 9D FF 01 CA D0 F7 60'),        # $4D33 hours text
    asm(0x0AA0, '8C E8 09 8E E9 09 AD E0 09 AC E1 09 20 F9 EA 18 AD E0 09 69 05 8D E0 09'
                ' 90 03 EE E1 09 EE E2 09 AC E8 09 AE E9 09 60'),       # RND from a table (X, Y kept)
]
STUBS = {0x4D00: 0x0A40, 0x4D03: 0x0A48, 0x4D09: 0x0A50, 0x4D21: 0x0A20, 0x4D24: 0x0A30,
         0x4D27: 0x0A38, 0x4D2A: 0x0A00, 0x4D2D: 0x0A7A, 0x4D30: 0x0A6A, 0x4D33: 0x0A84,
         0x4D39: 0x0A76}
RUNTIME = {0x0321: 0x0AA0, 0x03DB: 0x0A58, 0xB000: 0x0A7C}   # poked once DOS is done
LOG, YES, NUM, MARK, HOURS, RNDP, TABLE = 0x0910, 0x0902, 0x0904, 0x0908, 0x0940, 0x09E0, 0x0C00


def poke(addr, data):
    return [f'poke:{addr + i:04X}:{v:02X}' for i, v in enumerate(data)]


def build_disk():
    journey = smalldos.Disk((HERE / 'build/JOURNEY.dsk').read_bytes())
    journey.flip = True
    game = (HERE / 'build/game.bin').read_bytes()
    state = bytearray(game[0x4000:0x8000])
    for entry, target in STUBS.items():
        state[entry - 0x4000:entry - 0x4000 + 3] = bytes((0x4C, target & 255, target >> 8))
    pristine = game[0x4000:0x4D00] + game[0x6000:0x6100] + game[0x0D00:0x0E00]
    driver = bytearray(0x300)
    for org, code in DRIVER:
        driver[org - 0x800:org - 0x800 + len(code)] = code
    OUT.mkdir(parents=True, exist_ok=True)
    files = {'STATE': (state, 0x4000), 'PRISTINE': (pristine, 0x2000), 'DRIVER': (driver, 0x0800)}
    m1 = journey.run(0x0F, 7, 6) + journey.run(0x12, 8, 6)                    # $7000
    m2 = journey.run(0x12, 0, 8) + journey.run(0x11, 7, 8)                    # $3000
    m3 = journey.run(0x0D, 0, 7).ljust(0x800, b'\0') + journey.run(0x06, 4, 6)  # $8000
    files.update(M1=(m1, 0x7000), M2=(m2, 0x3000), M3=(m3, 0x8000))
    args = []
    for name, (data, org) in files.items():
        (OUT / f'{name.lower()}.bin').write_bytes(data)
        args += ['--bin', f'{name}={OUT / (name.lower() + ".bin")}@{org:#x}']
    hello = ''.join(f'{10 * (i + 1)} PRINT CHR$(4);"BLOAD {n}"\n'
                    for i, n in enumerate(('STATE', 'PRISTINE', 'M1', 'M2', 'M3')))
    hello += '90 PRINT CHR$(4);"BRUN DRIVER"\n'
    (OUT / 'hello.bas').write_text(hello)
    disk = OUT / 'forage.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'), '--out', str(disk),
                    '--bas', f'HELLO={OUT / "hello.bas"}'] + args, check=True, capture_output=True)
    return disk, game


# ---------------------------------------------------------------------------
# Cases. zp: page-zero bytes; pokes: (addr, bytes); rnd: imposed draws.
def case(name, module, entry, zp, pokes=(), rnd=(), num=0, yes=0, hours='', **info):
    return dict(name=name, module=module, entry=entry, zp=zp, pokes=list(pokes), rnd=list(rnd),
                num=num, yes=yes, hours=hours, info=info)


def hunt_cases(lat=38):
    c = []
    kill = dict(zip((3, 5, 6), (17, 80, 11)))
    gun = [(B2 + 57, [1])]
    game_here = [(b2 + 5, [0])]
    fish_here = [(b2 + 6, [0])]
    # KILL GAME, five means; p = .1 x (means - 18), zero in the dark ($0D5D = 0)
    for means, pk, p in ((21, gun, .3), (20, [(b2 + 14, [1])], .2), (19, [(b2 + 15, [1])], .1),
                         (18, [(B2 + 58, [1])], 0), (17, [(b2 + 16, [1])], -.1)):
        for r in ((p - .0001, p + .0001) if p > 0 else (0.0,)):
            c.append(case(f'kill game means {means} rnd {r:.4f}', 't0fs07', 0x5800, kill,
                          game_here + pk, [r, .5], means=means, p=p, r=r))
    c.append(case('kill game gun dark', 't0fs07', 0x5800, kill, game_here + gun + [(0x0D5D, [0])],
                  [.0001], means=21, p=0, r=.0001))
    c.append(case('kill game no weapon', 't0fs07', 0x5800, kill, game_here, []))
    c.append(case('cut game gun', 't0fs07', 0x5800, {**kill, 3: 31}, game_here + gun, []))
    c.append(case('cut game knife', 't0fs07', 0x5800, {**kill, 3: 31}, game_here + [(B2 + 59, [1])],
                  [0.0]))
    c.append(case('scare game', 't0fs07', 0x5800, {**kill, 3: 18}, game_here, []))
    # quantity 4 + INT(64 RND)
    for q in (0.0, .999):
        c.append(case(f'kill game quantity rnd {q}', 't0fs07', 0x5800, kill, game_here + gun, [.1, q], q=q))
    # FISH quality: p0 = .05 - .001 |lat|
    p0 = .05 - .001 * abs(lat)
    for r3 in (.9501, .9499, p0 - .0001, p0 + .0001, 5 * p0 - .0002, 5 * p0 + .0002):
        c.append(case(f'kill fish quality {r3:.4f}', 't0fs07', 0x5800, {**kill, 5: 81},
                      fish_here + gun, [.1, .5, r3], r3=r3, p0=p0))
    # SCARE BEAR: noise threshold .8 - .03 x record[14]
    c.append(case('scare bear success', 't0fs07', 0x5800, {**kill, 3: 18, 5: 76}, [(b2 + 1, [0])], [.4999]))
    c.append(case('scare bear fail', 't0fs07', 0x5800, {**kill, 3: 18, 5: 76}, [(b2 + 1, [0])], [.5001]))
    c.append(case('kill bear gun', 't0fs07', 0x5800, {**kill, 5: 76}, [(b2 + 1, [0])] + gun, []))
    # CATCH with TRAP (72) / FISHNG GEAR (67): p = minutes x .0007 / .008
    catch = {3: 1, 5: 80, 6: 11}
    c.append(case('catch game no trap', 't0fs07', 0x5800, catch, game_here, []))
    for hours, minutes in (('2', 120), ('.5', 30)):
        p = minutes * .0007
        for r in (p - .0001, p + .0001):
            c.append(case(f'catch game {hours} h rnd {r:.4f}', 't0fs07', 0x5800, catch,
                          game_here + [(B2 + 72, [1])], [r, .5], hours=hours, minutes=minutes, p=p, r=r))
    for hours, minutes in (('1', 60),):
        p = minutes * .008
        for r in (p - .0001, p + .0001):
            c.append(case(f'catch fish {hours} h rnd {r:.4f}', 't0fs07', 0x5800, {**catch, 5: 81},
                          fish_here + [(B2 + 67, [1])], [r, .5, .5], hours=hours, minutes=minutes, p=p, r=r))
    c.append(case('catch fish no gear', 't0fs07', 0x5800, {**catch, 5: 81}, fish_here, []))
    # GET / KILL on absent, killed, packed
    c.append(case('get bear present', 't0fs07', 0x5800, {**catch, 5: 76}, [(b2 + 1, [0])], []))
    c.append(case('get game killed', 't0fs07', 0x5800, catch, [(b2 + 5, [1])], []))
    c.append(case('get game absent', 't0fs07', 0x5800, catch, [], []))
    c.append(case('get game packed', 't0fs07', 0x5800, catch, [(b1 + 5, [2])], []))
    c.append(case('kill game killed', 't0fs07', 0x5800, kill, [(b2 + 5, [1])], []))
    c.append(case('kill game absent', 't0fs07', 0x5800, kill, [], []))
    return c


def ground(k, oz, spoil, n=None, taste=0, code=0, pct=0):
    """Wild food k (7-11) or game k (5, 6) on the ground: quantity, spoil, record n - 17."""
    p = [(b1 + k, [0]), (w5 + 2 * k, w(oz)), (w7 + 2 * k, w(oz)), (w8 + 2 * k, w(0))]
    p.append(((w10 + 2 * (k + 15)) if k >= 7 else (w11 + 2 * (k + 21)), w(spoil)))
    if n is not None:
        i = n - 17
        p += [(W9 + 2 * i, w(taste)), (W10 + 2 * i, w(code)), (W11 + 2 * i, w(pct))]
    return p


def meal_cases():
    c = []
    eat = {3: 12, 6: 3}
    cook = {3: 11, 6: 3}
    stove = [(B2 + 71, [1])]
    # EAT, toxicity: code 1/2 p = pct/100; code 3 p x (1 - |lat|/64); spoiled: .5
    for label, k, n, code, pct, p in (('mushrooms', 10, 85, 2, 80, .8), ('insects', 7, 82, 1, 80, .8),
                                       ('fruit white', 8, 83, 3, 30, .3 * (1 - 38 / 64))):
        for r in (p - .0001, p + .0001):
            c.append(case(f'eat {label} rnd {r:.4f}', 't12s00', 0x5800, {**eat, 5: n},
                          ground(k, 20, 50, n, 0, code, pct), [r], num=4, k=k, n=n, code=code, pct=pct, p=p, r=r))
    c.append(case('eat fruit white lat 0', 't12s00', 0x5800, {**eat, 5: 83},
                  ground(8, 20, 50, 83, 0, 3, 30) + [(0x60A8, [0])], [.2999], num=4, p=.3))
    c.append(case('eat fruit white lat -64', 't12s00', 0x5800, {**eat, 5: 83},
                  ground(8, 20, 50, 83, 0, 3, 30) + [(0x60A8, [256 - 64])], [.0001], num=4, p=0))
    for r in (.4999, .5001):
        c.append(case(f'eat spoiled mushrooms rnd {r}', 't12s00', 0x5800, {**eat, 5: 85},
                      ground(10, 20, 0, 85, 0, 0, 0), [r], num=4, r=r))
    c.append(case('eat safe plants', 't12s00', 0x5800, {**eat, 5: 86}, ground(11, 20, 50, 86, 0, 0, 0), [],
                  num=10))
    nuts = [(B1 + 23, [0]), (W5 + 46, w(10)), (W7 + 46, w(10)), (W8 + 46, w(0)), (W11 + 46, w(720)),
            (W9 + 140, w(1)), (W10 + 140, w(1)), (W11 + 140, w(80))]
    c.append(case('eat nuts code 1', 't12s00', 0x5800, {**eat, 5: 23}, nuts, [.8001], num=2))
    c.append(case('eat cheese pack', 't12s00', 0x5800, {**eat, 5: 28}, [], [], num=8, yes=0))
    c.append(case('eat cheese pack spoiled', 't12s00', 0x5800, {**eat, 5: 28}, [(W11 + 56, w(0))],
                  [.5001], num=8, yes=0))
    c.append(case('eat bologna ground', 't12s00', 0x5800, {**eat, 5: 33}, [], [], num=4, yes=1))
    c.append(case('eat 49 oz', 't12s00', 0x5800, {**eat, 5: 28}, [], [], num=49, yes=0))
    c.append(case('eat 0 oz', 't12s00', 0x5800, {**eat, 5: 28}, [], [], num=0))
    c.append(case('eat more than available', 't12s00', 0x5800, {**eat, 5: 85},
                  ground(10, 20, 50, 85), [], num=30))
    c.append(case('eat starving', 't12s00', 0x5800, {**eat, 5: 28}, [(0x48A9, [90])], [], num=8, yes=0))
    # COOK: fire or stove; cooked when minutes > 15 + INT(.6 oz); detox .75 (NUTS) .85 (code 1) .2 (2, 3)
    c.append(case('cook no fire', 't12s00', 0x5800, {**cook, 5: 85}, ground(10, 20, 50, 85, 0, 2, 80), []))
    for hours, cooked in (('.37', True), ('.35', False)):
        for r in ((.1999, .2001) if cooked else (None,)):
            c.append(case(f'cook mushrooms {hours} h rnd {r}', 't12s00', 0x5800, {**cook, 5: 85},
                          ground(10, 20, 50, 85, 0, 2, 80) + stove, [r] if r is not None else [],
                          num=10, hours=hours, cooked=cooked, r=r))
    for r in (.8499, .8501):
        c.append(case(f'cook insects rnd {r}', 't12s00', 0x5800, {**cook, 5: 82},
                      ground(7, 20, 50, 82, 1, 1, 80) + [(0x45CD, [0])], [r], num=10, hours='1', r=r))
    for r in (.7499, .7501):
        c.append(case(f'cook nuts rnd {r}', 't12s00', 0x5800, {**cook, 5: 23}, nuts + stove, [r],
                      num=5, hours='1', r=r))
    c.append(case('cook cheese ground', 't12s00', 0x5800, {**cook, 5: 28}, stove, [], num=10, yes=1,
                  hours='1'))
    c.append(case('cook 289 oz', 't12s00', 0x5800, {**cook, 5: 85}, ground(10, 400, 50, 85) + stove, [],
                  num=289))
    c.append(case('cook 288 oz', 't12s00', 0x5800, {**cook, 5: 85}, ground(10, 400, 50, 85) + stove, [],
                  num=288, hours='4'))
    return c


def game_cases():
    c = []
    killed = lambda k, oz: [(0x4AE0 + k - 1, [1]), (b2 + k, [1]), (b1 + k, [0]),    # noqa: E731
                            (w5 + 2 * k, w(oz)), (w7 + 2 * k, w(oz)), (w8 + 2 * k, w(0))]
    skin = {3: 4, 6: 11}
    for label, k, extra in (('bear', 1, []), ('bear knife', 1, [(B2 + 59, [1])]),
                            ('bear dark', 1, [(0x0D5D, [0])]), ('bear dark knife', 1, [(0x0D5D, [0]), (B2 + 59, [1])]),
                            ('cougar', 2, []), ('rattlesnake', 3, []), ('game', 5, [])):
        c.append(case(f'skin {label}', 't11s07', 0x5800, {**skin, 5: 75 + k}, killed(k, 2000) + extra, [],
                      k=k))
    c.append(case('skin fish', 't11s07', 0x5800, {**skin, 5: 81}, killed(6, 100), []))
    c.append(case('skin bear alive', 't11s07', 0x5800, {**skin, 5: 76}, [(b2 + 1, [0])], []))
    c.append(case('skin bear skinned', 't11s07', 0x5800, {**skin, 5: 76}, [(b2 + 1, [1])], []))
    c.append(case('skin bear 72 oz', 't11s07', 0x5800, {**skin, 5: 76}, killed(1, 72), []))
    c.append(case('skin bear 73 oz', 't11s07', 0x5800, {**skin, 5: 76}, killed(1, 73), []))
    eat, cook = {3: 12, 6: 11}, {3: 11, 6: 11}
    c.append(case('eat game', 't11s07', 0x5800, {**eat, 5: 80}, killed(5, 36) + [(w11 + 52, w(29))], [],
                  num=4))
    c.append(case('eat game spoiled', 't11s07', 0x5800, {**eat, 5: 80}, killed(5, 36) + [(w11 + 52, w(0))],
                  [.5001], num=4))
    c.append(case('eat bear meat', 't11s07', 0x5800, {**eat, 5: 76}, killed(1, 2340) + [(w11 + 44, w(29))],
                  [], num=10))
    p = .15 * (1 - 38 / 64)
    for r in (p - .0001, p + .0001):
        c.append(case(f'eat fish code 3 rnd {r:.4f}', 't11s07', 0x5800, {**eat, 5: 81},
                      killed(6, 30) + [(w11 + 54, w(9)), (W10 + 128, w(3)), (W11 + 128, w(15))], [r], num=4,
                      p=p, r=r))
    c.append(case('eat bear alive', 't11s07', 0x5800, {**eat, 5: 76}, [(b2 + 1, [0])], [], num=4))
    c.append(case('eat game 49', 't11s07', 0x5800, {**eat, 5: 80}, killed(5, 100), [], num=49))
    c.append(case('cook game no fire', 't11s07', 0x5800, {**cook, 5: 80}, killed(5, 36), [], num=10))
    c.append(case('cook game', 't11s07', 0x5800, {**cook, 5: 80}, killed(5, 36) + [(0x45CD, [0])], [],
                  num=10, hours='.37'))
    for r in (.2999, .3001):
        c.append(case(f'cook fish rnd {r}', 't11s07', 0x5800, {**cook, 5: 81},
                      killed(6, 30) + [(0x45CD, [0]), (W10 + 128, w(3)), (W11 + 128, w(15))], [r], num=10,
                      hours='.37', r=r))
    c.append(case('cook game 849', 't11s07', 0x5800, {**cook, 5: 80}, killed(5, 1000) + [(0x45CD, [0])],
                  [], num=849))
    c.append(case('cook game 848', 't11s07', 0x5800, {**cook, 5: 80}, killed(5, 1000) + [(0x45CD, [0])],
                  [], num=848, hours='9'))
    return c


def taste_cases():
    c = []
    t = {3: 35, 0x1E: 35}
    for taste in range(10):
        c.append(case(f'taste plants code {taste}', 't12s08', 0x5800, {**t, 5: 86, 6: 3},
                      ground(11, 20, 50, 86, taste, 0, 0), [], taste=taste))
    c.append(case('taste plants spoiled', 't12s08', 0x5800, {**t, 5: 86, 6: 3}, ground(11, 20, 0, 86, 1),
                  []))
    c.append(case('taste plants pack', 't12s08', 0x5800, {**t, 5: 86, 6: 3},
                  [(b1 + 11, [2]), (w5 + 22, w(5)), (w8 + 22, w(5)), (w11 + 22, w(9)), (b4 + 11, [7])], []))
    c.append(case('taste cheese', 't12s08', 0x5800, {**t, 5: 28, 6: 3}, [], [], yes=0))
    c.append(case('taste game', 't12s08', 0x5800, {**t, 5: 80, 6: 11},
                  [(b1 + 5, [0]), (w5 + 10, w(10)), (w7 + 10, w(10)), (w11 + 52, w(20))], []))
    c.append(case('taste bear absent', 't12s08', 0x5800, {**t, 5: 76, 6: 11}, [], []))
    c.append(case('taste food', 't12s08', 0x5800, {**t, 5: 135, 6: 13}, [], []))
    return c


def discovery_cases():
    """T0D/S00 $585F: events $0D90 + x, x = $0D GAME .. $14 NUTS."""
    c = []
    for x, label, seqs in ((0x0F, 'insects', ([.5, .0999], [.5, .1001])),
                           (0x10, 'fruit', ([.5, .1999], [.5, .2001, .3499], [.5, .4999, .3501], [.5, .5001])),
                           (0x11, 'cacti', ([.5, .0999], [.5, .1001])),
                           (0x12, 'mushrooms', ([.5, .2999], [.5, .3001])),
                           (0x13, 'plants', ([.5, .0999], [.5, .1999], [.5, .2999], [.5, .4999], [.5, .5001])),
                           (0x14, 'nuts', ([0.0, .0999], [.999, .1001])),
                           (0x0D, 'game', ([],)), (0x0E, 'fish', ([],))):
        for seq in seqs:
            c.append(case(f'discover {label} {seq}', 't0ds00', 0x585F, {},
                          [(0x0D90 + x, [1])], seq + [.5] * 3, x=x, seq=seq))
    c.append(case('discover fruit ripe (season 70)', 't0ds00', 0x585F, {}, [(0x0DA0, [1]), (0x4ADA, [70])],
                  [.5, .3, .2, .5], x=0x10))
    return c


def animal_kill_cases():
    """T06/S04 $593A: success .01 x record[means + 6] / (2 - light)."""
    c = []
    for light, r, ok in ((1, .3499, True), (1, .3501, False), (0, .1749, True)):
        zp = {4: 21, 5: 76, 0x15: 1, 0x19: 2 - light, 0x18: 1, 0x14: 0}
        c.append(case(f'kill bear gun light {light} rnd {r}', 't06s04', 0x593A, zp,
                      [(0x0D5D, [light]), (b2 + 1, [0])], [r, .5, .5, .5], light=light, r=r, ok=ok))
    for k, zp5 in ((2, 77), (3, 78)):
        zp = {4: 21, 5: zp5, 0x15: k, 0x19: 1, 0x18: 1, 0x14: 0}
        c.append(case(f'kill animal {k} gun', 't06s04', 0x593A, zp, [(b2 + k, [0])], [0.0], k=k))
    return c


PAGES = {'t0fs07': (0x70, 6), 't12s08': (0x76, 6), 't12s00': (0x30, 8), 't11s07': (0x38, 8),
         't0ds00': (0x80, 7), 't06s04': (0x88, 6)}


def isolated():
    disk, game = build_disk()
    cases = hunt_cases() + meal_cases() + game_cases() + taste_cases() + discovery_cases() + animal_kill_cases()
    steps = ['until:0800:40000']          # the boot sector runs $0801-$08FF, never $0800
    for addr, target in RUNTIME.items():
        steps += poke(addr, [0x4C, target & 255, target >> 8])
    for c in cases:
        steps.append('until:0803:40000')
        page, count = PAGES[c['module']]
        steps += poke(0x09F2, w(c['entry'])) + poke(0x09F4, [page, count])
        steps += poke(0x0900, [0] * 0x40) + poke(RNDP, [TABLE & 255, TABLE >> 8, 0])
        table = b''.join(encode(r) for r in c['rnd'])
        steps += poke(TABLE, table)
        steps += poke(YES, [c['yes']]) + poke(NUM, w(c['num']))
        h = [0x80 | ord(ch) for ch in c['hours']]
        steps += poke(HOURS, [len(h)] + h)
        for a, v in sorted(c['zp'].items()):
            steps += poke(a, [v])
        for a, v in c['pokes']:
            steps += poke(a, v)
        steps += ['until:0809:400000', 'peek:0900:64', 'peek:09E0:3', 'peek:0000:256', 'peek:4000:3328',
                  'peek:0D80:64', 'peek:5C08:3']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=3600)
    for k, c in enumerate(cases):
        m = r.mem(0x900, 64, k)
        zp = r.mem(0, 256, k)
        st = bytearray(0x4000) + r.mem(0x4000, 3328, k)
        c['log'] = list(m[0x11:0x11 + m[0x10]])
        c['final'] = m[0]
        c['exit'] = {0: None, 1: '$4D00', 3: '$4D03', 9: '$4D09', 0xDB: 'chain'}.get(m[8], m[8])
        if m[8] == 0xDB:
            c['chain'] = dict(sectors=m[9], track=m[10], sector=m[11])
        if m[0] == 0xFE:
            c['exit'] = '$B000'
        c['rnd_calls'] = r.mem(0x09E0, 3, k)[2]
        c['zp'] = {f'{a:02X}': zp[a] for a in (3, 4, 5, 7, 8, 0x0E, 0x0F)}
        c['out'] = decode_state(st, game)
        c['t0f_means'] = r.mem(0x5C08, 3, k)[0] if c['module'] == 't0fs07' else None
    return cases


def word(m, a):
    return int.from_bytes(m[a:a + 2], 'little', signed=True)


def decode_state(m, game):
    """State variables that differ from the pristine saved game, by name."""
    out = {}
    names = {}
    for i in range(1, 76):
        for base, n in ((B1, 'B1'), (B2, 'B2'), (B3, 'B3'), (B4, 'B4')):
            names[base + i] = (f'{n}[{i}]', 1)
        for base, n in ((W5, 'W5'), (W7, 'W7'), (W8, 'W8'), (W9, 'W9'), (W10, 'W10'), (W11, 'W11')):
            names[base + 2 * i] = (f'{n}[{i}]', 2)
    for k in range(1, 28):
        for base, n in ((b1, 'b1'), (b2, 'b2'), (b3, 'b3'), (b4, 'b4')):
            names[base + k] = (f'{n}[{k}]', 1)
        for base, n in ((w5, 'w5'), (w7, 'w7'), (w8, 'w8'), (w9, 'w9'), (w10, 'w10'), (w11, 'w11')):
            names[base + 2 * k] = (f'{n}[{k}]', 2)
    floats = {0x4C20: 'effort $4C20', A1(17): 'A1[17] last meal', A2(17): 'A2[17]', A1(18): 'A1[18] last rest',
              A1(22): 'A1[22] water deficit', A1(23): 'A1[23] food deficit', A1(24): 'A1[24] rest deficit',
              0x4C3E: '$4C3E'}
    words = {0x4BC6: '$4BC6 minutes', 0x4BDC: '$4BDC kcal eaten', 0x4BD2: '$4BD2', 0x4A4A: '$4A4A salt',
             0x4C04: '$4C04 available', 0x4C18: '$4C18 old spoil'}
    bytes_ = {0x4B41: '$4B41', 0x4B42: '$4B42', 0x4B44: '$4B44', 0x4B73: '$4B73', 0x4B83: '$4B83',
              0x4B54: '$4B54', 0x4B82: '$4B82', 0x4B77: '$4B77', 0x4B72: '$4B72',
              0x47E0: 'cond prevented[11]', 0x4B71: '$4B71', 0x4B50: '$4B50 bait'}
    for i in range(6):
        bytes_[0x4AE0 + i] = f'$4AE0[{i}] skinnable k={i + 1}'
    for a in range(0x4000, 0x4D00):
        if m[a] == game[a]:
            continue
        if a in names:
            n, size = names[a]
            out[n] = word(m, a) if size == 2 else m[a]
        elif a - 1 in names and names[a - 1][1] == 2:
            n, _ = names[a - 1]
            out[n] = word(m, a - 1)
    for a, n in floats.items():
        if m[a:a + 5] != game[a:a + 5]:
            out[n] = [round(fp(game[a:a + 5]), 7), round(fp(m[a:a + 5]), 7)]
    for a, n in words.items():
        if m[a:a + 2] != game[a:a + 2]:
            out[n] = [word(game, a), word(m, a)]
    for a, n in bytes_.items():
        if n and m[a] != game[a]:
            out[n] = [game[a], m[a]]
    return out


# ---------------------------------------------------------------------------
# Part 2: the real game.
def rnd_const(o, value):
    """Make $0321 return a constant (12 bytes, restored by rnd_restore)."""
    o.saved_rnd = o.mem()[0x0321:0x032D]
    o.poke(0x0321, bytes.fromhex('A9 28 A0 03 4C F9 EA') + encode(value))


def rnd_restore(o):
    o.poke(0x0321, o.saved_rnd)


def snapshot(m):
    sel = dict(
        game=dict(b1=m[b1 + 5], b2=m[b2 + 5], b3=m[b3 + 5], b4=m[b4 + 5], w5=word(m, w5 + 10), w7=word(m, w7 + 10),
                  w8=word(m, w8 + 10), w11_pack=word(m, w11 + 10), w11_ground=word(m, w11 + 52)),
        bear=dict(b1=m[b1 + 1], b2=m[b2 + 1], w5=word(m, w5 + 2), w7=word(m, w7 + 2), w8=word(m, w8 + 2),
                  w11_pack=word(m, w11 + 2), w11_ground=word(m, w11 + 44)),
        hide=dict(b1=m[b1 + 19], w5=word(m, w5 + 38), w7=word(m, w7 + 38), w8=word(m, w8 + 38)),
        mushrooms=dict(b1=m[b1 + 10], b2=m[b2 + 10], b3=m[b3 + 10], b4=m[b4 + 10], w5=word(m, w5 + 20),
                       w7=word(m, w7 + 20), w8=word(m, w8 + 20), w9_pack_pct=word(m, w9 + 50),
                       w11_pack=word(m, w11 + 20), w10_ground_spoil=word(m, w10 + 50),
                       g_taste=word(m, W9 + 136), g_code=word(m, W10 + 136), g_pct=word(m, W11 + 136)),
        cheese=dict(b1=m[B1 + 28], w5=word(m, W5 + 56), w7=word(m, W7 + 56), w8=word(m, W8 + 56),
                    w11_pack=word(m, W11 + 56), w11_ground=word(m, W11 + 82)),
        skinnable=list(m[0x4AE0:0x4AE6]), kcal=word(m, 0x4BDC), salt=word(m, 0x4A4A),
        hour=round(fp(m[0x4C57:0x4C5C]), 4), air=m[0x4B9B], spoil_factor=round(fp(m[0x4C48:0x4C4D]), 5),
        selectors=[m[0x4B41], m[0x4B42], m[0x4B44]], hp=round(fp(m[0x4C34:0x4C39]), 4))
    return sel


def run_game():
    import re_camp_probe

    class Original(re_camp_probe.Original):
        def __exit__(self, *a):
            (OUT / 'game.log').write_text(self.s.out)
            self.s.__exit__(*a)

    rows = []

    def do(o, *cmd, rnd=None):
        if rnd is not None:
            rnd_const(o, rnd)
        text = o.cmd(*cmd)
        if rnd is not None:
            rnd_restore(o)
        rows.append(dict(command=' '.join(cmd) + (f' [RND={rnd}]' if rnd is not None else ''), text=text,
                         state=snapshot(o.mem())))

    with Original() as o:
        rows.append(dict(command='START', state=snapshot(o.mem())))
        # GAME present, GUN carried and in use
        o.poke(b2 + 5, [0])
        o.poke(B1 + 57, [3])
        o.poke(B2 + 57, [1])
        do(o, 'KILL GAME', rnd=.1)                 # p .3 (light), 4 + INT(6.4) = 10 oz
        do(o, 'TASTE GAME')
        do(o, 'EAT GAME', '4')
        do(o, 'PACK GAME', '3')
        do(o, 'COOK GAME', 'G', '1')                # no fire: msg 65
        o.poke(0x45CD, [0])                         # a fire on the cell
        do(o, 'COOK GAME', '2', 'P', '.5')
        do(o, 'SKIN GAME')
        do(o, 'REST', '3')                          # spoilage clock
        # wild food on the ground: mushrooms code 2, 80 %
        o.poke(b1 + 10, [0])
        o.poke(w5 + 20, w(20))
        o.poke(w7 + 20, w(20))
        o.poke(w10 + 50, w(50))
        o.poke(W9 + 136, w(0))
        o.poke(W10 + 136, w(2))
        o.poke(W11 + 136, w(80))
        do(o, 'PACK MUSHROOMS', '5')
        do(o, 'TASTE MUSHROOMS', 'P')
        do(o, 'EAT MUSHROOMS', '2', 'P', rnd=.9)
        do(o, 'COOK MUSHROOMS', '3', 'P', '1', rnd=.9)  # cooked from the pack, no detox (RND .9)
        do(o, 'EAT CHEESE', '4', 'G')
        do(o, 'COOK CHEESE', '4', 'P', '1')
        # DROP from the pack: does the pack quality reach the ground record?
        do(o, 'PACK MUSHROOMS', '4')
        o.poke(b3 + 10, [3])
        o.poke(b4 + 10, [5])
        o.poke(w9 + 50, w(15))
        o.poke(w11 + 20, w(5))
        do(o, 'DROP MUSHROOMS', '2')
        do(o, 'CARRY MUSHROOMS')
        do(o, 'GET MUSHROOMS')
        do(o, 'PACK MUSHROOMS', '40')
    with Original() as o:
        rows.append(dict(command='START (bear)', state=snapshot(o.mem())))
        o.poke(b2 + 1, [0])
        o.poke(0x4B72, [1])
        o.poke(B1 + 57, [3])
        o.poke(B2 + 57, [1])
        do(o, 'KILL BEAR', rnd=.1)
        do(o, 'SKIN BEAR')
        do(o, 'GET BEAR')
        do(o, 'EAT BEAR', '10')
    with Original() as o:
        # spoilage below freezing and with 15-minute steps
        o.poke(b1 + 5, [0])
        o.poke(w5 + 10, w(20))
        o.poke(w7 + 10, w(20))
        o.poke(w11 + 52, w(29))
        rows.append(dict(command='START (spoil)', state=snapshot(o.mem())))
        do(o, 'WAIT', '1')
        do(o, 'WAIT', '4')
        do(o, 'IGNORE FOOD')
        do(o, 'FLAG FOOD')
        do(o, 'GET FOOD')
        do(o, 'USE BAIT')
        do(o, 'GET FRUIT')
    return rows


def run_spoil_trace():
    """Spoilage clock of T09/S05 ($5A1D-$5ADC): each health update with an
    air temperature $4B9B >= 33 F takes INT($4C08 / 60 + .5) hours off every
    counter. $5A2C is reached when $4C08 >= $4BCC; $5A43 stores the hours."""
    import re
    import re_camp_probe

    class Original(re_camp_probe.Original):
        def __exit__(self, *a):
            (OUT / 'spoil.log').write_text(self.s.out)
            self.s.__exit__(*a)

    rows = []
    with Original() as o:
        o.s.step('watch:5A2C:4C08:2')
        o.s.step('watch:5A43:5A41:4')
        for cmd in (('WAIT', '1'), ('WAIT', '4'), ('REST', '3')):
            start = len(o.s.out)
            before = word(o.mem(), W11 + 56)
            text = o.cmd(*cmd)
            after = word(o.mem(), W11 + 56)
            log = o.s.out[start:]
            minutes, hours = [], []
            for line in log.splitlines():
                m = re.match(r'watch 5A2C .* mem=([0-9A-F]+)', line)
                if m:
                    minutes.append(int.from_bytes(bytes.fromhex(m[1]), 'little'))
                m = re.match(r'watch 5A43 A=([0-9A-F]{2}) .* mem=A5A185FB', line)
                if m:
                    hours.append(int(m[1], 16))
            rows.append(dict(command=' '.join(cmd), cheese_spoil=[before, after], minutes_at_update=minutes,
                             hours_taken=hours))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cases = isolated()
    for c in cases:
        print(c['name'], '| log', c['log'], 'final', c['final'], 'exit', c['exit'], 'rnd', c['rnd_calls'],
              '|', c['out'])
    game = run_game() if '--no-game' not in sys.argv else []
    for row in game:
        print(row['command'], '|', row.get('text', ''), '|', row['state'])
    spoil = run_spoil_trace() if '--no-game' not in sys.argv else []
    for row in spoil:
        print(row)
    (OUT / 'results.json').write_text(json.dumps(dict(isolated=cases, game=game, spoil=spoil), indent=1) + '\n')


if __name__ == '__main__':
    main()
