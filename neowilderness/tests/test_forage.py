#!/usr/bin/env python3
"""FORAGE, lot 4 (docs/FORAGE.md): hunting, fishing, gathering, meals.

Step 1 (section 4): the random draws of the food discoveries
(module_resource_results, ITEMS since step 2) follow the original T0D/S00,
measured on the ROM by tools/re_forage_probe.py: one draw for the quantity
(4 + INT(32 RND) oz), one for the quality, and for FRUIT a third one when
.2 <= quality < .5; the eighth resource is WILD NUTS (2 calls).

Steps 2-5: the port against the ROM's measures (build/re_forage/results.json,
part 1: 134 cases of the modules alone; part 3: the spoilage clock), each
case replayed in the game: the state of the original translated into the
port's (src/forage.s forage_state), the command typed with its numbers and
keys, RND imposed by a stub (the FORAGE module's fr_rnd, or SIM's
weather_random for the discoveries) that also counts the draws, the
module's decisions read at forage_ran (before its time passes), then the
messages, ounces, records, counters, credits and minutes compared.
Cases the port does not play are listed with their reason (SKIPPED).

  python3 tests/test_forage.py              all of it (the ROM values if
                                            results.json is there, else the
                                            same values written here)
  python3 tests/test_forage.py --original   the ROM cases only (fails if
                                            results.json is missing)
"""
import json
import math
import re
import sys
from common import HERE, L, DISK, a2test, idle_bytes, fp, text_screen
from gendata import fp as encode
from test_input import IDLE

M = 67099547                    # src/weather.s wf_modulus
STEP = pow(2, 13, M)            # one draw: seed * 8192 mod m
MAP = 0x7000
FOODS = {2: 'INSECTS', 3: 'FRUIT', 4: 'CACTI', 5: 'MUSHROOMS', 6: 'PLANTS', 7: 'NUTS'}
RESULTS = HERE / 'build/re_forage/results.json'
OUT_VALUE = (HERE / 'build/wildout.bin').read_bytes()[L['out_value'] - 0x5800:][:4]
STUB = 0x9500                   # overlay_text (SCRATCH): free during these commands
TABLE, COUNT, INDEX = STUB + 0x40, STUB + 0x3E, STUB + 0x3F
FORAGE_RUN = 0x9600
FG_CGND, FG_CPROV = 11, 22
fails = []


def check(name, ok, detail=''):
    print(f'  {name}: {"OK" if ok else "FAIL"}' + (f' {detail}' if not ok and detail else ''))
    if not ok:
        fails.append(name)


def seed_for(quality, position=2):
    """The seed whose draw number `position` (1 = the next) is `quality`."""
    s = round(quality * M)
    inv = pow(STEP, -1, M)
    for _ in range(position):
        s = s * inv % M
    return s


def draws(before, after):
    s = before
    for n in range(8):
        if s == after:
            return n
        s = s * STEP % M
    raise AssertionError((before, after))


# ---------------------------------------------------------------------------
# Step 1: the discovery draws (kept as written for step 1)
# ---------------------------------------------------------------------------
def discovery_draws():
    cases = [(3, .1999, 2), (3, .2001, 3), (3, .4999, 3), (3, .5001, 2), (7, .05, 2), (7, .5, 2)]
    cases += [(x, .5, 2) for x in (2, 4, 5, 6)]
    original = idle_bytes(3)
    a = L['native_resource_results']
    results = []
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        for x, quality, want in cases:
            seed = seed_for(quality)
            s.step(f'poke:{MAP + 36:04X}:{1 << x:02X}')
            for i in range(4):
                s.step(L.poke('weather_seed', seed >> 8 * i & 255, i))
            for i, b in enumerate((0x20, a & 255, a >> 8)):     # JSR, then idle again
                s.step(L.poke('idle', b, i))
            s.step(L.until('native_resource_results', 20000))   # (idle + 3 is also the loop's BPL)
            s.step(f'until:{L["idle"] + 3:04X}:20000')
            for i, b in enumerate(original):
                s.step(L.poke('idle', b, i))
            after = int.from_bytes(s.step(L.peek('weather_seed', 4)).data, 'little')
            qty = s.step(f'peek:{MAP + 26 + x:04X}:1').data[0]
            n = draws(seed, after)
            first = seed * STEP % M / M
            assert n == want, (FOODS[x], quality, n, want)
            assert qty == 4 + int(32 * first), (FOODS[x], qty, first)
            results.append((FOODS[x], quality, n, qty))
        s.step(f'poke:{MAP + 36:04X}:00')
    for food, quality, n, qty in results:
        print(f'  {food:9} quality {quality:.4f}: {n} draws, {qty} oz: OK')
    print('FORAGE step 1, discovery draws as the ROM: OK')


# ---------------------------------------------------------------------------
# The port's state (src/forage.s)
# ---------------------------------------------------------------------------
def pokes(s, addr, data):
    """a2shot pokes one byte a step: only the bytes that differ."""
    data = bytes(data)
    now = s.step(f'peek:{addr:04X}:{len(data)}').data
    for i, (a, b) in enumerate(zip(now, data)):
        if a != b:
            s.step(f'poke:{addr + i:04X}:{b:02X}')


def word(v):
    return [v & 255, v >> 8 & 255]


def signed(lo, hi):
    v = hi << 8 | lo
    return v - 65536 if v >= 32768 else v


