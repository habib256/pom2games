#!/usr/bin/env python3
"""Fire, light and water of the original on the Apple II ROM (lot 2).

Part 1 runs the water module T0F/S00 alone (loaded at $5800 over the saved
first-journey state build/game.bin), RND ($0321) imposed, message and
input entries of the core stubbed: the six sources (rain, snow, river,
cacti, timed search, condensation), the giardia threshold at two altitudes.
Part 2 plays the real game (build/SIERRA.woz + build/JOURNEY.dsk) with a few
RAM pokes between commands: fire, light, batteries, matches, the flags
"in use" that time clears, water collection and DRINK.

No original byte enters the repository: module and disks stay in build/,
results go to build/re_camp/results.json (numbers quoted in docs/CAMP.md).
"""
import json
import re
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

OUT = HERE / 'build/re_camp'
LOG, RND, YES, NUM, MSG = 0x0910, 0x0920, 0x0902, 0x0904, 0x0900


def poke(addr, data):
    return [f'poke:{addr + i:04X}:{v:02X}' for i, v in enumerate(data)]


def water_disk():
    """DOS 3.3 disk: state $4000-$7FFF with T0F/S00 at $5800, a driver at
    $0800 (JSR entry, JMP $0800) and the stubs at $0A00."""
    journey = smalldos.Disk((HERE / 'build/JOURNEY.dsk').read_bytes())
    journey.flip = True
    module = journey.run(0x0F, 0, 7)
    state = bytearray((HERE / 'build/game.bin').read_bytes()[0x4000:0x8000])
    state[0x1800:0x1800 + len(module)] = module
    state[0xD00] = 0x60                                     # $4D00: time engine -> RTS
    for entry, target in ((0x4D21, 0x0A20), (0x4D24, 0x0A30), (0x4D2A, 0x0A00),
                          (0x4D30, 0x0A50), (0x4D39, 0x0A40)):
        state[entry - 0x4000:entry - 0x4000 + 3] = bytes((0x4C, target & 255, target >> 8))
    driver = bytearray(0x260)
    driver[0:6] = bytes.fromhex('20 00 58 4C 00 08')
    stubs = {0x0A00: '8C 1F 09 AC 10 09 8A 99 11 09 EE 10 09 AC 1F 09 60',  # log X, keep Y
             0x0A20: '8E 00 09 4C 00 0A',                                  # $4D21: final message
             0x0A30: '85 0E 84 0F 4C 00 0A',                               # $4D24: A,Y -> $0E,$0F
             0x0A40: 'AD 02 09 60',                                        # $4D39: the answer
             0x0A50: 'AC 04 09 AD 05 09 60'}                               # $4D30: the number
    for addr, code in stubs.items():
        b = bytes.fromhex(code)
        driver[addr - 0x800:addr - 0x800 + len(b)] = b
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'state.bin').write_bytes(state)
    (OUT / 'driver.bin').write_bytes(driver)
    (OUT / 'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BRUN DRIVER"\n')
    disk = OUT / 'water.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'), '--out', str(disk),
                    '--bas', f'HELLO={OUT / "hello.bas"}', '--bin', f'STATE={OUT / "state.bin"}@0x4000',
                    '--bin', f'DRIVER={OUT / "driver.bin"}@0x0800'], check=True, capture_output=True)
    return disk


