#!/usr/bin/env python3
"""Projection bounds and cc65 call costs, including 16-bit shift rejection."""
import argparse, hashlib, subprocess, sys, re, json, tempfile
from pathlib import Path
from test_hgr import DEV,compile_source,run,a2test
sys.path.insert(0,str(DEV/'bench'))
import run as bench

def measure(source,iie,full=False):
    with tempfile.TemporaryDirectory(prefix='projection-bench-') as tmp:
        work=Path(tmp)
        c=work/'fixture.c'; c.write_text('''#include "perspective.h"
unsigned x,shift; unsigned char scale,sy,result;
a2_projected_t point;
a2_perspective_t camera={&scale,&shift,&sy,1};
void done(void);
void probe(void){result=a2_perspective_project(&camera,x,0,&point);}
int main(void){done();return 0;}
''')
        m=work/'marker.s';m.write_text('.export _done\n.code\n_done:rts\n')
        objects=[]
        for j,s in enumerate((DEV/'cc65/crt0_apple2.s',c,m,source)):
            o=work/f'{j}.o';compile_source(s,o,['-t','none','-Oirs','-I',DEV/'lib/perspective']);objects.append(o)
        binary=work/'p.bin';lab=work/'p.lbl';mapfile=work/'p.map'
        run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',lab,'-m',mapfile,'-o',binary,*objects])
        labels=a2test.labels(lab)
        cases={}
        for x in (0,1,140,255,256,279):
            for scale in (range(256) if full else (0,1,127,255)):
                projected=x*(scale or 256)//256
                for shift in (0,279-projected,280-projected,280,65535):
                    name=f'x{x}_q{scale}_s{shift}';cases[name]=(x,scale,shift,191)
        cases['bad_y']=(279,0,0,192)
        initial=[labels.until('_done',3000)] if iie else a2test.bin_steps(binary)+[labels.until('_done',3000)]
        disk=a2test.build_disk(work,'PROJ',binary) if iie else None
        report={}
        for first in range(0,len(cases),128):
            chunk=dict(list(cases.items())[first:first+128])
            steps=list(initial)
            for x,scale,shift,sy in chunk.values():
                for name,value in (('_x',x.to_bytes(2,'little')),('_shift',shift.to_bytes(2,'little')),('_scale',bytes([scale])),('_sy',bytes([sy])),('_point',b'\x34\x12\x56')):
                    steps+=a2test.pokes(labels[name],value)
                steps += ['hwstackwatch',f'stackwatch:{labels["sp"]:02X}:{labels["__STACKSTART__"]:04X}:{labels["__STACKSIZE__"]:04X}',f'call:{labels["_probe"]:04X}:2',labels.peek('_result',1),labels.peek('_point',3),'hwstack','stack']
            r=a2test.run(disk,steps,iie=iie,timeout=180)
            cycles=re.findall(r'call [0-9A-F]+ cycles=\d+ elapsed=(\d+)',r.out)
            assert len(cycles)==len(chunk),(len(cycles),len(chunk))
            sizes=bench.segments(mapfile);sizes['binary_bytes']=binary.stat().st_size
            c_stacks=re.findall(r'^stack peak=(\d+) reserved=(\d+) overflow=(\d+)',r.out,re.M)
            hw_stacks=re.findall(r'^hwstack peak=(\d+) available=(\d+) overflow=(\d+)',r.out,re.M)
            assert len(c_stacks)==len(hw_stacks)==len(chunk)
            for peak,capacity,overflow in c_stacks+hw_stacks:
                assert int(overflow)==0 and int(peak)<int(capacity)
            for i,(name,(x,q,s,y)) in enumerate(chunk.items()):
                px=x*(q or 256)//256+s;valid=px<=279 and y<=191
                assert r.dumps[i][:1]==bytes([valid]),name
                assert r.dumps[i][1:]==(bytes((px&255,px>>8,y)) if valid else b'\x34\x12\x56'),name
                report[name]=dict(sizes,cycles=int(cycles[i]),c_stack_peak_bytes=int(c_stacks[i][0]),
                                  hardware_stack_peak_bytes=int(hw_stacks[i][0]))
        return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--full',action='store_true',help='all 256 scale bytes at input/shift boundaries')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    source=(args.reference or DEV/'lib/perspective/perspective.c').resolve()
    results=measure(source,args.iie,args.full)
    version=subprocess.run(['cl65','--version'],text=True,capture_output=True,check=True)
    digest=lambda p:dict(name=Path(p).name,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    report=dict(schema=1,scope='complete C wrapper call, outside disk IO',
                source=digest(source),test_source=digest(__file__),
                support_sources=[digest(DEV/'cc65/crt0_apple2.s'),digest(DEV/'lib/perspective/perspective.h')],
                compiler=(version.stdout+version.stderr).strip(),flags='-t none -Oirs',
                environment=bench.environment(args.iie),results=results)
    if args.out:args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(f'{len(results)} projection boundary calls: independent products/sums and untouched rejected outputs OK')


if __name__=='__main__':main()
