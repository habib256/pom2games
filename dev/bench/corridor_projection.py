#!/usr/bin/env python3
"""Exhaustive Light3DBall projection correctness + cycles, JSR/RTS included.

Optional --before DIR reads DIR/{game.bin,game.lbl,assets.bin}; capture these
before an edit to compare the original renderer to the extracted kernel.
"""
import argparse
import hashlib
import json
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
    parser.add_argument('--current',type=Path,help='use an isolated game.bin/game.lbl/assets.bin capture without rebuilding')
    parser.add_argument('--out',type=Path,help='write timings, deltas and artifact identities')
    args=parser.parse_args()
    if args.current:
        current_directory=args.current.resolve()
    else:
        game=DEV.parent/'light3dball'
        subprocess.run(['make','-s','-C',str(game)],check=True)
        current_directory=game/'build'
    with tempfile.TemporaryDirectory(prefix='pom2-corridor-bench-') as temp:
        work=Path(temp)
        current=probe(work,a2test.labels(current_directory/'game.lbl',strip=True),
                      current_directory/'game.bin',current_directory/'assets.bin')
        old=None
        if args.before:
            old=probe(work,a2test.labels(args.before/'game.lbl',strip=True),
                      args.before/'game.bin',args.before/'assets.bin')
        for family,minimum,maximum,total,count in current:
            name=('select','project X','project Y')[family]
            print(f'{name}: {minimum}..{maximum} cycles, mean {total/count:.3f}, {count} calls verified')
        if old is not None:
            # Each probe independently checks the complete public output domain.
            # Link layout can change timings; expose that change rather than
            # requiring the optimized kernel to keep the old measurements.
            assert [(v[0],v[4]) for v in current]==[(v[0],v[4]) for v in old]
            for before,after in zip(old,current):
                family,lo,hi,total,count=after
                name=('select','project X','project Y')[family]
                print(f'{name} delta: min {lo-before[1]:+d}, max {hi-before[2]:+d}, '
                      f'mean {(total-before[3])/count:+.6f} cycles/call')
            print('Before/after: both captures pass all public depth/span/coordinate checks.')
        if args.out:
            digest=lambda path:dict(name=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
            artifacts=lambda directory:[digest(directory/name) for name in ('game.bin','game.lbl','assets.bin')]
            version=subprocess.run(['ca65','--version'],capture_output=True,text=True,check=True)
            report=dict(schema=1,compiler=(version.stdout+version.stderr).strip(),
                        flags='native game capture; host probe -O2',cpu='NMOS6502',
                        current=dict(artifacts=artifacts(current_directory),results=current),
                        before=dict(artifacts=artifacts(args.before),results=old) if old is not None else None,
                        delta=[dict(family=a[0],minimum=a[1]-b[1],maximum=a[2]-b[2],
                                    total=a[3]-b[3],calls=a[4]) for b,a in zip(old,current)] if old is not None else None,
                        sources=[digest(__file__),digest(DEV/'bench/corridor_probe.c'),
                                 digest(DEV/'tools/a2run/cpu6502.c')])
            args.out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
