#!/usr/bin/env python3
"""re_orientation_probe.py: the original's orientation rules, on the ROM.

Lot 7 (docs/ORIENTATION.md). Two kinds of runs, both on the unchanged
original (build/SIERRA.woz + build/JOURNEY.dsk, local and ignored):

1. Sessions typed at the original's prompt (as tools/re_parser_probe.py):
   message numbers given to $4E78, short messages ($0EB4), the in-use
   flags B2[53] COMPASS / B2[54] WATCH ($40CD/$40CE), the shadow stick
   $4B4A, the heading $D2/$D3 (degrees), the clock $4C57 and the elapsed
   hours $4C61. State is poked between commands when a case needs it
   (night, clear sky, latitude, $E0/$E1, light $0D5D, shelter $0D5E).
2. The light range of T$0D/S$07 ($5886, the sub-routine that writes $E1)
   run directly, as tools/re_tree_probe.py does, for phases and
   visibilities: LOOK SUN and the watch need $E0 = 0 and $E1 >= 44.

Every formula checked here is the one src/orient.s ports. Usage:
re_orientation_probe.py (prints the checks, writes build/re_orientation/).
"""
import json, math, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test, smalldos  # noqa: E402

A2SHOT = str(HERE.parent / 'dev/tools/a2shot/a2shot')
BOOT = ['wait:5000', 'key:1\\r', 'wait:3000', 'insert:build/JOURNEY.dsk', 'key:\\r', 'wait:3000',
        'key:\\r', 'wait:600', 'key:\\r', 'wait:2400']
PEEKS = ['peek:0650:432', 'peek:40CD:2', 'peek:4B4A:1', 'peek:00D2:2', 'peek:4C57:5', 'peek:4C61:5',
         'peek:00B5:3', 'peek:60A8:2', 'peek:00BC:4']
OUT = HERE / 'build/re_orientation'


def mbf(b):
    if not b[0]:
        return 0.0
    m = int.from_bytes(b[1:], 'big')
    return (-1 if m & 0x80000000 else 1) * (m | 0x80000000) / 2**32 * 2**(b[0] - 128)


