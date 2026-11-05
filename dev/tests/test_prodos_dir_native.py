#!/usr/bin/env python3
"""Compare native directory listing with portable C, including real ProDOS.

Measured calls use an injected MLI; disk device I/O is excluded. The separate
real-volume checks exercise resident/OVL2 code and data with LOWBSS buffers.
"""
import argparse
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_hgr import DEV, compile_source, run, a2test
from test_prodos_file import compile_asm


@dataclass(frozen=True)
class Case:
    maximum: int = 3
    stride: int = 16
    suffix_len: int = 0
    entry_len: int = 39
    per_block: int = 13
    blocks: int = 2
    got: int = 512
    prefix_error: int = 0
    open_error: int = 0
    read_error: int = 0
    close_error: int = 0
    style: int = 0

    def fields(self):
        return (self.maximum,self.stride,self.suffix_len,self.entry_len,self.per_block,
                self.blocks,self.got & 255,self.got >> 8,self.prefix_error,self.open_error,
                self.read_error,self.close_error,self.style)


FILTER=Case(suffix_len=4)
NAMED=[
    ('filter',FILTER),('limit',replace(FILTER,maximum=1)),('all',Case()),
    ('no_match',Case(suffix_len=5)),('long_match',Case(suffix_len=14,style=1)),
    ('suffix15',Case(suffix_len=15)),('suffix255',Case(suffix_len=255)),
    ('empty',Case(maximum=0)),('wide_stride',replace(FILTER,stride=255)),
    ('short511',replace(FILTER,got=511)),('short0',replace(FILTER,got=0)),
    ('prefix_error',replace(FILTER,prefix_error=0x27)),
    ('open_error',replace(FILTER,open_error=0x46)),
    ('read_error',replace(FILTER,read_error=0x27,close_error=0x43)),
    ('eof_close_error',replace(FILTER,read_error=0x4C,close_error=0x43)),
    ('close_error',Case(suffix_len=5,close_error=0x43)),
    ('per0',replace(FILTER,per_block=0)),('per1',replace(FILTER,per_block=1)),
    *[(f'entry{length}',Case(entry_len=length,per_block=255,style=2))
      for length in (255,1)],
    ('entry0',Case(entry_len=0,style=2)),
    ('max255',Case(maximum=255,entry_len=0,per_block=255,style=2)),
    *[(f'entry{length}',Case(entry_len=length,per_block=255,style=2))
      for length in (15,16,38,40,127,128)],
]


def matrix():
    cases=[]
    for value in range(256):
        cases += [(f'entry_len{value}',Case(entry_len=value,per_block=255,style=2)),
                  (f'per_block{value}',Case(per_block=value)),
                  (f'max{value}',Case(maximum=value,entry_len=0,per_block=255,style=2)),
                  (f'suffix{value}',Case(suffix_len=value,style=1))]
        for field in ('prefix_error','open_error','read_error','close_error'):
            errors={field:value}
            if field!='close_error':
                errors['close_error']=0x43
            cases.append((f'{field}{value}',Case(**errors)))
    cases += [(f'stride{value}',replace(FILTER,stride=value)) for value in range(16,256)]
    for value in range(16):
        cases += [(f'storage{value}',Case(style=128+value)),
                  (f'name_len{value}',Case(style=32+value))]
    cases += [(f'prefix_shape{value}',Case(style=value)) for value in (64,65,66)]
    return cases


