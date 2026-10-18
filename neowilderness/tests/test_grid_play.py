#!/usr/bin/env python3
"""The grid played with the arrows and RETURN alone (docs/MENUS.md 4), on
both editions: from the start of the Sierra Nevada journey, light a fire
(MAKE, FIRE: USE MATCHES, MAKE FIRE and USE FIRE in the morning cold, the
grid's queue), explicitly prepare utensils through CAMP then boil water
(BOIL, 8 OZ: USE UTENSILS, BOIL WATER 8 OZ),
eat a pile of mushrooms found here (EAT, MUSHROOMS, 8 OZ, lot 4) and stop a
bleeding (CARE: the MEDICAL page on SEVERE CUTS, RETURN on STOP BLEEDING).
Only the keys a joystick gives are pressed: LEFT, RIGHT, UP, DOWN, RETURN.

Each action reports its keys, the commands typed for the player, its disk
reads (NEOWILD.BLK: FORAGE, MEDVIEW on both editions) and its emulated time.
"""
from common import L, DISK, DISK140, a2test, text_screen
from test_menu_bar import grid_cells, selected, bottom, RIGHT, RET, open_boil_quantities

LIMIT = 400000
IDLE = L.until('idle', LIMIT)
KEYS = {'\\<', '\\>', '\\^', '\\v', '\\r'}
MUSHROOMS = 85 - 76                     # their pile (src/forage.s fg_*)


def peek(s, name, k=0):
    return s.step(L.peek(name, 1, k)).data[0]


def decline_followup(s):
    """Keep this native-comparison scenario on its own explicit action path."""
    ready = L.until('keyboard_wait', LIMIT)
    s.step(ready)
    assert peek(s, 'dep_running') & 0x80, bottom(s)
    assert 'BOILED PORTION' in '\n'.join(bottom(s)), bottom(s)
    assert 'RET:SELECT ESC:CANCEL' in ' '.join(bottom(s)), bottom(s)
    s.step('key:\\e'); s.step('wait:1'); s.step(IDLE)


