#!/usr/bin/env python3
"""DHGR overlay group/row oracles, piece boundaries and reloaded code windows.

The group oracle covers every raw width/start-byte pair; the row oracle
checks contiguous 256-row pieces across byte and 16-bit pointer wraparound.
Public updates independently check pixels, stores, banking and IRQs with
small pieces and fresh code reloaded before each update.
"""
import argparse
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from test_hgr import DEV, ROOT, build, compile_source, a2test
from test_dhgr_spr import SOURCES
import test_dhgr_spr as compositor


def check_groups(source):
    with tempfile.TemporaryDirectory(prefix='dhgr-ovgroup-') as directory:
        w=Path(directory);src=w/'dhgr_spr_overlay.s'
        src.write_text(source.read_text()+'''
.export _probe_group
.import _inputs,_outputs,_bits
.code
_probe_group:
 lda _inputs
 sta cur_nw
 lda _inputs+1
 sta cur_nbx
 lda _inputs+2
 sta tmp4
 lda #<_bits
 sta ptr1
 lda #>_bits
 sta ptr1+1
 lda _inputs+3
 sta tmp1
 lda _inputs+4
 sta tmp2
 lda _inputs+5
 sta tmp3
 ldx _inputs+7
 lda _inputs+6
 jsr ov_group
 sta _outputs+3
 stx _outputs+4
 php
 pla
 and #4
 sta _outputs+5
 lda tmp1
 sta _outputs
 lda tmp2
 sta _outputs+1
 lda tmp3
 sta _outputs+2
 lda tmp4
 sta _outputs+6
 lda ptr1
 sta _outputs+7
 lda ptr1+1
 sta _outputs+8
 rts
''')
        fixture=w/'fixture.c';fixture.write_text('''void probe_group(void);void batch_done(void);void finished(void);
unsigned char inputs[8],outputs[9],bits[256],records[9][256];
int main(void){
 unsigned index,width;unsigned char field;
 for(index=0;index<256;++index)bits[index]=(unsigned char)(index*73u+19u);
 for(width=0;width<256;++width){
  for(index=0;index<256;++index){
   inputs[0]=(unsigned char)width;
   inputs[2]=(unsigned char)(index^width);
   inputs[1]=(unsigned char)(2u*inputs[2]-index);
   inputs[3]=(unsigned char)(index*3u+width);
   inputs[4]=(unsigned char)(index^width^0x55u);
   inputs[5]=(unsigned char)(width*7u-index);
   inputs[6]=(unsigned char)(index+width*5u);
   inputs[7]=(unsigned char)(index*53u+width);
   if(index&1){asm("sei");}else{asm("cli");}
   probe_group();
   for(field=0;field<9;++field)records[field][index]=outputs[field];
  }
  batch_done();
 }
 finished();for(;;){}return 0;
}''')
        marker=w/'marker.s';marker.write_text('.export _batch_done,resume,_finished\n.code\n_batch_done:nop\nresume:rts\n_finished:rts\n')
        disk=build(w,fixture,extra_sources=[src,marker]+[DEV/'lib/hgrc'/s for s in SOURCES if s!='dhgr_spr_overlay.s'])
        labels=a2test.labels(w/'test.lbl');steps=[]
        for _ in range(256):steps += [labels.until('_batch_done'),labels.peek('_records',9*256),labels.until('resume')]
        steps += [labels.until('_finished')]
        for iie in (False,True):
            result=a2test.run(disk,steps,iie=iie)
            assert len(result.dumps)==256
            for width,raw in enumerate(result.dumps):
                for index in range(256):
                    expect=[(index*3+width)&255,index^width^0x55,(width*7-index)&255,(index+width*5)&255,
                                (index*53+width)&255,4 if index&1 else 0,index^width,labels['_bits']&255,labels['_bits']>>8]
                    for j in range(4):
                        at=(index+j)&255
                        if at<width:expect[j]|=(at*73+19)&127
                    got=[raw[field*256+index] for field in range(9)]
                    assert got==expect,(iie,width,index,got,expect)
            print('Overlay group: 65,536 calls, all raw widths/byte phases and wraparound; full bytes, X/tmp4/ptr1/IRQ preservation, IIe=',iie)

