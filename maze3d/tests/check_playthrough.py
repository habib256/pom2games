#!/usr/bin/env python3
"""Complete three floors and persist a record using keyboard input only."""
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
import dos33

# BEEF: collect eight caches, buy supplies, use guard/potions, slay dragon.
KEYS = 'SBEEF\rIIIIIILIIJIJIILIIILILIIJIJIILILIJIIJILILIIIIILIIJIIJILILLIJILIILIIJIIIIIHPCLIIJIILILIILLIIIILILLILILIJIILIIJIIIJIIJIILIIIIJIIDCIILIJIJILIILIJIAAAAAAGPGAGAIIIJILILIIIILILIJIIJIJILILIJILIIILIAGAGPGAGAGPGALLIJIIIJILILIJII'


def main():
    labels = a2test.labels(ROOT / 'maze3d/build/maze3d.lbl')
    steps = ['wait:2200']
    for i, key in enumerate(KEYS):
        steps += ['key:' + key, 'wait:25']
        if i == 5:  # Seed accepted: allow the deferred text disk read to finish.
            steps += ['wait:700']
    # The final move saves the best score through DOS before displaying victory.
    steps += ['wait:700', labels.peek('gstate'), labels.peek('p_floor'),
              labels.peek('p_hp'), labels.peek('p_chests'), labels.peek('mob_type', 1, 7)]
    with tempfile.TemporaryDirectory(prefix='maze3d-victory-') as tmp:
        disk = Path(tmp) / 'won.dsk'
        r = a2test.run(ROOT / 'dist/MAZE3D.dsk', steps + ['dsk:' + str(disk)],
                       emulator=a2test.A2RUN)
        assert r.mem(labels['gstate'], 1) == b'\5'
        assert r.mem(labels['p_floor'], 1) == b'\3'
        assert r.mem(labels['p_hp'], 1)[0] > 0
        assert r.mem(labels['p_chests'], 1) == b'\x08'
        assert r.mem(labels['mob_type'] + 7, 1) == b'\xff'
        record = dos33.read_file(disk.read_bytes(), 'MAZESCORE')
        assert record[:4] == b'MZ3\1' and record[4] == 163
        assert record[5:7] == bytes.fromhex('efbe')
        assert record[7] == record[4] ^ record[5] ^ record[6] ^ 0xa5
        # Enter the final stairs exactly at a low-byte carry and at saturation.
        stairs = [*a2test.keys('SBEEF\r', 25), 'wait:700', labels.poke('p_floor', 3),
                  labels.poke('p_relic', 1), labels.poke('p_col', 9), labels.poke('p_row', 6),
                  labels.poke('grid', 2, 75), labels.poke('mob_type', 255, 7),
                  labels.poke('p_turns', 255)]
        for high, expected in ((0, 41), (3, 0)):
            a2test.run(ROOT / 'dist/MAZE3D.dsk',
                       ['wait:2200', *stairs, labels.poke('p_turns_hi', high),
                        *a2test.keys('I', 25), 'wait:700', f'dsk:{disk}'],
                       emulator=a2test.A2RUN)
            record = dos33.read_file(disk.read_bytes(), 'MAZESCORE')
            assert record[4:7] == bytes((expected, 0xef, 0xbe))
        replay = a2test.run(disk, ['wait:2200', *a2test.keys('R', 25), 'wait:700',
                                   labels.peek('p_seed_lo', 2)], emulator=a2test.A2RUN)
        assert replay.mem(labels['p_seed_lo'], 2) == bytes.fromhex('efbe')
        # The completed zero-score run is still the disk record if a later
        # victory cannot write its higher score.
        protected = a2test.run(disk, ['wait:2200', *stairs, *a2test.keys('I', 25),
                                      'wait:700', labels.peek('score_run'), 'peek:1f00:8'],
                               emulator=a2test.A2RUN, wp=True)
        assert protected.mem(labels['score_run'], 1) == bytes([41])
        assert protected.mem(0x1f00, 8) == record
    print('playthrough: three floors, eight caches, shops, dragon, victory and persisted score 163')


if __name__ == '__main__':
    main()
