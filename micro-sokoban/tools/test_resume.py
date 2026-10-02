#!/usr/bin/env python3
"""Reboot real disk images: positions, isolation, corruption and sector writes."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
from test_score import file_sectors, read_file, replace_file

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', type=Path, default=ROOT / 'dev/tools/a2run/a2run')
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/MICRO-SOKOBAN.dsk')
    args = ap.parse_args()
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', (GAME / 'build/micro_sokoban.lbl').read_text(), re.M)}
    def peek(name, count):
        return f'peek:{labels[name]:04X}:{count}'
    state = [peek('STATE_GRID', 240), peek('player_row', 2), peek('moves_lo', 5)]
    def run(disk, steps, wp=False):
        result = subprocess.run([str(args.a2run), '--disk', str(disk), *(['--wp'] if wp else []), *steps],
                                check=True, text=True, capture_output=True, timeout=30)
        return b''.join(bytes.fromhex(row) for row in re.findall(r'^[0-9A-F]{4}: (.+)$', result.stdout, re.M))
    base = args.disk.read_bytes()
    start = ['wait:1800', 'key:G', 'wait:90', 'key:\r', 'wait:180']
    solution = next(row.split()[3] for row in (GAME / 'levels/solutions.txt').read_text().splitlines()
                    if row.startswith('I 1 '))
    keys = ''.join(dict(u='I', d='K', l='J', r='L')[c] for c in solution.lower())
    with tempfile.TemporaryDirectory(prefix='micro-resume-') as tmp:
        tmp = Path(tmp)
        saved = tmp / 'saved.dsk'
        before = run(args.disk, start + ['key:' + keys[:12], 'key:U', 'wait:30', *state,
                                        'key:\x1b', 'wait:180', 'dsk:' + str(saved)])
        assert len(before) == 247 and int.from_bytes(before[242:244], 'little') == 11
        resumed = run(saved, ['wait:1800', 'key: ', 'wait:180', *state, peek('undo_n_lo', 4)])
        assert resumed == before + bytes(4), 'board, player, counters and fresh Undo after reboot'
        print('Exact position, moves and pushes restored after reboot; Undo history starts fresh: ok')
        changed = {i for i in range(0, len(base), 256) if base[i:i+256] != saved.read_bytes()[i:i+256]}
        assert changed == {file_sectors(base, 'MICROSAVE')[7]}, changed
        print('A position checkpoint changes exactly one data sector, without catalog/VTOC writes: ok')

        idle = tmp / 'idle.dsk'
        idle_state = run(args.disk, start + ['key:' + keys[:12], 'wait:600', *state, 'dsk:' + str(idle)])
        assert run(idle, ['wait:1800', 'key: ', 'wait:180', *state]) == idle_state
        unchanged = tmp / 'unchanged.dsk'
        run(idle, ['wait:1800', 'key: ', 'wait:180', 'key:\x1b', 'wait:180',
                   'key:\x1b', 'wait:180', 'key:\x1b', 'wait:180', 'dsk:' + str(unchanged)])
        assert unchanged.read_bytes() == idle.read_bytes()
        print('Idle autosave and reopening the menu without changes: no redundant disk writes: ok')

        # Selecting the active profile must preserve the live Undo/Redo history.
        current = run(saved, ['wait:1800', 'key: ', 'wait:180', 'key:' + keys[11], 'wait:30',
                             *state, peek('undo_n_lo', 4), 'key:\x1b', 'wait:180', 'key:V', 'wait:180',
                             'key:\r', 'wait:180', 'key:\x1b', 'wait:60', *state, peek('undo_n_lo', 4)])
        assert current[:251] == current[251:]
        print('Selecting the active profile retains the live position and Undo history: ok')

        # A new profile has its own start position; switching back restores GIS.
        switched = run(saved, ['wait:1800', 'key: ', 'wait:180', 'key:\x1b', 'wait:180',
                              'key:V', 'wait:180', 'key:N', 'wait:180', 'key:ABC', 'key:\r', 'wait:180',
                              peek('moves_lo', 4), 'key:\x1b', 'wait:180', 'key:V', 'wait:180',
                              'key:I', 'key:\r', 'wait:180', *state])
        assert switched == bytes(4) + before
        print('Independent in-progress positions across profile switches: ok')

        # A damaged snapshot is ignored, without losing valid best records.
        for name, offset in [('checksum', 1830+20), ('fingerprint', 1830+4), ('version', 1831)]:
            image = bytearray(saved.read_bytes())
            payload = bytearray(read_file(image, 'MICROSAVE'))
            payload[offset] ^= 1
            replace_file(image, 'MICROSAVE', payload)
            path = tmp / (name + '.dsk')
            path.write_bytes(image)
            assert run(path, ['wait:1800', peek('resume_pending', 1)]) == bytes(1)
        print('Corrupt, obsolete and different-level snapshots are rejected: ok')

        protected = tmp / 'protected.dsk'
        run(args.disk, start + ['key:' + keys[:12], 'wait:600', 'key:\x1b', 'wait:180',
                               'dsk:' + str(protected)], wp=True)
        assert protected.read_bytes() == base
        print('Write-protected media remain byte-for-byte unchanged: ok')


if __name__ == '__main__':
    main()
