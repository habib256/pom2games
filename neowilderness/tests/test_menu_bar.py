#!/usr/bin/env python3
"""The four 80-column rows as a command surface (src/menu.s, lot 8 step 2).

Rows 20-22, columns 0-37: the grid of verbs, then the list of the open verb
(durations, directions, items, ounces), scrolled by row, the selected cell
in inverse; column 38 the separator (^ / V when rows are out of view);
columns 40-78 the result column (the last message, wrapped by words, then
the stock row); row 23 the command as the parser reads it, then the hints.

Every choice composes the text the keyboard would give (read in inbuf when
do_command starts) and the simulation state equals the typed command's;
an item chosen in a list names its noun through menu_noun (COTTN SOCKS is
not a vocabulary word); contextual verbs come first when they apply; ESC
backs up; letters return to the typed line; nothing changes until a
command runs.
"""
import tempfile
from common import HERE, L, DISK, a2test, disk_with, text_screen, result_rows
from test_input import flat, snapshot, IDLE

DO_COMMAND = L.until('do_command', 6000)
RET, ESC, LEFT, RIGHT, UP, DOWN = '\\r', '\\e', '\\<', '\\>', '\\^', '\\v'
BASE = ['WALK', 'SWIM', 'LOOK', 'REST', 'WAIT', 'EAT', 'DRINK', 'GET', 'TAKE', 'WEAR', 'DROP',
        'USE', 'CLIMB', 'HANG', 'LOWER', 'STATUS', 'INVENT', 'TOPO', 'MAP', 'HELP', 'QUIT']


def screen(s):
    return text_screen(s.step('peek:0400:1024').data)


def bottom(s):
    return screen(s)[20:]


def grid_cells(s):
    """The labels of the three grid rows (left column), row by row."""
    return [r[:38].split() for r in bottom(s)[:3]]


