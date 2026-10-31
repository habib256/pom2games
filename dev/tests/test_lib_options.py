#!/usr/bin/env python3
"""Library options are values, not mere definitions: RWTS_SEI, RWTS_KEEP_ZP,
DOS_SEI, DOS_CMD_HEX_IFREF, STICK_KEY_FAST,
STICK_KEY_REPEAT (lib/apple2), MUL_ACC and MUL_INIT_BOOT (lib/math) assemble the same
bytes when set to 0 as when left out, and differ when set to 1. Then
DOS_SEI = 1 in a2run: a real CATALOG through dos_cmd_run with IRQs enabled
returns C = 0 and the caller's I flag (clear) put back. And hgr_plot.asm
with hgr_plot_tables.inc only assembles with full-width tables, either order."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

INC = ['-I', str(ROOT / 'dev/lib/apple2'), '-I', str(ROOT / 'dev/lib/math'), '-I', str(ROOT / 'dev/lib/hgr')]

RWTS = '''.include "apple2.inc"
DOS_ZP_START = $50
DOS_ZP_LEN = $10
.code
        JSR     rwts_read
        JSR     rwts_find_file
.include "rwts.asm"
'''
DOS = '''.include "apple2.inc"
.bss
apple2_zp_buf: .res 256
.code
        JSR     dos_cmd_run
.include "dos.asm"
'''
MATH = '''MUL_TABLES = $0800
.include "math.inc"
.code
        JSR     mul_init
        JSR     mul_acc_add
        LDA     mul_acc0
.include "mul.asm"
'''
STICK = '''.include "apple2.inc"
.code
        JSR     stick_key
.include "joy.asm"
'''
MATH_NOACC = MATH.replace('        JSR     mul_acc_add\n        LDA     mul_acc0\n', '')


def listing(work, source):
    """Object code and segment use of one assembly, as ca65's listing."""
    src = work / 'o.s'
    src.write_text(source)
    lst = work / 'o.lst'
    r = subprocess.run(['ca65', *INC, '-l', str(lst), '-o', str(work / 'o.o'), str(src)],
                       capture_output=True, text=True)
    if r.returncode:
        return 'error: ' + r.stderr
    # addresses + bytes of the lines that emit code or data (not the source)
    return '\n'.join(line[:24] for line in lst.read_text().splitlines()[4:]
                     if line[11:24].strip())


def options(work):
    for name, base, source in (('RWTS_SEI', RWTS, RWTS), ('RWTS_KEEP_ZP', RWTS, RWTS),
                               ('DOS_SEI', DOS, DOS), ('DOS_CMD_HEX_IFREF', DOS, DOS),
                               ('MUL_INIT_BOOT', MATH_NOACC, MATH_NOACC),
                               ('MUL_ACC', MATH_NOACC, MATH),
                               ('STICK_KEY_FAST', STICK, STICK), ('STICK_KEY_REPEAT', STICK, STICK)):
        plain = listing(work, base)
        zero = listing(work, f'{name} = 0\n' + base)
        one = listing(work, f'{name} = 1\n' + source)
        assert not plain.startswith('error'), (name, plain)
        assert zero == plain, f'{name} = 0 is not the same as leaving it out'
        assert not one.startswith('error') and one != plain, f'{name} = 1 changes nothing'
        if name == 'MUL_ACC':
            assert listing(work, f'{name} = 0\n' + source).startswith('error'), \
                'MUL_ACC = 0 still allocates mul_acc0..2'
    print('Options RWTS_SEI, RWTS_KEEP_ZP, DOS_SEI, DOS_CMD_HEX_IFREF, MUL_INIT_BOOT, MUL_ACC, '
          'STICK_KEY_FAST, STICK_KEY_REPEAT: '
          '= 0 assembles as undefined, = 1 takes effect.')


DOS_RUN = '''.include "apple2.inc"
DOS_SEI = 1
.code
entry:  LDX     #0
@save:  LDA     $00,X
        STA     apple2_zp_buf,X
        INX
        BNE     @save
        JSR     dos_cmd_new
        LDA     #<command
        LDY     #>command
        JSR     dos_cmd_add
        CLI                             ; the program runs with IRQs on
        JSR     dos_cmd_run
        PHP
        PLA
        STA     res                     ; P after the command
        SEI
done:   JMP     done
command: .byte  "CATALOG", 0
.bss
apple2_zp_buf: .res 256
res:    .res 1
.code
.include "dos.asm"
'''


def dos_sei(work):
    from test_asm_boundaries import fixture
    r = fixture(work, 'dossei', DOS_RUN, lambda L: [L.until('done'), L.peek('res')])
    p = r.dumps[0][0]
    assert p & 0x04 == 0, f'DOS_SEI: I flag not put back (P = {p:02X})'
    assert p & 0x01 == 0, f'DOS_SEI: C = 1 after a valid command (P = {p:02X})'
    print('DOS_SEI = 1: CATALOG through dos_cmd_run, C = 0, caller I flag restored.')


def plot_tables(work):
    plot, tables = '.include "hgr_plot.asm"\n', '.include "hgr_plot_tables.inc"\n'
    for full in (False, True):
        for first, second in ((plot, tables), (tables, plot)):
            source = ('HGR_FULL_WIDTH_TABLES = 1\n' if full else '') + \
                '.code\n' + first + second + '.include "hgr_scanline.inc"\n'
            ok = not listing(work, source).startswith('error')
            assert ok == full, f'hgr_plot16 + {"280" if full else "256"}-column tables: ' \
                               f'{"rejected" if full else "accepted"}'
    print('hgr_plot16: 256-column hgr_plot_tables rejected in both include orders.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='lib-options-') as tmp:
        options(Path(tmp))
        plot_tables(Path(tmp))
        dos_sei(Path(tmp))
