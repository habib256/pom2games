#!/usr/bin/env python3
"""mouse.s without a mouse (a2run's II+ has no card): mouse_init answers 0,
then _mouse_timing_mode and _mouse_serve_irq return C = 1 at once instead of
jumping into an empty slot ROM, before and after mouse_init."""
import sys
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

SRC = '''.import _mouse_init, _mouse_timing_mode, _mouse_serve_irq, _mouse_slot
.exportzp ptr1
.export res, finished
.zeropage
ptr1:   .res 2
.bss
res:    .res 6
.code
entry:  SEI
        LDX     #5
        LDA     #0
@clr:   STA     res,X                   ; BSS is not cleared
        DEX
        BPL     @clr
        STA     _mouse_slot             ; BSS as cc65's crt0 leaves it
        LDA     #9
        JSR     _mouse_timing_mode      ; before mouse_init
        ROL     res+0
        JSR     _mouse_serve_irq
        ROL     res+1
        JSR     _mouse_init
        STA     res+2                   ; slot found: none
        LDA     #9
        JSR     _mouse_timing_mode
        ROL     res+3
        JSR     _mouse_serve_irq
        ROL     res+4
        INC     res+5                   ; reached the end
finished:
        JMP     finished
'''


def main():
    with tempfile.TemporaryDirectory(prefix='mouse-noslot-') as tmp:
        work = Path(tmp)
        (work / 't.s').write_text(SRC)
        cfg = work / 't.cfg'
        cfg.write_text('''MEMORY { ZP: start=$50, size=$10, type=rw; RAM: start=$6000, size=$3600, file=%O; }
SEGMENTS { ZEROPAGE: load=ZP, type=zp; CODE: load=RAM, type=ro; RODATA: load=RAM, type=ro;
           BSS: load=RAM, type=bss; }
''')
        objs = []
        for name, src in (('t', work / 't.s'), ('mouse', ROOT / 'dev/lib/mouse/mouse.s')):
            obj = work / (name + '.o')
            subprocess.run(['ca65', '-o', str(obj), str(src)], check=True)
            objs.append(str(obj))
        subprocess.run(['ld65', '-C', str(cfg), '-Ln', str(work / 't.lbl'), '-o', str(work / 't.bin'),
                        *objs], check=True)
        L = a2test.labels(work / 't.lbl')
        disk = a2test.build_disk(work, 'NOSLOT', work / 't.bin')
        r = a2test.run(disk, ['wait:200', L.until('finished', 4000), L.peek('res', 6)])
        res = r.mem(L['res'], 6)
    assert res[5] == 1, f'never reached the end: {list(res)}'
    assert res[2] == 0, f'mouse_init found a mouse in slot {res[2]}'
    assert list(res[0:2]) == [1, 1] and list(res[3:5]) == [1, 1], f'C = 0 without a mouse: {list(res)}'
    print('Mouse without a card: timing_mode / serve_irq return C = 1, before and after mouse_init.')


if __name__ == '__main__':
    main()