class Port:
    """A session at idle, with readers and writers of the lot's state."""

    def __init__(self, s):
        self.s = s
        lo = (HERE / 'build/wildlo.bin').read_bytes()
        a, b = L['forage_state'], L['forage_state_end']
        self.pristine = lo[a - 0x1000:b - 0x1000]
        self.prov = {name: s.step(L.peek(name, 76)).data
                     for name in ('it_place', 'it_oz_lo', 'it_oz_hi', 'it_gnd_lo', 'it_gnd_hi',
                                  'it_pack_lo', 'it_pack_hi', 'it_x', 'it_y')}

    def poke(self, name, value, k=0):
        for i, v in enumerate(value if isinstance(value, (bytes, bytearray, list)) else [value]):
            self.s.step(L.poke(name, v & 255, k + i))

    def byte(self, name, k=0):
        return self.s.step(L.peek(name, 1, k)).data[0]

    def bytes(self, name, n):
        return self.s.step(L.peek(name, n)).data

    def float(self, name, k=0):
        return fp(self.s.step(L.peek(name, 5, k)).data)

    def cell(self):
        return self.bytes('px', 2)[1], self.bytes('py', 2)[1]

    def reset(self):
        """The lot's state of the saved game, the player's cell its piles'
        cell, no fire, no tool in use, daylight, nothing pending."""
        s = self.s
        pokes(s, L['forage_state'], self.pristine)
        x, y = self.cell()
        self.poke('fg_x', x)
        self.poke('fg_y', y)
        for name in ('fire_on', 'camp_use', 'care_tools', 'resource_seen', 'fg_after'):
            self.poke(name, 0)
        self.poke('light', 1)
        self.poke('injury_active', 0, 10)
        self.poke('injury_prevented', 0, 10)
        self.poke('al_last', 100, 16)
        self.poke('mn_mode', 0)             # the typed line, not the grid
        self.poke('al_forced', 0)
        for name in ('s_defw', 's_deff', 's_defr'):     # rested and fed: no alert hides
            for i in range(5):                          # the result (134 cases in a row)
                self.poke(name, 0, i)
        for name, data in self.prov.items():
            pokes(s, L[name] + 23, data[23:38])
        s.step(f'poke:{MAP + 12:04X}:26')        # M_LAT: the Sierra's 38

    def counter(self, i):
        return signed(self.byte('fg_cl', i), self.byte('fg_ch', i))

    def set_counter(self, i, v):
        self.poke('fg_cl', v, i)
        self.poke('fg_ch', v >> 8, i)

    def pile(self, j):
        return dict(b1=self.byte('fg_b1', j), w7=self.byte('fg_gl', j) | self.byte('fg_gh', j) << 8,
                    w8=self.byte('fg_pl', j) | self.byte('fg_ph', j) << 8)

    def set_pile(self, j, w7=None, w8=None, b1=None):
        if w7 is not None:
            self.poke('fg_gl', w7, j)
            self.poke('fg_gh', w7 >> 8, j)
        if w8 is not None:
            self.poke('fg_pl', w8, j)
            self.poke('fg_ph', w8 >> 8, j)
        if b1 is not None:
            self.poke('fg_b1', b1, j)

    def stub(self, values):
        """weather_random / fr_rnd -> the next value of `values` (counted)."""
        code = bytes.fromhex(f'AD{INDEX & 255:02X}{INDEX >> 8:02X} 18 69{TABLE & 255:02X} A0{TABLE >> 8:02X}'
                             ' 20F9EA'
                             f' AD{INDEX & 255:02X}{INDEX >> 8:02X} 18 6905 8D{INDEX & 255:02X}{INDEX >> 8:02X}'
                             f' EE{COUNT & 255:02X}{COUNT >> 8:02X} 60'.replace(' ', ''))
        table = b''.join(encode(v) for v in values) or encode(.5)
        data = code.ljust(0x3E, b'\0') + b'\0\0' + table
        pokes(self.s, STUB, data)

    def stub_count(self):
        return self.s.step(f'peek:{COUNT:04X}:1').data[0]

    def jump(self, label):
        """JMP STUB at label (the module's or SIM's generator)."""
        pokes(self.s, L[label], (0x4C, STUB & 255, STUB >> 8))


def rows(s):
    """The result column (rows 20-23), words joined."""
    return ' '.join(' '.join(line[:39].split()) for line in text_screen(s.step('peek:0400:1024').data)[20:24])


def run(port, command, answers=(), rnd=None, decisions=None):
    """The command, its answers (numbers end with RETURN, a letter is a key),
    RND imposed in the module when rnd is a list; decisions() is called at
    forage_ran (the module's state before its time). Returns (screens, final
    result text, decisions' value or None, draws or None)."""
    s = port.s
    s.step(f'key:{command}')
    s.step('press:\\r')
    s.step(L.until('do_command', 40000))    # the line is read (not idle's poll)
    if rnd is not None:
        s.step(f'until:{FORAGE_RUN:04X}:40000')
        port.stub(rnd)
        port.jump('fr_rnd')
    answers, screens, got, count = list(answers), [], None, None
    ran, kw, idle = L['forage_ran'], L['keyboard_wait'], L['idle']
    asked = None
    for _ in range(400):
        r = s.step(f'until:{ran:04X},{kw:04X},{idle:04X}:60000')
        pc = int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16)
        if pc == ran:
            got = decisions() if decisions else None
            count = port.stub_count() if rnd is not None else None
            screens.append(rows(s))             # the module's own words, before its time
            for _ in range(8):              # its time: a full result waits for a key
                r = s.step(f'until:{idle:04X},{kw:04X}:60000')
                if int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16) == idle:
                    break
                s.step('key: ')
            break
        if pc == idle:
            break
        # A question: the reader waits and the message rows changed (the
        # keys of the previous answer echo on row 23 only).
        question = '\n'.join(text_screen(s.step('peek:0400:1024').data)[20:23])
        if question == asked:
            s.step('wait:2')
            continue
        asked = question
        s.step('wait:30')                       # the reader is ready: no key lost
        screens.append(rows(s))
        if not answers:
            fails.append(f'{command}: unexpected question {screens[-1]!r}')
        a = answers.pop(0) if answers else '\x1b'
        s.step(f'key:{a}')
        if len(a) > 1 or a.isdigit() or a.startswith('.'):
            s.step('press:\\r')
    else:
        raise AssertionError(f'{command}: too many prompts')
    return screens, rows(s), got, count


# ---------------------------------------------------------------------------
# The ROM's cases, translated
# ---------------------------------------------------------------------------
b1, b2, b3, b4 = 0x45C0, 0x45DC, 0x45F8, 0x4614
w5, w7, w8, w9, w10, w11 = 0x4630, 0x46A0, 0x46D8, 0x4710, 0x4748, 0x4780
B1, B2, W5, W7, W8, W9, W10, W11 = 0x404C, 0x4098, 0x417C, 0x42AC, 0x4344, 0x43DC, 0x4474, 0x450C
VERBS = {1: 'CATCH', 4: 'SKIN', 11: 'COOK', 12: 'EAT', 17: 'KILL', 18: 'SCARE', 31: 'CUT', 35: 'TASTE'}
NOUNS = {23: 'NUTS', 28: 'CHEESE', 33: 'BOLOGNA', 76: 'BEAR', 77: 'COUGAR', 78: 'RATTLESNAKE',
         80: 'GAME', 81: 'FISH', 82: 'INSECTS', 83: 'FRUIT', 84: 'CACTI', 85: 'MUSHROOMS', 86: 'PLANTS',
         135: 'FOOD'}
