#!/usr/bin/env python3
"""joy.asm read_stick_x in a2run: the X axis alone at PREAD's scale (11
cycles a count: a2run's paddle timer is value * 11 cycles, so the count is
the value 0..255 within one), C = 0 with a stick, joy_y left alone, the
cost ~11 cycles a count; an unplugged X axis (joy:9,..) saturates at 255
with C = 1; a zero-page joy_x alias is kept."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

SRC = '''.include "apple2.inc"
.zeropage
joy_x:  .res 1                          ; alias: joy.asm skips its own
.code
loop:   LDA     #$A5
        STA     joy_y
        JSR     read_stick_x
        LDA     #0
        ROL     A
        STA     res+1
        LDA     joy_x
        STA     res+0
        LDA     joy_y
        STA     res+2
done:   JMP     loop
.bss
res:    .res 3
.code
.include "joy.asm"
.export res, loop, done
.exportzp joy_x
'''


def main():
    with tempfile.TemporaryDirectory(prefix='joyx-') as tmp:
        work = Path(tmp)
        (work / 'j.s').write_text(SRC)
        subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(work / 'j.o'), str(work / 'j.s')],
                       check=True)
        subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 'j.lbl'),
                        '-o', str(work / 'j.bin'), str(work / 'j.o')], check=True)
        L = a2test.labels(work / 'j.lbl')
        assert L['joy_x'] < 0x100, 'joy_x alias not kept in zero page'
        axes = [(-1, 0), (-0.5, 1), (0, 0), (0, -1), (0.25, 9), (1, -1), (9, 0)]
        steps = [L.until('loop', 4000)]
        for x, y in axes:
            steps += [f'joy:{x},{y}', 'wait:5', L.until('loop', 5), L.until('done', 5), L.peek('res', 3)]
        r = a2test.run(None, a2test.bin_steps(work / 'j.bin') + steps)
        cyc = [int(c) for c in re.findall(r'^until \S+ cycles=(\d+)', r.out, re.M)][1:]
        rows = [r.mem(L['res'], 3, i) for i in range(len(axes))]
    for i, ((x, y), (jx, c, jy)) in enumerate(zip(axes, rows)):
        spent = cyc[2 * i + 1] - cyc[2 * i]
        assert jy == 0xA5, f'joy {x},{y}: joy_y changed ({jy:02X})'
        if x > 1:
            assert jx == 255 and c == 1, f'joy {x},{y}: open X axis read {jx}, C = {c}'
            continue
        value = int((x + 1) * 127.5 + 0.5)
        assert c == 0 and abs(jx - value) <= 1, f'joy {x},{y}: count {jx} for {value}, C = {c}'
        assert spent <= 11 * jx + 60, f'joy {x},{y}: {spent} cycles for a count of {jx}'
    print(f'read_stick_x: counts = the paddle value (PREAD scale, 0/64/128/255 for left/-0.5/centre/right), '
          f'C = 0, joy_y untouched whatever Y is (even unplugged), ~11 cycles a count '
          f'({cyc[5] - cyc[4]} centred), open X axis: 255 and C = 1, zero-page alias kept.')


if __name__ == '__main__':
    main()