def play(disk):
    with a2test.Session(disk, timeout=1800) as s:
        s.step(L.until('idle', 40000))
        s.step(L.poke('nature_frequency', 0))
        log = []

        def key(k):
            assert k in KEYS, k
            s.step(f'key:{k}')
            s.step('wait:1')

        def to(label):
            """RIGHT until the label is selected (the grid wraps)."""
            for _ in range(40):
                if selected(s) == label:
                    return
                key(RIGHT)
                s.step(IDLE)
            raise AssertionError((label, grid_cells(s)))

        def action(name, *labels):
            """RETURN on each label; the last one runs the commands (and
            their queue) until the prompt: the commands typed, the disk
            reads, the cycles."""
            # The MEDICAL page (CARE types STATUS) is detected at the resident
            # entry scr_status: page_top lies in the SIM window, where the GRID
            # image ($A300) runs the queue at the same addresses.
            preparation = []
            for label in labels[:-1]:
                if label == 'BOIL':
                    preparation += open_boil_quantities(s)
                else:
                    to(label)
                    key(RET)
                    s.step(IDLE)
            to(labels[-1])
            reads = int.from_bytes(s.step(L.peek('mli_reads', 2)).data, 'little')
            s.step(f'press:{RET}')              # in the latch at once: do_command is on the way
            commands = preparation[:]
            out = s.step(L.until('do_command', LIMIT))
            cycles0 = out.cycles[-1]
            while True:
                commands.append(s.step(L.peek('inbuf', 24)).data.split(b'\0')[0].decode())
                out = s.step(f'until:{L["get_line"]:04X},{L["scr_status"]:04X}:{LIMIT}')
                if f'PC={L["scr_status"]:04X}' in out.out:
                    break
                out = s.step(f'until:{L["do_command"]:04X},{L["idle"]:04X},{L["keyboard_wait"]:04X}:{LIMIT}')
                if f'PC={L["keyboard_wait"]:04X}' in out.out:
                    decline_followup(s)
                    out = s.step(IDLE)
                    break
                if f'PC={L["idle"]:04X}' in out.out:
                    break
            log.append((name, commands, int.from_bytes(s.step(L.peek('mli_reads', 2)).data, 'little') - reads,
                        out.cycles[-1] - cycles0))
            return out

        key(RET)                                    # the grid
        s.step(IDLE)
        assert selected(s) == 'WALK', bottom(s)
        # A fire: MAKE, FIRE (a match first; USE FIRE in the cold).
        action('fire', 'MAKE', 'FIRE')
        assert peek(s, 'fire_on') and peek(s, 'fire_near') and peek(s, 'mq_n') == 0, (log, bottom(s))
        assert log[-1][1] == ['USE MATCHES', 'MAKE FIRE', 'USE FIRE'], log
        # Water: explicitly confirm UTENSILS and READY before BOIL, 8 OZ.
        water = peek(s, 'it_pack_lo', 22)
        action('boil', 'BOIL', '8 OZ')
        assert log[-1][1] == ['USE UTENSILS', 'BOIL WATER 8 OZ'], log
        assert peek(s, 'camp_use') & 32 and peek(s, 'it_pack_lo', 22) == water - 8, log
        # A pile of mushrooms found here (as a discovery leaves it): EAT, the
        # pile first in the list, 8 OZ.
        s.step(L.poke('fg_gl', 20, MUSHROOMS))
        s.step(L.poke('fg_b1', 0, MUSHROOMS))
        x, y = peek(s, 'px', 1), peek(s, 'py', 1)
        s.step(L.poke('fg_x', x))
        s.step(L.poke('fg_y', y))
        action('mushrooms', 'EAT', 'MUSHROOMS', '8 OZ')
        assert log[-1][1] == ['EAT MUSHROOMS 8 OZ'] and peek(s, 'fg_gl', MUSHROOMS) == 12, \
            (log, peek(s, 'fg_gl', MUSHROOMS))
        # A bleeding fixture: close the existing grid, then turn the view
        # to refresh offered actions without simulation. Native injuries
        # refresh them when simulation returns; injected state needs this
        # explicit refresh. CARE opens MEDICAL on SEVERE CUTS.
        s.step(L.poke('injury_active', 1, 0))
        for _ in range(4):
            if selected(s) is None:
                break
            key('\\^')
            s.step(IDLE)
        # Closing/reopening alone deliberately retains the existing grid.
        for turn in (RIGHT, '\\<'):
            key(turn)
            s.step(IDLE)
        key(RET)
        s.step(IDLE)
        out = action('care', 'CARE')
        assert f'PC={L["scr_status"]:04X}' in out.out, out.out
        s.step(L.until('keyboard_wait', LIMIT))
        row = text_screen(s.step('peek:0400:1024').data)[23]
        foot = ' \u2190\u2192 ' if disk == DISK else ''     # XL: the pages' footer (docs/MENUS.md 9)
        assert peek(s, 'pg_focus') == 6 and row.startswith(foot + 'STOP BLEEDING'), row
        reads = int.from_bytes(s.step(L.peek('mli_reads', 2)).data, 'little')
        s.step(f'press:{RET}')
        s.step(L.until('do_command', LIMIT))
        typed = s.step(L.peek('inbuf', 20)).data.split(b'\0')[0].decode()
        s.step(L.until('q_care_wait', LIMIT))
        s.step(f'press:{RET}'); s.step(L.until('keyboard_wait', LIMIT))
        log.append(('bleeding', [typed], int.from_bytes(s.step(L.peek('mli_reads', 2)).data, 'little') - reads, 0))
        assert typed == 'STOP BLEEDING' and peek(s, 'medical_actions', 0) == 1 and \
            peek(s, 'injury_treated', 0) == 1, log
    print(f'  {disk.name}:')
    for name, commands, reads, cycles in log:
        time = f', {cycles / a2test.CPU_HZ:.2f} s' if cycles else ''
        print(f'    {name:10} {", ".join(commands)}: {reads} READ_BLOCK{time}')


