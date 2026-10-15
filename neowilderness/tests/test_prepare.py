#!/usr/bin/env python3
"""Journey preparation and difficulty levels (fidelity lot 1: P1, P2).

NEOWILD.PRE (src/prepare.s) runs after the region pack for every journey
other than a scenario at level 4. For each case of tools/prepare_ref.CASES
(Sierra Nevada, plane crash), the test types P, the region, the level and
the answers at the port's menu with the RND imposed (pr_fixed), stops at
game_start and compares the start state with tools/prepare_ref.py:
date, hour, temperature wave phase, crash injury (condition active at
90 %), wreck lot (it_place), uses of the consumables and FUEL, body weight,
metabolism and eating rate, Hmax and health, thermal surface Q, th_a and the
overweight factor (SIM image), wildlife (NATURE) and storm frequencies (the
ADVENTURE image), first weather front, its duration, wind, and the words of
the introduction and the fitness verdict on the screen.

Then two journeys without questions: Chile at level 10 (a scenario: drawn
date, injury, wreck lot; the frozen body untouched) and a free journey at
level 4; and the default path (RETURN, RETURN) never reads NEOWILD.PRE.

--original: the same cases on the original (tools/re_prepare_probe.py,
build/SIERRA.woz + build/JOURNEY.dsk): every float of the port must equal
the original's bytes (same ROM operations), every integer its value.
"""
import json
import math
import sys
from common import HERE, L, DISK, a2test, text_screen, menu_keys

sys.path.insert(0, str(HERE / 'tools'))
import prepare_ref as R  # noqa: E402

FLOATS = ('s_date', 's_hour', 's_temp_phase', 'f_rest_rate', 'f_eat_rate', 'f_hmax', 's_health',
          'weather_start', 'pr_freq', 'pr_storm', 'pr_wild')
GAME_FLOATS = FLOATS[:-3]


def state(s):
    out = {name: s.step(L.peek(name, 5)).data for name in GAME_FLOATS}
    for name, n in (('it_place', 76), ('it_pack_lo', 76), ('it_pack_hi', 76), ('it_oz_lo', 76),
                    ('it_oz_hi', 76), ('it_vol_lo', 76), ('it_vol_hi', 76), ('it_gnd_lo', 76),
                    ('it_gnd_hi', 76), ('injury_active', 15), ('injury_percent', 15),
                    ('body_weight', 2), ('weather_duration', 2), ('wind', 1), ('nature_frequency', 1)):
        out[name] = s.step(L.peek(name, n)).data
    out['header'] = s.step('peek:7000:64').data
    return out


def word(d, i=0):
    return d[i] | d[i + 1] << 8


def run_port(case, region='2', level=None, prepared=True, free=False):
    level = case['level'] if level is None else level
    with a2test.Session(DISK, timeout=900, menu=False) as s:
        s.step(L.until('menu_key', 40000))
        if prepared:
            s.step('key:P')
            s.step('key:' + {'2': '1', '6': '6'}[region])
        elif free:
            s.step('key:7')
            s.step('key:' + {'2': '1', '6': '6'}[region])
        else:
            s.step('key:' + {'2': '1', '6': '6'}[region])
        s.step(f'key:{level}\\r')
        s.step(L.until('prepare', 20000))
        for i, b in enumerate(R.encode(case['rnd'])):
            s.step(L.poke('pr_fixed', b, i))
        screens = []
        if prepared:
            answers = R.port_answers(case)
            for k, answer in enumerate(answers):
                s.step(L.until('ld_menu_key', 4000))
                s.step(f'key:{answer}\\r')
                if not case['research'] and k == len(answers) - 3:
                    s.step('wait:30')
                    screens.append(text_screen(s.step('peek:0400:1024').data))
            s.step('wait:60')
            screens.append(text_screen(s.step('peek:0400:1024').data))
            s.step('press:\\r')                 # PRESS RETURN TO BEGIN. (queued: the start is quick)
        # PRE's own variables, before the grid of the menu covers $2000-$3FFF.
        s.step(L.until('ld_no_prepare', 20000))
        own = {name: s.step(L.peek(name, n)).data for name, n in
               (('pr_freq', 5), ('pr_storm', 5), ('pr_wild', 5), ('pr_inj', 1), ('pr_verdict', 1))}
        s.step(L.until('game_start', 20000))
        if not prepared:
            screens.append(text_screen(s.step('peek:0400:1024').data))
        got = state(s)
        got.update(own)
        # Patched module image: SIM (th_surface, th_a, composition, and
        # wf_storm since ADVENTURE is LZ-packed), copied into its window
        # from the idle loop.
        s.step(L.until('idle', 20000))
        images = {}
        for index, names in ((3, ('th_surface', 'th_a', 'th_native_composition', 'wf_storm')),):
            entry = L['idle']
            code = (0xA9, index, 0x20, L['overlay_load'] & 255, L['overlay_load'] >> 8,
                    0x4C, entry & 255, entry >> 8)
            for i, b in enumerate(code):
                s.step(f'poke:{entry + i:04X}:{b:02X}')
            s.step(L.poke('overlay_current', 0))
            s.step(L.poke('sim_loaded', 0))
            s.step(f'until:{entry + 5:04X}:200')
            for name in names:
                images[name] = s.step(L.peek(name, 5)).data
            s.step(L.until('idle', 100))
        got['images'] = images
        got['screens'] = screens
    return got


