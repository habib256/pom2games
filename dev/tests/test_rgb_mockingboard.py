#!/usr/bin/env python3
"""Actual ASM execution with traced RGB soft switches and modeled VIA/AY buses."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile

DEV = Path(__file__).resolve().parents[1]


def build(work, name, source):
    src=work/(name+'.s'); src.write_text(source)
    obj=src.with_suffix('.o'); binary=src.with_suffix('.bin')
    cfg=work/'hardware.cfg'
    cfg.write_text('''MEMORY { ZP: start=$50,size=$B0,type=rw;
 RAM: start=$6000,size=$3600,type=rw,file=%O; }
SEGMENTS { ZEROPAGE: load=ZP,type=zp; CODE: load=RAM,type=ro; BSS: load=RAM,type=bss; }
''')
    subprocess.run(['ca65','-I',str(DEV/'lib/apple2'),'-o',str(obj),str(src)],check=True)
    subprocess.run(['ld65','-C',str(cfg),'-o',str(binary),str(obj)],check=True)
    return binary


def run(probe, binary, machine, slot=0, irq=0):
    lines=subprocess.check_output([str(probe),str(binary),str(machine),str(slot),str(irq)],text=True).splitlines()
    state=bytes.fromhex(next(s[6:] for s in lines if s.startswith('STATE ')))
    return lines, state


def rgb(work, probe):
    for mode in ('col140','hgr','dhgr'):
        binary=build(work,'rgb_'+mode,f'''.code
entry:
    jsr rgb_{mode}
    sta $1020
    stx $1021
    lda #1
    sta $10FF
finished: jmp finished
.include "rgb.asm"
.include "rgb.asm"
''')
        for machine in (0,1,2):
            lines,state=run(probe,binary,machine)
            bus=[int(line.split()[1],16) for line in lines if line[:2] in ('W ','R ')]
            if not machine:
                assert state[:2]==bytes([int(mode=='hgr'),0])
                assert bus==([0xC057,0xC054,0xC052,0xC050] if mode=='hgr' else []),lines
            else:
                assert state[:2]==b'\x01\x00'
                edges=[0xC00D,0xC05E,0xC05F,0xC05E,0xC05F,0xC05E]
                if mode=='hgr': edges += [0xC05F,0xC00C]
                if mode!='col140': edges += [0xC000,0xC002,0xC004,0xC057,0xC054,0xC052,0xC050]
                assert bus==edges,lines
                expected='RGB 3 '+('0 1' if mode=='hgr' else '1 0')
                assert expected in lines,lines
    print('RGB: COL140 edge order, HGR/DHGR entry, II+/IIe/IIc and duplicate inclusion OK.')


def mockingboard(work, probe):
    binary=build(work,'mockingboard','''.code
entry:
    jsr mb_tick
    sta $1020
    lda #0
    ldx #1
    jsr mb_timer_start
    jsr mb_stop
    lda #0
    sta $10FE
    jsr mb_detect
    sta $1020
    php
    pla
    and #4
    sta $1021
    lda #1
    sta $10FE
    lda $1020
    bne play
    jmp finish
play:
    lda #0
    jsr mb_init
    sta $1022
    lda #$34
    ldx #0
    jsr mb_write
    lda #1
    sta mb_chip
    lda #15
    ldx #10
    jsr mb_write
    lda #99
    ldx #16
    jsr mb_write
    lda #2
    sta $10FE
    lda #0
    ldx #1
    jsr mb_timer_start
.repeat 300
    nop
.endrepeat
    jsr mb_tick
    sta $1023
    jsr mb_tick
    sta $1024
    lda #0
    ldx #2
    jsr mb_timer_start
    jsr mb_stop
    lda mb_chip
    sta $1025
    jsr mb_tick
    sta $1026
    php
    pla
    and #4
    sta $1027
finish:
    lda #1
    sta $10FF
finished: jmp finished
.include "mockingboard.asm"
.include "mockingboard.asm"
''')
    for machine in (0,1,2):
        for slot in (0,1,2,4,5,6,7):
            for irq in (0,1):
                lines,state=run(probe,binary,machine,slot,irq)
                assert state[0]==slot,(machine,slot,lines)
                assert state[1]==4*irq
                # Safe no-ops before init do not touch any I/O address.
                assert not any(l.startswith('W ') for l in lines[:lines.index('S 0')]),lines
                writes=[l.split() for l in lines if l.startswith('W ')]
                assert all(int(l[3],16)&4 for l in writes), 'hardware writes must mask IRQ'
                assert not any(l[1] in ('C080','C082','C003','C005') for l in writes),lines
                if not slot:
                    assert len(writes)==int(machine==2),lines  # //c wake only
                    continue
                assert state[2:8]==bytes([0,1,0,1,0,4*irq]),(machine,slot,state)
                assert 'VIA0 20 55' in lines and 'VIA1 20 55' in lines,lines
                for chip in (0,1):
                    registers=bytes.fromhex(next(l[4:] for l in lines if l.startswith(f'AY{chip} ')))
                    assert registers[8:11]==bytes(3),lines
                    if chip==0: assert registers[0]==0x34,lines
                # The first/second chip use the six-step AY write protocol.
                after=lines[lines.index('S 1')+1:lines.index('S 2')]
                protocol=[(int(l.split()[1],16),int(l.split()[2],16)) for l in after if l.startswith('W ')]
                base=0xC000+slot*256
                expected=[]
                for chip,reg,value in ((0,0,0x34),(1,10,15)):
                    b=base+chip*128
                    expected += [(b+1,reg),(b,7),(b,4),(b+1,value),(b,6),(b,4)]
                assert protocol==expected,lines
    print('Mockingboard: 42 machine/slot/IRQ configurations; absence, 4c wake, dual AY writes, three-voice silence, polling and timer state restoration OK.')


def mockingboard_reinit(work, probe):
    for restart in ('lda #4\n    jsr mb_init', 'jsr mb_detect'):
        binary=build(work,'mockingboard_reinit','''.code
entry:
    jsr mb_detect
    lda #0
    ldx #1
    jsr mb_timer_start
    ''' + restart + '''
    jsr mb_stop
    jsr mb_tick
    sta $1020
    php
    pla
    and #4
    sta $1021
    lda #1
    sta $10FF
finished: jmp finished
.include "mockingboard.asm"
''')
        for machine in (0,1,2):
            for irq in (0,1):
                lines,state=run(probe,binary,machine,4,irq)
                assert state[:2]==bytes([0,4*irq]),lines
                assert 'VIA0 20 55' in lines and 'VIA1 20 55' in lines,lines
    print('Mockingboard: reinitialisation and rediscovery restore an active timer and preserve the IRQ mask.')


def mockingboard_session_transitions(work, probe):
    cases=(
        ('invalid', 'lda #0\n    jsr mb_init', bytes([0,4,1])),
        ('different_slot', 'lda #5\n    jsr mb_init', bytes([5,5,0])),
        # Simulate unsuccessful probes while keeping the old VIA readable,
        # so its saved state can still be checked after rediscovery fails.
        ('absent', '''lda #$A9
    sta mb_t1_probe
    lda #1
    sta mb_t1_probe+1
    lda #$60
    sta mb_t1_probe+2
    jsr mb_detect''', bytes([0,0,0])),
    )
    for name,transition,expected in cases:
        binary=build(work,'mockingboard_'+name,'''.code
entry:
    jsr mb_detect
    lda #0
    ldx #1
    jsr mb_timer_start
    ''' + transition + '''
    sta $1020
    lda mb_slot
    sta $1021
    lda mb_timer_active
    sta $1022
    jsr mb_stop
    lda #1
    sta $10FF
finished: jmp finished
.include "mockingboard.asm"
''')
        for machine in (0,1,2):
            for irq in (0,1):
                lines,state=run(probe,binary,machine,4,irq)
                assert state[:3]==expected,(name,lines)
                assert 'VIA0 20 55' in lines and 'VIA1 20 55' in lines,(name,lines)
    print('Mockingboard: invalid init retains the session; slot changes and failed rediscovery release the old timer.')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='rgb-mockingboard-') as tmp:
        work=Path(tmp); probe=work/'hardware_bus'
        subprocess.run([*shlex.split(os.environ.get('CC','cc')),'-O1','-g',
                        '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                        '-I',str(DEV/'tools/a2run'),str(DEV/'tests/hardware_bus.c'),
                        str(DEV/'tools/a2run/cpu6502.c'),'-o',str(probe)],check=True)
        rgb(work,probe)
        mockingboard(work,probe)
        mockingboard_reinit(work,probe)
        mockingboard_session_transitions(work,probe)
