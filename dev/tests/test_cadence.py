#!/usr/bin/env python3
"""Long NTSC/PAL cadence runs with real POM2 VIA IRQs, overload and wrap."""
from pathlib import Path
import re
import tempfile
from test_hgr import DEV, run, compile_source, a2test

FRAMES = 1000


def build(work, refresh):
    fixture = work/'cadence.c'
    fixture.write_text('''#include "apple2frame.h"
void clock_start(void); void clock_stop(void);
void burn_short(void); void burn_long(void); void present(void);
unsigned snapshot(void); unsigned char masked_timeout(void);
void checkpoint(void);
void __fastcall__ jump_clock(unsigned distance);
unsigned history[1000]; unsigned skips[1000];
unsigned char blanking[1000];
unsigned long_result[16], long_delta[16];
unsigned total; unsigned char checks[8];
int main(void) {
    unsigned i, base, distance;
    unsigned char period;
    checks[0] = a2_cadence_wait() == A2_CADENCE_TIMEOUT;
    a2_cadence_ticks = 0xff00;
    clock_start();
    checks[1] = a2_cadence_init(2);
    checks[2] = !a2_cadence_init(0);
    checks[3] = !a2_cadence_init(9);
    checks[4] = !a2_cadence_init(255);
    for (i=0; i<1000; ++i) {
        if (i==250 || i==750) burn_long();
        else if (i&1) burn_short();
        skips[i] = a2_cadence_wait();
        present();
        blanking[i] = *(volatile unsigned char*)0xc019;
        history[i] = snapshot();
    }
    total = a2_cadence_missed;
    for (i=0;i<16;++i) {
        period=(i&7)+1;
        distance=i<8 ? 10000u : 32760u;
        a2_cadence_init(period);
        base=snapshot();
        jump_clock(distance);
        long_result[i]=a2_cadence_wait();
        long_delta[i]=snapshot()-base;
    }
    checks[5] = masked_timeout();
    clock_stop();
    checks[6] = a2_cadence_wait() == A2_CADENCE_TIMEOUT;
    checks[7] = a2_cadence_init(8) && a2_cadence_wait()==A2_CADENCE_TIMEOUT;
    checkpoint();
    return 0;
}
''')
    timer = work/'timer.s'
    # VIA free-running T1 has a two-cycle reload interval.
    latch = refresh-2
    timer.write_text(f'''.export _clock_start, _clock_stop, _burn_short, _burn_long
.export _present, _snapshot, _masked_timeout, _checkpoint
.export _jump_clock
.import _a2_cadence_tick, _a2_cadence_ticks, _a2_cadence_wait
.import _a2_frame_init, _a2_frame_wait
.bss
old_vector: .res 2
old_status: .res 1
saved_tick: .res 1
page: .res 1
.code
_clock_start:
    jsr _a2_frame_init
    jsr _a2_frame_wait
    php
    pla
    sta old_status
    sei
    lda $03fe
    sta old_vector
    lda $03ff
    sta old_vector+1
    lda #<handler
    sta $03fe
    lda #>handler
    sta $03ff
    lda #$7f
    sta $c40e
    lda #$40
    sta $c40b
    lda #{latch & 255}
    sta $c404
    lda #{latch >> 8}
    sta $c405
    lda #$c0
    sta $c40e
    cli
    rts
_clock_stop:
    sei
    lda #$7f
    sta $c40e
    lda $c404
    lda old_vector
    sta $03fe
    lda old_vector+1
    sta $03ff
    lda old_status
    pha
    plp
    rts
handler:
    pha
    txa
    pha
    tya
    pha
    lda $c404
    jsr _a2_cadence_tick
    pla
    tay
    pla
    tax
    pla
    rti
_snapshot:
    php
    sei
    lda _a2_cadence_ticks
    ldx _a2_cadence_ticks+1
    plp
    rts
_jump_clock:
    php
    sei
    clc
    adc _a2_cadence_ticks
    sta _a2_cadence_ticks
    txa
    adc _a2_cadence_ticks+1
    sta _a2_cadence_ticks+1
    plp
    rts
_present:
    lda page
    eor #1
    sta page
    tax
    lda $c054,x
    rts
_checkpoint: rts
_burn_short:
    ldy #16
    bne burn
_burn_long:
    ldy #44
burn:
    ldx #0
loop:
    dex
    bne loop
    dey
    bne burn
    rts
_masked_timeout:
    php
    sei
    jsr _a2_cadence_wait
    cmp #$ff
    bne failed
    cpx #$ff
    bne failed
    php
    pla
    and #4
    beq failed
    lda #1
    bne done
failed:
    lda #0
done:
    ldx #0
    plp
    rts
''')
    objects = []
    for source in (DEV/'cc65/crt0_apple2.s', fixture, timer,
                   DEV/'lib/apple2c/apple2cadence.s', DEV/'lib/apple2c/apple2frame.s'):
        obj = work/(source.stem+'.o')
        compile_source(source, obj, ['-t','none','-Oirs','-I',DEV/'lib/apple2c'])
        objects.append(obj)
    labels, binary = work/'cadence.lbl', work/'cadence.bin'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
         '-Ln',labels,'-o',binary,*objects])
    return a2test.build_disk(work,'CADENCE',binary), a2test.labels(labels)