def check_rows(source):
    with tempfile.TemporaryDirectory(prefix='dhgr-ovrow-') as directory:
        w=Path(directory);src=w/'dhgr_spr_overlay.s'
        src.write_text(source.read_text()+'''
.export _probe_sequence
.import _inputs,_records,_dhgr_cv_y0
.code
_probe_sequence:
 php
 lda _inputs
 sta cur_nw
 lda _inputs+1
 sta cur_ny
 lda _inputs+2
 sta cur_nh
 lda _inputs+3
 sta _dhgr_cv_y0
 lda _inputs+4
 sta cur_bits
 lda _inputs+5
 sta cur_bits+1
 lda _inputs+6
 sta _dhgr_spr_w_g0
 lda _inputs+7
 sta w_g1
 lda _inputs+8
 sta _dhgr_spr_goff
 lda _inputs+9
 sta _dhgr_spr_gend
 lda #$5a
 sta ptr1
 lda #$a5
 sta ptr1+1
 lda _inputs+10
 beq @on
 sei
 bne @start
@on: cli
@start: ldx #0
@row:
 txa
 clc
 adc _inputs+3
 sta spr_row
 jsr ov_row
 lda ptr1
 sta _records,x
 lda ptr1+1
 sta _records+256,x
 lda spr_ovhook
 sta _records+512,x
 php
 pla
 and #4
 sta _records+768,x
 inx
 bne @row
 plp
 rts
''')
        fixture=w/'fixture.c';fixture.write_text('''void probe_sequence(void);void batch_done(void);void finished(void);
unsigned char inputs[11],records[4][256];
int main(void){
 unsigned seed;unsigned char phase;
 for(phase=0;phase<4;++phase)for(seed=0;seed<256;++seed){
  inputs[0]=(unsigned char)seed;
  inputs[1]=(unsigned char)(seed*73u+phase);
  inputs[2]=(unsigned char)(seed*29u+phase*67u);
  inputs[3]=(unsigned char)(seed^(phase*85u));
  inputs[4]=(unsigned char)seed;
  inputs[5]=(unsigned char)(phase*64u+seed*3u);
  inputs[6]=phase==0?0:(unsigned char)(seed*5u);
  inputs[7]=phase==1?19:(unsigned char)(seed*7u);
  inputs[8]=phase==2?40:0;
  inputs[9]=phase==3?0:40;
  inputs[10]=phase&1;
  probe_sequence();batch_done();
 }
 finished();for(;;){}return 0;
}''')
        marker=w/'marker.s';marker.write_text('.export _batch_done,resume,_finished\n.code\n_batch_done:nop\nresume:rts\n_finished:rts\n')
        disk=build(w,fixture,extra_sources=[src,marker]+[DEV/'lib/hgrc'/s for s in SOURCES if s!='dhgr_spr_overlay.s'])
        labels=a2test.labels(w/'test.lbl');steps=[]
        for _ in range(1024):steps += [labels.until('_batch_done'),labels.peek('_records',1024),labels.until('resume')]
        steps += [labels.until('_finished')]
        for iie in (False,True):
            result=a2test.run(disk,steps,iie=iie)
            assert len(result.dumps)==1024
            for phase in range(4):
                for seed in range(256):
                    raw=result.dumps[phase*256+seed];cy=(seed*73+phase)&255;height=(seed*29+phase*67)&255
                    start=seed^(phase*85);base=seed+(((phase*64+seed*3)&255)<<8)
                    g0=0 if phase==0 else(seed*5)&255;g1=19 if phase==1 else(seed*7)&255
                    goff=40 if phase==2 else 0;gend=0 if phase==3 else 40
                    horizontal=((g0*2)&255)<gend and ((g1*2)&255)>=goff;ptr=0xa55a
                    for j in range(256):
                        row=(start+j)&255;valid=horizontal and row>=cy and row-cy<height
                        if valid:ptr=(base+(row-cy)*seed)&65535
                        expect=[ptr&255,ptr>>8,0x20 if valid else 0x2c,4 if phase&1 else 0]
                        got=[raw[p*256+j] for p in range(4)]
                        assert got==expect,(iie,phase,seed,j,got,expect)
            print('Overlay rows: 262,144 native calls, all width/height/first-row bytes, piece starts, wrap/carry, horizontal rejection and IRQ preservation; IIe=',iie)