def execute(work,cases,kernel):
    work.mkdir()
    (work/'prodos_dir_cases.inc').write_text(',\n'.join(
        '{'+','.join(map(str,case.fields()))+'}' for _,case in cases))
    marker=work/'markers.s'
    marker.write_text('.export _bench_begin,_bench_end,_prepared,resume\n.code\n'
                      '_bench_begin:rts\n_bench_end:rts\n_prepared:nop\nresume:rts\n')
    objects=[]
    for index,source in enumerate((DEV/'cc65/crt0_apple2.s',
        DEV/'tests/prodos_dir_native_fixture.c',marker,DEV/'lib/prodos/mli_cmd.s',kernel)):
        obj=work/f'{index}.o'
        compile_source(source,obj,['-t','none','-g','-Oirs','-I',work,'-I',DEV/'lib/prodos'])
        objects.append(obj)
    binary=work/'test.bin'
    mapfile=work/'test.map'
    label_file=work/'test.lbl'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-m',mapfile,
         '-Ln',label_file,'-o',binary,*objects])
    labels=a2test.labels(label_file)
    disk=a2test.build_disk(work,'DIRECTORY',binary)
    steps=[]
    for _ in cases:
        steps += [labels.until('_bench_begin'),'hwstackwatch',
            f'stackwatch:{labels["sp"]:02X}:{labels["__STACKSTART__"]:04X}:{labels["__STACKSIZE__"]:04X}',
            labels.until('_bench_end'),'stack','hwstack',labels.until('_prepared'),
            labels.peek('_result',2),labels.peek('_prodos_dir_count'),labels.peek('_trace_n'),
            labels.peek('_trace',16),labels.peek('_storage',4096),labels.until('resume')]
    sys.path.insert(0,str(DEV/'bench'))
    import run as bench
    sizes=bench.segments(mapfile)
    results={}
    for iie in (False,True):
        output=a2test.run(disk,steps,iie=iie)
        ticks=[int(value) for value in re.findall(r'cycles=(\d+)',output.out)]
        stacks=[tuple(map(int,m)) for m in re.findall(
            r'(?m)^stack peak=(\d+) reserved=(\d+) overflow=(\d+)',output.out)]
        hardware=[tuple(map(int,m)) for m in re.findall(
            r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',output.out)]
        assert len(ticks)==len(cases)*4
        assert len(output.data)==len(cases)*4116
        for index,(name,_) in enumerate(cases):
            peak,reserved,overflow=stacks[index]
            hw_peak,hw_available,hw_overflow=hardware[index]
            assert not overflow and peak<reserved,(name,'C stack overflow')
            assert not hw_overflow and hw_peak<hw_available,(name,'hardware stack overflow')
            key=name+('_iie' if iie else '')
            metrics=dict(sizes,binary_bytes=binary.stat().st_size,
                cycles=ticks[index*4+1]-ticks[index*4]-12,c_stack_peak_bytes=peak,
                c_stack_reserved_bytes=reserved,hardware_stack_peak_bytes=hw_peak,
                hardware_stack_available_bytes=hw_available)
            results[key]=(metrics,output.data[index*4116:(index+1)*4116])
    return results


def expected_payload(case,status,names,commands):
    storage=bytearray([0xA5])*4096
    for index,name in enumerate(names):
        data=name.encode('ascii')+b'\0'
        offset=8+index*case.stride
        storage[offset:offset+len(data)]=data
    return (bytes((status,0,len(names),len(commands)))+
            bytes(commands).ljust(16,b'\0')+storage)


def check_named(results):
    reads=(0xC7,0xC8,0xCA,0xCA,0xCC)
    eof=(0xC7,0xC8,0xCA,0xCA,0xCA,0xCC)
    empty=[]
    names=['FIRST.AYS','SECOND.AYS','THIRD.AYS']
    expected={
        'filter':(0,names,reads),'all':(0,names,reads),'wide_stride':(0,names,reads),
        'limit':(0,names[:1],(0xC7,0xC8,0xCA,0xCC)),
        'no_match':(0,empty,eof),'long_match':(0,['A123456789ABCDE'],eof),
        'suffix15':(0,empty,()),'suffix255':(0,empty,()),'empty':(0,empty,()),
        'short511':(0,empty,(0xC7,0xC8,0xCA,0xCC)),
        'short0':(0,empty,(0xC7,0xC8,0xCA,0xCC)),
        'prefix_error':(0x27,empty,(0xC7,)),
        'open_error':(0x46,empty,(0xC7,0xC8)),
        'read_error':(0x27,empty,(0xC7,0xC8,0xCA,0xCC)),
        'eof_close_error':(0x43,empty,(0xC7,0xC8,0xCA,0xCC)),
        'close_error':(0x43,empty,eof),
    }
    for name,case in NAMED:
        if name not in expected:
            continue
        payload=expected_payload(case,*expected[name])
        for suffix in ('','_iie'):
            assert results[name+suffix][1]==payload,(name+suffix,'independent expected result/trace/guards')


def compare_batch(work,cases,kernel):
    work.mkdir()
    reference=execute(work/'reference',cases,DEV/'lib/prodos/dir.c')
    actual=execute(work/'actual',cases,kernel)
    for key,(metrics,payload) in actual.items():
        old,expected=reference[key]
        assert payload==expected,(key,'C/native status, count, MLI order or output/guards')
        for field in ('zp_bytes','c_stack_peak_bytes','hardware_stack_peak_bytes'):
            assert metrics[field]<=old[field],(key,field,old[field],metrics[field])
    return actual


def placement(work,kernel,overlay):
    if kernel.suffix.lower()=='.c':
        flags=['--bss-name','LOWBSS']
        if overlay:
            flags+=['--code-name','OVL2','--rodata-name','OVL2','--data-name','OVL2']
        return kernel,flags
    wrapper=work/'placed_dir.s'
    wrapper.write_text('PRODOS_DIR_CUSTOM_SEGMENTS=1\n'+
        f'.define PRODOS_DIR_CODE_SEGMENT "{"OVL2" if overlay else "CODE"}"\n'+
        f'.define PRODOS_DIR_DATA_SEGMENT "{"OVL2" if overlay else "DATA"}"\n'+
        '.define PRODOS_DIR_BSS_SEGMENT "LOWBSS"\n.include '+json.dumps(kernel.name)+'\n')
    return wrapper,['--asm-include-dir',str(kernel.parent)]


def real_volume(work,kernel,overlay):
    work.mkdir()
    source=work/'main.c'
    source.write_text('''#include <string.h>
#include "prodos.h"
void prepared(void);
#pragma bss-name(push,"IOBUF")
static unsigned char iobuf[1024];
#pragma bss-name(pop)
void *prodos_file_iobuf=iobuf;
unsigned char names[255][16],scene;unsigned status;
static const char *suffixes[]={".AYS",".AYS",".BIN",".NONE","A123456789ABCDE",""};
static const unsigned char limits[]={8,1,8,8,8,255};
int main(void){unsigned i;for(i=0;i<14;++i)*(unsigned char*)(0xBF5Cu+i)=255;
 *(unsigned char*)0xBF5A=0;*(unsigned char*)0xBF5B=0;
 for(scene=0;scene<6;++scene){memset(names,0xA5,sizeof(names));
 status=prodos_dir_list((char*)names,16,limits[scene],suffixes[scene]);prepared();}
 for(;;){}return 0;}''')
    marker=work/'marker.s'
    marker.write_text('.export _prepared,resume\n.code\n_prepared:nop\nresume:rts\n')
    placed,extra=placement(work,kernel,overlay)
    cfg=work/'main.cfg'
    config=(DEV/'cc65/apple2_hgr_c.cfg').read_text().replace('$6000','$2000')
    config=config.replace('    LOWBSS:',
        '    IOBUF: load = LOWRAM, type = bss, align = $100;\n    LOWBSS:')
    if overlay:
        config=config.replace('    CODE:','    OVL2: load = RAM, type = ro;\n    CODE:')
    cfg.write_text(config)
    objects=[]
    for index,path in enumerate((DEV/'cc65/crt0_apple2.s',source,marker,
        DEV/'lib/prodos/mli.s',DEV/'lib/prodos/mli_cmd.s',placed)):
        flags=['-t','none','--cpu','65c02','-Ors','--static-locals','-I',DEV/'lib/prodos']
        if path==placed:
            flags+=extra
        obj=work/f'{index}.o'
        compile_source(path,obj,flags)
        objects.append(obj)
    binary=work/'main.bin'
    label_file=work/'main.lbl'
    run(['cl65','-t','none','-C',cfg,'-Ln',label_file,'-o',binary,*objects])
    labels=a2test.labels(label_file)
    boot,_=compile_asm(work,'boot','.define SYSBOOT_FILE "TEST.SYS"\n'
        '.define SYSBOOT_TITLE "PRODOS DIRECTORY TEST"\n.include "sysboot.s"\n',
        config=(DEV/'cc65/prodos_sysboot.cfg').read_text())
    files={'PRODOS#FF0000':(DEV/'tools/prodos/PRODOS').read_bytes(),
        'TEST.SYS#FF2000':binary.read_bytes(),'TEST.SYSTEM#FF2000':boot.read_bytes(),
        'A.AYS':b'A','B.AYS':b'B','C.AYS':b'C','D.BIN#060000':b'D'}
    disk=a2test.prodos_volume(work/'test.po',files,'DIRTEST')
    steps=[]
    for _ in range(6):
        steps += [labels.until('_prepared'),labels.peek('_status',2),
            labels.peek('_prodos_dir_count'),labels.peek('_names',4080),labels.until('resume')]
    output=a2test.run(disk,steps,iie=True)
    expected=[['A.AYS','B.AYS','C.AYS'],['A.AYS'],['D.BIN'],[],[],
              ['A.AYS','B.AYS','C.AYS','D.BIN','PRODOS','TEST.SYS','TEST.SYSTEM']]
    assert len(output.data)==6*4083
    for index,names in enumerate(expected):
        data=output.data[index*4083:(index+1)*4083]
        assert data[:3]==bytes((0,0,len(names))),(overlay,index,'real status/count')
        storage=bytearray([0xA5])*4080
        for row,name in enumerate(names):
            storage[row*16:row*16+len(name)+1]=name.encode('ascii')+b'\0'
        assert data[3:]==storage,(overlay,index,'real names/order/guards')
    print(f'Real ProDOS directory: filter/full/boundary/long suffix, LOWBSS, '
          f'{"OVL2 code/data" if overlay else "resident code/data"} OK.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,help='test/measure this C or native directory source instead')
    parser.add_argument('--quick',action='store_true',help='skip the additional 2,323-case byte-domain matrix')
    parser.add_argument('--bench',action='store_true',help='report the named injected-MLI workloads; device I/O excluded')
    parser.add_argument('--out',type=Path,help='write measurement report (requires --bench)')
    args=parser.parse_args()
    if args.out and not args.bench:
        parser.error('--out requires --bench')
    kernel=(args.reference or DEV/'lib/prodos/dir_list.s').resolve()
    with tempfile.TemporaryDirectory(prefix='prodos-dir-native-') as directory:
        work=Path(directory)
        named=compare_batch(work/'named',NAMED,kernel)
        check_named(named)
        checked=len(NAMED)
        if not args.quick:
            cases=matrix()
            for offset in range(0,len(cases),150):
                compare_batch(work/f'matrix{offset}',cases[offset:offset+150],kernel)
                checked+=len(cases[offset:offset+150])
        print(f'ProDOS directory: {checked} paired cases per CPU; C/native output, '
              'memory guards, MLI order/error cleanup and stack bounds match (II+/IIe).')
        real_volume(work/'resident',kernel,False)
        real_volume(work/'overlay',kernel,True)
        if not args.bench:
            return
        results={'prodos_dir_'+name:metrics for name,(metrics,_) in named.items()}
        for name,metrics in results.items():
            print(f'{name}: {metrics["cycles"]} cycles, {metrics["binary_bytes"]} loaded bytes, '
                  f'{metrics["ram_bytes"]} RAM; injected MLI, no device I/O.')
        sys.path.insert(0,str(DEV/'bench'))
        import run as bench
        version=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
        report=dict(schema=1,scope='Complete C directory calls through an injected MLI; device I/O excluded',
            source=dict(name=kernel.name,sha256=hashlib.sha256(kernel.read_bytes()).hexdigest()),
            compiler=(version.stdout+version.stderr).strip(),flags='-Oirs',paired_cases_per_cpu=checked,
            results=results,case_environments={name:'iie' if name.endswith('_iie') else 'nmos' for name in results},
            environments={name:bench.environment(name=='iie') for name in ('nmos','iie')})
        if args.out:
            args.out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
