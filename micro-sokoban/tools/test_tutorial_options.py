#!/usr/bin/env python3
"""Play all five teaching levels and exercise persistent sound options."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

from test_score import read_file
import micro_sokoban_levels as levels
import solver

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', default=ROOT / 'dev/tools/a2run/a2run', type=Path)
    ap.add_argument('--disk', default=ROOT / 'dist/MICRO-SOKOBAN.dsk', type=Path)
    args = ap.parse_args()
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', (GAME / 'build/micro_sokoban.lbl').read_text(), re.M)}
    base = args.disk.read_bytes()

    def peek(name, n=1):
        return f'peek:{labels[name]:04X}:{n}'

    def run(disk, steps, timeout=30):
        result = subprocess.run([str(args.a2run), '--disk', str(disk), *steps],
                                check=True, text=True, capture_output=True, timeout=timeout)
        dumps = [bytes.fromhex(x) for x in re.findall(r'^[0-9A-F]{4}: (.+)$', result.stdout, re.M)]
        speakers = [int(x) for x in re.findall(r'^spk (\d+)$', result.stdout, re.M)]
        return dumps, speakers

    # Each lesson has a checked tiny solution, independently replayed by the solver.
    solutions = ['rr', 'ru', 'rrull', 'udrru', 'rrddluu']
    grids = levels.parse_xsb(GAME / 'levels/tutorial.xsb')
    for (_, _, grid), solution in zip(grids, solutions):
        assert solver.check(grid, solution), solution
    with tempfile.TemporaryDirectory(prefix='micro-sokoban-tutorial-') as directory:
        tmp = Path(directory)
        completed = tmp / 'completed.dsk'
        steps = ['wait:1400', 'key: ', 'wait:120', peek('tutorial_on'),
                 'key:L', 'wait:30', 'key:U', 'wait:30', peek('moves_lo', 2),
                 'key:Y', 'wait:30', peek('moves_lo', 2), 'key:U', 'wait:30']
        for solution in solutions:
            keys = ''.join(dict(u='I', d='K', l='J', r='L')[c] for c in solution)
            steps += ['key:' + keys, 'wait:120', peek('moves_lo', 2), peek('boxes_left'),
                      peek('score_total', 3), 'key: ', 'wait:600']
        steps += [peek('tutorial_on'), 'dsk:' + str(completed)]
        dumps, _ = run(args.disk, steps)
        assert dumps[:3] == [b'\x01', b'\0\0', b'\x01\0'], dumps[:3]
        for i, solution in enumerate(solutions):
            count, boxes, score = dumps[3 + i * 3:6 + i * 3]
            assert int.from_bytes(count, 'little') == len(solution), (i, count)
            assert not any(boxes + score), (i, boxes, score)
        assert dumps[-1] == b'\0'
        image = completed.read_bytes()
        assert read_file(image, 'MICROSAVE')[14:1830] == read_file(base, 'MICROSAVE')[14:1830]
        assert read_file(image, 'MICROHOF')[87] & 1
        dumps, _ = run(completed, ['wait:1600', 'key: ', 'wait:120', peek('tutorial_on'),
                                  'key:\x1b', 'wait:90', 'key:T', 'wait:120',
                                  peek('tutorial_on'), peek('tutorial_idx')])
        assert dumps == [b'\0', b'\x01', b'\0'], dumps
        print('Five lessons (2, 2, 5, 5, 7 moves), Undo/Redo, no score reward and saved completion: ok')

        # HELP from the title returns to the animated title without entering a level.
        dumps, speakers = run(args.disk, ['wait:1400', 'spk', 'key:\x1b', 'wait:90', 'key:H', 'wait:90',
                                         'key:\x1b', 'wait:90', 'key:\x1b', 'wait:300', peek('tutorial_on'),
                                         peek('moves_lo', 2), peek('title_phase'), 'spk'])
        assert dumps[0] == b'\0' and dumps[1] == b'\0\0' and dumps[2][0] > 0, dumps
        assert speakers[-1] > 0
        assert read_file(base, 'MICROHOF')[88] == 3
        print('Title → MENU → HELP → MENU → title, no gameplay and menu sound on by default: ok')
        dumps, _ = run(args.disk, ['wait:1400', 'btn:1,1', 'wait:90', 'btn:1,0', 'wait:30',
                                  'key:K', 'wait:30', 'btn:1,1', 'wait:90', 'btn:1,0', 'wait:300',
                                  peek('tutorial_on'), peek('title_phase')])
        assert dumps[0] == b'\0' and dumps[1][0] > 0, dumps

        options = tmp / 'options.dsk'
        steps = ['wait:1400', 'spk', 'key:\x1b', 'wait:90', 'key:O', 'wait:120',
                 'key:\r', 'wait:120', 'spk']  # game off
        steps += ['key:K', 'wait:120']   # menu already on: leave it enabled
        for _ in range(2):               # demo on, deadlock off
            steps += ['key:K', 'wait:120', 'key:\r', 'wait:120']
        steps += ['spk', 'key:\x1b', 'wait:600', 'key:\x1b', 'wait:90',
                  peek('deadwarn_on'), 'dsk:' + str(options)]
        dumps, speakers = run(args.disk, steps)
        assert dumps == [b'\0'] and speakers[1] > 0 and speakers[2] > 0, (dumps, speakers)
        hof = read_file(options.read_bytes(), 'MICROHOF')
        assert hof[87:89] == bytes([0, 6]), hof[87:89]
        # Game off and demo on are independent, and both settings survive reboot.
        dumps, speakers = run(options, ['wait:1400', 'spk', peek('deadwarn_on'),
                                        'wait:5000', 'spk', peek('score_total', 3)])
        assert not any(b''.join(dumps)) and speakers[-1] > 0, (dumps, speakers)
        dumps, speakers = run(options, ['wait:1400', 'key:G', 'wait:90', 'key:\r', 'wait:600',
                                        'spk', 'key:LUYJ', 'wait:60', 'spk'])
        assert speakers[-1] == 0
        print('Separate game/menu/demo sound switches, deadlock option and reboot persistence: ok')

        # Title music uses only MENU SOUND and stops in the menu/game.
        for sound, audible in [(0, False), (1, False), (4, False), (2, True)]:
            _, speakers = run(args.disk, [
                'wait:1800', f'poke:{labels["hof_buf"]+88:04X}:{sound:02X}',
                'wait:60', 'spk',  # let any already-playing note finish
                'wait:240', 'spk',
                'key:\x1b', 'wait:120', 'spk', 'wait:180', 'spk',
                'key:\r', 'wait:600', 'spk', 'wait:240', 'spk',
            ])
            assert (speakers[1] > 0) == audible, (sound, speakers)
            # A held title note can finish before the pending ESC is consumed.
            # Once the menu is open, there must be no continuing music.
            assert speakers[3:] == [0, 0, 0], (sound, speakers)
        print('Calm native-speaker title music, independent switch, silent menu/game idle: ok')

        _, speakers = run(args.disk, [
            'wait:1800', f'until:{labels["run_hof_attract"]:04X}:5000', 'spk',
            'wait:300', 'spk', f'until:{labels["run_demo"]:04X}:1200', 'spk',
            'wait:900', 'spk',
        ])
        assert speakers[0] > 0 and speakers[1] == speakers[3] == 0, speakers
        print('Title music stops for the automatic ranking and silent demo: ok')

        cheat = tmp / 'cheat.dsk'
        steps = ['wait:1400', 'key:\x1b', 'wait:90', 'key:O', 'wait:120']
        for _ in range(4):                 # land on CHEAT MODE, leave the others
            steps += ['key:K', 'wait:40']
        steps += ['key:\r', 'wait:40', 'key:\x1b', 'wait:400',
                  f'peek:{labels["hof_buf"]+88:04X}:1', 'dsk:' + str(cheat)]
        dumps, _ = run(args.disk, steps, timeout=60)
        sound = dumps[0][0]
        assert sound & 8 and sound & 7 == 3, sound
        assert read_file(cheat.read_bytes(), 'MICROHOF')[88] == sound
        # SOLUTION is the last menu line. It plays the level, records nothing,
        # then restores the position.
        dumps, _ = run(cheat, [
            'wait:1400', 'key: ', 'wait:500',
            'key:\x1b', 'wait:80', 'key:I', 'wait:40', 'key:\r', 'wait:200',
            peek('watching'), peek('moves_lo', 2), peek('score_total', 3),
            'wait:1400',
            peek('watching'), peek('boxes_left'), peek('moves_lo', 2),
            peek('score_total', 3), 'dsk:' + str(tmp / 'aftersol.dsk'),
        ], timeout=90)
        assert dumps[0] == b'\x01', dumps[0]
        assert int.from_bytes(dumps[1], 'little') > 0, dumps[1]
        assert not any(dumps[2])
        assert dumps[3] == b'\x00'
        assert int.from_bytes(dumps[5], 'little') == 0
        assert not any(dumps[6])
        before = read_file(cheat.read_bytes(), 'MICROSAVE')
        after = read_file((tmp / 'aftersol.dsk').read_bytes(), 'MICROSAVE')
        assert after[14:1830] == before[14:1830]
        print('Cheat mode reveals SOLUTION; playback solves nothing and saves nothing: ok')


if __name__ == '__main__':
    main()
