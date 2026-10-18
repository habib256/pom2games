#!/usr/bin/env python3
"""MouseText page hierarchy, folded details, roles and catalogue at the game port."""
import tempfile
from common import L, disk_with, postit_errors, TAB_ROW
from test_forest import map_fixture
from test_fit_quantities import boot
from test_joystick_journey import GamePortSession, event, byte, rows, saved_state, equipment_item, action, IDLE
from test_save import differing, DERIVED_BYTES
from test_craft_followup import setup, open_recipe


def frame(s, page):
    assert rows(s)[0] == TAB_ROW
    mem = s.step('peek:0400:1024').data
    assert not postit_errors(mem, page), postit_errors(mem, page)


def readonly(before, s):
    assert not differing(before, saved_state(s), DERIVED_BYTES | {L['ui_dirty']}), differing(before, saved_state(s), DERIVED_BYTES | {L['ui_dirty']})


def main():
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, map_fixture())
        with GamePortSession(disk, menu=False) as s:
            boot(s); event(s, 'up'); frame(s, 'STATUS')
            page = rows(s)
            for row, name in ((3,'HEALTH'),(4,'ENERGY'),(5,'MEAL'),(6,'WATER'),(7,'BODY')):
                assert name in page[row][:40]
            assert 'BROKEN ARM' not in '\n'.join(page)
            assert 'SUNBURN' in '\n'.join(page) and '◆' in page[16]
            assert '0%' not in '\n'.join(page[16:21])
            before = saved_state(s)
            for focus in range(1, 6):
                event(s, 'down')
                assert byte(s, 'pg_focus') == focus
                readonly(before, s)
            event(s, 'down'); assert 'ALL CONDITIONS' in rows(s)[23]
            assert byte(s, 'pg_focus') == 6
            event(s, 'ok'); frame(s, 'STATUS')
            assert byte(s, 'st_all') == 1 and byte(s, 'st_med_n') == 14
            assert 'BROKEN ARM' in '\n'.join(rows(s)) and 'ALTITUDE SICKNESS' in '\n'.join(rows(s))
            event(s, 'ok'); assert byte(s, 'st_all') == 0
            event(s, 'up'); event(s, 'cancel', IDLE); readonly(before, s)
            print('  STATUS: compact unambiguous gauges, useful care only, full catalogue and readonly cancel: OK', flush=True)
        with GamePortSession(disk, menu=False) as s:
            boot(s); event(s, 'up'); event(s, 'right'); frame(s, 'OBJECTS')
            page = rows(s)
            assert 'MORE' not in page[15]
            assert '/' in page[15][:40] and '/' in page[15][41:]
            assert 'PACK ' in page[19] and 'HANDS ' in page[19]
            event(s, 'right'); frame(s, 'EQUIPMENT')
            event(s, 'ok'); before = saved_state(s)
            for role in range(4):
                assert byte(s, 'eq_view') == role
                frame(s, 'EQUIPMENT')
                entries = s.step(L.peek('overlay_text', byte(s, 'eq_n'))).data
                if role != 2:
                    for item in entries:
                        place = byte(s, 'it_place', item) if item < 89 else byte(s,'cr_b1',item-89)
                        assert place == (1,3,None,2)[role], (role,item,place)
                if role == 2:
                    assert not entries and 'NO ITEM IN THIS ROLE' in '\n'.join(rows(s))
                    event(s,'ok'); assert byte(s,'pg_cur') == 2  # empty role never acts on stale data
                event(s, 'right'); readonly(before, s)
            equipment_item(s, 59); action(s, 1)
            assert byte(s, 'eq_view') == 1 and byte(s,'eq_selected') == 59
            assert 'LOCATION: HANDS' in rows(s)[5] and 'ACTIVE: NO' in rows(s)[7]
            action(s,4)
            assert byte(s,'care_tools') & 2 and 'ACTIVE: YES' in rows(s)[7]
            before=saved_state(s); event(s,'right')
            assert byte(s,'eq_view') == 2
            assert 59 in s.step(L.peek('overlay_text',byte(s,'eq_n'))).data
            event(s,'cancel',IDLE); readonly(before,s)
            print('  OBJECTS: range counters and load retained; EQUIPMENT: four roles, empty role, actual actions, selection follows item: OK',flush=True)
        with GamePortSession(disk, menu=False) as s:
            boot(s);event(s,'up')
            for _ in range(4): event(s,'right')
            assert byte(s,'pg_cur') == 4;frame(s,'HELP')
            before=saved_state(s)
            for topic,title in enumerate(('MOVEMENT','OBJECTS & GEAR','FOOD, WATER & CARE','SAVE & LEAVE'),1):
                event(s,'down');frame(s,'HELP')
                assert byte(s,'pg_focus') == topic and title in rows(s)[2][30:]
                assert all(row[30] in ('▏',' ','‾') for row in rows(s)[3:22])
                readonly(before,s)
            event(s,'cancel',IDLE); readonly(before,s)
            print('  HELP: four topics, one body at a time, clean frames and readonly browsing: OK',flush=True)
        with GamePortSession(disk, menu=False) as s:
            setup(s,90);open_recipe(s,4);frame(s,'CRAFT')
            assert 'FACTORS:' not in '\n'.join(rows(s)) and 'SLOWER:' not in '\n'.join(rows(s))
            assert 'READY TO MAKE' in '\n'.join(rows(s))
            before=saved_state(s);summary=rows(s)
            event(s,'right');assert 'FACTORS:' in '\n'.join(rows(s))
            event(s,'left');assert rows(s) == summary
            event(s,'cancel',IDLE);readonly(before,s)
            print('  CRAFT: summary, right details, left exact summary, no simulation during browsing: OK',flush=True)
        with GamePortSession(disk,menu=False) as s:
            boot(s);event(s,'up')
            for _ in range(5):event(s,'right')
            frame(s,'OPTIONS'); before=saved_state(s)
            assert 'WILDLIFE FREQUENCY' in rows(s)[3] and 'C  WILDLIFE' not in rows(s)[3]
            event(s,'down');assert 'HOW OFTEN' in rows(s)[9]
            event(s,'up');event(s,'right');frame(s,'MENU')
            assert 'SAVE' in rows(s)[7] and 'RESTORE' in rows(s)[8] and 'QUIT' in rows(s)[9]
            event(s,'cancel',IDLE); readonly(before,s)
            print('  OPTIONS: compact list with contextual help; MENU: objective and one action list; cancel readonly: OK',flush=True)
    print('Readable MouseText pages: OK')


if __name__ == '__main__':
    main()
