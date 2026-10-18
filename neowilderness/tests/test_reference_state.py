#!/usr/bin/env python3
"""Simulation state of the ProDOS/128 KB build against the frozen HGR build.

The same ordinary-play script (tests/play_scenario.py) runs on
build/reference-hgr/WILDERNESS.dsk (II+, DOS 3.3, its own wild.lbl) and on
dist/NEOWILDERNESSXL.po (enhanced //e). After every step, every named variable
of the resident game state (segments GDATA and BSS) and of the game zero page
must hold the same bytes in both builds, located through each label file.
The approved progressive REST recovery is checked against an independent
clock/debt/health model; only its documented consequences may differ.
"""
import re
import sys
from pathlib import Path
from common import HERE, L, DISK, REFERENCE, REFERENCE_DISK, a2test, reference_labels, fp
from play_scenario import REFERENCE_SCRIPT, play

# Compare complete native steps: the first six take 58 minutes; after REST,
# the next three take 9 + 13 + 13 = 35. WALK 30 MIN formerly spent 35 in the
# reference, while XL now correctly stops after 22. Oversized budgets and
# explicit continuation are covered separately by test_travel_resume.py.
SCRIPT = [(('WALK 58 MIN\r' if keys == 'WALK 1 H\r' else
            'WALK 35 MIN\r' if keys == 'WALK 30 MIN\r' else keys), target, leave)
          for keys, target, leave in REFERENCE_SCRIPT]
SCRIPT.insert(-1, ('SLEEP 8 H\r', 'idle', None))

# Address-valued data, not simulation state: tables of code/text addresses
# (relocated by the new memory map, checked constant below), the game's
# pointer scratch and linker symbols.
ADDRESS_TABLES = {'verb_lo', 'verb_hi', 'cdef_lo', 'cdef_hi', 'ctol_lo', 'ctol_hi'}
# The verb list grows with the port's commands (lot 9: SAVE, RESTORE): a
# constant table too, checked constant below, not simulation state.
ADDRESS_TABLES |= {'verbs'}
POINTERS = {'gp1', 'gp2'}
# Module-cache bookkeeping, not simulation state: lot 4 returns from TOPO
# by copying back a snapshot of the view instead of redrawing it, so the
# window holds another module and fewer module copies are counted.
LOADING = {'overlay_reads', 'overlay_current', 'overlay_wanted'}
# Rebased on 15 October 2026 (docs/LOOK_UPDOWN.md 4): an animal of the cell
# is no longer the scene's single sprite but drawn after the view (PROJECT
# module_animal). With one there, the scene bookkeeping of the last picture
# (the main slot is the site or the nearest billboard; the cache is dropped;
# turns redraw) and the floating point scratch of its projection differ by
# design; they are compared whenever no animal is on the player's cell.
SCENE = {'scene_drawn', 'scene_cache_valid', 'scene_cache_pos', 'scene_cache_drawn',
         'scene_cache_asset', 't1', 't2', 't3', 't4', 't5'}


def animal_here(snap):
    return (snap['animal_kind'][0] and snap['animal_x'][0] == snap['px'][1]
            and snap['animal_y'][0] == snap['py'][1])


def segments(path):
    text = Path(path).read_text()
    return {name: (int(start, 16), int(end, 16) + 1) for name, start, end in
            re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]{6}', text, re.M)}


def fields(labels, segs):
    """{name: (address, size)} for the labels of the state segments."""
    ranges = [segs[name] for name in ('GDATA', 'BSS', 'GZP') if name in segs]
    found = sorted((address, name) for name, address in labels.items()
                   if any(lo <= address < hi for lo, hi in ranges))
    result = {}
    for k, (address, name) in enumerate(found):
        end = next(hi for lo, hi in ranges if lo <= address < hi)
        following = [a for a, _ in found[k + 1:] if a > address]
        if following and following[0] < end:
            end = following[0]
        result[name] = (address, end - address)
    return result


def common_fields():
    new = fields(L, segments(HERE / 'build/wild.map'))
    old = fields(reference_labels(), segments(REFERENCE / 'wild.map'))
    names = sorted(n for n in set(new) & set(old) - POINTERS - LOADING if not n.startswith('__'))
    sizes = {name: min(new[name][1], old[name][1]) for name in names}
    # Aliases share an address: keep one name per address in each build.
    keep, seen_new, seen_old = [], set(), set()
    for name in names:
        if new[name][0] in seen_new or old[name][0] in seen_old:
            continue
        seen_new.add(new[name][0])
        seen_old.add(old[name][0])
        keep.append(name)
    return keep, new, old, sizes


def snapshots(disk, labels, plan):
    """Run the script; after each step dump every field of `plan`."""
    spans = sorted({(address, size) for address, size in plan.values()})
    out = []
    with a2test.Session(disk, timeout=600) as s:
        def dump(step):
            memory = {}
            for address, size in spans:
                memory[address] = s.step(f'peek:{address:04X}:{size}').data
            out.append({name: memory[address] for name, (address, size) in plan.items()})
        play(s, labels, SCRIPT, dump)
    return out


