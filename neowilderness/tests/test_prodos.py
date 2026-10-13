#!/usr/bin/env python3
"""NEOWILD.SYSTEM and the return to ProDOS 8.

- A ][+ (64 KB, no auxiliary RAM) gets the message and returns to ProDOS.
- QUIT (and the end of a game) restores the system and runs NEOWILD.SYSTEM
  again: the start menu, no state kept (lot 7).
- Q in the menu and Ctrl-RESET leave in 40-column text with main banks and
  the ROM selected, the bitmap, RESET vector and zero page restored;
  ProDOS's launcher (Bitsy Bye 2.4.3) runs and /RAM is again a readable
  empty volume.
- The game can be launched again from the launcher.
- A /RAM holding files is erased only after Y; N returns to ProDOS.
"""
import common
from common import L, DISK, MENU_SKIP, a2test, text_screen

IDLE = L.until('idle', 20000)
SWITCHES = 'peek:C011:15'   # LCBNK2 LCRAM RAMRD RAMWRT CXROM ALTZP C3ROM 80STORE VBL TEXT MIXED PAGE2 HIRES ALTCHAR 80COL


def screen(result, occurrence=0):
    return '\n'.join(text_screen(result.mem(0x0400, 1024, occurrence)))


def main_banks(switches):
    lcram, ramrd, ramwrt, altzp, store80 = (switches[i] >> 7 for i in (1, 2, 3, 5, 7))
    text, mixed, hires, col80 = (switches[i] >> 7 for i in (9, 10, 12, 14))
    return (lcram, ramrd, ramwrt, altzp, store80, text, mixed, hires, col80) == (0, 0, 0, 0, 0, 1, 0, 0, 0)


def check_launcher(result, label, occurrence=0):
    text = screen(result, occurrence)
    assert 'BITSY' in text and '/NEOWILDERNESS' in text, (label, text)
    switches = result.mem(0xC011, 15, occurrence)
    assert main_banks(switches), (label, switches.hex())


def main():
    # The unwrapped runner: a ][+ on purpose (common.py routes .po to the //e).
    r = common._run(DISK, ['wait:1500', 'peek:0400:1024', 'key: ', 'wait:600', 'peek:0400:1024'],
                    emulator=a2test.A2SHOT)
    assert 'NEEDS AN APPLE //E' in screen(r), screen(r)
    assert 'BITSY' in screen(r, 1), screen(r, 1)
    print('  ][+: incompatible-machine message, then ProDOS launcher: OK')

    vector = L['reset_exit']
    menu = L.until('menu_key', 40000)
    # Lot 7 step 6: every ending runs NEOWILD.END; QUIT at once scores 0 (never
    # ranked, no name to type): one key at hof_key_wait returns to the menu.
    quit_steps = ['key:QUIT', 'key:\\r', 'wait:60', 'key:Y', L.until('hof_key_wait', 40000),
                  'key: ']
    after = ['peek:0400:1024', SWITCHES, 'peek:03F2:3']
    # QUIT during play: back to the start menu, NEOWILD.SYSTEM read again.
    # Turn first: the new game must start from the map's heading again.
    steps = (MENU_SKIP + [IDLE, L.peek('heading', 2), 'key:\\>', IDLE, L.peek('heading', 2)]
             + quit_steps + [menu, 'peek:0400:1024', SWITCHES, L.peek('mli_calls', 2),
                             'key:2\\r', IDLE, L.peek('heading', 2), L.peek('mem_ready')])
    r = a2test.run(DISK, steps, menu=False)
    first, turned = r.mem(L['heading'], 2, 0), r.mem(L['heading'], 2, 1)
    assert first != turned, 'the turn must change the heading'
    text = screen(r)
    assert 'CHOOSE A JOURNEY' in text and '2 SIERRA NEVADA' in text, text
    assert main_banks(r.mem(0xC011, 15)), r.mem(0xC011, 15).hex()
    calls = int.from_bytes(r.mem(L['mli_calls'], 2), 'little')
    assert 0 < calls < 40, ('the counters restart with the loader', calls)
    assert r.mem(L['heading'], 2, 2) == first, 'no state kept between two games'
    assert r.mem(L['mem_ready'], 1) == b'\x01'
    print(f'  QUIT: back to the start menu (fresh loader, {calls} MLI calls), '
          'new game from the start position: OK')

    # Q in the menu leaves to ProDOS as QUIT did before lot 7.
    r = a2test.run(DISK, [menu, 'key:Q', 'wait:900'] + after + ['key:\t', 'wait:300', 'peek:0400:1024'])
    check_launcher(r, 'Q')
    assert r.mem(0x03F2, 3) != bytes((vector & 255, vector >> 8, (vector >> 8) ^ 0xA5)), 'RESET vector'
    assert 'S3,D2:/RAM' in screen(r, 1), screen(r, 1)
    print('  Q in the menu: text, main banks, ROM, RESET vector restored; launcher; empty /RAM rebuilt: OK')

    # QUIT, then Q: the same cleanup after a game.
    r = a2test.run(DISK, MENU_SKIP + [IDLE] + quit_steps + [menu, 'key:Q', 'wait:900'] + after,
                   menu=False)
    check_launcher(r, 'QUIT then Q')
    print('  QUIT then Q: ProDOS launcher after a game: OK')

    r = a2test.run(DISK, [IDLE, 'reset', 'wait:900'] + after)
    check_launcher(r, 'RESET')
    print('  Ctrl-RESET during play: same cleanup and ProDOS launcher: OK')

    # Bitsy Bye lists DAT, END, HOF, R1..R6, then SYSTEM: nine down arrows.
    r = a2test.run(DISK, [menu, 'key:Q', 'wait:900', 'key:' + '\\v' * 9, 'key:\\r'] + MENU_SKIP
                   + [IDLE, L.peek('mem_ready'), L.peek('xfer_count', 2)], menu=False)
    assert r.mem(L['mem_ready'], 1) == b'\x01'
    print('  relaunch from the ProDOS launcher reaches the menu and the command line again: OK')

    files = L['loader_ram_files']
    for answer, playable in (('N', False), ('Y', True)):
        steps = [f'until:{files:04X}:6000', 'poke:2025:01', f'until:{L["ld_wait"]:04X}:100',
                 'peek:0400:1024', f'key:{answer}']
        steps += MENU_SKIP + [IDLE] if playable else ['wait:900', 'peek:0400:1024']
        r = a2test.run(DISK, steps)
        assert '/RAM HOLDS FILES' in screen(r), screen(r)
        if not playable:
            assert 'BITSY' in screen(r, 1), screen(r, 1)
    print('  /RAM with files: N returns to ProDOS untouched, Y erases it and plays: OK')


if __name__ == '__main__':
    main()
