#!/usr/bin/env python3
"""The MAKE recipes of the original (lot 3, docs/CRAFT.md), on the ROM.

Part 1 runs the Journey modules alone on the Apple II ROM, the way
tools/re_forage_probe.py does (its driver, stubs and state decoder): each
module copied to $5800 over a pristine copy of the saved first-journey state
(build/game.bin, reset before every case), RND ($0321) replaced by a table of
imposed values that counts the draws, the message, input, time-engine and
chain entries of the core stubbed:

  T10/S00  MAKE of the families 1, 5, 7 (core T05/S00 $551E): shelters HUT,
           IGLOO, TRENCH; HIDE; clothes, tent and pack from hide; CLUB,
           SPEAR, BOW, AXE; SPLINT; SUNGLASSES (bark eye shades), SUNSCREEN
           (mud)
  T10/S05  MAKE of the families 8, 9 (selector $1E 8 or 9): ROPE, RAFT,
           CANTEEN, UTENSILS, FISHNG GEAR, SNOWSHOES, TRAP, TRINKETS
  T11/S00  USE of the shelters, of the tent, of the weapons

Part 2 plays a few commands in the real game (build/SIERRA.woz +
build/JOURNEY.dsk): MAKE at the wreck ($D9 = $7F), after a walk, in the
woods, USE HUT, EXIT and ENTER, with the printed texts.

Part 3 (the transaction T0E/S02 of the second set, real game): GET, PACK,
CARRY, DROP, REMOVE, WEAR, USE of the ROCK of the start cell and of a BOW,
SPEAR, CLUB, SPLINT made on the next cell (their b1 poked to 0), a walk
away and back: b1..b4[14..18] after each command. The tent and the rope
are dropped first and the player carries one heavy thing at a time, so
that no weight limit answers (the limits: tools/re_load_probe.py).

No original byte enters the repository: modules and disks stay in build/,
results go to build/re_craft/results.json (numbers quoted in docs/CRAFT.md).
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
import re_forage_probe as rf        # noqa: E402

OUT = HERE / 'build/re_craft'
B1, B2, B3, B4 = rf.B1, rf.B2, rf.B3, rf.B4
W5, W7, W8 = rf.W5, rf.W7, rf.W8
b1, b2, b3, b4 = rf.b1, rf.b2, rf.b3, rf.b4
w5, w7, w8 = rf.w5, rf.w7, rf.w8
w = rf.w
HEALTH = 0x4C34
# Pages where the images wait (the driver copies them to $5800).
PAGES = {'t10s00': (0x70, 5), 't10s05': (0x76, 7), 't11s00': (0x30, 7)}
# Nouns (docs/logic/parser.md) and their family ($06).
N = dict(PARKA=2, TENT=9, BACKPACK=21, SUNGLASSES=43, SUNSCREEN=44, AXE=58, ROPE=60, SNOWSHOES=63,
         CANTEEN=64, GEAR=67, RAFT=70, TRAP=72, UTENSILS=73, TRINKETS=74, BOW=89, SPEAR=90, CLUB=91,
         ROCK=92, SPLINT=93, HIDE=94, HUT=95, IGLOO=96, TRENCH=97)
FAMILY = {2: 1, 9: 1, 21: 1, 43: 5, 44: 5, 58: 7, 60: 8, 63: 8, 64: 9, 67: 9, 70: 9, 72: 9, 73: 9,
          74: 9, 89: 7, 90: 7, 91: 7, 92: 7, 93: 5, 94: 1, 95: 1, 96: 1, 97: 1}
# The usual context of a case: daylight, clear ground, no tree, away from the
# wreck and the outpost, no airplane nor outpost on the cell (b1[23], b1[24]),
# the Sierra (region 2).
BASE = [(0x0D5D, [1]), (0x4B56, [0]), (0x4B57, [0]), (0x4B6B, [0]), (b1 + 23, [255]), (b1 + 24, [255])]
NO_TOOLS = [(B1 + 58, [255]), (B1 + 60, [255]), (B1 + 67, [255]), (B1 + 65, [255])]


def make(name, noun, pokes=(), zp=None, verb=3, module='t10s00', sel=None, **info):
    z = {3: verb, 5: N[noun], 6: FAMILY[N[noun]], 0x1E: 0, 0xD7: 0, 0xD8: 0xFF, 0xD9: 0xFF}
    if sel is not None:
        z[0x1E] = sel
    z.update(zp or {})
    return rf.case(name, module, 0x5800, z, BASE + list(pokes), info.pop('rnd', []),
                   num=info.pop('num', 0), yes=info.pop('yes', 0), hours='', **info)


def health(v):
    return [(HEALTH, list(encode(v)))]


def shelter_cases():
    c = []
    woods = [(0x4B56, [1])]
    for label, extra in (('light 1', []), ('light 0', [(0x0D5D, [0])]), ('axe in use', [(B2 + 58, [1])]),
                         ('health 2.5', health(2.5)), ('light 0 axe health 2.5',
                                                       [(0x0D5D, [0]), (B2 + 58, [1])] + health(2.5))):
        for noun, ground in (('TRENCH', []), ('HUT', woods), ('IGLOO', [(0x4B57, [1])])):
            c.append(make(f'make {noun.lower()} {label}', noun, ground + extra))
    c.append(make('make hut clear', 'HUT'))
    c.append(make('make hut rocky', 'HUT', [(0x4B56, [2])]))
    c.append(make('make hut tree', 'HUT', zp={0xD7: 1}))
    c.append(make('make igloo no snow', 'IGLOO'))
    c.append(make('make igloo snow woods', 'IGLOO', [(0x4B57, [1]), (0x4B56, [1])]))
    c.append(make('make trench woods', 'TRENCH', [(0x4B56, [1])]))
    c.append(make('make trench rocky', 'TRENCH', [(0x4B56, [2])]))
    for label, terrain, shore in (('river', 3, 3), ('lake', 4, 0), ('river shore', 3, 1), ('lake shore', 4, 1),
                                  ('river 0', 3, 0)):
        c.append(make(f'make trench {label}', 'TRENCH', [(0x4B56, [terrain]), (0x4B6B, [shore])]))
    c.append(make('make trench at the outpost', 'TRENCH', zp={0xD8: 0x7F}))
    c.append(make('make trench at the wreck', 'TRENCH', zp={0xD9: 0x7F}))
    c.append(make('make hut at the wreck clear', 'HUT', zp={0xD9: 0x7F}))
    c.append(make('make hut there', 'HUT', [(0x4B56, [1]), (b1 + 20, [0])]))
    c.append(make('make igloo there', 'IGLOO', [(0x4B57, [1]), (b1 + 21, [0])]))
    c.append(make('make hide none', 'HIDE'))
    c.append(make('make hide some', 'HIDE', [(b1 + 19, [0]), (w5 + 38, w(50)), (w7 + 38, w(50))]))
    return c


def weapon_cases():
    c = []
    woods = [(0x4B56, [1])]
    c.append(make('make club woods', 'CLUB', woods))
    c.append(make('make club health 2.5', 'CLUB', woods + health(2.5)))
    c.append(make('make club clear', 'CLUB'))
    c.append(make('make club tree', 'CLUB', zp={0xD7: 1}))
    c.append(make('make club rocky tree', 'CLUB', [(0x4B56, [2])], zp={0xD7: 1}))
    c.append(make('make club river', 'CLUB', [(0x4B56, [3]), (0x4B6B, [3])]))
    c.append(make('make club at the wreck', 'CLUB', woods, zp={0xD9: 0x7F}))
    for noun in ('SPEAR', 'BOW', 'AXE'):
        n = noun.lower()
        c.append(make(f'make {n} woods rope', noun, woods + [(B1 + 58, [255])]))      # (the AXE absent)
        c.append(make(f'make {n} clear', noun))
        c.append(make(f'make {n} woods no rope', noun, woods + NO_TOOLS))
        c.append(make(f'make {n} woods gear', noun, woods + NO_TOOLS + [(B1 + 67, [2])]))
        c.append(make(f'make {n} woods rope ground', noun, woods + NO_TOOLS + [(B1 + 60, [0])]))
        c.append(make(f'make {n} woods knife', noun, woods + [(B1 + 58, [255]), (B2 + 59, [1])]))
        c.append(make(f'make {n} woods health 2.5', noun, woods + [(B1 + 58, [255])] + health(2.5)))
        c.append(make(f'make {n} woods light 0', noun, woods + [(B1 + 58, [255]), (0x0D5D, [0])]))
        c.append(make(f'make {n} woods knife light 0', noun,
                      woods + [(B1 + 58, [255]), (B2 + 59, [1]), (0x0D5D, [0])]))
        for region in (3, 1):
            c.append(make(f'make {n} woods no rope region {region}', noun, woods + NO_TOOLS + [(0x601F, [region])]))
    c.append(make('make rock', 'ROCK', woods))
    return c


def care_cases():
    c = []
    woods = [(0x4B56, [1])]
    no_shortcut = [(B1 + 58, [255]), (b1 + 15, [255])]
    c.append(make('make splint axe here', 'SPLINT'))            # the saved game: AXE in the pack
    c.append(make('make splint axe health 2.5', 'SPLINT', health(2.5)))
    c.append(make('make splint axe light 0', 'SPLINT', [(0x0D5D, [0])]))
    c.append(make('make splint axe knife', 'SPLINT', [(B2 + 59, [1])]))
    c.append(make('make splint axe rocky', 'SPLINT', [(0x4B56, [2])]))
    c.append(make('make splint axe river', 'SPLINT', [(0x4B56, [3])]))
    c.append(make('make splint spear', 'SPLINT', [(B1 + 58, [255]), (b1 + 15, [0]), (0x4B56, [2])]))
    c.append(make('make splint airplane', 'SPLINT', no_shortcut + [(b1 + 23, [0]), (0x4B56, [2])]))
    c.append(make('make splint outpost', 'SPLINT', no_shortcut + [(b1 + 24, [0]), (0x4B56, [2])]))
    c.append(make('make splint clear', 'SPLINT', no_shortcut))
    c.append(make('make splint clear tree', 'SPLINT', no_shortcut, zp={0xD7: 1}))
    c.append(make('make splint rocky tree', 'SPLINT', no_shortcut + [(0x4B56, [2])], zp={0xD7: 1}))
    c.append(make('make splint woods', 'SPLINT', no_shortcut + woods))
    c.append(make('make splint woods knife', 'SPLINT', no_shortcut + woods + [(B2 + 59, [1])]))
    c.append(make('make splint woods no rope', 'SPLINT', no_shortcut + woods + NO_TOOLS))
    c.append(make('make splint woods gear', 'SPLINT', no_shortcut + woods + NO_TOOLS + [(B1 + 67, [2])]))
    c.append(make('make splint woods no rope region 4', 'SPLINT',
                  no_shortcut + woods + NO_TOOLS + [(0x601F, [4])]))
    for noun in ('SUNGLASSES', 'SUNSCREEN'):
        n = noun.lower()
        absent = [(B1 + N[noun], [255])]
        c.append(make(f'make {n} clear', noun, absent))
        c.append(make(f'make {n} woods', noun, absent + woods))
        c.append(make(f'make {n} rocky', noun, absent + [(0x4B56, [2])]))
        c.append(make(f'make {n} river', noun, absent + [(0x4B56, [3])]))
    return c


def hide_cases():
    """Clothes, tent and pack from hide ($584A-$599B, A3)."""
    c = []
    hide = lambda g, p=0: [(b1 + 19, [0 if not p else (4 if g else 2)]), (b2 + 19, [1]),        # noqa: E731
                           (w5 + 38, w(g + p)), (w7 + 38, w(g)), (w8 + 38, w(p))]
    for noun in ('PARKA', 'TENT', 'BACKPACK'):
        n = noun.lower()
        absent = [(B1 + N[noun], [255])]
        c.append(make(f'make {n} hide not in use', noun, absent + [(b1 + 19, [0]), (w5 + 38, w(400)),
                                                                     (w7 + 38, w(400))]))
        c.append(make(f'make {n} hide 400 ground', noun, absent + hide(400)))
        c.append(make(f'make {n} hide 20 ground', noun, absent + hide(20)))
        c.append(make(f'make {n} hide 10 + 390 pack', noun, absent + hide(10, 390)))
    c.append(make('make parka hide knife sewing', 'PARKA',
                  [(B1 + 2, [255]), (B2 + 59, [1]), (B2 + 65, [1])] + hide(400)))
    return c


def craft2_cases():
    """T10/S05 (A3): selector 8 ROPE, 9 the family 9 and SNOWSHOES."""
    c = []
    m = 't10s05'
    woods = [(0x4B56, [1])]
    hide = lambda g: [(b1 + 19, [0]), (w5 + 38, w(g)), (w7 + 38, w(g))]        # noqa: E731
    rope = [(B1 + 60, [255]), (B1 + 1, [2])]    # (the sleeping bag present: item 1 of the menu)
    for item in range(1, 8):
        c.append(make(f'make rope artificial item {item}', 'ROPE', rope, module=m, sel=8, yes=0, num=item))
    c.append(make('make rope artificial 0', 'ROPE', rope, module=m, sel=8, yes=0, num=0))
    c.append(make('make rope natural hide 40', 'ROPE', rope + hide(40), module=m, sel=8, yes=1))
    c.append(make('make rope natural hide 20 clear', 'ROPE', rope + hide(20), module=m, sel=8, yes=1))
    for d in (2, 4, 8, 38):
        c.append(make(f'make rope natural woods diameter {d}', 'ROPE', rope + woods, module=m, sel=8, yes=1,
                      num=d))
    c.append(make('make rope natural woods region 3', 'ROPE', rope + woods + [(0x601F, [3])], module=m, sel=8,
                  yes=1))
    for r in (.1999, .2001):
        c.append(make(f'make trinkets rnd {r}', 'TRINKETS', [(B1 + 74, [255])], module=m, sel=9, rnd=[r]))
    for noun in ('RAFT', 'UTENSILS', 'GEAR', 'SNOWSHOES', 'TRAP'):
        n = noun.lower()
        absent = [(B1 + N[noun], [255])]
        c.append(make(f'make {n} clear', noun, absent, module=m, sel=9))
        c.append(make(f'make {n} woods', noun, absent + woods, module=m, sel=9))
        c.append(make(f'make {n} woods no tools', noun, absent + woods + NO_TOOLS + [(B1 + 59, [255])],
                      module=m, sel=9))
        c.append(make(f'make {n} woods knife axe', noun, absent + woods + [(B2 + 58, [1]), (B2 + 59, [1])],
                      module=m, sel=9))
    c.append(make('make raft river shore', 'RAFT', [(B1 + 70, [255]), (0x4B56, [3]), (0x4B6B, [1])],
                  module=m, sel=9))
    c.append(make('make raft hide 400 woods', 'RAFT', [(B1 + 70, [255])] + woods + hide(400), module=m, sel=9,
                  yes=0))
    for item in range(1, 7):
        c.append(make(f'make canteen artificial item {item}', 'CANTEEN', [(B1 + 64, [255]), (B1 + 1, [2])], module=m, sel=9,
                      yes=0, num=item))
    c.append(make('make canteen natural woods', 'CANTEEN', [(B1 + 64, [255])] + woods, module=m, sel=9,
                  yes=1))
    c.append(make('make canteen natural hide 40', 'CANTEEN', [(B1 + 64, [255])] + woods + hide(40),
                  module=m, sel=9, yes=1))
    c.append(make('make canteen natural hide 40 no', 'CANTEEN', [(B1 + 64, [255])] + woods + hide(40),
                  module=m, sel=9, yes=1, num=1))
    return c


def use_cases():
    """T11/S00: USE HUT, IGLOO, TRENCH ($58BD), TENT ($58E4), the weapons ($5C42)."""
    c = []
    m = 't11s00'
    for noun, k in (('HUT', 20), ('IGLOO', 21), ('TRENCH', 22)):
        c.append(make(f'use {noun.lower()}', noun, [(b1 + k, [0])], verb=2, module=m))
    c.append(make('use tent pack', 'TENT', [], verb=2, module=m))
    c.append(make('use tent ground', 'TENT', [(B1 + 9, [0])], verb=2, module=m))
    c.append(make('use tent at the wreck', 'TENT', [], verb=2, module=m, zp={0xD9: 0x7F}))
    for noun, k in (('BOW', 14), ('SPEAR', 15), ('CLUB', 16), ('ROCK', 17)):
        c.append(make(f'use {noun.lower()} ground', noun, [(b1 + k, [0])], verb=2, module=m))
        c.append(make(f'use {noun.lower()} carried', noun, [(b1 + k, [3])], verb=2, module=m))
    c.append(make('use splint', 'SPLINT', [(b1 + 18, [0])], verb=2, module=m))
    return c


def build_disk():
    journey = smalldos.Disk((HERE / 'build/JOURNEY.dsk').read_bytes())
    journey.flip = True
    game = (HERE / 'build/game.bin').read_bytes()
    state = bytearray(game[0x4000:0x8000])
    for entry, target in rf.STUBS.items():
        state[entry - 0x4000:entry - 0x4000 + 3] = bytes((0x4C, target & 255, target >> 8))
    pristine = game[0x4000:0x4D00] + game[0x6000:0x6100] + game[0x0D00:0x0E00]
    driver = bytearray(0x300)
    for org, code in rf.DRIVER:
        driver[org - 0x800:org - 0x800 + len(code)] = code
    OUT.mkdir(parents=True, exist_ok=True)
    m1 = journey.run(0x10, 0, 5).ljust(0x600, b'\0') + journey.run(0x10, 5, 7)    # $7000, $7600
    m2 = journey.run(0x11, 0, 7)                                                  # $3000
    files = {'STATE': (state, 0x4000), 'PRISTINE': (pristine, 0x2000), 'DRIVER': (driver, 0x0800),
             'M1': (m1, 0x7000), 'M2': (m2, 0x3000)}
    args = []
    for name, (data, org) in files.items():
        (OUT / f'{name.lower()}.bin').write_bytes(data)
        args += ['--bin', f'{name}={OUT / (name.lower() + ".bin")}@{org:#x}']
    hello = ''.join(f'{10 * (i + 1)} PRINT CHR$(4);"BLOAD {n}"\n'
                    for i, n in enumerate(('STATE', 'PRISTINE', 'M1', 'M2')))
    hello += '90 PRINT CHR$(4);"BRUN DRIVER"\n'
    (OUT / 'hello.bas').write_text(hello)
    disk = OUT / 'craft.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'), '--out', str(disk),
                    '--bas', f'HELLO={OUT / "hello.bas"}'] + args, check=True, capture_output=True)
    return disk, game


def isolated():
    disk, game = build_disk()
    cases = shelter_cases() + weapon_cases() + care_cases() + hide_cases() + craft2_cases() + use_cases()
    steps = ['until:0800:40000']
    for addr, target in rf.RUNTIME.items():
        steps += rf.poke(addr, [0x4C, target & 255, target >> 8])
    for c in cases:
        steps.append('until:0803:40000')
        page, count = PAGES[c['module']]
        steps += rf.poke(0x09F2, w(c['entry'])) + rf.poke(0x09F4, [page, count])
        steps += rf.poke(0x0900, [0] * 0x40) + rf.poke(rf.RNDP, [rf.TABLE & 255, rf.TABLE >> 8, 0])
        steps += rf.poke(rf.TABLE, b''.join(encode(r) for r in c['rnd']))
        steps += rf.poke(rf.YES, [c['yes']]) + rf.poke(rf.NUM, w(c['num']))
        steps += rf.poke(rf.HOURS, [0])
        for a, v in sorted(c['zp'].items()):
            steps += rf.poke(a, [v])
        for a, v in c['pokes']:
            steps += rf.poke(a, v)
        steps += ['until:0809:400000', 'peek:0900:64', 'peek:09E0:3', 'peek:0000:256', 'peek:4000:3328',
                  'peek:0D00:256', 'peek:6000:256']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=3600)
    for k, c in enumerate(cases):
        m = r.mem(0x900, 64, k)
        zp = r.mem(0, 256, k)
        st = bytearray(0x4000) + r.mem(0x4000, 3328, k)
        d = r.mem(0x0D00, 256, k)
        c['log'] = list(m[0x11:0x11 + m[0x10]])
        c['final'] = m[0]
        c['exit'] = {0: None, 1: '$4D00', 3: '$4D03', 9: '$4D09', 0xDB: 'chain'}.get(m[8], m[8])
        if m[8] == 0xDB:
            c['chain'] = dict(sectors=m[9], track=m[10], sector=m[11])
        if m[0] == 0xFE:
            c['exit'] = '$B000'
        c['rnd_calls'] = r.mem(0x09E0, 3, k)[2]
        c['zp_out'] = {f'{a:02X}': zp[a] for a in (3, 4, 5, 7, 8, 0x0E, 0x0F)}
        out = rf.decode_state(st, game)
        for a, name in ((0x4BCC, '$4BCC step'), (0x4B45, '$4B45'), (0x4B53, '$4B53'), (0x4B4B, '$4B4B'),
                        (0x4BAF, '$4BAF')):
            if st[a] != game[a]:
                out[name] = [game[a], st[a]]
        for a in (0x0D5E, 0x0D5F, 0x0D88, 0x0D89, 0x0D8A, 0x0D8B):
            if d[a - 0x0D00] != game[a]:
                out[f'${a:04X}'] = [game[a], d[a - 0x0D00]]
        for a in (0x4BF0, 0x4BF2, 0x4BF4, 0x4BF8, 0x4BFC, 0x4BEE):
            if st[a:a + 2] != game[a:a + 2]:
                out[f'${a:04X}'] = [rf.word(game, a), rf.word(st, a)]
        c['out'] = out
    return cases


# ---------------------------------------------------------------------------
# Part 2: the real game.
def run_game():
    import re_camp_probe

    class Original(re_camp_probe.Original):
        def __exit__(self, *a):
            (OUT / 'game.log').write_text(self.s.out)
            self.s.__exit__(*a)

    rows = []

    def snap(m):
        return dict(d8=m[0xD8], d9=m[0xD9], d7=m[0xD7], light=m[0xD5D], inside=m[0xD5E], flags=list(m[0xD88:0xD8C]),
                    b1=[m[b1 + k] for k in (14, 15, 16, 17, 18, 20, 21, 22)],
                    b2=[m[b2 + k] for k in (14, 15, 16, 17, 18, 20, 21, 22)],
                    b3=[m[b3 + k] for k in (14, 15, 16, 18, 20, 21, 22)],
                    b4=[m[b4 + k] for k in (14, 15, 16, 18, 20, 21, 22)],
                    tent=[m[B1 + 9], m[B2 + 9]], step=m[0x4BCC], terrain=m[0x4B56],
                    hour=round(fp(m[0x4C57:0x4C5C]), 4), effort=round(fp(m[0x4C20:0x4C25]), 5),
                    cell=[m[0xF5], m[0xF7]], wreck=[m[0x6083], m[0x6084]], outpost=[m[0x6080], m[0x6081]])

    def do(o, *cmd):
        text = o.cmd(*cmd)
        rows.append(dict(command=' '.join(cmd), text=text, state=snap(o.mem())))

    with Original() as o:
        rows.append(dict(command='START', state=snap(o.mem())))
        do(o, 'MAKE HUT')                   # at the wreck: msg 49
        do(o, 'MAKE TRENCH')
        do(o, 'USE TENT')
        do(o, 'MAKE CLUB')                  # clear: msg 76
        do(o, 'MAKE SPLINT')                # the AXE in the pack: the shortcut
        do(o, 'MAKE SPLINT')
        do(o, 'WALK', '1')
        do(o, 'MAKE TRENCH')
        do(o, 'USE TRENCH')
        do(o, 'ENTER TRENCH')
        do(o, 'EXIT TRENCH')
        do(o, 'EXIT SHELTER')
        do(o, 'ENTER SHELTER')
        do(o, 'MAKE TRENCH')
        o.poke(0x4B56, [1])                 # woods
        do(o, 'MAKE HUT')
        o.poke(0x4B56, [1])
        do(o, 'MAKE CLUB')
        do(o, 'USE CLUB')
        o.poke(0x4B56, [1])
        do(o, 'MAKE SPEAR')
        do(o, 'MAKE SPEAR')
        do(o, 'INVENTORY')
        do(o, 'USE HUT')
        do(o, 'WAIT', '1')
        do(o, 'EXIT SHELTER')
        do(o, 'USE TENT')
        do(o, 'WALK', '1')
        do(o, 'MAKE HUT')
    with Original() as o:                   # ENTER and EXIT of a crafted shelter
        rows.append(dict(command='START (enter, exit)', state=snap(o.mem())))
        do(o, 'WALK', '1')
        o.poke(0x4B56, [1])
        do(o, 'MAKE HUT')
        do(o, 'EXIT HUT')
        do(o, 'ENTER HUT')
        do(o, 'ENTER HUT')
        do(o, 'EXIT HUT')
        do(o, 'USE HUT')
        do(o, 'USE HUT')
        do(o, 'EXIT TRENCH')
        do(o, 'EXIT HUT')
        do(o, 'USE IGLOO')
        do(o, 'MAKE BOW')
        do(o, 'MAKE AXE')
        do(o, 'MAKE SUNGLASSES')
        do(o, 'MAKE PARKA')
        do(o, 'MAKE CHEESE')
        do(o, 'MAKE BEAR')
        do(o, 'MAKE AIRPLANE')
        do(o, 'MAKE FOOD')
        do(o, 'MAKE TREE')
        do(o, 'MAKE STOVE')
        do(o, 'MAKE ROPE')
        do(o, 'MAKE GUN')
        do(o, 'MAKE ROCK')
        for noun in ('NORTH', 'CUTS', 'BODY', 'COLD', 'RAIN', 'SHELTER', 'STATUS', 'BAIT', 'SHADOW', 'COUGAR',
                     'FRUIT', 'GAME', 'STICKS', 'HIDE', 'OUTPOST', 'CITY'):
            do(o, 'MAKE ' + noun)
    return rows


# Part 3: GET, PACK, CARRY, DROP of the second set, the ROCK, leaving the cell.
ITEMS = [
    'DROP TENT', 'DROP ROPE',
    'GET ROCK', 'GET ROCK', 'DROP ROCK', 'DROP ROCK', 'PACK ROCK', 'PACK ROCK', 'CARRY ROCK', 'USE ROCK',
    'MAKE ROCK', 'WAIT 1', 'WEAR ROCK', 'DROP ROCK',
    'WALK .2',                                  # the cell A next to the wreck
    'made BOW SPEAR CLUB SPLINT',               # b1[14, 15, 16, 18] = 0 here
    'GET BOW', 'DROP BOW', 'PACK SPEAR', 'GET SPEAR', 'DROP SPEAR', 'CARRY CLUB', 'DROP CLUB',
    'GET SPLINT', 'WEAR SPLINT', 'REMOVE SPLINT', 'WEAR SPLINT', 'PACK SPLINT', 'DROP SPLINT',
    'USE BOW', 'DROP BOW', 'GET ROCK',
    'WALK .2',                                  # the cell B
    'GET SPEAR', 'GET CLUB', 'DROP ROCK',
    'LOOK BACK', 'WALK .2',                     # back on A: "PREVIOUSLY DROPPED ITEM"
    'GET SPEAR', 'GET CLUB', 'DROP SPEAR', 'GET ROCK',
]


def run_items():
    import re_camp_probe

    class Original(re_camp_probe.Original):
        def __exit__(self, *a):
            (OUT / 'items.log').write_text(self.s.out)
            self.s.__exit__(*a)

    def snap(m):
        return dict(cell=[m[0x4BA5], m[0x4BA6]], here=[m[0xD0], m[0xD1]], b1=[m[b1 + k] for k in range(14, 19)],
                    b2=[m[b2 + k] for k in range(14, 19)], b3=[m[b3 + k] for k in range(14, 19)],
                    b4=[m[b4 + k] for k in range(14, 19)], terrain=m[0x4B56],
                    sel3=m[0x4ABE])             # care selector 3 (the splint worn)

    rows = []
    with Original() as o:
        rows.append(dict(command='START', state=snap(o.mem())))
        for cmd in ITEMS:
            if cmd.startswith('made'):
                for k in (14, 15, 16, 18):
                    o.poke(b1 + k, [0])
                rows.append(dict(command=cmd, state=snap(o.mem())))
                continue
            words = cmd.split()
            text = o.cmd(*([' '.join(words[:-1]), words[-1]] if words[0] in ('WALK', 'WAIT') else [cmd]))
            rows.append(dict(command=cmd, text=text, state=snap(o.mem())))
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
    items = run_items() if '--no-game' not in sys.argv else []
    for row in items:
        print(row['command'], '|', row.get('text', ''), '|', row['state'])
    (OUT / 'results.json').write_text(json.dumps(dict(isolated=cases, game=game, items=items), indent=1) + '\n')


if __name__ == '__main__':
    main()
