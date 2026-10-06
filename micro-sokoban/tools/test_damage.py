#!/usr/bin/env python3
"""Damaged or missing save files and rankings: the game starts, goes on and repairs what it can."""
from pathlib import Path
import argparse
import re
import sys
import tempfile
from test_score import entries

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
import dos33
import micro_sokoban_levels as levels


def set_length(image, name, length):
    """The length field of a DOS binary file, whatever its sectors hold."""
    offset = dos33.file_sectors(image, name)[0]
    image[offset + 2:offset + 4] = length.to_bytes(2, 'little')


def rename(image, name, other):
    """Change a catalog entry, so the game no longer finds `name`."""
    old = bytes(c | 0x80 for c in name.ljust(30).encode('ascii'))
    assert image.count(old) == 1 and len(other) == len(name)
    at = image.index(old)
    image[at:at + 30] = bytes(c | 0x80 for c in other.ljust(30).encode('ascii'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', type=Path, default=ROOT / 'dev/tools/a2run/a2run')
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/MICRO-SOKOBAN.dsk')
    args = ap.parse_args()
    labels = a2test.labels(GAME / 'build/micro_sokoban.lbl')
    base = args.disk.read_bytes()
    save = dos33.read_file(base, 'MICROSAVE')
    hof = dos33.read_file(base, 'MICROHOF')
    keys = levels.solution_keys(levels.read_solutions(GAME / 'levels/solutions.txt')[('I', 1)])
    peek = labels.peek

    def run(disk, steps):
        result = a2test.run(disk, steps, emulator=args.a2run, timeout=60)
        return result.lines(), result.out

    def status(page):
        """The seven cells of the status corner (byte columns 31-37, scanlines 180-187) on an HGR page."""
        rows = []
        for y in range(180, 188):
            address = (0x4000 if page else 0x2000) + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28
            rows.append(f'peek:{address + 31:04X}:7')
        return rows

    def cells(rows):
        return [bytes(row[i] for row in rows) for i in range(7)]

    def records(payload):
        return {i: int.from_bytes(payload[14 + 4 * i:16 + 4 * i], 'little')
                for i in range(454) if any(payload[14 + 4 * i:18 + 4 * i])}

    boot = ['wait:1800']
    start = ['key:G', 'wait:90', 'key:\r', 'wait:180']
    first = boot + start
    menu = ['key:\x1b', 'wait:300']
    state = [peek('cur_coll', 2), peek('moves_lo', 2), peek('game_active')]

    with tempfile.TemporaryDirectory(prefix='micro-damage-') as directory:
        tmp = Path(directory)

        def disk(name, change, records_=None, ranking=None):
            image = bytearray(base)
            payload = bytearray(save)
            for index, moves in (records_ or {}).items():
                payload[14 + index * 4:18 + index * 4] = moves.to_bytes(2, 'little') + bytes(2)
            dos33.replace_file(image, 'MICROSAVE', payload)
            if ranking is not None:
                dos33.replace_file(image, 'MICROHOF', bytes(ranking))
            change(image)
            path = tmp / name
            path.write_bytes(image)
            return path

        # A save file whose length cannot be: the profile starts empty, and the next save makes a good file.
        bad = disk('length.dsk', lambda image: set_length(image, 'MICROSAVE', 4000), {0: 40, 7: 50})
        again = tmp / 'again.dsk'
        dumps, _ = run(bad, boot + [peek('score_solved', 2)] + start +
                       ['key:' + keys[:11], 'wait:30', *state, *menu, 'dsk:' + str(again)])
        assert dumps == [b'\0\0', b'\0\0', b'\x0b\0', b'\x01'], dumps
        rewritten = dos33.read_file(again.read_bytes(), 'MICROSAVE')
        assert len(rewritten) == len(save) and rewritten[:4] == b'SOK2' and not records(rewritten)
        assert rewritten[6:14] == save[6:14] and rewritten[1830:1831] == b'P'
        dumps, _ = run(again, boot + ['key: ', 'wait:180', *state])
        assert dumps == [b'\0\0', b'\x0b\0', b'\x01'], dumps
        print('Save file with an impossible length: empty profile, play goes on, the next save rewrites it: ok')

        # The same for the ranking: the defaults replace it on the disk during the start.
        bad = disk('ranking.dsk', lambda image: set_length(image, 'MICROHOF', 121))
        run(bad, boot + ['dsk:' + str(again)])
        assert dos33.read_file(again.read_bytes(), 'MICROHOF') == hof[:4] + b'GIS' + bytes(80) + hof[87:], \
            'the defaults were not written over the unreadable ranking at once'
        dumps, _ = run(bad, first + ['key:' + keys, 'wait:600', peek('hof_buf', 120), *state,
                                     'dsk:' + str(again)])
        ranking = b''.join(dumps[:8])
        assert ranking[:7] == b'HOF3GIS' and entries(ranking) == [('GIS', 33, 1)] and dumps[-1] == b'\x01'
        assert dos33.read_file(again.read_bytes(), 'MICROHOF') == ranking
        print('Ranking with an impossible length: defaults written over it at once, play goes on: ok')

        # No save file at all: nothing can be written. "IO ERR" says so, and the game goes on.
        gone = disk('gone.dsk', lambda image: rename(image, 'MICROSAVE', 'MICROSAVX'), {0: 40})
        dumps, _ = run(gone, first + [peek('score_solved', 2), 'key:' + keys[:11], 'wait:700',
                                      peek('front_page'), *status(0), *status(1), *state,
                                      'key:' + keys[11:], 'wait:600', 'key: ', 'wait:300', *state,
                                      'dsk:' + str(again)])
        assert dumps[0] == b'\0\0'
        shown = cells(dumps[10:18] if dumps[1][0] else dumps[2:10])
        assert all(any(cell) for cell in shown[:2] + shown[3:6]) and not any(shown[2]) and not any(shown[6]), \
            'the status corner does not read "IO ERR "'
        assert dumps[18:21] == [b'\0\0', b'\x0b\0', b'\x01'], dumps[18:21]
        assert dumps[21:] == [b'\0\x01', b'\0\0', b'\x01'], dumps[21:]
        after = bytearray(again.read_bytes())
        offset = dos33.file_sectors(base, 'MICROHOF')[0]
        after[offset:offset + 256] = gone.read_bytes()[offset:offset + 256]
        assert after == gone.read_bytes(), 'something else than the ranking was written'
        print('Missing save file: "IO ERR" stays in the status corner, the level is played and solved: ok')

        # A level pack cannot be done without: the error covers the whole "LOADING", any key leaves.
        pack = disk('pack.dsk', lambda image: set_length(image, 'MB1B', 3000))
        dumps, text = run(pack, boot + ['key:G', 'wait:90', 'key:KKKKKLLLLLLLL', 'wait:60', 'key:\r', 'wait:300',
                                        peek('cur_lvl'), 'key:N', 'wait:400', peek('front_page'),
                                        *status(0), *status(1), 'key: ', 'wait:600', 'text'])
        assert dumps[0] == b'\x3a'
        shown = cells(dumps[10:18] if dumps[1][0] else dumps[2:10])
        assert any(shown[0]) and any(shown[5]) and not any(shown[6]), 'a letter of "LOADING" is left after "IO ERR"'
        assert re.search(r'^\|\]', text, re.M), 'a key after a pack error must leave to BASIC'
        print('Unreadable level pack: "IO ERR" over all of "LOADING", then BASIC: ok')

        # A save file cut short with its magic intact: what the file does not hold is empty.
        short = disk('short.dsk', lambda image: set_length(image, 'MICROSAVE', 0x06AC), {0: 33, 440: 77})
        dumps, _ = run(short, boot + [peek('score_solved', 2), peek('score_total', 4)] + start +
                       ['key:' + keys[:5], 'wait:30', *menu, 'dsk:' + str(again)])
        assert dumps[:2] == [b'\x01\0', b'\x21\0\0\0'], dumps[:2]
        rewritten = dos33.read_file(again.read_bytes(), 'MICROSAVE')
        assert len(rewritten) == len(save) and records(rewritten) == {0: 33}, records(rewritten)
        print('Save file shorter than its records: the missing ones are empty, not leftover memory: ok')

        # A ranking that disagrees with its own profiles is put right from them.
        def ranking(active, initials, names, rows, magic=b'HOF3'):
            data = bytearray(hof)
            data[:4], data[4:7], data[119] = magic, initials, active
            data[7:87] = b''.join(name + total.to_bytes(3, 'little') + solved.to_bytes(2, 'little')
                                  for name, total, solved in rows).ljust(80, b'\0')
            data[89:119] = b''.join(names).ljust(30, b'\0')
            return data

        def loaded(data, records_=None):
            path = disk('ranking.dsk', lambda image: None, records_, data)
            dumps, _ = run(path, boot + [peek('hof_buf', 120), *menu, 'key:O', 'wait:120', 'key:\r', 'wait:60',
                                         'key:\x1b', 'wait:300', 'dsk:' + str(again)])
            data = b''.join(dumps)
            written = dos33.read_file(again.read_bytes(), 'MICROHOF')
            assert written[:87] == data[:87] and written[89:] == data[89:], 'the repaired ranking was not written'
            return data[4:7], data[119], data[89:119].rstrip(b'\0'), entries(data)

        rows = [(b'ABC', 50, 2), (b'GIS', 100, 2)]
        assert loaded(ranking(1, b'XYZ', [b'GIS', b'ABC'], rows)) == \
            (b'ABC', 1, b'GISABC', [('GIS', 100, 2), ('ABC', 0, 0)])
        assert loaded(ranking(0, b'GIS', [b'GIS', b'ABC'], [(b'ZZZ', 5, 9)] + rows + [(b'ABC', 7, 3)]),
                      {0: 60, 1: 40}) == (b'GIS', 0, b'GISABC', [('ABC', 50, 2), ('GIS', 100, 2)])
        assert loaded(ranking(7, b'ABC', [b'GIS', b'ABC'], rows), {0: 60, 1: 40}) == \
            (b'GIS', 0, b'GISABC', [('ABC', 50, 2), ('GIS', 100, 2)])
        assert loaded(ranking(1, b'GIS', [b'GIS', b'GIS'], rows)) == (b'GIS', 0, b'GIS', [('GIS', 0, 0)])
        print('Ranking header, active slot and rows are made to agree with the ten profiles: ok')

        old = ranking(0, b'GIS', [b'GIS', b'ABC'], [(b'GIS', 2000, 2), (b'ZZZ', 5000, 9), (b'ABC', 1900, 2)],
                      magic=b'HOF2')
        assert loaded(old, {0: 60, 1: 40}) == (b'GIS', 0, b'GISABC', [('GIS', 100, 2), ('ABC', 0, 0)])
        print('HOF2 migration keeps no row without a profile: ok')


if __name__ == '__main__':
    main()
