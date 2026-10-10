#!/usr/bin/env python3
"""Exhaustive Light3DBall projection correctness + cycles, JSR/RTS included.

Optional --before DIR reads DIR/{game.bin,game.lbl,assets.bin}; capture these
before an edit to compare the original renderer to the extracted kernel.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

DEV=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DEV/'tools'))
import a2test


def probe(work, labels, binary, assets=None, centers=(128,80), shift=1, sanitize=False):
    names={'PROJECT_X':'project_x','PROJECT_Y':'project_y','SELECT_DEPTH':'perspective',
           'STATE_SX':'sx','STATE_SY':'sy','STATE_LEFT':'left','STATE_TOP':'top',
           'STATE_DEPTH':'depth','TABLE_X':'scale_x','TABLE_Y':'scale_y'}
    (work/'corridor_labels.h').write_text(
        '\n'.join(f'#define {name} {labels[symbol]}' for name,symbol in names.items())+
        f'\n#define CENTER_X {centers[0]}\n#define CENTER_Y {centers[1]}\n#define DEPTH_SHIFT {shift}\n')
    executable=work/'probe'
    flags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'] if sanitize else []
    subprocess.run([*shlex.split(os.environ.get('CC','cc')),'-O2',*flags,
                    '-I',str(work),'-I',str(DEV/'tools/a2run'),
                    str(DEV/'bench/corridor_probe.c'),str(DEV/'tools/a2run/cpu6502.c'),
                    '-o',str(executable)],check=True)
    output=subprocess.check_output([str(executable),str(binary),*([str(assets)] if assets else [])],text=True)
    return [tuple(map(int,line.split())) for line in output.splitlines()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path)
    args=parser.parse_args()
    game=DEV.parent/'light3dball'
    subprocess.run(['make','-s','-C',str(game)],check=True)
    with tempfile.TemporaryDirectory(prefix='pom2-corridor-bench-') as temp:
        work=Path(temp)
        current=probe(work,a2test.labels(game/'build/game.lbl',strip=True),
                      game/'build/game.bin',game/'build/assets.bin')
        old=None
        if args.before:
            old=probe(work,a2test.labels(args.before/'game.lbl',strip=True),
                      args.before/'game.bin',args.before/'assets.bin')
        for family,minimum,maximum,total,count in current:
            name=('select','project X','project Y')[family]
            print(f'{name}: {minimum}..{maximum} cycles, mean {total/count:.3f}, {count} calls verified')
        if old is not None:
            assert current==old, ('projection cycles changed',old,current)
            print('Before/after: identical cycle counts for every measured family (0% change).')


if __name__=='__main__':
    main()
