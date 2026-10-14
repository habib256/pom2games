#!/usr/bin/env python3
"""Fire, light and water of lot 2 (src/camp.s, src/water.s; docs/CAMP.md).

Each expectation comes from the original on the ROM (tools/re_camp_probe.py,
tools/re_thermal_probe.py): messages, minutes, stocks, flags, effort, care
selectors, the +25 F of a fire in the thermal chain, the giardia threshold
and the timed search, drawn with the game's own RND (weather_random, the
Lehmer generator of SMALLDOS $0321) from imposed seeds.
"""
import json
import re
import tempfile

from common import HERE, L, DISK, a2test, disk_with, fp, text_screen
from gendata import fp as encode
from test_input import IDLE, command, flat

fails = []


def check(name, ok, detail=''):
    print(f'  {name}: {"OK" if ok else "FAIL"}' + (f' {detail}' if not ok and detail else ''))
    if not ok:
        fails.append(name)


def rows(s):
    """The result column (rows 20-23, columns 40-79), words joined."""
    return ' '.join(' '.join(l[40:].split()) for l in text_screen(s.step('peek:0400:1024').data)[20:24])


def say(s, text, *answers):
    """A command with its answers (numbers end with RETURN, a letter is a key)."""
    s.step(f'key:{text}')
    s.step('press:\\r')
    answers, seen = list(answers), []
    for _ in range(12):
        s.step('wait:1')
        r = s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:40000')
        seen.append(rows(s))
        if int(re.search(r'PC=([0-9A-F]{4})', r.out)[1], 16) == L['idle']:
            return ' // '.join(seen)
        a = answers.pop(0) if answers else ' '
        s.step(f'key:{a}')
        if len(a) > 1 or a.isdigit():
            s.step('press:\\r')
    raise AssertionError(f'{text}: too many prompts')


def b(s, name, k=0):
    return s.step(L.peek(name, 1, k)).data[0]


def f(s, name):
    return fp(s.step(L.peek(name, 5)).data)


def poke(s, name, value, k=0):
    for i, v in enumerate(value if isinstance(value, (bytes, list)) else [value]):
        s.step(L.poke(name, v, k + i))


def lehmer(seed):
    """weather_random: 13 modular doublings of the 32-bit seed, then S / m."""
    m = 67099547
    for _ in range(13):
        seed *= 2
        if seed >= m:
            seed -= m
    return seed, seed / m