def frame(disk):
    """The grid's cells (docs/MENUS.md 9): on NeoWildernessXL a bar on the
    right of each labelled cell ($5A) and the separator a bar ($5F); the
    140 KB edition keeps its spaces and "|"."""
    with a2test.Session(disk) as s:
        s.step(L.until('idle', LIMIT))
        s.step('key:\\v')
        s.step('wait:5')
        mem = s.step('peek:0400:1024').data
        rows = text_screen(mem)[20:24]
        if disk == DISK:
            assert rows[0][39:] == '\u258f WALK \u2595LOOK \u2595REST \u2595WAIT \u2595EAT  \u2595DRINK    ', rows[0]
            assert all(r[39] == '\u258f' for r in rows), rows
        else:
            assert rows[0][39:] == '| WALK  LOOK  REST  WAIT  EAT   DRINK    ', rows[0]
    print(f'  {disk.name}: the grid\'s cells ' + ('in MouseText boxes' if disk == DISK else 'plain') + ': OK')


def one_ounce(disk):
    """The last ounce can be chosen with arrows alone, exactly as typed."""
    from test_menu_bar import choose, typed, move_to, press, ESC
    from test_input import snapshot

    def state(s):
        return (snapshot(s), s.step(L.peek('s_hour', L['s_t0']+5-L['s_hour'])).data)

    for labels, line in ((('DRINK',), 'DRINK WATER 1 OZ'),
                         (('EAT', 'EGGS', '1 OZ'), 'EAT EGGS 1 OZ'),
                         (('BOIL',), 'BOIL WATER 1 OZ')):
        outcomes = []
        for grid in (True, False):
            with a2test.Session(disk) as s:
                s.step(IDLE)
                s.step(L.poke('nature_frequency', 0))
                # One ounce in the canteen and of eggs in the pack; none
                # on the ground. A ready fire/utensils skips BOIL's setup.
                for item in (22, 24):
                    for name, value in (('it_pack_lo', 1), ('it_pack_hi', 0),
                                        ('it_gnd_lo', 0), ('it_gnd_hi', 0),
                                        ('it_place', 2)):
                        s.step(L.poke(name, value, item))
                s.step(L.poke('fire_on', 1))
                s.step(L.poke('camp_use', 32))
                typed(s, 'LOOK AHEAD')       # rebuild the contextual verbs
                if grid:
                    press(s, RET)
                    if labels[0] == 'EAT':
                        before = state(s)
                        move_to(s, 'EAT'); press(s, RET)
                        move_to(s, 'EGGS'); press(s, RET)
                        assert sum(grid_cells(s), []) == ['TASTE', '1', 'OZ'], bottom(s)
                        press(s, ESC, ESC)
                        assert state(s) == before, 'cancelling the portion changed the journey'
                        if selected(s) is None:
                            press(s, RET)
                    composed, _ = choose(s, *labels, settle=labels[0] != 'BOIL')
                    if labels[0] == 'BOIL':
                        decline_followup(s)
                    assert composed == line, (labels, composed)
                    assert peek(s, 'mq_n') == 0
                else:
                    typed(s, line)
                item = 24 if labels[0] == 'EAT' else 22
                assert peek(s, 'it_pack_lo', item) == 0, (line, bottom(s))
                if labels[0] == 'BOIL':
                    assert peek(s, 'it_gnd_lo', 22) == 1, bottom(s)
                else:
                    result = 'YOU ATE 1 OUNCE.' if item == 24 else 'YOU DRANK 1 OUNCE.'
                    assert result in '\n'.join(bottom(s)), bottom(s)
                outcomes.append(state(s))
        assert outcomes[0] == outcomes[1], (disk, line, 'grid differs from typed command')
    print(f'  {disk.name}: last ounce of food/water, BOIL 1 OZ, atomic ESC; grid = typed simulation, no numeric prompt: OK')


def main():
    for disk in (DISK,):
        one_ounce(disk)
    for disk in (DISK,):
        frame(disk)
    for disk in (DISK,):
        play(disk)
    print('The grid with the arrows and RETURN alone (fire, boiled water, mushrooms, bleeding), both editions: OK')


if __name__ == '__main__':
    main()
