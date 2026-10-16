#!/usr/bin/env python3
"""The four 80-column rows as a command surface (src/menu.s, src/grid.s;
docs/MENUS.md 4).

Rows 20-23, columns 0-38: the result column: the last message, wrapped by
words, and on its last row the stock row or the command as the parser reads
it while one is typed or composed; column 39 the separator (^ / V when rows
are out of view); columns 41-78: the grid of verbs, then the list of the
open verb (durations, directions, items, ounces), scrolled by row, the
selected cell in inverse.

The grid: eleven base verbs at fixed cells (a verb that cannot act here is
greyed, in lower case, and RETURN on it only beeps), then the contextual
verbs that can act, by urgency (an animal's KILL first, the cursor on it
when the animal arrives). Every choice composes the text the keyboard
would give (read in inbuf when do_command starts) and the simulation state
equals the typed command's; an item chosen in a list names its noun through
menu_noun (COTTN SOCKS is not a vocabulary word); a list of one entry is
skipped; a choice that needs other commands first (MAKE FIRE: USE MATCHES,
then USE FIRE in the cold) queues them, and the state equals the same
commands typed; ESC backs up; letters return to the typed line; nothing
changes until a command runs.
"""
import re
import tempfile
from common import HERE, L, DISK, a2test, disk_with, text_screen, result_rows, is_status
from test_input import flat, snapshot, IDLE

DO_COMMAND = L.until('do_command', 6000)
RET, ESC, LEFT, RIGHT, UP, DOWN = '\\r', '\\e', '\\<', '\\>', '\\^', '\\v'
TAB = '\t'
# The base verbs at their fixed cells (row 20, then row 21; src/menu.s
# verb_table): WALK becomes SWIM in or facing water; on the flat test map
# (no tree, no water, no fire) no contextual verb applies at the start.
# STATUS, INVENTORY, TOPO, MAP, HELP and QUIT left the grid with the pages
# (14 October 2026): the arrows reach them, the MENU page types QUIT.
BASE = ['WALK', 'LOOK', 'REST', 'WAIT', 'EAT', 'DRINK', 'GET', 'WEAR', 'DROP', 'USE', 'MAKE']


def screen(s):
    return text_screen(s.step('peek:0400:1024').data)


def bottom(s):
    return screen(s)[20:]


def grid_cells(s):
    """The labels of the four grid rows (right column), row by row (XL: the
    bars after the cells, docs/MENUS.md 9, are not labels)."""
    return [r[41:79].replace('\u2595', ' ').split() for r in bottom(s)[:4]]