def progressive_rest(step, previous, current):
    """Independent interval accounting, including unrefreshed health minutes."""
    from gendata import FLOATS
    number = lambda snap, name: fp(snap[name][:5])
    pending = lambda snap: int.from_bytes(snap['health_minutes'], 'little') / 60
    rest = step[0].startswith(('REST ', 'SLEEP '))
    dt = number(current, 's_elap') - number(previous, 's_elap')
    p0, p1 = pending(previous), pending(current)
    refreshed = dt + p0 - p1 > 1e-7
    debt = number(previous, 's_defr')
    if rest:
        # Three hours of credit per hour actually resting; health refreshes
        # add clock debt and clamp at zero. The final pending interval has
        # received its credit but has not yet received its clock debt.
        expected = max(0, debt + p0 - 2 * (dt - p1)) - 3 * p1
        used = int.from_bytes(current['used'], 'little')
        assert abs(used / 60 - dt) < 1e-6, (step, used, dt)
        requested = int(step[0].split()[1]) * 60
        assert 0 < used <= requested, (step, used, requested)
        stamp = number(previous, 's_elap') + int(.017 * used)
        assert abs(fp(current['s_last'][10:15]) - stamp) < 1e-6, (step, stamp)
        assert abs(number(current, 's_rest') - .5) < 1e-7
        interrupted = used < requested or bool(current['fauna_alert'][0])
        assert int.from_bytes(current['msgnum'], 'little') == (used if interrupted else requested // 60)
        assert int.from_bytes(current['minutes'], 'little') == (requested if interrupted else 0)
    else:
        expected = max(0, debt + dt + p0 - p1) if refreshed else debt
        assert current['s_last'] == previous['s_last'], (step, 'rest timestamp changed')
    assert abs(number(current, 's_defr') - expected) < 1e-6, (step, 'rest debt', expected, number(current, 's_defr'))
    if refreshed:
        last_rest_debt = max(0, number(current, 's_defr') + (3 * p1 if rest else 0))
        health = FLOATS['f_hmax'] * number(current, 's_injury_factor') * number(current, 's_therm_factor')
        for deficit, tolerance in ((number(current, 's_defw'), 190.5),
                                   (number(current, 's_deff'), 480), (last_rest_debt, 68)):
            health *= int(max(0, 1 - (max(0, deficit) / tolerance) ** 2) * 100) / 100
        assert abs(number(current, 's_health') - health) < 1e-6, (step, 'health', health, number(current, 's_health'))
    else:
        assert current['s_health'] == previous['s_health'], (step, 'health changed without refresh')


def main():
    names, new, old, sizes = common_fields()
    reference = snapshots(REFERENCE_DISK, reference_labels(),
                          {n: (old[n][0], sizes[n]) for n in names})
    current = snapshots(DISK, L, {n: (new[n][0], sizes[n]) for n in names})
    failures = 0
    for run in (reference, current):
        for name in ADDRESS_TABLES & set(names):
            assert all(snap[name] == run[0][name] for snap in run), (name, 'address table changed')
    names = [n for n in names if n not in ADDRESS_TABLES]
    total = sum(sizes[n] for n in names)
    rest_started = False
    for index, (step, before, after) in enumerate(zip(SCRIPT, reference, current)):
        if step[0] in ('WALK 58 MIN\r', 'WALK 35 MIN\r'):
            duration, steps = (58, 6) if step[0] == 'WALK 58 MIN\r' else (35, 3)
            for run in (reference, current):
                dt = fp(run[index]['s_elap'][:5]) - fp(run[index - 1]['s_elap'][:5])
                count = (int.from_bytes(run[index]['journey_steps'], 'little') -
                         int.from_bytes(run[index - 1]['journey_steps'], 'little'))
                assert abs(dt * 60 - duration) < 1e-5 and count == steps, (step, dt, count)
        rest_started |= step[0].startswith(('REST ', 'SLEEP '))
        approved = set()
        if rest_started:
            progressive_rest(step, current[index - 1], after)
            # Command scratch: last loop index; remaining/requested duration;
            # displayed number; and elapsed rest minutes (previously travel only).
            approved = {'g0', 'minutes', 'msgnum', 'used', 's_defr', 's_health', 's_last'}
            assert before['s_last'][:10] == after['s_last'][:10], 'meal/drink timestamps differ'
        differ = [n for n in names if before[n] != after[n] and n not in approved
                  and not (n in SCENE and animal_here(before) and animal_here(after))]
        label = step[0].replace('\r', '').replace('\\', '')
        if differ:
            failures += 1
            print(f'  {label:18} DIFFER: ' + ', '.join(
                f'{n} {before[n].hex()} != {after[n].hex()}' for n in differ[:6]))
        else:
            print(f'  {label:18} ' + ('parity + progressive rest model' if rest_started else 'identical'))
    print(f'  {len(names)} state variables, {total} bytes, compared after each of '
          f'{len(SCRIPT)} steps (reference II+/DOS 3.3 vs //e/ProDOS)')
    # The script must cross midnight (start 7:00) and update health.
    elapsed = fp(current[-1]['s_elap'][:5])
    assert elapsed > 17, ('no day change', elapsed)
    assert current[-1]['s_health'] != current[0]['s_health'], 'no health update'
    print(f'  {elapsed:.2f} elapsed hours (day change at 17 h), health updated')
    if failures:
        print(f'{failures} steps differ')
        sys.exit(1)
    print('Reference state: OK')


if __name__ == '__main__':
    main()
