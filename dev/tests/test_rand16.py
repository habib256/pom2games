#!/usr/bin/env python3
"""C PRNG ABI and state transition for all 65,536 input states."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import DEV, run, a2test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rand16-') as directory:
        work = Path(directory)
        fixture = work / 'fixture.s'
        fixture.write_text('''
.import _a2_rand16, _a2_rand_state
.export start, done, fail, seed_hi, results
.bss
seed_hi: .res 1
seed_lo: .res 1
saved_stack: .res 1
results: .res 1024
.code
start:
 sei
 cld
 lda _a2_rand_state
 cmp #$E1
 bne fail
 lda _a2_rand_state+1
 cmp #$AC
 bne fail
 lda #0
 sta seed_lo
loop:
 lda seed_lo
 sta _a2_rand_state
 lda seed_hi
 sta _a2_rand_state+1
 tsx
 stx saved_stack
 ldy #$A5
 jsr _a2_rand16
 cpy #$A5
 bne fail
 ldy seed_lo
 sta results,y
 txa
 sta results+256,y
 lda _a2_rand_state
 sta results+512,y
 lda _a2_rand_state+1
 sta results+768,y
 tsx
 cpx saved_stack
 bne fail
 inc seed_lo
 bne loop
done: jmp done
fail: jmp fail
''')
        cfg = work / 'fixture.cfg'
        cfg.write_text('''MEMORY {
 MAIN: start=$6000, size=$3000, type=rw, file=%O;
 RAM: start=$4000, size=$1000, type=rw;
}
SEGMENTS {
 CODE: load=MAIN, type=ro;
 DATA: load=MAIN, type=rw;
 BSS: load=RAM, type=bss;
}
''')
        kernel = work / 'kernel.s'
        kernel.write_text((DEV/'lib/apple2c/apple2rand.s').read_text()+
                          '\n.export rand_end\nrand_end:\n')
        objects = []
        for source in (fixture, kernel):
            obj = source.with_suffix('.o')
            run(['ca65', '-I', DEV/'lib/apple2', '-o', obj, source])
            objects.append(obj)
        binary, labels = work/'fixture.bin', work/'fixture.lbl'
        run(['ld65', '-C', cfg, '-Ln', labels, '-o', binary, *objects])
        points = a2test.labels(labels)
        disk = a2test.build_disk(work, 'TEST', binary) if args.iie else None
        for high in range(256):
            steps = a2test.bin_steps(binary)+[points.poke('seed_hi', high),
                    points.until('done'), points.peek('results', 1024)]
            result = a2test.run(disk, steps, iie=args.iie)
            expected = bytearray(1024)
            for low in range(256):
                seed = high*256+low
                value = (seed >> 1) ^ (0xB400 if seed & 1 else 0)
                expected[low] = expected[512+low] = value & 255
                expected[256+low] = expected[768+low] = value >> 8
            assert result.mem(points['results'], 1024) == expected, high
        print(f'C PRNG: all 65,536 states, return A/X, stored state, initial seed, '
              f'Y and balanced stack OK; {points["rand_end"]-points["_a2_rand16"]} '
              f'code bytes; IIe={args.iie}.')


if __name__ == '__main__':
    main()
