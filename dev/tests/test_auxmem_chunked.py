#!/usr/bin/env python3
"""lib/apple2/auxmem.asm aux_store_chunked / aux_fetch_chunked on an enhanced
//e (a2shot): 700 bytes main -> aux -> main through page boundaries and a
last partial chunk, source and neighbours untouched, variables consumed.
Built twice: the ROM's AUXMOVE (default) and AUXMEM_CHUNK_NATIVE = 1 (the
zero-page loop); both must move the same bytes, and the native one must be
at least 1.8 times faster. Fetch-only build of the native flavour too."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

N = 700
PROGRAM = '''
.setcpu "65C02"
.include "apple2.inc"
.code
        ldx #0                  ; source: $4000.., pattern; guards around
@fill:  txa
        eor #$5C
        sta $4000,x
        adc #$31
        sta $4100,x
        eor #$FF
        sta $4200,x
        lda #$EE
        sta $5000,x
        sta $5100,x
        sta $5200,x
        sta $5300,x
        inx
        bne @fill
.if STORE
        lda #<$3011             ; main $4000 -> aux $3011, N bytes
        sta auxmem_fdst
        lda #>$3011
        sta auxmem_fdst+1
        lda #<N
        sta auxmem_flen
        lda #>N
        sta auxmem_flen+1
        lda #<$4000
        ldy #>$4000
t0:     jsr aux_store_chunked
t1:
.endif
        lda #<$5005             ; aux $3011 -> main $5005
        sta auxmem_fdst
        lda #>$5005
        sta auxmem_fdst+1
        lda #<N
        sta auxmem_flen
        lda #>N
        sta auxmem_flen+1
        lda #<$3011
        ldy #>$3011
t2:     jsr aux_fetch_chunked
done:   jmp done
N = %d
.include "auxmem.asm"
.export t2, done, auxmem_flen, auxmem_fdst
.if STORE
.export t0, t1
.endif
''' % N


def run(work, defines, store=True):
    (work / 't.s').write_text(defines + f'STORE = {int(store)}\n' + PROGRAM)
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(work / 't.o'), str(work / 't.s')], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 't.lbl'),
                    '-o', str(work / 't.bin'), str(work / 't.o')], check=True)
    L = a2test.labels(work / 't.lbl')
    disk = a2test.build_disk(work, 'AUXT', work / 't.bin')
    marks = (['t0', 't1'] if store else []) + ['t2', 'done']
    r = a2test.run(disk, ['wait:300'] + [L.until(m, 4000) for m in marks]
                   + ['peek:4000:768', 'peek:5000:1024', L.peek('auxmem_flen', 2), L.peek('auxmem_fdst', 2)],
                   iie=True)
    return L, r


def main():
    if not a2test.have_a2shot('aux chunked copies'):
        return
    cycles = {}
    for label, defines in (('AUXMOVE', ''), ('native', 'AUXMEM_CHUNK_NATIVE = 1\n')):
        with tempfile.TemporaryDirectory(prefix='auxc-') as tmp:
            L, r = run(Path(tmp), defines)
            source = r.mem(0x4000, 768)
            back = r.mem(0x5000, 1024)
            assert back[5:5 + N] == source[:N], f'{label}: main -> aux -> main differs'
            assert back[:5] == b'\xEE' * 5 and back[5 + N:] == b'\xEE' * (1024 - 5 - N), f'{label}: wrote outside the range'
            assert r.mem(L['auxmem_flen'], 2) == b'\0\0', f'{label}: length not consumed'
            assert int.from_bytes(r.mem(L['auxmem_fdst'], 2), 'little') == 0x5005 + N, f'{label}: destination not advanced'
            c = r.cycles
            cycles[label] = (c[1] - c[0], c[3] - c[2])
    with tempfile.TemporaryDirectory(prefix='auxc-') as tmp:      # the fetch-only build assembles and runs
        L, r = run(Path(tmp), 'AUXMEM_CHUNK_NATIVE = 1\n', store=False)
        assert r.mem(L['auxmem_flen'], 2) == b'\0\0', 'native fetch-only: length not consumed'
    (s0, f0), (s1, f1) = cycles['AUXMOVE'], cycles['native']
    assert s0 >= 1.8 * s1 and f0 >= 1.8 * f1, cycles
    print(f'aux chunked: {N} bytes main -> aux -> main exact, both flavours; store {s0} -> {s1} cycles '
          f'({s0 / N:.1f} -> {s1 / N:.1f} a byte), fetch {f0} -> {f1} ({f0 / N:.1f} -> {f1 / N:.1f}).')


if __name__ == '__main__':
    main()
