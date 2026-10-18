#!/usr/bin/env python3
"""CRAFT, lot 3 step 1 (docs/CRAFT.md): the MAKE recipes of the original.

Part 1: the cases of tools/re_craft_probe.py (build/re_craft/results.json:
T10/S00 and T11/S00 run alone on the ROM) replayed in the port: the
original's state translated into the port's (src/craft.s, camp.s, care.s,
forage.s), the command typed, the context the CRAFT module cannot compute
(the ground class, the snow line: camp_craft) imposed when sim_fetch reads
the module, the decisions read at camp_done (before the time passes) or at
the prompt, then the messages, minutes, effort, created objects, shelters
and "in use" flags compared.
Part 2: the real-game commands of the probe (ENTER, EXIT, MAKE of every
noun family), their messages.
Part 3: the ROM's transaction script of the second set (results.json
'items': GET, PACK, CARRY, DROP, WEAR, USE of the ROCK, BOW, SPEAR, CLUB,
SPLINT, a walk away and back), the places, "in use" flags and refusals
compared after each command.
Part 4 (the port): the inventory, a KILL GAME with the BOW, a real walk
(the CLUB lost, a ROCK on the new cell), SAVE/RESTORE of the crafted things
on their cells, ATTACK with each weapon in use (the thresholds of
build/regions/fauna.json, measured on the ROM), the 140 KB edition.

  python3 tests/test_craft.py              all of it
  python3 tests/test_craft.py --original   parts 1 and 2 (fails if
                                           results.json is missing)
"""
import json
import re
import sys
from pathlib import Path
from common import HERE, L, DISK, DISK140, a2test, fp, text_screen
from gendata import fp as encode
from test_input import IDLE

RESULTS = HERE / 'build/re_craft/results.json'
MAP = 0x7000
b1, b2 = 0x45C0, 0x45DC
B1, B2 = 0x404C, 0x4098
HEALTH = 0x4C34
fails = []

TEXTS = {1: 'SORRY, THAT ITEM IS NOT AVAILABLE.', 2: "YOU'RE NOT MAKING MUCH SENSE.", 4: 'YOU NEED STRONG ROPE.',
         9: "YOU'RE NOW SAFELY INSIDE SHELTER.", 10: 'OK, WHAT NEXT?', 11: 'YOU ALREADY HAVE.',
         15: 'IT TOOK A WHILE TO MAKE YOUR', 17: 'TRY TO BE MORE SPECIFIC.',
         21: "YOUR POWERS DON'T EXTEND THAT FAR!", 28: 'GOOD! YOU MADE EYE SHADES FROM SLITTED BARK.',
         35: 'YOU NEED TO SKIN A CREATURE FOR ITS HIDE.', 49: 'THINK!',
         65: 'YOU NEED A FIRE TO BOIL OR COOK THINGS', 76: 'SORRY, SUFFICIENT RAW MATERIAL IS NOT AVAILABLE.',
         92: "YOU'RE IN THE WATER ALREADY!", 101: 'FOR MORE HIDE, SKIN A CREATURE AND ADD TO YOUR SUPPLY.',
         205: "SMEARING MUD ON YOUR SKIN TO BLOCK THE SUN'S RAYS."}
EFFORT = {1: .01, 2: .02, 3: .023}
SKIP = {
    'make parka': 'clothes from hide: lot 5 (A3)', 'make tent': 'tent from hide: lot 5 (A3)',
    'make backpack': 'pack from hide: lot 5 (A3)', 'make rope': 'T10/S05: lot 5 (A3)',
    'make trinkets': 'T10/S05: lot 5', 'make raft': 'T10/S05: lot 5', 'make utensils': 'T10/S05: lot 5',
    'make gear': 'T10/S05: lot 5', 'make snowshoes': 'T10/S05: lot 5', 'make trap': 'T10/S05: lot 5',
    'make canteen': 'T10/S05: lot 5',
    'use splint': 'lot 13 (tests/test_care.py)',
    'make hide some': None,
}
TREE = 'a tree out of the woods ($D7): the port grows trees in the woods only'


def check(name, ok, detail=''):
    print(f'  {name}: {"OK" if ok else "FAIL"}' + (f' {detail}' if not ok and detail else ''))
    if not ok:
        fails.append(name)


def rows(s):
    return ' '.join(' '.join(line[:39].split()) for line in text_screen(s.step('peek:0400:1024').data)[20:24])