def selected(s):
    """The inverse cell of the grid (the selection), or None. A greyed verb
    keeps its lower-case letters normal (the primary character set has no
    inverse lower case): the spaces after it are inverse, its label is read
    before them."""
    mem = s.step('peek:0400:1024').data
    for row in range(20, 24):
        o = (row % 8) * 128 + (row // 8) * 40
        cells = bytes(b for pair in zip(mem[1024 + o:1024 + o + 40], mem[o:o + 40]) for b in pair)
        inverse = ''.join(chr(c + 0x40) if c < 0x20 else chr(c) if c < 0x40 else ' '
                          for c in cells[41:79])
        if inverse.strip():
            return inverse.strip()
        cols = [c for c in range(41, 79) if cells[c] < 0x80 and not 0x40 <= cells[c] < 0x60]
        if cols:
            start = cols[0]
            while start > 41 and cells[start - 1] >= 0xE0:
                start -= 1
            return ''.join(chr(c & 0x7F) for c in cells[start:cols[0]])
    return None


def press(s, *keys):
    # One key at a time: with 23 verbs (lot 2) an arrow redraws the grid in
    # about 65,000 cycles, more than the three frames between the keys of one
    # a2shot key: step, and the single keyboard latch would lose one.
    for k in keys:
        s.step(f'key:{k}')
        s.step('wait:1')
        s.step(IDLE)


def move_to(s, label, limit=40):
    """RIGHT until `label` is the selection (the grid scrolls as needed)."""
    for _ in range(limit):
        if selected(s) == label:
            return
        press(s, RIGHT)
    raise AssertionError((label, grid_cells(s), selected(s)))


def choose(s, *labels):
    """Select each label in turn with RETURN; the last one runs the command:
    returns (inbuf, menu_noun) as do_command sees them."""
    for label in labels:
        move_to(s, label)
        if label is labels[-1]:
            s.step(f'press:{RET}')  # in the latch at once: do_command is on the way
            s.step(DO_COMMAND)
        else:
            press(s, RET)
    inbuf = s.step(L.peek('inbuf', 37)).data.split(b'\0')[0].decode()
    noun = s.step(L.peek('menu_noun')).data[0]
    s.step(IDLE)
    return inbuf, noun


def typed(s, text):
    s.step(f'key:{text}')
    s.step(f'press:{RET}')
    s.step('wait:1')
    s.step(IDLE)


def layout(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        rows = bottom(s)
        assert grid_cells(s) == [BASE[:6], BASE[6:], [], []], rows
        assert all(rows[k][39] == '|' for k in range(4)), 'every verb in view: no scroll mark'
        res = result_rows(rows)
        assert res[0].startswith('CRASH IN') and res[3].startswith('FOOD '), rows
        assert re.fullmatch(r'FOOD \d+ WATER \d+ LOCAL \d+/\d+ OZ *', res[3]), 'the whole stock row fits'
        assert selected(s) is None, 'typed line: no selection'
        press(s, RET)
        assert selected(s) == 'WALK', bottom(s)
        press(s, DOWN)
        assert selected(s) == 'GET', 'DOWN: the cell below'
        press(s, RIGHT, RIGHT, RIGHT)
        assert selected(s) == 'USE'
        press(s, UP)
        assert selected(s) == 'WAIT'
        before = snapshot(s)
        press(s, UP)
        assert selected(s) is None and snapshot(s) == before, 'UP above the first row: back to the view'
        press(s, RET)
        assert selected(s) == 'WAIT', 'RETURN reopens the grid on the same verb'
        press(s, ESC)
        assert selected(s) is None, 'ESC closes the grid'
        press(s, TAB)
        assert selected(s) == 'WAIT', 'TAB opens the grid on the last verb'
        press(s, RIGHT, RIGHT)
        assert selected(s) == 'DRINK'
        press(s, DOWN)
        assert selected(s) == 'MAKE', 'no cell below: the last cell of the shorter last row'
        press(s, LEFT, LEFT, LEFT, LEFT, LEFT, LEFT, LEFT)
        assert selected(s) == 'WAIT'
        press(s, ESC)
        # DOWN on the view opens the grid (on the last verb), DOWN moves
        # down its rows; DOWN past the last row closes it and opens the
        # bottom pages (TOPO first); UP from TOPO: the view, the grid closed.
        press(s, DOWN)
        assert selected(s) == 'WAIT', 'DOWN opens the grid'
        press(s, DOWN)
        assert selected(s) == 'USE'
        s.step(f'key:{DOWN}')
        s.step(L.until('graphical_topo_key', 20000))
        assert screen(s)[20].startswith('TOPO, NORTH UP'), bottom(s)
        press(s, UP)
        assert selected(s) is None and snapshot(s) == before, 'DOWN past the last row: TOPO, UP: the view, no grid'
        press(s, TAB)
        assert selected(s) == 'WAIT', 'TAB too'
        press(s, RET)                               # WAIT: its list of durations
        assert grid_cells(s)[0][0] == '10', grid_cells(s)
        press(s, TAB)
        assert selected(s) is None and grid_cells(s)[0] == BASE[:6], 'TAB closes the grid from a list'
        before = snapshot(s)
        press(s, TAB, RIGHT, ESC)
        assert snapshot(s) == before, 'navigation runs no command'
        # The list of a verb scrolls: EAT names the provisions and the
        # remedies at hand, three per row.
        press(s, RET)
        move_to(s, 'EAT')
        press(s, RET)
        cells = grid_cells(s)
        assert cells[0] == ['EGGS', 'CANDYBARS', 'BACON'] and rows[0][39] == '|', cells
        assert bottom(s)[3][39] == 'V', 'more rows below: V in the separator'
        press(s, DOWN, DOWN, DOWN, DOWN)
        assert bottom(s)[0][39] == '^', bottom(s)
        press(s, ESC, ESC)
    print('  eleven base verbs at fixed cells, selection, RETURN, ESC and TAB, DOWN = grid then TOPO, '
          'scrolling marks of a list: OK')


def composition(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        press(s, RET)
        # COTTN SOCKS is a display name: the parser would read SOCKS (wool).
        # Ground items lie on the crash cell: before any travel. GET packs
        # them (PACK x; CARRY x if PACK is refused, not needed here).
        assert choose(s, 'GET', 'COTTN SOCKS') == ('PACK COTTN SOCKS', 18)
        assert s.step(L.peek('it_place', 1, 18)).data[0] == 2 and 'PACK: COTTN SOCKS' in result_rows(screen(s))[0]
        assert s.step(L.peek('mq_n')).data[0] == 0, 'PACK done: the fallback CARRY is dropped'
        assert choose(s, 'WALK', '20 MIN') == ('WALK 20 MIN', 0)
        assert selected(s) == 'WALK', 'a command from the grid leaves it open'
        assert 'TRAVEL: 18 MINUTES.' in '\n'.join(result_rows(screen(s)))
        menu = (s.step(L.peek('px', 2)).data, s.step(L.peek('s_elap', 5)).data)
        assert choose(s, 'LOOK', 'RIGHT') == ('LOOK RIGHT', 0)
        heading = s.step(L.peek('heading', 2)).data
        for label, tilt in (('UP', 1), ('DOWN', 255), ('AHEAD', 0)):    # LOOK UP / DOWN
            assert choose(s, 'LOOK', label) == (f'LOOK {label}', 0)
            assert s.step(L.peek('tilt')).data[0] == tilt, label
        assert choose(s, 'REST', '10 MIN') == ('REST 10 MIN', 0)
        assert 'YOU RESTED 10 MINUTES.' in result_rows(screen(s))[0]
        assert result_rows(screen(s))[3].startswith('FOOD ') and 'WATER' in result_rows(screen(s))[3], \
            'the stock row takes the free last row'
        # One source of water (the canteen and the crash site's pile): DRINK
        # goes straight to the ounces, at most .2 x the body weight (33).
        move_to(s, 'DRINK')
        press(s, RET)
        assert sum(grid_cells(s), []) == ['1', 'OZ', '2', 'OZ', '4', 'OZ', '8', 'OZ', '12', 'OZ', '16', 'OZ', '24', 'OZ',
                                          '32', 'OZ'], grid_cells(s)
        press(s, ESC)
        assert choose(s, 'DRINK', '4 OZ') == ('DRINK WATER 4 OZ', 22)
        assert 'YOU DRANK 4 OUNCES.' in result_rows(screen(s))[0]
        water = s.step(L.peek('it_pack_lo', 1, 22)).data[0]
        # EAT: TASTE first, then the ounces, at most what is here (16 oz).
        move_to(s, 'EAT')
        press(s, RET)
        move_to(s, 'EGGS')
        press(s, RET)
        assert sum(grid_cells(s), []) == ['TASTE', '1', 'OZ', '2', 'OZ', '4', 'OZ', '8', 'OZ', '12', 'OZ', '16', 'OZ'], grid_cells(s)
        press(s, ESC)
        assert choose(s, 'EAT', 'EGGS', '8 OZ') == ('EAT EGGS 8 OZ', 24)
        assert 'YOU ATE 8 OUNCES.' in result_rows(screen(s))[0]
        assert s.step(L.peek('it_pack_lo', 1, 24)).data[0] == 16 - 8
        assert choose(s, 'EAT', 'EGGS', 'TASTE') == ('TASTE EGGS', 24)
        # WEAR: the clothes not worn, then the worn ones ("-"), which PACK
        # takes off.
        move_to(s, 'WEAR')
        press(s, RET)
        items = [c.strip() for r in bottom(s) for c in (r[41:53], r[53:65], r[65:79]) if c.strip()]
        assert items[0] == 'DOWN PARKA' and '-WOOL PANTS' in items and \
            items.index('RAINCOAT') < items.index('-BALACLAVA'), items
        press(s, ESC)
        assert choose(s, 'WEAR', 'DOWN PARKA') == ('WEAR DOWN PARKA', 2)
        assert s.step(L.peek('it_place', 1, 2)).data[0] == 1 and 'WEARING: DOWN PARKA' in result_rows(screen(s))[0]
        assert choose(s, 'WEAR', '-MITTENS') == ('PACK MITTENS', 7)
        assert s.step(L.peek('it_place', 1, 7)).data[0] == 2
        final = snapshot(s)
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        s.step('key:PACK SOCKS')         # the typed equivalent needs the item's own word
        s.step(L.poke('menu_noun', 18))
        s.step(f'press:{RET}')
        s.step('wait:1')
        s.step(IDLE)
        typed(s, 'WALK 20 MIN')
        assert (s.step(L.peek('px', 2)).data, s.step(L.peek('s_elap', 5)).data) == menu
        typed(s, 'LOOK R')
        assert s.step(L.peek('heading', 2)).data == heading
        for text in ('LOOK UP', 'LOOK DOWN', 'LOOK AHEAD'):
            typed(s, text)
        for text in ('REST 10 MIN', 'DRINK WATER 4 OZ', 'EAT EGGS 8 OZ', 'TASTE EGGS', 'WEAR PARKA',
                     'PACK MITTENS'):
            typed(s, text)
        assert s.step(L.peek('it_pack_lo', 1, 22)).data[0] == water
        assert snapshot(s) == final, 'menu and keyboard reach the same state'
    print('  WALK, LOOK (RIGHT, UP, DOWN, AHEAD), REST, DRINK (one source: the ounces), EAT (TASTE, the ounces), '
          'WEAR (on, off), GET (PACK) composed from the grid = typed: OK')


def contexts(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('shelter_inside', 1))
        typed(s, 'V')
        assert grid_cells(s)[:2] == [BASE[:6], BASE[6:] + ['EXIT']], grid_cells(s)
        s.step(L.poke('shelter_inside', 0))
        x, y = (s.step(L.peek(n, 1, 1)).data[0] for n in ('px', 'py'))
        # An animal arrives: KILL (ATTACK), SCARE, IGNORE first among the
        # contextual verbs, the cursor on KILL.
        for name, value in (('animal_kind', 6), ('animal_x', x), ('animal_y', y)):
            s.step(L.poke(name, value))
        typed(s, 'V')
        assert grid_cells(s)[1:3] == [BASE[6:] + ['KILL'], ['SCARE', 'IGNORE']], grid_cells(s)
        press(s, RET)
        assert selected(s) == 'KILL', 'the cursor on KILL when an animal arrives'
        press(s, ESC)
        s.step(L.poke('animal_kind', 0))
        typed(s, 'V')
        assert grid_cells(s)[0][0] == 'WALK'
        # The place's conditions (src/game.s verb_extra): SWIM in water (the
        # player's cell made water; swim_ok's cache forgotten), CLIMB from a
        # tree (CLIMB DOWN), LOWER with the backpack hung on this cell.
        cell = 0x7040 + y * 112 + x
        ground = s.step(f'peek:{cell:04X}:1').data[0]
        s.step(f'poke:{cell:04X}:{ground | 0x80:02X}')
        s.step(L.poke('wb_key', 0xFF, 5))     # heading high byte: never $FF
        typed(s, 'V')
        verbs = sum(grid_cells(s), [])
        assert verbs[0] == 'SWIM' and 'WALK' not in verbs, ('in water: SWIM; WALK meets "WATER AHEAD"', verbs)
        s.step(f'poke:{cell:04X}:{ground:02X}')
        # Water ahead: a shore three quarters into the cell, heading east
        # (the start's); a turn rebuilds the grid (SWIM follows the heading).
        for dx in (1, 2):
            s.step(f'poke:{cell + dx:04X}:{ground | 0x80:02X}')
        fraction = s.step(L.peek('px')).data[0]
        s.step(L.poke('px', 0xC0))
        typed(s, 'V')
        verbs = sum(grid_cells(s), [])
        assert 'SWIM' in verbs and 'WALK' not in verbs, ('water ahead: SWIM, no WALK', verbs)
        for _ in range(4):                     # north: 4 x 22.5 degrees
            press(s, LEFT)
            s.step(IDLE)
        verbs = sum(grid_cells(s), [])
        assert 'SWIM' not in verbs and 'WALK' in verbs, ('turned away from the water', verbs)
        for _ in range(4):
            press(s, RIGHT)
            s.step(IDLE)
        assert 'SWIM' in sum(grid_cells(s), []), 'facing it again'
        for dx in (1, 2):
            s.step(f'poke:{cell + dx:04X}:{ground:02X}')
        s.step(L.poke('px', fraction))
        s.step(L.poke('wb_key', 0xFF, 5))     # heading high byte: never $FF
        s.step(L.poke('tree_in', 1))
        typed(s, 'V')
        verbs = sum(grid_cells(s), [])
        assert 'CLIMB' in verbs and 'SWIM' not in verbs and 'HANG' not in verbs, verbs
        s.step(L.poke('tree_in', 0))
        place = s.step(L.peek('it_place', 1, 21)).data[0]
        for name, value in (('it_place', 5), ('it_x', x), ('it_y', y)):
            s.step(L.poke(name, value, 21))
        typed(s, 'V')
        verbs = sum(grid_cells(s), [])
        assert 'LOWER' in verbs and 'CLIMB' not in verbs, verbs
        s.step(L.poke('it_place', place, 21))
        typed(s, 'V')
        assert grid_cells(s)[0] == BASE[:6], grid_cells(s)
        # Lists: ESC goes back to the verbs, a letter to the typed line.
        press(s, RET)
        move_to(s, 'EAT')
        press(s, RET)
        assert grid_cells(s)[0][0] == 'EGGS' and result_rows(screen(s))[3].startswith('> EAT'), bottom(s)
        press(s, ESC)
        assert selected(s) == 'EAT' and result_rows(screen(s))[3].startswith('FOOD ')
        press(s, 'L')
        assert selected(s) is None and result_rows(screen(s))[3].startswith('> L'), 'a letter types'
        press(s, ESC)
        assert result_rows(screen(s))[3].startswith('FOOD ')
        # A base verb with nothing to name stays at its cell, greyed (lower
        # case): no medicine, no instrument (lot 7: USE MAP...CHART) and no
        # camp item (lot 2: MATCHES, GLASS, FUEL, FLASHLIGHT, STOVE,
        # UTENSILS), no USE; no water at hand, no DRINK. RETURN on it beeps
        # and does nothing else.
        for item in list(range(38, 57)) + [66, 71, 73]:
            s.step(L.poke('it_place', 255, item))
        s.step(L.poke('cr_b1', 255, 3))           # no ROCK (lot 3: USE ROCK on land)
        s.step(L.poke('cr_still', 1))
        s.step(L.poke('it_pack_lo', 0, 22))       # the canteen and the crash
        s.step(L.poke('it_gnd_lo', 0, 22))        # site's water pile both empty
        typed(s, 'V')
        assert grid_cells(s)[:2] == [BASE[:5] + ['drink'], BASE[6:9] + ['use', 'MAKE' if
                                     'MAKE' in grid_cells(s)[1] else 'make']], grid_cells(s)
        before = snapshot(s)
        press(s, RET)
        move_to(s, 'use')
        line = result_rows(screen(s))[3]
        press(s, RET)
        assert selected(s) == 'use' and snapshot(s) == before and result_rows(screen(s))[3] == line, \
            'RETURN on a greyed verb: nothing'
        press(s, ESC)
        s.step(L.poke('it_pack_lo', 40, 22))
        typed(s, 'V')
        assert grid_cells(s)[0] == BASE[:6], 'water in the canteen: DRINK'
        # UP on the typed line shows STATUS; the numeric prompt uses the
        # last row of the result column.
        s.step(f'key:{UP}')
        s.step(L.until('status_key', 20000))
        assert is_status(screen(s), xl=False)          # (disk_with: the plain pages)
        s.step(f'key:{ESC}')
        s.step(IDLE)
        assert grid_cells(s)[0] == BASE[:6], 'the grid is back after a screen'
        s.step('key:WALK')
        s.step(f'press:{RET}')
        s.step(L.until('input_number_idle', 20000))
        res = result_rows(screen(s))
        assert res[3].startswith('> ') and 'DURATION?' in res[0], res
        s.step(f'key:{ESC}')
        s.step(IDLE)
        assert 'ACTION CANCELLED.' in result_rows(screen(s))[0]
    print('  contextual verbs (shelter, animal, water ahead or around: SWIM/WALK, tree, hung pack), ESC and letters from a list, '
          'verbs without items hidden, UP = STATUS, numeric prompt: OK')


def state(s):
    """The journey's state, wider than snapshot(): the core block (position
    to the travel raster: clock, body, deficits, health), the items, the
    camp (fire, light, in-use flags), lot 4's piles, the conditions, the
    generators, and the last message."""
    blocks = [('px', L['travel_delta'] + 5 - L['px']),
              ('camp_state', L['camp_state_end'] - L['camp_state']),
              ('forage_state', L['forage_state_end'] - L['forage_state']),
              ('medical_state', L['medical_state_end'] - L['medical_state']),
              ('fauna_rng', 1), ('water_rng', 1), ('weather_seed', 4)]
    blocks += [(name, 76) for name in ('it_place', 'it_pack_lo', 'it_pack_hi', 'it_gnd_lo', 'it_gnd_hi')]
    return tuple(s.step(L.peek(name, size)).data for name, size in blocks), result_rows(screen(s))[:3]


def queues(disk):
    """A choice that needs commands first queues them (src/grid.s): MAKE
    FIRE lights a match first and warms up at the fire in the cold, BOIL
    sets the utensils down first; every step is typed as the keyboard would
    (same time, draws and state), a step already done is skipped."""
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        press(s, RET)
        move_to(s, 'MAKE')
        press(s, RET)
        move_to(s, 'FIRE')
        s.step(f'press:{RET}')
        steps = []
        while True:
            s.step(DO_COMMAND)
            steps.append((s.step(L.peek('inbuf', 20)).data.split(b'\0')[0].decode(),
                          s.step(L.peek('menu_noun')).data[0]))
            if not s.step(L.peek('mq_n')).data[0]:
                break                                   # the last step
            s.step(L.until('get_line', 400000))         # the step ran: the queue's next
        felt = int.from_bytes(s.step(L.peek('felt_temp', 2)).data, 'little', signed=True)
        s.step(IDLE)
        cold = [('USE FIRE', 88)] if felt < 50 else []
        assert steps == [('USE MATCHES', 38), ('MAKE FIRE', 88)] + cold, (steps, felt)
        typed_fire = ['USE MATCHES', 'MAKE FIRE'] + ['USE FIRE'] * bool(cold)
        assert s.step(L.peek('fire_on')).data[0] and s.step(L.peek('fire_near')).data[0] == bool(cold)
        fire = state(s)
        assert 'BOIL' in sum(grid_cells(s), []), 'a fire, utensils, water: BOIL'
        move_to(s, 'BOIL')
        press(s, RET)
        assert grid_cells(s)[:2] == [['1', 'OZ', '2', 'OZ', '4', 'OZ', '8', 'OZ', '12', 'OZ', '16', 'OZ'],
                                     ['24', 'OZ', '32', 'OZ', '48', 'OZ']], ('the ounces, at most the canteen\'s 64', grid_cells(s))
        move_to(s, '8 OZ')
        s.step(f'press:{RET}')
        s.step(DO_COMMAND)
        assert s.step(L.peek('inbuf', 20)).data.startswith(b'USE UTENSILS\0')
        s.step(L.until('get_line', 400000))
        s.step(DO_COMMAND)
        assert s.step(L.peek('inbuf', 20)).data.startswith(b'BOIL WATER 8 OZ\0'), s.step(L.peek('inbuf', 20)).data
        s.step(IDLE)
        assert s.step(L.peek('mq_n')).data[0] == 0
        boil = state(s)
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        for text in typed_fire:
            typed(s, text)
        assert state(s) == fire, ('MAKE FIRE from the grid = the same commands typed', typed_fire)
        typed(s, 'USE UTENSILS')
        s.step('key:BOIL WATER')
        s.step(f'press:{RET}')
        s.step(L.until('input_number_idle', 400000))
        # The amount asked is the canteen's, the water BOIL takes (it
        # announced the canteen and the pile together before).
        assert result_rows(screen(s))[0].startswith('ACCESSIBLE: 64 OZ.'), result_rows(screen(s))
        s.step('key:\\e')
        s.step(IDLE)
        typed(s, 'BOIL WATER 8 OZ')
        assert state(s) == boil, 'BOIL WATER 8 OZ from the grid = USE UTENSILS, BOIL WATER 8 OZ typed'
        # Typed commands keep the original's refusals: no queue.
        typed(s, 'DOUSE FIRE')
        typed(s, 'MAKE FIRE')
        assert 'APPROPRIATE ITEM' in ' '.join(result_rows(screen(s))) and \
            not s.step(L.peek('fire_on')).data[0], result_rows(screen(s))
    print(f'  queues: MAKE FIRE ({", ".join(typed_fire)}: {felt} F felt), BOIL 8 OZ (USE UTENSILS, BOIL WATER '
          "8 OZ) = the same commands typed; typed BOIL WATER asks the canteen's ounces; typed MAKE FIRE keeps its refusal: OK")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, flat())
        layout(disk)
        composition(disk)
        contexts(disk)
        queues(disk)
    print('Neowilderness menu bar (lot 8 step 2): OK')


if __name__ == '__main__':
    main()
