#!/usr/bin/env python3
"""Save through real DOS, reboot exported disks, and resume three profiles."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
import dos33
from check_generation import neighbours

L = a2test.labels(ROOT / 'maze3d/build/maze3d.lbl')
DISK = ROOT / 'dist/MAZE3D.dsk'
FIELDS = ('p_col', 'p_row', 'p_face', 'p_hp', 'p_atk', 'p_def', 'p_lvl',
          'p_xp', 'p_gold', 'xp_next', 'p_floor', 'p_relic', 'p_potions',
          'p_chests', 'p_turns', 'p_turns_hi', 'old_col', 'old_row', 'p_guard', 'p_focus',
          'mob_phase', 'p_seed_lo', 'p_seed_hi', 'gstate', 'cur_mob')
DUMPS = ['peek:1000:77', 'peek:10a0:32', 'peek:0056:2'] + [L.peek(f) for f in FIELDS]


def keys(text, delay=25):
    return a2test.keys(text, delay)


def run(disk, steps, emulator=a2test.A2RUN, wp=False):
    return a2test.run(disk, ['wait:2200', *steps], emulator=emulator, wp=wp)


def snapshot(r):
    return (r.mem(0x1000, 77), r.mem(0x10a0, 32), r.mem(0x56, 2),
            tuple(r.mem(L[f], 1)[0] for f in FIELDS))


def save_manually():
    return [*keys("\x1bW"), "wait:700", *keys("R")]


def main():
    with tempfile.TemporaryDirectory(prefix='maze3d-profiles-') as tmp:
        work = Path(tmp)
        start = [*keys('SBEEF\r'), 'wait:700']
        first = run(DISK, start + DUMPS)
        grid = list(first.mem(0x1000, 77))
        target = neighbours(grid, 0)[0]
        movement = 'I' if target == 1 else 'LI'
        # Starting, moving, waiting and quitting must not write a checkpoint.
        unsaved_disk = work / 'unsaved.dsk'
        run(DISK, [*start, *keys(movement), 'wait:700', *keys('\x1b'), 'press:Q',
                   L.until('apple2_exit'), f'dsk:{unsaved_disk}'])
        assert dos33.read_file(unsaved_disk.read_bytes(), 'MAZESAVE1') == bytes(256)
        saved_disk = work / 'saved.dsk'
        played = run(DISK, [*start, L.poke('p_turns', 255), *keys(movement), 'wait:700',
                            L.poke('prng_lo', 0xcc), L.poke('prng_hi', 0), *keys('L'),
                            *save_manually(), *DUMPS,
                           L.peek('save_available'), f'dsk:{saved_disk}'])
        assert played.mem(L['p_turns'], 1) == b'\0'
        assert played.mem(L['p_turns_hi'], 1) == b'\1'
        assert played.mem(L['prng_lo'], 2) != bytes(2), 'turning produced an invalid checkpoint RNG'
        state1 = snapshot(played)
        assert played.mem(L['save_available'], 1) == b'\1'
        stored = dos33.read_file(saved_disk.read_bytes(), 'MAZESAVE1')
        assert stored[77:81] == b'MZS\1' and len(stored) == 256
        assert stored[:77] == state1[0]
        assert not any(dos33.read_file(saved_disk.read_bytes(), 'MAZESAVE2'))
        unchanged_disk = work / 'unchanged.dsk'
        run(saved_disk, [*keys('C'), 'wait:700', *keys('L'), 'wait:700',
                         *keys('\x1b'), 'press:Q', L.until('apple2_exit'),
                         f'dsk:{unchanged_disk}'])
        assert dos33.read_file(unchanged_disk.read_bytes(), 'MAZESAVE1') == stored
        # A2SHOT boots the disk written by A2RUN: actual DOS interoperability.
        resumed = run(saved_disk, [L.peek('save_available'), *keys('C'), 'wait:700', *DUMPS],
                      emulator=a2test.A2SHOT)
        assert resumed.mem(L['save_available'], 1) == b'\1'
        assert snapshot(resumed) == state1, 'position/stats/RNG/monsters changed after reboot'
        # Legacy checkpoints could contain a zero RNG after a keyboard turn.
        legacy = bytearray(stored)
        rng = 0x51 + L['ev_dmg'] - L['p_col'] + 1
        legacy[0x9f] ^= legacy[rng] ^ legacy[rng + 1]
        legacy[rng:rng + 2] = bytes(2)
        image = bytearray(saved_disk.read_bytes())
        dos33.replace_file(image, 'MAZESAVE1', legacy)
        legacy_disk = work / 'legacy-zero.dsk'
        legacy_disk.write_bytes(image)
        recovered = run(legacy_disk, [*keys('C'), 'wait:700', *DUMPS, L.peek('active_game')])
        assert recovered.mem(L['active_game'], 1) == b'\1'
        assert snapshot(recovered) == state1
        # A missing slot must not inherit the previously loaded checkpoint.
        image = saved_disk.read_bytes()
        name = bytes(c | 0x80 for c in b'MAZESAVE2') + b'\xa0' * 21
        assert image.count(name) == 1
        missing = work / 'missing-slot.dsk'
        missing.write_bytes(image.replace(name, b'\xd8' + name[1:]))
        switched = run(missing, [*keys('2'), 'wait:700', *keys('C'),
                                 L.peek('active_profile'), L.peek('save_available'),
                                 L.peek('active_game')], emulator=a2test.A2SHOT)
        assert switched.mem(L['active_profile'], 1) == b'\2'
        assert switched.mem(L['save_available'], 1) == b'\0', 'missing slot inherited a checkpoint'
        assert switched.mem(L['active_game'], 1) == b'\0'
        # A zero-length binary reads successfully but contains no checkpoint.
        short_image = bytearray(image)
        sector = dos33.file_sectors(short_image, 'MAZESAVE2')[0]
        short_image[sector + 2:sector + 4] = bytes(2)
        short = work / 'short-slot.dsk'
        short.write_bytes(short_image)
        switched = run(short, [*keys('2'), 'wait:700', *keys('C'),
                               L.peek('save_available'), L.peek('active_game')])
        assert switched.mem(L['save_available'], 1) == b'\0'
        assert switched.mem(L['active_game'], 1) == b'\0'
        # Enter a real fight and guard before saving: resuming must not reset
        # the player's focus or the orc's announced heavy attack.
        combat_disk = work / 'combat.dsk'
        combat_setup = [f'poke:{0x10b0+i:04x}:ff' for i in range(8)]
        combat_setup += [f'poke:10a0:{target % 11:02x}',
                         f'poke:10a8:{target // 11:02x}',
                         'poke:10b0:01', 'poke:10b8:1e']
        fighting = run(DISK, [*start, *combat_setup, *keys(movement),
                              *keys('G'), 'wait:700', *save_manually(), *DUMPS, f'dsk:{combat_disk}'])
        assert fighting.mem(L['gstate'], 1) == b'\4'
        assert fighting.mem(L['p_focus'], 1) == b'\2'
        assert fighting.mem(L['mob_phase'], 1) == b'\1'
        combat_resumed = run(combat_disk, [*keys('C'), 'wait:700', *DUMPS])
        assert snapshot(combat_resumed) == snapshot(fighting), 'combat state reset on resume'
        configured_disk = work / 'configured.dsk'
        run(saved_disk, [*keys('\x1bSD'), 'press:Q', L.until('apple2_exit'), f'dsk:{configured_disk}'])
        configured = run(configured_disk, [L.peek('sound_enabled'),
                                           L.peek('configured_depth'), *keys('C'),
                                           'wait:700', *DUMPS])
        assert configured.mem(L['sound_enabled'], 1) == b'\0'
        assert configured.mem(L['configured_depth'], 1) == b'\4'
        assert snapshot(configured) == state1
        # Profile 2 has a different dungeon; changing it must preserve profile 1.
        second_disk = work / 'second.dsk'
        second = run(saved_disk, [*keys('2'), 'wait:700', *keys('SCAFE\r'), 'wait:700',
                                  *save_manually(), *DUMPS, f'dsk:{second_disk}'])
        state2 = snapshot(second)
        assert state2 != state1
        assert dos33.read_file(second_disk.read_bytes(), 'MAZESAVE1') == stored
        remembered = run(second_disk, [L.peek('active_profile'), *keys('C'), 'wait:700', *DUMPS])
        assert remembered.mem(L['active_profile'], 1) == b'\2'
        assert snapshot(remembered) == state2
        again = run(second_disk, [*keys('1'), 'wait:700', *keys('C'), 'wait:700', *DUMPS])
        assert snapshot(again) == state1
        empty = run(second_disk, [*keys('3'), 'wait:700', *keys('C'),
                                  L.peek('save_available'), L.peek('active_game')])
        assert empty.mem(L['save_available'], 1) == b'\0'
        assert empty.mem(L['active_game'], 1) == b'\0'
        # Invalid checksum is rejected instead of resuming damaged state.
        image = bytearray(saved_disk.read_bytes())
        broken = bytearray(stored)
        broken[0] ^= 2
        dos33.replace_file(image, 'MAZESAVE1', broken)
        corrupt = work / 'corrupt.dsk'
        corrupt.write_bytes(image)
        rejected = run(corrupt, [L.peek('save_available')])
        assert rejected.mem(L['save_available'], 1) == b'\0'
        protected = run(DISK, start + save_manually() + [L.peek('save_available'), L.peek('active_game')], wp=True)
        assert protected.mem(L['save_available'], 1) == b'\0'
        assert protected.mem(L['active_game'], 1) == b'\1'
    print('profiles: no idle/quit autosave, manual save, full reboot/resume including combat, independent slots, remembered selection, corrupt/WP disks')


if __name__ == '__main__':
    main()