def rows(blob):
    out = []
    for r in range(20, 24):
        o = 0x400 + (r % 8) * 128 + (r // 8) * 40 - 0x650
        out.append(bytes(c & 0x7F for c in blob[o:o + 40]).decode('latin1').rstrip())
    return ' | '.join(x for x in out if x)


def session(commands):
    """commands: list of str (typed, '\\r' included) or 'poke:...' steps.
    Returns one record per typed command."""
    steps = BOOT + ['watch:4E78', 'watch:0EB4']
    typed = []
    for c in commands:
        if c.startswith('poke:'):
            steps.append(c)
            continue
        typed.append(c)
        steps += [f'key:{c}', 'wait:1500'] + PEEKS
    out = subprocess.run([A2SHOT, '--disk', 'build/SIERRA.woz'] + steps, capture_output=True,
                         text=True, cwd=HERE, timeout=600).stdout
    records, msgs, dumps = [], [], []
    for line in out.splitlines():
        m = re.match(r'^watch (4E78|0EB4) A=\w\w X=(\w\w)', line)
        if m:
            msgs.append(('m' if m[1] == '4E78' else 's') + str(int(m[2], 16)))
            continue
        m = re.match(r'^([0-9A-F]{4}): ([0-9A-F ]+)$', line)
        if m:
            a, b = int(m[1], 16), bytes.fromhex(m[2])
            if dumps and dumps[-1][0] + len(dumps[-1][1]) == a:
                dumps[-1][1] += b
            else:
                if a == 0x0650:
                    records.append({'msgs': msgs})
                    msgs = []
                dumps.append([a, bytearray(b)])
    n = len(PEEKS)
    for i, rec in enumerate(records):
        d = [x[1] for x in dumps[i * n:(i + 1) * n]]
        rec.update(cmd=typed[i], text=rows(d[0]), compass=d[1][0], watch=d[1][1], shadow=d[2][0],
                   heading=d[3][0] + 256 * d[3][1], hour=mbf(d[4]), elapsed=mbf(d[5]),
                   sun_az=d[6][0] + 256 * d[6][1], sun_alt=d[6][2], lat=d[7][0] - 256 * (d[7][0] > 127),
                   decl=d[7][1] - 256 * (d[7][1] > 127), lcg=bytes(d[8]))
    assert len(records) == len(typed), (len(records), typed, out[-2000:])
    return records


def watch_heading(base, sun_az, hour, est, south):
    """T$10/S$0C $5A3C: hour hand (12-hour dial) on the Sun."""
    h12 = hour - 12 if hour > 12 else hour
    a = h12 * 57.296
    off = math.floor(a * (0.262 if south else -0.262))
    return (base + sun_az + off + (180 if a >= 344 else 0) - est) % 360


def lcg(m):
    """SURV3D $0D2A on $BC-$BF; returns the new state."""
    m = list(m)
    c, a = 0, m[3]
    for x in (2, 1, 0):
        a += m[x] + c
        c, a = a >> 8, a & 255
        m[x] = a
    for x in (3, 2, 1, 0):
        m[x] = (m[x] + 1) & 255
        if m[x]:
            break
    return bytes(m)


def stars_heading(state, lat):
    v = (lcg(state)[0] >> 2) - 33
    return (v + (180 if lat < 0 else 0)) % 360


def shadow_error(minutes, hour, rnd):
    """$59C4: (RND - 0.5) * 481 * (1 + .33 |12 - (hour + minutes/120)|) / minutes."""
    t = minutes * 0.00833 + hour
    return math.floor((rnd - 0.5) * 481 * (abs(12 - t) * 0.33 + 1) / minutes)


def light_range():
    """T$0D/S$07 $5886 on the ROM: $E1 = min(128, INT(V*L/(V+L))/2) by day."""
    out = OUT / 'range'
    out.mkdir(parents=True, exist_ok=True)
    journey = smalldos.Disk((HERE / 'build/JOURNEY.dsk').read_bytes())
    journey.flip = True
    module = journey.run(0x0d, 0x07, 8)
    state = bytearray((HERE / 'build/game.bin').read_bytes()[0x4000:0x8000])
    state[0x1800:0x1800 + len(module)] = module
    (out / 'state.bin').write_bytes(state)
    (out / 'driver.bin').write_bytes(bytes((0x20, 0x86, 0x58, 0x4c, 0, 8)))
    (out / 'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BRUN DRIVER"\n')
    d = out / 'range.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'), '--out', str(d), '--bas',
                    f'HELLO={out / "hello.bas"}', '--bin', f'STATE={out / "state.bin"}@0x4000', '--bin',
                    f'DRIVER={out / "driver.bin"}@0x0800'], check=True, capture_output=True)
    cases = [(phase, v) for phase in (0, 1) for v in (24, 60, 100, 138, 139, 140, 162, 163, 164, 200, 240)]
    steps = ['until:0800:20000']
    for phase, v in cases:
        steps += [f'poke:4B49:{phase:02X}', f'poke:4B91:{v:02X}', 'poke:47F9:00',
                  'until:0803:1000', 'peek:00E1:1', 'peek:4B96:1', 'until:0800:1000']
    r = a2test.run(d, steps, emulator=a2test.A2SHOT, timeout=900)
    rows_ = []
    for i, (phase, v) in enumerate(cases):
        e1, b96 = r.dumps[2 * i][0], r.dumps[2 * i + 1][0]
        light = 240 if phase else 192
        want = int(v * light / (v + light))
        assert b96 == want, (phase, v, b96, want)
        assert e1 == (128 if want >> 1 >= 60 else want >> 1), (phase, v, e1)
        rows_.append(dict(phase=phase, visibility=v, range=e1, sun=e1 >= 44))
    hidden = {p: max(x['visibility'] for x in rows_ if x['phase'] == p and not x['sun']) for p in (0, 1)}
    print(f'{len(cases)} light ranges $E1 = min(128, INT(V*L/(V+L))/2), L 192 dawn/dusk, 240 day: OK;'
          f' Sun hidden for V <= {hidden[1]} by day, <= {hidden[0]} at dawn/dusk')
    return rows_



def fp(x):
    """Applesoft 5-byte float."""
    if x == 0:
        return bytes(5)
    m, e = math.frexp(abs(x))
    v = round(m * 2**32)
    if v >= 2**32:
        v, e = v >> 1, e + 1
    v = (v & 0x7FFFFFFF) | (0x80000000 if x < 0 else 0)
    return bytes([e + 128]) + v.to_bytes(4, 'big')


