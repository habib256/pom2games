#!/usr/bin/env python3
"""T80 init: real 65C02 bus/state, cold/warm repeated calls and guarded stacks.

The void C entry may clobber A/X/Y and arithmetic flags. I/D must remain
unchanged. The model checks the complete display switch sequence, every
visible cell once, screen holes, cursor/pointer state, tables and both stacks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from test_hgr import DEV,run,a2test

BUS=Path(__file__).with_name('t80_init_bus.cpp')


def check(work,kernel):
    host=work/'bus'
    run(['make','-s','-C',DEV/'tools/a2shot','probe',f'SRC={BUS}',f'OUT={host}'])
    defs=work/'defs.s'
    defs.write_text('.exportzp ptr1,ptr2,tmp1,tmp2,sp\nptr1=$50\nptr2=$52\ntmp1=$54\ntmp2=$55\nsp=$56\n.export popa\n.code\npopa:rts\n')
    run(['ca65','-o',work/'defs.o',defs])
    config=work/'init.cfg'
    # Match the current MB TRACKER init entry, including branch-page placement.
    config.write_text('MEMORY{RAM:start=$6528,size=$2AD8,type=rw,file=%O;}'
                      'SEGMENTS{CODE:load=RAM,type=ro;DATA:load=RAM,type=rw;BSS:load=RAM,type=bss;}')
    results={}
    for pointer in (False,True):
        run(['ca65','-g','-D',f'T80_PTR={int(pointer)}','-o',work/'t80.o',kernel])
        objects=[work/'defs.o',work/'t80.o']
        if pointer:
            run(['ca65','-g','-o',work/'ptr.o',DEV/'lib/apple2c/apple2t80_ptr.s'])
            objects.append(work/'ptr.o')
        binary=work/f'init_{pointer}.bin';label_file=binary.with_suffix('.lbl')
        run(['ld65','-C',config,'-Ln',label_file,'-o',binary,*objects])
        labels=a2test.labels(label_file)
        names=('_t80_init','_t80_x','_t80_y','_t80_mode','_t80_sw')
        args=[f'{labels[name]:04X}' for name in names]
        args += [f'{labels[name]:04X}' if pointer else '0' for name in ('_t80_ptr_x','_t80_ptr_y','_t80_ptr_on')]
        output=run([host,binary,'6528',*args,DEV/'tools/a2shot/roms/apple2e.rom'])
        rows=[tuple(map(int,line.split())) for line in output.splitlines()]
        assert len(rows)==16*3*2 and labels['_t80_init']==0x6529
        for flags,scenario,repeat,cycles,hardware,software in rows:
            name=f'{"pointer" if pointer else "plain"}_{flags:02x}_{scenario}_{repeat}'
            results[name]=dict(cycles=cycles,binary_bytes=binary.stat().st_size,
                               hardware_stack_peak_bytes=hardware,c_stack_peak_bytes=software)
        print(f'T80 init pointer={pointer}: {len(rows)} cold/warm/repeated C/I/V/D states; '
              'exact switch/stores, holes/tables, cursor/pointer, I/D and stacks OK.')
    return results


def report(kernel,results):
    sys.path.insert(0,str(DEV/'bench'))
    import run as bench
    version=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
    host=subprocess.run(['c++','--version'],capture_output=True,text=True,check=True)
    digest=lambda path:dict(name=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
    return dict(schema=1,scope='direct T80 init at MBT entry $6529, real 65C02 bus; injected return frame excluded',
                source=digest(kernel),test_source=digest(__file__),
                support_sources=[digest(BUS),digest(DEV/'lib/apple2c/apple2t80_ptr.s'),digest(DEV/'tools/a2shot/sdk/include/pom2/core.hpp')],
                compiler=(version.stdout+version.stderr).strip(),flags='ca65 T80_PTR=0/1; ld65 $6528',
                host_compiler=host.stdout.strip(),host_flags='SDK make probe: C++17 -O2',
                environments={'iie':bench.environment(True)},case_environments={name:'iie' for name in results},
                initial_flags=dict(C=[0,1],I=[0,1],V=[0,1],D=[0,1]),
                scenarios=['cold','warm main-selected','warm aux-selected'],repeats=2,
                software_stack=dict(pointer=0x56,first=0xB800,last=0xBFFF),results=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,help='assemble this apple2t80.s instead')
    parser.add_argument('--bench',action='store_true')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    if args.out and not args.bench:parser.error('--out requires --bench')
    kernel=(args.reference or DEV/'lib/apple2c/apple2t80.s').resolve()
    with tempfile.TemporaryDirectory(prefix='t80-init-') as directory:
        results=check(Path(directory),kernel)
    if args.bench:
        measurement=report(kernel,results)
        if args.out:args.out.write_text(json.dumps(measurement,indent=2)+'\n')


if __name__=='__main__':main()
