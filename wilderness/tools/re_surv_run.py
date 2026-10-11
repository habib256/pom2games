#!/usr/bin/env python3
"""Drive the original game and retain every command's RAM and screenshot.

Usage: re_surv_run.py OUTPREFIX 'REST|2' 'DRINK WATER|!C|10'
Answers normally include RETURN; !C is a single-key answer (container
selection). @N waits N frames, ~N waits between answers, !KEY types raw
keys. An emulator failure or missing checkpoint is an error, never success.
Original disks remain local in build/; no ROM or original code is embedded.
"""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import a2test


def boot():
    return ['wait:5000', 'key:1\r', 'wait:3000',
            'insert:build/JOURNEY.dsk', 'key:\r', 'wait:3000',
            'key:\r', 'wait:600', 'key:\r', 'wait:60', 'until:B0E2:8000']


def command_steps(command):
    if command.startswith('!'):
        return [f'key:{command[1:]}']
    first, *answers = command.split('|')
    steps = [f'key:{first}\r']
    for answer in answers:
        if answer.startswith('~'):
            steps.append(f'wait:{answer[1:]}')
        else:
            steps.extend(['wait:400', f'key:{answer[1:]}' if answer.startswith('!')
                          else f'key:{answer}\r'])
    return steps


def play(prefix, commands, timeout=1800):
    prefix = Path(prefix)
    if not prefix.is_absolute():
        prefix = HERE / prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    # Validate prerequisites before boot; absent disks must not silently skip.
    for name in ('SIERRA.woz', 'JOURNEY.dsk'):
        if not (HERE / 'build' / name).is_file():
            raise FileNotFoundError(f'Missing local original disk: build/{name}')
    steps = boot() + ['peek:0000:49152', f'shot:{prefix}0.png']
    labels = ['START']
    for command in commands:
        if command.startswith('@'):
            steps.append(f'wait:{command[1:]}')
            continue
        labels.append(command)
        steps += command_steps(command) + ['wait:60', 'until:B0E2:8000',
                  'peek:0000:49152', f'shot:{prefix}{len(labels)-1}.png']
    result = subprocess.run([str(a2test.A2SHOT), '--disk', 'build/SIERRA.woz',
                             *a2test.escape(steps)], cwd=HERE,
                            capture_output=True, text=True, timeout=timeout)
    prefix.with_suffix('.log').write_text(result.stdout + result.stderr)
    decoded = a2test.Result(result.stdout)
    dumps = []
    for i, label in enumerate(labels):
        try:
            dump = decoded.mem(0, 49152, i)
        except AssertionError:
            raise RuntimeError(f'Original stopped before checkpoint {i}: {label}. '
                               f'Emulator exit {result.returncode}; see {prefix.with_suffix(".log")}') from None
        Path(f'{prefix}{i}.bin').write_bytes(dump)
        dumps.append(dump)
    if result.returncode:
        raise RuntimeError(f'Original emulator exit {result.returncode}; see {prefix.with_suffix(".log")}')
    return dumps


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    try:
        dumps = play(sys.argv[1], sys.argv[2:])
    except (RuntimeError, FileNotFoundError) as error:
        raise SystemExit(str(error))
    print(f'{len(dumps)} checkpoints verified')


if __name__ == '__main__':
    main()
