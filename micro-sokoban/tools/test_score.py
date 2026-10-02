#!/usr/bin/env python3
"""Exercise scoring, initials, ranking and disk persistence in the real game."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'


def file_sectors(image, name):
    """DOS 3.3 catalog -> ordered data sectors for a binary file."""
    def sector(t, s):
        return image[(t * 16 + s) * 256:(t * 16 + s + 1) * 256]
    t, s = 17, 15
    while t:
        cat = sector(t, s)
        for off in range(11, 256, 35):
            entry = cat[off:off + 35]
            if entry[0] in (0, 255):
                continue
            filename = ''.join(chr(c & 127) for c in entry[3:33]).rstrip()
            if filename == name:
                ts, ss = entry[:2]
                sectors = []
                while ts:
                    listing = sector(ts, ss)
                    sectors += [(listing[i] * 16 + listing[i + 1]) * 256
                                for i in range(12, 256, 2) if listing[i]]
                    ts, ss = listing[1:3]
                return sectors
        t, s = cat[1:3]
    raise AssertionError('file not found: ' + name)


def read_file(image, name):
    raw = b''.join(image[s:s + 256] for s in file_sectors(image, name))
    return raw[4:4 + int.from_bytes(raw[2:4], 'little')]


def replace_file(image, name, payload):
    sectors = file_sectors(image, name)
    old = b''.join(image[s:s + 256] for s in sectors)
    assert len(payload) == int.from_bytes(old[2:4], 'little')
    new = old[:4] + payload
    for i, off in enumerate(sectors):
        chunk = new[i * 256:(i + 1) * 256]
        image[off:off + len(chunk)] = chunk


def entries(buf):
    return [(buf[i:i + 3].decode('ascii'), int.from_bytes(buf[i + 3:i + 6], 'little') + ((buf[i+7] >> 7) << 24),
             int.from_bytes(buf[i + 6:i + 8], 'little') & 511)
            for i in range(7, 87, 8) if buf[i]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', default=ROOT / 'dev/tools/a2run/a2run', type=Path)
    ap.add_argument('--disk', default=ROOT / 'dist/MICRO-SOKOBAN.dsk', type=Path)
    args = ap.parse_args()
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', (GAME / 'build/micro_sokoban.lbl').read_text(), re.M)}
    base = args.disk.read_bytes()
    save = read_file(base, 'MICROSAVE')
    header = 14
    total = 454
    solutions = {int(row.split()[1]): row.split()[3] for row in
                 (GAME / 'levels/solutions.txt').read_text().splitlines()
                 if row.startswith('I ')}

    def peek(label, n=1):
        return f'peek:{labels[label]:04X}:{n}'

    def run(disk, steps, wp=False, silent=False):
        command = [str(args.a2run), '--disk', str(disk)] + (['--wp'] if wp else []) + steps
        result = subprocess.run(command, check=True, text=True, capture_output=True, timeout=30)
        if silent:
            assert re.findall(r'^spk (\d+)$', result.stdout, re.M)[-1] == '0', result.stdout
        return [bytes.fromhex(row) for row in
                re.findall(r'^[0-9A-F]{4}: (.+)$', result.stdout, re.M)]

    def fixture(path, records, hof=None):
        image = bytearray(base)
        payload = bytearray(save)
        for index, moves in records.items():
            payload[header + index * 4:header + index * 4 + 4] = moves.to_bytes(2, 'little') + bytes(2)
        replace_file(image, 'MICROSAVE', payload)
        if hof is not None:
            replace_file(image, 'MICROHOF', hof)
        path.write_bytes(image)

    def keys(level):
        return ''.join(dict(u='I', d='K', l='J', r='L')[c] for c in solutions[level].lower())

    with tempfile.TemporaryDirectory(prefix='micro-sokoban-profiles-') as temp:
        tmp = Path(temp)
        def create(name):
            return ['key:V', 'wait:180', 'key:N', 'wait:180', 'key:' + name,
                    'key:\r', 'wait:600']
        def solve(level):
            return ['key:' + keys(level), 'wait:600']
        saved = tmp / 'abc.dsk'
        steps = ['wait:1800'] + create('ABC') + ['key:G', 'wait:90', 'key:\r', 'wait:600']
        steps += solve(1) + [peek('score_total', 4), peek('score_solved', 2),
                            'key: ', 'wait:180', 'key:P', 'wait:180', 'key:KI']
        steps += solve(1) + [peek('score_total', 4), peek('score_solved', 2),
                            'key: ', 'wait:180']
        steps += solve(2) + [peek('score_total', 4), peek('score_solved', 2),
                            'key: ', 'wait:180', peek('cur_lvl'), peek('hof_buf', 120),
                            'dsk:' + str(saved)]
        dumps = run(args.disk, steps)
        assert [int.from_bytes(x, 'little') for x in dumps[:7]] == [33, 1, 33, 1, 49, 2, 2], dumps
        hof = b''.join(dumps[7:])
        assert hof[4:7] == b'ABC' and entries(hof) == [('ABC', 49, 2), ('GIS', 0, 0)], entries(hof)
        assert hof[89:95] == b'GISABC' and hof[119] == 1
        image = saved.read_bytes()
        assert read_file(image, 'MICROHOF') == hof
        assert read_file(image, 'MICROSAVE') == save
        assert int.from_bytes(read_file(image, 'MICROSAV1')[14:16], 'little') == 33
        reboot = run(saved, ['wait:1800', peek('score_total', 4), peek('score_solved', 2), peek('hof_buf', 120)])
        assert [int.from_bytes(x, 'little') for x in reboot[:2]] == [49, 2]
        assert b''.join(reboot[2:]) == hof
        print('Profile ABC: automatic records, no initials prompt, best records and active-profile reboot: ok')

        # A second player starts with separate records, then the first resumes level 3.
        two = tmp / 'two.dsk'
        steps = ['wait:1800', 'key:V', 'wait:180', 'key:N', 'wait:180',
                 peek('hof_initials', 3), 'key:XYZ', 'key:\r', 'wait:600',
                 peek('score_total', 4), 'key:G', 'wait:90', 'key:\r', 'wait:600']
        steps += solve(1) + ['key: ', 'wait:180', 'key:\x1b', 'wait:180', 'key:V', 'wait:180',
                            'key:I', 'wait:120', 'key:\r', 'wait:600',
                            peek('score_total', 4), peek('cur_lvl'), peek('hist_pos_lo', 2),
                            peek('hof_buf', 120), 'dsk:' + str(two)]
        dumps = run(saved, steps)
        assert dumps[:5] == [b'ABC', bytes(4), (49).to_bytes(4, 'little'), b'\x02', bytes(2)], dumps[:5]
        two_hof = b''.join(dumps[5:])
        assert entries(two_hof) == [('ABC', 49, 2), ('XYZ', 33, 1), ('GIS', 0, 0)], entries(two_hof)
        assert read_file(two.read_bytes(), 'MICROSAV1')[:1830] == read_file(image, 'MICROSAV1')[:1830]
        assert int.from_bytes(read_file(two.read_bytes(), 'MICROSAV2')[14:16], 'little') == 33
        print('Independent profiles, new-name defaults, ranked results and resumed progress after switching: ok')

        # Renaming a profile preserves its stable save slot and ranked row.
        renamed = tmp / 'renamed.dsk'
        dumps = run(two, ['wait:1800', 'key:V', 'wait:180', 'key:R', 'wait:180',
                          peek('hof_initials', 3), 'key:DEF', 'key:\r', 'wait:600',
                          peek('hof_buf', 120), 'dsk:' + str(renamed)])
        assert dumps[0] == b'ABC'
        renamed_hof = b''.join(dumps[1:])
        assert entries(renamed_hof) == [('DEF', 49, 2), ('XYZ', 33, 1), ('GIS', 0, 0)]
        assert renamed_hof[92:95] == b'DEF' and renamed_hof[4:7] == b'DEF'
        assert read_file(renamed.read_bytes(), 'MICROSAV1')[:1830] == read_file(image, 'MICROSAV1')[:1830]
        print('Renaming preserves the profile progression and its single Hall of Fame row: ok')

        canceled = tmp / 'canceled.dsk'
        dumps = run(two, ['wait:1800', 'key:V', 'wait:180', 'key:N', 'wait:180',
                         'key:XYZ', 'key:\r', 'wait:180', peek('hof_initials', 3),
                         'key:\x1b', 'wait:180', 'key:\x1b', 'wait:180',
                         peek('hof_buf', 120), 'dsk:' + str(canceled)])
        assert dumps[0] == b'XYZ' and b''.join(dumps[1:]) == two_hof
        assert canceled.read_bytes() == two.read_bytes()
        print('Duplicate initials are rejected; canceling leaves every profile and disk untouched: ok')

        # Ten profiles, including unsolved players, remain visible without eviction.
        full = tmp / 'full.dsk'
        steps = ['wait:1800']
        for name in ['BBB', 'CCC', 'DDD', 'EEE', 'FFF', 'GGG', 'HHH', 'III', 'JJJ']:
            steps += create(name)
        steps += ['key:V', 'wait:180', 'key:N', 'wait:180', 'key:\x1b', 'wait:180',
                  peek('hof_buf', 120), 'dsk:' + str(full)]
        dumps = run(args.disk, steps)
        full_hof = b''.join(dumps)
        assert len(entries(full_hof)) == 10 and {r[0] for r in entries(full_hof)} == {
            'GIS', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF', 'GGG', 'HHH', 'III', 'JJJ'}
        assert all(r[1:] == (0, 0) for r in entries(full_hof))
        print('Ten named profiles, unsolved rows and full-registry behavior: ok')

        improved = tmp / 'improved.dsk'
        fixture(improved, {0: 35})
        dumps = run(improved, ['wait:1800', 'key: ', 'wait:180', 'key:P', 'wait:180',
                              peek('score_total', 4), *solve(1), peek('score_total', 4), peek('score_solved', 2)])
        assert [int.from_bytes(x, 'little') for x in dumps] == [35, 33, 1]
        mixed = tmp / 'mixed.dsk'
        fixture(mixed, {0: 33, 149: 16, 150: 1000, 271: 1001, total - 1: 65535})
        dumps = run(mixed, ['wait:1800', peek('score_total', 4), peek('score_solved', 2)])
        assert [int.from_bytes(x, 'little') for x in dumps] == [67585, 5]
        maximum = tmp / 'maximum.dsk'
        fixture(maximum, dict.fromkeys(range(total), 1))
        dumps = run(maximum, ['wait:1800', peek('score_total', 4), peek('score_solved', 2)])
        assert [int.from_bytes(x, 'little') for x in dumps] == [total, total]
        print('Improved records, all collections and exact move totals: ok')

        # Exact totals beyond 24 bits: the spare solved-count bit stores bit 24.
        huge = tmp / 'huge.dsk'
        fixture(huge, dict.fromkeys(range(total), 65535))
        persisted = tmp / 'huge-saved.dsk'
        dumps = run(huge, ['wait:1800', peek('score_total', 4), peek('hof_buf', 120),
                          'key:\x1b', 'wait:90', 'key:O', 'wait:90', 'key:\x1b', 'wait:180',
                          'dsk:' + str(persisted)])
        assert int.from_bytes(dumps[0], 'little') == total * 65535
        assert entries(b''.join(dumps[1:])) == [('GIS', total * 65535, total)]
        assert run(persisted, ['wait:1800', peek('score_total', 4)])[0] == dumps[0]
        print('Full 32-bit move totals, packed Hall of Fame and reboot: ok')

        # HOF2 points are rebuilt from every named profile, preserving the active one.
        migration = tmp / 'migration.dsk'
        old = bytearray(read_file(base, 'MICROHOF'))
        old[:4] = b'HOF2'
        old[92:95] = b'ABC'
        old[7:15] = b'GIS' + (2000).to_bytes(3, 'little') + (2).to_bytes(2, 'little')
        old[15:23] = b'ABC' + (1900).to_bytes(3, 'little') + (2).to_bytes(2, 'little')
        fixture(migration, {0: 60, 1: 40}, old)
        image = bytearray(migration.read_bytes())
        other = bytearray(save)
        other[14:16] = (35).to_bytes(2, 'little')
        other[18:20] = (15).to_bytes(2, 'little')
        replace_file(image, 'MICROSAV1', other)
        migration.write_bytes(image)
        dumps = run(migration, ['wait:1800', peek('hof_buf', 120)])
        migrated = b''.join(dumps)
        assert migrated[:7] == b'HOF3GIS' and migrated[119] == 0
        assert entries(migrated) == [('ABC', 50, 2), ('GIS', 100, 2)]
        print('HOF2 migration rebuilds every profile; equal solved counts favor fewer moves: ok')

        # Old shared records become the last active profile, with no fake extra players.
        legacy = tmp / 'legacy.dsk'
        old_hof = b'HOF1OLD' + bytes(80) + bytes([2, 1]) + bytes(31)
        fixture(legacy, {0: 35}, old_hof)
        dumps = run(legacy, ['wait:1800', peek('score_total', 4), peek('hof_buf', 120)])
        migrated = b''.join(dumps[1:])
        assert dumps[0] == (35).to_bytes(4, 'little')
        assert migrated[4:7] == b'OLD' and migrated[89:92] == b'OLD'
        assert entries(migrated) == [('OLD', 35, 1)]
        print('Legacy HOF1 initials and SOK2 progress import into profile zero: ok')

        consulted = tmp / 'consulted.dsk'
        dumps = run(two, ['wait:1800', 'key:\x1b', 'wait:180', 'key:F', 'wait:180',
                         'key:\r', 'wait:180', 'key:\x1b', 'wait:180',
                         peek('tutorial_on'), peek('hof_buf', 120), 'dsk:' + str(consulted)])
        assert dumps[0] == b'\0' and b''.join(dumps[1:]) == two_hof
        assert consulted.read_bytes() == two.read_bytes()
        print('Single menu → Hall of Fame → menu → title without starting a game: ok')

        visual = tmp / 'visual.dsk'
        steps = ['wait:1800', 'key:\x1b', 'wait:180', 'key:F', 'wait:60', 'spk']
        for _ in range(12):
            steps += [peek('hof_blink_state', 2), 'peek:5F00:16', 'peek:4888:16', 'wait:30']
        steps += ['spk', 'dsk:' + str(visual)]
        dumps = run(args.disk, steps, silent=True)
        states = [dumps[i][0] for i in range(0, len(dumps), 3)]
        colors = {dumps[i][1] for i in range(0, len(dumps), 3) if dumps[i][0]}
        assert set(states) == {0, 1} and len(colors) >= 3, (states, colors)
        assert len({dumps[i] for i in range(1, len(dumps), 3)}) == 1
        assert visual.read_bytes() == base
        print('Slow colored title blink, stable ranking and silent Hall of Fame: ok')

        # Attract mode shows the ranking for ten seconds before starting the demo.
        timed = tmp / 'timed.dsk'
        steps = ['wait:1800', 'spk']
        for _ in range(100):
            steps += [peek('hof_cycles'), peek('demo_active'), peek('title_phase'), 'wait:30']
        steps += ['spk', 'dsk:' + str(timed)]
        dumps = run(args.disk, steps, silent=True)
        phases = [dumps[i][0] for i in range(0, len(dumps), 3)]
        demo = [dumps[i][0] for i in range(1, len(dumps), 3)]
        animation = [dumps[i][0] for i in range(2, len(dumps), 3)]
        hall = [i for i, phase in enumerate(phases) if phase]
        assert hall and max(phases) == 10 and 19 <= len(hall) <= 22, (phases, demo)
        assert all(animation[i] == 16 for i in hall), animation
        assert not any(demo[:hall[-1] + 1]) and any(demo[hall[-1] + 1:]), (phases, demo)
        assert timed.read_bytes() == base
        interrupted = tmp / 'interrupted.dsk'
        steps = ['wait:1800', 'wait:%d' % (hall[0] * 30 + 60),
                 peek('hof_cycles'), 'key:Z', 'wait:180',
                 peek('demo_active'), peek('hof_cycles'), peek('tutorial_on'),
                 'dsk:' + str(interrupted)]
        dumps = run(args.disk, steps)
        assert dumps[0][0] > 0 and not any(b''.join(dumps[1:])), dumps
        assert interrupted.read_bytes() == base
        print('Animation ends with the box on target, then ten-second Hall of Fame, silent and interruptible: ok')

        protected = tmp / 'protected.dsk'
        run(args.disk, ['wait:1800', 'key:G', 'wait:90', 'key:\r', 'wait:600', *solve(1),
                        'dsk:' + str(protected)], wp=True)
        assert protected.read_bytes() == base
        attract = tmp / 'attract.dsk'
        dumps = run(args.disk, ['wait:1800', 'spk', 'wait:15600', 'spk',
                               peek('score_total', 4), peek('score_solved', 2),
                               'dsk:' + str(attract)], silent=True)
        assert not any(b''.join(dumps)) and attract.read_bytes() == base
        print('Write-protected disk and all seven attract levels leave save files unchanged: ok')


if __name__ == '__main__':
    main()
