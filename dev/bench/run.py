#!/usr/bin/env python3
"""Measure real cc65 calls (including argument setup), linker code/RAM/ZP.

HGR runs on portable a2run (NMOS); DHGR on a2shot --iie (65C02).
Use --check for regression gates, --update to intentionally accept a baseline.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_hgr import DEV, ROOT, build, run

CASES={
 'hgr_clear': ('hgr_clear(0);',False),
 'hgr_span': ('hgr_hline(0,279,40);',False),
 'hgr_rect': ('hgr_fill_pixrect(7,32,140,16);',False),
 'hgr_text': ('hgr_puts8(0,0,"APPLE II");',False),
 'hgr_sprite7': ('hgr_blit7(0,40,4,8,bits,HGR_SET);',False),
 'dhgr_clear': ('dhgr_clear(9);',True),
 'dhgr_span': ('dhgr_hline(0,559,40,1);',True),
 'dhgr_rect': ('dhgr_fill_rect(7,32,70,16,9);',True),
 'dhgr_block': ('dhgr_write_block(0,40,8,8,bits,8);',True),
 'dhgr_sprite': ('dhgr_sprite(7,40,2,2,2,bits,bits);',True),
 'dhgr_text': ('dhgr_puts("APPLE II",0,0);',True),
}
BASELINE=Path(__file__).with_name('baseline.json')


def segments(mapfile):
    section=mapfile.read_text().split('Segment list:')[1].split('Exports list')[0]
    sizes={m[1]:int(m[2],16) for m in re.finditer(r'^([A-Z][A-Z0-9_]*)\s+[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]+)',section,re.M)}
    return dict(code_bytes=sizes.get('CODE',0)+sizes.get('STARTUP',0),
                rodata_bytes=sizes.get('RODATA',0),
                ram_bytes=sum(sizes.get(s,0) for s in ('BSS','LOWBSS','DATA','ZPSAVE')),
                zp_bytes=sizes.get('ZEROPAGE',0))


def measure(work,name,call,dhgr):
    source=work/(name+'.c'); obj=source.with_suffix('.o'); binary=source.with_suffix('.bin')
    source.write_text('#include "hgr.h"\n#include "dhgr.h"\n#include "apple2io.h"\n'
      'void hgr_build_tables(void); void bench_begin(void); void bench_end(void);\n'
      'static const unsigned char bits[64]={127,85,42,127};\nint main(void) {\n'+
      ('if (!dhgr_init()) return 1;' if dhgr else 'hgr_init(); hgr_build_tables();')+
      '\nbench_begin();\n'+call+
      '\nbench_end();\napple2_getkey(); return 0; }\n')
    run(['cl65','-t','none','-Oirs','-I',DEV/'lib/hgrc','-I',DEV/'lib/apple2c','-c','-o',obj,source])
    mapfile=source.with_suffix('.map'); labels=source.with_suffix('.lbl')
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-m',mapfile,'-Ln',labels,
         '-o',binary,work/'crt0_apple2.o',obj,work/'markers.o',work/'apple2io_asm.o',work/'hgrc.lib'])
    points=dict((name,int(addr,16)) for addr,name in re.findall(r'al ([0-9A-Fa-f]+) \.(_bench_\w+)',labels.read_text()))
    hello=work/'hello.bas';hello.write_text('10 PRINT CHR$(4);"BRUN BENCH"\n')
    disk=source.with_suffix('.dsk')
    run(['python3',DEV/'tools/dos33.py','--master',DEV/'tools/dos33_system.bin','--out',disk,
         '--bas',f'HELLO={hello}','--bin',f'BENCH={binary}@0x6000'])
    emulator=DEV/'tools'/('a2shot/a2shot' if dhgr else 'a2run/a2run')
    output=run([emulator,*(['--iie'] if dhgr else []),'--disk',disk,
                f'until:{points["_bench_begin"]:04X}:1500',f'until:{points["_bench_end"]:04X}:1500'])
    ticks=[int(c) for c in re.findall(r'cycles=(\d+)',output)]
    assert len(ticks)==2
    return dict(segments(mapfile),binary_bytes=binary.stat().st_size,cycles=ticks[1]-ticks[0]-12)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dhgr',action='store_true'); ap.add_argument('--check',action='store_true')
    ap.add_argument('--update',action='store_true'); ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    if args.check and args.update:ap.error('choose --check or --update')
    run(['make','-s','-C',DEV/'tools/a2run'])
    with tempfile.TemporaryDirectory(prefix='apple2-bench-') as directory:
        work=Path(directory); build(work)
        markers=work/'markers.s'
        markers.write_text('.export _bench_begin, _bench_end\n.segment "CODE"\n_bench_begin: rts\n_bench_end: rts\n')
        run(['ca65','-t','none','-o',work/'markers.o',markers])
        results={name:measure(work,name,call,dhgr) for name,(call,dhgr) in CASES.items() if args.dhgr or not dhgr}
    import subprocess
    version_result=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
    version=(version_result.stdout+version_result.stderr).strip()
    report=dict(compiler=version,flags='-Oirs',results=results)
    for name,metrics in results.items():
        print(f'{name:16} {metrics["cycles"]:8} cycles  {metrics["binary_bytes"]:5} B binary  '+
              f'{metrics["code_bytes"]:5} B code  {metrics["ram_bytes"]:4} B RAM  {metrics["zp_bytes"]:3} B ZP')
    baseline=json.loads(BASELINE.read_text()) if BASELINE.exists() else dict(compiler=version,flags='-Oirs',results={})
    if args.update:
        baseline['compiler']=version;baseline['results'].update(results)
        BASELINE.write_text(json.dumps(baseline,indent=2)+'\n')
    if args.out:args.out.write_text(json.dumps(report,indent=2)+'\n')
    if args.check:
        failures=[]
        # Small compiler differences are permitted, concrete regressions fail.
        for name,metrics in results.items():
            if name not in baseline['results']:failures.append(name+': missing baseline');continue
            for key,value in metrics.items():
                old=baseline['results'][name][key]
                margin=max(16,int(old*.05)) if key=='cycles' else 0 if key=='zp_bytes' else max(16,int(old*.03))
                if value>old+margin:failures.append(f'{name}.{key}: {value} > {old}+{margin}')
        if failures:raise SystemExit('\n'.join(failures))
        print('Performance budgets passed.')

if __name__=='__main__':main()