def pc(r):
    return int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16)


class Port:
    def __init__(self, s):
        self.s = s
        game = (HERE / 'build/wildgame.bin').read_bytes()
        self.place = game[L['it_place'] - 0x4000:][:76]
        self.health = list(game[L['s_health'] - 0x4000:][:5])
        self.wreck = tuple(s.step(f'peek:{MAP + 3:04X}:3').data[::2])
        self.goal = tuple(s.step(f'peek:{MAP + 8:04X}:2').data)
        x, y = self.wreck
        self.away = (x + 3, y) if (x + 3, y) != self.goal else (x + 4, y)

    def poke(self, name, value, k=0):
        for i, v in enumerate(value if isinstance(value, (list, bytes, bytearray)) else [value]):
            self.s.step(L.poke(name, v & 255, k + i))

    def byte(self, name, k=0):
        return self.s.step(L.peek(name, 1, k)).data[0]

    def move(self, cell):
        self.poke('px', cell[0], 1)
        self.poke('py', cell[1], 1)

    def reset(self, cell):
        """A fresh state on `cell`: nothing crafted, no tool in use, daylight,
        the saved health, the Sierra, the items of the saved game."""
        self.move(cell)
        self.poke('cr_b1', [255, 255, 255, 0, 255])         # the ROCK on the ground, as the saved game
        self.poke('cr_still', 1)
        self.poke('cr_sx', [255] * 6)
        self.poke('cr_cx', [255] * 6)
        for name, v in (('splint_place', 255), ('care_tools', 0), ('fg_use', 0), ('shelter_inside', 0),
                        ('health_period', 15), ('light', 1), ('region_number', 2), ('fire_on', 0),
                        ('camp_use', 0), ('al_forced', 0), ('mn_mode', 0)):
            self.poke(name, v)
        self.poke('s_health', self.health)
        self.poke('load_limits', [815 & 255, 815 >> 8])      # (lot 14: the original's weight)
        for n in (9, 43, 44, 58, 59, 60, 65, 67):
            self.poke('it_place', self.place[n], n)
        self.poke('fg_b1', 255, 11)
        self.poke('fg_gl', 0, 11)
        self.poke('fg_x', cell[0])                          # (forage_here: the cell's piles)
        self.poke('fg_y', cell[1])
        self.poke('animal_kind', 0)
        for name in ('s_defw', 's_deff', 's_defr'):         # rested and fed: no alert hides
            self.poke(name, [0] * 5)                          # the result
        self.poke('al_last', [100] * 21)


def translate(port, c):
    """The case's pokes and zero page onto the port; returns the context
    (cr_class, cr_snow) for camp_craft, or a reason to skip."""
    zp = {int(k): v for k, v in c['zp'].items()}
    pokes = {a: v for a, v in c['pokes']}
    if zp.get(0xD7):
        return TREE
    cell = port.away
    if zp.get(0xD9) == 0x7F or pokes.get(b1 + 23) == [0]:
        cell = port.wreck
    if zp.get(0xD8) == 0x7F or pokes.get(b1 + 24) == [0]:
        cell = port.goal
    port.reset(cell)
    terrain = pokes.get(0x4B56, [0])[0]
    shore = pokes.get(0x4B6B, [0])[0]
    cls = (3 if shore in (0, 3) else 0) if terrain >= 3 else terrain
    ctx = dict(cr_class=cls, cr_snow=pokes.get(0x4B57, [0])[0])
    for addr, data in c['pokes']:
        v = data[0]
        if addr == 0x0D5D:
            port.poke('light', v)
        elif addr in (0x4B56, 0x4B57, 0x4B6B, b1 + 23, b1 + 24):
            pass
        elif addr == HEALTH:
            port.poke('s_health', data)
        elif addr == 0x601F:
            port.poke('region_number', v)
        elif B2 + 58 <= addr <= B2 + 59:
            port.poke('care_tools', port.byte('care_tools') | (addr - B2 - 57))
            port.poke('care_tool_x', cell[0])
            port.poke('care_tool_y', cell[1])
        elif B2 < addr < B2 + 76:
            pass                                            # (SEWING KIT: lot 5)
        elif B1 < addr < B1 + 76:
            n = addr - B1
            port.poke('it_place', v, n)
            if v == 0:
                port.poke('it_x', cell[0], n)
                port.poke('it_y', cell[1], n)
        elif b1 + 14 <= addr <= b1 + 18:
            k = addr - b1 - 14
            port.poke('cr_b1', v, k)
            if k in (0, 1, 4):
                port.poke('cr_cx', cell[0], min(k, 2))
                port.poke('cr_cy', cell[1], min(k, 2))
        elif addr == b1 + 19:
            port.poke('fg_b1', v, 11)
            port.poke('fg_gl', 50, 11)
            port.poke('fg_x', cell[0])
            port.poke('fg_y', cell[1])
        elif b1 + 20 <= addr <= b1 + 22:
            port.poke('cr_sx', cell[0], addr - b1 - 20)
            port.poke('cr_sy', cell[1], addr - b1 - 20)
        elif 0x4630 <= addr < 0x47B8:
            pass                                            # hide ounces (presence only)
        else:
            raise AssertionError(f'{c["name"]}: no translation for ${addr:04X}')
    return ctx


