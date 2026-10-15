#!/usr/bin/env python3
"""The grid played with the arrows and RETURN alone (docs/MENUS.md 4), on
both editions: from the start of the Sierra Nevada journey, light a fire
(MAKE, FIRE: USE MATCHES, MAKE FIRE and USE FIRE in the morning cold, the
grid's queue), boil water (BOIL, 8 OZ: USE UTENSILS, BOIL WATER 8 OZ),
eat a pile of mushrooms found here (EAT, MUSHROOMS, 8 OZ, lot 4) and stop a
bleeding (CARE: the MEDICAL page on SEVERE CUTS, RETURN on STOP BLEEDING).
Only the keys a joystick gives are pressed: LEFT, RIGHT, UP, DOWN, RETURN.

Each action reports its keys, the commands typed for the player, its disk
reads (NEOWILD.BLK: FORAGE, MEDVIEW on both editions) and its emulated time.
"""
from common import L, DISK, DISK140, a2test, text_screen
from test_menu_bar import grid_cells, selected, bottom, RIGHT, RET

LIMIT = 400000
IDLE = L.until('idle', LIMIT)
KEYS = {'\\<', '\\>', '\\^', '\\v', '\\r'}
MUSHROOMS = 85 - 76                     # their pile (src/forage.s fg_*)


def peek(s, name, k=0):
    return s.step(L.peek(name, 1, k)).data[0]


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
            for label in labels[:-1]:
                to(label)
                key(RET)
                s.step(IDLE)
            to(labels[-1])
            reads = int.from_bytes(s.step(L.peek('mli_reads', 2)).data, 'little')
            s.step(f'press:{RET}')              # in the latch at once: do_command is on the way
            commands = []
            out = s.step(L.until('do_command', LIMIT))
            cycles0 = out.cycles[-1]
            while True:
                commands.append(s.step(L.peek('inbuf', 24)).data.split(b'\0')[0].decode())
                out = s.step(f'until:{L["get_line"]:04X},{L["scr_status"]:04X}:{LIMIT}')
                if f'PC={L["scr_status"]:04X}' in out.out:
                    break
                out = s.step(f'until:{L["do_command"]:04X},{L["idle"]:04X}:{LIMIT}')
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
        # Water: BOIL, 8 OZ (the utensils first).
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
        # A bleeding (poked: the next grid offers CARE; UP above the first
        # row closes the grid and rebuilds it, RETURN reopens it): CARE,
        # the MEDICAL page on SEVERE CUTS, RETURN.
        s.step(L.poke('injury_active', 1, 0))
        for _ in range(4):
            if selected(s) is None:
                break
            key('\\^')
            s.step(IDLE)
        key(RET)
        s.step(IDLE)
        out = action('care', 'CARE')
        assert f'PC={L["scr_status"]:04X}' in out.out, out.out
        s.step(L.until('keyboard_wait', LIMIT))
        row = text_screen(s.step('peek:0400:1024').data)[23]
        foot = ' \u2190\u2192 ' if disk == DISK else ''     # XL: the pages' footer (docs/MENUS.md 9)
        assert peek(s, 'pg_focus') == 1 and row.startswith(foot + 'STOP BLEEDING'), row
        reads = int.from_bytes(s.step(L.peek('mli_reads', 2)).data, 'little')
        s.step(f'press:{RET}')
        s.step(L.until('do_command', LIMIT))
        typed = s.step(L.peek('inbuf', 20)).data.split(b'\0')[0].decode()
        s.step(IDLE)
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
            assert rows[0][39:] == '\u258f WALK \u2595LOOK \u2595REST \u2595WAIT \u2595EAT  \u2595DRINK\u2595   ', rows[0]
            assert all(r[39] == '\u258f' for r in rows), rows
        else:
            assert rows[0][39:] == '| WALK  LOOK  REST  WAIT  EAT   DRINK    ', rows[0]
    print(f'  {disk.name}: the grid\'s cells ' + ('in MouseText boxes' if disk == DISK else 'plain') + ': OK')


def main():
    for disk in (DISK, DISK140):
        frame(disk)
    for disk in (DISK, DISK140):
        play(disk)
    print('The grid with the arrows and RETURN alone (fire, boiled water, mushrooms, bleeding), both editions: OK')


if __name__ == '__main__':
    main()