def water_cases():
    """(name, entry, pokes, expectation) of the isolated module."""
    game = (HERE / 'build/game.bin').read_bytes()
    freq = fp(game[0x4C43:0x4C48])
    cases = []
    common = poke(0x0321, bytes.fromhex('A9 20 A0 09 4C F9 EA'))     # RND: FAC <- $0920
    # Giardia, $5CF7: untreated ($4B48 = 0), altitude $D4 + $60A1 hundreds of feet.
    for level, base in ((10, 10), (10, 90)):
        p = .2 / ((level + base) / 10)
        for r in (p * .999, p * 1.001):
            cases.append(dict(kind='giardia', altitude=(level + base) * 100, p=p, rnd=r,
                              steps=poke(0xD4, [level]) + poke(0x60A1, [base]) + poke(0x4B48, [0])
                              + poke(0x4B41, [0]) + poke(0x4B44, [0]) + poke(RND, encode(r)), entry=0x5CF7))
    # Timed search, $5943 (after the hours): p = minutes x $4C43 x k.
    for terrain, region, k in ((0, 2, .00033), (1, 2, .00083), (1, 4, .004)):
        p = 120 * freq * k
        for r in (p * .999, p * 1.001):
            cases.append(dict(kind='search', terrain=terrain, region=region, k=k, minutes=120,
                              frequency=freq, p=p, rnd=r, entry=0x5943,
                              steps=poke(0x4BC6, [120, 0]) + poke(0x4B56, [terrain]) + poke(0x601F, [region])
                              + poke(0x03, [1]) + poke(0x4B48, [1]) + poke(NUM, [0, 0]) + poke(YES, [0])
                              + poke(RND, encode(r))))
    # Cacti, $5909: RND < .5 (B1 of CACTI on the cell).
    for r in (.4999, .5001):
        cases.append(dict(kind='cactus', rnd=r, entry=0x5909,
                          steps=poke(0x03, [1]) + poke(0x4B48, [1]) + poke(NUM, [0, 0]) + poke(YES, [0])
                          + poke(RND, encode(r))))
    # Condensation, $5A22 (MAKE WATER, a cover in use): the hours stubbed.
    for minutes, hour, sunset in ((120, 9, 18.88), (600, 14, 18.88), (55, 9, 18.88), (90, 17.5, 18.88)):
        limit = 60 * (sunset - hour - .5)
        cases.append(dict(kind='condense', minutes=minutes, hour=hour, sunset=sunset,
                          oz=int(.1 * min(minutes, limit) + .5), entry=0x5A22,
                          steps=poke(0x5E00, bytes.fromhex('AC 04 09 AD 05 09 60'))
                          + poke(NUM, [minutes & 255, minutes >> 8]) + poke(0x4C57, encode(hour))
                          + poke(0x4C6B, encode(sunset)) + poke(0x4098 + 12, [1]) + poke(0x03, [3])))
    # Rain, snow, river from the entry ($5800): GET, 10 oz asked, canteen full.
    for name, noun, sky, terrain, answer in (('rain', 169, 2, 0, 0), ('snow', 170, 3, 0, 0),
                                              ('river', 22, 0, 3, 1)):
        cases.append(dict(kind='source', source=name, entry=0x5800,
                          steps=poke(0x05, [noun]) + poke(0x03, [1]) + poke(0x4B4C, [sky]) + poke(0x4B57, [0])
                          + poke(0x4B56, [terrain]) + poke(0x4B6B, [3 if terrain else 0])
                          + poke(0x404C + 22, [2]) + poke(0x42AC + 44, [0, 0]) + poke(0x4344 + 44, [54, 0])
                          + poke(0x4098 + 22, [1]) + poke(YES, [answer]) + poke(NUM, [10, 0])))
    return common, cases


def run_water():
    disk = water_disk()
    common, cases = water_cases()
    steps = ['until:0800:20000'] + common
    for c in cases:
        steps += poke(0x801, [c['entry'] & 255, c['entry'] >> 8]) + poke(LOG, [0] * 9) + poke(MSG, [0])
        steps += c['steps'] + ['until:0803:4000', 'peek:0900:32', 'peek:4B41:4', 'peek:000E:2',
                               'peek:42AC:46', 'peek:4098:23', 'peek:4C04:2', 'peek:0007:2', 'until:0800:4000']
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=1800)
    for k, c in enumerate(cases):
        msg = r.mem(0x900, 32, k)
        c['log'] = list(msg[0x11:0x11 + msg[0x10]])
        c['final'] = msg[0]
        ev = r.mem(0x4B41, 4, k)
        c['event'] = [ev[0], ev[3]]
        c['number'] = int.from_bytes(r.mem(0x0E, 2, k), 'little')
        c['ground'] = int.from_bytes(r.mem(0x42AC, 46, k)[44:46], 'little')
        c['canteen_safe'] = r.mem(0x4098, 23, k)[22]
        c['available'] = int.from_bytes(r.mem(0x4C04, 2, k), 'little')
        c['amount'] = int.from_bytes(r.mem(0x0007, 2, k), 'little')
        del c['steps']
    for c in cases:
        if c['kind'] == 'giardia':
            infected = c['rnd'] <= c['p']
            assert c['event'] == ([3, 12] if infected else [0, 0]), c
        elif c['kind'] == 'search':
            assert c['log'][0] == (56 if c['rnd'] <= c['p'] else 62), c
        elif c['kind'] == 'cactus':
            assert c['log'][0] == (179 if c['rnd'] < .5 else 55), c
        elif c['kind'] == 'condense':
            assert 63 in c['log'] and c['number'] == c['oz'], c
        else:
            assert c['available'] == 160 and c['ground'] == 160, c
            assert c['canteen_safe'] == (0 if c['source'] == 'river' else 1), c
            assert c['amount'] == 10, c
    return cases


