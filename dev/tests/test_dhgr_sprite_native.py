#!/usr/bin/env python3
"""Native masked rows: source/screen crossings, raw counts and ordered stores.

Exercise every count byte, including the existing zero-means-256 behavior.
The screen address deliberately crosses a page, beyond visible-row bounds,
and the data/mask pointers independently visit all low-byte alignments.
"""
import argparse
import tempfile
from pathlib import Path

import test_hgr
from test_hgr import DEV, build, a2test
from test_dhgr import PATTERNS
from test_dhgr_spr import STORE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEV/'lib/hgrc/dhgr_block_asm.s',
                        help='optional old or candidate assembly member')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-sprite-native-') as directory:
        work = Path(directory)
        fixture = work/'fixture.c'
        fixture.write_text('''#include "dhgr_internal.h"
void tint(void); void started(void); void finished(void);
unsigned char data[512],masks[512],irq_after,intact;
int main(void) {
    unsigned i;
    unsigned char page,bank,count;
    if(!dhgr_init()) return 1;
    for(i=0;i<512;++i) {
        data[i]=(unsigned char)(i*29u+17u);
        masks[i]=(unsigned char)(i*73u+91u);
    }
    for(page=1;page<=2;++page) for(bank=0;bank<2;++bank) {
        count=0;
        do {
            dhgr_draw_page(1); dhgr_clear(6);
            dhgr_draw_page(2); dhgr_clear(9);
            dhgr_addr=(unsigned char*)((page==1?0x2000u:0x4000u)+0xf0u+(count&15));
            dhgr_aux=bank; dhgr_count=count;
            dhgr_buffer=data+((count*131u)&255u);
            dhgr_sprite_mask=masks+((count*73u+17u)&255u);
            tint();
            if((count^bank)&1) { asm("sei"); } else { asm("cli"); }
            started(); dhgr_sprite_asm();
            asm("php"); asm("pla"); asm("sta _irq_after");
            intact=dhgr_addr==(unsigned char*)((page==1?0x2000u:0x4000u)+0xf0u+(count&15))
                &&dhgr_aux==bank &&dhgr_count==count
                &&dhgr_buffer==data+((count*131u)&255u)
                &&dhgr_sprite_mask==masks+((count*73u+17u)&255u);
            finished(); asm("cli"); ++count;
        } while(count);
    }
    for(;;) {} return 0;
}
''')
        marker = work/'marker.s'
        marker.write_text('''.export _tint, _started, _finished
.import _dhgr_addr
.importzp ptr1
.code
_started: rts
_finished: rts
_tint:
    php
    sei
    lda _dhgr_addr
    sta ptr1
    lda _dhgr_addr+1
    sta ptr1+1
    ldy #128
    lda #$a5
@main: sta (ptr1),y
    dey
    bpl @main
    sta $c005
    ldy #128
    lda #$da
@aux: sta (ptr1),y
    dey
    bpl @aux
    sta $c004
    plp
    rts
''')
        original = test_hgr.compile_source

        def compile_member(source, obj, flags):
            source = args.source if Path(source).name == 'dhgr_block_asm.s' else source
            return original(source, obj, flags)

        test_hgr.compile_source = compile_member
        try:
            disk = build(work, fixture, extra_sources=(marker,))
        finally:
            test_hgr.compile_source = original
        labels = a2test.labels(work/'test.lbl')
        steps = []
        for _ in range(1024):
            steps += [labels.until('_started'), 'storewatch:2000:5FFF',
                      labels.until('_finished'), 'unstorewatch',
                      labels.peek('_irq_after', 2), 'peek:C013:2', 'peek:2000:16384',
                      'poke:C003:0', 'peek:2000:16384', 'poke:C002:0']
        result = a2test.run(disk, steps, iie=True)
        assert len(result.dumps) == 4096
        expected_stores = []
        frame = 0
        for page in range(2):
            for bank in range(2):
                for count in range(256):
                    banks = [[bytearray(PATTERNS[color][1-b::2])*4096
                              for b in (0, 1)] for color in (6, 9)]
                    address = 0xf0+(count&15)
                    data_start, mask_start = (count*131)&255, (count*73+17)&255
                    for b in (0, 1):
                        banks[page][b][address:address+129] = bytes([0xa5 if b == 0 else 0xda])*129
                    at, auxiliary = address, bank
                    for j in range(count or 256):
                        mask = ((mask_start+j)*73+91)&255
                        write = (~mask)&127
                        b = 1 if auxiliary else 0
                        if write:
                            old = banks[page][b][at]
                            data = ((data_start+j)*29+17)&127
                            value = data if write == 127 else (old&~write)|(data&write)
                            banks[page][b][at] = value
                            expected_stores.append((b, 0x2000*(page+1)+at, value))
                        if not auxiliary:
                            at += 1
                        auxiliary ^= 1
                    status, state, main, aux = result.dumps[frame*4:frame*4+4]
                    assert bool(status[0]&4) == bool((count^bank)&1), ('IRQ', page, bank, count)
                    assert status[1] == 1, ('shared parameters', page, bank, count)
                    assert not any(v&128 for v in state), ('banks', page, bank, count)
                    assert main == banks[0][0]+banks[1][0], ('main', page, bank, count)
                    assert aux == banks[0][1]+banks[1][1], ('aux', page, bank, count)
                    frame += 1
        stores = []
        for line in result.out.splitlines():
            match = STORE.match(line)
            if match:
                assert match[9] == '0' and match[10] == '0', ('ALTZP/RAMRD', line)
                assert int(match[6], 16)&4, ('unmasked store', line)
                stores.append((1 if match[11] == '1' else 0,
                               int(match[2], 16), int(match[3], 16)))
        assert stores == expected_stores, ('store order', len(stores), len(expected_stores))
    print(f'Native sprite: {frame:,} calls, every count including zero=256, both banks/pages,')
    print(f'independent source/screen crossings, globals, IRQ masks and {len(stores):,} ordered stores OK.')


if __name__ == '__main__':
    main()
