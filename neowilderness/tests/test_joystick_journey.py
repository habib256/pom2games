#!/usr/bin/env python3
"""XL integration journey: real game-port input, never keyboard events.

The forest and small-game encounter are deterministic fixtures. Crafting,
transfers, activation, hunting, meals, care, saves and scores use the UI.
"""
import tempfile
from common import L, a2test, disk_with, text_screen, fp
from test_forest import map_fixture
from test_objects import entry
from test_menu_bar import selected, grid_cells
from test_forage import seed_for
from test_save import RANGES, DERIVED_BYTES, differing
from score import Hof

IDLE = L.until('idle', 60000)
READY = L.until('keyboard_wait', 60000)


class GamePortSession(a2test.Session):
    def step(self, step):
        assert not step.startswith(('key:', 'press:')), 'Keyboard event in joystick journey'
        return super().step(step)


def byte(s, name, offset=0):
    return s.step(L.peek(name, 1, offset)).data[0]


def rows(s):
    return text_screen(s.step('peek:0400:1024').data)


def event(s, control, ready=READY):
    axes = {'up': '0,-1', 'down': '0,1', 'left': '-1,0', 'right': '1,0'}
    if control in axes:
        start, stop = 'joy:'+axes[control], 'joy:0,0'
    else:
        button = 0 if control == 'ok' else 1
        start, stop = f'btn:{button},1', f'btn:{button},0'
    s.step(start)
    s.step('wait:8')
    s.step(ready)
    s.step(stop)
    s.step('wait:6')


def object_item(s, side, item):
    if not byte(s, 'pg_focus'):
        event(s, 'ok')
    if byte(s, 'obj_side') != side:
        event(s, 'right' if side else 'left')
    entries = s.step(L.peek('overlay_text', byte(s, 'ob_n', side), byte(s, 'ob_at', side))).data
    assert item in entries, (item, entries, rows(s))
    target = entries.index(item)
    for _ in range(140):
        if entry(s, side) == item:
            return
        event(s, 'up' if byte(s, 'obj_cur', side) > target else 'down')
    raise AssertionError(('object missing', side, item, rows(s)))


def action(s, target):
    event(s, 'ok')
    for _ in range(8):
        if byte(s, 'om_action') == target:
            break
        event(s, 'down')
    assert byte(s, 'om_action') == target, rows(s)
    event(s, 'ok')
    if byte(s, 'om_phase') == 1:
        event(s, 'ok')
    event(s, 'ok')


def grid(s, *labels, ready=IDLE):
    if not byte(s, 'mn_mode'):
        event(s, 'ok', IDLE)
    for label in labels:
        for _ in range(60):
            if selected(s) == label:
                break
            event(s, 'right', IDLE)
        assert selected(s) == label, (label, grid_cells(s))
        event(s, 'ok', ready if label == labels[-1] else IDLE)


def saved_state(s):
    return b''.join(s.step(f'peek:{address:04X}:{size}').data for address, size in RANGES)


def menu_action(s, choice):
    """From the view, select SAVE=1, RESTORE=2 or QUIT=3 in MENU."""
    event(s, 'up')
    for _ in range(7):
        if byte(s, 'pg_cur') == 6:
            break
        event(s, 'left')
    assert byte(s, 'pg_cur') == 6 and byte(s, 'pg_focus') == 0
    for _ in range(choice):
        event(s, 'down')
    event(s, 'ok')


def slot(s, number, ready=IDLE):
    for _ in range(number):
        event(s, 'up')
    event(s, 'ok', ready)