# ---------------------------------------------------------------------------
# Part 2: the real game.
PROMPT, KEYWAIT = 0xB0E2, 0xFD1B


class Original:
    def __enter__(self):
        from re_surv_run import boot
        from common import text_screen
        self.text_screen = text_screen
        self.s = a2test.Session(HERE / 'build/SIERRA.woz', cwd=HERE)
        self.s.__enter__()
        for step in boot():
            self.s.step(step)
        # SURV3D $103E pages $4000-$4FFF out (HGR page 2) during long rests:
        # observe the state each time it is saved (tests/test_adventure.py).
        self.s.step('watch:103E:4000:4096')
        return self

    def __exit__(self, *a):
        (OUT / 'game.log').write_text(self.s.out)
        self.s.__exit__(*a)

    def mem(self):
        m = bytearray(self.s.step('peek:0000:49152').mem(0, 49152))
        if m[0x4D00:0x4D03] != bytes.fromhex('4c3c4d'):
            for h in re.findall(r'^watch 103E .* mem=([0-9A-F]+)$', self.s.out, re.M):
                c = bytes.fromhex(h)
                if c[0xD00:0xD03] == bytes.fromhex('4c3c4d'):
                    m[0x4000:0x5000] = c
        return bytes(m)

    def screen(self):
        m = self.s.step('peek:0400:1024').mem(0x400, 1024)
        return ' '.join(' '.join(self.text_screen(m)[20:24]).split())

    def poke(self, addr, data):
        for step in poke(addr, data):
            self.s.step(step)

    def cmd(self, command, *answers):
        for ch in command:
            self.s.step('press:' + ch)
            self.s.step('until:B126:20000')
            self.s.step('until:B0E2:20000')
        self.s.step('press:\r')
        self.s.step('until:B143:20000')
        answers, texts = list(answers), []
        for _ in range(40):
            self.s.step('wait:1')
            r = self.s.step(f'until:{PROMPT:04X},{KEYWAIT:04X}:40000')
            texts.append(self.screen())
            if int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16) == PROMPT:
                return ' / '.join(t.replace('? ` > ', '').strip() for t in texts)
            a = answers.pop(0) if answers else '\r'
            self.s.step('key:' + (a if len(a) == 1 and not a.isdigit() else a + '\r'))
        raise AssertionError(f'{command}: too many prompts')


def state(m):
    w8 = lambda i: int.from_bytes(m[0x4344 + 2 * i:0x4346 + 2 * i], 'little', signed=True)
    w7 = lambda i: int.from_bytes(m[0x42AC + 2 * i:0x42AE + 2 * i], 'little', signed=True)
    return dict(matches=[m[0x404C + 38], m[0x4098 + 38], w8(38)], fuel=[m[0x404C + 40], m[0x4098 + 40], w8(40)],
                flashlight=[m[0x404C + 66], m[0x4098 + 66], w8(66)], fire=[m[0x45CD], m[0x45E9]],
                sticks=[m[0x45CC], m[0x45E8]], light=m[0xD5D], step=m[0x4BCC], effort=round(fp(m[0x4C20:0x4C25]), 6),
                hour=round(fp(m[0x4C57:0x4C5C]), 4), sky=m[0x4B4C], water=[m[0x404C + 22], m[0x4098 + 22], w7(22), w8(22)],
                water_deficit=round(fp(m[0x49B9:0x49BE]), 6), selectors=[i + 1 for i in range(30) if m[0x4ABC + i]],
                stove=[m[0x404C + 71], m[0x4098 + 71]], utensils=[m[0x404C + 73], m[0x4098 + 73]])


