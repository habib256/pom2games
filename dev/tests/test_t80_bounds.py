#!/usr/bin/env python3
"""80-column text clipping must not wrap at byte counters or scroll zero rows."""
from pathlib import Path
import tempfile
from test_hgr import DEV, compile_source, run, a2test


def check(work, pointer=False):
    src=work/'text.c'
    src.write_text('''#include "apple2t80.h"
#include <string.h>
void reset(void); void capture(void); void done(void); void ready(void);
char text[301];
unsigned char scene;
int main(void) {
    memset(text,'X',300); text[300]=0;
    for(scene=0;scene<8;++scene) {
        ready(); reset(); t80_init(); T80_AT(79,7);
#if T80_PTR
        t80_ptr_x=79; t80_ptr_y=7; t80_ptr_show();
#endif
        if(scene==0) t80_puts(text);
        else if(scene==1) t80_fill('X',255);
        else if(scene<4) { t80_x=0; t80_scroll(scene==3); }
        else if(scene==4) { T80_AT(1,2); t80_mode=T80_INVERSE; t80_puts("abc"); }
        else if(scene==5) t80_fill('X',0);
        else if(scene==6) { t80_x=1; t80_scroll(0); }
        else { T80_AT(0,23); t80_fill('X',80); }
#if T80_PTR
        t80_ptr_hide();
#endif
        capture(); done();
    }
    for (;;) {}
    return 0;
}
''')
    asm=work/'capture.s'
    asm.write_text('''.setcpu "65C02"
.export _reset, _capture, _done, _ready, _snapshot
.bss
_snapshot: .res 2048
.code
_reset:
    sta $C001
    ldy #2
bank:
    bit $C054
    cpy #2
    beq :+
    bit $C055
:   ldx #0
    lda #$A5
:   sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    inx
    bne :-
    dey
    bne bank
    bit $C054
    rts
_capture:
    bit $C054
    ldx #0
:   lda $0400,x
    sta _snapshot,x
    lda $0500,x
    sta _snapshot+256,x
    lda $0600,x
    sta _snapshot+512,x
    lda $0700,x
    sta _snapshot+768,x
    inx
    bne :-
    bit $C055
    ldx #0
:   lda $0400,x
    sta _snapshot+1024,x
    lda $0500,x
    sta _snapshot+1280,x
    lda $0600,x
    sta _snapshot+1536,x
    lda $0700,x
    sta _snapshot+1792,x
    inx
    bne :-
    bit $C054
    rts
_done: rts
_ready: rts
''')
    objects=[]
    sources=[DEV/'cc65/crt0_apple2.s',src,asm,DEV/'lib/apple2c/apple2t80.s']
    if pointer: sources.append(DEV/'lib/apple2c/apple2t80_ptr.s')
    for i,path in enumerate(sources):
        obj=work/f'{i}.o'
        compile_source(path,obj,['-t','none','--cpu','65c02','-Oirs','-I',DEV/'lib/apple2c','-D',f'T80_PTR={int(pointer)}','--asm-define',f'T80_PTR={int(pointer)}'])
        objects.append(obj)
    binary=work/'text.bin'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',work/'text.lbl','-o',binary,*objects])
    labels=a2test.labels(work/'text.lbl')
    steps=a2test.bin_steps(binary)
    for _ in range(8):
        steps += [labels.until('_ready'), labels.until('_done'), labels.peek('_snapshot',2048), labels.peek('_t80_x')]
    disk=work/'blank.dsk'; disk.write_bytes(bytes(143360))
    result=a2test.run(disk,steps,iie=True)
    data=result.data
    blank=bytearray([0xA5]*2048)
    for bank in (0,1024):
        for row in range(24):
            offset=bank+(row%8)*128+(row//8)*40
            blank[offset:offset+40]=bytes([0xA0])*40
    for scene in range(8):
        expected=blank.copy()
        if scene<2: expected[7*128+39]=ord('X')|128
        if scene==4:
            for col,char in enumerate(b'abc',1):
                expected[(0 if col & 1 else 1024)+2*128+col//2]=char
        if scene==7:
            for bank in (0,1024): expected[bank+7*128+80:bank+7*128+120]=bytes([ord('X')|128])*40
        actual=data[scene*2049:scene*2049+2048]
        assert actual==expected, ('text bounds',scene,next((i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b))
        assert data[scene*2049+2048]==(80,80,0,0,4,79,1,80)[scene],('cursor',scene,data[scene*2049+2048])
    print(f'T80 pointer={pointer}: long strings/fills, inverse text, zero/one-row scrolls and both banks/holes OK.')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='t80-bounds-') as tmp:
        check(Path(tmp))
        check(Path(tmp),True)
