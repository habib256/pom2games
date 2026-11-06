#!/usr/bin/env python3
"""T80 scrolling: independent bank/holes/pointer model, repeated calls and IRQ mask.

The 19-row cases match MB TRACKER's grid in both three/six-voice layouts.
Each legal scenario runs three times without resetting the screen or pointer;
I alternates between clear/set while no interrupt source is installed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_hgr import DEV,compile_source,run,a2test

seed=bytearray([0xA5]*2048)
for bank in (0,1024):
 for row in range(24):
  for col in range(40):seed[bank+a2test.text_offset(row)+col]=(row*73+col*151+bank//1024*11)&255
ops=[]
for direction in (0,1,255):
 for rows in (0,1,2,3,8,24):
  for y in (0,7,16,23):
   for sw in (0,13,39):
    item=(direction,min(rows,24-y),y,sw)
    if item not in ops:ops.append(item)
ops += [(direction,19,3,sw) for direction in (0,1,255) for sw in (19,25)]

assembly = """.setcpu "65C02"
.export _reset, _capture, _done, _ready, _snapshot
.segment "LOWBSS"
_snapshot: .res 2048
.code
_reset:
    sta $C001
    bit $C054
    ldx #0
@main:
    lda _seed,x
    sta $0400,x
    lda _seed+256,x
    sta $0500,x
    lda _seed+512,x
    sta $0600,x
    lda _seed+768,x
    sta $0700,x
    inx
    bne @main
    bit $C055
    ldx #0
@aux:
    lda _seed+1024,x
    sta $0400,x
    lda _seed+1280,x
    sta $0500,x
    lda _seed+1536,x
    sta $0600,x
    lda _seed+1792,x
    sta $0700,x
    inx
    bne @aux
    bit $C054
    rts
_capture:
    bit $C054
    ldx #0
:   lda $0400,x
    sta _snapshot,x
    lda $0500,x
    sta _snapshot+256,x
    lda $0600,x
    sta _snapshot+512,x
    lda $0700,x
    sta _snapshot+768,x
    inx
    bne :-
    bit $C055
    ldx #0
:   lda $0400,x
    sta _snapshot+1024,x
    lda $0500,x
    sta _snapshot+1280,x
    lda $0600,x
    sta _snapshot+1536,x
    lda $0700,x
    sta _snapshot+1792,x
    inx
    bne :-
    bit $C054
    rts
_done: rts
_ready: lda _irq_mode
    beq @enabled
    sei
    bra @done
@enabled:cli
@done:
.export measure_begin
measure_begin:rts
.export _called,_page_flag,_irq_status
.import _irq_mode
.import _seed
.bss
_page_flag:.res 1
_irq_status:.res 1
.code
_called:php
    pla
    sta _irq_status
    lda $C01C
    sta _page_flag
    rts