def run(port, command, ctx=None):
    """The command; ctx poked at sim_fetch (the CRAFT read); decisions read
    at camp_done (timed) or at the prompt. Returns (text, decisions)."""
    s = port.s
    s.step(f'key:{command}')
    s.step('press:\\r')
    s.step(L.until('do_command', 40000))
    got = None
    if ctx is not None:
        r = s.step(f'until:{L["sim_fetch"]:04X},{L["idle"]:04X}:60000')
        if pc(r) == L['sim_fetch']:
            for k, v in ctx.items():
                port.poke(k, v)
    screens = []
    r = s.step(f'until:{L["camp_done"]:04X},{L["idle"]:04X},{L["keyboard_wait"]:04X}:60000')
    if pc(r) == L['camp_done']:
        got = decisions(port)
        got['minutes'] = port.byte('camp_minutes') | port.byte('camp_minutes', 1) << 8
        got['eff'] = port.byte('cr_eff')
        got['metabolic'] = fp(s.step(L.peek('s_metabolic', 5)).data)
        s.step(f'until:{L["spend"]:04X}:60000')             # the result, before an animal's
        screens.append(rows(s))
    for _ in range(12):
        r = s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:60000')
        screens.append(rows(s))
        if pc(r) == L['idle']:
            break
        s.step('key: ')
    if got is None:
        got = decisions(port)
        got['minutes'] = 0
        got['eff'] = None
    return ' // '.join(screens), got


def decisions(port):
    x, y = port.byte('px', 1), port.byte('py', 1)
    return dict(cr_b1=[port.byte('cr_b1', i) for i in range(4)],
                shelters=[port.byte('cr_sx', i) == x and port.byte('cr_sy', i) == y for i in range(3)],
                splint=port.byte('splint_place'), fg_use=port.byte('fg_use'),
                inside=port.byte('shelter_inside'), period=port.byte('health_period'),
                place={n: port.byte('it_place', n) for n in (9, 43, 44, 58)})


