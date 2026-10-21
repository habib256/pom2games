#!/usr/bin/env python3
"""joy.asm read_stick_fast in a2run: counts follow both axes (~35 cycles a
turn with joy_cnt in BSS, a2run's paddle timer is value * 11 cycles), C = 0 with a stick,
read_stick unchanged beside it, joy_x / joy_y aliased in zero page."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

SRC = '''.include "apple2.inc"
.zeropage
joy_x:  .res 1                          ; aliases: joy.asm skips its own
joy_y:  .res 1
.code
loop:   JSR     read_stick_fast
        LDA     #0
        ROL     A
        STA     res+2
        LDA     joy_x
        STA     res+0
        LDA     joy_y
        STA     res+1
        JSR     read_stick
        LDA     joy_x
        STA     res+3
        LDA     joy_y
        STA     res+4
        JMP     loop
.bss
res:    .res 5
.code
.include "joy.asm"
.export res, loop
.exportzp joy_x
'''


def main():
    with tempfile.TemporaryDirectory(prefix='joy-') as tmp:
        work = Path(tmp)
        (work / 'j.s').write_text(SRC)
        subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(work / 'j.o'), str(work / 'j.s')],
                       check=True)
        subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 'j.lbl'),
                        '-o', str(work / 'j.bin'), str(work / 'j.o')], check=True)
        L = a2test.labels(work / 'j.lbl')
        assert L['joy_x'] < 0x100, 'joy_x alias not kept in zero page'
        disk = a2test.build_disk(work, 'JOY', work / 'j.bin')
        axes = [(-1, -1), (0, 0), (1, 1), (-1, 1), (0.5, -0.5)]
        steps = ['wait:200', L.until('loop', 4000)]
        for x, y in axes:
            steps += [f'joy:{x},{y}', 'wait:5', L.peek('res', 5)]
        r = a2test.run(disk, steps)
        rows = [r.mem(L['res'], 5, i) for i in range(len(axes))]
    for (x, y), row in zip(axes, rows):
        for axis, v, slow in ((x, row[0], row[3]), (y, row[1], row[4])):
            timer = int((axis + 1) * 127.5 + 0.5) * 11            # cycles
            # 35 cycles a turn while both run, 33-34 once the other axis is done
            assert timer / 35 - 1 <= v <= timer / 33 + 1, f'joy {x},{y}: fast count {v}, timer {timer}'
            assert timer / 25 - 1 <= slow <= timer / 24 + 1, f'joy {x},{y}: read_stick {slow}'
        assert row[2] == 0, f'joy {x},{y}: C = 1 with a stick'
    print('read_stick_fast: counts follow both axes (left/centre/right/mixed), C = 0, '
          'read_stick beside it, zero-page aliases kept.')


if __name__ == '__main__':
    main()
