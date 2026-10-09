#!/usr/bin/env python3
"""Measure real cc65 calls (including argument setup), linker code/RAM/ZP.

HGR runs on portable a2run (NMOS); DHGR on a2shot --iie (65C02).
Use --check for regression gates, --update to intentionally accept a baseline.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from functools import lru_cache
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_hgr import DEV, ROOT, build, run, a2test

CASES={
 'hgr_clear': ('hgr_clear(0);',False),
 'hgr_span': ('hgr_hline(0,279,40);',False),
 'hgr_rect': ('hgr_fill_pixrect(7,32,140,16);',False),
 'hgr_text': ('hgr_puts8(0,0,"APPLE II");',False),
 'hgr_sprite7': ('hgr_blit7(0,40,4,8,bits,HGR_SET);',False),
 'hgr_diagonal': ('hgr_line(0,0,279,191);',False),
 'gfx_diagonal': ('gfx_line(0,0,279,191);',False),
 'dhgr_clear': ('dhgr_clear(9);',True),
 'dhgr_span': ('dhgr_hline(0,559,40,1);',True),
 'dhgr_rect': ('dhgr_fill_rect(7,32,70,16,9);',True),
 'dhgr_block': ('dhgr_write_block(0,40,8,8,bits,8);',True),
 'dhgr_sprite': ('dhgr_sprite(7,40,2,2,2,bits,bits);',True),
 'dhgr_text': ('dhgr_puts("APPLE II",0,0);',True),
 'dhgr_clear_row': ('dhgr_clear_rows(40,1,9);',True),
}
# First call and steady-state frame workloads have their own budgets.
HUD = 'hgr_puts8(0,0,"SCORE"); hgr_putu_field(48,0,12345u,5); hgr_putu_field(160,0,42u,3);'
SPRITE_SETUP = '''
if (!hgr_spr_init_pool(1,pool,sizeof(pool),4,8)) return 2;
for (i=0; i<4; ++i) {
    if (!hgr_spr_define(i,&shape)) return 3;
    hgr_spr_move(i,28u+i*3u,60u+i*2u);
}
'''
FRAME = '''
for (i=0; i<4; ++i) hgr_spr_move(i,28u+i*3u+(frame&1u),60u+i*2u);
hgr_spr_render(); hgr_putu_field(48,0,frame,5); hgr_spr_present(); ++frame;
'''
SCENES = {
 'hgr_diagonal_cold': dict(call='hgr_line(0,0,279,191);', warmup=False),
 'hgr_hud_cold': dict(call=HUD, warmup=False),
 'hgr_hud_warm': dict(call=HUD),
 'hgr_scene_cold': dict(call=FRAME, setup=SPRITE_SETUP, sprites=True, warmup=False),
 # Two warm-up frames populate both pages' save-under history.
 'hgr_scene_warm': dict(call=FRAME, setup=SPRITE_SETUP, sprites=True, warmup=2),
}
SCENES.update({
 'hgr_hud_cached_same': dict(call='hgr_hud_putu(&hud,12345u);',
     setup='hgr_hud_init(&hud,48,0,5);', declarations='static hgr_hud_field_t hud;'),
 'hgr_hud_cached_digit': dict(call='hgr_hud_putu(&hud,12346u);',warmup=False,
     setup='hgr_hud_init(&hud,48,0,5); hgr_hud_putu(&hud,12345u);',
     declarations='static hgr_hud_field_t hud;'),
})
for phase in range(7):
    SCENES['hgr_scene_phase'+str(phase)] = dict(sprites=True, sprite_height=8,
        sprite_width=7, sprite_stride=2, warmup=2,
        declarations='static hgr_hud_field_t hud;',
        setup='hgr_hud_init(&hud,48,0,5);'+
        'if (!hgr_spr_init_pool(1,pool,sizeof(pool),4,16)) return 2;'+
        'for(i=0;i<4;++i) {if(!hgr_spr_define(i,&shape)) return 3;'+
        'hgr_spr_move(i,28u+%du+i*3u,60u+i*2u);}'%phase,
        call='hgr_spr_render(); hgr_hud_putu(&hud,frame++); hgr_spr_present();')
SCENES['hgr_scene_large_edge'] = dict(sprites=True, sprite_height=16,
    sprite_width=21, sprite_stride=4, warmup=2,
    declarations='static hgr_hud_field_t hud;',
    setup='hgr_hud_init(&hud,48,0,5);'+
    'if (!hgr_spr_init_pool(1,pool,sizeof(pool),4,64)) return 2;'+
    'for(i=0;i<4;++i) {if(!hgr_spr_define(i,&shape)) return 3; hgr_spr_move(i,262u+i*3u,180u+i);}',
    call='hgr_spr_render(); hgr_hud_putu(&hud,frame++); hgr_spr_present();')
SCENES['hgr_scene_large_full'] = dict(SCENES['hgr_scene_large_edge'],
    setup=SCENES['hgr_scene_large_edge']['setup'].replace('262u','28u').replace('180u','60u'))
for variant in ('compact','unrolled','fixed'):
    SCENES['hgr_rows_'+variant] = dict(call='bench_present();',presentation=variant,
        setup='hgr_build_tables();',warmup=False)
for mode in ('delay','vbl'):
    SCENES['hgr_loop_'+mode] = dict(sprites=True,sprite_width=7,sprite_height=8,sprite_stride=2,
        warmup=2,iie=(mode=='vbl'),cadence=True,declarations='static hgr_hud_field_t hud;',
        setup='a2_frame_init(); a2_frame_set_delay(40); hgr_hud_init(&hud,48,0,5);'+
        'if(!hgr_spr_init_pool(1,pool,sizeof(pool),4,16)) return 2;'+
        'for(i=0;i<4;++i) if(!hgr_spr_define(i,&shape)) return 3;',
        call='if(apple2_readkey()==KC_LEFT) frame=0;'+
        'for(i=0;i<4;++i) hgr_spr_move(i,28u+i*3u+(frame%7u),60u+i*2u);'+
        'hgr_spr_render(); hgr_hud_putu(&hud,frame); a2_frame_wait(); hgr_spr_present(); ++frame;')
# Keep historical stationary workloads; add movement across both page histories.
for name in list(SCENES):
    if name.startswith(('hgr_scene_phase','hgr_scene_large')):
        options=dict(SCENES[name])
        if name.startswith('hgr_scene_phase'):
            x='28u+%du+i*3u'%int(name[-1]); y='60u+i*2u'
        elif name.endswith('edge'):
            x='262u+i*3u'; y='180u+i'
        else:
            x='28u+i*3u'; y='60u+i'
        options['call']='for(i=0;i<4;++i) hgr_spr_move(i,'+x+'+(frame%3u),'+y+');'+options['call']
        SCENES[name+'_moving']=options
SCENES['hgr_hud_cached_cold']=dict(call='hgr_hud_putu(&hud,54321u);',warmup=False,
    setup='hgr_hud_init(&hud,48,0,5);',declarations='static hgr_hud_field_t hud;')
for phase in range(7):
    SCENES['hgr_hud_changed_phase'+str(phase)]=dict(call='hgr_hud_putu(&hud,65432u);',warmup=False,
        setup='hgr_hud_init(&hud,%d,0,5); hgr_hud_putu(&hud,12345u);'%(48+phase),
        declarations='static hgr_hud_field_t hud;')
SCENES['hgr_rows_explicit_asm']=dict(call='bench_present();',presentation='explicit',warmup=False)
SCENES['hgr_rows_explicit']=dict(call='for(y=0;y<192;++y) row=hgr_row_on_page(2,y);',
    declarations='static volatile unsigned char *row; unsigned char y;',warmup=False)
BASELINE=Path(__file__).with_name('baseline.json')
BUDGETS=Path(__file__).with_name('budgets.json')

# Representative work excludes waiting, but includes input, movement, render,
# changing every HUD digit and presentation. Initialization warms both pages.
for phase in range(7):
    SCENES['hgr_hud8_changed_phase'+str(phase)]=dict(
        call='hgr_hud8_putu(&hud,65432u);',warmup=False,
        setup='hgr_hud8_init(&hud,%d,0,5); hgr_hud8_putu(&hud,12345u);'%(48+phase),
        declarations='static hgr_hud8_field_t hud;')
for suffix, call in (('same','hgr_hud8_putu(&hud,12345u);'),
                     ('cold','hgr_hud8_putu(&hud,54321u);')):
    SCENES['hgr_hud8_'+suffix]=dict(call=call,warmup=(suffix=='same'),
        setup='hgr_hud8_init(&hud,48,0,5);', declarations='static hgr_hud8_field_t hud;')
SCENES['hgr_game_compact']=dict(sprites=True,sprite_width=7,sprite_height=8,sprite_stride=2,
    warmup=2,declarations='static hgr_hud8_field_t hud; unsigned char phase;'+
    'static const unsigned scores[3]={123u,654u,987u};',
    setup='hgr_hud8_init(&hud,48,0,3);'+
    'if(!hgr_spr_init_pool(1,pool,sizeof(pool),2,16)) return 2;'+
    'for(i=0;i<2;++i) if(!hgr_spr_define(i,&shape)) return 3;',
    call='if(apple2_readkey()==KC_LEFT) frame+=1; phase=frame%3u;'+
    'for(i=0;i<2;++i) hgr_spr_move(i,28u+i*3u+phase,60u+i*2u);'+
    'hgr_spr_render(); hgr_hud8_putu(&hud,scores[phase]);'+
    'hgr_spr_present(); ++frame;')
for damage in (False,True):
    SCENES['hgr_isolated_'+('damage' if damage else 'suffix')]=dict(
        sprites=True,sprite_width=21,sprite_height=16,sprite_stride=4,
        warmup=2,damage=damage,
        setup='if(!hgr_spr_init_pool(1,pool,sizeof(pool),4,64)) return 2;'+
              'for(i=0;i<4;++i) {if(!hgr_spr_define(i,&shape)) return 3;'+
              'hgr_spr_move(i,28u+i*56u,60u);}',
        call='hgr_spr_move(0,28u+(frame%3u),60u); hgr_spr_render(); hgr_spr_present(); ++frame;')
for name in ('hgr_game_compact','hgr_isolated_damage'):
    SCENES[name+'_pal']=dict(SCENES[name],iie=True,pal=True)
for phase in range(1,7):
    name='hgr_game_compact_phase'+str(phase)
    SCENES[name]=dict(SCENES['hgr_game_compact'],
        setup=SCENES['hgr_game_compact']['setup'].replace('48,0,3',f'{48+phase},0,3'),
        call=SCENES['hgr_game_compact']['call'].replace('28u+i',f'{28+phase}u+i'))
    SCENES[name+'_pal']=dict(SCENES[name],iie=True,pal=True)


SCENES['hgr_hud8_carry']=dict(call='hgr_hud8_putu(&hud,10000u);',warmup=False,
    setup='hgr_hud8_init(&hud,48,0,5);hgr_hud8_putu(&hud,9999u);',
    declarations='static hgr_hud8_field_t hud;')
SCENES['hgr_tile_background']=dict(sprites=True,sprite_width=7,sprite_height=8,sprite_stride=2,
    declarations='#include "hgr_internal.h"\nstatic hgr_tilemap_t background;'+
    'static unsigned char tilemap[960];static const unsigned char tiles[8]={85,42,85,42,85,42,85,42};',
    setup='if(!hgr_tilemap_init(&background,tilemap,tiles,1))return 2;hgr_set_draw_page(2);',
    call='hgr_tile_restore(&background,2,4,7,4,2);'+
    'hgr_ms_spr=&shape;hgr_ms_x=29;hgr_ms_y=60;hgr_ms_run();'+
    'hgr_ms_x=43;hgr_ms_y=60;hgr_ms_run();hgr_show_page();')
SCENES['hgr_tile_background_pal']=dict(SCENES['hgr_tile_background'],iie=True,pal=True)


def segment_sizes(mapfile):
    section=mapfile.read_text().split('Segment list:')[1].split('Exports list')[0]
    sizes={m[1]:int(m[2],16) for m in re.finditer(r'^([A-Z][A-Z0-9_]*)\s+[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]+)',section,re.M)}
    return sizes


def segments(mapfile):
    sizes=segment_sizes(mapfile)
    init=sum(sizes.get(s,0) for s in ('ONCE','INIT','LOWCODE'))
    return dict(code_bytes=sizes.get('CODE',0)+sizes.get('STARTUP',0)+init,
                init_code_bytes=init,
                rodata_bytes=sizes.get('RODATA',0),
                ram_bytes=sum(sizes.get(s,0) for s in ('BSS','LOWBSS','DATA','ZPSAVE')),
                zp_bytes=sizes.get('ZEROPAGE',0))


def sprite_source(width,height,stride):
    data=[]; masks=[]
    for phase in range(7):
        for y in range(height):
            coverage=((1<<width)-1)<<phase
            bits=sum(1<<(phase+x) for x in range(width) if (x+y)%3)
            data.extend((bits>>(7*i))&127 for i in range(stride))
            masks.extend(255^((coverage>>(7*i))&127) for i in range(stride))
    return ('static const unsigned char bits[]={'+','.join(map(str,data))+'};\n'+
            'static const unsigned char mask[]={'+','.join(map(str,masks))+'};\n')


def presentation_source(variant):
    # Compare the same work: change draw page and resolve all 192 row pointers.
    # Fixed base is a prototype, not the current public table ABI.
    if variant=='explicit':
        return ('.export _bench_present\n.import hgr_fixed_rowlo, hgr_fixed_rowhi\n.importzp ptr1\n'
                '.data\nbase: .byte $20\n.code\n_bench_present:\n'
                'lda base\neor #$60\nsta base\nldx #191\n'
                'rows: lda hgr_fixed_rowlo,x\nsta ptr1\nlda hgr_fixed_rowhi,x\nora base\n'
                'sta ptr1+1\ndex\ncpx #$ff\nbne rows\nrts\n')
    prefix='.export _bench_present\n.import _hgr_rowhi, _hgr_rowlo\n.importzp ptr1\n.code\n_bench_present:\n'
    if variant=='unrolled':
        prefix='.import _hgr_flip_rows\n'+prefix+'jsr _hgr_flip_rows\n'
    elif variant=='compact':
        prefix+='ldx #191\nflip: lda _hgr_rowhi,x\neor #$60\nsta _hgr_rowhi,x\ndex\ncpx #$ff\nbne flip\n'
    else:
        prefix='.bss\nbase: .res 1\n'+prefix+'lda base\neor #$60\nsta base\n'
    prefix+='ldx #191\nrows: lda _hgr_rowlo,x\nsta ptr1\nlda _hgr_rowhi,x\n'
    if variant=='fixed': prefix+='eor base\n'
    return prefix+'sta ptr1+1\ndex\ncpx #$ff\nbne rows\nrts\n'


def measure(work,name,call,dhgr=False,setup='',sprites=False,warmup=True,
            declarations='',sprite_width=None,sprite_height=4,sprite_stride=2,presentation=None,iie=False,cadence=False,
            pal=False,damage=False):
    source=work/(name+'.c'); obj=source.with_suffix('.o'); binary=source.with_suffix('.bin')
    source.write_text('#include "hgr.h"\n#include "gfx.h"\n#include "dhgr.h"\n#include "apple2io.h"\n'
      'void hgr_build_tables(void); void bench_begin(void); void bench_end(void); void bench_present(void);\n'+
      (sprite_source(sprite_width,sprite_height,sprite_stride) if sprite_width else
       'static const unsigned char bits[64]={127,85,42,127};\n')+
      (('' if sprite_width else 'static const unsigned char mask[56]={0};\n')+
       'static const hgr_mspr_t shape={bits,mask,%d,%d};\n'%(sprite_stride,sprite_height)+
       'static unsigned char pool[%d];\n'%(8*sprite_stride*sprite_height) if sprites else '')+
      declarations+'\n'+
      'int main(void) {\n'+('unsigned char i; unsigned frame=0;\n' if sprites else '')+
      ('if (!dhgr_init()) return 1;' if dhgr else 'hgr_init();')+setup+
      (call*int(warmup) if not dhgr else '')+
      '\nbench_begin();\n'+call+
      '\nbench_end();\napple2_getkey(); return 0; }\n')
    run(['cl65','-t','none','-Oirs','-I',DEV/'lib/hgrc','-I',DEV/'lib/apple2c','-I',DEV/'lib/gfx','-c','-o',obj,source])
    mapfile=source.with_suffix('.map'); labels=source.with_suffix('.lbl')
    extra=[]
    if damage:
        from test_hgr import compile_source
        damage_obj=work/(name+'_damage.o')
        compile_source(DEV/'lib/hgrc/hgr_sprengine.c',damage_obj,
                       ['-t','none','-Oirs','-DHGR_SPR_DAMAGE=1','-I',DEV/'lib/hgrc',
                        '-I',DEV/'lib/apple2c'])
        extra.append(damage_obj)
    if cadence:
        frame_obj=work/(name+'_frame.o')
        run(['ca65','-t','none','-o',frame_obj,DEV/'lib/apple2c/apple2frame.s'])
        extra.append(frame_obj)
    if presentation:
        asm=source.with_suffix('.s'); asm.write_text(presentation_source(presentation))
        asm_obj=work/(name+'_asm.o')
        run(['ca65','-t','none','-o',asm_obj,asm]); extra.append(asm_obj)
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-m',mapfile,'-Ln',labels,
         '-o',binary,work/'crt0_apple2.o',obj,work/'markers.o',work/'apple2io_asm.o',*extra,work/'hgrc.lib'])
    points=a2test.labels(labels)
    disk=a2test.build_disk(work,'BENCH',binary)
    emulator=DEV/'tools'/('a2shot/a2shot' if dhgr or iie else 'a2run/a2run')
    output=run([emulator,*(['--iie'] if dhgr or iie else []),*(['--pal'] if pal else []),'--disk',disk,
                f'until:{points["_bench_begin"]:04X}:1500',
                'hwstackwatch',f'stackwatch:{points["sp"]:02X}:{points["__STACKSTART__"]:04X}:{points["__STACKSIZE__"]:04X}',
                f'until:{points["_bench_end"]:04X}:1500','stack','hwstack'])
    ticks=[int(c) for c in re.findall(r'cycles=(\d+)',output)]
    assert len(ticks)==2
    peak,reserved,overflow=map(int,re.search(r'stack peak=(\d+) reserved=(\d+) overflow=(\d+)',output).groups())
    assert not overflow and peak < reserved,(name,'C stack overflow')
    hw_peak,hw_available,hw_overflow=map(int,re.search(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',output).groups())
    assert not hw_overflow and hw_peak < hw_available,(name,'hardware stack overflow')
    sizes=segment_sizes(mapfile)
    loaded=sum(sizes.get(s,0) for s in ('CODE','STARTUP','ONCE','INIT','LOWCODE','RODATA','DATA'))
    assert loaded==binary.stat().st_size,(name,'unaccounted loaded segment/padding')
    linked=mapfile.read_text().split('Segment list:')[0]
    row=re.search(r'hgr_rows_asm\.o\):\s+CODE\s+Offs=[0-9A-F]+\s+Size=([0-9A-F]+)',linked)
    return dict(segments(mapfile),binary_bytes=binary.stat().st_size,cycles=ticks[1]-ticks[0]-12,
                row_kernel_bytes=int(row[1],16) if row else 0,
                c_stack_peak_bytes=peak,c_stack_reserved_bytes=reserved,
                hardware_stack_peak_bytes=hw_peak,hardware_stack_available_bytes=hw_available)


@lru_cache(None)
def identity(path):
    return dict(name=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())


def environment(dhgr, pal=False):
    runner=DEV/'tools'/('a2shot/a2shot' if dhgr else 'a2run/a2run')
    paths=[runner,DEV/'tools/a2shot/roms'/('apple2e.rom' if dhgr else 'apple2p.rom'),
           DEV/'tools/a2shot/roms/disk2.rom',DEV/'tools/dos33_system.bin']
    paths += ([DEV/'tools/a2shot/sdk/lib/libpom2_core.a'] if dhgr else
              [DEV/'tools/a2run/cpu6502.c', DEV/'tools/a2run/a2run.c'])
    return dict(cpu='65C02' if dhgr else 'NMOS6502',model='IIe enhanced 128K' if dhgr else 'II+ 48K',
                frame_cycles=20280 if pal else 17030,artifacts=[identity(p) for p in paths])


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
        results.update({name:measure(work,name,**options) for name,options in SCENES.items() if args.dhgr or not options.get('iie',False)})
    import subprocess
    version_result=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
    version=(version_result.stdout+version_result.stderr).strip()
    case_environments={name:('iie_pal' if SCENES.get(name,{}).get('pal',False) else
                            'iie' if CASES.get(name,('',False))[1] or SCENES.get(name,{}).get('iie',False) else 'nmos') for name in results}
    report=dict(schema=2,case_environments=case_environments,stack_sampling='coherent cc65 call/return/jump/(sp),Y boundaries; observed workload, not a static bound',compiler=version,flags='-Oirs',results=results,
                environments={mode:environment(mode.startswith('iie'),mode=='iie_pal') for mode in sorted(set(case_environments.values()))})
    stress=[m['cycles'] for n,m in results.items() if n.startswith(('hgr_scene_phase','hgr_scene_large'))]
    report['scene_max_cycles']=max(stress)
    report['hud_changed_max_cycles']=max(m['cycles'] for n,m in results.items() if n.startswith('hgr_hud_changed_phase'))
    report['absolute_budgets']={}
    absolute_failures=[]
    for name,policy in json.loads(BUDGETS.read_text()).items():
        if name not in results: continue
        entry=dict(policy,measured_cycles=results[name]['cycles'])
        entry['limit_cycles']=policy['refreshes']*policy['frame_cycles']-policy['reserved_cycles']
        entry['spare_cycles']=entry['limit_cycles']-entry['measured_cycles']
        report['absolute_budgets'][name]=entry
        if entry['spare_cycles']<0: absolute_failures.append(f'{name}: absolute deadline exceeded by {-entry["spare_cycles"]} cycles')
    for name,metrics in results.items():
        print(f'{name:16} {metrics["cycles"]:8} cycles  {metrics["binary_bytes"]:5} B binary  '+
              f'{metrics["code_bytes"]:5} B code  {metrics["ram_bytes"]:4} B RAM  {metrics["zp_bytes"]:3} B ZP  '+
              f'{metrics["c_stack_peak_bytes"]:2} B C stack peak  {metrics["hardware_stack_peak_bytes"]:2} B hardware stack peak')
    baseline=json.loads(BASELINE.read_text()) if BASELINE.exists() else dict(compiler=version,flags='-Oirs',results={})
    if args.update:
        baseline['compiler']=version;baseline['results'].update(results)
        baseline['schema']=2
        baseline.setdefault('environments',{}).update(report['environments'])
        baseline.setdefault('case_environments',{}).update(report['case_environments'])
        BASELINE.write_text(json.dumps(baseline,indent=2)+'\n')
    if args.out:args.out.write_text(json.dumps(report,indent=2)+'\n')
    if args.check:
        failures=list(absolute_failures)
        # Small compiler differences are permitted, concrete regressions fail.
        for name,metrics in results.items():
            if name not in baseline['results']:failures.append(name+': missing baseline');continue
            previous=baseline.get('environments',{}).get(baseline.get('case_environments',{}).get(name))
            current=report['environments'][report['case_environments'][name]]
            if not previous: failures.append(name+': missing environment reference')
            if previous:
                for key in ('cpu','model','frame_cycles'):
                    if previous[key]!=current[key]: failures.append(name+': changed '+key)
                # Runner binaries differ by host/compiler. Gate the CPU source
                # or SDK and system ROM, while recording all binary hashes.
                old_hash={a['name']:a['sha256'] for a in previous['artifacts']}
                for artifact in current['artifacts']:
                    if artifact['name'] in ('cpu6502.c','libpom2_core.a','apple2e.rom','apple2p.rom'):
                        if old_hash.get(artifact['name'])!=artifact['sha256']:
                            failures.append(name+': changed core/ROM '+artifact['name'])
            for key,value in metrics.items():
                if key not in baseline['results'][name]:
                    failures.append(name+': missing '+key+' reference');continue
                old=baseline['results'][name][key]
                margin=max(16,int(old*.05)) if key=='cycles' else 0 if key=='zp_bytes' else max(16,int(old*.03))
                if value>old+margin:failures.append(f'{name}.{key}: {value} > {old}+{margin}')
        if failures:raise SystemExit('\n'.join(failures))
        print('Performance budgets passed.')
    print('Maximum measured stress scene:',report['scene_max_cycles'],'cycles (without VBL/game logic).')
    for name,budget in report['absolute_budgets'].items():
        print(f'{name}: {budget["measured_cycles"]}/{budget["limit_cycles"]} cycles, '+
              f'{budget["reserved_cycles"]} additionally reserved for game/audio/IRQ')

if __name__=='__main__':main()
