#!/usr/bin/env python3
"""lib/apple2/mb_irq.asm on a2shot with a Mockingboard (its VIA timer IRQs
are emulated): a DOS 3.3 program starts the service at 50 Hz with a tick
that writes AY register 0 = the tick count and register 7 = $3E through
mb_put, spins with fixed A/X/Y, then stops it. Checked: the ticks counted
(mb_irq_ticks and the tick's own count) match 50 Hz of emulated time; the
AY writes decoded from the VIA stores (storewatch of the slot's I/O: ORA
the value, ORB 7 latch / 6 write) are exactly R0 = 1, R7 = $3E, R0 = 2,
3 ... (mb_put's shadow: R7 once), then mb_irq_stop's silence on both
chips; the main loop's registers survive every interrupt; no tick after
mb_irq_stop; the vector is given back. Modes: MB_IRQ_PRODOS = 0 with the
vector at $03FE (//e with the NMOS and the 65C02 builds, //c: the ROM's
handler saves A at $45) and at $FFFE (//e and II+ NMOS, language card
RAM banked in: raw entry; a2shot's II+ ROM sends IRQs to the monitor). The ProDOS mode (ALLOC_INTERRUPT) is WARGALAGA II's, checked
by its test_audio.py on a byte-identical build. Then mb_hush: chip 1's
volumes to 0 and its shadows forgotten (the next tick writes R7 again).
MB_IRQ_HUSH_BOTH = 1 (MB TRACKER, 6 voices): mb_hush silences both chips."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

TICKS = 60
SRC = '''{cpu}
MB_IRQ_PRODOS = 0
MB_IRQ_VECTOR = {vector}
MB_IRQ_HZ = 50
MB_IRQ_TICK = tick
MB_FAST_WRITE = {fast}
MB_IRQ_HUSH_BOTH = {both}
.code
start:  lda #0                   ; (BSS: not cleared by BRUN)
        ldx #9
:       sta found,x
        dex
        bpl :-
        sta mb_irq_ticks
        jsr mb_detect
        sta found
        tax
        bne :+
        jmp done
:
.if MB_IRQ_VECTOR = $FFFE
        lda $C08B                ; language card RAM, read and write
        lda $C08B
.endif
        lda MB_IRQ_VECTOR
        sta oldvec
        lda MB_IRQ_VECTOR+1
        sta oldvec+1
        jsr mb_forget
        jsr mb_irq_start
started:
        lda #$5A
        ldx #$A5
        ldy #$3C
spin:   cmp #$5A                 ; the interrupts keep A, X, Y
        bne bad
        cpx #$A5
        bne bad
        cpy #$3C
        bne bad
        lda mb_irq_ticks
        cmp #{ticks}
        lda #$5A
        bcc spin
stopped:
        jsr mb_irq_stop
        lda mb_irq_ticks
        sta at_stop
        ldx #0                   ; ~30 ms more: no tick
        ldy #6
:       dex
        bne :-
        dey
        bne :-
        lda mb_irq_ticks
        sta after
        lda MB_IRQ_VECTOR
        sta newvec
        lda MB_IRQ_VECTOR+1
        sta newvec+1
.if MB_IRQ_VECTOR = $FFFE
        lda $C082                ; the ROM back
.endif
        lda #1                   ; mb_hush: the next mb_put of R7 writes
        sta hushed
        lda #$3E
        ldx #7
        jsr mb_put               ; (shadowed: no write)
        jsr mb_hush
        lda #$3E
        ldx #7
        jsr mb_put               ; (forgotten: written)
        jmp done
bad:    inc errors
done:   jmp done
tick:   inc ticks                ; R0 = the count, R7 = $3E (written once)
        lda mb_irq_ticks
        ldx #0
        jsr mb_put
        lda #$3E
        ldx #7
        jsr mb_put
        rts
.bss
found:  .res 1
errors: .res 1
ticks:  .res 1
at_stop: .res 1
after:  .res 1
hushed: .res 1
oldvec: .res 2
newvec: .res 2
.code
.include "mb_irq.asm"
.include "mockingboard.asm"
.export start, done, started, stopped
'''


SONG_TICKS = 150
SONG_SRC = '''.setcpu "65C02"
MB_IRQ_PRODOS = 0
MB_IRQ_TICK = ays_tick
MB_FAST_WRITE = 1
AYSONG_CPU65C02 = 1
AYSONG_FAST_PERIODS = {fast}
.code
start:  lda #0
        sta mb_irq_ticks
        jsr mb_detect
        tax                      ; (mb_detect ends with PLP: flags not A's)
        beq done
        jsr mb_forget
        lda #<song
        ldy #>song
        jsr ays_init
        jsr mb_irq_start
:       lda mb_irq_ticks
        cmp #{ticks}
        bcc :-
        jsr mb_irq_stop
done:   jmp done
song:   .byte {song}
.include "mb_irq.asm"
.include "aysong.asm"
.include "mockingboard.asm"
.export start, done
'''


def build(work, name, cpu, vector, fast, text=None, both=0):
    src = work / (name + '.s')
    src.write_text(text or SRC.format(cpu='.setcpu "65C02"' if cpu else '', vector=vector, fast=fast, ticks=TICKS,
                                      both=both))
    obj, binary, lbl = (src.with_suffix(e) for e in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-g', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(lbl),
                    '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(lbl)


def ay_writes(out, slot=4):
    """(chip, register, value) from the storewatch lines, AY protocol."""
    ora = [0, 0]
    reg = [None, None]
    marks, writes = [], []
    # I/O stores print 00>00 (a read of the address): the value is the
    # register the opcode stores.
    pat = r'^store [0-9A-F]{4} ([0-9A-F]{4}) \S+ A=([0-9A-F]{2}) X=([0-9A-F]{2}) Y=([0-9A-F]{2}) .* op=([0-9A-F]{2})'
    for m in re.finditer(pat, out, re.M):
        addr = int(m.group(1), 16)
        op = int(m.group(5), 16)
        a_, x_, y_ = (int(m.group(k), 16) for k in (2, 3, 4))
        new = x_ if op in (0x86, 0x96, 0x8E) else y_ if op in (0x84, 0x94, 0x8C) \
            else 0 if op in (0x64, 0x74, 0x9C, 0x9E) else a_
        base = 0xC000 + slot * 256
        if not base <= addr < base + 256:
            continue
        chip = (addr - base) >> 7
        port = addr & 0x7F
        if port == 1:
            ora[chip] = new
        elif port == 0 and new == 7:
            reg[chip] = ora[chip]
        elif port == 0 and new == 6:
            writes.append((chip, reg[chip], ora[chip]))
    return writes


def run(work, name, cpu, vector, machine, fast=1, both=0):
    binary, L = build(work, name, cpu, vector, fast, both=both)
    disk = a2test.build_disk(work, name.upper(), binary)
    flags = {'iie': ['--iie'], 'iic': ['--iic'], 'ii+': []}[machine]
    out = subprocess.run([str(a2test.A2SHOT), *flags, '--mockingboard', '--disk', str(disk),
                          f'storewatch:C400:C4FF', L.until('started', 2400), L.until('stopped', 200),
                          L.until('done', 100), 'wait:1',
                          f'peek:{L["found"]:04X}:10', f'peek:{L["mb_irq_ticks"]:04X}:1',
                          f'peek:{L["start"]:04X}:1'],
                         capture_output=True, text=True, timeout=180, check=True).stdout
    r = a2test.Result(out)
    state = r.mem(L['found'], 10)
    found, errors, ticks, at_stop, after, hushed = state[:6]
    old, new = state[6:8], state[8:10]
    assert found == 4, f'{name}: Mockingboard in slot 4 ({found})'
    assert errors == 0, f'{name}: A/X/Y changed by an interrupt'
    assert at_stop == TICKS and after == TICKS, f'{name}: ticks {at_stop} at the stop, {after} after'
    assert ticks == TICKS, f'{name}: the tick ran {ticks} times'
    assert old == new, f'{name}: vector {new.hex()} after the stop, {old.hex()} before'
    assert hushed == 1
    w = ay_writes(out)
    expected = [(0, 0, 1), (0, 7, 0x3E)] + [(0, 0, n) for n in range(2, TICKS + 1)]
    assert w[:len(expected)] == expected, f'{name}: AY writes {w[:8]}...'
    rest = w[len(expected):]
    stop = [(c, k, 0) for c in (0, 1) for k in (8, 9, 10)]
    hush = [(c, k, 0) for c in ((0, 1) if both else (0,)) for k in (8, 9, 10)] + [(0, 7, 0x3E)]
    assert rest == stop + hush, f'{name}: after the ticks {rest}'
    cyc = [int(c) for c in re.findall(r'^until [0-9A-F]+ cycles=(\d+)', out, re.M)]
    period = 1020484 // 50 - 2 + 2                 # T1 free run: latch + 2
    span = cyc[1] - cyc[0]
    assert (TICKS - 1) * period <= span <= (TICKS + 1) * period, f'{name}: {span} cycles for {TICKS} ticks'
    return span / TICKS


def song_run(work, fast):
    """The AYS demo played by ays_tick as the interrupt's tick (65C02 build,
    the default AYSONG_WRITE through mb_write, ays_out = mb_shadow): the AY
    writes on the bus are the Python model's, tick for tick."""
    sys.path.insert(0, str(ROOT / 'dev/tools/audio'))
    sys.path.insert(0, str(ROOT / 'dev/tests'))
    import aysong
    import test_aysong
    data = aysong.encode(aysong.demo())
    binary, L = build(work, f'song{fast}', 1, '', 0, SONG_SRC.format(fast=fast, ticks=SONG_TICKS,
                                                                     song=', '.join(map(str, data))))
    disk = a2test.build_disk(work, f'SONG{fast}', binary)
    out = subprocess.run([str(a2test.A2SHOT), '--iie', '--mockingboard', '--disk', str(disk),
                          'storewatch:C400:C4FF', L.until('done', 2400)],
                         capture_output=True, text=True, timeout=180, check=True).stdout
    w = ay_writes(out)
    _, writes = test_aysong.model(data, SONG_TICKS, (), 3)
    expected = [(cr >> 4, cr & 15, v) for cr, v in writes]
    assert w[:len(expected)] == expected, 'the song on the bus'
    assert w[len(expected):] == [(c, k, 0) for c in (0, 1) for k in (8, 9, 10)], 'then the silence'
    return len(expected)