def lifecycle_script():
    s = compositor.Script()
    s.solid(9)
    s.invalidate(0,0,140,192)
    s.set(0,0,28,17)
    s.update('background and sprite')
    s.overlay(0,0,1,127)
    s.update('long overlay across pieces')
    s.overlay(1,1,1,127)
    s.update('long overlay moves')
    s.overlay(79,65,1,127)
    s.update('last byte and bottom row')
    s.overlay(0,0,0,0)
    s.update('hide before resizing')
    s.overlay(17,17,3,7)
    s.update('short overlay starts inside a band')
    s.invalidate(28,0,7,40)
    s.update('rejected rows enter at r zero; next piece enters at r three')
    s.invalidate(0,0,7,40)
    s.update('whole piece rejected horizontally')
    s.overlay(18,18,3,7)
    s.update('overlay crosses group boundary')
    s.invalidate(28,10,14,30)
    s.update('two groups and several band starts')
    s.overlay(0,0,0,0)
    s.update('hide short overlay')
    s.area(28,40,111,100)
    s.overlay(15,35,4,31)
    s.update('overlay crosses area left and top')
    s.invalidate(28,40,7,40)
    s.update('piece starts halfway through overlay')
    s.overlay(16,36,4,31)
    s.update('clipped overlay moves')
    s.overlay(0,0,0,0)
    s.update('hide before area transition')
    s.area(35,45,104,95)
    s.overlay(16,36,4,31)
    s.invalidate(0,0,140,192)
    s.update('area transition with nonzero first overlay row')
    s.overlay(0,0,0,0)
    s.update('hide clipped overlay')
    s.area(0,0,139,191)
    s.invalidate(0,0,140,192)
    s.overlay(5,0,1,127)
    s.update('restore area and tall overlay')
    s.overlay(0,0,0,0)
    s.update('final restore')
    s.ops.append(0)
    return s


