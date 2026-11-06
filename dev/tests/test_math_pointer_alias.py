#!/usr/bin/env python3
"""Quarter-square operand/pointer aliases: products, cached calls and ABI guards.

Use --reference REV or --reference path/to/mul.asm for a paired timing proof.
Both CPU models run independently; default/other/unknown pointer relationships
must retain the reference bytes. Boot INIT placement is covered separately.
"""
import argparse
import hashlib
import json
import os
import shlex
from pathlib import Path
import subprocess
import tempfile
from test_hgr import DEV, run
from test_verlet_ground_probes import identity, metadata

FIELDS = ('mul_x', 'mul_x+1', 'mul_y', 'mul_p0', 'mul_p1', 'mul_p2', 'mul_t',
          'mul_s1l', 'mul_s1l+1', 'mul_s1h', 'mul_s1h+1', 'mul_s2l',
          'mul_s2l+1', 'mul_s2h', 'mul_s2h+1', 'mul_acc0', 'mul_acc1', 'mul_acc2')
LAYOUTS = {'default': '', 'coalesced': 'mul_y=mul_s1l\n',
           'other_pointer': 'mul_y=mul_s1h\n', 'absolute': 'mul_y=$3000\n',
           # Separate absolute/relocatable expressions are deliberately unknown
           # to ca65, even though the linker happens to put both at $56.
           'unknown': 'mul_y=$56\n'}
REFERENCES = {'u8': ('mul_u8u8',), 'u16': ('mul_u16u8',),
              'inline': ('mul_s16s8', 'mul_dir'),
              'shared': ('mul_s16s8', 'mul_u16u8', 'mul_u8u8', 'mul_dir')}
CONFIG = '''MEMORY { ZP:start=$50,size=$b0,type=rw;
RAM:start=$6000,size=$3000,type=rw,file=%O; }
SEGMENTS { ZEROPAGE:load=ZP,type=zp; CODE:load=RAM,type=ro;
INIT:load=RAM,type=ro,optional=yes; RODATA:load=RAM,type=ro; }
'''


def build(work, kernel, layout, kind, boot=False):
    work.mkdir()
    (work/'selected_mul.asm').write_bytes(kernel)
    names = REFERENCES[kind]
    source = LAYOUTS[layout] + ('MUL_INIT_BOOT=1\n' if boot else '') + '''MUL_TABLES=$0800
MUL_ACC=1
.include "math.inc"
.code
start:jmp start
.rodata
references:.word ''' + ','.join(names+('div16by8',)) + '''
.code
.include "div.asm"
.include "selected_mul.asm"
.code
set_y: MUL_SET_POINTERS
 rts
cached: MUL_LOW_BYTE
 rts
.export mul_init,start,set_y,cached,div16by8
.export ''' + ','.join(dict.fromkeys(f.replace('+1', '') for f in FIELDS)) + f'''
.export entry
entry={names[0]}
''' + ('.export mul_dir\n' if kind in ('inline', 'shared') else '')
    if kind == 'shared':
        source += '.export mul_u8u8,mul_u16u8\n'
    (work/'f.s').write_text(source)
    (work/'f.cfg').write_text(CONFIG)
    run(['ca65', '-I', work, '-I', DEV/'lib/math', '-o', work/'f.o', work/'f.s'])
    run(['ld65', '-C', work/'f.cfg', '-Ln', work/'f.lbl', '-o', work/'f.bin', work/'f.o'])
    return (work/'f.bin').read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEV/'lib/math/mul.asm')
    parser.add_argument('--reference', help='git revision or mul.asm file')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    selected = source.read_bytes()
    if not args.reference:
        reference = selected
    elif Path(args.reference).is_file():
        reference = Path(args.reference).read_bytes()
    else:
        reference = subprocess.run(['git', '-C', str(DEV.parent), 'show',
            args.reference+':dev/lib/math/mul.asm'], check=True, capture_output=True).stdout
    helper = DEV/'bench/math_pointer_alias_probe.cpp'
    report = dict(metadata=metadata(source, True), source=identity(source),
                  reference_sha256=hashlib.sha256(reference).hexdigest(),
                  support_sources=[identity(helper), identity(DEV/'lib/math/math.inc'),
                                   identity(DEV/'lib/math/div.asm'), identity(DEV/'tools/a2shot/probe.hpp')],
                  config_sha256=hashlib.sha256(CONFIG.encode()).hexdigest(), profiles={})
    report['metadata']['test_sha256'] = identity(__file__)['sha256']
    compiler = shlex.split(os.environ.get('CXX', 'c++'))
    report['metadata']['native_compiler'] = subprocess.run(
        [*compiler, '--version'], check=True, capture_output=True, text=True).stdout.strip()
    report['metadata']['native_flags'] = '-std=c++17 -O2; dev/tools/a2shot/sdk.mk'
    report['metadata'].pop('probe_config_sha256')
    report['metadata']['environment']['model'] = 'SDK NMOS6502 and CMOS65C02, direct RAM calls'
    with tempfile.TemporaryDirectory(prefix='math-pointer-alias-') as temporary:
        work = Path(temporary)
        executable = work/'probe'
        run(['make', '-s', '-C', DEV/'tools/a2shot', 'probe',
             'SRC='+str(helper), 'OUT='+str(executable)])
        sizes = {}
        profiles = [(layout, kind, False) for layout in LAYOUTS for kind in REFERENCES]
        profiles += [(layout, 'shared', True) for layout in ('default', 'coalesced')]
        for layout, kind, boot in profiles:
            name = layout+'_'+kind+('_boot' if boot else '')
            before, after = work/(name+'-before'), work/(name+'-after')
            old = build(before, reference, layout, kind, boot)
            new = build(after, selected, layout, kind, boot)
            if layout != 'coalesced':
                assert old == new, (name, 'fallback bytes changed')
            sizes[layout, kind, boot] = len(new)
            entry = dict(before_bytes=len(old), after_bytes=len(new),
                         before_sha256=hashlib.sha256(old).hexdigest(),
                         after_sha256=hashlib.sha256(new).hexdigest(), cpus={})
            for cpu, label in ((0, 'NMOS6502'), (1, 'CMOS65C02')):
                proof = run([executable, before/'f.bin', before/'f.lbl', after/'f.bin',
                    after/'f.lbl', cpu, {'u8':0, 'u16':1, 'inline':2, 'shared':2}[kind],
                    int(layout == 'coalesced' and not boot)]).strip()
                print(name, proof)
                entry['cpus'][label] = proof
            report['profiles'][name] = entry
        # Each fixture also emits an explicit cached setter. The shared variant
        # emits two public product setters; the others emit just one.
        for kind in REFERENCES:
            assert sizes['default', kind, False]-sizes['coalesced', kind, False] == (6 if kind == 'shared' else 4)
        assert sizes['default', 'shared', True]-sizes['coalesced', 'shared', True] == 6
    if args.out:
        args.out.write_text(json.dumps(report, indent=2)+'\n')
    print('22 pointer/INIT profiles on both CPUs: PASS')


if __name__ == '__main__':
    main()
