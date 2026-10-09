#!/usr/bin/env python3
"""Byte-overlap closure across four layers, both histories and pool guards."""
from pathlib import Path
import tempfile
from test_hgr import build
from test_sprengine import banks, SHAPES, scene
import a2test

# The first three shapes share save-under bytes although their visible pixels
# can be disjoint. Changing the highest layer requires reverse propagation.
CHAIN=((14,40),(21,40),(28,40),(140,60))
OPS=[CHAIN]*4 + [CHAIN[:2]+((29,40),CHAIN[3])]*2 + [CHAIN]*2
OPS += [((70,100),(140,60),(210,130),(14,40))]*2
OPS += [((71,100),(140,60),(210,130),(14,40))]*2
OPS += [((279,191),(278,190),None,(0,0))]*2
OPS += [(None,None,None,None)]*2 + [CHAIN]*2
OPS += [((28,40),(21,40),(14,40),(140,60))]*2


def main():
    with tempfile.TemporaryDirectory(prefix='hgr-damage-') as directory:
        work=Path(directory); source=work/'damage.c'
        data=''
        for i,shape in enumerate(SHAPES):
            for name,values in zip(('data','mask'),banks(shape)):
                data+=f'static const unsigned char {name}{i}[]={{'+','.join(map(str,values))+'};\n'
            data+=f'static const hgr_mspr_t shape{i}={{data{i},mask{i},2,3}};\n'
        data+='static const unsigned positions[][8]={'+','.join(
            '{'+','.join(str(v) for pos in op for v in (pos or (65535,0)))+'}' for op in OPS)+'};\n'
        source.write_text('#include "hgr.h"\n'+data+'''
static struct { unsigned char before, pool[48], after; } storage;
void damage_begin(void);
int main(void) {
    unsigned char i,id;
    hgr_init(); hgr_set_draw_page(1);hgr_clear(0xaa);
    hgr_set_draw_page(2);hgr_clear(0x55);
    storage.before=0xa5;storage.after=0x5a;
    if(!hgr_spr_init_pool(1,storage.pool,48,4,6)) return 1;
    for(id=0;id<4;++id)
        if(!hgr_spr_define(id,(id&1)?&shape1:&shape0)) return 2;
    for(i=0;i<sizeof(positions)/sizeof(positions[0]);++i) {
        for(id=0;id<4;++id) {
            if(positions[i][id*2]==65535) hgr_spr_hide(id);
            else hgr_spr_move(id,positions[i][id*2],positions[i][id*2+1]);
        }
        damage_begin(); hgr_spr_update();
        *(volatile unsigned char*)0x1000=storage.before;
        *(volatile unsigned char*)0x1001=storage.after;
        apple2_getkey();
    }
    return 0;
}''')
        marker=work/'marker.s'
        marker.write_text('.export _damage_begin\n.code\n_damage_begin:rts\n')
        disk=build(work,source,extra_sources=[marker],cflags=['-DHGR_SPR_DAMAGE=1'])
        labels=a2test.labels(work/'test.lbl');steps=[]
        for _ in OPS:
            steps += [labels.until('_damage_begin'),labels.until('_apple2_getkey'),
                      'peek:1000:2','peek:2000:16384','press: ']
        result=a2test.run(disk,steps,iie=True)
        backgrounds=[bytes([0xaa])*8192,bytes([0x55])*8192];pages=list(backgrounds)
        for frame,op in enumerate(OPS):
            pg=1-(frame&1)
            pages[pg]=scene(backgrounds[pg],[(id%2,*pos) for id,pos in enumerate(op) if pos])
            assert result.dumps[2*frame]==b'\xa5\x5a', (frame,'pool guard')
            assert result.dumps[2*frame+1]==pages[0]+pages[1],(frame,'byte-overlap closure')
    print('Sprite damage: four layers, reverse overlap propagation, byte padding, separated sprites, hiding/clipping and both-page guards OK.')


if __name__=='__main__': main()