def fire():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        poke(s, 'nature_frequency', 0)
        check('USE GLASS at 7 a.m.: the sun below 30 degrees, msg 53', 'INSUFFICIENT LIGHT' in say(s, 'USE GLASS'))
        hour = f(s, 's_hour')
        check('MAKE FIRE without MATCHES or GLASS in use: msg 25',
              'USE THE APPROPRIATE ITEM FIRST.' in say(s, 'MAKE FIRE') and b(s, 'fire_on') == 0)
        say(s, 'USE MATCHES')
        check('USE MATCHES: one match of 24, in the hand, in use, no time',
              b(s, 'it_pack_lo', 38) == 23 and b(s, 'it_place', 38) == 3 and b(s, 'camp_use') & 1
              and f(s, 's_hour') == hour)
        text = say(s, 'MAKE FIRE')
        check('MAKE FIRE: msg 15, 30 minutes, the match spent, care selector 24, effort 1.65 + .02 x 213 lb',
              'IT TOOK A WHILE TO MAKE YOUR FIRE.' in text and abs(f(s, 's_hour') - hour - .5) < 1e-6
              and b(s, 'fire_on') == 1 and b(s, 'camp_use') & 1 == 0 and b(s, 'medical_actions', 23) == 1
              and abs(f(s, 's_metabolic') - 5.91) < 1e-6 and b(s, 'health_period') == 83,
              (text, f(s, 's_metabolic'), b(s, 'health_period')))
        px = s.step(L.peek('px', 4)).data
        hour = f(s, 's_hour')
        text = say(s, 'WALK', '1 H')
        check('WALK with the fire burning: msg 132, no step, no time (M5)',
              'SMOKEY THE BEAR SAYS TO DOUSE YOUR FIRE FIRST!' in text
              and s.step(L.peek('px', 4)).data == px and f(s, 's_hour') == hour, text)
        say(s, 'USE FIRE')
        check('USE FIRE: near the fire, light, health steps of 15 minutes',
              b(s, 'fire_near') == 1 and b(s, 'light') == 1 and b(s, 'health_period') == 15)
        check('MAKE FIRE again: msg 11', 'YOU ALREADY HAVE.' in say(s, 'MAKE FIRE'))
        say(s, 'DOUSE FIRE')
        check('DOUSE FIRE: out, no time', b(s, 'fire_on') == 0 and b(s, 'fire_near') == 0 and f(s, 's_hour') == hour)
        check('USE FIRE without a fire: msg 1', 'SORRY, THAT ITEM IS NOT AVAILABLE.' in say(s, 'USE FIRE'))
        check('MAKE MATCHES: msg 11', 'YOU ALREADY HAVE.' in say(s, 'MAKE MATCHES'))
        # Weather ($5A32): rain or a wind of 41 mph and more need FUEL in use.
        say(s, 'USE MATCHES')
        poke(s, 'weather_sky', 2)
        check('MAKE FIRE in rain without FUEL: msg 79', 'SORRY, TOO MUCH RAIN OR WIND.' in say(s, 'MAKE FIRE'))
        poke(s, 'weather_sky', 2)
        say(s, 'USE FUEL')
        check('USE FUEL: one ounce of 8', b(s, 'it_pack_lo', 40) == 7 and b(s, 'camp_use') & 4)
        poke(s, 'weather_sky', 2)
        check('MAKE FIRE in rain with FUEL in use: lit', 'MAKE YOUR FIRE' in say(s, 'MAKE FIRE') and b(s, 'fire_on'))
        say(s, 'DOUSE FIRE')
        say(s, 'USE MATCHES')
        poke(s, 'weather_sky', 0)
        poke(s, 'wind', 41)
        check('MAKE FIRE at 41 mph: msg 79', 'SORRY, TOO MUCH RAIN OR WIND.' in say(s, 'MAKE FIRE'))
        poke(s, 'wind', 40)
        check('MAKE FIRE at 40 mph: lit', 'MAKE YOUR FIRE' in say(s, 'MAKE FIRE'))
        say(s, 'DOUSE FIRE')
        # In water: the player's cell of the grid gets the water bit.
        x, y = b(s, 'px', 1), b(s, 'py', 1)
        cell = 0x7000 + 64 + y * 112 + x
        old = s.step(f'peek:{cell:04X}:1').data[0]
        say(s, 'USE MATCHES')
        s.step(f'poke:{cell:04X}:{old | 0x80:02X}')
        check('MAKE FIRE in water: msg 78', 'IN OR ON WATER' in say(s, 'MAKE FIRE'))
        check('MAKE STICKS in water: msg 76', 'RAW MATERIAL IS NOT AVAILABLE' in say(s, 'MAKE STICKS'))
        s.step(f'poke:{cell:04X}:{old:02X}')
        hour = f(s, 's_hour')
        check('MAKE STICKS: msg 15, 30 minutes', 'MAKE YOUR STICKS' in say(s, 'MAKE STICKS')
              and abs(f(s, 's_hour') - hour - .5) < 1e-6 and b(s, 'sticks_on') == 1)
        check('MAKE STICKS again: msg 11', 'YOU ALREADY HAVE.' in say(s, 'MAKE STICKS'))
        say(s, 'USE STICKS')
        check('USE STICKS: in the hand, 30 minutes, no ignition',
              b(s, 'sticks_on') == 3 and abs(f(s, 's_hour') - hour - 1) < 1e-6
              and 'USE THE APPROPRIATE ITEM FIRST.' in say(s, 'MAKE FIRE'))
        hour = f(s, 's_hour')
        say(s, 'USE GLASS')
        check('USE GLASS at 10 a.m. under a clear sky: 15 minutes, in the hand; its flag lasts until time passes, '
              'so MAKE FIRE asks for an ignition (msg 25, as the ROM)',
              abs(f(s, 's_hour') - hour - .25) < 1e-6 and b(s, 'it_place', 39) == 3
              and 'USE THE APPROPRIATE ITEM FIRST.' in say(s, 'MAKE FIRE'))


