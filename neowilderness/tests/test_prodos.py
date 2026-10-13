#!/usr/bin/env python3
"""NEOWILD.SYSTEM and the return to ProDOS 8.

- A ][+ (64 KB, no auxiliary RAM) gets the message and returns to ProDOS.
- QUIT and Ctrl-RESET leave in 40-column text with main banks and the ROM
  selected, the bitmap, RESET vector and zero page restored; ProDOS's
  launcher (Bitsy Bye 2.4.3) runs and /RAM is again a readable empty volume.
- The game can be launched again from the launcher.
- A /RAM holding files is erased only after Y; N returns to ProDOS.
- At the final MLI QUIT (after QUIT Y or Ctrl-RESET during play), the zero
  page, the ProDOS bitmap and the RESET vector are byte for byte those found
  at NEOWILD.SYSTEM's entry, and the memory switches are back to main RAM
  and the ROM; during play the bitmap marks the game pages.
"""
import common
from common import L, DISK, a2test, text_screen

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


# Pages the loader marks in the ProDOS bitmap for the game (docs/MEMORY.md):
# $08-$57, $60-$B9 and $BE; one bit per page, bit 7 = first page of a byte.
PAGES = set(range(0x08, 0x58)) | set(range(0x60, 0xBA)) | {0xBE}
GAME_PAGES = bytes(sum(0x80 >> k for k in range(8) if 8 * i + k in PAGES) for i in range(24))


def exit_state():
    """ProDOS state at the loader's entry, during play, and at the final QUIT."""
    quit_call = L['quit_parms'] - 6         # JSR mli_call ; JMP @halt ; quit_parms
    entry = ['until:%04X:6000' % L['loader_main'], 'peek:0000:256', 'peek:BF58:24', 'peek:03F2:3']
    final = [f'until:{quit_call:04X}:6000', 'peek:0000:256', 'peek:BF58:24', 'peek:03F2:3', SWITCHES]
    for name, leave in (('QUIT', ['key:QUIT', 'key:\\r', 'wait:60', 'press:Y']), ('RESET', ['reset'])):
        r = a2test.run(DISK, entry + [IDLE, 'peek:BF58:24', 'peek:03F2:3'] + leave + final)
        zp, bitmap, vector = r.dumps[0:3]
        assert r.dumps[3] == bytes(b | g for b, g in zip(bitmap, GAME_PAGES)), \
            ('game pages $08-$57, $60-$B9 and $BE marked during play', r.dumps[3].hex())
        assert r.dumps[4] == bytes((L['reset_exit'] & 255, L['reset_exit'] >> 8, (L['reset_exit'] >> 8) ^ 0xA5))
        assert r.dumps[5] == zp, (name, 'zero page', [i for i in range(256) if r.dumps[5][i] != zp[i]])
        assert r.dumps[6] == bitmap, (name, 'bitmap', r.dumps[6].hex(), bitmap.hex())
        assert r.dumps[7] == vector, (name, 'RESET vector')
        switches = r.dumps[8]
        lcram, ramrd, ramwrt, altzp, store80 = (switches[i] >> 7 for i in (1, 2, 3, 5, 7))
        assert (lcram, ramrd, ramwrt, altzp, store80) == (0, 0, 0, 0, 0), (name, switches.hex())
    print('  QUIT and Ctrl-RESET: zero page, bitmap and RESET vector equal to the loader entry at the MLI QUIT; '
          'main RAM, ROM; exactly the game pages marked during play: OK')


def main():
    # The unwrapped runner: a ][+ on purpose (common.py routes .po to the //e).
    r = common._run(DISK, ['wait:1500', 'peek:0400:1024', 'key: ', 'wait:600', 'peek:0400:1024'],
                    emulator=a2test.A2SHOT)
    assert 'NEEDS AN APPLE //E' in screen(r), screen(r)
    assert 'BITSY' in screen(r, 1), screen(r, 1)
    print('  ][+: incompatible-machine message, then ProDOS launcher: OK')

    vector = L['reset_exit']
    quit_steps = ['key:QUIT', 'key:\\r', 'wait:60', 'key:Y', 'wait:900']
    after = ['peek:0400:1024', SWITCHES, 'peek:03F2:3']
    r = a2test.run(DISK, [IDLE] + quit_steps + after + ['key:\t', 'wait:300', 'peek:0400:1024'])
    check_launcher(r, 'QUIT')
    assert r.mem(0x03F2, 3) != bytes((vector & 255, vector >> 8, (vector >> 8) ^ 0xA5)), 'RESET vector'
    assert 'S3,D2:/RAM' in screen(r, 1), screen(r, 1)
    print('  QUIT: text, main banks, ROM, RESET vector restored; launcher; empty /RAM rebuilt: OK')

    r = a2test.run(DISK, [IDLE, 'reset', 'wait:900'] + after)
    check_launcher(r, 'RESET')
    print('  Ctrl-RESET during play: same cleanup and ProDOS launcher: OK')

    r = a2test.run(DISK, [IDLE] + quit_steps + ['key:\\v', 'key:\\r', IDLE, L.peek('mem_ready'),
                                                L.peek('xfer_count', 2)])
    assert r.mem(L['mem_ready'], 1) == b'\x01'
    print('  relaunch from the ProDOS launcher reaches the command line again: OK')

    files = L['loader_ram_files']
    for answer, playable in (('N', False), ('Y', True)):
        steps = [f'until:{files:04X}:6000', 'poke:2025:01', f'until:{L["ld_wait"]:04X}:100',
                 'peek:0400:1024', f'key:{answer}']
        steps += [IDLE] if playable else ['wait:900', 'peek:0400:1024']
        r = a2test.run(DISK, steps)
        assert '/RAM HOLDS FILES' in screen(r), screen(r)
        if not playable:
            assert 'BITSY' in screen(r, 1), screen(r, 1)
    print('  /RAM with files: N returns to ProDOS untouched, Y erases it and plays: OK')
    exit_state()


if __name__ == '__main__':
    main()
