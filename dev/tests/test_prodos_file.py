#!/usr/bin/env python3
"""Execute the real ASM/C file helpers on a 65C02, with an injected MLI.

The stub only implements the MLI calling convention and controlled results;
it does not replace the helpers under test. Real ProDOS separately checks
replacement with shorter/empty files and missing-file creation on disk.
"""
from pathlib import Path
import re
import shutil
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
bitmap_seen: .res 26
saved_y: .res 1
command: .res 1
stub_end:
'''


def compile_asm(work, name, source, extra=(), config=CFG):
    src = work / (name + '.s')
    src.write_text(source)
    obj = src.with_suffix('.o')
    subprocess.run(['ca65', '--cpu', '65c02', '-g', '-I', str(PD), '-o', str(obj), str(src)], check=True)
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
                       'prodos_load_free', 'prodos_save')
    refs = '.code\n' + ''.join(f' jsr {fn}\n' for fn in entrypoints)
    return compile_asm(work, name, refs + f'.include "{include}"\n' + STUB)


def c_fixture(work):
    src = work / 'calls.c'
    src.write_text('''#include "prodos.h"
unsigned char c_load(void) { return prodos_load(); }
unsigned char c_free(void) { return prodos_load_free(); }
unsigned char c_save(void) { return prodos_save(); }
''')
    cobj, pobj = work / 'calls.o', work / 'file.o'
    subprocess.run(['cl65', '-t', 'none', '--cpu', '65c02', '-Oirs', '-I', str(PD),
                    '-c', '-o', str(cobj), str(src)], check=True)
    subprocess.run(['ca65', '-g', '-o', str(pobj), str(PD / 'file.s')], check=True)
    return compile_asm(work, 'c', STUB, (cobj, pobj))


def invoke(binary, labels, fn, buf=0x2000, length=0x100, errors=(), actual=0x100,
           stale=0xBEEF, leave=False, reopen=0):
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
    for command, error in errors:
        byte('errors', error, command)
    steps += ['regs:77:88:9A', f'call:{L[fn]:04X}:3', L.peek('pf_err'),
              L.peek('pf_got', 2), L.peek('log_count'), L.peek('log', 16),
              L.peek('refs', 16), L.peek('eof_seen', 5), L.peek('actual_seen', 2),
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
                eof=r.mem(L['eof_seen'], 5), bitmap=r.mem(L['bitmap_seen'], 26),
                initial_actual=r.mem(L['actual_seen'], 2), cycles=elapsed, original=bitmap)


def injected(work):
    asm, L = asm_fixture(work)
    c, C = c_fixture(work)
    count = 0
    for binary, labels, load, free, save in (
            (asm, L, 'prodos_load', 'prodos_load_free', 'prodos_save'),
            (c, C, '_c_load', '_c_free', '_c_save')):
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
        r = invoke(binary, labels, free, buf=0xBFFF, length=2,
                   errors=[(0xCC, 0x2E)])
        assert (r['error'], r['actual'], r['log']) == (0x56, 0, b'\xC8\xCC'), r
        count += 1
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
               'prodos_write', 'prodos_load', 'prodos_load_free', 'prodos_save'):
        binary, labels = asm_fixture(work, name=fn, entrypoints=(fn,))
        r = invoke(binary, labels, fn)
        assert r['error'] == 0, (fn, r)
        if fn == 'prodos_open':
            assert r['actual'] == 0
        count += 1
    print(f'ProDOS files: {count} ASM/C injected scenarios, first error/CLOSE, '
          'actual reset, refs/SET_EOF, bitmap boundaries/restoration, Y/ZP and .ifref OK.')
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
    source += '''done: jmp done
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
    stage = work / 'stage'
    stage.mkdir()
    shutil.copyfile(DEV / 'tools/prodos/PRODOS', stage / 'PRODOS#FF0000')
    shutil.copyfile(binary, stage / 'TEST.SYS#FF2000')
    shutil.copyfile(boot, stage / 'TEST.SYSTEM#FF2000')
    (stage / 'SHORT').write_bytes(b'X' * 2048)
    (stage / 'ZERO').write_bytes(b'Y' * 1024)
    disk = work / 'native.po'
    subprocess.run([sys.executable, str(DEV / 'tools/prodos/build_volume.py'),
                    str(stage), str(disk), '--volume', 'FILETEST', '--blocks', '280',
                    '--boot', str(DEV / 'tools/prodos/boot.bin')], check=True,
                   capture_output=True, text=True)
    steps = ['wait:1100', 'key: ']
    for index, _ in enumerate(scenarios):
        steps += [L.until(f'check{index}', 3000), L.peek('results', 13, index*13), 'peek:5000:1024']
    r = a2test.run(disk, steps, iie=True)
    for index, (name, length) in enumerate(scenarios):
        status = 0 if length else 0x4C
        expected = (b'\0' + length.to_bytes(2, 'little') + b'\0\0' +
                    length.to_bytes(3, 'little') + bytes([0, status]) +
                    length.to_bytes(2, 'little') + bytes([status]))
        assert r.dumps[index*2] == expected, (name, r.dumps[index*2], expected, r.out[:3500])
        assert r.dumps[index*2+1] == (bytes(i & 255 for i in range(length)) +
                                        b'\xEE' * (1024-length)), (name, 'file contents/EOF')
    print('ProDOS files on disk: shorter 2048 -> 17 B, empty 1024 -> 0 B, '
          'missing -> 513 B; independent GET_EOF and reload contents OK.')


if __name__ == '__main__':
    if a2test.have_a2shot('ProDOS files (65C02)'):
        with tempfile.TemporaryDirectory(prefix='prodos-file-') as tmp:
            dependencies(Path(tmp))
            injected(Path(tmp))
            native(Path(tmp))