def care_save_end(s):
    # Both drugs come from the ordinary starting equipment.
    for item, operation, minutes in ((47, 5, 0), (49, 4, 15)):
        side = int(byte(s, 'it_place', item) in (1, 2, 3, 4))
        object_item(s, side, item)
        doses = byte(s, 'it_pack_lo', item)
        elapsed = fp(s.step(L.peek('s_elap', 5)).data)
        before = saved_state(s)
        event(s, 'ok')
        for _ in range(8):
            if byte(s, 'om_action') == operation:
                break
            event(s, 'down')
        assert byte(s, 'om_action') == operation
        event(s, 'ok')
        assert byte(s, 'om_phase') == 2  # a dose has no quantity step
        event(s, 'cancel'); event(s, 'cancel')
        assert saved_state(s) == before
        action(s, operation)
        assert byte(s, 'it_pack_lo', item) == doses-1
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-elapsed-minutes/60) < .001
        assert byte(s, 'pg_cur') == 1 and byte(s, 'pg_focus') == 1
        assert byte(s, 'it_place', item) == 3  # native USE takes the remedy in hand
        assert entry(s, byte(s, 'obj_side')) is not None
    print('  Oral medicine and oxygen: cancel atomic, single dose and native duration: OK', flush=True)
    event(s, 'cancel', IDLE)

    before = saved_state(s)
    menu_action(s, 1)
    event(s, 'cancel', IDLE)
    assert not differing(before, saved_state(s), DERIVED_BYTES)
    menu_action(s, 2)
    slot(s, 3)
    assert 'GAME 3 IS EMPTY.' in '\n'.join(rows(s))
    assert not differing(before, saved_state(s), DERIVED_BYTES)
    menu_action(s, 2)
    event(s, 'cancel', IDLE)
    assert not differing(before, saved_state(s), DERIVED_BYTES)
    menu_action(s, 1)
    slot(s, 2)
    assert 'GAME 2 SAVED.' in '\n'.join(rows(s))
    saved = saved_state(s)

    event(s, 'up')
    while byte(s, 'pg_cur') != 1:
        event(s, 'left')
    object_item(s, 1, 59)
    action(s, 2)                       # drop the knife after saving
    assert byte(s, 'it_place', 59) == 0
    event(s, 'cancel', IDLE)
    changed = saved_state(s)
    assert differing(saved, changed, DERIVED_BYTES)
    menu_action(s, 1)
    slot(s, 2, READY)                  # occupied slot: safe default N
    event(s, 'ok', IDLE)
    assert 'GAME 2 KEPT. NOT SAVED.' in '\n'.join(rows(s))
    assert not differing(changed, saved_state(s), DERIVED_BYTES)
    menu_action(s, 2)
    slot(s, 2)
    assert 'GAME 2 RESTORED.' in '\n'.join(rows(s))
    assert not differing(saved, saved_state(s), DERIVED_BYTES)
    assert byte(s, 'it_place', 59) != 0
    print('  MENU: cancel SAVE, empty RESTORE, SAVE 2, overwrite kept, full state restored: OK', flush=True)

    before = saved_state(s)
    menu_action(s, 3)
    event(s, 'ok', IDLE)               # safe default N
    assert not differing(before, saved_state(s), DERIVED_BYTES)
    menu_action(s, 3)
    event(s, 'right')                  # yes
    end = L.until('hof_key_wait', 60000)
    event(s, 'ok', end)
    assert 'JOURNEY SCORE' in '\n'.join(rows(s))
    assert byte(s, 'hof_rank') == 5     # unmoved player: zero score is unranked
    event(s, 'ok', L.until('menu_key', 60000))
    assert 'CHOOSE A JOURNEY' in '\n'.join(rows(s))
    print('  QUIT cancel, confirm, score and return to start menu: OK', flush=True)

    event(s, 'ok', L.until('menu_key', 60000))
    event(s, 'ok', IDLE)
    menu_action(s, 2)
    slot(s, 2)
    assert 'GAME 2 RESTORED.' in '\n'.join(rows(s))
    assert not differing(saved, saved_state(s), DERIVED_BYTES)
    print('  Restart and RESTORE 2: full saved state recovered: OK', flush=True)
    before_walk = saved_state(s)
    position = s.step(L.peek('px', 4)).data
    grid(s, 'WALK', '1 H')
    assert 'DOUSE YOUR FIRE' in '\n'.join(rows(s))
    assert not differing(before_walk, saved_state(s), DERIVED_BYTES)
    grid(s, 'DOUSE')
    assert not byte(s, 'fire_on')
    grid(s, 'WALK', '1 H')
    assert s.step(L.peek('px', 4)).data != position
    menu_action(s, 3)
    event(s, 'right'); event(s, 'ok', end)
    assert byte(s, 'hof_rank') == 0, rows(s)
    assert byte(s, 'hof_progress') > 0
    score = byte(s, 'hof_total') + 256*byte(s, 'hof_total', 1)
    event(s, 'ok', end)                # empty name cannot submit the score
    assert byte(s, 'hof_len') == 0
    for control in ('up', 'right', 'up'):
        event(s, control, end)
    assert byte(s, 'hof_len') == 2
    name = s.step('peek:5870:8').data
    assert bytes(c & 127 for c in name) == b'AB      ', name
    event(s, 'ok', end)
    assert 'HALL OF FAME SAVED.' in '\n'.join(rows(s))
    event(s, 'ok', L.until('menu_key', 60000))
    assert 'CHOOSE A JOURNEY' in '\n'.join(rows(s))
    hof = Hof(s.step('peek:2000:512').data)
    assert hof.valid() and hof.scenario_games(2) == 2
    assert hof.entry(2, 0)['name'] == 'AB' and hof.entry(2, 0)['score'] == score
    print('  WALK, ranked score, joystick name AB, HOF saved and start menu: OK', flush=True)