def expect(c, got, text):
    """The ROM's results against the port's decisions: a list of differences."""
    out, bad = c['out'], []
    use = c['name'].startswith('use ')
    for m in c['log']:
        if m in TEXTS and TEXTS[m] not in text:
            bad.append(('msg', m, text))
    if not c['log'] and use and TEXTS[10] not in text:
        bad.append(('msg', 10, text))                       # (CARRY's answer: msg 10)
    want = out.get('$4BC6 minutes', [0, 0])[1] if c['exit'] else 0
    if got['minutes'] != want:
        bad.append(('minutes', got['minutes'], want))
    if c['exit']:
        if 'effort $4C20' in out:
            k = EFFORT.get(got['eff'])
            if k is None or abs(1.65 + k * 213 - out['effort $4C20'][1]) > .01:
                bad.append(('effort', got['eff'], out['effort $4C20'][1]))
        elif got['eff']:
            bad.append(('effort', got['eff'], 'none'))
    for k in (14, 15, 16, 17):
        key = f'b1[{k}]'
        if key in out or (use and c['name'].split()[1].upper() == NAMES[k - 14]):
            w = 3 if use else out[key]                      # USE: then CARRY, in hand
            if got['cr_b1'][k - 14] != w:
                bad.append((key, got['cr_b1'][k - 14], w))
        key = f'b2[{k}]'
        bit = 4 << min(k - 14, 2)                           # the ROCK's b2 is the CLUB's bit
        want = out.get(key, 0) or (k >= 16 and out.get(f'b2[{33 - k}]', 0))
        if bool(got['fg_use'] & bit) != bool(want):
            bad.append((key, got['fg_use'], want))
    if 'b1[18]' in out and got['splint'] != out['b1[18]']:
        bad.append(('b1[18]', got['splint'], out['b1[18]']))
    for k in (20, 21, 22):
        made = out.get(f'b1[{k}]') == 0
        if made != got['shelters'][k - 20]:
            bad.append((f'b1[{k}]', got['shelters'][k - 20], made))
    for n in (43, 44, 58):
        key = f'B1[{n}]'
        if key in out and out[key] == 0 and got['place'][n] != 0:
            bad.append((key, got['place'][n], 0))
    if '$0D5E' in out:
        w = 2 if out.get('b2[21]') else out['$0D5E'][1]
        if got['inside'] != w:
            bad.append(('$0D5E', got['inside'], w))
    elif got['inside']:
        bad.append(('$0D5E', got['inside'], 0))
    if '$4BCC step' in out and got['period'] != out['$4BCC step'][1]:
        bad.append(('$4BCC', got['period'], out['$4BCC step'][1]))
    if out.get('B2[9]') == 1 and got['place'][9] != 0:
        bad.append(('tent set down', got['place'][9], 0))
    return bad


# The core's presence test (T05/S00 $552B) answers before the module in the
# game: a shelter here, the AXE in the pack: msg 11 (the ROM case ran the
# module alone).
CORE_FIRST = {'make hut there': [11], 'make igloo there': [11], 'make axe clear': [11],
              'make rock': [11]}           # (b1[17] = 0 in the saved game: the core's msg 11)
NAMES = ('BOW', 'SPEAR', 'CLUB', 'ROCK', 'SPLINT')


def skipped(name):
    for prefix, why in SKIP.items():
        if name.startswith(prefix) and why:
            return why
    return None


def original_cases(results):
    print('ROM cases (build/re_craft/results.json, part 1):')
    done = skip = 0
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        for c in results['isolated']:
            why = skipped(c['name']) or (None if c['module'] != 't10s05' else 'T10/S05: lot 5')
            ctx = None
            if not why:
                ctx = translate(port, c)
                if isinstance(ctx, str):
                    why = ctx
            if why:
                print(f'  {c["name"]}: SKIPPED ({why})')
                skip += 1
                continue
            if c['name'] in CORE_FIRST:
                c['log'] = CORE_FIRST[c['name']]
            if c['name'].startswith('use '):
                # The ROM's USE ran alone: its CARRY (the transaction,
                # stubbed) is taken as accepted; the port's checks the load
                # (lot 14, 16 October 2026): room for it here.
                port.poke('load_limits', [2000 & 255, 2000 >> 8])
            words = c['name'].split()
            command = f'{words[0].upper()} {words[1].upper()}'
            text, got = run(port, command, ctx)
            bad = expect(c, got, text)
            check(c['name'], not bad, str(bad))
            done += 1
    print(f'  {done} cases compared, {skip} skipped')


def game_script(results):
    """Part 2: the messages of the probe's second game (ENTER, EXIT, MAKE of
    every family) in the port, from a woods cell away from the wreck."""
    print('ROM real-game script (results.json, part 2):')
    rows_ = results['game']
    start = next(i for i, r in enumerate(rows_) if r['command'] == 'START (enter, exit)')
    port_skip = {'MAKE TREE', 'MAKE BAIT', 'MAKE SHADOW', 'MAKE STATUS', 'MAKE STICKS',
                 'WALK 1', 'MAKE HUT'}
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        port.reset(port.away)
        text, _ = run(port, 'MAKE HUT', dict(cr_class=1, cr_snow=0))
        check('MAKE HUT (woods): msg 15', TEXTS[15] in text, text)
        for row in rows_[start + 1:]:
            cmd = row['command']
            if cmd in port_skip:
                continue
            want = row['text'].split(' / ')[0].replace('? ', '').split(' > ')[-1].strip()
            want = re.sub(r'`.*', '', want).strip()
            text, _ = run(port, cmd, dict(cr_class=1, cr_snow=0) if cmd.startswith('MAKE') else None)
            ok = want.split('.')[0].split('!')[0] in text
            check(f'{cmd}: "{want}"', ok, text)