# Messages of the original (msg n) as the port prints them (src/frg.s, the bank).
TEXTS = {1: 'SORRY, THAT ITEM IS NOT AVAILABLE.', 2: "YOU'RE NOT MAKING MUCH SENSE.",
         10: 'OK, WHAT NEXT?', 11: 'YOU ALREADY HAVE.', 17: 'TRY TO BE MORE SPECIFIC.',
         25: 'USE THE APPROPRIATE ITEM FIRST.', 27: 'SPECIFY TIME IN HOURS.',
         31: 'NOURISHMENT MAKES A LOT OF SENSE.', 32: 'PLEASE SPECIFY AMOUNT IN OUNCES.',
         38: 'YOU MUST KILL THE', 39: "THAT'S NOT VERY WISE.", 47: 'HMM. UNRIPE RED FRUIT.',
         56: 'YOU WERE SUCCESSFUL!', 64: 'YOU CANNOT EXCEED THE AVAILABLE AMOUNT OF',
         65: 'YOU NEED A FIRE TO BOIL OR COOK THINGS.',
         66: 'USE THE PROPER DEVICE TO CATCH, OR WEAPON TO KILL.', 67: 'SORRY, BETTER LUCK NEXT TIME.',
         70: 'HAS JUST BITTEN THE DUST!', 71: 'IS THE FOOD FROM YOUR PACK [P] OR FROM THE GROUND [G]?',
         87: "DON'T BE RIDICULOUS!", 89: 'AHA! NICE RIPE RED FRUIT.', 93: 'IT APPEARS TO BE UNRIPE WHITE FRUIT.',
         94: 'IT IS SOME FORM OF RIPE WHITE FRUIT.', 119: 'YOUR FISH HAS FLABBY SKIN AND SUNKEN EYES.',
         120: 'YOUR FISH IS ODDLY SHAPED.', 121: 'YOUR FISH HAS NO SCALES.',
         122: 'YOUR FISH IS CONVENTIONAL IN SHAPE AND HAS SCALES.',
         123: 'ALTHOUGH NOT THE NECTAR OF THE GODS, THE TASTE IS OKAY.',
         124: 'IT SMELLS AND TASTES LIKE SPOILED FOOD.', 125: 'THE TASTE IS VERY BITTER.',
         126: 'THERE IS A SHARP STINGING SENSATION ON YOUR TONGUE.',
         183: 'THESE PLANTS HAVE A MILKY COLORED SAP.', 184: 'YOU NOTICE SILKY WINDBORNE SEEDS.',
         198: 'SORRY. GET HIDE FROM WILD ANIMALS OR SMALL GAME.',
         199: 'YOU NOW HAVE SOME HIDE. SEE INVENTORY FOR AMOUNT.', 200: 'TO OBTAIN ANY HIDE.'}
PROMPTS = (27, 32, 71)
SKIP = {
    'scare bear': 'the animals: OUTDOOR (lot 11, fauna)',
    'kill bear gun': 'KILL BEAR is OUTDOOR\'s, not the FORAGE module (its means 21: the carcass cases, '
                     'tests/test_craft.py attack_checks)',
    'kill bear gun light 1 rnd 0.3501': "a failed kill and the bear's theft: OUTDOOR (lot 11)",
    'discover mushrooms': None,         # (W10[1], the original's stray write, is not compared)
}
FIDELITY = ('eat cheese', 'eat bologna', 'eat starving', 'eat 49 oz', 'eat 0 oz')


def skipped(name):
    for prefix, why in SKIP.items():
        if name.startswith(prefix) and why:
            if prefix == 'kill bear gun' and 'light' in name:
                continue
            return why
    return None