def check(mode, refresh):
    with tempfile.TemporaryDirectory(prefix='pom2-cadence-') as directory:
        work = Path(directory)
        disk, labels = build(work, refresh)
        options = ['--iie','--mockingboard'] + (['--pal'] if mode=='PAL' else [])
        result = run([DEV/'tools/a2shot/a2shot',*options,'--disk',disk,
                      f'tracepc:{labels["_present"]:04X}:{FRAMES}:3500',
                      f'until:{labels["_checkpoint"]:04X}:400',
                      labels.peek('_history',FRAMES*2),
                      labels.peek('_skips',FRAMES*2),
                      labels.peek('_total',2), labels.peek('_checks',8),
                      labels.peek('_blanking',FRAMES),
                      labels.peek('_long_result',32), labels.peek('_long_delta',32)])
        cycles = [int(n) for n in re.findall(r'tracepc [0-9A-F]+ cycles=(\d+)', result)]
        parsed = a2test.Result(result)
        dumps = [parsed.mem(labels[name], size) for name,size in
                 (('_history',FRAMES*2),('_skips',FRAMES*2),('_total',2),('_checks',8),('_blanking',FRAMES),
                  ('_long_result',32),('_long_delta',32))]
        history = [int.from_bytes(dumps[0][i:i+2],'little') for i in range(0,FRAMES*2,2)]
        skips = [int.from_bytes(dumps[1][i:i+2],'little') for i in range(0,FRAMES*2,2)]
        assert len(cycles)==FRAMES, len(cycles)
        assert dumps[3]==bytes([1]*8), ('invalid input, timeout or IRQ mask',dumps[3])
        assert not any(v&128 for v in dumps[4]), 'presentation outside VBL'
        assert int.from_bytes(dumps[2],'little')==2, dumps[2]
        assert skips==[int(i in (250,750)) for i in range(FRAMES)], skips
        for i in range(16):
            period=(i&7)+1; distance=10000 if i<8 else 32760
            outcome=int.from_bytes(dumps[5][2*i:2*i+2],'little')
            delta=int.from_bytes(dumps[6][2*i:2*i+2],'little')
            assert outcome==distance//period, (i,'long suspension',outcome)
            assert delta==(distance//period+1)*period, (i,'original deadline grid',delta)
        assert history[0]==0xff02, hex(history[0])
        assert any(history[i]<history[i-1] for i in range(1,FRAMES)), 'no counter wrap'
        ordinary = []
        for i in range(1,FRAMES):
            ticks = (history[i]-history[i-1]) & 65535
            assert ticks==(4 if skips[i] else 2), (i,ticks,skips[i])
            span = cycles[i]-cycles[i-1]
            assert abs(span-ticks*refresh)<200, (i,span,ticks*refresh)
            if not skips[i]: ordinary.append(span)
        print(f'{mode}: {FRAMES} presentations, ordinary intervals '
              f'{min(ordinary)}..{max(ordinary)} cycles; overloads and 16 long suspensions, wrap/timeout/IRQ mask OK')


def main():
    run(['make','-s','-C',DEV/'tools/a2shot'])
    check('NTSC',17030)
    check('PAL',20280)


if __name__=='__main__':
    main()