def selected(s):
    """The inverse cell of the grid (the selection), or None."""
    mem = s.step('peek:0400:1024').data
    for row in range(20, 23):
        o = (row % 8) * 128 + (row // 8) * 40
        cells = bytes(b for pair in zip(mem[1024 + o:1024 + o + 20], mem[o:o + 20]) for b in pair)
        inverse = ''.join(chr(c + 0x40) if c < 0x20 else chr(c) if c < 0x40 else ' '
                          for c in cells[:38])
        if inverse.strip():
            return inverse.strip()
    return None


def press(s, *keys):
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
        assert grid_cells(s)[0] == BASE[:6] and grid_cells(s)[2] == BASE[12:18], rows
        assert rows[2][38] == 'V' and rows[0][38] == '|', 'more rows below: V in the separator'
        assert rows[3].startswith('> ') and 'RET: MENU' in rows[3][40:], rows[3]
        assert result_rows(rows)[0].startswith('CRASH IN'), rows
        assert selected(s) is None, 'typed line: no selection'
        press(s, RET)
        assert selected(s) == 'WALK' and 'ARROWS: MOVE' in bottom(s)[3][40:], bottom(s)
        press(s, DOWN, DOWN, DOWN)
        assert selected(s) == 'MAP' and grid_cells(s)[2] == BASE[18:], grid_cells(s)
        assert bottom(s)[0][38] == '^' and bottom(s)[2][38] == '|', bottom(s)
        press(s, LEFT, LEFT)
        assert selected(s) == 'INVENT'
        press(s, UP, UP, UP)
        assert selected(s) == 'WAIT', 'UP stops on the first row'
        press(s, ESC)
        assert selected(s) is None and 'RET: MENU' in bottom(s)[3][40:], 'ESC closes the grid'
        before = snapshot(s)
        press(s, UP, RIGHT, ESC)
        assert snapshot(s) == before, 'navigation runs no command'
    print('  grid of verbs, scrolling marks, selection, ESC: OK')


def composition(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        press(s, RET)
        # COTTN SOCKS is a display name: the parser would read SOCKS (wool).
        # Ground items lie on the crash cell: before any travel.
        assert choose(s, 'GET', 'COTTN SOCKS') == ('GET COTTN SOCKS', 18)
        assert s.step(L.peek('it_place', 1, 18)).data[0] == 2 and 'PACK: COTTN SOCKS' in result_rows(screen(s))[0]
        assert choose(s, 'WALK', '20 MIN') == ('WALK 20 MIN', 0)
        assert selected(s) == 'WALK', 'a command from the grid leaves it open'
        assert 'TRAVEL: 18 MINUTES.' in '\n'.join(result_rows(screen(s)))
        menu = (s.step(L.peek('px', 2)).data, s.step(L.peek('s_elap', 5)).data)
        assert choose(s, 'LOOK', 'RIGHT') == ('LOOK RIGHT', 0)
        heading = s.step(L.peek('heading', 2)).data
        assert choose(s, 'REST', '10 MIN') == ('REST 10 MIN', 0)
        assert 'YOU RESTED 10 MINUTES.' in result_rows(screen(s))[0]
        assert 'FOOD' in result_rows(screen(s))[2] and 'WATER' in result_rows(screen(s))[2], \
            'the stock row takes the free third row'
        assert choose(s, 'DRINK', '4 OZ') == ('DRINK WATER 4 OZ', 0)
        assert 'YOU DRANK 4 OUNCES.' in result_rows(screen(s))[0]
        water = s.step(L.peek('it_pack_lo', 1, 22)).data[0]
        assert choose(s, 'EAT', 'EGGS', '8 OZ') == ('EAT EGGS 8 OZ', 24)
        assert 'YOU ATE 8 OUNCES.' in result_rows(screen(s))[0]
        assert s.step(L.peek('it_pack_lo', 1, 24)).data[0] == 16 - 8
        assert choose(s, 'TAKE', 'DOWN PARKA') == ('TAKE DOWN PARKA', 2)
        assert s.step(L.peek('it_place', 1, 2)).data[0] == 3 and 'HAND: DOWN PARKA' in result_rows(screen(s))[0]
        assert choose(s, 'CLIMB', 'TREE') == ('CLIMB TREE', 0)
        final = snapshot(s)
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('nature_frequency', 0))
        s.step('key:GET SOCKS')          # the typed equivalent needs the item's own word
        s.step(L.poke('menu_noun', 18))
        s.step(f'press:{RET}')
        s.step('wait:1')
        s.step(IDLE)
        typed(s, 'WALK 20 MIN')
        assert (s.step(L.peek('px', 2)).data, s.step(L.peek('s_elap', 5)).data) == menu
        typed(s, 'LOOK R')
        assert s.step(L.peek('heading', 2)).data == heading
        for text in ('REST 10 MIN', 'DRINK WATER 4 OZ', 'EAT EGGS 8 OZ', 'TAKE DOWN PARKA'):
            typed(s, text)
        assert s.step(L.peek('it_pack_lo', 1, 22)).data[0] == water
        typed(s, 'CLIMB TREE')
        assert snapshot(s) == final, 'menu and keyboard reach the same state'
    print('  WALK, LOOK, REST, DRINK, EAT, TAKE, GET, CLIMB composed from the grid = typed: OK')


def contexts(disk):
    with a2test.Session(disk) as s:
        s.step(IDLE)
        s.step(L.poke('shelter_inside', 1))
        typed(s, 'V')
        assert grid_cells(s)[0][:2] == ['EXIT', 'WALK'], grid_cells(s)
        s.step(L.poke('shelter_inside', 0))
        x, y = (s.step(L.peek(n, 1, 1)).data[0] for n in ('px', 'py'))
        for name, value in (('animal_kind', 6), ('animal_x', x), ('animal_y', y)):
            s.step(L.poke(name, value))
        typed(s, 'V')
        assert grid_cells(s)[0][:4] == ['IGNORE', 'SCARE', 'ATTACK', 'WALK'], grid_cells(s)
        s.step(L.poke('animal_kind', 0))
        typed(s, 'V')
        assert grid_cells(s)[0][0] == 'WALK'
        # Lists: ESC goes back to the verbs, a letter to the typed line.
        press(s, RET)
        move_to(s, 'EAT')
        press(s, RET)
        assert grid_cells(s)[0][0] == 'EGGS' and bottom(s)[3].startswith('> EAT'), bottom(s)
        press(s, ESC)
        assert selected(s) == 'EAT' and bottom(s)[3].startswith('>  ')
        press(s, 'L')
        assert selected(s) is None and bottom(s)[3].startswith('> L'), 'a letter types'
        press(s, ESC)
        assert bottom(s)[3].startswith('>  ')
        # An empty list (no medicine left) offers nothing; ESC leaves it.
        for item in range(41, 52):
            s.step(L.poke('it_place', 255, item))
        press(s, RET)
        move_to(s, 'USE')
        press(s, RET)
        assert not any(grid_cells(s)) and selected(s) is None
        press(s, RET, RIGHT, DOWN)
        assert not any(grid_cells(s))
        press(s, ESC)
        assert selected(s) == 'USE'
        # DOWN on the typed line shows STATUS; the numeric prompt keeps row 23.
        press(s, ESC)
        s.step(f'key:{DOWN}')
        s.step(L.until('status_key', 20000))
        assert screen(s)[0].startswith('STATUS:')
        s.step(f'key:{ESC}')
        s.step(IDLE)
        assert grid_cells(s)[0] == BASE[:6], 'the grid is back after a screen'
        s.step('key:WALK')
        s.step(f'press:{RET}')
        s.step(L.until('input_number_idle', 20000))
        rows = bottom(s)
        assert rows[3].startswith('> ') and 'NUMBER THEN RET' in rows[3][40:], rows[3]
        assert 'DURATION?' in result_rows(rows)[0]
        s.step(f'key:{ESC}')
        s.step(IDLE)
        assert 'ACTION CANCELLED.' in result_rows(screen(s))[0]
    print('  contextual verbs, ESC and letters from a list, empty list, DOWN = STATUS, numeric prompt: OK')


def main():
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, flat())
        layout(disk)
        composition(disk)
        contexts(disk)
    print('Neowilderness menu bar (lot 8 step 2): OK')


if __name__ == '__main__':
    main()
