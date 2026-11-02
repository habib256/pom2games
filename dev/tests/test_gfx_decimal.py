#!/usr/bin/env python3
"""All signed/unsigned 16-bit decimal strings, lengths and buffer guards."""
from pathlib import Path
import tempfile
from test_hgr import DEV, run, compile_source, a2test


def check(work):
    source = work/'numbers.c'
    source.write_text('''#include "gfx.h"
void begin(void); void end(void);
unsigned char records[256][10];
int main(void) {
    unsigned hi, lo;
    unsigned char mode, i;
    for (mode=0; mode<2u; ++mode) for (hi=0; hi<256u; ++hi) {
        begin();
        for (lo=0; lo<256u; ++lo) {
            for (i=0; i<10u; ++i) records[lo][i]=0xA5u;
            if (mode) records[lo][9]=gfx_itoa((char *)records[lo]+1, (int)((hi<<8)|lo));
            else records[lo][9]=gfx_utoa((char *)records[lo]+1, (hi<<8)|lo);
        }
        end();
    }
    for (;;) {}
    return 0;
}
''')
    markers = work/'markers.s'
    markers.write_text('.export _begin, _end\n.code\n_begin: rts\n_end: rts\n')
    objects = []
    for index,path in enumerate((DEV/'cc65/crt0_apple2.s',source,markers,
                                DEV/'lib/gfx/gfx_num_dec.s',DEV/'lib/gfx/gfx_num_signed.s',
                                DEV/'lib/hgrc/hgr_utoa_asm.s')):
        obj = work/f'{index}.o'
        compile_source(path,obj,['-t','none','-Oirs','-I',DEV/'lib/gfx'])
        objects.append(obj)
    binary = work/'numbers.bin'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
         '-Ln',work/'numbers.lbl','-o',binary,*objects])
    labels = a2test.labels(work/'numbers.lbl')
    steps = a2test.bin_steps(binary)
    for _ in range(512):
        steps += [labels.until('_begin'),labels.until('_end'),labels.peek('_records',2560)]
    data = a2test.run(None,steps).data
    assert len(data) == 2*65536*10
    for mode in range(2):
        for bits in range(65536):
            value = bits-65536 if mode and bits >= 32768 else bits
            digits = str(value).encode()
            expected = b'\xA5'+digits+b'\0'+b'\xA5'*(7-len(digits))+bytes([len(digits)])
            offset = (mode*65536+bits)*10
            assert data[offset:offset+10] == expected, (mode,value,data[offset:offset+10],expected)
    print('Decimal: all 131072 signed/unsigned strings, digit counts, NULs and guards OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='gfx-decimal-') as tmp:
        check(Path(tmp))