def check_lifecycle(source):
    original_compile, original_run = compositor.compile_source, compositor.run
    with tempfile.TemporaryDirectory(prefix='dhgr-overlay-life-') as directory:
        work = Path(directory)
        build(work)
        (work/'markers.s').write_text(compositor.MARKERS)
        compile_source(work/'markers.s',work/'markers.o',['-t','none'])
        (work/'via.s').write_text(compositor.VIA_IRQ)
        compile_source(work/'via.s',work/'via.o',['-t','none'])
        script = lifecycle_script()
        compositor.write_inc(work,script,70,2)

        def compile_member(member,obj,flags):
            member = Path(member)
            if member.name == 'dhgr_spr_overlay.s':
                member = source
            elif member.name.endswith('_dhgr_spr_overlay.s'):
                replacement = work/('reference_'+member.name)
                replacement.write_text(member.read_text().replace(
                    '.include "dhgr_spr_overlay.s"',source.read_text()))
                member = replacement
            return original_compile(member,obj,flags)

        compositor.compile_source = compile_member
        try:
            for reload_window in (False,True):
                name = 'life_reload' if reload_window else 'life_plain'
                variant = ('DHGR_SPR_CODE_SEGMENT',) if reload_window else ()

                def run_with_reload(args,**kwargs):
                    if reload_window and Path(args[0]).name == 'a2shot':
                        table = (work/(name+'.map')).read_text().split('Segment list:')[1]
                        segment = re.search(r'(?m)^DHGRSPRCODE\s+([0-9A-F]+)\s+[0-9A-F]+\s+([0-9A-F]+)',table)
                        assert segment, 'missing overlay code segment'
                        address,size = (int(value,16) for value in segment.groups())
                        binary = (work/(name+'.bin')).read_bytes()
                        start = address-0x6000
                        assert 0 <= start < start+size <= len(binary)
                        window = work/'window.bin'
                        window.write_bytes(binary[start:start+size])
                        augmented = []
                        for argument in args:
                            if str(argument) == 'storewatch:2000:5FFF':
                                # CPU is paused at _begin in the external marker;
                                # BSS survives while the code's SMC operands reset.
                                augmented.append(f'load:{window}@{address:04X}')
                            augmented.append(argument)
                        args = augmented
                    return original_run(args,**kwargs)

                compositor.run = run_with_reload
                for machine in ('--iie','--iic'):
                    stores,_ = compositor.check(work,name,script,machine,variant)
                    print(f'Overlay lifecycle {machine[2:]} reload={reload_window}: '
                          f'{len(script.updates)} updates, {stores:,} once-only stores; '
                          'piece boundaries, r=0 entry, rejection and pixels OK.')
                if reload_window:
                    stores,_ = compositor.check(work,name,script,'--iie',variant,irq=True)
                    print(f'Overlay reload + VIA IRQ: {stores:,} stores; bank safety and negative control OK.')
        finally:
            compositor.compile_source,compositor.run = original_compile,original_run


CASES = ('dhgr_spr_move','dhgr_spr_move_wide','dhgr_spr_move_cells','dhgr_spr_move_solid',
         'dhgr_spr_move_tables','dhgr_spr_move_chunky','dhgr_cursor_move',
         'dhgr_spr_overlay_h1','dhgr_spr_overlay_h6','dhgr_spr_overlay_h31','dhgr_spr_overlay_move')


def bench(source,out):
    spec = importlib.util.spec_from_file_location('overlay_bench',DEV/'bench/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SCENES = {name:module.SCENES[name] for name in CASES}
    module.CASES = {}
    module.SPR_SRCS = tuple(str(source.resolve()) if Path(s).name == 'dhgr_spr_overlay.s' else s
                            for s in module.SPR_SRCS)
    saved = sys.argv
    try:
        sys.argv = ['run.py','--dhgr']+(['--out',str(out)] if out else [])
        module.main()
    finally:
        sys.argv = saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=DEV/'lib/hgrc/dhgr_spr_overlay.s')
    parser.add_argument('--reference',help='also test a source file or a git revision')
    parser.add_argument('--bench',action='store_true',help='measure eleven canonical compositor cases')
    parser.add_argument('--out',type=Path,help='benchmark JSON; reference uses a -reference sibling')
    args = parser.parse_args()
    if args.out and not args.bench:
        parser.error('--out requires --bench')
    with tempfile.TemporaryDirectory(prefix='dhgr-overlay-reference-') as directory:
        sources = []
        if args.reference:
            reference = Path(args.reference)
            if not reference.is_file():
                reference = Path(directory)/'dhgr_spr_overlay_reference.s'
                reference.write_bytes(subprocess.check_output(
                    ['git','show',args.reference+':dev/lib/hgrc/dhgr_spr_overlay.s'],cwd=ROOT))
            sources.append(('reference',reference))
        sources.append(('current',args.source))
        for label,source in sources:
            print(f'Overlay {label}: {source}')
            if args.bench:
                out = args.out
                if label == 'reference' and out:
                    out = out.with_name(out.stem+'-reference'+out.suffix)
                bench(source,out)
            else:
                check_groups(source)
                check_rows(source)
                check_lifecycle(source)


if __name__ == '__main__':
    main()