def main():
    if not a2test.have_a2shot('test_mb_irq (Mockingboard IRQs)'):
        return
    with tempfile.TemporaryDirectory(prefix='mbirq-') as tmp:
        work = Path(tmp)
        # (a2shot's II+ ROM vectors IRQ to $FF59, the monitor, not to the
        # Autostart handler at $FA40: on the II+ only the $FFFE mode runs.)
        for name, cpu, vector, machine, fast in (('nmos', 0, '$03FE', 'iie', 0), ('iie', 1, '$03FE', 'iie', 1),
                                                 ('iic', 1, '$03FE', 'iic', 1), ('lcram', 1, '$FFFE', 'iie', 1),
                                                 ('iiplus', 0, '$FFFE', 'ii+', 1)):
            per = run(work, name, cpu, vector, machine, fast)
            print(f'PASS mb_irq {machine}, vector {vector}, {"65C02" if cpu else "NMOS"}'
                  f'{", MB_FAST_WRITE" if fast else ""}: {TICKS} ticks at 50 Hz ({per:.0f} cycles a tick), R0 = 1..{TICKS} and R7 = $3E once '
                  f'(shadow), registers kept, stop: silence, no more ticks, the vector back; mb_hush forgets chip 1')
        run(work, 'both', 1, '$03FE', 'iie', 1, both=1)
        print('PASS mb_irq MB_IRQ_HUSH_BOTH = 1 (MB TRACKER): mb_hush silences both chips and forgets their '
              'shadows (the next mb_put of R7 writes)')
        for fast in (0, 1):
            n = song_run(work, fast)
            print(f'PASS aysong under mb_irq (//e, 65C02 builds{", fast periods" if fast else ""}): the demo\'s '
                  f'{n} AY writes of {SONG_TICKS} ticks on the bus as the Python model, then the silence')


if __name__ == '__main__':
    main()
