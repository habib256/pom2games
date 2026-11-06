#!/usr/bin/env python3
"""AYS active-volume paths: independent output/state guards on both CPUs.

Every @vmute arrival must already have ays_von bit 7 set. The paired reference
retains the former defensive load/branch; all registers, state, flags and stack
peaks must agree. By default that reference is reconstructed from the selected
source, so the test also works outside a Git checkout. --reference REV_OR_PATH
selects a saved source instead. Three mutants validate the route, output and
protected-store assertions. Ordered hardware writes remain in test_aysong.py
and test_mb_irq.py; this probe observes complete ticks without AY hardware.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import subprocess
import tempfile
from test_hgr import DEV, run

ENTRY = '@vmute: lda ays_bits,x'
GUARDED = '@vmute: lda ays_von,x\n        bpl @v0\n        lda ays_bits,x'
SOURCE = '''AYSONG_VOICES={voices}
AYSONG_FAST_PERIODS={fast}
AYSONG_CPU65C02={c02}
{cpu}
.macro AYSONG_WRITE
.endmacro
.bss
guard_before:.res 1
.code
start:rts
.word ays_tick
.include "selected_aysong.asm"
.bss
guard_after:.res 1
.export start
'''


def identity(path):
    path = Path(path)
    return dict(name=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def build(work, kernel, voices, fast, c02):
    work.mkdir()
    (work/'selected_aysong.asm').write_text(kernel)
    (work/'f.s').write_text(SOURCE.format(voices=voices, fast=fast, c02=c02,
                                        cpu='.setcpu "65C02"' if c02 else ''))
    run(['ca65', '-g', '-I', work, '-o', work/'f.o', work/'f.s'])
    run(['ld65', '-C', DEV/'cc65/apple2_hgr.cfg', '-Ln', work/'f.lbl',
         '-o', work/'f.bin', work/'f.o'])
    return work/'f.bin', work/'f.lbl'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEV/'lib/apple2/aysong.asm')
    parser.add_argument('--reference', help='Git revision or saved aysong.asm')
    parser.add_argument('--out', type=Path, help='write source identities and proofs')
    args = parser.parse_args()
    source = args.source.resolve()
    selected = source.read_text()
    assert selected.count(ENTRY) == 1, 'expected the active-volume entry once'
    if not args.reference:
        reference = selected.replace(ENTRY, GUARDED)
        reference_kind = 'selected source with the former defensive guard restored'
    elif Path(args.reference).is_file():
        reference = Path(args.reference).read_text()
        reference_kind = str(args.reference)
    else:
        reference = subprocess.check_output(['git', '-C', str(DEV.parent), 'show',
            args.reference+':dev/lib/apple2/aysong.asm'], text=True)
        reference_kind = str(args.reference)
    helper = DEV/'bench/aysong_volume_probe.cpp'
    compiler = shlex.split(os.environ.get('CXX', 'c++'))
    report = dict(source=identity(source), test=identity(__file__), helper=identity(helper),
                  reference=reference_kind,
                  reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),
                  fixture_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
                  linker_config=identity(DEV/'cc65/apple2_hgr.cfg'),
                  probe_header=identity(DEV/'tools/a2shot/probe.hpp'),
                  compiler=subprocess.check_output([*compiler, '--version'], text=True).strip(),
                  flags='-std=c++17 -O2; dev/tools/a2shot/sdk.mk', profiles={}, mutants={})
    # Expected assertion failures must never leave core files in the workspace.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with tempfile.TemporaryDirectory(prefix='aysong-volume-') as temporary:
        work = Path(temporary)
        executable = work/'probe'
        run(['make', '-s', '-C', DEV/'tools/a2shot', 'probe',
             'SRC='+str(helper), 'OUT='+str(executable)])
        first_reference = None
        for voices in (3, 6):
            for fast in (0, 1):
                for c02 in (0, 1):
                    name = f'{voices}-voice-fast{fast}-cpu{c02}'
                    before = build(work/(name+'-before'), reference, voices, fast, c02)
                    after = build(work/(name+'-after'), selected, voices, fast, c02)
                    old_size, new_size = before[0].stat().st_size, after[0].stat().st_size
                    assert old_size-new_size == 5, (name, old_size, new_size)
                    proof = run([executable, *before, *after, c02, voices, fast]).strip()
                    print(proof, flush=True)
                    report['profiles'][name] = dict(before_bytes=old_size, after_bytes=new_size,
                                                   before=identity(before[0]), after=identity(after[0]), proof=proof)
                    if first_reference is None:
                        first_reference = before
        mutants = {
            'silent-route': (
                selected.replace('jmp @v0                 ; retained volume offset cannot unmute it',
                                 'jmp @vol                ; deliberately wrong silent route'),
                'ays_von'),
            'wrong-mute': (selected.replace('and ays_mutem\n        beq @v1',
                                           'and ays_mutem\n        bne @v1'), 'volume'),
            'protected-store': (selected.replace(ENTRY, '@vmute: sta $2006\n        lda ays_bits,x'),
                                'allowed[target]'),
        }
        for name, (mutant, assertion) in mutants.items():
            assert mutant != selected, (name, 'mutation did not apply')
            after = build(work/('mutant-'+name), mutant, 3, 0, 0)
            result = subprocess.run([str(x) for x in
                [executable, *first_reference, *after, 0, 3, 0]],
                text=True, capture_output=True, cwd=work)
            assert result.returncode != 0 and assertion in result.stderr, (name, result.stderr)
            report['mutants'][name] = dict(returncode=result.returncode, stderr=result.stderr.strip(),
                                           source_sha256=hashlib.sha256(mutant.encode()).hexdigest())
            print(name+': rejected by '+assertion+' assertion', flush=True)
    if args.out:
        args.out.write_text(json.dumps(report, indent=2)+'\n')
    print('AYS volume: 780288 paired ticks on both CPUs, all entry paths, output/state/stack guards and 3 mutants PASS')


if __name__ == '__main__':
    main()