def close(a, b, tol):
    return abs(a - b) <= tol * max(1.0, abs(b))


def check(case, got, original=None):
    e = R.expected(case)
    f = {k: R.decode(v) for k, v in got.items() if k in FLOATS}
    bad = []
    for name, key, tol in (('s_date', 'date', 1e-6), ('s_hour', 'hour', 1e-6),
                           ('s_temp_phase', 'phase', 1e-6), ('weather_start', 'front', 2e-5),
                           ('pr_freq', 'precipitation', 2e-5), ('pr_storm', 'storm', 1e-7)):
        if not close(f[name], e[key], tol):
            bad.append((name, f[name], e[key]))
    if not close(f['f_rest_rate'], e['rate'], 1e-7) or not close(f['f_hmax'], e['hmax'], 1e-6) \
            or not close(f['s_health'], e['health'], 1e-6) or not close(f['f_eat_rate'], e['eat'], 1e-6):
        bad.append(('body', f['f_rest_rate'], f['f_hmax'], f['s_health'], f['f_eat_rate'], e['rate'],
                    e['hmax'], e['health'], e['eat']))
    if word(got['body_weight']) != e['weight']:
        bad.append(('weight', word(got['body_weight']), e['weight']))
    if got['pr_inj'][0] != e['injury']:
        bad.append(('injury', got['pr_inj'][0], e['injury']))
    active = [i for i in range(15) if got['injury_active'][i]]
    if active != ([e['injury'] - 1] if e['injury'] else []) or \
            any(got['injury_percent'][i] != 90 for i in active):
        bad.append(('conditions', active, list(got['injury_percent'][:3])))
    if list(got['it_place'][1:]) != e['b1'][1:]:
        bad.append(('wreck', [(i, a, b) for i, (a, b) in enumerate(zip(got['it_place'], e['b1']))
                              if i and a != b]))
    uses, edges = e['uses']
    port_uses = [got['it_pack_lo'][i] | got['it_pack_hi'][i] << 8 for i in range(38, 67)]
    port_uses += [got['it_oz_lo'][40], got['it_vol_lo'][40]]
    diff = [(i, a, b) for i, (a, b) in enumerate(zip(port_uses, uses)) if a != b and i not in edges]
    if diff:
        bad.append(('uses', diff))
    for i in range(22, 38):
        if got['it_pack_lo'][i] or got['it_gnd_lo'][i] != got['it_oz_lo'][i]:
            bad.append(('food', i))
    if word(got['weather_duration']) != e['duration'] or got['wind'][0] != e['wind']:
        bad.append(('front', word(got['weather_duration']), e['duration'], got['wind'][0], e['wind']))
    if got['nature_frequency'][0] != int(e['wildlife'] + .5):
        bad.append(('nature', got['nature_frequency'][0], e['wildlife']))
    im = {k: R.decode(v) for k, v in got['images'].items()}
    if round(im['th_surface']) != e['q'] or not close(im['th_a'], e['q'] * 1e-7, 1e-7) or \
            not close(im['th_native_composition'], e['composition'], 1e-7) or \
            not close(im['wf_storm'], e['storm'], 1e-7):
        bad.append(('images', im, e['q'], e['composition'], e['storm']))
    if e['verdict'] is not None:
        text = ' '.join(' '.join(r.split()) for r in got['screens'][0])
        if ' '.join(R.VERDICT[e['verdict']].split()) not in text or got['pr_verdict'][0] != e['verdict']:
            bad.append(('verdict', got['pr_verdict'][0], e['verdict'], got['screens'][0]))
    summary = ' '.join(' '.join(r.split()) for r in got['screens'][-1])
    terrain, difficulty = e['words']
    if f'THE TERRAIN IS {terrain}.' not in summary or f'LEVEL OF DIFFICULTY: {difficulty}.' not in summary:
        bad.append(('words', summary))
    if not case['research'] and f'YOU HAVE {R.INJURY[e["injury"]]} IN THE CRASH.' not in summary:
        bad.append(('injury words', summary))
    if original is not None:
        o = R.from_original(bytes.fromhex(original['page3']), bytes.fromhex(original['state']))
        for name, key in (('s_date', 'date'), ('s_hour', 'hour'), ('s_temp_phase', 'phase'),
                          ('f_rest_rate', 'rate'), ('f_hmax', 'hmax'), ('s_health', 'health'),
                          ('weather_start', 'front'), ('pr_freq', 'precipitation')):
            if got[name].hex() != o['raw'][key]:
                bad.append(('original ' + name, got[name].hex(), o['raw'][key]))
        if list(got['it_place'][1:]) != o['b1'][1:]:
            bad.append(('original wreck', [(i, a, b) for i, (a, b) in
                                          enumerate(zip(got['it_place'], o['b1'])) if i and a != b]))
        ou = o['w8'][38:67] + [o['w5'][40], o['w6'][40]]
        if port_uses != ou:
            bad.append(('original uses', port_uses, ou))
        for key, mine in (('injury', got['pr_inj'][0]), ('duration', word(got['weather_duration'])),
                          ('wind', got['wind'][0]), ('weight', word(got['body_weight'])),
                          ('q', round(im['th_surface']))):
            if mine != o[key]:
                bad.append(('original ' + key, mine, o[key]))
        conds = [i for i in range(15) if o['conditions'][i] < 95]
        if conds != active:
            bad.append(('original conditions', active, conds))
    assert not bad, (case['name'], bad)
    return e


