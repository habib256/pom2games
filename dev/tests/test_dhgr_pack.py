#!/usr/bin/env python3
"""DHGR packing carry, operand relocation, ordered stores and source guards."""
import argparse
import importlib.util
import sys
import tempfile
from pathlib import Path

from test_hgr import DEV, build, a2test
from test_dhgr import PATTERNS, offset
from test_dhgr_spr import SOURCES, STORE, pack


def nibbles(sample):
    return [sample&15, (sample>>4)&15, (sample>>8)&15, (sample>>8)&15,
            ((sample>>2)^(sample>>7))&15, sample&15, (sample>>4)&15]


def oracle(source):
    with tempfile.TemporaryDirectory(prefix='dhgr-pack-') as directory:
        work = Path(directory)
        fixture = work/'packing.c'
        fixture.write_text('''#include "dhgr.h"
void started(void); void finished(void); void page_done(void);
void probe_patch(void); void dhgr_spr_blit(void);
extern unsigned char *dhgr_cv_buf;
extern unsigned char dhgr_cv_w,dhgr_cv_h,dhgr_cv_y0,dhgr_spr_goff,dhgr_spr_gend;
unsigned char irq_after,params_ok,canvas[512];
int main(void) {
    unsigned batch,sample,start,i;
    unsigned char page,g;
    if(!dhgr_init()) return 1;
    for(page=1;page<=2;++page) {
        dhgr_draw_page(1); dhgr_clear(5);
        dhgr_draw_page(2); dhgr_clear(10);
        dhgr_draw_page(page); dhgr_show_page(3-page);
        for(batch=0;batch<256;++batch) {
            for(i=0;i<512;++i) canvas[i]=0;
            start=(batch*17u)&255u;
            for(g=0;g<16;++g) {
                sample=batch*16u+g; i=start+g*7u;
                canvas[i]=sample&15;
                canvas[i+1]=(sample>>4)&15;
                canvas[i+2]=canvas[i+3]=(sample>>8)&15;
                canvas[i+4]=((sample>>2)^(sample>>7))&15;
                canvas[i+5]=sample&15;
                canvas[i+6]=(sample>>4)&15;
            }
            dhgr_cv_buf=canvas+start;
            dhgr_cv_w=112; dhgr_cv_h=1; dhgr_cv_y0=batch%192u;
            dhgr_spr_goff=0; dhgr_spr_gend=32;
            probe_patch();
            if(batch&1) { asm("sei"); } else { asm("cli"); }
            started(); dhgr_spr_blit();
            asm("php"); asm("pla"); asm("sta _irq_after");
            params_ok=dhgr_cv_buf==canvas+start && dhgr_cv_w==112 && dhgr_cv_h==1
                &&dhgr_cv_y0==batch%192u &&dhgr_spr_goff==0 &&dhgr_spr_gend==32;
            finished(); asm("cli");
        }
        page_done();
    }
    for(;;) {} return 0;
}
''')
        member = work/'dhgr_spr_asm.s'
        member.write_text(source.read_text())
        marker = work/'marker.s'
        marker.write_text('''.export _started,_finished,_page_done,page_resume,_probe_patch
.import dhgr_cv_patch
.code
_started: rts
_finished: rts
_page_done: nop
page_resume: rts
_probe_patch: jmp dhgr_cv_patch
''')
        extras = [member, marker]+[DEV/'lib/hgrc'/s for s in SOURCES if s != 'dhgr_spr_asm.s']
        disk = build(work, fixture, extra_sources=extras)
        labels = a2test.labels(work/'test.lbl')
        steps = []
        for page in (1, 2):
            base, other = 0x2000*page, 0x2000*(3-page)
            for _ in range(256):
                steps += [labels.until('_started'), 'storewatch:2000:5FFF',
                          labels.until('_finished'), 'unstorewatch',
                          labels.peek('_irq_after', 2), 'peek:C013:2', labels.peek('_canvas', 512),
                          f'peek:{base:04X}:8192', 'poke:C003:0', f'peek:{base:04X}:8192', 'poke:C002:0']
            steps += [labels.until('_page_done'), 'peek:C013:2', f'peek:{other:04X}:8192',
                      'poke:C003:0', f'peek:{other:04X}:8192', 'poke:C002:0', labels.until('page_resume')]
        result = a2test.run(disk, steps, iie=True)
        expected_stores = []
        dump = 0
        for page in range(2):
            pages = [[bytearray(PATTERNS[c][1-b::2])*4096 for b in (0, 1)] for c in (5, 10)]
            for batch in range(256):
                canvas = bytearray(512)
                start = (batch*17)&255
                for group in range(16):
                    values = nibbles(batch*16+group)
                    canvas[start+7*group:start+7*group+7] = bytes(values)
                    b0,b1,b2,b3 = pack(values)
                    at = offset(batch%192)+2*group
                    for bank,address,value in ((0,at+1,b3),(0,at,b1),(1,at,b0),(1,at+1,b2)):
                        pages[page][bank][address] = value
                        expected_stores.append((bank, 0x2000*(page+1)+address, value,
                                                bool(batch&1) or bank == 1))
                state,banks,source_dump,main,aux = result.dumps[dump:dump+5]
                assert bool(state[0]&4) == bool(batch&1) and state[1] == 1, ('IRQ/globals', page, batch)
                assert not any(v&128 for v in banks), ('bank state', page, batch)
                assert source_dump == canvas, ('canvas changed', page, batch)
                assert main == pages[page][0] and aux == pages[page][1], ('packed bytes', page, batch)
                dump += 5
            banks,main,aux = result.dumps[dump:dump+3]
            assert not any(v&128 for v in banks)
            assert main == pages[1-page][0] and aux == pages[1-page][1], ('other page', page)
            dump += 3
        assert dump == len(result.dumps)
        observed = []
        for line in result.out.splitlines():
            match = STORE.match(line)
            if match:
                assert match[9] == '0' and match[10] == '0', ('ALTZP/RAMRD', line)
                observed.append((1 if match[11] == '1' else 0, int(match[2],16), int(match[3],16),
                                 bool(int(match[6],16)&4)))
        assert observed == expected_stores, ('ordered stores / IRQ masks', len(observed), len(expected_stores))
    print('DHGR pack: all 4,096 n3/n5/n6 triples, 256 canvas alignments, both pages/banks,')
    print(f'source preservation, globals, IRQ masks and {len(observed):,} exact ordered stores OK.')