"""

def flip(v):
 return v+192 if v<32 else v+128 if v<64 else 171 if v<96 else v+128 if v<128 else v-128 if v<192 else v-192 if v<224 else v-128


def check(work,kernel,pointer):
    version=kernel.name
    cases=[(*op,on,(i*37)%80,(op[2]+op[1]//2 if op[1] and i%2 else (i*17)%24)) for i,op in enumerate(ops) for on in ((0,1) if pointer else (0,))]
    source=work/'scroll.c'
    source.write_text('#include "apple2t80.h"\nvoid reset(void),capture(void),ready(void),called(void),done(void);unsigned char irq_mode;\n'
     'const unsigned char seed[2048]={'+','.join(map(str,seed))+'};\n'
     'static const struct {unsigned char down,rows,y,sw,on,px,py;} ops[]={'+','.join('{'+','.join(map(str,op))+'}' for op in cases)+'};\n'
     '#if T80_PTR\nextern unsigned char t80_ptr_save;\n#endif\n'
     'int main(void){unsigned i;unsigned char repeat;for(i=0;i<sizeof(ops)/sizeof(ops[0]);++i){'
     't80_init();reset();t80_x=ops[i].rows;t80_y=ops[i].y;t80_sw=ops[i].sw;'
     '\n#if T80_PTR\nt80_ptr_save=109;t80_ptr_x=ops[i].px;t80_ptr_y=ops[i].py;if(ops[i].on)t80_ptr_show();\n#endif\n'
     'for(repeat=0;repeat<3;++repeat){t80_x=ops[i].rows;t80_y=ops[i].y;t80_sw=ops[i].sw;irq_mode=(i+repeat)&1;ready();t80_scroll(ops[i].down);called();capture();done();}}for(;;){}return 0;}')
    marker=work/'capture.s';marker.write_text(assembly+('\n.import t80_ptr_save\n.export _t80_ptr_save := t80_ptr_save\n' if pointer else ''))
    sources=[DEV/'cc65/crt0_apple2.s',source,marker,kernel]+([DEV/'lib/apple2c/apple2t80_ptr.s'] if pointer else [])
    objects=[]
    for i,path in enumerate(sources):
     obj=work/f'{i}.o';compile_source(path,obj,['-t','none','--cpu','65c02','-Oirs','-I',DEV/'lib/apple2c','-D',f'T80_PTR={int(pointer)}','--asm-define',f'T80_PTR={int(pointer)}']);objects.append(obj)
    binary=work/'scroll.bin';label_file=work/'scroll.lbl'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',label_file,'-o',binary,*objects]);L=a2test.labels(label_file)
    cases=[op for op in cases for repeat in range(3)]
    steps=a2test.bin_steps(binary)
    for op in cases:
     steps += [L.until('measure_begin'),'hwstackwatch',L.until('_called'),'hwstack',L.until('_done'),L.peek('_snapshot',2048),L.peek('_t80_x'),L.peek('_t80_y')]
     if pointer:steps += [L.peek('_t80_ptr_on',2)]
     steps += [L.peek('_page_flag'),L.peek('_irq_status')]
    disk=work/'blank.dsk';disk.write_bytes(bytes(143360));result=a2test.run(disk,steps,iie=True)
    size=2054 if pointer else 2052;assert len(result.data)==size*len(cases)
    ticks=[int(c) for c in re.findall(r'cycles=(\d+)',result.out)]
    stacks=[tuple(map(int,m)) for m in re.findall(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',result.out)]
    assert len(ticks)==3*len(cases) and len(stacks)==len(cases),(len(ticks),len(stacks),len(cases))
    records=[]
    for i,(direction,rows,y,sw,on,px,py) in enumerate(cases):
     if i%3==0:underlying=seed.copy()
     expected=underlying.copy()
     if rows>1:
      row_order=range(y+rows-1,y,-1) if direction else range(y,y+rows-1)
      for dest in row_order:
       src=dest-1 if direction else dest+1
       for bank in (0,1024):
        dst=bank+a2test.text_offset(dest);start=bank+a2test.text_offset(src)
        expected[dst:dst+sw+1]=expected[start:start+sw+1]
     underlying=expected.copy()
     saved=109
     if on:
      at=(0 if px&1 else 1024)+a2test.text_offset(py)+px//2;saved=expected[at];expected[at]=flip(saved)
     actual=result.data[i*size:(i+1)*size]
     assert actual[:2048]==expected,(version,pointer,i,cases[i],'screen')
     final_y=y+rows-1 if rows>1 and not direction else y
     assert actual[2048:2050]==bytes((rows,final_y)),(version,pointer,i,'cursor')
     if pointer:assert actual[2050:2052]==bytes((on,saved)),(version,pointer,i,'pointer')
     assert actual[-2]&128==0,(version,pointer,i,'PAGE2 on exit')
     assert actual[-1]&12==(((i//3+i%3)&1)*4),(version,pointer,i,'I/D flags',actual[-1])
     peak,available,overflow=stacks[i];assert not overflow and peak<available
     records.append(dict(op=cases[i],cycles=ticks[i*3+1]-ticks[i*3]-12,hardware_stack_peak_bytes=peak,binary_bytes=binary.stat().st_size))
    print(f'T80 scroll pointer={pointer}: {len(cases)} repeated bank/holes/pointer/IRQ cases OK.')
    return records


def report(kernel,records):
    sys.path.insert(0,str(DEV/'bench'))
    import run as bench
    version=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
    digest=lambda path:dict(name=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
    results={}
    inputs={}
    for pointer,items in records.items():
        for index,record in enumerate(items):
            name=('pointer' if pointer else 'plain')+f'_{index:04d}'
            inputs[name]=dict(zip(('direction','rows','y','sw','visible','pointer_x','pointer_y'),record['op']))
            inputs[name].update(repeat=index%3,irq_mask=((index//3+index%3)&1))
            results[name]={key:value for key,value in record.items() if key!='op'}
    return dict(schema=1,scope='fastcall scroll including C argument fetch; video/pointer setup excluded',
                compiler=(version.stdout+version.stderr).strip(),flags='-t none --cpu 65c02 -Oirs; T80_PTR=0/1',
                source=digest(kernel),test_source=digest(__file__),
                support_sources=[digest(DEV/'lib/apple2c/apple2t80_ptr.s')],
                environments={'iie':bench.environment(True)},case_environments={name:'iie' for name in results},
                case_inputs=inputs,results=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,help='assemble this apple2t80.s instead')
    parser.add_argument('--bench',action='store_true',help='report cycles/loaded bytes/hardware stack for every case')
    parser.add_argument('--out',type=Path,help='write measurements (requires --bench)')
    args=parser.parse_args()
    if args.out and not args.bench:parser.error('--out requires --bench')
    kernel=(args.reference or DEV/'lib/apple2c/apple2t80.s').resolve()
    records={}
    with tempfile.TemporaryDirectory(prefix='t80-scroll-') as directory:
        root=Path(directory)
        for pointer in (False,True):
            work=root/str(pointer);work.mkdir()
            records[pointer]=check(work,kernel,pointer)
    if args.bench:
        measurement=report(kernel,records)
        print(f'{len(measurement["results"])} scroll measurements; both pointer modes, I=0/I=1.')
        if args.out:args.out.write_text(json.dumps(measurement,indent=2)+'\n')


if __name__=='__main__':main()