def look_module():
    """T$10/S$0C run alone with chosen inputs: exact watch and shadow
    formulas. RND ($0321) returns a poked constant; the heading setter
    ($0DC9) stores without wrapping; view and clock exits return."""
    out = OUT / 'look'
    out.mkdir(parents=True, exist_ok=True)
    journey = smalldos.Disk((HERE / 'build/JOURNEY.dsk').read_bytes())
    journey.flip = True
    module = bytearray(journey.run(0x10, 0x0c, 4))
    module = module.replace(bytes.fromhex('4C00B0'), bytes.fromhex('4CC60D'))
    game = (HERE / 'build/game.bin').read_bytes()
    state = bytearray(game[0x4000:0x8000])
    state[0x1800:0x1800 + len(module)] = module
    state[0xD21:0xD25] = bytes.fromhex('8E000960')        # message: X -> $0900
    state[0xD2A:0xD2E] = bytes.fromhex('8E010960')        # message, continue: X -> $0901
    state[0xD03] = 0x60                                    # clock: back to the driver
    low = bytearray(game[0x0D2A:0x0DE0])                   # $0D2A LCG ... jump table

    def o(a):
        return a - 0x0D2A
    low[o(0x0D41):o(0x0D41) + 5] = bytes.fromhex('86D285D360')     # STX $D2 STA $D3 RTS
    low[o(0x0DC6):o(0x0DC6) + 3] = bytes.fromhex('60EAEA')         # view: back to the driver
    low[o(0x0DC9):o(0x0DC9) + 3] = bytes.fromhex('4C410D')
    low[o(0x0DD2):o(0x0DD2) + 4] = bytes.fromhex('8E030960')       # short message
    rnd = bytes.fromhex('A940A0034CF9EA')                            # FAC = ($0340)
    (out / 'state.bin').write_bytes(state)
    (out / 'low.bin').write_bytes(low)
    (out / 'rnd.bin').write_bytes(rnd)
    (out / 'driver.bin').write_bytes(bytes((0x20, 0x00, 0x58, 0x4c, 0, 8)))
    (out / 'hello.bas').write_text('10 PRINT CHR$(4);"BLOAD STATE"\n20 PRINT CHR$(4);"BLOAD LOW"\n'
                                   '30 PRINT CHR$(4);"BLOAD RND"\n40 PRINT CHR$(4);"BRUN DRIVER"\n')
    d = out / 'look.dsk'
    subprocess.run([sys.executable, str(HERE.parent / 'dev/tools/dos33.py'), '--out', str(d), '--bas',
                    f'HELLO={out / "hello.bas"}', '--bin', f'STATE={out / "state.bin"}@0x4000',
                    '--bin', f'LOW={out / "low.bin"}@0x0D2A', '--bin', f'RND={out / "rnd.bin"}@0x0321',
                    '--bin', f'DRIVER={out / "driver.bin"}@0x0800'], check=True, capture_output=True)

    def poke(addr, data):
        return [f'poke:{addr + i:04X}:{b:02X}' for i, b in enumerate(data)]

    def common(noun, compass, watch, shadow, hour, heading=128):
        return (poke(5, [noun, 14]) + poke(0x0D5E, [0]) + poke(0x40CD, [compass, watch]) + poke(0x4B4A, [shadow])
                + poke(0x4C57, fp(hour)) + poke(0xD2, [heading & 255, heading >> 8]) + poke(0x4BC6, [0, 0])
                + poke(0x0900, [0, 0, 0, 0]) + poke(0xE0, [0, 128]))

    def typing(text):        # one key at a time, once the module waits for it
        return [s for c in text for s in ('wait:20', 'press:' + ('\\r' if c == '\r' else c))]

    tail = ['until:0803:3000', 'peek:0900:4', 'peek:00D2:2', 'peek:4BC6:2', 'until:0800:1000']
    steps, cases = ['until:0800:20000'], []
    # Watch: (noun, hour, Sun azimuth, sin lat, sin dec, estimate)
    for noun, hour, az, sl, sd, est in ((146, 7.0, 85, .6157, .2816, 30), (148, 13.0, 216, .6157, .2816, 200),
                                        (145, 15.5, 250, .6157, .2816, 0), (147, 18.25, 290, .6157, .2816, 359),
                                        (145, 9.0, 60, -.2924, .2816, 45), (146, 16.0, 280, -.2924, -.30, 123),
                                        (145, 12.0, 180, .6157, .2816, 0), (145, 6.0, 70, .6157, .2816, 10)):
        cases.append(('watch', noun, hour, az, sl, sd, est))
        steps += common(noun, 0, 1, 0, hour) + poke(0xB5, [az & 255, az >> 8]) + poke(0x4CDE, fp(sl)) \
            + poke(0x4CE8, fp(sd)) + typing('N' + str(est) + '\r') + tail
    # Shadow: (noun, hour, answer, typed hours, RND)
    for noun, hour, ans, typed, r in ((145, 7.0, 'E', '2', .1), (146, 9.0, 'W', '0', .9),
                                      (147, 10.0, 'E', '1.5', .25), (148, 15.0, 'E', '12', .5),
                                      (145, 11.0, 'W', '.25', .0), (145, 8.0, 'E', '24', .999)):
        cases.append(('shadow', noun, hour, ans, typed, r))
        steps += common(noun, 0, 0, 1, hour) + poke(0x0340, fp(r)) + typing(ans + typed + '\r') + tail
    res = a2test.run(d, steps, emulator=a2test.A2SHOT, timeout=900)
    rows_ = []
    for i, c in enumerate(cases):
        msg, hd, minutes = res.dumps[3 * i], res.dumps[3 * i + 1], res.dumps[3 * i + 2]
        heading = int.from_bytes(hd, 'little', signed=True) % 360
        minutes = int.from_bytes(minutes, 'little')
        card = {145: 0, 146: 90, 147: 180, 148: 270}[c[1]]
        if c[0] == 'watch':
            _, noun, hour, az, sl, sd, est = c
            south = sd - sl >= 0
            want = watch_heading(card, az, hour, est, south)
            assert (heading, minutes, msg[1]) == (want, 0, 201 if south else 13), (c, heading, want, msg.hex())
            rows_.append(dict(method='watch', cardinal=card, hour=hour, sun_az=az, south=south, estimate=est,
                              heading=heading))
        else:
            _, noun, hour, ans, typed, r = c
            h = float(typed)
            m = int(h) * 60 + (round((h - int(h)) * 60) if '.' in typed else 0) or 10
            want = (card + shadow_error(m, hour, r) + (180 if ans == 'W' else 0)) % 360
            assert (heading, minutes, msg[1]) == (want, m, 48), (c, heading, want, minutes, m, msg.hex())
            rows_.append(dict(method='shadow', cardinal=card, hour=hour, answer=ans, typed=typed, rnd=r,
                              minutes=m, heading=heading))
    print(f'{len(cases)} module runs: watch heading = cardinal + Sun az + INT(+-.262*57.296*h12)'
          ' (+180 past 6 on the dial) - estimate; shadow heading = cardinal'
          ' + INT((RND-.5)*481*(1+.33|12-t|)/min) (+180 for W), minutes typed (0 -> 10): OK')
    return rows_