def bench(source, out):
    spec = importlib.util.spec_from_file_location('dhgr_pack_bench', DEV/'bench/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='dhgr-pack-bench-') as directory:
        bridge = Path(directory)/'bridge.s'
        bridge.write_text('.export _probe_patch\n.import dhgr_cv_patch\n.code\n_probe_patch: jmp dhgr_cv_patch\n')
        module.SPR_SRCS = tuple(str(source.resolve()) if Path(s).name == 'dhgr_spr_asm.s' else s
                                for s in module.SPR_SRCS)+(str(bridge),)
        decl = '''extern unsigned char *dhgr_cv_buf;
extern unsigned char dhgr_cv_w,dhgr_cv_h,dhgr_cv_y0,dhgr_spr_goff,dhgr_spr_gend;
void probe_patch(void); void dhgr_spr_blit(void);
static unsigned char canvas[512]; static unsigned i;
'''
        common = 'for(i=0;i<512;++i)canvas[i]=(unsigned char)i&15;dhgr_cv_buf=canvas+250;'
        scenes = {
            'patch_cold': dict(setup=common, call='probe_patch();'),
            'patch_cached': dict(setup=common+'probe_patch();', call='probe_patch();'),
            'patch_moved': dict(setup=common+'probe_patch();dhgr_cv_buf=canvas+251;', call='probe_patch();'),
        }
        for name,groups,rows in (('one',1,1),('tall',2,18),('wide',20,1)):
            scenes['blit_'+name] = dict(setup=common+f'probe_patch();dhgr_cv_w={7*groups};'
                f'dhgr_cv_h={rows};dhgr_cv_y0=40;dhgr_spr_goff=0;dhgr_spr_gend={2*groups};',
                call='dhgr_spr_blit();')
        selected = {('dhgr_pack_'+name):dict(options,dhgr=True,iie=True,spr=(),warmup=False,
                                            declarations=decl) for name,options in scenes.items()}
        for name,base in (('steady_move','dhgr_spr_move'),('steady_wide','dhgr_spr_move_wide')):
            options = dict(module.SCENES[base])
            options['setup'] += options['call']
            options['call'] = 'dhgr_spr_set(0,&drone_s,32u,40u,0);dhgr_spr_update();'
            selected['dhgr_pack_'+name] = options
        module.SCENES = selected
        sys.argv = ['run.py','--dhgr','--only','dhgr_pack_']+(['--out',str(out)] if out else [])
        module.main()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEV/'lib/hgrc/dhgr_spr_asm.s')
    parser.add_argument('--bench', action='store_true', help='measure isolated patch/blit and steady frames')
    parser.add_argument('--out', type=Path, help='JSON benchmark output')
    args = parser.parse_args()
    if args.out and not args.bench:
        parser.error('--out requires --bench')
    if args.bench:
        bench(args.source, args.out)
    else:
        oracle(args.source)


if __name__ == '__main__':
    main()
