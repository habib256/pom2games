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
    print('playthrough: three floors, eight caches, shops, dragon, victory and persisted score 163')


if __name__ == '__main__':
    main()