def apply_pokes(port, c):
    """The case's pokes on the original's tables, onto the port's state."""
    seen = 0
    for addr, data in c['pokes']:
        v = data[0] | (data[1] << 8 if len(data) > 1 else 0)
        if addr == 0x0D5D:
            port.poke('light', v)
        elif addr == 0x48A9:
            port.poke('al_last', v, 16)
        elif addr == 0x60A8:
            port.s.step(f'poke:{MAP + 12:04X}:{v:02X}')
        elif addr == 0x4ADA:
            port.poke('fauna_env', v)
        elif 0x4AE0 <= addr < 0x4AE6:
            k = addr - 0x4AE0 + 1
            port.poke('fg_skin', port.byte('fg_skin') | 1 << (k - 1))
            if k <= 4:                          # V: the port keeps it from the kill
                port.poke('fg_v', OUT_VALUE[k - 1], k - 1)
        elif B2 < addr < B2 + 76:
            n = addr - B2
            if n == 57:
                port.poke('camp_use', port.byte('camp_use') | 128)
            elif n in (58, 59):
                port.poke('care_tools', port.byte('care_tools') | (n - 57))
                x, y = port.cell()
                port.poke('care_tool_x', x)
                port.poke('care_tool_y', y)
            elif n == 67:
                port.poke('fg_use', port.byte('fg_use') | 2)
            elif n == 71:
                port.poke('camp_use', port.byte('camp_use') | 16)
            elif n == 72:
                port.poke('fg_use', port.byte('fg_use') | 1)
        elif b1 < addr <= b1 + 19:
            k = addr - b1
            if k == 13:
                port.poke('fire_on', 1 if v == 0 else 0)
            elif k <= 11 or k == 19:
                port.poke('fg_b1', v, 11 if k == 19 else k - 1)
        elif b2 + 14 <= addr <= b2 + 16:        # BOW, SPEAR, CLUB in use (lot 3: fg_use)
            port.poke('fg_use', port.byte('fg_use') | 4 << (addr - b2 - 14))
        elif b2 < addr <= b2 + 6:
            k = addr - b2
            port.poke('fg_b2', v, k - 1)
            if v == 0 and k >= 5:
                seen |= k - 4
        elif b4 < addr <= b4 + 11:
            port.poke('fg_pt', v, addr - b4 - 6)
        elif w7 < addr <= w7 + 38:
            k = (addr - w7) // 2
            port.set_pile(11 if k == 19 else k - 1, w7=v)
        elif w8 < addr <= w8 + 38:
            k = (addr - w8) // 2
            port.set_pile(11 if k == 19 else k - 1, w8=v)
        elif w5 < addr <= w5 + 38:
            pass                                # the total: ground + pack
        elif w10 + 44 <= addr <= w10 + 52:      # w10[22..26]: ground of 7..11
            port.set_counter(FG_CGND + (addr - w10) // 2 - 16, v)
        elif w11 < addr <= w11 + 22:            # w11[1..11]: pack
            port.set_counter((addr - w11) // 2 - 1, v)
        elif w11 + 44 <= addr <= w11 + 54:      # w11[22..27]: ground of 1..6
            port.set_counter(FG_CGND + (addr - w11) // 2 - 22, v)
        elif W9 + 128 <= addr <= W9 + 140:
            port.poke('fg_gt', v, (addr - W9) // 2 - 64)
        elif W10 + 128 <= addr <= W10 + 140:
            port.poke('fg_gx', v, (addr - W10) // 2 - 64)
        elif W11 + 128 <= addr <= W11 + 140:
            port.poke('fg_gp', v, (addr - W11) // 2 - 64)
        elif W11 + 46 <= addr <= W11 + 74:      # W11[23..37]
            port.set_counter(FG_CPROV + (addr - W11) // 2 - 23, v)
        elif W11 + 82 <= addr <= W11 + 100:     # W11[41..50]
            port.set_counter(37 + (addr - W11) // 2 - 41, v)
        elif addr == B1 + 23:
            port.poke('it_place', 0 if v == 0 else v, 23)
        elif addr in (W5 + 46, W7 + 46, W8 + 46):
            name = {W5 + 46: 'it_oz', W7 + 46: 'it_gnd', W8 + 46: 'it_pack'}[addr]
            port.poke(name + '_lo', v, 23)
            port.poke(name + '_hi', v >> 8, 23)
            if addr == W7 + 46:
                x, y = port.cell()
                port.poke('it_x', x, 23)
                port.poke('it_y', y, 23)
        elif 0x0D9D <= addr <= 0x0DA4:
            pass                                # discovery events: the harness
        else:
            raise AssertionError(f'{c["name"]}: no translation for ${addr:04X}')
    if seen:
        port.poke('resource_seen', port.byte('resource_seen') | seen)


def reads(port, keys):
    """The port's values of the ROM's 'out' keys (None: not compared)."""
    out = {}
    for key in keys:
        m = re.fullmatch(r'([bwBW])(\d+)\[(\d+)\]', key)
        v = None
        if m:
            t, n, i = m[1], int(m[2]), int(m[3])
            if t == 'b' and n == 1:
                v = port.byte('fg_b1', 11 if i == 19 else i - 1) if i <= 11 or i == 19 else None
            elif t == 'b' and n == 2 and i <= 6:
                v = port.byte('fg_b2', i - 1)
            elif t == 'b' and n == 4:
                v = port.byte('fg_pt', i - 6)
            elif t == 'w' and n in (5, 7, 8) and (i <= 11 or i == 19):
                p = port.pile(11 if i == 19 else i - 1)
                v = p['w7'] + p['w8'] if n == 5 else p[f'w{n}']
            elif t == 'w' and n == 11 and i <= 11:
                v = port.counter(i - 1)
            elif t == 'w' and n == 11 and 22 <= i <= 27:
                v = port.counter(FG_CGND + i - 22)
            elif t == 'w' and n == 10 and 22 <= i <= 26:
                v = port.counter(FG_CGND + i - 16)
            elif t == 'W' and n in (9, 10, 11) and 64 <= i <= 70:
                v = port.byte({9: 'fg_gt', 10: 'fg_gx', 11: 'fg_gp'}[n], i - 64)
            elif t == 'W' and n == 11 and 23 <= i <= 37:
                v = port.counter(FG_CPROV + i - 23)
            elif t == 'W' and n == 11 and 41 <= i <= 50:
                v = port.counter(37 + i - 41)
            elif t == 'B' and n == 2:
                v = {57: lambda: port.byte('camp_use') >> 7, 59: lambda: port.byte('care_tools') >> 1 & 1,
                     67: lambda: port.byte('fg_use') >> 1 & 1, 71: lambda: port.byte('camp_use') >> 4 & 1,
                     72: lambda: port.byte('fg_use') & 1}.get(i, lambda: None)()
            elif t == 'B' and n == 1 and i == 23:
                v = port.byte('it_place', 23)
            elif t == 'W' and n in (5, 7, 8) and i == 23:
                name = {5: 'it_oz', 7: 'it_gnd', 8: 'it_pack'}[n]
                v = port.byte(name + '_lo', 23) | port.byte(name + '_hi', 23) << 8
        elif key.startswith('$4AE0['):
            v = port.byte('fg_skin') >> int(key[6]) & 1
        out[key] = v
    return out


def command_of(c):
    """The verb from the case's name (results.json keeps page zero after the
    run: the module rewrites $03), the noun from $05."""
    word = c['name'].split()[0].upper()
    return f'{word} {NOUNS[c["zp"]["05"]]}'


def answers_of(c, command):
    """Numbers and keys in the order the module asks them ($4D39's answer:
    EAT/COOK 0 pack, TASTE 0 ground)."""
    a = [str(c['num'])]
    key = None
    if command.startswith(('EAT', 'COOK')):
        key = 'P' if c['yes'] == 0 else 'G'
    elif command.startswith('TASTE'):
        key = 'G' if c['yes'] == 0 else 'P'
    return a, key, c['hours']


def original_cases(results):
    print('ROM cases (build/re_forage/results.json, part 1):')
    done = skip = 0
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        for c in results['isolated']:
            why = skipped(c['name'])
            if why:
                print(f'  {c["name"]}: SKIPPED ({why})')
                skip += 1
                continue
            port.reset()
            if c['module'] == 't0ds00':
                discovery_case(port, c)
            elif c['module'] == 't06s04':
                carcass_case(port, c)
            else:
                module_case(port, c)
            done += 1
    print(f'  {done} cases compared, {skip} skipped')


def compare(name, port, c, got, extra=()):
    bad = []
    for key, want in c['out'].items():
        v = got.get(key)
        if v is None:
            continue
        want = want[1] if isinstance(want, list) else want
        if isinstance(want, float) or isinstance(v, float):
            if abs(v - want) > 1e-3 * max(1, abs(want)):
                bad.append((key, v, want))
        elif v != want:
            bad.append((key, v, want))
    bad += list(extra)
    check(name, not bad, str(bad))


# The core's availability test (T05/S00 $523F) answers before the module in
# the game: an absent object is msg 1 there (the ROM case ran the module alone).
CORE_FIRST = {'kill game absent': [1], 'taste bear absent': [1]}


def module_case(port, c):
    if c['name'] in CORE_FIRST:
        c['log'] = CORE_FIRST[c['name']]
    # Lot 4 step 5: EAT of the provisions under the original's rules
    # (fg_fidelity, FORAGE_FIDELITY = 0 in the shipped image).
    port.poke('fg_fidelity', 1 if c['name'].startswith(FIDELITY) else 0)
    apply_pokes(port, c)
    command = command_of(c)
    numbers, key, hours = answers_of(c, command)
    ans = []
    log = [m for m in c['log']]
    for m in log:
        if m == 32:
            ans.append(numbers.pop(0) if numbers else '0')
        elif m == 71:
            ans.append(key)
        elif m == 27:
            ans.append(hours or '0')
    before = dict(e=port.float('s_eaten'), w=port.float('s_defw'), f=port.float('s_deff'),
                  r=port.float('s_defr'), salt=signed(*port.bytes('exposure_counter', 2)),
                  elap=port.float('s_elap'))
    keys = list(c['out'])

    def decisions():
        got = reads(port, keys)
        got['$4BC6 minutes'] = port.byte('camp_minutes') | port.byte('camp_minutes', 1) << 8
        got['A1[22] water deficit'] = port.float('s_defw') - before['w']
        got['A1[23] food deficit'] = port.float('s_deff') - before['f']
        got['A1[24] rest deficit'] = port.float('s_defr') - before['r']
        got['$4BDC kcal eaten'] = port.float('s_eaten') - before['e'] + 1000
        got['A1[17] last meal'] = port.float('s_last', 5) - before['elap']
        got['A1[18] last rest'] = port.float('s_last', 10) - before['elap']
        got['$4A4A salt'] = signed(*port.bytes('exposure_counter', 2)) - before['salt']
        poisoned = port.byte('injury_active', 10)
        got['poisoned'] = poisoned
        eff = port.byte('fg_eff')
        got['effort'] = (eff, port.float('s_metabolic'))
        got['med'] = port.byte('camp_med')
        return got
    rnd = c['rnd'] if c['rnd'] else []
    screens, final, got, count = run(port, command, ans, rnd, decisions)
    got = got or {}
    extra = []
    # T0E/S02 (docs/FORAGE.md 9) takes the ounces of a meal off its pile:
    # the port's module does it before forage_ran, the ROM's case did not.
    if command.startswith('EAT') and c['exit'] == '$4D00':
        pile = next((k for k in c['out'] if re.fullmatch(r'[wW]7\[\d+\]', k)), None)
        if pile:
            n = pile[3:-1]
            for k in (pile, pile.replace('7', '5', 1)):
                if k in c['out']:
                    c['out'][k] = c['out'][k] - c['num']
    want_poison = c['out'].get('$4B44', [0, 0])[1] == 11
    if '$4B44' in c['out'] and got:
        if bool(got.get('poisoned')) != want_poison:
            extra.append(('poisoned', got.get('poisoned'), want_poison))
    if '$4B42' in c['out'] and got:
        if got.get('med') != c['out']['$4B42'][1]:
            extra.append(('care selector', got.get('med'), c['out']['$4B42'][1]))
    if 'effort $4C20' in c['out'] and got and c['exit'] in ('$4D00', '$4D03'):
        eff, met = got['effort']
        want = c['out']['effort $4C20'][1]
        k = {1: .01, 2: .02, 3: .05}.get(eff)
        if k is None:
            ok = abs(met - want) < 1e-3
        else:
            ok = abs(1.65 + k * 213 - want) < .01
        if not ok:
            extra.append(('effort', got['effort'], want))
    if count is not None and count != c['rnd_calls']:
        extra.append(('draws', count, c['rnd_calls']))
    text = ' // '.join(screens + [final])
    for m in c['log']:
        if m in TEXTS and TEXTS[m] not in text:
            extra.append(('msg', m, text))
    if c['exit'] is None and got and got.get('$4BC6 minutes'):
        extra.append(('minutes', got['$4BC6 minutes'], 0))
    for k in ('A2[17]', '$4BD2', '$4B41', '$4B42', '$4B44', '$4B54', '$4B71', '$4B73', '$4B77',
              '$4B82', '$4B83', '$4C04 available', '$4C18 old spoil', 'effort $4C20', 'W10[1]'):
        c['out'].pop(k, None)
    compare(c['name'], port, c, got, extra)


def discovery_case(port, c):
    """T0D/S00: the event x ($0D90 + x) through module_resource_results."""
    s = port.s
    x = next(a - 0x0D90 for a, _ in c['pokes'] if 0x0D9D <= a <= 0x0DA4) - 0x0D
    season = next((d[0] for a, d in c['pokes'] if a == 0x4ADA), None)
    if season is not None:
        s.step(L.poke('fauna_env', season))
    original = idle_bytes(3)
    a = L['native_resource_results']
    s.step(f'poke:{MAP + 36:04X}:{1 << x:02X}')
    port.poke('resource_seen', 1 << x if x < 2 else 0)
    wr = L['weather_random']
    saved = s.step(f'peek:{wr:04X}:3').data
    port.stub(c['rnd'])
    port.jump('weather_random')
    for i, b in enumerate((0x20, a & 255, a >> 8)):
        s.step(L.poke('idle', b, i))
    s.step(L.until('native_resource_results', 20000))
    s.step(f'until:{L["idle"] + 3:04X}:20000')
    for i, b in enumerate(original):
        s.step(L.poke('idle', b, i))
    pokes(s, wr, saved)
    s.step(f'poke:{MAP + 36:04X}:00')
    count = port.stub_count()
    got = reads(port, list(c['out']))
    c['out'].pop('W10[1]', None)
    compare(c['name'], port, c, got, [('draws', count, c['rnd_calls'])] if count != c['rnd_calls'] else [])


def carcass_case(port, c):
    """T06/S04 $593A: an ATTACK that wins leaves the carcass. The port's
    OUTDOOR draws its own rolls (native: RND against threshold / 256): the
    seed is chosen so that the attack wins unhurt; the carcass is the lot's
    (src/forage.s forage_kill), read when OUTDOOR returns."""
    s = port.s
    slot = next((a - b2 - 1 for a, _ in c['pokes'] if b2 < a <= b2 + 4), None)
    if slot is None:
        slot = {'2': 1, '3': 2}[re.search(r'animal (\d)', c['name'])[1]]
    x, y = port.cell()
    port.poke('animal_kind', 6 + slot)
    port.poke('animal_x', x)
    port.poke('animal_y', y)
    # The means of the case (lot 3: OUTDOOR takes the first in use, T0F/S07
    # $590F): the GUN in use (B2[57]: 21), else the AXE of the pack (18).
    means = 21 if any(a == B2 + 57 for a, _ in c['pokes']) else 18
    if s.step(f'peek:{MAP + 37:04X}:1').data[0]:
        seed = winning_seed(slot, means)        # a native map: RND
        for i in range(4):
            s.step(L.poke('weather_seed', seed >> 8 * i & 255, i))
    else:
        port.poke('fauna_rng', winning_rng(slot, means))
    noun = ('BEAR', 'COUGAR', 'RATTLESNAKE')[slot]
    s.step(f'key:ATTACK {noun}')
    s.step('press:\\r')
    s.step(L.until('do_outdoor_done', 60000))
    got = reads(port, list(c['out']))
    s.step(L.until('idle', 60000))
    for k in list(c['out']):
        if k.startswith('$4B'):
            c['out'].pop(k)
    compare(c['name'], port, c, got)


def lfsr(v):
    """src/outdoor.s outdoor_roll on a legacy map: 7 steps of the fauna generator."""
    v = v or 0xB7
    for _ in range(7):
        c = v & 1
        v >>= 1
        if c:
            v ^= 0xB8
    return v


def thresholds(slot, means):
    """OUTDOOR's injury and success thresholds of ATTACK with `means`
    (out_means_*: rows 17..21, lot 3)."""
    image = (HERE / 'build/wildout.bin').read_bytes()
    row = 4 * (means - 17) + slot
    return image[L['out_means_injury'] - 0x5800 + row], image[L['out_means_success'] - 0x5800 + row]


def winning_rng(slot, means=18):
    """fauna_rng whose first roll misses the injury threshold and second
    meets the success one (outdoor_roll: hit when the value < threshold)."""
    ti, ts = thresholds(slot, means)
    for v in range(1, 256):
        r1 = lfsr(v)
        if r1 >= ti and lfsr(r1) < ts:
            return v
    raise AssertionError('no winning fauna_rng')


def winning_seed(slot, means=18):
    """weather_seed whose first draw misses the injury threshold and second
    meets the success one (src/outdoor.s outdoor_native_roll: RND < t / 256)."""
    ti, ts = (t / 256 for t in thresholds(slot, means))
    inv = pow(STEP, -1, M)
    for s2 in range(1, int(ts * M), 9973):
        s1 = s2 * inv % M
        if s1 / M >= ti:
            return s1 * inv % M
    raise AssertionError('no winning seed')


# ---------------------------------------------------------------------------
# Part 2: the ROM's real-game script (re_forage_probe.run_game), replayed
# ---------------------------------------------------------------------------
PILES = dict(game=4, bear=0, hide=11, mushrooms=9)


def snapshot(port):
    out = {}
    for name, j in PILES.items():
        p = port.pile(j)
        out[name] = dict(b1=p['b1'], w5=p['w7'] + p['w8'], w7=p['w7'], w8=p['w8'])
        if j < 6:
            out[name]['b2'] = port.byte('fg_b2', j)
    out['mushrooms'].update(b3=port.byte('fg_px', 4), b4=port.byte('fg_pt', 4), w9_pack_pct=port.byte('fg_pp', 4),
                            g_taste=port.byte('fg_gt', 4), g_code=port.byte('fg_gx', 4),
                            g_pct=port.byte('fg_gp', 4))
    out['cheese'] = dict(w7=port.byte('it_gnd_lo', 28) | port.byte('it_gnd_hi', 28) << 8,
                         w8=port.byte('it_pack_lo', 28) | port.byte('it_pack_hi', 28) << 8)
    out['cheese']['w5'] = out['cheese']['w7'] + out['cheese']['w8']
    skin = port.byte('fg_skin')
    out['skinnable'] = [skin >> i & 1 for i in range(6)]
    out['kcal'] = port.float('s_eaten')
    out['salt'] = signed(*port.bytes('exposure_counter', 2))
    return out


def game_script(results):
    """The commands of part 2, the ROM's state after each: piles (b1, b2,
    ounces), records, skinnable flags, kcal and salt of the meals, the last
    message. Counters and the hour follow the port's health cadence (the
    clock rule itself: clock_check) and are not compared."""
    print('ROM real-game script (results.json, part 2):')
    rows = results['game']
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        prev = None
        mushrooms = False
        for row in rows:
            cmd = row['command']
            want = row['state']
            if cmd.startswith('START'):
                port.reset()
                if cmd == 'START':
                    port.poke('fg_b2', 0, 4)
                    port.poke('resource_seen', 1)
                    port.poke('camp_use', 128)          # GUN in use (the port's: B2[57])
                elif cmd == 'START (bear)':
                    x, y = port.cell()
                    port.poke('animal_kind', 6)
                    port.poke('animal_x', x)
                    port.poke('animal_y', y)
                else:
                    port.set_pile(4, w7=20, b1=0)
                    port.set_counter(FG_CGND + 4, 29)
                prev, prev_want = snapshot(port), want
                continue
            m = re.fullmatch(r'(.+?)(?: \[RND=([0-9.]+)\])?', cmd)
            words, rnd = m[1].split(), m[2]
            line = ' '.join(words[:2])
            answers = words[2:]
            if line == 'COOK GAME' and answers[-1:] == ['.5']:
                port.poke('fire_on', 1)                 # o.poke(0x45CD, [0]) before it
            if line == 'PACK MUSHROOMS' and not mushrooms:  # (the ROM's pokes before it)
                mushrooms = True
                port.set_pile(9, w7=20, b1=0)
                port.set_counter(FG_CGND + 9, 50)
                for name, v in (('fg_gt', 0), ('fg_gx', 2), ('fg_gp', 80)):
                    port.poke(name, v, 4)
            if line == 'DROP MUSHROOMS':
                for name, v in (('fg_px', 3), ('fg_pt', 5), ('fg_pp', 15)):
                    port.poke(name, v, 4)
                port.set_counter(9, 5)
            port.poke('fg_fidelity', 1 if 'CHEESE' in line and line.startswith('EAT') else 0)
            if line == 'KILL BEAR':
                port.poke('fauna_rng', winning_rng(0))
                _, text, _, _ = run(port, 'ATTACK BEAR')
            elif line in ('REST 3', 'WAIT 1', 'WAIT 4'):
                _, text, _, _ = run(port, line)
            else:
                _, text, _, _ = run(port, line, answers, [float(rnd)] * 8 if rnd else None)
            got = snapshot(port)
            bad = []
            for name in ('game', 'bear', 'hide', 'mushrooms', 'cheese'):
                for k, v in got[name].items():
                    w = want[name].get(k)
                    # b2 of the game after hours of stationary scans: the
                    # port's own sightings (src/travel.s), not this lot's
                    if w is not None and v != w and not (k == 'b2' and line in ('REST 3', 'SKIN BEAR', 'GET BEAR')):
                        bad.append((name, k, v, w))
            if got['skinnable'] != want['skinnable']:
                bad.append(('skinnable', got['skinnable'], want['skinnable']))
            for k in ('kcal', 'salt'):
                if line.startswith('EAT') or k == 'kcal' and line.startswith(('COOK', 'PACK', 'TASTE')):
                    dg = got[k] - prev[k]
                    dw = want[k] - prev_want[k]
                    if abs(dg - dw) > 1e-6:
                        bad.append((k, dg, dw))
            last = row.get('text', '').split(' / ')[-1].strip().rstrip('!')
            if line.startswith('PACK ') and last == 'OK, WHAT NEXT?':
                # 16 October 2026 (docs/FORAGE.md 17.3, an intended
                # difference): PACK asks nothing and says the ounces taken;
                # the ROM was given the whole pile where it asks.
                last = f'YOU TOOK {answers[0]} OUNCES.'
            if last and '?' not in last and last.split('!')[0][:20] not in text and line != 'KILL BEAR':
                bad.append(('text', text, last))
            check(f'{cmd}', not bad, str(bad))
            prev, prev_want = got, want
        # (prev_want of a START: its own state)


def clock_check():
    """T09/S05: each health update with the air at 33 F and above takes
    INT(minutes / 60 + .5) hours off every counter (fg_hm, the minutes of the
    update; airtemp); WAIT 1, WAIT 4, REST 3 take 8 hours in all, as the
    ROM's trace (part 3: 0, 5, 1 + 2)."""
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        port.reset()
        total = 0
        start = port.counter(FG_CPROV + 5)              # CHEESE (28)
        for line in ('WAIT 1', 'WAIT 4', 'REST 3'):
            s.step(f'key:{line}')
            s.step('press:\\r')
            s.step(L.until('do_command', 40000))
            while True:
                r = s.step(f'until:{L["forage_clock"]:04X},{L["idle"]:04X}:60000')
                if int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16) == L['idle']:
                    break
                if port.byte('overlay_current') == 27:   # (the $5800 window: ALERT)
                    m = port.byte('fg_hm') | port.byte('fg_hm', 1) << 8
                    air = port.byte('airtemp')
                    total += (m + 30) // 60 if air >= 33 else 0
                s.step('wait:1')
        taken = start - port.counter(FG_CPROV + 5)
        check(f'spoilage clock: {taken} hours over WAIT 1, WAIT 4, REST 3 (ROM 8)',
              taken == total == 8, (taken, total))


# ---------------------------------------------------------------------------
# The port's own rules around the module
# ---------------------------------------------------------------------------
def area(slope, ta, tb, c):
    """T0C/S03 $5BCC (src/forage.s fg_seg) in Python."""
    sign = lambda v: (v > 0) - (v < 0)      # noqa: E731
    total = sign(slope * ta + c) + sign(slope * tb + c)
    if total < 0:
        return 0.0
    if total == 0:
        ta = -(c / slope)
    a = slope / 2 * (tb * tb - ta * ta) + c * (tb - ta)
    return -a if slope < 0 else a


def day_factor(port):
    """$4C48 of the day from the cycle in THERMAL (weather_cycle's values)."""
    f = port.float
    sb = lambda name: (lambda v: v - 256 if v > 127 else v)(port.byte(name))   # noqa: E731
    dawn, peak, end = f('wc_dawn'), f('wc_peak'), f('wc_end')
    mo, ev, ni = f('wc_morning'), f('wc_evening'), f('wc_night')
    hi, lo = sb('wc_max'), sb('wc_min')
    a23 = f('s_rise') + 23
    # AYINT (as weather_temperature's offsets): the floor, -47.96 -> -48
    off = lambda ref, anchor, slope: ref - math.floor(anchor * slope) - 32     # noqa: E731
    d = area(mo, dawn, peak, off(hi, peak, mo))
    d += area(ev, end, peak, off(hi, peak, ev))
    d += area(ni, dawn + 24, end, off(lo, a23, ni))
    return 792 / max(40.0, d), d


def saved_factor(state):
    """$4C48 from the original's saved cycle ($4CC0.., build/re_forage/state.bin)."""
    import re_surv_fp
    f = lambda a: re_surv_fp.fp(state[a - 0x4000:a - 0x3FFB])         # noqa: E731
    sb = lambda a: (lambda v: v - 256 if v > 127 else v)(state[a - 0x4000])     # noqa: E731
    word16 = int.from_bytes(state[0x4BBC - 0x4000:0x4BBE - 0x4000], 'little', signed=True)
    dawn, peak, end = f(0x4CB1), f(0x4CB6), f(0x4CBB)
    d = area(f(0x4CC0), dawn, peak, sb(0x4BB6) - 32) + area(f(0x4CC5), end, peak, word16 - 32)
    d += area(f(0x4CCA), dawn + 24, end, sb(0x4BB8) - 32)
    return 792 / max(40.0, d)


def call_carry(port, label):
    """JSR label from the idle loop: its carry (1 set)."""
    s = port.s
    original = idle_bytes(3)
    stub = (0x20, L[label] & 255, L[label] >> 8, 0xA9, 0, 0x2A, 0x8D, COUNT & 255, COUNT >> 8, 0x60)
    pokes(s, STUB, stub)
    for i, b in enumerate((0x20, STUB & 255, STUB >> 8)):
        s.step(L.poke('idle', b, i))
    s.step(f'until:{STUB:04X}:20000')
    s.step(f'until:{L["idle"] + 3:04X}:20000')
    for i, b in enumerate(original):
        s.step(L.poke('idle', b, i))
    return s.step(f'peek:{COUNT:04X}:1').data[0]


def port_checks():
    print('The lot around the module:')
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        port = Port(s)
        port.poke('nature_frequency', 0)
        port.reset()
        # Leaving the cell: the ground piles and the game stay behind.
        port.reset()
        port.set_pile(4, w7=36, b1=0)
        port.poke('fg_b2', 1, 4)
        port.poke('fg_skin', 16)
        port.set_pile(9, w8=5, w7=7, b1=4)
        run(port, 'WALK 1 H')
        moved = port.cell() != (port.byte('fg_x'), port.byte('fg_y'))
        check('a walk leaves the ground piles: GAME gone, MUSHROOMS kept in the pack (b1 2)',
              not moved and port.pile(4) == dict(b1=255, w7=0, w8=0) and port.pile(9) == dict(b1=2, w7=0, w8=5)
              and port.byte('fg_b2', 4) == 255 and port.byte('fg_skin') == 0, (port.pile(4), port.pile(9)))
        # The factor of the day: at midnight, 792 / D of the new day's cycle.
        check('$4C48 of the saved game: 1.61734', abs(port.float('fg_factor') - 1.61734) < 1e-5)
        saved = HERE / 'build/re_forage/state.bin'
        if saved.exists():                      # fg_seg on the original's own saved cycle
            check('the integral on the saved coefficients of the original: 1.61734 (D 489.69)',
                  abs(saved_factor(saved.read_bytes()) - 1.61734) < 1e-5)
        for i, b in enumerate(encode(23.75)):
            port.poke('s_hour', b, i)
        s.step('key:REST 1 H')
        s.step('press:\\r')
        s.step(L.until('forage_day', 60000))
        while True:                             # (the $5800 window: ALERT's own)
            s.step(L.until('fg_seg', 60000))
            if port.byte('overlay_current') == 27:
                break
        want, d = day_factor(port)
        s.step(L.until('idle', 60000))
        got = port.float('fg_factor')
        check(f'$4C48 after midnight: 792 / D, D = {d:.2f} degree-hours above 32 F ({got:.5f})',
              abs(got - want) < 1e-6 * want, (got, want))
        # The smell of spoiled food in the pack (T0D/S07 $5E3F, msg 209).
        port.reset()
        port.set_pile(9, w8=5, b1=2)
        port.set_counter(9, 0)
        _, text, _, _ = run(port, 'WAIT 1 H')
        check('spoiled food in the pack: THERE IS A BAD SMELL IN THE AIR.', 'BAD SMELL' in text, text)
        # IGNORE FOOD, REST, CAMP: forage_skip says "no draw" (TRAVEL's scan
        # calls it before the RND of each food or game type).
        travel = (HERE / 'build/wildtrv.bin').read_bytes()
        call = bytes((0x20, L['forage_skip'] & 255, L['forage_skip'] >> 8))
        skips = []
        for ignore, verb in ((0, 19), (1, 19), (0, 20), (1, 22)):
            port.poke('fg_ignore', ignore)
            port.poke('verb', verb)
            skips.append(call_carry(port, 'forage_skip'))
        port.poke('fg_ignore', 0)
        check('forage_skip: WAIT draws, IGNORE FOOD and REST do not; TRAVEL calls it',
              skips == [0, 1, 1, 1] and call in travel, skips)
        # The grid: CATCH, KILL with game here; SKIN with a carcass; COOK at
        # a fire; none otherwise (TASTE is EAT's: its first entry).
        port.reset()
        for want, setup in ((set(), ()), ({'CATCH', 'KILL'}, (('fg_b2', 0, 4), ('resource_seen', 1, 0))),
                            ({'SKIN'}, (('fg_skin', 16, 0), ('fg_gl', 30, 4), ('fg_b1', 0, 4),
                                        ('fg_b2', 1, 4))),
                            ({'SKIN', 'COOK'}, (('fire_on', 1, 0),))):
            for name, v, k in setup:
                port.poke(name, v, k)
            run(port, 'LOOK R')                 # a new prompt: the grid rebuilt
            s.step('press:\\t')
            s.step('wait:2')
            words = set(' '.join(line[40:] for line in text_screen(s.step('peek:0400:1024').data)[20:24])
                        .replace('\u2595', ' ').split())      # (XL: the cells' bars, docs/MENUS.md 9)
            s.step('press:\\t')
            s.step('wait:2')
            shown = words & {'CATCH', 'KILL', 'SKIN', 'COOK', 'TASTE'}
            check(f'grid: {sorted(shown) or "none of the lot"}', shown == want, (shown, want))
        grid_lists(port)


def grid_lists(port):
    """The grid's lists name lot 4's piles and targets (src/grid.s): EAT the
    piles first, TASTE before the ounces; GET packs a pile (PACK x); SKIN,
    COOK, KILL, CATCH their targets (one: chosen at once); KILL takes the
    best weapon first, CATCH the bait and the trap (the queue)."""
    from test_menu_bar import move_to, press, grid_cells, bottom, RET, ESC, TAB
    s = port.s

    def at(*labels):
        """RETURN on each label in turn: the screen, then the composed line."""
        press(s, TAB)
        for label in labels:
            move_to(s, label)
            press(s, RET)
        return sum(grid_cells(s), [])

    def chosen(*labels):
        """The command the labels compose (the first one typed when queued)."""
        press(s, TAB)
        for label in labels[:-1]:
            move_to(s, label)
            press(s, RET)
        move_to(s, labels[-1])
        s.step('press:\\r')
        s.step(L.until('do_command', 40000))
        line = s.step(L.peek('inbuf', 30)).data.split(b'\0')[0].decode()
        queued = [s.step(L.peek('mq_list', 1, k)).data[0] for k in range(s.step(L.peek('mq_n')).data[0])]
        return line, s.step(L.peek('menu_noun')).data[0], queued

    def back():
        """The command and its queue run to the prompt (an hour when asked,
        a key for a full result)."""
        for _ in range(12):
            r = s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:400000')
            if int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16) == L['idle']:
                break
            if 'HOURS' in rows(s) or 'OUNCES' in rows(s):
                s.step('key:8' if 'OUNCES' in rows(s) else 'key:1')
                s.step('press:\\r')
            else:
                s.step('key: ')
            s.step('wait:1')
        press(s, ESC)

    # (from the last setup: a carcass of GAME, 30 oz on the ground, a fire)
    items = at('EAT')
    check('EAT: the pile of food first', items[:1] == ['GAME'], items)
    move_to(s, 'GAME')
    press(s, RET)
    items = sum(grid_cells(s), [])
    check('EAT GAME: TASTE, then the ounces (at most the 30 here)', items[:1] == ['TASTE']
          and items[-2:] == ['24', 'OZ'], items)
    press(s, ESC, ESC)
    line = chosen('EAT', 'GAME', 'TASTE')
    check('TASTE GAME from EAT\'s list', line[:2] == ('TASTE GAME', 80), line)
    back()
    line = chosen('SKIN')
    check('SKIN: its one target, at once', line[:2] == ('SKIN GAME', 80), line)
    back()
    before = port.pile(4)
    line = chosen('GET', 'GAME')
    check('GET GAME: PACK GAME (a pile goes to the pack)', line[:2] == ('PACK GAME', 80), line)
    back()
    text = rows(s)
    after = port.pile(4)
    check(f'PACK GAME from the grid: no question, the whole pile ({before["w7"]} oz) in the pack, '
          'the ounces said (16 October 2026)',
          after['w8'] == before['w8'] + before['w7'] and after['w7'] == 0
          and f'YOU TOOK {before["w7"]} OUNCES' in text, (before, after, text))
    port.poke('fg_b2', 0, 4)            # game present again (seen: it stays)
    port.poke('resource_seen', 1)
    animal = port.byte('animal_kind')
    port.poke('animal_kind', 0)         # (an animal's KILL would come first)
    port.poke('fg_skin', 0)
    port.poke('fire_on', 0)
    run(port, 'LOOK R')
    line = chosen('KILL')
    check('KILL: GAME, the AXE in use first (no gun)', line == ('USE AXE', 58, [S_AXE, S_KILL]), line)
    back()
    port.poke('fg_b2', 0, 4)
    port.poke('resource_seen', 1)
    port.poke('care_tools', 0)
    port.poke('fg_bait', 0)
    port.poke('it_place', 2, 72)        # the TRAP in the pack
    run(port, 'LOOK R')
    line = chosen('CATCH', '1 H')
    check('CATCH: GAME, the bait and the TRAP first', line == ('USE BAIT', 175, [S_BAIT, S_TRAP, S_CATCH]), line)
    back()
    port.poke('animal_kind', animal)


S_BAIT, S_TRAP, S_AXE, S_KILL, S_CATCH = 9, 10, 13, 19, 20        # src/grid.s


def main():
    original = '--original' in sys.argv
    if not RESULTS.exists():
        if original:
            raise SystemExit(f'{RESULTS} is missing: python3 tools/re_forage_probe.py '
                             '(needs build/JOURNEY.dsk, build/game.bin: make extract)')
        print(f'{RESULTS} missing: the ROM cases are skipped (values of docs/FORAGE.md below)')
    if not original:
        discovery_draws()
        port_checks()
    if RESULTS.exists():
        results = json.loads(RESULTS.read_text())
        original_cases(results)
        game_script(results)
    clock_check()
    if fails:
        raise SystemExit(f'FORAGE: {len(fails)} failures: {fails}')
    print('FORAGE: OK')


if __name__ == '__main__':
    main()
