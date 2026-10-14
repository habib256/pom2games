#!/usr/bin/env python3
"""A crash -> rangers survival trip played at the keyboard, with zero disk access.

The fixture is the flat ground of test_input.flat() with the Sierra regional
climate (index 31, difficulty 4, base altitude 2 400 ft): the crash at
(10, 40) facing east, a river two cells wide at x = 12-13, a cabin at
(16, 40) and the ranger outpost at (24, 40). Typed command by command:

  NATURE 100, EAT, DRINK, WALK to the shore (WATER AHEAD), FILL CANTEEN,
  SWIM across, WALK to the cabin, REST outside until a rattlesnake comes,
  IGNORE RATTLER (bitten), SUCK VENOM, ENTER SHELTER, EAT, DRINK, SLEEP
  until daylight of the next day (the day changes; animals come and go),
  EXIT SHELTER, WALK to the outpost until the ending.

Every animal comes from the native rolls of the journey; NATURE 100 keeps
their presence and ageing active (the native encounter rolls themselves
use the map difficulty, not NATURE). One fixture intervention remains:
fauna_rng is set before IGNORE RATTLER so that the reaction bites
(test_animal_reactions.seed_for), giving the care action an injury.

Checks over the whole trip:
* zero MLI call: mli_calls/mli_reads/mli_bytes unchanged after the preload
  and an a2shot watch on the ProDOS entry $BF00 never fires;
* every module load is a RAM transfer (overlay_reads = xfer_count, per
  command and in total, plus at most one direct copy of the star catalogue
  head per command at night, lot 7);
* memory guards: the stack pointer and the I flag are the same at every
  command (do_command), the deepest stack stays above the copy loop at
  $0120-$015B (a2shot hwstack, no wrap), the auxiliary $0200-$03FF (ProDOS
  /RAM driver) and the memory soft switches are unchanged at the end;
* milestones: canteen filled at the shore, far bank reached by SWIM, cabin
  entered and left, animals met (journey_encounters), bite treated, health
  changed, clock past midnight with a new date, and the ending
  "RANGER OUTPOST REACHED" on screen before any key leaves the game; that
  key then reads NEOWILD.END and NEOWILD.HOF (lot 7: score and hall of
  fame, the only disk access of a journey) and reaches hof_key_wait.

The same keystrokes then run on the same ground made native (header byte
37, 224 x 168 fine geography resident, lot 5; the river is a lake, crossed
by SWIM). Native rules differ and are not forced: the map's cabin is not a
shelter there (native shelters are discovered), WALK stops in the first
water half-cell, the canteen question is cancelled by ESC and reactions use
their native rolls. That run checks the zero MLI call, the RAM transfers,
the stack, the new day, the ending at the exact outpost cell and reports
fine queries and tiles decoded per command. `-v` adds the message lines.
"""
import re
import sys
import tempfile
import time

from common import L, a2test, disk_with, fp, state, text_screen
from test_input import flat
from test_animal_reactions import seed_for
import geo_atlas
import mkmap

LIMIT = 40000
IDLE = L.until('idle', LIMIT)
READY = f'until:{L["idle"]:04X},{L["wait_key"]:04X}:{LIMIT}'
SWITCHES = 'peek:C011:15'   # LCBNK2 LCRAM RAMRD RAMWRT CXROM ALTZP C3ROM 80STORE VBL TEXT MIXED PAGE2 HIRES ALTCHAR 80COL
COUNTERS = (('mli_calls', 2), ('mli_reads', 2), ('mli_bytes', 3), ('xfer_count', 2),
            ('xfer_bytes', 3), ('overlay_reads', 2), ('xfer_texts', 2))
NATIVE = 'geo_decodes' in L     # resident fine geography (src/geoaux.s)
if NATIVE:
    COUNTERS += (('geo_queries', 3), ('geo_decodes', 2))
CRASH, RIVER, CABIN, GOAL, ROW = 10, (12, 13), 16, 24, 40
BITE = seed_for((0, 16))        # IGNORE RATTLER: the first reaction roll bites
RATTLER = 8
VERBOSE = '-v' in sys.argv


def legacy():
    m = flat()
    m[2:8] = bytes((0, CRASH, 0, ROW, 140, 0))
    m[8:10] = bytes((GOAL, ROW))
    m[10] = 24                                  # base altitude 2 400 ft
    m[16:21] = bytes((1, CABIN, ROW, 140, 0))
    m[22], m[23] = 4, 31                        # difficulty, Sierra climate
    m[26] = 1                                   # forest extension, no woods
    for y in range(2, 82):
        for x in RIVER:
            m[64 + y * 112 + x] |= 128
    return bytes(m) + bytes(mkmap.FOREST_BYTES)


def native():
    """The same ground as native fine geography: every coarse cell is 2 x 2
    fine cells; the resident 112 x 84 grid is rebuilt from them."""
    m = bytearray(legacy())
    cells = bytearray([10]) * (224 * 168)
    for y in range(4, 164):
        for x in range(2 * RIVER[0], 2 * RIVER[-1] + 2):
            cells[y * 224 + x] = 0x80 | 0x40 | 10   # lake: crossed by SWIM
    woods = bytes(28 * 168)
    m[64:mkmap.MAP_BYTES] = geo_atlas.Fine('journey', cells, woods, None, None, True).coarse()
    m[37] = 1
    return bytes(m) + bytes(cells) + woods


