#!/usr/bin/env python3
"""Glyph address arithmetic: unaligned fonts, carries, wraparound and X/Y ABI."""
import argparse
from pathlib import Path
import tempfile

from test_hgr import build, a2test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-glyph-addr-') as directory:
        work = Path(directory)
        source = work / 'address.c'
        source.write_text('''#include "hgr_internal.h"
void probe(void); void sampled(void);
unsigned char results[193], incoming; /* 96 low bytes, 96 high bytes, ABI flag */
static const unsigned bases[3]={0x0800u,0x6000u,0xff00u};
int main(void) {
    unsigned low;
    unsigned char bank;
    for (bank=0; bank<3; ++bank)
      for (low=0; low<256; ++low)
        for (incoming=0; incoming<2; ++incoming) {
            hgr_t_font=(const unsigned char *)(bases[bank]+low);
            probe(); sampled();
        }
    for (;;) {}
    return 0;
}
''')
        probe = work / 'probe.s'
        probe.write_text('''.export _probe, _sampled, resume, call_addr, returned
.import glyph_addr, _results, _incoming
.importzp _hgr_g_glyph
.bss
index: .res 1
.code
_probe:
    lda #0
    sta index
    sta _results+192
loop:
    ldx #$a5
    ldy #$5a
    lda _incoming
    lsr
    lda index
call_addr:
    jsr glyph_addr
returned:
    cpx #$a5
    bne failed
    cpy #$5a
    bne failed
    ldy index
    lda _hgr_g_glyph
    sta _results,y
    lda _hgr_g_glyph+1
    sta _results+96,y
    inc index
    lda index
    cmp #96
    bne loop
    rts
failed:
    lda #1
    sta _results+192
    rts
_sampled: nop
resume: rts
''')
        disk = build(work, source, extra_sources=(probe,))
        labels = a2test.labels(work / 'test.lbl')
        steps = [labels.until('call_addr'), labels.until('returned')]
        bases = [high+low for high in (0x0800, 0x6000, 0xFF00) for low in range(256)]
        for _ in range(len(bases)*2):
            steps += [labels.until('_sampled'), labels.peek('_results', 193),
                      labels.peek('_hgr_t_font', 2),
                      labels.until('resume')]
        result = a2test.run(disk, steps, iie=args.iie)
        cycles = result.cycles[1]-result.cycles[0]
        frame = 0
        for base in bases:
            addresses = [(base+8*i) & 65535 for i in range(96)]
            expected = bytes(value & 255 for value in addresses) + bytes(value >> 8 for value in addresses)
            for carry in range(2):
                record, font = result.dumps[frame*2:frame*2+2]
                assert record[192] == 0, ('X/Y clobbered', base, carry)
                assert record[:192] == expected, ('glyph address', base, carry)
                assert int.from_bytes(font, 'little') == base, ('font pointer changed', base, carry)
                frame += 1
    print(f'Glyph address: {frame*96:,} calls, every font low byte, both input carries,')
    print(f'16-bit wraparound and X/Y preservation OK; native call {cycles} cycles including JSR/RTS.')


if __name__ == '__main__':
    main()