def thermal():
    """USE FIRE then a health step in the cold: the ROM's rate and body."""
    path = HERE / 'build/re_thermal/results.json'
    if not path.exists():
        print('  near-fire thermal: SKIP (run tools/re_thermal_probe.py)')
        return
    rom = [c for c in json.loads(path.read_text()) if c['kind'] == 'fire']
    idle = L.until('idle', 20000)
    done = f'until:{L["idle"] + 9:04X}:6000'
    code = []
    for t in ('thermal_rate', 'thermal_integrate', 'thermal_condition'):
        code += [0x20, L[t] & 255, L[t] >> 8]
    code += [0x4C, L['idle'] & 255, L['idle'] >> 8]
    load = [0x20, L['thermal'] & 255, L['thermal'] >> 8, 0x4C, L['idle'] & 255, L['idle'] >> 8]
    steps = [idle] + [f'poke:{L["idle"] + i:04X}:{v:02X}' for i, v in enumerate(load)]
    steps += [L.poke(n, v, i) for n, x in (('s_metabolic', 1.65), ('s_step', 0)) for i, v in enumerate(encode(x))]
    steps += [f'until:{L["idle"] + 3:04X}:6000', idle] + [f'poke:{L["idle"] + i:04X}:{v:02X}' for i, v in enumerate(code)]
    steps += [L.poke('fire_near', 1)]
    for c in rom:
        for n, x in (('s_insul', c['index']), ('s_metabolic', 1.65), ('s_body', 98.6), ('s_step', 60)):
            steps += [L.poke(n, v, i) for i, v in enumerate(encode(x))]
        steps += [L.poke('felt_temp', c['air'] & 255), L.poke('felt_temp', (c['air'] >> 8) & 255, 1), L.poke('wet_mode', 0),
                  L.poke('shelter_inside', 0), done, L.peek('s_therm_rate', 5), L.peek('s_body', 5), idle]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    bad = [(c['air'], fp(r.mem(L['s_therm_rate'], 5, k)), c['computed_rate'], fp(r.mem(L['s_body'], 5, k)), c['result'])
           for k, c in enumerate(rom)
           if abs(fp(r.mem(L['s_therm_rate'], 5, k)) - c['computed_rate']) > 2e-7
           or abs(fp(r.mem(L['s_body'], 5, k)) - c['result']) > 3e-7]
    check(f'near fire, {len(rom)} air temperatures -40..110 F: rate and body after 60 min = ROM m0B2 with $45E9 = 1 '
          '(+25 F, 127 F when bit 7 is set)', not bad, bad)


def light():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        poke(s, 'nature_frequency', 0)
        poke(s, 'it_place', 2, 41)                      # a FIRSTAID KIT in the pack
        say(s, 'REST', '13 H')
        check('night: no light ($0D5D = 0 at the health step)', b(s, 'light') == 0)
        check('USE FIRSTAID KIT at night: msg 53', 'INSUFFICIENT LIGHT' in say(s, 'USE FIRSTAID KIT'))
        say(s, 'USE FLASHLIGHT')
        check('USE FLASHLIGHT: one use of 6, light', b(s, 'it_pack_lo', 66) == 5 and b(s, 'light') == 1)
        hour = f(s, 's_hour')
        text = say(s, 'USE FIRSTAID KIT')
        check('USE FIRSTAID KIT with the flashlight: accepted, 30 minutes; then no light (flag cleared by time)',
              'INSUFFICIENT' not in text and abs(f(s, 's_hour') - hour - .5) < 1e-6
              and b(s, 'light') == 0 and b(s, 'camp_use') & 8 == 0, text)
        poke(s, 'it_pack_lo', 0, 66)
        check('USE FLASHLIGHT without batteries: msg 83', 'BATTERIES ARE USED UP' in say(s, 'USE FLASHLIGHT'))
        poke(s, 'it_pack_lo', 0, 38)
        text = say(s, 'USE MATCHES')
        check('USE MATCHES with none left: msg 88, not in use',
              'THE MATCHES HAS BEEN USED UP.' in text and b(s, 'camp_use') & 1 == 0, text)


