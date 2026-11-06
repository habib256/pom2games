#!/usr/bin/env python3
"""Independent LZ4FH overlap, page-crossing, literal and full-output oracles.

Both CPU models run every match length at two code placements, three input
alignments and both 8K output pages. All main RAM outside documented scratch
and output is guarded; returned A/X/Y/P and the hardware stack are checked.
--reference REV compares a historical source; --source substitutes a candidate.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from test_hgr import DEV, ROOT, run

KERNEL = DEV / 'lib/apple2/lz4fh.asm'


def build(work, source, base):
    work.mkdir()
    (work / 'kernel.asm').write_text(Path(source).read_text())
    entry = work / 'entry.s'
    # The second fixture uses Dirtbike's actual borrowed ZP layout, ending at $FF.
    aliases = '' if base == 0x6000 else '''lz4fh_src=$D7
lz4fh_dst=$D9
lz4fh_read=$F8
lz4fh_write=$FA
lz4fh_match=$FC
lz4fh_token=$FE
lz4fh_length=$FF
'''
    entry.write_text(aliases + '.include "kernel.asm"\n'
                     '.exportzp lz4fh_src,lz4fh_dst,lz4fh_read,lz4fh_write,lz4fh_match,lz4fh_token,lz4fh_length\n'
                     '.export unpack:=LZ4FH::unpack,_desthi:=LZ4FH::_desthi\n')
    config = work / 'entry.cfg'
    config.write_text(f'''MEMORY {{
 ZP:start=$50,size=$B0,type=rw;
 RAM:start=${base:04x},size=$3000,type=rw,file=%O;
}}
SEGMENTS {{ ZEROPAGE:load=ZP,type=zp; CODE:load=RAM,type=ro; }}
''')
    run(['ca65', '-g', '-I', work, '-o', work / 'entry.o', entry])
    run(['ld65', '-C', config, '-o', work / 'entry.bin',
         '-Ln', work / 'entry.lbl', work / 'entry.o'])
    return work


def command(executable, before, after, cpu, base):
    return [executable, before / 'entry.bin', before / 'entry.lbl',
            after / 'entry.bin', after / 'entry.lbl', cpu, base]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--reference', help='git revision for the old source')
    group.add_argument('--source', type=Path, help='candidate source to compare')
    parser.add_argument('--negative', action='store_true', help='validate fault detectors')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='lz4fh-native-') as directory:
        work = Path(directory)
        before, after = KERNEL, args.source or KERNEL
        if args.reference:
            before = work / 'reference.asm'
            before.write_bytes(subprocess.check_output(
                ['git', 'show', args.reference + ':dev/lib/apple2/lz4fh.asm'], cwd=ROOT))
        executable = work / 'probe'
        run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
             'SRC=' + str(DEV / 'bench/lz4fh_probe.cpp'), 'OUT=' + str(executable)])
        for base in (0x6000, 0x60f1):
            old = build(work / f'before-{base}', before, base)
            new = build(work / f'after-{base}', after, base)
            print(f'${base:04x}: {old.joinpath("entry.bin").stat().st_size} -> '
                  f'{new.joinpath("entry.bin").stat().st_size} loaded bytes', flush=True)
            for cpu in (0, 1):
                print(run(command(executable, old, new, cpu, base)).strip(), flush=True)
        if args.negative:
            text = Path(after).read_text()
            mutations = {
                'overlap': text.replace('iny\ndex\nbne nohi5__copyloop',
                                        'nop\ndex\nbne nohi5__copyloop', 1),
                'advance': text.replace('tya                             ; copied length',
                                        'txa                             ; copied length', 1),
                'stack': text.replace('unpack:\n', 'unpack:\nsta $01fd\n', 1),
                'parity': text.replace('bcc copied', 'bcs copied', 1),
                'carry': text.replace('clc\ncopied:', 'sec\ncopied:', 1),
            }
            for name, mutation in mutations.items():
                assert mutation != text, ('missing mutation marker', name)
                source = work / f'{name}.asm'
                source.write_text(mutation)
                bad = build(work / name, source, base)
                result = subprocess.run(list(map(str, command(executable, old, bad, 0, base))),
                                        capture_output=True, text=True)
                assert result.returncode and 'assert' in result.stderr.lower(), (name, result.stderr)
                print('LZ4FH negative control:', name, 'rejected', flush=True)


if __name__ == '__main__':
    main()