def check(rec, msgs=None, text=None):
    if msgs is not None:
        assert rec['msgs'] == msgs, (rec['cmd'], rec['msgs'], msgs, rec['text'])
    if text is not None:
        assert text in rec['text'], (rec['cmd'], rec['text'])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'range': light_range(), 'module': look_module()}

    # 1. The rule, the watch at 7 h and 13 h, exclusion, time.
    r = session(['LOOK N\\r', 'CARRY COMPASS\\r', 'LOOK N\\r', 'LOOK SUN\\r', 'USE WATCH\\r', 'LOOK E\\r', 'N',
                 '30\\r', 'LOOK N\\r', 'Y', 'USE COMPASS\\r', 'LOOK S\\r', 'PACK COMPASS\\r', 'LOOK W\\r',
                 'USE WATCH\\r', 'USE ALTIMETER\\r', 'LOOK N\\r', 'USE WATCH\\r', 'REST\\r', '6\\r', 'LOOK N\\r',
                 'USE WATCH\\r', 'LOOK SUN\\r', 'LOOK W\\r', 'N', '200\\r', 'LOOK COMPASS\\r', 'LOOK WATCH\\r',
                 'LOOK ALTIMETER\\r'])
    for x in r:
        print(f"  {x['cmd']:18} {','.join(x['msgs']):12} cw={x['compass']}{x['watch']} "
              f"hd={x['heading']:3} sun={x['sun_az']}/{x['sun_alt']} h={x['hour']:.3f} | {x['text'][:70]}")
    check(r[0], ['m42'])
    check(r[1], ['m10'])
    check(r[2], ['m42'])                    # carrying the compass is not using it
    check(r[3], [])
    assert r[3]['heading'] == r[3]['sun_az']
    check(r[4], ['m10'])
    assert (r[4]['compass'], r[4]['watch'], r[4]['elapsed']) == (0, 1, 0.0)
    check(r[5], ['m189'])
    check(r[6], ['m13'])                    # Sierra: sin(dec) < sin(lat), hour hand on the Sun
    w7 = watch_heading(90, r[3]['sun_az'], 7.0, 30, False)
    assert r[7]['heading'] == w7 and r[7]['elapsed'] == 0.0, (r[7]['heading'], w7)
    check(r[9], ['m10'])                    # Y: the player uses LOOK SUN himself
    assert r[9]['heading'] == 0             # the cardinal is set, no view yet
    check(r[10], ['m10'])
    assert (r[10]['compass'], r[10]['watch']) == (1, 0)
    check(r[11], ['m44'])
    check(r[13], ['m44'])                   # PACK keeps B2[53]: still in use
    check(r[14], ['m10'])
    assert (r[14]['compass'], r[14]['watch']) == (0, 1)
    check(r[15], ['m10'])
    assert (r[15]['compass'], r[15]['watch']) == (0, 0)
    check(r[16], ['m42'])
    assert r[19]['watch'] == 0 and r[19]['hour'] == 13.0   # time spent clears the watch
    check(r[20], ['m42'])
    w13 = watch_heading(270, r[22]['sun_az'], 13.0, 200, False)
    assert r[25]['heading'] == w13, (r[25]['heading'], w13)
    check(r[26], ['m0'])                   # message 256: X wraps to 0
    assert str((r[26]['heading'] - r[26]['decl']) % 360) in r[26]['text']
    check(r[27], [], 'SEE STATUS DISPLAY')
    check(r[28], [], 'SEE STATUS DISPLAY')
    report['watch'] = [dict(hour=7, sun_az=r[3]['sun_az'], cardinal=90, estimate=30, heading=r[7]['heading']),
                       dict(hour=13, sun_az=r[22]['sun_az'], cardinal=270, estimate=200, heading=r[25]['heading'])]
    print(f"watch: 7 h az {r[3]['sun_az']} E est 30 -> {w7}; 13 h az {r[22]['sun_az']} W est 200 -> {w13};"
          ' no time; REST clears it; USE COMPASS/WATCH/ALTIMETER exclusion: OK')

    # 2. The shadow stick, both answers, then light and sky refusals.
    r = session(['USE SHADOW\\r', 'LOOK N\\r', 'E', '2\\r', 'LOOK N\\r', 'USE SHADOW\\r', 'LOOK E\\r', 'W',
                 '0\\r', 'USE COMPASS\\r', 'USE SHADOW\\r', 'poke:4B4C:01', 'USE SHADOW\\r', 'poke:4B4C:00',
                 'poke:0D5D:00', 'USE COMPASS\\r', 'USE WATCH\\r', 'USE MAP\\r', 'poke:0D5D:01'])
    for x in r:
        print(f"  {x['cmd']:18} {','.join(x['msgs']):12} cw={x['compass']}{x['watch']} s={x['shadow']} "
              f"hd={x['heading']:3} h={x['hour']:.3f} el={x['elapsed']:.3f} | {x['text'][:60]}")
    check(r[0], ['m10'])
    assert r[0]['shadow'] == 1 and r[0]['elapsed'] == 0.0
    check(r[1], ['m29'])
    check(r[2], ['m48'])
    def bound(minutes, hour):              # |error| for RND in [0, 1)
        return 481 * (abs(12 - (hour + minutes * 0.00833)) * 0.33 + 1) / minutes / 2 + 1
    e1 = (r[3]['heading'] + 180) % 360 - 180
    assert abs(e1) <= bound(120, 7.0) and abs(r[3]['elapsed'] - 2) < 1e-6 and r[3]['shadow'] == 0, \
        (r[3]['heading'], r[3]['elapsed'])
    check(r[4], ['m42'])                    # one observation per USE SHADOW
    e2 = (r[8]['heading'] - 270 + 180) % 360 - 180       # 0 hours -> 10 minutes; W -> +180
    assert abs(e2) <= bound(10, 9.0) and abs(r[8]['elapsed'] - (2 + 10 / 60)) < 1e-6, \
        (r[8]['heading'], r[8]['elapsed'])
    check(r[9], ['m10'])
    check(r[10], ['m10'])
    assert (r[10]['compass'], r[10]['shadow']) == (0, 1)       # USE SHADOW drops the compass
    check(r[11], ['m53'])                   # cloudy: no shadow
    check(r[12], ['m10'])                   # the compass needs no light
    check(r[13], ['m53'])
    assert (r[13]['compass'], r[13]['watch']) == (0, 0)        # cleared before the light refusal
    check(r[14], ['m53'])
    report['shadow'] = [dict(answer='E', minutes=120, hour=7, error=e1, heading=r[3]['heading']),
                        dict(answer='W', minutes=10, hour=9, error=e2, heading=r[8]['heading'])]
    print(f'shadow: E 2 h at 7 h -> error {e1}, 120 min; W 0 h -> 10 min, error {e2} + 180;'
          ' cloudy/dark refusals (msg 53), compass needs no light: OK')

    # 3. Sun and stars: night, range, clear night, latitude sign, shelter.
    r = session(['poke:00E1:2B', 'LOOK SUN\\r', 'poke:00E1:2C', 'LOOK SUN\\r', 'poke:00E0:01', 'LOOK SUN\\r',
                 'poke:00E0:00', 'poke:00E1:80', 'LOOK STARS\\r',
                 'poke:4B49:FF', 'poke:4B4C:01', 'LOOK STARS\\r', 'poke:4B49:00', 'poke:4B4C:00', 'LOOK STARS\\r',
                 'poke:4B49:FF', 'poke:00BC:12', 'poke:00BD:34', 'poke:00BE:56', 'poke:00BF:78', 'LOOK STARS\\r',
                 'poke:60A8:EF', 'poke:00BC:9A', 'poke:00BD:BC', 'poke:00BE:DE', 'poke:00BF:F0', 'LOOK STARS\\r',
                 'poke:00BC:FF', 'poke:00BD:FF', 'poke:00BE:FF', 'poke:00BF:FF', 'LOOK STARS\\r',
                 'poke:0D5E:01', 'LOOK N\\r', 'LOOK STARS\\r', 'LOOK COMPASS\\r', 'poke:0D5E:00'])
    for x in r:
        print(f"  {x['cmd']:18} {','.join(x['msgs']):12} hd={x['heading']:3} sun={x['sun_az']} "
              f"lat={x['lat']} | {x['text'][:60]}")
    check(r[0], ['m41'])
    check(r[1], [])
    assert r[1]['heading'] == r[1]['sun_az']
    check(r[2], ['m41'])
    check(r[3], ['m52'])                    # day
    check(r[4], ['m52'])                    # cloudy night
    check(r[5], ['m52'])                    # dawn/dusk, clear
    s1 = stars_heading(bytes.fromhex('12345678'), 38)
    s2 = stars_heading(bytes.fromhex('9ABCDEF0'), -17)
    s3 = stars_heading(bytes.fromhex('FFFFFFFF'), -17)
    assert (r[6]['heading'], r[7]['heading'], r[8]['heading']) == (s1, s2, s3), \
        ((r[6]['heading'], r[7]['heading'], r[8]['heading']), (s1, s2, s3))
    check(r[9], ['s23'])                    # INSIDE SHELTER (short message offset $17)
    check(r[10], ['s23'])
    check(r[11], ['m0'])                    # 256; T$0F/S$0F has no shelter test
    report['stars'] = dict(sierra=s1, south=[s2, s3])
    print(f'sun hidden: $E1 43/44 and $E0; stars: clear night only (msg 52), north {s1},'
          f' south (lat -17) {s2} and {s3}; INSIDE SHELTER for N and STARS, not COMPASS: OK')
    (OUT / 'orientation.json').write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    main()
