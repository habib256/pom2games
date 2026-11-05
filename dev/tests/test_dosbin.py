#!/usr/bin/env python3
"""DOS binary commands: byte arguments, atomic overflow, stacks and preparation cost.

The oracle returns from a2_dos_run without running DOS. Measurements stop at
that entry, before DOS/COUT or disk device I/O. Actual device integration is
covered by SNAKE's record save/load test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_hgr import DEV, build, compile_source, run, a2test

CASES=[]
for value in range(256):
    CASES += [('HISCORE',value | ((value ^ 0xA5) << 8),None),
              ('HISCORE',value | ((value ^ 0x5A) << 8),value | ((255-value) << 8))]
for length in (0,1,19,20,26,27,39,40,255):
    CASES += [('A'*length,0x2000,None),('A'*length,0x2000,17)]

WORKLOADS=(
    ('load_zero','DATA',0,None),('load_high','DATA',65535,None),
    ('save_zero','SAVE',0,0),('save_high','SAVE',65535,65535),
    ('save_mixed','SAVE',0x1234,0xABCD),
    ('load_exact','A'*26,0x2000,None),('save_exact','A'*19,0x2000,17),
    ('load_overflow','A'*27,0x2000,None),('save_overflow','A'*20,0x2000,17),
)


def expected_command(name,address,length):
    """String appends clip by character; two-digit hex appends are atomic."""
    data=bytearray()
    overflow=False

    def append(value,atomic=False):
        nonlocal overflow
        if overflow:
            return
        if atomic and len(data)+len(value)>39:
            overflow=True
            return
        for char in value:
            if len(data)==39:
                overflow=True
                return
            data.append(char)

    append(b'BLOAD ' if length is None else b'BSAVE ')
    append(name.encode('ascii'))
    append(b',A$')
    append(f'{address >> 8:02X}'.encode('ascii'),True)
    append(f'{address & 255:02X}'.encode('ascii'),True)
    if length is not None:
        append(b',L$')
        append(f'{length >> 8:02X}'.encode('ascii'),True)
        append(f'{length & 255:02X}'.encode('ascii'),True)
    return bytes(data)+b'\0',overflow


def check(work,kernel):
    source=work/'calls.c'
    source.write_text('#include "apple2dos.h"\nvoid ready(void);void prepared(void);\n'
        'static const struct {const char *name; unsigned addr,len; unsigned char save;} cases[]={'+
        ','.join('{"%s",%du,%du,%d}' % (name,addr,length or 0,length is not None)
                 for name,addr,length in CASES)+
        '};\nint main(void){unsigned i;ready();for(i=0;i<sizeof(cases)/sizeof(cases[0]);++i){'
        'if(cases[i].save)a2_dos_bsave(cases[i].name,(void*)cases[i].addr,cases[i].len);'
        'else a2_dos_bload(cases[i].name,(void*)cases[i].addr);prepared();}'
        'for(;;){}return 0;}')
    helper=work/'apple2dos_asm.s'
    helper.write_text('.export dos_cmd_buf,dos_cmd_ix,dos_cmd_overflow,dos_zp_prog\n'+
                      (DEV/'lib/apple2c/apple2dos_asm.s').read_text())
    markers=work/'markers.s'
    markers.write_text('''.export _ready,_prepared,checkpoint,resume,_stack_state
.importzp sp
.bss
_stack_state: .res 6
.code
_ready:
 tsx
 stx _stack_state
 lda sp
 sta _stack_state+2
 lda sp+1
 sta _stack_state+3
 rts
_prepared:
 tsx
 stx _stack_state+1
 lda sp
 sta _stack_state+4
 lda sp+1
 sta _stack_state+5
checkpoint: nop
resume: rts
''')
    disk=build(work,source,extra_sources=(helper,kernel,markers))
    labels=a2test.labels(work/'test.lbl')
    assert labels['dos_cmd_ix']==labels['dos_cmd_buf']+40
    assert labels['dos_cmd_overflow']==labels['dos_cmd_buf']+41
    steps=[labels.until('_ready'),labels.poke('_a2_dos_run',0x60),
           *labels.poke('dos_zp_prog',bytes([0xA5])*256)]
    for _ in CASES:
        steps += [labels.until('checkpoint'),labels.peek('dos_cmd_buf',42),
                  labels.peek('dos_zp_prog',256),labels.peek('_stack_state',6),
                  labels.until('resume')]
    for iie in (False,True):
        result=a2test.run(disk,steps,iie=iie)
        assert len(result.data)==len(CASES)*304
        for index,case in enumerate(CASES):
            text,overflow=expected_command(*case)
            frame=result.data[index*304:(index+1)*304]
            assert frame[:len(text)]==text,(iie,index,case,'command bytes')
            assert frame[40]==len(text)-1,(iie,index,case,'index')
            assert frame[41]==overflow,(iie,index,case,'overflow')
            assert frame[42:298]==bytes([0xA5])*256,(iie,index,'buffer overrun')
            state=frame[298:304]
            assert state[0]==state[1],(iie,index,'hardware stack balance',state)
            assert state[2:4]==state[4:6],(iie,index,'C stack balance',state)
        print(f'DOS binary commands ({"IIe" if iie else "II+"}): {len(CASES)} cases; '
              'all argument bytes, name bounds, atomic overflow, guards and stacks OK.')


def measure(work,bench,name,filename,address,length,iie):
    call=(f'a2_dos_bload("{filename}",(void*){address}u);' if length is None else
          f'a2_dos_bsave("{filename}",(void*){address}u,{length}u);')
    source=work/(name+'.c')
    source.write_text('#include "apple2dos.h"\nvoid bench_begin(void);\n'
                      'int main(void){bench_begin();'+call+'for(;;){}return 0;}')
    obj=source.with_suffix('.o')
    compile_source(source,obj,['-t','none','-Oirs','-I',DEV/'lib/apple2c'])
    binary=source.with_suffix('.bin')
    mapfile=source.with_suffix('.map')
    label_file=source.with_suffix('.lbl')
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-m',mapfile,
         '-Ln',label_file,'-o',binary,work/'crt0_apple2.o',obj,work/'bench_marker.o',
         work/'apple2io_asm.o',work/'hgrc.lib'])
    labels=a2test.labels(label_file)
    disk=a2test.build_disk(work,'BENCH',binary)
    emulator=DEV/'tools'/('a2shot/a2shot' if iie else 'a2run/a2run')
    output=run([emulator,*(['--iie'] if iie else []),'--disk',disk,
                labels.until('_bench_begin',1500),'hwstackwatch',
                f'stackwatch:{labels["sp"]:02X}:{labels["__STACKSTART__"]:04X}:{labels["__STACKSIZE__"]:04X}',
                labels.until('_a2_dos_run',1500),'stack','hwstack'])
    ticks=[int(c) for c in re.findall(r'cycles=(\d+)',output)]
    assert len(ticks)==2
    peak,reserved,overflow=map(int,re.search(r'stack peak=(\d+) reserved=(\d+) overflow=(\d+)',output).groups())
    hw_peak,hw_available,hw_overflow=map(int,re.search(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',output).groups())
    assert not overflow and peak<reserved,(name,'C stack overflow')
    assert not hw_overflow and hw_peak<hw_available,(name,'hardware stack overflow')
    # The interval contains the entry marker's RTS, with no exit-marker JSR.
    return dict(bench.segments(mapfile),binary_bytes=binary.stat().st_size,
                cycles=ticks[1]-ticks[0]-6,c_stack_peak_bytes=peak,
                c_stack_reserved_bytes=reserved,hardware_stack_peak_bytes=hw_peak,
                hardware_stack_available_bytes=hw_available)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,help='assemble this original apple2dosbin.s instead')
    parser.add_argument('--bench',action='store_true',help='measure argument setup/preparation before DOS device I/O')
    parser.add_argument('--out',type=Path,help='write the preparation measurement report (requires --bench)')
    args=parser.parse_args()
    if args.out and not args.bench:
        parser.error('--out requires --bench')
    kernel=(args.reference or DEV/'lib/apple2c/apple2dosbin.s').resolve()
    with tempfile.TemporaryDirectory(prefix='dosbin-test-') as directory:
        work=Path(directory)
        check(work,kernel)
        if not args.bench:
            return
        sys.path.insert(0,str(DEV/'bench'))
        import run as bench
        marker=work/'bench_marker.s'
        marker.write_text('.export _bench_begin\n.code\n_bench_begin:rts\n')
        compile_source(marker,work/'bench_marker.o',['-t','none'])
        results={}
        environments={}
        for iie in (False,True):
            for suffix,filename,address,length in WORKLOADS:
                name='dosbin_prepare_'+suffix+('_iie' if iie else '')
                results[name]=measure(work,bench,name,filename,address,length,iie)
                environments[name]='iie' if iie else 'nmos'
                m=results[name]
                print(f'{name}: {m["cycles"]} cycles, {m["binary_bytes"]} loaded bytes, '
                      f'{m["ram_bytes"]} RAM, {m["zp_bytes"]} ZP; before DOS device I/O.')
        version=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
        report=dict(schema=1,scope='C argument setup and command preparation, ending at a2_dos_run entry before DOS/COUT device I/O',
                    source=dict(name=kernel.name,sha256=hashlib.sha256(kernel.read_bytes()).hexdigest()),
                    compiler=(version.stdout+version.stderr).strip(),flags='-Oirs',
                    results=results,case_environments=environments,
                    environments={name:bench.environment(name=='iie') for name in ('nmos','iie')})
        if args.out:
            args.out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