GAME = [
    # fire
    ('MAKE FIRE',), ('USE MATCHES',), ('MAKE FIRE',), ('WALK',), ('USE FIRE',), ('MAKE FIRE',), ('DOUSE FIRE',),
    ('USE FIRE',), ('MAKE MATCHES',), ('USE MATCHES',), ('poke', 0x4B4C, [2]), ('MAKE FIRE',), ('poke', 0x4B4C, [2]),
    ('USE FUEL',), ('poke', 0x4B4C, [2]), ('MAKE FIRE',), ('DOUSE FIRE',), ('USE MATCHES',), ('poke', 0x4B9F, [41]),
    ('MAKE FIRE',), ('poke', 0x4B9F, [40]), ('MAKE FIRE',), ('DOUSE FIRE',), ('USE MATCHES',),
    ('poke', 0x4B56, [3]), ('poke', 0x4B6B, [0]), ('MAKE FIRE',), ('poke', 0x4B56, [2]), ('poke', 0x4B57, [1]),
    ('MAKE FIRE',), ('poke', 0x4B57, [0]), ('MAKE STICKS',), ('poke', 0x4B56, [0]), ('MAKE STICKS',),
    ('MAKE STICKS',), ('USE STICKS',), ('USE GLASS',),
    # water
    ('poke', 0x4B4C, [2]), ('GET RAIN', '40'), ('poke', 0x4B4C, [0]), ('GET RAIN',), ('DRINK WATER', 'C', '34'),
    ('DRINK WATER', 'C', '4'), ('poke', 0x4B4C, [3]), ('GET SNOW', '200'), ('GET SNOW', '100'),
    ('poke', 0x4B4C, [0]), ('BOIL WATER', 'C', '10'), ('USE UTENSILS',), ('BOIL WATER', 'C', '10'),
    ('poke', 0x404C + 71, [2]), ('USE STOVE',), ('USE MATCHES',), ('USE FUEL',), ('USE STOVE',),
    ('BOIL WATER', 'C', '10'),
]
NIGHT = [
    ('poke', 0x404C + 41, [2]), ('REST', '13'), ('USE FIRSTAID KIT',), ('USE FLASHLIGHT',), ('USE FIRSTAID KIT',),
    ('USE MATCHES',), ('WAIT', '1'), ('USE FIRSTAID KIT',), ('USE FLASHLIGHT',), ('poke', 0x4344 + 132, [0, 0]),
    ('USE FLASHLIGHT',), ('poke', 0x4344 + 76, [1, 0]), ('USE MATCHES',), ('USE MATCHES',), ('MAKE FIRE',),
]


def play(o, items, rows):
    for item in items:
        if item[0] == 'poke':
            o.poke(item[1], item[2])
            continue
        text = o.cmd(*item)
        rows.append(dict(command=' '.join(item), text=text, state=state(o.mem())))


def run_game():
    rows = []
    with Original() as o:
        rows.append(dict(command='START', state=state(o.mem())))
        play(o, GAME, rows)
    with Original() as o:
        rows.append(dict(command='START (night)', state=state(o.mem())))
        play(o, NIGHT, rows)
    with Original() as o:
        # "In use" flags cleared by the passing of time (WAIT 1 hour).
        o.poke(0x4098 + 1, [1] * 75)
        o.poke(0x45DC + 1, [1] * 27)
        o.cmd('WAIT', '1')
        m = o.mem()
        rows.append(dict(command='WAIT 1 (all B2 = 1 before)',
                         cleared=[i for i in range(1, 76) if m[0x4098 + i] == 0],
                         cleared_second=[i + 75 for i in range(1, 28) if m[0x45DC + i] == 0]))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    water = run_water()
    print(f'{len(water)} isolated T0F/S00 cases (RND imposed): OK')
    game = run_game()
    for row in game:
        print(row['command'], '|', row.get('text', ''), '|', row.get('state', row.get('cleared')))
    (OUT / 'results.json').write_text(json.dumps(dict(water=water, game=game), indent=1) + '\n')


if __name__ == '__main__':
    main()