def water():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        poke(s, 'nature_frequency', 0)
        ground = b(s, 'it_gnd_lo', 22) + 256 * b(s, 'it_gnd_hi', 22)
        poke(s, 'weather_sky', 2)
        text = say(s, 'GET RAIN', '40')
        check('GET RAIN, canteen full: 160 oz on the cell, msg 186',
              'MORE THAN TWO QUARTS' in text and b(s, 'it_gnd_lo', 22) + 256 * b(s, 'it_gnd_hi', 22) == ground + 160
              and b(s, 'water_untreated') == 0, text)
        poke(s, 'weather_sky', 0)
        check('GET RAIN without rain: msg 1', 'SORRY, THAT ITEM IS NOT AVAILABLE.' in say(s, 'GET RAIN'))
        before = f(s, 's_defw')
        check('DRINK more than .2 x 165 lb: msg 87', "DON'T BE RIDICULOUS!" in say(s, 'DRINK WATER', '34')
              and f(s, 's_defw') == before)
        say(s, 'DRINK WATER', '4')
        check('DRINK 4 oz: water deficit -4 x .38 (frozen $4C7A = 70/120)', abs(before - f(s, 's_defw') - 1.52) < 1e-6,
              before - f(s, 's_defw'))
        poke(s, 'weather_sky', 3)
        check('GET SNOW 200 oz: msg 64 (160)', 'AMOUNT OF 160 OUNCES' in say(s, 'GET SNOW', '200'))
        poke(s, 'weather_sky', 0)
        check('BOIL WATER without UTENSILS in use: msg 25', 'USE THE APPROPRIATE ITEM FIRST.' in say(s, 'BOIL WATER', '10'))
        hour = f(s, 's_hour')
        say(s, 'USE UTENSILS')
        check('USE UTENSILS: 15 minutes, set down', abs(f(s, 's_hour') - hour - .25) < 1e-6 and b(s, 'it_place', 73) == 0)
        check('BOIL WATER without a fire or STOVE: msg 65', 'NEED A FIRE' in say(s, 'BOIL WATER', '10'))
        poke(s, 'it_place', 2, 71)
        check('USE STOVE without FUEL and fire: msg 85', 'BOTH FUEL AND FIRE' in say(s, 'USE STOVE'))
        say(s, 'USE MATCHES')
        say(s, 'USE FUEL')
        say(s, 'USE STOVE')
        hour = f(s, 's_hour')
        can = b(s, 'it_pack_lo', 22)
        ground = b(s, 'it_gnd_lo', 22) + 256 * b(s, 'it_gnd_hi', 22)
        say(s, 'BOIL WATER', '10')
        check('BOIL WATER with the STOVE: 15 minutes, 10 oz from the canteen to the cell, care selector 22',
              abs(f(s, 's_hour') - hour - .25) < 1e-6 and b(s, 'it_pack_lo', 22) == can - 10
              and b(s, 'it_gnd_lo', 22) + 256 * b(s, 'it_gnd_hi', 22) == ground + 10
              and b(s, 'medical_actions', 21) == 1)


