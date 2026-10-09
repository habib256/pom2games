#!/usr/bin/env python3
"""Four moving/colliding sprites, HUD, keyboard and IRQ AY audio at 30/25 FPS."""
from pathlib import Path
import re
import tempfile
from test_hgr import DEV, build, run, a2test
from test_cadence import build as build_clock


def check(pal):
    refresh=20280 if pal else 17030
    with tempfile.TemporaryDirectory(prefix='pom2-game-clock-') as directory:
        work=Path(directory)
        build_clock(work,refresh)
        timer=work/'timer.s'
        text=timer.read_text().replace('.bss\n', '.export music_ticks\n.bss\nmusic_ticks: .res 2\n',1)
        # This fixture owns slot 4. No runtime library installs this IRQ/card.
        text=text.replace('_clock_start:\n', '''_clock_start:
    lda #$ff
    sta $c402
    sta $c403
    lda #0
    sta $c400
    lda #4
    sta $c400
    ldx #7
    lda #$3e
    jsr ay_write
    ldx #8
    lda #12
    jsr ay_write
''',1)
        text=text.replace('    jsr _a2_cadence_tick\n', '''    jsr _a2_cadence_tick
    inc music_ticks
    bne music_counted
    inc music_ticks+1
music_counted:
    lda _a2_cadence_ticks
    and #63
    ora #32
    ldx #0
    jsr ay_write
''',1)
        text=text.replace('_clock_stop:\n    sei\n', '''_clock_stop:
    sei
    ldx #8
    lda #0
    jsr ay_write
''',1)
        text+='''
; X=AY register, A=value. No cc65 scratch, flags/registers saved by IRQ.
ay_write:
    pha
    stx $c401
    lda #7
    sta $c400
    lda #4
    sta $c400
    pla
    sta $c401
    lda #6
    sta $c400
    lda #4
    sta $c400
    rts
'''
        timer.write_text(text)
        bits=[];mask=[]
        for phase in range(7):
            for row in range(8):
                cover=127<<phase
                pixels=sum(1<<(x+phase) for x in range(7) if (row+x)%3)
                bits += [pixels&127,(pixels>>7)&127]
                mask += [255^(cover&127),255^((cover>>7)&127)]
        source=work/'game.c'
        source.write_text('''#include "hgr.h"
#include "apple2frame.h"
void clock_start(void);void clock_stop(void);
unsigned snapshot(void);void game_work(void);void game_checkpoint(void);
static const unsigned char bits[]={'''+','.join(map(str,bits))+'''};
static const unsigned char mask[]={'''+','.join(map(str,mask))+'''};
static const hgr_mspr_t shape={bits,mask,2,8};
static unsigned char pool[128];static hgr_hud8_field_t hud;
static unsigned x[4]={24,29,34,39};static unsigned char y[4]={64,67,70,73};
static signed char dx[4]={1,-1,1,-1},dy[4]={1,1,-1,-1};
#pragma bss-name(push,"LOWBSS")
/* Test telemetry is written before every read; LOWBSS is not CRT-zeroed. */
unsigned history[1000],skips[1000];
#pragma bss-name(pop)
unsigned char blanking[1000];
unsigned frame=65520u;unsigned char seen;
void game_present(void){hgr_spr_present();}
int main(void){
 unsigned n;unsigned char i,j,key,page;signed char direction;int xx,yy;
 hgr_init();hgr_hud8_init(&hud,48,0,3);
 for(page=1;page<=2;++page){hgr_set_draw_page(page);hgr_clear(0);hgr_hud8_putu(&hud,0);}
 if(!hgr_spr_init_pool(1,pool,sizeof(pool),4,16))return 1;
 for(i=0;i<4;++i)if(!hgr_spr_define(i,&shape))return 2;
 /* Prepare both page histories and lazy lookup tables before starting music. */
 for(i=0;i<4;++i)hgr_spr_move(i,x[i],y[i]);
 hgr_spr_update();hgr_spr_update();
 a2_cadence_ticks=0xff00;clock_start();a2_cadence_init(2);
 for(n=0;n<1000;++n){
  game_work();key=apple2_readkey();
  if(key==KC_RIGHT)seen|=1;if(key==KC_LEFT)seen|=2;
  if(key==KC_UP)seen|=4;if(key==KC_DOWN)seen|=8;
  for(i=0;i<4;++i){
   if(key==KC_LEFT)dx[i]=-1;if(key==KC_RIGHT)dx[i]=1;
   if(key==KC_UP)dy[i]=-1;if(key==KC_DOWN)dy[i]=1;
   if(x[i]<=10)dx[i]=1;if(x[i]>=260)dx[i]=-1;
   if(y[i]<=48)dy[i]=1;if(y[i]>=160)dy[i]=-1;
   x[i]+=dx[i];y[i]+=dy[i];
  }
  for(i=0;i<4;++i)for(j=i+1;j<4;++j){
   xx=(int)x[i]-(int)x[j];yy=(int)y[i]-(int)y[j];
   if(xx>=-7 && xx<=7 && yy>=-8 && yy<=8 &&
      ((xx<0 && dx[i]>dx[j]) || (xx>0 && dx[i]<dx[j]))){
    direction=dx[i];dx[i]=dx[j];dx[j]=direction;
    direction=dy[i];dy[i]=dy[j];dy[j]=direction;
   }
  }
  for(i=0;i<4;++i)hgr_spr_move(i,x[i],y[i]);
  hgr_spr_render();hgr_hud8_putu(&hud,frame%1000u);
  skips[n]=a2_cadence_wait();blanking[n]=*(volatile unsigned char*)0xc019;
  game_present();history[n]=snapshot();++frame;
 }
 clock_stop();game_checkpoint();return 0;
}''')
        markers=work/'markers.s'
        markers.write_text('.export _game_work,_game_checkpoint\n.code\n_game_work:rts\n_game_checkpoint:rts\n')
        disk=build(work,source,extra_sources=[timer,markers,DEV/'lib/apple2c/apple2cadence.s',
                                             DEV/'lib/apple2c/apple2frame.s'])
        labels=a2test.labels(work/'test.lbl')
        steps=[labels.until('_game_work'),'hwstackwatch',
               f'stackwatch:{labels["sp"]:02X}:{labels["__STACKSTART__"]:04X}:{labels["__STACKSIZE__"]:04X}']
        for count,key in ((250,r'\>'),(250,r'\<'),(250,r'\^'),(150,r'\v'),(100,None)):
            steps += [f'tracepc:{labels["_game_present"]:04X}:{count}:1500']
            if key: steps += ['press:'+key,labels.until('_game_work',limit=10)]
        steps += [labels.until('_game_checkpoint',limit=10),'stack','hwstack',
                  labels.peek('_skips',2000),labels.peek('_history',2000),
                  labels.peek('_blanking',1000),labels.peek('music_ticks',2),labels.peek('_seen')]
        output=run([DEV/'tools/a2shot/a2shot','--iie','--mockingboard',*(['--pal'] if pal else []),
                    '--disk',disk,*steps])
        parsed=a2test.Result(output)
        skipped=parsed.mem(labels['_skips'],2000)
        misses=[(i//2,int.from_bytes(skipped[i:i+2],'little')) for i in range(0,2000,2) if skipped[i:i+2]!=b'\x00\x00']
        assert not misses,('complete game missed a deadline',len(misses),misses[:12])
        assert not any(v&128 for v in parsed.mem(labels['_blanking'],1000)),'flip outside VBL'
        assert parsed.mem(labels['_seen'],1)==b'\x0f',('keyboard branches not exercised',parsed.mem(labels['_seen'],1))
        music=int.from_bytes(parsed.mem(labels['music_ticks'],2),'little')
        assert 2000<=music<=2002,('IRQ audio service',music)
        cycles=[int(n) for n in re.findall(r'tracepc [0-9A-F]+ cycles=(\d+)',output)]
        assert len(cycles)==1000
        spans=[cycles[i]-cycles[i-1] for i in range(1,len(cycles))]
        assert all(abs(n-2*refresh)<300 for n in spans), (min(spans),max(spans))
        history=parsed.mem(labels['_history'],2000)
        ticks=[int.from_bytes(history[i:i+2],'little') for i in range(0,2000,2)]
        assert all((ticks[i]-ticks[i-1])&65535==2 for i in range(1,1000)), 'tick cadence'
        assert any(ticks[i]<ticks[i-1] for i in range(1,1000)),'no clock wrap'
        stacks=re.findall(r'(?:hw)?stack peak=(\d+) (?:reserved|available)=(\d+) overflow=(\d+)',output)
        assert len(stacks)==2 and all(int(peak)<int(limit) and not int(over) for peak,limit,over in stacks),stacks
        print(f'Complete game {"PAL" if pal else "NTSC"}: 1000 frames, four sprites/collisions/HUD/keys, '
              f'{music} IRQ music ticks, {min(spans)}..{max(spans)} cycles, no missed deadline; stacks OK')


def main():
    run(['make','-s','-C',DEV/'tools/a2shot'])
    check(False);check(True)


if __name__=='__main__':main()