def places(port):
    """BOW, SPEAR, CLUB, ROCK, SPLINT as the original's b1: on the ground of
    another cell (BOW, SPEAR, SPLINT: cr_cx/cr_cy) reads $FF."""
    x, y = port.byte('px', 1), port.byte('py', 1)
    out = []
    for i in range(5):
        v = port.byte('cr_b1', i)
        if v == 0 and i in (0, 1, 4) and (port.byte('cr_cx', min(i, 2)), port.byte('cr_cy', min(i, 2))) != (x, y):
            v = 255
        out.append(v)
    return out


def in_use(port):
    """b2[14..17] of the port: FT_BOW, FT_SPEAR, FT_CLUB (the CLUB or the ROCK)."""
    u = port.byte('fg_use')
    return [bool(u & 4), bool(u & 8), bool(u & 16)]


def items_script(results):
    """Part 3: the ROM's transaction script of the second set (results.json
    'items'), from the wreck; a WALK of the ROM moves the player to the same
    cell (relative to the wreck) and leaves the cell as the walk step does
    (forage_here: cr_still 0; the time clears the "in use" flags)."""
    print('ROM transaction script of the second set (results.json, part 3):')
    rows_ = results['items']
    x0, y0 = rows_[0]['state']['here']
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        wx, wy = port.wreck
        cell = lambda h: (wx + h[0] - x0, wy + h[1] - y0)          # noqa: E731
        port.reset(port.wreck)
        for n in (9, 60):                                           # (DROP TENT, DROP ROPE)
            port.poke('it_place', port.place[n], n)
        check('START: the ROCK on the ground of the wreck (b1[17] = 0)',
              places(port) == rows_[0]['state']['b1'], places(port))
        for k, row in enumerate(rows_[1:]):
            cmd, want = row['command'], row['state']
            if cmd == 'LOOK BACK':
                continue
            if cmd.startswith('WALK'):
                port.move(cell(want['here']))
                port.poke('fg_x', cell(want['here'])[0])   # (forage_here of the walk step)
                port.poke('fg_y', cell(want['here'])[1])
                port.poke('cr_still', 0)
                port.poke('fg_use', 0)
                continue
            if cmd.startswith('made'):
                x, y = cell(want['here'])
                port.poke('cr_b1', [0, 0, 0, want['b1'][3], 0], 0)
                port.poke('cr_still', 1)                    # (made on the new cell)
                port.poke('cr_cx', [x] * 3)
                port.poke('cr_cy', [y] * 3)
                continue
            text, _ = run(port, cmd)
            rom = row['text']
            bad = []
            if places(port) != want['b1']:
                bad.append(('b1', places(port), want['b1']))
            b2 = want['b2']
            if in_use(port) != [bool(b2[0]), bool(b2[1]), bool(b2[2] or b2[3])]:
                bad.append(('b2', in_use(port), b2[:4]))
            for m, key in ((11, 'YOU ALREADY HAVE'), (1, 'NOT AVAILABLE')):
                if (key in rom) != (TEXTS[m] in text):
                    bad.append(('msg', m, text))
            if ('TRY ANOTHER VERB' in rom) != ("CAN'T WEAR" in text):
                bad.append(('WEAR', text))
            if 'sel3' in want and bool(port.byte('medical_actions', 2)) != bool(want['sel3']):
                bad.append(('selector 3', port.byte('medical_actions', 2), want['sel3']))
            check(f'{k + 1:2d} {cmd}: {want["b1"]}', not bad, str(bad))


def craft_cells(port):
    return [port.byte('cr_b1', i) for i in range(12)] + [port.byte('cr_cx', i) for i in range(6)]


