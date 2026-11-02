#!/usr/bin/env python3
"""All 16-bit hex inputs on the 6502, lengths, NULs and buffer guards.

--implementation accepts a former C/assembly implementation for comparisons.
Reported cycles include the identical C fixture and buffer initialization.
"""
import argparse
from pathlib import Path
import tempfile
from test_hgr import DEV, run, compile_source, a2test


def check(work, implementation):
    source = work / 'hex.c'
    source.write_text('''#include "gfx.h"
void begin(void); void end(void);
unsigned char records[256][9];
int main(void) {
    unsigned hi, lo;
    unsigned char i;
    for (hi=0; hi<256u; ++hi) {
        begin();
        for (lo=0; lo<256u; ++lo) {
            for (i=0; i<9u; ++i) records[lo][i]=0xA5u;
            records[lo][8]=gfx_hexstr((char *)records[lo]+1, (hi<<8)|lo);
        }
        end();
    }
    for (;;) {}
    return 0;
}
''')
    markers = work / 'markers.s'
    markers.write_text('.export _begin, _end\n.code\n_begin: rts\n_end: rts\n')
    objects = []
    for index, path in enumerate((DEV/'cc65/crt0_apple2.s', source, markers, implementation)):
        obj = work / f'{index}.o'
        compile_source(path, obj, ['-t', 'none', '-Oirs', '-I', DEV/'lib/gfx'])
        objects.append(obj)
    binary = work/'hex.bin'
    run(['cl65', '-t', 'none', '-C', DEV/'cc65/apple2_hgr_c.cfg',
         '-Ln', work/'hex.lbl', '-o', binary, *objects])
    labels = a2test.labels(work/'hex.lbl')
    steps = a2test.bin_steps(binary)
    for _ in range(256):
        steps += [labels.until('_begin'), labels.until('_end'), labels.peek('_records', 256*9)]
    result = a2test.run(None, steps)
    data = result.data
    assert len(data) == 65536*9
    for value in range(65536):
        digits = f'{value:X}'.encode()
        expected = b'\xA5' + digits + b'\0' + b'\xA5'*(6-len(digits)) + bytes([len(digits)])
        actual = data[value*9:(value+1)*9]
        assert actual == expected, (value, actual, expected)
    assert len(result.cycles) == 512
    cycles = sum(result.cycles[i+1]-result.cycles[i]-12 for i in range(0,512,2))
    print(f'Hex: all 65536 inputs, lengths, NULs and guards OK; '
          f'{binary.stat().st_size} loaded bytes, {cycles} fixture cycles.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--implementation', type=Path, default=DEV/'lib/gfx/gfx_num_hex.s')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gfx-hex-') as tmp:
        check(Path(tmp), args.implementation)
