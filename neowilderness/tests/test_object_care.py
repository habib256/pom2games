#!/usr/bin/env python3
"""Object medical uses and whole-pack recovery through direction-only dialogs."""
import tempfile
from common import L, DISK, a2test, disk_with, fp
from test_forest import map_fixture
from test_objects import go, rows, state, open_page
from test_object_actions import key, command, select, confirm, IDLE


def byte(s, name, i=0):
    return s.step(L.peek(name, 1, i)).data[0]


def action(s, number):
    for _ in range(8):
        if byte(s, 'om_action') == number:
            return
        key(s, '\\v')
    raise AssertionError(('missing action', number, rows(s)[20:]))


def medicine():
    for item, verb, minutes in ((47, 5, 0), (48, 5, 0), (50, 5, 0), (49, 4, 15), (41, 4, 30)):
        with a2test.Session(DISK) as s:
            s.step(IDLE)
            s.step(L.poke('it_place', 2, item))
            s.step(L.poke('it_pack_lo', 2, item))
            s.step(L.poke('it_pack_hi', 0, item))
            select(s, 1, item)
            before = state(s)
            action(s, verb)
            line = rows(s)[21]
            assert 'QTY 1 USE; DOSES LEFT 2' in line, line
            assert f'/ {minutes} MIN' in line, line
            assert state(s) == before
            key(s, '\\r')
            assert byte(s, 'om_phase') == 2  # no ounce/ALL spinner for medicines
            key(s, '\\e'); key(s, '\\e')
            assert state(s) == before
            elapsed = fp(s.step(L.peek('s_elap', 5)).data)
            key(s, '\\r'); action(s, verb); confirm(s)
            assert abs(fp(s.step(L.peek('s_elap', 5)).data) - elapsed - minutes/60) < 1e-6
            assert byte(s, 'it_pack_lo', item) == 1
            assert byte(s, 'pg_cur') == 1 and byte(s, 'pg_focus') == 1
            assert byte(s, 'obj_selected', 1) == item
    print('  Oral doses, oxygen and first-aid: single use, stock/time shown, cancel atomic, same selection: OK')


def hung():
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        with a2test.Session(disk) as s:
            s.step(IDLE)
            s.step(L.poke('it_place', 2, 47))
            command(s, 'HANG FOOD')
            assert byte(s, 'it_place', 21) == 5
            before = state(s)
            elapsed = s.step(L.peek('s_elap', 5)).data
            open_page(s)
            assert go(s, 0, 28)  # independent ground CHEESE remains a normal object
            key(s, '\\r')
            assert byte(s, 'om_mask') != 16
            key(s, '\\e')
            assert go(s, 0, 21)  # then move into the hung section
            key(s, '\\v'); key(s, '\\v')  # EGGS, then the other CHEESE occurrence
            key(s, '\\r')
            assert rows(s)[20].startswith('ACTION: LOWER FOOD')
            key(s, '\\e')
            select(s, 0, 47)  # a medicine in LOCAL HUNG, rather than the bag itself
            assert byte(s, 'om_action') == 4 and byte(s, 'om_mask') == 16
            assert rows(s)[20].startswith('ACTION: LOWER FOOD'), rows(s)[20]
            assert 'ALL CONTENTS; 0 MIN; PACK NEED' in rows(s)[21], rows(s)[21]
            key(s, '\\r'); key(s, '\\e'); key(s, '\\e')
            assert state(s) == before
            s.step(L.poke('load_limits', 0))
            s.step(L.poke('load_limits', 0, 1))
            key(s, '\\r'); confirm(s)
            assert byte(s, 'it_place', 21) == 5
            assert s.step(L.peek('s_elap', 5)).data == elapsed
            assert 'LOAD CAPACITY' in ' '.join(rows(s)[20:23]), rows(s)[20:23]
            s.step(L.poke('load_limits', 815 & 255))
            s.step(L.poke('load_limits', 815 >> 8, 1))
            key(s, '\\r'); confirm(s)
            assert byte(s, 'it_place', 21) != 5 and byte(s, 'it_place', 25) != 5 and byte(s, 'it_place', 47) != 5
            assert s.step(L.peek('s_elap', 5)).data == elapsed
            assert byte(s, 'pg_cur') == 1 and byte(s, 'pg_focus') == 1
            assert 'RECOVERED' in ' '.join(rows(s)[20:23])
    print('  LOCAL HUNG: confirmation retrieves whole bag, cancellation atomic, native zero time, returns OBJECTS: OK')


if __name__ == '__main__':
    medicine()
    hung()
