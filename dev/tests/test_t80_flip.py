#!/usr/bin/env python3
"""80-column inversion: all screen bytes, registers/flags, pointer banks and cost."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_hgr import DEV, compile_source, run, a2test
import test_t80_bounds as bounds


def check(work, kernel):
    source=work/'pointer.s'
    source.write_text(kernel.read_text())
    obj=work/'pointer.o'
    compile_source(source,obj,['-t','none'])
    defs=work/'defs.s'
    defs.write_text('''.exportzp ptr1
ptr1=$50
.export t80_rowlo,t80_rowhi,prepare
 t80_rowlo=$9000
 t80_rowhi=$9100
.code
prepare: cld
 sei
 clv
 rts
''')
    compile_source(defs,work/'defs.o',['-t','none'])
    config=work/'flip.cfg'
    config.write_text('MEMORY{RAM:start=$6000,size=$3000,type=rw,file=%O;}'
                      'SEGMENTS{CODE:load=RAM,type=ro;BSS:load=RAM,type=bss;}')
    binary=work/'flip.bin'
    labels_file=work/'flip.lbl'
    run(['ld65','-C',config,'-Ln',labels_file,'-o',binary,obj,work/'defs.o'])
    labels=a2test.labels(labels_file)
    disk=work/'empty.dsk';disk.write_bytes(bytes(143360))
    steps=[f'load:{binary}@6000',*a2test.pokes(0,bytes([0xA5])*256),'hwstackwatch']
    for value in range(256):
        steps += [f'call:{labels["prepare"]:04X}:2',f'regs:{value:02X}:5A:A5',
                  f'call:{labels["t80_flip"]:04X}:2']
    steps += ['peek:0000:256','hwstack']
    result=a2test.run(disk,steps,iie=True)
    rows=re.findall(r'call ([0-9A-F]+) cycles=\d+ elapsed=(\d+) A=([0-9A-F]+) X=([0-9A-F]+) Y=([0-9A-F]+) P=([0-9A-F]+)',result.out)
    rows=[row for row in rows if int(row[0],16)==labels['t80_flip']]
    assert len(rows)==256
    metrics={}
    for value,row in enumerate(rows):
        _,cycles,a,x,y,p=row
        a,x,y,p=(int(v,16) for v in (a,x,y,p))
        # Independent screen-code ranges, including MouseText's '+' replacement.
        expected=(value+192 if value<32 else value+128 if value<64 else
                  171 if value<96 else value+128 if value<128 else
                  value-128 if value<192 else value-192 if value<224 else value-128)
        carry=int(96<=value<128 or value>=192)
        flags=0x24 | (expected & 128) | (2 if expected==0 else 0) | carry
        assert (a,x,y,p)==(expected,0x5A,0xA5,flags),(value,a,x,y,p,expected,flags)
        metrics[f'{value:02x}']=dict(cycles=int(cycles),binary_bytes=binary.stat().st_size)
    assert result.data==bytes([0xA5])*256,'inversion changed zero page'
    peak,available,overflow=map(int,re.search(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',result.out).groups())
    assert peak==2 and not overflow and peak<available
    print('T80 flip: all 256 outputs, A/X/Y/P, zero page and balanced hardware stack OK.')
    return metrics


def pointer_bounds(work,kernel):
    original=bounds.compile_source
    def selected(source,obj,flags):
        if Path(source).name=='apple2t80_ptr.s':source=kernel
        return original(source,obj,flags)
    bounds.compile_source=selected
    try:
        bounds.check(work,True)
    finally:
        bounds.compile_source=original


def benchmark(work,kernel):
    sys.path.insert(0,str(DEV/'bench'))
    import run as bench
    bench.build(work)
    marker=work/'markers.s'
    marker.write_text('.export _bench_begin,_bench_end\n.code\n_bench_begin:rts\n_bench_end:rts\n')
    run(['ca65','-t','none','-o',work/'markers.o',marker])
    original=bench.run
    def selected(args,**kwargs):
        args=[kernel if str(arg)==str(DEV/'lib/apple2c/apple2t80_ptr.s') else arg for arg in args]
        return original(args,**kwargs)
    bench.run=selected
    try:
        return {name:bench.measure(work,name,**options) for name,options in bench.SCENES.items()
                if name.startswith('t80_')}
    finally:
        bench.run=original



def report(kernel,helper,results):
    sys.path.insert(0,str(DEV/'bench'))
    import run as bench
    version=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
    digest=lambda path:dict(name=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
    return dict(schema=1,scope='direct helper and text operations after video/pointer setup',
                source=digest(kernel),test_source=digest(__file__),
                support_sources=[digest(bounds.__file__),digest(DEV/'lib/apple2c/apple2t80.s'),
                                 digest(DEV/'bench/run.py')],
                compiler=(version.stdout+version.stderr).strip(),flags='-Oirs',
                helper_flags='ca65 via cl65 -t none; source selects 65C02',
                environments={'iie':bench.environment(True)},
                case_environments={name:'iie' for name in results},
                helper_case_environments={name:'iie' for name in helper},
                helper=helper,results=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,help='assemble this pointer source instead')
    parser.add_argument('--bench',action='store_true',help='also measure the standard 22 text profiles')
    parser.add_argument('--out',type=Path,help='write helper and text measurements (requires --bench)')
    args=parser.parse_args()
    if args.out and not args.bench:parser.error('--out requires --bench')
    kernel=(args.reference or DEV/'lib/apple2c/apple2t80_ptr.s').resolve()
    with tempfile.TemporaryDirectory(prefix='t80-flip-') as directory:
        work=Path(directory)
        helper=check(work,kernel)
        pointer_bounds(work,kernel)
        results=benchmark(work,kernel) if args.bench else {}
    if args.bench:
        measurement=report(kernel,helper,results)
        for name,metrics in results.items():print(name,metrics['cycles'],'cycles')
        if args.out:args.out.write_text(json.dumps(measurement,indent=2)+'\n')


if __name__=='__main__':main()
