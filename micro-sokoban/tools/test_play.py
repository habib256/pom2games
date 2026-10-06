#!/usr/bin/env python3
"""Leave a game in progress and come back: tutorial, SOLUTION, profiles, shuttle, status text, counters."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
from test_score import entries, file_sectors, read_file

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', type=Path, default=ROOT / 'dev/tools/a2run/a2run')
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/MICRO-SOKOBAN.dsk')
    args = ap.parse_args()
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', (GAME / 'build/micro_sokoban.lbl').read_text(), re.M)}

    def peek(name, count=1, offset=0):
        return f'peek:{labels[name] + offset:04X}:{count}'

    def poke(name, value):
        return f'poke:{labels[name]:04X}:{value:02X}'

    def run(disk, steps, wp=False):
        result = subprocess.run([str(args.a2run), '--disk', str(disk), *(['--wp'] if wp else []), *steps],
                                check=True, text=True, capture_output=True, timeout=60)
        return [bytes.fromhex(row) for row in re.findall(r'^[0-9A-F]{4}: (.+)$', result.stdout, re.M)]

    def groups(rows, size):
        return [b''.join(rows[i:i + size]) for i in range(0, len(rows), size)]

    # Board, player, moves/pushes/boxes left, then history position, Undo and Redo counts.
    state = [peek('STATE_GRID', 240), peek('player_row', 2), peek('moves_lo', 5), peek('hist_pos_lo', 6)]
    rows = 15 + 3
    position = slice(0, 247)

    base = args.disk.read_bytes()
    solutions = {tuple(row.split()[:2]): row.split()[3] for row in
                 (GAME / 'levels/solutions.txt').read_text().splitlines() if row.startswith('I')}

    def keys(hud, number, count=None):
        return ''.join(dict(u='I', d='K', l='J', r='L')[c] for c in solutions[hud, str(number)].lower()[:count])

    boot = ['wait:1800']
    first = boot + ['key:G', 'wait:90', 'key:\r', 'wait:180']
    menu = ['key:\x1b', 'wait:300']
    cheat = ['key:O', 'wait:120', 'key:KKKK', 'wait:60', 'key:\r', 'wait:120', 'key:\x1b', 'wait:180']
    # From OPTIONS, four lines down: SOLUTION. A key stops the playback after a few moves.
    watch = ['key:KKKK', 'wait:60', 'key:\r', 'wait:400', 'key: ', 'wait:400']

    with tempfile.TemporaryDirectory(prefix='micro-play-') as directory:
        tmp = Path(directory)

        # T in the menu, in the middle of a level: the lessons, then that level again.
        lessons = tmp / 'lessons.dsk'
        dumps = groups(run(args.disk, first + ['key:' + keys('I', 1, 11), 'wait:30', *state, *menu,
                                              'key:T', 'wait:200', peek('tutorial_on'), *['key:N', 'wait:200'] * 5,
                                              peek('tutorial_on'), *state, 'wait:700', 'dsk:' + str(lessons)]), 1)
        before, during, after = b''.join(dumps[:rows]), dumps[rows], dumps[rows + 1]
        played = b''.join(dumps[rows + 2:])
        assert int.from_bytes(before[242:244], 'little') == 11 and during == b'\x01' and after == b'\0'
        assert played[position] == before[position], 'the level in progress did not come back after the tutorial'
        resumed = b''.join(run(lessons, boot + ['key: ', 'wait:180', *state]))
        assert resumed[position] == before[position], 'the tutorial replaced the saved position'
        assert read_file(lessons.read_bytes(), 'MICROSAVE')[4] & 0x80
        changed = {i for i in range(0, len(base), 256) if base[i:i + 256] != lessons.read_bytes()[i:i + 256]}
        assert changed <= set(file_sectors(base, 'MICROSAVE')) | set(file_sectors(base, 'MICROHOF')), changed
        print('Tutorial replayed from a game: level, counters and saved position come back: ok')

        # SOLUTION gives the position back, with its Undo/Redo history, protected disk or not.
        for wp in (False, True):
            image = tmp / 'watched.dsk'
            dumps = b''.join(run(args.disk, first + ['key:' + keys('I', 1, 12), 'key:UU', 'wait:30', *state, *menu,
                                                    *cheat, *watch, *state, 'key:' + 'U' * 10, 'wait:60', *state,
                                                    'key:' + 'Y' * 12, 'wait:60', *state, 'dsk:' + str(image)], wp))
            before, after, undone, redone = (dumps[i:i + 253] for i in range(0, 4 * 253, 253))
            assert before[247:] == bytes([10, 0, 10, 0, 2, 0]), before[247:]
            assert after == before, ('SOLUTION lost the position or the history', wp)
            assert undone[242:246] == bytes(4) and undone[247:] == bytes([0, 0, 0, 0, 12, 0]), undone[242:]
            assert int.from_bytes(redone[242:244], 'little') == 12 and redone[:240] != before[:240]
            assert wp is False or image.read_bytes() == base
        # A protected disk still carrying an older position of another level must not bring it back.
        saved = tmp / 'saved.dsk'
        run(args.disk, first + ['key:' + keys('I', 1, 11), 'wait:30', *menu, 'dsk:' + str(saved)])
        dumps = b''.join(run(saved, boot + ['key:G', 'wait:90', 'key:L', 'wait:60', 'key:\r', 'wait:180',
                                           'key:' + keys('I', 2, 3), 'wait:30', peek('cur_lvl'), *state, *menu,
                                           *cheat, *watch, peek('cur_lvl'), *state], wp=True))
        assert dumps[:254] == dumps[254:] and dumps[0] == 1, 'SOLUTION left the level being played'
        print('SOLUTION: position and Undo/Redo history kept, on a write-protected disk too: ok')

        # Button 0 + stick left rewinds; releasing the button first must not walk the player.
        shuttle = first + ['key:' + keys('I', 1, 12), 'wait:30', 'btn:0,1', 'wait:6', 'joy:-1,0', 'wait:60', *state]
        dumps = groups(run(args.disk, shuttle + ['btn:0,0', 'wait:60', *state, 'joy:0,0', 'wait:12',
                                                'joy:-1,0', 'wait:6', 'joy:0,0', 'wait:12', *state]), rows)
        rewound, released, moved = dumps
        assert rewound[242] < 12 and rewound[251] == 12 - rewound[242], rewound[242:]
        assert released == rewound, 'the stick moved the player before it was centred'
        assert moved[242] == rewound[242] + 1 and moved[251] == 0, 'the centred stick no longer moves the player'
        dumps = groups(run(args.disk, first + ['key:' + keys('I', 1, 12), 'wait:30', *state,
                                              'btn:0,1', 'wait:6', 'btn:0,0', 'wait:12', *state]), rows)
        assert dumps[1][242] == 11 and dumps[1][251] == 1, 'a tap of button 0 is one Undo'
        print('Shuttle released with the stick still held: no move, Redo kept; stick and tap as before: ok')

        # The two levels with tiles under the "SAVING" text: III:054 and IV:036.
        for route, name in ((['key:N', 'wait:60', 'key:N', 'wait:60', 'key:KKKKLLLLLLLL'], 'III:054'),
                            (['key:P', 'wait:60', 'key:KKKLLLL'], 'IV:036')):
            shots = [tmp / 'played.png', tmp / 'saved.png']
            image = tmp / 'status.dsk'
            grid = b''.join(run(args.disk, boot + ['key:G', 'wait:90', *route, 'wait:60', 'key:\r', 'wait:400',
                                                  'key:IKJL', 'wait:30', peek('STATE_GRID', 240),
                                                  'shot:' + str(shots[0]), 'wait:700', 'shot:' + str(shots[1]),
                                                  'dsk:' + str(image)]))
            assert grid[11 * 20 + 15] == 1, name + ' no longer has a wall under the status text'
            assert image.read_bytes() != base, 'no idle save took place'
            assert shots[0].read_bytes() == shots[1].read_bytes(), name + ': the status text damaged the level'
        print('Idle save on III:054 and IV:036: the tiles under "SAVING" are drawn again: ok')

        # Two profiles, GIS active and playing. Renaming the other one changes its name only.
        two = tmp / 'two.dsk'
        run(args.disk, boot + ['key:V', 'wait:180', 'key:N', 'wait:180', 'key:ABC', 'key:\r', 'wait:600',
                               'key:V', 'wait:180', 'key:I', 'wait:60', 'key:\r', 'wait:600', 'dsk:' + str(two)])
        renamed = tmp / 'renamed.dsk'
        dumps = run(two, first + ['key:' + keys('I', 1, 5), 'wait:30', *state, *menu, 'key:V', 'wait:180',
                                  'key:K', 'wait:60', 'key:R', 'wait:180', 'key:XYZ', 'key:\r', 'wait:600',
                                  'key:\x1b', 'wait:180', *state, peek('hof_buf', 120), 'dsk:' + str(renamed)])
        before, after, hof = b''.join(dumps[:rows]), b''.join(dumps[rows:2 * rows]), b''.join(dumps[2 * rows:])
        assert after == before, 'renaming another profile disturbed the game in progress'
        assert hof[4:7] == b'GIS' and hof[119] == 0 and hof[89:95] == b'GISXYZ', hof
        assert {row[0] for row in entries(hof)} == {'GIS', 'XYZ'}
        assert read_file(renamed.read_bytes(), 'MICROHOF') == hof
        print('Renaming a profile that is not the active one: active profile, game and history stay: ok')

        # A profile created from a game gets its five lessons, like one created from the title.
        dumps = run(args.disk, first + ['key:' + keys('I', 1, 5), 'wait:30', *menu, 'key:V', 'wait:180',
                                        'key:N', 'wait:180', 'key:ABC', 'key:\r', 'wait:600',
                                        peek('tutorial_on', 2), peek('hof_buf', 1, 119),
                                        *['key:N', 'wait:200'] * 5, 'wait:300', peek('tutorial_on'),
                                        peek('cur_coll', 2), peek('moves_lo', 2), *menu, 'key:V', 'wait:180',
                                        'key:I', 'wait:60', 'key:\r', 'wait:600', peek('tutorial_on'),
                                        peek('moves_lo', 2)])
        assert dumps[:5] == [b'\x01\0', b'\x01', b'\0', b'\0\0', b'\0\0'], dumps[:5]
        assert dumps[5:] == [b'\0', b'\x05\0'], dumps[5:]
        print('Profile created from the menu of a game: first-play tutorial, then its first level: ok')

        # Counters stop at 65535: 33 moves and 8 pushes from 65503 / 65530 are not a record of 0.
        record = f'peek:{labels["save_buf"] + 14:04X}:4'
        dumps = run(args.disk, first + [poke('moves_lo', 0xDF), poke('moves_hi', 0xFF), poke('pushes_lo', 0xFA),
                                        poke('pushes_hi', 0xFF), 'key:' + keys('I', 1), 'wait:600',
                                        peek('moves_lo', 4), record, peek('score_solved', 2)])
        assert dumps == [b'\xff' * 4, b'\xff' * 4, b'\x01\0'], dumps
        print('Move and push counters stay at 65535 and the level counts as solved: ok')

        # A key still repeating after the winning move (a //e), or typed ahead, must not skip SUCCESS or BRAVO.
        level = [peek('cur_coll', 2), peek('moves_lo', 2), peek('boxes_left')]
        won = keys('I', 1)
        dumps = run(args.disk, first + ['key:' + won + won[-1] * 6, 'wait:300', *level,
                                        'key: ', 'wait:300', *level])
        assert dumps[:3] == [b'\0\0', b'\x21\0', b'\0'], 'repeated keys skipped SUCCESS'
        assert dumps[3:] == [b'\0\x01', b'\0\0', b'\x01'], dumps[3:]
        won = keys('III', 100)
        dumps = run(args.disk, boot + ['key:G', 'wait:90', 'key:N', 'wait:60', 'key:N', 'wait:60',
                                       'key:KKKKKKKKKL', 'wait:60', 'key:\r', 'wait:400',
                                       'key:' + won + won[-1] * 2, 'wait:300', *level, 'key: ', 'wait:300', *level,
                                       'key: ', 'wait:400', peek('cur_coll', 2)])
        assert dumps[:3] == dumps[3:6] == [b'\x02\x5b', len(won).to_bytes(2, 'little'), b'\0'], dumps[:6]
        assert dumps[6] == b'\x03\0', 'SUCCESS, then BRAVO, then the next collection'
        dumps = run(args.disk, first + ['key:' + keys('I', 1), 'wait:120', 'btn:0,1', 'wait:6', 'btn:0,0',
                                        'wait:300', peek('cur_coll', 2)])
        assert dumps == [b'\0\x01'], 'a button must still leave SUCCESS'
        print('Typed-ahead or repeating keys do not skip SUCCESS / BRAVO; a later key or a button does: ok')


if __name__ == '__main__':
    main()