def river_and_search():
    m = flat()
    m[64 + 40 * 112 + 11] = 138                          # water east of the start (10, 40)
    with tempfile.TemporaryDirectory() as tmp, a2test.Session(disk_with(tmp, m)) as s:
        s.step(IDLE)
        poke(s, 'nature_frequency', 0)
        say(s, 'DRINK WATER', '16')
        hour = f(s, 's_hour')
        say(s, 'FILL CANTEEN')
        check('FILL CANTEEN on the crash pile: from the pile, safe, no time',
              b(s, 'it_pack_lo', 22) == 64 and b(s, 'water_untreated') == 0 and f(s, 's_hour') == hour)
        poke(s, 'it_x', 0, 22)                            # the pile elsewhere
        say(s, 'DRINK WATER', '16')
        say(s, 'FILL CANTEEN')
        check('FILL CANTEEN at the bank: 160 oz of river water on the cell, canteen 64, untreated, no time',
              b(s, 'it_pack_lo', 22) == 64 and b(s, 'it_gnd_lo', 22) == 144 and b(s, 'water_untreated') == 1
              and f(s, 's_hour') == hour)
        say(s, 'DRINK WATER', '16')
        say(s, 'FILL CANTEEN')
        check('the canteen stays contaminated ($5B38: B2[22] AND $4B48)', b(s, 'water_untreated') == 1)
        limits = s.step(L.peek('load_limits', 8)).data
        say(s, 'DRINK WATER', '16')
        used = s.step(L.peek('load_used', 2)).data      # the weight now: any refill exceeds it
        poke(s, 'load_limits', used)
        before = (b(s, 'it_pack_lo', 22), b(s, 'it_gnd_lo', 22))
        check('a transfer over the load limits is refused, atomic',
              'TOO MUCH WEIGHT' in say(s, 'FILL CANTEEN') and before == (b(s, 'it_pack_lo', 22), b(s, 'it_gnd_lo', 22)))
        poke(s, 'load_limits', limits)
        # Away from the river, no pile: the timed search, seeded.
        poke(s, 'px', 30, 1)
        freq = f(s, 'weather_frequency')
        for seed in (0x1388, 0x40F8):                     # RND .61 (not found), then .031 (found)
            poke(s, 'weather_seed', seed.to_bytes(4, 'little'))
            _, r = lehmer(seed)
            p = 60 * freq * .00033
            hour = f(s, 's_hour')
            text = say(s, 'GET WATER', 'Y', '1 H', '10')
            found = r <= p
            check(f'search 1 h on open ground, RND {r:.4f} vs p {p:.4f}: '
                  + ('msg 56 as the result, 160 oz untreated' if found else 'msg 62 and the condensation hint'),
                  (('YOU WERE SUCCESSFUL!' in text) if found else ('NO GROUND WATER' in text))
                  and abs(f(s, 's_hour') - hour - 1) < 1e-6, text)
            if found:
                check('found water: 160 oz on the cell, 10 oz to the canteen (asked), untreated',
                      b(s, 'it_gnd_lo', 22) == 150 and b(s, 'it_x', 22) == 30 and b(s, 'water_untreated') == 1)
        poke(s, 'px', 40, 1)
        check('no search: the condensation hint, no time', 'MAKE WATER BY CONDENSATION' in say(s, 'GET WATER', 'N')
              or 'PLANTS HIGH IN WATER' in rows(s))
        say(s, 'USE RAINCOAT')
        poke(s, 'weather_sky', 0)
        hour = f(s, 's_hour')
        ground = b(s, 'it_gnd_lo', 22) if b(s, 'it_x', 22) == b(s, 'px', 1) else 0
        text = say(s, 'MAKE WATER', '2 H')
        check('MAKE WATER 2 h under the RAINCOAT: 12 oz on the cell, 150 minutes',
              'CONDENSED 12 OUNCES' in text and b(s, 'it_gnd_lo', 22) == ground + 12
              and abs(f(s, 's_hour') - hour - 2.5) < 1e-6, text)


