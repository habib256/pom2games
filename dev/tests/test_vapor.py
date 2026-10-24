#!/usr/bin/env python3
"""lib/apple2 vapor.asm: the vapor lock on the floating bus, in a2run (II+)
and, when it is built, a2shot (POM2: II+ NTSC and PAL, enhanced //e).

The fixture shows HGR page 1, marks line 191, scatters lone $80 bytes over
the screen (they must not fake a sync), measures a frame with vapor_count,
then syncs forever on two alternating labels. Every sync must come exactly
one frame after the previous one, at the same point of the frame; with the
marker wiped, vapor_sync must give up (C = 1) after its 65536 polls."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

SOURCE = r'''
.include "apple2.inc"
.export s1, s2, fail, count, count_c
.segment "ZEROPAGE"
ptr:    .res 2
.segment "CODE"
start:  LDA TXTCLR
        LDA HIRES
        LDA MIXCLR
        LDA LOWSCR
        LDA #$20                ; clear HGR page 1
        STA ptr+1
        LDA #0
        STA ptr
        TAY
@clr:   STA (ptr),Y
        INY
        BNE @clr
        INC ptr+1
        LDX ptr+1
        CPX #$40
        BNE @clr
        JSR vapor_mark
        LDA #$80                ; lone markers elsewhere: no false sync
        STA $2000
        STA $2427
        STA $3B50
        STA $3FCF               ; right before line 191 in memory
        JSR vapor_count
        STA count
        STX count+1
        LDA #0
        ROL A
        STA count_c
loop:   JSR vapor_sync
s1:     BCS fail
        JSR vapor_sync
s2:     BCS fail
        JMP loop
fail:   JMP fail
.segment "BSS"
count:  .res 2
count_c: .res 1
.segment "CODE"
.include "vapor.asm"
'''


def build(work):
    (work / 'v.s').write_text(SOURCE)
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(work / 'v.o'), str(work / 'v.s')],
                   check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 'v.lbl'),
                    '-o', str(work / 'v.bin'), str(work / 'v.o')], check=True)
    return a2test.labels(work / 'v.lbl'), work / 'v.bin'


def check(name, L, run, frame, syncs=8):
    steps = [L.until('s1', 3000)] + [L.until(n, 3) for n in ('s2', 's1') * (syncs // 2)] + \
        [L.peek('count', 2), L.peek('count_c')]
    r = run(steps)
    cycles = r.cycles[-syncs - 1:]
    gaps = [b - a for a, b in zip(cycles, cycles[1:])]
    assert all(abs(g - frame) <= 13 for g in gaps), (name, gaps)
    phases = {c % frame for c in cycles}
    assert max(phases) - min(phases) <= 26, (name, sorted(phases))
    count = int.from_bytes(r.mem(L['count'], 2), 'little')
    assert r.mem(L['count_c'], 1) == b'\0' and abs(count - frame / 13) < 20, (name, count)
    wipe = [f'poke:{0x3FD0 + i:04X}:00' for i in range(24)]
    r = run(steps[:2] + wipe + [L.until('fail', 60)])
    print(f'PASS {name}: a sync every {frame} cycles (+-{max(abs(g - frame) for g in gaps)}), '
          f'same point of the frame (spread {max(phases) - min(phases)}), vapor_count {count}; '
          'no marker: C = 1 within 60 frames (65536 polls)')
    return count


def main():
    with tempfile.TemporaryDirectory(prefix='vapor-') as tmp:
        work = Path(tmp)
        L, binary = build(work)
        ntsc = check('a2run II+', L, lambda s: a2test.run(None, a2test.bin_steps(binary) + s), 17030)
        if not a2test.have_a2shot('vapor lock on POM2'):
            return
        disk = a2test.build_disk(work, 'VAPOR', binary)
        shot = lambda s, **kw: a2test.run(disk, s, emulator=a2test.A2SHOT, **kw)  # noqa: E731
        check('POM2 II+ NTSC', L, shot, 17030)
        pal = check('POM2 II+ PAL', L, lambda s: shot(s, pal=True), 20280)
        check('POM2 //e enhanced', L, lambda s: shot(s, iie=True), 17030)
        print(f'PASS PAL / NTSC frame in polls: {pal / ntsc:.3f} (20280 / 17030 = {20280 / 17030:.3f})')


if __name__ == '__main__':
    main()
