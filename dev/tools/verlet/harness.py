"""Run a physics on the 6502 with an input script and keep snapshots.

The generalised DIRTBIKE phystest driver: a script of rows

    (ticks 1..255, [K input bytes], snapshot?)

stores the K bytes into the K input operands, calls the tick routine
`ticks` times, then (snapshot) copies each snapshot block (operand, length)
after the previous snapshot. a2run runs the binary without a disk
(a2test.bin_steps); run() returns the snapshots, one bytes object each,
for the caller to compare with its Python model.

    snaps = harness.run(prelude, epilogue, inputs=['in_thr', 'in_lean'],
                        snaps=[('vl_xf', 30)], rows=[(10, [8, 0], 1), ...])

prelude: the program's top (definitions, `.include "verlet.inc"`, its
zero page); epilogue: its routines (the tick label) and the library
includes (`.include "verlet.asm"` ... `.include "mul.asm"`). The driver
calls `init` first if given. A snapshot block is up to 255 bytes.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

INCLUDES = [ROOT / 'dev/lib/apple2', ROOT / 'dev/lib/math', ROOT / 'dev/lib/physics']
CFG = ROOT / 'dev/cc65/apple2_hgr.cfg'


def segments(inputs):
    """Per-tick input tuples -> run-length rows (ticks, inputs) of <= 255 ticks."""
    out = []
    for key in inputs:
        key = tuple(key)
        if out and out[-1][1] == key and out[-1][0] < 255:
            out[-1] = (out[-1][0] + 1, key)
        else:
            out.append((1, key))
    return out


def source(prelude, epilogue, inputs, snaps, rows, tick='tick', init=None, snap_seg='BSS'):
    k = len(inputs)
    total = sum(n for _, n in snaps) * sum(1 for r in rows if r[2])
    assert all(0 < n <= 255 for _, n in snaps), snaps
    out = ['.code', '        JMP     hs_start', prelude, '.segment "ZEROPAGE"',
           'hs_snap: .res 2', 'hs_scr:  .res 2', 'hs_left: .res 1', '.code', 'hs_start:']
    if init:
        out.append(f'        JSR     {init}')
    out += ['        LDA     #<hs_snaps', '        STA     hs_snap', '        LDA     #>hs_snaps',
            '        STA     hs_snap+1', '        LDA     #<hs_script', '        STA     hs_scr',
            '        LDA     #>hs_script', '        STA     hs_scr+1',
            'hs_row: LDY     #0', '        LDA     (hs_scr),Y', '        BNE     :+',
            '        JMP     hs_done', ':       STA     hs_left']
    for name in inputs:
        out += ['        INY', '        LDA     (hs_scr),Y', f'        STA     {name}']
    out += ['hs_tick: JSR    ' + tick, '        DEC     hs_left', '        BNE     hs_tick',
            f'        LDY     #{k + 1}', '        LDA     (hs_scr),Y', '        BEQ     hs_next']
    for name, n in snaps:
        out += ['        LDY     #0', f':       LDA     {name},Y', '        STA     (hs_snap),Y',
                '        INY', f'        CPY     #{n}', '        BNE     :-', '        CLC',
                '        LDA     hs_snap', f'        ADC     #{n}', '        STA     hs_snap',
                '        BCC     :+', '        INC     hs_snap+1', ':']
    out += ['hs_next: CLC', '        LDA     hs_scr', f'        ADC     #{k + 2}', '        STA     hs_scr',
            '        BCC     :+', '        INC     hs_scr+1', ':       JMP     hs_row',
            'hs_done: JMP     hs_done', epilogue, '.segment "RODATA"', 'hs_script:']
    for n, vals, snap in rows:
        assert 0 < n <= 255 and len(vals) == k, (n, vals)
        out.append('        .byte ' + ', '.join(str(v & 0xFF) for v in [n, *vals, int(bool(snap))]))
    out += ['        .byte 0', f'.segment "{snap_seg}"', f'hs_snaps: .res {max(total, 1)}',
            '.export hs_done, hs_snaps', '']
    return '\n'.join(out)


def build(work, text, includes=(), cfg=CFG, defines=()):
    work = Path(work)
    (work / 'h.s').write_text(text)
    inc = [a for d in [*includes, *INCLUDES] for a in ('-I', str(d))]
    dfn = [a for d in defines for a in ('-D', d)]
    subprocess.run(['ca65', '-g', *inc, *dfn, '-l', str(work / 'h.lst'), '-o', str(work / 'h.o'),
                    str(work / 'h.s')], check=True)
    subprocess.run(['ld65', '-C', str(cfg), '-m', str(work / 'h.map'), '-Ln', str(work / 'h.lbl'),
                    '-o', str(work / 'h.bin'), str(work / 'h.o')], check=True)
    return a2test.labels(work / 'h.lbl'), work / 'h.bin'


def run(prelude, epilogue, inputs, snaps, rows, tick='tick', init=None, includes=(), cfg=CFG,
        snap_seg='BSS', limit=60000, work=None, load=0x6000):
    """Assemble, run, -> [bytes per snapshot]."""
    size = sum(n for _, n in snaps)
    nsnaps = sum(1 for r in rows if r[2])
    text = source(prelude, epilogue, inputs, snaps, rows, tick, init, snap_seg)
    with tempfile.TemporaryDirectory(prefix='verlet-') as tmp:
        L, binary = build(work or tmp, text, includes, cfg)
        steps = a2test.bin_steps(binary, load) + [L.until('hs_done', limit)]
        total = size * nsnaps
        for off in range(0, total, 4096):
            steps.append(L.peek('hs_snaps', min(4096, total - off), off))
        r = a2test.run(None, steps)
        got = b''.join(r.mem(L['hs_snaps'] + off, min(4096, total - off)) for off in range(0, total, 4096))
    return [got[i * size:(i + 1) * size] for i in range(nsnaps)]
