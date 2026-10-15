#!/usr/bin/env python3
"""Lot 7 orientation (docs/ORIENTATION.md): the original's rules, measured on
the ROM by tools/re_orientation_probe.py, played on the port.

LOOK N/E/S/W/AZ need a direction aid in use (msg 42), but a COMPASS at hand
is put in use by the LOOK itself (port, 14 October 2026: the grid offers
NORTH..WEST in every state); USE COMPASS, WATCH,
ALTIMETER exclude each other; the watch estimate and the shadow stick give
the formulas of T$10/S$0C; LOOK SUN follows the Sun of sky_position, LOOK
STARS the celestial pole of the hemisphere; USE MAP opens the map.
"""
import math
import sys
from common import L, DISK, a2test, fp, text_screen

UNITS = 560
MAP = 0x7000                     # region header (src/game.s M_LAT = MAP + 12)
WAIT = f"until:{L['idle']:04X},{L['keyboard_wait']:04X}:20000"


def cmd(text):
    return [f'key:{text}', 'wait:1', WAIT]


def poke(name, *values):
    return [L.poke(name, v, i) for i, v in enumerate(values)]


SNAP = [L.peek('heading', 2), L.peek('orient_aid'), L.peek('s_elap', 5), L.peek('s_hour', 5),
        L.peek('it_place', 4, 52), L.peek('sky_bearing', 2), L.peek('orient_lcg', 4),
        L.peek('weather_seed', 4), 'peek:700C:1', 'peek:7018:1', 'peek:0400:1024']


def snaps(r, n):
    out = []
    for i in range(n):
        lat, mag = r.mem(MAP + 12, 1, i)[0], r.mem(MAP + 24, 1, i)[0]
        out.append(dict(heading=int.from_bytes(r.mem(L['heading'], 2, i), 'little'),
                        aid=r.mem(L['orient_aid'], 1, i)[0], elapsed=fp(r.mem(L['s_elap'], 5, i)),
                        hour=fp(r.mem(L['s_hour'], 5, i)), place=list(r.mem(L['it_place'] + 52, 4, i)),
                        sun=int.from_bytes(r.mem(L['sky_bearing'], 2, i), 'little'),
                        lcg=bytes(r.mem(L['orient_lcg'], 4, i)), seed=bytes(r.mem(L['weather_seed'], 4, i)),
                        lat=lat - 256 * (lat > 127), mag=mag - 256 * (mag > 127),
                        text=' '.join(line.strip() for line in text_screen(r.mem(0x400, 1024, i)))))
    return out


def units(deg):
    return math.floor(deg * 560 / 360 + .5)


def wrap(u):
    return u % UNITS


def watch(base, sun, hour, est, south=False):
    """T$10/S$0C $5A3C on the port's units (the Sun in units)."""
    h12 = hour - 12 if hour > 12 else hour
    a = h12 * 57.296
    deg = math.floor(a * (.262 if south else -.262)) - est + (180 if math.floor(a) >= 344 else 0)
    return wrap(base + sun + units(deg))


def lehmer(seed):
    s = int.from_bytes(seed, 'little')
    for _ in range(13):
        s <<= 1
        if s >= 0x03FFDB9B:
            s -= 0x03FFDB9B
    return s / 67099547


def shadow(base, minutes, hour, seed, west):
    t = minutes * .00833 + hour
    err = math.floor((lehmer(seed) - .5) * 481 * (1 + .33 * abs(12 - t)) / minutes)
    return wrap(base + units(err + (180 if west else 0)))


def lcg_pole(state, lat):
    m = list(state)
    c, a = 0, m[3]
    for x in (2, 1, 0):
        a += m[x] + c
        c, a = a >> 8, a & 255
        m[x] = a
    for x in (3, 2, 1, 0):
        m[x] = (m[x] + 1) & 255
        if m[x]:
            break
    return wrap(units((m[0] >> 2) - 33 + (180 if lat < 0 else 0)))


def near(a, b, tol=1):
    return min((a - b) % UNITS, (b - a) % UNITS) <= tol


