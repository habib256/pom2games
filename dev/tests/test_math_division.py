#!/usr/bin/env python3
"""Exhaustive 16/8 division, including zero divisor and the preserved Y register."""
from pathlib import Path
import tempfile
import argparse
import subprocess
from test_math import ROOT, a2test

MATH=ROOT/'dev/lib/math'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full',action='store_true',help='check all 16,777,216 pairs')
    args=parser.parse_args()
    divisors=range(256) if args.full else (0,1,2,3,7,15,16,31,32,63,64,127,128,129,254,255)
    with tempfile.TemporaryDirectory(prefix='math-division-') as directory:
        work=Path(directory)
        source=work/'divide.s'
        source.write_text('''MUL_TABLES=$0800
.include "math.inc"
.zeropage
input: .res 2
divisor: .res 1
.code
start: sei
 cld
 lda #0
 sta input
 sta input+1
loop:
 lda input
 sta mul_x
 lda input+1
 sta mul_x+1
 lda divisor
 ldy #$A5
 jsr div16by8
 cpy #$A5
 bne fail
 ldx input
 sta results+512,x
 lda mul_x
 sta results,x
 lda mul_x+1
 sta results+256,x
 inc input
 bne loop
page_done:
 nop
resume:
 inc input+1
 bne loop
done: jmp done
fail: jmp fail
measure_setup:
 cld
 lda input
 sta mul_x
 lda input+1
 sta mul_x+1
 lda divisor
measure_start:
 jsr div16by8
measure_done:
 jmp measure_done
.align 256
.include "div.asm"
kernel_end:
.bss
results: .res 768
.export start, page_done, resume, done, results, measure_setup, measure_start, measure_done
.export div16by8, kernel_end
.exportzp input, divisor
''')
        cfg=work/'divide.cfg'
        cfg.write_text('''MEMORY {
 ZP: start=$50, size=$B0, type=rw;
 MAIN: start=$6000, size=$3000, type=rw, file=%O;
}
SEGMENTS {
 ZEROPAGE: load=ZP, type=zp;
 CODE: load=MAIN, type=ro, align=$100;
 BSS: load=MAIN, type=bss;
}
''')
        obj,binary,labels=(source.with_suffix(ext) for ext in ('.o','.bin','.lbl'))
        subprocess.run(['ca65','-I',str(MATH),'-o',str(obj),str(source)],check=True)
        subprocess.run(['ld65','-C',str(cfg),'-Ln',str(labels),'-o',str(binary),str(obj)],check=True)
        L=a2test.labels(labels)
        totals=[]
        for divisor in divisors:
            steps=a2test.bin_steps(binary)+[L.poke('divisor',divisor)]
            for _ in range(256):
                steps += [L.until('page_done'),L.peek('results',768),L.until('resume')]
            steps += [L.until('done')]
            result=a2test.run(None,steps)
            for high in range(256):
                nums=range(high*256,(high+1)*256)
                quotients=[n//divisor if divisor else 65535 for n in nums]
                expected=bytes(q&255 for q in quotients)+bytes(q>>8 for q in quotients)
                expected+=bytes(n%divisor if divisor else n&255 for n in nums)
                assert result.dumps[high]==expected, (divisor,high)
            totals.append(result.cycles[-1])
        print(f'Division: {len(divisors)*65536:,} numerator/divisor pairs ({len(divisors)} divisors), Y preserved, zero divisor => $FFFF/low-byte remainder; '
              f'{L["kernel_end"]-L["div16by8"]} code bytes; total sweeps {sum(totals)} cycles.')
        for numerator,divisor in ((0,1),(255,1),(255,2),(65535,255),(32511,127),
                                  (256,1),(65535,1),(65535,2),(65535,127),(65535,128),(65535,0)):
            steps=a2test.bin_steps(binary,start=L['measure_setup'])+[L.poke('input',numerator&255),
                    f'poke:{L["input"]+1:04X}:{numerator>>8:02X}',L.poke('divisor',divisor),
                    L.until('measure_start'),L.until('measure_done')]
            result=a2test.run(None,steps)
            print(f'Division {numerator}/{divisor}: {result.cycles[1]-result.cycles[0]} cycles including JSR/RTS.')


if __name__=='__main__':
    main()
