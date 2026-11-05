#!/usr/bin/env python3
"""ProDOS MLI C entries: injected ABI oracle and real-volume integration.

Optional measurements cover complete calls through the injected MLI, with
device I/O excluded. The real-volume test separately verifies ProDOS dispatch,
parameters, returned data and repeated calls through the public globals.
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
from test_prodos_file import compile_asm

STUB='''
.export _stub_setup,_stub_error,_stub_failed,_seen
.bss
_stub_error:.res 1
_stub_failed:.res 1
_seen:.res 3
.code
_stub_setup:
 lda #$4C
 sta $BF00
 lda #<stub
 sta $BF01
 lda #>stub
 sta $BF02
 rts
; Read all three inline bytes and advance the caller's saved return address.
; Use no cc65 scratch; deliberately return nonzero X and arbitrary success A.
stub:
 tsx
 lda $0101,x
 sta fetch+1
 clc
 adc #3
 sta $0101,x
 lda $0102,x
 sta fetch+2
 adc #0
 sta $0102,x
 ldy #1
 jsr fetch
 sta _seen
 iny
 jsr fetch
 sta _seen+1
 iny
 jsr fetch
 sta _seen+2
 lda _stub_failed
 beq ok
 lda _stub_error
 ldx #$A5
 ldy #$37
 sec
 rts
ok:
 lda _stub_error
 ldx #$A5
 ldy #$37
 clc
 rts
fetch: lda $FFFF,y
 rts
'''

MARKERS='''
.export _checked_call,_checked_mli,_record,_ready,_prepared,checkpoint,resume,_stack_state
.import _prodos_call,_prodos_mli
.importzp sp
.bss
_record:.res 8
_stack_state:.res 6
.code
_checked_call:
 jsr _prodos_call
 sta _record
 stx _record+1
 rts
_checked_mli:
 jsr _prodos_mli
 sta _record
 stx _record+1
 rts
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
checkpoint:nop
resume:rts
'''


def injected(work,kernel):
    source=work/'calls.c'
    source.write_text('''#include "prodos.h"
void stub_setup(void);void ready(void);void prepared(void);
void checked_call(void);void __fastcall__ checked_mli(unsigned char,void*);
extern unsigned char stub_error,stub_failed,seen[3],record[8];
int main(void){unsigned i;unsigned char api,fail;
 stub_setup();if(prodos_command||prodos_params)for(;;){}ready();
 for(api=0;api<3;++api)for(fail=0;fail<2;++fail)for(i=0;i<256;++i){
  stub_error=(unsigned char)i^0x5A;stub_failed=fail;
  prodos_command=0xEE;prodos_params=(void*)0xFFFF;
  if(!api){prodos_command=(unsigned char)i;prodos_params=(void*)(i|((i^0xA5)<<8));checked_call();}
  else{checked_mli((unsigned char)i,(void*)(i|((i^0xA5)<<8)));if(api==2)checked_call();}
  record[2]=seen[0];record[3]=seen[1];record[4]=seen[2];
  record[5]=prodos_command;record[6]=(unsigned)prodos_params;record[7]=(unsigned)prodos_params>>8;
  prepared();
 }for(;;){}return 0;}''')
    stub=work/'stub.s'
    stub.write_text(STUB)
    markers=work/'markers.s'
    markers.write_text(MARKERS)
    disk=build(work,source,extra_sources=(kernel,DEV/'lib/prodos/mli_cmd.s',stub,markers),
               cflags=('-I',DEV/'lib/prodos'))
    labels=a2test.labels(work/'test.lbl')
    assert labels['_stack_state']==labels['_record']+8
    cases=[(api,fail,value) for api in range(3) for fail in range(2) for value in range(256)]
    steps=[labels.until('_ready')]
    for _ in cases:
        steps += [labels.until('checkpoint'),labels.peek('_record',14),labels.until('resume')]
    for iie in (False,True):
        result=a2test.run(disk,steps,iie=iie)
        assert len(result.data)==len(cases)*14
        for index,(api,fail,value) in enumerate(cases):
            data=result.data[index*14:(index+1)*14]
            expected=bytes((value ^ 0x5A if fail else 0,0,
                            value,value,value ^ 0xA5,value,value,value ^ 0xA5))
            assert data[:8]==expected,(iie,index,api,fail,value,'MLI bytes/return/globals',data)
            assert data[8]==data[9],(iie,index,'hardware stack balance',data)
            assert data[10:12]==data[12:14],(iie,index,'C stack balance',data)
        print(f'ProDOS MLI ({"IIe" if iie else "II+"}): {len(cases)} direct/fastcall/repeat states; '
              'all command/pointer/error bytes, initial/public globals, return X and stacks OK.')


def real_volume(work,kernel):
    work.mkdir()
    source=work/'main.s'
    assembly='''.setcpu "65C02"
.import _prodos_call,_prodos_mli,_prodos_command,_prodos_params
.importzp sp
.export done,results,high_results,p_prefix,p_open,p_read,p_eof,p_close,globals_seen
.code
entry:
 bit $C000
 bpl entry
 bit $C010
 cld
 lda #$FF
 ldx #3
protect:sta $BF5C,x
 dex
 bpl protect
 lda $BF60
 and #$3F
 sta $BF60
'''
    operations=((0xC7,'p_prefix',True),(0xC7,'p_prefix',False),
                (0xC8,'p_open',False),(0xCA,'p_read',True),
                (0xD1,'p_eof',False),(0xCC,'p_close',False),(0xC8,'p_open',False))
    for index,(command,params,fastcall) in enumerate(operations):
        if index==3:
            assembly+=''' lda p_open+5
 sta p_read+1
 sta p_eof+1
 sta p_close+1
'''
        if index==6:
            assembly+=''' lda #<missing
 sta p_open+1
 lda #>missing
 sta p_open+2
'''
        if fastcall:
            assembly+=f''' lda #$FE
 sta sp
 lda #$1F
 sta sp+1
 ldy #0
 lda #${command:02X}
 sta (sp),y
 lda #<{params}
 ldx #>{params}
 jsr _prodos_mli
'''
        else:
            if index!=1:  # Repeat GET_PREFIX using the previously stored globals.
                assembly+=f''' lda #${command:02X}
 sta _prodos_command
 lda #<{params}
 sta _prodos_params
 lda #>{params}
 sta _prodos_params+1
'''
            assembly+=' jsr _prodos_call\n'
        assembly+=f''' sta results+{index}
 stx high_results+{index}
 lda _prodos_command
 sta globals_seen+{index*3}
 lda _prodos_params
 sta globals_seen+{index*3+1}
 lda _prodos_params+1
 sta globals_seen+{index*3+2}
'''
    assembly+='''done:jmp done
p_prefix:.byte 1
 .word $1400
p_open:.byte 3
 .word name,$1000
 .byte 0
p_read:.byte 4,0
 .word $4000,512,0
p_eof:.byte 2,0,0,0,0
p_close:.byte 1,0
name:.byte 5,"MARKS"
missing:.byte 4,"NOPE"
results:.res 7,0
high_results:.res 7,0
globals_seen:.res 21,0
'''
    source.write_text(assembly)
    cfg=work/'main.cfg'
    cfg.write_text('MEMORY {ZP:start=$50,size=$B0,type=rw; RAM:start=$2000,size=$2000,type=rw,file=%O;}\n'
                   'SEGMENTS {ZEROPAGE:load=ZP,type=zp; CODE:load=RAM,type=ro; BSS:load=RAM,type=bss;}\n')
    objects=[]
    for index,path in enumerate((source,kernel,DEV/'lib/prodos/mli_cmd.s')):
        obj=work/f'{index}.o'
        compile_source(path,obj,['-t','none'])
        objects.append(obj)
    binary=work/'main.bin'
    label_file=work/'main.lbl'
    run(['cl65','-t','none','-C',cfg,'-Ln',label_file,'-o',binary,*objects])
    labels=a2test.labels(label_file)
    boot,_=compile_asm(work,'boot','.define SYSBOOT_FILE "TEST.SYS"\n'
                       '.define SYSBOOT_TITLE "PRODOS MLI TEST"\n.include "sysboot.s"\n',
                       config=(DEV/'cc65/prodos_sysboot.cfg').read_text())
    content=bytes((value*13+7)&255 for value in range(513))
    disk=a2test.prodos_volume(work/'test.po',{
        'PRODOS#FF0000':(DEV/'tools/prodos/PRODOS').read_bytes(),
        'TEST.SYS#FF2000':binary.read_bytes(),'TEST.SYSTEM#FF2000':boot.read_bytes(),
        'MARKS':content},'MLITEST')
    result=a2test.run(disk,['wait:1100','key: ',labels.until('done'),
        labels.peek('results',7),labels.peek('high_results',7),labels.peek('p_read',8),
        labels.peek('p_eof',5),labels.peek('globals_seen',21),'peek:4000:512'],iie=True)
    assert result.mem(labels['results'],7)==bytes((0,0,0,0,0,0,0x46)),'real MLI statuses'
    assert result.mem(labels['high_results'],7)==bytes(7),'real MLI return X'
    assert result.mem(labels['p_read'],8)[6:8]==b'\0\2','real READ count'
    assert result.mem(labels['p_eof'],5)[2:5]==b'\1\2\0','real GET_EOF'
    expected=b''.join(bytes((command,labels[params] & 255,labels[params] >> 8))
                      for command,params,_ in operations)
    assert result.mem(labels['globals_seen'],21)==expected,'real MLI public globals'
    assert result.mem(0x4000,512)==content[:512],'real READ payload'
    print('Real ProDOS: GET_PREFIX/repeated call, OPEN/READ/GET_EOF/CLOSE, missing-file error, '
          'public globals, zero return X and exact payload OK.')


def measure(work,bench,name,direct,command,pointer,error,failed,iie):
    setup=f'stub_setup();stub_error={error};stub_failed={failed};prodos_command={command};prodos_params=(void*){pointer}u;'
    call=('value=prodos_call();' if direct else f'value=prodos_mli({command},(void*){pointer}u);')
    source=work/(name+'.c')
    source.write_text('#include "prodos.h"\nvoid stub_setup(void);void bench_begin(void);void bench_end(void);\n'
        'extern unsigned char stub_error,stub_failed;static volatile unsigned value;\n'
        'int main(void){'+setup+'bench_begin();'+call+'bench_end();for(;;){}return 0;}')
    obj=source.with_suffix('.o')
    compile_source(source,obj,['-t','none','-Oirs','-I',DEV/'lib/prodos'])
    binary=source.with_suffix('.bin')
    mapfile=source.with_suffix('.map')
    label_file=source.with_suffix('.lbl')
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-m',mapfile,'-Ln',label_file,
         '-o',binary,work/'crt0_apple2.o',obj,work/'bench_marker.o',
         work/'apple2io_asm.o',work/'hgrc.lib'])
    labels=a2test.labels(label_file)
    disk=a2test.build_disk(work,'BENCH',binary)
    emulator=DEV/'tools'/('a2shot/a2shot' if iie else 'a2run/a2run')
    output=run([emulator,*(['--iie'] if iie else []),'--disk',disk,
        labels.until('_bench_begin',1500),'hwstackwatch',
        f'stackwatch:{labels["sp"]:02X}:{labels["__STACKSTART__"]:04X}:{labels["__STACKSIZE__"]:04X}',
        labels.until('_bench_end',1500),'stack','hwstack'])
    ticks=[int(value) for value in re.findall(r'cycles=(\d+)',output)]
    assert len(ticks)==2
    peak,reserved,overflow=map(int,re.search(r'stack peak=(\d+) reserved=(\d+) overflow=(\d+)',output).groups())
    hw_peak,hw_available,hw_overflow=map(int,re.search(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',output).groups())
    assert not overflow and peak<reserved,(name,'C stack overflow')
    assert not hw_overflow and hw_peak<hw_available,(name,'hardware stack overflow')
    return dict(bench.segments(mapfile),binary_bytes=binary.stat().st_size,cycles=ticks[1]-ticks[0]-12,
                c_stack_peak_bytes=peak,c_stack_reserved_bytes=reserved,
                hardware_stack_peak_bytes=hw_peak,hardware_stack_available_bytes=hw_available)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,help='assemble this original mli.s instead')
    parser.add_argument('--bench',action='store_true',help='measure complete calls through the injected MLI; device I/O excluded')
    parser.add_argument('--out',type=Path,help='write the injected-call measurement report (requires --bench)')
    args=parser.parse_args()
    if args.out and not args.bench:
        parser.error('--out requires --bench')
    kernel=(args.reference or DEV/'lib/prodos/mli.s').resolve()
    with tempfile.TemporaryDirectory(prefix='prodos-mli-') as directory:
        work=Path(directory)
        injected(work,kernel)
        real_volume(work/'real',kernel)
        if not args.bench:
            return
        sys.path.insert(0,str(DEV/'bench'))
        import run as bench
        marker=work/'bench_marker.s'
        marker.write_text('.export _bench_begin,_bench_end\n.code\n_bench_begin:rts\n_bench_end:rts\n')
        compile_source(marker,work/'bench_marker.o',['-t','none'])
        results={}
        environments={}
        for iie in (False,True):
            for direct in (False,True):
                for suffix,command,pointer,error,failed in (
                    ('success',0xC7,0x1234,0xA5,0),('error',0xCA,0x5678,0x27,1),
                    ('null',0x80,0,0,0),('high',255,65535,255,1),
                ):
                    name='prodos_mli_'+('direct_' if direct else 'fastcall_')+suffix+('_iie' if iie else '')
                    results[name]=measure(work,bench,name,direct,command,pointer,error,failed,iie)
                    environments[name]='iie' if iie else 'nmos'
                    m=results[name]
                    print(f'{name}: {m["cycles"]} cycles, {m["binary_bytes"]} loaded bytes, '
                          f'{m["ram_bytes"]} RAM, {m["zp_bytes"]} ZP; injected MLI, no device I/O.')
        version=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
        report=dict(schema=1,scope='C argument setup and complete direct/fastcall calls through an injected MLI; device I/O excluded',
            source=dict(name=kernel.name,sha256=hashlib.sha256(kernel.read_bytes()).hexdigest()),
            compiler=(version.stdout+version.stderr).strip(),flags='-Oirs',results=results,
            case_environments=environments,
            environments={name:bench.environment(name=='iie') for name in ('nmos','iie')})
        if args.out:
            args.out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
