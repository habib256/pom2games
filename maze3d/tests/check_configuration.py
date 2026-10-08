#!/usr/bin/env python3
"""ESC pauses the title, seed editor, map, help, shop and combat safely."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test

L = a2test.labels(ROOT / 'maze3d/build/maze3d.lbl')
DISK = ROOT / 'dist/MAZE3D.dsk'


def keys(text):
    return [s for c in text for s in ('key:' + c, 'wait:30')]


def pause(prefix):
    steps = ['wait:2200', *prefix, L.peek('front_page'), 'peek:2000:16384',
             'peek:0056:2', L.peek('p_col', L['ev_dmg'] - L['p_col'] + 1),
             *keys('\x1b'), L.peek('quit_flag'), *keys('R'),
             L.peek('front_page'), 'peek:2000:16384', 'peek:0056:2',
             L.peek('p_col', L['ev_dmg'] - L['p_col'] + 1)]
    r = a2test.run(DISK, steps, emulator=a2test.A2RUN, wp=True)
    before = int(r.mem(L['front_page'], 1, 0)[0] != 0)
    after = int(r.mem(L['front_page'], 1, 1)[0] != 0)
    original = r.mem(0x2000, 16384, 0)[before * 8192:(before + 1) * 8192]
    restored = r.mem(0x2000, 16384, 1)[after * 8192:(after + 1) * 8192]
    assert a2test.hgr_visible(original) == a2test.hgr_visible(restored), 'resume did not restore the paused screen'
    assert r.mem(0x56, 2, 0) == r.mem(0x56, 2, 1), 'configuration changed RNG'
    length = L['ev_dmg'] - L['p_col'] + 1
    saved = bytearray(r.mem(L['p_col'], length, 0))
    resumed = bytearray(r.mem(L['p_col'], length, 1))
    # Rebuilding the HUD on both pages is permitted after modal UI.
    saved[L['hud_dirty'] - L['p_col']] = resumed[L['hud_dirty'] - L['p_col']]
    assert saved == resumed, 'configuration advanced the game or combat'
    assert r.mem(L['quit_flag'], 1) == b'\0'


def main():
    play = [*keys('SBEEF\r'), 'wait:700']
    pause([])
    pause(keys('S12'))
    pause(play)
    pause([*play, *keys('M')])
    pause([*play, *keys('H')])
    # Enter real combat and shop control paths; pause must retain their screens.
    combat = [*play, L.poke('gstate', 4), L.poke('cur_mob', 0),
              L.poke('prev_state', 2), *keys('L')]
    pause(combat)
    shop = [*play, L.poke('p_col', 9), L.poke('p_row', 6), L.poke('p_face', 1),
            L.poke('p_relic', 1), 'poke:104b:02', *keys('I')]
    pause(shop)
    settings = a2test.run(DISK, ['wait:2200', *keys('\x1b'), *keys('SDDDDR'),
                                 L.peek('configured_depth'), L.peek('sound_enabled')],
                         emulator=a2test.A2RUN, wp=True)
    assert settings.mem(L['configured_depth'], 1) == b'\x0a'
    assert settings.mem(L['sound_enabled'], 1) == b'\0'
    # Observe the intended DOS exit before the routine restores the game's ZP.
    quit_run = a2test.run(DISK, ['wait:2200', *play, *keys('\x1b'), 'press:Q',
                               L.until('apple2_exit'), L.peek('quit_flag')],
                         emulator=a2test.A2RUN, wp=True)
    assert quit_run.mem(L['quit_flag'], 1)[0] != 0
    print('configuration: ESC pauses seven contexts, resumes unchanged, sound/depth settings, Q exits to DOS')


if __name__ == '__main__':
    main()