def port_checks():
    print('The port:')
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        port.reset(port.away)
        run(port, 'MAKE BOW', dict(cr_class=1, cr_snow=0))
        run(port, 'MAKE HUT', dict(cr_class=1, cr_snow=0))
        s.step('key:INVENTORY')
        s.step('press:\\r')
        s.step(L.until('keyboard_wait', 60000))
        screen = text_screen(s.step('peek:0400:1024').data)
        local = '\n'.join(r[:40] for r in screen[3:14])
        check('OBJECTS, LOCAL: the BOW (50 OZ) and the ROCK (100 OZ), not the HUT (no object)',
              'BOW            50 OZ' in local and 'ROCK           100 OZ' in local and 'HUT' not in local,
              '\n'.join(screen))
        s.step('key:\x1b')
        s.step(IDLE)
        text, _ = run(port, 'USE BOW')
        check('USE BOW with the load of the start (772 + 50 > 815 oz): in use, left on the ground, '
              'TOO MUCH WEIGHT (the original: msg 7)', port.byte('cr_b1') == 0 and port.byte('fg_use') & 4
              and 'WEIGHT: NEED 50 OZ. FREE 43 OZ.' in text, text)
        run(port, 'DROP TENT')
        text, _ = run(port, 'USE BOW')
        check('USE BOW once the TENT is down: in hand, in use (msg 10)', port.byte('cr_b1') == 3
              and port.byte('fg_use') & 4 and TEXTS[10] in text, text)
        # KILL GAME with the BOW (means 20): p = .2 by day; the module's
        # generator imposed through its seed is test_forage.py's matter: here
        # the BOW is chosen and its flag cleared, 15 minutes pass.
        port.poke('fg_b2', 0, 4)
        port.poke('resource_seen', port.byte('resource_seen') | 1)
        x, y = port.byte('px', 1), port.byte('py', 1)
        port.poke('fg_x', x)
        port.poke('fg_y', y)
        text, _ = run(port, 'KILL GAME')
        check('KILL GAME with the BOW: the flag cleared, a result', port.byte('fg_use') & 4 == 0
              and ('BITTEN THE DUST' in text or 'MISSED. TRY AGAIN.' in text), text)
        run(port, 'USE BOW')
        run(port, 'WAIT 1')
        check('the BOW no longer in use once time passes', port.byte('fg_use') & 4 == 0)
        port.move((x + 1, y))
        text, _ = run(port, 'USE HUT')
        check('USE HUT on another cell: msg 1', TEXTS[1] in text, text)
        port.move((x, y))
        run(port, 'USE HUT')
        check('USE HUT: inside, 15-minute steps', port.byte('shelter_inside') == 1, port.byte('shelter_inside'))
        run(port, 'EXIT HUT')
        check('EXIT HUT: outside', port.byte('shelter_inside') == 0)
    walk_and_save()
    attack_checks()


def walk_and_save():
    """A real walk (forage_here, cr_here), then SAVE/RESTORE of the second
    set on its cells, on a private copy of the disk."""
    import shutil
    import tempfile
    from test_save import Game
    work = Path(tempfile.mkdtemp())
    disk = work / 'craft.po'
    shutil.copy(DISK, disk)
    with a2test.Session(disk, timeout=900) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        g = Game(s)
        x, y = port.byte('px', 1), port.byte('py', 1)
        port.poke('cr_b1', [255, 0, 0, 0, 0])                    # SPEAR, CLUB, ROCK, SPLINT here
        port.poke('cr_cx', [x, x, x])
        port.poke('cr_cy', [y, y, y])
        g.type('WALK 1 H')
        nx, ny = port.byte('px', 1), port.byte('py', 1)
        check('a real walk leaves the cell: cr_still 0 (forage_here)', (nx, ny) != (x, y)
              and port.byte('cr_still') == 0, (x, y, nx, ny, port.byte('cr_still')))
        text, _ = run(port, 'GET CLUB')
        water = s.step(f'peek:{L["cr_b1"] + 3:04X}:1').data[0]
        check('then the CLUB is lost (msg 1), a ROCK lies on the new land cell, the SPEAR and the SPLINT '
              'stay on theirs', TEXTS[1] in text and places(port) == [255, 255, 255, water, 255]
              and water in (0, 255) and port.byte('cr_still') == 1, (text, places(port)))
        run(port, 'DROP TENT')                                  # (lot 14: room for 100 oz)
        text, _ = run(port, 'GET ROCK')
        check('GET ROCK there: in hand', port.byte('cr_b1', 3) == 3 or water == 255, text)
        port.poke('cr_b1', [0, 2, 255, 3, 0])                    # BOW here, SPEAR packed, ROCK in hand
        port.poke('cr_cx', [nx, x, x])                           # (the SPLINT on the first cell)
        port.poke('cr_cy', [ny, y, y])
        port.poke('cr_still', 0)
        before = craft_cells(port)
        g.type('SAVE 1')
        check('SAVE 1 with the crafted things', g.result().startswith('GAME 1 SAVED.'), g.result())
        port.poke('cr_b1', [255] * 12)
        port.poke('cr_cx', [255] * 6)
        g.type('RESTORE 1')
        check('RESTORE 1: places, cr_still and the cells of the BOW, SPEAR, SPLINT come back',
              g.result().startswith('GAME 1 RESTORED.') and craft_cells(port) == before,
              (g.result(), before, craft_cells(port)))
        port.move((x, y))
        check('back on the first cell: the SPLINT is there, the BOW is not', places(port)[4] == 0
              and places(port)[0] == 255, places(port))
    shutil.rmtree(work, ignore_errors=True)