def giardia():
    """$5CF7: RND <= .2 / ((level + base) / 10); 100 seeds at 2,000 and 10,000 ft."""
    idle = L.until('idle', 20000)
    with a2test.Session(DISK) as s:
        s.step(idle)
        x, y = b(s, 'px', 1), b(s, 'py', 1)
        level = 10                                        # the cell at 1,000 ft above the base
        s.step(f'poke:{0x7000 + 64 + y * 112 + x:04X}:{level:02X}')
        code = [0x20, L['thermal'] & 255, L['thermal'] >> 8, 0x4C, L['idle'] & 255, L['idle'] >> 8]
        for i, v in enumerate(code):
            s.step(f'poke:{L["idle"] + i:04X}:{v:02X}')
        s.step(f'until:{L["idle"] + 3:04X}:6000')
        s.step(idle)
        code = [0x20, L['water_hazard'] & 255, L['water_hazard'] >> 8, 0x4C, L['idle'] & 255, L['idle'] >> 8]
        for i, v in enumerate(code):
            s.step(f'poke:{L["idle"] + i:04X}:{v:02X}')
        for feet in (2000, 10000):
            s.step(f'poke:700A:{feet // 100 - level:02X}')     # M_BASE = MAP + 10
            p = .2 / (feet / 100 / 10)
            got = want = 0
            seed = 12345
            for k in range(100):
                seed = (seed * 1103515245 + 12345) % 67099547
                poke(s, 'weather_seed', seed.to_bytes(4, 'little'))
                poke(s, 'water_drinking_untreated', 1)
                poke(s, 'injury_active', 0, 11)
                poke(s, 'injury_prevented', 0, 11)
                s.step(f'until:{L["idle"] + 3:04X}:6000')
                s.step(idle)
                got += b(s, 'injury_active', 11)
                want += lehmer(seed)[1] <= p
            check(f'giardia at {feet} ft: {got} infections in 100 drinks of untreated water '
                  f'(p = {p:.2f}; the same RND in Python: {want})', got == want, (got, want))


def menu():
    """The grid (src/menu.s): MAKE FIRE/STICKS/WATER, BOIL WATER, USE of the
    camp items and of the fire, DOUSE FIRE only while a fire burns."""
    from test_menu_bar import choose, move_to, press, grid_cells, RET, ESC
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        poke(s, 'nature_frequency', 0)
        press(s, RET)
        verbs = sum(grid_cells(s), [])
        check('grid: MAKE and BOIL, no DOUSE without a fire', 'MAKE' in verbs and 'BOIL' in verbs
              and 'DOUSE' not in verbs, verbs)
        move_to(s, 'MAKE')
        press(s, RET)
        check('MAKE lists FIRE STICKS WATER', sum(grid_cells(s), [])[:3] == ['FIRE', 'STICKS', 'WATER'], grid_cells(s))
        press(s, ESC)
        move_to(s, 'USE')
        press(s, RET)
        items = sum(grid_cells(s), [])
        check('USE lists MATCHES, MAGNF GLASS, FUEL, the medicine, FLASHLGHT', all(
            ('MATCHES' in items, 'MAGNF' in items, 'FUEL' in items, 'OXYGEN' in items, 'FLASHLGHT' in items)), items)
        press(s, ESC)
        check('USE MATCHES from the grid', choose(s, 'USE', 'MATCHES') == ('USE MATCHES', 38)
              and b(s, 'camp_use') & 1)
        check('MAKE FIRE from the grid', choose(s, 'MAKE', 'FIRE') == ('MAKE FIRE', 0) and b(s, 'fire_on'))
        press(s, ESC)
        press(s, RET)
        check('DOUSE once a fire burns', 'DOUSE' in sum(grid_cells(s), []))
        check('USE FIRE from the grid (the fire after the items)', choose(s, 'USE', 'FIRE') == ('USE FIRE', 88)
              and b(s, 'fire_near'))
        check('DOUSE FIRE from the grid', choose(s, 'DOUSE') == ('DOUSE FIRE', 0) and not b(s, 'fire_on'))
        move_to(s, 'BOIL')
        s.step(f'press:{RET}')
        s.step(f'until:{L["keyboard_wait"]:04X}:40000')
        text = rows(s)
        s.step(f'key:{ESC}')
        s.step(IDLE)
        check('BOIL WATER from the grid: the ounces asked', 'HOW MANY OZ' in text
              and s.step(L.peek('inbuf', 10)).data.startswith(b'BOIL WATER'), text)


def main():
    menu()
    fire()
    thermal()
    light()
    water()
    river_and_search()
    giardia()
    print(f'Lot 2, fire, light and water: {"OK" if not fails else "FAILED: " + ", ".join(fails)}')
    raise SystemExit(bool(fails))


if __name__ == '__main__':
    main()