def unprepared():
    """Chile, level 10 (scenario) and a free journey at level 4: draws only."""
    frozen = (HERE / 'build/wildgame.bin').read_bytes()
    base = 0x4000
    hmax0 = frozen[L['s_health'] - base:L['s_health'] - base + 5]
    case = dict(R.CASES[-1], name='chile10', rnd=0.9, research=False, date=None,
                **R.FROZEN_BODY)
    got = run_port(case, region='6', level=10, prepared=False)
    lat = got['header'][12] - 256 * (got['header'][12] > 127)
    e = R.expected(case, north=lat >= 0)
    assert got['header'][22] == 10 and got['header'][33] == 0, got['header'].hex()
    assert close(R.decode(got['s_date']), e['date'], 1e-6), (R.decode(got['s_date']), e['date'], lat)
    assert got['pr_inj'][0] == e['injury'] == 3 and got['injury_active'][2] == 1
    assert list(got['it_place'][1:]) == e['b1'][1:]
    assert got['s_health'] == hmax0 and word(got['body_weight']) == 165, 'frozen body'
    summary = ' '.join(' '.join(r.split()) for r in got['screens'][-1])
    assert 'THE TERRAIN IS PUNISHING.' in summary and 'BACK-BREAKING' in summary, summary
    print(f'  Chile level 10 (scenario, no questions, latitude {lat}): date {e["date"]:.4f}, '
          f'broken leg, wreck lot, frozen body kept: OK')
    case = dict(case, name='free4', rnd=0.3, level=4)
    got = run_port(case, region='2', level=4, prepared=False, free=True)
    e = R.expected(case)
    assert got['header'][33] == 1 and got['pr_inj'][0] == e['injury'] == 0
    assert close(R.decode(got['s_date']), e['date'], 1e-6) and list(got['it_place'][1:]) == e['b1'][1:]
    print(f'  free journey level 4: drawn date {e["date"]:.4f}, wreck lot: OK')


def default_path():
    """RETURN, RETURN: the frozen first journey; NEOWILD.PRE is never read."""
    steps = menu_keys() + [L.until('game_start', 20000), L.peek('mli_calls', 2), L.peek('s_date', 5),
                           L.peek('it_place', 76)]
    r = a2test.run(DISK, steps, menu=False, timeout=900)
    frozen = (HERE / 'build/wildgame.bin').read_bytes()
    for name, n in (('s_date', 5), ('it_place', 76)):
        assert r.mem(L[name], n) == frozen[L[name] - 0x4000:L[name] - 0x4000 + n], name
    print(f'  default path (Sierra, level 4): frozen state, {word(r.mem(L["mli_calls"], 2))} MLI calls, '
          'no NEOWILD.PRE: OK')
    return word(r.mem(L['mli_calls'], 2))


def main():
    original = '--original' in sys.argv
    probes = {}
    if original:
        import re_prepare_probe as P
        for case in R.CASES:
            probes[case['name']] = P.run_case(case)
    calls = default_path()
    for case in R.CASES:
        got = run_port(case)
        e = check(case, got, probes.get(case['name']))
        print(f"  {case['name']:9} level {case['level']:2} rnd {case['rnd']}: injury {e['injury']}, "
              f"Hmax {e['hmax']:.4f}, date {e['date']:.4f} {e['hour']:.2f} h, front {e['front']:.1f}/"
              f"{e['duration']}, wind {e['wind']}, words {'/'.join(e['words'])}"
              + (': OK (= original bytes)' if original else ': OK'))
    unprepared()
    print('Journey preparation and levels: OK' + (' (against the original)' if original else ''))


if __name__ == '__main__':
    main()
