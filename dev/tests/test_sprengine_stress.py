#!/usr/bin/env python3
"""Large save-under sprites, all phases, overlap/clipping and restore on both pages."""
from pathlib import Path
import tempfile
from test_hgr import build, pixel
import a2test


def main():
    width,height,stride=21,16,4
    data=[];mask=[]
    for phase in range(7):
        for y in range(height):
            cover=((1<<width)-1)<<phase
            bits=sum(1<<(x+phase) for x in range(width) if (x+y)%3)
            data += [(bits>>(7*i))&127 for i in range(stride)]
            mask += [255^((cover>>(7*i))&127) for i in range(stride)]
    with tempfile.TemporaryDirectory(prefix='spr-stress-') as directory:
        work=Path(directory);source=work/'stress.c'
        source.write_text('#include "hgr.h"\n'+
            'static const unsigned char data[]={'+','.join(map(str,data))+'};\n'+
            'static const unsigned char mask[]={'+','.join(map(str,mask))+'};\n'+
            '''static const hgr_mspr_t shape={data,mask,4,16};
static unsigned char pool[514];
int main(void) {
    unsigned char phase,frame,i;
    hgr_init();
    for(phase=0;phase<8;++phase) {
        hgr_set_draw_page(1);hgr_clear(0xaa);
        hgr_set_draw_page(2);hgr_clear(0x55);
        pool[0]=0xa5;pool[513]=0x5a;
        if(!hgr_spr_init_pool(1,pool+1,512,4,64)) return 1;
        for(i=0;i<4;++i) if(!hgr_spr_define(i,&shape)) return 2;
        for(frame=0;frame<4;++frame) {
            for(i=0;i<4;++i) hgr_spr_move(i,
                (phase==7 ? 262u : 28u+phase)+i*3u+frame,
                (phase==7 ? 180u : 60u)+i*2u);
            hgr_spr_render();
            *(volatile unsigned char*)0x1000=(pool[0]==0xa5 && pool[513]==0x5a);
            apple2_getkey();
            hgr_spr_present();
        }
    }
    return 0;
}''')
        disk=build(work,source);labels=a2test.labels(work/'test.lbl')
        steps=[]
        for _ in range(32):
            steps += [labels.until('_apple2_getkey'),'peek:1000:1','peek:2000:16384','key: ']
        result=a2test.run(disk,steps)
        for phase in range(8):
            background=[bytearray([0xaa])*8192,bytearray([0x55])*8192]
            pages=[bytearray(p) for p in background]
            for frame in range(4):
                page=1 if frame%2==0 else 0
                pages[page]=bytearray(background[page])
                for sprite in range(4):
                    x0=(262 if phase==7 else 28+phase)+sprite*3+frame
                    y0=(180 if phase==7 else 60)+sprite*2
                    for y in range(height):
                        for x in range(width): pixel(pages[page],x0+x,y0+y,int((x+y)%3!=0))
                stage=phase*4+frame
                assert result.dumps[2*stage]==b'\x01','pool overflow'
                assert result.dumps[2*stage+1]==pages[0]+pages[1],(phase,frame,'pixels/palette/holes/restore')
    print('Sprite stress: 32 large four-sprite scenes, all phases, overlaps, right/bottom clipping and both-page restores OK.')


if __name__=='__main__':main()