def report(row):
    command, delta, position, hour, animal, message = row
    geo = (f', {delta["geo_queries"]:4} fine queries, {delta["geo_decodes"]} decodes'
           if delta.get('geo_queries') else '')
    print(f'    {command:16} at ({position[0] / 256:5.2f},{position[1] / 256:5.2f}) {hour:5.2f} h, '
          f'animal {animal}: MLI {delta["mli_calls"]}, module loads {delta["overlay_reads"]:2}, '
          f'RAM transfers {delta["xfer_count"]:2} ({delta["xfer_bytes"]:5} bytes){geo}'
          + (f'  [{" / ".join(message)}]' if VERBOSE else ''), flush=True)


def waiting(reply):
    return reply.out.rstrip().endswith(f'PC={L["wait_key"]:04X}')


def ended(screen):
    return any('RANGER OUTPOST REACHED' in r or 'LOST IN THE WILDERNESS' in r for r in screen)


def play(disk, title, strict=True):
    rows, notes = [], dict(midnight=False)
    print(f'  {title}:', flush=True)
    with a2test.Session(disk, timeout=900) as s:
        def counters():
            return {n: int.from_bytes(s.step(L.peek(n, k)).data, 'little') for n, k in COUNTERS}

        def peek(name, size=1):
            return s.step(L.peek(name, size)).data

        def hour():
            return fp(peek('s_hour', 5))

        def run(command):
            """Type one command; its message lines, or None at the ending."""
            before, start = counters(), hour()
            s.step(f'key:{command}')
            s.step('press:\\r')
            s.step('wait:1')
            reply = s.step(READY)
            screen = text_screen(s.step('peek:0400:1024').data)
            while waiting(reply) and not ended(screen):
                s.step('press:\\e')           # a question (HOW MANY OZ?): cancel it
                s.step('wait:1')
                reply = s.step(READY)
                screen = text_screen(s.step('peek:0400:1024').data) + ['', '', '', '(ESC)']
            after = counters()
            if hour() < start:
                notes['midnight'] = True        # the clock wrapped: a new day
            message = [r[40:79].strip() for r in screen[20:23] if r[40:79].strip()]
            rows.append((command, {k: after[k] - before[k] for k in after}, state(peek('px', 6)),
                         hour(), peek('animal_kind')[0], message))
            report(rows[-1])
            if waiting(reply):
                notes['ending'] = screen        # the ending waits for a key
                return None
            return ' '.join(message)

        def machine():
            switches = tuple(b >> 7 for i, b in enumerate(s.step(SWITCHES).data) if i != 8)
            s.step('poke:C003:00')              # RAMRD on: read the auxiliary bank
            driver = s.step('peek:0200:512').data
            s.step('poke:C002:00')
            return switches, driver

        s.step(IDLE)
        boot = counters()
        start_health, start_date = fp(peek('s_health', 5)), peek('s_date', 5)
        start_machine = machine()
        s.step('hwstackwatch')
        s.step('watch:BF00')
        s.step(f'watch:{L["do_command"]:04X}')
        mark = len(s.out)
        for command in ('NATURE 100', 'EAT CHEESE 4 OZ', 'DRINK WATER 4 OZ'):
            run(command)
        notes['shore'] = run('WALK 1 H')       # stops at the river
        run('FILL CANTEEN')                     # river water: 160 oz on the cell (lot 2)
        notes['canteen'] = (s.step(L.peek('it_pack_lo', 1, 22)).data[0] == 64
                            and peek('water_untreated')[0] == 1)
        for _ in range(3):
            if 'REACHED LAND' in run('SWIM 100 MIN'):
                notes['far bank'] = state(peek('px', 6))[0] >> 8
                break
        run('WALK 36 MIN')
        assert state(peek('px', 6))[:2] == (CABIN << 8, ROW << 8) or not strict
        for _ in range(4):                      # wait outside for an animal
            if peek('animal_kind')[0] == RATTLER:
                break
            run('REST 3 H')
        assert peek('animal_kind')[0] == RATTLER or not strict, 'no rattlesnake came to the cabin'
        if peek('animal_kind')[0] == RATTLER:
            s.step(L.poke('fauna_rng', BITE))
        run('IGNORE RATTLER')
        notes['bitten'] = peek('injury_active', 15)[7] == 1
        run('SUCK VENOM')
        notes['treated'] = peek('injury_treated', 15)[7] == 1
        run('ENTER SHELTER')
        notes['cabin'] = peek('shelter_inside') == b'\x01'
        run('EAT CHEESE 4 OZ')
        run('DRINK WATER 8 OZ')
        for _ in range(10):                     # sleep until the next morning
            if notes['midnight'] and hour() >= 6:
                break
            run('SLEEP 8 H')
        run('EXIT SHELTER')
        notes['cabin'] &= peek('shelter_inside') == b'\x00'
        for _ in range(4):                      # walk away to the outpost
            if run('WALK 3 H') is None:
                break
        out = s.out[mark:]
        hw = re.search(r'peak=(\d+) available=(\d+) overflow=(\d)', s.step('hwstack').out)
        lowest, wrapped = 255 - int(hw.group(1)), int(hw.group(3))
        end_machine = machine()
        watched = out.count('watch BF00')
        stacks = set(re.findall(rf'^watch {L["do_command"]:04X} .* S=([0-9A-F]{{2}})', out, re.M))
        flags = {int(p, 16) & 4 for p in
                 re.findall(rf'^watch {L["do_command"]:04X} .* P=([0-9A-F]{{2}})', out, re.M)}
        final = counters()
        notes.update(health=(start_health, fp(peek('s_health', 5))),
                     day=notes['midnight'] and peek('s_date', 5) != start_date,
                     encounters=int.from_bytes(peek('journey_encounters', 2), 'little'),
                     won=peek('won') == b'\x01')
        if notes.get('ending'):
            # Lot 7: the key leaves the ending for the score and the hall of
            # fame, the only disk reads of a journey (NEOWILD.END, NEOWILD.HOF).
            s.step('key: ')
            s.step(L.until('hof_key_wait', LIMIT))
            notes['hall reads'] = counters()['mli_reads'] - final['mli_reads']
    total = {k: final[k] - boot[k] for k in final}
    print(f'    whole trip: {len(rows)} commands, MLI {total["mli_calls"]} (watch $BF00: {watched}), '
          f'module loads {total["overlay_reads"]}, RAM transfers {total["xfer_count"]} '
          f'({total["xfer_bytes"]} bytes), fine queries {total.get("geo_queries", 0)}, '
          f'tiles decoded {total.get("geo_decodes", 0)}; S=${"/".join(sorted(stacks))} at every command, '
          f'deepest S=${lowest:02X}')
    print(f'    health {notes["health"][0]:.2f} -> {notes["health"][1]:.2f}, '
          f'{notes["encounters"]} encounters, far bank x={notes.get("far bank")}, '
          f'new day {notes["day"]}, ending {"reached" if ended(notes.get("ending") or []) else "not reached"}')
    assert watched == 0, f'{watched} ProDOS MLI entries during the trip'
    assert total['mli_calls'] == total['mli_reads'] == total['mli_bytes'] == 0, total
    # Every module load is a RAM copy; the star module also copies the head
    # of its catalogue (directory entry 24) by a direct mem_fetch, not counted
    # as a module load: at most one per command (night hours outside).
    # The text bank's fetches (two per message, docs/MEMORY.md 13) are
    # transfers too, counted apart in xfer_texts.
    assert all(d['mli_calls'] == 0 and 0 <= d['xfer_count'] - d['xfer_texts'] - d['overlay_reads'] <= 1
               for _, d, *_ in rows), [(c, d) for c, d, *_ in rows]
    assert 0 < total['overlay_reads'] <= total['xfer_count']
    assert len(stacks) == 1, ('stack pointer at do_command varies', stacks)
    assert len(flags) == 1, ('I flag at do_command varies', flags)
    assert not wrapped and lowest > 0x5B, ('stack reached the copy loop $0120-$015B', lowest)
    # Memory switches (LC, RAMRD, RAMWRT, CXROM, ALTZP, C3ROM, 80STORE); the ending is a text screen.
    assert end_machine[0][:8] == start_machine[0][:8], ('memory switches', start_machine[0], end_machine[0])
    assert end_machine[1] == start_machine[1], 'auxiliary $0200-$03FF (/RAM driver) changed'
    if not strict:
        assert notes['day'] and ended(notes.get('ending') or []) and notes['won'], notes
        assert total['geo_queries'] > 0 and total['geo_decodes'] > 0, total
        assert notes.get('hall reads', 0) > 0, 'the hall of fame must follow the ending key'
        return total
    assert notes['cabin'] and notes['canteen'] and notes.get('far bank') == RIVER[-1] + 1, notes
    assert notes['bitten'] and notes['treated'], notes
    assert notes['encounters'] >= 2 and notes['day'], notes
    assert notes['health'][0] != notes['health'][1], notes
    ending = notes.get('ending') or []
    assert any('RANGER OUTPOST REACHED' in r for r in ending) and notes['won'], ending
    assert notes.get('hall reads', 0) > 0, 'the hall of fame must follow the ending key'
    print(f'    ending key: hall of fame reached after {notes["hall reads"]} MLI READ call(s) (NEOWILD.END, NEOWILD.HOF)')
    return total


def main():
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        play(disk_with(tmp, legacy()), 'legacy 112 x 84 map')
        if NATIVE:
            play(disk_with(tmp, native()), 'native map, fine geography resident', strict=False)
    print(f'Crash -> rangers trip without disk access on {"both maps" if NATIVE else "the legacy map"}: '
          f'OK ({time.monotonic() - started:.0f} s)')


if __name__ == '__main__':
    main()