def attack_checks():
    """ATTACK BEAR with each means in use (T0F/S07 $590F: GUN 21, BOW 20,
    SPEAR 19, AXE or KNIFE 18, CLUB or ROCK 17; the flag cleared): the two
    thresholds OUTDOOR rolls (outdoor_roll), against the ROM's fiche of the
    Sierra (build/regions/fauna.json: injury .02 x row[m], success .005 x
    row[m + 6], quantized as tools/build_disk.py threshold)."""
    fauna = HERE / 'build/regions/fauna.json'
    if not fauna.exists():
        print(f'  {fauna} missing: ATTACK thresholds not compared')
        return
    sierra = json.loads(fauna.read_text())['regions']['2']['species'][0]
    q = lambda p: 0 if p <= 0 else min(255, int(p * 256) + 1)      # noqa: E731
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        x, y = port.byte('px', 1), port.byte('py', 1)
        for label, means, setup, cleared in (
                ('GUN', 21, lambda: port.poke('camp_use', 128), lambda: port.byte('camp_use') & 128 == 0),
                ('BOW', 20, lambda: port.poke('fg_use', 4), lambda: port.byte('fg_use') == 0),
                ('SPEAR', 19, lambda: port.poke('fg_use', 8), lambda: port.byte('fg_use') == 0),
                ('AXE', 18, lambda: (port.poke('care_tools', 1), port.poke('care_tool_x', x),
                                     port.poke('care_tool_y', y)), lambda: port.byte('care_tools') == 0),
                ('ROCK', 17, lambda: port.poke('fg_use', 16), lambda: port.byte('fg_use') == 0),
                ('BOW and CLUB', 20, lambda: port.poke('fg_use', 20), lambda: port.byte('fg_use') == 16),
                ('none (the AXE in the pack)', 18, lambda: None, lambda: True)):
            for name, v in (('camp_use', 0), ('fg_use', 0), ('care_tools', 0), ('shelter_inside', 0),
                            ('tree_in', 0), ('animal_kind', 6), ('animal_x', x), ('animal_y', y)):
                port.poke(name, v)
            setup()
            s.step(f'watch:{L["outdoor_roll"]:04X}')
            s.step('key:ATTACK BEAR')
            s.step('press:\\r')
            out = s.step(L.until('do_outdoor_done', 60000)).out
            s.step('unwatch')
            rolls = [int(a, 16) for a in re.findall(r'^watch [0-9A-F]{4} A=([0-9A-F]{2})', out, re.M)][:2]
            want = [q(.02 * sierra['injury'][str(means)]), q(.005 * sierra['success'][str(means)])]
            check(f'ATTACK BEAR, {label} in use: means {means}, thresholds {want}, flag cleared',
                  rolls == want and cleared(), (rolls, want))
            s.step(L.until('idle', 60000))


def main():
    original = '--original' in sys.argv
    if not RESULTS.exists():
        if original:
            raise SystemExit(f'{RESULTS} is missing: python3 tools/re_craft_probe.py '
                             '(needs build/JOURNEY.dsk, build/game.bin: make extract)')
        print(f'{RESULTS} missing: the ROM cases are skipped')
    if RESULTS.exists():
        results = json.loads(RESULTS.read_text())
        original_cases(results)
        game_script(results)
        if 'items' in results:
            items_script(results)
        elif original:
            raise SystemExit(f'{RESULTS} has no part 3: python3 tools/re_craft_probe.py')
    if not original:
        port_checks()
    if fails:
        raise SystemExit(f'CRAFT: {len(fails)} failures: {fails}')
    print('CRAFT: OK')


if __name__ == '__main__':
    main()
