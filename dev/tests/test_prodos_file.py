#!/usr/bin/env python3
"""Execute the real ASM/C file helpers on a 65C02, with an injected MLI.

The stub only implements the MLI calling convention and controlled results;
it does not replace the helpers under test. Real ProDOS separately checks
replacement with shorter/empty files and missing-file creation on disk.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'
PD = DEV / 'lib/prodos'
sys.path.insert(0, str(DEV / 'tools'))
import a2test

CFG = '''MEMORY {
 ZP: start=$50,size=$B0,type=rw;
 RAM: start=$6000,size=$5000,type=rw,file=%O;
}
SEGMENTS { ZEROPAGE: load=ZP,type=zp,optional=yes;
 CODE: load=RAM,type=ro; RODATA: load=RAM,type=ro,optional=yes;
 DATA: load=RAM,type=rw,optional=yes; BSS: load=RAM,type=bss,optional=yes; }
'''

STUB = '''
.setcpu "65C02"
.code
setup:  cld
        sei
        lda #0
        ldx #0
:       sta errors,x
        inx
        bne :-
        ldx #stub_end-log-1
:       sta log,x
        dex
        bpl :-
        lda #$4C
        sta $BF00
        lda #<mli
        sta $BF01
        lda #>mli
        sta $BF02
        rts
; Read the inline command/parameter address and skip the three inline bytes.
; No ZP borrowed, so ZP sentinels also check the helpers' no-ZP contract.
mli:    sty saved_y
        tsx
        lda $0101,x
        sta fetch+1
        clc
        adc #3
        sta $0101,x
        lda $0102,x
        sta fetch+2
        adc #0
        sta $0102,x
        ldy #1
        jsr fetch
        sta command
        ldx log_count
        sta log,x
        inc log_count
        iny
        jsr fetch
        sta param_get+1
        sta param_put+1
        iny
        jsr fetch
        sta param_get+2
        sta param_put+2
        ldy #1
        jsr param_get
        ldx log_count
        sta refs-1,x
        lda command
        cmp #$C8
        beq opened
        cmp #$CA
        beq transfer
        cmp #$CB
        beq transfer
        cmp #$D0
        beq eof
        cmp #$CE
        beq stub_mark
        bra result
stub_mark:                      ; SET_MARK: its list (count, ref, 24-bit mark)
        ldy #4
:       jsr param_get
        sta mark_seen,y
        dey
        bpl :-
        bra result
opened: inc opens
        ldy #5
        lda #$07
        jsr param_put
        bra result
eof:    ldy #4
:       jsr param_get
        sta eof_seen,y
        dey
        bpl :-
        bra result
transfer:
        ldy #6
        jsr param_get
        sta actual_seen
        iny
        jsr param_get
        sta actual_seen+1
        ldx #25
:       lda $BF57,x
        sta bitmap_seen,x
        dex
        bpl :-
        lda leave_actual
        bne result
        ldy #6
        lda actual
        jsr param_put
        iny
        lda actual+1
        jsr param_put
result: ldx command
        lda errors,x
        cpx #$C8
        bne :+
        ldx opens
        cpx #2
        bne :+
        lda reopen_error
:       ldy saved_y
        cmp #1
        rts
fetch:  lda $FFFF,y
        rts
param_get: lda $FFFF,y
        rts
param_put: sta $FFFF,y
        rts
.bss
errors: .res 256
log: .res 16
refs: .res 16
log_count: .res 1
opens: .res 1
reopen_error: .res 1
leave_actual: .res 1
actual: .res 2
actual_seen: .res 2
eof_seen: .res 5
mark_seen: .res 5
bitmap_seen: .res 26
saved_y: .res 1
command: .res 1
stub_end:
'''


def compile_asm(work, name, source, extra=(), config=CFG):
    src = work / (name + '.s')
    src.write_text(source)
    obj = src.with_suffix('.o')
    subprocess.run(['ca65', '--cpu', '65c02', '-g', '-I', str(PD), '-I', str(DEV / 'lib/apple2'),
                    '-o', str(obj), str(src)], check=True)
    cfg = work / 'test.cfg'
    cfg.write_text(config)
    binary, lbl = src.with_suffix('.bin'), src.with_suffix('.lbl')
    subprocess.run(['ld65', '-C', str(cfg), '-Ln', str(lbl), '-o', str(binary),
                    str(obj), *map(str, extra)], check=True)
    return binary, a2test.labels(lbl)


def asm_fixture(work, include='file.asm', name='asm', entrypoints=None):
    if entrypoints is None:
        entrypoints = ('prodos_open', 'prodos_close', 'prodos_read',
                       'prodos_read_free', 'prodos_write', 'prodos_load',
                       'prodos_load_free', 'prodos_save', 'prodos_load_at')
    refs = '.code\n' + ''.join(f' jsr {fn}\n' for fn in entrypoints)
    return compile_asm(work, name, refs + f'.include "{include}"\n' + STUB)


def c_fixture(work):
    src = work / 'calls.c'
    src.write_text('''#include "prodos.h"
unsigned char c_load(void) { return prodos_load(); }
unsigned char c_free(void) { return prodos_load_free(); }
unsigned char c_save(void) { return prodos_save(); }
unsigned char c_at(void) { return prodos_load_at(); }
void c_mark(void) { prodos_file_mark = 0x123456ul; }
''')
    cobj, pobj = work / 'calls.o', work / 'file.o'
    subprocess.run(['cl65', '-t', 'none', '--cpu', '65c02', '-Oirs', '-I', str(PD),
                    '-c', '-o', str(cobj), str(src)], check=True)
    # file_at.s: file.s plus prodos_load_at (PRODOS_FILE_AT_SRCS).
    subprocess.run(['ca65', '-g', '-I', str(PD), '-o', str(pobj), str(PD / 'file_at.s')], check=True)
    return compile_asm(work, 'c', STUB, (cobj, pobj))


def invoke(binary, labels, fn, buf=0x2000, length=0x100, errors=(), actual=0x100,
           stale=0xBEEF, leave=False, reopen=0, mark=None):
    L = labels
    steps = [f'load:{binary}@6000', f'call:{L["setup"]:04X}:2']
    def byte(name, value, offset=0):
        steps.append(L.poke(name, value, offset))
    def word(name, value):
        byte(name, value & 255)
        byte(name, value >> 8, 1)
    for addr in range(0x100):
        steps.append(f'poke:{addr:04X}:{(addr ^ 0xA5):02X}')
    # Deliberately nonuniform allocation bits and guards on both sides.
    bitmap = bytes((i * 37 + 0xA5) & 255 for i in range(26))
    for i, value in enumerate(bitmap):
        steps.append(f'poke:{0xBF57+i:04X}:{value:02X}')
    word('pf_buf', buf)
    word('pf_len', length)
    word('pf_got', stale)
    word('actual', actual)
    byte('leave_actual', int(leave))
    byte('reopen_error', reopen)
    if mark is not None:
        for i in range(3):
            byte('pf_mark', mark >> 8 * i & 255, i)
    for command, error in errors:
        byte('errors', error, command)
    steps += ['regs:77:88:9A', f'call:{L[fn]:04X}:3', L.peek('pf_err'),
              L.peek('pf_got', 2), L.peek('log_count'), L.peek('log', 16),
              L.peek('refs', 16), L.peek('eof_seen', 5), L.peek('mark_seen', 5),
              L.peek('actual_seen', 2),
              L.peek('bitmap_seen', 26), 'peek:BF57:26', 'peek:0000:256']
    disk = binary.parent / 'stub.dsk'
    if not disk.exists():
        disk.write_bytes(bytes(143360))
    r = a2test.run(disk, steps, iie=True)
    calls = re.findall(r'call [0-9A-F]+ cycles=\d+ elapsed=(\d+) A=([0-9A-F]+) X=([0-9A-F]+) Y=([0-9A-F]+) P=([0-9A-F]+)', r.out)
    elapsed, a, x, y, p = (int(v, 10 if i == 0 else 16) for i, v in enumerate(calls[-1]))
    err = r.mem(L['pf_err'], 1)[0]
    assert a == err and (p & 1) == int(err != 0), (fn, err, a, p)
    assert y == 0x9A, (fn, 'Y changed', y)
    if fn.startswith('_'):
        assert x == 0, (fn, 'C ABI X', x)
    assert r.mem(0xBF57, 26) == bitmap, (fn, 'bitmap/guards not restored')
    assert r.mem(0, 256) == bytes(i ^ 0xA5 for i in range(256)), 'ZP changed'
    count = r.mem(L['log_count'], 1)[0]
    return dict(error=err, actual=int.from_bytes(r.mem(L['pf_got'], 2), 'little'),
                log=r.mem(L['log'], 16)[:count], refs=r.mem(L['refs'], 16)[:count],
                eof=r.mem(L['eof_seen'], 5), mark=r.mem(L['mark_seen'], 5), bitmap=r.mem(L['bitmap_seen'], 26),
                initial_actual=r.mem(L['actual_seen'], 2), cycles=elapsed, original=bitmap)


def injected(work):
    asm, L = asm_fixture(work)
    c, C = c_fixture(work)
    count = 0
    for binary, labels, load, free, save, at in (
            (asm, L, 'prodos_load', 'prodos_load_free', 'prodos_save', 'prodos_load_at'),
            (c, C, '_c_load', '_c_free', '_c_save', '_c_at')):
        # Independent failure at each stage, including simultaneous failures.
        cases = [({}, 0, bytes([0xC8, 0xCA, 0xCC]), 0x100),
                 ({'errors': [(0xC8, 0x46)]}, 0x46, b'\xC8', 0),
                 ({'errors': [(0xC8, 0x27)]}, 0x27, b'\xC8', 0),
                 ({'errors': [(0xCA, 0x4C)], 'actual': 0}, 0x4C, b'\xC8\xCA\xCC', 0),
                 ({'errors': [(0xCA, 0x27)], 'actual': 17}, 0x27, b'\xC8\xCA\xCC', 17),
                 ({'errors': [(0xCC, 0x2E)]}, 0x2E, b'\xC8\xCA\xCC', 0x100),
                 ({'errors': [(0xCA, 0x27), (0xCC, 0x2E)], 'leave': True}, 0x27, b'\xC8\xCA\xCC', 0)]
        for fn in (load, free):
            for options, error, log, actual in cases:
                r = invoke(binary, labels, fn, **options)
                assert (r['error'], r['log'], r['actual']) == (error, log, actual), (fn, options, r)
                assert r['initial_actual'] == b'\0\0', r
                if len(log) > 1:
                    assert r['refs'][1:] == b'\x07\x07', r
                count += 1
        savecases = [({}, 0, b'\xC8\xCB\xD0\xCC', 0x100),
                     ({'errors': [(0xC8, 0x27)]}, 0x27, b'\xC8', 0),
                     ({'errors': [(0xC8, 0x46)]}, 0, b'\xC8\xC0\xC8\xCB\xD0\xCC', 0x100),
                     ({'errors': [(0xC8, 0x46), (0xC0, 0x2B)]}, 0x2B, b'\xC8\xC0', 0),
                     ({'errors': [(0xC8, 0x46)], 'reopen': 0x42}, 0x42, b'\xC8\xC0\xC8', 0),
                     ({'errors': [(0xCB, 0x48), (0xCC, 0x2E)], 'actual': 17}, 0x48, b'\xC8\xCB\xCC', 17),
                     ({'errors': [(0xCB, 0x2B)], 'leave': True}, 0x2B, b'\xC8\xCB\xCC', 0),
                     ({'errors': [(0xD0, 0x27), (0xCC, 0x2E)]}, 0x27, b'\xC8\xCB\xD0\xCC', 0x100),
                     ({'errors': [(0xCC, 0x2E)]}, 0x2E, b'\xC8\xCB\xD0\xCC', 0x100),
                     ({'length': 0, 'actual': 0}, 0, b'\xC8\xCB\xD0\xCC', 0)]
        for options, error, log, actual in savecases:
            r = invoke(binary, labels, save, **options)
            assert (r['error'], r['log'], r['actual']) == (error, log, actual), (save, options, r)
            if 0xD0 in log:
                assert r['eof'] == b'\x02\x07' + actual.to_bytes(3, 'little'), r
            for command, ref in zip(r['log'], r['refs']):
                if command in (0xCB, 0xCC, 0xD0):
                    assert ref == 7, r
            count += 1
        # prodos_load_at: OPEN, SET_MARK (24 bits, the file's ref), READ,
        # CLOSE; SET_MARK's error ($4D past the end) skips the READ.
        atcases = [({}, 0, b'\xC8\xCE\xCA\xCC', 0x100),
                   ({'errors': [(0xC8, 0x46)]}, 0x46, b'\xC8', 0),
                   ({'errors': [(0xCE, 0x4D)]}, 0x4D, b'\xC8\xCE\xCC', 0),
                   ({'errors': [(0xCE, 0x4D), (0xCC, 0x2E)]}, 0x4D, b'\xC8\xCE\xCC', 0),
                   ({'errors': [(0xCA, 0x4C)], 'actual': 0}, 0x4C, b'\xC8\xCE\xCA\xCC', 0),
                   ({'errors': [(0xCA, 0x27)], 'actual': 9}, 0x27, b'\xC8\xCE\xCA\xCC', 9),
                   ({'errors': [(0xCC, 0x2E)], 'actual': 0x99}, 0x2E, b'\xC8\xCE\xCA\xCC', 0x99)]
        for options, error, log, actual in atcases:
            r = invoke(binary, labels, at, mark=0xABCDEF, **options)
            assert (r['error'], r['log'], r['actual']) == (error, log, actual), (at, options, r)
            assert all(ref == 7 for ref in r['refs'][1:]), r
            if 0xCE in log:
                assert r['mark'] == b'\x02\x07\xEF\xCD\xAB', (at, r['mark'].hex())
            count += 1
        r = invoke(binary, labels, free, buf=0xBFFF, length=2,
                   errors=[(0xCC, 0x2E)])
        assert (r['error'], r['actual'], r['log']) == (0x56, 0, b'\xC8\xCC'), r
        count += 1
    assert C['_prodos_file_mark'] == C['pf_mark'], 'C prodos_file_mark is the SET_MARK field'
    for fn, command in (('prodos_read', 0xCA), ('prodos_write', 0xCB)):
        r = invoke(asm, L, fn, errors=[(command, 0x27)], leave=True)
        assert (r['error'], r['actual'], r['initial_actual']) == (0x27, 0, b'\0\0'), r
        count += 1
    # Boundaries include the exact exclusive end $C000, beyond it, high
    # starts, 16-bit wrap, maximal lengths, and zero lengths at any address.
    ranges = [(0, 1), (0, 0xC000), (0, 0xFFFF), (0x2000, 0x2000),
              (0x2001, 0xFF), (0x20FF, 2), (0xBFFF, 1), (0xBFFF, 2),
              (0xBF00, 0x100), (0xBF00, 0x101), (0xC000, 1), (0xFFFF, 1),
              (0xFFFF, 2), (0xFF00, 0x100), (0x8000, 0x8000),
              (0, 0), (0x2000, 0), (0xC000, 0), (0xFFFF, 0)]
    for fn in ('prodos_read_free', 'prodos_load_free'):
        for buf, length in ranges:
            valid = length == 0 or buf + length <= 0xC000
            r = invoke(asm, L, fn, buf, length, actual=min(length, 17))
            assert r['error'] == (0 if valid else 0x56), (fn, buf, length, r)
            log = (b'\xCA' if valid else b'')
            if fn == 'prodos_load_free':
                log = b'\xC8' + log + b'\xCC'
            assert r['log'] == log, (fn, buf, length, r)
            assert r['actual'] == (min(length, 17) if valid else 0), r
            if valid:
                expected = bytearray(r['original'])
                if length:
                    for page in range(buf >> 8, ((buf + length - 1) >> 8) + 1):
                        expected[1 + page // 8] &= ~(0x80 >> (page % 8))
                assert r['bitmap'] == expected, (fn, buf, length, r)
            count += 1
    # Assemble every independent .ifref route, including save-only/load-only.
    for fn in ('prodos_open', 'prodos_close', 'prodos_read', 'prodos_read_free',
               'prodos_write', 'prodos_load', 'prodos_load_free', 'prodos_save',
               'prodos_load_at'):
        binary, labels = asm_fixture(work, name=fn, entrypoints=(fn,))
        r = invoke(binary, labels, fn)
        assert r['error'] == 0, (fn, r)
        if fn == 'prodos_open':
            assert r['actual'] == 0
        count += 1
    print(f'ProDOS files: {count} ASM/C injected scenarios, first error/CLOSE, '
          'actual reset, refs/SET_EOF/SET_MARK, bitmap boundaries/restoration, Y/ZP and .ifref OK.')
    return asm, L


def dependencies(work):
    build = work / 'chroma-build'
    build.mkdir()
    obj = build / 'file.o'
    obj.write_bytes(b'')
    args = ['make', '-s', '-C', str(ROOT / 'chromabreak'), f'BUILD={build}', '-n']
    plain = subprocess.run([*args, str(obj)], check=True, capture_output=True, text=True)
    assert 'ca65' not in plain.stdout, plain.stdout
    forced = subprocess.run([*args, '-W', '../dev/lib/prodos/file.asm', str(obj)],
                            check=True, capture_output=True, text=True)
    assert 'ca65' in forced.stdout and 'prodos/file.s' in forced.stdout, forced.stdout
    print('ProDOS files: CHROMABREAK rebuilds file.o when included file.asm changes OK.')


def native(work):
    scenarios = (('SHORT', 17), ('ZERO', 0), ('NEW', 513))
    source = '''.setcpu "65C02"
.code
start:  bit $C000
        bpl start
        bit $C010
        cld
        lda #$FF
        ldx #3
:       sta $BF5C,x             ; protect code $2000-$3FFF
        dex
        bpl :-
        ldx #0
:       txa
        sta $4000,x
        sta $4100,x
        sta $4200,x
        sta $4300,x
        inx
        bne :-
        lda #$00
        sta pf_iobuf
        lda #$10
        sta pf_iobuf+1
'''
    for index, (name, length) in enumerate(scenarios):
        source += f'''
        lda #<name{index}
        sta pf_name
        lda #>name{index}
        sta pf_name+1
        lda #0
        sta pf_buf
        lda #$40
        sta pf_buf+1
        lda #<{length}
        sta pf_len
        lda #>{length}
        sta pf_len+1
        jsr prodos_save
        sta results+{index*13}
        lda pf_got
        sta results+{index*13+1}
        lda pf_got+1
        sta results+{index*13+2}
        jsr prodos_open
        sta results+{index*13+3}
        lda pf_ref
        sta eof_ref
        jsr $BF00
        .byte $D1               ; GET_EOF, checked independently of actual
        .word get_eof
        sta results+{index*13+4}
        ldx #2
:       lda eof_pos,x
        sta results+{index*13+5},x
        dex
        bpl :-
        jsr prodos_close
        sta results+{index*13+8}
        ldx #0
        lda #$EE
:       sta $5000,x
        sta $5100,x
        sta $5200,x
        sta $5300,x
        inx
        bne :-
        lda #$50
        sta pf_buf+1
        lda #0
        sta pf_len
        lda #4
        sta pf_len+1
        jsr prodos_load_free
        sta results+{index*13+9}
        lda pf_got
        sta results+{index*13+10}
        lda pf_got+1
        sta results+{index*13+11}
        lda pf_err
        sta results+{index*13+12}
check{index}:
        nop
'''
    # prodos_load_at on MARKS (768 B): 64 bytes at $000201, then past the end ($301).
    for index, (mark, length) in enumerate(((0x201, 0x40), (0x301, 0x10))):
        source += f'''
        lda #<marks
        sta pf_name
        lda #>marks
        sta pf_name+1
        lda #0
        sta pf_buf
        lda #$52
        sta pf_buf+1
        lda #<{length}
        sta pf_len
        lda #>{length}
        sta pf_len+1
        lda #<{mark}
        sta pf_mark
        lda #>{mark}
        sta pf_mark+1
        stz pf_mark+2
        jsr prodos_load_at
        sta at_results+{index*3}
        lda pf_got
        sta at_results+{index*3+1}
        lda pf_got+1
        sta at_results+{index*3+2}
'''
    source += '''at_check:
        nop
done: jmp done
marks: .byte 5, "MARKS"
at_results: .res 6,0
get_eof: .byte 2
eof_ref: .byte 0
eof_pos: .byte 0,0,0
results: .res 39,0
'''
    source += ''.join(f'name{i}: .byte {len(name)}, "{name}"\n'
                      for i, (name, _) in enumerate(scenarios))
    source += '.include "file.asm"\n'
    binary, L = compile_asm(work, 'native', source,
                           config='MEMORY { RAM:start=$2000,size=$2000,type=rw,file=%O; }\n'
                                  'SEGMENTS { CODE:load=RAM,type=ro; }\n')
    boot, _ = compile_asm(work, 'boot', '.define SYSBOOT_FILE "TEST.SYS"\n'
                          '.define SYSBOOT_TITLE "PRODOS FILE TEST"\n.include "sysboot.s"\n',
                          config=(DEV / 'cc65/prodos_sysboot.cfg').read_text())
    disk = a2test.prodos_volume(work / 'native.po', {
        'PRODOS#FF0000': (DEV / 'tools/prodos/PRODOS').read_bytes(),
        'TEST.SYS#FF2000': binary.read_bytes(), 'TEST.SYSTEM#FF2000': boot.read_bytes(),
        'SHORT': b'X' * 2048, 'ZERO': b'Y' * 1024, 'MARKS': aux_data(0x300)}, 'FILETEST')
    steps = ['wait:1100', 'key: ']
    for index, _ in enumerate(scenarios):
        steps += [L.until(f'check{index}', 3000), L.peek('results', 13, index*13), 'peek:5000:1024']
    steps += [L.until('at_check', 3000), L.peek('at_results', 6), 'peek:5200:64']
    r = a2test.run(disk, steps, iie=True)
    at = r.mem(L['at_results'], 6)
    assert at == bytes([0, 0x40, 0, 0x4D, 0, 0]), ('prodos_load_at', at.hex())
    assert r.mem(0x5200, 64, len(scenarios)) == aux_data(0x300)[0x201:0x241], 'prodos_load_at contents'

    for index, (name, length) in enumerate(scenarios):
        status = 0 if length else 0x4C
        expected = (b'\0' + length.to_bytes(2, 'little') + b'\0\0' +
                    length.to_bytes(3, 'little') + bytes([0, status]) +
                    length.to_bytes(2, 'little') + bytes([status]))
        assert r.dumps[index*2] == expected, (name, r.dumps[index*2], expected, r.out[:3500])
        assert r.dumps[index*2+1] == (bytes(i & 255 for i in range(length)) +
                                        b'\xEE' * (1024-length)), (name, 'file contents/EOF')
    print('ProDOS files on disk: shorter 2048 -> 17 B, empty 1024 -> 0 B, '
          'missing -> 513 B; independent GET_EOF and reload contents; '
          'load_at 64 B at $000201, $4D past the end OK.')


def aux_data(length):
    return bytes((i * 7 + i // 256 + 3) & 255 for i in range(length))


def native_aux(work):
    """prodos_load_aux on a real ProDOS volume: chunks through a main window
    into aux, read back with auxmem.asm's aux_fetch_pages (aux_fetch_chunked
    and AUXMOVE too), with a length limit, an exact multiple of the window,
    a missing and an empty file."""
    # name, file length (None: missing), window, max, error, bytes moved
    scenarios = (('AUXF', 0x2345, 0x800, 0x2345, 0, 0x2345),
                 ('AUXF', 0x2345, 0x800, 0x2000, 0x56, 0x2000),
                 ('EXACT', 0x1000, 0x800, 0x3000, 0, 0x1000),
                 ('NOPE', None, 0x800, 0x3000, 0x46, 0),
                 ('EMPTY', 0, 0x800, 0x3000, 0, 0))
    source = '''.setcpu "65C02"
.include "auxmem.asm"           ; first: the AUXMOVE macro (routines: at the end)
.code
start:  bit $C000
        bpl start
        bit $C010
        cld
        lda #$FF
        ldx #3
:       sta $BF5C,x             ; protect code $2000-$3FFF
        dex
        bpl :-
        lda #$00
        sta pf_iobuf
        lda #$10
        sta pf_iobuf+1
'''
    for index, (name, _, window, limit, _, _) in enumerate(scenarios):
        source += f'''
        jsr fill_aux
        lda #<name{index}
        sta pf_name
        lda #>name{index}
        sta pf_name+1
        stz pf_buf
        lda #$40
        sta pf_buf+1
        lda #<{window}
        sta pf_len
        lda #>{window}
        sta pf_len+1
        lda #$5A                ; ignored: page aligned
        sta pa_dst
        lda #$60
        sta pa_dst+1
        lda #<{limit}
        sta pa_max
        lda #>{limit}
        sta pa_max+1
        jsr prodos_load_aux
        sta results+{index*4}
        lda pf_got
        sta results+{index*4+1}
        lda pf_got+1
        sta results+{index*4+2}
        lda pf_err
        sta results+{index*4+3}
        lda #48                 ; aux $6000-$8FFF -> main $5000-$7FFF
        ldx #$60
        ldy #$50
        jsr aux_fetch_pages
check{index}:
        nop
'''
        if index == 0:
            source += '''
        lda #<$8000             ; aux $6001, $123 bytes -> main $8000
        sta auxmem_fdst
        lda #>$8000
        sta auxmem_fdst+1
        lda #<$123
        sta auxmem_flen
        lda #>$123
        sta auxmem_flen+1
        lda #<$6001
        ldy #>$6001
        jsr aux_fetch_chunked
        AUXMOVE $6100, $61FF, $8200, AUX_TO_MAIN
extra:  nop
'''
    source += '''done: jmp done
; aux $6000-$8FFF = $EE (RAMWRT aux, interrupts masked)
fill_aux:
        php
        sei
        lda #$60
        sta $07
        stz $06
        ldy #0
        lda #$EE
        sta $C005
:       sta ($06),y
        iny
        bne :-
        inc $07
        ldx $07
        cpx #$90
        bne :-
        sta $C004
        plp
        rts
results: .res 20,0
'''
    source += ''.join(f'name{i}: .byte {len(name)}, "{name}"\n'
                      for i, (name, *_) in enumerate(scenarios))
    source += '.include "file.asm"\n.include "auxmem.asm"\n'
    binary, L = compile_asm(work, 'native_aux', source,
                            config='MEMORY { ZP: start=$50,size=$40,type=rw; '
                                   'RAM:start=$2000,size=$2000,type=rw,file=%O; }\n'
                                   'SEGMENTS { ZEROPAGE: load=ZP,type=zp; CODE:load=RAM,type=ro; '
                                   'BSS: load=RAM,type=bss,optional=yes; }\n')
    boot, _ = compile_asm(work, 'boot_aux', '.define SYSBOOT_FILE "TEST.SYS"\n'
                          '.define SYSBOOT_TITLE "PRODOS AUX TEST"\n.include "sysboot.s"\n',
                          config=(DEV / 'cc65/prodos_sysboot.cfg').read_text())
    disk = a2test.prodos_volume(work / 'native_aux.po', {
        'PRODOS#FF0000': (DEV / 'tools/prodos/PRODOS').read_bytes(),
        'TEST.SYS#FF2000': binary.read_bytes(), 'TEST.SYSTEM#FF2000': boot.read_bytes(),
        **{name: aux_data(length) for name, length, *_ in scenarios if length is not None}},
        'AUXTEST')
    steps = ['wait:1100', 'key: ']
    for index, _ in enumerate(scenarios):
        steps += [L.until(f'check{index}', 3000), L.peek('results', 4, index * 4),
                  'peek:5000:12288']
        if index == 0:
            steps += [L.until('extra', 3000), 'peek:8000:768']
    r = a2test.run(disk, steps, iie=True)
    blank = b'\xEE' * 0x3000
    for index, (name, length, window, limit, error, moved) in enumerate(scenarios):
        res = r.mem(L['results'] + index * 4, 4)
        assert res == bytes([error, moved & 255, moved >> 8, error]), (name, hex(limit), res.hex())
        aux = r.mem(0x5000, 0x3000, index)
        assert aux[:moved] == aux_data(moved), (name, 'aux contents')
        tail = (moved + 255) & ~255
        assert aux[tail:] == blank[tail:], (name, 'aux past the stored pages', hex(tail))
        if index == 0:
            extra = r.mem(0x8000, 768)
            assert extra[:0x123] == aux_data(0x124)[1:], 'aux_fetch_chunked'
            assert extra[0x200:0x300] == aux_data(0x200)[0x100:], 'AUXMOVE'
    print(f'ProDOS files into aux: {len(scenarios)} loads (chunks through a main window, '
          'limit -> $56 before the store, exact multiple, missing, empty) read back by '
          'aux_fetch_pages; aux_fetch_chunked and AUXMOVE OK.')


if __name__ == '__main__':
    if a2test.have_a2shot('ProDOS files (65C02)'):
        with tempfile.TemporaryDirectory(prefix='prodos-file-') as tmp:
            dependencies(Path(tmp))
            injected(Path(tmp))
            native(Path(tmp))
            native_aux(Path(tmp))
