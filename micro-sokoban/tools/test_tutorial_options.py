#!/usr/bin/env python3
"""Play all five teaching levels and exercise persistent sound options."""
from pathlib import Path
import argparse
import cmath
import sys
import tempfile

import solver

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
import dos33
import micro_sokoban_levels as levels


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', default=ROOT / 'dev/tools/a2run/a2run', type=Path)
    ap.add_argument('--disk', default=ROOT / 'dist/MICRO-SOKOBAN.dsk', type=Path)
    args = ap.parse_args()
    labels = a2test.labels(GAME / 'build/micro_sokoban.lbl')
    base = args.disk.read_bytes()

    peek = labels.peek

    def run(disk, steps, timeout=30):
        result = a2test.run(disk, steps, emulator=args.a2run, timeout=timeout)
        return result.lines(), result.spk

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
            keys = levels.solution_keys(solution)
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
        assert dos33.read_file(image, 'MICROSAVE')[14:1830] == dos33.read_file(base, 'MICROSAVE')[14:1830]
        assert dos33.read_file(image, 'MICROHOF')[87] & 1
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
        assert dos33.read_file(base, 'MICROHOF')[88] == 3
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
        hof = dos33.read_file(options.read_bytes(), 'MICROHOF')
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

        # Two voices: the first beat holds its bass count under its melody
        # count, each a square wave at its share of the speaker's level.
        binary = (GAME / 'build/micro_sokoban.bin').read_bytes()
        mel, bass = (binary[labels[name] - 0x6000] for name in ('title_mel', 'title_bass'))
        assert 0 < mel < bass, (mel, bass)
        log = tmp / 'speaker.txt'
        run(args.disk, ['wait:700', f'spklog:{log}', 'wait:1700'])
        toggles = [int(line) for line in log.read_text().split()]
        turn, turns = 33, 255                    # title_music.inc: DUET_CYCLES, DUET_TURNS
        slice_cycles = turns * turn + 47
        step, count = 128, 3000                  # 0.38 s of the first, 0.55 s note
        start, level, at, means = toggles[0] + 2 * slice_cycles, 0, 0, []
        while toggles[at] < start:
            at += 1
        for window in range(count):              # mean level of each window
            end, t, high = start + (window + 1) * step, start + window * step, 0
            while toggles[at] < end:
                high += level * (toggles[at] - t)
                t, level, at = toggles[at], level ^ 1, at + 1
            means.append((high + level * (end - t)) / step)
        mean = sum(means) / count

        def amplitude(half_period):
            w = cmath.pi * step * turns / (half_period * slice_cycles)
            return abs(sum((x - mean) * cmath.exp(-1j * w * k) for k, x in enumerate(means))) * 2 / count
        square = 4 / cmath.pi / 2                # fundamental of a 0/1 square wave
        for count_, share in ((mel, 19 / 33), (bass, 14 / 33)):
            assert abs(amplitude(count_) / (square * share) - 1) < 0.1, (count_, amplitude(count_))
        assert amplitude(mel * 1.2) < 0.03, amplitude(mel * 1.2)
        # Ten bars before the loop, on a steady beat although the corridor is
        # redrawn meanwhile. Notes are detached at each beat: a silence starts one.
        starts = [toggles[0]] + [b for a, b in zip(toggles, toggles[1:]) if b - a > 25000]
        beat = 72 * slice_cycles
        for index, bars in ((4, 1), (39, 10)):   # the last bar has a silent beat
            assert abs((starts[index] - starts[0]) / beat - 4 * bars) < 0.1, (index, starts[index] - starts[0])
        # A key cuts the note being played instead of waiting for its end.
        _, speakers = run(args.disk, ['wait:1000', 'spk', 'press:\x1b', 'wait:1', 'spk',
                                      'wait:2', 'spk', 'wait:120', 'spk'])
        assert speakers[0] > 0 and speakers[2:] == [0, 0], speakers
        print('Two-voice title music: bass under melody, ten steady bars, cut by a key: ok')

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
        assert dos33.read_file(cheat.read_bytes(), 'MICROHOF')[88] == sound
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
        before = dos33.read_file(cheat.read_bytes(), 'MICROSAVE')
        after = dos33.read_file((tmp / 'aftersol.dsk').read_bytes(), 'MICROSAVE')
        assert after[14:1830] == before[14:1830]
        print('Cheat mode reveals SOLUTION; playback solves nothing and saves nothing: ok')

        color = tmp / 'color.dsk'
        steps = ['wait:1400', 'key:\x1b', 'wait:90', 'key:O', 'wait:120']
        for _ in range(5):                 # COLOR MODE is the last switch, above BACK
            steps += ['key:K', 'wait:40']
        steps += ['key:\r', 'wait:40', 'key:K', 'wait:40', 'key:\r', 'wait:400',
                  f'peek:{labels["hof_buf"]+88:04X}:1', 'dsk:' + str(color)]
        dumps, _ = run(args.disk, steps, timeout=60)
        assert dumps[0][0] == 3 | 16, dumps[0]
        assert dos33.read_file(color.read_bytes(), 'MICROHOF')[88] == 3 | 16
        dumps, _ = run(color, ['wait:1400', f'peek:{labels["hof_buf"]+88:04X}:1'])
        assert dumps[0][0] == 3 | 16, dumps[0]
        print('COLOR MODE is off by default, toggles, BACK leaves OPTIONS, and it survives reboot: ok')


if __name__ == '__main__':
    main()