def main():
    failures = []

    def check(name, ok):
        print(f'  {name}: {"OK" if ok else "FAIL"}', flush=True)
        if not ok:
            failures.append(name)

    # 1. Day at the crash site (7 h, clear): the rule, the watch, the stick.
    script = ['LOOK N\r', 'USE WATCH\r', 'USE COMPASS\r', 'USE WATCH\r', 'USE ALTIMETER\r', 'LOOK AZ\r',
              'LOOK SUN\r', 'LOOK STARS\r', 'USE WATCH\r', 'LOOK E\r', 'N', '30\r', 'LOOK N\r', 'Y',
              'LOOK COMPASS\r', 'LOOK WATCH\r', 'USE SHADOW\r', 'LOOK N\r', 'E', '2\r', 'LOOK N\r',
              'USE SHADOW\r', 'LOOK E\r', 'W', '30 MIN\r', 'REST 4 H\r', 'USE WATCH\r', 'LOOK SUN\r',
              'LOOK W\r', 'N', '200\r']
    # The ROM's msg 42 cases without a compass at hand (the port puts a
    # carried one in use): the compass is set aside for those commands.
    compass = a2test.run(DISK, [L.until('idle', 20000), L.peek('it_place', 1, 53)],
                         emulator=a2test.A2SHOT).mem(L['it_place'] + 53, 1)[0]
    steps = [L.until('idle', 20000)] + SNAP
    for i, c in enumerate(script):
        aside = i in (0, 5, 20)
        steps += ([L.poke('it_place', 0xFF, 53)] if aside else []) + cmd(c) + SNAP
        steps += [L.poke('it_place', compass, 53)] if aside else []
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    s = snaps(r, len(script) + 1)
    d = dict(zip(['start'] + script, s))
    for i, c in enumerate(script):
        x = s[i + 1]
        print(f'    {c!r:16} hd={x["heading"]:3} aid={x["aid"]} el={x["elapsed"]:.3f} | {x["text"][-90:]}')
    check('LOOK N without an aid in use: msg 42, view and clock unchanged',
          'FIRST PUT DIRECTION AID IN USE' in s[1]['text'] and s[1]['heading'] == s[0]['heading']
          and s[1]['elapsed'] == 0)
    check('USE WATCH, COMPASS, WATCH, ALTIMETER: one aid at a time, in hand, no time',
          [x['aid'] for x in s[2:6]] == [2, 1, 2, 0] and s[5]['place'][1:4] == [3, 3, 3]
          and all(x['elapsed'] == 0 for x in s[2:6]))
    check('LOOK AZ without an aid: msg 42', 'FIRST PUT DIRECTION AID' in s[6]['text'])
    sun7 = s[7]['heading']
    check('LOOK SUN turns the view to the azimuth of sky_position',
          sun7 == s[7]['sun'] and near(sun7, units(85), 2))
    check('LOOK STARS by day: msg 52', 'STARS ARE NOT VISIBLE' in s[8]['text'] and s[8]['heading'] == sun7)
    w7 = watch(140, sun7, 7.0, 30)
    check(f'watch at 7 h, LOOK E, N, estimate 30: msg 189, 13, heading {w7} (ROM: 219 deg)',
          'ESTIMATE NORTH-SOUTH' in s[10]['text'] and 'HOUR HAND POINTED AT THE SUN' in s[11]['text']
          and near(s[12]['heading'], w7) and near(s[12]['heading'], units(219), 2) and s[12]['elapsed'] == 0)
    check('watch, Y: OK, WHAT NEXT? and the view unchanged',
          'OK, WHAT NEXT' in s[14]['text'] and s[14]['heading'] == s[12]['heading'])
    deg = (math.floor(s[15]['heading'] * 360 / 560 + .5) - s[15]['mag']) % 360
    check(f'LOOK COMPASS: msg 256, {deg} degrees magnetic', f'{deg} DEGREES MAGNETIC' in s[15]['text'])
    check('LOOK WATCH: see the STATUS display', 'SEE STATUS DISPLAY' in s[16]['text'])
    check('USE SHADOW by a clear day: the stick alone in use', s[17]['aid'] == 4 and s[17]['elapsed'] == 0)
    sh1 = shadow(0, 120, 7.0, s[19]['seed'], False)
    check(f'shadow, LOOK N, E, 2 hours: msg 29, 48, heading {sh1}, two hours spent, stick used up',
          'TIP OF THE SHADOW' in s[18]['text'] and 'SHADOW TIP MOVE' in s[19]['text']
          and near(s[20]['heading'], sh1, 2) and abs(s[20]['elapsed'] - 2) < 1e-4 and s[20]['aid'] == 0)
    check('after the observation: msg 42 again', 'FIRST PUT DIRECTION AID' in s[21]['text'])
    sh2 = shadow(140, 30, 9.0, s[24]['seed'], True)
    check(f'shadow, LOOK E, W, 30 MIN: heading {sh2} (+180 for W), 30 minutes',
          near(s[25]['heading'], sh2, 2) and abs(s[25]['elapsed'] - 2.5) < 1e-4)
    sun13 = s[28]['heading']
    w13 = watch(420, sun13, 13.5, 200)
    check(f'REST ends the watch; at 13.5 h, LOOK W, N, 200: heading {w13}',
          s[26]['aid'] == 0 and abs(s[28]['hour'] - 13.5) < 1e-4 and sun13 == s[28]['sun']
          and near(s[31]['heading'], w13))

    # 1b. The port: LOOK EAST, then NORTH, with the compass only carried.
    steps = [L.until('idle', 20000)] + SNAP
    for c in ('LOOK EAST\r', 'LOOK NORTH\r'):
        steps += cmd(c) + SNAP
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    s = snaps(r, 3)
    check('LOOK EAST, NORTH with a carried compass: in use (in hand), magnetic headings',
          s[0]['aid'] == 0 and s[1]['aid'] == 1 and s[1]['place'][1] == 3
          and 'MAGNETIC, NOT TRUE' in s[1]['text']
          and near(s[1]['heading'], wrap(140 + units(s[1]['mag'])), 4)
          and near(s[2]['heading'], wrap(units(s[2]['mag'])), 4))

    # 2. Night, clouds, latitude and shelter (state poked as in the ROM probe).
    script = [('poke', 'night', 1), ('poke', 'period', 0), 'LOOK SUN\r', 'LOOK STARS\r', ('poke', 'MAP+12', 0xEF), 'LOOK STARS\r',
              ('poke', 'weather_sky', 1), 'LOOK STARS\r', 'USE SHADOW\r', 'USE COMPASS\r', 'USE WATCH\r',
              ('poke', 'night', 0), ('poke', 'period', 2), ('poke', 'weather_visibility', 138), 'USE WATCH\r', 'LOOK SUN\r',
              ('poke', 'weather_visibility', 139), ('poke', 'weather_sky', 0), 'LOOK SUN\r',
              ('poke', 'shelter_inside', 1), 'LOOK N\r', 'LOOK STARS\r', ('poke', 'shelter_inside', 0),
              'PAN N\r', 'PAN SUN\r', 'USE MAP\r']
    steps = [L.until('idle', 20000)] + SNAP
    n = 1
    for c in script:
        if isinstance(c, tuple):
            name, v = c[1], c[2]
            off = 0
            if '+' in name:
                name, off = name.split('+')
                off = int(off)
            steps.append(f'poke:{(MAP if name == "MAP" else L[name]) + off:04X}:{v:02X}')
            continue
        steps += cmd(c) + SNAP
        n += 1
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    s = snaps(r, n)
    typed = [c for c in script if not isinstance(c, tuple)]
    for i, c in enumerate(typed):
        x = s[i + 1]
        print(f'    {c!r:16} hd={x["heading"]:3} aid={x["aid"]} | {x["text"][-90:]}')
    check('LOOK SUN at night: msg 41', 'SUN IS OBSCURED' in s[1]['text'])
    north = lcg_pole(s[1]['lcg'], 38)
    check(f'LOOK STARS, clear night in the Sierra: heading {north} (north +-33 deg)',
          s[2]['heading'] == north and near(north, 0, units(33) + 1))
    south = lcg_pole(s[2]['lcg'], -17)
    check(f'LOOK STARS, clear night at latitude -17 (Bolivia): heading {south} (south)',
          s[3]['heading'] == south and near(south, 280, units(33) + 1))
    check('LOOK STARS under clouds: msg 52', 'STARS ARE NOT VISIBLE' in s[4]['text'])
    check('USE SHADOW at night: msg 53', 'INSUFFICIENT LIGHT' in s[5]['text'] and s[5]['aid'] == 0)
    check('USE COMPASS at night (no light needed), then USE WATCH: msg 53, the compass dropped',
          s[6]['aid'] == 1 and 'INSUFFICIENT LIGHT' in s[7]['text'] and s[7]['aid'] == 0)
    check('by day, visibility 138: USE WATCH works, LOOK SUN msg 41',
          s[8]['aid'] == 2 and 'SUN IS OBSCURED' in s[9]['text'])
    check('visibility 139: LOOK SUN turns the view', s[10]['heading'] == s[10]['sun'])
    check('in the shelter: LOOK N and LOOK STARS answer INSIDE SHELTER',
          all('INSIDE SHELTER' in s[i]['text'] for i in (11, 12)))
    check('PAN N, PAN SUN: msg 2 (T$15/S$0A), the view unchanged',
          all('NOT MAKING MUCH SENSE' in s[i]['text'] and s[i]['heading'] == s[12]['heading'] for i in (13, 14)))
    check('USE MAP: the map, in hand', 'CONTOURS' in s[15]['text'] and s[15]['place'][0] == 3)
    print(f'{len(failures)} failures')
    sys.exit(bool(failures))


if __name__ == '__main__':
    main()