def journey(disk):
    with GamePortSession(disk, menu=False) as s:
        menu = L.until('menu_key', 60000)
        s.step(menu)
        event(s, 'ok', menu)
        event(s, 'ok', IDLE)
        s.step(L.poke('nature_frequency', 0))
        event(s, 'up')
        event(s, 'right'); event(s, 'right'); event(s, 'right')
        assert byte(s, 'pg_cur') == 3
        for _ in range(5):
            event(s, 'down')
        event(s, 'ok', L.until('get_line', 100000))
        s.step(L.until('q_craft_wait', 100000))
        assert 'RETURN RECIPES' in rows(s)[23]
        event(s, 'cancel', IDLE)
        assert byte(s, 'cr_b1', 1) == 0, rows(s)
        print('  Joystick boot and CRAFT SPEAR: OK', flush=True)

        event(s, 'up'); event(s, 'left'); event(s, 'left')
        object_item(s, 0, 90)
        before = s.step(L.peek('s_elap', 5)).data
        action(s, 1)
        assert byte(s, 'cr_b1', 1) == 0
        assert s.step(L.peek('s_elap', 5)).data == before
        assert 'WEIGHT' in ' '.join(rows(s)[20:23]), rows(s)
        object_item(s, 1, 2)
        action(s, 2)
        object_item(s, 0, 90)
        action(s, 1)
        assert byte(s, 'cr_b1', 1) == 3, rows(s)
        assert not byte(s, 'fg_use') & 8
        print('  Capacity refusal, DROP PARKA, CARRY SPEAR without activation: OK', flush=True)

        event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'right')
        assert byte(s, 'pg_cur') == 2
        event(s, 'ok')
        for _ in range(140):
            if byte(s, 'overlay_text', byte(s, 'eq_cur')) == 90:
                break
            event(s, 'down')
        assert 'IN HANDS: YES' in rows(s)[6] and 'IN USE: NO' in rows(s)[7]
        action(s, 4)
        assert byte(s, 'fg_use') & 8
        assert 'IN USE: YES' in rows(s)[7]
        event(s, 'cancel', IDLE)
        print('  EQUIPMENT activates the held spear: OK', flush=True)

        # Fixed encounter; no simulated catch or inventory is injected.
        for slot in (4, 5):
            s.step(L.poke('fg_b2', 0 if slot == 4 else 255, slot))
        s.step(L.poke('resource_seen', 1))
        for axis in ('x', 'y'):
            s.step(L.poke('fg_'+axis, byte(s, 'p'+axis, 1)))
        event(s, 'right', IDLE); event(s, 'left', IDLE)
        seed = seed_for(.001, position=1)
        for i in range(4):
            s.step(L.poke('weather_seed', seed >> (8*i) & 255, i))
        assert not byte(s, 'fg_use') & 1  # an active spear does not prepare a trap
        grid(s, 'CATCH', '10 MIN')
        assert byte(s, 'mq_n') == 0
        assert byte(s, 'fg_use') & 1
        caught = byte(s, 'fg_gl', 4) + 256*byte(s, 'fg_gh', 4)
        assert caught > 0, rows(s)
        print(f'  CATCH with prerequisite queue: {caught} OZ: OK', flush=True)
        grid(s, 'MAKE', 'FIRE')
        assert byte(s, 'fire_on')
        print('  MAKE FIRE: OK', flush=True)
        grid(s, 'COOK', ready=READY)     # GAME is the only cookable pile here
        event(s, 'up')                  # one ounce
        event(s, 'ok')                  # native decimal-hour question
        before = tuple(s.step(L.peek(n, k)).data for n, k in
                       [('s_elap', 5), ('fg_gl', 12), ('fg_gh', 12), ('weather_seed', 4)])
        event(s, 'down')
        assert s.step(L.peek('fr_min', 2)).data == b'\0\0'
        for _ in range(30):
            event(s, 'up')              # thirty exact minutes
        event(s, 'down')
        assert s.step(L.peek('fr_min', 2)).data == b'\x1d\0'
        for _ in range(1499-29):
            event(s, 'up')
        event(s, 'up')
        assert int.from_bytes(s.step(L.peek('fr_min', 2)).data, 'little') == 1499
        event(s, 'down')
        assert int.from_bytes(s.step(L.peek('fr_min', 2)).data, 'little') == 1498
        event(s, 'cancel', IDLE)
        assert tuple(s.step(L.peek(n, k)).data for n, k in
                     [('s_elap', 5), ('fg_gl', 12), ('fg_gh', 12), ('weather_seed', 4)]) == before
        grid(s, 'COOK', ready=READY)
        event(s, 'up'); event(s, 'ok')
        for _ in range(30):
            event(s, 'up')
        assert s.step(L.peek('fr_min', 2)).data == b'\x1e\0'
        before_cook = fp(s.step(L.peek('s_elap', 5)).data)
        old_counter = byte(s, 'fg_cl', 15) + 256*byte(s, 'fg_ch', 15)
        event(s, 'ok', IDLE)
        assert byte(s, 'fg_cl', 15) + 256*byte(s, 'fg_ch', 15) > old_counter
        assert abs(fp(s.step(L.peek('s_elap', 5)).data)-before_cook-.5) < .001
        print('  Fire and COOK GAME: OK', flush=True)
        if byte(s, 'mn_mode'):
            event(s, 'cancel', IDLE)
        event(s, 'up'); event(s, 'left')
        assert byte(s, 'pg_cur') == 1
        object_item(s, 0, 80)
        action(s, 5)
        assert byte(s, 'fg_gl', 4) + 256*byte(s, 'fg_gh', 4) == caught-1
        print('  OBJECTS consumes one ounce of the cooked local game: OK', flush=True)
        care_save_end(s)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        journey(disk_with(tmp, map_fixture()))
    print('Joystick journey: OK')
